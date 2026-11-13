"""11/13 FABLE - SHOULD THE COLLEGE HOOPS LEANS CARRY UNITS? The lean record of TODAY'S code on every college hoops
board day 2018-26 (funnel4.py's rows: the board re-built at the close, every date gate open, nothing after the day known).
  lean      what the board would show (2 college hoops leans a day at most, after the unit plays' games)
  lean_any  the lean rule's WHOLE pool - the side viewer_leans would take in every game (the big sample)
Every cell: W-L, covered / won %, flat ROI at the price we'd bet AND at a flat -110 (spreads), TRAIN (seasons 2018-22)
vs HELD OUT (2023-26), seasons up, z, and a PLACEBO (2,000 random sets of the same size from every college hoops side
of that market in the rows - how often luck does as well). A cell earns units only if it beats the price in BOTH
halves, in most seasons, and survives the placebo.
NOT a clean out-of-sample test for a weight-picked side: the study weights were fit with every season seen.
Usage: python results/studies/leans_1113/s1_leans.py > results/studies/leans_1113/s1_leans.out"""
import glob, json, math, os, random

ROWS = os.path.join(os.path.expanduser("~"), ".cache", "d503_leans1113", "rows", "s20*.jsonl")
R = []
for f in sorted(glob.glob(ROWS)):
    for line in open(f):
        r = json.loads(line)
        if r.get("result") in ("won", "lost"):
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            r["md"] = r["date"][5:]
            r["win"] = r["result"] == "won"
            r["pnl"] = (r["dec"] - 1) if r["win"] else -1.0
            r["pnl110"] = (100 / 110) if r["win"] else -1.0
            r["mn"] = min(r.get("games_in") or 0, r.get("opp_games_in") or 0)
            o = r.get("ml_home_open" if r["side"] == "home" else "ml_away_open")
            r["open"] = None
            if r["market"] == "ml" and o not in ("", None):
                try:
                    o = float(o)
                    r["open"] = (o / 100 if o > 0 else 100 / -o) if r["win"] else -1.0
                    r["open_odds"] = o
                except ValueError:
                    pass
            R.append(r)
CELLS = [0]
random.seed(1113)
POOL = {m: [r for r in R if r["market"] == m] for m in ("ml", "spread")}
TRAIN = lambda r: r["season"] <= 2022      # noqa: E731


def roi(rows, k="pnl"):
    return 100 * sum(r[k] for r in rows) / len(rows) if rows else float("nan")


def placebo(rows, k, pool, n=2000):
    """How many of n random sets of the same size (same market, same season mix) do as well as the cell."""
    if len(rows) < 30:
        return None
    by = {}
    for r in pool:
        by.setdefault(r["season"], []).append(r[k])
    need = {}
    for r in rows:
        need[r["season"]] = need.get(r["season"], 0) + 1
    mine = sum(r[k] for r in rows)
    hit = 0
    for _ in range(n):
        tot = 0.0
        for s, c in need.items():
            tot += sum(random.sample(by[s], min(c, len(by[s]))))
        hit += tot >= mine
    return hit


def rec(name, rows, k="pnl", flat110=True, pool=None, show_open=False):
    if len(rows) < 25:
        if rows:
            print(f"   {name:58s} only {len(rows)} ({sum(r['win'] for r in rows)}-{sum(not r['win'] for r in rows)})")
        return None
    CELLS[0] += 1
    w = sum(r["win"] for r in rows)
    l = len(rows) - w
    m = sum(r[k] for r in rows) / len(rows)
    sd = math.sqrt(sum((r[k] - m) ** 2 for r in rows) / len(rows)) or 1
    z = m / (sd / math.sqrt(len(rows)))
    tr = [r for r in rows if TRAIN(r)]
    he = [r for r in rows if not TRAIN(r)]
    by = {}
    for r in rows:
        by.setdefault(r["season"], []).append(r[k])
    up = sum(sum(v) > 0 for v in by.values())
    pb = placebo(rows, k, pool if pool is not None else POOL[rows[0]["market"]])
    s = (f"   {name:58s} {w:5d}-{l:<5d} {100 * w / len(rows):4.1f}%  ROI {100 * m:+5.1f}%"
         + (f" (at -110 {roi(rows, 'pnl110'):+5.1f}%)" if flat110 and all(r["market"] == "spread" for r in rows) else "")
         + f" z {z:+4.1f} | train {roi(tr, k):+5.1f}% on {len(tr)} | held {roi(he, k):+5.1f}% on {len(he)} | seasons up {up}/{len(by)}"
         + (f" | placebo {pb}/2000" if pb is not None else ""))
    if show_open:
        op = [r for r in rows if r["open"] is not None]
        if len(op) >= 25:
            s += f" | at the OPEN {100 * sum(r['open'] for r in op) / len(op):+5.1f}% on {len(op)}"
    print(s)
    return m


def phase(r):
    return "Nov" if r["md"][:2] == "11" else "Dec" if r["md"][:2] == "12" else "Jan-Apr (league play)"


def early(r):
    return "11-01" <= r["md"] <= "12-15"


def spread_bucket(r):
    ln = r["line"]
    if ln is None:
        return None
    if ln >= 25:
        return "dog getting 25+"
    if ln >= 20:
        return "dog getting 20-24.5"
    if ln >= 15:
        return "dog getting 15-19.5"
    if ln >= 7.5:
        return "dog getting 7.5-14.5"
    if ln > 0:
        return "dog getting 0.5-7"
    if ln == 0:
        return "pick'em"
    if ln >= -7:
        return "favorite laying 0.5-7"
    return "favorite laying 7.5+"


def weighted(r):
    return abs((r.get("rank_p") or 0) - r["p"]) > 1e-6


print(f"rows graded: {len(R)} college hoops sides ({len(POOL['ml'])} moneyline, {len(POOL['spread'])} spread), "
      f"{len({r['date'] for r in R})} board days, seasons {min(r['season'] for r in R)}-{max(r['season'] for r in R)}")
print("the base: every college hoops side in the rows")
for m in ("ml", "spread"):
    rec(f"every {m} side", POOL[m], pool=POOL[m])
rec("every spread DOG (getting points)", [r for r in POOL["spread"] if (r["line"] or 0) > 0])
rec("every spread dog getting 15+", [r for r in POOL["spread"] if (r["line"] or 0) >= 15])
rec("every spread dog getting 25+", [r for r in POOL["spread"] if (r["line"] or 0) >= 25])

for tag, key, title in (("A", "lean", "THE LEANS THE BOARD WOULD SHOW (2 a day, after the unit plays)"),
                        ("B", "lean_any", "THE LEAN RULE'S WHOLE POOL (its side in every game, no 2-a-day cap)")):
    L = [r for r in R if r[key]]
    print(f"\n==== {tag}. {title}: {len(L)} graded, {len({r['date'] for r in L})} days")
    rec("ALL", L, pool=R)
    rec("  the fill leans (a who-wins favorite after the regular leans)", [r for r in L if r.get("fill" if key == "lean" else "fill_any")], pool=R)
    for m in ("ml", "spread"):
        M = [r for r in L if r["market"] == m]
        print(f" -- {m.upper()}")
        rec(f"{m}: all", M, show_open=(m == "ml"))
        if m == "ml":
            rec("ml: favorites (-150..-101)", [r for r in M if r["odds"] < 0], show_open=True)
            rec("ml: favorites -150..-130", [r for r in M if -150 <= r["odds"] <= -130], show_open=True)
            rec("ml: favorites -129..-101", [r for r in M if -129 <= r["odds"] <= -101], show_open=True)
            rec("ml: dogs (+100 and up)", [r for r in M if r["odds"] >= 100], show_open=True)
            rec("ml: home side", [r for r in M if r["home"] and str(r["neutral"]) != "1"], show_open=True)
            rec("ml: road side", [r for r in M if not r["home"] and str(r["neutral"]) != "1"], show_open=True)
        else:
            for b in ("dog getting 25+", "dog getting 20-24.5", "dog getting 15-19.5", "dog getting 7.5-14.5", "dog getting 0.5-7",
                      "favorite laying 0.5-7", "favorite laying 7.5+"):
                rec(f"spread: {b}", [r for r in M if spread_bucket(r) == b])
            rec("spread: every dog getting 15+", [r for r in M if (r["line"] or 0) >= 15])
            rec("spread: every dog getting 20+", [r for r in M if (r["line"] or 0) >= 20])
            rec("spread: small numbers (inside 7 either way)", [r for r in M if abs(r["line"] or 0) <= 7])
            rec("spread: every favorite", [r for r in M if (r["line"] or 0) < 0])
            rec("spread: a STUDIED WEIGHT on the side (rank weights moved it)", [r for r in M if weighted(r)])
            rec("spread: NO studied weight (the big-favorite dial alone)", [r for r in M if not weighted(r)])
            rec("spread: studied weights +0.03 or more", [r for r in M if (r.get('rank_p') or 0) - r['p'] >= 0.03 - 1e-9])
            rec("spread: studied weights +0.05 or more", [r for r in M if (r.get('rank_p') or 0) - r['p'] >= 0.05 - 1e-9])
            rec("spread: lean read 53%+", [r for r in M if (r.get('lean_read') or 0) >= 0.53])
            rec("spread: lean read 55%+", [r for r in M if (r.get('lean_read') or 0) >= 0.55])
            rec("spread: price -105 or better", [r for r in M if r["odds"] >= -105])
            rec("spread: price -113 or worse", [r for r in M if r["odds"] <= -113])
        print(f"   by season phase ({m})")
        for ph in ("Nov", "Dec", "Jan-Apr (league play)"):
            rec(f"{m}: {ph}", [r for r in M if phase(r) == ph], show_open=(m == "ml"))
        E = [r for r in M if early(r)]
        rec(f"{m}: EARLY WINDOW Nov 1 - Dec 15", E, show_open=(m == "ml"))
        rec(f"{m}: early window, a team under 5 games in", [r for r in E if r["mn"] < 5], show_open=(m == "ml"))
        rec(f"{m}: early window, a team under 4 games in", [r for r in E if r["mn"] < 4], show_open=(m == "ml"))
        rec(f"{m}: early window, both teams 5+ games in", [r for r in E if r["mn"] >= 5], show_open=(m == "ml"))
        if m == "spread":
            rec("spread: early window, dog getting 15+", [r for r in E if (r["line"] or 0) >= 15])
            rec("spread: early window, dog getting 20+", [r for r in E if (r["line"] or 0) >= 20])
            rec("spread: early window, dog getting 25+", [r for r in E if (r["line"] or 0) >= 25])
            rec("spread: early window under 5 games, dog getting 25+", [r for r in E if (r["line"] or 0) >= 25 and r["mn"] < 5])
            rec("spread: Nov 1-14 (the live leans' two weeks), dog getting 25+", [r for r in M if "11-01" <= r["md"] <= "11-14" and (r["line"] or 0) >= 25])
            rec("spread: Nov 1-14, every lean", [r for r in M if "11-01" <= r["md"] <= "11-14"])
    print(" -- by season (all leans): " + "  ".join(
        f"{s}: {sum(r['win'] for r in L if r['season'] == s)}-{sum(not r['win'] for r in L if r['season'] == s)} {roi([r for r in L if r['season'] == s]):+.1f}%"
        for s in sorted({r['season'] for r in L})))

# C. the live 5-5: how often does the lean record run 4-1 / 5-5 by luck?
L = [r for r in R if r["lean"] and r["market"] == "spread" and (r["line"] or 0) >= 25]
if L:
    p = sum(r["win"] for r in L) / len(L)
    print(f"\n==== C. THE HOT HAND: the replay's 25+ dog leans cover {100 * p:.1f}%. At that rate 4 of 5 or better happens "
          f"{100 * (5 * p ** 4 * (1 - p) + p ** 5):.0f}% of the time - a 4-1 run says nothing either way.")

# D. the unit plays the board made in college hoops (the slot check's other half): when they first fire each season
print("\n==== D. THE COLLEGE HOOPS UNIT PLAYS IN THE SAME REPLAY (today's code): the first day each fires, by season")
K = [r for r in R if r.get("kind")]
for kind in sorted({r["kind"] for r in K}):
    X = [r for r in K if r["kind"] == kind]
    first = {}
    for r in X:
        first[r["season"]] = min(first.get(r["season"], "9"), r["date"])
    rec(f"{kind}", X, flat110=False, pool=POOL[X[0]["market"]])
    print("        first day: " + "  ".join(f"{s}: {d[5:]}" for s, d in sorted(first.items()))
          + " | a season: " + "  ".join(f"{s}: {sum(r['season'] == s for r in X)}" for s in sorted(first)))
print("\ncells:", CELLS[0])
