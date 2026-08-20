import discord
from core.config import bot, EMOJI
from core.helpers import anime_embed
from core.player_store import get_player
from core.settings import _t

# =========================
# SKIP / STOP / PAUSE / RESUME
# =========================

@bot.command()
async def skip(ctx):
    player = get_player(ctx)
    if not player or not player.current:
        return await ctx.send(f"{EMOJI['skip']} {_t(ctx.guild.id, 'not_playing')}")

    vc = ctx.voice_client
    if vc:
        player._manual_skip = True
        vc.stop()

    embed = anime_embed(
        title=f"{EMOJI['skip']} {_t(ctx.guild.id, 'skipped')}",
        description=f"**{player.current['title']}** 已被跳過"
    )
    await ctx.send(embed=embed)

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send(f"{EMOJI['pause']} 已暫停播放")
    else:
        await ctx.send(f"{EMOJI['warn']} 目前沒有在播放")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send(f"{EMOJI['resume']} 已繼續播放")
    else:
        await ctx.send(f"{EMOJI['warn']} 目前沒有暫停")

@bot.command()
async def stop(ctx):
    player = get_player(ctx)
    if player:
        player._stopped = True
        player._manual_skip = True
        player._kill_proc()
        player.next_event.set()

    if ctx.voice_client:
        await ctx.voice_client.disconnect()

    from core.player_store import players
    players.pop(ctx.guild.id, None)

    embed = anime_embed(
        title=f"{EMOJI['stop']} {_t(ctx.guild.id, 'stopped')}",
        description="機器人已離開語音頻道"
    )
    await ctx.send(embed=embed)