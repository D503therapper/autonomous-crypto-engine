"""11/7 S1 / S2 / S3 - the 🔍 college football gap play's BIGGEST gaps (priority 1), the college QB change and the
ratings (priority 2), the stale-preseason-prior gap (games 1-3).
Rows: s1_gap_rows.py (walk-forward raw read = sm.own_p, every priced college game 2018-26). The 🔍 rule as wired: a dog
+100..+350, both teams FBS, Elo + home edge backing the dog (elo >= 0), raw read 15+ over the no-vig close.
Second price: the paid odds history's FIRST FAIR number (lib.early_price - posted after both teams' last games).
QB: the top passer (most attempts) of each team-game in the box scores (2021-26)."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

rows = json.load(open(os.path.join(lib.CACHE, "_gap1107_rows.json")))
xby = {x["id"]: x for x in lib.load_football("ncaaf")}


# ---------- the QB of every team-game (box scores 2021-26)
def att(st, r):
    if r["group"] != "passing":
        return None
    try:
        return int(str(st.get("completions/passingAttempts", "0/0")).split("/")[1])
    except (ValueError, IndexError):
        return None


bx = lib.boxes("ncaaf", att)
qb = {}   # (gid, team) -> pid of the top passer
for gid, teams in bx.items():
    for tm, ps in teams.items():
        if ps:
            pid, a = max(ps.items(), key=lambda kv: kv[1])
            if a >= 8:
                qb[(gid, tm)] = pid
fin = lib.all_finals("ncaaf")
tl = lib.team_log(fin)


def qb_state(team, start, season):
    """(qb box known for the last 2 games, changed at the last game, changed at either of the last 2, the last game's
    QB is not the season's main starter (most starts so far, 3+ games), n games this season)"""
    prev = [g for g in lib.before(tl, team, start) if g["season"] == season]
    q = [qb.get((g["id"], str(team))) or qb.get((g["id"], team)) for g in prev]
    if len(q) < 2 or q[-1] is None or q[-2] is None:
        return None
    ch1 = q[-1] != q[-2]
    ch2 = ch1 or (len(q) >= 3 and q[-3] is not None and q[-2] != q[-3])
    main = None
    known = [x for x in q if x]
    if len(known) >= 3:
        cnt = defaultdict(int)
        for x in known:
            cnt[x] += 1
        main = max(cnt, key=cnt.get)
    off_main = main is not None and q[-1] != main
    nq = len(set(known))
    return {"ch1": ch1, "ch2": ch2, "off_main": off_main, "nqb": nq}


C = lib.Cells()
CAL = defaultdict(lambda: [0, 0.0, 0.0, 0.0])   # cell -> [n, sum won, sum own, sum nv]


def cal(k, r):
    x = CAL[k]
    x[0] += 1
    x[1] += r["won"]
    x[2] += r["own"]
    x[3] += r["nv"]


dog = lambda r: 100 <= r["odds"] <= 350  # noqa: E731
for r in rows:
    if r["fbs"] != 2:
        continue
    s = r["season"]
    gap = r["own"] - r["nv"]
    backed = r["elo"] >= 0
    p_close = lib.profit(r["won"], r["dec"])
    ep = lib.early_price(xby, r["gid"], r["side"])
    p_ff = lib.profit(r["won"], ep[1]) if ep and 100 <= ep[0] <= 350 else None
    st = qb_state(r["team"], r["start"], s) if s >= 2021 else None
    ost = qb_state(r["opp"], r["start"], s) if s >= 2021 else None
    r["qb"], r["oqb"] = st, ost
    # ---- calibration of the raw read by QB state (every FBS side, priority 2)
    if st:
        for lab, on in (("ch1", st["ch1"]), ("ch2", st["ch2"]), ("off_main", st["off_main"]), ("nqb3+", st["nqb"] >= 3)):
            cal(f"S2 cal ALL sides, own QB {lab}={on}", r)
            if dog(r):
                cal(f"S2 cal DOGS, own QB {lab}={on}", r)
                C.add(f"S2 dog +100..+350, own QB {lab}={on}", s, p_close)
                if gap >= 0.10 and backed:
                    C.add(f"S2 dog backed gap 10+, own QB {lab}={on}", s, p_close)
            if -250 <= r["odds"] <= -101:
                C.add(f"S2 fav -101..-250, own QB {lab}={on}", s, p_close)
                cal(f"S2 cal FAVS -101..-250, own QB {lab}={on}", r)
    if not dog(r):
        continue
    rule = backed and gap >= 0.15
    bands = ((0.15, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.35), (0.35, 0.45), (0.45, 1))
    if backed and gap >= 0.10:
        for lo, hi in bands:
            if lo <= gap < hi:
                C.add(f"S1 rule gap {int(lo*100)}-{int(hi*100) if hi < 1 else 99}", s, p_close)
                C.add(f"S1 rule gap {int(lo*100)}-{int(hi*100) if hi < 1 else 99} FIRST FAIR", s, p_ff)
                cal(f"S1 cal gap {int(lo*100)}-{int(hi*100) if hi < 1 else 99}", r)
        for lab, ok in (("15-25", 0.15 <= gap < 0.25), ("25+", gap >= 0.25), ("35+", gap >= 0.35), ("15+", gap >= 0.15),
                        ("15-35", 0.15 <= gap < 0.35)):
            if ok:
                C.add(f"S1 rule gap {lab}", s, p_close)
                C.add(f"S1 rule gap {lab} FIRST FAIR", s, p_ff)
                cal(f"S1 cal gap {lab}", r)
                C.add(f"S1 rule gap {lab} ATS", s, None if r["sp"] is None else
                      lib.ats({"sp": r["sp"], "hs": r["margin"] if r["side"] == "home" else 0,
                               "as": 0 if r["side"] == "home" else r["margin"], "spho": None, "spao": None}, r["side"]))
        # own-read level (the read itself, not the gap)
        for lab, ok in (("own 50-60", 0.5 <= r["own"] < 0.6), ("own 60-70", 0.6 <= r["own"] < 0.7), ("own 70+", r["own"] >= 0.7)):
            if rule and ok:
                C.add(f"S1 rule {lab}", s, p_close)
    if rule:
        # S3 the stale preseason prior: the dog's / favorite's game number this season
        gn = min(r["gno"] or 99, r["ogno"] or 99)
        C.add(f"S3 rule, games in (min) {'1-3' if gn <= 3 else '4-6' if gn <= 6 else '7+'}", s, p_close)
        C.add(f"S3 rule, games in (min) {'1-3' if gn <= 3 else '4-6' if gn <= 6 else '7+'} FIRST FAIR", s, p_ff)
        big = gap >= 0.25
        C.add(f"S3 rule gap {'25+' if big else '15-25'}, games {'1-3' if gn <= 3 else '4+'}", s, p_close)
        # the Elo gap vs the record: a dog rated higher raw (elo_raw > 0) vs only with home edge
        C.add(f"S1b rule, dog rated higher raw={r['elo_raw'] > 0}", s, p_close)
        C.add(f"S1b rule gap {'25+' if big else '15-25'}, dog rated higher raw={r['elo_raw'] > 0}", s, p_close)
        # the market's disagreement: how big the dog is
        C.add(f"S1b rule gap {'25+' if big else '15-25'}, price {'+100..+150' if r['odds'] <= 150 else '+151..+350'}", s, p_close)
        if st:
            for lab, on in (("ch1", st["ch1"]), ("ch2", st["ch2"]), ("off_main", st["off_main"])):
                C.add(f"S2 RULE dog's QB {lab}={on}", s, p_close)
                C.add(f"S2 RULE dog's QB {lab}={on} FIRST FAIR", s, p_ff)
                cal(f"S2 cal RULE dog's QB {lab}={on}", r)
                C.add(f"S2 RULE gap {'25+' if big else '15-25'}, dog's QB {lab}={on}", s, p_close)
        if ost:
            C.add(f"S2 RULE fav's QB ch2={ost['ch2']}", s, p_close)

hdr = ("11/7 S1-S3 (college football 2018-26, FBS v FBS, at the close unless FIRST FAIR; TRAIN 2018-22 / held 2023-26; "
       "QB cells 2021-26 - train 2021-22)")
C.dump("s1_s2_s3", hdr, (2018, 2022), [2023, 2024, 2025, 2026])
lines = ["\nCALIBRATION (n, won%, raw read%, no-vig%) - where the truth sits between the market and the read:"]
for k in sorted(CAL):
    n, w, o, v = CAL[k]
    share = ((w - v) / (o - v)) if abs(o - v) > 1e-9 else float("nan")
    lines.append(f"{k:60s} n {n:5d} won {w/n:6.1%} read {o/n:6.1%} no-vig {v/n:6.1%}  truth = {share:+.2f} of the way to the read")
print("\n".join(lines))
open(os.path.join(lib.OUT, "s1_s2_s3_out.txt"), "a").write("\n".join(lines) + "\n")
# the live gap plays + today's four, and the biggest historical gaps (who they were)
big = sorted([r for r in rows if r["fbs"] == 2 and dog(r) and r["elo"] >= 0 and r["own"] - r["nv"] >= 0.35],
             key=lambda r: r["start"])
out = [f"\nEVERY 35+ GAP (FBS, backed) - {len(big)}:"]
for r in big:
    out.append(f"{r['start'][:10]} {r['tn']:22s} +{r['odds']:<4d} vs {r['on']:22s} read {r['own']:.0%} no-vig {r['nv']:.0%} "
               f"g{r['gno']}/{r['ogno']} {'W' if r['won'] else 'L'} {r['margin']:+.0f} qb {r.get('qb')}")
print("\n".join(out))
open(os.path.join(lib.OUT, "s1_s2_s3_out.txt"), "a").write("\n".join(out) + "\n")
