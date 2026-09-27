"""Team drama from the news: coach fired, suspensions, arrests, personal/family leave, deaths in the family,
trade requests, holdouts. ESPN's league news is scanned every run; each hit tags the team for DRAMA_DAYS.
There is no free news archive to learn these from, so they're used as rules: drama on the other side is a
reason for our pick; drama on our side means the engine wants twice the usual value."""
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import sports_data as sd

NEWS = "https://site.api.espn.com/apis/site/v2/sports/{path}/news?limit=100"
PATH = os.path.join(sd.DATA, "news.json")
DRAMA_DAYS = 10
KINDS = [   # (kind, pattern) - checked on the headline + description
    ("coach fired", r"\b(fire[sd]?|firing|dismiss(ed|es)?|part(s|ed)? ways with)\b.*\b(coach|manager|coordinator)\b|\binterim (head )?coach\b"),
    ("suspension", r"\bsuspend(ed|s|sion)?\b"),
    ("legal trouble", r"\barrest(ed)?\b|\bcharged\b|\bindict(ed|ment)\b|\bdomestic\b"),
    ("family/personal", r"\bpersonal (reasons|matter)\b|\bleave of absence\b|\bbereavement\b|\bfamily (matter|emergency)\b|"
                        r"\b(passed away|died|death of)\b"),
    ("illness", r"\billness\b|\bflu\b|\bhospitali[sz]ed\b|\bvirus\b"),
    ("relationship drama", r"\bdivorc(e|ed|ing)\b|\bsplit (from|with)\b|\bbr(eak|oke) ?up\b|\bseparat(ed|ion) from\b|"
                           r"\bcustody\b|\bex-(wife|girlfriend|fiancee?)\b"),
    ("new baby", r"\bbirth of (his|their)\b|\bwelcome[sd]? (a |their )?(baby|son|daughter)\b|\bpaternity\b"),
    ("trade drama", r"\btrade request\b|\brequest(s|ed)? (a )?trade\b|\bhold ?out\b|\bdemand(s|ed)? (a )?trade\b"),
]


def _teams(article):
    ids = set()
    for c in article.get("categories") or []:
        if c.get("type") == "team" or c.get("teamId") or c.get("team"):
            tid = c.get("teamId") or (c.get("team") or {}).get("id")
            if tid:
                ids.add(str(tid))
    return ids


def classify(text):
    t = text.lower()
    return [k for k, pat in KINDS if re.search(pat, t)]


def sync(budget_s=60):
    """Pull every league's news, tag teams with drama. Returns number of new tags."""
    now = datetime.now(timezone.utc)
    data = {}
    if os.path.exists(PATH):
        with open(PATH) as f:
            data = json.load(f)
    seen = {e["id"] for evs in data.values() for e in evs}
    new = 0
    deadline = time.time() + budget_s
    for lg, (path, *_rest) in sd.LEAGUES.items():
        if time.time() > deadline:
            break
        try:
            with urllib.request.urlopen(NEWS.format(path=path), timeout=20) as r:
                arts = json.load(r).get("articles") or []
        except Exception as e:                              # noqa: BLE001
            sd.ERRORS.append(f"news {lg}: {str(e)[:100]}")
            continue
        for a in arts:
            aid = str(a.get("id") or a.get("headline"))
            if aid in seen:
                continue
            kinds = classify(f'{a.get("headline", "")} {a.get("description", "")}')
            if not kinds:
                continue
            for tid in _teams(a):
                data.setdefault(f"{lg}:{tid}", []).append({"id": aid, "kind": kinds[0], "date": (a.get("published") or now.isoformat())[:10],
                                                          "headline": (a.get("headline") or "")[:140]})
                new += 1
            seen.add(aid)
    cutoff = (now - timedelta(days=DRAMA_DAYS)).strftime("%Y-%m-%d")
    data = {k: [e for e in v if e["date"] >= cutoff] for k, v in data.items()}
    data = {k: v for k, v in data.items() if v}
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    return new


def load():
    if os.path.exists(PATH):
        with open(PATH) as f:
            return json.load(f)
    return {}


def drama(news, league, team_id):
    """The team's recent drama events (newest first)."""
    return sorted(news.get(f"{league}:{team_id}", []), key=lambda e: e["date"], reverse=True)
