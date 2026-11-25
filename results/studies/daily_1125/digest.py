"""The short read of a *_out.txt: every cell at 80+ whose ROI sits 5+ points off its BASE cell (name | n | ROI | train /
held | the base), then the placebo lines. python results/studies/daily_1125/digest.py <file> [min gap] [min n]"""
import re
import sys

fn = sys.argv[1]
gap = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
minn = int(sys.argv[3]) if len(sys.argv) > 3 else 80


def f(p):
    m = re.search(r"(\d+)\s+([+-][\d.]+)%\s+z\s*([+-][\d.]+)", p)
    return (int(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None


rows, plc = {}, []
for ln in open(fn):
    if "placebo" in ln:
        m = re.search(r"placebo (.*?) vs (.*?): (\d+) of (\d+).*?\(cell ([+-][\d.]+)%, pool ([+-][\d.]+)% on (\d+)\)", ln)
        if m:
            plc.append(f"  placebo {m.group(3):>4s}/{m.group(4)}  {m.group(1)[:80]}  ({m.group(5)}% vs {m.group(6)}% | {m.group(2)[:40]})")
        continue
    if " ALL " not in ln or "|" not in ln:
        continue
    name, rest = ln.split(" ALL ", 1)
    parts = [p.strip() for p in rest.split("|")]
    seas = " ".join(f"{p.split()[0][2:]}:{f(p)[1]:+.0f}/{f(p)[0]}" for p in parts[2:-1] if f(p))
    rows[name.strip()] = (f(parts[0]), f(parts[1]), f(parts[-1]), seas)
for name, (a, t, hd, seas) in rows.items():
    if name.startswith("BASE") or name.startswith("TOTAL BASE") or not a or a[0] < minn:
        continue
    kind = name.rsplit(": ", 1)[1]
    base = rows.get(("TOTAL BASE every game: " if name.startswith("TOTAL") else "BASE: ") + kind)
    b = base[0][1] if base and base[0] else None
    if b is not None and abs(a[1] - b) < gap:
        continue
    print(f"{name[:86]:86s} {a[0]:5d} {a[1]:+6.1f}% z{a[2]:+5.2f} | T {t[1] if t else 0:+6.1f}/{t[0] if t else 0:<4d} H {hd[1] if hd else 0:+6.1f}/{hd[0] if hd else 0:<4d}"
          f" | base {b if b is not None else 0:+5.1f} | {seas}")
for p in plc:
    print(p)
