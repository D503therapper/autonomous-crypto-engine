"""The football base table for the early-line studies: every side of every graded NFL / college game in the paid odds
history (2020-25 + Sept 2026), with every FAIR look (posted after both teams' last games ended - no look-ahead), the
close, the spots the live engine would tag (bye / Monday night / East-West / blew somebody out / hammered), and the
engine's own read walk-forward (tuned on the 3 seasons before, blind to injuries - what's known midweek).
-> ~/.cache/d503_early1111/base_<lg>.pkl : [row]
row: {id, lg, season, start, side, home(bool), won, close_o, close_p (no-vig), open_o (the game file's opener),
      looks: [(days out, hours since ready, median american, no-vig p, best american, {book: no-vig p})] oldest first,
      own (blind read) or None, rest, orest, last_margin, mnf, eastwest, neutral, dow_et}"""
import os
import pickle
import statistics
import sys
from datetime import timedelta

import elib as E

lib, sd, sm, se = E.lib, E.sd, E.sm, E.se
ef = lib.ef


def reads(lg):
    """{gid: own_blind home %} walk-forward (each season by an engine tuned on the 3 seasons before)."""
    cache = os.path.join(E.CACHE, f"reads_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    games = sd.load_games(lg)
    out = {}
    for season in range(2020, 2027):
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        p = sm.tune(learn, lg)
        if not p or "w" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            if lo <= g["start"] < hi:
                out[g["id"]] = sm.own_p(p, {**f, "inj": 0.0, "key": 0.0})
    pickle.dump(out, open(cache, "wb"))
    return out


def build(lg):
    cache = os.path.join(E.CACHE, f"base_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    games = sd.load_games(lg)
    own = reads(lg)
    ready = ef.ready_at(games, lg)
    htz = se._home_tz(games)
    allfin = lib.all_finals(lg)
    tl = lib.team_log(allfin)
    rows = []
    for x in lib.load_football(lg):
        g = games.get(x["id"])
        if not g or str(g.get("stype") or "2") not in sd.REAL or x["c_mlh"] in (None, 0) or x["c_mla"] in (None, 0) \
                or x["margin"] == 0:
            continue
        start = E.t(x["start"])
        rd = ready.get(x["id"])
        looks_h = []
        for days, books in x["ml"]:                    # fair looks, oldest first
            if not 0.03 <= days <= 7.5 or len(books) < 3:
                continue
            dh = statistics.median(E.dec(v[0]) for v in books.values())
            da = statistics.median(E.dec(v[1]) for v in books.values())
            ph = (1 / dh) / (1 / dh + 1 / da)
            bh = max(E.dec(v[0]) for v in books.values())
            ba = max(E.dec(v[1]) for v in books.values())
            hrs = ((start - timedelta(days=days)) - rd).total_seconds() / 3600 if rd else None
            per = {b: E.nv(v[0], v[1]) for b, v in books.items()}
            looks_h.append((days, hrs, dh, da, ph, bh, ba, per))
        if not looks_h:
            continue
        et = start.astimezone(E.ET)
        try:
            gtz = float(g.get("tzo"))
        except (TypeError, ValueError):
            gtz = None
        oh, oa = lib.num(g.get("ml_home_open")), lib.num(g.get("ml_away_open"))
        for side, other, sign in (("home", "away", 1), ("away", "home", -1)):
            home = side == "home"
            me = lib.before(tl, x[side], x["start"], 1)
            op = lib.before(tl, x[other], x["start"], 1)
            rest = orest = lm = None
            if me and me[-1]["season"] == x["season"]:
                rest = (start - E.t(me[-1]["start"])).days
                m = me[-1]["hs"] - me[-1]["as"]
                lm = m if me[-1]["home"] == x[side] else -m
            if op and op[-1]["season"] == x["season"]:
                orest = (start - E.t(op[-1]["start"])).days
            mine = htz.get((lg, x[side]))
            ew = bool(lg == "nfl" and not home and not x["neutral"] and mine is not None and gtz is not None
                      and mine >= -5 and gtz <= -7)
            looks = [(d, h, E.am(dh if home else da), (ph if home else 1 - ph), E.am(bh if home else ba),
                      {b: (p if home else 1 - p) for b, p in per.items()})
                     for d, h, dh, da, ph, bh, ba, per in looks_h]
            co = x["c_mlh"] if home else x["c_mla"]
            cp = E.nv(x["c_mlh"], x["c_mla"])
            o = own.get(x["id"])
            rows.append({"id": x["id"], "lg": lg, "season": x["season"], "start": x["start"], "side": side,
                         "home": home, "won": (x["margin"] > 0) == home, "close_o": co,
                         "close_p": cp if home else 1 - cp,
                         "open_p": (E.nv(oh, oa) if home else 1 - E.nv(oh, oa)) if oh and oa else None,
                         "looks": looks, "own": (o if home else 1 - o) if o is not None else None,
                         "rest": rest, "orest": orest, "last_margin": lm, "mnf": lg == "nfl" and et.weekday() == 0,
                         "eastwest": ew, "neutral": x["neutral"], "dow_et": et.weekday(), "team": x[side],
                         "opp": x[other]})
    pickle.dump(rows, open(cache, "wb"))
    return rows


def first_fair(r):
    """The week's first fair look 1.5-7.5 days out (the early number), or None."""
    e = [k for k in r["looks"] if 1.5 <= k[0] < 7.5]
    return e[0] if e else None


def early_looks(r):
    return [k for k in r["looks"] if 1.5 <= k[0] < 7.5]


def game_day(r):
    """The last look inside 1.5 days (game morning in this history), or None."""
    e = [k for k in r["looks"] if 0.03 <= k[0] < 1.5]
    return e[-1] if e else None


def spots(r, look, first=None):
    """The spots the live scan would tag for this dog at `look` (hammered needs an earlier fair look)."""
    o = look[2]
    if not 100 <= o <= 350:
        return []
    hit = []
    if r["rest"] is not None and r["orest"] is not None and r["rest"] >= se.REST_BYE and r["orest"] <= se.REST_NORMAL:
        hit.append("bye")
    if r["mnf"]:
        hit.append("mnf")
    if r["eastwest"]:
        hit.append("eastwest")
    if r["last_margin"] is not None and r["last_margin"] >= se.BLOWOUT and r["rest"] is not None and r["rest"] <= 21:
        hit.append("blowout")
    if first is not None and first is not look and (look[3] - first[3]) * 100 >= se.HAMMER_PTS:
        hit.append("hammered")
    return hit


if __name__ == "__main__":
    for lg in sys.argv[1:] or ("nfl", "ncaaf"):
        rows = build(lg)
        print(lg, len(rows), "sides;", sum(1 for r in rows if first_fair(r)), "with an early fair look;",
              sum(1 for r in rows if r["own"] is not None), "with a read")
        import collections
        print(collections.Counter(r["season"] for r in rows))
        print("looks per side:", collections.Counter(len(r["looks"]) for r in rows))
