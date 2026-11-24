"""11/23 - DOUBLE-CHECKED, EVERY SOURCE: how right were the cards' injury / starter / goalie / QB / price claims?

Every posted pick (data/sports/picks.json) and early play (early.json) since SINCE, each claim the card made, against
what happened (the box scores in data/sports/roster + players: who played, who started in net, who threw the passes)
and - for prices - against our own time-stamped line tape (data/sports/line_history, ESPN / DraftKings) at the post
minute and the open / close the game files hold. No request goes out; nothing is written but the JSON beside this file.

    python results/studies/accuracy_1123/measure.py [--since 2026-11-02] [--list]
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd                  # noqa: E402
import sports_card_check as cc            # noqa: E402
import sports_absences as sa              # noqa: E402
import sports_players as sp               # noqa: E402

SINCE = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "2026-11-02"
LIST = "--list" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = r"([A-Z][\w.'-]+(?: [A-Z][\w.'-]+){1,2})"
QB_LINE = re.compile(r"\d+ TDs?, \d+ picks?")


def names_of(entries):
    return [n for n in cc._card_names(entries) if n]


def q_names(leg):
    """The men the card called questionable / a game-time call: the header's ❓ half, the 🚑 line's, the waiting list."""
    out = []
    parts = [str(leg.get("our_q") or "")]
    for x in leg.get("breakdown") or []:
        s = str(x)
        if s.startswith("🚑") and "questionable:" in s:
            parts.append(s.split("questionable:", 1)[1])
        for m in re.finditer(NAME + r" (?:is )?a game-time call", s):
            out.append(m.group(1))
    for part in parts:
        for chunk in re.split(r",\s*(?![^()]*\))", part):
            chunk = re.sub(r"\+\d+ more", "", chunk).strip(" .")
            if chunk:
                out += names_of([chunk])
    out += names_of(leg.get("waiting"))
    return list(dict.fromkeys(out))


def said(leg, name):
    """Did the card ever say anything new about him after it posted (a 🔄 / ✅ line, an ⚠️ alert)?"""
    return any(name in str(x) for x in (leg.get("fresh") or []) + (leg.get("injury_alerts") or [])) \
        or name in (leg.get("stale") or [])


def pool_for(lg, g, side):
    return cc.box_played(lg, g["id"], g[side])


def side_of(lg, g, name):
    """Which team's box score has him, when the card doesn't say ('home' / 'away' / None)."""
    for s_ in ("home", "away"):
        p = pool_for(lg, g, s_)
        if p and sa.match(name, p):
            return s_
    return None


def tape(gid, when):
    """Our line tape's last row for the game at or before `when` (ISO minute), and the first after."""
    before = after = None
    for r in TAPE.get(gid, []):
        if r["t"] <= when:
            before = r
        elif after is None:
            after = r
    return before, after


def _p(american):
    try:
        a = float(american)
    except (TypeError, ValueError):
        return None
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


TAPE = {}
for fn in sorted(os.listdir(os.path.join(sd.DATA, "line_history"))):
    if fn.endswith(".jsonl"):
        with open(os.path.join(sd.DATA, "line_history", fn)) as fh:
            for ln in fh:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                TAPE.setdefault(r["g"], []).append(r)
for v in TAPE.values():
    v.sort(key=lambda r: r["t"])

games = sd.load_games()
sp.CACHE.update(sp.load())
picks = json.load(open(os.path.join(sd.DATA, "picks.json")))
early = json.load(open(os.path.join(sd.DATA, "early.json")))

C = {k: 0 for k in (
    "cards", "cards_with_claims", "out_claims", "out_right", "out_played_said", "out_played_never_said", "out_nobox",
    "out_played_not_on_report",
    "q_claims", "q_played", "q_sat", "q_resolved_on_card", "q_never_resolved", "q_nobox",
    "lineup_claims", "lineup_right", "lineup_sat",
    "goalie_claims", "goalie_right", "goalie_wrong_said", "goalie_wrong_never_said", "goalie_nobox",
    "qb_claims", "qb_right", "qb_wrong_said", "qb_wrong_never_said", "qb_nobox",
    "upd_plays", "upd_plays_right", "upd_out", "upd_out_right", "upd_goalie", "upd_goalie_right",
    "price_legs", "price_on_tape", "price_tape_same", "price_tape_off", "price_no_tape", "price_in_open_close",
    "price_outside_open_close", "price_second_source_saved")}
ROWS = []


def note(kind, pk, leg, what):
    ROWS.append({"kind": kind, "date": pk.get("date") or (pk.get("posted") or "")[:10], "league": leg.get("league"),
                 "team": leg.get("team"), "what": what})


for pk in picks:
    if (pk.get("date") or "") < SINCE:
        continue
    for leg in pk.get("legs") or []:
        g = games.get(leg.get("game_id"))
        if not g:
            continue
        lg, side = leg.get("league"), leg.get("side")
        C["cards"] += 1
        n0 = sum(C[k] for k in ("out_claims", "q_claims", "lineup_claims", "goalie_claims", "qb_claims"))
        final = g.get("status") == "final"
        other = "away" if side == "home" else "home"
        if side in ("home", "away") and final:
            # ---- listed OUT ------------------------------------------------------------------------------------
            was_on = set(leg.get("on_report") or []) | set(leg.get("rep_status") or {})
            for which, s_, lst in (("us", side, list(leg.get("outs") or []) + list(leg.get("absent") or [])),
                                   ("them", other, leg.get("opp_outs") or [])):
                pool = pool_for(lg, g, s_)
                for nm in dict.fromkeys(names_of(lst)):
                    C["out_claims"] += 1
                    if not pool:
                        C["out_nobox"] += 1
                    elif not sa.match(nm, pool):
                        C["out_right"] += 1
                    elif said(leg, nm):
                        C["out_played_said"] += 1
                        note("out, played - the card said so before the start", pk, leg, f"{nm} ({g[s_ + '_name']})")
                    else:
                        C["out_played_never_said"] += 1
                        if was_on and not any(sa.match(nm, {sa._nm(x)}) for x in was_on):
                            C["out_played_not_on_report"] += 1
                        note("out, PLAYED - the card never said so", pk, leg, f"{nm} ({g[s_ + '_name']})")
            # ---- questionable / game-time ----------------------------------------------------------------------
            for nm in q_names(leg):
                s_ = side_of(lg, g, nm)
                C["q_claims"] += 1
                if not (pool_for(lg, g, "home") or pool_for(lg, g, "away")):
                    C["q_nobox"] += 1
                    continue
                C["q_played" if s_ else "q_sat"] += 1
                if said(leg, nm):
                    C["q_resolved_on_card"] += 1
                else:
                    C["q_never_resolved"] += 1
                    note("questionable - the card never said how it ended (" + ("played" if s_ else "sat") + ")", pk, leg, nm)
            # ---- 🌟 in the lineup ------------------------------------------------------------------------------
            for x in leg.get("breakdown") or []:
                s = str(x)
                if s.startswith("🌟") and "in the lineup" in s:
                    for nm in re.findall(NAME + r" \(", s.split(" · ")[0]):
                        if nm in (leg.get("stale") or []):
                            continue
                        C["lineup_claims"] += 1
                        if side_of(lg, g, nm):
                            C["lineup_right"] += 1
                        else:
                            C["lineup_sat"] += 1
                            note("'in the lineup' - he sat", pk, leg, nm)
        # ---- the goalie / the quarterback the card gave numbers for ------------------------------------------------
        if final and lg in ("nhl", "nfl", "ncaaf"):
            rows = sp.CACHE.get(lg) or []
            box = cc.started(lg, g["id"])
            role = "G" if lg == "nhl" else "QB"
            body = [str(x) for x in leg.get("breakdown") or []
                    if (lg == "nhl" and (str(x).startswith(("🥅", "🧱")) or "save %" in str(x)))
                    or (lg != "nhl" and (QB_LINE.search(str(x)) or str(x).startswith(("🎯", "🗑️", "🧓"))))]
            text = " ".join(body)
            men = {}
            for r in rows[-8000:]:
                if str(r["team"]) in (str(g["home"]), str(g["away"])) and r.get("role", role) == role and r["player"] in text:
                    men[r["player"]] = str(r["team"])
            k = "goalie" if lg == "nhl" else "qb"
            for nm, team in men.items():
                C[k + "_claims"] += 1
                st = box.get(team)
                if not st:
                    C[k + "_nobox"] += 1
                elif sa._nm(st) == sa._nm(nm):
                    C[k + "_right"] += 1
                elif said(leg, nm):
                    C[k + "_wrong_said"] += 1
                    note(f"{k} named, another man started - the card said so before the start", pk, leg, f"{nm} -> {st}")
                else:
                    C[k + "_wrong_never_said"] += 1
                    note(f"{k} named, another man STARTED - the card never said so", pk, leg, f"{nm} -> {st}")
        # ---- the 🔄 / ✅ / ⚠️ updates themselves -------------------------------------------------------------------
        if final and side in ("home", "away"):
            for x in (leg.get("fresh") or []) + (leg.get("injury_alerts") or []):
                s = str(x)
                m = re.search(r"(?:Update: )?" + NAME + r"(?: \([^)]*\))? is off the injury report", s)
                if m:
                    C["upd_plays"] += 1
                    ok = bool(side_of(lg, g, m.group(1)))
                    C["upd_plays_right"] += ok
                    if not ok:
                        note("update said 'expected to play' - he SAT", pk, leg, m.group(1))
                m = re.search(r"Update: " + NAME + r" is (?:OUT now|out) for", s)
                if m:
                    C["upd_out"] += 1
                    ok = not side_of(lg, g, m.group(1))
                    C["upd_out_right"] += ok
                    if not ok:
                        note("update said OUT - he PLAYED", pk, leg, m.group(1))
                m = re.search(r"Update: " + NAME + r" is (?:confirmed in net|the .+? goalie now|in net for)", s)
                if m and lg == "nhl":
                    C["upd_goalie"] += 1
                    ok = any(sa._nm(v) == sa._nm(m.group(1)) for v in cc.started("nhl", g["id"]).values())
                    C["upd_goalie_right"] += ok
                    if not ok:
                        note("update named the goalie - another man started", pk, leg, m.group(1))
        C["cards_with_claims"] += sum(C[k] for k in ("out_claims", "q_claims", "lineup_claims", "goalie_claims", "qb_claims")) > n0
        # ---- the price ----------------------------------------------------------------------------------------------
        if leg.get("market") == "ml" and pk.get("posted") and leg.get("odds") is not None and side in ("home", "away"):
            C["price_legs"] += 1
            if leg.get("price_2nd"):
                C["price_second_source_saved"] += 1
            when = pk["posted"][:16] + "Z"
            b, a = tape(g["id"], when)
            k = "h" if side == "home" else "a"
            if b is None or b.get(k) in (None, ""):
                C["price_no_tape"] += 1
            else:
                C["price_on_tape"] += 1
                # (the board is built from the run's scoreboard read; the tape row is written by the same run - a row
                #  up to 70 minutes after the post still counts as "the tape at the post")
                near = [r for r in (b, a) if r and r.get(k) not in (None, "")
                        and abs((datetime.strptime(r["t"], "%Y-%m-%dT%H:%MZ") - datetime.strptime(when, "%Y-%m-%dT%H:%MZ")).total_seconds()) <= 70 * 60 or r is b]
                if any(int(float(r[k])) == int(leg["odds"]) for r in near):
                    C["price_tape_same"] += 1
                else:
                    C["price_tape_off"] += 1
                    note("price not the tape's at the post", pk, leg, f"posted {leg['odds']} at {when}, tape {b[k]} ({b['t']})"
                         + (f", next {a[k]} ({a['t']})" if a else ""))
            po, pc, pp = _p(g.get(f"ml_{side}_open")), _p(g.get(f"ml_{side}")), _p(leg["odds"])
            if po is not None and pc is not None and pp is not None:
                lo, hi = min(po, pc) - 0.03, max(po, pc) + 0.03
                if lo <= pp <= hi:
                    C["price_in_open_close"] += 1
                else:
                    C["price_outside_open_close"] += 1
                    note("price outside the open-to-close range by 3+ points", pk, leg,
                         f"posted {leg['odds']}, open {g.get(f'ml_{side}_open')}, close {g.get(f'ml_{side}')}")

# ---- the early plays -------------------------------------------------------------------------------------------------
E = {"plays": 0, "nba_out_over": 0, "out_men": 0, "out_men_sat": 0, "out_men_played": 0, "played_and_card_said_back": 0,
     "price_legs": 0, "price_tape_same": 0, "price_tape_off": 0, "price_no_tape": 0}
for p in early.get("picks") or []:
    if (p.get("posted") or "")[:10] < SINCE:
        continue
    g = games.get(p.get("game_id"))
    if not g:
        continue
    E["plays"] += 1
    if p.get("spot") == "nba_out_over" and g.get("status") == "final":
        E["nba_out_over"] += 1
        for nm in p.get("out") or []:
            E["out_men"] += 1
            if side_of("nba", g, nm):
                E["out_men_played"] += 1
                if nm in (p.get("back") or []):
                    E["played_and_card_said_back"] += 1
                else:
                    ROWS.append({"kind": "early: listed OUT, played - never said", "date": p["posted"][:10], "league": "nba",
                                 "team": p.get("team"), "what": nm})
            else:
                E["out_men_sat"] += 1
    if p.get("market", "ml") == "ml" and p.get("side") in ("home", "away") and p.get("odds") is not None:
        E["price_legs"] += 1
        when = p["posted"][:16] + "Z"
        b, a = tape(g["id"], when)
        k = "h" if p["side"] == "home" else "a"
        if b is None or b.get(k) in (None, ""):
            E["price_no_tape"] += 1
        elif any(r and r.get(k) not in (None, "") and int(float(r[k])) == int(p["odds"]) for r in (b, a)):
            E["price_tape_same"] += 1
        else:
            E["price_tape_off"] += 1      # (an early play may take BetRivers' / the better book's number - by design)

out = {"since": SINCE, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "board": C, "early": E, "rows": ROWS}
with open(os.path.join(HERE, "measure.json"), "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(json.dumps({"board": C, "early": E}, indent=1))
by = {}
for r in ROWS:
    by.setdefault(r["kind"], []).append(r)
for k, v in sorted(by.items(), key=lambda z: -len(z[1])):
    print(f"\n{len(v):3d}  {k}")
    for r in v[: (200 if LIST else 12)]:
        print(f"       {r['date']} {r['league']:5s} {r['team']}: {r['what']}")
