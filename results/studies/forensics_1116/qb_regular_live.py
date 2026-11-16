"""11/16 FABLE: every football pick since 10/25 whose card listed a QB out (ours or theirs) - was he the last game's
starter (the old 'starting QB' test), the season's regular (the 11/16 test), or neither (a real backup)?"""
import json, re, sys
sys.path.insert(0, '.')
import sports, sports_players as sp, sports_data as sd, sports_absences as sa

cache = sp.load()
games = sd.load_games()
picks = json.load(open('data/sports/picks.json'))
for pk in picks:
    if pk['date'] < '2026-10-25' or pk.get('kind') in sports.PARLAY_KINDS:
        continue
    for l in pk.get('legs') or []:
        lg = l.get('league')
        if lg not in ('nfl', 'ncaaf'):
            continue
        g = games.get(l['game_id'])
        if not g:
            continue
        me, op = (g['home'], g['away']) if l['side'] == 'home' else (g['away'], g['home'])
        for tag, team, key in (('OURS', me, 'outs'), ('THEIRS', op, 'opp_outs')):
            for n in l.get(key) or []:
                if '(QB)' not in n:
                    continue
                name = n.split(' (')[0]
                rows = [r for r in cache[lg] if r['team'] == team]
                last = sp.last_starter(rows, team, g['start'])
                reg = sp.qb_regular(rows, team, g['start'])
                cnt = sp.qb_starts(rows, team, g['start'])[0]
                m = lambda a, b: bool(a and b and (sp._nm(a) == sp._nm(b) or sa.match(a, {sa._nm(b)})))
                kind = ('the last starter' if m(name, last) else f'THE REGULAR ({cnt.get(reg)} starts) - read as a backup till 11/15' if m(name, reg) and cnt.get(reg, 0) >= sp.QB_REGULAR_MIN
                        else 'a backup')
                u = sports.leg_units(pk, l) or 0
                print(f"{pk['date'][5:]} {pk['kind']:5s} u={u} {l['team']:16s} {l['odds']:>5} {l.get('result') or pk['status']:5s} {tag} QB out: {name:22s} -> {kind} | starts {cnt}")
