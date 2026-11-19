"""S3 - THE HINDSIGHT TRAP in "who started", and the cell with it taken out.
Our box scores keep ONE goalie a team-game: the man who faced the MOST shots. When a starter is pulled early (his team
is getting run - so the other side is winning) the reliever can face more shots and our file calls HIM the starter:
"the favorite's backup started" then holds games the favorite's #1 started and got chased - dog wins by construction.
The fix that needs no other source: only count games where the man on file faced 24+ shots (a reliever almost never
does - he'd have to come in inside the first ten minutes), for #1s and backups alike, and compare inside that.
Also the honest 8 AM version: what the PROJECTION said (no hindsight at all)."""
import glib
from glib import line, st

say = glib.Tee(glib.HERE + "/s3_leak.out")
S = glib.games()
for r in S:
    me, op = r["g_me"], r["g_op"]
    r["rm"] = None if not me["n1"] else "n1" if me["actual"] == me["n1"] else "bk"
    r["ro"] = None if not op["n1"] else "n1" if op["actual"] == op["n1"] else "bk"
    r["pm"] = None if not me["n1"] or not me["proj"] else "n1" if me["proj"] == me["n1"] else "bk"
    r["po"] = None if not op["n1"] or not op["proj"] else "n1" if op["proj"] == op["n1"] else "bk"
    r["sa_o"], r["sa_m"] = float(op["sa"] or 0), float(me["sa"] or 0)
    r["b2b"], r["ob2b"] = me["b2b"], op["b2b"]
D = [r for r in S if 100 <= r["odds_c"] <= 350]
F = [r for r in S if -250 <= r["odds_c"] <= -101]

say("how many shots the man on file faced, by role (a reliever on file shows up as a short night):")
for k in ("n1", "bk"):
    xs = [r["sa_m"] for r in S if r["rm"] == k]
    say(f"  {k}: n {len(xs)}, under 20 shots {sum(x < 20 for x in xs) / len(xs):.1%}, under 24 {sum(x < 24 for x in xs) / len(xs):.1%}, "
        f"lost while under 20: {sum(1 for r in S if r['rm'] == k and r['sa_m'] < 20 and not r['won'])} of {sum(1 for r in S if r['rm'] == k and r['sa_m'] < 20)}")

for nm, P in (("DOGS +100..+350 at the close 2018-26", D), ("FAVORITES -101..-250 at the close 2018-26", F)):
    say(f"\n=== {nm}")
    for cut in (0, 24, 27):
        say(f" -- the other side's goalie on file faced {cut}+ shots" if cut else " -- every game (the trap in)")
        Q = [r for r in P if r["sa_o"] >= cut]
        line("their #1 started", [r for r in Q if r["ro"] == "n1"], say=say)
        line("their backup started", [r for r in Q if r["ro"] == "bk"], say=say)
        line("their backup, neither side on a b2b", [r for r in Q if r["ro"] == "bk" and not r["b2b"] and not r["ob2b"]], say=say)
        line("their #1, neither side on a b2b", [r for r in Q if r["ro"] == "n1" and not r["b2b"] and not r["ob2b"]], say=say)
    for cut in (0, 24):
        say(f" -- OUR goalie on file faced {cut}+ shots" if cut else " -- our goalie, every game (the trap in, the other way)")
        Q = [r for r in P if r["sa_m"] >= cut]
        line("our #1 started", [r for r in Q if r["rm"] == "n1"], say=say)
        line("our backup started", [r for r in Q if r["rm"] == "bk"], say=say)
    say(" -- NO HINDSIGHT: what the 8 AM projection said (sports_players.projected_starter)")
    line("projected: their #1", [r for r in P if r["po"] == "n1"], say=say)
    line("projected: their backup", [r for r in P if r["po"] == "bk"], say=say)
    line("projected: their backup, they are NOT on a b2b", [r for r in P if r["po"] == "bk" and not r["ob2b"]], say=say)
    line("projected: their backup, they ARE on a b2b", [r for r in P if r["po"] == "bk" and r["ob2b"]], say=say)
    line("they are on a b2b, projected their #1 anyway", [r for r in P if r["po"] == "n1" and r["ob2b"]], say=say)
    line("projected: our #1", [r for r in P if r["pm"] == "n1"], say=say)
    line("projected: our backup", [r for r in P if r["pm"] == "bk"], say=say)
    line("projected: ours #1 / theirs backup", [r for r in P if r["pm"] == "n1" and r["po"] == "bk"], say=say)
    line("projected: ours #1 / theirs backup, no b2b either side", [r for r in P if r["pm"] == "n1" and r["po"] == "bk" and not r["b2b"] and not r["ob2b"]], say=say)
    say(" -- the same projection cells at the price before the news")
    for key, lab in (("dec_m", "MORNING 2021-23"), ("dec_o", "OPEN 2023-26")):
        line(f"{lab}: projected their backup", [r for r in P if r["po"] == "bk"], key, say)
        line(f"{lab}: projected their #1", [r for r in P if r["po"] == "n1"], key, say)
