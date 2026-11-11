"""B3 - THE ENGINE vs THE LINE, EVERY GAME (the 10/6 Dr. Bob study's side note: on the weeks his pages covered, the
engine's own margin read 2+ points off the closing spread went 76-58-1 ATS, 5 of 5 seasons - 'the known engine-vs-the-
line lead'. It was never run on EVERY week, in college football or the NBA, or at an early price.)
The read is BLIND exactly as tools/drbob_study.engine_reads builds it: each season's spread weights (sm.tune) fit on
the 3 seasons before it, Elo walked in order, the game-day injury / key-player inputs zeroed (no history of them).
  (a) the engine's number 2 / 3 / 4 / 6+ points off the CLOSING spread -> its side ATS at the close;
  (b) football: the same against the first FAIR spread of the paid odds history, graded at that early number;
  (c) WHERE THE MONEYLINE READ AND THE SPREAD DISAGREE: the engine's own win read (sm.own_p) has the spread DOG
      winning outright -> that dog ATS and on the moneyline (+100..+350).
Seasons 2019-26, every one out of sample (TRAIN column = 2019-22, HELD = 2023 / 2024 / 2025 / 2026 apart)."""
import sys
import lib

B, sm, sd = lib.B, lib.sm, lib.sd
LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
o = lib.Out(f"b3_{LG}")
FB = LG in ("nfl", "ncaaf")


def reads():
    games = sd.load_games(LG)
    fin = sm.finals(games, LG)
    out = {}
    for season in range(2019, 2027):
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        p = sm.tune(learn, LG)
        if not p or "sw" not in p:
            continue
        _, played = sm.replay(fin, p["k"], p["hfa"], LG)
        for g, f, *_ in played:
            if lo <= g["start"] < hi:
                f0 = {**f, "inj": 0.0, "key": 0.0}
                out[g["id"]] = (sum(a * b for a, b in zip(p["sw"], sm._spread_x(f0))), sm.own_p(p, f0))
    return out


rd = lib.cached(f"b3_reads_{LG}", reads)
fin = [g for g in B.finals(LG) if g["stype"] == "2" and g["sp"] is not None and g["id"] in rd]
hist = {x["id"]: x for x in B.load_football(LG)} if FB else {}
C = lib.Cells()
se = [0.0, 0.0, 0]
for g in fin:
    s = g["season"]
    mine, own = rd[g["id"]]
    m = g["hs"] - g["as"]
    se[0] += (m - mine) ** 2; se[1] += (m + g["sp"]) ** 2; se[2] += 1
    d = mine + g["sp"]
    side = "home" if d > 0 else "away"
    a = B.ats(g, side)
    spme = g["sp"] if side == "home" else -g["sp"]
    for cut in (2, 3, 4, 6):
        if abs(d) >= cut:
            C.add(f"KEY (a) engine {cut}+ pts off the CLOSE", s, a)
            C.add(f"(a) {cut}+ off the close, on the {'dog' if spme > 0 else 'favorite'}", s, a)
    if 2 <= abs(d) < 4:
        C.add("(a) engine 2-4 pts off the close", s, a)
    if FB and g["id"] in hist:
        ff = B.first_fair(hist[g["id"]]["sp"])
        if ff:
            pts, dh, da = B.sp_med(ff[1])
            de = mine + pts
            es = "home" if de > 0 else "away"
            cov = (m + pts) if es == "home" else -(m + pts)
            for cut in (2, 3, 4, 6):
                if abs(de) >= cut and cov != 0:
                    C.add(f"KEY (b) engine {cut}+ off the FIRST FAIR spread, at that number", s,
                          lib.profit(cov > 0, dh if es == "home" else da))
    # (c) the moneyline read has the spread dog winning outright
    dog = "home" if g["sp"] > 0 else "away" if g["sp"] < 0 else None
    if dog:
        pw = own if dog == "home" else 1 - own
        od = g["mlh"] if dog == "home" else g["mla"]
        won = (m > 0) if dog == "home" else (m < 0)
        for cut in (0.50, 0.55, 0.60):
            if pw >= cut:
                C.add(f"KEY (c) own read {int(cut*100)}%+ on the spread DOG -> the dog ATS", s, B.ats(g, dog))
                if 100 <= od <= 350:
                    C.add(f"KEY (c) own read {int(cut*100)}%+ on the spread DOG -> its MONEYLINE", s, lib.profit(won, lib.dec(od)))
        if pw < 0.35:
            C.add("(c) own read under 35% on the dog -> the FAVORITE ATS", s, B.ats(g, "away" if dog == "home" else "home"))
o.p(f"B3 - {LG}: {len(fin)} priced games 2019-26 with a blind engine read; RMSE engine {(se[0]/se[2])**.5:.2f} vs the close {(se[1]/se[2])**.5:.2f}")
o.cells(C, (2019, 2022), (2023, 2024, 2025, 2026), zshow=99)
o.p(f"cells: {len(C.c)}")
o.save()
