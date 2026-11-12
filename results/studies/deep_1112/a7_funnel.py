"""11/12 DEEP PROGRAM - A7: THE REPLAY BOARD ON TODAY'S CODE, BY SPORT - AND THE CALIBRATION FIXES, A/B.
Rows: results/studies/deep_1112/funnel2.py (every moneyline AND spread candidate on every board day 2023-10-01 ->
2026-11-10, closing prices, params re-tuned each July, no injury reports; what make_board / plays / dog_plays /
nba_fav_plays / viewer_leans made of each). NEW arm = the 11/12 calibration (the blend's dials on every game pulled to
zero, the college football read on FBS-vs-FBS); OLD arm = the tune as it was, on the held-out stretch (2025-04-11 on).
Not in the rows (as in the 10/30 funnel): the floor plays, the college hoops slot / stack plays, the 🔍 play, the early
box, mid-day adds, and every rule dated 11/11 on (the board is built for the replay day).
train = to 2025-06-30, held = after. flat = 1u a play at the close.
  1  the unit kinds and the leans (by market) by sport - the replay's expectation under the new calibration
  2  the reads' calibration under the new dials (the 'home' side of every game)
  3  A/B on the same days: what the fixes add, drop and keep
  4  the dog score against the result, by sport (is the dog read honest?)
  5  spread leans vs moneyline leans; the favorite / dog spread lean
Usage: python results/studies/deep_1112/a7_funnel.py > results/studies/deep_1112/a7_funnel.out"""
import json, math, os
from collections import defaultdict
import dlib as D

BASE = os.path.join(os.path.expanduser("~"), ".cache", "d503_deep1112")


def load(arm, parts="ABCD"):
    rows = []
    for p in parts:
        fp = os.path.join(BASE, f"funnel_{arm}", f"f{p}.jsonl")
        if not os.path.exists(fp):
            continue
        for ln in open(fp):
            r = json.loads(ln)
            if r.get("result") not in ("won", "lost"):
                continue
            r["y"] = 1.0 if r["result"] == "won" else 0.0
            r["half"] = "train" if r["date"] <= "2025-06-30" else "held"
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
            rows.append(r)
    return rows


NEW = load("new")
print(f"NEW arm rows: {len(NEW)} ({min(r['date'] for r in NEW)} -> {max(r['date'] for r in NEW)}); board days {len({r['date'] for r in NEW})}")
LGS = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")
print("\n1. THE BOARD BY SPORT (new calibration)")
for lg in LGS:
    rs = [r for r in NEW if r["league"] == lg]
    print(f" == {lg.upper()}")
    for k in ("lock", "dog", "play", "dogplay", "nbafav"):
        x = [r for r in rs if r["kind"] == k]
        if x:
            D.cell(f"{k}", x)
    D.cell("every unit play", [r for r in rs if r["kind"]])
    D.cell("unit favorites", [r for r in rs if r["kind"] and r["odds"] < 0])
    D.cell("unit dogs", [r for r in rs if r["kind"] and r["odds"] > 0])
    D.cell("leans, moneyline", [r for r in rs if r["lean"] and not r["kind"] and r["market"] == "ml"])
    D.cell("leans, spread", [r for r in rs if r["lean"] and not r["kind"] and r["market"] == "spread"])
    D.cell("   spread lean laying points", [r for r in rs if r["lean"] and not r["kind"] and r["market"] == "spread" and (r.get("line") or 0) < 0])
    D.cell("   spread lean getting points", [r for r in rs if r["lean"] and not r["kind"] and r["market"] == "spread" and (r.get("line") or 0) > 0])
    D.cell("   spread lean laying 10+", [r for r in rs if r["lean"] and not r["kind"] and r["market"] == "spread" and (r.get("line") or 0) <= -10])
print("\n2. THE READS UNDER THE NEW DIALS (moneyline, the home side): said / the close / won, and what the read adds to the close")
for lg in LGS:
    hs = [r for r in NEW if r["league"] == lg and r["market"] == "ml" and r["home"] and r.get("p_market") is not None]
    for key, nm in (("p", "blended"), ("own", "own read"), ("w_p", "weighed")):
        for hf in ("train", "held"):
            hh = [r for r in hs if r.get(key) is not None and r["half"] == hf and 0.02 < r[key] < 0.98]
            if len(hh) < 150:
                continue
            D.CELLS[0] += 1
            X = [[D.logit(r[key]) - D.logit(r["p_market"]), 1.0] for r in hh]
            w, se = D.fit_offset(X, [r["y"] for r in hh], [D.logit(r["p_market"]) for r in hh])
            said = sum(r[key] for r in hh) / len(hh)
            won = sum(r["y"] for r in hh) / len(hh)
            mk = sum(r["p_market"] for r in hh) / len(hh)
            gap = sum(abs(r[key] - r["p_market"]) for r in hh) / len(hh)
            dogs = [r for r in hh if r["odds"] > 0]
            dmiss = (sum(r[key] for r in dogs) - sum(r["y"] for r in dogs)) / max(1, len(dogs))
            print(f"   {lg:5s} {nm:9s} {hf:5s} n {len(hh):5d}: said {100 * said:4.1f} close {100 * mk:4.1f} won {100 * won:4.1f} | home dogs: said - won {100 * dmiss:+4.1f} pts | avg gap to the close {100 * gap:.1f} pts | "
                  f"b {w[0]:+.2f} (se {se[0]:.2f}) | log loss {D.ll([r[key] for r in hh], [r['y'] for r in hh]):.4f} vs the close {D.ll([r['p_market'] for r in hh], [r['y'] for r in hh]):.4f}")
OLD = load("old", "CD")
if OLD:
    days = {r["date"] for r in OLD}
    N2 = [r for r in NEW if r["date"] in days]
    print(f"\n3. A/B ON THE SAME {len(days)} BOARD DAYS ({min(days)} -> {max(days)}): the tune as it was (OLD) vs the 11/12 calibration (NEW)")
    key = lambda r: (r["date"], r["gid"], r["side"], r["market"])      # noqa: E731
    for lg in LGS + ("all",):
        o = {key(r): r for r in OLD if (lg == "all" or r["league"] == lg)}
        n = {key(r): r for r in N2 if (lg == "all" or r["league"] == lg)}
        print(f" == {lg.upper()}")
        for nm, sel in (("unit plays", lambda r: bool(r["kind"])), ("  Lock", lambda r: r["kind"] == "lock"), ("  Dog", lambda r: r["kind"] == "dog"),
                        ("  value plays", lambda r: r["kind"] == "play"), ("  runner-up dog", lambda r: r["kind"] == "dogplay"), ("  NBA favorite play", lambda r: r["kind"] == "nbafav"),
                        ("leans (moneyline)", lambda r: r["lean"] and not r["kind"] and r["market"] == "ml"), ("leans (spread)", lambda r: r["lean"] and not r["kind"] and r["market"] == "spread")):
            so = {k for k, r in o.items() if sel(r)}
            sn = {k for k, r in n.items() if sel(r)}
            if not so and not sn:
                continue
            def st(ks, src):
                rs = [src[k] for k in ks]
                nn, w, roi, z = D.bet(rs)
                return f"{w}-{nn - w} {roi:+5.1f}%"
            D.CELLS[0] += 4
            print(f"   {nm:20s} OLD {st(so, o):18s} | NEW {st(sn, n):18s} | in both {st(so & sn, n):18s} | only OLD (the fix drops) {st(so - sn, o):18s} | only NEW (the fix adds) {st(sn - so, n):18s}")
        # own read over the price as a gate: how many favorites / dogs pass under each
        for nm, band in (("favorites -150..-101 the own read has over the price", lambda r: -150 <= r["odds"] <= -101), ("dogs +100..+350 the own read has over the price", lambda r: 100 <= r["odds"] <= 350)):
            so = [r for r in o.values() if r["market"] == "ml" and band(r) and (r.get("edge_own") or -1) > 0]
            sn = [r for r in n.values() if r["market"] == "ml" and band(r) and (r.get("edge_own") or -1) > 0]
            bo, bn = D.bet(so), D.bet(sn)
            D.CELLS[0] += 2
            print(f"   {nm:52s} OLD n {bo[0]:5d} {bo[2]:+5.1f}% | NEW n {bn[0]:5d} {bn[2]:+5.1f}%")
print("\n4. THE DOG SCORE AGAINST THE RESULT (moneyline dogs +100..+350, new arm): the close said / won, flat ROI")
for lg in LGS:
    ds = [r for r in NEW if r["league"] == lg and r["market"] == "ml" and 100 <= r["odds"] <= 350 and r.get("dog_score") is not None and r.get("p_market") is not None]
    if len(ds) < 200:
        continue
    print(f" == {lg.upper()} ({len(ds)} dogs)")
    for lo, hi in ((-99, -4), (-4, 0), (0, 2), (2, 4), (4, 6), (6, 8), (8, 99)):
        x = [r for r in ds if lo <= r["dog_score"] < hi]
        if len(x) < 25:
            continue
        said = sum(r["p_market"] for r in x) / len(x)
        won = sum(r["y"] for r in x) / len(x)
        c = D.cell(f"dog score {lo if lo > -99 else 'under'}..{hi if hi < 99 else '+'}", x, out=False)
        print(f"   score {str(lo) if lo > -99 else 'under':>5s}..{str(hi) if hi < 99 else '+':<3s} n {len(x):5d}: the close said {100 * said:4.1f}%, the score says {100 * said + sum(r['dog_score'] for r in x) / len(x):4.1f}%, won {100 * won:4.1f}% | flat {c['roi']:+5.1f}% z {c['z']:+4.1f} | train {c['train']:+5.1f}% ({c['ntr']}) held {c['held']:+5.1f}% ({c['nhe']}) | seasons up {c['up']}/{c['ns']}")
    D.cell("the gated dogs (dog_gate)", [r for r in ds if r.get("dog_gate") is True])
print("\n5. COLLEGE HOOPS: THE FAVORITE SLOT'S RULE ON THE REPLAY ROWS (approx: -150..-120, own read over the price, weighed read 56%+ and 1-5 points over the price; the slot's fade / early-season / injury checks are not in the rows)")
hf = [r for r in NEW if r["league"] == "ncaab" and r["market"] == "ml" and -150 <= r["odds"] <= -120 and (r.get("edge_own") or -1) > 0]
D.cell("own read over the price, -150..-120", hf)
sl = [r for r in hf if (r.get("w_p") or r["own"]) >= 0.56 and 0.01 <= (r.get("w_p") or r["own"]) - 1 / r["dec"] <= 0.05]
D.cell("the slot's rule", sl)
D.cell("the slot's rule, weighed read under 1 point over", [r for r in hf if (r.get("w_p") or r["own"]) - 1 / r["dec"] < 0.01])
D.cell("the slot's rule, weighed read 5+ over", [r for r in hf if (r.get("w_p") or r["own"]) - 1 / r["dec"] > 0.05])
print("\ncells:", D.CELLS[0])
