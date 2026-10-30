"""STUDY 3 (10/30): NBA favorites -101..-150 by rest / travel / schedule combos at the CLOSE (flat 1u), from
sports_nba_open.table() (each team's pre-game schedule facts, nothing from the box). TRAIN 2018-19..2023-24, HOLDOUT
2024-25 + 2025-26 (apart), NOW 2026-27. The mirror (the dog in the same spot) as a second check."""
import sys, os
sys.path.insert(0, os.getcwd())
import sports_data as sd
import sports_nba_open as no

games = sd.load_games("nba")
tab = no.table(games)
rows = []
for gid, r in tab.items():
    if not r["reg"] or r["home_win"] is None or r["season"] < 2018 or not r["ml_home"] or not r["ml_away"]:
        continue
    for side in ("home", "away"):
        ml = r["ml_home"] if side == "home" else r["ml_away"]
        opp_ml = r["ml_away"] if side == "home" else r["ml_home"]
        t, o = (r["h"], r["a"]) if side == "home" else (r["a"], r["h"])
        won = r["home_win"] if side == "home" else 1 - r["home_win"]
        rows.append(dict(season=r["season"], date=r["date"], side=side, home=side == "home", ml=ml, opp_ml=opp_ml, t=t, o=o,
                         won=won, pnl=(no._dec(ml) - 1) if won else -1.0, mp=no._mp(ml, opp_ml), gid=gid))
TRAIN = range(2018, 2024)


def rep(name, sel, band=(-150, -101)):
    sub = [x for x in rows if band[0] <= x["ml"] <= band[1] and sel(x)]
    by = {}
    for x in sub:
        o = by.setdefault(x["season"], [0, 0, 0.0])
        o[0] += x["won"]; o[1] += 1 - x["won"]; o[2] += x["pnl"]

    def agg(seasons):
        w = sum(by[s][0] for s in seasons if s in by); l = sum(by[s][1] for s in seasons if s in by)
        u = sum(by[s][2] for s in seasons if s in by); n = w + l
        up = sum(1 for s in seasons if s in by and by[s][2] > 0); tot = sum(1 for s in seasons if s in by)
        return f"{w:.0f}-{l:.0f} {u / n * 100 if n else 0:+6.1f}% ({up}/{tot})"
    print(f"{name:52s} train {agg(TRAIN):28s} | hold {agg([2024, 2025]):26s} | 24 {agg([2024]):22s} 25 {agg([2025]):22s} | now {agg([2026])}")


def travelled(o):
    return o["tz_cross"] >= 1 or o["trip_game"] >= 2


print("FAVORITES -101..-150 at the close, flat 1u (train 2018-23 / holdout 2024-25 / now 2026):")
rep("the band (base)", lambda x: True)
rep("home favorite", lambda x: x["home"])
rep("road favorite", lambda x: not x["home"])
print("-- the opponent's legs:")
rep("vs opp on a b2b", lambda x: x["o"]["b2b"] == 1)
rep("rested (2+ days) vs opp b2b", lambda x: x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1)
rep("rested home fav vs opp b2b", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1)
rep("rested home fav vs opp b2b + travelled", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1 and travelled(x["o"]))
rep("rested home fav vs opp b2b, tz 1+", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1 and x["o"]["tz_cross"] >= 1)
rep("rested home fav vs opp b2b, tz 2+", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1 and x["o"]["tz_cross"] >= 2)
rep("rested road fav vs opp b2b", lambda x: not x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1)
rep("3+ days rest vs opp b2b", lambda x: x["t"]["rest"] >= 3 and x["o"]["b2b"] == 1)
rep("vs opp 3 in 4 nights", lambda x: x["o"]["n4"] >= 3)
rep("rested vs opp 3 in 4", lambda x: x["t"]["rest"] >= 2 and x["o"]["n4"] >= 3)
rep("vs opp 4 in 6 nights", lambda x: x["o"]["n6"] >= 4)
rep("rested vs opp 4 in 6", lambda x: x["t"]["rest"] >= 2 and x["o"]["n6"] >= 4)
rep("home fav vs opp road trip game 4+", lambda x: x["home"] and x["o"]["trip_game"] >= 4)
rep("home fav vs opp road trip game 3+", lambda x: x["home"] and x["o"]["trip_game"] >= 3)
rep("home fav vs opp b2b on trip game 2+", lambda x: x["home"] and x["o"]["b2b"] == 1 and x["o"]["trip_game"] >= 2)
rep("home fav at altitude vs lowland opp", lambda x: x["home"] and x["o"]["alt"] == 1)
rep("home fav at altitude vs opp b2b", lambda x: x["home"] and x["o"]["alt"] == 1 and x["o"]["b2b"] == 1)
rep("home fav vs opp 2+ time zones", lambda x: x["home"] and x["o"]["tz_cross"] >= 2)
rep("home fav vs opp 3 time zones", lambda x: x["home"] and x["o"]["tz_cross"] >= 3)
print("-- our own legs (fades?):")
rep("fav on a b2b", lambda x: x["t"]["b2b"] == 1)
rep("fav on a b2b vs rested opp", lambda x: x["t"]["b2b"] == 1 and x["o"]["rest"] >= 2)
rep("road fav on a b2b", lambda x: not x["home"] and x["t"]["b2b"] == 1)
rep("fav 3 in 4", lambda x: x["t"]["n4"] >= 3)
rep("fav road trip game 4+", lambda x: not x["home"] and x["t"]["trip_game"] >= 4)
rep("fav road trip game 2-3", lambda x: not x["home"] and 2 <= x["t"]["trip_game"] <= 3)
rep("fav home after a 4+ game trip", lambda x: x["home"] and x["t"]["home_after"] >= 4)
rep("fav home after a 3+ game trip", lambda x: x["home"] and x["t"]["home_after"] >= 3)
rep("fav 3+ days rest (rust?)", lambda x: x["t"]["rest"] >= 3)
rep("fav 3+ days rest vs opp 1 day", lambda x: x["t"]["rest"] >= 3 and x["o"]["rest"] <= 1)
rep("fav 4+ days rest", lambda x: x["t"]["rest"] >= 4)
rep("both on a b2b", lambda x: x["t"]["b2b"] == 1 and x["o"]["b2b"] == 1)
rep("both rested 2+", lambda x: x["t"]["rest"] >= 2 and x["o"]["rest"] >= 2)
print("-- the rest edge (days):")
for lo in (1, 2, 3):
    rep(f"rest edge {lo}+ days (ours - theirs)", lambda x, lo=lo: min(x["t"]["rest"], 6) - min(x["o"]["rest"], 6) >= lo)
    rep(f"rest edge -{lo} or worse", lambda x, lo=lo: min(x["t"]["rest"], 6) - min(x["o"]["rest"], 6) <= -lo)
print("-- the same at -151..-200 (out of the play band, a check):")
rep("rested home fav vs opp b2b", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1, band=(-200, -151))
rep("rested home fav vs opp b2b + travelled", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1 and travelled(x["o"]), band=(-200, -151))
print("-- the MIRROR: the dog +100..+350 in the spot (the other side):")
rep("dog on a b2b vs rested fav", lambda x: x["t"]["b2b"] == 1 and x["o"]["rest"] >= 2, band=(100, 350))
rep("road dog on a b2b + travelled vs rested home fav", lambda x: not x["home"] and x["t"]["b2b"] == 1 and travelled(x["t"]) and x["o"]["rest"] >= 2, band=(100, 350))
rep("rested dog vs fav on a b2b", lambda x: x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1, band=(100, 350))
rep("dog base", lambda x: True, band=(100, 350))
print("-- stage of season (games 1-5 off the play anyway):")
rep("rested home fav vs opp b2b, game 6+", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1 and x["t"]["n_season"] >= 5)
rep("rested home fav vs opp b2b, game 11+", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1 and x["t"]["n_season"] >= 10)
print("-- by price inside the best cell:")
rep("rested home fav vs opp b2b, -101..-125", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1, band=(-125, -101))
rep("rested home fav vs opp b2b, -126..-150", lambda x: x["home"] and x["t"]["rest"] >= 2 and x["o"]["b2b"] == 1, band=(-150, -126))
