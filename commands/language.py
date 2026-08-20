import discord
from core.config import bot, EMOJI
from core.helpers import anime_embed
from core.settings import settings, save_settings, guild_lang
from core.player_store import players

# =========================
# LANGUAGE
# =========================

LANG_MAP = {
    "zh-tw": "zh-TW", "zh-cn": "zh-CN", "tw": "zh-TW", "cn": "zh-CN",
    "繁體": "zh-TW", "簡體": "zh-CN", "简中": "zh-CN", "繁中": "zh-TW",
    "english": "en", "英文": "en", "en": "en",
}

@bot.command(aliases=["lang"])
async def language(ctx, lang=None):
    if lang is None:
        return await ctx.send(
            f"{EMOJI['language']} 目前語言：**`{guild_lang(ctx.guild.id)}`**\n可用：`zh-TW`、`zh-CN`、`en`"
        )

    target = LANG_MAP.get(lang.strip().lower())
    if not target:
        return await ctx.send(
            f"{EMOJI['error']} 不支援的語言：`{lang}`（可用：`zh-TW`、`zh-CN`、`en`）"
        )

    settings.setdefault(str(ctx.guild.id), {})["lang"] = target
    save_settings()
    
    for p in players.values():
        if p.guild_id == ctx.guild.id:
            p.lang = target

    embed = anime_embed(
        title=f"{EMOJI['language']} 語言已設定",
        description=f"已切換為 **`{target}`**"
    )
    await ctx.send(embed=embed)