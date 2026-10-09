"""Combos added AFTER seeing the train ranking (counted as extra cells): the moneyline-only rule plus one more cut."""
RULES = {
    "X ml only + no MLB": lambda r: r["market"] == "ml" and r["league"] != "mlb",
    "X ml only + no college hoops": lambda r: r["market"] == "ml" and r["league"] != "ncaab",
    "X ml only + favs -150..-130 or dog": lambda r: r["market"] == "ml" and (r["odds"] >= 100 or r["odds"] <= -130),
    "X ml only + own agrees": lambda r: r["market"] == "ml" and r["own_agrees"],
    "X ml only + rank 1": lambda r: r["market"] == "ml" and r["rank"] == 1,
    "X ml only + pros": lambda r: r["market"] == "ml" and r["league"] in ("nfl", "nba", "nhl", "mlb"),
}
