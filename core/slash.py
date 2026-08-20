import discord
from discord import app_commands
from core.config import bot, EMOJI
from core.player_store import get_player
from core.settings import _t, guild_lang
from core.helpers import anime_embed, format_time
from core.lyrics import search_lyrics
from core.subtitles import (
    extract_subtitle_info, pick_subtitle, download_subtitle_text,
    _download_audio_for_whisper, _whisper_generate_srt, _whisper_lang_code,
    WHISPER_AVAILABLE
)
from core.ytdlp import get_download_ytdl, get_ytdl
from core.helpers import extract_song, URL_REGEX
from core.blacklist import is_blacklisted
import asyncio
import os
import re
from io import BytesIO

# =========================
# SLASH COMMAND TREE
# =========================

tree = bot.tree

def _guild_id(interaction: discord.Interaction) -> int:
    return interaction.guild_id

def _t_slash(interaction: discord.Interaction, key: str, **kw) -> str:
    return _t(interaction.guild_id, key, **kw)

# =========================
# HELPERS
# =========================

async def _ensure_voice(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message(f"{EMOJI['error']} 請先加入語音頻道", ephemeral=True)
        return None
    vc = interaction.guild.voice_client
    if not vc:
        try:
            vc = await interaction.user.voice.channel.connect(timeout=30)
        except discord.VoiceClientConnectionError:
            await interaction.response.send_message(f"{EMOJI['error']} 無法連接到語音頻道", ephemeral=True)
            return None
    elif vc.channel != interaction.user.voice.channel:
        await vc.move_to(interaction.user.voice.channel)
    player = get_player(interaction)
    player.voice = vc
    return player

# =========================
# SLASH COMMANDS
# =========================

@tree.command(name="play", description="播放音樂（關鍵字或網址）")
@app_commands.describe(query="歌名、關鍵字或支援平台的網址")
async def slash_play(interaction: discord.Interaction, query: str):
    player = await _ensure_voice(interaction)
    if not player:
        return
    await interaction.response.defer()
    if not URL_REGEX.match(query):
        query = f"ytsearch1:{query}"
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: get_ytdl().extract_info(query, download=False))
    if "entries" in data:
        data = data["entries"][0]
    song = extract_song(data)
    if is_blacklisted(song):
        embed = anime_embed(
            title=f"{EMOJI['error']} 歌曲已被封鎖",
            description=f"**[{song['title']}]({song.get('url')})**\n\n命中黑名單項目：`{blocked}`"
        )
        await interaction.followup.send(embed=embed)
        return
    player.queue.append(song)
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        embed = anime_embed(
            title=f"{EMOJI['success']} {_t_slash(interaction, 'add_queue')}",
            description=f"**[{song['title']}]({song.get('url')})**",
        )
        embed.add_field(name="⏱ 時長", value=format_time(song["duration"]), inline=True)
        embed.add_field(name="📜 位置", value=f"**{len(player.queue)}**", inline=True)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("✅ 即將開始播放")

@tree.command(name="skip", description="跳過目前歌曲")
async def slash_skip(interaction: discord.Interaction):
    player = get_player(interaction)
    if not player or not player.current:
        return await interaction.response.send_message(f"{EMOJI['skip']} {_t_slash(interaction, 'not_playing')}", ephemeral=True)
    vc = interaction.guild.voice_client
    if vc:
        player._manual_skip = True
        vc.stop()
    await interaction.response.send_message(f"{EMOJI['skip']} {_t_slash(interaction, 'skipped')}")

@tree.command(name="stop", description="停止播放並離開語音頻道")
async def slash_stop(interaction: discord.Interaction):
    player = get_player(interaction)
    if player:
        player._stopped = True
        player._manual_skip = True
        player._kill_proc()
        player.next_event.set()
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
    from core.player_store import players
    players.pop(interaction.guild_id, None)
    await interaction.response.send_message(f"{EMOJI['stop']} {_t_slash(interaction, 'stopped')}")

@tree.command(name="pause", description="暫停播放")
async def slash_pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message(f"{EMOJI['pause']} 已暫停播放")
    else:
        await interaction.response.send_message(f"{EMOJI['warn']} 目前沒有在播放", ephemeral=True)

@tree.command(name="resume", description="繼續播放")
async def slash_resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message(f"{EMOJI['resume']} 已繼續播放")
    else:
        await interaction.response.send_message(f"{EMOJI['warn']} 目前沒有暫停", ephemeral=True)

@tree.command(name="queue", description="顯示播放隊列")
@app_commands.describe(page="頁碼（預設 1）")
async def slash_queue(interaction: discord.Interaction, page: int = 1):
    player = get_player(interaction)
    if not player or not player.queue:
        return await interaction.response.send_message(f"{EMOJI['queue']} {_t_slash(interaction, 'queue_empty')}", ephemeral=True)
    songs = list(player.queue)
    per_page = 10
    total_pages = max(1, (len(songs) + per_page - 1) // per_page)
    if page < 1 or page > total_pages:
        return await interaction.response.send_message(f"{EMOJI['error']} 頁面範圍為 1 ~ {total_pages}", ephemeral=True)
    start = (page - 1) * per_page
    end = start + per_page
    embed = anime_embed(
        title=f"{EMOJI['queue']} 播放隊列",
        description=f"總共 **{len(songs)}** 首歌曲"
    )
    for i, song in enumerate(songs[start:end], start=start+1):
        embed.add_field(name=f"`{i}.` {song['title']}", value=f"⏱ {format_time(song.get('duration', 0))}", inline=False)
    embed.set_footer(text=f"🎀 頁面 {page}/{total_pages} | 💖 Iron Music Bot")
    await interaction.response.send_message(embed=embed)

@tree.command(name="nowplaying", description="顯示目前播放歌曲")
async def slash_nowplaying(interaction: discord.Interaction):
    player = get_player(interaction)
    if not player or not player.current:
        return await interaction.response.send_message(f"{EMOJI['now']} {_t_slash(interaction, 'no_playing')}", ephemeral=True)
    await interaction.response.send_message(embed=player.now_playing_embed())

@tree.command(name="volume", description="調整或查看音量")
@app_commands.describe(vol="音量 0-150（不填則顯示目前音量）")
async def slash_volume(interaction: discord.Interaction, vol: int = None):
    player = get_player(interaction)
    if not player:
        return await interaction.response.send_message(f"{EMOJI['volume']} 目前沒有播放器", ephemeral=True)
    if vol is None:
        return await interaction.response.send_message(f"{EMOJI['volume']} {_t_slash(interaction, 'volume_now', v=int(player.volume*100))}", ephemeral=True)
    if not 0 <= vol <= 150:
        return await interaction.response.send_message(f"{EMOJI['error']} 音量範圍為 0 ~ 150", ephemeral=True)
    async with player.volume_lock:
        player.volume = vol / 100
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = player.volume
    embed = anime_embed(
        title=f"{EMOJI['volume']} {_t_slash(interaction, 'volume_set')}",
        description=f"{_t_slash(interaction, 'volume', v=vol)}"
    )
    embed.add_field(name="🔊 音量條", value=f"`{'🟩' * (vol // 10)}{'⬜' * (15 - vol // 10)}`", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="seek", description="跳轉播放時間")
@app_commands.describe(seconds="目標秒數")
async def slash_seek(interaction: discord.Interaction, seconds: int):
    player = get_player(interaction)
    if not player or not player.current:
        return await interaction.response.send_message(f"{EMOJI['error']} {_t_slash(interaction, 'no_playing')}", ephemeral=True)
    if seconds < 0: seconds = 0
    if player.duration and seconds > player.duration: seconds = player.duration
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message(f"{EMOJI['error']} {_t_slash(interaction, 'not_playing')}", ephemeral=True)
    song = player.current
    player.duration = song.get("duration", 0)
    url = song.get("url") or song.get("webpage_url")
    if not player._manual_restart(url, seconds):
        return await interaction.response.send_message(f"{EMOJI['error']} 重新載入失敗", ephemeral=True)
    await interaction.response.send_message(f"{EMOJI['seek']} {_t_slash(interaction, 'seek_desc', t=format_time(seconds))}")

@tree.command(name="speed", description="調整播放倍速")
@app_commands.describe(rate="倍速：0.5 / 1 / 1.5 / 2")
async def slash_speed(interaction: discord.Interaction, rate: float):
    player = get_player(interaction)
    if not player or not player.current:
        return await interaction.response.send_message(f"{EMOJI['error']} {_t_slash(interaction, 'no_playing')}", ephemeral=True)
    if rate not in (0.5, 1.0, 1.5, 2.0):
        return await interaction.response.send_message(f"{EMOJI['error']} 倍速僅支援：0.5、1、1.5、2", ephemeral=True)
    ok = await player.set_speed(rate)
    await interaction.response.send_message(f"{EMOJI['speed']} {_t_slash(interaction, 'speed_set')}: **{rate}x**" + ("" if ok else "（無法重啟，下次生效）"))

@tree.command(name="shuffle", description="洗牌隊列")
async def slash_shuffle(interaction: discord.Interaction):
    player = get_player(interaction)
    if not player or not player.queue:
        return await interaction.response.send_message(f"{EMOJI['shuffle']} {_t_slash(interaction, 'queue_empty')}", ephemeral=True)
    import random
    songs = list(player.queue)
    random.shuffle(songs)
    player.queue = deque(songs)
    await interaction.response.send_message(f"{EMOJI['shuffle']} {_t_slash(interaction, 'shuffled')}")

@tree.command(name="clear", description="清空隊列")
async def slash_clear(interaction: discord.Interaction):
    player = get_player(interaction)
    if not player or not player.queue:
        return await interaction.response.send_message(f"{EMOJI['clear']} {_t_slash(interaction, 'queue_empty')}", ephemeral=True)
    player.queue.clear()
    await interaction.response.send_message(f"{EMOJI['clear']} {_t_slash(interaction, 'cleared')}")

@tree.command(name="lyrics", description="搜尋並顯示歌詞")
async def slash_lyrics(interaction: discord.Interaction):
    player = get_player(interaction)
    if not player or not player.current:
        return await interaction.response.send_message(f"{EMOJI['lyrics']} {_t_slash(interaction, 'no_playing')}", ephemeral=True)
    await interaction.response.defer()
    title = player.current["title"]
    artist = title.split(" - ")[0] if " - " in title else ""
    text, found_title, source = await search_lyrics(title, artist, interaction.guild_id)
    if not text:
        return await interaction.followup.send(f"{EMOJI['warn']} {_t_slash(interaction, 'no_result')}")
    embed = anime_embed(
        title=f"{EMOJI['lyrics']} 歌詞：{found_title}",
        description=text[:4000],
        color=discord.Color.from_rgb(255, 105, 180)
    )
    embed.set_footer(text=f"來源：{source}")
    await interaction.followup.send(embed=embed)

@tree.command(name="subtitles", description="導出字幕（或自動生成）")
@app_commands.describe(url="支援平台的網址（不填則用目前播放歌曲）", lang="語言代碼（如 zh-Hans, en）")
async def slash_subtitles(interaction: discord.Interaction, url: str = None, lang: str = None):
    player = get_player(interaction)
    if not url and player and player.current:
        url = player.current.get("url")
        title = player.current.get("title")
    if not url:
        return await interaction.response.send_message(f"{EMOJI['error']} 請提供支援平台的網址或先播放歌曲", ephemeral=True)
    await interaction.response.defer()
    info = None
    used_lang = lang
    srt = None
    try:
        info = await extract_subtitle_info(url)
        used_lang, best, subs, lang_missing = pick_subtitle(info, lang)
        if lang_missing:
            avail = sorted(subs.keys())
            avail_str = "`" + "` `".join(avail[:30]) + "`"
            if len(avail) > 30: avail_str += f"\n...等共 {len(avail)} 種語言"
            embed = anime_embed(title=f"{EMOJI['warn']} 找不到語言 `{used_lang}`", description=f"可用字幕語言：\n\n{avail_str}")
            embed.add_field(name="💡 用法", value="`/subtitles url:<網址> lang:<語言>`", inline=False)
            return await interaction.followup.send(embed=embed)
        if best: srt = await download_subtitle_text(best)
    except Exception: srt = None
    source = "原本字幕"
    if not (srt and srt.strip()):
        if not WHISPER_AVAILABLE:
            return await interaction.followup.send(f"{EMOJI['error']} 無字幕且未安裝 Whisper（`pip install faster-whisper`）")
        source = "Whisper 自動生成"
        await interaction.followup.send(f"{EMOJI['music']} 正在下載音訊並用 Whisper 生成字幕...")
        try:
            filepath = await asyncio.get_event_loop().run_in_executor(None, lambda: _download_audio_for_whisper(url))
            wlang = _whisper_lang_code(lang)
            srt = await asyncio.get_event_loop().run_in_executor(None, lambda: _whisper_generate_srt(filepath, wlang))
        except Exception as e:
            return await interaction.followup.send(f"{EMOJI['error']} 自動生成字幕失敗：{e}")
    if not srt or not srt.strip():
        return await interaction.followup.send(f"{EMOJI['warn']} 無法取得字幕")
    video_title = title or (info.get("title") if info else "video") or "video"
    preview = srt[:600]
    embed = anime_embed(title=f"{EMOJI['success']} 字幕完成", description=f"**[{video_title}]({url})**\n來源：`{source}`" + (f"\n語言：`{used_lang}`" if used_lang else ""))
    embed.add_field(name="📄 預覽", value=f"```\n{preview}\n```" + (f"\n*(僅顯示前 {len(preview)} 字元，完整字幕見附檔)*" if len(srt) > len(preview) else ""), inline=False)
    filename = f"subtitle_{int(asyncio.get_event_loop().time())}.srt"
    await interaction.followup.send(embed=embed, file=discord.File(BytesIO(srt.encode("utf-8")), filename=filename))

@tree.command(name="download", description="下載目前歌曲為 MP3")
@app_commands.describe(query="歌名或網址（不填則下載目前播放歌曲）")
async def slash_download(interaction: discord.Interaction, query: str = None):
    await interaction.response.defer()
    url = None
    title = None
    if query:
        url = query; title = query
        if not URL_REGEX.match(url): url = f"ytsearch1:{url}"
    else:
        player = get_player(interaction)
        if not player or not player.current:
            return await interaction.followup.send(f"{EMOJI['error']} 目前沒有播放，請先 `/play` 或提供查詢", ephemeral=True)
        url = player.current.get("url"); title = player.current.get("title")
    loop = asyncio.get_event_loop()
    try:
        dl = get_download_ytdl()
        result = await loop.run_in_executor(None, lambda: dl.extract_info(url, download=True))
        if "entries" in result and result.get("entries"): result = result["entries"][0]
        filepath = dl.prepare_filename(result)
        if not filepath.lower().endswith(".mp3"): filepath = os.path.splitext(filepath)[0] + ".mp3"
        if not os.path.exists(filepath): return await interaction.followup.send(f"{EMOJI['error']} 下載失敗：找不到檔案")
        size = os.path.getsize(filepath)
        if size > 8 * 1024 * 1024: return await interaction.followup.send(f"{EMOJI['warn']} 檔案太大（{size//1024//1024}MB > 8MB）")
        safe = re.sub(r'[\\/:*?"<>|]', "_", (result.get("title") or title or "audio"))[:80]
        await interaction.followup.send(file=discord.File(filepath, filename=f"{safe}.mp3"))
    except Exception as e:
        await interaction.followup.send(f"{EMOJI['error']} 下載失敗：{e}")

@tree.command(name="stats", description="顯示播放統計")
async def slash_stats(interaction: discord.Interaction):
    from core.settings import stats_data
    embed = anime_embed(title=f"{EMOJI['stats']} 播放統計")
    total_plays = sum(s.get("count", 0) for s in stats_data["plays"].values())
    embed.add_field(name="🎧 總播放次數", value=f"**{total_plays}**", inline=True)
    embed.add_field(name="⏱ 總播放時長", value=f"**{format_time(stats_data.get('total_seconds', 0))}**", inline=True)
    top = sorted(stats_data["plays"].values(), key=lambda s: s.get("count", 0), reverse=True)[:10]
    if top:
        embed.add_field(name="🏆 TOP 10", value="\n".join(f"`{i}.` **{s.get('title','?')}** ({s.get('count',0)} 次)" for i, s in enumerate(top, 1)), inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="language", description="設定伺服器語系")
@app_commands.describe(lang="zh-TW / zh-CN / en")
async def slash_language(interaction: discord.Interaction, lang: str = None):
    from core.settings import settings, save_settings, guild_lang
    from core.player_store import players
    if lang is None:
        return await interaction.response.send_message(f"{EMOJI['language']} 目前語言：**`{guild_lang(interaction.guild_id)}`**\n可用：`zh-TW`、`zh-CN`、`en`", ephemeral=True)
    LANG_MAP = {"zh-tw":"zh-TW","zh-cn":"zh-CN","tw":"zh-TW","cn":"zh-CN","繁體":"zh-TW","簡體":"zh-CN","简中":"zh-CN","繁中":"zh-TW","english":"en","英文":"en","en":"en"}
    target = LANG_MAP.get(lang.strip().lower())
    if not target:
        return await interaction.response.send_message(f"{EMOJI['error']} 不支援的語言：`{lang}`", ephemeral=True)
    settings.setdefault(str(interaction.guild_id), {})["lang"] = target
    save_settings()
    for p in players.values():
        if p.guild_id == interaction.guild_id: p.lang = target
    await interaction.response.send_message(f"{EMOJI['language']} 語言已設定為 **`{target}`**", ephemeral=True)

@tree.command(name="history", description="顯示播放歷史")
@app_commands.describe(index="編號（不填則列出）")
async def slash_history(interaction: discord.Interaction, index: int = None):
    player = get_player(interaction)
    if not player or not player.history:
        return await interaction.response.send_message(f"{EMOJI['history']} {_t_slash(interaction, 'history_empty')}", ephemeral=True)
    items = list(player.history)
    if index is None:
        embed = anime_embed(title=f"{EMOJI['history']} 播放歷史（最近 {len(items)} 首）")
        for i, song in enumerate(reversed(items), 1):
            embed.add_field(name=f"`{i}.` {song.get('title','')}", value=f"⏱ {format_time(song.get('duration',0))}", inline=False)
            if i >= 20: break
        embed.add_field(name="💡 用法", value=_t_slash(interaction, 'history_usage'), inline=False)
        return await interaction.response.send_message(embed=embed)
    if index < 1 or index > len(items):
        return await interaction.response.send_message(f"{EMOJI['error']} 無效編號（1 ~ {len(items)}）", ephemeral=True)
    song = dict(items[-index])
    if is_blacklisted(song):
        return await interaction.response.send_message(f"{EMOJI['error']} 歌曲已被封鎖", ephemeral=True)
    player.queue.append(song)
    await interaction.response.send_message(f"{EMOJI['success']} {_t_slash(interaction, 'add_queue')}: **[{song.get('title')}]({song.get('url')})**")

@tree.command(name="remove", description="移除隊列歌曲")
@app_commands.describe(index="隊列位置（從 1 開始）")
async def slash_remove(interaction: discord.Interaction, index: int):
    player = get_player(interaction)
    if not player or not player.queue:
        return await interaction.response.send_message(f"{EMOJI['error']} {_t_slash(interaction, 'queue_empty')}", ephemeral=True)
    if index < 1 or index > len(player.queue):
        return await interaction.response.send_message(f"{EMOJI['error']} 無效位置（1 ~ {len(player.queue)}）", ephemeral=True)
    songs = list(player.queue)
    song = songs.pop(index - 1)
    player.queue = deque(songs)
    await interaction.response.send_message(f"{EMOJI['success']} {_t_slash(interaction, 'removed')}: **[{song.get('title')}]({song.get('url')})**")

@tree.command(name="move", description="移動隊列歌曲")
@app_commands.describe(src="來源位置", dst="目標位置")
async def slash_move(interaction: discord.Interaction, src: int, dst: int):
    player = get_player(interaction)
    if not player or not player.queue:
        return await interaction.response.send_message(f"{EMOJI['error']} {_t_slash(interaction, 'queue_empty')}", ephemeral=True)
    n = len(player.queue)
    if src < 1 or src > n or dst < 1 or dst > n:
        return await interaction.response.send_message(f"{EMOJI['error']} 位置需在 1 ~ {n}", ephemeral=True)
    songs = list(player.queue)
    song = songs.pop(src - 1)
    songs.insert(dst - 1, song)
    player.queue = deque(songs)
    await interaction.response.send_message(f"{EMOJI['success']} {_t_slash(interaction, 'moved_desc', title=song.get('title',''), src=src, dst=dst)}")

# =========================
# SYNC
# =========================

async def setup_slash_commands():
    """在 on_ready 時呼叫同步指令樹（全域同步，所有伺服器生效，傳播需最多 1 小時）"""
    await tree.sync()
    print(f"[SLASH] 全域同步完成，共 {len(tree.get_commands())} 個斜線指令（傳播需最多 1 小時）")