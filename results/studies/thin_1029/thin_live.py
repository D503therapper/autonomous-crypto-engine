"""10/29 (night) THIN EDGES - the LIVE record: every unit play since 9/27 split thin (own read under THIN_EDGE over the
price - sports.thin_edge on the posted leg) vs real, by kind / sport / price band / own-read gap, with CLV."""
import json
import os
import sys
from collections import defaultdict

REPO = "/home/user/autonomous-crypto-engine/.claude/worktrees/agent-ae23cc9a369e50331"
sys.path.insert(0, REPO)
os.chdir(REPO)
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_moves             # noqa: E402

picks = json.load(open("data/sports/picks.json"))
early = json.load(open("data/sports/early.json"))
games = sd.load_games()
FROM = "2026-09-27"
rows = []
for p in picks:
    if p["date"] < FROM or p.get("lean") or p["status"] not in ("won", "lost", "push") or p["kind"] in sports.PARLAY_KINDS:
        continue
    u = p.get("units")
    if u is None:
        u = sports.units_for(p)
    if not u:
        continue
    leg = p["legs"][0]
    g = games.get(leg["game_id"]) or {}
    close = sports_moves.closing(g, leg.get("market"), leg.get("side"), leg.get("line")) if g else None
    own = None if leg.get("edge_own") is None else (leg["edge_own"] + 1) / leg["dec"]
    pm = leg.get("p_market")
    rows.append({"date": p["date"], "kind": sports.posted_kind(p), "league": leg["league"], "team": leg.get("team"),
                 "odds": leg["odds"], "dec": leg["dec"], "units": u, "status": p["status"], "pnl": p.get("pnl"),
                 "edge_own": leg.get("edge_own"), "own": own, "p_market": pm, "thin": sports.thin_edge(leg),
                 "owner": bool(p.get("owner_post")), "clv": None if close is None else round(100 * (sd.implied(close) - sd.implied(leg["odds"])), 2),
                 "gap": None if own is None or pm is None else round(100 * (own - pm), 2), "src": "board"})
for e in early["picks"]:
    e.setdefault("date", (e.get("start") or "")[:10])
    if e["date"] < FROM or e.get("result") not in ("won", "lost", "push") or not e.get("units"):
        continue
    dec = sports._dec(e["odds"])
    own = e.get("own")
    g = games.get(e["game_id"]) or {}
    close = sports_moves.closing(g, "ml" if e.get("market", "ml") == "ml" else e.get("market"), e["side"], e.get("line")) if g else None
    edge_own = None if own is None else own * dec - 1
    rows.append({"date": e["date"], "kind": "early:" + e["spot"], "league": e["league"], "team": e["team"], "odds": e["odds"],
                 "dec": dec, "units": e["units"], "status": e["result"], "pnl": None, "edge_own": edge_own, "own": own,
                 "p_market": e.get("mkt"), "thin": edge_own is not None and edge_own < sports.THIN_EDGE, "owner": False,
                 "clv": None if close is None else round(100 * (sd.implied(close) - sd.implied(e["odds"])), 2),
                 "gap": None if own is None or e.get("mkt") is None else round(100 * (own - e["mkt"]), 2), "src": "early"})


def pnl(r):
    if r["status"] == "won":
        return r["units"] * (r["dec"] - 1)
    if r["status"] == "lost":
        return -r["units"]
    return 0.0


def st(rs, label):
    rs = [r for r in rs if r["status"] in ("won", "lost")]
    if not rs:
        print(f"  {label:48s} n=0")
        return
    w = sum(r["status"] == "won" for r in rs)
    net = sum(pnl(r) for r in rs)
    risk = sum(r["units"] for r in rs)
    cl = [r["clv"] for r in rs if r["clv"] is not None]
    clv = f"CLV {sum(cl) / len(cl):+.2f} (beat {sum(c > 0 for c in cl)}/{len(cl)})" if cl else "CLV n/a"
    print(f"  {label:48s} {w}-{len(rs) - w}  {net:+6.2f}u on {risk:.1f}u  ROI {100 * net / risk:+6.1f}%  {clv}")


board = [r for r in rows if r["src"] == "board"]
print(f"{len(rows)} graded unit plays since {FROM} ({len(board)} board, {len(rows) - len(board)} early)")
print("\n== ALL unit plays (board + early)")
st(rows, "all")
st([r for r in rows if r["thin"]], "THIN (own read under 3c over the price)")
st([r for r in rows if not r["thin"]], "REAL edge")
print("\n== BOARD picks only")
st(board, "all board")
st([r for r in board if r["thin"]], "thin")
st([r for r in board if not r["thin"]], "real")
st([r for r in board if r["thin"] and not r["owner"]], "thin, engine's own (no owner posts)")
for title, key in (("by KIND", "kind"), ("by SPORT", "league")):
    print(f"\n== THIN plays {title}")
    by = defaultdict(list)
    for r in rows:
        if r["thin"]:
            by[r[key]].append(r)
    for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
        st(v, k)
    print(f"-- REAL plays {title}")
    by = defaultdict(list)
    for r in rows:
        if not r["thin"]:
            by[r[key]].append(r)
    for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
        st(v, k)
print("\n== THIN plays by PRICE BAND")
for lo, hi in ((-150, -101), (100, 150), (151, 199), (200, 350)):
    st([r for r in rows if r["thin"] and lo <= r["odds"] <= hi], f"{lo}..{hi}")
    st([r for r in rows if not r["thin"] and lo <= r["odds"] <= hi], f"   real {lo}..{hi}")
print("\n== THIN plays by OWN READ vs the NO-VIG market (points)")
for lo, hi in ((-99, -2), (-2, 0), (0, 2), (2, 4), (4, 99)):
    st([r for r in rows if r["thin"] and r["gap"] is not None and lo <= r["gap"] < hi], f"own - market {lo}..{hi}")
st([r for r in rows if r["thin"] and r["gap"] is None], "no own read / market")
print("\n== THIN plays by own read vs the PRICE (cents per dollar, edge_own)")
for lo, hi in ((-99, -0.03), (-0.03, 0), (0, 0.015), (0.015, 0.03), (0.03, 9)):
    st([r for r in rows if r["thin"] and r["edge_own"] is not None and lo <= r["edge_own"] < hi], f"edge_own {lo}..{hi}")
print("\n== the FLOOR / NBA floor / dog_play plays, every one")
for r in sorted(rows, key=lambda r: r["date"]):
    if r["kind"] in ("floor", "nbafloor", "dogplay"):
        print(f"  {r['date']} {r['kind']:9s} {r['league']:5s} {r['team']:16s} {r['odds']:+5d} {r['units']}u {r['status']:4s} own {r['own'] if r['own'] is None else round(r['own'], 3)} mkt {r['p_market']} gap {r['gap']} edge_own {r['edge_own'] if r['edge_own'] is None else round(r['edge_own'], 3)} thin {r['thin']} clv {r['clv']}")
print("\n== every THIN play")
for r in sorted(rows, key=lambda r: r["date"]):
    if r["thin"]:
        print(f"  {r['date']} {r['kind']:14s} {r['league']:5s} {r['team']:16s} {r['odds']:+5d} {r['units']}u {r['status']:4s} gap {r['gap']} edge_own {r['edge_own'] if r['edge_own'] is None else round(r['edge_own'], 3)} clv {r['clv']}{' OWNER' if r['owner'] else ''}")
json.dump(rows, open("/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/thin_live.json", "w"), indent=1)
