"""Offline tests for the sports engine (no network): ESPN parsing, model tuning, the board rules,
grading. Run: python sports_test.py"""
import math
import os
import random
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

import sports
import sports_comeback as sc
import sports_data as sd
import sports_model as sm
import sports_live
import sports_players as sp


def espn_event(eid, home, away, start, state="pre", hs=None, as_=None, ml=(-130, 110), spread=None, nested=False):
    comp = {"competitors": [
        {"homeAway": "home", "team": {"id": home, "shortDisplayName": f"T{home}"}, "score": str(hs or 0)},
        {"homeAway": "away", "team": {"id": away, "shortDisplayName": f"T{away}"}, "score": str(as_ or 0)}],
        "status": {"type": {"state": state, "completed": state == "post", "name": "STATUS_FINAL" if state == "post" else "STATUS_SCHEDULED"}}}
    if ml:
        if nested:
            comp["odds"] = [{"moneyline": {"home": {"open": {"odds": "-120"}, "close": {"odds": f"{ml[0]:+d}"}},
                                           "away": {"open": {"odds": "+100"}, "close": {"odds": f"{ml[1]:+d}"}}},
                             "pointSpread": {"home": {"close": {"line": f"{spread:+g}", "odds": "-110"}},
                                             "away": {"close": {"line": f"{-spread:+g}", "odds": "-110"}}} if spread is not None else {}}]
        else:
            comp["odds"] = [{"homeTeamOdds": {"moneyLine": ml[0], "spreadOdds": -105}, "awayTeamOdds": {"moneyLine": ml[1], "spreadOdds": -115},
                             "spread": spread}]
    return {"id": eid, "date": start, "competitions": [comp]}


def test_parse():
    p = {"events": [espn_event("1", "10", "20", "2026-09-27T17:00Z", ml=(-150, 130), spread=-3.5),
                    espn_event("2", "30", "40", "2026-09-26T17:00Z", "post", 24, 17, ml=None),
                    espn_event("3", "50", "60", "2026-09-27T20:00Z", ml=(120, -140), spread=2.5, nested=True)]}
    g = {r["id"]: r for r in sd.parse_scoreboard("nfl", p)}
    a = g["nfl:1"]
    assert a["ml_home"] == -150 and a["ml_away"] == 130 and a["spread_home"] == -3.5 and a["spread_home_odds"] == -105
    assert g["nfl:2"]["status"] == "final" and g["nfl:2"]["home_score"] == 24 and g["nfl:2"]["ml_home"] == ""
    c = g["nfl:3"]
    assert c["ml_home"] == 120 and c["ml_away"] == -140 and c["ml_home_open"] == -120 and c["spread_home"] == 2.5
    assert sd.parse_american("EVEN") == 100 and sd.parse_american("+365") == 365 and sd.parse_american("-3.5") is None
    assert abs(sd.no_vig(-110, -110) - 0.5) < 1e-9


def test_merge_keeps_closing_odds():
    pre = sd.parse_scoreboard("nba", {"events": [espn_event("9", "1", "2", "2026-09-27T17:00Z", ml=(-200, 170))]})[0]
    post = sd.parse_scoreboard("nba", {"events": [espn_event("9", "1", "2", "2026-09-27T17:00Z", "post", 101, 99, ml=None)]})[0]
    g = sd.merge(None, pre, "t0")
    g = sd.merge(g, post, "t1")
    assert g["status"] == "final" and g["ml_home"] == -200 and g["home_score"] == 101 and g["odds_time"] == "t0"


def test_action_network_odds_attach():
    payload = {"games": [{"start_time": "2026-09-25T00:15:00.000Z", "home_team_id": 147, "away_team_id": 151,
                          "teams": [{"id": 151, "full_name": "Atlanta Falcons"}, {"id": 147, "full_name": "Green Bay Packers"}],
                          "odds": [{"book_id": 15, "type": "game", "ml_home": -250, "ml_away": 205, "spread_home": -4.5,
                                    "spread_home_line": -115, "spread_away_line": -104},
                                   {"book_id": 30, "type": "game", "ml_home": -375, "ml_away": 295}]}]}
    rows = sd.parse_an(payload)
    assert rows[0]["ml_home"] == -250 and rows[0]["ml_home_open"] == -375 and rows[0]["spread_home"] == -4.5
    games = {"nfl:1": {"id": "nfl:1", "league": "nfl", "start": "2026-09-25T00:15Z", "home_name": "Packers", "away_name": "Falcons",
                       "ml_home": "", "ml_away": "", "ml_home_open": "", "ml_away_open": "", "spread_home": ""},
             "nfl:2": {"id": "nfl:2", "league": "nfl", "start": "2026-09-25T00:15Z", "home_name": "Bears", "away_name": "Lions",
                       "ml_home": "", "ml_away": "", "ml_home_open": "", "ml_away_open": "", "spread_home": ""}}
    assert sd.attach_an(games, "nfl", rows) == 1
    g = games["nfl:1"]
    assert g["ml_home"] == -250 and g["ml_away_open"] == 295 and g["spread_away_odds"] == -104
    assert games["nfl:2"]["ml_home"] == ""
    assert abs(sm.line_move(g)) > 0.1                  # opener -375 -> close -250: the market moved toward Atlanta


def test_preseason_ignored_and_key_injuries():
    ev = espn_event("7", "1", "2", "2026-08-22T17:00Z", "post", 26, 3, ml=None)
    ev["season"] = {"year": 2026, "type": 1}
    pre = sd.parse_scoreboard("nfl", {"events": [ev]})[0]
    assert pre["stype"] == "1"
    games = {pre["id"]: pre}
    assert sm.finals(games, "nfl") == [], "preseason results never move the ratings"
    inj = sd.parse_injuries({"injuries": [{"id": "19", "displayName": "New York Giants", "injuries": [
        {"status": "Injured Reserve", "athlete": {"displayName": "Jaxson Dart", "position": {"abbreviation": "QB"}}},
        {"status": "Questionable", "athlete": {"displayName": "Some Guard", "position": {"abbreviation": "G"}}}]}]})
    assert [r[0] for r in sd.team_key_out(inj, "19", "Giants", "nfl")] == ["Jaxson Dart"]
    assert sd.team_unsure(inj, "19", "Giants", "nfl") == []          # a questionable guard isn't a QB
    assert sd.team_injuries(inj, "19", "Giants") == []               # IR isn't counted as a fresh absence


def test_never_back_injured_side():
    games, _ = fake_league("nfl", days=120)
    model = {"params": {}, "log": []}
    sm.tune_all(games, model)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
    g = {**games["nfl:1"], "id": "nfl:x", "status": "pre", "home": "3", "away": "4", "home_name": "Giants",
         "away_name": "Titans", "home_score": "", "away_score": "", "start": "2026-09-27T20:00Z",
         "ml_home": "-130", "ml_away": "110", "ml_home_open": "-130", "ml_away_open": "110", "stype": "2"}
    games[g["id"]] = g
    row = lambda n, pos, st: {"status": st, "athlete": {"displayName": n, "position": {"abbreviation": pos}}}
    inj = {"nfl": sd.parse_injuries({"injuries": [
        {"id": "3", "displayName": "New York Giants", "injuries": [row("Jaxson Dart", "QB", "Injured Reserve")]},
        {"id": "4", "displayName": "Tennessee Titans", "injuries": [row("A", "WR", "Out")]}]})}
    cs = [c for c in sports.candidates(games, model, now, now.astimezone(sports.PT).date(), inj)
          if c["game_id"] == "nfl:x" and c["market"] == "ml"]
    for c in cs:     # starter out: the market prices the backup; the ratings (which think the starter plays) don't count
        assert abs(c["p"] - c["p_market"]) < 1e-9, (c["team"], c["p"], c["p_market"])
    assert not any(sports.good(c) for c in cs), "no fake edge from ratings that assume the starter plays"
    inj["nfl"]["3"] = []                                     # Giants healthy, Titans 2 more out
    inj["nfl"]["4"] = [("A", "WR", "Out"), ("B", "CB", "Out")]
    sides = {c["team"] for c in sports.candidates(games, model, now, now.astimezone(sports.PT).date(), inj)
             if c["game_id"] == "nfl:x"}
    assert "Titans" not in sides and "Giants" in sides, "never back the more banged-up team"


def test_player_stats():
    nfl = {"boxscore": {"players": [{"team": {"id": "1"}, "statistics": [{"name": "passing", "keys": [
        "completions/passingAttempts", "passingYards", "yardsPerPassAttempt", "passingTouchdowns", "interceptions"],
        "athletes": [{"athlete": {"displayName": "Backup Guy"}, "stats": ["2/3", "12", "4.0", "0", "0"]},
                     {"athlete": {"displayName": "Baker Mayfield"}, "stats": ["18/31", "201", "6.5", "0", "2"]}]}]}]}}
    rows = sp.parse_box("nfl", "nfl:1", "2026-09-20T17:00Z", nfl)
    assert rows[0]["player"] == "Baker Mayfield" and rows[0]["int"] == 2 and rows[0]["att"] == 31
    mlb = {"boxscore": {"players": [{"team": {"id": "8"}, "statistics": [
        {"keys": ["hits-atBats"], "athletes": [{"athlete": {"displayName": "Hitter"}, "stats": ["1-4"]}]},
        {"keys": ["fullInnings.partInnings", "hits", "runs", "earnedRuns", "walks", "strikeouts"],
         "athletes": [{"athlete": {"displayName": "Ace"}, "stats": ["6.2", "3", "1", "1", "1", "9"]},
                      {"athlete": {"displayName": "Reliever"}, "stats": ["2.1", "1", "0", "0", "0", "3"]}]}]}]}}
    r = sp.parse_box("mlb", "mlb:1", "2026-09-20T17:00Z", mlb)[0]
    assert r["player"] == "Ace" and abs(r["ip"] - 6.667) < 0.01 and r["k"] == 9
    nhl = {"boxscore": {"players": [{"team": {"id": "3"}, "statistics": [{"name": "goalies", "keys": ["goalsAgainst", "shotsAgainst"],
        "athletes": [{"athlete": {"displayName": "Wall"}, "stats": ["1", "35"]}]}]}]}}
    assert sp.parse_box("nhl", "nhl:1", "2026-09-20T17:00Z", nhl)[0]["sa"] == 35
    # form lines + key player edge
    qb = [{"gid": f"nfl:{i}", "start": f"2026-09-{10 + i}T17:00Z", "team": "1", "player": "Baker Mayfield", "role": "QB",
           "att": 30, "cmp": 18, "yds": 190, "td": 0, "int": 2} for i in range(2)]
    txt, mood = sp.form_line("nfl", "Baker Mayfield", qb, "2026-09-27T17:00Z")
    assert mood == "cold" and "4 picks" in txt
    good_qb = [{**r, "team": "2", "player": "Cooking", "td": 3, "int": 0, "yds": 320} for r in qb]
    games = {"nfl:x": {"id": "nfl:x", "league": "nfl", "status": "pre", "start": "2026-09-27T17:00Z", "home": "2", "away": "1"}}
    edge = sp.key_edges(games, {"nfl": sorted(qb + good_qb, key=lambda r: r["start"])})["nfl:x"]
    assert edge > 0.5, "home QB playing much better -> positive home edge"


def test_altitude_cold_weather():
    e = sm.Elo(20, 40, "nfl")
    base = {"league": "nfl", "status": "final", "home_score": "20", "away_score": "10", "neutral": "0", "stype": "2"}
    # each team's usual home spot: Denver high and cold-ish, Miami low and warm
    e.update({**base, "id": "a", "start": "2026-09-07T20:00Z", "home": "DEN", "away": "X", "elev": "1600", "wx_temp": "40",
              "indoor": "0"})
    e.update({**base, "id": "b", "start": "2026-09-07T20:00Z", "home": "MIA", "away": "Y", "elev": "2", "wx_temp": "85",
              "indoor": "0"})
    g = {**base, "id": "c", "status": "pre", "start": "2026-12-20T20:00Z", "home": "DEN", "away": "MIA", "elev": "1600",
         "wx_temp": "20", "wx_wind": "25", "wx_rain": "0", "indoor": "0"}
    f = e.features(g)
    assert f["alt"] > 1.0, "Miami's in thin air in Denver"
    assert f["cold"] > 0.5, "Miami's freezing"
    assert f["weather"] != 0, "25 mph winds count"
    dome = {**g, "wx_temp": "", "wx_wind": "", "wx_rain": "", "indoor": "1"}
    assert e.features(dome)["cold"] == 0 and e.features(dome)["weather"] == 0


def fake_league(league, teams=16, days=300, seed=1):
    """A season where true strength drives results, and the market prices it with some noise."""
    rnd = random.Random(seed)
    strength = {str(i): rnd.gauss(0, 120) for i in range(teams)}
    games = {}
    t0 = datetime(2026, 9, 27, tzinfo=timezone.utc) - timedelta(days=days)
    n = 0
    for d in range(days):
        ids = list(strength)
        rnd.shuffle(ids)
        for h, a in zip(ids[::2][:3], ids[1::2][:3]):
            n += 1
            diff = strength[h] - strength[a] + 40
            p = 1 / (1 + 10 ** (-diff / 400))
            pm = min(0.9, max(0.1, p + rnd.gauss(0, 0.06)))
            mlh = -round(100 * pm / (1 - pm) * 1.02) if pm >= 0.5 else round(100 * (1 - pm) / pm * 0.98)
            mla = round(100 * pm / (1 - pm) * 0.98) if pm >= 0.5 else -round(100 * (1 - pm) / pm * 1.02)
            mlh = mlh if abs(mlh) >= 100 else (100 if mlh > 0 else -101)
            mla = mla if abs(mla) >= 100 else (100 if mla > 0 else -101)
            win = rnd.random() < p
            margin = max(1, int(abs(rnd.gauss(diff / 25, 10)))) * (1 if win else -1)
            hs, as_ = (20 + max(0, margin), 20 - min(0, margin))
            start = (t0 + timedelta(days=d, hours=18)).strftime("%Y-%m-%dT%H:%MZ")
            gid = f"{league}:{n}"
            games[gid] = {"id": gid, "league": league, "start": start, "status": "final", "home": h, "away": a,
                          "home_name": f"H{h}", "away_name": f"A{a}", "home_score": str(hs), "away_score": str(as_),
                          "ml_home": str(mlh), "ml_away": str(mla), "odds_time": "", "neutral": "0",
                          "ml_home_open": str(mlh), "ml_away_open": str(mla), "spread_home": str(-round(diff / 25 * 2) / 2),
                          "spread_home_odds": "-110", "spread_away_odds": "-110", "inj_home": "", "inj_away": ""}
    return games, strength


def test_tune_learns():
    games, _ = fake_league("nba")
    p = sm.tune(games, "nba")
    assert p and p["accuracy"] > 0.6, p
    assert p["logloss_own"] < 0.69 and 0.0 <= p["trust"] <= 1.0 and p["sigma"] > 0
    model = {"params": {}, "log": []}
    sm.tune_all(games, model)
    assert model["params"]["nba"]["games"] == len(games) and model["log"][-1]["change"] == "first tune"


def _cand(gid, odds, p, market="ml", line=None, league="mlb"):
    dec = sd.decimal(odds)
    return {"game_id": gid, "league": league, "side": "home", "team": gid, "opp": "x", "home": True,
            "start": "2026-09-27T23:00Z", "reasons": ["the stronger team"], "market": market, "line": line, "odds": odds,
            "dec": dec, "p": p, "p_market": 1 / dec, "edge": p * dec - 1}


def test_board_rules():
    c = [_cand("a", -300, 0.80), _cand("b", -140, 0.62), _cand("c", 150, 0.43), _cand("d", 180, 0.39),
         _cand("e", 220, 0.34), _cand("f", -115, 0.56), _cand("g", 365, 0.24), _cand("h", 130, 0.46),
         _cand("i", -110, 0.54, "spread", -3.5, "nfl")]
    b = sports.make_board(c)
    for kind in ("two", "three"):
        legs = b[kind]["legs"]
        assert all(sports.good(l) for l in legs), "never a filler leg"
        assert len({l["game_id"] for l in legs}) == len(legs) == (2 if kind == "two" else 3)
        assert all(l["odds"] >= sports.MAX_FAV for l in legs), "no huge favorites"
    assert b["lock"]["legs"][0]["odds"] >= -120 and b["lock"]["legs"][0]["market"] == "ml"
    dog = b["dog"]["legs"][0]
    assert dog["odds"] >= 100 and dog["game_id"] != b["lock"]["legs"][0]["game_id"]
    assert dog["game_id"] == "d", "a big dog needs to be clearly better value than the best regular dog"
    c = [x if x["game_id"] != "g" else _cand("g", 365, 0.30) for x in c]     # now a real shot at great value
    assert sports.make_board(c)["dog"]["legs"][0]["game_id"] == "g"
    slate = [_cand(f"g{i}", -150 + 5 * i, 0.64 - 0.005 * i) for i in range(10)]
    slate += [_cand("big", -475, 0.86), _cand("big", -110, 0.63, "spread", -9.5, "nfl")]   # huge favorite: spread only
    eight = sports.make_board(slate)["eight"]["legs"]
    assert len(eight) == 8 and len({l["game_id"] for l in eight}) == 8 and all(sports.good(l) for l in eight)
    assert all(l["odds"] >= sports.MAX_FAV for l in eight), "no -475 in the 8-leg"
    assert [l for l in eight if l["game_id"] == "big"][0]["market"] == "spread"
    short = slate[:5] + [_cand(f"n{i}", -120, 0.50) for i in range(5)]      # only 5 value legs: still an 8-leg
    short += [_cand("sp", -110, 0.51, "spread", -10.5, "nfl")]              # a no-value big-favorite spread: never filler
    eight = sports.make_board(short)["eight"]["legs"]
    assert len(eight) == 8 and sum(sports.good(l) for l in eight) == 5 and all(l["odds"] >= sports.MAX_FAV for l in eight)
    assert all(l["market"] == "ml" for l in eight if not sports.good(l)), "a spread only gets in as a real value play"
    filler = [_cand("p", 202, 0.32), _cand("q", -115, 0.52), {**_cand("r", 150, 0.45), "reasons": []}]
    b = sports.make_board(filler)
    assert b["two"] is None and b["three"] is None, "no good pair on the slate = no play, never a filler"
    assert b["dog"] is None and b["lock"] is None
    sharp_only = {**_cand("s", 120, 0.50), "edge_own": 0.0}                # value only from the line moving
    assert not sports.good(sharp_only), "sharp money alone can never carry a pick"
    drama = {**_cand("t", 120, 0.465), "our_drama": [{"kind": "coach fired"}]}      # ~2.3% edge
    assert sports.good({**drama, "our_drama": []}) and not sports.good({**drama, "edge": 0.015, "edge_own": 0.015}), \
        "our own drama needs twice the value"
    import sports_news
    assert sports_news.classify("Jets fire head coach after 2-3 start") == ["coach fired"]
    assert sports_news.classify("Star WR leaves team for personal reasons") == ["family/personal"]
    assert sports_news.classify("Rookie scores twice in win") == []


def test_grading():
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    games = {"g1": {"status": "final", "home_score": "24", "away_score": "20", "home_name": "A", "away_name": "B"},
             "g2": {"status": "final", "home_score": "21", "away_score": "24", "home_name": "C", "away_name": "D"}}
    leg = lambda gid, side, market="ml", line=None, odds=150: {"game_id": gid, "side": side, "market": market, "line": line,
                                                               "odds": odds, "dec": sd.decimal(odds), "start": "2026-09-27T17:00Z"}
    picks = [{"status": "open", "stake": 100, "legs": [leg("g1", "home"), leg("g2", "away")], "pnl": 0},
             {"status": "open", "stake": 100, "legs": [leg("g1", "home", "spread", -4.0, -110)], "pnl": 0},
             {"status": "open", "stake": 100, "legs": [leg("g1", "away", "spread", 3.5, -110), leg("g2", "away")], "pnl": 0}]
    sports.grade(picks, games, now)
    assert picks[0]["status"] == "won" and abs(picks[0]["pnl"] - 525) < 0.01      # 2.5 * 2.5 - 1
    assert picks[1]["status"] == "push" and picks[1]["pnl"] == 0
    assert picks[2]["status"] == "lost" and picks[2]["pnl"] == -100


def test_post_when_settled_and_never_change():
    now = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)                 # 5am PT
    games, _ = fake_league("mlb", days=120)
    model = {"params": {}, "log": []}
    sm.tune_all(games, model)
    slate = [(-140, 120, True), (150, -170, False), (-110, -110, True), (260, -320, False), (-125, 105, True),
             (135, -155, True), (120, -140, False), (175, -205, True)]
    for i, (h, a, known) in enumerate(slate):
        gid = f"mlb:up{i}"
        games[gid] = {**games["mlb:1"], "id": gid, "status": "pre", "home": str(2 * i % 16), "away": str((2 * i + 1) % 16),
                      "home_name": f"H{i}", "away_name": f"A{i}", "home_score": "", "away_score": "",
                      "start": (now + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%MZ"),
                      "ml_home": str(h), "ml_away": str(a), "ml_home_open": str(h), "ml_away_open": str(a),
                      "sp_home": "Ace" if known else "", "sp_away": "Ace" if known else ""}
    sd.fetch_injuries = lambda lg: {}
    day = now.astimezone(sports.PT).date()
    picks = []
    sports.post_board(games, model, picks, now, day)
    for p in picks:
        if p["status"] == "open":
            assert all(not l["waiting"] for l in p["legs"]), "posted plays only use settled games"
        else:
            assert p["status"] == "waiting" and any("starting pitcher" in w for w in p["waiting"])
    posted = [dict(p) for p in picks if p["status"] == "open"]
    sports.post_board(games, model, picks, now + timedelta(hours=1), day)
    assert [p for p in picks if p["status"] == "open"] == posted, "a posted play never changes"
    for g in games.values():                                                  # news arrives for one game
        if g["id"] == "mlb:up1":
            g["sp_home"] = g["sp_away"] = "Ace"
    late = now + timedelta(hours=8)                                           # past every deadline (3h before)
    sports.post_board(games, model, picks, late, day)
    assert [p for p in picks if p["status"] == "open"][:len(posted)] == posted
    assert all(p["status"] == "open" for p in picks) and len(picks) == 4
    assert all(not l["waiting"] for p in picks for l in p["legs"])
    kept = [p for p in picks if p["kind"] != "two"]                           # say the 2-leg never went up...
    started = now + timedelta(hours=10, minutes=1)                            # ...once the first game starts, it can't
    assert sports.post_board(games, model, kept, started, day) == [] and all(p["kind"] != "two" for p in kept)


def _check_js(html):
    """The dashboard's scripts must parse (a stray quote once broke the whole live section)."""
    import re
    import subprocess
    if not shutil.which("node"):
        return
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
        path = os.path.join(tempfile.gettempdir(), f"sports_check_{i}.js")
        with open(path, "w") as f:
            f.write(js)
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:500]


def test_full_cycle_offline():
    tmp = tempfile.mkdtemp()
    cwd = os.getcwd()
    try:
        os.chdir(tmp)
        games, _ = fake_league("nhl", days=200)
        now = datetime.now(timezone.utc)
        today = now.astimezone(sports.PT).replace(hour=19, minute=0).astimezone(timezone.utc)
        if today < now + timedelta(minutes=30):
            today = now + timedelta(hours=1)
        for i in range(6):
            gid = f"nhl:up{i}"
            games[gid] = {**games["nhl:1"], "id": gid, "status": "pre", "home": str(2 * i), "away": str(2 * i + 1),
                          "home_score": "", "away_score": "", "start": today.strftime("%Y-%m-%dT%H:%MZ"),
                          "ml_home": str([-140, 120, -110, 160, 250, -125][i]), "ml_away": str([120, -140, -110, -190, -320, 105][i])}
        sd.save_games(games)
        sd.fetch_injuries = lambda lg: {}
        picks = sports.run(fetch=False)
        kinds = {p["kind"] for p in picks}
        assert kinds, "the fake slate has at least one real play"
        assert all(sports.good(l) for p in picks for l in p["legs"]), "every posted leg is a real play"
        assert os.path.exists("docs/sports/index.html")
        html = open("docs/sports/index.html").read()
        assert "TRUST THE ALGORITHM" in html and "LOCK OF THE DAY" in html
        _check_js(html)
        again = sports.run(fetch=False)                  # a second run the same day keeps the board
        assert len(again) == len(picks)
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp)


def _sim_nba(n=3000, seed=7):
    """Simulated NBA seasons with quarter scores: the truth is a normal random walk + the pregame edge."""
    rnd = random.Random(seed)
    games = {}
    for i in range(n):
        p = rnd.uniform(0.2, 0.8)
        mu = 12.0 * sc.phi_inv(p)
        h, a = [], []
        for q in range(4):
            d = rnd.gauss(mu / 4, 6.0)
            base = rnd.randint(22, 30)
            h.append(base + max(0, round(d)))
            a.append(base + max(0, -round(d)))
        if sum(h) == sum(a):
            h[-1] += 1
        ml_h = int(-100 * p / (1 - p)) if p >= 0.5 else int(100 * (1 - p) / p)
        ml_a = int(100 * p / (1 - p)) if p >= 0.5 else int(-100 * (1 - p) / p)
        gid = f"nba:{i}"
        games[gid] = {"id": gid, "league": "nba", "start": f"2024-01-01T{i % 24:02d}:{i % 60:02d}Z{i}", "status": "final",
                      "home": "1", "away": "2", "home_name": "Lakers", "away_name": "Celtics",
                      "home_score": str(sum(h)), "away_score": str(sum(a)), "ml_home": str(ml_h), "ml_away": str(ml_a),
                      "stype": "2", "ls_home": ",".join(map(str, h)), "ls_away": ",".join(map(str, a))}
    return games


def test_comeback_study_and_live_rules():
    games = _sim_nba()
    snaps = sc.snapshots(games, "nba")
    assert len(snaps) == 3 * len(games)
    fit = sc.fit_curve("nba", snaps)
    assert fit["ll"] <= fit["ll_base"]                         # the study never makes the curve worse
    st = {"nba": {"curve": fit, "table": sc.table("nba", snaps)}}
    h = sc.spot(st, "nba", 0.5, 8, True)                        # a favorite down 6-10 at the half
    assert h and h[0] >= sc.MIN_N and 0.05 < h[1] < 0.8 and sc.when("nba", h[2]) == "at the half"
    box = {"period": 3, "clock": "11:00", "total_home_points": 64, "total_away_points": 70,
           "linescore": [{"home_points": 25, "away_points": 30}, {"home_points": 28, "away_points": 30},
                         {"home_points": 11, "away_points": 10}]}
    g = {"id": "nba:x", "home_name": "Lakers", "away_name": "Celtics"}
    # the Lakers were a solid favorite (65%), down 6 early in the 3rd, live at +320: history + better team -> a play
    plays = sports_live.evaluate("nba", g, box, 320, -400, st, 0.65, 0.65, 0.0, "", 1)
    assert len(plays) == 1 and plays[0]["team"] == "Lakers" and plays[0]["odds"] == 320
    pl = plays[0]
    assert "history" in pl["reasons"] and "better" in pl["reasons"]
    assert pl["breakdown"] and pl["breakdown"][0].startswith("📚") and "Lakers" in pl["line"]
    # never minus money live
    assert all(p["odds"] >= 100 for p in sports_live.evaluate("nba", g, box, -120, 100, st, 0.65, 0.65, 0.0, "", 1))
    assert not [p for p in sports_live.evaluate("nba", g, box, -120, 100, st, 0.65, 0.65, 0.0, "", 1) if p["team"] == "Lakers"]
    # a dog coming in (no 'better team', no pregame value, no ball, no momentum): history alone isn't enough
    assert not [p for p in sports_live.evaluate("nba", g, box, 900, -2000, st, 0.35, 0.35, 0.0, "", 1)
                if p["team"] == "Lakers"]
    # a price miles from what the score says (e.g. a favorite +900 in a tied game): the book knows something
    tied = dict(box, total_home_points=70, total_away_points=70)
    assert not [p for p in sports_live.evaluate("nba", g, tied, 900, -2000, st, 0.65, 0.65, 0.0, "", 1) if p["team"] == "Lakers"]
    # ...but a price confirmed by two sources is real, so the value math decides (not the too-far-off filter)
    assert sports_live.evaluate("nba", g, box, 320, -400, st, 0.65, 0.65, 0.0, "", 1, True)
    # the live price comes from the sportsbook (Bovada), cross-checked with Action Network
    gm_ = {"home_name": "Jaguars", "away_name": "Patriots"}
    lines = [{"home": "Jacksonville Jaguars", "away": "New England Patriots", "ml_home": -140, "ml_away": 120}]
    assert sports_live.book_line(lines, gm_) == (-140, 120)
    assert sports_live._clean("Alabama (#8)") == "Alabama"
    assert sports_live.confirmed_line((-140, 120), (None, None)) == (-140, 120)            # the book alone is fine
    assert sports_live.confirmed_line((-140, 120), (-150, 130)) == (-140, 120)             # they agree
    assert sports_live.confirmed_line((-140, 120), (220, -295)) == (None, None)            # a glitch: no price
    assert sports_live.confirmed_line((None, None), (220, -295)) == (None, None)           # no sportsbook line: no play
    # two real sportsbooks: agree = confirmed, one = used unconfirmed, far apart = no price
    assert sports_live.two_books((-145, 110), (-140, 115)) == (-145, 110, True)
    assert sports_live.two_books((None, None), (-140, 115)) == (-140, 115, False)
    assert sports_live.two_books((-145, 110), (220, -295)) == (None, None, False)
    assert sports_live.two_books((None, None), (None, None)) == (None, None, False)
    # live prices: only the LIVE line, never the pregame "game" line
    assert sports_live.live_line({"latest_odds": {"game": {"ml_home": -300, "ml_away": 272}}}) == (None, None)
    assert sports_live.live_line({"latest_odds": {"game": {"ml_home": -300, "ml_away": 272},
                                                  "live": {"ml_home": 110, "ml_away": -130}}}) == (110, -130)
    # the board: max 2 at once, a play that's up keeps its slot while its value holds
    fake = [{"id": i, "edge": e} for i, e in (("a", 0.06), ("b", 0.07), ("c", 0.20))]
    assert [x["id"] for x in sports_live.board(fake, ["a", "b"])] == ["b", "a"]     # "c" waits for a slot
    assert [x["id"] for x in sports_live.board(fake[:1] + fake[2:], ["a", "b"])] == ["a", "c"]   # "b" gone: "c" takes it
    # no study for the sport yet: no bets
    long_shot = dict(box, total_home_points=50)                # down 20: +900 is a lottery ticket, never a play
    assert not [p for p in sports_live.evaluate("nba", g, long_shot, 900, -2000, st, 0.65, 0.65, 0.0, "", 1) if p["team"] == "Lakers"]
    assert sports_live.evaluate("nba", g, box, 320, -400, {}, 0.65, 0.65, 0.0, "", 1) == []



def test_big_favorites_cover_study():
    """Big favorites that win but don't cover: the cover study learns it and the engine stops trusting their spreads."""
    rnd = random.Random(3)
    X, y, off = [], [], []
    for _ in range(3000):
        line = rnd.choice([-3.0, -6.5, -10.5, -14.0, 3.0, 10.5])
        bf = sm.big_fav(line)
        cover = 0.40 if bf > 0 else 0.60 if bf < 0 else 0.50      # big favorites cover only 40%
        X.append([bf])
        y.append(1.0 if rnd.random() < cover else 0.0)
        off.append(0.0)                                            # the plain curve says 50/50
    bfav = sm.fit_logistic_offset(X, y, off, prior=[0.0], lam=4.0)[0]
    assert bfav < -0.2
    params = {"sw": [0.0] * 16, "sigma": 13.0, "strust": 1.0, "bfav": bfav}
    f = {k: 0.0 for k in ("elo_pts", "form", "rest", "b2b", "inj", "key", "revenge", "letdown", "bye", "short", "intl",
                          "alt", "cold", "weather", "travel")}
    g = {"spread_home": "-14"}
    params["sw"][0] = 14.0                                         # the curve expects a 14-point win: a coin flip to cover
    fav = sm.cover_p(params, f, g, "home")
    assert fav < 0.45 and abs(sm.cover_p({**params, "bfav": 0.0}, f, g, "home") - 0.5) < 0.01
    small = {"spread_home": "-3"}                                  # small spreads: no big-favorite correction
    assert sm.cover_p(params, f, small, "home") == sm.cover_p({**params, "bfav": 0.0}, f, small, "home")



def test_tennis():
    import sports_tennis as st
    assert st.surface_of("Roland Garros") == "clay" and st.surface_of("Wimbledon") == "grass" and st.surface_of("US Open") == "hard"
    assert st.to_bo5(0.70) > 0.70 and abs(st.to_bo5(0.5) - 0.5) < 1e-6
    payload = {"events": [{"id": "9", "name": "Madrid Open", "groupings": [
        {"grouping": {"displayName": "Men's Singles"}, "competitions": [
            {"id": "1", "date": "2026-05-01T10:00Z", "round": {"displayName": "Round 1"},
             "status": {"type": {"name": "STATUS_FINAL"}},
             "competitors": [{"athlete": {"id": "11", "displayName": "Carlos Alcaraz"}, "winner": True,
                              "linescores": [{"value": 6}, {"value": 6}]},
                             {"athlete": {"id": "22", "displayName": "Joe Blow"}, "winner": False,
                              "linescores": [{"value": 3}, {"value": 4}]}]}]},
        {"grouping": {"displayName": "Women's Singles"}, "competitions": [{"id": "2"}]}]}]}
    rows = st.parse_espn(payload)
    assert len(rows) == 1 and rows[0]["surface"] == "clay" and rows[0]["winner"] == 1 and rows[0]["done"] == 2
    # the study: a clearly better player shows up in the ratings
    rnd = random.Random(5)
    ms, t0 = {}, datetime(2024, 1, 1, tzinfo=timezone.utc)
    skill = {str(i): rnd.gauss(0, 1) for i in range(30)}
    for i in range(3000):
        a, b = rnd.sample(list(skill), 2)
        pa = 1 / (1 + math.exp(-(skill[a] - skill[b]) * 1.5))
        w = 1 if rnd.random() < pa else 2
        ms[str(i)] = {"id": str(i), "start": (t0 + timedelta(hours=6 * i)).strftime("%Y-%m-%dT%H:%MZ"), "event": "e",
                      "tourney": "Somewhere Open", "round": "R1", "surface": "hard", "bo": "3", "p1": a, "p1_name": f"P {a}",
                      "p2": b, "p2_name": f"Q {b}", "winner": w, "sets1": "6 6", "sets2": "3 3", "status": "STATUS_FINAL", "done": 2}
    rt, w8, rep = st.study(ms, eval_n=500)
    assert rep["acc"] > 0.6, rep
    # the slate: 8 straights, value first, then the likeliest favorites; the parlay = the 3 likeliest
    cands = []
    for i in range(12):
        p = 0.52 + 0.02 * i
        fair = -round(100 * p / (1 - p))
        odds = fair + (40 if i < 3 else -25)                      # 3 value spots, the rest priced too high
        c = {"id": f"m{i}:1", "match": f"m{i}", "p": p, "odds": odds, "dec": sd.decimal(odds)}
        c["edge"] = p * c["dec"] - 1
        cands.append(c)
    picks, parlay = st.pick_slate(cands)
    assert len(picks) == 8 and [c["match"] for c in picks[:3]] == ["m2", "m1", "m0"]
    assert len(parlay) == 3 and parlay[0]["p"] >= parlay[-1]["p"] and all(c in picks for c in parlay)
    # retirements: void before a set is done, the advancer wins after
    m = {**ms["0"], "status": "STATUS_RETIRED", "done": 0}
    slate = [{"picks": [{"id": "0:1", "match": "0", "side": 1, "result": None}], "parlay": None}]
    st.grade({"0": m}, slate)
    assert slate[0]["picks"][0]["result"] == "void"
    slate[0]["picks"][0]["result"] = None
    st.grade({"0": {**m, "done": 1, "winner": 1}}, slate)
    assert slate[0]["picks"][0]["result"] == "won"
    # the WTA reads the women's draw; countries: home crowd + conflict matchups; she/her in women's breakdowns
    wpay = {"events": [{"id": "8", "name": "China Open", "groupings": [{"grouping": {"displayName": "Women's Singles"}, "competitions": [
        {"id": "5", "date": "2026-10-01T06:00Z", "venue": {"fullName": "Beijing, China PR"}, "status": {"type": {"name": "STATUS_SCHEDULED"}},
         "competitors": [{"athlete": {"id": "7", "displayName": "Qinwen Zheng", "flag": {"alt": "China PR"}}},
                         {"athlete": {"id": "8", "displayName": "Elina Svitolina", "flag": {"alt": "Ukraine"}}}]}]}]}]}
    wr = st.parse_espn(wpay, "wta")
    assert len(wr) == 1 and wr[0]["id"] == "wta:5" and wr[0]["bo"] == 3 and st.parse_espn(wpay, "atp") == []
    assert st.is_home(wr[0]["cc1"], wr[0]["venue"], wr[0]["tourney"]) == 1 and st.is_home("Ukraine", wr[0]["venue"], "") == 0
    assert st.conflict("Russia", "Ukraine") and not st.conflict("Spain", "Ukraine")
    bd = st.breakdown({"id": "x", "player": "Qinwen Zheng", "opp": "Elina Svitolina", "surface": "hard", "bo": 3, "value": True,
                       "tour": "wta", "f": {"surface_gap": 0, "fatigue": 0, "form": 0, "h2h": 0, "home": 1}}, None, set())
    assert bd and not any(__import__("re").search(r"\b(he|him|his)\b", x) for x in bd), bd
    # drama on our side: twice the value and never a filler
    dcands = [{"id": "d:1", "match": "d", "p": 0.8, "odds": -350, "dec": sd.decimal(-350), "our_drama": [{"kind": "relationship drama"}]}]
    dcands[0]["edge"] = 0.8 * dcands[0]["dec"] - 1
    assert st.pick_slate(dcands)[0] == []
    # no moneyline shorter than -300; a big favorite only on the game spread, and only as real value
    big = {"id": "b:1", "match": "b", "p": 0.95, "odds": -1200, "dec": sd.decimal(-1200), "market": "ml"}
    big["edge"] = 0.95 * big["dec"] - 1
    sp_ok = {**big, "id": "b:1:sp", "market": "spread", "hcp": -5.5, "odds": -110, "dec": sd.decimal(-110), "p": 0.60}
    sp_ok["edge"] = 0.60 * sp_ok["dec"] - 1
    assert st.pick_slate([big])[0] == []
    assert st.pick_slate([big, sp_ok])[0][0]["market"] == "spread"
    assert st.pick_slate([big, {**sp_ok, "p": 0.50, "edge": 0.5 * sp_ok["dec"] - 1}])[0] == [], "no filler spreads"
    gm = {"3": [4.0, 5.0]}
    assert st.cover_p(gm, 0.9, -5.5, 3) > st.cover_p(gm, 0.7, -5.5, 3)
    fin = {"sets1": "6 6", "sets2": "2 3", "status": "STATUS_FINAL"}
    assert st.margin(fin) == 7
    sl = [{"picks": [{"id": "s:1:sp", "match": "s", "side": 1, "market": "spread", "hcp": -5.5, "result": None}], "parlay": None}]
    st.grade({"s": {**ms["0"], **fin, "winner": 1}}, sl)
    assert sl[0]["picks"][0]["result"] == "won"
    # odds matching by last names, either order
    m2 = {**ms["1"], "p1_name": "Carlos Alcaraz", "p2_name": "Jannik Sinner", "start": "2026-05-01T10:00Z"}
    assert st.price(m2, [{"a": "Jannik Sinner", "b": "Carlos Alcaraz", "a_ml": -150, "b_ml": 130,
                          "start": "2026-05-01T11:00Z"}]) == (130, -150)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
