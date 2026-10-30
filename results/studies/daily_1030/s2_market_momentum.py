"""STUDY 2 (10/30) - TEAM MARKET MOMENTUM: the team the money keeps coming to (steam, team angle).
For every team, the market's move on it in each of its earlier games this season = its no-vig win % at the CLOSE minus
at that game's first fair look (median book, paid odds history). A team the market moved TOWARD in each of its last 2
(1.5+ points each) / last 3 (sum 5+) is a team the books keep under-rating at the open - does that carry into THIS
week's first fair number (the market slow to learn), or is it priced? And the mirror (moved AWAY each time).
Graded at this game's first fair price: moneyline dogs +100..+350, favorites -101..-150, and ATS at the first fair
spread. Second check: NHL / NBA from the game files' open -> close (2023-26 only - the opens start 2023).
TRAIN 2020-23, HELD OUT 2024 / 2025 / 2026 (football); NHL / NBA 2023 train / 2024 / 2025 held / 2026 now."""
import json
import os

import lib

TRAIN, HELD = (2020, 2023), [2024, 2025, 2026]


def football(lg):
    games = lib.load_football(lg)
    hist = {}        # (season, team) -> [move]
    rows = []
    for g in games:
        ff = lib.first_fair(g["ml"])
        close = None
        if g["c_mlh"] is not None and g["c_mla"] is not None:
            try:
                close = lib.nv(g["c_mlh"], g["c_mla"])
            except ZeroDivisionError:
                close = None
        if ff:
            h, a, p = lib.ml_med(ff[1])
            fs = lib.first_fair(g["sp"])
            for side, team in (("home", g["home"]), ("away", g["away"])):
                past = hist.get((g["season"], team), [])
                d = h if side == "home" else a
                won = (g["margin"] > 0) == (side == "home")
                ats = None
                if fs:
                    line, hp, ap = lib.sp_med(fs[1])
                    pts = line if side == "home" else -line
                    mg = g["margin"] if side == "home" else -g["margin"]
                    if mg + pts != 0:
                        ats = lib.profit(mg + pts > 0, hp if side == "home" else ap)
                rows.append({"season": g["season"], "past": list(past), "d": d, "won": won, "ats": ats})
            if close is not None and g["margin"] != 0:
                mv = close - p
                hist.setdefault((g["season"], g["home"]), []).append(mv)
                hist.setdefault((g["season"], g["away"]), []).append(-mv)
    return rows


def gamefile(lg):
    games = sorted((x for x in lib.sd.load_games(lg).values() if (x.get("stype") or "?") in lib.sd.REAL),
                   key=lambda x: x.get("start") or "")
    hist, rows = {}, []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            oh, oa, ch, ca = (float(g[k]) for k in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or (oh == ch and oa == ca) and lib.season(g["start"]) < 2023:
            continue
        s = lib.season(g["start"])
        if s < 2023:
            continue
        po, pc = lib.nv(oh, oa), lib.nv(ch, ca)
        for side, team in (("home", g["home"]), ("away", g["away"])):
            d = lib.dec(oh if side == "home" else oa)
            rows.append({"season": s, "past": list(hist.get((s, team), [])), "d": d,
                         "won": (hs > as_) == (side == "home"), "ats": None})
        mv = pc - po
        hist.setdefault((s, g["home"]), []).append(mv)
        hist.setdefault((s, g["away"]), []).append(-mv)
    return rows


def cells(rows, train, held, lines, out, tag, mv_cut):
    defs = {
        f"moved TO it in each of its last 2 ({mv_cut}+ each)": lambda p: len(p) >= 2 and all(m >= mv_cut for m in p[-2:]),
        "moved TO it, last 3 sum 0.05+": lambda p: len(p) >= 3 and sum(p[-3:]) >= 0.05,
        "moved TO it, last 3 sum 0.08+": lambda p: len(p) >= 3 and sum(p[-3:]) >= 0.08,
        f"moved AWAY in each of its last 2 ({mv_cut}+ each)": lambda p: len(p) >= 2 and all(m <= -mv_cut for m in p[-2:]),
        "moved AWAY, last 3 sum 0.05+": lambda p: len(p) >= 3 and sum(p[-3:]) <= -0.05,
        "moved AWAY, last 3 sum 0.08+": lambda p: len(p) >= 3 and sum(p[-3:]) <= -0.08,
        "every side with 3+ games (base)": lambda p: len(p) >= 3,
    }
    for nm, fn in defs.items():
        cell = [r for r in rows if fn(r["past"])]
        dog = [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if 2.0 <= r["d"] <= 4.5]
        fav = [(r["season"], lib.profit(r["won"], r["d"])) for r in cell if 1.6667 <= r["d"] < 2.0]
        ats = [(r["season"], r["ats"]) for r in cell if r["ats"] is not None]
        for k, b in (("dog +100..+350", dog), ("fav -101..-150", fav), ("ATS first fair", ats)):
            if not b:
                continue
            s = lib.summ(b, train, held)
            out[f"{tag} {nm} {k}"] = s
            lines.append(lib.fmt(f"{tag} {nm[:34]} {k}", s))


def main():
    out, lines = {}, []
    for lg in ("nfl", "ncaaf"):
        lines.append(f"\n=== {lg.upper()} (first fair price; the move = close no-vig minus first fair no-vig) ===")
        cells(football(lg), TRAIN, HELD, lines, out, lg, 0.015)
    for lg in ("nhl", "nba"):
        lines.append(f"\n=== {lg.upper()} second check (bet at the OPEN; the move = close minus open, 2023-26) ===")
        cells(gamefile(lg), (2023, 2023), [2024, 2025, 2026], lines, out, lg, 0.015)
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s2_out.txt"), "w").write(txt + "\n")
    json.dump(out, open(os.path.join(lib.OUT, "s2_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
