"""11/21 daily studies S1-S4 - COLLEGE HOOPS AND THE NON-D1 GAMES (the board check asked: UT Rio Grande +160 2u went up
on "out-rebounding people by +7.2 a game" with 2 of its 5 box games against non-D1 schools).
  S1  the built GLASS weight (sports.NCAAB_REB_GAP 6 / the dog's +, the spread rank's +/-0.02) when the rebound margin
      holds non-D1 games - the margin as the engine reads it (every box game) against the same margin on D1 games only
  S2  the DOG SLOT's "both teams 4+ games" gate counted in D1 games (the 11/16 replay rows, the slot as it runs live)
  S3  the 1/2u SPREAD STACK play's replay with the 11/20 tune-up weight added (+0.02 off a non-D1 tune-up against a
      team off a D1 game, -0.02 across) - the 11/20 run's "next money step"
  S4  the favorite with NO Division I win (the card's "both of their wins came over schools that aren't Division I")
Prices: ESPN's close at its own juice, regular season, what a team did THIS season before tonight (no look-ahead).
Cells are fixed before the run. python results/studies/daily_1121/s_cbb.py"""
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_ncaab_roster as nr  # noqa: E402

TRAIN, HELD = (2016, 2021), [2022, 2023, 2024, 2025, 2026]
BTRAIN, BHELD = (2021, 2023), [2024, 2025, 2026]          # the box seasons


def load():
    cache = os.path.join(lib.CACHE, "_g1121_ncaab.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = []
    for g in sm.finals(sd.load_games("ncaab"), "ncaab"):
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError, TypeError):
            continue
        out.append({"id": g["id"], "start": g["start"], "season": lib.season(g["start"]), "home": g["home"], "away": g["away"],
                    "hs": hs, "as": as_, "mlh": lib.num(g.get("ml_home")), "mla": lib.num(g.get("ml_away")),
                    "sp": lib.num(g.get("spread_home")), "spho": lib.num(g.get("spread_home_odds")),
                    "spao": lib.num(g.get("spread_away_odds")), "neutral": str(g.get("neutral")) == "1",
                    "stype": str(g.get("stype") or "2")})
    out.sort(key=lambda x: x["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


fin = load()
D1 = sm.ncaab_d1(fin)
byid = {g["id"]: g for g in fin}
tl = lib.team_log(fin)


def opp_of(g, t):
    return g["away"] if g["home"] == t else g["home"]


def prior(t, g):
    return [x for x in lib.before(tl, t, g["start"]) if x["season"] == g["season"]]


def ml(g, side):
    o = g["mlh"] if side == "home" else g["mla"]
    if o is None or o == 0 or g["hs"] == g["as"]:
        return None, None
    won = (g["hs"] > g["as"]) == (side == "home")
    return o, lib.profit(won, lib.dec(o))


def priced(g):
    return g["stype"] == "2" and g["mlh"] and g["mla"] and g["home"] in D1 and g["away"] in D1


# ------------------------------------------------------------------ S1 the glass
def s1():
    O = h.Out("s1_glass", BTRAIN, BHELD)
    O.p("S1 - THE GLASS WEIGHT AND THE NON-D1 GAMES (box seasons 2021-26; train 2021-23 / held 2024-26)")
    reb = {}

    def margins(t, g):
        s = nr.season_of(g["start"])
        if s not in reb:
            reb[s] = nr.team_rebounds(s)
        rows = [(st, gid, m) for st, gid, m in (reb[s].get(str(t)) or []) if st < g["start"]]
        d1rows = [m for st, gid, m in rows if gid in byid and opp_of(byid[gid], t) in D1]
        return [m for _, _, m in rows], d1rows

    for g in fin:
        if not priced(g) or g["season"] < 2021:
            continue
        ma, mad = margins(g["home"], g)
        mb, mbd = margins(g["away"], g)
        if len(ma) < nr.REB_MIN_GAMES or len(mb) < nr.REB_MIN_GAMES:
            continue
        gh = sum(ma) / len(ma) - sum(mb) / len(mb)
        ghd = (sum(mad) / len(mad) - sum(mbd) / len(mbd)) if (len(mad) >= 3 and len(mbd) >= 3) else None
        early = g["start"][5:7] in ("11", "12")
        for side, gap, gapd, mine, mined in (("home", gh, ghd, ma, mad), ("away", -gh, None if ghd is None else -ghd, mb, mbd)):
            o, pr = ml(g, side)
            a = lib.ats(g, side) if not g["neutral"] or True else None
            pad = len(mine) - len(mined)                      # non-D1 box games inside this side's margin
            dog = o is not None and 100 <= o <= 350
            tags = ["all"] + (["Nov-Dec"] if early else ["Jan-Mar"])
            for tg in tags:
                if dog:
                    O.add(f"dog base | {tg}", g["season"], pr, o)
                O.add(f"ats base | {tg}", g["season"], a)
                if gap >= 6:
                    if dog:
                        O.add(f"dog glass 6+ (as built) | {tg}", g["season"], pr, o)
                        O.add(f"dog glass 6+ pad {'0' if pad == 0 else '1' if pad == 1 else '2+'} non-D1 games | {tg}", g["season"], pr, o)
                        if gapd is not None:
                            O.add(f"dog glass 6+ D1-only {'still 6+' if gapd >= 6 else 'under 6'} | {tg}", g["season"], pr, o)
                        else:
                            O.add(f"dog glass 6+ D1-only unknown (<3 D1 box games) | {tg}", g["season"], pr, o)
                    O.add(f"ats glass 6+ (as built) | {tg}", g["season"], a)
                    O.add(f"ats glass 6+ pad {'0' if pad == 0 else '1+'} | {tg}", g["season"], a)
                    if gapd is not None:
                        O.add(f"ats glass 6+ D1-only {'still 6+' if gapd >= 6 else 'under 6'} | {tg}", g["season"], a)
                if gap >= 8 and dog:
                    O.add(f"dog glass 8+ | {tg}", g["season"], pr, o)
                    O.add(f"dog glass 8+ pad {'0' if pad == 0 else '1+'} | {tg}", g["season"], pr, o)
                if gapd is not None and gapd >= 6 and gap < 6:
                    if dog:
                        O.add(f"dog D1-only 6+ the built read misses | {tg}", g["season"], pr, o)
                    O.add(f"ats D1-only 6+ the built read misses | {tg}", g["season"], a)
                if gap <= -6:
                    O.add(f"ats trails by 6+ (as built) | {tg}", g["season"], a)
                    if gapd is not None:
                        O.add(f"ats trails by 6+ D1-only {'still' if gapd <= -6 else 'not'} | {tg}", g["season"], a)
    O.show()
    for nm, pool in (("dog glass 6+ pad 1 non-D1 games | all", "dog glass 6+ (as built) | all"),
                     ("dog glass 6+ pad 2+ non-D1 games | all", "dog glass 6+ (as built) | all"),
                     ("dog glass 6+ D1-only under 6 | all", "dog glass 6+ (as built) | all"),
                     ("dog glass 6+ D1-only still 6+ | all", "dog base | all"),
                     ("dog glass 6+ (as built) | all", "dog base | all"),
                     ("ats glass 6+ D1-only under 6 | all", "ats glass 6+ (as built) | all"),
                     ("ats glass 6+ D1-only still 6+ | all", "ats base | all")):
        O.placebo(nm, pool, fade="under 6" in nm or "pad" in nm)
    O.save()


# ------------------------------------------------------------------ the 11/16 replay rows (S2 / S3)
def rows():
    R = pickle.load(open(os.path.expanduser("~/.cache/d503_maxcol1116/cbb_rows.pkl"), "rb"))
    return R


def side_team(r):
    g = byid.get(r["gid"])
    if not g:
        return None, None, None
    t = g["home"] if r["side"] == "home" else g["away"]
    return g, t, opp_of(g, t)


def d1_counts(t, g):
    ps = prior(t, g)
    n1 = sum(1 for x in ps if opp_of(x, t) in D1)
    return n1, len(ps) - n1, (ps[-1] if ps else None)


def s2(R):
    O = h.Out("s2_slot_d1_games", (2018, 2022), [2023, 2024, 2025, 2026])
    O.p("S2 - THE DOG SLOT'S '4+ GAMES' GATE COUNTED IN D1 GAMES (the 11/16 replay rows; the slot as live: read 4+ with the")
    O.p("     11/14 home-dog -1, both teams 4+ games, the read clears the price, best two a night; train 2018-22 / held 2023-26)")

    def live_read(r):
        x = r["dog_read"]
        if r.get("where") == "home" and not (r.get("dog_read_parts") or {}).get("home"):
            if not ((r.get("effgap") or 0) >= 0.15):
                x -= 1
        return x
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in R:
        if r.get("market", "ml") != "ml" or not 100 <= r["odds"] <= 350 or r.get("dog_read") is None or r["mn"] < 4:
            continue
        lr = live_read(r)
        if lr < 4 or min(0.95, r["p_market"] + lr / 100) * r["dec"] - 1 <= 0:
            continue
        if r["gid"] in lockg or r["kind"] in ("stackplay", "floor"):
            continue
        r = dict(r, lr=lr)
        pool[r["date"]].append(r)
    slot = []
    for d, v in pool.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["lr"], -(r.get("effgap") or 0))):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                if len(seen) <= 2:
                    slot.append(r)
    for r in slot:
        g, t, o = side_team(r)
        if not g:
            continue
        a1, a0, _ = d1_counts(t, g)
        b1, b0, _ = d1_counts(o, g)
        s, p, od = r["season"], r["pnl"], r["odds"]
        O.add("slot (all)", s, p, od)
        O.add("slot | both 4+ D1 games" if min(a1, b1) >= 4 else "slot | a team under 4 D1 games (4+ only with tune-ups)", s, p, od)
        O.add(f"slot | the dog's non-D1 games so far: {'0' if a0 == 0 else '1' if a0 == 1 else '2+'}", s, p, od)
        O.add(f"slot | the favorite's non-D1 games so far: {'0' if b0 == 0 else '1' if b0 == 1 else '2+'}", s, p, od)
        if r["date"][5:7] in ("11", "12"):
            O.add("slot Nov-Dec (all)", s, p, od)
            O.add("slot Nov-Dec | both 4+ D1 games" if min(a1, b1) >= 4 else "slot Nov-Dec | a team under 4 D1 games", s, p, od)
            O.add(f"slot Nov-Dec | dog's non-D1 share of its games {'0' if a0 == 0 else 'under a third' if a0 / (a0 + a1) < 1 / 3 else 'a third+'}", s, p, od)
            if (a1 + a0) <= 6:
                O.add("slot Nov-Dec | the dog 4-6 games in", s, p, od)
                O.add(f"slot Nov-Dec | the dog 4-6 games in, {'2+ of them non-D1' if a0 >= 2 else 'under 2 non-D1'}", s, p, od)
    O.show()
    O.placebo("slot | a team under 4 D1 games (4+ only with tune-ups)", "slot (all)", fade=True)
    O.placebo("slot Nov-Dec | the dog 4-6 games in, 2+ of them non-D1", "slot Nov-Dec (all)", fade=True)
    O.placebo("slot | the dog's non-D1 games so far: 2+", "slot (all)", fade=True)
    O.save()


def s3(R):
    O = h.Out("s3_stack_tuneup", (2018, 2022), [2023, 2024, 2025, 2026])
    O.p("S3 - THE 1/2u SPREAD STACK PLAY WITH THE 11/20 TUNE-UP WEIGHT ADDED (the 11/16 replay rows' spread sides and their")
    O.p("     stack; +0.02 off a non-D1 tune-up against a team off a D1 game on a true home / road floor, -0.02 across)")
    E = 1e-9
    byday = defaultdict(list)
    for r in R:
        if r.get("market") != "spread" or r.get("stack") is None or r.get("pnl") is None:
            continue
        g, t, o = side_team(r)
        if not g or t not in D1 or o not in D1:
            continue
        _, _, lt = d1_counts(t, g)
        _, _, lo = d1_counts(o, g)
        tu = 0
        if lt and lo and not g["neutral"]:
            mine_t = opp_of(lt, t) not in D1
            opp_t = opp_of(lo, o) not in D1
            tu = 1 if (mine_t and not opp_t) else -1 if (opp_t and not mine_t) else 0
        s, p, st = r["season"], r["pnl"], r["stack"]
        new = st + 0.02 * tu
        r2 = dict(r, tu=tu, new=new)
        byday[r["date"]].append(r2)
        O.add("every spread side", s, p)
        if tu == 1:
            O.add("off a tune-up vs a team off a D1 game (the 11/20 weight's side)", s, p)
        if tu == -1:
            O.add("across it", s, p)
        if st >= 0.05 - E:
            O.add("stack +0.05+ (today's play pool)", s, p)
            O.add(f"stack +0.05+ | tune-up {'for' if tu == 1 else 'against' if tu == -1 else 'none'}", s, p)
            if tu == -1 and st < 0.07 - E:
                O.add("DROPPED by the weight (stack +0.05..+0.06, across a tune-up team)", s, p)
        if 0.03 - E <= st < 0.05 - E:
            O.add("stack +0.03..+0.04", s, p)
            O.add(f"stack +0.03..+0.04 | tune-up {'for (ADDED by the weight)' if tu == 1 else 'against' if tu == -1 else 'none'}", s, p)
        if 0.01 - E <= st < 0.03 - E and tu == 1:
            O.add("stack +0.01..+0.02 + tune-up (still under the bar)", s, p)
        if new >= 0.05 - E:
            O.add("NEW pool: stack with the tune-up weight +0.05+", s, p)
        if r.get("kind") == "stackplay":
            O.add("the replay's posted stack plays", s, p)
            O.add(f"the replay's posted stack plays | tune-up {'for' if tu == 1 else 'against' if tu == -1 else 'none'}", s, p)
    for cap in (3,):                                           # the play as posted: the biggest stack first, 3 a night
        for name, key in (("OLD", "stack"), ("NEW", "new")):
            for d, v in byday.items():
                seen = set()
                for r in sorted((x for x in v if x[key] >= 0.05 - E), key=lambda x: -x[key]):
                    if r["gid"] in seen:
                        continue
                    seen.add(r["gid"])
                    if len(seen) > cap:
                        break
                    O.add(f"top {cap} a night by the {name} stack", r["season"], r["pnl"])
    O.show()
    O.placebo("stack +0.03..+0.04 | tune-up for (ADDED by the weight)", "stack +0.03..+0.04")
    O.placebo("DROPPED by the weight (stack +0.05..+0.06, across a tune-up team)", "stack +0.05+ (today's play pool)", fade=True)
    O.placebo("stack +0.05+ | tune-up for", "stack +0.05+ (today's play pool)")
    O.save()


def s4():
    O = h.Out("s4_no_d1_win", TRAIN, HELD)
    O.p("S4 - THE FAVORITE WITH NO DIVISION I WIN (Nov-Dec, D1 vs D1, 2+ wins all over non-D1 schools and 1+ D1 loss)")
    for g in fin:
        if not priced(g) or g["start"][5:7] not in ("11", "12"):
            continue
        st = {}
        for side, t in (("home", g["home"]), ("away", g["away"])):
            ps = prior(t, g)
            w1 = sum(1 for x in ps if lib.won_g(x, t) and opp_of(x, t) in D1)
            w0 = sum(1 for x in ps if lib.won_g(x, t) and opp_of(x, t) not in D1)
            l1 = sum(1 for x in ps if not lib.won_g(x, t) and opp_of(x, t) in D1)
            st[side] = (w1, w0, l1)
        for side, other in (("home", "away"), ("away", "home")):
            w1, w0, l1 = st[side]
            o, pr = ml(g, side)
            oo, opr = ml(g, other)
            if o is None or oo is None:
                continue
            padded = w1 == 0 and w0 >= 2 and l1 >= 1
            ow1 = st[other][0]
            s = g["season"]
            if 100 <= oo <= 350:
                O.add("dog base (Nov-Dec)", s, opr, oo)
            O.add("ats base (Nov-Dec)", s, lib.ats(g, side))
            if not padded:
                continue
            if o < 0:
                O.add("padded favorite: its own spread", s, lib.ats(g, side))
                O.add("padded favorite: the spread across", s, lib.ats(g, other))
                if 100 <= oo <= 350:
                    O.add("padded favorite: the dog across +100..+350", s, opr, oo)
                    O.add(f"padded favorite: the dog across | the dog has {'a D1 win' if ow1 >= 1 else 'no D1 win either'}", s, opr, oo)
                    O.add(f"padded favorite: the dog across | {'neutral' if g['neutral'] else 'fav at home' if side == 'home' else 'fav on the road'}", s, opr, oo)
                if -150 <= o <= -101:
                    O.add("padded small favorite -150..-101", s, pr, o)
            elif 100 <= o <= 350:
                O.add("padded DOG +100..+350", s, pr, o)
                O.add("padded dog: its spread", s, lib.ats(g, side))
    O.show()
    O.placebo("padded favorite: the dog across +100..+350", "dog base (Nov-Dec)")
    O.placebo("padded favorite: the spread across", "ats base (Nov-Dec)")
    O.placebo("padded DOG +100..+350", "dog base (Nov-Dec)", fade=True)
    O.save()


if __name__ == "__main__":
    which = sys.argv[1:] or ["s1", "s2", "s3", "s4"]
    if "s1" in which:
        s1()
    if "s4" in which:
        s4()
    if "s2" in which or "s3" in which:
        R = rows()
        if "s2" in which:
            s2(R)
        if "s3" in which:
            s3(R)
