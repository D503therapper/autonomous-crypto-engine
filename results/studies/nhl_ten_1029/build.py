"""10/29 TEN HOCKEY STUDIES - the study table. Every NHL regular-season final 2016-27 with a closing moneyline, the ACTUAL
starting goalies (players/nhl.csv - the G row per team-game with the most shots faced), and features known BEFORE the game:
goalie season-to-date save % (shrunk), #1 / backup, who started the team's LAST game (night 1 of a b2b), goalie starts
in a row, goalie career save % vs this opponent, team last-5 record + goal differential, season record + goal
differential, win / loss streaks, head-to-head this season, b2b with / without a move, the engine's live read (the line +
b2b / rest, fit blind on the train seasons). Writes rows.json here."""
import csv, glob, json, os, math
from collections import defaultdict, deque, Counter
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
OUT = os.path.dirname(os.path.abspath(__file__))
LG_SV = 0.905
SHRINK = 300.0   # shots: a goalie's save % shrunk toward the league number by ~10 starts' worth of shots


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{str(y + 1)[2:]}" if m >= 9 else f"{y - 1}-{str(y)[2:]}"


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def novig(oh, oa):
    ph, pa = 1 / dec(oh), 1 / dec(oa)
    return ph / (ph + pa)


def t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


goalie = {}   # (gid, team) -> (player, sa, ga)
for r in csv.DictReader(open(f'{ROOT}/data/sports/players/nhl.csv')):
    if r.get('role', 'G') == 'G':
        k = (r['gid'], r['team'])
        sa, ga = float(r['sa'] or 0), float(r['ga'] or 0)
        if k not in goalie or sa > goalie[k][1]:
            goalie[k] = (r['player'], sa, ga)

games = []
for f in sorted(glob.glob(f'{ROOT}/data/sports/games/nhl/*.csv')):
    for g in csv.DictReader(open(f)):
        if g['status'] == 'final' and g.get('stype') == '2' and g['home_score'] != '' and g['ml_home'] != '' and g['ml_away'] != '':
            games.append(g)
games.sort(key=lambda g: g['start'])

last = {}                                            # team -> (time, tzo, start, home?, goalie)
starts = defaultdict(lambda: deque(maxlen=20))       # team -> last 20 starters
gsv_season = {}                                      # (goalie, season) -> [sa, ga, starts]
gsv_opp = defaultdict(lambda: [0.0, 0.0, 0])         # (goalie, opp) -> career sa, ga, starts
g_streak = defaultdict(int)                          # goalie -> consecutive starts for his team
form = defaultdict(lambda: deque(maxlen=5))          # team -> last 5 (won, gd)
played = defaultdict(int); wins = defaultdict(int); gd = defaultdict(int)
streak = defaultdict(int)                            # team -> +n wins / -n losses in a row
h2h = {}                                             # (season, a, b) -> last meeting (winner, margin)
rows = []
for g in games:
    try:
        oh, oa = int(float(g['ml_home'])), int(float(g['ml_away']))
        hs, as_ = int(g['home_score']), int(g['away_score'])
    except ValueError:
        continue
    h, a = g['home'], g['away']
    tm = t(g['start'])
    tz = float(g.get('tzo') or 0)
    ssn = season(g['start'])
    gh, ga_ = goalie.get((g['id'], h)), goalie.get((g['id'], a))

    def rest(team):
        return min(7.0, (tm - last[team][0]).total_seconds() / 86400) if team in last and season(last[team][2]) == ssn else 7.0

    def backup(team, name):
        xs = list(starts[team])
        if len(xs) < 10 or not name:
            return None
        return xs.count(name) / len(xs) < 0.4

    def n1(team):
        xs = list(starts[team])[-10:]
        if len(xs) < 6:
            return None
        c = Counter(xs).most_common(2)
        return None if len(c) > 1 and c[0][1] == c[1][1] else c[0][0]

    def svs(name):
        """season-to-date save %, shrunk; None under 5 starts"""
        x = gsv_season.get((name, ssn))
        if not x or x[2] < 5:
            return None
        return (x[0] - x[1] + SHRINK * LG_SV) / (x[0] + SHRINK)

    def svo(name, opp):
        x = gsv_opp.get((name, opp))
        if not x or x[2] < 3:
            return None
        return (x[0] - x[1]) / x[0] if x[0] else None

    def l5(team):
        xs = list(form[team])
        if len(xs) < 5:
            return None, None
        return sum(w for w, _ in xs), sum(d for _, d in xs)

    def night1_starter(team):
        return last[team][4] if team in last and season(last[team][2]) == ssn else None

    rh, ra = rest(h), rest(a)
    try:
        oho, oao = int(float(g['ml_home_open'])), int(float(g['ml_away_open']))
    except (ValueError, TypeError):
        oho = oao = None
    l5w_h, l5d_h = l5(h); l5w_a, l5d_a = l5(a)
    k1 = (ssn, h, a) if h < a else (ssn, a, h)
    prev = h2h.get(k1)
    row = dict(id=g['id'], start=g['start'], season=ssn, month=g['start'][5:7], home=h, away=a, hn=g['home_name'], an=g['away_name'],
               oh=oh, oa=oa, oho=oho, oao=oao, hs=hs, as_=as_, hw=int(hs > as_), mkt_h=novig(oh, oa),
               rest_h=rh, rest_a=ra, b2b_h=int(rh <= 1.2), b2b_a=int(ra <= 1.2),
               # b2b with a move: played somewhere else yesterday (the road team yesterday, or home yesterday and road today)
               move_h=int(rh <= 1.2 and not (h in last and last[h][3])), move_a=int(ra <= 1.2 and a in last and last[a][1] != tz),   # the road team crossed a time zone overnight
               tzmove_a=abs(tz - last[a][1]) if a in last else 0.0,
               gk_h=gh[0] if gh else None, gk_a=ga_[0] if ga_ else None,
               bk_h=backup(h, gh[0] if gh else None), bk_a=backup(a, ga_[0] if ga_ else None),
               n1_h=(gh[0] == n1(h)) if gh and n1(h) else None, n1_a=(ga_[0] == n1(a)) if ga_ and n1(a) else None,
               n1name_h=n1(h), n1name_a=n1(a),
               night1_h=night1_starter(h), night1_a=night1_starter(a),
               svs_h=svs(gh[0]) if gh else None, svs_a=svs(ga_[0]) if ga_ else None,
               gst_h=gsv_season.get((gh[0], ssn), [0, 0, 0])[2] if gh else 0, gst_a=gsv_season.get((ga_[0], ssn), [0, 0, 0])[2] if ga_ else 0,
               svo_h=svo(gh[0], a) if gh else None, svo_a=svo(ga_[0], h) if ga_ else None,
               grun_h=g_streak.get(gh[0], 0) if gh else 0, grun_a=g_streak.get(ga_[0], 0) if ga_ else 0,
               l5w_h=l5w_h, l5d_h=l5d_h, l5w_a=l5w_a, l5d_a=l5d_a,
               gp_h=played[(h, ssn)], gp_a=played[(a, ssn)],
               wp_h=wins[(h, ssn)] / played[(h, ssn)] if played[(h, ssn)] else None,
               wp_a=wins[(a, ssn)] / played[(a, ssn)] if played[(a, ssn)] else None,
               gd_h=gd[(h, ssn)], gd_a=gd[(a, ssn)],
               stk_h=streak[(h, ssn)], stk_a=streak[(a, ssn)],
               prev_win_h=(None if prev is None else int(prev[0] == h)), prev_margin=(None if prev is None else prev[1]))
    rows.append(row)
    # update state AFTER the row
    last[h] = (tm, tz, g['start'], True, gh[0] if gh else None); last[a] = (tm, tz, g['start'], False, ga_[0] if ga_ else None)
    for team, gk, allowed_shots, allowed_goals, opp in ((h, gh, None, as_, a), (a, ga_, None, hs, h)):
        if gk:
            starts[team].append(gk[0])
            x = gsv_season.setdefault((gk[0], ssn), [0.0, 0.0, 0]); x[0] += gk[1]; x[1] += gk[2]; x[2] += 1
            y = gsv_opp[(gk[0], opp)]; y[0] += gk[1]; y[1] += gk[2]; y[2] += 1
            # consecutive starts: reset every other goalie of this team
            for other in set(starts[team]):
                if other != gk[0]:
                    g_streak[other] = 0
            g_streak[gk[0]] += 1
    form[h].append((int(hs > as_), hs - as_)); form[a].append((int(as_ > hs), as_ - hs))
    played[(h, ssn)] += 1; played[(a, ssn)] += 1
    wins[(h, ssn)] += int(hs > as_); wins[(a, ssn)] += int(as_ > hs)
    gd[(h, ssn)] += hs - as_; gd[(a, ssn)] += as_ - hs
    for team, won in ((h, hs > as_), (a, as_ > hs)):
        s = streak[(team, ssn)]
        streak[(team, ssn)] = (s + 1 if s > 0 else 1) if won else (s - 1 if s < 0 else -1)
    h2h[k1] = (h if hs > as_ else a, abs(hs - as_))

json.dump(rows, open(f'{OUT}/rows.json', 'w'))
print(len(rows), 'rows; seasons', sorted({r['season'] for r in rows}))
print('with both goalies', sum(1 for r in rows if r['gk_h'] and r['gk_a']), 'with open', sum(1 for r in rows if r['oho'] is not None))
