"""S11 - THE LIVE CODE, REPLAYED: sports_early.alt_over_1111 run game by game on every season's priced home games at
1,400 m+ (the game marked 'pre', the clock set to 6 PM PT the night before, ESPN's close standing in for the number),
graded at that close. It should land on S3's candidate cell (499-342, +13.1% on 848) - the proof the code posts the
rule the study tested. Plus today's two games from the brother's engine, at his numbers."""
import os
import sys
from datetime import datetime, timedelta, timezone

import lib

sys.path.insert(0, lib.ROOT)
os.chdir(lib.ROOT)
import sports_early as se  # noqa: E402

se.ALT_1111_FROM = "2000-01-01"                      # the rule on every season (the replay only)
G = {r["id"]: r for r in lib.load("ncaab", finals=False)}
bets = []
for r in list(G.values()):
    if r["status"] != "final" or (r.get("stype") or "2") != "2" or r["neu"] or (r["el"] or 0) < 1400 or r["tot"] is None:
        continue
    st = datetime.strptime(r["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    pt = st - timedelta(hours=8)
    now = datetime(pt.year, pt.month, pt.day, 2, 0, tzinfo=timezone.utc)          # 6 PM PST the day before
    g = dict(r, status="pre")
    c = se.alt_over_1111({**G, r["id"]: g}, g, {"picks": []}, now, {})
    if c:
        bets.append(r)
lib.line("the live code, replayed OVER", bets, "over")
print(f"   (S3's candidate cell: 499-342 +13.1% on 848)")

print("\n== TODAY'S TWO (the brother's engine's 11/11 plays), through the live code at his numbers")
se.ALT_GAME_DAY = True                               # (they tip today - the read and the limits, not the timing)
now = datetime(2026, 11, 11, 16, 0, tzinfo=timezone.utc)
for away, home, nums in (("Loyola Chicago", "Air Force", (154.5, 159.5)), ("Portland St", "Colorado St", (147.5,))):
    g0 = next((x for x in G.values() if x["home_name"] == home and x["away_name"] == away and x["start"][:10] in
               ("2026-11-11", "2026-11-12")), None)
    if not g0:
        print(f"   {away} @ {home}: not in the file")
        continue
    avs = {}
    for t in nums:
        g = dict(g0, status="pre", total=str(t), over_odds="-115")
        c = se.alt_over_1111({**G, g0["id"]: g}, g, {"picks": []}, now, avs)
        rd = se.alt_early_read(avs[2026], avs[2025], g) if 2026 in avs else None
        print(f"   {away} @ {home} ({g0['el'] * lib.FT:,.0f} ft) over {t:g}: points read "
              f"{'none' if rd is None else f'{rd:.1f}'} -> {'QUALIFIES' if c else 'no play'}"
              + (f" (the read's limit: no over past {rd + se.ALT_FIGHT:.1f})" if rd is not None else ""))
        if c:
            print("      why:", c["why"])
            for f in c["facts"]:
                print("      -", f)
    print(f"   our file's number for it at the last run: {g0.get('total') or 'none yet'} (status {g0['status']})")
