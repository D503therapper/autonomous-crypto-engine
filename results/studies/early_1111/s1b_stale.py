"""S1b - WAS THE PRICE WE "GOT" A REAL ONE? For every football early play: the tape (our hourly line history) from a
day before the post to two days after - a number that sat unchanged since before the teams' last games and jumped at
the feed's next refresh was a STALE look-ahead price (the books take a game down while its teams are playing; the feed
keeps showing the old number), not one anybody could bet."""
import json
from datetime import timedelta

import elib as E

out = E.Tee("s1b_stale_out.txt")
st = json.load(open(E.se.PATH))
tape = E.line_tape()
tot = {"stale": [], "fresh": []}
for p in sorted(st["picks"] + st.get("pulled", []), key=lambda p: p["posted"]):
    if p["league"] not in ("nfl", "ncaaf") or p.get("market") == "total":
        continue
    i = 1 if p["side"] == "home" else 2
    tp = tape.get(p["game_id"], [])
    post = E.t(p["posted"])
    fa = p.get("fair_at")
    before = [x for x in tp if E.t(x[0]) <= post]
    after = [x for x in tp if E.t(x[0]) > post]
    # the last time the number CHANGED at or before the post, and the first change after
    last_change = None
    for a, b in zip(before, before[1:]):
        if (a[1], a[2]) != (b[1], b[2]):
            last_change = b[0]
    first_seen = before[0][0] if before else None
    set_at = last_change or first_seen
    nxt = next((x for x in after if (x[1], x[2]) != (before[-1][1], before[-1][2])), None) if before else None
    stale = bool(fa and set_at and set_at < fa)          # the number we took was hung BEFORE the fair moment
    g = E.games(p["league"]).get(p["game_id"]) or {}
    other = "away" if p["side"] == "home" else "home"
    ch, co = E.se._int(g.get(f"ml_{p['side']}")), E.se._int(g.get(f"ml_{other}"))
    got = E.nv(p["odds"], p["opp_odds"])
    clv = (E.nv(ch, co) - got) * 100 if g.get("status") == "final" and ch and co else None
    nx = f"{nxt[i]:+d} at {nxt[0][5:16]} ({(E.t(nxt[0]) - post).total_seconds() / 3600:.0f}h later, " \
         f"{(E.nv(nxt[i], nxt[3 - i]) - got) * 100:+.1f} pts)" if nxt else "-"
    out(f"{p['start'][:10]} {p['league']:5s} {(p.get('spot') or 'exam'):9s} {p['team'][:15]:15s} got {p['odds']:+5d} "
        f"posted {p['posted'][5:16]} fair {str(fa)[5:16]} number set {str(set_at)[5:16]} "
        f"{'STALE (set before fair)' if stale else 'fresh'} | next change {nx} | close CLV "
        f"{('%+.1f' % clv) if clv is not None else '?'} {p.get('result') or ''}")
    if clv is not None:
        # CLV against the first REFRESHED number (what a bettor could really have had)
        real = (E.nv(ch, co) - E.nv(nxt[i], nxt[3 - i])) * 100 if (stale and nxt) else clv
        tot["stale" if stale else "fresh"].append((clv, real, p))
for k, v in tot.items():
    res = [(x[2]["result"] == "won", E.dec(x[2]["odds"])) for x in v if x[2].get("result") in ("won", "lost")]
    out(f"\n{k}: n {len(v)}  CLV on the posted price {E.mean(x[0] for x in v):+.2f} pts (t {E.tstat([x[0] for x in v]):+.1f}); "
        f"CLV from the first refreshed number {E.mean(x[1] for x in v):+.2f} pts (t {E.tstat([x[1] for x in v]):+.1f}); "
        f"record {sum(1 for w, _ in res if w)}-{sum(1 for w, _ in res if not w)} "
        f"{E.mean([(d - 1) if w else -1 for w, d in res]) * 100 if res else 0:+.1f}% flat")
allv = tot["stale"] + tot["fresh"]
out(f"\nALL football early plays: posted-price CLV {E.mean(x[0] for x in allv):+.2f} pts; with a stale number replaced by "
    f"its first refresh {E.mean(x[1] for x in allv):+.2f} pts (t {E.tstat([x[1] for x in allv]):+.1f}), "
    f"beat {sum(1 for x in allv if x[1] > 0.25)} / worse {sum(1 for x in allv if x[1] < -0.25)} of {len(allv)}")
