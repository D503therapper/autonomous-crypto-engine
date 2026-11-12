"""11/12 DEEP PROGRAM - A9: DO THE ABSENCE POINTS HOLD AT THE CLOSE? sports_absences.penalty takes 9 points off an NBA
team's own read when its top scorer (most points over its last 10 box games) is out, 11 for two of its top three,
6 / 4 / 7 in hockey (top point man / one of the top two / two of the top three) - numbers measured 10/2 against a
RATINGS read that did not know the injury. The own read now starts from the books' price (trust ~0), and the price
knows. THE TEST: every game 2016-26 (NBA) / 2021-26 (NHL) where the live rule's key men (same definition, walk-forward
from the box scores) took no part tonight - the no-vig close said X for the side ACROSS; did it win X, or X + 9?
'said' = the no-vig close; 'engine' = the close + the absence points (what the own read says today).
LEAK NOTE: 'did not play tonight' is the box score's fact - known at the tip, and the CLOSE has it. That is the point:
this asks whether anything is LEFT at the close. Bets are at the close.
Usage: python results/studies/deep_1112/a9_absence_close.py > results/studies/deep_1112/a9_absence_close.out"""
import json, math, os, sys
from collections import defaultdict
import dlib as D
import lib as L          # fifteen_1112

os.chdir(D.ROOT)
sys.path.insert(0, D.ROOT)
import sports_roster as R   # noqa: E402


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def box(lg):
    out = defaultdict(lambda: defaultdict(dict))
    for r in R.load(lg):
        try:
            st = json.loads(r["stats"])
        except ValueError:
            continue
        if lg == "nba":
            m, p = f(st.get("minutes")), f(st.get("points"))
        else:
            toi = str(st.get("timeOnIce") or "0:0").split(":")
            m = f(toi[0]) + (f(toi[1]) / 60 if len(toi) > 1 else 0)
            p = f(st.get("goals")) + f(st.get("assists"))
            if r.get("group") == "goalies":
                continue
        out[r["gid"]][r["team"]][r["pid"]] = (m, p)
    return out


def novig(g, side):
    ph, pa = 1 / L.dec(g["mlh"]), 1 / L.dec(g["mla"])
    return (ph if side == "H" else pa) / (ph + pa)


def run(lg):
    rows = [g for g in L.table(lg) if g["mlh"] and g["mla"] and g["hs"] != g["as"]]
    bx = box(lg)
    hist = defaultdict(list)                       # team -> [(gid, {pid: (min, pts)})] in order
    out = []
    for g in L.table(lg):
        b = bx.get(g["id"])
        rec = {}
        for side, t in (("H", g["home"]), ("A", g["away"])):
            h = hist[t][-10:]
            pts = 0
            if b and t in b and len(h) >= 10:
                tot = defaultdict(float)
                for _, pl in h:
                    for pid, (m, p) in pl.items():
                        tot[pid] += p
                top = [pid for pid, v in sorted(tot.items(), key=lambda kv: -kv[1]) if v > 0][:3]
                gone = [pid for pid in top if b[t].get(pid, (0, 0))[0] <= 0]
                fresh = [pid for pid in gone if h[-1][1].get(pid, (0, 0))[0] > 0]      # played the last game
                if lg == "nba":
                    pts = min(max(9 if top and top[0] in gone else 0, 11 if len(gone) >= 2 else 0), 12)
                else:
                    pts = min(max(6 if top and top[0] in gone else 4 if any(p in gone for p in top[:2]) else 0, 7 if len(gone) >= 2 else 0), 8)
                rec[side] = (pts, len(gone), bool(fresh), top and top[0] in gone)
        g["_abs"] = rec
        if b:
            for t in (g["home"], g["away"]):
                if t in b:
                    hist[t].append((g["id"], b[t]))
    print(f"\n==== {lg.upper()}: {len(rows)} games with a close")
    for nm, sel in (("the top scorer out (the -9 / -6)", lambda a: a[3] and a[1] == 1),
                    ("two or more of the top three out (the -11 / -7)", lambda a: a[1] >= 2),
                    ("any absence points", lambda a: a[0] > 0),
                    ("any absence points, FRESH (one of them played the last game)", lambda a: a[0] > 0 and a[2]),
                    ("any absence points, all of them already out last game", lambda a: a[0] > 0 and not a[2])):
        for band, bf in (("the side ACROSS, every price", lambda o: True), ("the side ACROSS as a dog +100..+350", lambda o: 100 <= o <= 350),
                         ("the side ACROSS as a favorite -150..-101", lambda o: -150 <= o <= -101)):
            bets, said, eng, won = [], [], [], []
            for g in rows:
                for side in ("H", "A"):
                    a = g["_abs"].get(side)
                    oth = L.other(side)
                    if not a or not sel(a) or (g["_abs"].get(oth) or (0,))[0] > 0:      # only ONE side short (a clean read)
                        continue
                    o = L.odds(g, oth)
                    if not bf(o):
                        continue
                    bets.append((g["season"], L.ml(g, oth)))
                    said.append(novig(g, oth))
                    eng.append(min(0.99, novig(g, oth) + a[0] / 100))
                    won.append(1.0 if (g["hs"] > g["as"]) == (oth == "H") else 0.0)
            if len(bets) < 30:
                continue
            c = L.cell(f"{nm[:34]} | {band[16:]}", bets, show=False)
            n = len(bets)
            w = sum(won) / n
            se = math.sqrt(w * (1 - w) / n)
            print(f"  {nm:62s} {band:42s} n {n:5d}: the close said {100 * sum(said) / n:4.1f}%, the engine's own read says {100 * sum(eng) / n:4.1f}%, won {100 * w:4.1f}% "
                  f"(z vs the close {(w - sum(said) / n) / se:+.1f}, vs the engine {(w - sum(eng) / n) / se:+.1f}) | at the close {100 * c['all']['roi']:+5.1f}% (train {100 * c['train']['roi']:+5.1f}% / blind {100 * c['blind']['roi']:+5.1f}%, seasons up {c['up_tr'] + c['up_bl']}/{c['n_tr'] + c['n_bl']})")


def football(lg):
    """NFL: the lead back (most rushing yards over the last 3 box games) -3, a top-2 receiver -3, two+ roles (QB too) -10,
    the QB alone -8; college: the QB -3 (a fresh absence only - he played the last game), two+ roles -5."""
    rows = [g for g in L.table(lg) if g["mlh"] and g["mla"] and g["hs"] != g["as"]]
    bx = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0])))
    for r in R.load(lg):
        try:
            st = json.loads(r["stats"])
        except ValueError:
            continue
        v = bx[r["gid"]][r["team"]][r["pid"]]
        ca = str(st.get("completions/passingAttempts") or "").split("/")
        v[0] += f(ca[1]) if len(ca) > 1 else 0.0
        v[1] += f(st.get("rushingYards"))
        v[2] += f(st.get("receivingYards"))
    hist = defaultdict(list)
    for g in L.table(lg):
        b = bx.get(g["id"])
        rec = {}
        for side, t in (("H", g["home"]), ("A", g["away"])):
            h = hist[t][-3:]
            if b and t in b and len(h) >= 3:
                tot = defaultdict(lambda: [0.0, 0.0, 0.0])
                for pl in h:
                    for pid, v in pl.items():
                        for i in range(3):
                            tot[pid][i] += v[i]

                def top(i, m):
                    return [p for p, v in sorted(tot.items(), key=lambda kv: -kv[1][i]) if v[i] > 0][:m]
                qb, rb, wr = (top(0, 1) or [None])[0], (top(1, 1) or [None])[0], top(2, 2)
                roles, seen = [], set()
                for rname, p in [("QB", qb), ("RB", rb)] + [("WR", w) for w in wr]:
                    if p is not None and p not in seen:
                        seen.add(p)
                        roles.append((rname, p))
                if lg == "ncaaf":
                    roles = [(rn, p) for rn, p in roles if p in h[-1]]            # a fresh absence only
                gone = {rn for rn, p in roles if p not in b[t]}
                if lg == "nfl":
                    pts = 10 if len(gone) >= 2 else 8 if "QB" in gone else 3 if gone else 0
                else:
                    pts = 5 if len(gone) >= 2 else 3 if "QB" in gone else 0
                rec[side] = (pts, gone)
        g["_abs"] = rec
        if b:
            for t in (g["home"], g["away"]):
                if t in b:
                    hist[t].append(dict(b[t]))
    print(f"\n==== {lg.upper()}: {len(rows)} games with a close (box scores 2021 on)")
    cuts = [("the lead back or a top-2 receiver out, the QB in (the -3)", lambda a: a[0] == 3 and "QB" not in a[1]),
            ("the QB out alone (the -8 NFL / -3 college)", lambda a: a[1] == {"QB"}),
            ("two or more roles out (the -10 / -5)", lambda a: len(a[1]) >= 2),
            ("two or more roles out, the QB in", lambda a: len(a[1]) >= 2 and "QB" not in a[1]),
            ("any absence points", lambda a: a[0] > 0)]
    for nm, sel in cuts:
        for band, bf in (("the side ACROSS, every price", lambda o: True), ("the side ACROSS as a dog +100..+350", lambda o: 100 <= o <= 350),
                         ("the side ACROSS as a favorite -150..-101", lambda o: -150 <= o <= -101)):
            bets, said, eng, won = [], [], [], []
            for g in rows:
                for side in ("H", "A"):
                    a = g["_abs"].get(side)
                    oth = L.other(side)
                    if not a or not sel(a) or (g["_abs"].get(oth) or (0,))[0] > 0:
                        continue
                    o = L.odds(g, oth)
                    if not bf(o):
                        continue
                    bets.append((g["season"], L.ml(g, oth)))
                    said.append(novig(g, oth))
                    eng.append(min(0.99, novig(g, oth) + a[0] / 100))
                    won.append(1.0 if (g["hs"] > g["as"]) == (oth == "H") else 0.0)
            if len(bets) < 30:
                continue
            c = L.cell(nm, bets, train_to=2023, show=False)
            n = len(bets)
            w = sum(won) / n
            se = math.sqrt(w * (1 - w) / n)
            print(f"  {nm:62s} {band:42s} n {n:5d}: the close said {100 * sum(said) / n:4.1f}%, the engine's own read says {100 * sum(eng) / n:4.1f}%, won {100 * w:4.1f}% "
                  f"(z vs the close {(w - sum(said) / n) / se:+.1f}, vs the engine {(w - sum(eng) / n) / se:+.1f}) | at the close {100 * c['all']['roi']:+5.1f}% (to 2023 {100 * c['train']['roi']:+5.1f}% / 2024 on {100 * c['blind']['roi']:+5.1f}%, seasons up {c['up_tr'] + c['up_bl']}/{c['n_tr'] + c['n_bl']})")


run("nba")
run("nhl")
football("nfl")
football("ncaaf")
L.done()
