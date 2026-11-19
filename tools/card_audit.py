"""🧾 THE CARD AUDIT (11/17 - the owner: "My buddy keeps complaining about the breakdowns and says they make no sense and
false, outdated information of injuries and stuff. Fable needs to run a sweep and make sure that these breakdowns are
always accurate and up to date").

The standing self-audit. It reads every card the page is showing - the line under the pick, every FULL BREAKDOWN line,
the 🚑 line, the early plays' lines - exactly as the page shows them (the 🔄 news overlay, the card guard and the card
check already applied), then re-derives every fact it can from the files and says what is still wrong:

  FALSE     a number the game files don't back (a record, a streak, a score, points a game, who played last night,
            the road-trip count, the last meeting), a "full squad" for a team we hold no injury data on
  STALE     a man the card lists out who is off the report now (or who PLAYED, once the box score is in), a man the
            card has playing who is out now, a quarterback / goalie line for a man who isn't the starter, an early
            play's record that moved since it posted
            ... and on a graded card: a 📝 review whose score isn't the game's
  NONSENSE  a line that says nothing or fights its own card ("+0 a game", a word from another sport, "full squad"
            beside the same team's men out, a man listed out for the wrong team, the lean's words on a unit play)

It never changes a pick or a card - it only reports. The engine runs it every run after the page is built
(sports.card_audit_run -> data/sports/card_audit.json); tools/health.py reads that file, so a bad line on a live card is
a PROBLEM line on the hourly bug check.

    python tools/card_audit.py                       the live cards (games not started), as the page shows them
    python tools/card_audit.py --since 2026-11-01    every card posted since, as the page would show it today
    python tools/card_audit.py --since 2026-11-01 --raw     ... as it was written (before the guard / the check)
    python tools/card_audit.py --since ... --with-leans     ... and the leans that came off the board (leans_removed.json)
    python tools/card_audit.py --out FILE            write the report there (default data/sports/card_audit.json for
                                                     the live run; history runs only print unless --out is given)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd                  # noqa: E402
import sports_card_check as cc            # noqa: E402

OUT = os.path.join(sd.DATA, "card_audit.json")
OUT_WORDS = re.compile(r"\bout\b|\bwithout\b|\bmissing\b|\bdown\b|won'?t suit up|not dressing|\bno\b|gotta play", re.I)
Q_SPLIT = re.compile(r"questionable:", re.I)
WORDING_NONSENSE = ("a lean's words on a unit play", "a unit play's words on a lean", "coin-flip", "the bottom line",
                    "hype on a thin", "LOCK", "sure-thing")


def _plain(x):
    return " ".join(re.sub(r"[^a-z ]", "", str(x or "").lower().replace(" jr", "").replace(" iii", "")
                           .replace(" ii", "")).split())


def shown(pk, leg, games):
    """(the line under the pick, the breakdown lines) as the page shows them right now."""
    import sports_dashboard as dash
    import sports_card_guard
    dash._GAMES_[0] = games
    quiet = cc.note
    cc.note = lambda *a, **k: None                           # (the audit reads the page - it doesn't log the check's catches)
    try:
        lines = [dash.pct_ok(x) for x in sports_card_guard.clean(
            [x for x in dash.fresh_lines(leg, leg.get("breakdown") or []) if isinstance(x, str) and dash.latest_ok(x)],
            leg.get("league"), leg.get("team", ""), leg.get("opp", ""))]
        wl = leg.get("why_line") or ""
        wl = cc.check_one(pk, leg, sports_card_guard.one("" if dash.stale_in(wl, leg) else wl, leg.get("league"),
                                                         leg.get("team", ""), leg.get("opp", "")), games)
        if wl and cc.knocks_us(wl, leg):                     # (11/18: exactly the page's order - sports_dashboard._leg:
            wl = ""                                          #  the one-liner first (never a knock on us; the card's
        try:                                                 #  first real fact when it falls), then the body checked
            wl = dash.pct_ok(wl or dash._why_fallback(leg, pk))   # AGAINST it, so the one-liner's fact isn't said twice)
        except Exception:                                    # noqa: BLE001
            pass
        lines = cc.check(pk, leg, lines, games, why=wl)
    finally:
        cc.note = quiet
    return wl, lines


def raw(leg):
    return leg.get("why_line") or "", [x for x in leg.get("breakdown") or [] if isinstance(x, str)]


# ---- the box score: who really played ---------------------------------------------------------------------------------
def box_names(league, gid, team):
    """The men in a finished game's box score for one team (None = no box score on file)."""
    return cc.box_played(league, gid, team)


def _in(name, pool):
    try:
        import sports_absences
        return sports_absences.match(name, pool)
    except Exception:                                        # noqa: BLE001
        return _plain(name) in pool


def said_out(leg, lines):
    """{'us': [names], 'them': [names]} the card says are OUT (its lists + its lines; a 'questionable:' part never)."""
    us, them = leg.get("team") or "", leg.get("opp") or ""
    ours = cc._card_names(list(leg.get("outs") or []) + list(leg.get("absent") or []))
    theirs = cc._card_names(leg.get("opp_outs"))
    body = " ".join(Q_SPLIT.split(x)[0] for x in lines if x.startswith(("🚑", "⚠️", "🌟")) and OUT_WORDS.search(x))
    gone = set(leg.get("stale") or [])
    return {"us": [n for n in dict.fromkeys(ours) if n in body and n not in gone and us],
            "them": [n for n in dict.fromkeys(theirs) if n in body and n not in gone and them]}


def after_the_game(pk, leg, games, lines):
    """Once the box score is in: who the card had OUT that played, the star it had 'in the lineup' who sat (the
    quarterback / goalie who didn't start is the card check's own who_plays)."""
    out = []
    g = games.get(leg.get("game_id"))
    if not g or g.get("status") != "final":
        return out
    lg = leg.get("league")
    side = leg.get("side")
    other = "away" if side == "home" else "home"
    if side not in ("home", "away"):
        return out
    so = said_out(leg, lines)
    for which, sd_ in (("us", side), ("them", other)):
        pool = box_names(lg, g["id"], g[sd_])
        if not pool:
            continue
        for nm in so[which]:
            if _in(nm, pool):
                ln = next((x for x in lines if nm in x), "")
                out.append(("stale", f"{nm} listed OUT for {g[sd_ + '_name']} - he played", ln))
        for x in lines:
            if x.startswith("🌟") and "in the lineup" in x and g[sd_ + "_name"] in x:
                part = x.split(" · ")[0]
                for nm in re.findall(r"([A-Z][\w.'-]+(?: [A-Z][\w.'-]+){1,2}) \(", part):
                    if not _in(nm, pool):
                        out.append(("stale", f"{nm} said 'in the lineup' for {g[sd_ + '_name']} - he didn't play", x))
    return out


# ---- the injury report: is the card's news still the news --------------------------------------------------------------
def with_the_report(leg, g, lines, injuries):
    """Before the game: the card's injury words against the report as it reads now."""
    out = []
    lg = leg.get("league")
    inj = (injuries or {}).get(lg)
    if inj is None or not g or g.get("status") != "pre":
        return out
    side = leg.get("side")
    if side not in ("home", "away"):
        return out
    other = "away" if side == "home" else "home"
    rows = {s_: sd._team_rows(inj, g[s_], g[s_ + "_name"]) for s_ in ("home", "away")}
    if not rows["home"] and not rows["away"]:
        return out                                           # (a report with nobody for either side: a hiccup)
    us = leg.get("team") or ""
    so = said_out(leg, lines)
    for which, s_ in (("us", side), ("them", other)):
        listed = {_plain(r[0]): r[2].lower() for r in rows[s_]}
        for nm in so[which]:
            st = next((v for k, v in listed.items() if _in(nm, {k})), None)
            ln = next((x for x in lines if nm in x), "")
            if st is None:
                out.append(("stale", f"{nm} listed out for {g[s_ + '_name']} - he's off the injury report now", ln))
            elif any(u in st for u in sd.UNSURE):
                out.append(("stale", f"{nm} listed out for {g[s_ + '_name']} - the report has him {st} now", ln))
    gone_us = [r for r in rows[side] if any(s in r[2].lower() for s in sd.SHORT_TERM + sd.UNSURE)]
    for x in lines:
        if cc.HEALTHY.search(x) and us in x:
            if not sd.covered(inj, lg, g[side], g[side + "_name"]):
                out.append(("false", f"'full squad' for {us} - we hold no injury data on them (unknown is never healthy)", x))
            elif gone_us:
                out.append(("stale", f"'full squad' for {us} - the report lists {gone_us[0][0]} ({gone_us[0][2]}) now", x))
        if x.startswith("🌟") and "in the lineup" in x:
            part = x.split(" · ")[0]
            for s_ in ("home", "away"):
                for r in rows[s_]:
                    if r[0] in part and any(s in r[2].lower() for s in sd.SHORT_TERM):
                        out.append(("stale", f"{r[0]} said 'in the lineup' - the report has him {r[2].lower()} now", x))
    return out


# ---- the review: the score it says is the score ----------------------------------------------------------------------
_SC = re.compile(r"(?<![\d+.-])(\d{1,3})-(\d{1,3})(?![\d-])")
_FINAL_SAID = re.compile(r"\b(?:won|lost)\b[^.]*\d+-\d+")


def review_check(pk, leg, games):
    """A graded card's 📝 review: every score in it is the final or a score the game really stood at after a period (the
    leg's own period-by-period flow). [] = fine / nothing to check."""
    try:
        import sports_dashboard as dash
        rv = dash._rev_text(pk, leg)
    except Exception:                                        # noqa: BLE001
        rv = ""
    g = games.get(leg.get("game_id"))
    if not rv or not g or g.get("status") != "final":
        return []
    try:
        final = {int(g["home_score"]), int(g["away_score"])}
    except (TypeError, ValueError):
        return []
    ok = [final]
    fl = leg.get("flow") or {}
    try:
        a = [int(x) for x in str(fl.get("a") or "").split(",") if x != ""]
        h = [int(x) for x in str(fl.get("h") or "").split(",") if x != ""]
        ok += [{x, y} for x, y in zip(a, h)]
        ok += [{sum(a[:i + 1]), sum(h[:i + 1])} for i in range(min(len(a), len(h)))]
    except ValueError:
        a = h = []
    pairs = [{int(x), int(y)} for x, y in _SC.findall(rv)]
    if not pairs:
        return []
    out = []
    if final not in pairs and _FINAL_SAID.search(rv):
        out.append(("false", f"the review's final score isn't the game's ({g['away_score']}-{g['home_score']})", rv))
    elif a and h and any(p_ not in ok for p_ in pairs):
        out.append(("false", "a score in the review the game never stood at", rv))
    return out


# ---- one card -----------------------------------------------------------------------------------------------------------
def audit_leg(pk, leg, games, injuries=None, as_shown=True):
    """[(class, why, line)] for one card: 'false' / 'stale' / 'nonsense'."""
    out = []
    wl, lines = shown(pk, leg, games) if as_shown else raw(leg)
    cx = cc.ctx_of(pk, leg)
    allc = [x for x in [wl] + list(lines) if x]
    contra = cc.card_sense(leg, lines)
    for x in allc:
        _, w = cc.wording(x, cx, leg)
        if w and any(k in w for k in WORDING_NONSENSE):
            out.append(("nonsense", w, x))
        elif w:
            out.append(("lingo", w, x))
        if not cc.BOTTOM.match(x):
            fw = cc.facts(x, leg, games)
            if fw:
                out.append(("false", fw, x))
            dw = cc.derived(x, leg, games)
            if dw:                                           # (rest talk is true numbers making no argument)
                out.append(("nonsense" if "rest talk" in dw else "false", dw, x))
            sw = cc.sense(x, leg)
            if sw:
                out.append(("nonsense", sw, x))
            pw = cc.who_plays(x, leg, games)
            if pw:
                out.append(("stale", pw, x))
        if x in contra:
            out.append(("nonsense", contra[x], x))
    if x_ := (cc._no_move(wl)[1] if wl else ""):
        out.append(("nonsense", x_, wl))
    g = games.get(leg.get("game_id"))
    out += with_the_report(leg, g, allc, injuries)
    out += after_the_game(pk, leg, games, allc)
    out += review_check(pk, leg, games)
    seen, uniq = set(), []
    for c, w, x in out:
        if (w, x) not in seen:
            seen.add((w, x))
            uniq.append((c, w, x))
    return uniq, len(allc)


# ---- 🧹 the card-quality score (11/18, results/studies/cards_1118) ---------------------------------------------------------
# The owner, 11/18, on the Nuggets card: "the breakdown just sucks ... This has been a major problem with these breakdowns
# ... This needs to be fixed permanently." Every line on that card was TRUE - the fact audit above passed it. What was wrong
# is what a card is FOR: it argued against its own pick, said the one-liner twice and named a bench man as the knock. So a
# card is also scored on how well it makes its case (sports_card_check.quality): every line that knocks us / argues for
# them / says nothing / repeats / talks jargon / names a man out who doesn't matter.
#   100 = clean. -15 for each bad line the write-up put on the card (the check cuts it on the page - but the pool wrote
#   it), -25 for each one a reader can still SEE, -20 for a unit play left with fewer than 2 fact lines.
# A PROBLEM on the hourly bug check: a bad line still on the page; a live card whose write-up put 3+ bad lines on it (a
# pool went bad - fix it at the root); a live unit play under its floor of fact lines (class "short", the card named).
Q_WRITTEN, Q_SHOWN, Q_THIN, Q_ROOT = 15, 25, 20, 3


def card_quality(pk, leg, games):
    """{'score', 'written': [(kind, line)], 'shown': [(kind, line)], 'facts': n} for one board card."""
    w_why, w_lines = raw(leg)
    written = cc.quality(leg, w_why, w_lines, games)
    try:
        s_why, s_lines = shown(pk, leg, games)
    except Exception:                                        # noqa: BLE001
        s_why, s_lines = w_why, w_lines
    still = cc.quality(leg, s_why, s_lines, games)
    facts = cc.fact_lines(s_lines)
    unit = not (pk.get("lean") or leg.get("is_lean") or leg.get("tier") in ("lean", "strong"))
    thin = unit and facts < cc.THIN_BODY
    score = max(0, 100 - Q_WRITTEN * len(written) - Q_SHOWN * len(still) - (Q_THIN if thin else 0))
    # 🧱 11/18 (night) THE FLOOR IS A STANDING CHECK (the owner: "it's just short and fucking vague ... This is a fucking
    # permanent bug" / "permanent fix for everything going forward"): a card under its floor on the page (6 fact lines a
    # unit play, 5 a lean - sports_breakdown_v24.FLOOR_*) is named, with why it's short.
    floor = cc.card_floor({"lean": not unit})
    short = facts < floor
    why = ""
    if short:
        spare = leg.get("spare")
        why = ("written before the refill kept spare facts - the next run rewrites it" if spare is None else
               "the engine holds no more facts for this side (a new season, a team we don't fully see, or a side with "
               "little going for it but the price)" if not spare else
               f"{len(spare)} spare fact{'s' if len(spare) != 1 else ''} didn't pass the page's checks")
    return {"score": score, "written": written, "shown": still, "facts": facts, "thin": bool(thin),
            "floor": floor, "short": bool(short), "short_why": why, "unit": bool(unit)}


def early_quality(p, lines, games):
    """[(kind, line)] for an early row's lines: a clause that knocks our own side, a losing live record, rest talk."""
    leg = cc._early_leg(p)
    out = []
    for x in lines or []:
        try:
            w = cc.early_for_us(x, leg, games)[1]
        except Exception:                                    # noqa: BLE001
            w = ""
        if w and cc.Q_KNOCK in w:
            out.append(("knocks us", x))
    return out


def audit_early(p, games):
    """An early play's lines (its why + fact lines): a record / last-game margin that moved since it posted."""
    out = []
    try:
        import sports_early
        why = sports_early.no_pct(p) if (p.get("spot") in sports_early.SPOTS or p.get("why")) else ""
        lines = [x for x in [why] + list(sports_early.fresh_facts(sports_early.card_facts(p), why)) if x]
    except Exception:                                        # noqa: BLE001
        lines = [x for x in [p.get("why")] + list(p.get("facts") or []) if x]
    return lines


def run(picks, early, games, injuries=None, since=None, as_shown=True, live_only=True):
    """The report: every card (live ones only, or everything posted since `since`) with what's wrong on it."""
    cc.reset()
    rep = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "cards": 0, "lines": 0, "problems": [],
           "by_class": {}, "bad_cards": 0, "shown": bool(as_shown)}
    Q = {"n": 0, "sum": 0, "thin": 0, "short": [], "facts": 0, "written": {}, "shown": {}, "cards": []}
    if not live_only:                                        # (a history run reads the graded cards' 📝 reviews too)
        try:
            import sports_dashboard as dash
            dash._GAMES_[0] = games
            dash._history(picks)
        except Exception:                                    # noqa: BLE001
            pass
    for pk in picks or []:
        if since and (pk.get("date") or "") < since:
            continue
        for leg in pk.get("legs") or []:
            g = games.get(leg.get("game_id"))
            if live_only and (pk.get("status") != "open" or not g or g.get("status") != "pre"):
                continue
            if not leg.get("breakdown") and not leg.get("why_line"):
                continue
            try:
                probs, n = audit_leg(pk, leg, games, injuries, as_shown)
            except Exception as e:                           # noqa: BLE001 - the audit never breaks a run
                probs, n = [("error", f"the audit broke on this card: {str(e)[:80]}", "")], 0
            try:                                             # 🧹 11/18: the card-quality score
                q = card_quality(pk, leg, games)
            except Exception:                                # noqa: BLE001
                q = None
            if q:
                Q["n"] += 1
                Q["sum"] += q["score"]
                Q["thin"] += q["thin"]
                Q["facts"] += q["facts"]
                if q["short"] and q["unit"]:
                    Q["short"].append({"date": pk.get("date"), "team": leg.get("team"), "league": leg.get("league"),
                                       "facts": q["facts"], "floor": q["floor"], "why": q["short_why"]})
                for k, _ in q["written"]:
                    Q["written"][k] = Q["written"].get(k, 0) + 1
                for k, _ in q["shown"]:
                    Q["shown"][k] = Q["shown"].get(k, 0) + 1
                if q["score"] < 100:
                    Q["cards"].append({"date": pk.get("date"), "team": leg.get("team"), "league": leg.get("league"),
                                       "score": q["score"], "facts": q["facts"],
                                       "written": [[k, str(x)[:200]] for k, x in q["written"]][:8],
                                       "shown": [[k, str(x)[:200]] for k, x in q["shown"]][:8]})
                for k, x in (q["shown"] if as_shown else []):   # (a bad line a reader can still see: always a problem)
                    probs.append(("quality", f"a line that {k} is still on the page", x))
                if live_only and len(q["written"]) >= Q_ROOT:
                    kinds = {}
                    for k, _ in q["written"]:
                        kinds[k] = kinds.get(k, 0) + 1
                    probs.append(("quality", f"the write-up put {len(q['written'])} bad lines on this card ("
                                  + ", ".join(f"{n_} {k}" for k, n_ in sorted(kinds.items(), key=lambda z: -z[1]))
                                  + f") - the check cut them; card quality {q['score']}/100, fix the pool", q["written"][0][1]))
                if live_only and q["short"] and q["unit"]:  # (11/18 night: under the floor = a PROBLEM, the card named)
                    probs.append(("short", f"a short card: {q['facts']} fact line{'s' if q['facts'] != 1 else ''} on a "
                                           f"unit play, the floor is {q['floor']} - {q['short_why']}", ""))
            rep["cards"] += 1
            rep["lines"] += n
            rep["bad_cards"] += bool([p for p in probs if p[0] != "lingo"])
            for c, w, x in probs:
                rep["problems"].append({"date": pk.get("date"), "team": leg.get("team"), "league": leg.get("league"),
                                        "kind": pk.get("kind"), "class": c, "why": w, "line": str(x)[:260]})
    for p in (early or {}).get("picks") or []:
        if since and (p.get("posted") or "")[:10] < since:
            continue
        g = games.get(p.get("game_id"))
        if live_only and (p.get("result") or not g or g.get("status") != "pre"):
            continue
        lines = audit_early(p, games)
        eq_w = early_quality(p, lines, games)                # 🧹 11/18: an early row argues for our side too
        Q["n"] += 1
        Q["sum"] += max(0, 100 - Q_WRITTEN * len(eq_w))
        for k, x in eq_w:
            Q["written"][k] = Q["written"].get(k, 0) + 1
        if eq_w:
            Q["cards"].append({"date": (p.get("start") or "")[:10], "team": p.get("team"), "league": p.get("league"),
                               "score": max(0, 100 - Q_WRITTEN * len(eq_w)), "facts": len(lines),
                               "written": [[k, str(x)[:200]] for k, x in eq_w], "shown": []})
        if as_shown:
            quiet = cc.note
            cc.note = lambda *a, **k: None
            try:
                lines = cc.early_lines(p, lines, games=games)
            finally:
                cc.note = quiet
        rep["cards"] += 1
        rep["lines"] += len(lines)
        bad = 0
        for x in lines:
            w = cc.early_fact(p, x, games) if not (as_shown and p.get("result")) else ""   # (a graded row is history)
            mv = cc._no_move(x)[1]
            for c, why in (("nonsense" if "rest talk" in w else "stale", w), ("nonsense", mv)):
                if why:
                    bad = 1
                    rep["problems"].append({"date": (p.get("start") or "")[:10], "team": p.get("team"),
                                            "league": p.get("league"), "kind": "early", "class": c, "why": why,
                                            "line": str(x)[:260]})
        rep["bad_cards"] += bad
    for p in rep["problems"]:
        rep["by_class"][p["class"]] = rep["by_class"].get(p["class"], 0) + 1
    rep["quality"] = {"score": round(Q["sum"] / Q["n"]) if Q["n"] else 100, "cards": Q["n"], "thin": Q["thin"],
                      "short": Q["short"][:20], "under_floor": len(Q["short"]),
                      "avg_facts": round(Q["facts"] / Q["n"], 1) if Q["n"] else 0,
                      "written": Q["written"], "shown": Q["shown"],
                      "worst": sorted(Q["cards"], key=lambda c: c["score"])[:12]}
    return rep


def save(rep, path=OUT):
    try:
        with open(path, "w") as f:
            json.dump(rep, f, indent=1, sort_keys=True, ensure_ascii=False)
    except OSError as e:
        print(f"card audit: couldn't write {path}: {e}")


def words(rep, n=8):
    """The report as PROBLEM lines (the hourly bug check prints these). Lingo catches the check already rewrites on the
    page are not problems - only what a reader would still see wrong."""
    real = [p for p in rep.get("problems") or [] if p.get("class") != "lingo"]
    return [f"{p['class'].upper()} on the {p['team']} card ({p['date']}): {p['why']} - \"{p['line'][:120]}\"" for p in real[:n]]


if __name__ == "__main__":
    a = sys.argv[1:]
    since = a[a.index("--since") + 1] if "--since" in a else None
    out = a[a.index("--out") + 1] if "--out" in a else (None if since else OUT)
    games_ = sd.load_games()
    try:
        import sports_players as sp
        sp.CACHE.update(sp.load())
    except Exception:                                        # noqa: BLE001
        pass
    with open(os.path.join(sd.DATA, "picks.json")) as f_:
        picks_ = json.load(f_)
    if "--with-leans" in a:                                  # (the leans that came off the board 11/16 - posted cards too)
        try:
            with open(os.path.join(sd.DATA, "leans_removed.json")) as f_:
                picks_ = picks_ + json.load(f_)
        except (OSError, ValueError):
            pass
    try:
        with open(os.path.join(sd.DATA, "early.json")) as f_:
            early_ = json.load(f_)
    except (OSError, ValueError):
        early_ = {}
    inj_ = None
    if not since and "--no-report" not in a:                 # (the live run reads the report the way the engine does)
        lgs = {l["league"] for p in picks_ if p.get("status") == "open" for l in p.get("legs") or []}
        inj_ = {lg: sd.fetch_injuries(lg) for lg in lgs}
    rep_ = run(picks_, early_, games_, inj_, since=since, as_shown="--raw" not in a, live_only=not since)
    if out:
        save(rep_, out)
    print(f"card audit: {rep_['cards']} cards, {rep_['lines']} lines, {len(rep_['problems'])} problems "
          f"{rep_['by_class']} on {rep_['bad_cards']} cards")
    q_ = rep_.get("quality") or {}
    print(f"card quality: {q_.get('score')}/100 on {q_.get('cards')} cards - bad lines the write-up put on them {q_.get('written')}, "
          f"still on the page {q_.get('shown')}, thin cards {q_.get('thin')}; fact lines a card: "
          f"{q_.get('avg_facts')}, unit cards under the floor of 6: {q_.get('under_floor')}")
    for c in q_.get("short") or []:
        print(f"   SHORT {c['date']} {c['league']} {c['team']}: {c['facts']} fact lines (floor {c['floor']}) - {c['why']}")
    for p_ in rep_["problems"]:
        if p_["class"] != "lingo" or "--all" in a:
            print(f"  {p_['class'].upper():8} {p_['date']} {p_['team']}: {p_['why']}\n           {p_['line'][:200]}")
