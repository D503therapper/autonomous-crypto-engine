"""S1 / S2 (11/13): THE NHL MORNING GOALIE GUESS.
S1 - the open question from the 11/12 Blackhawks card (Colten Ellis named for the Sabres; Alex Lyon started): how right is
     sports_players.projected_starter on the 2nd night of a back-to-back, split by whether last night's starter was PULLED
     (our box row = the goalie who faced the most shots; pulled proxy: under 20 shots faced and 4+ goals) and by whether
     the real starter was a goalie with NO start in the team's last 10 (a third goalie - the Lyon case).
S2 - the morning SOURCE (Daily Faceoff's page, data/sports/nhl_goalies.json, read from the repo's history - the snapshot
     just before the 8 AM PT board, 16:00Z / 15:00Z in PDT) vs our own projection, when the source says only
     'unconfirmed' (sports_goalies.starter ignores those and falls to the projection): who is right more often?
Truth = the box score's goalie row (most shots faced) - the starter on all but the rare relief-faced-more game.
Input: snaps.txt (hash + commit time of every nhl_goalies.json commit, written by `git log` before this runs)."""
import csv, json, os, subprocess, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402  (chdir to the repo root)
import sports_data as sd  # noqa: E402
import sports_players as sp  # noqa: E402

rows = list(csv.DictReader(open("data/sports/players/nhl.csv")))
rows.sort(key=lambda r: r["start"])
for r in rows:
    r["sa"], r["ga"] = lib.num(r["sa"]) or 0, lib.num(r["ga"]) or 0
by_gt = {(r["gid"], r["team"]): r for r in rows}
by_team = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)


def b2b_nights():
    for t, rs in by_team.items():
        for i in range(1, len(rs)):
            cur, prev = rs[i], rs[i - 1]
            if cur["start"] < "2023-09-01":
                continue
            h = sp._hours(prev["start"], cur["start"])
            if h is None or h >= sp.PROJ_B2B_DAYS * 24:
                continue
            yield t, rs, i, cur, prev


out = []
res = defaultdict(lambda: [0, 0])
pp = defaultdict(Counter)
for t, rs, i, cur, prev in b2b_nights():
    guess = sp.projected_starter(rows, t, cur["start"])
    if not guess:
        continue
    pulled = prev["sa"] < 20 and prev["ga"] >= 4
    floor = f"{lib.season(cur['start'])}-09-01"
    seq = [r["player"] for r in rs[max(0, i - sp.PROJ_GAMES):i] if r["start"] >= floor]
    is_third = cur["player"] not in seq
    hit = guess == cur["player"]
    s = "2026" if cur["start"] >= "2026-09-01" else "2023-26"
    for k in (f"{s} all", f"{s} pulled last night" if pulled else f"{s} not pulled",
              f"{s} real starter a 3rd goalie (no start in last 10)" if is_third else f"{s} real starter in last 10"):
        res[k][0] += hit
        res[k][1] += 1
    pp[f"{s} {'pulled' if pulled else 'not pulled'}"]["the same goalie again" if cur["player"] == prev["player"] else "a different goalie"] += 1
out.append("S1 - the b2b 2nd-night projection (the other goalie) - right / nights")
for k in sorted(res):
    a, n = res[k]
    out.append(f"  {k:55s} {a:5d}/{n:5d} = {a / n:.1%}")
out.append("  who starts night 2: " + "; ".join(f"{k}: " + ", ".join(f"{b} {a}" for a, b in v.items()) for k, v in sorted(pp.items())))

# ---------------- S2: the morning source vs the projection
snaps = []
for line in open(os.path.join(lib.OUT, "snaps.txt")):
    if line.strip():
        h, t = line.split()
        snaps.append((t[:16], h))
snaps.sort()
lg = sd.load_games("nhl")
games = lg if isinstance(lg, dict) else {g["id"]: g for g in lg}
by_day = defaultdict(list)
for t, h in snaps:
    by_day[t[:10]].append((t, h))
cmp_ = Counter()
detail = []
for day, lst in sorted(by_day.items()):
    cut = f"{day}T15:00" if day < "2026-11-01" else f"{day}T16:00"      # the 8 AM PT board (PDT before 11/1)
    pre = [x for x in lst if x[0] <= cut]
    if not pre:
        continue
    t, h = pre[-1]
    try:
        d = json.loads(subprocess.run(["git", "show", f"{h}:data/sports/nhl_goalies.json"], capture_output=True,
                                      text=True).stdout)
    except ValueError:
        continue
    for gid, v in (d.get("games") or {}).items():
        g = games.get(gid)
        if not g or g.get("status") != "final" or g["start"][:10] < day:
            continue
        for side in ("home", "away"):
            s = v.get(side) or {}
            tid = str(g[side])
            real = by_gt.get((gid, tid))
            if not real or not s.get("name"):
                continue
            proj = sp.projected_starter(rows, tid, g["start"])
            src = s["name"]
            st = s.get("status") or "?"
            ok_src = sp._nm(src) == sp._nm(real["player"])
            ok_proj = proj is not None and sp._nm(proj) == sp._nm(real["player"])
            cmp_[(st, "source right")] += ok_src
            cmp_[(st, "projection right")] += ok_proj
            cmp_[(st, "n")] += 1
            if sp._nm(src) != sp._nm(proj or ""):
                cmp_[(st, "disagree n")] += 1
                cmp_[(st, "disagree: source right")] += ok_src
                cmp_[(st, "disagree: projection right")] += ok_proj
                if st == "unconfirmed":
                    detail.append(f"{g['start'][:10]} {g.get(side + '_name')}: source {src} / ours {proj} / real {real['player']}")
out.append("")
out.append(f"S2 - the source's name at the last snapshot before the 8 AM PT board ({len(by_day)} days, {min(by_day)}..{max(by_day)})")
for st in sorted({k[0] for k in cmp_}):
    n = cmp_[(st, "n")]
    dn = cmp_[(st, "disagree n")]
    out.append(f"  status {st:12s} n {n:4d}: source right {cmp_[(st, 'source right')] / n:.1%}, our projection right "
               f"{cmp_[(st, 'projection right')] / n:.1%} | they disagree on {dn}: source right "
               f"{cmp_[(st, 'disagree: source right')]}, projection right {cmp_[(st, 'disagree: projection right')]}")
out.append("  the unconfirmed disagreements:")
out += ["    " + x for x in detail]
open(os.path.join(lib.OUT, "s1_s2_out.txt"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
