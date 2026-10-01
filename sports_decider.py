"""HOW THE GAME WAS DECIDED - the one big thing that won or lost it, for the graded review (the owner, 10/1: "reviews
say how it was won or lost" - a last-second field goal, a blocked kick, a pick-six, overtime, a walk-off, an
empty-netter, a late comeback).

From ESPN's public game summary (the same free, no-key site.api.espn.com the scoreboards come from - a plain request,
like sports_data). Fetched once per graded game and kept in data/sports/deciders.json; a failed fetch never blocks
grading (it's tried again next run, 3 tries max, then the review just goes without it).

parse() gives a neutral fact ({"type", "win": "home"/"away", the names and numbers}); say() turns it into one short
plain sentence from OUR side ("Won it on a 52-yard field goal with 0:03 left" / "Lost in overtime on a Bucs field
goal"). In priority order: overtime / shootout / extra innings, walk-off, a go-ahead score late, a missed or blocked
kick at the end, a defensive or special-teams touchdown that swung it, an empty-netter that sealed it, a big comeback,
a blowout. Nothing big = {} (the review keeps its usual line)."""
import json
import os
import random
import re
import time
import urllib.request

import sports_data as sd

URL = "https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}"
REG = {"nfl": 4, "ncaaf": 4, "nba": 4, "ncaab": 2, "nhl": 3, "mlb": 9}          # regulation periods / innings
LATE = {"nfl": 120, "ncaaf": 120, "nhl": 180, "nba": 10, "ncaab": 10}            # "late" = this many seconds left
COMEBACK = {"nfl": 14, "ncaaf": 14, "nhl": 3, "mlb": 4, "nba": 18, "ncaab": 15}   # trailed by this much and won
BLOWOUT = {"nfl": 21, "ncaaf": 28, "nhl": 4, "mlb": 7, "nba": 25, "ncaab": 25}    # won by this much
UNIT = {"nhl": "goal", "mlb": "run"}                                              # (football / hoops: points)
MAX_TRIES = 3
MAX_LEN = 70                                         # the sentence stays short (the review never gets longer)


def path():
    return os.path.join(sd.DATA, "deciders.json")


def load():
    try:
        with open(path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(cache):
    keep = dict(list(cache.items())[-3000:])                 # (the newest games; the old ones are in picks.json)
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    with open(path(), "w") as f:
        json.dump(keep, f, separators=(",", ":"))


def fetch_summary(league, eid):
    url = URL.format(path=sd.LEAGUES[league][0], eid=eid)
    with urllib.request.urlopen(url, timeout=10) as r:      # plain request: ESPN 403s custom user agents
        return json.load(r)


# ---------------------------------------------------------------- reading the summary
def _secs(clock):
    m = re.match(r"\s*(\d+):(\d\d)", str(clock or ""))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _clock(secs):
    return f"{secs // 60}:{secs % 60:02d}"


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


_NAME = r"([A-Z][\w.'\-]+(?: [A-Z][\w.'\-]+){1,3})"


def _who(x, league):
    """The player on a play: ESPN's participant if it's there, else the name the play's text starts with."""
    for k in ("participants", "athletesInvolved"):
        for a in x.get(k) or []:
            n = (a.get("athlete") or a).get("displayName") if isinstance(a, dict) else None
            if n:
                return n
    t = re.sub(r"^\s*(?:Goal|GOAL)\s*[-:]\s*", "", str(x.get("text") or ""))
    pat = {"nhl": _NAME + r" \(\d+\)", "mlb": _NAME + r" (?:homered|singled|doubled|tripled|walked|hit|grounded|flied"
           r"|lined|reached|sacrificed|was hit|scored|popped|bunted)"}.get(league, _NAME + r",? \d+ ?(?:Yd|Yard|yd|yard)")
    m = re.match(pat, t)
    return m.group(1) if m and len(m.group(1)) <= 28 else None


def _yards(x):
    m = re.search(r"(\d+)[ -]?(?:Yd|Yard|yd|yard)s?\b", str(x.get("text") or ""))
    return int(m.group(1)) if m else None


def _kind(x):
    t = f'{(x.get("type") or {}).get("text") or ""} {(x.get("scoringType") or {}).get("name") or ""} ' \
        f'{x.get("text") or ""}'.lower()
    if "field goal" in t or re.search(r"\bfg\b", t):
        return "fg"
    if "touchdown" in t or re.search(r"\btd\b", t) or "kick)" in t:
        return "td"
    return ""


def _mlb_what(x):
    t = str(x.get("text") or "").lower()
    for k, v in (("homered", "homer"), ("sacrifice fly", "sac fly"), ("singled", "single"), ("doubled", "double"),
                 ("tripled", "triple"), ("walked", "walk"), ("hit by pitch", "hit-by-pitch"), ("wild pitch", "wild pitch")):
        if k in t:
            return v
    return None


def _plays(p):
    out = list(p.get("plays") or [])
    if not out:                                          # football: the plays live inside the drives
        for dr in ((p.get("drives") or {}).get("previous") or []):
            for x in dr.get("plays") or []:
                out.append({**x, "team": x.get("team") or dr.get("team") or {}})
    return out


def _scores(p, league):
    """Every scoring play in order: who scored (by the score change), the score before / after, period, clock."""
    src = p.get("scoringPlays") or [x for x in _plays(p) if x.get("scoringPlay")]
    out, h0, a0 = [], 0, 0
    for x in src:
        h, a = _int(x.get("homeScore")), _int(x.get("awayScore"))
        if h is None or a is None or (h, a) == (h0, a0):
            continue
        side = "home" if h > h0 else "away" if a > a0 else None
        per = x.get("period") or {}
        if side:
            out.append({"side": side, "h": h, "a": a, "hb": h0, "ab": a0, "per": _int(per.get("number")) or 0,
                        "secs": _secs((x.get("clock") or {}).get("displayValue")), "x": x, "kind": _kind(x),
                        "who": _who(x, league), "en": bool(re.search(r"empty[ -]?net|\(EN\)", str(x.get("text") or ""),
                                                                     re.I) or x.get("emptyNet"))})
        h0, a0 = h, a
    return out


def _lead(e, win, after=True):
    h, a = (e["h"], e["a"]) if after else (e["hb"], e["ab"])
    return h - a if win == "home" else a - h


def parse(league, p):
    """The decider of a final game (a neutral fact - who won is 'win'), {} when nothing big decided it, or None when
    the summary can't be read (so it's tried again)."""
    comp = ((p.get("header") or {}).get("competitions") or [None])[0] or {}
    teams = {c.get("homeAway"): c for c in comp.get("competitors") or []}
    if league not in REG or "home" not in teams or "away" not in teams:
        return None
    hs, as_ = _int((teams["home"].get("score"))), _int(teams["away"].get("score"))
    if hs is None or as_ is None:
        return None
    if hs == as_:
        return {}                                        # (a tie: nobody won it)
    win, lose = ("home", "away") if hs > as_ else ("away", "home")
    w_, l_ = max(hs, as_), min(hs, as_)
    margin, s = w_ - l_, f"{w_}-{l_}"
    side_of = {str((c.get("team") or {}).get("id")): k for k, c in teams.items()}
    st = comp.get("status") or {}
    detail = str(((st.get("type") or {}).get("detail") or (st.get("type") or {}).get("shortDetail") or ""))
    per = max(_int(st.get("period")) or 0, *(len(c.get("linescores") or []) for c in teams.values()))
    reg = REG[league]
    ev = _scores(p, league)
    base = {"win": win, "s": s}

    def ls(side, n):
        try:
            return sum(_int((x.get("value") if x.get("value") is not None else x.get("displayValue"))) or 0
                       for x in (teams[side].get("linescores") or [])[:n])
        except (TypeError, AttributeError):
            return None
    go = None                                            # the go-ahead-for-good score (the winner's last lead change)
    for e in ev:
        if e["side"] == win and _lead(e, win, False) <= 0 < _lead(e, win):
            go = e
    last = ev[-1] if ev else None

    # 1. overtime / shootout / extra innings (a walk-off in extras is still a walk-off)
    if league == "mlb":
        if per > reg or (last and last["per"] >= reg):
            if win == "home" and last and last["side"] == "home" and last["per"] >= reg and _lead(last, win, False) <= 0:
                return {**base, "type": "walkoff", "n": last["per"], "p": last["who"], "w": _mlb_what(last["x"])}
            if per > reg:
                d = {**base, "type": "extras", "n": per}
                if go and go["per"] > reg:
                    d.update(p=go["who"], w=_mlb_what(go["x"]))
                return d
    elif league == "nhl" and re.search(r"\bSO\b", detail):
        return {**base, "type": "so"}
    elif per > reg or re.search(r"\bOT\b", detail):
        d = {**base, "type": "ot", "n": max(1, per - reg)}
        if last and last["side"] == win and last["per"] > reg:
            d.update(p=last["who"], k=last["kind"], y=_yards(last["x"]) if last["kind"] == "fg" else None)
        return d
    # 2. a go-ahead score late
    if go and go["secs"] is not None and go["per"] == reg and go["secs"] <= LATE.get(league, -1):
        return {**base, "type": "late", "p": go["who"], "k": go["kind"], "c": _clock(go["secs"]),
                "y": _yards(go["x"]) if go["kind"] == "fg" else None}
    if league == "mlb" and go and go["per"] == reg:      # (baseball: took the lead for good in the 9th)
        return {**base, "type": "late", "n": reg, "p": go["who"], "w": _mlb_what(go["x"])}
    # 3. a missed or blocked kick at the end (football, a one-score game)
    if league in ("nfl", "ncaaf") and margin <= 3:
        miss = None
        for x in _plays(p):
            t = f'{(x.get("type") or {}).get("text") or ""} {x.get("text") or ""}'.lower()
            if "field goal" not in t or not re.search(r"no good|missed|blocked", t):
                continue
            pr = _int((x.get("period") or {}).get("number")) or 0
            sec = _secs((x.get("clock") or {}).get("displayValue"))
            if side_of.get(str((x.get("team") or {}).get("id"))) == lose and pr == reg and sec is not None and sec <= 120:
                miss = {**base, "type": "kick", "blocked": "blocked" in t, "c": _clock(sec), "y": _yards(x)}
        if miss:
            return miss
    # 4. a defensive / special-teams touchdown that swung it (the game was within one score of it)
    if league in ("nfl", "ncaaf") and margin <= 7:
        for e in ev:
            t = f'{(e["x"].get("type") or {}).get("text") or ""} {e["x"].get("text") or ""}'.lower()
            how = ("pick-six" if "interception" in t else "fumble" if "fumble return" in t else
                   "punt" if "punt return" in t else "kickoff" if re.search(r"kickoff return|kick return", t) else
                   "blocked" if "blocked" in t and "return" in t else None)
            if e["side"] == win and how and e["kind"] == "td":
                return {**base, "type": "dtd", "how": how, "p": e["who"]}
    # 5. an empty-netter that sealed it
    if league == "nhl" and margin <= 2:
        for e in ev:
            if e["side"] == win and e["en"] and _lead(e, win) == margin and _lead(e, win, False) == margin - 1:
                return {**base, "type": "en", "p": e["who"], "c": _clock(e["secs"]) if e["secs"] is not None else None}
    # 6. a big comeback (in-game when we have the plays, else the period-by-period score)
    down = max([max(0, -_lead(e, win)) for e in ev] + [0])
    if not ev:
        for n in range(1, per):
            a, b = ls(win, n), ls(lose, n)
            if a is not None and b is not None:
                down = max(down, b - a)
    if down >= COMEBACK.get(league, 99):
        return {**base, "type": "comeback", "d": down}
    # 7. a blowout
    if margin >= BLOWOUT.get(league, 99):
        d = {**base, "type": "blowout"}
        if league not in ("mlb", "nhl"):
            a, b = ls(win, 2 if reg == 4 else 1), ls(lose, 2 if reg == 4 else 1)
            if a is not None and b is not None and a > b:
                d["h"] = f"{a}-{b}"
        return d
    return {}


# ---------------------------------------------------------------- the sentence, from our side
def _ord(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# (won, type, detail) -> templates. {us} / {them}: the teams as the review says them; {p} player, {y} yards, {c} clock
# left, {s} the final (winner first), {d} how far down, {n} inning / which OT, {w} the hit, {h} the halftime score
SAY = {
    (True, "ot", "fg"): ["Won it in [overtime|OT] on {p}'s {y}-yard field goal.",
                         "{p} [hit|drilled|nailed] a {y}-yarder in overtime to win it.",
                         "Overtime, and {p} [won it|ended it] from {y} yards.",
                         "Won it in [overtime|OT] on a {y}-yard field goal."],
    (True, "ot", "td"): ["{p} scored in overtime to [win it|end it].", "Won it in [overtime|OT] on a {p} touchdown.",
                         "Won it in [overtime|OT] on a touchdown, {s}."],
    (True, "ot", "goal"): ["{p} [ended it|won it] in overtime.", "Won it in overtime on a {p} goal.",
                           "{p} scored in overtime to win it {s}."],
    (True, "ot", ""): ["Won it in {ot}, {s}.", "Needed {ot}, but {us} got it done {s}.", "Pulled it out in {ot}, {s}."],
    (True, "so", ""): ["Won it in a shootout.", "Went to a shootout and {us} [won it|took it].",
                       "Took it in a shootout, {s}."],
    (True, "extras", ""): ["{p}'s {w} in the {n} won it.", "Won it in the {n} inning, {s}.",
                           "Took {n_} innings, but {us} won it {s}."],
    (True, "walkoff", ""): ["{p} walked it off with a {w} in the {n}.", "Walk-off {w} by {p} in the {n}.",
                            "{p} [ended it|won it] with a walk-off {w}.", "Walked it off in the {n}, {s}."],
    (True, "late", "fg"): ["Won it on a {y}-yard field goal with {c} left.",
                           "{p} [hit|drilled|nailed] it from {y} with {c} left to win it.",
                           "{p}'s {y}-yarder with {c} left won it."],
    (True, "late", "td"): ["{p} scored the go-ahead touchdown with {c} left.",
                           "Went ahead for good on a {p} touchdown with {c} left.",
                           "Took the lead with {c} left on a {p} touchdown."],
    (True, "late", "goal"): ["{p} scored the winner with {c} left.", "Went ahead for good on a {p} goal with {c} left.",
                             "{p} put {us} ahead with {c} left."],
    (True, "late", "bucket"): ["{p} hit the winner with {c} left.", "Won it on a {p} bucket with {c} left."],
    (True, "late", "mlb"): ["{p}'s {w} in the 9th put {us} ahead for good.", "Went ahead for good in the 9th on a {p} {w}."],
    (True, "late", ""): ["Went ahead for good with {c} left.", "Took the lead with {c} left and held it."],
    (True, "kick", "missed"): ["{them} missed a {y}-yard field goal with {c} left. That was the game.",
                               "Their {y}-yard kick [missed|went wide] with {c} left. That was the game.",
                               "{them} missed a field goal with {c} left. That was the game."],
    (True, "kick", "blocked"): ["Blocked their {y}-yard field goal with {c} left. That was the game.",
                                "{us} blocked a {y}-yarder with {c} left to hold on.",
                                "Their kick got blocked with {c} left. That was the game."],
    (True, "dtd", ""): ["{p}'s {hw} swung it.", "A {hw} by {p} swung it, {s}.", "The {hw} swung it, {s}."],
    (True, "en", ""): ["{p} iced it with an empty-netter, {s}.", "{p}'s empty-net goal sealed it, {s}.",
                       "An empty-netter with {c} left sealed it."],
    (True, "comeback", ""): ["Came back from {d} {u} down to win {s}.", "Were down {d} and still won {s}.",
                             "Trailed by {d}, won {s}."],
    (True, "blowout", ""): ["Up {h} at the half, {s} final. Never close.", "Won {s} like they stole something.",
                            "{us} won {s}. Never close.", "{s} final. {them} got cooked."],
    (False, "ot", "fg"): ["Lost in [overtime|OT] on {p}'s {y}-yard field goal.",
                          "{them} won it in overtime on a {y}-yard field goal.", "Lost it in overtime on a field goal."],
    (False, "ot", "td"): ["Lost in [overtime|OT] on a {p} touchdown.", "{p} scored in overtime to beat us.",
                          "{them} won it in overtime on a touchdown."],
    (False, "ot", "goal"): ["Lost in overtime on a {p} goal.", "{p} beat us in overtime.",
                            "{them} won it in overtime, {s}."],
    (False, "ot", ""): ["Lost in {ot}, {s}.", "Took it to {ot} and lost {s}.", "{them} got it in {ot}, {s}."],
    (False, "so", ""): ["Lost it in a shootout.", "Went to a shootout and {them} took it.", "Lost in a shootout, {s}."],
    (False, "extras", ""): ["{p}'s {w} in the {n} beat us.", "Lost in the {n} inning, {s}.",
                            "Went {n_} innings and lost {s}."],
    (False, "walkoff", ""): ["{p} walked it off on us with a {w} in the {n}.", "Lost on a {p} walk-off {w} in the {n}.",
                             "{them} walked it off in the {n}, {s}."],
    (False, "late", "fg"): ["Lost on a {y}-yard field goal with {c} left.", "{p} beat us from {y} with {c} left.",
                            "{them} kicked the winner from {y} with {c} left."],
    (False, "late", "td"): ["Lost on a {p} touchdown with {c} left.", "{p} scored with {c} left to beat us.",
                            "{them} went ahead for good with {c} left on a {p} touchdown."],
    (False, "late", "goal"): ["{p} scored with {c} left to beat us.", "Lost on a {p} goal with {c} left.",
                              "{them} scored the winner with {c} left."],
    (False, "late", "bucket"): ["{p} hit the winner with {c} left.", "Lost on a {p} bucket with {c} left."],
    (False, "late", "mlb"): ["{p}'s {w} in the 9th beat us.", "Lost the lead for good in the 9th on a {p} {w}."],
    (False, "late", ""): ["{them} went ahead for good with {c} left.", "Lost the lead with {c} left."],
    (False, "kick", "missed"): ["Our {y}-yard field goal [missed|went wide] with {c} left. That was the game.",
                                "{us} missed a {y}-yarder with {c} left. That was the game.",
                                "Missed a field goal with {c} left. That was the game."],
    (False, "kick", "blocked"): ["Our {y}-yard kick got blocked with {c} left. That was the game.",
                                 "Our kick got blocked with {c} left. That was the game.",
                                 "{them} blocked our {y}-yarder with {c} left."],
    (False, "dtd", ""): ["{p}'s {hw} swung it, {s}.", "A {hw} by {p} swung it.", "Gave up a {hw}. That swung it, {s}."],
    (False, "en", ""): ["{p}'s empty-netter sealed it, {s}.", "{them} iced it into an empty net, {s}.",
                        "An empty-netter with {c} left put it away."],
    (False, "comeback", ""): ["Blew a {d}-{u} lead and lost {s}.", "Up {d} and still lost {s}.",
                              "Had a {d}-{u} lead. Lost {s}."],
    (False, "blowout", ""): ["Down {h} at the half, lost {s}.", "{us} got cooked, {s}.", "Lost {s}. Never close."],
}
HOW = {"pick-six": "pick-six", "fumble": "fumble return for six", "punt": "punt return touchdown",
       "kickoff": "kick return touchdown", "blocked": "blocked-kick touchdown"}


def say(d, side, us, them, league, seed, cap=MAX_LEN):
    """One short sentence of how it went, from our side (side = the side we're on), or "" when there's nothing."""
    if not d or not d.get("type") or d.get("win") not in ("home", "away") or side not in ("home", "away"):
        return ""
    won, t = d["win"] == side, d["type"]
    sub = ""
    if t in ("ot", "late"):
        sub = {"fg": "fg", "td": "td"}.get(d.get("k") or "", "")
        if league == "nhl" and d.get("p"):
            sub = "goal"
        elif league in ("nba", "ncaab") and t == "late" and d.get("p"):
            sub = "bucket"
        elif league == "mlb" and t == "late":
            sub = "mlb"
    elif t == "kick":
        sub = "blocked" if d.get("blocked") else "missed"
    n = d.get("n")
    ot = ("overtime" if (n or 1) == 1 else "double overtime" if n == 2 else f"{n} overtimes") if t == "ot" else None
    kw = {"us": us, "them": them, "p": d.get("p"), "y": d.get("y"), "c": d.get("c"), "s": d.get("s"), "d": d.get("d"),
          "n": _ord(n) if isinstance(n, int) and t != "ot" else None, "n_": n if t != "ot" else None, "w": d.get("w"),
          "h": d.get("h"), "u": UNIT.get(league, "point") if t == "comeback" else None, "ot": ot,
          "hw": HOW.get(d.get("how")) if t == "dtd" else None}
    if t == "comeback" and won and (kw["d"] or 0) > 1:
        kw["u"] += "s"                                   # ("17 points down", but "a 17-point lead")
    pool = SAY.get((won, t, sub)) or SAY.get((won, t, ""), [])
    ok = [x for x in pool if all(kw.get(k) not in (None, "") for k in re.findall(r"\{(\w+)\}", x))]
    if not ok:
        return ""
    rng = random.Random(f"how|{seed}")
    rng.shuffle(ok)
    for tpl in ok:
        line = re.sub(r"\[([^\[\]]*)\]", lambda m: rng.choice(m.group(1).split("|")), tpl)
        line = line.format(**{k: v for k, v in kw.items() if v is not None})
        line = re.sub(r"s's\b", "s'", line)                # (Matthews' empty-netter)
        line = re.sub(r"(^|[.!?] )([a-z])", lambda m: m.group(1) + m.group(2).upper(), line)   # (". The Falcons")
        if len(line) <= cap:
            return line
    return ""


# ---------------------------------------------------------------- once per graded game
def same_game(p, eid):
    """The summary is THIS game (its event id) and it's over - never another game's, never a past season's."""
    hd = (p or {}).get("header") or {}
    comp = (hd.get("competitions") or [None])[0] or {}
    done = (((comp.get("status") or {}).get("type") or {}).get("completed"))
    return str(hd.get("id") or "") == str(eid) and done is not False


def score_matches(d, leg):
    """The decider's final ('24-21', winner first) is the score we graded the leg on (leg['score'], any order)."""
    want = sorted(int(x) for x in re.findall(r"(\d+)(?=\s*@|\s*$)", str(leg.get("score") or ""))[:2]) \
        if leg.get("score") else None                    # ('49ers 20 @ Rams 17': the scores, never the "49")
    got = sorted(int(x) for x in re.findall(r"\d+", str(d.get("s") or ""))[:2]) if d.get("s") else None
    return want is None or got is None or want == got


def fill(picks, fetch=None, budget_s=45, last=80):
    """Put each newly graded leg's decider on it (leg["decider"]: the fact, or {} for nothing big). One fetch per game
    (kept in deciders.json); a failure is tried again next run (3 tries, then {}), and never stops the grading."""
    fetch = fetch or fetch_summary
    cache, changed, t0, tried = load(), False, time.time(), set()
    for pk in picks[-last:]:
        for leg in pk.get("legs") or []:
            gid = str(leg.get("game_id") or "")
            lg = gid.split(":")[0]
            if leg.get("result") not in ("won", "lost") or "decider" in leg or lg not in REG or ":" not in gid:
                continue
            e = cache.get(gid)
            if (e is None or 0 < (e.get("_fail") or 0) < MAX_TRIES) and gid not in tried:
                if time.time() - t0 > budget_s:
                    continue
                tried.add(gid)
                try:
                    raw = fetch(lg, gid.split(":", 1)[1])
                    d = parse(lg, raw) if same_game(raw, gid.split(":", 1)[1]) else {}
                except Exception as ex:                  # noqa: BLE001 - never blocks grading
                    print(f"   decider {gid}: {str(ex)[:80]}")
                    d = None
                cache[gid] = d if d is not None else {"_fail": ((e or {}).get("_fail") or 0) + 1}
                changed, e = True, cache[gid]
            if e is None:
                continue                                 # (out of time this run: next run)
            if e.get("_fail"):
                if e["_fail"] >= MAX_TRIES:
                    leg["decider"] = {}
                continue
            if e and not score_matches(e, leg):              # (the owner, 10/1: never from another game - the
                e = {}                                       # decider's final must be the score we graded)
            leg["decider"] = e
    if changed:
        try:
            save(cache)
        except OSError as ex:
            print(f"   deciders not saved: {str(ex)[:80]}")
    return cache
