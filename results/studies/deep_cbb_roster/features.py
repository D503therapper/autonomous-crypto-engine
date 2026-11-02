"""Build the roster features on every team-side row 2022-26 (cached). python features.py prints a coverage summary.

PRE (per team-season, see lib): ret_min / ret_pts / ret_fga = share of LAST season's team minutes / points / FGA played
by men on this season's roster; tin_min / tin_pts = last-season minutes / points the roster's D1 TRANSFERS logged for
other teams, as a share of this team's last-season totals; tin_pts_pow = the same from POWER-tier programs only;
tin_q = transfer points weighted by the source team's end-of-season Elo over 1500 (per 100 Elo); top1_back / top2_back
= last season's top scorer / how many of the top 2 are on the roster; n_new = men on the roster with no D1 box score
in any earlier season we hold (freshmen, JUCO, overseas, non-D1 transfers).
SO-FAR (strict, before tonight): sf_ret / sf_tin / sf_new = this season's minutes so far by returners / D1 transfers /
newcomers; sf_n = box games so far.
AVAILABILITY (strict + the game's own box): the team's top 2 scorers by points a game this season so far (3+ games
played, 20+ minutes a game) - star_missed_last (one of them NOT in the last game's box though in the season's earlier
ones), star_out_now (one of them not in tonight's box - known only after tip unless reported; for 'did the line move
enough' only), star_back (missed the last game, plays tonight - also ex post)."""
import os, pickle, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403


def build():
    pk = os.path.join(CACHE, "deep_cbb_feat.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    rws = rows()
    box, names, starts = load_box()
    P, T = season_lines(box, starts, rws)
    seasons = sorted(P)
    # end-of-season Elo + tier per team (last row of the season)
    end_elo, tier = {}, {}
    for x in rws:
        end_elo[(x["season"], x["team"])] = x["elo"]
        tier[(x["season"], x["team"])] = x["tier"]
    # earliest season each pid appears in any D1 box (2021+)
    first = {}
    for s in seasons:
        for pid in P[s]:
            first.setdefault(pid, s)
    pre = {}
    for s in seasons:
        if s - 1 not in P:
            continue
        last = P[s - 1]
        roster = defaultdict(set)
        for pid, tms in P[s].items():
            for tm in tms:
                roster[tm].add(pid)
        for tm, R in roster.items():
            TL = T[s - 1].get(tm)
            if not TL or TL[3] < 15 or TL[0] <= 0:
                continue
            ret = [0, 0, 0]
            tin = [0, 0]
            tin_pow = 0
            tin_q = 0.0
            n_new = 0
            tin_n = 0
            for pid in R:
                lp = last.get(pid)
                if lp and tm in lp:
                    a = lp[tm]
                    ret[0] += a[0]; ret[1] += a[1]; ret[2] += a[2]
                if lp:
                    for ot, a in lp.items():
                        if ot == tm:
                            continue
                        tin[0] += a[0]; tin[1] += a[1]
                        if a[0] >= 300:
                            tin_n += 1
                        if tier.get((s - 1, ot)) == "power":
                            tin_pow += a[1]
                        tin_q += a[1] * (end_elo.get((s - 1, ot), 1500) - 1500) / 100
                elif first.get(pid, s) >= s:
                    n_new += 1
            # last season's top scorers (points)
            sc = sorted(((a[tm][1], pid) for pid, a in last.items() if tm in a), reverse=True)
            top = [pid for _, pid in sc[:2]]
            pre[(s, tm)] = {"ret_min": ret[0] / TL[0], "ret_pts": ret[1] / max(TL[1], 1),
                            "ret_fga": ret[2] / max(TL[2], 1), "tin_min": tin[0] / TL[0],
                            "tin_pts": tin[1] / max(TL[1], 1), "tin_pts_pow": tin_pow / max(TL[1], 1),
                            "tin_q": tin_q / max(TL[1], 1), "tin_n": tin_n,
                            "top1_back": bool(top) and top[0] in R,
                            "top2_back": sum(1 for p in top if p in R), "n_new": n_new,
                            "last_elo": end_elo.get((s - 1, tm))}
    # strict, game by game
    feat = {}
    by_team = defaultdict(list)
    for i, x in enumerate(rws):
        if x["season"] >= 2021:
            by_team[(x["season"], x["team"])].append(i)
    for (s, tm), ii in by_team.items():
        last = P.get(s - 1, {})
        hist = []          # [(gid, {pid: (min, pts, fga, starter)})] of earlier games with a box
        for i in ii:
            x = rws[i]
            f = dict(pre.get((s, tm)) or {})
            f["has_pre"] = (s, tm) in pre
            b = (box.get(x["id"]) or {}).get(tm)
            f["has_box"] = b is not None
            tot = r = t = n = 0
            for _, hb in hist:
                for pid, (m, *_r) in hb.items():
                    tot += m
                    lp = last.get(pid)
                    if lp and tm in lp:
                        r += m
                    elif lp:
                        t += m
                    elif first.get(pid, s) >= s:
                        n += m
            f["sf_n"] = len(hist)
            if tot:
                f["sf_ret"], f["sf_tin"], f["sf_new"] = r / tot, t / tot, n / tot
            # stars so far
            if len(hist) >= 3:
                gp = defaultdict(lambda: [0, 0, 0])
                for _, hb in hist:
                    for pid, (m, pts, *_r) in hb.items():
                        if m > 0:
                            g = gp[pid]; g[0] += 1; g[1] += pts; g[2] += m
                cand = sorted(((g[1] / g[0], pid) for pid, g in gp.items()
                               if g[0] >= 3 and g[2] / g[0] >= 20), reverse=True)[:2]
                stars = [pid for _, pid in cand]
                f["stars"] = stars
                f["star_ppg"] = [round(v, 1) for v, _ in cand]
                lastb = hist[-1][1]
                f["star_missed_last"] = sum(1 for p in stars if p not in lastb or lastb[p][0] <= 0)
                if b is not None:
                    f["star_out_now"] = sum(1 for p in stars if p not in b or b[p][0] <= 0)
                    f["star_back"] = sum(1 for p in stars if (p not in lastb or lastb[p][0] <= 0)
                                         and p in b and b[p][0] > 0)
                # top scorer share of points so far
                tp = sum(g[1] for g in gp.values())
                f["star_share"] = sum(gp[p][1] for p in stars) / tp if tp else None
            feat[(x["id"], tm)] = f
            if b is not None:
                hist.append((x["id"], b))
    out = feat
    pickle.dump(out, open(pk, "wb"))
    return out


def table():
    """rows (2021+) with the team's features under x['f'] and the opponent's under x['of']."""
    rws = rows()
    F = build()
    out = []
    for x in rws:
        if x["season"] < 2021:
            continue
        f, of = F.get((x["id"], x["team"])), F.get((x["id"], x["opp"]))
        if f is None:
            continue
        y = dict(x)
        y["f"], y["of"] = f, of or {}
        out.append(y)
    return out


if __name__ == "__main__":
    tb = table()
    from collections import Counter
    c = Counter((x["season"], x["f"].get("has_pre"), x.get("ml") is not None) for x in tb)
    for k in sorted(c):
        print(k, c[k])
    import statistics as stt
    for s in (2022, 2023, 2024, 2025, 2026):
        v = [x["f"]["ret_min"] for x in tb if x["season"] == s and x["f"].get("has_pre") and x["gn"] == 1]
        t = [x["f"]["tin_min"] for x in tb if x["season"] == s and x["f"].get("has_pre") and x["gn"] == 1]
        if v:
            print(s, "teams", len(v), "ret_min median %.2f" % stt.median(v), "tin_min median %.2f" % stt.median(t))
