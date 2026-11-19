"""S7 - WHEN THE PRICE IS BEST, on history.
(1) R3 (the board on today's code, 2023-10 -> 2026-11): every posted unit play's price the NIGHT BEFORE (ESPN's open -
    hockey / NBA / college hoops only; football's "open" is a summer look-ahead) vs its CLOSE - how far the market
    came toward the engine's sides, and the same plays' ROI at each. The 8 AM price sits between the two (our tape:
    about two thirds of a hockey day's move is in by 8 AM - the 10/6 study).
(2) The paid NHL morning look 2021-23 (15:00Z = the board's hour): hockey dog cells bet at the morning price vs the
    close, and the simplest "wait" rules (bet at the close only if the price got longer / skip if it got shorter)."""
import os
import sys
import glib
from glib import dec, nv, sane, st

sys.path.insert(0, os.path.join(glib.ROOT, "results", "studies", "money_1117"))
import mlib as M  # noqa: E402
import dlib as D  # noqa: E402

say = glib.Tee(glib.HERE + "/s7_history.out")
P, DAYS = M.board()
rows = []
for r in P:
    if r["league"] not in ("nhl", "nba", "ncaab") or r["market"] != "ml":
        continue
    s = r["side"]
    if not sane(r.get(f"ml_{s}_open"), r.get("ml_home_open" if s == "away" else "ml_away_open")):
        continue
    r["won"] = r["result"] == "won"
    r["dec_c"] = r["dec"]
    r["dec_o"] = dec(r[f"ml_{s}_open"])
    po = nv(r["ml_home_open"], r["ml_away_open"])
    pc = nv(r["ml_home"], r["ml_away"])
    r["mv"] = 100 * ((pc - po) if s == "home" else (po - pc))
    rows.append(r)


def T(name, rs):
    rs = [r for r in rs if D.half(r["date"]) != "live"]
    if len(rs) < 10:
        return
    tr = [r for r in rs if D.half(r["date"]) == "train"]
    he = [r for r in rs if D.half(r["date"]) == "held"]
    mv = sum(r["mv"] for r in rs) / len(rs)
    to = sum(r["mv"] > 0.25 for r in rs) / len(rs)
    aw = sum(r["mv"] < -0.25 for r in rs) / len(rs)
    say(f"  {name:44s} n {len(rs):4d} | the market's move to our side, open -> close {mv:+5.2f} pts (to us {to:.0%} / away {aw:.0%})"
        f" | ROI at the open {st(rs, 'dec_o')['roi']:+6.1f}% vs the close {st(rs, 'dec_c')['roi']:+6.1f}%"
        f" | train {st(tr, 'dec_o')['roi']:+6.1f}% vs {st(tr, 'dec_c')['roi']:+6.1f}% | held {st(he, 'dec_o')['roi']:+6.1f}% vs {st(he, 'dec_c')['roi']:+6.1f}%")


say("=== (1) R3: the posted plays, the night-before price vs the close")
for lg in ("nhl", "nba", "ncaab"):
    R = [r for r in rows if r["league"] == lg]
    say(f" -- {lg.upper()}")
    T("every unit play", R)
    T("dogs", [r for r in R if r["odds"] >= 100])
    T("favorites", [r for r in R if r["odds"] < 0])
    for k in sorted({r["k"].rsplit(" (", 1)[0] for r in R}):
        T(k, [r for r in R if r["k"].rsplit(" (", 1)[0] == k])
    T("dogs, at home", [r for r in R if r["odds"] >= 100 and r["home"]])
    T("dogs, on the road", [r for r in R if r["odds"] >= 100 and not r["home"]])

say("\n=== (2) the paid NHL morning look 2021-23: hockey dog cells at the morning (8 AM board hour) vs the close")
S = [r for r in glib.games() if r.get("dec_m")]
for r in S:
    r["b2b"], r["ob2b"] = r["g_me"]["b2b"], r["g_op"]["b2b"]
    r["am_m"] = glib.am(r["dec_m"])
    r["mv"] = 100 * (r["p_c"] - r["p_m"])


def W(name, rs):
    if len(rs) < 10:
        return
    a, c = st(rs, "dec_m"), st(rs, "dec_c")
    mv = sum(r["mv"] for r in rs) / len(rs)
    best = [dict(r, dec_b=max(r["dec_m"], r["dec_c"])) for r in rs]
    longer = [r for r in rs if r["dec_c"] > r["dec_m"] + 0.02]
    shorter = [r for r in rs if r["dec_c"] < r["dec_m"] - 0.02]
    say(f"  {name:40s} n {a['n']:4d} {a['w']}-{a['n'] - a['w']} | morning {a['roi']:+6.1f}% vs close {c['roi']:+6.1f}% (move to us {mv:+.2f} pts)"
        f" | got LONGER by the close: {len(longer)} at the close {st(longer, 'dec_c')['roi']:+6.1f}% (at the morning {st(longer, 'dec_m')['roi']:+6.1f}%)"
        f" | got SHORTER: {len(shorter)} at the morning {st(shorter, 'dec_m')['roi']:+6.1f}% (close {st(shorter, 'dec_c')['roi']:+6.1f}%)"
        f" | the better of the two (hindsight) {st(best, 'dec_b')['roi']:+6.1f}%")


dogs = [r for r in S if 100 <= r["am_m"] <= 350]
W("every dog +100..+350", dogs)
W("dogs +100..+150", [r for r in dogs if r["am_m"] <= 150])
W("dogs +151..+350", [r for r in dogs if r["am_m"] > 150])
W("the rested dog vs a b2b favorite", [r for r in dogs if r["ob2b"] and not r["b2b"]])
W("  ...+100..+150", [r for r in dogs if r["ob2b"] and not r["b2b"] and r["am_m"] <= 150])
W("home dogs", [r for r in dogs if r["home"]])
W("road dogs", [r for r in dogs if not r["home"]])
fav = [r for r in S if -150 <= r["am_m"] <= -101]
W("favorites -101..-150", fav)
W("the rested favorite vs a b2b dog", [r for r in fav if r["ob2b"] and not r["b2b"]])
for ssn in sorted({r["season"] for r in dogs}):
    W(f"rested dog vs b2b favorite {ssn}", [r for r in dogs if r["ob2b"] and not r["b2b"] and r["season"] == ssn])
