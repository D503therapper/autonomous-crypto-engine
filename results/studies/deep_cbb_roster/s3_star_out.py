"""S3 - IN-SEASON AVAILABILITY: a team's top-2 scorer (by points a game so far, 3+ games, 20+ minutes) misses a game.

(a) EX POST - he's not in tonight's box. Does the close have it? Mean (margin + closing spread) for the team when a
    star sat vs when both played; the same at the ML (won - no-vig) and, 2023-25, how far the ML moved open -> close.
    Not a bet by itself (an unannounced absence isn't known before tip) - it says whether the market prices it.
(b) BETTABLE - he missed the team's LAST game (known before tip): the team tonight (whether he plays or not), at the
    close; split by his status tonight (ex post) to show what the market does with each.
(c) the RETURN - he missed the last game and is back tonight.
Cut by the team's tier (power / mid / low = the inferred conference) and the star's share of the scoring."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, cell, profit_ml, profit_ats, profit_open, dec  # noqa: E402
import numpy as np

tb = [x for x in table() if x["stype"] == "2" and x["f"].get("stars") and x["f"].get("has_box")]
out = []


def P(s):
    print(s)
    out.append(s)


def resid(xs, fn=lambda x: x["margin"] + x["sp"] if x.get("sp") is not None else None):
    v = [fn(x) for x in xs]
    v = [a for a in v if a is not None]
    if not v:
        return "-"
    return f"{np.mean(v):+5.2f} pts (se {np.std(v)/np.sqrt(len(v)):.2f}, n{len(v)})"


def mlres(xs):
    v = [(x["won"] - x["p"]) * 100 for x in xs if x.get("p") is not None]
    return f"{np.mean(v):+5.1f}% (n{len(v)})" if v else "-"


def move(xs):
    v = [(x["p"] - x["po"]) * 100 for x in xs if x.get("p") is not None and x.get("po") is not None]
    return f"{np.mean(v):+5.2f}% (n{len(v)})" if v else "-"


P(f"{len(tb)} team sides with 2 stars defined (game 4+) and a box tonight")
for lab, sel in (("both stars play", lambda x: x["f"].get("star_out_now") == 0),
                 ("a star SITS tonight (ex post)", lambda x: x["f"].get("star_out_now", 0) >= 1),
                 ("  - one sits", lambda x: x["f"].get("star_out_now") == 1),
                 ("  - both sit", lambda x: x["f"].get("star_out_now") == 2),
                 ("missed LAST game (known)", lambda x: x["f"].get("star_missed_last", 0) >= 1),
                 ("  - and sits again", lambda x: x["f"].get("star_missed_last", 0) >= 1 and x["f"].get("star_out_now", 0) >= 1),
                 ("  - back tonight", lambda x: x["f"].get("star_back", 0) >= 1),
                 ("first game OUT (played last, sits tonight)", lambda x: x["f"].get("star_missed_last") == 0 and x["f"].get("star_out_now", 0) >= 1)):
    xs = [x for x in tb if sel(x)]
    P(f"{lab:45s} ATS resid {resid(xs)} | ML resid {mlres(xs)} | open->close move {move(xs)}")
    for t in ("power", "mid", "low"):
        ys = [x for x in xs if x["tier"] == t]
        P(f"    {t:6s} ATS resid {resid(ys)} | ML resid {mlres(ys)} | move {move(ys)}")

P("")
P("=== BETTABLE CELLS (bet the side named; ATS at the closing spread juice, ML at the close; train 2022-23, held 2024/25)")
sm = lambda x: x["f"].get("star_missed_last", 0) >= 1
osm = lambda x: x["of"].get("star_missed_last", 0) >= 1 if x.get("of") else False
for lab, sel in (("team whose star missed its last game", lambda x: sm(x) and not osm(x)),
                 ("  low tier", lambda x: sm(x) and not osm(x) and x["tier"] == "low"),
                 ("  mid tier", lambda x: sm(x) and not osm(x) and x["tier"] == "mid"),
                 ("  power", lambda x: sm(x) and not osm(x) and x["tier"] == "power"),
                 ("  star share 40%+ of scoring", lambda x: sm(x) and not osm(x) and (x["f"].get("star_share") or 0) >= 0.4),
                 ("OPPONENT of a team whose star missed its last", lambda x: osm(x) and not sm(x)),
                 ("  low tier opp", lambda x: osm(x) and not sm(x) and x["otier"] == "low"),
                 ("  power opp", lambda x: osm(x) and not sm(x) and x["otier"] == "power")):
    xs = [x for x in tb if sel(x)]
    cell(f"ATS {lab}", xs, profit_ats, out)
    cell(f"ML fav -101..-250 {lab}", [x for x in xs if x.get("ml") and -250 <= x["ml"] <= -101], profit_ml, out)
    cell(f"ML dog +100..+350 {lab}", [x for x in xs if x.get("ml") and 100 <= x["ml"] <= 350], profit_ml, out)
P("")
P("=== EX POST (not bettable without the news) - how much a sitting star is under-priced at the close")
for lab, sel in (("team, a star sits tonight, played last game", lambda x: x["f"].get("star_missed_last") == 0 and x["f"].get("star_out_now", 0) >= 1),
                 ("  low", lambda x: x["f"].get("star_missed_last") == 0 and x["f"].get("star_out_now", 0) >= 1 and x["tier"] == "low"),
                 ("  power", lambda x: x["f"].get("star_missed_last") == 0 and x["f"].get("star_out_now", 0) >= 1 and x["tier"] == "power"),
                 ("team, star missed last AND sits again", lambda x: x["f"].get("star_missed_last", 0) >= 1 and x["f"].get("star_out_now", 0) >= 1),
                 ("team, star missed last, BACK tonight", lambda x: x["f"].get("star_back", 0) >= 1)):
    xs = [x for x in tb if sel(x)]
    cell(f"ATS {lab}", xs, profit_ats, out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_out.txt"), "w").write("\n".join(out) + "\n")
