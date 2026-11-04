"""11/4 FABLE - PLAYS EVERY DAY: an OFFLINE re-run of a past board day through the real post_board, on the real files -
the day's games set back to 'pre' at the 16:00Z (8 AM PT board-hour) price from data/sports/line_history, every later
game dropped, the day's picks removed (an opening board); no network (ESPN's injury feed is stubbed: the official reports
on disk for the day + a 'healthy' pro feed - so the hurt / waiting blocks on pro sides can't be reproduced here - and
nothing is written: slate_check / lock_miss / lean_sides / lead tracker all go to a temp dir).
Then EVERY NHL and NBA moneyline side is dumped with the exact checks that keep it off the board.
Usage: python dryrun.py <repo> <YYYY-MM-DD> [--all-leagues]"""
import copy
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

REPO = sys.argv[1]
DAY = sys.argv[2]
os.chdir(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_players as sp     # noqa: E402
import sports_model as sm       # noqa: E402

TMP = tempfile.mkdtemp()
sports.SLATE_PATH = os.path.join(TMP, "slate.json")
sports.LOCK_MISS_PATH = os.path.join(TMP, "lock_miss.json")
sports.LEAN_SIDES_PATH = os.path.join(TMP, "lean_sides.json")
try:
    import sports_leads
    sports_leads.log = lambda *a, **k: None
    sports_leads.grade = lambda *a, **k: None
except Exception:                                            # noqa: BLE001
    pass
sports.announce_pick = lambda pk: None
sports.HOLD_DAYS = set()

day = datetime.strptime(DAY, "%Y-%m-%d").date()
iso = day.isoformat()
at = datetime(day.year, day.month, day.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
BOARD_T = f"{iso}T16:00Z"


def real_official(league):
    try:
        return sd.official(league, day=iso)
    except TypeError:
        return sd.official(league)
    except Exception as e:                                   # noqa: BLE001
        print(f"official({league}) failed: {str(e)[:80]}")
        return {}


def fake_injuries(league):
    got = {}
    for tid, rows in (real_official(league) or {}).items():
        got[tid] = list(rows)
    if league in sd.PRO and not got:
        got["0"] = []                                        # (a non-empty 'healthy' pro feed - nobody listed)
    return got


sd.fetch_injuries = fake_injuries

# ---- the snapshot: the day's games at the board-hour price, nothing after the day
games = sd.load_games()
hist = {}
for mo in ("2026-10", "2026-11"):
    p = os.path.join(REPO, "data", "sports", "line_history", f"{mo}.jsonl")
    if not os.path.exists(p):
        continue
    with open(p) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:                                # noqa: BLE001
                continue
            if r.get("t", "") <= BOARD_T and (r["g"] not in hist or r["t"] >= hist[r["g"]]["t"]):
                hist[r["g"]] = r
snap = {}
n_day = n_priced = 0
for gid, g in games.items():
    st = g.get("start") or ""
    if not st:
        continue
    d = datetime.strptime(st[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(sports.PT).date()
    if d > day:
        continue
    c = copy.copy(g)
    if d == day:
        n_day += 1
        c["status"], c["home_score"], c["away_score"] = "pre", "", ""
        h = hist.get(gid)
        if h and h.get("h") is not None and h.get("a") is not None:
            n_priced += 1
            c["ml_home"], c["ml_away"] = h["h"], h["a"]
            if h.get("sp") is not None:
                c["spread_home"] = h["sp"]
                if h.get("spo"):
                    c["spread_home_odds"], c["spread_away_odds"] = h["spo"][0], h["spo"][1]
    snap[gid] = c
print(f"{iso}: {n_day} games on the day, {n_priced} re-priced from the 16:00Z line history; board hour {at:%H:%MZ}")

model = sports._load("model.json", {"params": {}, "log": []})
picks = [p for p in copy.deepcopy(sports.dedupe_picks(sports._load("picks.json", []))) if p["date"] < iso]
sp.CACHE = sp.load()
sm.KEY_EDGE = sp.key_edges(snap, sp.CACHE)
sports.load_states(snap)
if sports.STATE_FAILS:
    print("!! states that failed to load:", sports.STATE_FAILS)
new = sports.post_board(snap, model, picks, at, day, force=False)

print("\n==== THE BOARD post_board would post at 8:35 AM PT")
order = {"lock": 0, "dog": 1, "solo": 2, "night": 3, "play": 4, "lean": 5}
for pk in sorted(new, key=lambda p: (order.get(p["kind"], 9), -(p.get("p_hit") or 0))):
    leg = pk["legs"][0]
    u = sports.units_for(pk)
    tag = sports.posted_kind(pk) + ("⭐" if pk.get("best") else "") + ("(forced)" if pk.get("forced") else "")
    print(f"  {pk['kind'].upper():5} {tag:9} {leg['league'].upper():5} {sports.leg_label(leg)} ({sports.fmt_american(leg['odds'])}) vs {leg.get('opp')} - "
          f"{'LEAN' if pk.get('lean') else f'{u:g}u'} - p {leg.get('p', 0):.3f} own {((leg.get('edge_own') or 0) + 1) / leg['dec'] if leg.get('edge_own') is not None else float('nan'):.3f} "
          f"mkt {leg.get('p_market')} w_p {leg.get('w_p')} dog_p {leg.get('dog_p')} score {leg.get('dog_score')} "
          f"{'THIN' if sports.thin_edge(leg) else ''} reasons={leg.get('reasons')}")
if not new:
    print("  (nothing)")
waiting = [p for p in picks if p["date"] == iso and p["status"] == "waiting"]
for w in waiting:
    print(f"  WAITING {w['kind']}: on {w.get('waiting')}")

# ---- every NHL / NBA moneyline side: the read and what keeps it off
LEAGUES = None if "--all-leagues" in sys.argv else ("nhl", "nba")
raw = [c for c in sports.LAST_RAW if c.get("market") == "ml" and (LEAGUES is None or c.get("league") in LEAGUES)]
taken = {l["game_id"] for p in new for l in p["legs"]}


def own_p(c):
    return None if c.get("edge_own") is None or not c.get("dec") else (c["edge_own"] + 1) / c["dec"]


def checks(c):
    out = []
    lg = c.get("league")
    d = dict(c)
    if c.get("trap"):
        out.append("TRAP")
    if c.get("waiting"):
        out.append("waiting: " + "; ".join(c["waiting"])[:60])
    if c.get("hurt"):
        out.append("HURT (no units): " + ", ".join(c["hurt"][:3]))
    if c.get("odds", 0) >= 100:                               # ---- the dog paths
        if c["odds"] > sports.DAILY_DOG_MAX:
            out.append(f"past +{sports.DAILY_DOG_MAX}")
        if sports.fighting(d):
            out.append("FIGHTING (own read under the price)")
        try:
            sc = round(sports.dog_score(d), 2)
        except Exception as e:                               # noqa: BLE001
            sc = None
            out.append(f"dog_score ERR {str(e)[:40]}")
        gate = {"nfl": sports.DOG_GATE, "nhl": sports.NHL_DOG_GATE, "ncaaf": sports.NCAAF_DOG_GATE, "nba": sports.NBA_DOG_GATE}.get(lg)
        if sc is not None and gate is not None:
            out.append(f"score {sc:+.2f} vs gate {gate:g} -> {'GATED' if sc >= gate else 'under the gate'}")
        ok_own = sports.dog_own_ok(d)
        gap = sports.hockey_own_gap(d)
        if not ok_own:
            out.append("own read UNDER the " + ("no-vig market" if sports.DOG_OWN_RULE.get(lg, "price") == "market" else "price") + " (dog_own_ok)")
        if lg == "nhl":
            if gap is not None:
                out.append(f"own gap {gap:+.2f} pts on the no-vig (fallback needs {sports.NHL_FALLBACK_OWN_GAP:g}+)")
            bhd = sports.best_hockey_dog([dict(c)])
            out.append("hockey fallback: " + ("PASSES" if bhd is not None else "fails"))
            if sc is not None and gap is not None and sc > sports.NHL_BEST_DOG_MIN and gap >= sports.NHL_FALLBACK_OWN_GAP and ok_own and bhd is None:
                dp = min(0.95, (c.get("p_market") or 1 / c["dec"]) + sc / 100)
                out.append(f"  (fallback value check {dp * c['dec'] - 1:+.3f} vs MIN_EDGE {sports.MIN_EDGE})")
        sports.score_reason(d)
        if not d.get("reasons"):
            out.append("no named reason (good() / the floor)")
        if not sports.good(dict(d)):
            out.append("not good()")
        if not sports.beats_price(dict(d)):
            out.append("read doesn't beat the price (beats_price)")
        if sports.dog_gate(dict(d)):
            out.append("DOG GATE PASSES (dog_p %.3f)" % dict(d).get("dog_p", 0) if False else "DOG GATE PASSES")
        if sports.thin_edge(d):
            out.append("thin")
        why = sports.floor_skip(d) if lg not in sports.FLOOR_LEAGUES_OFF or True else None
        out.append(f"floor: {'skip - ' + why if why else 'eligible'}")
    else:                                                    # ---- the favorite paths (Lock / value play / NBA favorite)
        if c["odds"] < sports.MAX_FAV:
            out.append(f"past {sports.MAX_FAV}")
        if sports.fighting(d):
            out.append("FIGHTING (own read under the price)")
        if sports.S6_LOCK_SKIP[0] <= c["odds"] <= sports.S6_LOCK_SKIP[1]:
            out.append("in the -119..-101 no-Lock band")
        out.append(f"p {c.get('p', 0):.3f} ({'lock_ok' if sports.lock_ok(d) else 'under 56% - no Lock'}; {'53%+ play' if c.get('p', 0) >= sports.PLAY_MIN_P else 'under 53% - no play'})")
        if not c.get("reasons"):
            out.append("no named reason")
        out.append("own_agrees " + ("yes" if sports.own_agrees(d) else "NO"))
        out.append("real_value " + ("yes" if sports.real_value(d) else "NO"))
        out.append("own_beats " + ("yes" if sports.own_beats(d) else "NO"))
        if lg == "nhl":
            if sports.nhl_pricey(d):
                out.append("nhl_pricey")
            if sports.hockey_fav_bad(d):
                out.append("hockey_fav_bad")
        if sports.thin_edge(d):
            out.append("thin (no thin Lock; a ½u play at most)")
        out.append("tier " + str(sports.leg_tier(dict(d))))
        if not sports.good(dict(d)):
            out.append("not good()")
        if lg == "nba":
            w = c.get("nba_fav_w") or {}
            out.append(f"nba_fav_w {w} ({'net +' if w and sum(w.values()) > 0 else 'no net weight'})" + (" week-one" if sports.nba_week_one(d) else ""))
    return out


print(f"\n==== EVERY {'/'.join(l.upper() for l in LEAGUES) if LEAGUES else ''} MONEYLINE SIDE at the board hour")
for c in sorted(raw, key=lambda c: (c.get("league"), c.get("start") or "", c.get("game_id"), -c.get("odds", 0))):
    o = own_p(c)
    flag = "  <-- POSTED" if c["game_id"] in taken and any(l["side"] == c["side"] and l["game_id"] == c["game_id"] for p in new for l in p["legs"]) else ""
    print(f"\n{c['league'].upper()} {c.get('team')} {sports.fmt_american(c['odds'])} vs {c.get('opp')} ({'home' if c.get('home') else 'away'}){flag}")
    print(f"   p {c.get('p', 0):.3f}  own {o if o is None else round(o, 3)}  no-vig {c.get('p_market')}  w_p {c.get('w_p')}  raw_own {c.get('raw_own')}  edge {c.get('edge'):+.3f}  edge_own {c.get('edge_own')}")
    dm = c.get("dog_more") or {}
    dm = list(dm.items())[:10] if isinstance(dm, dict) else list(dm)[:10]
    print("   reasons:", c.get("reasons"), "| dog_more:", dm, "| rested_vs_b2b:", c.get("rested_vs_b2b"), "| hot_key:", c.get("hot_key"), "key_edge:", c.get("key_edge"), "pdo:", c.get("pdo"), "drift:", c.get("drift"))
    for x in checks(c):
        print("   -", x)
