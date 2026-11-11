"""STUDY 8b - THE BANGED-UP NFL DOG (+100..+350 at the close), every cut - is it the injuries or just a longshot?
Rows / measures from s8_nfl_inj.py (missing snaps = starters' worth of snap share listed Out / Doubtful, plus the
carried absences - a 50%+ regular who missed the last game and is off the report: injured reserve).
Usage: python s8b_nfl_dog.py > s8b_nfl_dog.out"""
import contextlib
import io
from collections import defaultdict

with contextlib.redirect_stdout(io.StringIO()):
    import s8_nfl_inj as S

rows, bet = S.rows, S.bet
S.N[0] = 0


def dogrow(r):
    """(dog side, the dog's missing minus the favorite's: listed, listed + carried, the dog's decimal price) or None."""
    if r["dh"] == r["da"]:
        return None
    s = "h" if r["dh"] > r["da"] else "a"
    d = r["dh"] if s == "h" else r["da"]
    if not 2.0 <= d <= 4.5:
        return None
    k = 1 if s == "h" else -1
    return s, (r["hmiss"] - r["amiss"]) * k, (r["hmissc"] - r["amissc"]) * k, d


def dogbet(name, f):
    bet(name, lambda r: (dogrow(r)[0] if f(*dogrow(r)[1:]) else None) if dogrow(r) else None)


print("THE NFL DOG +100..+350 at the close, weeks 3+, 2016-26 (train 2016-21 / held out 2022-26)")
dogbet("EVERY dog +100..+350 (the base)", lambda l, c, d: True)
for cut in (1.0, 1.5, 2.0, 2.5, 3.0):
    dogbet(f"dog misses {cut:g}+ MORE (listed + carried)", lambda l, c, d, cut=cut: c >= cut)
for cut in (1.0, 1.5, 2.0):
    dogbet(f"dog misses {cut:g}+ MORE (listed Out / Doubtful only)", lambda l, c, d, cut=cut: l >= cut)
dogbet("dog within 1 either way (listed + carried)", lambda l, c, d: -1 < c < 1)
for cut in (1.0, 2.0, 3.0):
    dogbet(f"dog is the HEALTHIER side by {cut:g}+ (listed + carried)", lambda l, c, d, cut=cut: c <= -cut)
dogbet("dog misses 2+ more, +100..+150", lambda l, c, d: c >= 2 and d <= 2.5)
dogbet("dog misses 2+ more, +151..+250", lambda l, c, d: c >= 2 and 2.5 < d <= 3.5)
dogbet("dog misses 2+ more, +251..+350", lambda l, c, d: c >= 2 and d > 3.5)
bet("home dog misses 2+ more", lambda r: ("h" if dogrow(r) and dogrow(r)[0] == "h" and dogrow(r)[2] >= 2 else None))
bet("road dog misses 2+ more", lambda r: ("a" if dogrow(r) and dogrow(r)[0] == "a" and dogrow(r)[2] >= 2 else None))
bet("weeks 3-9: dog misses 2+ more", lambda r: (dogrow(r)[0] if dogrow(r) and dogrow(r)[2] >= 2 and r["week"] <= 9 else None))
bet("weeks 10+: dog misses 2+ more", lambda r: (dogrow(r)[0] if dogrow(r) and dogrow(r)[2] >= 2 and r["week"] >= 10 else None))
print("  by season, the dog missing 2+ more (listed + carried):")
ss = defaultdict(list)
w = n = 0
e = 0.0
for r in rows:
    x = dogrow(r)
    if x and x[2] >= 2 and r["hs"] != r["as_"]:
        won = (r["hs"] > r["as_"]) == (x[0] == "h")
        ss[r["season"]].append((x[3] - 1) if won else -1.0)
        n += 1
        w += won
        e += r["pm"] if x[0] == "h" else 1 - r["pm"]
print("   " + "  ".join(f"{y} {sum(v) / len(v) * 100:+.0f}% ({len(v)})" for y, v in sorted(ss.items())))
print(f"  the dog missing 2+ more: won {w} of {n} ({100 * w / n:.1f}%) vs the no-vig close's {100 * e / n:.1f}% = {100 * (w - e) / n:+.1f} points")
for lo, hi in ((-99, -2), (-2, -1), (-1, 1), (1, 2), (2, 3), (3, 99)):
    w = n = 0
    e = 0.0
    for r in rows:
        x = dogrow(r)
        if x and lo <= x[2] < hi and r["hs"] != r["as_"]:
            n += 1
            w += (r["hs"] > r["as_"]) == (x[0] == "h")
            e += r["pm"] if x[0] == "h" else 1 - r["pm"]
    if n:
        print(f"  the dog's missing snaps minus the favorite's in [{lo}, {hi}): won {100 * w / n:.1f}% vs the no-vig close's {100 * e / n:.1f}% = {100 * (w - e) / n:+.1f} points on {n}")
print(f"\n{S.N[0]} cells here (+62 in s8)")
