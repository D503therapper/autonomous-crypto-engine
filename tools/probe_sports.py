"""What the engine thinks about a live game right now (Texans @ Colts): live win chance, the comeback study for
this spot, the sportsbook's live price, value - and who gets the ball after halftime."""
import json
import os
import sys
import urllib.request

sys.path.insert(0, ".")
import sports_comeback as sc  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_live as sl  # noqa: E402
import sports_model as sm  # noqa: E402

TEAM = "Texans"
games = sd.load_games()
model = json.load(open(os.path.join(sd.DATA, "model.json")))
st = sc.load()
lg = "nfl"
books = sl.bovada_live(lg)
print("bovada:", sl.BOOKS)
for ang in sl.fetch_live(lg):
    g = sl._match(games, lg, ang)
    if not g or TEAM not in (g["home_name"], g["away_name"]):
        continue
    box = ang.get("boxscore") or {}
    hs, as_ = sl._score(box, "home"), sl._score(box, "away")
    left = sl.time_left(lg, box.get("period"), box.get("clock"))
    ball = sl.ball_value(lg, ang, box)
    lh, la = sl._last_period(box)
    fit = st[lg]["curve"]
    mkt = sm.market_p(g)
    ph = sl.live_prob(lg, mkt, hs - as_, left, ball, lh - la, fit)
    side_home = g["home_name"] == TEAM
    p = ph if side_home else 1 - ph
    book = sl.book_line(books, g)
    print(f"{g['away_name']} {as_} @ {g['home_name']} {hs} | {sl._clock_txt(lg, box)} | {(box.get('situation') or {}).get('display_short')}")
    print(f"pregame: {TEAM} {sd.no_vig(int(g['ml_home']), int(g['ml_away'])) if side_home else 1 - mkt:.0%} to win "
          f"(ml {g['ml_home' if side_home else 'ml_away']})")
    print(f"engine now: {TEAM} {p:.1%} to win")
    if book[0] is not None:
        ml = book[0] if side_home else book[1]
        be = 1 / sd.decimal(ml)
        print(f"bovada live: {TEAM} {ml:+d} (needs {be:.0%}) -> edge {p * sd.decimal(ml) - 1:+.1%}")
    my, their = (hs, as_) if side_home else (as_, hs)
    if my < their:
        h = sc.spot(st, lg, left, their - my, (mkt >= 0.5) == side_home)
        print("comeback study:", h and f"{h[0]} games, teams down {h[3]} {sc.when(lg, h[2])} "
              f"({'favored' if (mkt >= 0.5) == side_home else 'dogs'} coming in) won {h[1]:.0%}")
    print("reasons:", [k for k, _ in sl.reasons(st, lg, (mkt if side_home else 1 - mkt), my, their, left,
                                                (book[0] if side_home else book[1]) or 150, False, "",
                                                lh if side_home else la, la if side_home else lh, False, fit)])
    eid = g["id"].split(":")[1]
    try:
        s = json.load(urllib.request.urlopen(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={eid}", timeout=20))
        drives = (s.get("drives") or {}).get("previous") or []
        first = ((drives[0].get("team") or {}).get("displayName")) if drives else None
        print("opening kickoff received by:", first, "-> the other team gets the ball after halftime")
    except Exception as e:                                   # noqa: BLE001
        print("summary ERR", e)
