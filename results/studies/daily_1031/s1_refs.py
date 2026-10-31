"""Studies 1-4 (10/31): THE REFEREE CREW - does a crew's own history (its earlier games' home team vs the closing
price, its earlier games vs the closing total) say anything the closing price doesn't? NFL (the Referee = the crew
chief), NBA (3 referees), NHL (2 referees, linesmen out), college hoops (3 referees; prep - college hoops crews are
NOT published before tip, so a finding there could never be used live).

No look-ahead: a crew's lean on a game uses only the games each official worked BEFORE that game's day.
lean = sum(home won - no-vig home %) / (n + K) per official, averaged over the game's officials (shrunk to 0).
over = sum(points over the total: +1 / -1) / (n + K), the same way.
Step 1 - is the lean even PERSISTENT (each official's first half of games vs his second half)?
Step 2 - at the close: dogs +100..+350 with the crew lean on their side (home dog + home-leaning crew; road dog +
road-leaning crew) vs against them; ATS the same; the over-lean crew vs dogs (more points = less variance?).
Train = the old seasons, each newer season held out apart.
usage: python s1_refs.py nfl|nba|nhl|ncaab"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

LG = sys.argv[1]
ROLES = {"nfl": ("Referee",), "nba": ("Referee", "Crew Chief", "Umpire"), "nhl": ("Referee",),
         "ncaab": ("Referee", "Umpire")}[LG]
K = {"nfl": 40, "nba": 60, "nhl": 60, "ncaab": 40}[LG]
TRAIN = {"nfl": (2018, 2022), "nba": (2018, 2022), "nhl": (2018, 2022), "ncaab": (2018, 2021)}[LG]
HELD = {"nfl": (2023, 2024, 2025, 2026), "nba": (2023, 2024, 2025), "nhl": (2023, 2024, 2025, 2026),
        "ncaab": (2022, 2023, 2024, 2025)}[LG]
MINN = {"nfl": 15, "nba": 30, "nhl": 30, "ncaab": 20}[LG]

offs = json.load(open(os.path.join(lib.sd.DATA, "officials.json")))["games"]
games = lib.finals(LG)
hist = {}          # official -> [home residuals], [over signs]
rows = []
day_buf = []       # games of the current day, added to history only after the day (no same-day look-ahead)
cur = None
for g in games:
    d = g["start"][:10]
    if d != cur:
        for name, r, o in day_buf:
            h = hist.setdefault(name, ([], []))
            h[0].append(r)
            if o is not None:
                h[1].append(o)
        day_buf, cur = [], d
    of = [n for role, n in offs.get(g["id"], []) if any(x in role for x in ROLES)]
    if not of:
        continue
    hd, ad = lib.dec(g["mlh"]), lib.dec(g["mla"])
    p = lib.nv(g["mlh"], g["mla"])
    res = (1.0 if g["hs"] > g["as"] else 0.0) - p
    ov = None
    if g["total"]:
        t = g["hs"] + g["as"]
        ov = 0 if t == g["total"] else (1 if t > g["total"] else -1)
    leans, overs, ns = [], [], []
    for n in of:
        h = hist.get(n, ([], []))
        ns.append(len(h[0]))
        leans.append(sum(h[0]) / (len(h[0]) + K))
        overs.append(sum(h[1]) / (len(h[1]) + K))
    rows.append({"g": g, "lean": sum(leans) / len(leans), "over": sum(overs) / len(overs), "n": min(ns),
                 "p": p, "hd": hd, "ad": ad})
    for n in of:
        day_buf.append((n, res, ov))

out = {"league": LG, "games_with_officials": len(rows)}
# step 1: persistence - each official's first half vs second half of his games (home residual mean)
import statistics as st  # noqa: E402
pairs = []
for n, (r, o) in hist.items():
    if len(r) >= 2 * MINN:
        h = len(r) // 2
        pairs.append((sum(r[:h]) / h, sum(r[h:]) / (len(r) - h), sum(o[:len(o) // 2]) / max(1, len(o) // 2),
                      sum(o[len(o) // 2:]) / max(1, len(o) - len(o) // 2)))


def corr(a, b):
    if len(a) < 3:
        return None
    ma, mb = st.mean(a), st.mean(b)
    sa, sb = st.pstdev(a), st.pstdev(b)
    return round(sum((x - ma) * (y - mb) for x, y in zip(a, b)) / len(a) / (sa * sb), 3) if sa and sb else None


out["officials_2x"] = len(pairs)
out["persist_home_corr"] = corr([x[0] for x in pairs], [x[1] for x in pairs])
out["persist_over_corr"] = corr([x[2] for x in pairs], [x[3] for x in pairs])

# step 2: the bets. Lean cut = the top / bottom third of leans among rows whose officials have MINN+ games.
ok = [r for r in rows if r["n"] >= MINN]
ls = sorted(r["lean"] for r in ok)
os_ = sorted(r["over"] for r in ok)
lo, hi = ls[len(ls) // 3], ls[2 * len(ls) // 3]
olo, ohi = os_[len(os_) // 3], os_[2 * len(os_) // 3]
out["cuts"] = {"lean_lo": round(lo, 4), "lean_hi": round(hi, 4), "over_lo": round(olo, 4), "over_hi": round(ohi, 4),
               "rows_ok": len(ok)}
cells = {}


def add(name, s, pr):
    cells.setdefault(name, []).append((s, pr))


for r in ok:
    g = r["g"]
    s = g["season"]
    for side, team, opp, o, won, home in lib.sides(g):
        d = lib.dec(o)
        pr = lib.profit(won, d)
        crew_for = r["lean"] >= hi if home else r["lean"] <= lo
        crew_against = r["lean"] <= lo if home else r["lean"] >= hi
        if lib.dog_band(o):
            add("dog, all (base)", s, pr)
            add(f"{'home' if home else 'road'} dog, base", s, pr)
            if crew_for:
                add("dog, crew leans TO its side (top third)", s, pr)
                add(f"{'home' if home else 'road'} dog, crew leans to its side", s, pr)
            if crew_against:
                add("dog, crew leans AGAINST its side (fade)", s, pr)
            if r["over"] >= ohi:
                add("dog, over-leaning crew (top third)", s, pr)
            if r["over"] <= olo:
                add("dog, under-leaning crew (bottom third)", s, pr)
        if -150 <= o <= -101:
            add("fav -101..-150, base", s, pr)
            if crew_for:
                add("fav -101..-150, crew leans to its side", s, pr)
            if crew_against:
                add("fav -101..-150, crew leans against it (fade)", s, pr)
        a = lib.ats(g, side)
        if a is not None and home:
            add("ATS home, base", s, a)
            if r["lean"] >= hi:
                add("ATS home, home-leaning crew", s, a)
            if r["lean"] <= lo:
                add("ATS home, road-leaning crew (fade)", s, a)
    if g["total"]:
        t = g["hs"] + g["as"]
        if t != g["total"]:
            for nm, cond in (("over, over-leaning crew", r["over"] >= ohi), ("under, under-leaning crew", r["over"] <= olo)):
                if cond:
                    won = (t > g["total"]) if nm.startswith("over") else (t < g["total"])
                    add(nm + " (total, -110)", s, lib.profit(won, lib.dec(-110)))

res = {k: lib.summ(v, TRAIN, HELD) for k, v in cells.items()}
out["cells"] = res
lines = [f"REFEREE CREWS - {LG}: {len(rows)} games with officials, {len(ok)} with {MINN}+ earlier games each",
         f"persistence (officials with {2*MINN}+ games, first half vs second half): home lean corr "
         f"{out['persist_home_corr']}  over lean corr {out['persist_over_corr']}  ({len(pairs)} officials)",
         f"cuts {out['cuts']}"]
for k, v in res.items():
    lines.append(lib.fmt(k, v))
txt = "\n".join(lines)
print(txt)
open(os.path.join(lib.OUT, f"s1_refs_{LG}_out.txt"), "w").write(txt + "\n")
json.dump(out, open(os.path.join(lib.OUT, f"s1_refs_{LG}_out.json"), "w"), indent=1)
