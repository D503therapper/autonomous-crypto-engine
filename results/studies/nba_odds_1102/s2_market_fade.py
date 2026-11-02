"""STUDY 2 (11/2): RE-VALIDATE THE MARKET-FADE WEIGHT (sports.market_trend / MKT_FADE_SUM 0.08 / MKT_FADE_W 2 - an NBA dog
+100..+350 whose last 3 priced regular-season games this season moved 8+ no-vig points AGAINST it, open -> close, summed)
on 2020-22. The 10/30 study had ESPN's open (2023-26 only). Here each past game's move is the GAME-DAY MORNING median-book
look -> ESPN's close (the earliest number this data holds for ~96% of games - and step 0 says the morning already holds
~85% of the open->close move, so these moves are SMALLER: the 8-point sum flags fewer teams). Three versions:
  RAW     the live rule as written (8+ points against) on morning->close moves
  MATCHED the cut that flags the same SHARE of dogs in 2020-22 as 8+ flags on ESPN open->close in 2023-25
  DOSE    the sum in bands
Graded flat 1u at tonight's CLOSE and at tonight's MORNING price; 2023-25 re-run on ESPN's open with this same code."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib                       # noqa: E402

games = lib.load_games()
lk = lib.looks(games)
prev = lib.prev_tips(games)

rows = sorted((g for g in games.values() if g.get("stype") == "2" and g.get("status") == "final"
               and lib.num(g.get("home_score")) is not None and lib.num(g.get("ml_home")) is not None),
              key=lambda g: g["start"])


def move(g, src):
    """This game's no-vig move toward the HOME side, from `src` (espn open / morning look) to the close."""
    ch, ca = lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
    if src == "espn":
        oh, oa = lib.num(g.get("ml_home_open")), lib.num(g.get("ml_away_open"))
    else:
        mo = lib.pick_looks(lk, prev, g["id"])[1] if g["id"] in lk else None
        oh, oa = (mo["mh"], mo["ma"]) if mo else (None, None)
    if None in (oh, oa, ch, ca) or min(abs(oh), abs(oa), abs(ch), abs(ca)) < 100:
        return None
    return lib.nv(ch, ca) - lib.nv(oh, oa)


def trend_rows(src, seasons):
    hist = {}                    # team -> [(season, move from its side)]
    out = []
    for g in rows:
        s = lib.season(g["start"])
        if s not in seasons:
            continue
        mv = move(g, src)
        mo = lib.pick_looks(lk, prev, g["id"])[1] if g["id"] in lk else None
        for side, other in (("home", "away"), ("away", "home")):
            tm = g[side]
            last = [m for ss, m in hist.get(tm, []) if ss == s][-3:]
            trend = sum(last) if len(last) == 3 else None
            ml = int(float(g[f"ml_{side}"]))
            won = 1 if (float(g[f"{side}_score"]) > float(g[f"{other}_score"])) else 0
            mml = (mo["mh"] if side == "home" else mo["ma"]) if mo else None
            out.append(dict(season=s, trend=trend, ml=ml, won=won, mml=mml))
        if mv is not None:
            hist.setdefault(g["home"], []).append((s, mv))
            hist.setdefault(g["away"], []).append((s, -mv))
    return out


new = trend_rows("morn", (2020, 2021, 2022))
ref = trend_rows("espn", (2023, 2024, 2025, 2026))
dog = lambda r, k="ml": r.get(k) is not None and 100 <= r[k] <= 350   # noqa: E731
ref_d = [r for r in ref if dog(r) and r["trend"] is not None and r["season"] <= 2025]
share = sum(1 for r in ref_d if r["trend"] <= -0.08) / len(ref_d)
new_d = sorted(r["trend"] for r in new if dog(r) and r["trend"] is not None)
cut = new_d[int(share * len(new_d))]
print(f"2023-25 ESPN open->close: {share:.1%} of dogs flagged at 8+ points against; 2020-22 morning->close: "
      f"{sum(1 for x in new_d if x <= -0.08) / len(new_d):.1%} at 8+, the matched cut = {-cut * 100:.1f} points")

C = lib.Cells("NBA DOGS +100..+350, flat 1u (graded at tonight's close unless 'morn')",
              [("2020-22", {2020, 2021, 2022}), ("2023-25 ref", {2023, 2024, 2025})])
for r in new + ref:
    if r["trend"] is None:
        continue
    s = r["season"]
    if s == 2026:
        continue
    src = "espn" if s >= 2023 else "morn"
    if dog(r):
        p = lib.profit(r["won"], lib.dec(r["ml"]))
        C.add("all dogs with 3 priced games (base)", s, p)
        if r["trend"] <= -0.08:
            C.add("RAW: faded 8+ pts (the live rule)", s, p)
        if r["trend"] >= 0.08:
            C.add("RAW mirror: backed 8+ pts", s, p)
        if s <= 2022:
            if r["trend"] <= cut:
                C.add("MATCHED: faded past the matched cut", s, p)
            if r["trend"] >= -cut:
                C.add("MATCHED mirror: backed past the matched cut", s, p)
        for lo, hi in ((-1, -0.08), (-0.08, -0.05), (-0.05, -0.02), (-0.02, 0.02), (0.02, 0.05), (0.05, 1)):
            if lo <= r["trend"] < hi:
                C.add(f"DOSE {lo * 100:+.0f}..{hi * 100:+.0f}", s, p)
    if s <= 2022 and dog(r, "mml"):
        p = lib.profit(r["won"], lib.dec(r["mml"]))
        C.add("morn: all dogs (base, at the morning price)", s, p)
        if r["trend"] <= -0.08:
            C.add("morn: RAW faded 8+", s, p)
        if r["trend"] <= cut:
            C.add("morn: MATCHED faded", s, p)
C.dump()
json.dump(C.as_dict(), open(os.path.join(lib.OUT, "s2_out.json"), "w"), indent=1)
