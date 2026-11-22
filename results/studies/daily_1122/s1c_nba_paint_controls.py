"""11/22 daily studies S1c - THE NBA PAINT DEFENSE, the controls before a weight (s1b: the dog that SHUTS the paint
+8.5% on 707, the dog ACROSS a paint-shutting team -15.5% on 747, both halves). Is it only "a good defense" the
books already have another way? The same league-relative fifths, split by
  (a) the team's points allowed a game (the league's best fifth / the rest) and its scoring margin (winning / losing)
  (b) home / road, the price (+100..+149 / +150..+199 / +200..+350), the month (Oct-Dec / Jan-Apr)
  (c) the plain defense read alone as a control (best fifth in points allowed, whatever the paint)
python results/studies/daily_1122/s1c_nba_paint_controls.py"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_hoops  # noqa: E402
import s_rest  # noqa: E402

TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]


def main():
    O = h.Out("s1c_nba_paint_controls", TRAIN, HELD)
    O.p("S1c - NBA PAINT DEFENSE: THE CONTROLS (league-relative fifths, 10+ box games)")
    tb = s_hoops.teambox("nba")
    fin = [g for g in lib.finals("nba") if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals("nba") if g["season"] >= 2021 and g["stype"] == "2"]

    def counters(g, t, o):
        a, b = (tb.get(g["id"]) or {}).get(str(t)), (tb.get(g["id"]) or {}).get(str(o))
        if not a or not b:
            return None
        op = lib.num(b.get("pointsInPaint"))
        if op is None:
            return None
        pts, opts = (g["hs"], g["as"]) if g["home"] == t else (g["as"], g["hs"])
        return {"o_paint": op, "pts": pts, "o_pts": opts}

    def feats(s, n):
        return {"pd": s["o_paint"] / max(1.0, s["o_pts"]), "allowed": s["o_pts"] / n, "margin": (s["pts"] - s["o_pts"]) / n}

    rk = s_rest.ranked(allf, counters, feats, 10, minteams=20)
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if not a or not b:
            continue
        s = g["season"]
        mth = int(g["start"][5:7])
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (a, b) if side == "home" else (b, a)
            pr = lib.profit(won, lib.dec(o))
            if not 100 <= o <= 350:
                continue
            O.add("BASE dog +100..+350", s, pr, o)
            shut, across = me["pd"][1] <= 0.2, th["pd"][1] <= 0.2 and me["pd"][1] > 0.2
            gooddef = me["allowed"][1] <= 0.2
            if gooddef:
                O.add("CONTROL the dog in the best fifth of points allowed (whatever the paint)", s, pr, o)
            if th["allowed"][1] <= 0.2:
                O.add("CONTROL the dog across a best-fifth defense by points allowed", s, pr, o)
            for nm, c in (("SHUT dog", shut), ("dog ACROSS a paint-shutting team", across)):
                if not c:
                    continue
                O.add(nm, s, pr, o)
                x = me if nm == "SHUT dog" else th
                O.add(f"{nm}: the shutting team is a best-fifth defense by points allowed" if x["allowed"][1] <= 0.2
                      else f"{nm}: the shutting team is NOT a best-fifth defense", s, pr, o)
                O.add(f"{nm}: the shutting team wins on the scoreboard (margin above 0)" if x["margin"][0] > 0
                      else f"{nm}: the shutting team loses on the scoreboard", s, pr, o)
                O.add(f"{nm}: the dog at home" if side == "home" else f"{nm}: the dog on the road", s, pr, o)
                O.add(f"{nm}: +100..+149" if o < 150 else f"{nm}: +150..+199" if o < 200 else f"{nm}: +200..+350", s, pr, o)
                O.add(f"{nm}: Oct-Dec" if mth >= 10 else f"{nm}: Jan-Apr", s, pr, o)
            if shut and th["pd"][1] <= 0.2:
                O.add("both shut the paint: the dog", s, pr, o)
    O.show()
    O.p("")
    O.placebo("SHUT dog: the shutting team is NOT a best-fifth defense", "BASE dog +100..+350")
    O.placebo("CONTROL the dog in the best fifth of points allowed (whatever the paint)", "BASE dog +100..+350")
    O.placebo("dog ACROSS a paint-shutting team", "BASE dog +100..+350", fade=True)
    O.placebo("dog ACROSS a paint-shutting team: the shutting team is NOT a best-fifth defense", "BASE dog +100..+350", fade=True)
    O.placebo("CONTROL the dog across a best-fifth defense by points allowed", "BASE dog +100..+350", fade=True)
    O.save()


if __name__ == "__main__":
    main()
