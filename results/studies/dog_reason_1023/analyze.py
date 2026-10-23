"""Analyze replay_dogs.py output: Dog of the Day under variants A-D, flat 1u and 10/23-plan units."""
import json, glob, collections, sys
D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/cutoff_study/"
R = [json.loads(l) for f in sorted(glob.glob(D + "r_20*.jsonl")) for l in open(f)]
print(len(R), "rows; board days", len({r["date"] for r in R}), "first", min(r["date"] for r in R), "last", max(r["date"] for r in R))
BLIND = "2025-01-01"


def season(d):
    y, m = int(d[:4]), int(d[5:7]); return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def pnl(r): return (r["dec"] - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0
def u_flat(r): return 1.0
def u_s6(r):
    if r["league"] in ("nba", "ncaab"): return 0.5
    return 2.0 if (r.get("edge_own") or 0) > 0 else 1.0


def stats(rs, uf):
    rs = [r for r in rs if r["result"] in ("won", "lost", "push")]
    if not rs: return dict(n=0, w=0, l=0, net=0, roi=0, dd=0, risk=0)
    w = sum(r["result"] == "won" for r in rs); l = sum(r["result"] == "lost" for r in rs)
    net = sum(pnl(r) * uf(r) for r in rs); risk = sum(uf(r) for r in rs)
    day = collections.defaultdict(float)
    for r in rs: day[r["date"]] += pnl(r) * uf(r)
    cum = peak = dd = 0
    for d in sorted(day): cum += day[d]; peak = max(peak, cum); dd = min(dd, cum - peak)
    # longest losing streak (bets)
    s = best = 0
    for r in sorted(rs, key=lambda r: r["date"]):
        s = s + 1 if r["result"] == "lost" else 0 if r["result"] == "won" else s; best = max(best, s)
    need = sum(1 / r["dec"] for r in rs) / len(rs)
    return dict(n=len(rs), w=w, l=l, net=net, roi=100 * net / risk, dd=dd, risk=risk, streak=best, need=100 * need)


def fmt(s): return (f"n={s['n']:3d} {s['w']}-{s['l']} ({100*s['w']/max(1,s['w']+s['l']):.1f}% vs {s.get('need',0):.1f} needed) "
                    f"{s['net']:+6.1f}u ROI {s['roi']:+5.1f}% dd {s['dd']:+5.1f}u L-streak {s.get('streak',0)}") if s["n"] else "n=0"


dogs = collections.defaultdict(dict)    # variant -> date -> row
for r in R:
    if r["variant"] != "cand" and r["kind"] == "dog":
        dogs[r["variant"]][r["date"]] = r
V = sorted(dogs)
for uname, uf in (("FLAT 1u", u_flat), ("10/23-PLAN UNITS", u_s6)):
    print(f"\n===== {uname} =====")
    for v in V:
        rs = list(dogs[v].values())
        print(f"{v}  ALL   {fmt(stats(rs, uf))}")
        print(f"   BLIND(2025+) {fmt(stats([r for r in rs if r['date'] >= BLIND], uf))}")
        bys = collections.defaultdict(list)
        for r in rs: bys[season(r["date"])].append(r)
        print("   by season: " + " | ".join(f"{k} {stats(x, uf)['w']}-{stats(x, uf)['l']} {stats(x, uf)['net']:+.1f}u" for k, x in sorted(bys.items())))
        byl = collections.defaultdict(list)
        for r in rs: byl[r["league"]].append(r)
        print("   by sport:  " + " | ".join(f"{k} {stats(x, uf)['w']}-{stats(x, uf)['l']} {stats(x, uf)['net']:+.1f}u" for k, x in sorted(byl.items())))
        if v == "A": continue
        A = dogs["A"]
        added = [r for d, r in dogs[v].items() if d not in A]
        swapped_in = [r for d, r in dogs[v].items() if d in A and A[d]["team"] != r["team"]]
        swapped_out = [A[d] for d, r in dogs[v].items() if d in A and A[d]["team"] != r["team"]]
        lost_days = [A[d] for d in A if d not in dogs[v]]
        print(f"   vs A: ADDED on no-Dog days  {fmt(stats(added, uf))}")
        print(f"         by sport: " + ", ".join(f"{k} {n}" for k, n in collections.Counter(r['league'] for r in added).most_common()))
        print(f"         blind added           {fmt(stats([r for r in added if r['date'] >= BLIND], uf))}")
        print(f"         SWAPPED IN            {fmt(stats(swapped_in, uf))}")
        print(f"         (A's dogs swapped out {fmt(stats(swapped_out, uf))})")
        print(f"         A days with no Dog now {len(lost_days)}")
        if v in ("B", "D") and uname.startswith("FLAT"):
            for r in sorted(added + swapped_in, key=lambda r: r["date"])[-12:]:
                print(f"           {r['date']} {r['league']} {r['team']} +{r['odds']} score {r['dog_score']} own {r['edge_own']} lm {r['lm']} {r['result']}")

# the population B unlocks, at the candidate level (every gated ml dog with no named reason, any rank)
C = [r for r in R if r["variant"] == "cand"]
print("\n===== CANDIDATE LEVEL (every ml dog +100..+350 on the slate, flat 1u, one row per side per board day) =====")
gated = [r for r in C if r["dog_gate"]]
for lab, sel in (("gated, has a reason (A-eligible)", lambda r: r["reasons"]), ("gated, NO named reason (B unlocks)", lambda r: not r["reasons"])):
    xs = [r for r in gated if sel(r)]
    print(f"{lab:40s} ALL {fmt(stats(xs, u_flat))}\n{'':40s} BLIND {fmt(stats([r for r in xs if r['date'] >= BLIND], u_flat))}")
    byl = collections.defaultdict(list)
    for r in xs: byl[r["league"]].append(r)
    print(f"{'':40s} " + " | ".join(f"{k} n{len(x)} {stats(x, u_flat)['roi']:+.1f}%" for k, x in sorted(byl.items())))
# only-reason-is-sharp gated dogs
sh = [r for r in gated if r["reasons"] == ["sharp money moving this way"]]
print(f"{'gated, sharp money the ONLY reason':40s} ALL {fmt(stats(sh, u_flat))}")
# the 0.04-0.08 line-move band (what C adds) among gated, otherwise reasonless
cb = [r for r in gated if not r["reasons"] and 0.04 <= r["lm"] < 0.08]
print(f"{'gated, no reason, move 0.04-0.08 (C adds)':40s} ALL {fmt(stats(cb, u_flat))}")
# line-move bands for gated dogs: does the move itself carry signal?
for lo, hi in ((-9, -0.08), (-0.08, 0), (0, 0.04), (0.04, 0.08), (0.08, 9)):
    xs = [r for r in gated if lo <= r["lm"] < hi]
    print(f"  gated, line move {lo:+.2f}..{hi:+.2f}: {fmt(stats(xs, u_flat))}")
