"""STUDY 1 (11/2): RE-VALIDATE THE 🏀 OPENING-LINE PLAY on 2020-23 (seasons 2020 / 2021 / 2022 - never in any test of it).
The same module (sports_nba_open: the 37 inputs, ridge lam 300, the 4-point bar, -150..+300, the #1 side a night, model
score only - as the 10/30 sizing study), each season FIT ON THE SEASONS BEFORE IT ONLY (the module's own walk-forward:
2020 on 2018-19, 2021 on 2018-20, 2022 on 2018-21) - no new inputs, no re-tuning. Scored at:
  OPEN*  the fair next-day look (20h+, both teams' last games over) - exists for only ~4% of regular-season games here
  MORN   the game-day 15:00Z median-book price (the earliest number this data holds for ~96% of games)
  CLOSE  ESPN's close
graded at the price it was picked at and at the close. 2023-25 (+2026) with ESPN's open re-run beside it for reference.
Also: the LIVE 2026 model's coefficients (fit 2018-25 - it SAW 2020-22, look-ahead) on 2020-22 at the morning, as a check."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib                       # noqa: E402
import sports_nba_open as no     # noqa: E402

games = lib.load_games()
lk = lib.looks(games)
prev = lib.prev_tips(games)
tab = no.table(games)
models = {s: no.fit(games, s, path=False, tab=tab) for s in (2020, 2021, 2022, 2023, 2024, 2025, 2026)}
for s, m in models.items():
    print(f"model {s}: trained on {m['train_seasons'] if m else None}, rows {m['rows'] if m else 0}")
live = no.load()
print("live model season", live and live["season"], "trained", live and live["train_seasons"])

prices = {"open": {}, "morn": {}, "close": {}, "espn_open": {}}
for gid, r in tab.items():
    if not r["reg"] or r["home_win"] is None:
        continue
    if r["ml_home"] and r["ml_away"]:
        prices["close"][gid] = (r["ml_home"], r["ml_away"])
    if r["ml_home_open"] and r["ml_away_open"]:
        prices["espn_open"][gid] = (r["ml_home_open"], r["ml_away_open"])
    if gid in lk:
        op, mo = lib.pick_looks(lk, prev, gid)
        if op:
            prices["open"][gid] = (op["mh"], op["ma"])
        if mo:
            prices["morn"][gid] = (mo["mh"], mo["ma"])


def picks(src, model_of, band=(-150, 300), bar=0.04, top=1):
    by = {}
    for gid in prices[src]:
        r = tab[gid]
        if model_of(r["season"]):
            by.setdefault((r["season"], r["date"]), []).append(gid)
    out = []
    for (s, d), gids in sorted(by.items()):
        m = model_of(s)
        cands = []
        for gid in gids:
            r = tab[gid]
            mh, ma = prices[src][gid]
            mp_h = no._mp(mh, ma)
            if mp_h is None or r["h"]["n_season"] < 1 or r["a"]["n_season"] < 1:
                continue
            for side, ml, mp in (("home", mh, mp_h), ("away", ma, 1 - mp_h)):
                if not band[0] <= ml <= band[1]:
                    continue
                sc = no.score(m, r, side, mp)
                if sc >= bar:
                    cands.append((sc, gid, side, ml))
        cands.sort(reverse=True)
        for rank, (sc, gid, side, ml) in enumerate(cands[:top]):
            r = tab[gid]
            won = r["home_win"] if side == "home" else 1 - r["home_win"]
            cl = prices["close"].get(gid)
            mc = (cl[0] if side == "home" else cl[1]) if cl else None
            out.append(dict(season=s, date=d, gid=gid, side=side, odds=ml, close=mc, score=sc, won=won, rank=rank,
                            pnl=lib.profit(won, lib.dec(ml)), pnl_close=lib.profit(won, lib.dec(mc)) if mc else None,
                            dog=ml > 0))
    return out


def rep(name, ps, key="pnl"):
    c = lib.Cells("", [("all", set(range(2018, 2030)))])
    for p in ps:
        if p.get(key) is not None:
            c.add(name, p["season"], p[key])
    print(c.line(name))


res = {}
morn_ps = []
wf = models.get
print("\n=== THE OPENING-LINE PLAY, walk-forward fit, #1 side a night, 4+ points, -150..+300, flat 1u ===")
for src, seasons, label in (("espn_open", (2023, 2024, 2025, 2026), "2023-26 at ESPN's OPEN (the 10/30 reference)"),
                            ("open", (2020, 2021, 2022), "2020-22 at the FAIR NEXT-DAY look (rare)"),
                            ("morn", (2020, 2021, 2022), "2020-22 at the GAME-DAY MORNING look"),
                            ("close", (2020, 2021, 2022), "2020-22 picked at ESPN's CLOSE"),
                            ("close", (2023, 2024, 2025), "2023-25 picked at ESPN's CLOSE (reference)")):
    ps = [p for p in picks(src, wf) if p["season"] in seasons]
    print(f"\n{label}: {len(ps)} plays, avg read {sum(p['score'] for p in ps) / max(1, len(ps)) * 100:.1f} pts")
    rep("graded at the price picked", ps)
    rep("same sides graded at the close", ps, "pnl_close")
    rep("  dogs (graded at pick price)", [p for p in ps if p["dog"]])
    rep("  favorites", [p for p in ps if not p["dog"]])
    for lo, hi in ((0.04, 0.05), (0.05, 0.07), (0.07, 1)):
        rep(f"  read {lo * 100:.0f}-{hi * 100:.0f} pts", [p for p in ps if lo <= p["score"] < hi])
    res[f"{src}_{min(seasons)}"] = {"n": len(ps), "units": round(sum(p["pnl"] for p in ps), 2),
                                    "roi": round(sum(p["pnl"] for p in ps) / max(1, len(ps)), 4)}
    if src == "morn":
        morn_ps = ps

print("\n2020-22 at the morning - every side 4+ (not just #1):")
allp = [p for p in picks("morn", wf, top=99) if p["season"] in (2020, 2021, 2022)]
rep("every side 4+", allp)
rep("#2 side a night", [p for p in allp if p["rank"] == 1])

print("\n2020-22 at the morning - the LIVE 2026 model's weights (fit 2018-25: it SAW these seasons - look-ahead, a check):")
lp = [p for p in picks("morn", lambda s: live) if p["season"] in (2020, 2021, 2022)]
rep("live weights, #1 a night", lp)

mv = [1 / lib.dec(p["close"]) - 1 / lib.dec(p["odds"]) for p in morn_ps if p["close"]]
print(f"\nCLV of the 2020-22 morning picks: n {len(mv)}, avg {sum(mv) / max(1, len(mv)) * 100:+.2f} pts toward us, "
      f"our way {sum(1 for x in mv if x > 0)} / against {sum(1 for x in mv if x < 0)}")
print("\nSPLITS of the 2020-22 morning picks (is it the no-fans 2020-21 season?):")
rep("home side", [p for p in morn_ps if p["side"] == "home"])
rep("away side", [p for p in morn_ps if p["side"] == "away"])
for lo, hi, nm in ((1, 10, "games 1-10"), (11, 30, "games 11-30"), (31, 60, "games 31-60"), (61, 99, "games 61+")):
    rep(nm, [p for p in morn_ps if lo <= tab[p["gid"]]["h"]["n_season"] + 1 <= hi])
json.dump(res, open(os.path.join(lib.OUT, "s1_out.json"), "w"), indent=1)
