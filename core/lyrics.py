import asyncio
import json
import re
import html
from urllib.request import urlopen, Request
from urllib.parse import quote
from core.settings import _t

LYRICS_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"}

def _http_get(url, timeout=15):
    req = Request(url, headers=LYRICS_UA)
    return urlopen(req, timeout=timeout).read()

def _extract_genius_lyrics(html_text):
    parts = re.findall(r'<div data-lyrics-container="true"[^>]*>(.*?)</div>', html_text, re.S)
    if not parts:
        return None
    text = "\n".join(parts)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text or None

def _parse_title(title):
    m = re.search(r"【([^】]+)】", title)
    if m:
        return title[:m.start()].strip(" -"), m.group(1).strip()
    if " - " in title:
        artist, song = title.split(" - ", 1)
        return artist.strip(), song.strip()
    return "", title

def _clean_song(song):
    s = re.sub(r"[（(][^）)]*[）)]", " ", song)
    s = re.sub(r"(Official|Live|MV|Music Video|Lyrics|Lyric Video|Video|Remaster|HD|4K|現場版|Album|專輯)", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -")
    return s or song

def _netease_lrc_to_text(lrc):
    lines = []
    for line in lrc.splitlines():
        text = re.sub(r"\[[^\]]*\]", "", line).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)

async def search_lyrics(title, artist="", guild_id=None):
    loop = asyncio.get_event_loop()
    query = f"{artist} {title}".strip() or title

    # 1) Genius
    try:
        data = await loop.run_in_executor(
            None, lambda: json.loads(_http_get(f"https://genius.com/api/search/multi?q={quote(query)}")))
        for section in data.get("response", {}).get("sections", []):
            if section.get("type") != "song":
                continue
            for hit in section.get("hits", []):
                result = hit.get("result") or {}
                page_url = result.get("url")
                if not page_url:
                    continue
                html_text = await loop.run_in_executor(
                    None, lambda: _http_get(page_url).decode("utf-8", "ignore"))
                text = _extract_genius_lyrics(html_text)
                if text:
                    return text, result.get("full_title") or result.get("title") or title, page_url
    except Exception:
        pass

    # 2) NetEase
    try:
        _, song = _parse_title(title)
        song_clean = _clean_song(song)
        cjk = "".join(re.findall(r"[\u4e00-\u9fff]+", song_clean))
        variants = []
        if artist:
            variants.append(f"{song_clean} {artist}")
        if song_clean:
            variants.append(song_clean)
        if cjk and cjk != song_clean:
            variants.append(cjk)
        if query not in variants:
            variants.append(query)

        best = None
        for q in variants:
            try:
                data = await loop.run_in_executor(None, lambda: json.loads(_http_get(
                    f"https://music.163.com/api/search/get?s={quote(q)}&type=1&limit=5", timeout=10)))
            except Exception:
                continue
            for s in (data.get("result") or {}).get("songs") or []:
                name = s.get("name") or ""
                score = 0
                sl = song_clean.lower()
                nl = name.lower()
                if sl and nl == sl:
                    score = 4
                elif sl and sl in nl:
                    score = 3
                elif cjk and name == cjk:
                    score = 3
                elif cjk and cjk in name:
                    score = 2
                elif sl and len(name) >= 2 and nl in sl:
                    score = 1
                if score and (best is None or score > best[0]):
                    best = (score, s)
        if best:
            s = best[1]
            sid = s.get("id")
            if sid:
                lyric = await loop.run_in_executor(None, lambda: json.loads(_http_get(
                    f"https://music.163.com/api/song/lyric?id={sid}&lv=1&kv=1&tv=-1", timeout=10)))
                lrc = ((lyric or {}).get("lrc") or {}).get("lyric") or ""
                text = _netease_lrc_to_text(lrc)
                if text:
                    aname = "".join(a.get("name") or "" for a in (s.get("artists") or [])[:2])
                    return text, f"{aname} - {s.get('name', '')}".strip(" -"), "網易雲音樂"
    except Exception:
        pass

    # 3) lyrics.ovh
    try:
        if artist:
            data = await loop.run_in_executor(
                None, lambda: json.loads(_http_get(
                    f"https://api.lyrics.ovh/v1/{quote(artist)}/{quote(title)}", timeout=8)))
            text = (data or {}).get("lyrics")
            if text and text.strip():
                return text.strip(), title, "lyrics.ovh"
    except Exception:
        pass

    return None, None, None