"""11/2 - NHL ODDS HISTORY STUDIES: the shared table (read-only on the repo; the cache lands here as _rows.pkl).

The paid odds history (data/sports/odds_history/icehockey_nhl.jsonl.gz, tools/odds_history.DAILY_PLAN): ONE 15:00Z look a
day, 2021-01 .. 2023-04, regular season, every US book. Each look holds the game-day MORNING price (the 8 AM board's hour)
and the NEXT day's line already up (~28 hours out - the overnight opener, like ESPN's open; a team that plays tonight
gets no next-day line yet). A row whose snapshot is at or after puck drop is dropped. The CLOSE is ESPN's (games/nhl).

Every price: each book's quote is kept only when it is sane (both sides |price| >= 100, the two implied chances add to
0.99..1.10 - drops the exchange's lay quotes and the odd broken feed); the MARKET = the median book's no-vig win %, the
PRICE we grade at = the median book's price for that side (a board price, not the best line).

State features (known before the game, from every NHL final since 2016): rest / back-to-back, win / loss streak, both
teams' last result, how the last game ended (OT / shootout), Pythagorean luck (games 5-20), last-10 shot share and
puck luck (from the goalie rows: shots for = the other team's goalies' shots faced), 40+ shots allowed last game, the
market's move on the team over its last 3 priced games (open -> close; 2021-23 open = the paid next-day line, else the
morning look), and the engine's LIVE hockey read (the line + b2b / rest, sports_hockey's form, weights fit on the
2016-20 closes only = blind for 2021-23)."""
import csv, glob, gzip, json, math, os, pickle, statistics, sys
from collections import defaultdict, deque, Counter
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
sys.path.insert(0, ROOT)

SEASONS = ("2020-21", "2021-22", "2022-23")
TRAIN = ("2020-21", "2021-22")       # the NEW angles (studies 4-5): train on the first two seasons ...
HELD = ("2022-23",)                  # ... and hold the newest out; re-validations (1-3) treat all three as held out


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


def t(s):
    s = s.replace("Z", "")
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{str(y + 1)[2:]}" if m >= 8 else f"{y - 1}-{str(y)[2:]}"


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


def sane(ph, pa):
    if abs(ph) < 100 or abs(pa) < 100:
        return False
    s = 1 / dec(ph) + 1 / dec(pa)
    return 0.99 <= s <= 1.10


def consensus(books):
    """{book: [home, away]} -> dict(p=median no-vig home %, ph=median home price, pa=median away price, n, best_h, best_a,
    q={book: (home, away)}) or None."""
    q = {b: (v[0], v[1]) for b, v in books.items() if isinstance(v, list) and len(v) >= 2 and v[0] and v[1] and sane(v[0], v[1])}
    if len(q) < 3:
        return None
    ps = [nv(h, a) for h, a in q.values()]
    hs = sorted(dec(h) for h, _ in q.values())
    as_ = sorted(dec(a) for _, a in q.values())
    return dict(p=statistics.median(ps), dh=statistics.median(hs), da=statistics.median(as_), n=len(q),
                bh=max(hs), ba=max(as_), q=q)


TEAM_FIX = {"Montréal Canadiens": "Canadiens", "Montreal Canadiens": "Canadiens", "St Louis Blues": "Blues"}


def odds_by_game():
    """{(home nickname, away nickname, date of puck drop): {'open': cons, 'morning': cons, ...}} from the paid file."""
    looks = defaultdict(list)
    for line in gzip.open(f"{ROOT}/data/sports/odds_history/icehockey_nhl.jsonl.gz", "rt"):
        r = json.loads(line)
        if "snap" not in r:
            continue
        snap, tip = t(r["snap"]), t(r["t"])
        if snap >= tip:                                   # at or after puck drop: dropped (the owner's rule)
            continue
        c = consensus(r["b"])
        if not c:
            continue
        looks[(r["h"], r["a"], r["t"][:13])].append(((tip - snap).total_seconds() / 3600, c))
    return looks


def nick(full, names):
    full = TEAM_FIX.get(full, full)
    for n in sorted(names, key=len, reverse=True):
        if full.endswith(n):
            return n
    return None


def load_games():
    games = []
    for f in sorted(glob.glob(f"{ROOT}/data/sports/games/nhl/*.csv")):
        for g in csv.DictReader(open(f)):
            if g["status"] == "final" and g.get("stype") == "2" and g["home_score"] != "":
                games.append(g)
    games.sort(key=lambda g: g["start"])
    return games


def goalie_rows():
    by = defaultdict(list)                            # (gid, team) -> [(player, sa, ga)]
    for r in csv.DictReader(open(f"{ROOT}/data/sports/players/nhl.csv")):
        if r.get("role", "G") == "G":
            try:
                by[(r["gid"], r["team"])].append((r["player"], float(r["sa"] or 0), float(r["ga"] or 0)))
            except ValueError:
                pass
    return by


LIVE_W = [0.1166, 0.01]    # data/sports/hockey.json's b2b / rest weights - the read exactly as it runs live (a 2-term fit on
#                            every close; the blind 2016-20 fit is kept beside it as read_w_blind - the b2b sign agrees)


def fit_read(rows_):
    """sports_hockey's own fit on top of the line: logit(p) + w_b2b * b2b + w_rest * rest (home side). rows_: (p, b2b, rest, y)."""
    w = [0.0, 0.0]
    for _ in range(300):
        g0 = g1 = 0.0
        for p, b, r, y in rows_:
            e = sig(logit(p) + w[0] * b + w[1] * r) - y
            g0 += e * b; g1 += e * r
        w[0] -= 0.5 * (g0 / len(rows_) + 0.002 * w[0]); w[1] -= 0.5 * (g1 / len(rows_) + 0.002 * w[1])
    return w


def build(force=False):
    cache = f"{OUT}/_rows.pkl"
    if os.path.exists(cache) and not force:
        return pickle.load(open(cache, "rb"))
    games = load_games()
    gk = goalie_rows()
    names = {g["home_name"] for g in games} | {g["away_name"] for g in games}
    looks = odds_by_game()
    # index the odds looks by (home nick, away nick, date)
    oidx = defaultdict(list)
    for (h, a, tip), ls in looks.items():
        nh, na = nick(h, names), nick(a, names)
        if nh and na:
            oidx[(nh, na)].append((t(tip + ":00"), ls))

    last = {}                                      # team -> (time, tz, start, home?)
    streak = defaultdict(int); lastres = {}        # team -> won last (bool)
    lastgame = {}                                  # team -> game dict (for OT check)
    rec = defaultdict(lambda: [0, 0, 0, 0])        # (team, season) -> w, n, gf, ga
    shots = defaultdict(lambda: deque(maxlen=10))  # team -> (sf, sa, gf, ga)
    mk = defaultdict(list)                         # (team, season) -> [no-vig move open->close from team side]
    starts = defaultdict(lambda: deque(maxlen=20))
    read_train = []
    rows = []
    for g in games:
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except ValueError:
            continue
        h, a = g["home"], g["away"]
        tm = t(g["start"]); tz = float(g.get("tzo") or 0); ssn = season(g["start"])
        try:
            ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
            close_ok = sane(ch, ca)
        except (ValueError, TypeError):
            close_ok = False

        def rest(team):
            return min(7.0, (tm - last[team][0]).total_seconds() / 86400) if team in last and season(last[team][2]) == ssn else 7.0

        rh, ra = rest(h), rest(a)
        # odds history looks for this game
        morning = opn = None
        for tip, ls in oidx.get((g["home_name"], g["away_name"]), []):
            if abs((tip - tm).total_seconds()) <= 6 * 3600:
                for hrs, c in sorted(ls, key=lambda x: -x[0]):
                    if hrs > 20 and opn is None:
                        opn = dict(c, hrs=hrs)
                    if hrs <= 20:
                        morning = dict(c, hrs=hrs)
        row = None
        if close_ok:
            def ot(team):
                pg = lastgame.get(team)
                if not pg or (tm.date() - t(pg["start"]).date()).days > 4:
                    return None
                n = len([p for p in str(pg.get("ls_home") or "").split(",") if p.strip() != ""])
                if n < 4:
                    return None
                me = "home" if pg["home"] == team else "away"; op = "away" if me == "home" else "home"
                won = int(pg[f"{me}_score"]) > int(pg[f"{op}_score"])
                return ("so_" if n >= 5 else "ot_") + ("win" if won else "loss")

            def pyth(team):
                w, n, gf, ga = rec[(team, ssn)]
                if not 5 <= n <= 20 or gf + ga <= 0:
                    return None
                return w / n - gf ** 2 / (gf ** 2 + ga ** 2)

            def sh(team):
                xs = list(shots[team])
                if len(xs) < 5:
                    return None, None, False
                sf = sum(x[0] for x in xs); sa = sum(x[1] for x in xs); gf = sum(x[2] for x in xs); ga = sum(x[3] for x in xs)
                share = sf / (sf + sa) if sf + sa else None
                pdo = ((gf / sf if sf else 0) + (1 - ga / sa if sa else 0)) * 1000
                lastsa = xs[-1][1]
                return share, pdo, lastsa >= 40

            def trend(team):
                xs = mk.get((team, ssn), [])
                return sum(xs[-3:]) if len(xs) >= 3 else None

            def backup(team):
                gl = gk.get((g["id"], team))
                if not gl:
                    return None
                st = max(gl, key=lambda x: x[1])[0]
                xs = list(starts[team])
                return None if len(xs) < 10 else xs.count(st) / len(xs) < 0.4

            ssh, pdoh, osh = sh(h); ssa, pdoa, osa = sh(a)
            row = dict(id=g["id"], start=g["start"], season=ssn, date=g["start"][:10], home=h, away=a,
                       hn=g["home_name"], an=g["away_name"], hs=hs, as_=as_, hw=int(hs > as_),
                       ch=ch, ca=ca, p_close=nv(ch, ca), morning=morning, open=opn,
                       rest_h=rh, rest_a=ra, b2b_h=int(rh <= 1.2), b2b_a=int(ra <= 1.2),
                       stk_h=streak[(h, ssn)], stk_a=streak[(a, ssn)], wonlast_h=lastres.get((h, ssn)), wonlast_a=lastres.get((a, ssn)),
                       ot_h=ot(h), ot_a=ot(a), pyth_h=pyth(h), pyth_a=pyth(a), ss_h=ssh, ss_a=ssa, pdo_h=pdoh, pdo_a=pdoa,
                       out_h=osh and rh <= 2.05, out_a=osa and ra <= 2.05, mt_h=trend(h), mt_a=trend(a),
                       bk_h=backup(h), bk_a=backup(a),
                       gp_h=rec[(h, ssn)][1], gp_a=rec[(a, ssn)][1],
                       wp_h=rec[(h, ssn)][0] / rec[(h, ssn)][1] if rec[(h, ssn)][1] else None,
                       wp_a=rec[(a, ssn)][0] / rec[(a, ssn)][1] if rec[(a, ssn)][1] else None,
                       travel_a=abs(tz - last[a][1]) if a in last else 0.0, road_a_prev=(a in last and not last[a][3]))
            rows.append(row)
            if ssn < "2020-21" and hs != as_:
                read_train.append((nv(ch, ca), float(ra <= 1.2) - float(rh <= 1.2), (rh - ra) / 7, int(hs > as_)))
        # ---- update state AFTER the row
        last[h] = (tm, tz, g["start"], True); last[a] = (tm, tz, g["start"], False)
        lastgame[h] = g; lastgame[a] = g
        for team, won, gf, ga in ((h, hs > as_, hs, as_), (a, as_ > hs, as_, hs)):
            s = streak[(team, ssn)]
            streak[(team, ssn)] = (s + 1 if s > 0 else 1) if won else (s - 1 if s < 0 else -1)
            lastres[(team, ssn)] = won
            r = rec[(team, ssn)]; r[0] += int(won); r[1] += 1; r[2] += gf; r[3] += ga
        sah = sum(x[1] for x in gk.get((g["id"], h), [])); saa = sum(x[1] for x in gk.get((g["id"], a), []))
        if sah and saa:
            shots[h].append((saa, sah, hs, as_)); shots[a].append((sah, saa, as_, hs))
        for team in (h, a):
            gl = gk.get((g["id"], team))
            if gl:
                starts[team].append(max(gl, key=lambda x: x[1])[0])
        # market move on each team (open -> close): ESPN open (2023+) or the paid next-day line / morning look
        if close_ok:
            po = None
            try:
                oho, oao = int(float(g["ml_home_open"])), int(float(g["ml_away_open"]))
                if sane(oho, oao):
                    po = nv(oho, oao)
            except (ValueError, TypeError):
                pass
            if po is None and row is not None:
                src = row["open"] or row["morning"]
                po = src["p"] if src else None
            if po is not None:
                mv = nv(ch, ca) - po
                mk[(h, ssn)].append(mv); mk[(a, ssn)].append(-mv)
    wb = fit_read(read_train)
    for r in rows:
        r["read_w"] = LIVE_W
    out = dict(rows=rows, read_w=LIVE_W, read_w_blind=wb, n_train=len(read_train))
    pickle.dump(out, open(cache, "wb"))
    return out


def own_p(r, p_home, side):
    """The live hockey read for `side` ('h' / 'a') on top of a home no-vig market p_home."""
    w = r["read_w"]
    z = logit(p_home) + w[0] * (r["b2b_a"] - r["b2b_h"]) + w[1] * (r["rest_h"] - r["rest_a"]) / 7
    ph = sig(z)
    return ph if side == "h" else 1 - ph


def sides(r, at="morning"):
    """Both sides of a game at a price point ('morning' / 'open' / 'close'): dicts with price (dec + american), market p,
    own p, the dog-score pieces. None when that price is missing."""
    if at == "close":
        P = dict(p=r["p_close"], dh=dec(r["ch"]), da=dec(r["ca"]))
    else:
        P = r.get(at)
        if not P:
            return None
    out = []
    for s, o in (("h", "a"), ("a", "h")):
        pm = P["p"] if s == "h" else 1 - P["p"]
        d = P["dh"] if s == "h" else P["da"]
        am = (d - 1) * 100 if d >= 2 else -100 / (d - 1)
        op = own_p(r, P["p"], s)
        won = r["hw"] if s == "h" else 1 - r["hw"]
        out.append(dict(r=r, side=s, opp=o, team=r["home" if s == "h" else "away"], home=s == "h", dec=d, am=round(am),
                        pm=pm, own=op, gap=(op - pm) * 100, won=won, profit=(d - 1) if won else -1.0,
                        b2b=r[f"b2b_{s}"], ob2b=r[f"b2b_{o}"], rest=r[f"rest_{s}"], orest=r[f"rest_{o}"],
                        stk=r[f"stk_{s}"], ostk=r[f"stk_{o}"], wonlast=r[f"wonlast_{s}"], owonlast=r[f"wonlast_{o}"],
                        ot=r[f"ot_{s}"], oot=r[f"ot_{o}"], pyth=r[f"pyth_{s}"], ss=r[f"ss_{s}"], oss=r[f"ss_{o}"],
                        pdo=r[f"pdo_{s}"], out=r[f"out_{s}"], oout=r[f"out_{o}"], mt=r[f"mt_{s}"], bk=r[f"bk_{s}"],
                        obk=r[f"bk_{o}"], gp=r[f"gp_{s}"]))
    return out


OT_W = {"ot_win": 1, "ot_loss": -2, "so_win": -2}


def dog_score(x, drift=None, hot_w=2, fade_w=2, parts=False):
    """The live hockey dog score (sports.dog_score / dog_spots, the NHL pieces we can rebuild from history - no hits, no
    hot-goalie key_edge / hot_key, no coach changes; capped at +-6 like STUDY_CAP). drift = this side's no-vig move from
    the open to now (+ = the money ran away from it)."""
    base = min(x["gap"], 12.0)
    sc = 0.0
    p = {}
    if x["b2b"] and not x["ob2b"]:
        sc -= 3; p["tired"] = -3
    if x["out"]:
        sc -= 2; p["outshot_me"] = -2
    if x["oout"]:
        sc += 1; p["outshot_opp"] = 1
    if x["wonlast"] is False and x["owonlast"] is False:
        sc += 3.5; p["both_lost"] = 3.5
    if x["am"] >= 200:
        sc -= 2; p["200"] = -2
    if x["ss"] is not None and x["oss"] is not None:
        gap = x["ss"] - x["oss"]
        v = 3 if gap > 0 else -3 if gap <= -0.03 else 0
        sc += v; p["ss"] = v
    if drift is not None:
        if drift >= 0.02:
            sc -= 4; p["drift_away"] = -4
        elif drift <= -0.02:
            sc += 2; p["drift_to"] = 2
    if x["pdo"] is not None:
        v = 2 if x["pdo"] <= 985 else -3 if x["pdo"] >= 1015 else 0
        sc += v; p["pdo"] = v
    if not x["b2b"] and x["ob2b"]:
        sc += 3; p["rested_vs_b2b"] = 3
    if x["mt"] is not None and x["mt"] <= -0.08:
        sc -= fade_w; p["mkt_fade"] = -fade_w
    sc += OT_W.get(x["ot"], 0)
    if x["oot"] == "ot_loss":
        sc += 2
    if x["pyth"] is not None and x["pyth"] <= -0.10:
        sc += 2; p["pyth"] = 2
    if x["am"] >= 220:
        sc -= 3; p["220"] = -3
    if x["stk"] >= 3:
        sc -= hot_w; p["hot"] = -hot_w
    tot = base + max(-6, min(6, sc))
    return (tot, p) if parts else tot


# ---- stats
def st(bets):
    """bets: [(season, profit, stake)] -> dict n, w, units, roi, z, by season."""
    if not bets:
        return dict(n=0)
    ps = [b[1] * b[2] for b in bets]; stake = sum(b[2] for b in bets)
    flat = [b[1] for b in bets]
    m = sum(flat) / len(flat)
    sd = statistics.pstdev(flat) if len(flat) > 1 else 1.0
    by = defaultdict(list)
    for b in bets:
        by[b[0]].append(b[1])
    return dict(n=len(bets), w=sum(1 for b in bets if b[1] > 0), u=round(sum(ps), 2), roi=round(100 * sum(ps) / stake, 1),
                flat=round(100 * m, 1), z=round(m / (sd / math.sqrt(len(flat))), 2) if sd else 0.0,
                by={k: (len(v), round(100 * sum(v) / len(v), 1)) for k, v in sorted(by.items())})


def line(name, s):
    if not s or not s.get("n"):
        return f"{name}: none"
    by = " ".join(f"{k}:{n}/{r:+.1f}%" for k, (n, r) in s["by"].items())
    up = sum(1 for n, r in s["by"].values() if r > 0)
    return (f"{name}: {s['w']}-{s['n'] - s['w']} flat {s['flat']:+.1f}% z {s['z']:+.2f} | units {s['u']:+.2f} ROI {s['roi']:+.1f}%"
            f" | {by} | {up} of {len(s['by'])} up")


def in_seasons(r):
    return r["season"] in SEASONS
