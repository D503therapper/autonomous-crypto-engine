"""S3 - THE LIVE BOOK (data/sports/early.json, read-only): every early play, how long before the game it posted, whether
that was before the week's injury news (NFL: before the first practice report - ilib.report_times; college: more than
3 days out = before the Wednesday-night availability reports / before game week's depth-chart news), what it did, how it
went against the close, and whether the injury watch ever flagged a key man (key_out)."""
import json

import ilib
from ilib import E

out = ilib.Tee("s3_live_out.txt")
st = json.load(open(E.se.PATH))
ps = [dict(p, pulled=False) for p in st["picks"]] + [dict(p, pulled=True) for p in st.get("pulled") or []]


def units(p):
    try:
        return float(p.get("units") or E.se.units(p))
    except Exception:                                        # noqa: BLE001
        return 0.5


def rec(v):
    g = [p for p in v if p.get("result") in ("won", "lost")]
    w = sum(1 for p in g if p["result"] == "won")
    u = sum(units(p) * (E.dec(p["odds"]) - 1) if p["result"] == "won" else -units(p) for p in g)
    f = E.mean([(E.dec(p["odds"]) - 1) if p["result"] == "won" else -1.0 for p in g]) * 100 if g else float("nan")
    c = [p["clv"] for p in g if isinstance(p.get("clv"), (int, float))]
    return (f"n {len(v):2d} graded {len(g):2d} {w}-{len(g) - w} {u:+5.2f}u flat {f:+6.1f}%"
            + (f" | beat the close {E.mean(c):+.2f} pts on {len(c)}" if c else ""))


out("S3 - THE LIVE EARLY BOOK, as of the file")
kept = [p for p in ps if not p["pulled"]]
since = [p for p in kept if p.get("start", "") >= "2026-10-25T08"]
out(f" every kept early play:             {rec(kept)}")
out(f" kept, games from 10/25 on:         {rec(since)}")
out(f"   dogs (plus money sides) 10/25 on: {rec([p for p in since if p.get('market') != 'total' and p['odds'] >= 100])}")
out(f" the injury watch: plays with a key man ruled out after the post (key_out): "
    f"{[(p['team'], p['key_out']) for p in ps if p.get('key_out')]}; plays the watch ran on: "
    f"{sum(1 for p in ps if 'out_at_post' in p)}; with a key man already out at the post: "
    f"{[(p['team'], p['out_at_post']) for p in ps if p.get('out_at_post')]}")

fb = [p for p in ps if p["league"] in ("nfl", "ncaaf") and p.get("market") != "total" and p.get("posted")]
for p in fb:
    start, posted = E.t(p["start"]), E.t(p["posted"])
    p["days_out"] = (start - posted).total_seconds() / 86400
    if p["league"] == "nfl":
        a, b = ilib.report_times({"start": p["start"]})
        p["phase"] = "pre" if posted < a else "mid" if posted < b else "final"
    else:
        p["phase"] = "pre" if p["days_out"] > 3 else "mid"
out(f"\n FOOTBALL early sides (kept + pulled): {len(fb)}")
for lg in ("nfl", "ncaaf"):
    v = [p for p in fb if p["league"] == lg]
    d = sorted(p["days_out"] for p in v)
    out(f"  {lg}: {len(v)} plays; posted a median {d[len(d) // 2]:.1f} days before the game (min {d[0]:.1f}, max {d[-1]:.1f})")
    for ph, nm in (("pre", "BEFORE the week's first injury news"), ("mid", "after the first report"), ("final", "after the final statuses")):
        w = [p for p in v if p["phase"] == ph]
        if w:
            out(f"    {nm:38s} kept {rec([p for p in w if not p['pulled']])} | pulled {len([p for p in w if p['pulled']])}")
    for sp in sorted({p.get("spot") or "exam" for p in v}):
        w = [p for p in v if (p.get("spot") or "exam") == sp and not p["pulled"]]
        out(f"    spot {sp:9s} {rec(w)}")
out("\n every football play, oldest first (days out | phase | spot | price -> close | result):")
for p in sorted(fb, key=lambda p: p["posted"]):
    out(f"  {p['posted'][:10]} {p['league']:5s} {p['team'][:18]:18s} {p['odds']:+4d} {p['days_out']:4.1f}d {p['phase']:5s} "
        f"{(p.get('spot') or 'exam'):9s} close {p.get('close')} clv {p.get('clv')} "
        f"{'PULLED ' if p['pulled'] else ''}{p.get('result')} {('key_out ' + str(p['key_out'])) if p.get('key_out') else ''}")
