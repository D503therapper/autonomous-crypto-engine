"""THE HALVES STUDY: first halves, second halves and baseball's first 5 innings, from 10 seasons of period scores.

For every real final with period-by-period scores and a closing line, per sport:
  - how much of a team's pregame edge shows up in the first half (or first 5 innings) vs the second half:
        first-half margin ~ share_1h * pregame expected margin (+ noise sd_1h), same for the second half
  - how often the first-half leader wins the game, how often baseball's first 5 innings end tied
This is the groundwork for first-half and first-5-innings bets: those only go on the board once this study, checked
against real first-half lines, shows it can beat them. Saved to data/sports/halves.json every time new scores come in."""
import json
import math
import os

import sports_comeback as sc
import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "halves.json")
FIRST = {"nfl": 2, "ncaaf": 2, "nba": 2, "ncaab": 1, "mlb": 5, "nhl": 1}   # periods in the 1st half / first 5 / 1st period
NAME = {"mlb": "first 5 innings", "nhl": "1st period"}


def rows(games, league):
    """[(pregame expected margin (home), first-part margin, rest margin, home won)] for real finals with scores + a line."""
    k = FIRST[league]
    out = []
    for g in sm.finals(games, league):
        h, a = sc._ints(g.get("ls_home")), sc._ints(g.get("ls_away"))
        p = sm.market_p(g)
        if p is None or len(h) < k or len(a) < k:
            continue
        try:
            total = int(g["home_score"]) - int(g["away_score"])
        except (TypeError, ValueError):
            continue
        mu0 = sc.SIGMA[league] * sc.phi_inv(p)
        m1 = sum(h[:k]) - sum(a[:k])
        out.append((mu0, m1, total - m1, 1 if total > 0 else 0))     # rest of the game from the final score
    return out


def _fit(pairs):
    """y ~ share * x: (share, sd of what's left)."""
    sxx = sum(x * x for x, _ in pairs)
    share = sum(x * y for x, y in pairs) / sxx if sxx else 0.0
    sd_ = math.sqrt(sum((y - share * x) ** 2 for x, y in pairs) / max(1, len(pairs)))
    return round(share, 3), round(sd_, 2)


def study(games, path=PATH):
    out = {}
    for lg in FIRST:
        rs = rows(games, lg)
        if len(rs) < 200:
            out[lg] = {"games": len(rs)}
            continue
        s1, sd1 = _fit([(mu, m1) for mu, m1, _, _ in rs])
        s2, sd2 = _fit([(mu, m2) for mu, _, m2, _ in rs])
        led = [(m1, won) for _, m1, _, won in rs if m1 != 0]
        out[lg] = {"games": len(rs), "share_1h": s1, "sd_1h": sd1, "share_2h": s2, "sd_2h": sd2,
                   "leader_wins": round(sum((m1 > 0) == (won == 1) for m1, won in led) / max(1, len(led)), 3),
                   "tied_1h": round(sum(m1 == 0 for _, m1, _, _ in rs) / len(rs), 3)}
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return out


def summary(st):
    parts = []
    for lg, v in st.items():
        if "share_1h" not in v:
            parts.append(f"{lg} {v['games']} games (not enough yet)")
            continue
        first = NAME.get(lg, "1st half")
        parts.append(f"{lg} {v['games']} games: {first} gets {v['share_1h']:.0%} of the edge (sd {v['sd_1h']}), "
                     f"2nd {v['share_2h']:.0%}; {first} leader wins {v['leader_wins']:.0%}, tied {v['tied_1h']:.0%}")
    return "halves study: " + "; ".join(parts)


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}
