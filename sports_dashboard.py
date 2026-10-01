"""Phone dashboard for THE D503 SPORTS ENGINE (docs/sports/index.html).
Top: today's board (2-leg, 3-leg, lock, dog). Below: results, record, and what the engine learned.
Self-contained HTML (inline CSS/SVG, tiny JS for the live scores and the 🟢 LIVE light)."""
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
PLAY_FRESH_S = 45             # a live play shows only while the watcher re-checked its price in the last 45s (it
                              # re-checks every second and re-sends at least every 15s): a frozen price never shows
LOOK = {   # kind -> label, accent, second accent - in BOARD ORDER: the Lock of the Day always on top (the owner, 9/29)
    "lock":  ("LOCK OF THE DAY", "#22e39a", "#0fb87a"),
    "dog":   ("DOG OF THE DAY", "#ff5a1f", "#ff2a2a"),
    "two":   ("2-LEG PARLAY", "#2f8bff", "#22d3ee"),
    "three": ("3-LEG PARLAY", "#ffc233", "#ff8a00"),
    "four": ("4-LEG PARLAY", "#b36bff", "#ff4fd8"),
    "solo": ("ONE-GAME PICK", "#22e39a", "#22d3ee"),
    "night": ("NIGHT FOOTBALL", "#2f8bff", "#22e39a"),   # 🏈 Monday / Thursday football: every game gets a pick
    "eight": ("8-LEG (RETIRED)", "#8a5cff", "#c04fd8"),
}
BIG_HIT = 300                 # +300 and up that cashes gets the big brag
ICON = {"night": "🏈", "solo": "🎯", "two": "⚡", "three": "👑", "four": "🚀", "eight": "🎰", "lock": "🔒", "dog": "🐺"}
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
    if e.get("result") is None:                              # still going: just the hold - a score from when it went
        return _hold_line(e, used)                           # up reads wrong minutes later (the owner, 9/29)
    if lg == "tennis":
        return _tennis_live_story(e, used)
    m = re.match(r"(.+?) (\d+) @ (.+?) (\d+)$", str(e.get("score_at_post") or ""))
    if not m:
        return ""
    away, a_s, home, h_s = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    ours_away = e.get("side") == "away"
    us = _the(e["team"], lg)
    mine, theirs = (a_s, h_s) if ours_away else (h_s, a_s)
    ck = str(e.get("clock_at_post") or "")                  # '6:12 - 2nd' / '1st Intermission' (older: 'Q2 3:00')
    per = re.search(r"(\d+)(?:st|nd|rd|th)", ck) or re.search(r"(\d+)", ck)
    n = int(per.group(1)) if per else 0
    unit = {"nhl": "period", "ncaab": "half", "mlb": "inning"}.get(lg, "quarter")
    w = f"in the {({1: '1st', 2: '2nd', 3: '3rd'}.get(n, f'{n}th'))} {unit}" if n else "mid-game"
    if re.search(r"\b(\d?OT|SO)\b", ck):
        w = "in overtime"
    elif "Halftime" in ck:
        w = "at halftime"
    an, hn = _the(away, lg), _the(home, lg)
    what = "come back" if mine < theirs else "hold on" if mine > theirs else "take it"
    res = e.get("result")
    best = e.get("best_odds") or e.get("odds") or 0
    ran = res == "won" and best >= (e.get("odds") or 0) + 40      # the line ran long while it was up - and it cashed
    seed = f'{e.get("posted") or e.get("date")}|{e["team"]}|{e.get("odds")}'    # stable: same bet, same words
    return sports_lingo.live_story(res, seed, used, ran=ran, an=an, a=a_s, hn=hn, h=h_s, w=w, us=us, what=what, best=best)


def _hold_line(e, used):
    """A still-going live bet's line. The name's masked while it's picked, so no two bets on the night share a line's
    shape (9/29: 'Sticking with Kudermetova till it's done', then 'Sticking with Snigur till it's done')."""
    lg = e.get("league", "")
    import sports_tennis as stn
    me = (stn._say_name(e.get("team")) if lg == "tennis" else _the(e.get("team", ""), lg)) or "our pick"
    seed = f'{e.get("posted") or e.get("date")}|{e.get("team")}|{e.get("odds")}'
    return _cap(sports_lingo.say("lv:hold", seed, used, me="ourplayer").replace("ourplayer", me).replace("Ourplayer", me))


def live_stories(entries):
    """Every live bet's line on the list, oldest first, sharing one `used`: a graded bet's hold line (what it said
    while it was going) stays spoken for, so a newer bet never repeats it later that night."""
    used, out = set(), {}
    for e in sorted(entries, key=lambda e: e.get("posted", "")):
        if e.get("result") is not None:
            _hold_line(e, used)
        out[id(e)] = _live_story(e, used)
    return out


LIVE_KEEP_HOUR_PT = 8         # a day's live bets (cashed, lost or still going) stay on the list till the next board
                              # drops at 8 AM PT - then they live on in PAST RESULTS (the owner, 9/29)


def live_days(now_pt):
    """The dates whose live bets are on the LIVE PLUS MONEY list right now."""
    d = now_pt.date()
    return {d.isoformat()} | ({(d - timedelta(days=1)).isoformat()} if now_pt.hour < LIVE_KEEP_HOUR_PT else set())


def _live_by_sport(entries):
    """The live plus money record, one line per sport (the owner, 9/29: see how the engine does in each sport - never
    one number for all of them). Busiest sport first."""
    by = {}
    for e in entries:
        if e.get("result") in ("won", "lost"):
            by.setdefault(live_sport_key(e), [0, 0])[e["result"] == "lost"] += 1
    return ('<div class="hs-by">' + "".join(                 # tap a sport: its live bets open right under it
        f'<div class="tap" data-hs="📡 {E(k)}"><span>{E(k)}</span><b>{w_}-{l_}</b><i>{w_ / (w_ + l_):.0%}</i><em>▾</em></div>'
        for k, (w_, l_) in sorted(by.items(), key=lambda kv: -sum(kv[1]))) + "</div>") if by else ""


def live_sport_key(e):
    return f"{_live_icon(e)} {_live_sport(e)}"


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


TIER_CHIP = {"ou": '<span class="chip val">📏 O/U</span>', "lock": '<span class="chip lk">🔒 LOCK</span>', "value": '<span class="chip val">🔥 VALUE PLAY</span>',
             "lean": '<span class="chip lean">🟡 SLIGHT LEAN</span>', "strong": '<span class="chip lean">💪 STRONG LEAN</span>'}
TIER_LOOK = {"lock": ("🔒 LOCKS", "#22e39a", "#0fb87a"), "value": ("🔥 VALUE PLAYS", "#ff5a1f", "#ff8a00"),
             "lean": ("🟡 LEANS", "#ffc233", "#e8c77a")}




LIVE_NO_UNITS = '<div class="nou">🎲 NO UNITS ON THESE — WE GAMBLIN’</div>'   # (the owner, 9/30)
UNITS_ON = True              # the owner OK'd it 9/30: the engine sizes every play by its own edge (the sizing study)


HALF_WHY = {   # ½u - the owner, 9/30: people need the WHY (big bets on expensive lines lose money over time)
    "fav": ("Line's too expensive — betting big at prices like this loses money over time.",
            "Expensive line. Big bets at prices like this lose money in the long run.",
            "Line's too expensive. Big bets at expensive prices lose money long term.",
            "Pricey line. Over time, big bets at this kind of price lose money.",
            "At a price this steep, big bets lose money long term. Keep it small.",
            "Expensive line — the long-run money says keep this bet small."),
    "dog": ("Small bet, big payout — the value's still worth it.", "Small bet, big payout — still worth it.",
            "Plus money does the heavy lifting. A small bet is plenty.", "Small stake, big return if they cash.",
            "Big payout on a small bet — that's the play.", "Keep it small — the plus money pays big when it hits.")}
FULL_WHY = {   # 1-1½u: why it's more than ½
    "fav": ("Fair price — worth a full unit.", "The price is fair — a solid bet.", "Price is right where we want it. Full unit.",
            "Not too expensive — worth a full unit.", "Fair line for how much we like it. Solid bet."),
    "dog": ("Real value here — worth a full unit.", "The value's real — a solid bet.", "Good value at this price. Full unit.",
            "The payout's worth more than the risk. Solid bet.", "Plus money with real value — full unit.")}
BIGGER_WHY = {   # 2-3½u
    "fav": ("Good price — worth a bigger bet.", "Price is right — we bet this one bigger.",
            "This line's cheaper than it should be. Bigger bet.", "Good number on a team we like. Bigger bet.",
            "The price gives us an edge — we go bigger."),
    "dog": ("The value's there — worth a bigger bet.", "Good value — we bet this one bigger.",
            "The payout's bigger than it should be. We go bigger.", "Real value on a plus-money price. Bigger bet.",
            "This dog's paying more than it should. Bigger bet.")}
BIG_WHY = {   # 4u+
    "early": ("Big edge before the line moves — load up.", "The engine sees this line moving our way. Big bet.",
              "We got in before the line moves. Big bet.", "Price won't last — the engine's betting big.",
              "Early number with a big edge. Load up."),
    "board": ("Big edge at this price — big bet.", "This price is a gift — load up.", "The engine's all over this one. Big bet.",
              "Priced way too cheap. We're betting big.", "Too good a price to bet small. Load up.")}
# (the owner's words, 9/30: EVERY size says why in a few plain words, 5+ ways each so nothing repeats - never doubt in
# our own pick)


WHY_USED = set()                 # the unit reasons already on the page this build (reset in render)


def _units_line(u, key="", odds=None, early=False):
    if not UNITS_ON:
        return ""
    if not u:                                                # a lean: no units (the owner, 9/30)
        return '<div class="un">🟡 NO UNITS — JUST A LEAN</div>'
    side = "dog" if (odds or 100) > 0 else "fav"             # (a plus-money dog is never "expensive")
    pool = (HALF_WHY[side] if u == 0.5 else FULL_WHY[side] if u < 2 else BIGGER_WHY[side] if u < 4 else
            BIG_WHY["early" if early else "board"])
    start = sum(map(ord, key))                               # a line already on the board this build is skipped
    order = [pool[(start + i) % len(pool)] for i in range(len(pool))]   # (never the same reason twice in a row)
    why = next((x for x in order if x not in WHY_USED), order[0]) if pool else ""
    WHY_USED.add(why)
    return (f'<div class="un"><span class="mb">💰</span> {_units_txt(u)}'
            + (f'<span class="unw">{E(why)}</span>' if why else "") + '</div>')   # units only - everybody's unit is
    #                                                                              their own bankroll's (the owner, 9/30)


def _units_txt(u):
    n = f"{int(u)}½" if u % 1 else f"{int(u)}"             # 5½ UNITS, not 5.5
    return "½ UNIT" if u == 0.5 else f"{n} UNIT" + ("" if u == 1 else "S")


def units_box(picks, today=None):
    """💰 The open bankroll (the owner + Ricky, 9/30: measure it like money, not just W-L; everything transparent): $1,000
    to start, a unit = 1% of the bankroll that morning, every graded pick at its size and price. Said in plain dollars +
    ROI only (the owner, 9/30: '+6.6u on 14u bet' was confusing)."""
    import sports
    import sports_early
    led = sports.units_ledger(picks, sports_early.load().get("picks") or [])
    if not led["rows"]:
        return ""
    bank, start = led["bankroll"], sports.BANKROLL_START
    today = today or datetime.now(sports.PT).strftime("%Y-%m-%d")
    wk = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d")

    def line(label, rs, cls="unr"):                          # '+$66.68 · +47% ROI' over some picks
        nd, nu, u = sum(r[3] for r in rs), sum(r[2] for r in rs), sum(r[1] for r in rs)
        return (f'<div class="{cls}"><span>{E(label)}</span><b class="{"up" if nd >= 0 else "dn"}">'
                f'{"+" if nd >= 0 else "-"}${abs(nd):,.2f} · {nu / u:+.0%} ROI</b></div>') if rs and u else ""
    rows = led["rows"]
    tier = lambda r: r[0].get("units_tier")
    out = (line("Overall", rows, "unr unh") + line("Today", [r for r in rows if r[0]["date"] == today])
           + line("Last 7 days", [r for r in rows if r[0]["date"] >= wk])
           + "".join(line(k, [r for r in rows if tier(r) == t]) for t, k in    # by kind of pick (the owner, 9/30: the
                     (("early", "⏰ Early value plays"), ("lock", "🔒 Locks"), ("value", "🔥 Value plays"),        # Dog of the Day is a value play)
                      ("strong", "💪 Strong leans"), ("slight", "🟡 Slight leans"))))
    return (f'<div class="unb"><div class="ovr-t"><span class="mb">💰</span> BANKROLL</div>'
            f'<div class="unt {"up" if bank >= start else "dn"}">${bank:,.2f}</div>'
            f'<div class="unp">Started at ${start:,.0f}<br>1 unit = 1% of our bankroll = ${led["unit_today"]:,.2f}</div>'
            f'{out}</div>')


def day_calls(picks, today):
    """The day's PICKS, each once (a parlay's picks count on their own; a pick on two cards once) -> ({key: result},
    anything still to grade?). The brain's day line and 📊 TODAY'S RESULTS both use it (the owner, 10/1: 3-2, not 1-4)."""
    import sports
    calls, pending = {}, False
    for p in picks:
        if p["date"] != today or p["kind"] == "eight" or not sports.in_record(p):
            continue
        for l in p.get("legs") or []:
            r = l.get("result") or (p.get("status") if len(p["legs"]) == 1 else None)
            key = (l.get("game_id"), l.get("side"), l.get("market"))
            if r in ("won", "lost"):
                calls[key] = r
            elif r not in ("push", "void") and key not in calls:
                pending = True
    return calls, pending


def day_recap(picks, today=None, early=None, now=None):
    """📊 The day's units, up top once every pick with units that day is graded (the owner, 10/1: 'after the last
    game of the day' - never a half-day number), gone at midnight Pacific. The bankroll's own plays only: the Lock, the
    Dog, value plays, early value plays (leans, parlays, live plus money, tennis keep their own records)."""
    import sports
    import sports_early
    now = now or datetime.now(sports.PT)
    today = today or now.strftime("%Y-%m-%d")
    early = sports_early.load().get("picks") or [] if early is None else early
    rows = [r for r in sports.units_ledger(picks, early)["rows"] if r[0]["date"] == today]
    calls, pending = day_calls(picks, today)
    if not rows or pending or sports.day_pending(picks, early, today):
        return ""                                            # (every pick in - leans too - never a half-day number)
    bet, net = sum(r[1] for r in rows), sum(r[2] for r in rows)
    w = sum(r == "won" for r in calls.values())              # the record: every pick (the owner, 10/1: we went 3-2 -
    l = sum(r == "lost" for r in calls.values())             # leans count in our record; the units are the plays with
    pu = 0                                                   # units only, leans carry none)
    midnight = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=sports.PT) + timedelta(days=1)
    rec = f"{w}-{l}" + (f"-{pu}" if pu else "")
    return (f'<div class="dayr {"up" if net >= 0 else "dn"}" data-until="{int(midnight.timestamp() * 1000)}">'
            f'<div class="dayr-t">📊 TODAY\'S RESULTS</div>'
            f'<div class="dayr-n">{"+" if net >= 0 else "-"}{abs(net):.1f} UNITS</div>'
            f'<div class="dayr-s">ROI {net / bet:+.0%} · {rec}</div></div>'
            f'<script>(function(){{var d=document.currentScript.previousElementSibling;'
            f'if(Date.now()>+d.dataset.until)d.remove();}})();</script>') if bet else ""


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


PENDING_TALK = re.compile(r"\s*(?:—\s*)?[^.!?—]*\b(?:gon'? see|finna see|we'?ll see)\b[^.!?]*[.!?]?", re.I)


SHOW_PCT_OVER = 55            # the owner, 9/30: a win % only shows when it's over 55% ("37% to cash is not the greatest")
_PCT = re.compile(r"(\d{1,2})% (to cash|to hit|to get it done|in our numbers)( on)?")


def pct_ok(text):
    """Any win % of 55 or under said as words instead ('54% to cash' -> 'the price is right')."""
    def sub(m):
        if int(m.group(1)) > SHOW_PCT_OVER:
            return m.group(0)
        if m.group(2) == "in our numbers":
            return "right in our numbers"
        return "the price is right" + (" on" if m.group(3) else "")
    out = _PCT.sub(sub, text)
    out = re.sub(r"(^|[.!?—] )the price is right", lambda m: m.group(1) + "The price is right", out)
    out = re.sub(r"\bat (\d{1,2})%", lambda m: m.group(0) if int(m.group(1)) > SHOW_PCT_OVER
                 else "right where we want 'em", out)
    return re.sub(r"\bgives (him|her) (\d{1,2})%", lambda m: m.group(0) if int(m.group(2)) > SHOW_PCT_OVER
                  else f"likes {m.group(1)} here", out)


_LATEST = re.compile(r"^📅 [^:]+: (.*)$")
_RES = re.compile(r" ([WLT]) \d+-\d+ (?:vs|@) ")


def latest_ok(line):
    """A 'latest games' line only stays when it backs the pick: we won our last one, and they lost theirs or had none
    (the owner, 9/30: "Kings L 1-5 vs Avalanche" in the Kings' breakdown hurts the pick). Covers breakdowns already
    posted, before the engine stopped writing them."""
    m = _LATEST.match(line)
    if not m:
        return True
    parts = m.group(1).split(" · ")
    res = [(_RES.search(x) or [None, None])[1] for x in parts]
    return res[0] == "W" and (len(res) < 2 or res[1] == "L")


def _breakdown(leg):
    secs = leg.get("breakdown")
    if not secs:
        return ""
    done = leg.get("result") in ("won", "lost", "push")
    lines = [pct_ok(x) for x in secs if isinstance(x, str) and latest_ok(x)]
    if done:                                                 # it's over: no "we gon' see" on a graded pick
        lines = [PENDING_TALK.sub("", x).rstrip(" —") or x for x in lines]
    body = "".join(f"<p>{E(x)}</p>" for x in lines)
    return (f'<details class="bd"><summary>🔍 {"Pregame breakdown" if done else "Full breakdown"}</summary>'
            f'<div class="bd-s">{body}</div></details>')


LEG_TAG = {"ou": '<span class="lt-t val">📏 O/U</span>', "lock": '<span class="lt-t lk">🔒 LOCK</span>', "value": '<span class="lt-t val">🔥 VALUE PLAY</span>',
           "lean": '<span class="lt-t lean">🟡 SLIGHT LEAN</span>', "strong": '<span class="lt-t lean">💪 STRONG LEAN</span>'}


WHY_TAG = {   # a pick written before the one-line "why" existed: its top reason, still said our way
    "the stronger team": "💪 {us} are just the better team tonight.",
    "hotter recent form": "🔥 {us} are playing better ball than {opp} lately.",
    "opponent missing key players": "🚑 {opp} are banged up — we pouncing.",
    "sharp money moving this way": "💸 The market's catching up to {us} — the engine had it first.",
    "better rested": "🛌 {us} got the extra rest. Fresh legs.",
    "opponent on a back-to-back": "😮‍💨 {opp} played last night — tired legs.",
    "better starting pitcher": "⚾ We got the better arm on the mound.",
    "hotter goalie": "🧱 {us} got the hotter goalie.",
    "better QB play lately": "🎯 {us} got the better QB play lately.",
    "revenge game": "😤 {us} owe {opp} one.",
}


def _why_fallback(leg):
    rs = leg.get("reasons") or []
    for r in [x for x in rs if x != "sharp money moving this way"] + [x for x in rs if x == "sharp money moving this way"]:
        if r in WHY_TAG:
            return WHY_TAG[r].format(us=leg["team"], opp=leg["opp"])
    return ""


EARLY_IN = {}                    # {(game id, side): the price we got in at} - early value plays (set in render)
EARLY_WHY = {   # (the owner, 9/30: an early play on the daily board says we got in early - and why it's still a play)
    "worse": ("⏰ We got in early at {o}. The market corrected, and it's still worth it at this price.",
              "⏰ Early bettors got {o}. The line moved, but the value's still here.",
              "⏰ We grabbed this at {o} early. Even after the move, it's still worth a bet."),
    "better": ("⏰ We got in early at {o} — and the price is even better now.",
               "⏰ Early bettors got {o}. It's paying even more now — still a play.")}


def _early_line(leg):
    """The 'we got in early' line for a daily pick that's also one of our early value plays ('' otherwise)."""
    o = EARLY_IN.get((leg.get("game_id"), leg.get("side")))
    if o is None or leg.get("market") != "ml":
        return ""
    better = sd.decimal(leg["odds"]) > sd.decimal(o)
    pool = EARLY_WHY["better" if better else "worse"]
    return f'<div class="why">{E(pool[sum(map(ord, leg.get("team", ""))) % len(pool)].format(o=_am(o)))}</div>'


def _leg(leg, tagged=False, review="", units=None):
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
    why = E(pct_ok(leg.get("why_line") or _why_fallback(leg)))      # a real line in our lingo, never a bare tag (the owner, 9/29)
    pub = leg.get("public")
    tag = ('<span class="pub fade">🤡 FADING THE PUBLIC</span>' if pub == "fade" else
           '<span class="pub ride">🤝 RIDING WITH THE PUBLIC</span>' if pub == "ride" else "")
    outs = f'<div class="outs">🚑 {E(leg["opp"])} missing: {E(", ".join(leg["opp_outs"]))}</div>' if leg.get("opp_outs") else ""
    if leg.get("injury_alerts") and not res:            # a status changed after we posted it: loud, right on the card
        outs += "".join(f'<div class="outs">⚠️ INJURY ALERT: {E(a)}</div>' for a in leg["injury_alerts"][-3:])
    if leg.get("line_alerts") and not res:              # the money ran away from us after we posted: loud, on the card
        outs += "".join(f'<div class="outs">💸 LINE ALERT: {E(a)}</div>' for a in leg["line_alerts"][-1:])
    return f"""<div class="leg {res or ''}">
  <div class="lt"><span class="lgb">{lg[3]} {lg[2]}{ltag}</span>{badge or f'<span class="tm" data-start="{E(leg["start"])}" data-gid="{E(leg.get("game_id", ""))}" data-side="{E(leg.get("side", ""))}" data-mk="{E(leg.get("market", ""))}" data-line="{E(str(leg.get("line") if leg.get("line") is not None else ""))}">Starts at {_time(leg["start"])}</span>'}</div>
  <div class="lm"><span class="pick">{mark}{E(leg["team"])} <em>{mk}</em></span><span class="od">{_am(leg["odds"])}</span></div>
  <div class="ls">{E(leg["opp"]) if leg["market"] == "total" else ("vs " if leg["home"] else "@ ") + E(leg["opp"])}</div>
  {_units_line(units, leg.get("team", ""), leg.get("odds")) if units is not None else ""}{_early_line(leg) if not res else ""}{f'<div class="why rvy">📝 {E(review)}</div>' if review else f'<div class="why rvy">{why}</div>' if why else ""}{f'<div class="pubs">{tag}</div>' if tag else ""}{outs}{_breakdown(leg)}
  {f'<div class="fin">Final: {E(leg["score"])}</div>' if leg.get("score") else ""}
</div>"""


FULL_BOARD = ("lock", "dog", "two", "three", "four")


def _short_note(day, day_picks):
    """A short board says so up top (fewer than the usual 5 plays, not a one-game day) - so nobody thinks it broke."""
    return ""                                                # the owner, 9/30: "take away that stupid disclaimer" -
    have = {p["kind"] for p in day_picks if not p.get("lean")}           # the board's always full now (Lock, Dog, 2/3/4)
    n = sum(k in have for k in FULL_BOARD)
    if not n or n >= len(FULL_BOARD) or "solo" in have or set(FULL_BOARD) - have == {"dog"}:
        return ""                                            # (only the dog missing: its own note says so - one note)
    return f'<div class="drop leanday">🔒 {E(sports_lingo.short_note(n, day))}</div>'


def _dog_note(day, day_picks):
    """🐺 No Dog of the Day (the owner, 9/28): where the dog card would go, on a full board with no dog worth it.
    Only when the dog is the ONLY thing missing - a shorter board's top note already covers it (never two notes)."""
    return ""                                                # (9/30: a Dog of the Day every day - no note)
    have = {p["kind"] for p in day_picks if not p.get("lean")}
    if "solo" in have or set(FULL_BOARD) - have != {"dog"}:
        return ""
    return f'<div class="drop leanday">🐺 {E(sports_lingo.dog_note(day))}</div>'


def _cards(day, day_picks, cards_by_kind, gone=None, after_lock=""):
    """The day's cards in board order, with the no-dog note right after the Lock of the Day. gone: {kind: ms} - a
    graded card's 3 hours are up at that moment, and the page takes it down itself (no waiting on a rebuild)."""
    out = ""
    for k, card, *g in cards_by_kind:                        # (k, card[, when it comes down]) - two night football
        g = g[0] if g else (gone or {}).get(k)               # picks share a kind, so each card carries its own
        if k == "lock":
            card += _dog_note(day, day_picks)
        out += f'<div class="gn" data-gone="{g}">{card}</div>' if g else card
    return after_lock + out                              # 🎯 WE GOT IN EARLY on game day: just ABOVE the Lock of
    #                                                      the Day (the owner, 9/30) - its own box


def gone_ms(p):
    """When a graded card comes down (settled + SHOW_GRADED_H), in epoch ms - None while it's not graded."""
    if p.get("status") not in ("won", "lost", "push"):
        return None
    try:
        t = datetime.strptime(str(p.get("settled"))[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int((t.timestamp() + SHOW_GRADED_H * 3600) * 1000)


BOARD_KEEP_HOUR_PT = 1          # the day's board (graded picks + their reviews) stays up till 1 AM PT the next morning -
                                # later if a pick is still being played (the owner, 9/29: late college football games,
                                # and a late game can be the Lock) - then it goes to the results and the 8 AM note shows


SHOW_GRADED_H = 3               # a graded card stays up with its grade + review for 3 hours, then it's in the results only
#                                 (the owner, 9/29) - so once the day's cards are all done, the 8 AM note shows early


def still_up(p, now_utc):
    """A pick still on the board: not graded yet, or graded less than SHOW_GRADED_H hours ago."""
    if p.get("status") in ("open", "waiting"):
        return True
    try:
        t = datetime.strptime(str(p.get("settled"))[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return False                                        # (graded long ago, before the time was kept)
    return (now_utc - t).total_seconds() < SHOW_GRADED_H * 3600


def board_day(now_pt, picks):
    """The date whose board is up right now: yesterday's till 1 AM PT, or till its last game is graded (before the next
    8 AM board); otherwise today's."""
    d = now_pt.date()
    y = (d - timedelta(days=1)).isoformat()
    if now_pt.hour < BOARD_KEEP_HOUR_PT:
        return y
    if now_pt.hour < 8 and any(p["date"] == y and p.get("status") == "open" for p in picks):   # a game still going
        return y
    return d.isoformat()


DROP_NOTES = []   # (replaced by DROP_PARTS: the note's built fresh each day)


DROP_PARTS = (   # the 8 AM note, built fresh each day: WHEN + the engine WATCHING the lines all night + WHY + a closer
    ["🎯 Picks drop at <b>8 AM PT</b> on game day.", "⏳ Board goes up <b>8 AM PT</b> game day.",
     "🧠 Picks land <b>8 AM PT</b> on game day.", "🕗 <b>8 AM PT</b> on game day — that's when the board drops.",
     "📡 The board hits at <b>8 AM PT</b> on game day.", "👀 <b>8 AM PT</b> game day, the picks go up.",
     "🔔 Picks come out <b>8 AM PT</b> on game day."],
    ["All night the engine's watching the lines move", "The engine's up all night watching every line move",
     "Till then the engine's on the lines all night", "Overnight the engine watches every number move",
     "The engine's glued to the lines all night", "Every line gets watched all night long",
     "We watching the line movement overnight", "We watching the line movement all night"],
    ["— where the money goes, what the injury news does.", "— when a line jumps or a starter sits, we see it first.",
     "— the money and the news move the numbers, then we move.", "— so every big move and late scratch is baked in.",
     "— catching the line moves and the late news before we post.", "— so we never bite on a stale number.",
     "— lines tell on themselves overnight, and we're listening.", "— the late injury news always hits before the first pitch.",
     "— the overnight moves get baked in before we post."],
    ["Sharper number, sharper pick.", "No guessing over here.", "We pick off the best number, not the first one.",
     "Posted means final.", "Patience pays.", "That's how the pros do it.", "Trust the algorithm.",
     "Best number wins.", "We don't chase, we wait.", "Tell the homies.", "Tap in at 8."],
)


def _fold(inner, legs):
    """A parlay card shows its legs in one line - tap to open the full legs (the owner, 9/29: parlays are too long)."""
    mark = {"won": "✅ ", "lost": "❌ ", "push": "➖ "}
    def one(l):
        mk = l.get("mk") or ("ML" if l.get("market") == "ml" else f'{l["line"]:g}' if l.get("market") == "total"
                             else f'{l["line"]:+g}' if l.get("line") is not None else "ML")
        team = ("Over" if l.get("side") == "over" else "Under") if l.get("market") == "total" else l["team"]
        return f'{mark.get(l.get("result"), "")}{E(team)} {E(mk)}'
    n = len(legs)                                          # no list of the legs up top (the owner, 9/29: the card
    return (f'<details class="px"><summary class="pxs"><span class="pxo">▾ Tap to see the {n} legs</span>'   # already
            f'<span class="pxc">▴ Hide the legs</span>{_fold_times(legs)}</summary>{inner}</details>')  # shows them)


def _fold_times(legs, one=False):
    """When the games go (the owner, 9/29: start times, live times, live scores on the cards - a folded parlay too):
    '🕐 First game starts at 5 PM PT' up top; the page swaps it for '🔴 2 LIVE · Next game starts at 7:30 PM PT' /
    '🏁 All games final' as the games go (the owner: say 'first game starts at', not 'next up')."""
    ts = sorted({l["start"][:16] for l in legs if l.get("start") and not l.get("result")})
    if one:                                       # a one-game card (lock, dog): same yellow line (the owner, 9/29: the
        return (f'<div class="pxt" data-one="1">🕐 Game starts at {_time(ts[0])}</div>' if ts   # lock showed no time)
                else '<div class="pxt" data-one="1">🏁 Final</div>')
    if not ts:
        return '<span class="pxt">🏁 All games final</span>'
    return f'<span class="pxt">🕐 First game starts at {_time(ts[0])}</span>'


def _drop_parts(day, parts=None):
    """The pieces for this date. Each piece steps by its own amount every day (plus a drift every lap), so no piece is
    ever the same as the day before's and the combos keep shifting against each other."""
    from datetime import date as _d
    parts = parts or DROP_PARTS
    try:
        d = _d.fromisoformat(str(day)[:10]).toordinal()
    except ValueError:
        d = 0
    steps = (1, 2, 3, 2, 1, 3)
    return [(steps[k % len(steps)] * d + d // len(p) + 7 * k) % len(p) for k, p in enumerate(parts)]


def _drop_note(day):
    """The before-the-board note: when picks drop, that the engine watches the lines move all night, and why - built
    from pieces (1,500+ ways), a different wording every day, no piece repeating from yesterday (the owner, 9/29)."""
    return " ".join(DROP_PARTS[k][i] for k, i in enumerate(_drop_parts(day))).replace(" —", " —", 1)


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

    if kind in ("solo", "night") and pk.get("legs"):      # a one-game day / Monday-Thursday football: the header IS the
        #                                                     pick (STEELERS ML - the owner, 9/30), the 🏈 says football                    # a one-game day: the header IS the pick (BEARS +3.5)
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
    legs = "".join(_leg(leg, tagged=len(pk["legs"]) > 1, review=_rev_text(pk, leg),     # a parlay: each pick in it
                        units=sports.leg_units(pk, leg) if len(pk["legs"]) > 1 else None) for leg in pk["legs"])   # has its units   # graded: the
    #                                                                   after-game review takes the pregame line's spot
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
                      "🔒 Plus money on a LOCK? That's super value. Line makers trippin' fr.",
                      "🔒 The book priced this wrong and we ain't complaining. Plus money LOCK."]) + '</div>'
                  if len(pk["legs"]) == 1 and _tier(pk) == "lock" and pk.get("american", 0) > 0   # one pick at plus money:
                  and pk["status"] == "open" else "")      # a parlay always pays plus - that's no dog (the owner, 9/30)
    return f"""<section class="pk {pk["status"]}" style="--c1:{c1};--c2:{c2}">
  <div class="pk-h"><span class="pk-i">{ICON[kind]}</span><span class="pk-l{' pk-big' if kind == 'solo' else ''}">{label}</span>{TIER_CHIP["value" if kind == "dog" else "strong" if _tier(pk) == "lean" and (pk["legs"][0].get("p") or 0) >= sports.STRONG_LEAN_P else _tier(pk)] if len(pk["legs"]) == 1 else ""}{_chip(pk["status"])}</div>
  <div class="pk-o"><span class="big">{_am(pk["american"])}</span>
    <span class="pay">$100 wins <b>${win:,.0f}</b></span></div>
  {_units_line(sports.units_for(pk), pk["legs"][0].get("team", ""), pk["legs"][0].get("odds")) if len(pk["legs"]) == 1 else ""}
  {f'<div class="stamp-row">{stamp}</div>' if stamp else ""}{book_wrong}{track}{_fold(legs, pk["legs"]) if len(pk["legs"]) > 1 else _fold_times(pk["legs"], one=True) + legs}
</section>"""


def _delayed(l):
    """Past its start time but the feed says it hasn't started (tennis order of play slips all the time)."""
    try:
        st = datetime.strptime(l["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return False
    return l.get("state") == "pre" and datetime.now(timezone.utc) > st + timedelta(minutes=20)


TN_DROP_PARTS = (   # no tennis slate up: WHEN + the engine WATCHING + WHY + a closer, built fresh each day
    ["🎾 Tennis picks drop at <b>8 AM PT</b> on game day.", "🎾 Next tennis slate lands <b>8 AM PT</b>.",
     "🎾 Tennis board's clear — new picks at <b>8 AM PT</b>.", "🎾 <b>8 AM PT</b> on game day: that's when tennis goes up.",
     "🎾 Nothing up right now — tennis drops <b>8 AM PT</b>.", "🎾 The tennis card hits at <b>8 AM PT</b> on game day."],
    ["Till then the engine's watching every line", "The engine's on the tennis lines", "Every match line gets watched",
     "The engine's glued to the numbers", "We watch the lines move"],
    ["— the order of play, the draws, who pulled out.", "— money moves tennis lines quick.",
     "— late withdrawals and injury news hit tennis hard.", "— so the price we post is the right one.",
     "— catching every move before we post."],
    ["We don't guess, we wait.", "Sharper number, sharper pick.", "Patience pays.", "Trust the algorithm.",
     "No bad numbers over here.", "That's how the pros do it."],
)


def _tn_drop_note(day):
    """The no-tennis-slate note: built from pieces, a different wording every day (no piece repeats from yesterday)."""
    return " ".join(TN_DROP_PARTS[k][i] for k, i in enumerate(_drop_parts(day, TN_DROP_PARTS)))


def _battle(sets):
    """Won every set, and at least one went to a tiebreak or 7-5: the other side fought, we still swept."""
    try:
        g = [(int(re.match(r"\d+", a).group()), int(re.match(r"\d+", b).group())) for a, b in sets]
    except (ValueError, AttributeError):
        return False
    return len(g) >= 2 and all(x > y for x, y in g) and any(x == 7 for x, _ in g)


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
    badge = {"won": '<span class="lr won">✅ CASHED</span>', "lost": '<span class="lr lost">❌ MISSED</span>',
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
            out = sports_lingo.say("rc:cover", l["id"], used, who=who, sc="")
        elif l.get("result") == "won" and _battle(sets):          # swept it, but a set went the distance
            opp = stn._say_name(l.get("opp")) or "They"
            out = sports_lingo.say("rc:battle", l["id"], used, who=who, opp=opp, his=his, sets=f"{len(sets)}-0")
        elif l.get("result") == "won" and his == "his" and len(sets) >= 2 and won_sets == len(sets) \
                and sum(int(b[:1]) for _, b in sets) <= 4:         # 💐 a men's straight-sets beatdown: his flowers
            out = sports_lingo.say("rc:flowers", l["id"], used, who=who, sc="")
        elif l.get("result") == "won":
            out = sports_lingo.say("rc:won", l["id"], used, who=who, sc="", his=his)
        elif l.get("result") == "lost":
            out = sports_lingo.say("rc:lost", l["id"], used, who=who, sc="", his=his)
        elif l.get("result") == "void":
            out = "🤷 Voided — no result, no harm."
        recaps[l["id"]] = out
        return out

    def row(l):
        done = l.get("result") in ("won", "lost", "push", "void")
        lines = [x for x in (l.get("breakdown") or []) if isinstance(x, str) and latest_ok(x)]
        if done:                                             # it's over: no "we gon' see" in the pregame read
            lines = [PENDING_TALK.sub("", x).rstrip(" —") or x for x in lines]
        tag, lines = (lines[0], lines[1:]) if len(lines) > 1 else ("", lines)   # the headline line up top, like the
        bd = "".join(f"<p>{E(pct_ok(x))}</p>" for x in lines)                        # main board (the owner, 9/29) - tap for the rest
        rv = ""                                              # graded: the review takes the headline line's spot
        if done and recap(l):
            tag = f"📝 {recap(l)}"
        return f"""<div class="leg {l['result'] or ''}">
  <div class="lt"><span class="lgb">🎾 {"Women's Tennis" if stn.tour_of(l) == "wta" else "Men's Tennis"} · {E(l['tourney'])}</span>{badge.get(l['result']) or f'<span class="tm{" dly" if _delayed(l) else ""}" data-start="{E(l["start"])}" data-gid="tennis:{E(l.get("match", ""))}" data-side="{E(str(l.get("side", "")))}" data-mk="{E(l.get("market") or "ml")}">{"⏳ DELAYED" if _delayed(l) else "Starts at " + _time(l["start"])}</span>'}</div>
  <div class="lm"><span class="pick">{E(l['player'])} <em>{f"{l['hcp']:+g} games" if l.get("market") == "spread" else "ML"}</em></span><span class="od">{_am(l['odds'])}</span></div>
  <div class="ls">vs {E(l['opp'])} · {E(l['round'])} · {E({"hard": "Hard court", "clay": "Clay", "grass": "Grass"}.get(l['surface'], l['surface']))}</div>
  {f'<div class="why rvy">{E(pct_ok(tag))}</div>' if tag else ""}
  {f'<details class="bd"><summary>🔍 {"Pregame breakdown" if done else "Full breakdown"}</summary><div class="bd-s">{bd}</div></details>' if bd else ""}
  {f'<div class="fin">Final: {E(", ".join(f"{a}-{b}" for a, b in ours(l)) or l["score"])}</div>' if l.get("score") else ""}
  {rv}
</div>"""
    PAR_TITLE = {"atp": "MEN'S TENNIS PARLAY", "wta": "WOMEN'S TENNIS PARLAY", "mixed": "TENNIS PARLAY OF THE DAY"}

    def par_card(key, par, legs):
        stamp = {"won": '<div class="stamp won">CASHED</div>', "lost": '<div class="stamp lost">LOST</div>'}.get(par["status"], "")
        return f"""<section class="pk {par['status']}" style="--c1:#c6f000;--c2:#1fd17a">
  <div class="pk-h"><span class="pk-i">🎾</span><span class="pk-l">{PAR_TITLE[key].replace("PARLAY", f'{len(par.get("legs") or [])}-LEG PARLAY')}</span>{_chip(par["status"])}</div>
  <div class="pk-o"><span class="big">{_am(par['american'])}</span><span class="pay">$100 wins <b>${100 * (par['dec'] - 1):,.0f}</b></span></div>
  {f'<div class="stamp-row">{stamp}</div>' if stamp else ""}{_fold("".join(row(legs[i]) for i in par["legs"] if i in legs), [{"team": legs[i]["player"], "result": legs[i].get("result"), "mk": "ML" if legs[i].get("market") != "spread" else f'{legs[i]["hcp"]:+g} games'} for i in par["legs"] if i in legs])}
</section>"""

    def block(s):                                        # (kept for a single slate; the card groups by tour below)
        return tour_blocks([s])

    def tour_blocks(sl_):
        """ONE section per tour across every slate on the card (the owner, 9/28: no men's / women's / men's again):
        MEN'S TENNIS (all picks, by start, each with its day) -> men's parlays -> WOMEN'S TENNIS -> women's parlays."""
        out = ""
        many = len(sl_) > 1
        dname = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%a")
        for t, title in (("atp", "MEN'S TENNIS"), ("wta", "WOMEN'S TENNIS")):
            ls = sorted(((s_["date"], l) for s_ in sl_ for l in s_["picks"] if stn.tour_of(l) == t),
                        key=lambda x: (x[0], x[1].get("start") or ""))
            if ls:
                out += (f'<section class="pk" style="--c1:#c6f000;--c2:#1fd17a"><div class="pk-h"><span class="pk-i">🎾</span>'
                        f'<span class="pk-l">{title}</span></div>'
                        + "".join((f'<div class="tn-day">{dname(d).upper()}</div>' if many and (i == 0 or ls[i - 1][0] != d) else "")
                                  + row(l) for i, (d, l) in enumerate(ls)) + "</section>")
            for s_ in sl_:
                pars = dict(stn.parlays_of(s_))
                if t in pars:
                    card = par_card(t, pars[t], {l["id"]: l for l in s_["picks"]})
                    if many:                             # which day's parlay it is
                        card = card.replace('-LEG PARLAY</span>', f'-LEG PARLAY · {dname(s_["date"]).upper()}</span>', 1)
                    out += card
        return out                                       # (an old combined parlay stays off the card - it's in the results)
    # the owner, 9/28: graded picks stay up - CASHED / MISSED with their review - until the NEXT slate posts (8am PT);
    # then the old one goes to the results. (An older slate with a match still going stays up too.)
    live = lambda x: any(l.get("result") is None for l in x["picks"]) or any(p["status"] == "open" for _, p in stn.parlays_of(x))
    # (like the main board: a slate stays up through its own day, graded picks and all, till 1 AM PT)
    now_pt = datetime.now(PT)
    bd = board_day(now_pt, [{"date": x["date"], "status": "open" if live(x) else "done"} for x in slates])
    up = lambda x: x["date"] >= bd                        # (same clock as the main board: till 1 AM / last match graded)
    shown = [x for x in slates if up(x) or (live(x) and x["date"] >= (now_pt.date() - timedelta(days=1)).isoformat())]
    what = _tn_count(shown, stn.tour_of)
    body = tour_blocks(shown) if shown else f'<div class="nopick">{_tn_drop_note(now_pt.date().isoformat())}</div>'
    m_, w_, x_ = r["atp"], r["wta"], r["mixed"]
    pars = (f"parlays: men's {m_['p_won']}-{m_['p_lost']} · women's {w_['p_won']}-{w_['p_lost']}"
            + (f" · old mixed {x_['p_won']}-{x_['p_lost']}" if x_["p_won"] + x_["p_lost"] else ""))
    return f"""<details class="tn"><summary><span class="tn-t">🎾 TENNIS BONUS</span>
<span class="tn-s">{what} · men's {m_['won']}-{m_['lost']} · women's {w_['won']}-{w_['lost']} · tap to open</span></summary>
<div class="tn-b">{body}</div></details>"""


def _jl(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


LEG_REVIEWS = {}   # (date, "game|side|market") -> that pick's review (filled by _history, shown on today's graded cards)


def _rev_text(pk, leg):
    """A graded pick's after-game review ("" before it's graded)."""
    if leg.get("result") not in ("won", "lost", "push"):
        return ""
    return LEG_REVIEWS.get((pk.get("date", ""), f'{leg.get("game_id")}|{leg.get("side")}|{leg.get("market")}')) or ""



def _tn_count(shown, tour_of):
    """The tennis card's count: TODAY's slate (the owner, 9/30: "9 men's + 4 women's" was two days added together) -
    plus a yesterday match that's still going (moved / suspended) said on its own."""
    last = max((x["date"] for x in shown), default=None)
    cur = [l for x in shown if x["date"] == last for l in x["picks"]]
    nm, nw = sum(tour_of(l) == "atp" for l in cur), sum(tour_of(l) == "wta" for l in cur)
    held = sum(l.get("result") is None for x in shown if x["date"] != last for l in x["picks"])
    if not nm + nw:
        return "new picks at 8 AM PT"
    return f"{nm} men's + {nw} women's" + (f" · {held} from yesterday still going" if held else "")


_GAMES_ = [{}]                   # the games file for the reviews' box-score lookups (set once per build)


def _history(picks):
    """📜 PAST RESULTS: tap open any sport and see every pick that won or lost, newest first."""
    import sports
    ok = {"won": "✅", "lost": "❌", "push": "➖"}
    kinds = {"lock": "Lock of the Day", "dog": "Dog of the Day", "two": "2-Leg", "three": "3-Leg", "four": "4-Leg",
             "eight": "8-Leg", "solo": "One-Game Pick", "night": "Night Football"}

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

    def rows(items):                                         # every game with its review right under it - no tap
        def one(x):                                          # (the owner, 9/30)
            head = (f'<span class="hd">{day(x[0])}</span><span class="hw">{ok.get(x[1], "")}</span>'
                    f'<span class="hp">{E(x[2])}<small>{E(x[3])}</small></span>')
            if len(x) > 4 and x[4]:
                return (f'<div class="hx hxo {x[1]}"><div class="hr {x[1]}">{head}</div>'
                        f'<div class="hrv">📝 {E(x[4])}</div></div>')
            return f'<div class="hr {x[1]}">{head}</div>'
        return "".join(one(x) for x in items)

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

    COMEBACK = {"nfl": 10, "ncaaf": 14, "nba": 12, "ncaab": 10, "mlb": 3, "nhl": 2}   # down this much = a comeback
    LUCKY = {"nfl": 1, "ncaaf": 1, "nba": 1.5, "ncaab": 1.5, "mlb": 0.5, "nhl": 0.5}    # covered by this or less = lucky

    def swing(l):
        """(final margin, our worst deficit, our biggest lead) at the end of each period, from our side - or None when the
        game's period scores weren't kept."""
        f = l.get("flow") or {}
        try:
            h = [int(x) for x in str(f.get("h") or "").split(",") if x != ""]
            a = [int(x) for x in str(f.get("a") or "").split(",") if x != ""]
        except ValueError:
            return None
        if len(h) < 2 or len(h) != len(a):
            return None
        us, them = (h, a) if l.get("side") == "home" else (a, h)
        adj = 0                                              # (the real scoreboard: "down 10" means down 10)
        m, marg = 0, []
        for x, y in zip(us[:-1], them[:-1]):                 # the score after each period (not the final)
            m += x - y
            marg.append(m + adj)
        if not marg:
            return None
        return (sum(us) - sum(them) + adj, max(0, -min(marg)), max(0, max(marg)))

    def _star(l):
        try:
            import sports_roster as sr
            g = _GAMES_[0].get(l.get("game_id")) or {}
            return sr.star_night(l.get("league"), l.get("game_id"), g.get(l.get("side")), l.get("start") or g.get("start", ""))
        except Exception:                                    # noqa: BLE001
            return None

    def rev_leg(l, r, date, p=None, lean=False):
        """The review for one game pick: blowout / close / confident-and-folded / fav / dog / spread / total."""
        lg, mg = l.get("league"), margin(l.get("score"), l.get("team"))
        flow, xtra = swing(l), {}
        cover = None if mg is None or l.get("line") is None else mg + l["line"]   # how much we covered by
        t_, o_ = _the(l["team"], lg), _the(l.get("opp", "them"), lg)
        kind = "spread" if l.get("market") == "spread" else "dog" if (l.get("odds") or 0) > 0 else "fav"
        x = f'{l["line"]:+g}' if l.get("line") is not None else ""
        if l.get("market") == "total":
            kind, t_, x = "total", ("the over" if l.get("side") == "over" else "the under"), ""   # (no numbers in a review)
        elif flow and flow[1] >= COMEBACK.get(lg, 99) and r == "won":   # down big and came back (how we won matters)
            kind, xtra = "comeback", {"d": flow[1]}
        elif flow and flow[2] >= COMEBACK.get(lg, 99) and r == "lost":  # up big and blew it
            kind, xtra = "collapse", {"d": flow[2]}
        elif r == "won" and l.get("market") == "spread" and cover is not None and 0 < cover <= LUCKY.get(lg, 0):
            kind = "lucky"                                   # covered by a hair: we got lucky - a win is a win
        elif l.get("public") == "fade":                   # 🤡 we faded the public: that's the story, win or lose
            kind = "fade"
        elif mg is not None and abs(mg) >= BIG.get(lg, 99) and (mg > 0) == (r == "won"):
            kind = "big"
        elif mg is not None and abs(mg) <= CLOSE.get(lg, 0) and kind != "spread":
            kind = "close"
        elif r == "lost" and (p or l.get("p") or 0) >= 0.6:
            kind = "conf"
        if r == "won" and l.get("market") != "total" and kind not in ("comeback",):   # 💐 one of ours went off: his
            star = _star(l)                                   # flowers (the owner's words, 9/30)
            if star:
                kind, xtra = "flowers", {"star": star}
        if r == "lost" and l.get("market") == "spread" and (l.get("line") or 0) < 0 and mg is not None and mg < 0 \
                and kind not in ("collapse", "fade"):          # laid the points and lost the game outright: say so,
            kind, xtra = "outright", {}                     # (the owner, 9/29 - never just "couldn't cover")
        return later(date, f'{l.get("game_id")}|{l.get("side")}|{l.get("market")}', kind, r, lean, t=t_, o=o_, x=x, **xtra)

    def box(title, items, head="", leans=()):
        if not items and not leans:
            return ""
        w, l_ = sum(x[1] == "won" for x in items), sum(x[1] == "lost" for x in items)   # (the leans never count here)
        lw, ll_ = sum(x[1] == "won" for x in leans), sum(x[1] == "lost" for x in leans)
        items = sorted(list(items) + list(leans), key=lambda x: x[0], reverse=True)
        tot = "by sport ▾" if head else f'{w}-{l_}{f" · {w / (w + l_):.0%}" if w + l_ else ""}'   # (live: never lumped)
        tot += f" · leans {lw}-{ll_}" if lw + ll_ else ""
        return (f'<details class="hs"><summary><b>{title}</b><span>{tot}</span></summary>{head}{rows(items)}</details>')

    # our record, by sport: every leg we posted (a team we're on in two picks the same day shows once, with both cards)
    legs, lean_legs = {}, {}
    for p in picks:
        if not sports.in_record(p) or p["status"] not in ("won", "lost", "push", "open"):
            continue
        for l in p["legs"]:
            if l.get("result") not in ("won", "lost", "push"):
                continue
            if l.get("tier") == "lean" and p["date"] < sports.LEANS_COUNT_FROM:   # a lean leg: in its sport (the owner,
                k = (p["date"], l["game_id"], l["side"], l.get("market"))   # hockey from yesterday's not in here"),
                e = lean_legs.setdefault(k, {"l": l, "date": p["date"], "cards": []})   # marked LEAN, never in its record
                e["cards"].append(kinds.get(p["kind"], p["kind"]))
                continue
            k = (p["date"], l["game_id"], l["side"], l.get("market"))
            e = legs.setdefault(k, {"l": l, "date": p["date"], "cards": [], "lean": True})
            e["cards"].append(kinds.get(p["kind"], p["kind"]))
            e["lean"] = e["lean"] and bool(p.get("lean") or l.get("tier") == "lean")   # (a lean anywhere it's posted)
    by = {}
    for e in legs.values():
        l = e["l"]
        by.setdefault(l["league"], []).append(
            (e["date"], l["result"], f'{"🟡 LEAN · " if e["lean"] else ""}{bet(l)} ({_am(l["odds"])})', f' · {" + ".join(dict.fromkeys(e["cards"]))}'
             + (f' · {l["score"]}' if l.get("score") else ""), rev_leg(l, l["result"], e["date"])))
    for p in picks:                                          # a lean on its own (not in our record) shows in its sport too
        if sports.in_record(p) or p.get("status") not in ("won", "lost") or len(p.get("legs") or []) != 1:
            continue
        l = p["legs"][0]
        lean_legs.setdefault((p["date"], l.get("game_id"), l.get("side"), l.get("market")),
                             {"l": {**l, "result": l.get("result") or p["status"]}, "date": p["date"],
                              "cards": [kinds.get(p["kind"], p["kind"])]})
    by_lean = {}
    for k, e in lean_legs.items():
        l = e["l"]
        if k in legs:
            continue                                         # (the same pick counted as ours elsewhere: once)
        by_lean.setdefault(l["league"], []).append(
            (e["date"], l["result"], f'🟡 LEAN · {bet(l)} ({_am(l["odds"])})',
             f' · {" + ".join(dict.fromkeys(e["cards"]))}' + (f' · {l["score"]}' if l.get("score") else ""),
             rev_leg(l, l["result"], e["date"], lean=True)))
    # the parlays, as tickets
    tix = [(p["date"], p["status"], f'{kinds.get(p["kind"], p["kind"])} ({_am(p["american"])})',
            " · " + ", ".join(bet(l) + ("" if l.get("result") in (None, "won") else " ❌") for l in p["legs"]),
            later(p["date"], p["kind"], "parlay", p["status"],
                  x=" and ".join(bet(l) if l.get("market") == "total" else _the(l["team"], l["league"])
                                 for l in p["legs"] if l.get("result") == "lost")))
           for p in picks if sports.in_record(p) and len(p["legs"]) > 1 and p["status"] in ("won", "lost")]
    # their own records
    lean = [(p["date"], p["status"], f'{bet(p["legs"][0])} ({_am(p["legs"][0]["odds"])})',
             f' · {sd.LEAGUES.get(p["legs"][0]["league"], ("", "", ""))[2]}'
             + (f' · {p["legs"][0]["score"]}' if p["legs"][0].get("score") else ""),
             rev_leg(p["legs"][0], p["status"], p["date"], lean=True))              # a lean: no hype, win or lose
            for p in picks if not sports.in_record(p) and p["status"] in ("won", "lost") and p.get("legs")]
    live = ((_jl(os.path.join(sd.DATA, "live_log.json"), {}) or {}).get("plays") or {}).values()

    def rev_live(e):
        mg = margin(e.get("score_at_post"), e.get("team"))
        lg = e.get("league")
        if lg == "tennis":                                   # 🎾 tennis words: ahead / behind in sets, then games
            t = e.get("tennis") or {}
            me_, them_ = (t.get("sets") or [0, 0])[:2] if len(t.get("sets") or []) >= 2 else (0, 0)
            g1, g2 = (t.get("games") or [0, 0])[:2] if len(t.get("games") or []) >= 2 else (0, 0)
            ahead = me_ > them_ or (me_ == them_ and g1 > g2)
            wta = e.get("tour") == "wta"
            return later(e.get("date", ""), f'live|{e.get("team")}|{e.get("posted")}',
                         "tlive_up" if ahead else "tlive_back", e["result"], t=e.get("team", ""),
                         o=e.get("opp") or "them", pr="she" if wta else "he", pro="her" if wta else "him",
                         pos="her" if wta else "his")
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
    lv_keys = [live_sport_key(e) for e in live if e.get("result") in ("won", "lost")]   # (same order as lv)
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
        LEG_REVIEWS[c["key"]] = c["text"]                   # the same review shows on the graded card up top
    done = lambda items: [x[:4] + (x[4]["text"],) for x in items]
    out = "".join(box(f'{sd.LEAGUES[lg][3]} {sd.LEAGUES[lg][2]}', done(by.get(lg, [])), leans=done(by_lean.get(lg, [])))
                  for lg in sd.LEAGUES)
    # (no parlay record - the owner, 9/28: a parlay's picks each count on their own, in their sport)
    lv_done = done(lv)                                       # the live bets: one box per sport (the grades' live
    own = ("".join(box(f"📡 {k}", [x for x, kk in zip(lv_done, lv_keys) if kk == k])   # box opens each one by name)
                   for k in dict.fromkeys(lv_keys)) + box("🟡 Leans", done(lean)) + box("🎾 Men's Tennis", done(tn["atp"]))
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
async function alertNow(e) {
  let m = {};
  try { m = (e && e.data && e.data.json()) || {}; } catch (x) { m = {}; }   // the alert rides in the push itself
  if (!m.title) try {                                     // (an old-style empty push: ask the Worker - it only answers
    if (!API) throw new Error("no worker");               // with an alert under 10 minutes old)
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
    renotify: !m.id,                                      // the same alert twice (a phone signed up twice): the 2nd
    //                                                       quietly replaces the 1st - never two rings (the owner, 9/30)
    icon: "icon-512.png?v=8",
    badge: "icon-512.png?v=8",
    data: { url: m.url && m.url.indexOf(DASH) === 0 ? m.url : DASH },
  });
}
self.addEventListener("push", (e) => e.waitUntil(alertNow(e)));
self.addEventListener("pushsubscriptionchange", (e) => e.waitUntil((async () => {   // the phone swapped its sign-up:
  const old = e.oldSubscription;                          // drop the old one so alerts don't come in twice
  if (old && API) await fetch(API + "/unsubscribe", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint: old.endpoint }) }).catch(() => {});
  const s = e.newSubscription;
  if (s && API) await fetch(API + "/subscribe", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(s.toJSON()) }).catch(() => {});
})()));
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
    import sports
    WHY_USED.clear()
    _GAMES_[0] = games or {}
    try:                                                     # ⏰ which of today's picks we already got in early on
        import sports_early
        EARLY_IN.clear()
        EARLY_IN.update({(e["game_id"], e["side"]): e["odds"] for e in sports_early.load().get("picks") or []
                         if e.get("odds") and e.get("result") is None})
    except Exception as e:                                   # noqa: BLE001
        print(f"early-in map failed: {e}")
    now = datetime.now(PT)
    today = board_day(now, picks)                           # (yesterday's board till 1 AM / its last game is graded)
    order = list(LOOK)
    todays = sorted((p for p in picks if p["date"] == today), key=lambda p: (order.index(p["kind"]) if p["kind"] in order else 99, p.get("posted") or ""))
    # the owner, 9/29: every card stays up till it's graded, then 3 more hours with CASHED/MISSED and its review; then
    # it's in the results only. Nothing left up: the "picks drop 8 AM PT" note shows right away (the results live below)
    now_utc = datetime.now(timezone.utc)
    recent = {(now.date() - timedelta(days=1)).isoformat(), now.date().isoformat(), today}
    todays = [p for p in sorted((p for p in picks if p["date"] in recent),
                                key=lambda p: (p["date"], order.index(p["kind"]) if p["kind"] in order else 99,
                                               p.get("posted") or "")) if still_up(p, now_utc)]
    todays = sorted(todays, key=lambda p: (order.index(p["kind"]) if p["kind"] in order else 99, p["date"]))   # Lock on top
    if todays:
        today = max(p["date"] for p in todays)
    active = list(todays)
    board_date = datetime.strptime(today, "%Y-%m-%d").strftime("%A, %B %-d")
    ask_url = _ask_url()
    ask_note = ("Tap in! Ask me whatever the fuck. No stupid shit though. Ain't nobody got time for that." if ask_url else
                "Ask about any game — who wins, spreads, first half. Heads up: these <b>ain’t our picks</b> and don’t count toward our record.")
    ask_btn = '<button id="askgo" type="button">Ask 🧠</button>' if ask_url else ""
    bell = ('<div class="bell"><button id="bellb" type="button" hidden>🔔 Get live bet alerts</button>'   # 🔔 Web Push
            '<div class="bell-n" id="belln" hidden></div></div>') if ask_url else ""
    api = ask_url.rstrip("/")
    drop = f'<div class="drop">{_drop_note(today)}</div>'
    done_today = ('<div class="drop">✅ Everything on today\'s board is graded — scroll down to <b>THE RESULTS</b>. '
                  'Tomorrow\'s card drops at <b>8 AM PT</b> on game day — the engine watches the lines and the news overnight.</div>')
    hist = _history(picks)                                  # (first: it writes the reviews the graded cards show)
    try:                                                     # 🥊 a friend's ticket vs the engine's (the owner, 9/30)
        import sports_challenge as sch
        challenge = sch.html(sch._load(), E)
    except Exception as e:                                   # noqa: BLE001 - the page never waits on it
        print(f"challenge box failed: {e}")
        challenge = ""
    try:                                                     # ⏰ early value plays (the owner, 9/30)
        import sports_early
        eu = lambda u, k="", o=None: _units_line(u, k, o, early=True)
        early = sports_early.html(sports_early.load(), E, show_units=eu)
        early_today = sports_early.gameday_html(sports_early.load(), games, E, show_units=eu)
    except Exception as e:                                   # noqa: BLE001
        print(f"early box failed: {e}")
        early = early_today = ""
    board = _cards(today, todays, [(p["kind"], _pick_card(p["kind"], p), gone_ms(p)) for p in active],
                   after_lock=early_today) if active else early_today + drop
    if active and all(gone_ms(p) for p in active):          # every card graded: the 8 AM note waits, ready to show
        board += f'<template id="dropnote">{drop}</template>'   # the moment the last one's 3 hours are up
    if todays and all(p.get("lean") for p in todays if p["status"] != "waiting") and any(p["status"] != "waiting" for p in todays):
        board = _lean_note(today) + board                    # a leans-only day says so up top
    elif active:
        board = _short_note(today, todays) + board           # a short board says so too

    tmr = datetime.strptime(today, "%Y-%m-%d").date() + timedelta(days=1)
    tomorrows = {p["kind"]: p for p in picks if p["date"] == tmr.isoformat()}
    tmr_real = [p for p in tomorrows.values() if p["status"] != "waiting"]
    tomorrow = (f'<div class="sec"><h2><i>●</i> TOMORROW\'S BOARD</h2><span>{tmr:%A, %B %-d}</span></div>'
                + (_lean_note(tmr.isoformat()) if tmr_real and all(p.get("lean") for p in tmr_real)
                   else _short_note(tmr.isoformat(), list(tomorrows.values())))
                + _cards(tmr.isoformat(), list(tomorrows.values()), [(k, _pick_card(k, tomorrows[k])) for k in LOOK if k in tomorrows])) if tomorrows else ""

    graded_all = [p for p in picks if p["status"] in ("won", "lost", "push")]
    done = [p for p in graded_all if sports.in_record(p)]         # our record (leans keep their own - the owner, 9/30)
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
            live = json.load(f)
    except (OSError, ValueError):
        pass
    live = live.get("plays", {})
    # today's live bets only (a new day starts clean - old ones live on in the records): what they were, did they cash
    days_ = live_days(now)
    tonight_ = [e for e in live.values() if e.get("date") in days_]
    lrows = sorted((e for e in tonight_ if e.get("result") is None), key=lambda e: e["posted"], reverse=True)   # still
    #   going only (the owner, 9/30): the second a live bet's graded it clears into THE RESULTS, under its sport
    badge_ = {"won": '<span class="lr won">✅ CASHED</span>', "lost": '<span class="lr lost">❌ MISSED</span>'}
    def pending_(pid, e):                                    # still going: the live score shows right under it
        gid, side = pid.rsplit(":", 1) if pid.count(":") >= 2 else (pid, "")
        start = str(e.get("posted") or "")
        start = start if start.endswith("Z") and "T" in start else ""
        return (f'<span class="tm" data-gid="{E(gid)}" data-start="{E(start)}" data-side="{E(side)}">⏳ STILL GOING</span>'
                if start else '<span class="tm">⏳ STILL GOING</span>')
    stories = live_stories(tonight_)                         # no two bets share a line - oldest first, graded ones
    #                                                        too (their lines stay spoken for the night)
    try:                                                     # owning our mistakes, right on the bet itself
        with open(os.path.join(sd.DATA, "notes.json")) as f:
            owned = {n["live"]: n["text"] for n in json.load(f) if n.get("live")}
    except (OSError, ValueError, KeyError):
        owned = {}
    pid_of = {id(e): pid for pid, e in live.items()}
    live_list = ("" if not lrows else
                 '<section class="pk" style="--c1:#22d3ee;--c2:#2f8bff;margin-top:14px"><div class="pk-h"><span class="pk-i">📡</span>'
                 '<span class="pk-l tn8">TONIGHT\'S LIVE BETS</span><span class="chip in">WE\'RE IN</span></div>'
                 + (LIVE_NO_UNITS if UNITS_ON else "") + "".join(
                     f'<div class="leg {e.get("result") or ""}" data-pid="{E(pid_of.get(id(e), ""))}"><div class="lt"><span class="lgb">{_live_icon(e)} '
                     f'{E(_live_sport(e))}{" · 🔁 DOUBLE DOWN" if e.get("double_down") else ""}</span>'
                     f'{badge_.get(e.get("result")) or pending_(pid_of.get(id(e), ""), e)}</div>'
                     f'<div class="lm"><span class="pick">{E(e["team"])} <em>ML</em></span><span class="od">{_am(e["odds"])}</span></div>'
                     f'<div class="ls">{E(stories[id(e)])}</div>'
                     f'{"<div class=own>" + E(owned[pid_of[id(e)]]) + "</div>" if pid_of.get(id(e)) in owned else ""}</div>'
                     for e in lrows) + "</section>")
    # the engine's grades: locks, value, leans and live - each graded on its own, never lumped into one number
    def grade(name, c1, c2, rows, today_rows, hs="", by_sport=False):
        w_, l_ = sum(r == "won" for r in rows), sum(r == "lost" for r in rows)
        tap = f' tap" data-hs="{E(hs)}' if hs and w_ + l_ else ""                  # tap: its past games open right here
        if by_sport is not False:                            # the owner, 9/29: never one lumped-together number -
            if not by_sport:                                 # line per sport, behind one tap: box -> sports -> bets
                return (f'<div class="rc gr" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{name}</div>'
                        f'<div class="rc-p" style="margin-top:8px">no results yet</div></div>')
            return (f'<div class="rc gr rc-wide lvbox" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{name}</div>'
                    f'<div class="rc-p lvt">Tap a sport to see full results ▾</div>{by_sport}</div>')
        return (f'<div class="rc gr{tap}" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{name}</div><div class="rc-r">{w_} won · {l_} lost</div>'
                f'<div class="rc-p">{f"{w_ / (w_ + l_):.0%}" if w_ + l_ else "no results yet"}</div></div>')
    # every PICK we posted, graded once (a parlay's picks each count on their own - no parlay record, the owner 9/28;
    # a team we're on twice the same day counts once), by its label: lock / value / lean (leans count from 9/29 on)
    calls = {}
    rank = {"lock": 3, "value": 2, "lean": 1, "ou": 0}
    for p in sorted(picks, key=lambda p: p.get("posted") or ""):
        for l in p["legs"]:                                  # (leans too - they get their own record below)
            if l.get("result") in ("won", "lost"):
                if l.get("market") == "total":
                    t = "ou"
                elif p.get("lean"):
                    t = "lean"
                elif p["kind"] == "lock":
                    t = "lock"
                elif p["kind"] == "dog":                     # the Dog of the Day is a value play (the owner, 9/30)
                    t = "value"
                elif l.get("tier") in ("lock", "value", "lean"):
                    t = l["tier"]
                else:                                    # older picks: the rule back then (minus money = lock)
                    t = "lock" if l["odds"] < 0 else "value"
                key = (p["date"], l["game_id"], l["side"])
                if rank.get(calls.get(key, ("",))[0], -1) < rank[t]:
                    calls[key] = (t, l["result"], p["date"])
    by_tier = {t: [(r, d) for tt, r, d in calls.values() if tt == t] for t in ("lock", "value", "lean")}
    ours = [c for c in calls.values() if c[0] != "lean" or c[2] >= sports.LEANS_COUNT_FROM]   # OVERALL: every pick we
    ow = sum(r == "won" for _, r, _ in ours)                # made, once each - leans too (the owner, 10/1)
    ol = sum(r == "lost" for _, r, _ in ours)
    tw = sum(r == "won" for _, r, d in ours if d == today)
    tl = sum(r == "lost" for _, r, d in ours if d == today)
    overall = (f'<div class="ovr"><div class="ovr-t">📊 OVERALL RECORD</div><div class="ovr-r">{ow}-{ol}</div>'
               f'<div class="ovr-p">{f"{ow} won · {ol} lost · {ow / (ow + ol):.0%}" if ow + ol else "no results yet"}</div>'
               f'{f"<div class=ovr-s>today {tw}-{tl}</div>" if tw + tl else ""}</div>')
    overall += units_box(picks, today) if UNITS_ON else ""
    lrs = sorted((e for e in live.values() if e.get("result") in ("won", "lost")), key=lambda e: e.get("posted", ""))
    RECORDS.clear()                                          # the same numbers the page shows, for the AI's data sheet
    def wlt(w, l):
        return f"{w}-{l}"
    RECORDS.update({"overall": wlt(ow, ol), "today": wlt(tw, tl),
                    "locks": wlt(sum(r == "won" for r, _ in by_tier["lock"]), sum(r == "lost" for r, _ in by_tier["lock"])),
                    "value": wlt(sum(r == "won" for r, _ in by_tier["value"]), sum(r == "lost" for r, _ in by_tier["value"])),
                    "leans (own record, not ours)": wlt(sum(r == "won" for r, _ in by_tier["lean"]), sum(r == "lost" for r, _ in by_tier["lean"])),
                    "live plus money (own record, not ours)": wlt(sum(e["result"] == "won" for e in lrs), sum(e["result"] == "lost" for e in lrs))})
    grades = "".join(grade(*TIER_LOOK[t], [r for r, _ in by_tier[t]], [r for r, d in by_tier[t] if d == today])
                     for t in ("lock", "value"))
    lotd = sorted((p for p in graded_all if p["kind"] == "lock"), key=lambda p: (p["date"], p.get("posted") or ""))
    dotd = sorted((p for p in graded_all if p["kind"] == "dog"), key=lambda p: (p["date"], p.get("posted") or ""))
    grades = (grade("🔒 LOCK OF THE DAY", "#22e39a", "#ffc233", [p["status"] for p in lotd], [p["status"] for p in lotd if p["date"] == today])
              + grade("🐺 DOG OF THE DAY", "#ff3b3b", "#ff8a00", [p["status"] for p in dotd], [p["status"] for p in dotd if p["date"] == today])
              + grades)
    # their own categories, never in our record: live bets and leans
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
        return grade(name, "#c6f000", "#1fd17a", [r for r, _ in rows_], [r for r, dd in rows_ if dd == today],
                     hs="🎾 Men's Tennis" if t == "atp" else "🎾 Women's Tennis")   # (no parlay
        #                                                        record - the owner, 9/28)
    others = (grade("📡 LIVE PLUS MONEY", "#22d3ee", "#2f8bff", [e["result"] for e in lrs], [e["result"] for e in lrs if e.get("date") == today],
                    by_sport=_live_by_sport(lrs))
              + (grade(*TIER_LOOK["lean"], [r for r, _ in by_tier["lean"]], [r for r, d in by_tier["lean"] if d == today],
                       hs="🟡 Leans") if by_tier["lean"] else "")     # leans: their own record (the owner, 9/30)
              + tn_box("🎾 MEN'S TENNIS", "atp") + tn_box("🎾 WOMEN'S TENNIS", "wta"))
    for t, label in (("atp", "men's tennis"), ("wta", "women's tennis")):
        RECORDS[f"{label} (own record, not ours)"] = wlt(sum(r == 'won' for r, _ in tn_rows[t]), sum(r == 'lost' for r, _ in tn_rows[t]))

    # by sport: just our hit rate on the board - locks, value, leans (live bets are their own category; the 8-leg stays out)
    groups = [("🏈 NFL", ("nfl",)), ("🏈 College Football", ("ncaaf",)), ("🏀 NBA", ("nba",)),
              ("🏀 College Basketball", ("ncaab",)), ("⚾ Baseball", ("mlb",)), ("🏒 Hockey", ("nhl",))]
    seen_ = {}                                               # a team we're on in two picks the same day counts once
    for p in picks:
        if sports.in_record(p):                            # our daily record (never leans, never live bets)
            for l in p["legs"]:
                if l.get("result") in ("won", "lost") and (l.get("tier") != "lean" or p["date"] >= sports.LEANS_COUNT_FROM):
                    seen_[(p["date"], l["game_id"], l["side"])] = (l["league"], l["result"])
    res = list(seen_.values())
    lean_ = {}                                               # 🟡 the leans in each sport (the owner, 10/1: "leans or not,
    for p in picks:                                          # put everything in the correct sport") - shown, never in
        for l in p.get("legs") or []:                        # the sport's record
            lr = l.get("result") or (p.get("status") if len(p.get("legs") or []) == 1 else None)
            if lr in ("won", "lost") and not sports.in_record(p) and l.get("league"):   # (only leans before 9/29 now)
                k = (p["date"], l.get("game_id"), l.get("side"))
                if k not in seen_:
                    lean_[k] = (l["league"], lr)
    res += [(f"tennis_{t}", r) for t, r, _ in tennis_.values()]   # 🎾 men's and women's apart (a match counts once)
    tn_groups = [("🎾 Men's Tennis", ("tennis_atp",)), ("🎾 Women's Tennis", ("tennis_wta",))]
    chips = []
    for name, lgs in groups + tn_groups:
        rr = [r for lg, r in res if lg in lgs]
        w_, n_ = sum(r == "won" for r in rr), len(rr)
        hue = "#fff" if not n_ else "#22e39a" if w_ / n_ >= 0.55 else "#ffc233" if w_ / n_ >= 0.45 else "#ff5a5a"
        hs = {"tennis_atp": "🎾 Men's Tennis", "tennis_wta": "🎾 Women's Tennis"}.get(lgs[0]) or \
            f"{sd.LEAGUES[lgs[0]][3]} {sd.LEAGUES[lgs[0]][2]}"          # the matching Past Results list (tap = open it)
        lr_ = [r for lg, r in lean_.values() if lg in lgs]
        lw_ = sum(r == "won" for r in lr_)
        ltxt = f" · leans {lw_}-{len(lr_) - lw_}" if lr_ else ""
        chips.append(f'<div class="spc{" tap" if n_ or lr_ else ""}" data-hs="{E(hs)}"><span><b>{name}</b>'
                     f'<small>{f"{w_}-{n_ - w_}" if n_ else "no results yet"}{ltxt}</small></span>'
                     f'<i style="color:{hue}">{f"{w_ / n_:.0%}" if n_ else "—"}</i>{"<em>▾</em>" if n_ or lr_ else ""}</div>')
    by_sport = "".join(chips)
    RECORDS["by sport"] = {name.split(" ", 1)[1]: wlt(sum(r == 'won' for lg, r in res if lg in lgs),
                                                      sum(r == 'lost' for lg, r in res if lg in lgs)) for name, lgs in groups + tn_groups}
    # record per pick type
    rec = []
    for kind, (label, c1, c2) in LOOK.items():
        if kind in ("lock", "dog"):                          # (their own boxes up top - no double boxes)
            continue
        ps = [p for p in graded_all if p["kind"] == kind]
        if kind in ("eight", "solo", "night") and not ps:             # the retired 8-leg / one-game-day pick: only with history
            continue
        r, h = wl(ps)
        pass   # (no per-parlay / one-game-pick records - the owner, 9/28)
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
    calls_, open_ = day_calls(picks, today)                  # the day's PICKS, each once (the owner, 10/1: "we won
    #                                                          three and lost two" - never the parlay cards as L's)
    w_, l_ = sum(r == "won" for r in calls_.values()), sum(r == "lost" for r in calls_.values())
    graded = [p for p in done if p["date"] == today and p["kind"] != "eight"]           # (the cards: the big-hit lines)
    live_today = any(e.get("result") in ("won", "lost") and e.get("date") == today for e in live.values())
    if w_ + l_ == 0 and live_today:
        pass                                                      # the live results below speak for the day
    elif open_:
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
    # (no "studied the tape on N games" line - the owner, 9/28: it doesn't belong in a daily review)
    n = sum(p.get("eval_games", 0) for p in params.values())
    if n:
        a_ = sum((p.get("oos") or {}).get("acc", p["accuracy"]) * p.get("eval_games", 0) for p in params.values()) / n
        lines.append([f"🎯 The engine calls the straight-up winner {a_:.0%} of the time on games it never saw.",
                      f"🎯 On games it never saw, the engine picks the winner {a_:.0%} of the time.",
                      f"🎯 Straight-up winners, games the engine never saw: {a_:.0%} called right."][k % 3])
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
    seen_s, uniq = set(), []                                  # no sentence twice in the nutshell ("Trust the algorithm"
    for ln in lines:                                          # showed up on two lines, 9/28)
        keep = [x for x in re.split(r"(?<=[.!?])\s+", ln) if re.sub(r"\W", "", x.lower()) not in seen_s or not x.strip()]
        seen_s |= {re.sub(r"\W", "", x.lower()) for x in keep if len(x) < 40}   # (short sayings: once)
        if keep:
            uniq.append(" ".join(keep))
    lines = uniq
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
/* 🥊 PATTY vs THE ALGORITHM (sports_challenge.py) */
.pvw-w{{color:#22e39a;font-weight:900}}.pvw-l{{color:#ff5a5a;font-weight:900}}

.pvw{{font-size:13px;font-weight:800;color:#ffd23f;margin:0 0 6px}}
.pvx .pvs{{font-size:17px;font-weight:900;color:#fff;margin:6px 0 8px;letter-spacing:.01em}}
.pvr{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px;margin-top:6px}}
.pvh>div{{font-size:12px;font-weight:900;letter-spacing:.08em;color:#ffd23f;text-transform:uppercase}} .pvh em{{font-style:normal;color:#fff}}
.pvc{{display:flex;flex-direction:column;gap:2px;background:rgba(255,255,255,.05);border-radius:10px;padding:7px 9px;font-size:14px;font-weight:800;color:#fff;min-width:0}}
.pvp{{display:flex;align-items:center;gap:6px}} .pvp b{{flex:1}}
.pvc small{{font-size:10px;font-weight:800;opacity:.9}}
.pvc span{{overflow-wrap:anywhere}} .pvc b{{font-weight:900;font-variant-numeric:tabular-nums}}
.pvc .pvp>i{{font-style:normal;min-width:1.2em;text-align:right;font-size:12px}} .pvc.lost>span,.pvc.lost .pvp b{{text-decoration:line-through;text-decoration-color:#ff3b3b;text-decoration-thickness:2px}}
.pvc.won{{box-shadow:inset 0 0 0 1px #22c55e88}} .pvc.lost{{box-shadow:inset 0 0 0 1px #ff3b3b88}}
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
.sec span{{font-size:12px;color:var(--gold);font-weight:800}}
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

.px>summary{{list-style:none;cursor:pointer;padding:10px 12px;margin:6px 0 2px;border:1px solid rgba(255,255,255,.18);border:1px solid color-mix(in srgb,var(--c1) 45%,transparent);border-radius:12px;display:flex;flex-direction:column;gap:4px}}
.px>summary::-webkit-details-marker{{display:none}}
.pxo,.pxc{{font-size:14px;color:var(--gold);font-weight:800}} div.pxt{{margin:2px 0 10px!important}} .pxt{{display:block;font-size:13.5px;font-weight:900;margin-top:4px;letter-spacing:.2px;color:var(--gold);text-shadow:0 0 10px rgba(255,194,51,.35)}} .pxc{{display:none}} .px[open] .pxo{{display:none}} .px[open] .pxc{{display:inline}}
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
.ask-b{{padding:0 12px 12px}} .ask-n{{font-size:12px;font-weight:700;color:#fff;margin:2px 0 8px}} .ask-n b{{color:#22e39a}}
.ask-row{{display:flex;gap:6px}} #askgo{{flex:none;font-size:15px;font-weight:900;padding:8px 12px;border-radius:12px;border:0;background:linear-gradient(90deg,#22d3ee,#b36bff);color:#04060c}}
#askq{{width:100%;font-size:16px;padding:8px 11px;border-radius:12px;border:1px solid rgba(34,211,238,.55);background:#060a12;color:#fff}}
#askq::placeholder{{color:#5fd4e8}}
#asklist{{display:flex;flex-direction:column;gap:6px;margin-top:10px}}
.ask-g{{text-align:left;background:var(--card2);border:1px solid var(--line);color:#fff;border-radius:10px;padding:10px 12px;font-size:14px;font-weight:700}}
.ask-g small{{color:#22d3ee;font-weight:700;margin-left:6px}}
.ask-c{{margin-top:12px}} .ask-l{{font-size:17px;margin:8px 0 2px}} .ask-l b{{color:#fff}}
.ask-a{{font-weight:800;color:#fff;margin:2px 0 6px}} .ask-w{{font-size:13px;font-weight:700;color:#fff;margin:6px 0}}
.ask-h{{font-size:13px;font-weight:700;color:#fff;margin:4px 0}} .ask-h b{{color:#fff}}
.ask-prop{{font-size:15px;font-weight:900;color:#ff5a7a;margin:6px 0 10px}}
.ask-d{{font-size:12px;font-weight:800;color:#ffc233;margin-top:8px}}
.own{{font-size:13px;font-weight:800;color:#ffc233;margin-top:6px;border-left:3px solid #ffc233;padding-left:8px}}
.hist{{margin:4px 0 14px;border:1px solid rgba(255,194,51,.35);border-radius:12px;background:var(--card2);padding:0 12px}}
.hist>summary{{list-style:none;cursor:pointer;padding:12px 0;font-weight:900;font-size:15px;letter-spacing:.06em;color:#ffc233}}
.hist>summary span{{display:block;font-size:12px;font-weight:700;letter-spacing:0;color:#fff;margin-top:2px}}
.hist summary::-webkit-details-marker{{display:none}}
.hs{{border-top:1px solid rgba(255,255,255,.08)}}
.hs>summary{{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 0;font-size:15px}}
.hs>summary b{{color:#fff;font-weight:900}} .hs>summary span{{color:#ffc233;font-weight:800;white-space:nowrap}}
.hs>summary::after{{content:"▾";color:#fff;margin-left:6px}} .hs[open]>summary::after{{content:"▴"}}
.hs-own{{font-size:11px;font-weight:900;letter-spacing:.14em;color:#fff;padding:12px 0 2px;border-top:1px solid rgba(255,255,255,.08)}}
.hr{{display:grid;grid-template-columns:3.6em 1.4em minmax(0,1fr);gap:6px;padding:7px 0;border-top:1px dashed rgba(255,255,255,.06);font-size:13.5px;align-items:start}}
.hr .hd{{color:#fff;font-weight:700;white-space:nowrap}} .hr .hp{{color:#fff;font-weight:800;overflow-wrap:anywhere}}
.hx>summary{{list-style:none;cursor:pointer;grid-template-columns:3.6em 1.4em minmax(0,1fr) 1em}} .hx>summary::-webkit-details-marker{{display:none}}
.hx .hc{{font-style:normal;color:#fff;font-size:12px;transition:transform .2s}} .hx[open] .hc{{transform:rotate(180deg)}}
.hrv{{padding:2px 0 9px calc(5em + 12px);font-size:13.5px;font-weight:700;color:#ffc233}}
.hr .hp small{{color:#fff;font-weight:700}} .hr .hp em{{display:block;font-style:normal;font-weight:800;color:#ffc233;margin-top:3px}} .hr.lost .hp{{color:#fff}}
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
.un{{margin-top:2px;text-align:right;font-size:17px;font-weight:900;letter-spacing:.08em;color:#fff}}
.evr .un,.egl .un{{text-align:left;margin-top:4px}} .evr .un .mb,.egl .un .mb{{display:inline-block;margin:0}}   /* an early play's units: under its game time */
.unw{{display:block;font-size:13px;letter-spacing:.02em;font-weight:800;color:#fff;text-transform:none}}   /* why ½u */
.nou{{text-align:center;font-size:14px;font-weight:900;letter-spacing:.06em;color:#fff;margin:2px 0 8px}}   /* live: no units */
.mb{{display:inline-block;filter:hue-rotate(75deg) saturate(1.6)}}   /* the money bag in green (the owner, 9/30) */
.dayr{{margin:12px 0 0;padding:14px;border-radius:12px;background:var(--card);border:2px solid #22e39a;text-align:center}}
.dayr.dn{{border-color:#ff3b3b}}
.dayr-t{{font-size:14px;font-weight:900;color:#ffc233;letter-spacing:.06em}}
.dayr-n{{font-size:28px;font-weight:900;color:#22e39a;margin-top:4px}}
.dayr.dn .dayr-n{{color:#ff5a5a}}
.dayr-s{{font-size:15px;font-weight:800;color:#fff;margin-top:2px}}
.unb{{margin-top:12px;padding:14px;border-radius:16px;background:var(--card);border:1px solid rgba(255,194,51,.45)}}
.unt{{font-size:clamp(34px,10vw,46px);font-weight:900;text-align:center;line-height:1.1}} .unt.up,.unr b.up{{color:var(--up)}} .unt.dn,.unr b.dn{{color:var(--dn)}}
.unp{{text-align:center;font-size:13px;font-weight:800;color:#fff;margin:2px 0 8px}}
.unr{{display:flex;justify-content:space-between;gap:10px;font-size:14px;font-weight:800;color:#fff;padding:6px 0;border-top:1px solid var(--line)}}
.evx{{margin-top:14px}} .gdx{{margin-top:14px}} .egh{{text-align:right;font-size:10.5px;font-weight:900;letter-spacing:.1em;color:#fff;margin:10px 0 2px}}
.egr{{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 0;border-top:1px solid var(--line)}}
.egl b{{color:#fff;font-size:19px;font-weight:900}} .egl small{{color:#fff;font-weight:800}} .egl span{{display:block;font-size:14.5px;font-weight:800;color:#fff;margin-top:2px}}
.egl u{{display:block;text-decoration:none;font-size:14.5px;font-weight:900;color:#ffc233;margin-top:2px}}
.egp{{text-align:right;white-space:nowrap}} .egp s{{text-decoration:none;font-size:17px;font-weight:900;color:#fff}} .egp em{{font-style:normal;color:#ff7a00;margin:0 4px;font-weight:900}}
.egp b{{font-size:20px;font-weight:900;color:#fff}} .egp i{{display:block;font-style:normal;font-size:13.5px;font-weight:900;color:#fff;margin-top:3px}} .pk-l.evt{{font-size:clamp(17px,5vw,23px);letter-spacing:.04em;line-height:1.1;white-space:nowrap;color:#fff;text-shadow:0 0 14px rgba(255,45,45,.85)}}
.pk-i.evi{{width:46px;height:46px;font-size:24px;border-radius:13px}} .evs{{font-size:13px;font-weight:800;color:#fff;margin:10px 0 6px}} .evs b{{color:#ffc233}}
.evb{{margin:12px 0 6px;padding:8px 4px;border-radius:12px;display:flex;justify-content:center;align-items:center;text-align:center;font-weight:900;font-size:clamp(11px,3.3vw,15px);
letter-spacing:.03em;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.35);background:linear-gradient(90deg,#d90000,#ff3b3b,#ff7a00,#ff3b3b,#d90000);background-size:200% 100%;
box-shadow:0 0 24px -4px rgba(255,45,45,.85);animation:evb 3s linear infinite;white-space:nowrap;overflow:hidden}}
@keyframes evb{{to{{background-position:-200% 0}}}}
.evr i.evg{{flex-shrink:0;white-space:nowrap;font-size:12px;font-weight:900;letter-spacing:.08em;color:#fff;background:#ff2d2d;padding:6px 10px;border-radius:999px;
box-shadow:0 0 14px -2px #ff2d2d;animation:evp 1.4s ease-in-out infinite}} @keyframes evp{{50%{{transform:scale(1.07)}}}}
.evr{{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 0;border-top:1px solid var(--line)}}
.evr b{{color:#fff;font-size:20px;font-weight:900}} .evr small{{color:#fff;font-weight:800;font-size:14px}} .evr em{{font-style:normal;font-weight:900;color:#fff;font-size:20px}}
.evr span{{display:block;font-size:15px;font-weight:800;color:#fff;margin-top:4px}} .evr i{{font-style:normal;font-size:18px}} .evr u{{display:block;text-decoration:none;font-size:15px;font-weight:900;color:#ffc233;margin-top:4px}}
.evh{{font-size:11px;font-weight:900;letter-spacing:.14em;color:#fff;margin-top:10px}} .evn{{font-size:13px;font-weight:700;color:#fff;padding:6px 0}}
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
.pay{{text-align:right;font-size:14px;color:#fff;font-weight:700}} .pay b{{color:var(--c1);font-size:18px}} .pay span{{color:var(--c1);font-size:12px}}
.leg{{border-top:1px solid rgba(255,255,255,.07);padding:10px 0 8px}}
.lt{{display:flex;justify-content:space-between;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--c1)}} .lt>.tm{{font-size:13px;font-weight:900;letter-spacing:.04em;color:var(--gold);text-shadow:0 0 10px rgba(255,194,51,.35);white-space:nowrap}}
.lgb{{color:#fff}}
.lm{{display:flex;justify-content:space-between;align-items:baseline;margin-top:3px}}
.pick{{font-size:18px;font-weight:850;color:#fff}} .pick em{{font-style:normal;color:#fff;font-weight:900;margin-left:2px}}
.od{{font-size:17px;font-weight:900;color:#fff;font-variant-numeric:tabular-nums}}
.ls{{font-size:13px;color:#fff;font-weight:700;margin-top:2px}} .ls b{{color:#fff}}
.ep{{color:var(--up);font-weight:800}} .en{{color:#ff8a5c;font-weight:800}}
.why{{font-size:13px;color:#fff;font-weight:700;margin-top:4px}} .why.rvy{{color:#ffc233}}   /* reviews, pre-game + after: yellow (the owner) */
.pubs{{margin-top:6px}} .pub{{display:inline-block;font-size:11px;font-weight:900;letter-spacing:.1em;padding:4px 9px;border-radius:999px}}
.pub.fade{{color:#fff;background:linear-gradient(90deg,#7c3aed00,#e3121b33);border:1px solid #ff3b3b}} .pub.ride{{color:#22e39a;border:1px solid #22e39a;background:rgba(34,227,154,.1)}}
.lv{{color:#ff3b3b !important;animation:blink 1.2s infinite}} @keyframes blink{{50%{{opacity:.2}}}}
.dly{{color:#ffc233;font-weight:900;letter-spacing:.06em}} .lvb{{color:#ff4040;font-weight:900;letter-spacing:.08em;white-space:nowrap;text-shadow:0 0 8px rgba(255,64,64,.6)}} .fnb{{color:#fff;font-weight:900;letter-spacing:.08em}} .lsc{{font-size:.9em;color:#fff;font-weight:700;margin:2px 0 4px;font-variant-numeric:tabular-nums}} .lsc b{{font-weight:800}} .lsc>span{{color:#ff8a8a;font-weight:700}}
.tsb{{display:grid;gap:2px 0;align-items:center;max-width:250px;margin:4px 0 6px;padding:5px 9px;border-radius:8px;background:rgba(255,255,255,.05);font-size:.95em}}
.tsb .nm{{color:#fff;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .tsb .nm i{{font-style:normal;margin-left:6px;font-size:.78em;font-weight:900;color:#d7ff3a;letter-spacing:.02em}}   /* who's serving, in words (the owner, 9/29) */
.tsb b{{text-align:center;font-weight:700;color:#fff}} .tsb b.w{{color:#fff;font-weight:900}} .tsb b.l{{color:#fff;font-weight:700}}
.tsb em{{font-style:normal;text-align:center;font-weight:900;color:#ff8a8a}} .lvb i{{display:inline-block;width:10px;height:10px;border-radius:50%;background:#ff2b2b;margin-right:6px;vertical-align:0;box-shadow:0 0 6px 1px #ff2b2b;animation:lvp 1.4s infinite}}
@keyframes lvp{{0%{{box-shadow:0 0 0 0 rgba(255,43,43,.9),0 0 6px 1px #ff2b2b}}70%{{box-shadow:0 0 0 9px rgba(255,43,43,0),0 0 6px 1px #ff2b2b}}100%{{box-shadow:0 0 0 0 rgba(255,43,43,0),0 0 6px 1px #ff2b2b}}}}
.nolive{{font-size:14px;font-weight:700;color:#fff;line-height:1.45}} .pk.lvi{{padding-top:16px;padding-bottom:16px}}
.tn{{margin:26px 0 10px;border:2px solid #c6f000;border-radius:20px;background:linear-gradient(165deg,#c6f00026,var(--card));box-shadow:0 0 22px #c6f00033}}
.tn summary{{list-style:none;cursor:pointer;padding:24px 20px;display:flex;flex-direction:column;gap:8px}}
.tn summary::-webkit-details-marker{{display:none}}
.tn-t{{font-weight:900;letter-spacing:.14em;color:#c6f000;font-size:22px}} .tn-s{{font-size:15px;color:#fff;font-weight:700}}
.spc.tap{{cursor:pointer}} .spc.on{{border-color:#22d3ee}}
.rc.tap{{cursor:pointer}} .rc.on{{outline:1px solid #22d3ee}}
.spx{{grid-column:1/-1;text-align:left;background:var(--card2);border:1px solid #22d3ee55;border-radius:12px;padding:6px 10px;margin:-2px 0 4px}} .spc em{{font-style:normal;color:#fff;font-size:12px;margin-left:8px}}
.tn[open] .tn-s{{color:#c6f000}} .tn-b{{padding:0 12px 14px}} .tn-d{{font-size:12px;color:#fff;font-weight:700;margin:0 6px 10px}}
.tn-day{{font-size:11px;font-weight:900;letter-spacing:.12em;color:#c6f000;margin:10px 0 -2px}}
.chip.lean{{background:#ffc233;color:#111;margin-right:6px}} .chip.val{{background:#ff5a1f;color:#fff;margin-right:6px}}
.chip.lk{{background:#22e39a;color:#06281c;margin-right:6px}}
.chip.in{{background:#22d3ee;color:#04202a;margin-left:auto}} .chip.bin{{background:#ff3b3b;color:#fff;margin-left:auto}} .sec h2.bn,.sec span.bn{{color:#ff4d4d;text-shadow:0 0 12px rgba(255,59,59,.45)}} .sec span.bn{{font-weight:900;letter-spacing:.08em}} .pk-l.tn8{{letter-spacing:.1em;font-size:15px;white-space:nowrap}}
.pk.lvc{{box-shadow:0 0 0 2px #ff3b3b,0 18px 50px -14px #ff3b3b}} .chip.livechip{{color:#fff;background:#ff3b3b}}
.bd{{margin-top:8px;border:1px solid color-mix(in srgb,var(--c1) 45%,transparent);border-radius:12px;background:rgba(0,0,0,.25)}}
.bd summary{{list-style:none;cursor:pointer;padding:8px 12px;font-size:13px;font-weight:800;color:var(--c1);letter-spacing:.04em}}
.bd summary::-webkit-details-marker{{display:none}}
.bd summary:after{{content:"▾";float:right;transition:transform .2s}} .bd[open] summary:after{{transform:rotate(180deg)}}
.bd-s{{padding:2px 12px 8px}} .bd-t{{font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);margin-top:4px}}
.bd-s p{{margin:6px 0;font-size:13.5px;color:#fff;font-weight:700;line-height:1.45}} .bd-s p:last-child{{color:var(--gold);font-weight:700}}
.outs{{font-size:11.5px;color:#ff8a5c;margin-top:3px}}
.fin{{font-size:12.5px;color:#fff;font-weight:700;margin-top:3px}}
.lw{{color:var(--up);margin-right:6px}} .ll{{color:var(--dn);margin-right:6px}} .lp{{color:var(--gold);margin-right:6px}}
.nopick{{color:#fff;font-weight:700;font-size:13px;padding:12px 0 6px}}
.hero{{position:relative;background:linear-gradient(160deg,#131a28 0%,var(--card) 60%);border:1px solid rgba(255,194,51,.28);border-radius:24px;padding:20px 20px 8px;overflow:hidden;
  box-shadow:0 20px 60px -24px rgba(255,160,40,.45)}}
.lbl{{color:#fff;font-size:12px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}
.total{{font-size:42px;font-weight:800;letter-spacing:-.02em;margin:4px 0 8px;font-variant-numeric:tabular-nums}}
.sp-n{{font-size:12px;color:#fff;font-weight:700;margin:4px 0 12px}}
.grades{{margin-bottom:12px}}
.ovr{{text-align:center;background:linear-gradient(160deg,rgba(34,227,154,.14),rgba(255,194,51,.10));border:1px solid rgba(34,227,154,.45);border-radius:16px;padding:14px 12px;margin:10px 0 12px}}
.ovr-t{{font-size:13px;font-weight:900;letter-spacing:.12em;color:#22e39a}} .ovr-r{{font-size:46px;font-weight:900;line-height:1.1}}
.ovr-p{{font-size:15px;font-weight:800;color:#ffc233}} .ovr-s{{font-size:13px;font-weight:700;color:#22d3ee;margin-top:2px}}
.sp-n.what{{color:#fff;font-weight:700;line-height:1.5}} .sp-n.what b{{color:#22e39a}}
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
.rc-wide{{grid-column:1/-1}} .rc-wide .hs-by{{margin:8px 0 0}} .lvt{{margin-top:6px}}
.hs-by{{margin:6px 0 10px;padding:8px 10px;border-radius:10px;background:rgba(34,211,238,.08);border:1px solid rgba(34,211,238,.25)}}
.hs-by>div{{display:flex;align-items:baseline;gap:8px;font-size:13px;font-weight:800;color:#fff;padding:3px 0}}
.hs-by>div>span{{flex:1}} .hs-by>div.tap{{cursor:pointer}} .hs-by em{{font-style:normal;color:#22d3ee;font-size:11px}}
.hs-by>div.on{{color:#22d3ee}} .hs-by .spx{{display:block;padding:6px 10px;font-size:inherit;overflow:hidden}} .hs-by b{{font-variant-numeric:tabular-nums}} .hs-by i{{font-style:normal;color:#22d3ee;min-width:3.2em;text-align:right}}
.rc-t{{font-size:11px;font-weight:900;letter-spacing:.12em;color:var(--c1)}}
.rc-r{{font-size:clamp(13px,4vw,15.5px);font-weight:900;color:#fff;margin-top:8px;white-space:nowrap;letter-spacing:-.01em;font-variant-numeric:tabular-nums}}
.rc-p{{font-weight:800;color:var(--c1);font-size:12.5px;white-space:nowrap;letter-spacing:-.01em}} .rc-s{{font-size:11.5px;color:var(--c2);font-weight:700;margin-top:2px}}
.list{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:4px 14px}}
.rr{{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}} .rr:last-child{{border:0}}
.rk{{font-size:18px}} .rd{{flex:1;min-width:0}}
.rl{{font-weight:750;color:#fff;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rm{{font-size:11.5px;color:#fff;font-weight:700}}
.rv{{font-weight:900;font-variant-numeric:tabular-nums}}
.empty{{color:#fff;font-weight:700;font-size:13px;padding:12px 0}}
.br{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 14px;margin-bottom:10px}}
.br.self{{border-color:rgba(255,194,51,.35)}}
.bh{{display:flex;justify-content:space-between;align-items:center}}
.bn{{font-weight:900;color:#fff;font-size:15px}} .bt{{font-size:12px;color:var(--muted);font-weight:700}} .bt b{{color:var(--gold)}}
.bs{{font-size:12.5px;color:#fff;font-weight:700;margin-top:3px}} .bs b{{color:#fff}} .bs b.up,.bs .up{{color:var(--up)}} .bs b.dn,.bs .dn{{color:var(--dn)}}
.fxs{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:9px}}
.fx{{position:relative;font-size:10px;font-weight:800;color:#fff;letter-spacing:.04em;padding-top:8px;text-align:center}}
.fx i{{position:absolute;top:0;left:0;height:4px;border-radius:4px;box-shadow:0 0 8px currentColor}}
.fx::before{{content:"";position:absolute;top:0;left:0;right:0;height:4px;border-radius:4px;background:rgba(255,255,255,.08)}}
.bc{{font-size:11.5px;color:#fff;margin-top:8px}}
.nut{{font-size:13.5px;font-weight:700;margin-top:7px;padding-left:14px;position:relative}} .nut:before{{content:"▸";position:absolute;left:0;color:var(--gold)}}
.foot{{text-align:center;color:#fff;font-weight:700;font-size:12px;margin-top:22px;line-height:1.6}}
.foot b{{color:#fff}} .foot a{{color:#22d3ee;text-decoration:none;font-weight:700}}
.bell{{margin:-2px 2px 10px}}
#bellb{{display:inline-flex;align-items:center;gap:6px;max-width:100%;white-space:nowrap;font-size:13px;font-weight:900;letter-spacing:.04em;color:#fff;
  padding:7px 13px;border-radius:999px;border:1px solid rgba(255,59,59,.6);background:linear-gradient(90deg,rgba(255,59,59,.16),rgba(255,138,0,.12));
  box-shadow:0 6px 18px -10px #ff3b3b;cursor:pointer;-webkit-tap-highlight-color:transparent}}
#bellb[hidden],.bell-n[hidden]{{display:none}}
#bellb:active{{transform:scale(.97)}} #bellb:disabled{{opacity:.6}}
#bellb.on{{color:var(--up);border-color:rgba(34,227,154,.45);background:rgba(34,227,154,.08);box-shadow:none}}
.bell-n{{font-size:12px;font-weight:700;color:#fff;margin:7px 2px 0;line-height:1.4}} .bell-n b{{color:#fff}}
</style></head><body><main>
<header class="head">
  <div class="title"><span class="the">THE</span> <span class="d503">D503</span></div>
  <div class="tag">SPORTS ENGINE</div>
  <div class="live"><span class="dot" id="dot"></span><span id="ago">LIVE</span></div>
</header>
<div class="trust-wrap"><div class="trust">TRUST THE ALGORITHM</div></div>
{day_recap(picks) if UNITS_ON else ""}
<div class="ask" id="ask"><div class="ask-top"><span class="ask-t">🤔 QUESTION BOX</span></div>
<div class="ask-b"><div class="ask-n">{ask_note}</div>
<div class="ask-row"><input id="askq" type="search" placeholder="What’s good? 🤔" autocomplete="off" enterkeyhint="send">{ask_btn}</div>
<div id="asklist"></div><div id="askout"></div></div></div>
<div class="sec"><h2 class="bn"><i class="lv">●</i> LIVE</h2><span>updates every 5 sec</span></div>
{bell}<div id="live"><section class="pk lvi" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="pk-h"><span class="pk-i">🔥</span><span class="pk-l tn8">LIVE PLUS MONEY</span><span class="chip bin">BET IT NOW</span></div><div class="nolive">👀 The algorithm’s watching every play for value.</div></section></div>
<div id="livetoday">{live_list}</div>
<div class="sec"><h2><i>●</i> TODAY'S BOARD</h2><span>{E(board_date)}</span></div>
<div class="board">{board}</div>
{tomorrow}
{early}
{_tennis()}
{challenge}
<div class="sec"><h2><i>●</i> THE RESULTS</h2><span>every play, graded</span></div>
<section class="hero">
  <div class="lbl">The engine's grades</div>
  <div class="sp-n what"><b>What counts:</b> all locks, the Dog of the Day and every value pick (parlay legs too) go in our record. Leans, live plus money and tennis keep their own. Question box reads don’t count. Every W, every L, right here — we don’t hide nothing.</div>
  {overall}
  <div class="recs grades">{grades}</div>
  <div class="lbl" style="margin-top:4px">Their own records <small style="color:#ffc233;letter-spacing:0">· not in our record</small></div>
  <div class="recs grades">{others}</div>
  <div class="lbl" style="margin-top:4px">By sport</div>
  <div class="sports">{by_sport}</div>
  <div hidden>{hist}</div>
</section>
<div class="sec"><h2><i>●</i> THE BRAIN</h2><span>retrained {E(tuned)}</span></div>
{brain}
<div class="foot"><b>THE D503 SPORTS ENGINE</b><br>
Ratings · form · rest · injuries · line moves — retrained after every final score.<br>
Picks only — no bets placed · refreshes hourly</div>
</main>
<script>
(function(){{   // 📡 LIVE VALUE: checks live.json every 2 seconds; a play disappears the moment its value is gone
function esc(x){{return String(x).replace(/[&<>"]/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var last="",PLAY_FRESH_MS={PLAY_FRESH_S}*1000;
var NOU='{LIVE_NO_UNITS if UNITS_ON else ""}';   // no units on live bets (the owner, 9/30): said once, up top
var HEAD='<div class="pk-h"><span class="pk-i">🔥</span><span class="pk-l tn8">LIVE PLUS MONEY</span><span class="chip bin">BET IT NOW</span></div>';
function idle(n){{return '<section class="pk lvi" style="--c1:#ff3b3b;--c2:#ff8a00">'+HEAD+NOU+'<div class="nolive">'+(n<0?   // one red box:
  '👀 The algorithm’s watching every play for value.':n>0?                                                                  // what you can bet
  '👀 The algorithm’s watching every play for value. '+n+' game'+(n>1?'s':'')+' going.':   // right now
  '😴 No games going right now.')+'</div></section>';}}
function draw(d){{var el=document.getElementById("live");if(!el)return;var ps=(d&&d.plays)||[],n=d?(d.live_games||0):-1;
 var key=JSON.stringify(ps)+n;if(key===last)return;last=key;          // unchanged: leave it (an open breakdown stays open)
 el.innerHTML=(ps.length?'<section class="pk lvc" style="--c1:#ff3b3b;--c2:#ff8a00">'+HEAD+NOU+ps.map(function(p){{
  return '<div class="leg"><div class="lt"><span class="lgb">'+esc(p.emoji)+' '+esc(p.sport)+(p.double_down?' · 🔁 DOUBLE DOWN':'')+
   (p.paused?' · ⏸ LINE PAUSED':'')+'</span><span class="tm">'+esc(p.clock)+'</span></div>'+
   '<div class="lm"><span class="pick">'+esc(p.team)+' <em>ML</em></span><span class="od">+'+esc(p.odds)+'</span></div>'+
   '<div class="ls">'+esc(p.score)+(p.ball?' · '+esc(p.ball):'')+'</div><div class="why">'+esc(p.line)+'</div>'+
   ((p.breakdown||[]).length?'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">'+p.breakdown.map(function(x){{return"<p>"+esc(x)+"</p>"}}).join("")+'</div></details>':'')+
   '</div>';}}).join("")+'</section>':idle(n));}}
function badge(r){{return r==="won"?'<span class="lr won">✅ CASHED</span>':r==="lost"?'<span class="lr lost">❌ MISSED</span>':""}}
function today(T){{var el=document.getElementById("livetoday");if(!el||!T)return;   // today's live bets, pending too: straight
 T.forEach(function(e){{var have=el.querySelector('.leg[data-pid="'+e.pid+'"]');       // from the watcher, no page rebuild needed
  if(e.result){{if(have)have.remove();return}}   // graded: it clears into THE RESULTS right away (the owner, 9/30)
  if(have)return;
  var sec=el.querySelector("section");
  if(!sec){{el.innerHTML='<section class="pk" style="--c1:#22d3ee;--c2:#2f8bff;margin-top:14px"><div class="pk-h"><span class="pk-i">📡</span><span class="pk-l tn8">TONIGHT&#39;S LIVE BETS</span><span class="chip in">WE&#39;RE IN</span></div>'+NOU+'</section>';sec=el.querySelector("section");}}
  var i=e.pid.lastIndexOf(":"),b=badge(e.result)||'<span class="tm" data-gid="'+esc(e.pid.slice(0,i))+'" data-start="'+esc(e.start||"")+'" data-side="'+esc(e.pid.slice(i+1))+'">⏳ STILL GOING</span>';
  var h=document.createElement("div");h.className="leg "+(e.result||"");h.setAttribute("data-pid",e.pid);
  h.innerHTML='<div class="lt"><span class="lgb">'+esc(e.icon)+' '+esc(e.sport)+(e.dd?' · 🔁 DOUBLE DOWN':'')+'</span>'+b+'</div><div class="lm"><span class="pick">'+esc(e.team)+' <em>ML</em></span><span class="od">+'+esc(e.odds)+'</span></div>'+(e.story?'<div class="ls">'+esc(e.story)+'</div>':'');
  var hd=sec.querySelector(".nou")||sec.querySelector(".pk-h");hd.parentNode.insertBefore(h,hd.nextSibling);}});   // (under the no-units line)
 var s2=el.querySelector("section");if(s2&&!s2.querySelector(".leg"))el.innerHTML="";   // none going: no blue box
 if(window.d503lt)window.d503lt();}}   // newest on top
function show(d){{var age=d?Date.now()-d.updated:1e12;   // plays must be fresh; a "nothing on" board holds till the next watch
 if(d&&age<6*3600000)today(d.today);
 if(d&&(d.plays||[]).length&&age>PLAY_FRESH_MS)d=Object.assign({{}},d,{{plays:[],live_games:-1}});   // a price we haven't re-checked in 45s never shows
 if(d&&d.done)Object.keys(d.done).forEach(function(k){{var r=document.querySelector('.leg[data-pid="'+k+'"]');
   if(r&&!r.classList.contains("won")&&!r.classList.contains("lost"))window.d503stale=1}});   // graded, page says pending
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
function tick(){{m=Math.max(0,Math.round((Date.now()-t)/60000));}}   // (m: the page's age - check() uses it)
// the owner, 9/29: 'Live · 10 min ago' read like the scores were 10 minutes old, and a 'Reconnecting' reads like a
// glitch - so the top right just says 🟢 LIVE. A stalled feed is the hourly bug check's job (it flags the owner).
var touched=0;["touchstart","scroll","keydown","click"].forEach(function(ev){{window.addEventListener(ev,function(){{touched=Date.now()}},{{passive:true}})}});
function check(){{if(document.hidden)return;              // a newer page? swap it in - only once the SITE serves it
 var st=window.d503stale;                                 // a result landed: swap as soon as the new page is up
 if(!st&&Date.now()-touched<30000)return;                  // (otherwise never while someone's scrolling or tapping)
 try{{if(Date.now()-(+sessionStorage.getItem("d503r")||0)<(st?15000:60000))return;}}catch(e){{}}   // at most once a minute
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
 document.querySelectorAll(".tm[data-gid],.pvc[data-gid]").forEach(function(s){{var st=Date.parse(s.getAttribute("data-start")),g=s.getAttribute("data-gid");
  if(g&&st&&n>=st-60000&&n<st+8*3600000)ids[g]=1}});
 var k=Object.keys(ids);if(!k.length)return;
 fetch(API+"/scores?ids="+encodeURIComponent(k.join(",")),{{cache:"no-store"}}).then(function(r){{return r.ok?r.json():null}})
 .then(function(d){{if(d){{window.D503F=d;window.D503Ft=Date.now();liveTags()}}}}).catch(function(){{}});}}
function games(sc){{return (sc.sets||[]).reduce(function(t,x){{return t+(+x[0]||0)+(+x[1]||0)}},0)}}
function flip(sc){{return {{tennis:true,n:[sc.n[1],sc.n[0]],sets:(sc.sets||[]).map(function(x){{return [x[1],x[0]]}}),
  pts:sc.pts?[sc.pts[1],sc.pts[0]]:null,srv:sc.srv===0?1:sc.srv===1?0:null,done:sc.done,live:sc.live,delayed:sc.delayed}}}}
function called(s,sc){{   // the second it's final: ✅ HIT / ❌ MISS from the final score (the official grade + review follow)
 var mk=s.getAttribute("data-mk")||"",side=s.getAttribute("data-side")||"",r=null;
 if(sc.tennis){{if(mk!=="ml")return null;var w=[0,0];(sc.sets||[]).slice(0,sc.done||0).forEach(function(x){{if(x[0]>x[1])w[0]++;else if(x[1]>x[0])w[1]++}});
   if(w[0]===w[1]||Math.max(w[0],w[1])<2)return null;r=w[0]>w[1]?"won":"lost";}}    // (our player's first here; 10/1:
   //                                                         the feed once said "over" after ONE set - Ruud was down
   //                                                         a set, not done. Only 2 sets won calls it.)
 else{{if(side!=="home"&&side!=="away")return null;var us=side==="home"?+sc.h:+sc.a,th=side==="home"?+sc.a:+sc.h;
   if(mk==="ml")r=us>th?"won":us<th?"lost":null;
   else if(mk==="spread"){{var L=parseFloat(s.getAttribute("data-line"));if(isNaN(L))return null;var m=us-th+L;r=m>0?"won":m<0?"lost":"push";}}
   else return null;}}
 if(!r)return null;
 return r==="won"?'<span class="lr won">✅ HIT</span>':r==="lost"?'<span class="lr lost">❌ MISS</span>':'<span class="lr push">PUSH</span>';}}
function liveTags(){{var n=Date.now(),S={{}},W=window.D503S||{{}},F=(n-(window.D503Ft||0)<15000&&window.D503F)||{{}};
 Object.keys(W).forEach(function(k){{S[k]=W[k]}});
 Object.keys(F).forEach(function(k){{var w=W[k],f=F[k];   // tennis: whichever feed is further along wins (the watcher's
  if(w&&w.tennis&&f&&f.tennis){{var wg=games(w),fg=games(f);if(wg>fg||(wg===fg&&w.pts&&!f.pts&&w.src==="book")){{S[k]=w;return}}}}   // book score beats a
  S[k]=f}});                                                                                       // lagging ESPN one
 var B=window.D503B=window.D503B||{{}};   // a score never goes backwards (ESPN's servers hand out older copies)
 Object.keys(S).forEach(function(k){{var sc=S[k],p=B[k];if(!sc)return;
  var g=sc.tennis?games(sc):(+sc.a||0)+(+sc.h||0),pg=p?(p.tennis?games(p):(+p.a||0)+(+p.h||0)):-1;
  if(p&&sc.live&&g<pg)S[k]=p;else B[k]=sc}});
 document.querySelectorAll(".tm[data-start]").forEach(function(s){{
  // 🔴 LIVE while it's being played, with the score + time left right under it (tennis: sets, games, points)
  var st=Date.parse(s.getAttribute("data-start"));if(!st)return;
  var sc=S[s.getAttribute("data-gid")||""];if(sc&&sc.p1&&s.getAttribute("data-side")==="2")sc=flip(sc);   // our player first
  var row=s.closest(".lt"),leg=row&&row.parentNode,box=leg?leg.querySelector(":scope>.lsc"):null;   // the score sits
  //                                                      under the pick (right above its breakdown), never above it
  var on=sc?true:(n>=st&&n<st+6*3600000&&!s.classList.contains("dly"));   // (not started yet: stays DELAYED)
  if(on){{if(!s.dataset.lv)s.dataset.lv=s.innerHTML;
    var tag=sc&&sc.delayed?'⏳ DELAYED':sc&&!sc.live?(called(s,sc)||'<span class="fnb">FINAL</span>'):'<span class="lvb"><i></i>LIVE</span>';
    s.classList.toggle("dly",!!(sc&&sc.delayed));if(s.innerHTML!==tag)s.innerHTML=tag;}}
  else if(s.dataset.lv){{s.innerHTML=s.dataset.lv;delete s.dataset.lv}}   // (only when it's NOT on - it used to undo LIVE)
  if(sc&&!sc.live&&!sc.delayed)window.d503stale=1;       // a pick's game is final: the graded page is coming
  if(sc&&on&&row){{var q=function(x){{return String(x).replace(/[&<>"]/g,"")}},h;
    if(!box){{box=document.createElement("div");box.className="lsc";var bd=leg.querySelector(":scope>details.bd");
      if(bd)leg.insertBefore(box,bd);else leg.appendChild(box);}}
    if(sc.tennis){{var ns=(sc.sets||[]).length,cols="1fr repeat("+ns+",1.5em)"+(sc.pts?" 2.4em":"");   // 🎾 a TV-style scoreboard
      h='<div class="tsb" style="grid-template-columns:'+cols+'">'+[0,1].map(function(i){{
        return '<span class="nm">'+q(sc.n[i])+(sc.live&&sc.srv===i?'<i>serving</i>':'')+'</span>'+(sc.sets||[]).map(function(st,k){{
          var won=k<sc.done&&st[i]>st[1-i];return '<b'+(won?' class="w"':k<sc.done?' class="l"':'')+'>'+st[i]+'</b>'}}).join("")+
          (sc.pts?'<em>'+q(sc.pts[i])+'</em>':'')}}).join("")+'</div>';}}
    else{{var c=sc.clock&&sc.clock!=="Final"?sc.clock:"";
      h='<b>'+q(sc.away+" "+sc.a+" @ "+sc.home+" "+sc.h)+'</b>'+(c?' <span>· '+q(c)+'</span>':'');}}
    if(box.innerHTML!==h)box.innerHTML=h;}}
  else if(box)box.remove();}});
 document.querySelectorAll(".pxt").forEach(function(t){{var d=t.closest("section.pk");if(!d)return;   // a card's yellow
  var one=t.getAttribute("data-one");                                                 // line says how its games are going
  var lv=0,dl=0,up=[];d.querySelectorAll(".tm[data-start]").forEach(function(s){{
   var st=Date.parse(s.getAttribute("data-start")),fin=!!s.querySelector(".fnb,.lr");
   if(s.textContent.indexOf("DELAYED")>=0)dl++;
   else if(s.querySelector(".lvb")||(!fin&&st<=n))lv++;     // started, not FINAL: live (a score just hasn't landed)
   else if(!fin)up.push(st)}});
  if(!lv&&!dl&&!(up.length&&Math.min.apply(null,up)<=n)&&up.length)return;   // nothing started yet: the times stay
  up=up.filter(function(x){{return x>n}});
  var nx=up.length?new Date(Math.min.apply(null,up)).toLocaleTimeString("en-US",{{hour:"numeric",minute:"2-digit",timeZone:"America/Los_Angeles"}}).replace(":00 "," ")+" PT":"";
  var h=one?(lv?"🔴 LIVE":dl?"⏳ DELAYED":"🏁 Final"):
   lv||dl?(lv?"🔴 "+lv+" LIVE":"")+(lv&&dl?" · ":"")+(dl?"⏳ "+dl+" DELAYED":"")+(nx?" · Next game starts at "+nx:""):
   nx?"🕐 Next game starts at "+nx:"🏁 All games final";   // ('Final' only once every game really is final)
  if(t.textContent!==h)t.textContent=h;}})}}
document.addEventListener("click",function(ev){{var c=ev.target.closest&&ev.target.closest("[data-hs].tap");if(!c)return;
 var want=c.getAttribute("data-hs"),hit=null;document.querySelectorAll("details.hs>summary>b").forEach(function(b){{if(b.textContent===want)hit=b.closest("details")}});
 if(!hit)return;var nx=c.nextElementSibling,was=nx&&nx.classList.contains("spx");   // the results open right under
 document.querySelectorAll(".spx").forEach(function(x){{x.remove()}});                        // the chip - no jumping down
 document.querySelectorAll("[data-hs].on").forEach(function(x){{x.classList.remove("on")}});
 if(was)return;                                                                               // (tap again: closed)
 var pn=document.createElement("div");pn.className="spx";var sm=hit.querySelector(":scope>summary");
 pn.innerHTML=hit.innerHTML.replace(sm?sm.outerHTML:"","");c.classList.add("on");c.parentNode.insertBefore(pn,c.nextSibling);}});
function gone(){{var n=Date.now(),b=document.querySelector(".board");if(!b)return;   // a graded card's 3 hours are up:
 b.querySelectorAll(".gn[data-gone]").forEach(function(c){{if(n>=+c.getAttribute("data-gone"))c.remove()}});   // it
 var t=document.getElementById("dropnote");                                          // comes down right then (it's in
 if(t&&!b.querySelector(".gn,.pk"))b.innerHTML=t.innerHTML;}}                        // the results); board empty: 8 AM note
gone();setInterval(gone,30000);
function pvLive(){{var B=window.D503B||{{}};document.querySelectorAll(".pvc[data-gid]").forEach(function(c){{   // 🥊 challenge:
 var i=c.querySelector(".pvp>i"),sc=B[c.getAttribute("data-gid")];if(!i)return;   // 10/1, the owner: it said LIVE for
 if(sc&&sc.p1&&c.getAttribute("data-side")==="2")sc=flip(sc);                      // 6 hours off the clock - now only the
 var h="";if(sc&&sc.live&&!sc.delayed){{                                          // real score feed says LIVE / done
   h='<span class="lvb"><i></i>LIVE</span> '+(sc.sets||[]).map(function(x){{return x[0]+"-"+x[1]}}).join(" ");}}
 else if(sc&&sc.delayed)h="⏳";
 else if(sc&&!sc.live){{var w=[0,0];(sc.sets||[]).slice(0,sc.done||0).forEach(function(x){{if(x[0]>x[1])w[0]++;else if(x[1]>x[0])w[1]++}});
   h=Math.max(w[0],w[1])<2?"":w[0]>w[1]?'<span class="pvw-w">✅ WIN</span>':'<span class="pvw-l">❌ LOSS</span>';}}
 c.classList.toggle("won",h.indexOf("WIN")>=0);c.classList.toggle("lost",h.indexOf("LOSS")>=0);   // (10/1, the owner: a loss
 if(i.innerHTML!==h)i.innerHTML=h;}})}}                     // called live looks just like a graded one)
pvLive();setInterval(pvLive,3000);
window.d503lt=liveTags;liveTags();setInterval(liveTags,15000);fastScores();setInterval(fastScores,1000);
document.addEventListener("visibilitychange",fastScores);
tick();setInterval(tick,30000);check();setInterval(check,15000);document.addEventListener("visibilitychange",check);}})();
</script><script>
(function(){{   // 🤔 ASK THE ENGINE: the engine's read on any game, from reads.json (not our picks, never in the record)
var games=[], q=document.getElementById("askq"), list=document.getElementById("asklist"), out=document.getElementById("askout");
if(!q) return;
var AI="{ask_url}", hist=[];                                   // 🧠 the AI question box (the relay), when it's live
function ai(again){{
  var t=q.value.trim(); if(!AI||!t) return;
  list.innerHTML="";
  out.innerHTML='<section class="pk ask-c" style="--c1:#22d3ee;--c2:#b36bff"><div class="ask-l">🤔 '+esc(t)+'</div><div class="ask-a">🧠 The engine’s doing its homework…</div></section>';
  var ctl=window.AbortController?new AbortController():null, to=setTimeout(function(){{if(ctl)ctl.abort()}},90000);
  fetch(AI,{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{q:t,history:hist}}),signal:ctl?ctl.signal:undefined}})
  .then(function(r){{return r.ok?r.json():Promise.reject(r.status)}})
  .then(function(d){{clearTimeout(to);if(!d||!d.answer)throw 0;
    hist.push({{role:"user",content:t}},{{role:"assistant",content:d.answer}});hist=hist.slice(-6);
    out.innerHTML='<section class="pk ask-c" style="--c1:#22d3ee;--c2:#b36bff"><div class="ask-l">🤔 '+esc(t)+'</div><div class="ask-a">'+esc(d.answer).replace(/\\*\\*(.+?)\\*\\*/g,"<b>$1</b>").replace(/\\n/g,"<br>")+'</div></section>'}})
  .catch(function(){{clearTimeout(to);if(again!==true){{ai(true);return}}   // one hiccup never sends you to the fallback
    out.innerHTML="";render();
    list.insertAdjacentHTML("afterbegin",'<div class="ask-n">The AI’s taking a breather — here’s the engine’s quick read instead. 👇</div>')}});
}}
q.addEventListener("keydown",function(e){{if(e.key==="Enter"){{e.preventDefault();ai()}}}});
var go=document.getElementById("askgo"); if(go) go.addEventListener("click",function(){{ai()}});
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
var WHYL={{"the stronger team":"💪 {{u}} are just the better team tonight.","hotter recent form":"🔥 {{u}} are playing better ball lately.",
 "opponent missing key players":"🚑 {{o}} are banged up — that's the opening.","sharp money moving this way":"💸 The market's catching up to {{u}} — the engine had it first.",
 "better rested":"🛌 {{u}} got the extra rest. Fresh legs.","opponent on a back-to-back":"😮‍💨 {{o}} played last night — tired legs.",
 "better starting pitcher":"⚾ {{u}} got the better arm on the mound.","hotter goalie":"🧱 {{u}} got the hotter goalie.",
 "better QB play lately":"🎯 {{u}} got the better QB play lately.","revenge game":"😤 {{u}} owe these guys one."}};
function whyl(L,g){{var o=L.team===g.home?g.away:g.home;   // a read's top reason in our lingo - never a bare tag (the owner, 9/29)
 for(var i=0;i<L.reasons.length;i++){{var w=WHYL[L.reasons[i]];if(w)return w.replace("{{u}}",L.team).replace("{{o}}",o)}}
 return "🧠 The engine's numbers lean "+L.team+".";}}
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
       (L.reasons.length?'<div class="why">'+esc(whyl(L,g))+'</div>':"")+'</section>';out.innerHTML=h;return}}
  if(g.why=="started"||g.why=="final"){{h+='<div class="ask-a">'+(g.why=="final"?"⏹️ This one’s over — no reads on finished games.":
    pick(g.id+"s",["⏱️ This one already kicked off — pregame reads are closed. Peep LIVE PLUS MONEY up top: if the algorithm sees live value, it shows up there.",
                   "⏱️ Game’s already going. No pregame reads once it starts — watch LIVE PLUS MONEY, that’s where the in-game value shows up."]))+'</div></section>';out.innerHTML=h;return}}
  h+='<div class="ask-l">🧠 The engine’s leaning: <b>'+esc(L.team)+" "+mk+'</b> <span class="od">'+am(L.odds)+'</span></div>'+
     '<div class="ask-a">'+(pct>55?pct+'% to '+(L.market=="ml"?"win":"cover"):"The price is right")+(L.market!="ml"?" ("+Math.round(L.win_p*100)+"% to win)":"")+' · '+vibe(L.p,g.id)+'</div>'+
     (L.reasons.length?'<div class="why">'+esc(whyl(L,g))+'</div>':"")+
     (g.h1?'<div class="ask-h">⏱️ '+(g.h1.name=="first 5 innings"?"After 5 innings":g.h1.name=="1st period"?"After the 1st":"At the half")+': we got <b>'+esc(g.h1.team)+'</b> up — '+Math.round(g.h1.p*100)+'%'+(g.h1.tie>0.05?' (tied '+Math.round(g.h1.tie*100)+'%)':'')+'. '+pick(g.id+"h",["No 1st-half line posted yet, so that’s just the read.","Just the read — books ain’t posted the 1st-half line.","That’s our read on the early action."])+'</div>':"")+
     '<div class="ask-w">Why it’s not a pick: '+pick(g.id,WHY[g.why]||WHY.no_value)+'</div>'+
     '<div class="ask-d">⚠️ Not our pick — this doesn’t count toward our record. '+pick(g.id+"x",OUT)+'</div></section>';
  out.innerHTML=h;
}}
var STOP={{"who":1,"wins":1,"win":1,"will":1,"the":1,"and":1,"what":1,"think":1,"you":1,"about":1,"game":1,"tonight":1,"today":1,"does":1,"engine":1,"gonna":1,"should":1,"bet":1,"take":1,"vs":1,"over":1,"under":1,"first":1,"half":1,"spread":1,"total":1,"lean":1,"lock":1,"pick":1,"with":1,"for":1,"this":1,"that":1,"how":1,"like":1,
  "tennis":1,"match":1,"next":1,"set":1,"sets":1,"mens":1,"womens":1,"men":1,"women":1,"nfl":1,"nba":1,"mlb":1,"nhl":1,
  "football":1,"basketball":1,"baseball":1,"hockey":1,"college":1,"score":1,"live":1,"right":1,"now":1,"going":1,"happen":1}};
// (sport words never count as a name: "tennis" matched every tennis match - the owner, 9/29)
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
  var ts=hay.split(/[^a-z0-9]+/);                              // a short word only matches a whole name ("han" isn't
  if(w.length<4) return ts.indexOf(w)>=0;                          // "shang"), a longer one the start of a name or a typo
  return ts.some(function(t){{return t.length>=4&&(t.indexOf(w)==0||w.indexOf(t)==0||(w.length>=5&&lev(w,t)<=1))}});
}}
function render(){{
  out.innerHTML="";
  if(!loaded){{list.innerHTML='<div class="ask-n">⏳ Hold up — pulling up the engine’s reads…</div>';return}}
  var words=q.value.toLowerCase().replace(/[^a-z0-9 ]/g," ").split(/\s+/).filter(function(w){{return w.length>2&&!STOP[w]}});
  var hits=games.filter(function(g){{return words.some(function(w){{return hit(w,(g.away+" "+g.home).toLowerCase())}})}}).slice(0,12);
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
  if(!same(s,k))return post("/unsubscribe",{{endpoint:s.endpoint}}).catch(function(){{}}).then(function(){{return s.unsubscribe()}})
   .then(function(){{return subscribe(k)}});   // the Worker's key changed: re-join (the old sign-up dropped - never 2 pings)
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
    try:                                                     # every live bet any watch logged: main's copy + the one
        lp = os.path.join(sd.DATA, "live_log.json")          # the watcher ships with its board (live-data), merged
        mine = json.load(open(lp)) if os.path.exists(lp) else {"plays": {}}
        merged = sd.merge_live_logs(mine, sd.live_log_from_branch())
        if merged != mine:
            with open(lp, "w") as f:
                json.dump(merged, f, indent=1, sort_keys=True)
    except (OSError, ValueError):
        pass
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
                                  "start", "breakdown", "outs", "opp_outs", "injury_alerts", "reasons", "game_id", "side")
            if l.get(k) not in (None, [], "")} | ({"season": {"1": "preseason", "2": "regular season", "3": "playoffs"}
                                                  .get(str(l.get("stype")), "regular season")} if l.get("stype") else {})


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
