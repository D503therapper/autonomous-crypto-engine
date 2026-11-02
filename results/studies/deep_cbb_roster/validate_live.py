"""Does the LIVE code (sports_ncaab_roster.top_out / tin_m) flag the same sides as the study (s7 / s5b)? Every team side
of 2024-25 and 2025-26 regular-season games with a study flag known, compared one by one."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table  # noqa: E402
from lib import load_box, ROOT  # noqa: E402
from collections import defaultdict
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd  # noqa: E402
import sports_ncaab_roster as nr  # noqa: E402

games = sd.load_games()
box, _, _ = load_box()
tb = [x for x in table() if x["stype"] == "2" and x["season"] in (2024, 2025)]
order = defaultdict(list)
for x in tb:
    order[(x["season"], x["team"])].append(x)
agree = dis = unk_live = unk_study = 0
ex = []
for (s, t), xs in order.items():
    xs.sort(key=lambda x: x["start"])
    for i, x in enumerate(xs):
        st = x["f"].get("stars")
        study = None
        if st and i:
            b = (box.get(xs[i - 1]["id"]) or {}).get(t)
            if b is not None:
                study = st[0] not in b or b[st[0]][0] <= 0
        live = nr.top_out(games, t, x["start"])
        lv = None if live is None else live["out"]
        if study is None and lv is None:
            continue
        if study is None:
            unk_study += 1
        elif lv is None:
            unk_live += 1
        elif study == lv:
            agree += 1
        else:
            dis += 1
            if len(ex) < 5:
                ex.append((x["id"], x["name"], study, live))
print(f"top_out: agree {agree}, disagree {dis}, live unknown (study known) {unk_live}, study unknown (live known) {unk_study}")
for e in ex:
    print("  ", e)
