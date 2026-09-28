"""🎾 THE HEAVY-FAVORITES STUDY (RESEARCH ONLY - nothing here changes a pick, a rule or the dashboard).

The crew's question: are heavy tennis favorites lucrative - especially the ones our engine likes - and 3-leg
parlays of them (three ~-150 legs pay about +363)?

Data: data/sports/tennis/hist_odds.csv.gz (ATP + WTA since 2012, closing prices), read by sports_tennis_edge.
Walkovers are void (left out); a retirement stands for whoever advanced once a set was finished. Same older / newer
split date as the tennis edge study (edge.json), and the same walk-forward model (surface-blended Elo + fatigue /
retirements / layoff, the "model" and the "blend" into Pinnacle's fair price, weights cross-fit: each half is
predicted with weights learned on the OTHER half).

1) STRAIGHTS, per tour and book (Pinnacle = the sharp close; Bet365 = the soft-book proxy for what the crew can get):
   the favorite at that book, banded by its American price (-101..-150, -151..-200, -201..-300, -301..-500, -500+),
   overall and split by best-of-3 / best-of-5 and level (Slam / 1000 / other). n, win% vs that book's no-vig
   chance, ROI at that book's closing price, edge z (result minus the no-vig chance), older / newer half.
2) ENGINE-LIKED: the same, only favorites where the model (or the blend) beats that book's no-vig chance by 2%+ / 4%+.
3) PARLAYS: each day, per tour (never mixed), the 3 likeliest favorites (by that book's no-vig chance) priced
   -101 to the cap (-150 / -200 / -300), one leg per match; all favorites or engine-liked only. Tickets, hit rate vs
   the fair hit rate, ROI at the real closing prices (product of the decimals), older / newer.
4) PROOF BAR for "lucrative": profit in BOTH halves, n >= 300 (tickets for parlays), edge z >= 3.5 for straights.
   Expected false positives: tests x the one-sided luck odds of z 3.5 for straights; for parlays (no z bar) the
   chance a no-edge strategy at Pinnacle's fair prices still shows a profit in both halves, summed over the tests.

Everything goes to data/sports/tennis/favs.json. Runs in well under a minute."""
import json
import math
import os
import time
import zlib
from datetime import datetime, timezone

import sports_data as sd
import sports_model as sm
import sports_tennis_edge as te

DIR = os.path.join(sd.DATA, "tennis")
HIST = te.HIST
OUT = os.path.join(DIR, "favs.json")
EDGE = te.PATH

MIN_N, Z_PROVEN = 300, 3.5
P_LUCK = 0.5 * math.erfc(Z_PROVEN / math.sqrt(2))
BOOKS = ("pin", "b365")
BANDS = (("-101..-150", 101, 150), ("-151..-200", 151, 200), ("-201..-300", 201, 300), ("-301..-500", 301, 500),
         ("-500+", 501, 10 ** 9))
CAPS = (150, 200, 300)
LIKED = (("model", 0.02), ("model", 0.04), ("blend", 0.02), ("blend", 0.04))
LEGS = 3


def american(dec):
    """Decimal -> American (favorites negative, rounded); None for evens or longer."""
    if not dec or dec >= 2.0 or dec <= 1.0:
        return None
    return -round(100 / (dec - 1))


def band_of(dec):
    a = american(dec)
    if a is None:
        return None
    return next((name for name, lo, hi in BANDS if lo <= -a <= hi), None)


def level3(lvl):
    return lvl if lvl in ("slam", "1000") else "other"


def _phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


# ---------------------------------------------------------------- the model (same features / fit as model_study)
def model_probs(facts, split):
    """{id(m): {"model": p(W wins), "blend": p(W wins)}} - cross-fit, like sports_tennis_edge.model_study.
    Empty when either half has fewer than 500 rated matches."""
    rows = []
    for m in facts:
        f = m.fx
        if not f or not f["known"] or f["eW"] is None:
            continue
        flip = zlib.crc32(f"{m.d}{m.W}{m.L}".encode()) & 1
        sgn = -1 if flip else 1
        pa = 1 - m.fw if flip else m.fw
        ea = 1 - f["eW"] if flip else f["eW"]
        x = [sm.logit(pa), sm.logit(ea), sgn * (f["gL"] - f["gW"]) / 30, sgn * (f["rL"] - f["rW"]),
             sgn * (f["lL"] - f["lW"])]
        rows.append((m, flip, x, 0 if flip else 1, 1 if m.d >= split else 0))
    halves = [[r for r in rows if not r[4]], [r for r in rows if r[4]]]
    if min(len(h) for h in halves) < 500:
        return {}, {}
    fits = {}
    for h in (0, 1):
        tr = halves[h]
        fits[("model", h)] = sm.fit_logistic_offset([r[2][1:] for r in tr], [r[3] for r in tr], [0.0] * len(tr),
                                                    prior=[1.0, 0.0, 0.0, 0.0], lam=5.0, iters=8)
        fits[("blend", h)] = sm.fit_logistic_offset([r[2] for r in tr], [r[3] for r in tr], [0.0] * len(tr),
                                                    prior=[1.0, 0.0, 0.0, 0.0, 0.0], lam=5.0, iters=8)
    out = {}
    for m, flip, x, _, h in rows:
        d = {}
        for kind in ("model", "blend"):
            w = fits[(kind, 1 - h)]
            q = sm.sigmoid(sum(a * b for a, b in zip(w, x[1:] if kind == "model" else x)))
            d[kind] = 1 - q if flip else q
        out[id(m)] = d
    return out, {k[0] + ("_fit_on_older" if k[1] == 0 else "_fit_on_newer"): [round(v, 3) for v in w]
                 for k, w in fits.items()}


# ---------------------------------------------------------------- one favorite per match per book
def favorites(facts, probs, book, split):
    """[(m, side, dec, fair_book, fair_pin, won, new, band, liked set)] - the favorite at that book's close."""
    out = []
    for m in facts:
        o = m.odds.get(book)
        if not o or o[0] == o[1]:
            continue
        side = 0 if o[0] < o[1] else 1
        dec = o[side]
        band = band_of(dec)
        if band is None:
            continue
        nvW = te._nv(*o)
        fair = nvW if side == 0 else 1 - nvW
        fpin = m.fw if side == 0 else 1 - m.fw
        liked = set()
        p = probs.get(id(m))
        if p:
            for kind, t in LIKED:
                q = p[kind] if side == 0 else 1 - p[kind]
                if q - fair >= t:
                    liked.add(f"{kind}+{int(t * 100)}%")
        out.append((m, side, dec, fair, fpin, 1 if side == 0 else 0, m.d >= split, band, liked))
    return out


def _stats(acc):
    s = acc.out()
    if not s["n"]:
        return None
    r = {k: s[k] for k in ("n", "win", "fair", "edge", "z_edge", "roi", "z", "fair_pin", "z_pin")}
    for h, name in ((0, "old"), (1, "new")):
        x = acc.out(h)
        r[name] = {k: x[k] for k in ("n", "win", "fair", "roi", "z_edge")} if x["n"] else {"n": 0, "roi": 0.0}
    return r


def passes(s):
    return bool(s and s["n"] >= MIN_N and s["old"]["n"] and s["new"]["n"] and s["old"]["roi"] > 0
                and s["new"]["roi"] > 0 and s["z_edge"] >= Z_PROVEN)


def straights(favs, universes):
    """{universe: {band: {slice: stats}}} for one tour + book. Slices: all, bo3, bo5, slam, 1000, other."""
    acc = {}
    for m, side, dec, fair, fpin, won, new, band, liked in favs:
        for u in universes:
            if u != "all" and u not in liked:
                continue
            for sl in ("all", f"bo{m.bo}", level3(m.lvl)):
                a = acc.setdefault(u, {}).setdefault(band, {}).setdefault(sl, te.Acc())
                a.add(won, fair, (dec - 1) if won else -1.0, fpin, new)
    out = {}
    for u in universes:
        out[u] = {}
        for band, _, _ in BANDS:
            sl = acc.get(u, {}).get(band, {})
            out[u][band] = {k: _stats(sl[k]) for k in ("all", "bo3", "bo5", "slam", "1000", "other")
                            if k in sl and sl[k].out()["n"]}
    return out


# ---------------------------------------------------------------- parlays
def tickets(favs, cap, universe):
    """Each day: the 3 likeliest favorites priced -101..-cap (by the book's no-vig chance), one leg per match.
    [(day, [legs])] with a leg = (m, dec, fair, fair_pin, won)."""
    lo_dec = 1 + 100 / cap
    days = {}
    for m, side, dec, fair, fpin, won, new, band, liked in favs:
        if dec < lo_dec - 1e-9 or (universe != "all" and universe not in liked):
            continue
        days.setdefault(m.d, []).append((m, dec, fair, fpin, won))
    out = []
    for d in sorted(days):
        c = sorted(days[d], key=lambda x: (-x[2], x[0].W, x[0].L))
        legs, seen = [], set()
        for leg in c:
            k = (leg[0].W, leg[0].L, leg[0].tkey)
            if k in seen:                                   # never two legs from the same match
                continue
            seen.add(k)
            legs.append(leg)
            if len(legs) == LEGS:
                break
        if len(legs) == LEGS:
            out.append((d, legs))
    return out


def parlay_stats(tk, split):
    """Tickets, hit rate vs fair, ROI at the real prices, z of the profit; per half, plus the luck odds that a
    no-edge strategy (the truth = Pinnacle's fair chances) shows a profit in that half."""
    res = {}
    for name, sel in (("all", lambda d: True), ("old", lambda d: d < split), ("new", lambda d: d >= split)):
        rows = [legs for d, legs in tk if sel(d)]
        n = len(rows)
        if not n:
            res[name] = {"tickets": 0}
            continue
        pr, hits, fair, mu, var = [], 0, 0.0, 0.0, 0.0
        for legs in rows:
            dec = math.prod(x[1] for x in legs)
            won = all(x[4] for x in legs)
            q = math.prod(x[3] for x in legs)
            hits += won
            fair += math.prod(x[2] for x in legs)
            pr.append(dec - 1 if won else -1.0)
            mu += dec * q - 1
            var += dec * dec * q * (1 - q)
        roi = sum(pr) / n
        sd_ = math.sqrt(sum((p - roi) ** 2 for p in pr) / (n - 1)) if n > 1 else 0.0
        res[name] = {"tickets": n, "hit": round(hits / n, 4), "fair_hit": round(fair / n, 4), "roi": round(roi, 4),
                     "z": round(roi / (sd_ / math.sqrt(n)), 2) if sd_ > 0 else 0.0,
                     "avg_payout_american": round(100 * (sum(math.prod(x[1] for x in legs) for legs in rows) / n - 1)),
                     "p_profit_if_no_edge": round(_phi(mu / math.sqrt(var)), 4) if var > 0 else 0.0}
    a = res["all"]
    a["proven"] = bool(a.get("tickets", 0) >= MIN_N and res["old"].get("tickets") and res["new"].get("tickets")
                       and res["old"]["roi"] > 0 and res["new"]["roi"] > 0)
    return res


# ---------------------------------------------------------------- the run
def _split(edge_path, ms):
    try:
        with open(edge_path) as f:
            s = json.load(f).get("split")
        if s:
            return s
    except (OSError, ValueError):
        pass
    return te._median_date(ms)


def study(path=OUT, hist=HIST, edge_path=EDGE, split=None, verbose=True):
    t0 = time.time()
    log = print if verbose else (lambda *a, **k: None)
    ms = te.read_hist(hist)
    rep = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "research_only": True, "proven": []}
    if len(ms) < 1000:
        rep["skipped"] = f"only {len(ms)} matches in the history"
        _save(path, rep)
        return rep
    split = split or _split(edge_path, ms)
    _, facts = te.build(ms)
    probs, weights = model_probs(facts, split)
    rep["split"] = split
    rep["data"] = {"matches": len(ms), "priced": len(facts), "from": facts[0].d if facts else None,
                   "to": facts[-1].d if facts else None, "rated_for_model": len(probs), "model_weights": weights,
                   "note": "void = walkovers (left out); retirements stand once a set was finished. Engine-liked = "
                           "the model's chance minus THAT book's no-vig chance for the favorite."}
    universes = ["all"] + ([f"{k}+{int(t * 100)}%" for k, t in LIKED] if probs else [])
    rep["straights"], rep["parlays"] = {}, {}
    n_straight, n_parlay, fp_parlay, passed, near = 0, 0, 0.0, [], []
    for tour in ("atp", "wta"):
        tf = [m for m in facts if m.tour == tour]
        rep["straights"][tour], rep["parlays"][tour] = {}, {}
        for book in BOOKS:
            fv = favorites(tf, probs, book, split)
            st = straights(fv, universes)
            rep["straights"][tour][book] = st
            for u, bands in st.items():
                for band, sls in bands.items():
                    for sl, s in sls.items():
                        if not s or s["n"] < MIN_N:
                            continue
                        n_straight += 1
                        key = f"{tour}|{book}|{u}|{band}|{sl}"
                        if passes(s):
                            passed.append(key)
                        elif s["old"]["roi"] > 0 and s["new"]["roi"] > 0:
                            near.append({"test": key, "n": s["n"], "roi": s["roi"], "z_edge": s["z_edge"],
                                         "roi_old": s["old"]["roi"], "roi_new": s["new"]["roi"]})
            pb = {}
            for u in universes:
                pb[u] = {}
                for cap in CAPS:
                    ps = parlay_stats(tickets(fv, cap, u), split)
                    pb[u][f"-{cap}"] = ps
                    a = ps["all"]
                    if a.get("tickets", 0) >= MIN_N:
                        n_parlay += 1
                        fp_parlay += ps["old"].get("p_profit_if_no_edge", 0) * ps["new"].get("p_profit_if_no_edge", 0)
                        if a["proven"]:
                            passed.append(f"{tour}|{book}|{u}|parlay -{cap}")
            rep["parlays"][tour][book] = pb
    rep["passed_bar"] = passed
    rep["closest"] = sorted(near, key=lambda r: -r["z_edge"])[:12]
    rep["false_positives"] = {
        "straight_tests_n300": n_straight, "parlay_tests_n300": n_parlay,
        "expected_straight_by_luck": round(n_straight * P_LUCK, 3),
        "expected_parlay_by_luck": round(fp_parlay, 3),
        "note": "straights: tests x the one-sided odds of z 3.5 (~1 in 4,300) - an upper bound, the tests overlap. "
                "Parlays have no z bar: the sum over tests of P(profit in both halves) for a no-edge bettor at these "
                "real prices (truth = Pinnacle's fair chances)."}
    rep["verdict"] = verdict(rep)
    rep["proven"] = [] if rep["verdict"].startswith("NOT LUCRATIVE") else passed    # a luck-sized pass is not proof
    rep["secs"] = round(time.time() - t0, 1)
    _save(path, rep)
    log(report(rep))
    return rep


def verdict(rep):
    fp = rep["false_positives"]
    luck = f"(expected by luck: {fp['expected_straight_by_luck']} straights, {fp['expected_parlay_by_luck']} parlays)"
    if not rep["passed_bar"]:
        return ("NOT LUCRATIVE. No price band, engine-liked subset or 3-leg favorite parlay clears the bar (n 300+, "
                "profit in both halves, edge z 3.5+ for straights) at Pinnacle or Bet365 " + luck + ". Favorites win "
                "about as often as the no-vig price says; the book's margin is the loss, and a parlay multiplies it.")
    zs = []
    for key in rep["passed_bar"]:
        tour, book, u, rest = key.split("|", 3)
        if rest.startswith("parlay "):
            a = rep["parlays"][tour][book][u][rest.split()[1]]["all"]
            zs.append((key, a["z"], a["tickets"], a["roi"]))
        else:
            band, sl = rest.split("|")
            s = rep["straights"][tour][book][u][band][sl]
            zs.append((key, s["z"], s["n"], s["roi"]))
    listed = "; ".join(f"{k} (n {n}, roi {r:+.3f}, profit z {z:+.2f})" for k, z, n, r in zs)
    weak = all(z < 2 for _, z, _, _ in zs)
    exp = fp["expected_straight_by_luck"] + fp["expected_parlay_by_luck"]
    if weak and len(zs) <= max(1, round(2 * exp)):
        return (f"NOT LUCRATIVE (a pass that looks like luck). {listed} clears the bar, but its profit z is under 2 and "
                f"{round(exp, 2)} passes were expected by luck alone. Nothing to act on. Research only.")
    return f"{len(zs)} test(s) clear the bar: {listed} {luck}. Research only - re-check before trusting any of them."


def _save(path, rep):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(rep, f, indent=1)
    os.replace(path + ".tmp", path)


def _fmt(s):
    if not s:
        return "-"
    return (f"n {s['n']:>5} win {s['win']:.3f} fair {s['fair']:.3f} roi {s['roi']:+.3f} z_edge {s['z_edge']:+.2f} | "
            f"old n {s['old']['n']} roi {s['old'].get('roi', 0):+.3f} | new n {s['new']['n']} "
            f"roi {s['new'].get('roi', 0):+.3f}")


def report(rep):
    L = [f"HEAVY TENNIS FAVORITES (research only): {rep['data']['priced']} priced matches "
         f"{rep['data']['from']} -> {rep['data']['to']}, split {rep['split']}, {rep['data']['rated_for_model']} rated"]
    for tour, books in rep["straights"].items():
        for book, us in books.items():
            for u in ("all", "blend+2%", "model+2%"):
                if u not in us:
                    continue
                L.append(f" {tour.upper()} {book} straights [{u}]")
                for band, sls in us[u].items():
                    L.append(f"   {band:>11}: {_fmt(sls.get('all'))}")
    for tour, books in rep["parlays"].items():
        for book, us in books.items():
            for u in ("all", "blend+2%", "model+2%"):
                if u not in us:
                    continue
                for cap, ps in us[u].items():
                    a, o, w = ps["all"], ps["old"], ps["new"]
                    if not a.get("tickets"):
                        continue
                    L.append(f" {tour.upper()} {book} parlay cap {cap} [{u}]: {a['tickets']} tickets, hit "
                             f"{a['hit']:.3f} (fair {a['fair_hit']:.3f}), avg +{a['avg_payout_american']}, roi "
                             f"{a['roi']:+.3f} z {a['z']:+.2f} | old {o.get('tickets')} {o.get('roi', 0):+.3f} | new "
                             f"{w.get('tickets')} {w.get('roi', 0):+.3f}")
    fp = rep["false_positives"]
    L.append(f" tests at n300+: {fp['straight_tests_n300']} straight, {fp['parlay_tests_n300']} parlay; expected by luck "
             f"{fp['expected_straight_by_luck']} + {fp['expected_parlay_by_luck']}")
    L.append(f" passed the bar: {rep['passed_bar'] or 'none'} · proven (not luck-sized): {rep['proven'] or 'none'}")
    L.append(f" VERDICT: {rep['verdict']}")
    return "\n".join(L)


if __name__ == "__main__":
    study()
