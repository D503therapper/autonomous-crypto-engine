"""Offline tests for the sports engine (no network): ESPN parsing, model tuning, the board rules,
grading. Run: python sports_test.py"""
import csv
import gzip
import json
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
sports_live.NOTIFY[0] = False                                       # (no real pushes from tests)
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
    slate += [_cand("big", -475, 0.86), _cand("big", -110, 0.63, "spread", -9.5, "nfl"), _cand("dg", 140, 0.47)]
    bd = sports.make_board(slate)
    lock_g = bd["lock"]["legs"][0]["game_id"]
    two = [l["game_id"] for l in bd["two"]["legs"]]
    three = [l["game_id"] for l in bd["three"]["legs"]]
    assert lock_g in two and set(two) <= set(three) and len(set(three)) == 3, "option A: Lock -> 2-leg -> 3-leg ladder"
    dog_g = bd["dog"]["legs"][0]["game_id"]
    assert dog_g not in three, "the Dog is its own pick, never in the parlays"
    four = [l["game_id"] for l in bd["four"]["legs"]]
    assert len(set(four)) == 4 and set(three) <= set(four) and dog_g not in four, "4-leg = the 3-leg + one more, never the Dog"
    assert all(sports.good(l) and l["odds"] >= sports.MAX_FAV for l in bd["four"]["legs"]), "locks + value only, no -475"
    assert sports.make_board([_cand("x1", -140, 0.66), _cand("x2", -145, 0.66)])["lock"], "no -101..-120 lock: go up to -150"
    assert sports.make_board([_cand("x1", -140, 0.70), _cand("x3", -110, 0.60)])["lock"]["legs"][0]["game_id"] == "x3", \
        "the -101..-120 range comes first"
    one = sports.make_board([_cand("mnf", 170, 0.40), dict(_cand("mnf", -205, 0.70), side="away"),
                             dict(_cand("mnf", -110, 0.58, "spread", -4.5, "nfl"), side="away")])
    assert one["lock"] and all(one[k] is None for k in ("solo", "dog", "two", "three", "four")), "one game = that pick is the Lock"
    assert one["lock"]["legs"][0]["market"] == "spread" and sports.leg_tier(one["lock"]["legs"][0]) == "lock", "a -110 spread = LOCK"
    sure_dog = _cand("sd", 120, 0.66)                                        # a dog the engine thinks WINS (66%)
    bs = sports.make_board(slate + [sure_dog])
    assert bs["dog"]["legs"][0]["game_id"] == "sd" and "sd" in [l["game_id"] for l in bs["two"]["legs"]], "a confident Dog can ride"
    likely = _cand("pl", 120, 0.62)                                          # plus money, 62%
    fav = _cand("fv", -110, 0.54)                                            # minus money, only 54%
    val2 = _cand("v2", 150, 0.615)                                           # about as likely as pl, more value
    bl = sports.make_board([likely, fav, val2, _cand("L", -110, 0.66), _cand("D", 250, 0.46)])   # D = the dog
    assert [l["game_id"] for l in bl["two"]["legs"]] == ["L", "v2"], "accuracy first, then the most value"
    short = slate[:5] + [_cand(f"n{i}", -120, 0.50) for i in range(5)]      # only 5 real plays
    assert sports.make_board(short[:3])["four"] is None, "no 4 real plays = no 4-leg that day (never a lean filler)"
    filler = [_cand("p", 130, 0.43), _cand("q", -115, 0.52), {**_cand("r", 150, 0.45), "reasons": []}]
    b = sports.make_board(filler)
    assert all(b[k] is None for k in ("lock", "dog", "two", "three", "four")), "no value = no picks - never a lean on the board"
    # a pick posted earlier is built on, never rebuilt
    fixed = {"lock": bd["lock"]["legs"]}
    assert sports.make_board(slate[3:], fixed=fixed)["two"]["legs"][0]["game_id"] == lock_g
    # confidence tiers: a plus-money pick can be a LOCK when the engine's sure; a parlay is only as sure as its weakest leg
    both = [dict(_cand("g1", -140, 0.66), side="home"), dict(_cand("g1", 130, 0.45), side="away"),
            _cand("g2", -120, 0.60), _cand("g3", -130, 0.62), _cand("g4", 140, 0.46)]
    bb = sports.make_board(both)
    sides = {(l["game_id"], l["side"]) for pk in bb.values() if pk for l in pk["legs"]}
    assert len({g for g, _ in sides}) == len(sides), "never both teams of one game on the same board"
    val = dict(_cand("g9", 150, 0.46), side="away")          # value on the dog...
    weak = dict(_cand("g9", -150, 0.58), side="home")        # ...vs a so-so favorite (no value): value wins
    strong = dict(_cand("g9", -150, 0.61), side="home")      # ...vs a strong lean (61%): the strong lean wins
    assert {c["side"] for c in sports.one_side([val, weak])} == {"away"}, "value takes precedence"
    assert {c["side"] for c in sports.one_side([val, strong])} == {"home"}, "unless the engine has a strong lean on the other side"
    assert sports.leg_tier(_cand("pl", 120, 0.58)) == "value", "plus money is always value - locks are minus money only"
    assert sports.leg_tier(_cand("pt", 110, 0.55)) == "value", "plus money treads lightly: 55% at +110 isn't enough for a lock"
    assert sports.leg_tier(_cand("mn", -120, 0.60)) == "lock", "minus money: 60% at -120 (10% edge) = a lock"
    assert sports.leg_tier(_cand("v", 150, 0.43)) == "value" and sports.leg_tier(_cand("n", -110, 0.50)) == "lean"
    assert sports.pick_tier({"legs": [{"tier": "lock"}, {"tier": "value"}]}) == "value"
    assert sports.pick_tier({"kind": "lock", "tier": "value", "legs": [{"tier": "value"}]}) == "lock", "the Lock of the Day counts as a lock"
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
    assert all(p["status"] == "open" for p in picks) and len(picks) >= 2
    assert all(not l["waiting"] for p in picks for l in p["legs"])
    # picks all day: once a play is graded, a fresh one of the same kind goes up from games that haven't started
    lock = next((p for p in picks if p["kind"] == "lock"), picks[0])
    lock["status"] = "won"
    later = [g for g in games.values() if g["id"].startswith("mlb:up") and g["id"] != lock["legs"][0]["game_id"]]
    for g in later:
        g["start"] = (now + timedelta(hours=14)).strftime("%Y-%m-%dT%H:%MZ")          # the night games
    assert not sports.post_board(games, model, picks, now + timedelta(hours=11), day), \
        "no afternoon replacements: the record is the start-of-day board (ASK THE ENGINE covers the rest)"
    assert lock in picks, "the graded one stays in the results"
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
    box = {"period": 3, "clock": "11:00", "total_home_points": 64, "total_away_points": 67,
           "linescore": [{"home_points": 25, "away_points": 30}, {"home_points": 28, "away_points": 27},
                         {"home_points": 11, "away_points": 10}]}
    g = {"id": "nba:x", "home_name": "Lakers", "away_name": "Celtics"}
    # the Lakers were a solid favorite (65%), down 3 early in the 3rd, live at +200: history + better team -> a play
    plays = sports_live.evaluate("nba", g, box, 200, -250, st, 0.65, 0.65, 0.0, "", 1)
    assert len(plays) == 1 and plays[0]["team"] == "Lakers" and plays[0]["odds"] == 200
    # accuracy first: never a new live bet longer than +250, never under a 40% chance
    assert not sports_live.evaluate("nba", g, box, 320, -400, st, 0.65, 0.65, 0.0, "", 1), "no +320 live shots"
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
    assert sports_live.evaluate("nba", g, box, 200, -250, st, 0.65, 0.65, 0.0, "", 1, True)
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
    assert sports_live.two_books((-145, 110), (-140, 115)) == (-140, 115, True)        # Bovada's price, confirmed
    assert sports_live.two_books((None, None), (-140, 115)) == (-140, 115, False)      # Bovada alone is enough
    assert sports_live.two_books((-145, 110), (None, None)) == (-145, 110, False)      # DraftKings when Bovada has none
    assert sports_live.two_books((-145, 110), (220, -295)) == (220, -295, False)       # books apart: Bovada, unconfirmed
    assert sports_live.two_books((None, None), (None, None)) == (None, None, False)
    assert sports_live.two_books((0, 0), (None, None)) == (None, None, False), "a pulled line (0) is no price"
    # a play that's already up stays while there's any value left, a new one needs 5%+
    thin = None
    for ml in range(120, 400, 5):
        up = sports_live.evaluate("nba", g, box, ml, -ml - 60, st, 0.65, 0.65, 0.0, "", 1, True, ["nba:x:home"])
        if up and 0.0 <= up[0]["edge"] < 0.05:
            thin = ml
            break
    assert thin, "expected a price with a thin (0-5%) edge"
    assert not sports_live.evaluate("nba", g, box, thin, -thin - 60, st, 0.65, 0.65, 0.0, "", 1, True)       # new: not enough
    # ...but a play that's up comes down once the price blows out past +500 (a prayer, not a live bet)
    assert not sports_live.evaluate("nba", g, box, 700, -1100, st, 0.65, 0.65, 0.0, "", 1, True, ["nba:x:home"])
    # halftime in football: whoever didn't take the opening kickoff gets the ball to start the 2nd half
    sports_live.KICK["77"] = "34"                                  # the away team (34) took the opening kickoff
    assert sports_live.second_half_ball("nfl", {"id": "nfl:77", "home": "11", "away": "34"}) == "home"
    assert sports_live.halftime("nfl", {"status_display": "Halftime"}, {"period": 2, "clock": "00:00"})
    assert not sports_live.halftime("nfl", {}, {"period": 2, "clock": "03:10"}) and not sports_live.halftime("nba", {}, {"period": 2, "clock": "0:00"})
    # the team getting the ball to start the 2nd half: counted, and said in the breakdown (never a reason on its own)
    pl = sports_live.evaluate("nba", g, box, 200, -250, st, 0.65, 0.65, 0.0, "", 1, True, (), "home")
    assert pl and "half" in pl[0]["reasons"] and any("2nd" in x or "halftime" in x for x in pl[0]["breakdown"])
    assert not sports_live.substantial([("half", {}), ("better", {})], False)
    # never contradict ourselves: once we're on a side in a game, the other side never goes up
    lg_ = {"plays": {"nfl:9:home": {"date": datetime.now(sports_live.PT).date().isoformat(), "result": None}}}
    assert sports_live.locked_sides(lg_, datetime.now(timezone.utc))["nfl:9"] == "home"
    import json                                               # ...and a pregame pick locks the game too
    tmp, keep = tempfile.mkdtemp(), sd.DATA
    with open(os.path.join(tmp, "picks.json"), "w") as f:
        json.dump([{"date": datetime.now(sports_live.PT).date().isoformat(), "kind": "two", "status": "open",
                    "legs": [{"game_id": "nfl:7", "side": "away"}]}], f)
    sd.DATA = tmp
    try:
        assert sports_live.locked_sides({"plays": {}}, datetime.now(timezone.utc))["nfl:7"] == "away", "live never goes against a pregame pick"
    finally:
        sd.DATA = keep
    # the live feature grades itself: said 45%, hit 20% -> it raises its own bar for new bets
    keep_tune = sports_live.TUNE
    sports_live.TUNE = os.path.join(tempfile.mkdtemp(), "live_tune.json")
    try:
        rows = {f"x:{i}:home": {"posted": f"2026-01-01T{i:02d}:00Z", "p": 0.45, "result": "won" if i < 3 else "lost"} for i in range(15)}
        t = sports_live.self_tune({"plays": rows})
        assert t["min_p"] > sports_live.LIVE_MIN_P and t["hit"] < t["said"], t
    finally:
        sports_live.TUNE = keep_tune
    # the last minutes of a football game: no new play if we can't see who has the ball
    late = {"period": 4, "clock": "1:48", "total_home_points": 16, "total_away_points": 17, "linescore": [], "situation": {}}
    nfl_st = {"nfl": {"curve": {"s": 1.0, "w": 1.0, "m": 0.0, "ll": 0.5}, "table": {}}}
    assert sports_live.evaluate("nfl", {"id": "nfl:1", "home_name": "Colts", "away_name": "Texans"}, late, -250, 212, nfl_st,
                                0.45, 0.45, 0.0, "", 1, True) == []
    # live prices: only the LIVE line, never the pregame "game" line
    assert sports_live.live_line({"latest_odds": {"game": {"ml_home": -300, "ml_away": 272}}}) == (None, None)
    assert sports_live.live_line({"latest_odds": {"game": {"ml_home": -300, "ml_away": 272},
                                                  "live": {"ml_home": 110, "ml_away": -130}}}) == (110, -130)
    # the board: max 2 at once, a play that's up keeps its slot while its value holds
    n = sports_live.MAX_PLAYS
    fake = [{"id": f"p{i}", "edge": 0.06 + 0.001 * i} for i in range(n)] + [{"id": "new", "edge": 0.50}]
    up = [f"p{i}" for i in range(n)]
    assert {x["id"] for x in sports_live.board(fake, up)} == set(up)                           # "new" waits for a slot
    assert "new" in {x["id"] for x in sports_live.board(fake[1:], up)}                          # a slot opens: it takes it
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
    # the slate: only picks we expect to win (55%+) with real value, likeliest first - never filler to reach 8
    cands = []
    for i in range(12):
        p = 0.50 + 0.02 * i
        fair = -round(100 * p / (1 - p)) if p > 0.5 else 100
        odds = fair + (40 if i % 2 == 0 else -25)                 # every other one is value
        c = {"id": f"m{i}:1", "match": f"m{i}", "p": p, "odds": odds, "dec": sd.decimal(odds)}
        c["edge"] = p * c["dec"] - 1
        cands.append(c)
    picks, parlay = st.pick_slate(cands)
    assert picks and all(c["p"] >= st.MIN_P and c["edge"] >= st.MIN_EDGE for c in picks), "likely to win AND value"
    assert [c["p"] for c in picks] == sorted((c["p"] for c in picks), reverse=True) and len(picks) < 8, "no filler"
    assert len(parlay) == 3 and parlay[0]["p"] >= parlay[-1]["p"] and all(c in picks for c in parlay)
    mixed = [dict(c, id=f"w{i}", match=f"w{i}", tour="wta", p=0.60, odds=-110, dec=sd.decimal(-110), edge=0.6 * sd.decimal(-110) - 1)
             for i, c in enumerate(cands[:4])]
    mixed += [dict(c, id=f"m{i}", match=f"m{i}", tour="atp", p=0.70, odds=-110, dec=sd.decimal(-110), edge=0.7 * sd.decimal(-110) - 1)
              for i, c in enumerate(cands[:8])]
    pk, _ = st.pick_slate(mixed)
    assert sum(c["tour"] == "wta" for c in pk) == 4 and len(pk) == 8, "men's and women's even when both have real picks"
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



def test_hockey_line_first():
    g = {"ml_home": "-120", "ml_away": "100"}
    m = sm.market_p(g)
    params = {"hockey": {"b2b": 0.12}, "w": [0.0] * 20, "trust": 0.5, "move_w": 0.0}
    assert abs(sm.final_p(params, {"b2b": 0.0}, g) - m) < 1e-9, "hockey: the line itself, no own-model tilt"
    assert sm.final_p(params, {"b2b": 1.0}, g) > m, "...plus the back-to-back edge the study proved"


def test_no_game_twice_in_a_parlay():
    import sys as _s
    _s.path.insert(0, "tools")
    import merge_json
    leg = {"game_id": "mlb:1", "team": "Marlins"}
    p = {"date": "d", "kind": "eight", "status": "open", "posted": "x", "legs": [leg, {"game_id": "mlb:2"}, dict(leg)]}
    out = merge_json.merge_picks([p], [])
    assert [l["game_id"] for l in out[0]["legs"]] == ["mlb:1", "mlb:2"], "the Marlins never show up twice"


def test_ats_disagreement():
    import sports_ats
    st = {"nfl": {"proven": True, "b": -0.07}}
    g = {"ml_home": "164", "ml_away": "-198", "spread_home": "3.5"}          # Bears (home) +3.5, ML says Eagles by ~5.5
    assert sports_ats.adjust(st, "nfl", g, 0.5) > 0.5, "the moneyline says more than the spread: the dog covers more"
    assert sports_ats.adjust({"nfl": {"proven": False, "b": -0.07}}, "nfl", g, 0.5) == 0.5, "unproven: no nudge"


def test_lines_study():
    import sports_lines
    rnd = random.Random(3)
    rs = []
    for _ in range(4000):                                     # truth: P(win by 2+) = sigmoid(-1 + 1.2*logit(p) + 0.1*home)
        x, h = rnd.uniform(-1.2, 1.2), rnd.randint(0, 1)
        rs.append((x, h, 1 if rnd.random() < 1 / (1 + math.exp(-(-1 + 1.2 * x + 0.1 * h))) else 0))
    w = sports_lines.fit(rs)
    assert abs(w["a"] + 1) < 0.25 and abs(w["b"] - 1.2) < 0.3 and w["ll"] < w["ll_base"], w
    st = {"nhl": w}
    fav = sports_lines.cover(st, "nhl", 0.62, "home", -1.5)
    dog = sports_lines.cover(st, "nhl", 0.62, "away", 1.5)
    assert 0 < fav < 0.62 and dog > 0.38 and abs(fav + dog - 1) < 1e-9, "-1.5 covers less often than a win; +1.5 is the rest"


def test_halves_study():
    import sports_halves as sh
    games = _sim_nba()
    st = sh.study(games, os.path.join(tempfile.gettempdir(), "halves_test.json"))["nba"]
    assert st["games"] == len(games) and 0.3 < st["share_1h"] < 0.7 and 0.3 < st["share_2h"] < 0.7
    assert 0.5 < st["leader_wins"] <= 1.0
    assert "halves study: nba" in sh.summary({"nba": st})
    import sports_dashboard as dash
    e = {"team": "Texans", "league": "nfl", "side": "away", "score_at_post": "Texans 7 @ Colts 10", "clock_at_post": "Q2 3:00",
         "result": "won", "odds": 185, "best_odds": 300}
    assert "+300" in dash._live_story(e), "a live bet that cashed after its line ran long says so"

def test_leans_through_the_day():
    """Afternoon LEANS: the likeliest sides on games we're not already on, each game once - even with no value."""
    assert sports.MAX_REPLACEMENTS > 0
    mk = lambda gid, p, odds: {"game_id": gid, "league": "mlb", "side": "home", "team": gid, "market": "ml", "line": None,
                               "odds": odds, "dec": sports.sd.decimal(odds), "p": p, "edge": -0.01, "reasons": ["x"],
                               "start": "2026-09-28T23:00Z", "home": True, "waiting": []}
    cands = [mk("g1", 0.66, -140), mk("g2", 0.64, -130), mk("g3", 0.62, -120), mk("g4", 0.61, -125), mk("g5", 0.59, -115)]
    two = sports.lean([c for c in cands if c["game_id"] != "g1"], "two")
    assert two and two["lean"] and [l["game_id"] for l in two["legs"]] == ["g2", "g3"]
    four = sports.lean(cands, "four")
    assert four and len({l["game_id"] for l in four["legs"]}) == 4
    lock = sports.lean(cands, "lock")
    assert lock and lock["legs"][0]["game_id"] == "g3"          # a lean lock still follows the lock price rule
    big = [dict(c, league="ncaab") for c in cands[:3]] + [dict(cands[4], stype="3")]   # a playoff game beats college
    assert sports.lean(big, "two")["legs"][0]["game_id"] == "g5"
    assert sports.importance(dict(cands[0], league="nfl", start="2026-09-29T00:15Z")) == 2   # Monday night
    print("ok test_leans_through_the_day")


def test_public_splits():
    """Who's betting who: the Action Network splits parse, match our game, and grade the public side."""
    import sports_public as spub
    bi = lambda t, m: {"tickets": {"percent": t}, "money": {"percent": m}}
    payload = {"games": [{"start_time": "2026-09-29T00:15:00.000Z", "home_team_id": 1, "away_team_id": 2, "season": 2026,
                          "teams": [{"id": 1, "full_name": "Chicago Bears"}, {"id": 2, "full_name": "Philadelphia Eagles"}],
                          "markets": {"15": {"event": {
                              "moneyline": [{"side": "home", "odds": 165, "bet_info": bi(6, 8)},
                                            {"side": "away", "odds": -202, "bet_info": bi(94, 92)}],
                              "spread": [{"side": "home", "odds": -106, "value": 3.5, "bet_info": bi(22, 28)},
                                         {"side": "away", "odds": -113, "value": -3.5, "bet_info": bi(78, 72)}]}}}}]}
    rows = spub.parse(payload)
    assert rows and rows[0]["splits"]["sp_away_t"] == 78 and rows[0]["splits"]["ml_home_m"] == 8
    games = {"nfl:9": {"id": "nfl:9", "league": "nfl", "start": "2026-09-29T00:15Z", "home_name": "Bears",
                       "away_name": "Eagles", "status": "final", "home_score": "17", "away_score": "20"}}
    pub = spub.match(games, "nfl", rows)
    assert "nfl:9" in pub
    ev = spub.events(games, pub)
    heavy = [e for e in ev if e[2] == "sp" and e[3] == "public 70%+ of bets"]
    assert heavy and heavy[0][5] is False, ev                     # Eagles by 3: the public's -3.5 did NOT cover
    print("ok test_public_splits")


def test_injury_guards():
    """No injury report = the game waits (never a pick made blind); a status change after posting = an alert."""
    g = {"id": "nfl:1", "league": "nfl", "home": "3", "away": "21", "home_name": "Bears", "away_name": "Eagles",
         "status": "pre"}
    assert "the injury report" in sports.waiting_on(g, {"nfl": None})
    assert "the injury report" not in sports.waiting_on(g, {"nfl": {}})
    assert any("questionable" in w for w in sports.waiting_on(g, {"nfl": {"21": [("Star QB", "QB", "Questionable")]}}))
    leg = {"game_id": "nfl:1", "league": "nfl", "team": "Bears", "opp": "Eagles", "side": "home", "market": "spread",
           "line": 3.5, "odds": -108, "key_seen": {}}
    picks = [{"status": "open", "legs": [leg]}]
    real = sports.sd.fetch_injuries
    try:
        sports.sd.fetch_injuries = lambda lg: {"3": [("Caleb Williams", "QB", "Out")]}
        alerts = sports.injury_watch({"nfl:1": g}, picks, push=False)
    finally:
        sports.sd.fetch_injuries = real
    assert alerts and "Caleb Williams" in alerts[0] and leg["injury_alerts"], alerts
    print("ok test_injury_guards")


def test_one_game_always_picks():
    """Monday/Thursday night (a one-game day) always gets a Pick of the Day - the side closest to value."""
    base = {"game_id": "g1", "league": "nfl", "reasons": [], "start": "2026-09-29T00:15Z", "home": True}
    cands = [{**base, "side": "home", "team": "A", "market": "spread", "line": 3.5, "odds": -108, "dec": 1.926, "p": 0.517, "edge": -0.004},
             {**base, "side": "away", "team": "B", "market": "ml", "line": None, "odds": -198, "dec": 1.505, "p": 0.653, "edge": -0.018}]
    b = sports.make_board(cands)
    assert b["lock"] and b["lock"]["legs"][0]["team"] == "A" and not b["solo"], b     # one-game day: it's the Lock
    print("ok test_one_game_always_picks")


def test_dog_traps():
    """The big study: a dog in a spot the books still overprice is never a real play; a proven price check shifts reads."""
    import sports_dogs
    st = {"nhl": {"traps": ["+140-179|away|on b2b"], "proven": [], "price": {"proven": True, "shifts": {"5": 0.2}}}}
    assert sports_dogs.verdict(st, "nhl", 150, False, "on b2b") == "trap"
    assert sports_dogs.verdict(st, "nhl", 150, True) is None
    assert sports_dogs.adjust(st, "nhl", 0.65) > 0.65 and sports_dogs.adjust(st, "nba", 0.65) == 0.65
    c = {"edge": 0.2, "edge_own": 0.2, "reasons": ["x"], "trap": True}
    assert not sports.good(c) and sports.good({**c, "trap": False})
    print("ok test_dog_traps")


def _trend_games(bias, seed, seasons=(2019, 2020, 2021, 2022), per_day=3, days=150):
    """Simulated NHL totals (no prices, fresh teams every game so no back-to-backs): each weekday in each season
    goes one way `bias` of the time (the way picked at random per season)."""
    rnd = random.Random(seed)
    games = {}
    for se in seasons:
        way = {wd: rnd.random() < 0.5 for wd in range(7)}
        for d in range(days):
            day = datetime(se, 10, 5, 23, 0, tzinfo=timezone.utc) + timedelta(days=d)      # 7pm ET
            for j in range(per_day):
                over = way[(day - timedelta(hours=5)).weekday()] if rnd.random() < bias else rnd.random() < 0.5
                gid = f"nhl:{se}{d:03d}{j}"
                goals = 7 if over else 4
                games[gid] = {"id": gid, "league": "nhl", "start": (day + timedelta(minutes=j)).strftime("%Y-%m-%dT%H:%MZ"),
                              "status": "final", "stype": "2", "home": f"h{gid}", "away": f"a{gid}", "home_name": "H",
                              "away_name": "A", "home_score": str(goals - 2), "away_score": "2", "ml_home": "",
                              "ml_away": "", "spread_home": "", "total": "5.5"}
    return games


def test_trends():
    """A pattern that really persists gets proven; coin flips stay watch only; a 6-game Thursday-night under streak
    shows up as active with the next Thursday game."""
    import sports_trends as tr
    path = os.path.join(tempfile.gettempdir(), "trends_test.json")
    st = tr.study(_trend_games(0.85, 1), path, leagues=("nhl",))
    assert st["cells"]["nhl|streak"]["status"] == "proven_follow", st["cells"]["nhl|streak"]
    assert st["cells"]["nhl|rate"]["status"] == "proven_follow", st["cells"]["nhl|rate"]
    assert tr.verdict(st, "nhl", "streak") == "ride"
    st = tr.study(_trend_games(0.0, 2), path, leagues=("nhl",))
    assert all(v["status"] == "watch only" for v in st["cells"].values()), \
        {k: v for k, v in st["cells"].items() if v["status"] != "watch only"}
    assert tr.verdict(st, "nhl", "streak") == "coin flip"

    games = {}
    first = datetime(2025, 9, 12, 0, 15, tzinfo=timezone.utc)                     # Thursday 8:15pm ET
    for w in range(7):
        gid = f"nfl:t{w}"
        games[gid] = {"id": gid, "league": "nfl", "start": (first + timedelta(days=7 * w)).strftime("%Y-%m-%dT%H:%MZ"),
                      "status": "final" if w < 6 else "pre", "stype": "2", "home": f"h{w}", "away": f"a{w}",
                      "home_name": f"H{w}", "away_name": f"A{w}", "home_score": "17" if w < 6 else "",
                      "away_score": "10" if w < 6 else "", "ml_home": "-150", "ml_away": "130", "spread_home": "-3",
                      "total": "44.5"}
    now = first + timedelta(days=36)
    act = tr.active(games, now, {}, leagues=("nfl",))
    tnf = [a for a in act if a["situation"] == "thursday night" and a["outcome"] == "total"]
    assert tnf and tnf[0]["trend"] == "under" and tnf[0]["streak"] == 6 and tnf[0]["record"] == "6-0", tnf
    assert tnf[0]["upcoming"] == ["nfl:t6"] and tnf[0]["verdict"] == "coin flip"
    ls = tr.lean({"active": act}, "nfl", games["nfl:t6"])
    assert ("total", "under") in [(m, s) for m, s, _, _ in ls] and all(v == "coin flip" for *_, v in ls)
    ride = [dict(a, verdict="fade") for a in tnf]
    assert tr.lean({"active": ride}, "nfl", games["nfl:t6"])[0][:2] == ("total", "over"), "a proven fade flips it"


def test_selfcheck():
    """45 graded legs that said 60% but hit 40% -> that group needs extra edge; 10 such legs -> report only."""
    import sports_selfcheck as sck
    path = os.path.join(tempfile.gettempdir(), "selfcheck_test.json")

    def cards(n, wins):
        return [{"date": "2026-09-01", "kind": "lock", "lean": False, "status": "settled",
                 "legs": [{"league": "nhl", "market": "ml", "odds": -120, "p": 0.6, "result": "won" if i < wins else "lost",
                           "their_drama": [], "our_drama": []}]} for i in range(n)]
    for f in (path, path + ".tmp"):
        if os.path.exists(f):
            os.remove(f)
    st = sck.study(cards(45, 18), {"plays": {}}, path)
    g = st["groups"]["league:nhl"]
    assert g["n"] == 45 and g["said"] == 0.6 and g["hit"] == 0.4
    cand = {"league": "nhl", "market": "ml", "odds": -130}
    assert sck.extra_edge(st, cand) > 0 and sck.extra_edge(st, cand) <= sck.CAP
    assert st["extra_edge"]["price:-149..-101"] == 0.04, "20 points short = capped at +4"
    assert any("bar raised" in x for x in sck.summary(st))
    os.remove(path)
    st = sck.study(cards(10, 4), {"plays": {}}, path)
    assert st["extra_edge"] == {} and sck.extra_edge(st, cand) == 0.0 and st["groups"]["all"]["n"] == 10
    os.remove(path)
    st = sck.study(cards(45, 30), {"plays": {}}, path)
    assert sck.extra_edge(st, cand) == 0.0, "hitting above what we said: no extra"
    os.remove(path)


def _totals_games(league, signal, seed, n=3000, teams=20):
    """Simulated totals, line 8.5 every game. With `signal`: 25+ mph wind at an outdoor park goes under 80% of the
    time, and teams 0-2's home park goes over 80%. Without it: coin flips."""
    rnd = random.Random(seed)
    games = {}
    t0 = datetime(2019, 4, 1, 23, 0, tzinfo=timezone.utc)
    for i in range(n):
        h, a = rnd.sample(range(teams), 2)
        wind = rnd.choice((3, 6, 9, 12, 25, 28)) if signal else rnd.randint(0, 25)
        if signal and wind >= 25:
            over = rnd.random() < 0.2
        elif signal and h < 3:
            over = rnd.random() < 0.8
        else:
            over = rnd.random() < 0.5
        gid = f"{league}:s{i}"
        games[gid] = {"id": gid, "league": league, "start": (t0 + timedelta(hours=8 * i)).strftime("%Y-%m-%dT%H:%MZ"),
                      "status": "final", "stype": "2", "home": f"t{h}", "away": f"t{a}", "home_name": f"H{h}",
                      "away_name": f"A{a}", "home_score": "6" if over else "4", "away_score": "4" if over else "3",
                      "total": "8.5", "over_odds": "-110", "under_odds": "-110", "indoor": "0", "wx_wind": str(wind),
                      "wx_temp": "70", "wx_rain": "0", "elev": "100", "tzo": "-5"}
    return games


def test_totals():
    """Over/Under 2.0: a real wind + park signal gets kept and proven on the unseen games; coin flips stay unproven."""
    import sports_totals as tot
    path = os.path.join(tempfile.gettempdir(), "totals_test.json")
    games = {**_totals_games("mlb", True, 1), **_totals_games("nba", False, 2)}
    st = tot.study(games, path, leagues=("mlb", "nba"), public={}, news={})
    mlb, nba = st["mlb"], st["nba"]
    assert "wind" in mlb["kept"] and "park" in mlb["kept"], mlb["kept"]
    assert mlb["proven"] and mlb["hit_top"] > 0.6 and mlb["n_top"] >= 150, (mlb["hit_top"], mlb["n_top"])
    assert not nba["proven"], nba["grade"]
    sv = tot.state(games, "mlb")
    windy = {"id": "mlb:x", "league": "mlb", "start": "2030-01-01T23:00Z", "status": "pre", "home": "t10", "away": "t11",
             "total": "8.5", "indoor": "0", "wx_wind": "28", "wx_temp": "70", "wx_rain": "0", "elev": "100", "tzo": "-5"}
    with open(path) as f:
        saved = json.load(f)
    assert tot.p_over(saved["mlb"], sv, windy) < 0.4
    assert tot.p_over(saved["mlb"], sv, {**windy, "home": "t0", "wx_wind": "5"}) > 0.6
    assert tot.p_over({}, sv, windy) is None and tot.p_over(saved["mlb"], sv, {**windy, "home": "new"}) is None
    os.remove(path)


def _steam_games(planted, seed, n=1000):
    """Simulated NHL games that open -110/-110 and close with the home side bet to ~-130/+110 (a medium move).
    planted: the side the line moved toward wins 70% (far more than the close's ~54%); else it wins at the close."""
    rnd = random.Random(seed)
    games = {}
    t0 = datetime(2023, 10, 1, 23, 0, tzinfo=timezone.utc)
    for i in range(n):
        fair = sd.no_vig(-130, 110)
        won = rnd.random() < (0.70 if planted else fair)
        gid = f"nhl:s{seed}{i}"
        games[gid] = {"id": gid, "league": "nhl", "start": (t0 + timedelta(days=i)).strftime("%Y-%m-%dT%H:%MZ"),
                      "status": "final", "stype": "2", "home": f"h{i}", "away": f"a{i}", "home_name": "H",
                      "away_name": "A", "home_score": "3" if won else "1", "away_score": "1" if won else "3",
                      "ml_home": "-130", "ml_away": "110", "ml_home_open": "-110", "ml_away_open": "-110",
                      "spread_home": ""}
    return games


def test_moves():
    """Line movement: a planted steam edge is proven, a fair one isn't; open==close is 'no info'; CLV is exact."""
    import sports_moves as mv
    path = os.path.join(tempfile.gettempdir(), "moves_test.json")
    st = mv.study(_steam_games(True, 1), path, pub={}, picks=[])
    cell = st["steam"]["nhl"]["cells"]["ml|follow|medium|all"]
    assert cell["proven"] and cell["n_old"] >= 150 and cell["n_new"] >= 150, cell
    assert not st["steam"]["nhl"]["cells"]["ml|fade|medium|all"]["proven"]
    st = mv.study(_steam_games(False, 2), path, pub={}, picks=[])
    assert not st["proven"], st["proven"]
    g = _steam_games(False, 3, n=1)
    only = next(iter(g.values()))
    assert mv.moved({**only, "ml_home_open": "-130", "ml_away_open": "110"}) is None      # backfilled open = no info
    with open(path) as f:
        assert "steam" in json.load(f)
    os.remove(path)
    games = {"nfl:1": {"id": "nfl:1", "league": "nfl", "status": "final", "ml_home": "-162", "ml_away": "136",
                       "spread_home": "-3", "spread_home_odds": "-105", "spread_away_odds": "-115"},
             "nfl:2": {"id": "nfl:2", "league": "nfl", "status": "pre", "ml_home": "164", "ml_away": "-198"}}
    picks = [{"date": "2026-09-27", "kind": "dog", "legs": [
                {"game_id": "nfl:1", "league": "nfl", "side": "away", "market": "ml", "odds": 130},
                {"game_id": "nfl:1", "league": "nfl", "side": "away", "market": "spread", "line": 3.0, "odds": -120},
                {"game_id": "nfl:1", "league": "nfl", "side": "away", "market": "spread", "line": 3.5, "odds": -110},
                {"game_id": "nfl:2", "league": "nfl", "side": "home", "market": "ml", "odds": 150}]}]
    r = mv.clv(picks, games)
    ml, sp = r["legs"]
    assert ml["clv_cents"] == -6 and abs(ml["clv_pts"] - round(100 * (100 / 236 - 100 / 230), 2)) < 1e-9, ml
    assert sp["close"] == -115 and sp["clv_cents"] == -5 and sp["clv_pts"] < 0, sp
    assert r["skipped"] == {"not closed yet": 1, "line moved / no closing price": 1}, r["skipped"]
    assert r["summary"]["all"]["legs"] == 2 and r["summary"]["all"]["beat"] == 0
    assert "closing line value" in mv.clv_summary(picks, games)[0]
    assert mv.load() is not None


def _sim_spots(seed=11):
    """Synthetic NBA seasons: teams off a blowout loss REALLY win 15 points more often than their (juiced) price."""
    rnd = random.Random(seed)
    games, last = {}, {}                                    # team -> (season, its last margin)
    teams = [str(t) for t in range(1, 31)]
    n = 0
    for yr in range(2016, 2024):
        day0 = datetime(yr, 10, 20, tzinfo=timezone.utc)
        for d in range(150):
            ts = rnd.sample(teams, 16)
            for j in range(0, 16, 2):
                h, a = ts[j], ts[j + 1]
                p = rnd.uniform(0.3, 0.7)
                bh, ba = (last.get(t, (0, 0))[0] == yr and last[t][1] <= -15 for t in (h, a))
                true = min(0.95, max(0.05, p + 0.15 * (bh - ba)))
                m = rnd.randint(16, 25) if rnd.random() < 0.5 else rnd.randint(1, 10)
                m = m if rnd.random() < true else -m
                ml = [int(-100 * q / (1 - q)) if q >= 0.5 else int(100 * (1 - q) / q) for q in (p + 0.02, 1.02 - p)]
                gid = f"nba:s{n}"
                n += 1
                games[gid] = {"id": gid, "league": "nba", "start": (day0 + timedelta(days=d)).strftime("%Y-%m-%dT%H:%MZ"),
                              "status": "final", "home": h, "away": a, "home_name": h, "away_name": a,
                              "home_score": str(100 + max(0, m)), "away_score": str(100 + max(0, -m)),
                              "ml_home": str(ml[0]), "ml_away": str(ml[1]), "spread_home": str(-round((p - 0.5) * 20) - 0.5),
                              "spread_home_odds": "-110", "spread_away_odds": "-110", "stype": "2", "neutral": "0"}
                last[h], last[a] = (yr, m), (yr, -m)
    return games


def test_spots():
    import sports_spots as ss
    path = os.path.join(tempfile.gettempdir(), "spots_test.json")
    st = ss.study(_sim_spots(), path, sims=2)
    os.remove(path)
    nba = st["nba"]
    c = nba["cells"]["off_blowout_loss|ml|team"]
    assert c["proven"] and "off_blowout_loss|ml" in nba["proven"], ("the planted edge is found", c)
    assert c["n_old"] >= ss.MIN_N and c["n_new"] >= ss.MIN_N and c["profit_old"] > 0 and c["profit_new"] > 0
    assert not nba["cells"]["off_blowout_loss|ml|fade"]["proven"]
    for k in ("home_after_trip|ml|team", "home_after_trip|ml|fade", "revenge|ml|team", "3in4|spread|team"):
        assert not nba["cells"][k]["proven"], ("a spot with no edge is not proven", k, nba["cells"][k])
    assert st["_meta"]["tested"] > 0 and st["_meta"]["z_bonferroni"] > 1.96
    sh = nba["shifts"]["ml"]["off_blowout_loss"]
    assert 0.2 < sh < 1.0, sh
    assert ss.adjust(st, "nba", ["off_blowout_loss"], 0.5) > 0.55, "a proven spot moves the side up"
    assert ss.adjust(st, "nba", ["home_after_trip"], 0.5) == 0.5, "an unproven spot doesn't move it"
    assert ss.adjust(st, "nba", [], 0.5, ["off_blowout_loss"]) < 0.45, "the opponent's proven spot moves it down"
    assert ss.adjust({}, "nba", ["off_blowout_loss"], 0.5) == 0.5
    # flags come from earlier games only: a game 3 hours before doesn't count, one 7 hours before does
    g0 = {"id": "x0", "league": "nba", "start": "2030-01-01T00:00Z", "status": "final", "home": "A", "away": "B",
          "home_score": "80", "away_score": "120", "ml_home": "-150", "ml_away": "130", "stype": "2"}
    up = {"id": "x1", "league": "nba", "start": "2030-01-01T03:00Z", "status": "pre", "home": "A", "away": "C",
          "home_score": "", "away_score": "", "ml_home": "-400", "ml_away": "300", "stype": "2"}
    idx = ss.index({"x0": g0})
    assert "off_blowout_loss" not in ss.flags(idx, up, "home"), "no peeking at a game 3 hours earlier"
    up["start"] = "2030-01-01T07:00Z"
    f = ss.flags(idx, up, "home")
    assert "off_blowout_loss" in f and "revenge" not in f and "early_season" in f, f
    assert "big_fav_off_loss" in f and "off_upset_loss" not in f, f               # a -150 fave last time: not an upset
    assert ss.flags({"x0": g0}, up, "home") == f, "a plain games dict works too"
    nxt = dict(up, start="2030-01-01T23:00Z")                                   # the next night, vs a rested team
    assert "b2b" in ss.flags(idx, nxt, "home") and "rest_edge" in ss.flags(idx, nxt, "away")
    again = dict(up, away="B", start="2030-01-04T00:00Z")                        # vs the team that beat it
    assert "revenge" in ss.flags(idx, again, "home") and "revenge" not in ss.flags(idx, again, "away")
    assert "b2b" not in ss.flags(idx, again, "home")


def _explorer_games(days, seed, sunday_home=0.8, t0=datetime(2021, 1, 4, 23, 0, tzinfo=timezone.utc), first=0):
    """Simulated NBA: 6 games a day among 20 teams, priced fairly (with juice). Planted: on SUNDAYS the home team
    wins `sunday_home` of the time whatever its price (None = no edge: it wins at its price like every other game)."""
    rnd = random.Random(seed)
    games = {}
    for d in range(first, first + days):
        day = t0 + timedelta(days=d)
        teams = rnd.sample(range(20), 12)
        for k in range(6):
            p = rnd.uniform(0.35, 0.65)

            def am(q):
                dec = 1 / (q * 1.025)
                return int((dec - 1) * 100) if dec >= 2 else int(-100 / (dec - 1))
            edge = day.weekday() == 6 and sunday_home is not None
            won = rnd.random() < (sunday_home if edge else p)
            gid = f"nba:x{d}_{k}"
            games[gid] = {"id": gid, "league": "nba", "start": day.strftime("%Y-%m-%dT%H:%MZ"), "status": "final",
                          "stype": "2", "home": f"t{teams[2 * k]}", "away": f"t{teams[2 * k + 1]}",
                          "home_score": "110" if won else "100", "away_score": "100" if won else "110",
                          "ml_home": str(am(p)), "ml_away": str(am(1 - p)), "spread_home": "", "total": ""}
    return games


def test_explorer():
    """The explorer: a planted edge becomes a suspect, is PROVEN on later games, noise never is, nothing is retested,
    an edge that vanishes going forward is killed, and the engine hooks nudge only matching sides."""
    import sports_explorer as ex
    path = os.path.join(tempfile.mkdtemp(), "explorer_test.json")
    planted, noise = "nba|ml|Sun&home", "nba|ml|Mon"
    games = _explorer_games(420, 1)
    r1 = ex.explore(games, path, batch=150, leagues=("nba",), verbose=False)
    first = set(ex.LAST_TESTED)
    assert planted in r1["new_suspects"] and noise in first and noise not in r1["suspects"], r1
    assert r1["tested"] == len(first) == 150 and r1["expected_by_luck"] < 1
    st = ex.load(path)
    s = st["suspects"][planted]
    assert s["disc"]["n"] >= 300 and s["disc"]["roi_old"] > 0 and s["disc"]["roi_new"] > 0 and s["disc"]["z"] >= 3.5
    assert s["cutoff"] == max(g["start"] for g in games.values())
    shutil.copy(path, path + ".kill")
    r2 = ex.explore(games, path, batch=150, leagues=("nba",), verbose=False)       # same games: only NEW angles
    assert r2["tested"] > 0 and not first & set(ex.LAST_TESTED) and r2["tested_total"] == r1["tested"] + r2["tested"]
    assert planted not in r2["new_suspects"] and not r2["new_proven"]               # no forward games yet
    later = {**games, **_explorer_games(160, 2, first=420)}                          # forward games, same edge
    r3 = ex.explore(later, path, batch=50, leagues=("nba",), verbose=False)
    assert planted in r3["new_proven"] and planted in r3["proven"], r3
    assert noise not in r3["proven"] and all("home" in k.split("|")[2].split("&") for k in r3["proven"]), r3["proven"]
    pv = ex.load(path)["proven"][planted]
    assert pv["fwd"]["n"] >= 100 and pv["fwd"]["roi"] > 0 and pv["fwd"]["z_edge"] >= 1 and pv["shift"] > 0
    # the edge vanishes going forward -> killed
    gone = {**games, **_explorer_games(160, 3, sunday_home=0.2, first=420)}
    r4 = ex.explore(gone, path + ".kill", batch=10, leagues=("nba",), verbose=False)
    assert planted in r4["new_killed"] and planted not in r4["proven"] + r4["suspects"], r4
    # hooks
    st = ex.load(path)
    assert [p["key"] for p in ex.proven(st)] == r3["proven"]
    up = {"id": "nba:up", "league": "nba", "start": "2022-12-04T23:00Z", "status": "pre", "home": "t1", "away": "t2",
          "ml_home": "110", "ml_away": "-130", "stype": "2"}                       # a Sunday
    idx = ex.index(later)
    home, away = ex.atoms_for(later, up, "home", idx), ex.atoms_for(later, up, "away", idx)
    assert "Sun" in home and "home" in home and "dog" in home and "road" in away, home
    assert ex.adjust_side(st, "nba", home, 0.45) > 0.45 and ex.adjust_side(st, "nba", away, 0.55) == 0.55
    assert ex.adjust_side(st, "nfl", home, 0.45) == 0.45 and ex.adjust_side({}, "nba", home, 0.45) == 0.45
    assert ex.adjust_total(st, "nba", ex.game_atoms_for(later, up, idx), 0.5) == 0.5
    assert ex.load("/nonexistent/explorer.json") == {}
    shutil.rmtree(os.path.dirname(path))


def _sim_games(days, seed, over_bias, first=0, t0=datetime(2021, 1, 4, 23, 0, tzinfo=timezone.utc)):
    """Simulated NHL: 16 teams with fixed true attack/defense, Poisson goals, a regulation tie settled in OT (+1).
    The market prices the moneyline and puck line at the TRUE chances (with juice); its total is priced as if
    scoring were `over_bias` lower than it really is (0 = a fair market everywhere)."""
    import sports_sim as ss
    tr, rnd = random.Random(99), random.Random(seed)
    att = [tr.uniform(-0.25, 0.25) for _ in range(16)]
    dfn = [tr.uniform(-0.25, 0.25) for _ in range(16)]

    def am(q):
        dec = 1 / (q * 1.025)
        return int((dec - 1) * 100) if dec >= 2 else int(-100 / (dec - 1))

    def pois(lam):
        L, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rnd.random()
            if p <= L:
                return k
            k += 1
    games = {}
    for d in range(first, first + days):
        day = t0 + timedelta(days=d)
        teams = rnd.sample(range(16), 8)
        for k in range(4):
            h, a = teams[2 * k], teams[2 * k + 1]
            lh, la = 2.9 * math.exp(att[h] - dfn[a] + 0.04), 2.9 * math.exp(att[a] - dfn[h] - 0.04)
            q = lh / (lh + la)
            gh, ga = pois(lh), pois(la)
            if gh == ga:
                gh, ga = (gh + 1, ga) if rnd.random() < q else (gh, ga + 1)
            true = ss.CountGame(lh, la, 0, {1: q, -1: 1 - q}, [0.0, 1.0])
            mkt = ss.CountGame(lh * (1 - over_bias), la * (1 - over_bias), 0, {1: q, -1: 1 - q}, [0.0, 1.0])
            ph = ss.p_home_win(true.M)
            line = -1.5 if ph >= 0.5 else 1.5
            pc, po = ss.p_cover(true.M, line), ss.p_over(mkt.T, 5.5)
            gid = f"nhl:s{d}_{k}"
            games[gid] = {"id": gid, "league": "nhl", "start": day.strftime("%Y-%m-%dT%H:%MZ"), "status": "final",
                          "stype": "2", "home": f"t{h}", "away": f"t{a}", "home_score": str(gh), "away_score": str(ga),
                          "neutral": "0", "ml_home": str(am(ph)), "ml_away": str(am(1 - ph)), "spread_home": str(line),
                          "spread_home_odds": str(am(pc)), "spread_away_odds": str(am(1 - pc)), "total": "5.5",
                          "over_odds": str(am(po)), "under_odds": str(am(1 - po))}
    return games


def test_sim():
    """The simulator: exact pricing matches the Monte Carlo, a planted total mispricing is found and PROVEN on later
    games, pure noise never is, no config is ever retried, a suspect whose edge disappears is killed, and the hooks
    leave p alone unless that league x market is proven."""
    import sports_sim as ss
    # the score models: exact = the Monte Carlo without the noise
    cg = ss.CountGame(3.1, 2.7, 0, {1: 0.53, -1: 0.47}, [0.0, 1.0])
    assert abs(cg.t_le(60) - 1) < 1e-6 and abs(cg.M.gt(-100) - 1) < 1e-6 and cg.M.eq(0) == 0
    assert abs(cg.M.gt(0) - cg.M.gt(-1)) < 1e-12 and abs(cg.T.eq(5) - (cg.t_le(5) - cg.t_le(4))) < 1e-12
    assert abs(ss.p_home_win(cg.M) + (1 - cg.M.gt(0)) - 1) < 1e-9
    mb, add, _, _ = ss.mlb_extras(1.0)
    assert abs(sum(mb.values()) - 1) < 1e-9 and abs(mb[1] - 0.5) < 1e-6 and 0 not in mb   # walk-offs: home by 1
    assert mb.get(2, 0) == 0 and mb[-2] > 0.05 and abs(sum(add) - 1) < 1e-9
    for lg in ("nhl", "mlb", "nba", "nfl"):
        m = ss.Model(lg, ss.default_cfg(lg))
        m.games, m.avg = 999, {"nhl": 3.0, "mlb": 4.5, "nba": 112.0, "nfl": 22.0}[lg]
        m.s = {"A": {"nhl": 0.3, "mlb": 0.4, "nba": 4.0, "nfl": 3.0}[lg]}
        g = {"id": f"{lg}:mc", "start": "2024-01-10T00:00Z", "home": "A", "away": "B", "neutral": "0"}
        mu_h, mu_a, margin, total, _ = m.predict(g, sm._ts(g["start"]))
        M, T, _ = m.dists(g, mu_h, mu_a, margin, total)
        line, tot = {"nhl": (-1.5, 5.5), "mlb": (-1.5, 8.5), "nba": (-3.5, 224.5), "nfl": (-3.0, 44.5)}[lg]
        hs, as_ = ss.simulate(m, g, 6000, seed=3)
        mc = ss.mc_prices(hs, as_, line, tot)
        assert abs(mc["ml"] - ss.p_home_win(M)) < 0.03, (lg, mc, ss.p_home_win(M))
        assert abs(mc["spread"] - ss.p_cover(M, line)) < 0.03 and abs(mc["total"] - ss.p_over(T, tot)) < 0.03, lg
        assert ss.p_home_win(M) > 0.5 and abs(mc["home"] - mc["away"] - margin) < 0.6
    assert ss.simulate(m, g, 500, seed=3) == ss.simulate(m, g, 500, seed=3)            # seeded
    # the planted edge: the market thinks there are 12% fewer goals than there are
    d = tempfile.mkdtemp()
    path = os.path.join(d, "sim.json")
    hist = _sim_games(450, 1, 0.12)
    r1 = ss.run(hist, path, batch=2, leagues=("nhl",), verbose=False)
    first = set(ss.LAST_TESTED)
    assert r1["tested_configs"] == len(first) == 3 and r1["expected_by_luck"] < 1, r1
    planted = [k for k in r1["new_suspects"] if k.startswith("nhl|total|")]
    assert planted and all(k.startswith("nhl|total|") for k in r1["suspects"]), r1["suspects"]
    s = ss.load(path)["suspects"][planted[0]]
    assert s["cutoff"] == max(g["start"] for g in hist.values()) and not r1["proven"]
    shutil.copy(path, path + ".kill")
    r2 = ss.run(hist, path, batch=2, leagues=("nhl",), verbose=False)                   # same games: only NEW configs
    assert r2["tested_configs"] == 2 and not first & set(ss.LAST_TESTED), ss.LAST_TESTED
    assert r2["tested_total"] == r1["tested_total"] + 2 and not r2["new_proven"]
    later = {**hist, **_sim_games(200, 2, 0.12, first=450)}                             # forward games, same edge
    r3 = ss.run(later, path, batch=1, leagues=("nhl",), verbose=False)
    assert planted[0] in r3["new_proven"] and planted[0] in r3["proven"], r3
    assert all(k.startswith("nhl|total|") for k in r3["proven"])
    pv = ss.load(path)["proven"][planted[0]]
    assert pv["fwd"]["n"] >= ss.FWD_N and pv["shift"] != 0
    # the edge disappears going forward -> killed
    gone = {**hist, **_sim_games(200, 3, 0.0, first=450)}
    r4 = ss.run(gone, path + ".kill", batch=1, leagues=("nhl",), verbose=False)
    assert planted[0] in r4["new_killed"] and planted[0] not in r4["proven"] + r4["suspects"], r4
    # hooks: nothing proven -> p unchanged; proven over -> the over chance moves toward the sim
    up = {"id": "nhl:up", "league": "nhl", "start": "2022-06-01T23:00Z", "status": "pre", "stype": "2", "home": "t0",
          "away": "t1", "neutral": "0", "ml_home": "-120", "ml_away": "100", "spread_home": "-1.5",
          "spread_home_odds": "150", "spread_away_odds": "-170", "total": "5.5", "over_odds": "260", "under_odds": "-320"}
    td = ss.today({**later, up["id"]: up}, path, sims=2000, leagues=("nhl",), verbose=False)
    row = td["games"]["nhl:up"]
    assert row["total"]["over"] > row["total"]["market_over"] and row["ml"]["fair_home"] and row["proj"]["total"] > 5
    st = ss.load(path)
    assert [p["key"] for p in ss.proven(st)] == r3["proven"] and "today" in st
    p_mkt = sd.no_vig(260, -320)
    assert ss.adjust_total(st, "nhl", up, p_mkt) > p_mkt
    assert ss.adjust_side(st, "nhl", up, "home", 0.53) == 0.53 and ss.adjust_side(st, "nhl", up, "away", 0.4, "spread") == 0.4
    assert ss.adjust_total(st, "nba", up, 0.5) == 0.5 and ss.adjust_total({}, "nhl", up, 0.5) == 0.5
    assert ss.adjust_total(st, "nhl", dict(up, total="6.5"), 0.4) == 0.4                # the line moved: no sim price
    assert ss.load("/nonexistent/sim.json") == {} and ss.proven({}) == []
    # pure noise: a fair market everywhere -> never promoted
    npath = os.path.join(d, "noise.json")
    noise = _sim_games(450, 4, 0.0)
    n1 = ss.run(noise, npath, batch=2, leagues=("nhl",), verbose=False)
    n2 = ss.run({**noise, **_sim_games(200, 5, 0.0, first=450)}, npath, batch=2, leagues=("nhl",), verbose=False)
    assert not n1["proven"] and not n2["proven"] and not n2["new_proven"], (n1, n2)
    nst = ss.load(npath)
    assert ss.adjust_total(nst, "nhl", up, 0.45) == 0.45 and ss.adjust_side(nst, "nhl", up, "home", 0.55) == 0.55
    shutil.rmtree(d)


TENNIS_COLS = ["tour", "date", "tourney", "location", "series", "court", "surface", "round", "bo", "winner", "loser",
               "wrank", "lrank", "wpts", "lpts", "w1", "l1", "w2", "l2", "w3", "l3", "w4", "l4", "w5", "l5", "wsets",
               "lsets", "comment", "psw", "psl", "b365w", "b365l", "maxw", "maxl", "avgw", "avgl"]


def _tennis_hist(path, weeks, plant=None, seed=8):
    """Simulated tennis-data.co.uk history: ATP + WTA, one 32-player event a week (levels and surfaces rotate), priced
    efficiently (Pinnacle 2.5% margin, Bet365 6%, average 5%, best 1.5% - all around the true chance).
    plant(week, tour, is_fav) -> Bet365 underrates that side's chance by this factor (then adds its usual margin)."""
    import sports_tennis as stn
    rnd = random.Random(seed)
    skill = {t: [rnd.gauss(0, 0.8) for _ in range(64)] for t in ("atp", "wta")}
    rank = {t: {i: 3 * k + 1 for k, i in enumerate(sorted(range(64), key=lambda i: -skill[t][i]))} for t in skill}
    t0 = datetime(2014, 1, 6)
    rows = []

    def sets_of(r, bo, won_all):
        need = 3 if bo == 5 else 2
        lost = r.randint(0, need - 1)
        seq = ["L"] * lost + ["W"] * (need - 1)
        r.shuffle(seq)
        out = []
        for x in seq + ["W"]:
            a, b = (6, r.randint(0, 4)) if r.random() < 0.8 else (7, 6)
            out.append((a, b) if x == "W" else (b, a))
        return out
    for w in range(weeks):
        for tour in ("atp", "wta"):
            r = random.Random(seed * 1000003 + w * 7 + (tour == "wta"))
            series = (("ATP250", "ATP500", "Masters 1000", "Grand Slam") if tour == "atp" else
                      ("International", "Premier", "Premier Mandatory", "Grand Slam"))[w % 4]
            surf = ("Hard", "Clay", "Grass", "Hard")[(w // 6) % 4]
            bo = 5 if tour == "atp" and w % 4 == 3 else 3
            alive = r.sample(range(64), 32)
            for k, rn in enumerate(("1st Round", "2nd Round", "Quarterfinals", "Semifinals", "The Final")):
                day = (t0 + timedelta(days=7 * w + k)).strftime("%Y-%m-%d")
                nxt = []
                for a, b in zip(alive[::2], alive[1::2]):
                    q = 1 / (1 + math.exp(-(skill[tour][a] - skill[tour][b])))
                    q = stn.to_bo5(q) if bo == 5 else q
                    a_won = r.random() < q
                    wi, li = (a, b) if a_won else (b, a)
                    pw = q if a_won else 1 - q
                    nxt.append(wi)
                    row = {"tour": tour, "date": day, "tourney": f"{tour} event {w % 12}", "location": f"City{w % 12}",
                           "series": series, "court": "Indoor" if w % 5 == 0 else "Outdoor", "surface": surf,
                           "round": rn, "bo": bo, "winner": f"Player{wi:02d} {tour[0].upper()}.",
                           "loser": f"Player{li:02d} {tour[0].upper()}.", "wrank": rank[tour][wi],
                           "lrank": rank[tour][li], "comment": "Completed"}
                    if r.random() < 0.005:
                        row["comment"] = "Walkover"
                        rows.append(row)
                        continue
                    ss = sets_of(r, bo, True)
                    for n, (x, y) in enumerate(ss, 1):
                        row[f"w{n}"], row[f"l{n}"] = x, y
                    row["wsets"], row["lsets"] = sum(x > y for x, y in ss), sum(x < y for x, y in ss)
                    if r.random() < 0.01:
                        row["comment"] = "Retired"
                    fav_w = pw >= 0.5
                    mult = {True: 1.0, False: 1.0}
                    if plant:
                        mult = {True: plant(w, tour, fav_w), False: plant(w, tour, not fav_w)}
                    for c, marg, dg in (("ps", 1.025, 3), ("b365", 1.06, 2), ("avg", 1.05, 2), ("max", 1.015, 2)):
                        bw, bl = (pw / mult[True], (1 - pw) / mult[False]) if c == "b365" else (pw, 1 - pw)
                        bw, bl = bw / (bw + bl), bl / (bw + bl)          # what the book believes, + its margin
                        row[f"{c}w"] = round(1 / (bw * marg), dg)
                        row[f"{c}l"] = round(1 / (bl * marg), dg)
                    rows.append(row)
                alive = nxt
    with gzip.open(path, "wt", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=TENNIS_COLS, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    return (t0 + timedelta(days=7 * weeks)).strftime("%Y-%m-%d")


def test_tennis_edge():
    """The tennis edge study: a soft book's planted mispricing is found on the older half and forward-confirmed,
    noise never gets promoted, nothing is retested on the same data, a suspect whose edge disappears is killed,
    and adjust() leaves p alone unless a proven angle matches."""
    import sports_tennis_edge as te
    tmp = tempfile.mkdtemp()
    hist, path = os.path.join(tmp, "hist.csv.gz"), os.path.join(tmp, "edge.json")
    kw = dict(matches=None, lines=None, verbose=False, budget_s=60)
    planted = "wta|b365|dog"
    soft = lambda w, tour, fav: 1.4 if tour == "wta" and not fav else 1.0          # Bet365 way too generous on WTA dogs
    split = _tennis_hist(hist, 40, soft)                                             # (the date right after week 40)
    r1 = te.study(path, hist, split=split, batch=150, **kw)
    first = set(te.LAST_TESTED)
    assert planted in r1["new_suspects"] and planted in r1["suspects"] and not r1["new_proven"], r1
    s = te.load(path)["suspects"][planted]
    assert s["disc"]["n"] >= 150 and s["disc"]["roi"] > 0 and s["disc"]["z_edge"] >= 3.5 and s["fwd"]["n_new"] == 0
    assert r1["false_positives"]["suspects_by_luck"] < 1
    shutil.copy(path, path + ".kill")
    r2 = te.study(path, hist, batch=150, **kw)                                       # same data: only NEW angles
    assert r2["tested"] > 0 and not first & set(te.LAST_TESTED), r2
    assert planted not in r2["new_suspects"] and not r2["new_proven"]
    _tennis_hist(hist, 60, soft)                                                     # 20 more weeks, same edge
    r3 = te.study(path, hist, batch=20, **kw)
    assert planted in r3["new_proven"] and planted in r3["proven"], r3
    st = te.load(path)
    pv = st["proven"][planted]
    assert pv["fwd"]["n_new"] >= 100 and pv["fwd"]["roi_new"] > 0 and pv["fwd"]["z_edge_new"] >= 2 and pv["fwd"]["n"] >= 300
    assert all(k.startswith("wta|b365|") for k in st["proven"]), st["proven"]
    assert "fixed: line shop b365 wta dog gap>10%" in r3["proven"], r3["proven"]
    assert st["split"] == split and len(st["log"]) == 3
    # the edge disappears going forward -> the suspect is killed
    _tennis_hist(hist, 60, lambda w, tour, fav: soft(w, tour, fav) if w < 40 else 1.0)
    r4 = te.study(path + ".kill", hist, batch=10, **kw)
    assert planted in r4["new_killed"] and planted not in r4["proven"] + r4["suspects"], r4
    # pure noise: an efficient market never gets anything promoted
    noise_path = os.path.join(tmp, "noise.json")
    _tennis_hist(hist, 60, None, seed=11)
    r5 = te.study(noise_path, hist, batch=400, **kw)
    assert r5["proven"] == [] and r5["tested"] == 400 and "atp|pin|surf:clay" in te.LAST_TESTED, r5
    assert "atp|pin|surf:clay" not in r5["suspects"]
    # hooks
    assert [p["key"] for p in te.proven(st)] == sorted(st["proven"])
    feats = {"tour": "wta", "atoms": ["dog", "surf:clay"]}
    assert te.adjust({}, feats, 0.4) == 0.4 and te.adjust(te.load(noise_path), feats, 0.4) == 0.4
    assert te.adjust(st, {"tour": "atp", "atoms": ["dog"]}, 0.4) == 0.4                  # no proven angle matches
    assert te.adjust(st, {"tour": "wta", "atoms": ["fav"]}, 0.6) == 0.6
    sh = pv["shift"]
    assert abs(te.adjust(st, feats, 0.4) - (sm.sigmoid(sm.logit(0.4) + sh) if sh else 0.4)) < 1e-12
    assert te.adjust(st, {"tour": "wta", "p": 0.3}, 0.3) == te.adjust(st, {"tour": "wta", "atoms": ["dog"]}, 0.3)
    assert te.load("/nonexistent/edge.json") == {} and te.study(path, os.path.join(tmp, "none.gz"), **kw)["proven"] == []
    head = os.path.join(tmp, "header_only.csv.gz")                                  # the fetch saved just the header
    with gzip.open(head, "wt", newline="") as f:
        csv.writer(f).writerow(TENNIS_COLS)
    r6 = te.study(os.path.join(tmp, "empty.json"), head, **kw)
    assert r6["proven"] == [] and r6.get("skipped"), r6
    shutil.rmtree(tmp)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
