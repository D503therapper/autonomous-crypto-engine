"""S4 - STARS AND INJURIES, DEEPER (the owner, 11/4: "star players and injuries"): the star's usage share (his share of
the team's shots), the drop-off to the next man, the star RETURNING (tonight his 2nd game back - pre-tip; his 1st game
back - ex post, only the news could flag it), and the opponent's star out as a dog boost. Built on top of top_out /
long_out (the 11/3 weights) - not redone. Player box 2021-26: train 2021-22, held 2023-25."""
import lib

rows = [x for x in lib.boxed(lib.build()) if x.get("top_fga") is not None and x.get("opp_top_fga") is not None]
out = lib.Out("s4")
out.h("the table: priced sides, both teams 5+ player-box games with a top scorer (3+ games, 20+ min)")
out.note(f"rows {len(rows)}; dogs {len(lib.dogs(rows))}, favs {len(lib.favs(rows))}, spreads {len(lib.spreads(rows))}")
lib.three("base", rows, out)

out.h("A. USAGE: the top scorer's share of the team's shots (season to date)")
for lo, hi, nm in ((0, 0.20, "<20%"), (0.20, 0.25, "20-25%"), (0.25, 0.30, "25-30%"), (0.30, 1, "30%+")):
    lib.three(f"top scorer's FGA share {nm}", [x for x in rows if lo <= x["top_fga"] < hi], out)
out.h("B. THE DROP-OFF: points a game, the top man over the 2nd")
for lo, hi, nm in ((0, 2, "<2"), (2, 5, "2-5"), (5, 8, "5-8"), (8, 99, "8+")):
    lib.three(f"star gap {nm} ppg", [x for x in rows if lo <= x["star_gap"] < hi], out)

out.h("C. TOP SCORER OUT (missed the last game - the built weight) BY USAGE / DROP-OFF: is the fade bigger for a bigger star?")
to = [x for x in rows if x["top_out"]]
lib.three("top_out (all)", to, out)
lib.three("top_out, FGA share 25%+", [x for x in to if x["top_fga"] >= 0.25], out)
lib.three("top_out, FGA share under 25%", [x for x in to if x["top_fga"] < 0.25], out)
lib.three("top_out, star gap 5+ ppg", [x for x in to if x["star_gap"] >= 5], out)
lib.three("top_out, star gap under 5", [x for x in to if x["star_gap"] < 5], out)
lib.three("top_out, missed 1 game only (fresh)", [x for x in to if x.get("miss_run") == 1], out)
lib.three("top_out, missed 2-4 games", [x for x in to if 2 <= (x.get("miss_run") or 0) <= 4], out)
lib.three("top_out, missed 5+ games", [x for x in to if (x.get("miss_run") or 0) >= 5], out)

out.h("D. THE OPPONENT'S STAR OUT - the dog boost (the side across a team whose top scorer missed its last game)")
oto = [x for x in rows if x["opp_top_out"]]
lib.three("opp top_out (all)", oto, out)
lib.three("opp top_out, their FGA share 25%+", [x for x in oto if x["opp_top_fga"] >= 0.25], out)
lib.three("opp top_out, their star gap 5+", [x for x in oto if (x["opp_star_gap"] or 0) >= 5], out)
lib.three("opp top_out, I'm at home", [x for x in oto if x["venue"] == "home"], out)
lib.three("opp top_out, I'm on the road", [x for x in oto if x["venue"] == "away"], out)
lib.three("opp top_out AND my top scorer in", [x for x in oto if not x["top_out"]], out)
lib.three("opp top_out AND opp regular out 4+ (both)", [x for x in oto if x.get("opp_long_out")], out)
lib.three("opp top_out, Jan-Mar", [x for x in oto if lib.month(x) in ("01", "02", "03")], out)
lib.three("opp top_out, Nov-Dec", [x for x in oto if lib.month(x) in ("11", "12")], out)

out.h("E. THE STAR RETURNING: tonight is his 2nd game back (he missed 2+, played the last one) - PRE-TIP")
b2 = [x for x in rows if x["back2"]]
lib.three("back2 (all)", b2, out)
lib.three("back2, missed 2-3", [x for x in b2 if (x.get("miss_before") or 0) <= 3], out)
lib.three("back2, missed 4+", [x for x in b2 if (x.get("miss_before") or 0) >= 4], out)
lib.three("back2, FGA share 25%+", [x for x in b2 if x["top_fga"] >= 0.25], out)
lib.three("opp back2 (the side across a returning star's 2nd game)", [x for x in rows if x.get("opp_back2")], out)
out.h("F. THE STAR'S FIRST GAME BACK - EX POST (he plays tonight after missing 2+; the box says so after the fact)")
b1 = [x for x in rows if x["back1"]]
lib.three("back1 (ex post)", b1, out)
lib.three("back1, missed 2-3", [x for x in b1 if (x.get("miss_run") or 0) <= 3], out)
lib.three("back1, missed 4+", [x for x in b1 if (x.get("miss_run") or 0) >= 4], out)
lib.three("top_out but he does NOT play tonight either (ex post: still out)", [x for x in to if not x["back1"]], out)
out.save()
