"""10/30 SIZING, step 2: size schedules on the same board unit plays (board.py - today's rules, 1,097 replay board days +
the live stretch). Every schedule is a function (kind, row, units_today) -> units. Judged on: units won, ROI, the worst
stretch (peak-to-trough, by day), seasons up, train (2023-25) vs held out (2025-27), and units won per unit of worst
stretch. A size-up counts only if its cell wins MORE vs the price in BOTH halves (signals.out) - the size is the owner's
confidence signal. Usage: python sizing.py > sizing.out"""
from collections import defaultdict

from board import PLAYS, half, pnl, season, gap, days

LIVE_FROM = "2026-10-13"


def lock_edge(r):
    return r.get("edge_own") or 0


def run(name, fn, kinds=None, quiet=False):
    per_day = defaultdict(float)
    by_half = defaultdict(lambda: [0, 0, 0.0, 0.0])
    seas = defaultdict(float)
    for d, r, k, u in PLAYS:
        if kinds and k not in kinds:
            continue
        nu = fn(k, r, u)
        if not nu:
            continue
        p = pnl(r, nu)
        h = half(d)
        s = by_half[h]
        s[0] += r["result"] == "won"
        s[1] += r["result"] == "lost"
        s[2] += p
        s[3] += nu
        if h != "live":
            per_day[d] += p
            seas[season(d)] += p

    def worst(ds):
        cum = peak = w = 0.0
        for d in ds:
            cum += per_day.get(d, 0.0)
            peak = max(peak, cum)
            w = min(w, cum - peak)
        return w
    tr = [d for d in days if d < "2025-07-01"]
    he = [d for d in days if "2025-07-01" <= d < LIVE_FROM]
    al = tr + he
    out = []
    for lab, h, ds in (("train", "train", tr), ("held", "held", he)):
        w, l, net, risk = by_half[h]
        out.append(f"{lab} {w}-{l} {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}% dd {worst(ds):+5.1f}")
    w = by_half["train"][0] + by_half["held"][0]
    l = by_half["train"][1] + by_half["held"][1]
    net = by_half["train"][2] + by_half["held"][2]
    risk = by_half["train"][3] + by_half["held"][3]
    dd = worst(al)
    up = sum(v > 0 for v in seas.values())
    lv = by_half["live"]
    if not quiet:
        print(f"{name:58s} | " + " | ".join(out) + f" | ALL {w}-{l} {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}% "
              f"dd {dd:+5.1f} up {up}/{len(seas)} u/dd {net / -dd if dd else 0:4.1f} | live {lv[0]}-{lv[1]} {lv[2]:+5.1f}u")
    return net, dd


TODAY = lambda k, r, u: u          # noqa: E731


def with_(**over):
    """today's sizes with some kinds replaced: over[kind] = fn(r, u) -> units."""
    def f(k, r, u):
        return over[k](r, u) if k in over else u
    return f


FOOTBALL = ("nfl", "ncaaf")


def lock_flat(n):
    return lambda r, u: n


def lock_by_edge(lo_u, hi_u, cut=0.08, football_cap=None):
    """the Lock: hi_u while its own read beats the price by 3%..cut (the Locks that win more), lo_u past cut (the big-edge
    Locks - three studies: they're the worst)."""
    def f(r, u):
        n = hi_u if lock_edge(r) < cut else lo_u
        if football_cap is not None and r["league"] in FOOTBALL:
            n = min(n, football_cap)
        return n
    return f


def dog_band(short_u, long_u, cut=150, thin_u=0.5, hoops=None):
    """the Dog: short_u at +100..+cut, long_u past it; thin (today's ½u) stays thin_u; hoops (ncaab) its own."""
    def f(r, u):
        if r["league"] == "ncaab":
            return hoops if hoops is not None else u
        if r["league"] == "nba":
            return u
        if u <= 0.5:
            return thin_u
        return short_u if r["odds"] <= cut else long_u
    return f


if __name__ == "__main__":
    print("== THE BOARD, every unit play kind (today's rules), size schedules")
    run("TODAY (Lock 3u/1u, Dog 2u own-over / ½u thin, plays ½u ...)", TODAY)
    run("everything flat 1u", lambda k, r, u: 1)
    print("\n== THE LOCK alone (lock kind)")
    for name, f in (("today 3u both reads / 1u", TODAY), ("flat 1u", lambda k, r, u: 1), ("flat 2u", lambda k, r, u: 2),
                    ("flat 3u", lambda k, r, u: 3), ("flat ½u", lambda k, r, u: 0.5),
                    ("today, football capped 1u", lambda k, r, u: min(u, 1) if r["league"] in FOOTBALL else u),
                    ("2u own edge 3-8%, 1u 8%+", lambda k, r, u: lock_by_edge(1, 2)(r, u)),
                    ("2u own edge 3-8%, 1u 8%+, football 1u", lambda k, r, u: lock_by_edge(1, 2, football_cap=1)(r, u)),
                    ("3u own edge 3-8%, 1u 8%+", lambda k, r, u: lock_by_edge(1, 3)(r, u)),
                    ("2u own edge 3-6%, 1u 6%+", lambda k, r, u: lock_by_edge(1, 2, cut=0.06)(r, u)),
                    ("2u own edge 3-10%, 1u 10%+", lambda k, r, u: lock_by_edge(1, 2, cut=0.10)(r, u)),
                    ("1u own edge 3-8%, ½u 8%+", lambda k, r, u: lock_by_edge(0.5, 1)(r, u)),
                    ("by price: 2u -150..-135, 1u -134..-120", lambda k, r, u: 2 if r["odds"] <= -135 else 1),
                    ("Kelly-ish on own read (¼ Kelly, ½-5u)", lambda k, r, u: max(0.5, min(5, round(0.25 * r["edge_own"] / (r["dec"] - 1) * 100 * 2) / 2)))):
        run(name, f, kinds=("lock",))
    print("\n== THE DOG OF THE DAY alone (dog kind; NBA / hoops untouched unless named)")
    dogs = (("today (2u own-over, ½u thin; NBA 1u/½u, hoops ½u)", TODAY),
            ("flat 1u (all sports)", lambda k, r, u: 1),
            ("flat 2u (all sports)", lambda k, r, u: 2),
            ("thin dogs 2u too (no thin cut)", lambda k, r, u: 2 if u <= 0.5 and r["league"] not in ("nba", "ncaab") else u),
            ("thin dogs 1u", lambda k, r, u: 1 if u <= 0.5 and r["league"] not in ("nba", "ncaab") else u),
            ("2u to +150, 1u past", lambda k, r, u: dog_band(2, 1)(r, u)),
            ("2u to +160, 1u past", lambda k, r, u: dog_band(2, 1, cut=160)(r, u)),
            ("2u to +150, ½u past", lambda k, r, u: dog_band(2, 0.5)(r, u)),
            ("3u to +150, 1u past", lambda k, r, u: dog_band(3, 1)(r, u)),
            ("2u to +150, 1u past, thin 1u to +150", lambda k, r, u: (1 if r["odds"] <= 150 else 0.5) if u <= 0.5 and r["league"] not in ("nba", "ncaab") else dog_band(2, 1)(r, u)),
            ("2u to +150, 1u past, hoops ½u -> none", lambda k, r, u: 0 if r["league"] == "ncaab" else dog_band(2, 1)(r, u)))
    for name, f in dogs:
        run(name, f, kinds=("dog",))
    for lg in ("nhl", "ncaaf", "nba", "ncaab"):
        print(f"  -- the {lg} Dog")
        for name, f in dogs[:7]:
            run("   " + name, (lambda f, lg: lambda k, r, u: f(k, r, u) if r["league"] == lg else 0)(f, lg), kinds=("dog",))
    print("\n== THE OTHER KINDS, flat sizes")
    for k in ("play", "dogplay", "nbafav", "nbafloor", "floor", "floorfb"):
        for n in (0.5, 1, 2):
            run(f"{k} flat {n}u", lambda kk, r, u, n=n: n, kinds=(k,))
    print("\n== value plays by price (½u)")
    run("plays -150..-120", lambda k, r, u: u if r["odds"] <= -120 else 0, kinds=("play",))
    run("plays -119..-101", lambda k, r, u: u if r["odds"] > -120 else 0, kinds=("play",))
    print("\n== WHOLE-BOARD SCHEDULES")
    L = lock_by_edge(1, 2, football_cap=1)
    Dg = dog_band(2, 1)
    run("TODAY", TODAY)
    run("A: Lock flat 1u", with_(lock=lambda r, u: 1))
    run("B: Lock 2u (own 3-8%) / 1u (8%+), football 1u", with_(lock=L))
    run("C: B + Dog 2u to +150 / 1u past", with_(lock=L, dog=Dg))
    run("D: C + no value play at -119..-101", lambda k, r, u: 0 if k == "play" and r["odds"] > -120 else with_(lock=L, dog=Dg)(k, r, u))
    run("E: Lock 3u (own 3-8%) / 1u, football 1u + Dog 2u/1u", with_(lock=lock_by_edge(1, 3, football_cap=1), dog=Dg))
    run("F: Lock flat 1u + Dog 2u/1u", with_(lock=lambda r, u: 1, dog=Dg))
    run("G: today + football Lock 1u only", with_(lock=lambda r, u: min(u, 1) if r["league"] in FOOTBALL else u))


# ---------------------------------------------------------------- THE RECOMMENDED SCHEDULE (step 6, after cells / cuts)
def new_lock(r, u):
    """Lock: 1u in football (NFL / college - the Lock loses there in both 10/30 football studies); else 2u when its own read
    sits under 7 points over the no-vig market, 1u at 7+ (the big-gap Locks are the worst - 4 studies)."""
    if r["league"] in FOOTBALL:
        return 1
    g = gap(r)
    return 2 if g is not None and g < 7 else 1


def new_dog(r, u):
    """Dog: hockey / football 2u at +100..+150, ½u at +151..+350 - thin or not (the price separates, the edge size
    doesn't); NBA unchanged; no college hoops Dog."""
    if r["league"] == "ncaab":
        return 0
    if r["league"] == "nba":
        return u
    return 2 if r["odds"] <= 150 else 0.5


NEW = with_(lock=new_lock, dog=new_dog)

if __name__ == "__main__":
    print("\n== THE RECOMMENDED SCHEDULE vs TODAY")
    run("TODAY", TODAY)
    run("NEW: Lock 2u gap<7 / 1u 7+ / football 1u; Dog 2u to +150, ½u past", NEW)
    run("NEW but Lock flat 1u", with_(lock=lambda r, u: 1, dog=new_dog))
    run("NEW but Dog long 1u", with_(lock=new_lock, dog=lambda r, u: new_dog(r, u) if r["odds"] <= 150 or r["league"] in ("nba", "ncaab") else 1))
    run("NEW but the short Dog 3u", with_(lock=new_lock, dog=lambda r, u: 3 if new_dog(r, u) == 2 else new_dog(r, u)))
    run("NEW but the Lock 3u gap<7", with_(lock=lambda r, u: 3 if new_lock(r, u) == 2 else new_lock(r, u), dog=new_dog))
    run("NEW but the college hoops Dog kept at ½u", with_(lock=new_lock, dog=lambda r, u: u if r["league"] == "ncaab" else new_dog(r, u)))
    print("  -- the Lock and the Dog alone")
    run("   Lock TODAY", TODAY, kinds=("lock",))
    run("   Lock NEW", NEW, kinds=("lock",))
    run("   Dog TODAY", TODAY, kinds=("dog",))
    run("   Dog NEW", NEW, kinds=("dog",))
    print("  -- scaled to the same worst stretch as TODAY (every size x k)")
    base_net, base_dd = run("TODAY", TODAY, quiet=True)
    for name, f in (("TODAY", TODAY), ("NEW", NEW)):
        net, dd = run(name, f, quiet=True)
        print(f"   {name}: {net:+.1f}u, worst {dd:.1f}u -> per {-base_dd:.1f}u of worst stretch: {net * base_dd / dd:+.1f}u")
