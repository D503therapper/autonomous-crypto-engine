"""Offline tests for the sports engine (no network): ESPN parsing, model tuning, the board rules,
grading. Run: python sports_test.py"""
import csv
import gzip
import json
import math
import os
import random
import re
import shutil
import tempfile
import time
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
    assert not any(sports.good(c) for c in cs if c["odds"] > 0), "no fake underdog edge from ratings that assume the starter plays"
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
    """THE LABEL STUDY's rules (9/28): picked by how likely it WINS - 53%+ = a play (STRONG LEAN), 56%+ = LOCK, the
    likeliest lock = Lock of the Day; an underdog only as VALUE with a proven angle; never fighting Vegas; -150 cap."""
    pr = lambda c: {**c, "reasons": c["reasons"] + ["proven spot: home dog after a loss"]}
    c = [_cand("a", -300, 0.80), _cand("b", -140, 0.62), _cand("f", -115, 0.57), _cand("k", -120, 0.55),
         _cand("n", -110, 0.52), pr(_cand("d", 150, 0.43)), _cand("e", 180, 0.40), _cand("i", -110, 0.58, "spread", -3.5, "nfl")]
    b = sports.make_board(c)
    assert b["lock"]["legs"][0]["game_id"] == "b", "the Lock of the Day = the likeliest lock, -150 cap (never the -300)"
    for kind in ("two", "three"):
        legs = b[kind]["legs"]
        assert all(sports.good(l) for l in legs) and all(l["odds"] >= sports.MAX_FAV for l in legs), "real plays only"
        assert len({l["game_id"] for l in legs}) == len(legs) == (2 if kind == "two" else 3)
    assert not sports.good(_cand("n", -110, 0.52)), "52% is a coin flip - not a play"
    assert sports.good(_cand("k", -120, 0.55)) and sports.leg_tier(_cand("k", -120, 0.55)) == "lean", "53-56% = a STRONG LEAN"
    assert sports.leg_tier(_cand("f", -115, 0.57)) == "lock", "56%+ = a LOCK"
    assert b["dog"]["legs"][0]["game_id"] == "d", "a dog only with a proven angle behind it"
    assert not sports.good(_cand("e", 180, 0.40)), "the engine alone disagreeing with Vegas is never value"
    assert sports.leg_tier(pr(_cand("d", 150, 0.43))) == "value"
    assert sports.leg_tier(pr(_cand("pl", 120, 0.58))) == "lock", "plus money up to +125 at 56%+ = a lock"
    assert sports.leg_tier(pr(_cand("pt", 140, 0.58))) == "value", "over +125 is always value"
    fight = {**_cand("ft", -140, 0.60), "edge_own": 0.50 * sd.decimal(-140) - 1}   # our own read: 50% vs the price's 58%
    assert not sports.good(fight), "never a side our own read says Vegas is overrating"
    assert sports.make_board([_cand("x1", -160, 0.70), _cand("x2", -170, 0.72)])["lock"] is None, "no moneyline over -150"
    assert sports.make_board([_cand("x3", -110, 0.57), _cand("sp", -110, 0.60, "spread", -2.5, "nfl")])["lock"]["legs"][0][
        "game_id"] == "sp", "any line counts - a spread the engine's surer of beats a moneyline"
    filler = [_cand("p", 130, 0.43), _cand("q", -115, 0.52), {**_cand("r", -150, 0.62), "reasons": []}]
    fb = sports.make_board(filler)
    assert all(fb[k] is None for k in ("lock", "dog", "two", "three", "four")), "nothing real = no picks (leans take over)"
    slate = [_cand(f"g{i}", -150 + 5 * i, 0.62 - 0.005 * i) for i in range(10)]
    bd = sports.make_board(slate)
    lock_g = bd["lock"]["legs"][0]["game_id"]
    two, three = [l["game_id"] for l in bd["two"]["legs"]], [l["game_id"] for l in bd["three"]["legs"]]
    assert lock_g in two and set(two) <= set(three), "Lock -> 2-leg -> 3-leg ladder"
    assert sports.make_board(slate[3:], fixed={"lock": bd["lock"]["legs"]})["two"]["legs"][0]["game_id"] == lock_g
    one = sports.make_board([dict(_cand("mnf", -108, 0.52, "spread", 3.5, "nfl"), side="home"),
                             dict(_cand("mnf", -112, 0.48, "spread", -3.5, "nfl"), side="away")])
    assert one["solo"] and one["lock"] is None, "one game, a coin flip = that game's pick, never the Lock of the Day"
    sure = sports.make_board([_cand("tnf", -130, 0.60), dict(_cand("tnf", 110, 0.40), side="away")])
    assert sure["lock"] and sure["solo"] is None, "one game, a real lock = the Lock of the Day"
    assert sports.pick_tier({"legs": [{"tier": "lock"}, {"tier": "lock"}]}) == "lock"
    assert sports.pick_tier({"legs": [{"tier": "lock"}, {"tier": "lean"}]}) == "lean", "only as sure as the weakest leg"
    assert sports.pick_tier({"legs": [{"tier": "lock"}, {"tier": "value"}]}) == "value"
    assert sports.pick_tier({"kind": "lock", "tier": "value", "legs": [{"tier": "value"}]}) == "lock"
    assert sports.in_record({"lean": True, "date": "2026-09-29"}) and not sports.in_record({"lean": True, "date": "2026-09-28"})


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
    picks, parlays = st.pick_slate(cands)
    parlay = parlays["atp"]
    assert picks and all(c["p"] >= st.MIN_P and c["edge"] >= st.MIN_EDGE for c in picks), "likely to win AND value"
    assert [c["p"] for c in picks] == sorted((c["p"] for c in picks), reverse=True) and len(picks) < 6, "no filler"
    assert len(parlay) == 3 and parlay[0]["p"] >= parlay[-1]["p"] and all(c in picks for c in parlay)
    assert parlays["wta"] == [], "no women's picks = no women's parlay"
    mixed = [dict(c, id=f"w{i}", match=f"w{i}", tour="wta", p=0.60, odds=-110, dec=sd.decimal(-110), edge=0.6 * sd.decimal(-110) - 1)
             for i, c in enumerate(cands[:4])]
    mixed += [dict(c, id=f"m{i}", match=f"m{i}", tour="atp", p=0.70, odds=-110, dec=sd.decimal(-110), edge=0.7 * sd.decimal(-110) - 1)
              for i, c in enumerate(cands[:8])]
    pk, _ = st.pick_slate(mixed)
    assert sum(c["tour"] == "wta" for c in pk) == 4 and sum(c["tour"] == "atp" for c in pk) == 6, \
        "each tour on its own: up to 6 men's, the 4 real women's picks - never filler from the other tour"
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



def _tn_sim(n, tour, seed, t0=datetime(2023, 1, 1, tzinfo=timezone.utc), players=30, id0=0):
    """Simulated finished matches for one tour (ids 0..players-1: the SAME numbers on both tours, like ESPN's)."""
    rnd = random.Random(seed)
    skill = {str(i): rnd.gauss(0, 1) for i in range(players)}
    out = {}
    for i in range(n):
        a, b = rnd.sample(list(skill), 2)
        w = 1 if rnd.random() < 1 / (1 + math.exp(-(skill[a] - skill[b]) * 1.5)) else 2
        mid = f"{tour}:{id0 + i}"
        out[mid] = {"id": mid, "tour": tour, "start": (t0 + timedelta(hours=3 * i)).strftime("%Y-%m-%dT%H:%MZ"), "event": "e",
                    "tourney": "Somewhere Open", "round": "R1", "surface": "hard", "bo": "3", "p1": a, "p1_name": f"P {a}",
                    "p2": b, "p2_name": f"Q {b}", "winner": w, "sets1": "6 6", "sets2": "3 3", "status": "STATUS_FINAL", "done": 2}
    return out, skill


def test_tennis_per_tour():
    """Men's and women's tennis are different worlds: separate ratings pools (the same ESPN id on both tours is two
    different people), weights learned + graded per tour, candidates priced with the tour's own weights."""
    import sports_tennis as st
    # the pools: an ATP result never touches a WTA rating (same player id "5" on both tours)
    pools = st.Pools()
    m = {"id": "atp:x", "tour": "atp", "start": "2024-01-01T10:00Z", "surface": "hard", "p1": "5", "p2": "6",
         "winner": 1, "sets1": "6 6", "sets2": "1 1", "status": "STATUS_FINAL", "done": 2}
    for _ in range(20):
        pools.update(m)
    assert pools.pool("atp").r[("5", None)] > 1600 and ("5", None) not in pools.pool("wta").r, "no cross-tour leak"
    assert pools.pool("wta").n.get("5", 0) == 0 and not pools.pool("wta").h2h
    wf = pools.features({**m, "id": "wta:y", "tour": "wta"})
    assert wf["p_elo"] == 0.5 and wf["known"] == 0 and wf["h2h"] == 0, "the WTA's #5 starts from scratch"
    assert st.tour_of({"match": "wta:1"}) == "wta" and st.tour_of({"id": "atp:1:2"}) == "atp" and st.tour_of("WTA") == "wta"
    # the study: each tour fits and grades on its own; a tour short on history borrows the shared weights (logged)
    atp, _ = _tn_sim(2400, "atp", 3)
    wta, _ = _tn_sim(2400, "wta", 4)
    keep = st.TOUR_MIN_RATED
    st.TOUR_MIN_RATED = 1500
    try:
        logs = []
        rt, w, rep = st.study({**atp, **wta}, eval_n=400, log=logs.append)
        assert set(w) == {"atp", "wta", "shared"} and not logs, logs
        for t in ("atp", "wta"):
            r = rep["tours"][t]
            assert r["own_weights"] and r["graded"] == 400 and r["acc"] > 0.6 and r["rated"] > 1500, (t, r)
        assert w["atp"] != w["wta"], "two tours, two sets of learned weights"
        assert rt.pool("atp") is not rt.pool("wta")
        small, _ = _tn_sim(900, "wta", 5)
        logs = []
        rt2, w2, rep2 = st.study({**atp, **small}, eval_n=400, log=logs.append)
        assert not rep2["tours"]["wta"]["own_weights"] and w2["wta"] == w2["shared"] and w2["atp"] != w2["shared"]
        assert any("WTA" in x and "shared weights" in x for x in logs), logs
    finally:
        st.TOUR_MIN_RATED = keep
    # model_p / candidates use the tour's own weights: a WTA weight set that ignores ratings gives a coin flip there
    ws = {"atp": [0.0, 1.0, 0, 0, 0, 0, 0], "wta": [0.0, 0.0, 0, 0, 0, 0, 0], "shared": [0.0, 1.0, 0, 0, 0, 0, 0]}
    f = {"elo": 1.0, "fatigue": 0, "form": 0, "h2h": 0}
    assert st.model_p(ws, f, 3, "atp") > 0.7 and st.model_p(ws, f, 3, "wta") == 0.5
    assert st.model_p(ws["atp"], f, 3) == st.model_p(ws, f, 3, "atp"), "a plain list still works"
    now = datetime(2023, 6, 1, tzinfo=timezone.utc)
    ms = {**atp, **wta}
    up = (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%MZ")
    for t in ("atp", "wta"):
        ms[f"{t}:up"] = {**ms[f"{t}:0"], "id": f"{t}:up", "status": "STATUS_SCHEDULED", "winner": 0, "sets1": "", "sets2": "",
                         "start": up, "p1": "1", "p2": "2", "p1_name": f"{t} One", "p2_name": f"{t} Two"}
    rt3, _, _ = st.study(ms, eval_n=400, log=lambda x: None)
    lines = [{"a": f"{t} One", "b": f"{t} Two", "a_ml": -150, "b_ml": 130, "start": up, "tour": t} for t in ("atp", "wta")]
    cs = st.candidates(ms, rt3, ws, lines, now, now + timedelta(hours=24))
    by = {c["id"]: c for c in cs}
    assert by["wta:up:1"]["p"] == 0.5 and by["atp:up:1"]["p"] != 0.5, "each tour priced with its own weights"
    assert st.match_line(ms["atp:up"], [{**lines[1], "a": "atp One", "b": "atp Two"}])[0] is None, "never a WTA line on an ATP match"


def test_tennis_bios():
    """ESPN athlete bios parse from both endpoints' payloads; age at a match; the parsers never invent a field."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ftp", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                       "tools", "fetch_tennis_players.py"))
    ftp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ftp)
    v3 = {"athlete": {"id": "3623", "displayName": "Jannik Sinner", "dateOfBirth": "2001-08-16T07:00Z",
                      "displayHeight": "6' 4\"", "height": 76.0, "hand": {"type": "RIGHT", "abbreviation": "R"},
                      "turnedPro": 2018, "displayDOB": "8/16/2001"}}
    b = ftp.parse_athlete(v3)
    assert b == {"name": "Jannik Sinner", "dob": "2001-08-16", "height_cm": 193, "hand": "R", "pro": 2018}, b
    core = {"id": "2375", "fullName": "Rafael Nadal", "displayDOB": "6/3/1986", "height": 185, "hand": {"displayValue": "Left"},
            "displayExperience": "Turned Pro: 2001", "statsSummary": {"statistics": [{"name": "aces"}]}}
    b = ftp.parse_athlete(core)
    assert b["dob"] == "1986-06-03" and b["height_cm"] == 185 and b["hand"] == "L" and b["pro"] == 2001, b
    assert b["stats"] == ["aces"]
    bare = ftp.parse_athlete({"athlete": {"id": "9", "displayName": "Some One"}})
    assert bare == {"name": "Some One"}, "nothing ESPN didn't send"
    assert ftp.parse_athlete({"code": 404}) is None and ftp.parse_athlete([]) is None
    assert ftp._date("22/05/1987") == "1987-05-22" and ftp._date("garbage") is None and ftp._date("1899-01-01") is None
    assert ftp._height_cm({"displayHeight": "1.88 m"}) == 188 and ftp._height_cm({"height": 0}) is None
    import sports_tennis as st
    assert abs(st.age_at("2001-08-16", "2026-08-16T10:00Z") - 25.0) < 0.01
    assert 24.99 < st.age_at("2001-08-16", "2026-08-15") < 25.0, "the day before the birthday: still 24"
    assert st.age_at(None, "2026-01-01") is None and st.age_at("2001-08-16", None) is None
    assert st.career_start({"pro": 2018}) == 2018.0 and 2019 < st.career_start({"dob": "2001-08-16"}) < 2020
    assert st.career_start({}) is None
    p = st.bios_for({"atp:1": {"dob": "2000-01-01"}, "wta:1": {"dob": "1990-01-01"}, "atp:2": {"none": True}}, "wta")
    assert p == {"1": {"dob": "1990-01-01"}}, "per tour, and never a 'none' entry"
    assert st.place_of("Wuhan, China") == ("as", 8) and st.place_of("Indian Wells, California, USA") == ("na", -8)
    assert st.place_of("Basel. Switzerland") == ("eu", 1) and st.place_of("World") is None
    assert st.far(("eu", 1), ("na", -5)) and not st.far(("eu", 1), ("eu", 2)) and st.far(("as", 3), ("as", 9))
    assert not st.far(None, ("eu", 1))


def _tm(i, p1, p2, win=1, tourney="Somewhere Open", rnd="Round 1", start=None, sets=("6 6", "3 3"), status="STATUS_FINAL",
        venue="Paris, France", bo=3):
    return {"id": f"atp:{i}", "tour": "atp", "start": start or f"2020-01-{1 + i:02d}T10:00Z", "event": "e", "tourney": tourney,
            "round": rnd, "surface": "hard", "bo": str(bo), "p1": p1, "p1_name": f"P {p1}", "p2": p2, "p2_name": f"P {p2}",
            "winner": win, "sets1": sets[0], "sets2": sets[1], "status": status, "done": 2, "venue": venue}


def test_tennis_life_features():
    """Experience counts only EARLIER matches (no peeking), big matches = Slam main draw or QF+ (never qualifying),
    the censoring fix only for players first seen at the start of the history, every age term neutral when a bio is
    missing (with the flag), and the last match / streaks / first sets / injuries / travel from earlier matches."""
    import sports_tennis as st
    r = st.Ratings()
    ms = [_tm(0, "1", "2"), _tm(1, "1", "3", tourney="Australian Open", rnd="Qualifying 1st Round"),
          _tm(2, "1", "2", tourney="Australian Open", rnd="Round 1", sets=("6 4 7", "4 6 5")),
          _tm(3, "3", "1", tourney="Madrid Open", rnd="Quarterfinal", win=2)]
    seen = []
    for m in ms:
        f = r.features(m)
        seen.append((f["exp_n1"], f["exp_n2"], f["big_n1"], f["big_n2"]))
        r.update(m)
    assert seen == [(0, 0, 0, 0), (1, 0, 0, 0), (2, 1, 0, 0), (1, 3, 0, 1)], seen
    assert r.big["1"] == 2 and r.n["1"] == 4, "the Slam main draw + the QF are big (once played); qualifying never"
    # a player first seen much later: no censoring fix; one seen at the very start with a turned-pro year: the fix
    r.bios.update({"1": {"dob": "2002-06-01", "pro": 2018}, "7": {"pro": 2010}})
    late = _tm(9, "7", "1", start="2021-06-01T10:00Z")
    r.update(late)
    assert r.exp_n("7", "2021-07-01T10:00Z") == 1, "first seen long after the history starts: counted as is"
    x1 = r.exp_n("1", "2021-07-01T10:00Z")
    assert x1 > r.n["1"], "seen from the start, turned pro before it: unseen years added"
    assert x1 <= r.n["1"] + st.PRE_YEARS_MAX * st.RATE_MAX
    del r.bios["1"]
    assert r.exp_n("1", "2021-07-01T10:00Z") == r.n["1"], "no bio: no fix"
    # neutral when missing
    q = st.Ratings()
    f = q.features(_tm(0, "a", "b"))
    for k in ("age_gap", "age_curve", "teen_rise", "vet_bo5", "bio_miss", "teen_vs_vet", "young_hot"):
        assert f[k] == 0.0, (k, f[k])
    assert f["age1"] is None and f["age2"] is None
    q.bios["a"] = {"dob": "2008-01-01"}
    f = q.features(_tm(0, "a", "b"))
    assert f["bio_miss"] == -1.0 and f["age_gap"] == 0.0 and f["teen_vs_vet"] == 0.0
    q.bios["b"] = {"dob": "1985-01-01"}
    f = q.features(_tm(0, "a", "b"))
    assert f["bio_miss"] == 0.0 and f["age_gap"] < -3 and f["teen_vs_vet"] == 1.0
    ff = st.flip_features(f)
    assert ff["teen_vs_vet"] == -1.0 and ff["age1"] == f["age2"] and ff["exp_n1"] == f["exp_n2"] and ff["form"] == -f["form"]
    assert st.model_p([0.0, 1.0, 0, 0, 0, 0, 0], {**f, "elo": 0.4}) == st.model_p([0.0, 1.0, 0, 0, 0, 0, 0] + [0.0] * len(st.LIFE),
                                                                                   {**f, "elo": 0.4}), "zero weights = no effect"
    # last match, streaks, first sets, injuries, travel
    g = st.Ratings()
    g.update(_tm(0, "x", "y", start="2020-03-01T10:00Z", sets=("6 4 7", "4 6 6"), venue="Miami, Florida, USA"))
    g.update(_tm(1, "x", "z", start="2020-03-02T10:00Z", sets=("6 6", "7 7"), venue="Miami, Florida, USA", win=2))
    g.update(_tm(2, "y", "z", start="2020-03-03T10:00Z", status="STATUS_WALKOVER", sets=("", ""), win=2))
    nxt = _tm(3, "x", "y", start="2020-03-05T10:00Z", venue="Madrid, Spain", tourney="Madrid Open")
    f = g.features(nxt)
    assert abs(f["last_sets"] + 1 / 3) < 1e-9 and f["last_dist"] == -1.0, "y's last match went the distance"
    assert f["travel"] == 0.0, "both came from Miami: y's walkover isn't a match played, both flew"
    one = g.one("x", nxt, nxt["start"])
    assert one["travel"] == 1.0 and one["last_sets"] == 2 / 3 and one["lost2"] == 0.0
    assert g.one("y", nxt, nxt["start"])["inj_recent"] > 0.9 and g.one("x", nxt, nxt["start"])["inj_recent"] == 0.0
    assert g.one("z", nxt, nxt["start"])["won3"] == 0.0 and g.one("x", nxt, "2020-03-01T09:00Z")["rest"] == math.log1p(0)
    assert g.one("x", nxt, nxt["start"])["fs_rate"] == (1 + 2) / (2 + 4) - 0.5, "won 1 of 2 first sets, shrunk"
    assert g.one("x", nxt, "2020-02-01T10:00Z")["inj_12m"] == 0.0


def test_tennis_life_study():
    """Noise never ships: random birth dates (age has nothing to do with winning) keep the age weights at 0. A real
    planted effect (the veteran wins more in best-of-5) is found and kept."""
    import sports_tennis as _stl
    _prev, _stl.LIFE_USE = _stl.LIFE_USE, True        # (the factors on, just for this test)
    try:
        import sports_tennis as st

        def sim(n, seed, plant):
            rnd = random.Random(seed)
            players = [str(i) for i in range(160)]
            skill = {p: rnd.gauss(0, 1) for p in players}
            bios = {f"atp:{p}": {"dob": f"{rnd.randint(1985, 2006)}-0{rnd.randint(1, 9)}-15"} for p in players}
            t0 = datetime(2022, 1, 1, tzinfo=timezone.utc)
            out = {}
            for i in range(n):
                a, b = rnd.sample(players, 2)
                when = t0 + timedelta(hours=3 * i)
                bo = 5 if i % 2 else 3
                x = 1.5 * (skill[a] - skill[b])
                if plant and bo == 5:
                    aa, ab = (st.age_at(bios[f"atp:{q}"]["dob"], when.strftime("%Y-%m-%d")) for q in (a, b))
                    x += 2.5 * (st._vet(aa) - st._vet(ab))
                w = 1 if rnd.random() < 1 / (1 + math.exp(-x)) else 2
                mid = f"atp:{i}"
                out[mid] = {"id": mid, "tour": "atp", "start": when.strftime("%Y-%m-%dT%H:%MZ"), "event": "e",
                            "tourney": "Somewhere Open", "round": "Round 1", "surface": "hard", "bo": str(bo), "p1": a,
                            "p1_name": f"P {a}", "p2": b, "p2_name": f"Q {b}", "winner": w, "sets1": "6 6", "sets2": "3 3",
                            "status": "STATUS_FINAL", "done": 2, "venue": "Paris, France"}
            return out, bios
        keep = (st.TOUR_MIN_RATED, st.FACTORS)
        st.TOUR_MIN_RATED = 1000
        st.FACTORS = {k: st.FACTORS[k] for k in ("age", "young_vs_aging")}
        try:
            ms, bios = sim(5000, 21, plant=False)
            _, w, rep = st.study(ms, eval_n=1000, log=lambda x: None, players=bios)
            lf = rep["tours"]["atp"]["life"]
            assert lf["kept"] == [] and all(v == 0.0 for v in w["atp"][len(st.PRIOR):]), lf
            assert lf["factors"]["age"]["n"] == 1000 and lf["factors"]["age"]["active"] > 900 and lf["graded_with_both_ages"] == 1000
            assert "z" in lf["factors"]["age"] and lf["curve"], lf
            ms, bios = sim(7000, 22, plant=True)
            _, w, rep = st.study(ms, eval_n=1000, log=lambda x: None, players=bios)
            lf = rep["tours"]["atp"]["life"]
            assert "age" in lf["kept"] and w["atp"][len(st.PRIOR) + st.LIFE.index("vet_bo5")] > 0.3, lf
            assert lf["factors"]["age"]["gain_mnats"] > 0 and lf["factors"]["age"]["z"] >= st.Z_KEEP
        finally:
            st.TOUR_MIN_RATED, st.FACTORS = keep
    finally:
        _stl.LIFE_USE = _prev

def test_tennis_life_off():
    """The crew's call: age / experience / first-set stay research only - the picks use the model as it was."""
    import sports_tennis as stl
    assert stl.LIFE_USE is False
    assert stl.life_line(None, {"f": {"age1": 19, "age2": 34, "exp_n1": 3, "exp_n2": 400}}, "A", "B", "she", "She", "her") == ""


def test_tennis_life_lines():
    """At most one age / experience line, only when it's on our side; never 'real talk' or 'chalk'; no repeats."""
    import sports_tennis as _stl
    _prev, _stl.LIFE_USE = _stl.LIFE_USE, True        # (the factors on, just for this test)
    try:
        import sports_tennis as st
        base = {"id": "x", "player": "Mirra Andreeva", "opp": "Venus Williams", "surface": "hard", "bo": 3, "tour": "wta",
                "f": {"surface_gap": 0, "fatigue": 0, "form": 0, "h2h": 0, "home": 0, "age1": 18.4, "age2": 44.1,
                      "exp_n1": 60, "exp_n2": 400, "big_n1": 3, "big_n2": 90}}
        used = set()
        bd = st.breakdown(base, None, used)
        teen = [x for x in bd if x.startswith("🔥") and "18" in x]
        assert len(teen) == 1 and not any("🧓" in x for x in bd), bd
        assert not any(re.search(r"\b(he|him|his)\b", x) for x in bd)
        vet = {**base, "id": "y", "player": "Novak Djokovic", "opp": "Joao Fonseca", "bo": 5, "tour": "atp",
               "f": {**base["f"], "age1": 39.3, "age2": 20.1, "exp_n1": 900, "exp_n2": 40, "big_n1": 150, "big_n2": 3}}
        bd2 = st.breakdown(vet, None, used)
        assert sum("🧓" in x for x in bd2) == 1 and any("five" in x.lower() or "best of 5" in x.lower() or "best-of-5" in x
                                                       for x in bd2 if "🧓" in x), bd2
        big = {**vet, "id": "z", "bo": 3}
        line = [x for x in st.breakdown(big, None, set()) if "🧓" in x]
        assert len(line) == 1 and "150" in line[0] and "3" in line[0], line
        plain = {**base, "f": {k: v for k, v in base["f"].items() if not k.startswith(("age", "exp", "big"))}}
        assert not any(x[:1] in ("🧓", "⚡") or "years old" in x for x in st.breakdown(plain, None, set()))
        from sports_breakdown import Voice
        v = Voice("q", set())
        seen = {st.life_line(v, {**big, "id": f"k{i}"}, "Djokovic", "Fonseca", "he", "He", "his") for i in range(4)}
        seen.discard("")
        assert len(seen) == 4, "four ways to say it, never the same one twice on a board"
        assert st.life_line(v, {**big, "id": "k9"}, "Djokovic", "Fonseca", "he", "He", "his") == "", "all taken: dropped"
        for x in seen | set(bd) | set(bd2):
            assert "real talk" not in x.lower() and "chalk" not in x.lower(), x
    finally:
        _stl.LIFE_USE = _prev

def test_tennis_edge_life_atoms():
    """'Lastname F.' -> ESPN id only on a UNIQUE match per tour; the new life atoms are new names (no existing atom
    changes); a teen vs a 30+ gets its own atom."""
    import sports_tennis_edge as te
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "m.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "tour", "start", "p1", "p1_name", "p2", "p2_name"])
        w.writeheader()
        w.writerow({"id": "1", "tour": "atp", "start": "2016-09-26T10:00Z", "p1": "3623", "p1_name": "Jannik Sinner",
                    "p2": "11", "p2_name": "Alexander Zverev"})
        w.writerow({"id": "2", "tour": "atp", "start": "2016-09-27T10:00Z", "p1": "12", "p1_name": "Mischa Zverev",
                    "p2": "13", "p2_name": "Juan Martin del Potro"})
        w.writerow({"id": "3", "tour": "wta", "start": "2016-09-27T10:00Z", "p1": "3623", "p1_name": "Anna Smith",
                    "p2": "14", "p2_name": "Andrea Smith"})
    nmap, first = te.name_map(path)
    assert te.espn_id(nmap, "atp", "Sinner J.") == "3623" and te.espn_id(nmap, "wta", "Sinner J.") is None
    assert te.espn_id(nmap, "atp", "Zverev A.") == "11" and te.espn_id(nmap, "atp", "Zverev M.") == "12"
    assert te.espn_id(nmap, "atp", "Del Potro J.M.") == "13"
    assert te.espn_id(nmap, "wta", "Smith A.") is None, "two ESPN players on one key: skipped"
    assert first == {"atp": "2016-09-26", "wta": "2016-09-27"}
    shutil.rmtree(tmp)
    m = te.M()
    m.lvl, m.bo = "slam", 5
    me = {"n": 400, "slam": 0, "big": 40, "w3": True}
    them = {"n": 30, "slam": 5, "big": 2, "w3": False}
    A = te.life_atoms(m, me, them, 19.2, 33.0, True)
    assert {"exp:vet", "expgap:x3+", "bigx:more", "slam:first", "age:teen", "oage:vet", "agegap:-8", "yvv:young",
            "tvv:teen", "yhot"} <= set(A), A
    assert te.life_atoms(m, me, them, None, None, False) == [], "not warm, no bios: nothing"
    assert all(te._life_atom(a) for a in A)
    old = ["lvl:slam", "surf:clay", "bo5", "fav", "p:80+", "rk:1-10", "q:out", "lay:long", "olay:long", "form:hot",
           "mdl:+5", "g365:3+", "home", "ohome", "srv:big", "rd:early", "ret:last"]
    assert not any(te._life_atom(a) for a in old), "existing atoms are not life atoms (their fingerprints stay)"


def test_tennis_slates_and_parlays():
    """Up to 6 men's + 6 women's picks, never a mixed parlay, a tour's parlay only with 3 picks; old slates (one
    mixed parlay) and new slates (one per tour) both grade; post() never reposts a match from any slate."""
    import sports_tennis as st

    def c(mid, tour, p, odds=-110):
        d = sd.decimal(odds)
        return {"id": f"{mid}:1", "match": mid, "side": 1, "tour": tour, "p": p, "odds": odds, "dec": d, "edge": p * d - 1,
                "player": f"P {mid}", "opp": "X", "start": "2026-10-01T10:00Z", "tourney": "T", "market": "ml", "hcp": None,
                "ml": odds, "round": "R1", "surface": "hard", "bo": 3}
    many = [c(f"atp:{i}", "atp", 0.60 + 0.01 * i) for i in range(10)] + [c(f"wta:{i}", "wta", 0.58 + 0.01 * i) for i in range(10)]
    picks, pars = st.pick_slate(many)
    assert sum(x["tour"] == "atp" for x in picks) == 6 and sum(x["tour"] == "wta" for x in picks) == 6
    for t in ("atp", "wta"):
        assert len(pars[t]) == 3 and all(x["tour"] == t for x in pars[t]), "never a mixed parlay"
        assert [x["p"] for x in pars[t]] == sorted((x["p"] for x in picks if x["tour"] == t), reverse=True)[:3]
    few = [c(f"atp:{i}", "atp", 0.62) for i in range(4)] + [c(f"wta:{i}", "wta", 0.65) for i in range(2)]
    few += [c("wta:bad", "wta", 0.52), c("wta:thin", "wta", 0.60, -200)]          # a coin flip, and no value
    picks, pars = st.pick_slate(few)
    assert len(picks) == 6 and pars["wta"] == [] and len(pars["atp"]) == 3, "2 women's picks: no women's parlay"
    # post(): one parlay per tour; a match already on ANY slate never goes up again
    keep = (st.candidates, st._used, st.breakdown)
    st.candidates = lambda *a, **k: [dict(x) for x in many]
    st._used = lambda skip=(): set()
    st.breakdown = lambda cand, rt, used: ["🎾 test"]
    try:
        old = [{"date": "2026-09-01", "picks": [{"id": "atp:9:2", "match": "atp:9", "side": 2, "result": "won"}], "parlay": None}]
        slate = st.post({}, None, None, [], old, datetime(2026, 9, 30, 20, tzinfo=timezone.utc))
        assert slate and "parlay" not in slate and set(slate["parlays"]) == {"atp", "wta"}
        assert "atp:9" not in {l["match"] for l in slate["picks"]}, "already on a slate: never again"
        assert sum(l["tour"] == "atp" for l in slate["picks"]) == 6 and sum(l["tour"] == "wta" for l in slate["picks"]) == 6
        legs = {l["id"]: l for l in slate["picks"]}
        for t, par in slate["parlays"].items():
            assert par["tour"] == t and all(legs[i]["tour"] == t for i in par["legs"]) and len(par["legs"]) == 3
    finally:
        st.candidates, st._used, st.breakdown = keep
    # grading both shapes
    ms = {f"atp:{i}": {"id": f"atp:{i}", "status": "STATUS_FINAL", "winner": 1, "done": 2, "sets1": "6 6", "sets2": "2 2"}
          for i in range(3)}
    ms.update({f"wta:{i}": {"id": f"wta:{i}", "status": "STATUS_FINAL", "winner": 2 if i == 0 else 1, "done": 2,
                            "sets1": "6 6", "sets2": "2 2"} for i in range(3)})
    L = lambda mid: {"id": f"{mid}:1", "match": mid, "side": 1, "result": None, "tour": mid[:3]}
    old_slate = {"date": "2026-09-27", "picks": [L("atp:0"), L("wta:1"), L("atp:1")],
                 "parlay": {"legs": ["atp:0:1", "wta:1:1", "atp:1:1"], "status": "open", "dec": 6.0, "american": 500}}
    new_slate = {"date": "2026-09-28", "picks": [L("atp:2"), L("wta:0"), L("wta:2")],
                 "parlays": {"atp": {"legs": ["atp:2:1"], "status": "open", "tour": "atp", "dec": 1.9, "american": -110},
                             "wta": {"legs": ["wta:0:1", "wta:2:1"], "status": "open", "tour": "wta", "dec": 3.6, "american": 260}}}
    sl = [old_slate, new_slate]
    st.grade(ms, sl)
    assert old_slate["parlay"]["status"] == "won" and new_slate["parlays"]["atp"]["status"] == "won"
    assert new_slate["parlays"]["wta"]["status"] == "lost"
    r = st.record(sl)
    assert r["atp"]["won"] == 3 and r["wta"]["won"] == 2 and r["wta"]["lost"] == 1
    assert r["mixed"]["p_won"] == 1 and r["atp"]["p_won"] == 1 and r["wta"]["p_lost"] == 1 and r["atp"]["p_lost"] == 0
    assert [k for k, _ in st.parlays_of(old_slate)] == ["mixed"] and {k for k, _ in st.parlays_of(new_slate)} == {"atp", "wta"}


def test_tennis_markov():
    """The live tennis model against known values."""
    import sports_tennis_live as stl
    assert abs(stl.game_p(0.6) - 0.7357) < 1e-4, "60% on serve holds 73.6% (the textbook number)"
    assert stl.game_p(0.5) == 0.5 and stl.game_p(0.64, 3, 3) == stl.game_p(0.64, 4, 4)
    assert abs(stl.tb_p(0.62, 0.62) - 0.5) < 1e-9 and abs(stl.live_p(0.64, 0.64) - 0.5) < 1e-9
    assert abs(sum(stl.set_dist(0.6, 0.6)) - 1) < 1e-9
    for tour in ("atp", "wta"):
        for bo in (3, 5):
            for p in (0.3, 0.5, 0.62, 0.8):
                pa, pb = stl.serve_split(p, tour, bo)
                assert abs(stl.live_p(pa, pb, bo=bo) - p) < 2e-3, "0-0 returns the pre-match chance"
    pa, pb = stl.serve_split(0.6, "atp", 3)
    assert stl.hold_p(pa) > stl.hold_p(pb) and 0.75 < stl.hold_p(pa) < 0.9
    base = stl.live_p(pa, pb)
    up = stl.live_p(pa, pb, (1, 0), (2, 0), None, None, 3)                       # up a set and a break
    assert up > 0.9 and up > base + 0.3
    down = stl.live_p(pa, pb, (0, 1), (2, 2), None, None, 3)                     # down a set, on serve
    assert 0.25 < down < base and stl.live_p(pa, pb, (0, 1), (0, 2), None, None, 3) < down
    assert abs(stl.live_p(0.64, 0.64, (0, 1), (0, 0), None, None, 3) - 0.25) < 1e-6, "even players, a set down: 25%"
    assert stl.live_p(pa, pb, (1, 0), (5, 4), (3, 0), True, 3) > 0.99, "serving for it at 40-0"
    assert stl.live_p(pa, pb, (1, 1), (6, 6), (6, 5), True, 3) > stl.live_p(pa, pb, (1, 1), (6, 6), (5, 6), True, 3)
    assert stl.live_p(pa, pb, (2, 0)) == 1.0 and stl.live_p(pa, pb, (0, 2)) == 0.0
    bo5 = stl.serve_split(0.6, "atp", 5)
    assert stl.live_p(*bo5, (0, 1), (0, 0), None, None, 5) > stl.live_p(pa, pb, (0, 1), (0, 0), None, None, 3), \
        "a set down hurts less in best of 5"
    assert stl.final_tb_of("Wimbledon") == 10 and stl.final_tb_of("Shanghai Masters") == 7
    s = stl.score_state({"sets1": "4 2", "sets2": "6 2", "pts1": "AD", "pts2": "40", "server": 1})
    assert s["sets"] == (0, 1) and s["games"] == (2, 2) and s["pts"] == (4, 3) and s["set_no"] == 2
    assert stl.score_state({"sets1": "6", "sets2": "4", "pts1": None, "pts2": None})["games"] == (0, 0)
    assert stl.score_state({"sets1": "6 3", "sets2": "4 1", "pts1": "50", "pts2": "0"})["pts"] is None, "junk points: left out"
    import time as _t
    t0 = _t.time()
    for i in range(200):
        stl.live_p(0.6 + i * 1e-4, 0.62, (1, 0), (3, 2), (2, 1), None, 3)
    assert _t.time() - t0 < 2.0, "fast enough for a 5-second loop"


def _tn_live_row(mid="atp:77", tour="atp", s1="4 2", s2="6 2", pts=(None, None), server=None, detail="", status="STATUS_IN_PROGRESS",
                 n1="Jannik Sinner", n2="Holger Rune", winner=0, done=1):
    return {"id": mid, "tour": tour, "start": "2026-09-28T10:00Z", "tourney": "Shanghai Masters", "round": "R2", "surface": "hard",
            "bo": 3, "p1": "1", "p1_name": n1, "p2": "2", "p2_name": n2, "winner": winner, "sets1": s1, "sets2": s2,
            "status": status, "done": done, "pts1": pts[0], "pts2": pts[1], "server": server, "detail": detail}


def _ml_for(p, edge):
    """A plus-money price that gives chance p the given edge."""
    dec = (1 + edge) / p
    return int(round((dec - 1) * 100))


def test_live_tennis_rules():
    import sports_tennis as stn
    import sports_tennis_live as stl
    L = sports_live
    L._TUNED.clear()
    m = _tn_live_row()                                              # Sinner dropped the 1st 4-6, 2-2 in the 2nd
    pre = {"mkt_p1": 0.78, "model_p1": 0.8}
    p1 = stl.p1_live(m, 0.78)[0]
    assert L.min_p() <= p1 < 0.78
    ml1 = _ml_for(p1, 0.10)
    assert 100 <= ml1 <= L.LIVE_MAX_ODDS, ml1
    line = {"a": "Holger Rune", "b": "Jannik Sinner", "a_ml": -ml1 - 40, "b_ml": ml1, "suspended": False}   # (Bovada lists them the other way)
    ln, flip = stn.match_line(m, [line])
    assert ln is line and flip
    # one of OUR pregame picks, trailing, now plus money: a MEN'S pick never gets the double down (the crew's call)...
    assert L.evaluate_tennis(m, line, flip, pre, 1, (), set()) == [], "no double down in men's tennis"
    # ...a WOMEN'S pick in the same spot: DOUBLE DOWN
    wm = _tn_live_row("wta:77", "wta", n1="Jessica Pegula", n2="Emma Navarro")
    wline = {"a": "Emma Navarro", "b": "Jessica Pegula", "a_ml": -ml1 - 40, "b_ml": ml1, "suspended": False}
    _, wflip = stn.match_line(wm, [wline])
    used = set()
    pl = L.evaluate_tennis(wm, wline, wflip, pre, 1, (), used)
    assert len(pl) == 1 and pl[0]["team"] == "Jessica Pegula" and pl[0]["odds"] == ml1 and pl[0]["double_down"], pl
    x = pl[0]
    assert x["emoji"] == "🎾" and x["league"] == "tennis" and x["sport"] == "Women's Tennis" and x["id"] == "tennis:wta:77:1"
    assert "4-6" in x["score"] and x["clock"].startswith("Set 2") and {"ours", "strong", "state"} <= set(x["reasons"])
    assert "double down" in x["line"].lower() and "dropped the first set" in x["line"], x["line"]
    assert x["edge"] >= L.LIVE_MIN_EDGE and x["breakdown"]
    txt = " ".join([x["line"]] + x["breakdown"]).lower()
    assert "real talk" not in txt and "chalk" not in txt
    # a WTA play in the same check: she/her, and no wording repeated from the first play
    w = _tn_live_row("wta:5", "wta", n1="Coco Gauff", n2="Iga Swiatek")
    wl = {"a": "Coco Gauff", "b": "Iga Swiatek", "a_ml": ml1, "b_ml": -ml1 - 40, "suspended": False}
    wp = L.evaluate_tennis(w, wl, False, pre, 1, (), used)
    assert wp and wp[0]["sport"] == "Women's Tennis" and not __import__("re").search(r"\b(he|him|his)\b", " ".join([wp[0]["line"]] + wp[0]["breakdown"]))
    assert wp[0]["line"] != x["line"] and not set(wp[0]["breakdown"]) & set(x["breakdown"]), "fresh wording, no repeats"
    # a strong favorite on our numbers (not our pick): a play, but no double down
    pl2 = L.evaluate_tennis(m, line, flip, pre, None)
    assert pl2 and not pl2[0]["double_down"] and "ours" not in pl2[0]["reasons"] and "strong" in pl2[0]["reasons"]
    # the engine didn't like him pregame (not our pick, not a strong favorite on OUR numbers): no play
    assert L.evaluate_tennis(m, line, flip, {"mkt_p1": 0.78, "model_p1": 0.52}, None) == []
    assert L.evaluate_tennis(m, line, flip, {"mkt_p1": 0.78}, None) == [], "no number of our own: no 'strong' reason"
    # plus money only / real edge only / no pre-match number
    minus = {**line, "b_ml": -120, "a_ml": 100}
    assert not [p for p in L.evaluate_tennis(m, minus, flip, pre, 1) if p["team"] == "Jannik Sinner"]
    thin = {**line, "b_ml": _ml_for(p1, 0.02), "a_ml": -_ml_for(p1, 0.02) - 40}
    assert L.evaluate_tennis(m, thin, flip, pre, 1) == []
    assert L.evaluate_tennis(m, line, flip, {}, 1) == []
    # the tuned min p: raise the bar above his chance and it's gone
    L._TUNED["min_p"] = 0.55
    assert L.evaluate_tennis(m, line, flip, pre, 1) == []
    L._TUNED.clear()
    # MAX_GAP: ESPN says he's up a set and a break but the book has him +150 = the score is stale (or the book
    # knows something) - never "value"
    ahead = _tn_live_row(s1="6 3", s2="4 1")
    assert stl.p1_live(ahead, 0.78)[0] > 0.9
    assert L.evaluate_tennis(ahead, {**line, "b_ml": 150, "a_ml": -180}, flip, pre, 1) == []
    # stale / delayed score
    L.SCORE_SEEN.clear()
    now_s = 1_000_000.0
    assert not L.tennis_stale(m, now_s)
    assert not L.tennis_stale(m, now_s + 300) and L.tennis_stale(m, now_s + L.TENNIS_STALE_S + 1), "a score sitting still"
    assert not L.tennis_stale(_tn_live_row(s2="6 3"), now_s + 700), "the score moved: fresh again"
    assert L.tennis_stale(_tn_live_row(detail="Rain Delay"), now_s)
    # the whole tennis check: suspended market / stale score = no play and the match isn't judged (a play that's up
    # holds, paused); fresh = the play, judged; the play goes against nobody's pregame pick
    keep = (L.tennis_feeds, stl.load_prematch, stl.our_picks)
    log = {"plays": {}}
    try:
        m, line = wm, wline                                   # (a women's pick - the double down is women's only)
        stl.load_prematch = lambda path=None: {"wta:77": pre}
        stl.our_picks = lambda path=None: {"wta:77": 1}
        L.SCORE_SEEN.clear()
        L.tennis_feeds = lambda: ([m], [m], [{**line, "suspended": True}])
        judged = set()
        assert L.tennis_plays(log, datetime.now(timezone.utc), (), judged) == [] and not judged
        assert L.TENNIS["suspended"] == 1
        L.tennis_feeds = lambda: ([m], [m], [line])
        L.SCORE_SEEN["wta:77"] = ((m["sets1"], m["sets2"], None, None), time.time() - L.TENNIS_STALE_S - 5)
        assert L.tennis_plays(log, datetime.now(timezone.utc), (), judged) == [] and not judged and L.TENNIS["stale"] == 1
        L.SCORE_SEEN.clear()
        got = L.tennis_plays(log, datetime.now(timezone.utc), (), judged)
        assert got and got[0]["double_down"] and "tennis:wta:77" in judged
        # graded like every live play: a final result settles it, a retirement before a set is done voids it
        log["plays"]["tennis:wta:77:1"] = {"league": "tennis", "match": "wta:77", "side": "1", "result": None}
        log["plays"]["tennis:wta:9:2"] = {"league": "tennis", "match": "wta:9", "side": "2", "result": None}
        L.grade_tennis(log, [_tn_live_row("wta:77", "wta", status="STATUS_FINAL", winner=1, s1="4 6 6", s2="6 3 2"),
                             _tn_live_row("wta:9", "wta", status="STATUS_RETIRED", winner=2, done=0)])
        assert log["plays"]["tennis:wta:77:1"]["result"] == "won" and log["plays"]["tennis:wta:9:2"]["result"] == "void"
        assert L.record(log) == {"won": 1, "lost": 0}, "tennis live plays count in the LIVE PLUS MONEY record"
        assert L.locked_sides({"plays": {}}, datetime.now(timezone.utc))["tennis:wta:77"] == "1"
    finally:
        L.tennis_feeds, stl.load_prematch, stl.our_picks = keep
    # Bovada's live tennis feed: live match moneylines; a suspended market is flagged, never priced
    bov = [{"path": [{"description": "ATP Shanghai"}, {"description": "Tennis"}], "events": [
        {"id": "1", "live": True, "startTime": 1790000000000, "displayGroups": [{"markets": [
            {"description": "Moneyline", "status": "O", "period": {"main": True, "live": True},
             "outcomes": [{"description": "Jannik Sinner", "status": "O", "price": {"american": "+150"}},
                          {"description": "Holger Rune", "status": "O", "price": {"american": "-190"}}]}]}]},
        {"id": "2", "live": True, "startTime": 1790000000000, "displayGroups": [{"markets": [
            {"description": "Moneyline", "status": "S", "period": {"main": True, "live": True},
             "outcomes": [{"description": "A Guy", "price": {"american": "+150"}},
                          {"description": "B Guy", "price": {"american": "-190"}}]}]}]},
        {"id": "3", "live": False, "startTime": 1790000000000, "displayGroups": [{"markets": [
            {"description": "Moneyline", "period": {"main": True, "live": False},
             "outcomes": [{"description": "C Guy", "price": {"american": "+150"}},
                          {"description": "D Guy", "price": {"american": "-190"}}]}]}]}]},
        {"path": [{"description": "WTA Wuhan"}], "events": []},
        {"path": [{"description": "ATP Challenger Tour"}], "events": [{"id": "4", "live": True}]}]
    rows = stn.parse_bovada(bov, live=True)
    assert len(rows) == 2 and {r["a"] for r in rows} == {"Jannik Sinner", "A Guy"}
    by = {r["a"]: r for r in rows}
    assert by["Jannik Sinner"]["a_ml"] == 150 and not by["Jannik Sinner"]["suspended"] and by["A Guy"]["suspended"]
    assert by["Jannik Sinner"]["tour"] == "atp"
    assert len(stn.parse_bovada(bov)) == 3, "pregame parsing unchanged (every priced event)"
    # ESPN's live score: who's serving and the points, when the feed has them
    pay = {"events": [{"id": "9", "name": "Shanghai Masters", "groupings": [{"grouping": {"displayName": "Men's Singles"}, "competitions": [
        {"id": "77", "date": "2026-09-28T10:00Z", "status": {"type": {"name": "STATUS_IN_PROGRESS", "detail": "2nd Set"}},
         "competitors": [{"athlete": {"id": "1", "displayName": "Jannik Sinner"}, "possession": True, "points": "30",
                          "linescores": [{"value": 4}, {"value": 2}]},
                         {"athlete": {"id": "2", "displayName": "Holger Rune"}, "possession": False, "points": "15",
                          "linescores": [{"value": 6}, {"value": 2}]}]}]}]}]}
    r = stn.parse_espn(pay)[0]
    assert r["server"] == 1 and (r["pts1"], r["pts2"]) == ("30", "15") and stn._state(r) == "live"
    s = stl.score_state(r)
    assert s["pts"] == (2, 1) and "(30-15)" in stl.score_text(r, s) and "Sinner serving" in stl.clock_text(r, s)


def test_dashboard_tennis_records():
    """Men's and women's tennis: two records boxes, two By sport rows, a parlay record per tour (old mixed parlays
    only under their old label), the card split by tour; tennis LIVE plays count in LIVE PLUS MONEY only."""
    import sports_dashboard as dash
    tmp = tempfile.mkdtemp()
    keep = sd.DATA
    today = datetime.now(sports_live.PT).date().isoformat()
    try:
        sd.DATA = tmp
        os.makedirs(os.path.join(tmp, "tennis"))
        L = lambda mid, res, tour, side=1: {"id": f"{mid}:{side}", "match": mid, "side": side, "player": f"Player {mid}", "opp": "Opp",
                                            "tour": tour, "odds": -130, "p": 0.6, "start": f"{today}T10:00Z", "tourney": "Open",
                                            "market": "ml", "hcp": None, "round": "R1", "surface": "hard", "bo": 3, "result": res,
                                            "breakdown": ["🎾 x"]}
        old = {"date": "2026-09-01", "picks": [L("atp:1", "won", "atp"), L("wta:1", "lost", "wta"), L("atp:2", "won", "atp")],
               "parlay": {"legs": ["atp:1:1", "wta:1:1", "atp:2:1"], "status": "lost", "dec": 6.0, "american": 500}}
        new = {"date": today, "picks": [L("atp:3", "won", "atp"), L("atp:4", None, "atp"), L("atp:5", "won", "atp"),
                                        L("atp:6", None, "atp"), L("wta:2", "won", "wta"), L("wta:3", None, "wta"), L("wta:4", "lost", "wta")],
               "parlays": {"atp": {"legs": ["atp:3:1", "atp:4:1", "atp:5:1"], "status": "open", "dec": 5.0, "american": 400, "tour": "atp"},
                           "wta": {"legs": ["wta:2:1", "wta:3:1", "wta:4:1"], "status": "lost", "dec": 5.0, "american": 400, "tour": "wta"}}}
        dup = {"date": "2026-09-02", "picks": [L("atp:1", "won", "atp")], "parlays": {"atp": None, "wta": None}}   # the same match again
        with open(os.path.join(tmp, "tennis", "picks.json"), "w") as f:
            json.dump([old, dup, new], f)
        live = {"plays": {"tennis:atp:88:1": {"league": "tennis", "tour": "atp", "team": "Jannik Sinner", "odds": 180, "side": "1",
                                              "result": "won", "date": today, "posted": f"{today}T11:00Z", "double_down": True,
                                              "match": "atp:88", "tennis": {"sets": [0, 1], "games": [2, 2], "done": [[4, 6]], "side": 1, "set_no": 2},
                                              "score_at_post": "Sinner vs Rune · 4-6, 2-2", "clock_at_post": "Set 2", "p": 0.45}}}
        with open(os.path.join(tmp, "live_log.json"), "w") as f:
            json.dump(live, f)
        html = dash.render([], {"params": {}}, {}, [], 1000, int(time.time() * 1000))
        R = dash.RECORDS
        assert R["men's tennis (own record, not ours)"] == "4-0", R          # atp:1 once (two slates), 2, 3, 5
        assert R["women's tennis (own record, not ours)"] == "1-2", R
        assert R["men's tennis parlays"] == "0-0" and R["women's tennis parlays"] == "0-1"
        assert R["old mixed tennis parlays (before the tours were split)"] == "0-1"
        assert R["by sport"]["Men's Tennis"] == "4-0" and R["by sport"]["Women's Tennis"] == "1-2" and "Tennis" not in R["by sport"]
        assert R["live plus money (own record, not ours)"] == "1-0", "the tennis live play counts in LIVE PLUS MONEY"
        assert "tennis (own record, not ours)" not in R
        assert "🎾 MEN&#x27;S TENNIS" in html or "🎾 MEN'S TENNIS" in html
        assert "🎾 WOMEN'S TENNIS</div>" in html and "🎾 MEN'S TENNIS</div>" in html and ">🎾 TENNIS<" not in html
        assert "<b>🎾 Men's Tennis</b>" in html and "<b>🎾 Women's Tennis</b>" in html and "<b>🎾 Tennis</b>" not in html
        assert "4 men's + 3 women's" in html, "the card's summary line"
        assert "MEN'S TENNIS 3-LEG PARLAY" in html and "WOMEN'S TENNIS" in html
        # the owner's rule (9/28): EVERY parlay title says how many legs it has
        titles = [x for x in re.findall(r'class="pk-l[^"]*">([^<]*)<', html) if "PARLAY" in x]
        assert titles and all(re.search(r"\d-LEG (LEAN )?PARLAY", x) for x in titles), titles
        assert "parlays: men's 0-0 · women's 0-1 · old mixed 0-1" in html
        assert "🎾 Men&#x27;s Tennis · 🔁 DOUBLE DOWN" in html and "4-6, 2-2 in set 2" in html, "the live list: 🎾 and the set/game score"
        assert html.count("class=\"rc gr\"") >= 6
        _check_js(html)
    finally:
        sd.DATA = keep
        shutil.rmtree(tmp)


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
    assert b["solo"] and b["solo"]["legs"][0]["team"] == "A" and not b["lock"], b     # one-game coin flip: a pick, not the LOTD
    print("ok test_one_game_always_picks")


def test_dog_traps():
    """The big study: a dog in a spot the books still overprice is never a real play; a proven price check shifts reads."""
    import sports_dogs
    st = {"nhl": {"traps": ["+140-179|away|on b2b"], "proven": [], "price": {"proven": True, "shifts": {"5": 0.2}}}}
    assert sports_dogs.verdict(st, "nhl", 150, False, "on b2b") == "trap"
    assert sports_dogs.verdict(st, "nhl", 150, True) is None
    assert sports_dogs.adjust(st, "nhl", 0.65) > 0.65 and sports_dogs.adjust(st, "nba", 0.65) == 0.65
    c = {"edge": 0.2, "edge_own": 0.2, "reasons": ["x", "proven spot: y"], "trap": True, "odds": 150, "dec": 2.5, "p": 0.48}
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


def test_team_trend_atoms():
    """The explorer's team trends on synthetic NFL games: the ATS streak and season ATS rate counted right, a result
    from the same day (under 6 hours earlier) is never seen, prime-time records only on prime-time games, 1Q form,
    O/U streaks, the opponent versions; first-part bets graded only at real prices; the pooled family test runs."""
    import sports_explorer as ex

    def mk(gid, start, home, away, hs, as_, line=-3.0, ls=("7,7,7,6", "0,7,3,10"), total=40.0):
        return {"id": gid, "league": "nfl", "start": start, "status": "final", "stype": "2", "home": home,
                "away": away, "home_name": home, "away_name": away, "home_score": str(hs), "away_score": str(as_),
                "neutral": "0", "ml_home": "-160", "ml_away": "140", "spread_home": str(line),
                "spread_home_odds": "-110", "spread_away_odds": "-110", "total": str(total), "over_odds": "-110",
                "under_odds": "-110", "ls_home": ls[0], "ls_away": ls[1]}
    games = {}
    sun = datetime(2024, 9, 8, 17, 0, tzinfo=timezone.utc)                  # Sunday 1pm ET
    iso = "%Y-%m-%dT%H:%MZ"
    for w in range(5):                                                       # A covers (and goes over) 5 straight
        games[f"a{w}"] = mk(f"a{w}", (sun + timedelta(weeks=w)).strftime(iso), "A", f"O{w}", 27, 20)
    t5 = sun + timedelta(weeks=5)
    games["a5"] = mk("a5", t5.strftime(iso), "A", "O5", 17, 20)                  # fails to cover (and under)
    games["a6"] = mk("a6", (t5 + timedelta(hours=3)).strftime(iso), "A", "O6", 30, 20)   # same day, 3h later
    games["a7"] = mk("a7", (sun + timedelta(weeks=6)).strftime(iso), "A", "O7", 24, 20)
    mnf = datetime(2024, 9, 10, 0, 15, tzinfo=timezone.utc)                 # Monday 8:15pm ET
    for w in range(5):                                                       # P wins 5 Monday nights
        games[f"p{w}"] = mk(f"p{w}", (mnf + timedelta(weeks=w)).strftime(iso), "P", f"Q{w}", 24, 10)
    games["p5"] = mk("p5", "2024-10-14T00:20Z", "Q5", "P", 10, 24, line=3.0)   # Sunday night, P on the road
    games["p6"] = mk("p6", "2024-10-20T17:00Z", "P", "Q6", 24, 10)             # Sunday day game
    L = ex.League("nfl", games)
    got = {}
    for g in sm.finals(games, "nfl"):
        t = sm._ts(g["start"])
        L.advance(t)
        got[g["id"]] = {s: L.side_atoms(g, s, t) for s in ("home", "away")}
        got[g["id"]]["game"] = L.game_atoms(g, t)
        L.pending.append((t, g))

    pre = tuple(o + x + ":" for x in ("ats", "atsr", "rats", "pt", "divr", "q1", "ou") for o in ("", "o"))

    def tt(gid, side):
        return sorted(a for a in got[gid][side] if a.startswith(pre))
    assert tt("a0", "home") == [] and tt("a2", "home") == []                      # 2 covers: no streak yet
    assert "ats:w3" in tt("a3", "home") and "ats:w5" not in tt("a3", "home")
    a5 = tt("a5", "home")
    assert "ats:w3" in a5 and "ats:w5" in a5 and "oats:w5" in tt("a5", "away") and "ou:o4" in a5, a5
    a6 = tt("a6", "home")                                                        # a5's loss is only 3h old: unseen
    assert "ats:w5" in a6 and "ou:o4" in a6 and "ats:l3" not in a6, a6
    a7 = tt("a7", "home")                                                        # fail, cover -> streak +1
    assert not any(a.startswith("ats:") for a in a7), a7
    assert "atsr:hi" in a7 and "q1:won" in a7 and "oq1:won" in tt("a7", "away"), a7    # 6/7 covers, 7/7 1Qs
    assert "h.q1:won" in got["a7"]["game"] and "h.atsr:hi" in got["a7"]["game"]
    assert not any(a.startswith(("pt:", "opt:")) for g in got for s in ("home", "away") for a in tt(g, s)
                   if g != "p5"), "prime-time atoms off prime time"
    assert "pt:strong" in tt("p5", "away") and "opt:strong" in tt("p5", "home")     # SNF, 5-0 on Monday nights
    assert "pt:strong" not in tt("p6", "home")                                     # a Sunday day game
    assert L.prime(games["p0"]) and L.prime(games["p5"]) and not L.prime(games["p6"])
    # the road ATS rate: P covered 1 road game only -> nothing yet
    assert not any(a.startswith("rats:") for a in tt("p6", "away"))
    # first-part grading: real prices only, a tie is no bet
    mlb = {"ls_home": "1,0,2,0,0,3,0,0,0", "ls_away": "0,0,0,1,0,0,0,0,4", "h1_ml_home": "-150", "h1_ml_away": "130",
           "h1_spread_home": "-0.5", "h1_spread_home_odds": "-120", "h1_spread_away_odds": "100"}
    h, a = ex._grade_p1(mlb, "home", "mlb"), ex._grade_p1(mlb, "away", "mlb")
    assert h["p1ml"][0] and not a["p1ml"][0] and abs(h["p1ml"][2] - 100 / 150) < 1e-9 and a["p1ml"][2] == -1.0
    assert h["p1spread"][0] and abs(h["p1spread"][1] + a["p1spread"][1] - 1) < 1e-9
    assert ex._grade_p1({**mlb, "ls_away": "1,0,2,0,0,0,0,0,9"}, "home", "mlb")["p1ml"] is None      # F5 tied
    assert ex._grade_p1({**mlb, "h1_spread_away_odds": ""}, "home", "mlb")["p1spread"] is None       # no price
    assert ex._grade_p1(mlb, "home", "nfl") == {"p1ml": None, "p1spread": None}                      # no 1Q lines
    bad = {**mlb, "h1_spread_home": "-1.5", "h1_spread_home_odds": "310", "h1_spread_away_odds": "175"}
    assert ex._grade_p1(bad, "home", "mlb")["p1spread"] is None                  # not one market's two sides
    # the pooled family test: follow + fade are the two sides of the same bets
    _, side, game = ex.build(games, "nfl")
    fam = ex.family_tests({"nfl": (side, game)})
    c = fam["team ATS streak 3+|spread"]
    assert c["n"] >= 3 and abs(c["follow"]["hit"] + c["fade"]["hit"] - 1) < 1e-9 and not c["follow"]["passes"], c
    assert "O/U streak 4+|total" in fam and any("team ATS streak 3+|spread" in x for x in ex.family_lines(fam))


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


def _ctx_games(seasons, seed, div_edge=0.2, first=2010):
    """Simulated NHL: 12 teams, 2 conferences x 2 divisions of 3. A season: division pairs meet 6 times, conference
    pairs 3, the other conference 2 (33 games a team). Fairly priced (with juice) off fixed team strengths; planted:
    in DIVISION games the home team wins `div_edge` more often than its price says. Totals are a pure coin flip."""
    rnd = random.Random(seed)
    teams = [f"c{i}" for i in range(12)]
    power = {t: (i % 6 - 2.5) / 2.0 for i, t in enumerate(teams)}

    def am(q):
        dec = 1 / (q * 1.025)
        return int((dec - 1) * 100) if dec >= 2 else int(-100 / (dec - 1))
    games = {}
    for y in range(first, first + seasons):
        mus = []
        for i, a in enumerate(teams):
            for b in teams[i + 1:]:
                ia, ib = teams.index(a), teams.index(b)
                n = 6 if ia // 3 == ib // 3 else 3 if ia // 6 == ib // 6 else 2
                mus += [(a, b, ia // 3 == ib // 3) if k % 2 else (b, a, ia // 3 == ib // 3) for k in range(n)]
        rnd.shuffle(mus)
        day0 = datetime(y, 10, 10, 23, 0, tzinfo=timezone.utc)
        for k, (h, a, div) in enumerate(mus):
            p = 1 / (1 + math.exp(-(power[h] - power[a] + 0.1)))
            won = rnd.random() < min(0.95, p + (div_edge if div else 0.0))
            over = rnd.random() < 0.5
            gid = f"nhl:c{y}_{k}"
            games[gid] = {"id": gid, "league": "nhl", "start": (day0 + timedelta(hours=k * 22)).strftime("%Y-%m-%dT%H:%MZ"),
                          "status": "final", "stype": "2", "home": h, "away": a, "home_name": h, "away_name": a,
                          "home_score": "4" if won else "1", "away_score": ("1" if won else "4") if over else ("0" if won else "2"),
                          "ml_home": str(am(p)), "ml_away": str(am(1 - p)), "neutral": "0", "total": "4.5",
                          "over_odds": "-110", "under_odds": "-110"}
            if not over:
                games[gid]["home_score"] = "2" if won else "0"
    return games


def test_context():
    """The context study: a planted division edge is found, PROVEN and confirmed on later games (and killed when it
    vanishes); noise never is; divisions/conferences come out of the schedule; travel miles; stakes; refs are skipped
    until officials.json exists; the engine hook moves only proven factors and takes only the strongest one."""
    import sports_context as sc
    import sports_news
    import sports_breakdown as sb
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "context.json")
    games = _ctx_games(10, 3)
    st = sc.study(games, path, officials=None, sims=2, leagues=("nhl",), verbose=False)
    nhl = st["nhl"]
    c = nhl["cells"]["div|ml|home"]
    assert c["proven"] and "div|ml|home" in nhl["proven"], c
    assert c["n"] >= sc.MIN_N and c["roi_old"] > 0 and c["roi_new"] > 0 and c["z"] >= sc.Z_PROOF and c["edge"] > 0.1, c
    for k in ("conf|ml|home", "nonconf|ml|home", "div|total|over", "div|total|under", "conf|ml|road"):
        assert not nhl["cells"][k].get("proven"), ("noise is never promoted", k, nhl["cells"][k])
    assert set(nhl["proven"]) <= {"div|ml|home", "div|ml|fav", "div|ml|dog"}, nhl["proven"]
    m = st["_meta"]
    assert m["tested"] > 10 and 0 < m["expected_false_positives"] < 1 and m["refs"].startswith("skipped"), m
    assert st["registry"]["nhl|div|ml|home"]["status"] == "proven" and nhl["shifts"]["div|ml|home"] > 0.2
    # divisions + conferences from the schedule alone
    W = sc.Walker("nhl", games)
    S = W.sched
    assert S.rel("c0", "c1", 2012) == "div" and S.rel("c0", "c4", 2012) == "conf" and S.rel("c0", "c7", 2012) == "nonconf"
    conf = S.conferences(2012)
    assert conf and len({conf[f"c{i}"] for i in range(6)}) == 1 and conf["c0"] != conf["c6"], conf
    # forward confirmation: the same edge on two more seasons -> confirmed; a copy where it vanishes -> killed
    shutil.copy(path, path + ".kill")
    later = {**games, **_ctx_games(2, 4, first=2020)}
    st2 = sc.study(later, path, officials=None, sims=0, leagues=("nhl",), verbose=False)
    e = st2["registry"]["nhl|div|ml|home"]
    assert e["status"] == "confirmed" and e["fwd"]["n"] >= sc.FWD_N and "div|ml|home" in st2["nhl"]["confirmed"], e
    gone = {**games, **_ctx_games(2, 5, div_edge=-0.3, first=2020)}
    st3 = sc.study(gone, path + ".kill", officials=None, sims=0, leagues=("nhl",), verbose=False)
    assert "div|ml|home" in st3["nhl"]["killed"] and "div|ml|home" not in st3["nhl"]["shifts"], st3["nhl"]["killed"]
    # the engine hook: only proven factors move a number, and only the strongest one counts
    up = {"id": "nhl:up", "league": "nhl", "start": "2020-03-01T23:00Z", "status": "pre", "stype": "2", "home": "c0",
          "away": "c1", "home_name": "c0", "away_name": "c1", "ml_home": "-110", "ml_away": "-110", "neutral": "0"}
    f = sc.Index(games, officials=None).facts(up)
    assert f["rel"] == "div"
    assert sc.adjust_side(st, "nhl", f, "home", 0.5) > 0.55 and sc.adjust_side(st, "nhl", f, "away", 0.5) < 0.45
    assert sc.adjust_side(st, "nba", f, "home", 0.5) == 0.5 and sc.adjust_side({}, "nhl", f, "home", 0.5) == 0.5
    assert sc.adjust_total(st, "nhl", f, 0.5) == 0.5
    assert sc.reasons(st, "nhl", f, "home") and not sc.reasons(st, "nhl", f, "away")
    far = dict(up, away="c7", away_name="c7")
    assert sc.adjust_side(st, "nhl", sc.Index(games, officials=None).facts(far), "home", 0.5) == 0.5
    assert sc.best([(0.1, "a"), (-0.3, "b"), (0.2, "c")]) == (-0.3, "b") and sc.best([]) == (0.0, None)
    old = sports.CONTEXT_ST, sports.SPOTS_ST, sports.EXPLORER_ST
    sports.CONTEXT_ST, sports.SPOTS_ST, sports.EXPLORER_ST = st, {}, {}
    s, name = sports.study_shift(games, up, "ml", f)
    assert s > 0 and name == "context:div|ml|home" and sports.study_shift(games, up, "spread", f) == (0.0, None)
    sports.CONTEXT_ST, sports.SPOTS_ST, sports.EXPLORER_ST = old
    # stakes, walked forward from results: late in a season somebody has clinched and somebody is out
    spots = sc.SPOTS["nhl"]
    sc.SPOTS["nhl"] = lambda s: 2                       # (6-team conferences: 2 playoff spots each)
    tbl = sc.facts_table(dict(games), "nhl", None)
    last = [x for x in sorted(games.values(), key=lambda x: x["start"]) if sc.season("nhl", x["start"]) == 2011][-12:]
    stk = [tbl[x["id"]][k].get("stk") for x in last for k in ("h", "a")]
    assert "clinched" in stk and ("elim" in stk or "out" in stk), stk
    early = sorted(games.values(), key=lambda x: x["start"])[5]
    assert "stk" not in tbl[early["id"]]["h"], "no stakes before 70% of the season"
    mw = next((tbl[x["id"]] for x in last if tbl[x["id"]]["h"].get("mustwin") or tbl[x["id"]]["a"].get("mustwin")), None)
    if mw:
        k, o = ("h", "a") if mw["h"].get("mustwin") else ("a", "h")
        assert mw[k]["stk"] == "race" and mw[o].get("stk") != "race"
    sc.SPOTS["nhl"] = spots
    # travel: great-circle miles, direction, a road trip's week of miles, road games in 6 days
    ven = {"NY|NY|": [40.71, -74.0, 10, ""], "LA|CA|": [34.05, -118.24, 90, ""], "SF|CA|": [37.77, -122.42, 16, ""],
           "SEA|WA|": [47.61, -122.33, 50, ""]}

    def gm(i, day, h, a, city, st_):
        return {"id": f"nba:t{i}", "league": "nba", "start": f"2023-01-{day:02d}T03:00Z", "status": "final", "stype": "2",
                "home": h, "away": a, "home_name": h, "away_name": a, "home_score": "100", "away_score": "90",
                "ml_home": "-150", "ml_away": "130", "neutral": "0", "city": city, "state": st_, "country": ""}
    tg = {g["id"]: g for g in (gm(1, 2, "NYK", "X", "NY", "NY"), gm(2, 5, "LAL", "NYK", "LA", "CA"),
                               gm(3, 6, "GSW", "NYK", "SF", "CA"), gm(4, 8, "SEA", "NYK", "SEA", "WA"),
                               gm(5, 9, "LAL", "X", "LA", "CA"), gm(6, 10, "GSW", "X", "SF", "CA"))}
    Wt = sc.Walker("nba", tg, ven=ven)
    f2, f3, f4 = (Wt.facts(tg[f"nba:t{i}"]) for i in (2, 3, 4))
    assert 2400 < f2["a"]["mi"] < 2500 and f2["a"]["dir"] == "W", f2["a"]           # New York -> Los Angeles
    assert 330 < f3["a"]["mi"] < 360 and f3["a"]["road6"] == 2, f3["a"]               # LA -> SF the next night
    assert 670 < f4["a"]["mi"] < 700 and f4["a"]["road6"] == 3, f4["a"]               # SF -> Seattle, 3rd road game
    assert f4["a"]["wk"] > 3400 and "trip2000" in sc.flags(f2)[1] and "west1000" in sc.flags(f2)[1]
    assert "road3in6" in sc.flags(f4)[1] and "road3in6" not in sc.flags(f3)[1]
    assert f2["h"]["mi"] == 0 and "trip1000" not in sc.flags(f2)[0]
    assert sc.miles((40.71, -74.0), (40.71, -74.0)) == 0
    # a college team at 5 wins going for 6
    cf = {}
    for i in range(9):
        cf[f"ncaaf:b{i}"] = {"id": f"ncaaf:b{i}", "league": "ncaaf", "start": f"2023-{9 + i // 4:02d}-{1 + (i % 4) * 7:02d}T20:00Z",
                             "status": "final", "stype": "2", "home": "U", "away": f"o{i}", "home_name": "U",
                             "away_name": f"o{i}", "home_score": "30" if i < 5 else "10", "away_score": "20", "neutral": "0"}
    fb = sc.facts_table(cf, "ncaaf", None)
    assert fb["ncaaf:b8"]["h"].get("bowl5") and not fb["ncaaf:b7"]["h"].get("bowl5") and not fb["ncaaf:b5"]["h"].get("bowl5")
    # refs: skipped cleanly until officials.json exists; with it, a crew that leans over is flagged (earlier games only)
    assert sc.load_officials(os.path.join(tmp, "nope.json")) is None
    offs = {gid: [["Referee", "Ref Over" if i % 2 else "Ref Plain"]] for i, gid in enumerate(sorted(games))}
    for gid, o in offs.items():
        if o[0][1] == "Ref Over":
            games[gid]["away_score"], games[gid]["home_score"] = "3", games[gid]["home_score"] if \
                games[gid]["home_score"] == "4" else "2"
    tr = sc.facts_table(games, "nhl", offs)
    late = sorted(games, key=lambda k: games[k]["start"])[-50:]
    over_flag = [("ref_over" in sc.flags(tr[k])[2]) for k in late if offs[k][0][1] == "Ref Over"]
    assert over_flag and all(over_flag) and not any("ref_over" in sc.flags(tr[k])[2] for k in late
                                                   if offs[k][0][1] == "Ref Plain")
    assert sc.parse_officials({"gameInfo": {"officials": [{"displayName": "Bill Vinovich", "position": {"displayName": "Referee"}}]}}) \
        == [["Referee", "Bill Vinovich"]]
    assert sc.key_officials("mlb", [["Home Plate Umpire", "A"], ["First Base Umpire", "B"]]) == ["A"]
    # the backfill walks games in chunks and saves them (a fake fetcher here - ESPN is blocked in this container)
    bf = os.path.join(tmp, "officials.json")
    n, _ = sc.refs_backfill(budget_s=30, path=bf, games=dict(list(games.items())[:30]),
                            fetch=lambda lg, eid: [["Referee", f"R{int(eid.split('_')[1]) % 3}"]], chunk=10)
    assert n == 30 and len(sc.load_officials(bf)) == 30
    # pregame talk: forward-only tags, never drama
    assert sports_news.talk_kinds("Coach says Sunday is a must-win game") == ["must-win"]
    assert sports_news.talk_kinds("QB guarantees a win over the Jets") == ["trash talk"]
    assert sports_news.talk_kinds("Rookie scores twice in win") == []
    nw = {"nfl:1": [{"id": "a|must-win", "kind": "must-win", "date": "2026-09-27", "talk": 1},
                    {"id": "b", "kind": "suspension", "date": "2026-09-26"}]}
    assert [e["kind"] for e in sports_news.drama(nw, "nfl", "1")] == ["suspension"]
    assert [e["kind"] for e in sports_news.talk(nw, "nfl", "1", today=datetime(2026, 9, 28).date())] == ["must-win"]
    # breakdown lines in our voice, never a repeated wording on one board
    used = set()
    v = sb.Voice("x", used)
    leg = {"market": "ml", "league": "nba", "ctx": [{"k": "div"}, {"k": "trip", "mi": 1900, "road6": 3, "dir": "W"},
                                   {"k": "dome_cold", "who": "them"}, {"k": "mustwin", "rec": "9-7"}],
           "talk_theirs": [{"kind": "trash talk"}]}
    lines = sb.context_lines(leg, v, "Bears", "Rams", "the Bears", "the Rams", {"wx_temp": "38", "wx_wind": "18"})
    assert len(lines) == 5 and any("1,900-mile" in x and "3rd road game in 6 days" in x for x in lines), lines
    assert all("real talk" not in x.lower() and "chalk" not in x.lower() for x in lines)
    lines2 = sb.context_lines(leg, sb.Voice("y", used), "Bears", "Rams", "the Bears", "the Rams", {"wx_temp": "38"})
    assert not set(lines) & set(lines2)
    shutil.rmtree(tmp)


def test_tennis_edge():
    """The tennis edge study: a soft book's planted mispricing is found on the older half and forward-confirmed,
    noise never gets promoted, nothing is retested on the same data, a suspect whose edge disappears is killed,
    and adjust() leaves p alone unless a proven angle matches."""
    import sports_tennis_edge as te
    tmp = tempfile.mkdtemp()
    hist, path = os.path.join(tmp, "hist.csv.gz"), os.path.join(tmp, "edge.json")
    _tennis_hist(hist, 40, None)
    assert "loading" in te.study(path, hist, matches=None, lines=None, verbose=False)["skipped"]   # waits for the history
    min_s, te.MIN_SEASONS = te.MIN_SEASONS, 0
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
    r5 = te.study(noise_path, hist, batch=1200, **kw)                              # (the life atoms added more)
    assert r5["proven"] == [] and r5["tested"] > 400 and "atp|pin|surf:clay" in te.LAST_TESTED, r5
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
    te.MIN_SEASONS = min_s
    shutil.rmtree(tmp)


def test_tennis_favs():
    """The heavy-favorites study (research only): American price bands at the right edges; a soft book planted too
    generous on favorites shows up as profit at that book (and is proven) while Pinnacle's efficient close is not;
    parlay tickets are 3 legs of one tour, one day, three different matches, all inside the cap; the split is
    taken from edge.json; the whole run writes favs.json."""
    import sports_tennis_favs as tf
    assert tf.american(1.5) == -200 and tf.band_of(1.5) == "-151..-200" and tf.band_of(1.2) == "-301..-500"
    assert tf.band_of(1.19) == "-500+" and tf.band_of(1.67) == "-101..-150" and tf.band_of(1.99) == "-101..-150"
    assert tf.band_of(2.0) is None and tf.band_of(3.1) is None and tf.band_of(1.34) == "-201..-300"
    assert tf.level3("500") == "other" and tf.level3("slam") == "slam"
    tmp = tempfile.mkdtemp()
    hist, out, edge = (os.path.join(tmp, n) for n in ("hist.csv.gz", "favs.json", "edge.json"))
    split = _tennis_hist(hist, 80, lambda w, tour, fav: 1.3 if fav else 1.0)   # Bet365 way too long on favorites
    split = (datetime.strptime(split, "%Y-%m-%d") - timedelta(days=7 * 40)).strftime("%Y-%m-%d")
    with open(edge, "w") as f:
        json.dump({"split": split}, f)
    r = tf.study(out, hist, edge, verbose=False)
    with open(out) as f:
        saved = json.load(f)
    assert saved["split"] == split and r["research_only"] and saved["proven"] == r["proven"]
    assert r["data"]["rated_for_model"] > 1000 and "model+2%" in r["straights"]["atp"]["pin"]
    assert any(k.startswith("atp|b365|all|") for k in r["proven"]), r["proven"]
    assert not any(k.startswith(("atp|pin|all|", "wta|pin|all|")) and "parlay" not in k for k in r["proven"]), r["proven"]
    b = r["straights"]["atp"]["b365"]["all"]
    # (near 50/50 the planted Bet365 "favorite" is often the real underdog, so the closest band is left out)
    assert sum(s["all"]["roi"] * s["all"]["n"] for k, s in b.items() if s and k != "-101..-150") > 0
    p = r["straights"]["atp"]["pin"]["all"]
    assert sum(s["all"]["roi"] * s["all"]["n"] for s in p.values() if s) < 0
    assert all(set(s) <= {"all", "bo3", "bo5", "slam", "1000", "other"} for s in b.values())
    assert "bo5" not in "".join(k for s in r["straights"]["wta"]["pin"]["all"].values() for k in s)
    # the parlay tickets themselves
    ms = [m for m in tf.te.build(tf.te.read_hist(hist))[1] if m.tour == "wta"]
    fv = tf.favorites(ms, {}, "pin", split)
    tk = tf.tickets(fv, 200, "all")
    assert tk and len({d for d, _ in tk}) == len(tk)
    for d, legs in tk:
        assert len(legs) == 3 and len({(x[0].W, x[0].L) for x in legs}) == 3
        assert all(x[0].d == d and x[0].tour == "wta" and 1.5 - 1e-9 <= x[1] < 2.0 for x in legs)
    ps = tf.parlay_stats(tk, split)
    assert ps["all"]["tickets"] == len(tk) == ps["old"]["tickets"] + ps["new"]["tickets"]
    assert 0 < ps["all"]["fair_hit"] < 0.25 and 0 < ps["old"]["p_profit_if_no_edge"] < 0.5
    assert tf.study(os.path.join(tmp, "x.json"), os.path.join(tmp, "none.gz"), edge, verbose=False).get("skipped")
    shutil.rmtree(tmp)


def test_tennis_set1_math():
    """The implied first-set chance: the interpolated table matches the exact serve_split route, 50/50 stays 50/50,
    it's symmetric and monotone, a set is always closer to a coin flip than the match (more so in best of 5), and
    two independent sets at that chance roughly rebuild the best-of-3 match chance."""
    import sports_tennis_set1 as s1
    assert abs(s1.set1_from_serve(0.64, 0.64) - 0.5) < 1e-9
    for tour in ("atp", "wta"):
        assert abs(s1.set1_p(0.5, tour, 3) - 0.5) < 1e-6 and abs(s1.set1_p(0.5, tour, 5) - 0.5) < 1e-6
        prev = 0.0
        for k in range(2, 99, 4):
            p = k / 100
            q3, q5 = s1.set1_p(p, tour, 3), s1.set1_p(p, tour, 5)
            assert q3 > prev, "monotone"
            prev = q3
            assert abs(q3 + s1.set1_p(1 - p, tour, 3) - 1) < 1e-3, "symmetric"
            if p > 0.5:
                assert 0.5 < q5 < q3 < p, (p, q3, q5)
            if k % 12 == 2:
                assert abs(q3 - s1.set1_exact(p, tour, 3)) < 1e-3 and abs(q5 - s1.set1_exact(p, tour, 5)) < 1e-3
            assert abs(q3 * q3 * (3 - 2 * q3) - p) < 0.02, "two iid sets ~ the bo3 match chance"
    assert abs(s1.set1_p(0.8, "atp", 5, 10) - s1.set1_p(0.8, "atp", 5, 7)) < 0.01      # (the final-set tiebreak barely matters)
    # the log loss / ROI arithmetic
    a = s1.Acc()
    for _ in range(10):
        a.add(1, 0.5, 1 / (0.5 * 1.05))
    r = a.rep()
    assert r["hit"] == 1.0 and abs(r["roi"] - (1 / 0.525 - 1)) < 1e-3 and r["z"] > 3
    assert abs(s1.slope_of([(0.7, 1), (0.7, 0), (0.7, 1), (0.3, 0), (0.3, 1), (0.3, 0)] * 50) - 0.8) < 0.3


def test_tennis_set1_no_peeking():
    """The crew's stat is walk-forward: a match (and every match that day) only sees earlier days - changing a day's
    results never changes that day's stats; the window is the last 20 and 10 are needed; a planted first-set
    specialist is found; the whole study runs on a history file and fixes its split."""
    import sports_tennis_set1 as s1
    rnd = random.Random(3)
    rows = []
    for day in range(60):
        d = f"2020-{1 + day // 28:02d}-{1 + day % 28:02d}"
        ps = rnd.sample(range(8), 8)
        for a, b in zip(ps[::2], ps[1::2]):
            p = 0.5 + 0.05 * (a - b) / 8
            y = 1 if rnd.random() < p else 0
            rows.append((d, "atp", f"P{a}", f"P{b}", y, p, 3, p))
    rows.sort(key=lambda r: r[0])
    bets, full = s1.walk(rows)
    assert bets and all(len(full[k]) == 60 for k in full), "every result is learned"
    first_day = min(b[0] for b in bets)
    assert sum(1 for r in rows if r[0] < first_day) >= 4 * 10, "nobody has a stat before 10 matches"
    cut = sorted({r[0] for r in rows})[30]
    changed = [(r[0], r[1], r[2], r[3], 1 - r[4], r[5], r[6], r[7]) if r[0] >= cut else r for r in rows]
    b2, _ = s1.walk(changed)
    assert [b[:4] for b in bets if b[0] <= cut] == [b[:4] for b in b2 if b[0] <= cut], "no peeking at the same day or later"
    assert [b[:4] for b in bets if b[0] > cut] != [b[:4] for b in b2 if b[0] > cut]
    h = full[("atp", "P0")]
    assert all(h[i][0] <= h[i + 1][0] for i in range(len(h) - 1))
    # the window: the stat is the mean over the last 20
    hist = [(1, 0.5)] * 5 + [(0, 0.5)] * 20
    from collections import deque
    dq = deque(maxlen=s1.WINDOW)
    for x in hist:
        dq.append(x)
    assert s1._stat(dq) == (-0.5, 0.0) and s1._stat([(1, 0.5)] * 9) is None
    # a planted first-set specialist (wins set 1 at 80% whatever the price): the overperformance test finds it
    rows = []
    for day in range(400):
        d = (datetime(2014, 1, 1) + timedelta(days=day)).strftime("%Y-%m-%d")
        ps = rnd.sample(range(10), 10)
        for a, b in zip(ps[::2], ps[1::2]):
            p = 0.5
            pa = 0.8 if a == 0 else 0.2 if b == 0 else 0.5
            y = 1 if rnd.random() < pa else 0
            rows.append((d, "wta", f"P{a}", f"P{b}", y, p, 3, p))
    bets, _ = s1.walk(rows)
    split = sorted(b[0] for b in bets)[len(bets) // 2]
    res = s1.crew_test(bets, split, 0, (0.3,))
    r = res["0.30"]
    assert r["all"]["n"] >= 300 and r["all"]["z"] >= 3.5 and r["older"]["roi"] > 0 and r["newer"]["roi"] > 0 and r["proven"]
    assert s1.closest(res)["misses"][0].startswith("nothing")
    # the whole study on a simulated history (efficient prices: nothing should come close)
    tmp = tempfile.mkdtemp()
    try:
        hist_p, out = os.path.join(tmp, "hist.csv.gz"), os.path.join(tmp, "set1.json")
        _tennis_hist(hist_p, 40, None)
        t0 = time.time()
        rep = s1.study(out, hist_p, os.path.join(tmp, "none.json"), os.path.join(tmp, "none.csv"), verbose=False)
        assert time.time() - t0 < 60 and rep["rows"] > 1000 and rep["split"] and rep["research_only"]
        assert set(rep["calibration"]) == {"atp", "wta"} and rep["calibration"]["atp"]["reliability"]
        assert rep["real"]["waiting"] and rep["real"]["lines"] == 0
        with open(out) as f:
            saved = json.load(f)
        assert saved["split"] == rep["split"]
        _tennis_hist(hist_p, 60, None)
        assert s1.study(out, hist_p, os.path.join(tmp, "none.json"), os.path.join(tmp, "none.csv"),
                        verbose=False)["split"] == rep["split"], "the split never moves"
    finally:
        shutil.rmtree(tmp)


def _bov_set1_payload(start_ms=1790000000000):
    def mk(desc, outs, period=None, status="O"):
        return {"description": desc, "status": status, "period": period or {"description": "Match", "main": True},
                "outcomes": [{"description": n, "price": {"american": a, **({"handicap": h} if h is not None else {})}}
                             for n, a, h in outs]}
    s1p = {"description": "1st Set", "abbreviation": "1S", "main": False, "live": False}
    return [
        {"path": [{"description": "ATP Shanghai"}, {"description": "Tennis"}], "events": [
            {"id": "11", "live": False, "startTime": start_ms, "displayGroups": [
                {"description": "Game Lines", "markets": [
                    mk("Moneyline", [("Jannik Sinner", "-250", None), ("Holger Rune", "+200", None)]),
                    mk("Game Spread", [("Jannik Sinner", "-110", "-4.5"), ("Holger Rune", "-120", "4.5")])]},
                {"description": "Set Props", "markets": [
                    mk("1st Set Winner", [("Holger Rune", "+170", None), ("Jannik Sinner", "-210", None)], s1p),
                    mk("1st Set Game Spread", [("Jannik Sinner", "-105", "-1.5"), ("Holger Rune", "-125", "1.5")], s1p),
                    mk("1st Set Total Games", [("Over", "-110", "9.5"), ("Under", "-110", "9.5")], s1p),
                    mk("1st Set - Game 3 Winner", [("Jannik Sinner", "-300", None), ("Holger Rune", "+220", None)], s1p),
                    mk("Set Betting", [("Jannik Sinner 2-0", "+100", None), ("Jannik Sinner 2-1", "+300", None),
                                       ("Holger Rune 2-0", "+600", None), ("Holger Rune 2-1", "+500", None)])]}]},
            {"id": "12", "live": False, "startTime": start_ms, "displayGroups": [{"markets": [
                mk("Moneyline", [("Casper Ruud", "+120", None), ("Taylor Fritz", "-140", None)]),
                mk("Moneyline", [("Casper Ruud", "+110", None), ("Taylor Fritz", "-130", None)], s1p)]}]},
            {"id": "13", "live": False, "startTime": start_ms, "displayGroups": [{"markets": [
                mk("Moneyline", [("Tommy Paul", "+150", None), ("Ben Shelton", "-170", None)])]}]},
            {"id": "14", "live": True, "startTime": start_ms, "displayGroups": [{"markets": [
                mk("Moneyline", [("A Guy", "+150", None), ("B Guy", "-170", None)]),
                mk("Set 1 Winner", [("A Guy", "+150", None), ("B Guy", "-170", None)])]}]}]},
        {"path": [{"description": "WTA Wuhan"}], "events": [
            {"id": "21", "live": False, "startTime": start_ms, "displayGroups": [{"markets": [
                mk("Moneyline", [("Iga Swiatek", "-400", None), ("Coco Gauff", "+300", None)]),
                mk("Set 1 Winner", [("Iga Swiatek", "-320", None), ("Coco Gauff", "EVEN", None)]),
                mk("Set 1 Winner", [("Iga Swiatek", "-320", None), ("Coco Gauff", "+250", None)])]}]}]},
        {"path": [{"description": "ATP Doubles"}], "events": [
            {"id": "31", "live": False, "startTime": start_ms, "displayGroups": [{"markets": [
                mk("1st Set Winner", [("X/Y", "+100", None), ("Z/W", "-120", None)])]}]}]}]


def test_tennis_set1_parse():
    """Bovada's first-set markets (research only): '1st Set Winner', 'Set 1 Winner' or a moneyline in a '1st Set'
    period, the first-set game handicap and set betting are captured per match with the players in the moneyline's
    order; totals, game props, live events and doubles are not; the picks' match prices are unchanged; the last price
    before the start is kept; and the real-price hook waits for 300 matched lines."""
    import sports_tennis as stn
    import sports_tennis_set1 as s1
    assert stn.is_set1("1st Set Winner") and stn.is_set1("Set 1 Winner") and stn.is_set1("First Set - Moneyline")
    assert stn.is_set1("Moneyline 1st Set") and not stn.is_set1("Moneyline") and not stn.is_set1("Set Betting")
    assert not stn.is_set1("2nd Set Winner") and not stn.is_set1("Set 10 Winner")
    bov = _bov_set1_payload()
    rows = {r["event"]: r for r in stn.parse_bovada_set1(bov)}
    assert set(rows) == {"11", "12", "21"}, rows
    r = rows["11"]
    assert (r["a"], r["b"], r["tour"]) == ("Jannik Sinner", "Holger Rune", "atp") and (r["a_ml"], r["b_ml"]) == (-250, 200)
    assert (r["a_s1"], r["b_s1"]) == (-210, 170), "mapped by name, not by outcome order"
    assert (r["a_s1_hcp"], r["a_s1_sp"], r["b_s1_hcp"], r["b_s1_sp"]) == (-1.5, -105, 1.5, -125)
    assert r["set_betting"] == {"Jannik Sinner 2-0": 100, "Jannik Sinner 2-1": 300, "Holger Rune 2-0": 600, "Holger Rune 2-1": 500}
    assert (rows["12"]["a_s1"], rows["12"]["b_s1"], rows["12"]["a_ml"]) == (110, -130, 120), "a moneyline in a 1st Set period"
    assert rows["21"]["tour"] == "wta" and rows["21"]["b_s1"] == 250 and "set_betting" not in rows["21"]
    main = {x["a"]: x for x in stn.parse_bovada(bov)}
    assert main["Jannik Sinner"]["a_ml"] == -250 and main["Casper Ruud"]["a_ml"] == 120, "the picks' prices untouched"
    assert main["Jannik Sinner"]["a_hcp"] == -4.5 and "Tommy Paul" in main
    assert stn.parse_bovada_set1(None) == [] and stn.parse_bovada_set1([{"path": "junk"}]) == []
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "set1_lines.json")
        start = datetime.fromtimestamp(1790000000, timezone.utc)
        stn.save_set1_lines(stn.parse_bovada_set1(bov), start - timedelta(hours=5), path)
        later = _bov_set1_payload()
        later[0]["events"][0]["displayGroups"][1]["markets"][0]["outcomes"][0]["price"]["american"] = "+180"
        stn.save_set1_lines(stn.parse_bovada_set1(later), start - timedelta(minutes=10), path)
        stn.save_set1_lines(stn.parse_bovada_set1(_bov_set1_payload()), start + timedelta(minutes=5), path)  # started: ignored
        with open(path) as f:
            saved = json.load(f)
        day = start.strftime("%Y-%m-%d")
        assert set(saved) == {f"sinner|rune|{day}", f"ruud|fritz|{day}", f"swiatek|gauff|{day}"}
        assert saved[f"sinner|rune|{day}"]["b_s1"] == 180, "the last price before the start"
        # the real-price hook: matched to finished ESPN results (first set from sets1 / sets2), waits for 300
        st_iso = start.strftime("%Y-%m-%dT%H:%MZ")
        ms = [{"id": "atp:1", "tour": "atp", "start": st_iso, "p1_name": "Holger Rune", "p2_name": "Jannik Sinner",
               "status": "STATUS_FINAL", "sets1": "6 3 4", "sets2": "4 6 6", "bo": "3"},
              {"id": "wta:2", "tour": "wta", "start": st_iso, "p1_name": "Iga Swiatek", "p2_name": "Coco Gauff",
               "status": "STATUS_FINAL", "sets1": "3", "sets2": "2", "bo": "3"}]       # (retired inside set 1: void)
        full = {("atp", "Sinner J."): sorted(("2026-01-%02d" % (i + 1), 1, 0.6) for i in range(15)),
                ("atp", "Rune H."): sorted(("2026-01-%02d" % (i + 1), 0, 0.5) for i in range(15))}
        real = s1.real_study(saved, ms, full)
        assert real["lines"] == 3 and real["matched"] == 1 and real["waiting"] and "tests" not in real
        gap = real["bovada_set1_vs_markov_from_its_match_line"]
        assert gap["n"] == 1 and abs(gap["mean_gap"]) < 0.1
        keep = s1.REAL_MIN
        s1.REAL_MIN = 1
        try:
            real = s1.real_study(saved, ms, full)
            t = real["tests"]["atp|overperformance"]["thresholds"]["0.05"]["all"]
            assert t["n"] == 1 and t["hit"] == 0.0 and t["roi"] == -1.0, "backed Sinner (the overperformer); Rune won set 1"
        finally:
            s1.REAL_MIN = keep
    finally:
        shutil.rmtree(tmp)


def test_web_push():
    """🔔 After ntfy takes an alert, the engine hands ntfy's message id to the Worker's /push (and only the id)."""
    import urllib.request
    import sports_dashboard
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "ask_url.txt"), "w") as f:
        f.write("https://d503-ask.example.workers.dev/\n")
    sent = []

    class Resp:
        def __init__(self, body):
            self.body = body

        def read(self):
            return self.body

    def fake(req, timeout=None):
        sent.append((req.full_url, req.data, dict(req.header_items()), timeout))
        if "ntfy.sh" in req.full_url:
            return Resp(json.dumps({"id": f"nt{len(sent):010d}", "event": "message"}).encode())
        return Resp(b'{"ok":true}')

    real, data, notify = urllib.request.urlopen, sd.DATA, sports_live.NOTIFY[0]
    urllib.request.urlopen, sd.DATA, sports_live.NOTIFY[0] = fake, tmp, True
    try:
        t = sports_live.notify({"team": "Bears", "odds": 150, "score": "CHI 14 - GB 10", "clock": "Q3 4:12", "line": "value"})
        t.join(5)
        assert sent[0][0] == "https://ntfy.sh/d503-live-7b1123" and b"Bears ML +150" in sent[0][1]
        assert sent[1][0] == "https://d503-ask.example.workers.dev/push", sent
        assert json.loads(sent[1][1]) == {"ntfy_id": "nt0000000001"} and sent[1][3] == 5
        assert sent[1][2].get("Content-type") == "application/json"
        sports._push("INJURY ALERT: QB", "ruled out").join(5)                     # the injury alerts ring it too
        assert sent[2][0].startswith("https://ntfy.sh/") and json.loads(sent[3][1]) == {"ntfy_id": "nt0000000003"}
        # the Worker being down never stops anything (the error is just logged)
        def down(req, timeout=None):
            if "workers.dev" in req.full_url:
                raise OSError("timed out")
            return fake(req, timeout)
        urllib.request.urlopen = down
        sports_live.notify({"team": "Bears", "odds": 150}).join(5)
        assert any(e.startswith("web push:") for e in sd.ERRORS)
        # no Worker address / no id from ntfy: ntfy still went out, nothing else happens
        os.remove(os.path.join(tmp, "ask_url.txt"))
        assert sd.web_push(b'{"id":"abc123"}') is None and sd.web_push(b"{}") is None
        # the dashboard's service worker, written next to the page with the Worker's address
        with open(os.path.join(tmp, "ask_url.txt"), "w") as f:
            f.write("https://d503-ask.example.workers.dev")
        sports_dashboard.write_sw(os.path.join(tmp, "sw.js"))
        with open(os.path.join(tmp, "sw.js")) as f:
            sw = f.read()
        assert 'const API = "https://d503-ask.example.workers.dev";' in sw and "showNotification" in sw and "notificationclick" in sw
    finally:
        urllib.request.urlopen, sd.DATA, sports_live.NOTIFY[0] = real, data, notify
        shutil.rmtree(tmp)


def test_lean_day_card():
    """A leans-only day: a note up top in our voice, and a lean is never titled Lock/Dog of the Day."""
    import copy
    import sports_dashboard as dsh
    real = next(p for p in json.load(open(os.path.join(sd.DATA, "picks.json"))) if len(p.get("legs") or []) == 1)
    pk = copy.deepcopy(real)
    pk.update(kind="lock", lean=True, tier="lean")
    card = dsh._pick_card("lock", pk)
    assert "LEAN</span>" in card and "LOCK OF THE DAY" not in card, card[:300]
    pk["legs"][0]["p"] = 0.66
    assert "STRONG LEAN" in dsh._pick_card("lock", pk), "a 60%+ lean says STRONG LEAN"
    one = [{"kind": "lock", "status": "open"}]
    assert "one" in dsh._short_note("2026-09-29", one).lower(), "one play: says so"
    assert "3" in dsh._short_note("2026-09-29", one + [{"kind": "dog"}, {"kind": "two"}]), "the count's in it"
    import sports_lingo as sl
    notes = {sl.short_note(1, f"2026-10-{d:02d}") for d in range(1, 31)}
    assert len(notes) >= 25 and sum("pros pick their spots" in x for x in notes) <= 5, "never the same line every day"
    full = [{"kind": k} for k in dsh.FULL_BOARD]
    assert dsh._short_note("2026-09-29", full) == "" and dsh._short_note("2026-09-29", [{"kind": "solo"}]) == ""
    note = dsh._lean_note("2026-09-29")
    assert "leans" in note.lower() and "never in ours" not in note and note.count("drop leanday") == 1 and "real talk" not in note.lower()


def test_plus_money_lock_rule():
    """The label study (9/28): a LOCK is 56%+ to win, never plus money past +125 (over +125 is always VALUE; a +156 at
    40% labeled Lock of the Day was the bug)."""
    import sports
    assert not sports.lock_ok({"odds": 156, "p": 0.396}) and not sports.lock_ok({"odds": 130, "p": 0.7})
    assert sports.lock_ok({"odds": 125, "p": 0.57}) and sports.lock_ok({"odds": -140, "p": 0.6})
    assert not sports.lock_ok({"odds": 110, "p": 0.55}) and not sports.lock_ok({"odds": -105, "p": 0.53})


def _sample_history(days=24, seed=5):
    """Graded picks over `days` days: locks, dogs, spreads, totals, parlays, leans, a push - for the review tests."""
    rnd = random.Random(seed)
    teams = {"nfl": ["Ravens", "Cowboys", "Bills", "Jets", "Rams", "Broncos", "Chiefs", "Eagles", "Lions", "Packers"],
             "mlb": ["Cubs", "Mets", "Royals", "Twins", "Giants", "Padres", "Astros", "Orioles"],
             "nba": ["Lakers", "Celtics", "Knicks", "Heat", "Suns", "Bucks"]}
    picks, gid = [], 0
    for d in range(days):
        date = (datetime(2026, 9, 1) + timedelta(days=d)).strftime("%Y-%m-%d")
        def leg(market="ml", result=None):
            nonlocal gid
            gid += 1
            lg = rnd.choice(list(teams))
            a, b = rnd.sample(teams[lg], 2)
            x, y = rnd.randint(0, 40), rnd.randint(0, 40)
            res = result or rnd.choice(["won", "lost"])
            won = (x > y) == (res == "won")
            l = {"game_id": f"{lg}:{gid}", "league": lg, "side": "away", "team": a, "opp": b, "market": market,
                 "odds": rnd.choice([-180, -140, -110, 120, 165, 210]), "line": None, "result": res, "p": rnd.random(),
                 "score": f"{a} {max(x, y) if won else min(x, y)} @ {b} {min(x, y) if won else max(x, y)}"}
            if market == "spread":
                l["line"] = rnd.choice([-3.5, 2.5, 6.5])
            if market == "total":
                l.update(side=rnd.choice(["over", "under"]), team="Over", opp=f"{a} @ {b}", line=44.5, score="")
            return l
        for kind, legs, lean in (("lock", [leg()], False), ("dog", [leg("spread")], False),
                                 ("two", [leg(), leg("total")], False), ("lock", [leg()], True)):
            st = "lost" if any(l["result"] == "lost" for l in legs) else "won"
            picks.append({"date": date, "kind": kind, "status": st, "lean": lean, "legs": legs, "american": 264})
    picks[1]["legs"][0].update(line=3.0, result="push")
    picks[1]["status"] = "push"
    return picks


def test_past_results_vocab():
    """📜 PAST RESULTS: every review worded differently - no 4-word run twice in the whole section (names and
    numbers aside), nothing banned, no hype on a lean, never longer than the old line, and stable: the same page
    every run, and a new day never rewords the old ones."""
    import html as html_
    import sports_breakdown as sb
    import sports_dashboard as dash
    import sports_lingo as sl
    keep, tmp = sd.DATA, tempfile.mkdtemp()
    sd.DATA = tmp                                           # (no live log / tennis on disk: just these picks)
    try:
        picks = _sample_history()
        page = dash._history(picks)
        revs = [html_.unescape(x) for x in re.findall(r"<div class=\"hrv\">📝 (.*?)</div>", page)]
        assert len(revs) >= 80 and all(revs), len(revs)
        names = sorted(list({f"{t}{n}" for p in picks for l in p["legs"] if l["market"] != "total"
                        for n in (l["team"], l["opp"]) for t in ("", "the ")})
                       + ["Over 44.5", "Under 44.5"], key=len, reverse=True)   # (as the reviews name them)
        seen = {}
        for r in revs:
            assert not re.search(r"real talk|chalk", r, re.I), r
            for g in sb.grams(r, names):
                if any(w not in ("_", "#") for w in g[2:].split()):
                    assert g not in seen, f"{g!r} twice: {seen.get(g)!r} / {r!r}"
                    seen[g] = r
        assert any(re.search(r"push|wash|money back|stake back", r.lower()) for r in revs), "a push says so"
        assert dash._history(picks) == page, "the same words every run"
        more = picks + [dict(p, date="2026-10-30") for p in _sample_history(1, seed=9)]
        old = re.findall(r"<div class=\"hrv\">📝 (.*?)</div>", dash._history(more))
        assert set(re.findall(r"<div class=\"hrv\">📝 (.*?)</div>", page)) <= set(old), "a new day never rewords the old reviews"
        lean_rows = page[page.index("🟡 Leans"):]
        assert not sl.LEAN_BAN.search(html_.unescape(lean_rows)), "no hype on a lean"
    finally:
        sd.DATA = keep
        shutil.rmtree(tmp)
    # never longer than the old line (names / numbers count as one character), never more sentences
    caps, used = sl.caps(), set()
    for (k, r), (c, n, _) in sl.REVIEWS.items():
        for i in range(8):
            x = sl.review(k, "push" if k == "push" else r, f"cap{i}", used, t="①", o="②", x="③" if r != "" else "")
            assert x and len(x) <= c and len(re.findall(r"[.!?](?=\s|$)", x)) <= n, (k, r, x)
    for k, ((c, n), low, t) in sl.LINES.items():
        kw = {m: "①" for m in set(re.findall(r"\{(\w+)\}", " ".join(t))) if m.lower() not in __import__("sports_vocab").SLOTS}
        for x in sl.roll(t, "cap", (c, n), 60, low, **kw):
            assert len(x) <= c and len(re.findall(r"[.!?](?=\s|$)", x)) <= n, (k, x)
    for x in sl.good("①", "②", "cap", n=60):
        assert len(x) <= caps["good"][0], x
    # a big supply: hundreds to thousands of ways for every review
    sup = sl.supply()
    assert all(v >= 300 for k, v in sup.items() if k.startswith("review") and "push" not in k), sup
    assert sl.note_supply()["leans"] > 100000 and sup["good"] > 5000


def test_live_words_stay_put():
    """A live play's wording is pinned while it's up (live.json is rewritten every second): same play, same words -
    only the facts move; a second play on the board never shares a 4-word run with the first."""
    L = sports_live
    rs = [("better", {}), ("pre", {})]
    w1 = L._team_words("nba", "the Lakers", "the Celtics", True, "7", rs, "nba:1:home")
    w1b = L._team_words("nba", "the Lakers", "the Celtics", True, "9", rs, "nba:1:home")
    assert w1(0)[0].replace("7", "9") == w1b(0)[0], "the score moves, the words don't"
    assert w1(0) == L._team_words("nba", "the Lakers", "the Celtics", True, "7", rs, "nba:1:home")(0), "stable"
    a = {"id": "nba:1:home", "team": "Lakers", "opp": "Celtics", "line": w1(0)[0], "breakdown": w1(0)[1], "_words": w1}
    w2 = L._team_words("nba", "the Knicks", "the Heat", True, "7", rs, "nba:2:away")
    b = {"id": "nba:2:away", "team": "Knicks", "opp": "Heat", "line": w2(0)[0], "breakdown": w2(0)[1], "_words": w2}
    log = {"plays": {}}
    first = L.settle_words([dict(a), dict(b)], {}, log)
    assert not any("_words" in p for p in first) and L._runs(first[0]).isdisjoint(L._runs(first[1]))
    again = L.settle_words([dict(a), dict(b)], {p["id"]: p for p in first}, log)
    assert [(p["line"], p["breakdown"]) for p in again] == [(p["line"], p["breakdown"]) for p in first], "no flicker"
    txt = " ".join(x for p in first for x in [p["line"]] + p["breakdown"]).lower()
    assert "real talk" not in txt and "chalk" not in txt


def test_breakdown_variety():
    """The owner: write-ups can't read like yesterday's. A whole board rolled for a day: no 4-word run on two cards, none
    from yesterday's board, no line the same as yesterday's, every roll no longer than today's version of that line,
    never "real talk" / "chalk", no leftover template bits - and every card still ends on its bottom line."""
    import types
    import sports_breakdown as sb
    import sports_vocab as vo
    teams = ["Hawks", "Bulls", "Suns", "Nets", "Kings", "Bucks", "Heat", "Magic", "Spurs", "Rockets", "Lakers", "Knicks"]
    rnd, games = random.Random(7), {}
    t0 = datetime(2026, 1, 1, 3, 0)
    for d in range(40):                                   # a season so far: records, streaks, rest, head to head
        order = teams[:]
        rnd.shuffle(order)
        for i in range(0, len(order), 2):
            if rnd.random() < 0.5:
                continue
            gid = f"nba:h{d}_{i}"
            hs, as_ = rnd.randint(90, 125), rnd.randint(90, 125)
            games[gid] = {"id": gid, "league": "nba", "start": (t0 + timedelta(days=d)).strftime("%Y-%m-%dT%H:%MZ"),
                          "status": "final", "stype": "2", "home": order[i], "away": order[i + 1], "home_name": order[i],
                          "away_name": order[i + 1], "home_score": str(hs), "away_score": str(as_ + (hs == as_)), "neutral": "0"}
    elo = {"nba": types.SimpleNamespace(r={t: 1500 + rnd.randint(-120, 120) for t in teams}, hfa=50)}
    reasons = ["revenge game", "the stronger team", "better rested", "hotter recent form", "letdown spot for the opponent"]

    def board(day):
        legs = []
        order = teams[:]
        random.Random(day).shuffle(order)
        for i in range(0, len(order), 2):
            gid = f"nba:u{day}_{i}"
            ml_h, ml_a = random.Random(gid).choice([(-150, 130), (120, -140), (-110, -110)])
            games[gid] = {"id": gid, "league": "nba", "start": (t0 + timedelta(days=40 + day)).strftime("%Y-%m-%dT%H:%MZ"),
                          "status": "pre", "stype": "2", "home": order[i], "away": order[i + 1], "home_name": order[i],
                          "away_name": order[i + 1], "home_score": "", "away_score": "", "neutral": "0",
                          "ml_home": str(ml_h), "ml_away": str(ml_a), "ml_home_open": str(ml_h + 15), "ml_away_open": str(ml_a)}
            for side in ("home", "away"):                   # both sides (two cards on the same game read differently too)
                odds = ml_h if side == "home" else ml_a
                dec = 1 + (odds / 100 if odds > 0 else 100 / -odds)
                legs.append({"game_id": gid, "league": "nba", "side": side, "market": "ml", "line": None, "odds": odds,
                             "dec": dec, "p": min(0.8, 1 / dec + random.Random(gid + side).choice([0.01, 0.12])),
                             "team": games[gid][side + "_name"], "opp": games[gid][("away" if side == "home" else "home") + "_name"],
                             "reasons": random.Random(gid + side).sample(reasons, 3)})
        return legs

    said, orig = [], sb.Voice.say
    def spy(self, key, options, must=False, names=()):     # what Voice itself compares: the line's runs, facts blanked
        out = orig(self, key, options, must, names)
        said.append((self.seed, out, sb.grams(out, tuple(names) + self.names) if out else set()))
        return out
    sb.Voice.say = spy
    try:
        yesterday, cards = [], {}
        for day in (0, 1):
            used = sb.recent_grams(yesterday)
            said.clear()
            texts = []
            for leg in board(day):
                bd = sb.breakdown(leg, games, elo, None, used)
                assert bd and bd[-1].startswith("✅ Bottom line:"), bd
                for x in bd:
                    assert "real talk" not in x.lower() and "chalk" not in x.lower(), x
                    assert not re.search(r"[\[\]{}\ue000-\ue1ff]", x), x
                texts += [(x, (leg["team"], leg["opp"])) for x in bd]
            per = {}
            for seed, out, g in said:
                per.setdefault(seed, set()).update(g)
            seeds = list(per)
            for i, a in enumerate(seeds):
                for b in seeds[i + 1:]:
                    assert not per[a] & per[b], ("a 4-word run on two cards", a, b, per[a] & per[b])
            if day:
                old = sb.recent_grams(yesterday)
                for seed, g in per.items():
                    assert not g & old, ("a 4-word run from yesterday", seed, g & old)
                assert not {x for x, _ in texts} & {x for x, _ in yesterday}, "a line word for word from yesterday"
            cards[day] = texts
            yesterday = texts
    finally:
        sb.Voice.say = orig
    # every roll stays within today's size for its line, and the big lines have thousands of ways to go
    for k, ts in sb.T.items():
        assert k in sb._CAP, k
        facts = {p: "Xx" for p in re.findall(r"\{(\w+)\}", " ".join(ts)) if p.lower() not in vo.SLOTS and p not in ("field", "a_n", "a_rec")}
        rolls = sb._roll(k, "t", {"field": "court", "a_n": "a", "a_rec": "a"}, **facts)
        assert rolls and all(sb._size(r.replace("Xx", "\ue000\ue100\ue001"))[0] <= sb._CAP[k][0] for r in rolls), k
    assert vo.supply(sb.T["bottom"]) > 5000 and vo.supply(sb.T["bottom_s"]) > 2000 and len(sb.T["bottom"]) >= 10
    # every call site rolls clean with exactly the facts it passes (no "{x}" left, no pool shadowing a fact)
    import ast
    calls, words = {}, {"field": "court", "a_n": "a", "a_rec": "a"}
    for node in ast.walk(ast.parse(open(sb.__file__).read())):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_say":
            kw = {k.arg for k in node.keywords if k.arg} - {"must", "words", "tkey", "extra", "names"}
            if not kw:                                    # **names in context_lines
                kw = {"the_us", "the_them", "The_us", "The_them"}
            kw |= {"the_us", "the_them", "The_us", "The_them"} if any(k.arg is None for k in node.keywords) else set()
            tk = next((k.value.value for k in node.keywords if k.arg == "tkey" and isinstance(k.value, ast.Constant)), None)
            key = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else None
            for k in ([tk or key] if (tk or key) else []):
                calls.setdefault(k, set()).update(kw)
    dyn = {"better": {"us", "them", "us_s"}, "better_s": {"us", "them", "us_s"}, "worse": {"us", "them", "us_s"},
           "even": {"us", "them", "us_s"}, **{f"{r}_{m}": {"name", "txt"} for r in ("QB", "SP", "G") for m in ("hot", "cold")},
           **{k: {"The_them", "the_them", "the_them_s", "hl"} for k in sb.T if k.startswith("drama_")},
           **{k: {"who", "Who", "who_s", "Who_s"} for k in sb.T if k.startswith("talk_")},
           **{f"splits_{x}": calls.get("splits", set()) for x in ("fade", "ride", "even")},
           "lean": {"team", "tms"}}
    for k in sb.T:
        facts = calls.get(k) or dyn.get(k)
        assert facts, ("no call site says this line", k)
        assert not set(sb._P) & facts, ("a word pool shadows a fact", k, set(sb._P) & facts)
        for r in sb._roll(k, "guard", words, **{f: "Xx" for f in facts}):
            assert not re.search(r"[\[\]{}]", r), (k, r)
    lean = sb.lean_tone(["✅ Bottom line: trust the algorithm.", "🔥 Hawks are rolling. Let's eat."], {"team": "Hawks"}, "x")
    assert lean[-1].startswith("🟡 Bottom line:") and not any(sb.HYPE.search(x) for x in lean), lean


def test_no_dog_note():
    """🐺 A full board with no dog worth it says so where the dog would go - one note, never a second (short-board) one,
    in our voice, never a sentence from yesterday's note."""
    import sports_dashboard as dsh, sports_lingo as L
    full_no_dog = [{"kind": k} for k in ("lock", "two", "three", "four")]
    assert dsh._dog_note("2026-10-01", full_no_dog) and not dsh._short_note("2026-10-01", full_no_dog)
    assert not dsh._dog_note("2026-10-01", full_no_dog + [{"kind": "dog"}]), "a dog on the board = no note"
    short = [{"kind": "lock"}, {"kind": "two"}]
    assert not dsh._dog_note("2026-10-01", short) and dsh._short_note("2026-10-01", short), "shorter board: its top note only"
    for d in range(1, 28):
        a, b = L.dog_note(f"2026-10-{d:02d}"), L.dog_note(f"2026-10-{d + 1:02d}")
        assert not set(a.split(". ")) & set(b.split(". ")), (a, b)
        assert "real talk" not in a.lower() and "chalk" not in a.lower()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
