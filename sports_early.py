"""⏰ EARLY VALUE PLAYS - get it before the line moves (the owner, 9/30: "this is what the sharps do - get in early on
these lines for the value").

The 9/30 night studies (tools/): the engine's own read spots the right underdogs BEFORE the market does - the money
followed its 8+ point dogs 73-79% of the time - but the value is only in the EARLY price (the engine retrained on
seasons before 7/2024 only, graded on the two since: NFL own +4..8 dogs +11%, own +8 +20%; NHL own +8 +10%, at the
morning price; at game-time prices the same dogs lose). So these don't wait for the 8 AM board:

Every engine run (hourly), every upcoming game with a line (the NFL a week out, the NHL the night before):
  - a +100 .. +280 moneyline dog in a league that passed the exam (EARLY),
  - the engine's OWN read (its model, not the market blend) EARLY[league]+ points over the price right now,
  - the money hasn't already moved it: the price is still within MOVED_MAX cents of the opening line,
  - not a trap spot (sports_dogs), no key player out on its side, the game 2+ hours away,
goes up right then at that price, with a push to everybody. Graded at the posted price, its own record (never ours).
Posted = final (the owner's rule: a posted pick is never changed).
"""
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_model as sm

PT = ZoneInfo("America/Los_Angeles")
PATH = os.path.join(sd.DATA, "early.json")
EXAM_PATH = os.path.join(sd.DATA, "early_exam.json")
PARAMS_PATH = os.path.join(sd.DATA, "early_params.json")   # the engine retrained on recent seasons (a week's cache)
ON = True                               # the owner OK'd it 9/30 (the box, the game-day box, the ping)
PINGS = False                           # the owner, 10/4: "no need to send notifications anymore for early value plays"
#                                         (was on since 10/1: one ping each once the dashboard showed it - tools/early_ping.py)
LEARN_Y = 3                             # the engine for these learns on the last 3 seasons only: the owner's call
                                        # (9/30: "the sports have changed"), and the exam agreed - NBA and college
                                        # football only pass it learning recent, the NFL passes both ways
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")   # every sport takes the exam, 3 times a day
BANDS = ((0.04, 0.08, 100, 280), (0.08, 1.0, 100, 280),   # (how far the engine's own read beats the early price,
         (0.08, 0.12, 100, 149))                          #  the dog's price range): +4..8, +8 or more, and short dogs
                                                          # +100..+149 at +8..12 (9/30, with who's pitching / in net:
                                                          # MLB 4 of 4 seasons +11.5%, NHL 3 of 3 +7.4%)
PASS_N, PASS_SEASON_N, PASS_ROI = 60, 20, 0.02   # a band passes: 60+ dogs, 20+ in each exam season, +2% in EACH
EARLY = {}                              # 10/1: nothing until an exam on bettable prices passes (the 9/30 NFL / NBA
#                                         passes were graded at the NFL's summer look-ahead opens - see bettable())
DOG_MIN, DOG_MAX = 100, 280
MOVED_MAX = 15                          # cents the price may have already moved toward the dog since the open
LEAD_H = 2                              # the game at least this many hours away
AHEAD_D = 8                             # look this many days ahead (the NFL posts a week out)


def load(path=None):
    try:
        with open(path or PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"picks": []}


def save(st, path=None):
    path = path or PATH
    with open(path + ".tmp", "w") as f:
        json.dump(st, f, indent=1)
    os.replace(path + ".tmp", path)


def _t(s):
    return datetime.strptime(str(s)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def band(b):
    """(lo, hi, min price, max price) - older 2-number bands cover every dog +100..+280."""
    b = tuple(b)
    return b if len(b) == 4 else (b[0], b[1], DOG_MIN, DOG_MAX)


def band_name(b):
    lo, hi, omin, omax = band(b)
    return (f"+{round(lo * 100)}{'..' + str(round(hi * 100)) if hi < 1 else '+'}"
            + ("" if (omin, omax) == (DOG_MIN, DOG_MAX) else f" (+{omin}..+{omax} dogs)"))


def passed(path=None):
    """league -> the bands that passed the latest early-price exam."""
    try:
        with open(path or EXAM_PATH) as f:
            ex = json.load(f)
        return {lg: [tuple(b) for b in v["passed"]] for lg, v in ex["leagues"].items() if v.get("passed")}
    except (OSError, ValueError, KeyError, TypeError):
        return dict(EARLY)


_RECENT = {}


def recent_params(games, now=None, leagues=None):
    """The engine retrained on the last LEARN_Y seasons only (cached in early.json for a week: a retrain is slow)."""
    now = now or datetime.now(timezone.utc)
    leagues = leagues or list(passed())
    try:                                                 # (its own file: post() saves early.json after this and
        with open(PARAMS_PATH) as f:                     #  would drop the cache - it retrained every hour, 9/30)
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    cache = st.get("params") or {}
    fresh = st.get("tuned") and now - _t(st["tuned"]) < timedelta(days=7)
    if fresh and all(lg in cache for lg in leagues):
        return {lg: cache[lg] for lg in leagues}
    since = (now - timedelta(days=365 * LEARN_Y)).strftime("%Y-%m-%d")
    recent = {k: g for k, g in games.items() if g.get("start", "") >= since}
    for lg in leagues:
        p = sm.tune(recent, lg)
        if p:
            cache[lg] = p
    st["params"], st["tuned"] = cache, now.strftime("%Y-%m-%dT%H:%MZ")
    with open(PARAMS_PATH, "w") as f:
        json.dump(st, f)
    return {lg: cache[lg] for lg in leagues if lg in cache}


def _dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def exam(games, now=None, leagues=LEAGUES, path=None):
    """THE EARLY-PRICE EXAM (runs with the studies, 3x a day). Retrain on the LEARN_Y seasons before the last two, then
    on those two it never saw: every +100..+280 dog, at the EARLY price (the open) and at game time, by how far the
    engine's own read beat that price. A band goes live only if it made PASS_ROI+ in EACH of the two seasons."""
    now = now or datetime.now(timezone.utc)
    y = now.year if now.month >= 7 else now.year - 1
    split, mid = f"{y - 2}-07-01", f"{y - 1}-07-01"
    learn = {k: g for k, g in games.items() if f"{y - 2 - LEARN_Y}-07-01" <= g.get("start", "") < split}
    if not sm.KEY_EDGE:                                  # who's pitching / in net / at QB (form from earlier starts only):
        try:                                             # the live scan has it, so the exam has to grade with it too
            import sports_players as sp
            sm.KEY_EDGE = sp.key_edges(games, sp.load())
        except Exception as e:                           # noqa: BLE001
            print(f"   early exam: no starters ({str(e)[:60]})")
    out = {}
    for lg in leagues:
        p = sm.tune(learn, lg)
        if not p or "w" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        rows = {}
        for g, f, *_ in played:
            if g["start"] < split:
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
            except (KeyError, ValueError):
                continue
            oh, oa, ch, ca = (_int(g.get(k)) for k in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
            if hs == as_ or None in (oh, oa, ch, ca) or (oh, oa) == (ch, ca):
                continue                                 # no real early price
            own = sm.own_p(p, f)
            for price, (a, b) in (("early", (oh, oa)), ("game time", (ch, ca))):
                pa, pb = 1 / _dec(a), 1 / _dec(b)
                mk = pa / (pa + pb)
                for o, won, ow, m, c in ((a, hs > as_, own, mk, ch), (b, as_ > hs, 1 - own, 1 - mk, ca)):
                    if not DOG_MIN <= o <= DOG_MAX:
                        continue
                    if price == "early" and not bettable(o, c):
                        continue                         # 10/1 audit: the live scan never posts once the price has
                        #                                  run MOVED_MAX+ toward the dog - and the NFL's "open" is often
                        #                                  the summer look-ahead line (Ravens opened -250, closed +265),
                        #                                  a price nobody can bet a week out. Grading at it made the NFL
                        #                                  look +57% on exactly those dogs (-23% on the rest).
                    for b in BANDS:
                        lo, hi, omin, omax = b
                        if lo <= ow - m < hi and omin <= o <= omax:
                            rows.setdefault((price, b), []).append((g["start"] >= mid, won, _dec(o)))
        roi = lambda b: round(sum((d - 1) if w else -1 for _, w, d in b) / len(b), 4) if b else None
        res, ok = {}, []
        for (price, bd), b in sorted(rows.items()):
            s1, s2 = [r for r in b if not r[0]], [r for r in b if r[0]]
            res[f"{price} {band_name(bd)}"] = {
                "dogs": len(b), "won": round(sum(r[1] for r in b) / len(b), 3), "money": roi(b),
                "season1": [len(s1), roi(s1)], "season2": [len(s2), roi(s2)]}
            if price == "early" and len(b) >= PASS_N and min(len(s1), len(s2)) >= PASS_SEASON_N \
                    and roi(s1) >= PASS_ROI and roi(s2) >= PASS_ROI:
                ok.append(list(bd))
        out[lg] = {"bands": res, "passed": ok}
    ex = {"at": now.strftime("%Y-%m-%dT%H:%MZ"), "learned_on": [f"{y - 2 - LEARN_Y}-07", split[:7]],
          "exam": [split[:7], now.strftime("%Y-%m")], "leagues": out,
          "proven": [f"{lg} {band_name(b)}" for lg, v in out.items() for b in v["passed"]]}
    if path is not False:
        with open(path or EXAM_PATH, "w") as f:
            json.dump(ex, f, indent=1)
    return ex


def study(games):
    return exam(games)


def bettable(open_ml, close_ml):
    """Could the live scan have posted this dog at its open? Only if the price hadn't run MOVED_MAX+ cents toward it -
    the exam grades the same dogs the scan would take (10/1: the NFL's summer look-ahead opens made it look +57%)."""
    return moved_toward(open_ml, close_ml) <= MOVED_MAX


def moved_toward(open_ml, now_ml):
    """How many cents the dog's price has come in since the open (+ = toward the dog). 0 when there's no real open."""
    if open_ml is None or now_ml is None or open_ml == now_ml:
        return 0
    return open_ml - now_ml                          # +160 -> +140 = 20 cents toward the dog


def scan(games, model, now=None, injuries=None, trap=None):
    """-> the NEW early value dogs right now (not yet posted), each {game_id, league, side, team, opp, odds, open,
    own, mkt, gap, start}."""
    now = now or datetime.now(timezone.utc)
    bands = passed()
    model = {"params": {**(model.get("params") or {}), **{lg: p for lg, p in recent_params(games, now).items()}}}
    elo = sm.ratings(games, model)
    out = []
    for g in games.values():
        lg = g.get("league")
        if lg not in bands or g.get("status") != "pre" or (g.get("stype") or "?") not in sd.REAL:
            continue
        try:
            start = _t(g["start"])
        except (KeyError, ValueError):
            continue
        if start < now + timedelta(hours=LEAD_H) or start > now + timedelta(days=AHEAD_D):
            continue
        if start.astimezone(PT).date() <= now.astimezone(PT).date():
            continue                                 # game day is the daily board's, never "early" (9/30: the Kings
            #                                          went up at 5 PM for a 7 PM game - the owner: "that's not early")
        mkt = sm.market_p(g)
        if mkt is None:
            continue
        params = (model.get("params") or {}).get(lg) or sm.default_params(lg)
        if "w" not in params:
            continue
        f = elo[lg].features(g)
        if f.get("known", 0) < 3:
            continue
        own = sm.own_p(params, f)                    # the engine's OWN read (the model the exam graded)
        inj = (injuries or {}).get(lg)
        for side, o_mkt, o_own in (("home", mkt, own), ("away", 1 - mkt, 1 - own)):
            odds = _int(g.get(f"ml_{side}"))
            if odds is None or not DOG_MIN <= odds <= DOG_MAX:
                continue
            gap = o_own - o_mkt
            if not any(lo <= gap < hi and omin <= odds <= omax for lo, hi, omin, omax in map(band, bands[lg])):
                continue
            if lg == "mlb" and not (g.get("sp_home") and g.get("sp_away")):
                continue                             # baseball: both starting pitchers announced, or no read at all
            if moved_toward(_int(g.get(f"ml_{side}_open")), odds) > MOVED_MAX:
                continue                             # the money already took the value
            if inj is not None and not sd.covered(inj, lg, g[side], g[f"{side}_name"]):
                continue                             # (10/3 sweep) no injury data on this team = unknown, never a play
            if inj and sd.team_key_out(inj, g[side], g[f"{side}_name"], lg, maybe=True):
                continue                             # a key player out on OUR side: the ratings can't see it
            if inj and sd.team_unsure(inj, g[side], g[f"{side}_name"], lg, maybe=True):
                continue                             # ...or QUESTIONABLE (the owner, 9/30: the good early price is only
                                                     # good because the book's guessing he plays - then he's ruled out)
            if trap and trap(lg, odds, side == "home"):
                continue
            other = "away" if side == "home" else "home"
            out.append({"game_id": g["id"], "league": lg, "side": side, "team": g[f"{side}_name"],
                        "opp": g[f"{other}_name"], "odds": odds, "opp_odds": _int(g.get(f"ml_{other}")), "sp": g.get(f"sp_{side}") or None, "open": _int(g.get(f"ml_{side}_open")),
                        "own": round(o_own, 4), "mkt": round(o_mkt, 4), "gap": round(gap, 4), "start": g["start"]})
    return out


BOOK_LEAGUES = ("nfl", "ncaaf", "nba", "nhl", "mlb", "ncaab")


def with_book_lines(games, st, now, fetch=None):
    """The owner (9/30): 'as soon as the lines come out, that's when we need to see them - some books have lines before
    others.' A book's line (BetRivers posts football a week out) fills any upcoming game ESPN has no price for yet, and
    the FIRST price any of our books ever showed is kept as that game's open. Returns a copy - the stored games and
    the main board never see these."""
    if fetch is None:
        import sports_books
        fetch = sports_books.pregame
    seen = st.setdefault("first_seen", {})
    out = dict(games)
    for lg in [x for x in BOOK_LEAGUES if x in passed()]:
        try:
            rows = fetch(lg)
        except Exception as e:                           # noqa: BLE001 - a book down never breaks the scan
            print(f"   early lines {lg}: {str(e)[:60]}")
            continue
        for r in rows:
            try:
                t = datetime.strptime(r["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                continue
            for gid, g in games.items():
                if g.get("league") != lg or g.get("status") != "pre" or not g.get("start"):
                    continue
                if abs((_t(g["start"]) - t).total_seconds()) > 3 * 3600 or not sd._same(g["home_name"], r["home"]) \
                        or not sd._same(g["away_name"], r["away"]):
                    continue
                seen.setdefault(gid, {"ml_home": r["ml_home"], "ml_away": r["ml_away"], "src": r.get("src", "book"),
                                      "at": now.strftime("%Y-%m-%dT%H:%MZ")})
                g2 = dict(g)
                if str(g.get("ml_home", "")) == "":          # ESPN hasn't priced it yet: the book's line is the line
                    g2.update(ml_home=str(r["ml_home"]), ml_away=str(r["ml_away"]))
                if str(g.get("ml_home_open", "")) == "":     # the first line any book showed = the open
                    g2.update(ml_home_open=str(seen[gid]["ml_home"]), ml_away_open=str(seen[gid]["ml_away"]))
                out[gid] = g2
                break
    return out


def post(games, model, now=None, injuries=None, trap=None, path=None, ping=None, lines=None):
    """Scan, post the new ones (once per game), grade the finished ones. Returns the new posts."""
    now = now or datetime.now(timezone.utc)
    st = load(path)
    if not ON:
        return []
    games = with_book_lines(games, st, now, lines)
    have = {p["game_id"] for p in st["picks"]} | {p.get("game_id") for p in st.get("pulled") or []}   # (10/2 audit:
    new = []                                         # a pulled play never comes back)
    for c in scan(games, model, now, injuries, trap):
        if c["game_id"] in have:
            continue                                 # one early dog per game, posted = final
        c.update(posted=now.strftime("%Y-%m-%dT%H:%MZ"), result=None)
        g = games.get(c["game_id"]) or {}
        inj = (injuries or {}).get(c["league"])
        if inj is not None:                          # already out at post (priced in): the watch only flags NEW outs
            c["out_at_post"] = [r[0] for r in sd.team_key_out(inj, g.get(c["side"]), c["team"], c["league"])]
        st["picks"].append(c)
        have.add(c["game_id"])
        new.append(c)
        if ping and not st.get("launched"):          # 🚨 the one-time breakthrough ping - with the FIRST real play
            st["launched"] = now.strftime("%Y-%m-%dT%H:%MZ")   # (the owner, 9/30: "send it when the first play posts")
            try:
                ping(None)
            except Exception as e:                   # noqa: BLE001
                print(f"   launch ping failed: {str(e)[:60]}")
        if ping:
            try:
                ping(c)
            except Exception as e:                   # noqa: BLE001 - an alert never breaks the engine
                print(f"   early dog ping failed: {str(e)[:60]}")
    try:                                                     # 🧪 the six spots (the owner, 10/1)
        elo = None

        def own_of(g, side):
            nonlocal elo
            p_ = (model.get("params") or {}).get(g["league"]) or sm.default_params(g["league"])
            if "w" not in p_:
                return None
            elo = elo or sm.ratings(games, model)
            f = elo[g["league"]].features(g)
            if f.get("known", 0) < 3:
                return None
            o = sm.own_p(p_, {**f, "inj": 0.0, "key": 0.0, "weather": 0.0, "cold": 0.0})   # Tuesday-known only
            return o if side == "home" else 1 - o
        ws_ = week_start(now)
        room = 10 ** 6 if SPOT_MAX_WEEK is None else SPOT_MAX_WEEK - sum(
            1 for p in st.get("picks", []) if p.get("spot") and p.get("posted") and _t(p["posted"]) >= ws_)
        for c in pick_spots(spot_scan(games, now, injuries, own_of), st, now, have) + \
                min_one(games, st, now, injuries, own_of, have):
            if c["game_id"] in have:
                continue
            if room <= 0:
                break                                        # (10/1 audit: never past 2 a week, both paths together)
            room -= 1
            c.update(posted=now.strftime("%Y-%m-%dT%H:%MZ"), result=None)
            st["picks"].append(pick_wording(c, st))
            have.add(c["game_id"])
            new.append(c)
            if ping:                                         # (10/2 audit: the spots - the only football path -
                try:                                         #  never pinged; the Jaguars went up silent)
                    ping(c)
                except Exception as e:                       # noqa: BLE001
                    print(f"   early spot ping failed: {str(e)[:60]}")
    except Exception as e:                                   # noqa: BLE001 - the spots never break the engine
        print(f"   early spots failed: {str(e)[:120]}")
    try:                                                     # 🌍 the Europe morning NFL under (the owner, 10/4)
        for c in euro_unders(games, st, now):
            if c["game_id"] in have:
                continue
            st["picks"].append(c)
            have.add(c["game_id"])
            new.append(c)
    except Exception as e:                                   # noqa: BLE001 - never breaks the engine
        print(f"   europe under failed: {str(e)[:120]}")
    watch(st, games, injuries)
    grade(st, games)
    save(st, path)
    return new


def euro_quit(st):
    """The quit rule: 15+ graded and under 50% = no more posts."""
    w, l_, _ = spot_record(st).get("euro_under", (0, 0, 0.0))
    return w + l_ >= EURO_QUIT[0] and w / (w + l_) < EURO_QUIT[1]


def euro_unders(games, st, now):
    """🌍 THE EUROPE MORNING NFL UNDER - ½u, its own record (the owner, 10/4: "we can't wait years to prove anything -
    the books will catch up by then ... half unit with the quit rule, build it"). Every NFL game in Europe kicking off
    before noon ET (sports_intl.fits): the UNDER at the number the night before (from EURO_FROM_PT the day before the
    game, PT) - the 10/4 study: 17-9 under since 2018 in those games (SPORTS_FINDINGS). A live test the owner OK'd on a
    small sample, not a proven edge; under 50% after 15 = it's off (EURO_QUIT)."""
    import sports_intl
    if euro_quit(st):
        return []
    out = []
    for g in games.values():
        if not sports_intl.fits(g) or g.get("status") != "pre":
            continue
        tot, odds = sports_intl._f(g.get("total")), _int(g.get("under_odds")) or -110
        if tot is None or odds < -150:
            continue                                         # (no number yet / the -150 rule)
        st_ = _t(g["start"])
        eve = datetime.combine((st_.astimezone(PT) - timedelta(days=1)).date(), datetime.min.time(),
                               tzinfo=PT).replace(hour=EURO_FROM_PT)
        if not eve <= now < st_ or now.astimezone(PT).date() >= st_.astimezone(PT).date():
            continue                                         # the night before only - never game day
        w, l_, _ = spot_record(st).get("euro_under", (0, 0, 0.0))
        city = g.get("city") or g.get("country") or "Europe"
        out.append({"game_id": g["id"], "league": "nfl", "market": "total", "side": "under", "line": tot,
                    "team": f"Under {tot:g}", "opp": f"{g.get('away_name')} @ {g.get('home_name')}", "odds": odds,
                    "start": g["start"], "spot": "euro_under", "spots": ["euro_under"], "fades": [],
                    "why": f"🌍 {city}, {st_.astimezone(PT):%-I:%M %p} PT kickoff. NFL games in Europe that start "
                           f"this early went 17-9 to the under since 2018"
                           + (f" - {w}-{l_} since we started betting it." if w + l_ else "."),
                    "posted": now.strftime("%Y-%m-%dT%H:%MZ"), "result": None})
    return out


def watch(st, games, injuries):
    """A posted play's key player (QB, goalie...) ruled out after we posted: the price blows up for a reason the early
    read never saw. The play itself never changes (the owner's rule) - its rows say it plain: don't chase it."""
    for p in st["picks"]:
        g = games.get(p["game_id"])
        if p.get("sp") and g and not p.get("result") and g.get(f"sp_{p['side']}") and g[f"sp_{p['side']}"] != p["sp"]:
            p["key_out"] = f"{p['sp']} (SP)"                 # the owner, 9/30: a last-minute pitcher swap blows up the
            continue                                         # line - our starter isn't going: don't chase it
        inj = (injuries or {}).get(p["league"])
        if p.get("result") or not g or g.get("status") != "pre" or inj is None or p.get("market") == "total":
            continue
        out = sd.team_key_out(inj, g.get(p["side"]), g.get(f"{p['side']}_name") or p["team"], p["league"])
        if "out_at_post" not in p:                   # who was already out when it posted: priced in, not news
            p["out_at_post"] = [r[0] for r in out]
        new = [r for r in out if r[0] not in p["out_at_post"]]
        p["key_out"] = f"{new[0][0]} ({new[0][1]})" if new else None


def grade(st, games):
    for p in st["picks"]:
        if p.get("result"):
            continue
        g = games.get(p["game_id"])
        if not g or g.get("status") != "final":
            stale = bool(p.get("start")) and datetime.now(timezone.utc) - _t(p["start"]) > timedelta(days=4)
            if (g and g.get("status") in ("void", "postponed", "canceled", "cancelled")) or stale:
                p["result"] = "void"                         # (10/2 audit: a game that never went final was stuck
            continue                                         #  pending forever - 4 days, like the board's picks)
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError):
            continue
        if p.get("market") == "total":                       # 🌍 a total: points vs the line we took
            d = (hs + as_ - p["line"]) * (-1 if p["side"] == "under" else 1)
            p["result"] = "won" if d > 0 else "lost" if d < 0 else "push"
        else:
            us, them = (hs, as_) if p["side"] == "home" else (as_, hs)
            p["result"] = "won" if us > them else "lost" if us < them else "push"
        p["graded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        p["score"] = f'{g["away_name"]} {g["away_score"]} @ {g["home_name"]} {g["home_score"]}'


def record(st):
    ps = [p for p in st.get("picks", []) if p.get("result") in ("won", "lost")]
    w = sum(p["result"] == "won" for p in ps)
    units = sum((_dec(p["odds"]) - 1) if p["result"] == "won" else -1 for p in ps)   # (10/2 audit: -150 won = -1.5u)
    return {"won": w, "lost": len(ps) - w, "units": round(units, 2)}


LAUNCH = ("🚨 MAJOR ENGINE BREAKTHROUGH",                     # the owner's pick (#1), 9/30 - sent once, with the first play
          "We just found an edge on underdogs: get in early before the line moves. 🔥 Most plays start next week.")


def ping_text(c):
    """The push: short, the price front and center (it's taken before it moves). None = the launch ping."""
    if c is None:
        return LAUNCH
    t = _t(c["start"]).astimezone(PT)
    day = f'{when(c["start"], datetime.now(timezone.utc))}, game starts at {t.strftime("%-I:%M %p").replace(":00 ", " ")} PT'
    return (f"⏰ EARLY VALUE PLAY: {c['team']} +{c['odds']}",
            f"{c['team']} ML +{c['odds']} vs {c['opp']}. {day}. Get it before the line moves.")


def send(c):
    title, body = ping_text(c)
    sd.web_push(None, title, body, ref=f"early:{c['game_id']}" if c else "early:launch")


UNITS_MAX = 10


def units(p):
    """⏰ An early play's units - the ENGINE's call (the owner, 9/30): sized by how far its own read beats the price we got
    (a quarter of the Kelly stake, 1u = 1% of the bankroll), ½u to 10u. The sizing study (5 seasons it never saw): at the
    opening price a bigger engine edge won more AND moved the line more (NFL: the biggest edges moved our way 80% of the
    time, 61% flipped to favorites) - sized this way it made the most money in the NFL, NBA, NHL and college football."""
    if p.get("spot") in SPOTS:                               # 🧪 a spot play: its fixed size until it proves
        return SPOTS[p["spot"]][1]                           # itself live (the owner, 10/1)
    import sports
    return sports.kelly_units(p.get("own"), p["odds"])


# ---------------------------------------------------------------- 🧪 THE SIX EARLY SPOTS (the owner, 10/1: "there's only
# one way to prove anything - you do it"). The studies on the odds history (SPORTS_FINDINGS, 10/1) - every one at a
# FAIR price (posted after both teams' last games ended) - live, small, each with its OWN record so the real ones show.
# The one that held every honest test gets 1 unit; the leads get ½ unit until they prove it (30-40 live bets each).
SPOTS = {   # key: (label, units, leagues)
    "bye":       ("🛌 Off a bye vs a team that played", 1.0, ("nfl", "ncaaf")),   # NFL +29% / college +16% (fair)
    "hammered":  ("🔨 Hammered early", 0.5, ("nfl", "ncaaf")),                  # in 4+ win-% pts since the first fair price
    "mnf":       ("🏈 Monday night dog", 0.5, ("nfl",)),                          # NFL +21%, 5 of 6
    "eastwest":  ("✈️ East Coast team flying West", 0.5, ("nfl",)),              # NFL +17%, 6 of 6
    "blowout":   ("💥 Blew somebody out last week", 0.5, ("nfl", "ncaaf")),      # +8 / +9%, both sports
    "engine":    ("🧠 Engine likes it, the line moved away", 0.5, ("ncaaf",)),  # college +8%, the cutoffs around it too
    "best":      ("🎯 The engine's best dog of the week", 0.5, ("nfl", "ncaaf")),   # the minimum-one rule (10/1)
    "euro_under": ("🌍 Europe morning NFL under", 0.5, ("nfl",)),               # 17-9 since 2018 - live test (10/4)
}
EURO_QUIT = (15, 0.5)                    # the owner, 10/4: "half unit with the quit rule" - under 50% after 15 = it's off
EURO_FROM_PT = 18                        # posted the night before (6 PM PT on): the line's set, nobody moves it overnight
# THE ENGINE NEVER PICKS OFF ONE FACTOR (the owner, 10/1: "an East Coast dog out West still gets blown out - weigh
# everything, never automatically take a pick because the numbers back one thing"). A spot only ADDS weight to the
# engine's own full read (ratings, form, rest, injuries...); the fades take weight away. An early play posts only when
# the engine's read isn't fighting the side AND everything added up clears SPOT_MIN_TOTAL - ranked by that total.
SPOT_WEIGHT = {"best": 0.0, "bye": 0.04, "mnf": 0.015, "eastwest": 0.03, "blowout": 0.02, "hammered": 0.02, "engine": 0.0}
FADE_WEIGHT = {"ice cold": -0.04, "coach's first season": -0.04, "losing streak": -0.04}
SPOT_MIN_TOTAL = 0.05                   # the engine's edge + the spots + the fades, in win-% points
SPOT_FIGHT = 0.01                       # the engine's own read may not be more than 1 point under the price
SPOT_MAX_WEEK = None                    # the owner, 10/1 (later): "I don't want to cap the early value plays at two -
#                                         build it the best for us": every play that clears the whole bar posts, the
#                                         moment it's found (waiting costs the price). None = no cap. (Was 2.) The engine
#                                         ranks everything it finds and posts the best 2 a week (Tuesday to Monday)
SPOT_ORDER = ("bye", "mnf", "eastwest", "blowout", "hammered", "engine", "best")
SPOT_MIN_WEEK = 0                       # the owner, 10/1: "one minimum, two max early value plays" - a week the spots
MIN_ONE_FROM = (2, 6)                   # find nothing, the engine's best weighed dog goes up (½u) from Wednesday 6 AM
#                                         PT on - early, before the line moves (dog prices only shorten in the week)   # most believed first
SPOT_WINDOW_H = 72                      # an early play posts within 3 days of its first fair number - after that the
#                                         early number's gone (the owner, 10/1: "we're already late" on a Thursday)
SPOT_SLATE_HOUR_PT = 6                  # it waits for the whole slate: college numbers come Sunday, the NFL's after
#                                         Monday night - it ranks them all together Tuesday 6 AM PT, then fills
SPOT_DOG = (100, 220)                   # the dog spots: +100 to +220 (the owner, 10/1: "never no damn +400" - the
#                                         +130..+160 that moves toward a favorite is the target, a +220 now and then)
SPOT_ANY = (-150, 220)                  # the engine spot: any side, never past -150 (the -150 rule) or +220
REST_BYE, REST_NORMAL = 13, 8           # off a bye: 13+ days since its last game; the other team on a normal week
HAMMER_PTS, ENGINE_OUT_PTS, ENGINE_GAP = 4.0, 2.0, 0.04
BLOWOUT = 17


def _imp(o):
    return 1 / _dec(o)


def _schedule(games):
    """{team key: [(start, game)]} by league - every real game, in order."""
    out = {}
    for g in games.values():
        if not g.get("start") or (g.get("stype") or "?") not in sd.REAL:
            continue
        for side in ("home", "away"):
            out.setdefault((g.get("league"), g[side]), []).append((g["start"], g))
    for v in out.values():
        v.sort(key=lambda x: x[0])
    return out


def ago(prev_start, now):
    """When their last game was (10/3, the owner: an Alabama card said 'beat Mississippi St 56-23 last week' the same
    afternoon they played): 'last week' only when it was 5+ days before we post, else the day with its date ('on
    Saturday 10/3') - the line is saved once and stays on the card all week, so never 'today' / 'yesterday'."""
    t = _t(prev_start).astimezone(PT)
    d = (now.astimezone(PT).date() - t.date()).days
    return "last week" if 5 <= d <= 9 else f"on {t:%A} {t.month}/{t.day}"   # (10/4: the blowout spot reaches back
    #   21 days - a team off a bye beat somebody two Saturdays ago, never 'last week')


def when(start, now):
    """The day an early play's game is on: 'Tomorrow', else the weekday WITH the date ('Saturday 10/10') - a bare
    'Saturday' posted on a Saturday read like tonight (10/3, the owner: "Alabama vs Georgia today?")."""
    t = _t(start).astimezone(PT)
    d = (t.date() - now.astimezone(PT).date()).days
    return "Today" if d <= 0 else "Tomorrow" if d == 1 else f"{t:%A} {t.month}/{t.day}"


def spot_why(sched, g, side, other, lg, spot, now=None, own=None, odds=None):
    """The early play's reason in plain words (the owner, 10/1: "'blew somebody out last week' is very vague"; 10/4:
    the spot is ONE weight - lead with the engine's own read, the spot is the fact behind it). One line. -> a list of
    wordings (READS); pick_spots / the save takes one no other early card on the board is using ("no same wording
    across the two")."""
    me, opp = g.get(f"{side}_name") or "They", g.get(f"{other}_name") or "them"
    p = _prev(sched, lg, g[side], g["start"])
    fact = {"mnf": f"Monday night dog.", "eastwest": f"{me} flying from the East Coast out West.",
            "hammered": f"The money hit {me} early.", "engine": f"The line moved away from them - better price for us.",
            "best": ""}.get(spot, "")
    facts = [fact] * 3
    try:
        if spot == "blowout" and p:
            mine = p["home"] == g[side]
            us, them = (p["home_score"], p["away_score"]) if mine else (p["away_score"], p["home_score"])
            vs = p.get("away_name") if mine else p.get("home_name")
            sc, when_ = f"{int(float(us))}-{int(float(them))}", ago(p["start"], now or datetime.now(timezone.utc))
            facts = [f"They beat {vs} {sc} {when_}.", f"Coming off a {sc} beatdown of {vs} {when_}.",
                     f"Fresh off smacking {vs} {sc} {when_}."]
        if spot == "bye" and p:
            facts = [f"{me} had last week off; {opp} played.", f"Rested - {me} sat last week, {opp} didn't.",
                     f"{opp} played last week, {me} got the week off."]
    except (KeyError, ValueError, TypeError):
        pass
    pr = f"+{odds}" if odds and odds > 0 else "this price"
    pc = round(own * 100) if own is not None else 0
    if pc > 55:                                              # a win % only shows over 55% (the owner) - 55.2% rounds to
        #                                                      "55%", so it's judged after the rounding (10/4 audit: Fresno St)
        reads = [f"🧠 Our numbers got {me} winning {pc}% - way more than {pr} pays for.",
                 f"🧠 {me} at {pr} is a gift: we got 'em winning {pc}% of the time.",
                 f"🧠 The books got {me} as the dog; our read has 'em winning {pc}%."]
    else:
        reads = [f"🧠 Our numbers like {me} more than {pr} does.", f"🧠 {me} at {pr} is a gift on our read.",
                 f"🧠 The books got {me} as the dog; our read says they're better than that."]
    return [(r + (" " + f if f else "")).strip() for r, f in zip(reads, facts)]


def pick_wording(c, st):
    """One wording for a new early play no open early card already uses (the owner, 10/4: no same wording across
    the cards)."""
    ws = c.pop("whys", None)
    if not ws:
        return c
    used = {p.get("why_t") for p in st.get("picks", []) if not p.get("result")}
    k = next((i for i in range(len(ws)) if i not in used), 0)
    c.update(why=ws[k], why_t=k)
    return c


def _prev(sched, lg, team, start):
    """The team's previous game before `start` (any status), or None."""
    prev = None
    for st, g in sched.get((lg, team), []):
        if st >= start:
            break
        prev = g
    return prev


def ready(sched, g):
    """When both teams' last games were over (their start + 4h) - an early price only counts after that (10/1)."""
    ps = [_prev(sched, g["league"], g[s], g["start"]) for s in ("home", "away")]
    ps = [p for p in ps if p]
    return (_t(max(p["start"] for p in ps)) + timedelta(hours=4)) if ps else None


def _home_tz(games):
    tz = {}
    for g in games.values():
        if str(g.get("neutral")) != "1" and g.get("tzo") not in (None, ""):
            try:
                tz.setdefault((g.get("league"), g["home"]), []).append(float(g["tzo"]))
            except ValueError:
                pass
    return {k: max(set(v), key=v.count) for k, v in tz.items()}


def first_fair(gid, since, hist_dir=None):
    """The first price we recorded for this game at or after `since`: (home ml, away ml) - from the line history the
    engine keeps every hour (sports_data.record_lines)."""
    d = hist_dir or sd.LINE_HIST_DIR
    best = None
    try:
        files = sorted(f for f in os.listdir(d) if f.endswith(".jsonl"))[-2:]
    except OSError:
        return None
    for fn in files:
        with open(os.path.join(d, fn)) as f:
            for x in f:
                try:
                    r = json.loads(x)
                except ValueError:
                    continue
                if r.get("g") != gid or (since and r.get("t", "") < since.strftime("%Y-%m-%dT%H:%MZ")):
                    continue
                if best is None or r["t"] < best["t"]:
                    best = r
    if not best:
        return None
    h, a = _int(best.get("h")), _int(best.get("a"))
    return (h, a) if h is not None and a is not None else None


_COACH = {}


def _first_season_coach(lg, team_name, season):
    """An NFL team in its head coach's first season with it (real coach history - sports_coach_history)."""
    if lg != "nfl":
        return False
    if "exp" not in _COACH:
        try:
            import sports_coach_history as ch
            _COACH["exp"] = ch.experience(ch.load(), "nfl")
        except Exception:                                    # noqa: BLE001
            _COACH["exp"] = {}
    for (team, s_), (_, _, first, _) in _COACH["exp"].items():
        if s_ == season and team_name and sd._same(team_name, team):
            return bool(first)
    return False


def _fades(sched, g, side, lg, et):
    """The fades that held (10/1 studies, game-day AND early prices): ice cold (last 3 games 7+ points worse than its
    season, 5+ games in), an NFL team in its coach's first season, a college team on a 3+ game losing streak, a
    Thursday night dog."""
    start = g["start"]
    season = int(start[:4]) if int(start[5:7]) >= 7 else int(start[:4]) - 1
    lo = f"{season}-07-01"
    ms = []
    for st, x in sched.get((lg, g[side]), []):
        if st >= start:
            break
        if st < lo or x.get("status") != "final":
            continue
        try:
            m = float(x["home_score"]) - float(x["away_score"])
        except (KeyError, ValueError, TypeError):
            continue
        ms.append(m if x["home"] == g[side] else -m)
    out = []
    if len(ms) >= 5 and sum(ms[-3:]) / 3 - sum(ms) / len(ms) <= -7:
        out.append("ice cold")
    other = "away" if side == "home" else "home"
    if _first_season_coach(lg, g.get(f"{side}_name"), season) and \
            not _first_season_coach(lg, g.get(f"{other}_name"), season):   # (10/1 audit: both coaches new cancels,
        out.append("coach's first season")                               # like the game-day dog score does)
    if lg == "ncaaf" and len(ms) >= 3 and all(m < 0 for m in ms[-3:]):
        out.append("losing streak")
    return out   # (no Thursday-night fade - the owner, 10/1: "that's a night of football like any other... a small
    #               sample." Checked: 91 NFL Thursday dogs at the close since 2018, up 5 of 9 seasons, the -9% from 3 bad
    #               years; college 72, all over the place. Noise - every game gets read on its own)


def spot_scan(games, now=None, injuries=None, own_of=None, hist_dir=None, any_dog=False):
    """-> the six spots' new candidates right now: {game_id, league, side, team, opp, odds, opp_odds, start, spot,
    spots, own}. Fair prices only, never game day, never a side with a key player out / questionable."""
    now = now or datetime.now(timezone.utc)
    sched = _schedule(games)
    htz = _home_tz(games)
    out = []
    cfin = None
    for g in games.values():
        lg = g.get("league")
        if lg not in ("nfl", "ncaaf") or g.get("status") != "pre" or (g.get("stype") or "?") not in sd.REAL \
                or g.get("tbd") == "1":                      # (no start time set yet: "game day" can't be known)
            continue
        try:
            start = _t(g["start"])
        except (KeyError, ValueError):
            continue
        if start < now + timedelta(hours=LEAD_H) or start > now + timedelta(days=AHEAD_D) or \
                start.astimezone(PT).date() <= now.astimezone(PT).date():
            continue                                         # never on its own game day (the owner, 9/30)
        r = ready(sched, g)
        if r and now < r:
            continue                                         # last week's games aren't over: not a fair price yet
        if r and now > r + timedelta(hours=SPOT_WINDOW_H):
            continue                                         # the early number's gone - late is not early (10/1; the
            #                                                  audit: the backup path skipped this - the Jaguars, 95h)
        oh, oa = _int(g.get("ml_home")), _int(g.get("ml_away"))
        if oh is None or oa is None:
            continue
        mk_h = _imp(oh) / (_imp(oh) + _imp(oa))
        ff = None
        inj = (injuries or {}).get(lg)
        if injuries is not None and inj is None:
            continue                                         # no injury report = we can't see who's out: never post
        et = start.astimezone(ZoneInfo("America/New_York"))
        if lg == "ncaaf":                                    # (10/1: Delaware "off a bye" - we were missing their
            if cfin is None:                                 # 9/26 game at Virginia) a college spot needs every game
                cfin = [x for x in games.values() if x.get("league") == "ncaaf" and x.get("status") == "final"
                        and (x.get("stype") or "?") in sd.REAL and _t(x["start"]) < now]
            import sports_breakdown_v24 as v24           # both teams played this season, or it's a guess
            if not (v24.seen_all(cfin, g["home"], start, lg) and v24.seen_all(cfin, g["away"], start, lg)):
                continue
        for side, other, odds, opp_odds in (("home", "away", oh, oa), ("away", "home", oa, oh)):
            if inj is not None and not sd.covered(inj, lg, g[side], g[f"{side}_name"]):
                continue                                     # (10/3 sweep) a team the injury data doesn't cover is
                #                                              UNKNOWN, never 'healthy' - the board already refuses a
                #                                              blind pick; an early play (units, always) does too
            if inj and (sd.team_key_out(inj, g[side], g[f"{side}_name"], lg, maybe=True) or
                        sd.team_unsure(inj, g[side], g[f"{side}_name"], lg, maybe=True)):
                continue                                     # a dog whose QB is questionable: -21% (10/1) - never
            mk = mk_h if side == "home" else 1 - mk_h
            me_prev = _prev(sched, lg, g[side], g["start"])
            op_prev = _prev(sched, lg, g[other], g["start"])
            hit = []
            dog = SPOT_DOG[0] <= odds <= SPOT_DOG[1]
            if dog and me_prev and op_prev:
                rest = (start - _t(me_prev["start"])).days
                orest = (start - _t(op_prev["start"])).days
                if rest >= REST_BYE and orest <= REST_NORMAL:
                    hit.append("bye")
            if dog and lg == "nfl" and et.weekday() == 0:
                hit.append("mnf")
            if dog and lg == "nfl" and str(g.get("neutral")) != "1" and side == "away":
                mine, gtz = htz.get((lg, g[side])), _int(g.get("tzo"))
                try:
                    gtz = float(g.get("tzo"))
                except (TypeError, ValueError):
                    gtz = None
                if mine is not None and gtz is not None and mine >= -5 and gtz <= -7:
                    hit.append("eastwest")
            if dog and me_prev and me_prev.get("status") == "final" and \
                    (_t(g["start"]) - _t(me_prev["start"])).days <= 21:
                try:
                    m = float(me_prev["home_score"]) - float(me_prev["away_score"])
                    m = m if me_prev["home"] == g[side] else -m
                    if m >= BLOWOUT:
                        hit.append("blowout")
                except (KeyError, ValueError, TypeError):
                    pass
            if dog or (lg == "ncaaf" and SPOT_ANY[0] <= odds <= SPOT_ANY[1]):
                if ff is None:
                    ff = first_fair(g["id"], r, hist_dir) or False
                if ff:
                    f_odds = ff[0] if side == "home" else ff[1]
                    f_opp = ff[1] if side == "home" else ff[0]
                    f_mk = _imp(f_odds) / (_imp(f_odds) + _imp(f_opp))
                    moved = (mk - f_mk) * 100                # + = the price came IN toward this side
                    if dog and moved >= HAMMER_PTS:
                        hit.append("hammered")
                    own = own_of(g, side) if own_of else None
                    if lg == "ncaaf" and own is not None and own - mk >= ENGINE_GAP and moved <= -ENGINE_OUT_PTS:
                        hit.append("engine")
            if not hit:
                continue
            hit = [h for h in hit if lg in SPOTS[h][2]]
            if any_dog and dog and not hit:
                hit = ["best"]                               # the minimum-one week: the engine's best weighed dog
            if not hit or not dog:
                continue                                     # (10/1 price-path study: a favorite's price only gets
                #                                              worse through the week - favorites on game day, never
                #                                              early; a dog's only shortens - dogs early. NFL 6 of 7
                #                                              seasons, college 6 of 7, 2026 too)
            own = own_of(g, side) if own_of else None
            if own is None or own < mk - SPOT_FIGHT:
                continue                                     # no engine read, or the engine's read is fighting it
            fades = _fades(sched, g, side, lg, et)
            extra = lead_weights(games, g, side, other, lg, own, mk) if dog else 0.0
            gap = own - mk                                   # (10/1 audit) the engine's read over the price, capped like
            if gap * 100 > sports_own_cap():                 # the game-day dog score: big reads are traps - 12 pts at
                gap = 0.0 if lg in ("nfl", "nba") else sports_own_cap() / 100   # most, none past 12 in the NFL
            total = round(gap + sum(SPOT_WEIGHT[h] for h in hit) + sum(FADE_WEIGHT[f] for f in fades) + extra, 4)
            if total < (0.0 if any_dog else SPOT_MIN_TOTAL):
                continue                                     # everything weighed together doesn't say value
            main = max(hit, key=lambda h: SPOTS[h][1])
            whys = spot_why(sched, g, side, other, lg, main, now, own, odds)
            out.append({"game_id": g["id"], "league": lg, "side": side, "team": g[f"{side}_name"], "opp": g[f"{other}_name"],
                        "odds": odds, "opp_odds": opp_odds, "start": g["start"], "spot": main, "spots": hit,
                        "fades": fades, "score": round(total, 4), "why": whys[0], "whys": whys, "mkt": round(mk, 4), "own": round(own, 4),
                        "fair_at": r.strftime("%Y-%m-%dT%H:%MZ") if r else None})
    sides = {}
    for c in out:
        sides.setdefault(c["game_id"], set()).add(c["side"])
    return [c for c in out if len(sides[c["game_id"]]) == 1]   # both sides of one game hit (the engine likes one,
    #                                                             the money hammered the other): they cancel - no play


def sports_own_cap():
    import sports
    return sports.OWN_CAP


LEAD_W = {"win_pct": 0.015, "neutral": 0.015, "win_streak": 0.01, "go4": 0.01, "style": -0.02, "rain": 0.015}
#  rain (10/1 audit - standing on fair prices, never wired till now): college dogs with rain / snow in the forecast,
#  outdoors (0.5+, early_round3's cut) +8.1% on 822, the engine liking them +10.9%, 5 of 6 seasons


def lead_weights(games, g, side, other, lg, own, mk):
    """The believed-but-unproven leads, weighed in (the owner, 10/1: "the engine needs all the good things we found -
    even the ones you couldn't prove - for the early plays too"): a .700+ college dog, a neutral-site dog the engine
    likes, an NFL dog on a 3+ win streak, 4th-down nerve (NFL), college coaching style. Small weights, never a trigger."""
    try:
        import sports
        mo = sports._dog_more(games, g, side, other, lg) or {}
    except Exception:                                        # noqa: BLE001 - extra facts never block a play
        return 0.0
    w = 0.0
    if lg == "ncaaf" and (mo.get("win_pct") or 0) >= 0.70:
        w += LEAD_W["win_pct"]
    if mo.get("neutral") and own > mk:
        w += LEAD_W["neutral"]
    if lg == "nfl" and (mo.get("win_streak") or 0) >= 3:
        w += LEAD_W["win_streak"]
    gap = mo.get("go4_gap")
    if lg == "nfl" and gap is not None:
        import sports_go4
        w += -LEAD_W["go4"] if gap <= sports_go4.GAP_LO else LEAD_W["go4"] if gap >= sports_go4.GAP_HI else 0.0
    if lg == "ncaaf" and (mo.get("conservative") or mo.get("fast")):
        w += LEAD_W["style"]
    try:
        wet = str(g.get("indoor")) != "1" and float(g.get("wx_rain") or 0) >= 0.5
    except (TypeError, ValueError):
        wet = False
    if lg == "ncaaf" and wet:
        w += LEAD_W["rain"]
    return round(w, 4)


def week_start(now):
    """This betting week's start: the latest Tuesday 00:00 PT."""
    loc = now.astimezone(PT)
    d = loc.date() - timedelta(days=(loc.weekday() - 1) % 7)
    return datetime(d.year, d.month, d.day, tzinfo=PT)


def pick_spots(cands, st, now, have=()):
    """The best SPOT_MAX_WEEK a week (the owner, 10/1: "the most confident ones" - two): ranked by the engine's whole
    weighed total (its own read + the spots - the fades), never one factor. Before Tuesday 6 AM PT it waits for the whole slate (the NFL's numbers come after
    Monday night) - unless a play's early window would close first."""
    ws = week_start(now)
    loc = now.astimezone(PT)
    d = loc.date() + timedelta(days=(1 - loc.weekday()) % 7)        # the coming Tuesday (today, on a Tuesday)
    slate = datetime(d.year, d.month, d.day, SPOT_SLATE_HOUR_PT, tzinfo=PT)
    if SPOT_MAX_WEEK is not None and loc.weekday() in (5, 6, 0, 1) and now < slate:   # (a cap: hold for Tuesday's
        #                                                   full slate to rank it - no cap: post it now, before it moves)
        cands = [c for c in cands if c.get("fair_at") and _t(c["fair_at"]) + timedelta(hours=SPOT_WINDOW_H) < slate]
    cands = [c for c in cands if c["game_id"] not in have]   # (10/1 bug check: an already-posted game used a slot)
    taken = sum(1 for p in st.get("picks", []) if p.get("spot") and p.get("posted") and _t(p["posted"]) >= ws)
    room = len(cands) if SPOT_MAX_WEEK is None else max(0, SPOT_MAX_WEEK - taken)
    cands.sort(key=lambda c: -(c.get("score") or 0))          # everything weighed together - the best total first
    return cands[:room]


def min_one(games, st, now, injuries, own_of, have=()):
    """The owner, 10/1: "one minimum, two max." A week with no early play yet: from Wednesday 6 AM PT, the engine's best
    weighed dog (+100..+220, the engine not fighting it, everything weighed - its read, the spots, the fades, the leads)
    for an upcoming game this week, ½u. Never on its own game day; never a total that says it's overpriced."""
    ws = week_start(now)
    if not SPOT_MIN_WEEK:
        return []                                           # (10/1: paused - the owner: "I don't want to force early
        #                                                     plays if the algorithm doesn't believe")
    if sum(1 for p in st.get("picks", []) if p.get("spot") and p.get("posted") and _t(p["posted"]) >= ws) >= SPOT_MIN_WEEK:
        return []                                           # (the week already has its early play)
    loc = now.astimezone(PT)
    if ((loc.weekday() - 1) % 7, loc.hour) < (MIN_ONE_FROM[0] - 1, MIN_ONE_FROM[1]):
        return []                                            # (Tuesday's slate gets the first shot)
    nxt = ws + timedelta(days=7)
    cands = [c for c in spot_scan(games, now, injuries, own_of, any_dog=True)
             if c["game_id"] not in have and _t(c["start"]) < nxt and (c.get("score") or 0) > 0]
    cands.sort(key=lambda c: -(c.get("score") or 0))
    out = cands[:SPOT_MIN_WEEK]                             # the minimum one: the best weighed dog
    out += [c for c in cands[SPOT_MIN_WEEK:SPOT_MAX_WEEK or len(cands)] if c["score"] >= SPOT_MIN_TOTAL]   # a 2nd if it clears
    for c in out:                                           # the normal bar too ("one minimum, two max")
        c["spot"] = "best"                                  # (10/1 audit: a backup pick skipped the spots' own window -
    return out                                              # it counts as the engine's best dog, never in a spot's record)


def spot_record(st):
    """{spot: (won, lost, units)} - each spot's own live record (the owner: the real ones show)."""
    out = {}
    for p in st.get("picks", []):
        if not p.get("spot") or p.get("result") not in ("won", "lost"):
            continue
        w, l_, u = out.get(p["spot"], (0, 0, 0.0))
        uu = units(p)
        if p["result"] == "won":
            out[p["spot"]] = (w + 1, l_, u + uu * (_dec(p["odds"]) - 1))
        else:
            out[p["spot"]] = (w, l_ + 1, u - uu)
    return out


def now_line(p, games):
    """📈 Got it at -> now (the owner, 10/5: "put what we got in the early value plays for and what they move to now"):
    one line under an early card - the price we got, the price now, and what the move means. '' with no price now."""
    g = (games or {}).get(p.get("game_id")) or {}
    if not g or p.get("result") or g.get("status") not in (None, "pre") or not p.get("side") or p.get("odds") is None:
        return ""
    am = lambda o: f"+{o}" if o > 0 else str(o)               # noqa: E731
    if p.get("market") == "total":                           # 🌍 the under: the number (and its price) now
        tot, o = g.get("total"), _int(g.get("under_odds"))
        try:
            tot = float(tot)
        except (TypeError, ValueError):
            return ""
        if o is None:
            return ""
        call = ("🔥 we beat the number" if tot < p["line"] else "👀 the number went up" if tot > p["line"] else "")
        return (f"📈 Got it at {p['line']:g} ({am(p['odds'])}) ➜ now {tot:g} ({am(o)})"
                + (f" · {call}" if call else " · hasn't moved"))
    now_odds = _int(g.get(f"ml_{p['side']}"))
    if now_odds is None:
        return ""
    if now_odds == p["odds"]:
        return f"📈 Got it at {am(p['odds'])} ➜ still {am(now_odds)} · hasn't moved"
    opp = _int(g.get(f"ml_{'away' if p['side'] == 'home' else 'home'}"))
    call = label({**p, "key_out": None}, now_odds, opp)
    return f"📈 Got it at {am(p['odds'])} ➜ now {am(now_odds)}" + (f" · {call}" if call else "")


def html(st, E, now=None, show_units=None, games=None):
    """The box under today's board: the early plays whose game day hasn't come yet (the owner, 9/30: on game day
    they're no longer early plays - they leave the box; no grading shown here)."""
    now = now or datetime.now(timezone.utc)
    if not ON or not st.get("picks"):
        return ""
    today = now.astimezone(PT).date()
    up = sorted((p for p in st["picks"] if not p.get("result") and _t(p["start"]).astimezone(PT).date() > today),
                key=lambda p: p["start"])

    def row(p):
        t = _t(p["start"]).astimezone(PT)
        o = p["odds"]
        tot = p.get("market") == "total"                     # 🌍 a total: 'Under 46.5 (-110)', the game below
        return (f'<div class="evr"><div><b>{E(p["team"])}</b> <small>{"" if tot else "ML"}</small> '
                f'<em>{"+" if o > 0 else ""}{o}</em>'
                f'<span>{"" if tot else "vs "}{E(p["opp"])} · {E(p["league"].upper())}</span>'
                + (f'<span>{E(p.get("why") or SPOTS[p["spot"]][0])}</span>' if p.get("spot") in SPOTS else "") +
                f'<u>{when(p["start"], now)} · game starts at {t.strftime("%-I:%M %p").replace(":00 ", " ")} PT</u>'
                + (f'<span class="evm">{E(now_line(p, games))}</span>' if now_line(p, games) else "")
                + (f'<span>🚑 {E(p["key_out"])} ruled out since we posted it - don\'t chase it</span>' if p.get("key_out") else "")
                + (show_units(units(p), p.get("team", ""), p.get("odds")) if show_units else "") + '</div></div>')
    body = "".join(row(p) for p in up) or \
        '<div class="evn">👀 Watching every new line. The next one posts the second it shows up.</div>'
    rec = spot_record(st)                                    # 🧪 each spot's own live record (the owner, 10/1)
    num = lambda u: f"{u:.2f}".rstrip("0").rstrip(".")      # +0.65u, +1.5u, -1u
    recs = " · ".join(f'{E(SPOTS[k][0])} {w}-{l_} ({"+" if u >= 0 else ""}{num(u)}u)' for k, (w, l_, u) in rec.items()
                      if k in SPOTS)
    return (f'<section class="pk evx" style="--c1:#ff2d2d;--c2:#ff7a00"><div class="pk-h"><span class="pk-i evi">⏰</span>'
            f'<span class="pk-l evt">EARLY VALUE PLAYS</span></div>'
            f'<div class="evb">🔥 GET IT BEFORE THE LINE MOVES 🔥</div>{body}'
            + (f'<div class="evn">🧪 How each spot\'s doing live: {recs}</div>' if recs else "") + '</section>')


def label(p, now_odds, opp_now=None):
    """The game-day row's call (the owner, 9/30): the price came our way = we beat the line; it got bigger and the engine
    still likes it = better price now; bigger and it doesn't = the money went against it; no move = no label.
    opp_now: the other side's price right now (the 10/4 audit: the market's number was read off the opponent's price
    at post time, not today's)."""
    if p.get("key_out"):                                  # our QB / goalie ruled out since we posted
        return f"🚑 {p['key_out'].split(' (')[0]} out - don't chase it"
    if now_odds is None or now_odds == p["odds"]:
        return ""
    if now_odds < p["odds"]:                              # +185 -> +150 / -120: the money came our way
        return "🔥 we beat the line"
    dec = _dec(now_odds)
    opp = _int(opp_now) if opp_now is not None else None
    mkt_now = 1 / dec / (1 / dec + 1 / _dec(opp if opp is not None else _int(p.get("opp_odds")) or -200))
    if p.get("own") is not None and p["own"] - mkt_now >= min(band(b)[0] for b in (passed().get(p["league"]) or [(0.04, 1)])):
        return "💰 better price now"
    return "👀 money went against it"


MOVE_SAY = {   # (10/1, the owner: every row explains the move - "the line moved in our favor, let's go to work")
    "🔥 we beat the line": (
        "We got {t} at {a}, it's {n} now. The line came our way - let's go to work.",
        "{a} when we got in, {n} now. The books moved toward us - we already got the better number.",
        "Grabbed {t} at {a} and the market followed us to {n}. That's beating the line."),
    "💰 better price now": (
        "{t} went from {a} to {n}, and the engine still likes 'em. Line got worse for us, but this still gon' smack.",
        "We took {a}, it's {n} now - a bigger price and our read didn't move. Still riding.",
        "{a} to {n}: the price drifted off us, but the engine still has the edge on {t}."),
    "👀 money went against it": (
        "{a} when we got in, {n} now - the money went the other way. Our number's locked; we see how it plays.",
        "The line ran from {a} to {n} against us. We already got ours - now it's on the field.",
        "Money came in on the other side ({a} to {n}). We're holding {a}."),
    "": (
        "Still {a}, same as when we got in. Nobody's touched this line.",
        "{t} hasn't moved off {a}. The books ain't budging, and neither are we."),
}


def move_say(p, now_odds, call):
    """The plain-words line under a game-day early row: what the price did since we got in, and where that leaves us."""
    if now_odds is None or p.get("result") or call.startswith("🚑"):
        return ""
    pool = MOVE_SAY.get(call) or MOVE_SAY[""]
    am = lambda o: f"+{o}" if o > 0 else str(o)
    line = pool[sum(map(ord, p.get("game_id", "") + p.get("team", ""))) % len(pool)]
    return line.format(t=p.get("team", ""), a=am(p["odds"]), n=am(now_odds))


GRADED_STAYS_H = 3                                        # a graded row stays 3 hours, like every card on the board


def gameday_html(st, games, E, now=None, show_units=None):
    """🎯 WE GOT IN EARLY: on game day the early plays move onto Today's Board - one box, one row each: the price we got
    -> the price now. A graded row stays 3 hours with its ✅ / ❌ (the board's rule), then it's gone."""
    now = now or datetime.now(timezone.utc)
    if not ON:
        return ""
    today = now.astimezone(PT).date()
    rows = []
    for p in sorted(st.get("picks") or [], key=lambda p: p["start"]):
        t = _t(p["start"]).astimezone(PT)
        if t.date() != today:
            continue
        if p.get("result") and p.get("graded_at") and now - _t(p["graded_at"]) > timedelta(hours=GRADED_STAYS_H):
            continue
        g = games.get(p["game_id"]) or {}
        now_odds = _int(g.get(f"ml_{p['side']}")) if not p.get("result") and g.get("status") == "pre" \
            and p.get("market") != "total" else None             # (a total: no price-move call)
        mark = {"won": "✅", "lost": "❌", "push": "➖"}.get(p.get("result"), "")
        other = "away" if p.get("side") == "home" else "home"
        call = mark or label(p, now_odds, g.get(f"ml_{other}") if now_odds is not None else None)
        am = lambda o: f"+{o}" if o > 0 else str(o)
        price = f'<s>{am(p["odds"])}</s>' + (f'<em>➜</em><b>{am(now_odds)}</b>' if now_odds is not None else "")
        tot = p.get("market") == "total"
        rows.append(f'<div class="egr"><div class="egl"><b>{E(p["team"])}</b> <small>{"" if tot else "ML"}</small>'
                    f'<span>{"" if tot else "vs "}{E(p["opp"])} · {E(p["league"].upper())}</span>'
                    f'<u>Today · game starts at {t.strftime("%-I:%M %p").replace(":00 ", " ")} PT</u>'
                    + (f'<span>{E(SPOTS[p["spot"]][0])}</span>' if p.get("spot") in SPOTS else "")
                    + (f'<span>The engine has them at {round(p["own"] * 100)}%</span>'   # a win % only over 55%
                       if (p.get("own") or 0) * 100 > 55 else "")                           # (the owner, 9/30)
                    + (f'<span>{E(move_say(p, now_odds, call))}</span>' if move_say(p, now_odds, call) else "")
                    + (show_units(units(p), p.get("team", ""), p.get("odds")) if show_units else "")
                    + f'</div><div class="egp">{price}{f"<i>{call}</i>" if call else ""}</div></div>')
    if not rows:
        return ""
    return ('<section class="pk gdx" style="--c1:#ff2d2d;--c2:#ff7a00"><div class="pk-h"><span class="pk-i evi">🎯</span>'
            '<span class="pk-l evt">WE GOT IN EARLY</span></div><div class="egh">WE GOT IT AT ➜ NOW</div>'
            + "".join(rows) + '</section>')


PINGS_PATH = os.path.join(sd.DATA, "early_pings.json")
PING_FRESH_MIN = 50                                      # a queue older than this is a past run's: never re-sent


def queue_pings(items, now, path=None):
    """This run's pings (None = the breakthrough ping), written for tools/early_ping.py - it sends them only once the
    live dashboard shows the play (the owner, 9/29-9/30: never a ping for something that's not on the dashboard).
    Written every run, empty when there's nothing, so a past run's pings never go out twice."""
    with open(path or PINGS_PATH, "w") as f:
        json.dump({"at": now.strftime("%Y-%m-%dT%H:%MZ"), "pings": items}, f)


def pending(now, path=None):
    """This run's queued pings (fresh only), or []."""
    try:
        with open(path or PINGS_PATH) as f:
            q = json.load(f)
    except (OSError, ValueError):
        return []
    return q.get("pings") or [] if now - _t(q.get("at") or "2000-01-01T00:00") <= timedelta(minutes=PING_FRESH_MIN) else []


def send_queued(page, now=None, path=None, send_fn=None):
    """-> the pings sent: only a fresh queue, and only plays whose team the live `page` (html text) already shows."""
    now = now or datetime.now(timezone.utc)
    try:
        with open(path or PINGS_PATH) as f:
            q = json.load(f)
    except (OSError, ValueError):
        return []
    if not q.get("pings") or now - _t(q["at"]) > timedelta(minutes=PING_FRESH_MIN):
        return []
    plays = [c for c in q["pings"] if c]
    box = page[page.find("EARLY VALUE PLAYS"):] if "EARLY VALUE PLAYS" in page else ""
    box = box[:box.find("</section>")] if "</section>" in box else box   # (10/2 audit: the box only, never the
    #                                                                       results further down the page)
    if not plays or not all(c["team"] in box for c in plays):
        return []                                        # not live yet: wait (the caller checks again)
    send_fn = send_fn or send
    for c in q["pings"]:
        send_fn(c)
    return q["pings"]
