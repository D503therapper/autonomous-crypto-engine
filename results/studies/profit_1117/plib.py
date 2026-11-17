"""11/17 - THE MAX-PROFIT SIZING PLAN - the shared rig. money_1117's board (mlib.board, R3L: the board re-built on TODAY's
code, 2023-10 -> 2026-11 at the closing price) with the sizes as PIECES that can be switched on together - they interact
(the ⭐ goes on the day's biggest play of its kind, so a bigger size moves the ⭐). TODAY = the 11/17 code with the money
study's one change in (the short hockey runner-up dog 1u).
A piece = (name, test(r) -> bool, the new size for the kind). The ⭐ is re-picked on the new sizes (the same order as
mlib: the 3u play first, the kind's rank, the bigger size, the bigger edge) and raised to STAR at least."""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "money_1117"))
import mlib as M  # noqa: E402

P, DAYS = M.board()
NL = [r for r in P if M.half(r["date"]) != "live"]
YEARS = 3.03
BY = defaultdict(list)
for _r in P:
    BY[_r["date"]].append(_r)


def k(r):
    return r["k"].rsplit(" (", 1)[0]


def today0(r):
    """the kind's own size on today's code (the ⭐ raise off): the money study's short hockey runner-up at 1u is in."""
    if r["kind"] == "dogplay" and r["league"] == "nhl" and r["odds"] <= 150:
        return 1.0
    return r["u0"]


PIECES = {
    "ru2": ("the hockey runner-up dog +100..+150 at 2u (now 1u)", lambda r: r["kind"] == "dogplay" and r["league"] == "nhl" and r["odds"] <= 150, 2.0),
    "ru_long": ("the hockey runner-up dog +151..+350 at 1u", lambda r: r["kind"] == "dogplay" and r["odds"] > 150, 1.0),
    "cfb_thin": ("the college football thin Lock at 1u", lambda r: k(r) == "Lock - college football, thin", 1.0),
    "nbafloor": ("the NBA floor dog at 1u", lambda r: r["kind"] == "nbafloor", 1.0),
    "nhl_fav": ("the hockey favorite value play at 1u", lambda r: k(r) == "value play - hockey favorite", 1.0),
    "oth_fav": ("the other favorite value plays at 1u (college hoops / NBA / football, the college hoops favorite slot)",
                lambda r: (r["kind"] == "play" and r["league"] != "nhl") or k(r) == "college hoops favorite slot", 1.0),
    "nhl_long": ("the hockey Dog +151..+350 at 1u", lambda r: k(r) == "Dog - hockey +151..+350", 1.0),
    "nba_dog": ("the NBA Dog (½u thin) at 1u", lambda r: r["kind"] == "dog" and r["league"] == "nba" and r["u0"] <= 0.5, 1.0),
    "nfl_lock": ("the NFL Lock at 1u", lambda r: k(r) == "Lock - NFL", 1.0),
    "nfl_long": ("the NFL Dog +151..+350 / one-game picks at 1u", lambda r: k(r).startswith("Dog - NFL +151") or r["kind"] in ("solo", "night"), 1.0),
    "floor": ("the floor's dogs at 1u", lambda r: r["kind"] == "floor", 1.0),
    "nbafav2": ("the NBA favorite play at 2u (now 1u)", lambda r: r["kind"] == "nbafav", 2.0),
    "cbb4_2": ("the college hoops dog slot at a read of 4 at 2u (now 1u)", lambda r: k(r) == "college hoops dog slot, read 4", 2.0),
}
HALF_ALL = ["ru_long", "cfb_thin", "nbafloor", "nhl_fav", "oth_fav", "nhl_long", "nba_dog", "nfl_lock", "nfl_long", "floor"]


def sizes(pieces=(), star=1.0, star_from=0.0, star_ok=None):
    """-> {id(r): (u0, u, star?)} for the bundle. star = the ⭐'s least size; star_from = the ⭐ is raised past 1u only
    when the play's own size is this or more (0 = always); star_ok(r) = the ⭐ is raised past 1u only on these."""
    out = {}
    for d, ps in BY.items():
        u0 = {}
        for r in ps:
            u = today0(r)
            for p in pieces:
                _, t, nu = PIECES[p]
                if t(r):
                    u = max(u, nu)
            u0[id(r)] = u
        pool = [r for r in ps if -150 <= r["odds"] <= 350 and not r.get("fighting") and M.margin(r) > 0
                and not (r["kind"] == "lock" and r["league"] == "nfl")]
        b = min(pool, key=lambda r: (-1 if u0[id(r)] >= 3 else M.RANK.get(r["kind"], 9), -u0[id(r)], -M.margin(r))) if pool else None
        for r in ps:
            u = u0[id(r)]
            if r is b:
                u = max(1.0, u)
                if u0[id(r)] >= star_from and (star_ok is None or star_ok(r)):
                    u = max(star, u)
            out[id(r)] = (u0[id(r)], u, r is b)
    return out


def summ(sz):
    return M.summ(P, DAYS, lambda r: sz[id(r)][1])


def row(name, o, base=None):
    yr = o["net"] / YEARS
    s = (f"  {name:58s} {yr:+6.1f}u/yr ({o['net']:+6.1f}u on {o['risk']:6.0f}u) ROI {o['roi']:+5.1f}% | train {o['tr']:+6.1f}u {M.roi(o['tr'], o['trr']):+5.1f}%"
         f" | held {o['he']:+6.1f}u {M.roi(o['he'], o['her']):+5.1f}% | worst stretch {o['dd']:+6.1f}u"
         f" | worst season {min(o['seas'].values()):+5.1f}u | up {o['up']}/{o['ns']} | live {o['live'][0]}-{o['live'][1]} {o['live'][2]:+.1f}u")
    if base:
        s += f" | vs today {(o['net'] - base['net']) / YEARS:+5.1f}u/yr, worst x{o['dd'] / base['dd']:.2f}"
    return s


def added(sz_a, sz_b, test=lambda r: True):
    """what the units b adds over a earn, on the plays `test` picks: (n plays, train added u, train gain, held added u, held gain)."""
    n = 0
    t = {"train": [0.0, 0.0], "held": [0.0, 0.0]}
    for r in NL:
        d = sz_b[id(r)][1] - sz_a[id(r)][1]
        if abs(d) < 1e-9 or not test(r):
            continue
        n += 1
        h = M.half(r["date"])
        t[h][0] += d
        t[h][1] += d * M.flat(r)
    return n, t["train"][0], t["train"][1], t["held"][0], t["held"][1]


def added_str(a):
    n, tu, tg, hu, hg = a
    return (f"{n:4d} plays; the added units {tg + hg:+6.1f}u on {tu + hu:5.1f}u ({M.roi(tg + hg, tu + hu):+5.1f}%) | train {tg:+5.1f}u {M.roi(tg, tu):+5.1f}%"
            f" | HELD OUT {hg:+5.1f}u {M.roi(hg, hu):+5.1f}%")
