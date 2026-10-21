"""Study 4 - STAR ABSENCE / RETURN (box scores 2021-25): the top man by minutes (last 15 team games) sits / comes
back after 2+ missed. Does the close over- or under-adjust? Train 2021-22, blind 2023-25 (box data starts 2021)."""
import pandas as pd
import numpy as np
from common import load, sides, grade, fmt
from box import load_box

T4, B4 = (2021, 2022), (2023, 2024, 2025)
rows = load()
feats, _ = load_box()
df = pd.DataFrame(sides(rows))
df = df[(df.ml >= -150) & (df.ml <= 300) & (df.season >= 2021)].copy()
df["kind"] = np.where(df.ml < 100, "fav", "dog")
df["g"] = df.t_n_season + 1

def bf(r, k, who):
    me = r["home"] if r["side"] == "home" else r["away"]
    opp = r["away"] if r["side"] == "home" else r["home"]
    return feats.get((r["gid"], me if who == "t" else opp), {}).get(k)
for k in ("star_out", "star_streak", "star_back", "top2_out", "top5_out", "top8_out", "top2_back", "top5_back", "out_minutes", "has_stars", "star_mpg"):
    df["t_" + k] = df.apply(lambda r: bf(r, k, "t"), axis=1)
    df["o_" + k] = df.apply(lambda r: bf(r, k, "o"), axis=1)
df = df[(df.t_has_stars == True) & (df.o_has_stars == True)]   # noqa: E712
print("rows with stars defined both sides:", len(df), "by season", df.season.value_counts().sort_index().to_dict())
cells = 0

def rep(d, label, base, min_n=40):
    global cells
    cells += 1
    a, b = d[d.season.isin(T4)], d[d.season.isin(B4)]
    ba, bb = base[base.season.isin(T4)], base[base.season.isin(B4)]
    ga, gb = grade(a, label + " TRAIN"), grade(b, "BLIND")
    if ga.get("n", 0) < min_n:
        return
    gba, gbb = grade(ba), grade(bb)
    mark = ""
    if gb.get("n", 0) >= 50 and ga["roi"] - gba.get("roi", 0) >= 4 and gb["roi"] - gbb.get("roi", 0) >= 4:
        mark = "  <== beats the band train AND blind"
    print(f"{fmt(ga)}  (band {gba.get('roi', 0):+.1f})\n   {fmt(gb)}  (band {gbb.get('roi', 0):+.1f}){mark}")

print("=== STUDY 4: star absence / return, sides -150..+300, flat 1u at the close ===")
for kind in ("dog", "fav"):
    base = df[df.kind == kind]
    print(f"\n##### {kind.upper()}  band baseline: " + fmt(grade(base[base.season.isin(T4)], "TRAIN")) + " | " + fmt(grade(base[base.season.isin(B4)], "BLIND")))
    rep(base[base.t_star_out == 1], f"{kind} MY star out", base)
    rep(base[base.o_star_out == 1], f"{kind} OPP star out", base)
    rep(base[(base.t_star_out == 1) & (base.o_star_out == 0)], f"{kind} my star out, opp whole", base)
    rep(base[(base.o_star_out == 1) & (base.t_star_out == 0)], f"{kind} opp star out, me whole", base)
    rep(base[(base.t_star_out == 1) & (base.t_star_streak == 0)], f"{kind} my star out - FIRST game missed", base)
    rep(base[(base.t_star_out == 1) & (base.t_star_streak >= 1) & (base.t_star_streak <= 4)], f"{kind} my star out, missed 2-5 straight", base)
    rep(base[(base.t_star_out == 1) & (base.t_star_streak >= 5)], f"{kind} my star out, missed 6+ straight (long absence)", base)
    rep(base[(base.o_star_out == 1) & (base.o_star_streak == 0)], f"{kind} opp star out - first game missed", base)
    rep(base[(base.o_star_out == 1) & (base.o_star_streak >= 5)], f"{kind} opp star out 6+ straight", base)
    rep(base[base.t_top2_out >= 1], f"{kind} me: 1+ of top-2 out", base)
    rep(base[base.t_top2_out >= 2], f"{kind} me: BOTH top-2 out", base)
    rep(base[base.o_top2_out >= 2], f"{kind} opp: both top-2 out", base)
    rep(base[base.t_top5_out >= 2], f"{kind} me: 2+ of top-5 out", base)
    rep(base[base.t_top5_out >= 3], f"{kind} me: 3+ of top-5 out", base)
    rep(base[base.o_top5_out >= 2], f"{kind} opp: 2+ of top-5 out", base)
    rep(base[base.o_top5_out >= 3], f"{kind} opp: 3+ of top-5 out", base)
    rep(base[base.t_out_minutes >= 60], f"{kind} me: 60+ rotation minutes out", base)
    rep(base[base.o_out_minutes >= 60], f"{kind} opp: 60+ rotation minutes out", base)
    rep(base[(base.t_out_minutes >= 30) & (base.o_out_minutes < 10)], f"{kind} me 30+ min out vs whole opp", base)
    rep(base[(base.o_out_minutes >= 30) & (base.t_out_minutes < 10)], f"{kind} opp 30+ min out vs whole me", base)
    rep(base[(base.t_top5_out == 0) & (base.o_top5_out == 0)], f"{kind} both sides whole (top-5 all play)", base)
    rep(base[base.t_star_back == 1], f"{kind} MY star BACK (after 2+ missed)", base)
    rep(base[base.o_star_back == 1], f"{kind} OPP star back", base)
    rep(base[base.t_top2_back >= 1], f"{kind} me: a top-2 man back", base)
    rep(base[base.o_top2_back >= 1], f"{kind} opp: a top-2 man back", base)
    rep(base[base.t_top5_back >= 1], f"{kind} me: a top-5 man back", base)
    rep(base[base.o_top5_back >= 1], f"{kind} opp: a top-5 man back", base)
    # the old finding: a favorite facing a team missing its star was a trap (-7.8%); dogs missing their star ~flat
    rep(base[(base.o_star_out == 1) & (base.ml <= -120)], f"{kind} -150..-120 opp star out", base[base.ml <= -120])
    # games 1-10 cut
    e = base[base.g <= 10]
    print(f"  -- {kind} games 1-10 band: " + fmt(grade(e[e.season.isin(T4)], "TRAIN")) + " | " + fmt(grade(e[e.season.isin(B4)], "BLIND")))
    rep(e[e.t_star_out == 1], f"{kind} g1-10 my star out", e, min_n=20)
    rep(e[e.o_star_out == 1], f"{kind} g1-10 opp star out", e, min_n=20)
    rep(e[e.t_top5_out >= 2], f"{kind} g1-10 me 2+ of top-5 out", e, min_n=20)
    rep(e[e.o_top5_out >= 2], f"{kind} g1-10 opp 2+ of top-5 out", e, min_n=20)
    rep(e[e.t_top5_back >= 1], f"{kind} g1-10 me top-5 man back", e, min_n=20)
print(f"\ncells tried: {cells}; expected false positives at 5%: ~{cells*0.05:.1f}")
print("\nhow often: my star out", round(df.t_star_out.mean() * 100, 1), "% of sides; star back", round(df.t_star_back.mean() * 100, 1), "%")
