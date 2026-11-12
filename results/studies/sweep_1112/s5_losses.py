"""11/12 FULL SWEEP, part 1b - EVERY LOSS OF THE TWO WEEKS SORTED (10/29 -> 11/10, s1_rows.json): a bug / a stale
number, a rule that has since been cut (a leaking kind), a kind under watch, or a fair bet that lost - and what each
bucket cost. The buckets are rules written down here, not hindsight on single games:
  STALE NUMBER   an early play posted inside the first hour on the look-ahead number (the 11/11 early study's list) -
                 fixed 11/11 (the fresh-number rule)
  CUT KIND       the 🔍 college football gap play (re-cut 11/11, paused 11/12), the runner-up dog in college football /
                 the NBA (cut 11/12), the blowout early spot (paused 11/11), an NBA ½u dog past +199 (capped 11/11)
  ONE VOICE      an early play of a kind the 11/11 one-voice gate now holds most of (the NBA opening line, hammered) -
                 not a proven loser (fought plays ran flat), listed apart
  WATCH          the NBA floor (0-3; a judge at 20 from 11/12) and the other NBA dogs
  FAIR BET       everything else: a play today's rules would post again
The wins of the same buckets are netted, so a bucket's number is what the KIND cost, not just its losers.
Usage: python results/studies/sweep_1112/s5_losses.py > results/studies/sweep_1112/s5_losses.out"""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in json.load(open(os.path.join(HERE, "s1_rows.json"))) if r["date"] >= "2026-10-29"]
STALE = {("2026-10-31", "Arizona"), ("2026-10-31", "Northwestern"), ("2026-11-01", "Chargers"), ("2026-11-07", "Ole Miss")}


def bucket(r):
    k = r["kind"]
    if k.startswith("early") and (r["date"], r["team"]) in STALE and r["am"] in (215, 230, 285, 130):
        return "1 STALE NUMBER (fixed 11/11)"
    if k == "gap":
        return "2 CUT: the 🔍 college football gap play (re-cut 11/11, paused 11/12)"
    if k == "dogplay":
        return "2 CUT: the runner-up dog, college football / NBA (11/12)"
    if k == "early:blowout":
        return "2 CUT: the blowout early spot (paused 11/11)"
    if r["lg"] == "nba" and r["u"] <= 0.5 and r["am"] > 199 and not k.startswith("early"):
        return "2 CUT: an NBA ½u dog past +199 (capped 11/11)"
    if k in ("early:nba_open", "early:hammered"):
        return "3 ONE VOICE now gates it (the NBA opening line, hammered)"
    if k == "nbafloor" or (r["lg"] == "nba" and r["am"] > 0):
        return "4 WATCH: NBA dogs (the floor's judge at 20, from 11/12)"
    return "5 FAIR BET (today's rules post it again)"


by = defaultdict(list)
for r in rows:
    by[bucket(r)].append(r)
tot = sum(r["net"] for r in rows)
print(f"THE TWO WEEKS: {sum(r['won'] for r in rows)}-{sum(not r['won'] for r in rows)}, {tot:+.2f}u on {sum(r['u'] for r in rows):.1f}u")
for b in sorted(by):
    v = by[b]
    w = sum(r["won"] for r in v)
    e = sum(r["u"] * ((r["pm"] or 1 / r["dec"]) * r["dec"] - 1) for r in v)
    print(f"\n{b}: {w}-{len(v) - w}, {sum(r['net'] for r in v):+.2f}u on {sum(r['u'] for r in v):.1f}u (the market at our prices expected {e:+.2f}u)")
    for r in v:
        print(f"    {r['date'][5:]} {r['lg']:6s} {r['kind']:15s} {(r['team'] or ''):16s} {r['am']:+5d} {r['u']}u {'WON ' if r['won'] else 'lost'} {r['net']:+.2f}u  {r['score'] or ''}")
fair = by["5 FAIR BET (today's rules post it again)"]
print(f"\nWHAT TODAY'S RULES WOULD STILL POST: {sum(r['won'] for r in fair)}-{sum(not r['won'] for r in fair)}, {sum(r['net'] for r in fair):+.2f}u on {sum(r['u'] for r in fair):.1f}u"
      f" ({100 * sum(r['net'] for r in fair) / sum(r['u'] for r in fair):+.1f}%)")
