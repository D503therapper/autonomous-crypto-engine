import json, sys
rows = json.load(open(sys.argv[1]))
fbs = [r for r in rows if r["fbs_game"] is not False]
print(len(rows), "college sides in band;", len(fbs), "FBS / unknown")


def why(r):
    w = []
    if r["posted"]:
        return "POSTED " + r["posted"]
    if r["waiting"]:
        w.append("waiting: " + "; ".join(r["waiting"])[:70])
    if r["hurt"]:
        w.append("hurt")
    if r["trap"]:
        w.append("trap")
    if r["odds"] >= 100:
        g = r["gap"]
        if g is not None and g >= 0.15 and (r["elo_edge"] or -1) >= 0 and r["fbs_game"] is False:
            w.append("gap 15+ but FCS game")
        elif g is not None and g >= 0.15 and (r["elo_edge"] or -1) < 0:
            w.append(f"gap {g:+.2f} but Elo backs the favorite")
        elif g is not None:
            w.append(f"raw gap {g:+.2f} (<0.15)")
        if not r["dog_gate"]:
            w.append(f"dog gate (score {r['dog_score']})")
        if not r["n_reasons"]:
            w.append("no named reason")
        if not r["own_beats"]:
            w.append("own read under price")
    else:
        if -150 <= r["odds"] <= -130:
            w.append("lean band -150..-130")
        if not r["own_beats"]:
            w.append("own read under price")
        if not r["real_value"]:
            w.append("weighed read under price")
        if not r["lock_ok"]:
            w.append("no Lock (blend<56%)")
        if r["thin_edge"]:
            w.append("thin")
        if not r["good"]:
            w.append("not good()")
    return ", ".join(w)


for lab, sel in (("DOGS +100..+350", lambda r: r["odds"] >= 100), ("SLIGHT FAVORITES -101..-150", lambda r: r["odds"] < 0)):
    print(f"\n== {lab} ==")
    for r in sorted((r for r in rows if sel(r)), key=lambda r: (r["fbs_game"] is False, r["odds"])):
        tag = "FCS" if r["fbs_game"] is False else "FBS" if r["fbs_game"] else "?"
        print(f"  [{tag}] {r['team']} {r['odds']:+d} vs {r['opp']}: mkt {r['p_mkt'] or 0:.3f} own {r['own'] or 0:.3f} "
              f"w_p {r['w_p'] if r['w_p'] is None else round(r['w_p'], 3)} raw {r['raw_own'] or 0:.3f} elo {r['elo_edge']} "
              f"ruleA={bool(r['rule_a'])} offloss={bool(r['off_loss'])} -> {why(r)}")
