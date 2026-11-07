"""11/7 S1b / S2b follow-ups on the s1_s2_s3 cells (each a pre-named robustness cut, not a new hunt):
(a) the 🔍 rule's BIG gaps (25+) by the season stage, with the calibration (where the truth sits);
(b) the college favorite that has used 3+ quarterbacks this season (s2's strongest cell, z -3.1): the first fair number,
    ATS, the dose (2 QBs vs 3 vs 4+), month, the last game's QB the main starter or not; and the NFL as the second check."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

rows = json.load(open(os.path.join(lib.CACHE, "_gap1107_rows.json")))
xby = {x["id"]: x for x in lib.load_football("ncaaf")}


def att(st, r):
    if r["group"] != "passing":
        return None
    try:
        return int(str(st.get("completions/passingAttempts", "0/0")).split("/")[1])
    except (ValueError, IndexError):
        return None


def qbmap(lg):
    out = {}
    for gid, teams in lib.boxes(lg, att).items():
        for tm, ps in teams.items():
            if ps:
                pid, a = max(ps.items(), key=lambda kv: kv[1])
                if a >= 8:
                    out[(gid, str(tm))] = pid
    return out


def qb_info(tl, qb, team, start, season):
    prev = [g for g in lib.before(tl, team, start) if g["season"] == season]
    q = [qb.get((g["id"], str(team))) for g in prev]
    known = [x for x in q if x]
    if len(q) < 2 or q[-1] is None:
        return None
    cnt = defaultdict(int)
    for x in known:
        cnt[x] += 1
    main = max(cnt, key=cnt.get) if cnt else None
    return {"nqb": len(cnt), "nqb2": sum(1 for v in cnt.values() if v >= 2), "last_main": q[-1] == main,
            "ch1": len(q) >= 2 and q[-2] is not None and q[-1] != q[-2], "n": len(q)}


C = lib.Cells()
CAL = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
qb = qbmap("ncaaf")
tl = lib.team_log(lib.all_finals("ncaaf"))
dog = lambda r: 100 <= r["odds"] <= 350  # noqa: E731
for r in rows:
    if r["fbs"] != 2:
        continue
    s = r["season"]
    gap = r["own"] - r["nv"]
    p = lib.profit(r["won"], r["dec"])
    ep = lib.early_price(xby, r["gid"], r["side"])
    if dog(r) and r["elo"] >= 0 and gap >= 0.15:
        gn = min(r["gno"] or 99, r["ogno"] or 99)
        stage = "1-3" if gn <= 3 else "4-6" if gn <= 6 else "7+"
        band = "35+" if gap >= 0.35 else "25-35" if gap >= 0.25 else "15-25"
        k = f"(a) rule gap {band}, games {stage}"
        C.add(k, s, p)
        C.add(k + " FIRST FAIR", s, lib.profit(r["won"], ep[1]) if ep and 100 <= ep[0] <= 350 else None)
        x = CAL[k]
        x[0] += 1; x[1] += r["won"]; x[2] += r["own"]; x[3] += r["nv"]
        if gn > 3:
            k2 = f"(a) rule gap {'25+' if gap >= 0.25 else '15-25'}, games 4+"
            x = CAL[k2]
            x[0] += 1; x[1] += r["won"]; x[2] += r["own"]; x[3] += r["nv"]
    if s < 2021 or not -250 <= r["odds"] <= -101:
        continue
    st = qb_info(tl, qb, r["team"], r["start"], s)
    if not st:
        continue
    lab = "4+" if st["nqb"] >= 4 else str(st["nqb"])
    k = f"(b) fav -101..-250, QBs used {lab}"
    C.add(k, s, p)
    C.add(k + " FIRST FAIR", s, lib.profit(r["won"], ep[1]) if ep and ep[0] < 0 else None)
    g_ = {"sp": r["sp"], "hs": r["margin"] if r["side"] == "home" else 0, "as": 0 if r["side"] == "home" else r["margin"],
          "spho": None, "spao": None}
    C.add(k + " ATS", s, None if r["sp"] is None else lib.ats(g_, r["side"]))
    if st["nqb"] >= 3:
        C.add(f"(b) fav 3+ QBs, last game the main starter={st['last_main']}", s, p)
        C.add(f"(b) fav 3+ QBs, -101..-150={r['odds'] >= -150}", s, p)
        C.add(f"(b) fav 3+ QBs, month {r['start'][5:7]}", s, p)
        C.add(f"(b) fav 3+ QBs with 2+ starts each = {st['nqb2']}", s, p)
        C.add(f"(b) fav 3+ QBs, opp QBs used 3+={((qb_info(tl, qb, r['opp'], r['start'], s) or {}).get('nqb') or 0) >= 3}", s, p)

# NFL second check (the game files' close; the QB from the box scores)
fin = lib.finals("nfl")
qbn = qbmap("nfl")
tln = lib.team_log(lib.all_finals("nfl"))
for g in fin:
    if g["stype"] != "2":
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        if not -250 <= o <= -101:
            continue
        st = qb_info(tln, qbn, team, g["start"], g["season"])
        if not st:
            continue
        lab = "4+" if st["nqb"] >= 4 else str(st["nqb"])
        C.add(f"(b NFL) fav -101..-250, QBs used {lab}", g["season"], lib.profit(won, lib.dec(o)))
        C.add(f"(b NFL) fav -101..-250, QBs used {lab} ATS", g["season"], lib.ats(g, side))

C.dump("s1b", "11/7 S1b/S2b follow-ups (college: TRAIN 2018-22 (QB cells 2021-22) / held 2023-26; NFL same split)",
       (2018, 2022), [2023, 2024, 2025, 2026])
lines = ["\nCALIBRATION (n, won, read, no-vig):"]
for k in sorted(CAL):
    n, w, o, v = CAL[k]
    lines.append(f"{k:50s} n {n:4d} won {w/n:6.1%} read {o/n:6.1%} no-vig {v/n:6.1%} truth {((w - v) / (o - v)):+.2f} of the way to the read")
print("\n".join(lines))
open(os.path.join(lib.OUT, "s1b_out.txt"), "a").write("\n".join(lines) + "\n")
