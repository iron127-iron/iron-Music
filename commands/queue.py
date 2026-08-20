import discord
from core.config import bot, EMOJI
from core.helpers import format_time, anime_embed
from core.player_store import get_player
from core.settings import _t, record_play
from core.blacklist import is_blacklisted
from collections import deque

# =========================
# QUEUE / REMOVE / MOVE / HISTORY
# =========================

@bot.command()
async def queue(ctx, page: int = 1):
    player = get_player(ctx)
    if not player or not player.queue:
        return await ctx.send(f"{EMOJI['queue']} {_t(ctx.guild.id, 'queue_empty')}")

    songs = list(player.queue)
    per_page = 10
    total_pages = max(1, (len(songs) + per_page - 1) // per_page)

    if page < 1 or page > total_pages:
        return await ctx.send(f"{EMOJI['error']} 頁面範圍為 1 ~ {total_pages}")

    start = (page - 1) * per_page
    end = start + per_page

    embed = anime_embed(
        title=f"{EMOJI['queue']} 播放隊列",
        description=f"總共 **{len(songs)}** 首歌曲"
    )

    for i, song in enumerate(songs[start:end], start=start+1):
        duration = format_time(song.get("duration", 0))
        embed.add_field(
            name=f"`{i}.` {song['title']}",
            value=f"⏱ {duration}",
            inline=False
        )

    embed.set_footer(text=f"🎀 頁面 {page}/{total_pages} | 💖 Iron Music Bot")
    await ctx.send(embed=embed)

@bot.command()
async def remove(ctx, index: int):
    player = get_player(ctx)
    if not player or not player.queue:
        return await ctx.send(f"{EMOJI['error']} {_t(ctx.guild.id, 'queue_empty')}")

    if index < 1 or index > len(player.queue):
        return await ctx.send(f"{EMOJI['error']} 無效位置（1 ~ {len(player.queue)}）")

    songs = list(player.queue)
    song = songs.pop(index - 1)
    player.queue = deque(songs)

    embed = anime_embed(
        title=f"{EMOJI['success']} {_t(ctx.guild.id, 'removed')}",
        description=f"**[{song.get('title')}]({song.get('url')})**",
    )
    embed.add_field(name=f"📜 {_t(ctx.guild.id, 'remaining')}", value=f"{len(player.queue)} 首", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def move(ctx, src: int, dst: int):
    player = get_player(ctx)
    if not player or not player.queue:
        return await ctx.send(f"{EMOJI['error']} {_t(ctx.guild.id, 'queue_empty')}")

    n = len(player.queue)
    if src < 1 or src > n:
        return await ctx.send(f"{EMOJI['error']} 無效來源位置（1 ~ {n}）")
    if dst < 1 or dst > n:
        return await ctx.send(f"{EMOJI['error']} 無效目標位置（1 ~ {n}）")

    songs = list(player.queue)
    song = songs.pop(src - 1)
    songs.insert(dst - 1, song)
    player.queue = deque(songs)

    embed = anime_embed(
        title=f"{EMOJI['success']} {_t(ctx.guild.id, 'moved')}",
        description=_t(ctx.guild.id, 'moved_desc', title=song.get('title', ''), src=src, dst=dst)
    )
    await ctx.send(embed=embed)

@bot.command()
async def history(ctx, index: int = None):
    player = get_player(ctx)
    if not player or not player.history:
        return await ctx.send(f"{EMOJI['history']} {_t(ctx.guild.id, 'history_empty')}")

    items = list(player.history)

    if index is None:
        embed = anime_embed(
            title=f"{EMOJI['history']} 播放歷史（最近 {len(items)} 首）"
        )
        for i, song in enumerate(reversed(items), 1):
            embed.add_field(
                name=f"`{i}.` {song.get('title', '')}",
                value=f"⏱ {format_time(song.get('duration', 0))}",
                inline=False
            )
            if i >= 20:
                break
        embed.add_field(name="💡 用法", value=_t(ctx.guild.id, 'history_usage'), inline=False)
        return await ctx.send(embed=embed)

    if index < 1 or index > len(items):
        return await ctx.send(f"{EMOJI['error']} 無效編號（1 ~ {len(items)}）")

    song = dict(items[-index])

    if is_blacklisted(song):
        return await ctx.send(f"{EMOJI['error']} 歌曲已被封鎖（`{blocked}`）")

    player.queue.append(song)
    embed = anime_embed(
        title=f"{EMOJI['success']} {_t(ctx.guild.id, 'add_queue')}",
        description=f"**[{song.get('title')}]({song.get('url')})**",
    )
    embed.add_field(name=f"📜 {_t(ctx.guild.id, 'position')}", value=f"**{len(player.queue)}**", inline=True)
    await ctx.send(embed=embed)