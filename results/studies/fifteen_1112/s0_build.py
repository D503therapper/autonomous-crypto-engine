"""Build / refresh the five league tables (lib.table) and print the base rates every study reads against."""
import sys, time
import lib as L

for lg in ("nba", "nhl", "nfl", "ncaaf", "ncaab"):
    t = time.time()
    rows = L.table(lg, fresh="fresh" in sys.argv)
    rg = [g for g in rows if L.reg(g)]
    print(f"\n{lg}: {len(rows)} finals ({len(rg)} regular season), {time.time() - t:.1f}s")
    L.cell(f"{lg} every over", [(g["season"], L.tot(g, "over")) for g in rg])
    L.cell(f"{lg} every under", [(g["season"], L.tot(g, "under")) for g in rg])
    L.cell(f"{lg} every home side ATS", [(g["season"], L.ats(g, "H")) for g in rg])
    L.cell(f"{lg} every away side ATS", [(g["season"], L.ats(g, "A")) for g in rg])
    fv = [(g, L.fav(g)) for g in rg if L.fav(g)]
    L.cell(f"{lg} favorite -151..-199 at the close", [(g["season"], L.ml(g, f)) for g, f in fv if -199 <= L.odds(g, f) <= -151])
    L.cell(f"{lg} favorite -101..-150 at the close", [(g["season"], L.ml(g, f)) for g, f in fv if -150 <= L.odds(g, f) <= -101])
L.done()
