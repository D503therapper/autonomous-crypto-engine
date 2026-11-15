"""11/15 FABLE FULL ENGINE AUDIT - S4: the live ledger by play type (data/sports/picks.json + early.json, graded rows
only, each at the units it was graded at) - where the live money came from and where it went. Small samples: a ledger,
not a study.  Run from the repo root:  python results/studies/audit_1115/s4_live_ledger.py"""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.getcwd())
import sports_early as se


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def main():
    R = defaultdict(lambda: [0, 0, 0.0, 0.0])

    def add(k, won, odds, u):
        r = R[k]
        r[0 if won else 1] += 1
        r[2] += u
        r[3] += u * ((dec(odds) - 1) if won else -1)
    for p in json.load(open("data/sports/picks.json")):
        if p.get("status") not in ("won", "lost") or len(p.get("legs") or []) != 1 or p.get("kind") in ("parlay", "two", "three", "four"):
            continue
        L = p["legs"][0]
        u = p.get("units") or 0
        if p.get("kind") == "lean" or not u:
            add(("lean", L.get("league")), p["status"] == "won", L["odds"], 1.0)
            add(("lean", "ALL"), p["status"] == "won", L["odds"], 1.0)
            continue
        tag = ("floor (nba)" if (p.get("floor") or {}).get("nba") else "floor") if p.get("floor") else \
            "ncaab slot" if p.get("ncaab_play") else "gap 🔍" if p.get("gap") or L.get("gap_play") else \
            "nba fav" if p.get("nba_fav") else "dog play" if p.get("dog_play") else p.get("kind")
        won = p["status"] == "won"
        add((tag, L.get("league")), won, L["odds"], u)
        add((tag, "ALL"), won, L["odds"], u)
        add(("UNIT PLAYS", L.get("league")), won, L["odds"], u)
        add(("UNIT PLAYS", "ALL"), won, L["odds"], u)
        if p.get("best"):
            add(("⭐", "ALL"), won, L["odds"], u)
        thin = L.get("edge_own") is not None and L["edge_own"] < 0.03
        add(("own read under 3c over" if thin else "own read 3c+ over", "ALL"), won, L["odds"], u)
        add(("home" if L.get("home") else "road", "dogs" if L["odds"] >= 100 else "favs"), won, L["odds"], u)
    for p in se.load().get("picks", []):
        if p.get("result") not in ("won", "lost"):
            continue
        u = se.units(p)
        add(("early: " + (p.get("spot") or "exam scan"), p.get("league")), p["result"] == "won", p["odds"], u)
        add(("early: " + (p.get("spot") or "exam scan"), "ALL"), p["result"] == "won", p["odds"], u)
        add(("EARLY PLAYS", "ALL"), p["result"] == "won", p["odds"], u)
    for k in sorted(R, key=lambda k: (k[0], k[1] != "ALL", str(k[1]))):
        w, l, risk, net = R[k]
        print(f"{k[0]:<28} {str(k[1]):<6} {w:>3}-{l:<3} {net:+7.2f}u on {risk:6.1f}u  ({net / risk * 100 if risk else 0:+.1f}%)")


if __name__ == "__main__":
    main()
