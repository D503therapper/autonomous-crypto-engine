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
    ("coach fired", r"\b(fire[sd]?|firing|dismiss(ed|es)?|part(s|ed)? ways with)\b.*\b(coach|manager|coordinator|oc|dc|hc)\b|\binterim (head )?coach\b"),
    ("suspension", r"\bsuspen(d|ded|ds|sion|sions)\b"),   # (11/11: 'suspend(ed|s|sion)?' never matched the word "suspension")
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


# A death only counts as a team's drama when it's in a current player's / coach's family or a teammate (10/5, the owner:
# "🧯 The Stars dealing with some personal stuff" was Lyle Odelein, a retired defenseman, dying at 58 - and "Former
# Falcons C Jeff Van Note dies at 80" counted against the Falcons). An old player's obituary is nothing in today's room.
_DEATH = re.compile(r"\b(passed away|died|dies|death of)\b", re.I)
_FAMILY = re.compile(r"\b(mother|father|mom|dad|wife|husband|son|daughter|brother|sister|grand\w+|uncle|aunt|cousin|"
                     r"fianc[eé]e?|girlfriend|boyfriend|child|children|baby|family|teammate)\b", re.I)
_PERSONAL = re.compile(r"\bpersonal (reasons|matter)\b|\bleave of absence\b|\bbereavement\b|\bfamily (matter|emergency)\b",
                       re.I)


def obituary(text):
    """A death in the news that isn't in a current team member's family (a former player's obituary) - not drama."""
    t = str(text or "")
    return bool(_DEATH.search(t)) and not _FAMILY.search(t) and not _PERSONAL.search(t)


def classify(text):
    t = text.lower()
    return [k for k, pat in KINDS if re.search(pat, t) and not (k == "family/personal" and obituary(t))]


# 🔎 11/11 SWEEP - A DRAMA TAG HAS TO BE TRUE (the owner, 10/1: "never false information"). ESPN tags an article with
# EVERY team it touches and the kind was read off the headline + the description, so on 11/10 the Predators +114 floor
# play's only named reason was "opponent drama: suspension" on the KINGS - the headline: "Ottawa Senators F Hayden
# Hodgson suspended by NHL's Department of Player Safety" (the Kings were the other team in that game) - and the Celtics
# card carried "opponent drama: legal trouble" on the 76ers off "Man arrested on stalking charges at LeBron James' home";
# a 23-7 game recap was "coach fired" on both teams, a Hall of Famer in the hospital an "illness" on his old team, "back
# from suspension" a suspension. A floor play needs a named reason, so a false tag CHOSE a pick. Now: the kind has to
# read off the HEADLINE (the line the card can show), the story can't be one that's over (back from / reinstated /
# overturned), and - when the caller hands in the team's name - the headline has to NAME that team, first among the
# league's teams it names (the subject: "Hawks' Flemings suspended for elbowing Pelicans' McGowens" is the Hawks').
# Can't tell = no drama (unknown is never a reason).
_OVER = re.compile(r"\bback from\b|\breturn(s|ed|ing)?\b|\breinstat\w*|\boverturn\w*|\brescind\w*|\blifted\b|"
                   r"\bcleared\b|\bacquitt\w*|\bcharges dropped\b|\bwon'?t be suspended\b|\bavoids? suspension\b|"
                   r"\b(have|has|had) not\b|\b(haven|hasn|hadn|didn|isn|wasn)'?t\b|\bden(y|ies|ied)\b|\bno (trade|formal) request\b", re.I)
_ONE_GAME = re.compile(r"\b(1|one)[- ]game\b|\bfor (the |its |their |season )*opener\b|\bfor (the )?first half\b|"
                       r"\bfor (sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b|\bfor (game|week) \d+\b", re.I)


def headline_kinds(headline):
    """The drama kinds the HEADLINE itself states (never the description - a passing mention there tagged game recaps),
    none when the story is over ("back from suspension", "reinstated")."""
    h = str(headline or "")
    return [] if _OVER.search(h) else classify(h)


def one_game(e):
    """A suspension for ONE game ("suspends X 1 game", "for opener") - game news: stale once the team has played since
    (sports.fresh_drama), like an illness."""
    return e.get("kind") == "suspension" and bool(_ONE_GAME.search(str(e.get("headline") or "")))


def _alts(name):
    n = " ".join(str(name or "").split())
    out = [n] if len(n) >= 3 else []
    if n.endswith(" St"):
        out.append(n + "ate")                                # 'Florida St' - the headline says 'Florida State'
    return out


def _find(headline, name):
    """(position, end) of the team's name in the headline as its own word(s), case kept ('Wild', 'Stars', 'Kings' are
    words too; 'Kings' never matches 'Vikings', 'Stars' never 'All-Stars'), or None."""
    best = None
    for n in _alts(name):
        m = re.search(r"(?<![A-Za-z-])" + re.escape(n) + r"(?![A-Za-z])", str(headline or ""))
        if m and (best is None or (m.start(), -m.end()) < (best[0], -best[1])):
            best = (m.start(), m.end())
    return best


def about(headline, name, others=()):
    """Is this headline about THIS team? It names the team, the name isn't a piece of a longer team name sitting on the
    same words ('Texas' in 'Texas Tech'), and no other team of the league is named before it."""
    me = _find(headline, name)
    if me is None:
        return False
    mine = set(_alts(name))
    for o in others or ():
        if not o or o in mine:
            continue
        ot = _find(headline, o)
        if ot is None:
            continue
        if ot[0] <= me[0] and ot[1] >= me[1] and (ot[1] - ot[0]) > (me[1] - me[0]):
            return False                                     # our name is inside a longer team's name
        if me[0] <= ot[0] and me[1] >= ot[1]:
            continue                                         # theirs is inside ours ('Texas' in our 'Texas Tech')
        if ot[0] < me[0]:
            return False                                     # another team is the subject
    return True


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
            kinds, talk_ = headline_kinds(a.get("headline", "")), talk_kinds(text)   # (11/11: drama off the headline only)
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


def drama(news, league, team_id, name=None, others=()):
    """The team's recent drama events (newest first) - pregame talk is not drama. 11/11: only an event whose HEADLINE
    states its kind (headline_kinds); with the team's `name` (and the league's other team names in `others`) only a
    headline that is ABOUT this team (about) - ESPN tags every team an article touches."""
    return sorted((e for e in news.get(f"{league}:{team_id}", []) if not e.get("talk")
                   and not (e.get("kind") == "family/personal" and obituary(e.get("headline")))
                   and e.get("kind") in headline_kinds(e.get("headline"))
                   and (name is None or about(e.get("headline"), name, others))),
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
