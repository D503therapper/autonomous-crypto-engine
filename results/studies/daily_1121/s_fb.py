"""11/21 daily studies S5-S6 - FOOTBALL, the team box 2021-26 (data/sports/teamstats/<lg>.jsonl) - two columns the
studies never read (the player box holds no fumbles; the 11/4 / 11/10 luck studies read interceptions only):
  S5  FUMBLE LUCK (NFL + college): fumbles lost by the opponents minus our own, a game, this season before tonight
      (4+ box games) - UNLUCKY -0.4 or worse, LUCKY +0.4 or better; and the game after losing 2+ fumbles in a loss
  S6  NFL DEFENSIVE TOUCHDOWNS (the box's defensiveTouchdowns): the game after a win with one, the season's count
Prices: ESPN's close at its own juice, regular season; train 2021-23 / held out 2024 / 2025 / 2026. Cells fixed before
the run. python results/studies/daily_1121/s_fb.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402

TRAIN, HELD = (2021, 2023), [2024, 2025, 2026]


def teambox(lg):
    out = {}
    with open(os.path.join(sd.DATA, "teamstats", f"{lg}.jsonl")) as f:
        for ln in f:
            r = json.loads(ln)
            out[r["gid"]] = r["teams"]
    return out


def run(lg):
    O = h.Out(f"s5_s6_{lg}", TRAIN, HELD)
    O.p(f"S5 / S6 - {lg.upper()} (the team box 2021-26; train 2021-23 / held 2024-26)")
    tb = teambox(lg)
    fin = [g for g in lib.finals(lg) if g["stype"] == "2" and g["season"] >= 2021]
    allf = [g for g in lib.all_finals(lg) if g["season"] >= 2021]
    tl = lib.team_log(allf)

    def fl(gid, t):
        x = (tb.get(gid) or {}).get(str(t))
        v = lib.num((x or {}).get("fumblesLost"))
        return v

    def dtd(gid, t):
        x = (tb.get(gid) or {}).get(str(t))
        return lib.num((x or {}).get("defensiveTouchdowns"))

    def state(t, g):
        ps = [x for x in lib.before(tl, t, g["start"]) if x["season"] == g["season"]]
        rows = []
        for x in ps:
            o = x["away"] if x["home"] == t else x["home"]
            a, b = fl(x["id"], t), fl(x["id"], o)
            if a is not None and b is not None:
                rows.append((x, a, b, dtd(x["id"], t)))
        return ps, rows

    for g in fin:
        st = {s: state(t, g) for s, t in (("home", g["home"]), ("away", g["away"]))}
        for side, team, opp, o, won, _ in lib.sides(g):
            other = "away" if side == "home" else "home"
            ps, rows = st[side]
            _, orows = st[other]
            pr = lib.profit(won, lib.dec(o))
            a = lib.ats(g, side)
            b = h.band(o)
            s = g["season"]
            if b:
                O.add(f"base {b}", s, pr, o)
            O.add("base ats", s, a)
            if len(rows) >= 4:
                m = sum(y - x for _, x, y, _ in rows) / len(rows)
                tag = "UNLUCKY (-0.4 or worse)" if m <= -0.4 else "LUCKY (+0.4 or better)" if m >= 0.4 else None
                if tag:
                    if b:
                        O.add(f"S5 fumble {tag} {b}", s, pr, o)
                    O.add(f"S5 fumble {tag} ats", s, a)
                    if len(orows) >= 4:
                        om = sum(y - x for _, x, y, _ in orows) / len(orows)
                        if (m <= -0.4 and om >= 0.4) or (m >= 0.4 and om <= -0.4):
                            O.add(f"S5 fumble {tag} vs the opposite ats", s, a)
                            if b:
                                O.add(f"S5 fumble {tag} vs the opposite {b}", s, pr, o)
            if rows and rows[-1][0]["id"] == ps[-1]["id"]:
                lg_, mine, theirs, d = rows[-1]
                lost = not lib.won_g(lg_, team)
                if mine >= 2 and lost:
                    if b:
                        O.add(f"S5 lost 2+ fumbles in a loss last game {b}", s, pr, o)
                    O.add("S5 lost 2+ fumbles in a loss last game ats", s, a)
                if theirs >= 2 and not lost:
                    if b:
                        O.add(f"S5 won last game with 2+ fumbles recovered {b}", s, pr, o)
                    O.add("S5 won last game with 2+ fumbles recovered ats", s, a)
                if lg == "nfl" and d is not None:
                    if d >= 1 and not lost:
                        if b:
                            O.add(f"S6 won last game with a defensive TD {b}", s, pr, o)
                        O.add("S6 won last game with a defensive TD ats", s, a)
                        if abs(lib.margin_g(lg_, team)) <= 8:
                            O.add("S6 won last game by one score with a defensive TD ats", s, a)
                            if b:
                                O.add(f"S6 won last game by one score with a defensive TD {b}", s, pr, o)
            if lg == "nfl" and len(rows) >= 6:
                n = sum((d or 0) for _, _, _, d in rows)
                if n >= 3:
                    if b:
                        O.add(f"S6 3+ defensive TDs this season {b}", s, pr, o)
                    O.add("S6 3+ defensive TDs this season ats", s, a)
                if n == 0:
                    O.add("S6 no defensive TD this season (6+ games) ats", s, a)
    res = O.show()
    for k in list(res):
        if k.startswith("S") and res[k] and res[k]["all"]["n"] >= 60:
            pool = "base ats" if k.endswith("ats") else f"base {k.rsplit(' ', 1)[1]}"
            O.placebo(k, pool, fade=res[k]["all"]["roi"] < (res[pool]["all"]["roi"] if res.get(pool) else 0))
    O.save()


if __name__ == "__main__":
    for lg in (sys.argv[1:] or ["nfl", "ncaaf"]):
        run(lg)
