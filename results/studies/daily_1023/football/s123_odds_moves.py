"""Studies 1-3 (10/23) on the paid odds history, NFL + college 2020-26. No look-ahead: every signal uses the first
FAIR look (after both teams' last games) and looks up to the bet; ML bets at the LAST look before kickoff (median
book), spread bets at the game-file closing number + its juice (the last number the signal can know).
1 CONFLICT: the spread moved toward side A (Tuesday -> close) while the moneyline (first fair -> last look) moved
  toward B. 2 BREADTH: a moneyline move made by nearly every book vs one made by only part of the market.
3 QUIET WEEK: no move at all (ML within 1% all week, spread never moved) - bet the dog."""
import json
import lib

OUTF = lib.OUT + "/s123_out.json"
BAND = (-150, 350)


def am(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def inband(d):
    a = am(d)
    return BAND[0] <= a <= BAND[1] and not -100 < a < 100


def rows(lg):
    out = []
    for r in lib.load(lg):
        fl = lib.first_last(r["ml"])
        if not fl:
            continue
        (d0, b0), (d1, b1) = fl
        h0, a0, p0 = lib.ml_med(b0)
        h1, a1, p1 = lib.ml_med(b1)
        tue = lib.sp_med(r["sp"][0][1]) if r["sp"] and 1.5 <= r["sp"][0][0] < 7.5 else None
        close = lib.num(r["c_sp"])
        common = [k for k in b0 if k in b1]
        ch = [lib.nv(*b1[k]) - lib.nv(*b0[k]) for k in common]
        allp = [lib.ml_med(b)[2] for d, b in r["ml"] if 0.03 <= d < 7.5]
        if tue and abs(tue[0]) >= 3 and (p0 > 0.5) != (tue[0] < 0):
            continue                                  # the two feeds disagree on who's favored = a matching error
        ch_, ca_ = lib.num(r["c_mlh"]), lib.num(r["c_mla"])
        pc = lib.nv(ch_, ca_) if ch_ and ca_ and abs(ch_) >= 100 and abs(ca_) >= 100 else None
        if pc is not None and close is not None and abs(close) >= 3 and (pc > 0.5) != (close < 0):
            continue
        out.append({**r, "lg": lg, "pc": pc, "p0": p0, "p1": p1, "h1": h1, "a1": a1, "tue": tue[0] if tue else None,
                    "close": close, "ch": ch, "allp": allp, "nlooks": len(allp)})
    return out


def bet_ml(x, side):
    d = x["h1"] if side == "h" else x["a1"]
    if not inband(d):
        return None
    return lib.mlp(x, side, d)


def bet_sp(x, side):
    if x["close"] is None:
        return None
    pts = x["close"] if side == "h" else -x["close"]
    if abs(pts) > 21:
        return None
    return lib.cover(x, side, pts, lib.sp_dec(x["c_sho"] if side == "h" else x["c_sao"]))


def collect(xs, pick, fn):
    b = []
    for x in xs:
        s = pick(x)
        if not s:
            continue
        p = fn(x, s)
        if p is not None:
            b.append((x["season"], p))
    return lib.summ(b)


def other(s):
    return "a" if s == "h" else "h"


def main():
    rep = {}
    for lg in ("nfl", "ncaaf"):
        xs = rows(lg)
        R = {}
        print(f"\n===== {lg.upper()} {len(xs)} games with first fair + last ML looks")
        # baselines
        R["base every side ML -150..+350 last look"] = lib.summ(
            [(x["season"], p) for x in xs for s in "ha" for p in [bet_ml(x, s)] if p is not None])
        R["base every dog ML +100..+350 last look"] = lib.summ(
            [(x["season"], p) for x in xs for s in "ha" for p in [bet_ml(x, s)] if p is not None
             and (x["h1"] if s == "h" else x["a1"]) >= 2.0])
        R["base every spread side at the close"] = lib.summ(
            [(x["season"], p) for x in xs for s in "ha" for p in [bet_sp(x, s)] if p is not None])
        # 1 CONFLICT
        for ts in (0.5, 1.0, 1.5):
            for tm in (0.01, 0.02):
                def pick(x, ts=ts, tm=tm):
                    if x["tue"] is None or x["close"] is None:
                        return None
                    smv = x["tue"] - x["close"]        # + = home got more favored on the spread
                    mmv = x["p1"] - x["p0"]            # + = home got more favored on the moneyline
                    if smv >= ts and mmv <= -tm:
                        return "h"
                    if smv <= -ts and mmv >= tm:
                        return "a"
                    return None
                k = f"1 conflict sp>={ts} ml>={tm:.0%}"
                R[k + " | spread side, spread"] = collect(xs, pick, bet_sp)
                R[k + " | spread side, ML"] = collect(xs, pick, bet_ml)
                R[k + " | ML side, ML"] = collect(xs, lambda x, p=pick: other(p(x)) if p(x) else None, bet_ml)
                R[k + " | ML side, spread"] = collect(xs, lambda x, p=pick: other(p(x)) if p(x) else None, bet_sp)
        # 1b CONFLICT known at the close: ML first fair -> game-file closing ML, spread Tuesday -> close; bet the close
        for ts in (0.5, 1.0):
            for tm in (0.01, 0.02):
                def pick(x, ts=ts, tm=tm):
                    if x["tue"] is None or x["close"] is None or x["pc"] is None:
                        return None
                    smv = x["tue"] - x["close"]
                    mmv = x["pc"] - x["p0"]
                    if smv >= ts and mmv <= -tm:
                        return "h"
                    if smv <= -ts and mmv >= tm:
                        return "a"
                    return None
                k = f"1b conflict@close sp>={ts} ml>={tm:.0%}"
                R[k + " | spread side, spread"] = collect(xs, pick, bet_sp)
                R[k + " | ML side, spread"] = collect(xs, lambda x, p=pick: other(p(x)) if p(x) else None, bet_sp)
        # late move check (is the game-file close later than our last look, and does that late move carry info?)
        for tm in (0.02, 0.04):
            def pick(x, tm=tm):
                if x["pc"] is None:
                    return None
                m = x["pc"] - x["p1"]
                return "h" if m >= tm else "a" if m <= -tm else None
            R[f"chk late move last look->gf close >={tm:.0%} | that side spread at close"] = collect(xs, pick, bet_sp)
        # 2 BREADTH
        for mv in (0.02, 0.03):
            for lbl, lo, hi in (("unanimous 90%+", 0.9, 1.01), ("partial <=60%", 0.0, 0.6)):
                def pick(x, mv=mv, lo=lo, hi=hi):
                    if len(x["ch"]) < 5:
                        return None
                    m = x["p1"] - x["p0"]
                    if abs(m) < mv:
                        return None
                    s = "h" if m > 0 else "a"
                    sg = 1 if m > 0 else -1
                    share = sum(1 for c in x["ch"] if c * sg >= 0.01) / len(x["ch"])
                    return s if lo <= share < hi else None
                k = f"2 breadth move>={mv:.0%} {lbl}"
                R[k + " | follow ML"] = collect(xs, pick, bet_ml)
                R[k + " | fade ML"] = collect(xs, lambda x, p=pick: other(p(x)) if p(x) else None, bet_ml)
                R[k + " | follow spread"] = collect(xs, pick, bet_sp)
        # 3 QUIET WEEK
        for tol in (0.01, 0.015):
            def quiet(x, tol=tol):
                return (x["nlooks"] >= 3 and max(x["allp"]) - min(x["allp"]) <= tol and x["tue"] is not None
                        and x["close"] is not None and x["tue"] == x["close"])
            def dog(x):
                return "h" if x["p1"] < 0.5 else "a"
            k = f"3 quiet week (ML within {tol:.1%}, spread unmoved)"
            R[k + " | dog ML"] = collect(xs, lambda x, q=quiet: dog(x) if q(x) else None, bet_ml)
            R[k + " | dog spread"] = collect(xs, lambda x, q=quiet: dog(x) if q(x) else None, bet_sp)
            R[k + " | favorite spread"] = collect(xs, lambda x, q=quiet: other(dog(x)) if q(x) else None, bet_sp)
            R[k + " | home dog spread"] = collect(xs, lambda x, q=quiet: "h" if q(x) and x["p1"] < 0.5 and not x["neutral"] else None, bet_sp)
            R[k + " | road dog spread"] = collect(xs, lambda x, q=quiet: "a" if q(x) and x["p1"] >= 0.5 and not x["neutral"] else None, bet_sp)
        for k, v in R.items():
            print(lib.line(k, v))
        rep[lg] = R
    json.dump(rep, open(OUTF, "w"), indent=1)


if __name__ == "__main__":
    main()
