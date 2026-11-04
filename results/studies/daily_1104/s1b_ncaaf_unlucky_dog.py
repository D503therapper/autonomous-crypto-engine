"""s1b - FOLLOW-UP on s1's one live cell: the COLLEGE dog +100..+350 whose season INT margin runs -0.5 a game or worse
(+20.4% on 277 at the close, train 3/3, held 2/3 + 2026). Robustness: the paid history's FIRST FAIR price, the dose
(-1.0 or worse / -0.5..-1.0), the last-6-game margin instead of the season's, which half carries it (throws picks vs
makes none), home / road, FBS vs FBS, the month, the price band, the dog's record (a bad team or a good one), the
favorite across's own luck, and the mirror (the lucky dog). Train 2021-23, held out 2024 / 2025 / 2026."""
import lib
import sports_data as sd
import sports_players as sp

C = lib.Cells()


def ints(st, r):
    if r["group"] == "passing":
        v = lib.num(st.get("interceptions"))
        return ("thrown", v) if v is not None else None
    if r["group"] == "interceptions":
        v = lib.num(st.get("interceptions"))
        return ("made", v) if v is not None else None
    return None


lg = "ncaaf"
box = lib.boxes(lg, ints)
fin = lib.finals(lg)
xby = {g["id"]: g for g in lib.load_football(lg)}
games = sd.load_games(lg)
per = {}
for gid, teams in box.items():
    for t, pl in teams.items():
        per[(gid, t)] = (sum(v[1] for v in pl.values() if v[0] == "made"), sum(v[1] for v in pl.values() if v[0] == "thrown"))
tl = lib.team_log(fin)
fbs_cache = {}


def luck(team, g):
    prev = [p for p in lib.before(tl, team, g["start"]) if p["season"] == g["season"] and (p["id"], team) in per]
    if len(prev) < 5:
        return None
    made = [per[(p["id"], team)][0] for p in prev]
    thrown = [per[(p["id"], team)][1] for p in prev]
    n = len(prev)
    wins = sum(1 for p in prev if lib.won_g(p, team))
    return {"m": (sum(made) - sum(thrown)) / n, "made": sum(made) / n, "thrown": sum(thrown) / n,
            "m6": (sum(made[-6:]) - sum(thrown[-6:])) / len(made[-6:]), "wpct": wins / n, "n": n}


for g in fin:
    if g["stype"] != "2":
        continue
    s = g["season"]
    key = g["start"][:7]
    if key not in fbs_cache:
        fbs_cache[key] = sp.fbs_set(games, g["start"]) or set()
    fbs_game = g["home"] in fbs_cache[key] and g["away"] in fbs_cache[key]
    for side, team, opp, o, won, home in lib.sides(g):
        if not lib.dog_band(o):
            continue
        L, Lo = luck(team, g), luck(opp, g)
        if not L:
            continue
        p = lib.profit(won, lib.dec(o))
        ff = lib.early_price(xby, g["id"], side)
        pf = lib.profit(won, ff[1]) if ff else None
        unl = L["m"] <= -0.5
        tag = "UNLUCKY" if unl else "lucky" if L["m"] >= 0.5 else "mid"
        C.add(f"{tag} dog close", s, p)
        C.add(f"{tag} dog FIRST FAIR", s, pf)
        if unl:
            C.add(f"UNLUCKY dose {'-1.0 or worse' if L['m'] <= -1.0 else '-0.5..-1.0'}", s, p)
            C.add(f"UNLUCKY half: {'throws picks (1.5+ thrown/g)' if L['thrown'] >= 1.5 else 'few made (under 0.5/g)' if L['made'] < 0.5 else 'both middling'}", s, p)
            C.add(f"UNLUCKY {'home' if home else 'road/neutral'}", s, p)
            C.add(f"UNLUCKY {'FBS vs FBS' if fbs_game else 'not both FBS'}", s, p)
            C.add(f"UNLUCKY month {g['start'][5:7]}", s, p)
            C.add(f"UNLUCKY price {'+100..+150' if o <= 150 else '+151..+250' if o <= 250 else '+251..+350'}", s, p)
            C.add(f"UNLUCKY record {'under .400' if L['wpct'] < 0.4 else '.400-.599' if L['wpct'] < 0.6 else '.600+'}", s, p)
            if Lo:
                C.add(f"UNLUCKY vs a {'lucky' if Lo['m'] >= 0.5 else 'unlucky' if Lo['m'] <= -0.5 else 'mid'} favorite", s, p)
            C.add(f"UNLUCKY games in {'5-7' if L['n'] <= 7 else '8+'}", s, p)
        # the last-6 version
        if L["m6"] <= -0.5:
            C.add("last-6 margin -0.5 or worse dog close", s, p)
            C.add("last-6 margin -0.5 or worse dog FIRST FAIR", s, pf)
        if L["m6"] <= -1.0:
            C.add("last-6 margin -1.0 or worse dog close", s, p)
        # the favorite across (the mirror from the other seat): a lucky favorite -101..-350
    for side, team, opp, o, won, home in lib.sides(g):
        if not (-350 <= o <= -101):
            continue
        L = luck(team, g)
        if not L:
            continue
        p = lib.profit(won, lib.dec(o))
        tag = "UNLUCKY" if L["m"] <= -0.5 else "lucky" if L["m"] >= 0.5 else "mid"
        C.add(f"{tag} FAVORITE -101..-350 close", s, p)
        if L["m"] >= 0.5:
            C.add(f"lucky favorite {'-101..-150' if o >= -150 else '-151..-350'}", s, p)

C.dump("s1b", "s1b COLLEGE FOOTBALL INTERCEPTION-UNLUCKY DOG +100..+350 (season INT margin -0.5/g or worse, 5+ box games) - robustness - "
       "train 2021-23, held 2024 / 2025 / 2026", (2021, 2023), [2024, 2025, 2026])
