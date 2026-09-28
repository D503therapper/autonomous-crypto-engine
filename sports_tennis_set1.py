"""🎾 THE FIRST-SET STUDY (RESEARCH ONLY - nothing here changes a pick or the dashboard).

The crew's idea: players who win the first set a lot might be mispriced in FIRST-SET WINNER markets. We have no
historical first-set prices, so:

1) THE IMPLIED FIRST-SET PRICE. For every match with a Pinnacle closing price (data/sports/tennis/hist_odds.csv.gz),
   the no-vig match chance goes through the tour's Markov model (sports_tennis_live: tour-average serve-point
   chance +/- d, d solved so the match chance fits, best of 3 or 5, a 10-point final-set tiebreak at the Slams) and
   out comes the model's P(win the first set) - what a book pricing its first-set line from the match odds would
   charge. Calibration first: log loss vs the actual first sets per tour, a reliability table by price, and a
   logistic recalibration (slope / intercept on the logit) learned on the older half and graded on the newer.
2) THE CREW'S STAT, walk-forward (a day's matches only see earlier days), per tour: a player's first-set win rate
   over his last 20 priced matches (10 needed) minus what the implied first-set chances predicted in those matches
   ("first-set overperformer"), and the raw first-set win rate. When A's stat minus B's clears a threshold, back A
   to win the first set: n, hit rate vs the implied chance, z of the result over the implied chance, and the ROI at
   the implied fair price with a 5% margin taken out (decimal odds 1 / (p * 1.05)) - older / newer half.
   PROOF BAR (same as ours): n >= 300, profit in BOTH halves, z >= 3.5. Research only regardless.
3) THE REAL PRICES. sports_tennis captures Bovada's first-set markets before the start (set1_lines.json). Once 300+
   of those lines are matched to a finished first set, the same stat is graded at Bovada's real first-set price
   (and Bovada's first-set line is compared with the Markov price from its own match line).
Everything goes to data/sports/tennis/set1.json. Runs in well under 2 minutes (the Markov model is tabulated once
per tour / best-of / final tiebreak and interpolated)."""
import bisect
import json
import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from functools import lru_cache

import sports_data as sd
import sports_tennis as stn
import sports_tennis_edge as te
import sports_tennis_live as stl

DIR = os.path.join(sd.DATA, "tennis")
HIST = te.HIST
OUT = os.path.join(DIR, "set1.json")
SET1_LINES = stn.SET1_LINES
MATCHES = stn.MATCHES

WINDOW, MIN_HIST = 20, 10           # the crew's stat: the last 20 priced matches, 10 needed
MARGIN = 0.05                       # a book pricing its first-set line from the match odds, with a 5% margin
MIN_N, Z_PROVEN = 300, 3.5          # the proof bar
REAL_MIN = 300                      # matched real first-set lines before the real-price test runs
OVER_T = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
RAW_T = (0.10, 0.20, 0.30, 0.40, 0.50)
BUCKETS = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.01)
GRID = 0.002                        # the serve-point offset grid (d from -0.25 to +0.25)


# ---------------------------------------------------------------- the implied first-set chance
def set1_from_serve(pa, pb):
    """A wins the first set (7-point tiebreak at 6-6), serve-point chances pa / pb, the first server a coin flip."""
    pa, pb = round(pa, 5), round(pb, 5)
    x, y = stl.set_dist(pa, pb, 0, 0, True, 7), stl.set_dist(pa, pb, 0, 0, False, 7)
    return 0.5 * (x[0] + x[1] + y[0] + y[1])


def set1_exact(p_match, tour="atp", bo=3, final_tb=7):
    """Straight from sports_tennis_live.serve_split (slow: the bisection every time) - the reference."""
    pa, pb = stl.serve_split(round(p_match, 4), tour, bo, final_tb)
    return set1_from_serve(pa, pb)


@lru_cache(maxsize=16)
def _table(tour, bo, final_tb):
    """(match chances ascending, first-set chances) over the serve_split family base +/- d."""
    base = stl.SERVE[stn.tour_of(tour)]
    n = int(round(0.25 / GRID))
    pm, ps = [], []
    for i in range(-n, n + 1):
        pa, pb = round(base + i * GRID, 5), round(base - i * GRID, 5)
        pm.append(stl.live_p(pa, pb, bo=bo, final_tb=final_tb))
        ps.append(set1_from_serve(pa, pb))
    return pm, ps


def set1_p(p_match, tour="atp", bo=3, final_tb=7):
    """The implied P(win the first set) from the no-vig match chance (the tour's Markov model, interpolated)."""
    pm, ps = _table(stn.tour_of(tour), 5 if int(bo or 3) == 5 else 3, int(final_tb))
    p = min(max(p_match, pm[0]), pm[-1])
    i = min(max(bisect.bisect_left(pm, p), 1), len(pm) - 1)
    w = (p - pm[i - 1]) / ((pm[i] - pm[i - 1]) or 1e-12)
    return ps[i - 1] + w * (ps[i] - ps[i - 1])


# ---------------------------------------------------------------- the history
def rows_of(ms):
    """Priced matches with a finished first set -> [(date, tour, W, L, W won set 1, W's implied set-1 chance, bo,
    W's no-vig match chance)] oldest first."""
    out = []
    for m in ms:
        if m.status == "void" or not m.fw or not m.sets or not te._done(*m.sets[0]):
            continue
        ftb = stl.final_tb_of(m.tourney)
        out.append((m.d, m.tour, m.W, m.L, 1 if m.sets[0][0] > m.sets[0][1] else 0, set1_p(m.fw, m.tour, m.bo, ftb),
                    m.bo, m.fw))
    return out


def _ll(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def _logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def slope_of(pairs):
    """Symmetric logistic recalibration y ~ sigmoid(b * logit(p)) (Newton steps). Symmetric on purpose: the history
    lists the MATCH WINNER first, so an intercept would learn the result, not the price."""
    b = 1.0
    for _ in range(30):
        g = h = 0.0
        for p, y in pairs:
            x = _logit(p)
            q = 1 / (1 + math.exp(-b * x))
            g += (y - q) * x
            h += q * (1 - q) * x * x
        if h <= 1e-12:
            break
        step = g / h
        b += step
        if abs(step) < 1e-9:
            break
    return b


def recal(p, b):
    return 1 / (1 + math.exp(-b * _logit(p)))


def calibration(rows, split):
    """Per tour: log loss of the implied first-set chance (and of naive stand-ins), a reliability table (from the
    first-set favorite's side) and an older-half recalibration graded on the newer half."""
    out = {}
    for tour in sorted({r[1] for r in rows}):
        rs = [r for r in rows if r[1] == tour]
        n = len(rs)
        ll = sum(_ll(r[5], r[4]) for r in rs) / n
        ll_match = sum(_ll(r[7], r[4]) for r in rs) / n          # the match chance used as the first-set chance
        tbl = []
        for lo, hi in zip(BUCKETS, BUCKETS[1:]):
            got = [(r[5], r[4]) if r[5] >= 0.5 else (1 - r[5], 1 - r[4]) for r in rs]
            got = [(p, y) for p, y in got if lo <= p < hi]
            if not got:
                continue
            k = len(got)
            ep, hit = sum(p for p, _ in got) / k, sum(y for _, y in got) / k
            var = sum(p * (1 - p) for p, _ in got)
            tbl.append({"bucket": f"{int(lo * 100)}-{min(int(hi * 100), 100)}%", "n": k, "implied": round(ep, 4),
                        "actual": round(hit, 4), "z": round((hit - ep) * k / math.sqrt(var), 2) if var else 0.0})
        rec = {}
        for bo in (3, 5):
            old = [(r[5], r[4]) for r in rs if r[0] < split and r[6] == bo]
            new = [(r[5], r[4]) for r in rs if r[0] >= split and r[6] == bo]
            if len(old) < 500 or len(new) < 500:
                continue
            b = slope_of(old)
            ll_new = sum(_ll(p, y) for p, y in new) / len(new)
            ll_rec = sum(_ll(recal(p, b), y) for p, y in new) / len(new)
            k = len(new)
            d = [_ll(p, y) - _ll(recal(p, b), y) for p, y in new]
            mu = sum(d) / k
            sdv = math.sqrt(sum((x - mu) ** 2 for x in d) / (k - 1)) if k > 1 else 0
            rec[f"bo{bo}"] = {"slope_learned_on_older": round(b, 4), "newer_logloss": round(ll_new, 5),
                              "newer_logloss_recalibrated": round(ll_rec, 5), "gain_mnats": round(mu * 1000, 2),
                              "gain_z": round(mu / (sdv / math.sqrt(k)), 2) if sdv else 0.0}
        by_bo = {}
        for bo in (3, 5):
            b_rs = [r for r in rs if r[6] == bo]
            if b_rs:
                by_bo[f"bo{bo}"] = {"n": len(b_rs), "logloss": round(sum(_ll(r[5], r[4]) for r in b_rs) / len(b_rs), 5),
                                    "implied_fav": round(sum(max(r[5], 1 - r[5]) for r in b_rs) / len(b_rs), 4),
                                    "actual_fav": round(sum((r[4] if r[5] >= 0.5 else 1 - r[4]) for r in b_rs) / len(b_rs), 4)}
        out[tour] = {"n": n, "logloss": round(ll, 5), "logloss_match_p_as_set1": round(ll_match, 5),
                     "logloss_coinflip": round(math.log(2), 5), "reliability": tbl, "recalibration": rec, "by_bo": by_bo}
    return out


# ---------------------------------------------------------------- the crew's stat, walk-forward
def _stat(h):
    """(first-set overperformance, raw first-set rate) from a player's recent (won, implied) - None under MIN_HIST."""
    if len(h) < MIN_HIST:
        return None
    k = len(h)
    return sum(y - p for y, p in h) / k, sum(y for y, _ in h) / k


def walk(rows):
    """Walk-forward: every match gets both players' stats from EARLIER DAYS only (a whole day is scored before any
    of its results is learned). -> ([(date, tour, W's stat, L's stat, W won set 1, W's implied)], histories)
    histories: {(tour, name): [(date, won, implied)]} for the real-price hook."""
    recent, full, out = {}, {}, []
    i = 0
    while i < len(rows):
        d = rows[i][0]
        j = i
        while j < len(rows) and rows[j][0] == d:
            j += 1
        day = rows[i:j]
        for r in day:
            sw, sl = _stat(recent.get((r[1], r[2]), ())), _stat(recent.get((r[1], r[3]), ()))
            if sw and sl:
                out.append((d, r[1], sw, sl, r[4], r[5], r[6]))
        for r in day:                                            # ...only now learn the day's results
            for who, y, p in ((r[2], r[4], r[5]), (r[3], 1 - r[4], 1 - r[5])):
                recent.setdefault((r[1], who), deque(maxlen=WINDOW)).append((y, p))
                full.setdefault((r[1], who), []).append((d, y, p))
        i = j
    return out, full


class Acc:
    def __init__(self):
        self.n = self.won = 0
        self.ep = self.var = self.pnl = self.ep2 = self.var2 = 0.0

    def add(self, y, p, dec, p2=None):
        self.n += 1
        self.won += y
        self.ep += p
        self.var += p * (1 - p)
        self.pnl += (dec - 1) if y else -1.0
        p2 = p if p2 is None else p2
        self.ep2 += p2
        self.var2 += p2 * (1 - p2)

    def rep(self):
        if not self.n:
            return {"n": 0}
        return {"n": self.n, "hit": round(self.won / self.n, 4), "implied": round(self.ep / self.n, 4),
                "z": round((self.won - self.ep) / math.sqrt(self.var), 2) if self.var else 0.0,
                "roi": round(self.pnl / self.n, 4),
                "recal_implied": round(self.ep2 / self.n, 4),
                "z_vs_recal": round((self.won - self.ep2) / math.sqrt(self.var2), 2) if self.var2 else 0.0}


def crew_test(bets, split, idx, thresholds, margin=MARGIN, slopes=None):
    """bets: walk() rows of one tour; idx 0 = overperformance, 1 = raw rate. Back the player whose stat is higher by
    `t`+ to win the first set at the implied fair price with the margin taken out (decimal 1 / (p * (1 + margin))).
    slopes {bo: b}: also grade against the recalibrated implied chance (the model's own favorite bias taken out -
    learned on the older half, so the older half's z_vs_recal is in-sample)."""
    res = {}
    for t in thresholds:
        acc = {"all": Acc(), "older": Acc(), "newer": Acc()}
        for d, _, sw, sl, y, p, bo in bets:
            diff = sw[idx] - sl[idx]
            if abs(diff) < t or diff == 0:
                continue
            yy, pp = (y, p) if diff > 0 else (1 - y, 1 - p)
            dec = 1 / (pp * (1 + margin))
            p2 = recal(pp, slopes[bo]) if slopes and bo in slopes else None
            for k in ("all", "older" if d < split else "newer"):
                acc[k].add(yy, pp, dec, p2)
        r = {k: v.rep() for k, v in acc.items()}
        a = r["all"]
        r["proven"] = bool(a["n"] >= MIN_N and a.get("z", 0) >= Z_PROVEN and r["older"].get("roi", -1) > 0
                           and r["newer"].get("roi", -1) > 0)
        res[f"{t:.2f}"] = r
    return res


def closest(res):
    """The threshold nearest the bar: n >= 300 first, then the highest z; with what it still misses."""
    best = None
    for t, r in res.items():
        a = r["all"]
        if not a["n"]:
            continue
        key = (a["n"] >= MIN_N, a.get("z", -99))
        if best is None or key > best[0]:
            best = (key, t, r)
    if not best:
        return None
    _, t, r = best
    miss = []
    if r["all"]["n"] < MIN_N:
        miss.append(f"n {r['all']['n']} < {MIN_N}")
    if r["all"].get("z", 0) < Z_PROVEN:
        miss.append(f"z {r['all'].get('z')} < {Z_PROVEN}")
    for h in ("older", "newer"):
        if r[h].get("roi", -1) <= 0:
            miss.append(f"{h} ROI {r[h].get('roi')} <= 0")
    return {"threshold": t, **r["all"], "older_roi": r["older"].get("roi"), "newer_roi": r["newer"].get("roi"),
            "misses": miss or ["nothing - PROVEN (research only)"]}


# ---------------------------------------------------------------- the real Bovada first-set prices
def _dec(am):
    return 1 + (am / 100 if am > 0 else 100 / -am)


def _nv(a, b):
    ia, ib = 1 / _dec(a), 1 / _dec(b)
    return ia / (ia + ib)


def bov_key(name):
    """'Jannik Sinner' -> ('sinner', 'j') - the history's ('Sinner J.') key."""
    t = stn._norm(name)
    return (" ".join(t[1:]), t[0][0]) if len(t) >= 2 else None


def _hist_index(full):
    """{(tour, surname, initial): [(date, won, implied)]} - only unambiguous (surname, initial) keys."""
    idx, clash = {}, set()
    for (tour, name), h in full.items():
        k = te._td_key(name)
        if not k:
            continue
        kk = (tour, *k)
        if kk in idx:
            clash.add(kk)
        idx[kk] = h
    return {k: v for k, v in idx.items() if k not in clash}


def _stat_at(idx, tour, name, day):
    k = bov_key(name)
    h = idx.get((tour, *k)) if k else None
    if not h:
        return None
    i = bisect.bisect_left([x[0] for x in h], day)
    return _stat([(y, p) for _, y, p in h[max(0, i - WINDOW):i]])


def real_study(lines, matches, full):
    """Bovada's captured first-set lines, matched to finished matches (ESPN results): how Bovada's first-set price
    compares with the Markov price from its own match line, and - once REAL_MIN are matched - the crew's stat at
    Bovada's real first-set price."""
    lines = [v for v in (lines or {}).values() if "a_s1" in v and "b_s1" in v]
    out = {"lines": len(lines), "min_needed": REAL_MIN}
    if not lines:
        return {**out, "matched": 0, "waiting": True}
    lo = min(v["start"] for v in lines)[:10]
    done = [m for m in matches if str(m.get("status")) == "STATUS_FINAL" and m.get("start", "") >= lo
            and m.get("sets1") and m.get("sets2")]
    idx = _hist_index(full)
    graded, gaps = [], []
    for m in done:
        ln, flip = stn.match_line(m, lines)
        if ln is None:
            continue
        try:
            g1, g2 = int(str(m["sets1"]).split()[0]), int(str(m["sets2"]).split()[0])
        except (ValueError, IndexError):
            continue
        if not te._done(g1, g2):
            continue                                              # (a retirement inside the first set: void)
        a_won = (g1 > g2) != flip                                 # did line side a win the first set?
        tour = stn.tour_of(m)
        p_a = _nv(ln["a_s1"], ln["b_s1"])
        if "a_ml" in ln and "b_ml" in ln:
            gaps.append(p_a - set1_p(_nv(ln["a_ml"], ln["b_ml"]), tour, int(m.get("bo") or 3)))
        day = m["start"][:10]
        graded.append((day, tour, _stat_at(idx, tour, ln["a"], day), _stat_at(idx, tour, ln["b"], day), a_won, p_a,
                       ln["a_s1"], ln["b_s1"]))
    out.update({"matched": len(graded), "waiting": len(graded) < REAL_MIN})
    if gaps:
        out["bovada_set1_vs_markov_from_its_match_line"] = {
            "n": len(gaps), "mean_gap": round(sum(gaps) / len(gaps), 4),
            "mean_abs_gap": round(sum(abs(g) for g in gaps) / len(gaps), 4)}
    if len(graded) < REAL_MIN:
        return out
    days = sorted(g[0] for g in graded)
    split = days[len(days) // 2]
    tests = {}
    for tour in ("atp", "wta"):
        for name, idx_s, ths in (("overperformance", 0, OVER_T), ("raw_rate", 1, RAW_T)):
            res = {}
            for t in ths:
                acc = {"all": Acc(), "older": Acc(), "newer": Acc()}
                for d, tr, sa, sb, y, p, am_a, am_b in graded:
                    if tr != tour or not sa or not sb:
                        continue
                    diff = sa[idx_s] - sb[idx_s]
                    if abs(diff) < t or diff == 0:
                        continue
                    yy, pp, am = (y, p, am_a) if diff > 0 else (not y, 1 - p, am_b)
                    for k in ("all", "older" if d < split else "newer"):
                        acc[k].add(int(yy), pp, _dec(am))
                r = {k: v.rep() for k, v in acc.items()}
                r["proven"] = bool(r["all"]["n"] >= MIN_N and r["all"].get("z", 0) >= Z_PROVEN
                                   and r["older"].get("roi", -1) > 0 and r["newer"].get("roi", -1) > 0)
                res[f"{t:.2f}"] = r
            tests[f"{tour}|{name}"] = {"thresholds": res, "closest": closest(res)}
    out["tests"] = tests
    out["split"] = split
    return out


# ---------------------------------------------------------------- the run
def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _load_matches(path):
    import csv
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def study(path=OUT, hist=HIST, lines_path=SET1_LINES, matches_path=MATCHES, verbose=True):
    """The whole study -> set1.json. Research only: nothing reads it for picks."""
    t0 = time.time()
    log = print if verbose else (lambda *a, **k: None)
    ms = te.read_hist(hist)
    rows = rows_of(ms)
    prev = _load(path)
    rep = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "research_only": True,
           "rows": len(rows), "proven": []}
    if len(rows) < 1000:
        rep["skipped"] = f"only {len(rows)} priced matches with a finished first set"
        _save(path, rep)
        return rep
    bets, full = walk(rows)
    split = prev.get("split")
    if not split:                                              # fixed the first time: never moves
        ds = sorted(b[0] for b in bets) or sorted(r[0] for r in rows)
        split = ds[len(ds) // 2]
    rep["split"] = split
    rep["calibration"] = calibration(rows, split)
    rep["crew"] = {}
    for tour in sorted({r[1] for r in rows}):
        tb = [b for b in bets if b[1] == tour]
        slopes = {int(k[2:]): v["slope_learned_on_older"] for k, v in rep["calibration"][tour]["recalibration"].items()}
        over, raw = crew_test(tb, split, 0, OVER_T, slopes=slopes), crew_test(tb, split, 1, RAW_T, slopes=slopes)
        rep["crew"][tour] = {"bets_with_both_stats": len(tb), "overperformance": over, "raw_rate": raw,
                             "closest": {"overperformance": closest(over), "raw_rate": closest(raw)}}
        rep["proven"] += [f"{tour}|overperformance>={t}" for t, r in over.items() if r["proven"]]
        rep["proven"] += [f"{tour}|raw_rate>={t}" for t, r in raw.items() if r["proven"]]
    rep["real"] = real_study(_load(lines_path), _load_matches(matches_path), full)
    rep["secs"] = round(time.time() - t0, 1)
    _save(path, rep)
    for tour, c in rep["calibration"].items():
        log(f"first set {tour.upper()}: {c['n']} matches, implied log loss {c['logloss']} (match chance as set-1 "
            f"chance {c['logloss_match_p_as_set1']}, coin {c['logloss_coinflip']})")
        for k, v in rep["crew"][tour]["closest"].items():
            if v:
                log(f"  crew {k}: closest >= {v['threshold']}: n {v['n']}, hit {v['hit']} vs implied {v['implied']}, "
                    f"z {v['z']} (vs recalibrated {v.get('z_vs_recal')}), ROI {v['roi']} (older {v['older_roi']}, newer {v['newer_roi']}) - {'; '.join(v['misses'])}")
    log(f"first set real Bovada lines: {rep['real'].get('lines')} captured, {rep['real'].get('matched')} matched "
        f"(test runs at {REAL_MIN}) · {rep['secs']}s")
    return rep


def _save(path, rep):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(rep, f, indent=1)
    os.replace(path + ".tmp", path)


if __name__ == "__main__":
    study()
