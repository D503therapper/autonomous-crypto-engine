"""STUDY 1 (10/30) - THE MARKET'S OWN RATINGS vs THE FIRST FAIR NUMBER (NFL + college football, paid odds history).
Openers vs closers / when value appears: build each team's rating ONLY from the closing spreads of its games already
played (this season, ridge-shrunk toward 60% of last season's final rating), so the 'market line' for a new game is what
the market itself said about these teams last week. Where the first fair number of the week (median book, posted after
both teams' last games) sits 1.5 / 2.5 / 3.5+ points off that market line:
  (a) does the close move toward the market line (the first number was off), and
  (b) does the side the market line favors win at the first fair price - ATS at the median number + juice, and the
      moneyline (dogs +100..+350, favorites -101..-150) at the median price?
TRAIN 2020-23, HELD OUT 2024 / 2025 apart, NOW 2026. Nothing here sees the game it grades."""
import json
import os

import lib

TRAIN, HELD = (2020, 2023), [2024, 2025, 2026]
LAM = 2.0          # games-worth of pull toward the prior
CARRY = 0.6        # last season's final rating carried in


def solve(gs, r, h, prior, sweeps=25):
    """gs: [(home, away, market home margin, neutral)]; coordinate descent on the ridge least squares."""
    teams = {}
    for i, (a, b, m, n) in enumerate(gs):
        teams.setdefault(a, []).append(i)
        teams.setdefault(b, []).append(i)
    for _ in range(sweeps):
        for t, idx in teams.items():
            s, w = LAM * prior.get(t, 0.0), LAM
            for i in idx:
                a, b, m, n = gs[i]
                he = 0.0 if n else h
                if t == a:
                    s += m - he + r.get(b, prior.get(b, 0.0))
                else:
                    s += r.get(a, prior.get(a, 0.0)) + he - m
                w += 1
            r[t] = s / w
        res = [(m - (r[a] - r[b])) for a, b, m, n in gs if not n]
        if res:
            h = (sum(res) + 2.5 * 20) / (len(res) + 20)      # home edge, shrunk toward 2.5
    return r, h


def build(lg):
    games = lib.load_football(lg)
    rows = []
    final_prev = {}
    for season in sorted({g["season"] for g in games}):
        sg = [g for g in games if g["season"] == season]
        prior = {t: CARRY * v for t, v in final_prev.items()}
        played, r, h = [], dict(prior), 2.5
        dates = sorted({g["start"][:10] for g in sg})
        di = 0
        for d in dates:
            today = [g for g in sg if g["start"][:10] == d]
            if played:
                r, h = solve(played, r, h, prior, sweeps=8 if di else 25)
            di += 1
            for g in today:
                ff = lib.first_fair(g["sp"])
                nplayed_h = sum(1 for x in played if g["home"] in (x[0], x[1]))
                nplayed_a = sum(1 for x in played if g["away"] in (x[0], x[1]))
                if ff and (nplayed_h + nplayed_a) >= 2:
                    line, hp, ap = lib.sp_med(ff[1])
                    mkt_line = -(r.get(g["home"], prior.get(g["home"], 0.0)) - r.get(g["away"], prior.get(g["away"], 0.0))
                                 + (0.0 if g["neutral"] else h))
                    mlf = lib.first_fair(g["ml"])
                    rows.append({"season": season, "id": g["id"], "line": line, "hp": hp, "ap": ap, "mkt": mkt_line,
                                 "close": g["c_sp"], "margin": g["margin"], "ng": min(nplayed_h, nplayed_a),
                                 "ml": lib.ml_med(mlf[1]) if mlf else None, "month": int(g["start"][5:7])})
            for g in today:
                if g["c_sp"] is not None:
                    played.append((g["home"], g["away"], -g["c_sp"], g["neutral"]))
        r, h = solve(played, r, h, prior, sweeps=25) if played else (r, h)
        final_prev = r
    return rows


def main():
    out, lines = {}, []
    for lg in ("nfl", "ncaaf"):
        rows = build(lg)
        lines.append(f"\n=== {lg.upper()} - {len(rows)} games with a first fair spread and a market rating ===")
        # how good is the market line itself: mean abs error vs the first fair number and vs the close
        errs = [abs(x["mkt"] - x["line"]) for x in rows]
        lines.append(f"market line vs first fair number: mean |gap| {sum(errs)/len(errs):.2f} pts")
        for cut in (1.5, 2.5, 3.5, 5.0):
            for minng in (0, 3):
                cell = [x for x in rows if abs(x["mkt"] - x["line"]) >= cut and x["ng"] >= minng and x["close"] is not None]
                if not cell:
                    continue
                # side the market line favors: home if mkt < line (market says home should lay more / get less)
                toward = sum(1 for x in cell if (x["close"] - x["line"]) * (x["mkt"] - x["line"]) > 0)
                away_ = sum(1 for x in cell if (x["close"] - x["line"]) * (x["mkt"] - x["line"]) < 0)
                ats, mlb_dog, mlb_fav = [], [], []
                for x in cell:
                    home_side = x["mkt"] < x["line"]
                    pts = x["line"] if home_side else -x["line"]
                    mg = x["margin"] if home_side else -x["margin"]
                    if mg + pts != 0:
                        d = x["hp"] if home_side else x["ap"]
                        ats.append((x["season"], lib.profit(mg + pts > 0, d)))
                    if x["ml"]:
                        hd, ad, p = x["ml"]
                        d = hd if home_side else ad
                        won = (x["margin"] > 0) == home_side
                        if 2.0 <= d <= 4.5:
                            mlb_dog.append((x["season"], lib.profit(won, d)))
                        elif 1.6667 <= d < 2.0:
                            mlb_fav.append((x["season"], lib.profit(won, d)))
                tag = f"{lg} gap {cut}+ (both teams {minng}+ games)"
                lines.append(f"{tag}: n {len(cell)}, close moved TOWARD the market line {toward} / away {away_}")
                for nm, b in (("ATS at the first fair number", ats), ("ML dog +100..+350", mlb_dog), ("ML fav -101..-150", mlb_fav)):
                    s = lib.summ(b, TRAIN, HELD)
                    out[f"{tag} {nm}"] = s
                    lines.append(lib.fmt("  " + nm, s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s1_out.txt"), "w").write(txt + "\n")
    json.dump(out, open(os.path.join(lib.OUT, "s1_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
