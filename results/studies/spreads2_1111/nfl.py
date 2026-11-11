"""nflverse's public schedule file (games.csv: every NFL game 1999-2026 with the closing spread, total, rest, roof,
wind, division flag) - a plain public download into ~/.cache/d503_spreads2_1111/dl, never the repo.
   python nfl.py   (downloads if missing)"""
import csv, math, os, statistics, subprocess

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_spreads2_1111", "dl")
os.makedirs(DL, exist_ok=True)
P = os.path.join(DL, "games.csv")
URL = "https://" + "github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"


def fetch():
    if not (os.path.exists(P) and os.path.getsize(P) > 1_000_000):
        r = subprocess.run(["curl", "-sSL", "-o", P, "-w", "%{http_code} %{size_download}", URL], capture_output=True, text=True)
        print(r.stdout, r.stderr[:200])


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def games(reg_only=False):
    """[{season, week, date, home, away, m (home margin), hl (the home team's closing line, - = home favored), total,
    pts, div, hrest, arest, roof, wind, temp, neutral, reg, wd, hso / aso (the closing spread juice)}] - finished
    games with a closing spread."""
    fetch()
    out = []
    for r in csv.DictReader(open(P)):
        hs, as_, sl = _f(r["home_score"]), _f(r["away_score"]), _f(r["spread_line"])
        if hs is None or as_ is None or sl is None:
            continue
        reg = r["game_type"] == "REG"
        if reg_only and not reg:
            continue
        out.append({"gid": r["game_id"], "season": int(r["season"]), "week": int(r["week"]), "date": r["gameday"],
                    "home": r["home_team"], "away": r["away_team"], "m": hs - as_, "hl": -sl, "total": _f(r["total_line"]),
                    "pts": hs + as_, "div": r["div_game"] == "1", "hrest": _f(r["home_rest"]), "arest": _f(r["away_rest"]),
                    "roof": r["roof"], "wind": _f(r["wind"]), "temp": _f(r["temp"]), "neutral": r["location"] == "Neutral",
                    "reg": reg, "wd": r["weekday"], "hso": _f(r["home_spread_odds"]), "aso": _f(r["away_spread_odds"]),
                    "hml": _f(r["home_moneyline"]), "aml": _f(r["away_moneyline"]), "ot": r["overtime"] == "1",
                    "time": r["gametime"]})
    out.sort(key=lambda g: (g["date"], g["gid"]))
    return out


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def st(ps):
    """n, W-L, win %, ROI %, z for a list of profits on 1 (0 = push)."""
    n = len(ps)
    if not n:
        return "     0       -        -"
    w = sum(1 for x in ps if x > 0)
    l = sum(1 for x in ps if x < 0)
    m = sum(ps) / n
    sdv = statistics.pstdev(ps) if n > 1 else 0
    z = m / (sdv / math.sqrt(n)) if sdv else 0.0
    return f"{n:5d} {w:4d}-{l:<4d} {w / max(1, w + l) * 100:5.1f}% {m * 100:+6.1f}% z{z:+5.2f}"


def roi(ps):
    return sum(ps) / len(ps) * 100 if ps else float("nan")


def by_season(rows):
    """rows = [(season, profit)] -> (seasons up, seasons, 'yr n roi' text)."""
    by = {}
    for s, p in rows:
        by.setdefault(s, []).append(p)
    up = sum(1 for v in by.values() if sum(v) > 0)
    return up, len(by), " ".join(f"{k % 100:02d}:{roi(v):+.0f}({len(v)})" for k, v in sorted(by.items()))


class Out:
    def __init__(self, tag):
        self.tag, self.lines = tag, []

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.lines.append(s)

    def save(self):
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), self.tag + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


if __name__ == "__main__":
    g = games()
    print(len(g), g[0], g[-1])
    import collections
    print(sorted(collections.Counter(x["season"] for x in g).items()))
