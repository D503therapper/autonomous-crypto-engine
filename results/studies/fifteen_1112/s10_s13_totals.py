"""S10-S13 - TOTALS IN THE NBA, THE NHL, COLLEGE FOOTBALL AND THE NFL: new cuts only (the dead list of 11/1-11/11 is
not re-run: NBA Denver / Utah totals, one-team back-to-back totals, pace totals, total streaks, very high / low totals,
hockey goalie totals, football weather, NFL division unders as a whole, NFL night totals, altitude outside college
hoops). The close at its own juice, train to 2021 / blind 2022 on.

S10 NBA: BOTH teams' rest together (both on a back-to-back, both on a 3rd game in 4, both rested 2+), stars OUT (box
    scores: the minutes leader / two of the top three with no minutes tonight), a team's first game back home after a
    4+ game trip, a rested team hosting a tired one.
S11 NHL: both teams on a back-to-back, both backups in net, shooting-% / save-% luck regressing (season shooting % +
    save % from the box scores: 'PDO'), shot volume against the total.
S12 COLLEGE FOOTBALL: tempo (offensive plays a game from the box scores), a lower-division opponent, annual opponents
    late in the season (the conference-game proxy: the two met in each of the last two seasons), the second half of
    the season by month.
S13 NFL: the division REMATCH (the second meeting of a season), primetime, a dome team outdoors in the cold late, the
    wind PROXY a bettor could have had (the stadium's own windy history - earlier seasons' games there - not the
    game-day reading)."""
from collections import defaultdict

import lib as L
import box as B


def both(rows, name, tt=L.TRAIN_TO):
    a = L.cell(name + " OVER", [(g["season"], L.tot(g, "over")) for g in rows], train_to=tt)
    b = L.cell(name + " UNDER", [(g["season"], L.tot(g, "under")) for g in rows], train_to=tt)
    return a, b


def miss(rows):
    v = [g["hs"] + g["as"] - g["tot"] for g in rows if g["tot"] is not None]
    return sum(v) / len(v) if v else 0.0


# ---------------------------------------------------------------- S10
print("=" * 30, "S10. NBA TOTALS")
nba = B.nba_stars(L.table("nba"))
N = [g for g in nba if L.reg(g) and g["tot"] is not None]
both(N, "every NBA game")
both([g for g in N if g["H"].get("b2b") and g["A"].get("b2b")], "BOTH on a back-to-back")
both([g for g in N if g["H"].get("g4", 0) >= 2 and g["A"].get("g4", 0) >= 2], "BOTH on a 3rd game in 4 nights")
both([g for g in N if g["H"].get("g6", 0) >= 3 and g["A"].get("g6", 0) >= 3], "BOTH on a 4th game in 6 nights")
both([g for g in N if g["H"].get("rest", 0) >= 3 and g["A"].get("rest", 0) >= 3], "BOTH off 3+ days")
both([g for g in N if g["H"].get("rest", 0) >= 2 and g["A"].get("b2b")], "home rested, the visitor on a back-to-back")
both([g for g in N if g["A"].get("rest", 0) >= 2 and g["H"].get("b2b")], "visitor rested, the home team on a back-to-back")
both([g for g in N if g["A"].get("b2b") and g["A"]["last"]["ven"] == "A" and (g["A"]["last"].get("ot"))], "visitor on a back-to-back off an overtime game")
both([g for g in N if g["H"].get("star_out") or g["A"].get("star_out")], "a minutes leader OUT (either team)")
both([g for g in N if g["H"].get("star_out") and g["A"].get("star_out")], "BOTH minutes leaders out")
both([g for g in N if g["H"].get("two_out") or g["A"].get("two_out")], "two of a team's top three out")
both([g for g in N if (g["H"].get("n_out") or 0) + (g["A"].get("n_out") or 0) >= 3], "three+ of the six top-minutes men out")
both([g for g in N if g["H"].get("n_out") == 0 and g["A"].get("n_out") == 0], "all six top-minutes men play")
both([g for g in N if (g["H"].get("star_out") or g["A"].get("star_out")) and (g["H"].get("b2b") or g["A"].get("b2b"))],
     "a leader out on a back-to-back night (the rest night)")
both([g for g in N if (g["H"].get("two_out") and g["H"].get("pf", 0) and g["start"][5:7] in ("03", "04"))
      or (g["A"].get("two_out") and g["start"][5:7] in ("03", "04"))], "two of a top three out, March-April (the tank)")
both([g for g in N if g["H"]["n"] >= 5 and g["H"]["last"]["ven"] == "A" and g["H"].get("road_run", 0) >= 4], "home after a 4+ game trip")
for lo, hi in ((1400, 9999), (0, 100)):
    both([g for g in N if lo <= (g["elev"] or 0) < hi and g["A"].get("b2b")], f"visitor on a back-to-back, floor {lo}-{hi} m")
print(f"   the mean miss (points - total): a leader out {miss([g for g in N if g['H'].get('star_out') or g['A'].get('star_out')]):+.2f}, "
      f"all six play {miss([g for g in N if g['H'].get('n_out') == 0 and g['A'].get('n_out') == 0]):+.2f}, every game {miss(N):+.2f}")

# ---------------------------------------------------------------- S11
print("\n" + "=" * 30, "S11. NHL TOTALS")
nhl = B.nhl_shots(L.table("nhl"))
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
H = [g for g in nhl if L.reg(g) and g["tot"] is not None]
both(H, "every NHL game")
both([g for g in H if g["H"].get("b2b") and g["A"].get("b2b")], "BOTH on a back-to-back")
both([g for g in H if g["H"]["bk"] and g["A"]["bk"]], "BOTH backups in net")
both([g for g in H if g["H"]["bk"] and g["A"]["bk"] and g["tot"] <= 6], "BOTH backups, total 6 or less")
both([g for g in H if g["H"]["bk"] and g["A"]["bk"] and g["tot"] >= 6.5], "BOTH backups, total 6.5+")
both([g for g in H if g["H"]["bk"] is False and g["A"]["bk"] is False], "BOTH No. 1 goalies")
both([g for g in H if g["H"].get("b2b") and g["A"].get("b2b") and (g["H"]["bk"] or g["A"]["bk"])], "both back-to-back + a backup")
both([g for g in H if g["H"].get("rest", 0) >= 4 and g["A"].get("rest", 0) >= 4], "BOTH off 4+ days")
P = [g for g in H if "sh" in g["H"] and "sh" in g["A"]]
print(f"   ({len(P)} games with both teams' shooting / save % on 10+ box games)")
pdo = lambda f: f["sh"] + f["sv"]   # noqa: E731
both([g for g in P if pdo(g["H"]) >= 1.02 and pdo(g["A"]) >= 1.02], "BOTH teams running hot (PDO 102+)")
both([g for g in P if pdo(g["H"]) <= 0.98 and pdo(g["A"]) <= 0.98], "BOTH teams running cold (PDO 98 or less)")
both([g for g in P if g["H"]["sh"] >= 0.115 and g["A"]["sh"] >= 0.115], "BOTH shooting 11.5%+ (due to cool off)")
both([g for g in P if g["H"]["sh"] <= 0.09 and g["A"]["sh"] <= 0.09], "BOTH shooting 9% or less (due to heat up)")
both([g for g in P if g["H"]["sv"] <= 0.89 and g["A"]["sv"] <= 0.89], "BOTH save % .890 or worse")
both([g for g in P if g["H"]["sv"] >= 0.915 and g["A"]["sv"] >= 0.915], "BOTH save % .915+")
both([g for g in P if g["H"]["sh"] + g["A"]["sh"] >= 0.225 and g["tot"] >= 6.5], "hot shooting pair + total 6.5+ (the market chased it)")
both([g for g in P if g["H"]["sh"] + g["A"]["sh"] <= 0.185 and g["tot"] <= 5.5], "cold shooting pair + total 5.5 or less")
vol = lambda g: (g["H"]["sf"] + g["A"]["sa"] + g["A"]["sf"] + g["H"]["sa"]) / 2   # noqa: E731
both([g for g in P if vol(g) >= 63 and g["tot"] <= 6], "shot volume 63+ a game, total 6 or less")
both([g for g in P if vol(g) <= 56 and g["tot"] >= 6.5], "shot volume 56 or less, total 6.5+")
both([g for g in H if g["H"]["n"] <= 3 and g["A"]["n"] <= 3], "the first week (both 3 or fewer games in)")
both([g for g in H if g["start"][5:7] == "04"], "April (playoff seeding / dead rubbers)")

# ---------------------------------------------------------------- S12
print("\n" + "=" * 30, "S12. COLLEGE FOOTBALL TOTALS")
cf = B.plays(L.table("ncaaf"), "ncaaf")
priced = defaultdict(int)
for g in cf:
    if g["mlh"]:
        priced[(g["season"], g["home"])] += 1
        priced[(g["season"], g["away"])] += 1
met = defaultdict(set)
for g in cf:
    met[g["season"]].add(frozenset((g["home"], g["away"])))
F = [g for g in cf if L.reg(g) and g["tot"] is not None]
both(F, "every college football game")
T2 = [g for g in F if "plays" in g["H"] and "plays" in g["A"]]
print(f"   ({len(T2)} games with both teams' plays a game on 3+ box games; seasons {sorted({g['season'] for g in T2})})")
tempo = lambda g: g["H"]["plays"] + g["A"]["plays"]   # noqa: E731
qs = sorted(tempo(g) for g in T2)
hi_t, lo_t = qs[int(len(qs) * 0.8)], qs[int(len(qs) * 0.2)]
print(f"   both teams' plays a game: top fifth {hi_t:.0f}+, bottom fifth {lo_t:.0f} or less")
both([g for g in T2 if tempo(g) >= hi_t], "the two fastest-tempo fifth (plays a game)", tt=2023)
both([g for g in T2 if tempo(g) <= lo_t], "the two slowest-tempo fifth", tt=2023)
both([g for g in T2 if abs(g["H"]["plays"] - g["A"]["plays"]) >= 12], "a tempo mismatch of 12+ plays", tt=2023)
both([g for g in T2 if tempo(g) >= hi_t and g["tot"] <= 52], "fast pair, total 52 or less", tt=2023)
both([g for g in T2 if tempo(g) <= lo_t and g["tot"] >= 52], "slow pair, total 52+", tt=2023)
both([g for g in F if priced.get((g["season"] - 1, g["away"]), 0) < 4 or priced.get((g["season"] - 1, g["home"]), 0) < 4],
     "a lower-division / unpriced-last-season opponent")
ann = [g for g in F if frozenset((g["home"], g["away"])) in met.get(g["season"] - 1, ()) and
       frozenset((g["home"], g["away"])) in met.get(g["season"] - 2, ())]
both(ann, "annual opponents (met in each of the last two seasons)")
both([g for g in ann if g["start"][5:7] == "11"], "annual opponents in November")
both([g for g in ann if g["start"][5:7] == "11" and g["start"][8:10] >= "15"], "annual opponents from Nov 15")
both([g for g in ann if g["start"][5:7] in ("09",)], "annual opponents in September")
both([g for g in F if g["start"][5:7] == "11" and g["start"][8:10] >= "15"], "every game from Nov 15")
both([g for g in F if g["start"][5:7] == "11" and g["start"][8:10] >= "15" and g["tot"] >= 58], "from Nov 15, total 58+")
both([g for g in F if g["start"][5:7] == "11" and g["start"][8:10] >= "15" and g["tot"] <= 45], "from Nov 15, total 45 or less")
both([g for g in ann if g["start"][5:7] == "11" and all(g[s]["n"] >= 8 and g[s]["w"] / g[s]["n"] <= 0.34 for s in "HA")],
     "annual opponents in November, both .340 or worse")
both([g for g in F if g["H"]["n"] == 0 and g["A"]["n"] == 0], "both teams' opener")
both([g for g in F if g["H"].get("rest", 0) >= 13 and g["A"].get("rest", 0) >= 13], "both off a bye")
both([g for g in F if g["H"].get("rest", 9) <= 5 and g["A"].get("rest", 9) <= 5], "both on a short week")

# ---------------------------------------------------------------- S13
print("\n" + "=" * 30, "S13. NFL TOTALS")
nf = L.table("nfl")
seen = defaultdict(list)
dome = defaultdict(lambda: [0, 0])
wind_hist = defaultdict(list)
for g in nf:
    k = (g["season"], frozenset((g["home"], g["away"])))
    g["rematch"] = seen[k][-1] if seen[k] else None
    hd = dome[(g["season"] - 1, g["home"])]
    ad = dome[(g["season"] - 1, g["away"])]
    g["home_dome"] = hd[1] >= 5 and hd[0] / hd[1] >= 0.8
    g["away_dome"] = ad[1] >= 5 and ad[0] / ad[1] >= 0.8
    wh = [w for s, w in wind_hist[g["home"]] if s < g["season"]]
    g["wind_proxy"] = (sum(wh) / len(wh)) if len(wh) >= 8 else None
    g["wind_n"] = len(wh)
    if L.reg(g):
        seen[k].append(g)
    if not g["neutral"]:
        d = dome[(g["season"], g["home"])]
        d[1] += 1
        d[0] += 1 if str(g["indoor"]) == "1" else 0
        if g["wind"] is not None and str(g["indoor"]) != "1" and g["start"][5:7] in ("11", "12", "01"):
            wind_hist[g["home"]].append((g["season"], g["wind"]))
X = [g for g in nf if L.reg(g) and g["tot"] is not None]
both(X, "every NFL game")
RM = [g for g in X if g["rematch"]]
both(RM, "the division rematch (second meeting)")
both([g for g in RM if g["rematch"]["tot"] is not None and g["rematch"]["hs"] + g["rematch"]["as"] > g["rematch"]["tot"] + 7],
     "rematch, the first game went 7+ over")
both([g for g in RM if g["rematch"]["tot"] is not None and g["rematch"]["hs"] + g["rematch"]["as"] < g["rematch"]["tot"] - 7],
     "rematch, the first game went 7+ under")
both([g for g in RM if g["start"][5:7] in ("12", "01")], "rematch in Dec-Jan")
both([g for g in RM if (g["day"] - g["rematch"]["day"]).days <= 35], "rematch within 5 weeks")
both([g for g in RM if g["tot"] <= 42], "rematch, total 42 or less")
both([g for g in RM if g["tot"] >= 47], "rematch, total 47+")


def hour_et(g):
    return (int(g["start"][11:13]) + int(g["start"][14:16]) / 60 - 5) % 24


PT_ = [g for g in X if hour_et(g) >= 19 or hour_et(g) < 2]
both(PT_, "primetime (7 PM ET or later)")
both([g for g in PT_ if g["day"].weekday() == 6], "Sunday night")
both([g for g in PT_ if g["day"].weekday() == 0], "Monday night")
both([g for g in PT_ if g["day"].weekday() == 3], "Thursday night")
both([g for g in PT_ if g["rematch"]], "primetime division rematch")
both([g for g in PT_ if g["tot"] >= 47], "primetime, total 47+")
OUTC = [g for g in X if str(g["indoor"]) != "1" and not g["neutral"] and g["temp"] is not None]
both([g for g in OUTC if g["away_dome"] and g["temp"] <= 40 and g["start"][5:7] in ("11", "12", "01")], "a dome team outdoors, 40 F or colder, Nov on")
both([g for g in OUTC if g["away_dome"] and g["temp"] <= 32], "a dome team outdoors at freezing or colder")
both([g for g in OUTC if not g["away_dome"] and g["temp"] <= 40 and g["start"][5:7] in ("11", "12", "01")], "an OUTDOOR team in the same cold (the control)")
L.cell("  the dome team's SIDE against the spread, 40 F or colder",
       [(g["season"], L.ats(g, "A")) for g in OUTC if g["away_dome"] and g["temp"] <= 40 and g["start"][5:7] in ("11", "12", "01")])
L.cell("  the home side there", [(g["season"], L.ats(g, "H")) for g in OUTC if g["away_dome"] and g["temp"] <= 40 and g["start"][5:7] in ("11", "12", "01")])
L.cell("  a dome team outdoors (any weather) Sep-Oct, its side ATS", [(g["season"], L.ats(g, "A")) for g in OUTC if g["away_dome"] and g["start"][5:7] in ("09", "10")])
W = [g for g in X if str(g["indoor"]) != "1" and not g["neutral"] and g["wind_proxy"] is not None and g["start"][5:7] in ("11", "12", "01")]
print(f"   the wind PROXY: {len(W)} outdoor Nov-Jan games at a stadium with 8+ earlier late-season readings")
for k in (10, 11, 12, 13):
    both([g for g in W if g["wind_proxy"] >= k], f"a stadium that averages {k}+ mph late in the year (earlier seasons)")
both([g for g in W if g["wind_proxy"] < 8], "a calm stadium late in the year (under 8 mph on average)")
aw = [g for g in X if str(g["indoor"]) != "1" and g["wind"] is not None and g["wind"] >= 15]
both(aw, "for scale: the game-day reading 15+ mph (after the fact - NOT bettable)")
both([g for g in aw if g["season"] >= 2024], "   ... 2024 on")
if W:
    hit = [g for g in W if g["wind_proxy"] >= 11 and g["wind"] is not None]
    print(f"   at an 11+ mph stadium the game-day reading was 15+ in {sum(1 for g in hit if g['wind'] >= 15)} of {len(hit)} games "
          f"(every outdoor Nov-Jan game: {sum(1 for g in W if g['wind'] is not None and g['wind'] >= 15)} of {sum(1 for g in W if g['wind'] is not None)})")
L.done()
