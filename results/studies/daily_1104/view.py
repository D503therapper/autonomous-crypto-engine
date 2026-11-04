"""Compact view of a study's *_out.json: python view.py s1 [substring ...] - one short line per cell."""
import json, os, sys

d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), sys.argv[1] + "_out.json")))
subs = sys.argv[2:]


def f(x):
    return f"{x['n']:4d} {x['roi']*100:+6.1f}%" if x else "   -        "


for k, r in d.items():
    if subs and not all(s in k for s in subs):
        continue
    if not r:
        continue
    held = [h for h in r if h.isdigit()]
    print(f"{k[:70]:70s} ALL {f(r['all'])} z{r['all']['z']:+.1f} | TR {f(r['train'])} {r['train_up']} | "
          + " ".join(f"{h[2:]}:{f(r[h])}" for h in held) + f" | HELD {f(r['held_all'])}")
