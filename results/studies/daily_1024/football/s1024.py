"""10/24 daily run - 5 new football studies (NFL + college). Read-only on the worktree.
S1 dog's defense trend (points allowed last 3 vs its own season-to-date before that)
S2 big favorite's close escape last game (won by <=3 or lost as a 10+ college / 7+ NFL spread favorite)
S3 the ground game: dog out-rushes (season rush-yard margin per game, box scores 2021-26) the favorite
S4 first time a dog this season (favored in every one of its 3+ priced games before) / first time a favorite
S5 college neutral-site regular-season games (not bowls / title games), dogs by price
Primary price: the closing moneyline / spread from the game files (2018-26). Second check: the median FAIR look
1.5-7.5 days out from the paid odds history (2020-25), early_football_study.fair (no look-ahead).
Train 2018-24, holdout 2025, current 2026."""
import sys, os, gzip, csv, json, math, statistics, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt/results/studies/daily_1023/football")
import lib  # noqa: E402  (chdirs to the worktree)
from lib import sd, sm, dec, season, num  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
lib.OUT = OUT  # cache here, never in the repo
TRAIN = (2018, 2024)


def ml_profit(won, am):
    return (dec(am) - 1) if won else -1.0


def summ(bets):
    """bets [(season, profit)]"""
    def s(bs):
        if not bs:
            return None
        p = [b[1] for b in bs]; n = len(p); m = sum(p) / n
        sdv = statistics.pstdev(p) if n > 1 else 1
        return {"n": n, "win": sum(1 for x in p if x > 0) / n, "roi": m, "z": m / (sdv / math.sqrt(n)) if sdv else 0}
    by = collections.defaultdict(list)
    for se, pr in bets:
        by[se].append((se, pr))
    seas = {k: s(v) for k, v in sorted(by.items())}
    return {"all": s(bets), "train": s([b for b in bets if TRAIN[0] <= b[0] <= TRAIN[1]]),
            "hold": s(by.get(2025, [])), "cur": s(by.get(2026, [])),
            "seasons": {k: (v["n"], round(v["roi"] * 100)) for k, v in seas.items()},
            "up": f"{sum(1 for k, v in seas.items() if v['roi'] > 0 and k <= 2024)}/{sum(1 for k in seas if k <= 2024)}",
            "up3": f"{sum(1 for k, v in seas.items() if v['roi'] > 0 and 2023 <= k)}/{sum(1 for k in seas if k >= 2023)}"}


def fmt(name, r):
    if not r or not r["all"]:
        return f"  {name:60s} -"
    f = lambda x: f"{x['n']}/{x['roi']:+.1%}" if x else "-"
    a = r["all"]
    return (f"  {name:60s} n {a['n']:4d} win {a['win']:.1%} ROI {a['roi']:+.1%} z {a['z']:+.1f} | train {f(r['train'])}"
            f" | hold25 {f(r['hold'])} | 2026 {f(r['cur'])} | up(train) {r['up']} 2023+ {r['up3']} {r['seasons']}")


CELLS = []


def report(lines, name, bets, base=None):
    r = summ(bets)
    CELLS.append((name, r))
    lines.append(fmt(name, r))
    if base is not None:
        lines.append(fmt("    baseline same league/price band", summ(base)))


def early_prices(lg):
    """{game id: (home dec, away dec)} the median FAIR look 1.5..7.5 days out (first such look)."""
    res = {}
    for r in lib.load(lg):
        early = [x for x in r["ml"] if 1.5 <= x[0] < 7.5]
        if early:
            h, a, _ = lib.ml_med(early[0][1])
            res[r["id"]] = (h, a)
    return res


def rush_box(lg):
    """{(gid, team): rushing yards}"""
    out = collections.Counter()
    for y in range(2021, 2027):
        p = os.path.join(sd.DATA, "roster", f"{lg}_{y}.csv.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rt") as f:
            for row in csv.DictReader(f):
                if row["group"] != "rushing":
                    continue
                try:
                    out[(row["gid"], row["team"])] += float(json.loads(row["stats"]).get("rushingYards") or 0)
                except (ValueError, json.JSONDecodeError):
                    pass
    return out


def run(lg, lines):
    games = sd.load_games(lg)
    fin = [g for g in sm.finals(games, lg) if (g.get("stype") or "2") == "2"]
    fin.sort(key=lambda g: g["start"])
    try:
        early = early_prices(lg)
    except Exception as e:  # noqa
        print("early load failed", e); early = {}
    rush = rush_box(lg)
    hist = collections.defaultdict(list)   # (season, team) -> list of dicts (prior games)
    big = 10 if lg == "ncaaf" else 7
    S = collections.defaultdict(list)       # cell -> [(season, profit)]
    E = collections.defaultdict(list)       # cell -> early-price bets
    BASE = collections.defaultdict(list)
    for g in fin:
        se = season(g["start"])
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        mh, ma, sp = num(g.get("ml_home")), num(g.get("ml_away")), num(g.get("spread_home"))
        neutral = str(g.get("neutral")) == "1"
        month = int(g["start"][5:7])
        priced = mh is not None and ma is not None and abs(mh) >= 100 and abs(ma) >= 100
        if priced and se >= 2018 and hs != as_:
            for side, opp, am, oam, won, sgn in (("h", "a", mh, ma, hs > as_, 1), ("a", "h", ma, mh, as_ > hs, -1)):
                if not (100 <= am <= 350 and oam < 0):
                    continue
                dog = g["home"] if side == "h" else g["away"]
                fav = g["away"] if side == "h" else g["home"]
                p = ml_profit(won, am)
                band = "100-175" if am < 175 else ("175-250" if am < 250 else "250-350")
                ep = early.get(g["id"])
                epp = None
                if ep:
                    d = ep[0] if side == "h" else ep[1]
                    if 2.0 <= d <= 4.5:
                        epp = (d - 1) if won else -1.0
                # ATS for the dog at the close
                ats = None
                if sp is not None:
                    pts = sp if side == "h" else -sp
                    m = (hs - as_) * sgn + pts
                    if m != 0:
                        ats = (dec(-110) - 1) if m > 0 else -1.0
                BASE[band].append((se, p)); BASE["all"].append((se, p))
                dh, fh = hist[(se, dog)], hist[(se, fav)]

                def add(cell, extra_ats=True):
                    S[cell].append((se, p))
                    if epp is not None:
                        E[cell].append((se, epp))
                    if extra_ats and ats is not None:
                        S[cell + " [ATS]"].append((se, ats))

                # S1 defense trend
                if len(dh) >= 5:
                    prior = [x["pa"] for x in dh[:-3]]; last3 = [x["pa"] for x in dh[-3:]]
                    dlt = statistics.mean(last3) - statistics.mean(prior)
                    if dlt <= -7: add("S1 dog D improving 7+ (last3 vs before)")
                    if dlt <= -10: add("S1 dog D improving 10+")
                    if dlt >= 7: add("S1 dog D getting worse 7+")
                    if len(fh) >= 5:
                        fd = statistics.mean(x["pa"] for x in fh[-3:]) - statistics.mean(x["pa"] for x in fh[:-3])
                        if dlt <= -7 and fd >= 7: add("S1 dog D improving 7+ AND fav D worse 7+")
                # S2 close escape: the favorite (the team the dog faces) escaped last game
                if fh and fh[-1]["sp"] is not None and fh[-1]["sp"] <= -big:
                    if fh[-1]["mg"] <= 3: add(f"S2 fav off a close escape/loss as {big}+ fav (back the dog)")
                    if 0 < fh[-1]["mg"] <= 3: add(f"S2 fav off a WIN by 1-3 as {big}+ fav (back the dog)")
                if dh and dh[-1]["sp"] is not None and dh[-1]["sp"] <= -big and dh[-1]["mg"] <= 3:
                    add(f"S2 DOG itself off a close escape/loss as {big}+ fav")
                # S3 ground game (box seasons only)
                if se >= 2021:
                    dr = [x["rm"] for x in dh if x["rm"] is not None]
                    fr = [x["rm"] for x in fh if x["rm"] is not None]
                    if len(dr) >= 3 and len(fr) >= 3:
                        gap = statistics.mean(dr) - statistics.mean(fr)
                        if gap >= 50: add("S3 dog's rush margin/gm 50+ better than fav's")
                        if gap >= 100: add("S3 dog's rush margin/gm 100+ better")
                        if gap <= -100: add("S3 dog's rush margin/gm 100+ worse")
                # S4 first time a dog
                pr = [x for x in dh if x["am"] is not None]
                if len(pr) >= 3 and all(x["am"] < 0 for x in pr):
                    add("S4 dog favored in all 3+ prior priced games (first time a dog)")
                    if len(pr) >= 5: add("S4 first time a dog, 5+ games in")
                fpr = [x for x in fh if x["am"] is not None]
                if len(fpr) >= 3 and all(x["am"] > 0 for x in fpr):
                    add("S4 fav was a dog in all 3+ prior (first time a fav) - back the dog")
                # S5 neutral site, college regular season Sep-Nov
                if lg == "ncaaf" and neutral and 8 <= month <= 11:
                    add("S5 college neutral-site reg-season dog")
                    add(f"S5 neutral dog {band}")
                    if month <= 9: add("S5 neutral dog Aug/Sep (kickoff games)")
                    else: add("S5 neutral dog Oct/Nov")
                if lg == "ncaaf" and not neutral and 8 <= month <= 11:
                    S["S5 [control] non-neutral reg-season dog"].append((se, p))
            # S2 / S4 from the favorite's side: does the escaped favorite cover / win at -101..-350?
        # update histories
        for side, team, opp in (("h", g["home"], g["away"]), ("a", g["away"], g["home"])):
            mg = (hs - as_) if side == "h" else (as_ - hs)
            pa = as_ if side == "h" else hs
            am = (mh if side == "h" else ma) if priced else None
            tsp = None if sp is None else (sp if side == "h" else -sp)
            rm = None
            if (g["id"], team) in rush and (g["id"], opp) in rush:
                rm = rush[(g["id"], team)] - rush[(g["id"], opp)]
            hist[(se, team)].append({"mg": mg, "pa": pa, "am": am, "sp": tsp, "rm": rm})
    lines.append(f"\n=== {lg.upper()} (dogs +100..+350 vs a favorite, closing ML; [ATS] = the dog's closing spread at -110) ===")
    for band in ("all", "100-175", "175-250", "250-350"):
        lines.append(fmt(f"BASELINE all dogs {band}", summ(BASE[band])))
    for cell in sorted(S):
        report(lines, f"{lg} {cell}", S[cell])
        if cell in E:
            lines.append(fmt(f"    early fair-look price (2020-25), same bets", summ(E[cell])))


def main():
    lines = [__doc__]
    for lg in ("nfl", "ncaaf"):
        run(lg, lines)
    # multiple testing
    ml_cells = [c for c in CELLS if "[ATS]" not in c[0] and "control" not in c[0]]
    lines.append(f"\nCells: {len(CELLS)} ({len(ml_cells)} moneyline). Expected chance 'up train AND holdout': ~{len(CELLS)//4}"
                 f" (a coin flip each half); expected |z|>2 by chance ~{max(1, round(len(CELLS)*0.05))}.")
    surv = [n for n, r in CELLS if r and r["train"] and r["hold"] and r["train"]["roi"] > 0 and r["hold"]["roi"] > 0
            and r["all"]["z"] > 1]
    lines.append("Up in train AND holdout with z>1: " + (", ".join(surv) or "none"))
    txt = "\n".join(lines)
    open(os.path.join(OUT, "s1024_out.txt"), "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
