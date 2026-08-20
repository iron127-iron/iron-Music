import asyncio
import json
import re
import os
import tempfile
from urllib.request import urlopen, Request
from core.settings import WHISPER_TEMP_DIR
from core.ytdlp import SUB_UA, get_subtitle_ytdl, get_subtitle_dl

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

WHISPER_MODEL_SIZE = "small"
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model

def fmt_srt_time(seconds):
    seconds = max(0, int(seconds * 1000))
    ms = seconds % 1000
    s = (seconds // 1000) % 60
    m = (seconds // 60000) % 60
    h = seconds // 3600000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def json3_to_srt(data):
    lines = []
    idx = 1
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(seg.get("utf8", "") for seg in segs).strip()
        if not text:
            continue
        t0 = ev.get("tStartMs", 0) / 1000
        t1 = t0 + ev.get("dDurationMs", 0) / 1000
        lines.append(f"{idx}\n{fmt_srt_time(t0)} --> {fmt_srt_time(t1)}\n{text}\n")
        idx += 1
    return "\n".join(lines)

def vtt_to_srt(vtt):
    out = []
    idx = 0
    for raw in vtt.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        m = re.match(r"((?:\d{2}:)?\d{2}:\d{2}\.\d{3}) --> ((?:\d{2}:)?\d{2}:\d{2}\.\d{3})", line)
        if m:
            idx += 1
            out.append(f"{idx}\n{m.group(1)} --> {m.group(2)}\n")
            continue
        out.append(line + "\n")
    return "\n".join(out).strip()

async def extract_subtitle_info(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: get_subtitle_ytdl().extract_info(url, download=False))

def pick_subtitle(info, lang):
    subs = {}
    for key, val in (info.get("subtitles") or {}).items():
        subs[key] = val
    for key, val in (info.get("automatic_captions") or {}).items():
        subs.setdefault(key, val)

    if not subs:
        return None, None, None, False

    if lang:
        lang = lang.replace("_", "-")
    else:
        for candidate in ("zh-Hans", "zh-CN", "zh-Hant", "zh-TW", "zh", "en"):
            if candidate in subs:
                lang = candidate
                break
        else:
            lang = next(iter(subs))

    if lang not in subs:
        return lang, None, subs, True

    formats = subs[lang] or []
    if not formats:
        return None, None, None, False

    priority = {"json3": 0, "srv3": 0, "vtt": 1, "srt": 2, "vtt_srt": 2}
    best = min(formats, key=lambda f: priority.get(f.get("ext"), 9))
    return lang, best, subs, False

async def download_subtitle_text(entry):
    req = Request(entry["url"], headers=SUB_UA)
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, lambda: urlopen(req, timeout=20).read())
    text = raw.decode("utf-8", errors="replace")
    ext = entry.get("ext", "vtt")
    if ext == "json3":
        return json3_to_srt(json.loads(text))
    if ext == "vtt":
        return vtt_to_srt(text)
    return text

def _download_audio_for_whisper(url):
    dl = get_subtitle_dl()
    info = dl.extract_info(url, download=True)
    if "entries" in info and info.get("entries"):
        info = info["entries"][0]
    return dl.prepare_filename(info)

def _whisper_generate_srt(filepath, lang):
    model = get_whisper_model()
    segments, _ = model.transcribe(filepath, language=lang, vad_filter=False)
    lines = []
    idx = 1
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        lines.append(f"{idx}\n{fmt_srt_time(seg.start)} --> {fmt_srt_time(seg.end)}\n{text}\n")
        idx += 1
    return "\n".join(lines)

def _whisper_lang_code(lang):
    if not lang:
        return None
    mapping = {
        "zh-hans": "zh", "zh-cn": "zh", "zh-hant": "zh", "zh-tw": "zh", "zh": "zh",
    }
    return mapping.get(lang.lower(), lang.lower())