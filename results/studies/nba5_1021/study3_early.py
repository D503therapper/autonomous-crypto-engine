"""Study 3 - EARLY-SEASON MISPRICING (the deepest): games 1-20, with the games 1-10 cut everywhere. Roster turnover
(minutes returning, from box scores 2022-25), the market's summer re-rating vs last season's results (market p minus
carried Elo p), hot / cold starts vs last season, big year-to-year win changes, and the engine's own read early."""
import pandas as pd
import numpy as np
from common import load, sides, grade, fmt, split, report, TRAIN, BLIND
from box import load_box
from nba_engine import load_engine

rows = load()
eng = load_engine()
feats, turnover = load_box()
df = pd.DataFrame(sides(rows))
df = df[(df.ml >= -150) & (df.ml <= 300)].copy()
df["kind"] = np.where(df.ml < 100, "fav", "dog")
df["g"] = df.t_n_season + 1                       # this team's game number this season
df["og"] = df.o_n_season + 1
df["gmin"] = df[["g", "og"]].min(axis=1)
df["own_h"] = df.gid.map(lambda g: eng.get(g, {}).get("own"))
df["own"] = np.where(df.is_home == 1, df.own_h, 1 - df.own_h)
df["dis"] = (df.own - df.mp) * 100
df["mkt_vs_elo"] = (df.mp - df.p_elo) * 100       # + = the market rates me above last season's results (carried Elo)
df["wp_jump"] = df.t_wp_season - df.t_wp_last     # this season so far vs last season
df["o_wp_jump"] = df.o_wp_season - df.o_wp_last
# box turnover (season-level), 2022-25
def tv(r, k, side):
    me = r["home"] if r["side"] == "home" else r["away"]
    opp = r["away"] if r["side"] == "home" else r["home"]
    tm = me if side == "t" else opp
    return turnover.get((tm, r["season"]), {}).get(k)
df["ret"] = df.apply(lambda r: tv(r, "ret_share", "t"), axis=1)
df["o_ret"] = df.apply(lambda r: tv(r, "ret_share", "o"), axis=1)
df["top3b"] = df.apply(lambda r: tv(r, "top3_back", "t"), axis=1)
df["o_top3b"] = df.apply(lambda r: tv(r, "top3_back", "o"), axis=1)

early = df[df.g <= 20]
print("=== STUDY 3: early season (team's games 1-20), sides -150..+300, flat 1u at the close ===")
cells = 0

def rep(d, label, base, tr=TRAIN, bl=BLIND, min_n=50):
    global cells
    cells += 1
    a, b = d[d.season.isin(tr)], d[d.season.isin(bl)]
    ba, bb = base[base.season.isin(tr)], base[base.season.isin(bl)]
    ga, gb = grade(a, label + " TRAIN"), grade(b, "BLIND")
    if ga.get("n", 0) < min_n:
        return
    gba, gbb = grade(ba), grade(bb)
    mark = ""
    if gb.get("n", 0) >= 40 and ga["roi"] - gba.get("roi", 0) >= 4 and gb["roi"] - gbb.get("roi", 0) >= 4:
        mark = "  <== beats the band train AND blind"
    print(f"{fmt(ga)}  (band {gba.get('roi', 0):+.1f})\n   {fmt(gb)}  (band {gbb.get('roi', 0):+.1f}){mark}")

print("\n--- A. baseline by game number, side and home/away (the market's early calibration)")
for kind in ("dog", "fav"):
    for lo, hi in [(1, 5), (6, 10), (11, 20), (21, 82)]:
        d = df[(df.kind == kind) & (df.g >= lo) & (df.g <= hi)]
        print(report(d, f"{kind} games {lo}-{hi}"))
        for hm in (1, 0):
            print("   " + report(d[d.is_home == hm], f"  {'home' if hm else 'away'}").replace("\n", "\n   "))
print(report(df[(df.kind == "dog") & (df.ml <= 200) & (df.is_home == 1) & (df.g >= 6) & (df.g <= 20)], "BUILT check: home dog +100..+200 games 6-20"))
print(report(df[(df.kind == "dog") & (df.ml <= 200) & (df.is_home == 1) & (df.g <= 10)], "  home dog +100..+200 games 1-10"))
print(report(df[(df.kind == "dog") & (df.ml <= 200) & (df.is_home == 1) & (df.g >= 6) & (df.g <= 10)], "  home dog +100..+200 games 6-10"))

print("\n--- B. the market's summer re-rating: market p minus carried-Elo p (last season's results, regressed 1/3)")
for kind in ("dog", "fav"):
    for gl, gh, nm in [(1, 10, "g1-10"), (11, 20, "g11-20"), (1, 20, "g1-20")]:
        base = df[(df.kind == kind) & (df.g >= gl) & (df.g <= gh)]
        for lo, hi, lab in [(-100, -12, "mkt 12+ UNDER elo (market says I got worse)"), (-12, -6, "mkt 6-12 under"), (-6, 6, "within 6"),
                            (6, 12, "mkt 6-12 over"), (12, 100, "mkt 12+ OVER elo (market says I got better)")]:
            rep(base[(base.mkt_vs_elo >= lo) & (base.mkt_vs_elo < hi)], f"{kind} {nm} {lab}", base)

print("\n--- C. hot / cold starts vs last season (after 5+ games): win% this season minus last season's")
for kind in ("dog", "fav"):
    for gl, gh, nm in [(6, 10, "g6-10"), (11, 20, "g11-20"), (6, 20, "g6-20")]:
        base = df[(df.kind == kind) & (df.g >= gl) & (df.g <= gh)]
        for lo, hi, lab in [(-2, -0.3, "COLD start (-.30+)"), (-0.3, -0.15, "cool (-.15..-.30)"), (-0.15, 0.15, "as expected"),
                            (0.15, 0.3, "warm (+.15..+.30)"), (0.3, 2, "HOT start (+.30+)")]:
            rep(base[(base.wp_jump >= lo) & (base.wp_jump < hi)], f"{kind} {nm} me {lab}", base)
        for lo, hi, lab in [(-2, -0.3, "opp COLD start"), (0.3, 2, "opp HOT start")]:
            rep(base[(base.o_wp_jump >= lo) & (base.o_wp_jump < hi)], f"{kind} {nm} {lab}", base)
    # hot start AND the market still prices me under last season's Elo (slow to believe) / over (already believes)
    base = df[(df.kind == kind) & (df.g >= 6) & (df.g <= 20)]
    rep(base[(base.wp_jump >= 0.3) & (base.mkt_vs_elo < 0)], f"{kind} g6-20 HOT start, market still under my carried Elo", base)
    rep(base[(base.wp_jump >= 0.3) & (base.mkt_vs_elo >= 6)], f"{kind} g6-20 HOT start, market already 6+ over my carried Elo", base)
    rep(base[(base.wp_jump <= -0.3) & (base.mkt_vs_elo > 0)], f"{kind} g6-20 COLD start, market still over my carried Elo", base)

print("\n--- D. last season's record (the public's memory): dogs / favs by last season's win%")
for kind in ("dog", "fav"):
    for gl, gh, nm in [(1, 10, "g1-10"), (11, 20, "g11-20")]:
        base = df[(df.kind == kind) & (df.g >= gl) & (df.g <= gh)]
        for lo, hi, lab in [(0, 0.35, "bad last yr (<35%)"), (0.35, 0.5, "35-50%"), (0.5, 0.65, "50-65%"), (0.65, 1.01, "good last yr (65%+)")]:
            rep(base[(base.t_wp_last >= lo) & (base.t_wp_last < hi)], f"{kind} {nm} {lab}", base)
        rep(base[(base.t_wp_last < 0.4) & (base.o_wp_last > 0.6)], f"{kind} {nm} bad-last-yr me vs good-last-yr opp", base)
        rep(base[(base.t_wp_last > 0.6) & (base.o_wp_last < 0.4)], f"{kind} {nm} good-last-yr me vs bad-last-yr opp", base)

print("\n--- E. ROSTER TURNOVER (box scores; 2022-23 train, 2024-25 blind - only 4 seasons, read as a lead at best)")
T2, B2 = (2022, 2023), (2024, 2025)
tv_df = df.dropna(subset=["ret", "o_ret"])
print("teams/season with turnover:", {s: int(tv_df[tv_df.season == s].drop_duplicates(["home", "season"]).shape[0]) for s in sorted(tv_df.season.unique())})
for kind in ("dog", "fav"):
    for gl, gh, nm in [(1, 10, "g1-10"), (11, 20, "g11-20"), (1, 20, "g1-20")]:
        base = tv_df[(tv_df.kind == kind) & (tv_df.g >= gl) & (tv_df.g <= gh)]
        for lo, hi, lab in [(0, 0.5, "BIG turnover (<50% minutes back)"), (0.5, 0.65, "50-65% back"), (0.65, 1.01, "steady (65%+ back)")]:
            rep(base[(base.ret >= lo) & (base.ret < hi)], f"{kind} {nm} me {lab}", base, T2, B2, min_n=40)
        for lo, hi, lab in [(0, 0.5, "opp BIG turnover"), (0.65, 1.01, "opp steady")]:
            rep(base[(base.o_ret >= lo) & (base.o_ret < hi)], f"{kind} {nm} {lab}", base, T2, B2, min_n=40)
        rep(base[(base.top3b <= 1)], f"{kind} {nm} me: 2+ of last yr's top-3 minutes men GONE", base, T2, B2, min_n=40)
        rep(base[(base.o_top3b <= 1)], f"{kind} {nm} opp: 2+ of last yr's top-3 gone", base, T2, B2, min_n=40)
        rep(base[(base.ret < 0.5) & (base.o_ret >= 0.65)], f"{kind} {nm} me big turnover vs steady opp", base, T2, B2, min_n=30)
        rep(base[(base.ret >= 0.65) & (base.o_ret < 0.5)], f"{kind} {nm} me steady vs big-turnover opp", base, T2, B2, min_n=30)
    # turnover crossed with the market's re-rating: big turnover AND the market moved me up a lot = the hype side?
    base = tv_df[(tv_df.kind == kind) & (tv_df.g <= 10)]
    rep(base[(base.ret < 0.55) & (base.mkt_vs_elo >= 8)], f"{kind} g1-10 big turnover + market 8+ over carried Elo (hyped rebuild)", base, T2, B2, min_n=30)
    rep(base[(base.ret < 0.55) & (base.mkt_vs_elo <= -8)], f"{kind} g1-10 big turnover + market 8+ under carried Elo (torn down)", base, T2, B2, min_n=30)
    rep(base[(base.o_ret < 0.55) & (base.mkt_vs_elo >= 8)], f"{kind} g1-10 opp big turnover + market 8+ over my elo", base, T2, B2, min_n=30)

print("\n--- F. year-to-year win change (last season vs the season before): did a jumper hold / a faller bounce?")
# wp two seasons back: from the games rows we only carry last season; rebuild via a per-team-season table
import collections
wps = {}
for r in rows:
    for side in ("home", "away"):
        tm = r[side]
        wps.setdefault((tm, r["season"]), r["h_wp_last" if side == "home" else "a_wp_last"])
def wp_before(r):
    return wps.get((r["home"] if r["side"] == "home" else r["away"], r["season"] - 1))
df["wp_before"] = df.apply(wp_before, axis=1)
df["jump_last"] = df.t_wp_last - df.wp_before
for kind in ("dog", "fav"):
    for gl, gh, nm in [(1, 10, "g1-10"), (1, 20, "g1-20")]:
        base = df[(df.kind == kind) & (df.g >= gl) & (df.g <= gh)].dropna(subset=["jump_last"])
        rep(base[base.jump_last >= 0.2], f"{kind} {nm} me: jumped +.20 last season", base)
        rep(base[base.jump_last <= -0.2], f"{kind} {nm} me: fell -.20 last season", base)

print("\n--- G. the engine's own read early (no rosters) by disagreement, games 1-10 and 11-20")
for kind in ("dog", "fav"):
    for gl, gh, nm in [(1, 10, "g1-10"), (11, 20, "g11-20")]:
        base = df[(df.kind == kind) & (df.g >= gl) & (df.g <= gh)].dropna(subset=["dis"])
        rep(base[base.dis >= 5], f"{kind} {nm} own 5+ over price", base)
        rep(base[base.dis <= -5], f"{kind} {nm} own 5+ under price (fighting)", base)
        rep(base[(base.dis > -5) & (base.dis < 5)], f"{kind} {nm} own within 5", base)

print("\n--- H. opening-week specifics: game 1, games 1-3, the home opener, first road game")
for kind in ("dog", "fav"):
    base = df[df.kind == kind]
    rep(base[base.g == 1], f"{kind} GAME 1", base[base.g <= 20])
    rep(base[base.g <= 3], f"{kind} games 1-3", base[base.g <= 20])
    rep(base[(base.g <= 3) & (base.is_home == 1)], f"{kind} games 1-3 at home", base[base.g <= 20])
    rep(base[(base.g <= 3) & (base.is_home == 0)], f"{kind} games 1-3 away", base[base.g <= 20])
    rep(base[(base.g <= 10) & (base.og >= base.g + 3)], f"{kind} g1-10 opp has played 3+ more games than me", base[base.g <= 10])
    rep(base[(base.g <= 10) & (base.g >= base.og + 3)], f"{kind} g1-10 I have played 3+ more games than opp", base[base.g <= 10])
print(f"\ncells tried: {cells}; expected false positives at 5%: ~{cells*0.05:.1f}")
