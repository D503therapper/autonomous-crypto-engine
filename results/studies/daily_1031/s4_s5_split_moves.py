"""Studies 4 + 5 (10/31): the paid odds history, NFL + college football - WHEN THE TWO MARKETS MOVE APART.
First FAIR look (1.5-7.5 days out, posted after both teams' last games - ef.ready_at / fair), the median book ->
the CLOSE (the game file's closing moneyline / spread / juice; the paid history holds the spread at one early look
per game, so the close is the only later spread number we have). Never run before as a MOVE (the 10/8 study was the static ML-vs-spread gap at
one look; the 10/10 'spread juice' was the juice at one look; the 10/8 shape study was the moneyline's shape alone).

4. THE MONEYLINE-ONLY MOVE: the dog's no-vig moneyline % moves 2+ points while the spread NUMBER stays put (under ½
   point) - money that came only through the moneyline. Both ways (to the dog / away from it). Compared with the same
   ML move WITH the spread moving the same way (1+ point), and the spread-only move (1+ point, ML under 1 point).
5. THE JUICE-ONLY MOVE ON THE SPREAD: the number stays put (same median number) but the dog side's spread juice
   moves 8+ cents (e.g. +3 -105 -> +3 -115 = the book leaning on the dog without moving the number) - the step
   before a number move. Graded on the dog: ATS at the last look's number / juice, ML at the last look and the close.
Bets graded at the CLOSE (the move is only seen once it's done - the price after it).
Train 2020-23, held out 2024 / 2025 / 2026 apart."""
import json, os, statistics, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2020, 2023), (2024, 2025, 2026)
out4, out5 = {}, {}
txt4, txt5 = [], []
for lg in ("nfl", "ncaaf"):
    G = lib.load_football(lg)
    c4, c5 = defaultdict(list), defaultdict(list)
    n_both = 0
    for x in G:
        f_ml, f_sp = lib.first_fair(x["ml"]), lib.first_fair(x["sp"])
        if not (f_ml and f_sp) or None in (x["c_mlh"], x["c_mla"], x["c_sp"]):
            continue
        n_both += 1
        s = x["season"]
        h0, a0, p0 = lib.ml_med(f_ml[1])
        p1 = lib.nv(x["c_mlh"], x["c_mla"])
        sp0, hj0, aj0 = lib.sp_med(f_sp[1])
        sp1 = x["c_sp"]
        hj1, aj1 = lib.dec(x["c_sho"] or -110), lib.dec(x["c_sao"] or -110)
        if p1 < 0.5:                                    # the dog = the side under 50% at the close
            side, c_o, dp0, dp1, dsp0, dsp1, dj0, dj1 = "home", x["c_mlh"], p0, p1, sp0, sp1, hj0, hj1
        else:
            side, c_o, dp0, dp1, dsp0, dsp1, dj0, dj1 = "away", x["c_mla"], 1 - p0, 1 - p1, -sp0, -sp1, aj0, aj1
        if not (100 <= c_o <= 350):
            continue
        won = (x["margin"] > 0) if side == "home" else (x["margin"] < 0)
        pr_close = lib.profit(won, lib.dec(c_o))
        dml = dp1 - dp0                                 # + = the moneyline moved TO the dog
        dsp = dsp0 - dsp1                               # + = the dog gets FEWER points = the spread moved to the dog
        m = x["margin"] if side == "home" else -x["margin"]
        cov = m + dsp1
        ats_close = None if cov == 0 else lib.profit(cov > 0, dj1)

        def put(cells, k):
            cells[k + " | ML at the close"].append((s, pr_close))
            if ats_close is not None:
                cells[k + " | ATS at the close"].append((s, ats_close))
        put(c4, "dog, all (base)")
        same_num = abs(dsp) < 0.5
        if dml >= 0.02 and same_num:
            put(c4, "ML-only move TO the dog (2+ pts, spread put)")
        if dml <= -0.02 and same_num:
            put(c4, "ML-only move AWAY from the dog (2+ pts, spread put)")
        if dml >= 0.02 and dsp >= 1:
            put(c4, "ML 2+ AND spread 1+ both TO the dog")
        if dml <= -0.02 and dsp <= -1:
            put(c4, "ML 2+ AND spread 1+ both AWAY from the dog")
        if dsp >= 1 and abs(dml) < 0.01:
            put(c4, "spread-only move TO the dog (1+ pt, ML under 1)")
        if dsp <= -1 and abs(dml) < 0.01:
            put(c4, "spread-only move AWAY from the dog")
        # study 5: the number exactly the same, the juice moved
        if sp0 == sp1:
            dj = (1 / dj1) - (1 / dj0)                 # + = the dog's spread price got SHORTER (more juice on it)
            put(c5, "dog, number unchanged (base)")
            if dj >= 0.02:                             # ~8 cents of American juice around -110
                put(c5, "juice 8c+ ONTO the dog, number put")
            if dj <= -0.02:
                put(c5, "juice 8c+ OFF the dog, number put")
            if dj >= 0.02 and dml >= 0.01:
                put(c5, "juice onto the dog AND its ML moved to it 1+")
            if dj >= 0.02 and dml <= 0:
                put(c5, "juice onto the dog, its ML flat / away")
    r4 = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(c4.items())}
    r5 = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(c5.items())}
    out4[lg], out5[lg] = r4, r5
    txt4.append(f"== {lg}: {n_both} games with a first fair ML + spread and a close (dogs +100..+350 at the close)")
    txt4 += [lib.fmt(k, v) for k, v in r4.items()]
    txt5.append(f"== {lg}: number unchanged first fair -> close")
    txt5 += [lib.fmt(k, v) for k, v in r5.items()]
for name, txt, out in (("s4", txt4, out4), ("s5", txt5, out5)):
    t = "\n".join(txt)
    print(t)
    open(os.path.join(lib.OUT, f"{name}_out.txt"), "w").write(t + "\n")
    json.dump(out, open(os.path.join(lib.OUT, f"{name}_out.json"), "w"), indent=1)
