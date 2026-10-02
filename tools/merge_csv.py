"""Git merge driver for the game files (data/sports/games/<league>/<YYYY-MM>.csv) that more than one job writes.

10/2 audit: the hourly sports job loads the month files at checkout and rewrites them whole; when the college backfill
landed in between, `git pull --rebase -X theirs` kept the job's stale copy and wiped 316 backfilled college games
(Idaho, Montana St... then "we don't hold all their games"). This merges row by row, by game id - a game is never
dropped; when both sides changed a game, the further-along copy wins (final > live > pre), then the fuller one, then
the newer side's.
Usage (set up in the workflows):  git config merge.sportscsv.driver "python tools/merge_csv.py %O %A %B"
Writes the merged result to %A (ours) and exits 0."""
import csv
import sys

RANK = {"final": 3, "void": 3, "post": 2, "live": 2, "pre": 1}


def _load(path):
    try:
        with open(path, newline="") as f:
            r = csv.DictReader(f)
            return list(r.fieldnames or []), {row["id"]: row for row in r if row.get("id")}
    except (OSError, ValueError, KeyError):
        return [], {}


def _better(a, b):
    """The copy of one game to keep: further along, then fuller, then b (the side being merged in)."""
    ka = (RANK.get(a.get("status") or "", 0), sum(1 for v in a.values() if v not in (None, "")))
    kb = (RANK.get(b.get("status") or "", 0), sum(1 for v in b.values() if v not in (None, "")))
    return a if ka > kb else b


def merge(base, ours, theirs):
    """-> (fields, rows) - every game in either side (or the base), the better copy of each."""
    fb, rb = base
    fo, ro = ours
    ft, rt = theirs
    fields = fo or ft or fb
    for f in ft + fb:
        if f not in fields:
            fields = fields + [f]
    out = {}
    for gid in set(rb) | set(ro) | set(rt):               # a game is never dropped by a stale copy
        if gid in rb and ((gid not in ro and rt.get(gid) == rb[gid]) or (gid not in rt and ro.get(gid) == rb[gid])):
            continue                                      # one side really removed it (moved month), the other didn't touch it
        have = [x for x in (ro.get(gid), rt.get(gid)) if x] or [rb[gid]]
        out[gid] = have[0] if len(have) == 1 else _better(*have)
    return fields, sorted(out.values(), key=lambda r: (r.get("start") or "", r.get("id") or ""))


if __name__ == "__main__":
    base_p, ours_p, theirs_p = sys.argv[1:4]
    fields, rows = merge(_load(base_p), _load(ours_p), _load(theirs_p))
    if not fields:
        sys.exit(1)                                       # unreadable: let git report a conflict
    with open(ours_p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    sys.exit(0)
