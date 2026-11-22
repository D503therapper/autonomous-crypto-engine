"""11/22 daily studies S5-S10 - box columns no study has read (ESPN's team box 2021-26 + the player box), every read
LEAGUE-RELATIVE (a team's rank among the league's CURRENT values that night - the top / bottom fifth), what a team
did THIS season before tonight (no look-ahead), ESPN's close at its own juice, regular season; train 2021-23 / held
out 2024 / 2025 / 2026. Cells fixed before the run.
  S5  NHL: SHOT ATTEMPTS (shots on net + the shots the other team blocked - the team box's blockedShots, never read)
      against the built shots-on-net share (the dog score's ss_pos / ss_neg), last 10 games: does the attempt share
      say more, and who is right when the two disagree?
  S6  NHL: WHO SHOOTS - the defensemen's share of a team's shots (the skater box's positions), last 10: a team living
      on point shots; is its good shot share worth less?
  S7  FOOTBALL (NFL + college): PASSES DEFENDED AGAINST INTERCEPTIONS - a defense that gets its hands on the ball
      (the player box's passesDefended) but hasn't caught them (the opponents' interceptions in the team box): "due"
      (the 11/4 / 11/10 luck studies read the interception MARGIN, never the deflections)
  S8  FOOTBALL: THE BIG-PLAY PASSING OFFENSE - yards per completion (net passing yards / completions), the top fifth
      as a dog / a small favorite / against the spread, and the total
  S9  NFL: FIRST DOWNS BY PENALTY - the flags' gift (the team box's firstDownsPenalty, for minus against, a game)
  S10 FOOTBALL: THE RUN-GAME MISMATCH - yards per rush for (top fifth) against a run defense in the bottom fifth of
      yards per rush allowed (and the mirror)
python results/studies/daily_1122/s_rest.py [nhl nfl ncaaf]"""
import os
import sys
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_hoops  # noqa: E402

TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]


def ranked(allf, counters, feats, minn, window=None, minteams=20):
    """{(gid, team): {feat: (value, league pct)}} - each team's features from its earlier games this season (the last
    `window` when given), ranked among every team's current value that night."""
    hist = defaultdict(lambda: deque(maxlen=window))
    latest = defaultdict(dict)
    out = {}
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            rows = hist[(s, t)]
            if len(rows) >= minn:
                sums = defaultdict(float)
                for r in rows:
                    for k, v in r.items():
                        sums[k] += v
                f = feats(sums, len(rows))
                if f:
                    cur[t] = f
                    latest[s][t] = f
        vals = latest[s]
        if len(vals) >= minteams:
            for t, f in cur.items():
                out[(g["id"], t)] = {k: (f[k], sum(1 for x in vals.values() if x[k] < f[k]) / (len(vals) - 1)) for k in f}
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            c = counters(g, t, o)
            if c:
                hist[(s, t)].append(c)
    return out


def cells(O, fin, rk, flags, totals=()):
    """flags(me, them) -> [tags]; every tag gets ATS / dog / small fav / fav past -150 cells + the BASE."""
    n = 0
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if not a or not b:
            continue
        n += 1
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (a, b) if side == "home" else (b, a)
            pr, at = lib.profit(won, lib.dec(o)), lib.ats(g, side)
            for tag in ["BASE"] + list(flags(me, th)):
                O.add(f"{tag}: ATS", s, at)
                if 100 <= o <= 350:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                if -150 <= o <= -101:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
                if o < -150:
                    O.add(f"{tag}: fav past -150", s, pr, o)
        for name, cond in [("BASE every game", lambda x, y: True)] + list(totals):
            if cond(a, b):
                O.add(f"TOTAL {name}: over", s, lib.tot_profit(g, True))
                O.add(f"TOTAL {name}: under", s, lib.tot_profit(g, False))
    O.p(f"priced games with both teams ranked: {n}")
    res = O.show()
    O.p("")
    for k, r in res.items():
        if k.startswith("BASE") or k.startswith("TOTAL BASE") or not r or r["all"]["n"] < 100 or not r["train"] or not r["held_all"]:
            continue
        kind = k.rsplit(": ", 1)[1]
        base = ("TOTAL BASE every game: " if k.startswith("TOTAL") else "BASE: ") + kind
        b = res.get(base)
        if not b:
            continue
        d = r["all"]["roi"] - b["all"]["roi"]
        if abs(d) >= 0.06 and (r["train"]["roi"] - b["train"]["roi"]) * d > 0 and (r["held_all"]["roi"] - b["held_all"]["roi"]) * d > 0:
            O.placebo(k, base, fade=d < 0)


def hi(x, k, q=0.8):
    return x[k][1] >= q


def lo(x, k, q=0.2):
    return x[k][1] <= q


def nhl():
    tb = s_hoops.teambox("nhl")
    fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nhl") if g["season"] >= 2021 and g["stype"] == "2"]
    bx = lib.box_rows("nhl")

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        v = [lib.num(a.get("shotsTotal")), lib.num(b.get("shotsTotal")), lib.num(a.get("blockedShots")), lib.num(b.get("blockedShots"))]
        if None in v:
            return None
        c = {"sf": v[0], "sa": v[1], "af": v[0] + v[3], "aa": v[1] + v[2]}
        rows = (bx.get(g["id"]) or {}).get(str(t)) or []
        d = sum(lib.num(r["st"].get("shotsTotal")) or 0 for r in rows if r["pos"] == "D")
        al = sum(lib.num(r["st"].get("shotsTotal")) or 0 for r in rows if r["group"] != "goalies" and "shotsTotal" in r["st"])
        if al:
            c["dsh"], c["allsh"] = d, al
        return c

    def feats(s, n):
        if not s.get("allsh"):
            return None
        return {"ss": s["sf"] / (s["sf"] + s["sa"]), "as": s["af"] / (s["af"] + s["aa"]), "dshare": s["dsh"] / s["allsh"],
                "blk": (s["aa"] - s["sa"]) / max(1.0, s["aa"])}          # the share of the other side's attempts we block

    rk = ranked(allf, counters, feats, 10, window=10)
    O = h.Out("s5_s6_nhl", TRAIN, HELD)
    O.p("S5 / S6 - NHL SHOT ATTEMPTS AND WHO SHOOTS (last 10 games, league-relative fifths; team box + skater box 2021-26)")

    def flags(me, th):
        t = []
        for k, nm in (("ss", "shots-on-net share (the built read)"), ("as", "shot-ATTEMPT share (on net + blocked)"),
                      ("dshare", "defensemen's share of the shots"), ("blk", "share of the other side's attempts blocked")):
            if hi(me, k):
                t.append(f"S{'6' if k == 'dshare' else '5'} TOP fifth {nm}")
            elif lo(me, k):
                t.append(f"S{'6' if k == 'dshare' else '5'} BOTTOM fifth {nm}")
        if lo(me, "ss") and me["as"][1] >= 0.4:
            t.append("S5 DISAGREE out-shot on net (bottom fifth) but fine in attempts (40th pct up)")
        if lo(me, "ss") and me["as"][1] < 0.4:
            t.append("S5 AGREE out-shot on net and in attempts")
        if hi(me, "ss") and me["as"][1] <= 0.6:
            t.append("S5 DISAGREE out-shooting on net (top fifth) but not in attempts (60th pct down)")
        if hi(me, "ss") and me["as"][1] > 0.6:
            t.append("S5 AGREE out-shooting on net and in attempts")
        if hi(me, "ss") and hi(me, "dshare"):
            t.append("S6 out-shooting (top fifth) on point shots (top fifth D share)")
        if hi(me, "ss") and lo(me, "dshare", 0.4):
            t.append("S6 out-shooting (top fifth) with forwards shooting (bottom 40% D share)")
        if hi(me, "dshare") and lo(th, "dshare"):
            t.append("S6 point-shot team vs a forwards-shoot team")
        return t
    cells(O, fin, rk, flags, totals=[("both top-fifth D share of shots", lambda x, y: hi(x, "dshare") and hi(y, "dshare")),
                                     ("both top-fifth shot blockers", lambda x, y: hi(x, "blk") and hi(y, "blk"))])
    O.save()


def football(lg):
    tb = s_hoops.teambox(lg)
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021 and g["stype"] == "2"]
    bx = lib.box_rows(lg)

    def comp(x):
        try:
            c, a = str(x.get("completionAttempts")).replace("-", "/").split("/")[:2]
            return float(c), float(a)
        except (ValueError, AttributeError):
            return None

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        ca, cb = comp(a), comp(b)
        v = {"py": lib.num(a.get("netPassingYards")), "o_int": lib.num(b.get("interceptions")), "ry": lib.num(a.get("rushingYards")),
             "ra": lib.num(a.get("rushingAttempts")), "o_ry": lib.num(b.get("rushingYards")), "o_ra": lib.num(b.get("rushingAttempts"))}
        if None in v.values() or not ca or not cb:
            return None
        v["cmp"], v["o_att"] = ca[0], cb[1]
        rows = (bx.get(g["id"]) or {}).get(str(t))
        if rows:
            v["pd"] = sum(lib.num(r["st"].get("passesDefended")) or 0 for r in rows)
            v["pdn"] = 1
        if lg == "nfl":
            x, y = lib.num(a.get("firstDownsPenalty")), lib.num(b.get("firstDownsPenalty"))
            if x is None or y is None:
                return None
            v["fdp"], v["o_fdp"] = x, y
        return v

    def feats(s, n):
        if not s.get("cmp") or not s.get("ra") or not s.get("o_ra") or not s.get("pdn") or s["pdn"] < n:
            return None
        f = {"ypc": s["py"] / s["cmp"], "ypr": s["ry"] / s["ra"], "ypr_a": s["o_ry"] / s["o_ra"],
             "pd": s["pd"] / n, "int": s["o_int"] / n,
             "due": (s["pd"] - s["o_int"]) / max(1.0, s["pd"])}   # the share of the balls it got a hand on that it did NOT catch
        if lg == "nfl":
            f["fdp"] = (s["fdp"] - s["o_fdp"]) / n
        return f

    rk = ranked(allf, counters, feats, 4, minteams=20 if lg == "nfl" else 60)
    O = h.Out(f"s7_s10_{lg}", TRAIN, HELD)
    O.p(f"S7-S10 - {lg.upper()} PASSES DEFENDED / BIG-PLAY PASSING / PENALTY FIRST DOWNS / THE RUN-GAME MISMATCH (season to date, 4+ box games, league-relative fifths)")

    def flags(me, th):
        t = []
        if hi(me, "pd") and lo(me, "int", 0.4):
            t.append("S7 DUE: top-fifth passes defended, bottom-40% interceptions")
        if hi(me, "due") and me["pd"][1] >= 0.4:
            t.append("S7 DUE: top-fifth share of deflections not caught (40th pct up in deflections)")
        if lo(me, "due") and hi(me, "int"):
            t.append("S7 LUCKY: top-fifth interceptions on a bottom-fifth share not caught")
        if hi(me, "pd"):
            t.append("S7 top-fifth passes defended a game")
        if lo(me, "pd"):
            t.append("S7 bottom-fifth passes defended a game")
        if hi(me, "ypc"):
            t.append("S8 BIG-PLAY passing (top-fifth yards per completion)")
        if lo(me, "ypc"):
            t.append("S8 dink-and-dunk passing (bottom-fifth yards per completion)")
        if hi(me, "ypc") and lo(th, "ypc"):
            t.append("S8 big-play passing vs dink-and-dunk")
        if lg == "nfl":
            if hi(me, "fdp"):
                t.append("S9 top-fifth penalty first downs margin (the flags' gifts)")
            if lo(me, "fdp"):
                t.append("S9 bottom-fifth penalty first downs margin")
        if hi(me, "ypr") and hi(th, "ypr_a"):
            t.append("S10 MISMATCH top-fifth run game vs a bottom-fifth run defense")
        if hi(me, "ypr") and lo(th, "ypr_a"):
            t.append("S10 top-fifth run game vs a top-fifth run defense")
        if lo(me, "ypr") and hi(th, "ypr_a"):
            t.append("S10 bottom-fifth run game vs a bottom-fifth run defense")
        if lo(me, "ypr_a") and lo(th, "ypr"):
            t.append("S10 top-fifth run defense vs a bottom-fifth run game")
        if hi(me, "ypr"):
            t.append("S10 top-fifth yards per rush")
        if hi(me, "ypr_a"):
            t.append("S10 bottom-fifth run defense (most yards per rush allowed)")
        return t
    cells(O, fin, rk, flags, totals=[("both big-play passing (top fifth)", lambda x, y: hi(x, "ypc") and hi(y, "ypc")),
                                     ("both dink-and-dunk (bottom fifth)", lambda x, y: lo(x, "ypc") and lo(y, "ypc")),
                                     ("a top-fifth run game vs a bottom-fifth run defense (either way)",
                                      lambda x, y: (hi(x, "ypr") and hi(y, "ypr_a")) or (hi(y, "ypr") and hi(x, "ypr_a")))])
    O.save()


if __name__ == "__main__":
    for a in sys.argv[1:] or ("nhl", "nfl", "ncaaf"):
        nhl() if a == "nhl" else football(a)
