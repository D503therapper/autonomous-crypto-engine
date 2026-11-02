"""S3b - THE STAR WHO MISSED THE LAST GAME (known before tip): the dose and the base.

Each cell is read against its own BASE (the same price band / tier / game 4+ sides whose stars both played the last
game), season by season: 'exc' = the cell's ROI minus the base's. The miss run: missed exactly the last game (played the
one before = a NEW absence) vs missed 2+ in a row (a known, priced absence). Which star: the top scorer vs the 2nd.
Also the residual in points (margin + spread) and in win % (won - no-vig) vs the base - the bet-free read."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, build as fbuild, profit_ml, profit_ats, TRAIN, HELD  # noqa: E402
from lib import load_box, rows  # noqa: E402
import numpy as np
from collections import defaultdict

tb = [x for x in table() if x["stype"] == "2" and x["f"].get("stars") and x["f"].get("has_box")]
box, names, _ = load_box()
# the miss run + which star, from the team's earlier boxes
order = defaultdict(list)
for x in tb:
    order[(x["season"], x["team"])].append(x)
for k, xs in order.items():
    xs.sort(key=lambda x: x["start"])
    for i, x in enumerate(xs):
        f = x["f"]
        st = f["stars"]
        run = 0
        top_missed = False
        if f.get("star_missed_last", 0) >= 1:
            # the earlier boxes, newest first: how many in a row was a star missing
            for j in range(i - 1, -1, -1):
                b = (box.get(xs[j]["id"]) or {}).get(x["team"]) or {}
                if any(p not in b or b[p][0] <= 0 for p in st):
                    run += 1
                else:
                    break
            lb = (box.get(xs[i - 1]["id"]) or {}).get(x["team"]) or {} if i else {}
            top_missed = st[0] not in lb or lb[st[0]][0] <= 0
        x["run"] = run
        x["top_missed"] = top_missed
out = []


def P(s):
    print(s)
    out.append(s)


def band(x):
    m = x.get("ml")
    if m is None:
        return None
    return "dog+100..+350" if 100 <= m <= 350 else "fav-101..-250" if -250 <= m <= -101 else \
        "fav-251+" if m < -250 else "dog+351+" if m > 350 else None


def exc(name, sel, kind):
    """kind 'ats' / 'dog' / 'fav': the cell vs its base by season."""
    fn = profit_ats if kind == "ats" else profit_ml
    bsel = (lambda x: True) if kind == "ats" else (lambda x: band(x) == ("dog+100..+350" if kind == "dog" else "fav-101..-250"))
    by, bb = defaultdict(list), defaultdict(list)
    for x in tb:
        if not bsel(x):
            continue
        p = fn(x)
        if p is None:
            continue
        if x["f"].get("star_missed_last", 0) == 0 and sel(x, base=True):
            bb[x["season"]].append(p)
        elif x["f"].get("star_missed_last", 0) >= 1 and sel(x, base=False):
            by[x["season"]].append(p)
    cs = []
    tot_c, tot_b = [], []
    for s in (2022, 2023, 2024, 2025):
        c, b = by.get(s, []), bb.get(s, [])
        tot_c += c
        tot_b += b
        cs.append(f"{s} {len(c):4d} {np.mean(c)*100 if c else 0:+6.1f}% exc {(np.mean(c)-np.mean(b))*100 if c and b else 0:+6.1f}")
    allc = np.array(tot_c)
    e = (allc.mean() - np.mean(tot_b)) * 100 if len(allc) else 0
    z = e / (allc.std() / np.sqrt(len(allc)) * 100) if len(allc) > 1 else 0
    up_tr = sum(1 for s in range(TRAIN[0], TRAIN[1] + 1) if by.get(s) and np.mean(by[s]) > np.mean(bb[s]))
    up_he = sum(1 for s in HELD if by.get(s) and np.mean(by[s]) > np.mean(bb[s]))
    P(f"{kind:3s} {name:46s} n{len(allc):5d} roi {allc.mean()*100 if len(allc) else 0:+6.1f}% base {np.mean(tot_b)*100:+5.1f}% "
      f"EXC {e:+6.1f} z{z:+5.2f} | over base: train {up_tr}/2 held {up_he}/2 | " + " | ".join(cs))


CUTS = {
    "all": lambda x, base: True,
    "low tier": lambda x, base: x["tier"] == "low",
    "mid tier": lambda x, base: x["tier"] == "mid",
    "power": lambda x, base: x["tier"] == "power",
    "NEW absence (missed only the last)": lambda x, base: base or x["run"] == 1,
    "missed 2+ in a row": lambda x, base: base or x["run"] >= 2,
    "the TOP scorer missed": lambda x, base: base or x["top_missed"],
    "only the 2nd scorer missed": lambda x, base: base or not x["top_missed"],
    "NEW + low tier": lambda x, base: x["tier"] == "low" and (base or x["run"] == 1),
    "NEW + top scorer": lambda x, base: base or (x["run"] == 1 and x["top_missed"]),
    "games 4-10": lambda x, base: x["gn"] <= 10,
    "games 11+ Nov-Dec": lambda x, base: x["gn"] > 10 and x["start"][5:7] in ("11", "12"),
    "Jan-Mar": lambda x, base: x["start"][5:7] in ("01", "02", "03"),
    "away / neutral": lambda x, base: x["venue"] != "home",
    "home": lambda x, base: x["venue"] == "home",
    "opp NOT missing a star": lambda x, base: not (x["of"].get("star_missed_last", 0) >= 1),
}
for kind in ("ats", "dog", "fav"):
    P(f"=== {kind}")
    for k, fn in CUTS.items():
        exc(k, fn, kind)
# bet-free residuals vs base, by cut
P("=== residuals: (margin + spread) pts and (won - no-vig) win-% for the cell minus the base, by season")
for k, fn in CUTS.items():
    cs = []
    for s in (2022, 2023, 2024, 2025):
        c = [x for x in tb if x["season"] == s and x["f"].get("star_missed_last", 0) >= 1 and fn(x, False)]
        b = [x for x in tb if x["season"] == s and x["f"].get("star_missed_last", 0) == 0 and fn(x, True)]
        ra = np.mean([x["margin"] + x["sp"] for x in c if x.get("sp") is not None]) - \
            np.mean([x["margin"] + x["sp"] for x in b if x.get("sp") is not None])
        rm = (np.mean([x["won"] - x["p"] for x in c if x.get("p") is not None]) -
              np.mean([x["won"] - x["p"] for x in b if x.get("p") is not None])) * 100
        cs.append(f"{s} {ra:+5.2f}pt {rm:+5.1f}%")
    P(f"  {k:40s} " + " | ".join(cs))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3b_out.txt"), "w").write("\n".join(out) + "\n")
