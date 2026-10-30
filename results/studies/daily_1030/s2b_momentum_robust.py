"""STUDY 2b (10/30) - robustness of the NHL / NBA 'market momentum' cells found in s2 (bet at the OPEN):
(a) no-leak: the team's previous game started 2+ days before this one (so its close was known before this open);
(b) the SAME sides graded at the CLOSE - if the profit is only this game's move it vanishes there (bettable early only);
(c) does this game's own line keep moving the same way (open -> close), how far;
(d) dose: sum of the last 3 moves by size; (e) the 2026 season so far; (f) overlap with the NBA opening-line play's
inputs - the 10-game form (does momentum just re-find form?)."""
import json
import os
from datetime import datetime

import lib


def rows_for(lg):
    games = sorted((x for x in lib.sd.load_games(lg).values() if (x.get("stype") or "?") in lib.sd.REAL),
                   key=lambda x: x.get("start") or "")
    hist, last, form, rows = {}, {}, {}, []
    for g in games:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            oh, oa, ch, ca = (float(g[k]) for k in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
        except (KeyError, ValueError, TypeError):
            continue
        s = lib.season(g["start"])
        if s < 2023 or hs == as_:
            continue
        t = datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
        po, pc = lib.nv(oh, oa), lib.nv(ch, ca)
        for side, team in (("home", g["home"]), ("away", g["away"])):
            prev = last.get((s, team))
            gap = (t - prev).total_seconds() / 86400 if prev else None
            sg = 1 if side == "home" else -1
            rows.append({"season": s, "past": list(hist.get((s, team), [])), "gap": gap,
                         "do": lib.dec(oh if side == "home" else oa), "dc": lib.dec(ch if side == "home" else ca),
                         "won": (hs > as_) == (side == "home"), "move": sg * (pc - po),
                         "form": list(form.get((s, team), []))})
        mv = pc - po
        hist.setdefault((s, g["home"]), []).append(mv)
        hist.setdefault((s, g["away"]), []).append(-mv)
        last[(s, g["home"])] = last[(s, g["away"])] = t
        form.setdefault((s, g["home"]), []).append(hs - as_)
        form.setdefault((s, g["away"]), []).append(as_ - hs)
    return rows


def main():
    lines, out = [], {}
    TR, HE = (2023, 2023), [2024, 2025, 2026]
    for lg in ("nhl", "nba"):
        rows = [r for r in rows_for(lg) if len(r["past"]) >= 3]
        lines.append(f"\n=== {lg.upper()} ({len(rows)} sides with 3+ earlier priced games) ===")
        groups = {
            "AWAY each of last 2 (1.5+)": lambda r: all(m <= -0.015 for m in r["past"][-2:]),
            "AWAY last 3 sum 0.08+": lambda r: sum(r["past"][-3:]) <= -0.08,
            "AWAY last 3 sum 0.05-0.08": lambda r: -0.08 < sum(r["past"][-3:]) <= -0.05,
            "AWAY last 3 sum 0.02-0.05": lambda r: -0.05 < sum(r["past"][-3:]) <= -0.02,
            "flat last 3 (-0.02..+0.02)": lambda r: abs(sum(r["past"][-3:])) < 0.02,
            "TO last 3 sum 0.02-0.05": lambda r: 0.02 <= sum(r["past"][-3:]) < 0.05,
            "TO last 3 sum 0.05-0.08": lambda r: 0.05 <= sum(r["past"][-3:]) < 0.08,
            "TO last 3 sum 0.08+": lambda r: sum(r["past"][-3:]) >= 0.08,
            "TO each of last 2 (1.5+)": lambda r: all(m >= 0.015 for m in r["past"][-2:]),
        }
        for nm, fn in groups.items():
            for band, lo, hi in (("dog +100..+350", 2.0, 4.5), ("fav -101..-150", 1.6667, 2.0)):
                cell = [r for r in rows if fn(r) and lo <= r["do"] < hi + (0.0001 if hi == 4.5 else 0)]
                if not cell:
                    continue
                noleak = [r for r in cell if r["gap"] is not None and r["gap"] >= 2.0]
                a = lib.summ([(r["season"], lib.profit(r["won"], r["do"])) for r in cell], TR, HE)
                b = lib.summ([(r["season"], lib.profit(r["won"], r["do"])) for r in noleak], TR, HE)
                c = lib.summ([(r["season"], lib.profit(r["won"], r["dc"])) for r in cell], TR, HE)
                mv = sum(r["move"] for r in cell) / len(cell)
                lines.append(lib.fmt(f"{nm} {band} @open", a))
                lines.append(lib.fmt(f"   no-leak (prev game 2+ days) @open", b))
                lines.append(lib.fmt(f"   same sides @CLOSE", c))
                lines.append(f"   this game's own move open->close for the side: {mv*100:+.2f} pts")
                out[f"{lg} {nm} {band}"] = {"open": a, "noleak": b, "close": c, "move": round(mv, 4)}
        # does momentum just re-find form? split the AWAY-sum-0.05+ dogs by last-5 margin
        cell = [r for r in rows if sum(r["past"][-3:]) <= -0.05 and 2.0 <= r["do"] <= 4.5 and len(r["form"]) >= 5]
        for nm, fn in (("form last 5 margin > 0", lambda r: sum(r["form"][-5:]) > 0),
                       ("form last 5 margin <= 0", lambda r: sum(r["form"][-5:]) <= 0)):
            sub = [r for r in cell if fn(r)]
            lines.append(lib.fmt(f"AWAY sum 0.05+ dogs, {nm} @open", lib.summ([(r["season"], lib.profit(r["won"], r["do"])) for r in sub], TR, HE)))
        base = [r for r in rows if 2.0 <= r["do"] <= 4.5 and len(r["form"]) >= 5]
        for nm, fn in (("form last 5 margin > 0", lambda r: sum(r["form"][-5:]) > 0),
                       ("form last 5 margin <= 0", lambda r: sum(r["form"][-5:]) <= 0)):
            sub = [r for r in base if fn(r)]
            lines.append(lib.fmt(f"ALL dogs, {nm} @open (base)", lib.summ([(r["season"], lib.profit(r["won"], r["do"])) for r in sub], TR, HE)))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s2b_out.txt"), "w").write(txt + "\n")
    json.dump(out, open(os.path.join(lib.OUT, "s2b_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
