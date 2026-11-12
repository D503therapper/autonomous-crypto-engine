"""11/12 SWEEP (a) - THE PULL: the four open college early plays for Saturday 11/14 that fail today's rules come off
the way an early play is pulled (the 10/14, 10/17 and 10/30 pulls): the row moves from early.json's "picks" to its
"pulled" list with pulled_at / pulled_why - never graded, never deleted, out of every record; the dashboard reads
"picks" only; a pulled game can post again only through a fresh scan 12+ hours on (sports_early.repost_ok).
Steelers +150 (NFL bye) and Georgia St +170 (the exam band) pass and stay. Idempotent.
Usage: python results/studies/sweep_1112/e5_pull.py [--write]"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_early as se  # noqa: E402

HEAD = ("11/12 full sweep (the owner, 11/12: \"If we need to get rid of some early plays for Saturday ... that's what we "
        "need to do\"; 10/17: an early play a Fable audit says should come off gets pulled without asking): ")
WHY = {
    ("ncaaf:401858301", "SMU"): "posted on the BLOWOUT spot, paused 11/11 for games from 11/12 (held out -7.4% on 182, this season's "
                                "college dogs off a 17+ win 5-20, live 3-11). The money came 5 points to SMU (+110 -> -115) - the spot's "
                                "worst cell: college blowout dogs the money chased 2+ points by midweek went 7-24 (held out 2-20).",
    ("ncaaf:401862826", "FAU"): "posted on the BLOWOUT spot, paused 11/11 for games from 11/12, and the engine's main read fights it "
                                "(35.1% vs the 37.0% +170 needs - no early play under the 11/11 one-voice rule). The price ran away, +170 -> +180.",
    ("ncaaf:401862829", "UAB"): "the engine's main read fights it (45.1% vs the 48.8% +105 needs) - under the 11/11 one-voice rule it would "
                                "not post. The hammered spot bought after the move (+128 -> +105) and the price went back out to +114; "
                                "college spot dogs the main read fights ran -9.4% on 136.",
    ("ncaaf:401860915", "San Diego St"): "the engine's main read fights it (46.2% vs the 49.0% +104 needs) - under the 11/11 one-voice rule "
                                         "it would not post. The money left it, +104 -> +120 (3.2 points): college dogs the money ran 2+ from "
                                         "by midweek -21.3% on 82 held out; the college bye spot is -0.6% held out (2025: 1-10).",
}
AT = "2026-11-12T06:00Z"
st = se.load()
keep, n = [], 0
for p in st["picks"]:
    k = (p.get("game_id"), p.get("team"))
    if k in WHY and p.get("result") is None and p.get("market") != "total":
        st.setdefault("pulled", []).append({**p, "pulled_at": AT, "pulled_why": HEAD + WHY[k]})
        n += 1
        print(f"PULL  {p['team']} {p['odds']:+d} ({p.get('spot')}, {se.units(p)}u) - {WHY[k][:110]}...")
    else:
        keep.append(p)
st["picks"] = keep
print(f"{n} pulled; still open: " + ", ".join(f"{p['team']} {p['odds']:+d} ({p.get('spot') or 'exam'})" for p in keep if p.get("result") is None))
if "--write" in sys.argv and n:
    se.save(st)
    print("written")
