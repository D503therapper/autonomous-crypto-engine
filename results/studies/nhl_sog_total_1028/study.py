"""NHL totals: shots on goal x (1 - opposing goalie's save %) projection vs the closing total.
Walk-forward: every input from games BEFORE the game's date. Run from the repo root."""
import csv, glob, sys, collections, statistics
from collections import defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y + (1 if m >= 9 else 0)

# ---- goalie box rows: per gid, per team -> [(goalie, sa, ga)]
box = defaultdict(lambda: defaultdict(list))
for r in csv.DictReader(open(f"{ROOT}/data/sports/players/nhl.csv")):
    if r["role"] != "G": continue
    try: sa, ga = float(r["sa"] or 0), float(r["ga"] or 0)
    except ValueError: continue
    box[r["gid"]][r["team"]].append((r["player"], sa, ga))

# ---- games
games = []
for f in sorted(glob.glob(f"{ROOT}/data/sports/games/nhl/*.csv")):
    for r in csv.DictReader(open(f)):
        if r["status"] != "final" or r.get("stype") != "2": continue
        if r["id"] not in box: continue
        games.append(r)
games.sort(key=lambda r: r["start"])
print("regular-season finals with goalie box:", len(games))

def payout(odds, won):
    if odds is None: return 0.0
    if not won: return -1.0
    return odds / 100.0 if odds > 0 else 100.0 / -odds

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

# ---- walk forward
class Team:
    def __init__(s): s.sf = []; s.sa = []; s.last_goalie = None; s.n = 0
team = {}            # (season, team) -> Team
goalie = defaultdict(lambda: {"sa": 0.0, "sv": 0.0, "n": 0, "hist": []})   # name -> career to date; hist of (season, sa, sv)
league = defaultdict(lambda: [0.0, 0.0])   # season -> [sa, saves]
league_goals = defaultdict(list)           # season -> total goals per game
rows = []

def gl_pct(name, mode, season):
    g = goalie.get(name)
    la = league[season]; lp = la[1] / la[0] if la[0] > 500 else (league[season - 1][1] / league[season - 1][0] if league[season - 1][0] > 500 else 0.905)
    if g is None: return None, lp
    if mode == "season":            # season to date, raw (the video)
        sa = sum(x[1] for x in g["hist"] if x[0] == season); sv = sum(x[2] for x in g["hist"] if x[0] == season)
        return ((sv / sa) if sa > 0 else None), lp
    if mode == "season_min3":
        st = [x for x in g["hist"] if x[0] == season]
        sa = sum(x[1] for x in st); sv = sum(x[2] for x in st)
        return ((sv / sa) if len(st) >= 3 else None), lp
    if mode == "reg2":              # this + last season, regressed 500 shots to the league avg
        st = [x for x in g["hist"] if x[0] >= season - 1]
        sa = sum(x[1] for x in st); sv = sum(x[2] for x in st)
        return (sv + lp * 500) / (sa + 500), lp
    if mode == "reg_career":
        return (g["sv"] + lp * 500) / (g["sa"] + 500), lp
    raise ValueError(mode)

for r in games:
    gid, s = r["id"], season_of(r["start"])
    h, a = r["home"], r["away"]
    th = team.setdefault((s, h), Team()); ta = team.setdefault((s, a), Team())
    bh, ba = box[gid].get(h, []), box[gid].get(a, [])
    # team shots for = shots the OPPONENT's goalies faced; shots against = own goalies' sa
    h_sf = sum(x[1] for x in ba); a_sf = sum(x[1] for x in bh)
    actual_h = max(bh, key=lambda x: x[1])[0] if bh else None
    actual_a = max(ba, key=lambda x: x[1])[0] if ba else None
    total = num(r.get("total")); oo = num(r.get("over_odds")); uo = num(r.get("under_odds"))
    hs, as_ = num(r["home_score"]), num(r["away_score"])
    if total is not None and hs is not None and th.n >= 1 and ta.n >= 1:
        row = {"gid": gid, "season": s, "total": total, "oo": oo, "uo": uo, "pts": hs + as_,
               "h_n": th.n, "a_n": ta.n,
               "h_sf": statistics.mean(th.sf), "a_sf": statistics.mean(ta.sf),
               "h_sa": statistics.mean(th.sa), "a_sa": statistics.mean(ta.sa),
               "lg_goals": statistics.mean(league_goals[s]) if len(league_goals[s]) >= 30 else (statistics.mean(league_goals[s - 1]) if league_goals[s - 1] else 6.0)}
        for tag, gh, ga_ in (("prob", r.get("sp_home") or None, r.get("sp_away") or None),
                             ("last", th.last_goalie, ta.last_goalie),
                             ("actual", actual_h, actual_a)):
            for mode in ("season", "season_min3", "reg2", "reg_career"):
                ph, lp = gl_pct(gh, mode, s) if gh else (None, gl_pct("", mode, s)[1])
                pa, _ = gl_pct(ga_, mode, s) if ga_ else (None, lp)
                row[f"{tag}_{mode}_h"] = ph; row[f"{tag}_{mode}_a"] = pa
            row["lp"] = lp
        rows.append(row)
    # ---- update state (after the game)
    th.sf.append(h_sf); th.sa.append(a_sf); ta.sf.append(a_sf); ta.sa.append(h_sf); th.n += 1; ta.n += 1
    th.last_goalie, ta.last_goalie = actual_h, actual_a
    for tm in (bh, ba):
        for name, sa, ga in tm:
            g = goalie[name]; g["sa"] += sa; g["sv"] += sa - ga; g["n"] += 1; g["hist"].append((s, sa, sa - ga))
            league[s][0] += sa; league[s][1] += sa - ga
    if hs is not None: league_goals[s].append(hs + as_)

print("rows with a total and both teams' prior games:", len(rows))
seasons = sorted({r["season"] for r in rows})
print("seasons:", seasons)

# ---- projections
def project(r, shots, gtag, gmode, min_games=5, fallback=True, bias=0.0):
    if r["h_n"] < min_games or r["a_n"] < min_games: return None
    ph, pa = r.get(f"{gtag}_{gmode}_h"), r.get(f"{gtag}_{gmode}_a")
    if ph is None or pa is None:
        if not fallback: return None
        ph = ph if ph is not None else r["lp"]; pa = pa if pa is not None else r["lp"]
    if shots == "for":
        hsh, ash = r["h_sf"], r["a_sf"]
    elif shots == "blend":
        hsh, ash = (r["h_sf"] + r["a_sa"]) / 2, (r["a_sf"] + r["h_sa"]) / 2
    else: raise ValueError
    return hsh * (1 - pa) + ash * (1 - ph) + bias

def grade(rows_, fn, thr, train_seasons):
    out = defaultdict(lambda: {"n": 0, "w": 0, "l": 0, "p": 0, "u": 0.0, "over": 0})
    for r in rows_:
        pr = fn(r)
        if pr is None: continue
        d = pr - r["total"]
        if abs(d) < thr: continue
        over = d > 0
        if r["pts"] == r["total"]:
            res = "p"; pay = 0.0
        else:
            won = (r["pts"] > r["total"]) == over
            res = "w" if won else "l"; pay = payout(r["oo"] if over else r["uo"], won)
        c = out[r["season"]]; c["n"] += 1; c[res] += 1; c["u"] += pay; c["over"] += over
    return out

def summarize(out, train):
    def agg(ss):
        n = sum(out[s]["n"] for s in ss); w = sum(out[s]["w"] for s in ss); l = sum(out[s]["l"] for s in ss)
        p = sum(out[s]["p"] for s in ss); u = sum(out[s]["u"] for s in ss); ov = sum(out[s]["over"] for s in ss)
        return n, w, l, p, u, (u / n * 100 if n else 0), ov
    tr = [s for s in out if s in train]; ho = [s for s in out if s not in train]
    up_tr = sum(1 for s in tr if out[s]["u"] > 0); up_ho = sum(1 for s in ho if out[s]["u"] > 0)
    return agg(tr), agg(ho), f"{up_tr}/{len(tr)}", f"{up_ho}/{len(ho)}", agg(list(out))

TRAIN = {s for s in seasons if s <= 2023}
print("train seasons", sorted(TRAIN), "held-out", [s for s in seasons if s not in TRAIN])

# bias of the raw projection on TRAIN (the video's version ignores empty-net goals etc.)
def bias_of(shots, gtag, gmode):
    ds = [project(r, shots, gtag, gmode) - r["pts"] for r in rows if r["season"] in TRAIN and project(r, shots, gtag, gmode) is not None]
    dt = [project(r, shots, gtag, gmode) - r["total"] for r in rows if r["season"] in TRAIN and project(r, shots, gtag, gmode) is not None]
    return statistics.mean(ds), statistics.mean(dt), len(ds)

def fmt(a):
    n, w, l, p, u, roi, ov = a
    return f"n={n:4d} {w}-{l}-{p} {u:+7.1f}u {roi:+5.1f}% (over {ov})"

VERSIONS = [
    ("V1 video: SOG for x opp PROBABLE goalie season sv%", "for", "prob", "season"),
    ("V1b video, LAST-START goalie season sv%", "for", "last", "season"),
    ("V1c video, ACTUAL starter (look-ahead upper bound)", "for", "actual", "season"),
    ("V2 blend shots (for + opp against) x probable season sv%", "blend", "prob", "season"),
    ("V3 SOG for x probable goalie sv% 2-season regressed 500", "for", "prob", "reg2"),
    ("V4 blend shots x probable regressed 2-season", "blend", "prob", "reg2"),
    ("V4b blend shots x last-start regressed 2-season", "blend", "last", "reg2"),
    ("V4c blend shots x actual regressed 2-season (look-ahead)", "blend", "actual", "reg2"),
    ("V5 blend shots x probable career-regressed", "blend", "prob", "reg_career"),
]
cells = 0
for name, shots, gtag, gmode in VERSIONS:
    b_pts, b_tot, nb = bias_of(shots, gtag, gmode)
    print(f"\n=== {name}\n    train bias: proj - actual goals {b_pts:+.2f}, proj - book total {b_tot:+.2f} (n {nb})")
    for adj_name, bias in (("raw", 0.0), ("bias-fixed(train)", -b_tot)):
        for thr in (0.25, 0.5, 0.75, 1.0):
            fn = lambda r, shots=shots, gtag=gtag, gmode=gmode, bias=bias: project(r, shots, gtag, gmode, bias=bias)
            out = grade(rows, fn, thr, TRAIN); cells += 1
            tr, ho, utr, uho, al = summarize(out, TRAIN)
            print(f"  {adj_name:18s} thr {thr:4.2f}: TRAIN {fmt(tr)} up {utr} | HELD-OUT {fmt(ho)} up {uho}")
            if thr == 0.5:
                print("      by season:", " ".join(f"{s}:{out[s]['w']}-{out[s]['l']} {out[s]['u']/out[s]['n']*100 if out[s]['n'] else 0:+.0f}%" for s in sorted(out)))
print("\ncells graded:", cells)

# ---- over vs under split and the market's own baseline
print("\nBaseline: every game over / under at the close")
for side in ("over", "under"):
    out = defaultdict(lambda: [0, 0.0])
    for r in rows:
        if r["pts"] == r["total"]: continue
        won = (r["pts"] > r["total"]) if side == "over" else (r["pts"] < r["total"])
        out[r["season"]][0] += 1; out[r["season"]][1] += payout(r["oo"] if side == "over" else r["uo"], won)
    print(" ", side, " ".join(f"{s}:{out[s][1]/out[s][0]*100:+.1f}%(n{out[s][0]})" for s in sorted(out)))

# ---- does the projection carry info the total lacks? correlation of (proj - total) with (pts - total), by season
print("\nSignal check: corr(proj - total, actual - total) by season, V4 blend/probable/reg2 bias-fixed")
b = bias_of("blend", "prob", "reg2")[1]
for s in seasons:
    xs, ys = [], []
    for r in rows:
        if r["season"] != s: continue
        p = project(r, "blend", "prob", "reg2", bias=-b)
        if p is None: continue
        xs.append(p - r["total"]); ys.append(r["pts"] - r["total"])
    if len(xs) > 50:
        mx, my = statistics.mean(xs), statistics.mean(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
        print(f"  {s}: n {len(xs)} corr {cov / (vx * vy) ** 0.5:+.3f}  sd(proj-total) {(vx/len(xs))**0.5:.2f}")
