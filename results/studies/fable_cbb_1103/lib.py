"""11/3 FABLE - COLLEGE HOOPS SECOND OPINION: the shared table (read-only on the repo; the cache lands in
~/.cache/d503_studies, never the repo).

Starts from the 11/3 (B) side table (results/studies/cbb_1103_b/lib.py - one row per team side of every college hoops
game 2016-27 at ESPN's close, the 2023-25 ML open, conferences inferred from the schedule) and adds, with NO look-ahead
(everything from the team's EARLIER games this season, or last season's finished table):
  - the calendar: this game's weekday and the last game's (ET nights), the slate size (priced games that night)
  - luck: the record in close games (3 / 5 points), win % minus the margin-implied win % (a normal on the average margin)
  - variance: the spread of the team's margins and of its cover margins (margin + its spread) so far
  - halves: first-half / second-half margins (ls_home / ls_away) - the second-half team
  - the market's running error on the team: mean (margin + spread) this season so far, and last season's
  - style from the ESPN box scores 2021-26 (data/sports/roster/ncaab_<season>.csv.gz - minutes, points, FGM-FGA,
    rebounds, assists only; no threes / free throws / turnovers on file): pace (both teams' FGA a game), FG% for /
    against, rebound margin, assist share, bench points share, the top-5 minutes share (rotation tightness)
TRAIN 2018-22, HELD OUT 2023 / 2024 / 2025 apart (box features 2022 train only - the box starts 2021)."""
import csv, glob, gzip, json, math, os, pickle, statistics, sys
from collections import defaultdict, Counter

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("cbb_b_lib", os.path.join(ROOT, "results/studies/cbb_1103_b/lib.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

CACHE = B.CACHE
TRAIN, HELD, NOW = B.TRAIN, B.HELD, B.NOW
dec, num, st, cell, fmt, regular, dogs, favs, spreads = B.dec, B.num, B.st, B.cell, B.fmt, B.regular, B.dogs, B.favs, B.spreads
profit_ml, profit_ats, profit_open = B.profit_ml, B.profit_ats, B.profit_open


class Out(B.Out):
    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")



def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def halves():
    """{game id: (home 1H, away 1H)} from the line scores."""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data/sports/games/ncaab/*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["status"] != "final" or not r.get("ls_home") or not r.get("ls_away"):
                continue
            try:
                h = [float(v) for v in r["ls_home"].split(",")]
                a = [float(v) for v in r["ls_away"].split(",")]
            except ValueError:
                continue
            if len(h) < 2 or len(a) < 2:
                continue
            out[r["id"]] = (h[0], a[0])
    return out


def box():
    """{(game id, team id): {fga, fgm, pts, reb, ast, top5, bench, n}} from the ESPN box scores."""
    pk = os.path.join(CACHE, "fable_cbb_box.pkl")
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data/sports/roster/ncaab_*.csv.gz"))):
        with gzip.open(f, "rt") as fh:
            for r in csv.DictReader(fh):
                try:
                    s = json.loads(r["stats"])
                    mins = float(s.get("minutes") or 0)
                    pts = float(s.get("points") or 0)
                    fg = s.get("fieldGoalsMade-fieldGoalsAttempted") or "0-0"
                    fgm, fga = (float(v) for v in fg.split("-"))
                    reb = float(s.get("rebounds") or 0)
                    ast = float(s.get("assists") or 0)
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
                k = (r["gid"], r["team"])
                d = out.setdefault(k, {"fga": 0, "fgm": 0, "pts": 0, "reb": 0, "ast": 0, "mins": [], "spts": 0, "n": 0})
                d["fga"] += fga
                d["fgm"] += fgm
                d["pts"] += pts
                d["reb"] += reb
                d["ast"] += ast
                d["n"] += 1
                d["mins"].append(mins)
                if r.get("starter") == "1":
                    d["spts"] += pts
    for d in out.values():
        m = sorted(d["mins"], reverse=True)
        tot = sum(m) or 1
        d["top5"] = sum(m[:5]) / tot
        d["bench"] = (d["pts"] - d["spts"]) / d["pts"] if d["pts"] else None
        del d["mins"]
    pickle.dump(out, open(pk, "wb"))
    return out


def _mean(v):
    return sum(v) / len(v) if v else None


def _sd(v):
    return statistics.pstdev(v) if len(v) > 1 else None


def build():
    pk = os.path.join(CACHE, "fable_cbb_rows.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    rows = B.build()
    hv = halves()
    bx = box()
    slate = Counter()
    for x in rows:
        if x["side"] == "home" and x.get("ml") is not None:
            slate[(x["season"], x["night"])] += 1
    H = defaultdict(list)             # (season, team) -> per-game dicts, in order
    last_resid = {}                   # (season, team) -> mean cover margin that season (set when the season is done)
    season_resid = defaultdict(list)
    for x in rows:
        s, t = x["season"], x["team"]
        h = H[(s, t)]
        x["dow"] = (x["night"] + 3) % 7                      # 0 = Monday ... 5 = Saturday, 6 = Sunday (ET nights)
        x["ldow"] = (h[-1]["night"] + 3) % 7 if h else None
        x["slate"] = slate[(s, x["night"])]
        m = [g["margin"] for g in h]
        x["n_prev"] = len(m)
        if len(m) >= 5:
            x["cw3"] = sum(1 for v in m if 0 < v <= 3)
            x["cl3"] = sum(1 for v in m if -3 <= v < 0)
            x["cw5"] = sum(1 for v in m if 0 < v <= 5)
            x["cl5"] = sum(1 for v in m if -5 <= v < 0)
            x["cnet5"] = x["cw5"] - x["cl5"]
            x["cnet3"] = x["cw3"] - x["cl3"]
            am = _mean(m)
            x["avg_m"] = am
            x["luck"] = (sum(1 for v in m if v > 0) / len(m)) - ncdf(am / 11.0)
            x["m_sd"] = _sd(m)
            cm = [g["cm"] for g in h if g.get("cm") is not None]
            if len(cm) >= 5:
                x["cm_sd"] = _sd(cm)
                x["cm_mean"] = _mean(cm)
                x["n_cm"] = len(cm)
            hm = [(g["h2m"] - g["h1m"]) for g in h if g.get("h1m") is not None]
            if len(hm) >= 5:
                x["h2_gain"] = _mean(hm)                         # 2nd-half margin minus 1st-half margin, on average
                x["h1_avg"] = _mean([g["h1m"] for g in h if g.get("h1m") is not None])
            bb = [g["box"] for g in h if g.get("box")]
            if len(bb) >= 5:
                x["pace"] = _mean([b["pace"] for b in bb])
                x["fgp"] = _mean([b["fgp"] for b in bb])
                x["ofgp"] = _mean([b["ofgp"] for b in bb])
                x["rebm"] = _mean([b["rebm"] for b in bb])
                x["astr"] = _mean([b["astr"] for b in bb])
                x["bench"] = _mean([b["bench"] for b in bb if b["bench"] is not None] or [0])
                x["top5"] = _mean([b["top5"] for b in bb])
                x["fga_own"] = _mean([b["fga"] for b in bb])
        x["lresid"] = last_resid.get((s - 1, t))
        # this game's own box (stored on history after the game; never a feature of this row)
        b = bx.get((x["id"], x["team"]))
        ob = bx.get((x["id"], x["opp"]))
        g = {"night": x["night"], "margin": x["margin"], "cm": (x["margin"] + x["sp"]) if x.get("sp") is not None else None}
        hv1 = hv.get(x["id"])
        if hv1:
            h1 = (hv1[0] - hv1[1]) if x["side"] == "home" else (hv1[1] - hv1[0])
            g["h1m"], g["h2m"] = h1, x["margin"] - h1
            x["h1m_now"] = h1
        if b and ob and b["fga"] >= 30 and ob["fga"] >= 30:
            g["box"] = {"pace": b["fga"] + ob["fga"], "fgp": b["fgm"] / b["fga"], "ofgp": ob["fgm"] / ob["fga"],
                        "rebm": b["reb"] - ob["reb"], "astr": b["ast"] / b["fgm"] if b["fgm"] else 0,
                        "bench": b["bench"], "top5": b["top5"], "fga": b["fga"]}
        h.append(g)
        if g["cm"] is not None:
            season_resid[(s, t)].append(g["cm"])
    for k, v in season_resid.items():
        if len(v) >= 10:
            last_resid[k] = _mean(v)
    for x in rows:                                            # fill lresid now that every season's mean is known
        x["lresid"] = last_resid.get((x["season"] - 1, x["team"]))
        x["olresid"] = last_resid.get((x["season"] - 1, x["opp"]))
    # the opponent's features on the same row (pair rows sit next to each other)
    by_id = {}
    for i, x in enumerate(rows):
        by_id[(x["id"], x["team"])] = i
    OPP = ("cnet5", "cnet3", "luck", "m_sd", "cm_sd", "cm_mean", "h2_gain", "pace", "fgp", "ofgp", "rebm", "astr", "bench",
           "top5", "n_prev", "ldow", "fga_own", "avg_m")
    for x in rows:
        j = by_id.get((x["id"], x["opp"]))
        if j is None:
            continue
        o = rows[j]
        for k in OPP:
            if k in o:
                x["o_" + k] = o[k]
    pickle.dump(rows, open(pk, "wb"))
    return rows


def q(v, cuts):
    """which bucket a value falls in (cuts ascending) - None stays None."""
    if v is None:
        return None
    for i, c in enumerate(cuts):
        if v < c:
            return i
    return len(cuts)
