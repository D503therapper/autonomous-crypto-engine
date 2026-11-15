"""11/15 FABLE FULL ENGINE AUDIT - S3: the board's own rules checked on every replay row at hand (the 11/14 football
replay board, ~/.cache/d503_fb1114/rows - 958 football board days 2018-26 on the 11/14 code, every date gate open):
does any unit play break a standing rule? (the -150 / +350 band, a moneyline-only unit play, one pick a game and never
both sides, the size its kind may carry, a Lock that is a dog, a dog that fails the football money check.)
Run from the repo root:  python results/studies/audit_1115/s3_replay_invariants.py"""
import glob, json, os
from collections import Counter, defaultdict

ROWS = os.path.join(os.path.expanduser("~"), ".cache", "d503_fb1114", "rows", "*.jsonl")
SIZES = {"lock": {0.5, 1.0, 2.0}, "dog": {0.5, 1.0, 2.0}, "play": {0.5, 1.0}, "gap": {1.0, 2.0}, "dogplay": {0.5}, "floor": {0.5},
         "solo": {0.5, 1.0, 2.0}, "night": {0, 0.0, 0.5, 1.0, 2.0}}


def main():
    bad, kinds, sizes = defaultdict(list), Counter(), defaultdict(Counter)
    by_game = defaultdict(list)
    n = 0
    for fn in sorted(glob.glob(ROWS)):
        with open(fn) as f:
            for ln in f:
                if '"kind": null' in ln and '"lean": false' in ln:
                    continue
                r = json.loads(ln)
                k = r.get("kind")
                if not k:
                    continue
                n += 1
                u = r.get("units")
                kinds[k] += 1
                sizes[k][u] += 1
                o = r.get("odds") or 0
                unit = (u or 0) > 0
                by_game[(r["date"], r["gid"])].append((k, r["side"], r["market"], u))
                if unit and r["market"] == "ml" and not -150 <= o <= 350:
                    bad["a unit play outside -150..+350"].append((r["date"], r["team"], o, k, u))
                if unit and r["market"] != "ml" and k not in ("night", "solo"):
                    bad["a unit play that is not a moneyline"].append((r["date"], r["team"], r["market"], k, u))
                if k == "lock" and o >= 100:
                    bad["a Lock that is a dog"].append((r["date"], r["team"], o))
                if k in ("dog", "dogplay", "floor", "gap") and o < 100:
                    bad["a dog kind on a favorite"].append((r["date"], r["team"], o, k))
                if k in SIZES and u not in SIZES[k]:
                    bad["a size its kind never carries"].append((r["date"], r["team"], k, u, o))
                if k in ("dog", "dogplay") and r.get("dog_own_ok") is False:
                    bad["a football Dog that fails the money check"].append((r["date"], r["team"], k, o))
                if unit and r.get("fighting"):
                    bad["a unit play the own read is fighting"].append((r["date"], r["team"], k, o))
                if unit and r.get("trap"):
                    bad["a unit play on a trap"].append((r["date"], r["team"], k, o))
    for key, v in by_game.items():
        sides = {x[1] for x in v if x[2] in ("ml", "spread") and (x[3] or 0) > 0}
        if len(sides) > 1:
            bad["unit plays on both sides of a game"].append((key, v))
        ks = [x[0] for x in v if (x[3] or 0) > 0 and x[2] == "ml"]
        if len(ks) > 1 and not ("gap" in ks or "night" in ks):
            bad["two moneyline unit plays on one game"].append((key, v))
    print(f"{n} football replay rows the board made a pick of; kinds: {dict(kinds)}")
    for k, c in sizes.items():
        print(f"  {k}: sizes {dict(sorted(c.items(), key=lambda x: str(x[0])))}")
    if not bad:
        print("NO RULE BROKEN on any replay row")
    for k, v in bad.items():
        print(f"BROKEN - {k}: {len(v)}")
        for x in v[:8]:
            print("     ", x)


if __name__ == "__main__":
    main()
