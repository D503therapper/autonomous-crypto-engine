"""S5 - THE PUBLIC IN A THIN MARKET: do lopsided public splits in college hoops push lines too far, more so in the
low-major games (small handle -> a few public tickets move the number)?
Data: data/sports/public.json (Action Network's final pre-tip ticket % / money %, college hoops 2024-26 - check the
seasons below), ESPN/AN's ML open + close. The splits are the FINAL snapshot, so only the CLOSE is bettable on them
(the 10/7 study: every split signal loses at the close across sports, college hoops money-over-tickets -26%).
New here: by TIER, and the spread market. Honest about sample: two seasons."""
from collections import Counter

import lib

out = lib.Out("s5_public", train=(2024,), held=(2025,))
S = [x for x in lib.nc_sides() if x["stype"] == "2" and x.get("pub_t") is not None]
out.note("sides with splits by season: " + str(sorted(Counter(x["season"] for x in S).items())))
for x in S:
    x["gt"] = "P" if "power" in (x["tier"], x["otier"]) else ("M" if "mid" in (x["tier"], x["otier"]) else "L")
out.h("ML: the side with 75%+ of the TICKETS - did the line move to it (open->close), and betting it / fading it at the close")
for t in ("P", "M", "L", "all"):
    pub = [x for x in S if (x["gt"] == t or t == "all") and x["pub_t"] >= 75 and x.get("po") is not None and x.get("ml")]
    if not pub:
        continue
    mv = sum(x["p"] - x["po"] for x in pub) / len(pub) * 100
    out.note(f"tier {t}: {len(pub)} public sides, mean move TO the public side {mv:+.2f} pts")
    out.bets(f"  tier {t} public side at CLOSE", [(x["season"], lib.ml_pl(x["ml"], x["won"])) for x in pub])
    out.bets(f"  tier {t} public side at OPEN (hindsight-free? no - splits are final)", [(x["season"], lib.ml_pl(x["mlo"], x["won"])) for x in pub])
    out.bets(f"  tier {t} FADE the public at CLOSE", [(x["season"], lib.ml_pl(x["oml"], not x["won"])) for x in pub])
    big = [x for x in pub if x["p"] - x["po"] >= 0.03]
    out.bets(f"  tier {t} public AND line moved 3+ to it: FADE at close", [(x["season"], lib.ml_pl(x["oml"], not x["won"])) for x in big])
out.h("SPREAD: the side with 75%+ of the spread tickets - cover rate at the close, by tier")
for t in ("P", "M", "L", "all"):
    pub = [x for x in S if (x["gt"] == t or t == "all") and (x.get("pub_sp_t") or 0) >= 75 and x.get("sp") is not None]
    out.bets(f"tier {t} public spread side", [(x["season"], lib.ats_pl(x["margin"] + x["sp"], x["spodds"])) for x in pub])
    out.bets(f"tier {t} FADE public spread side", [(x["season"], lib.ats_pl(-(x["margin"] + x["sp"]), -110)) for x in pub])
out.h("TOTALS: 75%+ of tickets on the over - the under at the close, by tier")
G = [x for x in S if x["side"] == "home" and x.get("total") and x.get("pub_over_t") is not None]
for t in ("P", "M", "L", "all"):
    sel = [x for x in G if (x["gt"] == t or t == "all") and x["pub_over_t"] >= 75]
    out.bets(f"tier {t} public OVER -> bet the UNDER", [(x["season"], lib.ats_pl(x["total"] - x["pts"], x["under_odds"])) for x in sel])
    sel = [x for x in G if (x["gt"] == t or t == "all") and x["pub_over_t"] <= 25]
    out.bets(f"tier {t} public UNDER -> bet the OVER", [(x["season"], lib.ats_pl(x["pts"] - x["total"], x["over_odds"])) for x in sel])
out.save()
