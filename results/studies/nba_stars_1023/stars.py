"""🌟 THE STAR-POWER STUDY (10/23): do NBA dogs with as many / more stars than the favorite beat their price?
Seasons with box scores (who was on the floor): 2021-22 .. 2026-27. Train 2021-22 + 2022-23, blind 2023-26.
Star values from sports_nba_stars (honors of the seasons BEFORE - never this season's). Flat 1u at the close; the open
where it exists (2023-25). No fit anywhere - fixed hand-set weights, thresholds chosen on train, read on blind.

    python results/studies/nba_stars_1023/stars.py > results/studies/nba_stars_1023/stars.out
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.getcwd())
import sports_data as sd                  # noqa: E402
import sports_roster as sr                # noqa: E402
import sports_nba_stars as ns             # noqa: E402

TRAIN = (2021, 2022)
BLIND = (2023, 2024, 2025, 2026)


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 9 else y - 1


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def main():
    data = ns.load()
    games = sd.load_games("nba")
    rows = sr.load("nba")
    by_gid = defaultdict(lambda: defaultdict(list))      # gid -> team -> [(pid, name, minutes)]
    log = defaultdict(list)                              # pid -> [(start, gid, minutes, points, plus-minus)] in order
    for r in sorted(rows, key=lambda r: (r["start"], r["gid"])):
        try:
            st = json.loads(r["stats"])
            m = float(st.get("minutes") or 0)
            pts = float(st.get("points") or 0)
            pm = float(str(st.get("plusMinus") or "0").replace("+", ""))
        except (ValueError, TypeError):
            m = 0.0
        if m > 0:
            by_gid[r["gid"]][r["team"]].append((r["pid"], r["player"], m))
            log[r["pid"]].append((r["start"], r["gid"], m, pts, pm))

    def form(pid, start):
        """A star's form before tonight: his last 5 games' points a minute vs his baseline (this season's earlier games,
        10+ of them, else last season's) -> 'hot' (+20%), 'cold' (-20%), '' or None (not enough games)."""
        prev = [x for x in log.get(pid, []) if x[0] < start]
        s = season_of(start)
        this = [x for x in prev if season_of(x[0]) == s]
        recent = this[-FORM_N:]
        if len(recent) < FORM_N:
            return None
        base = this[:-FORM_N] if len(this) - FORM_N >= 10 else [x for x in prev if season_of(x[0]) == s - 1]
        if len(base) < 10:
            return None
        rm, bm = sum(x[2] for x in recent), sum(x[2] for x in base)
        if rm < 100 or bm < 300:
            return None
        rr, br = sum(x[3] for x in recent) / rm, sum(x[3] for x in base) / bm
        if br <= 0:
            return None
        return "hot" if rr >= br * (1 + FORM_PCT) else "cold" if rr <= br * (1 - FORM_PCT) else ""
    team_season_pids = defaultdict(set)                  # (team, season) -> every pid who played for it that season
    starts = {g["id"]: g["start"] for g in games.values()}
    for gid, teams in by_gid.items():
        if gid not in starts:
            continue
        s = season_of(starts[gid])
        for t, ps in teams.items():
            team_season_pids[(t, s)].update(p for p, _, _ in ps)
    fin = sorted((g for g in games.values() if g.get("status") == "final" and g.get("stype") == "2"
                  and g["id"] in by_gid and g.get("ml_home") and g.get("ml_away")), key=lambda g: g["start"])
    roster_so_far = defaultdict(dict)                    # (team, season) -> {pid: name} seen so far (before tonight)
    n_games = defaultdict(int)
    sides = []
    for g in fin:
        s = season_of(g["start"])
        if not ns.covered(s, data) and s != 2026:        # (2026-27 kept for the owner's replays - with 2024 / 2025
            continue                                     #  honors only; the 2026 honors wait on the fetch)
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        mh, ma = int(g["ml_home"]), int(g["ml_away"])
        oh, oa = (int(g["ml_home_open"]) if g.get("ml_home_open") else None), (int(g["ml_away_open"]) if g.get("ml_away_open") else None)
        box = by_gid[g["id"]]
        facts = {}
        for side in ("home", "away"):
            t = g[side]
            tonight = [(nm, m) for _, nm, m in box.get(t, [])]
            ros = roster_so_far[(t, s)]
            all_names = set(nm for _, nm, _ in box.get(t, [])) | set(ros.values())
            st_t = ns.team([nm for nm, _ in tonight], s, data)
            st_r = ns.team(list(all_names), s, data)
            last = team_season_pids.get((t, s - 1), set())
            pids_of = defaultdict(set)                   # name -> his pid(s) on this team this season
            for p, n, _ in box.get(t, []):
                pids_of[n].add(p)
            for p, n in ros.items():
                pids_of[n].add(p)
            added = [x for x in st_r["stars"] if not (pids_of.get(x[0], set()) & last)]
            on_names = {nm for nm, _ in tonight}
            star_out = [x[0] for x in st_r["stars"] if x[0] not in on_names]      # a star who played for them this
            fm = defaultdict(int)                                                  # season and isn't in tonight's box
            for x in st_t["stars"]:
                for pid in pids_of.get(x[0], ()):
                    f = form(pid, g["start"])
                    if f:
                        fm[f] += 1
                    break
            facts[side] = dict(team=t, score=st_t["score"], n=st_t["n"], roster_score=st_r["score"], roster_n=st_r["n"],
                               added=len(added), has_last=(t, s - 1) in team_season_pids, g=n_games[(t, s)],
                               stars=[x[0] for x in st_t["stars"]], star_out=len(star_out), hot=fm["hot"], cold=fm["cold"])
        for side, oth in (("home", "away"), ("away", "home")):
            ml = mh if side == "home" else ma
            ml_o = ma if side == "home" else mh
            op = (oh if side == "home" else oa)
            op_o = (oa if side == "home" else oh)
            won = (hs > as_) if side == "home" else (as_ > hs)
            f, o = facts[side], facts[oth]
            sides.append(dict(season=s, gid=g["id"], date=g["start"][:10], side=side, team=g[side + "_name"], opp=g[oth + "_name"],
                              ml=ml, mp=novig(ml, ml_o), op=op, op_mp=(novig(op, op_o) if op and op_o else None),
                              won=won, g=f["g"], score=f["score"], n=f["n"], gap=round(f["score"] - o["score"], 2),
                              n_gap=f["n"] - o["n"], r_gap=round(f["roster_score"] - o["roster_score"], 2),
                              added=f["added"] if f["has_last"] else None, stars=f["stars"], opp_stars=o["stars"],
                              opp_n=o["n"], star_out=f["star_out"], opp_star_out=o["star_out"],
                              hot=f["hot"], cold=f["cold"], opp_hot=o["hot"], opp_cold=o["cold"]))
        for side in ("home", "away"):
            t = g[side]
            for pid, nm, _ in box.get(t, []):
                roster_so_far[(t, s)][pid] = nm
            n_games[(t, s)] += 1
    print(f"sides {len(sides)} seasons {sorted({x['season'] for x in sides})}")
    json.dump(sides, open(os.path.join(os.path.dirname(__file__), "sides.json"), "w"))
    report(sides)
    owner_cuts(sides)
    replay(sides)


FORM_N, FORM_PCT = 5, 0.20


def diff_line(xs, lab):
    for h, ss in (("train", TRAIN), ("blind", BLIND)):
        ys = [x for x in xs if x["season"] in ss]
        if ys:
            w = sum(x["won"] for x in ys) / len(ys)
            e = sum(x["mp"] for x in ys) / len(ys)
            print(f"     {lab} {h}: n {len(ys):5d} won {100 * w:4.1f}% price {100 * e:4.1f}% diff {100 * (w - e):+4.1f}  "
                  f"ROI {100 * sum((dec(x['ml']) - 1) if x['won'] else -1 for x in ys) / len(ys):+5.1f}%")


def owner_cuts(sides):
    dogs = [x for x in sides if 100 <= x["ml"] <= 350]
    favs = [x for x in sides if -150 <= x["ml"] <= -100]
    print("\n=== THE OWNER (10/23 later): (1) STAR COUNT MATCHUPS - 'a team with no All-Stars can't be expected to upset a team of All-Stars' ===")
    cell("dog with 0 stars vs a favorite with 2+ (the dog)", [x for x in dogs if x["n"] == 0 and x["opp_n"] >= 2])
    cell("...the same games, the FAVORITE (any price)", [x for x in sides if x["ml"] < 0 and x["n"] >= 2 and x["opp_n"] == 0])
    cell("...the favorite at -150..-100", [x for x in favs if x["n"] >= 2 and x["opp_n"] == 0])
    cell("...the favorite at -300..-151", [x for x in sides if -300 <= x["ml"] < -150 and x["n"] >= 2 and x["opp_n"] == 0])
    cell("dog with 0 stars vs a favorite with 1+", [x for x in dogs if x["n"] == 0 and x["opp_n"] >= 1])
    cell("dog with 0 stars, any favorite", [x for x in dogs if x["n"] == 0])
    cell("dog with 1+ stars vs a favorite with 0", [x for x in dogs if x["n"] >= 1 and x["opp_n"] == 0])
    cell("dog with 2+ stars vs a favorite with 2+", [x for x in dogs if x["n"] >= 2 and x["opp_n"] >= 2])
    cell("0 stars vs 0 stars (the dog)", [x for x in dogs if x["n"] == 0 and x["opp_n"] == 0])
    print("  does a team with NO stars win less than its price says, whoever it plays?")
    diff_line([x for x in sides if x["n"] == 0], "0-star teams, all prices  ")
    diff_line([x for x in sides if x["n"] == 0 and x["opp_n"] >= 2], "0-star vs 2+ stars        ")
    diff_line([x for x in sides if x["n"] >= 2 and x["opp_n"] == 0], "2+ stars vs 0-star        ")
    diff_line([x for x in sides if x["n"] >= 3], "3+ stars on the floor     ")
    print("\n=== (2) STAR FORM - a star's last 5 games' points a minute vs his own baseline (+/-20% = hot / cold; sports_form's HOT_W found the books OVER-rate a hot key man) ===")
    cell("dog with a HOT star", [x for x in dogs if x["hot"] >= 1])
    cell("dog with a COLD star", [x for x in dogs if x["cold"] >= 1])
    cell("dog vs a favorite with a HOT star", [x for x in dogs if x["opp_hot"] >= 1])
    cell("dog vs a favorite with a COLD star", [x for x in dogs if x["opp_cold"] >= 1])
    cell("favorite -150..-100 with a HOT star", [x for x in favs if x["hot"] >= 1])
    cell("favorite -150..-100 with a COLD star", [x for x in favs if x["cold"] >= 1])
    cell("favorite -150..-100 vs a dog with a HOT star", [x for x in favs if x["opp_hot"] >= 1])
    print("  all prices, win % minus the price:")
    diff_line([x for x in sides if x["hot"] >= 1], "side with a hot star      ")
    diff_line([x for x in sides if x["cold"] >= 1], "side with a cold star     ")
    diff_line([x for x in sides if x["n"] >= 1 and not x["hot"] and not x["cold"]], "stars, none hot or cold   ")
    print("\n=== (3) A STAR OUT TONIGHT (a value-2+ man who played for them this season, not in tonight's box) ===")
    cell("dog missing a star", [x for x in dogs if x["star_out"] >= 1])
    cell("dog vs a favorite missing a star", [x for x in dogs if x["opp_star_out"] >= 1])
    cell("dog vs a favorite missing a star, the dog has all its stars", [x for x in dogs if x["opp_star_out"] >= 1 and x["star_out"] == 0])
    cell("favorite -150..-100 missing a star", [x for x in favs if x["star_out"] >= 1])
    cell("favorite -150..-100 vs a dog missing a star", [x for x in favs if x["opp_star_out"] >= 1])
    cell("favorite past -150 vs a dog missing a star", [x for x in sides if x["ml"] < -150 and x["opp_star_out"] >= 1])
    print("  all prices, win % minus the price:")
    diff_line([x for x in sides if x["star_out"] >= 1], "side missing a star       ")
    diff_line([x for x in sides if x["opp_star_out"] >= 1], "side facing a missing star")
    diff_line([x for x in sides if x["star_out"] >= 2], "side missing 2+ stars     ")


def roi(xs, price="ml"):
    n = len(xs)
    if not n:
        return "n 0"
    u = sum((dec(x[price]) - 1) if x["won"] else -1 for x in xs)
    w = sum(1 for x in xs if x["won"])
    exp = sum(x["mp" if price == "ml" else "op_mp"] for x in xs) / n
    return f"n {n:4d} {w}-{n - w} {100 * w / n:4.1f}% (price said {100 * exp:4.1f}%) ROI {100 * u / n:+5.1f}% {u:+.1f}u"


def seasons_line(xs, price="ml"):
    out = []
    for s in sorted({x["season"] for x in xs}):
        ys = [x for x in xs if x["season"] == s]
        u = sum((dec(x[price]) - 1) if x["won"] else -1 for x in ys)
        out.append(f"{s}: {len(ys)} {100 * u / len(ys):+.0f}%")
    return " | ".join(out)


def cell(name, xs, price="ml"):
    tr = [x for x in xs if x["season"] in TRAIN]
    bl = [x for x in xs if x["season"] in BLIND]
    print(f"  {name}")
    print(f"     train {roi(tr, price)}")
    print(f"     blind {roi(bl, price)}   {seasons_line(bl, price)}")


def report(sides):
    dogs = [x for x in sides if 100 <= x["ml"] <= 350]
    print("\n=== DOGS +100..+350 at the close, flat 1u (the baseline = every dog in the band) ===")
    cell("all dogs", dogs)
    for lo, hi in ((100, 150), (150, 250), (250, 350)):
        cell(f"band +{lo}..+{hi}", [x for x in dogs if lo <= x["ml"] <= hi])
    print("\n--- star gap (dog's score on the floor tonight minus the favorite's) ---")
    for th in (0, 2, 4, 6, 8):
        cell(f"gap >= {th}", [x for x in dogs if x["gap"] >= th])
    cell("gap <= -4 (the favorite has the stars - the fade?)", [x for x in dogs if x["gap"] <= -4])
    cell("gap <= -8", [x for x in dogs if x["gap"] <= -8])
    print("\n--- star COUNT gap (All-Star-level men, value 2+) ---")
    for th in (0, 1, 2):
        cell(f"as many or more stars by {th}+ (n_gap >= {th})", [x for x in dogs if x["n_gap"] >= th])
    cell("dog has 2+ stars, the favorite none", [x for x in dogs if x["n"] >= 2 and x["n"] - x["n_gap"] == 0])
    cell("dog has 3+ stars on the floor", [x for x in dogs if x["n"] >= 3])
    print("\n--- the whole roster so far (men out tonight count too - no 'who played' look-ahead) ---")
    for th in (0, 2, 4):
        cell(f"roster gap >= {th}", [x for x in dogs if x["r_gap"] >= th])
    print("\n--- a dog that ADDED stars in the offseason (value-2+ men not on last season's team) ---")
    for th in (1, 2):
        cell(f"added >= {th}", [x for x in dogs if (x["added"] or 0) >= th])
    cell("added >= 2 AND gap >= 0", [x for x in dogs if (x["added"] or 0) >= 2 and x["gap"] >= 0])
    print("\n--- early season (team games 1-20) vs the rest ---")
    for th in (0, 2, 4):
        cell(f"games 1-20, gap >= {th}", [x for x in dogs if x["g"] < 20 and x["gap"] >= th])
        cell(f"games 21+, gap >= {th}", [x for x in dogs if x["g"] >= 20 and x["gap"] >= th])
    cell("games 1-10, gap >= 2", [x for x in dogs if x["g"] < 10 and x["gap"] >= 2])
    cell("games 1-20, added >= 2", [x for x in dogs if x["g"] < 20 and (x["added"] or 0) >= 2])
    print("\n--- by price band, gap >= 2 ---")
    for lo, hi in ((100, 150), (150, 250), (250, 350)):
        cell(f"+{lo}..+{hi} gap >= 2", [x for x in dogs if lo <= x["ml"] <= hi and x["gap"] >= 2])
    print("\n=== AT THE OPENING LINE (2023-25 hold an open; the side a dog +100..+350 at the open) ===")
    od = [x for x in sides if x["op"] and x["op_mp"] and 100 <= x["op"] <= 350]
    cell("all open dogs", od, "op")
    print("  (gap = who PLAYED tonight: the open can't know who sits - a LEAK of game-day news; roster gap = every man "
          "on the roster so far, out or not - the honest open read)")
    for th in (0, 2, 4):
        cell(f"open, gap >= {th} (leaky)", [x for x in od if x["gap"] >= th], "op")
        cell(f"open, ROSTER gap >= {th} (honest)", [x for x in od if x["r_gap"] >= th], "op")
        xs = [x for x in od if x["r_gap"] >= th]
        print(f"     ...the same sides graded at the CLOSE: {roi([x for x in xs if 100 <= x['ml'] <= 350])}")
        if xs:
            print(f"     ...their open no-vig {100 * sum(x['op_mp'] for x in xs) / len(xs):.1f}% -> close {100 * sum(x['mp'] for x in xs) / len(xs):.1f}%")
    cell("open, ROSTER gap >= 2, games 1-20", [x for x in od if x["g"] < 20 and x["r_gap"] >= 2], "op")
    cell("open, ROSTER gap >= 2, games 21+", [x for x in od if x["g"] >= 20 and x["r_gap"] >= 2], "op")
    cell("open, ROSTER gap <= -4 (the favorite's stars)", [x for x in od if x["r_gap"] <= -4], "op")
    print("  open, ROSTER gap >= 2 by open price band:")
    for lo, hi in ((100, 150), (150, 250), (250, 350)):
        cell(f"   +{lo}..+{hi}", [x for x in od if lo <= x["op"] <= hi and x["r_gap"] >= 2], "op")
    of = [x for x in sides if x["op"] and x["op_mp"] and -150 <= x["op"] <= -100]
    cell("open favorites -150..-100, all", of, "op")
    cell("open favorites -150..-100, ROSTER gap >= 4", [x for x in of if x["r_gap"] >= 4], "op")
    cell("open favorites -150..-100, ROSTER gap <= -2", [x for x in of if x["r_gap"] <= -2], "op")
    print("\n=== FAVORITES -150..-100 with the star edge ===")
    favs = [x for x in sides if -150 <= x["ml"] <= -100]
    cell("all favorites -150..-100", favs)
    for th in (4, 6, 8):
        cell(f"favorite gap >= {th}", [x for x in favs if x["gap"] >= th])
    cell("favorite n_gap >= 2", [x for x in favs if x["n_gap"] >= 2])
    cell("favorite gap <= -2 (the dog has more stars)", [x for x in favs if x["gap"] <= -2])
    big = [x for x in sides if x["ml"] < -150]
    cell("favorites past -150, gap >= 6", [x for x in big if x["gap"] >= 6])
    print("\n=== win % minus the price, all sides, by star gap bucket (does the market price the stars?) ===")
    for lo, hi in ((-99, -8), (-8, -4), (-4, -1), (-1, 1), (1, 4), (4, 8), (8, 99)):
        xs = [x for x in sides if lo <= x["gap"] < hi]
        for lab, ss in (("train", TRAIN), ("blind", BLIND)):
            ys = [x for x in xs if x["season"] in ss]
            if ys:
                w = sum(x["won"] for x in ys) / len(ys)
                e = sum(x["mp"] for x in ys) / len(ys)
                print(f"  gap [{lo:3d},{hi:3d}) {lab}: n {len(ys):5d} won {100 * w:4.1f}% price {100 * e:4.1f}% diff {100 * (w - e):+4.1f}")


def replay(sides):
    print("\n=== THE OWNER'S THREE GAMES (2026-27; honors through 2025 only - the 2025-26 All-Stars / All-NBA wait on the fetch) ===")
    want = {("nba:401909089", "away"), ("nba:401909090", "home"), ("nba:401909840", "away")}
    for x in sides:
        if (x["gid"], x["side"]) in want:
            print(f"  {x['date']} {x['team']} {x['ml']:+d} (open {x['op']}) at/vs {x['opp']}: star score gap {x['gap']:+.1f} "
                  f"(stars {x['n']} vs {x['n'] - x['n_gap']}), roster gap {x['r_gap']:+.1f}, added {x['added']}, "
                  f"{'WON' if x['won'] else 'lost'}\n     theirs: {x['stars']}\n     other side: {x['opp_stars']}")


if __name__ == "__main__":
    main()
