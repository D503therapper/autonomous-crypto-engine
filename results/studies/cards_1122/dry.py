"""The 11/22 dry run (results/studies/cards_1122/README.md): (a) every card posted since SINCE - as it posted, re-written by
yesterday's writer (the sell layer off) and re-written now, each as the page shows it; (b) every candidate moneyline
side -150..+350 for the days given, before / now. Counts: fact lines a card, same-stat repeats, reason-backed lines,
matchup lines, filler. No network (the injury lists are the ones each posted card stored); nothing is saved but
dry_posted.md / dry_cand.md next to this file. Run from the repo root:
    python results/studies/cards_1122/dry.py posted
    python results/studies/cards_1122/dry.py cand 2026-11-22 2026-11-23 2026-11-24"""
import sys, os, json, copy, re, time, io, contextlib
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(__file__))
from datetime import datetime, timezone, timedelta
import h
from h import games, elo, picks, model, sm, sd, sports, sports_breakdown, v24, cc
import sports_card_sell as cs
import sports_dashboard as dash
import sports_card_guard

SINCE = "2026-11-08"
dash._GAMES_[0] = games
NOTES = []
NOTE_ON = [False]
cc.note = lambda day, leg, why, line, where: NOTES.append((leg.get("team"), why, str(line)[:160])) if NOTE_ON[0] else None


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
    reps = len(cs.dedupe(body, us, them, why)[1])
    kinds = [cs.reason_backed(x, leg) for x in allf]
    fill = sum(1 for x in body if cc.filler(x, leg)) + (1 if why and cc.weak_lead(why, leg) else 0)
    return {"facts": len(allf), "repeats": reps, "reason": kinds.count("reason"), "matchup": kinds.count("matchup"),
            "filler": fill, "why_kind": kinds[0] if why else "none"}


def fmt(why, lines):
    return "\n".join(["WHY: " + (why or "(none)")] + ["  " + str(x) for x in lines])


def agg(rows, label):
    n = len(rows)
    if not n:
        return f"| {label} | 0 | | | | | | |"
    s = lambda k: sum(r[k] for r in rows)
    return (f"| {label} | {n} | {s('facts') / n:.1f} | {sum(1 for r in rows if r['facts'] < 6)} | {s('repeats')} | "
            f"{s('reason')} ({sum(1 for r in rows if r['reason'])} cards) | {s('reason') + s('matchup')} ({sum(1 for r in rows if r['reason'] + r['matchup'])} cards) | "
            f"{sum(1 for r in rows if r['why_kind'] in ('reason', 'matchup'))} | {s('filler')} |")


def posted(out):
    B, A, AP, O = [], [], [], []
    used, used_o = set(), set()
    for pk in picks:
        if pk["date"] < SINCE:
            continue
        for leg in pk["legs"]:
            if leg["game_id"] not in games:
                continue
            b = score(leg, leg.get("why_line") or "", leg.get("breakdown") or [])
            buf = io.StringIO()
            cs.SELL, v24.SELL_FROM = False, "9999"
            with contextlib.redirect_stdout(buf):
                old = h.rewrite(leg, used_o)
            ow, ol = page({**pk, "legs": [old]}, old)
            o = score(old, ow, ol)
            cs.SELL, v24.SELL_FROM = True, "2026-11-01"
            with contextlib.redirect_stdout(buf):
                new = h.rewrite(leg, used)
            a = score(new, new.get("why_line") or "", new.get("breakdown") or [])
            NOTE_ON[0] = True
            pw, pl = page({**pk, "legs": [new]}, new)
            NOTE_ON[0] = False
            ap = score(new, pw, pl)
            B.append(b); A.append(a); AP.append(ap); O.append(o)
            out.append(f"\nYesterday's writer, on the page ({o['facts']} fact lines, {o['repeats']} repeats, {o['reason']} reason-backed, {o['matchup']} matchup):\n\n```\n{fmt(ow, ol)}\n```\n")
            u = sports.units_for(pk) if hasattr(sports, "units_for") else ""
            out.append(f"\n### {pk['date']} {leg['league']} - {leg['team']} {leg.get('odds'):+} vs {leg['opp']} ({pk['kind']}, {u}u)\n")
            out.append(f"Before ({b['facts']} fact lines, {b['repeats']} repeats, {b['reason']} reason-backed, {b['matchup']} matchup):\n\n```\n{fmt(leg.get('why_line'), leg.get('breakdown') or [])}\n```\n")
            out.append(f"After, on the page ({ap['facts']} fact lines, {ap['repeats']} repeats, {ap['reason']} reason-backed, {ap['matchup']} matchup):\n\n```\n{fmt(pw, pl)}\n```\n")
            if (pw, pl) != (new.get("why_line") or "", new.get("breakdown") or []):
                cut = [x for x in new.get("breakdown") or [] if x not in pl]
                if cut or pw != (new.get("why_line") or ""):
                    out.append("(the page's check changed the write-up: " + " / ".join(["why: " + str(new.get('why_line'))] * (pw != (new.get('why_line') or '')) + cut) + ")\n")
    return B, A, AP, O


def cands(day, out):
    d = datetime.strptime(day, "%Y-%m-%d").date()
    at = datetime(d.year, d.month, d.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
    if day == "2026-11-22":
        at = datetime(2026, 11, 22, 0, 5, tzinfo=sports.PT).astimezone(timezone.utc)
    rows_b, rows_a = [], []
    try:
        cs_ = sports.candidates(games, model, now=at, day=d, injuries={lg: {} for lg in sd.LEAGUES})
    except Exception as e:                                   # noqa: BLE001
        print("cand err", repr(e), file=sys.stderr)
        return rows_b, rows_a
    used_a, used_b = set(), set()
    n = 0
    for c in cs_:
        if c.get("market") != "ml" or not (-150 <= (c.get("odds") or 0) <= 350):
            continue
        g = games[c["game_id"]]
        for sell, rows, used in ((False, rows_b, used_b), (True, rows_a, used_a)):
            leg = copy.deepcopy(c)
            leg.setdefault("tier", "value")
            cs.SELL = sell
            v24.SELL_FROM = "2026-11-22" if sell else "9999"
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, {leg["league"]: {}}, used)
                    sports.card_extras(leg, g, {leg["league"]: {}})
            except Exception as e:                           # noqa: BLE001
                print("bd err", c.get("team"), repr(e), file=sys.stderr)
                continue
            pk = {"date": day, "kind": "play", "legs": [leg], "lean": False, "tier": "value", "status": "open", "american": leg.get("odds")}
            pw, pl = page(pk, leg)
            rows.append(score(leg, pw, pl))
            if sell and n < 400:
                out.append(f"\n#### {day} {leg['league']} - {leg['team']} {leg.get('odds'):+} vs {leg['opp']}\n\n```\n{fmt(pw, pl)}\n```\n")
        n += 1
    cs.SELL = True
    v24.SELL_FROM = "2026-11-22"
    return rows_b, rows_a


if __name__ == "__main__":
    what = sys.argv[1]
    out = []
    if what == "posted":
        B, A, AP, O = posted(out)
        print("| what | cards | fact lines a card | cards under 6 | same-stat repeats | reason-backed lines | lines that say why (reason + matchup) | line under the pick says why | filler |")
        print("|---|---|---|---|---|---|---|---|---|")
        print(agg(B, f"posted {SINCE}..11/22, as written"))
        print(agg(O, "the same cards, re-written by yesterday's writer (v82), on the page"))
        print(agg(A, "the same cards, re-written now"))
        print(agg(AP, "re-written, as the page shows them"))
    else:
        tb, ta = [], []
        for day in sys.argv[2:]:
            b, a = cands(day, out)
            print(agg(b, f"{day} candidates, before"))
            print(agg(a, f"{day} candidates, now"))
            tb += b; ta += a
        print(agg(tb, "all candidates, before"))
        print(agg(ta, "all candidates, now"))
    open(os.path.join(os.path.dirname(__file__), f"dry_{what}.md"), "w").write("\n".join(out))
    print("\nPAGE CHECK CATCHES ON THE NEW CARDS:")
    for n in NOTES:
        print("  ", n)
