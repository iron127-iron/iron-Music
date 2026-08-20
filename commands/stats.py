import discord
from core.config import bot, EMOJI
from core.helpers import anime_embed, format_time
from core.settings import stats_data
from core.settings import _t

# =========================
# STATS
# =========================

@bot.command()
async def stats(ctx):
    embed = anime_embed(
        title=f"{EMOJI['stats']} 播放統計"
    )
    total_plays = sum(s.get("count", 0) for s in stats_data["plays"].values())
    embed.add_field(name="🎧 總播放次數", value=f"**{total_plays}**", inline=True)
    embed.add_field(name="⏱ 總播放時長", value=f"**{format_time(stats_data.get('total_seconds', 0))}**", inline=True)
    top = sorted(stats_data["plays"].values(), key=lambda s: s.get("count", 0), reverse=True)[:10]
    if top:
        lines = [f"`{i}.` **{s.get('title', '?')}**（{s.get('count', 0)} 次）" for i, s in enumerate(top, 1)]
        embed.add_field(name="🏆 最常播放 TOP 10", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="🏆 最常播放 TOP 10", value="尚無播放紀錄", inline=False)
    await ctx.send(embed=embed)