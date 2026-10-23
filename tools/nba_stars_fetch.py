"""🌟 Fetch the NBA honors from Basketball-Reference on GitHub's servers (nba_stars.yml) -> data/sports/nba_stars.json.
Claude's sandbox can't reach the site (10/23), so the seasons in the file today were compiled from Claude's own
knowledge (tools/nba_stars_compiled.py, source "claude-knowledge"). This job READS the public pages with a plain,
honest request (no disguise, no borrowed key - the owner's rule), ~4 seconds apart (the site asks for under 20 a
minute), and REPLACES every season it can read in full (source "bbref"). A page that fails keeps what the file holds.

    python tools/nba_stars_fetch.py [first_end_year] [last_end_year]      (default 2014 .. the season that last ended)

Pages: /awards/all_league.html (All-NBA teams, every season), /awards/all_rookie.html (All-Rookie teams),
/allstar/NBA_<year>.html (that game's rosters - injured selections and their replacements both count),
/awards/awards_<year>.html (the MVP vote - the top 5), /draft/NBA_<year>.html (the picks)."""
import html as _html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://www.basketball-reference.com"
UA = {"User-Agent": "D503-sports-engine/1.0 (GitHub Actions; public pages, read only; github.com/D503therapper)"}
PATH = os.path.join("data", "sports", "nba_stars.json")
PAUSE = 4.0
FIRST_DRAFT = 2013          # the 2013 draft's picks are rookies in 2013-14 (end year 2014)


def get(url, pause=PAUSE):
    """One page's HTML (comments opened up - the site wraps some tables in them) or None."""
    time.sleep(pause)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
            raw = r.read().decode("utf-8", "replace")
    except Exception as e:                                   # noqa: BLE001
        print(f"  FAILED {url}: {str(e)[:100]}")
        return None
    return raw.replace("<!--", "").replace("-->", "")


# ------------------------------------------------------------------ parsing (regex on the site's data-stat cells)
def tables(page):
    """{table id: table html} for every <table> on a page."""
    out = {}
    for m in re.finditer(r'<table[^>]*\bid="([^"]+)"[^>]*>(.*?)</table>', page or "", re.S):
        out[m.group(1)] = m.group(2)
    return out


def rows(table_html):
    return re.findall(r"<tr[^>]*>(.*?)</tr>", table_html or "", re.S)


def cells(row):
    """{data-stat: plain text} for a row's th / td cells."""
    out = {}
    for m in re.finditer(r'<(?:td|th)[^>]*\bdata-stat="([^"]+)"[^>]*>(.*?)</(?:td|th)>', row, re.S):
        out[m.group(1)] = clean(m.group(2))
    return out


def players(row):
    """The player names linked in a row, in order."""
    return [clean(n) for n in re.findall(r'<a[^>]*href="/players/[^"]+"[^>]*>(.*?)</a>', row, re.S)]


def clean(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def end_year(season_text):
    """'2024-25' -> 2025; '1999-00' -> 2000."""
    m = re.match(r"(\d{4})-(\d{2})", season_text or "")
    if not m:
        return None
    y = int(m.group(1))
    return y + 1


def parse_teams_page(page):
    """all_league / all_rookie -> {end year: {"1": [names], "2": [...], "3": [...]}}."""
    out = {}
    for tid, t in tables(page).items():
        for r in rows(t):
            c = cells(r)
            y, kind = end_year(c.get("season", "")), (c.get("type") or "").lower()
            if not y or "nba" not in (c.get("lg_id") or "nba").lower():
                continue
            k = {"1st": "1", "2nd": "2", "3rd": "3"}.get(kind[:3])
            names = players(r)
            if k and names:
                out.setdefault(y, {})[k] = names
    return out


def parse_allstar(page):
    """An All-Star game page -> the selections (every player linked in a roster / box table; injured men and their
    replacements are all listed), or [] when the page holds nothing."""
    names = []
    for tid, t in tables(page).items():
        if "roster" in tid.lower() or tid.lower() in ("east", "west") or "team" in tid.lower() or re.match(r"^[A-Z][a-z]+$", tid):
            for r in rows(t):
                names += players(r)
    if not names:                                            # (a format we don't know: take every player link on the page)
        for t in tables(page).values():
            for r in rows(t):
                names += players(r)
    seen, out = set(), []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def parse_mvp(page, top=5):
    t = tables(page).get("mvp") or tables(page).get("nba_mvp") or ""
    out = []
    for r in rows(t):
        c = cells(r)
        if c.get("player") and c.get("rank"):
            out.append(c["player"])
    return out[:top]


def parse_draft(page, top=10):
    out = {}
    for tid, t in tables(page).items():
        if tid not in ("stats", "draft", "round_1"):
            continue
        for r in rows(t):
            c = cells(r)
            try:
                pick = int(c.get("pick_overall") or 0)
            except ValueError:
                continue
            if 1 <= pick <= top and c.get("player"):
                out[pick] = c["player"]
    return [out[i] for i in range(1, top + 1) if i in out]


# ------------------------------------------------------------------ the merge
def merge(old, got, day):
    """Fetched pieces into the file: a season is rewritten only when all four lists came back whole (All-NBA 15 men,
    20+ All-Stars, 5 MVP names, 5 All-Rookie); a draft year when its 10 picks did. Everything else stays as it was."""
    out = json.loads(json.dumps(old or {"v": 1, "seasons": {}, "draft": {}}))
    out.setdefault("seasons", {})
    out.setdefault("draft", {})
    for y, s in (got.get("seasons") or {}).items():
        an = s.get("all_nba") or {}
        whole = (sum(len(v) for v in an.values()) >= 15 and len(s.get("all_star") or []) >= 20
                 and len(s.get("mvp_top5") or []) >= 5 and len(s.get("all_rookie_1") or []) >= 5)
        if whole:
            out["seasons"][str(y)] = {"all_nba": an, "all_star": s["all_star"], "mvp_top5": s["mvp_top5"][:5],
                                      "all_rookie_1": s["all_rookie_1"], "source": "bbref", "fetched": day}
        else:
            print(f"  {y}: incomplete ({sum(len(v) for v in an.values())} All-NBA, {len(s.get('all_star') or [])} All-Stars, "
                  f"{len(s.get('mvp_top5') or [])} MVP, {len(s.get('all_rookie_1') or [])} All-Rookie) - kept what the file had")
    for d, picks in (got.get("draft") or {}).items():
        if len(picks) >= 10:
            out["draft"][str(d)] = picks
    out["fetched"] = day
    return out


def main(first=2014, last=None):
    now = datetime.now(timezone.utc)
    last = last or (now.year if now.month >= 7 else now.year - 1)     # the season that last ended
    day = now.strftime("%Y-%m-%d")
    got = {"seasons": {}, "draft": {}}
    print(f"all_league / all_rookie ...")
    all_nba = parse_teams_page(get(f"{BASE}/awards/all_league.html"))
    all_rookie = parse_teams_page(get(f"{BASE}/awards/all_rookie.html"))
    print(f"  All-NBA seasons read: {len(all_nba)}, All-Rookie: {len(all_rookie)}")
    for y in range(first, last + 1):
        s = got["seasons"].setdefault(y, {})
        if y in all_nba:
            s["all_nba"] = all_nba[y]
        if y in all_rookie:
            s["all_rookie_1"] = all_rookie[y].get("1") or []
        s["all_star"] = parse_allstar(get(f"{BASE}/allstar/NBA_{y}.html")) if y != 1999 else []
        s["mvp_top5"] = parse_mvp(get(f"{BASE}/awards/awards_{y}.html"))
        print(f"  {y}: All-NBA {sum(len(v) for v in (s.get('all_nba') or {}).values())}, All-Stars {len(s['all_star'])}, "
              f"MVP {s['mvp_top5'][:1]}, All-Rookie {len(s.get('all_rookie_1') or [])}")
    for d in range(max(FIRST_DRAFT, first - 1), last + 1):
        got["draft"][d] = parse_draft(get(f"{BASE}/draft/NBA_{d}.html"))
        print(f"  draft {d}: {len(got['draft'][d])} picks, #1 {got['draft'][d][:1]}")
    try:
        with open(PATH) as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = None
    out = merge(old, got, day)
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    src = {}
    for y, s in out["seasons"].items():
        src[s.get("source", "?")] = src.get(s.get("source", "?"), 0) + 1
    print(f"saved {PATH}: {len(out['seasons'])} seasons by source {src}, {len(out['draft'])} drafts")


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:3]]
    main(*a)
