"""11/12 DEEP PROGRAM - A2: THE REPLAY'S CALIBRATION, BY SPORT. The funnel rows (every moneyline candidate the board
saw on 1,097 replay days 2023-26, closing prices, the reads the live board stamps). For each league and each read
(p = the blended win %, own = the own read, w_p = the weighed read, raw = the raw ratings read):
  1. buckets: what the read said vs what happened (one side a game - the HOME side - so games aren't counted twice);
  2. by venue and by favorite / dog: the read's average miss (said - won), in points of win chance;
  3. DOES THE READ KNOW ANYTHING THE CLOSE DOESN'T: outcome ~ logit(market) + b * (logit(read) - logit(market)) + h * home,
     fit on train (to 2025-06) and on held (after) apart; b = 0 means the read adds nothing, b < 0 means fade it.
Usage: python results/studies/deep_1112/a2_replay_calib.py > results/studies/deep_1112/a2_replay_calib.out"""
import math
import dlib as D

R = D.funnel()
print("funnel rows (graded, deduped):", len(R))
LGS = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")
READS = (("p", "blended"), ("own", "own read"), ("w_p", "weighed"), ("raw_own", "raw ratings"))


def miss(rs, key):
    rs = [r for r in rs if r.get(key) is not None]
    if not rs:
        return None
    said = sum(r[key] for r in rs) / len(rs)
    won = sum(r["y"] for r in rs) / len(rs)
    mk = sum(r["p_market"] for r in rs) / len(rs)
    se = math.sqrt(max(1e-9, won * (1 - won) / len(rs)))
    return len(rs), 100 * said, 100 * mk, 100 * won, (said - won) / se


for lg in LGS:
    rows = [r for r in R if r["league"] == lg and r.get("p_market") is not None]
    home = [r for r in rows if r["home"]]
    print(f"\n==== {lg.upper()}: {len(home)} games")
    for key, nm in READS:
        hs = [r for r in home if r.get(key) is not None]
        if len(hs) < 200:
            continue
        print(f" -- {nm} ({key}), home side, by bucket: n / said / market / won / z(said - won)")
        for lo, hi in ((0, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)):
            D.CELLS[0] += 1
            m = miss([r for r in hs if lo <= r[key] < hi], key)
            if m and m[0] >= 20:
                print(f"    {lo:.1f}-{hi:.1f}: n {m[0]:5d} said {m[1]:5.1f}% market {m[2]:5.1f}% won {m[3]:5.1f}%  z {m[4]:+5.1f}")
        for nm2, f in (("home, all", lambda r: r["home"]), ("road, all", lambda r: not r["home"]),
                       ("home favorite", lambda r: r["home"] and r["odds"] < 0), ("home dog", lambda r: r["home"] and r["odds"] > 0),
                       ("road favorite", lambda r: not r["home"] and r["odds"] < 0), ("road dog", lambda r: not r["home"] and r["odds"] > 0),
                       ("dog +100..+199", lambda r: 100 <= r["odds"] <= 199), ("dog +200..+350", lambda r: 200 <= r["odds"] <= 350),
                       ("fav -150..-101", lambda r: -150 <= r["odds"] <= -101)):
            for hf in ("train", "held"):
                D.CELLS[0] += 1
                m = miss([r for r in rows if f(r) and r["half"] == hf], key)
                if m:
                    print(f"    {nm2:16s} {hf:5s}: n {m[0]:5d} said {m[1]:5.1f}% market {m[2]:5.1f}% won {m[3]:5.1f}%  miss {m[1] - m[3]:+5.1f} pts (z {m[4]:+5.1f})")
        # the information test
        for hf in ("train", "held"):
            hh = [r for r in hs if r["half"] == hf and 0.02 < r[key] < 0.98]
            if len(hh) < 150:
                continue
            D.CELLS[0] += 1
            X = [[D.logit(r[key]) - D.logit(r["p_market"]), 1.0] for r in hh]
            w, se = D.fit_offset(X, [r["y"] for r in hh], [D.logit(r["p_market"]) for r in hh])
            gap = sum(abs(r[key] - r["p_market"]) for r in hh) / len(hh)
            llm = D.ll([r["p_market"] for r in hh], [r["y"] for r in hh])
            llr = D.ll([r[key] for r in hh], [r["y"] for r in hh])
            print(f"    INFO {hf:5s} n {len(hh):5d}: b(read - market) {w[0]:+.3f} (se {se[0]:.3f}, z {w[0] / se[0] if se[0] else 0:+.1f}), home shift {w[1]:+.3f} (se {se[1]:.3f})"
                  f" | avg |read - market| {100 * gap:.1f} pts | logloss market {llm:.4f} read {llr:.4f}")
print("\ncells:", D.CELLS[0])
