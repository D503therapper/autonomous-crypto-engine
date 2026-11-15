"""11/15 FABLE FULL ENGINE AUDIT - S3b: the same rule check as S3 on the 11/13 all-sports replay board
(~/.cache/d503_leans1113/rows - every board day 2018-26, every sport, the 11/13 code with every date gate open; rows
streamed). A unit play outside -150 / +350, a non-moneyline unit play, a plus-money Lock, both sides of a game, a unit
play the own read is fighting / on a trap, a size its kind never carries.
Run from the repo root:  python results/studies/audit_1115/s3b_replay_invariants_all.py"""
import glob, json, os, sys
from collections import Counter, defaultdict

ROWS = os.path.join(os.path.expanduser("~"), ".cache", sys.argv[1] if len(sys.argv) > 1 else "d503_leans1113", "rows", "*.jsonl")


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def main():
    bad, kinds, sizes = defaultdict(list), Counter(), defaultdict(Counter)
    by_game = defaultdict(set)
    plus_lock = []
    n = rows = 0
    keys = None
    for fn in sorted(glob.glob(ROWS)):
        with open(fn) as f:
            for ln in f:
                rows += 1
                if '"kind": null' in ln:
                    continue
                r = json.loads(ln)
                k = r.get("kind")
                if not k:
                    continue
                keys = keys or sorted(r)
                n += 1
                u = r.get("units")
                lg = r.get("league") or str(r.get("gid") or r.get("game_id") or "").split(":")[0]
                r["league"] = lg
                sized = u is not None                        # (the 11/13 rows carry no size - the size checks skip them)
                u = u if sized else 0.5
                kinds[(lg, k)] += 1
                sizes[k][u] += 1
                o = r.get("odds") or 0
                unit = (u or 0) > 0
                key = (r["date"], r.get("gid") or r.get("game_id"), k, r["side"], r["market"])
                if key in by_game[(r["date"], r.get("gid") or r.get("game_id"))]:
                    continue                                 # (a row written twice by a resumed chunk)
                by_game[(r["date"], r.get("gid") or r.get("game_id"))].add(key)
                if unit and r["market"] == "ml" and not -150 <= o <= 350:
                    bad["a unit play outside -150..+350"].append((r["date"], lg, r["team"], o, k, u))
                if unit and r["market"] != "ml" and k not in ("night", "solo", "stack", "stackplay"):
                    bad["a unit play that is not a moneyline"].append((r["date"], lg, r["team"], r["market"], k, u))
                if k == "lock" and r["market"] == "ml" and o >= 100:
                    plus_lock.append(r)
                if k == "lock" and r["market"] == "ml" and -119 <= o <= -101:
                    bad["a Lock at -119..-101"].append((r["date"], lg, r["team"], o, u))
                if k in ("dog", "dogplay", "floor", "gap") and o < 100:
                    bad["a dog kind on a favorite"].append((r["date"], lg, r["team"], o, k))
                if unit and r.get("fighting") and k not in ("stackplay", "gap", "ncaabplay"):   # (their own reads)
                    bad["a unit play the own read is fighting"].append((r["date"], lg, r["team"], k, o))
                if unit and r.get("trap"):
                    bad["a unit play on a trap"].append((r["date"], lg, r["team"], k, o))
                if unit and k == "dog" and lg == "ncaab":
                    bad["a college hoops Dog of the Day"].append((r["date"], r["team"], o, u))
                if sized and unit and u > 2 and k != "lock":
                    bad["a size past 2u"].append((r["date"], lg, r["team"], k, u, o))
                if sized and unit and k == "lock" and u > 2:
                    bad["a Lock past 2u"].append((r["date"], lg, r["team"], u, o))
    for key, v in by_game.items():
        sides = {x[3] for x in v if x[4] in ("ml", "spread") and x[2] not in ("lean",)}
        if len(sides) > 1:
            bad["picks on both sides of a game"].append((key, sorted(v)))
    print(f"{rows} rows read, {n} the board made a pick of")
    print("row keys:", keys)
    print("kinds:", dict(sorted(kinds.items(), key=lambda x: str(x[0]))))
    for k, c in sizes.items():
        print(f"  {k}: sizes {dict(sorted(c.items(), key=lambda x: str(x[0])))}")
    w = sum(1 for r in plus_lock if r.get("result") == "won")
    pr = sum((dec(r["odds"]) - 1) if r.get("result") == "won" else -1 for r in plus_lock if r.get("result") in ("won", "lost"))
    by = Counter((r["league"], r["date"][:4]) for r in plus_lock)
    print(f"PLUS-MONEY LOCKS: {len(plus_lock)}  won {w}  flat {pr:+.1f}u  by league / year {dict(sorted(by.items()))}")
    if not bad:
        print("NO OTHER RULE BROKEN on any replay row")
    for k, v in bad.items():
        print(f"BROKEN - {k}: {len(v)}")
        for x in v[:6]:
            print("     ", x)


if __name__ == "__main__":
    main()
