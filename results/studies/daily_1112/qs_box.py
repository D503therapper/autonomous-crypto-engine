"""11/12 DAILY - QUICK NEW STUDIES FROM THE TEAM BOX (ESPN's team box, data/sports/teamstats, 2021-26) - angles the
findings file has never run (checked: "red zone" 0, "leadPercentage" / "time leading" 0, "technical" 0, NHL "hits" 0):
  Q1 NFL: RED-ZONE LUCK - a team's touchdown rate inside the 20 this season (TD trips / trips, 4+ games, 10+ trips): the
     team cashing its trips far above / below the league - does the market chase it?
  Q2 NBA: THE CLOSERS' LUCK - its win % this season minus the share of the game it spent LEADING (leadPercentage, 10+
     games): the team winning more than its time in front says (lucky closers) / less
  Q3 NBA: THE HOT HEADS - 2+ technical fouls (or a flagrant) in its last game, the next game within 4 days
  Q4 NHL: THE HITTING TEAM - hits for minus hits against a game this season (10+ games): the team that hits a lot is the
     team without the puck - is it priced?
Every state is built from FINISHED games strictly before tonight (no look-ahead); prices are the game file's CLOSE at its
own juice. Bands: favorites -150..-101, dogs +100..+350 (NHL +100..+300); ATS at the close (NFL / NBA). Cut points are
the TRAIN seasons' terciles / quintiles. TRAIN 2021-23, HELD 2024 / 2025 / 2026 (2026 = this season, to 11/10).
~60 cells: ~3 would clear |z| 2 by luck.
Usage: python results/studies/daily_1112/qs_box.py > results/studies/daily_1112/qs_box_out.txt"""
import importlib.util, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fl1111", os.path.join(os.path.dirname(HERE), "fable_1111", "lib.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
B = L.B
TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]


def frac(s):
    p = L.pair(s)
    return p


def num(x):
    try:
        return float(str(x).replace("%", ""))
    except (TypeError, ValueError):
        return None


def quant(vals, qs):
    v = sorted(vals)
    return [v[int(q * (len(v) - 1))] for q in qs]


def run(lg, state_fn, update_fn, ready_fn, cuts_q, name, dog_hi=350, spreads=True):
    fin = [g for g in B.finals(lg) if g["season"] >= 2021 and g["stype"] == "2"]
    box = L.teambox(lg)
    acc = defaultdict(lambda: defaultdict(float))
    last = {}
    rows = []
    for g in fin:
        tb = box.get(g["id"]) or {}
        for side, team, opp, odds, won, home in B.sides(g):
            k, ko = (g["season"], team), (g["season"], opp)
            if ready_fn(acc[k], last.get(team), g):
                rows.append({"season": g["season"], "x": state_fn(acc[k], last.get(team), g), "odds": odds, "won": won,
                             "ats": B.ats(g, side) if spreads else None,
                             "xo": state_fn(acc[ko], last.get(opp), g) if ready_fn(acc[ko], last.get(opp), g) else None})
        for side, team, opp, odds, won, home in B.sides(g):
            st, so = tb.get(team), tb.get(opp)
            if st:
                update_fn(acc[(g["season"], team)], st, so, won)
                last[team] = (g["start"], st, won)
    tr = [r["x"] for r in rows if TRAIN[0] <= r["season"] <= TRAIN[1] and r["x"] is not None]
    if len(tr) < 100:
        print(f"{name}: too few train rows ({len(tr)})")
        return
    cuts = quant(tr, cuts_q)
    cells = B.Cells()
    for r in rows:
        if r["x"] is None:
            continue
        grp = "LOW" if r["x"] <= cuts[0] else "HIGH" if r["x"] >= cuts[-1] else "MID"
        d = B.dec(r["odds"])
        for nm, ok in (("fav -150..-101", -150 <= r["odds"] <= -101), (f"dog +100..+{dog_hi}", 100 <= r["odds"] <= dog_hi)):
            if ok:
                cells.add(f"{name} {grp:4s} {nm}", r["season"], B.profit(r["won"], d))
                cells.add(f"BASE {name} {nm}", r["season"], B.profit(r["won"], d))
        if r["ats"] is not None:
            cells.add(f"{name} {grp:4s} ATS", r["season"], r["ats"])
            cells.add(f"BASE {name} ATS", r["season"], r["ats"])
        if r["xo"] is not None:
            gap = r["x"] - r["xo"]
            r["gap"] = gap
    gaps = [r["gap"] for r in rows if r.get("gap") is not None and TRAIN[0] <= r["season"] <= TRAIN[1]]
    if len(gaps) > 100:
        gc = quant(gaps, cuts_q)
        for r in rows:
            if r.get("gap") is None:
                continue
            grp = "LOW" if r["gap"] <= gc[0] else "HIGH" if r["gap"] >= gc[-1] else None
            if not grp:
                continue
            d = B.dec(r["odds"])
            for nm, ok in (("fav -150..-101", -150 <= r["odds"] <= -101), (f"dog +100..+{dog_hi}", 100 <= r["odds"] <= dog_hi)):
                if ok:
                    cells.add(f"{name} GAP-{grp} {nm}", r["season"], B.profit(r["won"], d))
            if r["ats"] is not None:
                cells.add(f"{name} GAP-{grp} ATS", r["season"], r["ats"])
    print(f"\n== {name}: {len(rows)} sides with a state; cuts {[round(c, 3) for c in cuts]}")
    for k, v in sorted(cells.c.items()):
        print(B.fmt(k, B.summ(v, TRAIN, HELD)))


# Q1 NFL red-zone luck -------------------------------------------------------------------------------------------
def rz_upd(a, st, so, won):
    p = frac(st.get("redZoneAttempts"))
    if p:
        a["m"] += p[0]
        a["t"] += p[1]
    a["g"] += 1


run("nfl", lambda a, l, g: a["m"] / a["t"], rz_upd, lambda a, l, g: a["g"] >= 4 and a["t"] >= 10, (1 / 3, 2 / 3),
    "Q1 NFL red-zone TD rate")


# Q2 NBA closers' luck ----------------------------------------------------------------------------------------------
def lead_upd(a, st, so, won):
    lp = num(st.get("leadPercentage"))
    if lp is not None:
        a["lp"] += lp / 100 if lp > 1 else lp
        a["n"] += 1
        a["w"] += 1 if won else 0


run("nba", lambda a, l, g: a["w"] / a["n"] - a["lp"] / a["n"], lead_upd, lambda a, l, g: a["n"] >= 10, (0.2, 0.8),
    "Q2 NBA win% minus time leading")


# Q3 NBA hot heads ---------------------------------------------------------------------------------------------------
def none_upd(a, st, so, won):
    a["g"] += 1


def tech_state(a, l, g):
    if not l or B.days_between(l[0], g["start"]) > 4:
        return None
    t = num(l[1].get("totalTechnicalFouls")) or num(l[1].get("technicalFouls")) or 0
    f = num(l[1].get("flagrantFouls")) or 0
    return 1.0 if (t >= 2 or f >= 1) else 0.0


run("nba", tech_state, none_upd, lambda a, l, g: tech_state(a, l, g) is not None, (0.5, 0.99),
    "Q3 NBA 2+ techs / a flagrant last game")


# Q4 NHL hitting team -----------------------------------------------------------------------------------------------
def hit_upd(a, st, so, won):
    h, ho = num(st.get("hits")), num((so or {}).get("hits"))
    if h is not None and ho is not None:
        a["d"] += h - ho
        a["n"] += 1


run("nhl", lambda a, l, g: a["d"] / a["n"], hit_upd, lambda a, l, g: a["n"] >= 10, (0.2, 0.8),
    "Q4 NHL hits for minus against", dog_hi=300, spreads=False)
