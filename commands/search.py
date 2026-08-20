import discord
from core.config import bot, EMOJI
from core.helpers import format_time, anime_embed, URL_REGEX
from core.player_store import get_player
from core.settings import _t, guild_lang
from core.ytdlp import get_ytdl
from core.lyrics import search_lyrics
from core.subtitles import (
    extract_subtitle_info, pick_subtitle, download_subtitle_text,
    _download_audio_for_whisper, _whisper_generate_srt, _whisper_lang_code,
    WHISPER_AVAILABLE
)
from core.helpers import extract_song
from core.blacklist import is_blacklisted
from core.ui import SearchUI
import re
import os
import time
import asyncio
from io import BytesIO

# =========================
# SEARCH
# =========================

@bot.command()
async def search(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send(f"{EMOJI['error']} 請先加入語音頻道")

    msg = await ctx.send(f"{EMOJI['search']} 搜尋中...")

    import asyncio
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: get_ytdl().extract_info(f"ytsearch5:{query}", download=False))

    if "entries" not in data:
        return await msg.edit(content=f"{EMOJI['error']} 找不到結果")

    entries = data["entries"][:5]

    embed = anime_embed(
        title=f"{EMOJI['search']} 搜尋結果",
        description=f"請選擇要播放的歌曲："
    )

    for i, e in enumerate(entries, 1):
        duration = format_time(e.get("duration", 0))
        embed.add_field(
            name=f"**{i}.** {e['title']}",
            value=f"⏱ {duration}",
            inline=False
        )

    player = get_player(ctx)
    await msg.edit(embed=embed, view=SearchUI(entries, ctx, player))