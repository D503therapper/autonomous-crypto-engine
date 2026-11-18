"""S2b - COLLEGE: THE KEY MAN WHO ISN'T THERE ON SATURDAY. There is no college injury-report history on file (the
availability reports started 2023-25, league by league, and nobody archives them), so the news is read off the box
scores (sports_absences._games, 2021-26) - HINDSIGHT, used only to say what late news does to an early dog:
  QB NEWS    = the dog's top passer this game is a different man than its top passer last game (both 10+ throws)
  BACK NEWS  = the dog's lead ball carrier of its last 3 games (most carries) has no line in this game's box at all
Early dogs = +100..+350 at the Tuesday-noon fair look. For each cell: how often, what the price did after our number,
the bet at our number / the Thursday number / the close, train 2021-22 / held out 2023-26. Then what a scan CAN see on
Tuesday: the quarterback already changed in the last 2 games (sports_absences.qb_changed's kind of flag)."""
import json

import ilib
from ilib import E, base, pl

import sports_absences as sa

out = ilib.Tee("s2b_college_out.txt")
BOX = sa._games("ncaaf")
MIN_ATT = 10


def top(rs, group, key, idx=None):
    best, n = None, 0
    for r in rs:
        if r.get("group") != group:
            continue
        try:
            v = json.loads(r.get("stats") or "{}").get(key, "0")
            a = int(str(v).split("/")[idx]) if idx is not None else int(float(v))
        except (ValueError, IndexError, TypeError):
            continue
        if a > n:
            best, n = r.get("pid") or r.get("player"), a
    return best, n


rows = []
for r in base.build("ncaaf"):
    ks = [k for k in r["looks"] if k[0] >= 3.0]
    if not ks or not 100 <= ks[0][2] <= 350 or r["season"] < 2021:
        continue
    log = sorted(BOX.get(str(r["team"]), []), key=lambda x: x[0])
    since = f"{r['season']}-07-01"
    prev = [x for x in log if since <= x[0] < r["start"]]
    this = next((x for x in log if x[1] == r["id"]), None)
    if this is None or len(prev) < 1:
        continue
    q_now, a_now = top(this[2], "passing", "completions/passingAttempts", 1)
    q_last, a_last = top(prev[-1][2], "passing", "completions/passingAttempts", 1)
    if not q_now or not q_last or a_now < MIN_ATT or a_last < MIN_ATT:
        continue
    carries = {}
    for _, _, rs in prev[-3:]:
        for x in rs:
            if x.get("group") == "rushing":
                try:
                    carries[x.get("pid") or x.get("player")] = carries.get(x.get("pid") or x.get("player"), 0) + \
                        int(float(json.loads(x.get("stats") or "{}").get("rushingAttempts", 0)))
                except (ValueError, TypeError):
                    pass
    carries.pop(q_last, None)
    back = max(carries, key=carries.get) if carries else None
    in_box = {x.get("pid") or x.get("player") for x in this[2]}
    unsettled = None
    if len(prev) >= 3:
        qs = [top(x[2], "passing", "completions/passingAttempts", 1)[0] for x in prev[-3:]]
        unsettled = len(set(qs)) > 1
    mid = next((k for k in r["looks"] if 1.5 <= k[0] < 3.0), None)
    rows.append({"r": r, "k": ks[0], "mid": mid, "qb_news": q_now != q_last,
                 "back_news": bool(back) and carries[back] >= 20 and back not in in_box, "unsettled": unsettled,
                 "bar": [h for h in ilib.live_bar(r, ks[0]) if h in ("bye", "hammered")]})
out(f"S2b - college early dogs (+100..+350 at the Tuesday look, 2021-26, both box scores on file): {len(rows)}; "
    f"the bye-spot dogs under the live bar: {sum(1 for x in rows if x['bar'])}")


def cell(name, v, pool=None):
    if len(v) < 8:
        out(f"  {name:58s} n {len(v)}")
        return
    mv = [(x["r"]["close_p"] - x["k"][3]) * 100 for x in v]
    f0 = lambda x: pl(x["r"], x["k"][2])                      # noqa: E731
    w = [x for x in v if x["mid"]]
    d = [pl(x["r"], x["mid"][2]) - f0(x) for x in w]
    out(f"  {name:58s} {len(v) / len(pool or rows) * 100:4.1f}% | the price after {E.mean(mv):+5.2f} pts (t {E.tstat(mv):+4.1f}; 3+ away "
        f"{sum(1 for q in mv if q <= -3) / len(mv) * 100:2.0f}%) | OUR number {ilib.halves(v, f0)}")
    out(f"  {'':58s}        waiting till Thursday = {E.mean(d) * 100:+.2f}% a bet (t {E.tstat(d):+.1f}) | the close "
        f"{E.mean(pl(x['r'], x['r']['close_o']) for x in v) * 100:+.1f}% | z vs our price {E.zwin([(x['r']['won'], x['k'][3]) for x in v]):+.2f}")


out("\n(a) the news, read off Saturday's box (hindsight)")
cell("every early dog", rows)
cell("QB NEWS: a different quarterback than last game", [x for x in rows if x["qb_news"]])
cell("the same quarterback", [x for x in rows if not x["qb_news"]])
cell("BACK NEWS: the lead ball carrier didn't play", [x for x in rows if x["back_news"]])
cell("either", [x for x in rows if x["qb_news"] or x["back_news"]])
cell("neither", [x for x in rows if not (x["qb_news"] or x["back_news"])])
f0 = lambda x: pl(x["r"], x["k"][2])                          # noqa: E731
qn = [x for x in rows if x["qb_news"]]
out(f"  placebo: the QB-news dogs {E.mean(f0(x) for x in qn) * 100:+.1f}% on {len(qn)}; a random {len(qn)} early dogs did as badly "
    f"{ilib.placebo(rows, len(qn), E.mean(f0(x) for x in qn), f0)} of 2,000 times")
out("\n(b) the bye-spot dogs under the live bar")
bar = [x for x in rows if x["bar"]]
cell("every bye-spot dog", bar, bar)
cell("QB or back news", [x for x in bar if x["qb_news"] or x["back_news"]], bar)
cell("no news", [x for x in bar if not (x["qb_news"] or x["back_news"])], bar)
out("\n(c) what a scan can see on Tuesday: the quarterback already changed inside the last 3 games")
for name, sel in (("unsettled (2+ different top passers in the last 3)", True), ("settled", False)):
    v = [x for x in rows if x["unsettled"] is sel]
    hit = sum(1 for x in v if x["qb_news"])
    out(f"  {name}: a different quarterback this game {hit} of {len(v)} ({hit / max(1, len(v)) * 100:.0f}%)")
    cell("   " + name, v)
