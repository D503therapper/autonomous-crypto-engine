"""STUDY 5 - THE HOCKEY FAVORITE (the live book's best small kind: hockey value plays 11-2, the tracker tag 'hockey fav
weighed UP' 59-24). Every NHL favorite side in the funnel rows (closing prices, 2023-10 -> 2026-10 + live 10/13-10/29),
price -150..-101, cut by what the engine knows at post time: the weighed read (w_p) vs the no-vig market, the own read vs
the price, the flags the board uses. THE QUESTION: is there a hockey favorite cell that wins MORE than its price in both
halves - an NHL favorite play like the NBA's? Cells counted at the end.
Usage: python s5_nhl_fav.py > s5_nhl_fav.out"""
from collections import defaultdict

from blib import cell, sv

N = [0]
rows = [r for r in sv.rows if r["league"] == "nhl" and r["odds"] < 0]
print(f"NHL favorites in the rows: {len(rows)}")


def cut(title, rs, key, order=None):
    print(f" {title}")
    g = defaultdict(list)
    for r in rs:
        k = key(r)
        if k is not None:
            g[k].append((r["date"], r, 1))
    for k in (order or sorted(g)):
        if len(g.get(k, [])) >= 20:
            cell(f"   {k}", g[k])
            N[0] += 1


def wgap(r):
    if r.get("w_p") is None or r.get("p_market") is None:
        return None
    g = 100 * (r["w_p"] - r["p_market"])
    return "weighed 2+ UNDER the market" if g <= -2 else "weighed 0-2 under" if g < 0 else "weighed 0-2 OVER" if g < 2 else "weighed 2-4 over" if g < 4 else "weighed 4+ over"


def ogap(r):
    from blib import gap
    g = gap(r)
    return None if g is None else "own 2+ under the market" if g <= -2 else "own 0-2 under" if g < 0 else "own 0-2 over" if g < 2 else "own 2-4 over" if g < 4 else "own 4+ over"


for lo, hi, name in ((-150, -101, "-150..-101 (the board's band)"), (-250, -151, "-250..-151 (past the board's limit - context only)")):
    rs = [r for r in rows if lo <= r["odds"] <= hi]
    print(f"\n=== NHL favorites {name}: {len(rs)}")
    cell("all", [(r["date"], r, 1) for r in rs])
    cut("the weighed read vs the no-vig market", rs, wgap)
    cut("the own read vs the no-vig market", rs, ogap)
    cut("home / road", rs, lambda r: "home" if r["home"] else "road")
    cut("price", rs, lambda r: "-119..-101" if r["odds"] > -120 else "-130..-120" if r["odds"] >= -130 else "-150..-131" if r["odds"] >= -150 else "-200..-151" if r["odds"] >= -200 else "-250..-201")
    cut("the board's flags", rs, lambda r: "good + own_beats + real_value" if r["good"] and r["own_beats"] and r["real_value"] else "good, own read under" if r["good"] else "not good (no reason / under 53%)")
    cut("hockey_fav_bad / nhl_pricey", rs, lambda r: "hockey_fav_bad" if r["hockey_fav_bad"] else "nhl_pricey" if r["nhl_pricey"] else "neither")
    cut("the move since the open", rs, lambda r: None if r.get("drift") is None else "money came TO it 2+" if r["drift"] <= -0.02 else "money ran AWAY 2+" if r["drift"] >= 0.02 else "flat")
    cut("named reasons", rs, lambda r: f"{min(3, r['n_reasons'])} reasons")
    cut("weighed OVER x home", rs, lambda r: None if r.get("w_p") is None else ("weighed over" if r["w_p"] > r["p_market"] else "weighed under") + (" home" if r["home"] else " road"))
    cut("weighed OVER x the own read", rs, lambda r: None if r.get("w_p") is None or r.get("edge_own") is None else ("weighed over" if r["w_p"] > r["p_market"] else "weighed under") + (" / own over the price" if r["edge_own"] > 0 else " / own under the price"))
print(f"\n{N[0]} cells printed")
