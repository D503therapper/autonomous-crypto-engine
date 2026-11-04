"""The NHL game-by-game funnel of the last 8 board days, one line a dog, from the dry-run dumps."""
import glob
import re
import os

D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/vol"
files = sorted(glob.glob(D + "/dry_2026-*.txt")) + [D + "/dry_1104.txt"]
for f in files:
    day = os.path.basename(f)[4:-4]
    txt = open(f).read()
    body = txt.split("==== EVERY")[1] if "==== EVERY" in txt else ""
    print(f"\n{day}")
    for block in body.split("\n\n"):
        lines = block.strip().split("\n")
        if not lines or not lines[0].startswith("NHL "):
            continue
        head = lines[0]
        m = re.match(r"NHL (.+?) ([+-]\d+) vs (.+?) \((home|away)\)(.*)", head)
        if not m:
            continue
        team, odds, opp, ha, posted = m.groups()
        if int(odds) < 100:
            continue                                         # dogs only (the favorite's line below if it posted)
        rd = re.search(r"own (\S+)\s+no-vig (\S+)", lines[1])
        own, mkt = (rd.group(1), rd.group(2)[:6]) if rd else ("?", "?")
        sc = re.search(r"score ([+-][\d.]+) vs gate (\d+) -> (\S+(?: the gate)?)", block)
        gap = re.search(r"own gap ([+-][\d.]+)", block)
        fb = re.search(r"hockey fallback: (\w+)", block)
        why = []
        if "FIGHTING" in block:
            why.append("own read under the price (fighting)")
        if "own read UNDER the no-vig" in block:
            why.append("own read under the no-vig")
        if "HURT" in block:
            why.append("hurt (2+ out)")
        if "TRAP" in block:
            why.append("trap")
        if sc and sc.group(3).startswith("under"):
            why.append(f"score {sc.group(1)} under the gate 6")
        if sc and sc.group(3) == "GATED" and "no named reason" in block:
            why.append(f"GATED {sc.group(1)} but no named reason (the 11/4 bug)")
        if fb and fb.group(1) == "fails" and gap and float(gap.group(1)) < 2:
            why.append(f"fallback needs own gap 2+ (has {gap.group(1)})")
        print(f"  {team} {odds} vs {opp} ({ha}) own {own} vs no-vig {mkt} | score {sc.group(1) if sc else '?'} | " + "; ".join(why) + (" | POSTED" if "POSTED" in posted else ""))
