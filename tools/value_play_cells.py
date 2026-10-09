"""THE 10/9 VALUE-PLAY STUDY, part 1 - slices (usage: python tools/value_play_cells.py all_rows.jsonl).
Clean cells, train (2023-24) vs blind test (2025-26), flat 1u, with per-season units."""
import json, sys
from collections import defaultdict
rows = [json.loads(l) for l in open(sys.argv[1])]
plays = [r for r in rows if r["kind"] == "play" and r["result"] in ("won", "lost", "push")]
TR = lambda r: r["date"] < "2025-01-01"   # noqa: E731


def pnl(r):
    return (r["dec"] - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def fmt(rs):
    n = len(rs)
    if not n:
        return "n=0"
    u = sum(pnl(r) for r in rs)
    w = sum(r["result"] == "won" for r in rs)
    seas = defaultdict(float)
    for r in rs:
        seas[season(r["date"])] += pnl(r)
    s = " ".join(f"{k[2:]}:{v:+.0f}" for k, v in sorted(seas.items()))
    return f"{w}-{n - w - sum(r['result'] == 'push' for r in rs)} n={n} {u:+.1f}u {u / n * 100:+.1f}% [{s}]"


CELLS = {
    "every value play": lambda r: True,
    "spread plays (any sport)": lambda r: r["market"] == "spread",
    "  ncaab spreads": lambda r: r["market"] == "spread" and r["league"] == "ncaab",
    "  nfl/nba/ncaaf spreads": lambda r: r["market"] == "spread" and r["league"] != "ncaab",
    "moneyline plays": lambda r: r["market"] == "ml",
    "  ml favorites -150..-130": lambda r: r["market"] == "ml" and r["odds"] <= -130,
    "  ml favorites -129..-101": lambda r: r["market"] == "ml" and -129 <= r["odds"] <= -101,
    "  ml dogs (dog gate)": lambda r: r["market"] == "ml" and r["odds"] >= 100,
    "    ncaab dogs": lambda r: r["odds"] >= 100 and r["league"] == "ncaab",
    "    nhl dogs": lambda r: r["odds"] >= 100 and r["league"] == "nhl",
    "    football dogs": lambda r: r["odds"] >= 100 and r["league"] in ("nfl", "ncaaf"),
    "  ml favs by sport: nhl": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["league"] == "nhl",
    "  ml favs: nba": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["league"] == "nba",
    "  ml favs: ncaab": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["league"] == "ncaab",
    "  ml favs: mlb": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["league"] == "mlb",
    "  ml favs: nfl+ncaaf": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["league"] in ("nfl", "ncaaf"),
    "  ml favs own edge <3%": lambda r: r["market"] == "ml" and r["odds"] < 0 and (r["edge_own"] or 0) < 0.03,
    "  ml favs own edge 3-6%": lambda r: r["market"] == "ml" and r["odds"] < 0 and 0.03 <= (r["edge_own"] or 0) < 0.06,
    "  ml favs own edge 6-10%": lambda r: r["market"] == "ml" and r["odds"] < 0 and 0.06 <= (r["edge_own"] or 0) < 0.10,
    "  ml favs own edge 10%+": lambda r: r["market"] == "ml" and r["odds"] < 0 and (r["edge_own"] or 0) >= 0.10,
    "  ml favs p 53-56 (value tier)": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["p"] < 0.56,
    "  ml favs p 56-60": lambda r: r["market"] == "ml" and r["odds"] < 0 and 0.56 <= r["p"] < 0.60,
    "  ml favs p 60+": lambda r: r["market"] == "ml" and r["odds"] < 0 and r["p"] >= 0.60,
    "  ml hockey fav w_p (weighed)": lambda r: r["market"] == "ml" and r["league"] == "nhl" and r["w_p"] is not None,
    "rank 1": lambda r: r["rank"] == 1, "rank 2": lambda r: r["rank"] == 2, "rank 3+": lambda r: r["rank"] >= 3,
    "playoffs": lambda r: str(r["stype"]) == "3",
}
print(f"{'cell':34} | TRAIN 2023-24 {'':40} | TEST 2025-26 (blind)")
for name, f in CELLS.items():
    tr = [r for r in plays if TR(r) and f(r)]
    te = [r for r in plays if not TR(r) and f(r)]
    print(f"{name:34} | {fmt(tr):54} | {fmt(te)}")
print()
for kind in ("lock", "dog", "play"):
    rs = [r for r in rows if r["kind"] == kind and r["result"] in ("won", "lost", "push")]
    print(f"{kind:6} train {fmt([r for r in rs if TR(r)])} | test {fmt([r for r in rs if not TR(r)])}")
days = {r["date"] for r in rows}
print("board days with a unit pick:", len(days), " train", sum(d < "2025-01-01" for d in days), " test", sum(d >= "2025-01-01" for d in days))
print("plays per day with plays:", round(len(plays) / len({r['date'] for r in plays}), 2))
