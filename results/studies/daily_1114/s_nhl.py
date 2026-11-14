"""11/14 daily studies - NHL (S1-S5). Prices: ESPN's close at its own juice (regular season); the paid NHL history
(2021-23, one ~15:00Z look a day) for the morning / day-before looks.
S1 NHL REGULARS OUT TONIGHT (box TOI 2021-26: the team's top-9 skaters by ice time over its last 10, 6+ of 10 played,
   not in tonight's box) - the side vs the price, by how many more it's missing than the opponent; the hockey 'hurt'
   rule (2+ out = no units) has never been studied.
S2 NHL REGULARS BACK (a top-9 ice-time man of the season, 10+ games, who missed the team's last 3+ games and dresses).
S3 NHL TOTALS WITH REGULARS OUT (both teams' missing top-9 men added) - the hockey twin of the NBA 'main guys sit' over.
S4 NHL SURPRISE GOALIE (players/nhl.csv 2016-26): the starter is NOT the team's #1 of its last 10 (6+ of 10) and it is
   NOT the 2nd night of a back-to-back - the side at the close; the morning -> close move (2021-23) says if the market
   caught it.
S5 NHL LINE SHAPE (paid 2021-23): the day-before look -> the game-day morning look -> the close; a side that moved one
   way and came back (or kept going), bet at the CLOSE (every price before the bet)."""
import gzip
import json
import os
import pickle
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402

C = lib.CACHE
fin = lib.finals("nhl")
allf = lib.all_finals("nhl")
tl = defaultdict(list)                       # team -> [(start, gid)] every final (priced or not)
for g in allf:
    for t in (g["home"], g["away"]):
        tl[t].append((g["start"], g["id"]))
SK = pickle.load(open(os.path.join(C, "nhl_skaters.pkl"), "rb"))
GL = pickle.load(open(os.path.join(C, "nhl_goalies.pkl"), "rb"))
MO = lib.nhl_morning()


def prior(team, start, season, n=None):
    lst = [x for x in tl[team] if x[0] < start and lib.season(x[0]) == season]
    return lst[-n:] if n else lst


def gap_h(team, start):
    lst = [x for x in tl[team] if x[0] < start]
    if not lst:
        return None
    return (lib._t(start) - lib._t(lst[-1][0])).total_seconds() / 3600


def regulars(team, start, season):
    """(top-9 by TOI over the last 10 with 6+ played, top point man of the season (10+ games)) or None."""
    last = [gid for _, gid in prior(team, start, season, 10) if gid in SK and team in SK[gid]]
    if len(last) < 8:
        return None
    tot, cnt = defaultdict(float), defaultdict(int)
    for gid in last:
        for pid, t, grp, pts in SK[gid][team]:
            tot[pid] += t
            cnt[pid] += 1
    regs = [p for p in sorted(tot, key=lambda p: -tot[p]) if cnt[p] >= 6][:9]
    seas = [gid for _, gid in prior(team, start, season) if gid in SK and team in SK[gid]]
    ptot, pc = defaultdict(float), defaultdict(int)
    for gid in seas:
        for pid, t, grp, pts in SK[gid][team]:
            ptot[pid] += pts
            pc[pid] += 1
    top = max(ptot, key=lambda p: ptot[p]) if len(seas) >= 10 and ptot else None
    return regs, top, seas


def back_count(team, start, season, seas, tonight):
    """season top-9 ice-time men (10+ games) who missed each of the team's last 3 games and dress tonight."""
    if len(seas) < 13:
        return 0
    tot, cnt = defaultdict(float), defaultdict(int)
    for gid in seas:
        for pid, t, grp, pts in SK[gid][team]:
            tot[pid] += t
            cnt[pid] += 1
    avg = {p: tot[p] / cnt[p] for p in tot if cnt[p] >= 10}
    top9 = sorted(avg, key=lambda p: -avg[p])[:9]
    last3 = seas[-3:]
    missed = [p for p in top9 if all(p not in {x[0] for x in SK[g][team]} for g in last3)]
    return sum(1 for p in missed if p in tonight)


MV = defaultdict(list)


def s1_s3():
    o = h.Out("s1_s3_nhl_regulars", (2021, 2022), [2023, 2024, 2025, 2026])
    o.p("S1-S3 NHL REGULARS OUT / BACK (box TOI 2021-26; train 2021-22 / held 2023 / 2024 / 2025 / now 2026)")
    for g in fin:
        if g["season"] < 2021 or g["stype"] != "2" or g["id"] not in SK:
            continue
        b = SK[g["id"]]
        if g["home"] not in b or g["away"] not in b or len(b[g["home"]]) < 16 or len(b[g["away"]]) < 16:
            continue
        info = {}
        for t in (g["home"], g["away"]):
            r = regulars(t, g["start"], g["season"])
            if r is None:
                break
            regs, top, seas = r
            tonight = {x[0] for x in b[t]}
            info[t] = {"out": sum(1 for p in regs if p not in tonight),
                       "out3": sum(1 for p in regs[:3] if p not in tonight),
                       "top_out": top is not None and top not in tonight,
                       "back": back_count(t, g["start"], g["season"], seas, tonight)}
        if len(info) < 2:
            continue
        for side, t, opp, odds, won, home in lib.sides(g):
            me, op = info[t], info[opp]
            pr = lib.profit(won, lib.dec(odds))
            bd = h.band(odds)
            o.add("BASE all sides", g["season"], pr, odds)
            if bd:
                o.add(f"BASE {bd}", g["season"], pr, odds)
            d = me["out"] - op["out"]
            db = "<=-2" if d <= -2 else "+3+" if d >= 3 else f"{d:+d}"
            o.add(f"S1 diff {db}", g["season"], pr, odds)
            if bd and d >= 1:
                o.add(f"S1 {bd} missing 1+ MORE regulars than the opponent", g["season"], pr, odds)
            ms = lib.morning_side(MO, g["id"], side)
            if ms and bd:
                pcl = lib.nv(g["mlh"], g["mla"]) if side == "home" else 1 - lib.nv(g["mlh"], g["mla"])
                k = "1+ more out" if d >= 1 else "1+ fewer out" if d <= -1 else "even"
                MV[k].append(pcl - ms[2])
                o.add(f"S1m {bd} {k} at the paid MORNING price", g["season"], lib.profit(won, ms[1]), odds)
                o.add(f"S1m {bd} {k} at the close (same games)", g["season"], pr, odds)
            if bd:
                o.add(f"S1 {bd} diff {db}", g["season"], pr, odds)
                if me["out"] >= 2:
                    o.add(f"S1 {bd} own 2+ out (the hurt rule)", g["season"], pr, odds)
                if me["out"] >= 3:
                    o.add(f"S1 {bd} own 3+ out", g["season"], pr, odds)
                if me["out3"] >= 1:
                    o.add(f"S1 {bd} a top-3 ice-time man out", g["season"], pr, odds)
                if me["top_out"]:
                    o.add(f"S1 {bd} the top point man out", g["season"], pr, odds)
                if op["top_out"] and not me["top_out"]:
                    o.add(f"S1 {bd} vs the top point man out", g["season"], pr, odds)
                if me["back"] >= 1:
                    o.add(f"S2 {bd} 1+ regular back", g["season"], pr, odds)
                if me["back"] >= 2:
                    o.add(f"S2 {bd} 2+ regulars back", g["season"], pr, odds)
                if op["back"] >= 1 and me["back"] == 0:
                    o.add(f"S2 {bd} vs 1+ regular back", g["season"], pr, odds)
            if me["back"] >= 1:
                o.add("S2 any 1+ back", g["season"], pr, odds)
        tot = info[g["home"]]["out"] + info[g["away"]]["out"]
        tb = "4+" if tot >= 4 else str(tot)
        for over in (True, False):
            pr = lib.tot_profit(g, over)
            o.add(f"S3 {'over' if over else 'under'} BASE", g["season"], pr)
            o.add(f"S3 {'over' if over else 'under'} both out {tb}", g["season"], pr)
            if tot >= 3:
                o.add(f"S3 {'over' if over else 'under'} both out 3+", g["season"], pr)
            if info[g["home"]]["out3"] + info[g["away"]]["out3"] >= 2:
                o.add(f"S3 {'over' if over else 'under'} 2+ top-3 men out", g["season"], pr)
    o.show()
    for k, v in MV.items():
        o.p(f"  morning -> close move of the side's no-vig %, {k}: mean {statistics.mean(v)*100:+.2f} pts on {len(v)}")
    for c, pool, fade in (("S1 dog missing 1+ MORE regulars than the opponent", "BASE dog", True),
                          ("S1 fav missing 1+ MORE regulars than the opponent", "BASE fav", True),
                          ("S1 dog diff +1", "BASE dog", True),
                          ("S1 dog own 2+ out (the hurt rule)", "BASE dog", True),
                          ("S1 fav own 2+ out (the hurt rule)", "BASE fav", True),
                          ("S1 dog diff +3+", "BASE dog", True), ("S1 fav diff +3+", "BASE fav", True),
                          ("S1 dog diff <=-2", "BASE dog", False), ("S1 fav diff <=-2", "BASE fav", False),
                          ("S2 dog 1+ regular back", "BASE dog", False), ("S2 fav 1+ regular back", "BASE fav", False),
                          ("S3 over both out 3+", "S3 over BASE", False), ("S3 under both out 3+", "S3 under BASE", False)):
        o.placebo(c, pool, fade=fade)
    o.save()


def s4():
    o = h.Out("s4_nhl_surprise_goalie", (2016, 2021), [2022, 2023, 2024, 2025, 2026])
    o.p("S4 NHL SURPRISE GOALIE (players/nhl.csv 2016-26; train 2016-21 / held 2022-25 / now 2026)")
    moves = defaultdict(list)
    for g in fin:
        if g["stype"] != "2" or g["id"] not in GL:
            continue
        gg = GL[g["id"]]
        st = {}
        for t in (g["home"], g["away"]):
            last = [gid for _, gid in prior(t, g["start"], g["season"], 10) if gid in GL and t in GL[gid]]
            if len(last) < 8 or t not in gg:
                break
            cnt = defaultdict(int)
            for gid in last:
                cnt[GL[gid][t]] += 1
            no1 = max(cnt, key=cnt.get)
            b2b = (gap_h(t, g["start"]) or 99) < 30
            st[t] = {"surprise": gg[t] != no1 and cnt[no1] >= 6 and not b2b,
                     "planned": gg[t] != no1 and cnt[no1] >= 6 and b2b,
                     "unknown": cnt.get(gg[t], 0) == 0}
        if len(st) < 2:
            continue
        for side, t, opp, odds, won, home in lib.sides(g):
            pr = lib.profit(won, lib.dec(odds))
            bd = h.band(odds)
            me, op = st[t], st[opp]
            ms = lib.morning_side(MO, g["id"], side)
            pclose = lib.nv(g["mlh"], g["mla"]) if side == "home" else 1 - lib.nv(g["mlh"], g["mla"])
            if bd:
                o.add(f"BASE {bd}", g["season"], pr, odds)
                if me["surprise"]:
                    o.add(f"S4 {bd} on a SURPRISE backup (rested night)", g["season"], pr, odds)
                    if me["unknown"]:
                        o.add(f"S4 {bd} surprise, a goalie with no start in the last 10", g["season"], pr, odds)
                if me["planned"]:
                    o.add(f"S4 {bd} backup on the b2b 2nd night (planned)", g["season"], pr, odds)
                if op["surprise"] and not me["surprise"]:
                    o.add(f"S4 {bd} vs a SURPRISE backup", g["season"], pr, odds)
            if ms:
                k = "surprise" if me["surprise"] else "planned" if me["planned"] else "no1"
                moves[k].append(pclose - ms[2])
                if me["surprise"] and bd:
                    o.add(f"S4m {bd} surprise side at the MORNING price (look-ahead, info only)", g["season"],
                          lib.profit(won, ms[1]), odds)
    o.show()
    for k, v in moves.items():
        o.p(f"  morning -> close move of the side's no-vig %, {k}: mean {statistics.mean(v)*100:+.2f} pts on {len(v)}"
            f" (median {statistics.median(v)*100:+.2f})")
    for c, pool in (("S4 dog on a SURPRISE backup (rested night)", "BASE dog"),
                    ("S4 fav on a SURPRISE backup (rested night)", "BASE fav"),
                    ("S4 dog vs a SURPRISE backup", "BASE dog"), ("S4 fav vs a SURPRISE backup", "BASE fav")):
        o.placebo(c, pool, fade=False)
        o.placebo(c, pool, fade=True)
    o.save()


def s5():
    o = h.Out("s5_nhl_line_shape", (2020, 2021), [2022])
    o.p("S5 NHL LINE SHAPE (moves: 1+ pt overnight, 0.75+ on game day; paid 2021-23: the day-before look -> the game-day morning -> ESPN's close; bet at the close;"
        " train the 2020-21 + 2021-22 seasons / held 2022-23)")
    games = sd.load_games("nhl")
    by_day = defaultdict(list)
    for g in games.values():
        if g.get("status") == "final":
            by_day[g["start"][:10]].append(g)
    looks = defaultdict(dict)                       # gid -> {"pre": p_home, "mor": p_home}
    with gzip.open(os.path.join(sd.DATA, "odds_history", "icehockey_nhl.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            if "snap" not in r:
                continue
            g, flip = lib._find(r, by_day)
            if not g:
                continue
            hs = [lib.dec(v[0]) for v in r["b"].values() if v and v[0] is not None]
            as_ = [lib.dec(v[1]) for v in r["b"].values() if v and v[1] is not None]
            if len(hs) < 3:
                continue
            hd, ad = statistics.median(hs), statistics.median(as_)
            if flip:
                hd, ad = ad, hd
            p = (1 / hd) / (1 / hd + 1 / ad)
            kind = "mor" if r["snap"][:10] == g["start"][:10] or r["snap"][:10] == r["t"][:10] else "pre"
            if kind == "pre" and (lib._t(g["start"]) - lib._t(r["snap"])).total_seconds() > 40 * 3600:
                continue
            looks[g["id"]][kind] = p
    n = 0
    for g in fin:
        lk = looks.get(g["id"])
        if not lk or "pre" not in lk or "mor" not in lk or g["stype"] != "2":
            continue
        n += 1
        pc = lib.nv(g["mlh"], g["mla"])
        for side, t, opp, odds, won, home in lib.sides(g):
            sgn = 1 if side == "home" else -1
            m1 = sgn * (lk["mor"] - lk["pre"]) * 100
            m2 = sgn * (pc - lk["mor"]) * 100
            pr = lib.profit(won, lib.dec(odds))
            bd = h.band(odds)
            if not bd:
                continue
            o.add(f"BASE {bd}", g["season"], pr, odds)
            if m1 >= 1 and m2 <= -0.75:
                o.add(f"S5 {bd} moved TO it, then gave back", g["season"], pr, odds)
            if m1 >= 1 and m2 >= 0.75:
                o.add(f"S5 {bd} moved TO it, kept going", g["season"], pr, odds)
            if m1 <= -1 and m2 >= 0.75:
                o.add(f"S5 {bd} moved AWAY, then came back", g["season"], pr, odds)
            if m1 <= -1 and m2 <= -0.75:
                o.add(f"S5 {bd} moved AWAY, kept going", g["season"], pr, odds)
            if abs(m1) < 0.5 and m2 >= 1.5:
                o.add(f"S5 {bd} flat overnight, game-day move TO it 1.5+", g["season"], pr, odds)
            if abs(m1) < 0.5 and m2 <= -1.5:
                o.add(f"S5 {bd} flat overnight, game-day move AWAY 1.5+", g["season"], pr, odds)
    o.p(f"games with both looks: {n}")
    o.show()
    for c in list(o.c):
        if c.startswith("S5") and len(o.c[c]) >= 40:
            pool = "BASE dog" if " dog " in c else "BASE fav"
            o.placebo(c, pool, fade=sum(p for _, p, _ in o.c[c]) < 0)
    o.save()


if __name__ == "__main__":
    which = sys.argv[1:] or ["s1", "s4", "s5"]
    if "s1" in which:
        s1_s3()
    if "s4" in which:
        s4()
    if "s5" in which:
        s5()
