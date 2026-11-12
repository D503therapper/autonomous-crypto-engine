"""🏀 THE NBA OVER WHEN THE MAIN MEN SIT (11/12 - FABLE: 15 STUDIES; results/studies/fifteen_1112/s10_s13_totals.py,
s10b_nba_out_over.py, s10c_live_rule.py). The owner, 11/12: "we also need to ... figure out how to be profitable at ...
the over-unders" + "add plays what you need to" - the one total outside college hoops that cleared the five checks.

THE FINDING (every NBA regular-season close 2018-26, both teams 10+ games in, the box scores for who played): take each
team's three men with the most minutes so far this season - six men a game. When THREE OR MORE of the six don't play,
the book's total drops too far: the OVER went 354-254, +11.0% on 615 (train 2018-21 +11.6%, 4 of 4 seasons up; blind
2022 on +10.4%, 4 of 4 up; z +2.9; the under -20.0%, z -5.3). The dose is a step, not noise: 0 out -4.7%, 1 out -3.9%,
2 out -1.6%, 3 out +12.5%, 4 out +10.3%; games scored +1.7 points over the total with a leader out against +0.5 for
every game. A point WORSE than the close it still made +7.7% (8 of 8 seasons), two worse +2.9%. 0 of 2,000 random sets
of NBA overs matched it (0 of 4,000 in both halves at once). Other ways to pick the men agree in sign: the top three
over the last 15 games +13.9% on 249 (8 of 8 seasons), six or more of the two teams' top TEN out +14.7% on 448 (z +3.4).
NEVER ONE FACTOR: when both teams' own season scoring sat 3+ points UNDER the total the same over made only +4.4% on
162 - so the number may sit at most 3 over both teams' scoring; inside that: 267-182, +13.4% on 453 (z +3.0, 8 of 8).

THE LIVE RULE: an NBA regular-season game, both teams 10+ box games this season, 3+ of the six listed OUT on the
injury report (a doubtful / questionable man never counts; a man who hasn't played any of his team's last 5 games and
isn't on the report is gone - traded - and counts, as he does in the study), both teams' scoring no more than
READ_FIGHT under the total, the over no worse than MAX_PRICE. THE CLOCK: the study's price is the CLOSE - the number
after the news. A total can sit stale for a few minutes when a man is ruled out, so the play waits until the same
3+ have been out on our report for WAIT_MIN (the next hourly run) before it takes the number - never a stale one.
½u, its own record, judged at QUIT[0] graded: under QUIT[1] on the units = it's off."""
import re
from datetime import datetime, timezone

FROM = "2026-11-13"             # games from this Pacific game day
MIN_GAMES = 10                  # both teams' box games this season before the top three mean anything
TOP_N = 3                       # the three men with the most minutes this season, a team
NEED_OUT = 3                    # 3+ of the six out
GONE_GAMES = 5                  # off the report and absent from the team's last 5 box games = gone (traded): he counts
READ_FIGHT = 3.0                # the total limit: no over when the number is more than 3 over both teams' scoring
MAX_PRICE = -115                # the price limit (the cell: -112 or cheaper +12.0% on 572; worse -1.9% on 43)
GOOD_TO = 1.0                   # the card's "good to": a point worse than the close still +7.7%, two worse +2.9%
WAIT_MIN = 50                   # the same 3+ on our report this long before we take the number (never a stale total)
QUIT = (40, -0.05)              # judged at 40 graded: ROI under -5% on the units risked = off
REC = "267-182"                 # the rule's record at the close, 2018-26 (s10b: the read not fighting) - the card's line
UNITS = 0.5


def _nm(x):
    return " ".join(re.sub(r"[^a-z ]", "", str(x or "").lower().replace(" jr", "").replace(" iii", "")
                           .replace(" ii", "")).split())


def _season(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 8 else y - 1


def team_minutes(rows, season, before):
    """{team id: {"games": n, "top": [(name, minutes a game played, total minutes)], "recent": {name: played in the last
    GONE_GAMES}}} from this season's NBA box rows (sports_roster.load) for games that started before `before` (iso)."""
    by_game = {}
    for r in rows:
        st = r.get("start") or ""
        if not st or st >= before or _season(st) != season:
            continue
        try:
            import json
            m = float(json.loads(r.get("stats") or "{}").get("minutes") or 0)
        except (ValueError, TypeError):
            m = 0.0
        by_game.setdefault((r.get("team"), st, r.get("gid")), {})[r.get("player")] = m
    teams = {}
    for (t, st, gid), d in sorted(by_game.items(), key=lambda kv: kv[0][1]):
        teams.setdefault(t, []).append(d)
    out = {}
    for t, gs in teams.items():
        tot, gp = {}, {}
        for d in gs:
            for p, m in d.items():
                tot[p] = tot.get(p, 0.0) + m
                if m > 0:
                    gp[p] = gp.get(p, 0) + 1
        top = sorted(tot.items(), key=lambda kv: -kv[1])[:TOP_N]
        last = gs[-GONE_GAMES:]
        out[t] = {"games": len(gs),
                  "top": [(p, (m / gp[p]) if gp.get(p) else 0.0, m) for p, m in top],
                  "recent": {p: any(d.get(p, 0) > 0 for d in last) for p, _ in top}}
    return out


def outs(team_id, team_name, tm, inj):
    """[(name, minutes a game)] - this team's top-minutes men who are OUT tonight: listed out on the report (never a
    doubtful / questionable / probable man), or off the report and absent from the team's last GONE_GAMES games."""
    import sports_nba_roster as nr
    info = tm.get(str(team_id))
    if not info or info["games"] < MIN_GAMES:
        return None
    rep = nr.report_chances(inj, team_id, team_name)
    got = []
    for name, mpg, _ in info["top"]:
        c = rep.get(nr._nm(name))
        if c is not None:
            if c[0] <= 0.0:
                got.append((name, mpg))
        elif not info["recent"].get(name, True):
            got.append((name, mpg))
    return got


def quit_now(st, units_of):
    """The judge: QUIT[0]+ graded and the ROI on the units risked under QUIT[1] = no more posts."""
    ps = [p for p in st.get("picks", []) if p.get("spot") == "nba_out_over" and p.get("result") in ("won", "lost")]
    if len(ps) < QUIT[0]:
        return False
    risk = sum(units_of(p) for p in ps)
    net = sum(units_of(p) * ((p["odds"] / 100 if p["odds"] > 0 else 100 / -p["odds"]) if p["result"] == "won" else -1.0) for p in ps)
    return risk > 0 and net / risk < QUIT[1]


def candidates(games, st, now, inj, rows=None, se=None):
    """The 🏀 overs to post now (see the module doc). inj = the NBA injury report ({team: [(player, pos, status)]});
    None = we DON'T KNOW who's out = no play. st carries 'nba_out_seen' {game id: [first seen iso, the men]}."""
    import sports_early as _se
    se = se or _se
    if inj is None or quit_now(st, se.units):
        return []
    seen = st.setdefault("nba_out_seen", {})
    for gid in [k for k in seen if (games.get(k) or {}).get("status") != "pre"]:
        seen.pop(gid, None)                                  # (a game that tipped or left the slate: its clock goes)
    out, tms, avs = [], {}, {}
    for g in games.values():
        if g.get("league") != "nba" or g.get("status") != "pre" or (g.get("stype") or "2") != "2" or not g.get("start"):
            continue
        st_ = se._t(g["start"])
        if not now < st_ or st_.astimezone(se.PT).date().isoformat() < FROM:
            continue                                         # never a started game; games from FROM
        tot, odds = se.sm._num(g.get("total")), se._int(g.get("over_odds")) or -110
        if tot is None or odds < MAX_PRICE:
            continue
        s = _season(g["start"])
        if s not in tms:
            if rows is None:
                import sports_roster
                rows = sports_roster.load("nba", seasons=[s])
            tms[s] = team_minutes(rows, s, now.strftime("%Y-%m-%dT%H:%MZ"))
            avs[s] = se.scoring_avgs(games, "nba", s, now)
        oh = outs(g.get("home"), g.get("home_name"), tms[s], inj)
        oa = outs(g.get("away"), g.get("away_name"), tms[s], inj)
        if oh is None or oa is None or len(oh) + len(oa) < NEED_OUT:
            seen.pop(g["id"], None)                          # (a man came back: the clock starts over)
            continue
        names = sorted(n for n, _ in oh + oa)
        was = seen.get(g["id"])
        stamp = now.strftime("%Y-%m-%dT%H:%MZ")
        still = sorted(set(was[1]) & set(names)) if was else []
        if len(still) < NEED_OUT:                            # first look (or not the same three): the clock starts now
            seen[g["id"]] = [stamp, names]
            continue
        seen[g["id"]] = [was[0], still]                      # the same 3+ still out: the clock keeps running
        first = datetime.strptime(seen[g["id"]][0], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        if (now - first).total_seconds() < WAIT_MIN * 60:
            continue                                         # the book gets its hour to move the number
        h, a = avs[s].get(g.get("home")), avs[s].get(g.get("away"))
        if not h or not a or h[2] < MIN_GAMES or a[2] < MIN_GAMES:
            continue
        read = (h[0] + a[1] + a[0] + h[1]) / 2
        if read - tot < -READ_FIGHT:
            continue                                         # the number's run past both teams' scoring + 3: no bet
        facts = []
        for nm, o in ((g.get("home_name"), oh), (g.get("away_name"), oa)):
            if o:
                facts.append(f"{nm} without " + " and ".join(f"{n} ({m:.0f} minutes a night)" for n, m in o))
        for side, av in (("home", h), ("away", a)):
            facts.append(f"{g.get(side + '_name')}'s games are averaging {av[0] + av[1]:.0f} points - scoring {av[0]:.0f}, "
                         f"giving up {av[1]:.0f} through {av[2]} games")
        for side in ("home", "away"):
            ln = se._alt_last(games, g.get(side), s, now, league="nba")
            if ln:
                facts.append(ln)
        w = sum(1 for p in st.get("picks", []) if p.get("spot") == "nba_out_over" and p.get("result") == "won")
        l_ = sum(1 for p in st.get("picks", []) if p.get("spot") == "nba_out_over" and p.get("result") == "lost")
        facts.append(f"NBA overs with three or more of the six top-minutes guys out are {REC} since 2018"
                     + (f", {w}-{l_} since we started betting it" if w + l_ else ""))
        facts.append(f"Good to {tot + GOOD_TO:g} - don't take it past that, or worse than {MAX_PRICE}")
        n_out = len(oh) + len(oa)
        word = {3: "Three", 4: "Four", 5: "Five", 6: "All six"}.get(n_out, str(n_out))
        out.append({"game_id": g["id"], "league": "nba", "market": "total", "side": "over", "line": tot,
                    "team": f"Over {tot:g}", "opp": f"{g.get('away_name')} @ {g.get('home_name')}", "odds": odds,
                    "start": g["start"], "spot": "nba_out_over", "spots": ["nba_out_over"], "fades": [],
                    "read": round(read, 1), "good_to": tot + GOOD_TO, "out": names, "facts": facts,
                    "why": f"🏀 {word} of the six guys who play the most in this one are out ({', '.join(names)}), and NBA "
                           f"overs are {REC} since 2018 when that many of the main guys sit.",
                    "posted": stamp, "result": None})
    return out
