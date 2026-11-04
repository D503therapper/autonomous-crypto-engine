"""S1 - TEAMS IN SHAMBLES (the owner, 11/4: "teams that are in shambles with stuff going on with the players and the
transfers and the coaches"): turmoil read from the box scores - rotation men who vanished (0 minutes 3+ games running),
men LOST in the last 3 weeks, fresh absences, lineup churn, starters shuffled - on the team's own sides and on the side
ACROSS it (is that dog a buy?). The news feed (data/sports/news.json) holds 2 college hoops items and no archive -
nothing to test there; its live form is a field + a tracker. Box years: train 2021-22, held 2023-25."""
import lib

rows = [x for x in lib.boxed(lib.build()) if x.get("pbox_n", 0) >= 5 and x.get("opp_vanished") is not None]
out = lib.Out("s1")
out.h("the table: priced sides with 5+ player-box games on both teams")
out.note(f"rows {len(rows)}; dogs {len(lib.dogs(rows))}, favs -101..-150 {len(lib.favs(rows))}, spreads {len(lib.spreads(rows))}")
lib.three("base (every side)", rows, out)

out.h("A. the team's OWN sides by how many regulars vanished (0 minutes, the last 3+ games)")
for lo, hi, nm in ((0, 0, "none"), (1, 1, "1"), (2, 2, "2"), (3, 99, "3+")):
    lib.three(f"vanished {nm}", [x for x in rows if lo <= x["vanished"] <= hi], out)

out.h("B. LOST LATELY: regulars gone whose last game was within 21 days (the shambles read)")
for lo, hi, nm in ((1, 1, "1"), (2, 2, "2"), (3, 99, "3+"), (2, 99, "2+")):
    lib.three(f"lost3w {nm}", [x for x in rows if lo <= x["lost3w"] <= hi], out)
lib.three("lost3w 2+, Jan-Mar", [x for x in rows if x["lost3w"] >= 2 and lib.month(x) in ("01", "02", "03")], out)
lib.three("lost3w 2+, Nov-Dec", [x for x in rows if x["lost3w"] >= 2 and lib.month(x) in ("11", "12")], out)
lib.three("lost3w 2+ AND top scorer in (top_out False)", [x for x in rows if x["lost3w"] >= 2 and x.get("top_out") is False], out)

out.h("C. THE SIDE ACROSS a team in shambles (the owner's dog)")
for lo, hi, nm in ((1, 1, "1"), (2, 2, "2"), (3, 99, "3+"), (2, 99, "2+")):
    lib.three(f"opp lost3w {nm}", [x for x in rows if lo <= (x["opp_lost3w"] or 0) <= hi], out)
lib.three("opp vanished 3+", [x for x in rows if (x["opp_vanished"] or 0) >= 3], out)
lib.three("opp vanished 2+ (any age)", [x for x in rows if (x["opp_vanished"] or 0) >= 2], out)
lib.three("opp lost3w 2+ AND opp top scorer in", [x for x in rows if (x["opp_lost3w"] or 0) >= 2 and x.get("opp_top_out") is False], out)
lib.three("opp lost3w 2+, dog at home", [x for x in rows if (x["opp_lost3w"] or 0) >= 2 and x["venue"] == "home"], out)
lib.three("opp lost3w 2+, dog on the road", [x for x in rows if (x["opp_lost3w"] or 0) >= 2 and x["venue"] == "away"], out)

out.h("D. FRESH ABSENCES (played 2 games ago, sat the last) - the own side and across")
for n in (1, 2):
    lib.three(f"fresh_abs {n}+", [x for x in rows if x["fresh_abs"] >= n], out)
    lib.three(f"opp fresh_abs {n}+", [x for x in rows if (x["opp_fresh_abs"] or 0) >= n], out)

out.h("E. CHURN (the last game's minutes outside the season's top 7) and starters shuffled")
for lo, hi, nm in ((0.0, 0.15, "<15%"), (0.15, 0.30, "15-30%"), (0.30, 1.01, "30%+")):
    lib.three(f"churn {nm}", [x for x in rows if lo <= x["churn"] < hi], out)
lib.three("starters used (last 5) 8+", [x for x in rows if x["starters_used5"] >= 8], out)
lib.three("starters used (last 5) 5 (one lineup)", [x for x in rows if x["starters_used5"] <= 5], out)

out.h("F. THE STACK - shambles both ways: lost3w 2+ vs an opponent with none")
lib.three("lost3w 2+ vs opp lost3w 0", [x for x in rows if x["lost3w"] >= 2 and (x["opp_lost3w"] or 0) == 0], out)
lib.three("lost3w 0 vs opp lost3w 2+", [x for x in rows if x["lost3w"] == 0 and (x["opp_lost3w"] or 0) >= 2], out)
out.save()
