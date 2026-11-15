"""11/15 - THE EXAM SCAN, WALK-FORWARD: the early-price exam (sports_early.exam) re-run one test season at a time - the
engine learns on the LEARN_Y (3) seasons before the test season, then every +100..+280 dog of that season is graded at
its EARLY price (the open, only if the scan could have bet it - sports_early.bettable) with the raw own read the scan
sizes on. One row a dog: league, season, start, open / close odds, own, no-vig market at the open, gap, won.
Rows -> ~/.cache/d503_sizing1115/exam_<league>.jsonl.  Usage: python e1_exam_rows.py ncaaf [first_season]"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd      # noqa: E402
import sports_early as se     # noqa: E402
import sports_model as sm     # noqa: E402

CACHE = os.path.expanduser("~/.cache/d503_sizing1115")
os.makedirs(CACHE, exist_ok=True)
lg = sys.argv[1]
first = int(sys.argv[2]) if len(sys.argv) > 2 else 2019
t0 = time.time()
games = sd.load_games(lg)
games = games if isinstance(games, dict) else {g["id"]: g for g in games}
print(lg, len(games), "games", round(time.time() - t0), "s", flush=True)
if not sm.KEY_EDGE:
    try:
        import sports_players as sp
        sm.KEY_EDGE = sp.key_edges(games, sp.load())
    except Exception as e:  # noqa: BLE001
        print("no starters", str(e)[:80])
fin = sm.finals(games, lg)
out = open(os.path.join(CACHE, f"exam_{lg}.jsonl"), "w")
n = 0
for y in range(first, 2027):                       # the test season y = July y .. June y+1
    lo, hi = f"{y}-07-01", f"{y + 1}-07-01"
    learn = {k: g for k, g in games.items() if f"{y - se.LEARN_Y}-07-01" <= g.get("start", "") < lo}
    p = sm.tune(learn, lg)
    if not p or "w" not in p:
        print(y, "no params", flush=True)
        continue
    _, played = sm.replay(fin, p["k"], p["hfa"], lg)
    k = 0
    for g, f, *_ in played:
        if not lo <= g["start"] < hi:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        oh, oa, ch, ca = (se._int(g.get(x)) for x in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
        if hs == as_ or None in (oh, oa, ch, ca) or (oh, oa) == (ch, ca):
            continue
        own = sm.own_p(p, f)
        pa, pb = 1 / se._dec(oh), 1 / se._dec(oa)
        mk = pa / (pa + pb)
        ca_, cb_ = 1 / se._dec(ch), 1 / se._dec(ca)
        mkc = ca_ / (ca_ + cb_)
        for side, o, c, won, ow, m, mc in (("home", oh, ch, hs > as_, own, mk, mkc),
                                           ("away", oa, ca, as_ > hs, 1 - own, 1 - mk, 1 - mkc)):
            if not se.DOG_MIN <= o <= se.DOG_MAX or not se.bettable(o, c):
                continue
            out.write(json.dumps({"lg": lg, "season": y, "start": g["start"], "id": g["id"], "side": side,
                                  "neutral": str(g.get("neutral") or "0") in ("1", "True", "true"), "open": o, "close": c, "own": round(ow, 4),
                                  "mkt": round(m, 4), "mkt_close": round(mc, 4), "gap": round(ow - m, 4),
                                  "won": bool(won)}) + "\n")
            k += 1
    n += k
    out.flush()
    print(y, "dogs", k, round(time.time() - t0), "s", flush=True)
print("done", n)
