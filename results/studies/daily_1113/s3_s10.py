"""11/13 daily studies S3-S10 (lib2's side rows at ESPN's close, regular season; train 2018-21, held 2022-25 apart,
2026 = now). Each study: its cells, then a placebo (random sets of the same size from the cell's own price band) on the
cells that look like something. Usage: python s3_s10.py [s3 s4 ...]"""
import os
import statistics
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib2  # noqa: E402

OUTD = os.path.dirname(os.path.abspath(__file__))
want = set(sys.argv[1:])


def dog(r, lo=100, hi=350):
    return lo <= r["odds"] <= hi


def fav(r, lo=-150, hi=-101):
    return lo <= r["odds"] <= hi


def reg(r):
    return r["stype"] == "2"


def run(name, fn):
    if want and name not in want:
        return
    out = []

    def say(s=""):
        print(s)
        out.append(s)
    say(f"===== {name}")
    fn(say)
    open(os.path.join(OUTD, f"{name}_out.txt"), "w").write("\n".join(out) + "\n")


def plac(say, label, rs, pool, kind="ml"):
    h = lib2.placebo(rs, pool, kind)
    say(f"    placebo {label}: {h} of 2,000 random same-size sets from the band did as well")


# ---------------- S3: college hoops sides by the closing total (relative to the league's last 300 totals)
def s3(say):
    rs = [r for r in lib2.rows("ncaab") if reg(r)]
    win = deque(maxlen=600)          # 300 games = 600 side rows
    seen = set()
    for r in rs:
        r["rel_t"] = (r["total"] - statistics.median(win)) if (r["total"] is not None and len(win) >= 200) else None
        if r["total"] is not None and r["id"] not in seen:
            seen.add(r["id"])
            win.append(r["total"])
            win.append(r["total"])
    bands = [("rel total 10+ under", lambda x: x <= -10), ("6-10 under", lambda x: -10 < x <= -6),
             ("2-6 under", lambda x: -6 < x <= -2), ("within 2", lambda x: -2 < x < 2), ("2-6 over", lambda x: 2 <= x < 6),
             ("6-10 over", lambda x: 6 <= x < 10), ("10+ over", lambda x: x >= 10)]
    R = [r for r in rs if r["rel_t"] is not None]
    say("MONEYLINE DOGS +100..+350")
    D = [r for r in R if dog(r)]
    lib2.cell("every dog", D, say=say)
    for nm, f in bands:
        lib2.cell(f"dog, {nm}", [r for r in D if f(r["rel_t"])], say=say)
    say("MONEYLINE FAVORITES -101..-150")
    F = [r for r in R if fav(r)]
    lib2.cell("every favorite", F, say=say)
    for nm, f in bands:
        lib2.cell(f"favorite, {nm}", [r for r in F if f(r["rel_t"])], say=say)
    say("SPREAD - the dog getting 10+ (fewer possessions = fewer chances to pull away)")
    B = [r for r in R if r["line"] is not None and r["line"] >= 10]
    lib2.cell("every dog +10 or more ATS", B, "ats", say=say)
    for nm, f in bands:
        lib2.cell(f"dog +10+ ATS, {nm}", [r for r in B if f(r["rel_t"])], "ats", say=say)
    S = [r for r in R if r["line"] is not None and 2.5 <= r["line"] < 10]
    lib2.cell("every dog +2.5..+9.5 ATS", S, "ats", say=say)
    for nm, f in bands[:2] + bands[-2:]:
        lib2.cell(f"dog +2.5..+9.5 ATS, {nm}", [r for r in S if f(r["rel_t"])], "ats", say=say)
    low_d = [r for r in D if r["rel_t"] <= -10]
    plac(say, "ML dog 10+ under", low_d, D)
    low_b = [r for r in B if r["rel_t"] <= -10]
    plac(say, "ATS dog +10, 10+ under", low_b, B, "ats")
    say("November-December only (where the engine is betting now)")
    nd = [r for r in D if r["start"][5:7] in ("11", "12")]
    for nm, f in (bands[0], bands[1], bands[-1]):
        lib2.cell(f"Nov-Dec dog, {nm}", [r for r in nd if f(r["rel_t"])], say=say)


# ---------------- S4 / S5: football - LAST SEASON'S MEETING (the same two teams)
def football_meet(lg, big):
    def f(say):
        rs = [r for r in lib2.rows(lg) if reg(r) and r["last_season_meet"] is not None]
        say(f"{lg}: sides with a meeting LAST season: {len(rs)} (the team's margin in the last one)")
        cuts = [(f"lost it by {big}+ (payback)", lambda m: m <= -big), (f"lost it by 1-{big - 1}", lambda m: -big < m < 0),
                (f"won it by 1-{big - 1}", lambda m: 0 < m < big), (f"won it by {big}+", lambda m: m >= big)]
        for kind, sel, lab in (("ml", dog, "DOG +100..+350"), ("ml", fav, "FAVORITE -101..-150"),
                               ("ats", lambda r: True, "ATS every side"),
                               ("ats", lambda r: r["line"] is not None and r["line"] > 0, "ATS the spread dog")):
            say(lab)
            base = [r for r in rs if sel(r)]
            lib2.cell("  all with a meeting", base, kind, say=say)
            for nm, c in cuts:
                lib2.cell(f"  {nm}", [r for r in base if c(r["last_season_meet"])], kind, say=say)
        # the payback side at home vs away
        pb = [r for r in rs if r["last_season_meet"] <= -big]
        lib2.cell("payback side at home, ATS", [r for r in pb if r["home"]], "ats", say=say)
        lib2.cell("payback side on the road, ATS", [r for r in pb if not r["home"]], "ats", say=say)
        lib2.cell("payback side, Oct-Dec (conference play), ATS", [r for r in pb if r["start"][5:7] in ("10", "11", "12")], "ats", say=say)
        plac(say, "payback ATS", pb, rs, "ats")
        plac(say, "payback dog ML", [r for r in pb if dog(r)], [r for r in rs if dog(r)])
    return f


# ---------------- S6: NBA back-to-back 2nd night by LAST NIGHT'S margin (a blowout = the starters sat the 4th)
def s6(say):
    rs = [r for r in lib2.rows("nba") if reg(r) and r["prev_gap_h"] is not None and r["prev_gap_h"] <= 30]
    say(f"NBA sides on the 2nd night of a back-to-back: {len(rs)}")
    cuts = [("last night a 20+ WIN", lambda m: m >= 20), ("last night a 20+ LOSS", lambda m: m <= -20),
            ("last night within 5", lambda m: abs(m) <= 5), ("last night 6-19 either way", lambda m: 6 <= abs(m) < 20)]
    for kind, sel, lab in (("ml", dog, "DOG +100..+350"), ("ml", fav, "FAVORITE -101..-150"),
                           ("ats", lambda r: True, "ATS every side")):
        say(lab)
        base = [r for r in rs if sel(r)]
        lib2.cell("  every b2b side", base, kind, say=say)
        for nm, c in cuts:
            lib2.cell(f"  {nm}", [r for r in base if c(r["prev_margin"])], kind, say=say)
        lib2.cell("  last night went to OT-ish (margin <= 3)", [r for r in base if abs(r["prev_margin"]) <= 3], kind, say=say)
    bw = [r for r in rs if r["prev_margin"] >= 20]
    plac(say, "ATS after a 20+ win", bw, rs, "ats")
    plac(say, "dog after a 20+ win", [r for r in bw if dog(r)], [r for r in rs if dog(r)])
    say("the side ACROSS a b2b team (rested or not) by that team's last-night margin")
    allr = lib2.rows("nba")
    across = {}
    for r in rs:
        across[(r["id"], r["opp"])] = r["prev_margin"]
    X = [r for r in allr if reg(r) and (r["id"], r["team"]) in across]
    for nm, c in cuts:
        lib2.cell(f"  across, {nm} - ATS", [r for r in X if c(across[(r['id'], r['team'])])], "ats", say=say)


# ---------------- S7: college hoops - the team that plays AGAIN within 30 hours (night 1 of a tournament back-to-back)
def s7(say):
    rs = [r for r in lib2.rows("ncaab") if reg(r) and r["start"][5:7] in ("11", "12")]
    n1 = [r for r in rs if r["next_gap_h"] is not None and r["next_gap_h"] <= 30]
    no = [r for r in rs if r["next_gap_h"] is not None and r["next_gap_h"] >= 48]
    say(f"Nov-Dec college hoops sides: night 1 of a back-to-back (plays again within 30h) {len(n1)}, next game 48h+ {len(no)}")
    for kind, sel, lab in (("ml", dog, "DOG +100..+350"), ("ml", fav, "FAVORITE -101..-150"),
                           ("ats", lambda r: r["line"] is not None and r["line"] < 0, "ATS the spread favorite"),
                           ("ats", lambda r: r["line"] is not None and r["line"] > 0, "ATS the spread dog")):
        say(lab)
        lib2.cell("  night 1 (plays again within 30h)", [r for r in n1 if sel(r)], kind, say=say)
        lib2.cell("  control: next game 48h+", [r for r in no if sel(r)], kind, say=say)
        lib2.cell("  night 1, the OPPONENT does NOT play tomorrow", [r for r in n1 if sel(r) and (r["onext_gap_h"] or 99) >= 48], kind, say=say)
        lib2.cell("  night 1, both play tomorrow", [r for r in n1 if sel(r) and (r["onext_gap_h"] or 99) <= 30], kind, say=say)
        lib2.cell("  night 1, at a neutral site", [r for r in n1 if sel(r) and r["neutral"]], kind, say=say)
        lib2.cell("  night 1, a true home / road game", [r for r in n1 if sel(r) and not r["neutral"]], kind, say=say)
    f1 = [r for r in n1 if r["line"] is not None and r["line"] < 0 and (r["onext_gap_h"] or 99) >= 48]
    plac(say, "ATS fav night 1 vs a team not playing tomorrow", f1, [r for r in rs if r["line"] is not None and r["line"] < 0], "ats")


# ---------------- S8: NFL - THE COLD DOG (.300 or worse after 6+ games)
def s8(say):
    rs = [r for r in lib2.rows("nfl") if reg(r) and r["w"] + r["l"] >= 6]
    say(f"NFL sides with 6+ games played: {len(rs)}")
    cold = lambda r: lib2.winpct(r["w"], r["l"]) <= 0.300
    for kind, sel, lab in (("ml", dog, "DOG +100..+350"), ("ats", lambda r: r["line"] is not None and r["line"] > 0, "ATS the spread dog")):
        say(lab)
        base = [r for r in rs if sel(r)]
        lib2.cell("  every one", base, kind, say=say)
        lib2.cell("  .300 or worse", [r for r in base if cold(r)], kind, say=say)
        lib2.cell("  .300 or worse vs a .500+ team", [r for r in base if cold(r) and lib2.winpct(r["ow"], r["ol"]) >= .5], kind, say=say)
        lib2.cell("  .300 or worse at home", [r for r in base if cold(r) and r["home"]], kind, say=say)
        lib2.cell("  .300 or worse on the road", [r for r in base if cold(r) and not r["home"]], kind, say=say)
        lib2.cell("  .200 or worse", [r for r in base if lib2.winpct(r["w"], r["l"]) <= 0.2], kind, say=say)
        lib2.cell("  .301-.450", [r for r in base if 0.3 < lib2.winpct(r["w"], r["l"]) <= 0.45], kind, say=say)
        lib2.cell("  .700+ (the hot dog)", [r for r in base if lib2.winpct(r["w"], r["l"]) >= 0.7], kind, say=say)
    cd = [r for r in rs if dog(r) and cold(r)]
    plac(say, "cold dog ML", cd, [r for r in rs if dog(r)])
    ca = [r for r in rs if r["line"] is not None and r["line"] > 0 and cold(r)]
    plac(say, "cold dog ATS", ca, [r for r in rs if r["line"] is not None and r["line"] > 0], "ats")


# ---------------- S9: college football - the team HELD TO 7 OR FEWER last game
def s9(say):
    rs = [r for r in lib2.rows("ncaaf") if reg(r) and r["prev_pts"] is not None]
    say(f"college football sides with a last game this season: {len(rs)}")
    cuts = [("held to 0-7 last game", lambda p: p <= 7), ("8-13", lambda p: 8 <= p <= 13), ("14-34", lambda p: 14 <= p <= 34),
            ("35+", lambda p: p >= 35)]
    for kind, sel, lab in (("ml", dog, "DOG +100..+350"), ("ml", fav, "FAVORITE -101..-150"),
                           ("ats", lambda r: True, "ATS every side"),
                           ("ats", lambda r: r["line"] is not None and r["line"] > 0, "ATS the spread dog"),
                           ("ats", lambda r: r["line"] is not None and r["line"] < 0, "ATS the spread favorite")):
        say(lab)
        base = [r for r in rs if sel(r)]
        lib2.cell("  every one", base, kind, say=say)
        for nm, c in cuts:
            lib2.cell(f"  {nm}", [r for r in base if c(r["prev_pts"])], kind, say=say)
    h7 = [r for r in rs if r["prev_pts"] <= 7]
    lib2.cell("held to 7, it was a LOSS by 21+ (a beatdown) ATS", [r for r in h7 if (r["prev_margin"] or 0) <= -21], "ats", say=say)
    lib2.cell("held to 7, a close loss (within 7) ATS", [r for r in h7 if -7 <= (r["prev_margin"] or 0) < 0], "ats", say=say)
    plac(say, "ATS held to 7", h7, rs, "ats")
    plac(say, "dog ML held to 7", [r for r in h7 if dog(r)], [r for r in rs if dog(r)])


# ---------------- S10: NBA - the BAD team favored (win % .400 or worse after 10+, favored -101..-150) / at home
def s10(say):
    rs = [r for r in lib2.rows("nba") if reg(r) and r["w"] + r["l"] >= 10]
    bad = lambda r: lib2.winpct(r["w"], r["l"]) <= 0.4
    worse = lambda r: r["ow"] + r["ol"] > 0 and lib2.winpct(r["w"], r["l"]) + 0.15 <= lib2.winpct(r["ow"], r["ol"])
    say(f"NBA sides with 10+ games: {len(rs)}")
    for kind, sel, lab in (("ml", fav, "FAVORITE -101..-150"),
                           ("ats", lambda r: r["line"] is not None and r["line"] < 0, "ATS the spread favorite")):
        say(lab)
        base = [r for r in rs if sel(r)]
        lib2.cell("  every one", base, kind, say=say)
        lib2.cell("  .400 or worse", [r for r in base if bad(r)], kind, say=say)
        lib2.cell("  .400 or worse at home", [r for r in base if bad(r) and r["home"]], kind, say=say)
        lib2.cell("  .400 or worse, the opponent 15+ points of win % better", [r for r in base if bad(r) and worse(r)], kind, say=say)
        lib2.cell("  any record, the opponent 15+ points better", [r for r in base if worse(r)], kind, say=say)
        lib2.cell("  .600+ favorite (control)", [r for r in base if lib2.winpct(r["w"], r["l"]) >= 0.6], kind, say=say)
    say("THE DOG ACROSS (the better team getting a price) +100..+199")
    D = [r for r in rs if 100 <= r["odds"] <= 199]
    lib2.cell("  every dog +100..+199", D, say=say)
    lib2.cell("  dog 15+ points of win % BETTER than the favorite", [r for r in D if r["ow"] + r["ol"] > 0 and lib2.winpct(r["w"], r["l"]) >= lib2.winpct(r["ow"], r["ol"]) + 0.15], say=say)
    bf = [r for r in rs if fav(r) and bad(r) and r["home"]]
    plac(say, "ML .400-or-worse home favorite -101..-150", bf, [r for r in rs if fav(r)])
    sf = [r for r in rs if r["line"] is not None and r["line"] < 0]
    bs = [r for r in sf if bad(r) and r["home"]]
    plac(say, "ATS .400-or-worse home spread favorite", bs, sf, "ats")
    say("dose (home favorites, ATS) by the win %:")
    for lo, hi in ((0, .3), (.3, .4), (.4, .5), (.5, .6), (.6, 1.01)):
        lib2.cell(f"  home spread fav, win % {lo:.2f}-{hi:.2f}", [r for r in sf if r["home"] and lo <= lib2.winpct(r["w"], r["l"]) < hi], "ats", say=say)
    say("the same on the road (a .400 team favored away)")
    lib2.cell("  road spread fav .400 or worse", [r for r in sf if not r["home"] and bad(r)], "ats", say=say)
    say("the side ACROSS (the road dog vs a .400-or-worse home favorite): ATS / ML")
    ids = {(r["id"]) for r in bs}
    allr = [r for r in rs if r["id"] in ids and not r["home"]]
    lib2.cell("  road dog across ATS", allr, "ats", say=say)
    lib2.cell("  road dog across ML +100..+199", [r for r in allr if 100 <= r["odds"] <= 199], say=say)
    say("by month (does the market catch up as the season goes?)")
    for m in ("11", "12", "01", "02", "03", "04"):
        lib2.cell(f"  month {m}", [r for r in bs if r["start"][5:7] == m], "ats", say=say)


run("s3", s3)
run("s4", football_meet("ncaaf", 17))
run("s5", football_meet("nfl", 14))
run("s6", s6)
run("s7", s7)
run("s8", s8)
run("s9", s9)
run("s10", s10)
