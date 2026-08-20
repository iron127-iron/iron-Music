import os
import sys
import subprocess
import tempfile
from datetime import datetime
from core.settings import SONG_TEMP_DIR

# =========================
# STREAM ARGS & RETRY CLIENTS
# =========================

STREAM_ARGS = [
    "--no-playlist", "--quiet", "--no-warnings",
    "-f", "bestaudio[ext=webm][protocol=https]/bestaudio[ext=opus][protocol=https]/bestaudio[protocol=https]/best",
    "--socket-timeout", "20",
    "--retries", "5",
    "--fragment-retries", "5",
    "--extractor-args", "youtube:player_client=tv,web,android",
    "--no-youtube-include-dash-manifest",
    "-o", "-",
]

RETRY_CLIENTS = [
    None,
    "tv",
    "web",
    "android",
]

FFMPEG = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 15 -reconnect_at_eof 1 -timeout 60 -user_agent \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\"",
    "executable": None,
}

URL_REGEX = None  # set from helpers

def set_ffmpeg_executable(path):
    FFMPEG["executable"] = path

def set_url_regex(regex):
    global URL_REGEX
    URL_REGEX = regex

# =========================
# SPAWN STREAM
# =========================

def spawn_stream(url, clients=None):
    stream_args = list(STREAM_ARGS)
    if clients:
        for i, a in enumerate(stream_args):
            if a == "--extractor-args":
                stream_args[i + 1] = f"youtube:player_client={clients}"
                break
    args = [sys.executable, "-m", "yt_dlp"] + stream_args + [url]
    log_path = os.path.join(SONG_TEMP_DIR, f"stream_{abs(hash(url)) % 100000}.log")
    diag_path = log_path + ".diag"
    logf = open(log_path, "wb")
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=logf,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        logf.write(f"[spawn error] {e!r}\n".encode("utf-8", "ignore"))
        logf.close()
        raise
    try:
        with open(diag_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] pid={proc.pid} cmd={' '.join(args)}\n")
    except Exception:
        pass
    proc._log_path = log_path
    proc._diag_path = diag_path
    proc._url = url
    return proc

def write_diag(proc, msg):
    try:
        with open(getattr(proc, "_diag_path", ""), "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] {msg}\n")
    except Exception:
        pass

def stream_error(proc):
    try:
        with open(getattr(proc, "_log_path", ""), "rb") as f:
            for line in reversed(f.read().decode("utf-8", "ignore").splitlines()):
                if line.strip():
                    return line.strip()[:200]
    except Exception:
        pass
    return "串流失敗"