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
LEARN_Y = 3                             # the engine for these learns on the last 3 seasons only: the owner's call
                                        # (9/30: "the sports have changed"), and the exam agreed - NBA and college
                                        # football only pass it learning recent, the NFL passes both ways
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")   # every sport takes the exam, 3 times a day
BANDS = ((0.04, 0.08, 100, 280), (0.08, 1.0, 100, 280),   # (how far the engine's own read beats the early price,
         (0.08, 0.12, 100, 149))                          #  the dog's price range): +4..8, +8 or more, and short dogs
                                                          # +100..+149 at +8..12 (9/30, with who's pitching / in net:
                                                          # MLB 4 of 4 seasons +11.5%, NHL 3 of 3 +7.4%)
PASS_N, PASS_SEASON_N, PASS_ROI = 60, 20, 0.02   # a band passes: 60+ dogs, 20+ in each exam season, +2% in EACH
# what passed on 9/30 (used until the first study run writes early_exam.json)
EARLY = {"nfl": [(0.04, 0.08), (0.08, 1.0)], "nba": [(0.04, 0.08)]}
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
                for o, won, ow, m in ((a, hs > as_, own, mk), (b, as_ > hs, 1 - own, 1 - mk)):
                    if not DOG_MIN <= o <= DOG_MAX:
                        continue
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
            if inj and sd.team_key_out(inj, g[side], g[f"{side}_name"], lg):
                continue                             # a key player out on OUR side: the ratings can't see it
            if inj and sd.team_unsure(inj, g[side], g[f"{side}_name"], lg):
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
    have = {p["game_id"] for p in st["picks"]}
    new = []
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
    watch(st, games, injuries)
    grade(st, games)
    save(st, path)
    return new


def watch(st, games, injuries):
    """A posted play's key player (QB, goalie...) ruled out after we posted: the price blows up for a reason the early
    read never saw. The play itself never changes (the owner's rule) - its rows say it plain: don't chase it."""
    for p in st["picks"]:
        g = games.get(p["game_id"])
        if p.get("sp") and g and not p.get("result") and g.get(f"sp_{p['side']}") and g[f"sp_{p['side']}"] != p["sp"]:
            p["key_out"] = f"{p['sp']} (SP)"                 # the owner, 9/30: a last-minute pitcher swap blows up the
            continue                                         # line - our starter isn't going: don't chase it
        inj = (injuries or {}).get(p["league"])
        if p.get("result") or not g or g.get("status") != "pre" or inj is None:
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
            if g and g.get("status") in ("void", "postponed", "canceled", "cancelled"):
                p["result"] = "void"
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, ValueError):
            continue
        us, them = (hs, as_) if p["side"] == "home" else (as_, hs)
        p["result"] = "won" if us > them else "lost" if us < them else "push"
        p["graded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        p["score"] = f'{g["away_name"]} {g["away_score"]} @ {g["home_name"]} {g["home_score"]}'


def record(st):
    ps = [p for p in st.get("picks", []) if p.get("result") in ("won", "lost")]
    w = sum(p["result"] == "won" for p in ps)
    units = sum((p["odds"] / 100) if p["result"] == "won" else -1 for p in ps)
    return {"won": w, "lost": len(ps) - w, "units": round(units, 2)}


LAUNCH = ("🚨 MAJOR ENGINE BREAKTHROUGH",                     # the owner's pick (#1), 9/30 - sent once, with the first play
          "We just found an edge on underdogs: get in early before the line moves. 🔥 Most plays start next week.")


def ping_text(c):
    """The push: short, the price front and center (it's taken before it moves). None = the launch ping."""
    if c is None:
        return LAUNCH
    t = _t(c["start"]).astimezone(PT)
    when = f'{t.strftime("%A")}, game starts at {t.strftime("%-I:%M %p").replace(":00 ", " ")} PT'
    return (f"⏰ EARLY VALUE PLAY: {c['team']} +{c['odds']}",
            f"{c['team']} ML +{c['odds']} vs {c['opp']}. {when}. Get it before the line moves.")


def send(c):
    title, body = ping_text(c)
    sd.web_push(None, title, body, ref=f"early:{c['game_id']}" if c else "early:launch")


def html(st, E, now=None):
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
        return (f'<div class="evr"><div><b>{E(p["team"])}</b> <small>ML</small> <em>+{p["odds"]}</em>'
                f'<span>vs {E(p["opp"])} · {E(p["league"].upper())}</span>'
                f'<u>{t.strftime("%A")} · game starts at {t.strftime("%-I:%M %p").replace(":00 ", " ")} PT</u>'
                + (f'<span>🚑 {E(p["key_out"])} ruled out since we posted it - don\'t chase it</span>' if p.get("key_out") else "")
                + '</div></div>')
    body = "".join(row(p) for p in up) or \
        '<div class="evn">👀 Watching every new line. The next one posts the second it shows up.</div>'
    return (f'<section class="pk evx" style="--c1:#ff2d2d;--c2:#ff7a00"><div class="pk-h"><span class="pk-i evi">⏰</span>'
            f'<span class="pk-l evt">EARLY VALUE PLAYS</span></div>'
            f'<div class="evb">🔥 GET IT BEFORE THE LINE MOVES 🔥</div>{body}</section>')


def label(p, now_odds):
    """The game-day row's call (the owner, 9/30): the price came our way = we beat the line; it got bigger and the engine
    still likes it = better price now; bigger and it doesn't = the money went against it; no move = no label."""
    if p.get("key_out"):                                  # our QB / goalie ruled out since we posted
        return f"🚑 {p['key_out'].split(' (')[0]} out - don't chase it"
    if now_odds is None or now_odds == p["odds"]:
        return ""
    if now_odds < p["odds"]:                              # +185 -> +150 / -120: the money came our way
        return "🔥 we beat the line"
    dec = _dec(now_odds)
    mkt_now = 1 / dec / (1 / dec + 1 / _dec(_int(p.get("opp_odds")) or -200))
    if p.get("own") is not None and p["own"] - mkt_now >= min(band(b)[0] for b in (passed().get(p["league"]) or [(0.04, 1)])):
        return "💰 better price now"
    return "👀 money went against it"


GRADED_STAYS_H = 3                                        # a graded row stays 3 hours, like every card on the board


def gameday_html(st, games, E, now=None):
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
        now_odds = _int(g.get(f"ml_{p['side']}")) if not p.get("result") and g.get("status") == "pre" else None
        mark = {"won": "✅", "lost": "❌", "push": "➖"}.get(p.get("result"), "")
        call = mark or label(p, now_odds)
        am = lambda o: f"+{o}" if o > 0 else str(o)
        price = f'<s>{am(p["odds"])}</s>' + (f'<em>➜</em><b>{am(now_odds)}</b>' if now_odds is not None else "")
        rows.append(f'<div class="gr"><div class="gl"><b>{E(p["team"])}</b> <small>ML</small>'
                    f'<span>vs {E(p["opp"])} · {E(p["league"].upper())}</span>'
                    f'<u>Today · game starts at {t.strftime("%-I:%M %p").replace(":00 ", " ")} PT</u>'
                    + (f'<span>The engine has them at {round(p["own"] * 100)}%</span>' if p.get("own") else "")
                    + f'</div><div class="gp">{price}{f"<i>{call}</i>" if call else ""}</div></div>')
    if not rows:
        return ""
    return ('<section class="pk gdx" style="--c1:#ff2d2d;--c2:#ff7a00"><div class="pk-h"><span class="pk-i evi">🎯</span>'
            '<span class="pk-l evt">WE GOT IN EARLY</span></div><div class="gh">WE GOT IT AT ➜ NOW</div>'
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
    if not plays or not all(c["team"] in box for c in plays):
        return []                                        # not live yet: wait (the caller checks again)
    send_fn = send_fn or send
    for c in q["pings"]:
        send_fn(c)
    return q["pings"]
