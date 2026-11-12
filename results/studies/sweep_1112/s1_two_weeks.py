"""11/12 FULL SWEEP, part 1 - THE LAST TWO WEEKS, PLAY BY PLAY (10/29 -> 11/11): every graded unit play (the dashboard's
own ledger, sports.units_ledger - board + early), then the leans; for each: the kind, the price, the engine's reads (the
blended win %, the OWN read, the no-vig market), the close and how far we beat it, the result. Then the numbers: units
by kind / sport / day / side / size / slot, and HOW MUCH IS VARIANCE: the wins the no-vig market expected at our prices
(and at the close) against the wins we got, with the sd.   Read-only.
Usage: python results/studies/sweep_1112/s1_two_weeks.py > results/studies/sweep_1112/s1_two_weeks.out"""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_early  # noqa: E402

FROM = os.environ.get("FROM", "2026-10-29")
picks = json.load(open("data/sports/picks.json"))
EST = json.load(open("data/sports/early.json"))
early = EST.get("picks") or []
led = sports.units_ledger(picks, early)
clv = {(c["date"], c["team"], c.get("market") or "ml"): c for c in json.load(open("data/sports/clv_record.json")).get("picks") or []}
jr = {(j["date"], j["team"], j.get("market") or "ml"): j for j in json.load(open("data/sports/pick_journal.json"))}
games = {}
for lg in sd.LEAGUES:
    try:
        games.update(sd.load_games(lg))
    except Exception:  # noqa: BLE001
        pass


def imp(o):
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def pt_day(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(sports.PT).strftime("%Y-%m-%d")


rows = []
for p, u, net, _ in led["rows"]:
    if u <= 0 or not net:
        continue
    l = (p.get("legs") or [{}])[0]
    am = l.get("odds") or p.get("american")
    dec = sports._dec(am)
    e = None
    if p.get("kind") == "early":
        e = next((x for x in early if x.get("team") == l.get("team") and x.get("odds") == am and x.get("result") in ("won", "lost")
                  and pt_day(x["start"]) == p["date"]), None)
        kind = "early:" + ((e or {}).get("spot") or "exam")
    else:
        kind = "parlay leg" if p.get("kind") == "pick" else sports.posted_kind(p)
        if kind == "play":
            kind = "value play"
    posted = (e or p).get("posted") or ""
    slot = "early"
    if not e:
        try:
            ph = datetime.strptime(posted, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(sports.PT)
            slot = "8 AM" if ph.hour < 9 else "mid-day" if ph.hour < 14 else "2 PM on"
        except ValueError:
            slot = "?"
    c = clv.get((p["date"], l.get("team"), l.get("market") or "ml")) or {}
    j = jr.get((p["date"], l.get("team"), l.get("market") or "ml")) or {}
    close = c.get("close") if c else None
    pm = l.get("p_market")
    cl_p = None
    if e:                                                    # an early play: the game file's close, no-vig
        g = games.get(e["game_id"]) or {}
        s, o = e["side"], "away" if e["side"] == "home" else "home"
        a, b = sports_early._int(g.get(f"ml_{s}")), sports_early._int(g.get(f"ml_{o}"))
        pm = e.get("mkt")
        if a and b and e.get("market") != "total":
            close, cl_p = a, imp(a) / (imp(a) + imp(b))
    elif close is not None and pm is not None:
        cl_p = pm + (c.get("pts") or 0) / 100                # the close's no-vig = our no-vig + the move to us
    own = (e or {}).get("own") if e else (l.get("raw_own") if l.get("edge_own") is None else (l["edge_own"] + 1) / dec)
    rows.append(dict(date=p["date"], u=u, net=net, won=net > 0, am=am, dec=dec, kind=kind, lg=l.get("league") or p.get("league"), team=l.get("team"),
                     opp=l.get("opp") or (e or {}).get("opp"), home=l.get("home") if not e else e.get("side") == "home", pm=pm, p=l.get("p"), own=own,
                     close=close, cl_p=cl_p, clv=c.get("pts") if c else (None if cl_p is None or pm is None else round(100 * (cl_p - pm), 2)),
                     slot=slot, best=bool(p.get("best")), reasons=l.get("reasons") or (e or {}).get("spots") or [], score=j.get("score") or (e or {}).get("score"),
                     dow=datetime.strptime(p["date"], "%Y-%m-%d").strftime("%a"), ds=l.get("dog_score"), posted=posted,
                     outs=l.get("outs") or [], opp_outs=l.get("opp_outs") or []))
allrows = rows
rows = [r for r in rows if r["date"] >= FROM]


def pc(x):
    return "  -  " if x is None else f"{x * 100:4.1f}%"


print(f"EVERY GRADED UNIT PLAY {FROM} -> {rows[-1]['date']} ({len(rows)} plays)")
print("date  dow  lg     kind            side                      price  units  blend  own    mkt   | close  beat-close | result  net   | score / slot / why")
for r in rows:
    print(f"{r['date'][5:]} {r['dow']} {r['lg'] or '':6s} {r['kind']:15s} {(r['team'] or '')[:17]:17s} {'H' if r['home'] else 'A'} v {(r['opp'] or '')[:14]:14s} {r['am']:+5d} {r['u']:3.1f}u "
          f"{pc(r['p'])} {pc(r['own'])} {pc(r['pm'])} | {('%+5d' % r['close']) if r['close'] else '  -  '} {('%+5.1f' % r['clv']) if r['clv'] is not None else '  -  '} | "
          f"{'WON ' if r['won'] else 'lost'} {r['net']:+5.2f}u | {r['score'] or ''} | {r['slot']}{' ⭐' if r['best'] else ''} | {'; '.join(str(x) for x in r['reasons'])[:150]}")


def line(name, rs):
    if not rs:
        return
    w = sum(r["won"] for r in rs)
    st = sum(r["u"] for r in rs)
    pr = sum(r["net"] for r in rs)
    flat = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    z = (w - bev) / math.sqrt(var) if var else 0
    print(f"  {name:38s} {w:3d}-{len(rs) - w:<3d} {pr:+7.2f}u on {st:5.1f}u ({pr / st * 100:+6.1f}%)  flat 1u {flat / len(rs) * 100:+6.1f}%  the price expects {bev:5.1f} wins  z {z:+.2f}")


def cut(title, key, rs=None):
    print(f"\n{title}")
    d = defaultdict(list)
    for r in (rs or rows):
        k = key(r)
        if k is not None:
            d[k].append(r)
    for k in sorted(d, key=lambda k: sum(r["net"] for r in d[k])):
        line(str(k), d[k])


print()
line("ALL UNIT PLAYS, the two weeks", rows)
line("   before that (9/27 -> 10/28)", [r for r in allrows if r["date"] < FROM])
line("   favorites", [r for r in rows if r["am"] < 0])
line("   dogs", [r for r in rows if r["am"] > 0])
cut("BY KIND", lambda r: r["kind"])
cut("BY SPORT", lambda r: r["lg"])
cut("BY SPORT x SIDE", lambda r: f"{r['lg']} {'dog' if r['am'] > 0 else 'fav'}")
cut("BY DAY", lambda r: r["date"] + " " + r["dow"])
cut("BY WEEK", lambda r: "10/29-11/04" if r["date"] <= "2026-11-04" else "11/05-11/11")
cut("BY SIZE", lambda r: f"{r['u']}u")
cut("BY SLOT", lambda r: r["slot"])
cut("BY PRICE", lambda r: "fav" if r["am"] < 0 else "+100..+119" if r["am"] < 120 else "+120..+150" if r["am"] <= 150 else "+151..+199" if r["am"] < 200 else "+200 on")
cut("HOME / ROAD x SIDE", lambda r: ("home" if r["home"] else "road") + (" dog" if r["am"] > 0 else " fav"))
cut("COLLEGE FOOTBALL DOGS by kind", lambda r: r["kind"] if r["lg"] == "ncaaf" and r["am"] > 0 else None)
cut("SATURDAYS", lambda r: r["date"] if r["dow"] == "Sat" else None)

# ---- how much is variance
print("\nHOW MUCH IS BAD LUCK (the wins the no-vig MARKET expected, at the number we bet and at the close)")
for name, rs in (("all unit plays", rows), ("dogs", [r for r in rows if r["am"] > 0]), ("favorites", [r for r in rows if r["am"] < 0]),
                 ("college football dogs", [r for r in rows if r["lg"] == "ncaaf" and r["am"] > 0]),
                 ("everything but college football dogs", [r for r in rows if not (r["lg"] == "ncaaf" and r["am"] > 0)])):
    a = [r for r in rs if r["pm"] is not None]
    if not a:
        continue
    w = sum(r["won"] for r in a)
    e = sum(r["pm"] for r in a)
    s = math.sqrt(sum(r["pm"] * (1 - r["pm"]) for r in a))
    eu = sum(r["u"] * (r["pm"] * r["dec"] - 1) for r in a)                 # the units a fair-market bettor expects (the vig)
    su = math.sqrt(sum((r["u"] * r["dec"]) ** 2 * r["pm"] * (1 - r["pm"]) for r in a))
    net = sum(r["net"] for r in a)
    c = [r for r in a if r["cl_p"] is not None]
    ec = sum(r["cl_p"] for r in c)
    euc = sum(r["u"] * (r["cl_p"] * r["dec"] - 1) for r in c)
    print(f"  {name:38s} n {len(a):3d} won {w:2d} | the market at our number expected {e:5.1f} wins (sd {s:.1f}) z {(w - e) / s:+.2f} | units {net:+6.2f} vs {eu:+5.2f} expected "
          f"(sd {su:.1f}u) z {(net - eu) / su:+.2f} | the CLOSE expected {ec:5.1f} wins on the {len(c)} with a close ({sum(r['won'] for r in c)} won), {euc:+5.2f}u")

# ---- the closing line on the losses
print("\nPRICE: the close against the number we bet (points of no-vig win %; + = the money came to our side)")
for name, rs in (("all with a close", rows), ("losses", [r for r in rows if not r["won"]]), ("wins", [r for r in rows if r["won"]]),
                 ("8 AM board", [r for r in rows if r["slot"] == "8 AM"]), ("mid-day adds", [r for r in rows if r["slot"] == "mid-day"]),
                 ("2 PM on", [r for r in rows if r["slot"] == "2 PM on"]), ("early plays", [r for r in rows if r["slot"] == "early"])):
    c = [r for r in rs if r["clv"] is not None]
    if c:
        m = sum(r["clv"] for r in c) / len(c)
        print(f"  {name:20s} n {len(c):3d} avg {m:+5.2f} pts | beat {sum(r['clv'] > 0.25 for r in c)} / same {sum(abs(r['clv']) <= 0.25 for r in c)} / worse {sum(r['clv'] < -0.25 for r in c)}"
              f" | ran 2+ AWAY: {sum(r['won'] for r in c if r['clv'] <= -2)}-{sum(not r['won'] for r in c if r['clv'] <= -2)}; came 2+ to us: {sum(r['won'] for r in c if r['clv'] >= 2)}-{sum(not r['won'] for r in c if r['clv'] >= 2)}")

# ---- the leans
print(f"\nTHE LEANS {FROM} on (no units; flat 1u for the read only)")
ln = []
for p in picks:
    if not p.get("lean") or p.get("status") not in ("won", "lost") or p.get("pulled") or p.get("void") or p.get("date", "") < FROM:
        continue
    l = (p.get("legs") or [{}])[0]
    am = l.get("odds") or p.get("american")
    c = clv.get((p["date"], l.get("team"), l.get("market") or "ml")) or {}
    ln.append(dict(u=1, net=(sports._dec(am) - 1) if p["status"] == "won" else -1, won=p["status"] == "won", am=am, dec=sports._dec(am), lg=l.get("league"),
                   market=l.get("market") or "ml", date=p["date"]))
    print(f"  {p['date'][5:]} {l.get('league'):6s} {(l.get('team') or '')[:16]:16s} v {(l.get('opp') or '')[:14]:14s} {(l.get('market') or 'ml'):6s} {l.get('line') or '':>5} {am:+5d} blend {pc(l.get('p'))} own {pc(l.get('raw_own'))} "
          f"mkt {pc(l.get('p_market'))} close {c.get('close')} -> {p['status']}")
line("all leans", ln)
for k in sorted({r["lg"] for r in ln}):
    line(f"leans {k}", [r for r in ln if r["lg"] == k])
line("leans moneyline favorites", [r for r in ln if r["am"] < 0 and r["market"] == "ml"])
line("leans on a spread", [r for r in ln if r["market"] != "ml"])
json.dump(allrows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1_rows.json"), "w"), indent=0, default=str)
