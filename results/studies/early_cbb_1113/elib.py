"""11/13 - EARLY-SEASON COLLEGE HOOPS UNIT PLAYS: shared helpers (read-only on the repo).
Two tables, both built before this study (no new engine):
  F = the 11/13 lean funnel's rows (results/studies/leans_1113/funnel4.py - TODAY'S code, the board re-built at the
      close each day 2018-26, every date gate open; ~/.cache/d503_leans1113/rows) - games_in / opp_games_in, the own
      read (edge_own), the weighed read (w_p), the dog read (sports.ncaab_dog_read), trap / fighting, the lean flags.
  K = the 11/3 KNOWLEDGE (B) side table (results/studies/cbb_knowledge_b/lib.py, ~/.cache/d503_studies) - the walk-
      forward EFFICIENCY read (sports_cbb_eff: last season's final ratings carried in as the prior), gn / ogn, dog_pts,
      the ESPN open 2023-25. 2018-25.
TRAIN = seasons 2018-22, HELD OUT = 2023-26. The early window = either team under 4 regular-season games in."""
import glob, json, math, os, pickle, random
from collections import defaultdict

ROWS = os.path.join(os.path.expanduser("~"), ".cache", "d503_leans1113", "rows", "s20*.jsonl")
KPK = os.path.join(os.path.expanduser("~"), ".cache", "d503_studies", "cbb_knowledge_b_rows.pkl")
random.seed(1113)
CELLS = [0]


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def load_f():
    R = []
    for f in sorted(glob.glob(ROWS)):
        for line in open(f):
            r = json.loads(line)
            if r.get("result") not in ("won", "lost") or str(r.get("stype") or "2") != "2":
                continue
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            r["win"] = r["result"] == "won"
            r["pnl"] = (r["dec"] - 1) if r["win"] else -1.0
            r["mn"] = min(r.get("games_in") or 0, r.get("opp_games_in") or 0)
            o = r.get("ml_home_open" if r["side"] == "home" else "ml_away_open")
            r["open"] = None
            if r["market"] == "ml" and o not in ("", None):
                try:
                    r["open"] = (dec(o) - 1) if r["win"] else -1.0
                except (ValueError, ZeroDivisionError):
                    pass
            R.append(r)
    return R


def load_k():
    rows = pickle.load(open(KPK, "rb"))
    out = []
    for x in rows:
        if x.get("stype") != "2" or x.get("ml") is None or x.get("p") is None or x["season"] < 2018:
            continue
        x = dict(x)
        x["win"] = bool(x["won"])
        x["pnl"] = (dec(x["ml"]) - 1) if x["win"] else -1.0
        x["open"] = None if x.get("mlo") is None else ((dec(x["mlo"]) - 1) if x["win"] else -1.0)
        x["mn"] = min(x.get("gn") or 0, x.get("ogn") or 0)
        x["date"] = x["start"][:10]
        x["gid"] = x["id"]
        out.append(x)
    return out


def placebo(rows, pool, k="pnl", n=2000):
    """How many of n random sets of the same size and season mix from `pool` do as well as the cell."""
    if len(rows) < 30:
        return None
    by = defaultdict(list)
    for r in pool:
        by[r["season"]].append(r[k])
    need = defaultdict(int)
    for r in rows:
        need[r["season"]] += 1
    mine = sum(r[k] for r in rows)
    hit = 0
    for _ in range(n):
        tot = 0.0
        for s, c in need.items():
            if by[s]:
                tot += sum(random.choices(by[s], k=c)) if c > len(by[s]) else sum(random.sample(by[s], c))
        hit += tot >= mine
    return hit


def roi(rows, k="pnl"):
    rows = [r for r in rows if r.get(k) is not None]
    return (100 * sum(r[k] for r in rows) / len(rows), len(rows)) if rows else (float("nan"), 0)


def rec(name, rows, pool=None, k="pnl", min_n=20):
    """W-L, ROI at the price, z, TRAIN (2018-22) vs HELD (2023-26), seasons up, the open, the placebo."""
    if len(rows) < min_n:
        if rows:
            print(f"   {name:64s} only {len(rows)} ({sum(r['win'] for r in rows)}-{sum(not r['win'] for r in rows)}, {roi(rows)[0]:+.1f}%)")
        return None
    CELLS[0] += 1
    w = sum(r["win"] for r in rows)
    m = sum(r[k] for r in rows) / len(rows)
    sd = math.sqrt(sum((r[k] - m) ** 2 for r in rows) / len(rows)) or 1
    z = m / (sd / math.sqrt(len(rows)))
    tr, he = [r for r in rows if r["season"] <= 2022], [r for r in rows if r["season"] >= 2023]
    by = defaultdict(list)
    for r in rows:
        by[r["season"]].append(r[k])
    up = sum(sum(v) > 0 for v in by.values())
    pb = placebo(rows, pool) if pool is not None else None
    op = roi(rows, "open")
    print(f"   {name:64s} {w:4d}-{len(rows) - w:<4d} {100 * w / len(rows):4.1f}% ROI {100 * m:+6.1f}% z {z:+4.1f} | "
          f"train {roi(tr)[0]:+6.1f}% n{len(tr)} | held {roi(he)[0]:+6.1f}% n{len(he)} | up {up}/{len(by)}"
          + (f" | open {op[0]:+.1f}% n{op[1]}" if op[1] >= 15 else "")
          + (f" | placebo {pb}/2000" if pb is not None else "")
          + " | " + " ".join(f"{s % 100}:{100 * sum(v) / len(v):+.0f}" for s, v in sorted(by.items())))
    return {"n": len(rows), "roi": m, "z": z, "tr": roi(tr)[0], "he": roi(he)[0], "up": up, "ns": len(by), "pb": pb}


def per_night(rows, key, cap=1):
    """The best `cap` rows a day by key (one a game)."""
    byn = defaultdict(list)
    for r in rows:
        byn[r["date"]].append(r)
    out = []
    for v in byn.values():
        seen = set()
        for r in sorted(v, key=key, reverse=True):
            g = r.get("gid")
            if g in seen:
                continue
            seen.add(g)
            out.append(r)
            if len(seen) >= cap:
                break
    return out
