"""11/22 daily studies S1-S4 - THE TEAM BOX COLUMNS NO STUDY HAS READ (NBA + college hoops; data/sports/teamstats -
ESPN's team box 2021-26: pointsInPaint, fastBreakPoints, turnoverPoints, blocks). SPORTS_FINDINGS has no study on the
paint, on points off turnovers, or on the transition MATCHUP (the 11/13 quick study read the running team on a
back-to-back only).
  S1  NBA: THE PAINT - the share of a team's points scored in the paint / of its opponents' points given up there, the
      paint margin a game; the inside team against a defense that gives the paint up / against a shot-blocking team
  S2  COLLEGE HOOPS: THE PAINT - the same reads (D1 opponents only - a tune-up is never form)
  S3  POINTS OFF TURNOVERS (both leagues) - the margin a game and the share of a team's points that come off turnovers
  S4  THE TRANSITION MATCHUP (both leagues) - the running team (fast-break share of its points) against a team that
      gives up fast-break points, and both running on the total
Season to date before tonight (NBA 10+ box games, college 5+ against D1 teams) - no look-ahead. The top / bottom
fifth by cut points taken from the TRAIN seasons (2021-23) only; held out 2024 / 2025 / 2026. ESPN's close at its own
juice, regular season. Cells fixed before the run.   python results/studies/daily_1122/s_hoops.py [nba ncaab]"""
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]
MIN = {"nba": 10, "ncaab": 5}
COLS = ("pointsInPaint", "fastBreakPoints", "turnoverPoints", "blocks")


def teambox(lg):
    out = {}
    for f in [os.path.join(sd.DATA, "teamstats", f"{lg}.jsonl")] + sorted(glob.glob(os.path.join(sd.DATA, "teamstats", lg, "*.jsonl"))):
        if not os.path.exists(f):
            continue
        for ln in open(f):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            out[r["gid"]] = r["teams"]
    return out


def pct(vals, q):
    v = sorted(vals)
    return v[min(len(v) - 1, int(q * len(v)))]


def run(lg):
    O = h.Out(f"s1_s4_{lg}", TRAIN, HELD)
    O.p(f"S1-S4 - {lg.upper()} THE PAINT / POINTS OFF TURNOVERS / TRANSITION (team box 2021-26; train 2021-23 / held 2024-26)")
    tb = teambox(lg)
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    d1 = sm.ncaab_d1(allf) if lg == "ncaab" else None
    tl = lib.team_log(allf)

    def row(x, t):
        """One finished game as the team's raw line (None when the box is missing a column)."""
        o = x["away"] if x["home"] == t else x["home"]
        if d1 is not None and (o not in d1 or t not in d1):
            return None
        a, b = (tb.get(x["id"]) or {}).get(str(t)), (tb.get(x["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        v = {}
        for c in COLS:
            v[c], v["o_" + c] = lib.num(a.get(c)), lib.num(b.get(c))
            if v[c] is None or v["o_" + c] is None:
                return None
        v["pts"], v["o_pts"] = (x["hs"], x["as"]) if x["home"] == t else (x["as"], x["hs"])
        return v

    memo = {}

    def state(t, g):
        k = (t, g["id"])
        if k in memo:
            return memo[k]
        rows = [r for r in (row(x, t) for x in lib.before(tl, t, g["start"]) if x["season"] == g["season"]) if r]
        if len(rows) < MIN[lg]:
            memo[k] = None
            return None
        n = len(rows)
        s = lambda c: sum(r[c] for r in rows)                # noqa: E731
        f = {"paint_off": s("pointsInPaint") / max(1, s("pts")), "paint_def": s("o_pointsInPaint") / max(1, s("o_pts")),
             "paint_net": (s("pointsInPaint") - s("o_pointsInPaint")) / n,
             "fb_off": s("fastBreakPoints") / max(1, s("pts")), "fb_def": s("o_fastBreakPoints") / max(1, s("o_pts")),
             "top_net": (s("turnoverPoints") - s("o_turnoverPoints")) / n, "top_share": s("turnoverPoints") / max(1, s("pts")),
             "blk": s("blocks") / n}
        memo[k] = f
        return f

    FEATS = ("paint_off", "paint_def", "paint_net", "fb_off", "fb_def", "top_net", "top_share", "blk")
    pool = defaultdict(list)
    rows = []
    for g in fin:
        sh, sa = state(g["home"], g), state(g["away"], g)
        if not sh or not sa:
            continue
        rows.append((g, sh, sa))
        if TRAIN[0] <= g["season"] <= TRAIN[1]:
            for st in (sh, sa):
                for k in FEATS:
                    pool[k].append(st[k])
    cut = {k: (pct(pool[k], 0.2), pct(pool[k], 0.8)) for k in FEATS}
    O.p(f"games with both teams read: {len(rows)}; cut points (bottom / top fifth, train seasons): "
        + "; ".join(f"{k} {cut[k][0]:.3f} / {cut[k][1]:.3f}" for k in FEATS))
    NAME = {"paint_off": "scores in the paint (share of its points)", "paint_def": "gives up the paint (share of opp points)",
            "paint_net": "paint margin a game", "fb_off": "runs (fast-break share of its points)",
            "fb_def": "gives up the break (share of opp points)", "top_net": "points-off-turnovers margin a game",
            "top_share": "lives off turnovers (share of its points)", "blk": "blocks a game"}

    def hi(st, k):
        return st[k] >= cut[k][1]

    def lo(st, k):
        return st[k] <= cut[k][0]

    for g, sh, sa in rows:
        s = g["season"]
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (sh, sa) if side == "home" else (sa, sh)
            pr = lib.profit(won, lib.dec(o))
            at = lib.ats(g, side)
            dog, fav = 100 <= o <= 350, -150 <= o <= -101

            def put(tag):
                O.add(f"{tag}: ATS", s, at)
                if dog:
                    O.add(f"{tag}: dog +100..+350", s, pr, o)
                if fav:
                    O.add(f"{tag}: small fav -150..-101", s, pr, o)
            put("BASE every side")
            for k in FEATS:
                if hi(me, k):
                    put(f"TOP fifth {NAME[k]}")
                elif lo(me, k):
                    put(f"BOTTOM fifth {NAME[k]}")
            # the matchups
            if hi(me, "paint_off") and hi(th, "paint_def"):
                put("MATCHUP inside team vs a defense that gives up the paint")
            if hi(me, "paint_off") and lo(th, "paint_def"):
                put("MATCHUP inside team vs a defense that shuts the paint")
            if hi(me, "paint_off") and hi(th, "blk"):
                put("MATCHUP inside team vs a top-fifth shot-blocking team")
            if hi(me, "paint_net") and lo(th, "paint_net"):
                put("MATCHUP top paint margin vs bottom paint margin")
            if hi(me, "fb_off") and hi(th, "fb_def"):
                put("MATCHUP running team vs a team that gives up the break")
            if hi(me, "fb_off") and lo(th, "fb_def"):
                put("MATCHUP running team vs a team that takes the break away")
            if hi(me, "top_net") and lo(th, "top_net"):
                put("MATCHUP top turnover-points margin vs bottom")
            if hi(me, "top_share") and lo(th, "top_share"):
                put("MATCHUP lives off turnovers vs a team that doesn't")
        for name, cond in (("both score in the paint (top fifth)", hi(sh, "paint_off") and hi(sa, "paint_off")),
                           ("both bottom-fifth paint scorers", lo(sh, "paint_off") and lo(sa, "paint_off")),
                           ("both give up the paint (top fifth)", hi(sh, "paint_def") and hi(sa, "paint_def")),
                           ("both run (top fifth fast-break share)", hi(sh, "fb_off") and hi(sa, "fb_off")),
                           ("a running team vs a team that gives up the break (either way)",
                            (hi(sh, "fb_off") and hi(sa, "fb_def")) or (hi(sa, "fb_off") and hi(sh, "fb_def"))),
                           ("both live off turnovers (top fifth share)", hi(sh, "top_share") and hi(sa, "top_share")),
                           ("both top-fifth shot blockers", hi(sh, "blk") and hi(sa, "blk")),
                           ("BASE every game", True)):
            if cond:
                O.add(f"TOTAL {name}: over", s, lib.tot_profit(g, True))
                O.add(f"TOTAL {name}: under", s, lib.tot_profit(g, False))
    res = O.show()
    O.p("")
    O.p("PLACEBO - every cell at 100+ bets whose ROI sits 6+ points off its base, both halves the same side of it:")
    for k, r in res.items():
        if k.startswith("BASE") or k.startswith("TOTAL BASE") or not r or r["all"]["n"] < 100:
            continue
        kind = k.rsplit(": ", 1)[1]
        base = ("TOTAL BASE every game: " if k.startswith("TOTAL") else "BASE every side: ") + kind
        b = res.get(base)
        if not b or not r["train"] or not r["held_all"]:
            continue
        d = r["all"]["roi"] - b["all"]["roi"]
        if abs(d) >= 0.06 and (r["train"]["roi"] - b["train"]["roi"]) * d > 0 and (r["held_all"]["roi"] - b["held_all"]["roi"]) * d > 0:
            O.placebo(k, base, fade=d < 0)
    O.save()


if __name__ == "__main__":
    for lg in sys.argv[1:] or ("nba", "ncaab"):
        run(lg)
