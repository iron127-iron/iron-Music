import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
USER_BLACKLIST_FILE = os.path.join(BASE_DIR, "user_blacklist.json")
BLACKLIST_ADMIN_ID = 1299949671090749462

def load_blacklist():
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_blacklist(items):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

blacklist = load_blacklist()

def is_blacklisted(song):
    title = (song.get("title") or "").lower()
    url = (song.get("url") or "").lower()
    vid = (song.get("id") or "").lower()
    for item in blacklist:
        item = item.lower().strip()
        if not item:
            continue
        if item in url or item in title or item == vid:
            return item
    return None

def load_user_blacklist():
    try:
        with open(USER_BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_user_blacklist(items):
    with open(USER_BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

user_blacklist = load_user_blacklist()