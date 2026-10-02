"""Git merge driver for the sports data files that more than one job writes at the same time
(data/sports/picks.json and data/sports/live_log.json).

A line-by-line merge of two versions of these files once stitched two different 8-legs into one broken pick (9 legs,
the same game twice). This merges them record by record instead:
  picks.json    - one entry per (date, kind, round, posted); a graded version beats an open one beats a waiting one
  live_log.json - one entry per live play id; a graded version beats an ungraded one, the longest best price is kept
Usage (set up in the workflows):  git config merge.sportsjson.driver "python tools/merge_json.py %O %A %B"
Writes the merged result to %A (ours) and exits 0 (no conflict)."""
import json
import sys

RANK = {"waiting": 0, "open": 1, "won": 2, "lost": 2, "push": 2, "void": 2}


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _pkey(p):
    if p.get("status") == "waiting":
        return (p.get("date"), p.get("kind"), "waiting")
    games = tuple(sorted(str(l.get("game_id")) + "|" + str(l.get("side")) for l in p.get("legs") or []))
    return (p.get("date"), p.get("kind"), p.get("round") or 1, p.get("posted") or "", games)   # (10/1: two leans
    #   posted the same minute shared one key - the merge kept the Steelers and dropped the Kraken; the game is in it)


def merge_picks(ours, theirs, base=None):
    # (10/1 audit) three-way: a pick that was in the base and one side deleted stays deleted - unless the other side
    # changed it since (graded it, say): then it's kept. Without the base, a pulled pick came back on the next merge.
    gone = set()
    if base:
        b_ = {_pkey(p): p for p in base}
        o_, t_ = {_pkey(p): p for p in ours or []}, {_pkey(p): p for p in theirs or []}
        for k, p in b_.items():
            if (k not in o_ and t_.get(k, p) == p) or (k not in t_ and o_.get(k, p) == p):
                gone.add(k)
    out = {}
    for p in (ours or []) + (theirs or []):
        k = _pkey(p)
        if k in gone:
            continue
        old = out.get(k)
        if old is None or RANK.get(p.get("status"), 0) > RANK.get(old.get("status"), 0) or \
                (RANK.get(p.get("status"), 0) == RANK.get(old.get("status"), 0)
                 and sum(bool(l.get("result")) for l in p.get("legs") or []) > sum(bool(l.get("result")) for l in old.get("legs") or [])):
            out[k] = p
    for p in out.values():                                   # a parlay never carries the same game twice (a merge once
        seen, legs = set(), []                               # stitched the Marlins into an 8-leg twice)
        for leg in p.get("legs") or []:
            if leg.get("game_id") not in seen:
                seen.add(leg.get("game_id"))
                legs.append(leg)
        if legs:
            p["legs"] = legs
    # a waiting card never sits next to a posted play of the same kind that day
    posted = {(p.get("date"), p.get("kind")) for p in out.values() if p.get("status") != "waiting"}
    rows = [p for p in out.values() if p.get("status") != "waiting" or (p.get("date"), p.get("kind")) not in posted]
    return sorted(rows, key=lambda p: (p.get("date") or "", p.get("posted") or "", p.get("kind") or ""))


def merge_log(ours, theirs):
    plays = dict((ours or {}).get("plays") or {})
    for pid, e in ((theirs or {}).get("plays") or {}).items():
        old = plays.get(pid)
        if old is None:
            plays[pid] = e
            continue
        best = dict(e if (e.get("result") == "void" and old.get("result") != "void")   # a void (the owner's call) always
                    or (e.get("result") and not old.get("result")) else old)              # wins (10/2 audit)
        b = max(old.get("best_odds") or old.get("odds") or 0, e.get("best_odds") or e.get("odds") or 0)
        if b:
            best["best_odds"] = b
        plays[pid] = best
    return {**(ours or {}), "plays": plays}


def main(base, ours_path, theirs_path):
    ours, theirs = _load(ours_path), _load(theirs_path)
    if isinstance(ours, list) or isinstance(theirs, list):
        b_ = _load(base) if base else None
        merged = merge_picks(ours if isinstance(ours, list) else [], theirs if isinstance(theirs, list) else [],
                             b_ if isinstance(b_, list) else None)
    else:
        merged = merge_log(ours, theirs)
    with open(ours_path, "w") as f:
        json.dump(merged, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
