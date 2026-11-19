"""S10 - THE SECOND RIG: does "the engine's hockey plays win when the other side's backup is in" hold on seasons the
R3 board never saw? The 2020-23 paid-odds rig (nhl_odds_1102/lib.py - the hockey dog score rebuilt from history, the
MORNING price = the 8 AM board's hour, the close beside it): every gated dog (score 6+, the live gates) and the one
Dog a day, split by the goalie the favorite started (the pulled-starter trap out: 24+ shots on the man on file)."""
import importlib.util
import os
from collections import defaultdict
import glib

say = glib.Tee(glib.HERE + "/s10_older.out")
spec = importlib.util.spec_from_file_location("lib1102", os.path.join(glib.ROOT, "results", "studies", "nhl_odds_1102", "lib.py"))
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)
lib.OUT = glib.CACHE
D = lib.build()
ROWS = [r for r in D["rows"] if lib.in_seasons(r)]
G = glib.goalies()


def drift_of(x, r):
    if not r["open"] or not r["morning"]:
        return None
    mv = r["morning"]["p"] - r["open"]["p"]
    return -mv if x["side"] == "h" else mv


by_day = defaultdict(list)
for r in ROWS:
    ss = lib.sides(r, "morning")
    if not ss:
        continue
    for x in ss:
        if not 100 <= x["am"] <= 350:
            continue
        x["score"] = lib.dog_score(x, drift=drift_of(x, r))
        opp = r["home"] if x["side"] == "a" else r["away"]
        me = r["home"] if x["side"] == "h" else r["away"]
        go, gm = G.get((r["id"], opp)), G.get((r["id"], me))
        x["ro"] = None if not go or not go["n1"] else "n1" if go["actual"] == go["n1"] else "bk"
        x["rm"] = None if not gm or not gm["n1"] else "n1" if gm["actual"] == gm["n1"] else "bk"
        x["sa_o"] = float(go["sa"] or 0) if go else 0
        x["po"] = None if not go or not go["n1"] or not go["proj"] else "n1" if go["proj"] == go["n1"] else "bk"
        x["dec_c"] = lib.dec(r["ch"] if x["side"] == "h" else r["ca"])
        x["season"] = r["season"]
        by_day[r["date"]].append(x)


def fighting(x):
    return x["own"] < 1 / x["dec"] - 0.03


def L(name, xs):
    if not xs:
        say(f"  {name:58s} none")
        return
    n = len(xs)
    w = sum(x["won"] for x in xs)
    m = 100 * sum(x["profit"] for x in xs) / n
    c = 100 * sum((x["dec_c"] - 1) if x["won"] else -1 for x in xs) / n
    by = defaultdict(list)
    for x in xs:
        by[x["season"]].append(x["profit"])
    say(f"  {name:58s} {w:3d}-{n - w:<3d} morning {m:+6.1f}% / close {c:+6.1f}% | " + " ".join(f"{k}:{len(v)}/{100 * sum(v) / len(v):+.0f}%" for k, v in sorted(by.items())))


allx = [x for d in by_day.values() for x in d]
ok = [x for x in allx if not fighting(x) and x["own"] >= x["pm"]]
for nm, pool in (("EVERY GATED DOG (score 6+, live gates)", [x for x in ok if x["score"] >= 6]),
                 ("THE DOG, one a day (best gated)", [max([x for x in d if not fighting(x) and x["own"] >= x["pm"] and x["score"] >= 6], key=lambda x: x["score"])
                                                      for d in by_day.values() if any(not fighting(x) and x["own"] >= x["pm"] and x["score"] >= 6 for x in d)]),
                 ("DOGS AT A SCORE OF 3..6 (the floor's kind)", [x for x in ok if 3 <= x["score"] < 6]),
                 ("DOGS AT A SCORE OF 0..6", [x for x in ok if 0 <= x["score"] < 6]),
                 ("EVERY DOG +100..+350", allx)):
    say(f"=== {nm} - 2020-23")
    L("all", pool)
    L("their #1 started (trap in)", [x for x in pool if x["ro"] == "n1"])
    L("their backup started (trap in)", [x for x in pool if x["ro"] == "bk"])
    L("their #1 started, 24+ shots on him", [x for x in pool if x["ro"] == "n1" and x["sa_o"] >= 24])
    L("their backup started, 24+ shots on him", [x for x in pool if x["ro"] == "bk" and x["sa_o"] >= 24])
    L("their backup, the favorite NOT on a b2b (24+)", [x for x in pool if x["ro"] == "bk" and x["sa_o"] >= 24 and not x["ob2b"]])
    L("their #1, the favorite NOT on a b2b (24+)", [x for x in pool if x["ro"] == "n1" and x["sa_o"] >= 24 and not x["ob2b"]])
    L("projected at 8 AM: their #1", [x for x in pool if x["po"] == "n1"])
    L("projected at 8 AM: their backup", [x for x in pool if x["po"] == "bk"])
