"""Compact view of a *_out.json: name | ALL n roi z | TRAIN roi up | 2023 2024 2025 roi | HELD n roi.
python view.py s1_out.json [substring] [min n]"""
import json
import sys

res = json.load(open(sys.argv[1]))
pat = sys.argv[2] if len(sys.argv) > 2 else ""
minn = int(sys.argv[3]) if len(sys.argv) > 3 else 0


def f(x, z=False):
    return (f"{x['roi'] * 100:+5.1f}" + (f" z{x['z']:+.1f}" if z else "")) if x else "   - "


for k, r in res.items():
    if pat and pat not in k:
        continue
    if not r or not r["all"] or r["all"]["n"] < minn:
        continue
    held = " ".join(f(r.get(h)) for h in ("2023", "2024", "2025"))
    print(f"{k[:72]:72s} A{r['all']['n']:5d} {f(r['all'], True)} | T {f(r['train'])} {r['train_up']} | {held} | "
          f"H{(r['held_all'] or {}).get('n', 0):5d} {f(r['held_all'])}")
