"""H51 - THE TWO REPLAYS SIDE BY SIDE ON THE SAME SEASONS (2023-25): the 11/13 funnel4 rows and the 11/14 funnel5 rows
(the same games, the engine one day of code apart, each with its own July re-tune). A cell that is real reads the same
on both; a knife-edge cut (the read at exactly 56%, the lift at exactly 2 points) does not."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

rec = M.rec


def load(src):
    out = []
    for f in sorted(glob.glob(os.path.expanduser(f"~/.cache/{src}/rows/s20*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            if r["market"] != "ml" or r.get("result") not in ("won", "lost", "push") or not -150 <= r["odds"] <= -101:
                continue
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            if not 2023 <= r["season"] <= 2025:
                continue
            r["win"] = r["result"] == "won"
            r["pnl"] = 0.0 if r["result"] == "push" else ((r["dec"] - 1) if r["win"] else -1.0)
            r["mn"] = min(r.get("games_in") or 0, r.get("opp_games_in") or 0)
            r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
            r["lift"] = None if (r.get("w_p") is None or r["own"] is None) else r["w_p"] - r["own"]
            r["we"] = None if r.get("w_p") is None else r["w_p"] * r["dec"] - 1
            if r["mn"] >= 3:
                out.append(r)
    return out


A, B = load("d503_leans1113"), load("d503_cbb1114")
ka = {(r["gid"], r["side"]): r for r in A}
kb = {(r["gid"], r["side"]): r for r in B}
both = [k for k in ka if k in kb]
print(f"favorites -150..-101 (3+ games) 2023-25: {len(A)} on the 11/13 rows, {len(B)} on the 11/14 rows, {len(both)} on both")
d_p = [abs(ka[k]["p"] - kb[k]["p"]) for k in both]
d_w = [abs(ka[k]["w_p"] - kb[k]["w_p"]) for k in both if ka[k].get("w_p") is not None and kb[k].get("w_p") is not None]
d_l = [abs(ka[k]["lift"] - kb[k]["lift"]) for k in both if ka[k]["lift"] is not None and kb[k]["lift"] is not None]
q = lambda v, f: sorted(v)[int(f * (len(v) - 1))] if v else float("nan")
print(f"   the same side on the two: the read differs by a median {100 * q(d_p, .5):.2f} pts (90th pct {100 * q(d_p, .9):.2f}), the weighed read "
      f"{100 * q(d_w, .5):.2f} ({100 * q(d_w, .9):.2f}), the lift {100 * q(d_l, .5):.2f} ({100 * q(d_l, .9):.2f})")
clean = lambda r: not r.get("trap") and not r.get("fighting")
for nm, f in (("the Lock (kind)", lambda r: r.get("kind") == "lock"),
              ("56%+, weighed over the market and the price, clean (B)", lambda r: r["we"] is not None and r["p"] >= 0.56 and r["we"] > 0 and r["w_p"] >= r["p_market"] and clean(r)),
              ("B, lift 2+ (the knife-edge cut)", lambda r: r["we"] is not None and r["p"] >= 0.56 and r["we"] > 0 and r["w_p"] >= r["p_market"] and clean(r) and r["lift"] >= 0.02 - 1e-9),
              ("B, lift 1.5+", lambda r: r["we"] is not None and r["p"] >= 0.56 and r["we"] > 0 and r["w_p"] >= r["p_market"] and clean(r) and r["lift"] >= 0.015),
              ("B, lift under 1.5", lambda r: r["we"] is not None and r["p"] >= 0.56 and r["we"] > 0 and r["w_p"] >= r["p_market"] and clean(r) and r["lift"] < 0.015),
              ("55%+, weighed over the price, clean, lift 1.5+ (a soft edge)", lambda r: r["we"] is not None and r["p"] >= 0.55 and r["we"] > 0 and clean(r) and r["lift"] >= 0.015),
              ("any read, weighed over the price, clean", lambda r: r["we"] is not None and r["we"] > 0 and clean(r)),
              ("any read, lift 1.5+, clean", lambda r: r["lift"] is not None and r["lift"] >= 0.015 and clean(r)),
              ("any read, lift 0..1.5, clean", lambda r: r["lift"] is not None and 0 < r["lift"] < 0.015 and clean(r)),
              ("any read, lift under 0", lambda r: r["lift"] is not None and r["lift"] < 0),
              ("lift -2 or worse", lambda r: r["lift"] is not None and r["lift"] <= -0.02)):
    print(nm)
    sa, sb = [r for r in A if f(r)], [r for r in B if f(r)]
    rec("   11/13 rows", sa, None, min_n=1)
    rec("   11/14 rows", sb, None, min_n=1)
    xa, xb = {(r["gid"], r["side"]) for r in sa}, {(r["gid"], r["side"]) for r in sb}
    un = {k: (ka.get(k) or kb.get(k)) for k in xa | xb}
    rec(f"   on BOTH ({len(xa & xb)})", [ka[k] for k in xa & xb], None, min_n=1)
    rec(f"   on EITHER ({len(un)})", list(un.values()), None, min_n=1)
