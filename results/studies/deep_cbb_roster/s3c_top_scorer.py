"""S3c - THE TOP SCORER MISSED THE LAST GAME: dose by the miss run, the OPEN (2023-25 ML), the OTHER side (the
favorite / spread side across him), the line move, his scoring share, and whether he plays tonight (ex post).
'top scorer' = the team's leader in points a game so far (3+ games, 20+ minutes a game) - all known before tip."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, profit_ml, profit_ats, profit_open, TRAIN, HELD  # noqa: E402
from lib import load_box  # noqa: E402
import numpy as np
from collections import defaultdict

tb = [x for x in table() if x["stype"] == "2" and x["f"].get("stars") and x["f"].get("has_box")]
box, names, _ = load_box()
order = defaultdict(list)
for x in tb:
    order[(x["season"], x["team"])].append(x)


def runs(xs, team):
    xs.sort(key=lambda x: x["start"])
    for i, x in enumerate(xs):
        top = x["f"]["stars"][0]
        r = 0
        for j in range(i - 1, -1, -1):
            b = (box.get(xs[j]["id"]) or {}).get(team) or {}
            if top not in b or b[top][0] <= 0:
                r += 1
            else:
                break
        x["top_run"] = r
        b = (box.get(x["id"]) or {}).get(team) or {}
        x["top_now"] = top in b and b[top][0] > 0
        gp = 0
        for j in range(i):
            b = (box.get(xs[j]["id"]) or {}).get(team) or {}
            if top in b and b[top][0] > 0:
                gp += 1
        x["top_gp"] = gp


for (s, t), xs in order.items():
    runs(xs, t)
idx = {(x["id"], x["team"]): x for x in tb}
for x in tb:
    o = idx.get((x["id"], x["opp"]))
    x["o_top_run"] = o["top_run"] if o else None
out = []


def P(s):
    print(s)
    out.append(s)


def band(x, o="ml"):
    m = x.get(o)
    if m is None:
        return None
    return "dog" if 100 <= m <= 350 else "fav" if -250 <= m <= -101 else None


def row(name, sel, kind, fn=None, base=None):
    fn = fn or (profit_ats if kind == "ats" else profit_ml)
    pick = (lambda x: True) if kind == "ats" else (lambda x: band(x, "mlo" if fn is profit_open else "ml") == kind)
    by, bb = defaultdict(list), defaultdict(list)
    for x in tb:
        if not pick(x):
            continue
        p = fn(x)
        if p is None:
            continue
        if sel(x):
            by[x["season"]].append(p)
        elif base(x):
            bb[x["season"]].append(p)
    c = [p for v in by.values() for p in v]
    b = [p for v in bb.values() for p in v]
    if not c:
        P(f"{kind:3s} {name:52s} -")
        return
    e = (np.mean(c) - np.mean(b)) * 100
    z = e / (np.std(c) / np.sqrt(len(c)) * 100)
    ss = " | ".join(f"{s} {len(by.get(s, [])):4d} {((np.mean(by[s]) - np.mean(bb[s])) * 100 if by.get(s) and bb.get(s) else 0):+6.1f}"
                    for s in (2022, 2023, 2024, 2025))
    up = lambda S: sum(1 for s in S if by.get(s) and np.mean(by[s]) > np.mean(bb[s]))
    P(f"{kind:3s} {name:52s} n{len(c):5d} roi {np.mean(c)*100:+6.1f}% base {np.mean(b)*100:+5.1f}% EXC {e:+6.1f} "
      f"z{z:+5.2f} | over base train {up(range(TRAIN[0], TRAIN[1]+1))}/2 held {up(HELD)}/2 | exc by season: {ss}")


nomiss = lambda x: x["top_run"] == 0 and (x["o_top_run"] or 0) == 0
P("=== the team whose TOP scorer missed the last game (base = neither team's top scorer missed the last game)")
for lab, sel in (("missed the last game (run 1+)", lambda x: x["top_run"] >= 1),
                 ("  run 1 (a NEW absence)", lambda x: x["top_run"] == 1),
                 ("  run 2-3", lambda x: 2 <= x["top_run"] <= 3),
                 ("  run 4-7", lambda x: 4 <= x["top_run"] <= 7),
                 ("  run 8+ (gone for the season?)", lambda x: x["top_run"] >= 8),
                 ("  run 1-3", lambda x: 1 <= x["top_run"] <= 3),
                 ("  plays TONIGHT (ex post)", lambda x: x["top_run"] >= 1 and x["top_now"]),
                 ("  sits again tonight (ex post)", lambda x: x["top_run"] >= 1 and not x["top_now"]),
                 ("  low tier", lambda x: x["top_run"] >= 1 and x["tier"] == "low"),
                 ("  mid tier", lambda x: x["top_run"] >= 1 and x["tier"] == "mid"),
                 ("  power", lambda x: x["top_run"] >= 1 and x["tier"] == "power"),
                 ("  his share of scoring 25%+", lambda x: x["top_run"] >= 1 and (x["f"].get("star_ppg") or [0])[0] >= 15),
                 ("  ppg under 15", lambda x: x["top_run"] >= 1 and (x["f"].get("star_ppg") or [0])[0] < 15),
                 ("  Nov-Dec", lambda x: x["top_run"] >= 1 and x["start"][5:7] in ("11", "12")),
                 ("  Jan-Mar", lambda x: x["top_run"] >= 1 and x["start"][5:7] in ("01", "02", "03")),
                 ("  conference game", lambda x: x["top_run"] >= 1 and x["same_conf"]),
                 ("  non-conference", lambda x: x["top_run"] >= 1 and not x["same_conf"])):
    for kind in ("ats", "dog", "fav"):
        row(lab, lambda x, sel=sel: sel(x) and (x["o_top_run"] or 0) == 0, kind, base=nomiss)
P("=== second check: ESPN's OPEN moneyline (2023-25)")
for lab, sel in (("missed the last game (run 1+)", lambda x: x["top_run"] >= 1),
                 ("  run 1-3", lambda x: 1 <= x["top_run"] <= 3)):
    for kind in ("dog", "fav"):
        row(lab + " @OPEN", lambda x, sel=sel: sel(x) and (x["o_top_run"] or 0) == 0, kind, fn=profit_open, base=nomiss)
P("=== the OTHER side (bet the opponent of the team whose top scorer missed the last game)")
for lab, sel in (("opp's top scorer missed the last game", lambda x: (x["o_top_run"] or 0) >= 1),
                 ("  opp run 1-3", lambda x: 1 <= (x["o_top_run"] or 0) <= 3),
                 ("  opp run 4+", lambda x: (x["o_top_run"] or 0) >= 4)):
    for kind in ("ats", "dog", "fav"):
        row(lab, lambda x, sel=sel: sel(x) and x["top_run"] == 0, kind, base=nomiss)
P("=== the line: no-vig open -> close move for the team (2023-25), and the residual vs the close")
for lab, sel in (("base", nomiss), ("top missed last (run 1+)", lambda x: x["top_run"] >= 1 and (x["o_top_run"] or 0) == 0),
                 ("  run 1", lambda x: x["top_run"] == 1 and (x["o_top_run"] or 0) == 0),
                 ("  run 2-3", lambda x: 2 <= x["top_run"] <= 3 and (x["o_top_run"] or 0) == 0),
                 ("  run 4+", lambda x: x["top_run"] >= 4 and (x["o_top_run"] or 0) == 0)):
    xs = [x for x in tb if sel(x)]
    mv = [(x["p"] - x["po"]) * 100 for x in xs if x.get("po") is not None and x.get("p") is not None]
    rs = [(x["won"] - x["p"]) * 100 for x in xs if x.get("p") is not None]
    ra = [x["margin"] + x["sp"] for x in xs if x.get("sp") is not None]
    P(f"  {lab:28s} move {np.mean(mv):+5.2f}% (n{len(mv)}) | won - close {np.mean(rs):+5.2f}% | margin + spread "
      f"{np.mean(ra):+5.2f} pts (se {np.std(ra)/np.sqrt(len(ra)):.2f}, n{len(ra)})")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3c_out.txt"), "w").write("\n".join(out) + "\n")
