import discord
from core.config import bot, EMOJI
from core.helpers import anime_embed
from core.player_store import get_player
from core.lyrics import search_lyrics
from core.settings import _t

# =========================
# LYRICS
# =========================

@bot.command()
async def lyrics(ctx):
    player = get_player(ctx)
    if not player or not player.current:
        return await ctx.send(f"{EMOJI['lyrics']} {_t(ctx.guild.id, 'no_playing')}")

    title = player.current["title"]
    artist = title.split(" - ")[0] if " - " in title else ""

    msg = await ctx.send(f"{EMOJI['search']} 正在上網搜尋歌詞...")
    text, found_title, source = await search_lyrics(title, artist, ctx.guild.id)

    if not text:
        return await msg.edit(content=f"{EMOJI['warn']} {_t(ctx.guild.id, 'no_result')}")

    embed = anime_embed(
        title=f"{EMOJI['lyrics']} 歌詞：{found_title}",
        description=text[:4000],
        color=discord.Color.from_rgb(255, 105, 180)
    )
    embed.set_footer(text=f"來源：{source}")
    await msg.edit(content=None, embed=embed)