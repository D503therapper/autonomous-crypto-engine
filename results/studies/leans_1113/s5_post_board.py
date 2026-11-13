"""11/13 FABLE - THE SLOT CHECK, END TO END: the REAL sports.post_board (the slate check, the injury hold, the pre-post
pick check - everything the 8 AM run does) on past college hoops days where the replay's slot logic fired, on today's
code (every date gate open - funnel4.py). If a college hoops unit play (the dog slot / the favorite slot / the 🔍 gap
play / the ½u spread stack play) clears its own rule but the board never saves it, something past the rule is
blocking it. Nothing real is written (every path post_board writes goes to a temp folder); the injury report is a stub
that covers every team with nobody out (no report exists for a past day).
Usage: python results/studies/leans_1113/s5_post_board.py 2025-11-22 2025-11-25 ... > results/studies/leans_1113/s5_post_board.out"""
import copy, os, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
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
    # what the slot rules themselves pick (the replay's way)
    cands = [c for c in sports.candidates(snap, rp.model, now, d, None) if not c.get("hurt")]
    want = {}
    for kind, got in (("gap", [c for c in sports.gap_plays(cands, set()) if c["league"] == "ncaab"]),
                      ("slot", sports.ncaab_play_plays(cands, set())),
                      ("stack", sports.ncaab_stack_plays(cands, set())[:sports.NCAAB_STACK_PLAY_MAX_DAY])):
        for c in got:
            want.setdefault(kind, []).append(f"{c['team']} {c['odds']:+d}" + (f" {c['line']:+g}" if c.get("line") is not None else ""))
    picks = []
    try:
        new = sports.post_board(snap, rp.model, picks, now, d, force=False)
    except Exception as e:      # noqa: BLE001
        print(f"{d}: post_board FAILED {type(e).__name__}: {str(e)[:200]}")
        new = []
    print(f"\n{d}: the rules pick -> {want or 'nothing'}")
    nb = [p for p in new if any(l.get("league") == "ncaab" for l in p["legs"])]
    for p in nb:
        l = p["legs"][0]
        tag = "gap" if p.get("gap") is not None else p.get("tag") or p.get("slot") or ""
        print(f"   POSTED {p['kind']:5s} {tag:12s} {l.get('team')} {l['odds']:+d}" + (f" {l['line']:+g}" if l.get("line") is not None else "")
              + f" - {'lean, no units' if p.get('lean') else str(sports.units_for(p)) + 'u'}"
              + "".join(f" [{k}]" for k in ("cbb_test", "stack_play", "ncaab_slot", "floor", "dog_play") if p.get(k) or l.get(k)))
    for r in sports.LAST_PICK_CHECK or []:
        if r.get("held"):
            print(f"   HELD by the pre-post check: {r['kind']} {r['team']} {r['odds']} - {r['why']}")
    for p in picks:
        if p.get("status") == "waiting":
            print(f"   WAITING {p['kind']}: {p.get('waiting')}")
    rp.feed(d)
    d = d.fromordinal(d.toordinal() + 1)
