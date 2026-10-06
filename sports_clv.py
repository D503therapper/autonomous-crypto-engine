"""📈 BEAT THE CLOSE - the record of every pick's price vs the closing price (the owner, 10/2: "we need to have a record
of everything so we can go back and improve the engine always"). Vegas lines are sharp: if the engine keeps getting a
better number than the line closes at (Vikings -115 that closes -130), it saw something before the market did - the
fastest real test of an edge, weeks instead of seasons of wins and losses. Every straight pick (Lock / Dog / value play
/ lean / Monday-Thursday football / one-game day), by kind, by sport and the Lock by its size.

The close = the last price our line history saw BEFORE the start (data/sports/line_history - never an in-game line);
for a pick older than the line history, the game's stored price only if it was saved before the start. No close we
can trust = left out (never a guess). Moneylines, and a spread only when the closing number is the same line.
Writes data/sports/clv_record.json every run. Report only - never touches a pick."""
import glob
import json
import os

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "clv_record.json")
JOURNAL = os.path.join(sd.DATA, "pick_journal.json")   # every graded pick: what the engine saw, what it did, what happened
KINDS = ("lock", "dog", "play", "lean", "night", "solo")


def _hist(path=None):
    """{game id: [(time, home ml, away ml, home spread, [home spread odds, away spread odds]), ...]} oldest first."""
    out = {}
    for f in sorted(glob.glob(os.path.join(path or sd.LINE_HIST_DIR, "*.jsonl"))):
        try:
            with open(f) as fh:
                for ln in fh:
                    try:
                        r = json.loads(ln)
                    except ValueError:
                        continue
                    if r.get("t") and r.get("s") and r["t"] < r["s"]:
                        out.setdefault(r["g"], []).append((r["t"], r.get("h"), r.get("a"), r.get("sp"), r.get("spo")))
        except OSError:
            continue
    for v in out.values():
        v.sort(key=lambda x: x[0])
    return out


def close_for(leg, g, hist):
    """The closing price of this pick's side, or None when we can't trust one."""
    side, mk = leg.get("side"), leg.get("market")
    rows = hist.get(leg.get("game_id")) or []
    if mk == "ml":
        for t, h, a, _, _ in reversed(rows):
            v = sm._int(h if side == "home" else a)
            if v is not None:
                return v
        if g and (g.get("odds_time") or "9") <= (g.get("start") or ""):
            return sm._int(g.get(f"ml_{side}"))
        return None
    if mk == "spread":
        for t, h, a, sp, spo in reversed(rows):
            try:
                line = float(sp) if side == "home" else -float(sp)
            except (TypeError, ValueError):
                continue
            if abs(line - float(leg.get("line") or 0)) > 1e-9:
                return None                                  # the number moved: not the same bet
            o = sm._int((spo or ["", ""])[0 if side == "home" else 1])
            return o
    return None


def journal_row(pk, games, clv):
    """📓 THE PICK JOURNAL (the owner, 10/2: "a record of what the engine found and the actual results and absolutely
    everything that could help us ... every week we go back and look at the past week and improve the engine"). One
    row per graded straight pick: the engine's reads, the price it took and the close, the angles and the injuries it
    saw, the units, the final score and how it ended."""
    import sports
    leg = pk["legs"][0]
    g = games.get(leg.get("game_id")) or {}
    side = leg.get("side")
    other = "away" if side == "home" else "home"
    try:
        us, them = float(g.get(f"{side}_score")), float(g.get(f"{other}_score"))
        score, margin = f"{us:g}-{them:g}", us - them
    except (TypeError, ValueError):
        score, margin = None, None
    c = clv.get((pk["date"], pk["kind"], leg.get("team"))) or {}
    own = sports.read_of(leg)
    return {"date": pk["date"], "kind": pk["kind"], "lean": bool(pk.get("lean")), "tier": pk.get("tier"),
            "league": leg.get("league"), "game_id": leg.get("game_id"), "team": leg.get("team"), "opp": leg.get("opp"),
            "home": side == "home", "market": leg.get("market"), "line": leg.get("line"), "odds": leg.get("odds"),
            "posted": pk.get("posted"), "price_says": round(1 / leg["dec"], 3) if leg.get("dec") else None,
            "win_p": leg.get("p"), "own_read": round(own, 3) if own is not None else None,
            "weighed": leg.get("w_p"), "dog_p": leg.get("dog_p"), "edge_own": leg.get("edge_own"),
            "near_lock": bool(leg.get("near_price")), "units": sports.units_for(pk),
            "reasons": [r[1] if isinstance(r, (list, tuple)) else r for r in (leg.get("reasons") or [])][:12],
            "angles": leg.get("dog_more") or leg.get("bd_tags") or None,
            "injuries_seen": leg.get("key_seen"), "ours_out": leg.get("outs"), "theirs_out": leg.get("opp_outs"),
            "goalie_roles": ({"ours_is_1": leg.get("g_role_me"), "theirs_is_1": leg.get("g_role_opp")}   # 🥅 (10/6: the
                             if leg.get("league") == "nhl" else None),                                   # roles spot's live tally)
            "public": leg.get("public"), "close": c.get("close"), "beat_close_pts": c.get("pts"),
            "result": pk.get("status"), "score": score, "margin": margin, "pnl_units": round(
                (sports.units_for(pk) * (leg["dec"] - 1) if pk["status"] == "won" else -sports.units_for(pk)
                 if pk["status"] == "lost" else 0.0), 2) if leg.get("dec") else None}


def size_bucket(u):
    return "½u" if u <= 0.5 else "1-2u" if u < 2 else "2-4u" if u < 4 else "4u+"


def build(picks, games, hist=None):
    import sports
    hist = _hist() if hist is None else hist
    rows = []
    for pk in picks:
        if pk.get("kind") not in KINDS or pk.get("status") not in ("won", "lost", "push") or len(pk.get("legs") or []) != 1:
            continue
        leg = pk["legs"][0]
        g = games.get(leg.get("game_id")) or {}
        if not (g.get("start") and leg.get("odds")):
            continue
        c = close_for(leg, g, hist)
        if c is None:
            continue
        a, b = sd.decimal(leg["odds"]), sd.decimal(c)
        pts = round((1 / b - 1 / a) * 100, 1)                # + = we got a better number than the close (in win %)
        u = sports.units_for(pk)
        rows.append({"date": pk["date"], "kind": pk["kind"], "lean": bool(pk.get("lean")), "league": leg.get("league"),
                     "team": leg.get("team"), "market": leg.get("market"), "line": leg.get("line"),
                     "odds": leg["odds"], "close": c, "pts": pts, "units": u, "result": pk["status"]})
    by_key = {(r["date"], r["kind"], r["team"]): r for r in rows}
    journal = [journal_row(pk, games, by_key) for pk in picks
               if pk.get("kind") in KINDS and pk.get("status") in ("won", "lost", "push", "void")
               and len(pk.get("legs") or []) == 1]
    def summ(rs):
        if not rs:
            return None
        return {"n": len(rs), "beat": sum(r["pts"] > 0 for r in rs), "same": sum(r["pts"] == 0 for r in rs),
                "worse": sum(r["pts"] < 0 for r in rs), "avg_pts": round(sum(r["pts"] for r in rs) / len(rs), 2)}
    by = lambda key: {k: summ([r for r in rows if key(r) == k]) for k in sorted({key(r) for r in rows})}   # noqa: E731
    unit = [r for r in rows if r["units"] > 0 and not r["lean"]]
    return {"all": summ(rows), "unit_plays": summ(unit), "by_kind": by(lambda r: "lean" if r["lean"] else r["kind"]),
            "by_sport": by(lambda r: r["league"]),
            "lock_by_size": {k: summ([r for r in rows if r["kind"] == "lock" and not r["lean"] and size_bucket(r["units"]) == k])
             for k in ("½u", "1-2u", "2-4u", "4u+")},
            "picks": rows}, journal


def run(picks, games, path=None, journal_path=None):
    st, journal = build(picks, games)
    with open(path or PATH, "w") as f:
        json.dump(st, f, indent=1)
    with open(journal_path or JOURNAL, "w") as f:
        json.dump(journal, f, indent=1)
    a = st.get("unit_plays")
    if a:
        print(f"beat the close: unit plays {a['beat']} of {a['n']} better than the close, avg {a['avg_pts']:+.1f} pts")
    return st
