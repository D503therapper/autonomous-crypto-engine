"""THE 10/9 VALUE-PLAY STUDY, part 2 - candidate rules (usage: python tools/value_play_rules.py "replay_*.jsonl" [extra]).
Candidate value-play rules: each is a KEEP filter on the replay's value plays. Chosen on TRAIN (2023-01..2024-12),
graded blind on TEST (2025-01..2026-09). Flat 1u per play (the ½u system scales it). Counts every cell tried."""
import json, sys, glob
from collections import defaultdict

rows = []
for p in sorted(glob.glob(sys.argv[1])):
    with open(p) as f:
        rows += [json.loads(l) for l in f if l.strip()]
plays = [r for r in rows if r["kind"] == "play" and r["result"] in ("won", "lost", "push")]
TRAIN = lambda r: r["date"] < "2025-01-01"                                              # noqa: E731
TEST = lambda r: r["date"] >= "2025-01-01"                                              # noqa: E731


def pnl(r):
    return (r["dec"] - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def stat(rs):
    n = len(rs)
    u = sum(pnl(r) for r in rs)
    seas = defaultdict(float)
    for r in rs:
        seas[season(r["date"])] += pnl(r)
    up = sum(v > 0 for v in seas.values())
    return n, u, (u / n * 100 if n else 0.0), up, len(seas)


def fmt(rs):
    n, u, roi, up, ns = stat(rs)
    return f"n={n:4d} {u:+7.1f}u {roi:+6.1f}% {up}/{ns} seasons up"


day_n = defaultdict(int)
for r in plays:
    day_n[r["date"]] += 1

RULES = {
    "as is (every value play)": lambda r: True,
    "rank 1 only": lambda r: r["rank"] == 1,
    "rank <= 2": lambda r: r["rank"] <= 2,
    "rank <= 3": lambda r: r["rank"] <= 3,
    "dogs only": lambda r: r["odds"] >= 100,
    "favorites only": lambda r: r["odds"] < 0,
    "moneyline only": lambda r: r["market"] == "ml",
    "spreads only": lambda r: r["market"] == "spread",
    "own edge >= 3%": lambda r: (r["edge_own"] or 0) >= 0.03,
    "own edge >= 5%": lambda r: (r["edge_own"] or 0) >= 0.05,
    "own edge >= 8%": lambda r: (r["edge_own"] or 0) >= 0.08,
    "own read agrees": lambda r: r["own_agrees"],
    "dog gate dogs only": lambda r: r["odds"] >= 100 and r["dog_gate"],
    "proven-only dogs dropped": lambda r: not (r["odds"] >= 100 and not r["dog_gate"]),
    "dog score >= 6 (dogs) / favs kept": lambda r: r["odds"] < 0 or (r["dog_score"] or 0) >= 6,
    "no college hoops": lambda r: r["league"] != "ncaab",
    "no college football": lambda r: r["league"] != "ncaaf",
    "no hockey": lambda r: r["league"] != "nhl",
    "no NBA": lambda r: r["league"] != "nba",
    "no MLB": lambda r: r["league"] != "mlb",
    "no NFL": lambda r: r["league"] != "nfl",
    "pros only": lambda r: r["league"] in ("nfl", "nba", "nhl", "mlb"),
    "college only": lambda r: r["league"] in ("ncaab", "ncaaf"),
    "price -150..+129 only": lambda r: r["odds"] < 130,
    "price +100..+169 dogs only": lambda r: 100 <= r["odds"] < 170,
    "no dogs past +170": lambda r: r["odds"] < 170,
    "p >= 55% (favs) or dog": lambda r: r["odds"] >= 100 or r["p"] >= 0.55,
    "lock-grade favs (56%+) or dog": lambda r: r["odds"] >= 100 or r["lock_ok"],
    "regular season only": lambda r: str(r["stype"]) == "2",
    "days with <= 2 plays": lambda r: day_n[r["date"]] <= 2,
    "days with <= 3 plays": lambda r: day_n[r["date"]] <= 3,
    "rank<=2 and own edge>=3%": lambda r: r["rank"] <= 2 and (r["edge_own"] or 0) >= 0.03,
    "dogs with dog gate, rank<=2": lambda r: r["odds"] >= 100 and r["dog_gate"] and r["rank"] <= 2,
    "favs only, own edge >= 3%": lambda r: r["odds"] < 0 and (r["edge_own"] or 0) >= 0.03,
    "favs only, no hockey": lambda r: r["odds"] < 0 and r["league"] != "nhl",
    "dogs only, no college": lambda r: r["odds"] >= 100 and r["league"] not in ("ncaab", "ncaaf"),
}
if len(sys.argv) > 2 and sys.argv[2] == "extra":
    import value_play_extra_rules as extra_rules
    RULES.update(extra_rules.RULES)

print(f"{len(RULES)} cells tried. TRAIN {sum(TRAIN(r) for r in plays)} plays, TEST {sum(TEST(r) for r in plays)} plays")
print(f"{'rule':38} | {'TRAIN (2023-24)':42} | {'TEST (2025-26, blind)':42} | dropped(train)")
out = []
for name, f in RULES.items():
    tr = [r for r in plays if TRAIN(r) and f(r)]
    te = [r for r in plays if TEST(r) and f(r)]
    dr = [r for r in plays if TRAIN(r) and not f(r)]
    out.append((stat(tr)[2], name, tr, te, dr))
for roi, name, tr, te, dr in sorted(out, key=lambda x: -x[0]):
    print(f"{name:38} | {fmt(tr)} | {fmt(te)} | {fmt(dr)}")
