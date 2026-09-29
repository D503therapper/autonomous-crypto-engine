"""The full breakdown behind a pick: the facts the engine weighed, in plain words, frozen at posting time.
Shown on the dashboard behind a "Full breakdown" tap."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import re
import sports_data as sd
import sports_lingo
import sports_model as sm
import sports_players as sp

PT = ZoneInfo("America/Los_Angeles")
VERSION = 28          # bump when the wording changes: posted plays get their breakdown rewritten (never the pick)


def _t(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _am(a):
    return f"+{a}" if a > 0 else str(a)


def _team_games(fin, tid):
    return [g for g in fin if tid in (g["home"], g["away"])]


def _line(g, tid):
    """'W 27-20 vs Lions' from tid's point of view."""
    home = g["home"] == tid
    us, them = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    opp = g["away_name"] if home else g["home_name"]
    res = "W" if us > them else "L" if us < them else "T"
    return f"{res} {us}-{them} {'vs' if home else '@'} {opp}"


def _season(games_of_team, before):
    """This season's games: walk back until a break of 75+ days (the off-season)."""
    out = []
    last = before
    for g in reversed(games_of_team):
        t = _t(g["start"])
        if (last - t).days > sm.BREAK_DAYS:
            break
        out.append(g)
        last = t
    return list(reversed(out))


def _record(gs, tid):
    w = sum(1 for g in gs if _line(g, tid).startswith("W"))
    lo = sum(1 for g in gs if _line(g, tid).startswith("L"))
    t = len(gs) - w - lo
    return f"{w}-{lo}" + (f"-{t}" if t else "")


def _streak(gs, tid):
    """'won 5 straight' / 'lost 3 straight' / ''."""
    if not gs:
        return ""
    last = _line(gs[-1], tid)[0]
    n = 0
    for x in reversed(gs):
        if _line(x, tid)[0] != last:
            break
        n += 1
    if n < 2 or last == "T":
        return ""
    return f"{'won' if last == 'W' else 'lost'} {n} straight"


def _names(rows, k=3):
    names = [n for n, _, _ in rows[:k]]
    more = len(rows) - len(names)
    return ", ".join(names) + (f" +{more} more" if more > 0 else "")


SLANG = {                        # our big phrases: each FAMILY shows up once on a board (any wording of it)
    "cheeks": r"cheeks", "complete ass": r"complete ass", "smack": r"smack that ass", "cook": r"\bcook(ing)?\b",
    "eat": r"\b(let's eat|we eat|we're eating|we eating|eat)\b", "tap in": r"tap in", "we gon see": r"gon' see|finna see",
    "trust": r"trust (the algorithm|it)", "let y'all down": r"let y'all down", "levels": r"levels to this|whole nother caliber",
    "trippin": r"trippin", "business": r"go to work|handle business|take care of business", "sheep": r"sheep",
    "clowns": r"clown", "run it back": r"run it back", "coming back": r"always be coming back", "gift": r"a gift",
    "free money": r"free money", "lock it in": r"lock it in", "tail it": r"tail it", "heater": r"heater",
    "nice": r"\bnice\b", "go off": r"go(ing)? off", "no answer": r"no answer", "watch": r"watch (him|her)|just watch",
    "problem": r"a problem", "different": r"different|built for|another level|ain't regular", "him": r"\bis (him|her)\b",
    "light": r"light work|easy work|handle .* light", "long day": r"long (day|night)", "ready": r"ain't ready",
    "pray": r"better pray", "mark it": r"mark it", "show": r"put on a show", "silly": r"look silly",
    "sleep": r"in their sleep|don't sleep", "trouble": r"in trouble", "on one": r"been on one|feeling it",
    # the context lines (rivalries, travel, domes, stakes, refs, pregame talk)
    "bad blood": r"bad blood", "no love lost": r"no love lost", "frequent flyer": r"frequent flyer",
    "suitcase": r"out of a suitcase", "backs to the wall": r"backs? (are )?(to|against) the wall",
    "nothing to play for": r"nothing to play for", "zebras": r"zebra", "hot seat": r"hot seat",
    "bulletin board": r"bulletin[- ]board", "circled": r"circled", "fishbowl": r"fishbowl", "thermostat": r"thermostat"}


def slang_in(texts):
    """The phrase families already used in these write-ups (so nothing else on the dashboard repeats them)."""
    return {f"slang:{k}" for t in texts for k, pat in SLANG.items() if re.search(pat, (t or "").lower())}


def dashboard_texts(skip=()):
    """Every write-up on the dashboard right now - open main-board picks and pending tennis picks - except the legs in
    `skip` (the ones being rewritten)."""
    import json
    import os
    out = []
    for path, key in ((os.path.join(sd.DATA, "picks.json"), "legs"), (os.path.join(sd.DATA, "tennis", "picks.json"), "picks")):
        try:
            with open(path) as f:
                cards = json.load(f)
        except (OSError, ValueError):
            continue
        for c in cards[-12:]:
            for l in c.get(key) or []:
                if l.get("result") is None and (l.get("id") or l.get("game_id"), l.get("side"), l.get("market")) not in skip:
                    out += l.get("breakdown") or []
    return out


def recent_texts(picks=None, since=None, skip=()):
    """[(line, names)] for every main-board write-up posted since `since` (an ISO date, default yesterday in PT) -
    open AND graded, today's and yesterday's - so a new board never reuses a phrase from them. `picks`: the board's
    cards (read from picks.json when None); `skip`: legs being rewritten (their old wording doesn't count)."""
    import json
    import os
    from datetime import timedelta
    since = since or (datetime.now(PT).date() - timedelta(days=1)).isoformat()
    if picks is None:
        try:
            with open(os.path.join(sd.DATA, "picks.json")) as f:
                picks = json.load(f)
        except (OSError, ValueError):
            return []
    out = []
    for c in picks:
        if str(c.get("date") or "") < since:
            continue
        for l in c.get("legs") or []:
            if (l.get("id") or l.get("game_id"), l.get("side"), l.get("market")) in skip:
                continue
            nm = tuple(x for x in (l.get("team"), l.get("opp")) if x)
            out += [(x, nm) for x in l.get("breakdown") or []]
    return out


def memory(picks=None, since=None, skip=()):
    """What a board starts out knowing: our big phrases already on the dashboard (once a board) plus every 4-word run
    written today or yesterday (never twice in a row)."""
    return slang_in(dashboard_texts(skip)) | recent_grams(recent_texts(picks, since, skip))


def grams(text, names=(), n=4):
    """The 4-word runs in a line (names and numbers -> _): what makes two write-ups read alike. No run is said twice
    on a board or from one day to the next - words come back, phrases don't."""
    t = f" {text or ''} ".lower()
    t = re.sub(r"^\W*bottom line:", " ", t)               # (the card's fixed label - what follows it still can't repeat)
    for nm in names:
        if nm:
            t = t.replace(str(nm).lower(), " _ ")
    t = re.sub(r"[+-]?\d+(\.\d+)?%?", " # ", t)
    w = []
    for x in re.findall(r"[a-z_#']+", t):                  # a run of names/numbers is one blank ("_"), however it
        x = "_" if x.strip("'") in ("_", "#") else x      # was written: yesterday's "9-4" and today's {rec} match
        if x.strip("'") and not (x == "_" and w and w[-1] == "_"):
            w.append(x)
    return {"g:" + " ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def recent_grams(entries):
    """{4-word runs} of earlier write-ups: entries = [(text, (names...)), ...]."""
    out = set()
    for text, names in entries:
        out |= grams(text, names)
    return out


class Voice:
    """Picks a way to say each line: different wording from game to game and day to day, and never the same
    wording twice on one board (share one `used` set across a board's breakdowns). No 4-word run repeats either
    (seed `used` with recent_grams(...) of yesterday's write-ups and it holds day to day too)."""

    def __init__(self, seed, used=None, names=()):
        self.seed, self.used, self.mine, self.names = seed, used if used is not None else set(), [], tuple(names)

    def say(self, key, options, must=False, names=()):
        """A fresh way to say it, or "" (the line is dropped) when every way is already taken on this board.
        must=True: a line the card can't go without (the pick, the bottom line) - reuse the least-repeated wording.
        Our big phrases ("cheeks clapped", "smack that ass"...) show up once a board, never on two cards in a row."""
        if not options:
            return ""
        nm = tuple(names) + self.names
        start = sum(map(ord, f"{self.seed}|{key}")) % len(options)
        order = [(start + i) % len(options) for i in range(len(options))]
        def slang(x):
            out = [f"slang:{k}" for k, pat in SLANG.items() if re.search(pat, x.lower())]
            if names:                                         # mixer lines: every opener / ending once a board
                t = x
                for nm_ in names:
                    t = t.replace(nm_, "_").replace(nm_[:1].upper() + nm_[1:], "_")
                out += [f"piece:{p.strip().lower()}" for p in re.split(r"(?<=[.!?])\s+", re.sub(r"^\W+", "", t)) if p.strip()]
            return out + sorted(grams(x, nm))
        unused = [n for n in order if f"{key}:{n}" not in self.used]
        fresh = [n for n in unused if not any(s in self.used for s in slang(options[n]))]
        if fresh:
            n = fresh[0]
        elif not must:
            return ""                                         # every fresh way repeats a phrase: drop the line
        else:                                                 # must say it: the wording that repeats the fewest phrases
            n = min(unused or order, key=lambda i: sum(s in self.used for s in slang(options[i])))
        self.used.add(f"{key}:{n}")
        self.used.update(slang(options[n]))
        self.mine.append(f"{key}:{n}")
        return re.sub(r"(?<!\.)\.\.(?!\.)", ".", options[n])   # "Bain Jr.." -> "Bain Jr."


HYPE = re.compile(r"trust the algorithm|lock it in|free money|easy money|hammer it|hammer time|smash it|we eating|real edge|"
                  r"tips it our way|let'?s eat|bag|money energy|can'?t lose|guaranteed", re.I)


def lean_tone(lines, leg, seed=""):
    """A LEAN has no edge on our numbers - so no hype: sentences that sell it hard come out, and the bottom line says
    straight that it's a lean, not a lock (the owner: never 'trust the algorithm' when there's zero edge)."""
    out = []
    for ln in lines or []:
        if ln.lstrip("✅ ").lower().startswith("bottom line"):
            continue
        keep = [s for s in re.split(r"(?<=[.!?])\s+", ln) if s and not HYPE.search(s)]
        if keep and not (len(keep) == 1 and len(keep[0]) <= 3):
            out.append(" ".join(keep))
    team = leg.get("team", "")
    ends = [x for x in _roll("lean", f"{seed}|{team}", team=team, tms=_pos(team)) if not HYPE.search(x)]
    out.append(ends[sum(map(ord, str(seed) + team)) % len(ends)])
    return out


def breakdown(leg, games, elo, injuries, used=None):
    """The main board's breakdown: the ORIGINAL voice (sports_breakdown_v24 - the owner, 9/29: the vocabulary rewrite
    came out vague and not our lingo). Tennis keeps rolling from this module's vocabulary."""
    import sports_breakdown_v24 as v24
    return v24.breakdown(leg, games, elo, injuries, used)


def _breakdown_vocab(leg, games, elo, injuries, used=None):
    """A plain-talk case for one leg: a list of short bullets ending with the bottom line."""
    g = games[leg["game_id"]]
    lg, side = leg["league"], leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg["team"], leg["opp"]
    start = _t(g["start"])
    fin = [x for x in sm.finals(games, lg) if _t(x["start"]) < start]
    ours, theirs = _team_games(fin, tid), _team_games(fin, oid)
    s_ours, s_theirs = _season(ours, start), _season(theirs, start)
    v = Voice(f"{g['id']}|{start:%Y-%m-%d}|{side}", used)
    pro = lg in ("nfl", "nba", "mlb", "nhl")
    the_us, the_them = (f"the {us}", f"the {them}") if pro else (us, them)
    field = {"nba": "court", "ncaab": "court", "wnba": "court", "nhl": "ice"}.get(lg, "field")
    W = {"field": field}                                  # plain words for the phrasebook (not facts)
    if ours and theirs and (start - _t(ours[-1]["start"])).days - (start - _t(theirs[-1]["start"])).days < 2:
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "better rested"]
    if (sm._num(g.get("elev")) or 0) < sm.THIN_AIR_M:  # "altitude edge" only means something up in real thin air
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "altitude edge"]
    out, said = [], set()          # said: reasons already used as a "because", so no line repeats another
    leg["bd_tags"] = v.mine        # which wordings this breakdown used (so the rest of the board avoids them)

    # form
    rec_u = _record(s_ours, tid) if s_ours else None
    heat = _streak(ours, tid)
    n_hot = int(heat.split()[1]) if heat.startswith("won") else 0
    if rec_u and n_hot >= 2:
        said.add("hotter recent form")
        out.append(_say(v, "hot", words={"a_n": _a(n_hot)}, us=us, rec=rec_u, cnt=n_hot))
    elif rec_u:
        out.append(_say(v, "rec", words={**W, "a_rec": _a(rec_u)}, us=us, rec=rec_u))
    if s_theirs:
        rec_t = _record(s_theirs, oid)
        cold = _streak(theirs, oid)
        n_cold = int(cold.split()[1]) if cold.startswith("lost") else 0
        w_t = sum(1 for x in s_theirs if _line(x, oid).startswith("W"))
        rating_t = elo[lg].r.get(oid, 1500.0) if elo.get(lg) is not None else 1500.0
        trash = (len(s_theirs) >= 3 and w_t / len(s_theirs) < 0.35) or n_cold >= 3 or rating_t < 1420
        if n_cold >= 2 and not trash:                   # the trash-talk line below covers the really bad ones
            out.append(_say(v, "cold", them=them, rec=rec_t, cnt=n_cold))

    # strength
    e = elo.get(lg)
    if e is not None:
        home_edge = 0 if str(g.get("neutral")) == "1" else (e.hfa if side == "home" else -e.hfa)
        gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0) + home_edge      # same yardstick as the card's reasons
        said.add("the stronger team")                   # said here either way (better / even / worse): not again later
        key = "better" if gap > 60 else "better_s" if gap > 15 else "worse" if gap < -15 else "even"
        out.append(_say(v, key, words=W, us=us, them=them, us_s=_pos(us)))

    # talk our talk when the other side's been bad (only when the numbers back it up)
    if s_theirs:
        w = sum(1 for x in s_theirs if _line(x, oid).startswith("W"))
        rating_them = e.r.get(oid, 1500.0) if e is not None else 1500.0
        n_cold = int(_streak(theirs, oid).split()[1]) if _streak(theirs, oid).startswith("lost") else 0
        if (len(s_theirs) >= 3 and w / len(s_theirs) < 0.35) or n_cold >= 3 or rating_them < 1420:
            out.append(_say(v, "trash", them=them, rec=_record(s_theirs, oid)))

    # last games: just the latest scores - the form/streak lines above already cover runs
    if ours:
        last_us = _line(ours[-1], tid)
        both = f"{us} {last_us}" + (f" · {them} {_line(theirs[-1], oid)}" if theirs else "")
        out.append(_say(v, "latest", words=W, both=both))

    # head to head
    h2h = [x for x in ours if oid in (x["home"], x["away"])]
    if h2h:
        last3 = h2h[-3:]
        w = sum(1 for x in last3 if _line(x, tid).startswith("W"))
        if 2 * w >= len(last3) and len(last3) > 1:
            out.append(_say(v, "h2h", us=us, them=them, us_s=_pos(us), them_s=_pos(them), w=w, cnt=len(last3)))
        elif w == 1 and len(last3) == 1:
            out.append(_say(v, "h2h1", us=us, them=them, us_s=_pos(us), res=_line(h2h[-1], tid)))

    # the key players: QB / starting pitcher / goalie (the fun part)
    rows = sp.CACHE.get(lg) or []
    role = sp.ROLE.get(lg)
    if rows and role:
        def who(team_side, tid_):
            if role == "SP":
                return g.get("sp_" + team_side) or None
            return sp.last_starter(rows, tid_, g["start"])
        for team_side, t_id, ours_ in ((other, oid, False), (side, tid, True)):
            name = who(team_side, t_id)
            if not name:
                continue
            txt, mood = sp.form_line(lg, name, rows, g["start"])
            if not txt:
                continue
            if not ours_ and mood == "cold":
                out.append(_say(v, role + "_cold", name=name, txt=txt))
            elif ours_ and mood == "hot":
                out.append(_say(v, role + "_hot", name=name, txt=txt))

    # situational spots the engine learned from 10 seasons of games
    rsn = leg.get("reasons") or []
    if "revenge game" in rsn:
        out.append(_say(v, "revenge", us=us, them=them))
        said.add("revenge game")
    if "letdown spot for the opponent" in rsn:
        out.append(_say(v, "letdown", them=them))
        said.add("letdown spot for the opponent")
    if "rolling off a blowout win" in rsn:
        out.append(_say(v, "momentum", words=W, us=us))
        said.add("rolling off a blowout win")
    temp, wind, rain = g.get("wx_temp", ""), g.get("wx_wind", ""), g.get("wx_rain", "")
    if "altitude edge" in rsn and (sm._num(g.get("elev")) or 0) >= sm.THIN_AIR_M:
        out.append(_say(v, "alt", elev=g.get("elev"), The_them=_cap(the_them), the_them=the_them))
        said.add("altitude edge")
    if "cold-weather edge" in rsn:
        out.append(_say(v, "cold_w", temp=temp, The_them=_cap(the_them), the_them=the_them, the_us=the_us))
        said.add("cold-weather edge")
    if "nasty weather helps us" in rsn:
        what = f"{wind} mph winds" if str(wind) not in ("", "0") and float(wind or 0) >= 15 else f"{rain} mm of rain"
        out.append(_say(v, "wx", what=what))
        said.add("nasty weather helps us")
    if "opponent's body clock is off" in rsn:
        out.append(_say(v, "jetlag", The_them=_cap(the_them), the_them=the_them))
        said.add("opponent's body clock is off")
    drama_r = next((r for r in rsn if r.startswith("opponent drama:")), None)
    if drama_r and leg.get("their_drama"):
        ev = leg["their_drama"][0]
        key = "drama_" + ev["kind"].replace("/", "_").replace(" ", "_")
        if key in T:
            out.append(_say(v, key, The_them=_cap(the_them), the_them=the_them, the_them_s=_pos(the_them),
                            hl=f"\"{ev.get('headline', '')}\""))
        said.add(drama_r)
    out += context_lines(leg, v, us, them, the_us, the_them, g)
    if "coming off a bye" in rsn:
        out.append(_say(v, "bye", us=us))
        said.add("coming off a bye")
    if "opponent on a short week" in rsn:
        out.append(_say(v, "short", them=them))
        said.add("opponent on a short week")

    # overseas games are always weird
    if str(g.get("intl")) == "1":
        out.append(_say(v, "intl", where=g.get("country") or "overseas"))

    # home / road
    if str(g.get("intl")) == "1":
        pass                                            # no real home crowd overseas
    elif side == "home":
        out.append(_say(v, "home", words=W, us=us))
    else:
        out.append(_say(v, "road", us=us))

    # rest
    if ours and theirs:
        d_us, d_them = (start - _t(ours[-1]["start"])).days, (start - _t(theirs[-1]["start"])).days
        if d_them <= 1 < d_us:
            out.append(_say(v, "b2b", us=us, them=them))
        elif d_us - d_them >= 2:
            out.append(_say(v, "rest", us=us, them=them, d=d_us - d_them))

    # pitchers
    if lg == "mlb" and (g.get("sp_home") or g.get("sp_away")):
        ps, po = g.get("sp_" + side) or "TBA", g.get("sp_" + other) or "TBA"
        nice = [f"⚾ {x}" for x in sports_lingo.good(ps, the_them, f"{g['id']}|sp")] \
            if "better starting pitcher" in (leg.get("reasons") or []) and ps != "TBA" else []   # our arm's the better one
        out.append(_say(v, "bump", extra=nice, names=(ps, the_them), ps=ps, po=po, us=us, them=them))

    # injuries
    inj = (injuries or {}).get(lg)
    if inj:
        ours_out, theirs_out = sd.team_injuries(inj, tid, us), sd.team_injuries(inj, oid, them)
        key_them = sd.team_key_out(inj, oid, them, lg)
        if key_them:
            out.append(_say(v, "keyout", them=them, pos=key_them[0][1], nm=key_them[0][0]))
        if theirs_out and len(theirs_out) > len(ours_out):
            out.append(_say(v, "banged", them=them, them_s=_pos(them), hurt=_names(theirs_out)))
        elif not ours_out:
            out.append(_say(v, "healthy", us=us))

    # a starting QB/goalie out: the line moved for the INJURY, not sharp money - say that, never "sharps"/"clowns"
    op, now = sm._int(g.get(f"ml_{side}_open")), sm._int(g.get(f"ml_{side}"))
    key_us = sd.team_key_out(inj, tid, us, lg)
    key_any = key_us or sd.team_key_out(inj, oid, them, lg)
    if key_us:
        pos, nm = key_us[0][1], key_us[0][0]
        import sports_vocab
        mv = " " + sports_vocab.one(["[The line already moved for it|The line's already moved on it|The number already "
                                     "adjusted|Vegas already moved the line] ({o} → {n})."], f"{v.seed}|mv", o=_am(op), n=_am(now)) \
            if op is not None and now is not None and op != now else ""
        pts = leg.get("line") if leg.get("market") == "spread" else None
        need = " " + sports_vocab.one([
            "{T} [gotta|have to|need to] win by {n1}+ to [beat us|cover|beat this ticket]. [Win by {n0}, win by 1, or lose "
            "— we cash.|Anything short of {a1} {n1}-point win and we cash.|They win by {n0} or less, or lose — we still cash.]"],
            f"{v.seed}|need", T=_cap(the_them), n0=int(pts), n1=int(pts) + 1, a1=_a(int(pts) + 1)) if pts and pts > 0 and pts != int(pts) else ""
        out.append(_say(v, "keyout_us", must=True, nm=nm, pos=pos, the_us=the_us, mv=mv, need=need))
    if not key_any and op is not None and now is not None and op != now and sd.implied(now) > sd.implied(op):
        out.append(_say(v, "sharp", us=us, op=_am(op), now=_am(now)))

    # sharp money going the other way and we still like our side: say it our way, with a quick reason
    op_o, now_o = sm._int(g.get(f"ml_{other}_open")), sm._int(g.get(f"ml_{other}"))
    if not key_any and op is not None and now is not None and sm.logit(sd.implied(op)) - sm.logit(sd.implied(now)) >= 0.08:
        move = f" ({_am(op_o)} → {_am(now_o)})" if op_o is not None and now_o is not None else ""
        why, r = _why(leg, said, us, them, f"{v.seed}|why")
        said.add(r)
        out.append(_nowhy(_say(v, "fade", The_them=_cap(the_them), the_them=the_them, move=move, the_us=the_us,
                               why=why)))

    # who's betting who: the real splits (the same numbers Google shows)
    sp_ = public_split(leg)
    if sp_:
        t, m = sp_
        mk = {"ml": "the moneyline", "spread": "the spread", "total": "the total"}[leg["market"]]
        kind = "splits_fade" if t <= 35 else "splits_ride" if t >= 65 else "splits_even"
        rnd_ = __import__("random").Random(f"{v.seed}|split")     # the stat itself, worded per card ("72% of the tickets")
        bets = lambda x: f"{x}% " + rnd_.choice(["of the bets", "of the tickets", "of bets", "of tickets", "of the action"])
        cash = lambda x: f"{x}% " + rnd_.choice(["of the money", "of the cash", "of the handle", "of the dollars"])
        out.append(_say(v, "splits", tkey=kind, must=True, t=t, m=m, pt=100 - t, pm=100 - m, mk=mk, tb=bets(t),
                        mc=cash(m), ptb=bets(100 - t), pmc=cash(100 - m),
                        the_us=the_us, the_them=the_them, The_us=_cap(the_us), The_them=_cap(the_them)))

    # the public: fading them or riding with them
    pub = public_side(leg, g)
    why_pub = _why(leg, said, us, them, f"{v.seed}|whyp")[0]
    if sp_:
        pass                                          # the real splits already said it (with the numbers)
    elif pub == "fade":
        out.append(_nowhy(_say(v, "pub_fade", The_them=_cap(the_them), the_them=the_them, the_us=the_us, why=why_pub)))
    elif pub == "ride":
        out.append(_nowhy(_say(v, "pub_ride", the_us=the_us, why=why_pub)))

    # bottom line
    need, have = 1 / leg["dec"], leg["p"]
    bet = f"{us} {leg['line']:+g}" if leg["market"] == "spread" else us
    price = f"{bet} ({_am(leg['odds'])})"
    if _odds_words(need) != _odds_words(have):
        out.append(_say(v, "bottom", must=True, price=price, need=_odds_words(need), have=_odds_words(have)))
    else:
        import sports                                     # a LOCK never hedges (the owner: if we call it a lock, we're
        lock = leg.get("tier") == "lock" or sports.lock_ok(leg)   # confident; a lean's bottom line gets rewritten anyway)
        if lock:
            out.append(_say(v, "bottom_ls", must=True, price=price, need=_odds_words(need)))
        else:
            out.append(_say(v, "bottom_s", must=True, price=price, need=_odds_words(need)))
    lines = [x for x in out if x]
    if len(lines) > 2:
        import random
        rnd = random.Random(f"{g['id']}|{start:%Y-%m-%d}|{side}|shape")
        body, bottom = lines[:-1], lines[-1]
        keep = max(4, len(body) - rnd.randint(0, 2))          # not every pick gets every line
        must = {i for i, x in enumerate(body) if x[:1] in "🤡🤝💸🚑" or x.startswith("🗑️")}   # the spicy stuff stays
        drop = [i for i in range(len(body)) if i not in must]
        rnd.shuffle(drop)
        gone = set(drop[:max(0, len(body) - keep)])
        body = [x for i, x in enumerate(body) if i not in gone]
        rnd.shuffle(body)
        lines = body + [bottom]
    return lines


WHY = {   # the pick's reasons, said as a quick "because" (each one several ways)
    "the stronger team": "[they're the better team|they're just better|they got more talent|they're the stronger side]",
    "hotter recent form": "[they're the hotter team|they're rolling|they've been playing better|their form's better]",
    "better rested": "[they got extra days of rest|they're fresher|they had more rest|their legs are fresher]",
    "opponent on a back-to-back": "[{them} are on tired legs|{them} played last night|{them} are on a back-to-back]",
    "opponent missing key players": "[{them} are banged up|{them} are missing bodies|{them} are short-handed]",
    "revenge game": "[they owe these guys one|it's a get-back game|they want this one back]",
    "altitude edge": "[{them} gonna be sucking wind up there|the thin air gets to {them}|{them} ain't built for altitude]",
    "opponent's body clock is off": "[{them} are playing on jet lag|{them} are jet-lagged|{them} are on the wrong clock]",
    "cold-weather edge": "[{them} aren't built for the cold|{them} hate the cold|the cold hits {them} harder]",
    "nasty weather helps us": "[sloppy weather keeps it close|the slop evens it out|bad weather keeps it tight]",
    "rolling off a blowout win": "[they're rolling off a blowout|they just blew somebody out|they're coming off a blowout]",
    "letdown spot for the opponent": "[{them} are due for a letdown|{them} are in a trap spot|{them} could come out flat]",
    "coming off a bye": "[they're fresh off a bye|they had the bye to prep|they're rested off a bye]",
    "opponent on a short week": "[{them} are on a short week|{them} had a short week|{them} are on a quick turnaround]",
    "better starting pitcher": "[we've got the better arm on the mound|our starter's better|we got the better arm]",
    "better QB play lately": "[our QB's been playing better|our QB's been sharper|we got the hotter QB]",
    "hotter goalie": "[our goalie's been hotter|our goalie's been sharper|we got the hotter goalie]",
}


def _why(leg, said, us, them, seed):
    """(the next reason not said yet as a quick "because" - worded fresh per game -, that reason) or (NO_WHY, None)."""
    import sports_vocab
    r = next((r for r in leg.get("reasons") or [] if r in WHY and r not in said), None)
    if r is None:
        return NO_WHY, None
    x = sports_vocab.one([WHY[r]], seed, us=us, them=them)
    return (x[:1].lower() + x[1:] if WHY[r][1:2].islower() else x), r


NO_WHY = "\u00a7"     # placeholder: no fresh reason left, so the line ends on our side instead of a filler "because"


def _nowhy(line):
    import re
    return re.sub(r"[\s\u2014:.,]*\u00a7\.?$", ".", line) if NO_WHY in line else line


def _cap(x):
    return x[:1].upper() + x[1:]


def _mi(n):
    return f"{int(round(n or 0, -1)):,}"


def _nth(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def context_lines(leg, v, us, them, the_us, the_them, g):
    """Breakdown lines for the context study's facts (rivalry, travel, domes, stakes, refs) and pregame talk.
    Proven or not, these are just what's around the game - the numbers only move for PROVEN factors."""
    out = []
    total = leg.get("market") == "total"
    names = dict(the_us=the_us, the_them=the_them, The_us=_cap(the_us), The_them=_cap(the_them))
    for c in leg.get("ctx") or []:
        k = c.get("k")
        if k == "rival":
            out.append(_say(v, "cx_rival", tkey="cx_rival_t", them=them) if total else _say(v, "cx_rival", **names))
        elif k == "div":
            out.append(_say(v, "cx_div", tkey="cx_div_t", them=them) if total else _say(v, "cx_div", **names))
        elif k == "trip":
            mi, r6, d = c.get("mi") or 0, c.get("road6") or 0, c.get("dir")
            bits = []
            if mi >= 1000:
                bits.append(f"{_mi(mi)}-mile trip{' east' if d == 'E' else ' west' if d == 'W' else ''}")
            if r6 >= 3 and leg.get("league") in ("nba", "nhl", "ncaab"):   # (a baseball series always is)
                bits.append(f"{_nth(r6)} road game in 6 days")
            if not bits:
                continue
            fact = ", ".join(bits)
            out.append(_say(v, "cx_trip", fact=fact, Fact=fact.capitalize(), **names))
        elif k == "dome_cold":
            temp, wind = g.get("wx_temp", ""), g.get("wx_wind", "")
            wx = (f"{temp}°" if str(temp) != "" else "cold") + (f" with {wind} mph wind" if str(wind) not in ("", "0")
                                                                and float(wind or 0) >= 15 else "")
            who = the_them if not total else ("the home dome team" if c.get("who") == "home" else "the road dome team")
            out.append(_say(v, "cx_domecold", wx=wx, Wx=_cap(wx), who=who, Who=_cap(who)))
        elif k == "dome_out":
            out.append(_say(v, "cx_domeout", **names))
        elif k == "mustwin":
            out.append(_say(v, "cx_mustwin", rec=c.get("rec"), **names))
        elif k == "rest":
            out.append(_say(v, "cx_rest", **names))
        elif k == "tank":
            out.append(_say(v, "cx_tank", rec=c.get("rec"), **names))
        elif k == "elim":
            out.append(_say(v, "cx_elim", **names))
        elif k == "bowl5":
            out.append(_say(v, "cx_bowl", us=us))
        elif k == "hotseat":
            out.append(_say(v, "cx_hotseat", cnt=c.get("n") or 0, the_them_s=_pos(the_them), **names))
        elif k in ("ref_side", "ref_total"):
            nm = (c.get("names") or ["the crew"])[0]
            lean = c.get("lean")
            what = {"home": "the home team", "road": "the road team", "over": "the over", "under": "the under"}.get(lean, lean)
            out.append(_say(v, "cx_ref", nm=nm, Nm=_cap(nm), nm_s=_pos(nm), what=what))
    for key, who in (("talk_theirs", the_them), ("talk_ours", the_us)):
        for t in (leg.get(key) or [])[:1]:
            tk = "talk_" + str(t.get("kind")).replace(" ", "_").replace("-", "_")
            if tk in T and not total:
                out.append(_say(v, tk, who=who, Who=_cap(who), who_s=_pos(who), Who_s=_cap(_pos(who))))
    return [x for x in out if x]


def public_split(leg):
    """(our % of the bets, our % of the money) on this leg's market, from the real public splits, or None."""
    import sports_public
    s = sports_public.splits_for(leg["game_id"])
    mk = {"ml": "ml", "spread": "sp", "total": "tot"}.get(leg["market"])
    if not s or not mk:
        return None
    t, m = s.get(f"{mk}_{leg['side']}_t"), s.get(f"{mk}_{leg['side']}_m")
    return (t, m) if t is not None else None


def public_side(leg, g):
    """'fade' when the public is on the other side, 'ride' when it's with us - from the real splits (% of bets) when
    we have them; otherwise the favorite stands in for the public on moneylines."""
    sp_ = public_split(leg)
    if sp_:
        return "fade" if sp_[0] <= 35 else "ride" if sp_[0] >= 65 else None
    if leg["market"] != "ml":
        return None
    other = "away" if leg["side"] == "home" else "home"
    ours, theirs = sm._int(g.get(f"ml_{leg['side']}")), sm._int(g.get(f"ml_{other}"))
    if ours is None or theirs is None:
        return None
    if ours >= 105 and theirs <= -125:
        return "fade"
    if ours <= -125:
        return "ride"
    return None


def _odds_words(p):
    """0.5 -> 'a coin flip', 0.62 -> 'about 6 in 10', 0.3 -> 'about 3 in 10'."""
    if abs(p - 0.5) < 0.03:
        return "a coin flip"
    n = round(p * 10)
    if n <= 1:
        return f"about 1 in {round(1 / p)}"
    return f"about {n} in 10"


# ─── THE PHRASEBOOK ──────────────────────────────────────────────────────────────────────────────────────────────────
# Every breakdown line is a handful of sentence skeletons with slots ({us}, {rec}... = the facts, passed in) and inline
# picks ([a|b|c]; [a|] = maybe). sports_vocab.variants() rolls them out per game and day, Voice.say keeps a roll that
# repeats no 4-word run from the board or from yesterday. Facts never change - only the wording around them.
# The owner: variety never makes a line longer - every roll stays within today's size for that line (_CAP) and never
# has more sentences. Never "real talk", never "chalk".

_P = {   # breakdown-only word pools (one flat [..] each - never nested inside another pick)
    "rn": "[right now|lately|these days|this stretch|of late|at the moment]",
    "yr": "[on the year|on the season|this season|so far|overall|on the campaign]",
    "str8": "[straight|in a row]",
    "Ls": "[L's|losses]",
    "tn": "[tonight|today|this time|in this one]",
    "cash_w": "[of the money|of the cash|of the handle|of the dollars]",
    "ofl": "[{w} of the last {cnt}|{w} of their last {cnt}|{w} out of the last {cnt}|{w} of the past {cnt}|{w} of {cnt} lately|{w} of the {cnt} most recent|{w} in {cnt} tries]",
    "opnow": "[{op} → {now}|{op} to {now}|from {op} to {now}|{op}, now {now}]",
    "bk": "[Vegas|the book|the sportsbook|the oddsmaker|the house|the market]",
    "Bk": "[Vegas|The book|The sportsbook|The oddsmaker|The house|The market]",
    "close": "[That's the value.|That's the play.|That gap is the play.|Trust the algorithm.|Easy call.|Value all day.|"
             "We'll take that all day.|That's the edge.|Math is math.|Tail it.|We ride.|Book it.|Let's eat.|Nice nice.|"
             "Say less.|Light work.|Cook.|Numbers don't lie.|That's where the money's at.|Levels to this.|]",
    "sclose": "[We gon' see.|We finna see.|Tap in.|I won't let y'all down.|Right side, that's all.|Quiet play.|"
              "Stay disciplined.|We'll see.|Small bet energy.|Let it ride.|]",
}


def _x(t):
    """Drop the pools into a template ({rn} -> [right now|lately|...])."""
    return re.sub(r"\{(\w+)\}", lambda m: _P.get(m.group(1), m.group(0)), t)


# today's size of each line (before the phrasebook): (characters outside the facts - each fact counts 6 -, sentences)
_CAP = {"hot": (64, 1), "rec": (82, 2), "cold": (55, 2), "better": (54, 1), "better_s": (65, 1), "worse": (92, 3),
        "even": (83, 2), "trash": (81, 2), "latest": (36, 1), "h2h": (78, 1), "h2h1": (51, 1),
        "QB_cold": (58, 1), "SP_cold": (44, 1), "G_cold": (51, 1), "QB_hot": (35, 1), "SP_hot": (43, 1),
        "G_hot": (41, 1), "revenge": (73, 2), "letdown": (81, 2), "momentum": (63, 2), "alt": (80, 2),
        "cold_w": (78, 2), "wx": (78, 2), "jetlag": (75, 2), "drama_coach_fired": (56, 2),
        "drama_suspension": (53, 2), "drama_legal_trouble": (60, 2), "drama_family_personal": (55, 2),
        "drama_illness": (40, 1), "drama_trade_drama": (52, 2), "bye": (65, 2), "short": (58, 2), "intl": (116, 2),
        "home": (70, 2), "road": (65, 2), "b2b": (57, 2), "rest": (53, 1), "bump": (58, 1), "keyout": (60, 1),
        "banged": (45, 1), "healthy": (48, 1), "keyout_us": (143, 3), "sharp": (68, 2), "fade": (103, 2),
        "splits_fade": (180, 3), "splits_ride": (180, 3), "splits_even": (180, 3), "pub_fade": (106, 2),
        "pub_ride": (81, 2), "bottom": (115, 3), "bottom_s": (126, 3), "bottom_ls": (126, 3), "lean": (94, 2),
        "cx_rival": (64, 2), "cx_rival_t": (64, 2), "cx_div": (65, 2), "cx_div_t": (65, 2), "cx_trip": (55, 2),
        "cx_domecold": (77, 2), "cx_domeout": (65, 1), "cx_mustwin": (74, 3), "cx_rest": (71, 2),
        "cx_tank": (69, 2), "cx_elim": (68, 2), "cx_bowl": (60, 2), "cx_hotseat": (69, 2), "cx_ref": (86, 2),
        "talk_contract_year": (68, 2), "talk_unhappy": (78, 2), "talk_trash_talk": (67, 2),
        "talk_must_win": (68, 2), "talk_rivalry_week": (60, 2), "talk_hot_seat": (69, 2)}

_TOK = re.compile("[-]")


def _size(line):
    """(characters outside the facts, sentences) of a rolled line whose facts are still tokens."""
    m = _TOK.sub("\x01" * 6, line)
    n = len(re.findall(r"[.!?]+(?=\s|$|\x01)", m)) + (0 if re.search(r"[.!?]\W*$", m) else 1)
    return len(m), n


def _roll(key, seed, words=None, tkey=None, keep=60, **facts):
    """This line rolled out many ways (up to 60), the facts dropped in untouched, every roll within today's size."""
    import sports_vocab
    tok = {k: f"{chr(0xe100 + i)}" for i, k in enumerate(facts)}
    lim = _CAP.get(tkey or key)
    out = []
    for r in sports_vocab.variants(T[tkey or key], f"{seed}|{key}", n=keep * 4, **tok, **(words or {})):
        if lim:
            c, s = _size(r)
            if c > lim[0] or s > lim[1]:
                continue
        for k, t in tok.items():
            r = r.replace(t, str(facts[k]))
        out.append(r)
        if len(out) >= keep:
            break
    return out


def _say(v, key, must=False, words=None, tkey=None, extra=(), names=(), **facts):
    """Roll the line and let the Voice pick the wording nobody's used yet (facts count as names: no run is 'new'
    just because the numbers or teams changed)."""
    nm = sorted({str(x) for x in facts.values() if len(str(x)) >= 3 and re.search("[A-Za-z]", str(x))} | set(names),
                key=len, reverse=True)
    rolls = _roll(key, v.seed, words, tkey, keep=240 if must else 60, **facts)
    return v.say(tkey or key, list(extra) + rolls, must=must, names=tuple(nm))


def _a(x):
    """'a' / 'an' before a number: an 8-game, an 11-5, an 18-game."""
    s = str(x)
    return "an" if s[:1] == "8" or s[:2] in ("11", "18") and (len(s) == 2 or not s[2:3].isdigit()) else "a"


def _pos(x):
    """Bears -> Bears', Alabama -> Alabama's."""
    return x + ("'" if x.endswith("s") else "'s")


T = {
    "hot": [
        "🔥 {us} are {rec} and on {a_n} {cnt}-game [heater|win streak|run|tear].",
        "🔥 {us} ({rec}) have [won|taken|stacked] {cnt} {str8} and they're {hot}.",
        "🔥 {cnt} {str8} for {us} — {rec} {yr} and [still climbing|not slowing down|rolling|still going].",
        "🔥 {us} can't [stop winning|lose right now|lose lately|miss]: {cnt} {str8}, {rec} {yr}.",
        "🔥 Winners of {cnt} {str8}, {us} [roll in|show up|walk in|come in|pull up] at {rec}.",
        "🔥 [Heat check|Form check|Streak check|Hot streak]: {us} have [won|taken] {cnt} {str8} ({rec}).",
        "🔥 {us} [got|have] {cnt} [straight W's|wins in a row|dubs in a row|straight wins], {rec} {yr}.",
        "🔥 {rec} {yr} and {cnt} {str8} — {us} are {hot}.",
        "🔥 {us} keep [stacking|piling up|racking up|collecting] [W's|wins|dubs]: {cnt} {str8}, {rec} {yr}.",
        "🔥 Nobody's [cooled off|slowed down] {us} [yet|lately|so far] — {cnt} {str8}, {rec}.",
        "🔥 {us} ({rec}) are riding {a_n} {cnt}-game [streak|heater|wave|run].",
        "🔥 [Hottest|Hot|Rolling] team in the [building|matchup]: {us}, {cnt} {str8} and {rec}.",
    ],
    "rec": [
        "📋 {us} [sitting at|rolling in at|walking in at|come in at] {rec} {yr}. [Tonight's the only one that counts though.|Only this one matters now.|Clean slate tonight.|Tonight's what counts.]",
        "📋 [Record check|Quick check|Resume check]: {us} {rec}. [We already did our homework.|The homework's done.|We did the digging already.|We know the rest.]",
        "📋 {rec} {yr} for {us} — the record [don't|doesn't] [cash tickets|pay us|win bets], the number does.",
        "📋 {us} got {a_rec} {rec} record [walking in|coming in|on the board]. [We gon' see what they do with it.|Now go prove it.|Let's see what it's worth.]",
        "📋 {us} are {rec} {rn} — the rest [is|gets decided|gets settled] on the {field}.",
        "📋 {rec} {yr} for {us}. [Nice resume|Solid|Fine], but [tonight|this game|this one] is what [counts|matters|pays].",
        "📋 [Where they stand|The resume|Standing|The record]: {us} at {rec} {yr}.",
        "📋 {us} [sit at|stand at|check in at] {rec}. [Records don't cash tickets|The record's just background|The record ain't the bet] — the [price|number] is.",
        "📋 [Resume|Track record|Report card] for {us}: {rec} {yr}. [Now the real part.|The {field} settles the rest.|Numbers did the rest.]",
        "📋 {us} [bring|carry] {a_rec} {rec} mark [in|into this one|into tonight]. [We know what we're doing.|Homework's done.|We read it all.]",
    ],
    "cold": [
        "🧊 {them} are {rec} and {cold} — {cnt} straight {Ls}.",
        "🧊 {them} have [dropped|lost] {cnt} {str8} ({rec}). [Not a good look.|Ugly.|Yikes.|]",
        "🧊 {cnt} straight {Ls} for {them} ({rec}). [Not a good look.|Ugly.|Rough stretch.|Yikes.|Woof.]",
        "🧊 {them} ({rec}) keep [taking|eating|stacking|piling up] {Ls} — {cnt} {str8}.",
        "🧊 {them} ({rec}) [are in a slump|can't buy a win|are skidding|are sliding] — {cnt} {str8}.",
        "🧊 {them} [forgot how to win|lost the recipe|can't close]: {cnt} {str8}, {rec}.",
        "🧊 Losers of {cnt} {str8}, {them} [sit|limp in|show up|stumble in] at {rec}.",
        "🧊 [Skid|Slide|Slump] [watch|check|alert]: {them} have [lost|dropped] {cnt} {str8} ({rec}).",
        "🧊 {them} can't [find|get|buy] a W — {cnt} {str8}, {rec}.",
        "🧊 {them} are {cold} — {cnt} {str8}, {rec} {yr}.",
    ],
    "better": [
        "💪 {us} are [straight up|flat out|just|simply] the better [team|squad] {rn}.",
        "💪 This is a mismatch — {us} are [just|simply|flat out|clearly] better.",
        "💪 {us} are [the better squad|a tier above|levels above|a class above] and it's not [close|that close].",
        "💪 On talent, {us} have the edge [all day|easy|by a mile|big time].",
        "💪 {us} got more dog in them than {them} {rn}.",
        "💪 Talent gap goes {us_s} way — [big time|by a lot|not close|and it's wide].",
        "💪 {us} [outclass|are a tier above|are levels above|are a class above] {them} {rn}.",
        "💪 [Straight up|Flat out|Plain and simple], {us} are the [better|stronger|deeper] [team|squad].",
        "💪 {them} [can't hang with|aren't on the level of|can't match] {us} {rn}.",
        "💪 Levels to this — {us} are [just|simply|clearly] [better|the better team].",
        "💪 [Better roster|More talent|Deeper roster], [better results|more juice|more wins]: that's {us}.",
        "💪 [Mismatch|Talent gap|No contest] on paper: {us} [by a lot|easy|clearly|by a mile].",
    ],
    "better_s": [
        "💪 {us} are the better [squad|team|side], even if it's closer than it [looks|seems].",
        "💪 {us} have the edge on paper — not a [blowout|landslide], but it's there.",
        "💪 [Slight|Small|Modest|Little] edge {us} on who's [actually|really|truly] better.",
        "💪 {us} have a [little|touch|bit] more juice than {them}.",
        "💪 Close-ish on paper, but {us} are [better|the better side|a notch up|a step ahead].",
        "💪 {us} got the upper hand, not by a mile but it's there.",
        "💪 {us} are [a notch|a step|a hair|a tick] better than {them} {rn}.",
        "💪 [Not a mismatch|No blowout on paper|Not by much], but {us} are the [better|stronger] [side|team].",
        "💪 Edge {us}, [slim but real|small but there|thin but there] on [talent|paper].",
        "💪 {them} keep it close on paper; {us} [still grade out better|are still a notch up|still rate higher].",
    ],
    "worse": [
        "🐺 {them} look better on paper — that's [exactly|precisely] why [we're getting|we get] this [juicy|fat|sweet] price on {us}.",
        "🐺 Everybody's on {them}. That's how we get {us} at this [number|price].",
        "🐺 {them} are the name brand here, but the price on {us} is too [good|sweet] to pass.",
        "🐺 On paper it's {them}. On the {field}? We like {us} at this [price|number].",
        "🐺 {them} get all the [love|hype|respect] — that's why {us} are sitting at this [number|price].",
        "🐺 [Paper|The resume] says {them}. [The price|This number] says {us}, and we [listen to|follow|trust] the price.",
        "🐺 [Sure|Yeah|Fine], {them} are better on paper. [That's baked in|That's in the price|Priced in] — the value's on {us}.",
        "🐺 We know {them} got more talent. That's why {us} come [this cheap|at a discount|at this price].",
        "🐺 [Price spot|Value spot]: {them} [have|got] the [names|resume|hype], we [have|got] the [number|price] on {us}.",
        "🐺 {them} [are favored|get the respect] for a reason. [Still,|But] {us} at this [price|number] is [value|the play].",
    ],
    "even": [
        "⚖️ On paper these two [close as hell|neck and neck|dead even|about even] — so we [taking|take] the number that pays.",
        "⚖️ Talent's about even. When it's this tight, the [number|price] makes the play.",
        "⚖️ Coin-flip matchup on paper — and the line makers [trippin'|sleeping|off] on the price.",
        "⚖️ Dead even on paper. We ain't guessing who's better, we taking the better [number|price].",
        "⚖️ Nobody's clearly better here — so we let the [number|price] do the talking.",
        "⚖️ [Even|Level|Pick'em] [matchup|fight|game] on paper. [The price|The number] is where [our edge|the value] lives.",
        "⚖️ [Can't split these two|Hard to split these two|These two are twins] on talent. [The number|The price] [breaks the tie|decides it].",
        "⚖️ [Talent-wise|On paper] it's a wash — [so|and] {bk} [gave|handed] us the [better|right] side of it.",
        "⚖️ [Evenly matched|Even squads|Two even teams]. [We're|We] here for the [price|number], not the names.",
        "⚖️ [Neither|No] team [stands out|separates] on paper. {Algo} [likes|prefers] the number on our side.",
    ],
    "trash": [
        "🗑️ {them} have been complete ass {rn} — {rec} and it ain't getting [prettier|better].",
        "🗑️ Straight up, {them} are [trash|a mess|bad|rough] {rn} ({rec}).",
        "🗑️ {them} can't get out of their own way ({rec}).",
        "🗑️ {them} are a [mess|wreck|disaster] {rn}. {rec} says it all.",
        "🗑️ Nothing about {them} [scares us|worries us] ({rec}).",
        "🗑️ {them} been looking like a [JV squad|practice squad|scrimmage team] ({rec}).",
        "🗑️ Watching {them} {rn} hurts ({rec}).",
        "🗑️ {them} are about to get their cheeks clapped. {rec} — they been [complete ass|awful|bad].",
        "🗑️ {rec} {rn}. {them} are complete ass and it [shows|ain't close].",
        "🗑️ {them} [stink|are rough|are ugly] {rn} — {rec} [don't lie|tells you everything|says enough].",
        "🗑️ [No offense|Respectfully], {them} are [bad|a mess|a disaster] ({rec}).",
        "🗑️ {them} at {rec}? [Nah|Yeah no], [we're not scared|nothing to fear|we good].",
        "🗑️ [Basement|Bottom-feeder] energy from {them}: {rec} {rn}.",
    ],
    "latest": [
        "📅 [Latest|Last time out|Most recent|Last outing|Previous game|Fresh off|Last game|Coming off|Last results|Last go-round|Last time|Recent form]: {both}.",
        "📅 [The last one|Last one|Freshest results|Newest results|Latest scores|Last box scores|How they got here|Last time on the {field}]: {both}.",
        "📅 [Most recent games|Where they're coming from|Last week's tape|Last tape|Previous results|The latest|Their last ones|Last run out]: {both}.",
        "📅 [Last|Recent] [tape|results|scores|box scores]: {both}.",
    ],
    "h2h": [
        "🆚 {us} [own|run] this [matchup|series] — [won|took] {ofl}.",
        "🆚 {us} have had {them_s} number: {ofl}.",
        "🆚 History's on our side — {ofl} went {us_s} way.",
        "🆚 {us} been [owning|handling|bullying] {them} lately — {ofl}.",
        "🆚 {them} can't figure {us} out: {ofl}.",
        "🆚 [Head to head|Series history|Recent meetings]: {us} [took|won] {ofl}.",
        "🆚 {ofl} [meetings|matchups|go-rounds] [went to|belonged to] {us}.",
        "🆚 {us} [know how to beat|have the book on|have a feel for] {them} — {ofl}.",
        "🆚 [When these two meet|In this matchup], {us} [usually|tend to] [win|come out on top]: {ofl}.",
        "🆚 {them} [keep losing to|struggle with|can't solve] {us} — {ofl}.",
    ],
    "h2h1": [
        "🆚 {us} got 'em [last time|the last go]: {res}.",
        "🆚 Last [meeting|matchup] went {us_s} way ({res}).",
        "🆚 {us} [handled|beat|got] {them} last time ({res}).",
        "🆚 Last time these two met, {us} [took it|won|got it] ({res}).",
        "🆚 [Previous|Last] [meeting|matchup|go-round]: {us} [won|took it] ({res}).",
        "🆚 {us} [took down|got past|got by] {them} last time ({res}).",
        "🆚 [Most recent|The last] [meeting|matchup] [belonged to|went to] {us} ({res}).",
    ],
    "QB_cold": [
        "🗑️ {name} has been complete booty cheeks — {txt}.",
        "🗑️ {name} has been throwing it to the other team — {txt}.",
        "🗑️ {name} looks [lost|confused|shook] out there: {txt}.",
        "🗑️ {name} [can't|hasn't been able to] find [the open man|a receiver|anybody] — {txt}.",
        "🗑️ {name} has been [a mess|rough|shaky|ugly|a liability] {rn}: {txt}.",
        "🗑️ {name} [keeps|been] [missing throws|turning it over|missing reads]: {txt}.",
        "🗑️ [Bad|Rough|Ugly] [stretch|run|patch] for {name} — {txt}.",
        "🗑️ {name} under center? [A problem|A liability|A gift] — {txt}.",
        "🗑️ [Yikes|Oof], {name} {rn}: {txt}.",
    ],
    "SP_cold": [
        "💣 {name} has been getting [shelled|lit up|tagged|rocked] — {txt}.",
        "💣 {name} has been [getting lit up|hittable|a piñata]: {txt}.",
        "💣 Hitters [are teeing off|feast|are feasting] on {name} — {txt}.",
        "💣 {name} keeps getting [tagged|rocked|hit hard]: {txt}.",
        "💣 Bats [love|feast on|tee off on|light up] {name}: {txt}.",
        "💣 [Rough|Ugly|Bad] [run|stretch|patch] for {name}: {txt}.",
        "💣 {name} can't [miss bats|get outs|keep it in the park]: {txt}.",
        "💣 {name} [lately|of late]? [Batting practice|Rough|Ugly]: {txt}.",
    ],
    "G_cold": [
        "🥅 {name} has been leaky as hell — {txt}.",
        "🥅 {name} can't stop a beach ball {rn}: {txt}.",
        "🥅 Pucks keep [getting past|beating|sneaking by] {name} — {txt}.",
        "🥅 {name} has been [a sieve|shaky|leaky|a turnstile] {rn}: {txt}.",
        "🥅 [Rough|Ugly|Bad] [run|stretch] in net for {name}: {txt}.",
        "🥅 {name} [can't find|lost] the puck {rn} — {txt}.",
        "🥅 Shooters [love|feast on|are lighting up] {name}: {txt}.",
    ],
    "QB_hot": [
        "🎯 {name} has been [cooking|dealing|sharp] — {txt}.",
        "🎯 {name} is [locked in|dialed in|on fire|rolling]: {txt}.",
        "🎯 {name} is [slinging it|cooking|dealing] — {txt}.",
        "🎯 {name} [been|is] [dicing|carving] [defenses|'em up]: {txt}.",
        "🎯 [Hot|Sharp|Clean|Big] [stretch|run] for {name}: {txt}.",
        "🎯 {name} [can't miss|is dialed]: {txt}.",
        "🎯 {name} [is|has been] [dealing|sharp|rolling|money]: {txt}.",
    ],
    "SP_hot": [
        "🔥 {name} has been [dealing|nasty|filthy|sharp] — {txt}.",
        "🔥 {name} is [on a roll|dealing|locked in]: {txt}.",
        "🔥 Nobody's [touching|hitting|solving] {name} lately — {txt}.",
        "🔥 {name} [is|has been] [dealing|nasty|filthy|dialed in|sharp|lights out]: {txt}.",
        "🔥 Hitters [can't touch|can't solve|are lost against] {name}: {txt}.",
        "🔥 [Nasty|Filthy|Sharp|Big] [stretch|run] for {name}: {txt}.",
    ],
    "G_hot": [
        "🧱 {name} has been a [brick wall|wall|brick] — {txt}.",
        "🧱 {name} is standing on his head: {txt}.",
        "🧱 Good luck [scoring on|beating] {name} — {txt}.",
        "🧱 {name} [is|has been] [locked in|a wall|dialed in|lights out]: {txt}.",
        "🧱 [Nothing's|Nothing is] getting past {name}: {txt}.",
        "🧱 [Hot|Sharp|Big] [stretch|run] in net for {name}: {txt}.",
    ],
    "revenge": [
        "😤 [Revenge|Payback|Get-back] game — {us} lost the last meeting and they haven't forgotten.",
        "😤 {us} owe {them} one from last time. [Payback's coming.|Time to collect.|Get-back time.]",
        "😤 Get-back game for {us}. They took an L to {them} [last time|in the last one].",
        "😤 {us} been [waiting on|itching for] this rematch.",
        "😤 {them} got {us} last time. [That stuck with them.|That one stung.|They remember.]",
        "😤 [Payback|Rematch|Get-back] [spot|game|time]: {us} dropped the last one to {them}.",
        "😤 {us} [lost the last meeting|took an L last time] — [they want this one back|this one's personal|they remember].",
        "😤 [Bad memories|Unfinished business|Sour taste] for {us} — {them} [won|took] the last meeting.",
        "😤 {us} [circled|marked] this one after losing to {them} last time.",
    ],
    "letdown": [
        "🪤 [Letdown|Trap|Flat] spot for {them} — fresh off a blowout win, they're gonna come out flat.",
        "🪤 {them} just blew somebody out. [Classic letdown game.|Letdown alert.|Trap spot.]",
        "🪤 {them} are riding high off a big W. That's when teams [slip|sleepwalk|get caught].",
        "🪤 Trap game for {them} after that [blowout|beatdown|big win].",
        "🪤 {them} [are|come in] [feeling themselves|a little too comfy|full of themselves] after a blowout. [Flat spot.|Letdown alert.|Trap spot.]",
        "🪤 Blowout win last time for {them}. [Hard to keep that energy.|The hangover's real.|Easy to come out flat.]",
        "🪤 [After|Coming off] a blowout, {them} [could|might|tend to] [sleepwalk|come out flat|ease off] here.",
        "🪤 [Letdown|Hangover|Flat] spot: {them} just [blew out|ran over|smacked] their last opponent.",
    ],
    "momentum": [
        "🚀 {us} just blew somebody out — teams like that keep [rolling|going].",
        "🚀 {us} are coming in hot off a blowout. [Momentum's real.|Confidence is up.]",
        "🚀 Blowout last time out for {us}. They're [feeling themselves|rolling|confident].",
        "🚀 {us} [ran|rolled] somebody off the {field} last time. [Keep it going.|Carry it over.|Ride it.]",
        "🚀 [Momentum|Confidence] [is|stays] [high|up] for {us} after a blowout.",
        "🚀 [Last time out|Last game], {us} [won big|won going away|blew somebody out]. [Confidence is up.|They're rolling.]",
        "🚀 {us} [smoked|ran over|blew out] their last opponent. [Momentum's on our side.|That carries.]",
    ],
    "alt": [
        "🏔️ Thin air — {elev} meters up. {The_them} gonna be sucking wind by the [second half|end].",
        "🏔️ Altitude game. {The_them} ain't used to [breathing|playing] up there.",
        "🏔️ Mile-high problems for {the_them}. Legs get [heavy|tired] fast at that [elevation|height].",
        "🏔️ {elev} meters [up|above sea level]. {The_them} [will|gonna] feel it [late|in the legs].",
        "🏔️ Thin air at {elev} meters — [lungs burn|legs go|gas tanks drain] fast for {the_them}.",
        "🏔️ {The_them} [visiting|playing] at {elev} meters. [Oxygen's|Air's] [thin|scarce] up there.",
        "🏔️ [Altitude|Elevation] check: {elev} meters. {The_them} ain't [built|ready] for it.",
    ],
    "cold_w": [
        "🥶 {temp}°F at kickoff. {The_them} are a warm-weather [squad|team] walking into a freezer.",
        "🥶 It's gonna be {temp}°F. {The_them} don't play in this — {the_us} do.",
        "🥶 Cold one ({temp}°F). Welcome to real weather, {the_them}.",
        "🥶 {temp}°F [tonight|out there|at kickoff]. {The_them} [ain't used to this|are a warm-weather team].",
        "🥶 [Freezer|Ice box|Cold] game: {temp}°F. {The_them} [won't like it|are out of their element].",
        "🥶 [Bundle up|Gloves on], {the_them} — {temp}°F [at kickoff|out there].",
        "🥶 {The_them} [come from|live in] the warm. [Tonight|Kickoff] is {temp}°F.",
    ],
    "wx": [
        "🌧️ {what} in the forecast. Sloppy game, fewer big plays — that's how dogs eat.",
        "🌬️ {what}. Ugly weather drags everybody down to the same level.",
        "🌧️ Weather's nasty ({what}). Anything can happen in the slop.",
        "🌧️ [Forecast|Weather] [says|calls for] {what}. [Messy|Sloppy|Ugly] [game|night] — [good for dogs|keeps it close|evens it out].",
        "🌧️ {what} [expected|on tap|coming]. [Slop|Bad weather] [levels the field|shrinks the gap|keeps it tight].",
        "🌧️ [Ugly|Nasty|Rough] [conditions|weather]: {what}. [Fewer big plays.|Grind-it-out game.|Coin-flip chaos.]",
    ],
    "jetlag": [
        "🕐 {The_them} crossed a few time zones for this one. Body clock's all messed up.",
        "🕐 Jet-lag game for {the_them} — their bodies think it's a different time.",
        "🕐 Long trip for {the_them}, time zones and all. Legs gonna be heavy.",
        "🕐 {The_them} [flew|traveled] across [a few|several] time zones. [Body clocks are off.|Sleep's off.|Clocks don't adjust that fast.]",
        "🕐 [Time-zone|Jet-lag|Body-clock] [issues|problems] for {the_them} — [their bodies lag behind|the legs feel it].",
        "🕐 {The_them} [are|come in] [jet-lagged|on the wrong clock|a few hours off]. [That matters.|Legs feel it.|It adds up.]",
    ],
    "drama_coach_fired": [
        "🧯 {The_them} just [fired|canned] their coach. [Locker room's a mess.|Messy week.|Chaos.]",
        "🧯 Coaching change for {the_them} — [interim guy|new voice], [total chaos|pure chaos].",
        "🧯 [New|Interim] coach for {the_them}. [Chaos inside.|Confusion everywhere.|Turmoil.]",
        "🧯 {The_them} [canned|fired] the coach. [Nobody knows the plan.|Messy week.|Vibes are off.]",
        "🧯 [Coach gone|Coach fired], {the_them} [in chaos|scrambling|reeling].",
    ],
    "drama_suspension": [
        "🧯 {The_them} got a suspension hanging over them: {hl}",
        "🧯 Suspension news for {the_them}. [That shakes a team up.|That rattles a room.]",
        "🧯 [Suspension|Discipline] [drama|news|mess] for {the_them}: {hl}",
        "🧯 {The_them} [lose a guy to|deal with] a suspension. [That hurts.|Tough week.|Rough.]",
    ],
    "drama_legal_trouble": [
        "🧯 {The_them} got off-field drama going on: {hl}",
        "🧯 Legal mess around {the_them} this week. [Distractions are real.|Hard to focus.]",
        "🧯 [Off-field|Legal] [noise|drama|mess] for {the_them}: {hl}",
        "🧯 {The_them} got legal stuff [hanging around|going on]. [Hard to focus.|Distractions.|Noise.]",
    ],
    "drama_family_personal": [
        "🧯 {The_them} dealing with some personal stuff: {hl}",
        "🧯 Heavy week for {the_them} off the field. [Hard to lock in.|Heads elsewhere.]",
        "🧯 [Tough|Heavy|Rough] [personal|off-field] news for {the_them}: {hl}",
        "🧯 {The_them} got [real life|heavy stuff] going on. [Hard to focus.|Heads elsewhere.]",
    ],
    "drama_illness": [
        "🤒 Sickness going around {the_them}: {hl}",
        "🤒 {The_them} got guys [under the weather|sick].",
        "🤒 [Bug|Flu|Illness] [hitting|in] {the_them_s} room.",
        "🤒 [Sick|Ill] bodies for {the_them}: {hl}",
    ],
    "drama_trade_drama": [
        "🧯 Trade drama in {the_them_s} room: {hl}",
        "🧯 {The_them} got a guy wanting out. [Locker room's split.|Vibes are off.]",
        "🧯 [Trade|Trade-request] [noise|drama] around {the_them}: {hl}",
        "🧯 {The_them} got a guy who wants out. [Vibes are off.|Awkward room.]",
    ],
    "bye": [
        "🛌 {us} are fresh off a bye — rested and [game-planned up|ready|healthy].",
        "🛌 Extra week to prep for {us}. [That matters.|Big deal.|It shows.]",
        "🛌 Bye week in the rearview for {us}. Fresh legs, full playbook.",
        "🛌 {us} had [a week off|the bye|extra time] — [fresh legs|healthy bodies|full prep|a full game plan].",
        "🛌 [Post-bye|Off a bye], {us} [come in|show up] [rested|fresh|with fresh legs].",
        "🛌 Extra time to [prep|game-plan|get healthy] for {us}. [That's big.|Matters.|Rested up.]",
    ],
    "short": [
        "⏱️ {them} are on a short week. Not much time to [prep|recover].",
        "⏱️ Short week for {them} — tired bodies, rushed game plan.",
        "⏱️ {them} barely had time to [recover|prep]. Short week.",
        "⏱️ [Quick|Short] turnaround for {them} — [less prep|tired bodies|a rushed plan].",
        "⏱️ {them} [had|got] [barely any|little] time to [prep|recover|heal up].",
        "⏱️ [Short-week|Quick-week] [problems|issues] for {them}. [Tired bodies.|Rushed prep.]",
    ],
    "intl": [
        "🌍 Game's overseas in {where}. These are always weird — {algo} needed extra value to take it.",
        "🌍 International game ({where}). Nobody's really home, everybody's jet-lagged — we only play these with a bigger edge.",
        "🌍 {where} game. Weird spot, so {algo} made sure the number's extra juicy.",
        "🌍 [Overseas|International] [game|trip] ({where}). [Weird spot|Odd setup|Strange vibes] — {algo} [wanted|needed|demanded] extra [value|cushion] to [take|play] it.",
        "🌍 Nobody's-home game in {where}. {Algo} [wanted|needed] [a fatter|a bigger] [number|edge] [for it|to play it].",
        "🌍 {where} [hosts this one|is the venue]. [Travel for everybody|No real home team] — we [only|] [play|take] these with [extra|more] value.",
    ],
    "home": [
        "🏟️ {us} at the crib tonight — their building, their rules.",
        "🏟️ Home cooking for {us}. That crowd finna be loud as hell.",
        "🏟️ {us} in their own house. Y'all know teams play different at home.",
        "🏟️ {us} are home tonight and ready to handle business.",
        "🏟️ {us} got the whole building behind 'em tonight.",
        "🏟️ {us} at home, fans rocking. They about to go to work.",
        "🏟️ {us} [at home|in their building|on home {field}] {tn}. {Crowd} [will be|gonna be] [loud|rocking|behind them].",
        "🏟️ Home [game|night] for {us}. [Friendly building|Their people|Their crowd], their [rules|energy].",
        "🏟️ {us} [play|get to play] in front of their own [fans|people|crowd] {tn}.",
        "🏟️ [Crib game|Home turf|Home {field}] for {us} — [comfortable spot|familiar spot|their building].",
    ],
    "road": [
        "🧳 {us} are on the road — [doesn't scare us|no worries|we don't mind].",
        "🧳 Road game for {us}, but they travel just fine.",
        "🧳 {us} walk into a [hostile|loud|tough] building — we're not worried.",
        "🧳 Away game for {us}. The numbers still like them.",
        "🧳 {us} on the road, but this team doesn't care where they play.",
        "🧳 Away game — {us} bring their own energy.",
        "🧳 {us} hit the road. [Doesn't matter to us.|No big deal.|We're fine with it.]",
        "🧳 {us} [travel|go on the road] {tn}. [Doesn't worry us.|Not a concern.|We don't care.]",
        "🧳 [Road|Away] [spot|trip|game] for {us} — [the numbers still like them|still our side].",
        "🧳 {us} [play|are] in a [hostile|loud|road] building {tn}, and [that's fine|we're cool with it].",
    ],
    "b2b": [
        "😴 {them} played yesterday — [tired|heavy] legs. {us} are [fresh|rested].",
        "😴 {them} are on a back-to-back; {us} had the night off.",
        "😴 Short rest for {them}, full tank for {us}.",
        "😴 {them} are running on [fumes|empty] — played last night.",
        "😴 Back-to-back for {them}. [Tired legs, cold shooting.|Heavy legs.|Dead legs.]",
        "😴 {them} [played|suited up] last night. {us} [didn't|sat|rested].",
        "😴 [Tired|Heavy|Dead] legs for {them} — second night of a back-to-back.",
        "😴 Back-to-back for {them}; {us} [come in fresh|are rested|had a day off].",
    ],
    "rest": [
        "🛌 {us} had {d} more days [off|of rest] than {them}.",
        "🛌 Rest edge: {us} got {d} extra days to [recover|reset|heal].",
        "🛌 {us} come in with {d} more days of rest.",
        "🛌 {us} [got|had] {d} extra days to [get right|recover|reset].",
        "🛌 {d} [extra|more] days [off|of rest] for {us} — [fresh legs|fresher legs].",
        "🛌 Rest edge goes to {us} ({d} more days).",
        "🛌 {us} [rested|sat] {d} more days than {them}.",
        "🛌 Fresher legs for {us}: {d} [more|extra] days [off|of rest].",
    ],
    "bump": [
        "⚾ On the [bump|mound|hill]: {ps} for {us}, {po} for {them}.",
        "⚾ Pitching matchup: {ps} ({us}) vs {po} ({them}).",
        "⚾ {ps} takes the ball for {us}; {them} go with {po}.",
        "⚾ {ps} gets the ball for {us} [against|vs] {po}.",
        "⚾ It's {ps} for {us}, {po} for {them}.",
        "⚾ {ps} ({us}) [vs|against|opposite] {po} ({them}) on the [mound|hill|bump].",
        "⚾ [Starters|Arms|Mound matchup]: {ps} for {us}, {po} for {them}.",
        "⚾ {us} [send|roll with] {ps}; {them} [counter with|go with|send] {po}.",
        "⚾ {po} [starts|goes] for {them}, {ps} for {us}.",
    ],
    "keyout": [
        "🚑 {them} are [rolling|playing] without their starting {pos} ({nm}).",
        "🚑 No {nm} for {them} — that's their starting {pos}.",
        "🚑 {them} are down their starting {pos}, {nm}.",
        "🚑 {them} [lose|are missing|are without] {nm}, their starting {pos}.",
        "🚑 {nm} [is out|sits|won't play] for {them} — [that's|there goes] their starting {pos}.",
        "🚑 Starting {pos} [out|down] for {them}: {nm}.",
        "🚑 [Big|Key] absence: {them} [without|minus] {nm} (starting {pos}).",
    ],
    "banged": [
        "🚑 {them} are [hella|real] banged up ({hurt}).",
        "🚑 {them_s} injury list is [stacking up|piling up]: {hurt}.",
        "🚑 {them} are missing [bodies|guys] — {hurt}.",
        "🚑 {them} are dealing with injuries: {hurt}.",
        "🚑 {them} are [short-handed|thin] ({hurt}).",
        "🚑 {them} [are|come in] [beat up|dinged up|thin]: {hurt}.",
        "🚑 [Injury list|Injuries] for {them}: {hurt}.",
        "🚑 {them} [missing|without] [bodies|guys]: {hurt}.",
    ],
    "healthy": [
        "✅ {us} are healthy — nobody [important|big] sitting.",
        "✅ Full [squad|roster|strength] for {us}.",
        "✅ {us} have [everybody|everyone] available.",
        "✅ {us} are at full strength.",
        "✅ Nobody [big|important|key] missing for {us}.",
        "✅ {us} [come in|are] [healthy|at full strength|full go].",
        "✅ [Clean|Empty] injury report [for|on] {us}.",
        "✅ {us} [got|have] [the whole squad|everyone] [available|ready|good to go].",
        "✅ No [key|big|major] [absences|injuries] for {us}.",
    ],
    "keyout_us": [
        "🚑 {nm} [is out|is ruled out|is sidelined], {the_us} rolling with the backup {pos}.{mv} [We know.|We see it.] We still riding with {algo}.{need}",
        "🚑 No {nm} tonight — backup {pos} gets the keys for {the_us}.{mv} Vegas already baked that in, and the numbers still say this the side.{need}",
        "🚑 Yeah, {nm} [is out|is ruled out|is sidelined]. Everybody and they mama jumped off {the_us}.{mv} We ain't scared — teams always be coming back.{need}",
        "🚑 {nm} [sits|is out|won't go] — [the backup|a backup] {pos} [starts|takes over] for {the_us}.{mv} [We know.|We saw it.|Noted.] [We still riding with {algo}.|Numbers still say this the side.|Still the side.]{need}",
        "🚑 [No|Without] {nm} [tonight|today], {the_us} [turn to|go with|hand it to] the backup {pos}.{mv} [Priced in already, and we're still here.|The price already knows, and so do we.|Still our side.]{need}",
        "🚑 [Yeah|Yep|We see it], {nm} [is out|won't play] and the backup {pos} [starts|is in] for {the_us}.{mv} [Folks jumped ship|The crowd bailed] — [we didn't|not us].{need}",
        "🚑 Backup {pos} [time|duty] for {the_us}: {nm} [is out|is ruled out|is sidelined].{mv} [That's in the number.|It's baked in.] [Still riding.|Still our side.|We stay put.]{need}",
        "🚑 {nm} out, [backup|second-string] {pos} in for {the_us}.{mv} [Everybody else ran|The public ran] — [we're staying|we ain't moving].{need}",
    ],
    "sharp": [
        "💰 [Sharp|Smart|Pro] money is on us: {us} opened {op}, now {now}.",
        "💰 The pros are [hammering|backing|loading up on] {us} — {op} at open, {now} now.",
        "💰 The line moved our way ({opnow}). [Smart money agrees.|The pros agree.]",
        "💰 Money's been [pouring|piling|flowing] in on {us}: {opnow}.",
        "💰 Big money moved {us} {opnow}. We like the company.",
        "💰 {us} went [from {op} to {now}|{op} → {now}] — the pros see it too.",
        "💰 {us} [opened|started] at {op} and [sit|now sit] at {now}. [Smart money agrees.|The pros agree.|Sharps see it too.]",
        "💰 Line [moved|went] our way: {us} {opnow}.",
        "💰 [Pro money|Smart money|Sharp action] [pushed|moved|took] {us} [from {op} to {now}|{op} → {now}].",
        "💰 {op} at open, {now} now — [the market's|money's] [coming our way|backing {us}].",
    ],
    "fade": [
        "💸 Sharp money's been coming in on {the_them}{move}, but they must be some clowns. We're on {the_us} — {why}.",
        "💸 The so-called sharps are all over {the_them}{move}. We're fading the clowns and taking {the_us} — {why}.",
        "💸 Line's moving toward {the_them}{move}. [Let 'em|Cool] — we still like {the_us}, {why}.",
        "💸 Money's pouring in on {the_them}{move}. They must've lost their minds — we got {the_us}, {why}.",
        "💸 Everybody's jumping on {the_them}{move}. They're tweaking — we're riding {the_us}, {why}.",
        "💸 The market's leaning {the_them}{move}. Somebody's about to learn a lesson — we're on {the_us}, {why}.",
        "💸 [Sharp money's coming in on|The so-called sharps love|Line's drifting toward|Money's piling on|Bettors keep pushing|The pros are piling on] {the_them}{move}. [Let 'em|Not buying it|Respectfully, no|We don't care|Cool with us] — we're [on|riding|with] {the_us}, {why}.",
        "💸 {The_them}{move} [are getting|keep getting] the [sharp|big] money. [Fine by us|We fade it] — {the_us} for us, {why}.",
    ],
    "splits_fade": [
        "📊 The whole world on {the_them} — {pt}% of the bets and {pm}% of the money on {mk}. We fading the public and taking {the_us}. That's how Vegas eats, and tonight we eating with 'em.",
        "📊 {pt}% of the bets on {the_them} ({pm}% of the money) on {mk}. Sheep gon' be sheep — we on {the_us} with the other {t}%.",
        "📊 Public's hammering {the_them} on {mk}: {pt}% of the bets, {pm}% of the money. We ain't following the herd — {the_us} all day.",
        "📊 [Splits|The splits|Betting splits] on {mk}: {pt}% of [bets|tickets] and {pm}% of [the money|the cash] on {the_them}. [Fade the crowd|Fade the public|Other way for us]: {the_us}.",
        "📊 {The_them} [are pulling|got] {pt}% of the [tickets|bets] and {pm}% of the money on {mk}. [Crowd's loud, but we ride {the_us}.|Classic fade — give us {the_us}.|We go the other way: {the_us}.]",
        "📊 [The crowd|The public|Everybody] [loves|is piling on] {the_them} on {mk}: {pt}% of bets, {pm}% of money. [We're with the other {t}%|Not us] — {the_us}.",
        "📊 [Lopsided|One-sided] [action|market] on {mk}: {the_them} [have|hold] {pt}% of the bets and {pm}% of the money. We [fade|go against] it with {the_us}.",
    ],
    "splits_ride": [
        "📊 Public's with us on this one — {t}% of the bets and {m}% of the money on {the_us} ({mk}). Sometimes the crowd gets it right.",
        "📊 {t}% of the bets on {the_us} ({m}% of the money) on {mk}. We with the crowd tonight, but we got our own reasons.",
        "📊 [Splits|The splits|Betting splits] on {mk}: {t}% of [bets|tickets] and {m}% of the money on {the_us}. [Crowd's right this time.|We agree, for our own reasons.|Same side, different reasons.]",
        "📊 {The_us} [are pulling|got] {t}% of the [tickets|bets] and {m}% of the money on {mk}. [The public's not wrong every time.|No shame riding with the crowd.|We're on it too.]",
        "📊 [The crowd|The public|Everybody] [likes|is on] {the_us} on {mk} ({t}% of bets, {m}% of money). [Fine by us — our numbers got there first.|Broken clock, right time.|We got our own reasons.]",
    ],
    "splits_even": [
        "📊 Bets are split — {t}% on {the_us}, {pt}% on {the_them} ({m}% / {pm}% of the money). Nobody knows nothing on this one, except us.",
        "📊 Who's betting who: {t}% of the bets on {the_us}, {pt}% on {the_them} ({m}% / {pm}% of the money). Pretty split crowd.",
        "📊 [Split|Divided|Mixed] [market|crowd] on {mk}: {t}% of bets on {the_us}, {pt}% on {the_them}; money {m}% / {pm}%. [Nobody's sure — we are.|No consensus.|Coin-flip crowd.]",
        "📊 {t}% [of the bets|of tickets] on {the_us}, {pt}% on {the_them} ({m}% / {pm}% of the money). [The public can't decide.|Crowd's torn.|No herd to follow.]",
        "📊 [No clear public side|Public's split|Crowd's torn] on {mk}: {the_us} {t}% of bets and {m}% of money, {the_them} {pt}% and {pm}%.",
    ],
    "pub_fade": [
        "🤡 {The_them} are the clear favorite and the public's all over 'em. Don't be a sheep — we're on {the_us}, {why}.",
        "🤡 The public is all over {the_them}. Dummies are about to lose their money — we're on {the_us}, {why}.",
        "🤡 Everybody and their mama is on {the_them}. Not us — we got {the_us}, {why}.",
        "🤡 The sheep are lining up for {the_them}. We're not sheep — we're on {the_us}, {why}.",
        "🤡 Crowd's on {the_them}. We're riding {the_us} and {algo} — {why}.",
        "🤡 Public's hammering {the_them} like it's free money. It ain't — we got {the_us}, {why}.",
        "🤡 All the casuals love {the_them}. We're not casuals — {the_us} all day, {why}.",
        "🤡 [The public is all over|The crowd's piling onto|Casual money loves|Square money loves|The sheep love] {the_them}. [Let 'em|Not us|Cool story|We pass] — we're [on|riding|with] {the_us}, {why}.",
        "🤡 {The_them} [are|look like] the [popular|public|people's] pick. [We fade the crowd|We go the other way] — {the_us}, {why}.",
    ],
    "pub_ride": [
        "🤝 Riding with the [public|crowd] on {the_us} — sometimes the public gotta win, {why}.",
        "🤝 Public's on {the_us} too, and this time they're not [dummies|wrong] — {why}.",
        "🤝 Even a broken clock is right twice a day — the public got {the_us} right, {why}.",
        "🤝 We're with the crowd on {the_us} and not ashamed of it — {why}.",
        "🤝 [Public|Crowd] side on {the_us}, but we got our own reasons — {why}.",
        "🤝 We're riding with the crowd on {the_us}. Sometimes they get it right — {why}.",
        "🤝 [The crowd likes|Casuals like|The public likes] {the_us} [too|as well], and [this time|for once] they're right — {why}.",
        "🤝 [Same side as|Riding with] the [public|crowd] on {the_us}. [No shame|Fine by us|It happens] — {why}.",
    ],
    "bottom": [
        "✅ Bottom line: {bk} [has|got|lists|hangs] {price} [priced like|pegged at|set at|lined as] {need}. {Algo} [sees|says|has it at|makes it|reads] {have}. {close}",
        "✅ Bottom line: {bk} [treats|prices|lists|reads] {price} [like|as] {need}; {algo} [has it closer to|sees|puts it at|lands at] {have}. {close}",
        "✅ Bottom line: {price} [should be|ought to be|is really] [more like|closer to|nearer] {have}, [and|but|while] {bk} [is pricing|has it at|is charging|is dealing] {need}. {close}",
        "✅ Bottom line: {have} [in our book|on our sheet|by our math|on our end|per {algo}] [vs|against|versus] {need} [at the book|in Vegas|on the board] [for|on] {price}. {close}",
        "✅ Bottom line: {bk} [says|shows|posts|hangs] {need} [on|for] {price}, {algo} [says|shows|reads|gets] {have}. {close}",
        "✅ Bottom line: {bk} [says|shows|posts] {need} [on|for] {price}, {algo} [says|reads] {have}. Easy money if {algo}'s right.",
        "✅ Bottom line: {price} [is priced|is pegged|is lined|gets priced] [like|as|at] {need} — [we see|we get|we read|we got] {have}. {close}",
        "✅ Bottom line: {price} [is priced|is lined|gets priced] [like|at] {need}, [and|but] {algo} [sees|says|reads] {have}. That gap is the whole play.",
        "✅ Bottom line: [the book|Vegas|the house] [says|posts|thinks] {need}, [we say|we see|we read|we got] {have}. [We ride {price}.|{price} it is.|Give us {price}.|{price}, say less.|Tail {price}.]",
        "✅ Bottom line: {price} [is|runs|grades out] {have} [by our numbers|on our sheet|by {algo}|to us], [but|yet|and] it's [priced|paying|lined] [like|as] {need}. {close}",
        "✅ Bottom line: we [make|have|grade|put] {price} [at|as|around] {have}; {bk} [only gives it|is giving it|says|hangs] {need}. {close}",
        "✅ Bottom line: [our number|our read|the model|our math] [on|for] {price} [is|says|reads] {have}, [vs|against|versus] {need} [at the book|in Vegas|on the board]. {close}",
        "✅ Bottom line: [priced for|paying like|lined at|posted at] {need}, [real odds|true odds|our odds|fair odds] {have} — {price} [is the play|all day|it is|for us].",
        "✅ Bottom line: [the gap|the difference|the space] between {need} ({bk}) and {have} ({algo}) [is why we're on|puts us on|sends us to|is the case for] {price}.",
        "✅ Bottom line: {bk} [thinks|figures|guesses|says] {need} [for|on] {price}. [We think|We figure|We say|We see|Our read's] {have}. {close}",
        "✅ Bottom line: {price} [sits|trades|lives|hangs] at {need} [on the board|in Vegas|at the book]; {algo} [lands on|comes out at|spits out|gets] {have}. {close}",
        "✅ Bottom line: {have} [vs|against|over] {need} — [that's|call it|it's] [our math|the math|our read|our model] [against|over|vs] {bk} [on|for] {price}. {close}",
        "✅ Bottom line: we [call|make|grade] {price} {have}. {Bk} [calls|makes|grades] it {need}. {close}",
        "✅ Bottom line: [we're|we are|we land] at {have} [on|for] {price}; [the market's|the book's|Vegas is] at {need}. {close}",
        "✅ Bottom line: [{bk} is|the price is|the board is] {need} [on|for] {price}. [Truth is|The real number is|Our number is|We have it] {have}. {close}",
        "✅ Bottom line: {need} is what {bk} [charges|asks|posts|hangs]; {have} is what {algo} [sees|reads|gets] on {price}. {close}",
        "✅ Bottom line: {price} [wins|gets there|lands|cashes] {have} [by|on|per] {algo}, [priced|paid|posted] [like|as] {need}. {close}",
    ],
    "bottom_ls": [   # a LOCK with a small edge: still said with our whole chest - never "not a sure thing" / "thin value"
        "✅ Bottom line: {price} is the [right|smart|correct] side and we're [on it|riding it|all in]. {close}",
        "✅ Bottom line: [we like|we're riding|we're on] {price}. {Bk} has it at {need} — [the matchup|the details|everything above] [makes it|puts it] ours. {close}",
        "✅ Bottom line: {price}. [Every angle|Everything above|The whole breakdown] [points|breaks|leans] our way. {close}",
        "✅ Bottom line: [tail it|ride it|we're riding it]: {price}. [The details|The matchup|The spots] [all back us|all favor us|line up for us].",
        "✅ Bottom line: {price} [is our lock|is the lock|is locked in]. [The edges|The details|The angles] above [seal it|decide it|carry it]. {close}",
        "✅ Bottom line: [confident|locked in|all in] on {price}. {Bk} [sits|is] at {need}; [we see more|we like it more|our side's stronger]. {close}",
        "✅ Bottom line: [give us|we want|put us on] {price}. [Every little edge|All the details|The whole picture] [goes|breaks|leans] our way. {close}",
        "✅ Bottom line: {price}, [no hesitation|no second guessing|zero doubt]. {close}",
    ],
    "bottom_s": [
        "✅ Bottom line: {bk} [got|has|lists] {price} [priced like|pegged at|lined at] {need}, but [everything above|the fine print|the small stuff|every little detail] [tips it our way|leans our way|breaks our way|points our way]. {sclose}",
        "✅ Bottom line: [close to|near|right around] {need} [at the book|in Vegas|on the board], [but|yet|and still] the [details|little things|small edges] [break|lean|tilt] our way on {price}. {sclose}",
        "✅ Bottom line: {price} [ain't|isn't] a [slam dunk|sure thing|gimme], it's a [smart|sharp|good] number — [and|plus] the little things all [point|lean|tilt] our way. {sclose}",
        "✅ Bottom line: {price} is a [thin|slim|small|skinny] edge, but it's [an edge|still an edge|ours]. {sclose}",
        "✅ Bottom line: no [blowout|runaway|landslide] [expected|coming|in sight] on {price}, just a [smart|sharp|right] number with everything [tilting|leaning|breaking] our way. {sclose}",
        "✅ Bottom line: {price} [ain't|isn't] [flashy|pretty|sexy]. It's just the [right|smart|correct] side. {sclose}",
        "✅ Bottom line: [the book|Vegas|the market|the house] [has|got|keeps] {price} close, but the [small stuff|fine print] [breaks|tips|leans] our way. {sclose}",
        "✅ Bottom line: {price} [sits|is priced|lives|hangs] [near|around|close to] {need}. [Small|Slim|Thin|Tiny] [edge|margin], [but it's ours|right side|still an edge]. {sclose}",
        "✅ Bottom line: [not a lot of|little|not much] [cushion|room|space] on {price} ({need} at {bk}), but every [tiebreaker|close call|coin toss] [goes|breaks|leans] our way. {sclose}",
        "✅ Bottom line: [thin|slim|small|narrow] [value|edge] on {price} — {bk} is [close|near fair|about right] at {need}, the [extras|details|intangibles] [favor|push|help] us. {sclose}",
        "✅ Bottom line: {price} [won't|ain't gonna] [blow anybody away|wow anybody|make headlines], [but|and|yet] {algo} still [likes|picks|backs] it. {sclose}",
        "✅ Bottom line: [fair-ish|tight|honest] price on {price} ({need}); the [edges|extras|details] above [make it|tip it|swing it] ours. {sclose}",
        "✅ Bottom line: {price} is a [grinder|small-edge spot|margin play|quiet one], not a [haymaker|slam dunk|blowout call|big swing]. {sclose}",
        "✅ Bottom line: [tight|close|narrow] number on {price} ({need}), [so|and] the [details|little edges|tiebreakers] [decide it|carry it|settle it]. {sclose}",
        "✅ Bottom line: {bk} is [basically|pretty much|close to] right at {need} on {price}. [The extras|The margins|The details] [are ours|tip it|break our way]. {sclose}",
    ],
    "lean": [
        "🟡 Bottom line: no edge on this one — it's a lean, not a lock. {Algo} just leans {team}.",
        "🟡 Bottom line: the numbers don't give us an edge here. {team} is the lean, nothing more.",
        "🟡 Bottom line: lean only. The price is about right, {algo} just tilts {tms} way.",
        "🟡 Bottom line: no value, no lock — {team} is where {algo} leans, that's it.",
        "🟡 Bottom line: [no edge here|no value on our numbers|the price is about fair] — {team} is [a lean|the lean], not a lock.",
        "🟡 Bottom line: [small|slight] lean to {team}. [No edge on the price|The number's fair|Price is fair], so [no hype|keep it light].",
        "🟡 Bottom line: [it's|this is] a lean, not a lock. {Algo} [tilts|leans|nudges] toward {team}, [that's all|nothing more].",
        "🟡 Bottom line: {team} by a hair on {algo}. [No edge|No value] at this price — lean, not lock.",
        "🟡 Bottom line: [honest|straight] read — {team} is a lean. [The price is fair.|No edge on the number.]",
    ],
    # context study facts
    "cx_rival": [
        "🔥 Rivalry [game|night]. {The_us} and {the_them} got real history.",
        "🔥 Circled on both calendars — these two don't like each other.",
        "🔥 Straight-up rivalry. Records go out the window in these.",
        "🔥 Bad blood [game|night] — this is one of the classics.",
        "🔥 Rivalry [night|game]. No love lost between these two.",
        "🔥 [Rivalry|Grudge] [game|match]: {the_us} vs {the_them}. [Throw out the records.|History runs deep.|Emotions run hot.]",
        "🔥 {The_us} and {the_them} [can't stand|don't like] each other. [Expect a fight.|Records mean nothing.]",
        "🔥 [Old|Real|Deep] rivalry — [these two|{the_us} and {the_them}] [go way back|got history].",
    ],
    "cx_rival_t": [
        "🔥 Rivalry game — {them}. Emotions run [hot|high] in these.",
        "🔥 Classic rivalry on the board: {them}.",
        "🔥 Bad blood matchup ({them}). These get weird on the scoreboard.",
        "🔥 [Rivalry|Grudge] [game|matchup] ({them}). [Emotions run hot.|These get weird.|Anything goes on the scoreboard.]",
        "🔥 [History|Old beef] [on the board|in this one]: {them}.",
    ],
    "cx_div": [
        "🔥 Division game — {the_us} and {the_them} see each other every year.",
        "🔥 Division rivals. They know each other's playbook cold.",
        "🔥 Division matchup: familiarity on both sides.",
        "🔥 It's a division game, so both sides know exactly what's coming.",
        "🔥 Division beef. No secrets between these two.",
        "🔥 Division [game|matchup]: {the_us} and {the_them} [know each other cold|have no secrets].",
        "🔥 [Same division|Division rivals] — [no secrets here|familiar faces|they know the playbook].",
        "🔥 Every season {the_us} and {the_them} [meet|see each other]. [No surprises.|Familiar stuff.]",
    ],
    "cx_div_t": [
        "🔥 Division game ({them}) — two teams that know each other cold.",
        "🔥 Division matchup on the total: {them}.",
        "🔥 Familiar foes ({them}), division game.",
        "🔥 [Familiar|Division] [foes|rivals] on the total: {them}.",
        "🔥 Division [game|matchup] ({them}) — [no surprises either way|they know each other].",
    ],
    "cx_trip": [
        "🧳 {The_them}: {fact}. That travel adds up.",
        "🧳 {Fact} for {the_them}. Frequent flyer points, heavy legs.",
        "🧳 {The_them} living out of a suitcase — {fact}.",
        "🧳 Travel check on {the_them}: {fact}.",
        "🧳 {The_them} put in the miles to get here ({fact}).",
        "🧳 [Road-weary|Heavy-travel|Long-haul] spot for {the_them}: {fact}.",
        "🧳 [Miles pile up|Travel adds up|Miles add up] for {the_them} ({fact}).",
        "🧳 {The_them} [on|in] [travel|road] mode: {fact}.",
    ],
    "cx_domecold": [
        "🏟️ Dome team outside in {wx} — {who} usually play with the thermostat set.",
        "🏟️ {Who} play indoors at home. Tonight: {wx} outside.",
        "🏟️ No roof tonight for {who}. {Wx} in the forecast.",
        "🏟️ Indoor squad in the elements: {wx} for {who}.",
        "🏟️ [Roof's gone|No dome] for {who}: {wx} [on tap|in the forecast|at kickoff].",
        "🏟️ {Wx} [and no roof|outdoors] — [tough|rough] [ask|spot] for {who}, a dome team.",
        "🏟️ Dome team in {wx}? [Tough ask for|Rough spot for|Not ideal for] {who}.",
    ],
    "cx_domeout": [
        "🏟️ {The_them} are a dome team playing outside today.",
        "🏟️ No roof for {the_them} this time — they're used to playing inside.",
        "🏟️ {The_them} leave the dome for an open-air building.",
        "🏟️ Open air for an indoor team: {the_them} out of their element.",
        "🏟️ Dome team [outdoors|in open air|under the sky] today: {the_them}.",
        "🏟️ {The_them} [trade|swap] the roof for open air [today|this week].",
        "🏟️ [Out of the dome|Away from the roof], {the_them} [play outside|are in the elements] today.",
    ],
    "cx_mustwin": [
        "🚨 Must-win for {the_us} ({rec}) — right in the playoff race.",
        "🚨 {The_us} ({rec}) are fighting for a playoff spot. Backs against the wall.",
        "🚨 Playoff race: {the_us} need this one, {the_them} don't.",
        "🚨 Every game counts for {the_us} ({rec}) right now. {The_them}? Not so much.",
        "🚨 {The_us} ({rec}) [can't afford|can't take] [an L|a loss] — playoff race.",
        "🚨 [Playoff push|Playoff chase]: {the_us} ({rec}) [need|gotta have] this one.",
        "🚨 [Season on the line|Big stakes] for {the_us} ({rec}) in the playoff race.",
    ],
    "cx_rest": [
        "🪑 {The_them} already clinched — rest-the-starters territory.",
        "🪑 Playoff spot locked for {the_them}. Don't be shocked if the stars sit.",
        "🪑 {The_them} got their ticket punched already. Nothing to play for tonight.",
        "🪑 Clinched and coasting: {the_them} could rest guys.",
        "🪑 {The_them} [clinched already|locked their spot]. [Starters could sit.|Minutes could get managed.]",
        "🪑 [No stakes|Nothing on the line] for {the_them} — they've already clinched.",
        "🪑 [Clinched|Locked in], {the_them} [may|could] [rest|sit] [the stars|starters|key guys].",
    ],
    "cx_tank": [
        "📉 {The_them} ({rec}) are out of it. Draft-pick season over there.",
        "📉 Eliminated and {rec} — {the_them} are playing for ping-pong balls.",
        "📉 {The_them} ({rec}) got nothing to play for but next year.",
        "📉 Season's over for {the_them} ({rec}), they just haven't gone home yet.",
        "📉 {The_them} ({rec}) [are done|are eliminated]. [Next year's the focus.|Eyes on the draft.]",
        "📉 [Lottery|Draft] watch: {the_them} ({rec}) are out of it.",
        "📉 {rec} and eliminated, {the_them} are [playing out the string|counting down].",
    ],
    "cx_elim": [
        "📉 {The_them} are eliminated; {the_us} are still in the race.",
        "📉 One team's playing for a spot, the other's playing out the string.",
        "📉 {The_them} are out of the playoff picture. {The_us} ain't.",
        "📉 Playoff hopes: {the_us} alive, {the_them} done.",
        "📉 {The_us} [still alive|still in it]; {the_them} [are out|are eliminated|are done].",
        "📉 Only one side [still has|still got] [playoff hopes|something to play for]: {the_us}.",
        "📉 [Stakes gap|Motivation gap]: {the_us} in the race, {the_them} [eliminated|done|out].",
    ],
    "cx_bowl": [
        "🏈 {us} sit at 5 wins — one more and they're bowl eligible.",
        "🏈 Bowl eligibility on the line: {us} need win number 6.",
        "🏈 {us} are one W from a bowl game. Extra motivation.",
        "🏈 Win 6 means a bowl trip for {us}.",
        "🏈 {us} [are|sit] at 5 wins. [One more|Win 6] [gets|punches] a bowl [ticket|bid].",
        "🏈 [Bowl|Postseason] [bid|trip] on the line for {us} (5 wins, need 6).",
        "🏈 {us} [need|want] win [No. 6|number 6] for bowl eligibility.",
    ],
    "cx_hotseat": [
        "🔥 {The_them} have lost {cnt} straight — that coach is on the hot seat.",
        "🔥 {cnt} losses in a row for {the_them}. Coaching staff feeling the heat.",
        "🔥 {The_them} ({cnt} straight L's) are in a fishbowl right now.",
        "🔥 Losing streak at {cnt} for {the_them}. Jobs on the line over there.",
        "🔥 {cnt} straight {Ls} for {the_them} — [the coach's|coach's] [seat's warm|job's shaky|job's on the line].",
        "🔥 [Heat's on|Pressure's on] {the_them_s} coach after {cnt} straight {Ls}.",
        "🔥 {The_them} have [dropped|lost] {cnt} {str8}. [Hot seat talk is loud.|Jobs on the line.]",
    ],
    "cx_ref": [
        "🦓 {Nm} on the whistle tonight — those games have leaned toward {what}.",
        "🦓 Zebra check: {nm_s} crew has tilted to {what} over earlier games.",
        "🦓 {Nm} officiating. The track record leans {what}.",
        "🦓 Officials matter: {nm_s} games have gone {what}'s way more than the book expected.",
        "🦓 [Ref|Officiating] [note|check|watch]: {nm_s} games [lean|tilt|trend] toward {what}.",
        "🦓 {Nm} [has the whistle|is running the game|calls this one]. [History leans|Past games lean|The record leans] {what}.",
        "🦓 [With|Under] {nm}, games [have leaned|tend to lean|have tilted] toward {what}.",
    ],
    "talk_contract_year": [
        "📣 Contract-year energy around {who} — somebody's playing for a bag.",
        "📣 {Who} got money on the line this year. Contract talk all week.",
        "📣 Payday season for {who}: the contract chatter is loud.",
        "📣 Incentives on the line for {who}. Expect some extra effort.",
        "📣 [Payday|Contract] [talk|chatter] around {who}: [money's on the line|incentives in play].",
        "📣 {Who} got a contract year going. [Expect extra effort.|Motivation's up.]",
        "📣 [Incentives|Bonuses] [at stake|on the line] for {who}. [Watch the effort.|Extra juice.]",
    ],
    "talk_unhappy": [
        "📣 Not everybody's happy over there — {who} got some public frustration going.",
        "📣 Grumbling in {who_s} camp this week, and it's out in the open.",
        "📣 Somebody in {who_s} building is venting to the press. Vibes are off.",
        "📣 {Who} got a frustrated voice or two talking publicly.",
        "📣 [Frustration|Grumbling] [coming out of|around] {who} [this week|lately]. [Vibes are off.|Not a happy room.]",
        "📣 {Who} got [somebody|a player] [venting|complaining] [publicly|to the press].",
    ],
    "talk_trash_talk": [
        "📣 {Who} been running their mouth this week. Bulletin-board stuff.",
        "📣 Trash talk out of {who_s} side. Somebody gotta back it up now.",
        "📣 {Who} talked a big game all week — receipts get checked tonight.",
        "📣 Guarantees flying around {who}. Talk is cheap till kickoff.",
        "📣 {Who} [talked|popped off|ran their mouth] [all week|this week]. [Gotta back it up now.|Receipts tonight.]",
        "📣 [Big talk|Trash talk|Guarantees] out of {who} [this week|lately]. [Talk is cheap.|Now prove it.]",
    ],
    "talk_must_win": [
        "📣 {Who} already calling it a must-win out loud.",
        "📣 \"Must-win\" is the word around {who} this week. Backs to the wall.",
        "📣 {Who} say their season rides on this one.",
        "📣 Win-or-else talk coming out of {who}.",
        "📣 {Who} [calling|are calling] it a must-win [out loud|publicly].",
        "📣 [Must-win|Win-or-else] [talk|energy] [around|out of] {who} this week.",
    ],
    "talk_rivalry_week": [
        "📣 Rivalry week talk is loud around {who}. Bad blood energy.",
        "📣 {Who} been hyping the rivalry all week.",
        "📣 Bragging rights on the line, and {who} know it.",
        "📣 Circled on the calendar for {who}. No love lost here.",
        "📣 {Who} [been talking up|keep hyping] the rivalry [all week|this week].",
        "📣 [Rivalry|Bragging-rights] talk around {who}. [Bad blood energy.|No love lost.]",
    ],
    "talk_hot_seat": [
        "📣 Coach's job is a hot topic around {who}. Hot seat talk everywhere.",
        "📣 Job-security questions around {who_s} coach this week.",
        "📣 {Who_s} coach is feeling the heat in the papers.",
        "📣 The coach over at {who} is under the microscope right now.",
        "📣 [Coach's job|Job security] [talk|questions] [around|for] {who} this week.",
        "📣 {Who_s} coach [is feeling|feels] the heat [in the press|this week].",
    ],
}
T.update({
    "better_s": [
        "💪 {us} are the better [squad|team|side], even if it's closer than it [looks|seems|reads].",
        "💪 {us} have the [edge|upper hand] on paper — not a [blowout|landslide|runaway], but it's there.",
        "💪 [Slight|Small|Modest|Little] edge {us} on who's [actually|really|truly] [better|stronger].",
        "💪 {us} have a [little|touch|bit|hair] more [juice|talent|punch] than {them}.",
        "💪 Close-ish on paper, but {us} are [better|the better side|a notch up|a step ahead].",
        "💪 {us} got the upper hand, not by a mile but it's [there|real].",
        "💪 {us} are [a notch|a step|a hair|a tick] [better|stronger|sharper] than {them} {rn}.",
        "💪 [Not a mismatch|No blowout on paper|Not by much], but {us} are the [better|stronger] [side|team|squad].",
        "💪 Edge {us}, [slim but real|small but there|thin but there] on [talent|paper].",
        "💪 {them} keep it close on paper; {us} [still grade out better|are still a notch up|still rate higher].",
    ],
    "worse": [
        "🐺 {them} look better on paper — that's [exactly|precisely] why [we're getting|we get] this [juicy|fat|sweet] price on {us}.",
        "🐺 [Everybody's|The world's|Everyone's] on {them}. That's how we get {us} at this [number|price].",
        "🐺 {them} are the [name brand|big name|headline act] here, but the price on {us} is too [good|sweet] to pass.",
        "🐺 On paper it's {them}. On the {field}? We like {us} at this [price|number].",
        "🐺 {them} get all the [love|hype|respect] — that's why {us} are sitting at this [number|price].",
        "🐺 [Paper|The resume] says {them}. [The price|This number] says {us}, and we [listen to|follow|trust] the price.",
        "🐺 [Sure|Yeah|Fine], {them} are better on paper. [That's baked in|That's in the price|Priced in] — the value's on {us}.",
        "🐺 We know {them} got more [talent|names]. That's why {us} come [this cheap|at a discount|at this price].",
        "🐺 [Price spot|Value spot]: {them} [have|got] the [names|resume|hype], we [have|got] the [number|price] on {us}.",
        "🐺 {them} [are favored|get the respect] for a reason. [Still,|But] {us} at this [price|number] is [value|the play].",
    ],
    "h2h": [
        "🆚 {us} [own|run] this [matchup|series] — [won|took] {ofl}.",
        "🆚 {us} have had {them_s} number: {ofl}.",
        "🆚 History's on our side — {ofl} went {us_s} way.",
        "🆚 {us} been [owning|handling|bullying] {them} [lately|recently] — {ofl}.",
        "🆚 {them} can't [figure|solve] {us} out: {ofl}.",
        "🆚 [Head to head|Series history|Recent meetings|The series]: {us} [took|won] {ofl}.",
        "🆚 {ofl} [meetings|matchups|go-rounds] [went to|belonged to] {us}.",
        "🆚 {us} [know how to beat|have the book on|have a feel for] {them} — {ofl}.",
        "🆚 [When these two meet|In this matchup], {us} [usually|tend to] [win|come out on top]: {ofl}.",
        "🆚 {them} [keep losing to|struggle with|can't solve] {us} — {ofl}.",
    ],
    "h2h1": [
        "🆚 {us} got 'em [last time|the last go|in the last one]: {res}.",
        "🆚 Last [meeting|matchup|one] went {us_s} way ({res}).",
        "🆚 {us} [handled|beat|got] {them} [last time|last go] ({res}).",
        "🆚 Last time these two met, {us} [took it|won|got it] ({res}).",
        "🆚 [Previous|Last] [meeting|matchup|go-round]: {us} [won|took it|got it] ({res}).",
        "🆚 {us} [took down|got past|got by] {them} last time ({res}).",
        "🆚 [Most recent|The last] [meeting|matchup] [belonged to|went to] {us} ({res}).",
    ],
    "QB_cold": [
        "🗑️ {name} has been complete booty cheeks — {txt}.",
        "🗑️ {name} has been [throwing it|feeding it] to the other team — {txt}.",
        "🗑️ {name} looks [lost|confused|shook|rattled] out there: {txt}.",
        "🗑️ {name} [can't|hasn't been able to] find [the open man|a receiver|anybody] — {txt}.",
        "🗑️ {name} has been [a mess|rough|shaky|ugly|a liability] {rn}: {txt}.",
        "🗑️ {name} [keeps|been] [missing throws|turning it over|missing reads|forcing it]: {txt}.",
        "🗑️ [Bad|Rough|Ugly] [stretch|run|patch] for {name} — {txt}.",
        "🗑️ {name} under center? [A problem|A liability|A gift] — {txt}.",
        "🗑️ [Yikes|Oof|Woof], {name} {rn}: {txt}.",
    ],
    "SP_cold": [
        "💣 {name} has been getting [shelled|lit up|tagged|rocked] — {txt}.",
        "💣 {name} has been [getting lit up|hittable|a piñata|shaky]: {txt}.",
        "💣 Hitters [are teeing off|feast|are feasting] on {name} — {txt}.",
        "💣 {name} keeps getting [tagged|rocked|hit hard|squared up]: {txt}.",
        "💣 Bats [love|feast on|tee off on|light up] {name}: {txt}.",
        "💣 [Rough|Ugly|Bad] [run|stretch|patch] for {name}: {txt}.",
        "💣 {name} can't [miss bats|get outs|find the zone]: {txt}.",
        "💣 {name} [lately|of late]? [Batting practice|Rough|Ugly]: {txt}.",
    ],
    "G_cold": [
        "🥅 {name} has been leaky as hell — {txt}.",
        "🥅 {name} can't stop a beach ball {rn}: {txt}.",
        "🥅 Pucks keep [getting past|beating|sneaking by] {name} — {txt}.",
        "🥅 {name} has been [a sieve|shaky|leaky|a turnstile] {rn}: {txt}.",
        "🥅 [Rough|Ugly|Bad] [run|stretch|patch] in net for {name}: {txt}.",
        "🥅 {name} [can't find|lost] the puck {rn} — {txt}.",
        "🥅 Shooters [love|feast on|are lighting up|tee off on] {name}: {txt}.",
    ],
    "QB_hot": [
        "🎯 {name} has been [cooking|dealing|sharp|nice] — {txt}.",
        "🎯 {name} is [locked in|dialed in|on fire|rolling|hot]: {txt}.",
        "🎯 {name} is [slinging it|cooking|dealing|dicing] — {txt}.",
        "🎯 {name} [been|is] [dicing|carving] [defenses|'em up|'em]: {txt}.",
        "🎯 [Hot|Sharp|Clean|Big] [stretch|run|streak] for {name}: {txt}.",
        "🎯 {name} [can't miss|is dialed|is money]: {txt}.",
        "🎯 {name} [is|has been] [dealing|sharp|rolling|money|nice]: {txt}.",
    ],
    "SP_hot": [
        "🔥 {name} has been [dealing|nasty|filthy|sharp] — {txt}.",
        "🔥 {name} is [on a roll|dealing|locked in|rolling]: {txt}.",
        "🔥 Nobody's [touching|hitting|solving] {name} [lately|recently] — {txt}.",
        "🔥 {name} [is|has been] [dealing|nasty|filthy|dialed in|sharp|lights out]: {txt}.",
        "🔥 Hitters [can't touch|can't solve|are lost against|can't square up] {name}: {txt}.",
        "🔥 [Nasty|Filthy|Sharp|Big] [stretch|run|streak] for {name}: {txt}.",
    ],
    "G_hot": [
        "🧱 {name} has been a [brick wall|wall|brick] — {txt}.",
        "🧱 {name} is standing on his head: {txt}.",
        "🧱 Good luck [scoring on|beating|solving] {name} — {txt}.",
        "🧱 {name} [is|has been] [locked in|a wall|dialed in|lights out|hot]: {txt}.",
        "🧱 [Nothing's|Nothing is] getting [past|by] {name}: {txt}.",
        "🧱 [Hot|Sharp|Big] [stretch|run|streak] in net for {name}: {txt}.",
    ],
    "alt": [
        "🏔️ Thin air — {elev} meters up. {The_them} gonna be sucking wind by the [second half|end|late going].",
        "🏔️ Altitude game. {The_them} ain't used to [breathing|playing|running] up there.",
        "🏔️ Mile-high problems for {the_them}. Legs get [heavy|tired|dead] fast at that [elevation|height].",
        "🏔️ {elev} meters [up|above sea level]. {The_them} [will|gonna] feel it [late|in the legs|in the lungs].",
        "🏔️ Thin air at {elev} meters — [lungs burn|legs go|gas tanks drain] fast for {the_them}.",
        "🏔️ {The_them} [visiting|playing] at {elev} meters. [Oxygen's|Air's] [thin|scarce|short] up there.",
        "🏔️ [Altitude|Elevation] check: {elev} meters. {The_them} ain't [built|ready] for it.",
    ],
    "cold_w": [
        "🥶 {temp}°F at kickoff. {The_them} are a warm-weather [squad|team] walking into a [freezer|fridge].",
        "🥶 It's gonna be {temp}°F. {The_them} don't play in this — {the_us} do.",
        "🥶 [Cold|Frigid] one ({temp}°F). Welcome to real weather, {the_them}.",
        "🥶 {temp}°F [tonight|out there|at kickoff]. {The_them} [ain't used to this|are a warm-weather team|hate this].",
        "🥶 [Freezer|Ice box|Cold] game: {temp}°F. {The_them} [won't like it|are out of their element].",
        "🥶 [Bundle up|Gloves on|Grab a coat], {the_them} — {temp}°F [at kickoff|out there].",
        "🥶 {The_them} [come from|live in] the warm. [Tonight|Kickoff] is {temp}°F.",
    ],
    "jetlag": [
        "🕐 {The_them} crossed a few time zones for this one. Body clock's all [messed up|off].",
        "🕐 Jet-lag game for {the_them} — their bodies think it's a different time.",
        "🕐 Long trip for {the_them}, time zones and all. Legs gonna be [heavy|slow].",
        "🕐 {The_them} [flew|traveled] across [a few|several] time zones. [Body clocks are off.|Sleep's off.|Clocks don't adjust that fast.]",
        "🕐 [Time-zone|Jet-lag|Body-clock] [issues|problems] for {the_them} — [their bodies lag behind|the legs feel it].",
        "🕐 {The_them} [are|come in] [jet-lagged|on the wrong clock|a few hours off]. [That matters.|Legs feel it.|It adds up.]",
    ],
    "revenge": [
        "😤 [Revenge|Payback|Get-back] game — {us} lost the last meeting and they haven't forgotten.",
        "😤 {us} owe {them} one from last time. [Payback's coming.|Time to collect.|Get-back time.]",
        "😤 Get-back game for {us}. They took an L to {them} [last time|in the last one].",
        "😤 {us} been [waiting on|itching for|hungry for] this rematch.",
        "😤 {them} got {us} last time. [That stuck with them.|That one stung.|They remember.]",
        "😤 [Payback|Rematch|Get-back] [spot|game|time]: {us} dropped the last one to {them}.",
        "😤 {us} [lost the last meeting|took an L last time] — [they want this one back|this one's personal|they remember].",
        "😤 [Bad memories|Unfinished business|Sour taste] for {us} — {them} [won|took] the last meeting.",
        "😤 {us} [circled|marked] this one after losing to {them} [last time|in the last one].",
    ],
    "momentum": [
        "🚀 {us} just blew somebody out — teams like that keep [rolling|going|coming].",
        "🚀 {us} are coming in hot off a blowout. [Momentum's real.|Confidence is up.|They're rolling.]",
        "🚀 Blowout last time out for {us}. They're [feeling themselves|rolling|confident].",
        "🚀 {us} [ran|rolled] somebody off the {field} last time. [Keep it going.|Carry it over.|Ride it.]",
        "🚀 [Momentum|Confidence] [is|stays] [high|up|sky high] for {us} after a blowout.",
        "🚀 [Last time out|Last game], {us} [won big|won going away|blew somebody out]. [Confidence is up.|They're rolling.]",
        "🚀 {us} [smoked|ran over|blew out] their last opponent. [Momentum's on our side.|That carries.|Keep it rolling.]",
    ],
    "bye": [
        "🛌 {us} are fresh off a bye — rested and [game-planned up|ready|healthy].",
        "🛌 Extra week to [prep|plan|heal] for {us}. [That matters.|Big deal.|It shows.]",
        "🛌 Bye week in the rearview for {us}. Fresh legs, full [playbook|tank].",
        "🛌 {us} had [a week off|the bye|extra time] — [fresh legs|healthy bodies|full prep|a full game plan].",
        "🛌 [Post-bye|Off a bye], {us} [come in|show up] [rested|fresh|with fresh legs].",
        "🛌 Extra time to [prep|game-plan|get healthy] for {us}. [That's big.|Matters.|Rested up.]",
    ],
    "short": [
        "⏱️ {them} are on a short week. Not much time to [prep|recover|heal].",
        "⏱️ Short week for {them} — [tired|sore] bodies, [rushed|thin] game plan.",
        "⏱️ {them} barely had time to [recover|prep|heal]. [Short week.|Quick turnaround.]",
        "⏱️ [Quick|Short] turnaround for {them} — [less prep|tired bodies|a rushed plan].",
        "⏱️ {them} [had|got] [barely any|little] time to [prep|recover|heal up].",
        "⏱️ [Short-week|Quick-week] [problems|issues] for {them}. [Tired bodies.|Rushed prep.]",
    ],
    "b2b": [
        "😴 {them} played yesterday — [tired|heavy] legs. {us} are [fresh|rested].",
        "😴 {them} are on a back-to-back; {us} had the night off.",
        "😴 Short rest for {them}, full tank for {us}.",
        "😴 {them} are running on [fumes|empty] — played last night.",
        "😴 Back-to-back for {them}. [Tired legs, cold shooting.|Heavy legs.|Dead legs.]",
        "😴 {them} [played|suited up] last night. {us} [didn't|sat|rested].",
        "😴 [Tired|Heavy|Dead] legs for {them} — [second night of a|on a] back-to-back.",
        "😴 Back-to-back for {them}; {us} [come in fresh|are rested|had a day off].",
    ],
    "rest": [
        "🛌 {us} had {d} more days [off|of rest] than {them}.",
        "🛌 Rest edge: {us} got {d} extra days to [recover|reset|heal].",
        "🛌 {us} [come in|show up] with {d} more days of rest.",
        "🛌 {us} [got|had] {d} extra days to [get right|recover|reset].",
        "🛌 {d} [extra|more] days [off|of rest] for {us} — [fresh legs|fresher legs].",
        "🛌 Rest edge [goes to|belongs to] {us} ({d} more days).",
        "🛌 {us} [rested|sat] {d} more days than {them}.",
        "🛌 Fresher legs for {us}: {d} [more|extra] days [off|of rest].",
    ],
    "bump": [
        "⚾ On the [bump|mound|hill]: {ps} for {us}, {po} for {them}.",
        "⚾ [Pitching matchup|Mound duel]: {ps} ({us}) vs {po} ({them}).",
        "⚾ {ps} [takes|gets] the ball for {us}; {them} go with {po}.",
        "⚾ {ps} gets the ball for {us} [against|vs] {po}.",
        "⚾ It's {ps} for {us}, {po} for {them}.",
        "⚾ {ps} ({us}) [vs|against|opposite] {po} ({them}) on the [mound|hill|bump].",
        "⚾ [Starters|Arms|Mound matchup]: {ps} for {us}, {po} for {them}.",
        "⚾ {us} [send|roll with] {ps}; {them} [counter with|go with|send] {po}.",
        "⚾ {po} [starts|goes] for {them}, {ps} for {us}.",
    ],
    "keyout": [
        "🚑 {them} are [rolling|playing|going] without their starting {pos} ({nm}).",
        "🚑 No {nm} for {them} — that's their starting {pos}.",
        "🚑 {them} are [down|missing] their starting {pos}, {nm}.",
        "🚑 {them} [lose|are missing|are without] {nm}, their starting {pos}.",
        "🚑 {nm} [is out|sits|won't play] for {them} — [that's|there goes] their starting {pos}.",
        "🚑 Starting {pos} [out|down] for {them}: {nm}.",
        "🚑 [Big|Key] [absence|loss]: {them} [without|minus] {nm} (starting {pos}).",
    ],
    "banged": [
        "🚑 {them} are [hella|real] banged up ({hurt}).",
        "🚑 {them_s} injury list is [stacking up|piling up|growing]: {hurt}.",
        "🚑 {them} are missing [bodies|guys|pieces] — {hurt}.",
        "🚑 {them} are dealing with [injuries|bumps]: {hurt}.",
        "🚑 {them} are [short-handed|thin] ({hurt}).",
        "🚑 {them} [are|come in] [beat up|dinged up|thin]: {hurt}.",
        "🚑 [Injury list|Injuries|Out] for {them}: {hurt}.",
        "🚑 {them} [missing|without] [bodies|guys|pieces]: {hurt}.",
    ],
    "healthy": [
        "✅ {us} are healthy — nobody [important|big|key] sitting.",
        "✅ Full [squad|roster|strength] for {us}.",
        "✅ {us} have [everybody|everyone] [available|ready].",
        "✅ {us} are at full [strength|go].",
        "✅ Nobody [big|important|key] [missing|out] for {us}.",
        "✅ {us} [come in|are] [healthy|at full strength|full go].",
        "✅ [Clean|Empty] injury report [for|on] {us}.",
        "✅ {us} [got|have] [the whole squad|everyone] [available|ready|good to go].",
        "✅ No [key|big|major] [absences|injuries] for {us}.",
    ],
    "sharp": [
        "💰 [Sharp|Smart|Pro] money is on us: {us} opened {op}, now {now}.",
        "💰 The pros are [hammering|backing|loading up on] {us} — {op} at open, {now} now.",
        "💰 The line [moved|went] our way ({opnow}). [Smart money agrees.|The pros agree.]",
        "💰 Money's been [pouring|piling|flowing] in on {us}: {opnow}.",
        "💰 Big money [moved|pushed] {us} {opnow}. We like the company.",
        "💰 {us} went [from {op} to {now}|{op} → {now}] — the pros see it too.",
        "💰 {us} [opened|started] at {op} and [sit|now sit] at {now}. [Smart money agrees.|The pros agree.|Sharps see it too.]",
        "💰 Line [moved|went] our way: {us} {opnow}.",
        "💰 [Pro money|Smart money|Sharp action] [pushed|moved|took] {us} [from {op} to {now}|{op} → {now}].",
        "💰 {op} at open, {now} now — [the market's|money's] [coming our way|backing {us}].",
    ],
    "pub_ride": [
        "🤝 Riding with the [public|crowd] on {the_us} — sometimes the public gotta win, {why}.",
        "🤝 Public's on {the_us} too, and this time they're not [dummies|wrong] — {why}.",
        "🤝 Even a broken clock is right twice a day — the public got {the_us} right, {why}.",
        "🤝 We're with the crowd on {the_us} and not ashamed of it — {why}.",
        "🤝 [Public|Crowd] side on {the_us}, but we got our own reasons — {why}.",
        "🤝 We're [riding|rolling] with the crowd on {the_us}. Sometimes they get it right — {why}.",
        "🤝 [The crowd likes|Casuals like|The public likes] {the_us} [too|as well], and [this time|for once] they're right — {why}.",
        "🤝 [Same side as|Riding with] the [public|crowd] on {the_us}. [No shame|Fine by us|It happens] — {why}.",
    ],
    "cx_rival": [
        "🔥 Rivalry [game|night]. {The_us} and {the_them} got [real|deep] history.",
        "🔥 Circled on both calendars — these two don't [like|stand] each other.",
        "🔥 Straight-up rivalry. Records go out the window in these.",
        "🔥 Bad blood [game|night] — this is one of the classics.",
        "🔥 Rivalry [night|game]. No love lost between these two.",
        "🔥 [Rivalry|Grudge] [game|match]: {the_us} vs {the_them}. [Throw out the records.|History runs deep.|Emotions run hot.]",
        "🔥 {The_us} and {the_them} [can't stand|don't like] each other. [Expect a fight.|Records mean nothing.|Buckle up.]",
        "🔥 [Old|Real|Deep] rivalry — [these two|{the_us} and {the_them}] [go way back|got history].",
    ],
    "cx_rival_t": [
        "🔥 Rivalry game — {them}. Emotions run [hot|high] in these.",
        "🔥 [Classic|Old-school] rivalry on the board: {them}.",
        "🔥 Bad blood [matchup|game] ({them}). These get weird on the scoreboard.",
        "🔥 [Rivalry|Grudge] [game|matchup] ({them}). [Emotions run hot.|These get weird.|Anything goes on the scoreboard.]",
        "🔥 [History|Old beef] [on the board|in this one]: {them}.",
    ],
    "cx_div": [
        "🔥 Division game — {the_us} and {the_them} see each other every year.",
        "🔥 Division rivals. They know each other's playbook [cold|by heart].",
        "🔥 Division matchup: familiarity on both sides.",
        "🔥 It's a division game, so both sides know [exactly|just] what's coming.",
        "🔥 Division beef. No secrets between these two.",
        "🔥 Division [game|matchup]: {the_us} and {the_them} [know each other cold|have no secrets].",
        "🔥 [Same division|Division rivals] — [no secrets here|familiar faces|they know the playbook].",
        "🔥 Every season {the_us} and {the_them} [meet|see each other]. [No surprises.|Familiar stuff.]",
    ],
    "cx_div_t": [
        "🔥 Division game ({them}) — two teams that know each other [cold|well].",
        "🔥 Division matchup on the total: {them}.",
        "🔥 Familiar foes ({them}), division [game|matchup].",
        "🔥 [Familiar|Division] [foes|rivals] on the total: {them}.",
        "🔥 Division [game|matchup] ({them}) — [no surprises either way|they know each other].",
    ],
    "cx_trip": [
        "🧳 {The_them}: {fact}. That travel adds up.",
        "🧳 {Fact} for {the_them}. [Frequent flyer points, heavy legs.|Heavy legs.|Tired legs.]",
        "🧳 {The_them} living out of a suitcase — {fact}.",
        "🧳 [Travel|Mileage] check on {the_them}: {fact}.",
        "🧳 {The_them} put in the miles to get here ({fact}).",
        "🧳 [Road-weary|Heavy-travel|Long-haul] spot for {the_them}: {fact}.",
        "🧳 [Miles pile up|Travel adds up|Miles add up] for {the_them} ({fact}).",
        "🧳 {The_them} [on|in] [travel|road] mode: {fact}.",
    ],
    "cx_domecold": [
        "🏟️ Dome team outside in {wx} — {who} usually play with the thermostat set.",
        "🏟️ {Who} play indoors at home. [Tonight|Today]: {wx} outside.",
        "🏟️ No roof [tonight|today] for {who}. {Wx} in the forecast.",
        "🏟️ Indoor squad in the elements: {wx} for {who}.",
        "🏟️ [Roof's gone|No dome] for {who}: {wx} [on tap|in the forecast|at kickoff].",
        "🏟️ {Wx} [and no roof|outdoors] — [tough|rough] [ask|spot] for {who}, a dome team.",
        "🏟️ Dome team in {wx}? [Tough ask for|Rough spot for|Not ideal for] {who}.",
    ],
    "cx_domeout": [
        "🏟️ {The_them} are a dome team playing outside today.",
        "🏟️ No roof for {the_them} this time — they're used to playing [inside|indoors].",
        "🏟️ {The_them} leave the dome for an open-air [building|stadium].",
        "🏟️ Open air for an indoor team: {the_them} out of their element.",
        "🏟️ Dome team [outdoors|in open air|under the sky] today: {the_them}.",
        "🏟️ {The_them} [trade|swap] the roof for open air [today|this week].",
        "🏟️ [Out of the dome|Away from the roof], {the_them} [play outside|are in the elements] today.",
    ],
    "cx_mustwin": [
        "🚨 Must-win for {the_us} ({rec}) — right in the playoff [race|hunt].",
        "🚨 {The_us} ({rec}) are fighting for a playoff spot. Backs against the wall.",
        "🚨 Playoff race: {the_us} need this one, {the_them} don't.",
        "🚨 Every game counts for {the_us} ({rec}) right now. {The_them}? Not so much.",
        "🚨 {The_us} ({rec}) [can't afford|can't take] [an L|a loss] — playoff race.",
        "🚨 [Playoff push|Playoff chase]: {the_us} ({rec}) [need|gotta have] this one.",
        "🚨 [Season on the line|Big stakes] for {the_us} ({rec}) in the playoff [race|hunt].",
    ],
    "cx_tank": [
        "📉 {The_them} ({rec}) are out of it. Draft-pick season over there.",
        "📉 Eliminated and {rec} — {the_them} are playing for ping-pong balls.",
        "📉 {The_them} ({rec}) got nothing to play for but next year.",
        "📉 Season's over for {the_them} ({rec}), they just haven't gone home yet.",
        "📉 {The_them} ({rec}) [are done|are eliminated]. [Next year's the focus.|Eyes on the draft.]",
        "📉 [Lottery|Draft] watch: {the_them} ({rec}) are [out of it|done].",
        "📉 {rec} and eliminated, {the_them} are [playing out the string|counting down].",
    ],
    "cx_elim": [
        "📉 {The_them} are eliminated; {the_us} are still in the [race|hunt].",
        "📉 One team's playing for a spot, the other's playing out the string.",
        "📉 {The_them} are out of the playoff picture. {The_us} ain't.",
        "📉 Playoff hopes: {the_us} alive, {the_them} [done|gone].",
        "📉 {The_us} [still alive|still in it]; {the_them} [are out|are eliminated|are done].",
        "📉 Only one side [still has|still got] [playoff hopes|something to play for]: {the_us}.",
        "📉 [Stakes gap|Motivation gap]: {the_us} in the race, {the_them} [eliminated|done|out].",
    ],
    "cx_rest": [
        "🪑 {The_them} already clinched — rest-the-starters territory.",
        "🪑 Playoff spot locked for {the_them}. Don't be shocked if the [stars|starters] sit.",
        "🪑 {The_them} got their ticket punched already. Nothing to play for tonight.",
        "🪑 Clinched and coasting: {the_them} could rest [guys|starters].",
        "🪑 {The_them} [clinched already|locked their spot]. [Starters could sit.|Minutes could get managed.]",
        "🪑 [No stakes|Nothing on the line] for {the_them} — they've already clinched.",
        "🪑 [Clinched|Locked in], {the_them} [may|could] [rest|sit] [the stars|starters|key guys].",
    ],
    "cx_bowl": [
        "🏈 {us} sit at 5 wins — one more and they're bowl eligible.",
        "🏈 Bowl eligibility on the line: {us} need win [number|No.] 6.",
        "🏈 {us} are one W from a bowl game. [Extra motivation.|Big incentive.]",
        "🏈 Win 6 means a bowl [trip|bid] for {us}.",
        "🏈 {us} [are|sit] at 5 wins. [One more|Win 6] [gets|punches] a bowl [ticket|bid].",
        "🏈 [Bowl|Postseason] [bid|trip] on the line for {us} (5 wins, need 6).",
        "🏈 {us} [need|want] win [No. 6|number 6] for bowl eligibility.",
    ],
    "cx_ref": [
        "🦓 {Nm} on the whistle [tonight|today] — those games have leaned toward {what}.",
        "🦓 Zebra check: {nm_s} crew has tilted to {what} over [earlier|past] games.",
        "🦓 {Nm} officiating. The track record leans {what}.",
        "🦓 Officials matter: {nm_s} games have gone {what}'s way more than the book expected.",
        "🦓 [Ref|Officiating] [note|check|watch]: {nm_s} games [lean|tilt|trend] toward {what}.",
        "🦓 {Nm} [has the whistle|is running the game|calls this one]. [History leans|Past games lean|The record leans] {what}.",
        "🦓 [With|Under] {nm}, games [have leaned|tend to lean|have tilted] toward {what}.",
    ],
    "talk_contract_year": [
        "📣 Contract-year energy around {who} — somebody's playing for a bag.",
        "📣 {Who} got money on the line this year. Contract talk all [week|over].",
        "📣 Payday season for {who}: the contract chatter is [loud|real].",
        "📣 Incentives on the line for {who}. Expect some extra [effort|juice].",
        "📣 [Payday|Contract] [talk|chatter] around {who}: [money's on the line|incentives in play].",
        "📣 {Who} got a contract year going. [Expect extra effort.|Motivation's up.]",
        "📣 [Incentives|Bonuses] [at stake|on the line] for {who}. [Watch the effort.|Extra juice.]",
    ],
    "talk_unhappy": [
        "📣 Not everybody's happy over there — {who} got some public frustration going.",
        "📣 Grumbling in {who_s} camp this week, and it's out in the open.",
        "📣 Somebody in {who_s} building is venting to the [press|media]. Vibes are off.",
        "📣 {Who} got a frustrated voice or two talking publicly.",
        "📣 [Frustration|Grumbling] [coming out of|around] {who} [this week|lately]. [Vibes are off.|Not a happy room.]",
        "📣 {Who} got [somebody|a player] [venting|complaining] [publicly|to the press].",
    ],
    "talk_trash_talk": [
        "📣 {Who} been running their mouth this week. Bulletin-board stuff.",
        "📣 Trash talk out of {who_s} side. Somebody gotta back it up now.",
        "📣 {Who} talked a big game all week — receipts get checked [tonight|today].",
        "📣 Guarantees flying around {who}. Talk is cheap till kickoff.",
        "📣 {Who} [talked|popped off|ran their mouth] [all week|this week]. [Gotta back it up now.|Receipts tonight.]",
        "📣 [Big talk|Trash talk|Guarantees] out of {who} [this week|lately]. [Talk is cheap.|Now prove it.]",
    ],
    "talk_must_win": [
        "📣 {Who} already calling it a must-win out loud.",
        "📣 \"Must-win\" is the word around {who} this week. Backs to the wall.",
        "📣 {Who} say their season rides on this one.",
        "📣 Win-or-else talk coming out of {who} [this week|lately].",
        "📣 {Who} [calling|are calling] it a must-win [out loud|publicly].",
        "📣 [Must-win|Win-or-else] [talk|energy] [around|out of] {who} this week.",
    ],
    "talk_rivalry_week": [
        "📣 Rivalry week talk is loud around {who}. Bad blood energy.",
        "📣 {Who} been hyping the rivalry all week.",
        "📣 Bragging rights on the line, and {who} know it.",
        "📣 Circled on the calendar for {who}. No love lost here.",
        "📣 {Who} [been talking up|keep hyping] the rivalry [all week|this week].",
        "📣 [Rivalry|Bragging-rights] talk around {who}. [Bad blood energy.|No love lost.]",
    ],
    "talk_hot_seat": [
        "📣 Coach's job is a hot topic around {who}. Hot seat talk everywhere.",
        "📣 Job-security questions around {who_s} coach this week.",
        "📣 {Who_s} coach is feeling the heat in the papers.",
        "📣 The coach over at {who} is under the microscope right now.",
        "📣 [Coach's job|Job security] [talk|questions] [around|for] {who} this week.",
        "📣 {Who_s} coach [is feeling|feels] the heat [in the press|this week].",
    ],
})
T.update({
    "h2h": [
        "🆚 {us} [own|run|rule] this [matchup|series] — [won|took|grabbed] {ofl}.",
        "🆚 {us} have [had|got] {them_s} number: {ofl}.",
        "🆚 History's on our side — {ofl} went {us_s} way.",
        "🆚 {us} been [owning|handling|bullying] {them} [lately|recently] — {ofl}.",
        "🆚 {them} can't [figure|sort] {us} out: {ofl}.",
        "🆚 [Head to head|Series history|Recent meetings|The series]: {us} [took|won|grabbed] {ofl}.",
        "🆚 [{w} of the last {cnt}|{w} of their last {cnt}|{w} of the past {cnt}|{w} of the {cnt} most recent] [meetings|matchups|go-rounds] [went to|belonged to] {us}.",
        "🆚 {us} [know how to beat|have the book on|have a feel for|match up well with] {them} — {ofl}.",
        "🆚 [When these two meet|In this matchup|Head to head], {us} [usually|tend to] [win|come out on top]: {ofl}.",
        "🆚 {them} [keep losing to|struggle with|can't solve] {us} — {ofl}.",
    ],
    "h2h1": [
        "🆚 {us} got 'em [last time|the last go|in the last one]: {res}.",
        "🆚 Last [meeting|matchup|one] [went|broke] {us_s} way ({res}).",
        "🆚 {us} [handled|beat|got] {them} [last time|last go] ({res}).",
        "🆚 Last time these two met, {us} [took it|won|got it] ({res}).",
        "🆚 [Previous|Last] [meeting|matchup|go-round]: {us} [won|took it|got it] ({res}).",
        "🆚 {us} [took down|got past|got by] {them} [last time|last go] ({res}).",
        "🆚 [Most recent|The last] [meeting|matchup] [belonged to|went to] {us} ({res}).",
    ],
    "b2b": [
        "😴 {them} played [yesterday|last night] — [tired|heavy|dead] legs. {us} are [fresh|rested].",
        "😴 {them} are on a back-to-back; {us} had the [night|day] off.",
        "😴 [Short|No] rest for {them}, [full tank|fresh legs] for {us}.",
        "😴 {them} are running on [fumes|empty] — [played|suited up] last night.",
        "😴 Back-to-back for {them}. [Tired legs, cold shooting.|Heavy legs.|Dead legs.|Tired bodies.]",
        "😴 {them} [played|suited up|went] last night. {us} [didn't|sat|rested].",
        "😴 [Tired|Heavy|Dead] legs for {them} — [second night of a|on a] back-to-back.",
        "😴 Back-to-back for {them}; {us} [come in fresh|are rested|had a day off|slept in].",
    ],
    "rest": [
        "🛌 {us} had {d} more days [off|of rest] than {them}.",
        "🛌 [Rest edge|Rest advantage]: {us} got {d} extra days to [recover|reset|heal].",
        "🛌 {us} [come in|show up|walk in] with {d} more days of rest.",
        "🛌 {us} [got|had] {d} extra days to [get right|recover|reset|heal up].",
        "🛌 {d} [extra|more] days [off|of rest] for {us} — [fresh legs|fresher legs|big deal].",
        "🛌 Rest [edge|advantage] [goes to|belongs to] {us} ({d} more days).",
        "🛌 {us} [rested|sat] {d} more days than {them}.",
        "🛌 [Fresher|Fresh] legs for {us}: {d} [more|extra] days [off|of rest].",
    ],
    "bump": [
        "⚾ On the [bump|mound|hill]: {ps} for {us}, {po} for {them}.",
        "⚾ [Pitching matchup|Mound duel|Arms race]: {ps} ({us}) vs {po} ({them}).",
        "⚾ {ps} [takes|gets] the ball for {us}; {them} [go with|send|counter with] {po}.",
        "⚾ {ps} [gets|takes] the ball for {us} [against|vs] {po}.",
        "⚾ It's {ps} for {us}, {po} for {them} [tonight|today|].",
        "⚾ {ps} ({us}) [vs|against|opposite] {po} ({them}) on the [mound|hill|bump].",
        "⚾ [Starters|Arms|Mound matchup]: {ps} for {us}, {po} for {them}.",
        "⚾ {us} [send|roll with|hand it to] {ps}; {them} [counter with|go with|send] {po}.",
        "⚾ {po} [starts|goes|pitches] for {them}, {ps} for {us}.",
    ],
    "keyout": [
        "🚑 {them} are [rolling|playing|going] without their starting {pos} ({nm}).",
        "🚑 No {nm} for {them} — [that's|there goes] their starting {pos}.",
        "🚑 {them} are [down|missing|without] their starting {pos}, {nm}.",
        "🚑 {them} [lose|are missing|are without] {nm}, their starting {pos}.",
        "🚑 {nm} [is out|sits|won't play] for {them} — [that's|there goes] their starting {pos}.",
        "🚑 Starting {pos} [out|down|missing] for {them}: {nm}.",
        "🚑 [Big|Key|Huge] [absence|loss]: {them} [without|minus] {nm} (starting {pos}).",
    ],
    "banged": [
        "🚑 {them} are [hella|real|pretty] banged up ({hurt}).",
        "🚑 {them_s} injury list is [stacking up|piling up|growing]: {hurt}.",
        "🚑 {them} are missing [bodies|guys|pieces] — {hurt}.",
        "🚑 {them} are dealing with [injuries|bumps|bruises]: {hurt}.",
        "🚑 {them} are [short-handed|thin|beat up] ({hurt}).",
        "🚑 {them} [are|come in] [beat up|dinged up|thin]: {hurt}.",
        "🚑 [Injury list|Injuries|Out] for {them}: {hurt}.",
        "🚑 {them} [missing|without|minus] [bodies|guys|pieces]: {hurt}.",
    ],
    "sharp": [
        "💰 [Sharp|Smart|Pro] money is on us: {us} opened {op}, now {now}.",
        "💰 The pros are [hammering|backing|loading up on] {us} — {op} at open, {now} now.",
        "💰 The line [moved|went|slid] our way ({opnow}). [Smart money agrees.|The pros agree.|Sharps agree.]",
        "💰 Money's been [pouring|piling|flowing] in on {us}: {opnow}.",
        "💰 [Big|Smart|Heavy] money [moved|pushed] {us} [from {op} to {now}|{op} → {now}]. [We like the company.|Good company.]",
        "💰 {us} went [from {op} to {now}|{op} → {now}] — the [pros|sharps] see it too.",
        "💰 {us} [opened|started] at {op} and [sit|now sit] at {now}. [Smart money agrees.|The pros agree.|Sharps see it too.]",
        "💰 Line [moved|went|slid] our way: {us} [{op} → {now}|{op}, now {now}].",
        "💰 [Pro money|Smart money|Sharp action] [pushed|moved|took] {us} [from {op} to {now}|{op} → {now}].",
        "💰 {op} at open, {now} now — [the market's|money's] [coming our way|backing {us}].",
    ],
    "healthy": [
        "✅ {us} are healthy — nobody [important|big|key] sitting.",
        "✅ Full [squad|roster|strength] for {us} [tonight|today|].",
        "✅ {us} have [everybody|everyone] [available|ready|suited up].",
        "✅ {us} are at full [strength|go].",
        "✅ Nobody [big|important|key] [missing|out] for {us}.",
        "✅ {us} [come in|are] [healthy|at full strength|full go].",
        "✅ [Clean|Empty] injury report [for|on] {us}.",
        "✅ {us} [got|have] [the whole squad|everyone] [available|ready|good to go].",
        "✅ No [key|big|major] [absences|injuries] for {us}.",
    ],
    "latest": [
        "📅 [Latest|Last time out|Most recent|Last outing|Previous game|Fresh off|Last game|Coming off|Last results|Last go-round|Last time|Recent form]: {both}.",
        "📅 [The last one|Last one|Freshest results|Newest results|Latest scores|Last box scores|How they got here|Last time on the {field}]: {both}.",
        "📅 [Most recent games|Where they're coming from|Last week's tape|Last tape|Previous results|The latest|Their last ones|Last run out]: {both}.",
        "📅 [Last|Recent|Latest] [tape|results|scores|box scores|outings]: {both}.",
    ],
    "pub_ride": [
        "🤝 Riding with the [public|crowd] on {the_us} — sometimes the [public|crowd] gotta win, {why}.",
        "🤝 [Public's|The crowd's] on {the_us} too, and this time they're not [dummies|wrong] — {why}.",
        "🤝 Even a broken clock is right twice a day — the [public|crowd] got {the_us} right, {why}.",
        "🤝 We're with the [crowd|public] on {the_us} and not ashamed of it — {why}.",
        "🤝 [Public|Crowd] side on {the_us}, but we got our own reasons — {why}.",
        "🤝 We're [riding|rolling] with the crowd on {the_us}. Sometimes they [get it right|nail it] — {why}.",
        "🤝 [The crowd likes|Casuals like|The public likes] {the_us} [too|as well], and [this time|for once] they're right — {why}.",
        "🤝 [Same side as|Riding with] the [public|crowd] on {the_us}. [No shame|Fine by us|It happens] — {why}.",
    ],
    "splits_even": [
        "📊 Bets are [split|divided] — {t}% on {the_us}, {pt}% on {the_them} ({m}% / {pm}% of the money). Nobody knows nothing on this one, except us.",
        "📊 Who's betting who: {t}% of the bets on {the_us}, {pt}% on {the_them} ({m}% / {pm}% of the money). [Pretty split crowd.|Split room.|No herd.]",
        "📊 [Split|Divided|Mixed] [market|crowd] on {mk}: {t}% of bets on {the_us}, {pt}% on {the_them}; money {m}% / {pm}%. [Nobody's sure — we are.|No consensus.|Coin-flip crowd.]",
        "📊 {t}% [of the bets|of tickets] on {the_us}, {pt}% on {the_them} ({m}% / {pm}% of the money). [The public can't decide.|Crowd's torn.|No herd to follow.]",
        "📊 [No clear public side|Public's split|Crowd's torn] on {mk}: {the_us} {t}% of [bets|tickets] and {m}% of [money|cash], {the_them} {pt}% and {pm}%.",
    ],
    "splits_ride": [
        "📊 [Public's|The crowd's] with us on this one — {t}% of the bets and {m}% of the money on {the_us} ({mk}). Sometimes the crowd gets it right.",
        "📊 {t}% of the bets on {the_us} ({m}% of the money) on {mk}. We with the crowd [tonight|today], but we got our own reasons.",
        "📊 [Splits|The splits|Betting splits] on {mk}: {t}% of [bets|tickets] and {m}% of the money on {the_us}. [Crowd's right this time.|We agree, for our own reasons.|Same side, different reasons.]",
        "📊 {The_us} [are pulling|got] {t}% of the [tickets|bets] and {m}% of the money on {mk}. [The public's not wrong every time.|No shame riding with the crowd.|We're on it too.]",
        "📊 [The crowd|The public|Everybody] [likes|is on] {the_us} on {mk} ({t}% of bets, {m}% of money). [Fine by us — our numbers got there first.|Broken clock, right time.|We got our own reasons.]",
    ],
})
_SPLIT = {   # the public-splits line: an opener with the numbers x a closer with our stance (every window varies)
    "fade": ([
        "📊 {ptb} [and|plus|with] {pmc} [sit|are|landed|went] [on|with] {the_them} [on|for] {mk}.",
        "📊 [The whole world's|Everybody's|The public's|The crowd's|Everyone's] [on|all over|piling on] {the_them} [on|for] {mk}: {ptb}, {pmc}.",
        "📊 {The_them} [got|are pulling|draw|hold|have] {ptb} [and|plus|with] {pmc} [on|for] {mk}.",
        "📊 [Splits|The splits|Betting splits|The split] [on|for] {mk}: {the_them} [at|with|pulling] {ptb}, {pmc}.",
        "📊 [Lopsided|One-sided|Heavy|Tilted] [action|market|money] [on|for] {mk} — {ptb} [and|with] {pmc} [on|backing|riding] {the_them}.",
    ], [
        "[We fade|Fading|We're fading|We go against|We bet against] the [public|crowd|herd|sheep][ —|,] [{the_us} for us|give us {the_us}|we take {the_us}|we on {the_us}|{the_us} all day].",
        "[Sheep gon' be sheep|The herd's the herd|Let 'em follow each other] — [we on|we got|give us|we take] {the_us} [with|alongside|riding with] the other {t}%.",
        "[Not us|Nah|No thanks|Pass][,|:] [{the_us}|we're on {the_us}|we got {the_us}|{the_us} it is].",
        "[Contrarian|Classic fade|Other-side|Fade] spot — [{the_us}|give us {the_us}|{the_us} for us].",
        "",
    ]),
    "ride": ([
        "📊 {tb} [and|plus|with] {mc} [sit|are|landed|went] [on|with] {the_us} [on|for] {mk}.",
        "📊 [Public's|The crowd's|Everybody's|The herd's] [with us|on our side|riding with us] [on this one|here|tonight] — {tb}, {mc} [on|for] {mk}.",
        "📊 {The_us} [got|are pulling|draw|hold|have] {tb} [and|plus|with] {mc} [on|for] {mk}.",
        "📊 [Splits|The splits|Betting splits|The split] [on|for] {mk}: {the_us} [at|with|pulling] {tb}, {mc}.",
    ], [
        "[Crowd's|The public's|The herd's] [right|onto something|not wrong] [this time|for once|tonight].",
        "[We got|We have|We bring] our own [reasons|read|numbers] [though|anyway|too].",
        "[Same side|Same pick|Same team], [different|our own|separate] [reasons|math|read].",
        "[Sometimes|Every now and then|Once in a while] the [crowd|public] [gets it right|nails one|hits].",
        "",
    ]),
    "even": ([
        "📊 [Bets are|The action's|Tickets are|The betting's] [split|divided|mixed] — {t}% [on|for] {the_us}, {pt}% [on|for] {the_them} ({m}% / {pmc}).",
        "📊 [Who's betting who|The split|Betting breakdown|The breakdown]: {tb} [on|for|backing|riding] {the_us}, {pt}% [on|for|backing|riding] {the_them}; [money|cash|dollars] {m}% / {pm}%.",
        "📊 [No clear public side|Public's split|Crowd's torn|No lean from the public] [on|for] {mk}: {the_us} [at|with] {tb} and {mc}, {the_them} {pt}% and {pm}%.",
    ], [
        "[Nobody|No one] [knows|agrees|has a clue] [on this one|here|tonight] — [except us|we do|we know].",
        "[Pretty|Real|Dead] [split|torn|even] [crowd|room|market].",
        "[No herd|No consensus|No crowd] to [follow|fade|ride].",
        "",
    ]),
}
for _k, (_o, _c) in _SPLIT.items():
    T["splits_" + _k] = T["splits_" + _k][:3] + [f"{o} {c}".strip() for o in _o for c in _c]

_DENSE = {   # skeletons with a pick in every 4-word window: they can come back day after day in new words
    "fade": [
        "💸 [Sharp money's|Big money's|The money's|Action's] [pouring|piling|flowing|coming] [in on|onto|toward] {the_them}{move}. [Let 'em|Not buying it|Respectfully, no|Cool with us|We pass] — [we're on|we got|we're riding|give us] {the_us}, {why}.",
        "💸 [The line's|The number's|The market's|The price is] [moving|drifting|sliding|leaning] [toward|to] {the_them}{move}. [They must be clowns|Somebody's tweaking|Wrong way|Somebody's gonna learn] — [we're on|we got|we're with|we ride] {the_us}, {why}.",
        "💸 {The_them}{move} [are getting|keep getting|are soaking up|pull] [the|all the|most of the] [sharp|big|heavy] money. [Fine by us|We fade it|Let 'em|Cool] — [we're on|we got|give us] {the_us}, {why}.",
        "💸 [So-called sharps|Wise guys|Big bettors|The pros] [love|backed|jumped on|hit] {the_them}{move}. [Clowns|Their loss|Not us|We disagree] — [we're on|we got|we're riding] {the_us}, {why}.",
    ],
    "pub_fade": [
        "🤡 [The public's|The crowd's|Casual money's|Square money's|The sheep are] [all over|piling on|lined up for|in love with] {the_them}. [Let 'em|Not us|Cool story|We pass|Fine] — [we're on|we got|we're riding|give us] {the_us}, {why}.",
        "🤡 {The_them} [are|look like] the [popular|public|people's|trendy] [pick|side|play]. [We fade the crowd|We go the other way|Not for us|We pass] — [{the_us}|we got {the_us}|give us {the_us}], {why}.",
        "🤡 [Everybody and their mama|Every casual|The whole timeline|All the squares] [on|backing|riding] {the_them}? [Nah|Nope|Not us|Pass] — [we're on|we got|we're riding] {the_us}, {why}.",
        "🤡 [Don't be a sheep|Don't follow the herd|Don't chase the crowd|Skip the herd]: [the public's|the crowd's|the squares are] on {the_them}, [we're on|we got|we ride] {the_us} — {why}.",
    ],
    "pub_ride": [
        "🤝 [Same side as|Riding with|Rolling with|On the same side as] the [public|crowd|herd] [on|with] {the_us}. [No shame|Fine by us|It happens|So be it] — {why}.",
        "🤝 [The crowd's on|The public's on|Casuals are on|The squares are on] {the_us} [too|as well|here], and [this time|for once|tonight] they're [right|onto something|not wrong] — {why}.",
        "🤝 [Even a broken clock|A stopped clock|The public] [hits|gets one right|is right] [sometimes|twice a day|now and then]: {the_us}, {why}.",
    ],
    "worse": [
        "🐺 [Sure|Yeah|Fine|OK], {them} [look|grade out|rate] [better|stronger] on paper. [That's|It's|All that's] [baked in|in the price|priced in] — [we like|give us|we'll take] {us} [here|at this number|at this price].",
        "🐺 {them} [get|grab|soak up] [all the|the] [love|hype|respect|headlines]; {us} [get|come with] the [price|number|value]. [We'll take that.|Easy choice.|Say less.]",
        "🐺 [On paper it's {them}|The resume says {them}|The names say {them}]. [The price|This number|The value] [favors|points to|says] {us} — [and we follow the price|we listen to the price|price wins].",
        "🐺 [Price spot|Value spot|Number spot]: {them} [have|got|bring] the [names|resume|hype], we [have|got|take] the [number|price|value] [on|with] {us}.",
    ],
    "home": [
        "🏟️ {us} [at home|in their building|on home {field}|at the crib] {tn}. [{Crowd}|Their people|The home folks] [gonna be|will be] [loud|rocking|behind them|on their side].",
        "🏟️ [Home|Crib|Home-{field}] [game|night|spot] for {us}. [Friendly|Familiar|Their own] [building|crowd|surroundings], [their rules|their energy|their routine].",
        "🏟️ {us} [sleep|stay|rest up] in their own [beds|house|place] {tn} — [home|familiar|friendly] [crowd|building|routine] [behind them|on their side|at their back].",
    ],
    "road": [
        "🧳 {us} [travel|go on the road|hit the road|pack the bags] {tn}. [Doesn't worry us.|Not a concern.|We don't care.|No big deal.]",
        "🧳 [Road|Away] [spot|trip|game] for {us} — [the numbers still like them|still our side|still the play|doesn't change a thing].",
        "🧳 {us} [play|are|suit up] in a [hostile|loud|road|rowdy] [building|barn|house] {tn}, [and|but] [that's fine|we're cool with it|who cares].",
        "🧳 [Hostile|Loud|Rowdy] [building|crowd] [waiting|ahead|on deck] for {us}. [Don't care.|Doesn't matter.|We're good.]",
    ],
    "rest": [
        "🛌 {us} [got|had|enjoyed] {d} [more|extra] days [off|of rest|to recover] [than|compared to] {them}.",
        "🛌 [Rest|Legs|Recovery] [edge|advantage|gap]: {us} [by|with] {d} [days|extra days|more days].",
        "🛌 {them} [had|got] {d} fewer days [off|of rest] [than|compared to] {us}.",
    ],
    "b2b": [
        "😴 {them} [played|suited up|were out there] last night; {us} [rested|sat|had the night off|kicked back].",
        "😴 [Second night of a back-to-back|Back-to-back spot|No rest] for {them}. {us} [come in|walk in|show up] [fresh|rested|with fresh legs].",
    ],
    "better_s": [
        "💪 {us} [grade out|rate|come out] [a bit|a little|slightly|a touch] [better|stronger|higher] [on paper|on talent|overall].",
        "💪 [Slight|Small|Modest] [talent|roster|quality] [edge|advantage] [to|for] {us} [over|against] {them}.",
    ],
    "even": [
        "⚖️ [Talent's|Rosters are|Paper's] [about even|a wash|dead level|split] — [so|and] the [number|price|value] [picks|makes|decides] the [side|play|pick].",
        "⚖️ [Can't split|Can't separate|Hard to split] [these two|them|this one] on [paper|talent]; [the price|the number] [does it|breaks it|decides] for us.",
    ],
    "revenge": ["😤 {us} [dropped|lost|blew] the last [one|meeting|matchup] [to|against] {them}. [Payback|Get-back|Revenge] [time|spot|game]."],
    "letdown": ["🪤 {them} [just|recently] [blew out|ran over|smacked|rolled] [somebody|a team|their last opponent]. [Letdown|Trap|Hangover|Flat] [spot|alert|game] [here|now|tonight]."],
    "momentum": ["🚀 {us} [blew out|smoked|ran over|rolled] [somebody|a team|their last opponent] [last time|last game|last out]. [Momentum|Confidence|Juice] [carries|stays|is real]."],
    "alt": ["🏔️ [Thin|Light|Mountain] air [at|up at] {elev} meters — [lungs|legs|gas tanks] [burn|go|drain] [fast|quick|early] for {the_them}."],
    "cold_w": ["🥶 [Freezing|Frigid|Cold] [night|game|one]: {temp}°F. {The_them} [won't like it|ain't built for it|are out of their element]."],
    "G_hot": ["🧱 [Nothing|Not much|Barely anything] [getting|going|sneaking] [past|by] {name} {rn}: {txt}."],
    "intl": ["🌍 [Overseas|International|Neutral-site] [game|trip|spot] ({where}). {Algo} [wanted|needed|demanded] [extra|more|a bigger] [value|cushion|edge] [to take it|to play it|for it]."],
    "cx_div_t": ["🔥 [Division|Familiar|Same-division] [game|matchup|foes] [on the total|here|in this one]: {them}."],
    "cx_div": ["🔥 [Division|Same-division|Familiar] [game|matchup|beef]: {the_us} and {the_them} [know each other cold|have no secrets|see each other a lot]."],
    "cx_rival_t": ["🔥 [Rivalry|Grudge|Bad-blood] [game|matchup|spot] ({them}). [Emotions run hot.|These get weird.|Anything goes.]"],
    "cx_domecold": ["🏟️ [Dome|Indoor|Roof] [team|squad|club] [outside|outdoors|in the elements] [in|with] {wx} — [tough|rough|bad] [spot|ask|look] for {who}."],
    "cx_domeout": ["🏟️ [Dome|Indoor|Roof] [team|squad|club] [outdoors|in open air|under the sky] [today|this time|this week]: {the_them}."],
    "cx_bowl": ["🏈 [Bowl|Postseason] [eligibility|ticket|bid] [on the line|at stake|in play] for {us}: [win|W] [No. 6|number 6|six] [gets it|punches it|does it]."],
    "cx_elim": ["📉 [Stakes|Motivation|Urgency] [gap|edge]: {the_us} [alive|in the race|still in it], {the_them} [eliminated|done|out]."],
    "cx_hotseat": ["🔥 [Heat's|Pressure's|Spotlight's] on {the_them_s} [coach|staff|sideline] [after|with] {cnt} [straight|consecutive] {Ls}."],
    "cx_mustwin": ["🚨 [Playoff|Postseason] [push|chase|race]: {the_us} ({rec}) [need|gotta have|can't lose] this one."],
    "cx_rest": ["🪑 [Clinched|Locked in|Spot secured], {the_them} [may|could|might] [rest|sit|limit] [the stars|starters|key guys]."],
    "cx_tank": ["📉 [Lottery|Draft|Tank] [watch|season|mode]: {the_them} ({rec}) [are out of it|are done|are playing for next year]."],
    "drama_legal_trouble": ["🧯 [Legal|Court|Off-field] [stuff|noise|mess] [around|for|hanging over] {the_them} [this week|lately|right now]. [Distractions.|Hard to focus.|Noise.]"],
    "drama_trade_drama": ["🧯 [Trade|Trade-request|Wants-out] [noise|drama|talk] [around|for] {the_them} [this week|lately|right now]. [Awkward room.|Vibes are off.|Messy.]"],
    "drama_family_personal": ["🧯 [Tough|Heavy|Rough] [week|stretch|time] [off the field|away from the game|personally] for {the_them}. [Hard to focus.|Heads elsewhere.|Tough spot.]"],
    "drama_suspension": ["🧯 [Suspension|Discipline] [news|drama|hit] [for|around] {the_them} [this week|lately]. [That hurts.|Tough week.|Rattles a room.]"],
    "talk_must_win": ["📣 [Must-win|Win-or-else|Season-saving] [talk|energy|vibes] [around|out of|from] {who} [this week|all week|lately]."],
    "talk_contract_year": ["📣 [Contract year|Payday season|Money talk] [around|for] {who}. [Extra effort|Motivation|Hunger] [expected|incoming|on tap]."],
    "talk_hot_seat": ["📣 [Coach's job|Job security] [talk|chatter|questions] [around|for] {who} [this week|lately|all week]."],
    "talk_rivalry_week": ["📣 [Rivalry|Bragging-rights|Grudge] [talk|chatter|hype] [around|from|out of] {who} [this week|all week|lately]."],
    "talk_trash_talk": ["📣 [Big talk|Trash talk|Chirping] [out of|from|around] {who} [this week|lately|all week]. [Talk is cheap.|Now prove it.|Receipts tonight.]"],
    "talk_unhappy": ["📣 [Frustration|Grumbling|Unhappy noise] [coming out of|around|inside] {who} [this week|lately|all week]. [Vibes are off.|Not a happy room.|Tension.]"],
}
for _k, _v in _DENSE.items():
    T[_k] = T[_k] + _v


_SYN = [   # a few safe swaps applied everywhere outside the picks: more ways, same meaning, same size
    (r"\blately\b", "[lately|recently|of late]"), (r"\btonight\b", "[tonight|today]"),
    (r"\bthis week\b", "[this week|all week]"), (r"\ball week\b", "[all week|this week]"),
    (r"\bsquad\b", "[squad|team|side]"), (r"\bguys\b", "[guys|players|bodies]"), (r"\bright now\b", "{rn}"),
    (r"\bthese two\b", "[these two|these teams]"), (r"\ba big W\b", "[a big W|a big win|a statement win]"),
    (r"\b(tired|heavy|dead) legs\b", "[tired|heavy|dead] legs"), (r"\breally\b", "[really|truly]")]


def _syn(t):
    parts = re.split(r"(\[[^\]]*\]|\{\w+\})", t)          # leave the picks and slots alone
    for i in range(0, len(parts), 2):
        for pat, rep in _SYN:
            parts[i] = re.sub(pat, rep, parts[i])
    return "".join(parts)


T = {k: [_x(_syn(t)) for t in v] for k, v in T.items()}
