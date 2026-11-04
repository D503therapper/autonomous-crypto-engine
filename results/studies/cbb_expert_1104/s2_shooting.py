"""S2 - HOT SHOOTING / FORM (the owner, 11/4: "away teams that come in and upset and are playing really good and
shooting with really good percentage"): a team's last 3-5 games of eFG% / 3P% / FT% vs its own season and vs the
defenses it faced, shot quality (2P% / free-throw rate - the sustainable half) apart from 3P luck; the hot dog vs a
cold favorite; the matchup of my shooting vs their defense. Team box 2021-26: train 2021-22, held 2023-25."""
import lib

rows = [x for x in lib.boxed(lib.build()) if x.get("efg5") is not None and x.get("opp_efg5") is not None]
out = lib.Out("s2")
out.h("the table: priced sides, both teams 5+ team-box games")
out.note(f"rows {len(rows)}; dogs {len(lib.dogs(rows))}, favs {len(lib.favs(rows))}, spreads {len(lib.spreads(rows))}")
lib.three("base", rows, out)


def d_efg(x):
    return x["efg5"] - x["efg_s"]


def d_tp(x):
    return (x["tp5"] - x["tp_s"]) if x.get("tp5") is not None and x.get("tp_s") is not None else None


def d_two(x):
    return (x["two5"] - x["two_s"]) if x.get("two5") is not None and x.get("two_s") is not None else None


def d_ft(x):
    return (x["ft5"] - x["ft_s"]) if x.get("ft5") is not None and x.get("ft_s") is not None else None


out.h("A. HOT / COLD eFG% over the last 5 vs the season (raw)")
for lo, hi, nm in ((-1, -0.04, "cold -4+"), (-0.04, -0.015, "-4..-1.5"), (-0.015, 0.015, "flat"), (0.015, 0.04, "+1.5..4"), (0.04, 1, "hot +4+")):
    lib.three(f"eFG last5 - season {nm}", [x for x in rows if lo <= d_efg(x) < hi], out)
lib.three("eFG last3 - season +5+", [x for x in rows if x["efg3"] - x["efg_s"] >= 0.05], out)
lib.three("eFG last3 - season -5-", [x for x in rows if x["efg3"] - x["efg_s"] <= -0.05], out)

out.h("B. 3P LUCK vs SHOT QUALITY: hot by threes only, hot by twos only, free throws")
tp_hot = [x for x in rows if (d_tp(x) or 0) >= 0.06]
tp_cold = [x for x in rows if (d_tp(x) or 0) <= -0.06]
two_hot = [x for x in rows if (d_two(x) or 0) >= 0.05]
two_cold = [x for x in rows if (d_two(x) or 0) <= -0.05]
lib.three("3P% last5 - season +6+ (hot from deep)", tp_hot, out)
lib.three("3P% last5 - season -6- (cold from deep)", tp_cold, out)
lib.three("2P% last5 - season +5+ (hot inside)", two_hot, out)
lib.three("2P% last5 - season -5- (cold inside)", two_cold, out)
lib.three("hot from deep, NOT inside (3P luck)", [x for x in tp_hot if (d_two(x) or 0) < 0.02], out)
lib.three("hot inside, NOT from deep (shot quality)", [x for x in two_hot if (d_tp(x) or 0) < 0.02], out)
lib.three("FT% last5 - season +8+", [x for x in rows if (d_ft(x) or 0) >= 0.08], out)
lib.three("FT% last5 - season -8-", [x for x in rows if (d_ft(x) or 0) <= -0.08], out)
lib.three("FT rate last5 - season +0.08 (getting to the line)", [x for x in rows if x.get("ftr5") is not None and x["ftr5"] - x["ftr_s"] >= 0.08], out)

out.h("C. OVER THE DEFENSES FACED (adj5 = eFG minus what each opponent allowed at the time)")
for lo, hi, nm in ((-1, -0.05, "-5-"), (-0.05, -0.02, "-5..-2"), (-0.02, 0.02, "flat"), (0.02, 0.05, "+2..5"), (0.05, 1, "+5+")):
    lib.three(f"adj5 {nm}", [x for x in rows if x.get("adj5") is not None and lo <= x["adj5"] < hi], out)
lib.three("adj5 +5+ AND adj season under +2 (a real hot streak over good D)", [x for x in rows if x.get("adj5") is not None and x["adj5"] >= 0.05 and (x.get("adj_s") or 0) < 0.02], out)

out.h("D. THE MATCHUP: my season eFG vs the eFG their defense allows (both season to date)")
for lo, hi, nm in ((-1, -0.06, "-6-"), (-0.06, -0.02, "-6..-2"), (-0.02, 0.02, "flat"), (0.02, 0.06, "+2..6"), (0.06, 1, "+6+")):
    lib.three(f"my eFG - their D allows {nm}", [x for x in rows if x.get("odefg_s") is not None and lo <= x["efg_s"] - x["odefg_s"] < hi], out)

out.h("E. THE DOG SHOOTING WELL vs A FAVORITE IN A COLD STRETCH (the owner's spot)")
hot_dog = [x for x in rows if d_efg(x) >= 0.03]
cold_opp = [x for x in rows if x["opp_efg5"] - x["opp_efg_s"] <= -0.03]
lib.three("me hot +3, opp cold -3", [x for x in hot_dog if x["opp_efg5"] - x["opp_efg_s"] <= -0.03], out)
lib.three("me hot +3, opp cold -3, I'm on the road", [x for x in hot_dog if x["opp_efg5"] - x["opp_efg_s"] <= -0.03 and x["venue"] == "away"], out)
lib.three("me cold -3, opp hot +3", [x for x in rows if d_efg(x) <= -0.03 and x["opp_efg5"] - x["opp_efg_s"] >= 0.03], out)
lib.three("opp cold -3 (any me)", cold_opp, out)
lib.three("opp hot +3 (any me)", [x for x in rows if x["opp_efg5"] - x["opp_efg_s"] >= 0.03], out)
lib.three("hot road dog +3 (me hot, on the road)", [x for x in hot_dog if x["venue"] == "away"], out)
lib.three("hot dog by TWOS on the road", [x for x in two_hot if x["venue"] == "away"], out)
lib.three("hot dog by THREES on the road", [x for x in tp_hot if x["venue"] == "away"], out)

out.h("F. by phase: Nov-Dec vs Jan-Mar for the hot / cold eFG cuts")
for ph, ms in (("Nov-Dec", ("11", "12")), ("Jan-Mar", ("01", "02", "03"))):
    lib.three(f"hot +4 {ph}", [x for x in rows if d_efg(x) >= 0.04 and lib.month(x) in ms], out)
    lib.three(f"cold -4 {ph}", [x for x in rows if d_efg(x) <= -0.04 and lib.month(x) in ms], out)
out.save()
