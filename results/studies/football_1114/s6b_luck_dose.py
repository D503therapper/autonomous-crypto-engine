"""11/14 FOOTBALL - S6b: THE UNLUCKY SMALL FAVORITE - the dose, the two luck measures together, and the leak checks.
S6 found: a -101..-150 favorite whose RECORD lags its play loses against its price - NFL by the one-score record (net 2+
close losses: -18.0% on 114, 0 of 9 seasons up), college by the Pythagorean share (0.15+ under: -23.5% on 98, held 0 of
5 up). Here: each measure's dose in each league, the two together ("lags" = either), the price bands next door, the
side across, ATS, home / road, the month. Prices: ESPN's close. Train 2018-21 / held 2022-26.
Usage: python results/studies/football_1114/s6b_luck_dose.py > results/studies/football_1114/s6b_out.txt"""
import flib as F

N = [0]


def c(name, rs, kind="ml", pool=None, worse=True):
    N[0] += 1
    r = F.cell(name, rs, kind)
    if pool is not None and r and r["all"] and r["all"]["n"] >= 30:
        p = F.placebo(rs, pool, kind, worse=worse)
        print(f"      placebo ({'as badly' if worse else 'as well'}): {p} of 2000")
    return r


def fav(r, lo=-150, hi=-101):
    return lo <= r["odds"] <= hi


def luck(s):
    return s["w"] / s["n"] - s["py"]


def close(s):
    return s["one_w"] - (s["one_n"] - s["one_w"])


def lags(s, pc=-0.10, cc=-2):
    return luck(s) <= pc or close(s) <= cc


for lg in ("nfl", "ncaaf"):
    rows = F.sides(lg)
    if lg == "ncaaf":
        rows = [r for r in rows if r["fbs"] and r["ofbs"]]
    q = [r for r in rows if r["me"]["n"] >= 4 and r["op"]["n"] >= 4]
    F_ = [r for r in q if fav(r)]
    print(f"\n=================== {lg.upper()}: favorites -101..-150, 4+ games both ({len(F_)}) ===================")
    c("every one", F_)
    print("-- the Pythagorean dose (win share minus points share)")
    for lo, hi in ((-9, -0.20), (-0.20, -0.15), (-0.15, -0.10), (-0.10, -0.05), (-0.05, 0.05), (0.05, 0.10), (0.10, 9)):
        c(f"luck {lo:+.2f}..{hi:+.2f}", [r for r in F_ if lo < luck(r["me"]) <= hi])
    print("-- the one-score dose (close wins minus close losses)")
    for lo, hi in ((-99, -3), (-3, -2), (-2, -1), (-1, 0), (0, 1), (1, 99)):
        c(f"close net {lo}..{hi}", [r for r in F_ if lo < close(r["me"]) <= hi])
    print("-- together")
    L = [r for r in F_ if lags(r["me"])]
    c("LAGS (luck <= -0.10 or close net <= -2)", L, pool=F_)
    c("LAGS, both measures", [r for r in F_ if luck(r["me"]) <= -0.10 and close(r["me"]) <= -2], pool=F_)
    c("LAGS ATS (the same favorites on the spread)", L, "ats", pool=F_)
    c("LAGS home", [r for r in L if r["home"] and not r["neutral"]])
    c("LAGS road / neutral", [r for r in L if not r["home"] or r["neutral"]])
    c("LAGS Sep-Oct", [r for r in L if r["month"] in (8, 9, 10)])
    c("LAGS Nov+", [r for r in L if r["month"] in (11, 12, 1)])
    c("LAGS, the opponent also lags", [r for r in L if lags(r["op"])])
    c("LAGS, the opponent does not", [r for r in L if not lags(r["op"])])
    c("LAGS, the record .500+", [r for r in L if r["me"]["w"] * 2 >= r["me"]["n"]])
    c("LAGS, the record under .500", [r for r in L if r["me"]["w"] * 2 < r["me"]["n"]])
    print("-- next door")
    for lo, hi in ((-200, -151), (-300, -201)):
        B = [r for r in q if fav(r, lo, hi)]
        c(f"LAGS fav {lo}..{hi}", [r for r in B if lags(r["me"])], pool=B)
    D = [r for r in q if 100 <= r["odds"] <= 350]
    c("the DOG +100..+150 across a lagging favorite", [r for r in D if lags(r["op"]) and r["odds"] <= 150],
      pool=[r for r in D if r["odds"] <= 150], worse=False)
    c("LAGS dog +100..+350 (the same teams as dogs)", [r for r in D if lags(r["me"])], pool=D, worse=False)
    print("-- the 4-game minimum moved")
    for mn in (3, 5, 6):
        q2 = [r for r in rows if r["me"]["n"] >= mn and r["op"]["n"] >= mn and fav(r)]
        c(f"LAGS, {mn}+ games", [r for r in q2 if lags(r["me"])], pool=q2)
print(f"\n{N[0]} cells - about {N[0] * 3 // 20} lines (x3 halves) would clear |z| 2 by luck.")
