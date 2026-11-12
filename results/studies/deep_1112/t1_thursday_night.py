"""11/12 DEEP PROGRAM - THE THURSDAY NIGHT PICK (Commanders @ Giants, 11/12 5:15 PM PT): will sports.night_games /
night_pick post once the Giants' QB (J.J. McCarthy, questionable) settles, and is its card right? A dry run of the real
board builder (tools/board_preview.main - nothing saved) with the NFL injury report set by hand, four ways:
  A  9:00 AM PT, McCarthy QUESTIONABLE      -> expect: no night pick yet (waiting on him)
  B  2:20 PM PT, McCarthy still QUESTIONABLE -> expect: the pick posts (the 3-hours-before-kickoff deadline)
  C  9:00 AM PT, McCarthy OUT                -> expect: the pick posts, the card names him
  D  9:00 AM PT, McCarthy off the report     -> expect: the pick posts
(No network in the study box: every other league's report is empty-but-loaded, so only the NFL game is judged.)
Usage: python results/studies/deep_1112/t1_thursday_night.py > results/studies/deep_1112/t1_thursday_night.out"""
import io, os, shutil, sys, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import board_preview as bp      # noqa: E402

GID = "nfl:401873052"


def run(tag, clock, mccarthy):
    rows = [] if mccarthy is None else [("J.J. McCarthy", "QB", mccarthy)]
    nfl = {"19": rows, "Giants": rows, "28": [], "Commanders": []}
    for g in sd.load_games("nfl").values():           # every other NFL team: on the report, nobody listed
        for s in ("home", "away"):
            nfl.setdefault(str(g[s]), [])
            nfl.setdefault(g[s + "_name"], [])
    sd.fetch_injuries = lambda lg: nfl if lg == "nfl" else None
    keep = "results/board_preview.txt"
    shutil.copy(keep, keep + ".keep")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            bp.main(f"2026-11-12T{clock}")
    finally:
        shutil.move(keep + ".keep", keep)
    txt = buf.getvalue()
    print("=" * 100)
    print(f"{tag}: {clock} PT, McCarthy {mccarthy or 'not on the report'}")
    night = [c for c in sports.LAST_RAW if c["game_id"] == GID]
    for c in night:
        print(f"   candidate {c['team']:10s} {c['market']:6s} {c.get('line')} {c['odds']:+d}: win {c['p']:.3f} own {(c['edge_own'] + 1) / c['dec'] if c.get('edge_own') is not None else float('nan'):.3f} "
              f"market {c.get('p_market'):.3f} waiting {c.get('waiting')} key_out_me {c.get('key_out_me')} hurt {c.get('hurt')} fighting {sports.fighting(c)}")
    keepl = False
    for ln in txt.splitlines():
        if ln.startswith("NIGHT") or "night" in ln.lower() and ("Giants" in ln or "Commanders" in ln) or "Monday/Thursday" in ln:
            keepl = True
        elif keepl and not ln.startswith("      "):
            keepl = False
        if keepl or ("WAITING" in ln and "night" in ln):
            print("   | " + ln[:700])
    if "NIGHT" not in txt:
        print("   -> NO NIGHT CARD in this run")
    return txt


for tag, clock, st in (("A", "09:00", "Questionable"), ("B", "14:20", "Questionable"), ("C", "09:00", "Out"), ("D", "09:00", None)):
    t = run(tag, clock, st)
    open(os.path.join(os.path.expanduser("~"), ".cache", f"tnf_{tag}.txt"), "w").write(t)
