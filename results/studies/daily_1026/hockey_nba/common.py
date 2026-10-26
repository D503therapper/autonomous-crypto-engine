"""Shared loader for the 10/26 NHL + NBA studies (the 10/25 loader, pointed at this worktree). Read-only on the repo.
One row per side, every feature known before puck drop / tip (schedule + results of EARLIER games only). Graded flat 1u
at the closing ML; train 2016/18-24, holdout 2025, current 2026."""
import sys, os, collections, math
from datetime import datetime, timedelta
WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, WT)
os.chdir(WT)
import sports_data as sd  # noqa: E402


def season(start):
    y, m = int(start[:4]), int(start[5:7])
    if y == 2020 and m <= 10:
        return 2019          # bubble
    return y if m >= 9 else y - 1


def dt(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def prob(ml):
    ml = float(ml)
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def pay(ml):
    ml = float(ml)
    return ml / 100 if ml > 0 else 100 / -ml


def load(league, start="2016-09-01"):
    G = sd.load_games(league)
    fin = [g for g in G.values() if g.get("status") == "final" and str(g.get("stype")) == "2"
           and g.get("home_score") not in ("", None) and g.get("start", "") >= start and g.get("home") and g.get("away")]
    fin.sort(key=lambda g: (g["start"], g["id"]))
    sched = collections.defaultdict(list)
    for g in fin:
        sched[g["home"]].append(g); sched[g["away"]].append(g)
    return fin, sched


def report(rows, f, name, train, hold, cur=(2026,), out=print):
    """rows: dicts with season, ml, nv, won, roi. Prints train / holdout / current, by season, vs expected."""
    r = [x for x in rows if f(x)]
    line = [name]
    for part, ss in (("TRAIN", train), ("HOLD", hold), ("CUR", cur)):
        rs = [x for x in r if x["season"] in ss]
        if not rs:
            line.append(f"{part}: n=0"); continue
        n = len(rs); w = sum(x["won"] for x in rs); e = sum(x["nv"] for x in rs)
        roi = sum(x["roi"] for x in rs) / n * 100
        sd_ = math.sqrt(sum(x["nv"] * (1 - x["nv"]) for x in rs)) or 1
        z = (w - e) / sd_
        bys = " ".join(f"{s % 100}:{sum(x['roi'] for x in rs if x['season'] == s) / max(1, sum(1 for x in rs if x['season'] == s)) * 100:+.0f}({sum(1 for x in rs if x['season'] == s)})"
                       for s in ss if any(x['season'] == s for x in rs))
        up = sum(1 for s in ss if any(x['season'] == s for x in rs) and sum(x['roi'] for x in rs if x['season'] == s) > 0)
        tot = sum(1 for s in ss if any(x['season'] == s for x in rs))
        line.append(f"{part}: n={n} {w / n * 100:.1f}% vs {e / n * 100:.1f}% exp z{z:+.1f} ROI {roi:+.1f}% up {up}/{tot} [{bys}]")
    out("\n   ".join(line))
    return r


def sides(fin, sched, feat):
    """-> one row per priced side. feat(g, side, i_prev_games) -> dict of pre-game features for that side."""
    idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
    rows = []
    for g in fin:
        if not (g.get("ml_home") and g.get("ml_away")):
            continue
        try:
            mh, ma = float(g["ml_home"]), float(g["ml_away"])
        except ValueError:
            continue
        if abs(mh) < 100 or abs(ma) < 100:
            continue
        s = season(g["start"])
        fs = {side: feat(g, side, sched[g[side]][:idx[g[side]][g["id"]]], s) for side in ("home", "away")}
        for side, oside in (("home", "away"), ("away", "home")):
            ml, oml = (mh, ma) if side == "home" else (ma, mh)
            nv = prob(ml) / (prob(ml) + prob(oml))
            mar = float(g[f"{side}_score"]) - float(g[f"{oside}_score"])
            sp = g.get("spread_home"); ats = None
            if sp not in ("", None):
                try:
                    c = mar + (float(sp) if side == "home" else -float(sp))
                    ats = None if c == 0 else c > 0
                except ValueError:
                    pass
            rows.append(dict(season=s, ml=ml, nv=nv, won=mar > 0, roi=pay(ml) if mar > 0 else -1.0, home=side == "home",
                             ats=ats, start=g["start"], **fs[side], **{"o_" + k: v for k, v in fs[oside].items()}))
    return rows
