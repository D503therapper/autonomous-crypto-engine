"""STUDY 2c (10/30) - can the live engine see the team market-momentum read? This season's NBA / NHL finals: how many
carry a real open (different from the close), and the current AWAY / TO counts per team (sports.market_trend)."""
import lib
import sports


def main():
    games = lib.sd.load_games()
    for lg in ("nba", "nhl"):
        fin = [g for g in games.values() if g.get("league") == lg and lib.season(g.get("start") or "1900-01") == 2026
               and g.get("status") == "final" and str(g.get("stype")) == "2"]
        opened = [g for g in fin if lib.num(g.get("ml_home_open")) and lib.num(g.get("ml_home"))]
        moved = [g for g in opened if lib.num(g.get("ml_home_open")) != lib.num(g.get("ml_home"))]
        print(f"{lg}: {len(fin)} finals this season, {len(opened)} with an open + close, {len(moved)} moved")
        if hasattr(sports, "market_trend"):
            teams = {g["home"] for g in fin} | {g["away"] for g in fin}
            last = max(fin, key=lambda g: g["start"]) if fin else None
            if last:
                fake = {**last, "start": "2026-12-31T00:00Z"}
                vals = sorted((sports.market_trend(games, {**fake, "home": t}, "home"), t) for t in teams)
                vals = [v for v in vals if v[0] is not None]
                print("  most faded:", vals[:4], " most backed:", vals[-4:])


if __name__ == "__main__":
    main()
