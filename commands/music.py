import discord
import threading
from core.config import bot, EMOJI
from core.ytdlp import get_ytdl, get_ytdl_pl
from core.helpers import extract_song, format_time, anime_embed, URL_REGEX
from core.blacklist import is_blacklisted
from core.player_store import get_player
from core.ui import SearchUI

# =========================
# PLAY
# =========================

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send(f"{EMOJI['error']} 請先加入語音頻道")

    vc = ctx.voice_client
    if not vc:
        try:
            vc = await ctx.author.voice.channel.connect(timeout=30)
        except discord.VoiceClientConnectionError:
            return await ctx.send(f"{EMOJI['error']} 無法連接到語音頻道（交握超時），請檢查防火牆或語音區域")
    elif vc.channel != ctx.author.voice.channel:
        await vc.move_to(ctx.author.voice.channel)

    player = get_player(ctx)
    player.voice = vc

    # Playlist
    if "playlist" in query.lower() or "list=" in query:
        msg = await ctx.send(f"{EMOJI['playlist']} 正在讀取播放列表...")

        def _load():
            try:
                data = get_ytdl_pl().extract_info(query, download=False, process=False)
            except Exception as e:
                return ("error", str(e))
            entries = data.get("entries") or []
            added = blocked = 0
            for e in entries:
                if not e:
                    continue
                if added + blocked >= 50:
                    break
                s = extract_song(e)
                if is_blacklisted(s):
                    blocked += 1
                    continue
                player.queue.append(s)
                added += 1
            return ("ok", added, blocked)

        def _thread_target():
            result = _load()
            async def _done():
                if result[0] == "error":
                    await msg.edit(content=f"{EMOJI['error']} 讀取播放列表失敗：{result[1]}")
                    return
                added, blocked = result[1], result[2]
                desc = f"🎶 已加入 **{added}** 首歌曲到隊列"
                if blocked:
                    desc += f"\n🚫 已封鎖 **{blocked}** 首黑名單歌曲"
                embed = anime_embed(
                    title=f"{EMOJI['playlist']} 已加入播放列表",
                    description=desc
                )
                await msg.edit(embed=embed)
            bot.loop.call_soon_threadsafe(lambda: bot.loop.create_task(_done()))

        threading.Thread(target=_thread_target, daemon=True).start()
        await msg.edit(content=f"{EMOJI['playlist']} 播放列表載入中，會自動開始播放...")
        return

    # Normal play
    msg = await ctx.send(f"{EMOJI['search']} 搜尋中...")
    if not URL_REGEX.match(query):
        query = f"ytsearch1:{query}"

    import asyncio
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: get_ytdl().extract_info(query, download=False))
    if "entries" in data:
        data = data["entries"][0]
    song = extract_song(data)

    blocked = is_blacklisted(song)
    if blocked:
        embed = anime_embed(
            title=f"{EMOJI['error']} 歌曲已被封鎖",
            description=f"**[{song['title']}]({song.get('url')})**\n\n命中黑名單項目：`{blocked}`"
        )
        return await msg.edit(embed=embed)

    player.queue.append(song)

    if vc.is_playing():
        embed = anime_embed(
            title=f"{EMOJI['success']} 已加入隊列",
            description=f"**[{song['title']}]({song.get('url')})**",
        )
        embed.add_field(name="⏱ 時長", value=format_time(song["duration"]), inline=True)
        embed.add_field(name="📜 位置", value=f"**{len(player.queue)}**", inline=True)
        embed.add_field(name="🎧 狀態", value=f"已加入隊列", inline=True)
        await msg.edit(embed=embed)
    else:
        await msg.delete()