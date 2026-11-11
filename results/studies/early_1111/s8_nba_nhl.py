"""S8 - THE NBA OPENING-LINE PLAY + HOCKEY / HOOPS EARLY EDGES.
(a) the paid NBA / NHL history (2020-23, every book): the DAY-BEFORE number (the first look 18h+ before the start,
    after both teams' last games began + 4h - fair) -> the GAME-MORNING look (2-14h out) -> the close (the game
    file). Which side the line moves toward (dog / favorite, home / road, the team on the second night of a
    back-to-back), and the ROI betting each side at each time. TRAIN = the first two seasons, HELD = the third.
(b) our own hourly tape this season (10/1-11/11): the first number on the tape -> 8 AM PT game day -> the close, NBA /
    NHL / college hoops.
(c) the live nba_open plays against the close."""
import json
import os
import pickle
import statistics
from datetime import timedelta

import elib as E

lib, sd = E.lib, E.sd
out = E.Tee("s8_nba_nhl_out.txt")
SP = {"nba": "basketball_nba", "nhl": "icehockey_nhl"}


def load(lg):
    cache = os.path.join(E.CACHE, f"s8_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    games = sd.load_games(lg)
    fin = [g for g in games.values() if g.get("status") == "final" and (g.get("stype") or "2") in sd.REAL]
    fin.sort(key=lambda g: g["start"])
    by_day, last, prevs = {}, {}, {}
    for g in fin:
        by_day.setdefault(g["start"][:10], []).append(g)
        prevs[g["id"]] = {s: last.get(g[s]) for s in ("home", "away")}
        last[g["home"]] = last[g["away"]] = g["start"]
    ev = lib._events(os.path.join(sd.DATA, "odds_history", f"{SP[lg]}.jsonl.gz"))
    rows = []
    for eid, rs in ev.items():
        g, flip = lib._find(rs[0], by_day)
        if not g:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            ch, ca = float(g["ml_home"]), float(g["ml_away"])
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or not ch or not ca:
            continue
        start = E.t(g["start"])
        pv = [E.t(x) for x in prevs[g["id"]].values() if x]
        rd = (max(pv) + timedelta(hours=4)) if pv else None
        looks = []
        for r in rs:
            fl = flip if r["h"] == rs[0]["h"] else (not flip)
            ts = E.t(r["snap"])
            hrs = (start - ts).total_seconds() / 3600
            bk = {b: ((v[1], v[0]) if fl else (v[0], v[1])) for b, v in r["b"].items() if v and None not in v[:2]}
            if len(bk) < 3 or hrs < 0.5:
                continue
            dh = statistics.median(E.dec(v[0]) for v in bk.values())
            da = statistics.median(E.dec(v[1]) for v in bk.values())
            looks.append((hrs, dh, da, rd is None or ts >= rd))
        looks.sort(key=lambda x: -x[0])
        b2b = {s: bool(prevs[g["id"]][s]) and (start - E.t(prevs[g["id"]][s])).total_seconds() < 30 * 3600
               for s in ("home", "away")}
        rows.append({"id": g["id"], "season": lib.season(g["start"]), "start": g["start"], "hw": hs > as_,
                     "looks": looks, "ch": ch, "ca": ca, "b2b": b2b})
    pickle.dump(rows, open(cache, "wb"))
    return rows


def side(x, s):
    """(american, no-vig p) of side s at a look."""
    dh, da = x[1], x[2]
    p = (1 / dh) / (1 / dh + 1 / da)
    return (E.am(dh), p) if s == "home" else (E.am(da), 1 - p)


def mv(xs):
    return f"{E.mean(xs):+5.2f} (n {len(xs):4d}, t {E.tstat(xs):+5.1f})" if xs else "   -   "


out("=" * 30, "S8 (a) THE PAID NBA / NHL HISTORY: the day-before number -> game morning -> the close")
for lg in ("nba", "nhl"):
    rows = load(lg)
    seas = sorted({r["season"] for r in rows})
    held = seas[-1]
    use = []
    for r in rows:
        op = next((x for x in r["looks"] if x[0] >= 18 and x[3]), None)       # the first fair look a day+ ahead
        mo = next((x for x in reversed(r["looks"]) if 2 <= x[0] <= 14), None)
        if op and mo:
            use.append((r, op, mo))
    out(f"\n {lg}: {len(rows)} games matched, {len(use)} with a fair day-before look and a game-morning look "
        f"(seasons {seas}; held out = {held}); the day-before look is {E.mean(op[0] for _, op, _ in use):.0f}h out on average")
    for nm, sel in (("dogs +100..+300 at the day-before number", lambda r, s, o: 100 <= o <= 300),
                    ("  dogs +100..+149", lambda r, s, o: 100 <= o <= 149),
                    ("  dogs +150..+300", lambda r, s, o: 150 <= o <= 300),
                    ("  home dogs", lambda r, s, o: 100 <= o <= 300 and s == "home"),
                    ("  road dogs", lambda r, s, o: 100 <= o <= 300 and s == "away"),
                    ("  dogs on the 2nd night of a back-to-back (the other team rested)",
                     lambda r, s, o: 100 <= o <= 300 and r["b2b"][s] and not r["b2b"]["away" if s == "home" else "home"]),
                    ("  rested dogs vs a team on the 2nd night",
                     lambda r, s, o: 100 <= o <= 300 and not r["b2b"][s] and r["b2b"]["away" if s == "home" else "home"]),
                    ("favorites -150..-101 at the day-before number", lambda r, s, o: -150 <= o <= -101),
                    ("  home favorites -150..-101", lambda r, s, o: -150 <= o <= -101 and s == "home"),
                    ("  road favorites -150..-101", lambda r, s, o: -150 <= o <= -101 and s == "away")):
        v = [(r, s, op, mo) for r, op, mo in use for s in ("home", "away") if sel(r, s, side(op, s)[0])]
        if len(v) < 30:
            continue
        out(f"  {nm}")
        for tag, f in (("ALL", lambda r: True), ("TRAIN", lambda r: r["season"] < held), ("HELD", lambda r: r["season"] == held)):
            w = [x for x in v if f(x[0])]
            if not w:
                continue
            m1 = [(side(mo, s)[1] - side(op, s)[1]) * 100 for r, s, op, mo in w]
            m2 = [((E.nv(r["ch"], r["ca"]) if s == "home" else 1 - E.nv(r["ch"], r["ca"])) - side(op, s)[1]) * 100
                  for r, s, op, mo in w]
            won = [r["hw"] == (s == "home") for r, s, op, mo in w]
            a = [(E.dec(side(op, s)[0]) - 1) if k else -1.0 for (r, s, op, mo), k in zip(w, won)]
            b = [(E.dec(side(mo, s)[0]) - 1) if k else -1.0 for (r, s, op, mo), k in zip(w, won)]
            c = [(E.dec(r["ch"] if s == "home" else r["ca"]) - 1) if k else -1.0 for (r, s, op, mo), k in zip(w, won)]
            out(f"    {tag:5s} to the morning {mv(m1)} | to the close {mv(m2)} | ROI day-before {E.roi(a)} | morning "
                f"{E.mean(b) * 100:+5.1f}% | close {E.mean(c) * 100:+5.1f}%")

out("\n" + "=" * 30, "S8 (b) OUR TAPE THIS SEASON: the first number on the tape (12h+ before the start) -> 8 AM PT game "
    "day -> the close")
tape = E.line_tape()
for lg in ("nba", "nhl", "ncaab"):
    G = E.games(lg)
    v = []
    for gid, tp in tape.items():
        g = G.get(gid)
        if not g or g.get("status") != "final":
            continue
        try:
            hw = float(g["home_score"]) > float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        start = E.t(g["start"])
        tp = [(E.t(x[0]), x[1], x[2]) for x in tp if E.t(x[0]) < start]
        if not tp or (start - tp[0][0]).total_seconds() < 12 * 3600:
            continue
        eight = start.astimezone(E.PT).replace(hour=8, minute=0, second=0, microsecond=0)
        if eight >= start.astimezone(E.PT):
            eight = eight - timedelta(days=1)
        am8 = [x for x in tp if x[0] <= eight]
        v.append((g, hw, tp[0], am8[-1] if am8 else None, tp[-1], (start - tp[0][0]).total_seconds() / 3600))
    out(f"\n {lg}: {len(v)} games with a first number 12h+ ahead (first number {E.mean(x[5] for x in v):.0f}h out on average)")
    for nm, sel in (("dogs +100..+300 at the first number", lambda o, s: 100 <= o <= 300),
                    ("  home dogs", lambda o, s: 100 <= o <= 300 and s == 1),
                    ("  road dogs", lambda o, s: 100 <= o <= 300 and s == 2),
                    ("favorites -150..-101 at the first number", lambda o, s: -150 <= o <= -101)):
        m1, m2, m3, a, c, e8 = [], [], [], [], [], []
        for g, hw, f, e, cl, h in v:
            for s in (1, 2):
                if not sel(f[s], s):
                    continue
                won = hw == (s == 1)
                p0 = E.nv(f[s], f[3 - s])
                m2.append((E.nv(cl[s], cl[3 - s]) - p0) * 100)
                a.append((E.dec(f[s]) - 1) if won else -1.0)
                c.append((E.dec(cl[s]) - 1) if won else -1.0)
                if e:
                    m1.append((E.nv(e[s], e[3 - s]) - p0) * 100)
                    m3.append((E.nv(cl[s], cl[3 - s]) - E.nv(e[s], e[3 - s])) * 100)
                    e8.append((E.dec(e[s]) - 1) if won else -1.0)
        if len(m2) >= 15:
            out(f"  {nm:40s} first -> 8 AM {mv(m1)} | 8 AM -> close {mv(m3)} | first -> close {mv(m2)} | ROI first {E.roi(a)} | "
                f"8 AM {E.mean(e8) * 100:+5.1f}% | close {E.mean(c) * 100:+5.1f}%")

out("\n" + "=" * 30, "S8 (c) THE LIVE nba_open PLAYS vs THE CLOSE")
for r in json.load(open(os.path.join(E.OUT, "s1_live_rows.json"))):
    if r["spot"] == "nba_open" and r["clv"] is not None:
        out(f"  {r['start'][:10]} {r['team']:10s} got {r['odds']:+5d} -> close {r['close'][0]:+5d}  {r['clv']:+5.1f} pts  "
            f"({r['h_before']:.0f}h out)  {r['result'] or 'open'}")
