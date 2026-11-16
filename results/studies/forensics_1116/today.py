"""11/16 FABLE: the games on the next boards (who's home, the prices)."""
import sys
sys.path.insert(0, '.')
import sports_data as sd

for lg in ('nfl',):
    g = sd.load_games(lg)
    for k, x in g.items():
        if x['start'][:10] in ('2026-11-16', '2026-11-17', '2026-11-18') and x['status'] != 'final':
            print({a: x.get(a) for a in ('id', 'start', 'home_name', 'away_name', 'ml_home', 'ml_away', 'neutral', 'status', 'spread_home')})
