"""S5-S9 - SPREADS: new cuts only (dead already and not re-run: a power rating against the close in the NFL / college
football / the NBA, the engine's margin vs the line, key numbers, timing, the public, the hoops stack's own pieces,
the derivative 1H gap). The closing spread at its own juice, train to 2021 / blind 2022 on.

S5 THE CHANGE LAG: football - the game a new QB starts (the top passer differs from last game's), his SECOND start,
   the old starter's first game back; the NBA - the first game without the minutes leader, games 2-5 without him.
S6 SOFT MARKETS + S7 THE MARGIN READ: a walk-forward points rating a league (offence / defence, updated after every
   final, half of last season carried in, the step picked on the train seasons) turned into a margin; its gap to the
   closing spread by size, in every league, then inside the softest markets - low-major college hoops league games
   and college football games between two non-power teams.
S8 FIRST HALVES: the 1H spread (game files; NBA 2018-23 + 2026, college hoops 2018-26) for the rusty home side, a
   team on a back-to-back, the full-game stack's ideas; the real pre-tip log's count.
S9 THE BACK DOOR: dogs getting 8-15 in the NBA / college hoops by scoring pace and the favorite's rest; favorites
   laying 10+ in every league; from the quarter scores, how often the back door opens and shuts."""
import gzip, importlib.util, json, os
from collections import defaultdict

import lib as L
import box as B

A_ = lambda rows, side: [(g["season"], L.ats(g, side(g) if callable(side) else side)) for g in rows]   # noqa: E731


def two(rows, side_fn, name, tt=L.TRAIN_TO):
    """side_fn(g) -> 'H' / 'A' (the side the cut is about). Prints that side and the side across."""
    a = L.cell(name, [(g["season"], L.ats(g, side_fn(g))) for g in rows], train_to=tt)
    L.cell("   the side across", [(g["season"], L.ats(g, L.other(side_fn(g)))) for g in rows], train_to=tt)
    return a


# ---------------------------------------------------------------- S5
print("=" * 30, "S5. THE CHANGE LAG")
for lg in ("nfl", "ncaaf"):
    rows = L.table(lg)
    qb = defaultdict(dict)                          # gid -> team -> top passer (pid)
    att = defaultdict(lambda: defaultdict(dict))
    for r in B.R.load(lg):
        if r["group"] != "passing":
            continue
        try:
            ca = str(json.loads(r["stats"]).get("completions/passingAttempts") or "0/0").split("/")
            n = float(ca[1]) if len(ca) > 1 else 0.0
        except (ValueError, IndexError):
            n = 0.0
        att[r["gid"]][r["team"]][r["pid"]] = n
    for gid, tm in att.items():
        for t, d in tm.items():
            if d:
                qb[gid][t] = max(d.items(), key=lambda kv: kv[1])[0]
    hist = defaultdict(list)                        # (season, team) -> starters so far
    out = []
    for g in rows:
        for side, t in (("H", g["home"]), ("A", g["away"])):
            h = hist[(g["season"], t)]
            cur = qb.get(g["id"], {}).get(t)
            f = g[side]
            f["qb_new"] = f["qb_2nd"] = f["qb_back"] = None
            if cur and len(h) >= 2:
                f["qb_new"] = cur != h[-1]                                            # a different starter tonight
                f["qb_first"] = f["qb_new"] and cur not in h                          # ... who has not started this season
                f["qb_2nd"] = (cur == h[-1]) and h[-1] != h[-2] and h[-1] not in h[:-1]   # his second start
                f["qb_back"] = f["qb_new"] and cur in h[:-1]                          # the old starter back
            if cur:
                h.append(cur)
    G = [g for g in rows if L.reg(g) and g["sp"] is not None]
    print(f"   ({lg}: 'FIRST start' is read off TONIGHT's box score - who threw the most. A starter hurt or benched in the\n"
          f"    first half lands in that cell, so it is a LOOK-AHEAD and no bet: it is printed to show the leak's size. The\n"
          f"    'second start' and 'first game back' cells use last week's box score only - those are the clean ones.)")
    for key, nm in (("qb_first", "LEAK - a QB's FIRST start of the season (not the opener)"), ("qb_2nd", "his SECOND start"),
                    ("qb_back", "the old starter's first game back")):
        sel = [(g, s) for g in G for s in "HA" if g[s].get(key) and not g[L.other(s)].get(key)]
        L.cell(f"{lg} {nm}: that team ATS", [(g["season"], L.ats(g, s)) for g, s in sel])
        L.cell(f"{lg}    the side across", [(g["season"], L.ats(g, L.other(s))) for g, s in sel])
        L.cell(f"{lg}    that team as a dog", [(g["season"], L.ats(g, s)) for g, s in sel if L.spread(g, s) > 0])
        L.cell(f"{lg}    that team as a favorite", [(g["season"], L.ats(g, s)) for g, s in sel if L.spread(g, s) < 0])
    # the lag proper: the first start went badly / well - what does the number do to the second?
    sel = [(g, s) for g in G for s in "HA" if g[s].get("qb_2nd") and g[s].get("last") and g[s]["last"].get("cm") is not None]
    L.cell(f"{lg} second start after the first one MISSED its number by 7+", [(g["season"], L.ats(g, s)) for g, s in sel if g[s]["last"]["cm"] <= -7])
    L.cell(f"{lg} second start after the first one BEAT its number by 7+", [(g["season"], L.ats(g, s)) for g, s in sel if g[s]["last"]["cm"] >= 7])
    L.cell(f"{lg}    the side across", [(g["season"], L.ats(g, L.other(s))) for g, s in sel if g[s]["last"]["cm"] >= 7])
nba = B.nba_stars(L.table("nba"))
run = defaultdict(int)
for g in nba:
    for side, t in (("H", g["home"]), ("A", g["away"])):
        k = (g["season"], t)
        so = g[side].get("star_out")
        if so is None:
            g[side]["out_run"] = None
            continue
        run[k] = run[k] + 1 if so else 0
        g[side]["out_run"] = run[k]
N = [g for g in nba if L.reg(g) and g["sp"] is not None]
for lo, hi, nm in ((1, 1, "the FIRST game without the minutes leader"), (2, 3, "games 2-3 without him"), (4, 8, "games 4-8 without him"),
                   (9, 99, "game 9+ without him")):
    sel = [(g, s) for g in N for s in "HA" if g[s].get("out_run") and lo <= g[s]["out_run"] <= hi and not g[L.other(s)].get("star_out")]
    L.cell(f"NBA {nm}: that team ATS", [(g["season"], L.ats(g, s)) for g, s in sel])
    L.cell("NBA    the side across", [(g["season"], L.ats(g, L.other(s))) for g, s in sel])
sel = [(g, s) for g in N for s in "HA" if g[s].get("out_run") == 1 and not g[s].get("b2b") and not g[L.other(s)].get("star_out")]
L.cell("NBA first game without him, NOT a back-to-back (a real injury, not a rest night)", [(g["season"], L.ats(g, s)) for g, s in sel])
L.cell("NBA    the side across", [(g["season"], L.ats(g, L.other(s))) for g, s in sel])

# ---------------------------------------------------------------- S6 + S7
print("\n" + "=" * 30, "S6 + S7. THE MARGIN READ vs THE CLOSING SPREAD")


def rated(rows, k, hfa0, tune_to=None):
    off, de = defaultdict(float), defaultdict(float)
    hfa, cur = hfa0, None
    out, se, n = {}, 0.0, 0
    for g in rows:
        if g["season"] != cur:
            cur = g["season"]
            for t in list(off):
                off[t] *= 0.5
                de[t] *= 0.5
        h, a = g["home"], g["away"]
        hf = 0.0 if g["neutral"] else hfa
        mh = (off[h] + de[a]) - (off[a] + de[h]) + hf            # the read: home margin
        if g["H"]["n"] >= 4 and g["A"]["n"] >= 4:
            out[g["id"]] = mh
            if tune_to and g["season"] <= tune_to:
                se += (g["hs"] - g["as"] - mh) ** 2
                n += 1
        mu = (g["hs"] + g["as"]) / 2
        eh = (g["hs"] - mu) - ((off[h] + de[a]) - (off[a] + de[h]) + hf) / 2
        off[h] += k * eh
        de[a] += k * eh
        off[a] -= k * eh
        de[h] -= k * eh
        if not g["neutral"]:
            hfa += (g["hs"] - g["as"] - mh) / 3000
    return out, (se / n if n else 0.0)


cbspec = importlib.util.spec_from_file_location("cbb", os.path.join(L.ROOT, "results", "studies", "cbb10_1112", "lib.py"))
C = importlib.util.module_from_spec(cbspec)
cbspec.loader.exec_module(C)
cb = {g["id"]: g for g in C.build()}
POWER_F = {"Alabama", "Ohio State", "Ohio St", "Clemson", "Oklahoma St", "Oklahoma State", "Oregon", "Notre Dame", "Texas", "Michigan"}


def football_tiers(rows):
    """{season: {team: 'power' / 'other'}} - leagues from the Oct-Nov schedule (3+ common opponents), a league with
    an anchor school = power (membership is public before the season)."""
    names, by = {}, defaultdict(lambda: defaultdict(set))
    for g in rows:
        names[g["home"]], names[g["away"]] = g["hn"], g["an"]
        if L.reg(g) and g["start"][5:7] in ("10", "11"):
            by[g["season"]][g["home"]].add(g["away"])
            by[g["season"]][g["away"]].add(g["home"])
    out = {}
    for s, adj in by.items():
        par = {t: t for t in adj}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for a in adj:
            for b in adj[a]:
                if a < b and len(adj[a] & adj[b]) >= 3:
                    par[find(a)] = find(b)
        comp = defaultdict(set)
        for t in adj:
            comp[find(t)].add(t)
        m = {}
        for k_, mem in comp.items():
            tier = "power" if {names.get(t) for t in mem} & POWER_F else "other"
            for t in mem:
                m[t] = (k_, tier, len(mem))
        out[s] = m
    return out


for lg, hfa0, steps in (("nba", 2.5, (0.04, 0.07, 0.10)), ("nfl", 2.0, (0.04, 0.07, 0.10)), ("ncaaf", 2.5, (0.10, 0.16, 0.22)),
                        ("ncaab", 3.0, (0.06, 0.10, 0.14))):
    rows = L.table(lg)
    best = min(((rated(rows, k, hfa0, tune_to=2021)[1], k) for k in steps))
    R, _ = rated(rows, best[1], hfa0)
    G = [g for g in rows if L.reg(g) and g["sp"] is not None and g["id"] in R]
    e1 = (sum((g["hs"] - g["as"] - R[g["id"]]) ** 2 for g in G) / len(G)) ** 0.5
    e2 = (sum((g["hs"] - g["as"] + g["sp"]) ** 2 for g in G) / len(G)) ** 0.5
    print(f"\n{lg}: step {best[1]} (picked on train); the read misses the final margin by {e1:.2f} (RMSE), the closing spread by {e2:.2f}; {len(G)} games")
    gap = lambda g: R[g["id"]] + g["sp"]            # noqa: E731  (+ = the read likes the HOME side by that many points)
    for lo, hi in ((2, 4), (4, 6), (6, 9), (9, 99)):
        L.cell(f"{lg} the read {lo}..{hi} points off the spread -> its side",
               [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in G if lo <= abs(gap(g)) < hi])
    L.cell(f"{lg} 4+ off -> its side when that side is the DOG",
           [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in G if abs(gap(g)) >= 4 and L.spread(g, "H" if gap(g) > 0 else "A") > 0])
    L.cell(f"{lg} 4+ off -> its side when that side is the FAVORITE",
           [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in G if abs(gap(g)) >= 4 and L.spread(g, "H" if gap(g) > 0 else "A") < 0])
    if lg == "ncaab":
        for tier in ("low", "mid", "power"):
            S = [g for g in G if g["id"] in cb and cb[g["id"]]["conf"] and cb[g["id"]]["H"].get("tier") == tier]
            L.cell(f"ncaab {tier}-major LEAGUE games: every home side", [(g["season"], L.ats(g, "H")) for g in S])
            for lo, hi in ((2, 4), (4, 6), (6, 99)):
                L.cell(f"ncaab {tier}-major league games, the read {lo}..{hi} off -> its side",
                       [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in S if lo <= abs(gap(g)) < hi])
        S = [g for g in G if g["id"] in cb and cb[g["id"]]["conf"] and cb[g["id"]]["H"].get("tier") == "low"]
        L.cell("ncaab low-major league, 4+ off, Jan only", [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in S if abs(gap(g)) >= 4 and g["start"][5:7] == "01"])
        L.cell("ncaab low-major league, 4+ off, Feb-Mar", [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in S if abs(gap(g)) >= 4 and g["start"][5:7] in ("02", "03")])
        L.cell("ncaab low-major league, 4+ off, the read's side at HOME", [(g["season"], L.ats(g, "H")) for g in S if gap(g) >= 4])
        L.cell("ncaab low-major league, 4+ off, the read's side on the ROAD", [(g["season"], L.ats(g, "A")) for g in S if gap(g) <= -4])
    if lg == "ncaaf":
        tiers = football_tiers(rows)

        def tr_(g, t):
            return tiers.get(g["season"], {}).get(t, (None, None, 0))
        S = [g for g in G if tr_(g, g["home"])[1] == "other" and tr_(g, g["away"])[1] == "other" and tr_(g, g["home"])[2] >= 6
             and tr_(g, g["away"])[2] >= 6]
        S2 = [g for g in S if tr_(g, g["home"])[0] == tr_(g, g["away"])[0]]
        print(f"   {len(S)} games between two non-power teams, {len(S2)} of them league games")
        L.cell("ncaaf non-power league games: every home side", [(g["season"], L.ats(g, "H")) for g in S2])
        L.cell("ncaaf non-power league games: every dog", [(g["season"], L.ats(g, "H" if g["sp"] > 0 else "A")) for g in S2 if g["sp"] != 0])
        for lo, hi in ((3, 6), (6, 10), (10, 99)):
            L.cell(f"ncaaf non-power league games, the read {lo}..{hi} off -> its side",
                   [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in S2 if lo <= abs(gap(g)) < hi])
            L.cell(f"ncaaf POWER league games, the read {lo}..{hi} off -> its side",
                   [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A")) for g in G
                    if tr_(g, g["home"])[1] == "power" and tr_(g, g["home"])[0] == tr_(g, g["away"])[0] and lo <= abs(gap(g)) < hi])
        L.cell("ncaaf non-power league games on a weeknight (Tue-Thu)", [(g["season"], L.ats(g, "H" if gap(g) > 0 else "A"))
                                                                         for g in S2 if g["day"].weekday() in (1, 2, 3) and abs(gap(g)) >= 3])

# ---------------------------------------------------------------- S8
print("\n" + "=" * 30, "S8. FIRST HALVES (the game files' 1H spread, graded on the 1H score at its own juice)")


def h1(g, side):
    if g["h1sp"] is None or not g["lsh"] or not g["lsa"]:
        return None
    n = 2 if g["lg"] in ("nba", "nfl", "ncaaf") else 1
    if len(g["lsh"]) < n or len(g["lsa"]) < n:
        return None
    r = sum(g["lsh"][:n]) - sum(g["lsa"][:n]) + g["h1sp"]
    if side == "A":
        r = -r
    o = g["h1ho"] if side == "H" else g["h1ao"]
    if o is None or abs(o) < 100 or abs(o) > 160:
        o = -112
    return 0.0 if r == 0 else (L.dec(o) - 1 if r > 0 else -1.0)


for lg in ("ncaab", "nba"):
    rows = [g for g in L.table(lg) if L.reg(g) and g["h1sp"] is not None]
    L.cell(f"{lg} every 1H home side", [(g["season"], h1(g, "H")) for g in rows])
    L.cell(f"{lg} every 1H away side", [(g["season"], h1(g, "A")) for g in rows])
    rusty = [g for g in rows if not g["neutral"] and g["H"].get("rest", 0) >= 7 and g["A"].get("rest", 9) <= 4 and g["H"]["n"] >= 4 and g["A"]["n"] >= 4]
    L.cell(f"{lg} the rusty home side (7+ days off vs a team in rhythm): its 1H", [(g["season"], h1(g, "H")) for g in rusty])
    L.cell(f"{lg}    the visitor's 1H", [(g["season"], h1(g, "A")) for g in rusty])
    L.cell(f"{lg}    the visitor's full game (for scale)", [(g["season"], L.ats(g, "A")) for g in rusty])
    for side, nm in (("H", "home"), ("A", "road")):
        b = [g for g in rows if g[side].get("b2b") and not g[L.other(side)].get("b2b")]
        L.cell(f"{lg} a {nm} team on a back-to-back: its 1H", [(g["season"], h1(g, side)) for g in b])
        L.cell(f"{lg}    the rested side's 1H", [(g["season"], h1(g, L.other(side))) for g in b])
    trip = [g for g in rows if not g["neutral"] and g["A"].get("road_run", 0) >= 3]
    L.cell(f"{lg} a visitor on its 4th+ straight road game: its 1H", [(g["season"], h1(g, "A")) for g in trip])
    L.cell(f"{lg}    the home side's 1H", [(g["season"], h1(g, "H")) for g in trip])
    early = [g for g in rows if g["tzo"] is not None and (int(g["start"][11:13]) + g["tzo"]) % 24 < 13 and not g["neutral"]]
    L.cell(f"{lg} a tip before 1 PM local: the home 1H", [(g["season"], h1(g, "H")) for g in early])
    L.cell(f"{lg}    the visitor's 1H", [(g["season"], h1(g, "A")) for g in early])
    west = [g for g in rows if not g["neutral"] and g["tzo"] is not None and g["A"].get("last") and g["H"]["n"] >= 3]
    big = [g for g in rows if g["sp"] is not None and abs(g["sp"]) >= 12]
    L.cell(f"{lg} a favorite laying 12+: its 1H", [(g["season"], h1(g, "H" if g["sp"] < 0 else "A")) for g in big])
    L.cell(f"{lg}    the big dog's 1H", [(g["season"], h1(g, "A" if g["sp"] < 0 else "H")) for g in big])
p = os.path.join(L.ROOT, "data", "sports", "h1_lines.jsonl.gz")
if os.path.exists(p):
    n = sum(1 for _ in gzip.open(p, "rt"))
    print(f"   our own pre-tip 1H log holds {n} rows (the 11/11 re-test bar: 1,000 college hoops games) - not re-read before then")

# ---------------------------------------------------------------- S9
print("\n" + "=" * 30, "S9. THE BACK DOOR + BIG FAVORITES")
for lg in ("nba", "ncaab"):
    rows = [g for g in L.table(lg) if L.reg(g) and g["sp"] is not None]
    D = [(g, "H" if g["sp"] > 0 else "A") for g in rows if 8 <= abs(g["sp"]) <= 15]
    L.cell(f"{lg} every dog getting 8-15", [(g["season"], L.ats(g, s)) for g, s in D])
    pace = lambda g: g["H"].get("pf", 0) + g["H"].get("pa", 0) + g["A"].get("pf", 0) + g["A"].get("pa", 0)   # noqa: E731
    ok = [(g, s) for g, s in D if g["H"]["n"] >= 8 and g["A"]["n"] >= 8]
    qs = sorted(pace(g) for g, s in ok)
    hi_p, lo_p = qs[int(len(qs) * 0.75)], qs[int(len(qs) * 0.25)]
    L.cell(f"{lg}   the fastest-scoring quarter of those games", [(g["season"], L.ats(g, s)) for g, s in ok if pace(g) >= hi_p])
    L.cell(f"{lg}   the slowest-scoring quarter", [(g["season"], L.ats(g, s)) for g, s in ok if pace(g) <= lo_p])
    L.cell(f"{lg}   the favorite on a back-to-back (starters sit the 4th)", [(g["season"], L.ats(g, s)) for g, s in D if g[L.other(s)].get("b2b")])
    L.cell(f"{lg}   the favorite plays again tomorrow-ish (3rd game in 4)", [(g["season"], L.ats(g, s)) for g, s in D if g[L.other(s)].get("g4", 0) >= 2])
    L.cell(f"{lg}   the dog at home", [(g["season"], L.ats(g, s)) for g, s in D if s == "H" and not g["neutral"]])
    L.cell(f"{lg}   the dog on the road", [(g["season"], L.ats(g, s)) for g, s in D if s == "A" and not g["neutral"]])
    L.cell(f"{lg}   the dog off a 15+ loss", [(g["season"], L.ats(g, s)) for g, s in D if g[s].get("last") and g[s]["last"]["m"] <= -15])
    L.cell(f"{lg}   the favorite off a 15+ win", [(g["season"], L.ats(g, s)) for g, s in D if g[L.other(s)].get("last") and g[L.other(s)]["last"]["m"] >= 15])
    if lg == "nba":
        L.cell("nba   the dog's minutes leader out", [(g["season"], L.ats(g, s)) for g, s in D if g[s].get("star_out")])
        L.cell("nba   the favorite's minutes leader out", [(g["season"], L.ats(g, s)) for g, s in D if g[L.other(s)].get("star_out")])
    # the back door from the period scores
    nper = 4 if lg == "nba" else 2
    cov3 = cov = inn = outn = tot_n = 0
    for g, s in D:
        if not g["lsh"] or not g["lsa"] or len(g["lsh"]) < nper:
            continue
        k = nper - 1 if lg == "nba" else 1
        m3 = sum(g["lsh"][:k]) - sum(g["lsa"][:k])
        m = g["hs"] - g["as"]
        frac = k / nper
        c3 = (m3 + g["sp"] * frac) > 0 if s == "H" else (-(m3 + g["sp"] * frac)) > 0
        cf = (m + g["sp"]) > 0 if s == "H" else (-(m + g["sp"])) > 0
        tot_n += 1
        cov3 += c3
        cov += cf
        inn += (not c3) and cf
        outn += c3 and not cf
    if tot_n:
        lab = "three quarters" if lg == "nba" else "the half"
        print(f"   {lg} dogs getting 8-15: covering their share after {lab} {100 * cov3 / tot_n:.1f}%, at the final {100 * cov / tot_n:.1f}%; "
              f"in the back door {100 * inn / tot_n:.1f}%, lost it late {100 * outn / tot_n:.1f}% ({tot_n} games)")
for lg in ("nba", "ncaab", "nfl", "ncaaf"):
    rows = [g for g in L.table(lg) if L.reg(g) and g["sp"] is not None]
    for lo, hi in ((10, 13.5), (14, 19.5), (20, 60)):
        F = [(g, "H" if g["sp"] < 0 else "A") for g in rows if lo <= abs(g["sp"]) <= hi]
        L.cell(f"{lg} a favorite laying {lo}-{hi}", [(g["season"], L.ats(g, s)) for g, s in F])
        L.cell(f"{lg}    at home", [(g["season"], L.ats(g, s)) for g, s in F if s == "H" and not g["neutral"]])
        L.cell(f"{lg}    on the road", [(g["season"], L.ats(g, s)) for g, s in F if s == "A" and not g["neutral"]])
L.done()
