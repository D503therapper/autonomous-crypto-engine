"""11/12 DAILY STUDIES - FOOTBALL'S MONEY CHECK: shared loaders on the 11/12 deep program's replay rows
(results/studies/deep_1112/funnel2.py -> ~/.cache/d503_deep1112/funnel_{new,old}/f[A-D].jsonl, and this study's own
football-day runs, funnel3.py -> ~/.cache/d503_daily1112/). Read-only on the repo."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "deep_1112"))
import dlib as D  # noqa: E402,F401

DEEP = os.path.join(os.path.expanduser("~"), ".cache", "d503_deep1112")
MINE = os.path.join(os.path.expanduser("~"), ".cache", "d503_daily1112")
FB = ("nfl", "ncaaf")


def prep(r):
    r["y"] = 1.0 if r["result"] == "won" else 0.0
    r["half"] = "train" if r["date"] <= "2025-06-30" else "held"
    y, m = int(r["date"][:4]), int(r["date"][5:7])
    r["season"] = y if m >= 7 else y - 1
    r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
    return r


def load(folder, parts="ABCD", leagues=FB, market="ml"):
    rows = []
    for p in parts:
        fp = os.path.join(folder, f"f{p}.jsonl")
        if not os.path.exists(fp):
            continue
        for ln in open(fp):
            r = json.loads(ln)
            if r.get("league") not in leagues or (market and r.get("market") != market):
                continue
            if r.get("result") not in ("won", "lost"):
                continue
            rows.append(prep(r))
    return rows


def key(r):
    return (r["date"], r["gid"], r["side"], r["market"])
