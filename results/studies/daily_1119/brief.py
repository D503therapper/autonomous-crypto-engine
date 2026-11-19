"""One short line per cell of a study's *_out.txt: ALL / TRAIN / HELD and how many held seasons were up.
usage: python brief.py s3_nfl_surface [n=30] [z=1.6]   (n = the smallest cell shown; z = only cells with |z| at least this,
the 'A0' base rows always shown; the placebo lines only for the cells shown)"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
cell = re.compile(r"\s*(\d+)\s+([+-][\d.]+)% z([+-][\d.]+)")
opt = dict(a.split("=") for a in sys.argv[1:] if "=" in a)
minn, minz = int(opt.get("n", 0)), float(opt.get("z", 0))
for tag in [a for a in sys.argv[1:] if "=" not in a]:
    shown = set()
    for line in open(os.path.join(HERE, tag + "_out.txt")):
        if " ALL " not in line or " | TRAIN " not in line:
            if line.strip().startswith("placebo"):
                nm = line.strip()[8:].split(" vs ")[0]
                if not minz or nm in shown:
                    print(line.rstrip()[:230])
            elif line.startswith("S") or "pct" in line:
                print(line.rstrip()[:230])
            continue
        name = line[:line.index(" ALL ")].rstrip()
        parts = line[line.index(" ALL "):].split(" | ")
        a = cell.match(parts[0].replace("ALL", "", 1))
        t = cell.match(parts[1].replace("TRAIN", "", 1).split(" up ")[0])
        up = parts[1].split(" up ")[1].strip() if " up " in parts[1] else ""
        hd = cell.match(parts[-1].replace("HELD", "", 1))
        seas = [cell.match(re.sub(r"^\d{4}", "", p.strip())) for p in parts[2:-1]]
        hu = sum(1 for s in seas if s and float(s.group(2)) > 0)
        hn = sum(1 for s in seas if s)
        if not a or int(a.group(1)) < minn:
            continue
        if minz and abs(float(a.group(3))) < minz and "A0" not in name and "control" not in name:
            continue
        shown.add(name)
        f = lambda m: f"{float(m.group(2)):+6.1f}% on {int(m.group(1)):5d} z{float(m.group(3)):+5.2f}" if m else "      -              "
        print(f"{name[:66]:66s} ALL {f(a)} | TRAIN {f(t)} up {up:5s} | HELD {f(hd)} up {hu}/{hn}")
