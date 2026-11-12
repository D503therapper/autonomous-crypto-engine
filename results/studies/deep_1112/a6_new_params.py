"""11/12 DEEP PROGRAM - A6: TODAY'S DIALS, OLD FIT vs NEW FIT (sports_model.tune with day = 11/12 vs 11/14: the blend on
every game with odds pulled to zero; the college football read fit on FBS-vs-FBS games). Prints both sets and saves
them (OUT=<folder>, default ~/.cache/d503_deep1112) for the board diff (a7).
Usage: python results/studies/deep_1112/a6_new_params.py [league ...] > results/studies/deep_1112/a6_new_params.out"""
import json, os, sys, time
import dlib as D

sys.path.insert(0, D.ROOT)
os.chdir(D.ROOT)
import sports_data as sd         # noqa: E402
import sports_model as sm        # noqa: E402

OUT = os.environ.get("OUT") or os.path.join(os.path.expanduser("~"), ".cache", "d503_deep1112")
os.makedirs(OUT, exist_ok=True)
MODEL = json.load(open("data/sports/model.json"))
res = {"old": {}, "new": {}}
for lg in (sys.argv[1:] or list(sd.LEAGUES)):
    games = sd.load_games(lg)
    prev = MODEL["params"].get(lg)
    t = time.time()
    old = sm.tune(games, lg, prev, day="2026-11-12")
    new = sm.tune(games, lg, prev, day="2026-11-14")
    for p in (old, new):
        if prev and prev.get("hockey") is not None:
            p["hockey"] = prev["hockey"]
    res["old"][lg], res["new"][lg] = old, new
    print(f"== {lg} ({time.time() - t:.0f}s)  reaction speed {old['k']} / {new['k']}, home edge {old['hfa']} / {new['hfa']}")
    for k in ("trust", "move_w", "cal", "hdog"):
        print(f"   {k:7s} live file {prev.get(k, 0):+.4f} | old fit {old.get(k, 0):+.4f} -> new fit {new.get(k, 0):+.4f}")
    print(f"   games in the blend fit: {old['odds_games']} -> {new['odds_games']}; log loss blend / close: {old['logloss_final']} / {old['logloss_market']} -> {new['logloss_final']} / {new['logloss_market']}")
    print(f"   blind third: old {old.get('oos')}")
    print(f"                new {new.get('oos')}")
    if lg == "ncaaf":
        print("   the ratings read's weights, old -> new:")
        for n, a, b in zip(["intercept"] + sm.FEATURES, old["w"], new["w"]):
            print(f"      {n:10s} {a:+.3f} -> {b:+.3f}")
        print(f"   sigma {old['sigma']:.2f} -> {new['sigma']:.2f}; strust {old['strust']} -> {new['strust']}; bfav {old.get('bfav'):+.4f} -> {new.get('bfav'):+.4f}")
    json.dump(res, open(os.path.join(OUT, "params_old_new.json"), "w"))
