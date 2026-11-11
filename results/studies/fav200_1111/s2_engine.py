"""11/11 THE -150 RULE (Victor's question) - S2 THE ENGINE'S OWN READ on favorites -151..-250, S3 the same favorites on
the closing SPREAD, S4 two-leg PARLAYS of them. Report only - no rule, no engine code.

The reads: the 10/30 funnel rows (results/studies/thin_1029/funnel_replay.py - every moneyline side on every board day
2023-10-01 -> 2026-10-12 + the live stretch 10/13-10/29, the engine's candidates() at the CLOSING price, params re-tuned
each July, so each season is read by a model fit only on the seasons before it). The same rows every 11/11 book study
reads (results/studies/book_1111/blib.py). FUNNEL=<folder with fA-fD.jsonl + fLive.jsonl> (54 MB, never committed).
Train = to 2025-06-30, BLIND (held out) = 2025-07-01 on, live apart.

The OWN read = sports.own_beats' read (the weighed w_p for NHL / NBA when it has one, else the ratings read edge_own);
'points over the price' = 100 x (own read - 1 / decimal price), juice in. The WEIGHED read = the row's p (sports.read_of).
The spread: the row joined to the game file's closing spread (results/studies/daily_1110/lib.py finals) by league, home /
away name and the Pacific date.
Usage: python results/studies/fav200_1111/s2_engine.py > results/studies/fav200_1111/s2_engine.out"""
import glob, importlib.util, itertools, json, math, os, random
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FUNNEL = os.environ.get("FUNNEL", "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030")
HELD_FROM, LIVE_FROM = "2025-07-01", "2026-10-13"
PT = ZoneInfo("America/Los_Angeles")
LEAGUES = ("nfl", "ncaaf", "nhl", "nba", "ncaab", "mlb")
PICK5 = ("nfl", "ncaaf", "nhl", "nba", "ncaab")

_s = importlib.util.spec_from_file_location("b1110", os.path.join(ROOT, "results", "studies", "daily_1110", "lib.py"))
B = importlib.util.module_from_spec(_s)
_s.loader.exec_module(B)

rows = []
for q in sorted(glob.glob(FUNNEL + "/f[A-D].jsonl")) + [FUNNEL + "/fLive.jsonl"]:
    with open(q) as f:
        rows += [json.loads(x) for x in f if x.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost") and r.get("stype") in ("2", None)]


def half(d):
    return "live" if d >= LIVE_FROM else "held" if d >= HELD_FROM else "train"


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 7 else y - 1


def own(r):
    if r["league"] in ("nhl", "nba") and r.get("w_p") is not None:
        return r["w_p"]
    return None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]


def own_m(r):
    o = own(r)
    return None if o is None else 100 * (o - 1 / r["dec"])


def wt_m(r):
    return 100 * (r["p"] - 1 / r["dec"])


def band(o):
    return "-101..-150" if -150 <= o <= -101 else "-151..-175" if -175 <= o <= -151 else "-176..-200" if -200 <= o <= -176 \
        else "-201..-250" if -250 <= o <= -201 else None


def st(bs):
    """bs: [(date, won, dec)] -> n, W, L, flat ROI %, z vs the price."""
    n = len(bs)
    if not n:
        return None
    w = sum(b[1] for b in bs)
    net = sum((b[2] - 1) if b[1] else -1 for b in bs)
    be = sum(1 / b[2] for b in bs)
    var = sum((1 / b[2]) * (1 - 1 / b[2]) for b in bs)
    return n, w, n - w, 100 * net / n, (w - be) / math.sqrt(var) if var else 0.0


def roi(bs):
    return sum((b[2] - 1) if b[1] else -1 for b in bs) / len(bs) if bs else 0.0


N_CELLS = [0]


def cell(name, bs, pool=None, seed=7):
    """One line: train + blind together, then train / blind / live, seasons up; with `pool`, a placebo - random sets of
    the same size drawn from the pool (2,000 tries): how often luck alone does as well (all and blind)."""
    N_CELLS[0] += 1
    tb = [b for b in bs if half(b[0]) != "live"]
    a, t = st(tb), st([b for b in bs if half(b[0]) == "train"])
    h, v = st([b for b in bs if half(b[0]) == "held"]), st([b for b in bs if half(b[0]) == "live"])
    if not a:
        print(f"  {name:52s} -")
        return
    seas = defaultdict(list)
    for b in tb:
        seas[season(b[0])].append(b)
    up = sum(roi(x) > 0 for x in seas.values())
    f = lambda x: f"{x[3]:+6.1f}% ({x[0]:4d}, z {x[4]:+.2f})" if x else "   -                 "  # noqa: E731
    s = (f"  {name:52s} n {a[0]:4d} {a[1]:4d}-{a[2]:<4d} flat {a[3]:+6.1f}% z {a[4]:+5.2f} | train {f(t)} | BLIND {f(h)} "
         f"| seasons up {up}/{len(seas)} ({' '.join(f'{k % 100:02d}:{100 * roi(x):+.0f}' for k, x in sorted(seas.items()))})")
    if v:
        s += f" | live {v[1]}-{v[2]} {v[3]:+.0f}%"
    if pool:
        rng = random.Random(seed)
        pa = [b for b in pool if half(b[0]) != "live"]
        ph = [b for b in pool if half(b[0]) == "held"]
        hb = [b for b in tb if half(b[0]) == "held"]
        ra, rh = roi(tb), roi(hb)
        ka = sum(roi(rng.sample(pa, len(tb))) >= ra for _ in range(2000)) if len(tb) < len(pa) else None
        kh = sum(roi(rng.sample(ph, len(hb))) >= rh for _ in range(2000)) if hb and len(hb) < len(ph) else None
        s += f" | placebo: luck did as well {ka}/2000 (all), {kh}/2000 (blind)"
    print(s)


def fav(r, lo=-250, hi=-151):
    return lo <= r["odds"] <= hi


def bet(r):
    return (r["date"], r["result"] == "won", r["dec"])


def main():
    F = [r for r in rows if fav(r)]
    P = [r for r in rows if fav(r, -150, -101)]
    print(f"rows {len(rows)} graded moneyline sides; favorites -151..-250: {len(F)}; -101..-150: {len(P)}")
    print("  coverage by league (-151..-250):", dict(sorted(defaultdict(int, {lg: sum(r['league'] == lg for r in F) for lg in LEAGUES}).items())))
    print("  own read missing on", sum(own(r) is None for r in F), "of", len(F))

    for lab, grp in (("THE FIVE LEAGUES WE PICK (NFL, college football, NHL, NBA, college hoops)", PICK5), ("MLB (history only)", ("mlb",))):
        G = [r for r in F if r["league"] in grp]
        pool = [bet(r) for r in G]
        print(f"\n== S2 - {lab}: favorites -151..-250 at the close, flat 1u")
        cell("BASE every favorite -151..-250 (in the funnel)", pool)
        for nm, fn in (("own read UNDER the price (fighting it)", lambda r: own_m(r) is not None and own_m(r) < 0),
                       ("own read 0..2 points over", lambda r: own_m(r) is not None and 0 <= own_m(r) < 2),
                       ("own read 2+ points over", lambda r: own_m(r) is not None and own_m(r) >= 2),
                       ("own read 4+ points over", lambda r: own_m(r) is not None and own_m(r) >= 4),
                       ("own read 6+ points over", lambda r: own_m(r) is not None and own_m(r) >= 6),
                       ("weighed read 2+ over", lambda r: wt_m(r) >= 2),
                       ("weighed read 4+ over", lambda r: wt_m(r) >= 4),
                       ("own AND weighed 2+ over", lambda r: own_m(r) is not None and own_m(r) >= 2 and wt_m(r) >= 2),
                       ("own 2+ over, clean (a reason, no trap, not fighting)", lambda r: own_m(r) is not None and own_m(r) >= 2
                        and not r["trap"] and not r["fighting"] and (r.get("n_reasons2") or r["n_reasons"]) > 0),
                       ("THE PLAY BAR but the price (good, lock/value tier, own beats, real value)", lambda r: r["good"]
                        and r["tier"] in ("lock", "value") and not r["fighting"] and not r["trap"] and r["real_value"] and r["own_beats"])):
            cell(nm, [bet(r) for r in G if fn(r)], pool=pool)
        print("  -- by band, own read 2+ / 4+ over:")
        for b in ("-151..-175", "-176..-200", "-201..-250"):
            gb = [r for r in G if band(r["odds"]) == b]
            pb = [bet(r) for r in gb]
            cell(f"{b} every one", pb)
            cell(f"{b} own 2+ over", [bet(r) for r in gb if own_m(r) is not None and own_m(r) >= 2], pool=pb)
            cell(f"{b} own 4+ over", [bet(r) for r in gb if own_m(r) is not None and own_m(r) >= 4], pool=pb)
        if len(grp) > 1:
            print("  -- by league, own read 2+ / 4+ over:")
            for lg in grp:
                gl = [r for r in G if r["league"] == lg]
                pl = [bet(r) for r in gl]
                cell(f"{lg} every one", pl)
                cell(f"{lg} own 2+ over", [bet(r) for r in gl if own_m(r) is not None and own_m(r) >= 2], pool=pl)
                cell(f"{lg} own 4+ over", [bet(r) for r in gl if own_m(r) is not None and own_m(r) >= 4], pool=pl)

    print("\n== REFERENCE - the same cuts in TODAY'S band (-101..-150, the five leagues):")
    G = [r for r in P if r["league"] in PICK5]
    pool = [bet(r) for r in G]
    cell("BASE every favorite -101..-150", pool)
    cell("own read 2+ over", [bet(r) for r in G if own_m(r) is not None and own_m(r) >= 2], pool=pool)
    cell("own read 4+ over", [bet(r) for r in G if own_m(r) is not None and own_m(r) >= 4], pool=pool)

    # ---------------- S3 the spread ----------------
    print("\n== S3 - THE SAME FAVORITES LAYING THE CLOSING SPREAD (real juice, -110 when missing; pushes out), football + hoops")
    idx = {}
    for lg in ("nfl", "ncaaf", "nba", "ncaab"):
        for g in B.finals(lg):
            t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT).date().isoformat()
            idx[(lg, g["hn"], g["an"], t)] = g
    miss = 0
    sp = defaultdict(list)
    for r in F:
        if r["league"] not in ("nfl", "ncaaf", "nba", "ncaab"):
            continue
        hn, an = (r["team"], r["opp"]) if r["home"] else (r["opp"], r["team"])
        g = idx.get((r["league"], hn, an, r["date"]))
        if not g or g["sp"] is None:
            miss += 1
            continue
        m = g["hs"] - g["as"]
        res = m + g["sp"] if r["home"] else -(m + g["sp"])
        if res == 0:
            continue
        o = (g["spho"] if r["home"] else g["spao"]) or -110
        b = (r["date"], res > 0, B.dec(o))
        om = own_m(r)
        sp[("all", r["league"])].append(b)
        sp[("all", "ALL")].append(b)
        if om is not None and om >= 2:
            sp[("own2", r["league"])].append(b)
            sp[("own2", "ALL")].append(b)
        if om is not None and om >= 4:
            sp[("own4", r["league"])].append(b)
            sp[("own4", "ALL")].append(b)
    print(f"  (no closing spread found for {miss} rows)")
    for lg in ("ALL", "nfl", "ncaaf", "nba", "ncaab"):
        cell(f"ATS {lg} every -151..-250 favorite", sp[("all", lg)])
        cell(f"ATS {lg} own 2+ over on the moneyline", sp[("own2", lg)], pool=sp[("all", lg)])
        cell(f"ATS {lg} own 4+ over on the moneyline", sp[("own4", lg)], pool=sp[("all", lg)])

    # ---------------- S4 parlays ----------------
    print("\n== S4 - TWO-LEG PARLAYS of engine-liked -151..-250 favorites (the five leagues), at the parlay price (d1 x d2)")
    for lab, thr in (("own 2+ over", 2), ("own 4+ over", 4), ("EVERY -151..-250 favorite (base)", None)):
        byd = defaultdict(list)
        for r in F:
            if r["league"] not in PICK5:
                continue
            om = own_m(r)
            if thr is not None and (om is None or om < thr):
                continue
            byd[r["date"]].append(r)
        top, allp, straight = [], [], []
        for d, rs in sorted(byd.items()):
            if len(rs) < 2:
                continue
            rs.sort(key=lambda r: -(own_m(r) or -99))
            a, b = rs[0], rs[1]
            top.append((d, a["result"] == "won" and b["result"] == "won", a["dec"] * b["dec"]))
            straight += [bet(a), bet(b)]
            if thr is not None:
                for x, y in itertools.combinations(rs, 2):
                    allp.append((d, x["result"] == "won" and y["result"] == "won", x["dec"] * y["dec"]))
        cell(f"{lab}: ONE parlay a day, the two best reads", top)
        cell(f"{lab}: the same two legs bet STRAIGHT", straight)
        if allp:
            cell(f"{lab}: EVERY pair on the day (pairs overlap)", allp)
    print(f"\n(cells printed: {N_CELLS[0]} - with ~{N_CELLS[0]} looks, one or two |z| 2 cells are expected by luck alone)")


if __name__ == "__main__":
    main()
