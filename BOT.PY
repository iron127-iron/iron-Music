# =========================
# IRON MUSIC BOT - Main Entry Point
# =========================

import discord
import asyncio
from core import config, ytdlp, settings, helpers, stream, blacklist, lyrics, subtitles, player, ui, player_store, slash
import web_panel

# Command modules (register commands on bot)
from core.config import bot, FFMPEG_PATH

# =command modules (register commands on bot)
from commands import music, search, queue, control, lyrics as lyrics_cmd, subtitles as subtitles_cmd, download, stats, language, playback, general, blacklist as bl_cmd, management

# Wire up stream module with config values
stream.set_ffmpeg_executable(FFMPEG_PATH)
stream.set_url_regex(helpers.URL_REGEX)

# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    print(f"[OK] 機器人已上線：{bot.user}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name="聽音樂")
    )
    # 同步斜線指令
    await slash.setup_slash_commands()
    # 啟動網頁控制面板
    asyncio.create_task(web_panel.start_web_panel())

# =========================
# RUN
# =========================

if __name__ == "__main__":
    bot.run(config.TOKEN)