"""THE MAIN-BOARD BREAKDOWN VOICE (restored 9/29 - the owner: the vocabulary rewrite came out vague and not our lingo).
The full breakdown behind a pick: the facts the engine weighed, in plain words, frozen at posting time.
Shown on the dashboard behind a "Full breakdown" tap."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import re
import sports_data as sd
import sports_lingo
import sports_model as sm
import sports_players as sp

PT = ZoneInfo("America/Los_Angeles")
VERSION = 24          # bump when the wording changes: posted plays get their breakdown rewritten (never the pick)


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


def seen_all(fin, tid, before, lg):
    """Do we hold every game this team has played this season? Pro leagues: yes. College: only when its game count this
    season is near the most-covered teams' (the feed misses games between small schools) - else its record is a guess."""
    if lg not in ("ncaaf", "ncaab"):
        return True
    cut = before - timedelta(days=sm.BREAK_DAYS)
    season = [g for g in fin if _t(g["start"]) > cut]
    if not season:
        return True
    n = {}
    for g in season:
        for t in (g["home"], g["away"]):
            n[t] = n.get(t, 0) + 1
    ref = sorted(n.values())[int(0.97 * (len(n) - 1))]   # (10/2 audit: the 90th percentile sank with the missing
    #                                                     games themselves - 4 instead of 5 - and let 0-4 Mercyhurst through)
    need = ref - 1 if lg == "ncaaf" else 0.8 * ref
    if n.get(tid, 0) >= need:
        return True
    if lg != "ncaaf" or not n.get(tid):                  # (10/2, the owner: the check blocked Penn State-Northwestern -
        return False                                     #  a Big Ten team that started a week late + had a bye: 3
    mine = sorted(_t(g["start"]) for g in season if tid in (g["home"], g["away"]))   # games, all of them) - judged by
    first0 = min(_t(g["start"]) for g in season)         # its OWN calendar: one game a week since its first, one bye
    if (mine[0] - first0).days > 9:                      # allowed - only when its opener is in our data (never a team
        return False                                     # whose first games might be the missing ones)
    weeks = -(-(before - mine[0]).days // 7)             # weekly slots since its first game (ceiling)
    return len(mine) >= weeks - 1


def _pos(name):
    """'UNLV' -> "UNLV's", 'Steelers' -> "Steelers'" (10/1 audit: "went UNLV' way")."""
    return f"{name}'" if name.endswith("s") else f"{name}'s"


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


SHORT_L = ["Book it.", "Lock it in.", "Stamp it.", "Say less.", "Easy money.", "Trust the algorithm.", "We locked in.",
           "All day.", "No doubt.", "Bank it.", "Cash it.", "Done deal."]
SHORT_S = ["Tap in.", "Get in.", "We finna see.", "We gon' see.", "Right side.", "Smart side.", "Good number.", "Say less.",
           "We like it.", "Ride it.", "Let it ride.", "Easy call."]


def _short(v, price, lock, fact=""):
    """Every full bottom line is used on this board or yesterday's: the pick + a short closer (too short to repeat a
    phrase), a closer not used yet on this board."""
    pool = SHORT_L if lock else SHORT_S
    for i in range(len(pool)):
        c = pool[(sum(map(ord, v.seed)) + i) % len(pool)]
        if f"short:{c}" not in v.used:
            v.used.add(f"short:{c}")
            return f"✅ Bottom line: {price}. {fact} {c}".replace("  ", " ")
    return f"✅ Bottom line: {price}. {fact}".rstrip()


POSNAME = {"G": "goalie", "QB": "quarterback", "SP": "starting pitcher", "LW": "left wing", "RW": "right wing",
           "C": "center", "D": "defenseman", "PG": "point guard", "SG": "shooting guard", "SF": "small forward",
           "PF": "power forward", "RB": "running back", "WR": "receiver", "TE": "tight end", "K": "kicker"}


POSNAME_LG = {   # (10/1, the owner: "the Browns are playing without the goalie?" - a football G is a GUARD) by sport
    "nfl": {"G": "guard", "C": "center", "T": "tackle", "OT": "tackle", "OG": "guard", "OL": "lineman", "DE": "defensive end",
            "DT": "defensive tackle", "DL": "defensive lineman", "LB": "linebacker", "CB": "cornerback", "S": "safety",
            "FS": "safety", "SS": "safety", "P": "punter", "LS": "long snapper", "FB": "fullback"},
    "nba": {"G": "guard", "F": "forward", "C": "center"},
    "nhl": {"G": "goalie", "C": "center", "D": "defenseman"},
    "mlb": {"C": "catcher", "RP": "reliever", "1B": "first baseman", "2B": "second baseman", "3B": "third baseman",
            "SS": "shortstop", "LF": "left fielder", "CF": "center fielder", "RF": "right fielder", "DH": "designated hitter"}}
POSNAME_LG["ncaaf"], POSNAME_LG["ncaab"] = POSNAME_LG["nfl"], POSNAME_LG["nba"]


def _posname(pos, lg=None):
    """'G' -> 'goalie' in hockey, 'guard' in football / hoops - a sentence never says just the letters (the owner, 9/29:
    'the backup G' confused everybody), and never the wrong sport's word (10/1: a Browns guard became a 'goalie')."""
    k = str(pos or "").upper()
    if lg in POSNAME_LG and k in POSNAME_LG[lg]:
        return POSNAME_LG[lg][k]
    if lg is not None and lg != "nhl" and k == "G":
        return "guard"
    return POSNAME.get(k, str(pos or ""))


def _poss(team):
    """'the Canucks' -> "The Canucks'", 'Duke' -> "Duke's" (whose goalie it is)."""
    t = team[:1].upper() + team[1:]
    return t + "'" if t.endswith("s") else t + "'s"


class Voice:
    """Picks a way to say each line: different wording from game to game and day to day, and never the same
    wording twice on one board (share one `used` set across a board's breakdowns)."""

    def __init__(self, seed, used=None):
        self.seed, self.used, self.mine = seed, used if used is not None else set(), []
        self.names = ()

    def say(self, key, options, must=False, names=()):
        """A fresh way to say it, or "" (the line is dropped) when every way is already taken on this board.
        must=True: a line the card can't go without (the pick, the bottom line) - reuse a wording rather than drop it.
        Our big phrases ("cheeks clapped", "smack that ass"...) show up once a board, never on two cards in a row."""
        start = sum(map(ord, f"{self.seed}|{key}")) % len(options)
        order = [(start + i) % len(options) for i in range(len(options))]
        def slang(x):
            out = [f"slang:{k}" for k, pat in SLANG.items() if re.search(pat, x.lower())]
            if names:                                         # mixer lines: every opener / ending once a board
                t = x
                for nm in names:
                    t = t.replace(nm, "_").replace(nm[:1].upper() + nm[1:], "_")
                out += [f"piece:{p.strip().lower()}" for p in re.split(r"(?<=[.!?])\s+", re.sub(r"^\W+", "", t)) if p.strip()]
            return out
        import sports_breakdown as _sb                        # no 4-word run from this board or the last days' boards
        runs = lambda x: _sb.grams(x, tuple(names) + tuple(self.names))   # (the same memory the vocabulary uses)
        unused = [n for n in order if f"{key}:{n}" not in self.used]
        fresh = [n for n in unused if not any(s in self.used for s in slang(options[n]))
                 and not (runs(options[n]) & self.used)]
        if fresh:
            n = fresh[0]
        elif not must:
            return ""                                         # every fresh way repeats a phrase: drop the line
        else:                                                 # must say it: the wording that repeats the fewest phrases
            n = min(unused or order, key=lambda i: sum(s in self.used for s in slang(options[i]))
                    + len(runs(options[i]) & self.used))
        self.used.add(f"{key}:{n}")
        self.used.update(slang(options[n]))
        self.used.update(runs(options[n]))
        self.mine.append(f"{key}:{n}")
        return re.sub(r"(?<!\.)\.\.(?!\.)", ".", options[n])   # "Bain Jr.." -> "Bain Jr."


HYPE = re.compile(r"trust the algorithm|lock it in|free money|easy money|hammer it|hammer time|smash it|we eating|real edge|"
                  r"tips it our way|let'?s eat|bag|money energy|can'?t lose|guaranteed", re.I)


VET_STARTS = {"QB": 100, "SP": 200, "G": 350}   # "washed" (the owner, 10/1) only for a long-time starter: this many
#                                                  starts in our box scores (2016 on - a QB's 100 = 6+ full seasons)
OLD_PID = 20000     # ...AND old: ESPN's player id under 20,000 = in the league by 2012 (Rodgers 8439, Stafford 12483 -
#                     Mahomes 3139477, Goff 3046779). The 10/2 audit: starts alone called a cold prime-age star "washed".
#                     No age for pitchers / goalies on file - so "washed" is QBs only (never false information).
_PIDS = {}


def old_qb(name):
    """A QB whose career started by 2012 (ESPN id under OLD_PID, from our NFL rosters)."""
    if "m" not in _PIDS:
        import csv
        import glob
        import gzip
        import os
        m = {}
        for f in sorted(glob.glob(os.path.join(sd.DATA, "roster", "nfl_*.csv.gz")))[-2:]:
            try:
                with gzip.open(f, "rt", newline="") as fh:
                    for r in csv.DictReader(fh):
                        if r.get("group") == "passing" and r.get("player") and str(r.get("pid") or "").isdigit():
                            m[r["player"]] = int(r["pid"])
            except (OSError, EOFError, ValueError):
                continue
        _PIDS["m"] = m
    pid = _PIDS["m"].get(name)
    return pid is not None and pid < OLD_PID


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
    import sports_breakdown as _sb
    team = leg.get("team", "")
    ends = _sb.lean_ends(leg)                       # (10/1, the owner: the real reason - a coin flip or the price)
    out.append(ends[sum(map(ord, str(seed) + team)) % len(ends)])
    return out


def breakdown(leg, games, elo, injuries, used=None):
    """A plain-talk case for one leg: a list of short bullets ending with the bottom line."""
    g = games[leg["game_id"]]
    lg, side = leg["league"], leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg["team"], leg["opp"]
    start = _t(g["start"])
    fin = [x for x in sm.finals(games, lg) if _t(x["start"]) < start]
    ours, theirs = _team_games(fin, tid), _team_games(fin, oid)
    if not seen_all(fin, tid, start, lg):            # (10/1, the owner: never false info) we don't hold all of a college
        ours = []                                    # team's games this year: no record, streak, last game or series
    if not seen_all(fin, oid, start, lg):            # from half the picture ("North Texas 0-1" when we had 1 game)
        theirs = []
    s_ours, s_theirs = _season(ours, start), _season(theirs, start)
    # (10/1 audit) a RECORD is regular-season games only ("Yankees 95-68" counted 2 playoff wins - really 93-68), and a
    # streak / last game is this season's, never last year's ("Vikings 3-0 ... won 8 straight")
    r_ours = [x for x in s_ours if str(x.get("stype") or "2") == "2"]
    r_theirs = [x for x in s_theirs if str(x.get("stype") or "2") == "2"]
    v = Voice(f"{g['id']}|{start:%Y-%m-%d}|{side}", used)
    v.names = (us, them)                                  # team names blanked when comparing wordings to yesterday's
    pro = lg in ("nfl", "nba", "mlb", "nhl")
    the_us, the_them = (f"the {us}", f"the {them}") if pro else (us, them)
    if ours and theirs and (start - _t(ours[-1]["start"])).days - (start - _t(theirs[-1]["start"])).days < 2:
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "better rested"]
    if (sm._num(g.get("elev")) or 0) < sm.THIN_AIR_M:  # "altitude edge" only means something up in real thin air
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "altitude edge"]
    out, said = [], set()          # said: reasons already used as a "because", so no line repeats another
    leg["bd_tags"] = v.mine        # which wordings this breakdown used (so the rest of the board avoids them)
    FORM = {}                      # (ours?, "hot"/"cold") -> (starter, his numbers) for the card's "why"
    rec_t = gap = None
    n_cold = 0

    # form
    rec_u = _record(r_ours, tid) if r_ours else None
    heat = _streak(s_ours, tid)
    n_hot = int(heat.split()[1]) if heat.startswith("won") else 0
    heat_t = _streak(s_theirs, oid)                 # (10/2, the owner: "Virginia Tech, four straight W's, we don't go
    their_hot = int(heat_t.split()[1]) if heat_t.startswith("won") else 0   # against a heater - well, the other team
    if n_hot >= 2 and their_hot >= n_hot:                                    # has four straight W's"): both hot = say
        said.add("hotter recent form")                                       # both, never "the heater's ours"
        out.append(v.say("bothhot", [f"🔥 Both teams are rolling: {us} have won {n_hot} straight, {them} {their_hot}.",
                                      f"🔥 Heater vs heater - {us} {n_hot} straight W's, {them} {their_hot}.",
                                      f"🔥 Neither team has lost lately: {us} {n_hot} in a row, {them} {their_hot}."]))
        n_hot = 0                                                             # (no 'hot hand' line in the why either)
    elif rec_u and n_hot >= 2:
        said.add("hotter recent form")
        out.append(v.say("hot", [f"🔥 {us} are {rec_u} and on a {n_hot}-game heater.",
                                  f"🔥 {us} ({rec_u}) have won {n_hot} straight and they're rolling.",
                                  f"🔥 {us} are rolling — {n_hot} wins in a row, {rec_u} on the year.",
                                  f"🔥 {us} can't stop winning: {n_hot} straight, {rec_u} overall.",
            f"🔥 {us} are cooking — {n_hot} straight W's, {rec_u} overall.",
            f"🔥 Heat check: {us} have won {n_hot} in a row ({rec_u})."]))
    elif rec_u:
        out.append(v.say("rec", [f"📋 {us} sitting at {rec_u} on the year.",
                                  f"📋 Record check: {us} {rec_u}. We already did our homework.",
                                  f"📋 {rec_u} so far for {us} — the record don't cash tickets, the number does.",
            f"📋 {us} rolling in at {rec_u}.",
            f"📋 {us} got a {rec_u} record walking in. We gon' see what they do with it.",
            f"📋 {us} are {rec_u} right now — the rest is on the field."]))
    if r_theirs:
        rec_t = _record(r_theirs, oid)
        cold = _streak(s_theirs, oid)
        n_cold = int(cold.split()[1]) if cold.startswith("lost") else 0
        w_t = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        rating_t = elo[lg].r.get(oid, 1500.0) if elo.get(lg) is not None else 1500.0
        trash = (len(r_theirs) >= 3 and w_t / len(r_theirs) < 0.35) or n_cold >= 3 or rating_t < 1420
        if elo.get(lg) is not None and elo[lg].r.get(tid, 1500.0) <= rating_t:
            trash = False                                # (no 'cold' dig either when the ratings don't have us better)
            n_cold = n_cold if n_cold < 2 else 0
        if n_cold >= 2 and not trash:                   # the trash-talk line below covers the really bad ones
            out.append(v.say("cold", [f"🧊 {them} are {rec_t} and ice cold — {n_cold} straight L's.",
                                       f"🧊 {them} have dropped {n_cold} in a row ({rec_t}).",
                                       f"🧊 {n_cold} straight losses for {them}. Not a good look.",
                                       f"🧊 {them} ({rec_t}) keep taking L's — {n_cold} straight.",
            f"🧊 {them} ({rec_t}) are in a slump — {n_cold} straight.",
            f"🧊 {them} forgot how to win: {n_cold} straight L's."]))

    # strength
    e = elo.get(lg)
    if e is not None:
        home_edge = 0 if str(g.get("neutral")) == "1" else (e.hfa if side == "home" else -e.hfa)
        gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0) + home_edge      # same yardstick as the card's reasons
        said.add("the stronger team")                   # said here either way (better / even / worse): not again later
        _ru = _record(r_ours, tid) if r_ours else None
        _rt = _record(r_theirs, oid) if r_theirs else None
        if _ru and _rt:                                  # (10/1, the owner: "they're just better" says nothing -
            _w = lambda r: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in r.split("-")[:2]])
            if gap > 15 and _w(_ru) > _w(_rt):           # the records do)
                out.append(v.say("better", [f"💪 {us} ({_ru}) vs {them} ({_rt}) — the better team is on our side.",
                                             f"💪 {_ru} against {_rt}: {us} been the better team.",
                                             f"💪 Records say it: {us} {_ru}, {them} {_rt}.",
                                             f"💪 {us} {_ru}, {them} {_rt}. Better squad on our side."]))
            elif gap < -15 and _w(_rt) > _w(_ru):
                out.append(v.say("worse", [f"🐺 {them} ({_rt}) look better than {us} ({_ru}) — that's why the price is this good.",
                                            f"🐺 {_rt} vs {_ru} — {them} get the respect, we get the price on {us}.",
                                            f"🐺 {them} are {_rt}, {us} {_ru}. The record's in the price already."]))
            elif abs(_w(_ru) - _w(_rt)) <= 0.15 and gap > 15:   # same-ish records, but the ratings (who they PLAYED)
                tough = [x for x in r_ours if _line(x, tid).startswith("L")]   # say we're better - name who beat us
                names = [x.get("away_name") if x.get("home") == tid else x.get("home_name") for x in tough][-3:]
                if names:
                    nm = ", ".join(names[:-1]) + (" and " if len(names) > 1 else "") + names[-1]
                    out.append(v.say("sched", [f"⚖️ {us} {_ru}, {them} {_rt} — but {_pos(us)} L's came against {nm}.",
                                               f"⚖️ Same kind of record, tougher schedule: {us} lost to {nm}.",
                                               f"⚖️ Don't let {_ru} fool you — {us} took those L's from {nm}."]))
            elif abs(_w(_ru) - _w(_rt)) <= 0.15 and abs(gap) <= 15:   # records AND ratings close: a coin-flip game
                out.append(v.say("even", [f"⚖️ {us} {_ru}, {them} {_rt} — about even, so the price makes the play.",
                                           f"⚖️ {_ru} vs {_rt}. Close matchup — the number's where the value is.",
                                           f"⚖️ Records are close ({us} {_ru}, {them} {_rt}). We're taking the side that pays."]))

    # talk our talk when the other side's been bad (only when the numbers back it up)
    if r_theirs:
        w = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        rating_them = e.r.get(oid, 1500.0) if e is not None else 1500.0
        n_cold = int(_streak(s_theirs, oid).split()[1]) if _streak(s_theirs, oid).startswith("lost") else 0
        better = e is None or e.r.get(tid, 1500.0) > rating_them   # (10/1, the owner: a record doesn't show who they
        if better and ((len(r_theirs) >= 3 and w / len(r_theirs) < 0.35) or n_cold >= 3 or rating_them < 1420):
            #   played - trash talk only when the engine's ratings, which count the schedule, have us better)
            rec = _record(r_theirs, oid)
            out.append(v.say("trash", [f"🗑️ {them} have been complete ass lately — {rec} and it ain't getting prettier.",
                                        f"🗑️ Straight up, {them} are trash right now ({rec}).",
                                        f"🗑️ {them} can't get out of their own way ({rec}).",
                                        f"🗑️ {them} are a mess right now. {rec} says it all.",
                                        f"🗑️ Nothing about {them} scares us ({rec}).",
            f"🗑️ {them} been looking like a JV squad ({rec}).",
            f"🗑️ {them} are straight garbage right now ({rec}).",
            f"🗑️ Watching {them} lately hurts ({rec}).",
            f"🗑️ {them} are about to get their cheeks clapped. {rec} — they been complete ass.",
            f"🗑️ {rec} lately. {them} are complete ass and it shows."]))

    # last games: just the latest scores - and only when they back the pick (the owner, 9/30: "Kings L 1-5 vs Avalanche"
    # in the Kings' breakdown makes no sense - we won our last one, and they lost theirs or had none)
    if s_ours and _line(s_ours[-1], tid).startswith("W") and (not s_theirs or _line(s_theirs[-1], oid).startswith("L")):
        last_us = _line(s_ours[-1], tid)                  # (this season's last game - never last year's)
        both = f"{us} {last_us}" + (f" · {them} {_line(s_theirs[-1], oid)}" if s_theirs else "")
        out.append(v.say("latest", [f"📅 Latest: {both}.", f"📅 Last time out: {both}.", f"📅 Most recent games: {both}.",
                                     f"📅 Where they're coming from: {both}.", f"📅 Last week's tape: {both}." if lg in ("nfl", "ncaaf")
                                     else f"📅 Last outing: {both}.", f"📅 Previous game: {both}.", f"📅 Fresh off: {both}."]))

    # head to head
    h2h = [x for x in ours if oid in (x["home"], x["away"])]
    if h2h:
        last3 = h2h[-3:]
        w = sum(1 for x in last3 if _line(x, tid).startswith("W"))
        if 2 * w > len(last3) and len(last3) > 1:          # (10/1 audit: 1 of 2 isn't "owning" anybody)
            out.append(v.say("h2h", [f"🆚 {us} own this matchup — won {w} of the last {len(last3)}.",
                                      f"🆚 {us} have had {them}'s number: {w} of the last {len(last3)}.",
                                      f"🆚 History's on our side — {w} of the last {len(last3)} meetings went {_pos(us)} way.",
            f"🆚 {us} been owning {them} lately — {w} of the last {len(last3)}.",
            f"🆚 {them} can't figure {us} out: {w} of {len(last3)} to {us}."]))
        elif w == 1 and len(last3) == 1:
            out.append(v.say("h2h1", [f"🆚 {us} got 'em last time: {_line(h2h[-1], tid)}.",
                                       f"🆚 Last meeting went {_pos(us)} way ({_line(h2h[-1], tid)}).",
            f"🆚 {us} handled {them} last time ({_line(h2h[-1], tid)}).",
            f"🆚 Last time these two met, {us} took it ({_line(h2h[-1], tid)})."]))

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
            FORM[(ours_, mood)] = (name, txt)                 # (the card's one-line "why" can use it)
            vet = role == "QB" and old_qb(name) and \
                sum(r["player"] == name and r["start"] < g["start"] for r in rows) >= VET_STARTS["QB"]
            if not ours_ and mood == "cold" and vet:          # (the owner, 10/1: "this dude is washed - old, out of his
                out.append(v.say(role + "_washed", [          #  prime") - only a long-time starter who's cold NOW
                    f"🧓 {name} is washed — {txt}.",
                    f"🧓 {name} looks washed: {txt}.",
                    f"🧓 Father Time is catching {name} — {txt}. Washed."]))
            elif not ours_ and mood == "cold":
                out.append(v.say(role + "_cold", {
                    "QB": [f"🗑️ {name} has been complete booty cheeks — {txt}.",
                           f"🗑️ {name} has been throwing it to the other team — {txt}.",
                           f"🗑️ {name} looks lost out there: {txt}."],
                    "SP": [f"💣 {name} has been getting shelled — {txt}.",
                           f"💣 {name} has been getting lit up: {txt}.",
                           f"💣 Hitters are teeing off on {name} — {txt}."],
                    "G": [f"🥅 {_poss(the_them)} goalie {name} has been giving up a lot of goals — {txt}.",
                          f"🥅 {_poss(the_them)} goalie {name} can't keep the puck out lately: {txt}.",
                          f"🥅 Pucks keep getting past {_poss(the_them)} goalie, {name} — {txt}."]}[role]))
            elif ours_ and mood == "hot":
                out.append(v.say(role + "_hot", {
                    "QB": [f"🎯 {name} has been cooking — {txt}.",
                           f"🎯 {name} is locked in: {txt}.",
                           f"🎯 {name} is slinging it — {txt}."],
                    "SP": [f"🔥 {name} has been dealing — {txt}.",
                           f"🔥 {name} is on a roll: {txt}.",
                           f"🔥 Nobody's touching {name} lately — {txt}."],
                    "G": [f"🧱 {_poss(the_us)} goalie {name} has been a brick wall — {txt}.",
                          f"🧱 {name} is standing on his head: {txt}.",
                          f"🧱 Good luck scoring on {name} — {txt}."]}[role]))

    # situational spots the engine learned from 10 seasons of games
    rsn = leg.get("reasons") or []
    if "revenge game" in rsn:
        out.append(v.say("revenge", [f"😤 Revenge game — {us} lost the last meeting and they haven't forgotten.",
                                      f"😤 {us} owe {them} one from last time. Payback's coming.",
                                      f"😤 Get-back game for {us}. They took an L to {them} last time.",
                                      f"😤 {us} been waiting on this rematch."]))
        said.add("revenge game")
    if "letdown spot for the opponent" in rsn:
        out.append(v.say("letdown", [f"🪤 Letdown spot for {them} — fresh off a blowout win, they're gonna come out flat.",
                                      f"🪤 {them} just blew somebody out. Classic letdown game.",
                                      f"🪤 {them} are riding high off a big W. That's when teams slip.",
                                      f"🪤 Trap game for {them} after that blowout."]))
        said.add("letdown spot for the opponent")
    if "rolling off a blowout win" in rsn:
        out.append(v.say("momentum", [f"🚀 {us} just blew somebody out — teams like that keep rolling.",
                                       f"🚀 {us} are coming in hot off a blowout. Momentum's real.",
                                       f"🚀 Blowout last time out for {us}. They're feeling themselves."]))
        said.add("rolling off a blowout win")
    temp, wind, rain = g.get("wx_temp", ""), g.get("wx_wind", ""), g.get("wx_rain", "")
    if "altitude edge" in rsn and (sm._num(g.get("elev")) or 0) >= sm.THIN_AIR_M:
        out.append(v.say("alt", [f"🏔️ Thin air — {g.get('elev')} meters up. {_cap(the_them)} gonna be sucking wind by the second half.",
                                  f"🏔️ Altitude game. {_cap(the_them)} ain't used to breathing up there.",
                                  f"🏔️ Mile-high problems for {the_them}. Legs get heavy fast at that elevation."]))
        said.add("altitude edge")
    if "cold-weather edge" in rsn:
        out.append(v.say("cold_w", [f"🥶 {temp}°F at kickoff. {_cap(the_them)} are a warm-weather squad walking into a freezer.",
                                     f"🥶 It's gonna be {temp}°F. {_cap(the_them)} don't play in this — {the_us} do.",
                                     f"🥶 Cold one ({temp}°F). Welcome to real weather, {the_them}."]))
        said.add("cold-weather edge")
    if "nasty weather helps us" in rsn:
        what = f"{wind} mph winds" if str(wind) not in ("", "0") and float(wind or 0) >= 15 else f"{rain} mm of rain"
        out.append(v.say("wx", [f"🌧️ {what} in the forecast. Sloppy game, fewer big plays — that's how dogs eat.",
                                 f"🌬️ {what}. Ugly weather drags everybody down to the same level.",
                                 f"🌧️ Weather's nasty ({what}). Anything can happen in the slop."]))
        said.add("nasty weather helps us")
    if "opponent's body clock is off" in rsn:
        out.append(v.say("jetlag", [f"🕐 {_cap(the_them)} crossed a few time zones for this one. Body clock's all messed up.",
                                     f"🕐 Jet-lag game for {the_them} — their bodies think it's a different time.",
                                     f"🕐 Long trip for {the_them}, time zones and all. Legs gonna be heavy."]))
        said.add("opponent's body clock is off")
    drama_r = next((r for r in rsn if r.startswith("opponent drama:")), None)
    if drama_r and leg.get("their_drama"):
        ev = leg["their_drama"][0]
        kind = ev["kind"]
        lines = {"coach fired": [f"🧯 {_cap(the_them)} just fired their coach. Locker room's a mess.",
                                 f"🧯 Coaching change for {the_them} — interim guy, total chaos."],
                 "suspension": [f"🧯 {_cap(the_them)} got a suspension hanging over them: \"{ev['headline']}\"",
                                f"🧯 Suspension news for {the_them}. That shakes a team up."],
                 "legal trouble": [f"🧯 {_cap(the_them)} got off-field drama going on: \"{ev['headline']}\"",
                                   f"🧯 Legal mess around {the_them} this week. Distractions are real."],
                 "family/personal": [f"🧯 {_cap(the_them)} dealing with some personal stuff: \"{ev['headline']}\"",
                                     f"🧯 Heavy week for {the_them} off the field. Hard to lock in."],
                 "illness": [f"🤒 Sickness going around {the_them}: \"{ev['headline']}\"",
                             f"🤒 {_cap(the_them)} got guys under the weather."],
                 "trade drama": [f"🧯 Trade drama in {the_them}' locker room: \"{ev['headline']}\"",
                                 f"🧯 {_cap(the_them)} got a guy wanting out. Locker room's split."]}.get(kind)
        named = [str(n).split(" (")[0] for n in (leg.get("opp_outs") or []) + list((leg.get("key_seen") or {}).keys())]
        if kind == "suspension" and any(n and n.split(" (")[0] in ev.get("headline", "") for n in named):
            lines = None                                 # (10/3: Dylan Stewart's suspension was already in the 🚑 line)
        if lines:
            out.append(v.say("drama_" + kind.replace("/", "_").replace(" ", "_"), lines))
        said.add(drama_r)
    out += context_lines(leg, v, us, them, the_us, the_them, g)
    if "coming off a bye" in rsn:
        out.append(v.say("bye", [f"🛌 {us} are fresh off a bye — rested and game-planned up.",
                                  f"🛌 Extra week to prep for {us}. That matters.",
                                  f"🛌 Bye week in the rearview for {us}. Fresh legs, full playbook."]))
        said.add("coming off a bye")
    if "opponent on a short week" in rsn:
        out.append(v.say("short", [f"⏱️ {them} are on a short week. Not much time to prep.",
                                    f"⏱️ Short week for {them} — tired bodies, rushed game plan.",
                                    f"⏱️ {them} barely had time to recover. Short week."]))
        said.add("opponent on a short week")

    # overseas games are always weird
    if str(g.get("intl")) == "1":
        where = g.get("country") or "overseas"
        out.append(v.say("intl", [f"🌍 Game's overseas in {where}. These are always weird — the engine needed extra value to take it.",
                                   f"🌍 International game ({where}). Nobody's really home, everybody's jet-lagged — we only play these with a bigger edge.",
                                   f"🌍 {where} game. Weird spot, so the engine made sure the number's extra juicy."]))

    # home / road
    if str(g.get("intl")) == "1":
        pass                                            # no real home crowd overseas
    elif side == "home":
        _hm = [x for x in r_ours if x.get("home") == tid]
        if len(_hm) >= 2:                                # (10/1: never vague - the home record, or nothing)
            _hr = _record(_hm, tid)
            out.append(v.say("home", [f"🏟️ {us} are {_hr} at home this year.",
                                       f"🏟️ Home game for {us} — {_hr} in their building so far.",
                                       f"🏟️ {us} at home: {_hr} this season.",
                                       f"🏟️ {_hr} at home for {us} this year."]))
    else:
        _rd = [x for x in r_ours if x.get("away") == tid]
        if len(_rd) >= 2:                                # (10/1: "they travel just fine" said nothing - the record does)
            _rr = _record(_rd, tid)
            out.append(v.say("road", [f"🧳 {us} are {_rr} on the road this year.",
                                       f"🧳 Road game for {us} — {_rr} away from home so far.",
                                       f"🧳 {us} away from home: {_rr} this season.",
                                       f"🧳 {_rr} on the road for {us} this year."]))

    # rest
    if ours and theirs:
        d_us, d_them = (start - _t(ours[-1]["start"])).days, (start - _t(theirs[-1]["start"])).days
        if d_them <= 1 < d_us:
            out.append(v.say("b2b", [f"😴 {them} played yesterday — tired legs. {us} are fresh.",
                                      f"😴 {them} are on a back-to-back; {us} had the night off.",
                                      f"😴 Short rest for {them}, full tank for {us}.",
            f"😴 {them} are running on fumes — played last night.",
            f"😴 Back-to-back for {them}. Tired legs, cold shooting."]))
        elif d_us - d_them >= 2 and d_us <= 10:              # (a season-opener gap isn't "rest")
            gap_d = d_us - d_them
            out.append(v.say("rest", [f"🛌 {us} had {gap_d} more days off than {them}.",
                                       f"🛌 Rest edge: {us} got {gap_d} extra days to recover.",
                                       f"🛌 {us} come in with {gap_d} more days of rest.",f"🛌 {us} are the more rested squad.", f"🛌 {us} had extra days to get right.",
                                       f"🛌 Rest edge goes to {us}.",
            f"🛌 {us} are well-rested and ready.",
            f"🛌 Extra rest for {us} — fresh legs."]))

    # pitchers
    if lg == "mlb" and g.get("sp_home") and g.get("sp_away"):   # (10/1 audit: "TBA gets the ball" - both named or no line)
        ps, po = g.get("sp_" + side) or "TBA", g.get("sp_" + other) or "TBA"
        nice = [f"⚾ {x}" for x in sports_lingo.good(ps, the_them, f"{g['id']}|sp")] \
            if "better starting pitcher" in (leg.get("reasons") or []) and ps != "TBA" else []   # our arm's the better one
        out.append(v.say("bump", names=(ps, the_them), options=nice + [f"⚾ On the bump: {ps} for {us}, {po} for {them}.",
                                   f"⚾ Pitching matchup: {ps} ({us}) vs {po} ({them}).",
                                   f"⚾ {ps} takes the ball for {us}; {them} go with {po}.",
            f"⚾ {ps} gets the ball for {us} against {po}.",
            f"⚾ It's {ps} for {us}, {po} for {them}."]))

    # injuries
    inj = (injuries or {}).get(lg)
    if inj:
        ours_out, theirs_out = sd.team_injuries(inj, tid, us), sd.team_injuries(inj, oid, them)
        key_them = sd.team_key_out(inj, oid, them, lg)
        both = key_them and sd.team_key_out(inj, tid, us, lg)
        if key_them and not both and lg == "mlb":         # baseball: one of their best bats is out (9/29, Judge)
            nm = key_them[0][0]
            out.append(v.say("keyout_bat", [f"🚑 {them} are without {nm} — one of their best bats is on the shelf.",
                                            f"🚑 No {nm} in {_pos(them)} lineup. That's a big bat gone.",
                                            f"🚑 {them} gotta score without {nm}. Their lineup just got a lot less scary."]))
        elif key_them and not both and any(w in str(key_them[0][2]).lower() for w in sd.LONG_OUT):
            pos, nm = _posname(key_them[0][1], lg), key_them[0][0]   # (10/4: Dart on IR read like fresh news -
            out.append(v.say("keyout", [                              #  Winston had started their last two games)
                f"🚑 {nm} is on IR — {them} are still on their backup {pos}.",
                f"🚑 {them} are still without {nm} (IR) — the backup {pos} keeps the job.",
                f"🚑 Still no {nm} for {them} — he's on IR, the backup {pos} goes again."]))
        elif key_them and not both:
            pos, nm = _posname(key_them[0][1], lg), key_them[0][0]
            out.append(v.say("keyout", [f"🚑 {them} are rolling without their starting {pos} ({nm}).",
                                         f"🚑 No {nm} for {them} — that's their starting {pos}.",
                                         f"🚑 {them} are down their starting {pos}, {nm}."]))
        # (the owner, 10/1: one depth guy out is no edge - "is he even a star?" - but "if a team's hella banged up and
        #  got a bunch of injured players, that line is totally good": 3+ out, and 2+ more than us)
        starters_out = sd.team_key_out(inj, oid, them, lg)    # (the owner, 10/1: "hella banged up" means STARTERS -
        if len(starters_out) >= 3 and len(theirs_out) - len(ours_out) >= 2:   # only players we KNOW are key count;
            #                                                       a depth guy on the report never does)
            out.append(v.say("banged", [f"🚑 {them} are hella banged up ({_names(theirs_out)}).",
                                         f"🚑 {_pos(them)} injury list is stacking up: {_names(theirs_out)}.",
                                         f"🚑 {them} are missing bodies — {_names(theirs_out)}.",
            f"🚑 {them} are dealing with injuries: {_names(theirs_out)}.",
            f"🚑 {them} are short-handed ({_names(theirs_out)})."]))
        elif not ours_out and not theirs_out:
            out.append(v.say("healthy", [f"✅ {us} are healthy — nobody important sitting.",
                                          f"✅ Full squad for {us}.", f"✅ {us} have everybody available.",
            f"✅ {us} are at full strength.",
            f"✅ Nobody big missing for {us}."]))

    # a starting QB/goalie out: the line moved for the INJURY, not sharp money - say that, never "sharps"/"clowns"
    op, now = sm._int(g.get(f"ml_{side}_open")), sm._int(g.get(f"ml_{side}"))
    op_o_fb = None
    if lg in ("nfl", "ncaaf"):                            # (10/1: a football "open" is the summer look-ahead line - a
        try:                                              # move from it is the season, not money. The move is from our
            import sports_early as _se                    # own first fair price this week, or there's no move line)
            ff = _se.first_fair(g["id"], _se.ready(_se._schedule(games), g))
        except Exception:                                 # noqa: BLE001
            ff = None
        op = (ff[0] if side == "home" else ff[1]) if ff else None
        op_o_fb = (ff[1] if side == "home" else ff[0]) if ff else None
    key_us = sd.team_key_out(inj, tid, us, lg)
    key_any = key_us or sd.team_key_out(inj, oid, them, lg)
    key_them2 = sd.team_key_out(inj, oid, them, lg) if inj else None
    if key_us and key_them2 and lg == "mlb":
        nm, nm2 = key_us[0][0], key_them2[0][0]
        out.append(v.say("keyout_both_bat", [
            f"🚑 Both lineups are missing a big bat — no {nm} for {the_us}, no {nm2} for {the_them}. Still our side.",
            f"🚑 Both sides are missing someone: {nm} ({the_us}) and {nm2} ({the_them}). The price already has it - we still like {the_us}."],
            must=True))
    elif key_us and key_them2:                            # both teams down a starter: one plain line, not two
        pos, nm, nm2 = _posname(key_us[0][1], lg), key_us[0][0], key_them2[0][0]
        mv = f" The line already moved for it ({_am(op)} → {_am(now)})." if op is not None and now is not None and op != now else ""
        out.append(v.say("keyout_both", [
            f"🚑 Both teams are down their starting {pos} — {nm} is out for {the_us}, {nm2} for {the_them}.{mv} We still riding with the algorithm.",
            f"🚑 Backups on both sides tonight: no {nm} for {the_us}, no {nm2} for {the_them}.{mv} The numbers still say this the side.",
            f"🚑 Neither team has its starting {pos} — {nm} ({the_us}) and {nm2} ({the_them}) are both out.{mv} We still like {the_us}."],
            must=True))
    elif key_us and lg == "mlb":                          # our best bat is out: say it, and say why we still ride
        nm = key_us[0][0]                                 # (the owner, 9/29: like the Caleb Williams one - it's out,
        mv = ""                                           # it don't change our call. A bat on the IL has been out a
        #                                                   while - today's line move isn't "for it")
        out.append(v.say("keyout_us_bat", [
            f"🚑 Yeah, {nm} is out for {the_us}. We know.{mv} The price already knows it too, and the numbers still say this the side.",
            f"🚑 No {nm} tonight — that's a big bat missing for {the_us}.{mv} Doesn't change our call. We riding with the algorithm.",
            f"🚑 {nm} ain't playing. Everybody's scared off {the_us} because of it.{mv} We ain't — the rest of this lineup still gets it done."],
            must=True))
    elif key_us:
        pos, nm = _posname(key_us[0][1], lg), key_us[0][0]
        mv = f" The line already moved for it ({_am(op)} → {_am(now)})." if op is not None and now is not None and op != now else ""
        pts = leg.get("line") if leg.get("market") == "spread" else None
        need = f" {_cap(the_them)} gotta win by {int(pts) + 1}+ to beat us. Win by {int(pts)}, win by 1, or lose — we cash." \
            if pts and pts > 0 and pts != int(pts) else ""
        out.append(v.say("keyout_us", [
            f"🚑 {nm} is out, {the_us} rolling with the backup {pos}.{mv} We know. We still riding with the algorithm.{need}",
            f"🚑 No {nm} tonight — backup {pos} gets the keys for {the_us}.{mv} Vegas already baked that in, and the numbers still say this the side.{need}",
            f"🚑 Yeah, {nm} is out. Everybody and they mama jumped off {the_us}.{mv} We ain't scared — teams always be coming back.{need}"],
            must=True))
    if not key_any and op is not None and now is not None and op != now and sd.implied(now) > sd.implied(op):
        # the price moving our way: the market catching up to US - never "we're with the sharps" (the owner, 9/29: we're
        # our own engine, not a sharp-money follower)
        out.append(v.say("sharp", [f"💰 {us} opened {_am(op)}, now {_am(now)}. The market's catching up to what the engine already saw.",
                                    f"💰 {us} went from {_am(op)} to {_am(now)} since the open. We were here first.",
                                    f"💰 The line moved toward {us} ({_am(op)} → {_am(now)}). The engine had this side before the move.",
                                    f"💰 {_am(op)} at the open, {_am(now)} now — the market's coming around to {us}.",
            f"💰 The price on {us} keeps shortening ({_am(op)} → {_am(now)}). Good thing we're already on it.",
            f"💰 Everybody else is showing up late on {us}: {_am(op)} to {_am(now)}.",
            f"💰 The pros are on {us} too ({_am(op)} → {_am(now)}). We rocking with the sharps on this one — we just got here first."]))

    # sharp money going the other way and we still like our side: say it our way, with a quick reason
    op_o, now_o = sm._int(g.get(f"ml_{other}_open")), sm._int(g.get(f"ml_{other}"))
    if lg in ("nfl", "ncaaf"):
        op_o = op_o_fb
    if not key_any and op is not None and now is not None and sm.logit(sd.implied(op)) - sm.logit(sd.implied(now)) >= 0.08:
        move = f" ({_am(op_o)} → {_am(now_o)})" if op_o is not None and now_o is not None else ""
        why = next((WHY[r].format(us=us, them=them) for r in leg.get("reasons") or [] if r in WHY and r not in said),
                   NO_WHY)
        said.update(r for r in leg.get("reasons") or [] if WHY.get(r, "").format(us=us, them=them) == why)
        out.append(_nowhy(v.say("fade", [
            f"💸 Money's been coming in on {the_them}{move}, but whoever's betting it must be some clowns. We're on {the_us} — {why}.",
            f"💸 Somebody's pushing {the_them}{move}. We're fading the clowns and taking {the_us} — {why}.",
            f"💸 Line's moving toward {the_them}{move}. Let 'em — we still like {the_us}, {why}.",
            f"💸 Money's pouring in on {the_them}{move}. They must've lost their minds — we got {the_us}, {why}.",
            f"💸 Everybody's jumping on {the_them}{move}. They're tweaking — we're riding {the_us}, {why}.",
            f"💸 The market's leaning {the_them}{move}. Somebody's about to learn a lesson — we're on {the_us}, {why}."])))

    # who's betting who: the real splits (the same numbers Google shows)
    sp_ = public_split(leg)
    if sp_ and sp_[1] is None:                            # bets % only (Yahoo's backup has no money %): say that plain
        t = sp_[0]
        crowd = the_us if t >= 50 else the_them
        out.append(v.say("splits_y", [
            f"📊 {max(t, 100 - t)}% of the bets are on {crowd}." + (" We with 'em on this one." if t >= 50 else " We on the other side."),
            f"📊 The public's got {max(t, 100 - t)}% of the tickets on {crowd}." + (" Same side as us." if t >= 50 else " Not us."),
            f"📊 {crowd} got {max(t, 100 - t)}% of the bets." + (" Popular pick, right pick." if t >= 50 else " We fading that.")]))
        sp_ = None
    if sp_:
        t, m = sp_
        mk = {"ml": "the moneyline", "spread": "the spread", "total": "the total"}[leg["market"]]
        if t <= 35:
            out.append(v.say("splits_f", [
                f"📊 The whole world on {the_them} — {100 - t}% of the bets and {100 - m}% of the money on {mk}. "
                f"We fading the public and taking {the_us}. That's how Vegas eats, and tonight we eating with 'em.",
                f"📊 {100 - t}% of the bets on {the_them} ({100 - m}% of the money). Sheep gon' be sheep — "
                f"we on {the_us} with the other {t}%.",
                f"📊 Public's hammering {the_them}: {100 - t}% of the bets, {100 - m}% of the money. "
                f"We ain't following the herd — {the_us} all day.",
                f"📊 {100 - t}% of the tickets on {the_them}. The books love that. We on {the_us}.",
                f"📊 The casuals got {the_them} ({100 - t}% of the bets). We fading 'em — {the_us}.",
                f"📊 Only {t}% of the bets on {the_us}. That's exactly where we want to be."]))
        elif t >= 65:
            out.append(v.say("splits_w", [
                f"📊 Public's with us on this one — {t}% of the bets and {m}% of the money on {the_us}. "
                f"Sometimes the crowd gets it right.",
                f"📊 {t}% of the bets on {the_us} ({m}% of the money). We with the crowd on this one.",
                f"📊 The crowd's on {the_us} too — {t}% of the tickets, {m}% of the cash. Public's usually wrong — not this time.",
                f"📊 {t}% of the bets and {m}% of the money on {the_us}. For once the casuals ain't wrong.",
                f"📊 Everybody and they mama on {the_us}: {t}% of the bets, {m}% of the money. Same side as us.",
                f"📊 {the_us} got {t}% of the bets ({m}% of the money). Popular pick, still the right one."]))
        else:
            out.append(v.say("splits", [
                f"📊 Bets are split — {t}% on {the_us}, {100 - t}% on {the_them} ({m}% / {100 - m}% of the money). "
                f"Nobody knows nothing on this one, except us.",
                f"📊 Who's betting who: {t}% of the bets on {the_us}, {100 - t}% on {the_them}. Pretty split crowd.",
                f"📊 {t}% on {the_us}, {100 - t}% on {the_them}. Crowd can't make up its mind — we already did.",
                f"📊 The public's torn on this one ({t}% / {100 - t}%). The engine ain't.",
                f"📊 Tickets are close to even — {t}% {the_us}, {100 - t}% {the_them}. We got our side."]))

    # the public: fading them or riding with them
    pub = public_side(leg, g)
    why_pub = next((WHY[r].format(us=us, them=them) for r in leg.get("reasons") or [] if r in WHY and r not in said),
                   NO_WHY)
    if sp_:
        pass                                          # the real splits already said it (with the numbers)
    elif pub == "fade":
        out.append(_nowhy(v.say("pub_fade", [
            f"🤡 {_cap(the_them)} are the clear favorite and the public's all over 'em. Don't be a sheep — we're on {the_us}, {why_pub}.",
            f"🤡 The public is all over {the_them}. Dummies are about to lose their money — we're on {the_us}, {why_pub}.",
            f"🤡 Everybody and their mama is on {the_them}. Not us — we got {the_us}, {why_pub}.",
            f"🤡 The sheep are lining up for {the_them}. We're not sheep — we're on {the_us}, {why_pub}.",
            f"🤡 Crowd's on {the_them}. We're riding {the_us} and the engine — {why_pub}.",
            f"🤡 Public's hammering {the_them} like it's free money. It ain't — we got {the_us}, {why_pub}.",
            f"🤡 All the casuals love {the_them}. We're not casuals — {the_us} all day, {why_pub}."])))
    elif pub == "ride":
        out.append(_nowhy(v.say("pub_ride", [
            f"🤝 Riding with the public on {the_us} — sometimes the public gotta win, {why_pub}.",
            f"🤝 Public's on {the_us} too, and this time they're not dummies — {why_pub}.",
            f"🤝 The public's usually on the wrong side. Not tonight — they got {the_us} right, {why_pub}.",
            f"🤝 We're with the crowd on {the_us} and not ashamed of it — {why_pub}.",
            f"🤝 Public side on {the_us}, but we got our own reasons — {why_pub}.",
            f"🤝 We're riding with the crowd on {the_us}. Sometimes they get it right — {why_pub}."])))

    # bottom line - in our lingo, never the book-vs-us odds talk (the owner, 9/29: that don't make sense), and never the
    # same wording twice on a board (a big pool per kind; the Voice skips any wording already used)
    bet = f"{us} {leg['line']:+g}" if leg["market"] == "spread" else us
    price = f"{bet} ({_am(leg['odds'])})"
    pct = round(100 * leg["p"])                                          # ONE number, ours, said plain - that's fine
    _need = 1 / leg["dec"] if leg.get("dec") else None                    # (10/1, the owner: never vague - the bottom
    try:                                                                 # line says the real numbers: the engine's
        import sports as _sp                                             # own read vs what the price needs)
        _own = _sp.read_of(leg) or leg["p"]
    except Exception:                                                    # noqa: BLE001
        _own = leg["p"]
    wp = f"{round(100 * _own)}%" if _own > 0.55 else ""                 # (10/1, the owner: "50 out of 100, the price
    pos = f" {us} at {wp}." if wp else ""                                # needs 48" is jargon - plain words: does our
    _fact = "Our read beats this price." if not _need or _own > _need else "The price is too steep for units."
    if leg.get("near_price"):                                            # the always-a-Lock backup (the owner, 10/1):
        out.append(v.say("bottom_near", [                                # the likeliest winner, priced about right -
            f"✅ Bottom line: {price}. Our Lock today, priced about right - a small bet, not a big one.",
            f"✅ Bottom line: {price}. We like {us} to win; the price is close to fair, so we keep it small.",
            f"✅ Bottom line: {price}. Fair price on a side we trust - small bet.",
            f"✅ Bottom line: {us} to win, {price}. The number's about even with our read - we ride it light."]) or
                   _short(v, price, True, ""))                           # (small, honest - never "value")
    elif _need and _own <= _need and _own < 0.56 and leg.get("market") == "ml":   # (10/1, the owner: "we like the Kraken,
        out.append(v.say("bottom_c", [                                   # just not at this price" at -108 makes no
            f"✅ Bottom line: {price}. We've got this one close to a coin flip - {us} by a hair. No units.",   # sense:
            f"✅ Bottom line: {price}. Close to 50-50 on our read, {us} a hair better. Just a lean.",          # the real
            f"✅ Bottom line: {price}. Near a coin flip to us - {us} is the side, not a bet we put money on.",  # reason is
            f"✅ Bottom line: {price}. Our read has it close to even. {us} by a hair - a lean."]) or         # a coin flip)
                   _short(v, price, False, "Close to a coin flip on our read."))
    elif _need and _own <= _need:                                        # read beat the price or not; ONE % only
        out.append(v.say("bottom_n", [                                   # when it's over 55. Never "value" on a read
            f"✅ Bottom line: {price}. Right side, but the price is too steep for units - just a lean.",   # under it)
            f"✅ Bottom line: we like {us}, not the price. A lean, no money on it.",
            f"✅ Bottom line: {price} costs too much for what we see. Lean only.",
            f"✅ Bottom line: {us} is the side - the odds just don't beat the price. A lean.",
            f"✅ Bottom line: good side, bad number. {price} is a lean, no units.",
            f"✅ Bottom line: {price}. We'd ride {us}, but not with money at this price.",
            f"✅ Bottom line: {us} is our side; {price} is too rich for units. Lean it."]) or _short(v, price, False, _fact))
    elif leg.get("tier") == "lock":                                      # a lock: our whole chest, never a hedge
        out.append(v.say("bottom_l", [
            f"✅ Bottom line: {price}. The engine likes {us} more than the books do. Lock it in.",
            f"✅ Bottom line: {price} — this price is cheaper than it should be. We're all in.",
            f"✅ Bottom line: {price}. The books got this one priced wrong. Stamp it.",
            f"✅ Bottom line: {price}. Our read beats this number. Say less.",
            f"✅ Bottom line: {price} — the value's on our side.{pos} Locked in.",
            f"✅ Bottom line: {price}.{pos} The price didn't catch up to our read. Tap in.",
            f"✅ Bottom line: {price}. We'd lay this all day - the number's in our favor.",
            f"✅ Bottom line: {price}. The side we trust most today, at a price that pays. That's money."]) or _short(v, price, True, _fact))
    else:
        out.append(v.say("bottom_s", [
            f"✅ Bottom line: {price}. The engine gives {us} a better shot than this price does. That's the bet.",
            f"✅ Bottom line: {price} pays more than it should. Tap in.",
            f"✅ Bottom line: {price}. The books are sleeping on {us}. We finna see.",
            f"✅ Bottom line: {price}. Our read beats the number. Riding {us}.",
            f"✅ Bottom line: {price} — the price is the value. Get in.",
            f"✅ Bottom line: {price}. {us} are better than this number says. Quiet play, right play.",
            f"✅ Bottom line: {price}.{pos} The books undersold 'em.",
            f"✅ Bottom line: {price}. The number's in our favor - that's why we're on {us}."]) or _short(v, price, False, _fact))
    inj_ = (injuries or {}).get(lg)
    leg["why_line"] = why_line(leg, v, g, us, them, the_us, the_them, rec_u=rec_u, n_hot=n_hot, rec_t=rec_t,
                               n_cold=n_cold, gap=gap, form=FORM,
                               key_them=sd.team_key_out(inj_, oid, them, lg) if inj_ else [],
                               key_us=sd.team_key_out(inj_, tid, us, lg) if inj_ else [])
    import sports_card_guard                              # 🛡️ every line passes the owner's checks before it posts
    leg["why_line"] = sports_card_guard.one(leg["why_line"], lg, us)
    lines = sports_card_guard.clean([x for x in out if x], lg, us)
    if str(leg.get("why_line") or "").startswith("💪"):   # (10/3: the record said twice - the headline already has it)
        lines = [x for x in lines if not str(x).startswith("💪")]
    if day_game(start):                                   # (10/4, the owner's queue: "tonight" on a 10 AM game)
        leg["why_line"] = not_tonight(leg["why_line"])
        lines = [not_tonight(x) for x in lines]
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


def day_game(start):
    """A game that starts before 3 PM PT (6 PM ET) is a day game - never 'tonight' on its card."""
    try:
        return start.astimezone(PT).hour < 15
    except (AttributeError, ValueError, TypeError):
        return False


def not_tonight(x):
    if not isinstance(x, str):
        return x
    x = re.sub(r"\bTonight\b", "Today", x)
    return re.sub(r"\btonight\b", "today", x)


def why_line(leg, v, g, us, them, the_us, the_them, rec_u=None, n_hot=0, rec_t=None, n_cold=0, gap=None, form=None,
             key_them=(), key_us=()):
    """The line right under the pick on the card (the owner, 9/29: 'the stronger team' is way too vague - a dope,
    strong line in our lingo, every pick, every sport). The engine's top reason, said with the real facts behind it
    (records, streaks, who's out, the arms, the miles), plus a short kicker now and then. Never the same wording twice
    on a board or from the days before (the breakdown's own memory)."""
    form = form or {}
    lg = leg["league"]
    rsn = [r for r in leg.get("reasons") or [] if not str(r).startswith(("proven", "trend:", "opponent drama"))]
    rsn = [r for r in rsn if r != "sharp money moving this way"] + [r for r in rsn if r == "sharp money moving this way"]
    pct = round(100 * (leg.get("p") or 0))
    sp_us, sp_them = g.get("sp_" + leg["side"]), g.get("sp_" + ("away" if leg["side"] == "home" else "home"))
    trip = next((c for c in leg.get("ctx") or [] if c.get("k") == "trip" and c.get("who") == "them" and (c.get("mi") or 0) >= 1000), None)
    rival = any(c.get("k") == "rival" for c in leg.get("ctx") or [])
    pools = []
    for r in rsn:
        if r == "the stronger team":
            _wr = lambda r_: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in r_.split("-")[:2]])
            if rec_u and rec_t and _wr(rec_u) > _wr(rec_t):   # (10/1 audit + the owner's never-vague rule: "just the
                pools.append(("w_better", [                     # better team" with no fact is gone - the records say it,
                    f"💪 {us} ({rec_u}) vs {them} ({rec_t}) — the better team's on our side.",   # or no line)
                    f"💪 {rec_u} against {rec_t}: {us} been the better team.",
                    f"💪 {us} {rec_u}, {them} {rec_t}. Better squad on our side.",
                    f"💪 {us} ({rec_u}) over {them} ({rec_t}) on the record. That's just facts."]))
        elif r == "hotter recent form":
            if n_hot < 2:
                continue                                  # (no streak to show = no line, never "the hotter team")
            hot = f"{n_hot} straight W's"
            pools.append(("w_hot", [
                f"🔥 {us} are rolling — {hot}{f', {rec_u} on the year' if rec_u else ''}. Ride the heater." if hot else
                f"🔥 {us} been playing way better ball than {them} lately. Ride the heat.",
                f"🔥 {us} are cooking right now{f' ({hot})' if hot else ''} and {them} ain't matching that energy.",
                f"🔥 Hot hand goes to {us}{f' — {hot}' if hot else ''}. We don't bet against a heater."]))
        elif r == "opponent missing key players":
            if not key_them or key_us:                    # (the owner, 10/1: "is he even a star? If he's not a factor
                continue                                  # the engine shouldn't put that" - only a KEY player out (their
            #                                               QB, goalie, one of their best bats) gets named; a depth
            #                                               guard or a 3rd-pair defenseman never does)
            star = "one of their best bats" if lg == "mlb" else f"their starting {_posname(key_them[0][1], lg)}"
            nm = f"{star}, {key_them[0][0]}" if lg == "mlb" else f"{star} {key_them[0][0]}"
            pools.append(("w_hurt", [
                f"🚑 {them} are without {nm} tonight — that's a hole we're attacking.",
                f"🚑 No {nm} for {them}. Short-handed teams get got.",
                f"🚑 {them} gotta play this one without {nm}, and we're taking advantage.",
                f"🚑 {_cap(nm)} is out for {them}. That changes the whole game — our way."]))
        elif r == "sharp money moving this way":             # (never the headline when the engine has its own reason)
            pools.append(("w_sharp", [
                f"💸 The money's been coming in on {us} since the open.",          # (9/30: never "the engine had
                f"💸 {_pos(us)} price keeps shortening since the open — the money's on them.",   # them first" - we
                f"💸 Smart money's been moving toward {us} all day."]))           # posted AFTER the move)
        elif r == "better starting pitcher" and sp_us:
            hot = form.get((True, "hot"))
            pools.append(("w_arm", [
                f"⚾ {sp_us} on the mound for {us}{f' — {hot[1]}' if hot else ''}. Better arm, better team.",
                f"⚾ We got the better arm tonight: {sp_us}{f' over {sp_them}' if sp_them else ''}.",
                f"⚾ {sp_us} gives {us} the edge on the bump{f' ({hot[1]})' if hot else ''}."]))
        elif r == "hotter goalie":                        # (10/1 audit: no numbers = no line - never vague)
            hot = form.get((True, "hot"))
            if not hot:
                continue
            pools.append(("w_goalie", [
                f"🧱 {hot[0]} has been a brick wall in net for {us} — {hot[1]}.",
                f"🧱 Better goalie play on {_pos(us)} side ({hot[0]}: {hot[1]}). Goals are gonna be tough for {them}."]))
        elif r == "better QB play lately":
            hot = form.get((True, "hot"))
            if not hot:
                continue
            pools.append(("w_qb", [
                f"🎯 {hot[0]} has been cooking for {us} — {hot[1]}.",
                f"🎯 The QB edge goes {us} ({hot[0]}: {hot[1]}). That's the game."]))
        elif r in ("better rested", "opponent on a back-to-back"):
            pools.append(("w_rest", [                    # (10/2: "running on fumes" went on a Bruins team with two
                f"😮‍💨 {them} played last night — tired legs against a fresh {us} team.",   # nights off - only a
                f"😮‍💨 {them} are running on fumes tonight. {us} are fresh."]           # real back-to-back says that)
                if r != "better rested" else [f"🛌 {us} got the extra rest, {them} don't. Fresh legs win late."]))
        elif r == "revenge game":
            pools.append(("w_revenge", [f"😤 {us} owe {them} one and they know it. Revenge game.",
                                        f"😤 Payback's on {_pos(us)} mind tonight — {them} got 'em last time.",
                                        f"😤 {them} won the last meeting. {us} get the rematch tonight.",
                                        f"😤 Rematch: {us} dropped the last one to {them}.",
                                        f"😤 Last time out against {them}, {us} took the L. Run it back.",
                                        f"😤 {us} lost to {them} last time - this one's personal."]))
        elif r == "the engine's scoring read":
            pools.append(("w_total", [f"📊 The engine's scoring numbers say this total is set wrong. We on it.",
                                      f"📊 Our scoring model sees this total different than the book does."]))
        elif r in WHY:
            pools.append(("w_" + r.split()[0], [f"🧠 {_cap(WHY[r].format(us=us, them=them))} — that's our edge tonight."]))
    try:                                                  # (10/1 audit) the card's number is the SAME read its bottom
        import sports as _sp                              # line uses - the engine's own read - never a second number
        own = _sp.read_of(leg) or leg["p"]                # ("35% to get it done" over "we see 37 in 100")
    except Exception:                                     # noqa: BLE001
        own = leg["p"]
    need = 1 / leg["dec"] if leg.get("dec") else None
    if round(100 * own) > 55:
        pct = round(100 * own)
        nums = ("w_num", [f"🔒 The numbers love {us} tonight — {pct}% to cash." if leg.get("tier") == "lock" else
                          f"🧠 The engine's got {us} at {pct}% tonight. We riding with it.",
                          f"🧠 {pct}% to cash on {us} — the numbers did the talking.",
                          f"🧠 {us} at {pct}% to get it done. That's the engine talking, not a hunch."])
    elif leg.get("near_price"):                           # the always-a-Lock backup: the likeliest winner, priced fair
        nums = ("w_num", [f"🔒 We trust {us} to win this one - priced about right, so it's a small bet.",
                          f"🔒 {us} to win at a fair price. A light bet, not a big one."])
    elif need and own <= need and own < 0.56 and leg.get("market") == "ml":   # (10/1, the owner: the Kraken at -108 - a near coin flip
        nums = ("w_num", [f"🧠 We've got {us} close to a coin flip - a hair better, not enough for units.",   # is the
                          f"🧠 Close to 50-50 on our read, {us} by a hair."])                              # reason)
    elif need and own <= need:                            # the read doesn't beat the price: say so, never "value"
        nums = ("w_num", [f"🧠 {us} is the side, but the price is too steep for units.",   # (plain words, no jargon -
                          f"🧠 We like {us} - just not at this price."])                    # the owner, 10/1)
    elif need:                                            # 55 or under: never a bare %, never number-vs-number
        nums = ("w_num", [f"🧠 The engine gives {us} a better shot than the books do.",
                          f"🧠 {us} at this price is the value - the books undersold 'em.",
                          f"🧠 Our read likes {us} more than the price does."])
    else:
        nums = ("w_num", [])
    line = ""                                             # the top reason first; every wording of it already used on
    for key, opts in pools + [nums]:                      # the board? the next reason - a repeat is the last resort
        line = v.say(key, opts)
        if line:
            break
    if not line:
        line = v.say("w_any", [o for _, opts in pools + [nums] for o in opts])   # any fresh wording left - else no line
        #                                                   (never the same reason line on two cards: the card's tag shows)
    kick = []                                             # a short second punch, when there's a real one
    if trip and rsn and "opponent's body clock is off" not in rsn:
        kick.append(("k_trip", [f" Plus {them} flew {_mi(trip['mi'])} miles for this.",
                                f" And {them} are coming off a {_mi(trip['mi'])}-mile trip."]))
    # (10/1 audit: the rivalry kicker - "Division rivals. No love lost." - is the owner's own banned example: gone)
    if leg.get("public") == "fade":
        kick.append(("k_fade", [" And the public's on the wrong side.", " The casuals are on the other side, too."]))
    for key, opts in kick[:1]:
        k = v.say(key, opts)
        if line and k and len(line) + len(k) <= 150:
            line += k
    return line


WHY = {   # the pick's reasons, said as a quick "because"
    "the stronger team": "they're the better team",
    "hotter recent form": "they're the hotter team",
    "better rested": "they got extra days of rest",
    "opponent on a back-to-back": "{them} are on tired legs",
    "opponent missing key players": "{them} are banged up",
    "revenge game": "they owe these guys one",
    "altitude edge": "{them} gonna be sucking wind up there",
    "opponent's body clock is off": "{them} are playing on jet lag",
    "cold-weather edge": "{them} aren't built for the cold",
    "nasty weather helps us": "sloppy weather keeps it close",
    "rolling off a blowout win": "they're rolling off a blowout",
    "letdown spot for the opponent": "{them} are due for a letdown",
    "coming off a bye": "they're fresh off a bye",
    "opponent on a short week": "{them} are on a short week",
    "better starting pitcher": "we've got the better arm on the mound",
    "better QB play lately": "our QB's been playing better",
    "hotter goalie": "our goalie's been hotter",
}


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


TALK_LINES = {   # pregame talk (sports_news TALK_KINDS): display only - forward-only tags, never a number
    "contract year": lambda who: [f"📣 Contract-year energy around {who} — somebody's playing for a bag.",
                                  f"📣 {_cap(who)} got money on the line this year. Contract talk all week.",
                                  f"📣 Payday season for {who}: the contract chatter is loud.",
                                  f"📣 Incentives on the line for {who}. Expect some extra effort."],
    "unhappy": lambda who: [f"📣 Not everybody's happy over there — {who} got some public frustration going.",
                            f"📣 Grumbling in {who}' camp this week, and it's out in the open.",
                            f"📣 Somebody in {who}' building is venting to the press. Vibes are off.",
                            f"📣 {_cap(who)} got a frustrated voice or two talking publicly."],
    "trash talk": lambda who: [f"📣 {_cap(who)} been running their mouth this week. Bulletin-board stuff.",
                               f"📣 Trash talk out of {who}'s side. Somebody gotta back it up now.",
                               f"📣 {_cap(who)} talked a big game all week — receipts get checked tonight.",
                               f"📣 Guarantees flying around {who}. Talk is cheap till kickoff."],
    "must-win": lambda who: [f"📣 {_cap(who)} already calling it a must-win out loud.",
                             f"📣 \"Must-win\" is the word around {who} this week. Backs to the wall.",
                             f"📣 {_cap(who)} say their season rides on this one.",
                             f"📣 Win-or-else talk coming out of {who}."],
    "rivalry week": lambda who: [f"📣 Rivalry week talk is loud around {who}. Bad blood energy.",
                                 f"📣 {_cap(who)} been hyping the rivalry all week.",
                                 f"📣 Bragging rights on the line, and {who} know it.",
                                 f"📣 {_cap(who)} been waiting on this one. No love lost here."],
    "hot seat": lambda who: [f"📣 Coach's job is a hot topic around {who}. Hot seat talk everywhere.",
                             f"📣 Job-security questions around {who}'s coach this week.",
                             f"📣 {_cap(who)}' coach is feeling the heat in the papers.",
                             f"📣 The coach over at {who} is under the microscope right now."],
}


def context_lines(leg, v, us, them, the_us, the_them, g):
    """Breakdown lines for the context study's facts (rivalry, travel, domes, stakes, refs) and pregame talk.
    Proven or not, these are just what's around the game - the numbers only move for PROVEN factors."""
    out = []
    total = leg.get("market") == "total"
    for c in leg.get("ctx") or []:
        k = c.get("k")
        if k == "rival":
            pass                                         # (10/1: never vague - the head-to-head line has the facts)
        elif k == "div":
            pass                                         # (10/1: never vague - the head-to-head line has the facts)
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
            out.append(v.say("cx_trip", [f"🧳 {_cap(the_them)}: {fact}. That travel adds up.",
                                         f"🧳 {fact.capitalize()} for {the_them}. Frequent flyer points, heavy legs.",
                                         f"🧳 {_cap(the_them)} living out of a suitcase — {fact}.",
                                         f"🧳 Travel check on {the_them}: {fact}.",
                                         f"🧳 {_cap(the_them)} put in the miles to get here ({fact})."]))
        elif k == "dome_cold":
            temp, wind = g.get("wx_temp", ""), g.get("wx_wind", "")
            wx = (f"{temp}°" if str(temp) != "" else "cold") + (f" with {wind} mph wind" if str(wind) not in ("", "0")
                                                                and float(wind or 0) >= 15 else "")
            who = the_them if not total else ("the home dome team" if c.get("who") == "home" else "the road dome team")
            out.append(v.say("cx_domecold", [f"🏟️ Dome team outside in {wx} — {who} usually play with the thermostat set.",
                                             f"🏟️ {_cap(who)} play indoors at home. Tonight: {wx} outside.",
                                             f"🏟️ No roof tonight for {who}. {wx.capitalize()} in the forecast.",
                                             f"🏟️ Indoor squad in the elements: {wx} for {who}."]))
        elif k == "dome_out":
            out.append(v.say("cx_domeout", [f"🏟️ {_cap(the_them)} are a dome team playing outside today.",
                                            f"🏟️ No roof for {the_them} this time — they're used to playing inside.",
                                            f"🏟️ {_cap(the_them)} leave the dome for an open-air building.",
                                            f"🏟️ Open air for an indoor team: {the_them} out of their element."]))
        elif k == "mustwin":
            out.append(v.say("cx_mustwin", [f"🚨 Must-win for {the_us} ({c.get('rec')}) — right in the playoff race.",
                                            f"🚨 {_cap(the_us)} ({c.get('rec')}) are fighting for a playoff spot. Backs against the wall.",
                                            f"🚨 Playoff race: {the_us} need this one, {the_them} don't.",
                                            f"🚨 Every game counts for {the_us} ({c.get('rec')}) right now. {_cap(the_them)}? Not so much."]))
        elif k == "rest":
            out.append(v.say("cx_rest", [f"🪑 {_cap(the_them)} already clinched — rest-the-starters territory.",
                                         f"🪑 Playoff spot locked for {the_them}. Don't be shocked if the stars sit.",
                                         f"🪑 {_cap(the_them)} got their ticket punched already. Nothing to play for tonight.",
                                         f"🪑 Clinched and coasting: {the_them} could rest guys."]))
        elif k == "tank":
            out.append(v.say("cx_tank", [f"📉 {_cap(the_them)} ({c.get('rec')}) are out of it. Draft-pick season over there.",
                                         f"📉 Eliminated and {c.get('rec')} — {the_them} are playing for ping-pong balls.",
                                         f"📉 {_cap(the_them)} ({c.get('rec')}) got nothing to play for but next year.",
                                         f"📉 Season's over for {the_them} ({c.get('rec')}), they just haven't gone home yet."]))
        elif k == "elim":
            out.append(v.say("cx_elim", [f"📉 {_cap(the_them)} are eliminated; {the_us} are still in the race.",
                                         "📉 One team's playing for a spot, the other's playing out the string.",
                                         f"📉 {_cap(the_them)} are out of the playoff picture. {_cap(the_us)} ain't.",
                                         f"📉 Playoff hopes: {the_us} alive, {the_them} done."]))
        elif k == "bowl5":
            out.append(v.say("cx_bowl", [f"🏈 {us} sit at 5 wins — one more and they're bowl eligible.",
                                         f"🏈 Bowl eligibility on the line: {us} need win number 6.",
                                         f"🏈 {us} are one W from a bowl game. Extra motivation.",
                                         f"🏈 Win 6 means a bowl trip for {us}."]))
        elif k == "hotseat":
            n = c.get("n") or 0
            out.append(v.say("cx_hotseat", [f"🔥 {_cap(the_them)} have lost {n} straight — that coach is on the hot seat.",
                                            f"🔥 {n} losses in a row for {the_them}. Coaching staff feeling the heat.",
                                            f"🔥 {_cap(the_them)} ({n} straight L's) are in a fishbowl right now.",
                                            f"🔥 Losing streak at {n} for {the_them}. Jobs on the line over there."]))
        elif k in ("ref_side", "ref_total"):
            nm = (c.get("names") or ["the crew"])[0]
            lean = c.get("lean")
            what = {"home": "the home team", "road": "the road team", "over": "the over", "under": "the under"}.get(lean, lean)
            out.append(v.say("cx_ref", [f"🦓 {nm} on the whistle tonight — his games have leaned toward {what}.",
                                        f"🦓 Zebra check: {nm}'s crew has tilted to {what} over his earlier games.",
                                        f"🦓 {nm} officiating. His track record leans {what}.",
                                        f"🦓 Officials matter: {nm}'s games have gone {what}'s way more than the book expected."]))
    for key, who in (("talk_theirs", the_them), ("talk_ours", the_us)):
        for t in (leg.get(key) or [])[:1]:                 # (10/3, the owner: "season rides on this one" says
            hl = str(t.get("headline") or "").strip()        # nothing - a talk line only with the actual quote)
            if TALK_LINES.get(t.get("kind")) and not total and hl:
                out.append(v.say("talk_q", [f"📣 Out of {who}'s camp this week: \"{hl}\"",
                                            f"📣 {_cap(who)} in the papers: \"{hl}\""]))
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
