"""11/4 FABLE - PLAYS EVERY DAY: the board re-built from the 10/30 funnel rows (results/studies/thin_1029/funnel_replay.py
on the 10/30 code: 1,097 board days 2023-10-01 -> 2026-10-12 + the live stretch 10/13-10/29, closing prices, params
re-tuned each July, no injury reports) under TODAY's sizing (the 10/30 SIZING: Lock 2u / 1u at a 7+ gap / football 1u /
backup ½u, no thin Lock; the Dog 2u to +150 / ½u past, NBA 1u own-over / ½u, no college hoops Dog; plays ½u; runner-up
dog ½u; NBA favorite 1u; floor / NBA floor ½u) and the volume variants:
  (a) the floor OFF (today, from the 11/5 board)
  (b) the floor v2 ON (FLOOR_MIN 2, fallback 1, thin only, NBA / college football out of the general floor + the NBA floor)
  (c) the honest middle grounds - see VARIANTS.
Train 2023-25 (to 2025-06-30), held out 2025-27 (2025-07-01 on, the 10/29 split); the live stretch reported apart.
Usage: python sim_volume.py"""
import glob
import json
from collections import defaultdict

D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030"
HELD_FROM = "2025-07-01"
LIVE_FROM = "2026-10-13"
FOOTBALL = ("nfl", "ncaaf")

rows = []
for q in sorted(glob.glob(D + "/f[A-D].jsonl")) + [D + "/fLive.jsonl"]:
    with open(q) as f:
        rows += [json.loads(l) for l in f if l.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost", "push")]
by_day = defaultdict(list)
for r in rows:
    by_day[r["date"]].append(r)
days = sorted(by_day)
UNIT_KINDS = ("lock", "dog", "solo", "play", "dogplay", "nbafav")
GAMES = lambda r: frozenset((r["team"], r["opp"]))     # noqa: E731


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def half(d):
    return "live" if d >= LIVE_FROM else "held" if d >= HELD_FROM else "train"


def pnl(r, u):
    return u * (r["dec"] - 1) if r["result"] == "won" else -u if r["result"] == "lost" else 0.0


def own_p(r):
    return None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]


def gap(r):
    o = own_p(r)
    return None if o is None or r.get("p_market") is None else 100 * (o - r["p_market"])


def clean(r):
    n = r.get("n_reasons2")
    if n is None:
        n = r["n_reasons"]
    return n > 0 and not r["trap"] and not r["fighting"] and not r.get("waiting")


def floor_ok(r):
    return 100 <= r["odds"] <= 350 and clean(r) and r.get("dog_score") is not None


def play_bar(r):
    return r["good"] and r["tier"] in ("lock", "value") and -150 <= r["odds"] < 100 and not r["fighting"] \
        and not r["trap"] and r["real_value"] and r["own_beats"]


def floor_v2(r):
    return r["league"] not in ("nba", "ncaaf") and bool(r.get("thin"))


# ---------------------------------------------------------------- today's sizing (10/30 SIZING, live from 10/31)
def size_today(k, r, u):
    if k == "lock":
        if u == 0.5:
            return 0.5                                       # the backup Lock
        if r["league"] in FOOTBALL:
            return 1.0
        g = gap(r)
        return 2.0 if g is not None and g < 7 else 1.0
    if k == "dog":
        if r["league"] == "ncaab":
            return 0.0                                       # no college hoops Dog
        if r["league"] == "nba":
            return 1.0 if (r.get("edge_own") or 0) > 0 else 0.5
        return 2.0 if r["odds"] <= 150 else 0.5
    if k == "nbafav":
        return 1.0
    if k == "solo":
        return u or 0.5
    return 0.5                                               # play / dogplay / floor / nbafloor / floorfb / hkfloor


def hockey_dog_ok(r, sc_min=3.0, gap_min=2.0):
    """best_hockey_dog's rule on a row: +100..+350, clean, dog_own_ok, score over sc_min, own gap gap_min+, 1%+ value."""
    if r["league"] != "nhl" or not 100 <= r["odds"] <= 350 or r["trap"] or r["fighting"] or r.get("waiting"):
        return False
    if not r["dog_own_ok"] or r.get("dog_score") is None:
        return False
    g = gap(r)
    if g is not None and g < gap_min:
        return False
    dp = min(0.95, (r["p_market"] if r.get("p_market") is not None else 1 / r["dec"]) + r["dog_score"] / 100)
    return r["dog_score"] > sc_min and dp * r["dec"] - 1 >= 0.01


def build(d, floor_on=True, floor_min=2, fallback_min=1, nba_floor=True, floor_leagues=None, hk_floor=None,
          hk_fallback_gap=None, floor_score_min=None, hk_floor_score=0.0, hk_floor_units=0.5, floor_units=0.5, hk_named=False):
    """One board day's unit plays: [(row, units, kind)].
    floor_on / floor_min / fallback_min / nba_floor: the 10/29 floor v2 as wired; floor_leagues restricts the general
    floor; hk_floor: a hockey floor (the best clean hockey dog by score, score hk_floor_score+, one a night with no
    hockey unit play) like the NBA floor; hk_fallback_gap: the hockey fallback Dog's own-gap rule loosened (replaces the
    rows' own Dog pick when the day's Dog was none); floor_score_min: the general floor's dog score bar."""
    out, taken = [], set()
    had_dog = False
    for r in by_day[d]:
        k = r["kind"]
        if k not in UNIT_KINDS:
            continue
        u = r.get("units") or 0
        if k == "lock" and r.get("thin"):
            if play_bar(r):
                k, u = "play", 0.5
            else:
                continue
        if k == "lock" and u == 0.5:
            k = "backup"
        if not u:
            continue
        nu = size_today("lock" if k == "backup" else k, r, u)
        if not nu:
            continue
        if k == "dog":
            had_dog = True
        out.append((r, nu, k))
        taken.add(GAMES(r))
    if hk_named and not had_dog:                            # the hockey named-reason fix: a GATED hockey dog with no
        pool = [r for r in by_day[d] if r["league"] == "nhl" and r.get("dog_gate") and r["n_reasons"] == 0   # model-factor
                and not r["trap"] and not r["fighting"] and not r.get("waiting") and r["dog_own_ok"]          # reason is the
                and 100 <= r["odds"] <= 350 and GAMES(r) not in taken]                                       # Dog (score_reason
        if pool:                                                                                             # names the score)
            b = max(pool, key=lambda r: (r["dog_score"], r["edge"]))
            out.append((b, size_today("dog", b, 1), "dog"))
            taken.add(GAMES(b))
            had_dog = True
    elif hk_named and had_dog and not any(k == "dogplay" for _, _, k in out):
        pool = [r for r in by_day[d] if r["league"] == "nhl" and r.get("dog_gate") and r["n_reasons"] == 0
                and not r["trap"] and not r["fighting"] and not r.get("waiting") and r["dog_own_ok"]
                and 100 <= r["odds"] <= 350 and GAMES(r) not in taken]
        if pool:
            b = max(pool, key=lambda r: (r["dog_score"], r["edge"]))
            out.append((b, 0.5, "dogplay"))
            taken.add(GAMES(b))
    if hk_fallback_gap is not None and not had_dog:          # the loosened hockey fallback Dog (score 3+, gap hk_fallback_gap+)
        pool = [r for r in by_day[d] if hockey_dog_ok(r, 3.0, hk_fallback_gap) and GAMES(r) not in taken]
        if pool:
            b = max(pool, key=lambda r: (r["dog_score"], r["edge"]))
            out.append((b, size_today("dog", b, 1), "dog"))
            taken.add(GAMES(b))
    have = len(out)
    if floor_on and nba_floor and any(r["league"] == "nba" for r in by_day[d]) and not any(r["league"] == "nba" for r, _, _ in out):
        pool = [r for r in by_day[d] if r["league"] == "nba" and floor_ok(r) and r["dog_score"] >= 0 and GAMES(r) not in taken]
        pool.sort(key=lambda r: (-r["dog_score"], -r["edge"]))
        if pool:
            out.append((pool[0], 0.5, "nbafloor"))
            taken.add(GAMES(pool[0]))
            have += 1
    if hk_floor and any(r["league"] == "nhl" for r in by_day[d]) and not any(r["league"] == "nhl" for r, _, _ in out):
        pool = [r for r in by_day[d] if r["league"] == "nhl" and floor_ok(r) and r["dog_own_ok"] and r["dog_score"] >= hk_floor_score
                and GAMES(r) not in taken and (hk_floor == "any" or (hk_floor == "short" and r["odds"] <= 150) or (hk_floor == "thin" and r.get("thin")))]
        pool.sort(key=lambda r: (-r["dog_score"], -r["edge"]))
        if pool:
            out.append((pool[0], hk_floor_units, "hkfloor"))
            taken.add(GAMES(pool[0]))
            have += 1
    if floor_on and have < floor_min:
        pool = sorted([r for r in by_day[d] if floor_ok(r) and GAMES(r) not in taken
                       and (floor_leagues is None or r["league"] in floor_leagues)
                       and (floor_score_min is None or r["dog_score"] >= floor_score_min)],
                      key=lambda r: (-r["dog_score"], -r["edge"]))
        for r in [r for r in pool if floor_v2(r)]:
            if have >= floor_min:
                break
            if GAMES(r) in taken:
                continue
            taken.add(GAMES(r))
            out.append((r, floor_units, "floor"))
            have += 1
        if have < fallback_min:
            for r in pool:
                if have >= fallback_min:
                    break
                if GAMES(r) in taken:
                    continue
                taken.add(GAMES(r))
                out.append((r, floor_units, "floorfb"))
                have += 1
    return out


def run(name, **kw):
    plays = [(d, r, u, k) for d in days for r, u, k in build(d, **kw)]
    per_day = defaultdict(float)
    stats = defaultdict(lambda: [0, 0, 0.0, 0.0, 0])          # half -> W, L, net, risk, plays
    seas = defaultdict(float)
    kinds = defaultdict(lambda: [0, 0, 0.0, 0.0])
    lg = defaultdict(lambda: [0, 0, 0.0, 0.0])
    fl = defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0, 0.0])   # the floor by league: W, L, net, risk, train net, held net
    days_with = defaultdict(set)
    for d, r, u, k in plays:
        p = pnl(r, u)
        h = half(d)
        s = stats[h]
        s[0] += r["result"] == "won"
        s[1] += r["result"] == "lost"
        s[2] += p
        s[3] += u
        s[4] += 1
        days_with[h].add(d)
        if h != "live":
            per_day[d] += p
            seas[season(d)] += p
            kk = kinds[k]
            kk[0] += r["result"] == "won"
            kk[1] += r["result"] == "lost"
            kk[2] += p
            kk[3] += u
            if k in ("floor", "floorfb", "hkfloor", "nbafloor"):
                ff = fl[(k, r["league"])]
                ff[0] += r["result"] == "won"
                ff[1] += r["result"] == "lost"
                ff[2] += p
                ff[3] += u
                ff[4 if h == "train" else 5] += p
            ll = lg[r["league"]]
            ll[0] += r["result"] == "won"
            ll[1] += r["result"] == "lost"
            ll[2] += p
            ll[3] += u
    n_days = {h: sum(1 for d in days if half(d) == h) for h in ("train", "held", "live")}

    def worst(ds):
        cum = peak = w = 0.0
        for d in ds:
            cum += per_day.get(d, 0.0)
            peak = max(peak, cum)
            w = min(w, cum - peak)
        return w
    print(f"\n{name}")
    for h in ("train", "held", "live"):
        W, L, net, risk, n = stats[h]
        ds = [d for d in days if half(d) == h]
        print(f"   {h:6} {n / max(1, n_days[h]):.2f}/day  {W}-{L}  {net:+7.1f}u on {risk:6.0f}u  ROI {100 * net / risk if risk else 0:+5.1f}%  "
              f"worst {worst(ds):+6.1f}u  >=1 play {100 * len(days_with[h]) / max(1, n_days[h]):5.1f}% of days")
    W = stats["train"][0] + stats["held"][0]
    L = stats["train"][1] + stats["held"][1]
    net = stats["train"][2] + stats["held"][2]
    risk = stats["train"][3] + stats["held"][3]
    n = stats["train"][4] + stats["held"][4]
    nd = n_days["train"] + n_days["held"]
    al = [d for d in days if half(d) != "live"]
    up = sum(v > 0 for v in seas.values())
    print(f"   ALL    {n / nd:.2f}/day  {W}-{L}  {net:+7.1f}u on {risk:6.0f}u  ROI {100 * net / risk if risk else 0:+5.1f}%  "
          f"worst {worst(al):+6.1f}u  >=1 play {100 * len(days_with['train'] | days_with['held']) / nd:5.1f}% of days  seasons up {up}/{len(seas)} "
          + " ".join(f"{k}:{v:+.1f}" for k, v in sorted(seas.items())))
    for k, (w, l, p, u) in sorted(kinds.items(), key=lambda kv: -kv[1][3]):
        print(f"      {k:9} {w}-{l} {p:+7.1f}u on {u:5.0f}u ROI {100 * p / u if u else 0:+5.1f}%")
    for (k, l), (w, l_, p, u, tn, hn) in sorted(fl.items()):
        print(f"         {k:8} {l:5} {w}-{l_} {p:+6.1f}u on {u:4.0f}u ROI {100 * p / u if u else 0:+5.1f}%  train {tn:+6.1f}u held {hn:+6.1f}u")
    print("      by sport: " + "  ".join(f"{k} {w}-{l} {p:+.1f}u/{u:.0f}u {100 * p / u if u else 0:+.1f}%" for k, (w, l, p, u) in sorted(lg.items())))
    return plays


if __name__ == "__main__":
    print(f"{len(rows)} graded rows, {len(days)} board days ({sum(1 for d in days if half(d) == 'train')} train / "
          f"{sum(1 for d in days if half(d) == 'held')} held / {sum(1 for d in days if half(d) == 'live')} live)")
    run("(a) TODAY from 11/5: the floor OFF, the NBA floor OFF", floor_on=False, nba_floor=False)
    run("(b) the 10/29 floor v2 ON (FLOOR_MIN 2, fallback 1, thin only, no NBA / college football) + the NBA floor", floor_on=True)
    run("(c1) (b) with college hoops out of the general floor too", floor_on=True, floor_leagues=("nhl", "mlb", "nfl"))
    run("(c2) (b) + a HOCKEY floor: the best clean hockey dog (score 0+, own read not under the market) every hockey night with no hockey unit play, ½u",
        floor_on=True, hk_floor="any")
    run("(c3) (c1) + the hockey floor (short dogs +100..+150 only)", floor_on=True, floor_leagues=("nhl", "mlb", "nfl"), hk_floor="short")
    run("(c4) (c1) + the hockey floor at score 3+", floor_on=True, floor_leagues=("nhl", "mlb", "nfl"), hk_floor="any", hk_floor_score=3.0)
    run("(c5) (a) + the hockey fallback Dog loosened to own gap 0+ (score 3+), sized like the Dog (2u short / ½u long)", floor_on=False, nba_floor=False, hk_fallback_gap=0.0)
    run("(c6) (a) + the NBA floor only", floor_on=True, floor_min=0, fallback_min=0, nba_floor=True)
    run("(c7) (a) + the NBA floor + the hockey floor (score 0+), no general floor", floor_on=True, floor_min=0, fallback_min=0, nba_floor=True, hk_floor="any")
    run("(c8) (c7) + the general floor to 1 (fallback 0) in hockey / baseball / NFL", floor_on=True, floor_min=1, fallback_min=0, nba_floor=True, hk_floor="any", floor_leagues=("nhl", "mlb", "nfl"))
    run("(c9) (c1) + hockey floor (score 0+) + the hockey fallback Dog at gap 0+", floor_on=True, floor_leagues=("nhl", "mlb", "nfl"), hk_floor="any", hk_fallback_gap=0.0)
    run("(c10) (b) with the fallback floor (floorfb) OFF", floor_on=True, fallback_min=0)
    run("(c13) (a) + THE HOCKEY NAMED-REASON FIX (a gated hockey dog's score is its reason - the Dog / runner-up)", floor_on=False, nba_floor=False, hk_named=True)
    run("(c14) (b) + THE HOCKEY NAMED-REASON FIX", floor_on=True, hk_named=True)
    run("(c15) (c14) with college hoops out of the general floor", floor_on=True, hk_named=True, floor_leagues=("nhl", "mlb", "nfl"))
    run("(c16) (c14) with the floor to 1 (fallback 1)", floor_on=True, hk_named=True, floor_min=1)
    run("(c11) (c1) with the general floor at dog score 0+", floor_on=True, floor_leagues=("nhl", "mlb", "nfl"), floor_score_min=0.0)
    run("(c12) (c4) with the fallback floor OFF", floor_on=True, floor_leagues=("nhl", "mlb", "nfl"), hk_floor="any", hk_floor_score=3.0, fallback_min=0)
