"""S4. FIRST-HALF SPREADS (NFL / college football / NBA / college hoops).
The game files' 1st-half spread (Action Network's number, filled after the game - its stamp unknown, the caveat the
11/3 study named) graded on the 1st-half score at the 1st-half line's OWN juice. Three reads, every input from before
the game:
 (a) THE DERIVATIVE GAP - a fair 1H number from the closing full-game spread (the ratio fit on the train seasons) vs
     the posted 1H line: bet the side the 1H line leaves cheap (football is new; hoops was the 11/3 lead).
 (b) FAST / SLOW STARTERS - a team's running 1H cover margin this season (1H margin + its 1H line, 4+ earlier games):
     does the 1H market chase it or miss it? And the raw version: 1H margin minus its share of the full-game margin.
 (c) THE PRE-TIP LOG (sports_h1log, 11/3 on - real timestamps): the 11/3 college hoops lead re-tested on the numbers
     a bettor could really get before tip.
   python s4_first_half.py"""
import gzip, json, statistics
from collections import defaultdict
import lib2 as L
import sports_data as sd
import sports_model as sm

o = L.Out("s4")
B = L.B
SPLIT = {"nfl": 2021, "ncaaf": 2021, "nba": 2021, "ncaab": 2021}     # train = seasons up to this one, held out after


def half(ls, lg):
    try:
        v = [float(x) for x in str(ls).split(",") if x != ""]
    except ValueError:
        return None
    if lg == "ncaab":
        return v[0] if len(v) >= 2 else None
    return v[0] + v[1] if len(v) >= 4 else None


def load(lg):
    out = []
    for g in sm.finals(sd.load_games(lg), lg):
        hs, as_ = B.num(g.get("home_score")), B.num(g.get("away_score"))
        h1, sp = B.num(g.get("h1_spread_home")), B.num(g.get("spread_home"))
        a, b = half(g.get("ls_home"), lg), half(g.get("ls_away"), lg)
        if None in (hs, as_, a, b):
            continue
        ho, ao = B.num(g.get("h1_spread_home_odds")), B.num(g.get("h1_spread_away_odds"))
        ok = h1 is not None and sp is not None and ho and ao and -150 <= ho <= 125 and -150 <= ao <= 125 \
            and (h1 * sp >= 0 or abs(sp) <= 2.5) and abs(h1) <= abs(sp) + 1.5
        out.append({"id": g["id"], "start": g["start"], "season": B.season(g["start"]), "home": g["home"], "away": g["away"],
                    "m": hs - as_, "m1": a - b, "sp": sp, "h1": h1 if ok else None, "ho": ho, "ao": ao,
                    "mlo": B.num(g.get("ml_home_open")), "mlc": B.num(g.get("ml_home")), "neutral": str(g.get("neutral")) == "1",
                    "stype": str(g.get("stype") or "2")})
    out.sort(key=lambda x: x["start"])
    return out


def bet1(g, side):
    r = g["m1"] + g["h1"]
    if side == "away":
        r = -r
    pr = g["ho"] if side == "home" else g["ao"]
    return 0.0 if r == 0 else (L.dec(pr) - 1 if r > 0 else -1.0)


def line(name, rows, split):
    tr = [p for s, p in rows if s <= split]
    he = [p for s, p in rows if s > split]
    up = L.by_season([(s, p) for s, p in rows if s > split])
    upt = L.by_season([(s, p) for s, p in rows if s <= split])
    return f"   {name[:58]:58s} all {L.st([p for _, p in rows])} | train {L.roi(tr):+6.1f}% ({upt[0]}/{upt[1]}) | HELD {L.st(he)} ({up[0]}/{up[1]} up: {up[2]})"


for lg in ("nfl", "ncaaf", "nba", "ncaab"):
    G = load(lg)
    H = [g for g in G if g["h1"] is not None]
    sp = SPLIT[lg]
    tr = [g for g in H if g["season"] <= sp and abs(g["sp"]) >= 1]
    ratio = sum(g["h1"] * g["sp"] for g in tr) / sum(g["sp"] ** 2 for g in tr)
    # what the 1H MARGIN really is against the full spread (the true ratio, train)
    true_ratio = sum(-g["m1"] * g["sp"] for g in tr) / sum(g["sp"] ** 2 for g in tr)
    o(f"\n== {lg.upper()}: {len(H)} games with a clean 1H line ({len(G)} with half scores); the 1H line = {ratio:.3f} x the full spread (train), the 1H MARGIN = {true_ratio:.3f} x it ==")
    T = defaultdict(list)
    for g in H:
        T["base: every 1H side at its juice"].append((g["season"], bet1(g, "home")))
        T["base: every 1H side at its juice"].append((g["season"], bet1(g, "away")))
        gap = ratio * g["sp"] - g["h1"]           # + = the 1H line is higher than fair for the home side... home gets more points -> home cheap
        # home line fair = ratio * sp ; posted h1 ; if h1 > fair the home side has extra points
        ex = g["h1"] - ratio * g["sp"]
        for cut in (0.5, 0.75, 1.0, 1.5):
            if abs(ex) >= cut:
                side = "home" if ex > 0 else "away"
                T[f"(a) the 1H line leaves the side {cut}+ cheap vs the full close"].append((g["season"], bet1(g, side)))
                if cut == 0.75:
                    fav = (g["h1"] < 0) == (side == "home") and g["h1"] != 0
                    T["(a)   0.75+ cheap: 1H favorite side" if fav else "(a)   0.75+ cheap: 1H dog side"].append((g["season"], bet1(g, side)))
        # by size of the full spread: do big favorites cover 1H?
        a = abs(g["sp"])
        favside = "home" if g["sp"] < 0 else "away"
        if a >= 1:
            band = ("fav 1-3.5", "fav 4-7.5", "fav 8-13.5", "fav 14-20.5", "fav 21+")[(a >= 4) + (a >= 8) + (a >= 14) + (a >= 21)]
            T[f"(d) the full-game {band}: its 1H side"].append((g["season"], bet1(g, favside)))
        if g["h1"] in (-3.0, 3.0, -0.5, 0.5):
            T[f"(e) 1H line {abs(g['h1']):g}: the 1H dog"].append((g["season"], bet1(g, "home" if g["h1"] > 0 else "away")))
    # (b) starters
    cov = defaultdict(list)       # (season, team) -> [1H cover margins]
    raw = defaultdict(list)       # (season, team) -> [1H margin - ratio_true * full margin]
    for g in G:
        s = g["season"]
        kh, ka = (s, g["home"]), (s, g["away"])
        if g["h1"] is not None and g["stype"] == "2":
            ch, ca = cov[kh], cov[ka]
            rh, ra = raw[kh], raw[ka]
            if len(ch) >= 4 and len(ca) >= 4:
                d = statistics.mean(ch) - statistics.mean(ca)
                for cut in ((1.5, 3.0) if lg in ("nfl", "ncaaf") else (2.0, 4.0)):
                    if abs(d) >= cut:
                        side = "home" if d > 0 else "away"
                        T[f"(b) WITH the better 1H-cover team this season, gap {cut}+"].append((s, bet1(g, side)))
            if len(rh) >= 4 and len(ra) >= 4:
                d = statistics.mean(rh) - statistics.mean(ra)
                for cut in ((2.0, 4.0) if lg in ("nfl", "ncaaf") else (2.5, 5.0)):
                    if abs(d) >= cut:
                        side = "home" if d > 0 else "away"
                        T[f"(b2) WITH the faster STARTER (1H margin over its share of the full), gap {cut}+"].append((s, bet1(g, side)))
        if g["h1"] is not None:
            c = g["m1"] + g["h1"]
            cov[kh].append(c)
            cov[ka].append(-c)
        x = g["m1"] - true_ratio * g["m"]
        raw[kh].append(x)
        raw[ka].append(-x)
    for k in sorted(T):
        if len(T[k]) >= 60:
            o(line(k, T[k], sp))

# ---------------- (c) the pre-tip log ----------------
o("\n== (c) THE PRE-TIP 1H LOG (sports_h1log - the last logged row 10+ minutes before tip; graded on the 1H score) ==")
rows = [json.loads(x) for x in gzip.open(sd.DATA + "/h1_lines.jsonl.gz", "rt")]
last = {}
for r in rows:
    if not r.get("g") or not r.get("h1") or r["h1"].get("sp") is None or not r.get("fg") or r["fg"].get("sp") is None:
        continue
    if r["t"] >= r["s"] or (B._t(r["s"]) - B._t(r["t"])).total_seconds() < 600:
        continue
    if r["g"] not in last or r["t"] > last[r["g"]]["t"]:
        last[r["g"]] = r
for lg, ratio in (("ncaab", 0.549), ("nba", 0.55)):
    fin = {g["id"]: g for g in load(lg)}
    T = defaultdict(list)
    n = 0
    for gid, r in last.items():
        g = fin.get(gid)
        if not g or r["lg"] != lg:
            continue
        h1, fg = r["h1"]["sp"], r["fg"]["sp"]
        spo = r["h1"].get("spo") or [None, None]
        if not spo[0] or not spo[1] or abs(h1) > abs(fg) + 1.5:
            continue
        n += 1
        ex = h1 - ratio * fg
        gg = dict(g, h1=h1, ho=spo[0], ao=spo[1])
        T["every 1H side"].append((0, bet1(gg, "home")))
        T["every 1H side"].append((0, bet1(gg, "away")))
        for cut in (0.5, 0.75, 1.0):
            if abs(ex) >= cut:
                T[f"the 1H line leaves the side {cut}+ cheap vs the full number at the same hour"].append((0, bet1(gg, "home" if ex > 0 else "away")))
        if g["h1"] is not None and abs(g["h1"] - h1) >= 0.5:
            T["the game file's 1H line differs from the last pre-tip one by a half point+ (share of games)"].append((0, 0.0))
    o(f"   {lg}: {n} games with a pre-tip 1H line and a final")
    for k in sorted(T):
        o(f"      {k:86s} {L.st([p for _, p in T[k]])}")
o("\ncells read: 4 leagues x ~22 rows + 2 x 5 log rows = ~100")
o.save()
