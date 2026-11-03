"""11/3 - FABLE: COLLEGE HOOPS KNOWLEDGE (B) - the shared table for the five studies (read-only on the repo; the cache
lands in $STUDY_CACHE or ~/.cache/d503_studies, never the repo).

Starts from the 11/3 FABLE side table (results/studies/fable_cbb_1103/lib.py = the 11/3 (B) table + box-score style,
luck, the market's running error) and adds, with NO look-ahead:
  - the engine's OLD college hoops read on every game (deep_old_read.pkl - the margin Elo + features blended with the
    market by the learned trust and pulled to the market by early_trust; sports_model with today's ncaab params)
  - the efficiency model's chance (deep_final.pkl, the 11/3 DEEP walk-forward model; P(home) = sigmoid(-0.001 + 0.1537 mh))
  - the TOP SCORER MISSED THE LAST GAME flag from the ESPN box scores (deep_cbb_box.pkl - 2021-26), the 11/3 DEEP rule:
    the leader in points a game so far (3+ games, 20+ minutes a game, the team 3+ box games in) not in the last box
  - this season's close-win count in the last 5 (sports_form's cw5), 'ice cold' (sports_early._fades), the last
    margins, the month in the US night, the line move open -> close (2023-25 only)
  - the engine's college hoops WEIGHTS replayed (sports.dog_spots / dog_score for a dog, weigh_favorites +
    weigh_ncaab_away_fav / weigh_ncaab_eff_fav / weigh_ncaab_top_out for a favorite) -> dog_pts, dog_read, fav_read
TRAIN 2018-22, HELD OUT 2023 / 2024 / 2025 apart (box-score cuts 2021-22 train)."""
import importlib.util
import math
import os
import pickle
from collections import defaultdict
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
_spec = importlib.util.spec_from_file_location("fable_cbb_lib", os.path.join(ROOT, "results/studies/fable_cbb_1103/lib.py"))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
B = F.B
CACHE = B.CACHE
TRAIN, HELD = B.TRAIN, B.HELD
dec, num, st, cell, fmt, regular, dogs, favs, spreads = (B.dec, B.num, B.st, B.cell, B.fmt, B.regular, B.dogs, B.favs,
                                                          B.spreads)
profit_ml, profit_ats, profit_open = B.profit_ml, B.profit_ats, B.profit_open

# the engine's college hoops constants (sports.py, 11/3) - copied, not imported (the study never loads the engine)
STUDY_CAP, FAV_CAP, FAV_PER_PT, OWN_CAP = 6, 0.04, 0.005, 12
AWAY_FAV_W, EFF_FAV_W, EFF_FAV_GAP, TOP_OUT_FAV_W = -0.03, -0.03, 0.03, -0.02
RANKED_ROAD_DOG, REB_GAP, REB_GAP_BIG, REB_DOG, ATS_GAP = 2, 6.0, 8.0, (1, 2), 3.0
ND = ("11", "12")


class Out(B.Out):
    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def sig(z):
    return 1 / (1 + math.exp(-z))


def top_out_flags(rows):
    """{(game id, team): top scorer missed the last game} from the box scores, the 11/3 DEEP rule."""
    box, _, _ = pickle.load(open(os.path.join(CACHE, "deep_cbb_box.pkl"), "rb"))
    order = defaultdict(list)
    for x in rows:
        if x["season"] >= 2021:
            order[(x["season"], x["team"])].append(x)
    out = {}
    for (s, t), xs in order.items():
        xs.sort(key=lambda x: (x["start"], x["id"]))
        hist = []                                       # earlier box scores this season (regular season + postseason)
        for x in xs:
            if len(hist) >= 3:
                gp = defaultdict(lambda: [0, 0.0, 0.0])
                for hb in hist:
                    for pid, (m, pts, *_r) in hb.items():
                        if m > 0:
                            g = gp[pid]
                            g[0] += 1
                            g[1] += pts or 0
                            g[2] += m
                cand = sorted(((g[1] / g[0], pid) for pid, g in gp.items() if g[0] >= 3 and g[2] / g[0] >= 20), reverse=True)
                if cand:
                    top = cand[0][1]
                    lastb = hist[-1]
                    out[(x["id"], t)] = top not in lastb or lastb[top][0] <= 0
            b = (box.get(x["id"]) or {}).get(t)
            if b:
                hist.append(b)
    return out


def build():
    pk = os.path.join(CACHE, "cbb_knowledge_b_rows.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    rows = F.build()
    old = pickle.load(open(os.path.join(CACHE, "deep_old_read.pkl"), "rb"))
    eff = pickle.load(open(os.path.join(CACHE, "deep_final.pkl"), "rb"))
    top = top_out_flags(rows)
    hist = defaultdict(list)                              # (season, team) -> margins so far, with close-win flags
    for x in rows:
        s, t = x["season"], x["team"]
        h = hist[(s, t)]
        try:
            x["month"] = (datetime.fromisoformat(x["start"].replace("Z", "+00:00")) - timedelta(hours=5)).strftime("%m")
        except ValueError:
            x["month"] = None
        x["nd"] = x["month"] in ND
        o = old.get(x["id"])
        if o and o[0] is not None:
            x["own"] = o[0] if x["side"] == "home" else 1 - o[0]
            x["raw"] = o[1] if x["side"] == "home" else 1 - o[1]
            x["em"] = o[2] if x["side"] == "home" else (-o[2] if o[2] is not None else None)
        e = eff.get(x["id"])
        if e and e.get("mh") is not None:
            ph = sig(-0.001 + 0.1537 * float(e["mh"]))
            x["eff"] = ph if x["side"] == "home" else 1 - ph
            x["eff_m"] = float(e["mh"]) if x["side"] == "home" else -float(e["mh"])
        x["top_out"] = top.get((x["id"], t))
        x["o_top_out"] = top.get((x["id"], x["opp"]))
        q = h[-5:]
        x["cw5"] = sum(1 for m, cw in q if cw) if q else 0
        ms = [m for m, _ in h]
        x["ice_cold"] = len(ms) >= 5 and sum(ms[-3:]) / 3 - sum(ms) / len(ms) <= -7
        x["last_m"] = x["last"]["margin"] if x.get("last") else None
        x["olast_m"] = x["olast"]["margin"] if x.get("olast") else None
        x["last_won"] = x["last"]["won"] if x.get("last") else None
        x["olast_won"] = x["olast"]["won"] if x.get("olast") else None
        x["move"] = (x["p"] - x["po"]) if x.get("p") is not None and x.get("po") is not None else None
        pm = x.get("prev_meet") or []
        x["rubber"] = len(pm) == 2 and (pm[0]["margin"] > 0) != (pm[1]["margin"] > 0)
        h.append((x["margin"], x["won"] and x["margin"] <= 3))   # (overtime isn't on the row - a 3-point win = close)
    # the opponent's new fields on the row
    by = {(x["id"], x["team"]): i for i, x in enumerate(rows)}
    for x in rows:
        j = by.get((x["id"], x["opp"]))
        if j is None:
            continue
        o = rows[j]
        x["o_ice_cold"], x["o_cw5"], x["o_rubber"] = o["ice_cold"], o["cw5"], o["rubber"]
        x["o_miles"], x["o_trip"], x["o_streak"] = o.get("miles"), o.get("trip"), o.get("streak")
        x["o_n_cm"] = o.get("n_cm")
        x["o_next_i"] = o.get("next_i")
    for x in rows:
        dog_pts(x)
        fav_read(x)
    pickle.dump(rows, open(pk, "wb"))
    return rows


def reb_gap(x):
    return (x["rebm"] - x["o_rebm"]) if x.get("rebm") is not None and x.get("o_rebm") is not None else None


def ats_gap(x):
    if x.get("cm_mean") is None or x.get("o_cm_mean") is None or (x.get("n_cm") or 0) < 10 or (x.get("o_n_cm") or 0) < 10:
        return None
    return x["cm_mean"] - x["o_cm_mean"]


def dog_pts(x):
    """sports.dog_spots for a college hoops dog side, replayed from the row (the 11/3 weights in). Sets x['dog_pts']
    (capped at STUDY_CAP like dog_score) and x['dog_read'] = the market + the dog score / 100 (the gated dog's read)."""
    if x.get("ml") is None or x["ml"] < 100:
        return None
    sc = 0.0
    if x.get("olast_won") is False:
        sc += 2
    elif x.get("last_won") is False and x.get("olast_won") is True:
        sc -= 3
    if (x.get("cw5") or 0) >= 2:
        sc -= 1
    if x.get("rubber"):
        sc -= 2
    if (x.get("streak") or 0) <= -5:
        sc -= 2
    if x.get("top_out"):
        sc -= 2
    road = x["venue"] == "away"
    if x.get("rank25") and road and x["nd"]:
        sc -= RANKED_ROAD_DOG
    elif x.get("orank25") and x["venue"] == "home" and x["nd"]:
        sc += RANKED_ROAD_DOG
    rg = reb_gap(x)
    if rg is not None:
        sc += REB_DOG[1] if rg >= REB_GAP_BIG else REB_DOG[0] if rg >= REB_GAP else -REB_DOG[0] if rg <= -REB_GAP else 0
    if road and x["gn"] <= 3:
        sc -= 2
    if x.get("ice_cold"):
        sc -= 3
    x["dog_pts_raw"] = sc
    x["dog_pts"] = max(-STUDY_CAP, min(STUDY_CAP, sc))
    if x.get("own") is not None:
        base = min(OWN_CAP, (x["own"] - x["p"]) * 100)
        x["dog_score"] = base + x["dog_pts"]
        x["dog_read"] = min(0.95, x["p"] + x["dog_score"] / 100)
    return x["dog_pts"]


def fav_read(x):
    """The favorite's WEIGHED read (sports.weigh_favorites + the three 11/3 college hoops favorite weights) from the
    row: x['fav_read'] (None when the engine has no own read on it), x['fav_w'] = the weights that fired."""
    if x.get("ml") is None or x["ml"] >= 0 or x.get("own") is None:
        return None
    own = x["own"]
    w = {}
    # the dog across: its study points move the favorite the other way (half a point per point, capped)
    pts = _opp_pts(x)
    if pts:
        w["opp_dog_pts"] = max(-FAV_CAP, min(FAV_CAP, -FAV_PER_PT * pts))
    r = own + w.get("opp_dog_pts", 0.0)
    if -150 <= x["ml"] <= -101 and x["venue"] != "home" and x["nd"]:
        w["away_nd"] = AWAY_FAV_W
        r = max(own - FAV_CAP, r + AWAY_FAV_W)
    if -150 <= x["ml"] <= -101 and x.get("eff") is not None and x["eff"] - x["p"] <= -EFF_FAV_GAP:
        w["eff_under"] = EFF_FAV_W
        r = max(own - FAV_CAP, r + EFF_FAV_W)
    if -250 <= x["ml"] <= -101 and x.get("top_out"):
        w["top_out"] = TOP_OUT_FAV_W
        r = max(own - FAV_CAP, r + TOP_OUT_FAV_W)
    x["fav_w"] = w
    x["fav_read"] = min(0.95, max(0.05, r))
    return x["fav_read"]


def _opp_pts(x):
    """dog_spots for the DOG across this favorite (its facts are the mirror of ours)."""
    o = {"ml": -x["ml"], "olast_won": x.get("last_won"), "last_won": x.get("olast_won"), "cw5": x.get("o_cw5"),
         "rubber": x.get("o_rubber"), "streak": x.get("o_streak"), "top_out": x.get("o_top_out"),
         "venue": {"home": "away", "away": "home"}.get(x["venue"], "neutral"), "nd": x["nd"],
         "rank25": x.get("orank25"), "orank25": x.get("rank25"), "rebm": x.get("o_rebm"), "o_rebm": x.get("rebm"),
         "gn": x.get("ogn") or 99, "ice_cold": x.get("o_ice_cold"), "p": None, "own": None}
    o["venue"] = o["venue"] if x["venue"] != "neutral" else "neutral"
    return dog_pts(o)


def tier_of(x):
    """The game's tier the way the DEEP / FABLE studies read it: P = a power team in it, M = the best team mid, L = low."""
    t = {x.get("tier"), x.get("otier")}
    return "P" if "power" in t else "M" if "mid" in t else "L"


def band(ml):
    if ml is None:
        return None
    if ml < 0:
        return "-101..-150" if ml >= -150 else "-151..-250" if ml >= -250 else "-251 and up"
    return "+100..+150" if ml <= 150 else "+151..+250" if ml <= 250 else "+251..+350" if ml <= 350 else "+351 and up"


def phase(x):
    m = x.get("month")
    return "Nov" if m == "11" else "Dec" if m == "12" else "Jan" if m == "01" else "Feb" if m == "02" else "Mar" if m == "03" else None


def zstr(o):
    return f"{o['roi'] * 100:+.1f}% n{o['n']} z{o['z']:+.1f}" if o else "-"


def cuts(o, name, rows, fn, labels, prof=None):
    """One cell per bucket of fn(x) (None = skipped), in the order of labels; prof = the profit function."""
    out = {}
    byb = defaultdict(list)
    for x in rows:
        b = fn(x)
        if b is not None:
            byb[b].append(x)
    for lab in labels:
        if byb.get(lab):
            out[lab] = o.c(f"{name} | {lab}", byb[lab], prof or profit_ml)
    return out


def win_vs_price(rows):
    """(won %, the no-vig price's %, n) - did these sides win more or less often than the close said?"""
    if not rows:
        return None
    n = len(rows)
    return sum(x["won"] for x in rows) / n, sum(x["p"] for x in rows) / n, n


def bk(v, edges):
    """A bucket label for v on ascending edges: '<e0', 'e0..e1', ..., 'e(n-1)+'."""
    if v is None:
        return None
    if v < edges[0]:
        return f"<{edges[0]}"
    for a, b in zip(edges, edges[1:]):
        if a <= v < b:
            return f"{a}..{b}"
    return f"{edges[-1]}+"


def bk_labels(edges):
    return [f"<{edges[0]}"] + [f"{a}..{b}" for a, b in zip(edges, edges[1:])] + [f"{edges[-1]}+"]
