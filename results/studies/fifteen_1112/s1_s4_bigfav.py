"""S1-S4 - FAVORITES -151..-199: IS THERE A PROFITABLE POCKET? (the owner, 11/12: "We might have to increase the limit
to -199 instead of -150. And those we might have to add more units on to be profitable.")

S1 SITUATIONAL (NHL / NBA at the close, 2018-26, train to 2021 / blind 2022 on): the favorite rested against a team on
   a back-to-back, the opponent's BACKUP goalie in net (the starter on file = who really started; 'backup' = he started
   under 40% of his team's games so far this season, 10+ team games), the opponent's minutes leader OUT (NBA box scores:
   the man with the most minutes a game over the team's games so far, 10+ games, no minutes tonight).
S2 BOTH READS AGREE BIG (the board's replay rows 2023-26, FUNNEL=...): the own read AND the weighed read both 5+ points
   over the price at -151..-199, then with an independent voice on top (the opponent on a back-to-back / its backup
   goalie in net, from the game files).
S3 THE FIRST NUMBER (ESPN's opening moneyline, 2023-26 only): -151..-199 favorites at the open vs the close.
S4 SIZING: printed for any pocket that is positive in BOTH halves with z 2+; none = no units fix it."""
import glob, json, os, sys
from collections import defaultdict
from datetime import date

import lib as L

sys.path.insert(0, L.ROOT)
LO, HI = -199, -151


def band(o, lo=LO, hi=HI):
    return o is not None and lo <= o <= hi


def favs(lg):
    out = []
    for g in L.table(lg):
        f = L.fav(g)
        if L.reg(g) and f and band(L.odds(g, f)):
            out.append((g, f))
    return out


# ---------------------------------------------------------------- S1
print("=" * 30, "S1. SITUATIONAL BIG FAVORITES -151..-199 AT THE CLOSE")
# the backup goalie, walk-forward: each team's starts by goalie this season before tonight
nhl = L.table("nhl")
starts = defaultdict(lambda: defaultdict(int))
tg = defaultdict(int)
for g in nhl:
    for side, t, gl in (("H", g["home"], g["gh"]), ("A", g["away"], g["ga"])):
        k = (g["season"], t)
        g[side]["bk"] = None
        if gl and tg[k] >= 10:
            g[side]["bk"] = starts[k][gl] / tg[k] < 0.40
        if gl:
            starts[k][gl] += 1
            tg[k] += 1
F = [(g, f) for g, f in favs("nhl")]
base = L.cell("NHL every favorite -151..-199", [(g["season"], L.ml(g, f)) for g, f in F])
pool_nhl = [p for _, p in base["bets"]]
L.cell("NHL home favorite", [(g["season"], L.ml(g, f)) for g, f in F if f == "H"])
L.cell("NHL road favorite", [(g["season"], L.ml(g, f)) for g, f in F if f == "A"])
L.cell("NHL the dog on a back-to-back", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b")])
x = L.cell("NHL favorite rested (2+ days), dog on a back-to-back",
           [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and g[f].get("rest", 0) >= 2])
L.cell("NHL ... and the favorite at home",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and g[f].get("rest", 0) >= 2 and f == "H"])
L.cell("NHL both on a back-to-back", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and g[f].get("b2b")])
L.cell("NHL the FAVORITE on a back-to-back, dog rested",
       [(g["season"], L.ml(g, f)) for g, f in F if g[f].get("b2b") and not g[L.other(f)].get("b2b")])
bk = L.cell("NHL the dog starts its BACKUP goalie", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["bk"]])
L.cell("NHL the dog starts its No. 1", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["bk"] is False])
L.cell("NHL dog's backup + the favorite's No. 1",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["bk"] and g[f]["bk"] is False])
L.cell("NHL dog's backup AND dog on a back-to-back",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["bk"] and g[L.other(f)].get("b2b")])
L.cell("NHL dog's backup, NOT a back-to-back (a real backup night)",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["bk"] and not g[L.other(f)].get("b2b")])
L.cell("NHL the FAVORITE starts its backup", [(g["season"], L.ml(g, f)) for g, f in F if g[f]["bk"]])
L.cell("NHL dog 3rd game in 4 nights", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("g4", 0) >= 2])
L.cell("NHL favorite off 3+ days", [(g["season"], L.ml(g, f)) for g, f in F if g[f].get("rest", 0) >= 3])
for lo, hi in ((-165, -151), (-180, -166), (-199, -181)):
    L.cell(f"NHL dog on a back-to-back, {lo}..{hi}",
           [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and band(L.odds(g, f), lo, hi)])
print(" the dose across the price (is -151..-199 part of one real thing, or a lucky band?)")
ALLF = [(g, L.fav(g)) for g in nhl if L.reg(g) and L.fav(g)]
for lo, hi in ((-130, -101), (-150, -131), (-199, -151), (-250, -200), (-400, -251)):
    L.cell(f"NHL favorite {lo}..{hi}, dog on a back-to-back, favorite not",
           [(g["season"], L.ml(g, f)) for g, f in ALLF if band(L.odds(g, f), lo, hi) and g[L.other(f)].get("b2b")
            and not g[f].get("b2b")])
    L.cell(f"NHL favorite {lo}..{hi}, every one",
           [(g["season"], L.ml(g, f)) for g, f in ALLF if band(L.odds(g, f), lo, hi)])
xb = L.cell("NHL favorite -151..-199, dog on a back-to-back, favorite not",
            [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and not g[f].get("b2b")])
L.cell("  ... the dog's No. 1 goalie starts anyway",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and not g[f].get("b2b") and g[L.other(f)]["bk"] is False])
L.cell("  ... the dog's backup starts",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and not g[f].get("b2b") and g[L.other(f)]["bk"]])
L.cell("  ... the dog played on the ROAD last night too",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and not g[f].get("b2b")
        and g[L.other(f)]["last"]["ven"] == "A"])
L.cell("  ... 2022 on, the open price (2023 on) instead of the close",
       [(g["season"], L.ml(g, f, True)) for g, f in F if g[L.other(f)].get("b2b") and not g[f].get("b2b")], train_to=2024)
L.cell("  ... the same games at the close, 2023 on",
       [(g["season"], L.ml(g, f)) for g, f in F if g["season"] >= 2023 and g[L.other(f)].get("b2b") and not g[f].get("b2b")], train_to=2024)
ps = [p for _, p in x["bets"]]
if ps:
    print(f"   placebo: random {len(ps)} NHL favorites in the band as good as 'rested vs a back-to-back': "
          f"{L.placebo(pool_nhl, len(ps), sum(ps) / len(ps))} of 2000")

# NBA: the minutes leader out, from the box scores
os.chdir(L.ROOT)                                # (sports_data reads data/ from the repo root)
import sports_roster as R  # noqa: E402

mins = defaultdict(dict)                         # gid -> team -> {pid: minutes}
for row in R.load("nba"):
    try:
        m = float(json.loads(row["stats"]).get("minutes") or 0)
    except (ValueError, TypeError):
        m = 0.0
    mins[row["gid"]].setdefault(row["team"], {})[row["pid"]] = m
nba = L.table("nba")
tot_m = defaultdict(lambda: defaultdict(float))
gp = defaultdict(int)
for g in nba:
    bx = mins.get(g["id"])
    for side, t in (("H", g["home"]), ("A", g["away"])):
        k = (g["season"], t)
        g[side]["star_out"] = None
        g[side]["two_out"] = None
        if bx and t in bx and gp[k] >= 10:
            top = sorted(tot_m[k].items(), key=lambda kv: -kv[1])[:3]
            out = [pid for pid, _ in top if bx[t].get(pid, 0) <= 0]
            g[side]["star_out"] = top[0][0] in out
            g[side]["two_out"] = len(out) >= 2
        if bx and t in bx:
            for pid, m in bx[t].items():
                tot_m[k][pid] += m
            gp[k] += 1
F = favs("nba")
base = L.cell("NBA every favorite -151..-199", [(g["season"], L.ml(g, f)) for g, f in F])
pool_nba = [p for _, p in base["bets"]]
L.cell("NBA home favorite", [(g["season"], L.ml(g, f)) for g, f in F if f == "H"])
L.cell("NBA road favorite", [(g["season"], L.ml(g, f)) for g, f in F if f == "A"])
L.cell("NBA the dog on a back-to-back", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b")])
x2 = L.cell("NBA favorite rested (2+ days), dog on a back-to-back",
            [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and g[f].get("rest", 0) >= 2])
L.cell("NBA ... and the favorite at home",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("b2b") and g[f].get("rest", 0) >= 2 and f == "H"])
L.cell("NBA the FAVORITE on a back-to-back, dog rested",
       [(g["season"], L.ml(g, f)) for g, f in F if g[f].get("b2b") and not g[L.other(f)].get("b2b")])
L.cell("NBA dog 3rd game in 4 nights", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)].get("g4", 0) >= 2])
so = L.cell("NBA the dog's minutes leader OUT", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["star_out"]])
L.cell("NBA the dog's leader plays", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["star_out"] is False])
L.cell("NBA two of the dog's top three OUT", [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["two_out"]])
L.cell("NBA dog's leader out, favorite's leader plays",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["star_out"] and g[f]["star_out"] is False])
L.cell("NBA the FAVORITE's leader out", [(g["season"], L.ml(g, f)) for g, f in F if g[f]["star_out"]])
L.cell("NBA dog's leader out + dog on a back-to-back",
       [(g["season"], L.ml(g, f)) for g, f in F if g[L.other(f)]["star_out"] and g[L.other(f)].get("b2b")])
L.cell("NBA favorite at home off 2+ days vs a dog on its 3rd+ straight road game",
       [(g["season"], L.ml(g, f)) for g, f in F if f == "H" and g["H"].get("rest", 0) >= 2 and g["A"].get("road_run", 0) >= 2])
for lg in ("nfl", "ncaaf", "ncaab"):
    Fx = favs(lg)
    L.cell(f"{lg} every favorite -151..-199", [(g["season"], L.ml(g, f)) for g, f in Fx])
    L.cell(f"{lg} favorite with 2+ more days of rest", [(g["season"], L.ml(g, f)) for g, f in Fx
                                                        if g[f].get("rest", 0) - g[L.other(f)].get("rest", 99) >= 2])
    L.cell(f"{lg} home favorite", [(g["season"], L.ml(g, f)) for g, f in Fx if f == "H" and not g["neutral"]])
    L.cell(f"{lg} road favorite", [(g["season"], L.ml(g, f)) for g, f in Fx if f == "A" and not g["neutral"]])

# ---------------------------------------------------------------- S3
print("\n" + "=" * 30, "S3. THE FIRST NUMBER (ESPN's opening moneyline, 2023-26; train 2023-24 / blind 2025-26)")
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    G = [g for g in L.table(lg) if L.reg(g) and g["oh"] and g["oa"] and g["mlh"] and g["mla"]]
    a, b_, mv = [], [], []
    for g in G:
        fo = "H" if g["oh"] < g["oa"] else "A" if g["oa"] < g["oh"] else None
        if fo and band(L.odds(g, fo, True)):
            a.append((g["season"], L.ml(g, fo, True)))
            b_.append((g["season"], L.ml(g, fo)))
            po, pc = 1 / L.dec(L.odds(g, fo, True)), 1 / L.dec(L.odds(g, fo))
            mv.append((g, fo, 100 * (pc - po)))
    L.cell(f"{lg} favorite -151..-199 AT THE OPEN, bet at the open", a, train_to=2024)
    L.cell(f"{lg}   the same sides bet at the close", b_, train_to=2024)
    if mv:
        up = sum(1 for _, _, m in mv if m > 0.5)
        dn = sum(1 for _, _, m in mv if m < -0.5)
        print(f"   the price moved {sum(m for _, _, m in mv) / len(mv):+.2f} points of win chance open -> close "
              f"(dearer {up}, cheaper {dn}, flat {len(mv) - up - dn})")
    L.cell(f"{lg}   opened in the band, got DEARER 2+ points (bet at the open)",
           [(g["season"], L.ml(g, f, True)) for g, f, m in mv if m >= 2], train_to=2024)
    L.cell(f"{lg}   opened in the band, got CHEAPER 2+ points (bet at the close)",
           [(g["season"], L.ml(g, f)) for g, f, m in mv if m <= -2], train_to=2024)
    L.cell(f"{lg}   opened -101..-150, CLOSED -151..-199 (bet at the open)",
           [(g["season"], L.ml(g, s, True)) for g in G for s in ("H", "A")
            if band(L.odds(g, s, True), -150, -101) and band(L.odds(g, s))], train_to=2024)
    L.cell(f"{lg}   opened -101..-150, CLOSED -151..-199 (bet at the close)",
           [(g["season"], L.ml(g, s)) for g in G for s in ("H", "A")
            if band(L.odds(g, s, True), -150, -101) and band(L.odds(g, s))], train_to=2024)

# ---------------------------------------------------------------- S2
print("\n" + "=" * 30, "S2. BOTH READS AGREE BIG (the board's replay rows 2023-26 at the close; train to 2025-06-30)")
FUNNEL = os.environ.get("FUNNEL", "")
rows = []
for q in sorted(glob.glob(FUNNEL + "/f[A-D].jsonl")) + ([FUNNEL + "/fLive.jsonl"] if FUNNEL else []):
    if os.path.exists(q):
        with open(q) as fh:
            rows += [json.loads(x) for x in fh if x.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost") and r.get("stype") in ("2", None) and band(r.get("odds"))
        and r["league"] in ("nfl", "ncaaf", "nhl", "nba", "ncaab")]
print(f"{len(rows)} favorites -151..-199 with an engine read")
if rows:
    idx = {}
    for lg in ("nhl", "nba"):
        for g in L.table(lg):
            idx[(lg, g["hn"], g["an"], g["day"])] = g

    def own(r):
        if r["league"] in ("nhl", "nba") and r.get("w_p") is not None:
            return r["w_p"]
        return None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]

    def om(r):
        o = own(r)
        return None if o is None else 100 * (o - 1 / r["dec"])

    def wm(r):
        return 100 * (r["p"] - 1 / r["dec"])

    def game(r):
        d = date.fromisoformat(r["date"])
        hn, an = (r["team"], r["opp"]) if r["home"] else (r["opp"], r["team"])
        for dd in (d, date.fromordinal(d.toordinal() - 1), date.fromordinal(d.toordinal() + 1)):
            g = idx.get((r["league"], hn, an, dd))
            if g:
                return g
        return None

    def cut(name, rs):
        L.CELLS[0] += 1
        tr = [r for r in rs if r["date"] < "2025-07-01"]
        he = [r for r in rs if "2025-07-01" <= r["date"] < "2026-10-13"]
        lv = [r for r in rs if r["date"] >= "2026-10-13"]

        def s(x):
            if not x:
                return "   n0"
            n = len(x)
            w = sum(1 for r in x if r["result"] == "won")
            roi = sum((r["dec"] - 1) if r["result"] == "won" else -1 for r in x) / n
            return f"{w}-{n - w} {100 * roi:+6.1f}%"
        print(f"{name[:58]:<58} all {s(tr + he)} | train {s(tr)} | HELD {s(he)} | live {s(lv)}")

    cut("every favorite in the band with a read", rows)
    for k in (2, 3, 5, 8):
        cut(f"own AND weighed both {k}+ over", [r for r in rows if (om(r) or -9) >= k and wm(r) >= k])
    for lg in ("nhl", "nba", "ncaab", "ncaaf", "nfl"):
        cut(f"  {lg}: both 5+ over", [r for r in rows if r["league"] == lg and (om(r) or -9) >= 5 and wm(r) >= 5])
        cut(f"  {lg}: both 2+ over", [r for r in rows if r["league"] == lg and (om(r) or -9) >= 2 and wm(r) >= 2])
    cut("both 5+ over, at home", [r for r in rows if (om(r) or -9) >= 5 and wm(r) >= 5 and r["home"]])
    cut("both 5+ over, 4+ reasons", [r for r in rows if (om(r) or -9) >= 5 and wm(r) >= 5 and (r.get("n_reasons") or 0) >= 4])
    cut("both 5+ over, the whole play bar (good, own beats, real value)",
        [r for r in rows if (om(r) or -9) >= 5 and wm(r) >= 5 and r.get("good") and r.get("own_beats") and r.get("real_value")])
    j = [(r, game(r)) for r in rows if r["league"] in ("nhl", "nba")]
    print(f"  (joined to the game files: {sum(1 for _, g in j if g)} of {len(j)} NHL / NBA rows)")

    def opp_side(r):
        return "A" if r["home"] else "H"
    cut("NHL / NBA weighed read at / over the price + the dog on a back-to-back",
        [r for r, g in j if g and wm(r) >= 0 and g[opp_side(r)].get("b2b")])
    cut("NHL / NBA weighed 2+ over + the dog on a back-to-back",
        [r for r, g in j if g and wm(r) >= 2 and g[opp_side(r)].get("b2b")])
    cut("NHL weighed at / over the price + the dog's backup goalie",
        [r for r, g in j if g and r["league"] == "nhl" and wm(r) >= 0 and g[opp_side(r)].get("bk")])
    cut("NBA weighed at / over + the dog's minutes leader out",
        [r for r, g in j if g and r["league"] == "nba" and wm(r) >= 0 and g[opp_side(r)].get("star_out")])
    cut("NHL / NBA weighed UNDER the price + the dog on a back-to-back",
        [r for r, g in j if g and wm(r) < 0 and g[opp_side(r)].get("b2b")])
else:
    print("  (no FUNNEL folder given - S2 skipped)")

# ---------------------------------------------------------------- S4
print("\n" + "=" * 30, "S4. SIZING")
print("A pocket earns a size only if it is up in BOTH halves with z 2+ and most seasons up. Scan of S1's cells:")
for nm, c in (("NHL rested vs a back-to-back", x), ("NHL dog's backup goalie", bk), ("NBA rested vs a back-to-back", x2),
              ("NBA dog's minutes leader out", so)):
    ok = c["train"]["roi"] > 0 and c["blind"]["roi"] > 0 and c["all"]["z"] >= 2
    print(f"  {nm}: all {100 * c['all']['roi']:+.1f}% on {c['all']['n']} (z {c['all']['z']:+.1f}), train "
          f"{100 * c['train']['roi']:+.1f}%, blind {100 * c['blind']['roi']:+.1f}% -> {'PASSES' if ok else 'no size'}")
L.done()
