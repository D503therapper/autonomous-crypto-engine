"""11/16 MAX PLAY HUNT - S1: CONFLUENCE ON THE RAW SCHEDULE RIGS (NHL / NBA, every side at the close 2018-26).
The signals are the ones the engine already carries as weights (named before looking, the direction the studies gave):
the rested side against a back-to-back, 3 in 4, the hot dog fade, goal luck, the cold dog, home, the short price, the blowout
bounce. The question: do 3+ of them AGREEING win far more than one - a dose in the count?
Usage: python results/studies/max_pro_1116/s1_raw_nhl_nba.py > results/studies/max_pro_1116/s1_raw_nhl_nba.out"""
import mp

for lg in ("nhl", "nba"):
    R = mp.build(lg)
    (t0, t1), (h0, h1) = mp.split(lg)
    C = lambda name, rs: mp.cell(name, rs, lg)   # noqa: E731
    dogs = [r for r in R if 100 <= r["odds"] <= 350]
    short = [r for r in dogs if r["odds"] <= 150]
    favs = [r for r in R if -150 <= r["odds"] <= -101]
    print(f"\n================ {lg.upper()} - every regular-season side at the close, train {t0}-{t1} / held {h0}-{h1} ================")
    C("BASE every dog +100..+350", dogs)
    C("BASE every dog +100..+150", short)
    C("BASE every favorite -150..-101", favs)

    print(" -- H1 the rested dog against a favorite on a back-to-back, and what stacks on it")
    rb = lambda r: r["o_b2b"] and not r["b2b"]   # noqa: E731
    C("H1 dog, fav on a b2b, dog not", [r for r in dogs if rb(r)])
    C("H1 ... +100..+150", [r for r in short if rb(r)])
    C("H1a ... +100..+150, dog at HOME", [r for r in short if rb(r) and r["home"]])
    C("H1b ... +100..+150, dog rested 2+ days", [r for r in short if rb(r) and r["rest"] >= 2])
    C("H1c ... +100..+150, fav played on the ROAD last night", [r for r in short if rb(r) and r["o_prev_home"] is False])
    C("H1d ... +100..+150, fav 3rd game in 4 nights", [r for r in short if rb(r) and r["o_n4"] >= 2])
    C("H1e ... +100..+150, fav's last night went to OT", [r for r in short if rb(r) and r["o_prev_ot"]])
    C("H1f ... +100..+150, dog not hot (streak under 3)", [r for r in short if rb(r) and r["streak"] < 3])
    C("H1g ... +100..+150, home + rested 2+ + fav on the road last night", [r for r in short if rb(r) and r["home"] and r["rest"] >= 2 and r["o_prev_home"] is False])

    print(" -- H2 the dog confluence COUNT (one point each, named before looking)")

    def dcount(r):
        k = 0
        k += 1 if rb(r) else 0                                    # rested vs a b2b
        k += 1 if r["o_n4"] >= 2 else 0                           # the favorite's 3rd in 4
        k += 1 if r["home"] else 0
        k += 1 if r["streak"] <= -2 else 0                        # cold (hockey: the cold dog wins vs the price)
        k += 1 if (r["luck"] is not None and r["luck"] <= -0.04) else 0   # unlucky record
        k += 1 if (r["prev_m"] is not None and r["prev_m"] <= (-3 if lg == "nhl" else -15)) else 0   # off a blowout loss
        k += 1 if (r["o_streak"] >= 3) else 0                     # the favorite is the hot one
        k -= 1 if r["streak"] >= 3 else 0                         # the hot dog fade
        k -= 1 if r["b2b"] and not r["o_b2b"] else 0
        return k
    for r in dogs:
        r["k"] = dcount(r)
    for k in range(-2, 6):
        C(f"H2 dog +100..+350 count == {k}", [r for r in dogs if r["k"] == k])
    for k in (2, 3, 4):
        x = C(f"H2 dog +100..+150 count >= {k}", [r for r in short if r["k"] >= k])
        sel = [r for r in short if r["k"] >= k]
        print(f"      placebo vs every short dog: {mp.placebo(sel, short)} of 2000")
        mp.size_line([r for r in sel if r["season"] >= h0])
    for k in (3, 4):
        C(f"H2 dog +151..+350 count >= {k}", [r for r in dogs if r["odds"] > 150 and r["k"] >= k])

    print(" -- H3 the FAVORITE -150..-101 with the fades stacked on the dog across (the count)")

    def fcount(r):
        k = 0
        k += 1 if r["o_b2b"] and not r["b2b"] else 0             # rested, the dog on a b2b
        k += 1 if r["o_streak"] >= 3 else 0                       # the hot dog (hockey fade)
        k += 1 if (r["o_luck"] is not None and r["o_luck"] >= 0.04) else 0   # the dog's record is lucky
        k += 1 if r["o_n4"] >= 2 else 0
        k += 1 if r["home"] else 0
        k += 1 if r["o_trip"] >= 3 else 0                         # the dog deep in a road trip
        k -= 1 if r["b2b"] and not r["o_b2b"] else 0
        return k
    for r in favs:
        r["k"] = fcount(r)
    C("H3a fav -150..-101, rested, dog on a b2b", [r for r in favs if r["o_b2b"] and not r["b2b"]])
    C("H3b fav -150..-101, the dog on a 3+ win streak", [r for r in favs if r["o_streak"] >= 3])
    C("H3c fav -150..-101, the dog's record lucky (4+ pts over its goals)", [r for r in favs if r["o_luck"] is not None and r["o_luck"] >= 0.04])
    for k in range(-1, 5):
        C(f"H3 fav count == {k}", [r for r in favs if r["k"] == k])
    for k in (2, 3, 4):
        sel = [r for r in favs if r["k"] >= k]
        C(f"H3 fav count >= {k}", sel)
        print(f"      placebo vs every fav in band: {mp.placebo(sel, favs)} of 2000")
        mp.size_line([r for r in sel if r["season"] >= h0])

    print(" -- H4 situational extremes")
    C("H4a any side: opp 3rd in 4 AND on a b2b, we rested 2+", [r for r in R if -150 <= r["odds"] <= 350 and r["o_b2b"] and r["o_n4"] >= 2 and r["rest"] >= 2])
    C("H4b any side -150..+150: opp 4th game in 6 nights on a b2b, we rested 2+", [r for r in R if -150 <= r["odds"] <= 150 and r["o_b2b"] and r["o_n6"] >= 3 and r["rest"] >= 2])
    C("H4c home dog +100..+150 off 3+ days rest vs a fav on a b2b", [r for r in short if r["home"] and r["rest"] >= 3 and r["o_b2b"]])
    C("H4d fav -150..-101 at home, 5+ game homestand, the dog 4+ straight on the road", [r for r in favs if r["home"] and r["stand"] >= 4 and r["o_trip"] >= 3])
    C("H4e dog +100..+150 on a 4+ game LOSING skid, at home", [r for r in short if r["home"] and r["streak"] <= -4])
    C("H4f fav -150..-101 off 2 straight losses by a blowout margin", [r for r in favs if r["streak"] <= -2 and r["prev_m"] is not None and r["prev_m"] <= (-3 if lg == "nhl" else -15)])
    C("H4g Elo likes the dog: +100..+150 with the walk-forward Elo 6+ pts over the no-vig close", [r for r in short if r["p_elo"] - r["p_nv"] >= 0.06])
    C("H4h Elo likes the fav: -150..-101 with Elo 6+ over the close", [r for r in favs if r["p_elo"] - r["p_nv"] >= 0.06])

print(f"\ncells printed: {len(mp.TRIED)}")
