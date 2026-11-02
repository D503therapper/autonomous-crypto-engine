"""STUDY 3 (11/2): RE-VALIDATE THE NBA DOG RULES on 2020-21 .. 2022-23 - the funnel replay on TODAY's code (funnel_1102.py:
every NBA moneyline candidate of every board day, the board's reads and gates, closing prices, params re-tuned each July,
no injury reports; the 2020-22 'open' = the game-day morning look so the 10/30 fade weight reads them). Never in any test:
the 10/9 gate was chosen on 2023-24, the 10/27 own-read / floor / favorite-play rules on 2023-26, the 10/30 sizing on
2023-27 (the 10/30 NBA Lock funnel touched only the first 75 days of 2022-23).
  THE GATE   dog score 4+ (NBA_DOG_GATE) vs the dogs under it
  THE DOG    the board's Dog of the Day (kind 'dog') - NBA_DOG_OWN_UNITS 1u own read over the price / ½u under (DOG_OWN_RULE
             nba None: no own-read gate)
  PRICE      +100..+150 vs +151..+350 (the 10/30 sizing's football / hockey Dog price rule - the NBA kept its own)
  WEIGHTS    the 12+ game slate (+2), the market fade (-2), the soft next game (-2) inside the score
  FLOOR      the 🏀 NBA floor: the best NBA dog by score 0+ a day (½u)
  FAV PLAY   the 🏀 NBA favorite play (kind 'nbafav', 1u) and the Lock test on -101..-150 favorites (study 5's second half)
Graded flat 1u at the CLOSE (the replay's price) and at the game-day MORNING median book (the 8 AM board's hour)."""
import glob
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib                       # noqa: E402

games = lib.load_games()
lk = lib.looks(games)
prev = lib.prev_tips(games)
rows = []
for f in sorted(glob.glob(os.path.join(lib.OUT, "funnel", "f20*.jsonl"))):
    for line in open(f):
        r = json.loads(line)
        if r["league"] == "nba" and r["result"] in ("won", "lost") and r.get("stype") == "2":
            rows.append(r)
seen, uniq = set(), []
for r in rows:
    k = (r["date"], r["team"], r["opp"])
    if k not in seen:
        seen.add(k); uniq.append(r)
rows = uniq
for r in rows:
    r["season"] = lib.season(r["date"] + "T12:00")
    r["won"] = 1 if r["result"] == "won" else 0
    r["pnl"] = lib.profit(r["won"], r["dec"])
    mo = lib.pick_looks(lk, prev, r["game_id"])[1] if r.get("game_id") in lk else None
    r["mml"] = (mo["mh"] if r["side"] == "home" else mo["ma"]) if mo else None
    r["pnl_m"] = lib.profit(r["won"], lib.dec(r["mml"])) if r["mml"] is not None else None
    r["own_over"] = r.get("edge_own") is not None and r["edge_own"] > 0
print(f"rows {len(rows)}, days {len({r['date'] for r in rows})}, seasons {sorted({r['season'] for r in rows})}")
G = [("2020-21", {2020}), ("2021-22", {2021}), ("2022-23", {2022}), ("all 3", {2020, 2021, 2022})]
dogs = [r for r in rows if 100 <= r["odds"] <= 350 and r.get("dog_score") is not None]
C = lib.Cells("NBA DOGS +100..+350 (the funnel's reads), flat 1u at the CLOSE", G)
Mo = lib.Cells("the same cells graded at the game-day MORNING price", G)


def add(name, sel, pool=None):
    for r in (pool if pool is not None else dogs):
        if sel(r):
            C.add(name, r["season"], r["pnl"])
            if r["pnl_m"] is not None:
                Mo.add(name, r["season"], r["pnl_m"])


add("every NBA dog (base)", lambda r: True)
add("dog score under 0", lambda r: r["dog_score"] < 0)
add("dog score 0-2", lambda r: 0 <= r["dog_score"] < 2)
add("dog score 2-4", lambda r: 2 <= r["dog_score"] < 4)
add("THE GATE: dog_gate (score 4+)", lambda r: r.get("dog_gate") is True)
add("  gate + own read over the price (1u today)", lambda r: r.get("dog_gate") is True and r["own_over"])
add("  gate + own read under (½u today)", lambda r: r.get("dog_gate") is True and not r["own_over"])
add("  gate +100..+150", lambda r: r.get("dog_gate") is True and r["odds"] <= 150)
add("  gate +151..+350", lambda r: r.get("dog_gate") is True and r["odds"] > 150)
add("  gate, score 4-6", lambda r: r.get("dog_gate") is True and r["dog_score"] < 6)
add("  gate, score 6+", lambda r: r.get("dog_gate") is True and r["dog_score"] >= 6)
add("THE DOG OF THE DAY (kind dog)", lambda r: r.get("kind") == "dog")
add("  the Dog, own over", lambda r: r.get("kind") == "dog" and r["own_over"])
add("  the Dog, own under", lambda r: r.get("kind") == "dog" and not r["own_over"])
add("  the Dog +100..+150", lambda r: r.get("kind") == "dog" and r["odds"] <= 150)
add("  the Dog +151..+350", lambda r: r.get("kind") == "dog" and r["odds"] > 150)
add("WEIGHT: 12+ game slate (all dogs)", lambda r: (r.get("dog_more") or {}).get("slate", 0) >= 12)
add("WEIGHT: under 12 games (all dogs)", lambda r: (r.get("dog_more") or {}).get("slate", 0) < 12)
add("WEIGHT: market faded 8+ (morning->close moves)", lambda r: r.get("mkt_trend") is not None and r["mkt_trend"] <= -0.08)
add("WEIGHT: the favorite's soft next game", lambda r: bool((r.get("dog_more") or {}).get("opp_next_soft")))
add("raw own read over the price (any score)", lambda r: r["own_over"])

# THE 🏀 NBA FLOOR: the best NBA dog by score 0+ a day (never a trap / fighting), on days with no NBA Dog / favorite play
by = {}
for r in dogs:
    by.setdefault(r["date"], []).append(r)
floor = []
for d, rs in by.items():
    if any(x.get("kind") in ("dog", "nbafav") for x in rows if x["date"] == d):
        continue
    ok = [x for x in rs if x["dog_score"] >= 0 and not x.get("trap") and x.get("fighting") is not True]
    if ok:
        floor.append(max(ok, key=lambda x: x["dog_score"]))
add("THE NBA FLOOR (best dog score 0+ a day, no other NBA unit play)", lambda r: True, floor)
add("  floor +100..+150", lambda r: r["odds"] <= 150, floor)
add("  floor +151..+350", lambda r: r["odds"] > 150, floor)
C.dump(); Mo.dump()

# THE FAVORITES: the 🏀 favorite play and the Lock test at -101..-150
favs = [r for r in rows if -150 <= r["odds"] <= -101]
F = lib.Cells("NBA FAVORITES -101..-150, flat 1u at the CLOSE | the morning price in [ ] below", G)
Fm = lib.Cells("NBA FAVORITES at the MORNING price", G)
for name, sel in (("every favorite -101..-150 (base)", lambda r: True),
                  ("THE NBA FAVORITE PLAY (kind nbafav, 1u)", lambda r: r.get("kind") == "nbafav"),
                  ("favorite-study weight net positive (nba_fav_w)", lambda r: sum((r.get("nba_fav_w") or {}).values()) > 0),
                  ("THE LOCK (kind lock)", lambda r: r.get("kind") == "lock"),
                  ("lock_ok + own_agrees", lambda r: r.get("lock_ok") is True and r.get("own_agrees") is True),
                  ("own read over the price", lambda r: r["own_over"])):
    for r in favs:
        if sel(r):
            F.add(name, r["season"], r["pnl"])
            if r["pnl_m"] is not None:
                Fm.add(name, r["season"], r["pnl_m"])
F.dump(); Fm.dump()
kinds = {}
for r in rows:
    if r.get("kind"):
        kinds.setdefault(r["kind"], []).append(r)
print("\nEVERY NBA UNIT PLAY KIND the replay posted (flat 1u at the close / at the morning):")
K = lib.Cells("", G)
for k, rs in sorted(kinds.items()):
    for r in rs:
        K.add(k, r["season"], r["pnl"])
        if r["pnl_m"] is not None:
            K.add(k + " (morning)", r["season"], r["pnl_m"])
K.dump()
json.dump({"dogs": C.as_dict(), "dogs_morning": Mo.as_dict(), "favs": F.as_dict(), "favs_morning": Fm.as_dict(),
           "kinds": K.as_dict()}, open(os.path.join(lib.OUT, "s3_out.json"), "w"), indent=1)
