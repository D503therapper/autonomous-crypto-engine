"""s10 - THE QUASI-HOME NEUTRAL SITE + THE TIP HOUR, COLLEGE HOOPS (never studied: a 'neutral' game played down the
road from one campus - the Thanksgiving tournament in its home city, the conference tournament a team hosts, the
'neutral' game in a pro arena 20 miles from campus). Each team's home floor = the most common venue of its home
games that season (venues.json); miles from it to the neutral venue. NEAR = within 60 miles, FAR = 300+. Cells: the
dog +100..+350 / the favorite -101..-200 / ATS by (dog near & fav far = the quasi-home dog, the quasi-home favorite,
both far = a true neutral), Nov-Dec / Jan-Feb / March apart; the tip hour in the venue's clock (the game file's tzo)
for every priced game - noon or earlier / afternoon / evening dogs. Train 2018-22, held out 2023 / 2024 / 2025 / 2026."""
import lib

C = lib.Cells()
fin = lib.finals("ncaab")
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
co = lib.coords("ncaab")
hc = lib.home_coords("ncaab", allf, co)
print("home floors known:", len(hc), "venues known:", len(co))


def dist(team, g):
    h, v = hc.get((g["season"], team)), co.get(g["id"])
    return lib.miles(h, v) if h and v else None


for g in fin:
    if g["stype"] != "2" or g["season"] < 2018:
        continue
    s = g["season"]
    mon = g["start"][5:7]
    period = "Nov-Dec" if mon in ("11", "12") else "Jan-Feb" if mon in ("01", "02") else "March"
    # the tip hour in the venue's clock
    hour = None
    if g["tzo"] is not None:
        hour = (lib._t(g["start"]).hour + g["tzo"]) % 24
        tip = "tip noon or earlier" if hour <= 12 else "tip 1-4 PM" if hour <= 16 else "tip 5 PM+"
    if g["neutral"]:
        d = {side: dist(team, g) for side, team, opp, o, won, home in lib.sides(g)}
        for side, team, opp, o, won, home in lib.sides(g):
            dm, do = d[side], d["away" if side == "home" else "home"]
            if dm is None or do is None:
                continue
            me = "near" if dm <= 60 else "far" if dm >= 300 else "mid"
            ot = "near" if do <= 60 else "far" if do >= 300 else "mid"
            p = lib.profit(won, lib.dec(o))
            a = lib.ats(g, side)
            for cut in (f"neutral {me} vs {ot}", f"neutral {me} vs any"):
                for pp in (period, "all"):
                    C.add(f"{cut} {pp} ATS", s, a)
                    if lib.dog_band(o):
                        C.add(f"{cut} {pp} dog +100..+350", s, p)
                    if -200 <= o <= -101:
                        C.add(f"{cut} {pp} fav -101..-200", s, p)
    if hour is not None:
        for side, team, opp, o, won, home in lib.sides(g):
            p = lib.profit(won, lib.dec(o))
            a = lib.ats(g, side)
            hr = "neutral" if g["neutral"] else ("home" if home else "road")
            C.add(f"{tip} {hr} ATS", s, a)
            if lib.dog_band(o):
                C.add(f"{tip} {hr} dog +100..+350", s, p)
                C.add(f"{tip} any dog +100..+350", s, p)
            if -200 <= o <= -101:
                C.add(f"{tip} {hr} fav -101..-200", s, p)

C.dump("s10", "s10 COLLEGE HOOPS QUASI-HOME NEUTRAL SITES (near = within 60 miles of its home floor, far = 300+) + the tip hour in the venue's clock - "
       "train 2018-22, held 2023 / 2024 / 2025 / 2026", (2018, 2022), [2023, 2024, 2025, 2026])
