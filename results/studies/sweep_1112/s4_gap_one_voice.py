"""11/12 SWEEP (b) - THE 🔍 GAP PLAY AND ONE VOICE: on the replay's funnel rows (every college football moneyline side
2023-26, closing prices, the board's own reads; the rows carry no FBS flag / QB change), the dogs +100..+350 whose RAW
own read is 15+ points over the no-vig market (the 🔍 rule), by home / road, by the 35 cap, and by whether the engine's
MAIN read (the blended win % the board ranks on) is under what the price needs ("the main read fights it") and by the
sign of the dog score (the engine's own angles for / against). Flat 1u at the close; train = to 2025-06, held = after.
Usage: python results/studies/sweep_1112/s4_gap_one_voice.py > results/studies/sweep_1112/s4_gap_one_voice.out"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "plays_every_day_1104"))
import sim_volume as sv  # noqa: E402

rows = [r for r in sv.rows if r["league"] == "ncaaf" and 100 <= r["odds"] <= 350 and r.get("raw_own") is not None
        and r.get("p_market") is not None and r["result"] in ("won", "lost")]
print(f"{len(rows)} college football dog sides +100..+350 with a raw read; keys with a dog score: {sum(r.get('dog_score') is not None for r in rows)}")


def line(name, rs):
    if not rs:
        print(f"  {name:58s} n 0")
        return

    def st(v):
        if not v:
            return "n   0"
        w = sum(r["result"] == "won" for r in v)
        fl = sum((r["dec"] - 1) if r["result"] == "won" else -1 for r in v)
        e = sum(r["p_market"] for r in v)
        s = math.sqrt(sum(r["p_market"] * (1 - r["p_market"]) for r in v))
        return f"n {len(v):3d} {w:3d}-{len(v) - w:<3d} {100 * fl / len(v):+6.1f}% z {(w - e) / s if s else 0:+.2f}"
    tr = [r for r in rs if sv.half(r["date"]) == "train"]
    he = [r for r in rs if sv.half(r["date"]) == "held"]
    lv = [r for r in rs if sv.half(r["date"]) == "live"]
    print(f"  {name:58s} all {st(tr + he)} | train {st(tr)} | held {st(he)} | live {st(lv)}")


gap = lambda r: r["raw_own"] - r["p_market"]                         # noqa: E731
fights = lambda r: r["p"] * r["dec"] < 1                              # noqa: E731  the main (blended) read under the price
G = [r for r in rows if gap(r) >= 0.15]
line("every dog", rows)
line("raw gap 15+ (the 🔍 rule's core)", G)
line("   home", [r for r in G if r["home"]])
line("   road", [r for r in G if not r["home"]])
R = [r for r in G if not r["home"] and gap(r) < 0.35]
line("road, gap 15-35 (the 11/11 cut, no QB / FBS flag here)", R)
line("   the main read is UNDER the price (fights)", [r for r in R if fights(r)])
line("   the main read is at / over the price (one voice)", [r for r in R if not fights(r)])
line("   dog score under 0 (our angles against it)", [r for r in R if r.get("dog_score") is not None and r["dog_score"] < 0])
line("   dog score 0+", [r for r in R if r.get("dog_score") is not None and r["dog_score"] >= 0])
line("   one voice AND dog score 0+", [r for r in R if not fights(r) and r.get("dog_score") is not None and r["dog_score"] >= 0])
line("   +100..+150", [r for r in R if r["odds"] <= 150])
line("   +151..+350", [r for r in R if r["odds"] > 150])
print("-- the same question on every road dog (not just 15+): does the main read fighting matter?")
RD = [r for r in rows if not r["home"]]
line("road dogs, main read fights", [r for r in RD if fights(r)])
line("road dogs, one voice", [r for r in RD if not fights(r)])
HD = [r for r in rows if r["home"]]
line("home dogs, main read fights", [r for r in HD if fights(r)])
line("home dogs, one voice", [r for r in HD if not fights(r)])
print("-- the home dogs the 11/11 cut dropped (for the record)")
H = [r for r in G if r["home"] and gap(r) < 0.35]
line("home, gap 15-35", H)
line("   one voice AND dog score 0+", [r for r in H if not fights(r) and r.get("dog_score") is not None and r["dog_score"] >= 0])
