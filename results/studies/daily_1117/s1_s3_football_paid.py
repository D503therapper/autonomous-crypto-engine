"""11/17 daily studies S1-S3 - FOOTBALL, THE PAID ODDS HISTORY (NFL + college, 2020-26, every book's timestamped price).
S1 THE RE-HANG: the books' price hung BEFORE the teams' last games (the look-ahead number) -> the first FAIR number
   (after both last games) - does the market over- or under-react to last week's results? Follow / fade the re-hang,
   bet at the first fair median price (the early number), graded there and at ESPN's close.
S2 THE SPLIT MOVE: first fair -> last look before kickoff, the moneyline and the spread moved DIFFERENT ways (ML money
   one way, the number the other) - which half is right?
S3 THE BOOKS' HOLD: the median book's overround at the first fair look, against the league's own median that season -
   are dogs in a wide-hold (books unsure / protecting) market mispriced?
No look-ahead in any bet price: S1 READS the look-ahead number (it was up before the bet) and bets the first fair one;
S2 bets the last look; S3 the first fair look. Train 2020-22, held 2023 / 2024 / 2025 / 2026 apart."""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from h import Out  # noqa: E402

TRAIN, HELD = (2020, 2022), [2023, 2024, 2025, 2026]


def bandname(o):
    if 100 <= o <= 350:
        return "dog"
    if -150 <= o <= -101:
        return "fav"
    return None


def close_side(g, side):
    o = g["c_mlh"] if side == "home" else g["c_mla"]
    return o


def res(g, side):
    return (g["margin"] > 0) if side == "home" else (g["margin"] < 0)


def ats_close(g, side):
    if g["c_sp"] is None or g["margin"] == -g["c_sp"]:
        return None
    hc = g["margin"] + g["c_sp"] > 0
    won = hc if side == "home" else not hc
    o = (g["c_sho"] if side == "home" else g["c_sao"]) or -110
    return lib.profit(won, lib.dec(o))


for lg in ("nfl", "ncaaf"):
    gs = lib.load_football(lg)
    o1 = Out(f"s1_rehang_{lg}", TRAIN, HELD)
    o2 = Out(f"s2_split_move_{lg}", TRAIN, HELD)
    o3 = Out(f"s3_hold_{lg}", TRAIN, HELD)
    # ---- S3 needs the season median hold first
    holds = {}
    for g in gs:
        f = lib.first_fair(g["ml"])
        if not f:
            continue
        hs = [1 / lib.dec(v[0]) + 1 / lib.dec(v[1]) - 1 for v in f[1].values()]
        g["_hold"] = statistics.median(hs)
        holds.setdefault(g["season"], []).append(g["_hold"])
    med = {s: statistics.median(v) for s, v in holds.items()}
    q = {s: statistics.quantiles(v, n=5) for s, v in holds.items()}     # the season's own quintiles (books' holds converge after 2022)
    o3.p(f"{lg}: season median hold at the first fair look: " + ", ".join(f"{s} {m*100:.2f}% (top fifth {q[s][3]*100:.2f}%+, bottom {q[s][0]*100:.2f}%-)" for s, m in sorted(med.items())))
    n1 = 0
    for g in gs:
        s = g["season"]
        f = lib.first_fair(g["ml"])
        if not f:
            continue
        hf, af, pf = lib.ml_med(f[1])
        # ---------------- S1 THE RE-HANG ----------------
        pre = [x for x in g["all_ml"] if x[0] > f[0] + 0.2]          # looks hung earlier than the first fair one
        if pre:
            la = pre[-1]                                              # the latest look-ahead look
            if la[0] - f[0] <= 6.5:
                _, _, pla = lib.ml_med(la[1])
                mv = (pf - pla) * 100                                 # + = the books moved TO the home side
                n1 += 1
                for side in ("home", "away"):
                    toward = mv if side == "home" else -mv
                    d = hf if side == "home" else af
                    am = lib.american(d)
                    b = bandname(am)
                    if b is None:
                        continue
                    won = res(g, side)
                    cl = close_side(g, side)
                    pc = lib.profit(won, lib.dec(cl)) if cl else None
                    for lo, hi, nm in ((-99, -5, "away 5+"), (-5, -3, "away 3-5"), (-3, -1.5, "away 1.5-3"),
                                       (-1.5, 1.5, "flat"), (1.5, 3, "to 1.5-3"), (3, 5, "to 3-5"), (5, 99, "to 5+")):
                        if lo <= toward < hi:
                            o1.add(f"{b} re-hung {nm:10s} @first fair", s, lib.profit(won, d))
                            o1.add(f"{b} re-hung {nm:10s} @close", s, pc)
                            o1.add(f"{b} re-hung {nm:10s} ATS close", s, ats_close(g, side))
                    o1.add(f"{b} ALL (base) @first fair", s, lib.profit(won, d))
                    o1.add(f"{b} ALL (base) @close", s, pc)
                    o1.add(f"{b} ALL (base) ATS close", s, ats_close(g, side))
        # ---------------- S2 THE SPLIT MOVE ----------------
        lst = lib.last_look(g["ml"])
        sf, sl = lib.first_fair(g["sp"]), lib.last_look(g["sp"])
        if lst and sf and sl:
            hl, al, pl = lib.ml_med(lst[1])
            ml_mv = (pl - pf) * 100                                   # + = ML money to home
            sp_f, _, _ = lib.sp_med(sf[1])
            sp_l, _, _ = lib.sp_med(sl[1])
            sp_mv = sp_f - sp_l                                       # + = the number moved to home (home laid more)
            for side in ("home", "away"):
                mlm = ml_mv if side == "home" else -ml_mv
                spm = sp_mv if side == "home" else -sp_mv
                d = hl if side == "home" else al
                am = lib.american(d)
                b = bandname(am)
                won = res(g, side)
                cl = close_side(g, side)
                pc = lib.profit(won, lib.dec(cl)) if cl else None
                kind = None
                if mlm >= 1.5 and spm <= -0.5:
                    kind = "ML money TO it, the number AWAY"
                elif mlm >= 1.5 and spm >= 0.5:
                    kind = "both moved TO it"
                elif mlm >= 1.5 and abs(spm) < 0.5:
                    kind = "ML to it, the number still"
                if kind:
                    if b:
                        o2.add(f"{b} {kind} @last look", s, lib.profit(won, d))
                        o2.add(f"{b} {kind} @close", s, pc)
                    o2.add(f"all {kind} ATS close", s, ats_close(g, side))
                if b:
                    o2.add(f"{b} ALL (base) @last look", s, lib.profit(won, d))
                o2.add("all ALL (base) ATS close", s, ats_close(g, side))
        # ---------------- S3 THE BOOKS' HOLD ----------------
        hb = ("hold top fifth of the season" if g["_hold"] > q[s][3] else
              ("hold bottom fifth" if g["_hold"] < q[s][0] else "hold middle three fifths"))
        for side in ("home", "away"):
            d = hf if side == "home" else af
            am = lib.american(d)
            b = bandname(am)
            if not b:
                continue
            won = res(g, side)
            cl = close_side(g, side)
            o3.add(f"{b} {hb} @first fair", s, lib.profit(won, d))
            o3.add(f"{b} {hb} @close", s, lib.profit(won, lib.dec(cl)) if cl else None)
            o3.add(f"{b} ALL @first fair", s, lib.profit(won, d))
    o1.p(f"{lg}: {n1} games with a look-ahead look within 6.5 days of the first fair one")
    o1.show()
    for nm in ("dog re-hung to 5+      @first fair", "dog re-hung away 5+    @first fair", "fav re-hung to 5+      @first fair",
               "fav re-hung away 5+    @first fair", "dog re-hung to 3-5     @first fair", "dog re-hung away 3-5   @first fair"):
        if nm in o1.c:
            o1.placebo(nm, "dog ALL (base) @first fair" if nm.startswith("dog") else "fav ALL (base) @first fair")
            o1.placebo(nm, "dog ALL (base) @first fair" if nm.startswith("dog") else "fav ALL (base) @first fair", fade=True)
    o1.save()
    o2.show()
    for nm in list(o2.c):
        if "AWAY" in nm and "@last look" in nm:
            base = ("dog" if nm.startswith("dog") else "fav") + " ALL (base) @last look"
            o2.placebo(nm, base)
            o2.placebo(nm, base, fade=True)
    o2.save()
    o3.show()
    for nm in list(o3.c):
        if ("top fifth" in nm or "bottom fifth" in nm) and "@first fair" in nm:
            base = ("dog" if nm.startswith("dog") else "fav") + " ALL @first fair"
            o3.placebo(nm, base)
            o3.placebo(nm, base, fade=True)
    o3.save()
