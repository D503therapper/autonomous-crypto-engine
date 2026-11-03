"""The engine's CURRENT college hoops read, replayed on every game: the margin Elo + features (sports_model), blended
with the market by the learned trust (final_p, move_w 0 = the own read) and pulled to the market by early_trust
(0 at game 0 -> 1 at 10 games). Params = today's model.json ncaab params (a slight look-ahead in the OLD read's favour).
Also the raw Elo read (own_p) and the Elo margin (the spread model's own margin before strust).
Writes ~/.cache/d503_studies/deep_old_read.pkl {game id: (old_final_home_p, old_raw_home_p, elo_margin)}."""
import csv
import glob
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))
import sports_model as sm  # noqa: E402

import lib  # noqa: E402


def main():
    games = {}
    for fn in sorted(glob.glob(os.path.join(lib.ROOT, "data/sports/games/ncaab/*.csv"))):
        for r in csv.DictReader(open(fn)):
            games[r["id"]] = r
    fin = sm.finals(games, "ncaab")
    prm = json.load(open(os.path.join(lib.ROOT, "data/sports/model.json")))["params"]["ncaab"]
    e = sm.Elo(prm["k"], prm["hfa"], "ncaab")
    cnt = {}
    out = {}
    for g in fin:
        f = e.features(g)
        s = lib.season_of(g["start"])
        nh, na = cnt.get((s, g["home"]), 0), cnt.get((s, g["away"]), 0)
        raw = sm.own_p(prm, f)
        m = sm.market_p(g)
        if m is not None:
            fp = sm.final_p({**prm, "move_w": 0.0}, f, g)
            w = min(1.0, min(nh, na) / 10)
            fp = sm.sigmoid(sm.logit(m) + w * (sm.logit(fp) - sm.logit(m)))
        else:
            fp = None
        try:
            em = sum(a * b for a, b in zip(prm["sw"], sm._spread_x(f)))
        except Exception:  # noqa: BLE001
            em = None
        out[g["id"]] = (fp, raw, em)
        e.update(g)
        if g.get("stype") == "2":
            cnt[(s, g["home"])] = nh + 1
            cnt[(s, g["away"])] = na + 1
    pickle.dump(out, open(os.path.join(lib.CACHE, "deep_old_read.pkl"), "wb"))
    print(len(out))


if __name__ == "__main__":
    main()
