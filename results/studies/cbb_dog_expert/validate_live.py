"""Replay the LIVE college hoops dog read and the 🔍 college hoops gap play on one past slate (read-only):
python validate_live.py 2026-02-21 - the marks the live engine runs, the efficiency read, then sports.mark_ncaab_dog_read
and sports.gap_plays; prints how many dogs clear the read's gate / the gap play, with examples and the parts."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
import sports  # noqa: E402
import sports_data as sd  # noqa: E402

day = sys.argv[1] if len(sys.argv) > 1 else "2026-02-21"
games = sd.load_games()
d = sd.decimal
cands = []
for gid, g in games.items():
    if g.get("league") != "ncaab" or not str(g.get("start", "")).startswith(day) or g.get("status") != "final":
        continue
    try:
        mh, ma = int(float(g["ml_home"])), int(float(g["ml_away"]))
    except (KeyError, TypeError, ValueError):
        continue
    pm = 1 / d(mh), 1 / d(ma)
    nv = pm[0] / (pm[0] + pm[1]), pm[1] / (pm[0] + pm[1])
    for i, (side, odds) in enumerate((("home", mh), ("away", ma))):
        p = nv[i]
        cands.append({"league": "ncaab", "market": "ml", "odds": odds, "dec": d(odds), "p": p, "p_market": p, "side": side,
                      "game_id": gid, "start": g["start"], "reasons": [], "dog_ctx": {}, "edge_own": p * d(odds) - 1,
                      "edge": p * d(odds) - 1, "team": g[side + "_name"], "opp": g[("away" if side == "home" else "home") + "_name"],
                      "team_id": g[side], "home": side == "home", "neutral": str(g.get("neutral")) == "1", "waiting": [],
                      "games_in": sports.season_games(games, g, side),
                      "opp_games_in": sports.season_games(games, g, "away" if side == "home" else "home")})
t = time.time()
sports._SCHED.clear()
sports.mark_ncaab_rubber(games, cands)
sports.mark_ncaab_top_out(games, cands)
sports.mark_ncaab_ats_gap(games, cands)
sports.mark_ncaab_reb(games, cands)
sports.mark_ncaab_coach(games, cands)
sports.mark_ncaab_long_out(games, cands)
sports.mark_ncaab_race(games, cands)
sports.mark_ncaab_identity(games, cands)
sports.mark_ncaab_roster_mix(games, cands)
sports.weigh_favorites(cands)
sports.weigh_ncaab_eff_fav(games, cands)
sports.mark_ncaab_dog_read(cands)
gap = sports.gap_plays(cands, avoid=())
print(f"{day}: {len(cands)} sides ({len(cands) // 2} priced games), marks + the read in {time.time() - t:.1f}s")
dogs = [c for c in cands if 100 <= c["odds"] <= 350]
with_read = [c for c in dogs if c.get("eff_p") is not None]
ok = [c for c in dogs if sports.ncaab_dog_read_ok(c)]
print(f"dogs +100..+350: {len(dogs)}, with an efficiency read {len(with_read)}, dog read 4+ (both 4+ games): {len(ok)}, 🔍 gap plays: {len(gap)}")


def won(c):
    g = games[c["game_id"]]
    hs, as_ = float(g["home_score"]), float(g["away_score"])
    return (hs > as_) if c["side"] == "home" else (as_ > hs)


for c in sorted(ok, key=lambda c: -c["dog_read"]):
    print(f"  read {c['dog_read']:g} {c['team']} {c['odds']:+d} vs {c['opp']} | parts {c['dog_read_parts']} | eff {c.get('eff_p')} vs {c['p_market']:.3f} | {'WON' if won(c) else 'lost'}")
for c in gap:
    print(f"  🔍 {c['team']} {c['odds']:+d} vs {c['opp']} gap {c['gap']:.3f} read {c.get('dog_read')} units {sports.gap_units({'legs': [c], 'gap': c['gap']})} | {'WON' if won(c) else 'lost'}")
if ok:
    w = sum(won(c) for c in ok)
    print(f"the read's dogs on this slate: {w}-{len(ok) - w}")
print("-- the top reads on the slate (the validator has no dog_ctx - the live engine's form flags add to these) --")
for c in sorted(with_read, key=lambda c: -(c.get("dog_read") or -99))[:8]:
    print(f"  read {c.get('dog_read')} {c['team']} {c['odds']:+d} | parts {c.get('dog_read_parts')} | eff {c.get('eff_p')} vs {c['p_market']:.3f} games {c['games_in']}/{c['opp_games_in']} | {'WON' if won(c) else 'lost'}")
backed = [c for c in with_read if c["eff_p"] > 0.5]
print(f"backed dogs {len(backed)}; gaps 15+ {sum(1 for c in with_read if c['eff_p'] - c['p_market'] >= 0.15)}; "
      f"eff gap spread: min {min(c['eff_p'] - c['p_market'] for c in with_read):+.2f} max {max(c['eff_p'] - c['p_market'] for c in with_read):+.2f}")
