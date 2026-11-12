"""Shared table for the 11/12 FABLE study: 10 college hoops studies (results/studies/cbb10_1112/).
Read-only on the repo; the cache lives in ~/.cache/d503_cbb1112 (never the repo). No network, no odds API calls.
One row per finished game with BOTH sides' facts as they stood BEFORE tip (walk-forward, no look-ahead):
schedule facts 2016-26 (rest, road swings, the last game, cover margins, earlier meetings, conference standings) and
team-box facts 2021-26 (threes, free throws, fouls, turnovers, steals, pace, time led).
Seasons are start years (2025 = 2025-26). Prices: ESPN's close (ML, the spread and the total at their own juice)."""
import csv, glob, json, math, os, pickle, statistics
from collections import defaultdict
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_cbb1112")
os.makedirs(CACHE, exist_ok=True)
ANCH_POWER = {"Duke", "Kansas", "Kentucky", "Michigan", "Villanova"}
ANCH_MID = {"Gonzaga", "San Diego St", "Dayton", "Memphis", "Saint Mary's"}


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def season(start):
    y = int(start[:4])
    return y if int(start[5:7]) >= 7 else y - 1


def day(start):
    """The US calendar day of a tip."""
    return (datetime.fromisoformat(start.replace("Z", "+00:00")) - timedelta(hours=6)).date()


def profit(won, o):
    return (dec(o) - 1) if won else -1.0


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


def pair(s):
    try:
        a, b = str(s).split("-")[:2]
        return float(a), float(b)
    except (ValueError, AttributeError):
        return None


def load_games():
    gs = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data/sports/games/ncaab/*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["status"] != "final":
                continue
            hs, as_ = num(r["home_score"]), num(r["away_score"])
            if hs is None or as_ is None or hs == as_:
                continue
            gs[r["id"]] = r
            r["hs"], r["as"] = hs, as_
    return sorted(gs.values(), key=lambda r: (r["start"], r["id"]))


def conferences(gs):
    """{season: {team: (conf key, tier)}} from the Jan 3 - Mar 1 home / road schedule (membership = a known fact)."""
    names, by = {}, defaultdict(lambda: defaultdict(set))
    for r in gs:
        names[r["home"]], names[r["away"]] = r["home_name"], r["away_name"]
        md = r["start"][5:10]
        if r["stype"] != "2" or str(r["neutral"]) == "1" or not ("01-03" <= md <= "03-01"):
            continue
        s = season(r["start"])
        by[s][r["home"]].add(r["away"])
        by[s][r["away"]].add(r["home"])
    out = {}
    for s, adj in by.items():
        par = {t: t for t in adj}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for a in adj:
            for b in adj[a]:
                if a < b and len(adj[a] & adj[b]) >= 3:
                    par[find(a)] = find(b)
        comp = defaultdict(set)
        for t in adj:
            comp[find(t)].add(t)
        m = {}
        for k, mem in comp.items():
            nm = {names.get(t) for t in mem}
            if nm & ANCH_POWER or (s <= 2023 and "UCLA" in nm) or (s >= 2024 and "Arizona" in nm):
                tier = "power"
            elif nm & ANCH_MID:
                tier = "mid"
            else:
                tier = "low"
            if len(mem) < 5:
                continue
            for t in mem:
                m[t] = (k, tier)
        out[s] = m
    return out


BOXK = ("fga", "fgm", "tpa", "tpm", "fta", "ftm", "orb", "to", "stl", "blk", "pf", "paint", "fb", "poss")


def load_box():
    """{gid: {team: {fga, fgm, tpa, tpm, fta, ftm, orb, to, stl, blk, pf, lead, paint, fb, poss}}}"""
    files = [os.path.join(ROOT, "data/sports/teamstats/ncaab.jsonl")] + sorted(
        glob.glob(os.path.join(ROOT, "data/sports/teamstats/ncaab/*.jsonl")))
    out = {}
    for fn in files:
        if not os.path.exists(fn):
            continue
        for line in open(fn):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("gid") in out or not d.get("teams"):
                continue
            tm = {}
            for tid, t in d["teams"].items():
                fg = pair(t.get("fieldGoalsMade-fieldGoalsAttempted"))
                tp = pair(t.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
                ft = pair(t.get("freeThrowsMade-freeThrowsAttempted"))
                orb, to = num(t.get("offensiveRebounds")), num(t.get("totalTurnovers") or t.get("turnovers"))
                if not fg or not tp or not ft or orb is None or to is None or fg[1] < 20:
                    continue
                tm[str(tid)] = {"fga": fg[1], "fgm": fg[0], "tpa": tp[1], "tpm": tp[0], "fta": ft[1], "ftm": ft[0],
                                "orb": orb, "to": to, "stl": num(t.get("steals")) or 0.0,
                                "blk": num(t.get("blocks")) or 0.0, "pf": num(t.get("fouls")),
                                "lead": num(t.get("leadPercentage")), "paint": num(t.get("pointsInPaint")),
                                "fb": num(t.get("fastBreakPoints")), "poss": fg[1] - orb + to + 0.475 * ft[1]}
            if len(tm) == 2:
                out[d["gid"]] = tm
    return out


def halves(ls):
    try:
        v = [float(x) for x in str(ls).split(",") if x != ""]
        return v if len(v) >= 2 else None
    except ValueError:
        return None


def build():
    """[game rows] sorted by start; each: prices + g['H'] / g['A'] = that side's pre-tip facts."""
    p = os.path.join(CACHE, "table.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    gs = load_games()
    conf = conferences(gs)
    box = load_box()
    last_home = {}                    # the last regular-season home game (the schedule is public before the season)
    for r in gs:
        md = r["start"][5:10]
        if r["stype"] == "2" and str(r["neutral"]) != "1" and (md >= "11-01" or md <= "03-10"):
            last_home[(season(r["start"]), r["home"])] = r["id"]
    hist = defaultdict(list)          # (season, team) -> the games before
    meet = defaultdict(list)          # (season, pair) -> earlier meetings
    cst = defaultdict(lambda: [0, 0])  # (season, team) -> conference W-L
    rows = []
    for r in gs:
        s = season(r["start"])
        h, a = r["home"], r["away"]
        neutral = str(r["neutral"]) == "1"
        d = day(r["start"])
        cm = conf.get(s, {})
        same_conf = h in cm and a in cm and cm[h][0] == cm[a][0]
        mlh, mla = num(r["ml_home"]), num(r["ml_away"])
        sp, tot = num(r["spread_home"]), num(r["total"])
        b = box.get(r["id"])
        b = b if b and h in b and a in b else None
        g = {"id": r["id"], "start": r["start"], "season": s, "day": d, "home": h, "away": a, "hn": r["home_name"],
             "an": r["away_name"], "hs": r["hs"], "as": r["as"], "neutral": neutral, "stype": r["stype"],
             "mlh": mlh if mlh else None, "mla": mla if mla else None, "oh": num(r["ml_home_open"]),
             "oa": num(r["ml_away_open"]), "sp": sp, "spho": num(r["spread_home_odds"]),
             "spao": num(r["spread_away_odds"]), "total": tot, "ovo": num(r["over_odds"]), "uno": num(r["under_odds"]),
             "elev": num(r.get("elev")), "lsh": halves(r.get("ls_home")), "lsa": halves(r.get("ls_away")),
             "conf": same_conf, "poss": (b[h]["poss"] + b[a]["poss"]) / 2 if b else None,
             "last_home": last_home.get((s, h)) == r["id"]}
        for side, t in (("H", h), ("A", a)):
            H = hist[(s, t)]
            f = {"n": len(H), "tier": cm.get(t, (None, None))[1], "ck": cm.get(t, (None, None))[0], "cw": cst[(s, t)][0], "cl": cst[(s, t)][1]}
            if H:
                L = H[-1]
                f["rest"] = (d - L["day"]).days
                f["last"] = L
                k = 0
                for x in reversed(H):
                    if x["ven"] != "A":
                        break
                    k += 1
                f["road_run"] = k
                f["road7"] = sum(1 for x in H if x["ven"] == "A" and (d - x["day"]).days <= 7)
                f["g7"] = sum(1 for x in H if (d - x["day"]).days <= 7)
                f["w"] = sum(1 for x in H if x["won"])
                cms = [x["cm"] for x in H if x["cm"] is not None]
                f["cm"], f["cmn"] = (sum(cms) / len(cms) if cms else None), len(cms)
                tms = [x["tm"] for x in H if x["tm"] is not None]
                f["tm"], f["tmn"] = (sum(tms) / len(tms) if tms else None), len(tms)
                bx = [x for x in H if x["b"]]
                if bx:
                    n = len(bx)
                    S = {k2: sum(x["b"][0][k2] or 0 for x in bx) for k2 in BOXK}
                    O = {k2: sum(x["b"][1][k2] or 0 for x in bx) for k2 in BOXK}
                    ln = [x for x in bx if x["b"][0]["lead"] is not None]
                    f["bx"] = {"n": n, "tpr": S["tpa"] / S["fga"], "tp": S["tpm"] / max(S["tpa"], 1),
                               "ftp": S["ftm"] / max(S["fta"], 1), "fta": S["fta"] / n, "ftr": S["fta"] / S["fga"],
                               "o_ftr": O["fta"] / O["fga"], "o_fta": O["fta"] / n, "o_tpr": O["tpa"] / O["fga"],
                               "pf": S["pf"] / n, "o_pf": O["pf"] / n, "tor": S["to"] / S["poss"],
                               "o_tor": O["to"] / O["poss"], "stl": S["stl"] / O["poss"], "o_stl": O["stl"] / S["poss"],
                               "pace": (S["poss"] + O["poss"]) / (2 * n),
                               "lead": sum(x["b"][0]["lead"] for x in ln) / len(ln) if ln else None, "leadn": len(ln),
                               "leadw": sum(1 for x in ln if x["won"]) / len(ln) if ln else None,
                               "leadm": sum(x["m"] for x in ln) / len(ln) if ln else None,
                               "ppp": sum(x["pf_"] for x in bx) / S["poss"], "o_ppp": sum(x["pa_"] for x in bx) / O["poss"],
                               "paint": S["paint"] / n, "blk": S["blk"] / n}
            g[side] = f
        g["meet"] = list(meet[(s, frozenset((h, a)))])
        rows.append(g)
        # ---- after the game: update the histories ----
        m = r["hs"] - r["as"]
        pts = r["hs"] + r["as"]
        for t, o, ven, mt, ml, spx in ((h, a, "N" if neutral else "H", m, mlh, sp),
                                       (a, h, "N" if neutral else "A", -m, mla, -sp if sp is not None else None)):
            hist[(s, t)].append({"day": d, "ven": ven, "won": mt > 0, "m": mt, "ml": ml if ml else None, "sp": spx,
                                 "cm": (mt + spx) if spx is not None else None,
                                 "tm": (pts - tot) if tot is not None else None, "opp": o, "conf": same_conf,
                                 "id": r["id"], "pf_": r["hs"] if t == h else r["as"],
                                 "pa_": r["as"] if t == h else r["hs"], "b": (b[t], b[o]) if b else None})
        if same_conf and r["stype"] == "2":
            cst[(s, h)][0 if m > 0 else 1] += 1
            cst[(s, a)][1 if m > 0 else 0] += 1
        meet[(s, frozenset((h, a)))].append({"home": h, "m": m, "pts": pts, "total": tot, "sp": sp, "day": d,
                                             "neutral": neutral, "poss": g["poss"]})
    pickle.dump(rows, open(p, "wb"))
    return rows


# ---------------- bets ----------------
def ml_p(g, side):
    o = g["mlh"] if side == "H" else g["mla"]
    if o is None:
        return None
    return profit((g["hs"] > g["as"]) == (side == "H"), o)


def ml_open_p(g, side):
    o = g["oh"] if side == "H" else g["oa"]
    if not o:
        return None
    return profit((g["hs"] > g["as"]) == (side == "H"), o)


def ats_p(g, side):
    if g["sp"] is None:
        return None
    r = g["hs"] - g["as"] + g["sp"]
    if side == "A":
        r = -r
    if r == 0:
        return None
    return profit(r > 0, (g["spho"] if side == "H" else g["spao"]) or -110)


def tot_p(g, over):
    if g["total"] is None:
        return None
    pts = g["hs"] + g["as"]
    if pts == g["total"]:
        return None
    return profit((pts > g["total"]) == over, (g["ovo"] if over else g["uno"]) or -110)


def odds(g, side):
    return g["mlh"] if side == "H" else g["mla"]


def spread(g, side):
    if g["sp"] is None:
        return None
    return g["sp"] if side == "H" else -g["sp"]


def both(g, need_box=0):
    """[(side, my facts, their facts)] for both sides; need_box = both teams that many box games."""
    if need_box and not all("bx" in g[x] and g[x]["bx"]["n"] >= need_box for x in "HA"):
        return []
    return [("H", g["H"], g["A"]), ("A", g["A"], g["H"])]


def band(o):
    if o is None:
        return None
    if 100 <= o <= 350:
        return "dog"
    if -150 <= o <= -101:
        return "sfav"
    if -400 <= o < -150:
        return "bfav"
    return None


def other(side):
    return "A" if side == "H" else "H"


def ven(g, side):
    return "N" if g["neutral"] else side


def stats(ps):
    if not ps:
        return None
    n = len(ps)
    m = sum(ps) / n
    sdv = statistics.pstdev(ps) if n > 1 else 1.0
    return {"n": n, "roi": m, "z": (m / (sdv / math.sqrt(n))) if sdv else 0.0,
            "win": sum(1 for x in ps if x > 0) / n}


class Cells:
    """cells[name] -> [(season, profit)]. TRAIN / HELD by season; every cell is counted (the multiple-testing note)."""
    def __init__(self, tag, train, held):
        self.c, self.tag, self.train, self.held, self.lines = defaultdict(list), tag, train, held, []

    def add(self, k, g, p):
        if p is not None:
            self.c[k].append((g["season"], p))

    def p(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.lines.append(s)

    def line(self, k):
        v = self.c.get(k)
        if not v:
            return f"{k:64s} -"
        by = defaultdict(list)
        for s, p in v:
            by[s].append(p)
        A = stats([p for _, p in v])
        T = stats([p for s, p in v if self.train[0] <= s <= self.train[1]])
        Hh = stats([p for s, p in v if s in self.held])
        tu = sum(1 for s in by if self.train[0] <= s <= self.train[1] and sum(by[s]) > 0)
        tn = sum(1 for s in by if self.train[0] <= s <= self.train[1])
        hu = sum(1 for s in by if s in self.held and sum(by[s]) > 0)
        hn = sum(1 for s in by if s in self.held)

        def f(x):
            return f"{x['roi']*100:+6.1f}% n{x['n']:<5d}" if x else "   -          "
        ys = " ".join(f"{str(s)[2:]}:{sum(by[s])/len(by[s])*100:+.0f}" for s in sorted(by))
        return (f"{k:64s} ALL {f(A)} w{A['win']*100:4.1f} z{A['z']:+5.2f} | TR {f(T)} {tu}/{tn} up | HELD {f(Hh)} "
                f"{hu}/{hn} up z{(Hh['z'] if Hh else 0):+5.2f} | {ys}")

    def dump(self, minn=0):
        for k in sorted(self.c):
            if len(self.c[k]) >= minn:
                self.p(self.line(k))
        self.p(f"CELLS: {len(self.c)}")
        open(os.path.join(OUT, self.tag + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def placebo(bets, base, n=2000, seed=7):
    """How many of n random draws of len(bets) from `base` land as far from the base mean as `bets` does."""
    import random
    rnd = random.Random(seed)
    m = sum(bets) / len(bets)
    bm = sum(base) / len(base)
    k = 0
    for _ in range(n):
        s = rnd.sample(base, len(bets)) if len(bets) <= len(base) else [rnd.choice(base) for _ in bets]
        if abs(sum(s) / len(s) - bm) >= abs(m - bm):
            k += 1
    return k
