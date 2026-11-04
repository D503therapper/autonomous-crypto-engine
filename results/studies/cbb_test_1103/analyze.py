"""🏀 THE COLLEGE HOOPS TEST - choosing the selection rule on 2018-22 (TRAIN) and grading it on 2023-25 (HELD OUT), from
the rows replay.py dumped (every college hoops side on every board day, the whole weighed read next to the price).

The read the live board would bet on each side (the same reads sports.py's gates use - never one factor):
  ML dog  (+100..+350): the dog's WHOLE score - the own read vs the no-vig price + every weighed study angle (dog_score,
                        the angles capped ±STUDY_CAP) -> read = no-vig + score / 100 (sports.dog_gate's read)
  ML fav  (-150..-101): the favorite's WEIGHED read w_p (its own read moved by the dog's angles across it, the Nov-Dec
                        away weight, the efficiency filter, its own top scorer out - inside FAV_CAP), else the own read
  spread  (either side): rank_p - the cover read plus every spread rank weight (ranked road, hot-ATS, the glass, top
                        scorer out, the big home favorite, cover runs, coaches...)
A side is a candidate when that read beats the REAL price (read x decimal - 1 > 0), never a trap, never one the own read
is fighting (sports.fighting), a favorite only once both teams have 3 games (the early Lock rule). Each day: the best
CBB_TEST_MAX_DAY by edge, one per game.

Usage: python analyze.py rows_*.jsonl   (prints every version on train, then the chosen one held out)"""
import glob
import json
import math
import sys
from collections import defaultdict

TRAIN = ("2018", "2019", "2020", "2021", "2022")
HELD = ("2023", "2024", "2025")
BAND = (-150, 350)
MAX_DAY = 2
STUDY_CAP = 6


def season_of(date):
    y, m = int(date[:4]), int(date[5:7])
    return str(y if m >= 7 else y - 1)


def load(paths):
    rows = []
    for p in paths:
        with open(p) as f:
            for line in f:
                r = json.loads(line)
                if r.get("result") not in ("won", "lost", "push"):
                    continue
                if isinstance(r.get("dog_score"), str) or isinstance(r.get("fighting"), str):
                    continue
                r["season"] = season_of(r["date"])
                rows.append(r)
    return rows


def fired(r):
    """The built college hoops edges that moved THIS side's read up (the card's named reasons)."""
    out = []
    m, odds = r["market"], r["odds"]
    if m == "ml" and odds >= 100:
        if r.get("vs_ranked_road"):
            out.append("home dog vs a top-25 road team (Nov-Dec)")
        if (r.get("reb_gap") or 0) >= 6:
            out.append("the glass")
        if (r.get("dog_ctx") or {}).get("opp_won") is False:
            out.append("the favorite lost its last")
    elif m == "ml":
        if r.get("opp_top_out"):
            out.append("their top scorer missed the last game")
        if (r.get("reb_gap") or 0) >= 6:
            out.append("the glass")
        if (r.get("opp_dog_pts") or 0) < 0:
            out.append("the dog's angles are against it")
    else:
        if r.get("vs_ranked_road"):
            out.append("vs a top-25 road team (Nov-Dec)")
        if r.get("ats_gap") is not None and r["ats_gap"] <= -3:
            out.append("the cold-ATS side")
        if (r.get("reb_gap") or 0) >= 6:
            out.append("the glass")
        if r.get("opp_top_out"):
            out.append("their top scorer missed the last game")
    return out


def read_of(r, weights_only=False):
    """(read, edge) for the side under the live rules; None when the side can't be a candidate."""
    m, odds, dec, pm = r["market"], r["odds"], r["dec"], r.get("p_market")
    if pm is None or not dec:
        return None
    if m == "ml" and odds >= 100:
        if r.get("dog_score") is None:
            return None
        sc = r["dog_score"] if not weights_only else max(-STUDY_CAP, min(STUDY_CAP, r["dog_score"] - r["dog_base"]))
        read = min(0.95, pm + sc / 100)
    elif m == "ml":
        own = (r["edge_own"] + 1) / dec if r.get("edge_own") is not None else None
        if own is None:
            return None
        wp = r["w_p"] if r.get("w_p") is not None else own
        read = wp if not weights_only else pm + (wp - own)
    else:
        if r.get("rank_p") is None:
            return None
        read = r["rank_p"] if not weights_only else pm + (r["rank_p"] - r["p"])
    return read, read * dec - 1


FADES = ("ncaab_away_fav", "ncaab_eff_fav", "ncaab_top_out_fav")


def lock_cell(r, opt):
    """The sister study's cell (college hoops knowledge (B), 11/3): a -120..-150 favorite whose WEIGHED read is 56%+ and
    over the price, its own read over the price too, carrying none of the three favorite fades; the early-lock rule."""
    lo, hi = opt.get("lock_band", (-150, -120))
    if r["market"] != "ml" or not lo <= r["odds"] <= hi or r.get("early_lock") == "none":
        return None
    if opt.get("regular") and str(r.get("stype") or "2") != "2" or opt.get("months") and r["date"][5:7] not in opt["months"]:
        return None
    if any(r.get(k) for k in FADES) or r.get("edge_own") is None or r["edge_own"] <= 0:
        return None
    own = (r["edge_own"] + 1) / r["dec"]
    wp = r["w_p"] if r.get("w_p") is not None else own
    if wp < opt.get("lock_min_p", 0.56):
        return None
    edge = wp * r["dec"] - 1
    pts = wp - 1 / r["dec"]
    band = opt.get("lock_pts")
    if edge <= 0 or (band and not band[0] <= pts <= band[1]):
        return None
    return edge


DOG_FADES = ("early_road_dog", "rubber_dog", "top_out", "ranked_road")


def dog_slot(r, opt):
    """The owner's DOG slot (11/3): a college hoops dog +100..+350 the dog gate likes - dog score DOG_GATE+ (every 11/3
    weight in it), the OWN read over the price (edge_own > 0), never a side carrying a fade (the early road dog, the
    rubber-match dog, the top scorer out, a top-25 road dog, a 5+ skid), never a trap / fighting. Ranked by the score
    (the best a night)."""
    if r["market"] != "ml" or not 100 <= r["odds"] <= 350 or r.get("trap") or r.get("fighting") or r.get("dog_score") is None:
        return None
    if opt.get("regular") and str(r.get("stype") or "2") != "2" or opt.get("months") and r["date"][5:7] not in opt["months"]:
        return None
    if any(r.get(k) for k in DOG_FADES) or (r.get("ncaab_skid") or 0) >= 5:
        return None
    if opt.get("dog_own", True) and (r.get("edge_own") is None or r["edge_own"] <= 0):
        return None
    sc = r["dog_score"] if not opt.get("weights_only") else max(-STUDY_CAP, min(STUDY_CAP, r["dog_score"] - r["dog_base"]))
    if sc < opt.get("dog_gate", 4.0):
        return None
    read = min(0.95, r["p_market"] + sc / 100)
    if read * r["dec"] - 1 <= 0:
        return None
    return sc                                                # (ranked by the score, like the Dog of the Day)


def candidate(r, opt):
    if opt.get("dogslot"):
        return dog_slot(r, opt)
    if opt.get("union"):                                     # the weights-only dog OR the sister's favorite cell
        a = candidate(r, dict(opt, union=False, markets=("ml",), side="dog", weights_only=True))
        b = lock_cell(r, dict(opt, lock_pts=opt.get("lock_pts") or (0.01, 0.05)))
        es = [e for e in (a, b) if e is not None]
        return max(es) if es else None
    if opt.get("lock"):
        return lock_cell(r, opt)
    if r["market"] not in opt["markets"] or r.get("trap") or r.get("fighting") or r.get("score") is None:
        return None
    if r["market"] == "ml" and not BAND[0] <= r["odds"] <= BAND[1]:
        return None
    if opt.get("regular") and str(r.get("stype") or "2") != "2":
        return None
    if r["market"] == "ml" and r["odds"] < 100 and r.get("early_lock") == "none":
        return None                                          # the early Lock rule: no college hoops favorite before game 3
    if opt.get("side") == "dog" and not (r["market"] == "ml" and r["odds"] >= 100):
        return None
    if opt.get("side") == "fav" and not (r["market"] == "ml" and r["odds"] < 100):
        return None
    x = read_of(r, opt.get("weights_only", False))
    if x is None:
        return None
    read, edge = x
    if edge <= opt.get("min_edge", 0.0):
        return None
    if opt.get("fired") and not fired(r):
        return None
    if opt.get("months") and r["date"][5:7] not in opt["months"]:
        return None
    return edge


def pick_days(rows, opt):
    """{day: [chosen rows]} - the best MAX_DAY by edge, one per game."""
    by_day = defaultdict(list)
    for r in rows:
        e = candidate(r, opt)
        if e is not None:
            by_day[r["date"]].append((e, r))
    out = {}
    for day, cs in by_day.items():
        seen, chosen = set(), []
        for e, r in sorted(cs, key=lambda x: -x[0]):
            if r["game_id"] in seen:
                continue
            seen.add(r["game_id"])
            r = dict(r, test_edge=round(e, 4))
            chosen.append(r)
            if len(chosen) >= opt.get("max_day", MAX_DAY):
                break
        out[day] = chosen
    return out


def grade(chosen):
    """(n, won, lost, net units at 1u flat, roi, seasons up / seasons)"""
    n = w = l = 0
    net = 0.0
    by_s = defaultdict(float)
    n_s = defaultdict(int)
    for day, rs in chosen.items():
        for r in rs:
            if r["result"] == "push":
                continue
            n += 1
            n_s[r["season"]] += 1
            if r["result"] == "won":
                w += 1
                net += r["dec"] - 1
                by_s[r["season"]] += r["dec"] - 1
            else:
                l += 1
                net -= 1
                by_s[r["season"]] -= 1
    up = sum(v > 0 for v in by_s.values())
    return n, w, l, round(net, 1), (net / n if n else 0.0), up, len(by_s), dict(by_s), dict(n_s)


def line(name, rows, opt, seasons):
    sub = [r for r in rows if r["season"] in seasons]
    ch = pick_days(sub, opt)
    n, w, l, net, roi, up, ns, by_s, n_s = grade(ch)
    days = len({d for d, rs in ch.items() if rs})
    per = f"{by_s[s]:+.0f}u/{n_s[s]}" if False else " ".join(f"{s[2:]}:{by_s.get(s, 0):+.0f}u" for s in sorted(n_s))
    z = (net / math.sqrt(n)) / 1.0 if n else 0.0            # (rough: units won per bet ~ sd 1)
    return (f"{name:58s} n {n:5d} {w:4d}-{l:<4d} {roi:+6.1%} {net:+7.1f}u  {up}/{ns} up  z {z:+.1f}  days {days:4d} "
            f"{n / max(days, 1):.2f}/day  {per}"), (n, roi, up, ns)


def main(paths):
    rows = load(paths)
    print(f"{len(rows)} graded sides, seasons {sorted({r['season'] for r in rows})}")
    print(f"days {len({r['date'] for r in rows})}")
    base = {"markets": ("ml", "spread"), "regular": True}
    versions = [
        ("BASE: ml + spread, whole read beats the price, top 2 / day", dict(base)),
        ("  ml only", dict(base, markets=("ml",))),
        ("  spread only", dict(base, markets=("spread",))),
        ("  ml dogs only", dict(base, markets=("ml",), side="dog")),
        ("  ml favorites only", dict(base, markets=("ml",), side="fav")),
        ("  edge 1%+", dict(base, min_edge=0.01)),
        ("  edge 2%+", dict(base, min_edge=0.02)),
        ("  edge 3%+", dict(base, min_edge=0.03)),
        ("  edge 5%+", dict(base, min_edge=0.05)),
        ("  a built college hoops edge has to fire on the side", dict(base, fired=True)),
        ("  fired + spread only", dict(base, fired=True, markets=("spread",))),
        ("  fired + ml only", dict(base, fired=True, markets=("ml",))),
        ("  WEIGHTS-ONLY read (own read = the market)", dict(base, weights_only=True)),
        ("  weights-only, spread only", dict(base, weights_only=True, markets=("spread",))),
        ("  weights-only, ml only", dict(base, weights_only=True, markets=("ml",))),
        ("  weights-only, ml dogs", dict(base, weights_only=True, markets=("ml",), side="dog")),
        ("  weights-only, ml favorites", dict(base, weights_only=True, markets=("ml",), side="fav")),
        ("  weights-only + fired", dict(base, weights_only=True, fired=True)),
        ("  weights-only + fired, spread", dict(base, weights_only=True, fired=True, markets=("spread",))),
        ("  weights-only + fired, ml", dict(base, weights_only=True, fired=True, markets=("ml",))),
        ("  weights-only, edge 2%+", dict(base, weights_only=True, min_edge=0.02)),
        ("  weights-only, edge 3%+", dict(base, weights_only=True, min_edge=0.03)),
        ("  weights-only, spread, edge 2%+", dict(base, weights_only=True, markets=("spread",), min_edge=0.02)),
        ("  Nov-Dec only", dict(base, months=("11", "12"))),
        ("  weights-only, Nov-Dec only", dict(base, weights_only=True, months=("11", "12"))),
        ("  Jan-Mar only", dict(base, months=("01", "02", "03", "04"))),
        ("  top 1 a day", dict(base, max_day=1)),
        ("  weights-only, top 1 a day", dict(base, weights_only=True, max_day=1)),
        ("  top 3 a day", dict(base, max_day=3)),
        ("  postseason in", dict(base, regular=False)),
        ("SISTER (B): -120..-150 fav, weighed 56%+ over price, own over, no fade", dict(base, lock=True)),
        ("  sister, edge 1-5 points over the price", dict(base, lock=True, lock_pts=(0.01, 0.05))),
        ("  sister, the -101..-150 band", dict(base, lock=True, lock_band=(-150, -101))),
        ("  sister, no cap a day", dict(base, lock=True, max_day=99)),
        ("  sister, edge 1-5, no cap a day", dict(base, lock=True, lock_pts=(0.01, 0.05), max_day=99)),
        ("  sister, Nov-Dec", dict(base, lock=True, months=("11", "12"))),
        ("FAV SLOT: the sister cell, 1 a day", dict(base, lock=True, max_day=1)),
        ("  fav slot, edge 1-5 points, 1 a day", dict(base, lock=True, lock_pts=(0.01, 0.05), max_day=1)),
        ("DOG SLOT: dog gate 4+, own over, no fade, best score a night", dict(base, dogslot=True, max_day=1)),
        ("  dog slot, gate 4+, no own-read rule", dict(base, dogslot=True, max_day=1, dog_own=False)),
        ("  dog slot, gate 2+", dict(base, dogslot=True, max_day=1, dog_gate=2.0)),
        ("  dog slot, gate 6+", dict(base, dogslot=True, max_day=1, dog_gate=6.0)),
        ("  dog slot, weights-only score 2+", dict(base, dogslot=True, max_day=1, weights_only=True, dog_gate=2.0)),
        ("  dog slot, weights-only score 4+", dict(base, dogslot=True, max_day=1, weights_only=True, dog_gate=4.0)),
        ("  dog slot, weights-only 2+, no own-read rule", dict(base, dogslot=True, max_day=1, weights_only=True, dog_gate=2.0, dog_own=False)),
        ("  dog slot, every gated dog (no cap)", dict(base, dogslot=True, max_day=99)),
        ("  dog slot, Nov-Dec", dict(base, dogslot=True, max_day=1, months=("11", "12"))),
        ("UNION: weights-only ml dog OR the sister cell (edge 1-5), top 2", dict(base, union=True)),
        ("  union, top 1 a day", dict(base, union=True, max_day=1)),
        ("  union, top 3 a day", dict(base, union=True, max_day=3)),
    ]
    print("\n=== TRAIN 2018-22 (the rule is chosen here) ===")
    for name, opt in versions:
        print(line(name, rows, opt, TRAIN)[0])
    print("\n=== HELD OUT 2023-25 (every version, for honesty - the choice is made on train) ===")
    for name, opt in versions:
        print(line(name, rows, opt, HELD)[0])
    print("\n=== every priced side at the close, the base rates (no rule) ===")
    for name, flt in (("ml dogs +100..+350", lambda r: r["market"] == "ml" and 100 <= r["odds"] <= 350),
                      ("ml favs -150..-101", lambda r: r["market"] == "ml" and -150 <= r["odds"] <= -101),
                      ("spread sides", lambda r: r["market"] == "spread")):
        for seasons, tag in ((TRAIN, "train"), (HELD, "held")):
            sub = [r for r in rows if flt(r) and r["season"] in seasons and r["result"] != "push"
                   and str(r.get("stype") or "2") == "2"]
            net = sum((r["dec"] - 1) if r["result"] == "won" else -1 for r in sub)
            print(f"  {name:22s} {tag:5s} n {len(sub):6d} roi {net / max(len(sub), 1):+6.1%}")


if __name__ == "__main__":
    paths = sys.argv[1:] or sorted(glob.glob("rows_*.jsonl"))
    main(paths)
