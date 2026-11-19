"""S0 - build the rig's caches and say how good the 8 AM projection is (2016-26)."""
import collections
import glib

say = glib.Tee(glib.HERE + "/s0_build.out")
G = glib.goalies()
S = glib.games()
say(f"goalie team-games {len(G)}; game sides {len(S)}; with the paid morning price {sum(1 for s in S if s['dec_m'])}; "
    f"with ESPN's open {sum(1 for s in S if s['dec_o'])}")
say("sides by season:", dict(sorted(collections.Counter(s["season"] for s in S).items())))
res = collections.defaultdict(lambda: [0, 0])
for s in S:
    g = s["g_me"]
    if not g["proj"]:
        continue
    era = "2023-26" if s["season"] >= "2023-24" else "2016-23"
    for k in (f"{era} all", f"{era} {'b2b night 2' if g['b2b'] else 'rested'}"):
        res[k][0] += g["proj"] == g["actual"]
        res[k][1] += 1
    if g["n1"]:
        k = f"{era} the #1 started ({'b2b' if g['b2b'] else 'rested'})"
        res[k][0] += g["n1"] == g["actual"]
        res[k][1] += 1
say("the 8 AM projection (sports_players.projected_starter) vs who started:")
for k in sorted(res):
    a, n = res[k]
    say(f"  {k:40s} {a:6d}/{n:6d} = {a / n:.1%}")
