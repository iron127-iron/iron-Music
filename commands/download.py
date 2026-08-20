import discord
import os
import re
from core.config import bot, EMOJI
from core.helpers import anime_embed, URL_REGEX
from core.player_store import get_player
from core.settings import _t
from core.ytdlp import get_download_ytdl
import asyncio

# =========================
# DOWNLOAD
# =========================

@bot.command()
async def download(ctx, *, query=None):
    url = None
    title = None

    if query:
        url = query
        title = query
        if not URL_REGEX.match(url):
            url = f"ytsearch1:{url}"
    else:
        player = get_player(ctx)
        if not player or not player.current:
            return await ctx.send(
                f"{EMOJI['error']} 目前沒有在播放，請先 `=play` 播放，或提供查詢：`=download <名稱/網址>`"
            )
        url = player.current.get("url")
        title = player.current.get("title")

    msg = await ctx.send(f"{EMOJI['download']} 正在下載...")
    loop = asyncio.get_event_loop()

    try:
        dl = get_download_ytdl()
        result = await loop.run_in_executor(None, lambda: dl.extract_info(url, download=True))
        if "entries" in result and result.get("entries"):
            result = result["entries"][0]
        filepath = dl.prepare_filename(result)
        if not filepath.lower().endswith(".mp3"):
            filepath = os.path.splitext(filepath)[0] + ".mp3"
        if not os.path.exists(filepath):
            return await msg.edit(content=f"{EMOJI['error']} 下載失敗：找不到產出的檔案")

        size = os.path.getsize(filepath)
        if size > 8 * 1024 * 1024:
            return await msg.edit(
                content=f"{EMOJI['warn']} 檔案太大（{size // 1024 // 1024}MB > 8MB），無法上傳到 Discord"
            )

        safe = re.sub(r'[\\/:*?"<>|]', "_", (result.get("title") or title or "audio"))[:80]
        filename = f"{safe}.mp3"
        await msg.delete()
        await ctx.send(file=discord.File(filepath, filename=filename))
    except Exception as e:
        await msg.edit(content=f"{EMOJI['error']} 下載失敗：{e}")