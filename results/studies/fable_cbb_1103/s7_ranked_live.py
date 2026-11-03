"""S7 - THE RANKED ROAD SIDE WITH THE ENGINE'S OWN ELO (sports_model.Elo, k 22 / hfa 80 / the 1/3 offseason regression
from data/sports/model.json) - the live definition: 'ranked' = top 25 by the engine's rating among D1 teams with 3+
games this season, on the night of the game; 'road' = the away side of a non-neutral game. Re-grades S6 A: all / Nov-Dec
/ Jan-Mar, the overlap with the built Nov-Dec away-favorite weight (ML band), the dose by rank, the spread size, and
the side across. Regular season 2018-26 at ESPN's close."""
import json, os, sys
from collections import defaultdict
import lib

sys.path.insert(0, lib.ROOT)
import sports_model as sm  # noqa: E402

rows = lib.regular(lib.build())
o = lib.Out("s7")
params = json.load(open(os.path.join(lib.ROOT, "data/sports/model.json")))["params"]["ncaab"]
gs = lib.B.load_games()
elo = sm.Elo(params["k"], params["hfa"], "ncaab")
gp = defaultdict(int)                      # (season, team) -> games this season so far
rank = {}                                  # (game id, team) -> True if top 25 that night
cur_night, snap = None, None
for g in gs:
    key = (g["season"], g["night"])
    if key != cur_night:
        s = g["season"]
        pool = sorted((elo.r.get(t, 1500.0) for (ss, t), n in gp.items() if ss == s and n >= 3), reverse=True)
        snap = pool[24] if len(pool) >= 25 else None
        cur_night = key
    for t in (g["home"], g["away"]):
        rank[(g["id"], t)] = snap is not None and elo.r.get(t, 1500.0) >= snap and gp[(g["season"], t)] >= 3
    try:
        elo.update({"id": g["id"], "start": g["start"], "home": g["home"], "away": g["away"], "home_score": int(g["hs"]),
                    "away_score": int(g["as"]), "neutral": g["neutral"], "elev": g.get("elev"), "wx_temp": g.get("wx_temp"),
                    "tzo": g.get("tzo"), "intl": g.get("intl"), "indoor": g.get("indoor"), "inj_home": "", "inj_away": ""})
    except Exception as e:  # noqa: BLE001
        print("update failed", g["id"], e)
        continue
    for t in (g["home"], g["away"]):
        gp[(g["season"], t)] += 1
agree = sum(1 for x in rows if rank.get((x["id"], x["team"])) == x["rank25"])
o.note(f"engine-Elo top-25 flag vs the study's: agree on {agree} of {len(rows)} sides ({agree / len(rows):.3f})")
for x in rows:
    x["erank"] = rank.get((x["id"], x["team"]), False)
    x["oerank"] = rank.get((x["id"], x["opp"]), False)
SP = lib.spreads(rows)
DG = lib.dogs(rows)
RR = [x for x in SP if x["erank"] and x["venue"] == "away"]
ND = ("11", "12")
o.h("A. The engine-ranked road side, ATS")
o.c("ATS ranked road side (engine Elo)", RR, lib.profit_ats)
o.c("ATS ranked road, Nov-Dec", [x for x in RR if x["start"][5:7] in ND], lib.profit_ats)
o.c("ATS ranked road, Jan-Mar", [x for x in RR if x["start"][5:7] not in ND], lib.profit_ats)
o.c("ATS ranked road, non-conference (inferred)", [x for x in RR if not x["same_conf"]], lib.profit_ats)
o.c("ATS ranked road, Nov-Dec, non-conference", [x for x in RR if x["start"][5:7] in ND and not x["same_conf"]], lib.profit_ats)
o.c("ATS ranked road, Nov-Dec, same conference", [x for x in RR if x["start"][5:7] in ND and x["same_conf"]], lib.profit_ats)
o.c("ATS ranked road, Jan-Mar, non-conference", [x for x in RR if x["start"][5:7] not in ND and not x["same_conf"]], lib.profit_ats)
o.h("B. The overlap with the built Nov-Dec away-favorite weight (ML -101..-150) - Nov-Dec ranked road by ML band")
NDR = [x for x in RR if x["start"][5:7] in ND and x.get("ml") is not None]
for lo, hi in ((-150, -101), (-250, -151), (-500, -251), (-5000, -501), (100, 350)):
    o.c(f"ATS ranked road Nov-Dec, ML {lo}..{hi}", [x for x in NDR if lo <= x["ml"] <= hi], lib.profit_ats)
    o.c(f"ML  ranked road Nov-Dec, ML {lo}..{hi}", [x for x in NDR if lo <= x["ml"] <= hi])
o.c("ATS ranked road Nov-Dec, ML under -150 (outside the built weight)", [x for x in NDR if x["ml"] < -150], lib.profit_ats)
o.c("ATS UNRANKED road favorite Nov-Dec, ML under -150 (the base)", [x for x in SP if not x["erank"] and x["venue"] == "away" and x["start"][5:7] in ND
                                                                       and x.get("ml") is not None and x["ml"] < -150], lib.profit_ats)
o.c("ATS UNRANKED road favorite Nov-Dec, ML -101..-150", [x for x in SP if not x["erank"] and x["venue"] == "away" and x["start"][5:7] in ND
                                                             and x.get("ml") is not None and -150 <= x["ml"] <= -101], lib.profit_ats)
o.h("C. Dose: the spread the ranked road side lays, Nov-Dec and all")
for lo, hi in ((-99, -12), (-12, -7), (-7, -3), (-3, 0), (0, 99)):
    o.c(f"ATS ranked road, spread {lo}..{hi}", [x for x in RR if lo <= x["sp"] < hi], lib.profit_ats)
    o.c(f"ATS ranked road Nov-Dec, spread {lo}..{hi}", [x for x in RR if x["start"][5:7] in ND and lo <= x["sp"] < hi], lib.profit_ats)
o.h("D. The side across: the home team vs an engine-ranked road team")
HV = [x for x in SP if x["oerank"] and x["venue"] == "home"]
o.c("ATS home vs ranked road", HV, lib.profit_ats)
o.c("ATS home vs ranked road, Nov-Dec", [x for x in HV if x["start"][5:7] in ND], lib.profit_ats)
o.c("ML home dog +100..+350 vs ranked road", [x for x in DG if x["oerank"] and x["venue"] == "home"])
o.c("ML home dog +100..+350 vs ranked road, Nov-Dec", [x for x in DG if x["oerank"] and x["venue"] == "home" and x["start"][5:7] in ND])
o.c("ML home dog +100..+200 vs ranked road, Nov-Dec", [x for x in DG if x["oerank"] and x["venue"] == "home" and x["start"][5:7] in ND and x["ml"] <= 200])
o.c("ML home dog +100..+350 vs ranked road, Jan-Mar", [x for x in DG if x["oerank"] and x["venue"] == "home" and x["start"][5:7] not in ND])
o.h("E. The engine-ranked side elsewhere (the mirror / the neutral site)")
o.c("ATS ranked side at home", [x for x in SP if x["erank"] and x["venue"] == "home"], lib.profit_ats)
o.c("ATS ranked side at home, Nov-Dec", [x for x in SP if x["erank"] and x["venue"] == "home" and x["start"][5:7] in ND], lib.profit_ats)
o.c("ATS ranked side, neutral", [x for x in SP if x["erank"] and x["venue"] == "neutral"], lib.profit_ats)
o.c("ATS ranked side, neutral, Nov-Dec", [x for x in SP if x["erank"] and x["venue"] == "neutral" and x["start"][5:7] in ND], lib.profit_ats)
o.c("ATS ranked side, neutral, Nov-Dec, vs an unranked team", [x for x in SP if x["erank"] and not x["oerank"] and x["venue"] == "neutral" and x["start"][5:7] in ND], lib.profit_ats)
o.h("F. By rank depth (the engine's rating over the top-25 cut) and the current season")
o.c("ATS ranked road Nov-Dec, vs an UNRANKED home team", [x for x in RR if x["start"][5:7] in ND and not x["oerank"]], lib.profit_ats)
o.c("ATS ranked road Nov-Dec, vs a RANKED home team", [x for x in RR if x["start"][5:7] in ND and x["oerank"]], lib.profit_ats)
o.c("ATS ranked road Nov-Dec, team's games 1-5", [x for x in RR if x["start"][5:7] in ND and x["gn"] <= 5], lib.profit_ats)
o.c("ATS ranked road Nov-Dec, team's games 6+", [x for x in RR if x["start"][5:7] in ND and x["gn"] >= 6], lib.profit_ats)
o.c("ATS ranked road Nov-Dec, 2026 so far", [x for x in RR if x["start"][5:7] in ND and x["season"] == 2026], lib.profit_ats)
o.note(f"ranked road Nov-Dec sides a season: " + ", ".join(f"{s}:{sum(1 for x in RR if x['season'] == s and x['start'][5:7] in ND)}" for s in range(2018, 2027)))
o.save()
