"""Offline tests for the sports engine (no network): ESPN parsing, model tuning, the board rules,
grading. Run: python sports_test.py"""
import csv
import gzip
import io
import json
import math
import os
import sys
import random
import re
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone

import sports

import sports_comeback as sc
import sports_data as sd
_REAL_FETCH_INJURIES = sd.fetch_injuries        # (older tests swap sd.fetch_injuries for a stub and never put it back)
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
    import sports_absences as A
    keep_box = dict(A._TEAM)
    A._TEAM["nfl"] = {}          # (10/3: only players who play count - these made-up names have no box scores, so the
    try:                         #  count falls back to the old rule, like a team with no box scores does)
        cs = [c for c in sports.candidates(games, model, now, now.astimezone(sports.PT).date(), inj) if c["game_id"] == "nfl:x"]
    finally:
        A._TEAM.clear(); A._TEAM.update(keep_box)
    sides = {c["team"] for c in cs}
    assert "Giants" in sides and all(c.get("hurt") for c in cs if c["team"] == "Titans"), \
        "never put money on the more banged-up team (10/2: it can still be a lean, its injuries named)"


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
            "dec": dec, "p": p, "p_market": 1 / dec, "edge": p * dec - 1, "edge_own": p * dec - 1}   # (own read = p)


def test_board_rules():
    """THE LABEL STUDY's rules (9/28): picked by how likely it WINS - 53%+ = a play (STRONG LEAN), 56%+ = LOCK, the
    likeliest lock = Lock of the Day; an underdog only as VALUE with a proven angle; never fighting Vegas; -150 cap."""
    pr = lambda c: {**c, "reasons": c["reasons"] + ["proven spot: home dog after a loss"]}
    c = [_cand("a", -300, 0.80), _cand("b", -140, 0.62), _cand("f", -115, 0.57), _cand("k", -120, 0.55),
         _cand("n", -110, 0.52), pr(_cand("d", 150, 0.43)), _cand("e", 180, 0.40), _cand("i", -110, 0.58, "spread", -3.5, "nfl")]
    b = sports.make_board(c)
    assert b["lock"]["legs"][0]["game_id"] == "b", "the Lock of the Day = the likeliest winner worth its price, -150 cap (never the -300)"
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
    assert fb["lock"] is None, "nothing real = no Lock"
    assert fb["two"] and {l["game_id"] for l in fb["two"]["legs"]} == {"q", "r"}   # 9/30, the owner: a 2-, 3-, 4-leg
    assert fb["three"] is None                                   # every day - but only from real games on the slate
    assert fb["dog"] is None                                     # 10/1, the owner: no real value = no Dog of the Day
    #   (a forced dog takes our ROI down - it's a unit play like the Lock, or it's not posted)
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
    assert sports.in_record({"lean": True, "date": "2026-09-30"}) and sports.in_record({"date": "2026-09-30"})   # leans count
    assert not sports.in_record({"lean": True, "date": "2026-09-27"})       # (the owner, 10/1) - from 9/29 on


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
    assert all(p["status"] == "open" for p in picks) and len(picks) >= 1   # (10/1: no filler parlays - this slate has
    #                                                    nothing real, so it's the Lock (a lean) and the leans)
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
    kept = [p for p in picks if p["kind"] != "play"]                          # say a unit play never went up...
    started = now + timedelta(hours=10, minutes=1)                            # ...once the games start, it can't
    assert sports.post_board(games, model, kept, started, day) == [] and all(p["kind"] != "play" for p in kept)


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
        noon = datetime.now(timezone.utc).astimezone(sports.PT).replace(hour=12, minute=0, second=0, microsecond=0)
        now = noon.astimezone(timezone.utc)                 # (pinned to noon PT: after 11pm the games would be
        today = noon.replace(hour=19).astimezone(timezone.utc)   # tomorrow's, and picks only post on game day)

        class _Noon(datetime):
            @classmethod
            def now(cls, tz=None):
                return now if tz else now.replace(tzinfo=None)
        keep_dt = sports.datetime
        sports.datetime = _Noon
        for i in range(6):
            gid = f"nhl:up{i}"
            games[gid] = {**games["nhl:1"], "id": gid, "status": "pre", "home": str(2 * i), "away": str(2 * i + 1),
                          "home_score": "", "away_score": "", "start": today.strftime("%Y-%m-%dT%H:%MZ"),
                          "ml_home": str([-140, 120, -110, 160, 250, -125][i]), "ml_away": str([120, -140, -110, -190, -320, 105][i])}
        sd.save_games(games)
        sd.fetch_injuries = lambda lg: {}
        try:
            picks = sports.run(fetch=False)
        finally:
            sports.datetime = keep_dt
        kinds = {p["kind"] for p in picks}
        assert kinds, "the fake slate has at least one real play"
        bad = [(p["kind"], p.get("lean"), l["team"], l["odds"], round(l["p"], 3)) for p in picks for l in p["legs"]
               if not (sports.good(l) or l.get("by_analysis") or p.get("lean"))]
        assert not bad, bad
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
    assert sports_live.two_books((-145, 110), (220, -295)) == (None, None, False)       # books apart: no price (10/1)
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
    # the slate: only picks we expect to win (55%+) that never fight the line, likeliest first - never filler to reach 8
    cands = []
    for i in range(12):
        p = 0.50 + 0.02 * i
        fair = -round(100 * p / (1 - p)) if p > 0.5 else 100
        odds = fair + (10 if i % 2 == 0 else -80)                 # every other one: the book is well above us (fighting)
        c = {"id": f"m{i}:1", "match": f"m{i}", "p": p, "odds": odds, "dec": sd.decimal(odds)}
        c["edge"] = p * c["dec"] - 1
        cands.append(c)
    picks, parlays = st.pick_slate(cands)
    parlay = parlays["atp"]
    assert picks and all(c["p"] >= st.MIN_P and not st.fighting(c) for c in picks), "likely to win, never fighting the line"
    assert [c["p"] for c in picks] == sorted((c["p"] for c in picks), reverse=True) and len(picks) < 6, "no filler"
    assert len(parlay) == 3 and parlay[0]["p"] >= parlay[-1]["p"] and all(c in picks for c in parlay)
    assert parlays["wta"] == [], "no women's picks = no women's parlay"
    mixed = [dict(c, id=f"w{i}", match=f"w{i}", tour="wta", p=0.60, odds=-150, dec=sd.decimal(-150), edge=0.6 * sd.decimal(-150) - 1)
             for i, c in enumerate(cands[:4])]
    mixed += [dict(c, id=f"m{i}", match=f"m{i}", tour="atp", p=0.70, odds=-233, dec=sd.decimal(-233), edge=0.7 * sd.decimal(-233) - 1)
              for i, c in enumerate(cands[:8])]
    pk, _ = st.pick_slate(mixed)
    assert sum(c["tour"] == "wta" for c in pk) == 4 and sum(c["tour"] == "atp" for c in pk) == 4, \
        "each tour on its own: up to 4 men's, the 4 real women's picks - never filler from the other tour"
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
    sp_ok = {**big, "id": "b:1:sp", "market": "spread", "hcp": -5.5, "odds": -140, "dec": sd.decimal(-140), "p": 0.60}
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
    assert by["wta:up:1"]["own"] == 0.5 and by["atp:up:1"]["own"] != 0.5, "each tour priced with its own weights"
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
    """Up to 4 men's + 4 women's picks (the owner, 9/29), never a mixed parlay, a tour's parlay only with 3 picks; old slates (one
    mixed parlay) and new slates (one per tour) both grade; post() never reposts a match from any slate."""
    import sports_tennis as st

    def c(mid, tour, p, odds=None):
        odds = odds if odds is not None else -round(100 * p / (1 - p))   # priced about where the engine has it
        d = sd.decimal(odds)
        return {"id": f"{mid}:1", "match": mid, "side": 1, "tour": tour, "p": p, "odds": odds, "dec": d, "edge": p * d - 1,
                "player": f"P {mid}", "opp": "X", "start": "2026-10-01T10:00Z", "tourney": "T", "market": "ml", "hcp": None,
                "ml": odds, "round": "R1", "surface": "hard", "bo": 3}
    many = [c(f"atp:{i}", "atp", 0.60 + 0.01 * i) for i in range(10)] + [c(f"wta:{i}", "wta", 0.58 + 0.01 * i) for i in range(10)]
    picks, pars = st.pick_slate(many)
    assert sum(x["tour"] == "atp" for x in picks) == 4 and sum(x["tour"] == "wta" for x in picks) == 4
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
        assert sum(l["tour"] == "atp" for l in slate["picks"]) == 4 and sum(l["tour"] == "wta" for l in slate["picks"]) == 4
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


def test_tennis_anchored_rules():
    """THE TENNIS LABEL STUDY's rules (tools/tennis_tier_study.py): the posted win % is ANCHORED to the book's no-vig
    price (p = market + trust * (engine - market), the trust learned per tour, clamped to 0..1, 0 when missing);
    a pick is chosen by how likely it WINS; never a side our own read has 3+ points under the book (fighting the
    line); no underdog without a PROVEN angle; spreads are anchored to the spread's own price; the breakdown prints
    the anchored %."""
    import sports_tennis as st
    assert abs(st.fair(-150, 130) + st.fair(130, -150) - 1) < 1e-9 and 0.55 < st.fair(-150, 130) < 0.6
    assert st.anchor(0.55, 0.73, 0.0) == 0.55 and abs(st.anchor(0.55, 0.73, 0.5) - 0.64) < 1e-9
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tier.json")
        with open(path, "w") as f:
            json.dump({"trust": {"atp": 0.2, "wta": 7}}, f)
        assert st.trust("atp", path) == 0.2 and st.trust("wta", path) == 1.0, "clamped to 0..1"
        assert st.trust("atp", os.path.join(d, "missing.json")) == st.TRUST == 0.0, "no study = the book's number"
    # candidates: the engine says ~73%, the book says a coin flip -> the posted win % is the book's (trust 0)

    class RT:
        def features(self, m, when=None):
            return {"elo": 1.0, "fatigue": 0.0, "form": 0.0, "h2h": 0.0, "known": 50, "surface_gap": 0.0, "home": 0}
    now = datetime(2026, 10, 1, 1, tzinfo=timezone.utc)
    up = (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%MZ")
    ms = {"atp:1": {"id": "atp:1", "tour": "atp", "start": up, "status": "STATUS_SCHEDULED", "winner": 0, "p1": "1",
                    "p2": "2", "p1_name": "Ace One", "p2_name": "Bee Two", "tourney": "T", "round": "R1", "surface": "hard",
                    "bo": 3, "sets1": "", "sets2": ""}}
    lines = [{"a": "Ace One", "b": "Bee Two", "a_ml": -110, "b_ml": -110, "start": up, "tour": "atp",
              "a_hcp": -1.5, "a_sp": -110, "b_hcp": 1.5, "b_sp": -110}]
    keep = dict(st._TRUST)
    st._TRUST.clear()
    st._TRUST[st.TIER] = {"atp": 0.0}
    try:
        cs = {c["id"]: c for c in st.candidates(ms, RT(), [0.0, 1.0, 0, 0, 0, 0, 0], lines, now, now + timedelta(hours=24),
                                                gm={"atp": {"3": [4.0, 5.0]}})}
        c1, c2, sp = cs["atp:1:1"], cs["atp:1:2"], cs["atp:1:1:sp"]
        assert c1["own"] > 0.7 and abs(c1["p"] - 0.5) < 1e-9 and abs(c1["mkt"] - 0.5) < 1e-9, c1
        assert abs(c1["p"] + c2["p"] - 1) < 1e-9 and c1["win_p"] == c1["p"]
        assert sp["own"] > 0.6 and abs(sp["p"] - 0.5) < 1e-9, "the spread's win % is anchored to the spread's price"
        assert st.pick_slate(list(cs.values()))[0] == [], "the engine loving a coin flip is never a pick"
        st._TRUST[st.TIER] = {"atp": 0.5}
        c1 = {c["id"]: c for c in st.candidates(ms, RT(), [0.0, 1.0, 0, 0, 0, 0, 0], lines, now,
                                                 now + timedelta(hours=24))}["atp:1:1"]
        assert abs(c1["p"] - (0.5 + 0.5 * (c1["own"] - 0.5))) < 1e-9, "the learned trust leans toward our number"
    finally:
        st._TRUST.clear()
        st._TRUST.update(keep)

    def c(mid, p, odds, own=None, mkt=None, **kw):
        d = sd.decimal(odds)
        return {"id": f"{mid}:1", "match": mid, "side": 1, "tour": "atp", "p": p, "odds": odds, "dec": d, "edge": p * d - 1,
                "own": p if own is None else own, "mkt": p if mkt is None else mkt, "market": "ml", **kw}
    ok = c("a", 0.62, -175, own=0.60)                          # the book 62%, us 60%: agrees enough
    fight = c("b", 0.66, -210, own=0.60)                       # the book 66%, us 60%: fighting the line
    steep = c("x", 0.80, -400)                                  # shorter than -300
    dog = c("d", 0.45, 130, own=0.60)                           # the engine loves a dog: no proven angle, no pick
    dog_ok = c("e", 0.47, 130, angle=True)                      # a proven angle + real value: allowed
    thin = c("f", 0.54, -125)                                   # under 55%
    picks, _ = st.pick_slate([ok, fight, steep, dog, dog_ok, thin])
    got = {x["match"] for x in picks}
    assert st.fighting(fight) and not st.fighting(ok)
    assert got == {"a", "e"}, got
    # the bottom line: our one win % said plain (never book-vs-us, the owner 9/29) and no bragging about a gap
    cb = {**ok, "player": "Ace One", "opp": "Bee Two", "surface": "hard", "bo": 3, "f": {"surface_gap": 0, "fatigue": 0,
                                                                                         "form": 0, "h2h": 0}}
    bd = st.breakdown(cb, None, set())
    assert any(x.startswith("✅") and "One ML" in x and x.count("%") == 1 and "62" in x for x in bd), bd
    assert not any(st.BRAG.search(x) for x in bd), bd


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


def test_live_tennis_super_value_only():
    """10/1, the owner: tennis live was popping up all night and losing (3-6) - "the engine has to see a super value".
    A NEW tennis live play needs a big pre-match favorite on the BOOKS (65%+) gone plus money, and a 10%+ edge."""
    import sports_tennis as stn
    import sports_tennis_live as stl
    L = sports_live
    L._TUNED.clear()
    m = _tn_live_row()
    pre = {"mkt_p1": 0.78, "model_p1": 0.8}
    p1 = stl.p1_live(m, 0.78)[0]
    def line_at(edge):
        ml = _ml_for(p1, edge)
        return {"a": "Holger Rune", "b": "Jannik Sinner", "a_ml": -ml - 40, "b_ml": ml, "suspended": False}
    ok = line_at(0.12)
    _, flip = stn.match_line(m, [ok])
    assert L.evaluate_tennis(m, ok, flip, pre, None)                             # a -350 favorite, now plus, 12%: a play
    assert L.evaluate_tennis(m, line_at(0.07), flip, pre, None) == []            # 7%: not super value any more
    mild = {"mkt_p1": 0.62, "model_p1": 0.8}                                     # only a -165 favorite pre-match
    assert L.evaluate_tennis(m, line_at(0.12), flip, mild, None) == []
    assert L.TENNIS_SUPER_PRE == 0.65 and L.TENNIS_MIN_EDGE == 0.10


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
    wpre = {"mkt_p1": 0.83, "model_p1": 0.85}                # (a bigger pregame favorite: down a set, the 9/30 SET_FIX
    wml = _ml_for(stl.p1_live(wm, 0.83)[0], 0.10)            # rates her lower - still over the live min win %)
    wline = {"a": "Emma Navarro", "b": "Jessica Pegula", "a_ml": -wml - 40, "b_ml": wml, "suspended": False}
    _, wflip = stn.match_line(wm, [wline])
    used = set()
    pl = L.evaluate_tennis(wm, wline, wflip, wpre, 1, (), used)
    assert len(pl) == 1 and pl[0]["team"] == "Jessica Pegula" and pl[0]["odds"] == wml and pl[0]["double_down"], pl
    x = pl[0]
    assert x["emoji"] == "🎾" and x["league"] == "tennis" and x["sport"] == "Women's Tennis" and x["id"] == "tennis:wta:77:1"
    assert "4-6" in x["score"] and x["clock"].startswith("Set 2") and {"ours", "strong", "state"} <= set(x["reasons"])
    assert "double down" in x["line"].lower() and "dropped the first set" in x["line"], x["line"]
    assert x["edge"] >= L.LIVE_MIN_EDGE and x["breakdown"]
    txt = " ".join([x["line"]] + x["breakdown"]).lower()
    assert "real talk" not in txt and "chalk" not in txt
    # a WTA play in the same check: she/her, and no wording repeated from the first play
    w = _tn_live_row("wta:5", "wta", n1="Coco Gauff", n2="Iga Swiatek")
    gml = _ml_for(stl.p1_live(w, 0.83)[0], 0.10)
    wl = {"a": "Coco Gauff", "b": "Iga Swiatek", "a_ml": gml, "b_ml": -gml - 40, "suspended": False}
    wp = L.evaluate_tennis(w, wl, False, wpre, 1, (), used)
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
        stl.load_prematch = lambda path=None: {"wta:77": wpre}
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
        L.TENNIS_BETS[0] = False                              # the switch off: no new live tennis bets at all
        try:
            assert L.tennis_plays(log, datetime.now(timezone.utc), (), set()) == []
        finally:
            L.TENNIS_BETS[0] = True
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
        assert not any("parlay" in k for k in R), "no parlay records (the owner, 9/28)"
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
        assert "parlays: men's" not in html and "parlays 0-" not in html, "no parlay records anywhere"
        live_list = html.split('id="livetoday">')[1].split("</div></div>")[0] if 'id="livetoday">' in html else ""
        assert "DOUBLE DOWN" not in live_list, "graded: out of tonight's list (the owner, 9/30)"
        assert "<b>📡 🎾 Men's Tennis</b>" in html and "Sinner vs Rune · 4-6, 2-2" in html, "...and in the results, under its sport"
        assert html.count("class=\"rc gr") >= 6
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
    r1 = ex.explore(games, path, batch=150, leagues=("nba",), verbose=False, dog_batch=0)
    first = set(ex.LAST_TESTED)
    assert planted in r1["new_suspects"] and noise in first and noise not in r1["suspects"], r1
    assert r1["tested"] == len(first) == 150 and r1["expected_by_luck"] < 1
    st = ex.load(path)
    s = st["suspects"][planted]
    assert s["disc"]["n"] >= 300 and s["disc"]["roi_old"] > 0 and s["disc"]["roi_new"] > 0 and s["disc"]["z"] >= 3.5
    assert s["cutoff"] == max(g["start"] for g in games.values())
    shutil.copy(path, path + ".kill")
    r2 = ex.explore(games, path, batch=150, leagues=("nba",), verbose=False, dog_batch=0)       # same games: only NEW angles
    assert r2["tested"] > 0 and not first & set(ex.LAST_TESTED) and r2["tested_total"] == r1["tested"] + r2["tested"]
    assert planted not in r2["new_suspects"] and not r2["new_proven"]               # no forward games yet
    later = {**games, **_explorer_games(160, 2, first=420)}                          # forward games, same edge
    r3 = ex.explore(later, path, batch=50, leagues=("nba",), verbose=False, dog_batch=0)
    assert planted in r3["new_proven"] and planted in r3["proven"], r3
    assert noise not in r3["proven"] and all("home" in k.split("|")[2].split("&") for k in r3["proven"]), r3["proven"]
    pv = ex.load(path)["proven"][planted]
    assert pv["fwd"]["n"] >= 100 and pv["fwd"]["roi"] > 0 and pv["fwd"]["z_edge"] >= 1 and pv["shift"] > 0
    # the edge vanishes going forward -> killed
    gone = {**games, **_explorer_games(160, 3, sunday_home=0.2, first=420)}
    r4 = ex.explore(gone, path + ".kill", batch=10, leagues=("nba",), verbose=False, dog_batch=0)
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
    assert dsh._short_note("2026-09-29", one) == "", "9/30, the owner: no 'short board' disclaimer - ever"
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
                       + ["the over", "the under", "The over", "The under"], key=len, reverse=True)   # (as the reviews name them)
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

    import sports_breakdown_v24 as v24                     # (the main board's voice since 9/29)
    said, orig, orig24 = [], sb.Voice.say, v24.Voice.say
    def spy_of(fn):
        def spy(self, key, options, must=False, names=()):  # what Voice itself compares: the line's runs, facts blanked
            out = fn(self, key, options, must, names)
            said.append((self.seed, out, sb.grams(out, tuple(names) + tuple(self.names)) if out else set()))
            return out
        return spy
    sb.Voice.say, v24.Voice.say = spy_of(orig), spy_of(orig24)
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
        sb.Voice.say, v24.Voice.say = orig, orig24
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
    assert dsh._dog_note("2026-10-01", full_no_dog) and not dsh._short_note("2026-10-01", full_no_dog)   # 10/1, the
    #   owner: no dog worth it = the board says so ("we pick our spots"), one note
    for d in range(1, 28):
        a, b = L.dog_note(f"2026-10-{d:02d}"), L.dog_note(f"2026-10-{d + 1:02d}")
        assert not set(a.split(". ")) & set(b.split(". ")), (a, b)
        assert "real talk" not in a.lower() and "chalk" not in a.lower()


def test_tennis_quick_grade():
    """A finished tennis match on our slate grades right away (the watcher calls this the moment it ends)."""
    import tempfile, sports_tennis as stq
    d, keep = tempfile.mkdtemp(), stq.PICKS
    stq.PICKS = os.path.join(d, "p.json")
    try:
        json.dump([{"date": "2026-09-29", "picks": [{"id": "atp:9:1", "match": "atp:9", "side": 1, "market": "ml", "result": None}],
                    "parlays": {}}], open(stq.PICKS, "w"))
        row = {"id": "atp:9", "status": "STATUS_FINAL", "winner": 2, "sets1": "4 3", "sets2": "6 6", "done": 2,
               "p1_name": "A B", "p2_name": "C D"}
        assert stq.quick_grade([row]) == 1 and json.load(open(stq.PICKS))[0]["picks"][0]["result"] == "lost"
    finally:
        stq.PICKS = keep


def test_tennis_overhype_cap():
    """Tighten up (the owner, 9/28): never a tennis side the engine likes 6+ points more than the book."""
    import sports_tennis as stt
    base = {"odds": -150, "dec": sd.decimal(-150), "market": "ml", "mkt": 0.58, "p": 0.58, "edge": 0.0}
    assert stt.good({**base, "own": 0.61}) and not stt.good({**base, "own": 0.66}) and not stt.good({**base, "own": 0.54})


def test_tennis_bovada_score():
    """Tennis scores as fast as the book posts them (the owner, 9/29): Bovada's live score oriented to OUR player,
    and it beats ESPN only when it's further along (ESPN's points stay only when both sit on the same game)."""
    import sports_live as slv
    m = {"p1_name": "Hubert Hurkacz", "p2_name": "Yexin Ma"}
    slv.BOV_HOME["77"] = "Ma Yexin"                       # home = p2 (name in the other order)
    slv.BOV_SCORE["77"] = (time.time(), {"clock": {"period": "Set 2"}, "previousPeriodsScore": [{"home": 6, "visitor": 4}],
                                        "currentPeriodScore": {"home": 1, "visitor": 3},
                                        "sportDetails": {"tennis": {"server": "visitor"}}})
    b = slv._bovada_score(m, {"event": 77}, 1)             # we're on Hurkacz (p1 = visitor)
    assert b["sets"] == [[4, 6], [3, 1]] and b["srv"] == 0 and b["done"] == 1 and b["live"] and b["n"][0] == "Hurkacz"
    b2 = slv._bovada_score(m, {"event": 77}, 2)            # on Ma: flipped
    assert b2["sets"] == [[6, 4], [1, 3]] and b2["srv"] == 1
    assert slv._bovada_score(m, {"event": 78}, 1) is None  # unknown event: ESPN keeps it
    espn = {"n": ["Hurkacz", "Ma"], "sets": [[4, 6], [2, 1]], "pts": ["30", "15"], "srv": 0, "done": 1, "delayed": False}
    f = slv.faster_score(espn, b)
    assert f["sets"] == [[4, 6], [3, 1]] and f["pts"] is None and f["delayed"] is False     # a game ahead: Bovada
    same = slv.faster_score(espn, {**b, "sets": [[4, 6], [2, 1]]})
    assert same["pts"] == ["30", "15"]                                                       # same game: ESPN's points
    assert slv.faster_score({**espn, "sets": [[4, 6], [4, 1]]}, b)["sets"] == [[4, 6], [4, 1]]   # ESPN ahead: ESPN
    assert slv.faster_score(espn, None) is espn


def test_live_price_against_the_score():
    """9/29 Garcia: -115 pregame (53%), up a break (the score says ~62%), and our line said +125 (43%) - the book's feed
    was minutes old (real price -150). A price that moved AGAINST the score is never value."""
    import sports_live as slv
    assert slv.against_the_score(0.53, 0.62, 0.43)            # score helped her, price says she got worse: stale
    assert not slv.against_the_score(0.53, 0.62, 0.58)        # price followed the score
    assert not slv.against_the_score(0.53, 0.54, 0.51)        # small wiggles are fine
    assert slv.against_the_score(0.60, 0.45, 0.70)            # the other way round too


def test_live_lines_newest_version_and_fresh_only():
    """The book's feeds sit in a cache (10 min an address): every check reads a new address, per match we keep the NEWEST version
    any address showed, and a price the book hasn't touched in LINE_MAX_AGE_S is no price (no play, no alert)."""
    import sports_live as slv
    now_ms = int(time.time() * 1000)
    grp = {"path": [{"description": "WTA"}, {"description": "Beijing"}]}

    def ev(mod, a, b, eid="9"):
        return {"id": eid, "live": True, "lastModified": mod, "startTime": now_ms - 3600000, "description": "X vs Y",
                "competitors": [{"name": "Andrea Lazaro Garcia", "home": True}, {"name": "Linda Fruhvirtova", "home": False}],
                "displayGroups": [{"markets": [{"description": "Moneyline", "status": "O",
                                                "period": {"description": "Live Match", "main": True, "live": True},
                                                "outcomes": [{"description": "Andrea Lazaro Garcia", "status": "O", "price": {"american": a}},
                                                             {"description": "Linda Fruhvirtova", "status": "O", "price": {"american": b}}]}]}]}
    old, new = [{**grp, "events": [ev(now_ms - 400000, "+125", "-155")]}], [{**grp, "events": [ev(now_ms - 5000, "-150", "+120")]}]
    keep = slv._safe_get, dict(slv.BOV_EV)
    try:
        slv.BOV_EV.clear()
        feeds, seen = iter([new, old, old]), []
        slv._safe_get = lambda u: seen.append(u) or next(feeds)
        for _ in range(3):
            got = slv.bovada_fresh("tennis-test")               # newest first, then two stale copies
        assert len(set(seen)) == 3 and all("eventsLimit=" in u for u in seen)   # a new address every check
        prices = [o["price"]["american"] for o in got[0]["events"][0]["displayGroups"][0]["markets"][0]["outcomes"]]
        assert len(got) == 1 and prices == ["-150", "+120"]    # the newest version wins, whatever order they came in
        import sports_tennis as stq
        ln = stq.parse_bovada(old, live=True)[0]
        assert ln["mod"] == now_ms - 400000 and now_ms - ln["mod"] > slv.LINE_MAX_AGE_S * 1000   # -> marked stale
    finally:
        slv._safe_get = keep[0]
        slv.BOV_EV.clear()
        slv.BOV_EV.update(keep[1])


def test_live_board_never_shows_a_frozen_price():
    """9/29: the watcher froze and the page kept a dead +125 up for minutes. Now: the page drops a play not re-checked in
    PLAY_FRESH_S, the watcher re-sends at least every HEARTBEAT_S, git can't hang, a watchdog restarts a stuck check,
    and the backstops cancel a watch that says "running" while its board is frozen."""
    import sports_dashboard as sdb, sports_live as slv
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import live_stuck
    assert sdb.PLAY_FRESH_S <= 60 and slv.HEARTBEAT_S * 2 < sdb.PLAY_FRESH_S and slv.WATCHDOG_S <= 120
    assert slv.PAUSE_HOLD_S <= 90
    src = open(sdb.__file__).read()
    assert "age>PLAY_FRESH_MS" in src
    r = slv._git("--version", timeout=5)
    assert r.returncode == 0
    from datetime import datetime, timezone, timedelta
    now = datetime(2026, 9, 29, 5, 0, tzinfo=timezone.utc)
    runs = [{"databaseId": 1, "status": "in_progress", "startedAt": "2026-09-29T04:20:00Z"},
            {"databaseId": 2, "status": "queued", "startedAt": None},
            {"databaseId": 3, "status": "in_progress", "startedAt": "2026-09-29T04:58:00Z"}]
    assert live_stuck.stuck_runs(age=400, runs=runs, now=now) == [1]      # frozen 6+ min, running 40 min: cancel
    assert live_stuck.stuck_runs(age=30, runs=runs, now=now) == []        # board fresh: leave it
    wf = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github/workflows/sports-live.yml")).read()
    assert '"$code" = 75' in wf                                             # the watchdog's exit restarts the watch
    assert "live_stuck.py" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools/backstop.sh")).read()


def test_live_bets_today_never_lost():
    """9/29: Garcia's live bet came down (she went to a big favorite) and was nowhere on the page - the watcher's saves to
    main failed and the list sat at the bottom. Now: the log rides with the live board and merges back (a graded copy
    wins), live.json carries today's bets, and the page lists them right under the live box."""
    a = {"plays": {"x:1": {"team": "A", "posted": "1", "result": None}, "x:2": {"team": "B", "result": "won"}}}
    b = {"plays": {"x:1": {"team": "A", "posted": "1", "result": "lost"}, "x:3": {"team": "C", "result": None}}}
    m = sd.merge_live_logs(a, b)["plays"]
    assert m["x:1"]["result"] == "lost" and m["x:2"]["result"] == "won" and "x:3" in m
    assert sd.merge_live_logs(b, {"plays": {"x:1": {"team": "A", "result": None}}})["plays"]["x:1"]["result"] == "lost"
    import sports_live as slv
    from datetime import datetime
    day = datetime.now(slv.PT).date().isoformat()
    t = slv.today_bets({"plays": {"tennis:wta:1:2": {"team": "Andrea Lazaro Garcia", "odds": 125, "date": day, "league": "tennis",
                                                     "tour": "wta", "posted": "x", "result": None},
                                  "nfl:9:home": {"team": "Bears", "odds": 120, "date": "2020-01-01", "league": "nfl"}}})
    assert [{k: v for k, v in x.items() if k != "story"} for x in t] == [
        {"pid": "tennis:wta:1:2", "team": "Andrea Lazaro Garcia", "odds": 125, "result": None, "start": "x", "icon": "🎾",
         "sport": "Women's Tennis", "dd": False}] and "story" in t[0]
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert src.index('<div id="livetoday">') < src.index("TODAY'S BOARD")      # right under the live box
    assert "today(d.today," in src and "live_log.json\\n" in open(slv.__file__).read().replace("\\t", "")


def test_scores_never_go_backwards():
    """9/29: ESPN's servers disagree - a tennis score flipped 1-3, 1-2, 1-3 inside seconds, so the page lagged and jumped
    back. Our worker asks ESPN for a fresh copy each second, and the page + the watcher never show an older score."""
    here = os.path.dirname(os.path.abspath(__file__))
    assert "_=${Math.floor(Date.now() / 1000)}" in open(os.path.join(here, "workers/ask/src/scores.js")).read()
    assert "window.D503B" in open(os.path.join(here, "sports_dashboard.py")).read()
    import sports_live as slv
    assert slv._games({"sets": [[6, 2], [1, 3]]}) == 12


def test_pending_live_bet_just_holds():
    """9/29: a pending live bet said '6-6 in set 1 at post' while the match had moved way on - a pending one never talks
    score or how it's going, just the hold. The score story waits for the grade."""
    import re, sports_dashboard as sdb
    used = set()
    for e in ({"league": "tennis", "team": "Elvina Kalieva", "odds": 125, "posted": "a", "tour": "wta",
               "tennis": {"games": [6, 6], "set_no": 1}, "result": None},
              {"league": "nfl", "team": "Bears", "odds": 120, "posted": "c", "score_at_post": "Eagles 0 @ Bears 7",
               "clock_at_post": "Q2", "side": "home", "result": None}):
        line = sdb._live_story(e, used)
        assert line and not re.search(r"\d", line) and "set" not in line.lower() and "quarter" not in line.lower(), line
    graded = sdb._live_story({"league": "nfl", "team": "Bears", "odds": 120, "posted": "d", "score_at_post": "Eagles 0 @ Bears 7",
                              "clock_at_post": "Q2", "side": "home", "result": "won"}, used)
    assert re.search(r"\d", graded)                        # graded: the full story


def test_live_bets_list_stays_till_the_board_drops_and_sport_chips_open_in_place():
    """The owner, 9/29: live bets (cashed, lost or pending) stay on the list till the 8 AM PT drop, then they're in
    PAST RESULTS; a pending one shows its live score; a sport chip opens its past bets right under it."""
    import sports_dashboard as sdb
    from datetime import datetime
    late = datetime(2026, 9, 28, 23, 30, tzinfo=sdb.PT)
    early = datetime(2026, 9, 29, 7, 30, tzinfo=sdb.PT)
    after = datetime(2026, 9, 29, 8, 5, tzinfo=sdb.PT)
    assert sdb.live_days(late) == {"2026-09-28"}
    assert sdb.live_days(early) == {"2026-09-28", "2026-09-29"}
    assert sdb.live_days(after) == {"2026-09-29"}
    src = open(sdb.__file__).read()
    assert 'data-gid="{E(gid)}" data-start="{E(start)}"' in src      # the live score under a pending live bet
    assert 'pn.className="spx"' in src and "scrollIntoView" not in src.split('closest("[data-hs].tap")')[1][:900]


def test_question_box_finds_the_player_and_retries():
    """9/29: 'Who wins next set in Han Shi tennis' - the AI hiccuped once and the fallback listed every tennis match
    ('tennis' matched them all, 'han' matched 'Shang'). Now: sport words never count as a name, a short word only matches
    a whole name, and the AI gets one retry before the fallback."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert '"tennis":1' in src and 'hit(w,(g.away+" "+g.home).toLowerCase())' in src
    assert "if(w.length<4) return ts.indexOf(w)>=0" in src and "if(again!==true){{ai(true);return}}" in src


def test_tennis_battle_review_only_on_a_real_sweep():
    """The owner, 9/29: 'Han fought hard but still got her cheeks clapped 2-0. Easy money, trust the algorithm' - only
    when the final really is a sweep and a set went the distance (7-6 / 7-5); never on a 3-setter or an easy 6-2 6-1."""
    import sports_dashboard as sdb
    import sports_lingo
    def review(score):
        sets = [tuple(x.strip().split("-", 1)) for x in score.split(",")]
        if not sdb._battle(sets):
            return ""
        return sports_lingo.say("rc:battle", "wta:1:1", set(), who="Kalieva", opp="Shi Han", his="her", sets=f"{len(sets)}-0")
    assert "2-0" in review("7-6(4), 6-4") and "Han" in review("7-6(4), 6-4")
    assert "2-0" not in review("6-2, 6-1") and "cheeks" not in review("6-2, 6-1")
    assert "2-0" not in review("7-6, 4-6, 6-3")


def test_watcher_asks_espn_for_fresh_copies():
    """9/29: the watcher's ESPN tennis read got old copies (Kalieva stuck at 5-4 after she'd won) - it asks for a fresh
    copy every second, like the worker."""
    import sports_live as slv
    assert slv.fresh_url("https://x/scoreboard").startswith("https://x/scoreboard?_=")
    assert "?dates=1&_=" in slv.fresh_url("https://x/scoreboard?dates=1")
    src = open(slv.__file__).read()
    assert "_get(fresh_url(stn.ESPN.format(tour=tour) + q))" in src and "_get(fresh_url(ESPN_SB.format(" in src


def test_nothing_posts_before_8am_whoever_calls():
    """9/29: the quick grader (a game ended at 12:21 AM PT) posted the day's whole board - the 8 AM PT rule only lived in
    run(). It lives in post_board now: nothing posts before 8 AM PT on game day, nothing for another day."""
    from datetime import datetime
    day = datetime(2026, 9, 29, 0, 21, tzinfo=sports.PT)
    assert sports.post_board({}, {}, [], day.astimezone(timezone.utc), day.date()) == []
    later = datetime(2026, 9, 28, 23, 0, tzinfo=sports.PT)
    assert sports.post_board({}, {}, [], later.astimezone(timezone.utc), day.date()) == []   # tomorrow's: never tonight


def test_drop_notes_built_fresh_every_day():
    """The owner, 9/29: the 8 AM note always says the engine watches the lines move all night and why, in our lingo, and
    it can't just cycle the same few - built from pieces, no piece the same as the day before (tennis too)."""
    import sports_dashboard as sdb
    from datetime import date, timedelta
    notes = set()
    for n in range(365):
        a, b = date(2026, 9, 1) + timedelta(n), date(2026, 9, 2) + timedelta(n)
        for parts in (sdb.DROP_PARTS, sdb.TN_DROP_PARTS):
            pa, pb = sdb._drop_parts(a.isoformat(), parts), sdb._drop_parts(b.isoformat(), parts)
            assert all(x != y for x, y in zip(pa, pb)), (a, parts[0][0])
        note = sdb._drop_note(a.isoformat())
        assert "8 AM PT" in note and ("all night" in note.lower() or "overnight" in note.lower()) and "—" in note
        notes.add(note)
    assert len(notes) > 100
    assert "8 AM PT" in sdb._tn_drop_note("2026-09-29")


def test_parlays_fold_to_one_line():
    """The owner, 9/29: parlays are too long - a parlay card folds to one 'tap to see the N legs' bar (no list of the
    legs up top - the card already shows them once open);
    a single pick (the lock, the dog) stays open."""
    import sports_dashboard as sdb
    leg = lambda t, **k: {"team": t, "market": "ml", "league": "mlb", "odds": -120, "start": "2026-09-29T23:00Z", "home": True,
                          "opp": "Opp", "reasons": [], "game_id": f"mlb:{t}", "side": "home", "p": 0.58, "tier": "lock", **k}
    two = {"kind": "two", "date": "2026-09-29", "status": "open", "stake": 100, "dec": 3.1, "american": 210,
           "legs": [leg("Yankees"), leg("Padres", result="won")]}
    html = sdb._card("two", two) if hasattr(sdb, "_card") else ""
    src = open(sdb.__file__).read()
    assert "_fold(legs, pk[\"legs\"]) if len(pk[\"legs\"]) > 1 else _fold_times(pk[\"legs\"], one=True) + legs" in src
    f = sdb._fold("<i>legs</i>", two["legs"])
    assert f.startswith('<details class="px">') and "Tap to see the 2 legs" in f and "Yankees" not in f.split("</summary>")[0]
    assert "<i>legs</i></details>" in f


def test_tennis_posts_at_8am_game_day():
    """The owner, 9/29: tennis goes up at 8 AM PT on game day, same as the main board (was 6 PM the night before)."""
    import sports_tennis as stq
    from datetime import datetime
    early = datetime(2026, 9, 29, 7, 30, tzinfo=stq.PT)
    keep = os.environ.pop("SPORTS_POST_NOW", None)
    try:
        assert stq.post({}, {}, {}, [], [], early.astimezone(timezone.utc)) is None        # 7:30 AM: not yet
        assert stq.post({}, {}, {}, [], [{"date": "2026-09-29", "picks": []}],
                        datetime(2026, 9, 29, 9, 0, tzinfo=stq.PT).astimezone(timezone.utc)) is None   # today's is up
    finally:
        if keep is not None:
            os.environ["SPORTS_POST_NOW"] = keep
    assert stq.POST_FROM_HOUR_PT == 8


def test_bottom_lines_no_odds_talk_and_no_repeats_on_a_board():
    """The owner, 9/29: 'book says 5 in 10, we say 6 in 10' don't make sense - and the same line on two cards (the
    Yankees + the Oilers both said 'we with the crowd tonight, but we got our own reasons'). No 'in 10' bottom line, and a
    board of breakdowns never repeats a wording."""
    import sports_breakdown_v24 as v24, re
    src = open(v24.__file__).read()
    bl = src[src.index("    # bottom line"):src.index("    lines = sports_card_guard.clean(")]
    assert "_odds_words" not in bl and not re.search(r" in 10\b", bl)    # (10/1: 'N in 100' is a real number, fine)
    used = set()
    lines = []
    for i in range(8):                                          # 8 cards on a board: the Voice never repeats a wording
        v = v24.Voice(f"seed{i}", used)
        lines.append(v.say("bottom_l", [f"a {i} one", f"b {i} two"], must=False) or "")
    for key, n in (("bottom_l", 14), ("bottom_s", 12), ("splits_w", 6)):
        assert src.count(f'v.say("{key}"') == 1
    assert 'must=True))' not in src[src.index('v.say("splits_f"'):src.index("    # the public: fading them")]


def test_tennis_bottom_lines_no_percent_talk():
    """The owner, 9/29: never 'book says X%, we say Y%' (one number, ours, is fine: '68% to cash, the house agrees'); 'has seen this movie
    before' always says what happened ('lost to him last time')."""
    import sports_tennis as stq
    for tpl in stq.T_BOTTOM + stq.T_BOTTOM_AGREE:            # one number (ours) is fine; never two side by side
        assert "{bk}" not in tpl and tpl.count("%") <= 1, tpl
    assert all("movie" not in t or "lost to" in t for t in stq.T_H2H)


def test_backup_books_fill_in_for_bovada():
    """The owner, 9/29: 'when one fails, it instantly goes to the other'. BetRivers (Kambi) reads the way its real feed
    looks; a backup fills in only a game Bovada has no fresh price for, and only with a fresh price; tennis sorts fresh
    prices first so a stale Bovada line never wins. No source that needs a borrowed key or access code (FanDuel dropped)."""
    import sports_books as bk, sports_live as slv
    now = time.time() * 1000
    iso = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    kam = {"events": [{"event": {"id": 1, "englishName": "Atlanta Braves - Philadelphia Phillies", "state": "STARTED",
                                 "start": "2026-09-29T18:16:00Z", "path": [{"englishName": "Baseball"}, {"englishName": "MLB"}]},
                       "betOffers": [{"criterion": {"englishLabel": "Moneyline"}, "betOfferType": {"englishName": "Match"},
                                      "outcomes": [{"englishLabel": "Atlanta Braves", "oddsAmerican": "-5000", "status": "OPEN", "changedDate": iso(now - 5000)},
                                                   {"englishLabel": "Philadelphia Phillies", "oddsAmerican": "850", "status": "OPEN", "changedDate": iso(now - 5000)}]}]},
                      {"event": {"id": 2, "englishName": "A - B", "state": "NOT_STARTED"}, "betOffers": []}]}
    got = bk.kambi_team(kam)
    assert got == [{"home": "Atlanta Braves", "away": "Philadelphia Phillies", "ml_home": -5000, "ml_away": 850,
                    "mod": got[0]["mod"], "src": "betrivers"}] and now - got[0]["mod"] < 10000
    ten = {"events": [{"event": {"englishName": "Elvina Kalieva - Shi Han", "state": "STARTED", "start": "2026-09-29T05:00:00Z",
                                 "path": [{"englishName": "Tennis"}, {"englishName": "WTA"}, {"englishName": "Beijing"}]},
                       "betOffers": [{"criterion": {"englishLabel": "Match Odds"}, "betOfferType": {"englishName": "Match"},
                                      "outcomes": [{"englishLabel": "Elvina Kalieva", "oddsAmerican": "-150", "status": "OPEN", "changedDate": iso(now)},
                                                   {"englishLabel": "Shi Han", "oddsAmerican": "120", "status": "OPEN", "changedDate": iso(now)}]}]},
                      {"event": {"englishName": "X Y - Z W", "state": "STARTED", "path": [{}, {"englishName": "ITF Men"}]}, "betOffers": []}]}
    tl = bk.kambi_tennis(ten)
    assert len(tl) == 1 and tl[0]["tour"] == "wta" and tl[0]["a_ml"] == -150 and not tl[0]["suspended"]
    bov = [{"home": "Atlanta Braves", "away": "Philadelphia Phillies", "ml_home": -4000, "ml_away": 900, "src": "bovada"}]
    other = {"home": "Houston Astros", "away": "Seattle Mariners", "ml_home": 120, "ml_away": -140, "mod": now, "src": "betrivers"}
    old = {**other, "home": "Texas Rangers", "away": "Oakland Athletics", "mod": now - 10 * 60 * 1000}
    out = slv.with_backups(bov, got + [other, old], now)
    assert out[0]["src"] == "bovada" and other in out and old not in out and len(out) == 2   # Bovada stands; stale out
    assert slv.with_backups([], got, now) == got                                             # Bovada down: backup takes over
    stale_bov = [{"a": "Elvina Kalieva", "b": "Shi Han", "a_ml": 125, "b_ml": -150, "stale": True, "src": "bovada"}]
    merged = slv.tennis_with_backups(stale_bov, tl, now)
    assert merged[0]["src"] == "betrivers" and merged[-1].get("stale")                        # fresh first
    import sports_tennis as stq
    m = {"p1_name": "Elvina Kalieva", "p2_name": "Shi Han", "start": "2026-09-29T05:00Z", "tour": "wta", "id": "wta:1"}
    ln, _ = stq.match_line(m, merged, hours=12)
    assert ln["src"] == "betrivers" and ln["a_ml"] == -150
    src = open(bk.__file__).read()
    assert "pinnacle" not in src.lower() and "X-API-Key" not in src                     # no borrowed keys
    import glob
    for f in [g for g in glob.glob("*.py") + glob.glob("tools/*.py") if "test" not in g]:   # ...and no access codes
        assert "_ak=" not in open(f).read(), f
    assert not hasattr(bk, "FANDUEL") and "fanduel" not in open(slv.__file__).read().lower()


def test_live_game_list_falls_back_to_espn_and_bets_grade_anyway():
    """The owner, 9/29: Action Network down = the watcher was blind (no live plays). It moves to ESPN's scoreboard in
    the same shape the watcher reads - football's ball spot included - and a live bet grades from our own stored finals
    whichever list it came from."""
    import sports_live as slv
    ev = {"id": "401", "date": "2026-10-02T00:15Z", "competitions": [{
        "status": {"period": 3, "displayClock": "8:42", "type": {"state": "in", "shortDetail": "8:42 - 3rd"}},
        "situation": {"possession": "3", "possessionText": "CHI 35", "downDistanceText": "2nd & 7 at CHI 35"},
        "competitors": [{"homeAway": "home", "score": "17", "team": {"id": "3", "displayName": "Chicago Bears", "abbreviation": "CHI"},
                         "linescores": [{"value": 7}, {"value": 3}, {"value": 7}]},
                        {"homeAway": "away", "score": "10", "team": {"id": "21", "displayName": "Philadelphia Eagles", "abbreviation": "PHI"},
                         "linescores": [{"value": 0}, {"value": 10}, {"value": 0}]}]}]}
    a = slv.espn_as_an("nfl", ev)
    assert a["status"] == "inprogress" and a["home_team_id"] == "3" and a["teams"][0]["full_name"] == "Chicago Bears"
    assert slv._score(a["boxscore"], "home") == 17 and slv._score(a["boxscore"], "away") == 10
    assert a["boxscore"]["situation"] == {"possession": "3", "yards_to_endzone": 65, "display_short": "2nd & 7 at CHI 35"}
    ev["competitions"][0]["situation"]["possessionText"] = "PHI 20"                    # in the red zone
    assert slv.espn_as_an("nfl", ev)["boxscore"]["situation"]["yards_to_endzone"] == 20
    keep = slv.fetch_live, slv._get
    try:
        def down(lg):
            sd.ERRORS.append(f"live {lg}: HTTP Error 403: Forbidden")
            return []
        slv.fetch_live = down
        slv._get = lambda url: {"events": [ev]}
        got = slv.fetch_live_any("nfl")
        assert got and got[0]["id"] == "espn:401" and "nfl" in slv.AN_DOWN       # Action Network down: ESPN's list
        slv.fetch_live = lambda lg: [{"id": 9}]
        assert slv.fetch_live_any("nfl") == [{"id": 9}] and "nfl" not in slv.AN_DOWN   # back: Action Network again
    finally:
        slv.fetch_live, slv._get = keep
    log = {"plays": {"nfl:401:home": {"result": None, "league": "nfl"}, "nfl:402:away": {"result": None, "league": "nfl"},
                     "nfl:403:home": {"result": None, "league": "nfl"}}}
    games = {"nfl:401": {"status": "final", "home_score": "24", "away_score": "20"},
             "nfl:402": {"status": "final", "home_score": "24", "away_score": "20"}, "nfl:403": {"status": "in"}}
    slv.grade_from_games(log, games)
    assert [log["plays"][k]["result"] for k in ("nfl:401:home", "nfl:402:away", "nfl:403:home")] == ["won", "lost", None]


def test_yahoo_splits_backup():
    """Action Network down: the betting splits come from Yahoo's odds page instead (% of bets only - Yahoo shows no
    money %), matched to our games by team, and a breakdown with bets % only says it plain (no 'None%')."""
    import sports_public as spb, json as _j
    games_json = [{"gameId": "mlb.g.1", "alias": {"url": "https://sports.yahoo.com/mlb/philadelphia-phillies-atlanta-braves-460929115/"},
                   "homeTeam": {"teamId": "mlb.t.15"}, "awayTeam": {"teamId": "mlb.t.22"},
                   "bets": [{"type": "MONEY_LINE", "eventState": "PREGAME", "options": [
                       {"name": "Atlanta", "americanOdds": -185, "teamIds": ["mlb.t.15"], "wagerPercentage": "73.47"},
                       {"name": "Philadelphia", "americanOdds": 155, "teamIds": ["mlb.t.22"], "wagerPercentage": "26.53"}]},
                            {"type": "MONEY_LINE", "eventState": "LIVE", "options": [{"name": "Atlanta", "teamIds": ["mlb.t.15"]}]}]}]
    html = 'x<script>self.__next_f.push([1,' + _j.dumps('81:["$","$L83",null,' + _j.dumps({"games": games_json}) + ']') + '])</script>'
    rows = spb.yahoo_rows(spb.yahoo_games(html))
    assert rows == [{"home_full": "atlanta braves", "away_full": "philadelphia phillies",
                     "splits": {"ml_home_t": 73, "ml_home_m": None, "ml_home_odds": -185, "ml_away_t": 27,
                                "ml_away_m": None, "ml_away_odds": 155, "src": "yahoo"}}]
    now = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)
    games = {"mlb:1": {"id": "mlb:1", "league": "mlb", "status": "pre", "start": "2026-09-29T23:15Z",
                       "home_name": "Atlanta Braves", "away_name": "Philadelphia Phillies"}}
    assert spb.yahoo_match(games, "mlb", rows, now) == {"mlb:1": rows[0]["splits"]}
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_breakdown_v24.py")).read()
    assert "if sp_ and sp_[1] is None:" in src


def test_breakdowns_say_it_plain():
    """The owner, 9/29 (Oilers-Canucks): 'starting G' / 'backup G' confused everybody, two goalie-out lines read like
    nonsense, and 'circled on both calendars' / 'leaky as hell' meant nothing; 'broken clock, right time' too (Yankees). Positions are spelled out, both teams
    missing a starter is one line, goalie form names whose goalie, and those idioms are gone."""
    import sports_breakdown_v24 as v24
    assert v24._posname("G") == "goalie" and v24._posname("LW") == "left wing" and v24._posname("QB") == "quarterback"
    assert v24._poss("the Canucks") == "The Canucks'" and v24._poss("Duke") == "Duke's"
    src = open(v24.__file__).read()
    for gone in ("leaky as hell", "beach ball", "Circled on", "out the window", "roken clock", "stopped clock", "starting {pos}\"" , "{key_them[0][1]}"):
        assert gone not in src, gone
    assert 'v.say("keyout_both"' in src and "_posname(key_us[0][1], lg)" in src and "_posname(key_them[0][1], lg)" in src


def test_playoff_game_gets_its_real_teams():
    """9/29: MLB playoff games were stored while the teams were 'TBD' (ids -1 / -2); ESPN filled in the Astros but our
    copy kept id -1, the engine knew '0 games' for them and skipped White Sox (+102, bet down from +120) @ Astros
    entirely. A fresh read with the real team always replaces a placeholder - and a placeholder never wipes a real one."""
    old = {"id": "mlb:1", "home": "-1", "away": "-2", "home_name": "TBD", "away_name": "TBD", "start": "2026-09-29T21:00Z",
           "status": "pre", "ml_home": "", "ml_away": ""}
    new = {**old, "home": "18", "away": "4", "home_name": "Astros", "away_name": "White Sox", "ml_home": "-123",
           "ml_away": "102", "home_score": "", "away_score": "", "neutral": 0, "sp_home": "", "sp_away": "", "stype": "3",
           "country": "", "intl": 0, "city": "", "state": "", "indoor": 0}
    g = sd.merge(old, new, "2026-09-29T15:00Z")
    assert g["home"] == "18" and g["away"] == "4"
    back = sd.merge(g, {**new, "home": "-1"}, "2026-09-29T15:05Z")
    assert back["home"] == "18"                                         # a placeholder never wipes the real team


def test_added_pick_pings_everyone():
    """The owner, 9/29: a pick added after the board is up pinged everyone. 9/30: 'the only notifications should be
    the live plus money' - so it's off (ANNOUNCE_PINGS); the wording still works for when it's back on."""
    assert sports.ANNOUNCE_PINGS is False
    quiet, keep0 = [], sd.web_push
    sd.web_push = lambda *a, **k: quiet.append(a)
    try:
        sports.announce_pick({"kind": "lock", "legs": [{"team": "Yankees", "market": "ml", "odds": -135, "league": "mlb",
                                                         "side": "home", "line": None}], "american": -135})
    finally:
        sd.web_push = keep0
    assert quiet == []                                               # no ping
    sports.ANNOUNCE_PINGS = True
    sent, keep = [], sd.web_push
    sd.web_push = lambda raw, title=None, body=None: sent.append((title, body))
    try:
        leg = {"team": "Yankees", "market": "ml", "odds": -135, "league": "mlb", "side": "home", "line": None}
        sports.announce_pick({"kind": "lock", "legs": [leg], "american": -135})
        sports.announce_pick({"kind": "two", "legs": [leg, {**leg, "team": "Oilers", "market": "spread", "line": -1.5, "odds": -118}],
                              "american": 212})
    finally:
        sd.web_push = keep
        sports.ANNOUNCE_PINGS = False
    assert sent[0][0].startswith("🆕 NEW PICK: Yankees") and "-135" in sent[0][0] and "Lock of the Day" in sent[0][1]
    assert "2-leg parlay (+212)" in sent[1][0] and "Oilers" in sent[1][1]
    src = open(sports.__file__).read()
    assert src.count("if had:\n") >= 2 and src.count("announce_pick(pk)") >= 2


def test_parlay_bar_shows_game_times_and_live_stays_live():
    """The owner, 9/29: start times, live times and live scores on the cards - a folded parlay too. The bar says
    'First game starts at 5 PM PT' (not 'next up'), then '🔴 N LIVE · Next game starts at ...', then 'All games
    final'. And a live game's LIVE badge stays put (a stray line used to swap the start time right back in)."""
    import sports_dashboard as sdb
    legs = [{"start": "2026-09-30T02:30Z"}, {"start": "2026-09-30T00:00Z"}, {"start": "2026-09-30T02:00Z"}]
    assert "🕐 First game starts at 5 PM PT" in sdb._fold_times(legs)
    css = open(sdb.__file__).read()                  # the owner: yellow at all times (never dull gray, never switching
    assert "color:var(--gold)" in css[css.index(".pxt{{"):css.index(".pxt{{") + 200]   # colors) - the 🔴 says live
    assert ".pxt." not in css and "t.className" not in css
    assert ".pxo,.pxc{{font-size:14px;color:var(--gold)" in css                         # 'Tap to see the legs': yellow too
    assert "5 PM PT" not in sdb._fold_times([{**legs[1], "result": "won"}, legs[0]])       # a graded game's done
    assert "All games final" in sdb._fold_times([{**l, "result": "won"} for l in legs])
    one = sdb._fold_times([legs[1]], one=True)                          # the lock / dog card gets the yellow line too
    assert "🕐 Game starts at 5 PM PT" in one and 'data-one="1"' in one  # (the owner, 9/29: 'it's simply not there')
    assert "🏁 Final" in sdb._fold_times([{**legs[1], "result": "won"}], one=True)
    assert '_fold_times(pk["legs"], one=True) + legs' in open(sdb.__file__).read()
    src = open(sdb.__file__).read()
    assert "Next game starts at" in src and "next up" not in src.replace("next up'", "")
    i = src.index('leg.parentNode.insertBefore(sr,leg);}}}}')          # (10/2: the final-score stamp closes the on-branch)
    assert src[i:i + 120].split("\n")[1].lstrip().startswith("else if(s.dataset.lv)")       # restore only when not on


def test_game_clock_says_intermission_and_all_that():
    """The owner, 9/29: hockey shows the time, the period and the score - and whether it's an intermission. Same for
    halftime, OT and the rest, when the watcher's backup scores are the ones on the card ('P1 0:00' meant nothing).
    The live-bet review still reads the right period out of it."""
    import sports_live as slv, sports_dashboard as sdb
    c = slv._clock_txt
    assert c("nhl", {"period": 2, "clock": "6:12"}) == "6:12 - 2nd"
    assert c("nhl", {"period": 1, "clock": "0:00"}) == "1st Intermission"
    assert c("nhl", {"period": 2, "clock": "0.0"}) == "2nd Intermission"
    assert c("nhl", {"period": 4, "clock": "3:21"}) == "3:21 - OT" and c("nhl", {"period": 5, "clock": ""}) == "SO"
    assert c("nfl", {"period": 2, "clock": "0:00"}) == "Halftime" and c("nba", {"period": 3, "clock": "8:21"}) == "8:21 - 3rd"
    assert c("ncaab", {"period": 1, "clock": "0:00"}) == "Halftime" and c("ncaab", {"period": 2, "clock": "12:34"}) == "12:34 - 2nd Half"
    assert c("mlb", {"period": 5, "inning_half": "top"}) == "Top 5th"
    assert c("nhl", {"period": 2, "clock": None}) == "2nd"                 # no clock is no clock - never a fake break
    base = {"team": "Oilers", "league": "nhl", "side": "home", "score_at_post": "Canucks 1 @ Oilers 1", "result": "won",
            "odds": 120, "date": "2026-09-29"}
    story = lambda ck: sdb._live_story({**base, "clock_at_post": ck}, set())
    assert "1st period" in story("1st Intermission") and "2nd period" in story("6:12 - 2nd")
    assert "overtime" in story("3:21 - OT") and "3rd period" not in story("3:21 - OT")


def test_top_right_just_says_live():
    """The owner, 9/29: 'Live · 10 min ago' read like the scores were 10 minutes old, 'Board updated…' was no better,
    and 'Reconnecting' reads like a glitch. The top right just says 🟢 LIVE (the hourly bug check handles a stall)."""
    import sports_dashboard as sdb
    src = open(sdb.__file__).read()
    assert '<span id="ago">LIVE</span>' in src
    for gone in ('"Live · "', "min ago", "Reconnecting", '"dot stale"'):
        assert gone not in src.split("def write(")[1], gone


def test_why_line_is_a_real_line_not_a_tag():
    """The owner, 9/29: 'the stronger team' under the pick is way too vague - a dope, strong line in our lingo, every
    pick, every sport. The line under the pick is written with the breakdown (real records / streaks / who's out),
    never a bare reason tag; old picks and the question box's reads get a lingo line too."""
    import sports_breakdown_v24 as v24, sports_dashboard as sdb
    g = {"id": "mlb:1", "start": "2026-09-30T00:00Z", "home": "10", "away": "2", "sp_home": "Gerrit Cole", "sp_away": "X"}
    base = {"team": "Yankees", "opp": "Red Sox", "league": "mlb", "side": "home", "p": 0.58, "tier": "lock", "ctx": []}
    say = lambda leg, **k: v24.why_line(leg, v24.Voice("s", set()), g, "Yankees", "Red Sox", "the Yankees", "the Red Sox", **k)
    a = say({**base, "reasons": ["the stronger team"]}, rec_u="93-68", rec_t="87-75")
    assert "93-68" in a and "87-75" in a and "stronger team" not in a and a[:1] in "💪"   # (10/1, never vague: the
    #                                                          records ARE the fact - "just the better team" is banned)
    assert not say({**base, "reasons": ["the stronger team"]}, rec_u="80-80", rec_t="90-70").startswith("💪")   # worse
    #                                                          record: never "the better team"
    b = say({**base, "reasons": ["hotter recent form"]}, n_hot=4, rec_u="93-68")
    assert "4 straight" in b or "heater" in b.lower() or "cooking" in b
    c = say({**base, "reasons": ["opponent missing key players"], "opp_outs": ["Lukas Cormier (D)"]})
    assert "Lukas Cormier" not in c and "(D)" not in c   # (10/1, the owner: a depth D is never sold as our edge)
    c2 = v24.why_line({**base, "reasons": ["opponent missing key players"]}, v24.Voice("s2", set()), g, "Yankees",
                      "Red Sox", "the Yankees", "the Red Sox", key_them=[("Garrett Crochet", "SP", "Out")], key_us=[])
    assert "Garrett Crochet" in c2                     # a KEY player out is named
    d = say({**base, "reasons": []})
    assert "58%" in d
    v = v24.Voice("board", set())                                       # never the same wording twice on a board
    lines = [v24.why_line({**base, "reasons": ["the stronger team"]}, v, g, "Yankees", "Red Sox", "the Yankees",
                          "the Red Sox", rec_u="93-68", rec_t="87-75") for _ in range(4)]
    assert len(set(lines)) == 4, lines
    card = sdb._leg({**base, "market": "ml", "odds": -135, "line": None, "home": True, "start": "2026-09-30T00:00Z",
                     "game_id": "mlb:1", "reasons": ["the stronger team"]})
    assert "the stronger team" not in card and "better team" in card               # an old pick: still our lingo
    card2 = sdb._leg({**base, "market": "ml", "odds": -135, "line": None, "home": True, "start": "2026-09-30T00:00Z",
                      "game_id": "mlb:1", "reasons": ["the stronger team"], "why_line": a})
    assert a in card2.replace("&#x27;", "'")
    src = open(sdb.__file__).read()
    assert 'L.reasons.map(esc).join(" · ")' not in src and "whyl(L,g)" in src     # the question box too



def test_tennis_cards_get_the_tag_line():
    """The owner, 9/29: tennis cards get the same line under the pick as the main board - the breakdown's headline -
    and the rest stays behind 'Full breakdown' (never said twice)."""
    import sports_dashboard as sdb
    src = open(sdb.__file__).read()
    assert 'tag, lines = (lines[0], lines[1:]) if len(lines) > 1 else ("", lines)' in src
    assert "{f'<div class=\"why rvy\">{E(pct_ok(tag))}</div>' if tag else \"\"}" in src   # (yellow; a win % only over 55)



def test_facts_only_after_a_claim():
    """The owner, 9/29: 'The math gives him 59%. Facts.' makes no sense - facts goes after a claim ('Yankees are just
    the better team. That's just facts.'), never tacked onto a number."""
    import sports_vocab as sv, sports_tennis as stn, sports_breakdown_v24 as v24
    assert not any("facts" in k.lower() for k in sv.WORDS["kick"]) if hasattr(sv, "WORDS") else True
    src = open(sv.__file__).read()
    assert '"Facts."' not in src
    for pool in (stn.T_FAV, stn.T_SMALLFAV):
        for line in pool:
            assert "{pct}%. Facts" not in line and "%.] Facts" not in line
    assert "That's just facts." in open(v24.__file__).read()


def test_started_game_is_live_never_final():
    """9/30: the Lock said '🏁 Final' at first pitch. A tennis 'var n' in the live-tag loop hid the clock 'n' (JS var
    hoisting), so a started game with no score yet never flipped to LIVE - and the yellow line read that as final.
    'Final' only once every game really shows FINAL; a delay says DELAYED."""
    import sports_dashboard as sdb
    src = open(sdb.__file__).read()
    loop = src[src.index('document.querySelectorAll(".tm[data-start]").forEach(function(s){{'):src.index('document.querySelectorAll(".pxt")')]
    assert "var n=" not in loop and "var ns=(sc.sets" in loop
    assert 'dl?"⏳ DELAYED":"🏁 Final"' in src and "(!fin&&st<=n))lv++" in src



def test_every_leg_says_starts_at_in_yellow():
    """The owner, 9/29: the small corner time got missed and was hard to see - it says 'Starts at 7 PM PT', big and
    bright yellow, on every leg (it flips to LIVE / FINAL itself). No second time line under the leg."""
    import sports_dashboard as sdb
    leg = {"team": "Oilers", "opp": "Canucks", "league": "nhl", "side": "home", "home": True, "market": "spread",
           "line": -1.5, "odds": -118, "start": "2026-09-30T02:00Z", "game_id": "nhl:1", "reasons": []}
    h = sdb._leg(leg, tagged=True)
    assert ">Starts at 7 PM PT</span>" in h and 'class="lst"' not in h
    assert ".lt>.tm{{font-size:13px;font-weight:900;letter-spacing:.04em;color:var(--gold)" in open(sdb.__file__).read()


def test_engine_knows_who_is_not_playing_baseball():
    """9/29: Aaron Judge was on the 10-day IL (ESPN listed him '10-Day-IL') and the engine never knew - the injury
    reader only kept 'Out' / 'Doubtful' / 'Injured Reserve', so every MLB injured-list player was invisible, and
    baseball had no key players at all. Now: every roster status counts, each team's best bats are key players (MLB's
    own season stats), a star missing from the confirmed lineup puts an alert on the card, and the breakdown says it
    in our lingo - out, but it don't change our call."""
    inj = sd.parse_injuries({"injuries": [{"id": "10", "displayName": "New York Yankees", "injuries": [
        {"status": "10-Day-IL", "athlete": {"displayName": "Aaron Judge", "position": {"abbreviation": "RF"}}},
        {"status": "60-Day-IL", "athlete": {"displayName": "Fernando Cruz", "position": {"abbreviation": "RP"}}},
        {"status": "paternity", "athlete": {"displayName": "Some Guy", "position": {"abbreviation": "C"}}},
        {"status": "Day-To-Day", "athlete": {"displayName": "Ben Rice", "position": {"abbreviation": "1B"}}}]}]})
    names = [r[0] for r in sd.team_injuries(inj, "10", "Yankees")]
    assert "Aaron Judge" in names and "Some Guy" in names and "Fernando Cruz" not in names   # 60-day: long-term
    stars = sd.parse_stars({"stats": [{"splits": [
        {"player": {"fullName": "Ben Rice"}, "team": {"name": "New York Yankees"}, "stat": {"plateAppearances": 667, "ops": ".897"}},
        {"player": {"fullName": "Aaron Judge"}, "team": {"name": "New York Yankees"}, "stat": {"plateAppearances": 285, "ops": ".871"}},
        {"player": {"fullName": "Cody Bellinger"}, "team": {"name": "New York Yankees"}, "stat": {"plateAppearances": 562, "ops": ".767"}},
        {"player": {"fullName": "Jazz Chisholm Jr."}, "team": {"name": "New York Yankees"}, "stat": {"plateAppearances": 532, "ops": ".711"}},
        {"player": {"fullName": "Call Up"}, "team": {"name": "New York Yankees"}, "stat": {"plateAppearances": 40, "ops": "1.200"}}]}]})
    assert stars["New York Yankees"] == ["Ben Rice", "Aaron Judge", "Cody Bellinger"]      # regulars only
    keep = dict(sd._STARS)
    sd._STARS.clear(); sd._STARS.update(stars)
    try:
        assert [r[0] for r in sd.team_key_out(inj, "10", "Yankees", "mlb")] == ["Aaron Judge"]
        assert [r[0] for r in sd.team_unsure(inj, "10", "Yankees", "mlb")] == ["Ben Rice"]
        lu = sd.parse_lineups({"dates": [{"games": [{"gameDate": "2026-09-30T00:00:00Z", "teams": {
            "away": {"team": {"name": "Boston Red Sox"}}, "home": {"team": {"name": "New York Yankees"}}},
            "lineups": {"homePlayers": [{"fullName": "Paul Goldschmidt"}, {"fullName": "Ben Rice"}],
                        "awayPlayers": [{"fullName": "Roman Anthony"}]}}]}]})
        g = {"league": "mlb", "home": "10", "away": "2", "home_name": "Yankees", "away_name": "Red Sox",
             "start": "2026-09-30T00:00Z"}
        assert sd.lineup_for(lu, g, "home") == ["Paul Goldschmidt", "Ben Rice"]
        ks = sports.key_status({}, g, lu)
        assert ks.get("Cody Bellinger (Yankees)") == "Not in the lineup"                   # a star sat: on the card
        ks2 = sports.key_status(inj, g, lu)
        assert "Aaron Judge (Yankees RF)" in ks2 and "Aaron Judge (Yankees)" not in ks2    # said once, as IL
    finally:
        sd._STARS.clear(); sd._STARS.update(keep)
    assert "mlb" in sd.INJ_LEAGUES
    src = open(__import__("sports_breakdown_v24").__file__).read()
    assert 'v.say("keyout_us_bat"' in src and "Doesn't change our call" in src


def test_never_lock_a_side_the_money_is_running_from():
    """9/29, the Astros: opened -143, the money ran to the White Sox all day (-123 at first pitch), they got smacked -
    and with the placeholder bug fixed the engine would have made them the Lock. 10 seasons: a favorite the money runs
    from wins what the CLOSE says (49-54% where the open said 56-64%), every league, old and new. Our engine hasn't
    proven it beats the pros after a move (sports_sharps), so a side the money ran 3+ points from is never the Lock /
    Dog / a leg; and after posting, the money running from our pick puts a LINE ALERT on the card (pick unchanged)."""
    import sports_sharps
    c = {"league": "mlb", "edge": -0.03, "edge_own": -0.03, "dec": 1.7, "drift": 0.034}
    keep = dict(sports_sharps._CACHE)
    sports_sharps._CACHE["p"] = set()
    try:
        assert sports.money_against(c) and sports.fighting(c)
        assert not sports.money_against({**c, "drift": 0.01})
        sports_sharps._CACHE["p"] = {"mlb"}                              # proven someday: our engine may go against it
        assert not sports.money_against(c)
    finally:
        sports_sharps._CACHE.clear(); sports_sharps._CACHE.update(keep)
    g = {"id": "mlb:1", "league": "mlb", "status": "pre", "ml_home": "-123", "ml_away": "102",
         "ml_home_open": "-143", "ml_away_open": "120"}
    leg = {"game_id": "mlb:1", "side": "home", "team": "Astros", "market": "ml", "odds": -143,
           "p_market": sd.no_vig(-143, 120)}
    picks = [{"status": "open", "legs": [leg]}]
    out = sports.line_watch({"mlb:1": g}, picks)
    assert len(out) == 1 and "-143 when we posted, -123 now" in out[0] and leg["line_alerts"]
    assert sports.line_watch({"mlb:1": g}, picks) == []                  # said once
    import sports_dashboard as sdb
    card = sdb._leg({"team": "Astros", "opp": "White Sox", "league": "mlb", "side": "home", "home": True, "market": "ml",
                     "line": None, "odds": -143, "start": "2026-09-29T21:00Z", "game_id": "mlb:1", "reasons": [],
                     "line_alerts": leg["line_alerts"]})
    assert "💸 LINE ALERT" in card


def test_owner_lingo_is_live_everywhere():
    """The owner, 9/29: 'always remember how I talk ... and add it into the engine'. Every phrase on his list is live
    somewhere in the write-ups, and the words he's banned never show up."""
    import sports_owner_lingo as ol
    text = "\n".join(open(f).read() for f in ol.SOURCES).lower()
    missing = [w for w in ol.OWNER if w.lower() not in text]
    assert not missing, missing                            # (the banned words: the existing variety tests keep them out)
    every = "\n".join(open(f).read() for f in ol.SOURCES + ("sports_vocab.py", "sports_breakdown.py")).lower()
    assert "class of th" not in every, "9/29: 'the class of the match' - he's never heard it said"
    assert "class of this" in ol.NEVER
    # 9/29: "Snigur won it. Cook." - bare 'Cook' after a win reads wrong; "got cooked" / "shit the bed" are for a LOSS
    assert not re.search(r"[\[|\"']Cook\.?[\]|\"']", every.replace("cook", "x") if False else
                         "\n".join(open(f).read() for f in ol.SOURCES + ("sports_vocab.py", "sports_breakdown.py"))), "bare Cook"
    import sports_lingo as SL
    for k in ("tn:won", "ls:won", "rc:battle"):
        assert not any("cooked" in t for t in SL.LINES[k][2]), k
    assert any("got cooked" in t for t in SL.LINES["tn:lost"][2]) and any("shit the bed" in t for t in SL.LINES["tn:lost"][2])
    # 9/30: "+200 moneyline, we smacked" / "the 49ers smacked" - a WIN; never "cooked" for a winner
    assert "We smacked." in SL.PAL["wk"] and any("smacked" in t for t in SL.REVIEWS[("dog", "won")][2])
    assert not any("cooked" in t for t in SL.REVIEWS[("dog", "won")][2])


def test_our_own_engine_never_a_sharp_follower():
    """The owner, 9/29: we're our own engine - the write-ups never say we're following the sharps, and never claim
    it's 'sharp money' at all (nobody outside the book knows who bet it; all we see is the price move). A price move
    toward us reads as the market catching up to the engine, and it's never the headline when the engine has its own
    reason. The studies + simulator run three times a day, with a backstop when GitHub's schedule skips one."""
    import re, sports_breakdown_v24 as v24, sports_dashboard as sdb
    shown = "\n".join(re.findall(r'f?"[^"\n]*"', open(v24.__file__).read() + open(sdb.__file__).read())).lower()
    for gone in ("sharp money's been", "we with the pros", "follow the money", "smart money agrees", "the pros see it",
                 "so-called sharps", "sharps show their hand", "sharp money is on us"):
        assert gone not in shown, gone
    g = {"id": "mlb:1", "start": "2026-09-30T00:00Z"}
    leg = {"team": "Yankees", "opp": "Red Sox", "league": "mlb", "side": "home", "p": 0.58, "tier": "lock", "ctx": [],
           "reasons": ["sharp money moving this way", "hotter recent form"]}
    line = v24.why_line(leg, v24.Voice("s", set()), g, "Yankees", "Red Sox", "the Yankees", "the Red Sox", n_hot=3)
    assert line.startswith("🔥")                                         # the engine's own reason leads
    assert "catching up" in sdb._why_fallback({"team": "Yankees", "opp": "Red Sox",
                                               "reasons": ["sharp money moving this way"]})
    wf = open(".github/workflows/sports_studies.yml").read()
    assert wf.count("- cron:") == 3 and 'dispatch(wf, f"{name} overdue' in open("tools/health.py").read()



def test_bug_check_has_a_backstop():
    """9/29: the 'hourly' bug check had 3-hour gaps (GitHub's schedule skips runs). The engine's backstop (run by every
    engine run) starts it when it's 90+ minutes old - the same way the studies, the simulator and the live watch are covered."""
    s = open("tools/backstop.sh").read()
    assert "gh workflow run health.yml" in s and '-gt 90' in s
    assert "workflow_dispatch" in open(".github/workflows/health.yml").read()


def test_a_game_that_has_not_started_is_never_final():
    """9/29: the Blackhawks card read 'FINAL 0-0' ten minutes after puck drop - the odds feed still said 'scheduled'
    and the watcher's 'done' list held 'scheduled'. Not started = no score; postponed = DELAYED; Final only when over.
    And the ML / -1.5 next to the team is white (the owner)."""
    import sports_live as slv, sports_dashboard as sdb
    games = {"nhl:9": {"id": "nhl:9", "league": "nhl", "home_name": "Golden Knights", "away_name": "Blackhawks",
                       "start": "2026-09-30T02:30Z", "home": "37", "away": "4"}}
    keep_m, keep_s = slv._match, dict(slv.SCORES)
    slv._match = lambda games_, lg, ang: games["nhl:9"]
    try:
        slv.SCORES.clear()
        box = {"period": 1, "clock": "20:00", "total_home_points": 0, "total_away_points": 0}
        slv._keep_score(games, "nhl", {}, box, "scheduled")
        assert "nhl:9" not in slv.SCORES
        slv._keep_score(games, "nhl", {}, box, "postponed")
        assert slv.SCORES["nhl:9"]["delayed"] and slv.SCORES["nhl:9"]["clock"] != "Final"
        slv._keep_score(games, "nhl", {}, {**box, "clock": "12:00"}, "inprogress")
        assert slv.SCORES["nhl:9"]["live"] and slv.SCORES["nhl:9"]["clock"] == "12:00 - 1st"
        slv._keep_score(games, "nhl", {}, box, "complete")
        assert slv.SCORES["nhl:9"]["clock"] == "Final" and not slv.SCORES["nhl:9"]["live"]
    finally:
        slv._match = keep_m; slv.SCORES.clear(); slv.SCORES.update(keep_s)
    assert ".pick em{{font-style:normal;color:#fff" in open(sdb.__file__).read()


def test_graded_card_shows_the_review_where_the_pregame_line_was():
    """The owner, 9/29: once a card is graded, the pregame line goes away and the after-game review takes its spot -
    both in white. (Main board and tennis.)"""
    import sports_dashboard as sdb
    leg = {"team": "Yankees", "opp": "Red Sox", "league": "mlb", "side": "home", "home": True, "market": "ml",
           "line": None, "odds": -135, "start": "2026-09-30T00:00Z", "game_id": "mlb:1", "reasons": [],
           "why_line": "💪 Yankees (93-68) vs Red Sox (88-74) — the better team's on our side.", "result": "won",
           "score": "Red Sox 0 @ Yankees 9"}                     # (a real line - filler is the card guard's job, 10/1)
    h = sdb._leg(leg, review="The Yankees beat the Red Sox like they stole something.")
    assert "📝 The Yankees beat the Red Sox like they stole something." in h and "93-68" not in h
    assert h.count('class="why rvy"') == 1
    pre = sdb._leg({**leg, "result": None})
    assert "93-68" in pre and "📝" not in pre
    src = open(sdb.__file__).read()
    assert ".why{{font-size:13px;color:#fff" in src and 'tag = f"📝 {recap(l)}"' in src


def test_lock_of_the_day_on_top_and_text_solid_white():
    """The owner, 9/29: the Lock of the Day always sits on top of the day's board (right under live plus money), graded
    or not; and the text on the cards is bold, solid white - no thin or faded gray (vs line, pregame line, review, final)."""
    import sports_dashboard as sdb
    assert list(sdb.LOOK)[:2] == ["lock", "dog"]
    css = open(sdb.__file__).read()
    for rule in (".ls{{font-size:13px;color:#fff;font-weight:700", ".why{{font-size:13px;color:#fff;font-weight:700",
                 ".fin{{font-size:12.5px;color:#fff;font-weight:700"):
        assert rule in css, rule


def test_no_dull_gray_text_anywhere():
    """The owner, 9/29: 'we don't want any dull gray - always solid bold white'. No gray/tan text colors, no faded lost
    cards, the score line / FINAL tag / tennis scoreboard / past results all white."""
    import re, sports_dashboard as sdb
    src = open(sdb.__file__).read()
    for gray in ("9fb0c8", "9aa4b2", "e8eef6", "cfd6df", "7d8794"):
        assert "color:#" + gray not in src and 'hue = "#' + gray not in src, gray
    assert "color:#e8c77a" not in src and ".pk.lost>*:not(.stamp-row){{opacity" not in src


def test_live_boxes_bet_it_now_and_tonights_bets():
    """The owner, 9/29: two clear boxes. Red: 'LIVE PLUS MONEY · BET IT NOW' - only what you can bet right now (or
    'The algorithm's watching every play for value. 13 games going.'); blue: 'TONIGHT'S LIVE BETS · WE'RE IN' - our bets, STILL GOING ->
    CASHED / MISSED, up till the next board. (An apostrophe inside the page script once broke the whole live section:
    the script is written with &#39;.)"""
    import sports_dashboard as sdb
    src = open(sdb.__file__).read()
    assert 'LIVE PLUS MONEY</span><span class="chip bin">BET IT NOW</span>' in src
    assert "TONIGHT&#39;S LIVE BETS" in src and "WE&#39;RE IN" in src and "⏳ STILL GOING" in src and "❌ MISSED" in src
    assert "Checking the live" not in src and "👀 The algorithm’s watching every play for value. '+n+' game" in src   # (the
    #                                                                                   owner's own words, short)


def test_tonights_live_bets_box_only_when_we_have_bets():
    """The owner, 9/29: the TONIGHT'S LIVE BETS box doesn't show at all until we actually have a live bet in. Built
    empty when there are none; the page adds it only when the first bet arrives; yesterday's clear at the 8 AM board."""
    import sports_dashboard as sdb
    from datetime import datetime
    src = open(sdb.__file__).read()
    assert 'live_list = ("" if not lrows else' in src and "T.forEach(function(e){{" in src
    assert "if(!sec){{el.innerHTML=" in src[src.index("function today(T,up)"):]            # created on the first bet only
    assert sdb.live_days(datetime(2026, 9, 30, 9, 0)) == {"2026-09-30"}                   # after 8 AM: last night's gone
    assert sdb.live_days(datetime(2026, 9, 30, 7, 0)) == {"2026-09-30", "2026-09-29"}


def test_board_stays_up_till_1am_or_its_last_game_is_graded():
    """The owner, 9/29: the day's board - Lock of the Day and all, graded with its review - stays up till about 1 AM PT
    (late college football), and past that if a pick is still being played; then it goes to the results."""
    import sports_dashboard as sdb
    from datetime import datetime
    done = [{"date": "2026-09-29", "status": "won"}]
    going = [{"date": "2026-09-29", "status": "open"}]
    assert sdb.board_day(datetime(2026, 9, 29, 23, 30), done) == "2026-09-29"       # 11:30 PM: still up
    assert sdb.board_day(datetime(2026, 9, 30, 0, 40), done) == "2026-09-29"        # 12:40 AM: still up
    assert sdb.board_day(datetime(2026, 9, 30, 1, 5), done) == "2026-09-30"         # 1:05 AM, all graded: cleared
    assert sdb.board_day(datetime(2026, 9, 30, 1, 5), going) == "2026-09-29"        # a late game still going: stays
    assert sdb.board_day(datetime(2026, 9, 30, 9, 0), going) == "2026-09-30"        # the new 8 AM board takes over
    assert "BOARD_CLEAR_HOUR_PT" not in open(sdb.__file__).read()


def test_graded_card_stays_3_hours_then_results():
    """The owner, 9/29: a graded card stays up with its grade + review for about 3 hours, then it's in the results only -
    so once the day's cards are done, the 8 AM note shows early and nobody wonders where the picks went."""
    import sports_dashboard as sdb
    from datetime import datetime, timezone
    now = datetime(2026, 9, 30, 5, 0, tzinfo=timezone.utc)
    assert sdb.still_up({"status": "open"}, now)
    assert sdb.still_up({"status": "won", "settled": "2026-09-30T03:17Z"}, now)        # graded 1h43m ago: up
    assert not sdb.still_up({"status": "lost", "settled": "2026-09-30T01:30Z"}, now)   # 3h30m ago: results only
    assert not sdb.still_up({"status": "won"}, now)                                    # no time kept: long gone
    assert sdb.SHOW_GRADED_H == 3


def test_strengths_by_sport_and_no_puck_or_run_lines():
    """The owner, 9/29: train on the engine's strengths - judged on thousands of games, never one night. Each sport's
    win % is corrected by its real track record; a sport PROVEN weak (200+ picks in each half, below the price and
    losing in both) can't be the Lock / Dog / a leg. And no puck lines or run lines on the board (spreads in football /
    basketball stay)."""
    import sports_strength as ss
    keep = dict(ss._CACHE)
    ss._CACHE["s"] = {"mlb": {"bias": -0.03, "weak": False}, "nhl": {"bias": -0.03, "weak": True}}
    try:
        assert abs(ss.calibrate("mlb", 0.58) - 0.55) < 1e-9                  # overconfident sport: said 58, really 55
        assert ss.calibrate("mlb", 0.50) == 0.50                              # a coin flip isn't moved
        assert ss.calibrate("nfl", 0.58) == 0.58                              # no record: as is
        assert ss.weak("nhl") and not ss.weak("mlb") and not ss.weak("nba")   # (10/3: the NBA always on)
        c = {"league": "nhl", "edge": 0.02, "edge_own": 0.02, "dec": 1.8, "drift": 0.0}
        assert sports.fighting(c) and not sports.fighting({**c, "league": "mlb"})
    finally:
        ss._CACHE.clear(); ss._CACHE.update(keep)
    h = {"old": {"n": 150, "won": 0.54, "price": 0.56, "roi": -0.05}, "new": {"n": 150, "won": 0.53, "price": 0.56, "roi": -0.07}}
    assert not all(x["n"] >= ss.MIN_N for x in h.values())                   # NFL-sized sample: never barred yet
    assert sports.NO_PUCK_RUN_LINES and "no puck lines, no run lines on our board" in open(sports.__file__).read()


def test_parlay_legs_must_earn_it():
    """The owner, 9/29 (don't look like clowns): a parlay only when EVERY leg is lock grade - 56%+ since 9/30 ("we want
    parlays": 57% left three 56% locks with no parlay). Nights nothing clears it: the Lock (+ Dog), and the board says
    why in our lingo."""
    import sports_lingo
    mk = lambda gid, p: {"game_id": f"mlb:{gid}", "league": "mlb", "market": "ml", "side": "home", "team": f"T{gid}",
                         "opp": "X", "odds": -120, "dec": 1.8333, "p": p, "p_market": 0.53, "edge": p * 1.8333 - 1,
                         "edge_own": p * 1.8333 - 1, "reasons": ["the stronger team"], "trap": False, "drift": 0.0}
    weak_legs = [mk(i, 0.545 + i * 0.001) for i in range(1, 6)]
    b = sports.make_board(weak_legs)
    # 9/30, the owner: "we need a two leg, a three leg and a four leg" - the surest plays fill them (52%+, never a
    # coin flip under that, never past -150); the 56%+ legs always go first
    assert b["two"] and b["three"] and b["four"] and all(l["p"] >= sports.PARLAY_FILL_MIN_P for l in b["four"]["legs"])
    assert not sports.make_board([mk(i, 0.51) for i in range(1, 6)])["two"]          # true coin flips: still nothing
    strong = [mk(i, 0.59 + i * 0.002) for i in range(1, 6)]
    b2 = sports.make_board(strong)
    assert b2["two"] and b2["three"] and all(l["p"] >= sports.PARLAY_LEG_MIN_P for l in b2["three"]["legs"])
    assert sports.lean(weak_legs, "two", floor=sports.LEAN_DAY_MIN_P) is None       # a leans-only night: no parlay either
    assert sports.lean(weak_legs, "lock", floor=sports.LEAN_DAY_MIN_P)               # (the Lock lean still goes up)
    assert "we don't force it" in open(sports_lingo.__file__).read()
    assert sports.PARLAY_LEG_MIN_P == 0.56 == sports.LOCK_P, "every parlay leg is lock grade, no higher"
    three_locks = [mk(1, 0.565), mk(2, 0.564), mk(3, 0.561)]          # 9/30's slate: Yankees, Flyers, Padres
    b3 = sports.make_board(three_locks)
    assert b3["two"] and b3["three"], "three lock-grade plays = a 2-leg and a 3-leg"



def test_question_box_gets_exact_pick_status():
    """9/29: the question box read 'Oilers down 5-4' right, then said they'd need two goals to tie. Each pick in the
    data sheet carries its game id + side, and the Worker hands the AI the exact standing (tested in the Worker)."""
    import sports_dashboard as sdb
    b = sdb._leg_brain({"team": "Oilers", "league": "nhl", "market": "spread", "line": -1.5, "game_id": "nhl:1",
                        "side": "home", "odds": -118})
    assert b["game_id"] == "nhl:1" and b["side"] == "home"
    for lg in ("nba", "nhl", "nfl", "mlb"):                                            # every sport: never 'preseason' by guess
        assert sdb._leg_brain({"team": "X", "league": lg, "stype": "2"})["season"] == "regular season"
    js = open("workers/ask/src/index.js").read()
    assert "export function standing(" in js and "never recount the score" in js
    assert sports.SEASON["2"] == "regular season" and '"season": SEASON.get(' in open(sports.__file__).read()
    assert "Never guess it from records" in js                                         # (9/29: 0-0-0 read as preseason)


def test_a_live_play_pings_right_away_and_the_push_carries_its_own_alert():
    """9/29: the Kudermetova alert rang as the Kalinina bet from 90 minutes before (the phone asked the Worker for
    'latest' and got a stale copy) - now each push carries its own text. The owner: pings go right away - a play
    goes up once it holds 2 checks in a row (~2 seconds), never a 15-second wait."""
    import sports_live as L
    L.SEEN.clear()
    P = lambda *ids: [{"id": i} for i in ids]
    t = 1_000_000.0
    assert L.HOLD_S <= 2, "pings right away"
    assert L.hold(P("a"), (), t) == []                               # one check: could be a blip
    assert [p["id"] for p in L.hold(P("a"), (), t + 1)] == ["a"]     # held 2 checks in a row: up + ping
    assert L.hold(P("b"), (), t + 2) == []                           # "a" missed a check...
    assert L.hold(P("a", "b"), (), t + 3) == [{"id": "b"}]           # ...so it starts over; "b" held 2 checks
    assert [p["id"] for p in L.hold(P("a"), ("a",), t + 4)] == ["a"]   # a play that's up stays up
    L.SEEN.clear()
    import sports_dashboard as D
    assert "e.data.json()" in D.SW and "alertNow(e)" in D.SW          # the phone reads the alert out of the push
    js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers", "ask", "src", "push.js")).read()
    assert "encryptPayload" in js and "aes128gcm" in js and "LATEST_MAX_S" in js


def test_live_tennis_never_bets_a_price_that_is_off():
    """9/29 twice: Garcia (-150 at the book, +125 on our line) and Kudermetova (-150 at the owner's book, +100 to +133
    on ours - pinged as LIVE PLUS MONEY). Now: only the MATCH moneyline, two books must agree, and our live read can't
    be more than 8 points off the price. Every tennis play says which book priced it."""
    import sports_tennis as stn
    import sports_tennis_live as stl
    L = sports_live
    L._TUNED.clear()
    # 1) Bovada: a set's moneyline for the same two players never stands in for the match price
    mk = lambda desc, a, b, per: {"description": desc, "status": "O", "period": per, "outcomes": [
        {"description": "Polina Kudermetova", "status": "O", "price": {"american": a}},
        {"description": "Yexin Ma", "status": "O", "price": {"american": b}}]}
    match = {"description": "Match", "main": True, "live": True}
    for set_mk in (mk("Moneyline", "+110", "-140", {"description": "1st Set", "live": True}),
                   mk("1st Set Moneyline", "+110", "-140", {"description": "1st Set", "main": True, "live": True}),
                   mk("Moneyline", "+110", "-140", {"description": "Current Set", "main": False, "live": True})):
        bov = [{"path": [{"description": "WTA Beijing"}], "events": [{"id": "9", "live": True, "startTime": 1790000000000,
                "displayGroups": [{"markets": [mk("Moneyline", "-150", "+120", match), set_mk]}]}]}]
        rows = stn.parse_bovada(bov, live=True)
        assert len(rows) == 1 and (rows[0]["a_ml"], rows[0]["b_ml"]) == (-150, 120), (set_mk, rows)
    # 2) our live read vs the price: 8 points apart at most (the favorite priced like a dog is a bad price)
    m = _tn_live_row("wta:184266", "wta", s1="1", s2="2", n1="Polina Kudermetova", n2="Ma YeXin", done=0)
    pre = {"mkt_p1": 0.62, "model_p1": 0.64}
    p1 = stl.p1_live(m, 0.62)[0]
    for gap, want in ((0.12, False), (0.05, True)):
        q = p1 - gap                                             # the book's no-vig chance for her
        dog = int(round(100 * (1 - q) / q))
        fav = -int(round(100 * (1 - q + 0.02) / (q - 0.02))) if q < 0.5 else -dog - 20
        line = {"a": "Polina Kudermetova", "b": "Yexin Ma", "a_ml": dog, "b_ml": fav, "suspended": False, "src": "betrivers"}
        if abs(p1 - sd.no_vig(line["a_ml"], line["b_ml"])) <= L.TENNIS_MAX_GAP and not want:
            continue                                             # (the test price landed inside the gap: skip)
        got = L.evaluate_tennis(m, line, False, pre, 1, (), set())
        if not want:
            assert got == [], (gap, line, got)
        else:
            assert all(x["src"] == "betrivers" for x in got), got   # the book that priced it rides with the play
    assert L.TENNIS_MAX_GAP <= 0.08
    # 3) two books on the same match: they agree, or neither counts
    a = {"a": "Polina Kudermetova", "b": "Yexin Ma", "a_ml": -150, "b_ml": 120, "src": "bovada"}
    b = {"a": "Polina Kudermetova", "b": "Ma Yexin", "a_ml": 110, "b_ml": -140, "src": "betrivers"}
    assert not L.books_agree(m, [a, b]), "-150 at one book, +110 at the other: neither is trusted"
    assert L.books_agree(m, [a, {**b, "a_ml": -145, "b_ml": 115}])
    assert L.books_agree(m, [b]) and L.books_agree(m, [a, {**b, "stale": True}])
    assert L.TENNIS_BETS[0], "live tennis back on, with the guards"


def test_graded_card_comes_down_on_time_without_a_rebuild():
    """9/29: the Lock (graded 8:17 PM PT) was still up past 11:17 PM - the page only dropped a card when it got rebuilt,
    and the last rebuild was at 11:10. Now each graded card carries its drop time and the page takes it down itself;
    once they're all down, the 8 AM note shows."""
    import sports_dashboard as D
    p = {"kind": "lock", "status": "won", "settled": "2026-09-30T03:17Z"}
    assert D.gone_ms(p) == int(datetime(2026, 9, 30, 6, 17, tzinfo=timezone.utc).timestamp() * 1000)
    assert D.gone_ms({"status": "open"}) is None and D.gone_ms({"status": "won", "settled": None}) is None
    html = D._cards("2026-09-29", [], [("lock", "<section class='pk'>L</section>"), ("two", "<section class='pk'>2</section>")],
                    {"lock": D.gone_ms(p), "two": None})
    assert f'<div class="gn" data-gone="{D.gone_ms(p)}">' in html and html.count('class="gn"') == 1   # open cards stay put
    src = open(D.__file__).read()
    assert "function gone()" in src and "setInterval(gone," in src and 'id="dropnote"' in src


def test_one_ping_per_live_bet_it_stays_up_and_its_note_shows_right_away():
    """9/29: Snigur +135 went up and came right back down, showed with no note, and phones got 'BACK ON' pings for
    bets already sent. Now: one ping per bet (the Worker refuses a repeat), a bet that's up only comes down past the
    old 20-point gap, and the live list carries each bet's note straight from the watcher."""
    import sports_tennis_live as stl
    L = sports_live
    src = open(L.__file__).read()
    assert "notify(pl, back=True)" not in src and 'ref=pl.get("id")' in src
    js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers", "ask", "src", "push.js")).read()
    assert "ref:${ref}" in js
    # a bet that's up: a price 12 points off our read keeps it up (a new bet at that gap never goes up)
    L._TUNED.clear()
    m = _tn_live_row("wta:184263", "wta", s1="3 6 0", s2="6 4 2", n1="Daria Snigur", n2="Kawa", done=2)
    pre = {"mkt_p1": 0.60, "model_p1": 0.62}
    p1 = stl.p1_live(m, 0.60)[0]
    q = p1 - 0.12
    line = {"a": "Daria Snigur", "b": "Kawa", "a_ml": int(round(100 * (1 - q) / q)), "b_ml": -int(round(100 * (1 - q) / q)) - 25,
            "suspended": False, "src": "betrivers"}
    assert L.evaluate_tennis(m, line, False, pre, None, (), set()) == []
    up = L.evaluate_tennis(m, line, False, pre, None, ("tennis:wta:184263:1",), set())
    assert [x["id"] for x in up] == ["tennis:wta:184263:1"], up
    # the live list carries each bet's note
    today = datetime.now(L.PT).date().isoformat()
    log = {"plays": {"tennis:wta:184263:1": {"posted": "2026-09-30T06:26Z", "team": "Daria Snigur", "odds": 135, "league": "tennis",
                                              "tour": "wta", "date": today, "result": None, "score_at_post": "Snigur vs Kawa · 3-6, 6-4, 0-2",
                                              "clock_at_post": "Set 3", "reasons": ["strong", "state"], "tennis": {"sets": [1, 1], "games": [0, 2],
                                              "done": [[3, 6], [6, 4]], "set_no": 3, "side": 1}}}}
    got = L.today_bets(log)
    assert got and got[0]["story"], got
    assert "e.story?" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()


def test_lost_parlay_clock_starts_at_its_first_losing_game():
    """The owner, 9/29: a parlay's 3 hours on the board count from the first game that loses on it - not from when
    the grader got to it, and never from its last game."""
    import sports
    L = sports_live
    tmp = tempfile.mkdtemp()
    keep = (sd.DATA, L.FINAL_AT_PATH, dict(L.FINAL_AT))
    try:
        sd.DATA, L.FINAL_AT_PATH = tmp, os.path.join(tmp, "final_at.json")
        L.FINAL_AT.clear()
        L.mark_final("nhl:1", datetime(2026, 9, 30, 4, 35, tzinfo=timezone.utc))    # the leg that loses ends first
        L.mark_final("nhl:1", datetime(2026, 9, 30, 4, 50, tzinfo=timezone.utc))    # (the first sighting sticks)
        L.mark_final("nhl:2", datetime(2026, 9, 30, 5, 5, tzinfo=timezone.utc))
        g = lambda gid, hs, as_: {"id": gid, "status": "final", "home_score": str(hs), "away_score": str(as_),
                                  "home_name": "H", "away_name": "A", "ls_home": "", "ls_away": ""}
        games = {"nhl:1": g("nhl:1", 5, 6), "nhl:2": g("nhl:2", 4, 2)}
        leg = lambda gid: {"game_id": gid, "market": "ml", "side": "home", "line": None, "dec": 1.8, "result": None}
        pk = {"status": "open", "stake": 100, "legs": [leg("nhl:1"), leg("nhl:2")]}
        sports.grade([pk], games, now=datetime(2026, 9, 30, 5, 14, tzinfo=timezone.utc))
        assert pk["status"] == "lost" and pk["settled"] == "2026-09-30T04:35Z", pk
        assert [l["settled"] for l in pk["legs"]] == ["2026-09-30T04:35Z", "2026-09-30T05:05Z"]
        won = {"status": "open", "stake": 100, "legs": [leg("nhl:2")]}
        sports.grade([won], games, now=datetime(2026, 9, 30, 5, 14, tzinfo=timezone.utc))
        assert won["status"] == "won" and won["settled"] == "2026-09-30T05:05Z"
        none = {"status": "open", "stake": 100, "legs": [leg("nhl:3")]}                  # no watcher time: when graded
        games["nhl:3"] = g("nhl:3", 1, 0)
        sports.grade([none], games, now=datetime(2026, 9, 30, 5, 14, tzinfo=timezone.utc))
        assert none["settled"] == "2026-09-30T05:14Z"
    finally:
        sd.DATA, L.FINAL_AT_PATH = keep[0], keep[1]
        L.FINAL_AT.clear(); L.FINAL_AT.update(keep[2])
        shutil.rmtree(tmp, ignore_errors=True)


def test_live_bet_lines_never_repeat_their_shape_in_a_night():
    """9/29: 'Sticking with Kudermetova till it's done', later 'Sticking with Snigur till it's done', and 'Locked in on
    X. We finna see.' again - machine-like. A night's live bets never share a line's shape (the name doesn't make it
    different), a graded bet's old line stays spoken for, and 'we gon'/finna see' is rare in the pool."""
    import sports_dashboard as D
    import sports_lingo as SL
    names = ["Polina Kudermetova", "Daria Snigur", "Anhelina Kalinina", "Alexander Blockx", "Tommy Paul", "Jiri Lehecka",
             "Iga Swiatek", "Coco Gauff", "Jannik Sinner", "Carlos Alcaraz", "Emma Navarro", "Holger Rune"]
    es = [{"team": n, "league": "tennis", "tour": "wta", "odds": 100 + 7 * k, "posted": f"2026-09-30T0{k % 10}:{10 + k}Z",
           "result": "lost" if k < 3 else None, "tennis": {"side": 1, "sets": [0, 0], "games": [1, 0], "done": [], "set_no": 1},
           "score_at_post": f"{n} vs X · 1-0", "clock_at_post": "Set 1"} for k, n in enumerate(names)]
    st = D.live_stories(es)
    holds = [st[id(e)] for e in es if e["result"] is None]
    shapes = []
    for e, line in zip([e for e in es if e["result"] is None], holds):
        me = __import__("sports_tennis")._say_name(e["team"])
        assert me in line, line
        shapes.append(re.sub(r"\b(finna|gon')\b", "~", line.replace(me, "@")))
    first3 = [" ".join(x.split()[:3]) for x in shapes]
    assert len(set(first3)) == len(first3), shapes                  # every line opens its own way
    assert sum("see" in x for x in shapes) <= 2, shapes             # 'we gon'/finna see' stays rare
    pool = SL.LINES["lv:hold"][2]
    assert len(pool) >= 18 and sum("see" in t for t in pool) <= 2
    for t in pool:
        assert not any(w in t.lower() for w in ("real talk", "chalk"))


def test_live_tennis_shows_who_is_serving_and_the_points():
    """The owner, 9/29: always show who's serving, and 15-0 / 30-0 if it's accurate. The book (BetRivers) posts every
    point, who's serving and the games per set - lined up to our player's side, never guessed."""
    import sports_books as sb
    L = sports_live
    ev = lambda home, away, h, a, pts, hs: {"event": {"homeName": home, "awayName": away}, "liveData": {
        "score": {"home": pts[0], "away": pts[1]}, "statistics": {"sets": {"home": h, "away": a, "homeServe": hs}}}}
    lv = sb.kambi_live(ev("Yexin Ma", "Polina Kudermetova", [7, 3, 0], [6, 6, 0], ("30", "15"), False))
    assert lv == {"home": "Yexin Ma", "sets": [[7, 6], [3, 6], [0, 0]], "pts": ["30", "15"], "home_serves": False}
    assert sb.kambi_live({"liveData": {}}) is None
    m = _tn_live_row("wta:184266", "wta", s1="6 6", s2="7 3", n1="Polina Kudermetova", n2="Ma YeXin", done=1)
    m["bo"] = 3
    ln = {"a": "Yexin Ma", "b": "Polina Kudermetova", "start": m["start"], "tour": "wta", "live": lv, "src": "betrivers"}
    for side in (None, 1, 2):                                   # our player first, whichever side she's on
        base = L._tennis_score(m, side)
        bk = L.book_score(m, ln, base)
        kud_first = base["n"][0] == "Kudermetova"
        assert bk and bk["n"] == base["n"], (side, bk)
        assert bk["sets"] == ([[6, 7], [6, 3], [0, 0]] if kud_first else [[7, 6], [3, 6], [0, 0]]), bk
        assert bk["pts"] == (["15", "30"] if kud_first else ["30", "15"])
        assert bk["srv"] == (0 if kud_first else 1), "Kudermetova's serving (the book: home doesn't serve)"
        assert bk["done"] == 2
    # a set list padded with unplayed 0-0 sets: trimmed to the one being played
    lv2 = {**lv, "sets": [[3, 1], [0, 0], [0, 0]]}
    assert L.book_score(m, {**ln, "live": lv2}, L._tennis_score(m, 1))["sets"] == [[1, 3]]
    # names that don't line up: no score at all (never a guess)
    assert L.book_score(m, {**ln, "a": "Some One", "b": "Else Who", "live": {**lv, "home": "Some One"}}, L._tennis_score(m, 1)) is None
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert 'wg===fg&&w.pts&&!f.pts&&w.src==="book"' in src


def test_question_box_checked_hourly_and_retries_lean():
    """9/29: the question box fell back to 'the AI's taking a breather' on a live-bet question and nobody knew why.
    The hourly bug check asks it a real question now; the Worker retries once without the web tools, says why when
    it can't answer, and knows tonight's live bets (the price we took) for 'what odds on Bai?'."""
    here = os.path.dirname(os.path.abspath(__file__))
    h = open(os.path.join(here, "tools", "health.py")).read()
    assert "question box" in h and "HTTPError" in h
    js = open(os.path.join(here, "workers", "ask", "src", "index.js")).read()
    assert "retry lean" in js and "why:" in js and "tonight's live bets we're in" in js and "Date.now() - t0 > 45000" in js


def test_live_plus_money_record_is_by_sport_behind_a_tap():
    """The owner, 9/29: live plus money by sport, never one lumped number, without cluttering the results - the box
    says 'Tap for full results', then each sport's record, then tap a sport for every bet in it."""
    import sports_dashboard as D
    es = [{"league": "nfl", "result": "won"}, {"league": "nfl", "result": "lost"}, {"league": "nfl", "result": "won"},
          {"league": "tennis", "tour": "wta", "result": "lost"}, {"league": "tennis", "tour": "atp", "result": None}]
    h = D._live_by_sport(es)
    assert "🏈 NFL" in h and "<b>2-1</b>" in h and "67%" in h and "Women&#x27;s Tennis" in h and "<b>0-1</b>" in h
    assert "Men's Tennis" not in h                                   # (still going: not a result yet)
    assert h.index("NFL") < h.index("Women&#x27;s Tennis")           # busiest sport first
    assert 'data-hs="📡 🏈 NFL"' in h and 'class="tap"' in h
    assert D._live_by_sport([]) == ""
    src = open(D.__file__).read()
    assert "Tap a sport to see full results" in src and "lvbox" in src and 'box(f"📡 {k}"' in src
    assert 'grade("📡 LIVE PLUS MONEY"' in src and "by_sport=_live_by_sport(lrs)" in src


def test_tennis_points_and_server_checked_every_second():
    """The owner, 9/29: the 15-30-40 and who's serving must be right to the second, with a constant check. The watcher
    flags a live match that's gone a minute without them; the hourly bug check reads that, and asks the page's
    1-second score route for the book's points."""
    L = sports_live
    keep = dict(L.SCORES)
    try:
        L.SCORES.clear(); L.NO_PTS.clear(); L.PTS_SEEN.clear()
        L.SCORES["tennis:wta:1"] = {"tennis": True, "live": True, "n": ["Bai", "Fruhvirtova"], "sets": [[2, 6]], "pts": None, "srv": None}
        L.SCORES["tennis:wta:2"] = {"tennis": True, "live": True, "n": ["Sonmez", "Inglis"], "sets": [[4, 6]], "pts": ["0", "30"], "srv": 1}
        assert L.tennis_score_check(1000.0) == []                       # just noticed: give it a minute
        got = L.tennis_score_check(1061.0)
        assert got == ["tennis Bai vs Fruhvirtova: no points for 61s"], got
        L.SCORES["tennis:wta:1"].update(pts=["15", "0"], srv=0)
        assert L.tennis_score_check(1062.0) == [] and "tennis:wta:1" not in L.NO_PTS
        # "0-15 sitting there forever": the same point score for 3 minutes is flagged frozen
        got = L.tennis_score_check(1062.0 + L.PTS_FROZEN_S)
        assert any("Bai vs Fruhvirtova: points frozen at 15-0" in x for x in got), got
        L.SCORES["tennis:wta:1"].update(pts=["30", "0"])
        assert not any("Bai" in x for x in L.tennis_score_check(1063.0 + L.PTS_FROZEN_S))
    finally:
        L.SCORES.clear(); L.SCORES.update(keep); L.NO_PTS.clear()
    h = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "health.py")).read()
    assert "live tennis points" in h and "/scores?debug=1" in h
    js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers", "ask", "src", "scores.js")).read()
    assert "bookScore" in js and "kambi" in js.lower()


def test_closing_line_counts_each_real_bet_once():
    """9/30 nightly review: the closing-line number counted a leg once per card (the Vikings -115 four times: 25 legs
    were really 14 bets). Each real bet counts once now; and the review rules say women's TENNIS is on (only women's
    team leagues are out) and the board posts 8 AM game day."""
    import sports_moves as M
    leg = lambda gid, odds: {"game_id": gid, "market": "ml", "side": "home", "odds": odds, "league": "nfl", "team": "X"}
    picks = [{"date": "d", "kind": k, "legs": [leg("nfl:1", -115)]} for k in ("lock", "two", "three", "four")] + \
            [{"date": "d", "kind": "dog", "legs": [leg("nfl:2", 130)]}]
    games = {"nfl:1": {"league": "nfl", "status": "final", "ml_home": "-125", "ml_away": "105"},
             "nfl:2": {"league": "nfl", "status": "final", "ml_home": "140", "ml_away": "-160"}}
    r = M.clv(picks, games)
    assert r["summary"]["all"]["beat"] == 0.8 and r["summary"]["all"]["per_bet"] == {"bets": 2, "avg_cents": 0.0, "beat": 0.5}
    assert any("counting each real bet once: beat the closing line 50% of 2 bets" in x for x in M.clv_summary(res=r))
    rules = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SPORTS_REVIEW.md")).read()
    assert "men's AND women's" in rules and "8 AM PT on game day" in rules and "6pm PT the night before" not in rules


def test_graded_live_bet_clears_into_the_results_right_away():
    """The owner, 9/30: a live bet clears out of TONIGHT'S LIVE BETS the second it's graded - it's in THE RESULTS under
    its sport, with its review. Only bets still going show; none going, no blue box."""
    import sports_dashboard as D
    src = open(D.__file__).read()
    assert 'if e.get("result") is None), key=lambda e: e["posted"]' in src
    assert "if(e.result||on[e.pid]){{if(have)have.remove();return}}" in src and 'if(s2&&!s2.querySelector(".leg"))el.innerHTML=""' in src
    assert "clears into the results" in open(os.path.join(os.path.dirname(D.__file__), "CLAUDE.md")).read()


def test_results_show_reviews_without_a_tap_and_tennis_gets_tennis_words():
    """The owner, 9/30: the reviews show right under each result - no tap. And a live tennis bet's review talks tennis
    ('never got the stops we needed' is football). No 'Get in.' after a result - that's what you say before a bet."""
    import sports_dashboard as D
    import sports_lingo as SL
    src = open(D.__file__).read()
    assert '<div class="hx hxo {x[1]}"><div class="hr {x[1]}">{head}</div>' in src and "<summary class=\"hr" not in src
    assert '"tlive_up" if ahead else "tlive_back"' in src
    for k in ("tlive_back", "tlive_up"):
        for r in ("won", "lost"):
            for t in SL.REVIEWS[(k, r)][2]:
                assert not re.search(r"\b(stops|drive|quarter|inning|period|touchdown|goal)\b", t), t
    assert "Get in." not in SL.PAL["wk"]


def test_what_counts_says_all_locks():
    """The owner, 9/30: 'what counts' said 'the Lock of the Day' - it's every lock (the Lock of the Day is one). 10/1
    audit: it also said leans keep their own record - they COUNT in ours (marked 🟡) - and 'what counts' is a NEVER
    phrase. The leans box sits with our records, never under 'not in our record'."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert "<b>💰 Unit plays:</b> the good bets we actually put money on — every Lock, Dog of the Day, value play and early play" in src
    assert "<b>🟡 Leans:</b> no units, just our lean" in src                                        # (10/2: no overall)
    assert "What counts" not in src and "leans (own record, not ours)" not in src
    i = src.index("# their own categories, never in our record")
    assert 'TIER_LOOK["lean"]' not in src[i:i + 900]


def test_slate_check_before_the_board():
    """The owner, 9/30: before the 8 AM picks, a checker makes sure nothing's missed and nothing's broken (9/29: a
    'TBD' playoff placeholder hid White Sox @ Astros). Every real game today: both teams named, a price, looked at by
    the engine; data pulls OK. A problem holds the opening board (the engine re-pulls at 8:12 / 8:32); from 8:30 it
    posts what checks out and the bug check flags the rest."""
    import sports
    tmp = tempfile.mkdtemp()
    keep = sports.SLATE_PATH
    try:
        sports.SLATE_PATH = os.path.join(tmp, "slate.json")
        day = datetime(2026, 9, 30).date()
        now = datetime(2026, 9, 30, 15, 2, tzinfo=timezone.utc)
        g = lambda gid, a, h, mh="-150", ma="130": {"id": gid, "league": "mlb", "stype": "3", "status": "pre",
                                                    "start": "2026-09-30T23:00Z", "away_name": a, "home_name": h,
                                                    "ml_home": mh, "ml_away": ma}
        games = {"mlb:1": g("mlb:1", "Yankees", "Red Sox"), "mlb:2": g("mlb:2", "White Sox", "TBD"),
                 "mlb:3": {**g("mlb:3", "Cubs", "Padres", mh=""), "stype": "2"}, "mlb:4": g("mlb:4", "Mets", "Braves")}
        #   (an unpriced REGULAR-season game holds the board; an unpriced playoff game is likely an "if necessary" one
        #    that won't be played - logged, not held: 10/1 audit)
        cands = [{"game_id": "mlb:1"}]
        probs = sports.slate_check(games, cands, day, now, errors=["odds: Action Network HTTP 503"])
        txt = " | ".join(probs)
        assert "White Sox @ TBD (MLB): a team isn't named yet" in txt
        assert "Cubs @ Padres (MLB): no price from the books" in txt
        assert "Mets @ Braves (MLB): priced but the engine never looked at it" in txt
        assert "data pull failed: odds: Action Network HTTP 503" in txt and "Yankees" not in txt
        saved = json.load(open(sports.SLATE_PATH))
        assert saved["games"] == 4 and saved["looked_at"] == 1 and len(saved["problems"]) == 4
        assert sports.slate_check({"mlb:1": games["mlb:1"]}, cands, day, now, errors=[]) == []
    finally:
        sports.SLATE_PATH = keep
        shutil.rmtree(tmp, ignore_errors=True)
    src = open(sports.__file__).read()
    assert "if probs and (local.hour, local.minute) < SLATE_LAST_TRY:" in src and "preflight(games, model, now)" in src
    assert "slate check:" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "health.py")).read()


def test_proven_value_dogs():
    """The owner, 9/30: 'we want value plays - underdogs win every day'. The value-dog machinery stays (a league goes in
    VALUE_DOG only once it passes the honest exam at the prices the board really posts at); the 9/30 night exam found
    the engine's dog edge only at the MORNING price, so none qualify at 8 AM. Never longer than +280."""
    assert sports.VALUE_DOG == {} and sports.VALUE_DOG_MAX == 280, \
        "9/30 honest exam: the dog edge is only at the MORNING price - nothing qualifies at the 8 AM board's prices"
    src = open(sports.__file__).read()
    assert "100 <= odds <= VALUE_DOG_MAX and vd[0] <= p_own - p_mk < vd[1]" in src and "p = max(p, p_mk + vd[2])" in src
    dog = {"game_id": "nhl:1", "league": "nhl", "market": "ml", "side": "away", "odds": 150, "dec": 2.5, "p": 0.42,
           "edge": 0.42 * 2.5 - 1, "edge_own": 0.52 * 2.5 - 1, "trap": False, "drift": 0.0,
           "reasons": ["proven value dog: our read 10+ pts over the price - these won more than the book said, 3+ seasons"]}
    assert sports.proven(dog) and sports.good(dog), "a proven value dog is a real play"


def test_explorer_underdog_lane():
    """The owner, 9/30: 'we gotta find a way for the engine to pick out these underdogs'. Every explorer run tests up
    to DOG_BATCH never-tested MONEYLINE angles on a dog FIRST (then the regular batch) - same strict proof (300+ bets,
    money in both halves, z 3.5+, then 100+ forward games) - so underdog angles aren't stuck at the back of the line."""
    import sports_explorer as X
    assert X.DOG_BATCH >= 3000 and "dog" in X.DOG_ATOMS and "p:25-40" in X.DOG_ATOMS
    src = open(X.__file__).read()
    assert 'if out_ == "ml")' in src and "if not any(a in DOG_ATOMS for a in atoms):" in src
    assert '"dog_angles": dogs' in src and "tested >= batch + dogs" in src
    games = {}
    import random as _r
    rng = _r.Random(3)
    for k in range(700):                                      # a toy NBA season: the dog lane tests dog angles only
        hp = rng.choice([-250, -180, -130, 120, 160, 210])
        games[f"nba:{k}"] = {"id": f"nba:{k}", "league": "nba", "start": f"2025-{1 + k // 60:02d}-{1 + k % 28:02d}T0{k % 10}:00Z",
                             "status": "final", "home": str(k % 17), "away": str((k * 7 + 3) % 17), "home_name": f"H{k % 17}",
                             "away_name": f"A{(k * 7 + 3) % 17}", "home_score": str(100 + rng.randint(-12, 12)),
                             "away_score": str(100), "ml_home": str(hp), "ml_away": str(-hp if abs(hp) >= 120 else 110),
                             "stype": "2", "neutral": "0"}
    tmp = tempfile.mkdtemp()
    r = X.explore(games, os.path.join(tmp, "x.json"), batch=0, leagues=("nba",), verbose=False, dog_batch=40)
    assert r["dog_angles"] == len(X.LAST_TESTED) and all("|ml|" in k and any(a in k for a in X.DOG_ATOMS) for k in X.LAST_TESTED)
    shutil.rmtree(tmp, ignore_errors=True)


def test_final_score_calls_the_pick_on_the_spot():
    """The owner, 9/29: tennis showed FINAL but no grade (the official grade waits for the engine run + page rebuild).
    The second a game's final, the card calls it from the final score - HIT / MISS / PUSH, moneyline, spread (win by
    enough / inside the number) or tennis sets - and the official grade + review follow."""
    import sports_dashboard as sdb
    leg = {"team": "Oilers", "opp": "Canucks", "league": "nhl", "side": "home", "home": True, "market": "spread",
           "line": -1.5, "odds": -118, "start": "2026-09-30T02:00Z", "game_id": "nhl:1", "reasons": []}
    h = sdb._leg(leg, tagged=True)
    assert 'data-side="home" data-mk="spread" data-line="-1.5"' in h
    src = open(sdb.__file__).read()
    assert "function called(s,sc)" in src and "(called(s,sc)||" in src
    assert 'data-mk="{E(l.get("market") or "ml")}"' in src                              # tennis legs too


def test_early_value_plays():
    """⏰ Early value plays (the owner, 9/30: get it before the line moves): a +100..+280 dog in a sport that passed the
    early-price exam, the engine's own read in a passed band over the price, the money not already on it -> posted
    once, pinged once (plus the one-time breakthrough ping), graded at the posted price. Nothing while it's off."""
    import sports_early as se
    d = tempfile.mkdtemp()
    se.PATH, se.EXAM_PATH = os.path.join(d, "early.json"), os.path.join(d, "early_exam.json")
    now = datetime(2026, 10, 1, 18, 0, tzinfo=timezone.utc)

    class Elo:
        def features(self, g):
            return {"known": 10}
    saved = (sm.ratings, sm.own_p, sm.market_p, se.recent_params, se.ON)
    sm.ratings = lambda games, model: {lg: Elo() for lg in sd.LEAGUES}
    sm.own_p = lambda params, f: 0.40                       # the engine: the home dog wins 40%
    sm.market_p = lambda g, open_line=False: 0.34           # the price: 34% (+6 pts: the +4..8 band)
    se.recent_params = lambda games, now=None, leagues=None: {"nfl": {"w": [0], "k": 1, "hfa": 0}}
    try:
        def game(i, ml, ml_open, lg="nfl", hours=48):
            return {"id": i, "league": lg, "status": "pre", "stype": "2", "home": f"h{i}", "away": f"a{i}",
                    "home_name": f"Home {i}", "away_name": f"Away {i}", "ml_home": str(ml), "ml_away": "-220",
                    "ml_home_open": str(ml_open), "ml_away_open": "-220",
                    "start": (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%MZ")}
        games = {"1": game("1", 185, 190),                  # a live one: +185, barely moved from the open
                 "2": game("2", 150, 185),                  # the money already moved it 35 cents: value's gone
                 "3": game("3", 320, 320),                  # past +280
                 "4": game("4", 185, 185, lg="mlb"),        # a sport that hasn't passed the exam
                 "5": game("5", 185, 185, hours=1)}         # starts too soon
        with open(se.EXAM_PATH, "w") as f:
            json.dump({"leagues": {"nfl": {"passed": [[0.04, 0.08]]}, "mlb": {"passed": []}}}, f)
        pings = []
        se.ON = False
        assert se.post(games, {"params": {}}, now, ping=pings.append) == [] and not pings   # off = nothing
        se.ON = True
        quiet = {k: v for k, v in games.items() if k != "1"}         # nothing qualifies: no breakthrough ping yet
        assert se.post(quiet, {"params": {}}, now, ping=pings.append, lines=lambda lg: []) == [] and not pings
        new = se.post(games, {"params": {}}, now, ping=pings.append, lines=lambda lg: [])
        assert [c["game_id"] for c in new] == ["1"] and new[0]["odds"] == 185, new
        assert pings[0] is None and pings[1]["game_id"] == "1"        # the breakthrough ping first, then the play
        assert se.post(games, {"params": {}}, now, ping=pings.append, lines=lambda lg: []) == [] and len(pings) == 2
        saved_un = sd.team_unsure                                     # the owner, 9/30: a questionable star on
        sd.team_unsure = lambda inj, tid, name, lg, maybe=False: [("Star", "PG", "Questionable")]   # our side = no early play
        try:
            games["6"] = game("6", 185, 190)
            assert se.scan(games, {"params": {}}, now, injuries={"nfl": {"x": []}}) == []
        finally:
            sd.team_unsure = saved_un
            del games["6"]
        sm.market_p = lambda g, open_line=False: 0.30                 # +10 pts: outside the only band that passed
        assert se.scan(games, {"params": {}}, now) == []
        games["1"].update(status="final", home_score="24", away_score="20")
        se.post(games, {"params": {}}, now, lines=lambda lg: [])
        st = se.load()
        assert st["picks"][0]["result"] == "won" and se.record(st) == {"won": 1, "lost": 0, "units": 1.85}
        assert "Get it before the line moves" in se.ping_text(st["picks"][0])[1]
        assert se.ping_text(None) == ("🚨 MAJOR ENGINE BREAKTHROUGH", "We just found an edge on underdogs: get in early "
                                      "before the line moves. 🔥 Most plays start next week.")
        assert len(se.ping_text(None)[1]) <= 150                       # fits a lock screen without getting cut
        assert "✅" not in se.html(st, lambda x: x) and "Last graded" not in se.html(st, lambda x: x)   # no grading here
        st["picks"].append({**st["picks"][0], "game_id": "9", "result": None, "team": "Soon Team",
                            "start": (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%MZ")})
        st["picks"].append({**st["picks"][0], "game_id": "8", "result": None, "team": "Today Team",
                            "start": (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%MZ")})
        h = se.html(st, lambda x: x, now)
        assert "EARLY VALUE PLAYS" in h and "Soon Team" in h and "game starts at" in h
        assert "Today Team" not in h                  # game day: no longer an early play, it leaves the box
    finally:
        sm.ratings, sm.own_p, sm.market_p, se.recent_params, se.ON = saved
    was, se.ON = se.ON, False
    assert se.html({"picks": [{"x": 1}]}, lambda x: x) == ""          # off: no box on the page
    se.ON = was


def test_early_exam_pass_rule():
    """A band only goes live if it made +2% in EACH of the two exam seasons on 60+ dogs (20+ a season)."""
    import sports_early as se
    ok = lambda n1, r1, n2, r2: n1 + n2 >= se.PASS_N and min(n1, n2) >= se.PASS_SEASON_N and min(r1, r2) >= se.PASS_ROI
    assert ok(29, 0.33, 33, 0.08)                    # the NFL +4..8 on 9/30
    assert not ok(27, 0.11, 24, 0.14)                # college football: +11% / +14% but only 51 dogs (yet)
    assert not ok(205, 0.003, 207, 0.03)             # NBA +8: one flat season
    assert se.passed(os.path.join(tempfile.mkdtemp(), "none.json")) == se.EARLY == {}   # no exam yet: nothing posts


def test_early_exam_grades_only_bettable_prices():
    """10/1 data audit: the NFL's "open" is often the summer look-ahead line (Ravens opened -250, closed +265) - a price
    nobody can bet a week out. Grading the engine's read at it made NFL early dogs look +57% (and -23% on the rest).
    The exam now skips a dog whose price ran MOVED_MAX+ cents toward it - the same dogs the live scan would skip."""
    import sports_early as se
    assert se.bettable(150, 150) and se.bettable(150, 140) and se.bettable(150, 190)   # moved away: still bettable
    assert not se.bettable(205, -320) and not se.bettable(160, 140)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_early.py")).read()
    assert 'if price == "early" and not bettable(o, c):' in src


def test_no_thin_or_dull_text():
    """The owner (9/30): no dull gray, no thin text, no colored moneylines - text is bold white (accents stay in color:
    headers, times, LIVE, percentages). A lost pick in the results stays white too (it was pink)."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert not re.findall(r"font-weight:[1-6]00\b", src), re.findall(r".{40}font-weight:[1-6]00", src)[:3]
    assert "#ffb4b4" not in src and ".hr.lost .hp{{color:#fff}}" in src
    for cls in (".foot{{", ".nut{{", ".bs{{", ".ask-n{{", ".sp-n.what{{", ".evr em{{", ".ask-a{{"):   # (question box answers too)
        rule = src[src.index(cls):src.index("}}", src.index(cls))]
        assert "color:#fff" in rule or cls in (".nut{{",), (cls, rule)


def test_reviews_are_yellow():
    """The owner (9/30): the pre-game and after-game reviews both come through in bold yellow (on the cards and in the
    results); every other piece of text stays bold white."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert ".why.rvy{{color:#ffc233}}" in src and "font-weight:700;color:#ffc233}}" in src[src.index(".hrv{{"):][:120]
    assert src.count('class="why rvy"') >= 3        # the main card's write-up + review, the tennis card's


def test_we_got_in_early_box():
    """🎯 On game day the early plays move onto Today's Board in ONE box, one row each: the price we got -> now.
    Came our way = 'we beat the line'; got bigger and the engine still likes it = 'better price now', else 'money went
    against it'; no move = no label. A graded row stays 3 hours (the board's rule), then it's gone."""
    import sports_early as se
    saved = (se.ON, se.passed)
    se.ON, se.passed = True, lambda path=None: {"nfl": [(0.04, 0.08)]}
    try:
        now = datetime(2026, 10, 4, 17, 0, tzinfo=timezone.utc)                  # Sunday 10 AM PT
        start = (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%MZ")
        pk = lambda i, odds, own: {"game_id": i, "league": "nfl", "side": "home", "team": f"Team{i}", "opp": "Opp",
                                   "odds": odds, "opp_odds": -220, "own": own, "start": start, "result": None}
        st = {"picks": [pk("a", 185, 0.40), pk("b", 185, 0.45), pk("c", 185, 0.33), pk("d", 185, 0.40)]}
        games = {"a": {"status": "pre", "ml_home": "-120"}, "b": {"status": "pre", "ml_home": "220"},
                 "c": {"status": "pre", "ml_home": "220"}, "d": {"status": "pre", "ml_home": "185"}}
        h = se.gameday_html(st, games, lambda x: x, now)
        assert h.count('class="egr"') == 4 and "WE GOT IN EARLY" in h and "still good" not in h
        rows = h.split('class="egr"')[1:]
        assert "we beat the line" in rows[0] and "-120" in rows[0]
        assert "The engine has them at" not in rows[0]        # the owner, 9/30: a win % only shows over 55%
        assert "better price now" in rows[1]                  # +220: 45% vs ~30% on the price - still value
        assert "money went against it" in rows[2]             # +220 and the engine's 33% (vs ~31% on the price) isn't enough now
        assert "<i>" not in rows[3]                           # no move, no label
        st["picks"][0].update(result="won", graded_at=(now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%MZ"))
        assert "✅" in se.gameday_html(st, games, lambda x: x, now)
        st["picks"][0]["graded_at"] = (now - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%MZ")
        assert "Teama" not in se.gameday_html(st, games, lambda x: x, now)     # 3 hours up: gone
        # the owner, 9/30: our starting QB ruled out after we posted -> the price blows up; never "better price now"
        games["b"].update(home="1", home_name="Teamb")
        saved_ko = sd.team_key_out
        sd.team_key_out = lambda inj, tid, name, lg, maybe=False: [("Lamar Jackson", "QB", "Out")] if name == "Teamb" else []
        try:
            st["picks"][1]["out_at_post"] = []                 # nobody out when it posted
            st["picks"][2]["out_at_post"] = ["Lamar Jackson"]  # already out when it posted: priced in, not news
            games["c"].update(home="2", home_name="Teamb")
            se.watch(st, games, {"nfl": {"x": []}})
            assert st["picks"][2]["key_out"] is None
        finally:
            sd.team_key_out = saved_ko
        row = se.gameday_html(st, games, lambda x: x, now).split('class="egr"')[1]
        assert "Lamar Jackson out - don't chase it" in row and "better price now" not in row, row
        assert "ruled out since we posted" in se.html(st, lambda x: x, now - timedelta(days=2))
        se.ON = False
        assert se.gameday_html(st, games, lambda x: x, now) == ""
    finally:
        se.ON, se.passed = saved


def test_roster_keeps_every_player():
    """The owner (9/30): the engine has to know every player - stars, bench, backups - in every sport. The roster
    collector keeps EVERYBODY from ESPN's box score (not just the starting QB / pitcher / goalie), skips guys who
    didn't play, and never breaks on a shape it doesn't know."""
    import sports_roster as sr
    d = tempfile.mkdtemp()
    saved = sr.DIR
    sr.DIR = d
    try:
        payload = {"boxscore": {"players": [
            {"team": {"id": "7"}, "statistics": [{"name": "", "keys": ["minutes", "points", "rebounds", "assists", "plusMinus"],
             "athletes": [
                 {"athlete": {"id": "1", "displayName": "Star Guy", "position": {"abbreviation": "PG"}}, "starter": True,
                  "stats": ["36", "31", "5", "9", "+12"]},
                 {"athlete": {"id": "2", "displayName": "Bench Guy", "position": {"abbreviation": "F"}}, "starter": False,
                  "stats": ["14", "6", "3", "1", "-4"]},
                 {"athlete": {"id": "3", "displayName": "Sat Out"}, "didNotPlay": True, "stats": []}]}]},
            {"team": {"id": "9"}, "statistics": [{"name": "weird", "keys": ["whatever"], "athletes": [
                {"athlete": {"id": "4", "displayName": "Odd"}, "stats": ["1"]}]}]}]}}
        rows = sr.parse("nba", "nba:1", "2026-01-05T00:00Z", payload)
        assert [r["player"] for r in rows] == ["Star Guy", "Bench Guy"]           # the DNP and unknown stats skipped
        assert rows[0]["starter"] == "1" and json.loads(rows[0]["stats"])["points"] == "31"
        assert sr.parse("nba", "x", "2026-01-05T00:00Z", {}) == [] and sr.parse("nba", "x", "", {"boxscore": None}) == []
        sr.add("nba", rows)
        sr.add("nba", rows)                                                        # twice: no doubles
        assert len(sr.load("nba")) == 2 and sr.have_ids("nba") == {"nba:1"}
        assert os.path.exists(os.path.join(d, "nba_2025.csv.gz"))                 # a Jan game = the 2025-26 season
        assert sr.volume("nba", {"minutes": "36"}) == 36 and sr.volume("nhl", {"timeOnIce": "18:30"}) == 18.5
        # a box score in a shape we can't read is retried later, never written off as "no box score" for good
        import urllib.request as ur
        saved_open = ur.urlopen
        class R(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        ur.urlopen = lambda req, timeout=0: R(json.dumps({"boxscore": {"players": [{"team": {"id": "1"},
                                                          "statistics": [{"keys": ["?"], "athletes": []}]}]}}).encode())
        try:
            assert sr.fetch("nba", "nba:9", "2026-01-05T00:00Z") is None
        finally:
            ur.urlopen = saved_open
    finally:
        sr.DIR = saved


def test_football_lines_loaded_a_week_early():
    """The owner (9/30): 'college football is Friday and Saturday - we couldn't get no good early lines?' The engine
    only looked 2 days ahead, so Saturday's / Sunday's lines never loaded till Thursday. Football looks 8 days out."""
    assert sd.days_ahead("ncaaf") >= 7 and sd.days_ahead("nfl") >= 7 and sd.days_ahead("nhl") >= 3
    import sports_early as se
    assert se.AHEAD_D >= sd.days_ahead("nfl")          # the early scan looks at least as far as the lines are loaded


def test_early_lines_from_a_book_before_espn():
    """The owner (9/30): 'as soon as the lines come out we need to see them - some books have lines before others.'
    A book's line fills a game ESPN hasn't priced yet, and the FIRST line any book showed stays that game's open."""
    import sports_early as se
    saved = se.passed
    se.passed = lambda path=None: {"ncaaf": [(0.04, 1)]}
    try:
        now = datetime(2026, 9, 28, 18, 0, tzinfo=timezone.utc)
        games = {"g1": {"league": "ncaaf", "status": "pre", "start": "2026-10-03T19:30Z", "home_name": "Penn State",
                        "away_name": "Northwestern", "ml_home": "", "ml_away": ""}}
        rows = [{"home": "Penn State Nittany Lions", "away": "Northwestern Wildcats", "ml_home": -280, "ml_away": 225,
                 "start": "2026-10-03T19:30:00Z", "src": "betrivers"}]
        st = {"picks": []}
        g = se.with_book_lines(games, st, now, lambda lg: rows)["g1"]
        assert g["ml_away"] == "225" and g["ml_away_open"] == "225" and games["g1"]["ml_away"] == ""   # a copy
        rows[0].update(ml_home=-140, ml_away=120)                   # the money came in on Northwestern
        games["g1"].update(ml_home="-140", ml_away="120")           # ...and ESPN's priced it now
        g = se.with_book_lines(games, st, now, lambda lg: rows)["g1"]
        assert g["ml_away"] == "120" and g["ml_away_open"] == "225"  # the open stays the first line we ever saw
        assert se.moved_toward(int(g["ml_away_open"]), int(g["ml_away"])) == 105      # value already taken
        import sports_books as sbk                                  # BetRivers' own shape -> the rows above
        data = {"events": [
            {"event": {"id": 1, "state": "NOT_STARTED", "homeName": "Penn State Nittany Lions",
                       "awayName": "Northwestern Wildcats", "start": "2026-10-03T19:30:00Z"},
             "betOffers": [{"criterion": {"englishLabel": "Moneyline"}, "betOfferType": {"englishName": "Match"},
                            "outcomes": [{"participant": "Penn State Nittany Lions", "oddsAmerican": "-280", "status": "OPEN"},
                                         {"participant": "Northwestern Wildcats", "oddsAmerican": "+225", "status": "OPEN"}]}]},
            {"event": {"id": 2, "state": "STARTED", "homeName": "A", "awayName": "B"}, "betOffers": []},
            {"event": {"id": 3, "state": "NOT_STARTED", "homeName": "C", "awayName": "D"}, "betOffers": []}]}
        miss = []
        got = sbk.kambi_pregame(data, miss)
        assert got == [{"home": "Penn State Nittany Lions", "away": "Northwestern Wildcats", "ml_home": -280,
                        "ml_away": 225, "start": "2026-10-03T19:30:00Z", "src": "betrivers"}] and miss == [3]
        def boom(lg):
            raise OSError("book down")
        assert se.with_book_lines(games, st, now, boom)["g1"] is games["g1"]            # a book down: no crash
    finally:
        se.passed = saved


def test_early_pings_wait_for_the_dashboard():
    """The owner (9/30): 'they get the notification, then they look' - an early play's ping (and the one-time
    breakthrough ping with it) goes out only once the LIVE dashboard's Early Value Plays box shows the play; a past
    run's queue never goes out twice."""
    import sports_early as se
    path = os.path.join(tempfile.mkdtemp(), "pings.json")
    now = datetime(2026, 10, 4, 3, 30, tzinfo=timezone.utc)
    play = {"game_id": "g", "team": "Browns", "odds": 185, "opp": "Steelers", "start": "2026-10-05T17:00Z"}
    se.queue_pings([None, play], now, path)
    sent = []
    assert se.pending(now, path) == [None, play]
    assert se.send_queued("<html>no box yet</html>", now, path, sent.append) == [] and not sent
    assert se.send_queued("<b>Browns</b> on the main board, EARLY box not up", now, path, sent.append) == []
    live = "<section>EARLY VALUE PLAYS ... <b>Browns</b> ML +185</section>"
    assert se.send_queued(live, now, path, sent.append) == [None, play] and sent == [None, play]   # breakthrough first
    sent.clear()
    assert se.send_queued(live, now + timedelta(hours=1), path, sent.append) == [] and not sent   # stale: never again
    se.queue_pings([], now, path)
    assert se.pending(now, path) == []


def test_early_short_dog_bands_and_pitcher_swap():
    """9/30: short dogs (+100..+149) at +8..12 pts passed with who's pitching / in net - a band carries its own price
    range. Baseball only posts with both starters announced; our pitcher swapped after we posted -> don't chase it."""
    import sports_early as se
    assert se.band([0.04, 0.08]) == (0.04, 0.08, 100, 280) and se.band((0.08, 0.12, 100, 149)) == (0.08, 0.12, 100, 149)
    assert se.band_name((0.08, 0.12, 100, 149)) == "+8..12 (+100..+149 dogs)" and se.band_name((0.08, 1.0)) == "+8+"
    st = {"picks": [{"game_id": "m", "league": "mlb", "side": "home", "team": "Cubs", "sp": "Kevin Gausman",
                     "result": None}]}
    games = {"m": {"status": "pre", "sp_home": "Kevin Gausman"}}
    se.watch(st, games, {})
    assert not st["picks"][0].get("key_out")
    games["m"]["sp_home"] = "Some Bullpen Guy"                  # scratched late
    se.watch(st, games, {})
    assert st["picks"][0]["key_out"] == "Kevin Gausman (SP)"
    assert "Kevin Gausman out - don't chase it" in se.label(st["picks"][0], 130)


def test_early_retrain_is_cached_for_a_week():
    """9/30: the recent-seasons retrain lived in early.json, and post() saved over it - it retrained every hour."""
    import sports_early as se
    saved = (se.PARAMS_PATH, sm.tune, se.passed)
    se.PARAMS_PATH = os.path.join(tempfile.mkdtemp(), "p.json")
    calls = []
    sm.tune = lambda games, lg, prev=None: calls.append(lg) or {"k": 1, "hfa": 0, "w": [0]}
    se.passed = lambda path=None: {"nfl": [(0.04, 1)]}
    try:
        now = datetime(2026, 10, 1, tzinfo=timezone.utc)
        se.recent_params({}, now)
        se.save({"picks": []}, os.path.join(tempfile.mkdtemp(), "e.json"))     # post() saving its own file
        se.recent_params({}, now + timedelta(hours=1))
        assert calls == ["nfl"]                                             # retrained once, not every hour
        se.recent_params({}, now + timedelta(days=8))
        assert calls == ["nfl", "nfl"]                                      # a week later: fresh
    finally:
        se.PARAMS_PATH, sm.tune, se.passed = saved


def test_lock_is_not_just_the_priciest_favorite():
    """The owner (9/30): 'any moron could take the biggest favorite closest to -150 and call it the Lock.' The Lock
    now has to be one the engine's OWN read says is worth its price; the priciest favorite only wins when it agrees."""
    base = {"league": "mlb", "market": "ml", "line": None, "home": True, "stype": "3", "reasons": ["ratings"], "trap": False,
            "start": "2026-09-30T21:00Z", "drift": 0.0}
    def cand(gid, team, odds, p, own):
        d = sd.decimal(odds)
        return {**base, "game_id": gid, "side": "home", "team": team, "opp": "X", "odds": odds, "dec": d, "p": p,
                "p_market": 0.57, "edge": p * d - 1, "edge_own": own * d - 1}
    priciest = cand("g1", "Pricey", -147, 0.575, 0.567)           # tops the board; the engine's own read isn't sold
    #                                                               (not "fighting Vegas" - just not convinced)
    agreed = cand("g2", "Agreed", -140, 0.570, 0.59)              # the engine's own read says worth it
    assert not sports.own_agrees(priciest) and sports.own_agrees(agreed)
    b = sports.make_board([priciest, agreed])
    assert b["lock"] and b["lock"]["legs"][0]["team"] == "Agreed", b["lock"]
    other = cand("g3", "Other", -135, 0.562, 0.56)                 # nothing agrees: no fake Lock (10/1 bug check -
    b = sports.make_board([priciest, other])                       # the Flyers) - post_board puts up a LEAN Lock
    assert b["lock"] is None


def test_new_boxes_never_restyle_the_record_cards():
    """9/30: the WE GOT IN EARLY rows used the class name 'gr' - the record cards' own class - and its flex rule laid
    every record card out sideways (the numbers cut off on phones). New boxes use their own class names."""
    import sports_early as se
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert ".gr{{display:flex" not in src and ".egr{{display:flex" in src
    assert 'class="gr"' not in open(se.__file__).read()


def test_early_plays_post_without_pings():
    """The owner (9/30): turn off the notifications for early value plays. 10/1 he turned them back on: "when the
    engine detects an early value play, it will send it over" - one ping each, only once the dashboard shows it."""
    import sports_early as se
    assert se.PINGS is False and se.SPOT_MAX_WEEK is None            # (10/4: no early-play pings anymore - the owner;
    #                                                                   10/1: no weekly cap either)
    src = open(sports.__file__).read()
    assert "ping=queue.append if sports_early.PINGS else None" in src


def test_series_spot_and_a_dog_of_the_day_every_day():
    """(9/30 the owner wanted a Dog every day; 10/1 he reversed it: "a Dog of the Day is a unit play - we don't force
    it".) Among the REAL-value dogs, the Dog of the Day is the one the analysis likes best (own read vs price + the 9/30 factors: a playoff
    favorite that just lost, hockey money moves, goalies). Weighed, never a hard 'can't' (the owner: no rigid rules)."""
    games = {"g1": {"id": "g1", "league": "mlb", "status": "final", "stype": "3", "start": "2026-09-29T21:00Z",
                    "home": "H", "away": "A", "home_score": "3", "away_score": "6"},
             "g2": {"id": "g2", "league": "mlb", "status": "pre", "stype": "3", "start": "2026-09-30T21:00Z",
                    "home": "H", "away": "A"}}
    assert sports.lost_last_in_series(games, games["g2"], "home") is True
    assert sports.lost_last_in_series(games, games["g2"], "away") is False
    assert sports.lost_last_in_series(games, {**games["g2"], "stype": "2"}, "home") is False       # regular season
    base = {"market": "ml", "line": None, "home": False, "stype": "3", "reasons": [], "trap": False,
            "start": "2026-09-30T21:00Z", "drift": 0.0}
    def dog(gid, team, lg, odds, own, mkt, **kw):
        d = sd.decimal(odds)
        return {**base, "league": lg, "game_id": gid, "side": "away", "team": team, "opp": "X", "odds": odds, "dec": d,
                "p": mkt, "p_market": mkt, "edge": mkt * d - 1, "edge_own": own * d - 1, **kw}
    wsox = dog("w", "White Sox", "mlb", 122, 0.42, 0.43, opp_lost_last=True)        # facing the desperate favorite
    pens = dog("p", "Penguins", "nhl", 120, 0.46, 0.44, drift=0.03)                  # the money ran away from them
    kings = dog("k", "Kings", "nhl", 160, 0.38, 0.37)
    assert sports.dog_score(wsox) > sports.dog_score(kings) > sports.dog_score(pens)
    b = sports.make_board([wsox, pens, kings])
    assert b["dog"] is None                     # 10/1, the owner: none has real value = no Dog of the Day (a forced dog
    #                                             takes our ROI down - the Dog is a unit play like the Lock, never a lean)
    keep_good = sports.good
    sports.good = lambda c: True                # ...among REAL-value dogs, the analysis picks: the White Sox, never the
    try:                                        # Penguins the money ran from (a trap score under 0 is never the Dog)
        wsox_v = {**wsox, "edge_own": 0.47 * wsox["dec"] - 1}   # (10/1 money check: a unit Dog's read beats its price)
        b = sports.make_board([wsox_v, pens, kings])
        assert b["dog"] and b["dog"]["legs"][0]["team"] == "White Sox"
    finally:
        sports.good = keep_good
    fav = lambda gid, team, p, lost: {**base, "league": "mlb", "game_id": gid, "side": "home", "team": team, "opp": "X",
                                      "odds": -140, "dec": sd.decimal(-140), "p": p, "p_market": p, "edge": 0.0,
                                      "edge_own": p * sd.decimal(-140) - 1, "lost_last": lost}
    three = sports.make_board([fav("f1", "Yanks", 0.60, False), fav("f2", "Fly", 0.59, False),
                               fav("f3", "Astros", 0.575, True), fav("f4", "Pads", 0.555, False)])["three"]
    assert [l["team"] for l in three["legs"]][-1] == "Pads"        # the favorite that just lost goes to the back
    # hoops / hockey bounce back after losing the last game (NBA +28%, NHL +29%); baseball doesn't
    assert sports.dog_score(dog("h", "H", "nhl", 130, 0.43, 0.43, lost_last=True)) > 0 > \
        sports.dog_score(dog("m", "M", "mlb", 130, 0.43, 0.43, lost_last=True))
    assert sports.dog_score(dog("o", "O", "nhl", 160, 0.38, 0.38, road_opener=True)) == sports.dog_score(dog("o", "O", "nhl", 160, 0.38, 0.38))   # (10/2 study: the road-opener angle is off - wrong sign)
    gm = {"a": {"league": "nhl", "home": "7", "stype": "2", "start": "2026-10-01T02:00Z"}}
    assert sports.home_opener(gm, gm["a"]) and not sports.home_opener(
        {**gm, "b": {"league": "nhl", "home": "7", "stype": "2", "start": "2026-09-29T02:00Z"}}, gm["a"])
    fixed3 = [fav("f1", "Yanks", 0.60, False), fav("f2", "Fly", 0.59, False), fav("f4", "Pads", 0.555, False)]
    b4 = sports.make_board(fixed3 + [fav("f3", "Astros", 0.575, True)], fixed={"three": fixed3})
    assert b4["four"] and [l["team"] for l in b4["four"]["legs"]] == ["Yanks", "Fly", "Pads", "Astros"]   # 9/30: the 4-leg
    #                                                             never drops the posted 3-leg's 55.5% leg
    held = {**fav("f9", "Waiting Fav", 0.58, False), "waiting": ["starting pitcher"]}    # a favorite waiting on news
    big = dog("x", "Longshot", "mlb", 450, 0.40, 0.18)                              # past +280: never
    keep_good = sports.good
    sports.good = lambda c: True
    try:
        assert sports.make_board([wsox_v, kings, held])["dog"]["legs"][0]["team"] == "White Sox"   # never holds the Dog
        assert (sports.make_board([big, kings])["dog"] or {"legs": [{}]})["legs"][0].get("team") != "Longshot"
    finally:
        sports.good = keep_good


def test_parlay_never_says_they_got_us_as_the_dog():
    """The owner (9/30): a 2-leg of -144 and -142 said 'They got us as the dog? Line makers trippin'.' A parlay always
    pays plus money - the 'plus-money lock' lines are for ONE pick priced plus money, never a parlay."""
    import sports_dashboard as sdb
    leg = lambda t, o: {"game_id": t, "league": "mlb", "market": "ml", "side": "home", "team": t, "opp": "X", "odds": o,
                        "p": 0.57, "line": None, "start": "2026-09-30T23:00Z", "home": True, "reasons": ["r"],
                        "result": None, "tier": "lock", "dec": sd.decimal(o), "edge": 0.0, "edge_own": 0.0,
                        "p_market": 0.57, "drift": 0.0}
    pk = {"kind": "two", "date": "2026-09-30", "status": "open", "stake": 100, "dec": 2.89, "american": 189,
          "legs": [leg("Yankees", -144), leg("Flyers", -142)]}
    try:
        h = sdb._pick_card("two", pk)
    except TypeError:
        h = sdb._pick_card(pk)
    assert "trippin" not in h and "got us as the dog" not in h


def test_writeups_make_sense():
    """The owner (9/30): check every review - not vague, makes sense, our lingo right. Found on the live board:
    'Bad read. Bad read.', 'Bergs's about to...', 'let it slip. Tip the cap.' (credit to the other side after OUR guy
    blew it), 'Judge and Mead are both out. It evens out' (a star isn't a bench guy), 'about to beat the brakes off' on a
    57% pick, 'best ball of the year (3 straight W's)', and live tennis reviews that never said win or lose."""
    import sports_lingo as L, sports_tennis as T, sports_breakdown_v24 as B
    assert "Tip the cap." not in L.PAL["lk"] and "Bad read." not in L.PAL["lk"]
    src_t, src_l, src_b = open(T.__file__).read(), open(L.__file__).read(), open(B.__file__).read()
    assert "{them}'s about" not in src_t and "{me}'s about" not in src_t and "{me}'s {age}" not in src_t
    assert "It evens out, and we still like" not in src_b and "best ball of the year" not in src_b
    assert "about to beat the brakes off {them}.\",\n" not in src_b.split('"w_better"')[1][:900]
    assert "closed the door] and beat {t}" in src_l and "flipped it] to win it" in src_l


def test_same_pick_never_counts_twice():
    """9/30: two runs at once both posted the Kings as the Dog of the Day - the same pick is kept once."""
    leg = {"game_id": "nhl:1", "side": "away", "market": "ml", "line": None, "team": "Kings"}
    ps = [{"date": "2026-09-30", "kind": "dog", "legs": [leg], "posted": "15:22"},
          {"date": "2026-09-30", "kind": "dog", "legs": [dict(leg)], "posted": "15:26"},
          {"date": "2026-09-30", "kind": "dog", "round": 2, "legs": [dict(leg)]},          # a replacement round: its own
          {"date": "2026-09-30", "kind": "lock", "status": "waiting", "legs": []}]
    out = sports.dedupe_picks(ps)
    assert [p.get("posted") for p in out if p["kind"] == "dog"] == ["15:22", None] and len(out) == 3


def test_win_pct_only_over_55():
    """The owner (9/30): '37% to cash on the Kings - only show a percentage if it's above 55%.' Anything 55 or under is
    said in words, everywhere a pick is written up (stored write-ups too)."""
    import sports_dashboard as d
    assert d.pct_ok("✅ Bottom line: Maple Leafs (-130). 54% to cash — get in.") == \
        "✅ Bottom line: Maple Leafs (-130). The price is right — get in."
    assert d.pct_ok("✅ Bottom line: 37% to hit on Kings (+160). Tap in.") == "✅ Bottom line: the price is right on Kings (+160). Tap in."
    assert d.pct_ok("🧠 The engine's got Kings at 37% tonight.") == "🧠 The engine's got Kings right where we want 'em tonight."
    assert d.pct_ok("✅ Bottom line: Ruud ML (-230). 67% to cash — tap in.").endswith("67% to cash — tap in.")
    assert d.pct_ok("📊 The casuals got the Avalanche (93% of the bets).").endswith("(93% of the bets).")   # not a win %
    assert "pct>55?" in open(d.__file__).read()                                                        # question box too


def test_units_and_the_open_bankroll():
    import sports_dashboard as d
    on = d.UNITS_ON
    d.UNITS_ON = True                                       # (tested on; the board shows them once the owner turns them on)
    import sports_early as se
    path, se.PATH = se.PATH, os.path.join(tempfile.mkdtemp(), "early.json")   # (no early plays from other tests)
    try:
        _units_and_the_open_bankroll()
    finally:
        d.UNITS_ON, se.PATH = on, path


def _units_and_the_open_bankroll():
    """The owner (9/30): units under each label (0.5u up to a 10u max play), and an open bankroll - $1,000 to start, a
    unit is 1% of that morning's bankroll, so it grows as we win. Everything transparent."""
    # the ENGINE sizes every play by its edge (the sizing study, 9/30): quarter-Kelly, ½u-10u
    lk = lambda own, o: {"kind": "lock", "legs": [{"p": 0.6, "p_market": 0.55, "odds": o,
                                                    "edge_own": own * (1 + 100 / -o) - 1}]}   # value per $1, as posted
    assert sports.units_for(lk(0.60, -125)) == 2.5 and sports.units_for(lk(0.52, -125)) == 0.0   # its OWN read, not p
    #   (10/1 bug check: a pick its own read says loses money gets NO units - it was ½u)
    assert sports.units_for(lk(0.75, -125)) > sports.units_for(lk(0.65, -125)) > 2.5 and sports.UNIT_MAX == 10
    assert sports.kelly_units(0.9, 200) == 10                                                   # the 10u max
    assert sports.units_for({"kind": "two", "legs": []}) == 0 == sports.units_for({"kind": "four", "legs": []})
    # a parlay has no units - each pick in it carries its own, as a straight bet (the owner, 9/30)
    two = {"date": "2026-09-30", "kind": "two", "status": "lost", "dec": 3.0, "legs": [
        {"game_id": "g1", "side": "home", "odds": -140, "p": 0.63, "tier": "lock", "result": "won"},
        {"game_id": "g2", "side": "away", "odds": -120, "p": 0.54, "tier": "lean", "result": "lost"}]}
    assert [sports.leg_units(two, l) for l in two["legs"]] == [3, 0]         # a lean in a parlay: no units
    lock = {"date": "2026-09-30", "kind": "lock", "status": "won", "dec": 1 + 100 / 140, "legs": [
        {"game_id": "g1", "side": "home", "odds": -140, "p": 0.63, "tier": "lock", "result": "won"}]}
    led = sports.units_ledger([two, lock])                 # the lock counts once (not again as a parlay leg)
    assert len(led["rows"]) == 1 and led["rows"][0][0]["kind"] == "lock"   # (the lean isn't in the bankroll)
    assert abs(sum(r[2] for r in led["rows"]) - 3 * 100 / 140) < 1e-9
    assert sports.units_for({"kind": "dog", "legs": [{"p": 0.37, "odds": 160, "tier": "lean"}]}) == 0.0   # no edge
    #   (+160 needs 38.5% - 37% is no value: no units, 10/1 bug check; a real-value dog gets its edge's units:)
    assert sports.units_for({"kind": "dog", "legs": [{"p": 0.45, "odds": 160}]}) == 2.5                     # by its edge
    assert sports.units_for({"kind": "solo", "lean": True, "legs": [{"p": 0.51}]}) == 0                   # just a lean
    # ⏰ early plays: the ENGINE's call - sized by how far its own read beats the price we got (the owner, 9/30)
    import sports_early as se
    assert se.units({"odds": 124, "own": 0.5703}) == 5.5 and se.units({"odds": 170, "own": 0.40}) == 1 and se.units({"odds": 160, "own": 0.39}) == 0.5
    assert se.units({"odds": 200, "own": 0.40}) == 2.5 and se.units({"odds": 200, "own": 0.9}) == 10
    early = [{"game_id": "nfl:9", "side": "away", "team": "Jaguars", "odds": 124, "own": 0.5703, "start": "2026-10-04T17:00Z",
              "result": "won", "graded_at": "2026-10-04T20:00Z"}]
    lk_j = {"date": "2026-10-04", "kind": "lock", "status": "won", "dec": 1.8, "legs": [
        {"game_id": "nfl:9", "side": "away", "odds": -125, "p": 0.6, "tier": "lock", "result": "won"}]}
    led = sports.units_ledger([lk_j], early)                 # on the board too: BOTH count, each with its units (the
    assert len(led["rows"]) == 2                              # owner, 10/4: "Jaguars can be both" - ½u early + 1u Dog)
    er = [r for r in led["rows"] if r[0]["units_tier"] == "early"][0]
    assert er[1] == 5.5 and abs(er[2] - 5.5 * 1.24) < 1e-9
    day1 = {"date": "2026-09-29", "kind": "lock", "status": "won", "dec": 1.5, "legs": [{"p": 0.563}]}   # 2u, +1u
    day2 = {"date": "2026-09-30", "kind": "lock", "status": "lost", "dec": 1.5, "legs": [{"p": 0.563}]}  # 2u, -2u
    led = sports.units_ledger([day2, day1])
    assert led["by_date"] == {"2026-09-29": 10.0, "2026-09-30": 10.1}      # the unit grew with the bankroll
    assert led["bankroll"] == round(1000 + 10.0 - 2 * 10.1, 2)
    import sports_dashboard as d
    assert "BANKROLL" in d.units_box([day1, day2]) and d.units_box([]) == ""
    box = d.units_box([day1, day2], "2026-09-30")          # the owner, 9/30: every ROI stat - overall, the day, the week
    assert all(x in box for x in ("Overall", "Today", "Last 7 days", "ROI", "Started at $1,000"))
    assert "Today" not in d.units_box([day1, day2], "2026-10-09")        # nothing graded that day: no empty row
    assert "Parlays" not in box
    assert "WE GAMBLIN" in d.LIVE_NO_UNITS and "var NOU=" in open(d.__file__).read()   # live plus money: no units, said so
    src = open(d.__file__).read()                             # it stays up (the owner, 9/30): the watching box, a live
    assert "+HEAD+NOU+'<div class=\"nolive\">'" in src and "WE&#39;RE IN</span></div>'+NOU+'</section>'" in src   # bet, tonight's bets
    assert "\n.nou{{text-align:center" in open(d.__file__).read()          # its own CSS rule (a spliced one broke it)
    assert d._units_line(1).startswith('<div class="un"><span class="mb">💰</span> 1 UNIT<') and "$" not in d._units_line(1)
    assert "NO UNITS — JUST A LEAN" in d._units_line(0)                   # a lean says so (the owner, 9/30)
    assert "½ UNIT" in d._units_line(0.5, "Yankees") and 'class="unw"' in d._units_line(0.5, "Yankees")   # ½u says why
    assert len({d._units_line(0.5, k, -140) for k in ("Yankees", "Flyers", "Kings", "Padres", "Bears")}) > 1   # not on repeat
    assert "expensive" in d.HALF_WHY["fav"][0] and not any("expensive" in x for x in d.HALF_WHY["dog"])   # his words
    assert "long run" in " ".join(d.HALF_WHY["fav"])       # the WHY: big bets on expensive lines lose over time
    line = d._units_line(0.5, "Kings", 160)                 # a ½u dog: small bet, big payout
    assert any(d.E(x) in line for x in d.HALF_WHY["dog"])
    assert all("unw" in d._units_line(u, "Kings", o) for u in (0.5, 1, 1.5, 2, 4, 10) for o in (160, -120))   # always a why
    line = d._units_line(1, "Padres", -130)
    assert any(d.E(x) in line for x in d.FULL_WHY["fav"])
    d.WHY_USED.clear()
    assert d._units_line(2, "Flyers", 136) != d._units_line(2.5, "Blues", 170).replace("2½ UNITS", "2 UNITS")   # no repeats
    line, line2 = d._units_line(2.5, "Blues", 170), d._units_line(3, "Yankees", -130)
    assert any(d.E(x) in line for x in d.BIGGER_WHY["dog"]) and any(d.E(x) in line2 for x in d.BIGGER_WHY["fav"])
    assert all(len(v) >= 5 for w in (d.HALF_WHY, d.FULL_WHY, d.BIGGER_WHY, d.BIG_WHY) for v in w.values())   # 5+ ways
    line = d._units_line(5.5, "Jaguars", 124, early=True)
    assert any(x in line for x in d.BIG_WHY["early"])
    assert "5½ UNITS" in d._units_line(5.5, "Jaguars", 124) and "1½ UNITS" in d._units_line(1.5)
    allw = [x for v in (d.HALF_WHY, d.FULL_WHY, d.BIGGER_WHY, d.BIG_WHY) for xs in v.values() for x in xs]
    assert not any(w in " ".join(allw).lower() for w in ("could hit", "not a big", "not worth", "%"))
    # (the owner, 9/30: never sound skeptical of our own pick - the price keeps the bet small, that's all)
    assert ".mb{{display:inline-block;filter:hue-rotate" in open(d.__file__).read()
    assert ".un{{margin-top:2px;text-align:right;font-size:17px;" in open(d.__file__).read()   # bigger (the owner, 9/30)
    assert "🔒 Locks" in box and "Lock of the Day" not in box       # rows by kind of pick (the owner, 9/30)
    assert "🔥 VALUE PLAY<" in d.TIER_CHIP["value"] and "🔥 VALUE PLAY<" in d.LEG_TAG["value"]   # 'value plays', not 'value'
    dog = {"date": "2026-09-30", "kind": "dog", "status": "won", "dec": 2.6, "legs": [{"p": 0.40, "odds": 160, "tier": "lean"}]}
    lean = {"date": "2026-09-30", "kind": "solo", "lean": True, "status": "lost", "dec": 1.9, "legs": [{"p": 0.52}]}
    tiers = [r[0]["units_tier"] for r in sports.units_ledger([dog, lean, two])["rows"]]
    assert sorted(tiers) == ["lock", "value"]          # the Dog of the Day is a value play; leans stay out
    assert "Strong leans" not in box and "Slight leans" not in box
    assert "u bet" not in box and "u ·" not in box          # plain dollars + ROI (the owner: '+6.6u on 14u bet' confused him)


def test_latest_games_line_only_backs_the_pick():
    """The owner, 9/30: 'Kings L 1-5 vs Avalanche' in the Kings' breakdown hurts the pick - the latest-games line only
    shows when we won our last one and they lost theirs (or had none); the units line is bold white, not yellow."""
    import inspect
    import sports_breakdown_v24
    import sports_dashboard as d
    assert not d.latest_ok("📅 Most recent games: Kings L 1-5 vs Avalanche · Avalanche L 1-2 @ Golden Knights.")
    assert not d.latest_ok("📅 Latest: Kings W 3-1 vs Ducks · Avalanche W 4-2 @ Stars.")
    assert d.latest_ok("📅 Latest: Kings W 3-1 vs Ducks · Avalanche L 1-2 @ Golden Knights.")
    assert d.latest_ok("📅 Fresh off: Kings W 3-1 vs Ducks.") and d.latest_ok("🔥 Kings are rolling.")
    leg = {"breakdown": ["🔥 Kings are rolling.", "📅 Latest: Kings L 1-5 vs Avalanche · Avalanche L 1-2 @ Golden Knights."]}
    assert "Avalanche" not in d._breakdown(leg) and "rolling" in d._breakdown(leg)
    src = inspect.getsource(sports_breakdown_v24.breakdown)
    assert '.startswith("W")' in src                        # the engine stops writing a losing latest line too
    css = re.search(r"\.un\{\{?[^}]*\}", inspect.getsource(d)).group(0)
    assert "#fff" in css and "font-weight" in css


def test_monday_thursday_football_always_gets_a_pick():
    """The owner, 9/30: every Monday / Thursday NFL game gets a pick - two games, two picks; a lean is fine."""
    from datetime import date
    import sports_dashboard as d
    mon = date(2026, 10, 5)                                  # a Monday
    g = lambda i, t, st="pre", lg="nfl": {"id": f"{lg}:{i}", "league": lg, "status": st, "stype": "2", "start": t}
    games = {x["id"]: x for x in (g(1, "2026-10-06T00:15Z"), g(2, "2026-10-06T03:00Z"), g(3, "2026-10-06T00:15Z", lg="mlb"),
                                  g(4, "2026-10-06T20:00Z"))}   # (4: Tuesday in Pacific time)
    now = datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc)
    assert sports.night_games(games, mon, [], now) == ["nfl:1", "nfl:2"]          # both Monday games, NFL only
    assert sports.night_games(games, date(2026, 10, 6), [], now) == []           # Tuesday: no rule
    lock = {"date": "2026-10-05", "kind": "lock", "status": "open", "legs": [{"game_id": "nfl:1"}]}
    par = {"date": "2026-10-05", "kind": "two", "status": "open", "legs": [{"game_id": "nfl:2"}]}
    assert sports.night_games(games, mon, [lock, par], now) == ["nfl:2"]       # the Lock covers it; a parlay leg doesn't
    c = lambda side, p, odds, **k: {"game_id": "nfl:2", "side": side, "market": "ml", "odds": odds, "p": p, "edge": 0.0,
                                    "dec": 1 + (odds / 100 if odds > 0 else 100 / -odds), "reasons": [], **k}
    b = sports.night_pick([c("home", 0.58, -140), c("away", 0.42, 120)])        # nothing clears the bar: a lean
    assert b["lean"] and b["legs"][0]["side"] == "home"
    assert sports.night_pick([c("home", 0.70, -250), c("away", 0.30, 200, trap=True)]) is None   # never past -150 / a trap
    pk = {"date": "2026-10-05", "kind": "night", "status": "open", "lean": True, "legs": [], "american": -140, "dec": 1.7,
          "stake": 100}
    leg = {"team": "Steelers", "market": "ml", "line": None}
    assert "STEELERS ML" in d._pick_card("night", {**pk, "legs": [leg], "status": "waiting", "waiting": [], "deadline": "2026-10-06T00:00Z"})
    two = d._cards("2026-10-05", [], [("night", "<a>", 111), ("night", "<b>", None)])   # each card its own clock
    assert 'data-gone="111"><a>' in two and two.endswith("<b>")


def test_tennis_count_is_todays_slate():
    """The owner, 9/30: the tennis card said '9 men's + 4 women's' - yesterday's slate (a match moved to tonight) and
    today's added together. It counts today's; a yesterday match still going is said on its own."""
    import sports_dashboard as d
    tour = lambda l: l["tour"]
    y = {"date": "2026-09-29", "picks": [{"tour": "atp", "result": "lost"}] * 4 + [{"tour": "atp", "result": None}]
         + [{"tour": "wta", "result": "won"}] * 2}
    t = {"date": "2026-09-30", "picks": [{"tour": "atp", "result": None}] * 4 + [{"tour": "wta", "result": None}] * 2}
    assert d._tn_count([y, t], tour) == "4 men's + 2 women's · 1 from yesterday still going"
    assert d._tn_count([t], tour) == "4 men's + 2 women's" and d._tn_count([], tour) == "new picks at 8 AM PT"


def test_tennis_live_set_correction():
    """9/30: tennis live plus money went 3-6 - the live model under-rated a set (69k matches, 2021+ never seen: women's
    down a set said 57%, really 50%). The player behind is now rated right; level sets are untouched."""
    import sports_tennis_live as stl
    assert abs(stl.set_fixed(0.57, "wta", (0, 1)) - 0.49) < 0.01 and abs(stl.set_fixed(0.57, "atp", (0, 1)) - 0.537) < 0.01
    assert stl.set_fixed(0.43, "wta", (1, 0)) > 0.50                    # up a set: more than the model said
    assert stl.set_fixed(0.5, "wta", (1, 1)) == 0.5 and abs(stl.set_fixed(0.6, "atp", (0, 0)) - 0.6) < 0.01   # level
    # the 9/30 bets it would have skipped: Sonmez +132 down a set (the model's 46%), Bondar +128 down a set (47%)
    for p, odds in ((0.46, 132), (0.47, 128)):
        assert stl.set_fixed(p, "wta", (0, 1)) * (1 + odds / 100) - 1 < 0.03      # no longer a live edge


def test_hot_key_player_counts_against_a_pick():
    """The form study (9/30): the books over-rate a hot key player - the side with the much hotter goalie (NHL, worse
    than average 5 of 5 seasons) / stars (NBA, 3 of 4) goes toward the back of the Lock / parlay line and the Dog's
    score. Weighed, never a ban. Last spring's form never carries into a new season."""
    import sports_form as sf
    assert sf.hot_side("nhl", 6.0) == "home" and sf.hot_side("nhl", -6.0) == "away" and sf.hot_side("nhl", 3.0) is None
    assert sf.hot_side("mlb", 50) is None                                     # baseball / QBs: mixed - not used
    rows = [{"player": "G1", "start": f"2026-01-{d:02d}T00:00Z", "sa": "30", "ga": "3"} for d in range(1, 21)] + \
           [{"player": "G1", "start": f"2026-01-{d:02d}T00:00Z", "sa": "30", "ga": "0"} for d in range(21, 26)]
    assert sf.goalie_form(rows, "G1", "2026-01-27T00:00Z") > 5             # a hot run: save % way up
    assert sf.goalie_form(rows, "G1", "2026-10-07T00:00Z") is None         # last spring's streak: doesn't count
    box = lambda pts: ("2026-01-01T00:00Z", {"A": (36, pts), "B": (34, 20), "C": (10, 2)})
    games = [box(20)] * 15 + [(f"2026-01-{d:02d}T00:00Z", {"A": (36, 35), "B": (34, 20), "C": (10, 2)}) for d in range(10, 15)]
    assert sf.star_form(games, "2026-01-16T00:00Z") > 7 and sf.star_form(games, "2026-03-20T00:00Z") is None
    c = lambda p, hot: {"p": p, "edge": 0.0, "hot_key": hot}
    key = lambda c: (c["p"] - (sports.HOT_W if c.get("hot_key") else 0), c["edge"])
    assert max([c(0.60, True), c(0.585, False)], key=key)["p"] == 0.585     # the Lock: the hot-goalie side goes back
    assert max([c(0.65, True), c(0.585, False)], key=key)["p"] == 0.65      # ...weighed, not banned


def test_overreaction_angle():
    """The form study, deeper (9/30): bettors overreact to an ugly loss. A football dog off a blowout loss (college
    +11.6%, NFL +7.9% vs -3.6% for every dog) and a college hoops favorite on a 6+ game losing streak (+6.7%, 7 of 8
    seasons) get weight - the Dog's score, the Lock / parlay line. Weighed, never a ban."""
    c = lambda lg, odds, st, mk="ml": {"league": lg, "odds": odds, "market": mk, "form_state": st}
    assert sports.overreact(c("nfl", 150, (-24, -1))) and sports.overreact(c("ncaaf", 200, (-35, -2)))
    assert not sports.overreact(c("nfl", 150, (-10, -1)))                  # a close loss: nothing
    assert not sports.overreact(c("nfl", -150, (-24, -1)))                 # a favorite off a blowout: no angle
    assert sports.overreact(c("ncaab", -140, (-3, -6))) and not sports.overreact(c("ncaab", 140, (-3, -6)))
    assert not sports.overreact(c("nfl", 150, (-24, -1), "spread")) and not sports.overreact(c("nba", 150, (-40, -8)))
    import sports_form as sf
    games = {f"nfl:{k}": {"id": f"nfl:{k}", "league": "nfl", "status": "final", "stype": "2", "start": f"2026-09-{d}T17:00Z",
                          "home": "A", "away": "B", "home_score": hs, "away_score": as_}
             for k, (d, hs, as_) in enumerate(((20, "3", "31"), (27, "10", "38")))}
    st = sf.team_states(games, "2026-09-30T20:00Z")
    assert st[("nfl", "A")][:2] == (-28.0, -2) and st[("nfl", "B")][:2] == (28.0, 2)
    assert sf.team_states(games, "2026-11-30T20:00Z") == {}                 # stale: nothing


def test_scoring_drought_favorite():
    """10/1, the owner's Red Sox point (announcer: their longest scoreless run going into the playoffs): a baseball
    FAVORITE that hasn't scored in 12+ innings in a row did +4.9% vs -3.8% for every favorite (-150..-101: +10.2%, 7 of
    9 seasons) - bettors fade cold bats too hard. It's weight on the Lock / parlay line, never a ban; dogs get nothing."""
    c = lambda lg, odds, st: {"league": lg, "odds": odds, "market": "ml", "form_state": st}
    assert sports.overreact(c("mlb", -130, (-9, -1, -120, False, 16)))
    assert not sports.overreact(c("mlb", -130, (-9, -1, -120, False, 11)))  # 11 innings: not a drought yet
    assert not sports.overreact(c("mlb", 130, (-9, -1, -120, False, 16)))   # a dog in a drought: no bump
    assert not sports.overreact(c("nhl", -130, (-3, -1, -120, False, 16)))  # baseball only
    assert not sports.overreact(c("mlb", -130, (-9, -1)))                   # old 2-field states still work
    import sports_form as sf
    ls = lambda runs: ",".join(map(str, runs))
    games = {f"mlb:{k}": {"id": f"mlb:{k}", "league": "mlb", "status": "final", "stype": "2",
                          "start": f"2026-09-{d}T17:00Z", "home": "A", "away": "B", "home_score": str(sum(h)),
                          "away_score": str(sum(a)), "ls_home": ls(h), "ls_away": ls(a)}
             for k, (d, h, a) in enumerate(((27, [0, 2, 0, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 0]),
                                            (29, [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 3, 0, 0, 0, 0, 0, 0])))}
    st = sf.team_states(games, "2026-09-30T20:00Z")
    assert st[("mlb", "A")][4] == 15 and st[("mlb", "B")][4] == 6          # A: 7 + 8 scoreless innings in a row


def test_live_never_takes_a_playoff_favorite_that_lost_the_last_game():
    """9/30: the engine grabbed the Astros live (+133, down 4-0 in the 1st) - a playoff favorite that lost the last game
    of the series (baseball: won 50%, -14%; the owner: "the Astros was a trap"). Live now knows the series too."""
    L = sports_live
    keep = (L.live_prob, L.substantial, L.time_left, L.min_p)
    try:
        L.live_prob = lambda *a, **k: 0.50
        L.substantial = lambda *a, **k: True
        L.time_left = lambda *a, **k: 8.5
        L.min_p = lambda: 0.40
        st = {"mlb": {"curve": {"ll": 0.6}, "table": {}}}
        box = {"period": 1, "total_home_points": 0, "total_away_points": 0, "linescore": [{"home_points": 0, "away_points": 0}]}
        g = {"id": "mlb:x", "home_name": "Astros", "away_name": "White Sox", "stype": "3"}   # (tied: the 10/1 trailing
        #                                                    cap below is its own rule - this one's the series knock)
        ev = lambda lost: [p["team"] for p in L.evaluate("mlb", g, box, 133, -160, st, 0.62, 0.62, 0.0, "", 1, True,
                                                          lost_last=lost)]
        assert ev(()) == ["Astros"]                          # (the price alone said value)
        assert ev({"home"}) == []                            # lost the last game as the favorite: 8 points off - no value left
        assert ev({"away"}) == ["Astros"]                    # (the other side losing it changes nothing here)
        L.live_prob = lambda *a, **k: 0.62                   # a real mispriced spot: still value after the knock -
        assert ev({"home"}) == ["Astros"]                    # weighed, not banned (the owner: no rigid rules)
    finally:
        L.live_prob, L.substantial, L.time_left, L.min_p = keep
    assert L.series_lost({"stype": "2"}) == set()            # regular season: no series


def test_live_calibration_spots():
    """10/1 live check (line scores 2018-26; learned 2018-23, checked 2024-26): the live curve runs high in a few spots,
    the same way both times - MLB trailing pregame favorites, college football tied / trailing favorites, NHL trailing
    pregame dogs. Those come down by the gap; everything else is left alone."""
    L = sports_live
    keep = (L.live_prob, L.substantial, L.time_left, L.min_p)
    try:
        L.live_prob = lambda *a, **k: 0.45
        L.substantial = lambda *a, **k: True
        L.time_left = lambda *a, **k: 7.0
        L.min_p = lambda: 0.30
        st = {"mlb": {"curve": {"ll": 0.6}, "table": {}}}
        box = {"period": 3, "total_home_points": 1, "total_away_points": 2, "linescore": [{"home_points": 1, "away_points": 2}]}
        g = {"id": "mlb:y", "home_name": "Mets", "away_name": "Braves", "stype": "2"}
        ev = lambda pre: L.evaluate("mlb", g, box, 170, -200, st, pre, pre, 0.0, "", 1, True)
        fav, dog = ev(0.6), ev(0.4)                          # the Mets down a run at +170: a pregame favorite / dog
        assert dog and abs(dog[0]["p"] - 0.45) < 0.002
        assert fav and abs(fav[0]["p"] - (0.45 + L.LIVE_CAL[("mlb", "trail", "fav")])) < 0.002
        assert ("nfl", "trail", "fav") not in L.LIVE_CAL and ("nba", "trail", "dog") not in L.LIVE_CAL
        assert L.LATE_HIST_W == {"mlb": 1.0, "nhl": 1.0}            # late + trailing: all the way to the real history
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_live.py")).read()
        assert "p = (1 - w_) * p + w_ * h[1]" in src
    finally:
        L.live_prob, L.substantial, L.time_left, L.min_p = keep


def test_live_baseball_knows_the_inning_half_and_a_shootout_is_a_coin_flip():
    """10/4 live audit. (1) Action Network's baseball box never said top or bottom: every MLB live bet (0-5) was logged
    at "Inning 7" and the clock counted the home team's at-bat as still to come - half an inning too much game left,
    the wrong history bucket late. ESPN's scoreboard (read the same check for the score) says it; the box takes it, the
    pending pick's clock says Top / Bot / End. (2) An NHL shootout has no clock and read as 20 minutes left - a 60%
    favorite showed 55% to win a coin flip. A shootout is as good as over: both sides sit at ~50%."""
    L = sports_live
    assert L.time_left("mlb", 9, None, "top") > L.time_left("mlb", 9, None, "bottom") > L.time_left("mlb", 9, None, "end")
    assert L.time_left("mlb", 7, None, None) == L.time_left("mlb", 7, None, "top")        # unknown = the top (as before)
    assert L._espn_half("Top 5th") == "top" and L._espn_half("Mid 5th") == "bottom" and L._espn_half("Bot 5th") == "bottom" \
        and L._espn_half("End 5th") == "end"
    L.ESPN_HALF.clear()
    L.ESPN_HALF["401"] = "bottom"
    g = {"id": "mlb:401", "home_name": "Astros", "away_name": "White Sox"}
    box = {"period": 7, "total_home_points": 0, "total_away_points": 1}
    L.SCORES["mlb:401"] = {"clock": "Inning 7", "live": True}
    try:
        assert L.fill_half("mlb", g, box) and box["inning_half"] == "bottom"
        assert L._clock_txt("mlb", box) == "Bot 7th" and L.SCORES["mlb:401"]["clock"] == "Bot 7th"
        assert not L.fill_half("mlb", g, box)                                            # a box that says: left alone
        assert not L.fill_half("nhl", {"id": "nhl:1"}, {"period": 2}) and not L.fill_half("mlb", {"id": "mlb:9"}, {"period": 2})
        assert L._clock_txt("mlb", {"period": 5, "inning_half": "end"}) == "End 5th"
    finally:
        L.SCORES.pop("mlb:401", None)
        L.ESPN_HALF.clear()
    ev = {"id": "401", "date": "2026-10-04T23:00Z", "competitions": [{"status": {"type": {"state": "in", "shortDetail": "End 6th"}, "period": 6},
          "competitors": [{"homeAway": "home", "score": "2", "team": {"id": "1", "displayName": "Astros", "abbreviation": "HOU"}},
                          {"homeAway": "away", "score": "1", "team": {"id": "2", "displayName": "White Sox", "abbreviation": "CWS"}}]}]}
    assert L.espn_as_an("mlb", ev)["boxscore"]["inning_half"] == "end"
    # a shootout: no clock, nothing left - the pregame favorite is no longer ~55% on the curve
    assert L.time_left("nhl", 5, None) == 0.02 and L.time_left("nhl", 5, "0:00") == 0.02
    assert abs(L.time_left("nhl", 4, "5:00") - 5 / 60 / 2) < 1e-9                             # overtime keeps its clock
    assert abs(L.time_left("nhl", 5, "12:30") - 12.5 / 60 / 2) < 1e-9                         # (playoff 2OT has one)
    fit = {"s": 1.2, "w": 1.5, "m": 0.0}
    assert abs(L.live_prob("nhl", 0.60, 0, L.time_left("nhl", 5, None), fit=fit) - 0.5) < 0.03


def test_rested_dog_vs_a_back_to_back():
    """Fatigue study (9/30): a rested dog facing a team on the 2nd night of a back-to-back - NBA +6.5%, NHL +1.9% (4 of
    5 seasons each) vs -6% for every dog. It adds to the Dog's score."""
    import sports_form as sf
    games = {"a": {"league": "nba", "status": "final", "stype": "2", "start": "2026-11-01T00:00Z", "home": "A", "away": "C"},
             "b": {"league": "nba", "status": "final", "stype": "2", "start": "2026-10-29T00:00Z", "home": "B", "away": "D"}}
    st = sf.last_starts(games)
    assert sf.played_yesterday(st, "nba", "A", "2026-11-02T00:30Z") and not sf.played_yesterday(st, "nba", "B", "2026-11-02T00:30Z")
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "league": "nba"}
    assert sports.dog_score({**base, "rested_vs_b2b": True}) == sports.dog_score(base) + 3


def test_early_play_on_the_daily_board_says_we_got_in_early():
    """The owner, 9/30: an early value play can still be a daily pick on game day (at the new line, if it's still a
    play) - its card says we got in early and why it's still worth it; the board never takes the other side of it."""
    import inspect
    import sports_dashboard as d
    d.EARLY_IN.clear()
    d.EARLY_IN[("nhl:1", "home")] = 136
    leg = {"game_id": "nhl:1", "side": "home", "market": "ml", "team": "Flyers", "odds": 110}
    assert "We got in early at +136" in d.E(d._early_line(leg)).replace("&amp;", "&") or "+136" in d._early_line(leg)
    assert "still" in d._early_line(leg)                               # the line moved against us: still worth it
    assert any(w in d._early_line({**leg, "odds": 150}) for w in ("better", "even more"))   # the price got better
    assert d._early_line({**leg, "side": "away"}) == "" and d._early_line({**leg, "market": "spread"}) == ""
    d.EARLY_IN.clear()
    assert "sports_early.load().get(\"picks\")" in inspect.getsource(sports.post_board)   # never the other side of it


def test_one_alert_never_rings_twice():
    """The owner, 9/30: an alert came in twice. A phone signed up twice (a renewed sign-up never dropped the old
    one) gets the same alert id twice - the 2nd now replaces the 1st quietly, and a renewal drops the old sign-up."""
    import sports_dashboard as d
    path = os.path.join(tempfile.mkdtemp(), "sw.js")
    d.write_sw(path)
    sw = open(path).read()
    assert "renotify: !m.id" in sw and "pushsubscriptionchange" in sw and "/unsubscribe" in sw
    assert 'post("/unsubscribe",{{endpoint:s.endpoint}})' in open(d.__file__).read()


def test_puck_luck():
    """NHL puck luck (9/30): the books over-rate a lucky team - a dog whose PDO (last 10) is <= 985 gets +2 on the Dog's
    score, >= 1015 gets -3."""
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "league": "nhl"}
    s0 = sports.dog_score(base)
    assert sports.dog_score({**base, "pdo": 975}) == s0 + 2 and sports.dog_score({**base, "pdo": 1025}) == s0 - 3
    assert sports.dog_score({**base, "pdo": 1000}) == s0
    import sports_form as sf
    assert sf.pdo_states({}, "2026-10-10T00:00Z") == {}


def test_coaches_season_names():
    """The coaching download (9/30) asks ESPN for each team's coaches by ESPN's season name: football = the year it
    starts (a January playoff game is last season's), NBA / NHL / college hoops = the year it ends."""
    import sports_coaches as co
    g = lambda lg, st: {"league": lg, "start": st, "home": "1", "away": "2"}
    assert list(co.teams_by_season({"a": g("nfl", "2025-01-12T18:00Z")}, "nfl")) == [2024]
    assert list(co.teams_by_season({"a": g("nba", "2024-11-01T00:00Z")}, "nba")) == [2025]
    assert list(co.teams_by_season({"a": g("nba", "2025-03-01T00:00Z")}, "nba")) == [2025]
    assert list(co.teams_by_season({"a": g("mlb", "2025-06-01T00:00Z")}, "mlb")) == [2025]


def test_team_stats_kept_for_the_coaching_study():
    """The coaching-style study (9/30): each team's own box (4th-down tries, 3-point attempts...) is kept from the same
    ESPN download as the players - every stat ESPN gives, one line per game."""
    import sports_roster as sr
    pay = {"boxscore": {"teams": [{"team": {"id": "12"}, "statistics": [{"name": "fourthDownEff", "displayValue": "2-3"},
                                                                         {"name": "rushingAttempts", "displayValue": "31"},
                                                                         {"name": "x", "displayValue": "--"}]},
                                  {"team": {"id": "7"}, "statistics": []}]}}
    assert sr.parse_team("nfl", "nfl:1", "2026-09-01T00:00Z", pay) == {"12": {"fourthDownEff": "2-3", "rushingAttempts": "31"}}
    keep = sr.TEAM_DIR
    sr.TEAM_DIR = tempfile.mkdtemp()
    try:
        sr.add_team("nfl", "nfl:1", "2026-09-01T00:00Z", {"12": {"a": "1"}})
        assert sr.team_ids("nfl") == {"nfl:1"} and sr.team_ids("nba") == set()
        # 9/30: two runs appended to ONE file at once and the save clashed (the job failed, the owner got emails) -
        # each run now writes its own file; an old file with clash markers still reads
        assert os.listdir(os.path.join(sr.TEAM_DIR, "nfl")) == [f"{sr.RUN_TAG}.jsonl"]
        with open(os.path.join(sr.TEAM_DIR, "nfl.jsonl"), "w") as f:
            f.write('<<<<<<< HEAD\n{"gid": "nfl:2", "start": "x", "teams": {}}\n=======\n>>>>>>> abc\n')
        assert sr.team_ids("nfl") == {"nfl:1", "nfl:2"}
    finally:
        sr.TEAM_DIR = keep
    assert "-X theirs" in open(".github/workflows/rosters.yml").read()


def test_upset_bounce_and_hangover():
    """Schedule spots (9/30): an NBA team that got upset as a -250 favorite bounces back (+4.9% as a fav, 6 of 8 seasons;
    +7.1% as a dog); a dog right after its +200 upset win is a hangover (NFL -30%, college -28%, MLB -14%)."""
    c = lambda lg, odds, st: {"league": lg, "odds": odds, "market": "ml", "form_state": st}
    assert sports.overreact(c("nba", -180, (-6, -1, -300, False)))               # upset as a big favorite: bounce
    assert not sports.overreact(c("nba", -180, (-6, -1, -150, False)))           # a normal loss: nothing
    assert sports.hangover(c("nfl", 150, (7, 1, 240, True))) and not sports.overreact(c("nfl", 150, (7, 1, 240, True)))
    assert not sports.hangover(c("nfl", -150, (7, 1, 240, True)))                # a favorite now: no hangover
    assert not sports.hangover(c("nba", 150, (7, 1, 240, True)))                 # (NBA: no hangover found)
    assert sports.overreact(c("nfl", 150, (-24, -1)))                            # the old 2-field state still works
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "league": "mlb", "market": "ml"}
    assert sports.dog_score({**base, "form_state": (3, 1, 210, True)}) == sports.dog_score(base) - 3


def test_cover_streaks_and_revenge():
    """Cover streaks & revenge (9/30): a spread pick on a team that failed to cover 4+ straight moves up the line, one
    that covered 4+ straight moves back; a college football dog facing the team that blew it out last meeting +3."""
    c = lambda run, mk="spread", lg="nfl": {"market": mk, "league": lg, "ats_run": run}
    assert sports.cover_run_w(c(-4)) == sports.HOT_W and sports.cover_run_w(c(5)) == -sports.HOT_W
    assert sports.cover_run_w(c(2)) == 0 and sports.cover_run_w(c(-5, "ml")) == 0 and sports.cover_run_w(c(-5, lg="nhl")) == 0
    import sports_form as sf
    g = lambda k, d, hs, as_, sp: {"id": k, "league": "ncaaf", "status": "final", "stype": "2", "start": f"2025-10-{d}T00:00Z",
                                   "home": "A", "away": "B", "home_score": hs, "away_score": as_, "spread_home": sp}
    ats, meet = sf.ats_states({"1": g("1", 10, "45", "7", "-10"), "2": g("2", 17, "30", "20", "-14")})
    assert ats[("ncaaf", "A")] == -1 and ats[("ncaaf", "B")] == 1 and meet[("ncaaf", "B", "A")] == -10
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "league": "ncaaf", "market": "ml"}
    assert sports.dog_score({**base, "revenge": True}) == sports.dog_score(base) + 3   # (the mechanism)
    assert sf.REVENGE == {}          # 10/1: OFF - with the 2024-25 games back in, 4 of 8 seasons: no flag gets set


def test_his_flowers_said_right():
    """The owner, 9/30: one of ours went off in a win - 'Somebody give this man his flowers. Cash it, baby.' It's ALWAYS
    'HIS flowers': never 'give him flowers' / 'give this man flowers' (said wrong it sounds all messed up)."""
    import itertools
    import sports_lingo as L
    import sports_owner_lingo as OL
    import sports_roster as sr
    pools = list(L.REVIEWS[("flowers", "won")][2]) + list(L.LINES["rc:flowers"][2])
    for tpl in pools:
        low = tpl.lower()
        assert "flowers" in low and ("his flowers" in low), tpl
        assert not any(w in low for w in ("give him flowers", "this man flowers", "her flowers")), tpl
    for seed in range(40):
        line = L.review("flowers", "won", f"s{seed}", set(), star="Trevor Lawrence", t="the Jaguars")
        assert "his flowers" in line and "{" not in line and "Trevor Lawrence" in line, line
    assert "give him flowers" in OL.NEVER and "give this man flowers" in OL.NEVER
    assert sr._big_night("nba", {"points": "36"}) and not sr._big_night("nba", {"points": "30"})   # only a real monster night
    assert sr._big_night("nfl", {"passingYards": "362"}) and not sr._big_night("nfl", {"passingYards": "280"})


def test_coaching_study_weights():
    """Coaching study round 1 (9/30) was measured on ESPN's per-season coach list - which turned out to be bad history
    (10/1: today's coach repeated back through every season in the NFL / NHL / MLB / college football, partly wrong in
    the NBA / college hoops). Both weights are OFF until re-tested on real history: no pick moves on them."""
    import sports_coaches as co
    assert co.VET_DOG == {} and co.NEW_FAV == ()
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "league": "nfl", "market": "ml"}
    assert sports.dog_score({**base, "coach": (12, False)}) == sports.dog_score(base)
    assert sports.coach_w({"league": "nba", "odds": -150, "coach": (3, True)}) == 0
    path = os.path.join(tempfile.mkdtemp(), "c.json")
    json.dump({"nba": {"2026": {"1": [{"id": "9", "exp": 1}]}, "2025": {"1": [{"id": "7", "exp": 8}]}},
               "nfl": {"2026": {"5": [{"id": "3", "exp": 12}]}, "2025": {"5": [{"id": "3", "exp": 11}]}}}, open(path, "w"))
    st = co.states("2025-11-01T00:00Z", path)                              # NBA 2025-26 = ESPN's 2026
    assert st[("nba", "1")] == (1, True)
    assert co.states("2026-10-05T00:00Z", path)[("nfl", "5")] == (12, False)


def test_first_time_head_coach_dog():
    """10/1, the owner's Belichick-at-UNC point: a FIRST-TIME head coach's first season, his team a +200 or bigger
    college football dog: -40% (+200..+399) / -72% (+400+) vs -7% / -26% for every such dog, every full season 2022-25.
    -4 on the Dog's score. A coach who's run a program before (Belichick) is NOT a first-timer."""
    import sports_coach_changes as scc
    base = {"odds": 250, "dec": 3.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.28, "league": "ncaaf", "market": "ml"}
    keep = dict(scc.FIRST_TIMER_DOG)
    assert scc.FIRST_TIMER_DOG == {}                    # 10/1: OFF - with the 2024-25 games back in, it flipped
    assert sports.dog_score({**base, "first_timer": True}) == sports.dog_score(base)
    scc.FIRST_TIMER_DOG.update({"ncaaf": 200})          # (the mechanism, if a later study turns it back on)
    try:
        assert sports.dog_score({**base, "first_timer": True}) == sports.dog_score(base) - 4
        assert sports.dog_score({**base, "odds": 150, "first_timer": True}) == sports.dog_score({**base, "odds": 150})
        assert sports.dog_score({**base, "league": "nfl", "first_timer": True}) == sports.dog_score({**base, "league": "nfl"})
    finally:
        scc.FIRST_TIMER_DOG.clear(); scc.FIRST_TIMER_DOG.update(keep)
    row = lambda team, out, date, why, rep, prev: f"| [[{team}]] || [[{out}]] || {date} || {why} || [[{rep}]] || {prev}"
    tb = "{|class=\"wikitable\"\n|-\n! School\n! Outgoing coach\n! Date\n! Reason\n! Replacement\n! Previous position\n" + \
         "\n|-\n".join(["|-", row("North Carolina", "Freddie Kitchens (interim)", "December 11, 2024", "Permanent replacement",
                                   "Bill Belichick", "[[New England Patriots]] head coach"),
                         row("Ole Miss", "Lane Kiffin", "November 30, 2025", "Hired by LSU", "Pete Golding",
                             "Ole Miss defensive coordinator"),
                         row("Fresno State", "Tim Skipper (interim)", "December 4, 2024", "Permanent replacement",
                             "Matt Entz", "USC associate head coach")]) + "\n|}"
    raw = {"ncaaf:2024": {"sections": [tb]}}
    h = {r["coach"]: r for r in scc.hires(raw)}
    assert h["Bill Belichick"]["first_time"] is False and h["Bill Belichick"]["season"] == 2025
    assert h["Pete Golding"]["first_time"] is True and h["Pete Golding"]["season"] == 2026
    assert h["Matt Entz"]["first_time"] is True                             # 'associate head coach' isn't head coach
    games = {"ncaaf:1": {"league": "ncaaf", "home": "145", "home_name": "Ole Miss", "away": "153",
                         "away_name": "North Carolina", "start": "2026-09-05T17:00Z"}}
    assert scc.first_timers(games, "2026-10-01T12:00Z", raw) == set()      # OFF: nobody gets the fade
    scc.FIRST_TIMER_DOG.update({"ncaaf": 200})
    try:
        assert scc.first_timers(games, "2026-10-01T12:00Z", raw) == {("ncaaf", "145")}
    finally:
        scc.FIRST_TIMER_DOG.clear()


def test_coach_changes_sections():
    """Coaching changes (9/30): the coaching sections of a Wikipedia season page are pulled out (the in-season firings
    ESPN doesn't list); the page names follow Wikipedia's (an en dash for split seasons)."""
    import sports_coach_changes as cc
    txt = "== Standings ==\nx\n== Coaching changes ==\n=== In-season ===\n{| \n| Bulls || Billy Donovan\n|}\n== Notes ==\ny"
    secs = cc.coaching_sections(txt)
    assert len(secs) == 1 and "Billy Donovan" in secs[0] and "In-season" in secs[0] and "Standings" not in secs[0]
    assert "Notes" not in secs[0]
    assert cc.pages(2023)["nba"] == "2023–24 NBA season" and cc.pages(2023)["nfl"] == "2023 NFL season"


def test_firing_study():
    """The firing study (9/30): mid-season coaching changes parsed from Wikipedia's season pages (a dated change for a
    team playing within ~2 weeks on both sides - truly mid-season); a dog that just fired its coach -3 on the Dog's
    score in football / hoops, an NHL team after a change +2."""
    import sports_coach_changes as cc
    g = lambda k, d, h, a: {"id": k, "league": "nfl", "status": "final", "stype": "2", "start": f"2023-{d}T17:00Z",
                            "home": h, "away": a, "home_name": "Raiders" if h == "13" else "Chiefs", "away_name": "Chiefs" if a == "12" else "Raiders"}
    games = {f"g{i}": g(f"g{i}", d, "13", "12") for i, d in enumerate(("10-08", "10-15", "10-22", "10-29", "11-05", "11-12", "11-19"))}
    raw = {"nfl:2023": {"sections": ["== In-season ==\n{|\n|-\n! scope=\"row\" |Las Vegas Raiders\n| Fired\n| After a "
                                    "start, McDaniels was fired on October 31 after one and a half seasons.\n|}",
                                    "* On June 18, 2023, the Las Vegas Raiders fired someone in the offseason."]}}
    got = cc.parse(games, raw)
    assert [(r["team"], r["date"]) for r in got] == [("13", "2023-10-31")]      # (June: not mid-season)
    path = os.path.join(tempfile.mkdtemp(), "f.json")
    json.dump(got, open(path, "w"))
    assert cc.recent("2023-11-20T00:00Z", path) == {("nfl", "13"): "2023-10-31"} and cc.recent("2024-09-20T00:00Z", path) == {}
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "league": "nfl", "market": "ml"}
    assert sports.dog_score({**base, "fired_on": "2023-10-31"}) == sports.dog_score(base) - 3
    assert sports.dog_score({**base, "league": "nhl", "fired_on": "2023-10-31"}) == sports.dog_score({**base, "league": "nhl"}) + 2


def test_leg_lock_label_needs_the_engines_own_read():
    """10/1, the owner: the Flyers' parlay leg said 🔒 LOCK and got blown out - it was 56% only because the price said
    so; the engine's OWN read was against the price. A leg is a LOCK only when the own read backs it (the Lock rule)."""
    flyers = {"odds": -142, "dec": 1.704, "p": 0.5634, "p_market": 0.5635, "edge": -0.04, "edge_own": -0.048,
              "market": "ml", "league": "nhl", "kind": "two", "reasons": ["form"]}
    yanks = {**flyers, "odds": -144, "dec": 1.694, "p_market": 0.5649, "edge_own": -0.0428}
    keep = sports.good
    sports.good = lambda c: True                                           # (both were real plays that night)
    try:
        assert sports.leg_tier(flyers) == "lean" and sports.leg_tier(yanks) == "lock"
        assert sports.leg_tier({k: v for k, v in flyers.items() if k != "edge_own"}) == "lock"   # an old leg, no read: as before
    finally:
        sports.good = keep
    assert not sports.own_agrees(flyers) and sports.own_agrees(yanks)


def test_college_football_pulled_conference_by_conference():
    """10/1 data audit: ESPN's all-of-FBS feed gives only ~25 games a Saturday now (2024-25 had ~500 finished games a
    season, not ~930). The pull goes conference by conference; a game two conferences both list is one game, and one
    conference failing fails the day (so it's retried, never half-saved)."""
    import sports_data as sd
    seen = []
    keep = sd._fetch_one

    def fake(league, day, extra, retries=2, quiet=False):
        seen.append(extra)
        return [{"id": "ncaaf:1"}, {"id": "ncaaf:" + extra}]
    sd._fetch_one = fake
    try:
        rows = sd.fetch_day("ncaaf", datetime(2025, 9, 6))
        n_req, n_opt = len(sd.SPLIT["ncaaf"]), len(sd.SPLIT_OPTIONAL["ncaaf"])
        assert len(seen) == n_req + n_opt and n_req >= 11 and "&groups=8" in seen and "&groups=80" in seen
        assert len(rows) == len(seen) + 1                                   # 'ncaaf:1' once
        sd._fetch_one = lambda league, day, extra, retries=2, quiet=False: None if extra == "&groups=8" else []
        assert sd.fetch_day("ncaaf", datetime(2025, 9, 6)) is None
        # (10/1 audit) the FCS conferences are optional: one failing never fails the day
        sd._fetch_one = lambda league, day, extra, retries=2, quiet=False: None if extra == "&groups=20" else []
        assert sd.fetch_day("ncaaf", datetime(2025, 9, 6)) == []
        seen.clear()
        sd._fetch_one = fake
        sd.fetch_day("nfl", datetime(2025, 9, 7))
        assert seen == [""]                                                 # the other leagues: one call, as before
    finally:
        sd._fetch_one = keep


def test_todays_damage_after_the_last_game():
    """10/1, the owner: the day's units / ROI / record go up top AFTER the last game of the day (never a half-day number)
    and come down at midnight Pacific. Only plays with units count (leans keep their own record)."""
    import sports_dashboard as D
    now = datetime(2026, 10, 1, 22, 0, tzinfo=sports.PT)
    leg = lambda team, res, odds=-130: {"team": team, "odds": odds, "result": res, "game_id": team, "side": "home",
                                       "p": 0.6, "edge_own": 0.05, "dec": 1.77, "p_market": 0.56}
    lock = {"date": "2026-10-01", "kind": "lock", "legs": [leg("Yankees", "won")], "status": "won", "units": 2}
    dog = {"date": "2026-10-01", "kind": "dog", "legs": [leg("Kings", None, 160)], "status": "pending", "units": 1}
    keep = sports.leg_units
    sports.leg_units = lambda p, l: p.get("units", 0)
    try:
        assert D.day_recap([lock, dog], "2026-10-01", [], now) == ""                 # the Kings still going: nothing yet
        dog["legs"][0]["result"], dog["status"] = "lost", "lost"
        h = D.day_recap([lock, dog], "2026-10-01", [], now)
        assert "TODAY" in h and "RESULTS" in h and "DAMAGE" not in h and "1-1" in h and "ROI +18%" in h
        assert "+0.5 UNITS" in h                                                   # 2u won at -130 (+1.54), 1u lost
        assert "+$" in h and "Leans count" not in h                       # dollars too; no note (the owner, 10/1)
        assert "(UNIT PLAYS ONLY)" in h                                      # the owner, 10/1: said right in the header
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
        assert ".dayr-t{{font-size:16px;font-weight:900;color:#fff" in src and ".dayr-u{{color:#fff;font-size:12px;font-weight:900" in src
        assert '<div class="dayr-t">📊 TODAY\'S RESULTS</div><div class="dayr-u">(UNIT PLAYS ONLY)</div>' in h   # its own line, under
    finally:
        sports.leg_units = keep
    until = int(re.search(r'data-until="(\d+)"', h).group(1))
    assert datetime.fromtimestamp(until / 1000, sports.PT) == datetime(2026, 10, 2, 0, 0, tzinfo=sports.PT)   # midnight PT
    assert "Date.now()>+d.dataset.until" in h
    assert D.day_recap([], "2026-10-01", [], now) == ""                          # no plays with units: nothing


def test_leans_show_in_their_sport():
    """10/1, the owner: "the hockey from yesterday's not in here... leans or not, put everything in the correct sport"
    and "leans have to go in our record": a lean (a leg in a parlay, or a lean pick) is listed in its sport marked
    🟡 LEAN and counts in that sport's record and ours (no units: never the bankroll)."""
    import sports_dashboard as D
    leg = lambda team, res, tier: {"team": team, "opp": "Canucks", "odds": -118, "result": res, "league": "nhl",
                                   "game_id": "nhl:" + team, "side": "home", "market": "ml", "tier": tier, "line": None,
                                   "score": "Canucks 6 @ " + team + " 5"}
    picks = [{"date": "2026-09-30", "kind": "two", "status": "lost", "american": 250, "legs": [leg("Flyers", "lost", "lock"),
                                                                                                 leg("Oilers", "lost", "lean")]}]
    h = D._history(picks)
    i = h.index("NHL")
    sec = h[i:h.index("</details>", i)]
    assert "0-2" in sec and "🟡 LEAN · Oilers" in sec and "Flyers ML" in sec    # 10/1 later, the owner: leans
    #                                                    count in our record too (they still carry no units)


def test_coach_history_infobox():
    """10/1: the real coach history (ESPN's is today's coach copied back). A team-season page's infobox -> its head
    coach(es) in order (a mid-season change lists them all); experience counts his seasons BEFORE this one."""
    import sports_coach_history as ch
    w = "{{Infobox NFL season\n| team = Raiders\n| head_coach = [[Jon Gruden]] (fired)<br />[[Rich Bisaccia]] (interim)\n| general_manager = [[Mike Mayock]]\n}}"
    assert ch.coaches(w, "nfl") == ["Jon Gruden", "Rich Bisaccia"]
    assert ch.coaches("{{Infobox MLB season\n| manager = [[Aaron Boone]]\n| owners = x\n}}", "mlb") == ["Aaron Boone"]
    assert ch.page("nba", "Boston Celtics", 2019) == "2019–20 Boston Celtics season"
    hist = {"nfl": {"A": {"2019": ["X"], "2020": ["X"], "2021": ["Y", "Z"]}, "B": {"2021": ["X"]}}}
    ex = ch.experience(hist, "nfl")
    assert ex[("A", 2020)] == ("X", 1, False, False) and ex[("A", 2021)] == ("Y", 0, True, True)
    assert ex[("B", 2021)] == ("X", 2, True, False)                        # a retread: 2 seasons before, new team


def test_dog_studies_10_1():
    """10/1, the owner ("all these dogs win every day - find them"): the 15 dog studies' steady angles go into the
    Dog's score - last results, tired NHL dogs, shot share, run share, the price bands that lose, and big own reads
    capped (traps in the NFL / NBA)."""
    import sports_form as sf
    base = {"odds": 150, "dec": 2.5, "edge": 0.0, "edge_own": 0.0, "p_market": 0.4, "market": "ml"}
    ds = lambda **k: sports.dog_score({**base, **k})
    assert ds(league="nhl", tired_vs_rested=True) == ds(league="nhl") - 3
    assert ds(league="nfl", dog_ctx={"won": True, "opp_won": False}) == ds(league="nfl") + 2
    assert ds(league="ncaab", dog_ctx={"won": False, "opp_won": True}) == ds(league="ncaab") - 3
    assert ds(league="nhl", dog_ctx={"won": False, "opp_won": False}) == ds(league="nhl") + 3.5   # (10/2 study)
    assert ds(league="nba", dog_ctx={"won": True, "opp_won": False}) == ds(league="nba") - 2
    assert ds(league="nhl", dog_ctx={"ss_gap": 0.02}) == ds(league="nhl") + 3
    assert ds(league="nhl", dog_ctx={"ss_gap": -0.05}) == ds(league="nhl") - 3
    assert ds(league="mlb", dog_ctx={"rs_gap": 0.03}) == ds(league="mlb") + 1.5
    big = {"edge_own": 0.5}                                                # own read way over the price
    assert ds(league="nba", **big) < ds(league="mlb", **big)               # NBA / NFL: a big own read is a trap
    assert sports.dog_spots({"league": "mlb", "odds": 230}) == -4 and sports.dog_spots({"league": "mlb", "odds": 160}) == 0
    assert ds(league="nba", dog_ctx={"cw5": 2}) == ds(league="nba") - 3                # round 2: close-win trap
    assert ds(league="ncaab", dog_ctx={"cw5": 3}) == ds(league="ncaab") - 1
    assert ds(league="nhl", dog_ctx={"hits_top": True}) == ds(league="nhl") + 2      # out-hitting people
    assert ds(league="mlb", dog_ctx={"luck_gap": -0.12}) == ds(league="mlb") + 1     # the unlucky dog (watch)
    nba = {f"nba:{k}": {"id": f"nba:{k}", "league": "nba", "status": "final", "stype": "2", "start": f"2026-09-{20 + k}T23:00Z",
                        "home": "A", "away": "B", "home_score": str(100 + (2 if k < 2 else 20)), "away_score": "100",
                        "ls_home": "25,25,25,25", "ls_away": "25,25,25,25"} for k in range(4)}
    assert sf.dog_states(nba, "2026-09-30T12:00Z", team_rows=[])[("nba", "A")]["cw5"] == 2
    games = {f"mlb:{k}": {"id": f"mlb:{k}", "league": "mlb", "status": "final", "stype": "2", "start": f"2026-09-{10 + k}T23:00Z",
                          "home": "A", "away": "B", "home_score": "5", "away_score": "2"} for k in range(8)}
    st = sf.dog_states(games, "2026-09-30T12:00Z", team_rows=[])
    assert st[("mlb", "A")]["won"] is True and abs(st[("mlb", "A")]["rs"] - 40 / 56) < 1e-9 and st[("mlb", "B")]["won"] is False


def test_nutshell_counts_picks_not_cards():
    """10/1, the owner: the brain said 1-4 on a night we went 3-2 (Yankees, Maple Leafs, Padres won; Flyers, Kings
    lost) - it counted the 2-, 3- and 4-leg cards as three L's off one Flyers loss. The day's line counts each PICK
    once, a parlay's picks on their own (the record's rule)."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    nut = src[src.index("# the brain, in a nutshell"):src.index("live_today = any(")]
    assert "day_calls(picks, today)" in nut and 'p["status"] == "won" for p in graded' not in nut
    import sports_dashboard as D
    leg = lambda t, r, tier="lock": {"team": t, "game_id": t, "side": "home", "market": "ml", "result": r, "tier": tier}
    day = [{"date": "2026-09-30", "kind": "lock", "status": "won", "legs": [leg("Yankees", "won")]},
           {"date": "2026-09-30", "kind": "dog", "status": "lost", "legs": [leg("Kings", "lost")]},
           {"date": "2026-09-30", "kind": "four", "status": "lost", "legs": [leg("Yankees", "won"), leg("Flyers", "lost"),
                                                                              leg("Padres", "won", "lean"), leg("Maple Leafs", "won", "lean")]}]
    calls, pending = D.day_calls(day, "2026-09-30")
    assert sorted(calls.values()).count("won") == 3 and list(calls.values()).count("lost") == 2 and not pending
    day[2]["legs"][2]["result"] = None
    assert D.day_calls(day, "2026-09-30")[1]                                # the Padres still going: not done


def test_tennis_watch_reads_yesterdays_scoreboard():
    """10/1, the owner: Volynets (an 11 PM ET match) won and the challenge box still said Algorithm 2 - the watcher only
    read today's + tomorrow's scoreboards, so it never saw a late-night match end (and never graded it). Yesterday's
    is read too now (every 30 seconds)."""
    import sports_tennis as stn
    L = sports_live
    keep = (L._get, stn.parse_espn, L.bovada_fresh, L.PREV_TN[:])
    asked = []
    try:
        L._get = lambda url: (asked.append(url), url)[1]
        prv = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
        stn.parse_espn = lambda url, tour: [{"id": f"{tour}:{'old' if prv in url else 'new'}", "status": "STATUS_FINAL"}]
        L.bovada_fresh = lambda sport: []
        L.PREV_TN[0], L.PREV_TN[1] = 0.0, []
        _, rows, _ = L.tennis_feeds()
        ids = {r["id"] for r in rows}
        assert "wta:old" in ids and "atp:old" in ids, ids                        # yesterday's matches are watched
        L.tennis_feeds()
        assert sum(prv in u for u in asked) == 2                               # (cached: not re-read every second)
    finally:
        L._get, stn.parse_espn, L.bovada_fresh = keep[:3]
        L.PREV_TN[:] = keep[3]


def test_line_history_kept():
    """10/1, the owner: the engine has to KNOW early value - which needs the midweek price, which our data never had
    (only the stale summer open and the close). Every run saves each upcoming game's moneyline when it changes."""
    import sports_data as sd
    d = tempfile.mkdtemp()
    now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    g = {"nfl:1": {"id": "nfl:1", "status": "pre", "start": "2026-10-04T17:00Z", "ml_home": "-148", "ml_away": "124"},
         "nfl:2": {"id": "nfl:2", "status": "final", "start": "2026-09-28T17:00Z", "ml_home": "-110", "ml_away": "-110"},
         "nfl:3": {"id": "nfl:3", "status": "pre", "start": "2026-11-20T17:00Z", "ml_home": "-110", "ml_away": "-110"}}
    assert sd.record_lines(g, now, d) == 1                                  # only the upcoming game in the window
    assert sd.record_lines(g, now + timedelta(hours=1), d) == 0             # no change, no row
    g["nfl:1"]["ml_away"] = "120"                                           # the Jaguars +124 -> +120
    assert sd.record_lines(g, now + timedelta(hours=2), d) == 1
    rows = [json.loads(x) for x in open(os.path.join(d, "2026-10.jsonl"))]
    assert [r["a"] for r in rows] == ["124", "120"] and rows[1]["t"] == "2026-10-01T14:00Z"
    g["nfl:1"]["spread_home"] = "-2.5"                                     # the spread moves, the ml doesn't: kept
    assert sd.record_lines(g, now + timedelta(hours=3), d) == 1
    assert sd.record_lines(g, now + timedelta(hours=4), d) == 0
    rows = [json.loads(x) for x in open(os.path.join(d, "2026-10.jsonl"))]
    assert rows[-1]["sp"] == "-2.5" and rows[-1]["a"] == "120"


def test_team_name_match_is_not_loose():
    """10/1 data audit: the name match fell back to the first word, so 'UC Davis' took any 'UC ...' school's odds and
    'Texas St' the Longhorns'. The rest of the short name has to be in there too."""
    import sports_data as sd
    assert sd._same("Miami OH", "Miami (OH) RedHawks") and sd._same("Chiefs", "Kansas City Chiefs")
    assert sd._same("North Carolina", "North Carolina Tar Heels")
    assert not sd._same("UC Davis", "UC Santa Barbara Gauchos") and not sd._same("Texas St", "Texas Longhorns")
    assert not sd._same("", "Texas Longhorns")


def test_firing_parse_audit_fixes():
    """10/1 data audit: next season's page repeats last season's yearless firing (Staley 12/15/2023 came back as
    12/15/2024) - the repeat goes; and a college row for 'Charleston Southern' / 'USC Upstate' / 'North Carolina A&T'
    never lands on 'Southern' / 'USC' / 'North Carolina'."""
    import sports_coach_changes as cc
    days = ("10-01", "10-08", "10-15", "10-22", "11-05", "11-12", "11-19", "12-01", "12-08", "12-22", "12-29", "01-05")
    games = {}
    for y in (2023, 2024):
        for i, d in enumerate(days):
            yr = y + 1 if d.startswith("01") else y
            games[f"nfl{y}{i}"] = {"id": f"nfl{y}{i}", "league": "nfl", "status": "final", "stype": "2",
                                    "start": f"{yr}-{d}T17:00Z", "home": "24", "away": "1", "home_name": "Chargers", "away_name": "Bears"}
            games[f"cb{y}{i}"] = {"id": f"cb{y}{i}", "league": "ncaab", "status": "final", "stype": "2",
                                   "start": f"{yr}-{d}T17:00Z", "home": "9", "away": "8", "home_name": "Southern", "away_name": "Alcorn St"}
    row = "! scope=\"row\" |Los Angeles Chargers\n| Fired\n| After a start, Staley was fired on December 15 after almost three seasons."
    raw = {"nfl:2023": {"sections": ["== In-season ==\n{|\n|-\n" + row + "\n|}"]},
           "nfl:2024": {"sections": ["== Offseason ==\n{|\n|-\n" + row + "\n|}"]},
           "ncaab:2024": {"sections": ["== In-season ==\n{|\n|-\n| Charleston Southern || Barclay Radebaugh || December 1, 2024 || Fired\n|}"]}}
    got = cc.parse(games, raw)
    assert [(r["league"], r["team"], r["date"]) for r in got] == [("nfl", "24", "2023-12-15")]


def test_early_season_hockey_favorites():
    """9/30 (the owner: 'we gotta tighten up hockey'): NHL favorites in the first 2 weeks of a season won 55%, -4.3%
    (ratings still lean on last year) - weeks 3-4 won 65%. Early on, a hockey favorite moves back the line."""
    keep = dict(sports.SEASON_START)
    try:
        sports.SEASON_START.clear()
        sports.SEASON_START["nhl"] = "2026-09-24"
        fav = {"league": "nhl", "odds": -140, "start": "2026-09-30T23:00Z"}
        assert sports.season_w(fav) == -sports.HOT_W
        assert sports.season_w({**fav, "start": "2026-10-20T23:00Z"}) == 0          # week 4: the best spot - no knock
        assert sports.season_w({**fav, "odds": 150}) == 0 and sports.season_w({**fav, "league": "nba"}) == 0
        games = {"a": {"league": "nhl", "stype": "2", "start": "2026-09-24T23:00Z"},
                 "b": {"league": "nhl", "stype": "1", "start": "2026-09-10T23:00Z"},      # (preseason doesn't count)
                 "c": {"league": "nhl", "stype": "2", "start": "2026-03-15T23:00Z"},      # last season: never the start
                 "d": {"league": "nhl", "stype": "2", "start": "2026-04-12T23:00Z"}}      # (9/30: it picked last March)
        assert sports.season_starts(games, datetime(2026, 9, 30, tzinfo=timezone.utc)) == {"nhl": "2026-09-24"}
    finally:
        sports.SEASON_START.clear(); sports.SEASON_START.update(keep)


def test_early_is_never_game_day_and_leads_game_day():
    """9/30 (the owner: 'we got this game day, not early'): the Kings went up as an 'early' play at 5 PM PT for a 7 PM
    game - an early play is never on its game day. And WE GOT IN EARLY on game day goes just ABOVE the Lock of the Day
    (the owner, 9/30), its own box."""
    import inspect
    import sports_early as se
    import sports_dashboard as d
    assert "start.astimezone(PT).date() <= now.astimezone(PT).date()" in inspect.getsource(se.scan)
    out = d._cards("2026-10-01", [], [("lock", "<L>", 111), ("dog", "<D>", None)], after_lock="<EARLY>")
    assert out.startswith("<EARLY>") and out.index("<EARLY>") < out.index("<L>") < out.index("<D>")   # just above the Lock
    assert d._cards("2026-10-01", [], [("dog", "<D>", None)], after_lock="<EARLY>").startswith("<EARLY>")


def test_sharp_money_line_never_claims_we_were_first():
    """9/30 (the owner: 'we never got in early'): 'The engine had Flyers before the number moved' - the Flyers went
    -125 -> -142 BEFORE we posted at 8 AM. The money-moving line says what's true (the money's on them since the open),
    never that the engine got there first."""
    import inspect
    import sports_breakdown_v24 as b
    src = inspect.getsource(b)
    for bad in ("before the number moved", "saw it first", "were already here"):
        assert bad not in src.replace("never \"the engine had", ""), bad
    assert "The money's been coming in on {us} since the open." in src


def test_odds_history_pull():
    """10/1: the owner paid one month of The Odds API so the engine can learn early football value on REAL midweek
    prices. The pull stays under the plan (20,000 credits, 10 per historical call) and keeps a game only with both
    sides priced."""
    import sys as _s
    _s.path.insert(0, "tools")
    import odds_history as oh
    from datetime import date
    n = sum(len(oh.snaps(s, date(2026, 10, 1))) for s in oh.PLAN)
    assert 0 < n * 10 < 20000 - oh.GUARD
    assert all(datetime.fromisoformat(x.replace("Z", "+00:00")).weekday() in oh.PLAN["americanfootball_nfl"]["days"]
               for x in oh.snaps("americanfootball_nfl", date(2026, 10, 1)))
    p = {"timestamp": "2024-10-01T18:00:00Z", "data": [
        {"id": "e1", "commence_time": "2024-10-06T17:00:00Z", "home_team": "Jacksonville Jaguars",
         "away_team": "Houston Texans", "bookmakers": [{"key": "fanduel", "markets": [{"key": "h2h", "outcomes": [
             {"name": "Jacksonville Jaguars", "price": 124}, {"name": "Houston Texans", "price": -148}]}]}]},
        {"id": "e2", "home_team": "A", "away_team": "B", "bookmakers": []}]}
    r = oh.rows(p, "x")
    assert len(r) == 1 and r[0]["b"] == {"fanduel": [124, -148]} and r[0]["snap"] == "2024-10-01T18:00:00Z"
    # spreads (the owner: "+9.5 that drops to +3.5" - one Tuesday look a week, the close is in our games)
    sp = {"data": [{"id": "e1", "home_team": "Jacksonville Jaguars", "away_team": "Houston Texans", "bookmakers": [
        {"key": "dk", "markets": [{"key": "spreads", "outcomes": [{"name": "Jacksonville Jaguars", "price": -110,
                                                                   "point": 9.5},
                                                                  {"name": "Houston Texans", "price": -110, "point": -9.5}]}]}]}]}
    assert oh.rows(sp, "x", "spreads")[0]["b"] == {"dk": [9.5, -110, -9.5, -110]}
    assert oh.rows(sp, "x") == []                                           # (a moneyline pull never reads spreads)
    assert 0 < sum(len(oh.snaps(s, date(2026, 10, 1), oh.SPREAD_PLAN)) for s in oh.SPREAD_PLAN) * 10 < 3500


def test_challenge_score_turned_to_each_players_side():
    """10/1, the owner: the Patty box's scores 'look fucked up again'. The live scores come from two feeds - ESPN's
    order (p1 first) and our own picks' (OUR player first) - and only the first one said so: a box player listed
    second, or on the other side of one of our picks, showed the other guy's sets (and a WIN as a LOSS). Every score
    now says who's first, and the page turns it to each box's own player."""
    import subprocess
    m = {"id": "atp:1", "p1_name": "Casper Ruud", "p2_name": "Holger Rune", "status": "live"}
    orig = sports_live.stl.score_state
    sports_live.stl.score_state = lambda m_: {"done": [(6, 3), (2, 6)], "games": (5, 1), "pts": None, "server": 1}
    try:
        a, b = sports_live._tennis_score(m, 1), sports_live._tennis_score(m, 2)
    finally:
        sports_live.stl.score_state = orig
    assert a["first"] == 1 and b["first"] == 2 and b["sets"][0] == [3, 6]
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    js = src[src.index("function flip(sc)"):src.index("function called(")].replace("{{", "{").replace("}}", "}")
    assert "sc.p1&&" not in src                                  # (the old rule: only ESPN's order ever got turned)
    if not shutil.which("node"):
        return
    test = js + """
var espn={tennis:true,p1:true,n:["Ruud","Rune"],sets:[[6,3],[2,6],[5,1]],done:2,live:true};
var ours2={tennis:true,first:2,n:["Rune","Ruud"],sets:[[3,6],[6,2],[1,5]],done:2,live:true};
var old={tennis:true,n:["Ruud","Rune"],sets:[[6,3]],done:1,live:true};
var out=[orient(espn,"1").n[0],orient(espn,"2").n[0],orient(ours2,"1").n[0],orient(ours2,"2").n[0],
 orient(ours2,"1").sets[0].join("-"),orient(orient(espn,"2"),"1").n[0],orient(old,"1").n[0],orient(old,"2").n[0]];
console.log(out.join("|"));"""
    path = os.path.join(tempfile.mkdtemp(), "orient.js")
    open(path, "w").write(test)
    r = subprocess.run(["node", path], capture_output=True, text=True)
    assert r.stdout.strip() == "Ruud|Rune|Ruud|Rune|6-3|Ruud|Ruud|Rune", (r.stdout, r.stderr[:300])


def test_six_early_spots():
    """10/1, the owner: "there's only one way to prove anything - you do it." The six early spots from the odds-history
    studies go live small, each with its own record: off a bye vs a team that played (1u), and ½u on hammered early,
    Monday night NFL dogs, East Coast NFL teams flying West, a dog that blew somebody out, and college sides the engine
    likes after the line moved away. Fair prices only (after both teams' last games), never game day, never a side with
    a key player out or questionable."""
    import sports_go4
    _go4 = dict(sports_go4._CACHE)
    sports_go4._CACHE["d"] = {}                  # (no real 4th-down rates leaking into the made-up teams)
    try:
        _six_early_spots()
    finally:
        sports_go4._CACHE.clear(); sports_go4._CACHE.update(_go4)


def _six_early_spots():
    import sports_early as se
    from html import escape
    now = datetime(2026, 10, 6, 18, 0, tzinfo=timezone.utc)                 # a Tuesday
    def gm(gid, lg, start, home, away, hn, an, mh=None, ma=None, status="pre", hs="", as_="", tzo="-5.0", neutral="0"):
        return {"id": gid, "league": lg, "stype": "2", "status": status, "start": start, "home": home, "away": away,
                "home_name": hn, "away_name": an, "ml_home": mh or "", "ml_away": ma or "", "home_score": hs,
                "away_score": as_, "tzo": tzo, "neutral": neutral}
    G = {
        # Bills (B) were off last week (a bye): last game 9/27; the Jets played 10/4. Sunday 10/11: Bills +150
        "n1": gm("n1", "nfl", "2026-09-27T17:00Z", "B", "X", "Bills", "X", status="final", hs="20", as_="17"),
        "n2": gm("n2", "nfl", "2026-10-04T17:00Z", "J", "Y", "Jets", "Y", status="final", hs="24", as_="10"),
        "n3": gm("n3", "nfl", "2026-10-11T17:00Z", "J", "B", "Jets", "Bills", "-170", "150"),
        # Monday night 10/12 (ET): the Rams +130 at the Packers - both played 10/4-10/5
        "m0": gm("m0", "nfl", "2026-10-05T00:20Z", "R", "Z", "Rams", "Z", status="final", hs="27", as_="3", tzo="-8.0"),
        "m1": gm("m1", "nfl", "2026-10-04T17:00Z", "P", "W", "Packers", "W", status="final", hs="10", as_="13"),
        "m2": gm("m2", "nfl", "2026-10-13T00:15Z", "P", "R", "Packers", "Rams", "-150", "130"),
    }
    G["r_home"] = gm("r_home", "nfl", "2026-09-14T20:00Z", "R", "Q", "Rams", "Q", status="final", hs="1", as_="0", tzo="-8.0")
    G["g_home"] = gm("g_home", "nfl", "2026-09-14T17:00Z", "P", "V", "Packers", "V", status="final", hs="1", as_="0", tzo="-6.0")
    def imp(o):
        o = int(o)
        return 100 / (o + 100) if o > 0 else -o / (-o + 100)
    def own_by(lean):                     # the engine's own read: the price's win % + `lean` (its full read, all factors)
        def f(g, side):
            h, a = imp(g["ml_home"]), imp(g["ml_away"])
            p = (h if side == "home" else a) / (h + a)
            return p + lean
        return f
    agree = own_by(0.02)
    se._COACH["exp"] = {}                                                   # (no coach history in the test)
    got = {(c["team"], c["spot"]): c for c in se.spot_scan(G, now, own_of=agree, hist_dir=tempfile.mkdtemp())}
    assert ("Bills", "bye") in got and se.units(got[("Bills", "bye")]) == 1.0
    rams = [c for c in got.values() if c["team"] == "Rams"][0]
    assert "mnf" in rams["spots"] and "blowout" in rams["spots"] and se.units(rams) == 0.5
    assert not any(c["team"] in ("Jets", "Packers") for c in got.values())          # favorites: never these spots
    # 10/1, the owner: "the engine NEVER picks off one factor - it weighs everything." No engine read, or the engine's
    # read fighting the side: no play, whatever the spot. A spot with the engine just at the price: not enough alone.
    assert se.spot_scan(G, now, hist_dir=tempfile.mkdtemp()) == []
    assert not any(c["team"] == "Bills" for c in se.spot_scan(G, now, own_of=own_by(-0.03), hist_dir=tempfile.mkdtemp()))
    flat = {(c["team"], c["spot"]) for c in se.spot_scan(G, now, own_of=own_by(0.0), hist_dir=tempfile.mkdtemp())}
    assert ("Bills", "bye") not in flat and ("Rams", "mnf") not in flat   # the bye alone (+4) < 5; Rams: Monday (+1.5,
    #                                                                     halved 10/1) + blowout (+2) = 3.5 < 5 too
    lift = {(c["team"], c["spot"]) for c in se.spot_scan(G, now, own_of=own_by(0.02), hist_dir=tempfile.mkdtemp())}
    assert ("Rams", "mnf") in lift                                      # ...with the engine 2 pts over the price: in
    # not before last week's games are over (the 10/1 audit: an early price then 'knew' nothing the engine knew)
    early = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)                       # the Jets' game still on
    assert not any(c["team"] == "Bills" for c in se.spot_scan(G, early, own_of=agree, hist_dir=tempfile.mkdtemp()))
    # never on game day
    gd = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)
    assert not any(c["team"] == "Bills" for c in se.spot_scan(G, gd, own_of=agree, hist_dir=tempfile.mkdtemp()))
    # a key player out / questionable on our side: never
    keep = (sd.team_key_out, sd.team_unsure)
    sd.team_key_out = lambda inj, tid, name, lg, maybe=False: [("QB1", "QB", "Out")] if name == "Bills" else []
    sd.team_unsure = lambda inj, tid, name, lg, maybe=False: []
    try:
        assert not any(c["team"] == "Bills" for c in se.spot_scan(G, now, {"nfl": {"x": 1}}, agree, hist_dir=tempfile.mkdtemp()))
    finally:
        sd.team_key_out, sd.team_unsure = keep
    # (10/1 audit) no NFL injury report at all = we can't see who's out: never post blind
    assert not any(c["team"] == "Bills" for c in se.spot_scan(G, now, {"mlb": {}}, agree, hist_dir=tempfile.mkdtemp()))
    src = open(sports.__file__).read()
    assert '| {"nfl", "ncaaf"}' in src                       # the run fetches football's report for the early plays
    # hammered early: the first fair price we recorded vs now (the line history)
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "2026-10.jsonl"), "w") as f:
        f.write(json.dumps({"g": "n3", "t": "2026-10-05T12:00Z", "s": "2026-10-11T17:00Z", "h": "-260", "a": "210"}) + "\n")
    assert "hammered" in [c for c in se.spot_scan(G, now, own_of=agree, hist_dir=d) if c["team"] == "Bills"][0]["spots"]
    # the engine spot (college): the engine likes the side, the price went OUT 2+ since the first fair price
    C = {"c0": gm("c0", "ncaaf", "2026-10-03T19:00Z", "U", "K", "Utah", "K", status="final", hs="20", as_="21"),
         "c1": gm("c1", "ncaaf", "2026-10-03T19:00Z", "T", "L", "TCU", "L", status="final", hs="20", as_="21"),
         "c2": gm("c2", "ncaaf", "2026-10-10T19:00Z", "U", "T", "Utah", "TCU", "-120", "100")}
    d2 = tempfile.mkdtemp()
    with open(os.path.join(d2, "2026-10.jsonl"), "w") as f:
        f.write(json.dumps({"g": "c2", "t": "2026-10-04T12:00Z", "s": "2026-10-10T19:00Z", "h": "-135", "a": "115"}) + "\n")
    own = lambda g, side: 0.58 if side == "home" else 0.42
    got = se.spot_scan(C, now, own_of=own, hist_dir=d2)
    assert got == []                                          # (10/1: a favorite is never an early play - game day)
    C["c2"] = {**C["c2"], "ml_home": "105", "ml_away": "-125"}     # Utah a dog now, out from -115 at the first look
    d3 = tempfile.mkdtemp()
    with open(os.path.join(d3, "2026-10.jsonl"), "w") as f:
        f.write(json.dumps({"g": "c2", "t": "2026-10-04T12:00Z", "s": "2026-10-10T19:00Z", "h": "-115", "a": "-105"}) + "\n")
    got = se.spot_scan(C, now, own_of=own, hist_dir=d3)
    assert [(c["team"], c["spot"]) for c in got] == [("Utah", "engine")]
    with open(os.path.join(d2, "2026-10.jsonl"), "w") as f:              # moved further: TCU now "hammered" too - the
        f.write(json.dumps({"g": "c2", "t": "2026-10-04T12:00Z", "s": "2026-10-10T19:00Z", "h": "-140", "a": "120"}) + "\n")
    assert [c["team"] for c in se.spot_scan(C, now, own_of=own, hist_dir=d2)] == ["Utah"]   # TCU got hammered, but
    #   the engine's read is against TCU - it never takes a side it's fighting
    # the best 3 a week (the owner, 10/1), the most believed spots first; they wait for Tuesday's full slate
    tue = datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc)                   # Tuesday 7 AM PT
    mk = lambda gid, spot, score=0.06, fair="2026-10-05T12:00Z": {"game_id": gid, "spot": spot, "score": score,
                                                                "fair_at": fair}
    cs = [mk("a", "engine", .07), mk("b", "blowout", .05), mk("c", "bye", .11), mk("d", "mnf", .06), mk("e", "mnf", .09)]
    # (the owner, 10/1: no weekly cap - every one that cleared the bar, best total first, posted now - never held)
    assert se.SPOT_MAX_WEEK is None
    assert [c["game_id"] for c in se.pick_spots([dict(c) for c in cs], {"picks": []}, tue)] == ["c", "e", "a", "d", "b"]
    assert len(se.pick_spots([dict(c) for c in cs], {"picks": []}, datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc))) == 5
    keep_cap = se.SPOT_MAX_WEEK                                                  # the cap code still works if it's
    se.SPOT_MAX_WEEK = 2                                                         # ever turned back on
    try:
        _capped_spots(se, cs, mk, tue)
    finally:
        se.SPOT_MAX_WEEK = keep_cap
    _six_early_spots_rest(se, G, now, agree, rams, got, escape)


def _capped_spots(se, cs, mk, tue):
    assert [c["game_id"] for c in se.pick_spots([dict(c) for c in cs], {"picks": []}, tue)] == ["c", "e"]   # 2 a week,
    #                                                           the best weighed totals - never one spot's rank
    posted = {"picks": [{"spot": "bye", "posted": "2026-10-06T13:30Z"}]}
    assert [c["game_id"] for c in se.pick_spots([dict(c) for c in cs], posted, tue)] == ["c"]    # 1 slot left this week
    posted["picks"].append({"spot": "mnf", "posted": "2026-10-06T13:40Z"})
    assert se.pick_spots([dict(c) for c in cs], posted, tue) == []                               # the week's full
    sun = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)
    assert se.pick_spots([dict(c) for c in cs], {"picks": []}, sun) == []      # Sunday: waits for Tuesday's slate...
    closing = mk("z", "blowout", fair="2026-10-02T00:00Z")                   # ...unless its window closes first
    assert [c["game_id"] for c in se.pick_spots([closing], {"picks": []}, sun)] == ["z"]


def _six_early_spots_rest(se, G, now, agree, rams, got, escape):
    late = datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc)                  # the Bills' number went fair Sun 10/4
    assert not any(c["team"] == "Bills" for c in se.spot_scan(G, late, own_of=agree, hist_dir=tempfile.mkdtemp()))   # late
    big = {**G, "n3": {**G["n3"], "ml_away": "260", "ml_home": "-320"}}       # never past +220 (the owner, 10/1)
    assert not any(c["team"] == "Bills" for c in se.spot_scan(big, now, own_of=agree, hist_dir=tempfile.mkdtemp()))
    # the box: the spot's name on the row, each spot's own record
    st = {"picks": [{**rams, "result": "won", "graded_at": "2026-10-13T04:00Z"},
                    {**got[0], "result": None, "posted": "2026-10-06T18:00Z"}]}
    keep_on, se.ON = se.ON, True                                           # (the suite switches the box off)
    try:
        h = se.html(st, escape, now)
    finally:
        se.ON = keep_on
    assert "Utah" in h and "The line moved away from them" in h and "How each spot" in h and "1-0 (+0.65u)" in h


def test_dog_findings_weighed_never_auto():
    """10/1, the owner: "wire in what you believe in - but the engine NEVER picks off one thing, it weighs every factor."
    The findings move the Dog's score (dog_spots) up or down; they never post a pick on their own."""
    base = {"league": "nfl", "odds": 150, "dog_ctx": {}}
    s0 = sports.dog_spots(base)
    assert sports.dog_spots({**base, "dog_more": {"east_west": True}}) == s0 + 3
    assert sports.dog_spots({**base, "dog_more": {"fades": ["ice cold"]}}) == s0 - 3
    assert sports.dog_spots({**base, "dog_more": {"fades": ["coach's first season", "Thursday night"]}}) == s0 - 3
    #   (10/1, the owner: no Thursday-night fade - "a night of football like any other"; a small, noisy sample)
    _se = __import__("sports_early")
    assert "Thursday night" not in _se.FADE_WEIGHT and 'out.append("Thursday night")' not in open(_se.__file__).read()
    cf = {**base, "league": "ncaaf"}
    assert sports.dog_spots({**cf, "dog_more": {"last_margin": 21}}) == sports.dog_spots(cf) + 2
    assert sports.dog_spots({**cf, "dog_more": {"fast": True}}) == sports.dog_spots(cf) - 2
    mlb = {**base, "league": "mlb"}
    assert sports.dog_spots({**mlb, "dog_more": {"series_blowout": True}}) == sports.dog_spots(mlb) + 3
    # the facts, from the schedule: an East Coast team (home time zone -5) at a West Coast game (-8)
    G = {"h1": {"id": "h1", "league": "nfl", "stype": "2", "status": "final", "start": "2026-09-27T17:00Z", "home": "E",
                "away": "Z", "home_name": "Giants", "away_name": "Z", "home_score": "38", "away_score": "10", "tzo": "-5.0"},
         "g1": {"id": "g1", "league": "nfl", "stype": "2", "status": "pre", "start": "2026-10-04T20:05Z", "home": "W",
                "away": "E", "home_name": "Rams", "away_name": "Giants", "tzo": "-8.0"}}
    import sports_early as se
    keep, se._COACH["exp"] = se._COACH.get("exp"), {}                    # (no coach history in the test)
    try:
        mo = sports._dog_more(G, G["g1"], "away", "home", "nfl")
    finally:
        se._COACH.pop("exp", None)
        if keep is not None:
            se._COACH["exp"] = keep
    assert mo["east_west"] is True and mo["last_margin"] == 28 and mo["fades"] == []
    assert sports._dog_more(G, G["g1"], "away", "home", "nhl") == {}   # (10/2: the NBA has its momentum facts now)
    src = open(sports.__file__).read()
    assert '"dog_more": _dog_more(games, g, side, other, lg)' in src     # every candidate carries them - weighed in
    #                                                                     dog_score with everything else, never a pick


def test_pick_logic_bug_check():
    """10/1, the owner: "check how it picks its dogs, its locks, everything - the Astros was a trap and I was right."
    The bug check's findings, each one pinned so it can't come back."""
    own = lambda c, o: {**c, "edge_own": o * c["dec"] - 1}
    # 1. the Astros: a playoff favorite that just lost the last game of the series is weighed in the Lock and the plays
    trap = own({**_cand("astros", -140, 0.62), "stype": "3", "lost_last": True}, 0.62)
    clean = own(_cand("clean", -130, 0.60), 0.60)
    assert sports.make_board([trap, clean])["lock"]["legs"][0]["game_id"] == "clean"
    assert sports.rank_p(trap) < sports.rank_p(clean)
    assert [c["game_id"] for c in sports.plays([trap, clean], ())][0] == "clean"
    # 2. the Lock never falls back to a pick the engine's own read disagrees with (the Flyers)
    fight = own(_cand("flyers", -120, 0.57), 0.53)
    assert sports.make_board([fight])["lock"] is None                 # -> post_board puts up a LEAN Lock instead
    # 3. no units on a bet that loses by the engine's own numbers: -150 needs 60%, the engine says 57%
    neg = own(_cand("neg", -150, 0.62), 0.585)                         # its blended % says 62, its own read 58.5:
    assert not sports.real_value(neg) and sports.plays([neg], ()) == [] and sports.kelly_units(0.585, -150) == 0.0
    assert sports.kelly_units(0.62, -130) > 0
    # 4. the Lock / Dog never on a game already on the board today
    assert sports.make_board([clean], avoid={"clean"})["lock"] is None
    # 5. a lean never carries units (the lean Dog carried 2u)
    assert sports.units_for({"kind": "dog", "lean": True, "legs": [clean]}) == 0
    # 6. a one-game day's Dog follows the Dog rules (the +280 cap, the dog analysis) and its Lock the own read
    big = {**_cand("long", 400, 0.30), "reasons": ["proven spot: x"]}
    keep = sports.good
    sports.good = lambda c: True
    try:
        assert sports.make_board([big])["dog"] is None
        assert sports.make_board([fight])["lock"] is None
    finally:
        sports.good = keep
    # 7. a pending Lock is rebuilt after the day's first game starts (it vanished before)
    src = open(sports.__file__).read()
    assert "(not started or k in pending or k == \"lock\")" in src
    # 8. an early play's slot is never used up by a game already posted
    import sports_early as se
    from datetime import datetime, timezone
    tue = datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc)
    cs = [{"game_id": "a", "spot": "bye", "score": .1, "fair_at": "2026-10-05T12:00Z"},
          {"game_id": "b", "spot": "mnf", "score": .08, "fair_at": "2026-10-05T12:00Z"},
          {"game_id": "c", "spot": "mnf", "score": .07, "fair_at": "2026-10-05T12:00Z"}]
    assert [c["game_id"] for c in se.pick_spots(cs, {"picks": []}, tue, have={"a"})] == ["b", "c"]


def test_dog_gate_uses_everything_we_learned():
    """10/1, the owner: "you wired all that dog knowledge in and it came up with the Red Wings at -142." The knowledge
    sat behind an old gate (a proven spot from before) - a football dog now qualifies on its whole DOG SCORE (the
    engine's read + every spot and fade) at 8+, and its units come from that weighed read. Never one factor alone."""
    import sports_strength
    keep_weak = sports_strength.weak
    sports_strength.weak = lambda lg: False                    # (the gate's own math - never today's strength file)
    try:
        _dog_gate_checks()
    finally:
        sports_strength.weak = keep_weak


def _dog_gate_checks():
    base = {"league": "nfl", "market": "ml", "odds": 150, "dec": 2.5, "p": 0.40, "p_market": 0.40, "edge": 0.0,
            "edge_own": 0.43 * 2.5 - 1, "reasons": ["r"], "dog_ctx": {}, "home": False, "side": "away", "start": "2026-10-04T20:00Z"}
    plain = dict(base)
    assert not sports.dog_gate(plain)                          # the read alone (+3) isn't enough
    spotted = {**base, "dog_more": {"east_west": True, "last_margin": 3}, "dog_ctx": {"opp_won": False}}
    assert sports.dog_gate(spotted) and spotted["dog_p"] > 0.40   # read +3, East-West +3, the favorite lost its last +2
    assert sports.good(spotted) and sports.real_value(spotted)
    assert sports.units_for({"kind": "dog", "legs": [spotted]}) > 0
    cold = {**spotted, "dog_more": {"east_west": True, "fades": ["ice cold"]}}
    assert not sports.dog_gate(cold)                           # a fade takes it back under - weighed, never one factor
    assert not sports.dog_gate({**spotted, "odds": 260, "dec": 3.6})   # never past +220 / the Dog's cap
    assert sports.dog_gate({**spotted, "league": "ncaaf"})       # college football: 4+ (10/1, a lead - UConn +210)
    assert not sports.dog_gate({**base, "league": "ncaaf"})      # its read alone (+3) isn't enough
    far = {**_cand("far", 230, 0.34), "edge_own": 0.40 * sd.decimal(230) - 1}
    assert not sports.viewer_leans([far], ())                   # a lean dog past +220: never (Delaware +230, 10/1)
    hoops = {**base, "league": "ncaab", "edge_own": 0.46 * 2.5 - 1}
    assert sports.dog_gate(hoops)                              # college hoops: its own read 6 points over the price


def test_hockey_dogs_by_the_whole_score():
    """10/1, the owner: "4 in 10 dogs win every day - the engine has to find the one that smacks AND has the most value."
    Hockey dogs on the whole dog score: 6+ qualifies anywhere (+12.8%, 7 of 7 seasons); no real-value dog on the board =
    the best hockey dog of the day whose weighed read still beats its price (2023+ +11.7%)."""
    base = {"league": "nhl", "market": "ml", "odds": 180, "dec": 2.8, "p": 0.343, "p_market": 0.343, "edge": 0.343 * 2.8 - 1,
            "edge_own": 0.343 * 2.8 - 1, "reasons": ["r"], "dog_ctx": {}, "home": False, "side": "away",
            "start": "2026-10-04T20:00Z", "game_id": "hawks", "team": "Hawks", "opp": "x"}
    hot = {**base, "dog_ctx": {"won": False, "opp_won": False, "hits_top": True, "ss_gap": 0.02}}   # +2 +2 +3 = 7
    assert sports.dog_gate(dict(hot))
    assert not sports.dog_gate(dict(base))
    fav = _cand("fav", -130, 0.56, league="nhl")
    mild = {**base, "dog_ctx": {"won": False, "opp_won": False}}                      # +2: 36.3% vs the 35.7% price
    b = sports.make_board([fav, dict(mild)])
    assert b["dog"] and b["dog"]["legs"][0]["game_id"] == "hawks"
    assert sports.units_for({"kind": "dog", "legs": b["dog"]["legs"]}) >= 0.5
    assert sports.make_board([fav, dict(base)])["dog"] is None        # score 0: nothing says it's worth the price
    assert sports.best_hockey_dog([{**mild, "odds": 250, "dec": 3.5}]) is None   # never past +220


def test_calibration_never_goes_under_the_line():
    """10/1, the owner: "college football tomorrow - a lot of locks, a lot of plus money - and the engine finds nothing."
    The record correction (college football -6) was taken off the WHOLE win %, putting every favorite 6-8 points under
    the line's own number (Virginia Tech: 52% vs the line's 60%). It only takes back what the engine said over the line."""
    import inspect
    src = inspect.getsource(sports.candidates)
    assert "never below the line's own number" in src and "p = m_side" in src


def test_lean_is_a_who_wins_call():
    """10/1, the owner: "two picks out of all those games - that's a broken engine." A lean carries no units - it's
    who wins. A favorite the engine's own read still has winning 55%+ is a lean even when the price is a bit high
    (a -142 at own 55%, the line 59%); under 55% it stays off."""
    ps = {**_cand("psu", -142, 0.59, league="ncaaf"), "edge_own": 0.551 * sd.decimal(-142) - 1, "p_market": 0.59}
    assert sports.fighting(ps)
    assert [c["game_id"] for c in sports.viewer_leans([ps], ())] == ["psu"]
    weak = {**ps, "game_id": "w", "edge_own": 0.53 * sd.decimal(-142) - 1}
    assert not sports.viewer_leans([weak], ())
    assert not sports.plays([ps], ())                          # never a UNIT play the engine's read is fighting


def test_there_is_always_a_lock():
    """The owner (CLAUDE.md; 10/1: "we need a Lock of the Day - how many times I gotta tell you"). Nothing clears the
    full Lock test = the pick the engine's own read has winning 56%+ that still beats its price, as a unit Lock; never
    the pricey hockey favorite, never past -150, never one its read is fighting."""
    nt = {**_cand("unt", -112, 0.519, league="ncaaf"), "edge_own": 0.588 * sd.decimal(-112) - 1, "p_market": 0.504}
    wild = {**_cand("wild", -142, 0.576, league="nhl"), "edge_own": 0.571 * sd.decimal(-142) - 1, "p_market": 0.563}
    coin = {**_cand("coin", -108, 0.50, league="nhl"), "edge_own": 0.50 * sd.decimal(-108) - 1}
    b = sports.make_board([nt, wild, coin])
    assert b["lock"] and b["lock"]["legs"][0]["game_id"] == "unt"
    assert sports.units_for({"kind": "lock", "legs": b["lock"]["legs"]}) > 0
    assert sports.make_board([wild, coin])["lock"] is None         # only a near -150 hockey favorite: never that


def test_bug_hunt_10_1():
    """10/1, the owner: "there's 10, 20 bugs in this engine - fix them." The bug hunt's verified ones, pinned."""
    import inspect
    # a game that starts before 8 AM (London NFL, 8:05 first pitch) never wipes out the opening board
    assert 'any(p["date"] == iso and p["status"] != "waiting" for p in picks)' in inspect.getsource(sports.post_board)
    # a -162 favorite we can never post doesn't hide the other side's dog
    fav = {**_cand("g", -162, 0.63, league="nhl"), "side": "home"}
    dog = {**_cand("g", 136, 0.43, league="nhl"), "side": "away", "edge_own": 0.43 * sd.decimal(136) - 1}
    assert [c["side"] for c in sports.one_side([fav, dog])] == ["away"]
    # the night game: a likely winner the price eats is a LEAN, never a 0-unit "LOCK"
    st = {**_cand("pit", -148, 0.572, league="nfl"), "edge_own": 0.593 * sd.decimal(-148) - 1, "p_market": 0.572}
    assert sports.night_pick([st]).get("lean")
    # football opens are summer look-ahead lines: a big move from them isn't "the money running away"
    assert not sports.money_against({**_cand("unt", -112, 0.55, league="ncaaf"), "drift": 0.09})
    assert sports.money_against({**_cand("x", -112, 0.55, league="mlb"), "drift": 0.09}) in (True, False)


def test_hockey_favorites_weigh_the_dog_across():
    """10/1, the owner: "hockey's been killing us" (1-8) - and "stop adding rules, it's weighed in." A hockey favorite's
    read is the line moved by the dog across the ice (its whole dog score) and the early-season weight; it's a pick
    only when that weighed read beats its price."""
    fav = {**_cand("g", -140, 0.57, league="nhl"), "side": "home", "edge_own": 0.565 * sd.decimal(-140) - 1, "p_market": 0.565}
    base_dog = {**_cand("g", 120, 0.43, league="nhl"), "side": "away", "home": False, "edge_own": 0.43 * sd.decimal(120) - 1,
                "p_market": 0.435, "dog_ctx": {}}
    keep = dict(sports.SEASON_START)
    try:
        sports.SEASON_START["nhl"] = "2025-10-07"                # (mid-season: no early weight)
        bad = {**base_dog, "tired_vs_rested": True, "dog_ctx": {"ss_gap": -0.05}}     # tired, out-shot: -6
        f1 = dict(fav); sports.mark_hockey_favorites([f1, dict(bad)])
        assert f1["w_p"] > f1["p_market"] and sports.real_value(f1) and not sports.hockey_fav_bad(f1)
        good_dog = {**base_dog, "dog_ctx": {"won": False, "opp_won": False, "hits_top": True}}    # +4
        f2 = dict(fav); sports.mark_hockey_favorites([f2, dict(good_dog)])
        assert f2["w_p"] < f2["p_market"] and sports.hockey_fav_bad(f2) and not sports.good(f2)
        sports.SEASON_START["nhl"] = "2026-09-20"                # the season's first 2 weeks: weighed down
        f3 = dict(fav); sports.mark_hockey_favorites([f3, dict(bad)])
        assert f3["w_p"] < f1["w_p"]
    finally:
        sports.SEASON_START.clear(); sports.SEASON_START.update(keep)


def test_first_season_coach_on_both_sides_cancels():
    """10/1, the owner: "who's this new coach - is he a vet?" The Browns (Monken, year 1) took the coach's-first-season
    fade while the Steelers (McCarthy, also year 1 in Pittsburgh) weren't checked. Both new = it cancels."""
    import inspect
    src = inspect.getsource(sports._dog_more)
    assert 'se._first_season_coach(lg, g.get(other + "_name"), season)' in src
    import sports_early as se
    keep = se._COACH.get("exp")
    try:
        se._COACH["exp"] = {("Cleveland Browns", 2026): (0, 0, True, 0), ("Pittsburgh Steelers", 2026): (0, 0, True, 0)}
        assert se._first_season_coach("nfl", "Steelers", 2026) and se._first_season_coach("nfl", "Browns", 2026)
    finally:
        se._COACH.pop("exp", None)
        if keep is not None:
            se._COACH["exp"] = keep


def test_money_on_leans_we_like():
    """10/1, the owner: "we can put money on leans we're confident about - it avoids calling them locks." ½u on a lean the
    engine has 55%+ whose own read isn't under the line; it counts in the bankroll; a coin-flip lean stays no units."""
    import sports_dashboard as dash
    like = {**_cand("stl", -130, 0.58, league="nfl"), "edge_own": 0.585 * sd.decimal(-130) - 1, "p_market": 0.55}
    coin = {**_cand("buf", -108, 0.50, league="nhl"), "edge_own": 0.50 * sd.decimal(-108) - 1, "p_market": 0.50}
    assert sports.confident_lean(like) and not sports.confident_lean(coin)
    strong = {**like, "edge_own": 0.66 * sd.decimal(-130) - 1}
    assert sports.lean_units(strong) > sports.lean_units(like) >= 0.5      # sized by its edge, not a flat ½u
    steelers = {**_cand("pit", -148, 0.572, league="nfl"), "edge_own": 0.587 * sd.decimal(-148) - 1, "p_market": 0.572}
    assert not sports.confident_lean(steelers)                 # 58.7% where -148 needs 59.7%: no money on a loser
    pk = {"kind": "lean", "lean": True, "lean_units": sports.CONF_LEAN_UNITS, "legs": [like]}
    assert sports.units_for(pk) == 0.5 and sports.units_for({"kind": "lean", "lean": True, "legs": [coin]}) == 0
    assert "A LEAN WE LIKE" in dash._units_line(0.5, "stl", -130, lean=True) and "LOCK" not in dash._units_line(0.5, "stl", -130, lean=True)
    graded = {**pk, "date": "2026-10-01", "status": "won", "legs": [{**like, "result": "won"}]}
    led = sports.units_ledger([graded])
    assert led["rows"] and led["rows"][0][1] == 0.5                # in the bankroll at ½u


def test_wiring_audit_weights():
    """10/1, the owner: "not everything we studied is wired in - the engine forgets so much." The audit's real edges
    that only lived in early plays or a ranking nudge now WEIGH the read: off a bye, Monday night, an NFL dog off a
    blowout win, and the baseball scoring-drought favorite."""
    base = {"league": "nfl", "odds": 150, "dog_ctx": {}}
    assert sports.dog_spots({**base, "dog_more": {"bye": True}}) == 3
    assert sports.dog_spots({**base, "league": "ncaaf", "dog_more": {"bye": True}}) == 2
    assert sports.dog_spots({**base, "dog_more": {"mnf": True}}) == 1      # (10/1 daily study: halved)
    assert sports.dog_spots({**base, "dog_more": {"last_margin": 21}}) == 2
    fav = {**_cand("nyy", -130, 0.56), "form_state": None}
    keep = sports.overreact
    try:
        sports.overreact = lambda c: True
        c = dict(fav); sports.weigh_mlb_drought([c])
        assert abs(c["p"] - 0.59) < 1e-9 and "12+ innings" in c["reasons"][-1]
    finally:
        sports.overreact = keep


def test_nfl_4th_down_nerve_weighs_the_dog():
    """10/1, the owner: "everything needs to be wired in - coaches, how they play." The NFL style study's one lead: a dog
    whose coach goes for it on 4th down clearly less than the other coach -1 on its score, a clearly bolder one +1."""
    import sports_go4 as g4
    rows = [("CLE", "2026-09-14", True), ("CLE", "2026-09-07", True), ("PIT", "2026-09-14", False),
            ("PIT", "2026-09-07", False)]
    r, league = g4.rates(rows)
    assert r["CLE"] > league > r["PIT"]
    keep = dict(g4._CACHE)
    try:
        g4._CACHE["d"] = {"teams": {"Browns": 0.70, "Steelers": 0.55, "Bears": 0.66}}
        assert g4.gap("Browns", "Steelers") == 0.15 and g4.gap("Browns", "Nobody") is None
        base = {"league": "nfl", "odds": 150, "dog_ctx": {}}
        assert sports.dog_spots({**base, "dog_more": {"go4_gap": 0.15}}) == 1
        assert sports.dog_spots({**base, "dog_more": {"go4_gap": -0.15}}) == -1
        assert sports.dog_spots({**base, "dog_more": {"go4_gap": 0.01}}) == 0
    finally:
        g4._CACHE.clear(); g4._CACHE.update(keep)


def test_the_money_check():
    """10/1, the owner: "build the money check." No pick carries units unless its read beats the REAL price we pay -
    the Steelers at -148 with the engine at 58.7% (needs 59.7%) carry none, whatever kind of pick they are."""
    st = {**_cand("pit", -148, 0.60, league="nfl"), "edge_own": 0.587 * sd.decimal(-148) - 1, "p_market": 0.572}
    assert not sports.beats_price(st)
    for kind in ("lock", "solo", "dog"):
        assert sports.units_for({"kind": kind, "legs": [st]}) == 0
    assert sports.units_for({"kind": "lean", "lean": True, "lean_units": 0.5, "legs": [st]}) == 0
    unt = {**_cand("unt", -112, 0.52, league="ncaaf"), "edge_own": 0.589 * sd.decimal(-112) - 1}
    assert sports.beats_price(unt) and sports.units_for({"kind": "lock", "legs": [unt]}) > 0
    hawks = {**_cand("chi", 180, 0.347, league="nhl"), "dog_p": 0.392}
    assert sports.beats_price(hawks) and sports.units_for({"kind": "dog", "legs": [hawks]}) > 0


def test_believed_leads_weighed_small():
    """10/1, the owner: "the engine needs all the good things we found - even the ones you believe in but couldn't
    prove - weighed against the numbers." The early rounds' smaller leads as small weights on the dog score."""
    base = {"league": "ncaaf", "odds": 150, "dog_ctx": {}, "dec": 2.5, "edge_own": 0.45 * 2.5 - 1, "p_market": 0.40}
    assert sports.dog_spots({**base, "dog_more": {"win_pct": 0.75}}) == 1.5
    assert sports.dog_spots({**base, "dog_more": {"neutral": True}}) == 1.5
    assert sports.dog_spots({**base, "edge_own": 0.38 * 2.5 - 1, "dog_more": {"neutral": True}}) == 0   # the engine
    assert sports.dog_spots({**base, "league": "nfl", "dog_more": {"win_streak": 3}}) == 1               # must like it
    import sports_form
    assert sports_form.PDO_SPAN_D == 60


def test_early_plays_weigh_the_believed_leads():
    """10/1, the owner: "don't forget the early plays - the engine needs all the edges we found, even the unproven
    ones, weighed for the early plays too - and no more than two a week." The early total adds the same small lead
    weights the game-day dog score uses; the 2-a-week cap and the units by edge stay."""
    import sports_early as se
    keep = sports._dog_more
    try:
        sports._dog_more = lambda *a: {"win_pct": 0.75, "conservative": True}
        assert abs(se.lead_weights({}, {}, "away", "home", "ncaaf", 0.45, 0.40) - (0.015 - 0.02)) < 1e-9
        sports._dog_more = lambda *a: {"neutral": True, "win_streak": 4}
        assert abs(se.lead_weights({}, {}, "away", "home", "nfl", 0.45, 0.40) - 0.025) < 1e-9
        assert abs(se.lead_weights({}, {}, "away", "home", "nfl", 0.38, 0.40) - 0.01) < 1e-9   # neutral: engine must like it
    finally:
        sports._dog_more = keep
    assert se.SPOT_MAX_WEEK is None                      # (the owner, 10/1 later: no weekly cap - newest rule wins)


def test_score_picked_dogs_are_lead_sized():
    """10/1, the owner: "4 units on UConn +215 seems like a lot." A dog picked by the dog score (its points rank dogs,
    they aren't proven win %) carries 2u at most."""
    uconn = {**_cand("uconn", 215, 0.31, league="ncaaf"), "dog_p": 0.425}
    assert sports.kelly_units(0.425, 215) > 2 and sports.units_for({"kind": "dog", "legs": [uconn]}) == 2.0


def test_both_teams_hot_never_called_our_heater():
    """10/2, the owner: "Virginia Tech, four straight W's, we don't go against a heater. Well, the other team has four
    straight W's" (Pitt 4-0 too). When the other team's streak is as long, the card says both, and the why never says
    the hot hand is ours."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_breakdown_v24.py")).read()
    i = src.index("their_hot = ")
    blk = src[i:src.index("elif rec_u and n_hot >= 2:", i)]
    assert "their_hot >= n_hot" in blk and "n_hot = 0" in blk and "{them} {their_hot}" in blk


def test_missing_key_players_move_the_own_read():
    """10/2 absence studies (the owner: "if the running backs are out and the wide receivers are out ... that changes
    everything"): key players come from the team's own last games (no look-ahead); a key player out takes the studied
    points off the engine's OWN read - NFL QB 8 / RB 3 / WR 3 / two+ 10, college QB 3 / two+ 5, NHL top scorer 6 /
    top-2 4 / two of top 3 7, NBA 9 / 11; MLB none."""
    import sports_absences as ab
    keep = dict(ab._TEAM)
    try:
        def box(players):
            return [{"player": n, "stats": json.dumps(st)} for n, st in players]
        ab._TEAM["nfl"] = {"1": [("2026-09-%02dT17:00Z" % d, f"nfl:{d}", box([
            ("Q B", {"completions/passingAttempts": "20/30"}), ("R B", {"rushingYards": "90"}),
            ("Wide Ace", {"receivingYards": "80"}), ("Wide Bee", {"receivingYards": "60"}), ("Wide Cee", {"receivingYards": "5"})]))
            for d in (7, 14, 21)]}
        G = {f"nfl:{d}": {"stype": "2"} for d in (7, 14, 21)}
        g = {"league": "nfl", "home": "1", "away": "2", "home_name": "A", "away_name": "B", "start": "2026-09-28T17:00Z"}
        assert ab.key_players(G, "nfl", "1", g["start"]) == {"qb": "Q B", "rb": "R B", "wr": ["Wide Ace", "Wide Bee"]}
        inj = lambda *rows: {"nfl": {"1": list(rows)}}                         # noqa: E731
        assert ab.penalty(G, g, "home", inj(("R B", "RB", "Out")))[0] == 0.03
        assert ab.penalty(G, g, "home", inj(("Q B", "QB", "Out")))[0] == 0.08
        assert ab.penalty(G, g, "home", inj(("R B", "RB", "Out"), ("Wide Ace", "WR", "Doubtful")))[0] == 0.10
        assert ab.penalty(G, g, "home", inj(("Wide Cee", "WR", "Out")))[0] == 0.0           # not a key player
        assert ab.penalty(G, g, "home", inj(("R B", "RB", "Questionable")))[0] == 0.0  # questionable isn't out
        assert ab.penalty(G, g, "home", inj(("Q B", "QB", "Out")), skip_qb=True)[0] == 0.0   # the key_out path has it
    finally:
        ab._TEAM.clear(); ab._TEAM.update(keep)


def test_save_retry_survives_a_push_race():
    """10/2: a run's save died on a push race - 'git rebase --abort' with no rebase going exits 128 and bash -e killed the
    retry loop, so the run's board / grades never reached main. Every workflow's abort is '|| true'."""
    import glob
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows", "*.yml")):
        y = open(f).read()
        assert "git rebase --abort 2>/dev/null;" not in y, f


def test_capper_benchmark_logs_and_grades():
    """10/2: Dr. Bob's free NFL leans - every shape on his page parsed ('Cleveland (+3 -115) or better', 'Arizona (-2.5)
    over NY GIANTS', 'Over (51.5) - CINCINNATI (-2.5)'), logged once with the number he gave, graded off the final next to
    our pick on the same game. A later page never rewrites a logged lean."""
    import sports_capper as cp, tempfile as _t
    lines = ["Pittsburgh Steelers", "@", "Cleveland Browns", "Thu, Oct 1 5:15 PM PT", "Lean – Cleveland (+3 -115) or better",
             "My ratings favor Pittsburgh by just 1.4 points with 38.2 total points.",
             "Arizona Cardinals", "@", "New York Giants", "Sun, Oct 4 10:00 AM PT", "Lean – Arizona (-2.5) over NY GIANTS",
             "Jacksonville Jaguars", "@", "Cincinnati Bengals", "Sun, Oct 4 10:00 AM PT",
             "Lean – Over (51.5) – CINCINNATI (-2.5) vs Jacksonville"]
    page = cp.parse(lines, 2026)
    assert page[0]["leans"] == [{"side": "home", "line": 3.0, "price": -115}] and page[0]["rating"] == ["away", 1.4]
    assert page[1]["leans"][0]["side"] == "away" and page[1]["leans"][0]["line"] == -2.5
    assert [x["side"] for x in page[2]["leans"]] == ["over", "home"]
    games = {"nfl:1": {"id": "nfl:1", "league": "nfl", "start": "2026-10-02T00:15Z", "status": "final", "home_name": "Browns",
                       "away_name": "Steelers", "home_score": "27", "away_score": "24"}}
    picks = [{"kind": "lean", "lean": True, "status": "lost", "legs": [{"league": "nfl", "game_id": "nfl:1", "side": "away", "market": "ml"}]}]
    p = os.path.join(_t.mkdtemp(), "bob.json")
    now = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
    st = cp.run(games, picks, now, path=p, page=page)
    row = st["leans"]["2026-10-01|Pittsburgh Steelers|Cleveland Browns|home"]
    assert row["result"] == "won" and row["us"]["same"] is False and st["record"]["against_us"]["won"] == 1
    assert st["record"]["all"]["won"] == 1 and sum(st["record"]["all"].values()) == 1      # Sunday's not played yet
    page[0]["leans"][0]["line"] = 1.5                                  # he moved it later: the first number stands
    st = cp.run(games, picks, now, path=p, page=page)
    assert st["leans"]["2026-10-01|Pittsburgh Steelers|Cleveland Browns|home"]["line"] == 3.0


def test_fetch_pages_reads_text():
    """10/2: the official availability reports get read on GitHub's servers (tools/fetch_pages.py) - scripts and styles
    stripped, the readable lines kept."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("fp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "fetch_pages.py"))
    fp = importlib.util.module_from_spec(spec); spec.loader.exec_module(fp)
    assert fp.text_of("<p>WR Koby Howard - Out</p><script>var x=1</script><style>p{}</style>") == ["WR Koby Howard - Out"]
    # Dr. Bob's pages keep his leans and margins, not injury words
    assert fp.key_for("https://drbobsports.com/nfl-analysis/").search("Lean: Packers -3.5")
    assert not fp.key_for("https://www.on3.com/x").search("Lean: Packers")
    assert "keep the whole page" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "fetch_pages.py")).read()
    assert fp.key_for("https://web.archive.org/web/2024/https://www.sportsoddshistory.com/nba-main/") is None   # odds tables whole


def test_same_board_posted_twice_merges_to_one():
    """10/2: two engine runs posted the same board 8 minutes apart; the merge keyed picks by their post time, so the
    dashboard showed every pick twice. The same day + kind + round + games is one pick - the first one posted stays."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("mj", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "merge_json.py"))
    mj = importlib.util.module_from_spec(spec); spec.loader.exec_module(mj)
    leg = {"game_id": "nhl:1", "side": "away", "market": "ml"}
    a = {"date": "2026-10-02", "kind": "dog", "status": "open", "posted": "2026-10-02T15:33Z", "legs": [leg]}
    b = {**a, "posted": "2026-10-02T15:41Z"}
    out = mj.merge_picks([b], [a])
    assert len(out) == 1 and out[0]["posted"] == "2026-10-02T15:33Z"
    c = {**a, "legs": [{**leg, "game_id": "nhl:2"}], "kind": "lean"}
    assert len(mj.merge_picks([a], [c])) == 2


def test_no_forced_lock():
    """10/2, the owner: "there doesn't always have to be a lock ... if we put the lock, we put units on it, and we
    potentially lose units - you make the call." A Lock only when the engine's read beats the price; the forced backup
    (near_lock) is off - it lost 17% flat over 78 replay days. The Lock spot says so."""
    import sports_dashboard as d
    assert sports.FORCE_LOCK is False
    under = {**_cand("u", -130, 0.54, league="ncaaf"), "game_id": "u", "edge_own": -0.02, "reasons": ["the stronger team"]}
    assert not sports.make_board([under]).get("lock")
    assert "No Lock of the Day today" in d._pick_card("lock", None)


def test_always_a_lock_even_under_the_floor():
    """10/2: Virginia Tech moved -135 -> -130, fell under the backup Lock's floor, and the board went up with NO Lock.
    There's ALWAYS a Lock (the owner): the likeliest winner the engine isn't fighting, never past -150, never blind."""
    cs = [{**_cand("vt", -130, 0.54, league="ncaaf"), "game_id": "vt"},
          {**_cand("rw", -130, 0.58, league="nhl"), "game_id": "rw"},
          {**_cand("big", -190, 0.65, league="nhl"), "game_id": "big"},
          {**_cand("blind", -120, 0.6, league="ncaaf"), "game_id": "blind", "waiting": ["Idaho injury report (not in our data)"]}]
    b = sports.last_lock(cs)
    assert b["legs"][0]["game_id"] == "rw" and b["legs"][0]["near_price"]
    assert sports.units_for({"date": "2026-10-03", "kind": "lock", "status": "open", "legs": b["legs"]}) == 0.5
    assert sports.last_lock(cs, avoid={"rw"})["legs"][0]["game_id"] == "vt"


def test_board_goes_up_at_8_sharp():
    """10/2, the owner's friend: "the board doesn't usually go up till 9." The 7:44 / 7:47 runs pull and check
    everything, then wait and post at 8:00 sharp."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports.py")).read()
    assert "local.minute >= BOARD_EARLY_MIN" in src and 40 <= sports.BOARD_EARLY_MIN < 60
    wf = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows", "sports.yml")).read()
    assert '"44,47 14,15 * * *"' in wf


def test_running_on_fumes_only_on_a_back_to_back():
    """10/2: the Jets card said 'Bruins are running on fumes tonight' - the Bruins had two nights off. 'Better rested'
    never says fumes or 'played last night'; only a real back-to-back does."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_breakdown_v24.py")).read()
    i = src.index('pools.append(("w_rest"')
    block = src[i:src.index("elif r ==", i)]
    rested = block[block.index('if r != "better rested" else'):]
    assert "fumes" not in rested and "last night" not in rested and "extra rest" in rested


def test_board_always_has_lock_dog_three_leans_with_injuries_named():
    """10/2, the owner: "we need a lock, we need a dog, and we need three leans, no matter what." With the injury reports
    in, a banged-up side can't carry units - but the backup Lock still goes up (it can be that side, ½u) and a lean can be
    that side, and the card names who's out."""
    g = {"league": "ncaaf", "home": "259", "away": "221", "home_name": "Virginia Tech", "away_name": "Pitt"}
    inj = {"ncaaf": {"259": [("Justin Terry", "OL", "Out"), ("Emmett Laws", "DL", "Out"),
                             ("Bill Davis", "RB", "Questionable")]}}
    line = sports.injury_line(g, "home", inj)
    assert line.startswith("🚑 Virginia Tech out: OL Justin Terry, DL Emmett Laws") and "RB Bill Davis" in line
    assert sports.injury_line(g, "away", inj) == ""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports.py")).read()
    assert "best = make_board(all_cands, lock_game" in src         # the Lock falls back to every side we have data on
    assert 'pool(all_cands if kind == "lean" else cands' in src     # the leans fill from every side we have data on
    assert "slate_check(games, raw_cands, day, now, model=model)" in src        # (10/2: a no-units / blind side isn't 'never looked at')
    assert '"(not in our data)" in w' in src                         # (a blind game is off the table, not 'waiting')
    assert "all_cands = [c for c in all_cands if no_gap(c)]" in src  # every safety filter covers the leans' pool too
    assert 'all_cands = [c for c in all_cands if ours.get(c["game_id"], c["side"]) == c["side"]]' in src
    assert 'night_pick([c for c in all_cands if c["game_id"] == gid])' in src
    c = {**_cand("n", 120, 0.6, league="nfl"), "game_id": "n", "hurt": ["A", "B"]}
    pk = sports.night_pick([c])
    assert pk and pk.get("lean"), "a banged-up night-football side is its game's lean, never a unit play"


def test_no_blind_picks_and_official_reports():
    """10/2, the owner: "our engine needs to have all the data". ESPN's college feed listed 3 teams, so 'nobody listed'
    meant UNKNOWN for Virginia Tech, Pitt, Penn State... A college team the data doesn't cover holds its game; the
    official availability reports we keep count as coverage; a side with 2+ players out (or 4+ questionable) the engine
    doesn't weigh carries no units."""
    import json as _j, tempfile as _t
    keep = sd.OFFICIAL_PATH
    try:
        sd.OFFICIAL_PATH = os.path.join(_t.mkdtemp(), "o.json")
        today = (datetime.now(timezone.utc) - timedelta(hours=7)).date().isoformat()
        _j.dump({today: {"ncaaf": {"259": {"players": [["Justin Terry", "OL", "Out"], ["Emmett Laws", "DL", "Out"]]}}}},
                open(sd.OFFICIAL_PATH, "w"))
        assert sd.official("ncaaf") == {"259": [("Justin Terry", "OL", "Out"), ("Emmett Laws", "DL", "Out")]}
        inj = {"99": [("Somebody", "QB", "Out")], **sd.official("ncaaf")}
        g = {"league": "ncaaf", "home": "259", "away": "221", "home_name": "Virginia Tech", "away_name": "Pitt"}
        assert sd.covered(inj, "ncaaf", "259") and not sd.covered(inj, "ncaaf", "221")
        assert any("Pitt injury report" in w for w in sports.waiting_on(g, {"ncaaf": inj}))
        assert sd.covered({"1": []}, "nhl", "5")                  # a pro feed: a team not listed = nobody hurt
        import sports_absences as _A
        keep_t = dict(_A._TEAM)
        _A._TEAM["ncaaf"] = {}                                     # (no box scores: the plain 2+ out rule - 10/3)
        assert sports.hurt(g, "home", {"ncaaf": inj}) == ["Justin Terry", "Emmett Laws"]
        one = {"259": [("Justin Terry", "OL", "Out")]}
        assert sports.hurt(g, "home", {"ncaaf": one}) == []       # one player out: weighed by the price, units stay
        _A._TEAM.clear(); _A._TEAM.update(keep_t)
    finally:
        sd.OFFICIAL_PATH = keep


def test_fill_lean_skips_a_team_missing_players():
    """10/2: the Red Wings fill lean had Dylan Larkin OUT, the Jets fill lean Connor Hellebuyck (their starting goalie)
    suspended - the engine weighs neither. A fill lean whose team has anyone out / doubtful, or a key player suspended,
    doesn't go up; injured-reserve depth players don't stop it."""
    g = {"league": "nhl", "home": "1", "away": "2", "home_name": "Red Wings", "away_name": "Rangers"}
    inj = {"nhl": {"1": [("Dylan Larkin", "C", "Out"), ("Carter Bear", "LW", "Injured Reserve")],
                   "2": [("Aidan Thompson", "C", "Injured Reserve")],
                   "3": [("Connor Hellebuyck", "G", "Suspension")]}}
    assert sports.fill_hurt(g, "home", inj) == ["Dylan Larkin"] and sports.fill_hurt(g, "away", inj) == []
    j = {"league": "nhl", "home": "3", "away": "2", "home_name": "Jets", "away_name": "Bruins"}
    assert sports.fill_hurt(j, "home", inj) == ["Connor Hellebuyck"]
    cs = [{**_cand("rw", -130, 0.576, league="nhl"), "game_id": "rw", "w_p": 0.55}]
    assert sports.viewer_leans(cs, set())[0].get("fill") is True


def test_lean_waits_only_on_a_verified_starter():
    """10/2, the owner: "the player listed is questionable. It's not a starting goalie ... it doesn't change the game."
    A lean (no money) waits only on a goalie our box scores show starting; a unit play keeps the safety (an unknown
    goalie still holds it)."""
    keep = sd.STARTER_OF
    try:
        sd.STARTER_OF = lambda lg, tid, name: None           # the season just started: we don't know him yet
        g = {"league": "nhl", "home": "1", "away": "2", "home_name": "Red Wings", "away_name": "Rangers"}
        inj = {"nhl": {"1": [("Cam Talbot", "G", "Questionable")]}}
        assert sports.waiting_on(g, inj)                         # a unit play: held
        assert sports.waiting_on(g, inj, maybe=False) == []      # a lean: posts
        sd.STARTER_OF = lambda lg, tid, name: True           # the real starter questionable: the lean waits too
        assert sports.waiting_on(g, inj, maybe=False)
    finally:
        sd.STARTER_OF = keep


def test_reviews_say_what_happened():
    """10/2, the owner: "our reviews should never be vague" - 'Not even close - New Mexico St smacked Western KY' had no
    score; 'Lost 6-0. Never close. Brutal.' no fact. Every game review gets who led at the half / after two periods and
    the final (only the half when the score's already there); nothing when we don't hold the period scores."""
    import sports_dashboard as d
    wk = {"league": "ncaaf", "side": "away", "team": "Western KY", "opp": "New Mexico St",
          "flow": {"a": "3,0,7,3", "h": "10,10,7,7"}}
    assert d.game_fact(wk) == "New Mexico St led 20-3 at the half and won 34-13."
    bh = {"league": "nhl", "side": "away", "team": "Blackhawks", "opp": "Mammoth", "flow": {"a": "0,0,0", "h": "1,2,3"}}
    assert d.with_fact("Lost 6-0. Brutal.", d.game_fact(bh)) == "Lost 6-0. Brutal. Mammoth led 3-0 after two periods."
    nt = {"league": "ncaaf", "side": "away", "team": "North Texas", "opp": "Tulsa", "flow": {"a": "7,10,14,14", "h": "14,10,10,10"}}
    assert d.game_fact(nt) == "Tulsa led 24-17 at the half, then North Texas won 45-44."
    assert d.game_fact({**wk, "flow": {}}) is None and d.with_fact("Won 3-2.", None) == "Won 3-2."


def test_leans_fill_the_board_to_five():
    """10/2, the owner: "we need five picks so we can have two more leans." A hockey favorite whose price isn't value is
    still a who-wins lean (no units) when the board is short - never past -150, never fighting its own read."""
    def hk(gid, odds, p):
        return {**_cand(gid, odds, p, league="nhl"), "game_id": gid, "w_p": p - 0.03, "reasons": ["the stronger team"]}
    cs = [hk("rw", -130, 0.576), hk("jets", -122, 0.525), hk("big", -190, 0.63)]
    assert all(sports.hockey_fav_bad(c) for c in cs[:2])
    got = [c["game_id"] for c in sports.viewer_leans(cs, set())]
    assert got == ["rw", "jets"]                              # the likeliest first; -190 is past -150
    assert sports.viewer_leans(cs, {"rw", "jets"}) == []


def test_stale_summer_open_replaced():
    """10/2, the owner: "how could Penn State open at -278?" ESPN's college open was a summer lookahead line; the
    first price we saw that week was -142 and it never moved. The open becomes the first price we saw (12+ hours out),
    so nothing reads it as money moving; a game we only saw late, and past games, keep theirs."""
    G = {"psu": {"status": "pre", "start": "2026-10-03T00:00Z", "home_name": "Northwestern", "away_name": "Penn State",
                 "ml_home": "120", "ml_away": "-142", "ml_home_open": "225", "ml_away_open": "-278"},
         "late": {"status": "pre", "start": "2026-10-01T12:00Z", "ml_home": "-150", "ml_away": "130",
                  "ml_home_open": "-200", "ml_away_open": "170"},
         "done": {"status": "final", "start": "2026-10-01T00:00Z", "ml_home_open": "-300", "ml_away_open": "250"},
         "ok": {"status": "pre", "start": "2026-10-03T00:00Z", "ml_home": "-110", "ml_away": "-110",
                "ml_home_open": "-115", "ml_away_open": "-105"}}
    hist = {"psu": [("2026-10-01T05:54Z", 120, -142, "", None)], "late": [("2026-10-01T05:54Z", -150, 130, "", None)],
            "done": [("2026-09-28T05:54Z", -150, 130, "", None)], "ok": [("2026-10-01T05:54Z", -112, -108, "", None)]}
    fixed = sports.fix_opens(G, hist)
    assert G["psu"]["ml_away_open"] == "-142" and abs(sports.sm.line_move(G["psu"])) < 1e-9 and len(fixed) == 1
    assert G["late"]["ml_home_open"] == "-200" and G["done"]["ml_home_open"] == "-300" and G["ok"]["ml_home_open"] == "-115"


def test_close_record_and_journal():
    """10/2, the owner: "a record of everything so we can go back and improve the engine always". Every graded pick's
    price vs the close (the last pre-game price - never an in-game line, never a guess) and the journal row: the
    engine's reads, units, injuries seen, the score."""
    import sports_clv
    G = {"g1": {"league": "ncaaf", "start": "2026-10-02T01:00Z", "status": "final", "home_score": "44", "away_score": "45",
                "ml_home": "130", "ml_away": "-160", "odds_time": "2026-10-02T01:20Z"},
         "g2": {"league": "nhl", "start": "2026-10-02T01:00Z", "status": "final", "home_score": "6", "away_score": "0",
                "ml_away": "190", "ml_home": "-230", "odds_time": "2026-10-02T03:00Z"}}
    hist = {"g1": [("2026-10-01T20:00Z", 100, -120, "", None), ("2026-10-02T00:58Z", 125, -148, "", None)]}
    l1 = {**_cand("g1", -118, 0.52, league="ncaaf"), "game_id": "g1", "side": "away", "team": "North Texas",
          "opp": "Tulsa", "key_seen": {}}
    l2 = {**_cand("g2", 180, 0.35, league="nhl"), "game_id": "g2", "side": "away", "team": "Blackhawks"}
    picks = [{"date": "2026-10-01", "kind": "lock", "status": "won", "units": 3.0, "legs": [l1]},
             {"date": "2026-10-01", "kind": "dog", "status": "lost", "units": 0.5, "legs": [l2]}]
    st, journal = sports_clv.build(picks, G, hist)
    assert st["all"]["n"] == 1 and st["picks"][0]["close"] == -148 and st["picks"][0]["pts"] > 5   # g2: saved after the start
    assert st["lock_by_size"]["2-4u"]["beat"] == 1
    j = {r["team"]: r for r in journal}
    assert j["North Texas"]["score"] == "45-44" and j["North Texas"]["margin"] == 1 and j["North Texas"]["units"] == 3.0
    assert j["North Texas"]["beat_close_pts"] > 5 and j["Blackhawks"]["close"] is None and j["Blackhawks"]["pnl_units"] == -0.5


def test_backup_lock_says_so():
    """10/2, the owner: a day nothing meets the Lock of the Day standard has no Lock of the Day - the best call goes up
    titled just LOCK, with its own box above it saying so. A real Lock of the Day never shows the box."""
    import sports_dashboard
    leg = {**_cand("vt", -135, 0.55, league="ncaaf"), "game_id": "vt", "team": "Virginia Tech", "opp": "Pitt",
           "near_price": True, "start": "2026-10-02T23:30Z", "breakdown": []}
    pk = {"date": "2026-10-02", "kind": "lock", "status": "open", "legs": [leg], "dec": leg["dec"], "american": -135,
          "stake": 100, "p_hit": 0.55}
    html = sports_dashboard._pick_card("lock", pk)
    assert 'backup-note' in html and any(x[:30] in html for x in sports_dashboard.BACKUP_LOCK)
    assert html.index("backup-note") < html.index("<section") and "LOCK OF THE DAY" not in html
    leg2 = {**leg, "near_price": False}
    real = sports_dashboard._pick_card("lock", {**pk, "legs": [leg2]})
    assert "backup-note" not in real and "LOCK OF THE DAY" in real


def test_checker_checks_itself_and_the_sizing():
    """10/2, the owner: "make sure our checker is working properly" / "is our sizing system checked properly?" The
    self-test feeds every check made-up broken data and each one has to catch it; the sizing check flags any pick off
    the unit system; the backup Lock is ½u; a public split from a failed pull is never quoted as today's."""
    assert sports.checker_selftest() == []
    leg = {**_cand("s", 120, 0.5), "game_id": "s"}
    assert sports.sizing_check([{"date": "2026-10-02", "kind": "play", "status": "open", "legs": [leg]}]) == []
    assert sports.sizing_check([{"date": "2026-10-02", "kind": "dog", "status": "open", "legs": [leg]}]) == []
    near = {**_cand("n", -140, 0.56), "game_id": "n", "near_price": True}
    assert sports.units_for({"date": "2026-10-02", "kind": "lock", "status": "open", "legs": [near]}) == 0.5
    import sports_public
    now = datetime(2026, 10, 2, 15, tzinfo=timezone.utc)
    assert sports_public.fresh({"at": "2026-10-02T14:00Z"}, now) and not sports_public.fresh({"at": ""}, now)
    assert not sports_public.fresh({"at": "2026-10-01T20:00Z"}, now)
    assert sports_public.splits_for("g", live={"g": {"at": "", "ml_home_m": 70}}, hist={}) is None


def test_question_box_knows_no_forced_lock():
    """10/2: the question box's rules still said 'Lock of the Day every day', '56%+ = LOCK' and posted parlays - asked
    'what would the Lock have been', it could crown a lean (Virginia Tech -130). It now knows: no Lock = no Lock."""
    w = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers", "ask", "src", "index.js")).read()
    assert "NO FORCED LOCK" in w and "however it's worded" in w and '"best Lock"' in w and "56%+ = LOCK" not in w and "3-leg, 4-leg" not in w
    assert "what it would have been" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()


def test_futures_price_log():
    """10/3 (the owner: futures): once a day the engine saves every title / conference futures price ESPN carries -
    team markets only (never MVPs / player awards), the first book, the season that has them; once a day only."""
    import sports_futures as F, tempfile as _t
    js = {"items": [
        {"id": 2567, "name": "NBA - Western Conference - Winner", "futures": [{"provider": {"name": "DraftKings"}, "books": [
            {"team": {"$ref": "http://x/seasons/2027/teams/22?lang=en"}, "value": "+4000"},
            {"team": {"$ref": "http://x/seasons/2027/teams/25?lang=en"}, "value": "+145"}]}]},
        {"id": 1, "name": "NBA - MVP", "futures": [{"provider": {"name": "DraftKings"}, "books": [
            {"athlete": {"$ref": "http://x/athletes/1"}, "value": "+300"}]}]}]}
    mk = F.parse(js)
    assert list(mk) == ["NBA - Western Conference - Winner"] and mk["NBA - Western Conference - Winner"]["prices"] == {"22": 4000, "25": 145}
    asked = []
    def get(url):
        asked.append(url)
        if "/nba/seasons/2027/" in url:
            return js
        raise OSError("404")
    d = _t.mkdtemp()
    now = datetime(2026, 10, 3, 15, tzinfo=timezone.utc)                  # 8 AM PT
    f = F.run(now, path=d, get=get)
    st = json.load(open(f))
    assert st["leagues"]["nba"]["season"] == 2027 and "nhl" not in st["leagues"]
    assert F.run(now, path=d, get=get) is None                            # once a day
    assert F.run(datetime(2026, 10, 4, 12, tzinfo=timezone.utc), path=d, get=get) is None   # 5 AM PT: not yet


def test_brain_rough_day_but_green():
    """10/2 (the owner): Virginia Tech, the Red Wings and the Jets lost as leans, the Blues Dog (+154, 1u) was the
    only bet with money on it and cashed - the brain says it was a rough day but we stay in the green. A losing day
    with the money plays down stays the plain rough-day line; nothing until every unit play is graded."""
    import sports_dashboard as D
    leg = lambda team, odds, res, lg="nhl": {"team": team, "odds": odds, "result": res, "league": lg, "game_id": team,
                                             "side": "home", "market": "ml", "start": "2026-10-02T23:00Z", "p": 0.5}
    pk = lambda kind, team, odds, res, lean: {"date": "2026-10-02", "kind": kind, "status": res, "lean": lean,
                                               "american": odds, "dec": 1 + (odds / 100 if odds > 0 else 100 / -odds),
                                               "legs": [leg(team, odds, res)], "units": 0 if lean else 1.0, "stake": 100,
                                               "posted": "2026-10-02T15:00Z", "settled": "2026-10-03T03:00Z"}
    picks = [pk("dog", "Blues", 154, "won", False), pk("lean", "Virginia Tech", -130, "lost", True),
             pk("lean", "Red Wings", -130, "lost", True), pk("lean", "Jets", -122, "lost", True)]
    line = D.green_day(picks, "2026-10-02", 1, 3, 0, early=[])
    assert "rough" in line and "Blues (+154)" in line and "+1.5u" in line and "green" in line, line
    picks[0]["status"] = picks[0]["legs"][0]["result"] = "lost"
    assert D.green_day(picks, "2026-10-02", 0, 4, 0, early=[]) == ""        # the money plays lost: no green line
    picks[0]["status"], picks[0]["legs"][0]["result"] = "open", None
    assert D.green_day(picks, "2026-10-02", 0, 3, 0, early=[]) == ""        # the Dog still playing: not yet


def test_two_records_unit_plays_and_leans():
    """10/2 (the owner): no overall record - "people get the wrong impression if they look at the overall record and
    it's shit". Two records: 💰 the unit plays (every Lock / Dog / value play / early play - "the good bets we put
    money on": W-L, units, ROI) and 🟡 the leans (the only picks without units)."""
    import sports_dashboard as D
    leg = lambda team, odds, res: {"team": team, "odds": odds, "result": res, "league": "nhl", "game_id": team,
                                   "side": "home", "market": "ml", "start": "2026-10-02T23:00Z", "p": 0.5}
    pk = lambda kind, team, odds, res, lean: {"date": "2026-10-02", "kind": kind, "status": res, "lean": lean,
                                               "american": odds, "dec": 1 + (odds / 100 if odds > 0 else 100 / -odds),
                                               "legs": [leg(team, odds, res)], "units": 0 if lean else 1.0, "stake": 100,
                                               "posted": "2026-10-02T15:00Z", "settled": "2026-10-03T03:00Z"}
    picks = [pk("dog", "Blues", 154, "won", False), pk("lean", "Jets", -122, "lost", True)]
    h = D.unit_record(picks, "2026-10-02", early=[])
    assert "UNIT PLAYS RECORD" in h and ">1-0<" in h and "+1.5 UNITS" in h and "The good bets we put money on" in h
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert "OVERALL RECORD" not in src and "OVERALL · LEANS" not in src and "🟡 LEANS RECORD" in src
    assert "today {ltw}-{ltl}" not in src                                  # (the owner: no 'today' line on the leans)
    assert ".ovu .ovr-t,.ovl .ovr-t{{color:#fff;font-weight:900}}" in src and src.count('class="ovr-s ovw"') == 2   # bold white


def test_regrade_window_outlasts_a_lagging_results_feed():
    """10/2: the Blues won 4-0 (the Dog, 1u) but ESPN's results feed said 'live' for 20+ minutes after the final - the
    watcher's 20-minute re-grade window ran out and TODAY'S RESULTS never showed. It keeps re-grading for an hour."""
    assert sports_live.REGRADE_S >= 60 * 60


def test_question_box_note():
    """10/3 (the owner): "delete 'ask me whatever the fuck' and leave the rest"."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert "whatever the fuck" not in src and "Tap in! No stupid shit though. Ain't nobody got time for that." in src


def test_slate_check_skipped_on_purpose_never_holds():
    """10/3: Saturday's 8 AM board was held till 8:47 - ten FCS / Ivy games (Brown @ Rhode Island, Penn @ Dartmouth...)
    'priced but the engine never looked at it'. It did: the model knows too little about those teams, so it skips them
    on purpose. Those (and games starting too soon) never hold the board; a real miss still does."""
    import tempfile as _t
    from datetime import date as _d
    now = datetime(2026, 10, 3, 15, 1, tzinfo=timezone.utc)
    g = lambda gid, away, home, start: {"id": gid, "league": "ncaaf", "stype": "2", "status": "pre", "start": start,
                                        "away_name": away, "home_name": home, "ml_home": "-150", "ml_away": "130"}
    games = {"a": g("a", "Brown", "Rhode Island", "2026-10-03T19:00Z"), "b": g("b", "Ohio State", "Illinois", "2026-10-03T19:00Z"),
             "c": g("c", "Penn", "Dartmouth", "2026-10-03T15:05Z")}
    class E:
        def features(self, gg):
            return {"known": 0 if gg["id"] == "a" else 99}
    keep = (sports._ELO.copy(), sports.SLATE_PATH)
    sports._ELO.update(ref=games, elo={"ncaaf": E()})
    sports.SLATE_PATH = os.path.join(_t.mkdtemp(), "slate.json")
    try:
        probs = sports.slate_check(games, [], _d(2026, 10, 3), now, errors=[], model={"params": {}})
    finally:
        sports._ELO.clear(); sports._ELO.update(keep[0]); sports.SLATE_PATH = keep[1]
    assert probs == ["Ohio State @ Illinois (NCAAF): priced but the engine never looked at it"], probs


def test_hurt_counts_only_players_who_play():
    """10/3 (the owner): no college picks on a huge Saturday - college availability reports list backup linemen,
    redshirts and walk-ons, so 51 of 52 covered teams tripped '2+ out, no units'. Football now counts only players
    who actually play (the team's last 3 box scores: QB, top 2 ball carriers, top 4 catchers, top 11 tacklers); a team
    with no box scores keeps the old rule."""
    import sports_absences as A
    keep = dict(A._TEAM)
    rows = lambda gid, start: [
        {"gid": gid, "start": start, "team": "1", "player": "Star Back", "stats": '{"rushingAttempts":"20"}'},
        {"gid": gid, "start": start, "team": "1", "player": "Top Wideout", "stats": '{"receptions":"8"}'},
        {"gid": gid, "start": start, "team": "1", "player": "Bench Guy", "stats": '{"totalTackles":"0"}'}]
    A._TEAM["ncaaf"] = {"1": [("2026-09-20T19:00Z", "g1", rows("g1", "2026-09-20T19:00Z"))]}
    try:
        g = {"league": "ncaaf", "home": "1", "home_name": "State", "away": "2", "away_name": "Tech", "start": "2026-10-03T19:00Z"}
        rep = lambda ps: {"ncaaf": {"1": ps}}
        walkons = [("Walk On", "OL", "Out"), ("Red Shirt", "DL", "Out"), ("Bench Guy", "LB", "Out")]
        assert sports.hurt(g, "home", rep(walkons)) == []                              # nobody who plays: units stay
        real = walkons + [("Star Back", "RB", "Out"), ("Top Wideout", "WR", "Out")]
        assert sports.hurt(g, "home", rep(real)) == []        # two who play: WEIGHED (10/4 - depth_penalty), never a block
        assert sports.out_count(g, "home", rep(real)) == 2    # ...and the count the weight reads sees the two
        A._TEAM["ncaaf"] = {}
        assert len(sports.hurt(g, "home", rep(walkons))) == 3                          # no box scores: the old rule
    finally:
        A._TEAM.clear(); A._TEAM.update(keep)



def test_empty_pro_injury_feed_is_unknown():
    """10/3 sweep: ESPN's pro feeds list only the teams with somebody hurt, so a team missing reads as 'nobody hurt' -
    a feed that came back EMPTY (a blank 200) would have cleared every NFL / NBA / NHL / MLB team to be picked blind.
    Empty pro feed = we don't know (the board waits); college can be near-empty (its real coverage is the official
    reports). An official report never erases ESPN's long-term rows (injured reserve / suspended) for that team."""
    import json as _j, tempfile as _t
    keep, keep_p = sd._fetch_espn_injuries, sd.OFFICIAL_PATH
    keep_w, keep_pg = sd.web_injuries, sd.page_injuries      # (10/3: offline - on GitHub these read the live college
    fetch = _REAL_FETCH_INJURIES                             #  injury pages and found real players)
    try:
        sd.web_injuries = sd.page_injuries = lambda *a, **k: {}
        sd.OFFICIAL_PATH = os.path.join(_t.mkdtemp(), "o.json")
        _j.dump({}, open(sd.OFFICIAL_PATH, "w"))
        sd._fetch_espn_injuries = lambda lg: {}
        for lg in sd.PRO:
            assert fetch(lg) is None, lg
        assert fetch("ncaaf") == {}                                # college: the feed is nearly empty on a good day
        g = {"id": "nfl:1", "league": "nfl", "home": "3", "away": "21", "home_name": "Bears", "away_name": "Eagles",
             "status": "pre"}
        assert "the injury report" in sports.waiting_on(g, {"nfl": fetch("nfl")})
        sd._fetch_espn_injuries = lambda lg: {"3": [("Caleb Williams", "QB", "Out")]}
        assert fetch("nfl") == {"3": [("Caleb Williams", "QB", "Out")]}
        today = (datetime.now(timezone.utc) - timedelta(hours=7)).date().isoformat()
        _j.dump({today: {"nfl": {"3": {"players": [["Rome Odunze", "WR", "Questionable"]]}}}}, open(sd.OFFICIAL_PATH, "w"))
        sd._fetch_espn_injuries = lambda lg: {"3": [("Caleb Williams", "QB", "Injured Reserve"), ("D.J. Moore", "WR", "Out"),
                                                   ("Rome Odunze", "WR", "Out")]}
        got = fetch("nfl")["3"]
        assert got[0] == ("Rome Odunze", "WR", "Questionable") and ("Caleb Williams", "QB", "Injured Reserve") in got
        assert len(got) == 2, got                                  # the report's word on Odunze stands; Moore (short-term,
    finally:                                                       # not on the official list) is gone
        sd._fetch_espn_injuries, sd.OFFICIAL_PATH = keep, keep_p
        sd.web_injuries, sd.page_injuries = keep_w, keep_pg


def test_nba_banged_up_side_carries_no_units():
    """10/3 sweep: hoops has no key position (team_key_out never lists an NBA player), yet _is_key read EVERY NBA player
    as 'weighed already' - hurt() dropped them all, so an NBA side with 3 out and 4 day-to-day kept its units. Now the
    rotation counts (anyone who played 3+ of the last 10 box scores); a two-way guy who never plays doesn't."""
    import sports_absences as A
    keep = dict(A._TEAM)
    try:
        g = {"league": "nba", "home": "1", "away": "2", "home_name": "Lakers", "away_name": "Celtics", "start": "2026-11-01T02:00Z"}
        rep = lambda ps: {"nba": {"1": ps}}
        out3 = [("A Guard", "G", "Out"), ("B Wing", "F", "Out"), ("C Big", "C", "Out")]
        A._TEAM["nba"] = {}                                       # no box scores: the plain rule
        assert sports.hurt(g, "home", rep(out3)) == ["A Guard", "B Wing", "C Big"]
        assert sports.hurt(g, "home", rep(out3[:1])) == []
        dtd = [(f"{n} Guy", "F", "Day-To-Day") for n in "DEFG"]
        assert len(sports.hurt(g, "home", rep(dtd))) == 4
        rows = lambda gid, start: [{"gid": gid, "start": start, "team": "1", "player": p, "stats": '{"minutes":"30"}'}
                                   for p in ("A Guard", "B Wing", "C Big")]
        A._TEAM["nba"] = {"1": [(f"2026-10-{20 + i}T02:00Z", f"g{i}", rows(f"g{i}", f"2026-10-{20 + i}T02:00Z")) for i in range(5)]}
        assert A.regulars(None, "nba", "1", "2026-11-01") == {"a guard", "b wing", "c big"}
        assert sports.hurt(g, "home", rep(out3)) == ["A Guard", "B Wing", "C Big"]
        bench = [("Two Way", "G", "Out"), ("G League", "F", "Out"), ("A Guard", "G", "Out")]
        assert sports.hurt(g, "home", rep(bench)) == []            # one rotation player out: the price has it
        assert sd.team_key_out(rep(out3)["nba"], "1", "Lakers", "nba") == []   # (still no key-position path for hoops)
    finally:
        A._TEAM.clear(); A._TEAM.update(keep)


def test_report_names_match_box_scores():
    """10/3 sweep: 23 of 485 official-report names were spelled differently from ESPN's box score ('Mike Hughes' /
    'Michael Hughes', "Brenton 'Inky' Jones" / 'Brenten Jones', 'Kait Wheaton' / 'Kai Wheaton'), so a regular ruled out
    didn't count. One close match (same last name, first name starts the same) counts; two candidates never. And a lead
    back put on injured reserve midweek (he played last week) is a fresh absence the read has to carry."""
    import sports_absences as A
    assert A.match("Mike Hughes", {"michael hughes", "carmelo taylor"}) and A.match("Brenton 'Inky' Jones", {"brenten jones"})
    assert A.match("Kait Wheaton", {"kai wheaton"}) and A.match("Marvin Harrison Jr.", {"marvin harrison"})
    assert not A.match("Rashad Smith", {"xavier smith", "shay smith"})       # two Smiths: no guess
    assert not A.match("Jalen Williams", {"ramar williams"}) and not A.match("Mason Robinson", {"zay robinson"})
    assert not A.match("Smith", {"xavier smith"}) and not A.match("", {"x y"})
    keep = dict(A._TEAM)
    try:
        rows = lambda gid, start: [
            {"gid": gid, "start": start, "team": "7", "player": "Star Back", "stats": '{"rushingYards":"120","rushingAttempts":"20"}'},
            {"gid": gid, "start": start, "team": "7", "player": "Mike Hughes", "stats": '{"receivingYards":"90","receptions":"6"}'},
            {"gid": gid, "start": start, "team": "7", "player": "Field General", "stats": '{"completions/passingAttempts":"20/30"}'}]
        A._TEAM["nfl"] = {"7": [("2026-09-27T17:00Z", "g1", rows("g1", "2026-09-27T17:00Z"))]}
        g = {"league": "nfl", "home": "7", "away": "8", "home_name": "Vikings", "away_name": "Lions", "start": "2026-10-04T17:00Z"}
        pts, who = A.penalty({}, g, "home", {"nfl": {"7": [("Star Back", "RB", "Injured Reserve")]}}, skip_qb=True)
        assert abs(pts - 0.03) < 1e-9 and who == ["RB Star Back"], (pts, who)
        pts, who = A.penalty({}, g, "home", {"nfl": {"7": [("Michael Hughes", "WR", "Out")]}}, skip_qb=True)
        assert abs(pts - 0.03) < 1e-9 and who == ["WR Mike Hughes"], (pts, who)
        assert A.penalty({}, g, "home", {"nfl": {"7": [("Star Back", "RB", "Probable")]}}, skip_qb=True) == (0.0, [])
        hurt_ = sports.hurt(g, "home", {"nfl": {"7": [("Michael Hughes", "WR", "Out"), ("Star Back", "RB", "Injured Reserve"),
                                                      ("Walk On", "OL", "Out")]}})
        assert hurt_ == [], hurt_   # two regulars gone (one to IR this week): weighed (penalty + depth), never a block (10/4)
        assert sports.out_count(g, "home", {"nfl": {"7": [("Michael Hughes", "WR", "Out"), ("Star Back", "RB", "Injured Reserve"),
                                                          ("Walk On", "OL", "Out")]}}) == 2
    finally:
        A._TEAM.clear(); A._TEAM.update(keep)


def test_sync_voids_a_game_espn_dropped():
    """10/3 sweep: three Wild Card Game 3s the sweeps made moot stayed 'pre' forever (ESPN dropped them from its
    schedule), and the factor check read them as "3 recent games have no final score yet" - the 10/3 board was held on
    nothing. A scheduled game 8h+ past its start that ESPN no longer lists on any day we fully re-read is void; a game
    still listed, a game that only just started, or a league with a failed day is left alone."""
    import csv as _c, tempfile as _t
    now = datetime(2026, 10, 3, 17, 0, tzinfo=timezone.utc)
    lo = {"mlb": now.date() - timedelta(days=4), "nhl": now.date() - timedelta(days=4)}
    base = {"league": "mlb", "status": "pre", "home": "1", "away": "2"}
    games = {"mlb:g3": {**base, "id": "mlb:g3", "start": "2026-10-02T00:00Z"},            # the moot Game 3
             "mlb:late": {**base, "id": "mlb:late", "start": "2026-10-03T12:00Z"},        # started 5h ago: still a game
             "mlb:listed": {**base, "id": "mlb:listed", "start": "2026-10-01T21:00Z"},    # ESPN still lists it
             "mlb:edge": {**base, "id": "mlb:edge", "start": (now.date() - timedelta(days=4)).isoformat() + "T23:00Z"},   # the
             "nhl:x": {**base, "id": "nhl:x", "league": "nhl", "start": "2026-10-01T23:00Z"}}  # first re-read day: Eastern
    n = sd.drop_unlisted(games, {"mlb": {"mlb:listed"}}, {"mlb": lo["mlb"]}, now)              # time could hide it (left)
    assert n == 1 and games["mlb:g3"]["status"] == "void", games
    assert all(games[k]["status"] == "pre" for k in ("mlb:late", "mlb:listed", "mlb:edge", "nhl:x")), games
    # the whole sync: a stored stale game, ESPN's pages without it, one league with a failed day
    keep_data, keep_fetch = sd.DATA, sd.fetch_day
    try:
        sd.DATA = _t.mkdtemp()
        today = datetime.now(timezone.utc).date()
        old = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%MZ")
        stale = {k: "" for k in sd.FIELDS}
        stale.update({"id": "mlb:stale", "league": "mlb", "start": old, "status": "pre", "home": "1", "away": "2",
                      "home_name": "A", "away_name": "B", "stype": "3", "intl": "0", "indoor": "0", "neutral": "0"})
        sd.save_games({"mlb:stale": stale, "nhl:stale": {**stale, "id": "nhl:stale", "league": "nhl"}})
        sd.fetch_day = lambda lg, day, retries=2: None if lg == "nhl" and day == today else []
        state = {"synced": {lg: today.isoformat() for lg in sd.LEAGUES}, "ls_walk": list(sd.LEAGUES),
                 "from": {lg: (today - timedelta(days=4000)).isoformat() for lg in sd.LEAGUES}}
        got, _, _ = sd.sync(state, backfill_days=5, ahead_days=1, max_days=5)
        assert got["mlb:stale"]["status"] == "void" and got["nhl:stale"]["status"] == "pre", {k: v["status"] for k, v in got.items()}
        assert sd.load_games("mlb")["mlb:stale"]["status"] == "void"
    finally:
        sd.DATA, sd.fetch_day = keep_data, keep_fetch




def test_review_fact_when_the_home_team_never_bats_in_the_ninth():
    """10/3 sweep: every MLB home win lost its review fact (and its comeback / collapse read) - the home team that led
    after 8½ never batted, so its line was one inning short and the fact came back None ("Favorite came through: the
    Padres over the Cubs" with no score, against the owner's "never vague"). The short line is padded with a 0."""
    import sports_dashboard as D
    l = {"league": "mlb", "side": "home", "team": "Padres", "opp": "Diamondbacks",
         "flow": {"a": "0,0,0,0,0,1,3,0,0", "h": "0,0,1,1,1,1,3,2"}}                 # D-backs 4 @ Padres 9 (9/27)
    assert D.game_fact(l) == "Padres led 4-1 after six innings and won 9-4."
    l["flow"]["h"] = "0,0,1,1,1,1,3,2,X"                                              # ESPN's other way to say it
    assert D.game_fact(l) == "Padres led 4-1 after six innings and won 9-4."
    a = {**l, "side": "away", "team": "Diamondbacks", "opp": "Padres", "flow": {"a": "0,0,0,0,0,1,3,0,0", "h": "0,0,1,1,1,1,3,2"}}
    assert D.game_fact(a) == "Padres led 4-1 after six innings and won 9-4."
    assert D.periods(a) == ([0, 0, 1, 1, 1, 1, 3, 2, 0], [0, 0, 0, 0, 0, 1, 3, 0, 0])
    # a hockey / football line still has to match period for period - nothing padded there
    assert D.game_fact({"league": "nhl", "side": "home", "team": "A", "opp": "B", "flow": {"a": "1,1,1", "h": "0,0"}}) is None
    assert D.periods({"league": "nhl", "flow": {"a": "1,1,1", "h": "0,0"}}) == (None, None)
    # the real 9/29 Yankees Lock (Red Sox 0 @ Yankees 9): its card review now carries the fact
    y = {"league": "mlb", "side": "home", "team": "Yankees", "opp": "Red Sox",
         "flow": {"a": "0,0,0,0,0,0,0,0,0", "h": "0,1,0,0,1,0,2,5"}}
    assert D.with_fact("Won 9-0 like they stole something.", D.game_fact(y)) == \
        "Won 9-0 like they stole something. Yankees led 2-0 after six innings."


def test_pick_on_a_vanished_game_voids_after_4_days():
    """10/3 sweep: a pick whose game dropped out of our data (an id change, a wiped month file - 316 college games were
    wiped once) never graded and never voided: grade_leg returned None forever, so the pick sat open, TODAY'S RESULTS
    waited on it and the board day stuck on it till 8 AM. Like a game that never goes final: 4 days, then void."""
    now = datetime(2026, 10, 3, tzinfo=timezone.utc)
    leg = {"game_id": "gone", "side": "home", "market": "ml", "line": None, "odds": 120, "dec": 2.2, "team": "X",
           "start": "2026-10-02T00:00Z", "tier": "value", "p": 0.5}
    pk = {"kind": "play", "status": "open", "stake": 100, "pnl": 0, "date": "2026-10-01", "legs": [leg]}
    sports.grade([pk], {}, now)
    assert pk["status"] == "open" and leg.get("result") is None          # a day later: still waiting on the data
    assert sports.day_pending([pk], [], "2026-10-01")
    sports.grade([pk], {}, now + timedelta(days=4))
    assert leg["result"] == "void" and pk.get("void") and pk["status"] == "push"
    assert not sports.day_pending([pk], [], "2026-10-01")
    assert sports.units_ledger([pk], [])["rows"] == []                   # a void: not a bet, not in the bankroll


def test_graded_units_frozen_for_every_graded_pick():
    """10/3 sweep: the freeze only ran on the pick being graded that moment - a pick graded before the freeze existed
    (9/27-9/30: the Vikings 5u Lock) and a busted parlay's later-graded legs still re-sized on every code change (the
    10/1 audit had seen 9 graded rows move once). Now every graded pick / leg is frozen on the next grading pass."""
    leg = lambda gid, res, odds=-110, **kw: {"game_id": gid, "side": "home", "market": "ml", "line": None, "odds": odds,
                                             "dec": sd.decimal(odds), "start": "2026-09-27T17:00Z", "result": res,
                                             "tier": "lock", "p": 0.6, "edge_own": 0.08, "team": gid, **kw}
    old = {"kind": "lock", "date": "2026-09-27", "status": "won", "stake": 100, "pnl": 90, "legs": [leg("a", "won")],
           "settled": "2026-09-27T20:00Z", "posted": "2026-09-27T09:00Z"}        # graded before the freeze existed
    busted = {"kind": "two", "date": "2026-09-27", "status": "lost", "stake": 100, "pnl": -100, "posted": "2026-09-27T09:00Z",
              "legs": [leg("b", "lost"), leg("c", None, 130, tier="value", p=0.48, edge_own=0.03)], "settled": "2026-09-27T20:00Z"}
    games = {"c": {"status": "final", "home_score": "3", "away_score": "1", "home_name": "H", "away_name": "A"}}
    sports.grade([old, busted], games, datetime(2026, 9, 28, tzinfo=timezone.utc))
    want = sports.units_for(old)
    assert old.get("units") == want and want > 0
    assert busted["legs"][1]["result"] == "won"
    assert busted["legs"][0].get("units") is not None and busted["legs"][1].get("units") is not None
    old["legs"][0]["p"], old["legs"][0]["edge_own"] = 0.9, 0.5            # a re-size never moves a graded row
    busted["legs"][1]["p"] = 0.9
    assert sports.units_for(old) == want
    assert sports.leg_units(busted, busted["legs"][1]) == busted["legs"][1]["units"]


def test_unit_ledger_row_is_the_parlay_leg_itself():
    """10/3 sweep: a parlay leg's bankroll row carried the whole ticket - the brain's green-day line named the
    ticket's FIRST leg at the PARLAY's price ("the only bet with money on it, Yankees (+300), cashed") for a ½u Blues
    leg at +140. The row is that pick: its team, its price."""
    import sports_dashboard as D
    legs = [{"game_id": "a", "side": "home", "market": "ml", "odds": -120, "dec": sd.decimal(-120), "team": "Yankees",
             "league": "mlb", "result": "won", "tier": "lean", "p": 0.55, "start": "2026-09-30T00:00Z"},
            {"game_id": "b", "side": "away", "market": "ml", "odds": 140, "dec": 2.4, "team": "Blues", "league": "nhl",
             "result": "won", "tier": "value", "p": 0.48, "units": 0.5, "start": "2026-09-30T01:00Z"}]
    pk = {"kind": "two", "date": "2026-09-30", "status": "won", "american": 300, "dec": 4.0, "stake": 100, "legs": legs,
          "posted": "2026-09-30T15:00Z", "settled": "2026-10-01T03:00Z"}
    rows = sports.units_ledger([pk], [])["rows"]
    assert len(rows) == 1 and rows[0][0]["legs"][0]["team"] == "Blues" and rows[0][0]["american"] == 140
    assert rows[0][0]["kind"] == "pick" and rows[0][1] == 0.5 and abs(rows[0][2] - 0.7) < 1e-9
    line = D.green_day([pk], "2026-09-30", 0, 1, 0, early=[])
    assert "Blues (+140)" in line and "+300" not in line and "Yankees" not in line, line


def test_tennis_spread_never_graded_off_the_winner():
    """10/3 sweep: a game-spread leg on a finished match whose games line we couldn't add up (a sets line one set short)
    fell through to the moneyline branch and was graded off the match WINNER - a +4.5 games pick read as a loss. It
    waits for a games count instead; the moneyline leg on the same match grades as before."""
    import sports_tennis as stn
    m = {"id": "atp:1", "status": "STATUS_FINAL", "sets1": "6 4 7", "sets2": "3 6", "winner": "1", "done": "3", "bo": "3"}
    slate = [{"date": "2026-10-02", "picks": [
        {"id": "atp:1:2:sp", "match": "atp:1", "side": 2, "market": "spread", "hcp": 4.5, "result": None},
        {"id": "atp:1:2", "match": "atp:1", "side": 2, "market": "ml", "result": None}], "parlays": {}}]
    stn.grade({"atp:1": m}, slate)
    assert slate[0]["picks"][0]["result"] is None and slate[0]["picks"][1]["result"] == "lost"
    m["sets2"] = "3 6 5"                                                   # the games line fixed: 17-14, +4.5 covers
    stn.grade({"atp:1": m}, slate)
    assert slate[0]["picks"][0]["result"] == "won"


def test_how_it_was_decided_review_still_carries_the_game_fact():
    """10/3 sweep: a review written off the decider ("The Blues won 4-0. Never close. Paid." - a blowout) skipped the
    game fact, so the Blues Dog and the Blackhawks Dog said nothing past the final (the owner, 10/2: 'Never close.
    Brutal.' says nothing). The half-time / two-period fact rides on those reviews too; the final isn't repeated."""
    import sports_dashboard as D
    D.LEG_REVIEWS.clear()
    leg = {"game_id": "nhl:1", "side": "away", "market": "ml", "odds": 154, "dec": 2.54, "team": "Blues", "opp": "Stars",
           "league": "nhl", "result": "won", "tier": "value", "p": 0.4, "start": "2026-10-03T01:00Z",
           "score": "Blues 4 @ Stars 0", "flow": {"a": "1,1,2", "h": "0,0,0"},
           "decider": {"s": "4-0", "type": "blowout", "win": "away"}}
    pk = {"kind": "dog", "date": "2026-10-02", "status": "won", "american": 154, "dec": 2.54, "stake": 100, "legs": [leg],
          "posted": "2026-10-02T15:33Z", "settled": "2026-10-03T04:03Z", "pnl": 154}
    h = D._history([pk])
    rev = D.LEG_REVIEWS[("2026-10-02", "nhl:1|away|ml")]
    assert "Blues led 2-0 after two periods" in rev and rev.count("4-0") == 1, rev
    assert "after two periods" in h


def test_banged_up_count_reads_only_players_who_play():
    """10/3 (the picks sweep): the regulars rule cleared hurt() but the 'more banged-up team' count (MAX_EXTRA_OUT) still
    read every walk-on, redshirt and season-long absence on a college availability report - 13 college sides on one
    Saturday lost their units off lists the engine had already said don't matter. The count reads the same list hurt()
    reads: football players who actually play, never a season-long absence; no box scores = the old count."""
    import sports_absences as A
    keep = dict(A._TEAM)
    rows = lambda gid, start: [
        {"gid": gid, "start": start, "team": "1", "player": "Star Back", "stats": '{"rushingAttempts":"20"}'},
        {"gid": gid, "start": start, "team": "1", "player": "Top Wideout", "stats": '{"receptions":"8"}'}]
    A._TEAM["ncaaf"] = {"1": [("2026-09-20T19:00Z", "g1", rows("g1", "2026-09-20T19:00Z"))]}
    try:
        g = {"id": "ncaaf:1", "league": "ncaaf", "home": "1", "home_name": "State", "away": "2", "away_name": "Tech",
             "start": "2026-10-03T19:00Z"}
        walkons = [("Walk On", "OL", "Out"), ("Red Shirt", "DL", "Out"), ("Third Stringer", "LB", "Out"),
                   ("Old Starter", "WR", "Out For Season")]
        inj = {"ncaaf": {"1": walkons, "2": []}}
        assert sports.out_count(g, "home", inj) == 0                         # nobody who plays: not 'banged up'
        assert sports.out_count(g, "away", inj) == 0
        inj["ncaaf"]["1"] = walkons + [("Star Back", "RB", "Out")]
        assert sports.out_count(g, "home", inj) == 1                         # one who plays counts (so does a QB)
        A._TEAM["ncaaf"] = {}                                                # no box scores: the old rule, minus
        assert sports.out_count(g, "home", inj) == 4                         # the season-long absence
        assert sports.out_count({**g, "league": "nhl"}, "home", {"nhl": {"1": walkons}}) == 3   # hockey: as before
    finally:
        A._TEAM.clear(); A._TEAM.update(keep)
    import inspect
    src = inspect.getsource(sports.candidates)
    assert "out_count(g, side, injuries)" in src and "len(sd.team_injuries(" not in src   # the board uses it


def test_football_banged_up_is_a_weight_not_a_block():
    """10/3, the owner: "just because a QB or a star is out or a team is too banged up doesn't necessarily mean no units.
    It all just depends." The 10/4 study (box scores 2021-26): a football side with 2+ regulars out doesn't lose vs its
    price (NFL -0.4 / college +0.1 pts) - the market has it; the NFL side 2+ MORE banged up than its opponent -2.5 (a
    lead). So in football, with box scores to say who plays: no block - the depth gap is a small, capped weight on the
    OWN read (NFL ½ pt a head, cap 3; college 0); the Missouri-type dog (+180, 2 regulars out) keeps its units. Hockey /
    hoops keep the block; a football team with no box scores keeps the old rule."""
    import sports_absences as A
    # the weight: per head beyond the opponent, capped, football only
    assert sports.depth_penalty("nfl", 2, 0) == 0.01 and sports.depth_penalty("nfl", 1, 1) == 0.0
    assert sports.depth_penalty("nfl", 9, 0) == sports.DEPTH_CAP == 0.03            # never more than 3 points
    assert sports.depth_penalty("nfl", 0, 3) == 0.0                                  # the healthier side isn't paid
    assert sports.depth_penalty("ncaaf", 5, 0) == 0.0 and sports.depth_penalty("nhl", 5, 0) == 0.0
    keep = dict(A._TEAM)
    rows = lambda gid, start, team: [
        {"gid": gid, "start": start, "team": team, "player": f"Back {team}", "stats": '{"rushingAttempts":"20"}'},
        {"gid": gid, "start": start, "team": team, "player": f"Wideout {team}", "stats": '{"receptions":"8"}'},
        {"gid": gid, "start": start, "team": team, "player": f"Backer {team}", "stats": '{"totalTackles":"9"}'}]
    try:
        A._TEAM["nfl"] = {t: [("2026-09-27T17:00Z", f"g{t}", rows(f"g{t}", "2026-09-27T17:00Z", t))] for t in ("3", "4")}
        games, _ = fake_league("nfl", days=120)
        model = {"params": {}, "log": []}
        sm.tune_all(games, model)
        now = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
        g = {**games["nfl:1"], "id": "nfl:x", "status": "pre", "home": "3", "away": "4", "home_name": "Giants",
             "away_name": "Titans", "home_score": "", "away_score": "", "start": "2026-10-04T20:00Z",
             "ml_home": "-130", "ml_away": "110", "ml_home_open": "-130", "ml_away_open": "110", "stype": "2"}
        games[g["id"]] = g
        day = now.astimezone(sports.PT).date()
        clean = {"nfl": {"3": [], "4": []}}
        base = {c["side"]: c for c in sports.candidates(games, model, now, day, clean) if c["game_id"] == "nfl:x" and c["market"] == "ml"}
        thin = {"nfl": {"3": [], "4": [("Back 4", "RB", "Out"), ("Wideout 4", "WR", "Out"), ("Backer 4", "LB", "Out")]}}
        cs = {c["side"]: c for c in sports.candidates(games, model, now, day, thin) if c["game_id"] == "nfl:x" and c["market"] == "ml"}
        assert not cs["away"].get("hurt") and not cs["home"].get("hurt"), "football: three regulars out is weighed, not a block"
        assert cs["away"].get("depth_pts") == 1.5 and "depth_pts" not in cs["home"]      # 3 heads x ½ pt
        own = lambda c: (c["edge_own"] + 1) / c["dec"]                                # noqa: E731
        drop = own(base["away"]) - own(cs["away"])
        assert 0.014 < drop < 0.10, (own(base["away"]), own(cs["away"]))   # the read moved by the weight (RB + WR penalty 10 + depth 1.5)
        A._TEAM["nhl"] = {}                                   # hockey (no study yet): the 2+ out block stays
        assert sports.hurt({**g, "league": "nhl"}, "away", {"nhl": {"4": [("A", "C", "Out"), ("B", "D", "Out")]}}) == ["A", "B"]
        A._TEAM["nfl"] = {}                                   # no box scores: the old block stays (can't tell who plays)
        assert sports.hurt(g, "away", thin) == ["Back 4", "Wideout 4", "Backer 4"]
    finally:
        A._TEAM.clear(); A._TEAM.update(keep)
    import inspect
    src = inspect.getsource(sports.candidates)
    assert "depth_penalty(lg, n_out[s_]" in src and "and not weighed[side]" in src   # the board weighs it, never blocks


def test_best_hockey_dog_needs_real_value():
    """10/3 (the picks sweep): the Jets +105 went up as the Dog of the Day, 1 unit, on a weighed read 0.04 points over
    the price (48.80% vs 48.78%) - a lean in all but the units. The best hockey dog has to beat its price by MIN_EDGE
    like every other unit pick; a real edge still goes up."""
    base = {"league": "nhl", "market": "ml", "odds": 105, "dec": 2.05, "p": 0.47, "p_market": 1 / 2.05,
            "edge": 0.47 * 2.05 - 1, "edge_own": 0.473 * 2.05 - 1, "reasons": ["r"], "dog_ctx": {}, "home": False,
            "side": "away", "start": "2026-10-04T20:00Z", "game_id": "jets", "team": "Jets", "opp": "x", "waiting": []}
    keep = sports.dog_score
    try:
        sports.dog_score = lambda c: 1.5                                     # 48.78% + 1.5 = 50.3%: 3% over - a Dog
        assert sports.best_hockey_dog([dict(base)]) is not None
        sports.dog_score = lambda c: 0.02                                    # +0.02 points: 0.04% value - no Dog
        assert sports.best_hockey_dog([dict(base)]) is None
        assert sports.make_board([dict(base)])["dog"] is None
    finally:
        sports.dog_score = keep


def test_no_value_play_past_the_dog_cap():
    """10/3 (the picks sweep): the owner's "no dog past +280" (DOG_DAY_MAX) only guarded the Dog of the Day - a +400 dog
    with a proven angle and 1% of value was a ½-unit value play. A plus-money play never goes past +280; a +250 with a
    proven angle still does."""
    pr = lambda c: {**c, "reasons": c["reasons"] + ["proven spot: home dog after a loss"]}
    far = pr(_cand("far", 400, 0.22, league="nfl"))                        # 0.22 x 5.0 = 10% of 'value'
    near = pr(_cand("near", 250, 0.30, league="nfl"))                      # 0.30 x 3.5 = 5%
    assert not sports.good(far) and not sports.plays([far], ())
    assert sports.good(near) and sports.plays([near], ())


def test_early_play_never_on_a_team_without_injury_data():
    """10/3 (the picks sweep): the board refuses a pick on a college team the injury data doesn't cover (UNKNOWN, never
    'healthy') - the early spots didn't: a Delaware-type dog with no report would post with units. A side whose team
    isn't in the data gets no early play; a pro team (the feed lists every team with anybody hurt) still does."""
    import sports_early as se
    now = datetime(2026, 10, 6, 18, 0, tzinfo=timezone.utc)                 # a Tuesday
    def gm(gid, lg, start, home, away, hn, an, mh=None, ma=None, status="pre", hs="", as_=""):
        return {"id": gid, "league": lg, "stype": "2", "status": status, "start": start, "home": home, "away": away,
                "home_name": hn, "away_name": an, "ml_home": mh or "", "ml_away": ma or "", "home_score": hs,
                "away_score": as_, "tzo": "-5.0", "neutral": "0"}
    G = {"n1": gm("n1", "nfl", "2026-09-27T17:00Z", "B", "X", "Bills", "X", status="final", hs="20", as_="17"),
         "n2": gm("n2", "nfl", "2026-10-04T17:00Z", "J", "Y", "Jets", "Y", status="final", hs="24", as_="10"),
         "n3": gm("n3", "nfl", "2026-10-11T17:00Z", "J", "B", "Jets", "Bills", "-170", "150")}
    def imp(o):
        o = int(o)
        return 100 / (o + 100) if o > 0 else -o / (-o + 100)
    def agree(g, side):
        h, a = imp(g["ml_home"]), imp(g["ml_away"])
        return (h if side == "home" else a) / (h + a) + 0.02
    se._COACH["exp"] = {}
    keep = sd.covered
    try:
        assert any(c["team"] == "Bills" for c in se.spot_scan(G, now, {"nfl": {}}, agree, hist_dir=tempfile.mkdtemp()))
        sd.covered = lambda inj, lg, tid, name="": name != "Bills"          # (a college-style team with no report)
        assert not any(c["team"] == "Bills" for c in se.spot_scan(G, now, {"nfl": {}}, agree, hist_dir=tempfile.mkdtemp()))
    finally:
        sd.covered = keep
    src = open(se.__file__).read()
    assert src.count("not sd.covered(inj, lg, g[side]") == 2               # the spots and the band scan both check



def test_lock_can_post_after_the_first_game_starts():
    """10/3 (the owner): no Lock on the 8 AM board, but a game later in the day clears the Lock test -> it goes up then
    (games not started only - candidates() never offers a game starting within 20 minutes), with its ping."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports.py")).read()
    assert '(not started or k in pending or k == "lock")' in src
    assert '"lock"' in src[src.index("MIDDAY_KINDS = ("):src.index("MIDDAY_KINDS = (") + 80]
    assert "start < now + timedelta(minutes=MIN_LEAD_MIN)" in src


def test_card_wording_kentucky_fixes():
    """10/3 (the owner, the Kentucky card: "the wording is all fucked up"): no vague talk lines ("season rides on this
    one", "win-or-else talk") - a talk line only with the real quote; a suspension already in the 🚑 line isn't pasted
    again; the record isn't said twice; no "Kentucky have been"."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_breakdown_v24.py")).read()
    i = src.index("for key, who in ((\"talk_theirs\"")
    assert "and hl:" in src[i:i + 700] and "talk_q" in src[i:i + 700]
    assert "have been the better team" not in src and "We're on the better squad" not in src
    assert 'if kind == "suspension" and any(' in src and 'startswith("💪")' in src


def test_nba_on_and_injured_list_only_counts_players_who_play():
    """10/3 (the owner): "the NBA is my favorite sport and I crush NBA" - never shut out as a 'weak' sport; and hockey /
    baseball players on the 10/15-day IL who haven't been playing lately don't take a team's units away."""
    import sports_strength as ss, sports_absences as A
    assert ss.weak("nba") is False and "nba" in ss.OWNER_ON
    keep = dict(A._TEAM)
    games = [(f"2026-09-{d:02d}T19:00Z", f"g{d}", [{"player": "Every Day", "team": "1"}] + ([{"player": "Hurt Guy", "team": "1"}] if d < 3 else []))
             for d in range(1, 16)]
    A._TEAM["mlb"] = {"1": games}
    try:
        reg = A.played_lately(None, "mlb", "1", "2026-10-03T19:00Z")
        assert "every day" in reg and "hurt guy" not in reg
        g = {"league": "mlb", "home": "1", "home_name": "Sox", "away": "2", "away_name": "Jays", "start": "2026-10-03T19:00Z"}
        rep = {"mlb": {"1": [("Hurt Guy", "SP", "10-Day-IL"), ("Gone Two", "RF", "15-Day-IL"), ("Every Day", "SS", "Out")]}}
        assert sports.hurt(g, "home", rep) == []          # only Every Day plays - 1 out, units stay
    finally:
        A._TEAM.clear(); A._TEAM.update(keep)



def test_web_injuries_cover_every_school_it_lists():
    """10/3 (the owner: "I can get injury reports at any second from Google, and the engine needs to be able to do the
    same"): Rotowire's college injury feed is read every run - every school it lists is covered with its players,
    names matched to our teams (UNC Charlotte = Charlotte); a thin / broken read adds nothing (never 'healthy')."""
    names = {"2429": "Charlotte", "2439": "UNLV", "25": "California", "194": "Ohio State"}
    rows = [{"RotoSchoolName": "UNC Charlotte", "player": "Conner Harrell", "position": "QB", "IR": "Out"},
            {"RotoSchoolName": "UNLV", "player": "Alex Orji", "position": "QB", "IR": "Out For Season"},
            {"RotoSchoolName": "California", "player": "Adam Mohammed", "position": "RB", "IR": "Questionable"},
            {"RotoSchoolName": "Nowhere Tech", "player": "X", "position": "WR", "IR": "Out"}] * 6
    got = sd.web_injuries("ncaaf", names, get=lambda u: rows)
    assert ("Conner Harrell", "QB", "Out") in got["2429"] and "2439" in got and "25" in got and "194" not in got
    assert sd.web_injuries("ncaaf", names, get=lambda u: rows[:3]) == {}            # thin read: not used
    def boom(u):
        raise OSError("blocked")
    assert sd.web_injuries("ncaaf", names, get=boom) == {}
    assert sd.web_injuries("nfl", names, get=lambda u: rows) == {}                  # pros keep ESPN's feed


def test_covers_injury_page_covers_every_school():
    """10/3, the owner: "I can get injury reports at any second from Google, and the engine needs to be able to do the
    same." College football reads Covers' page every run: every school it lists is covered (nobody hurt included),
    short names ('J. Dawson') still match the box-score regulars, a bare code block is never guessed."""
    import sports_absences as sa
    page = ["College Football Injuries", "Expand All", "Collapse All", "AF", "Player", "POS", "Status", "J. Dawson",
            "WR", "Out - Undisclosed", "(", "Fri, Sep 25)", "Dawson has been out.",          # (no marker: not guessed)
            "AK", "`\">", "Akron", "Zips", "(1)", "Player", "POS", "Status", "C. Gee", "RB",
            "Questionable - Undisclosed", "(", "Sat, Sep 26)", "Gee note.",
            "AP", "`\">", "Appalachian State", "Mountaineers", "(0)", "Player", "POS", "Status", "No injuries to report.",
            "AR", "`\">", "Arizona", "Wildcats", "(1)", "Player", "POS", "Status", "C. Warren III", "RB", "Out - Knee",
            "(", "Sat, Sep 26)", "Warren note."]   # (the 10/3 page: code | marker | school | mascot | count | headers)
    t = sd.parse_team_page(page)
    assert t == {"Akron": [("C. Gee", "RB", "Questionable")], "Appalachian State": [],
                 "Arizona": [("C. Warren III", "RB", "Out")]}, t
    names = {"2006": "Akron", "2026": "App State", "12": "Arizona", "9": "Arizona State"}
    assert sd._wn("Pittsburgh") in sd.WEB_ALIAS and sd.WEB_ALIAS[sd._wn("Jacksonville State")] == sd._wn("Jax State")
    old = sd.WEB_MIN_TEAMS
    sd.WEB_MIN_TEAMS = 3
    try:
        got = sd.page_injuries("ncaaf", names, get=lambda u: page)
    finally:
        sd.WEB_MIN_TEAMS = old
    assert got["2006"] == [("C. Gee", "RB", "Questionable")] and got["12"] and "9" not in got, got
    assert sd.page_injuries("ncaaf", names, get=lambda u: page[:13]) == {}          # a thin read is never 'healthy'
    assert sa.match("J. Dawson", {"jalen dawson", "mike smith"})
    assert not sa.match("J. Dawson", {"jalen dawson", "jay dawson"})               # two candidates = no guess
    assert sa.match("C. Warren III", {"cameron warren"})
    src = open("sports_data.py").read()
    assert "if league in WEB_PAGE:" in src and "page_injuries(league, team_names(league))" in src
    assert "sports_absences.match(r[0], reg)" in open("sports.py").read().split("def out_count")[1][:1200]


def test_college_injury_page_never_lands_on_the_wrong_school():
    """10/4 review of the Covers reader: 'North Carolina State' matched North Carolina (difflib 0.903 - the alias target
    'nc state' isn't normalized like the keys, 'nc st'), 'South Carolina State' matched South Carolina; hyphenated /
    accented players ('Jean-Luc', 'José') were dropped, so their school read as nobody hurt; a blowout 'last week' was
    said of a game two Saturdays back. Never false information - a school the reader can't place stays unknown."""
    import sports_early as se
    names = {"152": "NC State", "153": "North Carolina", "2579": "SC State", "2579b": "South Carolina", "2006": "Akron",
             "2005": "Abilene Chrstn", "399": "UAlbany", "2572": "Southern Miss", "2534": "Sam Houston"}
    page = []
    for code, school, player in (("NC", "North Carolina State", "G. Bailey"), ("SC", "South Carolina State", "T. Jones"),
                                 ("AK", "Akron", "Jean-Luc Smith"), ("AB", "Abilene Christian", "M. Lee"),
                                 ("AL", "Albany", "D. Ray"), ("SM", "Southern Mississippi", "K. Dean"),
                                 ("SH", "Sam Houston State", "H. Hill")):
        page += [code, "`\">", school, "Mascot", "(1)", "Player", "POS", "Status", player, "WR", "Out - Knee",
                 "(", "Sat, Oct 3)", "A note."]
    page += ["XX", "`\">", "Akron", "Zips", "(1)", "Player", "POS", "Status", "José Ramírez", "RB", "Out - Undisclosed",
             "(", "Sat, Oct 3)", "Note."]
    t = sd.parse_team_page(page)
    assert ("Jean-Luc Smith", "WR", "Out") in t["Akron"] and ("José Ramírez", "RB", "Out") in t["Akron"], t
    old = sd.WEB_MIN_TEAMS
    sd.WEB_MIN_TEAMS = 3
    try:
        got = sd.page_injuries("ncaaf", names, get=lambda u: page)
    finally:
        sd.WEB_MIN_TEAMS = old
    assert got["152"] == [("G. Bailey", "WR", "Out")] and "153" not in got, got          # the Wolfpack's, never UNC's
    assert got["2579"] == [("T. Jones", "WR", "Out")] and "2579b" not in got, got         # SC State's, never the Gamecocks'
    assert "2005" in got and "399" in got and "2572" in got and "2534" in got, got        # close spellings still land
    assert sd._close("north carolina st", ["north carolina", "nc st"]) is None            # a school plus a word = another school
    assert sd._close("abilene christian", ["abilene chrstn"]) == "abilene chrstn"
    rows = [{"RotoSchoolName": "North Carolina State", "player": "G. Bailey", "position": "WR", "IR": "Out"}] * 25
    w = sd.web_injuries("ncaaf", {"153": "North Carolina", "152": "NC State"}, get=lambda u: rows)
    assert "152" in w and "153" not in w, w
    now = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)                             # Tuesday 10/6
    assert se.ago("2026-09-26T23:30Z", now) == "on Saturday 9/26"                        # two Saturdays back: the date
    assert se.ago("2026-10-03T23:30Z", now) == "on Saturday 10/3"
    assert se.ago("2026-09-30T23:30Z", now) == "last week"


def test_early_play_dates_are_plain():
    """10/3, the owner: "Alabama vs Georgia today?" - the early card said 'Saturday · game starts at 4:30 PM PT' on a
    Saturday for NEXT Saturday's game, and 'Alabama beat Mississippi St 56-23 last week' the afternoon they played."""
    import sports_early as se
    now = datetime(2026, 10, 3, 23, 0, tzinfo=timezone.utc)                       # Saturday 10/3, 4 PM PT
    assert se.when("2026-10-10T23:30Z", now) == "Saturday 10/10"
    assert se.when("2026-10-04T17:00Z", now) == "Tomorrow"
    assert se.ago("2026-10-03T16:00Z", now) == "on Saturday 10/3"
    assert se.ago("2026-09-28T17:00Z", now) == "last week"
    G = {"p": {"id": "p", "league": "ncaaf", "start": "2026-10-03T16:00Z", "home": "M", "away": "A",
               "home_name": "Mississippi St", "away_name": "Alabama", "home_score": "23", "away_score": "56",
               "status": "final", "stype": "2"},
         "g": {"id": "g", "league": "ncaaf", "start": "2026-10-10T23:30Z", "home": "A", "away": "G", "home_name": "Alabama",
               "away_name": "Georgia", "status": "pre", "stype": "2"}}
    why = se.spot_why(se._schedule(G), G["g"], "home", "away", "ncaaf", "blowout", now, 0.624, 130)[0]
    assert "beat Mississippi St 56-23 on Saturday 10/3." in why and "last week" not in why, why
    keep_on, se.ON = se.ON, True
    try:
        html = se.html({"picks": [{"team": "Alabama", "opp": "Georgia", "league": "ncaaf", "odds": 130, "spot": "blowout",
                                   "why": why, "start": "2026-10-10T23:30Z", "game_id": "g"}]}, lambda x: x, now=now)
    finally:
        se.ON = keep_on
    assert "Saturday 10/10 · game starts at 4:30 PM PT" in html, html


def test_early_cards_lead_with_the_read_and_never_share_wording():
    """10/4, the owner: the Jaguars and Alabama cards both said only 'Dogs coming off a big win like that have beaten
    their price' - it looked like a one-factor pick (the blowout is a 2-point weight; the engine's own read carried
    both). The card leads with the read, and two early cards never use the same wording."""
    import sports_early as se
    now = datetime(2026, 10, 3, 23, 0, tzinfo=timezone.utc)
    G = {"p": {"id": "p", "league": "ncaaf", "start": "2026-10-03T16:00Z", "home": "M", "away": "A",
               "home_name": "Mississippi St", "away_name": "Alabama", "home_score": "23", "away_score": "56",
               "status": "final", "stype": "2"},
         "g": {"id": "g", "league": "ncaaf", "start": "2026-10-10T23:30Z", "home": "A", "away": "G", "home_name": "Alabama",
               "away_name": "Georgia", "status": "pre", "stype": "2"}}
    ws = se.spot_why(se._schedule(G), G["g"], "home", "away", "ncaaf", "blowout", now, 0.624, 130)
    assert len(set(ws)) == len(ws) >= 6 and all("62%" in w and "56-23" in w for w in ws), ws
    assert not any("beaten their price" in w for w in ws)
    low = se.spot_why(se._schedule(G), G["g"], "home", "away", "ncaaf", "blowout", now, 0.50, 130)
    assert not any("%" in w for w in low), low                       # (a win % only over 55)
    st = {"picks": [{"game_id": "x", "why_t": 0, "result": None}, {"game_id": "y", "why_t": 1, "result": "won"}]}
    c = se.pick_wording({"game_id": "g", "why": ws[0], "whys": ws}, st)
    assert c["why_t"] == 1 and c["why"] == ws[1] and "whys" not in c


def test_covers_page_reads_all_caps_schools():
    """10/4 review: LSU / USC / BYU / UNLV (no lowercase letter) were never read off the Covers page - those schools
    stayed unknown. The line after the marker is the school, whatever its case."""
    page = ["BY", "`\">", "BYU", "Cougars", "(1)", "Player", "POS", "Status", "J. Smith", "WR", "Out - Knee", "(",
            "Sat, Oct 3)", "note.", "LS", "`\">", "LSU", "Tigers", "(0)", "Player", "POS", "Status", "No injuries to report.",
            "AK", "`\">", "Akron", "Zips", "(0)", "Player", "POS", "Status", "No injuries to report."]
    t = sd.parse_team_page(page)
    assert t == {"BYU": [("J. Smith", "WR", "Out")], "LSU": [], "Akron": []}, t


def test_no_cap_on_unit_plays():
    """10/4, the owner: "I don't want the cap at five picks total. If the engine finds more picks, however many is
    fine." Every value play that beats its price goes up; leans still fill the board to 5."""
    assert sports.MAX_PLAYS >= 1000 and sports.BOARD_TARGET == 5


def test_day_games_never_say_tonight():
    """10/4 preview: 'Cardinals get the rematch tonight' / 'that's our edge tonight' on 10 AM / 1 PM PT games."""
    import sports_breakdown_v24 as v
    assert v.day_game(datetime(2026, 10, 4, 17, 0, tzinfo=timezone.utc))          # 10 AM PT
    assert not v.day_game(datetime(2026, 10, 5, 0, 20, tzinfo=timezone.utc))      # 5:20 PM PT, Sunday night
    assert v.not_tonight("Cardinals get the rematch tonight.") == "Cardinals get the rematch today."
    assert "if day_game(start):" in open("sports_breakdown_v24.py").read()


def test_graded_lock_and_dog_leaving_the_board_never_reads_as_no_lock():
    """10/4, 12:09 AM - the owner: "It's saying no lock today and no dog right now - that's a bug." 10/3 had the UNLV
    Lock and the Flyers Dog; once their cards' 3 hours were up the notes read only what was still on the board."""
    import sports_dashboard as sdb
    lock = {"date": "2026-10-03", "kind": "lock", "status": "won", "legs": []}
    dog = {"date": "2026-10-03", "kind": "dog", "status": "lost", "legs": []}
    lean = {"date": "2026-10-03", "kind": "lean", "lean": True, "status": "open", "legs": []}
    html = sdb._cards("2026-10-03", [lean], [("lean", "<div>LEAN</div>")], day_all=[lock, dog, lean])
    assert "leanday" not in html, html                                   # no 'No Lock' / 'No Dog' note
    html = sdb._cards("2026-10-03", [lean], [("lean", "<div>LEAN</div>")], day_all=[lean])
    assert "leanday" in html                                             # a day that truly had none still says so


def test_europe_morning_under_is_tracked_not_bet():
    """10/4, the owner: "track it and see if we can prove something." Every NFL game in Europe before noon ET: the
    Under at the night-before number, graded, its own record - never a pick, never units."""
    import sports_intl as si, tempfile as _t
    g = {"id": "nfl:1", "league": "nfl", "intl": "1", "country": "England", "city": "London", "start": "2026-10-04T13:30Z",
         "status": "pre", "total": "46.5", "under_odds": "-110", "away_name": "Colts", "home_name": "Commanders"}
    late = dict(g, id="nfl:2", start="2026-10-04T20:00Z")                     # 4 PM ET in London: not a morning game
    mex = dict(g, id="nfl:3", country="Mexico")
    p = os.path.join(_t.mkdtemp(), "i.json")
    st = si.run({"nfl:1": g, "nfl:2": late, "nfl:3": mex}, datetime(2026, 10, 3, 20, 0, tzinfo=timezone.utc), p)
    assert st["games"] == {}                                                  # 1 PM PT the day before: too early
    st = si.run({"nfl:1": g, "nfl:2": late, "nfl:3": mex}, datetime(2026, 10, 4, 6, 0, tzinfo=timezone.utc), p)
    assert list(st["games"]) == ["nfl:1"] and st["games"]["nfl:1"]["total"] == 46.5
    g2 = dict(g, status="final", home_score="20", away_score="17", total="44.5")   # the number never changes after
    st = si.run({"nfl:1": g2}, datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc), p)
    assert st["games"]["nfl:1"]["result"] == "won" and st["record"]["won"] == 1 and st["games"]["nfl:1"]["total"] == 46.5
    assert "sports_intl.run(games, now)" in open("sports.py").read()


def test_key_player_on_ir_is_not_called_news():
    """10/4 preview: 'No Jaxson Dart for Giants — that's their starting quarterback' - Dart was on IR and Jameis
    Winston had started their last two games. A key player on IR reads as still out, the backup going again."""
    src = open("sports_breakdown_v24.py").read()
    assert "any(w in str(key_them[0][2]).lower() for w in sd.LONG_OUT)" in src and "is on IR" in src
    i = src.index("any(w in str(key_them[0][2]).lower() for w in sd.LONG_OUT)")
    assert src.index("that's their starting {pos}") > i            # the 'starting QB' wording only after the IR check


def test_an_old_tab_swaps_to_the_new_board_even_while_scrolling():
    """10/4, 8 AM - the owner: "when I clicked the dashboard, I didn't see no picks." The picks were up at 8:00; his tab
    from last night never swapped because he was scrolling. A page 20+ minutes old swaps right away."""
    src = open("sports_dashboard.py").read()
    assert "var aged=Date.now()-t>1200000;" in src and "if(!st&&!aged&&Date.now()-touched<30000)return;" in src


def test_europe_morning_under_half_unit_with_the_quit_rule():
    """10/4, the owner: "we can't wait years to prove anything, the books will catch up ... half unit with the quit
    rule, build it." Every NFL game in Europe before noon ET: the UNDER at ½u, posted the night before (never game day),
    graded on the total, its own record - and under 50% after 15 graded, it's off."""
    import sports_early as se
    g = {"id": "nfl:9", "league": "nfl", "intl": "1", "country": "England", "city": "London", "start": "2026-10-11T13:30Z",
         "status": "pre", "total": "44.5", "under_odds": "-108", "away_name": "Jets", "home_name": "Vikings"}
    st = {"picks": []}
    assert se.euro_unders({"nfl:9": g}, st, datetime(2026, 10, 10, 20, 0, tzinfo=timezone.utc)) == []   # 1 PM PT: too early
    got = se.euro_unders({"nfl:9": g}, st, datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc))         # 7 PM PT the night before
    assert len(got) == 1 and got[0]["side"] == "under" and got[0]["line"] == 44.5 and got[0]["odds"] == -108
    assert se.units(got[0]) == 0.5 and "17-9" in got[0]["why"] and "London" in got[0]["why"]
    assert se.euro_unders({"nfl:9": g}, st, datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)) == []   # 2 AM PT game day: never
    p = dict(got[0])
    st = {"picks": [p]}
    se.grade(st, {"nfl:9": dict(g, status="final", home_score="20", away_score="17")})
    assert p["result"] == "won"                                                                      # 37 < 44.5
    keep_on, se.ON = se.ON, True                                    # (another test may switch the box off)
    try:
        html = se.html({"picks": [dict(got[0])]}, lambda x: x, now=datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc))
    finally:
        se.ON = keep_on
    assert "Under 44.5" in html and "vs Jets" not in html and "Jets @ Vikings" in html
    lost = [{"game_id": f"x{i}", "spot": "euro_under", "odds": -110, "result": "lost" if i < 8 else "won"} for i in range(15)]
    assert se.euro_quit({"picks": lost}) and se.euro_unders({"nfl:9": g}, {"picks": lost},
                                                            datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc)) == []
    assert not se.euro_quit({"picks": lost[:14]})                                                    # 14 graded: not yet


def test_early_play_and_the_same_board_pick_both_count():
    """10/4 audit. (1) The owner, 10/4: "Jaguars can be both" - the ½u early play AND the 1u game-day Dog on the same
    side each count with their own units. The ledger keyed both on (day, game, side) and the early row overwrote the
    Dog's: the unit record lost the Dog's +1.2u. (2) A win % shows only OVER 55% - 55.2% rounds to "55%", so no %.
    (3) The game-day 'better price now' call reads the market off the opponent's price NOW, not the one at post time."""
    import sports_early as se
    early = [{"game_id": "nfl:401872969", "side": "away", "team": "Jaguars", "odds": 120, "own": 0.6081, "spot": "best",
              "start": "2026-10-04T17:00Z", "result": "won", "graded_at": "2026-10-04T20:27Z"}]
    dog = {"date": "2026-10-04", "kind": "dog", "status": "won", "dec": 2.2, "units": 1.0, "legs": [
        {"game_id": "nfl:401872969", "side": "away", "team": "Jaguars", "odds": 120, "market": "ml", "p": 0.4571,
         "tier": "value", "result": "won"}]}
    led = sports.units_ledger([dog], early)
    assert sorted((r[0]["units_tier"], r[1], round(r[2], 2)) for r in led["rows"]) == [("early", 0.5, 0.6), ("value", 1.0, 1.2)]
    assert len(sports.units_ledger([dog], [])["rows"]) == 1 and len(sports.units_ledger([], early)["rows"]) == 1
    import sports_dashboard as d
    assert "2-0" in d.unit_record([dog], "2026-10-04", early) and "+1.8 UNITS" in d.unit_record([dog], "2026-10-04", early)
    # (2) 'Our numbers got Fresno St winning 55%' never shows - the rule is OVER 55
    g = {"home": "1", "away": "2", "home_name": "Fresno St", "away_name": "Boise St", "start": "2026-10-11T02:30Z", "league": "ncaaf"}
    now = datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)
    assert not any("55%" in w for w in se.spot_why({}, g, "home", "away", "ncaaf", "blowout", now, 0.5518, 205))
    assert all("56%" in w for w in se.spot_why({}, g, "home", "away", "ncaaf", "blowout", now, 0.5551, 205))
    # (3) the opponent's price moved too: the market's number comes from today's prices
    p = {"odds": 150, "opp_odds": -170, "own": 0.42, "league": "nfl"}   # posted +150 / -170; now +185 / -125 (both moved)
    assert se.label(p, 185, -125) == "👀 money went against it"   # 42% vs 38.6% now: under the 4-point bar
    assert se.label(p, 185, -300) == "💰 better price now"        # the other side at -300: the market's at 26% - value
    assert se.label(p, 185) == se.label(p, 185, -170)             # no price given = the post-time one, as before


def test_early_line_never_says_the_market_moved_when_it_didnt():
    """10/4, the owner: the Jaguars card said 'The market corrected' - the line never moved off the +120 we got in at."""
    import sports_dashboard as sdb
    sdb.EARLY_IN.clear()
    sdb.EARLY_IN[("nfl:1", "away")] = 120
    leg = {"game_id": "nfl:1", "side": "away", "market": "ml", "odds": 120, "team": "Jaguars"}
    out = sdb._early_line(leg)
    assert "hasn't moved" in out or "same number" in out, out
    assert "corrected" not in out and "moved, but" not in out
    assert "corrected" in sdb._early_line({**leg, "odds": 110}) or "line moved" in sdb._early_line({**leg, "odds": 110}) \
        or "after the move" in sdb._early_line({**leg, "odds": 110})
    assert "better now" in sdb._early_line({**leg, "odds": 130}) or "even more" in sdb._early_line({**leg, "odds": 130})
    sdb.EARLY_IN.clear()


def test_live_mlb_paused_and_draftkings_alone_never_posts():
    """10/4, the owner: "pause MLB" (live baseball 0-5 at long prices) and "fix" DraftKings-only live prices - ESPN's
    DK line has no time stamp, so a cached price could post a bet; alone it needs a second book to agree."""
    import sports_live as sl
    assert "mlb" in sl.PAUSED
    src = open("sports_live.py").read()
    j = src[src.index("def _judge("):src.index("def _judge(") + 3000]
    assert "if lg in PAUSED:" in j and 'if src == "draftkings" and not checked:' in j
    assert sl.two_books((120, -140), (None, None))[2] is False           # DK alone: never 'checked'


def test_early_card_shows_got_it_at_and_now():
    """10/5, the owner: "put what we got in the early value plays for and what they move to now"."""
    import sports_early as se
    p = {"game_id": "g", "side": "away", "odds": 130, "team": "Alabama", "league": "ncaaf", "opp_odds": -150, "own": 0.6}
    g = {"g": {"status": "pre", "ml_away": "-105", "ml_home": "-115"}}
    assert se.now_line(p, g).startswith("📈 Got it at +130 ➜ now -105") and "beat the line" in se.now_line(p, g)
    assert "hasn't moved" in se.now_line(p, {"g": {"status": "pre", "ml_away": "130", "ml_home": "-150"}})
    t = {"game_id": "g", "side": "under", "market": "total", "line": 44.5, "odds": -108}
    assert se.now_line(t, {"g": {"status": "pre", "total": "43.5", "under_odds": "-110"}}) == \
        "📈 Got it at 44.5 (-108) ➜ now 43.5 (-110) · 🔥 we beat the number"
    assert se.now_line(p, {"g": {"status": "in"}}) == ""                        # (game day / live: the other box)


def test_early_cards_have_enough_wordings_for_a_full_box():
    """10/5, the owner: "we don't want four early cards that share the same line" - 7 open cards ran out of 3
    wordings; now 6 reads and 6 blowout facts, every one different."""
    import sports_early as se
    st = se.load()
    open_ = [p["why"] for p in st["picks"] if not p.get("result")]
    reads = [w.split(". ")[0] for w in open_]
    assert len(set(open_)) == len(open_)
    src = open("sports_early.py").read()
    assert src.count("🧠 ") >= 12 and "Last time out:" in src


def test_no_head_to_head_lines_on_cards():
    """10/5, the owner: drop the 🆚 lines - "a team has another team's number" was dead in every sport."""
    import sports_card_guard as g
    lines = ["🆚 Panthers have had Lions's number: 2 of the last 3.", "🏟️ 49ers are 2-0 at home this year."]
    assert g.clean(lines, "nfl", "x") == ["🏟️ 49ers are 2-0 at home this year."]
    assert g.one("🆚 Last meeting went their way (W 24-10).", "nfl") == ""


def test_question_box_closes_quietly_when_the_credit_runs_out():
    """10/5, the owner: the question box costs too much - "when it's gone, that's it." Out of API credit, the box says
    it's closed (no error message, no retry)."""
    src = open("workers/ask/src/index.js").read()
    assert "/credit balance/i.test" in src and "The question box is closed for now." in src


def test_question_box_comes_off_when_the_credit_runs_out():
    """10/5, the owner: "you'll know when the credits run out and you'll remove the question box?" - the Worker flags
    it the first time the API says the credit's gone; the hourly run reads /askstatus and the page drops the box (the
    live-bet alerts on the same Worker keep working)."""
    import sports_dashboard as sdb, tempfile as _t
    keep_p, keep_u = sdb.ASK_CLOSED_PATH, sdb._ask_url
    try:
        sdb.ASK_CLOSED_PATH = os.path.join(_t.mkdtemp(), "a.json")
        sdb._ask_url = lambda: "https://d503-ask.x.workers.dev"
        assert sdb.ask_closed() is False
        assert sdb.refresh_ask_status(get=lambda u: {"closed": False}) is False and not sdb.ask_closed()
        assert sdb.refresh_ask_status(get=lambda u: {"closed": True}) is True and sdb.ask_closed()
        assert sdb.refresh_ask_status(get=lambda u: (_ for _ in ()).throw(OSError("down"))) is None and sdb.ask_closed()
    finally:
        sdb.ASK_CLOSED_PATH, sdb._ask_url = keep_p, keep_u
    src = open("sports_dashboard.py").read()
    assert 'ask_box = "" if ask_closed() else' in src and "{ask_box}" in src
    w = open("workers/ask/src/index.js").read()
    assert 'path === "/askstatus"' in w and 'env.LOG.put("ask_closed"' in w
    assert "sports_dashboard.refresh_ask_status()" in open("sports.py").read()


def test_patty_challenge_removed():
    """10/3 (the owner): "remove the Patty challenge off the dashboard ... no need to save it" - the box, its updates,
    its live-score hooks and its record are gone. A tennis score still needs 2 sets before it's called."""
    here = os.path.dirname(os.path.abspath(__file__))
    assert not os.path.exists(os.path.join(here, "sports_challenge.py"))
    assert not os.path.exists(os.path.join(here, "data", "sports", "challenge.json"))
    for f in ("sports.py", "sports_dashboard.py", "sports_live.py", "sports_tennis.py", ".github/workflows/scores_check.yml"):
        src = open(os.path.join(here, f)).read()
        assert "sports_challenge" not in src and "challenge.json" not in src and "pvLive" not in src, f
    src = open(os.path.join(here, "sports_dashboard.py")).read()
    called = src[src.index("function called("):src.index("function liveTags(")]
    assert "Math.max(w[0],w[1])<2" in called


def test_lock_miss_names_the_closest_pick():
    """10/2 (the owner): no Lock posted -> the engine saves what the Lock would have been and why it fell short (Virginia
    Tech -130), for the question box. It never touches the candidates (no near_price flag left behind)."""
    import tempfile as _t
    c = {"market": "ml", "odds": -130, "dec": 1 + 100 / 130, "edge_own": 0.0, "edge": 0.0, "reasons": ["x"], "team": "Virginia Tech",
         "opp": "Pitt", "league": "ncaaf", "game_id": "ncaaf:1", "waiting": [], "p": 0.565}
    c["edge_own"] = 0.57 * c["dec"] - 1
    old = sports.money_against
    sports.money_against = lambda c_: False
    try:
        m = sports.lock_miss([c])
    finally:
        sports.money_against = old
    assert m and m["team"] == "Virginia Tech" and m["odds"] == -130 and "near_price" not in c
    assert m["engine's own read %"] == 57 and "beats the price by" in m["why it's not the Lock"]
    p = os.path.join(_t.mkdtemp(), "m.json")
    for d in range(1, 10):
        sports.save_lock_miss(f"2026-10-{d:02d}", m, p)
    st = json.load(open(p))
    assert len(st) == 7 and "2026-10-09" in st and "2026-10-01" not in st
    sports.save_lock_miss("2026-10-09", {"team": "Later"}, p)          # a later run never overwrites the morning's
    assert json.load(open(p))["2026-10-09"]["team"] == "Virginia Tech"
    # the healthy pool decides first, like the Lock itself: a banged-up Penn State with the higher read never jumps
    # ahead of the pick the engine actually backed (10/2: Virginia Tech)
    pen = dict(c, team="Penn State", odds=-142, dec=1 + 100 / 142, game_id="ncaaf:2", hurt=["Koby Howard"])
    pen["edge_own"] = 0.589 * pen["dec"] - 1
    sports.money_against = lambda c_: False
    try:
        assert sports.lock_miss([c], [c, pen])["team"] == "Virginia Tech"
    finally:
        sports.money_against = old
    under = dict(c, edge_own=0.55 * c["dec"] - 1, p=0.55)              # VT 55% vs the 56.5% -130 needs
    assert "under what the price needs" in sports.lock_miss([under])["why it's not the Lock"]


def test_health_restarts_a_skipped_engine():
    """10/2: GitHub skipped the engine's hourly runs for 3 hours and nothing restarted it (the board check only looks
    after 9 AM). The hourly bug check now starts the engine when its last run is 80+ minutes old."""
    h = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "health.py")).read()
    assert "ENGINE_STALE_MIN = 80" in h and 'dispatch("sports.yml", f"engine {age_m:.0f} min since its last run")' in h
    assert '"--workflow", "sports.yml", "--limit", "1"' in h


def test_health_job_pushes_only_its_report():
    """10/2: the hourly health check went red 5 runs in a row - every check OK, but files it touched blocked its
    'git pull --rebase'. It commits health.json, sets everything else aside, then pulls."""
    y = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows", "health.yml")).read()
    assert y.index("git stash -q --include-untracked") > y.index('git commit -qm "health')
    assert y.index("git stash -q --include-untracked") < y.index("git pull --rebase")
    for wf in ("board_preview", "injury_report", "injury_probe"):   # (10/2: the board preview's save failed the same way)
        y2 = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows", wf + ".yml")).read()
        assert y2.index("git stash -q --include-untracked") < y2.index("git pull --rebase"), wf


def test_factor_check_has_fresh_data():
    """10/2, the owner: "did the engine have all the accurate, updated daily data across every aspect?" Before the
    board: most of the slate priced 12h+ ago (the odds pull failed), recent games with no final score, the player stats
    missing - each holds the board. A game or two the books stopped listing is only a note (never holds good picks)."""
    from datetime import date
    now = datetime(2026, 10, 2, 15, tzinfo=timezone.utc)
    keep = {k: dict(getattr(sports, k)) for k in ("DOG_ST", "LAST_STARTS")}
    keep_cache = sp.CACHE
    try:
        sports.DOG_ST[("nba", "1")] = {"won": True}; sports.LAST_STARTS[("nba", "1")] = ["x"]
        inj = {"nba": {"1": []}}
        G = {f"g{i}": {"league": "nba", "status": "pre", "start": "2026-10-02T23:00Z", "home_name": f"T{i}",
                       "odds_time": "2026-10-02T14:30Z"} for i in range(4)}
        cs = [{**_cand(f"g{i}", -120, 0.55, league="nba"), "game_id": f"g{i}"} for i in range(4)]
        assert not sports.factor_check(G, cs, inj, date(2026, 10, 2), now)
        G["g0"]["odds_time"] = "2026-10-01T22:00Z"                # one stale price: a note, not a hold
        assert not sports.factor_check(G, cs, inj, date(2026, 10, 2), now)
        for i in range(3):
            G[f"g{i}"]["odds_time"] = "2026-10-01T22:00Z"         # most stale: the pull failed - hold
        assert any("fresh price" in p for p in sports.factor_check(G, cs, inj, date(2026, 10, 2), now))
        for i in range(4):
            G[f"g{i}"]["odds_time"] = "2026-10-02T14:30Z"
        for i in range(3):                                       # last night's games never got their finals
            G[f"y{i}"] = {"league": "nba", "status": "pre", "start": "2026-10-02T00:00Z", "ml_home": "-130"}
        assert any("final score" in p for p in sports.factor_check(G, cs, inj, date(2026, 10, 2), now))
        for i in range(3):
            G[f"y{i}"]["status"] = "final"
        assert not sports.factor_check(G, cs, inj, date(2026, 10, 2), now)
        sports.DOG_ST[("mlb", "1")] = {"won": True}; inj["mlb"] = {"1": []}
        sp.CACHE = {}
        mc = [{**_cand("m", -120, 0.55, league="mlb"), "game_id": "m"}]
        assert any("player stats" in p for p in sports.factor_check(G, mc, inj, date(2026, 10, 2), now))
    finally:
        sp.CACHE = keep_cache
        for k, v in keep.items():
            getattr(sports, k).clear(); getattr(sports, k).update(v)


def test_the_daily_double_check():
    """10/1, the owner: "every day before the engine posts there needs to be a double check - every factor, every study,
    no bugs on the picks." Part 1: a missing study's data holds the board. Part 2: a pick breaking a rule gets pulled."""
    from datetime import date
    keep = {k: dict(getattr(sports, k)) for k in ("DOG_ST", "LAST_STARTS")}
    try:
        sports.DOG_ST.clear(); sports.LAST_STARTS.clear()
        c = {**_cand("g", -120, 0.55, league="mlb")}
        probs = sports.factor_check({}, [c], {}, date(2026, 10, 1), datetime(2026, 10, 1, 15, tzinfo=timezone.utc))
        assert any("dog studies" in p for p in probs) and any("injury report" in p for p in probs)
        sports.DOG_ST[("mlb", "1")] = {"won": True}; sports.LAST_STARTS[("mlb", "1")] = ["x"]
        keep_cache, sp.CACHE = sp.CACHE, {"mlb": [{"player": "x"}]}
        probs = sports.factor_check({}, [c], {"mlb": {"1": []}}, date(2026, 10, 1), datetime(2026, 10, 1, 15, tzinfo=timezone.utc))
        sp.CACHE = keep_cache
        assert not probs, probs
    finally:
        for k, v in keep.items():
            getattr(sports, k).clear(); getattr(sports, k).update(v)
    iso = "2026-10-01"
    ok = {"date": iso, "kind": "lean", "lean": True, "status": "open", "legs": [{**_cand("a", -120, 0.55), "game_id": "a"}]}
    big = {"date": iso, "kind": "lean", "lean": True, "status": "open", "legs": [{**_cand("b", -180, 0.65), "game_id": "b"}]}
    dup = {"date": iso, "kind": "lean", "lean": True, "status": "open", "legs": [{**_cand("a2", -110, 0.52), "game_id": "a"}]}
    pl = {"date": iso, "kind": "lean", "lean": True, "status": "open",
          "legs": [{**_cand("c", -110, 0.55, market="spread", line=-1.5, league="nhl"), "game_id": "c"}]}
    nolock = {"date": iso, "kind": "lock", "status": "open",
              "legs": [{**_cand("d", -148, 0.57), "edge_own": 0.58 * sd.decimal(-148) - 1, "game_id": "d"}]}
    picks = [ok, big, dup, pl, nolock]; new = list(picks)
    probs = sports.rule_check(picks, new, iso)
    assert new == [ok] and picks == [ok], [p["legs"][0]["game_id"] for p in new]
    assert len(probs) == 4


def test_hockey_third_game_in_four_nights():
    """10/1 study: a rested hockey favorite vs a team on its 3rd game in 4 nights beat its price 8 of 8 seasons - a
    weight (+1.5 pts) on the favorite's read."""
    keep = dict(sports.LAST_STARTS)
    try:
        sports.LAST_STARTS.clear()
        sports.LAST_STARTS[("nhl", "D")] = ["2026-10-08T23:00Z", "2026-10-10T23:00Z"]   # played 3 and 1 days before
        sports.LAST_STARTS[("nhl", "F")] = ["2026-10-08T23:00Z"]
        fav = {**_cand("g", -140, 0.57, league="nhl"), "team_id": "F", "start": "2026-10-11T23:00Z", "p_market": 0.565,
               "side": "home"}
        dog = {**_cand("g", 120, 0.43, league="nhl"), "team_id": "D", "start": "2026-10-11T23:00Z", "p_market": 0.435,
               "side": "away", "dog_ctx": {}}
        assert sports.third_in_four(fav, dog)
        sports.LAST_STARTS[("nhl", "F")] = ["2026-10-10T23:00Z"]                        # the favorite played yesterday
        assert not sports.third_in_four(fav, dog)
    finally:
        sports.LAST_STARTS.clear(); sports.LAST_STARTS.update(keep)


def test_overnight_study_weights():
    """10/1 overnight studies, wired as weights: the West Coast road favorite in the East (+2 pts on its read, -2 on the
    home dog's score) and a football dog without its key player (-3)."""
    games = {"g": {"id": "g", "league": "nfl", "away": "SF", "home": "NYG", "tzo": "-5.0", "neutral": "0"}}
    keep = dict(sports._SCHED)
    try:
        sports._SCHED.update(ref=games, k=id(games), s={}, tz={("nfl", "SF"): -8.0})
        fav = {**_cand("g", -140, 0.58, league="nfl"), "home": False, "side": "away"}
        dog = {**_cand("g", 120, 0.42, league="nfl"), "home": True, "side": "home", "dog_ctx": {}}
        sports.weigh_west_coast_road_fav(games, [fav, dog])
        assert abs(fav["p"] - 0.60) < 1e-9 and dog.get("west_trip_dog")
        assert sports.dog_spots(dog) == -2
    finally:
        sports._SCHED.clear(); sports._SCHED.update(keep)
    assert sports.dog_spots({"league": "nfl", "odds": 150, "dog_ctx": {}, "key_out_me": True}) == -3


def test_lead_tracker():
    """10/1, the owner: "keep a tracker to see if we can prove your theory - it's for you, not the dashboard." Every side
    where an unproven lead fires is logged with its price, then graded per lead (W-L, units, ROI)."""
    import sports_leads as sl, tempfile
    keep = (sl.PATH, sl.RECORD)
    try:
        d = tempfile.mkdtemp()
        sl.PATH, sl.RECORD = os.path.join(d, "t.json"), os.path.join(d, "r.json")
        dog = {**_cand("g1", 150, 0.40, league="nfl"), "side": "away", "dog_ctx": {}, "dog_more": {"mnf": True, "bye": True}}
        fav = {**_cand("g2", -140, 0.58, league="nhl"), "side": "home", "w_p": 0.60, "p_market": 0.565}
        assert sl.log("2026-10-12", [dog, fav], sports) == 2 and sl.log("2026-10-12", [dog, fav], sports) == 0
        games = {"g1": {"status": "final", "home_score": "17", "away_score": "20"},
                 "g2": {"status": "final", "home_score": "1", "away_score": "3"}}
        rec = sl.grade(games)
        assert rec["Monday night dog"] == {"w": 1, "l": 0, "units": 1.5, "roi": 1.5}
        assert rec["hockey fav weighed UP"]["l"] == 1
    finally:
        sl.PATH, sl.RECORD = keep
    import sports_ats
    assert sports_ats.ATS_CAP == 0.015 and sports_ats.ATS_SHRINK == 0.5


def test_sharp_money_lead():
    """10/1, the owner: "the smart money looks to be on the Browns - dig into it." The study (24,301 games): every
    "sharp" cut was dead except NHL dogs the line moved to against the tickets with the money over the tickets (+14.3%
    on 190) - a +1 lead weight; every sharp signal goes in the lead tracker."""
    import sports_breakdown as sb
    keep = sb.public_split
    try:
        sb.public_split = lambda leg: (40, 55)
        dog = {**_cand("g", 130, 0.43, league="nhl"), "drift": -0.03, "dog_ctx": {}}
        assert sports.sharp_dog(dog) and sports.dog_spots(dog) == 1
        assert not sports.sharp_dog({**dog, "drift": 0.0})
        sb.public_split = lambda leg: (40, 45)
        assert not sports.sharp_dog(dog)
        import sports_leads
        sb.public_split = lambda leg: (75, 90)
        assert "money 10+ over tickets" in sports_leads.tags({**_cand("f", -140, 0.58, league="nfl")}, sports)
    finally:
        sb.public_split = keep


def test_last_leads_wired():
    """10/1, the owner: "wire everything in the engine." The watch leads as small weights: the hoops favorite that wins
    inside (+1 pt), the MLB doubleheader game-2 dog (+1), an NFL dog whose offense scored 10 or fewer (+1)."""
    import sports_hoops_style as hs
    rows = []
    for k in range(10):
        teams = {str(t): {"fieldGoalsMade-fieldGoalsAttempted": "30-60",
                          "threePointFieldGoalsMade-threePointFieldGoalsAttempted": f"8-{10 + 2 * t}",
                          "offensiveRebounds": str(16 - t)} for t in range(12)}
        rows.append({"start": f"2026-11-{10 + k:02d}T00:00Z", "teams": teams})
    st = hs.states("ncaab", "2026-12-01T00:00Z", rows=rows)
    assert hs.inside(st, "ncaab", "0", "11") == 1          # crashes the glass, few 3s, facing a weak rebounder
    assert hs.inside(st, "ncaab", "0", "1") == 0           # ...facing a glass-crashing team: cancels (college)
    assert hs.inside(st, "ncaab", "11", "5") == 0
    base = {"odds": 150, "dog_ctx": {}}
    assert sports.dog_spots({**base, "league": "mlb", "dh_game2": True}) == 1
    assert sports.dog_spots({**base, "league": "nfl", "dog_more": {"last_pts": 7}}) == 1
    games = {"a": {"id": "a", "league": "mlb", "home": "1", "away": "2", "start": "2026-08-01T17:00Z"},
             "b": {"id": "b", "league": "mlb", "home": "1", "away": "2", "start": "2026-08-01T23:00Z"}}
    c = {"league": "mlb", "market": "ml", "game_id": "b"}
    sports.mark_doubleheader_game2(games, [c])
    assert c.get("dh_game2")


def test_price_path_timing():
    """10/1 odds studies: dogs early, favorites on game day (a favorite's price only gets worse through the week) - no
    early favorite ever; the hourly price log keeps the spread juice (the juice moves before the number)."""
    import inspect, sports_early as se, tempfile
    assert "if not hit or not dog:" in inspect.getsource(se.spot_scan)
    d = tempfile.mkdtemp()
    g = {"g1": {"id": "g1", "status": "pre", "start": "2026-10-04T17:00Z", "ml_home": "-130", "ml_away": "110",
                "spread_home": "-2.5", "spread_home_odds": "-120", "spread_away_odds": "100"}}
    now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    assert sd.record_lines(g, now, d) == 1 and sd.record_lines(g, now, d) == 0
    g["g1"]["spread_home_odds"] = "-125"
    assert sd.record_lines(g, now, d) == 1                 # a juice change alone is a new row
    row = [json.loads(x) for x in open(os.path.join(d, "2026-10.jsonl"))][-1]
    assert row["spo"] == ["-125", "100"]


def test_schedule_cache_holds_the_dict():
    """10/1: the schedule cache was keyed by id(games) - a new games dict at a freed address read the old schedule (the
    East-West spot vanished mid test run). It holds the dict itself now."""
    a = {"x": {"id": "x", "league": "nfl", "home": "1", "away": "2", "start": "2026-10-04T17:00Z", "status": "pre"}}
    sports._sched(a)
    assert sports._SCHED["ref"] is a
    b = dict(a)
    sports._sched(b)
    assert sports._SCHED["ref"] is b


def test_brain_knows_what_the_engine_weighs():
    """10/1, the owner: "the brain on the dashboard needs to be updated - every day." It lists what the engine weighs
    (from the live constants) and the lead tracker's grades."""
    import sports_dashboard as d
    w = d.engine_weights()
    assert "Lock" in w["the board"] and "NHL" in w["dog gates (the whole dog score)"] and "every one that clears the bar" in w["early plays"]
    import inspect
    assert '"leads being tested (graded every day)"' in inspect.getsource(d)


def test_hockey_goalie_slump():
    """10/1 daily study: a hockey favorite whose goalie is slumping (last-10 save % bottom quarter) beat its price 5 of 5
    seasons - +1.5 pts on its weighed read; the dog facing it -2 on its score."""
    import sports_form
    keep = (dict(sports_form.LAST_SV), set(sports.SV_SLUMP))
    try:
        sports_form.LAST_SV.clear(); sports_form.LAST_SV.update({"F": 0.870, "G": 0.905})
        assert sports_form.sv_slump() == {"F"}
        sports.SV_SLUMP.clear(); sports.SV_SLUMP.update({"F"})
        fav = {**_cand("g", -140, 0.57, league="nhl"), "team_id": "F", "start": "2025-12-01T00:00Z", "p_market": 0.565,
               "side": "home"}
        dog = {**_cand("g", 120, 0.43, league="nhl"), "team_id": "D", "start": "2025-12-01T00:00Z", "p_market": 0.435,
               "side": "away", "dog_ctx": {}}
        f2, d2 = dict(fav), dict(dog)
        sports.SV_SLUMP.clear()
        sports.mark_hockey_favorites([f2, d2])
        sports.SV_SLUMP.update({"F"})
        sports.mark_hockey_favorites([fav, dog])
        assert abs(fav["w_p"] - f2["w_p"] - 0.015) < 1e-9 and dog.get("opp_sv_slump")
        assert sports.dog_spots(dog) - sports.dog_spots(d2) == -2
    finally:
        sports_form.LAST_SV.clear(); sports_form.LAST_SV.update(keep[0])
        sports.SV_SLUMP.clear(); sports.SV_SLUMP.update(keep[1])


def test_steep_lean_says_why_its_not_the_lock():
    """10/1, the owner: "the algorithm should have said we couldn't label this a lock simply because the price isn't
    worth it." A lean the engine has at 56%+ whose price is too steep says so on its card; a coin flip doesn't."""
    import sports_dashboard as d
    st = {**_cand("pit", -148, 0.572, league="nfl"), "edge_own": 0.587 * sd.decimal(-148) - 1, "team": "Steelers"}
    line = d._units_line(0, "Steelers", -148, lean=True, leg=st)
    assert "-148" in line and "NO UNITS" in line and "Steelers" in line and "%" not in line and "in 100" not in line
    #   (the owner, 10/1: the likelier winner, a bad bet at the price - plain words, never number-vs-number jargon)
    coin = {**_cand("buf", -108, 0.501, league="nhl")}
    assert d._units_line(0, "Sabres", -108, lean=True, leg=coin) == '<div class="un">🟡 NO UNITS — JUST A LEAN</div>'
    worth = {**_cand("unt", -112, 0.58, league="ncaaf"), "edge_own": 0.589 * sd.decimal(-112) - 1}
    assert d._steep_line(worth) == ""                      # worth its price: never "too steep"
    assert len(d.STEEP) >= 12 and not any("likeliest" in x or "on the board" in x or "label" in x or "%" in x for x in d.STEEP)   # many ways to say it, never "the
    d.WHY_USED.clear()                                                         # likeliest on the board" (10/1)
    two = {d._steep_line({**st, "team": t}, t) for t in ("Steelers", "Lions")}
    assert len(two) == 2                                                       # never the same line twice on a page


def test_early_plays_one_minimum_two_max():
    """10/1, the owner: "one minimum, two max early value plays - get them today before the line moves." A week the spots
    find nothing: from Wednesday 6 AM PT the engine's best weighed dog goes up (a 2nd only if it clears the normal bar);
    never once the week has one; never a dog whose whole weighed total is under its price."""
    import sports_early as se
    keep, keep_min = se.spot_scan, se.SPOT_MIN_WEEK
    se.SPOT_MIN_WEEK = 1                                       # (the rule itself, as built - paused live 10/1)
    try:
        rows = [{"game_id": "a", "team": "A", "score": 0.20, "start": "2026-10-04T17:00Z", "spot": "best"},
                {"game_id": "b", "team": "B", "score": 0.08, "start": "2026-10-04T17:00Z", "spot": "best"},
                {"game_id": "c", "team": "C", "score": 0.02, "start": "2026-10-04T17:00Z", "spot": "best"}]
        se.spot_scan = lambda *a, **k: [dict(r) for r in rows]
        thu = datetime(2026, 10, 1, 20, tzinfo=timezone.utc)                 # Thursday 1 PM PT
        assert [c["game_id"] for c in se.min_one({}, {"picks": []}, thu, {}, None)] == ["a", "b"]
        tue = datetime(2026, 9, 29, 20, tzinfo=timezone.utc)                 # Tuesday: the spots get the first shot
        assert se.min_one({}, {"picks": []}, tue, {}, None) == []
        had = {"picks": [{"spot": "bye", "posted": "2026-09-30T14:00Z"}]}
        assert se.min_one({}, had, thu, {}, None) == []
        rows[:] = [{**r, "score": -0.01} for r in rows]
        assert se.min_one({}, {"picks": []}, thu, {}, None) == []
    finally:
        se.spot_scan, se.SPOT_MIN_WEEK = keep, keep_min
    assert se.units({"spot": "best", "odds": 120}) == 0.5


def test_no_only_one_that_counts():
    """10/1, the owner: "this team's record is so-and-so - tonight's the only one that counts. That don't make no sense."
    Gone from every write-up, and on the NEVER list so it can't come back."""
    import sports_owner_lingo as L
    for f in L.SOURCES:
        txt = open(f).read().lower()
        for w in ("only one that counts", "only this one matters", "clean slate tonight", "tonight's what counts"):
            assert w not in txt, (f, w)
    assert "only one that counts" in L.NEVER


def test_tracker_follows_the_engines_big_disagreements():
    """10/1, the owner (the Jaguars): "if the engine's right, it beat the line - it should believe in itself." Every dog
    the engine's own read likes 12+ pts over the line is tracked, so we learn whether those reads are right."""
    import sports_leads
    jags = {**_cand("jax", 120, 0.44, league="nfl"), "edge_own": 0.608 * sd.decimal(120) - 1, "p_market": 0.436,
            "dog_ctx": {}}
    assert "engine read 12+ over the line (believe it?)" in sports_leads.tags(jags, sports)
    mild = {**jags, "edge_own": 0.47 * sd.decimal(120) - 1}
    assert "engine read 12+ over the line (believe it?)" not in sports_leads.tags(mild, sports)


def test_early_play_reason_in_plain_words():
    """10/1, the owner: "'blew somebody out last week' is very vague - reword it." The early play says what happened."""
    import sports_early as se
    G = {"p": {"id": "p", "league": "nfl", "start": "2026-09-28T17:00Z", "home": "J", "away": "N", "home_name": "Jaguars",
               "away_name": "Patriots", "home_score": "35", "away_score": "6", "status": "final", "stype": "2"},
         "g": {"id": "g", "league": "nfl", "start": "2026-10-04T17:00Z", "home": "C", "away": "J", "home_name": "Bengals",
               "away_name": "Jaguars", "status": "pre", "stype": "2"}}
    whys = se.spot_why(se._schedule(G), G["g"], "away", "home", "nfl", "blowout", datetime(2026, 10, 1, tzinfo=timezone.utc),
                       0.608, 120)
    why = whys[0]
    assert "beat Patriots 35-6 on Monday 9/28" in why and "Blew somebody out" not in why, why
    keep_on, se.ON = se.ON, True                                    # (another test may switch the box off)
    html = se.html({"picks": [{"team": "Jaguars", "opp": "Bengals", "league": "nfl", "odds": 120, "spot": "blowout",
                               "why": why, "start": "2030-10-04T17:00Z", "game_id": "g"}]}, lambda x: x,
                   now=datetime(2030, 10, 1, tzinfo=timezone.utc))
    se.ON = keep_on
    assert "35-6" in html


def test_never_false_info_on_a_card():
    """The owner, 10/1: 'North Texas is not 0-1 ... they're 2-2. Our engine cannot have false information.' The 2026
    college feed held 1 of their 4 games. A college team whose games we don't all hold gets no record, streak, last game
    or series line; even records never say 'better'; a read under the price never reads like value; the bottom line
    always says our read vs what the price needs."""
    import sports_breakdown_v24 as v24
    G = {}
    def gm(i, day, a, h, sa, sh, an=None, hn=None):
        G[f"ncaaf:{i}"] = {"id": f"ncaaf:{i}", "league": "ncaaf", "start": f"2026-{day}T23:00Z", "status": "final",
                           "home": h, "away": a, "home_name": hn or h, "away_name": an or a, "home_score": str(sh),
                           "away_score": str(sa), "stype": "2", "neutral": "0", "elev": "100"}
    i = 0
    for w, day in enumerate(("09-05", "09-12", "09-19", "09-26")):
        for k in range(0, 20, 2):                                   # 20 fully-covered teams, a game every week
            i += 1
            gm(i, day, f"T{k}", f"T{(k + 2 * w + 1) % 20}", 10, 20)
    i += 1
    gm(i, "09-05", "NT", "T0", 16, 52, an="North Texas")              # the one North Texas game we hold
    G["g"] = {"id": "g", "league": "ncaaf", "start": "2026-10-02T23:00Z", "status": "pre", "home": "TU", "away": "NT",
              "home_name": "Tulsa", "away_name": "North Texas", "home_score": "", "away_score": "", "stype": "2",
              "neutral": "0", "elev": "100"}
    fin = [x for x in G.values() if x["status"] == "final"]
    when = v24._t("2026-10-02T23:00Z")
    assert not v24.seen_all(fin, "NT", when, "ncaaf") and v24.seen_all(fin, "T0", when, "ncaaf")
    assert v24.seen_all(fin, "NT", when, "nfl")                     # pro leagues: every game is in the feed
    leg = {"game_id": "g", "league": "ncaaf", "side": "away", "team": "North Texas", "opp": "Tulsa", "market": "ml",
           "odds": -122, "dec": 1 / 0.55, "p": 0.52, "edge_own": 0.61 / 0.55 - 1, "tier": "lock", "reasons": []}
    bd = v24.breakdown(dict(leg), G, {}, {}, set())
    assert not any("0-1" in x or "1-0" in x for x in bd), bd
    jargon = ("in 100", "price needs", "break even", "break-even", "55%")   # (10/1, the owner: "50 out of 100, the
    for seed in range(6):                                                  # price needs 48" is jargon - plain words)
        bd_ = v24.breakdown(dict(leg), G, {}, {}, {f"x{seed}"})
        bl = [x for x in bd_ if x.startswith("✅")][0]
        assert not any(j in bl for j in jargon) and "lean" not in bl.lower(), bl
    steep = {**leg, "edge_own": 0.59 / 0.6 - 1, "dec": 1 / 0.6, "odds": -150, "tier": "lean"}
    last = [x for x in v24.breakdown(steep, G, {}, {}, set()) if x.startswith("✅")][0]
    assert ("lean" in last.lower() or "steep" in last or "not the price" in last) and not any(j in last for j in jargon), last
    assert not any(w in last for w in ("That's the value", "the edge", "Tap in", "Get in")), last
    src = open(v24.__file__).read()
    assert "_w(_ru) > _w(_rt)" in src and "_w(_rt) > _w(_ru)" in src   # 2-1 vs 2-1 is never 'the better squad'


def test_early_college_spot_needs_every_game():
    """10/1: Delaware went up as a 'bye-week dog' - they'd played at Virginia 9/26, we just didn't have the game. A
    college early spot only fires when we hold every game both teams played this season."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_early.py")).read()
    i = src.index('if lg == "ncaaf":                                    # (10/1: Delaware')
    assert "seen_all(cfin, g[\"home\"]" in src[i:i + 600] and "continue" in src[i:i + 700]


def test_early_box_says_how_the_line_moved():
    """The owner, 10/1: the WE GOT IN EARLY row explains the move in our words - 'the line moved in our favor, let's go
    to work' / 'got worse for us, but this still gon' smack' - with the real numbers; nothing once it's graded."""
    import sports_early as se
    p = {"team": "Jaguars", "odds": 120, "game_id": "nfl:1"}
    for call, now in (("🔥 we beat the line", -105), ("💰 better price now", 135), ("👀 money went against it", 140),
                      ("", 120)):
        s = se.move_say(p, now, call)
        assert "+120" in s and (str(now) if now < 0 else f"+{now}") in s, s
    assert se.move_say({**p, "result": "won"}, 110, "🔥 we beat the line") == ""
    assert se.move_say(p, None, "") == ""



def test_data_gaps_every_sport():
    """The owner, 10/1: 'we can never have false information - we always have to have updated data', every sport. A
    team whose result from the last 10 days never came in (any league), or a college team we don't hold every game for,
    is a data gap: no pick on that game, and a missing result holds the opening board for a re-pull."""
    from datetime import datetime, timezone
    now = datetime(2026, 10, 1, 20, tzinfo=timezone.utc)
    G = {"old": {"id": "old", "league": "nhl", "start": "2026-09-29T23:00Z", "status": "pre", "home": "A", "away": "B",
                 "home_name": "Hawks", "away_name": "Blues", "ml_home": "-140"},
         "now": {"id": "now", "league": "nhl", "start": "2026-10-02T23:00Z", "status": "pre", "home": "A", "away": "C",
                 "home_name": "Hawks", "away_name": "Stars"},
         "ok": {"id": "ok", "league": "nhl", "start": "2026-10-02T23:00Z", "status": "pre", "home": "D", "away": "E",
                "home_name": "Kings", "away_name": "Ducks"}}
    gaps = sports.data_gaps(G, [{"game_id": "now", "league": "nhl"}, {"game_id": "ok", "league": "nhl"}], now)
    assert set(gaps) == {("nhl", "A")} and "no result" in gaps[("nhl", "A")] and "2026-09-29" in gaps[("nhl", "A")]
    G["old"]["ml_home"] = ""                                  # an "if necessary" game 3 that never got played:
    assert sports.data_gaps(G, [{"game_id": "now", "league": "nhl"}], now) == {}   # no price, not a gap (10/1)
    G["old"]["ml_home"], G["old"]["status"] = "-140", "final"
    assert sports.data_gaps(G, [{"game_id": "now", "league": "nhl"}], now) == {}
    src = open(sports.__file__).read()
    assert "DATA GAP (no pick on this game)" in src and "data_gaps(games, cands, now)" in src


def test_brain_never_says_tickets_cooking_before_a_game_starts():
    """The owner, 10/1: 'we're sitting at 0-0, there ain't no tickets that have started - that's not right.' At 0-0
    the brain says nothing's started and when the first one goes, or how many are playing right now."""
    import sports_dashboard as d
    from datetime import datetime, timezone
    ps = [{"date": "2026-10-01", "kind": "lock", "status": "open", "legs": [{"start": "2026-10-02T01:00Z"}]},
          {"date": "2026-10-01", "kind": "solo", "status": "open", "legs": [{"start": "2026-10-02T00:15Z"}]}]
    early = d.day_wait_line(ps, "2026-10-01", datetime(2026, 10, 1, 21, tzinfo=timezone.utc), 0)
    assert "5:15 PM PT" in early and "cooking" not in early and "live" not in early, early
    mid = d.day_wait_line(ps, "2026-10-01", datetime(2026, 10, 2, 0, 30, tzinfo=timezone.utc), 1)
    assert "1 of" in mid and "2" in mid, mid
    assert "groups=81" in open(sd.__file__).read()                       # FCS in the college feed: no gaps


def test_coaches_fall_back_to_last_season_never_a_false_new_coach():
    """10/1 audit: ESPN hadn't posted the 2026-27 NBA / college hoops coaches (2 of 30 NBA teams, 0 college), so the
    coach factor was blank for those sports. A team missing this season takes last season's coach (a year more
    experience) with 'new with the team' unknown (None) - never a false new-coach weight."""
    import sports_coaches as sc
    tmp = os.path.join(tempfile.mkdtemp(), "coaches.json")
    json.dump({"nba": {"2027": {"1": [{"id": "a", "exp": 5}]},
                       "2026": {"1": [{"id": "x", "exp": 3}], "2": [{"id": "b", "exp": 9}]}}}, open(tmp, "w"))
    st = sc.states("2026-10-01T21:00Z", tmp)
    assert st[("nba", "1")] == (5, True)                      # posted this season: a new coach, known
    assert st[("nba", "2")] == (10, None)                     # not posted yet: last season's man, "new" unknown
    import sports
    assert sports.coach_w({"coach": (10, None), "league": "nba", "odds": -150}) == 0.0


def test_football_drift_runs_from_the_fair_open_not_the_summer_line():
    """10/1 audit: football's 'money ran away from this dog' (-4 on the dog score) was measured from ESPN's summer
    look-ahead open - the season moving, not money. It runs from our own first fair price now; none = no drift."""
    import sports_early as se
    d = tempfile.mkdtemp()
    keep = sd.LINE_HIST_DIR
    sd.LINE_HIST_DIR = d
    try:
        G = {"p1": {"id": "p1", "league": "nfl", "start": "2026-09-27T17:00Z", "status": "final", "stype": "2",
                    "home": "A", "away": "X"},
             "p2": {"id": "p2", "league": "nfl", "start": "2026-09-27T17:00Z", "status": "final", "stype": "2",
                    "home": "B", "away": "Y"},
             "g": {"id": "g", "league": "nfl", "start": "2026-10-04T17:00Z", "status": "pre", "stype": "2",
                   "home": "A", "away": "B"}}
        se._SCHED.clear() if isinstance(getattr(se, "_SCHED", None), dict) else None
        assert sports.fair_open(G, G["g"]) is None                         # no fair price yet: no drift at all
        with open(os.path.join(d, "2026-09.jsonl"), "w") as f:
            f.write(json.dumps({"g": "g", "t": "2026-09-27T12:00Z", "h": -300, "a": 250}) + "\n")   # before the games
            f.write(json.dumps({"g": "g", "t": "2026-09-28T12:00Z", "h": -150, "a": 130}) + "\n")   # the fair open
        fo = sports.fair_open(G, G["g"])
        assert fo is not None and 0.56 < fo < 0.58, fo
    finally:
        sd.LINE_HIST_DIR = keep


def test_early_college_rain_dog_weighed():
    """10/1 audit: college rain / snow dogs (+8.1% on 822 at fair prices, 5 of 6 seasons) were standing but never
    wired - a weight on the early read now (outdoors, 0.5+ in the forecast), never a trigger, never indoors."""
    import sports_early as se
    g = {"id": "g", "league": "ncaaf", "home": "A", "away": "B", "start": "2026-10-03T17:00Z", "wx_rain": "2.0",
         "indoor": "0"}
    keep = sports._dog_more
    sports._dog_more = lambda *a, **k: {}
    try:
        assert se.lead_weights({}, g, "away", "home", "ncaaf", 0.4, 0.38) == se.LEAD_W["rain"]
        assert se.lead_weights({}, {**g, "indoor": "1"}, "away", "home", "ncaaf", 0.4, 0.38) == 0.0
        assert se.lead_weights({}, {**g, "wx_rain": "0.0"}, "away", "home", "ncaaf", 0.4, 0.38) == 0.0
        assert se.lead_weights({}, g, "away", "home", "nfl", 0.4, 0.38) == 0.0
    finally:
        sports._dog_more = keep


def test_coach_firings_refresh_this_season():
    """10/1 audit: the firing data was frozen - a season page already cached was never read again, so a coach fired
    mid-season never reached the engine (FIRED was empty). This season's pages are re-read every run; a failed read
    never wipes what we had; past seasons stay cached."""
    import sports_coach_changes as scc
    from datetime import datetime, timezone
    yr = datetime.now(timezone.utc).year
    tmp = tempfile.mkdtemp()
    keep = (scc.RAW, scc.PARSED, scc.fetch, scc.coaching_sections, scc.time.sleep)
    scc.time.sleep = lambda s_: None
    scc.RAW, scc.PARSED = os.path.join(tmp, "raw.json"), os.path.join(tmp, "parsed.json")
    json.dump({f"nfl:{yr}": {"page": "x", "sections": ["old"]}, f"nfl:{yr - 1}": {"page": "y", "sections": ["past"]}},
              open(scc.RAW, "w"))
    read = []
    scc.fetch = lambda page: read.append(page) or page
    scc.coaching_sections = lambda txt: ["new"] if str(yr) in txt and "NFL" in txt else []
    try:
        scc.run(seasons=[yr - 1, yr])
        raw = json.load(open(scc.RAW))
        assert raw[f"nfl:{yr}"]["sections"] == ["new"]                 # this season: read again
        assert raw[f"nfl:{yr - 1}"]["sections"] == ["past"]            # a past season: kept as is
        assert f"{yr - 1} NFL season" not in read
        scc.coaching_sections = lambda txt: []                          # a failed read: keeps what we had
        scc.run(seasons=[yr])
        assert json.load(open(scc.RAW))[f"nfl:{yr}"]["sections"] == ["new"]
    finally:
        scc.RAW, scc.PARSED, scc.fetch, scc.coaching_sections, scc.time.sleep = keep


def test_slate_check_holds_on_real_pull_errors_not_phantom_playoff_games():
    """10/1 audit: (1) a failed scoreboard pull ('nfl 2026-10-01: HTTP Error 500') never held the board - the error
    filter looked for words the real messages don't have; (2) three unpriced 'if necessary' playoff games that were
    never played held the 8 AM board till 8:38."""
    from datetime import date, datetime, timezone
    day = date(2026, 10, 1)
    now = datetime(2026, 10, 1, 15, tzinfo=timezone.utc)
    G = {"p": {"id": "p", "league": "mlb", "stype": "3", "status": "pre", "start": "2026-10-01T21:00Z",
               "home_name": "Astros", "away_name": "White Sox", "ml_home": "", "ml_away": ""}}
    assert sports.slate_check(G, [], day, now, errors=[]) == []
    probs = sports.slate_check(G, [], day, now, errors=["nfl 2026-10-01: HTTP Error 500", "web push: 404"])
    assert len(probs) == 1 and "HTTP Error 500" in probs[0], probs
    G["p"]["stype"] = "2"                                     # a regular-season game with no price still holds it
    assert any("no price" in x for x in sports.slate_check(G, [], day, now, errors=[]))


def test_one_input_failing_never_blanks_the_rest():
    """10/1 audit: every input the engine weighs loaded in one try block - one failure (say the coaches) left every
    input after it empty, silently. Each loads on its own now, and the double check reports what failed."""
    import sports_coaches
    keep = sports_coaches.states
    sports_coaches.states = lambda iso: 1 / 0
    try:
        G = {"g": {"id": "g", "league": "nfl", "start": "2026-09-20T17:00Z", "status": "final", "stype": "2",
                   "home": "A", "away": "B", "home_name": "Al", "away_name": "Bo", "home_score": "30", "away_score": "3",
                   "ml_home": "-150", "ml_away": "130"}}
        sports.load_states(G)
        assert sports.STATE_FAILS == ["coaches"], sports.STATE_FAILS
        assert any("coaches" in x for x in sports.factor_check(G, [], {}, None, datetime.now(timezone.utc)))
    finally:
        sports_coaches.states = keep
        sports.load_states({})
    assert sports.STATE_FAILS == []


def test_merge_keeps_a_deleted_pick_deleted():
    """10/1 audit: the picks merge ignored the base version - a pick pulled on one side came back whenever the other
    side's commit still had it. Three-way now: deleted stays deleted, unless the other side changed it (then kept)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import merge_json
    a = {"date": "2026-10-01", "kind": "lock", "round": 1, "posted": "15:00", "status": "open", "legs": []}
    b = {"date": "2026-10-01", "kind": "dog", "round": 1, "posted": "15:00", "status": "open", "legs": []}
    out = merge_json.merge_picks([a], [a, b], base=[a, b])         # ours pulled the dog, theirs didn't touch it
    assert [p["kind"] for p in out] == ["lock"], out
    graded = {**b, "status": "won"}
    out = merge_json.merge_picks([a], [a, graded], base=[a, b])    # theirs graded it meanwhile: kept, never lost
    assert {p["kind"] for p in out} == {"lock", "dog"}
    new = {**b, "posted": "16:00"}
    out = merge_json.merge_picks([a, new], [a], base=[a])          # a brand-new pick on one side: kept
    assert len(out) == 2
    assert len(merge_json.merge_picks([a], [a, b])) == 2            # no base: the old union, as before
    # (10/1: the Kraken lean vanished) two leans posted the same minute are two picks, never one
    s1 = {"date": "2026-10-01", "kind": "lean", "round": 1, "posted": "15:38", "status": "open",
          "legs": [{"game_id": "nfl:1", "side": "away", "team": "Steelers"}]}
    k1 = {**s1, "legs": [{"game_id": "nhl:2", "side": "home", "team": "Kraken"}]}
    out = merge_json.merge_picks([s1, k1], [s1, k1], base=[s1, k1])
    assert {p["legs"][0]["team"] for p in out} == {"Steelers", "Kraken"}, out
    assert len(merge_json.merge_picks([k1, s1], [s1])) == 2


def test_audit_batch_10_1():
    """10/1 audits (data, math, grading) - each a bug that was live:
    graded units re-sized after the fact (bankroll $1,059.70 -> $1,050.32); the MLB drought and the hockey early-season
    weight counted twice; a time-not-set game on the wrong day; all-star games as real games, the NBA play-in left out;
    a goalie's 'lately' from last May; '1 of 2' called owning the matchup; "UNLV' way"; a dog card as a lean."""
    import sports_breakdown_v24 as v24
    import sports_players as spl
    # units: a pick posted before the money check keeps its rule; a graded pick keeps the units it was graded at
    assert sports.kelly_units(0.40, -150, legacy=True) == 0.5 and sports.kelly_units(0.40, -150) == 0.0
    pk = {"date": "2026-10-02", "kind": "lock", "status": "won", "units": 3.0, "legs": [{"odds": -120, "p": 0.3}]}
    assert sports.units_for(pk) == 3.0
    # the drought: once in the read, never again in the ranking
    c = {"p": 0.58, "league": "mlb", "odds": -130, "drought_w": True}
    keep = sports.overreact
    sports.overreact = lambda c_: True
    try:
        assert abs(sports.rank_p(c) - (0.58 + sports.cover_run_w(c) + sports.coach_w(c) + sports.season_w(c))) < 1e-9
    finally:
        sports.overreact = keep
    # time not set / exhibitions / the play-in
    assert "5" in sd.REAL and sd.exhibition({"league": "nba", "home_name": "Team Stars", "away_name": "Team Stripes"})
    assert sd.exhibition({"league": "mlb", "home_name": "American", "away_name": "National"})
    assert not sd.exhibition({"league": "nba", "home_name": "Lakers", "away_name": "Celtics"})
    assert "tbd" in sd.FIELDS
    src = open(sports.__file__).read()
    assert 'g.get("tbd") == "1"' in src
    # "lately" = the last 45 days only
    rows = [{"player": "G1", "start": "2026-05-02T00:00Z", "sa": "30", "ga": "5"}]
    assert spl.form_line("nhl", "G1", rows, "2026-10-02T00:00Z") == (None, None)
    assert spl.form_line("nhl", "G1", rows, "2026-05-10T00:00Z")[0]
    # possessives, records = regular season, streaks = this season
    assert v24._pos("UNLV") == "UNLV's" and v24._pos("Steelers") == "Steelers'"
    bsrc = open(v24.__file__).read()
    assert "2 * w > len(last3)" in bsrc and "r_ours = [x for x in s_ours if" in bsrc and "heat = _streak(s_ours, tid)" in bsrc
    assert "it ain't close" not in bsrc and '"k_rival"' not in bsrc
    dsrc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert 'p["kind"] not in ("lock", "dog")' in dsrc


def _summ(hs, as_, plays=(), per=4, detail="Final", lines=None, key="scoringPlays", drives=None):
    """A tiny fake ESPN game summary (home team id 1, away 2) - for the decider tests, no network."""
    lines = lines or ((), ())
    comp = {"competitors": [{"homeAway": "home", "score": str(hs), "team": {"id": "1"},
                             "linescores": [{"displayValue": str(x)} for x in lines[0]]},
                            {"homeAway": "away", "score": str(as_), "team": {"id": "2"},
                             "linescores": [{"displayValue": str(x)} for x in lines[1]]}],
            "status": {"period": per, "type": {"detail": detail}}}
    p = {"header": {"competitions": [comp]}, key: list(plays)}
    if drives:
        p["drives"] = {"previous": drives}
    return p


def _sp(h, a, per, clock, text, typ="", team="1", half=""):
    return {"homeScore": h, "awayScore": a, "period": {"number": per, "type": half}, "clock": {"displayValue": clock},
            "text": text, "type": {"text": typ}, "team": {"id": team}, "scoringPlay": True}


def test_decider_finds_how_the_game_was_decided():
    """10/1, the owner: "reviews say how it was won or lost" - a last-second field goal, a blocked kick, a pick-six,
    overtime, a walk-off, an empty-netter, a late comeback. Each one read from ESPN's game summary (fake ones here),
    told from OUR side, short, with the real names and numbers."""
    import sports_decider as D
    import sports_owner_lingo as L

    def both(lg, d, us="the Chiefs", them="the Bills"):
        w = D.say(d, "home", us, them, lg, "s1")
        l_ = D.say(d, "away", them, us, lg, "s1")
        for x in (w, l_):
            assert x and len(x) <= D.MAX_LEN and "{" not in x and "None" not in x, (d, x)
            assert not any(n in x.lower() for n in L.NEVER), x
        return w, l_
    # overtime, won on a field goal
    ot = D.parse("nfl", _summ(10, 7, [_sp(0, 7, 1, "5:00", "Josh Allen 3 Yd Run (Tyler Bass Kick)", "Rushing Touchdown", "2"),
                                      _sp(7, 7, 4, "9:00", "Travis Kelce 12 Yd pass from Patrick Mahomes (Harrison Butker Kick)", "Passing Touchdown"),
                                      _sp(10, 7, 5, "2:11", "Harrison Butker 52 Yd Field Goal", "Field Goal Good")],
                                 per=5, detail="Final/OT"))
    assert ot["type"] == "ot" and ot["p"] == "Harrison Butker" and ot["y"] == 52 and ot["win"] == "home", ot
    w, l_ = both("nfl", ot)
    assert re.search(r"overtime|OT", w) and "52" in w and l_.startswith(("Lost", "The Chiefs won")) and re.search(r"overtime|OT", l_), (w, l_)
    # hockey shootout
    so = D.parse("nhl", _summ(3, 2, per=5, detail="Final/SO"))
    assert so["type"] == "so" and "shootout" in D.say(so, "away", "the Kings", "the Ducks", "nhl", "x")
    # walk-off
    wo = D.parse("mlb", _summ(4, 3, [_sp(2, 0, 3, "", "Giancarlo Stanton homered to left (402 feet), Juan Soto scored."),
                                     _sp(2, 3, 8, "", "Rafael Devers doubled to right, two scored.", team="2"),
                                     _sp(4, 3, 9, "", "Aaron Judge homered to left (410 feet), Juan Soto scored.", half="Bottom")],
                             per=9, key="plays"))
    assert wo["type"] == "walkoff" and wo["p"] == "Aaron Judge" and wo["w"] == "homer" and wo["n"] == 9, wo
    w, l_ = both("mlb", wo, "the Yankees", "the Red Sox")
    assert "9th" in w + l_ and "Judge" in w and ("walk" in l_.lower()), (w, l_)
    # a go-ahead field goal with 0:03 left
    late = D.parse("nfl", _summ(20, 17, [_sp(7, 0, 1, "8:00", "CeeDee Lamb 20 Yd pass from Dak Prescott (Brandon Aubrey Kick)", "Passing Touchdown"),
                                         _sp(7, 17, 3, "4:00", "Saquon Barkley 5 Yd Run (Jake Elliott Kick)", "Rushing Touchdown", "2"),
                                         _sp(17, 17, 4, "6:00", "CeeDee Lamb 40 Yd pass from Dak Prescott (Brandon Aubrey Kick)", "Passing Touchdown"),
                                         _sp(20, 17, 4, "0:03", "Brandon Aubrey 52 Yd Field Goal", "Field Goal Good")]))
    assert late["type"] == "late" and late["c"] == "0:03" and late["y"] == 52 and late["k"] == "fg", late
    w, l_ = both("nfl", late, "the Cowboys", "the Eagles")
    assert "0:03" in w and "0:03" in l_ and "52" in w + l_, (w, l_)
    # their kick got blocked at the end (no late score)
    blk = D.parse("nfl", _summ(20, 17, [_sp(14, 0, 2, "3:00", "A 1 Yd Run (B Kick)", "Rushing Touchdown"),
                                        _sp(14, 17, 3, "1:00", "C 3 Yd Run (D Kick)", "Rushing Touchdown", "2"),
                                        _sp(17, 17, 3, "0:10", "E 30 Yd Field Goal", "Field Goal Good", "1"),
                                        _sp(20, 17, 4, "9:00", "E 41 Yd Field Goal", "Field Goal Good", "1")],
                                  drives=[{"team": {"id": "2"}, "plays": [
                                      {"text": "Jake Elliott 48 yard field goal is BLOCKED", "type": {"text": "Blocked Field Goal"},
                                       "period": {"number": 4}, "clock": {"displayValue": "1:10"}}]}]))
    assert blk["type"] == "kick" and blk["blocked"] and blk["c"] == "1:10" and blk["y"] == 48, blk
    w, l_ = both("nfl", blk)
    assert "1:10" in w and "blocked" in l_.lower() and "1:10" in l_, (w, l_)
    # a missed one
    miss = D.parse("ncaaf", _summ(20, 17, [_sp(20, 17, 2, "3:00", "A 1 Yd Run (B Kick)", "Rushing Touchdown")],
                                  drives=[{"team": {"id": "2"}, "plays": [
                                      {"text": "Will Reichard 45 yd field goal is no good, wide right", "type": {"text": "Field Goal Missed"},
                                       "period": {"number": 4}, "clock": {"displayValue": "0:02"}}]}]))
    assert miss["type"] == "kick" and not miss["blocked"] and miss["y"] == 45
    assert "0:02" in D.say(miss, "away", "Alabama", "Auburn", "ncaaf", "q")
    # a pick-six that swung it
    p6 = D.parse("nfl", _summ(24, 20, [_sp(0, 10, 1, "2:00", "x 2 Yd Run", "Rushing Touchdown", "2"),
                                       _sp(10, 10, 2, "5:00", "y 9 Yd Run", "Rushing Touchdown"),
                                       _sp(17, 10, 3, "7:00", "Trent McDuffie 34 Yd Interception Return (Harrison Butker Kick)", "Interception Return Touchdown"),
                                       _sp(24, 20, 4, "6:00", "z 1 Yd Run", "Rushing Touchdown")]))
    assert p6["type"] == "dtd" and p6["how"] == "pick-six" and p6["p"] == "Trent McDuffie", p6
    w, l_ = both("nfl", p6)
    assert "pick-six" in w and "pick-six" in l_ and "swung" in w
    # an empty-netter that sealed it
    en = D.parse("nhl", _summ(3, 1, [_sp(1, 0, 1, "10:00", "William Nylander (3) Snap Shot"),
                                     _sp(1, 1, 2, "8:00", "Sidney Crosby (2) Wrist Shot", team="2"),
                                     _sp(2, 1, 3, "12:00", "Mitch Marner (4) Backhand"),
                                     _sp(3, 1, 3, "0:45", "Auston Matthews (12) Wrist Shot, Empty Net")], per=3, key="plays"))
    assert en["type"] == "en" and en["p"] == "Auston Matthews" and en["s"] == "3-1", en
    w, l_ = both("nhl", en, "the Maple Leafs", "the Penguins")
    assert "empty" in w.lower() and "empty" in l_.lower()
    # a big comeback (in-game) and one from the period scores only
    cb = D.parse("nfl", _summ(28, 21, [_sp(0, 7, 1, "9:00", "a", "Rushing Touchdown", "2"), _sp(0, 14, 1, "2:00", "b", "Rushing Touchdown", "2"),
                                       _sp(0, 21, 2, "4:00", "c", "Rushing Touchdown", "2"), _sp(7, 21, 2, "0:30", "d", "Rushing Touchdown"),
                                       _sp(14, 21, 3, "6:00", "e", "Rushing Touchdown"), _sp(21, 21, 4, "12:00", "f", "Rushing Touchdown"),
                                       _sp(28, 21, 4, "8:00", "g", "Rushing Touchdown")]))
    assert cb["type"] == "comeback" and cb["d"] == 21, cb
    w, l_ = both("nfl", cb)
    assert "21" in w and "21" in l_ and "lead" in l_, (w, l_)
    cb2 = D.parse("nhl", _summ(4, 3, per=3, lines=((0, 2, 2), (3, 0, 0))))
    assert cb2["type"] == "comeback" and cb2["d"] == 3
    # a blowout (the halftime score) and nothing big at all
    bo = D.parse("nfl", _summ(41, 10, lines=((14, 14, 7, 6), (3, 0, 7, 0))))
    assert bo["type"] == "blowout" and bo["h"] == "28-3" and bo["s"] == "41-10"
    w, l_ = both("nfl", bo)
    assert "41-10" in w and "41-10" in l_
    assert D.parse("nfl", _summ(27, 20, [_sp(0, 3, 1, "9:00", "k 30 Yd Field Goal", "Field Goal Good", "2"),
                                         _sp(7, 3, 2, "9:00", "a 2 Yd Run", "Rushing Touchdown")])) == {}
    assert D.parse("nfl", {"header": {}}) is None and D.say({}, "home", "a", "b", "nfl", "s") == ""


def test_decider_fetched_once_and_never_blocks_grading():
    """One summary per graded game (kept in deciders.json); a failed fetch leaves the leg alone (tried again next run,
    3 tries, then nothing) - grading never waits on it."""
    import sports_decider as D
    keep, tmp = sd.DATA, tempfile.mkdtemp()
    sd.DATA = tmp
    try:
        calls = []

        def fetch(lg, eid):
            calls.append(eid)
            p_ = _summ(41, 10, lines=((14, 14, 7, 6), (3, 0, 7, 0)))
            p_["header"]["id"] = eid                              # (the summary carries its own event id)
            return p_
        picks = [{"legs": [{"game_id": "nfl:9", "result": "won", "side": "home"},
                           {"game_id": "nfl:9", "result": "lost", "side": "away"},
                           {"game_id": "nfl:10", "result": None}]}]
        D.fill(picks, fetch=fetch)
        assert calls == ["9"] and picks[0]["legs"][0]["decider"]["type"] == "blowout"
        assert picks[0]["legs"][1]["decider"]["type"] == "blowout" and "decider" not in picks[0]["legs"][2]
        again = [{"legs": [{"game_id": "nfl:9", "result": "won", "side": "home"}]}]
        D.fill(again, fetch=fetch)
        assert calls == ["9"] and again[0]["legs"][0]["decider"]["type"] == "blowout", "fetched once"

        def down(lg, eid):
            raise OSError("ESPN down")
        bad = [{"legs": [{"game_id": "nhl:5", "result": "lost", "side": "home"}]}]
        for i in range(D.MAX_TRIES - 1):
            D.fill(bad, fetch=down)
            assert "decider" not in bad[0]["legs"][0], "a failed fetch: tried again next run"
        D.fill(bad, fetch=down)
        assert bad[0]["legs"][0]["decider"] == {}, "3 tries, then the review goes without it"
        # (the owner, 10/1: "it can't be from a past season") a summary for ANOTHER game is never used, and a decider
        # whose final isn't the score we graded is never said
        other = [{"legs": [{"game_id": "nfl:77", "result": "won", "side": "home"}]}]
        D.fill(other, fetch=lambda lg, eid: {**_summ(41, 10), "header": {**_summ(41, 10)["header"], "id": "12345"}})
        assert other[0]["legs"][0]["decider"] == {}
        mism = [{"legs": [{"game_id": "nfl:9", "result": "won", "side": "home", "score": "Bills 17 @ Jets 20"}]}]
        D.fill(mism, fetch=fetch)
        assert mism[0]["legs"][0]["decider"] == {}
        ok = [{"legs": [{"game_id": "nfl:9", "result": "won", "side": "home", "score": "Bills 10 @ Jets 41"}]}]
        D.fill(ok, fetch=fetch)
        assert ok[0]["legs"][0]["decider"]["type"] == "blowout"
    finally:
        sd.DATA = keep
        shutil.rmtree(tmp)


def test_review_says_how_it_was_won_or_lost():
    """The graded review tells the decider from OUR side - win or loss - in about the same length as the old line,
    never with banned words, no hype on a lean. No decider (or a spread we covered while losing the game) = the usual
    review, still there."""
    import html as html_
    import sports_dashboard as dash
    import sports_decider as D
    import sports_lingo as sl
    import sports_owner_lingo as L
    keep, tmp = sd.DATA, tempfile.mkdtemp()
    sd.DATA = tmp
    try:
        late = {"type": "late", "win": "home", "s": "20-17", "p": "Brandon Aubrey", "k": "fg", "y": 52, "c": "0:03"}
        blk = {"type": "kick", "win": "away", "s": "20-17", "blocked": True, "c": "1:10", "y": 48}

        def pk(date, side, res, dec, lean=False, market="ml", line=None):
            l = {"game_id": f"nfl:{date}{side}", "league": "nfl", "side": side, "team": "Cowboys", "opp": "Eagles",
                 "market": market, "odds": -120, "line": line, "result": res, "p": 0.6, "score": "Eagles 17 @ Cowboys 20"}
            if dec is not None:
                l["decider"] = dec
            return {"date": date, "kind": "lean" if lean else "lock", "status": res, "lean": lean, "legs": [l], "american": -120}
        picks = [pk("2026-09-20", "home", "won", late), pk("2026-09-21", "home", "lost", blk),
                 pk("2026-09-22", "home", "won", late, lean=True), pk("2026-09-23", "home", "won", None),
                 pk("2026-09-24", "away", "won", late, market="spread", line=6.5)]
        page = html_.unescape(dash._history(picks))
        revs = re.findall(r"📝 (.*?)</div>", page)
        assert len(revs) >= 5 and all(revs), revs
        won = dash.LEG_REVIEWS[("2026-09-20", "nfl:2026-09-20home|home|ml")]
        lost = dash.LEG_REVIEWS[("2026-09-21", "nfl:2026-09-21home|home|ml")]
        lean = dash.LEG_REVIEWS[("2026-09-22", "nfl:2026-09-22home|home|ml")]
        plain = dash.LEG_REVIEWS[("2026-09-23", "nfl:2026-09-23home|home|ml")]
        cover = dash.LEG_REVIEWS[("2026-09-24", "nfl:2026-09-24away|away|spread")]
        assert "0:03" in won and not won.startswith("Lost"), won
        assert "1:10" in lost and "block" in lost.lower(), lost
        assert "0:03" in lean and not sl.LEAN_BAN.search(lean), lean
        assert plain and "0:03" not in plain, "no decider: the usual review"
        assert "0:03" not in cover, "we covered while the game was lost: the decider isn't our story"
        for r in (won, lost, lean):
            assert len(r) <= sl.HOW_CAP and not any(n in r.lower() for n in L.NEVER), r
        assert dash._history(picks) == dash._history(picks), "the same words every run"
        # the cache (no decider on the leg yet) works too
        json.dump({"nfl:77": late}, open(os.path.join(tmp, "deciders.json"), "w"))
        p2 = [pk("2026-09-25", "home", "won", None)]
        p2[0]["legs"][0]["game_id"] = "nfl:77"
        dash._history(p2)
        assert "0:03" in dash.LEG_REVIEWS[("2026-09-25", "nfl:77|home|ml")]
    finally:
        sd.DATA = keep
        shutil.rmtree(tmp)
    assert "sports_decider.fill" in open("sports.py").read() and "def deciders(" in open("sports.py").read()

def test_build_your_own_parlay_line_on_top():
    """The owner, 10/1: '🧩 Build your own parlay from today's plays' goes AT THE TOP of the day's board (it sat
    under the last play card, where nobody saw it) - whenever there are 2+ straight picks up."""
    import sports_dashboard as d
    from datetime import date
    picks = [{"kind": "lock", "status": "open", "legs": []}, {"kind": "play", "status": "open", "legs": []}]
    html = d._cards(date(2026, 10, 1), picks, [("lock", "<div>LOCK</div>"), ("play", "<div>PLAY</div>")])
    assert "🧩 Build your own parlay" in html and html.index("🧩") < html.index("LOCK"), html[:300]
    one = d._cards(date(2026, 10, 1), picks[:1], [("lock", "<div>LOCK</div>")])
    assert "🧩" not in one                                     # one pick: nothing to build


def test_never_trash_a_team_with_our_record():
    """The owner, 10/1: 'we said New Mexico State's been complete ass - Western Kentucky has the same record.' The
    trash-talk / cold lines about the other side only run when our record is better."""
    import sports_breakdown_v24 as v24
    src = open(v24.__file__).read()
    assert "better = e is None or e.r.get(tid, 1500.0) > rating_them" in src     # (the owner: a record doesn't
    assert "if better and ((len(r_theirs) >= 3" in src                          # show who they played - ratings do)
    assert "abs(gap) <= 15" in src and "tougher schedule" in src


def test_college_football_stays_on():
    """The owner, 10/1: the strength study flipped college football to 'weak' (0.06 pts under the price on 463 picks)
    and shut off the whole college slate - 'turn it back on'. It never reads weak, whatever strength.json says."""
    import sports_strength as ss
    keep = ss._load
    ss._load = lambda: {"ncaaf": {"weak": True}, "nba": {"weak": True}}
    try:
        assert not ss.weak("ncaaf") and not ss.weak("nba")              # (10/3: the owner turned the NBA on too)
    finally:
        ss._load = keep


def test_pick_rules_audit_10_1():
    """10/1 pick-rules audit: (1) a one-game day's Dog must pass the money check, or it stays the game's pick (it got
    0u, was pulled, and left a Monday / Thursday game with no pick); (2) the backup Lock is never past +125; (3) an early
    play's 3-day window holds on every path (the Jaguars went up 95h after its fair number); (4) the early read over
    the price is capped like the game-day dog score (big reads are traps); (5) never past 2 early plays a week."""
    src = open(sports.__file__).read()
    assert 'dog_score(solo) > 0 and beats_price(solo)' in src
    assert 'MAX_FAV <= c["odds"] <= PLUS_LOCK_MAX and c.get("edge_own") is not None' in src
    plus = {"market": "ml", "odds": 150, "dec": 2.5, "edge_own": 0.6 * 2.5 - 1, "reasons": ["r"], "league": "mlb",
            "p": 0.45, "p_market": 0.4}
    keep = sports.fighting
    sports.fighting = lambda c: False
    try:
        assert sports.backup_lock([plus]) is None
    finally:
        sports.fighting = keep
    import sports_early as se
    esrc = open(se.__file__).read()
    assert "if r and now > r + timedelta(hours=SPOT_WINDOW_H):\n" in esrc
    assert 'gap = 0.0 if lg in ("nfl", "nba") else sports_own_cap() / 100' in esrc
    assert "if room <= 0:" in esrc


def test_position_words_by_sport():
    """The owner, 10/1: 'the Browns are playing without the goalie?' - a football G is a guard (Teven Jenkins). The
    position letter becomes a word by the SPORT: hockey G = goalie, football / hoops G = guard."""
    import sports_breakdown_v24 as v24
    assert v24._posname("G", "nfl") == "guard" and v24._posname("G", "ncaaf") == "guard"
    assert v24._posname("G", "nhl") == "goalie" and v24._posname("G", "nba") == "guard"
    assert v24._posname("C", "mlb") == "catcher" and v24._posname("D", "nhl") == "defenseman"
    assert v24._posname("QB", "nfl") == "quarterback"
    src = open(v24.__file__).read()
    assert "_posname(key_them[0][1])" not in src and "_posname(m.group(2))" not in src
def test_one_game_day_pick_always_has_units():
    """The owner, 10/1: 'on a one-game day we always put units on - a Lock, the Dog, or a value play with units.' The
    day's one pick carries units even when its read doesn't clear the money check (½u floor), and the rule check never
    pulls it for that."""
    leg = {"odds": -130, "dec": sd.decimal(-130), "p": 0.55, "edge_own": -0.02, "market": "ml", "league": "nfl",
           "team": "Bears", "game_id": "g1", "side": "home"}
    pk = {"kind": "solo", "date": "2026-10-05", "status": "open", "legs": [leg]}
    assert sports.units_for(pk) >= 0.5
    rich = {**leg, "edge_own": 0.6 * sd.decimal(-130) - 1}
    assert sports.units_for({**pk, "legs": [rich]}) >= sports.units_for(pk)
    probs = sports.rule_check([pk], [pk], "2026-10-05")
    assert not any("doesn't beat" in x for x in probs) and pk in [pk]


def test_card_guard_catches_every_slip_the_owner_caught():
    """The owner, 10/1: 'wire everything into the engine so it can't be making all these mistakes and then I gotta go
    tell you to fix it.' Every card line passes the guard: jargon, the wrong sport's position word, a name not set yet,
    filler, a NEVER word, a broken template - dropped (logged); a bad bottom line is cut back to the pick, never lost.
    It runs where the write-up is made AND where the page shows it."""
    import sports_card_guard as g
    import sports_breakdown_v24 as v24
    import sports_dashboard as d
    bad = [("✅ Bottom line: Western KY (+110). We see 50 in 100, the price needs 48 in 100. We finna see.", "ncaaf"),
           ("🚑 Browns gotta play this one without goalie Teven Jenkins, and we're taking advantage.", "nfl"),
           ("⚾ TBA gets the ball for Yankees against Drew Rasmussen.", "mlb"),
           ("🧳 Road game for North Texas, but they travel just fine.", "ncaaf"),
           ("📊 Real talk, the chalk is on the other side.", "nba"),
           ("🎯 None has been cooking.", "nfl")]
    for line, lg in bad:
        assert g.problem(line, lg), line
    assert g.clean([bad[0][0]], "ncaaf") == ["✅ Bottom line: Western KY (+110)."]
    good = [("🧱 Igor Shesterkin has been a brick wall in net for the Rangers.", "nhl"),
            ("🎯 Rodney Tisdale Jr. has been cooking — 4 TDs, 0 picks and 512 yards in his last 2 games.", "ncaaf"),
            ("✅ Bottom line: Western KY (+110) pays more than it should. Tap in.", "ncaaf")]
    for line, lg in good:
        assert not g.problem(line, lg), line
    assert "sports_card_guard.clean(" in open(v24.__file__).read() and "sports_card_guard.one(" in open(v24.__file__).read()
    dsrc = open(d.__file__).read()
    assert dsrc.count("sports_card_guard.") >= 2


def test_only_a_key_player_out_is_sold_as_an_edge():
    """The owner, 10/1: 'Teven Jenkins - is he even a star? If he's not a factor the engine shouldn't put that' (and
    the Mammoth / Flames depth guys). A card names a missing player as our edge ONLY when he's a key player (their QB,
    goalie, one of their best bats); a depth player never gets 'that changes the whole game'."""
    import sports_breakdown_v24 as v24
    g = {"id": "nfl:1", "start": "2026-10-02T00:15Z", "home": "5", "away": "23", "sp_home": "", "sp_away": ""}
    base = {"team": "Steelers", "opp": "Browns", "league": "nfl", "side": "away", "p": 0.58, "tier": "lean", "ctx": [],
            "reasons": ["opponent missing key players"], "opp_outs": ["Teven Jenkins (G)", "Tylan Wallace (WR)"]}
    say = lambda key_them: v24.why_line(base, v24.Voice("s", set()), g, "Steelers", "Browns", "the Steelers",
                                        "the Browns", key_them=key_them, key_us=[])
    assert "Jenkins" not in say([])                                     # a guard on the list: never our "edge"
    qb = say([("Deshaun Watson", "QB", "Out")])
    assert "Deshaun Watson" in qb and "starting quarterback" in qb, qb
    src = open(v24.__file__).read()                                     # (the owner: a team that's hella banged up -
    assert "if len(starters_out) >= 3 and len(theirs_out) - len(ours_out) >= 2:" in src   # 3+ STARTERS out (the owner:
    #                                                                     'that's what it implies') - says so, gladly)


def test_there_is_always_a_lock_near_the_price():
    """The owner, 10/1 ('yes' - there's always a Lock): the audit found no Lock on 30 of 65 days, mostly -135..-150
    favorites the engine had about 1 point short of the price. A day nothing clears the Lock test, the best own read
    (56%+) within 1 point of its price is the Lock - ½u floor, never past +125 / -150, its card honest (a small bet at a
    fair price - never 'value', never 'just a lean')."""
    fav = {"market": "ml", "odds": -140, "dec": sd.decimal(-140), "edge_own": 0.578 * sd.decimal(-140) - 1, "p": 0.57,
           "p_market": 0.57, "reasons": ["r"], "league": "mlb", "team": "Dodgers", "game_id": "m1", "side": "home"}
    far = {**fav, "edge_own": 0.55 * sd.decimal(-140) - 1, "team": "Mets", "game_id": "m2"}         # 3 pts short: no
    big = {**fav, "odds": -200, "dec": sd.decimal(-200), "edge_own": 0.66 * sd.decimal(-200) - 1, "game_id": "m3"}
    c = sports.near_lock([fav, far, big])
    assert c is fav and fav["near_price"]
    assert sports.near_lock([far, big]) is None
    pk = {"kind": "lock", "date": "2026-10-05", "status": "open", "legs": [fav]}
    assert sports.units_for(pk) >= 0.5
    assert not any("doesn't beat" in x for x in sports.rule_check([pk], [pk], "2026-10-05"))
    import sports_breakdown_v24 as v24
    src = open(v24.__file__).read()
    assert 'if leg.get("near_price"):' in src and '"bottom_near"' in src



def test_a_lean_says_the_real_reason_it_has_no_units():
    """10/1, the owner: "it says we like the Kraken, just not at this price - and the Kraken's only -108. It's not even
    expensive. That's real vague." A near coin flip says it's close to a coin flip; only a steep price blames the price;
    and a rewrite (a new wording version) keeps a lean in its lean voice."""
    import sports_breakdown as sb
    import sports_card_guard as cg
    close = sb.lean_ends({"team": "Kraken", "odds": -108, "p": 0.50, "market": "ml"})
    assert all("coin flip" in x or "50-50" in x or "close to even" in x for x in close)
    assert not any(w in x.lower() for x in close for w in ("steep", "too rich", "not at this price", "costs too much"))
    steep = sb.lean_ends({"team": "Steelers", "odds": -300, "p": 0.72, "market": "ml"})
    assert all("coin flip" not in x and "(-300)" in x for x in steep)
    dog = sb.lean_ends({"team": "Ducks", "odds": 140, "p": 0.44, "market": "ml"})
    assert all("hair" not in x for x in dog)
    assert not any(cg.problem(x) for x in close + steep + dog)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_breakdown_v24.py")).read()
    assert 'own <= need and own < 0.56' in src and "close to a coin flip - a hair better" in src   # the why line too
    leg = {"team": "Kraken", "opp": "Flames", "odds": -108, "p": 0.50, "dec": 1.926, "market": "ml", "side": "home",
           "game_id": "g1", "league": "nhl", "line": None}
    unit = {**leg, "game_id": "g2"}
    picks = [{"date": "2026-10-01", "kind": "lean", "status": "open", "lean": True, "legs": [leg]},
             {"date": "2026-10-01", "kind": "play", "status": "open", "lean": False, "legs": [unit]}]
    games = {"g1": {"status": "pre"}, "g2": {"status": "pre"}}
    keep = (sports.sd.fetch_injuries, sb.breakdown, sb.public_side, sports.sm.ratings)
    try:
        sports.sd.fetch_injuries = lambda lg: {}
        sb.breakdown = lambda *a, **k: ["📊 Kraken won 4 of their last 5.",
                                                      "✅ Bottom line: Kraken (-108). We'd ride Kraken, but not with money at this price."]
        sb.public_side = lambda *a: None
        sports.sm.ratings = lambda *a: {}
        sports.add_breakdowns(games, {}, picks)
    finally:
        sports.sd.fetch_injuries, sb.breakdown, sb.public_side, sports.sm.ratings = keep
    end = leg["breakdown"][-1]
    assert leg["breakdown"][0].startswith("📊") and end.startswith("🟡") and any(w in end for w in ("coin flip", "50-50", "close to even"))
    assert "not with money at this price" in unit["breakdown"][-1]        # (a unit play's own bottom line is untouched)


def test_midday_value_plays_ping_once_when_the_dashboard_shows_them():
    """10/1, the owner ("yes, yes, and yes"): the board drops at 8 AM, the engine keeps checking the lines all day, and a
    unit play it adds after the board is up sends ONE notification - only once the dashboard shows it. Leans never ping,
    the 8 AM board never pings, and nothing rings twice."""
    import sports_pings as spg
    from datetime import datetime, timezone
    path = os.path.join(tempfile.mkdtemp(), "play_pings.json")
    now = datetime(2026, 10, 1, 19, 23, tzinfo=timezone.utc)
    leg = {"team": "Kraken", "opp": "Flames", "odds": -108, "p": 0.56, "dec": 1.926, "market": "ml", "side": "home",
           "game_id": "nhl:1", "league": "nhl", "line": None, "start": "2026-10-02T02:00Z", "edge_own": 0.08}
    assert "vs Pitt," in spg.text({"legs": [{**leg, "league": "ncaaf", "opp": "Pitt"}], "kind": "play", "status": "open"})[1] \
        if sports.units_for({"legs": [{**leg, "league": "ncaaf"}], "kind": "play", "status": "open"}) else True
    play = {"date": "2026-10-01", "kind": "play", "status": "open", "lean": False, "midday": True,
            "posted": "2026-10-01T19:23Z", "legs": [leg]}
    lean = {**play, "kind": "lean", "lean": True, "legs": [{**leg, "game_id": "nhl:2"}]}
    morning = {**play, "midday": False, "posted": "2026-10-01T15:02Z", "legs": [{**leg, "game_id": "nhl:3"}]}
    keep = sports.units_for
    try:
        sports.units_for = lambda pk: 0 if pk.get("lean") else 1.5
        q = spg.queue([play, lean, morning], now, path)
        assert spg.queue([play], now, os.path.join(tempfile.mkdtemp(), "x.json")) and \
            (sports.__setattr__("units_for", lambda pk: 0) or not spg.queue([play], now, os.path.join(tempfile.mkdtemp(), "y.json")))
    finally:
        sports.units_for = keep                                           # (a pick with no units never pings)
    assert [x["gid"] for x in q] == ["nhl:1"], q
    assert "Kraken ML -108" in q[0]["title"] and "Flames, 1½ units." in q[0]["body"], q
    assert not any(cg_bad in q[0]["body"] for cg_bad in ("in 100", "price needs"))
    sent = []
    assert spg.send_queued("<html>no card yet</html>", now, path, sent.append) == [] and not sent   # not live: wait
    page = '<span class="tm" data-start="x" data-gid="nhl:1" data-side="home" data-mk="ml">'
    assert len(spg.send_queued(page, now, path, sent.append)) == 1 and sent[0]["ref"] == "play:2026-10-01:nhl:1"
    later = datetime(2026, 10, 1, 20, 23, tzinfo=timezone.utc)
    sports.units_for = lambda pk: 1.5
    try:
        assert spg.queue([play, lean, morning], later, path) == []       # the next run: already pinged, never twice
    finally:
        sports.units_for = keep
    assert spg.send_queued(page, later + timedelta(hours=2), path, sent.append) == [] and len(sent) == 1
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports.py")).read()
    assert 'pk["midday"] = True' in src and "sports_pings.queue(picks, now)" in src          # wired in the engine
    assert "spg.send_queued" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "early_ping.py")).read()


def test_momentum_leads_are_weights():
    """10/2, the owner: "run five studies on what changes the dynamics of a game - the crowd, nerves, pressure - across
    the sports." Two held a from-scratch re-check: an NBA team off a COMEBACK win is overpriced next game, and an MLB dog
    that lost but won the last 3 innings by 4+ is underpriced. Each is a small weight on the dog score, never a trigger;
    a broken line score never counts (no fact = no weight)."""
    nba = {"status": "final", "home": "A", "away": "B", "home_score": "101", "away_score": "99",
           "ls_home": "20,25,24,32", "ls_away": "30,25,24,20"}            # A trailed 69-79 after 3, won by 2
    assert sports.comeback_win(nba, "A") and not sports.comeback_win(nba, "B")
    assert not sports.comeback_win({**nba, "home_score": "110", "ls_home": "20,25,24,41"}, "A")   # won by 11: no
    assert not sports.comeback_win({**nba, "ls_home": "20,25,24,30"}, "A")   # line score doesn't add up: no fact
    mlb = {"status": "final", "home": "A", "away": "B", "home_score": "6", "away_score": "8",
           "ls_home": "0,0,0,1,0,0,2,1,2", "ls_away": "3,2,3,0,0,0,0,0,0"}   # lost 6-8, won the 7th-9th 5-0
    assert sports.late_rally(mlb, "A") and not sports.late_rally(mlb, "B")
    assert not sports.late_rally({**mlb, "ls_home": "0,0,0,3,0,0,1,1,1", "ls_away": "3,2,3,0,0,0,0,0,0"}, "A")   # 3-0: no
    base = {"league": "nba", "odds": 150, "dog_ctx": {}}
    assert sports.dog_spots({**base, "dog_more": {"opp_comeback": True}}) - sports.dog_spots(base) == 2
    assert sports.dog_spots({**base, "dog_more": {"comeback": True}}) - sports.dog_spots(base) == -2
    b2 = {"league": "mlb", "odds": 150, "dog_ctx": {}}
    assert sports.dog_spots({**b2, "dog_more": {"late_rally": True}}) - sports.dog_spots(b2) == 1.5
    assert sports.dog_spots({**b2, "odds": 240, "dog_more": {"late_rally": True}}) == sports.dog_spots({**b2, "odds": 240})


def test_a_live_bet_is_never_in_both_boxes_and_never_a_3way_price():
    """10/1, the owner (Devils ML +145, tied after 2, a -180 favorite at the close - in LIVE PLUS MONEY and TONIGHT'S
    LIVE BETS at once): "shouldn't be in both at the same time." A bet still up top as BET IT NOW shows there only; the
    blue box gets it once its value's gone. And a live price only ever comes from the real two-way moneyline - never a
    3-way / regulation-only line (a tie loses it, so it runs long and looks like value it isn't)."""
    import sports_books as sb
    two = [{"description": "Devils", "price": {"american": "-130"}}, {"description": "Flyers", "price": {"american": "+110"}}]
    three = two + [{"description": "Draw", "price": {"american": "+300"}}]
    assert sb.two_way("Moneyline Live Game", two)
    assert not sb.two_way("3-Way Moneyline", two) and not sb.two_way("Moneyline Regulation Time", two)
    assert not sb.two_way("Moneyline", three)
    assert not sb.two_way("Moneyline", [two[0], {"englishLabel": "X", "description": ""}])
    assert sb._kambi_ml({"betOffers": [{"criterion": {"englishLabel": "Moneyline"}, "betOfferType": {"englishName": "Match"},
                                        "outcomes": [{"englishLabel": "A"}, {"englishLabel": "Draw"}, {"englishLabel": "B"}]}]}) is None
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_live.py")).read()
    assert "sports_books.two_way(" in src
    dash = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports_dashboard.py")).read()
    assert "function today(T,up)" in dash and "if(e.result||on[e.pid])" in dash and "today(d.today,(age<10*60000&&d.plays)||[])" in dash


def test_a_favorite_tied_at_plus_money_needs_two_books():
    """10/1, the owner ("this needs fixed so it doesn't happen again"): the Devils, a -180 favorite tied after 2, went up
    at +145 - the books had them -174. Two books far apart = no price; and a pregame favorite that isn't losing at plus
    money only plays when a second book confirms that price."""
    assert sports_live.two_books((-174, 119), (145, -190)) == (None, None, False)
    assert sports_live.two_books((-174, 119), (-170, 125))[2] is True
    src = open(sports_live.__file__).read()
    assert "my >= their and (pre_market_p if side == \"home\" else 1 - pre_market_p) >= FAV_PRE" in src
    assert sports_live.FAV_PRE == 0.55
    g = {"home_name": "Devils", "away_name": "Flyers"}
    assert sports_live.book_src([{"home": "Devils", "away": "Flyers", "src": "betrivers"}], g) == "betrivers"
    assert sports_live.book_src([], g) == "?"
    assert 'log["plays"][pl["id"]]["src"] = pl["src"]' in src            # every live bet logs which book priced it


def test_a_small_edge_is_half_a_unit():
    """10/1, the owner (Western KY +110 at 1u - the engine's own read only ~1 point over the price): "a small value like
    that, probably should've been a half a unit." From 10/2: own read under 3% over the price = ½u. Posted picks keep
    their size."""
    leg = {"team": "Western KY", "odds": 110, "dec": 2.1, "p": 0.486, "dog_p": 0.501, "edge_own": 0.0099, "market": "ml"}
    assert sports.thin_edge(leg) and not sports.thin_edge({**leg, "edge_own": 0.10, "dog_p": 0.54})
    assert not sports.thin_edge({**leg, "edge_own": 0.05, "dog_p": 0.53})   # (10/2: 3% stays the line - "we can't be
    #                                                                         having half units all across the board")
    keep = (sports.pick_tier, sports.beats_price)
    try:
        sports.pick_tier = lambda pk: "value"
        sports.beats_price = lambda leg: True
        new = {"kind": "play", "date": "2026-10-02", "status": "open", "legs": [leg]}
        old = {**new, "date": "2026-10-01"}
        assert sports.units_for(new) == 0.5 and sports.units_for(old) == 1.0
        big = {**new, "legs": [{**leg, "edge_own": 0.12, "dog_p": 0.56}]}
        assert sports.units_for(big) == 0.5                               # (the 10/2 sizing replay: every value play
        #                                                                   ½u - they lost at every size)
        sports.pick_tier = lambda pk: "lock"
        lock = {**new, "kind": "lock", "legs": [{**leg, "odds": -130, "dec": 1.769, "edge_own": 0.12, "dog_p": None,
                                                 "p": 0.64}]}
        assert sports.units_for(lock) > 0.5                               # the Lock sizes by its own read
        assert sports.units_for({**new, "kind": "dog"}) == 1.0            # the Dog of the Day flat 1u
    finally:
        sports.pick_tier, sports.beats_price = keep


def test_washed_is_only_for_a_cold_long_time_starter():
    """10/1, the owner: "this dude is washed - he's old and out of his prime" (Aaron Rodgers). In his lingo now - only
    on the other side's long-time starter (100+ QB starts in our box scores) who's cold right now, with his numbers."""
    import sports_breakdown_v24 as v24
    import sports_card_guard as cg
    import sports_owner_lingo as ol
    assert "washed" in ol.OWNER and v24.VET_STARTS["QB"] == 100
    src = open(v24.__file__).read()
    assert 'if not ours_ and mood == "cold" and vet:' in src and 'role + "_washed"' in src
    for x in ("🧓 Aaron Rodgers is washed — 1 TD, 3 picks and 512 yards in his last 3 games.",
              "🧓 Father Time is catching Aaron Rodgers — 1 TD, 3 picks and 512 yards in his last 3 games. Washed."):
        assert not cg.problem(x), x


def test_every_unit_play_has_units_only_leans_dont():
    """10/1, the owner: "we do need units on value plays. The only thing that doesn't get units is leans." From 10/2 a
    value play / Lock / Dog never shows 0 units (½u at least); a lean stays at none."""
    leg = {"team": "A", "odds": 120, "dec": 2.2, "p": 0.40, "edge_own": -0.02, "market": "ml"}
    keep = (sports.pick_tier, sports.beats_price)
    try:
        sports.pick_tier = lambda pk: "value"
        sports.beats_price = lambda leg: False
        for kind, u in (("play", 0.5), ("lock", 0.5), ("dog", 1.0)):     # (the Dog flat 1u - the 10/2 sizing replay)
            assert sports.units_for({"kind": kind, "date": "2026-10-02", "status": "open", "legs": [leg]}) == u, kind
        assert sports.units_for({"kind": "lean", "lean": True, "date": "2026-10-02", "status": "open", "legs": [leg]}) == 0
    finally:
        sports.pick_tier, sports.beats_price = keep


def test_no_reasonless_crowd_line():
    """10/2 board preview: "We with the crowd tonight, but we got our own reasons." - no reason given = filler (the
    owner's never-vague rule). Gone from the pools, and the card guard drops it if it ever comes back."""
    import sports_card_guard as cg
    for f in ("sports_breakdown_v24.py", "sports_breakdown.py"):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f)).read()
        assert "got our own reasons." not in src and "got there on our own" not in src, f
    assert cg.problem("📊 91% of the bets on Penn State (30% of the money). We with the crowd tonight, but we got our own reasons.")
    assert not cg.problem("🤝 Public side on Penn State, but we got our own reasons — 4 straight W's.")


def test_every_sport_weighs_the_favorite_by_the_dog_across():
    """10/2, the owner: "make sure the engine weighs everything making its picks." The study weights (fades, spots,
    momentum, injuries) moved only the DOG's score outside hockey - a favorite like Virginia Tech never felt them. Now
    every favorite's read moves the other way: half a point per point of the dog's study score, capped at 4."""
    fav = {"game_id": "g", "league": "ncaaf", "market": "ml", "odds": -142, "dec": 1.704, "edge_own": -0.012, "p": 0.56}
    dog = {"game_id": "g", "league": "ncaaf", "market": "ml", "odds": 120, "dec": 2.2, "dog_ctx": {}, "dog_more": {}}
    own = (fav["edge_own"] + 1) / fav["dec"]
    keep = sports.dog_spots
    try:
        sports.dog_spots = lambda c: -3                                 # e.g. the dog's key player is out
        a, b = dict(fav), dict(dog)
        sports.weigh_favorites([a, b])
        assert abs(a["w_p"] - (own + 0.015)) < 1e-4 and sports.read_of(a) == a["w_p"]
        sports.dog_spots = lambda c: 20                                 # capped at 4 points
        a = dict(fav)
        sports.weigh_favorites([a, dict(dog)])
        assert abs(a["w_p"] - (own - 0.04)) < 1e-4
        sports.dog_spots = lambda c: 0                                  # nothing on the dog: the favorite's own read
        a = dict(fav)
        sports.weigh_favorites([a, dict(dog)])
        assert "w_p" not in a
    finally:
        sports.dog_spots = keep
    assert not sports.hockey_fav_bad({**fav, "w_p": 0.5})              # (outside hockey the backup Lock still works)
    src_ = open(sports.__file__).read()                                 # ...and "always a Lock" stands: the backup falls
    assert "return near_lock(cands, raw=True) if not raw else None" in src_   # back to the raw own read
    src = open(sports.__file__).read()
    assert "weigh_favorites(out)" in src


def test_game_files_merge_by_id():
    """10/2 audit: the hourly job's stale month file, rebased with -X theirs, wiped 316 backfilled college games (Idaho,
    Montana St: 'we don't hold all their games'). The games CSVs merge row by row: a game is never dropped by a stale
    copy, the further-along copy of a game wins, a real removal (moved month) stays removed."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import merge_csv as mc
    f = ["id", "start", "status", "home_score"]
    a = {"id": "a", "start": "2026-09-06", "status": "final", "home_score": "51"}
    b_pre = {"id": "b", "start": "2026-09-13", "status": "pre", "home_score": ""}
    b_fin = {**b_pre, "status": "final", "home_score": "20"}
    c = {"id": "c", "start": "2026-09-20", "status": "final", "home_score": "9"}
    base = (f, {"b": b_pre, "c": c})
    ours = (f, {"a": a, "b": b_pre, "c": c})          # upstream: the backfill added game a
    theirs = (f, {"b": b_fin})                           # the job: graded b, and moved c to another month
    _, rows = mc.merge(base, ours, theirs)
    got = {r["id"]: r for r in rows}
    assert set(got) == {"a", "b"} and got["b"]["status"] == "final"
    assert open(".gitattributes").read().count("merge=sportscsv") == 1
    for wf in ("sports.yml", "sports-live.yml", "ncaaf_backfill.yml"):
        assert "merge.sportscsv.driver" in open(os.path.join(".github", "workflows", wf)).read(), wf


def test_audit_10_2_fixes():
    """10/2 'double check for bugs on every aspect' (the owner) - each confirmed bug, pinned."""
    import sports_books as sb
    import sports_early as se
    import sports_breakdown as sbd
    import sports_breakdown_v24 as v24
    import sports_card_guard as cg
    # live: a 3rd-period / regular-time Kambi line is never the moneyline (the Devils +145)
    two = [{"englishLabel": "A"}, {"englishLabel": "B"}]
    for lab in ("Moneyline - Period 3", "Moneyline - Regular Time", "Moneyline - 1st Half", "Moneyline - Quarter 4"):
        assert not sb.two_way(lab, two), lab
    assert sb.two_way("Moneyline - Including Overtime", two) and sb.two_way("Moneyline", two)
    # live: "complete" with no winner never grades both sides lost; a tie / void game grades void
    log = {"plays": {"g:1:home": {"result": None, "an_id": 5, "side": "home"}}}
    sports_live._grade(log, {"status": "complete", "id": 5, "winning_team_id": None})
    assert log["plays"]["g:1:home"]["result"] is None
    log = {"plays": {"nfl:9:home": {"result": None, "league": "nfl"}}}
    sports_live.grade_from_games(log, {"nfl:9": {"status": "final", "home_score": "20", "away_score": "20"}})
    assert log["plays"]["nfl:9:home"]["result"] == "void"
    # a void (the owner's call) always survives the log merges
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import merge_json
    v, lo = {"result": "void"}, {"result": "lost", "odds": 145, "x": 1, "y": 2}
    assert merge_json.merge_log({"plays": {"p": lo}}, {"plays": {"p": v}})["plays"]["p"]["result"] == "void"
    assert sd.merge_live_logs({"plays": {"p": v}}, {"plays": {"p": lo}})["plays"]["p"]["result"] == "void"
    assert sd.merge_live_logs({"plays": {"p": lo}}, {"plays": {"p": v}})["plays"]["p"]["result"] == "void"
    # MLB late rally counts a road team that lost (ESPN lists no bottom 9th when the home team wins)
    x = {"home": "NYY", "away": "BOS", "home_score": "7", "away_score": "6",
         "ls_home": "3,2,2,0,0,0,0,0", "ls_away": "0,0,0,0,0,1,2,1,2"}
    assert sports.late_rally(x, "BOS")
    # a one-game day's pick follows the small-edge rule; a lean never carries units (from 10/2)
    leg = {"team": "A", "odds": 160, "dec": 2.6, "p": 0.45, "dog_p": 0.45, "edge_own": 0.01, "market": "ml"}
    keep = sports.pick_tier
    try:
        sports.pick_tier = lambda pk: "value"
        assert sports.units_for({"kind": "solo", "date": "2026-10-02", "status": "open", "legs": [leg]}) == 0.5
        assert sports.units_for({"kind": "lean", "lean": True, "lean_units": 1.0, "date": "2026-10-02",
                                 "status": "open", "legs": [leg]}) == 0
    finally:
        sports.pick_tier = keep
    # a spread lean talks about covering, never "win" / "underdog"
    for x_ in sbd.lean_ends({"team": "Bills", "odds": -110, "p": 0.45, "market": "spread", "line": -3.5}):
        assert "-3.5" in x_ and "underdog" not in x_ and "by a hair, not enough" not in x_
    # crowd lines with no reason are filler
    assert cg.problem("📊 70% of bets and 60% of the money on the Rams. We agree, for our own reasons.")
    # "washed" only for an old QB (career by 2012), never a cold prime-age star
    v24._PIDS["m"] = {"Aaron Rodgers": 8439, "Patrick Mahomes": 3139477}
    try:
        assert v24.old_qb("Aaron Rodgers") and not v24.old_qb("Patrick Mahomes") and not v24.old_qb("Nobody")
    finally:
        v24._PIDS.clear()
    # early plays: a pulled play never re-posts; the spots ping; the ping waits for the BOX itself; stuck = void at 4 days
    src = open(se.__file__).read()
    assert 'p.get("game_id") for p in st.get("pulled") or []' in src and "early spot ping failed" in src
    path = os.path.join(tempfile.mkdtemp(), "q.json")
    now = datetime(2026, 10, 2, 3, 0, tzinfo=timezone.utc)
    se.queue_pings([{"team": "Jaguars", "game_id": "g"}], now, path)
    page = '<section>EARLY VALUE PLAYS Watching...</section><section>RESULTS Jaguars 35</section>'
    assert se.send_queued(page, now, path, send_fn=lambda c: None) == []
    st = {"picks": [{"game_id": "x", "start": "2026-09-20T17:00Z", "result": None, "side": "home"}]}
    se.grade(st, {"x": {"status": "live"}})
    assert st["picks"][0]["result"] == "void"
    assert se.record({"picks": [{"result": "won", "odds": -150}]})["units"] > 0
    # a called-off game reads VOID, never PUSH
    pk = {"kind": "lock", "status": "open", "stake": 1, "legs": [{"game_id": "v", "result": "void", "dec": 1.8}]}
    sports.grade([pk], {})
    assert pk.get("void") and pk["status"] == "push"


def test_board_audit_10_2():
    """10/2 board audit: (1) a one-game PICK only on a real one-game day - never the last unpicked game of a bigger
    slate; (2) its fallback never a no-read 50/50 spread; (3) a Monday/Thursday strong lean posts as a LEAN, never a
    ½u play; (4) the daily Dog +100..+220 (the owner, 10/1); (5) unpriced small-school college games never hold the
    8 AM board."""
    src = open(sports.__file__).read()
    assert "len(slate_games) == 1 and" in src
    assert 'c["market"] == "spread" and c.get("edge_own") is None and abs(c["p"] - 0.5) < 0.005' in src
    assert 'DOG_MIN <= c["odds"] <= DAILY_DOG_MAX' in src and 'DOG_MIN <= solo["odds"] <= DAILY_DOG_MAX' in src
    assert "a small-school game the books skip" in src and sports.DAILY_DOG_MAX == 220
    c = {"market": "ml", "odds": -110, "dec": 1.909, "p": 0.545, "edge": 0.04, "edge_own": 0.04, "game_id": "n"}
    keep = (sports.good, sports.real_value, sports.leg_tier, sports.fighting)
    try:
        sports.good = lambda c: True
        sports.real_value = lambda c: True
        sports.fighting = lambda c: False
        sports.leg_tier = lambda c: "lean"
        assert sports.night_pick([c]).get("lean") is True                 # a strong lean is a LEAN
        sports.leg_tier = lambda c: "value"
        assert not sports.night_pick([c]).get("lean")                     # a real value play stays one
    finally:
        sports.good, sports.real_value, sports.leg_tier, sports.fighting = keep


def test_final_score_stamps_the_card_right_away():
    """10/2, the owner: "one says LOST across the middle, the Steelers does not" - the Steelers' game was final (the live
    scores marked MISS) but the stamp waited ~15 min for the official grade. The page stamps a one-pick card CASHED /
    LOST the second its game is final, same as a graded card."""
    import sports_dashboard as sdb
    src = open(sdb.__file__).read()
    assert "cd.querySelectorAll(\".leg\").length===1&&!cd.querySelector(\".stamp\")" in src
    assert "'<div class=\"stamp '+rs+'\">'" in src


def test_a_backup_qb_out_is_never_the_starter():
    """10/2, the Steelers card: "Both teams are down their starting quarterback - Drew Allar is out for the Steelers,
    Taylen Green for the Browns." Both were BACKUPS (Rodgers and Watson started) - false, and the engine weighed it
    ('opponent missing key players'). Only a QB / goalie who started one of the team's last 3 games is key."""
    import sports_players as sp
    keep, keep_hook = sp.CACHE, sd.STARTER_OF
    sd.STARTER_OF = sp._starter_of
    try:
        sp.CACHE = {"nfl": [{"gid": f"g{i}", "start": f"2026-09-{10 + i}", "team": "23", "player": "Aaron Rodgers",
                             "role": "QB"} for i in range(3)]}
        inj = {"23": [("Drew Allar", "QB", "Out"), ("Aaron Rodgers", "QB", "Out")], "5": [("Taylen Green", "QB", "Out")]}
        assert [r[0] for r in sd.team_key_out(inj, "23", "Steelers", "nfl")] == ["Aaron Rodgers"]
        assert sd.team_key_out(inj, "5", "Browns", "nfl") == []          # no box scores: unknown = never claimed
        assert sd.team_key_out(inj, "5", "Browns", "nfl", maybe=True) == [("Taylen Green", "QB", "Out")]   # ...but an
        #                                                     unverified QB still BLOCKS a bet (the safety checks only)
        sp.CACHE["nfl"] += [{"gid": "b1", "start": "2026-09-20", "team": "5", "player": "Deshaun Watson", "role": "QB"}]
        assert sd.team_key_out(inj, "5", "Browns", "nfl") == []                                   # a backup: never key
        assert sd.team_key_out(inj, "5", "Browns", "nfl", maybe=True) == []                       # nor a block
    finally:
        sp.CACHE, sd.STARTER_OF = keep, keep_hook


def test_study_angles_never_outweigh_the_read():
    """10/2, the owner: "I just don't want the engine to overweight these aspects." A dog's study angles together count
    at most ±STUDY_CAP points on top of the engine's own read - a stack of overlapping spots can't take over."""
    keep = sports.dog_spots
    c = {"league": "nfl", "odds": 200, "dec": 3.0, "edge": 0.0, "edge_own": 0.0, "p_market": 0.333}
    try:
        sports.dog_spots = lambda c: 15
        hi = sports.dog_score(c)
        sports.dog_spots = lambda c: -15
        lo = sports.dog_score(c)
        sports.dog_spots = lambda c: 0
        mid = sports.dog_score(c)
    finally:
        sports.dog_spots = keep
    assert abs(hi - mid - sports.STUDY_CAP) < 1e-9 and abs(mid - lo - sports.STUDY_CAP) < 1e-9 and sports.STUDY_CAP == 6


def test_daily_pick_audit_catches_false_data():
    """10/2, the owner: "we need to put a review on the engine's picks every day to make sure it made the picks with
    the right data and the right decisions." A player we said was OUT who played, a lean with units, a thin edge at
    more than ½u - each one flagged; the close vs our price logged."""
    import sports_audit as sa
    import sports_players as sp
    keep = (dict(sa._ROSTER), sp.CACHE, sports.units_for)
    try:
        sa._ROSTER.clear()
        sa._ROSTER["nfl"] = {"nfl:1": {"aaron rodgers", "deshaun watson", "drew allar"}}
        sp.CACHE = {"nfl": [{"gid": "nfl:1", "team": "5", "player": "Deshaun Watson", "role": "QB"}]}
        games = {"nfl:1": {"home": "5", "away": "23", "home_name": "Browns", "away_name": "Steelers", "ml_away": "-148"}}
        leg = {"team": "Steelers", "odds": -118, "dec": 1.847, "side": "away", "market": "ml", "league": "nfl",
               "game_id": "nfl:1", "edge_own": 0.08, "p": 0.6,
               "key_seen": {"Drew Allar (Steelers QB)": "Out", "Deshaun Watson (Browns QB)": "Out"}}
        lean = {"date": "2026-10-02", "kind": "lean", "lean": True, "status": "lost", "legs": [dict(leg)]}
        sports.units_for = lambda pk: 1.0
        r = sa.audit_day([lean], games, "2026-10-02")
        txt = " | ".join(r["flags"])
        assert "Drew Allar OUT" in txt and "Deshaun Watson OUT" in txt and "started for the Browns" in txt
        assert "a lean carried 1.0u" in txt and r["clv"] and "beat the close" in r["clv"][0]
    finally:
        sa._ROSTER.clear(); sa._ROSTER.update(keep[0]); sp.CACHE, sports.units_for = keep[1], keep[2]
    assert "sports_audit.run(picks, games" in open(sports.__file__).read()


def test_point_system_study_10_2():
    """10/2 point-system study (walk-forward, 41,497 dogs, 2019-26): only the changes that passed the false-discovery
    check or fixed a real double count / bug - NBA overreaction +5, NHL both-lost +3.5, MLB +200..+249 -4, the NHL
    road-opener angle off (wrong sign), NHL hot-key and key-edge never both, college ice-cold + losing-streak -4
    together, and a college 'bye' only within 30 days (it fired on season openers)."""
    src = open(sports.__file__).read()
    assert 'sc += 5 if c.get("league") == "nba" else 3' in src and "sc += 3.5" in src
    assert 'sc -= 4 if lg == "mlb" else 2' in src and 'if c.get("road_opener") and c.get("league") == "nhl"' not in src
    assert 'if k is not None and not c.get("hot_key")' in src
    assert 'se.REST_BYE <= (start - se._t(prev["start"])).days <= 30' in src
    base = {"league": "nhl", "odds": 150, "dog_ctx": {"won": False, "opp_won": False}}
    assert sports.dog_spots(base) - sports.dog_spots({**base, "dog_ctx": {}}) == 3.5
    m = {"league": "mlb", "odds": 210, "dog_ctx": {}}
    assert sports.dog_spots(m) - sports.dog_spots({**m, "odds": 150}) == -4
    cf = {"league": "ncaaf", "odds": 150, "dog_ctx": {}}
    both = sports.dog_spots({**cf, "dog_more": {"fades": ["ice cold", "losing streak"]}}) - sports.dog_spots(cf)
    assert both == -4


def test_late_start_plus_a_bye_is_a_full_season():
    """10/2, the owner: the completeness check held Penn State-Northwestern - Northwestern started a week late and had a
    bye (3 games, all of them) and failed the 'played about as many as the busiest teams' bar. A college team counts as
    fully seen when it has a game every week since its own opener (one bye allowed) and that opener is in our data."""
    import sports_breakdown_v24 as v24
    from datetime import datetime, timezone
    def g(d, h, a):
        return {"start": f"2026-{d}T19:00Z", "home": h, "away": a}
    fin = [g(f"08-{29 + i}", f"t{i}", f"u{i}") for i in range(2)]
    for wk, d in enumerate(("08-29", "09-05", "09-12", "09-19", "09-26")):
        for k in range(20):
            fin.append(g(d, f"busy{k}", f"opp{wk}_{k}"))
    fin += [g("09-05", "NW", "x1"), g("09-19", "NW", "x2"), g("09-26", "x3", "NW")]     # week 2 a bye
    fin += [g("09-19", "LATE", "y1"), g("09-26", "LATE", "y2")]                         # opener missing from our data
    before = datetime(2026, 10, 3, tzinfo=timezone.utc)
    assert v24.seen_all(fin, "NW", before, "ncaaf")
    assert not v24.seen_all(fin, "LATE", before, "ncaaf")


def test_small_slate_note():
    """10/2, the owner: "when there's small slates like this, we should put a disclaimer - small slate today, not many
    games on the board ... let's go to work." Under SMALL_SLATE real, priced games that day: the note, with the count."""
    import sports_dashboard as sdb
    keep = sdb._GAMES_[0]
    try:
        sdb._GAMES_[0] = {f"g{i}": {"league": "nhl", "stype": "2", "status": "pre", "ml_home": "-120",
                                     "start": "2026-10-03T01:00Z"} for i in range(5)}
        note = sdb._small_slate("2026-10-02")
        assert "Small slate today — only 5 games on the board. Let's go to work." in note
        assert "return (byo + _small_slate(day) + after_lock" in open(sdb.__file__).read()   # under the parlay line
        sdb._GAMES_[0] = {f"g{i}": {"league": "nhl", "stype": "2", "status": "pre", "ml_home": "-120",
                                     "start": "2026-10-03T01:00Z"} for i in range(20)}
        assert sdb._small_slate("2026-10-02") == ""
    finally:
        sdb._GAMES_[0] = keep


def test_audit_checks_the_cards_words():
    """10/2, the owner: "the checker needs to check all injury reports ... absolutely everything, no bugs." The audit
    checks a card's own words: a win streak vs the real games, 'road game' vs who's home, every player named as out vs
    the injury report it was posted with. It only reports - never touches a pick."""
    import sports_audit as sa
    games = {"p1": {"league": "ncaaf", "status": "final", "home": "VT", "away": "a", "home_score": "30",
                    "away_score": "10", "start": "2026-09-20T19:00Z"},
             "p2": {"league": "ncaaf", "status": "final", "home": "b", "away": "VT", "home_score": "10",
                    "away_score": "20", "start": "2026-09-27T19:00Z"},
             "g": {"league": "ncaaf", "status": "pre", "home": "VT", "away": "PIT", "home_name": "Virginia Tech",
                   "away_name": "Pitt", "neutral": "0", "start": "2026-10-03T19:00Z"}}
    leg = {"team": "Virginia Tech", "opp": "Pitt", "side": "home", "league": "ncaaf", "game_id": "g",
           "outs": [], "opp_outs": ["John Real (WR)"], "key_seen": {},
           "breakdown": ["🔥 Virginia Tech — 4 straight W's.", "🧳 Road game for Virginia Tech.",
                         "🚑 Pitt are without Fake Guy tonight."], "why_line": ""}
    txt = " | ".join(sa.card_facts(leg, games))
    assert "4 straight wins, the games say 2" in txt and "road game for Virginia Tech" in txt and "Fake Guy" in txt
    ok = {**leg, "breakdown": ["🔥 Virginia Tech — 2 straight W's.", "🚑 Pitt are without John Real tonight."]}
    assert sa.card_facts(ok, games) == []

def test_every_workflow_file_parses():
    """10/2: a step name in sports.yml had '10/2: a' unquoted - the colon broke the YAML and every sports run failed
    with 'No jobs were run'. Every workflow file has to parse, with its jobs and steps."""
    import glob
    import subprocess
    files = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows", "*.y*ml")))
    assert files
    code = ("import sys, yaml\nbad = []\nfor f in sys.argv[1:]:\n    try:\n        d = yaml.safe_load(open(f))\n"
            "        assert isinstance(d, dict) and isinstance(d.get('jobs'), dict) and d['jobs'], 'no jobs'\n"
            "        for j in d['jobs'].values():\n            assert isinstance(j.get('steps', []), list), 'bad steps'\n"
            "    except Exception as e:\n        bad.append(f + ': ' + str(e).splitlines()[0])\nprint('\\n'.join(bad))\n"
            "sys.exit(1 if bad else 0)\n")
    try:
        import yaml  # noqa: F401
        py = sys.executable
    except ImportError:                       # (the Actions python has no PyYAML; the runner's system python does)
        py = "/usr/bin/python3"
    r = subprocess.run([py, "-c", code, *files], capture_output=True, text=True)
    assert "No module named 'yaml'" not in r.stderr, "no PyYAML anywhere to check the workflow files with"
    assert r.returncode == 0, "workflow files that don't parse:\n" + r.stdout + r.stderr


def _tool(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_pacer_keeps_the_clock_when_github_skips_crons():
    """10/3: GitHub skipped every 7:44 / 7:47 / 8 AM board cron (1 of ~25 engine crons fired; 1 bug-check cron in 17 hours),
    so the restart chain (engine <-> bug check) had nothing to stand on. The pacer (tools/pacer.py, pacer.yml) is a job
    that's always running: it starts the engine when its hourly run is 65+ min late, at 7:40 PT for the 8:00 board, and
    every ~10 min in the 8 AM hour while a game day's board isn't up - right on both sides of the clock change."""
    pc = _tool("pacer")
    due = pc.engine_due
    T = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)   # noqa: E731
    assert "hourly" in due(T("2026-10-03T16:00"), T("2026-10-03T14:50"), False, False, 0)        # 70 min: skipped
    assert due(T("2026-10-03T16:00"), T("2026-10-03T15:30"), False, False, 0) == ""              # 30 min: fine
    assert due(T("2026-10-03T16:00"), T("2026-10-03T14:50"), False, False, 1) == ""              # one's running: wait
    assert "no engine run" in due(T("2026-10-03T16:00"), None, False, False, 0)
    assert "7:40" in due(T("2026-10-03T14:41"), T("2026-10-03T14:23"), False, False, 0)          # 7:41 PDT, last 7:23
    assert due(T("2026-10-03T14:41"), T("2026-10-03T14:40"), False, False, 0) == ""              # the 7:40 run is on
    assert due(T("2026-10-03T14:20"), T("2026-10-03T13:23"), False, False, 0) == ""              # 7:20: not yet
    assert "board not up" in due(T("2026-10-03T15:12"), T("2026-10-03T15:02"), False, True, 0)   # 8:12, no board
    assert due(T("2026-10-03T15:12"), T("2026-10-03T15:02"), True, True, 0) == ""                # board's up
    assert due(T("2026-10-03T15:12"), T("2026-10-03T15:02"), False, False, 0) == ""              # no games today
    assert due(T("2026-10-03T15:06"), T("2026-10-03T15:02"), False, True, 0) == ""               # a try 4 min ago
    assert "7:40" in due(T("2026-11-15T15:41"), T("2026-11-15T15:23"), False, False, 0)          # 7:41 PST (UTC-8)
    assert due(T("2026-11-15T14:41"), T("2026-11-15T14:23"), False, False, 0) == ""              # 6:41 PST: not 7:40
    assert "board not up" in due(T("2026-11-15T16:12"), T("2026-11-15T16:02"), False, True, 0)   # 8:12 PST
    assert pc.BOARD_PULL == (7, sports.BOARD_EARLY_MIN) and pc.HOURLY_MIN >= 60
    rows = [{"status": "in_progress", "databaseId": 5}, {"status": "queued", "databaseId": 6}, {"status": "completed", "databaseId": 7}]
    assert pc.busy(rows) == 2 and pc.busy(rows, skip_id="5") == 1 and pc.busy([]) == 0
    root = os.path.dirname(os.path.abspath(__file__))
    y = open(os.path.join(root, ".github", "workflows", "pacer.yml")).read()
    assert "workflow_dispatch" in y and "group: pacer" in y and "cancel-in-progress: false" in y
    assert "tools/pacer.py --backstop" in y and "tools/pacer.py --next" in y and "git fetch -q origin main" in y
    assert "workflows: [sports]" in y                      # every finished engine run can restart a broken chain
    assert "gh workflow run pacer.yml" in open(os.path.join(root, "tools", "backstop.sh")).read()
    assert 'dispatch("pacer.yml"' in open(os.path.join(root, "tools", "health.py")).read()
    assert "actions: write" in y and "contents: write" not in y   # it starts jobs, never commits


def test_bug_check_calls_the_board_late_from_805():
    """10/3 audit: the bug check only looked for the main board after 9 AM PT - an hour after the 8:00 post the owner
    wants, and the one restart that doesn't depend on the engine's own crons. From 8:05 a game day with no board is late."""
    h = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "health.py")).read()
    assert "BOARD_LATE = (8, 5)" in h and "pt.hour >= 9" not in h
    assert "(pt.hour, pt.minute) >= BOARD_LATE" in h


def test_every_sports_save_step_retries_and_never_fails_green():
    """10/2 17:14 (run 37039344253): the engine's push was rejected (another job pushed first), 'git rebase --abort'
    returned non-zero under bash -e and killed the retry loop - one try, red. Nine other sports jobs had no abort and no
    check at all: a failed save ended GREEN with nothing on main (studies, sims, refs, injury reports, fetched pages).
    Every save loop: retry after a rejected push (abort || true), and go red when nothing landed."""
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows")
    for wf in ("sports", "health", "sports_studies", "sports_sims", "sports_refs", "tennis_players", "fetch_pages",
               "injury_report", "board_preview", "injury_probe", "deploy_ask", "sports_public", "tennis_odds"):
        y = open(os.path.join(root, wf + ".yml")).read()
        assert "git rebase --abort 2>/dev/null || true" in y, wf
        assert "&& ok=1 && break" in y and '[ -n "$ok" ] ||' in y, wf


def test_tennis_slates_merge_graded_over_ungraded():
    """10/3 audit: data/sports/tennis/picks.json had no merge driver. The engine (10+ min a run) and the live watcher's
    quick grade both write it; the engine's 'pull --rebase -X theirs' kept its own older copy and dropped a grade the
    watcher had just saved. The driver merges slate by date, leg by id; a graded leg always wins."""
    mj = _tool("merge_json")
    a = {"id": "atp:1:2", "match": "atp:1", "player": "Munar", "result": None}
    b = {"id": "wta:2:1", "match": "wta:2", "player": "Swiatek", "result": None}
    ours = [{"date": "2026-10-02", "posted": "2026-10-02T15:02Z", "picks": [{**a, "id": "atp:0:1", "result": "won"}]},
            {"date": "2026-10-03", "posted": "2026-10-03T15:02Z", "picks": [a, b], "parlays": {"atp": None}}]
    theirs = [{"date": "2026-10-03", "posted": "2026-10-03T15:02Z", "picks": [{**a, "result": "lost", "final": "6-4 6-3"}, b]}]
    assert mj._is_tennis(ours) and not mj._is_tennis([{"date": "x", "kind": "lock", "legs": []}])
    out = mj.merge_tennis(ours, theirs)
    assert [s["date"] for s in out] == ["2026-10-02", "2026-10-03"]
    legs = {l["id"]: l for l in out[1]["picks"]}
    assert legs["atp:1:2"]["result"] == "lost" and legs["atp:1:2"]["final"] == "6-4 6-3" and legs["wta:2:1"]["result"] is None
    assert out[1]["parlays"] == {"atp": None}            # the side that had the extra field keeps it
    assert mj.merge_tennis(theirs, ours)[1]["picks"][0]["result"] == "lost"   # either way round
    d = tempfile.mkdtemp()
    for name, rows in (("o", ours), ("t", theirs), ("b", ours[:1])):
        json.dump(rows, open(os.path.join(d, name), "w"))
    assert mj.main(os.path.join(d, "b"), os.path.join(d, "o"), os.path.join(d, "t")) == 0
    got = json.load(open(os.path.join(d, "o")))
    assert {l["id"]: l["result"] for l in got[1]["picks"]} == {"atp:1:2": "lost", "wta:2:1": None}
    assert "data/sports/tennis/picks.json merge=sportsjson" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gitattributes")).read()


def test_official_reports_and_the_capper_use_pacific_time_both_sides_of_dst():
    """10/3 audit: sports_data.official() and the capper's game match took Pacific as a fixed UTC-7. From Nov 1 Pacific
    is UTC-8: the official injury reports' 'today' would be off by an hour at the day's edge. The real zone, not a number."""
    import inspect
    import sports_capper
    assert "timedelta(hours=7)" not in inspect.getsource(sd.official) and "timedelta(hours=7)" not in inspect.getsource(sports_capper._ours)
    assert str(sd.PT_) == "America/Los_Angeles"
    keep = sd.OFFICIAL_PATH
    try:
        sd.OFFICIAL_PATH = os.path.join(tempfile.mkdtemp(), "injuries_official.json")
        today = datetime.now(sd.PT_).date().isoformat()
        json.dump({today: {"ncaaf": {"333": {"players": [["A Guy", "QB", "out"]]}}}}, open(sd.OFFICIAL_PATH, "w"))
        assert sd.official("ncaaf") == {"333": [("A Guy", "QB", "out")]}
        assert sd.official("ncaaf", day="2020-01-01") == {}
    finally:
        sd.OFFICIAL_PATH = keep


def test_if_necessary_games_never_hold_the_finals_check():
    """10/3: Saturday's 8:01 board was held by 'FACTOR CHECK: 3 recent games have no final score yet' - the three MLB
    Wild Card 'if necessary' Game 3s (White Sox @ Astros, Red Sox @ Yankees, Cubs @ Padres): never played, never priced,
    still 'pre'. The slate check and the data-gap check already skip unpriced games; the finals check does too. Games
    that WERE priced and never got a final still hold."""
    from datetime import date
    now = datetime(2026, 10, 3, 15, 1, tzinfo=timezone.utc)
    keep = {k: dict(getattr(sports, k)) for k in ("DOG_ST", "LAST_STARTS")}
    keep_cache = sp.CACHE
    try:
        sports.DOG_ST[("mlb", "1")] = {"won": True}
        sp.CACHE = {"mlb": [{"player": "x"}]}
        inj = {"mlb": {"1": []}}
        G = {"g0": {"league": "mlb", "status": "pre", "start": "2026-10-03T20:00Z", "home_name": "Brewers", "indoor": "1",
                    "odds_time": "2026-10-03T14:30Z", "ml_home": "-120", "ml_home_open": "-120"}}
        for i, st in enumerate(("2026-10-01T21:00Z", "2026-10-02T00:00Z", "2026-10-02T00:00Z")):
            G[f"ifn{i}"] = {"league": "mlb", "status": "pre", "start": st, "stype": "3", "ml_home": "", "ml_away": ""}
        cs = [{**_cand("g0", -120, 0.55, league="mlb"), "game_id": "g0"}]
        probs = sports.factor_check(G, cs, inj, date(2026, 10, 3), now)
        assert not any("final score" in p for p in probs), probs
        for i in range(3):                                       # the same three WITH a price: played, result missing
            G[f"ifn{i}"]["ml_home"] = "-140"
        assert any("final score" in p for p in sports.factor_check(G, cs, inj, date(2026, 10, 3), now))
        assert not sports.checker_selftest()                     # (the self-test's own case still gets caught)
    finally:
        sp.CACHE = keep_cache
        for k, v in keep.items():
            getattr(sports, k).clear(); getattr(sports, k).update(v)


def test_empty_college_injury_feed_is_not_a_load_failure():
    """10/3 sweep: ESPN's college feeds carry ~3 college football teams and no college hoops at all. An EMPTY (but
    loaded) college report held the board as 'the injury report didn't load' - from November that's every college hoops
    day till 8:30. Empty is real for college (those teams are UNKNOWN and get no pick anyway); None (the pull failed)
    still holds, and so does an empty PRO feed (ESPN's pro feeds always list somebody)."""
    from datetime import date
    now = datetime(2026, 11, 10, 16, 1, tzinfo=timezone.utc)
    keep = {k: dict(getattr(sports, k)) for k in ("DOG_ST", "LAST_STARTS")}
    try:
        for lg in ("ncaab", "ncaaf", "nba"):
            sports.DOG_ST[(lg, "1")] = {"won": True}
        sports.LAST_STARTS[("nba", "1")] = ["x"]
        G = {"h": {"league": "ncaab", "status": "pre", "start": "2026-11-11T00:00Z", "home_name": "Duke", "indoor": "1",
                   "odds_time": "2026-11-10T14:30Z", "ml_home": "-150", "ml_home_open": "-150"},
             "f": {"league": "ncaaf", "status": "pre", "start": "2026-11-11T00:00Z", "home_name": "Toledo", "wx_temp": "40",
                   "odds_time": "2026-11-10T14:30Z", "ml_home": "-150", "ml_home_open": "-150"}}
        cs = [{**_cand("h", -150, 0.62, league="ncaab"), "game_id": "h"}, {**_cand("f", -150, 0.62, league="ncaaf"), "game_id": "f"}]
        probs = sports.factor_check(G, cs, {"ncaab": {}, "ncaaf": {}}, date(2026, 11, 10), now)
        assert not any("injury report" in p for p in probs), probs
        probs = sports.factor_check(G, cs, {"ncaab": None, "ncaaf": {}}, date(2026, 11, 10), now)
        assert any(p.startswith("NCAAB") and "injury report" in p for p in probs), probs
        G["n"] = {"league": "nba", "status": "pre", "start": "2026-11-11T02:00Z", "home_name": "Lakers", "indoor": "1",
                  "odds_time": "2026-11-10T14:30Z", "ml_home": "-150", "ml_home_open": "-150"}
        cs.append({**_cand("n", -150, 0.62, league="nba"), "game_id": "n"})
        probs = sports.factor_check(G, cs, {"ncaab": {}, "ncaaf": {}, "nba": {}}, date(2026, 11, 10), now)
        assert any(p.startswith("NBA") and "injury report" in p for p in probs), probs
    finally:
        for k, v in keep.items():
            getattr(sports, k).clear(); getattr(sports, k).update(v)


def test_hockey_favorite_check_only_for_pairs_the_weighing_covers():
    """10/3 sweep: the factor check wanted a weighed read (w_p) on every NHL favorite down to -300, but the weighing
    only covers favorites whose dog is +100..+220 (mark_hockey_favorites). A one-game hockey night with a -280 favorite
    would have held the board till 8:30 for a 'missing' weight that's missing by design."""
    from datetime import date
    now = datetime(2026, 10, 7, 15, 1, tzinfo=timezone.utc)
    keep = {k: dict(getattr(sports, k)) for k in ("DOG_ST", "LAST_STARTS")}
    keep_cache = sp.CACHE
    try:
        sports.DOG_ST[("nhl", "1")] = {"won": True}; sports.LAST_STARTS[("nhl", "1")] = ["x"]
        sp.CACHE = {"nhl": [{"player": "x"}]}
        G = {"g": {"league": "nhl", "status": "pre", "start": "2026-10-08T00:00Z", "home_name": "Panthers", "indoor": "1",
                   "odds_time": "2026-10-07T14:30Z", "ml_home": "-280", "ml_home_open": "-280"}}
        cs = [{**_cand("g", -280, 0.72, league="nhl"), "game_id": "g", "side": "home"},
              {**_cand("g", 230, 0.28, league="nhl"), "game_id": "g", "side": "away"}]
        probs = sports.factor_check(G, cs, {"nhl": {"1": []}}, date(2026, 10, 7), now)
        assert not any("weren't weighed" in p for p in probs), probs
        cs[1]["odds"] = 190                                      # a dog the weighing covers and no w_p: still caught
        assert any("weren't weighed" in p for p in sports.factor_check(G, cs, {"nhl": {"1": []}}, date(2026, 10, 7), now))
        cs[0]["w_p"] = 0.7
        assert not any("weren't weighed" in p for p in sports.factor_check(G, cs, {"nhl": {"1": []}}, date(2026, 10, 7), now))
    finally:
        sp.CACHE = keep_cache
        for k, v in keep.items():
            getattr(sports, k).clear(); getattr(sports, k).update(v)


def test_slate_check_knows_an_exhibition_is_skipped_on_purpose():
    """10/3 sweep: candidates() skips an all-star / Pro Bowl game (sd.exhibition); the slate check called it 'priced
    but the engine never looked at it' and would hold the board. Skipped on purpose = never a hold."""
    import tempfile as _t
    from datetime import date as _d
    now = datetime(2027, 2, 7, 15, 1, tzinfo=timezone.utc)
    games = {"x": {"id": "x", "league": "nfl", "stype": "2", "status": "pre", "start": "2027-02-07T20:00Z",
                   "away_name": "AFC", "home_name": "NFC", "ml_home": "-120", "ml_away": "100"}}
    keep = sports.SLATE_PATH
    sports.SLATE_PATH = os.path.join(_t.mkdtemp(), "slate.json")
    try:
        assert sports.skipped_why(games["x"], now, games, None).startswith("an all-star")
        assert sports.slate_check(games, [], _d(2027, 2, 7), now, errors=[], model={"params": {}}) == []
    finally:
        sports.SLATE_PATH = keep


def test_10_5_sweep_the_europe_under_takes_no_side_and_the_notes_say_it_once():
    """The 10/5 bug sweep of the 10/4 pieces. (1) The 🌍 Europe under (side "under") read as a SIDE in the board's
    'never against our early play' check - both teams of the London game would have been dropped from the board; and in
    the early post it shared the one-per-game set with the side plays, so an under blocked a spot play on the same game
    (and the other way round) - they're different bets. (2) With more open early cards than wordings, every extra card
    fell back to the FIRST wording (four cards said 'Our numbers like X more than +Y does') - the least-used one now.
    (3) The brain said early plays ping ('one ping each') after the owner turned the pings off. (4) A leans-only day
    put up three notes saying the same thing (leans only / no Lock / no Dog) - one note."""
    import sports_early as se
    import sports_dashboard as dsh
    under = {"game_id": "nfl:9", "side": "under", "market": "total", "line": 44.5, "odds": -108, "result": None}
    side = {"game_id": "nfl:8", "side": "away", "team": "Jaguars", "odds": 150, "result": None}
    assert sports.early_sides([under, side, {**side, "game_id": "nfl:7", "result": "won"}]) == {"nfl:8": "away"}
    # the early post: a side play already on the London game - the under still posts (and it never blocks a side)
    g = {"id": "nfl:9", "league": "nfl", "intl": "1", "country": "England", "city": "London", "start": "2026-10-11T13:30Z",
         "status": "pre", "total": "44.5", "under_odds": "-108", "away_name": "Eagles", "home_name": "Jaguars", "stype": "2"}
    keep = (se.ON, se.scan, se.pick_spots, se.min_one, se.spot_scan, se.with_book_lines)
    path = os.path.join(tempfile.mkdtemp(), "early.json")
    se.save({"picks": [dict(side, game_id="nfl:9", team="Jaguars", side="home", start="2026-10-11T13:30Z", league="nfl")]}, path)
    try:
        se.ON, se.scan, se.pick_spots, se.min_one, se.spot_scan = True, lambda *a, **k: [], lambda *a, **k: [], \
            lambda *a, **k: [], lambda *a, **k: []
        se.with_book_lines = lambda games, *a, **k: games
        new = se.post({"nfl:9": g}, {"params": {}}, datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc), path=path)
        assert len(new) == 1 and new[0]["side"] == "under" and new[0]["market"] == "total", new
        assert len(se.load(path)["picks"]) == 2
        assert se.post({"nfl:9": g}, {"params": {}}, datetime(2026, 10, 11, 2, 30, tzinfo=timezone.utc), path=path) == []
    finally:
        se.ON, se.scan, se.pick_spots, se.min_one, se.spot_scan, se.with_book_lines = keep
    # (2) the least-used wording
    st = {"picks": [{"why_t": 0, "result": None}, {"why_t": 1, "result": None}, {"why_t": 2, "result": None},
                    {"why_t": 0, "result": None}, {"why_t": 2, "result": "won"}]}
    assert se.pick_wording({"whys": ["a", "b", "c"]}, st)["why_t"] == 1
    assert se.pick_wording({"whys": ["a", "b", "c"]}, {"picks": []})["why_t"] == 0
    # (3) the brain: no pings for early plays
    assert se.PINGS is False and "one ping each" not in dsh.engine_weights()["early plays"]
    # (4) a leans-only day: one note
    lean = {"date": "2026-10-05", "kind": "lean", "status": "open", "lean": True, "legs": [{"game_id": "x"}]}
    cards = [("lean", "<card/>", None)]
    one = dsh._cards("2026-10-05", [lean], cards, day_all=[lean], lean_day=True)
    three = dsh._cards("2026-10-05", [lean], cards, day_all=[lean])
    assert "🔒" not in one and "🐺" not in one and "<card/>" in one
    assert "🔒" in three and "🐺" in three                               # (the notes still show when the lean note isn't up)
    # (5) the ledger's early row carries the price (the brain's green-day line said "Jaguars (None)")
    e = {"game_id": "nfl:1", "side": "away", "team": "Jaguars", "odds": 120, "spot": "best", "start": "2026-10-04T17:00Z",
         "result": "won", "graded_at": "2026-10-04T20:27Z"}
    row = sports.units_ledger([], [e])["rows"][0][0]
    assert row["legs"][0]["odds"] == 120
    assert "Jaguars (+120)" in dsh.green_day([], "2026-10-04", 0, 3, 0, early=[e])
    # (6) the game-day box on the under: the number we got -> the number now, never a struck-out price and nothing
    u = dict(under, start="2026-10-11T13:30Z", team="Under 44.5", opp="Eagles @ Jaguars", league="nfl", spot="euro_under")
    keep_on, se.ON = se.ON, True
    try:
        box = se.gameday_html({"picks": [u]}, {"nfl:9": dict(g, total="42.5")}, lambda x: x,
                              now=datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))
    finally:
        se.ON = keep_on
    assert "<s>44.5 (-108)</s>" in box and "<b>42.5</b>" in box and "beat the number" in box, box


def test_a_board_crash_never_loses_the_hours_run():
    """10/3 sweep: run() called the board builder bare - one KeyError in post_board (new code lands there every day)
    and the whole hourly run died: no grades saved, no dashboard rebuild, no tennis slate, and nothing but a red run to
    show for it. Now the crash is logged loudly, written to slate_check.json (the hourly bug check names it), the rest
    of the run saves, and the next run tries again."""
    import tempfile as _t
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sports.py")).read()
    i = src.index("    for d in days:\n        had = ")
    block = src[i:src.index("mid-day value plays", i)]
    assert "try:\n            new = post_board(" in block and "note_board_crash(d.isoformat(), e, now)" in block
    path = os.path.join(_t.mkdtemp(), "slate.json")
    json.dump({"day": "2026-10-04", "problems": []}, open(path, "w"))
    sports.note_board_crash("2026-10-04", KeyError("home_name"), datetime(2026, 10, 4, 15, tzinfo=timezone.utc), path=path)
    sc = json.load(open(path))
    assert sc["problems"] == [] and sc["crash"]["day"] == "2026-10-04" and "KeyError" in sc["crash"]["error"]
    h = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "health.py")).read()
    assert 'crash = sc.get("crash") or {}' in h and "THE BOARD BUILDER CRASHED" in h


def test_a_former_players_death_is_never_team_drama():
    """10/5, the owner OK'd: the Sharks card said "🧯 The Stars dealing with some personal stuff" off Lyle Odelein (a
    retired defenseman) dying at 58, and it counted as a reason; "Former Falcons C Jeff Van Note dies at 80" counted
    against the Falcons. A death is drama only in a current team member's family (or a teammate)."""
    import sports_news as sn, sports_card_guard as g
    odelein = "Lyle Odelein, Stanley Cup winning defenseman, dies at 58"
    assert sn.classify(odelein) == [] and sn.classify("Former Falcons C, 6-time Pro Bowler Jeff Van Note dies at 80") == []
    assert sn.classify("QB misses practice after the death of his father") == ["family/personal"]
    assert sn.classify("Star leaves team for personal reasons") == ["family/personal"]
    news = {"nhl:9": [{"id": "1", "kind": "family/personal", "date": "2026-10-04", "headline": odelein}]}
    assert sn.drama(news, "nhl", "9") == []                       # (already stored ones drop too)
    assert g.one(f'🧯 The Stars dealing with some personal stuff: "{odelein}"', "nhl") == ""
    assert g.one('🧯 The Stars dealing with some personal stuff: "Benn away after the death of his mother"', "nhl")


def test_no_basketball_sayings_or_record_filler_on_other_sports():
    """10/5, the owner OK'd: the Guardians Lock said "Gavin Williams a walking bucket right now" (a hoops saying on a
    pitcher) and "Guardians are 85-77 right now — the rest is on the field" (the record again, no fact)."""
    import sports_card_guard as g, sports_lingo
    assert g.one("⚾ Gavin Williams a walking bucket right now. It's his world.", "mlb") == ""
    assert g.one("📋 Guardians are 85-77 right now — the rest is on the field.", "mlb") == ""
    assert "walking bucket" not in open("sports_lingo.py").read()
    assert "rest is on the field" not in open("sports_breakdown_v24.py").read()


if __name__ == "__main__":
    sports_live.FINAL_AT_PATH = os.path.join(tempfile.mkdtemp(), "final_at.json")   # (tests never touch the real one)
    sports.SLATE_PATH = os.path.join(tempfile.mkdtemp(), "slate_check.json")          # (nor the real slate check)
    import sports_early
    sports_early.PATH = os.path.join(tempfile.mkdtemp(), "early.json")                   # (nor the early plays)
    sports_early.ON = False              # (live in the engine; tests switch it on themselves, never touching real books)
    sports_early.PINGS_PATH = os.path.join(tempfile.mkdtemp(), "early_pings.json")
    import sports_pings
    sports_pings.PATH = os.path.join(tempfile.mkdtemp(), "play_pings.json")                # (nor the mid-day pings)
    import sports_audit
    sports_audit.PATH = os.path.join(tempfile.mkdtemp(), "pick_audit.json")             # (nor the pick audit)
    import sports_clv
    sports_clv.PATH = os.path.join(tempfile.mkdtemp(), "clv_record.json")               # (nor the close record /
    sports_clv.JOURNAL = os.path.join(tempfile.mkdtemp(), "pick_journal.json")          #  the pick journal)
    import sports_capper; sports_capper.PATH = os.path.join(tempfile.mkdtemp(), "capper_drbob.json")  # (nor the capper record)
    sports.LOCK_MISS_PATH = os.path.join(tempfile.mkdtemp(), "lock_miss.json")              # (nor the Lock near-miss)
    import sports_players as _spl                        # (10/2: only a VERIFIED starter is key; the older tests list
    sd.STARTER_OF = lambda lg, tid, name: True           #  made-up injured starters - the starter tests use the real check)
    import sports_leads                  # (10/2: a test run rewrote the real lead_record.json - never again)
    sports_leads.PATH = os.path.join(tempfile.mkdtemp(), "lead_tracker.json")
    sports_leads.RECORD = os.path.join(tempfile.mkdtemp(), "lead_record.json")
    sports_early.PARAMS_PATH = os.path.join(tempfile.mkdtemp(), "early_params.json")
    sports_live.FINAL_AT.clear()
    sports.HOLD_DAYS = set()                             # (a real day on hold - 10/2 - never stops the test slates)
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
