"""The 11/3 KNOWLEDGE (A) facts on every college hoops side (the s7 dog view's exact construction - coaches, the
conference race, identity (off / def / turnover margin), availability (a regular out 4+ games, 2+ out of the last
game), the roster mix) -> {(game id, team): facts}, cached. Everything is known before tip (earlier games only)."""
import importlib.util
import os
import pickle
import sys
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
A_DIR = os.path.join(ROOT, "results/studies/cbb_knowledge_a")


def _load_a():
    spec = importlib.util.spec_from_file_location("cbbk_a_lib", os.path.join(A_DIR, "lib.py"))
    A = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)
    return A


def build():
    A = _load_a()
    pk = os.path.join(A.CACHE, "cbb_dog_expert_afacts.pkl")
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    sys.path.insert(0, ROOT)
    import sports_ncaab_coaches as nc
    rows_ = A.regular(A.rows())
    rows_.sort(key=lambda x: (x["start"], x["id"]))
    month = lambda x: x["start"][5:7]
    table = nc.load()
    for x in rows_:
        x["c"], x["oc"] = nc.state(x["team"], x["start"], table), nc.state(x["opp"], x["start"], table)
    stand = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for x in rows_:
        if not x["same_conf"] or not x["conf"]:
            continue
        tab = stand[(x["season"], x["conf"])]
        mine, theirs = tab[x["team"]], tab[x["opp"]]
        if len(tab) >= 6 and mine[0] + mine[1] >= 8 and theirs[0] + theirs[1] >= 8:
            lead = max(v[0] - v[1] for v in tab.values())
            x["gb"], x["ogb"] = (lead - (mine[0] - mine[1])) / 2, (lead - (theirs[0] - theirs[1])) / 2
        tab[x["team"]][0 if x["won"] else 1] += 1
    TB = A.teambox()
    score = {(x["id"], x["team"]): (x["pts"] + x["margin"]) / 2 for x in rows_}
    agg, lg, feat = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float)), {}
    for x in rows_:
        if x["season"] < 2021:
            continue
        s, tm, op = x["season"], x["team"], x["opp"]
        a, L = agg[(s, tm)], lg[s]
        if a["n"] >= 5 and L["n"] >= 200:
            feat[(x["id"], tm)] = {"off": 100 * a["pts"] / a["poss"] - 100 * L["pts"] / L["poss"],
                                   "def": 100 * a["opts"] / a["oposs"] - 100 * L["pts"] / L["poss"], "tom": (a["oto"] - a["to"]) / a["n"]}
        b = TB.get(x["id"])
        if b and tm in b and op in b and (x["id"], tm) in score and (x["id"], op) in score:
            me, th = b[tm], b[op]
            for d in (a, L):
                d["n"] += 1
                d["pts"] += score[(x["id"], tm)]
                d["poss"] += me["poss"]
                d["opts"] += score[(x["id"], op)]
                d["oposs"] += th["poss"]
                d["to"] += me["to"]
                d["oto"] += th["to"]
    for x in rows_:
        x["f"], x["of"] = feat.get((x["id"], x["team"])), feat.get((x["id"], x["opp"]))
    box = A.playerbox()
    by_team = defaultdict(list)
    for x in rows_:
        if x["season"] >= 2021:
            by_team[(x["season"], x["team"])].append(x)
    av = {}
    for (s, tm), xs in by_team.items():
        hist = []
        for x in xs:
            b = (box.get(x["id"]) or {}).get(tm)
            if len(hist) >= 5:
                mp = defaultdict(float)
                for hb in hist:
                    for pid, m in hb.items():
                        mp[pid] += m
                n = len(hist)
                regs = sorted(((v / n, pid) for pid, v in mp.items() if v / n >= 15), reverse=True)[:7]
                top = max(mp.items(), key=lambda kv: kv[1])[0]
                long_, out_last = 0, 0
                for _, pid in regs:
                    run = 0
                    for hb in reversed(hist):
                        if hb.get(pid, 0) > 0:
                            break
                        run += 1
                    if run >= 1:
                        out_last += 1
                    if run >= 4 and pid != top:
                        long_ += 1
                av[(x["id"], tm)] = (long_, out_last)
            if b is not None:
                hist.append({pid: v[0] for pid, v in b.items()})
    for x in rows_:
        x["av"], x["oav"] = av.get((x["id"], x["team"])), av.get((x["id"], x["opp"]))
    _dl = importlib.util.spec_from_file_location("lib", os.path.join(ROOT, "results/studies/deep_cbb_roster/lib.py"))
    DL = importlib.util.module_from_spec(_dl)
    _mine = sys.modules.get("lib")
    sys.modules["lib"] = DL
    _dl.loader.exec_module(DL)
    _spec = importlib.util.spec_from_file_location("deep_feat", os.path.join(ROOT, "results/studies/deep_cbb_roster/features.py"))
    FE = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(FE)
    if _mine is not None:
        sys.modules["lib"] = _mine
    F = FE.build()
    for x in rows_:
        f, of = F.get((x["id"], x["team"])), F.get((x["id"], x["opp"]))
        x["rm"] = (f.get("sf_tin"), f.get("sf_new")) if f and f.get("sf_n", 0) >= 10 else None
        x["orm"] = (of.get("sf_tin"), of.get("sf_new")) if of and of.get("sf_n", 0) >= 10 else None
    cut = {}
    for k in ("off", "def", "tom"):
        for s in sorted({x["season"] for x in rows_ if x["f"]}):
            v = sorted(x["f"][k] for x in rows_ if x["season"] == s and x["f"])
            cut[(k, s)] = (v[len(v) // 3], v[2 * len(v) // 3])
    hi = lambda x, k, w="f": bool(x[w]) and x[w][k] >= cut[(k, x["season"])][1]
    lo = lambda x, k, w="f": bool(x[w]) and x[w][k] <= cut[(k, x["season"])][0]
    late = lambda x: month(x) in ("01", "02", "03")
    out = {}
    for x in rows_:
        fm = month(x) in ("02", "03")
        bad = {
            "new_coach_late": bool(x["c"] and x["c"]["new"] and late(x)),
            "long_out": bool(x["av"] and x["av"][0] >= 1),
            "transfer_heavy_late": bool(x["rm"] and x["rm"][0] >= 0.28 and late(x)),
            "offense_first_late": bool(hi(x, "off") and not lo(x, "def") and late(x)),
            "race_dog": bool(x.get("gb") is not None and x["gb"] >= 5 and x["ogb"] <= 1 and fm and x["tier"] != "power"),
        }
        good = {
            "whole_vs_2out": bool(x["av"] and x["oav"] and x["av"][1] == 0 and x["oav"][1] >= 2),
            "def_first_vs_bad_off": bool(lo(x, "def") and not hi(x, "off") and lo(x, "off", "of")),
        }
        out[(x["id"], x["team"])] = {"bad": bad, "good": good, "nb": sum(bad.values()), "ng": sum(good.values()),
                                     "has_reads": bool(x["season"] >= 2021 and x["f"] and x["av"] is not None),
                                     "def_first": bool(lo(x, "def") and not hi(x, "off")),
                                     "off_first": bool(hi(x, "off") and not lo(x, "def")),
                                     "coach_new": bool(x["c"] and x["c"]["new"]), "tin": x["rm"][0] if x["rm"] else None,
                                     "new": x["rm"][1] if x["rm"] else None, "gb": x.get("gb"), "ogb": x.get("ogb"),
                                     "out_last": x["av"][1] if x["av"] else None, "o_out_last": x["oav"][1] if x["oav"] else None,
                                     "tom_hi": bool(hi(x, "tom")), "o_tom_lo": bool(lo(x, "tom", "of"))}
    pickle.dump(out, open(pk, "wb"))
    return out


if __name__ == "__main__":
    f = build()
    print(len(f), "sides with (A) facts")
