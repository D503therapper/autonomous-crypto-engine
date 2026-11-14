"""11/14 FOOTBALL - S6 CLOSE-GAME LUCK and S7 THE GAME AFTER LOSING AS A BIG FAVORITE (NFL + college; flib.sides).
S6: a team's record vs what its points say (season to date, 4+ games): LUCKY = win share 0.15+ over its Pythagorean
    share (points for / against, exponent 2.37), or 2+ net wins in one-score games (8 or fewer); UNLUCKY the mirror.
    Never studied for football (11/2 hockey Pythagorean luck only; 11/4-11/10 interception / yard luck are other reads).
S7: the team that LOST OUTRIGHT last game as a big favorite (closing -250 or shorter, or laying 7+), this game; and the
    side across it. The +250 HANGOVER (the team that won as a big dog) is built (10/17) - this is the other side.
Prices: ESPN's close at its own juice. Train 2018-21, held out 2022-25 apart, 2026 = now.
Usage: python results/studies/football_1114/s6_s7_luck_upset.py > results/studies/football_1114/s6_s7_out.txt"""
import flib as F

N = [0]


def c(name, rs, kind="ml", pool=None, worse=False):
    N[0] += 1
    r = F.cell(name, rs, kind)
    if pool is not None and r and r["all"] and r["all"]["n"] >= 30:
        p = F.placebo(rs, pool, kind, worse=worse)
        print(f"      placebo ({'as badly' if worse else 'as well'}): {p} of 2000")
    return r


def fav(r, lo=-150, hi=-101):
    return lo <= r["odds"] <= hi


def dog(r, lo=100, hi=350):
    return lo <= r["odds"] <= hi


for lg in ("nfl", "ncaaf"):
    rows = F.sides(lg)
    if lg == "ncaaf":
        rows = [r for r in rows if r["fbs"] and r["ofbs"]]
    print(f"\n=================== {lg.upper()} ({len(rows)} sides) ===================")
    MIN = 4
    q = [r for r in rows if r["me"]["n"] >= MIN and r["op"]["n"] >= MIN]

    def luck(s):
        return s["w"] / s["n"] - s["py"]

    def close(s):
        return s["one_w"] - (s["one_n"] - s["one_w"])
    print("-- S6 base cells")
    c("every fav -101..-150 (4+ games both)", [r for r in q if fav(r)])
    c("every dog +100..+350 (4+ games both)", [r for r in q if dog(r)])
    c("every side ATS (4+ games both)", q, "ats")
    for nm, f, cut in (("Pythag luck", luck, 0.15), ("Pythag luck", luck, 0.10), ("one-score net", close, 2)):
        L = [r for r in q if f(r["me"]) >= cut]
        U = [r for r in q if f(r["me"]) <= -cut]
        print(f"-- S6 {nm} {cut}")
        c(f"LUCKY ({nm} >= {cut}) fav -101..-150", [r for r in L if fav(r)], pool=[r for r in q if fav(r)], worse=True)
        c(f"LUCKY fav -151..-400", [r for r in L if fav(r, -400, -151)])
        c(f"LUCKY dog +100..+350", [r for r in L if dog(r)], pool=[r for r in q if dog(r)], worse=True)
        c(f"LUCKY ATS", L, "ats", pool=q, worse=True)
        c(f"UNLUCKY ({nm} <= -{cut}) dog +100..+350", [r for r in U if dog(r)], pool=[r for r in q if dog(r)])
        c(f"UNLUCKY fav -101..-150", [r for r in U if fav(r)], pool=[r for r in q if fav(r)])
        c(f"UNLUCKY ATS", U, "ats", pool=q)
        M = [r for r in q if f(r["me"]) <= -cut and f(r["op"]) >= cut]
        c(f"MATCHUP unlucky vs lucky - ML any price +-350", [r for r in M if -350 <= r["odds"] <= 350])
        c(f"MATCHUP unlucky vs lucky - ATS", M, "ats")
        c(f"MATCHUP unlucky vs lucky - unlucky is the dog", [r for r in M if dog(r)])
    print("-- S7 the game after losing outright as a big favorite")
    q7 = [r for r in rows if r["me"]["last"] and r["me"]["last"]["season"] == r["season"] and r["me"]["last"]["stype"] == "2"]

    def big_loss(s, mo=-250, ln=-7):
        L = s["last"]
        return L["pf"] < L["pa"] and ((L["odds"] is not None and L["odds"] <= mo) or (L["line"] is not None and L["line"] <= ln))
    for mo, ln in ((-250, -7), (-400, -10)):
        B = [r for r in q7 if big_loss(r["me"], mo, ln)]
        A = [r for r in q7 if r["op"]["last"] and r["op"]["last"]["season"] == r["season"] and big_loss(r["op"], mo, ln)]
        print(f"   ({mo} / {ln}: {len(B)} sides)")
        c(f"lost as {mo}/{ln} last: fav -101..-150 now", [r for r in B if fav(r)], pool=[r for r in q7 if fav(r)])
        c(f"lost as {mo}/{ln} last: fav -151..-500 now", [r for r in B if fav(r, -500, -151)], pool=[r for r in q7 if fav(r, -500, -151)])
        c(f"lost as {mo}/{ln} last: dog +100..+350 now", [r for r in B if dog(r)], pool=[r for r in q7 if dog(r)])
        c(f"lost as {mo}/{ln} last: ATS", B, "ats", pool=q7)
        c(f"lost as {mo}/{ln} last: ATS home", [r for r in B if r["home"]], "ats")
        c(f"lost as {mo}/{ln} last: ATS road", [r for r in B if not r["home"]], "ats")
        c(f"side ACROSS it: dog +100..+350", [r for r in A if dog(r)], pool=[r for r in q7 if dog(r)])
        c(f"side ACROSS it: ATS", A, "ats", pool=q7)
print(f"\n{N[0]} cells - about {N[0] * 3 // 20} lines (x3 halves) would clear |z| 2 by luck.")
