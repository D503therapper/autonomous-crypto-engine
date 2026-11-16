"""11/16 FABLE - WHY WE LOSE: re-build a posted board from the repo snapshot that posted it, with one input changed.
Usage (cwd = a `git archive <posting commit>` snapshot dir, never the repo):
  python reboard.py 2026-11-15 base|qbfix|nokey [HH:MM PT]
base  = the snapshot's own code and data, that day's picks taken out (should re-post the real board)
qbfix = sports_players.QB_SETTLED_FROM opened ("0000"): a QB is known only when the same man started the last 2
nokey = no football key-player (QB form) edge at all (sm.KEY_EDGE emptied for nfl / ncaaf games)
Prints every pick the board would post + each football candidate's read."""
import copy, os, sys, tempfile, json
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
import sports, sports_data as sd, sports_players as sp, sports_model as sm  # noqa: E402

day_iso, mode = sys.argv[1], sys.argv[2]
hh, mm = (int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "8:03").split(":"))
day = datetime.strptime(day_iso, "%Y-%m-%d").date()
at = datetime(day.year, day.month, day.day, hh, mm, tzinfo=sports.PT).astimezone(timezone.utc)
for a in ("SLATE_PATH", "PICK_CHECK_PATH", "LEAN_SIDES_PATH", "LOCK_MISS_PATH"):
    if hasattr(sports, a):
        setattr(sports, a, os.path.join(tempfile.mkdtemp(), a.lower() + ".json"))
try:
    import sports_leads
    sports_leads.log = lambda *a, **k: None
    sports_leads.grade = lambda *a, **k: None
except Exception:  # noqa: BLE001
    pass
sports.announce_pick = lambda pk: None
sports.PRICE_CLOCK = datetime.now(timezone.utc) if os.environ.get("PRICE_NOW") else at   # (a same-day dry run: the real clock)
sports.HOLD_DAYS = set()
if mode == "regular":                        # the season's regular starter on the out list IS the starting QB out
    _old_so = sd.STARTER_OF                  # (Kyler Murray, 4 of the Vikings' 5 starts before Wentz's fill-in game, was
    sd.STARTER_OF = lambda lg, tid, name: True if name == "Kyler Murray" else _old_so(lg, tid, name)   # tagged a backup)
if mode in ("qbfix", "regular"):
    if hasattr(sp, "QB_SETTLED_FROM"):
        sp.QB_SETTLED_FROM = "0000"
    else:                                   # a snapshot from before the 11/15 night fix: the same rule, patched in

        def settled(rows, team, before, n=2):
            names, seen = [], set()
            for r in reversed(rows):
                if r["team"] == team and r["start"] < before and r.get("gid") not in seen:
                    seen.add(r.get("gid"))
                    names.append(r["player"])
                    if len(names) >= n:
                        break
            return None if (not names or len(set(names)) > 1) else names[0]
        old_ls = sp.last_starter
        sp.last_starter = lambda rows, team, before: (settled(rows, team, before) if rows and rows[0].get("role", "QB") == "QB"
                                                      and (rows[0].get("gid") or "")[:3] in ("nfl", "nca") else old_ls(rows, team, before))
INJ = {"nfl": {"Minnesota Vikings": [("Kyler Murray", "QB", "Out"), ("T.J. Hockenson", "TE", "Out")], "_": []},
       "nba": {"_": []}, "nhl": {"_": []}, "mlb": {"_": []}}
if os.path.exists("inj_stub.json"):
    INJ = json.load(open("inj_stub.json"))
sd.fetch_injuries = lambda lg: INJ.get(lg)          # (the reports aren't in the repo: the pros read 'nobody hurt' but
sports.slate_check = lambda *a, **k: []              #  the names the posted card carried; college = no report = no pick)
sports.factor_check = lambda *a, **k: []
sports.checker_selftest = lambda *a, **k: []
games = sd.load_games()
# the snapshot holds the games as they stood when the board posted; nothing later is in it
model = sports._load("model.json", {"params": {}, "log": []})
picks = [p for p in copy.deepcopy(sports.dedupe_picks(sports._load("picks.json", []))) if p["date"] != day_iso]
sp.CACHE = sp.load()
real_ke = sp.key_edges


def ke(gs, cache):
    out = real_ke(gs, cache)
    if mode == "nokey":
        out = {k: v for k, v in out.items() if not (k.startswith("nfl:") or k.startswith("ncaaf:"))}
    return out


sp.key_edges = ke
sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
sports.load_states(games)
new = sports.post_board(games, model, picks, at, day, force=False)
print(f"== {day_iso} {mode}: {len(new)} picks")
for pk in new:
    l = pk["legs"][0]
    print(f"  {pk['kind']:5s} {'*' if pk.get('best') else ' '} {l.get('league'):5s} {l.get('team'):18s} {l.get('market'):6s} {l.get('odds')} "
          f"u={sports.units_for(pk)} p={l.get('p') and round(l['p'], 3)} own={l.get('edge_own') is not None and round((l['edge_own'] + 1) / l['dec'], 3)} "
          f"raw={l.get('raw_own')} mkt={l.get('p_market') and round(l['p_market'], 3)} key={l.get('key_edge') and round(l['key_edge'], 2)} "
          f"floor={pk.get('floor')} tags={[k for k in ('gap', 'dog_play', 'nba_fav', 'ncaab_play', 'forced', 'backup_lock') if pk.get(k) or l.get(k)]} | {l.get('reasons')}")
print("-- football candidates")
for c in sports.LAST_RAW:
    if c.get("league") in ("nfl", "ncaaf") and c.get("market") == "ml" and -200 <= c.get("odds", 0) <= 350:
        own = c.get("edge_own") is not None and round((c["edge_own"] + 1) / c["dec"], 3)
        print(f"  {c['league']:5s} {c['team']:18s} {c['odds']:>5} p={c.get('p') and round(c['p'], 3)} own={own} raw={c.get('raw_own')} "
              f"mkt={c.get('p_market') and round(c['p_market'], 3)} key={c.get('key_edge') is not None and round(c['key_edge'], 2)} "
              f"good={sports.good(dict(c))} lock_ok={sports.lock_ok(c)} agrees={sports.own_agrees(c)} | {c.get('reasons')}")
