"""11/13 FABLE - ARE THE COLLEGE HOOPS UNIT SLOTS SILENTLY BLOCKED? (the dog slot / the favorite slot / the 🔍 gap
play / the ½u spread stack play). Read-only: nothing is saved.
  1. how many college hoops teams have N regular-season games on file today (sports.season_games - what the gates read)
  2. the injury data: how many of the next days' teams the report covers (a team it doesn't cover gets no pick)
  3. every priced college hoops game of the next days through each slot's own checks, step by step - where sides fall out
  4. the schedule: the first day each gate (both teams 4+ games; 5 box games / 10 priced games for the stack) CAN open
Usage: python results/studies/leans_1113/s4_slots.py [first day YYYY-MM-DD] [days] > results/studies/leans_1113/s4_slots.out"""
import collections, os, sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.chdir(REPO)
sys.path.insert(0, REPO)
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402

NOINJ = os.environ.get("NOINJ")
day0 = datetime.strptime(sys.argv[1], "%Y-%m-%d").date() if len(sys.argv) > 1 else datetime.now(sports.PT).date()
ndays = int(sys.argv[2]) if len(sys.argv) > 2 else 5
sports.announce_pick = lambda pk: None
games = sd.load_games()
model = sports._load("model.json", {"params": {}, "log": []})
sp.CACHE = sp.load()
sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
sports.load_states(games)
print("states that failed to load:", sports.STATE_FAILS or "none")

# 1. games on file
nb = [g for g in games.values() if g.get("league") == "ncaab" and g.get("start", "") >= "2026-07-01"]
fin = [g for g in nb if g.get("status") == "final" and str(g.get("stype")) == "2"]
cnt = collections.Counter()
for g in fin:
    cnt[g["home"]] += 1
    cnt[g["away"]] += 1
try:
    d1 = sm.ncaab_d1([g for g in games.values() if g.get("league") == "ncaab" and g.get("status") == "final"])
except Exception as e:          # noqa: BLE001
    d1 = None
    print("d1 set failed:", str(e)[:80])
teams = [t for t in cnt if d1 is None or t in d1]
dist = collections.Counter(min(cnt[t], 6) for t in teams)
print(f"\n1. COLLEGE HOOPS GAMES ON FILE, this season: {len(fin)} finals, {len(teams)} D1 teams with a game (of {len(d1) if d1 else '?'} D1)")
print("   games played -> teams: " + "  ".join(f"{k}{'+' if k == 6 else ''}: {dist[k]}" for k in sorted(dist)))
print(f"   teams with 4+ games: {sum(v for k, v in dist.items() if k >= 4)}   with 5+: {sum(v for k, v in dist.items() if k >= 5)}")
last = max((g["start"] for g in fin), default="")
print(f"   the newest final on file: {last}")

# 4. the schedule ahead: the first day a game has BOTH teams 4+ games in (counting the games on the schedule file)
sched = collections.defaultdict(list)
for g in nb:
    if str(g.get("stype")) == "2":
        sched[g["home"]].append(g["start"])
        sched[g["away"]].append(g["start"])
for t in sched:
    sched[t].sort()
byday = collections.Counter()
allday = collections.Counter()
for g in nb:
    if str(g.get("stype")) != "2" or g.get("status") == "final":
        continue
    d = sports.pt_day(g)
    n = [sum(1 for s in sched[g[x]] if s < g["start"]) for x in ("home", "away")]
    allday[d] += 1
    if min(n) >= sports.NCAAB_DOG_READ_GAMES:
        byday[d] += 1
print("\n4. THE SCHEDULE AHEAD (games still to play on file; 'both 4+' counts every scheduled game before it as played):")
for d in sorted(allday)[:10]:
    print(f"   {d}: {allday[d]:3d} games on the schedule, {byday[d]:3d} with both teams 4+ games in")

# 2. the injury data
if NOINJ:
    injuries = None
    print("\n2. INJURY DATA: skipped (NOINJ) - every team read as covered")
else:
    injuries = {lg: sd.fetch_injuries(lg) for lg in ("ncaab",)}
    inj = injuries.get("ncaab")
    print(f"\n2. INJURY DATA (college hoops): {'DID NOT LOAD' if inj is None else str(len(inj)) + ' teams in the report'}")


def why_dog(c):
    if c.get("trap"):
        return "trap"
    if c.get("waiting"):
        return "waiting on news"
    if sports.fighting(c):
        return "own read fighting"
    if not (c.get("reasons") or sports.ncaab_play_fired(c)):
        return "no named reason"
    if sports.ncaab_dog_fade(c):
        return "a dog fade on it"
    if min(c.get("games_in") or 0, c.get("opp_games_in") or 0) < sports.NCAAB_DOG_READ_GAMES:
        return "a team under 4 games"
    r = c.get("dog_read") if c.get("dog_read") is not None else sports.ncaab_dog_read(c)
    if r is None:
        return "no dog read"
    if r < sports.NCAAB_DOG_READ_GATE:
        return "dog read under 4"
    if not (c.get("dog_read_parts") or {}).get("games_ok"):
        return "dog read: games not ok"
    return "PASSES" if sports.ncaab_play_dog(c) else "read under the price"


def why_fav(c):
    if c.get("trap"):
        return "trap"
    if c.get("waiting"):
        return "waiting on news"
    if sports.fighting(c):
        return "own read fighting"
    if not (c.get("reasons") or sports.ncaab_play_fired(c)):
        return "no named reason"
    if sports.ncaab_early_lock(c) == "none":
        return "a team under 3 games"
    if sports.ncaab_fav_fade(c):
        return "a favorite fade on it"
    if c.get("edge_own") is None or c["edge_own"] <= 0:
        return "own read under the price"
    return "PASSES" if sports.ncaab_play_fav(c) else "weighed read not 56%+ and 1-5 over"


print("\n3. THE SLOTS ON THE PRICED GAMES AHEAD (at the prices on file now)")
for i in range(ndays):
    day = day0 + timedelta(days=i)
    at = datetime(day.year, day.month, day.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
    try:
        raw = sports.candidates(games, model, at, day, injuries)
    except Exception as e:      # noqa: BLE001
        print(f"   {day}: candidates failed {str(e)[:120]}")
        continue
    nc = [c for c in raw if c.get("league") == "ncaab"]
    gids = {c["game_id"] for c in nc}
    blind = {c["game_id"] for c in nc if any("(not in our data)" in w for w in c.get("waiting") or [])}
    allc = [c for c in nc if c["game_id"] not in blind]
    cands = [c for c in allc if not c.get("hurt")]
    both4 = {c["game_id"] for c in nc if min(c.get("games_in") or 0, c.get("opp_games_in") or 0) >= 4}
    print(f"\n   {day}: {len(gids)} priced college hoops games; {len(blind)} off the table (a team not in the injury data); "
          f"{len({c['game_id'] for c in allc if c.get('hurt')})} with a side held 'hurt'; {len(both4)} with both teams 4+ games")
    dogs = [c for c in nc if c["market"] == "ml" and 100 <= c["odds"] <= 350]
    favs = [c for c in nc if c["market"] == "ml" and -150 <= c["odds"] <= -120]
    print(f"     dog slot: {len(dogs)} dogs +100..+350 -> " + ", ".join(f"{k}: {v}" for k, v in collections.Counter(
        ("not in the injury data" if c["game_id"] in blind else "hurt" if c.get("hurt") else why_dog(c)) for c in dogs).most_common()))
    print(f"     favorite slot: {len(favs)} favorites -120..-150 -> " + ", ".join(f"{k}: {v}" for k, v in collections.Counter(
        ("not in the injury data" if c["game_id"] in blind else "hurt" if c.get("hurt") else why_fav(c)) for c in favs).most_common()))
    eff = [c for c in dogs if c.get("eff_p") is not None]
    gap = [c for c in eff if c["eff_p"] - c["p_market"] >= sports.NCAAB_GAP_MIN]
    got = sports.gap_plays(cands, set())
    print(f"     gap play: {len(eff)} dogs with an efficiency read, {len(gap)} with a 15+ point gap, {len([c for c in got if c['league'] == 'ncaab'])} clear every gap check"
          + "".join(f"\n        {c['team']} {c['odds']:+d}: eff read {c['eff_p']:.0%} vs {c['p_market']:.0%}, games {c.get('games_in')}/{c.get('opp_games_in')}, backed {c['eff_p'] > .5}, spots {sports.dog_spots(c):+.1f}" for c in gap[:6]))
    sps = [c for c in nc if c["market"] == "spread"]
    st = [c for c in sps if c.get("spread_stack") is not None]
    big = [c for c in st if (c.get("spread_stack") or 0) >= sports.NCAAB_STACK_PLAY_MIN - 1e-9]
    stp = sports.ncaab_stack_plays(cands, set())
    print(f"     stack play: {len(sps)} spread sides, {len(st)} with any stack weight on, max {max([c['spread_stack'] for c in st], default=0):+.2f}, "
          f"{len(big)} at +0.05 or more, {len(stp)} clear every stack check")
    slot = sports.ncaab_play_plays(cands, set())
    for c in slot:
        print(f"     >>> SLOT PLAY: {c['team']} {c['odds']:+d} ({c.get('ncaab_slot')}) read {c.get('ncaab_read')}, score {c.get('ncaab_score')}")
    for c in [c for c in got if c['league'] == 'ncaab'] + stp:
        print(f"     >>> {'GAP' if c['market'] == 'ml' else 'STACK'} PLAY: {c['team']} {c['odds']:+d} {c.get('line') or ''}")
