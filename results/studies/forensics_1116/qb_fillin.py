"""11/16 FABLE - WHY WE LOSE: how often is the QB the engine reads the man who really starts? Every NFL / college
football team-game on file (the box scores' top passer = the starter), walk-forward:
  last starter      the old rule (to 11/15): whoever started the last game
  settled           the 11/15 night rule: the same man started the last 2
  settled REGULAR   settled AND no other QB has more starts for the team this season
  settled FILL-IN   settled, but another QB has more starts this season (the Ravens' Joe Fagnano behind Lamar Jackson's 4)
For each: how often that man started the game."""
import sys, collections
sys.path.insert(0, '.')
import sports_players as sp

cache = sp.load()


def season(d):
    return int(d[:4]) - (1 if d[5:7] < '07' else 0)


for lg in ('nfl', 'ncaaf'):
    rows = sorted(cache[lg], key=lambda r: r['start'])
    by_team = collections.defaultdict(list)          # team -> [(start, gid, player)] one a game
    seen = set()
    for r in rows:
        if (r['gid'], r['team']) in seen:
            continue
        seen.add((r['gid'], r['team']))
        by_team[r['team']].append((r['start'], r['gid'], r['player']))
    T = collections.defaultdict(lambda: [0, 0])
    H = collections.defaultdict(lambda: [0, 0])
    for team, gs in by_team.items():
        for i, (start, gid, actual) in enumerate(gs):
            se = season(start)
            prev = [x for x in gs[:i] if season(x[0]) == se]
            if not prev:
                continue
            last = prev[-1][2]
            half = 'train' if se <= 2022 else 'held'

            def add(k, ok):
                T[k][0] += ok
                T[k][1] += 1
                H[(k, half)][0] += ok
                H[(k, half)][1] += 1
            add('last starter (the old rule)', actual == last)
            if len(prev) >= 2 and prev[-2][2] == last:
                add('settled (the same man the last 2)', actual == last)
                cnt = collections.Counter(x[2] for x in prev)
                top = max(cnt.values())
                if cnt[last] >= top:
                    add('  settled REGULAR (most starts this season)', actual == last)
                else:
                    add('  settled FILL-IN (another QB has more starts)', actual == last)
                    reg = max(cnt, key=lambda n: cnt[n])
                    add('     ...the regular came back', actual == reg)
                    if cnt[last] == 2:
                        add('     fill-in with exactly 2 starts', actual == last)
                    else:
                        add('     fill-in with 3+ starts', actual == last)
            else:
                add('NOT settled (a change in the last 2)', actual == last)
    print(f"== {lg}: the man the rule names started the game")
    for k, (a, n) in T.items():
        t, h = H[(k, 'train')], H[(k, 'held')]
        print(f"  {k:52s} {a:5d} of {n:5d} = {a / n:6.1%} | 2018-22 {t[0] / max(1, t[1]):6.1%} on {t[1]} | 2023-26 {h[0] / max(1, h[1]):6.1%} on {h[1]}")
