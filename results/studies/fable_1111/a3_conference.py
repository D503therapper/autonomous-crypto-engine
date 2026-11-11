"""A3 / A4 / A5 - COLLEGE HOOPS: WHERE COULD IT PAY? (the 11/3 (B) side table: ESPN's close 2018-25, the ML open
2023-25, the walk-forward efficiency read, conferences inferred from the schedule, tiers.)
A3 - THE EFFICIENCY READ vs THE CLOSE, CONFERENCE PLAY vs NON-CONFERENCE (the 11/3 DEEP hunt cut stage x tier x
     venue x price and never the conference flag; the gap play's conference cell +31.6% on 161 pointed here):
     moneyline dogs / favorites by the read's gap over the no-vig, and ATS by the model margin vs the spread.
A4 - CONFERENCE BIAS (never studied in hoops): the conference's running NON-conference cover margin this season
     (every OTHER member's games before tonight, 30+) - does the market lag on a whole league running hot / cold?
     Read on the team's later non-conference games and the postseason.
A5 - SMALL-CONFERENCE DOGS: tier x opponent tier x conference flag x venue x band, moneyline and ATS.
TRAIN 2018-22, HELD 2023 / 2024 / 2025 apart."""
import os, pickle, statistics
from collections import defaultdict
import lib

o = lib.Out("a3")
rows = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
rows = [r for r in rows if 2018 <= r["season"] <= 2025 and r.get("ml") is not None]
rows.sort(key=lambda r: r["start"])
TR, HE = (2018, 2022), (2023, 2024, 2025)


def mlp(r, open_=False):
    od = r.get("mlo") if open_ else r["ml"]
    return None if od is None else lib.profit(r["won"], lib.dec(od))


def atsp(r):
    if r.get("sp") is None:
        return None
    x = r["margin"] + r["sp"]
    return None if x == 0 else lib.profit(x > 0, lib.dec(r.get("spodds") or -110))


def band(od):
    return "+100..+150" if 100 <= od <= 150 else "+151..+250" if od <= 250 else "+251..+350"


A3, A4, A5 = lib.Cells(), lib.Cells(), lib.Cells()
# ---- conference running non-conference cover margins (A4) ----
conf_cm = defaultdict(list)                       # (season, conf) -> [(team, cover margin)]
pend = []
last_night = None
for r in rows:
    if r["night"] != last_night:
        for k, v in pend:
            conf_cm[k].append(v)
        pend, last_night = [], r["night"]
    s, reg = r["season"], r["stype"] == "2"
    ph = "Nov-Dec" if r["month"] in ("11", "12") else "Jan-Mar"
    cf = "CONF" if r["same_conf"] else "NONCONF"
    od = r["ml"]
    a = atsp(r)
    if reg and r.get("eff") is not None and r["gn"] >= 4 and r["ogn"] >= 4:
        gap = r["eff"] - r["p"]
        if 100 <= od <= 350:
            A3.add(f"BASE dog {cf}", s, mlp(r))
            for cut in (0.05, 0.10, 0.15):
                if gap >= cut:
                    A3.add(f"{cf} dog, eff read {int(cut*100)}+ over", s, mlp(r))
                    A3.add(f"{cf} {ph} dog, eff read {int(cut*100)}+ over", s, mlp(r))
                    if s >= 2023:
                        A3.add(f"OPEN {cf} dog, eff read {int(cut*100)}+ over", s, mlp(r, True))
                    if r["eff"] > 0.5:
                        A3.add(f"{cf} dog, eff {int(cut*100)}+ over AND backed", s, mlp(r))
                        A3.add(f"{cf} dog, eff {int(cut*100)}+ over AND backed, ATS", s, a)
            if gap <= -0.05:
                A3.add(f"{cf} dog, eff read 5+ UNDER", s, mlp(r))
        if -250 <= od <= -101:
            A3.add(f"BASE fav {cf}", s, mlp(r))
            for cut in (0.03, 0.06, 0.10):
                if gap >= cut:
                    A3.add(f"{cf} fav -101..-250, eff read {int(cut*100)}+ over", s, mlp(r))
                    A3.add(f"{cf} {ph} fav -101..-250, eff {int(cut*100)}+ over", s, mlp(r))
                    if s >= 2023:
                        A3.add(f"OPEN {cf} fav -101..-250, eff {int(cut*100)}+ over", s, mlp(r, True))
            if gap <= -0.03:
                A3.add(f"{cf} fav -101..-250, eff 3+ UNDER", s, mlp(r))
        if r.get("sp") is not None and r.get("eff_m") is not None:
            mg = r["eff_m"] + r["sp"]                  # model margin minus the market's (-sp)
            A3.add(f"BASE ATS {cf}", s, a)
            for cut in (2, 4, 6):
                if mg >= cut:
                    A3.add(f"ATS {cf}, model {cut}+ pts over the spread", s, a)
                    A3.add(f"ATS {cf} {ph}, model {cut}+ over", s, a)
                    A3.add(f"ATS {cf}, model {cut}+ over, {'dog' if r['sp'] > 0 else 'fav'}", s, a)
    # ---- A4 ----
    key = (s, r["conf"])
    if r["conf"] and not r["same_conf"] and r.get("sp") is not None:
        oth = [c for t, c in conf_cm[key] if t != r["team"]]
        ok = (s, None)
        if len(oth) >= 30:
            bias = statistics.mean(oth)
            st = "postseason" if not reg else ph
            for cut in (1.0, 2.0):
                if bias >= cut:
                    A4.add(f"conf running +{cut:.0f} vs its numbers -> ATS", s, a)
                    A4.add(f"conf running +{cut:.0f} -> ATS, {st}", s, a)
                    if 100 <= od <= 350:
                        A4.add(f"conf running +{cut:.0f} -> dog ML", s, mlp(r))
                if bias <= -cut:
                    A4.add(f"conf running -{cut:.0f} vs its numbers -> ATS", s, a)
                    A4.add(f"conf running -{cut:.0f} -> ATS, {st}", s, a)
                    if 100 <= od <= 350:
                        A4.add(f"conf running -{cut:.0f} -> dog ML", s, mlp(r))
            A4.add("BASE non-conference ATS", s, a)
        if reg:
            pend.append((key, (r["team"], r["margin"] + r["sp"])))
    # ---- A5 ----
    if reg and 100 <= od <= 350 and r["tier"] in ("low", "mid", "power"):
        t, ot = r["tier"], r["otier"]
        A5.add(f"BASE dog tier {t}", s, mlp(r))
        A5.add(f"{t} dog vs {ot}, {cf}, ML", s, mlp(r))
        A5.add(f"{t} dog vs {ot}, {cf}, ATS", s, a)
        A5.add(f"{t} dog {cf} {r['venue']}, ML", s, mlp(r))
        A5.add(f"{t} dog {cf} {r['venue']}, ATS", s, a)
        A5.add(f"{t} dog {cf} {r['venue']} {band(od)}, ML", s, mlp(r))
        A5.add(f"{t} dog {cf} {ph}, ML", s, mlp(r))
        if t == "low" and r["same_conf"]:
            A5.add(f"low-major conference dog {r['venue']} {ph}, ML", s, mlp(r))
            A5.add(f"low-major conference dog {r['venue']} {ph}, ATS", s, a)
            if r.get("eff") is not None and r["eff"] > r["p"] + 0.05:
                A5.add(f"low-major conference dog {r['venue']}, eff 5+ over, ML", s, mlp(r))

Z = float(os.environ.get("ZSHOW", "2.6"))
o.p("A3 - THE EFFICIENCY READ vs THE CLOSE, CONFERENCE vs NON-CONFERENCE (both teams 4+ games)")
o.cells(A3, TR, HE, minn=40, zshow=Z)
o.p("\nA4 - CONFERENCE BIAS (the league's running non-conference cover margin, other members, 30+ games)")
o.cells(A4, TR, HE, minn=40, zshow=0)
o.p("\nA5 - SMALL-CONFERENCE DOGS (tier x opponent x conference x venue x band)")
o.cells(A5, TR, HE, minn=100, zshow=Z)
o.p(f"\ncells: {len(A3.c)} + {len(A4.c)} + {len(A5.c)}")
o.save()
