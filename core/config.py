import os
import discord
from discord.ext import commands

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("DISCORD_TOKEN", "MTUzOTE1NTAwODgxMTk2MjQ0MQ.GzRFGO.nDsIx5SBtU-8BfWA3DetulquqFzkA9U8eQVN30")
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
PREFIX = "="
TEST_GUILD_ID = 123456789012345678  # ← 替換成你的 Discord 伺服器 ID（右鍵伺服器 → 複製 ID）

# =========================
# CUTE ANIME THEME
# =========================

THEME = discord.Color.from_rgb(255, 105, 180)

EMOJI = {
    "play": "🎵",
    "pause": "⏸️",
    "resume": "▶️",
    "stop": "⏹️",
    "skip": "⏭️",
    "loop": "🔁",
    "queue": "📜",
    "now": "💿",
    "volume": "🔊",
    "shuffle": "🔀",
    "clear": "🧹",
    "search": "🔍",
    "lyrics": "📝",
    "seek": "⏩",
    "speed": "⏩",
    "playlist": "🎶",
    "error": "❌",
    "success": "✅",
    "warn": "⚠️",
    "clock": "🕒",
    "music": "🎧",
    "heart": "💖",
    "star": "✨",
    "sparkle": "🌸",
    "download": "⬇️",
    "history": "🕘",
    "stats": "📊",
    "language": "🌐",
}

# =========================
# BOT INIT
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)