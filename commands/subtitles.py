import discord
import re
import time
from core.config import bot, EMOJI
from core.helpers import anime_embed, format_time
from core.player_store import get_player
from core.settings import _t
from core.subtitles import (
    extract_subtitle_info, pick_subtitle, download_subtitle_text,
    _download_audio_for_whisper, _whisper_generate_srt, _whisper_lang_code,
    WHISPER_AVAILABLE
)
from io import BytesIO

# =========================
# SUBTITLES
# =========================

@bot.command(aliases=["captions", "字幕"])
async def subtitles(ctx, *, arg=None):
    player = get_player(ctx)
    url = None
    lang = None
    title = None

    if arg and "http" in arg:
        parts = arg.split()
        url = parts[0]
        if len(parts) > 1:
            lang = parts[1]
    else:
        lang = arg
        if player and player.current:
            url = player.current.get("url")
            title = player.current.get("title")

    if not url:
        embed = anime_embed(
            title=f"{EMOJI['error']} 無法導出字幕",
            description="目前沒有播放任何歌曲，請先 `=play` 播放再使用，或提供網址：`=subtitles <網址> [語言]`"
        )
        return await ctx.send(embed=embed)

    msg = await ctx.send(f"{EMOJI['search']} 正在擷取字幕...")

    info = None
    used_lang = lang
    srt = None
    try:
        info = await extract_subtitle_info(url)
        used_lang, best, subs, lang_missing = pick_subtitle(info, lang)
        if lang_missing:
            avail = sorted(subs.keys())
            avail_str = "`" + "` `".join(avail[:30]) + "`"
            if len(avail) > 30:
                avail_str += f"\n...等共 {len(avail)} 種語言"
            embed = anime_embed(
                title=f"{EMOJI['warn']} 找不到語言 `{used_lang}`",
                description=f"這部影片可用字幕語言：\n\n{avail_str}",
            )
            embed.add_field(name="💡 用法", value="`=subtitles <語言>`，例如：`=subtitles zh-Hans`", inline=False)
            return await msg.edit(content=None, embed=embed)
        if best:
            srt = await download_subtitle_text(best)
    except Exception:
        srt = None

    source = "原本字幕"

    if srt and srt.strip():
        pass
    elif not WHISPER_AVAILABLE:
        return await msg.edit(
            content=f"{EMOJI['error']} 這部影片沒有字幕，且未安裝 Whisper。請執行：`pip install faster-whisper`"
        )
    else:
        source = "Whisper 自動生成"
        await msg.edit(
            content=f"{EMOJI['music']} 影片沒有字幕，正在下載音訊並用 Whisper 生成字幕（首次會下載模型，可能需要數分鐘）..."
        )
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            filepath = await loop.run_in_executor(None, lambda: _download_audio_for_whisper(url))
            wlang = _whisper_lang_code(lang)
            srt = await loop.run_in_executor(None, lambda: _whisper_generate_srt(filepath, wlang))
        except Exception as e:
            return await msg.edit(content=f"{EMOJI['error']} 自動生成字幕失敗：{e}")

    if not srt or not srt.strip():
        return await msg.edit(content=f"{EMOJI['warn']} 無法取得字幕，且自動生成結果為空")

    video_title = title or (info.get("title") if info else "video") or "video"
    preview = srt[:600]

    embed = anime_embed(
        title=f"{EMOJI['success']} 字幕完成",
        description=f"**[{video_title}]({url})**\n\n來源：`{source}`"
        + (f"\n語言：`{used_lang}`" if used_lang else "")
    )
    embed.add_field(name="📄 預覽", value=f"```\n{preview}\n```\n" + (f"*(僅顯示前 {len(preview)} 字元，完整字幕請見附檔)*" if len(srt) > len(preview) else ""), inline=False)

    filename = f"subtitle_{int(time.time())}.srt"
    await msg.edit(content=None, embed=embed)
    await ctx.send(file=discord.File(BytesIO(srt.encode("utf-8")), filename=filename))