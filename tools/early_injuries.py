"""INJURIES x THE EARLY NUMBER (10/1, the owner: "factor in who's injured with these odds"). NFL injury reports
(tools/nfl_injuries.py, nflverse) joined to the early prices (moneyline dogs + spreads, first look of the week).
KNOWN EARLY = last week's report (out when we'd bet). LATE NEWS = this week's final report (Friday) - hindsight: what
news after our bet does to it. Saves results/early_injuries.json."""
import json
import os
import sys
from datetime import timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import early_round2 as r2           # noqa: E402
import nfl_injuries as ni           # noqa: E402

ET = ZoneInfo("America/New_York")
ABBR = {"ARI": "22", "ATL": "1", "BAL": "33", "BUF": "2", "CAR": "29", "CHI": "3", "CIN": "4", "CLE": "5", "DAL": "6",
        "DEN": "7", "DET": "8", "GB": "9", "HOU": "34", "IND": "11", "JAX": "30", "KC": "12", "LA": "14", "LAR": "14",
        "LAC": "24", "LV": "13", "OAK": "13", "MIA": "15", "MIN": "16", "NE": "17", "NO": "18", "NYG": "19", "NYJ": "20",
        "PHI": "21", "PIT": "23", "SEA": "26", "SF": "25", "TB": "27", "TEN": "10", "WAS": "28"}
OUT = ("Out", "Doubtful")


def reports():
    """{(season, team id, week): {"qb_out", "qb_q", "n_out"}}."""
    rep = {}
    for r in ni.load():
        if r["game_type"] != "REG" or r["team"] not in ABBR:
            continue
        k = (int(r["season"]), ABBR[r["team"]], int(r["week"]))
        d = rep.setdefault(k, {"qb_out": False, "qb_q": False, "n_out": 0})
        st = r["report_status"]
        if st in OUT:
            d["n_out"] += 1
            if r["position"] == "QB":
                d["qb_out"] = True
        elif st == "Questionable" and r["position"] == "QB":
            d["qb_q"] = True
    return rep


def week_of(rows):
    """{game id: week} - week 1 starts on each season's first game day (ET), weeks run 7 days."""
    first = {}
    for r in rows:
        d = ef._t(r["start"]).astimezone(ET).date()
        if r["season"] not in first or d < first[r["season"]]:
            first[r["season"]] = d
    return {r["gid"]: (ef._t(r["start"]).astimezone(ET).date() - first[r["season"]]).days // 7 + 1 for r in rows}


def main():
    rows = r2.build("nfl")
    rep = reports()
    wk = week_of(rows)
    blank = {"qb_out": False, "qb_q": False, "n_out": 0}
    for r in rows:
        w = wk[r["gid"]]
        r["me_now"], r["them_now"] = rep.get((r["season"], r["tid"], w), blank), rep.get((r["season"], r["oid"], w), blank)
        r["me_prev"], r["them_prev"] = rep.get((r["season"], r["tid"], w - 1), blank), rep.get((r["season"], r["oid"], w - 1), blank)
        r["has_rep"] = (r["season"], r["tid"], w) in rep or (r["season"], r["oid"], w) in rep
    rows = [r for r in rows if wk[r["gid"]] <= 18]
    print(f"NFL sides: {len(rows)}, with an injury report that week: {sum(r['has_rep'] for r in rows)}")
    A = {
        "KNOWN EARLY: their QB out last week (ours wasn't)": lambda r: r["them_prev"]["qb_out"] and not r["me_prev"]["qb_out"],
        "KNOWN EARLY: our QB out last week (theirs wasn't)": lambda r: r["me_prev"]["qb_out"] and not r["them_prev"]["qb_out"],
        "KNOWN EARLY: they had 4+ more out last week": lambda r: r["them_prev"]["n_out"] - r["me_prev"]["n_out"] >= 4,
        "KNOWN EARLY: we had 4+ more out last week": lambda r: r["me_prev"]["n_out"] - r["them_prev"]["n_out"] >= 4,
        "LATE NEWS: their QB ruled out (wasn't last week)": lambda r: r["them_now"]["qb_out"] and not r["them_prev"]["qb_out"],
        "LATE NEWS: our QB ruled out (wasn't last week)": lambda r: r["me_now"]["qb_out"] and not r["me_prev"]["qb_out"],
        "LATE NEWS: our QB questionable": lambda r: r["me_now"]["qb_q"],
        "LATE NEWS: they end up 4+ more out": lambda r: r["them_now"]["n_out"] - r["me_now"]["n_out"] >= 4,
        "LATE NEWS: we end up 4+ more out": lambda r: r["me_now"]["n_out"] - r["them_now"]["n_out"] >= 4,
    }
    out = {}
    for name, t in A.items():
        sel = [r for r in rows if t(r)]
        res = {"ML dog": r2.grade_ml(sel), "ML dog + engine likes": r2.grade_ml([r for r in sel if (r.get("ml_gap") or -1) >= .04]),
               "spread": r2.grade_sp(sel), "spread + engine 3.5+ pts": r2.grade_sp([r for r in sel if (r.get("sp_edge") or -99) >= 3.5])}
        out[name] = res
        print(f"\n-- {name}")
        for k, v in res.items():
            if v:
                what = "won" if k.startswith("ML") else "covered"
                print(f"   {k:26s} {v['n']:4d}  {what} {v['rate']:.1%} (needs {v['said']:.1%})  ROI {v['roi']:+.1%}  up {v['up']} {v['by']}")
    # the early NFL spread play (engine 3.5+): does late QB news on our side kill it? (risk check)
    play = [r for r in rows if (r.get("sp_edge") or -99) >= 3.5]
    for lbl, t in (("all", lambda r: True),
                   ("no QB on either report last week", lambda r: not (r["me_prev"]["qb_out"] or r["me_prev"]["qb_q"] or r["them_prev"]["qb_out"] or r["them_prev"]["qb_q"])),
                   ("our QB on last week's report", lambda r: r["me_prev"]["qb_out"] or r["me_prev"]["qb_q"]),
                   ("late: our QB ruled out", lambda r: r["me_now"]["qb_out"] and not r["me_prev"]["qb_out"]),
                   ("late: their QB ruled out", lambda r: r["them_now"]["qb_out"] and not r["them_prev"]["qb_out"])):
        v = r2.grade_sp([r for r in play if t(r)])
        out["engine spread play: " + lbl] = v
        if v:
            print(f"   engine spread play, {lbl:34s} {v['n']:4d}  covered {v['rate']:.1%}  ROI {v['roi']:+.1%}  up {v['up']}")
    with open("results/early_injuries.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
