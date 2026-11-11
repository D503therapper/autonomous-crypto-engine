"""S5. SITUATIONAL ATS - the spots books are said to shade (NFL, nflverse's closing spreads 1999-2026 at -110; the
angles are the handicapping books' own, none fit here - TRAIN 1999-2014 / BLIND 2015-26 shows whether each is still
there), then THE BIG PUBLIC SIDE on the spread (Action Network's final pre-tip splits, 2024-26, every league that has
them, at AN's own line and juice).
   python s5_situational.py"""
import json
from collections import defaultdict
import lib2 as L
import sports_data as sd

o = L.Out("s5")
B, N = L.B, L.N
G = [g for g in N.games() if g["reg"]]
P110 = L.dec(-110) - 1

# each team's schedule in order
log = defaultdict(list)
for g in G:
    log[(g["season"], g["home"])].append(g)
    log[(g["season"], g["away"])].append(g)


def tm(g, t):
    return g["m"] if g["home"] == t else -g["m"]


def ats(g, side):
    r = g["m"] + g["hl"]
    if side == "away":
        r = -r
    return 0.0 if r == 0 else (P110 if r > 0 else -1.0)


def record(prev, t):
    w = sum(1 for x in prev if tm(x, t) > 0)
    return w, len(prev)


T = defaultdict(list)
for g in G:
    for side, t, opp, line in (("home", g["home"], g["away"], g["hl"]), ("away", g["away"], g["home"], -g["hl"])):
        lg = log[(g["season"], t)]
        i = lg.index(g)
        prev, nxt = lg[:i], (lg[i + 1] if i + 1 < len(lg) else None)
        olg = log[(g["season"], opp)]
        oi = olg.index(g)
        oprev = olg[:oi]
        p = ats(g, side)
        s = g["season"]
        home = side == "home" and not g["neutral"]
        rest = g["hrest"] if side == "home" else g["arest"]
        orest = g["arest"] if side == "home" else g["hrest"]
        dog, fav = line > 0, line < 0

        def add(k):
            T[k].append((s, p))
        add("base: every side")
        if dog:
            add("every dog")
            if home:
                add("home dog")
            if g["div"]:
                add("division dog")
                if home:
                    add("division HOME dog")
                if line >= 7:
                    add("division dog getting 7+")
            if line >= 10:
                add("double-digit dog (+10 or more)")
            if 7.5 <= line <= 9.5:
                add("dog getting +7.5..+9.5 (the 11/1 WATCH, on 27 seasons)")
            if 3.5 <= line <= 6.5:
                add("dog getting +3.5..+6.5")
        if fav and 7.5 <= -line <= 9.5:
            add("favorite laying -7.5..-9.5")
        if prev:
            last = prev[-1]
            lm = tm(last, t)
            if dog and home and lm < 0:
                add("home dog off a loss")
            if dog and home and len(prev) >= 2 and lm < 0 and tm(prev[-2], t) < 0:
                add("home dog off 2+ losses")
            if lm <= -17:
                add("any side off a 17+ loss")
                if dog:
                    add("dog off a 17+ loss")
                if fav:
                    add("favorite off a 17+ loss")
            if lm >= 17:
                add("any side off a 17+ win")
                if fav:
                    add("favorite off a 17+ win (letdown?)")
            if lm <= -21 and oprev and tm(oprev[-1], opp) >= 21:
                add("off a 21+ loss vs a team off a 21+ win (the overreaction)")
            if last["ot"]:
                add("side off an overtime game")
            # failed to cover badly last week (needs last week's line)
            lc = (last["m"] + last["hl"]) if last["home"] == t else -(last["m"] + last["hl"])
            if lc <= -14:
                add("side that missed its number by 14+ last week")
            if lc >= 14:
                add("side that beat its number by 14+ last week")
        if rest is not None and orest is not None:
            if rest >= 13 and orest < 13:
                add("off a bye vs a team that isn't")
                if dog:
                    add("dog off a bye")
                if fav:
                    add("favorite off a bye")
            if rest <= 4 and not home:
                add("road team on a short week (4 days)")
            if rest - orest >= 3 and rest < 13:
                add("3+ more days of rest (no bye)")
        # lookahead / sandwich: a favorite in a non-division game with a division game next
        if fav and nxt is not None and not g["div"] and nxt["div"] and -line >= 3:
            add("favorite -3+ outside the division, a division game next (lookahead)")
            if prev and prev[-1]["div"]:
                add("... and a division game last week too (the sandwich)")
        if fav and nxt is not None and -line >= 6:
            nop = nxt["away"] if nxt["home"] == t else nxt["home"]
            w, n_ = record([x for x in log[(g["season"], nop)] if x["date"] < g["date"]], nop)
            if n_ >= 4 and w / n_ >= 0.7:
                add("favorite -6+ with a .700+ team next (lookahead)")
        if len(prev) >= 4:
            w, n_ = record(prev, t)
            ow, on = record(oprev, opp)
            if dog and on >= 4 and w / n_ > ow / on:
                add("dog with the better record")
            if dog and home and w / n_ <= 0.25 and g["week"] >= 10:
                add("home dog, .250 or worse, week 10 on (the spoiler)")
        if g["week"] >= 15 and dog and g["div"]:
            add("division dog, weeks 15-18")
        if g["week"] == 1 and dog:
            add("week 1 dog")
        if g["wd"] == "Monday" and dog and home:
            add("Monday night home dog")

o("== NFL situational ATS at the close, -110, regular season 1999-2026 (train 1999-2014 / BLIND 2015-26) ==")
o(f"   {'cell':66s} {'all':>34s} | train              | BLIND (seasons up)")
for k in sorted(T, key=lambda k: -L.roi([p for _, p in T[k]])):
    r = T[k]
    tr = [(s, p) for s, p in r if s <= 2014]
    bl = [(s, p) for s, p in r if s >= 2015]
    upt, upb = L.by_season(tr), L.by_season(bl)
    o(f"   {k[:66]:66s} {L.st([p for _, p in r])} | {L.roi([p for _, p in tr]):+5.1f}% ({upt[0]}/{upt[1]}) n{len(tr):5d} | {L.st([p for _, p in bl])} ({upb[0]}/{upb[1]})")
o(f"   cells: {len(T)} - about {len(T) * 0.05:.0f} would clear |z| 2 by luck")

# ---------------- the public on the spread ----------------
o("\n== THE BIG PUBLIC SIDE ON THE SPREAD (Action Network's final pre-tip ticket / money split, 2024-26; AN's line and juice) ==")
pub = json.load(open(sd.DATA + "/public.json"))["games"]
for lg in ("nfl", "ncaaf", "nba", "ncaab"):
    fin = {g["id"]: g for g in B.all_finals(lg)}
    T = defaultdict(list)
    for gid, v in pub.items():
        g = fin.get(gid)
        if not g or any(v.get(k_) is None for k_ in ("sp_home_t", "sp_home_line", "sp_away_t", "sp_away_line")):
            continue
        m = g["hs"] - g["as"]
        for side, line, tk, mo, od in (("home", v["sp_home_line"], v["sp_home_t"], v.get("sp_home_m"), v.get("sp_home_odds")),
                                       ("away", v["sp_away_line"], v["sp_away_t"], v.get("sp_away_m"), v.get("sp_away_odds"))):
            if od is None or not (-140 <= od <= 125):
                continue
            r = (m if side == "home" else -m) + line
            p = 0.0 if r == 0 else (L.dec(od) - 1 if r > 0 else -1.0)
            s = g["season"]
            T["every side"].append((s, p))
            for cut in (65, 75):
                if tk >= cut:
                    T[f"the public side ({cut}%+ of tickets)"].append((s, p))
                if tk <= 100 - cut:
                    T[f"FADE the public ({cut}%+ of tickets on the other side)"].append((s, p))
                    if line > 0:
                        T[f"   ... the faded-into side is the dog ({cut}%+)"].append((s, p))
                    if side == "home":
                        T[f"   ... and it's the home team ({cut}%+)"].append((s, p))
            if mo is not None:
                if mo - tk >= 15:
                    T["money 15+ over tickets (the sharp side)"].append((s, p))
                if mo - tk >= 25:
                    T["money 25+ over tickets"].append((s, p))
                if tk <= 35 and mo >= 50:
                    T["35% or less of tickets, half the money or more"].append((s, p))
    o(f"-- {lg}")
    for k in sorted(T):
        r = T[k]
        up = L.by_season(r)
        o(f"   {k[:60]:60s} {L.st([p for _, p in r])} ({up[0]}/{up[1]} up: {up[2]})")
o("\ncells read: ~45 NFL cells + 4 leagues x 12 public cells = ~95")
o.save()
