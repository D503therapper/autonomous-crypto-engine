"""Why is (or isn't) the Texans live bet up? Every number the live engine uses, right now."""
import json
import os
import sys

sys.path.insert(0, ".")
import sports_comeback as sc  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_live as sl  # noqa: E402
import sports_model as sm  # noqa: E402

TEAM = "Texans"
lg = "nfl"
games = sd.load_games()
model = json.load(open(os.path.join(sd.DATA, "model.json")))
st = sc.load()
books = sl.bovada_live(lg)
print("bovada:", sl.BOOKS, sd.ERRORS[-2:])
for ang in sl.fetch_live(lg):
    g = sl._match(games, lg, ang)
    if not g or TEAM not in (g["home_name"], g["away_name"]):
        continue
    box = ang.get("boxscore") or {}
    side = "home" if g["home_name"] == TEAM else "away"
    dk, bv = sl.dk_live(lg, g), sl.book_line(books, g)
    mlh, mla, checked = sl.two_books(dk, bv)
    print(f"{g['away_name']} {sl._score(box, 'away')} @ {g['home_name']} {sl._score(box, 'home')} | {sl._clock_txt(lg, box)} | "
          f"{(box.get('situation') or {}).get('display_short')} | DK {dk} Bovada {bv} -> {mlh, mla} confirmed {checked}")
    fit = st[lg]["curve"]
    mkt = sm.market_p(g)
    hs, as_ = sl._score(box, "home"), sl._score(box, "away")
    left = sl.time_left(lg, box.get("period"), box.get("clock"))
    ball = sl.ball_value(lg, ang, box)
    rec = sl.second_half_ball(lg, g)
    lh, la = sl._last_period(box)
    ph = sl.live_prob(lg, mkt, hs - as_, left, ball, lh - la, fit)
    p = ph if side == "home" else 1 - ph
    ml = mlh if side == "home" else mla
    print(f"engine: {TEAM} {p:.1%} to win; ball value {ball:+.2f}; 2nd-half ball: {rec}; time left {left:.2f}")
    if ml:
        be = 1 / sd.decimal(ml)
        print(f"price {ml:+d} needs {be:.1%} -> edge {p * sd.decimal(ml) - 1:+.1%}")
    for hold in ((), [f"{g['id']}:{side}"]):
        r = sl.evaluate(lg, g, box, mlh, mla, st, None, mkt, ball, "", 1, checked, hold, rec) if mlh else []
        print(("as a play already up" if hold else "as a new play") + ":", [(x["team"], x["odds"], x["reasons"]) for x in r] or "no")
