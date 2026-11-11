"""S3b / S10 on OUR OWN hourly line tape (data/sports/line_history, every football game 10/1-11/11/2026) - the part of
the week the paid history can't see (its first fair look is Tuesday): the night the number goes up -> Tuesday.
S10 - THE STALE NUMBER: the price on the feed at the moment a game turns 'fair' (both teams' last games + 4h) is very
      often the LOOK-AHEAD number hung before those games - it hasn't been re-hung yet. How often, how long until it
      is, and how far it jumps when it does (all games, then the dogs that just blew somebody out).
S3b - THE PATH FROM THE FIRST FRESH NUMBER (the first price that CHANGED at or after the fair moment): where the
      dog's no-vig % sits 6h / 12h / 24h / 48h / 72h later, a day before kickoff, and at the close; the ROI at each."""
from datetime import timedelta

import elib as E

out = E.Tee("s3b_s10_tape_out.txt")
se = E.se
tape = E.line_tape()
allg = {}
for lg in ("nfl", "ncaaf"):
    allg.update(E.games(lg))
sched = se._schedule(allg)
rows = []
for gid, g in allg.items():
    if g.get("status") != "final" or gid not in tape or (g.get("stype") or "?") not in E.sd.REAL:
        continue
    if not "2026-10-03" <= g["start"][:10] <= "2026-11-11":
        continue
    try:
        hw = float(g["home_score"]) > float(g["away_score"])
        if float(g["home_score"]) == float(g["away_score"]):
            continue
    except (KeyError, ValueError, TypeError):
        continue
    rd = se.ready(sched, g)
    if not rd:
        continue
    start = E.t(g["start"])
    tp = [(E.t(x[0]), x[1], x[2]) for x in tape[gid] if E.t(x[0]) < start]
    pre = [x for x in tp if x[0] < rd]
    post = [x for x in tp if x[0] >= rd]
    if not post or (start - rd).total_seconds() < 3 * 86400:
        continue
    # the tape keeps a row only when the price CHANGES: the number showing at the fair moment is the last row before it
    at_fair = pre[-1] if pre else post[0]               # what the engine's scan sees the first hour the game is fair
    stale = bool(pre)                                   # hung before the teams' last games ended
    fresh = next((x for x in post if (x[1], x[2]) != (at_fair[1], at_fair[2])), None) if stale else at_fair
    if not stale and (at_fair[0] - rd).total_seconds() > 24 * 3600:
        continue                                        # no number on the feed for a day after the fair moment
    prev = {s: se._prev(sched, g["league"], g[s], g["start"]) for s in ("home", "away")}
    lm = {}
    for s in ("home", "away"):
        p = prev[s]
        try:
            m = float(p["home_score"]) - float(p["away_score"])
            lm[s] = m if p["home"] == g[s] else -m
        except (KeyError, ValueError, TypeError):
            lm[s] = None
    rows.append({"g": g, "rd": rd, "start": start, "tp": tp, "at_fair": at_fair, "stale": stale, "fresh": fresh,
                 "hw": hw, "lm": lm})


def p_of(x, side):
    return E.nv(x[1], x[2]) if side == "home" else E.nv(x[2], x[1])


def o_of(x, side):
    return x[1] if side == "home" else x[2]


def at_time(r, when):
    v = [x for x in r["tp"] if x[0] <= when]
    return v[-1] if v else None


out("=" * 30, "S10 - THE STALE NUMBER (every football game 10/3-11/11 on our tape, 3+ days between the fair moment and "
    "kickoff)")
for lg in ("nfl", "ncaaf"):
    rs = [r for r in rows if r["g"]["league"] == lg]
    st = [r for r in rs if r["stale"]]
    out(f"\n {lg}: {len(rs)} games; the number at the fair moment was the SAME one hung before the teams' last games "
        f"in {len(st)} ({len(st) / max(1, len(rs)) * 100:.0f}%)")
    wait = [(r["fresh"][0] - r["rd"]).total_seconds() / 3600 for r in st if r["fresh"]]
    if wait:
        ws = sorted(wait)
        out(f"   hours from the fair moment until the number was re-hung: median {ws[len(ws) // 2]:.0f}h, "
            f"75% inside {ws[int(len(ws) * .75)]:.0f}h, 90% inside {ws[int(len(ws) * .9)]:.0f}h; never re-hung "
            f"{sum(1 for r in st if not r['fresh'])}")
    j = [abs(p_of(r["fresh"], "home") - p_of(r["at_fair"], "home")) * 100 for r in st if r["fresh"]]
    out(f"   the jump when it was re-hung: {E.mean(j):.1f} pts on average, 3+ pts in "
        f"{sum(1 for x in j if x >= 3) / max(1, len(j)) * 100:.0f}%, 5+ in {sum(1 for x in j if x >= 5) / max(1, len(j)) * 100:.0f}%")
    for nm, sel in (("dogs +100..+350 on the STALE number that just won by 17+ (the blowout spot's own trigger)",
                     lambda r, s: (r["lm"][s] or 0) >= 17),
                    ("dogs +100..+350 on the STALE number that just LOST by 17+", lambda r, s: (r["lm"][s] or 0) <= -17),
                    ("every dog +100..+350 on the STALE number", lambda r, s: True)):
        v = []
        for r in st:
            if not r["fresh"]:
                continue
            for s in ("home", "away"):
                if 100 <= o_of(r["at_fair"], s) <= 350 and sel(r, s):
                    v.append((r, s))
        if len(v) < 5:
            continue
        jump = [(p_of(r["fresh"], s) - p_of(r["at_fair"], s)) * 100 for r, s in v]
        won = [(r["hw"] == (s == "home")) for r, s in v]
        a = [(E.dec(o_of(r["at_fair"], s)) - 1) if w else -1.0 for (r, s), w in zip(v, won)]
        b = [(E.dec(o_of(r["fresh"], s)) - 1) if w else -1.0 for (r, s), w in zip(v, won)]
        out(f"   {nm}: n {len(v)}, the re-hung number moved {E.mean(jump):+.1f} pts toward them (t {E.tstat(jump):+.1f}; "
            f"toward 1+ {sum(1 for x in jump if x >= 1)}, away 1+ {sum(1 for x in jump if x <= -1)}) | paper ROI at the stale "
            f"number {E.roi(a)} | ROI at the re-hung number {E.roi(b)}")

out("\n" + "=" * 30, "S3b - THE PATH FROM THE FIRST FRESH NUMBER (dogs +100..+350 at the first number that changed at or "
    "after the fair moment; points of no-vig % gained since; + = the money came to the dog)")
for lg in ("nfl", "ncaaf"):
    for nm, sel in (("every dog", lambda r, s: True),
                    ("just won by 17+", lambda r, s: (r["lm"][s] or 0) >= 17),
                    ("just lost by 17+", lambda r, s: (r["lm"][s] or 0) <= -17),
                    ("home dogs", lambda r, s: s == "home"), ("road dogs", lambda r, s: s == "away")):
        v = [(r, s) for r in rows if r["g"]["league"] == lg and r["fresh"]
             and (r["start"] - r["fresh"][0]).total_seconds() >= 2 * 86400
             for s in ("home", "away") if 100 <= o_of(r["fresh"], s) <= 350 and sel(r, s)]
        if len(v) < 12:
            continue
        won = [(r["hw"] == (s == "home")) for r, s in v]
        a0 = [(E.dec(o_of(r["fresh"], s)) - 1) if w else -1.0 for (r, s), w in zip(v, won)]
        fd = [r["fresh"][0].astimezone(E.PT) for r, s in v]
        out(f"\n {lg} | {nm}: {len(v)} dogs; the fresh number showed {E.mean((r['fresh'][0] - r['rd']).total_seconds() / 3600 for r, s in v):.0f}h "
            f"after the fair moment on average ({E.mean((r['start'] - r['fresh'][0]).total_seconds() / 86400 for r, s in v):.1f} days out); "
            f"ROI at it {E.roi(a0)}")
        for lab, f in (("+6h", lambda r: r["fresh"][0] + timedelta(hours=6)),
                       ("+12h", lambda r: r["fresh"][0] + timedelta(hours=12)),
                       ("+24h", lambda r: r["fresh"][0] + timedelta(hours=24)),
                       ("+48h", lambda r: r["fresh"][0] + timedelta(hours=48)),
                       ("+72h", lambda r: r["fresh"][0] + timedelta(hours=72)),
                       ("2 days before kickoff", lambda r: r["start"] - timedelta(hours=48)),
                       ("1 day before kickoff", lambda r: r["start"] - timedelta(hours=24)),
                       ("3h before kickoff", lambda r: r["start"] - timedelta(hours=3)),
                       ("the close (last on the tape)", lambda r: r["start"])):
            mvs, pls = [], []
            for (r, s), w in zip(v, won):
                x = at_time(r, f(r))
                if not x or x[0] < r["fresh"][0]:
                    continue
                mvs.append((p_of(x, s) - p_of(r["fresh"], s)) * 100)
                pls.append((E.dec(o_of(x, s)) - 1) if w else -1.0)
            if mvs:
                out(f"   by {lab:28s} {E.mean(mvs):+5.2f} pts (t {E.tstat(mvs):+4.1f}; came 1+ toward "
                    f"{sum(1 for x in mvs if x >= 1) / len(mvs) * 100:3.0f}% / away 1+ {sum(1 for x in mvs if x <= -1) / len(mvs) * 100:3.0f}%) | "
                    f"ROI betting then {E.roi(pls)}")
        hrs = {}
        for d in fd:
            k = f"{d.strftime('%a')} {'night (6PM-6AM)' if (d.hour >= 18 or d.hour < 6) else 'day'}"
            hrs[k] = hrs.get(k, 0) + 1
        out("   when the fresh number showed (PT): " + ", ".join(f"{k} {n}" for k, n in sorted(hrs.items(), key=lambda t: -t[1])))

out("\n S3b(2) - WHAT THE MONEY DID IN THE FIRST 24 HOURS -> THE REST OF THE WEEK (dogs +100..+350 at the fresh number + 24h)")
BK = (("ran AWAY 2+ pts in the first 24h", -99, -2), ("ran away 1-2", -2, -1), ("flat", -1, 1), ("came to it 1-2", 1, 2),
      ("came to it 2+", 2, 99))
for lg in ("nfl", "ncaaf", "both"):
    for bn, lo, hi in BK:
        v = []
        for r in rows:
            if (lg != "both" and r["g"]["league"] != lg) or not r["fresh"]:
                continue
            x = at_time(r, r["fresh"][0] + timedelta(hours=24))
            c = at_time(r, r["start"])
            if not x or (r["start"] - x[0]).total_seconds() < 2 * 86400:
                continue
            for s in ("home", "away"):
                if 100 <= o_of(x, s) <= 350 and lo <= (p_of(x, s) - p_of(r["fresh"], s)) * 100 < hi:
                    w = r["hw"] == (s == "home")
                    v.append(((p_of(c, s) - p_of(x, s)) * 100, (E.dec(o_of(x, s)) - 1) if w else -1.0))
        if len(v) >= 8:
            out(f"   {lg:5s} {bn:34s} still to come {E.mean(a for a, _ in v):+5.2f} (t {E.tstat([a for a, _ in v]):+4.1f}) | "
                f"ROI at the 24h price {E.roi([b for _, b in v])}")
