"""11/13 FABLE - THE FIX, REPLAYED: the college hoops leans the board would show under the lean rule as it ran 11/13
(lean) against the same boards with the fix on (lean_new: a college hoops spread lean needs a studied weight FOR the
side - sports.lean_spread_bare). Rows: funnel4.py's.
Usage: python results/studies/leans_1113/s3_fix.py > results/studies/leans_1113/s3_fix.out"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1_leans as S            # noqa: E402  (prints its own table first - cut it with `| sed -n '/^#### S3/,$p'`)

R, rec = S.R, S.rec
print("\n#### S3")
for key, title in (("lean", "THE LEAN RULE AS IT RAN 11/13"), ("lean_new", "WITH THE FIX (no dial-only college hoops spread lean)")):
    L = [r for r in R if r.get(key)]
    days = collections.Counter(r["date"] for r in L)
    alld = {r["date"] for r in R}
    print(f"\n==== {title}: {len(L)} graded college hoops leans; days with 0 / 1 / 2: "
          f"{len(alld) - len(days)} / {sum(v == 1 for v in days.values())} / {sum(v >= 2 for v in days.values())}")
    rec("ALL", L, pool=R)
    rec("moneyline", [r for r in L if r["market"] == "ml"], show_open=True)
    rec("spread", [r for r in L if r["market"] == "spread"])
    rec("spread: dog getting 15+", [r for r in L if r["market"] == "spread" and (r["line"] or 0) >= 15])
    rec("Nov", [r for r in L if S.phase(r) == "Nov"], pool=R)
    rec("Dec", [r for r in L if S.phase(r) == "Dec"], pool=R)
    rec("Jan-Apr (league play)", [r for r in L if S.phase(r) == "Jan-Apr (league play)"], pool=R)
    rec("EARLY WINDOW Nov 1 - Dec 15", [r for r in L if S.early(r)], pool=R)
    rec("early window, a team under 5 games in", [r for r in L if S.early(r) and r["mn"] < 5], pool=R)
    rec("Nov 1-14", [r for r in L if "11-01" <= r["md"] <= "11-14"], pool=R)
    print(" by season: " + "  ".join(f"{s}: {sum(r['win'] for r in L if r['season'] == s)}-{sum(not r['win'] for r in L if r['season'] == s)} {S.roi([r for r in L if r['season'] == s]):+.1f}%"
                                      for s in sorted({r['season'] for r in L})))
old = {(r["gid"], r["side"], r["market"]) for r in R if r.get("lean")}
new = {(r["gid"], r["side"], r["market"]) for r in R if r.get("lean_new")}
print(f"\n==== WHAT CHANGED: {len(old - new)} leans come off, {len(new - old)} take their place, {len(old & new)} stay")
rec("the leans that come off", [r for r in R if r.get("lean") and not r.get("lean_new")], pool=R)
rec("  ...the spread dogs getting 25+ among them", [r for r in R if r.get("lean") and not r.get("lean_new") and r["market"] == "spread" and (r["line"] or 0) >= 25])
rec("the leans that take their place", [r for r in R if r.get("lean_new") and not r.get("lean")], pool=R)
rec("  ...moneyline", [r for r in R if r.get("lean_new") and not r.get("lean") and r["market"] == "ml"], show_open=True)
rec("  ...spread (a studied weight on it)", [r for r in R if r.get("lean_new") and not r.get("lean") and r["market"] == "spread"])
P = [r for r in R if r.get("lean_any_new")]
print("\n==== THE POOL WITH THE FIX (its side in every game)")
rec("ALL", P, pool=R)
rec("moneyline", [r for r in P if r["market"] == "ml"], show_open=True)
rec("spread", [r for r in P if r["market"] == "spread"])
rec("spread: studied weights under +0.03", [r for r in P if r["market"] == "spread" and (r.get("sw") or 0) < 0.03 - 1e-9])
rec("spread: studied weights +0.03..+0.05", [r for r in P if r["market"] == "spread" and 0.03 - 1e-9 <= (r.get("sw") or 0) < 0.05 - 1e-9])
rec("spread: studied weights +0.05 or more", [r for r in P if r["market"] == "spread" and (r.get("sw") or 0) >= 0.05 - 1e-9])
print("\ncells:", S.CELLS[0])
