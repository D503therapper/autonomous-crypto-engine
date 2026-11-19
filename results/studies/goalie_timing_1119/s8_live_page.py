"""S8 - (c) LIVE, 10/6 -> 11/18: the goalie page (Daily Faceoff, data/sports/nhl_goalies.json - every commit of it in
this repo's history) x our line tape x our hockey plays.
  - what the page said at the 8 AM PT board (a name, 'confirmed' or a guess) vs who started
  - WHEN each side's starter was first confirmed (hours before the puck)
  - the price of the side at 8 AM, at the first confirmation, and at the close - what waiting for the confirmation
    cost or paid, for the whole market and for OUR hockey plays
  - our hockey plays whose own / other goalie turned out NOT to be the 8 AM name: the record
Inputs: results/studies/daily_1113/snaps.txt + ~/.cache/d503_goalie1119/snaps_new.txt (hash + commit time of each
nhl_goalies.json commit - `git log --format='%H %cI' -- data/sports/nhl_goalies.json`)."""
import csv
import glob
import json
import os
import pickle
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import glib
from glib import dec, nv, sane

say = glib.Tee(glib.HERE + "/s8_live_page.out")
PT, UTC = ZoneInfo("America/Los_Angeles"), ZoneInfo("UTC")


def t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)


def nm(x):
    return " ".join(str(x or "").lower().replace(".", "").split())


cache = glib.CACHE + "/page_snaps.pkl"
if os.path.exists(cache):
    SNAP = pickle.load(open(cache, "rb"))
else:
    hs = []
    for f in (glib.ROOT + "/results/studies/daily_1113/snaps.txt", glib.CACHE + "/snaps_new.txt"):
        if os.path.exists(f):
            for ln in open(f):
                if ln.strip():
                    h, tm = ln.split()
                    hs.append((datetime.fromisoformat(tm).astimezone(UTC), h))
    hs = sorted(set(hs))
    SNAP = []
    for tm, h in hs:
        try:
            d = json.loads(subprocess.run(["git", "show", f"{h}:data/sports/nhl_goalies.json"], capture_output=True, text=True).stdout)
        except ValueError:
            continue
        seen = d.get("seen")
        if not seen:
            continue
        SNAP.append((seen, {gid: {s: (v.get("name"), v.get("status")) for s, v in g.items()} for gid, g in (d.get("games") or {}).items()}))
    pickle.dump(SNAP, open(cache, "wb"))
SNAP.sort(key=lambda x: x[0])
say(f"page snapshots: {len(SNAP)}, {SNAP[0][0]} -> {SNAP[-1][0]}")

G = glib.goalies()
GAMES = {}
for f in sorted(glob.glob("data/sports/games/nhl/2026-1*.csv")):
    for g in csv.DictReader(open(f)):
        if g["status"] == "final" and g["start"] >= "2026-10-06":
            GAMES[g["id"]] = g
HIST = defaultdict(list)
for f in sorted(glob.glob("data/sports/line_history/*.jsonl")):
    for ln in open(f):
        try:
            r = json.loads(ln)
            if r["g"].startswith("nhl") and r["t"] < r["s"] and r.get("h") is not None and r.get("a") is not None:
                HIST[r["g"]].append((r["t"], int(float(r["h"])), int(float(r["a"]))))
        except (ValueError, KeyError, TypeError):
            pass
for v in HIST.values():
    v.sort()


def price(gid, when):
    w = when.strftime("%Y-%m-%dT%H:%MZ")
    last = None
    for tt, h, a in HIST.get(gid, []):
        if tt <= w:
            last = (h, a)
        else:
            break
    return last if last and sane(*last) else None


by_game = defaultdict(list)                       # gid -> [(seen, {side: (name, status)})]
for seen, games in SNAP:
    for gid, v in games.items():
        by_game[gid].append((seen, v))

rows = []
for gid, g in GAMES.items():
    st_ = t(g["start"])
    eight = st_.astimezone(PT).replace(hour=8, minute=0).astimezone(UTC)
    if eight >= st_ or gid not in by_game:
        continue
    for i, s in enumerate(("home", "away")):
        act = (G.get((gid, g[s])) or {}).get("actual")
        if not act:
            continue
        at8 = None
        first_conf = None
        for seen, v in by_game[gid]:
            ts = t(seen)
            if ts >= st_:
                break
            x = v.get(s)
            if not x or not x[0]:
                continue
            if ts <= eight + timedelta(minutes=20) and (st_ - ts) < timedelta(hours=30):
                at8 = x
            if x[1] == "confirmed" and first_conf is None:
                first_conf = (ts, x[0])
        p8, pc = price(gid, eight + timedelta(minutes=20)), price(gid, st_ - timedelta(minutes=1))
        pf = price(gid, first_conf[0] + timedelta(minutes=70)) if first_conf else None   # the first look an hourly run after it
        gm = G[(gid, g[s])]
        rows.append(dict(gid=gid, side=s, i=i, team=g[s + "_name"], start=g["start"], actual=act, at8=at8, conf=first_conf,
                         p8=p8, pf=pf, pc=pc, n1=gm["n1"], proj=gm["proj"], b2b=gm["b2b"],
                         won=(int(g["home_score"]) > int(g["away_score"])) == (s == "home")))
say(f"game sides 10/6 -> 11/18 with a page look before the puck: {len(rows)}")

a8 = [r for r in rows if r["at8"]]
say("\n=== what the page said at the 8 AM PT board vs who started")
for lab, f in (("CONFIRMED at 8 AM", lambda r: r["at8"][1] == "confirmed"), ("likely / expected at 8 AM", lambda r: r["at8"][1] in ("likely", "expected")),
               ("a guess at 8 AM (unconfirmed / projected)", lambda r: r["at8"][1] in ("unconfirmed", "projected"))):
    c = [r for r in a8 if f(r)]
    if c:
        ok = sum(nm(r["at8"][0]) == nm(r["actual"]) for r in c)
        say(f"  {lab:44s} {len(c):4d} sides ({len(c) / len(a8):.0%}); the name started {ok}/{len(c)} = {ok / len(c):.1%}")
c = [r for r in a8 if r["proj"]]
say(f"  our own projection (no page) on the same sides: {sum(nm(r['proj']) == nm(r['actual']) for r in c)}/{len(c)} = {sum(nm(r['proj']) == nm(r['actual']) for r in c) / len(c):.1%}")
c = [r for r in a8 if r["b2b"]]
say(f"  the page's 8 AM name on a b2b night 2: {sum(nm(r['at8'][0]) == nm(r['actual']) for r in c)}/{len(c)}")

say("\n=== when the starter was first CONFIRMED on the page (hours before the puck; our hourly runs' looks)")
cf = [r for r in rows if r["conf"]]
hrs = sorted((t(r["start"]) - r["conf"][0]).total_seconds() / 3600 for r in cf)
say(f"  confirmed before the puck on {len(cf)}/{len(rows)} sides; hours before: median {hrs[len(hrs) // 2]:.1f}, "
    f"a quarter by {hrs[3 * len(hrs) // 4]:.1f}h, three quarters by {hrs[len(hrs) // 4]:.1f}h")
pt_h = sorted(r["conf"][0].astimezone(PT).hour + r["conf"][0].astimezone(PT).minute / 60 for r in cf)
say(f"  Pacific clock of the first confirmation: median {pt_h[len(pt_h) // 2]:.1f}h; by 8:20 AM {sum(x <= 8.34 for x in pt_h) / len(pt_h):.0%}, "
    f"by 10 AM {sum(x <= 10 for x in pt_h) / len(pt_h):.0%}, by noon {sum(x <= 12 for x in pt_h) / len(pt_h):.0%}, by 2 PM {sum(x <= 14 for x in pt_h) / len(pt_h):.0%}")
ok = sum(nm(r["conf"][1]) == nm(r["actual"]) for r in cf)
say(f"  the confirmed name started: {ok}/{len(cf)} = {ok / len(cf):.1%} (the rest: a late scratch or our box's most-shots man after a pull)")


def cents(a, b):
    def u(o):
        return o - 100 if o > 0 else o + 100
    return u(b) - u(a)


say("\n=== the price: 8 AM -> the first look after the confirmation -> the close (the side whose goalie it is)")


def mv(name, rs):
    rs = [r for r in rs if r["p8"] and r["pc"]]
    if len(rs) < 5:
        say(f"  {name:58s} n {len(rs)}")
        return
    def p(q, i):
        x = nv(*q)
        return x if i == 0 else 1 - x
    m = 100 * sum(p(r["pc"], r["i"]) - p(r["p8"], r["i"]) for r in rs) / len(rs)
    big = sum(abs(p(r["pc"], r["i"]) - p(r["p8"], r["i"])) >= 0.02 for r in rs)
    say(f"  {name:58s} n {len(rs):4d} | the market's move to this team 8 AM -> close {m:+5.2f} pts; moved 2+ pts either way {big}/{len(rs)}")


g8 = [r for r in a8 if r["at8"][1] != "confirmed"]
mv("the 8 AM name started (page guess right)", [r for r in g8 if nm(r["at8"][0]) == nm(r["actual"])])
mv("the 8 AM name did NOT start", [r for r in g8 if nm(r["at8"][0]) != nm(r["actual"])])
mv("  ...8 AM said the #1, another man started", [r for r in g8 if nm(r["at8"][0]) != nm(r["actual"]) and r["n1"] and nm(r["at8"][0]) == nm(r["n1"])])
mv("  ...8 AM said another man, the #1 started", [r for r in g8 if nm(r["at8"][0]) != nm(r["actual"]) and r["n1"] and nm(r["actual"]) == nm(r["n1"])])

say("\n=== OUR hockey plays 10/6 -> 11/18 x the 8 AM page")
SIDE = {(r["gid"], r["side"]): r for r in rows}
plays = []
for p in json.load(open("data/sports/picks.json")):
    if p.get("lean") or len(p.get("legs") or []) != 1 or p.get("status") not in ("won", "lost"):
        continue
    leg = p["legs"][0]
    if leg.get("league") != "nhl" or leg.get("market") != "ml":
        continue
    me = SIDE.get((leg["game_id"], leg["side"]))
    op = SIDE.get((leg["game_id"], "away" if leg["side"] == "home" else "home"))
    if not me or not op:
        continue
    plays.append(dict(date=p["date"], team=leg["team"], odds=p["american"], units=p.get("units") or 0, won=p["status"] == "won", me=me, op=op,
                      kind="floor" if p.get("floor") else "runner-up" if p.get("dog_play") else p["kind"]))


def rec(name, ps):
    if not ps:
        say(f"  {name:62s} none")
        return
    w = sum(x["won"] for x in ps)
    u = sum(x["units"] * ((dec(x["odds"]) - 1) if x["won"] else -1) for x in ps)
    fl = 100 * sum((dec(x["odds"]) - 1) if x["won"] else -1 for x in ps) / len(ps)
    say(f"  {name:62s} {w}-{len(ps) - w}  flat {fl:+6.1f}%  units {u:+.1f} on {sum(x['units'] for x in ps):.1f}")


def right(r):
    return None if not r["at8"] else nm(r["at8"][0]) == nm(r["actual"])


def role(r):
    return None if not r["n1"] else "n1" if nm(r["actual"]) == nm(r["n1"]) else "bk"


say(f"  hockey unit plays matched to the page: {len(plays)}")
rec("every play", plays)
rec("both 8 AM names started", [x for x in plays if right(x["me"]) and right(x["op"])])
rec("OUR 8 AM name did not start", [x for x in plays if right(x["me"]) is False])
rec("THEIR 8 AM name did not start", [x for x in plays if right(x["op"]) is False])
rec("our #1 started", [x for x in plays if role(x["me"]) == "n1"])
rec("our backup started", [x for x in plays if role(x["me"]) == "bk"])
rec("their #1 started", [x for x in plays if role(x["op"]) == "n1"])
rec("their backup started", [x for x in plays if role(x["op"]) == "bk"])
dg = [x for x in plays if x["odds"] >= 100]
rec("DOGS: their #1 started", [x for x in dg if role(x["op"]) == "n1"])
rec("DOGS: their backup started", [x for x in dg if role(x["op"]) == "bk"])
rec("DOGS: our 8 AM name did not start", [x for x in dg if right(x["me"]) is False])
say("  one a line (8 AM name -> who started, ours / theirs):")
for x in sorted(plays, key=lambda x: x["date"]):
    m, o = x["me"], x["op"]
    say(f"    {x['date']} {x['kind']:9s} {x['team'][:14]:14s} {x['odds']:+5d} {x['units']:g}u {'W' if x['won'] else 'L'} | ours: {(m['at8'] or ('?', '?'))[0]} ({(m['at8'] or ('?', '?'))[1]}) -> {m['actual']}"
        f"{'' if right(m) else '  **'} | theirs: {(o['at8'] or ('?', '?'))[0]} -> {o['actual']}{'' if right(o) else '  **'} [{role(o) or '-'}]")
