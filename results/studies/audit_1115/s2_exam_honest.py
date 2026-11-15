"""11/15 FABLE FULL ENGINE AUDIT - S2: the exam-scan dogs (S1's walk-forward rows, the +4..8 band) joined to the 11/14
football replay board's rows (~/.cache/d503_fb1114/rows - one row a football moneyline candidate on today's code, at the
close): does the HONEST weighed read (sports.weighed_dog_beats - the no-vig close + the dog score's STUDY part, over the
real price) separate the exam dogs the way it separates the board's football dogs (11/12 daily: kept +13.0%, dropped
-11.8%)? And the ONE VOICE check as it runs today (the board's read for the side not under the price - for a college
dog that read is the close + the old fit's home-dog tilt).
Run from the repo root after s1:  python results/studies/audit_1115/s2_exam_honest.py"""
import glob, json, os, pickle, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1_exam_scan as s1

ROWS = os.path.join(os.path.expanduser("~"), ".cache", "d503_fb1114", "rows", "*.jsonl")


def board():
    out = {}
    for fn in sorted(glob.glob(ROWS)):
        with open(fn) as f:
            for ln in f:
                if '"market": "ml"' not in ln or '"league": "ncaaf"' not in ln:
                    continue
                r = json.loads(ln)
                if r.get("odds", 0) >= 100:
                    out[(r["gid"], r["side"])] = {k: r.get(k) for k in ("wdb", "dog_score", "dog_base", "own_beats", "edge_own",
                                                                         "p_market", "dec", "dog_own_ok", "fighting", "p", "w_p")}
    return out


def main():
    rs = pickle.load(open(os.path.join(s1.CACHE, "s1_ncaaf.pkl"), "rb"))
    b = board()
    print("board football dog rows:", len(b))
    for price in ("early", "close"):
        B = [r for r in rs if r["price"] == price and 0.04 <= r["gap"] < 0.08]
        J = [dict(r, **b[(r["id"], r["side"])]) for r in B if (r["id"], r["side"]) in b]
        print(f"\n=== the +4..8 band at the {price} price: {len(B)} dogs, {len(J)} on the replay board ===")
        s1.cell("joined, flat", J)
        s1.cell("HONEST weighed read over the price (weighed_dog_beats)", [r for r in J if r["wdb"]])
        s1.cell("  ... not", [r for r in J if not r["wdb"]])
        s1.cell("the board's old own read over the price (edge_own > 0)", [r for r in J if (r["edge_own"] or 0) > 0])
        s1.cell("  ... not", [r for r in J if not (r["edge_own"] or 0) > 0])
        s1.cell("the dog score's study part 0+", [r for r in J if (r["dog_score"] or 0) - (r["dog_base"] or 0) >= 0])
        s1.cell("the dog score's study part under 0", [r for r in J if (r["dog_score"] or 0) - (r["dog_base"] or 0) < 0])
        s1.cell("HOME dog, honest read over", [r for r in J if r["wdb"] and r["side"] == "home" and not r["neutral"]])
        s1.cell("HOME dog, honest read NOT over", [r for r in J if not r["wdb"] and r["side"] == "home" and not r["neutral"]])
        s1.cell("ROAD dog, honest read over", [r for r in J if r["wdb"] and r["side"] == "away" and not r["neutral"]])
        s1.cell("ROAD dog, honest read NOT over", [r for r in J if not r["wdb"] and r["side"] == "away" and not r["neutral"]])
    # every college dog on the board at the close, for the base
    A = [r for r in rs if r["price"] == "close"]
    J = [dict(r, **b[(r["id"], r["side"])]) for r in A if (r["id"], r["side"]) in b]
    print(f"\n=== every college dog +100..+280 at the close on the board ({len(J)}) ===")
    s1.cell("all", J)
    s1.cell("honest weighed read over the price", [r for r in J if r["wdb"]])
    s1.cell("  ... and the raw read +4..8 over (the exam band)", [r for r in J if r["wdb"] and 0.04 <= r["gap"] < 0.08])
    s1.cell("  ... and the raw read NOT in the band", [r for r in J if r["wdb"] and not 0.04 <= r["gap"] < 0.08])


if __name__ == "__main__":
    main()
