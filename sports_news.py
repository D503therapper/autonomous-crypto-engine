"""Team drama from the news: coach fired, suspensions, arrests, personal/family leave, deaths in the family,
trade requests, holdouts. ESPN's league news is scanned every run; each hit tags the team for DRAMA_DAYS.
There is no free news archive to learn these from, so they're used as rules: drama on the other side is a
reason for our pick; drama on our side means the engine wants twice the usual value.

PREGAME TALK (TALK_KINDS: contract-year / incentive talk, a publicly unhappy player or coach, guarantees and trash
talk, "must-win" quotes, rivalry-week talk, a coach on the hot seat) is tagged too, FORWARD ONLY: stored with
"talk": 1, never counted as drama, never a pick's reason and never a number. Posted legs carry the tags so the
self-check can grade them once enough picks have them (report only until then)."""
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
TALK_KINDS = [   # forward-only pregame talk - display + self-check grading only, never the numbers until proven
    ("contract year", r"\bcontract year\b|\bincentives?\b|\bextension talks?\b|\bplaying for (a|his|her|their) "
                      r"(next )?(contract|deal)\b|\bpay ?day\b"),
    ("unhappy", r"\bunhappy\b|\bfrustrat(ed|ion)\b|\bdisgruntled\b|\bupset (with|about)\b|\bwants? out\b|"
                r"\bcall(s|ed)? out\b|\bblast(s|ed)\b|\bvent(s|ed)\b|\bdisappointed in\b"),
    ("trash talk", r"\bguarantee[sd]?\b|\btrash[- ]talk(ing)?\b|\bbulletin[- ]board\b|\bfire[sd]? back\b|"
                   r"\btroll(s|ed)\b|\bwar of words\b|\bjab(s|bed)? at\b"),
    ("must-win", r"\bmust[- ]win\b|\bwin[- ]or[- ]go[- ]home\b|\bseason on the line\b|\bbacks? (are )?against the wall\b|"
                 r"\bdo[- ]or[- ]die\b"),
    ("rivalry week", r"\brivalry (week|game)\b|\bbad blood\b|\bhate each other\b|\bbragging rights\b"),
    ("hot seat", r"\bhot seat\b|\bjob security\b|\bjob (is )?(in jeopardy|on the line)\b|\bon thin ice\b"),
]


def talk_kinds(text):
    """The pregame-talk tags a headline + description carries (forward only)."""
    t = text.lower()
    return [k for k, pat in TALK_KINDS if re.search(pat, t)]


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
    seen = {e["id"].split("|")[0] for evs in data.values() for e in evs}
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
            text = f'{a.get("headline", "")} {a.get("description", "")}'
            kinds, talk_ = classify(text), talk_kinds(text)
            if not kinds and not talk_:
                continue
            day = (a.get("published") or now.isoformat())[:10]
            for tid in _teams(a):
                if kinds:
                    data.setdefault(f"{lg}:{tid}", []).append({"id": aid, "kind": kinds[0], "date": day,
                                                              "headline": (a.get("headline") or "")[:140]})
                    new += 1
                for k in talk_:                                  # forward-only talk: its own entries, never drama
                    data.setdefault(f"{lg}:{tid}", []).append({"id": f"{aid}|{k}", "kind": k, "date": day, "talk": 1,
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
    """The team's recent drama events (newest first) - pregame talk is not drama."""
    return sorted((e for e in news.get(f"{league}:{team_id}", []) if not e.get("talk")),
                  key=lambda e: e["date"], reverse=True)


def talk(news, league, team_id, days=4, today=None):
    """The team's pregame talk from the last few days (newest first, one per kind) - display / self-check only."""
    today = today or datetime.now(timezone.utc).date()
    cut = (today - timedelta(days=days)).isoformat()
    out, kinds = [], set()
    for e in sorted(news.get(f"{league}:{team_id}", []), key=lambda e: e["date"], reverse=True):
        if e.get("talk") and e["date"] >= cut and e["kind"] not in kinds:
            kinds.add(e["kind"])
            out.append(e)
    return out
