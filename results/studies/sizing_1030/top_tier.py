"""10/30 SIZING, step 4: is there a 3u+ cell? Inside the best robust cell on the board (the football / hockey Dog of the Day
at +100..+150, +22% both halves) - does any signal pick a sub-cell that wins MORE in both halves with a real sample? And the
other candidates for a max play (the NBA favorite play, the Lock's best cells). Usage: python top_tier.py > top_tier.out"""
from board import PLAYS, gap, w_edge
from cells import show

sd = [p for p in PLAYS if p[2] == "dog" and p[1]["league"] in ("nhl", "nfl", "ncaaf") and p[1]["odds"] <= 150]
print("== THE SHORT DOG (+100..+150, football + hockey) - sub-cells for a 3u tier")
show("all", sd)
for name, f in (("odds +100..+129", lambda r: r["odds"] < 130), ("odds +130..+150", lambda r: r["odds"] >= 130),
                ("own read over the no-vig market 2+ (gap)", lambda r: (gap(r) or -9) >= 2),
                ("gap under 2", lambda r: (gap(r) or -9) < 2),
                ("own read over the price 3%+ (not thin)", lambda r: (r.get("edge_own") or -1) >= 0.03),
                ("thin", lambda r: (r.get("edge_own") or -1) < 0.03),
                ("dog score 8+", lambda r: (r.get("dog_score") or 0) >= 8),
                ("dog score 6-8", lambda r: 6 <= (r.get("dog_score") or 0) < 8),
                ("dog score under 6", lambda r: (r.get("dog_score") or 0) < 6),
                ("blend p 45%+", lambda r: r["p"] >= 0.45),
                ("blend p under 45%", lambda r: r["p"] < 0.45),
                ("home", lambda r: r.get("home")), ("road", lambda r: not r.get("home")),
                ("hockey", lambda r: r["league"] == "nhl"), ("football", lambda r: r["league"] != "nhl"),
                ("hot dog flag", lambda r: r.get("hot_dog")),
                ("weighed read over 10%", lambda r: (w_edge(r) or 0) >= 0.10)):
    show(name, [p for p in sd if f(p[1])])
print("\n== OTHER MAX-PLAY CANDIDATES")
nf = [p for p in PLAYS if p[2] == "nbafav"]
show("NBA favorite play", nf)
show("NBA favorite play -150..-135", [p for p in nf if p[1]["odds"] <= -135])
lk = [p for p in PLAYS if p[2] == "lock"]
show("Lock -150..-135", [p for p in lk if p[1]["odds"] <= -135])
show("Lock -134..-120", [p for p in lk if p[1]["odds"] > -135])
show("Lock blend 60%+", [p for p in lk if p[1]["p"] >= 0.60])
show("Lock blend 56-60%", [p for p in lk if p[1]["p"] < 0.60])
show("Lock gap 4-7", [p for p in lk if 4 <= (gap(p[1]) or 0) < 7])
show("Lock gap 7+", [p for p in lk if (gap(p[1]) or 0) >= 7])
