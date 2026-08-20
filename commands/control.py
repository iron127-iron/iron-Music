import discord
from core.config import bot, EMOJI, FFMPEG_PATH
from core.player_store import get_player
from core.player import Player
from core.settings import _t, guild_lang
from core.helpers import format_time, anime_embed
from collections import deque

# =========================
# NOWPLAYING / VOLUME / SEEK / SPEED
# =========================

@bot.command()
async def nowplaying(ctx):
    player = get_player(ctx)
    if not player or not player.current:
        return await ctx.send(f"{EMOJI['now']} {_t(ctx.guild.id, 'no_playing')}")
    await ctx.send(embed=player.now_playing_embed())

@bot.command()
async def volume(ctx, vol: int = None):
    player = get_player(ctx)
    if not player:
        return await ctx.send(f"{EMOJI['volume']} 目前沒有播放器")

    if vol is None:
        return await ctx.send(f"{EMOJI['volume']} {_t(ctx.guild.id, 'volume_now', v=int(player.volume*100))}")

    if not 0 <= vol <= 150:
        return await ctx.send(f"{EMOJI['error']} 音量範圍為 0 ~ 150")

    async with player.volume_lock:
        player.volume = vol / 100
        vc = ctx.voice_client
        if vc and vc.source:
            vc.source.volume = player.volume

    embed = anime_embed(
        title=f"{EMOJI['volume']} {_t(ctx.guild.id, 'volume_set')}",
        description=f"{_t(ctx.guild.id, 'volume', v=vol)}"
    )
    embed.add_field(name="🔊 音量條", value=f"`{'🟩' * (vol // 10)}{'⬜' * (15 - vol // 10)}`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def seek(ctx, seconds: int = None):
    player = get_player(ctx)
    if not player or not player.current:
        return await ctx.send(f"{EMOJI['error']} {_t(ctx.guild.id, 'no_playing')}")

    if seconds is None:
        return await ctx.send(f"{EMOJI['seek']} 目前進度：{player.progress()}")

    if seconds < 0:
        seconds = 0
    if player.duration and seconds > player.duration:
        seconds = player.duration

    vc = ctx.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send(f"{EMOJI['error']} {_t(ctx.guild.id, 'not_playing')}")

    song = player.current
    player.duration = song.get("duration", 0)
    url = song.get("url") or song.get("webpage_url")
    if not player._manual_restart(url, seconds):
        return await ctx.send(f"{EMOJI['error']} 重新載入失敗")

    embed = anime_embed(
        title=f"{EMOJI['seek']} {_t(ctx.guild.id, 'seek_done')}",
        description=_t(ctx.guild.id, 'seek_desc', t=format_time(seconds))
    )
    await ctx.send(embed=embed)

@bot.command()
async def speed(ctx, rate: float = None):
    player = get_player(ctx)
    if not player or not player.current:
        return await ctx.send(f"{EMOJI['error']} {_t(ctx.guild.id, 'no_playing')}")

    if rate is None:
        return await ctx.send(
            f"{EMOJI['speed']} {_t(ctx.guild.id, 'speed_now', s=player.speed)}\n"
            "可用：`=speed 0.5`｜`1`｜`1.5`｜`2`"
        )

    if rate not in (0.5, 1.0, 1.5, 2.0):
        return await ctx.send(f"{EMOJI['error']} 倍速僅支援：`0.5`、`1`、`1.5`、`2`")

    ok = await player.set_speed(rate)

    embed = anime_embed(
        title=f"{EMOJI['speed']} {_t(ctx.guild.id, 'speed_set')}",
        description=f"倍速：**{rate}x**" + ("" if ok else "\n（無法重啟，已設為下次播放生效）")
    )
    await ctx.send(embed=embed)

# =========================
# SHUFFLE / CLEAR
# =========================

@bot.command()
async def shuffle(ctx):
    player = get_player(ctx)
    if not player or not player.queue:
        return await ctx.send(f"{EMOJI['shuffle']} {_t(ctx.guild.id, 'queue_empty')}")

    import random
    songs = list(player.queue)
    random.shuffle(songs)
    player.queue = deque(songs)

    embed = anime_embed(
        title=f"{EMOJI['shuffle']} {_t(ctx.guild.id, 'shuffled')}",
        description=_t(ctx.guild.id, 'queue_shuffled', n=len(songs))
    )
    await ctx.send(embed=embed)

@bot.command()
async def clear(ctx):
    player = get_player(ctx)
    if not player or not player.queue:
        return await ctx.send(f"{EMOJI['clear']} {_t(ctx.guild.id, 'queue_empty')}")

    player.queue.clear()

    embed = anime_embed(
        title=f"{EMOJI['clear']} {_t(ctx.guild.id, 'cleared')}",
        description=_t(ctx.guild.id, 'queue_cleared')
    )
    await ctx.send(embed=embed)