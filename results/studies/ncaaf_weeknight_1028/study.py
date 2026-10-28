"""10/28 COLLEGE WEEKNIGHT DOG STUDIES (the owner, on New Mexico St +136 at home vs Jax State on a Wednesday: "they
just smacked Western Kentucky ... maybe even a 2-unit bet"). Five angles on college football dogs +100..+350, with the
weeknight (Tue/Wed/Thu/Fri, Eastern time) games split out from the Saturdays.

Rows: tools/early_football_study-style sides (the walk-forward own read trained on the 3 seasons before each one, the
closing price, the FIRST FAIR early price - up after both teams' last games - no look-ahead). The schedule facts (the
last game's margin and opponent, that opponent's record at the time, the favorite's last game as a priced dog) come from
the games file, games already final before kickoff only.

Train = 2020-2023, held out = 2024, 2025, 2026 (each on its own). Flat 1u at the close (and at the first fair price
where it says so). ROI next to the band's own ROI (the 'lift'), z against the no-vig price."""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO)
import sports_data as sd  # noqa: E402

ROWS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "rows_ncaaf.json")
TRAIN = {2020, 2021, 2022, 2023}
HOLDS = (2024, 2025, 2026)
E = "first look of the week"


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def nv(ml, ml_opp):
    a, b = 1 / dec(ml), 1 / dec(ml_opp)
    return a / (a + b)


rows = json.load(open(ROWS))
games = sd.load_games("ncaaf")

# ---- schedule facts: each team's games in order (finals only)
by_team = defaultdict(list)
for g in games.values():
    if g.get("status") != "final" or (g.get("stype") or "?") not in sd.REAL:
        continue
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (TypeError, ValueError):
        continue
    for side, other in (("home", "away"), ("away", "home")):
        m = (hs - as_) if side == "home" else (as_ - hs)
        try:
            ml = int(float(g["ml_" + side]))
        except (TypeError, ValueError):
            ml = None
        by_team[g[side]].append({"start": g["start"], "opp": g[other], "margin": m, "ml": ml, "won": m > 0,
                                 "home": side == "home"})
for t in by_team:
    by_team[t].sort(key=lambda x: x["start"])


def season0(start):
    y, mo = int(start[:4]), int(start[5:7])
    return f"{y if mo >= 7 else y - 1}-07-01"


def prev_game(team, start):
    pg = [x for x in by_team.get(team, []) if x["start"] < start and x["start"] >= season0(start)]
    return pg[-1] if pg else None


def record_before(team, start):
    pg = [x for x in by_team.get(team, []) if x["start"] < start and x["start"] >= season0(start)]
    return sum(x["won"] for x in pg), len(pg)


def _two_back(d):
    """The game before the dog's last one was a 14+ win (NM St: beat FIU 22-3, then lost at Sam Houston)."""
    pg = [x for x in by_team.get(d["team"], []) if x["start"] < d["start"] and x["start"] >= season0(d["start"])]
    return len(pg) >= 2 and pg[-2]["margin"] >= 14


def weekday_et(start):
    t = datetime.fromisoformat(start.replace("Z", "+00:00")) - timedelta(hours=5)
    return t.strftime("%a")


# ---- the dog rows
dogs = []
for r in rows:
    if not 100 <= r["close"] <= 350 or r["neutral"]:
        continue
    r = dict(r)
    r["nv"] = nv(r["close"], r["close_opp"])
    r["wd"] = weekday_et(r["start"])
    r["weeknight"] = r["wd"] in ("Tue", "Wed", "Thu", "Fri")
    r["midweek"] = r["wd"] in ("Tue", "Wed", "Thu")
    r["gap"] = (r["own"] - r["nv"]) * 100           # the own read over the no-vig price, points
    r["elo_gap"] = (r["elo_p"] - r["nv"]) * 100     # the ratings alone over the price
    r["own_over"] = r["own"] * dec(r["close"]) > 1  # the own read beats the juiced price
    pg = prev_game(r["team"], r["start"])
    og = prev_game(r["opp"], r["start"])
    r["last_big_win"] = bool(pg and pg["margin"] >= 14)
    if pg:
        ow, on = record_before(pg["opp"], pg["start"])            # that opponent's record going into that game
        r["last_opp_good"] = on >= 3 and ow / on > 0.5
        r["last_opp_liked"] = pg["ml"] is not None and pg["ml"] >= -120   # the dog was not a real favorite then
    else:
        r["last_opp_good"] = r["last_opp_liked"] = False
    r["fav_off_upset"] = bool(og and og["ml"] is not None and og["ml"] >= 100 and og["won"])
    r["fav_off_dog_loss"] = bool(og and og["ml"] is not None and og["ml"] >= 100 and not og["won"])
    r["fav_won_last"] = og["won"] if og else None
    r["won_last"] = pg["won"] if pg else None
    r["fav_road"] = r["side"] == "home"
    w = r.get("w", {}).get(E)
    if w and 100 <= w["price"] <= 350:
        r["early_price"] = w["price"]
        r["early_nv"] = w["mkt"]
        r["early_gap"] = (r["own_blind"] - w["mkt"]) * 100
    dogs.append(r)

out = []


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


def stats(rs, price="close"):
    if not rs:
        return (0, 0, 0.0, 0.0, 0.0, 0.0)
    if price == "early":
        pnl = sum((dec(d["early_price"]) - 1) if d["won"] else -1 for d in rs)
        imp = sum(d["early_nv"] for d in rs)
        var = sum(d["early_nv"] * (1 - d["early_nv"]) for d in rs)
    else:
        pnl = sum((dec(d["close"]) - 1) if d["won"] else -1 for d in rs)
        imp = sum(d["nv"] for d in rs)
        var = sum(d["nv"] * (1 - d["nv"]) for d in rs)
    w = sum(1 for d in rs if d["won"])
    z = (w - imp) / var ** 0.5 if var else 0.0
    return (len(rs), w, pnl / len(rs) * 100, w / len(rs) * 100, imp / len(rs) * 100, z)


def seasons_up(rs, price="close"):
    by = defaultdict(list)
    for d in rs:
        by[d["season"]].append(d)
    ok = [s for s in by if len(by[s]) >= 5]
    return sum(1 for s in ok if stats(by[s], price)[2] > 0), len(ok)


CELLS = 0


def cell(name, pred, pool=None, price="close", base_pred=None):
    """One line per slice: train / 2024 / 2025 / 2026, each 'n W-L ROI (band ROI) z'."""
    global CELLS
    CELLS += 1
    pool = pool if pool is not None else dogs
    if price == "early":
        pool = [d for d in pool if "early_price" in d]
    parts = []
    for lab, S in (("train", TRAIN), ("2024", {2024}), ("2025", {2025}), ("2026", {2026})):
        rs = [d for d in pool if d["season"] in S and pred(d)]
        bs = [d for d in pool if d["season"] in S and (base_pred(d) if base_pred else True)]
        n, w, roi, _, imp, z = stats(rs, price)
        bn, _, broi, *_ = stats(bs, price)
        if lab == "train":
            up, tot = seasons_up(rs, price)
            parts.append(f"train {w}-{n - w} {roi:+.1f}% (band {broi:+.1f}% on {bn}) z {z:+.1f} {up}/{tot} up")
        else:
            parts.append(f"{lab} {w}-{n - w} {roi:+.1f}% ({broi:+.1f}%)")
    P(f"  {name}: " + " | ".join(parts))


P(f"ROWS: {len(rows)} sides, {len(dogs)} dogs +100..+350 at the close (not neutral), "
  f"{sum(1 for d in dogs if d['weeknight'])} weeknight, {sum(1 for d in dogs if 'early_price' in d)} with a first fair price")
P("by weekday: " + ", ".join(f"{k} {v}" for k, v in sorted(defaultdict(int, {
    k: sum(1 for d in dogs if d['wd'] == k) for k in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')}).items())))

P("\n== STUDY 1: WEEKNIGHT vs SATURDAY college dogs (close) ==")
cell("ALL dogs", lambda d: True)
cell("Saturday", lambda d: d["wd"] == "Sat")
cell("weeknight Tue-Fri", lambda d: d["weeknight"])
cell("midweek Tue-Thu", lambda d: d["midweek"])
cell("Friday", lambda d: d["wd"] == "Fri")
for lo, hi in ((100, 150), (151, 250), (251, 350)):
    cell(f"weeknight +{lo}..+{hi}", lambda d, lo=lo, hi=hi: d["weeknight"] and lo <= d["close"] <= hi,
         base_pred=lambda d, lo=lo, hi=hi: lo <= d["close"] <= hi)
cell("weeknight HOME dog", lambda d: d["weeknight"] and d["side"] == "home", base_pred=lambda d: d["side"] == "home")
cell("weeknight ROAD dog", lambda d: d["weeknight"] and d["side"] == "away", base_pred=lambda d: d["side"] == "away")
cell("weeknight, own read over the price", lambda d: d["weeknight"] and d["own_over"], base_pred=lambda d: d["own_over"])
cell("Saturday, own read over the price", lambda d: d["wd"] == "Sat" and d["own_over"], base_pred=lambda d: d["own_over"])
cell("weeknight, own read UNDER the price", lambda d: d["weeknight"] and not d["own_over"], base_pred=lambda d: not d["own_over"])
cell("weeknight, Elo gap 0+", lambda d: d["weeknight"] and d["elo_gap"] >= 0, base_pred=lambda d: d["elo_gap"] >= 0)
cell("weeknight at the FIRST FAIR price", lambda d: d["weeknight"], price="early")
cell("weeknight, own over, FIRST FAIR price", lambda d: d["weeknight"] and d["own_blind"] * dec(d["early_price"]) > 1,
     price="early", base_pred=lambda d: d["own_blind"] * dec(d["early_price"]) > 1)
P("  (no conference map in the games file - MAC / CUSA / Sun Belt can't be split honestly; the weeknight slate IS those leagues)")

P("\n== STUDY 2: the dog's LAST GAME was a 14+ WIN over a GOOD team (the NM St story) ==")
cell("dog off a 14+ win (any opponent)", lambda d: d["last_big_win"])
cell("dog off a 14+ win over a WINNING-record team (3+ games)", lambda d: d["last_big_win"] and d["last_opp_good"])
cell("dog off a 14+ win where it was NOT the favorite (-120 or longer)", lambda d: d["last_big_win"] and d["last_opp_liked"])
cell("dog off a 14+ win over a winning team AND not favored then", lambda d: d["last_big_win"] and d["last_opp_good"] and d["last_opp_liked"])
cell("weeknight dog off a 14+ win over a winning team", lambda d: d["weeknight"] and d["last_big_win"] and d["last_opp_good"],
     base_pred=lambda d: d["weeknight"])
cell("dog off ANY win over a winning team", lambda d: d["won_last"] and d["last_opp_good"])
cell("dog off a LOSS last game (NM St's real spot)", lambda d: d["won_last"] is False)
cell("dog off a loss, 14+ win the game before that", lambda d: d["won_last"] is False and _two_back(d))

P("\n== STUDY 3: the FAVORITE is off an UPSET WIN as a dog last game (the brother's +15.1% on 167) ==")
cell("favorite off an upset win as a dog", lambda d: d["fav_off_upset"])
cell("  ...weeknight", lambda d: d["fav_off_upset"] and d["weeknight"], base_pred=lambda d: d["weeknight"])
cell("  ...Saturday", lambda d: d["fav_off_upset"] and d["wd"] == "Sat", base_pred=lambda d: d["wd"] == "Sat")
cell("  ...dog +100..+200", lambda d: d["fav_off_upset"] and d["close"] <= 200, base_pred=lambda d: d["close"] <= 200)
cell("  ...at the first fair price", lambda d: d["fav_off_upset"], price="early")
cell("  ...and our dog's own read over the price", lambda d: d["fav_off_upset"] and d["own_over"], base_pred=lambda d: d["own_over"])
cell("favorite off a LOSS as a dog last game", lambda d: d["fav_off_dog_loss"])
cell("favorite WON last game (any price)", lambda d: d["fav_won_last"] is True)
cell("favorite LOST last game (the built +2)", lambda d: d["fav_won_last"] is False)

P("\n== STUDY 4: REST and the favorite's TRAVEL on a weeknight ==")
WK = lambda d: d["weeknight"]  # noqa: E731
cell("weeknight dog on SHORT rest (<=5 days)", lambda d: d["weeknight"] and d["rest"] is not None and d["rest"] <= 5, base_pred=WK)
cell("weeknight dog on normal rest (6-8)", lambda d: d["weeknight"] and d["rest"] is not None and 6 <= d["rest"] <= 8, base_pred=WK)
cell("weeknight dog off a BYE (10+ days)", lambda d: d["weeknight"] and d["rest"] is not None and d["rest"] >= 10, base_pred=WK)
cell("weeknight FAVORITE on short rest (<=5)", lambda d: d["weeknight"] and d["orest"] is not None and d["orest"] <= 5, base_pred=WK)
cell("weeknight FAVORITE off a bye (10+)", lambda d: d["weeknight"] and d["orest"] is not None and d["orest"] >= 10, base_pred=WK)
cell("weeknight dog rested 2+ days MORE than the favorite", lambda d: d["weeknight"] and None not in (d["rest"], d["orest"]) and d["rest"] - d["orest"] >= 2, base_pred=WK)
cell("weeknight dog rested 2+ days LESS than the favorite", lambda d: d["weeknight"] and None not in (d["rest"], d["orest"]) and d["orest"] - d["rest"] >= 2, base_pred=WK)
cell("weeknight HOME dog vs a traveling favorite (= study 1 home)", lambda d: d["weeknight"] and d["fav_road"], base_pred=WK)
cell("weeknight home dog, favorite traveling on <=5 days rest", lambda d: d["weeknight"] and d["fav_road"] and d["orest"] is not None and d["orest"] <= 5, base_pred=WK)
cell("Saturday dog rested 2+ more than the favorite", lambda d: d["wd"] == "Sat" and None not in (d["rest"], d["orest"]) and d["rest"] - d["orest"] >= 2, base_pred=lambda d: d["wd"] == "Sat")

P("\n== STUDY 5: the OWN READ GAP (own read minus the no-vig price, points) on weeknight dogs ==")
for lo, hi in ((-100, 0), (0, 5), (5, 10), (10, 15), (15, 100)):
    cell(f"weeknight gap {lo}..{hi}", lambda d, lo=lo, hi=hi: d["weeknight"] and lo <= d["gap"] < hi, base_pred=WK)
for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 100)):
    cell(f"Saturday gap {lo}..{hi}", lambda d, lo=lo, hi=hi: d["wd"] == "Sat" and lo <= d["gap"] < hi, base_pred=lambda d: d["wd"] == "Sat")
for lo, hi in ((5, 10), (10, 15), (15, 100)):
    cell(f"weeknight gap {lo}..{hi}, ratings-backed (Elo gap 0+)", lambda d, lo=lo, hi=hi: d["weeknight"] and lo <= d["gap"] < hi and d["elo_gap"] >= 0, base_pred=WK)
for lo, hi in ((5, 10), (10, 15), (15, 100)):
    cell(f"weeknight gap {lo}..{hi} at the FIRST FAIR price (blind read)", lambda d, lo=lo, hi=hi: d["weeknight"] and lo <= d["early_gap"] < hi, price="early", base_pred=WK)
cell("weeknight gap 5+ HOME dog", lambda d: d["weeknight"] and d["gap"] >= 5 and d["side"] == "home", base_pred=WK)
cell("weeknight gap 5+ ROAD dog", lambda d: d["weeknight"] and d["gap"] >= 5 and d["side"] == "away", base_pred=WK)
cell("the NM St cell: weeknight home dog +100..+150, gap 5..10, off a loss", lambda d: d["weeknight"] and d["side"] == "home" and 100 <= d["close"] <= 150 and 5 <= d["gap"] < 10 and d["won_last"] is False, base_pred=WK)
P(f"\nCELLS: {CELLS} (expect ~{CELLS // 20} chance hits at z 2)")
open(os.path.join(os.path.dirname(__file__), "study.out"), "w").write("\n".join(out) + "\n")
