"""Offline tests for the sports engine (no network): ESPN parsing, model tuning, the board rules,
grading. Run: python sports_test.py"""
import os
import random
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

import sports
import sports_data as sd
import sports_model as sm


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
            "start": "2026-09-27T23:00Z", "reasons": [], "market": market, "line": line, "odds": odds,
            "dec": dec, "p": p, "p_market": 1 / dec, "edge": p * dec - 1}


def test_board_rules():
    c = [_cand("a", -300, 0.80), _cand("b", -140, 0.62), _cand("c", 150, 0.43), _cand("d", 180, 0.39),
         _cand("e", 220, 0.34), _cand("f", -115, 0.56), _cand("g", 365, 0.24), _cand("h", 130, 0.46),
         _cand("i", -110, 0.54, "spread", -3.5, "nfl")]
    b = sports.make_board(c)
    for kind, min_dec in (("two", 6.0), ("three", 11.0)):
        legs = b[kind]["legs"]
        assert b[kind]["dec"] >= min_dec, kind
        assert len({l["game_id"] for l in legs}) == len(legs) == (2 if kind == "two" else 3)
        assert all(l["odds"] >= sports.MAX_FAV for l in legs), "no huge favorites"
    assert b["lock"]["legs"][0]["odds"] >= -120 and b["lock"]["legs"][0]["market"] == "ml"
    dog = b["dog"]["legs"][0]
    assert dog["odds"] >= 100 and dog["game_id"] != b["lock"]["legs"][0]["game_id"]
    assert dog["game_id"] == "g", "a big dog with the best value is not discounted"


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
        sports.PICK_HOUR_PT = 0
        picks = sports.run(fetch=False)
        kinds = {p["kind"] for p in picks}
        assert {"lock", "dog"} <= kinds, kinds
        assert os.path.exists("docs/sports/index.html")
        html = open("docs/sports/index.html").read()
        assert "TRUST THE ALGORITHM!" in html and "LOCK OF THE DAY" in html
        again = sports.run(fetch=False)                  # a second run the same day keeps the board
        assert len(again) == len(picks)
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
