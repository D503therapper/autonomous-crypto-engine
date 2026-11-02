"""STUDY 5 - THE BACK-TO-BACK PRICED AT THE OPEN vs THE MORNING (only the paid history can say this): the next-day line
is up ~28 hours out, often BEFORE night 1 of a back-to-back is played; by the 8 AM board the books know night 1's
result and lean on the goalie news. Is the b2b edge (the hockey read's one term - the rested dog vs a tired favorite) gone
by the morning, or still there? Same games at both prices. Plus the road team that crossed 2+ time zones, and the
tired dog. TRAIN = 2020-21 + 2021-22, HELD OUT = 2022-23 (the open is thin there)."""
import json
import statistics
import lib

D = lib.build()
ROWS = [r for r in D["rows"] if lib.in_seasons(r)]
BOTH = [r for r in ROWS if r["open"] and r["morning"]]
out = []


def P(s):
    print(s); out.append(s)


def bet(r, s, at):
    if at == "close":
        d = lib.dec(r["ch"] if s == "h" else r["ca"])
    else:
        d = r[at]["dh"] if s == "h" else r[at]["da"]
    won = r["hw"] if s == "h" else 1 - r["hw"]
    return (r["season"], (d - 1) if won else -1.0, 1)


def pside(r, s, at):
    p = r["p_close"] if at == "close" else r[at]["p"]
    return p if s == "h" else 1 - p


def cell(name, pick):
    """pick(r) -> side or None. Same games, priced at the open / the morning / the close; plus the mean move."""
    xs = [(r, pick(r)) for r in BOTH]
    xs = [(r, s) for r, s in xs if s]
    if not xs:
        P(f"{name}: none"); return
    for at in ("open", "morning", "close"):
        P(lib.line(f"{name} @ {at}", lib.st([bet(r, s, at) for r, s in xs])))
    om = [100 * (pside(r, s, "morning") - pside(r, s, "open")) for r, s in xs]
    mc = [100 * (pside(r, s, "close") - pside(r, s, "morning")) for r, s in xs]
    P(f"   move toward this side: open -> morning {statistics.mean(om):+.2f} pts, morning -> close {statistics.mean(mc):+.2f} pts (n {len(xs)})")


def dogside(r, at="open"):
    return "h" if r[at]["p"] < 0.5 else "a"


def am(r, s, at="open"):
    d = r[at]["dh"] if s == "h" else r[at]["da"]
    return (d - 1) * 100 if d >= 2 else -100 / (d - 1)


def rested_dog_vs_b2b_fav(r):
    s = dogside(r); o = "a" if s == "h" else "h"
    return s if r[f"b2b_{o}"] and not r[f"b2b_{s}"] and 100 <= am(r, s) <= 350 else None


def tired_dog(r):
    s = dogside(r); o = "a" if s == "h" else "h"
    return s if r[f"b2b_{s}"] and not r[f"b2b_{o}"] and 100 <= am(r, s) <= 350 else None


def rested_fav_vs_b2b_dog(r):
    s = dogside(r); o = "a" if s == "h" else "h"
    return o if r[f"b2b_{s}"] and not r[f"b2b_{o}"] and -150 <= am(r, o) <= -101 else None


def rested_side_any(r):
    if r["b2b_h"] and not r["b2b_a"]:
        return "a"
    if r["b2b_a"] and not r["b2b_h"]:
        return "h"
    return None


P(f"games with both the open and the morning: {len(BOTH)}")
cell("THE REST EDGE - the rested side vs a b2b side (any price)", rested_side_any)
cell("the rested DOG vs a b2b favorite (+100..+350 at the open) - the hockey Dog's cell", rested_dog_vs_b2b_fav)
cell("the TIRED dog (b2b) vs a rested favorite", tired_dog)
cell("the rested FAVORITE -101..-150 vs a b2b dog", rested_fav_vs_b2b_dog)
cell("no b2b either side - every dog", lambda r: dogside(r) if not r["b2b_h"] and not r["b2b_a"] and 100 <= am(r, dogside(r)) <= 350 else None)

P("\n-- was night 1 already played when the open went up? (the open's hours-to-puck-drop vs the b2b team's night-1 game)")
pre, post = [], []
for r in BOTH:
    s = rested_side_any(r)
    if not s:
        continue
    o = "a" if s == "h" else "h"
    # night 1 ended ~ 24h before this game; the open was taken r['open']['hrs'] before - over ~26h = before night 1 ended
    (pre if r["open"]["hrs"] > 26 else post).append((r, s))
for nm, xs in (("open taken BEFORE night 1 ended", pre), ("open taken after night 1", post)):
    for at in ("open", "morning"):
        P(lib.line(f"  rested side, {nm} @ {at}", lib.st([bet(r, s, at) for r, s in xs])))
    if xs:
        P(f"    move to the rested side open -> morning {statistics.mean(100 * (pside(r, s, 'morning') - pside(r, s, 'open')) for r, s in xs):+.2f} pts")

P("\n-- the b2b favorite's goalie on night 2 (the ACTUAL starter - explains the move): rested dog vs a b2b favorite")
for nm, f in (("the favorite started its BACKUP", lambda r, o: r[f"bk_{o}"] is True), ("the favorite started its #1", lambda r, o: r[f"bk_{o}"] is False)):
    xs = []
    for r in BOTH:
        s = rested_dog_vs_b2b_fav(r)
        if s:
            o = "a" if s == "h" else "h"
            if f(r, o):
                xs.append((r, s))
    for at in ("open", "morning", "close"):
        P(lib.line(f"  {nm} @ {at}", lib.st([bet(r, s, at) for r, s in xs])))
    if xs:
        P(f"    move to the dog open -> morning {statistics.mean(100 * (pside(r, s, 'morning') - pside(r, s, 'open')) for r, s in xs):+.2f}, morning -> close {statistics.mean(100 * (pside(r, s, 'close') - pside(r, s, 'morning')) for r, s in xs):+.2f}")

P("\n-- TRAVEL: the road team crossed 2+ time zones since its last game (not a b2b)")
cell("road team after 2+ time zones (any price)", lambda r: "a" if r["travel_a"] >= 2 and not r["b2b_a"] else None)
cell("road DOG after 2+ time zones", lambda r: "a" if r["travel_a"] >= 2 and not r["b2b_a"] and dogside(r) == "a" and 100 <= am(r, "a") <= 350 else None)
cell("home side vs a road team after 2+ time zones", lambda r: "h" if r["travel_a"] >= 2 and not r["b2b_a"] else None)

json.dump(out, open(f"{lib.OUT}/s5_out.json", "w"), indent=0)
open(f"{lib.OUT}/s5_out.txt", "w").write("\n".join(out) + "\n")
