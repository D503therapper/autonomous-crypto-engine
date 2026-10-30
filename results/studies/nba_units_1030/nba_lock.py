"""STUDY 1 (10/30): the NBA LOCK. Every NBA moneyline favorite of every board day 2022-27 from the NBA-only funnel replay
(today's code, closing prices, params re-tuned each July): which favorites -101..-150 earn when the own read and the
weighed read beat the price, by season (TRAIN 2022-23 + 2023-24 + 2024-25, HOLDOUT 2025-26, NOW 2026-27), flat 1u."""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "f202*.jsonl"))):
    for l in open(f):
        r = json.loads(l)
        if r["league"] == "nba" and r["result"] in ("won", "lost"):
            rows.append(r)


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 9 else y - 1


for r in rows:
    r["season"] = season(r["date"])
    r["won"] = 1 if r["result"] == "won" else 0
    r["pnl"] = (r["dec"] - 1) if r["won"] else -1.0
    r["own_p"] = (r["edge_own"] + 1) / r["dec"] if r.get("edge_own") is not None else None
    r["own_over"] = (r["own_p"] - r["p_market"]) if r["own_p"] is not None and r.get("p_market") is not None else None
    r["w_over"] = (r["w_p"] - r["p_market"]) if r.get("w_p") is not None and r.get("p_market") is not None else None
    r["favw_sum"] = sum((r.get("nba_fav_w") or {}).values()) if r.get("nba_fav_w") else 0.0
print("rows", len(rows), "seasons", sorted({r["season"] for r in rows}), "days", len({r["date"] for r in rows}))
TRAIN = (2022, 2023, 2024)
HOLD = (2025,)
NOW = (2026,)


def rep(name, sel, band=(-150, -101), pool=rows):
    sub = [x for x in pool if band[0] <= x["odds"] <= band[1] and sel(x)]
    by = {}
    for x in sub:
        o = by.setdefault(x["season"], [0, 0, 0.0])
        o[0] += x["won"]; o[1] += 1 - x["won"]; o[2] += x["pnl"]

    def agg(seasons):
        w = sum(by[s][0] for s in seasons if s in by); l = sum(by[s][1] for s in seasons if s in by)
        u = sum(by[s][2] for s in seasons if s in by); n = w + l
        up = sum(1 for s in seasons if s in by and by[s][2] > 0); tot = sum(1 for s in seasons if s in by)
        return f"{w:.0f}-{l:.0f} {u / n * 100 if n else 0:+6.1f}% {u:+6.1f}u ({up}/{tot})"
    print(f"{name:58s} train {agg(TRAIN):34s} | hold {agg(HOLD):30s} | now {agg(NOW)}")
    return sub


print("\nNBA FAVORITES -101..-150 at the close (the board's reads), flat 1u:")
rep("the band", lambda x: True)
rep("the band -120..-150 (the Lock's price)", lambda x: True, band=(-150, -120))
rep("the band -101..-119 (S6_LOCK_SKIP)", lambda x: True, band=(-119, -101))
print("-- today's Lock test on an NBA favorite:")
rep("lock_ok (p 56%+, not week one)", lambda x: x["lock_ok"])
rep("lock_ok + good", lambda x: x["lock_ok"] and x["good"])
rep("lock_ok + own_agrees (w_p over the market)", lambda x: x["lock_ok"] and x["own_agrees"])
rep("lock_ok + own_agrees + real_value + good -120..-150", lambda x: x["lock_ok"] and x["own_agrees"] and x["real_value"] and x["good"], band=(-150, -120))
rep("...and NOT thin (would be a 1u+ Lock)", lambda x: x["lock_ok"] and x["own_agrees"] and x["real_value"] and x["good"] and not x["thin"], band=(-150, -120))
rep("...and thin (today: a ½u value play)", lambda x: x["lock_ok"] and x["own_agrees"] and x["real_value"] and x["good"] and x["thin"], band=(-150, -120))
print("-- the OWN read (the ratings + form, the roster prior) over the price:")
for lo in (0.0, 0.01, 0.02, 0.03, 0.05):
    rep(f"own read over the no-vig market by {lo * 100:.0f}+ pts", lambda x, lo=lo: x["own_over"] is not None and x["own_over"] >= lo)
rep("own read UNDER the market", lambda x: x["own_over"] is not None and x["own_over"] < 0)
for lo in (0.0, 0.03):
    rep(f"edge_own (per $) {lo * 100:.0f}+ (beats the real price)", lambda x, lo=lo: x.get("edge_own") is not None and x["edge_own"] >= lo)
print("-- the blended win % (p) over the market:")
for lo in (0.0, 0.01, 0.02, 0.03):
    rep(f"p over the market by {lo * 100:.0f}+ pts", lambda x, lo=lo: x["p"] - x["p_market"] >= lo)
rep("p 56%+", lambda x: x["p"] >= 0.56)
rep("p 58%+", lambda x: x["p"] >= 0.58)
rep("p 60%+", lambda x: x["p"] >= 0.60)
print("-- the WEIGHED read (w_p = market + the 10/22 favorite weights):")
rep("w_p over the market (net + weights)", lambda x: x["w_over"] is not None and x["w_over"] > 0)
rep("w_p under the market (net - weights)", lambda x: x["w_over"] is not None and x["w_over"] < 0)
rep("no weights", lambda x: x["w_over"] is not None and x["w_over"] == 0)
print("-- BOTH reads over the price:")
rep("own over 0+ AND w_p over", lambda x: x["own_over"] is not None and x["own_over"] >= 0 and (x["w_over"] or 0) > 0)
rep("own over 2+ AND w_p over", lambda x: x["own_over"] is not None and x["own_over"] >= 0.02 and (x["w_over"] or 0) > 0)
rep("own over 3+ AND w_p over", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and (x["w_over"] or 0) > 0)
rep("own over 0+ AND p 56%+", lambda x: x["own_over"] is not None and x["own_over"] >= 0 and x["p"] >= 0.56)
rep("own over 2+ AND p 56%+", lambda x: x["own_over"] is not None and x["own_over"] >= 0.02 and x["p"] >= 0.56)
rep("own over 3+ AND p 56%+", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56)
rep("own over 3+ AND p 56%+ AND w_p not under", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56 and (x["w_over"] or 0) >= 0)
rep("own over 3+ AND p 56%+, -120..-150", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56, band=(-150, -120))
rep("own over 3+ AND p 56%+, not week one, good", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56 and not x["nba_week_one"] and x["good"])
print("-- the raw own read (before the roster prior / trust) and the Elo:")
rep("raw_own over the market 3+", lambda x: x.get("raw_own") is not None and x["raw_own"] - x["p_market"] >= 0.03)
rep("raw_own over the market 5+", lambda x: x.get("raw_own") is not None and x["raw_own"] - x["p_market"] >= 0.05)
rep("elo_edge 50+", lambda x: (x.get("elo_edge") or 0) >= 50)
rep("elo_edge 100+", lambda x: (x.get("elo_edge") or 0) >= 100)
print("-- the no-trap / fighting / drift flags:")
rep("trap", lambda x: x["trap"])
rep("not trap, not fighting, own over 3+", lambda x: not x["trap"] and not x["fighting"] and x["own_over"] is not None and x["own_over"] >= 0.03)
rep("drift our way 2+ pts (money came to us)", lambda x: (x.get("drift") or 0) >= 0.02)
rep("drift against 2+ pts", lambda x: (x.get("drift") or 0) <= -0.02)
print("-- ONE a night (the best own_over among p 56%+ favorites) - the Lock is one pick:")
nights = {}
for x in rows:
    if -150 <= x["odds"] <= -120 and x["p"] >= 0.56 and x["own_over"] is not None and not x["nba_week_one"] and not x["trap"]:
        nights.setdefault(x["date"], []).append(x)
one = [max(v, key=lambda x: x["own_over"]) for v in nights.values()]
for lo in (0.0, 0.02, 0.03, 0.05):
    rep(f"best own_over a night, own over {lo * 100:.0f}+", lambda x, lo=lo: x["own_over"] >= lo, band=(-150, -120), pool=one)
print("-- the same at -151..-200 (out of band, a check):")
rep("own over 3+ AND p 56%+", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56, band=(-200, -151))
print("-- by stage (team games): own over 3+ AND p 56%+")
rep("  games 6-15", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56 and 5 <= (x.get("season_games") or 0) <= 14)
rep("  games 16-40", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56 and 15 <= (x.get("season_games") or 0) <= 39)
rep("  games 41+", lambda x: x["own_over"] is not None and x["own_over"] >= 0.03 and x["p"] >= 0.56 and (x.get("season_games") or 0) >= 40)
print("-- what the board posted (kind) on NBA favorites:")
for k in ("lock", "play", "nbafav", "solo"):
    rep(f"  posted as {k}", lambda x, k=k: x["kind"] == k, band=(-400, -101))
print("-- the ¹the NBA favorite play's cell (nba_fav_w net +, good, not week one):")
rep("nba_fav cell", lambda x: x["favw_sum"] > 0 and x["good"] and not x["nba_week_one"] and not x["trap"] and not x["fighting"])
rep("nba_fav cell AND own over 0+", lambda x: x["favw_sum"] > 0 and x["good"] and not x["nba_week_one"] and not x["trap"] and not x["fighting"] and (x["own_over"] or -1) >= 0)
rep("nba_fav cell AND own UNDER", lambda x: x["favw_sum"] > 0 and x["good"] and not x["nba_week_one"] and not x["trap"] and not x["fighting"] and (x["own_over"] or 1) < 0)
