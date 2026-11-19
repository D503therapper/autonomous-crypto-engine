"""S6 - WHEN THE PRICE IS BEST, on our own line tape (data/sports/line_history, every price change since 10/1/2026).
(1) THE WHOLE MARKET by sport: each moneyline side's price at the 8 AM PT board on its game day, 2 hours before the
    start, and the close (the last look before the start). The move in cents and in no-vig points, and the flat ROI of
    the same side bet at each of the three.
(2) OUR OWN PLAYS (picks.json unit plays + early.json side plays): the price we posted at, the price 2 hours before the
    start, the close - by kind and sport, with the result at each price (what the owner's ticket would have paid)."""
import csv
import glob
import json
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import glib
from glib import dec, nv, sane

say = glib.Tee(glib.HERE + "/s6_tape.out")
PT, UTC = ZoneInfo("America/Los_Angeles"), ZoneInfo("UTC")


def t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)


HIST = defaultdict(list)
for f in sorted(glob.glob("data/sports/line_history/*.jsonl")):
    for ln in open(f):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("t") and r.get("s") and r["t"] < r["s"] and r.get("h") is not None and r.get("a") is not None:
            try:
                HIST[r["g"]].append((r["t"], int(float(r["h"])), int(float(r["a"])), r["s"]))
            except (TypeError, ValueError):
                pass
for v in HIST.values():
    v.sort()

GAMES = {}
for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf"):
    for f in sorted(glob.glob(f"data/sports/games/{lg}/2026-*.csv")):
        for g in csv.DictReader(open(f)):
            if g["status"] == "final" and g["home_score"] not in ("", None) and g["start"] >= "2026-10-01":
                GAMES[g["id"]] = g


def at(gid, when):
    """the (home, away) price on the tape at `when` (the last look at or before it), or None"""
    w = when.strftime("%Y-%m-%dT%H:%MZ")
    last = None
    for tt, h, a, _ in HIST.get(gid, []):
        if tt <= w:
            last = (h, a)
        else:
            break
    return last if last and sane(*last) else None


def marks(gid, start):
    s = t(start)
    day = s.astimezone(PT).replace(hour=8, minute=0)
    if day >= s:                      # a game before 8 AM PT: no board mark
        day = None
    return (at(gid, day.astimezone(UTC)) if day else None, at(gid, s - timedelta(hours=2)), at(gid, s - timedelta(minutes=1)))


def roi(xs):
    """xs = [(dec, won)]"""
    return 100 * sum((d - 1) if w else -1 for d, w in xs) / len(xs) if xs else 0.0


say("=== (1) THE WHOLE MARKET since 10/1/2026 - 8 AM PT on game day -> 2 hours before -> the close")
say("  cents = American cents the side got LONGER (+ = waiting paid more); pts = no-vig points the market moved TO the side")
rows = []
for gid, g in GAMES.items():
    m8, m2, mc = marks(gid, g["start"])
    if not (m8 and m2 and mc):
        continue
    try:
        hs, as_ = int(g["home_score"]), int(g["away_score"])
    except ValueError:
        continue
    if hs == as_:
        continue
    for i, s in enumerate(("home", "away")):
        p8, p2, pc = nv(*m8), nv(*m2), nv(*mc)
        if i:
            p8, p2, pc = 1 - p8, 1 - p2, 1 - pc
        rows.append(dict(lg=g["league"], gid=gid, side=s, o8=m8[i], o2=m2[i], oc=mc[i], p8=p8, p2=p2, pc=pc,
                         won=(hs > as_) == (s == "home"), home=s == "home", date=g["start"][:10]))


def cents(a, b):
    """American cents from price a to price b on the 100-centred scale (+ = longer)"""
    def u(o):
        return o - 100 if o > 0 else o + 100
    return u(b) - u(a)


def mk(name, rs):
    if len(rs) < 8:
        say(f"  {name:44s} n {len(rs):4d}")
        return
    n = len(rs)
    c2 = sum(cents(r["o8"], r["o2"]) for r in rs) / n
    cc = sum(cents(r["o8"], r["oc"]) for r in rs) / n
    pp = 100 * sum(r["pc"] - r["p8"] for r in rs) / n
    lo = sum(cents(r["o8"], r["oc"]) > 0 for r in rs) / n
    sh = sum(cents(r["o8"], r["oc"]) < 0 for r in rs) / n
    say(f"  {name:44s} n {n:4d} | 8AM->2h {c2:+5.1f}c, 8AM->close {cc:+5.1f}c ({pp:+5.2f} pts to the side; longer {lo:.0%} / shorter {sh:.0%})"
        f" | ROI at 8 AM {roi([(dec(r['o8']), r['won']) for r in rs]):+6.1f}%, 2h before {roi([(dec(r['o2']), r['won']) for r in rs]):+6.1f}%,"
        f" close {roi([(dec(r['oc']), r['won']) for r in rs]):+6.1f}%")


for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf"):
    R = [r for r in rows if r["lg"] == lg]
    say(f" -- {lg.upper()} ({len(R) // 2} games with all three marks)")
    mk("dogs +100..+350 (at 8 AM)", [r for r in R if 100 <= r["o8"] <= 350])
    mk("  dogs +100..+150", [r for r in R if 100 <= r["o8"] <= 150])
    mk("  dogs +151..+350", [r for r in R if 151 <= r["o8"] <= 350])
    mk("  home dogs", [r for r in R if 100 <= r["o8"] <= 350 and r["home"]])
    mk("  road dogs", [r for r in R if 100 <= r["o8"] <= 350 and not r["home"]])
    mk("favorites -101..-150", [r for r in R if -150 <= r["o8"] <= -101])
    mk("favorites -151..-400", [r for r in R if -400 <= r["o8"] <= -151])

say("\n=== (2) OUR OWN PLAYS since 10/1 - the posted price vs 2 hours before vs the close")
P = []
for p in json.load(open("data/sports/picks.json")):
    if p.get("lean") or len(p.get("legs") or []) != 1 or p.get("status") not in ("won", "lost") or p.get("kind") in ("two", "three", "four", "eight"):
        continue
    leg = p["legs"][0]
    if leg.get("market") != "ml":
        continue
    kind = "floor" if p.get("floor") else "gap" if p.get("gap") else "runner-up" if p.get("dog_play") else p["kind"]
    P.append(dict(src="board", kind=kind, lg=leg["league"], gid=leg["game_id"], side=leg["side"], odds=p["american"], start=leg["start"],
                  posted=p.get("posted"), won=p["status"] == "won", units=p.get("units") or 0, date=p["date"], team=leg.get("team")))
for e in json.load(open("data/sports/early.json"))["picks"]:
    if e.get("market") != "ml" or e.get("result") not in ("won", "lost"):
        continue
    P.append(dict(src="early", kind="early:" + str(e.get("spot")), lg=e["league"], gid=e["game_id"], side=e["side"], odds=e["odds"],
                  start=e["start"], posted=e.get("posted"), won=e["result"] == "won", units=e.get("units") or 0, date=e["start"][:10], team=e.get("team")))
ok = []
for p in P:
    s = t(p["start"])
    i = 0 if p["side"] == "home" else 1
    m2, mc = at(p["gid"], s - timedelta(hours=2)), at(p["gid"], s - timedelta(minutes=1))
    if not (m2 and mc):
        continue
    p["o2"], p["oc"] = m2[i], mc[i]
    pc = nv(*mc)
    p["pc"] = pc if i == 0 else 1 - pc
    ok.append(p)
say(f"  graded moneyline unit plays {len(P)}, with a tape price 2h before and at the close {len(ok)}")


def mine(name, rs):
    if not rs:
        return
    n = len(rs)
    c2 = sum(cents(r["odds"], r["o2"]) for r in rs) / n
    cc = sum(cents(r["odds"], r["oc"]) for r in rs) / n
    lo = sum(cents(r["odds"], r["oc"]) > 0 for r in rs)
    sh = sum(cents(r["odds"], r["oc"]) < 0 for r in rs)
    w = sum(r["won"] for r in rs)
    u = sum(r["units"] for r in rs)

    def units(key):
        return sum(r["units"] * ((dec(r[key]) - 1) if r["won"] else -1) for r in rs)
    say(f"  {name:34s} n {n:3d} {w:3d}-{n - w:<3d} | post->2h {c2:+5.1f}c, post->close {cc:+5.1f}c (longer {lo}, shorter {sh}, same {n - lo - sh})"
        f" | flat ROI at the post {roi([(dec(r['odds']), r['won']) for r in rs]):+6.1f}%, 2h before {roi([(dec(r['o2']), r['won']) for r in rs]):+6.1f}%,"
        f" close {roi([(dec(r['oc']), r['won']) for r in rs]):+6.1f}% | units {units('odds'):+.1f} / {units('o2'):+.1f} / {units('oc'):+.1f} on {u:.1f}")


mine("every play", ok)
mine("the board's plays", [r for r in ok if r["src"] == "board"])
mine("the early plays", [r for r in ok if r["src"] == "early"])
for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf"):
    mine(f"board {lg}", [r for r in ok if r["src"] == "board" and r["lg"] == lg])
    mine(f"  {lg} dogs", [r for r in ok if r["src"] == "board" and r["lg"] == lg and r["odds"] >= 100])
    mine(f"  {lg} favorites", [r for r in ok if r["src"] == "board" and r["lg"] == lg and r["odds"] < 0])
for k in sorted({r["kind"] for r in ok}):
    mine(f"kind {k}", [r for r in ok if r["kind"] == k])
say(" -- hockey dogs by where they play")
mine("hockey dog plays, home", [r for r in ok if r["lg"] == "nhl" and r["odds"] >= 100 and r["side"] == "home"])
mine("hockey dog plays, road", [r for r in ok if r["lg"] == "nhl" and r["odds"] >= 100 and r["side"] == "away"])
mine("hockey dog plays, posted by 9 AM PT", [r for r in ok if r["lg"] == "nhl" and r["odds"] >= 100 and r["posted"] and t(r["posted"]).astimezone(PT).hour <= 9])
say(" -- every hockey play, one a line (post -> 2h before -> close)")
for r in sorted([r for r in ok if r["lg"] == "nhl"], key=lambda r: r["date"]):
    say(f"    {r['date']} {r['kind']:10s} {str(r['team'])[:16]:16s} {r['odds']:+5d} -> {r['o2']:+5d} -> {r['oc']:+5d}  {'W' if r['won'] else 'L'} {r['units']:g}u")
json.dump(ok, open(glib.CACHE + "/tape_plays.json", "w"))
