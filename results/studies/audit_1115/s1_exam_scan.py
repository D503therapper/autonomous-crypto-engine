"""11/15 FABLE FULL ENGINE AUDIT - S1: the early EXAM SCAN play (sports_early.scan - the plays with no "spot"), walked
forward. The live scan: the engine retrained on the last 3 seasons (sports_early.recent_params), every dog +100..+280
whose OWN read beats the no-vig price by a band the twice-a-season exam passed (today: college football +4..8 only),
at the price now AND at the open; sized by sports.kelly_units on that raw own read.
Here: for every season Y 2018..2026 the tune learns on the 3 seasons before Y only, then every college football (and,
for the placebo, every league's) dog of season Y in the +4..8 band at the EARLY price (bettable - the open hadn't run 15+
cents) is graded at that price: flat, by the Kelly size the scan would stamp, home / road, FBS-vs-FBS, and against the
honest read (the no-vig price itself - what the 11/12 deep program says the close is).
Run from the repo root:  python results/studies/audit_1115/s1_exam_scan.py [league]   (cache ~/.cache/d503_audit1115)"""
import json, os, pickle, random, sys
sys.path.insert(0, os.getcwd())
import sports as S
import sports_data as sd
import sports_early as se
import sports_model as sm

CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_audit1115")
os.makedirs(CACHE, exist_ok=True)
LG = sys.argv[1] if len(sys.argv) > 1 else "ncaaf"
BAND = (0.04, 0.08, 100, 280)


def season(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 7 else y - 1


def rows(lg):
    path = os.path.join(CACHE, f"s1_{lg}.pkl")
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    games = sd.load_games(lg)
    fin = sm.finals(games, lg)
    try:
        import sports_players as sp
        sm.KEY_EDGE = sp.key_edges(games, sp.load())
    except Exception as e:  # noqa: BLE001
        print("no starters", str(e)[:60])
        sp = None
    out = []
    for y in range(2018, 2027):
        learn = {k: g for k, g in games.items() if f"{y - 3}-07-01" <= g.get("start", "") < f"{y}-07-01"}
        p = sm.tune(learn, lg)
        if not p or "w" not in p:
            print(y, "no tune", flush=True)
            continue
        _, played = sm.replay(fin, p["k"], p["hfa"], lg)
        n = 0
        for g, f, *_ in played:
            if season(g["start"]) != y or (g.get("stype") or "?") not in sd.REAL:
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError, TypeError):
                continue
            oh, oa, ch, ca = (se._int(g.get(k)) for k in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
            if hs == as_ or None in (ch, ca) or 0 in (ch, ca):
                continue
            if f.get("known", 0) < 3:
                continue
            real_open = None not in (oh, oa) and 0 not in (oh, oa) and (oh, oa) != (ch, ca)
            own = sm.own_p(p, f)
            fbs = None
            if lg == "ncaaf" and sp is not None:
                try:
                    s_ = sp.fbs_set(games, g["start"])
                    fbs = None if s_ is None else (g["home"] in s_ and g["away"] in s_)
                except Exception:  # noqa: BLE001
                    fbs = None
            for price, (a, b) in (("early", (oh, oa)), ("close", (ch, ca))):
                if price == "early" and not real_open:
                    continue
                pa, pb = 1 / se._dec(a), 1 / se._dec(b)
                mk = pa / (pa + pb)
                for side, o, won, ow, m, c in (("home", a, hs > as_, own, mk, ch), ("away", b, as_ > hs, 1 - own, 1 - mk, ca)):
                    if not 100 <= o <= 280:
                        continue
                    if price == "early" and not se.bettable(o, c):
                        continue
                    out.append({"y": y, "price": price, "side": side, "neutral": str(g.get("neutral")) == "1", "odds": o,
                                "close": c, "won": bool(won), "own": ow, "mkt": m, "gap": ow - m, "fbs": fbs,
                                "start": g["start"], "id": g["id"], "ku": S.kelly_units(ow, o)})
                    n += 1
        print(y, "rows", n, "k", p["k"], "hfa", p["hfa"], flush=True)
    pickle.dump(out, open(path, "wb"))
    return out


def cell(name, rs, units=None):
    if not rs:
        print(f"  {name:<58} n=0")
        return
    w = sum(r["won"] for r in rs)
    u = [units(r) if units else 1.0 for r in rs]
    pr = sum(ui * ((se._dec(r["odds"]) - 1) if r["won"] else -1) for ui, r in zip(u, rs))
    need = sum(r["mkt"] for r in rs) / len(rs)
    half = lambda a: (lambda x: f"{sum((se._dec(r['odds']) - 1) if r['won'] else -1 for r in x) / len(x) * 100:+.1f}% on {len(x)}" if x else "-")(a)
    tr, he = [r for r in rs if r["y"] <= 2022], [r for r in rs if r["y"] >= 2023]
    ys = sorted({r["y"] for r in rs})
    up = sum(1 for y in ys if sum((se._dec(r["odds"]) - 1) if r["won"] else -1 for r in rs if r["y"] == y) > 0)
    print(f"  {name:<58} {w}-{len(rs) - w}  won {w / len(rs) * 100:.1f}% (priced {need * 100:.1f}%)  "
          f"ROI {pr / sum(u) * 100:+.1f}% ({pr:+.1f}u on {sum(u):.1f}u)  train {half(tr)} / held {half(he)}  seasons up {up}/{len(ys)}")


def main():
    rs = rows(LG)
    for price in ("early", "close"):
        A = [r for r in rs if r["price"] == price]
        print(f"\n=== {LG} dogs +100..+280 at the {price} price, walk-forward 2018-26 ({len(A)} dog sides) ===")
        cell("every dog", A)
        for lo, hi in ((-1, 0), (0, 0.04), (0.04, 0.08), (0.08, 0.12), (0.12, 1)):
            cell(f"own read {lo * 100:+.0f}..{hi * 100:+.0f} over the no-vig price", [r for r in A if lo <= r["gap"] < hi])
        B = [r for r in A if BAND[0] <= r["gap"] < BAND[1]]
        print(f" -- the band the scan posts (+4..8), {len(B)} --")
        cell("flat 1u", B)
        cell("sized like the scan (quarter-Kelly on the raw own read)", B, lambda r: r["ku"])
        for u in (0.5, 1.0, 1.5, 2.0, 2.5):
            cell(f"  the Kelly size {u}u (flat ROI)", [r for r in B if r["ku"] == u])
        cell("  Kelly size 1.5u+ (flat)", [r for r in B if r["ku"] >= 1.5])
        cell("  Kelly size under 1.5u (flat)", [r for r in B if r["ku"] < 1.5])
        cell("HOME dog (true home)", [r for r in B if r["side"] == "home" and not r["neutral"]])
        cell("ROAD dog (true road)", [r for r in B if r["side"] == "away" and not r["neutral"]])
        cell("neutral site", [r for r in B if r["neutral"]])
        if LG == "ncaaf":
            cell("FBS vs FBS", [r for r in B if r["fbs"]])
            cell("FBS vs FBS, HOME dog", [r for r in B if r["fbs"] and r["side"] == "home" and not r["neutral"]])
            cell("FBS vs FBS, ROAD dog", [r for r in B if r["fbs"] and r["side"] == "away" and not r["neutral"]])
        for lo, hi in ((100, 149), (150, 199), (200, 280)):
            cell(f"price +{lo}..+{hi}", [r for r in B if lo <= r["odds"] <= hi])
        for y in sorted({r["y"] for r in B}):
            cell(f"  season {y}", [r for r in B if r["y"] == y])
        # placebo: a random set of the same size from every dog at this price, the same home / road mix
        random.seed(1115)
        base = sum((se._dec(r["odds"]) - 1) if r["won"] else -1 for r in B) / max(1, len(B))
        hit = 0
        for _ in range(2000):
            smp = random.sample(A, len(B)) if len(A) >= len(B) else A
            if sum((se._dec(r["odds"]) - 1) if r["won"] else -1 for r in smp) / max(1, len(smp)) >= base:
                hit += 1
        print(f"  placebo: a random {len(B)} dogs at this price does as well {hit} times in 2,000")


if __name__ == "__main__":
    main()
