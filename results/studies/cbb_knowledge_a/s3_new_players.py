"""S3 - NEW PLAYERS, later in the season. The 11/3 DEEP roster table (results/studies/deep_cbb_roster/features.py -
every player matched by ESPN's id across seasons): sf_tin = the share of this season's minutes so far played by D1
TRANSFERS, sf_new = by NEWCOMERS with no earlier D1 box (freshmen / JUCO / overseas), ret_min = last season's minutes
back. The 11/3 study judged games 1-15 and 21+ by freshmen; here the TRANSFER-heavy team in Jan-Mar (do they gel, does
the market lag?) and the FRESHMAN-heavy team Feb-Mar, by month / game number / price / venue, and the gap between the
two rosters. Heavy = the top third of the season's teams on the share (set on the season's own January values - a
rank, no fit). Train 2022-23, held out 2024 / 2025 (the roster table starts 2022); ESPN's open on dog cells."""
import importlib.util, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403

_dl = importlib.util.spec_from_file_location("lib", os.path.join(ROOT, "results/studies/deep_cbb_roster/lib.py"))
DL = importlib.util.module_from_spec(_dl)
_mine = sys.modules.get("lib")
sys.modules["lib"] = DL                      # (features.py does 'from lib import *' - it means the roster study's lib)
_dl.loader.exec_module(DL)
_spec = importlib.util.spec_from_file_location("deep_feat", os.path.join(ROOT, "results/studies/deep_cbb_roster/features.py"))
FE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FE)
if _mine is not None:
    sys.modules["lib"] = _mine

out = Out("s3")
tb = [x for x in FE.table() if x["stype"] == "2" and x["season"] >= 2022 and x["f"].get("sf_n", 0) >= 10 and x["of"].get("sf_n", 0) >= 10]
month = lambda x: x["start"][5:7]
late = [x for x in tb if month(x) in ("01", "02", "03")]
# the season's top-third cuts on the January values (a rank, not a fit)
cut = {}
for s in sorted({x["season"] for x in late}):
    for key in ("sf_tin", "sf_new"):
        v = sorted(x["f"][key] for x in late if x["season"] == s and month(x) == "01" and key in x["f"])
        if v:
            cut[(s, key, "hi")] = v[int(len(v) * 2 / 3)]
            cut[(s, key, "lo")] = v[int(len(v) / 3)]
out.note("top-third cuts by season: " + ", ".join(f"{k[0]} {k[1]} {k[2]} {v:.2f}" for k, v in sorted(cut.items())))


def heavy(x, key, who="f"):
    f = x[who]
    c = cut.get((x["season"], key, "hi"))
    return c is not None and key in f and f[key] >= c


def light(x, key, who="f"):
    f = x[who]
    c = cut.get((x["season"], key, "lo"))
    return c is not None and key in f and f[key] <= c


out.h("A. THE TRANSFER-HEAVY TEAM (top third of this season's minutes by D1 transfers), Jan-Mar")
tr = [x for x in late if heavy(x, "sf_tin")]
lt = [x for x in late if light(x, "sf_tin")]
by_season_ats(late, "base: every Jan-Mar side (both 10+ box games)", out)
by_season_ats(tr, "transfer-heavy, Jan-Mar", out)
by_season_ats(lt, "transfer-light (returners), Jan-Mar", out)
for m in ("01", "02", "03"):
    by_season_ats([x for x in tr if month(x) == m], f"transfer-heavy, month {m}", out)
for lo, hi in ((11, 15), (16, 20), (21, 25), (26, 40)):
    by_season_ats([x for x in tr if lo <= x["gn"] <= hi], f"transfer-heavy, games {lo}-{hi}", out)
# the early-season control (the 11/3 lead lives in games 6-10)
early_tr = [x for x in tb if heavy(x, "sf_tin") and month(x) in ("11", "12")]
by_season_ats(early_tr, "transfer-heavy, Nov-Dec (control)", out)
for v in ("home", "away"):
    by_season_ats([x for x in tr if x["venue"] == v], f"transfer-heavy, Jan-Mar, {v}", out)
out.c("transfer-heavy dog +100..+200, Jan-Mar", dogs(tr, 100, 200))
out.c("transfer-heavy dog +201..+350, Jan-Mar", dogs(tr, 201, 350))
out.c("transfer-heavy fav -151..-300, Jan-Mar", favs(tr, -300, -151))
# the matchup: transfer-heavy vs a returning-heavy (transfer-light) opponent, and the reverse
mix = [x for x in tr if light(x, "sf_tin", "of")]
by_season_ats(mix, "transfer-heavy vs a returner team, Jan-Mar", out)
rev = [x for x in lt if heavy(x, "sf_tin", "of")]
by_season_ats(rev, "returner team vs a transfer-heavy team, Jan-Mar", out)
by_season_ats([x for x in rev if month(x) in ("02", "03")], "returner team vs transfer-heavy, Feb-Mar", out)
for t in ("power", "mid", "low"):
    by_season_ats([x for x in tr if x["tier"] == t], f"transfer-heavy, Jan-Mar, {t} tier", out)
# did they gel? the transfer-heavy team's cover margin by phase (price-free check)
def cm(xs):
    v = [x["margin"] + x["sp"] for x in xs if x.get("sp") is not None]
    return (sum(v) / len(v), len(v)) if v else (0, 0)
for lab, xs in (("games 1-5", [x for x in tb if heavy(x, "sf_tin") and x["gn"] <= 5]),
                ("games 6-10", [x for x in tb if heavy(x, "sf_tin") and 6 <= x["gn"] <= 10]),
                ("games 11-15", [x for x in tb if heavy(x, "sf_tin") and 11 <= x["gn"] <= 15]),
                ("games 16-20", [x for x in tr if 16 <= x["gn"] <= 20]), ("games 21-25", [x for x in tr if 21 <= x["gn"] <= 25]),
                ("games 26+", [x for x in tr if x["gn"] >= 26])):
    m, n = cm(xs)
    out.note(f"   transfer-heavy cover margin {lab}: {m:+.2f} pts on {n}")

out.h("B. THE FRESHMAN-HEAVY TEAM (top third of minutes by newcomers with no earlier D1 box), Feb-Mar")
fr = [x for x in late if heavy(x, "sf_new")]
ex = [x for x in late if light(x, "sf_new")]
by_season_ats(fr, "freshman-heavy, Jan-Mar", out)
by_season_ats([x for x in fr if month(x) in ("02", "03")], "freshman-heavy, Feb-Mar", out)
by_season_ats(ex, "experienced (few newcomers), Jan-Mar", out)
by_season_ats([x for x in ex if month(x) in ("02", "03")], "experienced, Feb-Mar", out)
for lo, hi in ((16, 20), (21, 25), (26, 40)):
    by_season_ats([x for x in fr if lo <= x["gn"] <= hi], f"freshman-heavy, games {lo}-{hi}", out)
by_season_ats([x for x in fr if month(x) in ("02", "03") and x["venue"] == "away"], "freshman-heavy, Feb-Mar, away", out)
by_season_ats([x for x in fr if month(x) in ("02", "03") and x["venue"] == "home"], "freshman-heavy, Feb-Mar, home", out)
out.c("freshman-heavy dog +100..+200, Feb-Mar", [x for x in dogs(fr, 100, 200) if month(x) in ("02", "03")])
out.c("freshman-heavy fav -101..-150, Feb-Mar", [x for x in favs(fr) if month(x) in ("02", "03")])
by_season_ats([x for x in fr if light(x, "sf_new", "of") and month(x) in ("02", "03")], "freshman-heavy vs an experienced team, Feb-Mar", out)
by_season_ats([x for x in ex if heavy(x, "sf_new", "of") and month(x) in ("02", "03")], "experienced vs a freshman-heavy team, Feb-Mar", out)
for t in ("power", "mid", "low"):
    by_season_ats([x for x in fr if x["tier"] == t and month(x) in ("02", "03")], f"freshman-heavy, Feb-Mar, {t} tier", out)
for lab, xs in (("Nov-Dec", [x for x in tb if heavy(x, "sf_new") and month(x) in ("11", "12")]), ("Jan", [x for x in fr if month(x) == "01"]),
                ("Feb", [x for x in fr if month(x) == "02"]), ("Mar", [x for x in fr if month(x) == "03"])):
    m, n = cm(xs)
    out.note(f"   freshman-heavy cover margin {lab}: {m:+.2f} pts on {n}")
# the whole-roster newness: transfers + newcomers 60%+ of the minutes (a 'new look' team) late
nl = [x for x in late if x["f"].get("sf_tin", 0) + x["f"].get("sf_new", 0) >= 0.6]
by_season_ats(nl, "60%+ of the minutes new this season, Jan-Mar", out)
by_season_ats([x for x in nl if month(x) in ("02", "03")], "60%+ new, Feb-Mar", out)
ol = [x for x in late if x["f"].get("ret_min") is not None and x["f"].get("sf_ret", 0) >= 0.7]
by_season_ats(ol, "70%+ of the minutes by returners, Jan-Mar", out)
by_season_ats([x for x in ol if month(x) in ("02", "03")], "70%+ returners, Feb-Mar", out)
by_season_ats([x for x in ol if x["of"].get("sf_tin", 0) + x["of"].get("sf_new", 0) >= 0.6 and month(x) in ("02", "03")],
              "70%+ returners vs a 60%+ new team, Feb-Mar", out)
out.save()
