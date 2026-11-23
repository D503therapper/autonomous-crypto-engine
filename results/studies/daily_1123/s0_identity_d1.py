"""11/23 - THE BUG FIX'S REPLAY: the college hoops team identity (sports_ncaab_box.identity - defense-first /
offense-first / the turnover margin / the turnover matchup) read on DIVISION I games only, against the read as built
(every boxed game, non-D1 tune-ups in). Every engine weight that stands on identity, as built / D1-only / the sides the
re-cut drops and adds; then the dog slot's own replay rows (the 11/16 funnel) with the defense-first fact re-cut.
ESPN's close at its own juice, D1-vs-D1 regular season, box seasons 2021-26 (train 2021-23 / held 2024-26).
python results/studies/daily_1123/s0_identity_d1.py"""
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_ncaab_box as nb  # noqa: E402

G = sd.load_games("ncaab")
fin = sm.finals(G, "ncaab")
D1 = sm.ncaab_d1(fin)
BT, BH = (2021, 2023), [2024, 2025, 2026]
O = h.Out("s0_identity_d1", BT, BH)
O.p("S0 - THE IDENTITY ON D1 GAMES ONLY (box seasons 2021-26; train 2021-23 / held 2024-26; ESPN's close)")
idc = {}


def ident(t, st, d1):
    k = (t, st, d1)
    if k not in idc:
        idc[k] = nb.identity(G, t, st, d1_only=d1)
    return idc[k]


def flags(me, op):
    if not me or not op:
        return None
    return {"def_first": nb.def_first(me) and nb.off_low(op),
            "off_first": nb.off_first(me),
            "prone": me["tom"] <= nb.TOM_PRONE,
            "to_lose": ((me["ftor"] - me["tor"]) - (op["ftor"] - op["tor"])) <= -0.05 + 1e-9}


def pct(v, q):
    v = sorted(v)
    return v[int(q * (len(v) - 1))]


dist = {False: {"off": [], "def": []}, True: {"off": [], "def": []}}
for g in fin:
    s_ = lib.season(g["start"])
    if not 2021 <= s_ <= 2023 or str(g.get("stype") or "2") != "2" or g["home"] not in D1 or g["away"] not in D1:
        continue
    for t in (g["home"], g["away"]):
        for d1 in (False, True):
            i = ident(t, g["start"], d1)
            if i and i.get("off") is not None:
                dist[d1]["off"].append(i["off"])
                dist[d1]["def"].append(i["def"])
for d1 in (False, True):
    O.p(f"the thirds on the train seasons 2021-23, {'D1 games only' if d1 else 'every boxed game (as built)'}: "
        f"{len(dist[d1]['off'])} team-games | defense best third <= {pct(dist[d1]['def'], 1/3):+.2f} | offense top third >= "
        f"{pct(dist[d1]['off'], 2/3):+.2f} | offense bottom third <= {pct(dist[d1]['off'], 1/3):+.2f}")
O.p(f"the built cuts: defense {nb.DEF_GOOD}, offense top {nb.OFF_HI}, bottom {nb.OFF_LO}; the D1 cuts in the module: "
    f"defense {nb.DEF_GOOD_D1}, offense top {nb.OFF_HI_D1}, bottom {nb.OFF_LO_D1}")
FACT = {}          # (gid, side) -> (the built flags, the D1-only flags)
for g in fin:
    st = g["start"]
    s = lib.season(st)
    if s < 2021 or str(g.get("stype") or "2") != "2" or g["home"] not in D1 or g["away"] not in D1:
        continue
    mlh, mla = lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (KeyError, TypeError, ValueError):
        continue
    late = st[5:7] in ("01", "02", "03")
    for side, t, o_, od in (("home", g["home"], g["away"], mlh), ("away", g["away"], g["home"], mla)):
        fa = flags(ident(t, st, False), ident(o_, st, False))
        fd = flags(ident(t, st, True), ident(o_, st, True))
        FACT[(g["id"], side)] = (fa, fd)
        if not od or not mlh or not mla or hs == as_:
            continue
        won = (hs > as_) == (side == "home")
        pr = lib.profit(won, lib.dec(od))
        dog, fav = 100 <= od <= 350, -150 <= od <= -101
        per = "Jan-Mar" if late else "Nov-Dec"
        if dog and (fa or fd):
            O.add("dog base (either read known)", s, pr, od)
            O.add(f"dog base | {per}", s, pr, od)
        if fav and (fa or fd):
            O.add("small fav base (either read known)", s, pr, od)
        for nm, key, grp in (("defense-first dog vs a bottom-third offense (+2 on the dog read)", "def_first", dog),
                             ("turnover-prone small favorite (-2 on its read)", "prone", fav),
                             ("dog losing the turnover matchup by .05+ (-2 on the dog)", "to_lose", dog),
                             ("offense-first dog Jan-Mar (-1 on the dog read)", "off_first", dog and late)):
            if not grp:
                continue
            a, d = bool(fa and fa[key]), bool(fd and fd[key])
            if a:
                O.add(f"{nm} | AS BUILT (every boxed game)", s, pr, od)
                if key == "def_first":
                    O.add(f"{nm} | AS BUILT | {per}", s, pr, od)
            if d:
                O.add(f"{nm} | D1 GAMES ONLY", s, pr, od)
                if key == "def_first":
                    O.add(f"{nm} | D1 GAMES ONLY | {per}", s, pr, od)
            if a and not d:
                O.add(f"{nm} | DROPPED by the re-cut (built yes, D1 no)", s, pr, od)
            if d and not a:
                O.add(f"{nm} | ADDED by the re-cut (D1 yes, built no)", s, pr, od)
            if a and d:
                O.add(f"{nm} | BOTH reads agree", s, pr, od)
O.show()
nm = "defense-first dog vs a bottom-third offense (+2 on the dog read)"
O.placebo(nm + " | DROPPED by the re-cut (built yes, D1 no)", nm + " | AS BUILT (every boxed game)", fade=True)
O.placebo(nm + " | D1 GAMES ONLY", "dog base (either read known)")
O.placebo(nm + " | AS BUILT (every boxed game)", "dog base (either read known)")

# ------------------------------------------------------------ the dog slot on its replay rows
O.p("")
O.p("THE DOG SLOT'S REPLAY (the 11/16 funnel rows; the slot as live: read 4+ with the 11/14 home-dog -1, both teams 4+")
O.p("games, the read clears the price, best two a night) - with the defense-first / offense-first facts re-cut on D1 games")
R = pickle.load(open(os.path.expanduser("~/.cache/d503_maxcol1116/cbb_rows.pkl"), "rb"))
S = h.Out("s0_slot", (2021, 2023), [2024, 2025, 2026])
S.lines = O.lines


def live_read(r):
    x = r["dog_read"]
    if r.get("where") == "home" and not (r.get("dog_read_parts") or {}).get("home"):
        if not ((r.get("effgap") or 0) >= 0.15):
            x -= 1
    return x


def slot(use_d1):
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in R:
        if r.get("market", "ml") != "ml" or not 100 <= r["odds"] <= 350 or r.get("dog_read") is None or r["mn"] < 4:
            continue
        if r["season"] < 2021:
            continue
        lr = live_read(r)
        delta = 0
        if use_d1:
            fa, fd = FACT.get((r["gid"], r["side"]), (None, None))
            late = r["date"][5:7] in ("01", "02", "03")
            delta += 2 * (bool(fd and fd["def_first"]) - bool(fa and fa["def_first"]))
            if late:
                delta -= (bool(fd and fd["off_first"]) - bool(fa and fa["off_first"]))
        lr += delta
        if lr < 4 or min(0.95, r["p_market"] + lr / 100) * r["dec"] - 1 <= 0:
            continue
        if r["gid"] in lockg or r["kind"] in ("stackplay", "floor"):
            continue
        pool[r["date"]].append(dict(r, lr=lr, delta=delta))
    out = []
    for d, v in pool.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["lr"], -(r.get("effgap") or 0))):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                if len(seen) <= 2:
                    out.append(r)
    return out


old, new = slot(False), slot(True)
ko = {(r["gid"], r["side"]) for r in old}
kn = {(r["gid"], r["side"]) for r in new}
for r in old:
    S.add("slot AS BUILT (2021-26)", r["season"], r["pnl"], r["odds"])
    if (r["gid"], r["side"]) not in kn:
        S.add("slot picks the re-cut DROPS", r["season"], r["pnl"], r["odds"])
    if r["date"][5:7] in ("11", "12"):
        S.add("slot AS BUILT | Nov-Dec", r["season"], r["pnl"], r["odds"])
for r in new:
    S.add("slot WITH THE D1-ONLY IDENTITY (2021-26)", r["season"], r["pnl"], r["odds"])
    if (r["gid"], r["side"]) not in ko:
        S.add("slot picks the re-cut ADDS", r["season"], r["pnl"], r["odds"])
    if r["date"][5:7] in ("11", "12"):
        S.add("slot WITH THE D1-ONLY IDENTITY | Nov-Dec", r["season"], r["pnl"], r["odds"])
S.show()
S.placebo("slot picks the re-cut DROPS", "slot AS BUILT (2021-26)", fade=True)
for r in sorted(old, key=lambda r: r["date"]):
    if (r["gid"], r["side"]) not in kn:
        S.p(f"   dropped {r['date']} {r['team']} {r['odds']:+d} vs {r['opp']}  read {r['lr']:g}  {r['result']}")
for r in sorted(new, key=lambda r: r["date"]):
    if (r["gid"], r["side"]) not in ko:
        S.p(f"   added   {r['date']} {r['team']} {r['odds']:+d} vs {r['opp']}  read {r['lr']:g}  {r['result']}")
O.p("")
for gid, g in G.items():
    if str(g.get("start", ""))[:10] in ("2026-11-22", "2026-11-23") and "Nicholls" in (str(g.get("home_name")) + str(g.get("away_name"))):
        for side in ("home", "away"):
            O.p(f"   {g.get(side + '_name')} {g['start'][:10]}: as built {nb.identity(G, g[side], g['start'], d1_only=False)}")
            O.p(f"   {'':20s} D1 only  {nb.identity(G, g[side], g['start'], d1_only=True)}")
O.save()
