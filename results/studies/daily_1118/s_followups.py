"""11/18 follow-ups on the four cells that stood out in s1_s10.py (every cut fixed BEFORE looking at it):
A  NHL dog that has played 3+ MORE games than the favorite (S4: -15.1% on 545).
B  NHL dog off a WIN over a .350- team (S9: -17.3% on 448).
C  College hoops dog vs a favorite off a 1-2 point WIN (S3: -18.0% on 992).
D  NHL dog at its BIGGEST price of the season by 30c+ (S7: -18.6% on 199).
Each: the dog's own price band (the base at the same prices), the dose, the dog's rest (NHL back-to-back), the
months, ESPN's open (2023-26) and the paid morning (NHL 2021-23) as the second price, and a price-matched placebo
(random dogs from the same 50-cent price bins)."""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from h import Out  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("s", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1_s10.py"))
S = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], "none"]
spec.loader.exec_module(S)

TRAIN, HELD = S.TRAIN, S.HELD
WHICH = set(os.environ.get("WHICH", "A,B,C,D").split(","))


def pbin(o):
    return "100-149" if o < 150 else "150-199" if o < 200 else "200-249" if o < 250 else "250-350"


def matched_placebo(o, cell, pool_rows, n=2000, seed=11, fade=True):
    """Random sets drawn bin-for-bin from the same price bins as the cell's rows."""
    rows = o.c.get(cell)
    if not rows:
        return
    need = defaultdict(int)
    for _, _, od in rows:
        need[pbin(od)] += 1
    by = defaultdict(list)
    for _, p, od in pool_rows:
        by[pbin(od)].append(p)
    got = sum(p for _, p, _ in rows) / len(rows)
    rnd = random.Random(seed)
    hit = 0
    for _ in range(n):
        tot = 0.0
        for b, k in need.items():
            tot += sum(rnd.choices(by[b], k=k))
        m = tot / len(rows)
        hit += (m <= got) if fade else (m >= got)
    pool_m = sum(p for _, p, _ in pool_rows) / len(pool_rows)
    o.p(f"  PRICE-MATCHED placebo {cell}: {hit} of {n} random price-matched sets did as {'badly' if fade else 'well'} "
        f"(cell {got*100:+.1f}%, pool {pool_m*100:+.1f}%)")


def nhl_rows():
    """Every NHL dog +100..+350 at the close with the facts A / B / D need (games 10+ for A, 8+ for B, 5 prices for D)."""
    mo = lib.nhl_morning()
    out = []
    for g, raw, st in S.walk("nhl"):
        s = g["season"]
        for side, t, opp in S.sides(g):
            r, ro = st[(s, t)], st[(s, opp)]
            od, pr = S.ml(g, side)
            if S.band(od) != "dog":
                continue
            won = (g["hs"] > g["as"]) == (side == "home")
            m = mo.get(g["id"])
            op = g["oh"] if side == "home" else g["oa"]
            row = {"s": s, "od": od, "pr": pr, "won": won, "gp": r["gp"], "ogp": ro["gp"], "home": side == "home",
                   "month": g["start"][5:7], "last": r["last"], "prices": list(r["prices"]),
                   "morn": lib.profit(won, m["dh"] if side == "home" else m["da"]) if m and m.get("dh") else None,
                   "open": lib.profit(won, lib.dec(op)) if op and 100 <= op <= 400 else None, "start": g["start"],
                   "t": t, "opp": opp, "win_streak": 0}
            out.append(row)
    return out


if WHICH & {"A", "B", "D"}:
    rows = nhl_rows()
    # the dog's rest: did it play the day before? (from the all-games file)
    allg = S.allg("nhl")
    last_day = {}
    prev = {}
    for g in allg:
        d = g["start"][:10]
        for t in (g["home"], g["away"]):
            prev[(t, g["start"])] = last_day.get(t)
            last_day[t] = g["start"]
    for r in rows:
        p = prev.get((r["t"], r["start"]))
        r["b2b"] = bool(p) and lib.days_between(p, r["start"]) < 1.6
        po = prev.get((r["opp"], r["start"]))
        r["opp_b2b"] = bool(po) and lib.days_between(po, r["start"]) < 1.6
    pool10 = [(r["s"], r["pr"], r["od"]) for r in rows if r["gp"] >= 10 and r["ogp"] >= 10]

    def emit(o, name, sel, base_sel):
        for r in rows:
            if not base_sel(r):
                continue
            o.add(f"BASE {pbin(r['od'])}", r["s"], r["pr"], r["od"])
            o.add("BASE ALL", r["s"], r["pr"], r["od"])
            if sel(r):
                o.add(f"{name} ALL", r["s"], r["pr"], r["od"])
                o.add(f"{name} price {pbin(r['od'])}", r["s"], r["pr"], r["od"])
                o.add(f"{name} {'home' if r['home'] else 'road'}", r["s"], r["pr"], r["od"])
                o.add(f"{name} dog on a b2b" if r["b2b"] else f"{name} dog rested", r["s"], r["pr"], r["od"])
                o.add(f"{name} favorite on a b2b" if r["opp_b2b"] else f"{name} favorite rested", r["s"], r["pr"], r["od"])
                o.add(f"{name} month {r['month']}", r["s"], r["pr"], r["od"])
                if r["morn"] is not None:
                    o.add(f"{name} @morning (2021-23)", r["s"], r["morn"], r["od"])
                if r["open"] is not None:
                    o.add(f"{name} @ESPN open", r["s"], r["open"], r["od"])
            if r["morn"] is not None:
                o.add("BASE @morning (2021-23)", r["s"], r["morn"], r["od"])
            if r["open"] is not None:
                o.add("BASE @ESPN open", r["s"], r["open"], r["od"])

    if "A" in WHICH:
        o = Out("fA_nhl_dog_played_more", TRAIN, HELD)
        base = lambda r: r["gp"] >= 10 and r["ogp"] >= 10
        emit(o, "A dog played 3+ MORE", lambda r: r["gp"] - r["ogp"] >= 3, base)
        for k in range(-4, 6):                                       # the dose, one game at a time
            for r in rows:
                if base(r) and (r["gp"] - r["ogp"] == k or (k == 5 and r["gp"] - r["ogp"] >= 5) or (k == -4 and r["gp"] - r["ogp"] <= -4)):
                    o.add(f"DOSE gap {k:+d}{'+' if k == 5 else '-' if k == -4 else ''}", r["s"], r["pr"], r["od"])
        for lo, hi in ((10, 30), (31, 55), (56, 90)):
            for r in rows:
                if base(r) and lo <= r["gp"] <= hi and r["gp"] - r["ogp"] >= 3:
                    o.add(f"A by stage games {lo}-{hi}", r["s"], r["pr"], r["od"])
        o.show(minn=20)
        matched_placebo(o, "A dog played 3+ MORE ALL", pool10)
        o.save()

    if "B" in WHICH:
        o = Out("fB_nhl_dog_off_cheap_win", TRAIN, HELD)
        base = lambda r: r["gp"] >= 8 and r["last"] and r["last"]["opp_wp"] is not None
        emit(o, "B off a WIN over .350-", lambda r: r["last"]["margin"] > 0 and r["last"]["opp_wp"] <= 0.35, base)
        for lo, hi, nm in ((0, 0.35, ".350-"), (0.35, 0.45, ".350-.450"), (0.45, 0.55, ".450-.550"), (0.55, 0.65, ".550-.650"), (0.65, 1.01, ".650+")):
            for r in rows:
                if base(r) and lo < r["last"]["opp_wp"] + 1e-9 <= hi + 1e-9:
                    o.add(f"DOSE off a WIN over {nm}" if r["last"]["margin"] > 0 else f"DOSE off a LOSS to {nm}", r["s"], r["pr"], r["od"])
        for r in rows:
            if base(r) and r["last"]["margin"] > 0:
                o.add("B any WIN last game", r["s"], r["pr"], r["od"])
                if r["last"]["opp_wp"] <= 0.35 and r["last"]["margin"] >= 3:
                    o.add("B off a 3+ goal WIN over .350-", r["s"], r["pr"], r["od"])
                if r["last"]["opp_wp"] <= 0.35 and r["last"]["ot"]:
                    o.add("B off an OT WIN over .350-", r["s"], r["pr"], r["od"])
            if base(r) and r["last"]["margin"] < 0:
                o.add("B any LOSS last game", r["s"], r["pr"], r["od"])
        o.show(minn=20)
        poolB = [(r["s"], r["pr"], r["od"]) for r in rows if base(r)]
        matched_placebo(o, "B off a WIN over .350- ALL", poolB)
        poolW = [(r["s"], r["pr"], r["od"]) for r in rows if base(r) and r["last"]["margin"] > 0]
        o.p("  (against dogs off ANY win:)")
        matched_placebo(o, "B off a WIN over .350- ALL", poolW)
        o.save()

    if "D" in WHICH:
        o = Out("fD_nhl_dog_biggest_price", TRAIN, HELD)
        base = lambda r: len(r["prices"]) >= 5
        emit(o, "D biggest dog price by 30c+", lambda r: max(r["prices"]) > 0 and r["od"] >= max(r["prices"]) + 30, base)
        o.show(minn=20)
        poolD = [(r["s"], r["pr"], r["od"]) for r in rows if base(r)]
        matched_placebo(o, "D biggest dog price by 30c+ ALL", poolD)
        o.save()

if "C" in WHICH:
    o = Out("fC_ncaab_dog_vs_close_winner", TRAIN, HELD)
    rows = []
    for g, raw, st in S.walk("ncaab"):
        s = g["season"]
        for side, t, opp in S.sides(g):
            r, ro = st[(s, t)], st[(s, opp)]
            if r["gp"] < 3 or not ro["last"]:
                continue
            od, pr = S.ml(g, side)
            if S.band(od) != "dog":
                continue
            won = (g["hs"] > g["as"]) == (side == "home")
            op = g["oh"] if side == "home" else g["oa"]
            m = ro["last"]["margin"]
            rows.append({"s": s, "od": od, "pr": pr, "m": m, "ot": ro["last"]["ot"], "ohome": ro["last"]["home"],
                         "month": g["start"][5:7], "home": side == "home", "neutral": g["neutral"],
                         "ats": lib.ats(g, side), "open": lib.profit(won, lib.dec(op)) if op and 100 <= op <= 600 else None})
    for r in rows:
        o.add(f"BASE {pbin(r['od'])}", r["s"], r["pr"], r["od"])
        o.add("BASE ALL", r["s"], r["pr"], r["od"])
        o.add("BASE ATS", r["s"], r["ats"], r["od"])
        if r["open"] is not None:
            o.add("BASE @ESPN open", r["s"], r["open"], r["od"])
        m = r["m"]
        dose = ("fav off a 1-2 WIN" if 1 <= m <= 2 else "fav off a 3-5 WIN" if 3 <= m <= 5 else "fav off a 6-10 WIN" if 6 <= m <= 10
                else "fav off an 11+ WIN" if m >= 11 else "fav off a 1-2 LOSS" if -2 <= m <= -1 else "fav off a 3+ LOSS")
        o.add(f"DOSE {dose}", r["s"], r["pr"], r["od"])
        if 1 <= m <= 2:
            nm = "C vs a fav off a 1-2 WIN"
            for k in ("ALL", f"price {pbin(r['od'])}", "home" if r["home"] else ("neutral" if r["neutral"] else "road"),
                      f"month {r['month']}", "fav's last was OT" if r["ot"] else "fav's last in regulation",
                      "fav's last at home" if r["ohome"] else "fav's last away"):
                o.add(f"{nm} {k}", r["s"], r["pr"], r["od"])
            o.add(f"{nm} ATS", r["s"], r["ats"], r["od"])
            if r["open"] is not None:
                o.add(f"{nm} @ESPN open", r["s"], r["open"], r["od"])
    o.show(minn=20)
    matched_placebo(o, "C vs a fav off a 1-2 WIN ALL", [(r["s"], r["pr"], r["od"]) for r in rows])
    o.save()
