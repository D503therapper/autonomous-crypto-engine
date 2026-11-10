"""S1 - THE ½u HOCKEY FLOOR, LIVE vs THE REPLAY (the 11/5 '½u LONGSHOT LEAK' 1b cell and its WATCH: "if the tag
reaches 80 rows still under -15%, cut the hockey floor to +100..+129").
LIVE (read only): every graded hockey floor play in data/sports/picks.json (the card's 'floor' mark), every hockey ½u
dog, and the tracker tag "hockey dog score 0-6" (data/sports/lead_tracker.json rows, graded here on the NHL game
file the way sports_leads.grade does - so the record is checkable by price band / score band / date).
THE REPLAY: the 11/5 s1b numbers (results/studies/daily_1105/s1b_out.txt - the (c15) board, 2023-26 + 10/13-10/29).
How unusual is live: z of the wins vs the price; and a binomial on the replay's ROI per band."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402
import sports_data as sd  # noqa: E402

out = []


def say(s=""):
    print(s)
    out.append(s)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def line(name, rs, stake=lambda r: 1.0):
    if not rs:
        say(f"{name:58s} -")
        return
    w = sum(r["won"] for r in rs)
    st = sum(stake(r) for r in rs)
    pr = sum(((dec(r["am"]) - 1) if r["won"] else -1) * stake(r) for r in rs)
    bev = sum(1 / dec(r["am"]) for r in rs)
    var = sum((1 / dec(r["am"])) * (1 - 1 / dec(r["am"])) for r in rs)
    z = (w - bev) / math.sqrt(var) if var else 0
    say(f"{name:58s} {w:3d}-{len(rs)-w:<3d} {pr:+7.2f}u on {st:5.1f}u ({pr/st*100:+6.1f}%)  price expects "
        f"{bev:5.1f} wins  z {z:+.2f}")


# ---------------- live: picks.json
p = json.load(open("data/sports/picks.json"))
floor, half = [], []
for x in p:
    lg = (x.get("legs") or [{}])[0].get("league")
    if lg != "nhl" or x.get("lean") or x.get("pulled") or x.get("void"):
        continue
    leg = x["legs"][0]
    r = dict(date=x["date"], team=leg.get("team"), am=x["american"], status=x.get("status"),
             won=x.get("status") == "won", score=(x.get("floor") or {}).get("dog_score"), u=sports.units_for(x)
             if x.get("status") in ("won", "lost") else x.get("units"), own=leg.get("raw_own"),
             mkt=leg.get("p_market"), kind=x["kind"])
    if x.get("floor"):
        floor.append(r)
    if x["american"] > 0 and r["u"] == 0.5:
        half.append(r)

say("LIVE HOCKEY FLOOR PLAYS (every one posted; graded ones counted)")
for r in floor:
    gap = (r["own"] - r["mkt"]) * 100 if r["own"] is not None and r["mkt"] is not None else None
    say(f"  {r['date']} {r['team']:14s} {r['am']:+5d} score {r['score']:+6.2f}  own-market "
        f"{gap:+5.1f} pts  {r['status']}")
g = [r for r in floor if r["status"] in ("won", "lost")]
line("hockey floor, all graded (1u flat)", g)
line("hockey floor +100..+129", [r for r in g if r["am"] <= 129])
line("hockey floor +130..+350", [r for r in g if r["am"] >= 130])
line("hockey floor, own read under the market", [r for r in g if r["own"] is not None and r["own"] < r["mkt"]])
line("hockey floor, own read at/over the market", [r for r in g if r["own"] is not None and r["own"] >= r["mkt"]])
line("hockey floor since 10/31", [r for r in g if r["date"] >= "2026-10-31"])
say()
gh = [r for r in half if r["status"] in ("won", "lost")]
line("every hockey ½u dog (floor + value play + ½u Dog)", gh)
line("  ... +100..+129", [r for r in gh if r["am"] <= 129])
line("  ... +130..+350", [r for r in gh if r["am"] >= 130])
say()
# every live floor play, any sport, since 10/31 (the coordinator's '2-5 since 10/31')
allf = []
for x in p:
    if x.get("floor") and x.get("status") in ("won", "lost") and x["date"] >= "2026-10-31" and not x.get("lean"):
        allf.append(dict(am=x["american"], won=x["status"] == "won",
                         lg=(x.get("legs") or [{}])[0].get("league")))
line("EVERY floor play since 10/31 (any sport)", allf)
line("  ... NHL", [r for r in allf if r["lg"] == "nhl"])
line("  ... NBA / NFL", [r for r in allf if r["lg"] != "nhl"])
say()

# ---------------- live: the tracker tag
TAG = "hockey dog score 0-6"
games = sd.load_games("nhl")
rows = []
for r in json.load(open("data/sports/lead_tracker.json")):
    if TAG not in r.get("tags", []):
        continue
    o = r.get("odds") or 100
    if o > 350:
        continue
    gm = games.get(r["game_id"]) or {}
    if gm.get("status") != "final":
        continue
    try:
        hs, as_ = float(gm["home_score"]), float(gm["away_score"])
    except (KeyError, TypeError, ValueError):
        continue
    if hs == as_:
        continue
    rows.append(dict(date=r["day"], am=o, won=(hs > as_) == (r["side"] == "home"), team=r.get("team")))
say(f"THE TRACKER TAG '{TAG}' (graded here; the WATCH line: 80 rows, under -15%)")
line("tag, all graded", rows)
line("tag +100..+129", [r for r in rows if r["am"] <= 129])
line("tag +130..+159", [r for r in rows if 130 <= r["am"] <= 159])
line("tag +160..+350", [r for r in rows if r["am"] >= 160])
line("tag to 11/4 (the 11/5 read)", [r for r in rows if r["date"] <= "2026-11-04"])
line("tag 11/5 on (since the read)", [r for r in rows if r["date"] >= "2026-11-05"])
for a, b in (("2026-10-01", "2026-10-15"), ("2026-10-16", "2026-10-31"), ("2026-11-01", "2026-11-10")):
    line(f"tag {a[5:]}..{b[5:]}", [r for r in rows if a <= r["date"] <= b])
say()
# what would the remaining 31 rows need to do for the 80-row read to land under -15%
n = len(rows)
pr = sum(((dec(r["am"]) - 1) if r["won"] else -1) for r in rows)
need = -0.15 * 80 - pr
avg_dec = sum(dec(r["am"]) for r in rows) / max(1, n)
say(f"rows graded {n}; to sit under -15% at 80 the next {80 - n} rows must lose more than {-need:.1f}u "
    f"({need / max(1, 80 - n) * 100:+.1f}% a row) - at the tag's average price {avg_dec:.2f} that is a "
    f"{(1 + need / max(1, 80 - n)) / avg_dec * 100:.0f}% win rate or worse vs the price's {100 / avg_dec:.0f}%")
say()
say("THE REPLAY (11/5 s1b, the (c15) board, closing prices): NHL floor +100..+129 45-34 +21.6% (train +17.3% / "
    "held +29.4%, 4/4); +130..+159 13-18 +1.0% (held -18.4%); +160..+350 10-17 +3.6%; score 0..6 41-45 +9.3%; "
    "every clean NHL dog score 0-6 +4.3% on 856 (the tag's pool)")
open(os.path.join(HERE, "s1_out.txt"), "w").write("\n".join(out) + "\n")
