"""STUDY 3 - letdown / lookahead (college hoops, regular season, closing prices; the OPEN 2023-25 the 2nd check).
LETDOWN: the game right after a big win - (a) beat a 'ranked' team (top 25 by the results Elo at that night) as a dog,
(b) any upset win as a +200 dog, (c) beat a ranked team at all; within 4 nights. LOOKAHEAD: this game's opponent is NOT
ranked, this side IS the favorite, and its NEXT game (the schedule is known) is vs a ranked team (Elo as of tonight) -
within 4 nights, both games home / road and before Mar 1 (a bracket's next game exists only for the winner - excluded);
the 'marquee' cut = that next game is a conference game. The early slice: a ranked
upset in Nov-Dec (the owner's opening-weeks focus)."""
import lib
from collections import defaultdict

ALL = lib.build()
R = lib.regular(ALL)
o = lib.Out("s3")
last_elo = {}         # (season, team) -> list of (night, elo before that game) for the 'Elo as of tonight' lookup
for x in ALL:
    last_elo.setdefault((x["season"], x["team"]), []).append((x["night"], x["elo"]))


def elo_asof(s, t, night):
    v = None
    for n, e in last_elo.get((s, t), []):
        if n <= night:
            v = e
        else:
            break
    return v


def trio(name, sub):
    o.c(f"{name} | ATS", lib.spreads(sub), lib.profit_ats)
    o.c(f"{name} | dog +100..+350", lib.dogs(sub))
    o.c(f"{name} | fav -101..-150", lib.favs(sub))
    o.c(f"{name} | fav -151..-400", [x for x in sub if x.get("ml") is not None and -400 <= x["ml"] <= -151])


def prev(x):
    return ALL[x["prev_i"]] if x.get("prev_i") is not None else None


o.h("A. LETDOWN - the next game after a big win (within 4 nights)")
base_after_win = [x for x in R if prev(x) and prev(x)["won"] and x["night"] - prev(x)["night"] <= 4]
trio("after ANY win (base)", base_after_win)
trio("after beating a ranked team as a dog", [x for x in base_after_win if prev(x)["orank25"] and (prev(x).get("ml") or 0) > 0])
trio("after beating a ranked team (any price)", [x for x in base_after_win if prev(x)["orank25"]])
trio("after a +200 upset win", [x for x in base_after_win if (prev(x).get("ml") or 0) >= 200])
trio("after a ranked upset, Nov-Dec", [x for x in base_after_win if prev(x)["orank25"] and (prev(x).get("ml") or 0) > 0
                                     and prev(x)["start"][5:7] in ("11", "12")])
trio("after a ranked upset, next is ON THE ROAD", [x for x in base_after_win if prev(x)["orank25"] and (prev(x).get("ml") or 0) > 0
                                                 and x["venue"] == "away"])
trio("after a ranked upset, next vs an UNRANKED team", [x for x in base_after_win if prev(x)["orank25"] and (prev(x).get("ml") or 0) > 0
                                                      and not x["orank25"]])
o.h("A2. The OPPONENT's view: facing a team off a ranked upset (the other side)")
BYID = {(x["id"], x["team"]): x for x in ALL}
opp_up = []
for x in R:
    ol = x.get("olast")
    if not ol or x["night"] - ol["night"] > 4 or not ol["won"] or (ol.get("ml") or 0) <= 0:
        continue
    pr = BYID.get((ol["id"], x["opp"]))
    if pr and pr["orank25"]:
        opp_up.append(x)
trio("vs a team off a ranked upset", opp_up)

o.h("B. LOOKAHEAD - the favorite vs an unranked team, a ranked team next")
look, look_mq, base_f = [], [], []
for x in R:
    if x.get("next_i") is None or x["orank25"] or x.get("ml") is None or x["ml"] >= 0:
        continue
    nx = ALL[x["next_i"]]
    if nx["night"] - x["night"] > 4:
        continue
    # NO BRACKETS: in a tournament (early-season event, conference tournament) the next game exists only if you WIN
    # tonight - a look-ahead leak (the first run had +17.7% / +22.7% from exactly that). Home / road both games, before
    # Mar 1 (some conference tournaments open on campus).
    if x["neutral"] or nx["neutral"] or x["start"][5:7] in ("03", "04"):
        continue
    base_f.append(x)
    cut = x.get("cut25")
    ne = elo_asof(x["season"], nx["opp"], x["night"])
    if cut is None or ne is None or ne < cut:
        continue
    look.append(x)
    if nx["same_conf"]:
        look_mq.append(x)
trio("favorite vs unranked, next game within 4 nights (base)", base_f)
trio("favorite vs unranked, a RANKED team next", look)
trio("favorite vs unranked, a ranked CONFERENCE team next", look_mq)
trio("favorite vs unranked, ranked next, tonight on the ROAD", [x for x in look if x["venue"] == "away"])
trio("favorite vs unranked, ranked next, Nov-Dec", [x for x in look if x["start"][5:7] in ("11", "12")])
o.h("C. SANDWICH - ranked last game AND ranked next game, unranked tonight")
sw = [x for x in look if prev(x) and prev(x)["orank25"] and x["night"] - prev(x)["night"] <= 4]
trio("sandwich (ranked - unranked - ranked)", sw)
o.save()
