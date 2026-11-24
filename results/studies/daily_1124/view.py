"""One short line a cell from a *_out.txt: name | ALL n roi z | TRAIN roi (seasons up) | HELD roi | each held season."""
import re
import sys

for fn in sys.argv[1:]:
    for ln in open(fn):
        if " ALL " not in ln or "|" not in ln:
            print(ln.rstrip()[:200])
            continue
        name, rest = ln.split(" ALL ", 1)
        parts = [p.strip() for p in rest.split("|")]

        def f(p):
            m = re.search(r"(\d+)\s+([+-][\d.]+)%\s+z\s*([+-][\d.]+)", p)
            return (m.group(1), m.group(2), m.group(3)) if m else None
        a = f(parts[0])
        tr = f(parts[1])
        up = re.search(r"up (\d+/\d+)", parts[1])
        he = f(parts[-1])
        seas = " ".join(f"{p.split()[0][2:]}:{f(p)[1]}/{f(p)[0]}" for p in parts[2:-1] if f(p))
        print(f"{name.strip()[:74]:74s} {a[0]:>6s} {a[1]:>6s}% z{a[2]:>5s} | T {tr[1] if tr else '-':>6s}%/{tr[0] if tr else '-':<5s} {up.group(1) if up else '':4s}"
              f"| H {he[1] if he else '-':>6s}%/{he[0] if he else '-':<5s}| {seas}")
