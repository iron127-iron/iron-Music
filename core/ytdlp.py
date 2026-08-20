import os
import yt_dlp
from core.config import FFMPEG_PATH

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cookies.txt")
if not os.path.exists(COOKIES_FILE):
    COOKIES_FILE = None

SUB_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# =========================
# YTDLP CONFIGS (lazy init)
# =========================

_base_opts = None
_ytdl = _ytdl_pl = _subtitle_ytdl = _subtitle_dl = _download_ytdl = None

def _get_base_opts():
    global _base_opts
    if _base_opts is None:
        _base_opts = {
            "quiet": True,
            "compat_opts": ["no-youtube-unavailable-formats"],
            "socket_timeout": 20,
            "retries": 5,
            "extractor_retries": 5,
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "web", "android"],
                }
            },
            "youtube_include_dash_manifest": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }
        if COOKIES_FILE:
            _base_opts["cookiefile"] = COOKIES_FILE
    return _base_opts

def get_ytdl():
    global _ytdl
    if _ytdl is None:
        _ytdl = yt_dlp.YoutubeDL({
            **_get_base_opts(),
            "format": "bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best",
            "noplaylist": True,
            "default_search": "ytsearch1",
        })
    return _ytdl

def get_ytdl_pl():
    global _ytdl_pl
    if _ytdl_pl is None:
        _ytdl_pl = yt_dlp.YoutubeDL({
            **_get_base_opts(),
            "noplaylist": False,
            "playlistend": 50,
        })
    return _ytdl_pl

def get_subtitle_ytdl():
    global _subtitle_ytdl
    if _subtitle_ytdl is None:
        _subtitle_ytdl = yt_dlp.YoutubeDL({
            **_get_base_opts(),
            "noplaylist": True,
            "skip_download": True,
        })
    return _subtitle_ytdl

def get_subtitle_dl():
    global _subtitle_dl
    if _subtitle_dl is None:
        _subtitle_dl = yt_dlp.YoutubeDL({
            **_get_base_opts(),
            "format": "bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best",
            "noplaylist": True,
            "outtmpl": None,
            "ffmpeg_location": os.path.dirname(FFMPEG_PATH),
        })
    return _subtitle_dl

def get_download_ytdl():
    global _download_ytdl
    if _download_ytdl is None:
        DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "temp", "iron_music_downloads")
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        _download_ytdl = yt_dlp.YoutubeDL({
            **_get_base_opts(),
            "format": "bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best",
            "noplaylist": True,
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "ffmpeg_location": os.path.dirname(FFMPEG_PATH),
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}],
        })
    return _download_ytdl

# Backwards compat (deprecated, use get_* functions)
ytdl = property(lambda self: get_ytdl())
ytdl_pl = property(lambda self: get_ytdl_pl())
SUBTITLE_YTDL = property(lambda self: get_subtitle_ytdl())
SUBTITLE_DL = property(lambda self: get_subtitle_dl())
DOWNLOAD_YTDL = property(lambda self: get_download_ytdl())