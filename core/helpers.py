import discord
import time
import re
from core.config import THEME, EMOJI

URL_REGEX = re.compile(r"https?://.+")

def format_time(seconds):
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def progress_bar(now, duration, length=20):
    if not duration:
        return "🔴 `[直播中]`"
    percent = min(now / duration, 1)
    filled = int(length * percent)
    bar = "🟩" * filled + "⬜" * (length - filled)
    return f"`{bar}` `{format_time(now)} / {format_time(duration)}`"

def anime_embed(title, description=None, color=THEME, **kwargs):
    embed = discord.Embed(title=title, description=description, color=color, **kwargs)
    embed.set_footer(text="🎀 Iron Music Bot 💖")
    return embed

def extract_song(data):
    """從 yt-dlp 資料中抽取歌曲資訊"""
    return {
        "title": data.get("title", "未知標題"),
        "stream": data.get("url", ""),
        "url": data.get("webpage_url") or data.get("url"),
        "duration": data.get("duration", 0),
        "id": data.get("id", "")
    }