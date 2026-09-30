"""COACHING CHANGES (the owner, 9/30: "you need to get all the data"): every in-season firing / interim coach, with
dates, from Wikipedia's season pages ("2023-24 NBA season" -> Coaching changes) through Wikipedia's own public API
(no key, a plain User-Agent that says who we are - Wikipedia's rule). ESPN only lists one coach per season.
Runs in GitHub Actions (coaches.yml - this sandbox can't reach it). Saves the raw sections to
data/sports/coach_changes_raw.json; sports_coach_changes.parse() turns them into firings."""
import json
import os
import re
import time
import urllib.parse
import urllib.request

import sports_data as sd

RAW = os.path.join(sd.DATA, "coach_changes_raw.json")
API = "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&redirects=1&page={page}"
UA = "D503-sports-engine/1.0 (https://github.com/D503therapper/autonomous-crypto-engine; coaching study)"


def pages(season):
    """Wikipedia page titles for a season (the year it starts)."""
    nxt = str(season + 1)[2:]
    return {"nfl": f"{season} NFL season", "nba": f"{season}–{nxt} NBA season", "nhl": f"{season}–{nxt} NHL season",
            "mlb": f"{season} Major League Baseball season", "ncaaf": f"{season} NCAA Division I FBS football season",
            "ncaab": f"{season}–{nxt} NCAA Division I men's basketball season"}


def fetch(page):
    req = urllib.request.Request(API.format(page=urllib.parse.quote(page)), headers={"User-Agent": UA})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return ((json.load(r).get("parse") or {}).get("wikitext") or {}).get("*") or ""
        except Exception as e:                               # noqa: BLE001
            if i == 2:
                print(f"   {page}: {str(e)[:80]}")
                return ""
            time.sleep(2)


def coaching_sections(text):
    """The wikitext of every section whose heading mentions coach / manager changes (its subsections included)."""
    out, cur, level = [], [], 0                          # level: the heading depth of the section we're keeping
    for line in text.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if m:
            d = len(m.group(1))
            if level and d > level:                      # a subsection ("=== In-season ==="): keep going
                cur.append(line)
                continue
            if cur:
                out.append("\n".join(cur))
            cur, level = ([line], d) if re.search(r"coach|manager", m.group(2), re.I) else ([], 0)
        elif level:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def run(seasons=range(2015, 2027)):
    try:
        with open(RAW) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        raw = {}
    for season in seasons:
        for lg, page in pages(season).items():
            key = f"{lg}:{season}"
            if raw.get(key, {}).get("sections"):
                continue
            secs = coaching_sections(fetch(page))
            raw[key] = {"page": page, "sections": secs}
            print(f"{key}: {page} - {len(secs)} coaching section(s), {sum(len(s) for s in secs)} chars", flush=True)
            time.sleep(0.5)                                  # (gentle on Wikipedia)
    with open(RAW, "w") as f:
        json.dump(raw, f)


if __name__ == "__main__":
    run()
