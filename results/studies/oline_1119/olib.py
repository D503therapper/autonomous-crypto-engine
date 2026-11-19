"""THE 11/19 OFFENSIVE LINE / SECONDARY / PASS RUSH STUDY - the shared table (nflverse's public files, fetch.py).

One row a TEAM-GAME (regular season 2016-26, a team's game 3+ so the snap counts say who starts):
  WHO STARTS: a man who played 70%+ of the snaps in 2+ of his team's last 4 games - offense for T / G / C (and TE),
    defense for CB / S / LB; 50%+ for the men up front on defense (DE / DT / NT - they rotate; a starting tackle
    plays ~55-65%).  (The FIRST pass - s1_first_rule.out / s2_first_rule.out - used "2+ of the last 3 games, 70%+ on
    average"; the Colts' own tackles broke it: Raimann went down 10% into his last game and Travis 41% into his, so
    the average called neither a starter. A game a man leaves hurt must not unmake him. Every table was re-run on the
    rule above; both passes are kept and say the same thing.)
  WHO IS OUT: a starter the final injury report lists Out / Doubtful, or a starter with no game status on the report
    who does not dress (injured reserve / a suspension - public before the game; study 8 measured the report: an
    Out / Doubtful man plays 0.2% of the time).  "report only" columns drop the second kind (no look-ahead at all).
  THE OTHER SIDE: its pass rush = sacks per opponent drop-back this season before the game (3+ games), ranked inside
    the season-week (top third = "good pass rush"); its passing offense = net passing yards a game, the same way.
  PRICES: the closing moneylines / spread of nflverse's schedules file; the FIRST FAIR price = our paid odds history's
    first snapshot 20+ hours after both teams' last games (2020-26 only; the median book)."""
import csv
import gzip
import json
import math
import os
import random
import re
import statistics
from collections import defaultdict

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_oline1119", "dl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TEAM = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA", "WSH": "WAS", "JAC": "JAX", "GNB": "GB", "KAN": "KC", "NWE": "NE",
        "NOR": "NO", "SFO": "SF", "TAM": "TB", "LVR": "LV", "HST": "HOU", "BLT": "BAL", "CLV": "CLE", "ARZ": "ARI"}
GROUP = {"T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL", "TE": "TE",
         "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
         "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB", "DB": "DB"}
OFFENSE = {"OL", "TE"}
MIN_SHARE = {"OL": 0.70, "TE": 0.70, "DB": 0.70, "LB": 0.70, "DL": 0.50}
LAST, NEED = 4, 2
TRAIN = range(2016, 2022)            # train 2016-21, held out 2022-26
FULL = {"Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
        "Carolina Panthers": "CAR", "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
        "Dallas Cowboys": "DAL", "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
        "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
        "Las Vegas Raiders": "LV", "Oakland Raiders": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LA",
        "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO",
        "New York Giants": "NYG", "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
        "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN",
        "Washington Commanders": "WAS", "Washington Football Team": "WAS", "Washington Redskins": "WAS"}


def tm(t):
    return TEAM.get(t, t)


def nm(s):
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", str(s).lower())
    return re.sub(r"[^a-z]", "", s)


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def load_games():
    out = []
    for r in csv.DictReader(open(os.path.join(DL, "games.csv"))):
        y = int(r["season"])
        if y < 2015 or r["game_type"] != "REG" or not r["home_score"] or not r["home_moneyline"] or not r["away_moneyline"]:
            continue
        dh, da = dec(r["home_moneyline"]), dec(r["away_moneyline"])
        out.append(dict(gid=r["game_id"], season=y, week=int(r["week"]), date=r["gameday"], time=r["gametime"],
                        home=tm(r["home_team"]), away=tm(r["away_team"]), hs=int(r["home_score"]), as_=int(r["away_score"]),
                        dh=dh, da=da, pm=(1 / dh) / (1 / dh + 1 / da), spread=_f(r["spread_line"], None),
                        hso=_f(r["home_spread_odds"], -110) or -110, aso=_f(r["away_spread_odds"], -110) or -110,
                        neutral=r["location"] != "Home"))
    out.sort(key=lambda g: (g["date"], g["gid"]))
    return out


def load_snaps():
    snaps = defaultdict(dict)        # (season, team) -> {week: {name: (pos, group, share)}}
    for y in range(2015, 2027):
        p = os.path.join(DL, f"snap_counts_{y}.csv")
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p)):
            if r["game_type"] != "REG" or r["position"] not in GROUP:
                continue
            g = GROUP[r["position"]]
            sh = _f(r["offense_pct"] if g in OFFENSE else r["defense_pct"])
            snaps[(y, tm(r["team"]))].setdefault(int(r["week"]), {})[nm(r["player"])] = (r["position"], g, sh)
    return snaps


def load_inj():
    inj = defaultdict(dict)          # (season, team, week) -> {name: status}
    for y in range(2015, 2027):
        p = os.path.join(DL, f"injuries_{y}.csv")
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p)):
            if r.get("game_type") != "REG":
                continue
            inj[(y, tm(r["team"]), int(r["week"]))][nm(r["full_name"])] = (r["report_status"] or "").strip()
    return inj


def load_team_stats():
    st = {}                          # (season, team, week) -> dict
    for y in range(2015, 2027):
        p = os.path.join(DL, f"stw_{y}.csv")
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p)):
            if r["season_type"] != "REG":
                continue
            st[(y, tm(r["team"]), int(r["week"]))] = dict(att=_f(r["attempts"]), sk_taken=_f(r["sacks_suffered"]),
                                                           py=_f(r["passing_yards"]), sk_lost=abs(_f(r["sack_yards_lost"])),
                                                           sacks=_f(r["def_sacks"]), hits=_f(r["def_qb_hits"]), opp=tm(r["opponent_team"]))
    return st


def starters(snaps, season, team, week):
    """{name: (pos, group, share)} - the starters going into `week` (the rule at the top), or None under 2 games."""
    wk = sorted(w for w in snaps.get((season, team), {}) if w < week)[-LAST:]
    if len(wk) < 2:
        return None
    seen = defaultdict(list)
    for w in wk:
        for n, (pos, g, sh) in snaps[(season, team)][w].items():
            if sh >= MIN_SHARE[g]:
                seen[n].append((pos, g, sh))
    out = {}
    for n, xs in seen.items():
        if len(xs) < NEED:
            continue
        out[n] = (xs[-1][0], xs[-1][1], sum(x[2] for x in xs) / len(xs))
    return out


def first_fair(games):
    """{(date, home): (dec home, dec away, spread home, home spread dec, away spread dec)} at the first snapshot 20+
    hours after both teams' last games (the paid odds history, 2020-26; the median book)."""
    last = {}
    prev = {}
    for g in games:
        ko = g["date"] + "T" + (g["time"] or "13:00")
        prev[g["gid"]] = max(last.get(g["home"], ""), last.get(g["away"], ""))
        last[g["home"]] = last[g["away"]] = ko
    by = {(g["date"], g["home"]): g for g in games}

    def read(name):
        got = defaultdict(list)
        p = os.path.join(ROOT, "data", "sports", "odds_history", name)
        if not os.path.exists(p):
            return got
        for line in gzip.open(p, "rt"):
            d = json.loads(line)
            if "id" not in d or d.get("h") not in FULL:
                continue
            for off in (0, -1):                              # (kickoff UTC -> the US date)
                day = d["t"][:10]
                if off:
                    import datetime as dt
                    day = (dt.date.fromisoformat(day) + dt.timedelta(days=off)).isoformat()
                g = by.get((day, FULL[d["h"]]))
                if g and FULL.get(d["a"]) == g["away"]:
                    got[g["gid"]].append((d["snap"], d["b"]))
                    break
        return got
    ml, sp = read("americanfootball_nfl.jsonl.gz"), read("americanfootball_nfl_spreads.jsonl.gz")
    out = {}
    import datetime as dt
    for g in games:
        p = prev.get(g["gid"]) or ""
        if not p:
            continue
        t0 = (dt.datetime.fromisoformat(p) + dt.timedelta(hours=5 + 20)).isoformat()   # (ET kickoff -> UTC, + 20 h)
        ko = (dt.datetime.fromisoformat(g["date"] + "T" + (g["time"] or "13:00")) + dt.timedelta(hours=5)).isoformat()
        m = sorted((s, b) for s, b in ml.get(g["gid"], []) if t0 <= s[:19] < ko)
        if not m:
            continue
        hs = [dec(v[0]) for v in m[0][1].values() if v and v[0] and v[1]]
        as_ = [dec(v[1]) for v in m[0][1].values() if v and v[0] and v[1]]
        if len(hs) < 3:
            continue
        rec = {"dh": statistics.median(hs), "da": statistics.median(as_), "snap": m[0][0]}
        s = sorted((s, b) for s, b in sp.get(g["gid"], []) if t0 <= s[:19] < ko)
        if s:
            pts = [v[0] for v in s[0][1].values() if v and len(v) >= 4]
            if len(pts) >= 3:
                rec["sp_home"] = statistics.median(pts)      # the home team's line (- = favored)
        out[g["gid"]] = rec
    return out


def build():
    games, snaps, inj, ts = load_games(), load_snaps(), load_inj(), load_team_stats()
    ff = first_fair(games)
    # season-to-date team numbers BEFORE each week
    cum = defaultdict(lambda: dict(n=0, att=0.0, skt=0.0, py=0.0, skl=0.0, sacks=0.0, hits=0.0, opp_db=0.0))
    todate = {}
    for (y, t, w) in sorted(ts):
        c = cum[(y, t)]
        todate[(y, t, w)] = dict(c)
        r = ts[(y, t, w)]
        o = ts.get((y, r["opp"], w))
        c["n"] += 1
        for k_, v in (("att", r["att"]), ("skt", r["sk_taken"]), ("py", r["py"]), ("skl", r["sk_lost"]), ("sacks", r["sacks"]),
                      ("hits", r["hits"])):
            c[k_] += v
        if o:
            c["opp_db"] += o["att"] + o["sk_taken"]
    rows = []
    for g in games:
        if g["season"] < 2016:
            continue
        side = {}
        for s, t, o in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            st = starters(snaps, g["season"], t, g["week"])
            if st is None:
                side = None
                break
            rep = inj.get((g["season"], t, g["week"]), {})
            played = snaps.get((g["season"], t), {}).get(g["week"], {})
            out_rep = {n for n in st if rep.get(n) in ("Out", "Doubtful")}
            out_ir = {n for n in st if n not in out_rep and not rep.get(n) and (n not in played or played[n][2] == 0)}
            q = {n for n in st if rep.get(n) == "Questionable"}
            td = todate.get((g["season"], t, g["week"])) or {}
            side[s] = dict(team=t, st=st, out_rep=out_rep, out=out_rep | out_ir, q=q,
                           rush=(td["sacks"] / td["opp_db"]) if td.get("n", 0) >= 3 and td.get("opp_db") else None,
                           hits=(td["hits"] / td["opp_db"]) if td.get("n", 0) >= 3 and td.get("opp_db") else None,
                           prot=(td["skt"] / (td["att"] + td["skt"])) if td.get("n", 0) >= 3 and td.get("att") else None,
                           passo=((td["py"] - td["skl"]) / td["n"]) if td.get("n", 0) >= 3 else None)
        if side is None:
            continue
        for s in ("home", "away"):
            me, op = side[s], side["away" if s == "home" else "home"]
            d_me, d_op = (g["dh"], g["da"]) if s == "home" else (g["da"], g["dh"])
            p = g["pm"] if s == "home" else 1 - g["pm"]
            margin = (g["hs"] - g["as_"]) * (1 if s == "home" else -1)
            sp = None if g["spread"] is None else (g["spread"] if s == "home" else -g["spread"])   # + = we're favored by
            f = ff.get(g["gid"]) or {}

            def cnt(names, pred):
                return sum(1 for n in names if pred(*me["st"][n][:2]))

            def cnt_o(names, pred):
                return sum(1 for n in names if pred(*op["st"][n][:2]))
            r = dict(gid=g["gid"], season=g["season"], week=g["week"], team=me["team"], opp=op["team"], home=s == "home",
                     neutral=g["neutral"], win=1 if margin > 0 else 0 if margin < 0 else 0.5, margin=margin,
                     p=p, d=d_me, d_opp=d_op, sp=sp, so=dec(g["hso"] if s == "home" else g["aso"]),
                     so_opp=dec(g["aso"] if s == "home" else g["hso"]),
                     ff_d=f.get("dh" if s == "home" else "da"), ff_d_opp=f.get("da" if s == "home" else "dh"),
                     ff_sp=None if f.get("sp_home") is None else (-f["sp_home"] if s == "home" else f["sp_home"]),
                     opp_rush=op["rush"], opp_hits=op["hits"], opp_pass=op["passo"], my_prot=me["prot"])
            for tag, names, names_o in (("", me["out"], op["out"]), ("r_", me["out_rep"], op["out_rep"]), ("q_", me["q"], op["q"])):
                r[tag + "ol"] = cnt(names, lambda pos, grp: grp == "OL")
                r[tag + "t"] = cnt(names, lambda pos, grp: pos in ("T", "OT"))
                r[tag + "int"] = cnt(names, lambda pos, grp: pos in ("G", "C", "OG"))
                r[tag + "db"] = cnt(names, lambda pos, grp: grp == "DB")
                r[tag + "cb"] = cnt(names, lambda pos, grp: pos == "CB")
                r[tag + "s"] = cnt(names, lambda pos, grp: pos in ("S", "SS", "FS"))
                r[tag + "dl"] = cnt(names, lambda pos, grp: grp == "DL")
                r[tag + "de"] = cnt(names, lambda pos, grp: pos == "DE")
                r[tag + "lb"] = cnt(names, lambda pos, grp: grp == "LB")
                r[tag + "te"] = cnt(names, lambda pos, grp: grp == "TE")
                r[tag + "o_ol"] = cnt_o(names_o, lambda pos, grp: grp == "OL")
                r[tag + "o_t"] = cnt_o(names_o, lambda pos, grp: pos in ("T", "OT"))
                r[tag + "o_cb"] = cnt_o(names_o, lambda pos, grp: pos == "CB")
                r[tag + "o_db"] = cnt_o(names_o, lambda pos, grp: grp == "DB")
                r[tag + "o_dl"] = cnt_o(names_o, lambda pos, grp: grp == "DL")
                r[tag + "o_de"] = cnt_o(names_o, lambda pos, grp: pos == "DE")
                r[tag + "o_all"] = len(names_o)
                r[tag + "all"] = len(names)
            r["n_ol_st"] = sum(1 for v in me["st"].values() if v[1] == "OL")
            r["n_t_st"] = sum(1 for v in me["st"].values() if v[0] in ("T", "OT"))
            rows.append(r)
    # the other side's pass rush / passing game, ranked inside the season-week (top third)
    by = defaultdict(list)
    for r in rows:
        by[(r["season"], r["week"])].append(r)
    for rs in by.values():
        for k_, name in (("opp_rush", "rush_top"), ("opp_pass", "pass_top"), ("opp_hits", "hits_top")):
            vals = sorted(x[k_] for x in rs if x[k_] is not None)
            for x in rs:
                if x[k_] is None or len(vals) < 9:
                    x[name] = None
                else:
                    x[name] = x[k_] >= vals[int(len(vals) * 2 / 3)]
                    x[name.replace("top", "bot")] = x[k_] <= vals[int(len(vals) / 3)]
    return rows


# ---------------------------------------------------------------- the bets
def ml(rows, fade=True, key=("d", "d_opp"), worse=0.0):
    """Moneyline at the close (or the first fair price): fade = bet the OTHER side of each row. `worse` = points of win
    chance the price is made worse by (0.01 = a point worse than the close). -> [(season, profit a unit, won - price)]."""
    out = []
    for r in rows:
        d = r[key[1] if fade else key[0]]
        d2 = r[key[0] if fade else key[1]]
        if not d or not d2:
            continue
        w = (1 - r["win"]) if fade else r["win"]
        if worse:
            d = 1 / (1 / d + worse)
        pm = (1 / d) / (1 / d + 1 / d2) if not worse else None
        out.append((r["season"], (d - 1) if w == 1 else 0.0 if w == 0.5 else -1.0, (w - pm) if pm is not None else 0.0))
    return out


def ats(rows, fade=True, key="sp", worse=0.0):
    """Against the spread at the close: fade = the other side. `worse` = points the number is made worse by."""
    out = []
    for r in rows:
        if r.get(key) is None:
            continue
        m = r["margin"] - r[key]                             # our side covers when > 0 (sp + = we lay that many)
        if fade:
            m = -m
        m -= worse
        d = (r["so_opp"] if fade else r["so"]) if key == "sp" else dec(-110)
        out.append((r["season"], (d - 1) if m > 0 else 0.0 if m == 0 else -1.0, 1.0 if m > 0 else 0.5 if m == 0 else 0.0))
    return out


def roi(xs):
    if not xs:
        return None
    pr = [x[1] for x in xs]
    n = len(pr)
    mean = sum(pr) / n
    sd = statistics.pstdev(pr) if n > 1 else 0
    return dict(n=n, roi=100 * mean, z=(mean / (sd / math.sqrt(n))) if sd else 0.0)


def cell(xs):
    a = roi([x for x in xs if x[0] in TRAIN])
    b = roi([x for x in xs if x[0] not in TRAIN])
    seas = defaultdict(float)
    for x in xs:
        seas[x[0]] += x[1]
    up = sum(1 for v in seas.values() if v > 0)
    f = lambda c: "none            " if not c else f"{c['roi']:+6.1f}% on {c['n']:4d} (z {c['z']:+.1f})"   # noqa: E731
    allc = roi(xs)
    return f"all {f(allc)} | train {f(a)} | held {f(b)} | seasons up {up}/{len(seas)}", a, b, allc


def placebo(pool_profit, n, obs_roi, draws=2000, seed=7):
    """How many of `draws` random sets of n bets from the pool do as well as the cell (the sign of the cell's ROI)."""
    rnd = random.Random(seed)
    k = 0
    for _ in range(draws):
        s = rnd.sample(pool_profit, min(n, len(pool_profit)))
        m = 100 * sum(s) / len(s)
        if (obs_roi >= 0 and m >= obs_roi) or (obs_roi < 0 and m <= obs_roi):
            k += 1
    return k


def vs_price(rows):
    """Won % vs what the no-vig close said, with z (the side in the row)."""
    xs = [r for r in rows if r["win"] != 0.5]
    if not xs:
        return "none"
    w = sum(r["win"] for r in xs) / len(xs)
    p = sum(r["p"] for r in xs) / len(xs)
    se = math.sqrt(sum(r["p"] * (1 - r["p"]) for r in xs)) / len(xs)
    return f"won {100 * w:.1f}% vs the close's {100 * p:.1f}% on {len(xs)} (z {(w - p) / se:+.1f})"
