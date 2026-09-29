"""THE TENNIS LABEL STUDY: does the tennis engine's disagreement with the market help or hurt - and how far should
the tennis picks trust our own number over the price? (The main board's tools/tier_study.py, done for tennis.)

Every finished ESPN match (data/sports/tennis/matches.csv) is replayed in order through the engine's own ratings
pools (sports_tennis.Pools: overall + surface Elo, form, fatigue, head-to-head - only what was known before the
match), then joined to its closing prices in data/sports/tennis/hist_odds.csv.gz (tennis-data names -> ESPN ids,
same winner + loser within 4 days). The market's number = the NO-VIG closing chance (Pinnacle when it has a price,
else the average across books).

Per tour, the priced matches are split by time: the OLDER half and the NEWER half. The engine's weights and the
trust blend (p = market + t * (engine - market)) are learned on the OLDER half only (the weights on every rated match
before the cut); everything is graded on the NEWER half the model never saw. Reported per tour:
  * calibration: the engine's own win % vs the market's implied %, by band, against what actually happened
  * hit rate + profit per $1 (at the closing average price, ~ a retail book like Bovada; Pinnacle too) bucketed by
    (a) win % bands and (b) how many points the engine disagrees with the market
  * the old tennis rule (engine 55%+ and 2%+ value) vs the new one (anchored win %, never fighting the line, no dogs)
  * the best trust t on the older half (the one the picks use) and on the newer half (the check)
Saves data/sports/tennis/tier_study.json."""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_tennis as stn         # noqa: E402
import sports_tennis_edge as ste    # noqa: E402

OUT = os.path.join(stn.DIR, "tier_study.json")
DAYS = 4                              # an ESPN match and a tennis-data row: same winner + loser within 4 days
TS = [i / 100 for i in range(-50, 101)]  # negative = the engine's disagreement points the WRONG way (a probe only)
P_BANDS = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.01)
GAPS = (-1.0, -0.10, -0.06, -0.03, 0.0, 0.03, 0.06, 0.10, 0.15, 0.20, 1.0)   # engine minus market, this side
OLD_MIN_P, OLD_MIN_EDGE, MAX_FAV = 0.55, 0.02, -300


def american(dec):
    return round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))


def replay(ms, players):
    """[(features, y, match)] per tour for every rated finished match, features from earlier matches only."""
    rows = sorted((m for m in ms.values() if stn._state(m) in ("final", "retired")), key=lambda m: (m["start"], m["id"]))
    wo = [m for m in ms.values() if "WALKOVER" in str(m.get("status")).upper()]
    rt = stn.Pools(players)
    data = {t: [] for t in stn.TOURS}
    for m in sorted(rows + wo, key=lambda m: (m["start"], m["id"])):
        if stn._state(m) == "void":
            rt.update(m)
            continue
        f = rt.features(m)
        if f["known"] >= stn.MIN_MATCHES and int(m["winner"] or 0) in (1, 2) and stn._state(m) == "final":
            data[stn.tour_of(m)].append((f, 1.0 if int(m["winner"]) == 1 else 0.0, m))
        rt.update(m)
    return data


def prices():
    """{(tour, winner espn id, loser espn id): [(day ordinal, {book: (dec winner, dec loser)})]}."""
    nmap, _ = ste.name_map(stn.MATCHES)
    out = defaultdict(list)
    for M in ste.read_hist():
        if M.status == "void" or not M.odds:
            continue
        w, l = ste.espn_id(nmap, M.tour, M.W), ste.espn_id(nmap, M.tour, M.L)
        if w and l:
            out[(M.tour, w, l)].append((M.dn, M.odds))
    return out


def join(data, px):
    """Per tour: [(features, y, match, {book: (dec p1, dec p2)})] for the rated matches with a closing price."""
    out = {}
    for t, rows in data.items():
        got = []
        for f, y, m in rows:
            wid, lid = (m["p1"], m["p2"]) if y == 1.0 else (m["p2"], m["p1"])
            dn = date.fromisoformat(m["start"][:10]).toordinal()
            near = [(abs(d - dn), o) for d, o in px.get((t, str(wid), str(lid)), []) if abs(d - dn) <= DAYS]
            if not near:
                continue
            odds = min(near, key=lambda x: x[0])[1]
            got.append((f, y, m, {b: (a, c) if y == 1.0 else (c, a) for b, (a, c) in odds.items()}))
        out[t] = got
    return out


def nv(pair):
    a, b = 1 / pair[0], 1 / pair[1]
    return a / (a + b)


def blend(mk, en, t):
    return min(max(mk + t * (en - mk), 0.01), 0.99)


def ll(ps, ys):
    return sum(-math.log(min(max(p if y else 1 - p, 1e-6), 1)) for p, y in zip(ps, ys)) / max(1, len(ys))


def best_t(rows):
    ys = [r["y"] for r in rows]
    scores = {t: ll([blend(r["mkt"], r["eng"], t) for r in rows], ys) for t in TS}
    t = min((t for t in TS if t >= 0), key=scores.get)             # the trust itself never goes below 0
    return t, scores


def sides(r, t):
    """Both sides of a graded match: win chances (engine, market, anchored), the prices, won?"""
    out = []
    for s, won in ((1, r["y"] == 1.0), (2, r["y"] == 0.0)):
        flip = (lambda x: x) if s == 1 else (lambda x: 1 - x)
        i = s - 1
        out.append({"eng": flip(r["eng"]), "mkt": flip(r["mkt"]), "p": flip(blend(r["mkt"], r["eng"], t)), "won": won,
                    "avg": r["odds"].get("avg", (None, None))[i], "pin": r["odds"].get("pin", (None, None))[i],
                    "day": r["day"]})
    return out


def summ(ss, book="avg"):
    ss = [s for s in ss if s.get(book)]
    n = len(ss)
    if not n:
        return {"n": 0}
    won = sum(s["won"] for s in ss)
    return {"n": n, "hit": round(won / n, 3), "eng_p": round(sum(s["eng"] for s in ss) / n, 3),
            "mkt_p": round(sum(s["mkt"] for s in ss) / n, 3), "anch_p": round(sum(s["p"] for s in ss) / n, 3),
            "roi": round(sum((s[book] - 1) if s["won"] else -1 for s in ss) / n, 3),
            "roi_pin": (round(sum((s["pin"] - 1) if s["won"] else -1 for s in ss if s["pin"]) / max(1, sum(1 for s in ss if s["pin"])), 3)
                        if any(s["pin"] for s in ss) else None)}


def band(x, cuts):
    for lo, hi in zip(cuts, cuts[1:]):
        if lo <= x < hi:
            return f"{round(100 * lo)}-{round(100 * hi)}" if hi < 1 else f"{round(100 * lo)}+"
    return None


def by(ss, key, cuts):
    g = defaultdict(list)
    for s in ss:
        b = band(key(s), cuts)
        if b:
            g[b].append(s)
    order = [band((lo + hi) / 2 if hi < 1 else lo, cuts) for lo, hi in zip(cuts, cuts[1:])]
    return {b: summ(g[b]) for b in order if g.get(b)}


def rule_old(s):
    return s["eng"] >= OLD_MIN_P and s["eng"] * s["avg"] - 1 >= OLD_MIN_EDGE and american(s["avg"]) >= MAX_FAV


def rule_new(s, min_p=OLD_MIN_P, fight=0.03):
    return s["p"] >= min_p and s["eng"] >= s["mkt"] - fight and s["mkt"] > 0.5 and american(s["avg"]) >= MAX_FAV


def slates(ss, rule, n=6):
    """The owner's slate: per day, the up-to-6 likeliest plays that pass the rule (the claimed % = what the rule
    ranks by), plus the day's 3-leg parlay of the likeliest three."""
    days = defaultdict(list)
    for s in ss:
        if rule(s):
            days[s["day"]].append(s)
    picks, par = [], []
    for d, v in days.items():
        v = sorted(v, key=lambda s: -s["p_rank"])[:n]
        picks += v
        if len(v) >= 3:
            legs = v[:3]
            dec = math.prod(s["avg"] for s in legs)
            par.append((all(s["won"] for s in legs), dec))
    out = summ(picks)
    out["days"] = len(days)
    out["per_day"] = round(len(picks) / max(1, len(days)), 2)
    if par:
        out["parlays"] = {"n": len(par), "hit": round(sum(w for w, _ in par) / len(par), 3),
                          "roi": round(sum((d - 1) if w else -1 for w, d in par) / len(par), 3)}
    return out


def tour_study(t, data_t, joined_t, log=print):
    joined_t = [j for j in joined_t if "avg" in j[3] or "pin" in j[3]]
    cut_i = len(joined_t) // 2
    cut = joined_t[cut_i][2]["start"]
    fit_on = [(f, y, m) for f, y, m in data_t if m["start"] < cut]
    w = stn._fit(fit_on)
    rows = []
    for f, y, m, odds in joined_t:
        mk = nv(odds["pin"]) if "pin" in odds else nv(odds["avg"])
        rows.append({"eng": stn.model_p(w, f, m["bo"]), "mkt": mk, "y": y, "odds": odds, "day": m["start"][:10],
                     "old": m["start"] < cut})
    old, new = [r for r in rows if r["old"]], [r for r in rows if not r["old"]]
    t_old, sc_old = best_t(old)
    t_new, sc_new = best_t(new)
    used = t_old if sc_new[t_old] < sc_new[0.0] else 0.0             # kept only if it beats the market on unseen matches
    lls = {"market": round(sc_new[0.0], 5), "engine": round(sc_new[1.0], 5),
           f"anchored t={t_old}": round(sc_new[t_old], 5), f"best on newer t={t_new}": round(sc_new[t_new], 5)}
    acc = {"market": round(sum((r["mkt"] > 0.5) == (r["y"] == 1.0) for r in new) / len(new), 4),
           "engine": round(sum((r["eng"] > 0.5) == (r["y"] == 1.0) for r in new) / len(new), 4)}
    ss = [s for r in new for s in sides(r, t_old) if s["avg"]]      # graded at the average (retail) price
    fav_eng = [s for s in ss if s["eng"] > 0.5]                   # each match once: the engine's side
    fav_mkt = [s for s in ss if s["mkt"] > 0.5]                   # each match once: the market's favorite
    pick_side = [s for s in ss if s["p"] > 0.5]                   # each match once: the anchored number's side
    for s in ss:
        s["gap"] = s["eng"] - s["mkt"]
    # (b) disagreement: the side the engine likes MORE than the market does, by how far (the old "edge" picks)
    likes = [s for s in ss if s["gap"] > 0]
    old_rank = [dict(s, p_rank=s["eng"]) for s in ss]
    new_rank = [dict(s, p_rank=s["p"]) for s in ss]
    rep = {
        "priced_matches": len(rows), "older": len(old), "newer": len(new), "cut": cut[:10],
        "newer_from": new[0]["day"] if new else None, "newer_to": new[-1]["day"] if new else None,
        "rated_fit_on": len(fit_on), "weights_fit_older": [round(v, 3) for v in w],
        "trust_learned_on_older": t_old, "trust_best_on_newer": t_new, "trust_used": used,
        "trust_any_sign_best_newer": min(TS, key=sc_new.get),
        "logloss_newer": lls, "acc_newer": acc,
        "trust_curve_newer": {str(t): round(sc_new[t], 5) for t in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0)},
        "calibration_engine_side_by_engine_pct": by(fav_eng, lambda s: s["eng"], P_BANDS),
        "calibration_market_fav_by_market_pct": by(fav_mkt, lambda s: s["mkt"], P_BANDS),
        "hit_by_anchored_pct": by(pick_side, lambda s: s["p"], P_BANDS),
        "disagreement_engine_likes_more": by(likes, lambda s: s["gap"], GAPS),
        "market_favorite_by_engine_gap": by(fav_mkt, lambda s: s["gap"], GAPS),
        "engine_vs_market_when_they_pick_different_sides": summ([s for s in fav_eng if s["mkt"] < 0.5]),
        "rules_all_qualifying": {"old (engine 55%+, 2%+ value)": summ([s for s in ss if rule_old(s)]),
                                 "new (anchored 55%+, fav, not fighting)": summ([s for s in ss if rule_new(s)])},
        "slates_6_a_day": {"old": slates([s for s in old_rank], rule_old),
                           "new": slates([s for s in new_rank], rule_new),
                           "new_60": slates([s for s in new_rank], lambda s: rule_new(s, 0.60))},
    }
    log(f"{t.upper()}: {len(rows)} priced ({len(old)} older / {len(new)} newer from {rep['newer_from']}), "
        f"trust older {t_old} / newer {t_new} -> used {used}, logloss newer {lls}")
    return rep


def main():
    ms = stn.load_matches()
    data = replay(ms, stn.load_players())
    joined = join(data, prices())
    report = {"what": __doc__.split("\n")[0], "tours": {}}
    for t in stn.TOURS:
        print(f"{t}: {len(data[t])} rated, {len(joined[t])} with a closing price", flush=True)
        report["tours"][t] = {"rated": len(data[t]), **tour_study(t, data[t], joined[t])}
    report["trust"] = {t: r["trust_used"] for t, r in report["tours"].items()}   # what sports_tennis anchors with
    with open(OUT, "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
