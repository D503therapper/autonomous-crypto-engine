"""🔁 DOUBLE-CHECKED, EVERY SOURCE (11/23 - the owner: "I just want to make sure we're always getting the accurate
information across lines, injuries, everything, and double checking sources always").

What the 11/23 accuracy audit measured on the cards of 11/2-11/23 (results/studies/accuracy_1123/README.md):
  - every posted price was the number on our own line tape at the post minute (62 of 62 board moneylines, 13 of 13 early
    ones) - but the tape IS the source (ESPN's scoreboard, DraftKings' line), and not one posted price had a second
    source's number saved beside it;
  - every injury claim on a pro card stood on ESPN's injury feed alone.

This module is the second look. It never builds, changes, sizes or holds a pick - facts and flags only:

  PRICES   second(league, ...) reads the same games off a second plain source we already use - Action Network's
           consensus line (its v2 scoreboard, the page the odds history is built from), BetRivers' pregame list when
           Action Network gives nothing -
           and confirm() says whether the price a pick posts at is one the second source shows too (inside TOL points
           of win chance, the same number on a spread / a total). stamp() writes the answer on the leg ("price_2nd")
           the moment the pick posts: confirmed, NOT confirmed (the two numbers, loud in the run log), or "no second
           source lists it". A pick is never held for it (Live Plus Money keeps its own no-confirmed-price-no-bet rule).
  CLAIMS   claims(pk, leg, ...) lists every injury / starter / price claim a live card makes with how many sources back
           it; report() is the standing health line (tools/card_audit.py -> card_audit.json "double_check" ->
           tools/health.py): a claim two sources DISAGREE on, or a posted price a second source does not show, is a
           PROBLEM line that names the card; a claim only one source makes is named on the hourly line as
           single-sourced.

Every request goes out as the engine itself (sports_http.JSON_HDR). A source that refuses or answers empty goes quiet
and says so (source_status.json "actionnetwork_pregame"); it is never worked around, and no paid odds are pulled.
"""
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import sports_data as sd
import sports_http as sh

ON = [True]                   # (tests turn it off - never a real request from a test; GET feeds a fixture instead)
GET = None                    # tests: a callable url -> payload
TOL = 0.03                    # a moneyline is "the same price" inside 3 points of win chance (-145 vs -135: 2 points)
TOL_JUICE = 0.04              # the juice on a spread / a total
TOL_LINE = 0.0                # the number itself on a spread / a total has to be the same number
TTL = 600                     # one second-source read per league at most every 10 minutes
_CACHE = {}                   # league -> (read at, {game id: row})
SRC_WORD = {"actionnetwork": "Action Network's consensus line", "betrivers": "BetRivers"}


def _get(url):
    if GET is not None:
        return GET(url)
    with urllib.request.urlopen(urllib.request.Request(url, headers=sh.JSON_HDR), timeout=12) as r:
        return json.load(r)


def _p(american):
    try:
        a = float(american)
    except (TypeError, ValueError):
        return None
    if a == 0:
        return None
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def _t(iso):
    return datetime.strptime(str(iso)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _match(games, league, rows, home_key, away_key, src, out):
    """Second-source rows -> our games (the same teams, the start inside 3 hours); the first source to list a game
    keeps it."""
    for r in rows or []:
        try:
            t = _t(r["start"])
        except (KeyError, ValueError, TypeError):
            continue
        for gid, g in games.items():
            if gid in out or g.get("league") != league or g.get("status") != "pre" or not g.get("start"):
                continue
            try:
                if abs((_t(g["start"]) - t).total_seconds()) > 3 * 3600:
                    continue
            except ValueError:
                continue
            if sd._same(g.get("home_name") or "", r.get(home_key) or "") and sd._same(g.get("away_name") or "", r.get(away_key) or ""):
                out[gid] = {**{k: r.get(k) for k in ("ml_home", "ml_away", "spread_home", "spread_home_odds",
                                                      "spread_away_odds", "total", "over_odds", "under_odds")}, "src": src}
                break
    return out


def second(league, games, now=None, days=None):
    """{game id: {"src", ml_home, ml_away, spread_home, spread_home_odds, spread_away_odds, total, over_odds,
    under_odds}} - a second plain source's CURRENT pregame line on each upcoming game of this league. {} when the reads
    are off or nobody answered (then nothing is confirmed, and the stamp says so)."""
    if not ON[0] and GET is None:
        return {}
    hit = _CACHE.get(league)
    if hit and time.time() - hit[0] < TTL and GET is None:
        return hit[1]
    now = now or datetime.now(timezone.utc)
    out = {}
    try:                                                     # 1. Action Network's consensus line (book 15)
        if league in sd.AN_WEEKS:
            urls = [sd.an_url(league, books=(sd.AN_CLOSE,))]                      # (football: the current week)
        else:
            days = days or sorted({(now - timedelta(hours=5) + timedelta(days=k)).strftime("%Y%m%d") for k in (0, 1)})
            urls = [sd.an_url(league, day=d, books=(sd.AN_CLOSE,)) for d in days]
        rows = []
        for u in urls:
            rows += sd.parse_an(_get(u))
        _match(games, league, rows, "home_full", "away_full", "actionnetwork", out)
        sh.note("actionnetwork_pregame", bool(rows), n=len(rows),
                how="plain request (v2 scoreboard, the consensus line) - the second look at a posted price"
                    + ("" if rows else " - answered with no priced game"))
    except Exception as e:                                   # noqa: BLE001 - quiet, and it says so
        sh.note("actionnetwork_pregame", False, err=sh.err_text(e),
                how="plain request (v2 scoreboard, the consensus line) - the second look at a posted price")
    try:                                                     # 2. Action Network gave nothing for this league: BetRivers'
        if GET is None and not out:                          #    pregame list (moneylines) is the second look
            import sports_books
            _match(games, league, sports_books.pregame(league), "home", "away", "betrivers", out)
    except Exception:                                        # noqa: BLE001 (sports_books keeps its own status line)
        pass
    _CACHE[league] = (time.time(), out)
    return out


def confirm(leg, row):
    """{"ok": True / False / None, "src", "odds", "line", "why"} - does the second source show the price this leg posts
    at? None = it doesn't list this game / this market (nothing to compare - never 'confirmed')."""
    if not row:
        return {"ok": None, "why": "no second source lists this game"}
    mk, side, src = leg.get("market") or "ml", leg.get("side"), row.get("src")
    mine = _p(leg.get("odds"))
    if mine is None:
        return {"ok": None, "why": "no price on the pick"}
    if mk == "ml" and side in ("home", "away"):
        theirs = row.get(f"ml_{side}")
        if _p(theirs) is None:
            return {"ok": None, "src": src, "why": "the second source has no moneyline on this game"}
        ok = abs(mine - _p(theirs)) <= TOL + 1e-9
        return {"ok": ok, "src": src, "odds": int(theirs),
                "why": "" if ok else f"posted {int(leg['odds']):+d}, {SRC_WORD.get(src, src)} has {int(theirs):+d}"}
    if mk == "spread" and side in ("home", "away"):
        ln, px = row.get("spread_home"), row.get(f"spread_{side}_odds")
        if ln is None or _p(px) is None or leg.get("line") is None:
            return {"ok": None, "src": src, "why": "the second source has no spread on this game"}
        ln = float(ln) if side == "home" else -float(ln)
        ok = abs(ln - float(leg["line"])) <= TOL_LINE + 1e-9 and abs(mine - _p(px)) <= TOL_JUICE + 1e-9
        return {"ok": ok, "src": src, "odds": int(px), "line": ln,
                "why": "" if ok else f"posted {float(leg['line']):+g} ({int(leg['odds']):+d}), "
                                     f"{SRC_WORD.get(src, src)} has {ln:+g} ({int(px):+d})"}
    if mk == "total" and side in ("over", "under"):
        ln, px = row.get("total"), row.get(f"{side}_odds")
        if ln is None or _p(px) is None or leg.get("line") is None:
            return {"ok": None, "src": src, "why": "the second source has no total on this game"}
        ok = abs(float(ln) - float(leg["line"])) <= TOL_LINE + 1e-9 and abs(mine - _p(px)) <= TOL_JUICE + 1e-9
        return {"ok": ok, "src": src, "odds": int(px), "line": float(ln),
                "why": "" if ok else f"posted {side} {float(leg['line']):g} ({int(leg['odds']):+d}), "
                                     f"{SRC_WORD.get(src, src)} has {float(ln):g} ({int(px):+d})"}
    return {"ok": None, "why": "a market the second look doesn't read"}


def stamp(leg, games, now=None, rows=None):
    """Write the second look on a leg as it posts (leg["price_2nd"]) and return it. Never raises, never holds a pick,
    never touches its price. rows: {league: second(...)} already read this run (one read per league)."""
    now = now or datetime.now(timezone.utc)
    try:
        lg = leg.get("league")
        if rows is not None and lg in rows:
            got = rows[lg]
        else:
            got = second(lg, games, now)
            if rows is not None:
                rows[lg] = got
        if not got and not ON[0] and GET is None:
            return None                                      # (the reads are off: nothing is claimed either way)
        res = confirm(leg, got.get(leg.get("game_id")))
    except Exception as e:                                   # noqa: BLE001
        res = {"ok": None, "why": f"the second look failed: {str(e)[:60]}"}
    res = {k: v for k, v in res.items() if v not in ("", None) or k == "ok"}
    res["at"] = now.strftime("%Y-%m-%dT%H:%MZ")
    leg["price_2nd"] = res
    return res


def words(leg):
    """The run log's line for a leg's second look ('' when confirmed)."""
    r = leg.get("price_2nd") or {}
    who = f"{leg.get('team')} {leg.get('odds')}"
    if r.get("ok") is True:
        return ""
    if r.get("ok") is False:
        return f"PRICE CHECK: {who} NOT confirmed by a second source - {r.get('why')}"
    return f"PRICE CHECK: {who} single-sourced - {r.get('why') or 'no second source'}"


# ---------------------------------------------------------------- the standing health line
PROBLEM_H = 6                 # an unconfirmed price is a PROBLEM line for this long after the post, then a note


def _fresh(at, now=None):
    try:
        return ((now or datetime.now(timezone.utc)) - _t(at)).total_seconds() <= PROBLEM_H * 3600
    except (ValueError, TypeError):
        return True
def claims(pk, leg, g=None, now=None):
    """Every injury / starter / price claim a live card makes, with what backs it:
    [{"what", "state": 'confirmed' / 'single' / 'disagree' / 'waiting' / 'unconfirmed', "why"}]."""
    out = []
    gday = leg.get("gameday") or {}
    src = leg.get("inj_src") or {}
    notes = {n.split(":")[0]: n for n in leg.get("src_notes") or []}

    def name(x):
        import sports_card_check as cc
        return (cc._card_names([x]) or [""])[0]
    stale = set(leg.get("stale") or [])
    for key in ("outs", "opp_outs"):
        for x in leg.get(key) or []:
            nm = name(x)
            if not nm or nm in stale:
                continue
            if gday.get(nm) == "inactive" or len(src.get(nm) or []) > 1:
                out.append({"what": f"{nm} out", "state": "confirmed", "why": ""})
            else:
                out.append({"what": f"{nm} out", "state": "single",
                            "why": "only " + (", ".join(sd.SRC_WORD.get(s, s) for s in src.get(nm) or [])
                                              or ("ESPN's injury feed" if leg.get("league") in sd.PRO else "one source"))
                                   + " says so"})
    for nm, c in (leg.get("rep_status") or {}).items():
        if c != "q" or nm in gday or nm in stale:
            continue
        out.append({"what": f"{nm} questionable", "state": "waiting",
                    "why": "no game-day word on him yet - the card says game-time, never out"})
    for nm, n in notes.items():
        out.append({"what": f"{nm}", "state": "disagree", "why": n.split(":", 1)[1].strip()})
    pr = leg.get("price_2nd")
    if pr is not None:
        if pr.get("ok") is True:
            out.append({"what": f"the price {leg.get('odds')}", "state": "confirmed", "why": ""})
        elif pr.get("ok") is False and _fresh(pr.get("at"), now):
            out.append({"what": f"the price {leg.get('odds')}", "state": "unconfirmed", "why": pr.get("why") or ""})
        elif pr.get("ok") is False:                          # (the check is the POST's - lines move after; hours later
            out.append({"what": f"the price {leg.get('odds')}", "state": "single",   # it is history, not a live problem)
                        "why": f"not confirmed at the post - {pr.get('why') or ''}"})
        else:
            out.append({"what": f"the price {leg.get('odds')}", "state": "single", "why": pr.get("why") or "no second source"})
    return out


def report(picks, games, now=None):
    """The double-check report on the live cards (open picks whose games haven't ended):
    {"cards", "claims", "confirmed", "single": [...], "disagree": [...], "unconfirmed": [...], "waiting": [...]}."""
    rep = {"cards": 0, "claims": 0, "confirmed": 0, "single": [], "disagree": [], "unconfirmed": [], "waiting": []}
    for pk in picks or []:
        if pk.get("status") != "open":
            continue
        for leg in pk.get("legs") or []:
            g = (games or {}).get(leg.get("game_id"))
            if not g or g.get("status") == "final":
                continue
            rep["cards"] += 1
            for c in claims(pk, leg, g, now):
                rep["claims"] += 1
                if c["state"] == "confirmed":
                    rep["confirmed"] += 1
                else:
                    rep[c["state"]].append(f"{leg.get('team')} card ({pk.get('date')}): {c['what']} - {c['why']}"[:200])
    return rep


def health_lines(rep):
    """(problems, ok) lines for the hourly health check from a report()."""
    probs, ok = [], []
    if not rep:
        return probs, ok
    for x in (rep.get("disagree") or [])[:6]:
        probs.append(f"double check: SOURCES DISAGREE - {x}"[:240])
    for x in (rep.get("unconfirmed") or [])[:6]:
        probs.append(f"double check: PRICE NOT CONFIRMED - {x}"[:240])
    n1, nw = len(rep.get("single") or []), len(rep.get("waiting") or [])
    line = (f"double check: {rep.get('claims', 0)} injury / starter / price claims on {rep.get('cards', 0)} live cards - "
            f"{rep.get('confirmed', 0)} confirmed by a second source, {n1} single-sourced, {nw} waiting on a game-day word")
    if n1:
        line += " · single: " + "; ".join((rep.get("single") or [])[:4])
    if nw:
        line += " · waiting: " + "; ".join((rep.get("waiting") or [])[:4])
    ok.append(line[:600])
    return probs, ok
