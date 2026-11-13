"""11/13 EARLY-SEASON COLLEGE HOOPS - s1: the early window on the 11/13 lean funnel's rows (today's code, the board
re-built at the close each day 2018-26). The early window = either team under 4 regular-season games in (mn < 4).
Adds K's walk-forward EFFICIENCY chance (eff - last season's final ratings carried in as the prior) by (game, side).
Caches the joined rows to ~/.cache/d503_early1113/rows.pkl for s2+."""
import os, pickle, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E

OUT = os.path.join(os.path.expanduser("~"), ".cache", "d503_early1113")
os.makedirs(OUT, exist_ok=True)
F = E.load_f()
K = pickle.load(open(E.KPK, "rb"))
eff = {(x["id"], x["side"]): x.get("eff") for x in K}
gnk = {(x["id"], x["side"]): (x.get("gn"), x.get("ogn")) for x in K}
hit = 0
for r in F:
    k = (r["gid"], r["side"])
    r["eff_p"] = eff.get(k)
    r["kgn"] = gnk.get(k)
    hit += r["eff_p"] is not None
pickle.dump(F, open(os.path.join(OUT, "rows.pkl"), "wb"))
print(f"rows {len(F)}, eff joined {hit}")
ml = [r for r in F if r["market"] == "ml"]
print("ml rows by season:", sorted(Counter(r["season"] for r in ml).items()))
print("ml rows by mn (min games in):", sorted(Counter(min(r["mn"], 10) for r in ml).items()))
print("eff joined by season:", sorted(Counter(r["season"] for r in ml if r["eff_p"] is not None).items()))
print("games_in vs K gn (early sample):", Counter((r["games_in"], (r["kgn"] or (None,))[0]) for r in ml if r["mn"] < 4).most_common(12))
print("kinds in early window:", Counter(r["kind"] for r in F if r["mn"] < 4).most_common())
print("kinds overall:", Counter(r["kind"] for r in F).most_common())
