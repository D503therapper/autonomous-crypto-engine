"""The 11/24 dry run (README.md next to this file): every unit card posted since SINCE - as it posted, and re-written
now as the page shows it - with the matchup edges the case builder ranked for it (sports_card_sell.case_edges) and the
counts: cards with a moral-victory line, cards whose line under the pick is a matchup edge, cards with no edge at all.
No network (the injury lists are the ones each posted card stored); nothing is saved but dry.md next to this file.
    python results/studies/cards_1124/dry.py [league]"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.getcwd())
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cards_1122"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cards_1123"))
import h                                                    # noqa: E402
from h import games, picks, elo, v24, cc                    # noqa: E402
import dry as d23                                           # noqa: E402
import sports                                               # noqa: E402
import sports_card_sell as cs                               # noqa: E402

SINCE = "2026-11-17"
v24.SELL_FROM = "2026-11-01"                               # (the older cards re-written by today's writer)
only = sys.argv[1] if len(sys.argv) > 1 else None


def edges(leg):
    g = games[leg["game_id"]]
    lg = leg["league"]
    if lg not in cs.CASE_BASE:
        return None
    side = leg["side"]
    tid, oid = g[side], g["away" if side == "home" else "home"]
    start = v24._t(g["start"])
    fin = [x for x in h.sm.finals(games, lg) if v24._t(x["start"]) < start]
    if lg == "ncaab":
        v24._d1_set(fin)
    gu = v24._real(v24._season(v24._team_games(fin, tid), start), tid, lg)
    gt = v24._real(v24._season(v24._team_games(fin, oid), start), oid, lg)
    e = elo.get(lg)
    fair = lg not in v24.SCHEDULE_FAIR or cs.fair_cmp(gu, gt, tid, oid, e)
    note = ""
    if not fair:
        keep, left = cs.fair_trim(lg, gu, gt, tid, oid, e)
        if not keep:
            return "their schedule clearly tougher and it can't be made level - no side-by-side numbers"
        gt, note = keep, cs.trim_note(left)
    pu, pt = cs.profile(lg, gu, tid), cs.profile(lg, gt, oid)
    if not pu or not pt:
        return "not enough box scores"
    return [(k, sz, ways[0] + note) for k, sz, ways in cs.case_edges(lg, leg["team"], leg["opp"], pu, pt, "d1" if lg == "ncaab" else "")]


out, rows = [], []
for pk in picks:
    if pk["date"] < SINCE or pk.get("lean") or pk.get("kind") == "lean":
        continue
    for leg in pk["legs"]:
        if leg["game_id"] not in games or leg.get("market") not in ("ml", "spread") or (only and leg["league"] != only):
            continue
        posted_why, posted = leg.get("why_line") or "", list(leg.get("breakdown") or [])
        with contextlib.redirect_stdout(io.StringIO()):
            sports.sync_sides([leg], games, "dry run")
            new = h.rewrite(leg, set())
            new.pop("bv", None)
        why, lines = d23.page({**pk, "legs": [new]}, new)
        try:
            ed = edges(new)
        except Exception as ex:                             # noqa: BLE001
            ed = f"error {ex!r}"
        body = [x for x in lines if isinstance(x, str) and not cc.BOTTOM.match(x)]
        r = {"moral_before": any(cs.moral(x) for x in [posted_why] + posted),
             "moral_now": any(cs.moral(x) for x in [why] + lines),
             "edges": len(ed) if isinstance(ed, list) else None,
             "lead_edge": isinstance(ed, list) and bool(ed) and any(cs.sig(w) == cs.sig(why.split(": ", 1)[-1]) or
                                                                    cs.stat_of(why) == cs.stat_of(e_[2]) for e_ in ed for w in [e_[2]]),
             "facts": len(body) + (1 if why else 0), "lg": leg["league"]}
        rows.append(r)
        out.append(f"\n### {pk['date']} {leg['league']} - {leg['team']} {leg.get('odds'):+} vs {leg['opp']} ({pk['kind']})\n")
        out.append("the reasons the leg carries: " + "; ".join(str(x)[:120] for x in leg.get("reasons") or []) + "\n")
        if isinstance(ed, list):
            out.append("the matchup edges, ranked (size in spreads): " + ("; ".join(f"{k} {sz}" for k, sz, _ in ed) or "NONE - no real matchup edge on file") + "\n")
        elif ed:
            out.append(f"the matchup edges: {ed}\n")
        out.append(f"As it posted:\n\n```\n{d23.fmt(posted_why, posted)}\n```\n")
        out.append(f"Now, on the page ({r['facts']} fact lines):\n\n```\n{d23.fmt(why, lines)}\n```\n")

hoops = [r for r in rows if r["edges"] is not None]
head = [f"# The 11/24 dry run - unit cards posted since {SINCE}" + (f" ({only})" if only else ""), "",
        f"- cards: {len(rows)}",
        f"- cards with a moral-victory line, as posted: {sum(r['moral_before'] for r in rows)}; now: {sum(r['moral_now'] for r in rows)}",
        f"- basketball cards the case builder could read: {len(hoops)}; with at least one ranked matchup edge: {sum(1 for r in hoops if r['edges'])}; "
        f"with none (the card stays shorter): {sum(1 for r in hoops if not r['edges'])}",
        f"- of the cards with an edge, the line under the pick is a matchup edge: {sum(1 for r in hoops if r['edges'] and r['lead_edge'])}",
        f"- fact lines a card now: {sum(r['facts'] for r in rows) / max(1, len(rows)):.1f}", ""]
open(os.path.join(HERE, "dry.md"), "w").write("\n".join(head + out))
print("\n".join(head))
