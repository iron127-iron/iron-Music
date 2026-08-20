import os
import json
import tempfile
from datetime import datetime

# =========================
# SETTINGS / LANGUAGE
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
STATS_FILE = os.path.join(BASE_DIR, "stats.json")

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

settings = load_settings()

def guild_lang(guild_id):
    return settings.get(str(guild_id), {}).get("lang", "zh-TW")

LANG = {
    "zh-TW": {
        "now_playing": "現在播放", "progress": "進度", "status": "狀態",
        "loop_on": "🔁 循環：開啟", "loop_off": "🔁 循環：關閉",
        "volume": "🔊 音量：{v}%", "speed": "⏩ 倍速：{s}x",
        "queue_count": "📜 隊列：{n} 首",
        "add_queue": "已加入隊列", "position": "位置", "duration": "時長",
        "queue_empty": "目前隊列是空的", "no_playing": "目前沒有在播放任何歌曲",
        "not_playing": "目前沒有在播放",
        "skipped": "已跳過", "stopped": "已停止播放",
        "shuffled": "已洗牌", "queue_shuffled": "隊列已隨機重新排列！共 {n} 首",
        "cleared": "已清空隊列", "queue_cleared": "所有待播放的歌曲已被移除",
        "volume_now": "目前音量：{v}%", "volume_set": "音量已調整",
        "seek_done": "已跳轉", "seek_desc": "已跳轉到 {t}",
        "speed_set": "已調整倍速",
        "removed": "已從隊列移除", "remaining": "剩餘",
        "moved": "已移動", "moved_desc": "{title} 已從 `{src}` 移到 `{dst}`",
        "history_empty": "目前沒有播放紀錄",
        "history_usage": "`=history <編號>` 可再次加入隊列",
        "no_result": "找不到歌詞，請嘗試其他歌曲",
    },
    "zh-CN": {
        "now_playing": "正在播放", "progress": "进度", "status": "状态",
        "loop_on": "🔁 循环：开启", "loop_off": "🔁 循环：关闭",
        "volume": "🔊 音量：{v}%", "speed": "⏩ 倍速：{s}x",
        "queue_count": "📜 队列：{n} 首",
        "add_queue": "已加入队列", "position": "位置", "duration": "时长",
        "queue_empty": "当前队列是空的", "no_playing": "当前没有在播放任何歌曲",
        "not_playing": "当前没有在播放",
        "skipped": "已跳过", "stopped": "已停止播放",
        "shuffled": "已洗牌", "queue_shuffled": "队列已随机重新排列！共 {n} 首",
        "cleared": "已清空队列", "queue_cleared": "所有待播放的歌曲已被移除",
        "volume_now": "当前音量：{v}%", "volume_set": "音量已调整",
        "seek_done": "已跳转", "seek_desc": "已跳转到 {t}",
        "speed_set": "已调整倍速",
        "removed": "已从队列移除", "remaining": "剩余",
        "moved": "已移动", "moved_desc": "{title} 已从 `{src}` 移到 `{dst}`",
        "history_empty": "当前没有播放记录",
        "history_usage": "`=history <编号>` 可再次加入队列",
        "no_result": "找不到歌词，请尝试其他歌曲",
    },
    "en": {
        "now_playing": "Now Playing", "progress": "Progress", "status": "Status",
        "loop_on": "🔁 Loop: On", "loop_off": "🔁 Loop: Off",
        "volume": "🔊 Volume: {v}%", "speed": "⏩ Speed: {s}x",
        "queue_count": "📜 Queue: {n} songs",
        "add_queue": "Added to queue", "position": "Position", "duration": "Duration",
        "queue_empty": "The queue is empty", "no_playing": "Nothing is currently playing",
        "not_playing": "Nothing is currently playing",
        "skipped": "Skipped", "stopped": "Stopped playing",
        "shuffled": "Shuffled", "queue_shuffled": "Queue shuffled! {n} songs in total",
        "cleared": "Queue cleared", "queue_cleared": "All queued songs have been removed",
        "volume_now": "Current volume: {v}%", "volume_set": "Volume updated",
        "seek_done": "Seeked", "seek_desc": "Seeked to {t}",
        "speed_set": "Speed updated",
        "removed": "Removed from queue", "remaining": "Remaining",
        "moved": "Moved", "moved_desc": "{title} moved from `{src}` to `{dst}`",
        "history_empty": "No play history yet",
        "history_usage": "`=history <number>` to re-add to queue",
        "no_result": "No lyrics found, try another song",
    },
}

def _t_lang(lang, key, **kw):
    text = LANG.get(lang, {}).get(key) or LANG["zh-TW"].get(key, key)
    if kw:
        try:
            text = text.format(**kw)
        except Exception:
            pass
    return text

def _t(guild_id, key, **kw):
    return _t_lang(guild_lang(guild_id), key, **kw)

# =========================
# STATS
# =========================

def load_stats():
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "plays" in data:
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {"plays": {}, "total_seconds": 0.0}

def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

stats_data = load_stats()

def record_play(song, duration):
    key = song.get("url") or song.get("id") or song.get("title") or "?"
    entry = stats_data["plays"].setdefault(key, {"title": "", "url": "", "count": 0})
    entry["title"] = song.get("title", entry.get("title", ""))
    entry["url"] = song.get("url", entry.get("url", ""))
    entry["count"] = entry.get("count", 0) + 1
    stats_data["total_seconds"] = stats_data.get("total_seconds", 0.0) + float(duration or 0)
    save_stats()

# =========================
# TEMP DIRS
# =========================

SONG_TEMP_DIR = os.path.join(tempfile.gettempdir(), "iron_music_songs")
os.makedirs(SONG_TEMP_DIR, exist_ok=True)

WHISPER_TEMP_DIR = os.path.join(tempfile.gettempdir(), "iron_music_subs")
os.makedirs(WHISPER_TEMP_DIR, exist_ok=True)