"""The 11/23 dry run (results/studies/cards_1123/README.md): (a) every card posted since SINCE - as it posted, re-written
by yesterday's writer (the 11/23 switches off) and re-written now, each as the page shows it; (b) every candidate side
for the days given (moneylines -150..+350 in every league + the college hoops spread sides with a study stack),
before / now. Counts: fact lines a card, cards under 6, cards with no reason line, cards with no line that says why,
same-stat repeats. No network (the injury lists are the ones each posted card stored); nothing is saved but
dry_posted.md / dry_cand.md next to this file. Run from the repo root:
    python results/studies/cards_1123/dry.py posted [league]
    python results/studies/cards_1123/dry.py cand 2026-11-23 2026-11-24 2026-11-25"""
import sys, os, json, copy, re, time, io, contextlib
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cards_1122"))
from datetime import datetime, timezone, timedelta
import h
from h import games, elo, picks, model, sm, sd, sports, sports_breakdown, v24, cc
import sports_card_sell as cs
import sports_dashboard as dash
import sports_card_guard

SINCE = "2026-11-12"
dash._GAMES_[0] = games
NOTES = []
NOTE_ON = [False]
cc.note = lambda day, leg, why, line, where: NOTES.append((leg.get("team"), why, str(line)[:160])) if NOTE_ON[0] else None


def switch(on):
    """the 11/23 changes on / off (off = the VERSION 85 writer)"""
    cs.TRIM = cs.SCHED_FACTS = cs.REASONS_1123 = bool(on)


def page(pk, leg):
    """(why, lines) as the page shows the card: the guard + the card check."""
    try:
        lines = [dash.pct_ok(x) for x in sports_card_guard.clean(
            [x for x in leg.get("breakdown") or [] if isinstance(x, str)], leg.get("league"), leg.get("team", ""), leg.get("opp", ""))]
        why = cc.check_one(pk, leg, leg.get("why_line") or "", games) if leg.get("why_line") else ""
        if isinstance(why, tuple):
            why = why[0]
        lines = cc.check(pk, leg, lines, games, why=why or "")
        return why or "", lines
    except Exception as e:                                   # noqa: BLE001
        print("page err", repr(e), file=sys.stderr)
        return leg.get("why_line") or "", list(leg.get("breakdown") or [])


def score(leg, why, lines):
    us, them = leg.get("team") or "", leg.get("opp") or ""
    body = [x for x in lines if isinstance(x, str) and not cc.BOTTOM.match(x) and not x.startswith(("⚠️", "🔄", "🌟", "🟡", "🔒", "💎"))]
    allf = ([why] if why else []) + body
    on = cs.REASONS_1123
    cs.REASONS_1123 = True                                   # (a repeat is counted by today's rule, before and after)
    reps = len(cs.dedupe(body, us, them, why)[1])
    cs.REASONS_1123 = on
    kinds = [cs.reason_backed(x, leg) for x in allf]
    return {"facts": len(allf), "repeats": reps, "reason": kinds.count("reason"), "matchup": kinds.count("matchup"),
            "why_kind": kinds[0] if why else "none"}


def fmt(why, lines):
    return "\n".join(["WHY: " + (why or "(none)")] + ["  " + str(x) for x in lines])


def agg(rows, label):
    n = len(rows)
    if not n:
        return f"| {label} | 0 | | | | | | |"
    s = lambda k: sum(r[k] for r in rows)
    return (f"| {label} | {n} | {s('facts') / n:.1f} | {sum(1 for r in rows if r['facts'] < 6)} | "
            f"{sum(1 for r in rows if not r['reason'])} | {sum(1 for r in rows if not r['reason'] + r['matchup'])} | {s('repeats')} | "
            f"{sum(1 for r in rows if r['why_kind'] in ('reason', 'matchup'))} |")


HEAD = ("| what | cards | fact lines a card | cards under 6 | cards with no reason line | cards with no line that says why | same-stat repeats | line under the pick says why |\n"
        "|---|---|---|---|---|---|---|---|")


def posted(out, only=None):
    B, O, A = [], [], []
    used, used_o = set(), set()
    for pk in picks:
        if pk["date"] < SINCE or pk.get("lean") or pk.get("kind") in ("lean",):
            continue
        for leg in pk["legs"]:
            if leg["game_id"] not in games or (only and leg["league"] != only) or leg.get("market") not in ("ml", "spread"):
                continue
            b = score(leg, leg.get("why_line") or "", leg.get("breakdown") or [])
            buf = io.StringIO()
            v24.SELL_FROM = "2026-11-01"
            switch(False)
            with contextlib.redirect_stdout(buf):
                old = h.rewrite(leg, used_o)
                old.pop("bv", None)
                ow, ol = page({**pk, "legs": [old]}, old)
            o = score(old, ow, ol)
            switch(True)
            with contextlib.redirect_stdout(buf):
                new = h.rewrite(leg, used)
                new.pop("bv", None)
            NOTE_ON[0] = True
            pw, pl = page({**pk, "legs": [new]}, new)
            NOTE_ON[0] = False
            a = score(new, pw, pl)
            B.append(b); O.append(o); A.append(a)
            out.append(f"\n### {pk['date']} {leg['league']} - {leg['team']} {leg.get('odds'):+} {('%+g' % leg['line']) if leg.get('market') == 'spread' else ''} vs {leg['opp']} ({pk['kind']})\n")
            out.append("the reasons the leg carries: " + "; ".join(str(r)[:110] for r in leg.get("reasons") or []) + "\n")
            out.append(f"As it posted ({b['facts']} fact lines, {b['repeats']} repeats, {b['reason']} reason-backed, {b['matchup']} matchup):\n\n```\n{fmt(leg.get('why_line'), leg.get('breakdown') or [])}\n```\n")
            out.append(f"VERSION 85's writer, on the page ({o['facts']} fact lines, {o['repeats']} repeats, {o['reason']} reason-backed, {o['matchup']} matchup):\n\n```\n{fmt(ow, ol)}\n```\n")
            out.append(f"Now, on the page ({a['facts']} fact lines, {a['repeats']} repeats, {a['reason']} reason-backed, {a['matchup']} matchup):\n\n```\n{fmt(pw, pl)}\n```\n")
    return B, O, A


def cands(day, out):
    d = datetime.strptime(day, "%Y-%m-%d").date()
    at = datetime(d.year, d.month, d.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
    rows_b, rows_a = {}, {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cs_ = sports.candidates(games, model, now=at, day=d, injuries={lg: {} for lg in sd.LEAGUES})
    except Exception as e:                                   # noqa: BLE001
        print("cand err", repr(e), file=sys.stderr)
        return rows_b, rows_a
    used_a, used_b = set(), set()
    for c in cs_:
        ml = c.get("market") == "ml" and -150 <= (c.get("odds") or 0) <= 350
        stack = c.get("league") == "ncaab" and c.get("market") == "spread" and (c.get("spread_stack") or 0) >= 0.05 - 1e-9
        if not (ml or stack):
            continue
        g = games[c["game_id"]]
        for on, rows, used in ((False, rows_b, used_b), (True, rows_a, used_a)):
            leg = copy.deepcopy(c)
            leg.setdefault("tier", "value")
            switch(on)
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, {leg["league"]: {}}, used)
                    sports.card_extras(leg, g, {leg["league"]: {}})
            except Exception as e:                           # noqa: BLE001
                print("bd err", c.get("team"), repr(e), file=sys.stderr)
                continue
            pk = {"date": day, "kind": "play", "legs": [leg], "lean": False, "tier": "value", "status": "open", "american": leg.get("odds")}
            NOTE_ON[0] = on
            pw, pl = page(pk, leg)
            NOTE_ON[0] = False
            rows.setdefault(leg["league"], []).append(score(leg, pw, pl))
            if on:
                out.append(f"\n#### {day} {leg['league']} - {leg['team']} {leg.get('odds'):+} {('%+g' % leg['line']) if leg.get('market') == 'spread' else ''} vs {leg['opp']}\n\n```\n{fmt(pw, pl)}\n```\n")
    switch(True)
    return rows_b, rows_a


if __name__ == "__main__":
    what = sys.argv[1]
    out = []
    print(HEAD)
    if what == "posted":
        only = sys.argv[2] if len(sys.argv) > 2 else None
        B, O, A = posted(out, only)
        tag = f"{only or 'every league'}, unit cards posted {SINCE}..11/23"
        print(agg(B, f"{tag}, as they posted"))
        print(agg(O, f"{tag}, re-written by VERSION 85's writer, on the page"))
        print(agg(A, f"{tag}, re-written now, on the page"))
        what = f"posted_{only or 'all'}"
    else:
        tb, ta = {}, {}
        for day in sys.argv[2:]:
            b, a = cands(day, out)
            for lg in b:
                tb.setdefault(lg, []).extend(b[lg]); ta.setdefault(lg, []).extend(a.get(lg, []))
            print(agg(b.get("ncaab", []), f"{day} college hoops candidates, before"))
            print(agg(a.get("ncaab", []), f"{day} college hoops candidates, now"))
        for lg in sorted(tb):
            print(agg(tb[lg], f"all days, {lg} candidates, before"))
            print(agg(ta[lg], f"all days, {lg} candidates, now"))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"dry_{what}.md"), "w").write("\n".join(out))
    print("\nPAGE CHECK CATCHES ON THE NEW CARDS:")
    seen = set()
    for n in NOTES:
        if n not in seen:
            seen.add(n)
            print("  ", n)
