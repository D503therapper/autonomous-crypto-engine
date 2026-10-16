"""THE MLB OWN READ vs THE PRICE (10/16): is the engine's baseball read optimistic, by how much, and what would a
calibrated read have done?

Two "own reads" live in the engine and both get measured, each WALK-FORWARD (params tuned only on games before the
season half they grade, 3/1 and 7/1 each year 2018-26; the key-player edge is prior-starts-only by construction):
  raw   - sports_model.own_p: the ratings + form + the starter's form, no line at all. The early-price exam and the
          early scan (sports_early) use it, tuned on the last 3 seasons only (LEARN_Y).
  board - sports_model.final_p with move_w = 0: what sports.run calls ph_own (the market, moved toward the raw read by
          the learned trust, plus the learned favorite / home-dog shifts). own_agrees, the Lock test and every unit
          size on the board ride on it.

Tables (regular season and postseason apart, favorite / dog apart, starter form known or not):
  1. calibration by read bucket (the home side): what the read said vs what happened vs the market
  2. the side the read liked MORE than the market, by the gap: won %, the read, the market, ROI at the close
  3. the fitted fix: logit(cal) = logit(market) + a * (logit(read) - logit(market)), a fit on the seasons before
     each one (blind), and the same tables with the calibrated read
  4. the bare Lock rule replayed (read 56%+, beats its price, -150..+125, best value per day, quarter-Kelly by the
     read) before / after, by season, postseason apart
  5. the early-price exam band (+100..+149 dogs, raw read +8..12 over the OPEN) sized by the raw read vs by the
     calibrated read, and what the live Brewers / Guardians / Rays plays would have been
Run: python tools/mlb_read_calibration_study.py  -> results/mlb_read_calibration_study.json
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402
import sports_players as sp   # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "mlb_read_calibration_study.json")
CACHE = os.environ.get("MLB_CAL_CACHE") or os.path.join(os.path.dirname(OUT), "mlb_read_calibration_params.json")
YEARS = range(2018, 2027)
BLIND_FROM = "2023-01-01"          # graded blind: 2023-26 (the owner: the last 3 seasons + this one)
LEARN_Y = 3                        # the early scan's engine learns on the last 3 seasons only (sports_early.LEARN_Y)
LOCK_P, MAX_FAV, PLUS_LOCK_MAX = 0.56, -150, 125
BAND = (0.08, 0.12, 100, 149)      # the MLB exam band that passed 10/1-10/14
MOVED_MAX = 15


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def kelly(p, odds, cap=10.0):
    d = dec(odds)
    k = (p * d - 1) / (d - 1)
    return 0.0 if k <= 0 else min(cap, max(0.5, round(0.25 * k / 0.01 * 2) / 2))


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def cutoffs():
    out = []
    for y in YEARS:
        out.append(f"{y}-03-01")
        out.append(f"{y}-07-01")
    out.append("2027-03-01")
    return out


def tune_all(games):
    """{cutoff: {"full": params, "recent": params}} - every cutoff tuned on the finals before it only."""
    try:
        with open(CACHE) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    cuts = cutoffs()[:-1]
    for cut in cuts:
        if cut in cache:
            continue
        before = {k: g for k, g in games.items() if g["start"] < cut and g["status"] == "final"}
        full = sm.tune(before, "mlb")
        since = f"{int(cut[:4]) - LEARN_Y}{cut[4:]}"
        recent = sm.tune({k: g for k, g in before.items() if g["start"] >= since}, "mlb")
        cache[cut] = {"full": full, "recent": recent}
        with open(CACHE + ".tmp", "w") as f:
            json.dump(cache, f)
        os.replace(CACHE + ".tmp", CACHE)
        print(f"   tuned {cut}: trust {full['trust']:.3f} cal {full.get('cal', 0):.3f} hdog {full.get('hdog', 0):.3f} "
              f"key {full['weights']['key']:+.3f} | recent trust {recent['trust']:.3f}", flush=True)
    return cache


def rows(games, params):
    """One row per priced, decided real game 2018-26, with every read made walk-forward."""
    fin = sm.finals(games, "mlb")
    cuts = cutoffs()
    out = []
    for i, cut in enumerate(cuts[:-1]):
        nxt = cuts[i + 1]
        pf, pr = params[cut]["full"], params[cut]["recent"]
        _, played_f = sm.replay(fin, pf["k"], pf["hfa"], "mlb")
        _, played_r = sm.replay(fin, pr["k"], pr["hfa"], "mlb")
        feats_r = {g["id"]: f for g, f, *_ in played_r}
        for g, f, *_ in played_f:
            if not (cut <= g["start"] < nxt):
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            ch, ca = _int(g.get("ml_home")), _int(g.get("ml_away"))
            if hs == as_ or None in (ch, ca) or f.get("known", 0) < 3:
                continue
            mk = sm.market_p(g)
            oh, oa = _int(g.get("ml_home_open")), _int(g.get("ml_away_open"))
            real_open = None not in (oh, oa) and (oh, oa) != (ch, ca)
            out.append({
                "id": g["id"], "start": g["start"], "post": (g.get("stype") or "") == "3",
                "day": datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                .astimezone(PT).date().isoformat(),
                "home_won": hs > as_, "ch": ch, "ca": ca, "oh": oh if real_open else None, "oa": oa if real_open else None,
                "mkt": mk, "mkt_open": sm.market_p(g, open_line=True) if real_open else None,
                "raw": sm.own_p(pf, f), "board": sm.final_p({**pf, "move_w": 0.0}, f, g),
                "early": sm.own_p(pr, feats_r[g["id"]]),
                "sp_known": g["id"] in sm.KEY_EDGE,
            })
    out.sort(key=lambda r: (r["start"], r["id"]))
    return out


def fit_a(pairs):
    """pairs of (logit(read) - logit(market), logit(market), won) -> a (how much of the read's disagreement to keep)."""
    if len(pairs) < 200:
        return None
    X = [[d] for d, _, _ in pairs]
    off = [m for _, m, _ in pairs]
    y = [1.0 if w else 0.0 for _, _, w in pairs]
    return sm.fit_logistic_offset(X, y, off, prior=[0.0], lam=1.0)[0]


def shrink(read, mkt, a):
    return sm.sigmoid(sm.logit(mkt) + a * (sm.logit(read) - sm.logit(mkt)))


def add_calibrated(rs):
    """a per season (fit on every priced game BEFORE that season - blind), for each read."""
    fits = {}
    by_year = defaultdict(list)
    for r in rs:
        by_year[r["start"][:4]].append(r)
    for which in ("raw", "board", "early"):
        hist = []
        for y in sorted(by_year):
            a = fit_a(hist)
            fits.setdefault(which, {})[y] = None if a is None else round(a, 3)
            for r in by_year[y]:
                r[f"{which}_cal"] = r[which] if a is None else shrink(r[which], r["mkt"], a)
                hist.append((sm.logit(r[which]) - sm.logit(r["mkt"]), sm.logit(r["mkt"]), r["home_won"]))
    return fits


def _agg(items):
    """items: (read, mkt, won, dec) -> n, read, market, won, roi."""
    if not items:
        return {"n": 0}
    n = len(items)
    return {"n": n, "read": round(sum(i[0] for i in items) / n, 3), "market": round(sum(i[1] for i in items) / n, 3),
            "won": round(sum(i[2] for i in items) / n, 3),
            "roi": round(sum((i[3] - 1) if i[2] else -1 for i in items) / n, 4)}


def bucket_table(rs, which, blind_only=True):
    """Calibration by read bucket (home side), regular / postseason apart."""
    out = {}
    for post in (False, True):
        bins = defaultdict(list)
        for r in rs:
            if r["post"] != post or (blind_only and r["start"] < BLIND_FROM):
                continue
            p = r[which]
            b = min(0.70, max(0.30, int(p * 20) / 20))
            bins[f"{b:.2f}"].append((p, r["mkt"], r["home_won"], dec(r["ch"])))
        out["postseason" if post else "regular"] = {k: _agg(v) for k, v in sorted(bins.items())}
    return out


GAPS = ((0, 0.02), (0.02, 0.04), (0.04, 0.06), (0.06, 0.08), (0.08, 0.12), (0.12, 1.0))


def sides(r, which):
    """Both sides of a game as (read, mkt, won, dec, odds, side)."""
    return ((r[which], r["mkt"], r["home_won"], dec(r["ch"]), r["ch"], "home"),
            (1 - r[which], 1 - r["mkt"], not r["home_won"], dec(r["ca"]), r["ca"], "away"))


def gap_table(rs, which, period=None):
    """The side the read likes more than the market, by the gap - with the splits."""
    out = {}
    for post in (False, True):
        cells = defaultdict(list)
        for r in rs:
            if r["post"] != post:
                continue
            if period == "blind" and r["start"] < BLIND_FROM:
                continue
            if period == "train" and r["start"] >= BLIND_FROM:
                continue
            for p, m, won, d, o, _ in sides(r, which):
                gap = p - m
                if gap < 0:
                    continue
                for lo, hi in GAPS:
                    if lo <= gap < hi:
                        key = f"{lo * 100:.0f}-{hi * 100:.0f}" if hi < 1 else f"{lo * 100:.0f}+"
                        item = (p, m, won, d)
                        cells[("all", key)].append(item)
                        cells[("favorite" if o < 0 else "dog", key)].append(item)
                        cells[("starter known" if r["sp_known"] else "starter unknown", key)].append(item)
        tbl = defaultdict(dict)
        for (split, key), v in cells.items():
            tbl[split][key] = _agg(v)
        out["postseason" if post else "regular"] = {k: dict(sorted(v.items(), key=lambda kv: float(kv[0].rstrip("+").split("-")[0])))
                                                     for k, v in tbl.items()}
    return out


def optimism(rs, which, period="blind"):
    """One number: on the side the read likes more than the market, read minus what happened (points), by season."""
    out = {}
    by = defaultdict(list)
    for r in rs:
        if period == "blind" and r["start"] < BLIND_FROM:
            continue
        for p, m, won, d, o, _ in sides(r, which):
            if p > m:
                by[r["start"][:4]].append((p, m, won))
                by["all"].append((p, m, won))
                by["postseason" if r["post"] else "regular"].append((p, m, won))
    for k, v in sorted(by.items()):
        n = len(v)
        out[k] = {"n": n, "read": round(sum(x[0] for x in v) / n, 3), "market": round(sum(x[1] for x in v) / n, 3),
                  "won": round(sum(x[2] for x in v) / n, 3),
                  "read_minus_won_pts": round(100 * (sum(x[0] for x in v) - sum(x[2] for x in v)) / n, 1),
                  "market_minus_won_pts": round(100 * (sum(x[1] for x in v) - sum(x[2] for x in v)) / n, 1)}
    return out


def lock_replay(rs, which):
    """The bare Lock rule, one a day: read 56%+, -150..+125, the read beats the price AND the no-vig number; the most
    value first; quarter-Kelly by the read. -> by season, regular / postseason, units and ROI at the close."""
    by_day = defaultdict(list)
    for r in rs:
        for p, m, won, d, o, side in sides(r, which):
            if p >= LOCK_P and MAX_FAV <= o <= PLUS_LOCK_MAX and p * d - 1 > 0 and p >= m:
                by_day[(r["day"], r["post"])].append((p * d - 1, p, m, won, d, o, r["start"][:4]))
    res = defaultdict(lambda: {"n": 0, "won": 0, "units_bet": 0.0, "units_won": 0.0, "flat": 0.0})
    for (day, post), cands in by_day.items():
        v, p, m, won, d, o, y = max(cands)
        u = kelly(p, o)
        if u <= 0:
            continue
        for key in (f"{y} {'post' if post else 'reg'}", f"all {'post' if post else 'reg'}",
                    f"{'blind' if y >= BLIND_FROM[:4] else 'train'} {'post' if post else 'reg'}"):
            s = res[key]
            s["n"] += 1
            s["won"] += int(won)
            s["units_bet"] += u
            s["units_won"] += u * (d - 1) if won else -u
            s["flat"] += (d - 1) if won else -1
    out = {}
    for k, s in sorted(res.items()):
        out[k] = {"n": s["n"], "won": s["won"], "units_bet": round(s["units_bet"], 1), "units_won": round(s["units_won"], 1),
                  "roi_sized": round(s["units_won"] / s["units_bet"], 4) if s["units_bet"] else None,
                  "roi_flat": round(s["flat"] / s["n"], 4) if s["n"] else None,
                  "avg_units": round(s["units_bet"] / s["n"], 2) if s["n"] else None}
    return out


def exam_replay(rs, which_raw, which_cal):
    """The exam band at the OPEN price (dogs +100..+149 whose RAW early read is +8..12 over the open's no-vig number,
    the price not yet moved MOVED_MAX toward them): flat, sized by the raw read, sized by the calibrated read."""
    res = defaultdict(lambda: {"n": 0, "won": 0, "flat": 0.0, "u_raw": 0.0, "w_raw": 0.0, "u_cal": 0.0, "w_cal": 0.0,
                               "gap_raw": 0.0, "gap_cal": 0.0, "cal_in_band": 0})
    for r in rs:
        if r["oh"] is None:
            continue
        mo = r["mkt_open"]
        for side in ("home", "away"):
            o = r["oh"] if side == "home" else r["oa"]
            c = r["ch"] if side == "home" else r["ca"]
            if not BAND[2] <= o <= BAND[3] or (o - c) > MOVED_MAX:
                continue
            m = mo if side == "home" else 1 - mo
            p = r[which_raw] if side == "home" else 1 - r[which_raw]
            pc = r[which_cal] if side == "home" else 1 - r[which_cal]
            won = r["home_won"] if side == "home" else not r["home_won"]
            if not BAND[0] <= p - m < BAND[1]:
                continue
            d = dec(o)
            y = r["start"][:4]
            for key in (y, "all", "blind" if y >= BLIND_FROM[:4] else "train", "post" if r["post"] else "reg"):
                s = res[key]
                s["n"] += 1
                s["won"] += int(won)
                s["flat"] += (d - 1) if won else -1
                ur, uc = kelly(p, o), kelly(pc, o)
                s["u_raw"] += ur
                s["w_raw"] += ur * (d - 1) if won else -ur
                s["u_cal"] += uc
                s["w_cal"] += uc * (d - 1) if won else -uc
                s["gap_raw"] += p - m
                s["gap_cal"] += pc - m
                s["cal_in_band"] += int(BAND[0] <= pc - m < BAND[1])
    out = {}
    for k, s in sorted(res.items()):
        n = s["n"]
        out[k] = {"n": n, "won": s["won"], "roi_flat": round(s["flat"] / n, 4) if n else None,
                  "units_raw": round(s["u_raw"], 1), "won_raw": round(s["w_raw"], 1),
                  "roi_raw_sized": round(s["w_raw"] / s["u_raw"], 4) if s["u_raw"] else None,
                  "avg_units_raw": round(s["u_raw"] / n, 2) if n else None,
                  "units_cal": round(s["u_cal"], 1), "won_cal": round(s["w_cal"], 1),
                  "roi_cal_sized": round(s["w_cal"] / s["u_cal"], 4) if s["u_cal"] else None,
                  "avg_units_cal": round(s["u_cal"] / n, 2) if n else None,
                  "avg_gap_raw_pts": round(100 * s["gap_raw"] / n, 1) if n else None,
                  "avg_gap_cal_pts": round(100 * s["gap_cal"] / n, 1) if n else None,
                  "still_in_band_with_cal": s["cal_in_band"]}
    return out


LIVE = [   # the live plays since 10/2 that rode on the read (posted odds, the read the units rode on, the no-vig number)
    {"what": "Brewers +112 early (10/12, won)", "odds": 112, "read": 0.5373, "mkt": 0.4501, "kind": "exam", "which": "early"},
    {"what": "Brewers +144 early (10/14, won)", "odds": 144, "read": 0.4847, "mkt": 0.3917, "kind": "exam", "which": "early"},
    {"what": "Guardians -149 Lock 1u (10/5, lost)", "odds": -149, "read": (0.03135502477029539 + 1) / dec(-149), "mkt": 0.572,
     "kind": "lock", "which": "board"},
    {"what": "Rays -132 Lock 1/2u (10/13, won)", "odds": -132, "read": (0.016845649100902804 + 1) / dec(-132), "mkt": 0.544,
     "kind": "lock", "which": "board"},
]


def live_replay(fits):
    out = []
    for p in LIVE:
        a = fits[p["which"]].get("2026")
        cal = shrink(p["read"], p["mkt"], a) if a is not None else p["read"]
        gap_raw, gap_cal = p["read"] - p["mkt"], cal - p["mkt"]
        if p["kind"] == "exam":
            posts_raw = BAND[0] <= gap_raw < BAND[1]
            posts_cal = BAND[0] <= gap_cal < BAND[1]
        else:
            posts_raw = p["read"] >= LOCK_P and p["read"] >= p["mkt"] and p["read"] * dec(p["odds"]) - 1 > 0
            posts_cal = cal >= LOCK_P and cal >= p["mkt"] and cal * dec(p["odds"]) - 1 > 0
        out.append({**{k: v for k, v in p.items() if k != "which"}, "read": round(p["read"], 4), "a": a, "cal_read": round(cal, 4),
                    "gap_raw_pts": round(100 * gap_raw, 1), "gap_cal_pts": round(100 * gap_cal, 1),
                    "units_raw": kelly(p["read"], p["odds"]), "units_cal": kelly(cal, p["odds"]) if posts_cal else 0.0,
                    "posts_raw": posts_raw, "posts_cal": posts_cal})
    return out


def main():
    games = sd.load_games("mlb")
    sm.KEY_EDGE = sp.key_edges(games, sp.load())           # prior starts only, per game
    print(f"games {len(games)}, key edges {len(sm.KEY_EDGE)}", flush=True)
    params = tune_all(games)
    rs = rows(games, params)
    print(f"rows {len(rs)} ({sum(r['post'] for r in rs)} postseason)", flush=True)
    fits = add_calibrated(rs)
    res = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "games": len(rs),
           "postseason_games": sum(r["post"] for r in rs), "blind_from": BLIND_FROM,
           "params_by_cutoff": {c: {"trust": round(v["full"]["trust"], 3), "cal": round(v["full"].get("cal", 0), 3),
                                    "hdog": round(v["full"].get("hdog", 0), 3), "key_w": v["full"]["weights"]["key"],
                                    "elo_w": v["full"]["weights"]["elo"], "k": v["full"]["k"], "hfa": v["full"]["hfa"],
                                    "recent_trust": round(v["recent"]["trust"], 3)} for c, v in params.items()},
           "fit_a_by_season": fits,
           "optimism": {w: optimism(rs, w) for w in ("raw", "board", "early", "raw_cal", "board_cal", "early_cal")},
           "logloss_blind": {}, "buckets_blind": {}, "gaps": {}, "lock": {}, "exam": {}}
    blind = [r for r in rs if r["start"] >= BLIND_FROM]
    for w in ("mkt", "raw", "board", "early", "raw_cal", "board_cal", "early_cal"):
        res["logloss_blind"][w] = round(sm.logloss([(r[w], 1.0 if r["home_won"] else 0.0) for r in blind]), 4)
    for w in ("raw", "board", "early", "raw_cal", "board_cal", "early_cal"):
        res["buckets_blind"][w] = bucket_table(rs, w)
        res["gaps"][w] = {"train": gap_table(rs, w, "train"), "blind": gap_table(rs, w, "blind")}
        res["lock"][w] = lock_replay(rs, w)
    res["exam"] = {"raw_early_read": exam_replay(rs, "early", "early_cal"),
                   "board_read_as_the_gap": exam_replay(rs, "board", "board_cal")}
    res["live"] = live_replay(fits)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    # the short version
    print("\nlog loss blind:", res["logloss_blind"])
    print("a by season:", json.dumps(fits))
    for w in ("raw", "board", "early"):
        o = res["optimism"][w]
        print(f"{w}: liked side blind - read {o['all']['read']} won {o['all']['won']} market {o['all']['market']} "
              f"(+{o['all']['read_minus_won_pts']} pts over), reg {o['regular']['read_minus_won_pts']} post {o['postseason']['read_minus_won_pts']}")
    for w in ("raw", "board", "early"):
        print(f"\nGAPS {w} blind regular:", json.dumps(res["gaps"][w]["blind"]["regular"]["all"]))
        print(f"GAPS {w} blind post:", json.dumps(res["gaps"][w]["blind"]["postseason"]["all"]))
    for w in ("board", "board_cal", "raw", "raw_cal"):
        print(f"\nLOCK {w}:", json.dumps({k: v for k, v in res["lock"][w].items() if k.startswith(("all", "blind", "train"))}))
    print("\nEXAM raw early read:", json.dumps({k: v for k, v in res["exam"]["raw_early_read"].items() if k in ("all", "blind", "train", "reg", "post", "2025", "2026")}))
    print("\nLIVE:", json.dumps(res["live"], indent=0))
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
