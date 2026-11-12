"""11/12 DAILY - MC3: FOOTBALL'S MONEY CHECK ON THE LIVE PLAYS (the truest blind test - every football moneyline unit
play the board posted, data/sports/pick_journal.json, graded).
The live stamps carry the OWN read (old dials) but not the dog score, so each live play is joined to the SAME side on
the same day in the replay rows built on the honest dials (the deep program's funnel_new, closing prices): its honest
dog score / weighed read there says whether the RE-BASED check would have passed it. Approximate (the close, not the
post-time price; no injury report in the replay) - it says which of the live plays the re-base keeps, and how those did.
Usage: python results/studies/daily_1112/mc3_live.py > results/studies/daily_1112/mc3_live.out"""
import json, math, os
import mclib as M

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
J = json.load(open(os.path.join(ROOT, "data/sports/pick_journal.json")))
REP = {(r["date"], r["gid"], r["side"]): r for r in M.load(os.path.join(M.DEEP, "funnel_new"), "D")}


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def line(name, rs):
    rs = [r for r in rs if r.get("result") in ("won", "lost")]
    if not rs:
        print(f"  {name:56s} none")
        return
    w = sum(r["result"] == "won" for r in rs)
    n = len(rs)
    fl = sum((dec(r["odds"]) - 1) if r["result"] == "won" else -1 for r in rs)
    un = sum(r.get("pnl_units") or 0 for r in rs)
    print(f"  {name:56s} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% units {un:+6.2f}")


def rebase(r):
    """True / False = the re-based check passes / fails this live side on its replay row; None = no row."""
    x = REP.get((r["date"], r["game_id"], "home" if r.get("home") else "away"))
    if x is None:
        return None
    if r["odds"] > 0:
        if x.get("dog_score") is None:
            return None
        return (x["p_market"] + x["dog_score"] / 100) * dec(r["odds"]) > 1
    return x.get("w_p") is not None and x["w_p"] * dec(r["odds"]) > 1


fb = [r for r in J if r["league"] in ("nfl", "ncaaf") and not r.get("lean") and (r.get("units") or 0) > 0 and r.get("market") == "ml"]
print(f"live football moneyline unit plays: {len(fb)} ({min(r['date'] for r in fb)} -> {max(r['date'] for r in fb)}); "
      f"joined to a replay row: {sum(rebase(r) is not None for r in fb)}")
for lg in ("ncaaf", "nfl", None):
    rs = [r for r in fb if lg is None or r["league"] == lg]
    print(f"== {(lg or 'both').upper()}")
    line("every unit play (today's check passed them all)", rs)
    for side, sel in (("favorites", lambda r: r["odds"] < 0), ("dogs", lambda r: r["odds"] > 0)):
        x = [r for r in rs if sel(r)]
        line(side, x)
        line(f"  {side} the re-based check KEEPS", [r for r in x if rebase(r) is True])
        line(f"  {side} the re-based check DROPS", [r for r in x if rebase(r) is False])
        line(f"  {side} no replay row", [r for r in x if rebase(r) is None])
print("\nEVERY LIVE FOOTBALL MONEYLINE UNIT PLAY - the honest dog score / weighed read at the close:")
for r in sorted(fb, key=lambda r: r["date"]):
    x = REP.get((r["date"], r["game_id"], "home" if r.get("home") else "away")) or {}
    rb = rebase(r)
    what = (f"score {x.get('dog_score'):+5.2f} close {100 * x['p_market']:4.1f} -> {100 * (x['p_market'] + x['dog_score'] / 100):4.1f}"
            if r["odds"] > 0 and x.get("dog_score") is not None else
            f"w_p {100 * x['w_p']:4.1f} close {100 * x['p_market']:4.1f}" if x.get("w_p") is not None else "-")
    print(f"  {r['date']} {r['league']:5s} {r['team']:16s} {r['odds']:+5d} {r['kind']:5s} {r['units']:3.1f}u | {what:38s} needs {100 / dec(r['odds']):4.1f} "
          f"{'KEEP' if rb else 'drop' if rb is False else '  ? '}  {r['result']}")
