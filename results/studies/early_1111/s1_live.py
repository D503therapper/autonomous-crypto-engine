"""S1 - THE LIVE TRUTH. Every early play we posted (data/sports/early.json, pulled ones too): the price we got vs the
close (the game file's closing moneyline; the engine's own hourly line history for the path), in no-vig win-% points
and cents - by spot, league, hours before the game, day of the week posted. Then last week (the 11/2-11/9 games) play by
play, and whether beating the close went with winning. Totals (the Europe under) are read on the number."""
import json

import elib as E

out = E.Tee("s1_live_out.txt")
st = json.load(open(E.se.PATH))
tape = E.line_tape()
rows = []
for p in st["picks"] + [dict(x, _pulled=True) for x in st.get("pulled", [])]:
    lg = p["league"]
    g = E.games(lg).get(p["game_id"]) or {}
    if p.get("market") == "total" or not p.get("side") in ("home", "away"):
        continue
    other = "away" if p["side"] == "home" else "home"
    ch, co = E.se._int(g.get(f"ml_{p['side']}")), E.se._int(g.get(f"ml_{other}"))
    tp = [x for x in tape.get(p["game_id"], []) if x[0] <= p["start"]]
    if g.get("status") != "final":
        ch = co = None
    if (ch is None or co is None) and tp and g.get("status") == "final":
        last = tp[-1]
        ch, co = (last[1], last[2]) if p["side"] == "home" else (last[2], last[1])
    got = E.nv(p["odds"], p["opp_odds"]) if p.get("opp_odds") is not None else p.get("mkt")
    r = {"p": p, "g": g, "got": got, "close": None, "clv": None, "cents": None, "path": []}
    if ch is not None and co is not None:
        r["close"] = (ch, co)
        r["clv"] = (E.nv(ch, co) - got) * 100           # + = the close made our side MORE likely than we paid for
        r["cents"] = E.cents(ch, p["odds"])              # + = we hold a better price than the close
    side_i = 1 if p["side"] == "home" else 2
    for x in tape.get(p["game_id"], []):
        if x[0] <= p["start"]:
            h = (E.t(p["start"]) - E.t(x[0])).total_seconds() / 3600
            r["path"].append((h, x[side_i], E.nv(x[side_i], x[3 - side_i]) * 100))
    # the first fair number on our tape (the first row at / after fair_at) and the money's move before the post
    fa = p.get("fair_at")
    ff = next((x for x in tape.get(p["game_id"], []) if (not fa or x[0] >= fa)), None)
    r["ff"] = (ff[side_i], E.nv(ff[side_i], ff[3 - side_i]) * 100, ff[0]) if ff else None
    r["h_before"] = (E.t(p["start"]) - E.t(p["posted"])).total_seconds() / 3600
    r["h_after_fair"] = (E.t(p["posted"]) - E.t(fa)).total_seconds() / 3600 if fa else None
    r["dow"] = E.t(p["posted"]).astimezone(E.PT).strftime("%a")
    rows.append(r)

graded = [r for r in rows if r["clv"] is not None and not r["p"].get("_pulled")]
pulled = [r for r in rows if r["clv"] is not None and r["p"].get("_pulled")]


def line(name, rs):
    if not rs:
        return
    c = [r["clv"] for r in rs]
    beat = sum(1 for x in c if x > 0.25)
    worse = sum(1 for x in c if x < -0.25)
    ce = [r["cents"] for r in rs]
    res = [r for r in rs if r["p"].get("result") in ("won", "lost")]
    w = sum(1 for r in res if r["p"]["result"] == "won")
    pl = [(E.dec(r["p"]["odds"]) - 1) if r["p"]["result"] == "won" else -1.0 for r in res]
    out(f" {name:34s} n {len(rs):3d}  CLV {E.mean(c):+5.2f} pts (t {E.tstat(c):+4.1f})  {E.mean(ce):+6.1f} cents  "
        f"beat {beat} / same {len(rs) - beat - worse} / worse {worse}   record {w}-{len(res) - w} "
        f"{(E.mean(pl) * 100 if pl else 0):+6.1f}% flat")


out("S1 (A) EVERY EARLY MONEYLINE PLAY WITH A CLOSE ON FILE (posted price vs the close; CLV = close no-vig % minus the "
    "no-vig % we paid; + = we beat the close)")
line("ALL posted (kept)", graded)
line("pulled plays (not in the record)", pulled)
line("kept + pulled", graded + pulled)
out(" by spot")
for s in sorted({r["p"].get("spot") or "exam band" for r in graded + pulled}):
    line("  " + s, [r for r in graded + pulled if (r["p"].get("spot") or "exam band") == s])
out(" by league")
for s in sorted({r["p"]["league"] for r in graded + pulled}):
    line("  " + s, [r for r in graded + pulled if r["p"]["league"] == s])
out(" football only: hours from the post to kickoff")
fb = [r for r in graded + pulled if r["p"]["league"] in ("nfl", "ncaaf")]
for lo, hi, nm in ((0, 72, "under 3 days"), (72, 120, "3-5 days"), (120, 150, "5-6.25 days"), (150, 999, "6.25+ days")):
    line("  " + nm, [r for r in fb if lo <= r["h_before"] < hi])
out(" football only: hours from the first fair number to the post")
for lo, hi, nm in ((-1, 2, "inside 2h"), (2, 12, "2-12h"), (12, 24, "12-24h"), (24, 999, "24h+")):
    line("  " + nm, [r for r in fb if r["h_after_fair"] is not None and lo <= r["h_after_fair"] < hi])
out(" football only: the day it posted (PT)")
for d in ("Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"):
    line("  " + d, [r for r in fb if r["dow"] == d])
out(" football only: the price")
for lo, hi in ((100, 129), (130, 199), (200, 350)):
    line(f"  +{lo}..+{hi}", [r for r in fb if lo <= r["p"]["odds"] <= hi])
out(" football only: what the money had done from the first fair number to our post (our tape)")
for nm, f in (("came TO us 2+ pts before the post", lambda m: m >= 2), ("flat", lambda m: -2 < m < 2),
              ("ran AWAY 2+ pts before the post", lambda m: m <= -2)):
    line("  " + nm, [r for r in fb if r["ff"] and f(r["got"] * 100 - r["ff"][1])])

out("\nS1 (B) DOES BEATING THE CLOSE GO WITH WINNING (our early moneyline plays, kept + pulled, graded games)")
allr = [r for r in graded + pulled if r["g"].get("status") == "final"]
for r in allr:
    g = r["g"]
    try:
        hw = float(g["home_score"]) > float(g["away_score"])
    except (KeyError, ValueError, TypeError):
        hw = None
    r["won"] = None if hw is None else (hw == (r["p"]["side"] == "home"))
for nm, f in (("beat the close 2+ pts", lambda c: c >= 2), ("beat it 0.25-2", lambda c: 0.25 < c < 2),
              ("same", lambda c: -0.25 <= c <= 0.25), ("worse 0.25-2", lambda c: -2 < c < -0.25),
              ("worse 2+ pts", lambda c: c <= -2)):
    rs = [r for r in allr if r.get("won") is not None and f(r["clv"])]
    pl = [(E.dec(r["p"]["odds"]) - 1) if r["won"] else -1.0 for r in rs]
    out(f" {nm:24s} {E.roi(pl)}   price said {E.mean(r['got'] for r in rs) * 100:5.1f}% / the close said "
        f"{E.mean(E.nv(*r['close']) for r in rs) * 100:5.1f}%")

out("\nS1 (C) EVERY FOOTBALL / NBA EARLY PLAY, ONE LINE EACH (posted -> first fair on our tape -> lowest / highest -> "
    "close)")
for r in sorted(graded + pulled, key=lambda r: r["p"]["start"]):
    p = r["p"]
    pa = [x[1] for x in r["path"] if x[0] <= r["h_before"]]
    best = max(pa) if pa else None
    worst = min(pa) if pa else None
    out(f" {p['start'][:10]} {p['league']:5s} {(p.get('spot') or 'exam'):9s} {p['team'][:16]:16s} "
        f"got {p['odds']:+5d} ({r['dow']} {r['h_before']:5.0f}h out, {('%4.0fh' % r['h_after_fair']) if r['h_after_fair'] is not None else '   ?'} after fair"
        f"{', first fair %+d' % r['ff'][0] if r['ff'] else ''}) -> close {r['close'][0]:+5d}  CLV {r['clv']:+5.1f} pts  "
        f"best after post {('%+d' % best) if best is not None else '?'} / worst {('%+d' % worst) if worst is not None else '?'}  "
        f"{p.get('result') or ('pulled' if p.get('_pulled') else 'open')}"
        f"{'  KEY OUT: ' + str(p['key_out']) if p.get('key_out') else ''}{'  (pulled)' if p.get('_pulled') else ''}")

out("\nS1 (D) STILL OPEN (the price now on the game file)")
for r in rows:
    p = r["p"]
    if p.get("_pulled") or p.get("result") or r["g"].get("status") == "final":
        continue
    other = "away" if p["side"] == "home" else "home"
    n, no = E.se._int(r["g"].get(f"ml_{p['side']}")), E.se._int(r["g"].get(f"ml_{other}"))
    if n is None or no is None:
        continue
    out(f" {p['start'][:10]} {p['league']:5s} {(p.get('spot') or 'exam'):9s} {p['team'][:16]:16s} got {p['odds']:+5d} "
        f"-> now {n:+5d}  ({(E.nv(n, no) - r['got']) * 100:+5.1f} pts)")

json.dump([{"game_id": r["p"]["game_id"], "team": r["p"]["team"], "spot": r["p"].get("spot"), "league": r["p"]["league"],
            "odds": r["p"]["odds"], "close": r["close"], "clv": r["clv"], "cents": r["cents"],
            "result": r["p"].get("result"), "pulled": bool(r["p"].get("_pulled")), "start": r["p"]["start"],
            "posted": r["p"]["posted"], "h_before": r["h_before"], "h_after_fair": r["h_after_fair"]}
           for r in rows], open(E.os.path.join(E.OUT, "s1_live_rows.json"), "w"), indent=0)
