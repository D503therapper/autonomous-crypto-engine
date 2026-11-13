"""11/13: placebos for the cells that looked like something (as-BAD counts for fades): the share of 2,000 random
same-size sets from the cell's own band that did at least as well (a bet) / at least as badly (a fade)."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib2  # noqa: E402

out = []


def say(s=""):
    print(s)
    out.append(s)


def pl(label, rs, pool, kind, fade, split=None):
    f = (lambda r: lib2.ml_profit(r)) if kind == "ml" else (lambda r: r["ats"])
    rs = [r for r in rs if f(r) is not None]
    pool = [r for r in pool if f(r) is not None]
    got = sum(f(r) for r in rs) / len(rs)
    vals = [f(r) for r in pool]
    rnd = random.Random(11)
    k = len(rs)
    n = 0
    for _ in range(2000):
        m = sum(rnd.sample(vals, k)) / k
        n += (m <= got) if fade else (m >= got)
    base = sum(vals) / len(vals)
    tr = [f(r) for r in rs if r["season"] <= 2021]
    he = [f(r) for r in rs if r["season"] >= 2022]
    say(f"{label:70s} n {k:4d} {got*100:+6.1f}% (band {base*100:+5.1f}%) train {sum(tr)/max(1,len(tr))*100:+6.1f}% on {len(tr)} / "
        f"held {sum(he)/max(1,len(he))*100:+6.1f}% on {len(he)} | placebo {'as bad' if fade else 'as good'}: {n} of 2,000")


nba = [r for r in lib2.rows("nba") if r["stype"] == "2"]
b2b = [r for r in nba if r["prev_gap_h"] is not None and r["prev_gap_h"] <= 30]
pl("S6 NBA b2b side after a 20+ LOSS last night, ATS", [r for r in b2b if r["prev_margin"] <= -20], b2b, "ats", False)
pl("S6 NBA b2b dog +100..+350 after a 20+ loss", [r for r in b2b if r["prev_margin"] <= -20 and 100 <= r["odds"] <= 350],
   [r for r in b2b if 100 <= r["odds"] <= 350], "ml", False)
pl("S6 NBA b2b dog after a game decided by 3 or fewer", [r for r in b2b if abs(r["prev_margin"]) <= 3 and 100 <= r["odds"] <= 350],
   [r for r in b2b if 100 <= r["odds"] <= 350], "ml", True)
pl("S6 NBA b2b side after a game decided by 3 or fewer, ATS", [r for r in b2b if abs(r["prev_margin"]) <= 3], b2b, "ats", True)
cf = [r for r in lib2.rows("ncaaf") if r["stype"] == "2" and r["last_season_meet"] is not None]
pl("S4 NCAAF side that WON last season's meeting by 17+, ATS (fade)", [r for r in cf if r["last_season_meet"] >= 17], cf, "ats", True)
pl("S4 NCAAF side that won last season's meeting by 1+, ATS (fade)", [r for r in cf if r["last_season_meet"] > 0], cf, "ats", True)
pl("S4 NCAAF payback side (lost by 17+), ATS", [r for r in cf if r["last_season_meet"] <= -17], cf, "ats", False)
s10 = [r for r in nba if r["w"] + r["l"] >= 10]
sf = [r for r in s10 if r["line"] is not None and r["line"] < 0]
pl("S10 NBA .400-or-worse HOME spread favorite, ATS (fade)", [r for r in sf if r["home"] and r["w"] / (r["w"] + r["l"]) <= .4], sf, "ats", True)
hf = [r for r in sf if r["home"]]
pl("S10 ... vs HOME spread favorites only (the home band)", [r for r in hf if r["w"] / (r["w"] + r["l"]) <= .4], hf, "ats", True)
mf = [r for r in s10 if -150 <= r["odds"] <= -101]
pl("S10 NBA .400-or-worse HOME ML favorite -101..-150 (fade)", [r for r in mf if r["home"] and r["w"] / (r["w"] + r["l"]) <= .4], mf, "ml", True)
mh = [r for r in mf if r["home"]]
pl("S10 ... vs HOME ML favorites only", [r for r in mh if r["w"] / (r["w"] + r["l"]) <= .4], mh, "ml", True)
nfl = [r for r in lib2.rows("nfl") if r["stype"] == "2" and r["w"] + r["l"] >= 6]
nd = [r for r in nfl if 100 <= r["odds"] <= 350]
pl("S8 NFL dog .300 or worse after 6+", [r for r in nd if r["w"] / (r["w"] + r["l"]) <= .3], nd, "ml", False)
pl("S8 NFL dog .301-.450 after 6+ (fade)", [r for r in nd if .3 < r["w"] / (r["w"] + r["l"]) <= .45], nd, "ml", True)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s_placebos_out.txt"), "w").write("\n".join(out) + "\n")
