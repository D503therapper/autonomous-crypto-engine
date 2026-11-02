"""STUDY 4 - NHL LINE MOVEMENT, next-day open -> game-day morning -> close (never studied for hockey at these points; the
10/28 bonus was ESPN open -> close 2023-27, the 10/30 market-trend is the team's PAST games).
 (a) FOLLOW or FADE the open -> morning move (bet at the morning price - the 8 AM board's number);
 (b) does the move keep going after the board (morning -> close)? = the CLV of following it at 8 AM;
 (c) the goalie news: how often a big morning move comes with a backup starting (the ACTUAL starter from the box score -
     known only after the game, so it EXPLAINS the move; a bet on it would need the news first);
 (d) BOOK SOFTNESS: each book's morning number vs the median book's no-vig - which books lag the market, and does
     betting a book's outlier price (its price beats the consensus fair price by 2%+ / 4%+) pay?
TRAIN = 2020-21 + 2021-22, HELD OUT = 2022-23 (the open is thin in 2022-23 - (a)/(b) lean on the two train seasons and
the per-season split). ~40 cells: about 2 would clear |z| 2 by luck."""
from collections import defaultdict
import json
import statistics
import lib

D = lib.build()
ROWS = [r for r in D["rows"] if lib.in_seasons(r)]
out = []


def P(s):
    print(s); out.append(s)


def S(bets):
    return lib.st(bets)


def side_bet(r, s, at):
    """(season, profit at that price) for side s ('h'/'a')."""
    if at == "close":
        d = lib.dec(r["ch"] if s == "h" else r["ca"])
    else:
        d = r[at]["dh"] if s == "h" else r[at]["da"]
    won = r["hw"] if s == "h" else 1 - r["hw"]
    return (r["season"], (d - 1) if won else -1.0, 1)


# ---- (a) + (b)
P("== (a) the open -> morning move: FOLLOW (bet the side the money came to) at the morning price ==")
both = [r for r in ROWS if r["open"] and r["morning"]]
P(f"games with both looks: {len(both)}; median |move| {100 * statistics.median(abs(r['morning']['p'] - r['open']['p']) for r in both):.2f} pts")
for lo, hi in ((0.015, 0.03), (0.03, 0.05), (0.05, 1.0), (0.03, 1.0)):
    fol, fad, fol_c, cont = [], [], [], []
    fol_dog, fol_fav = [], []
    for r in both:
        mv = r["morning"]["p"] - r["open"]["p"]
        if not lo <= abs(mv) < hi:
            continue
        s = "h" if mv > 0 else "a"
        o = "a" if s == "h" else "h"
        b = side_bet(r, s, "morning")
        fol.append(b); fad.append(side_bet(r, o, "morning")); fol_c.append(side_bet(r, s, "close"))
        d = r["morning"]["dh"] if s == "h" else r["morning"]["da"]
        (fol_dog if d >= 2.0 else fol_fav).append(b)
        mc = r["p_close"] - r["morning"]["p"]
        cont.append(1 if (mc > 0) == (mv > 0) and abs(mc) > 0.005 else 0 if abs(mc) > 0.005 else 0.5)
    P(lib.line(f" move {100 * lo:.1f}-{100 * hi:.0f} pts FOLLOW at the morning", S(fol)))
    P(lib.line(f"   FADE at the morning", S(fad)))
    P(lib.line(f"   follow, the side is a DOG", S(fol_dog)))
    P(lib.line(f"   follow, the side is a FAVORITE", S(fol_fav)))
    P(f"   kept going after the board (morning -> close same way): {100 * sum(cont) / max(len(cont), 1):.1f}% of {len(cont)}")

P("\n== (b) the morning -> close move (after the 8 AM board) - how much of the day's move is still to come ==")
mm = [abs(r["p_close"] - r["morning"]["p"]) for r in ROWS if r["morning"]]
om = [abs(r["morning"]["p"] - r["open"]["p"]) for r in both]
P(f" median |open -> morning| {100 * statistics.median(om):.2f} pts, |morning -> close| {100 * statistics.median(mm):.2f} pts; "
  f"3+ pts open->morning {sum(1 for x in om if x >= 0.03)} of {len(om)}, morning->close {sum(1 for x in mm if x >= 0.03)} of {len(mm)}")
# the dog the money came to in the morning: does it beat the close? (CLV of the 8 AM number)
for nm, f in (("dog the money came TO 2+ (open->morning)", lambda mv: mv >= 0.02), ("dog the money LEFT 2+", lambda mv: mv <= -0.02)):
    bets_m, bets_c, clv = [], [], []
    for r in both:
        for s in ("h", "a"):
            d = r["morning"]["dh"] if s == "h" else r["morning"]["da"]
            if not 2.0 <= d <= 4.5:
                continue
            mv = r["morning"]["p"] - r["open"]["p"]
            mv = mv if s == "h" else -mv
            if f(mv):
                bets_m.append(side_bet(r, s, "morning")); bets_c.append(side_bet(r, s, "close"))
                pc = r["p_close"] if s == "h" else 1 - r["p_close"]
                clv.append(pc * d - 1)
    P(lib.line(f" {nm} at the morning", S(bets_m)))
    P(lib.line(f"   ...at the close", S(bets_c)))
    P(f"   CLV of the morning price vs the close's fair %: {100 * statistics.mean(clv):+.2f}% (n {len(clv)})")

# ---- (c) goalie news
P("\n== (c) a big morning move and the backup goalie (the ACTUAL starter - explains, never a bet signal) ==")
cnt = defaultdict(lambda: [0, 0])
for r in both:
    mv = r["morning"]["p"] - r["open"]["p"]
    for s, sgn in (("h", 1), ("a", -1)):
        bk = r[f"bk_{s}"]
        if bk is None:
            continue
        m = mv * sgn                 # + = toward this team
        key = "moved AWAY 3+" if m <= -0.03 else "moved away 1.5-3" if m <= -0.015 else "flat" if m < 0.015 else "moved TO 1.5+"
        cnt[key][0] += 1; cnt[key][1] += int(bk)
for k in ("moved AWAY 3+", "moved away 1.5-3", "flat", "moved TO 1.5+"):
    n, b = cnt[k]
    P(f"  team the market {k}: its backup started {b}/{n} = {100 * b / max(n, 1):.1f}%")
mm_c = defaultdict(lambda: [0, 0])
for r in ROWS:
    if not r["morning"]:
        continue
    mv = r["p_close"] - r["morning"]["p"]
    for s, sgn in (("h", 1), ("a", -1)):
        bk = r[f"bk_{s}"]
        if bk is None:
            continue
        m = mv * sgn
        key = "AWAY 3+" if m <= -0.03 else "away 1.5-3" if m <= -0.015 else "flat" if m < 0.015 else "TO 1.5+"
        mm_c[key][0] += 1; mm_c[key][1] += int(bk)
for k in ("AWAY 3+", "away 1.5-3", "flat", "TO 1.5+"):
    n, b = mm_c[k]
    P(f"  after the board (morning -> close) moved {k}: backup started {b}/{n} = {100 * b / max(n, 1):.1f}%")
# the bet a goalie-news follower would make at the morning: the side the morning moved toward when the OTHER side started its
# backup is look-ahead; instead: does the morning price already hold the backup? side on its backup, bet at morning vs close
for nm, f in (("a team starting its BACKUP (bet at the morning)", lambda r, s: r[f"bk_{s}"] is True),
              ("the side FACING a backup", lambda r, s: r[f"bk_{'a' if s == 'h' else 'h'}"] is True and r[f"bk_{s}"] is False)):
    bm = [side_bet(r, s, "morning") for r in ROWS if r["morning"] for s in ("h", "a") if f(r, s)]
    bc = [side_bet(r, s, "close") for r in ROWS if r["morning"] for s in ("h", "a") if f(r, s)]
    P(lib.line(f"  {nm}", S(bm)))
    P(lib.line(f"    ...at the close (the news priced in)", S(bc)))

# ---- (d) book softness
P("\n== (d) BOOK SOFTNESS at the morning: each book's no-vig vs the median book's, and vs the close ==")
dev = defaultdict(list); clvb = defaultdict(list)
for r in ROWS:
    m = r["morning"]
    if not m:
        continue
    for b, (h, a) in m["q"].items():
        p = lib.nv(h, a)
        dev[b].append(abs(p - m["p"]))
        clvb[b].append(abs(p - r["p_close"]) - abs(m["p"] - r["p_close"]))   # + = this book further from the close than the median
for b in sorted(dev, key=lambda b: -statistics.mean(clvb[b])):
    if len(dev[b]) >= 300:
        P(f"  {b:16s} n {len(dev[b]):5d}  off the median {100 * statistics.mean(dev[b]):.2f} pts  further from the close than the median by {100 * statistics.mean(clvb[b]):+.2f} pts")


def outlier_bets(edge_min, books=None, dogs=None):
    bets = []
    for r in ROWS:
        m = r["morning"]
        if not m:
            continue
        for s in ("h", "a"):
            fair = m["p"] if s == "h" else 1 - m["p"]
            best = None
            for b, (h, a) in m["q"].items():
                if books and b not in books:
                    continue
                o = h if s == "h" else a
                d = lib.dec(o)
                ev = fair * d - 1
                if ev >= edge_min and (best is None or d > best[0]):
                    best = (d, b)
            if best:
                if dogs is True and best[0] < 2.0 or dogs is False and best[0] >= 2.0 or best[0] > 4.5 or best[0] < 1.667:
                    continue
                won = r["hw"] if s == "h" else 1 - r["hw"]
                bets.append((r["season"], (best[0] - 1) if won else -1.0, 1))
    return bets


for e in (0.02, 0.04, 0.06):
    P(lib.line(f" bet ANY book's price {100 * e:.0f}%+ over the consensus fair (-150..+350)", S(outlier_bets(e))))
    P(lib.line(f"   dogs", S(outlier_bets(e, dogs=True))))
    P(lib.line(f"   favorites", S(outlier_bets(e, dogs=False))))
US = {"draftkings", "fanduel", "betmgm", "williamhill_us", "caesars", "pointsbetus", "betrivers", "sugarhouse", "barstool",
      "wynnbet", "unibet_us", "foxbet", "twinspires", "superbook", "circasports"}
for e in (0.02, 0.04):
    P(lib.line(f" US-licensed books only, {100 * e:.0f}%+ over fair", S(outlier_bets(e, books=US))))

json.dump(out, open(f"{lib.OUT}/s4_out.json", "w"), indent=0)
open(f"{lib.OUT}/s4_out.txt", "w").write("\n".join(out) + "\n")
