"""🚑 THE INJURY REPORT, read back plainly (the owner, 10/2: "we need to check all the players for this slate who's out
- and are these players stars, a factor?"). For every game on a day's slate: each team's FULL list from ESPN (every
player, position, status), whether he's a key position the engine weighs (QB / goalie / MLB star bat), and whether our
box scores show him starting. Also how many teams the feed covers at all - "nobody listed" is only "nobody hurt" when
the feed actually covers that team. Writes results/injury_report.txt. Read only - never touches a pick.
Usage: python tools/injury_report.py [YYYY-MM-DD] (blank = today Pacific)"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_players as sp     # noqa: E402


def main(day_iso=None):
    day = day_iso or datetime.now(timezone.utc).astimezone(sports.PT).date().isoformat()
    games = sd.load_games()
    sp.CACHE = sp.load()
    slate = [g for g in games.values() if g.get("status") == "pre" and g.get("start") and str(g.get("ml_home", "")) != ""
             and datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
             .astimezone(sports.PT).date().isoformat() == day]
    out = [f"INJURY REPORT for {day} - pulled {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC ({len(slate)} priced games)"]
    for lg in sorted({g["league"] for g in slate}):
        inj = sd.fetch_injuries(lg)
        teams = len({k for k in (inj or {}) if k.isdigit()}) if inj else 0
        out.append(f"\n===== {lg.upper()} - the feed lists {teams} teams" + ("" if inj else " (DIDN'T LOAD)"))
        for g in sorted((g for g in slate if g["league"] == lg), key=lambda g: g["start"]):
            out.append(f"\n{g['away_name']} @ {g['home_name']} ({g['start'][11:16]} UTC)")
            for side in ("away", "home"):
                rows = sd._team_rows(inj, g[side], g[side + "_name"])
                if not rows:
                    out.append(f"   {g[side + '_name']}: NOT IN THE FEED (no list at all - unknown, not 'healthy')"
                               if inj and g[side] not in inj else f"   {g[side + '_name']}: nobody listed")
                    continue
                out.append(f"   {g[side + '_name']}: {len(rows)} listed")
                for r in rows:
                    key = sd._is_key(r, lg, g[side + "_name"])
                    st = sd.STARTER_OF(lg, g[side], r[0]) if (key and sd.STARTER_OF) else None
                    tag = ("KEY - verified starter" if st else "KEY - backup (box scores)" if st is False
                           else "KEY - starter unknown" if key else "")
                    out.append(f"      {r[0]} ({r[1] or '?'}) - {r[2]}" + (f"  [{tag}]" if tag else ""))
    txt = "\n".join(out)
    os.makedirs("results", exist_ok=True)
    with open("results/injury_report.txt", "w") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
