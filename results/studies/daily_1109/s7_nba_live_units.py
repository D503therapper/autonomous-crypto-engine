"""S7 - THE LIVE NBA UNIT PLAYS (1-6 since 10/31): every graded NBA unit pick in data/sports/picks.json (read-only),
one line each - kind, price, home / road, rest (b2b), the dog score, the engine's own read vs the no-vig market, the
named reasons, the result - then the shared traits against the replay's base rates: is anything systematic beyond the
+200..+350 band the 11/6 study reported? Wins vs the vigged price (z) per trait."""
import json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

pk = json.load(open("data/sports/picks.json"))
rows = []
for x in pk:
    if x.get("status") not in ("won", "lost") or not x.get("units") or x.get("void") or x.get("pulled"):
        continue
    legs = x.get("legs") or [{}]
    if len(legs) != 1 or legs[0].get("league") != "nba":
        continue
    l = legs[0]
    d = l.get("dec") or x.get("dec")
    own = (l["edge_own"] + 1) / d if l.get("edge_own") is not None and d else None
    kind = ("dog_play" if x.get("dog_play") else "floor" if x.get("floor") else "best" if x.get("best") else x.get("kind"))
    rows.append({"date": x["date"], "team": l.get("team"), "opp": l.get("opp"), "odds": l.get("odds"), "dec": d,
                 "home": l.get("home"), "kind": kind, "units": x["units"], "won": x["status"] == "won",
                 "b2b": l.get("b2b_me"), "tired_vs_rested": l.get("tired_vs_rested"), "rested_vs_b2b": l.get("rested_vs_b2b"),
                 "dog_score": l.get("dog_score"), "own": own, "mkt": l.get("p_market"), "p": l.get("p"),
                 "games_in": l.get("games_in"), "outs": len(l.get("outs") or []), "opp_outs": len(l.get("opp_outs") or []),
                 "reasons": l.get("reasons") or [], "midday": bool(x.get("midday")), "result": l.get("result")})
out = []
for r in rows:
    out.append(f"{r['date']} {r['kind']:8s} {r['units']:.1f}u {r['team']:14s} {'vs' if r['home'] else '@'} {r['opp'] or '?':14s} "
               f"{r['odds']:+5.0f} {'W' if r['won'] else 'L'} | own {r['own'] or 0:.3f} mkt {r['mkt'] or 0:.3f} "
               f"dog score {r['dog_score']} | games in {r['games_in']} | b2b {r['b2b']} | outs {r['outs']} vs {r['opp_outs']} "
               f"| midday {r['midday']} | {r['result']}")
    for why in r["reasons"][:4]:
        out.append(f"      - {why[:150]}")


def line(name, xs):
    if not xs:
        return f"  {name:44s} -"
    w = sum(r["won"] for r in xs)
    flat = sum(((r["dec"] - 1) if r["won"] else -1) for r in xs)
    uu = sum(r["units"] * ((r["dec"] - 1) if r["won"] else -1) for r in xs)
    exp = sum(1 / r["dec"] for r in xs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in xs)
    z = (w - exp) / var ** 0.5 if var else 0
    return f"  {name:44s} {w}-{len(xs) - w}  flat {flat:+.2f}u  as posted {uu:+.2f}u  expected wins {exp:.1f}  z {z:+.2f}"


out.append("\nTRAITS")
for name, f in (("all", lambda r: True), ("dogs", lambda r: r["odds"] > 0), ("favorites", lambda r: r["odds"] < 0),
                ("home", lambda r: r["home"]), ("road", lambda r: not r["home"]),
                ("+100..+199", lambda r: 100 <= r["odds"] <= 199), ("+200..+350", lambda r: r["odds"] >= 200),
                ("own read over the price", lambda r: r["own"] and r["own"] > 1 / r["dec"]),
                ("own read NOT over the price", lambda r: not (r["own"] and r["own"] > 1 / r["dec"])),
                ("midday add", lambda r: r["midday"]), ("8 AM board", lambda r: not r["midday"]),
                ("team games 1-10", lambda r: (r["games_in"] or 0) < 10),
                ("we have more outs", lambda r: r["outs"] > r["opp_outs"]),
                ("an injury reason named", lambda r: any("out" in w.lower() or "miss" in w.lower() for w in r["reasons"]))):
    out.append(line(name, [r for r in rows if f(r)]))
by = defaultdict(list)
for r in rows:
    by[r["kind"]].append(r)
for k, v in sorted(by.items()):
    out.append(line(f"kind {k}", v))
txt = "\n".join(out)
print(txt)
open(os.path.join(HERE, "s7_out.txt"), "w").write(txt + "\n")
