"""MLB: a starting pitcher's OWN history against today's opponent (10/6, the owner - the pitcher-level version of
"a team has another team's number", which is DEAD at the team level in every sport incl. MLB, 10/5).

Three angles, every cut fixed before the run and every cut counted (multiple testing):
  A. PITCHER VS THIS TEAM - his runs allowed per 9 in his past starts against this opponent vs his own normal
     (every start before today, strictly - no look-ahead). Dominated them = bet his side at the close; crushed by
     them = bet the lineup.
  B. JUST FACED THEM - his previous start was against this same team (rematch; playoffs, back-to-back series), or
     any start vs them within the last 14 days. Pitcher side AND the lineup side ("they just saw him").
  C. Cousins - last time out vs them he got crushed (revenge), last time he shut them down, his team lost last time.

Data: data/sports/players/mlb.csv (every starter's line 2017-26), the game files (sports_data.load_games: final score,
closing moneyline = the last price before first pitch, 2018-26). Spring training skipped (stype 1).
Grading: flat 1u on the side at the close; residual = win - the no-vig implied % of the price. No model, nothing fit,
so BLIND holds by construction; FAIR holds (same-day closing prices).
Run: python tools/mlb_pitcher_vs_team_study.py  ->  results/mlb_pitcher_vs_team_study.json
"""
import csv
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYERS = os.path.join(HERE, "..", "data", "sports", "players", "mlb.csv")
OUT = os.path.join(HERE, "..", "results", "mlb_pitcher_vs_team_study.json")

MIN_VS = 3          # starts vs this team before "has history" counts
MIN_OWN = 15        # his own starts before his "normal" counts
DOM = 2.0           # runs per 9 better (or worse) than his normal vs this team = dominated / crushed
RECENT_DAYS = 14    # "just faced them"
SHRINK = 5          # starts of shrinkage toward the league rate when his sample vs the team is small


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(oh, oa):
    ph, pa = sd.implied(oh), sd.implied(oa)
    return ph / (ph + pa), pa / (ph + pa)


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


class Tally:
    def __init__(self):
        self.n = 0
        self.w = 0
        self.ret = 0.0
        self.imp = 0.0
        self.by = defaultdict(lambda: [0, 0, 0.0, 0.0])

    def add(self, season, won, d, p):
        self.n += 1
        self.w += won
        self.ret += (d - 1) if won else -1
        self.imp += p
        b = self.by[season]
        b[0] += 1
        b[1] += won
        b[2] += (d - 1) if won else -1
        b[3] += p

    def out(self):
        if not self.n:
            return {"n": 0}
        wp = self.w / self.n
        se = math.sqrt(wp * (1 - wp) / self.n) * 100
        seasons = {s: {"n": b[0], "w": b[1], "roi": round(100 * b[2] / b[0], 1), "win%": round(100 * b[1] / b[0], 1),
                       "implied%": round(100 * b[3] / b[0], 1)} for s, b in sorted(self.by.items())}
        up = sum(1 for b in self.by.values() if b[2] > 0)
        return {"n": self.n, "w": self.w, "win%": round(100 * wp, 1), "implied%": round(100 * self.imp / self.n, 1),
                "edge_pts": round(100 * (wp - self.imp / self.n), 1), "se_pts": round(se, 1),
                "roi%": round(100 * self.ret / self.n, 1), "units": round(self.ret, 1),
                "seasons_up": f"{up} of {len(self.by)}", "last3_up": f"{sum(1 for s, b in self.by.items() if s >= '2024' and b[2] > 0)} of {sum(1 for s in self.by if s >= '2024')}",
                "by_season": seasons}


def load_starts():
    """starter -> list of his starts in time order (team, opp, ip, r, start, gid)."""
    games = sd.load_games("mlb")
    rows = defaultdict(list)
    with open(PLAYERS) as f:
        for r in csv.DictReader(f):
            if r["role"] != "SP":
                continue
            g = games.get(r["gid"])
            if not g or g.get("stype") == "1":
                continue
            opp = g["away"] if r["team"] == g["home"] else g["home"]
            ip, runs = _f(r["ip"]), _f(r["r"])
            if ip is None or runs is None:
                continue
            rows[r["gid"]].append({"name": r["player"], "team": r["team"], "opp": opp, "ip": ip, "r": runs,
                                   "start": r["start"], "gid": r["gid"]})
    return games, rows


def main():
    games, starts_by_game = load_starts()
    order = sorted(starts_by_game, key=lambda gid: starts_by_game[gid][0]["start"])
    hist = defaultdict(list)                   # pitcher -> his past starts (time order)
    lg = [0.0, 0.0]                            # league runs, innings so far
    cuts = defaultdict(Tally)
    pairs = []                                 # (diff vs team, residual, won, dec, implied) - correlation + quintiles
    price = defaultdict(list)                  # 'in the price' check: implied % of the pitcher's team by bucket
    rematch_perf = defaultdict(lambda: [0.0, 0.0, 0.0, 0])   # label -> [runs, ip, expected runs, starts]
    for gid in order:
        g = games[gid]
        t = _t(g["start"])
        season = g["start"][:4]
        hs, as_ = _f(g.get("home_score")), _f(g.get("away_score"))
        try:
            oh, oa = int(g["ml_home"]), int(g["ml_away"])
        except (ValueError, KeyError, TypeError):
            oh = oa = None
        priced = oh is not None and hs is not None and as_ is not None and hs != as_
        lg_ra9 = 9 * lg[0] / lg[1] if lg[1] > 500 else None
        for s in starts_by_game[gid]:
            name, team, opp = s["name"], s["team"], s["opp"]
            past = hist[name]
            vs = [p for p in past if p["opp"] == opp]
            own_ip = sum(p["ip"] for p in past)
            own_r = sum(p["r"] for p in past)
            own_ra9 = 9 * own_r / own_ip if own_ip > 0 else None
            vs_ip = sum(p["ip"] for p in vs)
            vs_r = sum(p["r"] for p in vs)
            # shrunk runs/9 vs this team toward his own normal (SHRINK starts of ~5.5 innings)
            diff = None
            if len(vs) >= MIN_VS and len(past) >= MIN_OWN and own_ra9 is not None and vs_ip > 0:
                k_ip = SHRINK * 5.5
                vs_ra9 = 9 * (vs_r + own_ra9 * k_ip / 9) / (vs_ip + k_ip)
                diff = own_ra9 - vs_ra9                      # + = he does better vs this team than usual
            last = past[-1] if past else None
            rematch = last is not None and last["opp"] == opp
            recent = [p for p in past if p["opp"] == opp and (t - _t(p["start"])).days <= RECENT_DAYS]
            last_vs = vs[-1] if vs else None
            # the pitcher's actual line this game vs expectation (does he do worse the second time?)
            if lg_ra9 is not None and own_ra9 is not None and len(past) >= MIN_OWN:
                l10 = past[-10:]
                l10_ip = sum(p["ip"] for p in l10)
                # expected runs from his LAST 10 starts (his career rate drifts with age / the run environment)
                exp_r = (9 * sum(p["r"] for p in l10) / l10_ip if l10_ip else own_ra9) * s["ip"] / 9
                if rematch:
                    rematch_perf["rematch_prev_start"][0] += s["r"]
                    rematch_perf["rematch_prev_start"][1] += s["ip"]
                    rematch_perf["rematch_prev_start"][2] += exp_r
                    rematch_perf["rematch_prev_start"][3] += 1
                if recent and not rematch:
                    rematch_perf["faced_within_14d_not_prev"][0] += s["r"]
                    rematch_perf["faced_within_14d_not_prev"][1] += s["ip"]
                    rematch_perf["faced_within_14d_not_prev"][2] += exp_r
                    rematch_perf["faced_within_14d_not_prev"][3] += 1
                if not vs:
                    rematch_perf["never_faced_them"][0] += s["r"]
                    rematch_perf["never_faced_them"][1] += s["ip"]
                    rematch_perf["never_faced_them"][2] += exp_r
                    rematch_perf["never_faced_them"][3] += 1
                if diff is not None:
                    key = "dominated_them" if diff >= DOM else "crushed_by_them" if diff <= -DOM else "neutral_history"
                    rematch_perf[key][0] += s["r"]
                    rematch_perf[key][1] += s["ip"]
                    rematch_perf[key][2] += exp_r
                    rematch_perf[key][3] += 1
            if priced:
                home = team == g["home"]
                o_mine, o_theirs = (oh, oa) if home else (oa, oh)
                p_mine, p_theirs = novig(o_mine, o_theirs)
                won_mine = (hs > as_) if home else (as_ > hs)
                d_mine, d_theirs = dec(o_mine), dec(o_theirs)

                def bet(label, mine=True):
                    if mine:
                        cuts[label].add(season, won_mine, d_mine, p_mine)
                    else:
                        cuts[label].add(season, not won_mine, d_theirs, p_theirs)
                bet("ALL pitcher sides (baseline)")
                if diff is not None:
                    pairs.append((diff, won_mine - p_mine, won_mine, d_mine, p_mine))
                    bucket = "dominated" if diff >= DOM else "crushed" if diff <= -DOM else "neutral"
                    price[bucket].append(p_mine)
                    price["his own normal vs lg: " + ("good" if own_ra9 < (lg_ra9 or 4.5) else "bad")].append(p_mine)
                    if diff >= DOM:
                        bet("A1 dominated this team (RA9 2+ better than his normal, 3+ starts) - his side")
                        if p_mine < 0.5:
                            bet("A1b dominated this team AND his team is the dog - his side")
                    if diff <= -DOM:
                        bet("A2 crushed by this team (RA9 2+ worse, 3+ starts) - bet the lineup", mine=False)
                    if diff >= 1.0:
                        bet("A3 looser: RA9 1+ better vs them - his side")
                        # POST-HOC (added after the quintile curve ran the wrong way): fade the dominator
                        bet("A3r post-hoc: fade the dominator (RA9 1+ better vs them) - bet the lineup", mine=False)
                    if diff <= -1.0:
                        bet("A4 looser: RA9 1+ worse vs them - bet the lineup", mine=False)
                if rematch:
                    bet("B1 rematch: his previous start was vs this team - his side")
                    bet("B1r rematch - the lineup that just saw him", mine=False)
                    if last["r"] >= 5:
                        bet("C1 revenge: they scored 5+ on him last start - his side")
                    if last["r"] <= 1 and last["ip"] >= 6:
                        bet("C2 he shut them down last start (<=1 run, 6+ IP) - his side again")
                        bet("C2r he shut them down last start - the lineup bounces back", mine=False)
                    if g.get("stype") == "3":
                        bet("B3 playoff rematch - his side")
                if recent:
                    bet("B2 faced them within 14 days (any start) - his side")
                    bet("B2r faced them within 14 days - the lineup", mine=False)
                if last_vs is not None and not rematch and (t - _t(last_vs["start"])).days <= 400 and last_vs["r"] >= 6:
                    bet("C3 they crushed him (6+ runs) last meeting within a year, not a rematch - his side")
                if rematch and last_vs is not None:
                    # did his team lose that last meeting? (score of that game)
                    lg_game = games.get(last_vs["gid"])
                    if lg_game:
                        lh, la = _f(lg_game.get("home_score")), _f(lg_game.get("away_score"))
                        if lh is not None and la is not None:
                            lost = (lh < la) if last_vs["team"] == lg_game["home"] else (la < lh)
                            if lost:
                                bet("C4 rematch and his team LOST the last meeting - his side")
                            else:
                                bet("C5 rematch and his team WON the last meeting - his side")
        # after the game: history and league rate
        for s in starts_by_game[gid]:
            hist[s["name"]].append(s)
            lg[0] += s["r"]
            lg[1] += s["ip"]

    # correlation of 'dominated them' with beating the price
    corr = None
    if len(pairs) > 10:
        xy = [(c[0], c[1]) for c in pairs]
        mx = sum(a for a, _ in xy) / len(xy)
        my = sum(b for _, b in xy) / len(xy)
        sxy = sum((a - mx) * (b - my) for a, b in xy)
        sxx = sum((a - mx) ** 2 for a, _ in xy)
        syy = sum((b - my) ** 2 for _, b in xy)
        corr = round(sxy / math.sqrt(sxx * syy), 3) if sxx and syy else None
    quint = {}
    if pairs:
        srt = sorted(pairs, key=lambda x: x[0])
        k = 5
        for i in range(k):
            chunk = srt[i * len(srt) // k:(i + 1) * len(srt) // k]
            n = len(chunk)
            w = sum(c[2] for c in chunk)
            ret = sum((c[3] - 1) if c[2] else -1 for c in chunk)
            quint[f"q{i + 1} diff {chunk[0][0]:+.2f}..{chunk[-1][0]:+.2f}"] = {
                "n": n, "win%": round(100 * w / n, 1), "implied%": round(100 * sum(c[4] for c in chunk) / n, 1),
                "roi%": round(100 * ret / n, 1)}
    res = {
        "settings": {"MIN_VS": MIN_VS, "MIN_OWN": MIN_OWN, "DOM": DOM, "RECENT_DAYS": RECENT_DAYS, "SHRINK": SHRINK},
        "cuts_tried": len([c for c in cuts if not c.startswith("ALL")]) + 1,     # + the quintile curve
        "corr_history_vs_residual": {"n": len(pairs), "r": corr},
        "quintiles of 'his RA9 vs them, better than his normal' (his side at the close)": quint,
        "in_the_price (avg implied % of the pitcher's team)": {k: {"n": len(v), "implied%": round(100 * sum(v) / len(v), 1)} for k, v in sorted(price.items())},
        "pitcher_actual_vs_his_normal (runs allowed vs expected from his LAST 10 starts)": {
            k: {"starts": v[3], "ip": round(v[1]), "runs": round(v[0]), "expected": round(v[2]),
                "ra9": round(9 * v[0] / v[1], 2) if v[1] else None, "exp_ra9": round(9 * v[2] / v[1], 2) if v[1] else None,
                "diff_ra9": round(9 * (v[0] - v[2]) / v[1], 2) if v[1] else None} for k, v in sorted(rematch_perf.items())},
        "cuts": {k: v.out() for k, v in sorted(cuts.items())},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "cuts"}, indent=1))
    for k, v in res["cuts"].items():
        print(f"\n{k}")
        print({kk: vv for kk, vv in v.items() if kk != "by_season"})
        for s, b in v.get("by_season", {}).items():
            print("  ", s, b)
    return res


if __name__ == "__main__":
    main()
