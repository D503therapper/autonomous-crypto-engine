"""S1 - DOES WAITING FOR THE INJURY NEWS PAY? The paid odds history (2020-25 + Sept 2026, the median book, FAIR looks
only). The NFL's looks sit right on the injury clock for a Sunday game: Tuesday noon ET (BEFORE Wednesday's first
practice report), Thursday noon (AFTER Wednesday's report), Saturday noon (AFTER Friday's final statuses), Sunday
morning, the close. College: Tuesday noon (before any availability report), Thursday noon (after the SEC / Big 12
Wednesday-night reports where a league has them - 2024 on), Saturday morning, the close.
(a) THE SAME DOGS, FOUR PRICES: the dogs picked at the pre-report look (every dog +100..+350; the spot dogs under the
    live bar - ilib.live_bar), graded at the pre-report price, the after-first-report price, the after-final price, the
    close. Head to head on the same bets (waiting = later minus earlier, a bet).
(b) THE RULE RE-RUN LATER: the spot bar run at the later look's own price (a dog has to still be +100..+350 and still
    clear the bar there) - what "post only after Wednesday's report" would have posted and how it did.
(c) every season, train 2020-22 / held out 2023-26, and a placebo for the waiting cost (random dogs, same n)."""
import ilib
from ilib import E, base, pl

out = ilib.Tee("s1_timing_out.txt")
ROWS = {lg: base.build(lg) for lg in ("nfl", "ncaaf")}
SPOTS_ON = ("bye", "mnf", "eastwest", "hammered")           # (the blowout spot is paused from 11/12 - shown apart)


def looks_by_phase(r):
    """{phase: the first look in it} - 1.5+ days out for pre / mid (an early play is never a game-day play), the
    final look = the first one after the final statuses that is still before game day (0.5+ days out)."""
    d = {}
    for k in r["looks"]:
        if r["lg"] == "nfl":
            ph = ilib.phase(r, k)
            if ph != "final" and k[0] < 1.5:
                continue
            if ph == "final" and k[0] < 0.5:
                d.setdefault("morning", k)
                continue
        else:
            ph = "pre" if k[0] >= 3.0 else "mid" if k[0] >= 1.5 else "morning"
        d.setdefault(ph, k)
    return d


def table(lg, nm, v):
    """v: [{r, L}] picked at the pre look."""
    if len(v) < 12:
        out(f"  {nm}: n {len(v)} - too few")
        return
    out(f"\n  {nm}: {len(v)} dogs picked BEFORE the first report")
    f0 = lambda x: pl(x["r"], x["L"]["pre"][2])               # noqa: E731
    out(f"    at the pre-report price     {ilib.halves(v, f0)} | won {sum(x['r']['won'] for x in v) / len(v) * 100:.1f}% "
        f"(price said {E.mean(x['L']['pre'][3] for x in v) * 100:.1f}%) | beat the close {E.mean((x['r']['close_p'] - x['L']['pre'][3]) * 100 for x in v):+.2f} pts")
    for ph, lab in (("mid", "after the FIRST report"), ("final", "after the FINAL statuses"), ("morning", "game morning")):
        w = [x for x in v if ph in x["L"]]
        if len(w) < 12:
            continue
        f1 = lambda x, ph=ph: pl(x["r"], x["L"][ph][2])       # noqa: E731
        d = [f1(x) - f0(x) for x in w]
        dh = [f1(x) - f0(x) for x in w if x["r"]["season"] > ilib.TRAIN_TO]
        dt = [f1(x) - f0(x) for x in w if x["r"]["season"] <= ilib.TRAIN_TO]
        mv = [(x["L"][ph][3] - x["L"]["pre"][3]) * 100 for x in w]
        by = {}
        for x in w:
            by.setdefault(x["r"]["season"], []).append(f1(x) - f0(x))
        out(f"    same dogs {lab:25s} {ilib.halves(w, f1)}")
        out(f"       WAITING = {E.mean(d) * 100:+.2f}% a bet (t {E.tstat(d):+.1f}; train {E.mean(dt) * 100:+.2f}% / held {E.mean(dh) * 100:+.2f}%; "
            f"seasons waiting paid {sum(1 for p in by.values() if sum(p) > 0)}/{len(by)}) | the price moved {E.mean(mv):+.2f} pts to the dog (t {E.tstat(mv):+.1f}) | "
            f"still +100..+350 there {sum(1 for x in w if 100 <= x['L'][ph][2] <= 350) / len(w) * 100:.0f}%")
    fc = lambda x: pl(x["r"], x["r"]["close_o"])             # noqa: E731
    d = [fc(x) - f0(x) for x in v]
    out(f"    same dogs at the close        {ilib.halves(v, fc)}")
    out(f"       WAITING to the close = {E.mean(d) * 100:+.2f}% a bet (t {E.tstat(d):+.1f})")


for lg in ("nfl", "ncaaf"):
    out("=" * 40, lg.upper())
    picks = []
    for r in ROWS[lg]:
        L = looks_by_phase(r)
        if "pre" not in L:
            continue
        picks.append({"r": r, "L": L})
    dogs = [x for x in picks if 100 <= x["L"]["pre"][2] <= 350]
    out(f" (a) THE SAME DOGS AT FOUR PRICES - sides with a pre-report fair look: {len(picks)}; dogs +100..+350 there: {len(dogs)}")
    table(lg, "EVERY DOG +100..+350", dogs)
    bar = [dict(x, hit=ilib.live_bar(x["r"], x["L"]["pre"])) for x in dogs]
    bar = [x for x in bar if x["hit"]]
    on = [x for x in bar if any(h in SPOTS_ON for h in x["hit"])]
    table(lg, "THE SPOT DOGS UNDER THE LIVE BAR (bye / Monday night / East-West / hammered - the spots that are on)", on)
    for sp in ("bye", "mnf", "eastwest", "hammered", "blowout"):
        if lg in E.se.SPOTS[sp][2]:
            table(lg, f"spot: {sp}" + (" (PAUSED 11/12)" if sp == "blowout" else ""), [x for x in bar if sp in x["hit"]])
    exam = [x for x in dogs if x["r"]["own"] is not None and x["r"]["own"] - x["L"]["pre"][3] >= 0.04]
    table(lg, "the read 4+ points over the price (the exam scan's kind of dog)", exam)
    if lg == "ncaaf":
        table(lg, "EVERY DOG, 2024-26 only (the seasons the SEC / Big 12 post Wednesday-night availability reports)",
              [x for x in dogs if x["r"]["season"] >= 2024])
        table(lg, "THE SPOT DOGS (on), 2024-26 only", [x for x in on if x["r"]["season"] >= 2024])

    out(f"\n (b) THE RULE RE-RUN AT EACH LOOK'S OWN PRICE ({lg}) - what posting only then would have posted")
    for ph, lab in (("pre", "BEFORE the first report (today's timing)"), ("mid", "only AFTER the first report"),
                    ("final", "only AFTER the final statuses")):
        v = []
        for r in ROWS[lg]:
            L = looks_by_phase(r)
            if ph not in L:
                continue
            hit = ilib.live_bar(r, L[ph])
            if any(h in SPOTS_ON for h in hit):
                v.append({"r": r, "L": L, "k": L[ph]})
        if len(v) < 12:
            out(f"  {lab}: n {len(v)}")
            continue
        f = lambda x: pl(x["r"], x["k"][2])                  # noqa: E731
        by = {}
        for x in v:
            by.setdefault(x["r"]["season"], []).append(f(x))
        out(f"  {lab:42s} {ilib.halves(v, f)} | beat the close {E.mean((x['r']['close_p'] - x['k'][3]) * 100 for x in v):+.2f} pts | "
            f"z vs the price {E.zwin([(x['r']['won'], x['k'][3]) for x in v]):+.2f}")
        out("       by season: " + "  ".join(f"{s} {sum(1 for q in p if q > 0)}-{sum(1 for q in p if q < 0)} {E.mean(p) * 100:+.0f}%" for s, p in sorted(by.items())))
        if ph != "pre":
            pre_ids = {(x["r"]["id"], x["r"]["side"]) for x in on}
            keep = [x for x in v if (x["r"]["id"], x["r"]["side"]) in pre_ids]
            new = [x for x in v if (x["r"]["id"], x["r"]["side"]) not in pre_ids]
            lost = [x for x in on if (x["r"]["id"], x["r"]["side"]) not in {(y["r"]["id"], y["r"]["side"]) for y in v} and ph in x["L"]]
            out(f"       of them: also a play at the pre look {E.roi([f(x) for x in keep])} | new at this look {E.roi([f(x) for x in new])} | "
                f"pre-look plays that no longer clear here (at the pre price) {E.roi([pl(x['r'], x['L']['pre'][2]) for x in lost])}")

    out(f"\n (c) PLACEBO ({lg}): is the spot dogs' cost of waiting for the first report any different from a random dog's?")
    w = [x for x in on if "mid" in x["L"]]
    pool = [x for x in dogs if "mid" in x["L"]]
    dd = lambda x: pl(x["r"], x["L"]["mid"][2]) - pl(x["r"], x["L"]["pre"][2])     # noqa: E731
    if w:
        tgt = E.mean(dd(x) for x in w)
        out(f"  spot dogs: waiting {tgt * 100:+.2f}% a bet on {len(w)}; every dog {E.mean(dd(x) for x in pool) * 100:+.2f}% on {len(pool)}; "
            f"a random {len(w)} dogs' waiting was as bad or worse {ilib.placebo(pool, len(w), tgt, dd)} of 2,000 times, "
            f"as good or better {ilib.placebo(pool, len(w), tgt, dd, worse=False)} of 2,000")
