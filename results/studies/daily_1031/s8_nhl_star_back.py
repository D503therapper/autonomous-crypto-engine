"""Study 8 (10/31): NHL - THE TOP SCORER'S FIRST GAME BACK (never run for hockey; the NBA favorite version is the
10/22 built -3 'top-5 man back (fade)'). A team's top-2 scorer (points a game this season, 10+ games played, before
tonight) who missed its last 2+ games and is in tonight's lineup. Also: the team still WITHOUT him (2nd+ straight game
missed - the market's had a game to adjust) and the FIRST game he misses. Closing moneylines, dogs +100..+350 /
favorites -101..-150, vs every side in the same band. Box scores 2021-26: train 2021-22, held out 2023 / 2024 /
2025 / 2026 apart.
Look-ahead note: tonight's lineup comes from tonight's box score - live, a returning skater is known at the morning
skate / the official report (often after the 8 AM board), so a finding here would have to ride a late update."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2021, 2022), (2023, 2024, 2025, 2026)


def nhl_points(st, r):
    if (r.get("group") or "") == "goalies":
        return None
    try:
        return int(st.get("goals") or 0) + int(st.get("assists") or 0)
    except ValueError:
        return 0


box = lib.boxes("nhl", nhl_points)
games = lib.finals("nhl")
hist = defaultdict(list)        # (season, team) -> [set of players in each game, in order]
pts = defaultdict(lambda: defaultdict(lambda: [0, 0]))    # (season, team) -> pid -> [points, games]
cells = defaultdict(list)
for g in games:
    s = g["season"]
    b = box.get(g["id"])
    if not b:
        continue
    lines = {}
    for t in (g["home"], g["away"]):
        lines[t] = b.get(str(t)) or b.get(t)
    if not all(lines.values()):
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else None
        if not band:
            continue
        pr = lib.profit(won, lib.dec(o))
        cells[f"{band} | base (box scores on file)"].append((s, pr))
        h = hist[(s, team)]
        p = pts[(s, team)]
        tops = sorted(((v[0] / v[1], pid) for pid, v in p.items() if v[1] >= 10), reverse=True)[:2]
        if len(h) < 12 or not tops:
            continue
        tags = set()
        for _, pid in tops:
            in_now = pid in lines[team]
            miss = 0
            for gs in reversed(h):
                if pid in gs:
                    break
                miss += 1
            if in_now and miss >= 2:
                tags.add("top-2 scorer BACK after missing 2+")
            if not in_now and miss == 0:
                tags.add("top-2 scorer's FIRST game out")
            if not in_now and miss >= 1:
                tags.add("top-2 scorer still out (2nd+ game)")
        # the opponent's side of it
        ho, po = hist[(s, opp)], pts[(s, opp)]
        otops = sorted(((v[0] / v[1], pid) for pid, v in po.items() if v[1] >= 10), reverse=True)[:2]
        if len(ho) >= 12:
            for _, pid in otops:
                in_now = pid in lines[opp]
                miss = 0
                for gs in reversed(ho):
                    if pid in gs:
                        break
                    miss += 1
                if in_now and miss >= 2:
                    tags.add("vs a team getting its top-2 scorer BACK")
                if not in_now and miss == 0:
                    tags.add("vs a team on its top-2 scorer's FIRST game out")
        for tg in tags:
            cells[f"{band} | {tg}"].append((s, pr))
    for t in (g["home"], g["away"]):
        hist[(s, t)].append(set(lines[t]))
        for pid, v in lines[t].items():
            pts[(s, t)][pid][0] += v
            pts[(s, t)][pid][1] += 1
res = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(cells.items())}
lines_ = ["NHL TOP-2 SCORER BACK / OUT (12+ team games in, 10+ games played by the scorer)"]
lines_ += [lib.fmt(k, v) for k, v in res.items()]
txt = "\n".join(lines_)
print(txt)
open(os.path.join(lib.OUT, "s8_out.txt"), "w").write(txt + "\n")
json.dump(res, open(os.path.join(lib.OUT, "s8_out.json"), "w"), indent=1)
