"""11/4 AUDIT (the E Michigan +110 dog_play: its only reason "opponent missing key players: QB Angel Flores" - Flores had
ALREADY MISSED C Michigan's last game). Question: does a football starting QB (most pass attempts over the team's last 3
box scores - sports_absences.key_players' own pick) who is out AGAIN still leave the engine's own read too high, or
is the 'known' absence already in it? Box scores 2021-26 (sports_roster), the engine's own read replayed pre-game with
today's model weights (sports_model.replay + own_p), the no-vig close as the second check.
  fresh  = absent from this game's box, IN the previous game's box (the 10/2 study's case - the -3 / -8)
  known  = absent from this game's box AND from the previous game's box (the backup already started)
Usage: python results/studies/audit_1104/qb_known_out.py"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import sports_data as sd          # noqa: E402
import sports_model as sm         # noqa: E402
import sports_roster as sr        # noqa: E402

games = sd.load_games()
model = json.load(open(os.path.join(sd.DATA, "model.json")))


def passes(rs):
    out = {}
    for r in rs:
        try:
            st = json.loads(r.get("stats") or "{}")
        except ValueError:
            continue
        x = str(st.get("completions/passingAttempts") or "0")
        try:
            out[r["player"]] = float(x.split("/")[-1])
        except ValueError:
            pass
    return out


for lg in ("ncaaf", "nfl"):
    p = model["params"][lg]
    fin = sm.finals(games, lg)
    _, rows = sm.replay(fin, p["k"], p["hfa"], lg)
    pre = {g["id"]: (f, res) for g, f, res, _ in rows}
    box = defaultdict(lambda: defaultdict(list))          # team -> gid -> rows
    starts = {}
    for r in sr.load(lg):
        box[str(r["team"])][r["gid"]].append(r)
        starts[r["gid"]] = r["start"]
    cells = defaultdict(lambda: [0, 0.0, 0.0, 0])       # n, sum(result - own), sum(result - mkt), n with mkt
    by_season = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    for team, gm in box.items():
        seq = sorted(gm, key=lambda x: starts[x])
        for i in range(4, len(seq)):
            gid = seq[i]
            if gid not in pre or gid not in games:
                continue
            if starts[gid][:4] != starts[seq[i - 3]][:4]:
                continue                                     # (inside one season only)
            tot = defaultdict(float)
            for g_ in seq[i - 3:i]:
                for pl, n in passes(gm[g_]).items():
                    tot[pl] += n
            if not tot:
                continue
            qb = max(tot, key=tot.get)
            if any(r["player"] == qb for r in gm[gid]):
                continue                                     # he played
            prev_in = any(r["player"] == qb for r in gm[seq[i - 1]])
            kind = "fresh" if prev_in else "known"
            g = games[gid]
            side = "home" if str(g["home"]) == team else "away"
            f, res = pre[gid]
            own = sm.own_p(p, f)
            own = own if side == "home" else 1 - own
            y = res if side == "home" else 1 - res
            c = cells[kind]
            c[0] += 1
            c[1] += y - own
            mk = sm.market_p(g)
            if mk is not None:
                c[2] += y - (mk if side == "home" else 1 - mk)
                c[3] += 1
            by_season[kind][starts[gid][:4]][0] += 1
            by_season[kind][starts[gid][:4]][1] += y - own
    print(f"== {lg.upper()} - the team whose starting QB (last-3 top passer) did NOT play")
    for k in ("fresh", "known"):
        n, so, sk, nm = cells[k]
        if n:
            print(f"  {k:6} n={n:4}  result - OWN read {100 * so / n:+.1f} pts   result - no-vig close "
                  f"{(100 * sk / nm if nm else float('nan')):+.1f} pts (n={nm})")
            print("     by season (result - own):", {s: f"{100 * v / n_:+.1f} on {n_}" for s, (n_, v) in sorted(by_season[k].items())})
