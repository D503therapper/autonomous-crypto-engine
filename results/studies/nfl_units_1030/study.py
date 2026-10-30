"""10/30 NFL UNIT-PLAY STUDIES (three): 1. the NFL Lock (which -101..-150 favorites earn, sized), 2. the early-week
number (the same sides at the first fair look), 3. the fresh QB change (box scores say who played) vs the price.
Train 2020-23 / held out 2024-26. Every cell: n, won %, ROI at our price, z (vs break-even), by season."""
import csv, gzip, json, os, pickle, sys, math, statistics
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))   # the repo root
from collections import defaultdict
from datetime import datetime, timedelta
sys.path.insert(0, REPO)
import sports_roster as sr

HERE = os.path.dirname(os.path.abspath(__file__))
rows = pickle.load(open(os.path.join(HERE, "rows.pkl"), "rb"))
TRAIN = (2020, 2021, 2022, 2023)
HOLD = (2024, 2025, 2026)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def grade(picks, label=""):
    """picks: [(row, american price)] -> one line."""
    if not picks:
        return f"{label:58} n 0"
    n = len(picks)
    rets = [(dec(o) - 1) if r["won"] else -1 for r, o in picks]
    roi = sum(rets) / n
    sd_ = statistics.pstdev(rets) if n > 1 else 1
    z = roi / (sd_ / math.sqrt(n)) if sd_ else 0
    won = sum(r["won"] for r, _ in picks) / n
    said = sum(1 / dec(o) for _, o in picks) / n
    by = defaultdict(list)
    for (r, o), x in zip(picks, rets):
        by[r["season"]].append(x)
    seas = " ".join(f"{s % 100}:{sum(v) / len(v):+.0%}/{len(v)}" for s, v in sorted(by.items()))
    up = sum(1 for v in by.values() if sum(v) > 0)
    return f"{label:58} n {n:4} won {won:.1%} (said {said:.1%}) ROI {roi:+.1%} z {z:+.1f} up {up}/{len(by)} | {seas}"


def split(sel, label, price=lambda r: r["close"]):
    tr = [(r, price(r)) for r in rows if r["season"] in TRAIN and sel(r)]
    ho = [(r, price(r)) for r in rows if r["season"] in HOLD and sel(r)]
    print(grade(tr, label + " [train]"))
    print(grade(ho, label + " [hold]"))


def fav_band(r, lo=-150, hi=-101):
    return lo <= r["close"] <= hi


def own_over(r, read="own"):
    return r["mkt_close"] is not None and r[read] >= r["mkt_close"]


def own_edge(r, read="own"):
    return r[read] * dec(r["close"]) - 1


print("=" * 100)
print("STUDY 1 - THE NFL LOCK AT THE CLOSE (favorites -101..-150; blend = the engine's blended win %, own = its ratings read)")
print("=" * 100)
split(lambda r: fav_band(r), "band -101..-150, every favorite")
split(lambda r: fav_band(r) and r["blend"] >= 0.56, "blend 56%+ (lock_ok)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r), "blend 56%+ AND own over the price (today's Lock)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and not own_over(r), "blend 56%+, own UNDER the price (no Lock)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and own_edge(r) >= 0.03, "...own edge 3%+ (the non-thin Lock)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and own_edge(r) < 0.03, "...own edge under 3% (thin)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and -119 <= r["close"] <= -101, "...at -119..-101 (S6_LOCK_SKIP)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and -150 <= r["close"] <= -120, "...at -150..-120")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["own"] >= 0.56, "...own read itself 56%+")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["own"] >= 0.60, "...own read itself 60%+")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["own"] < 0.56, "...own read under 56%")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["home"], "...home favorite")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and not r["home"], "...road favorite")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and own_over(r, "own_blind"), "...own_blind (no injuries) over too")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and not own_over(r, "own_blind"), "...own over only because of injuries")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and (r["inj"] or 0) > 0, "...the opponent is the banged-up one (inj>0)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and (r["inj"] or 0) < 0, "...we are the banged-up one (inj<0)")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["spread"] is not None and r["spread"] <= -3, "...laying 3+")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["spread"] is not None and r["spread"] > -3, "...laying under 3")
for gap in (0.02, 0.04, 0.06, 0.08):
    split(lambda r, g=gap: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["own"] - r["mkt_close"] >= g, f"...own read {gap:.0%}+ over the no-vig close")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["rest"] and r["orest"] and r["rest"] >= 13, "...off a bye")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["orest"] and r["orest"] >= 13, "...opponent off a bye")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["last_margin"] is not None and r["last_margin"] < 0, "...off a loss")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["last_margin"] is not None and r["last_margin"] > 0, "...off a win")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["month"] in (9,), "...September")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["month"] in (10, 11), "...Oct-Nov")
split(lambda r: fav_band(r) and r["blend"] >= 0.56 and own_over(r) and r["month"] in (12, 1, 2), "...Dec+")
print()
print("Bigger favorites the Lock never takes (for the size question):")
split(lambda r: -200 <= r["close"] <= -151 and r["blend"] >= 0.56 and own_over(r), "-151..-200, blend 56%+, own over")
split(lambda r: -300 <= r["close"] <= -201 and own_over(r), "-201..-300, own over")

print()
print("=" * 100)
print("STUDY 2 - THE EARLY-WEEK NUMBER (E = the first fair look of the week, 1.5-7.5 days out, after both teams' last games)")
print("=" * 100)


def e(r):
    return r["w"].get("E")


def e_fav(r, lo=-150, hi=-101):
    w = e(r)
    return w and lo <= w["price"] <= hi


def e_dog(r, lo=100, hi=350):
    w = e(r)
    return w and lo <= w["price"] <= hi


def e_price(r):
    return e(r)["price"]


def e_best(r):
    return e(r)["best"]


def e_own_over(r, read="own_blind"):
    return r[read] >= e(r)["mkt"]


for read in ("own_blind", "own"):
    print(f"--- read = {read} (own_blind = no injury info, what's known Tuesday)")
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd), f"EARLY LOCK: E fav -101..-150, blend@E 56%+, {read} over E", e_price)
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd), f"  ...same sides graded at the CLOSE price", lambda r: r["close"])
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd), f"  ...same sides at the best early book", e_best)
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd) and r[rd] * dec(e_price(r)) - 1 >= 0.03, f"  ...{read} edge 3%+ at E", e_price)
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd) and r[rd] >= 0.60, f"  ...{read} 60%+", e_price)
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd) and fav_band(r), f"  ...still -101..-150 at the close", e_price)
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd) and dec(r['close']) < dec(e_price(r)), f"  ...the price shortened by the close (CLV won)", e_price)
    split(lambda r, rd=read: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, rd) and dec(r['close']) >= dec(e_price(r)), f"  ...the price got longer by the close", e_price)
    for gap in (0.03, 0.06, 0.09):
        split(lambda r, rd=read, g=gap: e_fav(r) and r[rd] - e(r)["mkt"] >= g, f"  E fav, {read} {gap:.0%}+ over the E no-vig", e_price)
        split(lambda r, rd=read, g=gap: e_dog(r) and r[rd] - e(r)["mkt"] >= g, f"  E dog +100..+350, {read} {gap:.0%}+ over the E no-vig", e_price)
    split(lambda r, rd=read: e_fav(r, -250, -151) and r[rd] - e(r)["mkt"] >= 0.04, f"  E fav -151..-250, {read} 4%+ over", e_price)
print("--- how the early favorite's price moves (favorites -101..-150 at E): share whose close is shorter")
for sel, lbl in ((lambda r: e_fav(r), "all"), (lambda r: e_fav(r) and e(r)["blend"] >= 0.56 and e_own_over(r, "own_blind"), "early Lock (own_blind)"),
                 (lambda r: e_fav(r) and r["own_blind"] < e(r)["mkt"], "own_blind UNDER")):
    xs = [r for r in rows if sel(r)]
    sh = sum(1 for r in xs if dec(r["close"]) < dec(e_price(r))) / max(1, len(xs))
    avg = sum((1 / dec(r["close"])) - (1 / dec(e_price(r))) for r in xs) / max(1, len(xs))
    print(f"  {lbl:28} n {len(xs)} shortened {sh:.1%}, avg implied move {avg:+.2%}")

print()
print("=" * 100)
print("STUDY 3 - THE FRESH QB CHANGE (nflverse report: the QB who started the team's last game is Out / Doubtful this week; box scores confirm another QB threw)")
print("=" * 100)
ABBR = {"ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills", "CAR": "Panthers", "CHI": "Bears", "CIN": "Bengals",
        "CLE": "Browns", "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers", "HOU": "Texans", "IND": "Colts",
        "JAX": "Jaguars", "KC": "Chiefs", "LA": "Rams", "LAC": "Chargers", "LV": "Raiders", "MIA": "Dolphins", "MIN": "Vikings",
        "NE": "Patriots", "NO": "Saints", "NYG": "Giants", "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SEA": "Seahawks",
        "SF": "49ers", "TB": "Buccaneers", "TEN": "Titans", "WAS": "Commanders"}
inj = list(csv.DictReader(gzip.open(os.path.join(REPO, "data/sports/injuries/nfl.csv.gz"), "rt")))


def nm(x):
    return " ".join(x.lower().replace(".", "").replace("'", "").split())


qb_out = defaultdict(set)         # (season, week, nickname) -> {qb names Out/Doubtful}
qb_q = defaultdict(set)
for r in inj:
    if r["position"] != "QB" or r["game_type"] != "REG":
        continue
    k = (int(r["season"]), int(r["week"]), ABBR.get(r["team"]))
    if r["report_status"] in ("Out", "Doubtful"):
        qb_out[k].add(nm(r["full_name"]))
    elif r["report_status"] == "Questionable":
        qb_q[k].add(nm(r["full_name"]))
# the QB who threw the most in each team-game (box scores)
box = sr.load("nfl")
att = defaultdict(lambda: defaultdict(float))
for b in box:
    if b.get("group") != "passing":
        continue
    try:
        a = float(json.loads(b["stats"]).get("completions/passingAttempts", "0/0").split("/")[-1])
    except (ValueError, AttributeError):
        continue
    att[(b["gid"], b["team"])][b["player"]] += a
starter = {k: max(v, key=v.get) for k, v in att.items() if v}
# weeks: from each season's first regular-season game (a Thursday)
first = {}
for r in rows:
    if r["month"] in (9,) or (r["month"] == 8):
        first[r["season"]] = min(first.get(r["season"], r["start"]), r["start"])
def week(r):
    f = datetime.fromisoformat(first[r["season"]][:10])
    d = datetime.fromisoformat(r["start"][:10])
    return (d - f + timedelta(days=1)).days // 7 + 1    # (a Thursday opener; Monday games stay in the week - shift 1 day)
# the team's previous game this season (by rows)
by_team = defaultdict(list)
for r in rows:
    by_team[(r["season"], r["team"])].append(r)
for v in by_team.values():
    v.sort(key=lambda r: r["start"])
prev = {}
for v in by_team.values():
    for i, r in enumerate(v):
        prev[(r["gid"], r["team"])] = v[i - 1] if i else None
fresh, known, q_only, n_rows = {}, {}, {}, 0
for r in rows:
    if r["season"] not in first:
        continue
    wk = week(r)
    if not 1 <= wk <= 18:
        continue
    p = prev.get((r["gid"], r["team"]))
    if not p:
        continue
    last_qb = starter.get((p["gid"], r["team"]))
    this_qb = starter.get((r["gid"], r["team"]))
    if not last_qb or not this_qb:
        continue
    n_rows += 1
    outs = qb_out.get((r["season"], wk, r["team_name"]), set())
    qs = qb_q.get((r["season"], wk, r["team_name"]), set())
    k = (r["gid"], r["team"])
    if nm(last_qb) in outs and nm(this_qb) != nm(last_qb):
        fresh[k] = (last_qb, this_qb)
    elif nm(last_qb) in qs and nm(this_qb) != nm(last_qb):
        q_only[k] = (last_qb, this_qb)
    elif nm(this_qb) != nm(last_qb):
        known[k] = (last_qb, this_qb)   # a change the report didn't flag (benched / the week before's change)
print(f"team-games with a known last-game QB and this-game QB: {n_rows}; FRESH QB change (last starter Out/Doubtful): {len(fresh)}; "
      f"questionable-then-sat: {len(q_only)}; other changes (benching / already-known): {len(known)}")
opp_of = {}
for r in rows:
    opp_of[(r["gid"], r["team"])] = r
def is_fresh(r):      # this side's QB changed
    return (r["gid"], r["team"]) in fresh
def opp_fresh(r):     # the opponent's QB changed (we face a backup)
    return (r["gid"], r["opp"]) in fresh
def opp_q(r):
    return (r["gid"], r["opp"]) in q_only
def opp_known(r):
    return (r["gid"], r["opp"]) in known
for lbl, f_ in (("FRESH change (Out/Doubtful)", opp_fresh), ("questionable then sat", opp_q), ("other change (benched / 2nd week)", opp_known)):
    print(f"--- facing the backup: {lbl}")
    split(lambda r, f=f_: f(r), "  the side facing the new QB, any price, close")
    split(lambda r, f=f_: f(r) and r["close"] < 100, "  ...as a favorite, close")
    split(lambda r, f=f_: f(r) and fav_band(r), "  ...as a -101..-150 favorite, close")
    split(lambda r, f=f_: f(r) and -250 <= r["close"] <= -151, "  ...as a -151..-250 favorite, close")
    split(lambda r, f=f_: f(r) and r["close"] >= 100, "  ...as a dog, close")
    split(lambda r, f=f_: f(r) and r["close"] < 100 and own_over(r), "  ...favorite with the own read (inj in) over the close")
    split(lambda r, f=f_: f(r) and r["close"] < 100 and r["blend"] >= 0.56 and own_over(r), "  ...the Lock test (blend 56%+, own over)")
    split(lambda r, f=f_: f(r) and e(r) is not None, "  ...graded at E (first look - before the news?)", e_price)
    split(lambda r, f=f_: f(r) and e(r) is not None, "  ...the same sides at the close", lambda r: r["close"])
    split(lambda r, f=f_: f(r) and r["w"].get("M") is not None, "  ...graded at M (last look before game day)", lambda r: r["w"]["M"]["price"])
    split(lambda r, f=f_: f(r) and r["w"].get("M") is not None, "  ...the same sides at the close", lambda r: r["close"])
    split(lambda r, f=f_: f(r) and r["w"].get("G") is not None, "  ...graded at G (game morning)", lambda r: r["w"]["G"]["price"])
    print("  the new-QB side itself:")
    split(lambda r, f=f_: (r["gid"], r["team"]) in {k for k in (fresh if f is opp_fresh else q_only if f is opp_q else known)}, "  the new-QB team, any price, close")
    split(lambda r, f=f_: (r["gid"], r["team"]) in {k for k in (fresh if f is opp_fresh else q_only if f is opp_q else known)} and r["close"] >= 100, "  ...as a dog, close")
# the market move E -> close for the side facing a FRESH backup
xs = [r for r in rows if opp_fresh(r) and e(r)]
if xs:
    mv = [(1 / dec(r["close"])) - (1 / dec(e_price(r))) for r in xs]
    print(f"facing a fresh backup, E -> close implied move for our side: avg {sum(mv)/len(mv):+.2%}, n {len(mv)}; shortened {sum(1 for m in mv if m > 0)/len(mv):.0%}")
    # how much does the engine's own read (QB penalty in) differ from the close for these?
    gap = [r["own"] - r["mkt_close"] for r in xs if r["mkt_close"] is not None]
    print(f"  own read minus the no-vig close for the side facing the backup: avg {sum(gap)/len(gap):+.2%}")
print()
print("Calibration of the close for the side facing a fresh backup, by close band (train+hold pooled):")
for lo, hi in ((-400, -201), (-200, -151), (-150, -101), (100, 160), (161, 350)):
    xs = [r for r in rows if opp_fresh(r) and lo <= r["close"] <= hi]
    if xs:
        print(f"  {lo}..{hi}: n {len(xs)} won {sum(r['won'] for r in xs)/len(xs):.1%} said {sum(1/dec(r['close']) for r in xs)/len(xs):.1%}")
print("examples (hold):", [(r["season"], r["team_name"], "vs", r["opp_name"], fresh[(r["gid"], r["opp"])], r["close"], r["won"]) for r in rows if opp_fresh(r) and r["season"] >= 2025][:12])
