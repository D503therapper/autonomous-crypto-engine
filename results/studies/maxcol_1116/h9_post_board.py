"""H52 - THE MAX PLAY END TO END: the REAL sports.post_board (the slate check, the injury hold, the no-thin-Lock rule,
the pre-post pick check, the card check - everything the 8 AM run does) on past college hoops days where the replay
had a qualifying favorite, on today's code with every date gate open (leans_1113/funnel4.py). Does the max play
save, at its units, with its card - and does the Lock spot still say no Lock on a thin edge? Nothing real is written
(every path post_board writes goes to a temp folder); the injury report is a stub (no report exists for a past day).
Usage: python results/studies/maxcol_1116/h9_post_board.py 2026-01-01 2026-01-10 2026-02-19 2026-02-21"""
import copy, os, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "leans_1113"))
import funnel4 as F             # noqa: E402  (sets the cwd, the params cache, every date gate open)
sports, sd, sp, vpr = F.sports, F.sd, F.sp, F.vpr

tmp = tempfile.mkdtemp()
for name in ("SLATE_PATH", "PICK_CHECK_PATH", "LEAN_SIDES_PATH", "LOCK_MISS_PATH"):
    setattr(sports, name, os.path.join(tmp, name.lower() + ".json"))
try:
    import sports_leads
    sports_leads.log = lambda *a, **k: None
    sports_leads.grade = lambda *a, **k: None
except Exception:               # noqa: BLE001
    pass
sports.announce_pick = lambda pk: None
sports.HOLD_DAYS = set()


class Everyone(dict):
    """An injury report that lists every team with nobody out."""
    def __contains__(self, k):
        return True

    def get(self, k, d=None):
        return []

    def __getitem__(self, k):
        return []


sd.fetch_injuries = lambda lg: Everyone()
days = [datetime.strptime(a, "%Y-%m-%d").date() for a in sys.argv[1:]]
games = sd.load_games()
rp = F.Funnel(games, sp.load())
for day in sorted(d for d in rp.by_day if d < min(days)):
    for g in rp.by_day[day]:
        rp.hist[g["id"]] = g
d = min(days)
while d <= max(days):
    if d not in days:
        rp.feed(d)
        d = d.fromordinal(d.toordinal() + 1)
        continue
    tune_at = datetime.strptime(f"{d.year if d.strftime('%m-%d') >= vpr.TUNE_MONTH_DAY else d.year - 1}-{vpr.TUNE_MONTH_DAY}", "%Y-%m-%d").date()
    if rp.tuned_before != tune_at:
        rp.tune(tune_at)
    now = datetime(d.year, d.month, d.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
    snap = dict(rp.hist)
    for g in rp.by_day.get(d, []):
        c = copy.copy(g)
        c["status"], c["home_score"], c["away_score"] = "pre", "", ""
        c["inj_home"], c["inj_away"] = "", ""
        c["odds_time"] = now.strftime("%Y-%m-%dT%H:%MZ")
        snap[g["id"]] = c
    rp.states(snap, now)
    sports.PRICE_CLOCK = now
    cands = [c for c in sports.candidates(snap, rp.model, now, d, None) if not c.get("hurt")]
    want = {"max": [f"{c['team']} {c['odds']:+d} (weighed {c['w_p']:.3f}, needs {1 / c['dec']:.3f})" for c in sports.max_plays(cands, set())]}
    import io, contextlib
    buf = io.StringIO()
    picks = []
    try:
        with contextlib.redirect_stdout(buf):
            new = sports.post_board(snap, rp.model, picks, now, d, force=False)
    except Exception as e:      # noqa: BLE001
        print(f"{d}: post_board FAILED {type(e).__name__}: {str(e)[:200]}")
        new = []
    print(f"\n{d}: the rules pick -> {want or 'nothing'}")
    for ln in buf.getvalue().splitlines():
        if "thin-edge Lock" in ln or "max play" in ln or "RULE CHECK" in ln:
            print("   log:", ln.strip()[:200])
    for p in new:
        l = p["legs"][0]
        if l.get("league") != "ncaab" or p.get("lean"):
            continue
        print(f"   POSTED {p['kind']:5s} {'MAX PLAY' if p.get('max_play') else sports.posted_kind(p):12s} {l.get('team')} {l['odds']:+d} - {sports.units_for(p):g}u")
        if p.get("max_play"):
            for x in l.get("breakdown") or []:
                print("        ", str(x)[:230])
            import re
            import sports_dashboard as sdb
            card = sdb._pick_card("play", p)
            txt = re.sub(r"<[^>]+>", " ", card)
            print("      card:", " ".join(txt.split())[:420])
    for r in sports.LAST_PICK_CHECK or []:
        if r.get("held"):
            print(f"   HELD by the pre-post check: {r['kind']} {r['team']} {r['odds']} - {r['why']}")
    for p in picks:
        if p.get("status") == "waiting":
            print(f"   WAITING {p['kind']}: {p.get('waiting')}")
    rp.feed(d)
    d = d.fromordinal(d.toordinal() + 1)
