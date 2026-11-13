"""11/13 FABLE - THE TWO LEAN CELLS THAT BEAT THE PRICE IN BOTH HALVES, TAKEN APART.
  1. the SPREAD lean whose studied weights add to +0.05 or more (s1: +10.0% on 879, train +5.0% / held +15.3%)
     - is it the ½u spread STACK play (wired 11/12) under another name? the dose, the stack's share, what is left
       once the stack's own sides are out, the weights that are NOT in the stack (the 11/12 CBB10 / deep-program ones)
  2. the MONEYLINE favorite lean at -150..-130 (s1: +4.3% on 622 as posted, +2.8% on 1,260 in the pool)
     - against the right placebo (every college hoops favorite in the same band, not every moneyline side), and
       against the favorite SLOT (the ½u unit play that already takes the best of that band)
Rows: funnel4.py's. Usage: python results/studies/leans_1113/s2_weights.py > results/studies/leans_1113/s2_weights.out"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1_leans as S            # noqa: E402  (prints its own table first - cut it with `| sed -n '/^#### S2/,$p'`)

R, rec = S.R, S.rec
print("\n#### S2")
SP = [r for r in R if r["market"] == "spread"]
for r in SP:
    r["w"] = round((r.get("rank_p") or r["p"]) - r["p"], 4)
    r["st"] = r.get("stack") or 0.0
    r["other"] = round(r["w"] - r["st"], 4)
ok = lambda r: r["lean_any"] or r["kind"] == "stackplay"        # noqa: E731  (the lean pool + the sides the stack play took)

print("==== 1. THE SPREAD SIDE WITH STUDIED WEIGHTS OF +0.05 OR MORE")
A = [r for r in SP if r["w"] >= 0.05 - 1e-9]
print(" a. every college hoops spread side by the weights on it (no lean rule - the raw dose)")
for lo, hi in ((-9, -0.05), (-0.05, -0.03), (-0.03, -0.001), (-0.001, 0.001), (0.001, 0.03), (0.03, 0.05), (0.05, 0.06), (0.06, 0.08), (0.08, 9)):
    rec(f"weights {lo:+.2f}..{hi:+.2f}" if abs(lo) < 9 and abs(hi) < 9 else f"weights {'under' if lo < -1 else 'over'} {hi if lo < -1 else lo:+.2f}",
        [r for r in SP if lo - 1e-9 <= r["w"] < hi - 1e-9])
print(" b. +0.05 or more: what the board does with it today")
rec("every side at +0.05+", A)
rec("  taken by the ½u STACK play (2 a night)", [r for r in A if r["kind"] == "stackplay"])
rec("  a lean in the pool (the stack play full, or not a stack side)", [r for r in A if r["lean_any"]])
rec("  a lean the board shows", [r for r in A if r["lean"]])
rec("  neither (the game is another play's / the lean rule passed)", [r for r in A if not r["lean_any"] and r["kind"] != "stackplay"])
print(" c. +0.05 or more, by where the weights come from")
rec("the STACK alone is +0.05+ (the wired play's own rule)", [r for r in A if r["st"] >= 0.05 - 1e-9])
rec("  ...and a 3rd+ stack side of the night (the play's cap of 2 kept it a lean)", [r for r in A if r["st"] >= 0.05 - 1e-9 and r["kind"] != "stackplay" and r["lean_any"]])
rec("the stack is UNDER +0.05 - the other weights carry it", [r for r in A if r["st"] < 0.05 - 1e-9])
rec("  ...no stack weight at all (CBB10 / deep / cover run / coach / season)", [r for r in A if r["st"] == 0])
rec("  ...the pool's leans among them", [r for r in A if r["st"] < 0.05 - 1e-9 and r["lean_any"]])
rec("the non-stack weights +0.03 or more (any stack)", [r for r in SP if r["other"] >= 0.03 - 1e-9])
rec("the non-stack weights +0.05 or more", [r for r in SP if r["other"] >= 0.05 - 1e-9])
rec("the non-stack weights -0.03 or worse (the faded side)", [r for r in SP if r["other"] <= -0.03 + 1e-9])
print(" d. +0.05 or more by season / phase / side (every side, lean or stack play)")
B = [r for r in A if ok(r)]
rec("every +0.05+ side the board plays or leans", B)
for s in sorted({r["season"] for r in B}):
    X = [r for r in B if r["season"] == s]
    print(f"      {s}: {sum(r['win'] for r in X)}-{sum(not r['win'] for r in X)}  {S.roi(X):+.1f}%   (stack under +0.05: "
          f"{sum(r['win'] for r in X if r['st'] < 0.05 - 1e-9)}-{sum(not r['win'] for r in X if r['st'] < 0.05 - 1e-9)} {S.roi([r for r in X if r['st'] < 0.05 - 1e-9]):+.1f}%)")
for ph in ("Nov", "Dec", "Jan-Apr (league play)"):
    rec(f"  {ph}", [r for r in B if S.phase(r) == ph])
rec("  early window Nov 1 - Dec 15", [r for r in B if S.early(r)])
rec("  early window, a team under 5 games in", [r for r in B if S.early(r) and r["mn"] < 5])
rec("  dogs (getting points)", [r for r in B if (r["line"] or 0) > 0])
rec("  favorites (laying points)", [r for r in B if (r["line"] or 0) < 0])
rec("  home", [r for r in B if r["home"] and str(r["neutral"]) != "1"])
rec("  road", [r for r in B if not r["home"] and str(r["neutral"]) != "1"])
rec("  the price -110 or better", [r for r in B if r["odds"] >= -110])
rec("  the price -111 or worse", [r for r in B if r["odds"] <= -111])
print(" e. the leans the stack play does NOT already cover (stack under +0.05), +0.05+ total, in the lean pool - THE ONLY NEW BET HERE")
N = [r for r in A if r["st"] < 0.05 - 1e-9 and r["lean_any"]]
rec("the new cell", N)
rec("  2018-20 (before the team box: no stack weight exists)", [r for r in N if r["season"] <= 2020])
rec("  2021-22", [r for r in N if 2021 <= r["season"] <= 2022])
rec("  2023-26", [r for r in N if r["season"] >= 2023])
for ph in ("Nov", "Dec", "Jan-Apr (league play)"):
    rec(f"  {ph}", [r for r in N if S.phase(r) == ph])
rec("  Feb-Mar only (the league leader on the road / the home side across)", [r for r in N if r["md"][:2] in ("02", "03")])
rec("  NOT Feb-Mar", [r for r in N if r["md"][:2] not in ("02", "03")])

print("\n==== 2. THE MONEYLINE FAVORITE LEAN AT -150..-130")
ML = [r for r in R if r["market"] == "ml"]
band = [r for r in ML if -150 <= r["odds"] <= -130]
rec("every college hoops favorite -150..-130 (the fair base)", band, pool=band, show_open=True)
rec("  the lean pool's (the engine has it winning, not fighting)", [r for r in band if r["lean_any"]], pool=band, show_open=True)
rec("  a lean the board shows", [r for r in band if r["lean"]], pool=band, show_open=True)
rec("  NOT in the lean pool and not a unit play", [r for r in band if not r["lean_any"] and not r["kind"]], pool=band, show_open=True)
rec("  the unit plays the board made of that band (Lock / slot / play)", [r for r in band if r["kind"]], pool=band, show_open=True)
L = [r for r in band if r["lean_any"]]
print(" by season (the pool's): " + "  ".join(f"{s}: {sum(r['win'] for r in L if r['season'] == s)}-{sum(not r['win'] for r in L if r['season'] == s)} {S.roi([r for r in L if r['season'] == s]):+.1f}%" for s in sorted({r['season'] for r in L})))
rec("  the pool's: home", [r for r in L if r["home"] and str(r["neutral"]) != "1"], pool=band, show_open=True)
rec("  the pool's: road", [r for r in L if not r["home"] and str(r["neutral"]) != "1"], pool=band, show_open=True)
rec("  the pool's: neutral floor", [r for r in L if str(r["neutral"]) == "1"], pool=band, show_open=True)
rec("  the pool's: both teams 4+ games", [r for r in L if r["mn"] >= 4], pool=band, show_open=True)
rec("  the pool's: a team under 4 games", [r for r in L if r["mn"] < 4], pool=band, show_open=True)
rec("  the pool's: win read 58%+", [r for r in L if r["p"] >= 0.58], pool=band, show_open=True)
rec("  the pool's: weighed read over the price (w_p)", [r for r in L if r.get("w_p") and r["w_p"] * r["dec"] > 1], pool=band, show_open=True)
rec("  the pool's: own read over the price", [r for r in L if (r.get("edge_own") or -1) > 0], pool=band, show_open=True)
rec("  the pool's: own read UNDER the price", [r for r in L if (r.get("edge_own") or -1) <= 0], pool=band, show_open=True)
rec("  the fill leans only", [r for r in L if r["fill_any"]], pool=band, show_open=True)
print("\ncells:", S.CELLS[0])
