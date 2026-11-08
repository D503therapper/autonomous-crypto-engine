"""11/8 S4-S7 (never studied - checked against every 'Not re-run' list):
S4 COLLEGE HOOPS WEEK 2 - THE EARLY SURPRISE / FLOP TEAM: a team's AVERAGE cover margin (its margin + its closing spread)
   over every earlier D1 game this season, tonight its game 3-5 (2-4 games played) - when a team first separates from
   its number, does the market keep lagging (back the surprise) or over-correct (fade it)? The 11/5 'early overreaction'
   read ONE game (the last cover margin) - this is the running average; the same cut in games 11-20 the contrast.
S5 NHL - THE UNLUCKY LOSER: lost last game while out-shooting the other team by 12+ (shots = the other goalie's shots
   against); the LUCKY WINNER (won while out-shot by 12+) the mirror. (The built 'allowed 40+ shots' weight is the tired
   goalie; this is the result vs the play.)
S6 NHL - THE BACKUP ON A RESTED NIGHT (the 11/6 projection makes it knowable at 8 AM): tonight's starter is NOT the #1
   (most starts in the last 10 this season, 6+ held, a clear leader), the team NOT on the 2nd night of a back-to-back,
   and the #1 started the team's last game (a first sit - the 11/6 build is the #1 out 2+ straight). The b2b-night backup
   is the control. (The 10/6 role spot weighs the dog-#1 vs favorite-backup pair; this is the rest split.)
S7 NBA - THE STAR'S DUD: the team's top scorer (points a game this season, 5+ games) shot under 35% on 15+ shots last
   game; the side next game (and the opponent facing a star off a dud).
Prices: the game files' close; ESPN's open (2023-26) the second price. TRAIN 2018-22 (box angles 2021-22) / held 2023-26."""
import os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2018, 2022), [2023, 2024, 2025, 2026]
C = lib.Cells()


def add_side(tag, g, side, o, won, s):
    p = lib.profit(won, lib.dec(o))
    if -250 <= o <= -101:
        C.add(f"{tag} | fav -101..-250", s, p)
    if 100 <= o <= 350:
        C.add(f"{tag} | dog +100..+350", s, p)
    C.add(f"{tag} | ATS", s, lib.ats(g, side))
    oo = g["oh"] if side == "home" else g["oa"]
    if oo:
        if -250 <= oo <= -101:
            C.add(f"{tag} | fav OPEN", s, lib.profit(won, lib.dec(oo)))
        if 100 <= oo <= 350:
            C.add(f"{tag} | dog OPEN", s, lib.profit(won, lib.dec(oo)))


def bare(x):
    return str(x).split(":")[-1]


# ---------------- S4 college hoops: the running cover margin
fin = [g for g in lib.finals("ncaab") if g["stype"] == "2"]
cov = defaultdict(list)          # (season, team) -> [(start, cover margin)] in order
for g in fin:
    m = g["hs"] - g["as"]
    for side, team, opp, o, won, home in lib.sides(g):
        sp = g["sp"]
        prior = [c for st, c in cov[(g["season"], team)]]
        n = len(prior)
        if sp is not None and n >= 2 and int(g["start"][5:7]) in (11, 12, 1, 2):
            avg = sum(prior) / n
            win = "games 3-5" if n <= 4 else "games 11-20" if 10 <= n <= 19 else None
            if win:
                for lo, hi, nm in ((8, 99, "beat it by 8+ a game"), (12, 99, "beat it by 12+ a game"),
                                   (-99, -8, "missed it by 8+ a game"), (-99, -12, "missed it by 12+ a game"),
                                   (-4, 4, "within 4 (control)")):
                    if lo <= avg < hi or (hi == 99 and avg >= lo):
                        add_side(f"S4 NCAAB {win} running cover {nm}", g, side, o, won, g["season"])
        if sp is not None:
            c = (m + sp) if side == "home" else (-m - sp)
            cov[(g["season"], team)].append((g["start"], c))

# ---------------- S5 / S6 NHL from the goalie rows (one row a team-game = the starter)
gl = lib.boxes("nhl", lambda st, r: (r["player"], lib.num(st.get("shotsAgainst"))) if r["group"] == "goalies" else None)
start_by = {}                    # (bare gid, bare team) -> (goalie, shots against)
for gid, teams in gl.items():
    for t, pl in teams.items():
        if pl:
            start_by[(bare(gid), bare(t))] = list(pl.values())[0]
fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
allf = lib.all_finals("nhl")
tl = lib.team_log(allf)
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        prev = lib.before(tl, team, g["start"], 12)
        if not prev or prev[-1]["season"] != g["season"]:
            continue
        last = prev[-1]
        # S5
        mine = start_by.get((bare(last["id"]), bare(team)))
        theirs = start_by.get((bare(last["id"]), bare(last["away"] if last["home"] == team else last["home"])))
        if mine and theirs and mine[1] is not None and theirs[1] is not None and last["stype"] == "2":
            shots_for, shots_against = theirs[1], mine[1]
            d = shots_for - shots_against
            w = lib.won_g(last, team)
            if not w and d >= 12:
                add_side("S5 NHL unlucky loser (lost, out-shot them by 12+)", g, side, o, won, g["season"])
                if d >= 18:
                    add_side("S5 NHL ... unlucky loser, by 18+", g, side, o, won, g["season"])
            elif w and d <= -12:
                add_side("S5 NHL lucky winner (won, out-shot by 12+)", g, side, o, won, g["season"])
                if d <= -18:
                    add_side("S5 NHL ... lucky winner, by 18+", g, side, o, won, g["season"])
            elif not w:
                add_side("S5 NHL control: lost, shots within 12", g, side, o, won, g["season"])
            else:
                add_side("S5 NHL control: won, shots within 12", g, side, o, won, g["season"])
        # S6
        tonight = start_by.get((bare(g["id"]), bare(team)))
        same = [x for x in prev[-10:] if x["season"] == g["season"]]
        starts = [start_by.get((bare(x["id"]), bare(team))) for x in same]
        starts = [s[0] for s in starts if s]
        if not tonight or len(starts) < 6:
            continue
        top = Counter(starts).most_common(2)
        if len(top) > 1 and top[0][1] == top[1][1]:
            continue
        n1 = top[0][0]
        b2b = lib.days_between(last["start"], g["start"]) < 1.5
        last_start = start_by.get((bare(last["id"]), bare(team)))
        if tonight[0] != n1:
            first_sit = bool(last_start and last_start[0] == n1)
            nm = f"S6 NHL backup tonight, {'2nd night of a b2b' if b2b else 'RESTED night'}"
            add_side(nm, g, side, o, won, g["season"])
            if not b2b and first_sit:
                add_side("S6 NHL backup tonight, RESTED night, the #1 started the last game", g, side, o, won, g["season"])
            # the side across it
            oside = "away" if side == "home" else "home"
            oo = g["mla"] if side == "home" else g["mlh"]
            add_side(f"S6x NHL facing a backup on a {'b2b' if b2b else 'RESTED'} night", g, oside, oo, not won, g["season"])
        else:
            add_side(f"S6 NHL control: the #1 tonight, {'b2b' if b2b else 'rested'}", g, side, o, won, g["season"])

# ---------------- S7 NBA the star's dud
def nba_val(st, r):
    try:
        fgm, fga = [int(x) for x in str(st.get("fieldGoalsMade-fieldGoalsAttempted", "")).split("-")]
        return (int(st.get("points") or 0), fgm, fga)
    except (ValueError, TypeError):
        return None


bx = lib.boxes("nba", nba_val)
by_tg = {}
for gid, teams in bx.items():
    for t, pl in teams.items():
        by_tg[(bare(gid), bare(t))] = pl
fin = [g for g in lib.finals("nba") if g["stype"] == "2"]
tl = lib.team_log(lib.all_finals("nba"))
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"] and x["stype"] == "2"]
        if len(prev) < 5:
            continue
        pts, gp = Counter(), Counter()
        for x in prev:
            for pid, v in (by_tg.get((bare(x["id"]), bare(team))) or {}).items():
                pts[pid] += v[0]
                gp[pid] += 1
        if not pts:
            continue
        cand = [(pts[p] / gp[p], p) for p in pts if gp[p] >= 3]
        if not cand:
            continue
        ppg, star = max(cand)
        last = by_tg.get((bare(prev[-1]["id"]), bare(team))) or {}
        v = last.get(star)
        if not v or ppg < 18:
            continue
        pts_, fgm, fga = v
        oside = "away" if side == "home" else "home"
        oo = g["mla"] if side == "home" else g["mlh"]
        if fga >= 15 and fgm / fga < 0.35:
            add_side("S7 NBA the star shot under 35% on 15+ last game", g, side, o, won, g["season"])
            add_side("S7x NBA facing a star off a dud", g, oside, oo, not won, g["season"])
            if fgm / fga < 0.30:
                add_side("S7 NBA ... under 30%", g, side, o, won, g["season"])
            if not lib.won_g(prev[-1], team):
                add_side("S7 NBA ... dud AND lost", g, side, o, won, g["season"])
        elif fga >= 15 and fgm / fga >= 0.45:
            add_side("S7 NBA control: the star shot 45%+ on 15+", g, side, o, won, g["season"])
        else:
            add_side("S7 NBA control: anything else", g, side, o, won, g["season"])

C.dump("s4_s7", "11/8 S4-S7 - closing prices + ESPN's open; TRAIN 2018-22 / held 2023-2026", TRAIN, HELD)
