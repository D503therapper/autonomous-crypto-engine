"""Git merge driver for the sports data files that more than one job writes at the same time
(data/sports/picks.json, data/sports/live_log.json, data/sports/tennis/picks.json and data/sports/early.json).

A line-by-line merge of two versions of these files once stitched two different 8-legs into one broken pick (9 legs,
the same game twice). This merges them record by record instead:
  picks.json    - one entry per (date, kind, round, games); a graded version beats an open one beats a waiting one
  live_log.json - one entry per live play id; a graded version beats an ungraded one, the longest best price is kept
  tennis/picks.json - one slate per date, one leg per pick id; a graded leg beats an ungraded one
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
    return (p.get("date"), p.get("kind"), p.get("round") or 1, games)   # (10/2: two runs posted the same board 8
    #   minutes apart - with the post time in the key both copies stayed: the dashboard showed every pick twice) (10/1: two leans
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
        if old is not None and RANK.get(p.get("status"), 0) == RANK.get(old.get("status"), 0) \
                and (p.get("posted") or "9") < (old.get("posted") or "9") and not p.get("legs", [{}])[0].get("result"):
            out[k] = p                                       # (the same pick twice: the first one posted stays)
            continue
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


def _is_tennis(rows):
    return isinstance(rows, list) and any(isinstance(r, dict) and "picks" in r and "legs" not in r for r in rows)


def merge_tennis(ours, theirs):
    """data/sports/tennis/picks.json: one slate per date, one leg per pick id; a graded leg beats an ungraded one.
    (10/3 audit: the engine's save rebased with -X theirs over a slate the live watcher had just graded - with no merge
    driver the engine's older copy won and the grade was lost till the next re-grade.)"""
    slates = {}
    for s_ in (ours or []) + (theirs or []):
        if not isinstance(s_, dict) or not s_.get("date"):
            continue
        cur = slates.get(s_["date"])
        if cur is None:
            slates[s_["date"]] = {**s_, "picks": [dict(l) for l in s_.get("picks") or []]}
            continue
        legs = {l.get("id"): l for l in cur["picks"]}
        for l in s_.get("picks") or []:
            old = legs.get(l.get("id"))
            if old is None or (l.get("result") is not None and old.get("result") is None):
                legs[l.get("id")] = dict(l)
        cur["picks"] = list(legs.values())
        for k, v in s_.items():                          # anything only the other side has (a parlay, a note)
            if k != "picks" and cur.get(k) is None:
                cur[k] = v
    return [slates[d] for d in sorted(slates)][-120:]


def _is_early(x):
    return isinstance(x, dict) and isinstance(x.get("picks"), list)


def _ekey(p):
    return (str(p.get("game_id")), p.get("market") or "ml", str(p.get("side")))


def merge_early(ours, theirs, base=None):
    """data/sports/early.json (10/9 sweep): the hourly engine posts early plays and the live watcher's quick pass grades
    them - two jobs writing one file. Without a driver a conflicting hunk went to whichever job rebased (-X theirs):
    a just-posted early play vanished off the board, or a grade was lost. One pick per (game, market, side): a graded
    copy beats an ungraded one, a play one side pulled (unchanged on the other) stays pulled, the pulled list and the
    first-seen prices are the union."""
    ours, theirs, base = ours or {}, theirs or {}, base or {}
    o_, t_ = {_ekey(p): p for p in ours.get("picks") or []}, {_ekey(p): p for p in theirs.get("picks") or []}
    gone = set()
    for k, p in {_ekey(p): p for p in base.get("picks") or []}.items():
        if (k not in o_ and t_.get(k, p) == p) or (k not in t_ and o_.get(k, p) == p):
            gone.add(k)
    out = {}
    for k in list(o_) + [k for k in t_ if k not in o_]:
        if k in gone:
            continue
        a, b = o_.get(k), t_.get(k)
        if a is None or b is None:
            out[k] = dict(a or b)
            continue
        win, other = (b, a) if b.get("result") and not a.get("result") else (a, b)
        merged = dict(other)
        merged.update(win)                                   # (the graded copy wins; anything only the other had stays)
        out[k] = merged
    rows = sorted(out.values(), key=lambda p: (p.get("posted") or "", str(p.get("game_id"))))
    pulled = {str(x.get("game_id")): x for x in list(theirs.get("pulled") or []) + list(ours.get("pulled") or [])
              if isinstance(x, dict)}
    first = dict(theirs.get("first_seen") or {})
    first.update(ours.get("first_seen") or {})
    merged = {**theirs, **ours, "picks": rows}
    if pulled or "pulled" in ours or "pulled" in theirs:
        merged["pulled"] = list(pulled.values())
    if first or "first_seen" in ours or "first_seen" in theirs:
        merged["first_seen"] = first
    if ours.get("launched") or theirs.get("launched"):
        merged["launched"] = ours.get("launched") or theirs.get("launched")
    return merged


def main(base, ours_path, theirs_path):
    ours, theirs = _load(ours_path), _load(theirs_path)
    if _is_early(ours) or _is_early(theirs):
        b_ = _load(base) if base else None
        merged = merge_early(ours if _is_early(ours) else {}, theirs if _is_early(theirs) else {},
                             b_ if _is_early(b_) else None)
    elif _is_tennis(ours) or _is_tennis(theirs):
        merged = merge_tennis(ours if isinstance(ours, list) else [], theirs if isinstance(theirs, list) else [])
    elif isinstance(ours, list) or isinstance(theirs, list):
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
