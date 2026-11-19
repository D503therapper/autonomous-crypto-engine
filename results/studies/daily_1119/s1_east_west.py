"""S1 (asked) - THE NFL "EAST COAST TEAM FLYING WEST" EARLY SPOT: WHICH TEAMS DID THE STUDY MEAN?
The live rule (sports_early / sports.east_west) and the 10/1 study (tools/early_round3 #10) both read the RAW clock
offsets: the road team's home offset (the most common 'tzo' of its home games, every season) >= -5 and the venue's
offset on game day <= -7. On a wall clock that moves every November that is: [Eastern + Central teams] at [Pacific +
Arizona] before the clocks change, and [the same teams] at [Pacific + Arizona + DENVER] after it.
This reads the same road dogs on STANDARD time (ET / CT / MT / PT; Arizona on the clock it really keeps) -
nflverse's closes 2006-26 (21 seasons) and the paid odds history's first FAIR number 2020-26 (the price the spot bets)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
import lib
import nflv

G = nflv.games()
TRAIN, HELD = (2006, 2016), tuple(range(2017, 2027))
o = h.Out("s1_east_west", TRAIN, HELD)
o.p(__doc__)
o.p(f"nflverse regular-season games with a closing moneyline 2006-26: {len(G)}; TRAIN 2006-16 / HELD 2017-26 each apart")

# the live rule's home offsets, straight from our own game files (what the engine really holds today)
import sports_data as sd      # noqa: E402
import sports_early as se     # noqa: E402
our = sd.load_games("nfl")
htz = se._home_tz(our)
nm = {}
for g in our.values():
    nm[g["home"]] = g.get("home_name")
o.p("\nTHE LIVE RULE'S 'HOME OFFSET' PER TEAM (the mode of the raw tzo over every home game on file):")
by = {}
for (lg, t), v in htz.items():
    if lg == "nfl":
        by.setdefault(v, []).append(nm.get(t) or t)
for v in sorted(by, reverse=True):
    o.p(f"  {v:+.0f}: {', '.join(sorted(by[v]))}")

# our team ids -> nflverse abbreviations, by the name
AB = {"Bills": "BUF", "Dolphins": "MIA", "Patriots": "NE", "Jets": "NYJ", "Giants": "NYG", "Eagles": "PHI",
      "Commanders": "WAS", "Ravens": "BAL", "Steelers": "PIT", "Browns": "CLE", "Bengals": "CIN", "Falcons": "ATL",
      "Panthers": "CAR", "Buccaneers": "TB", "Jaguars": "JAX", "Colts": "IND", "Lions": "DET", "Bears": "CHI",
      "Packers": "GB", "Vikings": "MIN", "Cowboys": "DAL", "Texans": "HOU", "Titans": "TEN", "Chiefs": "KC",
      "Saints": "NO", "Broncos": "DEN", "Cardinals": "ARI", "Seahawks": "SEA", "49ers": "SF", "Rams": "LA",
      "Chargers": "LAC", "Raiders": "LV"}
MINE = {}
for (lg, t), v in htz.items():
    if lg == "nfl" and nm.get(t) in AB:
        MINE[AB[nm[t]]] = v
for old, new in (("STL", "LA"), ("SD", "LAC"), ("OAK", "LV")):
    MINE[old] = MINE.get(new)


def live_rule(g):
    mine = MINE.get(g["away"])
    return mine is not None and mine >= -5 and nflv.raw(g["home"], g["day"]) <= -7


rows = []
for g in G:
    if g["neutral"] or g["hs"] == g["as"]:
        continue
    tz_t, tz_v = nflv.ZONE[g["away"]], nflv.ZONE[g["home"]]
    west = nflv.clock(g["away"], g["day"]) - nflv.clock(g["home"], g["day"])    # hours the venue's clock is behind
    rows.append({"g": g, "tz_t": tz_t, "tz_v": tz_v, "west": west, "live": live_rule(g),
                 "dst": nflv.dst(g["day"]), "p": nflv.ml_profit(g, "away"), "ats": nflv.ats_profit(g, "away"),
                 "o": g["mla"], "s": g["season"]})

dogs = [r for r in rows if 100 <= r["o"] <= 350]
o.p(f"\nroad sides {len(rows)}; road dogs +100..+350 {len(dogs)}")


def cut(name, test, pool=dogs, key="p"):
    for r in pool:
        if test(r):
            o.add(name, r["s"], r[key], r["o"])


cut("A0 every road dog +100..+350", lambda r: True)
cut("A1 THE LIVE RULE (raw offsets)", lambda r: r["live"])
cut("A1a  live rule, before the clocks change", lambda r: r["live"] and r["dst"])
cut("A1b  live rule, after the clocks change", lambda r: r["live"] and not r["dst"])
# the live rule's pieces on standard time
cut("A2 Eastern team at a Pacific venue (3 zones)", lambda r: r["tz_t"] == -5 and r["tz_v"] == -8)
cut("A3 Eastern team in Arizona", lambda r: r["tz_t"] == -5 and r["g"]["home"] == "ARI")
cut("A3a  Eastern in Arizona, daylight time (3h)", lambda r: r["tz_t"] == -5 and r["g"]["home"] == "ARI" and r["dst"])
cut("A3b  Eastern in Arizona, standard time (2h)", lambda r: r["tz_t"] == -5 and r["g"]["home"] == "ARI" and not r["dst"])
cut("A4 Eastern team at Denver (2 zones)", lambda r: r["tz_t"] == -5 and r["g"]["home"] == "DEN")
cut("A4a  Eastern at Denver, before the change (NOT live)", lambda r: r["tz_t"] == -5 and r["g"]["home"] == "DEN" and r["dst"])
cut("A4b  Eastern at Denver, after the change (live)", lambda r: r["tz_t"] == -5 and r["g"]["home"] == "DEN" and not r["dst"])
cut("A5 CENTRAL team at a Pacific venue (2 zones)", lambda r: r["tz_t"] == -6 and r["tz_v"] == -8)
cut("A6 CENTRAL team in Arizona", lambda r: r["tz_t"] == -6 and r["g"]["home"] == "ARI")
cut("A7 CENTRAL team at Denver (1 zone)", lambda r: r["tz_t"] == -6 and r["g"]["home"] == "DEN")
cut("A7b  Central at Denver, after the change", lambda r: r["tz_t"] == -6 and r["g"]["home"] == "DEN" and not r["dst"])
# candidate definitions on the real clock gap (hours the venue is behind the team's home clock that day)
cut("B1 the clock gap 3 hours west", lambda r: r["west"] == 3)
cut("B2 the clock gap 2 hours west", lambda r: r["west"] == 2)
cut("B3 the clock gap 1 hour west", lambda r: r["west"] == 1)
cut("B4 same clock", lambda r: r["west"] == 0)
cut("B5 the clock gap 1 hour east", lambda r: r["west"] == -1)
cut("B6 the clock gap 2 hours east", lambda r: r["west"] == -2)
cut("B7 the clock gap 3 hours east", lambda r: r["west"] == -3)
cut("C1 STANDARD: Eastern team, venue 2+ hours behind (ET -> MT / PT)", lambda r: r["tz_t"] == -5 and r["tz_v"] <= -7)
cut("C2 STANDARD: 2+ zones west, any team (ET -> MT/PT, CT -> PT)", lambda r: r["tz_t"] - r["tz_v"] >= 2)
cut("C3 STANDARD: Eastern or Central team at a Pacific venue", lambda r: r["tz_t"] >= -6 and r["tz_v"] == -8)
cut("C4 the real clock: 2+ hours west", lambda r: r["west"] >= 2)
cut("E1 KEPT: live and a 3-hour clock gap (Eastern at a Pacific clock)", lambda r: r["live"] and r["west"] == 3)
cut("E2 DROPPED: live, not a 3-hour gap (Central teams, Denver, Arizona on standard)", lambda r: r["live"] and r["west"] != 3)
cut("E3 3-hour gap the live rule misses", lambda r: (not r["live"]) and r["west"] == 3)
cut("C5 live rule minus (Central at Denver / Eastern at Denver)", lambda r: r["live"] and r["g"]["home"] != "DEN")
cut("C6 in the live rule ONLY by the raw clock (Denver after the change)", lambda r: r["live"] and r["g"]["home"] == "DEN")
cut("C7 STANDARD says yes, the live rule no (ET at Denver before the change)", lambda r: (not r["live"]) and r["tz_t"] == -5 and r["tz_v"] <= -7)
for nm_, lo, hi in (("day (before 4 PM ET)", 0, 16), ("late afternoon (4-7 PM ET)", 16, 19), ("night (7 PM ET+)", 19, 30)):
    cut(f"D the clock 2+ hours west, {nm_}", lambda r, lo=lo, hi=hi: r["west"] >= 2 and r["g"]["et"] is not None and lo <= r["g"]["et"] < hi)
o.p("\nROAD DOGS +100..+350 AT THE CLOSE (nflverse 2006-26):")
o.show()
for a in ("A1 THE LIVE RULE (raw offsets)", "A2 Eastern team at a Pacific venue (3 zones)", "C1 STANDARD: Eastern team, venue 2+ hours behind (ET -> MT / PT)",
          "C2 STANDARD: 2+ zones west, any team (ET -> MT/PT, CT -> PT)", "C4 the real clock: 2+ hours west", "A5 CENTRAL team at a Pacific venue (2 zones)",
          "C6 in the live rule ONLY by the raw clock (Denver after the change)"):
    o.placebo(a, "A0 every road dog +100..+350")

CLOSE = {k: list(v) for k, v in o.c.items()}
# against the spread, every road side (not only dogs) - the second market
o.c.clear()
for r in rows:
    if r["ats"] is None:
        continue
    o.add("ATS every road side", r["s"], r["ats"])
    if r["live"]:
        o.add("ATS the live rule", r["s"], r["ats"])
    if r["tz_t"] == -5 and r["tz_v"] == -8:
        o.add("ATS Eastern at Pacific", r["s"], r["ats"])
    if r["tz_t"] == -5 and r["tz_v"] <= -7:
        o.add("ATS Eastern, venue 2+ zones west", r["s"], r["ats"])
    if r["tz_t"] == -6 and r["tz_v"] == -8:
        o.add("ATS Central at Pacific", r["s"], r["ats"])
    if r["west"] >= 2:
        o.add("ATS the real clock 2+ hours west", r["s"], r["ats"])
    if r["west"] >= 2 and 100 <= r["o"] <= 350:
        o.add("ATS the real clock 2+ hours west, dogs", r["s"], r["ats"])
o.p("\nAGAINST THE SPREAD AT THE CLOSE, the road side:")
o.show()

# ---- the paid odds history's first FAIR number (the price the early spot bets), 2020-26 ----
o.c.clear()
o.train, o.held = (2020, 2022), (2023, 2024, 2025, 2026)
X = {x["id"]: x for x in lib.load_football("nfl")}
fin = {g["id"]: g for g in lib.finals("nfl")}
byespn = {g["espn"]: g for g in G}
n_match = 0
for gid, x in X.items():
    g = byespn.get(gid.split(":")[-1])
    if not g or g["neutral"] or g["hs"] == g["as"]:
        continue
    n_match += 1
    ep = lib.early_price(X, gid, "away")
    if not ep or not 100 <= ep[0] <= 350:
        continue
    pr = (ep[1] - 1) if g["as"] > g["hs"] else -1.0
    tz_t, tz_v = nflv.ZONE[g["away"]], nflv.ZONE[g["home"]]
    west = nflv.clock(g["away"], g["day"]) - nflv.clock(g["home"], g["day"])
    live = live_rule(g)
    s = g["season"]
    o.add("F0 every road dog at the first fair number", s, pr, ep[0])
    if live:
        o.add("F1 THE LIVE RULE", s, pr, ep[0])
        o.add("F1a  live, Eastern at Pacific" if (tz_t == -5 and tz_v == -8) else "F1b  live, everything else (Central teams, Arizona, Denver late)", s, pr, ep[0])
    if tz_t == -5 and tz_v == -8:
        o.add("F2 Eastern at Pacific", s, pr, ep[0])
    if tz_t == -5 and tz_v <= -7:
        o.add("F3 STANDARD: Eastern, venue 2+ zones west", s, pr, ep[0])
    if tz_t - tz_v >= 2:
        o.add("F4 STANDARD: 2+ zones west, any team", s, pr, ep[0])
    if tz_t == -6 and tz_v == -8:
        o.add("F5 Central at Pacific", s, pr, ep[0])
    if west >= 2:
        o.add("F6 the real clock 2+ hours west", s, pr, ep[0])
    o.add("F9 KEPT: live and a 3-hour clock gap" if (live and west == 3) else "F9b DROPPED: live, not a 3-hour gap" if live else "F9c not live", s, pr, ep[0])
    if live and g["home"] == "DEN":
        o.add("F7 live only by the raw clock (Denver after the change)", s, pr, ep[0])
    if tz_t >= -6 and tz_v == -7 and not live:
        o.add("F8 ET / CT at a Mountain venue, not live", s, pr, ep[0])
o.p(f"\nTHE PAID ODDS HISTORY'S FIRST FAIR NUMBER (median book; {n_match} games matched; TRAIN 2020-22 / HELD 2023-26):")
o.show()
for a in ("F1 THE LIVE RULE", "F2 Eastern at Pacific", "F3 STANDARD: Eastern, venue 2+ zones west", "F4 STANDARD: 2+ zones west, any team", "F6 the real clock 2+ hours west"):
    o.placebo(a, "F0 every road dog at the first fair number")


def brief(title, names):
    o.p("\n" + title)
    for k in names:
        v = o.c.get(k)
        if not v:
            continue
        r = lib.summ([(s_, p_) for s_, p_, _ in v], o.train, o.held)
        by = {}
        for s_, p_, _ in v:
            by.setdefault(s_, []).append(p_)
        up = sum(1 for x in by.values() if sum(x) > 0)
        f = lambda x: f"{x['roi']*100:+6.1f}% on {x['n']:4d} (z {x['z']:+.2f})" if x else "-"
        o.p(f"  {k:78s} ALL {f(r['all'])} | TRAIN {f(r['train'])} | HELD {f(r['held_all'])} | seasons up {up}/{len(by)}")


brief("THE FIRST FAIR NUMBER, in one line each:", sorted(o.c))
o.c.clear()
o.c.update(CLOSE)
o.train, o.held = TRAIN, HELD
brief("THE CLOSE 2006-26, in one line each:", sorted(o.c))
o.save()
