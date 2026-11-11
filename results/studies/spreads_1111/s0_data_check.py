"""S0 - what we hold: the nflverse play-by-play boiled down, linked to our games and to the paid odds history."""
import collections, statistics
import splib as S

o = S.Out("s0")
pg = S.pbp_games()
o.p("play-by-play games", len(pg), sorted(collections.Counter(g["season"] for g in pg).items()))
lk = S.link_repo(pg)
o.p("linked to our game files", len(lk), "unlinked by season",
    sorted(collections.Counter(g["season"] for g in pg if g["gid"] not in lk).items()))
fb = {x["id"]: x for x in S.B.load_football("nfl")}
o.p("with a FAIR early spread across the books (paid history)",
    sorted(collections.Counter(g["season"] for g in pg if g["gid"] in lk and fb.get(lk[g["gid"]]["id"], {}).get("sp")).items()))
fin = {x["id"]: x for x in S.B.finals("nfl")}
d = [(g["close"], fin[lk[g["gid"]]["id"]]["sp"]) for g in pg
     if g["gid"] in lk and lk[g["gid"]]["id"] in fin and fin[lk[g["gid"]]["id"]]["sp"] is not None and g["close"] is not None]
o.p("nflverse close vs our ESPN close:", len(d), "games, mean abs gap %.2f, opposite signs %d"
    % (statistics.mean(abs(a - b) for a, b in d), sum(1 for a, b in d if a * b < 0)))
nb = collections.Counter()
for x in fb.values():
    for days, books in x["sp"][:1]:
        nb[min(len(books), 12)] += 1
o.p("books at the first fair spread look:", sorted(nb.items()))
o.save()
