"""S11 - ONE VOICE (the owner, 11/11: "I don't want the algorithm to confuse itself" - the Grizzlies +146 early play
read 45.8% on the opening-line model while the 8 AM board's own read on the same side was 36.5% against the 40.8% the
price needs). Does an early play the board's MAIN read fights win?
THE MAIN READ = sports.read_of on the board's own row for that side (a dog's weighed read, the weighed read, else the
own read) - from the 10/30 funnel replay rows (every side of every board day 2023-10 -> 2026-10 + the live stretch,
built blind: params re-tuned each July, no injury reports, CLOSING prices). FUNNEL=<folder with fA-fD.jsonl, fLive.jsonl>.
Two ways to hold it against the early price, both shown:
  (a) AT THE BOARD'S PRICE: the row's own beats_price (read x its closing price > 1) - what the 8 AM board says;
  (b) AT OUR PRICE: the read's margin over ITS market (read - no-vig close) carried onto the early price's no-vig
      number, against what the early price needs (1 / decimal) - no closing-line information in the verdict.
THE EARLY PLAYS:
  1. the 🏀 NBA opening-line play, walk-forward (sports_nba_open.fit on the seasons before only; the ONE best side a
     night at the game file's OPEN, score 4+, -150..+300 - the live rule without the dog weights / injuries);
  2. the football spot dogs under the live bar at the first fair number (base.py, the paid history) - 2023-26;
  3. the live early plays (early.json) against the live board's journal where it holds the game."""
import glob
import json
import os
import sys

import base
import elib as E

import sports
import sports_nba_open as no

out = E.Tee("s11_one_voice_out.txt")
F = os.environ.get("FUNNEL") or ""
rows = {}
for fn in sorted(glob.glob(os.path.join(F, "f[A-D].jsonl")) + glob.glob(os.path.join(F, "fLive.jsonl"))):
    with open(fn) as f:
        for x in f:
            r = json.loads(x)
            if r.get("market", "ml") != "ml" or r.get("dec") is None:
                continue
            rows[(r["league"], r["date"], r["team"])] = r
if not rows:
    out("no funnel rows (set FUNNEL) - nothing to replay")
    sys.exit(0)
out(f"funnel rows (moneyline sides): {len(rows)}")


def main_read(r):
    return sports.read_of(r)


def verdicts(r, odds, opp_odds):
    """-> (a) the board's read beats the board's price, (b) the read's margin over its market, on OUR price."""
    rd = main_read(r)
    if rd is None or r.get("p_market") is None:
        return None, None
    a = rd * r["dec"] > 1
    ours = E.nv(odds, opp_odds) + (rd - r["p_market"])
    b = ours * E.dec(odds) >= 1
    return a, b


def show(name, plays):
    """plays: [(season, won, odds, opp_odds, funnel row)]"""
    for way, idx in (("(a) at the board's price", 0), ("(b) at our price", 1)):
        for lab, want in (("the main read AGREES (not under the price)", True), ("the main read FIGHTS it (under the price)", False)):
            v = [(s, w, o, oo, r) for s, w, o, oo, r in plays if verdicts(r, o, oo)[idx] is want]
            if not v:
                out(f"   {name} {way:24s} {lab:44s} n 0")
                continue
            pl = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in v]
            z = E.zwin([(w, E.nv(o, oo)) for s, w, o, oo, r in v])
            ss = sorted({s for s, *_ in v})
            half = ss[len(ss) // 2] if len(ss) > 1 else None
            h1 = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in v if half is None or s < half]
            h2 = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in v if half is not None and s >= half]
            bys = "  ".join(f"{s} {sum(1 for q in v if q[0] == s and q[1])}-{sum(1 for q in v if q[0] == s and not q[1])}" for s in ss)
            out(f"   {name} {way:24s} {lab:44s} {E.roi(pl)} | z vs the price {z:+.2f} | first half {E.mean(h1) * 100 if h1 else 0:+.1f}% "
                f"({len(h1)}) / second {E.mean(h2) * 100 if h2 else 0:+.1f}% ({len(h2)}) | {bys}")


# ---------------------------------------------------------------- 1. the NBA opening-line play
out("\n1. THE 🏀 NBA OPENING-LINE PLAY, walk-forward at the open (one side a night)")
G = E.games("nba")
tab = no.table(G)
plays, miss = [], 0
for season in sorted({r["season"] for r in tab.values()}):
    m = no.fit(G, season, path=False, tab=tab)
    if not m:
        continue
    dates = sorted({r["date"] for r in tab.values() if r["season"] == season and r["reg"] and r["home_win"] is not None})
    for d in dates:
        prices = {}
        for gid, r in tab.items():
            if r["date"] != d:
                continue
            g = G.get(gid) or {}
            oh, oa = E.se._int(g.get("ml_home_open")), E.se._int(g.get("ml_away_open"))
            if oh and oa:
                prices[gid] = (oh, oa)
        if not prices:
            continue
        sub = {gid: tab[gid] for gid in prices}
        c = no.best_tonight(G, d, m, tab=sub, prices=prices)
        if not c:
            continue
        row = tab[c["game_id"]]
        won = (row["home_win"] == 1) == (c["side"] == "home")
        fr = rows.get(("nba", d, c["team"]))
        if not fr:
            miss += 1
            continue
        plays.append((season, won, c["odds"], c["opp_odds"], fr))
out(f"   opening-line plays matched to a board row: {len(plays)} (no board row: {miss})")
allp = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in plays]
out(f"   every one of them: {E.roi(allp)}")
show("NBA open", plays)
for nm, sel in (("favorites", lambda o: o < 100), ("dogs", lambda o: o >= 100)):
    show(f"NBA open {nm:9s}", [p for p in plays if sel(p[2])])
out("   (c) THE BOARD'S WEIGHTS: the main read against its own NO-VIG market (an NBA favorite's board read starts from the "
    "books, so 'under the price' there is the juice alone - the weights are what the board itself thinks)")
for nm, sel in (("favorites", lambda o: o < 100), ("dogs", lambda o: o >= 100), ("all", lambda o: True)):
    for lab, f in (("weights AGAINST it 1+ pt (read under the market)", lambda g: g <= -1.0),
                   ("weights against it 0-1 pt", lambda g: -1.0 < g < -1e-6),
                   ("no weight either way (read = the market)", lambda g: abs(g) <= 1e-6),
                   ("weights FOR it", lambda g: g > 1e-6),
                   ("NOT under the market (0 or for it)", lambda g: g >= -1e-6),
                   ("UNDER the market (any)", lambda g: g < -1e-6)):
        v = [(s, w, o, oo, r) for s, w, o, oo, r in plays if sel(o) and main_read(r) is not None
             and f((main_read(r) - r["p_market"]) * 100)]
        if not v:
            continue
        pl = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in v]
        ss = sorted({s for s, *_ in v})
        half = ss[len(ss) // 2] if len(ss) > 1 else None
        h1 = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in v if half is None or s < half]
        h2 = [(E.dec(o) - 1) if w else -1.0 for s, w, o, oo, r in v if half is not None and s >= half]
        out(f"     {nm:9s} {lab:50s} {E.roi(pl)} | z vs the price {E.zwin([(w, E.nv(o, oo)) for s, w, o, oo, r in v]):+.2f} | "
            f"first half {E.mean(h1) * 100 if h1 else 0:+.1f}% ({len(h1)}) / second {E.mean(h2) * 100 if h2 else 0:+.1f}% ({len(h2)})")
gaps = [(main_read(r) - r["p_market"]) * 100 for s, w, o, oo, r in plays if main_read(r) is not None]
out(f"   the main read's margin over its own market on these sides: average {E.mean(gaps):+.2f} pts; under the market on "
    f"{sum(1 for x in gaps if x < 0)} of {len(gaps)}")

# ---------------------------------------------------------------- 2. the football spot dogs
out("\n2. THE FOOTBALL SPOT DOGS UNDER THE LIVE BAR, at the first fair number (2023-26)")
se = E.se
for lg in ("nfl", "ncaaf"):
    Gf = E.games(lg)
    plays = []
    for r in base.build(lg):
        f = base.first_fair(r)
        sp = base.spots(r, f) if f else []
        if not f or not sp or r["own"] is None or r["own"] < f[3] - se.SPOT_FIGHT:
            continue
        if se.spot_gap(lg, r["own"], f[3]) + sum(se.SPOT_WEIGHT[h] for h in sp) < se.SPOT_MIN_TOTAL:
            continue
        g = Gf.get(r["id"]) or {}
        day = E.t(r["start"]).astimezone(E.PT).date().isoformat()
        fr = rows.get((lg, day, g.get(f"{r['side']}_name")))
        if not fr:
            continue
        opp = next((k for k in [x for x in base.build(lg) if x["id"] == r["id"] and x["side"] != r["side"]]), None) \
            if False else None
        # the other side's median price at the same look: from the no-vig % and our price
        p_us = f[3]
        d_us = E.dec(f[2])
        imp_opp = (1 / d_us) * (1 - p_us) / p_us
        oo = E.am(1 / imp_opp) if 0 < imp_opp < 1 else -110
        plays.append((r["season"], r["won"], f[2], oo, fr, sp))
    out(f" {lg}: {len(plays)} spot dogs matched to a board row")
    show(f"{lg} spots", [p[:5] for p in plays])
    for spot in ("bye", "blowout", "mnf", "eastwest"):
        sub = [p[:5] for p in plays if spot in p[5]]
        if len(sub) >= 15:
            show(f"{lg} {spot:8s}", sub)

# ---------------------------------------------------------------- 3. the live early plays
out("\n3. THE LIVE EARLY PLAYS against the live board's own row for the game (the funnel's live stretch + the pick journal)")
st = json.load(open(se.PATH))
jr = {}
try:
    J = json.load(open(os.path.join(E.sd.DATA, "pick_journal.json")))
    J = J.get("rows") if isinstance(J, dict) else J
    for x in J or []:
        if isinstance(x, dict) and x.get("game_id") and x.get("side"):
            jr[(x["game_id"], x["side"])] = x
except (OSError, ValueError):
    pass
out(f"   pick-journal rows with a game id: {len(jr)}")
live = []
for p in st["picks"]:
    if p.get("market") == "total" or p.get("result") not in ("won", "lost"):
        continue
    day = E.t(p["start"]).astimezone(E.PT).date().isoformat()
    fr = rows.get((p["league"], day, p["team"])) or jr.get((p["game_id"], p["side"]))
    if not fr or fr.get("dec") is None or fr.get("p_market") is None:
        continue
    live.append((p.get("spot") or "exam", p["result"] == "won", p["odds"], p["opp_odds"], fr))
    a, b = verdicts(fr, p["odds"], p["opp_odds"])
    rd = main_read(fr)
    out(f"   {day} {p['league']:5s} {(p.get('spot') or 'exam'):9s} {p['team'][:16]:16s} {p['odds']:+5d} early read "
        f"{(p.get('own') or 0) * 100:4.1f}% | the board: read {rd * 100:4.1f}% vs its price's {100 / fr['dec']:4.1f}% -> "
        f"{'agrees' if a else 'FIGHTS'} (at our price: {'agrees' if b else 'FIGHTS'}) | {p['result']}")
show("live", [(0, w, o, oo, r) for s, w, o, oo, r in live])
