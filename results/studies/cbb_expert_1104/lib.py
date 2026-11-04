"""11/4 FABLE: COLLEGE HOOPS EXPERT KNOWLEDGE - the shared table (read-only on the repo; caches in ~/.cache/d503_studies).

One row per team side of every college hoops game 2016-27 (the 11/3 (B) table - results/studies/cbb_1103_b/lib.py:
prices, Elo, conference / tier, streaks, rest, game numbers) plus, from the box scores 2021-26 (the full TEAM box in
data/sports/teamstats and every PLAYER line in data/sports/roster), everything below - built in start order with NO
look-ahead (every field is what was on file before tip):

  SHOOTING (team box, this season before tonight): efg_s / efg5 / efg3 (effective FG% season / last 5 / last 3),
      tp_s / tp5 (3P%), ft_s / ft5 (FT%), two_s / two5 (2P% - the rim / shot-quality half), ftr_s / ftr5 (FTA per FGA),
      tpr_s (3PA per FGA), adj5 (last-5 eFG minus the eFG each opponent was allowing at the time - shooting over the
      defenses faced), defg_s (eFG allowed season to date), box_n (team box games so far)
  TURMOIL (player box): vanished (regulars - 15+ min a game over 5+ games - with 0 minutes in the last 3+ games),
      lost3w (those whose last appearance was within the last 21 days - a team that LOST rotation men lately),
      fresh_abs (regulars who played 2 games ago and sat the last game), churn (share of the last game's minutes
      by men outside the season's top 7), starters_used5 (distinct starters over the last 5 games)
  STARS (player box): top_fga (the top scorer's share of the team's FGA this season), star_gap (his points a game minus
      the 2nd man's), top_out (he missed the last game - the 11/3 DEEP weight, recomputed here), opp_top_out, back2
      (he missed 2+ games, played the last one - tonight is his 2nd game back; pre-tip), back1 (EX POST: he plays tonight
      after missing 2+ - only the news could flag it), opp_back2, opp_long_out (the opponent has a regular out 4+)
  ROAD / HOME (the games file): road_w / road_l / road_cm (this season's true-road record and average cover margin
      there), home_cm, away_cm, home_edge (home_cm - away_cm, 3+ each), nhome / naway, ohome_cm (the opponent's home
      cover margin so far) ... everything per team-season, before tonight
  MOMENTUM (the games file + Elo): cm5 (average cover margin, last 5 priced games), adjm5 (margin minus the Elo-
      expected margin, last 5), adjm_prev (the same over the games before those 5), improve (adjm5 - adjm_prev),
      beat_good (won the last game vs an Elo top-25 team), lost_to_good, opp_beat_good, big_win (won last by 15+),
      upset_last (won the last game as a +150 or longer dog)
Prices: ESPN's close 2018-26, ESPN's ML open 2023-25 (the second check). Box-based cells: TRAIN 2021-22, HELD 2023 /
2024 / 2025 apart; price / schedule cells: TRAIN 2018-22, the same held-out seasons."""
import importlib.util, math, os, pickle, statistics, sys
from collections import defaultdict, Counter

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _load("cbb_b_lib", "results/studies/cbb_1103_b/lib.py")
A = _load("cbb_a_lib", "results/studies/cbb_knowledge_a/lib.py")
CACHE = B.CACHE
HELD = (2023, 2024, 2025)
TRAIN_PRICE = (2018, 2022)
TRAIN_BOX = (2021, 2022)
dec, nv = B.dec, B.nv
profit_ml, profit_ats, profit_open = B.profit_ml, B.profit_ats, B.profit_open
dogs, favs, spreads = B.dogs, B.favs, B.spreads
REG_MPG, REG_MIN_G = 15, 5
TOP_MPG, TOP_MIN_G = 20, 3
ELO_PT = 28.0            # Elo points per point of margin (the (B) table's K / scale - a rough expected margin)
ELO_HADV = 75


def _sd(v):
    return statistics.pstdev(v) if len(v) > 1 else 1.0


def _mean(v):
    return sum(v) / len(v) if v else None


def build():
    pk = os.path.join(CACHE, "cbb_expert_1104_rows.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    rows = B.build()
    tb = A.teambox()
    pb = A.playerbox()
    # ---- per (season, team) running state ----
    sh = defaultdict(list)       # team box lines: dict(efg, tp, ft, two, ftr, tpr, defg_opp, fgm, fga, tpm, tpa, ftm, fta, allowed-line)
    sh_def = defaultdict(lambda: [0.0, 0.0, 0.0])   # season defense: opp fgm, tpm, fga allowed
    pl = defaultdict(list)       # (season, team) -> [(night, gid, {pid: (min, pts, fga, starter, name)})]
    rec = defaultdict(lambda: {"road": [0, 0, []], "home": [0, 0, []], "away_cm": [], "hist": []})
    # rows come in pairs (home then away) in start order
    i = 0
    n = len(rows)
    while i < n:
        a = rows[i]
        pair = [a]
        if i + 1 < n and rows[i + 1]["id"] == a["id"]:
            pair.append(rows[i + 1])
        i += len(pair)
        s = a["season"]
        gid = a["id"]
        box = tb.get(gid) or {}
        pbox = pb.get(gid) or {}
        for x in pair:
            t, ot = x["team"], x["opp"]
            key, okey = (s, t), (s, ot)
            # ---------- shooting ----------
            L = sh[key]
            x["box_n"] = len(L)
            if len(L) >= 5:
                def agg(lines):
                    fgm = sum(l["fgm"] for l in lines); fga = sum(l["fga"] for l in lines)
                    tpm = sum(l["tpm"] for l in lines); tpa = sum(l["tpa"] for l in lines)
                    ftm = sum(l["ftm"] for l in lines); fta = sum(l["fta"] for l in lines)
                    return {"efg": (fgm + 0.5 * tpm) / fga if fga else None, "tp": tpm / tpa if tpa else None,
                            "ft": ftm / fta if fta else None, "two": (fgm - tpm) / (fga - tpa) if fga - tpa else None,
                            "ftr": fta / fga if fga else None, "tpr": tpa / fga if fga else None}
                S, F5, F3 = agg(L), agg(L[-5:]), agg(L[-3:])
                x.update({"efg_s": S["efg"], "efg5": F5["efg"], "efg3": F3["efg"], "tp_s": S["tp"], "tp5": F5["tp"],
                          "ft_s": S["ft"], "ft5": F5["ft"], "two_s": S["two"], "two5": F5["two"], "ftr_s": S["ftr"],
                          "ftr5": F5["ftr"], "tpr_s": S["tpr"], "tpr5": F5["tpr"]})
                x["adj5"] = _mean([l["efg"] - l["defg_opp"] for l in L[-5:] if l["defg_opp"] is not None])
                x["adj_s"] = _mean([l["efg"] - l["defg_opp"] for l in L if l["defg_opp"] is not None])
                d = sh_def[key]
                x["defg_s"] = (d[0] + 0.5 * d[1]) / d[2] if d[2] else None
                od = sh_def[okey]
                x["odefg_s"] = (od[0] + 0.5 * od[1]) / od[2] if od[2] and len(sh[okey]) >= 5 else None
            # ---------- players ----------
            P = pl[key]
            x["pbox_n"] = len(P)
            if len(P) >= 5:
                gp = defaultdict(lambda: [0, 0.0, 0.0, 0.0, ""])    # pid -> games, min, pts, fga, name
                tfga = 0.0
                for _, _, ps in P:
                    for pid, (m, pts, fga, st_, name) in ps.items():
                        if m > 0:
                            g = gp[pid]; g[0] += 1; g[1] += m; g[2] += pts; g[3] += fga; g[4] = name
                            tfga += fga
                ng = len(P)
                regs = [pid for pid, g in gp.items() if g[0] >= REG_MIN_G and g[1] / ng >= REG_MPG]
                top7 = sorted(gp, key=lambda p: -gp[p][1])[:7]
                lastps = P[-1][2]
                last_night = P[-1][0]
                vanished = lost3w = fresh = 0
                for pid in regs:
                    run = 0
                    for _, _, ps in reversed(P):
                        if (ps.get(pid) or (0,))[0] > 0:
                            break
                        run += 1
                    if run >= 3:
                        vanished += 1
                        # last appearance night
                        lastn = next((nn for nn, _, ps in reversed(P) if (ps.get(pid) or (0,))[0] > 0), None)
                        if lastn is not None and a["night"] - lastn <= 21:
                            lost3w += 1
                    elif run == 1 and len(P) >= 2 and (P[-2][2].get(pid) or (0,))[0] > 0:
                        fresh += 1
                x["vanished"], x["lost3w"], x["fresh_abs"], x["nregs"] = vanished, lost3w, fresh, len(regs)
                tot_last = sum(v[0] for v in lastps.values()) or 1
                x["churn"] = sum(v[0] for p, v in lastps.items() if p not in top7) / tot_last
                x["starters_used5"] = len({p for _, _, ps in P[-5:] for p, v in ps.items() if v[3]})
                # stars
                cand = [(g[2] / g[0], pid) for pid, g in gp.items() if g[0] >= TOP_MIN_G and g[1] / g[0] >= TOP_MPG]
                if cand:
                    cand.sort(reverse=True)
                    ppg1, p1 = cand[0]
                    x["top_ppg"] = ppg1
                    x["top_fga"] = gp[p1][3] / tfga if tfga else None
                    x["star_gap"] = ppg1 - (cand[1][0] if len(cand) > 1 else 0.0)
                    x["top_name"] = gp[p1][4]
                    x["top_out"] = (lastps.get(p1) or (0,))[0] <= 0
                    # missed-run before the last game
                    played = [(ps.get(p1) or (0,))[0] > 0 for _, _, ps in P]
                    # back2: played last, and before that a run of 2+ misses
                    if played[-1] and len(played) >= 3:
                        k = len(played) - 2
                        miss = 0
                        while k >= 0 and not played[k]:
                            miss += 1; k -= 1
                        x["back2"] = miss >= 2
                        x["miss_before"] = miss
                        # back3: played the last TWO after a 2+ miss run (the control - does it fade out?)
                        x["back3"] = False
                        if not x["back2"] and len(played) >= 4 and played[-2]:
                            k = len(played) - 3
                            miss3 = 0
                            while k >= 0 and not played[k]:
                                miss3 += 1; k -= 1
                            x["back3"] = miss3 >= 2
                    else:
                        x["back2"] = False
                        x["back3"] = False
                    # back1 EX POST: tonight's box has him after a run of 2+ misses ending at the last game
                    if not played[-1]:
                        k = len(played) - 1
                        miss = 0
                        while k >= 0 and not played[k]:
                            miss += 1; k -= 1
                        x["miss_run"] = miss
                        tonight = (pbox.get(t) or {}).get(p1)
                        x["back1"] = bool(tonight and tonight[0] > 0 and miss >= 2)
                    else:
                        x["miss_run"] = 0
                        x["back1"] = False
            # ---------- road / home ----------
            R = rec[key]
            rd = R["road"]
            x["road_w"], x["road_l"] = rd[0], rd[1]
            x["road_cm"] = _mean(rd[2]) if len(rd[2]) >= 3 else None
            x["home_cm"] = _mean(R["home"][2]) if len(R["home"][2]) >= 3 else None
            x["away_cm"] = _mean(R["away_cm"]) if len(R["away_cm"]) >= 3 else None
            x["nhome"], x["naway"] = len(R["home"][2]), len(R["away_cm"])
            x["home_edge"] = (x["home_cm"] - x["away_cm"]) if x["home_cm"] is not None and x["away_cm"] is not None else None
            OR = rec[okey]
            x["ohome_cm"] = _mean(OR["home"][2]) if len(OR["home"][2]) >= 3 else None
            x["oaway_cm"] = _mean(OR["away_cm"]) if len(OR["away_cm"]) >= 3 else None
            x["ohome_edge"] = (x["ohome_cm"] - x["oaway_cm"]) if x["ohome_cm"] is not None and x["oaway_cm"] is not None else None
            x["ohome_w"], x["ohome_l"] = OR["home"][0], OR["home"][1]
            # ---------- momentum ----------
            H = R["hist"]
            cms = [h["cm"] for h in H if h["cm"] is not None]
            x["cm5"] = _mean(cms[-5:]) if len(cms) >= 5 else None
            adj = [h["adjm"] for h in H]
            x["adjm5"] = _mean(adj[-5:]) if len(adj) >= 5 else None
            x["adjm_prev"] = _mean(adj[:-5]) if len(adj) >= 10 else None
            x["improve"] = (x["adjm5"] - x["adjm_prev"]) if x["adjm_prev"] is not None else None
            if H:
                h = H[-1]
                x["beat_good"] = h["won"] and h["orank"]
                x["lost_to_good"] = (not h["won"]) and h["orank"]
                x["big_win"] = h["won"] and h["margin"] >= 15
                x["upset_last"] = h["won"] and (h["ml"] or 0) >= 150
                x["last_cm"] = h["cm"]
            OH = OR["hist"]
            if OH:
                oh = OH[-1]
                x["opp_beat_good"] = oh["won"] and oh["orank"]
                x["opp_big_win"] = oh["won"] and oh["margin"] >= 15
                x["opp_upset_last"] = oh["won"] and (oh["ml"] or 0) >= 150
        # the opponent's player facts, from the pair
        if len(pair) == 2:
            for x, y in ((pair[0], pair[1]), (pair[1], pair[0])):
                x["opp_top_out"] = y.get("top_out")
                x["opp_back2"] = y.get("back2")
                x["opp_miss_run"] = y.get("miss_run")
                x["opp_vanished"] = y.get("vanished")
                x["opp_lost3w"] = y.get("lost3w")
                x["opp_fresh_abs"] = y.get("fresh_abs")
                x["opp_efg5"], x["opp_efg_s"] = y.get("efg5"), y.get("efg_s")
                x["opp_tp5"], x["opp_tp_s"] = y.get("tp5"), y.get("tp_s")
                x["opp_adj5"] = y.get("adj5")
                x["opp_cm5"], x["opp_improve"], x["opp_adjm5"] = y.get("cm5"), y.get("improve"), y.get("adjm5")
                x["opp_road_w"], x["opp_road_l"], x["opp_road_cm"] = y.get("road_w"), y.get("road_l"), y.get("road_cm")
                x["opp_star_gap"], x["opp_top_fga"] = y.get("star_gap"), y.get("top_fga")
        # ---------- update the states AFTER the game ----------
        for x in pair:
            t, ot = x["team"], x["opp"]
            key, okey = (s, t), (s, ot)
            bt, bo = box.get(t), box.get(ot)
            if bt and bo and bt["fga"] and bo["fga"]:
                od = sh_def[okey]
                defg_opp = (od[0] + 0.5 * od[1]) / od[2] if od[2] and len(sh[okey]) >= 3 else None
                sh[key].append({"fgm": bt["fgm"], "fga": bt["fga"], "tpm": bt["tpm"], "tpa": bt["tpa"], "ftm": bt["ftm"],
                                "fta": bt["fta"], "efg": (bt["fgm"] + 0.5 * bt["tpm"]) / bt["fga"], "defg_opp": defg_opp})
            if bo and bo["fga"]:
                d = sh_def[key]
                d[0] += bo["fgm"]; d[1] += bo["tpm"]; d[2] += bo["fga"]
            pt = pbox.get(t)
            if pt:
                pl[key].append((x["night"], gid, {pid: (v[0], v[1], v[2], v[5], v[6]) for pid, v in pt.items()}))
            R = rec[key]
            cm = (x["margin"] + x["sp"]) if x.get("sp") is not None else None
            if x["venue"] == "away":
                R["road"][0 if x["won"] else 1] += 1
                if cm is not None:
                    R["road"][2].append(cm)
                    R["away_cm"].append(cm)
            elif x["venue"] == "home":
                R["home"][0 if x["won"] else 1] += 1
                if cm is not None:
                    R["home"][2].append(cm)
            elif cm is not None:
                R["away_cm"].append(cm)          # (neutral counts as away ground for the home-edge read)
            hadv = 0 if x["neutral"] else (ELO_HADV if x["side"] == "home" else -ELO_HADV)
            exp_m = (x["elo"] + hadv - x["oelo"]) / ELO_PT
            R["hist"].append({"won": x["won"], "margin": x["margin"], "cm": cm, "adjm": x["margin"] - exp_m,
                              "orank": bool(x.get("orank25")), "ml": x.get("ml"), "night": x["night"]})
    pickle.dump(rows, open(pk, "wb"))
    return rows


# ---------------- cells ----------------
def st(ps):
    if not ps:
        return None
    n = len(ps)
    m = sum(ps) / n
    sd = _sd(ps)
    return {"n": n, "roi": m, "z": (m / (sd / math.sqrt(n))) if sd else 0.0}


def cell(name, rows, fn=profit_ml, train=TRAIN_PRICE):
    bets = [(x["season"], fn(x)) for x in rows]
    bets = [(s, p) for s, p in bets if p is not None]
    if not bets:
        return {"name": name, "all": None}
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    o = {"name": name, "all": st([p for _, p in bets]),
         "train": st([p for s, p in bets if train[0] <= s <= train[1]]),
         "held": st([p for s, p in bets if s in HELD]),
         "tr_up": sum(1 for s, v in by.items() if train[0] <= s <= train[1] and sum(v) > 0),
         "tr_n": sum(1 for s in by if train[0] <= s <= train[1]),
         "ho_up": sum(1 for s, v in by.items() if s in HELD and sum(v) > 0),
         "ho_n": sum(1 for s in by if s in HELD),
         "by": {s: st(v) for s, v in sorted(by.items())}}
    if fn is profit_ml:
        op = [profit_open(x) for x in rows if x["season"] in HELD]
        o["open"] = st([p for p in op if p is not None])
    return o


def fmt(o):
    if not o.get("all"):
        return f"{o['name']:66s} n 0"

    def f(s):
        return f"{s['roi']*100:+6.1f}% n{s['n']:<5d}" if s else "    -         "
    by = " ".join(f"{str(s)[2:]}:{v['roi']*100:+.0f}" for s, v in o["by"].items() if v)
    extra = f" | open {f(o['open'])}" if o.get("open") else ""
    return (f"{o['name']:66s} ALL {f(o['all'])} z{o['all']['z']:+.1f} | TR {f(o['train'])} {o['tr_up']}/{o['tr_n']}"
            f" | HELD {f(o['held'])} {o['ho_up']}/{o['ho_n']}{extra} | {by}")


class Out:
    def __init__(self, name, train=TRAIN_BOX):
        self.name, self.lines, self.cells, self.train = name, [], 0, train

    def h(self, t):
        self.lines.append("")
        self.lines.append("== " + t)
        print("\n== " + t)

    def c(self, name, rows, fn=profit_ml, train=None):
        o = cell(name, rows, fn, train or self.train)
        self.cells += 1
        s = fmt(o)
        self.lines.append(s)
        print(s)
        return o

    def note(self, t):
        self.lines.append(t)
        print(t)

    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def regular(rows):
    return [x for x in rows if x["stype"] == "2" and x["season"] >= 2018]


def boxed(rows):
    return [x for x in rows if x["stype"] == "2" and x["season"] >= 2021]


def month(x):
    return x["start"][5:7]


def q(v, cuts):
    for i, c in enumerate(cuts):
        if v < c:
            return i
    return len(cuts)


def three(name, rows_, out, train=None):
    """The standard three cuts of a set of sides: dogs +100..+350 ML, favorites -101..-150 ML, every spread side ATS."""
    out.c(f"{name} | dog +100..+350", dogs(rows_), train=train)
    out.c(f"{name} | fav -101..-150", favs(rows_), train=train)
    out.c(f"{name} | ATS", spreads(rows_), profit_ats, train=train)
