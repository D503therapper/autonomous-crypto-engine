"""S2b - the move model's one real input, alone: our results-Elo vs the OPEN. Does the college hoops close move toward
the ratings (CLV), and does buying the Elo side at the open pay - in every season, every tier, and NOT at the close
(if it also pays at the close 2018-22, it's a ratings edge, not a soft open)?
One parameter (the gap), no fit. FAIR = both teams' last games 3+ nights before tip. Also: the home drift (the move
leans to the home side)."""
import lib

out = lib.Out("s2b_elo_vs_open", train=(2023,), held=(2024, 2025))
R = [x for x in lib.nc_sides() if x["stype"] == "2" and x["season"] >= 2018 and x.get("p") is not None]
for x in R:
    hadv = 0 if x["neutral"] else (75 if x["side"] == "home" else -75)
    x["ep"] = 1 / (1 + 10 ** (-(x["elo"] - x["oelo"] + hadv) / 400))
    x["fair"] = (x.get("rest") or 9) >= 3 and (x.get("orest") or 9) >= 3
    x["gtier"] = "P" if "power" in (x["tier"], x["otier"]) else ("M" if "mid" in (x["tier"], x["otier"]) else "L")


def gr(rows, price="mlo"):
    return [(x["season"], lib.ml_pl(x[price], x["won"])) for x in rows]


O = [x for x in R if x.get("po") is not None and x["gn"] >= 4 and x["ogn"] >= 4]
for fair in (True, False):
    out.h(f"ELO OVER THE OPEN by X, open -150..+300, both teams 4+ games ({'FAIR' if fair else 'all'})")
    for g in (0.04, 0.06, 0.08, 0.10, 0.15):
        S = [x for x in O if (x["fair"] or not fair) and x["ep"] - x["po"] >= g and -150 <= x["mlo"] <= 300]
        clv = sum(x["p"] - x["po"] for x in S) / len(S) * 100 if S else 0
        out.bets(f"gap {g*100:.0f}+ at OPEN (clv {clv:+.2f})", gr(S))
        out.bets("    same at CLOSE", gr(S, "ml"))
        for t in "PML":
            T = [x for x in S if x["gtier"] == t]
            c = sum(x["p"] - x["po"] for x in T) / len(T) * 100 if T else 0
            out.bets(f"    tier {t} at OPEN (clv {c:+.2f})", gr(T))
        for side, f in (("home", lambda x: x["side"] == "home" and not x["neutral"]), ("away", lambda x: x["side"] == "away" and not x["neutral"]),
                        ("neutral", lambda x: x["neutral"])):
            T = [x for x in S if f(x)]
            c = sum(x["p"] - x["po"] for x in T) / len(T) * 100 if T else 0
            out.bets(f"    {side} at OPEN (clv {c:+.2f})", gr(T))
        T = [x for x in S if x["mlo"] > 0]
        out.bets("    dogs at OPEN", gr(T))
        T = [x for x in S if x["mlo"] < 0]
        out.bets("    favs at OPEN", gr(T))

out.h("THE SAME ELO GAP AT THE CLOSE, 2018-25 (is it a ratings edge? train 2018-22)")
out.train, out.held = lib.TRAIN, lib.HELD
for g in (0.04, 0.08, 0.10, 0.15):
    S = [x for x in R if x["gn"] >= 4 and x["ogn"] >= 4 and x["ep"] - x["p"] >= g and -150 <= x["ml"] <= 300]
    out.bets(f"elo over the CLOSE {g*100:.0f}+ (graded at close)", gr(S, "ml"))
out.train, out.held = (2023,), (2024, 2025)
out.h("THE HOME DRIFT: mean open->close move per side, and the home side bought at the open")
for t in "PML":
    for v in ("home", "away"):
        S = [x for x in O if x["gtier"] == t and not x["neutral"] and x["side"] == v and x["fair"]]
        mv = sum(x["p"] - x["po"] for x in S) / len(S) * 100
        out.note(f"tier {t} {v}: mean move {mv:+.2f} pts on {len(S)}")
S = [x for x in O if not x["neutral"] and x["side"] == "home" and x["fair"] and -150 <= x["mlo"] <= 300]
out.bets("home side -150..+300 at OPEN (fair)", gr(S))
out.bets("home side -150..+300 at CLOSE (fair)", gr(S, "ml"))
out.save()
