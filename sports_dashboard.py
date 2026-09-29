"""Phone dashboard for THE D503 SPORTS ENGINE (docs/sports/index.html).
Top: today's board (2-leg, 3-leg, lock, dog). Below: results, record, and what the engine learned.
Self-contained HTML (inline CSS/SVG, tiny JS for the "updated X min ago" light)."""
import html
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_lingo

PT = ZoneInfo("America/Los_Angeles")
REPO = "D503therapper/autonomous-crypto-engine"
PAGE = "docs/sports/index.html"
BRAIN = "docs/sports/brain.json"      # everything the AI question box knows (rewritten with the page every run)
RECORDS = {}
LIVE_JSON_PATH = "docs/sports/live.json"
LOOK = {   # kind -> label, accent, second accent
    "two":   ("2-LEG OF THE DAY", "#2f8bff", "#22d3ee"),
    "three": ("3-LEG OF THE DAY", "#ffc233", "#ff8a00"),
    "lock":  ("LOCK OF THE DAY", "#22e39a", "#0fb87a"),
    "dog":   ("DOG OF THE DAY", "#ff5a1f", "#ff2a2a"),
    "four": ("4-LEG OF THE DAY", "#b36bff", "#ff4fd8"),
    "solo": ("ONE-GAME PICK", "#22e39a", "#22d3ee"),
    "eight": ("8-LEG (RETIRED)", "#8a5cff", "#c04fd8"),
}
BIG_HIT = 300                 # +300 and up that cashes gets the big brag
ICON = {"solo": "🎯", "two": "⚡", "three": "👑", "four": "🚀", "eight": "🎰", "lock": "🔒", "dog": "🐺"}
E = html.escape


def _am(a):
    return f"+{a}" if a > 0 else str(a)


def _money(x, sign=False):
    s = ("+" if x >= 0 else "−") if sign else ("" if x >= 0 else "−")
    return f"{s}${abs(x):,.0f}"


def _time(iso):
    t = datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT)
    return t.strftime("%-I:%M %p").replace(":00 ", " ") + " PT"


def _chip(status):
    if status == "open":                                     # the tier chip says it all - no "LOCKED" next to "LOCK"
        return ""
    txt = {"won": "CASHED ✓", "lost": "LOST", "push": "PUSH"}[status]
    return f'<span class="chip {status}">{txt}</span>'


def _the(team, league):
    """Pro teams get "the" ("the Bills"), college teams don't ("Alabama")."""
    return f"the {team}" if league in ("nfl", "nba", "mlb", "nhl") else team


def _cap(x):
    return x[:1].upper() + x[1:]


def _live_story(e, used=None):
    """A live bet in plain talk and our lingo: the score + quarter when it went up, and how it played out.
    No two bets in the list share a phrase."""
    used = set() if used is None else used
    lg = e.get("league", "")
    if lg == "tennis":
        return _tennis_live_story(e, used)
    m = re.match(r"(.+?) (\d+) @ (.+?) (\d+)$", str(e.get("score_at_post") or ""))
    if not m:
        return ""
    away, a_s, home, h_s = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    ours_away = e.get("side") == "away"
    us = _the(e["team"], lg)
    mine, theirs = (a_s, h_s) if ours_away else (h_s, a_s)
    per = re.search(r"(\d+)", str(e.get("clock_at_post") or ""))
    n = int(per.group(1)) if per else 0
    unit = {"nhl": "period", "ncaab": "half", "mlb": "inning"}.get(lg, "quarter")
    w = f"in the {({1: '1st', 2: '2nd', 3: '3rd'}.get(n, f'{n}th'))} {unit}" if n else "mid-game"
    an, hn = _the(away, lg), _the(home, lg)
    what = "come back" if mine < theirs else "hold on" if mine > theirs else "take it"
    res = e.get("result")
    best = e.get("best_odds") or e.get("odds") or 0
    ran = res == "won" and best >= (e.get("odds") or 0) + 40      # the line ran long while it was up - and it cashed
    seed = f'{e.get("posted") or e.get("date")}|{e["team"]}|{e.get("odds")}'    # stable: same bet, same words
    return sports_lingo.live_story(res, seed, used, ran=ran, an=an, a=a_s, hn=hn, h=h_s, w=w, us=us, what=what, best=best)


def _live_icon(e):
    return "🎾" if e.get("league") == "tennis" else sd.LEAGUES.get(e["league"], ("", "", "", "🏟️"))[3]


def _live_sport(e):
    if e.get("league") == "tennis":
        return "Women's Tennis" if e.get("tour") == "wta" else "Men's Tennis"
    return sd.LEAGUES.get(e["league"], ("", "", e["league"].upper()))[2]


def _tennis_live_story(e, used):
    """A 🎾 live bet in our lingo: the set/game score when it went up (from our player's side) and how it played out."""
    t = e.get("tennis") or {}
    side = int(t.get("side") or e.get("side") or 1)
    import sports_tennis as stn
    me = stn._say_name(e.get("team")) or "our player"
    he = "she" if e.get("tour") == "wta" else "he"
    flip = (lambda xy: tuple(xy)) if side == 1 else (lambda xy: tuple(xy)[::-1])
    sets = ", ".join("-".join(map(str, flip(x))) for x in t.get("done") or [])
    g = flip(t.get("games") or (0, 0))
    now_ = f"{g[0]}-{g[1]} in set {t.get('set_no') or 1}"
    seed = f'{e.get("posted") or e.get("date")}|{e.get("team")}|{e.get("odds")}'
    score = sports_lingo.say("tn:score", seed, used, at=f"{sets + ', ' if sets else ''}{now_}")
    dd = " We doubled down on our pregame pick" if e.get("double_down") else ""
    res = e.get("result")
    if res == "won":
        end = sports_lingo.say("tn:won", seed, used, me=me, he=he, his="her" if he == "she" else "his")
    elif res == "lost":
        end = sports_lingo.say("tn:lost", seed, used, me=me, his="her" if he == "she" else "his")
    elif res == "void":
        end = "Voided — no result, no harm."
    else:
        end = sports_lingo.say("tn:pend", seed, used, me=me)
    return f"{score}{dd + '.' if dd else ''} {end}"


TIER_CHIP = {"ou": '<span class="chip val">📏 O/U</span>', "lock": '<span class="chip lk">🔒 LOCK</span>', "value": '<span class="chip val">🔥 VALUE</span>',
             "lean": '<span class="chip lean">🟡 SLIGHT LEAN</span>', "strong": '<span class="chip lean">💪 STRONG LEAN</span>'}
TIER_LOOK = {"lock": ("🔒 LOCKS", "#22e39a", "#0fb87a"), "value": ("🔥 VALUE", "#ff5a1f", "#ff8a00"),
             "lean": ("🟡 LEANS", "#ffc233", "#e8c77a")}


def _tier(pk):
    import sports
    return sports.pick_tier(pk)


def _wl_words(ps, h):
    """'3 won · 4 lost · 43%' - so a 3-4 record can't be read as '3 of 4'."""
    if h is None:
        return "no results yet"
    return f"{h:.0%}"


def _rot(k, options):
    """The day's line from a rotation: consecutive days never get the same one."""
    return options[k % len(options)]


def _breakdown(leg):
    secs = leg.get("breakdown")
    if not secs:
        return ""
    body = "".join(f"<p>{E(x)}</p>" for x in secs if isinstance(x, str))
    return f'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">{body}</div></details>'


LEG_TAG = {"ou": '<span class="lt-t val">📏 O/U</span>', "lock": '<span class="lt-t lk">🔒 LOCK</span>', "value": '<span class="lt-t val">🔥 VALUE</span>',
           "lean": '<span class="lt-t lean">🟡 SLIGHT LEAN</span>', "strong": '<span class="lt-t lean">💪 STRONG LEAN</span>'}


def _leg(leg, tagged=False):
    import sports
    lg = sd.LEAGUES[leg["league"]]
    lt_ = leg.get("tier") or sports.leg_tier({**leg, "edge_own": leg.get("edge_own", leg.get("edge", 0))})
    if lt_ == "lean" and (leg.get("p") or 0) >= sports.STRONG_LEAN_P:
        lt_ = "strong"                                       # some leans are stronger than others (60%+ to win/cover)
    ltag = LEG_TAG[lt_] if tagged else ""
    mk = "ML" if leg["market"] == "ml" else f'{leg["line"]:g}' if leg["market"] == "total" else f'{leg["line"]:+g}'
    res = leg.get("result")
    mark = ""
    badge = {"won": '<span class="lr won">✅ HIT</span>', "lost": '<span class="lr lost">❌ MISS</span>',
             "push": '<span class="lr push">PUSH</span>', "void": '<span class="lr push">VOID</span>'}.get(res, "")
    why = " · ".join(E(r) for r in leg.get("reasons") or [])
    pub = leg.get("public")
    tag = ('<span class="pub fade">🤡 FADING THE PUBLIC</span>' if pub == "fade" else
           '<span class="pub ride">🤝 RIDING WITH THE PUBLIC</span>' if pub == "ride" else "")
    outs = f'<div class="outs">🚑 {E(leg["opp"])} missing: {E(", ".join(leg["opp_outs"]))}</div>' if leg.get("opp_outs") else ""
    if leg.get("injury_alerts") and not res:            # a status changed after we posted it: loud, right on the card
        outs += "".join(f'<div class="outs">⚠️ INJURY ALERT: {E(a)}</div>' for a in leg["injury_alerts"][-3:])
    return f"""<div class="leg {res or ''}">
  <div class="lt"><span class="lgb">{lg[3]} {lg[2]}{ltag}</span>{badge or f'<span class="tm" data-start="{E(leg["start"])}" data-gid="{E(leg.get("game_id", ""))}">{_time(leg["start"])}</span>'}</div>
  <div class="lm"><span class="pick">{mark}{E(leg["team"])} <em>{mk}</em></span><span class="od">{_am(leg["odds"])}</span></div>
  <div class="ls">{E(leg["opp"]) if leg["market"] == "total" else ("vs " if leg["home"] else "@ ") + E(leg["opp"])}</div>
  {f'<div class="why">{why}</div>' if why else ""}{f'<div class="pubs">{tag}</div>' if tag else ""}{outs}{_breakdown(leg)}
  {f'<div class="fin">Final: {E(leg["score"])}</div>' if leg.get("score") else ""}
</div>"""


FULL_BOARD = ("lock", "dog", "two", "three", "four")


def _short_note(day, day_picks):
    """A short board says so up top (fewer than the usual 5 plays, not a one-game day) - so nobody thinks it broke."""
    have = {p["kind"] for p in day_picks if not p.get("lean")}           # (a waiting card is still coming: it counts)
    n = sum(k in have for k in FULL_BOARD)
    if not n or n >= len(FULL_BOARD) or "solo" in have:
        return ""
    return f'<div class="drop leanday">🔒 {E(sports_lingo.short_note(n, day))}</div>'


def _lean_note(day):
    """The top note on a leans-only day, in our voice (a different wording day to day)."""
    return f'<div class="drop leanday">🟡 {E(sports_lingo.lean_note(day))}</div>'      # one note - no second disclaimer under it


def _pick_card(kind, pk):
    import sports                                            # (the strong-lean bar lives there)
    label, c1, c2 = LOOK[kind]
    if pk and pk.get("lean") and pk.get("legs"):             # a LEAN is never titled Lock/Dog of the Day
        c1, c2 = "#ffc233", "#e8c77a"
        if len(pk["legs"]) == 1:
            l0 = pk["legs"][0]
            mk = "ML" if l0["market"] == "ml" else f'{l0["line"]:g}' if l0["market"] == "total" else f'{l0["line"]:+g}'
            label = E(f'{l0["team"]} {mk}'.upper())       # the chip says SLIGHT LEAN / STRONG LEAN
        else:
            label = f'{len(pk["legs"])}-LEG LEAN PARLAY'   # every leg wears its own SLIGHT / STRONG tag

    if kind == "solo" and pk.get("legs"):                    # a one-game day: the header IS the pick (BEARS +3.5)
        l0 = pk["legs"][0]
        mk = "ML" if l0["market"] == "ml" else f'{l0["line"]:g}' if l0["market"] == "total" else f'{l0["line"]:+g}'
        label = E(f'{l0["team"]} {mk}'.upper())
    if not pk:
        return f"""<section class="pk" style="--c1:{c1};--c2:{c2}"><div class="pk-h"><span class="pk-i">{ICON[kind]}</span>
<span class="pk-l">{label}</span></div><div class="nopick">No play today — nothing on the slate has real value. We don't force it.</div></section>"""
    if pk["status"] == "waiting":
        why = " · ".join(E(w) for w in pk.get("waiting") or [])
        return f"""<section class="pk waiting" style="--c1:{c1};--c2:{c2}"><div class="pk-h"><span class="pk-i">{ICON[kind]}</span>
<span class="pk-l">{label}</span><span class="chip waiting">PICK COMING</span></div>
<div class="lock">⏳ Waiting on: {why}</div><div class="lock">Posted by {_time(pk["deadline"])} at the latest — once it's up, it's final.</div></section>"""
    win = pk["stake"] * (pk["dec"] - 1)
    legs = "".join(_leg(leg, tagged=len(pk["legs"]) > 1) for leg in pk["legs"])   # parlays: each leg shows its own tier
    stamp = {"won": '<div class="stamp won">CASHED</div>', "lost": '<div class="stamp lost">LOST</div>',
             "push": '<div class="stamp push">PUSH</div>'}.get(pk["status"], "")
    hits = sum(l.get("result") == "won" for l in pk["legs"])
    left = sum(not l.get("result") for l in pk["legs"])
    track = (f'<div class="track">🔥 {hits} of {len(pk["legs"])} legs hit — {left} to go</div>'
             if pk["status"] == "open" and len(pk["legs"]) > 1 and hits and left else "")
    spin = datetime.strptime(pk["date"], "%Y-%m-%d").toordinal() + sum(map(ord, pk["legs"][0]["team"])) + list(LOOK).index(kind)
    book_wrong = ('<div class="bw">' + _rot(spin, [       # rotates by day and team - never the same line on repeat
                      "🔒 Plus money? The line makers trippin'. This a LOCK.",
                      "🔒 The line makers trippin' on this one. Plus money and it's a LOCK.",
                      "🔒 Books got this wrong — the line makers trippin'. LOCK it in.",
                      "🔒 They got us as the dog? Line makers trippin'. We calling it a LOCK.",
                      "🔒 Plus money on this? Somebody at the book was sleepin'. LOCK.",
                      "🔒 The books ain't see what we see. Plus money and a LOCK — let's eat.",
                      "🔒 Line makers trippin' fr. We're getting paid extra on a LOCK.",
                      "🔒 The book priced this wrong and we ain't complaining. Plus money LOCK."]) + '</div>'
                  if _tier(pk) == "lock" and pk.get("american", 0) > 0 and pk["status"] == "open" else "")
    return f"""<section class="pk {pk["status"]}" style="--c1:{c1};--c2:{c2}">
  <div class="pk-h"><span class="pk-i">{ICON[kind]}</span><span class="pk-l{' pk-big' if kind == 'solo' else ''}">{label}</span>{TIER_CHIP["strong" if _tier(pk) == "lean" and (pk["legs"][0].get("p") or 0) >= sports.STRONG_LEAN_P else _tier(pk)] if len(pk["legs"]) == 1 else ""}{_chip(pk["status"])}</div>
  <div class="pk-o"><span class="big">{_am(pk["american"])}</span>
    <span class="pay">$100 wins <b>${win:,.0f}</b></span></div>
  {f'<div class="stamp-row">{stamp}</div>' if stamp else ""}{book_wrong}{track}{legs}
</section>"""


def _delayed(l):
    """Past its start time but the feed says it hasn't started (tennis order of play slips all the time)."""
    try:
        st = datetime.strptime(l["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return False
    return l.get("state") == "pre" and datetime.now(timezone.utc) > st + timedelta(minutes=20)


def _tennis():
    """🎾 TENNIS BONUS: collapsed at the very bottom (tap to open) - the latest slate, its parlay, its own record."""
    try:
        with open(os.path.join(sd.DATA, "tennis", "picks.json")) as f:
            slates = json.load(f)
    except (OSError, ValueError):
        slates = []
    if not slates:
        return ""
    import sports_tennis as stn
    r = stn.record(slates)                                   # men's and women's apart; a match counts once
    badge = {"won": '<span class="lr won">✅ HIT</span>', "lost": '<span class="lr lost">❌ MISS</span>',
             "void": '<span class="lr push">VOID</span>'}

    used, recaps = set(), {}                                 # (no 4-word run twice in the recaps on the card)

    def ours(l):
        """The score from OUR player's side (the feed lists player 1 first)."""
        sets = []
        for s_ in (l.get("score") or "").split(","):
            a, _, b = s_.strip().partition("-")
            if a[:1].isdigit() and b[:1].isdigit():
                sets.append((a, b) if l.get("side", 1) == 1 else (b, a))
        return sets

    def recap(l):
        """The result, in our voice, on top of a graded pick's breakdown (rolled by the pick's id: stable)."""
        if l["id"] in recaps:
            return recaps[l["id"]]
        who = l["player"].split()[-1]
        his = "her" if stn.tour_of(l) == "wta" else "his"
        sets = ours(l)
        sc = f" ({', '.join(f'{a}-{b}' for a, b in sets)})" if sets else ""
        won_sets = sum(int(a[:1]) > int(b[:1]) for a, b in sets)
        lost_match = bool(sets) and won_sets * 2 < len(sets)
        out = ""
        if l.get("result") == "won" and l.get("market") == "spread" and lost_match:
            out = sports_lingo.say("rc:cover", l["id"], used, who=who, sc=sc, hcp=f"{l['hcp']:+g}")
        elif l.get("result") == "won":
            out = sports_lingo.say("rc:won", l["id"], used, who=who, sc=sc, his=his)
        elif l.get("result") == "lost":
            out = sports_lingo.say("rc:lost", l["id"], used, who=who, sc=sc, his=his)
        elif l.get("result") == "void":
            out = "🤷 Voided — no result, no harm."
        recaps[l["id"]] = out
        return out

    def row(l):
        bd = "".join(f"<p>{E(x)}</p>" for x in ([recap(l)] if recap(l) else []) + list(l.get("breakdown") or []))
        return f"""<div class="leg {l['result'] or ''}">
  <div class="lt"><span class="lgb">🎾 {"Women's Tennis" if stn.tour_of(l) == "wta" else "Men's Tennis"} · {E(l['tourney'])}</span>{badge.get(l['result']) or (f'<span class="tm dly">⏳ DELAYED</span>' if _delayed(l) else f'<span class="tm" data-start="{E(l["start"])}" data-gid="tennis:{E(l.get("match", ""))}" data-side="{E(str(l.get("side", "")))}">{_time(l["start"])}</span>')}</div>
  <div class="lm"><span class="pick">{E(l['player'])} <em>{f"{l['hcp']:+g} games" if l.get("market") == "spread" else "ML"}</em></span><span class="od">{_am(l['odds'])}</span></div>
  <div class="ls">vs {E(l['opp'])} · {E(l['round'])} · {E({"hard": "Hard court", "clay": "Clay", "grass": "Grass"}.get(l['surface'], l['surface']))}</div>
  {f'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">{bd}</div></details>' if bd else ""}
  {f'<div class="fin">Final: {E(", ".join(f"{a}-{b}" for a, b in ours(l)) or l["score"])}</div>' if l.get("score") else ""}
</div>"""
    PAR_TITLE = {"atp": "MEN'S TENNIS PARLAY", "wta": "WOMEN'S TENNIS PARLAY", "mixed": "TENNIS PARLAY OF THE DAY"}

    def par_card(key, par, legs):
        stamp = {"won": '<div class="stamp won">CASHED</div>', "lost": '<div class="stamp lost">LOST</div>'}.get(par["status"], "")
        return f"""<section class="pk {par['status']}" style="--c1:#c6f000;--c2:#1fd17a">
  <div class="pk-h"><span class="pk-i">🎾</span><span class="pk-l">{PAR_TITLE[key]}</span>{_chip(par["status"])}</div>
  <div class="pk-o"><span class="big">{_am(par['american'])}</span><span class="pay">$100 wins <b>${100 * (par['dec'] - 1):,.0f}</b></span></div>
  {f'<div class="stamp-row">{stamp}</div>' if stamp else ""}{"".join(row(legs[i]) for i in par["legs"] if i in legs)}
</section>"""

    def block(s):
        legs = {l["id"]: l for l in s["picks"]}
        pars = dict(stn.parlays_of(s))
        day = datetime.strptime(s["date"], "%Y-%m-%d").strftime("%A, %B %-d")
        out = f'<div class="tn-d">{E(day)}</div>'
        if "mixed" in pars:                                  # an old slate's one parlay (both tours): as it was posted
            out += par_card("mixed", pars["mixed"], legs)
        for t, title in (("atp", "MEN'S TENNIS"), ("wta", "WOMEN'S TENNIS")):    # each tour: its picks + its parlay
            ls = [l for l in s["picks"] if stn.tour_of(l) == t]
            if ls:
                out += (f'<section class="pk" style="--c1:#c6f000;--c2:#1fd17a"><div class="pk-h"><span class="pk-i">🎾</span>'
                        f'<span class="pk-l">{title}</span></div>{"".join(row(l) for l in ls)}</section>')
            if t in pars:
                out += par_card(t, pars[t], legs)
        return out
    # a slate stays up (WON / LOST and the breakdowns) while any of its matches is still being played; once its last
    # match is over, the whole slate goes away into the results. A new slate shows as soon as it's posted.
    live = lambda x: any(l.get("result") is None for l in x["picks"]) or any(p["status"] == "open" for _, p in stn.parlays_of(x))
    shown = [x for x in slates if live(x)]
    nm = sum(stn.tour_of(l) == "atp" for x in shown for l in x["picks"])
    nw = sum(stn.tour_of(l) == "wta" for x in shown for l in x["picks"])
    what = f"{nm} men's + {nw} women's" if nm + nw else "new picks by 6 PM"
    body = "".join(block(x) for x in shown) or \
        '<div class="nopick">The last slate\'s all graded — it\'s in the records. Next picks drop by 6 PM. 🎾</div>'
    m_, w_, x_ = r["atp"], r["wta"], r["mixed"]
    pars = (f"parlays: men's {m_['p_won']}-{m_['p_lost']} · women's {w_['p_won']}-{w_['p_lost']}"
            + (f" · old mixed {x_['p_won']}-{x_['p_lost']}" if x_["p_won"] + x_["p_lost"] else ""))
    return f"""<details class="tn"><summary><span class="tn-t">🎾 TENNIS BONUS</span>
<span class="tn-s">{what} · men's {m_['won']}-{m_['lost']} · women's {w_['won']}-{w_['lost']} · tap to open</span></summary>
<div class="tn-b"><div class="tn-d">{pars}</div>{body}</div></details>"""


def _jl(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _history(picks):
    """📜 PAST RESULTS: tap open any sport and see every pick that won or lost, newest first."""
    ok = {"won": "✅", "lost": "❌", "push": "➖"}
    kinds = {"lock": "Lock of the Day", "dog": "Dog of the Day", "two": "2-Leg", "three": "3-Leg", "four": "4-Leg",
             "eight": "8-Leg", "solo": "One-Game Pick"}

    def day(d):
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%b %-d")
        except ValueError:
            return d

    def bet(l):
        if l.get("market") == "total":
            return f'{"Over" if l.get("side") == "over" else "Under"} {l.get("line"):g}'
        if l.get("market") == "spread" and l.get("line") is not None:
            return f'{l["team"]} {l["line"]:+g}'
        return f'{l["team"]} ML'

    def rows(items):
        return "".join(f'<div class="hr {x[1]}"><span class="hd">{day(x[0])}</span><span class="hw">{ok.get(x[1], "")}</span>'
                       f'<span class="hp">{E(x[2])}<small>{E(x[3])}</small>'
                       f'{f"<em>{E(x[4])}</em>" if len(x) > 4 and x[4] else ""}</span></div>' for x in items)

    # every review is rolled from its own pick (seeded by date + pick: the same words every run), and they're all
    # written oldest first against ONE set of 4-word runs - so nothing repeats anywhere in the section, and a new
    # pick never rewords the older ones.
    todo = []
    BIG = {"nfl": 14, "ncaaf": 14, "nba": 15, "ncaab": 15, "mlb": 5, "nhl": 3}
    CLOSE = {"nfl": 3, "ncaaf": 3, "nba": 4, "ncaab": 4, "mlb": 1, "nhl": 1}

    def later(date, seed, kind, r, lean=False, **kw):
        cell = {"key": (date or "", seed), "args": (kind, r, f"{date}|{seed}"), "lean": lean, "kw": kw, "text": ""}
        todo.append(cell)
        return cell

    def margin(score, team):
        m_ = re.match(r"(.+?) (\d+) @ (.+?) (\d+)$", score or "")
        if not m_:
            return None
        a, x, b, y = m_.group(1), int(m_.group(2)), m_.group(3), int(m_.group(4))
        return x - y if a == team else y - x if b == team else None

    def rev_leg(l, r, date, p=None, lean=False):
        """The review for one game pick: blowout / close / confident-and-folded / fav / dog / spread / total."""
        lg, mg = l.get("league"), margin(l.get("score"), l.get("team"))
        t_, o_ = _the(l["team"], lg), _the(l.get("opp", "them"), lg)
        kind = "spread" if l.get("market") == "spread" else "dog" if (l.get("odds") or 0) > 0 else "fav"
        x = f'{l["line"]:+g}' if l.get("line") is not None else ""
        if l.get("market") == "total":
            kind, t_, x = "total", f'{"Over" if l.get("side") == "over" else "Under"} {l.get("line"):g}', f'{l.get("line"):g}'
        elif mg is not None and abs(mg) >= BIG.get(lg, 99) and (mg > 0) == (r == "won"):
            kind = "big"
        elif mg is not None and abs(mg) <= CLOSE.get(lg, 0) and kind != "spread":
            kind = "close"
        elif r == "lost" and (p or l.get("p") or 0) >= 0.6:
            kind = "conf"
        return later(date, f'{l.get("game_id")}|{l.get("side")}|{l.get("market")}', kind, r, lean, t=t_, o=o_, x=x)

    def box(title, items):
        if not items:
            return ""
        items = sorted(items, key=lambda x: x[0], reverse=True)
        w, l_ = sum(x[1] == "won" for x in items), sum(x[1] == "lost" for x in items)
        return (f'<details class="hs"><summary><b>{title}</b><span>{w}-{l_}'
                f'{f" · {w / (w + l_):.0%}" if w + l_ else ""}</span></summary>{rows(items)}</details>')

    # our record, by sport: every leg we posted (a team we're on in two picks the same day shows once, with both cards)
    legs = {}
    for p in picks:
        if p.get("lean") or p["status"] not in ("won", "lost", "push", "open"):
            continue
        for l in p["legs"]:
            if l.get("result") not in ("won", "lost", "push"):
                continue
            k = (p["date"], l["game_id"], l["side"], l.get("market"))
            e = legs.setdefault(k, {"l": l, "date": p["date"], "cards": []})
            e["cards"].append(kinds.get(p["kind"], p["kind"]))
    by = {}
    for e in legs.values():
        l = e["l"]
        by.setdefault(l["league"], []).append(
            (e["date"], l["result"], f'{bet(l)} ({_am(l["odds"])})', f' · {" + ".join(dict.fromkeys(e["cards"]))}'
             + (f' · {l["score"]}' if l.get("score") else ""), rev_leg(l, l["result"], e["date"])))
    # the parlays, as tickets
    tix = [(p["date"], p["status"], f'{kinds.get(p["kind"], p["kind"])} ({_am(p["american"])})',
            " · " + ", ".join(bet(l) + ("" if l.get("result") in (None, "won") else " ❌") for l in p["legs"]),
            later(p["date"], p["kind"], "parlay", p["status"],
                  x=" and ".join(bet(l) if l.get("market") == "total" else _the(l["team"], l["league"])
                                 for l in p["legs"] if l.get("result") == "lost")))
           for p in picks if not p.get("lean") and len(p["legs"]) > 1 and p["status"] in ("won", "lost")]
    # their own records
    lean = [(p["date"], p["status"], f'{bet(p["legs"][0])} ({_am(p["legs"][0]["odds"])})',
             f' · {sd.LEAGUES.get(p["legs"][0]["league"], ("", "", ""))[2]}'
             + (f' · {p["legs"][0]["score"]}' if p["legs"][0].get("score") else ""),
             rev_leg(p["legs"][0], p["status"], p["date"], lean=True))              # a lean: no hype, win or lose
            for p in picks if p.get("lean") and p["status"] in ("won", "lost") and p.get("legs")]
    live = ((_jl(os.path.join(sd.DATA, "live_log.json"), {}) or {}).get("plays") or {}).values()

    def rev_live(e):
        mg = margin(e.get("score_at_post"), e.get("team"))
        lg = e.get("league")
        opp = e.get("opp") or next((x for x in re.split(r" \d+ @ | \d+$", e.get("score_at_post") or "") if x and x != e.get("team")), "them")
        pro = {"atp": ("him", "his"), "wta": ("her", "her")}.get(e.get("tour"), ("them", "their"))
        return later(e.get("date", ""), f'live|{e.get("team")}|{e.get("posted")}',
                     "live_up" if mg is not None and mg > 0 else "live_back", e["result"],
                     t=_the(e.get("team", ""), lg) if lg in sd.LEAGUES else e.get("team", ""),
                     o=_the(opp, lg) if lg in sd.LEAGUES else opp, pro=pro[0], pos=pro[1])
    lv = [(e.get("date", ""), e["result"], f'{e.get("team")} ML ({_am(e["odds"])})',
           f' · {sd.LEAGUES.get(e.get("league"), ("", "", "🎾 Tennis"))[2]}'
           + (f' · went up at {e["score_at_post"]} ({e.get("clock_at_post", "")})' if e.get("score_at_post") else ""),
           rev_live(e))
          for e in live if e.get("result") in ("won", "lost")]
    tn = {"atp": [], "wta": []}
    seen = set()
    for sl in reversed(_jl(os.path.join(sd.DATA, "tennis", "picks.json"), []) or []):
        for l in sl.get("picks") or []:
            key = l.get("match") or l["id"]
            if l.get("result") not in ("won", "lost") or key in seen:
                continue
            seen.add(key)
            sc = ", ".join(s_.strip() if l.get("side", 1) == 1 else "-".join(reversed(s_.strip().split("-")))
                           for s_ in (l.get("score") or "").split(",") if s_.strip())
            b_ = f'{l["player"]} {l["hcp"]:+g} games' if l.get("market") == "spread" and l.get("hcp") is not None else f'{l["player"]} ML'
            tkind = "spread" if l.get("market") == "spread" else "dog" if (l.get("odds") or 0) > 0 else "fav"
            wta = l.get("tour") == "wta"
            trev = later(sl["date"], l["id"], tkind, l["result"], t=l["player"].split()[-1],
                         o=(l.get("opp") or "them").split()[-1], pro="her" if wta else "him", pos="her" if wta else "his",
                         x=f'{l["hcp"]:+g} games' if l.get("hcp") is not None else "")
            tn["wta" if wta else "atp"].append(
                (sl["date"], l["result"], f'{b_} ({_am(l["odds"])})', f' · vs {l.get("opp", "")}' + (f" · {sc}" if sc else ""), trev))
    used = set()                                             # one set of 4-word runs for the whole section
    for c in sorted(todo, key=lambda c: c["key"]):
        kind, r, seed = c["args"]
        c["text"] = sports_lingo.review(kind, r, seed, used, lean=c["lean"], **c["kw"])
    done = lambda items: [x[:4] + (x[4]["text"],) for x in items]
    out = "".join(box(f'{sd.LEAGUES[lg][3]} {sd.LEAGUES[lg][2]}', done(by.get(lg, []))) for lg in sd.LEAGUES)
    out += box("🎟️ Parlays", done(tix))
    own = (box("📡 Live plus money", done(lv)) + box("🟡 Leans", done(lean)) + box("🎾 Men's Tennis", done(tn["atp"]))
           + box("🎾 Women's Tennis", done(tn["wta"])))
    if not out and not own:
        return ""
    return (f'<details class="hist"><summary>📜 PAST RESULTS <span>every pick, won or lost — tap a sport</span></summary>'
            f'{out}{f"<div class=hs-own>THEIR OWN RECORDS</div>{own}" if own else ""}</details>')


def _ask_url():
    """The AI question box relay (set by the deploy_ask workflow) - also the live bet alerts' Worker. "" if not live."""
    try:
        with open(os.path.join(sd.DATA, "ask_url.txt")) as f:
            ask_url = f.read().strip()
    except OSError:
        return ""
    return ask_url if re.fullmatch(r"https://[A-Za-z0-9.-]+\.workers\.dev/?", ask_url or "x") else ""


# 🔔 The live bet alerts' service worker (scope /autonomous-crypto-engine/sports/). The pushes carry no payload, so on
# each one it asks the Worker what to show - and it ALWAYS shows something (iOS drops sites that push silently).
SW = r"""// 🔔 D503 live bet alerts - written by sports_dashboard.py
const API = "__API__";
const DASH = "https://d503therapper.github.io/autonomous-crypto-engine/sports/";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
async function myHash() {           // the Worker keys this phone by the SHA-256 of its endpoint (for its welcome)
  try {
    const s = await self.registration.pushManager.getSubscription();
    if (!s) return "";
    const d = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s.endpoint)));
    let b = "";
    for (const x of d) b += String.fromCharCode(x);
    return btoa(b).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  } catch (e) {
    return "";
  }
}
async function alertNow() {
  let m = {};
  try {
    if (!API) throw new Error("no worker");
    const ctl = new AbortController();
    const to = setTimeout(() => ctl.abort(), 6000);
    const h = await myHash();
    const r = await fetch(API + "/latest" + (h ? "?sub=" + h : ""), { cache: "no-store", signal: ctl.signal });
    clearTimeout(to);
    if (r.ok) m = await r.json();
  } catch (e) { /* the fallback below still shows */ }
  return self.registration.showNotification(m.title || "🔥 D503 LIVE BET", {
    body: m.body || "The algorithm just triggered a live bet. Tap to see it. 📡",
    tag: m.id || "d503-live",
    renotify: true,
    icon: "icon-512.png?v=8",
    badge: "icon-512.png?v=8",
    data: { url: m.url && m.url.indexOf(DASH) === 0 ? m.url : DASH },
  });
}
self.addEventListener("push", (e) => e.waitUntil(alertNow()));
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || DASH;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    for (const c of cs) if (c.url.indexOf(DASH) === 0 && "focus" in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});
"""


def write_sw(path):
    """docs/sports/sw.js - only rewritten when it changes (a changed SW makes every phone re-install it)."""
    body = SW.replace("__API__", _ask_url().rstrip("/"))
    try:
        with open(path) as f:
            if f.read() == body:
                return
    except OSError:
        pass
    with open(path, "w") as f:
        f.write(body)


def render(picks, model, games, series, start_bank, updated_ms):
    now = datetime.now(PT)
    today = now.date().isoformat()
    order = list(LOOK)
    todays = sorted((p for p in picks if p["date"] == today), key=lambda p: (order.index(p["kind"]) if p["kind"] in order else 99, p.get("posted") or ""))
    active = [p for p in todays if p["status"] in ("open", "waiting")]      # the top is only what's still live
    board_date = now.strftime("%A, %B %-d")
    ask_url = _ask_url()
    ask_note = ("Tap in! Ask me whatever the fuck. No stupid shit though. Ain't nobody got time for that." if ask_url else
                "Ask about any game — who wins, spreads, first half. Heads up: these <b>ain’t our picks</b> and don’t count toward our record.")
    ask_btn = '<button id="askgo" type="button">Ask 🧠</button>' if ask_url else ""
    bell = ('<div class="bell"><button id="bellb" type="button" hidden>🔔 Get live bet alerts</button>'   # 🔔 Web Push
            '<div class="bell-n" id="belln" hidden></div></div>') if ask_url else ""
    api = ask_url.rstrip("/")
    drop = '<div class="drop">🎯 Picks go up as soon as the engine is sure — from <b>6 PM PT</b> the night before. Once posted, they\'re final.</div>'
    done_today = ('<div class="drop">✅ Everything on today\'s board is graded — scroll down to <b>THE RESULTS</b>. '
                  'Tomorrow\'s card goes up from <b>6 PM PT</b>, and at midnight it slides up here as the new slate.</div>')
    board = "".join(_pick_card(p["kind"], p) for p in active) if active else done_today if todays else drop
    if todays and all(p.get("lean") for p in todays if p["status"] != "waiting") and any(p["status"] != "waiting" for p in todays):
        board = _lean_note(today) + board                    # a leans-only day says so up top
    elif active:
        board = _short_note(today, todays) + board           # a short board says so too

    tmr = (now + timedelta(days=1)).date()
    tomorrows = {p["kind"]: p for p in picks if p["date"] == tmr.isoformat()}
    tmr_real = [p for p in tomorrows.values() if p["status"] != "waiting"]
    tomorrow = (f'<div class="sec"><h2><i>●</i> TOMORROW\'S BOARD</h2><span>{tmr:%A, %B %-d}</span></div>'
                + (_lean_note(tmr.isoformat()) if tmr_real and all(p.get("lean") for p in tmr_real)
                   else _short_note(tmr.isoformat(), list(tomorrows.values())))
                + "".join(_pick_card(k, tomorrows[k]) for k in LOOK if k in tomorrows)) if tomorrows else ""

    graded_all = [p for p in picks if p["status"] in ("won", "lost", "push")]
    done = [p for p in graded_all if not p.get("lean")]          # the main record is value picks only
    done.sort(key=lambda p: (p["date"], p.get("settled", "")))

    def wl(ps):
        w, l_, pu = (sum(p["status"] == k for p in ps) for k in ("won", "lost", "push"))
        return f"{w}-{l_}" + (f"-{pu}" if pu else ""), (w / (w + l_) if w + l_ else None)

    def streak(ps):
        if not ps:
            return ""
        last, n = ps[-1]["status"], 0
        for p in reversed(ps):
            if p["status"] != last:
                break
            n += 1
        return f'{"W" if last == "won" else "L" if last == "lost" else "P"}{n}'
    # live bets: their own record
    live = {}
    try:
        with open(os.path.join(sd.DATA, "live_log.json")) as f:
            live = json.load(f).get("plays", {})
    except (OSError, ValueError):
        pass
    # today's live bets only (a new day starts clean - old ones live on in the records): what they were, did they cash
    days_ = {today}
    lrows = sorted((e for e in live.values() if e.get("date") in days_), key=lambda e: e["posted"], reverse=True)   # every one today - the list always matches the record
    badge_ = {"won": '<span class="lr won">✅ CASHED</span>', "lost": '<span class="lr lost">❌ LOST</span>'}
    pending_ = '<span class="tm">⏳ still going</span>'
    used_ = set()                                            # no two bets in the list share a phrase
    stories = {id(e): _live_story(e, used_) for e in sorted(lrows, key=lambda e: e["posted"])}   # oldest first: a new
    #                                                        bet never rewords the ones already on the list
    try:                                                     # owning our mistakes, right on the bet itself
        with open(os.path.join(sd.DATA, "notes.json")) as f:
            owned = {n["live"]: n["text"] for n in json.load(f) if n.get("live")}
    except (OSError, ValueError, KeyError):
        owned = {}
    pid_of = {id(e): pid for pid, e in live.items()}
    live_list = ("" if not lrows else
                 '<section class="pk" style="--c1:#22d3ee;--c2:#2f8bff;margin-top:14px"><div class="pk-h"><span class="pk-i">📡</span>'
                 '<span class="pk-l">LIVE PLUS MONEY TODAY</span></div>' + "".join(
                     f'<div class="leg {e.get("result") or ""}"><div class="lt"><span class="lgb">{_live_icon(e)} '
                     f'{E(_live_sport(e))}{" · 🔁 DOUBLE DOWN" if e.get("double_down") else ""}</span>'
                     f'{badge_.get(e.get("result"), pending_)}</div>'
                     f'<div class="lm"><span class="pick">{E(e["team"])} <em>ML</em></span><span class="od">{_am(e["odds"])}</span></div>'
                     f'<div class="ls">{E(stories[id(e)])}</div>'
                     f'{"<div class=own>" + E(owned[pid_of[id(e)]]) + "</div>" if pid_of.get(id(e)) in owned else ""}</div>'
                     for e in lrows) + "</section>")
    # the engine's grades: locks, value, leans and live - each graded on its own, never lumped into one number
    def grade(name, c1, c2, rows, today_rows):
        w_, l_ = sum(r == "won" for r in rows), sum(r == "lost" for r in rows)
        return (f'<div class="rc gr" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{name}</div><div class="rc-r">{w_} won · {l_} lost</div>'
                f'<div class="rc-p">{f"{w_ / (w_ + l_):.0%}" if w_ + l_ else "no results yet"}</div></div>')
    # locks and value: every call on the board, graded by how sure we were (a parlay's legs each count as their own call,
    # a team we're on twice the same day counts once). Leans never count; the 8-leg lottery ticket keeps its own record.
    calls = {}
    for p in sorted(picks, key=lambda p: p.get("posted") or ""):
        if p.get("lean"):
            continue
        for l in p["legs"]:
            if l.get("result") in ("won", "lost"):
                # if we posted it, it counts - labeled by the rule: minus money = lock, plus money = value
                t = "ou" if l.get("market") == "total" else "lock" if p["kind"] == "lock" or l["odds"] < 0 else "value"
                key = (p["date"], l["game_id"], l["side"])
                if calls.get(key, ("", ""))[0] != "lock":
                    calls[key] = (t, l["result"], p["date"])
    by_tier = {t: [(r, d) for tt, r, d in calls.values() if tt == t] for t in ("lock", "value")}
    ow = sum(r == "won" for _, r, _ in calls.values())       # OVERALL: every call we made (locks + value), once each
    ol = sum(r == "lost" for _, r, _ in calls.values())
    tw = sum(r == "won" for _, r, d in calls.values() if d == today)
    tl = sum(r == "lost" for _, r, d in calls.values() if d == today)
    overall = (f'<div class="ovr"><div class="ovr-t">📊 OVERALL RECORD</div><div class="ovr-r">{ow}-{ol}</div>'
               f'<div class="ovr-p">{f"{ow} won · {ol} lost · {ow / (ow + ol):.0%}" if ow + ol else "no results yet"}</div>'
               f'{f"<div class=ovr-s>today {tw}-{tl}</div>" if tw + tl else ""}</div>')
    lrs = sorted((e for e in live.values() if e.get("result") in ("won", "lost")), key=lambda e: e.get("posted", ""))
    RECORDS.clear()                                          # the same numbers the page shows, for the AI's data sheet
    def wlt(w, l):
        return f"{w}-{l}"
    RECORDS.update({"overall": wlt(ow, ol), "today": wlt(tw, tl),
                    "locks (minus money calls)": wlt(sum(r == "won" for r, _ in by_tier["lock"]), sum(r == "lost" for r, _ in by_tier["lock"])),
                    "value (plus money calls)": wlt(sum(r == "won" for r, _ in by_tier["value"]), sum(r == "lost" for r, _ in by_tier["value"])),
                    "live plus money (own record, not ours)": wlt(sum(e["result"] == "won" for e in lrs), sum(e["result"] == "lost" for e in lrs))})
    grades = "".join(grade(*TIER_LOOK[t], [r for r, _ in by_tier[t]], [r for r, d in by_tier[t] if d == today])
                     for t in ("lock", "value"))
    lotd = sorted((p for p in graded_all if p["kind"] == "lock"), key=lambda p: (p["date"], p.get("posted") or ""))
    dotd = sorted((p for p in graded_all if p["kind"] == "dog"), key=lambda p: (p["date"], p.get("posted") or ""))
    grades = (grade("🔒 LOCK OF THE DAY", "#22e39a", "#ffc233", [p["status"] for p in lotd], [p["status"] for p in lotd if p["date"] == today])
              + grade("🐺 DOG OF THE DAY", "#ff3b3b", "#ff8a00", [p["status"] for p in dotd], [p["status"] for p in dotd if p["date"] == today])
              + grades)
    # their own categories, never in our record: live bets and leans
    leans_ = sorted((p for p in graded_all if p.get("lean")), key=lambda p: (p["date"], p.get("posted") or ""))
    import sports_tennis as stn
    tennis_ = {}                                             # 🎾 tennis: men's and women's, each its own record
    tn_slates = []                                           # (a match counts once; tennis LIVE plays never count here)
    try:
        with open(os.path.join(sd.DATA, "tennis", "picks.json")) as f:
            tn_slates = json.load(f)
    except (OSError, ValueError):
        pass
    for sl in tn_slates:
        for l in sl.get("picks") or []:
            if l.get("result") in ("won", "lost"):
                tennis_[l.get("match") or l["id"]] = (stn.tour_of(l), l["result"], sl["date"])
    tn_rows = {t: sorted(((r, d) for tt, r, d in tennis_.values() if tt == t), key=lambda x: x[1]) for t in stn.TOURS}
    tn_rec = stn.record(tn_slates) if tn_slates else {t: {"p_won": 0, "p_lost": 0} for t in (*stn.TOURS, "mixed")}

    def tn_box(name, t):
        rows_ = tn_rows[t]
        pw, pl_ = tn_rec[t]["p_won"], tn_rec[t]["p_lost"]
        return grade(name, "#c6f000", "#1fd17a", [r for r, _ in rows_], [r for r, dd in rows_ if dd == today]).replace(
            "</div></div>", f'</div><div class="rc-s">parlays {pw}-{pl_}</div></div>', 1)
    others = (grade("📡 LIVE PLUS MONEY", "#22d3ee", "#2f8bff", [e["result"] for e in lrs], [e["result"] for e in lrs if e.get("date") == today])
              + grade("🟡 LEANS", "#ffc233", "#e8c77a", [p["status"] for p in leans_], [p["status"] for p in leans_ if p["date"] == today])
              + tn_box("🎾 MEN'S TENNIS", "atp") + tn_box("🎾 WOMEN'S TENNIS", "wta"))
    for t, label in (("atp", "men's tennis"), ("wta", "women's tennis")):
        RECORDS[f"{label} (own record, not ours)"] = wlt(sum(r == 'won' for r, _ in tn_rows[t]), sum(r == 'lost' for r, _ in tn_rows[t]))
        RECORDS[f"{label} parlays"] = wlt(tn_rec[t]["p_won"], tn_rec[t]["p_lost"])
    if tn_rec["mixed"]["p_won"] + tn_rec["mixed"]["p_lost"]:
        RECORDS["old mixed tennis parlays (before the tours were split)"] = wlt(tn_rec["mixed"]["p_won"], tn_rec["mixed"]["p_lost"])
    # by sport: just our hit rate on the board - locks, value, leans (live bets are their own category; the 8-leg stays out)
    groups = [("🏈 NFL", ("nfl",)), ("🏈 College Football", ("ncaaf",)), ("🏀 NBA", ("nba",)),
              ("🏀 College Basketball", ("ncaab",)), ("⚾ Baseball", ("mlb",)), ("🏒 Hockey", ("nhl",))]
    seen_ = {}                                               # a team we're on in two picks the same day counts once
    for p in picks:
        if not p.get("lean"):                              # our daily record only: no leans, no live bets
            for l in p["legs"]:
                if l.get("result") in ("won", "lost"):     # if we posted it, it counts
                    seen_[(p["date"], l["game_id"], l["side"])] = (l["league"], l["result"])
    res = list(seen_.values())
    res += [(f"tennis_{t}", r) for t, r, _ in tennis_.values()]   # 🎾 men's and women's apart (a match counts once)
    tn_groups = [("🎾 Men's Tennis", ("tennis_atp",)), ("🎾 Women's Tennis", ("tennis_wta",))]
    chips = []
    for name, lgs in groups + tn_groups:
        rr = [r for lg, r in res if lg in lgs]
        w_, n_ = sum(r == "won" for r in rr), len(rr)
        hue = "#9fb0c8" if not n_ else "#22e39a" if w_ / n_ >= 0.55 else "#ffc233" if w_ / n_ >= 0.45 else "#ff5a5a"
        chips.append(f'<div class="spc"><span><b>{name}</b><small>{f"{w_}-{n_ - w_}" if n_ else "no results yet"}</small></span>'
                     f'<i style="color:{hue}">{f"{w_ / n_:.0%}" if n_ else "—"}</i></div>')
    by_sport = "".join(chips)
    RECORDS["by sport"] = {name.split(" ", 1)[1]: wlt(sum(r == 'won' for lg, r in res if lg in lgs),
                                                      sum(r == 'lost' for lg, r in res if lg in lgs)) for name, lgs in groups + tn_groups}
    # record per pick type
    rec = []
    for kind, (label, c1, c2) in LOOK.items():
        if kind in ("lock", "dog"):                          # (their own boxes up top - no double boxes)
            continue
        ps = [p for p in graded_all if p["kind"] == kind]
        if kind in ("eight", "solo") and not ps:             # the retired 8-leg / one-game-day pick: only with history
            continue
        r, h = wl(ps)
        RECORDS.setdefault("by pick", {})[label] = r
        rec.append(f'<div class="rc" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{ICON[kind]} {label.replace(" OF THE DAY", "")}</div>'
                   f'<div class="rc-r">{sum(p["status"] == "won" for p in ps)} won · {sum(p["status"] == "lost" for p in ps)} lost</div>'
                   f'<div class="rc-p">{_wl_words(ps, h)}</div></div>')


    # the brain, in a nutshell - only what actually happened, in our voice, rotating day to day
    params = model.get("params", {})
    k = now.toordinal()
    lines = []
    try:                                                      # owning our mistakes: notes on what we fixed (that day only)
        with open(os.path.join(sd.DATA, "notes.json")) as f:
            lines += [n["text"] for n in json.load(f) if n.get("date") == today and not n.get("live")]
    except (OSError, ValueError, KeyError):
        pass
    graded = [p for p in done if p["date"] == today and p["kind"] != "eight"]           # a new day never talks about yesterday
    w_, l_ = sum(p["status"] == "won" for p in graded), sum(p["status"] == "lost" for p in graded)
    live_today = any(e.get("result") in ("won", "lost") and e.get("date") == today for e in live.values())
    if w_ + l_ == 0 and live_today:
        pass                                                      # the live results below speak for the day
    elif any(p["date"] == today and p["kind"] != "eight" and p["status"] == "open" for p in picks):
        lines.append(_rot(k, [f"⏳ {w_}-{l_} so far today — still got tickets live. We gon' see.",
                              f"⏳ {w_}-{l_} so far. Tickets still cooking — we finna see.",
                              f"⏳ Sitting at {w_}-{l_} right now. Day ain't over — more tickets still cooking.",
                              f"⏳ {w_}-{l_} so far. Still got action on the board — the day ain't done."]))
    elif w_ + l_ == 0:
        lines.append(["⏳ Nothing graded yet today — games still cooking.", "⏳ Tickets are still live. Check back after the games.",
                      "⏳ No results in yet. Sit tight."][k % 3])
    elif l_ == 0:
        lines.append(_rot(k, [f"🔥 {w_}-0. We crushed today — fuck yeah, let's go!",
                              f"🔥 {w_}-0. Today was a grace from baby Jesus himself. Let's fucking go!",
                              f"🔥 Clean sweep, {w_}-0. We smacked today. Let's go!",
                              f"🔥 {w_}-0. Didn't miss a single one. Trust the algorithm.",
                              f"🔥 {w_}-0. Today was a grace from Jesus. Let's fucking go!",
                              f"🔥 Perfect day, {w_}-0. Books are crying right now."]))
    elif w_ >= l_:
        lines.append(_rot(k, [f"✅ {w_}-{l_}. We crushed today — let's fucking go!",
                              f"✅ {w_}-{l_}. We smacked today. Let's go!",
                              f"✅ Went {w_}-{l_}. Cashing tickets.",
                              f"✅ {w_}-{l_} on the day. We eat.",
                              f"✅ {w_}-{l_}. Told y'all. Trust the algorithm.",
                              f"✅ {w_}-{l_}. Today was a grace from Jesus. Fuck yeah!",
                              f"✅ {w_}-{l_}. Another W in the books. Let's go!",
                              f"✅ {w_}-{l_}. Fed the whole squad today."]))
    else:
        lines.append(_rot(k, [f"😤 {w_}-{l_}. Our picks were fucking ass today. We gon' do better tomorrow.",
                              f"😤 {w_}-{l_}. Our picks were fucking ass today. We gon' bounce back. I won't let y'all down.",
                              f"😤 {w_}-{l_}. Not our day — the engine's already studying the tape.",
                              f"😤 Took some L's today ({w_}-{l_}). Shake it off. We gon' be right back.",
                              f"😤 {w_}-{l_}. Today was trash, no sugarcoating it. Tomorrow we eat.",
                              f"😤 {w_}-{l_}. Vegas got us today. Enjoy it while it lasts.",
                              f"😤 {w_}-{l_}. Rough day. Keep your head up — we back at it tomorrow.",
                              f"😤 {w_}-{l_}. Bad day at the office. The algorithm's taking notes."]))
    # big hits (+300 and up, board or live): they get their own brag, right under the day's record
    big = [(p["american"], (E(_the(p["legs"][0]["team"], p["legs"][0]["league"])) if len(p["legs"]) == 1
                            else "the " + LOOK[p["kind"]][0].replace(" OF THE DAY", "").lower()), "")
           for p in graded if p["status"] == "won" and p.get("american", 0) >= BIG_HIT]
    big += [(e["odds"], E(_the(e["team"], e.get("league"))), " live") for e in live.values()
            if e.get("result") == "won" and e.get("odds", 0) >= BIG_HIT and e.get("date") == today]
    for i, (o, what, how) in enumerate(sorted(big, reverse=True)[:2]):
        lines.insert(1 + i, _rot(k + o, [f"💰 DAMN. We smacked a +{o}{how} — {what}. I tried to fucking tell y'all. Let's go!",
                                         f"💰 +{o}{how}. CASHED. {_cap(what)} came through and I told y'all all day. Let's fucking go!",
                                         f"💰 Y'all doubted {what} at +{o}{how}? Smacked it. Trust the algorithm. LET'S GO!",
                                         f"💰 {_cap(what)} at +{o}{how}. Books are in shambles. I tried to fucking tell y'all!"]))
    big_live = {(e["team"], e["odds"]) for e in live.values() if e.get("odds", 0) >= BIG_HIT}
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%MZ")
    fresh = {}
    for g in (games or {}).values():
        if g.get("status") == "final" and g.get("start", "") >= cutoff and (g.get("stype") or "?") in sd.REAL:
            fresh[g["league"]] = fresh.get(g["league"], 0) + 1
    if fresh:
        parts = [f"{n} {sd.LEAGUES[lg][2]}" for lg, n in sorted(fresh.items(), key=lambda x: -x[1])]
        what = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
        lines.append([f"🎥 Studied the tape on last night's {what} games.", f"🎥 Broke down the film from {what} games.",
                      f"🎥 Went back over {what} games and got sharper."][k % 3])
    n = sum(p.get("eval_games", 0) for p in params.values())
    if n:
        a_ = sum((p.get("oos") or {}).get("acc", p["accuracy"]) * p.get("eval_games", 0) for p in params.values()) / n
        lines.append([f"🎯 Calling winners at a {a_:.1%} clip.", f"🎯 Hitting on {a_:.1%} of winners.",
                      f"🎯 {a_:.1%} of winners called straight up."][k % 3])
    legs = [l for p in picks if p["kind"] != "eight" for l in p["legs"] if l.get("result") in ("won", "lost")]
    if legs:
        said = sum(l["p"] for l in legs) / len(legs)
        got = sum(l["result"] == "won" for l in legs) / len(legs)
        lines.append(f"🧾 Receipts: said {said:.0%} of our legs would hit — <b class=\"{'up' if got >= said else 'dn'}\">{got:.0%}</b> did.")
    for e in sorted((e for e in live.values() if e.get("result") == "won" and e.get("date") == today
                     and (e["team"], e["odds"]) not in big_live),                  # big ones already got the brag
                    key=lambda e: e["posted"])[-2:]:
        o = f"+{e['odds']}" if e["odds"] > 0 else str(e["odds"])
        t = E(_the(e["team"], e.get("league")))
        lines.append(_rot(k + len(e["team"]), [f"📡 We smacked that {t} live bet ({o}). The algorithm never lies.",
                                               f"📡 Live bet cashed: {t} at {o}. Told y'all — teams always be coming back.",
                                               f"📡 {_cap(t)} live at {o}? Cashed. Trust the algorithm.",
                                               f"📡 Caught {t} live at {o} and they came through. Fuck yeah, let's go!",
                                               f"📡 {_cap(t)} live at {o} — CASHED. Everybody was jumping off, we jumped on."]))
    for e in sorted((e for e in live.values() if e.get("result") == "lost" and e.get("date") == today),
                    key=lambda e: e["posted"])[-2:]:
        o = f"+{e['odds']}" if e["odds"] > 0 else str(e["odds"])
        t = E(_the(e["team"], e.get("league")))
        lines.append(_rot(k + len(e["team"]), [f"📡 {_cap(t)} live bet ({o}) shit the bed. Bad call — is what it is.",
                                               f"📡 {_cap(t)} live at {o} was booty cheeks. Bad call — is what it is.",
                                               f"📡 Live L: {t} at {o}. Comeback never came. Is what it is — the algorithm's taking notes.",
                                               f"📡 {_cap(t)} live at {o} came up short. Bad call, shake it off — next one's ours."]))
    if not done and not any(x.startswith("📡") for x in lines):   # no finished day yet: nothing to brag or cry about
        lines = [_rot(k, ["👀 We gon' see.", "👀 We finna see."])]
    elif lines:                                               # results are in: remind everybody we're just getting started
        first = min((p["date"] for p in picks), default=today)
        young = (now.date() - datetime.strptime(first, "%Y-%m-%d").date()).days < 60
        lines.append(_rot(k, [
            "🧪 We just got this thing started. The algorithm's training every single day — it's only getting sharper.",
            "🧪 We're brand new out here. Every game makes the engine smarter. Give it time — we about to be dangerous.",
            "🧪 Day by day, the algorithm's leveling up. Wins or L's, it's learning from all of it. Trust the process.",
            "🧪 This engine is still a baby and it's already cooking. Wait till it grows up.",
            "🧪 Still training the algorithm and improving every day. The best is coming — stay locked in.",
            "🧪 Every result goes back into the brain. We getting better and better — y'all gonna see.",
            "🧪 We just started and we're analyzing EVERYTHING — every game, every line, every comeback. The engine improves daily.",
            "🧪 Heads up: we're still new. The algorithm breaks down every result and upgrades itself every day. Stick with us."] if young else [
            "🧪 The algorithm studies every result and gets sharper every day. We never stop improving.",
            "🧪 The engine's still leveling up daily. Every W and every L makes it smarter.",
            "🧪 We keep training this thing every single day. Better tomorrow than today — that's the deal.",
            "🧪 Always improving. The algorithm learns from every game — trust the process."]))
    brain = '<div class="br self"><div class="bn">🧠 Today in a nutshell</div>' + "".join(f'<div class="bs nut">{x}</div>' for x in lines) + "</div>"
    tuned = model.get("tuned_on", "—")

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400..900&display=swap" rel="stylesheet">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="D503 Sports">
<meta name="theme-color" content="#05070b">
<title>THE D503 · Sports Engine</title>
<meta property="og:type" content="website">
<meta property="og:title" content="THE D503 SPORTS ENGINE">
<meta property="og:description" content="Daily 2-Leg, 3-Leg, Lock &amp; Dog of the Day. Trust the algorithm.">
<meta property="og:url" content="https://d503therapper.github.io/autonomous-crypto-engine/sports/">
<meta property="og:image" content="https://d503therapper.github.io/autonomous-crypto-engine/sports/og.png?v=8">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="description" content="Daily 2-Leg, 3-Leg, Lock &amp; Dog of the Day. Trust the algorithm.">
<link rel="apple-touch-icon" href="apple-touch-icon.png?v=8"><link rel="icon" href="icon-512.png?v=8"><link rel="manifest" href="manifest.webmanifest">
<style>
:root{{--bg:#040609;--card:#0b0f17;--card2:#101723;--line:#1b2433;--text:#f2f5fb;--muted:#22d3ee;--up:#22e39a;--dn:#ff3b3b;--gold:#ffc233;--accent:#ffc233}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}}
input,button,textarea,select{{font:inherit}}
body{{font:15px/1.4 "Inter",-apple-system,BlinkMacSystemFont,system-ui,sans-serif;-webkit-text-size-adjust:100%;text-size-adjust:100%;min-height:100vh;
  background:radial-gradient(640px 400px at 10% -120px,rgba(255,194,51,.22),transparent 70%),
             radial-gradient(640px 420px at 100% -80px,rgba(255,90,31,.20),transparent 70%),
             repeating-linear-gradient(135deg,rgba(255,255,255,.018) 0 2px,transparent 2px 7px),var(--bg)}}
main{{max-width:520px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 18px) 16px 34px;overflow:hidden}}
.head{{position:relative;margin:6px 0 18px}}
.title{{font-weight:900;font-size:40px;letter-spacing:-.02em;line-height:1}}
.the{{font-size:20px;font-weight:800;letter-spacing:.2em;color:#ff2a2a;vertical-align:middle;text-shadow:0 0 14px rgba(255,42,42,.7)}}
.d503{{background:linear-gradient(95deg,#3b82ff 0%,#22d3ee 45%,#22e39a 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 6px 22px rgba(59,130,255,.45))}}
.tag{{margin-top:8px;font-size:12.5px;font-weight:900;letter-spacing:.34em;background:linear-gradient(90deg,#ffe08a,#ffc233 35%,#ff8a00 75%,#ff5a1f);
  -webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 0 10px rgba(255,160,40,.5))}}
.live{{position:absolute;top:2px;right:0;white-space:nowrap;display:flex;align-items:center;gap:7px;font-size:12px;font-weight:700;color:var(--up);
  background:rgba(34,227,154,.08);border:1px solid rgba(34,227,154,.35);padding:6px 10px;border-radius:999px}}
.dot{{width:8px;height:8px;border-radius:50%;background:var(--up);animation:pulse 2s infinite}}
.dot.stale{{background:#f5b73b;animation:none}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(34,227,154,.6)}}70%{{box-shadow:0 0 0 10px rgba(34,227,154,0)}}100%{{box-shadow:0 0 0 0 rgba(34,227,154,0)}}}}
.sec{{display:flex;align-items:baseline;justify-content:space-between;margin:22px 2px 10px}}
.sec h2{{margin:0;font-size:13px;font-weight:900;letter-spacing:.2em;color:#fff}}
.sec h2 i{{font-style:normal;color:var(--gold);text-shadow:0 0 10px rgba(255,194,51,.6)}}
.sec span{{font-size:12px;color:var(--gold);font-weight:600}}
.board{{position:relative}}
.trust-wrap{{display:flex;justify-content:center;margin:14px 0 4px}}
.trust{{font-weight:900;font-style:italic;font-size:22px;letter-spacing:.14em;color:#fff;padding:0 6px 8px;position:relative}}
.trust:after{{content:"";position:absolute;left:0;right:0;bottom:0;height:5px;background:#e3121b;transform:skewX(-20deg)}}
.drop{{text-align:center;font-weight:700;color:#fff;background:var(--card);border:1px dashed rgba(255,194,51,.55);border-radius:16px;padding:14px;margin-bottom:12px}}
.drop b{{color:var(--gold)}}
.pk{{position:relative;background:linear-gradient(165deg,color-mix(in srgb,var(--c1) 16%,var(--card2)) 0%,var(--card) 55%);border:1px solid color-mix(in srgb,var(--c1) 55%,transparent);
  border-radius:22px;padding:16px 16px 10px;margin-bottom:14px;overflow:hidden;box-shadow:0 18px 50px -22px var(--c1),inset 0 1px 0 rgba(255,255,255,.05)}}
.pk::before{{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.pk.won{{box-shadow:0 0 0 2px var(--up),0 18px 50px -14px var(--up)}}
.pk.lost>*:not(.stamp-row){{opacity:.5}}
.stamp-row{{display:flex;justify-content:center;margin:6px 0 12px}}
.stamp{{transform:rotate(-6deg);font-weight:900;font-size:34px;letter-spacing:.16em;padding:4px 22px;border:4px solid currentColor;
  border-radius:10px;background:rgba(0,0,0,.3)}}
.stamp.won{{color:var(--up);text-shadow:0 0 16px rgba(34,227,154,.7);box-shadow:0 0 22px rgba(34,227,154,.35)}}
.stamp.lost{{color:var(--dn);text-shadow:0 0 16px rgba(255,59,59,.6)}}
.stamp.push{{color:var(--gold)}}
.lt-t{{margin-left:8px;font-size:10px;font-weight:900;letter-spacing:.05em}} .lt-t.lk{{color:#22e39a}} .lt-t.val{{color:#ff8a00}} .lt-t.lean{{color:#ffc233}}
.ask{{background:var(--card);border:1px solid rgba(34,211,238,.35);border-radius:12px;margin:10px 0;overflow:hidden}}
.ask-top{{padding:10px 12px 6px}}
.ask-t{{font-size:13px;font-weight:900;letter-spacing:.08em;color:#22d3ee;white-space:nowrap}} .ask-s{{font-size:12px;font-weight:700;color:#ffc233;white-space:nowrap}}
.ask-b{{padding:0 12px 12px}} .ask-n{{font-size:12px;font-weight:600;color:#ffe08a;margin:2px 0 8px}} .ask-n b{{color:#22e39a}}
.ask-row{{display:flex;gap:6px}} #askgo{{flex:none;font-size:15px;font-weight:900;padding:8px 12px;border-radius:12px;border:0;background:linear-gradient(90deg,#22d3ee,#b36bff);color:#04060c}}
#askq{{width:100%;font-size:16px;padding:8px 11px;border-radius:12px;border:1px solid rgba(34,211,238,.55);background:#060a12;color:#fff}}
#askq::placeholder{{color:#5fd4e8}}
#asklist{{display:flex;flex-direction:column;gap:6px;margin-top:10px}}
.ask-g{{text-align:left;background:var(--card2);border:1px solid var(--line);color:#fff;border-radius:10px;padding:10px 12px;font-size:14px;font-weight:700}}
.ask-g small{{color:#22d3ee;font-weight:700;margin-left:6px}}
.ask-c{{margin-top:12px}} .ask-l{{font-size:17px;margin:8px 0 2px}} .ask-l b{{color:#fff}}
.ask-a{{font-weight:800;color:#22e39a;margin:2px 0 6px}} .ask-w{{font-size:13px;font-weight:600;color:#ff9f5a;margin:6px 0}}
.ask-h{{font-size:13px;font-weight:600;color:#b9a4ff;margin:4px 0}} .ask-h b{{color:#fff}}
.ask-prop{{font-size:15px;font-weight:900;color:#ff5a7a;margin:6px 0 10px}}
.ask-d{{font-size:12px;font-weight:800;color:#ffc233;margin-top:8px}}
.own{{font-size:13px;font-weight:800;color:#ffc233;margin-top:6px;border-left:3px solid #ffc233;padding-left:8px}}
.hist{{margin:4px 0 14px;border:1px solid rgba(255,194,51,.35);border-radius:12px;background:var(--card2);padding:0 12px}}
.hist>summary{{list-style:none;cursor:pointer;padding:12px 0;font-weight:900;font-size:15px;letter-spacing:.06em;color:#ffc233}}
.hist>summary span{{display:block;font-size:12px;font-weight:700;letter-spacing:0;color:#9fb0c8;margin-top:2px}}
.hist summary::-webkit-details-marker{{display:none}}
.hs{{border-top:1px solid rgba(255,255,255,.08)}}
.hs>summary{{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 0;font-size:15px}}
.hs>summary b{{color:#fff;font-weight:900}} .hs>summary span{{color:#ffc233;font-weight:800;white-space:nowrap}}
.hs>summary::after{{content:"▾";color:#9fb0c8;margin-left:6px}} .hs[open]>summary::after{{content:"▴"}}
.hs-own{{font-size:11px;font-weight:900;letter-spacing:.14em;color:#9fb0c8;padding:12px 0 2px;border-top:1px solid rgba(255,255,255,.08)}}
.hr{{display:grid;grid-template-columns:3.6em 1.4em minmax(0,1fr);gap:6px;padding:7px 0;border-top:1px dashed rgba(255,255,255,.06);font-size:13.5px;align-items:start}}
.hr .hd{{color:#9fb0c8;font-weight:700;white-space:nowrap}} .hr .hp{{color:#fff;font-weight:800;overflow-wrap:anywhere}}
.hr .hp small{{color:#9fb0c8;font-weight:600}} .hr .hp em{{display:block;font-style:normal;font-weight:600;color:#ffc233;margin-top:3px}} .hr.lost .hp{{color:#ffb4b4}}
.sports{{display:grid;grid-template-columns:1fr;gap:6px;margin:8px 0 14px}}
.spc{{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:10px;background:var(--card2);
  border:1px solid rgba(255,194,51,.35);border-radius:10px;padding:9px 12px;font-size:15px;font-weight:900}}
.spc b{{display:block;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.spc small{{display:block;font-size:13px;font-weight:700;color:#ffc233;white-space:nowrap}}
.spc i{{font-style:normal;text-align:right;white-space:nowrap;font-size:17px}}
.bw{{font-size:13px;font-weight:900;color:#22e39a;margin:2px 0 6px}}
.track{{font-size:13px;font-weight:900;letter-spacing:.04em;color:var(--gold);margin:2px 0 4px}}
.leg.won{{border-left:4px solid var(--up);padding-left:10px;margin-left:-14px;background:linear-gradient(90deg,rgba(34,227,154,.10),transparent 60%)}}
.leg.lost{{border-left:4px solid var(--dn);padding-left:10px;margin-left:-14px;background:linear-gradient(90deg,rgba(255,59,59,.10),transparent 60%)}}
.leg.lost .pick{{text-decoration:line-through;text-decoration-color:var(--dn);text-decoration-thickness:3px}}
.lr{{font-size:11.5px;font-weight:900;letter-spacing:.1em;padding:3px 8px;border-radius:999px}}
.lr.won{{color:#04110b;background:var(--up)}} .lr.lost{{color:#fff;background:var(--dn)}} .lr.push{{color:#000;background:var(--gold)}}
.pk-h{{display:flex;align-items:center;gap:10px}}
.pk-i{{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;font-size:18px;background:linear-gradient(135deg,var(--c1),var(--c2));box-shadow:0 6px 18px -6px var(--c1)}}
.pk-l{{flex:1;font-weight:900;font-size:14px;letter-spacing:.14em;color:var(--c1);text-shadow:0 0 12px color-mix(in srgb,var(--c1) 55%,transparent)}}
.pk-l.pk-big{{font-size:clamp(22px,6.6vw,30px);letter-spacing:.05em;line-height:1.1}}   /* a one-game day: the pick IS the headline */
.chip{{font-size:10.5px;font-weight:900;letter-spacing:.1em;padding:4px 8px;border-radius:999px;white-space:nowrap}}
.lock{{font-size:12.5px;font-weight:800;color:var(--gold);margin:2px 0 4px}}
.pk.waiting{{border-style:dashed}}
.chip.waiting{{color:#0a0a0a;background:var(--gold)}}
.chip.open{{color:#fff;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2)}}
.chip.won{{color:#04110b;background:var(--up)}} .chip.lost{{color:#fff;background:var(--dn)}} .chip.push{{color:#000;background:var(--gold)}}
.pk-o{{display:flex;align-items:center;justify-content:space-between;margin:12px 0 6px}}
.big{{font-size:42px;font-weight:900;letter-spacing:-.02em;line-height:1;color:#fff;font-variant-numeric:tabular-nums;text-shadow:0 0 24px color-mix(in srgb,var(--c1) 60%,transparent)}}
.pay{{text-align:right;font-size:14px;color:#fff;font-weight:600}} .pay b{{color:var(--c1);font-size:18px}} .pay span{{color:var(--c1);font-size:12px}}
.leg{{border-top:1px solid rgba(255,255,255,.07);padding:10px 0 8px}}
.lt{{display:flex;justify-content:space-between;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--c1)}}
.lgb{{color:#fff}}
.lm{{display:flex;justify-content:space-between;align-items:baseline;margin-top:3px}}
.pick{{font-size:18px;font-weight:850;color:#fff}} .pick em{{font-style:normal;color:var(--c1);font-weight:900;margin-left:2px}}
.od{{font-size:17px;font-weight:900;color:#fff;font-variant-numeric:tabular-nums}}
.ls{{font-size:12.5px;color:#fff;margin-top:2px}} .ls b{{color:#fff}}
.ep{{color:var(--up);font-weight:800}} .en{{color:#ff8a5c;font-weight:800}}
.why{{font-size:12px;color:#e8c77a;margin-top:4px}}
.pubs{{margin-top:6px}} .pub{{display:inline-block;font-size:11px;font-weight:900;letter-spacing:.1em;padding:4px 9px;border-radius:999px}}
.pub.fade{{color:#fff;background:linear-gradient(90deg,#7c3aed00,#e3121b33);border:1px solid #ff3b3b}} .pub.ride{{color:#22e39a;border:1px solid #22e39a;background:rgba(34,227,154,.1)}}
.lv{{color:#ff3b3b !important;animation:blink 1.2s infinite}} @keyframes blink{{50%{{opacity:.2}}}}
.dly{{color:#ffc233;font-weight:900;letter-spacing:.06em}} .lvb{{color:#ff4040;font-weight:900;letter-spacing:.08em;white-space:nowrap;text-shadow:0 0 8px rgba(255,64,64,.6)}} .fnb{{color:#9aa4b2;font-weight:900;letter-spacing:.08em}} .lsc{{font-size:.86em;color:#e8eef6;margin:2px 0 4px;font-variant-numeric:tabular-nums}} .lsc b{{font-weight:800}} .lsc>span{{color:#ff8a8a;font-weight:700}}
.tsb{{display:grid;gap:2px 0;align-items:center;max-width:250px;margin:4px 0 6px;padding:5px 9px;border-radius:8px;background:rgba(255,255,255,.05);font-size:.95em}}
.tsb .nm{{color:#fff;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .tsb .nm i{{display:inline-block;width:6px;height:6px;border-radius:50%;background:#d7ff3a;margin:0 5px 2px 0}}
.tsb b{{text-align:center;font-weight:700;color:#cfd6df}} .tsb b.w{{color:#fff;font-weight:900}} .tsb b.l{{color:#7d8794;font-weight:600}}
.tsb em{{font-style:normal;text-align:center;font-weight:900;color:#ff8a8a}} .lvb i{{display:inline-block;width:10px;height:10px;border-radius:50%;background:#ff2b2b;margin-right:6px;vertical-align:0;box-shadow:0 0 6px 1px #ff2b2b;animation:lvp 1.4s infinite}}
@keyframes lvp{{0%{{box-shadow:0 0 0 0 rgba(255,43,43,.9),0 0 6px 1px #ff2b2b}}70%{{box-shadow:0 0 0 9px rgba(255,43,43,0),0 0 6px 1px #ff2b2b}}100%{{box-shadow:0 0 0 0 rgba(255,43,43,0),0 0 6px 1px #ff2b2b}}}}
.nolive{{font-size:14px;font-weight:700;color:#fff;line-height:1.45}} .pk.lvi{{padding-top:16px;padding-bottom:16px}}
.tn{{margin:22px 0 6px;border:1px solid #c6f00066;border-radius:18px;background:linear-gradient(165deg,#c6f00014,var(--card))}}
.tn summary{{list-style:none;cursor:pointer;padding:16px 18px;display:flex;flex-direction:column;gap:4px}}
.tn summary::-webkit-details-marker{{display:none}}
.tn-t{{font-weight:900;letter-spacing:.14em;color:#c6f000;font-size:15px}} .tn-s{{font-size:12.5px;color:#fff;font-weight:700}}
.tn[open] .tn-s{{color:#c6f000}} .tn-b{{padding:0 12px 14px}} .tn-d{{font-size:12px;color:#e8c77a;font-weight:700;margin:0 6px 10px}}
.chip.lean{{background:#ffc233;color:#111;margin-right:6px}} .chip.val{{background:#ff5a1f;color:#fff;margin-right:6px}}
.chip.lk{{background:#22e39a;color:#06281c;margin-right:6px}}
.pk.lvc{{box-shadow:0 0 0 2px #ff3b3b,0 18px 50px -14px #ff3b3b}} .chip.livechip{{color:#fff;background:#ff3b3b}}
.bd{{margin-top:8px;border:1px solid color-mix(in srgb,var(--c1) 45%,transparent);border-radius:12px;background:rgba(0,0,0,.25)}}
.bd summary{{list-style:none;cursor:pointer;padding:8px 12px;font-size:13px;font-weight:800;color:var(--c1);letter-spacing:.04em}}
.bd summary::-webkit-details-marker{{display:none}}
.bd summary:after{{content:"▾";float:right;transition:transform .2s}} .bd[open] summary:after{{transform:rotate(180deg)}}
.bd-s{{padding:2px 12px 8px}} .bd-t{{font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);margin-top:4px}}
.bd-s p{{margin:6px 0;font-size:13.5px;color:#fff;line-height:1.45}} .bd-s p:last-child{{color:var(--gold);font-weight:700}}
.outs{{font-size:11.5px;color:#ff8a5c;margin-top:3px}}
.fin{{font-size:12px;color:#fff;opacity:.75;margin-top:3px}}
.lw{{color:var(--up);margin-right:6px}} .ll{{color:var(--dn);margin-right:6px}} .lp{{color:var(--gold);margin-right:6px}}
.nopick{{color:var(--muted);font-weight:600;font-size:13px;padding:12px 0 6px}}
.hero{{position:relative;background:linear-gradient(160deg,#131a28 0%,var(--card) 60%);border:1px solid rgba(255,194,51,.28);border-radius:24px;padding:20px 20px 8px;overflow:hidden;
  box-shadow:0 20px 60px -24px rgba(255,160,40,.45)}}
.lbl{{color:#fff;font-size:12px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}
.total{{font-size:42px;font-weight:800;letter-spacing:-.02em;margin:4px 0 8px;font-variant-numeric:tabular-nums}}
.sp-n{{font-size:12px;color:#9fb0c8;margin:4px 0 12px}}
.grades{{margin-bottom:12px}}
.ovr{{text-align:center;background:linear-gradient(160deg,rgba(34,227,154,.14),rgba(255,194,51,.10));border:1px solid rgba(34,227,154,.45);border-radius:16px;padding:14px 12px;margin:10px 0 12px}}
.ovr-t{{font-size:13px;font-weight:900;letter-spacing:.12em;color:#22e39a}} .ovr-r{{font-size:46px;font-weight:900;line-height:1.1}}
.ovr-p{{font-size:15px;font-weight:800;color:#ffc233}} .ovr-s{{font-size:13px;font-weight:700;color:#22d3ee;margin-top:2px}}
.sp-n.what{{color:#ffe08a;font-weight:600;line-height:1.5}} .sp-n.what b{{color:#22e39a}}
.pill{{display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:14px;padding:5px 11px;border-radius:999px;
  background:color-mix(in srgb,var(--p) 16%,transparent);color:var(--p);font-variant-numeric:tabular-nums}}
.pill small{{color:#fff;font-weight:900;font-size:11px;letter-spacing:.08em}}
.month{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}}
.tile{{background:linear-gradient(180deg,color-mix(in srgb,var(--h) 14%,transparent),rgba(255,255,255,.02));border:1px solid color-mix(in srgb,var(--h) 45%,transparent);
  border-radius:14px;padding:10px 9px;min-width:0;overflow:hidden;box-shadow:0 6px 22px -12px var(--h)}}
.tl{{color:#fff;font-size:9.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}}
.ts{{font-size:11px;font-weight:700;color:#fff;margin-top:1px;white-space:nowrap}} .ts.up{{color:var(--up)}} .ts.dn{{color:var(--dn)}}
.tv{{font-size:clamp(13px,4.2vw,17px);font-weight:800;margin-top:6px;white-space:nowrap}}
.ar{{font-size:.7em;margin-right:3px;vertical-align:1px}}
.up{{color:var(--up)}} .dn{{color:var(--dn)}} .w{{color:#fff}}
.strip{{display:flex;flex-wrap:wrap;gap:4px;margin:14px 0 12px}}
.strip i{{width:12px;height:12px;border-radius:3px;background:#2f8bff}}
.strip i.won{{background:var(--up);box-shadow:0 0 8px rgba(34,227,154,.6)}} .strip i.lost{{background:var(--dn)}} .strip i.push{{background:var(--gold)}}
.recs{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.rc{{position:relative;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px;overflow:hidden}}
.rc::before{{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.rc-t{{font-size:11px;font-weight:900;letter-spacing:.12em;color:var(--c1)}}
.rc-r{{font-size:clamp(13px,4vw,15.5px);font-weight:900;color:#fff;margin-top:8px;white-space:nowrap;letter-spacing:-.01em;font-variant-numeric:tabular-nums}}
.rc-p{{font-weight:800;color:var(--c1);font-size:12.5px;white-space:nowrap;letter-spacing:-.01em}} .rc-s{{font-size:11.5px;color:var(--c2);font-weight:700;margin-top:2px}}
.list{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:4px 14px}}
.rr{{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}} .rr:last-child{{border:0}}
.rk{{font-size:18px}} .rd{{flex:1;min-width:0}}
.rl{{font-weight:750;color:#fff;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rm{{font-size:11.5px;color:var(--muted);font-weight:600}}
.rv{{font-weight:900;font-variant-numeric:tabular-nums}}
.empty{{color:var(--muted);font-weight:600;font-size:13px;padding:12px 0}}
.br{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 14px;margin-bottom:10px}}
.br.self{{border-color:rgba(255,194,51,.35)}}
.bh{{display:flex;justify-content:space-between;align-items:center}}
.bn{{font-weight:900;color:#fff;font-size:15px}} .bt{{font-size:12px;color:var(--muted);font-weight:700}} .bt b{{color:var(--gold)}}
.bs{{font-size:12.5px;color:#fff;margin-top:3px}} .bs b{{color:#fff}} .bs b.up,.bs .up{{color:var(--up)}} .bs b.dn,.bs .dn{{color:var(--dn)}}
.fxs{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:9px}}
.fx{{position:relative;font-size:10px;font-weight:800;color:#fff;letter-spacing:.04em;padding-top:8px;text-align:center}}
.fx i{{position:absolute;top:0;left:0;height:4px;border-radius:4px;box-shadow:0 0 8px currentColor}}
.fx::before{{content:"";position:absolute;top:0;left:0;right:0;height:4px;border-radius:4px;background:rgba(255,255,255,.08)}}
.bc{{font-size:11.5px;color:#e8c77a;margin-top:8px}}
.nut{{font-size:13.5px;margin-top:7px;padding-left:14px;position:relative}} .nut:before{{content:"▸";position:absolute;left:0;color:var(--gold)}}
.foot{{text-align:center;color:#ffe08a;font-size:12px;margin-top:22px;line-height:1.6}}
.foot b{{color:#fff}} .foot a{{color:#22d3ee;text-decoration:none;font-weight:700}}
.bell{{margin:-2px 2px 10px}}
#bellb{{display:inline-flex;align-items:center;gap:6px;max-width:100%;white-space:nowrap;font-size:13px;font-weight:900;letter-spacing:.04em;color:#fff;
  padding:7px 13px;border-radius:999px;border:1px solid rgba(255,59,59,.6);background:linear-gradient(90deg,rgba(255,59,59,.16),rgba(255,138,0,.12));
  box-shadow:0 6px 18px -10px #ff3b3b;cursor:pointer;-webkit-tap-highlight-color:transparent}}
#bellb[hidden],.bell-n[hidden]{{display:none}}
#bellb:active{{transform:scale(.97)}} #bellb:disabled{{opacity:.6}}
#bellb.on{{color:var(--up);border-color:rgba(34,227,154,.45);background:rgba(34,227,154,.08);box-shadow:none}}
.bell-n{{font-size:12px;font-weight:700;color:#ffe08a;margin:7px 2px 0;line-height:1.4}} .bell-n b{{color:#fff}}
</style></head><body><main>
<header class="head">
  <div class="title"><span class="the">THE</span> <span class="d503">D503</span></div>
  <div class="tag">SPORTS ENGINE</div>
  <div class="live"><span class="dot" id="dot"></span><span id="ago">Live</span></div>
</header>
<div class="trust-wrap"><div class="trust">TRUST THE ALGORITHM</div></div>
<div class="ask" id="ask"><div class="ask-top"><span class="ask-t">🤔 QUESTION BOX</span></div>
<div class="ask-b"><div class="ask-n">{ask_note}</div>
<div class="ask-row"><input id="askq" type="search" placeholder="What’s good? 🤔" autocomplete="off" enterkeyhint="send">{ask_btn}</div>
<div id="asklist"></div><div id="askout"></div></div></div>
<div class="sec"><h2><i class="lv">●</i> LIVE PLUS MONEY</h2><span>updates every 5 sec</span></div>
{bell}<div id="live"><section class="pk lvi" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="nolive">📡 Checking the live games…</div></section></div>
<div class="sec"><h2><i>●</i> TODAY'S BOARD</h2><span>{E(board_date)}</span></div>
<div class="board">{board}</div>
{tomorrow}

{_tennis()}
<div class="sec"><h2><i>●</i> THE RESULTS</h2><span>every play, graded</span></div>
<section class="hero">
  <div class="lbl">The engine's grades</div>
  <div class="sp-n what"><b>What counts:</b> our record is the start-of-day board — the Lock, the Dog, the 2-Leg, the 3-Leg and the 4-Leg (on a one-game day, that one pick counts too — it only gets called the Lock of the Day when the engine’s as confident as it is in a real one), every leg a 🔒 lock or 🔥 value call the engine is confident in. The live plus money picks and leans that pop up throughout the day each keep their own record as well as tennis. Question box reads never count. Every W and every L is right here — we don’t hide nothing.</div>
  {overall}
  <div class="recs grades">{grades}{"".join(rec)}</div>
  <div class="lbl" style="margin-top:4px">Their own records <small style="color:#ffc233;letter-spacing:0">· not in our record</small></div>
  <div class="recs grades">{others}</div>
  <div class="lbl" style="margin-top:4px">By sport</div>
  <div class="sports">{by_sport}</div>
  {_history(picks)}
</section>
{live_list}
<div class="sec"><h2><i>●</i> THE BRAIN</h2><span>retrained {E(tuned)}</span></div>
{brain}
<div class="foot"><b>THE D503 SPORTS ENGINE</b><br>
Ratings · form · rest · injuries · line moves — retrained after every final score.<br>
Picks only — no bets placed · refreshes hourly</div>
</main>
<script>
(function(){{   // 📡 LIVE VALUE: checks live.json every 2 seconds; a play disappears the moment its value is gone
function esc(x){{return String(x).replace(/[&<>"]/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var last="";
function idle(n){{return '<section class="pk lvi" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="nolive">'+(n<0?
  '📡 Checking the live games…':n>0?
  '👀 No live plus money right now. '+n+' game'+(n>1?'s':'')+' going — the algorithm’s watching every play for value.':
  '😴 No live plus money right now — no games going.')+'</div></section>';}}
function draw(d){{var el=document.getElementById("live");if(!el)return;var ps=(d&&d.plays)||[],n=d?(d.live_games||0):-1;
 var key=JSON.stringify(ps)+n;if(key===last)return;last=key;          // unchanged: leave it (an open breakdown stays open)
 el.innerHTML=(ps.length?ps.map(function(p){{
  return '<section class="pk lvc" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="pk-h"><span class="pk-i">'+esc(p.emoji)+'</span><span class="pk-l">'+(p.double_down?'🔁 DOUBLE DOWN':'LIVE BET')+'</span><span class="chip livechip">'+(p.paused?'⏸ LINE PAUSED':'📡 LIVE')+'</span></div>'+
   
   '<div class="leg"><div class="lt"><span class="lgb">'+esc(p.emoji)+' '+esc(p.sport)+'</span><span class="tm">'+esc(p.clock)+'</span></div>'+
   '<div class="lm"><span class="pick">'+esc(p.team)+' <em>ML</em></span><span class="od">+'+esc(p.odds)+'</span></div>'+
   '<div class="ls">'+esc(p.score)+(p.ball?' · '+esc(p.ball):'')+'</div><div class="why">'+esc(p.line)+'</div>'+
   ((p.breakdown||[]).length?'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">'+p.breakdown.map(function(x){{return"<p>"+esc(x)+"</p>"}}).join("")+'</div></details>':'')+
   '</div></section>';}}).join(""):idle(n));}}
function show(d){{var age=d?Date.now()-d.updated:1e12;   // plays must be fresh; a "nothing on" board holds till the next watch
 window.D503S=(d&&age<10*60000&&d.scores)||{{}};if(window.d503lt)window.d503lt();   // live scores next to our pending picks
 if(d&&(age<10*60000||(!(d.plays||[]).length&&!d.live_games&&age<45*60000)))draw(d);else draw(null);}}
function raw(){{return fetch("https://raw.githubusercontent.com/{REPO}/live-data/live.json?t="+Date.now(),{{cache:"no-store"}}).then(function(r){{return r.ok?r.json():null}});}}
function poll(){{if(document.hidden)return;   // only while the app's on screen; "nothing changed" answers (304) don't count against GitHub's limit
 fetch("https://api.github.com/repos/{REPO}/contents/live.json?ref=live-data",{{headers:{{Accept:"application/vnd.github.raw"}},cache:"no-cache"}})
 .then(function(r){{return r.ok?r.json():raw()}}).catch(raw).then(show).catch(function(){{}});}}
poll();setInterval(poll,2000);document.addEventListener("visibilitychange",poll);}})();
(function(){{var t={int(updated_ms)},m=0;   // the whole page stays fresh while it's open
try{{var o=sessionStorage.getItem("d503o");if(o){{sessionStorage.removeItem("d503o");var ds=document.querySelectorAll("details");   // reopen what was open
  JSON.parse(o).forEach(function(i){{if(ds[i])ds[i].open=true}});}}
 var y=sessionStorage.getItem("d503y");if(y!==null){{sessionStorage.removeItem("d503y");window.scrollTo(0,+y);}}}}catch(e){{}}
function tick(){{m=Math.max(0,Math.round((Date.now()-t)/60000));
 var s=m<1?"just now":m<60?m+" min ago":Math.floor(m/60)+"h "+(m%60)+"m ago";
 document.getElementById("ago").textContent="Live · "+s;
 if(m>150)document.getElementById("dot").className="dot stale";}}
var touched=0;["touchstart","scroll","keydown","click"].forEach(function(ev){{window.addEventListener(ev,function(){{touched=Date.now()}},{{passive:true}})}});
function check(){{if(document.hidden)return;              // a newer page? swap it in - only once the SITE serves it
 if(Date.now()-touched<30000)return;                       // (never while someone's scrolling or tapping around)
 try{{if(Date.now()-(+sessionStorage.getItem("d503r")||0)<60000)return;}}catch(e){{}}   // at most once a minute
 fetch(location.pathname+"?c="+Date.now(),{{cache:"no-store"}})
 .then(function(r){{return r.ok?r.text():""}})
 .then(function(h){{var x=/var t=(\d+),m=/.exec(h);
   var aq=document.getElementById("askq");                     // (not while someone's asking a question)
   if(x&&+x[1]>t&&!(aq&&(aq.value||document.activeElement===aq))){{   // an open breakdown comes back open, same spot
     try{{var op=[];document.querySelectorAll("details").forEach(function(d,i){{if(d.open)op.push(i)}});
       sessionStorage.setItem("d503o",JSON.stringify(op));
       sessionStorage.setItem("d503y",String(window.scrollY));sessionStorage.setItem("d503r",String(Date.now()));}}catch(e){{}}
     location.replace(location.pathname+"?v="+x[1]);}}}})
 .catch(function(){{}});}}
var API="{_ask_url().rstrip('/')}";          // 📡 scores straight from ESPN every second (our server), the live board as backup
function fastScores(){{if(document.hidden||!API)return;var n=Date.now(),ids={{}};
 document.querySelectorAll(".tm[data-gid]").forEach(function(s){{var st=Date.parse(s.getAttribute("data-start")),g=s.getAttribute("data-gid");
  if(g&&st&&n>=st-60000&&n<st+8*3600000)ids[g]=1}});
 var k=Object.keys(ids);if(!k.length)return;
 fetch(API+"/scores?ids="+encodeURIComponent(k.join(",")),{{cache:"no-store"}}).then(function(r){{return r.ok?r.json():null}})
 .then(function(d){{if(d){{window.D503F=d;window.D503Ft=Date.now();liveTags()}}}}).catch(function(){{}});}}
function flip(sc){{return {{tennis:true,n:[sc.n[1],sc.n[0]],sets:(sc.sets||[]).map(function(x){{return [x[1],x[0]]}}),
  pts:sc.pts?[sc.pts[1],sc.pts[0]]:null,srv:sc.srv===0?1:sc.srv===1?0:null,done:sc.done,live:sc.live}}}}
function liveTags(){{var n=Date.now(),S={{}},W=window.D503S||{{}},F=(n-(window.D503Ft||0)<15000&&window.D503F)||{{}};
 Object.keys(W).forEach(function(k){{S[k]=W[k]}});Object.keys(F).forEach(function(k){{S[k]=F[k]}});   // the freshest wins
 document.querySelectorAll(".tm[data-start]").forEach(function(s){{
  // 🔴 LIVE while it's being played, with the score + time left right under it (tennis: sets, games, points)
  var st=Date.parse(s.getAttribute("data-start"));if(!st)return;
  var sc=S[s.getAttribute("data-gid")||""];if(sc&&sc.p1&&s.getAttribute("data-side")==="2")sc=flip(sc);   // our player first
  var row=s.closest(".lt"),box=row&&row.nextElementSibling&&row.nextElementSibling.classList.contains("lsc")?row.nextElementSibling:null;
  var on=sc?true:(n>=st&&n<st+6*3600000);
  if(on){{if(!s.dataset.lv)s.dataset.lv=s.innerHTML;
    var tag=sc&&!sc.live?'<span class="fnb">FINAL</span>':'<span class="lvb"><i></i>LIVE</span>';if(s.innerHTML!==tag)s.innerHTML=tag;}}
  else if(s.dataset.lv){{s.innerHTML=s.dataset.lv;delete s.dataset.lv}}
  if(sc&&on&&row){{var q=function(x){{return String(x).replace(/[&<>"]/g,"")}},h;
    if(!box){{box=document.createElement("div");box.className="lsc";row.parentNode.insertBefore(box,row.nextSibling)}}
    if(sc.tennis){{var n=(sc.sets||[]).length,cols="1fr repeat("+n+",1.5em)"+(sc.pts?" 2.4em":"");   // 🎾 a TV-style scoreboard
      h='<div class="tsb" style="grid-template-columns:'+cols+'">'+[0,1].map(function(i){{
        return '<span class="nm">'+(sc.live&&sc.srv===i?'<i></i>':'')+q(sc.n[i])+'</span>'+(sc.sets||[]).map(function(st,k){{
          var won=k<sc.done&&st[i]>st[1-i];return '<b'+(won?' class="w"':k<sc.done?' class="l"':'')+'>'+st[i]+'</b>'}}).join("")+
          (sc.pts?'<em>'+q(sc.pts[i])+'</em>':'')}}).join("")+'</div>';}}
    else{{var c=sc.clock&&sc.clock!=="Final"?sc.clock:"";
      h='<b>'+q(sc.away+" "+sc.a+" @ "+sc.home+" "+sc.h)+'</b>'+(c?' <span>· '+q(c)+'</span>':'');}}
    if(box.innerHTML!==h)box.innerHTML=h;}}
  else if(box)box.remove();}})}}
window.d503lt=liveTags;liveTags();setInterval(liveTags,15000);fastScores();setInterval(fastScores,1000);
document.addEventListener("visibilitychange",fastScores);
tick();setInterval(tick,30000);check();setInterval(check,60000);document.addEventListener("visibilitychange",check);}})();
</script><script>
(function(){{   // 🤔 ASK THE ENGINE: the engine's read on any game, from reads.json (not our picks, never in the record)
var games=[], q=document.getElementById("askq"), list=document.getElementById("asklist"), out=document.getElementById("askout");
if(!q) return;
var AI="{ask_url}", hist=[];                                   // 🧠 the AI question box (the relay), when it's live
function ai(){{
  var t=q.value.trim(); if(!AI||!t) return;
  list.innerHTML="";
  out.innerHTML='<section class="pk ask-c" style="--c1:#22d3ee;--c2:#b36bff"><div class="ask-l">🤔 '+esc(t)+'</div><div class="ask-a">🧠 The engine’s doing its homework…</div></section>';
  var ctl=window.AbortController?new AbortController():null, to=setTimeout(function(){{if(ctl)ctl.abort()}},90000);
  fetch(AI,{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{q:t,history:hist}}),signal:ctl?ctl.signal:undefined}})
  .then(function(r){{return r.ok?r.json():Promise.reject(r.status)}})
  .then(function(d){{clearTimeout(to);if(!d||!d.answer)throw 0;
    hist.push({{role:"user",content:t}},{{role:"assistant",content:d.answer}});hist=hist.slice(-6);
    out.innerHTML='<section class="pk ask-c" style="--c1:#22d3ee;--c2:#b36bff"><div class="ask-l">🤔 '+esc(t)+'</div><div class="ask-a">'+esc(d.answer).replace(/\\*\\*(.+?)\\*\\*/g,"<b>$1</b>").replace(/\\n/g,"<br>")+'</div></section>'}})
  .catch(function(){{clearTimeout(to);out.innerHTML="";render();
    list.insertAdjacentHTML("afterbegin",'<div class="ask-n">The AI’s taking a breather — here’s the engine’s quick read instead. 👇</div>')}});
}}
q.addEventListener("keydown",function(e){{if(e.key==="Enter"){{e.preventDefault();ai()}}}});
var go=document.getElementById("askgo"); if(go) go.addEventListener("click",ai);
function esc(x){{return String(x).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
function am(o){{return o>0?"+"+o:String(o)}}
function tm(s){{try{{return new Date(s.replace("Z",":00Z")).toLocaleString("en-US",{{weekday:"short",hour:"numeric",minute:"2-digit",timeZone:"America/Los_Angeles"}})+" PT"}}catch(e){{return ""}}}}
function pick(id,arr){{var h=0;for(var i=0;i<id.length;i++)h=(h*31+id.charCodeAt(i))%9973;return arr[h%arr.length]}}
var WHY={{steep:["They should win, but that price is way too steep. We ain’t laying all that.","Big favorite, but that number’s expensive as hell. Not worth it to us.","Yeah they probably win — but you gotta risk a grip to win a lil. Pass."],
 coin_flip:["This one’s a coin flip. The engine can barely separate these two.","Too close to call. Could go either way — we ain’t touching it.","50/50 type shit. No edge for us here."],
 tight:["There’s a lil value here, but it didn’t make the board — we keep the board tight.","Slight edge, but not enough for us to put our name on it.","It’s close to a play, but we only post what we’re sure about."],
 no_value:["The books got this one priced about right. Nothing for us here.","Line’s fair — no real value, so it’s not a pick.","Books did their homework on this one. No edge."]}};
var OUT=["You’re on your own with this one. Good luck — hope it smacks. 🤞","Your call, not ours. Hope it cashes. 🤞",
 "We ain’t on it, so you’re riding solo. Hope it hits. 🤞","If you tail it, that’s on you. Hope it smacks. 🤞"];
function vibe(p,id){{return pick(id+"v",p>=0.65?["The engine likes them to handle business.","They should take care of business.","Engine’s feeling good about this side.","They got the better squad and it shows."]:
 p>=0.55?["Slight lean our way — nothing crazy.","Small edge, but it’s there.","Leaning this way, not banging the table.","A lil lean — don’t go crazy on it."]:
 ["Barely a lean. Proceed with caution.","Basically a toss-up — tiny lean.","Hair of a lean. Be careful with this one.","Thin lean. Don’t bet the rent."])}}
function show(g){{
  var L=g.lean||{{market:"ml",reasons:[]}}, mk=L.market=="ml"?"ML":(L.line>0?"+":"")+L.line+(g.league=="nhl"?" puck line":g.league=="mlb"?" run line":g.league=="tennis"?" games":""), pct=Math.round(L.p*100);
  var h='<section class="pk ask-c" style="--c1:#22d3ee;--c2:#b36bff"><div class="lt"><span class="lgb">'+g.emoji+" "+esc(g.sport)+'</span><span class="tm">'+tm(g.start)+'</span></div>'+
    '<div class="ls">'+esc(g.away)+(g.vs?" vs ":" @ ")+esc(g.home)+'</div>';
  var KIND={{two:"2-Leg",three:"3-Leg",lock:"Lock of the Day",dog:"Dog of the Day",eight:"8-Leg",solo:"One-Game Pick",four:"4-Leg"}};
  if(g.why=="on_board"&&g.lean){{var mk0=L.market=="ml"?"ML":(L.line>0?"+":"")+L.line;
    if(L.result){{h+='<div class="ask-l">'+(L.result=="won"?"✅":"❌")+' We had <b>'+esc(L.team)+" "+mk0+'</b> <span class="od">'+am(L.odds)+'</span></div>'+
      '<div class="ask-a">'+(L.result=="won"?pick(g.id+"w",["Cashed. Told y’all. 💰","That one hit. Trust the algorithm. 💰"]):pick(g.id+"l",["That one didn’t hit. It’s in the record — no hiding.","L on that one. Counted in our record, full transparency."]))+'</div></section>';out.innerHTML=h;return}}
    h+='<div class="ask-l">🎯 We already on this one: <b>'+esc(L.team)+" "+mk0+'</b> <span class="od">'+am(L.odds)+'</span></div>'+
       '<div class="ask-a">It’s in our '+(KIND[g.board]||"board")+'. That’s our side — '+pick(g.id+"b",["tail it or don’t, but we ain’t switching up.","we riding with it.","no flip-flopping over here."])+'</div>'+
       (L.reasons.length?'<div class="why">'+L.reasons.map(esc).join(" · ")+'</div>':"")+'</section>';out.innerHTML=h;return}}
  if(g.why=="started"||g.why=="final"){{h+='<div class="ask-a">'+(g.why=="final"?"⏹️ This one’s over — no reads on finished games.":
    pick(g.id+"s",["⏱️ This one already kicked off — pregame reads are closed. Peep LIVE PLUS MONEY up top: if the algorithm sees live value, it shows up there.",
                   "⏱️ Game’s already going. No pregame reads once it starts — watch LIVE PLUS MONEY, that’s where the in-game value shows up."]))+'</div></section>';out.innerHTML=h;return}}
  h+='<div class="ask-l">🧠 The engine’s leaning: <b>'+esc(L.team)+" "+mk+'</b> <span class="od">'+am(L.odds)+'</span></div>'+
     '<div class="ask-a">'+pct+'% to '+(L.market=="ml"?"win":"cover")+(L.market!="ml"?" ("+Math.round(L.win_p*100)+"% to win)":"")+' · '+vibe(L.p,g.id)+'</div>'+
     (L.reasons.length?'<div class="why">'+L.reasons.map(esc).join(" · ")+'</div>':"")+
     (g.h1?'<div class="ask-h">⏱️ '+(g.h1.name=="first 5 innings"?"After 5 innings":g.h1.name=="1st period"?"After the 1st":"At the half")+': we got <b>'+esc(g.h1.team)+'</b> up — '+Math.round(g.h1.p*100)+'%'+(g.h1.tie>0.05?' (tied '+Math.round(g.h1.tie*100)+'%)':'')+'. '+pick(g.id+"h",["No 1st-half line posted yet, so that’s just the read.","Just the read — books ain’t posted the 1st-half line.","That’s our read on the early action."])+'</div>':"")+
     '<div class="ask-w">Why it’s not a pick: '+pick(g.id,WHY[g.why]||WHY.no_value)+'</div>'+
     '<div class="ask-d">⚠️ Not our pick — this doesn’t count toward our record. '+pick(g.id+"x",OUT)+'</div></section>';
  out.innerHTML=h;
}}
var STOP={{"who":1,"wins":1,"win":1,"will":1,"the":1,"and":1,"what":1,"think":1,"you":1,"about":1,"game":1,"tonight":1,"today":1,"does":1,"engine":1,"gonna":1,"should":1,"bet":1,"take":1,"vs":1,"over":1,"under":1,"first":1,"half":1,"spread":1,"total":1,"lean":1,"lock":1,"pick":1,"with":1,"for":1,"this":1,"that":1,"how":1,"like":1}};
var loaded=false, NOPE=["My bad — the engine can’t answer that one yet. We gotta update this shit. 🛠️ Try a team on today’s slate.",
 "Damn, we got nothing on that one. My bad — the engine’s still learning. Try another team. 🛠️",
 "My bad, can’t answer that one right now. Either it ain’t on the slate, it already started, or the books ain’t posted a line. 🛠️",
 "That one’s over the engine’s head for now. My bad — we updating it. Try a team name. 🛠️"];
function note(){{
  var t=q.value.toLowerCase(), n=[];
  if(/yard|rebound|assist|strikeout|touchdown|\\btd\\b|recept|rushing|passing|receiving|home run|homer|\\bprops?\\b|anytime|\\bshots?\\b|\\bsaves?\\b|\\bhits\\b|\\bpoints\\b|\\bpts\\b/.test(t))
    return '<div class="ask-prop">'+pick(t,["🙅 We don’t do no player props. Too risky, bro.","🙅 Player props? Nah. Risky ass shit — we stay away.",
      "🙅 No player props over here. One tweak and you’re cooked. We pass.","🙅 We don’t touch player props. Too many ways to lose. Stick to the games."])+'</div>';
  if(/over|under|\\btotal|o\\/u/.test(t)) n.push(pick(t+"ou",["📚 Over/unders: we studied 75,000+ games and the books are too sharp on totals right now. The engine ain’t gonna guess — we add ’em the day we can beat ’em.",
      "📚 Totals? We ran the numbers on every game for years — no real edge yet, so we don’t touch ’em. Accuracy over everything."]));
  if(/first half|1st half|1h|first 5|f5|first period|1st period/.test(t)) n.push("⏱️ First-half / first-5 / 1st-period reads show inside each game below.");
  return n.length?'<div class="ask-n">'+n.join("<br>")+'</div>':"";
}}
function lev(a,b){{if(Math.abs(a.length-b.length)>1)return 2;var d=[],i,j;for(i=0;i<=a.length;i++)d[i]=[i];for(j=0;j<=b.length;j++)d[0][j]=j;
  for(i=1;i<=a.length;i++)for(j=1;j<=b.length;j++)d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]==b[j-1]?0:1));return d[a.length][b.length]}}
function hit(w,hay){{                                          // loose matching: part of a name, plurals, a small typo
  if(hay.indexOf(w)>=0) return true;
  return hay.split(/[^a-z0-9]+/).some(function(t){{return t.length>=4&&w.length>=4&&(t.indexOf(w)==0||w.indexOf(t)==0||(w.length>=5&&lev(w,t)<=1))}});
}}
function render(){{
  out.innerHTML="";
  if(!loaded){{list.innerHTML='<div class="ask-n">⏳ Hold up — pulling up the engine’s reads…</div>';return}}
  var words=q.value.toLowerCase().replace(/[^a-z0-9 ]/g," ").split(/\s+/).filter(function(w){{return w.length>2&&!STOP[w]}});
  var hits=games.filter(function(g){{return words.some(function(w){{return hit(w,(g.away+" "+g.home+" "+g.sport).toLowerCase())}})}}).slice(0,12);
  if(!hits.length&&q.value.trim()){{                          // no team named (or no match): show the slate - always an answer
    var live=games.filter(function(g){{return g.why!="final"&&!g.done}});
    list.innerHTML=note()+(live.length?'<div class="ask-n">'+pick(q.value,["Here’s what’s on the slate — tap a game and the engine’ll break it down. 👇",
      "Not sure which game you mean — here’s everything we got. Tap one. 👇","Pick your game and we’ll tell you how we’re leaning. 👇"])+'</div>'+
      live.map(function(g){{return '<button class="ask-g" data-i="'+games.indexOf(g)+'">'+g.emoji+" "+esc(g.away)+(g.vs?" vs ":" @ ")+esc(g.home)+' <small>'+tm(g.start)+'</small></button>'}}).join(""):
      '<div class="ask-n">'+pick(q.value,NOPE)+'</div>');
    return;
  }}
  if(!words.length&&!note()){{list.innerHTML="";return}}
  if(!games.length){{list.innerHTML=note()+'<div class="ask-n">No games left on the slate right now. The engine drops new reads as soon as the next lines post.</div>';return}}
  list.innerHTML=note()+(hits.length?hits.map(function(g){{return '<button class="ask-g" data-i="'+games.indexOf(g)+'">'+g.emoji+" "+esc(g.away)+(g.vs?" vs ":" @ ")+esc(g.home)+' <small>'+tm(g.start)+'</small></button>'}}).join(""):
    '<div class="ask-n">'+pick(q.value,NOPE)+'</div>');
  if(hits.length==1&&words.length) show(hits[0]);
}}
list.addEventListener("click",function(e){{var b=e.target.closest(".ask-g");if(b)show(games[+b.dataset.i])}});
q.addEventListener("input",function(){{if(!AI)render()}});   // with the AI on: nothing pops up while typing
var timer=setTimeout(function(){{if(!loaded){{loaded=true;games=[];if(!AI)list.innerHTML='<div class="ask-n">The engine’s still cooking up the reads — check back in a few. 🍳</div>'}}}},8000);
function got(d){{return (d&&d.games)||[]}}
Promise.all([fetch("reads.json?v="+Date.now()).then(function(r){{return r.json()}}),
  fetch("reads_tennis.json?v="+Date.now()).then(function(r){{return r.json()}}).catch(function(){{return {{}}}})])
.then(function(ds){{clearTimeout(timer);loaded=true;games=got(ds[0]).concat(got(ds[1]));if(!AI)render()}})
.catch(function(){{clearTimeout(timer);loaded=true;if(!AI)list.innerHTML='<div class="ask-n">The engine’s still cooking up the reads — check back in a few. 🍳</div>'}});
if(!AI)render();
}})();
</script><script>
(function(){{   // 🔔 LIVE BET ALERTS: native Web Push. On iPhone it only works from the home-screen app (iOS 16.4+)
var API="{api}", b=document.getElementById("bellb"), n=document.getElementById("belln");
if(!b||!API)return;
var ua=navigator.userAgent||"", ios=/iPhone|iPad|iPod/.test(ua)||(/Macintosh/.test(ua)&&navigator.maxTouchPoints>1);
var home=navigator.standalone===true||!!(window.matchMedia&&matchMedia("(display-mode: standalone)").matches);
var ok=("serviceWorker" in navigator)&&("PushManager" in window)&&("Notification" in window);
function note(h){{n.innerHTML=h||"";n.hidden=!h}}
function set(on){{b.textContent=on?"🔔 Alerts on ✅":"🔔 Get live bet alerts";b.classList.toggle("on",!!on);
 try{{if(on)localStorage.setItem("d503push","1");else localStorage.removeItem("d503push")}}catch(e){{}}}}
function bytes(s){{s=s.replace(/-/g,"+").replace(/_/g,"/");var r=atob(s+"===".slice((s.length+3)%4)),a=new Uint8Array(r.length);
 for(var i=0;i<r.length;i++)a[i]=r.charCodeAt(i);return a}}
function key(){{return fetch(API+"/vapid",{{cache:"no-store"}}).then(function(r){{if(!r.ok)throw new Error("vapid");return r.json()}}).then(function(j){{return j.key}})}}
function same(sub,k){{try{{var a=new Uint8Array(sub.options.applicationServerKey),c=bytes(k);if(a.length!==c.length)return false;
 for(var i=0;i<a.length;i++)if(a[i]!==c[i])return false;return true}}catch(e){{return true}}}}
function post(path,sub){{return fetch(API+path,{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(sub)}})
 .then(function(r){{if(!r.ok)throw new Error(path+" "+r.status);return r}})}}
function reg(){{return navigator.serviceWorker.register("sw.js",{{scope:"./"}}).then(function(){{return navigator.serviceWorker.ready}})}}
function subscribe(k){{return reg().then(function(r){{return r.pushManager.subscribe({{userVisibleOnly:true,applicationServerKey:bytes(k)}})}})
 .then(function(s){{return post("/subscribe",s.toJSON())}}).then(function(){{set(true);try{{localStorage.setItem("d503pushT",String(Date.now()))}}catch(e){{}}}})}}
var was=false;try{{was=localStorage.getItem("d503push")==="1"}}catch(e){{}}
set(was);b.hidden=false;
if(ios&&!home){{   // the Safari tab: iOS only lets the home-screen app ask
 b.onclick=function(){{note("📲 Add D503 to your Home Screen first (<b>Share</b> ⬆️ → <b>Add to Home Screen</b>), then tap 🔔 there.")}};return}}
if(!ok){{b.onclick=function(){{note(ios?"📲 Alerts need iOS 16.4 or newer — update in Settings → General → Software Update.":
 "This browser can’t do alerts — open the dashboard in Chrome or Safari.")}};set(false);return}}
if(Notification.permission!=="granted")set(false);
reg().then(function(r){{return r.pushManager.getSubscription()}}).then(function(s){{   // re-check the real subscription
 if(!s||Notification.permission!=="granted"){{set(false);return}}
 set(true);
 return key().then(function(k){{
  if(!same(s,k))return s.unsubscribe().then(function(){{return subscribe(k)}});   // the Worker's key changed: re-join
  var t=0;try{{t=+localStorage.getItem("d503pushT")||0}}catch(e){{}}
  if(Date.now()-t>7*864e5)return post("/subscribe",s.toJSON()).then(function(){{try{{localStorage.setItem("d503pushT",String(Date.now()))}}catch(e){{}}}});
 }});
}}).catch(function(){{}});
b.onclick=function(){{
 if(b.classList.contains("on")){{
  if(!confirm("Turn off live bet alerts?"))return;
  navigator.serviceWorker.ready.then(function(r){{return r.pushManager.getSubscription()}}).then(function(s){{
   if(!s)return;return post("/unsubscribe",{{endpoint:s.endpoint}}).catch(function(){{}}).then(function(){{return s.unsubscribe()}})}})
  .catch(function(){{}}).then(function(){{set(false);note("🔕 Alerts off. Tap 🔔 any time to turn them back on.")}});return}}
 b.disabled=true;note("");
 var asked=Notification.requestPermission();   // straight from the tap (iOS needs that)
 Promise.resolve(asked).then(function(p){{if(p!=="granted")throw "denied";return key()}}).then(subscribe)
 .then(function(){{note("You’re locked in 🔥 Watch for the welcome alert.")}})
 .catch(function(e){{set(false);note(e==="denied"?"🔕 Alerts are blocked. Turn them on in Settings → Notifications → D503 Sports, then tap 🔔 again.":
  "😬 Couldn’t turn alerts on — try again in a sec.")}})
 .then(function(){{b.disabled=false}});
}};
}})();
</script></body></html>"""


def write(picks, model, games, series, start_bank, path=PAGE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(render(picks, model, games, series, start_bank, int(time.time() * 1000)))
    try:
        write_sw(os.path.join(os.path.dirname(path), "sw.js"))
    except OSError as e:
        print(f"sw.js failed: {e}")
    try:
        write_brain(picks, games, os.path.join(os.path.dirname(path), "brain.json"))
    except Exception as e:                                   # noqa: BLE001 - the page never waits on the brain
        print(f"brain.json failed: {e}")


def _leg_brain(l):
    return {k: l.get(k) for k in ("league", "team", "opp", "market", "line", "odds", "p", "tier", "result", "score",
                                  "start", "breakdown", "outs", "opp_outs", "injury_alerts", "reasons") if l.get(k) not in (None, [], "")}


def write_brain(picks, games, path=BRAIN):
    """The AI question box's data sheet: the board, the records, recent results, every game's read, what the studies
    found, the public splits and the live plus money board. Plain facts - the bot answers only from this."""
    def _j(p, default=None):
        try:
            with open(p) as f:
                return json.load(f)
        except (OSError, ValueError):
            return default
    now = datetime.now(PT)
    today, tmr = now.date().isoformat(), (now + timedelta(days=1)).date().isoformat()
    board = [{"date": p["date"], "kind": p["kind"], "status": p["status"], "odds": p.get("american"),
              "legs": [_leg_brain(l) for l in p["legs"]], "waiting_on": p.get("waiting")}
             for p in picks if p["date"] in (today, tmr)]
    recent = [{"date": p["date"], "kind": p["kind"], "status": p["status"], "lean": bool(p.get("lean")),
               "legs": [f"{l['team']} {l['market']}{'' if l.get('line') is None else ' ' + format(l['line'], '+g')} "
                        f"{l['odds']:+d} -> {l.get('result') or 'pending'}" for l in p["legs"]]}
              for p in sorted(picks, key=lambda p: p["date"])[-40:] if p["status"] in ("won", "lost", "push")]
    import sports_dogs
    import sports_selfcheck
    import sports_trends
    dogs = sports_dogs.load()
    studies = {
        "underdogs + favorites": {lg: {"proven dog spots": v.get("proven"), "trap dog spots (never taken)": v.get("traps"),
                                       "favorites/dogs price check proven": (v.get("price") or {}).get("proven"),
                                       "price table (book said vs really won)": (v.get("price") or {}).get("table")}
                                  for lg, v in dogs.items()},
        "trends": {"proven": (sports_trends.load() or {}).get("proven"),
                   "active now": [{k: t.get(k) for k in ("league", "situation", "trend", "record", "streak", "verdict", "upcoming_names")}
                                  for t in ((sports_trends.load() or {}).get("active") or [])[:15]]},
        "self-check on our picks": sports_selfcheck.summary(sports_selfcheck.load()),
        "spread vs moneyline": _j(os.path.join(sd.DATA, "ats.json"), {}),
        "rigged / fade the public": {k: v for k, v in ((_j(os.path.join(sd.DATA, "rigged.json"), {}) or {}).get("cells") or {}).items()
                                     if k.startswith("all|") or v.get("proven")},
        "over/unders proven in": [lg for lg, v in (_j(os.path.join(sd.DATA, "totals.json"), {}) or {}).items()
                                  if isinstance(v, dict) and v.get("proven")],
    }
    live = (_j(LIVE_JSON_PATH, {}) or {})
    tennis_picks = []                                        # 🎾 our posted tennis picks (their own record) - the last 3 slates
    for sl in (_j(os.path.join(sd.DATA, "tennis", "picks.json"), []) or [])[-3:]:
        pars = sl.get("parlays") or ({"mixed": sl["parlay"]} if sl.get("parlay") else {})
        tennis_picks.append({
            "slate": sl.get("date"),
            "picks": [{"player": l.get("player"), "vs": l.get("opp"),
                       "tour": "women's" if l.get("tour") == "wta" else "men's", "tourney": l.get("tourney"),
                       "round": l.get("round"),
                       "bet": f"{l['hcp']:+g} games" if l.get("market") == "spread" and l.get("hcp") is not None else "ML",
                       "odds": l.get("odds"), "engine win %": round(100 * l["p"]) if l.get("p") else None,
                       "result": l.get("result") or "not played yet",
                       "score (our player first)": ", ".join(
                           s_.strip() if l.get("side", 1) == 1 else "-".join(reversed(s_.strip().split("-")))
                           for s_ in (l.get("score") or "").split(",") if s_.strip()) or None,
                       "start": l.get("start")} for l in sl.get("picks") or []],
            "parlays": {k: {"odds": v.get("american"), "status": v.get("status"), "legs": len(v.get("legs") or [])}
                        for k, v in pars.items() if v}})
    brain = {"updated": now.strftime("%Y-%m-%d %I:%M %p PT"), "today": today, "tomorrow": tmr,
             "records": RECORDS, "board (today + tomorrow)": board, "recent graded picks": recent,
             "every game's read (not our picks)": (_j("docs/sports/reads.json", {}) or {}).get("games", []),
             "tennis picks (own record, not ours)": tennis_picks,
             "tennis reads": (_j("docs/sports/reads_tennis.json", {}) or {}).get("games", []),
             "public betting splits (% of bets / % of money)": _j(os.path.join(sd.DATA, "public_live.json"), {}),
             "live plus money right now": live.get("plays") or live.get("board") or [],
             "studies": studies}
    with open(path + ".tmp", "w") as f:
        json.dump(brain, f, separators=(",", ":"), default=str)
    os.replace(path + ".tmp", path)
