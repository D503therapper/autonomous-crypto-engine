"""S3. WONG TEASERS (NFL two-team six-point, through the 3 and the 7): favorites -7.5..-8.5 down to -1.5..-2.5, dogs
+1.5..+2.5 up to +7.5..+8.5. nflverse's closing lines 1999-2026, regular season + playoffs. The rule is Stanford
Wong's (2001) - not fit here; TRAIN 1999-2014 / BLIND 2015-26 is only to see whether the books closed it.
Leg rates by season, then REAL two-team tickets (every pair of Wong legs in the same week, and one ticket a week =
the two legs kicked off first) at -110 / -120 / -130 / -135; a pushed leg = the ticket is a push (most books: it
drops to a straight bet at reduced odds or refunds - a refund is the neutral reading).
   python s3_teasers.py"""
import itertools, math, random
import nfl

o = nfl.Out("s3")
G = nfl.games()
random.seed(11)


def legs(g, lo_f=7.5, hi_f=8.5, lo_d=1.5, hi_d=2.5, pts=6.0):
    """[(side, teased line for that side, result: 1 win / 0 push / -1 loss, kind)]"""
    out = []
    for side, line, m in (("home", g["hl"], g["m"]), ("away", -g["hl"], -g["m"])):
        if -hi_f <= line <= -lo_f:
            k = "fav"
        elif lo_d <= line <= hi_d:
            k = "dog"
        else:
            continue
        r = m + line + pts
        out.append({"g": g, "side": side, "line": line, "kind": k, "res": 1 if r > 0 else (0 if r == 0 else -1),
                    "season": g["season"], "week": g["week"], "home": side == "home" and not g["neutral"]})
    return out


L = [x for g in G for x in legs(g)]


def rate(ls):
    w = sum(1 for x in ls if x["res"] > 0)
    l = sum(1 for x in ls if x["res"] < 0)
    n = w + l
    if not n:
        return "    0      -"
    p = w / n
    return f"{n:5d} {w:4d}-{l:<4d} {p * 100:5.1f}% (se {math.sqrt(p * (1 - p) / n) * 100:.1f})"


def pct(ls):
    w = sum(1 for x in ls if x["res"] > 0)
    l = sum(1 for x in ls if x["res"] < 0)
    return w / max(1, w + l) * 100


BE = {p: math.sqrt(1 / nfl.dec(p)) * 100 for p in (-110, -120, -130, -135)}
o("two-team break-even per leg:", " ".join(f"{k}: {v:.2f}%" for k, v in BE.items()))
o("\n== LEG WIN RATES (pushes out) ==")
ERAS = (("all 1999-2026", 1999, 2026), ("TRAIN 1999-2014", 1999, 2014), ("BLIND 2015-2026", 2015, 2026),
        ("2015-2019", 2015, 2019), ("2020-2026", 2020, 2026), ("2023-2026", 2023, 2026))
CUTS = (("every Wong leg", lambda x: True),
        ("favorites -7.5..-8.5", lambda x: x["kind"] == "fav"),
        ("dogs +1.5..+2.5", lambda x: x["kind"] == "dog"),
        ("home favorites", lambda x: x["kind"] == "fav" and x["home"]),
        ("road favorites", lambda x: x["kind"] == "fav" and not x["home"]),
        ("home dogs", lambda x: x["kind"] == "dog" and x["home"]),
        ("road dogs", lambda x: x["kind"] == "dog" and not x["home"]),
        ("total under 49", lambda x: x["g"]["total"] is not None and x["g"]["total"] < 49),
        ("total 49+", lambda x: x["g"]["total"] is not None and x["g"]["total"] >= 49),
        ("total under 44", lambda x: x["g"]["total"] is not None and x["g"]["total"] < 44),
        ("regular season only", lambda x: x["g"]["reg"]),
        ("division game", lambda x: x["g"]["div"]),
        ("non-division", lambda x: not x["g"]["div"]),
        ("the strict lore: home fav / road dog, total under 49", lambda x: x["g"]["total"] is not None and x["g"]["total"] < 49
         and ((x["kind"] == "fav" and x["home"]) or (x["kind"] == "dog" and not x["home"]))),
        ("total under 49, any Wong leg, not a road favorite", lambda x: x["g"]["total"] is not None and x["g"]["total"] < 49
         and not (x["kind"] == "fav" and not x["home"])))
for name, f in CUTS:
    o(f"-- {name}")
    for en, a, b in ERAS:
        o(f"   {en:18s} {rate([x for x in L if f(x) and a <= x['season'] <= b])}")
o("\n== BY SEASON, every Wong leg (win %, n) ==")
row = []
for y in range(1999, 2027):
    ls = [x for x in L if x["season"] == y]
    row.append(f"{y % 100:02d}:{pct(ls):.0f}({len(ls)})")
o(" ".join(row))
up = {p: sum(1 for y in range(2015, 2027) if pct([x for x in L if x['season'] == y]) > BE[p]) for p in BE}
o("blind seasons (2015-26, 12) with the leg rate over the break-even:", up)
up = {p: sum(1 for y in range(1999, 2015) if pct([x for x in L if x['season'] == y]) > BE[p]) for p in BE}
o("train seasons (1999-2014, 16) over the break-even:", up)

o("\n== THE CONTROL: the same six points on NON-Wong legs (does the 3 / 7 crossing matter?) ==")
for name, lo_f, hi_f, lo_d, hi_d in (("favs -9..-10 / dogs +3..+4 (tease lands off the keys)", 9, 10, 3, 4),
                                     ("favs -4.5..-6.5 (to +1.5..-0.5) / dogs +4.5..+6.5", 4.5, 6.5, 4.5, 6.5),
                                     ("favs -3..-4 / dogs +7.5..+9 ", 3, 4, 7.5, 9),
                                     ("favs -1..-2.5 / dogs +9.5..+13", 1, 2.5, 9.5, 13)):
    LL = [x for g in G for x in legs(g, lo_f, hi_f, lo_d, hi_d)]
    o(f"-- {name}")
    for en, a, b in ERAS[:3]:
        o(f"   {en:18s} {rate([x for x in LL if a <= x['season'] <= b])}")
allL = [x for g in G for x in legs(g, 0.5, 30, 0.5, 30)]
o("-- every side teased 6 (the base):")
for en, a, b in ERAS[:3]:
    o(f"   {en:18s} {rate([x for x in allL if a <= x['season'] <= b])}")

o("\n== THE HALF-POINT INSIDE THE WINDOW (blind 2015-26 / all) ==")
for ln in (-8.5, -8.0, -7.5, 1.5, 2.0, 2.5):
    o(f"   line {ln:+.1f}: all {rate([x for x in L if x['line'] == ln])} | blind {rate([x for x in L if x['line'] == ln and x['season'] >= 2015])}")
for ln in (-9.0, -7.0, 1.0, 3.0):
    LL = [x for g in G for x in legs(g, abs(ln), abs(ln), abs(ln), abs(ln)) if x["line"] == ln]
    o(f"   (outside) line {ln:+.1f}: all {rate(LL)} | blind {rate([x for x in LL if x['season'] >= 2015])}")


def tickets(ls, how):
    """two-leg tickets inside a week: 'all' = every pair of legs in different games; 'one' = the first two legs by
    kickoff (one ticket a week)."""
    by = {}
    for x in ls:
        by.setdefault((x["season"], x["week"]), []).append(x)
    out = []
    for k, v in sorted(by.items()):
        v.sort(key=lambda x: (x["g"]["date"], x["g"]["time"], x["g"]["gid"]))
        if how == "one":
            pairs = [(v[0], v[1])] if len(v) >= 2 and v[0]["g"]["gid"] != v[1]["g"]["gid"] else []
        elif how == "seq":
            pairs = [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
        else:
            pairs = [p for p in itertools.combinations(v, 2) if p[0]["g"]["gid"] != p[1]["g"]["gid"]]
        for a, b in pairs:
            if a["res"] < 0 or b["res"] < 0:
                r = -1
            elif a["res"] == 0 or b["res"] == 0:
                r = 0
            else:
                r = 1
            out.append((k[0], r))
    return out


def tix(ls, how, price):
    d = nfl.dec(price)
    return [(s, (d - 1) if r > 0 else (0.0 if r == 0 else -1.0)) for s, r in tickets(ls, how)]


o("\n== TWO-TEAM TICKETS at the real price ==")
for name, f in (CUTS[0], CUTS[7], CUTS[13], CUTS[14], CUTS[1], CUTS[2]):
    ls = [x for x in L if f(x)]
    o(f"-- {name}")
    for how, hn in (("seq", "legs paired in kickoff order (no leg used twice)"), ("all", "every pair in the week (legs reused)")):
        for price in (-110, -120, -130, -135):
            t = tix(ls, how, price)
            tr = [p for s, p in t if s <= 2014]
            bl = [p for s, p in t if s >= 2015]
            r2 = [p for s, p in t if s >= 2020]
            upb = nfl.by_season([(s, p) for s, p in t if s >= 2015])
            upt = nfl.by_season([(s, p) for s, p in t if s <= 2014])
            o(f"   {hn[:28]:28s} {price}: all {nfl.st([p for s, p in t])} | train {nfl.roi(tr):+.1f}% ({upt[0]}/{upt[1]} up) | BLIND {nfl.st(bl)} ({upb[0]}/{upb[1]} up) | 2020-26 {nfl.st(r2)}")
        if how == "seq":
            o("      blind by season at -120:", nfl.by_season([(s, p) for s, p in tix(ls, how, -120) if s >= 2015])[2])
            o("      blind by season at -130:", nfl.by_season([(s, p) for s, p in tix(ls, how, -130) if s >= 2015])[2])

o("\n== PLACEBO: random pairs of teased-6 NON-Wong legs, same count as the blind Wong tickets, -120 ==")
non = [x for x in allL if x["season"] >= 2015 and not (-8.5 <= x["line"] <= -7.5 or 1.5 <= x["line"] <= 2.5)]
tb = [p for s, p in tix(L, "seq", -120) if s >= 2015]
real = nfl.roi(tb)
beat = 0
N = 2000
d = nfl.dec(-120)
for _ in range(N):
    smp = random.sample(non, 2 * len(tb))
    ps = []
    for i in range(0, len(smp), 2):
        a, b = smp[i], smp[i + 1]
        ps.append(-1.0 if (a["res"] < 0 or b["res"] < 0) else (0.0 if 0 in (a["res"], b["res"]) else d - 1))
    if nfl.roi(ps) >= real:
        beat += 1
o(f"   the blind Wong tickets {real:+.1f}% on {len(tb)}; a random set of non-Wong 6-point tickets did as well {beat} of {N} times")
o("\ncells read: ~15 leg cuts x 6 eras + 4 controls + 10 half-point rows + 6 x 2 x 4 ticket rows = ~160")
o.save()
