"""11/16 FABLE - WHY WE LOSE: the injury names each posted pick carried (ours out / theirs out) against the box score of
the game - a man the card said was OUT who PLAYED (stale), and in the NBA a top-3 minutes man of either side who was
NOT on the card's out list and did NOT play (a scratch after posting / a missed injury)."""
import json, re, sys, collections
sys.path.insert(0, '.')
import sports, sports_roster as sr, sports_data as sd

FROM = sys.argv[1] if len(sys.argv) > 1 else '2026-10-25'
picks = json.load(open('data/sports/picks.json'))
box = {}
for lg in ('nba', 'nfl', 'nhl', 'ncaaf', 'ncaab'):
    rows = sr.load(lg, [2026])
    by = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in rows:
        try:
            st = json.loads(r.get('stats') or '{}')
        except ValueError:
            st = {}
        mins = st.get('minutes')
        played = True
        if lg in ('nba', 'ncaab'):
            try:
                played = float(mins or 0) > 0
            except ValueError:
                played = False
            by[r['gid']][str(r['team'])][r['player']] = float(mins or 0) if played else 0.0
        else:
            by[r['gid']][str(r['team'])][r['player']] = 1.0
    box[lg] = by
games = sd.load_games()


def plain(n):
    return re.sub(r"\s*\(.*?\)\s*$", "", n).replace(".", "").lower().strip()


def top3(lg, team, before):
    tot = collections.Counter()
    gs = sorted((g for g in box[lg] if str(team) in box[lg][g] and (games.get(g) or {}).get('start', '') < before),
                key=lambda g: games[g]['start'])[-5:]
    for g in gs:
        for n, m in box[lg][g][str(team)].items():
            tot[n] += m
    return [n for n, _ in tot.most_common(3)]


T = collections.Counter()
for pk in picks:
    if pk['date'] < FROM or pk.get('kind') in sports.PARLAY_KINDS:
        continue
    for l in pk.get('legs') or []:
        lg = l.get('league')
        g = games.get(l.get('game_id') or '')
        if lg not in box or not g or g['id'] not in box[lg]:
            continue
        u = sports.leg_units(pk, l) or 0
        res = l.get('result') or pk.get('status')
        me, op = (g['home'], g['away']) if l['side'] == 'home' else (g['away'], g['home'])
        notes = []
        for tag, team, key in (('OURS', me, 'outs'), ('THEIRS', op, 'opp_outs')):
            played = {plain(n): m for n, m in box[lg][g['id']].get(str(team), {}).items() if m > 0}
            for n in l.get(key) or []:
                if plain(n) in played:
                    notes.append(f"{tag} listed out but PLAYED: {n}" + (f" ({played[plain(n)]:.0f} min)" if lg == 'nba' else ''))
            if lg == 'nba':
                listed = {plain(n) for n in (l.get(key) or [])} | {plain(n) for n in (l.get('on_report') or [])}
                for n in top3(lg, team, g['start']):
                    if plain(n) not in played and plain(n) not in listed:
                        notes.append(f"{tag} top-3 minutes man NOT on the card and did NOT play: {n}")
        bad_for_us = any(x.startswith('THEIRS listed out but PLAYED') or x.startswith('OURS top-3') for x in notes)
        T[('stale against us' if bad_for_us else 'stale other' if notes else 'clean', 'unit' if u else 'lean', res)] += 1
        if notes:
            print(f"{pk['date'][5:]} {pk['kind']:5s} u={u} {lg:5s} {l['team']:14s} {l['odds']:>5} {res}")
            for x in notes:
                print('      ', x)
for k, v in sorted(T.items()):
    print(k, v)
