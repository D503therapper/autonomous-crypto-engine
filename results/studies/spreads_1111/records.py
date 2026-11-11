"""One record per game for the grading studies: the model's number (QB read A = who started, P = last game's QB), the
closing spread, the first FAIR spread look of the paid history with every book's number and price.
   records('nfl' | 'ncaaf') -> [{id, season, wkn, margin (home), close (home spread), pA, pP (model home margin),
                                 look ({book: (home pts, home price, away pts, away price)} or None), days, qbchg, ...}]"""
import os, pickle, statistics
import splib as S

B = S.B
SHARP = ("circasports", "lowvig", "betonlineag", "bookmaker", "pinnacle")
SOFT = ("draftkings", "fanduel", "betmgm", "williamhill_us", "betrivers", "pointsbetus", "caesars", "fanatics",
        "barstool", "wynnbet", "unibet_us", "unibet", "sugarhouse", "twinspires", "foxbet", "superbook")


def nfl():
    import nfl_model as M
    pg = S.pbp_games()
    cfg = pickle.load(open(os.path.join(S.CACHE, "nfl_cfg.pkl"), "rb"))
    f = pickle.load(open(os.path.join(S.CACHE, "nflfeat_%g_%g_%g.pkl" % cfg), "rb"))
    pA, _ = M.stage2(pg, f, qb="A", cols="full", first_test=2018)
    pP, _ = M.stage2(pg, f, qb="P", cols="full", first_test=2018)
    lk = S.link_repo(pg)
    fb = {x["id"]: x for x in B.load_football("nfl")}
    out = []
    for g in pg:
        if g["gid"] not in pA or g["close"] is None or not g["reg"]:
            continue
        r = fb.get(lk[g["gid"]]["id"]) if g["gid"] in lk else None
        ff = B.first_fair(r["sp"]) if r else None
        out.append({"id": g["gid"], "season": g["season"], "wkn": g["week"], "margin": g["hs"] - g["as"],
                    "close": g["close"], "pA": pA[g["gid"]], "pP": pP[g["gid"]], "look": ff[1] if ff else None,
                    "days": ff[0] if ff else None, "qbchg": f[g["gid"]]["qbchg_h"] + f[g["gid"]]["qbchg_a"],
                    "feat": f[g["gid"]], "date": g["date"], "fb": r})
    return out


def ncaaf(cfg=None):
    import ncaaf_model as M
    gs = M.games()
    cfg = cfg or pickle.load(open(os.path.join(S.CACHE, "ncaaf_cfg.pkl"), "rb"))
    f = S.cached("ncaaffeat2_%g_%g_%g" % cfg, lambda: M.features(gs, tau=cfg[0], offw=cfg[1], lam_y=cfg[2]))
    pA, _ = M.stage2(gs, f, qb="A")
    pP, _ = M.stage2(gs, f, qb="P")
    fin = {x["id"]: x for x in B.finals("ncaaf")}
    fb = {x["id"]: x for x in B.load_football("ncaaf")}
    first = {}
    for g in gs:
        first.setdefault(g["season"], g["wk"])
    out = []
    for g in gs:
        c = fin.get(g["id"])
        if g["id"] not in pA or not c or c["sp"] is None or g["stype"] != "2":
            continue
        r = fb.get(g["id"])
        ff = B.first_fair(r["sp"]) if r else None
        out.append({"id": g["id"], "season": g["season"], "wkn": g["wk"] - first[g["season"]] + 1,
                    "margin": g["hs"] - g["as"], "close": c["sp"], "pA": pA[g["id"]], "pP": pP[g["id"]],
                    "look": ff[1] if ff else None, "days": ff[0] if ff else None,
                    "qbchg": f[g["id"]]["qbchg_h"] + f[g["id"]]["qbchg_a"], "feat": f[g["id"]], "date": g["date"], "fb": r,
                    "nmin": min(f[g["id"]]["n_h"], f[g["id"]]["n_a"])})
    return out


def records(lg):
    return nfl() if lg == "nfl" else ncaaf()


def med_line(look):
    """median home spread and the median price each side"""
    return (statistics.median(v[0] for v in look.values()),
            statistics.median(S.dec(v[1]) for v in look.values()), statistics.median(S.dec(v[3]) for v in look.values()))


def best_for(look, side, books=None):
    """The best number for `side` across the books (most points, then best price) -> (home-line equivalent, decimal
    price, book)."""
    best = None
    for bk, v in look.items():
        if books and bk not in books:
            continue
        pts, pr = (v[0], v[1]) if side == "home" else (v[2], v[3])
        k = (pts, S.dec(pr))
        if best is None or k > best[0]:
            best = (k, bk)
    if best is None:
        return None
    (pts, d), bk = best
    return (pts if side == "home" else -pts), d, bk


def pay(margin, home_line, side, d):
    r = margin + home_line
    if side == "away":
        r = -r
    return 0.0 if r == 0 else ((d - 1) if r > 0 else -1.0)
