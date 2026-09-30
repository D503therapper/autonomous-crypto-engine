"""🥊 PATTY vs THE ALGORITHM (the owner, 9/30): a friend's moneyline ticket against the engine's, one box on the dashboard.

Left: Patty's picks, just the player and the moneyline. Right: the algorithm's picks, same count, its total payout
as close to Patty's as it can get and NEVER less (fair odds - no hiding behind heavier favorites). Each leg grades
✅ / ❌ as its match ends; when every leg's in, whoever got more right wins.

- Patty's prices come from the book (the engine's tennis lines) and refresh until each of her matches starts. A leg
  the book hasn't priced yet shows TBD, and the algorithm WAITS for it (the owner: "we don't know if Fonseca's a
  -1,000") - no guessing.
- Once her whole ticket is priced, the algorithm picks from matches not started yet and re-picks each run until one
  of its own picks starts; then its ticket is locked - never changed after a ball's been hit.
- Picks: one side per match from the priced slate, chosen to get the most right (the engine's own win % per side),
  with the ticket's total payout at least Patty's and at most 5% over it - even odds. Most right wins.
"""
import json
import math
import os
from datetime import datetime, timezone

import sports_data as sd

PATH = os.path.join(sd.DATA, "challenge.json")
PREMATCH = os.path.join(sd.DATA, "tennis", "prematch.json")
WIN_P = 0.5                    # every algorithm pick is a player the engine has winning (50%+) - plus money only when
                               # the engine says that player wins anyway
EST_ML = -200                  # (a placeholder only - the algorithm never picks while any of Patty's legs is unpriced)
FAIR_OVER = 1.05               # the algorithm's payout: at least Patty's, at most 5% more - even (the owner, 9/30: "the
                               # algorithm cannot have an edge with the odds" - a smaller payout = an easier ticket)
STEP = 0.01                    # (log-odds buckets for the pick search)


def dec(ml):
    ml = int(ml)
    return 1 + (ml / 100 if ml > 0 else 100 / -ml)


def american(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def _t(s):
    return datetime.strptime(str(s)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _load(path=PATH):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save(c, path=PATH):
    with open(path + ".tmp", "w") as f:
        json.dump(c, f, indent=1)
    os.replace(path + ".tmp", path)


def _last(name):
    import sports_tennis as stn
    return stn._last(name)


def find(player, pm, now):
    """Patty's player -> (match id, side, moneyline, start) on the slate (the next match not started yet, or the one
    being played) - or None when the book has nothing for him yet."""
    import sports_tennis as stn
    want = str(player).strip()
    wl, wf = _last(want), (stn._norm(want) or [""])[0]
    best = None
    for mid, v in pm.items():
        for side, key in ((1, "p1_name"), (2, "p2_name")):
            nm = str(v.get(key) or "")
            if _last(nm) != wl or (len(stn._norm(want)) > 1 and wf not in stn._norm(nm)):
                continue                                     # same last name, and the first name when given
            ml = (v.get("ml") or [None, None])[side - 1]     # (two Cerundolos on tour)
            if ml is None:
                continue
            t = _t(v["start"])
            if (now - t).total_seconds() > 6 * 3600:
                continue                                     # (an old match)
            if best is None or t < best[3]:
                best = (mid, side, int(ml), t)
    return best


def pick(pm, target_dec, n, now, max_ml=None):
    """The algorithm's n picks: one side per match, not started yet - the most right it can expect (the engine's win %
    per side, summed; the owner, 9/30: "the mission is to beat Patty - get more right than him"), with the ticket's
    total decimal odds in [target, FAIR_OVER * target] - even odds, never an easier ticket. [(mid, side, ml, p)] or []."""
    groups = []                                              # each match: either side (one pick per match at most)
    for mid, v in pm.items():
        if not v.get("ml") or v.get("model_p1") is None or _t(v["start"]) <= now:
            continue
        p1 = float(v["model_p1"])
        g = [(mid, side, int(ml), p) for side, p, ml in ((1, p1, v["ml"][0]), (2, 1 - p1, v["ml"][1]))
             if ml is not None and p >= WIN_P and (max_ml is None or int(ml) <= max_ml)]   # only players the engine
        #                                                       says WIN, and no longer shot than Patty's longest (the
        #                                                       owner, 9/30: "+200 is most likely going to lose - Patty's
        #                                                       biggest dog is +160, he'd have the edge") -
        #                                                       and "+220 is most likely going to lose")
        if g:
            groups.append(g)
    items = groups
    if len(items) < n:
        return []
    lo = math.log(target_dec)                                # never a smaller payout than Patty's (the owner: that
    W = math.log(target_dec * FAIR_OVER)                     # hands him the edge) and never much bigger either
    B = int(W / STEP) + 2
    NEG = -1e9
    # dp[k][b] = (most expected right, picks) using k matches with log-odds bucket b
    dp = [dict() for _ in range(n + 1)]
    dp[0][0] = (0.0, ())
    for g in items:
        snap = [dict(d) for d in dp]                         # (both sides read the table from before this match)
        for it in g:
            w = int(round(math.log(dec(it[2])) / STEP))
            for k in range(n - 1, -1, -1):
                for b, (val, ps) in snap[k].items():
                    nb = b + w
                    if nb > B:
                        continue
                    cand = (val + it[3], ps + (it,))         # the most right (the owner: beat Patty - get more right)
                    if dp[k + 1].get(nb, (NEG,))[0] < cand[0]:
                        dp[k + 1][nb] = cand
    tot = lambda ps: sum(math.log(dec(x[2])) for x in ps)
    ok = [(val, ps) for b, (val, ps) in dp[n].items() if lo - 1e-9 <= tot(ps) <= W + 1e-9]
    if not ok:                                               # nothing in the band: the closest at or over Patty's
        over = [(-tot(ps), ps) for b, (val, ps) in dp[n].items() if tot(ps) >= lo - 1e-9]
        ok = over
    if not ok:
        return []
    return list(max(ok, key=lambda x: x[0])[1])


def total(legs):
    d = 1.0
    for l in legs:
        d *= dec(l["ml"])
    return d


def update(pm=None, rows=None, now=None, path=PATH):
    """Refresh prices (before the start), pick / lock the algorithm's side, grade from ESPN rows ({id: row})."""
    c = _load(path)
    if not c:
        return None
    now = now or datetime.now(timezone.utc)
    if pm is None:
        try:
            pm = json.load(open(PREMATCH))
        except (OSError, ValueError):
            pm = {}
    for l in c["patty"]:                                     # Patty's prices: the book's, till her match starts
        if l.get("start") and _t(l["start"]) <= now:
            continue
        got = find(l["player"], pm, now)
        if got:
            l.update(match=got[0], side=got[1], ml=got[2], start=got[3].strftime("%Y-%m-%dT%H:%MZ"), est=False)
    waiting = [l["player"] for l in c["patty"] if l.get("est")]
    c["waiting"] = waiting                                   # (the owner, 9/30: no guessing a price - wait for it)
    algo_started = any(_t(l["start"]) <= now for l in c.get("algo", []) if l.get("start"))
    if algo_started:
        c["locked"] = c.get("locked") or now.strftime("%Y-%m-%dT%H:%MZ")   # one of its picks is on: ticket locked
    elif not waiting:
        got = pick(pm, total(c["patty"]), len(c["patty"]), now, max_ml=max(int(l["ml"]) for l in c["patty"]))
        if got:
            c["algo"] = [{"player": pm[mid]["p1_name" if side == 1 else "p2_name"], "match": mid, "side": side,
                          "ml": ml, "p": round(p, 3), "start": pm[mid]["start"]} for mid, side, ml, p in got]
    for l in c["patty"] + c.get("algo", []):                 # grade
        if l.get("result") or not l.get("match") or not rows:
            continue
        m = rows.get(l["match"])
        if not m:
            continue
        import sports_tennis as stn
        st = stn._state(m)
        if st == "void" or (st == "retired" and int(m.get("done") or 0) < 1):
            l["result"] = "void"
        elif st in ("final", "retired") and int(m.get("winner") or 0) in (1, 2):
            l["result"] = "won" if int(m["winner"]) == int(l["side"]) else "lost"
    _save(c, path)
    return c


def start(name, players, path=PATH):
    """A new challenge: `name`'s moneyline picks (player names as typed on the ticket)."""
    c = {"name": name, "made": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
         "patty": [{"player": p, "ml": EST_ML, "est": True, "result": None} for p in players], "algo": []}
    _save(c, path)
    return update(path=path)


def score(c):
    w = lambda legs: sum(l.get("result") == "won" for l in legs)
    done = all(l.get("result") for l in c["patty"] + c["algo"]) and c["algo"]
    return w(c["patty"]), w(c.get("algo", [])), bool(done)


def html(c, E):
    """The box: Patty on the left, the algorithm on the right - player + moneyline, ✅ / ❌ as they grade."""
    if not c or not c.get("patty"):
        return ""
    name = c.get("name", "Patty")
    ps, as_, done = score(c)
    am = lambda d: f"+{american(d):,}" if american(d) > 0 else str(american(d))
    ml = lambda x: f"+{x}" if int(x) > 0 else str(x)

    def cell(l):
        if not l:
            return '<div class="pvc"></div>'
        r = l.get("result")
        mark = {"won": "✅", "lost": "❌", "void": "➖"}.get(r, "")
        import sports_tennis as stn
        last = stn._say_name(l["player"]) or str(l["player"])   # (de Minaur, Zheng Qinwen - the way they're said)
        price = "TBD" if l.get("est") else ml(l["ml"])
        st = f' data-start="{E(l["start"])}"' if l.get("start") and not r else ""   # the page shows ● LIVE once it starts
        return (f'<div class="pvc {r or ""}"{st}><span>{E(last)}</span>'
                f'<div class="pvp"><b><small>ML</small> {E(price)}</b><i>{mark}</i></div></div>')
    rows_ = "".join(f'<div class="pvr">{cell(p)}{cell(a)}</div>'
                    for p, a in zip(c["patty"] + [None] * max(0, len(c.get("algo", [])) - len(c["patty"])),
                                    c.get("algo", []) + [None] * max(0, len(c["patty"]) - len(c.get("algo", [])))))
    if done:
        top = (f"🏆 THE ALGORITHM WINS {as_}-{ps}" if as_ > ps else f"🏆 {E(name.upper())} WINS {ps}-{as_}" if ps > as_
               else f"🤝 DEAD EVEN {ps}-{as_}")
    else:
        top = f"{E(name)} {ps} · Algorithm {as_}"
    wait = c.get("waiting") or []
    ptot = "waiting" if wait else am(total(c["patty"]))
    note = (f'<div class="pvw">⏳ Waiting on {E(", ".join(str(x).split()[-1] for x in wait))}\'s price - the algorithm '
            f'picks once {E(name)}\'s whole ticket is priced, so the odds are fair.</div>') if wait else ""
    return (f'<section class="pk pvx" style="--c1:#ffd23f;--c2:#ff3b8d"><div class="pk-h"><span class="pk-i">🥊</span>'
            f'<span class="pk-l tn8">{E(name.upper())} VS THE ALGORITHM</span></div>'
            f'<div class="pvs">{top}</div>{note}'
            f'<div class="pvr pvh"><div>{E(name)} <em>{ptot}</em></div>'
            f'<div>Algorithm <em>{am(total(c["algo"])) if c.get("algo") else "—"}</em></div></div>{rows_}</section>')

