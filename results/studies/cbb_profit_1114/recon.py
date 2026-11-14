"""11/14 - the dog slot rebuilt on the 11/13 funnel4 rows (all nine seasons; the funnel5 re-run is too slow to finish
before the 8 AM board on a shared machine - it is the check on this where it has finished). The slot's pool: every
college hoops moneyline dog +100..+350, dog read 4+, both teams 4+ games, never a trap / a side the own read fights /
a positive edge missing, in a game no Lock took; ranked by the dog read, then the efficiency gap (the 11/3 K table's
walk-forward read), the best two a night. Its picks that the funnel saved as 'gap' are the TWINS (both count)."""
import os, pickle, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L


def slot(R):
    K = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
    eff = {(x["id"], x["side"]): x.get("eff") for x in K}
    del K
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in R:
        if r["market"] != "ml" or not 100 <= r["odds"] <= 350 or r["mn"] < 4 or r["trap"] or r["fighting"]:
            continue
        if (r.get("dog_read") or -99) < 4 or r["gid"] in lockg or r["kind"] in ("stackplay", "floor"):
            continue
        if min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] - 1 <= 0:
            continue
        e = r.get("eff_p") if r.get("eff_p") is not None else eff.get((r["gid"], r["side"]))
        r["effgap"] = None if e is None else e - r["p_market"]
        pool[r["date"]].append(r)
    out = []
    for d, v in pool.items():
        seen = set()
        for i, r in enumerate(sorted(v, key=lambda r: (-r["dog_read"], -(r["effgap"] or 0)))):
            if r["gid"] in seen:
                continue
            seen.add(r["gid"])
            r["rslot"] = len(seen) - 1
            out.append(r)
    return out


if __name__ == "__main__":
    R = L.load(L.OLD)
    S = slot(R)
    top = [r for r in S if r["rslot"] < 2]
    real = {(r["gid"], r["side"]) for r in R if r["kind"] == "ncaabplay" and r["odds"] > 0}
    got = {(r["gid"], r["side"]) for r in top}
    gap = {(r["gid"], r["side"]) for r in R if r["kind"] == "gap"}
    print(f"real slot dogs {len(real)}, rebuilt top-2 {len(got)}, overlap {len(real & got)}, real missed {len(real - got)}, "
          f"rebuilt extra {len(got - real)} (of them gap twins {len((got - real) & gap)})")
