"""S2 - AVAILABILITY IN-SEASON, from the box scores (2021-26; the college hoops injury reports on file start 10/28/2026,
so the history is who was in the box). REGULARS = the team's top 7 by minutes a game this season before tonight (3+ box
games, 15+ a game). Known before tip: how many regulars missed the LAST game (out_last), how many have missed the last
2+ / 4+ games (a stretch), whether the top scorer is among them (the built 11/3 weight - cut out here to see what's NEW),
the opponent's same numbers. Ex post (tonight's box - a 'did the line move enough' read, not a bet): a regular BACK after
a 2+ game absence, a NEW absence. Train 2021-22, held out 2023 / 2024 / 2025; ESPN's ML open 2023-25 on dog cells."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403

out = Out("s2")
box = playerbox()
rows_ = [x for x in regular(rows()) if x["season"] >= 2021]
rows_.sort(key=lambda x: (x["start"], x["id"]))
by_team = defaultdict(list)
for x in rows_:
    by_team[(x["season"], x["team"])].append(x)
feat = {}
for (s, tm), xs in by_team.items():
    hist = []                      # [(gid, {pid: min})] earlier games with a box
    for x in xs:
        b = (box.get(x["id"]) or {}).get(tm)
        f = {"has_box": b is not None, "nbox": len(hist)}
        if len(hist) >= 3:
            mp = defaultdict(lambda: [0, 0])
            for _, hb in hist:
                for pid, m in hb.items():
                    if m > 0:
                        mp[pid][0] += 1
                        mp[pid][1] += m
            cand = sorted(((v[1] / len(hist), pid) for pid, v in mp.items() if v[1] / len(hist) >= 15), reverse=True)
            regs = [pid for _, pid in cand[:7]]
            top = max(((v[1], pid) for pid, v in mp.items()), default=(0, None))[1]   # (minutes leader, not the scorer)
            played = lambda hb, p: (hb.get(p) or 0) > 0
            miss_run = {}
            for p in regs:
                r = 0
                for _, hb in reversed(hist):
                    if played(hb, p):
                        break
                    r += 1
                miss_run[p] = r
            f["regs"] = regs
            f["out_last"] = sum(1 for p in regs if miss_run[p] >= 1)
            f["out_2"] = sum(1 for p in regs if miss_run[p] >= 2)
            f["out_4"] = sum(1 for p in regs if miss_run[p] >= 4)
            f["min_out"] = sum(mp[p][1] / len(hist) for p in regs if miss_run[p] >= 1)
            f["top_min_out"] = top in regs and miss_run.get(top, 0) >= 1
            if b is not None:
                now = {pid: v[0] for pid, v in b.items()}
                f["back"] = sum(1 for p in regs if miss_run[p] >= 2 and played(now, p))
                f["back1"] = sum(1 for p in regs if miss_run[p] == 1 and played(now, p))
                f["new_out"] = sum(1 for p in regs if miss_run[p] == 0 and not played(now, p))
                f["out_now"] = sum(1 for p in regs if not played(now, p))
        feat[(x["id"], tm)] = f
        if b is not None:
            hist.append((x["id"], {pid: v[0] for pid, v in b.items()}))
for x in rows_:
    x["f"] = feat.get((x["id"], x["team"]), {})
    x["of"] = feat.get((x["id"], x["opp"]), {})
have = [x for x in rows_ if "out_last" in x["f"] and "out_last" in x["of"]]
out.note(f"sides 2021+ {len(rows_)}, both teams with 3+ box games {len(have)}; "
         f"out_last 0/1/2/3+: {sum(1 for x in have if x['f']['out_last']==0)} / {sum(1 for x in have if x['f']['out_last']==1)} / "
         f"{sum(1 for x in have if x['f']['out_last']==2)} / {sum(1 for x in have if x['f']['out_last']>=3)}")
# the 11/3 built flag (top SCORER missed the last game) - approximated by 'the minutes leader missed': keep it out
clean = [x for x in have if not x["f"]["top_min_out"] and not x["of"]["top_min_out"]]
month = lambda x: x["start"][5:7]

out.h("A. REGULARS OUT OF THE LAST GAME (known before tip) - the base: nobody out on either side")
base = [x for x in clean if x["f"]["out_last"] == 0 and x["of"]["out_last"] == 0]
by_season_ats(base, "base: no regular out, either side", out)
for k, lab in ((1, "1 regular out"), (2, "2 regulars out"), (3, "3+ regulars out")):
    sub = [x for x in clean if (x["f"]["out_last"] == k if k < 3 else x["f"]["out_last"] >= 3)]
    by_season_ats(sub, f"{lab} last game (minutes leader in)", out)
sub2 = [x for x in clean if x["f"]["out_last"] >= 2]
by_season_ats([x for x in sub2 if x["of"]["out_last"] == 0], "2+ out vs a whole opponent", out)
by_season_ats([x for x in sub2 if x["f"]["min_out"] >= 50], "2+ out, 50+ minutes a game missing", out)
by_season_ats([x for x in sub2 if month(x) in ("11", "12")], "2+ out, Nov-Dec", out)
by_season_ats([x for x in sub2 if month(x) in ("01", "02", "03")], "2+ out, Jan-Mar", out)
for t in ("power", "mid", "low"):
    by_season_ats([x for x in sub2 if x["tier"] == t], f"2+ out, {t} tier", out)
out.c("2+ out, fav -151..-300 ML", favs(sub2, -300, -151))
out.c("2+ out, dog +100..+200 ML", dogs(sub2, 100, 200))
out.c("2+ out, dog +201..+350 ML", dogs(sub2, 201, 350))
# the side ACROSS a banged-up team
across = [x for x in clean if x["of"]["out_last"] >= 2 and x["f"]["out_last"] == 0]
by_season_ats(across, "whole team vs 2+ regulars out", out)
out.c("whole team vs 2+ out, fav -151..-300 ML", favs(across, -300, -151))
out.c("whole team vs 2+ out, fav -301..-600 ML", favs(across, -600, -301))
# with the built top-scorer flag IN (the overlap)
top_in = [x for x in have if x["f"]["top_min_out"]]
by_season_ats(top_in, "the minutes leader out of the last game (near the built top-scorer weight)", out)
by_season_ats([x for x in top_in if x["f"]["out_last"] >= 2], "minutes leader + another regular out", out)

out.h("B. THE STRETCH - regulars out 2+ / 4+ games running (does the market catch up, or over-shoot?)")
st2 = [x for x in clean if x["f"]["out_2"] >= 1]
st4 = [x for x in clean if x["f"]["out_4"] >= 1]
by_season_ats([x for x in clean if x["f"]["out_last"] >= 1 and x["f"]["out_2"] == 0], "a regular's FIRST missed game (fresh)", out)
by_season_ats([x for x in st2 if x["f"]["out_4"] == 0], "a regular out 2-3 games running", out)
by_season_ats(st4, "a regular out 4+ games running", out)
by_season_ats([x for x in clean if x["f"]["out_4"] >= 2], "2+ regulars out 4+ games running", out)
by_season_ats([x for x in clean if x["f"]["out_2"] >= 2], "2+ regulars out 2+ games running", out)
by_season_ats([x for x in st4 if x["f"]["out_last"] == x["f"]["out_4"]], "4+ game absences only (nothing fresh)", out)
out.c("a regular out 4+ games, dog +100..+350, Jan-Mar", [x for x in dogs(st4) if month(x) in ("01", "02", "03")])
out.c("a regular out 4+ games, fav -101..-150", favs(st4))
out.c("the side across a 4+ game absence, ATS", [x for x in spreads(clean) if x["of"]["out_4"] >= 1 and x["f"]["out_last"] == 0], profit_ats)
out.c("the side across a 4+ game absence, dog +100..+350", [x for x in dogs(clean) if x["of"]["out_4"] >= 1 and x["f"]["out_last"] == 0])
out.c("the side across a FRESH absence (1st missed game), ATS", [x for x in spreads(clean) if x["of"]["out_last"] >= 1 and x["of"]["out_2"] == 0 and x["f"]["out_last"] == 0], profit_ats)
out.c("the side across a FRESH absence, dog +100..+350", [x for x in dogs(clean) if x["of"]["out_last"] >= 1 and x["of"]["out_2"] == 0 and x["f"]["out_last"] == 0])
out.c("the side across a FRESH absence, fav -101..-150", [x for x in favs(clean) if x["of"]["out_last"] >= 1 and x["of"]["out_2"] == 0 and x["f"]["out_last"] == 0])
out.c("the side across 2+ fresh absences, fav -101..-200", [x for x in favs(clean, -200, -101) if x["of"]["out_last"] >= 2 and x["of"]["out_2"] == 0 and x["f"]["out_last"] == 0])

out.h("C. THE FIRST GAME BACK (ex post: a regular who missed 2+ games is in tonight's box) - is the line slow / fast?")
boxed = [x for x in clean if "back" in x["f"] and "back" in x["of"]]
bk = [x for x in boxed if x["f"]["back"] >= 1]
by_season_ats(bk, "a regular back after 2+ games (ex post)", out)
by_season_ats([x for x in boxed if x["f"]["back1"] >= 1 and x["f"]["back"] == 0], "a regular back after ONE game (ex post)", out)
by_season_ats([x for x in bk if x["f"]["out_now"] == 0], "back after 2+ and the whole team plays (ex post)", out)
by_season_ats([x for x in boxed if x["f"]["new_out"] >= 1 and x["f"]["out_last"] == 0], "a NEW absence tonight, nobody out last game (ex post)", out)
by_season_ats([x for x in boxed if x["f"]["new_out"] >= 2], "2+ NEW absences tonight (ex post)", out)
# pre-tip proxy of 'back': the regular has missed exactly 2-3 games (the typical minor injury) - plays or not
pre = [x for x in clean if any(True for _ in [0]) and x["f"]["out_2"] >= 1 and x["f"]["out_4"] == 0]
by_season_ats([x for x in pre if x["f"].get("back", 0) >= 1], "missed 2-3 games: the ones who came back tonight (ex post)", out)
by_season_ats([x for x in pre if "back" in x["f"] and x["f"]["back"] == 0], "missed 2-3 games: still out tonight (ex post)", out)
# the market's reaction: the open vs the close on flagged dogs (held seasons)
def mv(xs, lab):
    v = [x["p"] - x["po"] for x in xs if x.get("po") is not None and x.get("p") is not None]
    if v:
        out.note(f"   {lab}: the close moved {sum(v)/len(v)*100:+.2f} win-% from the open on {len(v)} sides")
mv([x for x in clean if x["f"]["out_last"] >= 2], "2+ regulars out of the last game")
mv([x for x in clean if x["f"]["out_last"] == 0 and x["of"]["out_last"] >= 2], "the side across 2+ out")
mv(bk, "a regular back after 2+ (ex post)")
mv([x for x in boxed if x["f"]["new_out"] >= 1 and x["f"]["out_last"] == 0], "a new absence (ex post)")
out.save()
