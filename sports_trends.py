"""IN-SEASON TRENDS & PATTERNS: "Thursday Night Football went under 8 of 9" - do streaks like that keep going?

Every real final gets situation tags, worked out in US Eastern time: the football slot (thursday night, sunday
night = a Sunday start at 7:30pm ET or later, monday night, saturday for college, sunday day), the day of the week
(other sports), home favorite / road favorite, a big favorite (-250 or shorter), and for the NBA, NHL and MLB a
team on a back-to-back (either side played the day before). For each situation we track four things: did it go
over or under the total (pushes skipped), did the favorite win, did the favorite cover (spread sports), did the
home team win.

THE HONEST PART: we walk every game in time order, one season at a time. Before each day's games, a situation's
season-so-far record is checked. A trend is ACTIVE if it has gone the same way 5+ in a row (the "streak" family)
or 65%+ of the time over 8+ games (the "rate" family). Every time a trend is active, we write down whether the
next game kept it going. Only results from BEFORE that day count, so nothing peeks. A family of trends is
PROVEN_FOLLOW (ride it) only if following it hit 52.4%+ (beats -110 juice) on the older half AND the newer half of
the history, 200+ times each, and the pooled rate is surely above a coin flip (z >= 1.64). PROVEN_FADE is the
mirror (47.6% or less both halves, z <= -1.64). Anything else is WATCH ONLY: a fun note, not a bet.
Saved to data/sports/trends.json."""
import json
import math
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "trends.json")
ET = ZoneInfo("America/New_York")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
FOOTBALL = ("nfl", "ncaaf")
B2B_LEAGUES = ("nba", "nhl", "mlb")
OUTCOMES = ("total", "fav_ml", "fav_cover", "home")
WORDS = {"total": ("under", "over"), "fav_ml": ("underdogs win", "favorites win"),
         "fav_cover": ("underdogs cover", "favorites cover"), "home": ("road team wins", "home team wins")}
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
STREAK = 5                      # this many in a row the same way = an active streak
RATE, RATE_N = 0.65, 8          # ...or this share of the season so far, over at least this many games
BREAK_EVEN = 0.524              # what -110 juice needs
MIN_N = 200                     # follow-ups needed on EACH half before a family can be proven
Z = 1.64                        # 95% sure it isn't luck
BIG_FAV = -250
UPCOMING_DAYS = 7


def et(g):
    return datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(ET)


def season(league, t):
    """MLB seasons are calendar years; the rest start in the fall (Aug+ = that year's season)."""
    if league == "mlb":
        return t.year
    return t.year if t.month >= 8 else t.year - 1


def b2b_map(games, league):
    """{game id: True} when either team also played the day before (Eastern dates; finals and scheduled games)."""
    gs = sorted((g for g in games.values() if g["league"] == league and g["status"] in ("final", "pre")),
                key=lambda g: (g["start"], g["id"]))
    last, out = {}, {}
    for g in gs:
        d = et(g).date()
        out[g["id"]] = any(last.get(g[s]) == d - timedelta(days=1) for s in ("home", "away"))
        for s in ("home", "away"):
            last[g[s]] = d
    return out


def favorite(g):
    """'home' / 'away' by the moneyline (the spread if there's no moneyline), None for a pick'em."""
    mh, ma = sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))
    if mh is not None and ma is not None and mh != ma:
        return "home" if mh < ma else "away"
    line = sm._num(g.get("spread_home"))
    if line:
        return "home" if line < 0 else "away"
    return None


def tags(g, league, b2b=False):
    """The situations this game falls in."""
    t = et(g)
    day = DAYS[t.weekday()]
    out = []
    if league in FOOTBALL:
        mins = t.hour * 60 + t.minute
        if day == "thursday" and t.hour >= 18:
            out.append("thursday night")
        elif day == "sunday":
            out.append("sunday night" if mins >= 19 * 60 + 30 else "sunday day")
        elif day == "monday":
            out.append("monday night")
        elif day == "saturday" and league == "ncaaf":
            out.append("saturday")
        else:
            out.append(day)             # (the slots already are the day of the week in football)
    else:
        out.append(day)
    fav = favorite(g)
    if fav:
        out.append(f"{fav} favorite")
    mls = [x for x in (sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))) if x is not None]
    if mls and min(mls) <= BIG_FAV:
        out.append("big favorite")
    if league in B2B_LEAGUES and b2b:
        out.append("back-to-back")
    return out


def outcomes(g, league):
    """{outcome: (1/0, the no-vig chance of a 1)} for a final (1 = over / favorite won / favorite covered / home won).
    Totals and spreads are ~50/50 bets; a moneyline outcome carries its real price, so 'favorites keep winning' is
    graded against how often favorites SHOULD win, not against a coin flip. Pushes and ties skipped."""
    try:
        hs, as_ = int(g["home_score"]), int(g["away_score"])
    except (TypeError, ValueError):
        return {}
    out = {}
    tot = sm._num(g.get("total"))
    if tot is not None and tot > 0 and hs + as_ != tot:
        out["total"] = (1 if hs + as_ > tot else 0, 0.5)
    ph = sm.market_p(g)
    fav = favorite(g)
    if fav and hs != as_ and ph is not None:
        out["fav_ml"] = (1 if (hs > as_) == (fav == "home") else 0, max(ph, 1 - ph))
    line = sm._num(g.get("spread_home"))
    if league in sm.SPREAD_LEAGUES and line and hs - as_ + line != 0:
        home_cov = hs - as_ + line > 0
        out["fav_cover"] = (1 if home_cov == (line < 0) else 0, 0.5)
    if hs != as_ and ph is not None:
        out["home"] = (1 if hs > as_ else 0, ph)
    return out


def pairs(g, league, b2b=False):
    """[(situation, outcome, 1/0, chance of a 1)] - every stream this final feeds."""
    oc = outcomes(g, league)
    out = []
    for sit in tags(g, league, b2b):
        for o, (v, p1) in oc.items():
            if o == "home" and sit in ("home favorite", "away favorite"):
                continue                                      # (the same thing as 'the favorite won' there)
            out.append((sit, o, v, p1))
    return out


def state(s):
    """(streak side, streak length, season games, share going the '1' way) from a stream [last, streak, n, ones]."""
    return s[0], s[1], s[2], (s[3] / s[2] if s[2] else 0.5)


def active_calls(s):
    """{family: the side (1/0) an active trend says comes next} for one stream's season-so-far."""
    side, streak, n, r = state(s)
    out = {}
    if streak >= STREAK:
        out["streak"] = side
    if n >= RATE_N and (r >= RATE or r <= 1 - RATE):
        out["rate"] = 1 if r >= RATE else 0
    return out


def push(s, v, p1=0.5):
    """Add one result to a stream [last, streak, games, ones, expected ones by the price, variance]."""
    if s[2] and s[0] == v:
        s[1] += 1
    else:
        s[0], s[1] = v, 1
    s[2] += 1
    s[3] += v
    s[4] += p1
    s[5] += p1 * (1 - p1)


def new_stream():
    return [None, 0, 0, 0, 0.0, 0.0]


def follow_ups(games, league):
    """[(date, family, outcome, hit, price chance)] - every time a trend was active, did the next game keep it going?
    (price chance = how often the side the trend points to SHOULD hit: 0.5 for totals/spreads, the no-vig price
    for a moneyline outcome.)"""
    fin = sm.finals(games, league)
    b2b = b2b_map(games, league)
    streams = {}
    out = []
    by_day = {}
    for g in fin:
        t = et(g)
        by_day.setdefault(t.date(), []).append((t, g))
    for d in sorted(by_day):
        todays = []
        for t, g in by_day[d]:
            se = season(league, t)
            for sit, o, v, p1 in pairs(g, league, b2b.get(g["id"], False)):
                k = (se, sit, o)
                s = streams.get(k)
                if s:
                    for fam, side in active_calls(s).items():
                        out.append((d.isoformat(), fam, o, 1 if v == side else 0, p1 if side == 1 else 1 - p1))
                todays.append((k, v, p1))
        for k, v, p1 in todays:                               # the day's results count only after the day
            push(streams.setdefault(k, new_stream()), v, p1)
    return out


def cell(rows):
    """rows = [(date, hit, price chance)] -> the record, both halves, and the verdict. 'edge' = hit rate minus what
    the price said (for a -110 total or spread that's hit - 50%, so +2.4 points = the 52.4% break-even)."""
    rows = sorted(rows)
    n = len(rows)
    half = n // 2
    a, b = rows[:half], rows[half:]

    def rate(rs):
        return sum(h for _, h, _ in rs) / len(rs) if rs else 0.0

    def edge(rs):
        return sum(h - p for _, h, p in rs) / len(rs) if rs else 0.0
    var = sum(p * (1 - p) for _, _, p in rows)
    z = sum(h - p for _, h, p in rows) / math.sqrt(var) if var else 0.0
    ea, eb = edge(a), edge(b)
    margin = BREAK_EVEN - 0.5
    both = len(a) >= MIN_N and len(b) >= MIN_N
    if both and ea >= margin and eb >= margin and z >= Z:
        status = "proven_follow"
    elif both and ea <= -margin and eb <= -margin and z <= -Z:
        status = "proven_fade"
    else:
        status = "watch only"
    return {"n": n, "hit": round(rate(rows), 4), "said": round(sum(p for _, _, p in rows) / n, 4) if n else 0.0,
            "edge": round(edge(rows), 4), "n_old": len(a), "hit_old": round(rate(a), 4), "edge_old": round(ea, 4),
            "n_new": len(b), "hit_new": round(rate(b), 4), "edge_new": round(eb, 4), "z": round(z, 2),
            "status": status, "from": rows[0][0] if rows else None, "to": rows[-1][0] if rows else None}


def grade(events):
    """events = [(league, date, family, outcome, hit, price chance)] -> {key: cell} at 'all', 'family',
    'league|family', 'family|outcome', 'league|family|outcome'. Verdicts use league|family, then family (the finer
    cells are shown for info - slicing finer and picking winners would be fooling ourselves)."""
    groups = {}
    for lg, d, fam, o, h, p in events:
        for k in ("all", fam, f"{fam}|{o}", f"{lg}|all", f"{lg}|{fam}", f"{lg}|{fam}|{o}"):
            groups.setdefault(k, []).append((d, h, p))
    return {k: cell(v) for k, v in groups.items()}


VERDICT = {"proven_follow": "ride", "proven_fade": "fade"}


def verdict(st, league, family):
    """'ride' / 'fade' only when that trend family is proven (this sport first, else every sport), else 'coin flip'."""
    cells = (st or {}).get("cells") or {}
    for k in (f"{league}|{family}", family):
        v = VERDICT.get((cells.get(k) or {}).get("status"))
        if v:
            return v
    return "coin flip"


def _record(s, side):
    ones, n = s[3], s[2]
    return (ones, n - ones) if side == 1 else (n - ones, ones)


def active(games, now=None, st=None, leagues=LEAGUES):
    """Trends active right now in each sport's current season, strongest first, with the upcoming games they touch."""
    now = now or datetime.now(timezone.utc)
    st = load() if st is None else st
    nt = now.astimezone(ET)
    out = []
    for lg in leagues:
        se = season(lg, nt)
        b2b = b2b_map(games, lg)
        streams = {}
        for g in sm.finals(games, lg):
            t = et(g)
            if season(lg, t) != se or t >= nt:
                continue
            for sit, o, v, p1 in pairs(g, lg, b2b.get(g["id"], False)):
                push(streams.setdefault((sit, o), new_stream()), v, p1)
        soon = [g for g in games.values() if g["league"] == lg and g["status"] == "pre"
                and nt <= et(g) <= nt + timedelta(days=UPCOMING_DAYS) and (g.get("stype") or "?") in sd.REAL]
        soon.sort(key=lambda g: g["start"])
        for (sit, o), s in streams.items():
            calls = active_calls(s)
            if not calls:
                continue
            fams = sorted(calls, key=lambda f: f != "streak")         # the streak first
            side = calls[fams[0]]
            vs = {f: verdict(st, lg, f) for f in fams if calls[f] == side}
            proven = {v for v in vs.values() if v != "coin flip"}
            vd = proven.pop() if len(proven) == 1 else "coin flip"
            w, l = _record(s, side)
            exp = s[4] if side == 1 else s[2] - s[4]              # how many the prices said it'd win
            streak = s[1] if s[0] == side else 0
            z = (w - exp) / math.sqrt(s[5]) if s[5] else 0.0        # vs the price: favorites winning a lot is normal
            out.append({"league": lg, "season": se, "situation": sit, "outcome": o, "side": side,
                        "trend": WORDS[o][side], "record": f"{w}-{l}", "price_said": round(exp, 1),
                        "streak": streak, "families": fams, "verdict": vd,
                        "strength": round(z + (streak / 2 if streak >= STREAK else 0), 2),
                        "upcoming": [g["id"] for g in soon if sit in tags(g, lg, b2b.get(g["id"], False))],
                        "upcoming_names": [f"{g['away_name']} @ {g['home_name']}" for g in soon
                                           if sit in tags(g, lg, b2b.get(g["id"], False))]})
    out.sort(key=lambda x: -x["strength"])
    return out


def _flip(side):
    return {"over": "under", "under": "over", "home": "away", "away": "home"}[side]


def lean(st, league, game):
    """[(market, side, note, verdict)] for an upcoming game in an active situation. verdict 'ride'/'fade' = a proven
    family (side is the side to take); 'coin flip' = watch only (side is simply where the trend points)."""
    out = []
    my_tags = set(tags(game, league))                         # (the back-to-back tag comes from 'upcoming')
    fav = favorite(game)
    for t in (st or {}).get("active") or []:
        if t["league"] != league or not (game.get("id") in t["upcoming"] or t["situation"] in my_tags):
            continue
        o, side = t["outcome"], t["side"]
        if o == "total":
            market, pick = "total", ("over" if side else "under")
        elif o == "home":
            market, pick = "ml", ("home" if side else "away")
        else:
            if not fav:
                continue
            market = "ml" if o == "fav_ml" else "spread"
            pick = fav if side else ("away" if fav == "home" else "home")
        vd = t["verdict"]
        if vd == "fade":
            pick = _flip(pick)
        streak = f", {t['streak']} straight" if t["streak"] >= STREAK else ""
        note = (f"{t['situation']}: {t['trend']} {t['record']} this season{streak} - "
                + {"ride": "history says ride it", "fade": "history says fade it",
                   "coin flip": "history says it's a coin flip (watch only)"}[vd])
        out.append((market, pick, note, vd))
    return out


def study(games, path=PATH, now=None, leagues=LEAGUES):
    events = []
    per = {}
    for lg in leagues:
        ev = follow_ups(games, lg)
        per[lg] = len(ev)
        events += [(lg,) + e for e in ev]
    cells = grade(events)
    res = {"cells": cells, "follow_ups": per,
           "proven": sorted(k for k, v in cells.items() if v["status"] != "watch only"),
           "rules": {"streak": STREAK, "rate": RATE, "rate_n": RATE_N, "min_n": MIN_N, "z": Z},
           "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    res["active"] = active(games, now, res, leagues)
    with open(path + ".tmp", "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return res


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def summary(st, top=15):
    c = st.get("cells") or {}
    lines = []
    keys = ["all", "streak", "rate"] + [f"{f}|{o}" for f in ("streak", "rate") for o in OUTCOMES] + \
        [f"{lg}|{f}" for lg in LEAGUES for f in ("streak", "rate")]
    for k in keys:
        v = c.get(k)
        if v:
            lines.append(f"{k}: following hit {v['hit']:.1%} vs {v['said']:.1%} the price said over {v['n']}"
                         f" (edge {v['edge_old']:+.1%} older, {v['edge_new']:+.1%} newer, z {v['z']}) -> {v['status']}")
    lines.append("proven: " + (", ".join(st.get("proven") or []) or "none"))
    for t in (st.get("active") or [])[:top]:
        up = f" · next: {', '.join(t['upcoming_names'][:3])}" if t["upcoming"] else ""
        streak = f" ({t['streak']} straight)" if t["streak"] >= STREAK else ""
        said = f" (prices said {t['price_said']:g})" if t["outcome"] in ("fav_ml", "home") else ""
        lines.append(f"ACTIVE {t['league']} {t['situation']}: {t['trend']} {t['record']}{said}{streak}"
                     f" -> {t['verdict']}{up}")
    return lines


if __name__ == "__main__":
    r = study(sd.load_games())
    for x in summary(r):
        print(x)
    print("NFL active:")
    for t in r["active"]:
        if t["league"] == "nfl":
            print(f"  {t['situation']} / {t['outcome']}: {t['trend']} {t['record']} streak {t['streak']} -> {t['verdict']}"
                  f" {t['upcoming_names']}")
