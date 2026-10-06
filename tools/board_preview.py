"""👀 A DRY RUN of tomorrow's (or any day's) board, the way the 8 AM post would build it RIGHT NOW (the owner, 10/2:
"give me tomorrow's board ... make sure everything's working"). Nothing is saved: no picks, no slate check, no lead
tracker - it only writes results/board_preview.txt. Prices are whatever the books show at run time, so the real 8 AM
board can differ. Usage: python tools/board_preview.py [YYYY-MM-DD]"""
import copy
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_players as sp     # noqa: E402
import sports_model as sm       # noqa: E402

UNIT_KINDS = ("lock", "dog", "solo", "play", "night")


def main(day_iso=None):
    now_real = datetime.now(timezone.utc)
    day = datetime.strptime(day_iso, "%Y-%m-%d").date() if day_iso else (now_real.astimezone(sports.PT) + timedelta(days=1)).date()
    # 8:35 AM PT on that day (past the slate check's last try - the board always builds)
    at = datetime(day.year, day.month, day.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
    sports.SLATE_PATH = os.path.join(tempfile.mkdtemp(), "slate.json")          # nothing real gets written
    sports.LOCK_MISS_PATH = os.path.join(tempfile.mkdtemp(), "lock_miss.json")  # (10/5 sweep: the dry run wrote the real
    #                                              Lock near-miss - the question box would name a pick from a preview)
    try:
        import sports_leads
        sports_leads.log = lambda *a, **k: None
        sports_leads.grade = lambda *a, **k: None
    except Exception:                                                          # noqa: BLE001
        pass
    sports.announce_pick = lambda pk: None
    sports.HOLD_DAYS = set()                                                   # (a held board still previews)
    games = sd.load_games()
    model = sports._load("model.json", {"params": {}, "log": []})
    picks = copy.deepcopy(sports.dedupe_picks(sports._load("picks.json", [])))
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
    sports.load_states(games)
    out = [f"BOARD PREVIEW for {day} - built {now_real:%Y-%m-%d %H:%M} UTC at today's prices (a dry run: nothing posted)"]
    if sports.STATE_FAILS:
        out.append(f"!! states that failed to load: {sports.STATE_FAILS}")
    new = sports.post_board(games, model, picks, at, day, force=False)
    waiting = [p for p in picks if p["date"] == day.isoformat() and p["status"] == "waiting"]
    order = {"lock": 0, "dog": 1, "solo": 2, "night": 3, "play": 4, "lean": 5}
    units_tot = 0.0
    for pk in sorted(new, key=lambda p: (order.get(p["kind"], 9), -(p.get("p_hit") or 0))):
        leg = pk["legs"][0]
        u = sports.units_for(pk)
        units_tot += u
        size = "NO UNITS - LEAN" if pk.get("lean") else f"{u:g}u"
        label = sports.leg_label(leg)
        out.append(f"\n{pk['kind'].upper():5} {label} ({sports.fmt_american(leg['odds'])}) vs {leg.get('opp')} - "
                   f"{leg['league'].upper()} - {size} - win {leg.get('p', 0):.0%}, own read "
                   f"{(sports.read_of(leg) or 0):.0%}, edge {((leg.get('edge_own') or 0)):+.1%}"
                   + (" [THIN]" if sports.thin_edge(leg) else ""))
        for line in (leg.get("breakdown") or [])[-2:]:
            out.append(f"      {line}")
        if leg.get("why_line"):
            out.append(f"      why: {leg['why_line']}")
    if not new:
        out.append("\n(no picks would post right now)")
    for w in waiting:
        out.append(f"\nWAITING {w['kind']}: on {', '.join(w.get('waiting') or [])}")
    # 🐶 EVERY DOG on the slate (10/5, the owner: "there's no value in any dogs?") - the engine's read vs the price each
    # one needs, and what kept it off. Moneylines +100..+220.
    dogs = [c for c in sports.LAST_RAW if c.get("market") == "ml" and 100 <= c.get("odds", 0) <= sports.DAILY_DOG_MAX]
    if dogs:
        out.append("\nEVERY DOG (moneyline): price needs -> the engine's read")
        for c in sorted(dogs, key=lambda c: -((sports.read_of(c) or 0) - 1 / c["dec"])):
            need, rd = 1 / c["dec"], sports.read_of(c) or 0
            why = []
            if c.get("waiting"):
                why.append("waiting: " + ", ".join(c["waiting"])[:60])
            if c.get("trap"):
                why.append("trap")
            if c.get("hurt"):
                why.append("hurt: " + ", ".join(c["hurt"])[:50])
            if sports.fighting(c):
                why.append("own read under the price")
            try:
                why.append(f"dog score {sports.dog_score(c):+.1f}")
            except Exception:                                            # noqa: BLE001
                pass
            out.append(f"  {c['team']} +{c['odds']} vs {c.get('opp')} ({c['league'].upper()}) - needs {need:.1%}, "
                       f"read {rd:.1%} ({rd - need:+.1%})" + (f" - {'; '.join(why)}" if why else ""))
    unit_picks = [p for p in new if p["kind"] in UNIT_KINDS and not p.get("lean")]
    sizes = [sports.units_for(p) for p in unit_picks]
    out.append(f"\n{len(unit_picks)} unit plays, {sum(p.get('lean', False) for p in new)} leans - "
               f"{units_tot:g}u total; sizes {sorted(sizes, reverse=True)}")
    os.makedirs("results", exist_ok=True)
    txt = "\n".join(out)
    with open("results/board_preview.txt", "w") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
