"""🧾 THE CARD CHECK (the owner, 11/13: "These are bugs - this information and breakdowns, [we] cannot keep this crap
up"). Two days of card bugs fixed one at a time - a goalie who wasn't starting, Skattebo / McCarthy listed out while
playing, "warm-weather team" said of the Commanders, a 4th-down claim with no numbers, "We like Predators - just not at
this price" on a ½u Predators PLAY, canned tails, split lines. This is the check that stops the CLASS.

Every card line runs through here TWICE: before the pick posts (sports.post_board, after the rule check - the text is
rewritten before anybody sees it) and every time the page renders (sports_dashboard._pick_card -> _leg / _breakdown,
posted cards included). It never touches a pick's team / side / price / units - only the words.

What it checks, card by card (each one a class the 11/13 audit found - SPORTS_FINDINGS "11/13 - CARD AUDIT"):
  1. WORDING vs THE BET
     - a unit play never says a lean's words ("no units", "just a lean", "not at this price", "a lean", "parlay piece")
     - a lean never says a unit play's words ("tap in", "lock it in", "half a unit", "easy money", "hammer")
     - a ½u / thin play never hypes ("all day", "load up", "big bet", "lock it in", "free money")
     - only the Lock of the Day says LOCK ("lock it in", "our lock")
     - "coin flip / 50-50 / close to even / toss-up" only on a moneyline side whose read AND price sit near even
       (COIN_BAND) - never a -148 favorite, never a 37% dog
     - a play that carries 1u or more never says a small bet's words ("half a unit", "small bet", "thin edge", "keep it
       light" - 11/17: the sizes stamped at the post)
     - the bottom line's OUR NUMBER is the units line's number (sports_breakdown_v24.card_fair) - never a raw-gap price
       ("We got Tulane at -446" on a +124 dog) and never the book's own number as value ("-142 - -142 is extra money")
  2. FACTS vs THE DATA (re-verified against data/sports/games at check time - FACT_CHECK)
     - a season record, a home / road record, a last-5 record, a win / loss streak, the last game's score, a score
       "inside their last 5", the days of rest: each one against the game files the way the breakdown computes them
       (sports_breakdown_v24._season / _record / _streak / _days). A college team whose games we don't all hold
       (seen_all) gets no record / streak / last-game line. A fact that doesn't match is dropped - no fact = no line.
  3. LINGO
     - the owner's banned frames (sports_owner_lingo.STIFF / EAT_BAN / NEVER) and made-up slang (sports_lingo.MADE_UP)
       come off a line sentence by sentence - posted cards too
     - canned tails with no fact ("Nothing scary about that.", "Still riding Suns.", "Do the math.")
     - "outscoring teams 23 to 29" (outscored), "a 8-3 loss" (an), "Hawks's the side"
     - the same line twice on a card (the one-liner repeated in the breakdown, the 🚑 chip's names again)
  4. WHO PLAYS (11/16 FABLE - EVERY FACT TRUE; while the game hasn't started - who_plays)
     - a quarterback's numbers only for the man the engine can call the starter (sports_qb.call - the depth chart and
       the box scores agree, and he isn't out / questionable): "Carson Wentz has 0 TDs, 2 picks and 81 yards ... for
       Vikings" the day Kirk Cousins started; Gardner Minshew II's numbers on a card that also said he was out
     - a goalie said as tonight's starter only when the goalie page has CONFIRMED him; every other goalie line has to
       say what he is (projected / expected, not confirmed / in net last time out)
     - "a bye" only when a whole football week passed with no game (the 11/2 Bears: Thursday, then Monday)
     - (11/17) a goalie's numbers only once the goalie page has CONFIRMED him - a hedge ("in net last time out",
       "projected") named the wrong man 14 times in 39; once the box score is in, only the man who started
     - (11/17) on a graded card, a man listed out who is in the box score isn't "missing" (played_anyway)
  5. DERIVED FACTS + SENSE (11/17 THE BREAKDOWN SWEEP - results/studies/cards_1117)
     - points a game (lately / on the year), who played last night, the road-trip count, the last meeting: re-read
       off the game files (stats / played_last_night / road_trip / last_meeting)
     - a line that says nothing: "+0 a game", "4 for / 4 against ... 3 for / 3 against", a garbled last meeting,
       another sport's word, rest talk with no back-to-back (sense / rest_talk); a card that fights itself - "full
       squad" beside its own men out, a man out for the wrong team (card_sense)
     - an early play's record / last-game sentence that moved since it posted (early_fact)
A line that fails is rewritten or dropped (the bottom line is rebuilt from the pick, its price and our number - never
lost). Nothing here ever holds a pick: wording is never a reason to pull a bet.

What it caught goes to the run log ("CARD CHECK ...") and to data/sports/pick_audit.json under the pick's date
("card_check"), so the daily review sees it."""
import json
import os
import re
from datetime import datetime, timezone

import sports_data as sd

CAUGHT = []                     # this run's catches: (date, "team: class: line")
_LOGGED = set()                 # (printed once a process)

# ---- 1. WORDING vs THE BET ------------------------------------------------------------------------------------------
LEAN_TALK = re.compile(
    r"\bno units?\b|\bno money\b|not enough (?:for units|to put money on|there for units)|\blean only\b|"
    r"\bjust a lean\b|\ba lean\b|\bthe engine leans\b|\bwe (?:tilt|lean)\b|just not at this price|too steep for units|"
    r"not enough for units|no units at this price|not a unit play|price is too fair to bet|too fair to bet|"
    r"we ain'?t (?:betting|paying for|putting money)|no value at this number|no profit in it|parlay piece|"
    r"isn'?t quite big enough for units|if you gotta (?:pick one|have a side)|ain'?t putting money on it|"
    r"\bno money on it\b|not by enough for units|too close for units|\bnot the price\b", re.I)
UNIT_TALK = re.compile(
    r"\btap in\b|\block it in\b|half a unit|\bfull unit\b|(?<!no )\bunits? on (?:it|this|him|them)\b|\bbigger bet\b|"
    r"\bbig bet\b|\bload up\b|\beasy money\b|\bfree money\b|\bhammer\b|\bsmash\b|trust the algorithm|"
    r"\bwhole hood\b|\bmax play\b|\bwe riding\b|\bstill riding\b|\blet'?s eat\b", re.I)
SMALL_TALK = re.compile(r"half a unit|half-unit|half unit|\bsmall bet\b|\bthin edge\b|keep it (?:light|small)|tread light|"
                        r"\blight bet\b|small (?:stake|money|swing)|don'?t (?:go|get) crazy|\bnot a big one\b", re.I)
#   (11/17 max profit: a small bet's words on a play that carries 1u or more - the card is written before a size stamp /
#    the ⭐ goes on, so the college football thin Lock at 1u said "small bet, not a big one" and a 2u runner-up dog "Half a
#    unit, keep it light". The owner bets what the units say - the words under them never say a smaller bet.)
HYPE = re.compile(r"\ball day\b|\bhammer\b|\bload up\b|\bmax play\b|\bbig(?:ger)? bet\b|\block it in\b|\bfree money\b|"
                  r"\beasy money\b|\bcan'?t lose\b|\bsmash\b|\bwe going big\b", re.I)
SURE = re.compile(r"beat the brakes off|cheeks clapped|smack that ass|about to spank|fin to get spanked|"
                  r"get their ass beat|\beasy call\b|ain'?t a question|no hesitation|\ball day\b|fin to handle that|"
                  r"\bdone talking\b", re.I)
#   (11/17 sweep: a blowout / sure-thing call. Never on a LONG DOG - a moneyline side at +150 or longer the engine's own
#    read has under 40% (sports_breakdown_v24.long_dog): the dry run's Ball State +350 at a 23% read said "Ball State
#    about to beat the brakes off 'em". The pool no longer writes it; this is the last stop for a posted card.)
LOCK_TALK = re.compile(r"\block it in\b|\bour lock\b|\bthis (?:is )?a lock\b|\bit'?s a lock\b|\ba lock\b(?! of)", re.I)
NOT_LOCK = re.compile(r"\b(?:not|no|never) (?:a |the )?lock\b", re.I)
COIN = re.compile(r"coin[- ]flip|\b50-50\b|close to even|\btoss-up\b|could go either way|either way|"
                  r"near even\b|about even\b|by a nose\b", re.I)
COIN_BAND = (0.42, 0.58)        # a moneyline side may be called a coin flip only when its read AND its price sit here
#   (the 11/13 audit: "close to a coin flip - Seahawks by a hair" at -148 / a STRONG LEAN read of 60%; "our read says
#    coin flip" on the Panthers +164 at a 36.6% read; "Toss-up, close to even" on the Pacers -148. sports_breakdown_v24
#    .COIN_FLIP keeps the generator's band; this is the last stop for every card, posted ones too)
BOTTOM = re.compile(r"^\W*(?:✅|🟡)\s*Bottom line:")
LINE_MOVE = re.compile(r"line moved|number got bigger|price drifted|drifted out|since (?:it|the first number) opened|"
                       r"since the first number|moved [\w.' ]+ shorter|the money'?s on 'em|money followed us|"
                       r"the line (?:ran|went) from|line'?s moving|before the line moves", re.I)
#   (the owner, 10/23: "when the line moves it doesn't really matter" - the line under a pick never talks line movement)
BETTER = re.compile(r"\bbetter (?:team|squad|side|club|roster)\b(?! (?:on paper|by the records))|\bstronger (?:team|side|squad)\b|"
                    r"\bthe better team is on our side\b", re.I)
#   (the owner's never-false rule: "the better team" only when the engine's read has them winning)
AM = re.compile(r"(?<![\d.])([+-]\d{3,4})(?![\d.])")

# ---- 3. LINGO --------------------------------------------------------------------------------------------------------
TAILS = re.compile(
    r"^(?:nothing scary about that|teams don'?t come in here and eat|come right on in|"
    r"other people'?s buildings don'?t scare 'em|nobody'?s scared of that|do the math|"
    r"we know\.? the price knows too|the price knows too|we know|somebody'?s taking an l (?:today|tonight)|"
    r"one of 'em takes an l (?:today|tonight)|both sides walk in hot|still riding [\w.' -]{1,30}|"
    r"that'?s the one thing that could burn us|that'?s what could burn us|the numbers under the hood say [\w.' -]{1,30}|"
    r"look at who they played - [\w.' -]{1,40}|same spot in the standings, not the same team|"
    r"little extra juice in the legs|fresh legs, full (?:playbook|game plan)|edge us on the scoreboard|"
    r"so (?:they|we) feeling (?:themselves|ourselves) too|the matchup'?s where [\w.' -]{1,30}|"
    r"we like a coach w[\w' ]*|that'?s the risk here, and it'?s already in the price|"
    r"we saw it, we still got [\w.' -]{1,30}|we weighed it, and [\w.' -]{1,40}|priced in\. we still riding|"
    r"priced in|we still riding|noted\. not enough|noted|not enough|the rest of this card outweighs it|"
    r"that'?s the part that could bite us|the price is sleeping on that|keep reading|"
    r"two (?:winners|teams) (?:walk in, one walks out|looking to get right)|two teams looking to get right|"
    r"defense travels|small edge, ours|the homies riding at [+-]\d+|"
    r"good number|right side)[.!?]?$", re.I)
#   (a whole sentence only: "⚠️ Suns have dropped 3 straight. Still riding Suns." keeps the fact)
OUTSCORE = re.compile(r"\b(is|are|has|have|been)\s+(outscoring|outscored)\s+teams\s+(\d+)\s+to\s+(\d+)", re.I)
A_AN = re.compile(r"\b([Aa]) (8|11|18|8\d|8\d\d)(?=[-\s])")      # ("a 110" stays - a hundred ten)
POSS_SIDE = re.compile(r"\b([A-Z][\w.' ]{1,30}?s)'s the side\b")
FOURTH = re.compile(r"4th[- ]down|fourth[- ]down|goes for it", re.I)
FOURTH_NUM = re.compile(r"\d+ of \d+")
WARM = re.compile(r"warm[- ]weather team|cold[- ]weather team", re.I)


def _sentences(t):
    """(lead, [sentences]) - the emoji lead kept apart."""
    m = re.match(r"^(\W*\s*)", t)
    lead = m.group(1) if m else ""
    import sports_card_guard as g
    return lead, [x for x in g._SENTS.split(t[len(lead):]) if x.strip()]


def _join(lead, parts):
    body = " ".join(p.strip() for p in parts if p.strip()).strip()
    if not body:
        return ""
    return lead + body[:1].upper() + body[1:] if lead.strip() else body[:1].upper() + body[1:]


def _drop_clause(sentence, rx):
    """The sentence without the ' - ' / ' — ' / ', ' clause that matches rx ('' when no fact is left)."""
    parts = re.split(r"(\s[-—]\s|,\s)", sentence)
    out, i = [], 0
    while i < len(parts):
        seg = parts[i]
        if rx.search(seg):
            if out and re.fullmatch(r"\s[-—]\s|,\s", out[-1] or ""):
                out.pop()
            i += 2
            continue
        out.append(seg)
        i += 1
    s = "".join(out).strip(" ,-—")
    if not re.search(r"\d", s):
        return ""
    return s if s.endswith((".", "!", "?")) else s + "."


def _banned_hit(sentence):
    """(the banned phrase found, why) or (None, '')."""
    import sports_owner_lingo as ol
    low = sentence.lower()
    for w in ol.STIFF + tuple(ol.NEVER):
        if w in low and "the whole hood eating" not in low:
            return w, f"a banned frame ('{w}')"
    try:
        import sports_lingo
        m = sports_lingo.MADE_UP.search(sentence)
        if m and m.group(0).lower() not in ("public", "the crowd") and not re.search(r"\d", m.group(0)):
            return m.group(0).lower(), f"made-up slang ('{m.group(0)}')"
    except Exception:                                        # noqa: BLE001
        pass
    return None, ""


def _banned(sentence):
    """The owner's banned frames / made-up slang in this sentence ('' when clean)."""
    return _banned_hit(sentence)[1]


def _unban(sentence):
    """(the sentence with its banned frame taken out - a lead-in ('Say less — the Panthers played last night'), a clause
    ('29-20 win over the 49ers - two winners walk in, one walks out'), a frame before a colon ('Vikings go on the road
    and win: 3-0 away from home') - or '' when nothing with a fact is left, why)."""
    w, why = _banned_hit(sentence)
    if not w:
        return sentence, ""
    s = sentence
    for _ in range(3):
        w, _w = _banned_hit(s)
        if not w:
            break
        low = s.lower()
        i = low.find(w)
        if i < 0:
            return "", why
        m = re.match(r"\s*[-—,:!.]*\s*", s[i + len(w):])
        rest = s[i + len(w) + (m.end() if m else 0):]
        head = s[:i]
        if not head.strip(" -—,:") and re.search(r"\d|[A-Z][a-z]", rest):      # a lead-in: 'Say less — the Panthers ...'
            s = rest[:1].upper() + rest[1:]
            continue
        if re.search(r"\s[-—]\s*$", head) and re.search(r"\d", head):       # a tail clause after ' - '
            s = re.sub(r"\s[-—]\s*$", "", head).rstrip(" ,") + "."
            continue
        if re.match(r"(?:go|goes) on the road and win", w) and rest and re.search(r"\d", rest):
            s = head.rstrip() + " on the road: " + rest                        # ('Vikings on the road: 3-0 ...')
            continue
        return "", why
    return (s if re.search(r"\w", s) else ""), why


def ctx_of(pk, leg):
    """What the card is, for the wording checks: its units, kind, lean or not, thin or not, the read and the price."""
    import sports
    try:
        u = sports.units_for(pk) if pk else None
    except Exception:                                        # noqa: BLE001
        u = None
    if pk and pk.get("status") == "void" and not u:
        u = pk.get("units_posted") or pk.get("units") or u
    lean = bool(pk.get("lean")) if pk else bool(leg.get("is_lean"))
    if pk and not lean and not u and len(pk.get("legs") or []) == 1 and pk.get("status") != "void":
        lean = True                                          # (a straight pick with no units is a lean, whatever it's called)
    kind = (pk or {}).get("kind") or ("lean" if lean else "play")
    try:
        read = sports.read_of(leg)
    except Exception:                                        # noqa: BLE001
        read = leg.get("p")
    dec = leg.get("dec") or (sd.decimal(leg["odds"]) if leg.get("odds") else None)
    return {"units": u or 0, "kind": kind, "lean": lean, "unit": bool(u) and not lean,
            "thin": bool(u) and not lean and u <= 0.5, "lock": kind == "lock" and not lean,
            "floor": bool((pk or {}).get("floor")) or leg.get("floor_score") is not None,
            "market": leg.get("market"), "odds": leg.get("odds"), "read": read, "p": leg.get("p"),
            "implied": (1 / dec) if dec else None, "date": (pk or {}).get("date") or (leg.get("start") or "")[:10]}


def long_dog_cx(cx):
    """A long dog (sports_breakdown_v24.long_dog) from the card's context: +150 or longer, the read under 40%."""
    try:
        import sports_breakdown_v24 as v
        if cx.get("market") != "ml" or (cx.get("odds") or 0) < v.LONG_DOG_ODDS:
            return False
        r = cx.get("read") if cx.get("read") is not None else cx.get("p")
        return r is not None and r < v.LONG_DOG_READ
    except Exception:                                        # noqa: BLE001
        return False


def coin_ok(cx):
    """May this side be called a coin flip / 50-50? Only a moneyline side whose read and price both sit near even."""
    if cx.get("market") != "ml":
        return True                                          # (a spread's cover read is near 50-50 by design)
    lo, hi = COIN_BAND
    for x in (cx.get("read"), cx.get("p"), cx.get("implied")):
        if x is not None and not lo <= x <= hi:
            return False
    return True


def _fair(leg):
    """The card's OUR NUMBER - the units line's (sports_dashboard._units_line): card_fair on read_of, beat=True."""
    try:
        import sports
        import sports_breakdown_v24 as v
        return v.card_fair(leg, sports.read_of(leg), beat=True)
    except Exception:                                        # noqa: BLE001
        return None


def bottom_line(leg, cx):
    """A bottom line rebuilt from what's true: the pick, its price, our number (unit plays, when it beats the price)."""
    o = leg.get("odds")
    am = (f"+{o}" if o > 0 else str(o)) if isinstance(o, (int, float)) else ""
    team = leg.get("team") or ""
    bet = f"{team} {leg['line']:+g}" if leg.get("market") == "spread" and leg.get("line") is not None else team
    if leg.get("market") == "total":
        bet = f"{'Over' if leg.get('side') == 'over' else 'Under'} {leg.get('line'):g}" if leg.get("line") is not None else team
    head = f"{'🟡' if cx.get('lean') else '✅'} Bottom line: {bet}" + (f" ({am})" if am else "") + "."
    if cx.get("lean"):                                       # a lean: its own closer, re-picked under today's rules
        try:                                                 # (sports_breakdown.lean_ends - the coin flip only in band)
            import sports_breakdown as sb
            pool = sb.lean_ends(leg)
            for k in range(len(pool)):
                x = pool[(sum(map(ord, team + str(o))) + k) % len(pool)]
                y, w = wording(x, {**cx, "_rebuilt": True}, leg)
                if y and not w:
                    return y
        except Exception:                                    # noqa: BLE001
            pass
        return head + " No units - just a lean."
    f = _fair(leg) if leg.get("market") == "ml" and leg.get("floor_score") is None else None
    return head + (f" We make 'em {f}, the book's at {am}." if f and am else "")


def wording(line, cx, leg):
    """(the line as it may post, why it changed or '') - the wording-vs-bet and lingo checks."""
    t = str(line or "")
    if not t.strip():
        return t, ""
    whys = []
    bottom = bool(BOTTOM.match(t))
    lead, parts = _sentences(t)
    keep, head_bad = [], False
    for i, s in enumerate(parts):
        why = ""
        s0 = s.strip()
        if bottom and i == 0:                                # ("Bottom line: Celtics (-124)." - the head stays, unless
            if (cx.get("unit") and LEAN_TALK.search(s0)) or (cx.get("lean") and UNIT_TALK.search(s0)) \
                    or (COIN.search(s0) and not coin_ok(cx)):   #  it says the wrong bet: then the whole line is rebuilt)
                whys.append("the bottom line's head says the wrong bet")
                head_bad = True
            keep.append(s)
            continue
        if cx.get("unit") and LEAN_TALK.search(s0):
            why = "a lean's words on a unit play"
        elif cx.get("unit") and COIN.search(s0) and not re.search(r"\bprice\b|\bnumber\b", s0, re.I):
            why = "a coin-flip line on a unit play"          # ("Could go either way." on the 1u Celtics -124)
        elif cx.get("lean") and UNIT_TALK.search(s0):
            why = "a unit play's words on a lean"
        elif cx.get("unit") and (cx.get("units") or 0) >= 1 and SMALL_TALK.search(s0):
            why = "a small bet's words on a play with 1u or more"
            rest = _drop_clause(s0, SMALL_TALK)
            if rest:                                         # (the fact stays, the "half a unit" goes)
                whys.append(why)
                keep.append(rest)
                continue
        elif cx.get("thin") and HYPE.search(s0):
            why = "hype on a thin ½u play"
        elif not cx.get("lean") and SURE.search(s0) and long_dog_cx(cx):
            why = "a blowout / sure-thing call on a long dog"
        elif not cx.get("lock") and LOCK_TALK.search(s0) and not NOT_LOCK.search(s0):
            why = "Lock words on a pick that isn't the Lock"
        elif COIN.search(s0) and not coin_ok(cx):
            why = "a coin flip said of a side that isn't one"
        elif BETTER.search(s0) and cx.get("market") == "ml" and (cx.get("p") or 0.5) < 0.5 \
                and (cx.get("read") or 0.5) < 0.5:
            why = "a 'better team' claim the read doesn't back"   # (the read has them under 50% to win)
            rest = _drop_clause(s0, BETTER)
            if rest:                                         # ("Vikings (6-0) over Lions (4-2) on the record" stays)
                whys.append(why)
                keep.append(rest)
                continue
        elif TAILS.match(s0):
            why = "a canned tail with no fact"
        else:
            new_s, why = _unban(s0)
            if why and new_s:                                # (the fact stays, the frame goes)
                whys.append(why)
                keep.append(new_s)
                continue
        if why:
            whys.append(why)
        else:
            keep.append(s)
    names = [n for n in (leg.get("team"), leg.get("opp")) if n]
    if keep != parts and not any(re.search(r"\d", k) or any(n in k for n in names) or re.search(r".\b[A-Z][a-z]", k.strip())
                                 for k in keep):
        keep = []                                            # (nothing with a fact left: "That's just facts." alone goes)
    out = _join(lead, keep) if keep != parts else t
    if head_bad:
        out = ""
    if bottom:
        out, w2 = _bottom_number(out, leg, cx)
        if w2:
            whys.append(w2)
        if whys and not cx.get("_rebuilt") and (not out or len(_sentences(out)[1]) <= 1 or cx.get("lean")):
            out = bottom_line(leg, cx)                       # (a bottom line is never lost - rebuilt from the facts)
        if cx.get("unit") and out.lstrip().startswith("🟡"):
            out = out.replace("🟡", "✅", 1)
            whys.append("a lean's 🟡 on a unit play's bottom line")
        elif cx.get("lean") and out.lstrip().startswith("✅"):
            out = out.replace("✅", "🟡", 1)
    out2 = _grammar(out, leg)
    if out2 != out:
        out = out2
    if out and FOURTH.search(out) and leg.get("league") in ("nfl", "ncaaf") and not FOURTH_NUM.search(out):
        whys.append("a 4th-down claim with no plays behind it")
        out = ""
    if out and WARM.search(out) and not re.search(r"\d+\s*°|\d+ degrees", out):
        whys.append("a climate claim with no degrees behind it (the 11/12 rule)")
        out = ""
    return out, "; ".join(dict.fromkeys(whys))


def _imp(am):
    """'+130' -> 0.435, '-142' -> 0.587."""
    try:
        x = int(am)
    except (TypeError, ValueError):
        return None
    return 100 / (x + 100) if x > 0 else -x / (-x + 100)


def _bottom_number(t, leg, cx):
    """A unit play's bottom line says OUR number = the units line's (card_fair). A different number is swapped for the
    units line's; a number that is no fair price at all (the raw-gap read - 'We got Tulane at -446' on a +124 dog; the
    book's own price sold as value - 'We price Bruins at -142 - -142 is extra money') takes the clause with it."""
    if not cx.get("unit") or leg.get("market") != "ml":
        return t, ""
    o = leg.get("odds")
    if not isinstance(o, (int, float)):
        return t, ""
    book = f"+{o}" if o > 0 else str(o)
    allx = AM.findall(t)
    nums = [n for n in allx if n != book]
    same_as_book = not nums and allx.count(book) >= 3     # ("Bruins (-142). We price Bruins at -142 - -142 is extra")
    if not nums and not same_as_book:
        return t, ""
    f = _fair(leg) if leg.get("floor_score") is None else None
    if same_as_book:
        return "", "the bottom line sells the book's own price as our number"
    if f and all(n == f for n in nums):
        return t, ""
    if f:
        for n in set(nums):
            t = re.sub(r"(?<![\d.])" + re.escape(n) + r"(?![\d.])", f, t)
        return t, "the bottom line's number wasn't the units line's"
    try:
        import sports_breakdown_v24 as v
        gap = v.FAIR_MAX_GAP
    except Exception:                                        # noqa: BLE001
        gap = 0.15
    need = _imp(book)
    if any(_imp(n) is None or need is None or abs(_imp(n) - need) > gap for n in nums):
        return "", "the bottom line's number is no fair price (too far from the book's)"
    return t, ""


def _grammar(t, leg):
    """'a 8-3 loss' -> 'an 8-3 loss'; 'outscoring teams 23 to 29' -> 'scoring 23 and allowing 29'; "Hawks's the side"."""
    if not t:
        return t
    t = A_AN.sub(lambda m: ("An " if m.group(1) == "A" else "an ") + m.group(2), t)

    def fix(m):
        a, b = int(m.group(3)), int(m.group(4))
        if a > b:
            return m.group(0)
        verb = m.group(1).lower()
        v = {"is": "is", "are": "are", "has": "is", "have": "are", "been": "been"}.get(verb, verb)
        return f"{v} scoring {a} and allowing {b}"
    t = OUTSCORE.sub(fix, t)
    t = re.sub(r"\boutscored teams (\d+) to (\d+)",
               lambda m: m.group(0) if int(m.group(1)) > int(m.group(2)) else f"scored {m.group(1)} and allowed {m.group(2)}", t)

    def poss(m):
        try:
            from sports_breakdown_v24 import vb
            return f"{m.group(1)} {vb(m.group(1), 'are', 'is')} the side"
        except Exception:                                    # noqa: BLE001
            return f"{m.group(1)} are the side"
    return POSS_SIDE.sub(poss, t)


# ---- 2. FACTS vs THE DATA -------------------------------------------------------------------------------------------
FACT_CHECK = True
_FIN = {}


def _finals(games, lg):
    key = (id(games), len(games), lg)
    if key not in _FIN:
        import sports_model as sm
        if len(_FIN) > 12:
            _FIN.clear()
        _FIN[key] = sm.finals(games, lg)
    return _FIN[key]


_TF, _FIN_BEFORE, _IDX = {}, {}, {}


def reset():
    """Forget the game-file caches (a new build: the games dict is updated in place as games go final)."""
    _FIN.clear()
    _TF.clear()
    _FIN_BEFORE.clear()
    _IDX.clear()
    _BOXP.clear()


def _team_index(games, lg):
    """{team id: its finals, oldest first} for one league (once a games dict)."""
    key = (id(games), len(games), lg)
    if key not in _IDX:
        if len(_IDX) > 12:
            _IDX.clear()
        idx = {}
        for x in _finals(games, lg):
            idx.setdefault(x["home"], []).append(x)
            idx.setdefault(x["away"], []).append(x)
        _IDX[key] = idx
    return _IDX[key]


def team_facts(games, leg, which):
    """What the game files say about one side going into this game ('us' / 'them'): the season record (regular season),
    home / road records, the last 5, the streak, the last games, the days since the last one. None = can't check;
    {"unseen": True} = a college team whose games we don't all hold (no record / streak / last-game line may stand)."""
    try:
        import sports_breakdown_v24 as v
    except Exception:                                        # noqa: BLE001
        return None
    g = (games or {}).get(leg.get("game_id"))
    if not g or not g.get("start"):
        return None
    side = leg.get("side")
    if side not in ("home", "away"):
        return None
    if which == "them":
        side = "away" if side == "home" else "home"
    tid, lg = g.get(side), leg.get("league")
    key = (id(games), len(games), g.get("id"), side)
    if key in _TF:
        return _TF[key]
    start = v._t(g["start"])
    if lg in ("ncaaf", "ncaab"):                           # (college: is every game of theirs on file? one list a start
        fk = (id(games), len(games), lg, g["start"])        #  time, so seen_all's season memo hits)
        if fk not in _FIN_BEFORE:
            if len(_FIN_BEFORE) > 64:
                _FIN_BEFORE.clear()
            _FIN_BEFORE[fk] = [x for x in _finals(games, lg) if x["start"] < g["start"]]
        if not v.seen_all(_FIN_BEFORE[fk], tid, start, lg):
            _TF[key] = {"unseen": True}
            return _TF[key]
    s = v._season([x for x in _team_index(games, lg).get(tid, []) if x["start"] < g["start"]], start)
    reg = [x for x in s if str(x.get("stype") or "2") == "2"]
    lines = [v._line(x, tid) for x in s]
    home = [v._line(x, tid) for x in reg if x.get("home") == tid and str(x.get("neutral")) not in ("1", "True", "true")]
    road = [v._line(x, tid) for x in reg if x.get("away") == tid and str(x.get("neutral")) not in ("1", "True", "true")]
    streak = ("", 0)
    if s:
        last = lines[-1][0]
        n = 0
        for x in reversed(lines):
            if x[0] != last:
                break
            n += 1
        streak = (last, n)

    def rec(ls):
        w = sum(x.startswith("W") for x in ls)
        lo = sum(x.startswith("L") for x in ls)
        return (w, lo, len(ls) - w - lo)
    if len(_TF) > 2000:
        _TF.clear()
    _TF[key] = {"rec": {rec([v._line(x, tid) for x in reg]), rec(lines)}, "home": rec(home), "road": rec(road),
                "last5": rec(lines[-5:]), "streak": streak, "lines": lines,
                "rest": v._days(start, v._t(s[-1]["start"])) if s else None, "n": len(s),
                "weeks": (v._week(start) - v._week(v._t(s[-1]["start"]))) if s else None,
                # (11/17 - the breakdown sweep: what the derived-fact checks read)
                "tid": tid, "season": s, "reg": reg,
                "hours": (start - v._t(s[-1]["start"])).total_seconds() / 3600 if s else None}
    return _TF[key]


REC = re.compile(r"(?<![\d.:/+-])(\d{1,3})-(\d{1,3})(?:-(\d{1,2}))?(?![\d%:/]|\.\d|-\d)")
SCORE_AFTER = re.compile(r"^\s*(?:win|loss|victory|beating|final|in overtime|in a shootout|(?:@|vs\.?) (?-i:[A-Z])|\.\s*that'?s what|(?:over|by) (?:the )?(?-i:[A-Z]))", re.I)
SCORE_BEFORE = re.compile(r"(?:(?-i:\b[WL])|\ban?|\bput|\bby|\bbrakes off [\w.' ]+,|"
                          r"(?:smacked|spanked|clapped|embarrassed|cooked|buried|beat|took|blanked|whipped|handled|lost to|fell to|loss to|win over|won over) [\w.' ]{0,30}?|"
                          r"\bwon|\blost|\bended)\s*$", re.I)
SCORE_VERB = re.compile(r"spank|smack|\bbeat\b|beat the brakes|clapped|embarrass|\bput\b|did to|cooked|buried|"
                        r"\btook\b|\bwin over\b|\bloss to\b|\bwon\b|\blost\b|beating", re.I)
NO_CHECK = re.compile(r"last (?:season|year)|a year ago|year ago|since 20\d\d|these two met|all-time|\bATS\b|against the "
                      r"spread|as a dog|as a favorite|\bin (?:one|two)-score|\bh2h\b|head[- ]to[- ]head|last meeting|"
                      r"\bseries\b|\bbowl\b|\bcareer\b|\bstarts?\b|\bsave %|\bTDs?\b|\bpicks?\b|\byards\b|minutes|per 48|"
                      r"\bsince\b|\bquarter\b|\bperiods?\b|rated above", re.I)
HOME_W = re.compile(r"at home|home this|home so far|their (?:own )?building|in the crib|protects? the crib|"
                    r"takes care of home|home cooking|own building|\bhome\b", re.I)
ROAD_W = re.compile(r"on the road|road this|away from home|road game|other people'?s|\broad\b|\baway\b", re.I)
LAST5_W = re.compile(r"last (?:5|five)\b|of the last 5|of their last 5", re.I)
STREAK_W = re.compile(r"(?:(\d+) straight (?:W'?s|wins|Ws)\b|won (\d+) (?:straight|in a row)|(\d+) wins in a row|"
                      r"(\d+)-game heater|can'?t stop winning:? (\d+) straight|🔥 (\d+) straight for|"
                      r"(?:have|has) won (\d+) straight)", re.I)
STREAK_L = re.compile(r"(?:(?:dropped|lost) (\d+) (?:straight|in a row)|(\d+) straight L'?s|(\d+) losses in a row|"
                      r"(\d+) L'?s in a row|taking L'?s\W+(\d+) straight|lost (\d+) straight)", re.I)
REST_W = re.compile(r"(\d+) days?(?: of)?(?: rest| off|' rest)?\b", re.I)
BYE_W = re.compile(r"\bbye\b", re.I)
LASTGAME = re.compile(r"last time out|last outing|previous game|latest|fresh off|last game for each|most recent|"
                      r"how they came in|where they'?re coming from|\bjust took\b|\bjust beat\b|\bcome(?:s)? in off\b|"
                      r"\boff a\b|\bafter a\b|last played|last one|took an? L last time|last time\b|"
                      r"both (?:won|took an L|coming off|sides are coming off)|both coming off", re.I)


def _spans(text, names):
    """[(start, end, index)] of every team name in the text - a name inside a longer one ('Michigan' in 'C Michigan')
    doesn't count."""
    sp = []
    for i, n in enumerate(names):
        if n:
            sp += [(m.start(), m.end(), i) for m in re.finditer(r"(?<![\w])" + re.escape(n) + r"(?![\w])", text)]
    return [x for x in sp if not any(y[0] <= x[0] and x[1] <= y[1] and (y[1] - y[0]) > (x[1] - x[0]) for y in sp)]


def _anchor(text, pos, names):
    """The team (index into names) a fact at `pos` is about: the nearest name before it, else the nearest after."""
    sp = _spans(text, names)
    before = [x for x in sp if x[1] <= pos]
    if before:
        return max(before, key=lambda x: x[1])[2]
    after = [x for x in sp if x[0] >= pos]
    return min(after, key=lambda x: x[0])[2] if after else None


def _rs(r):
    return f"{r[0]}-{r[1]}" + (f"-{r[2]}" if r[2] else "")


def facts(line, leg, games):
    """'' when every checkable fact in the line matches the game files, else why it doesn't."""
    if not FACT_CHECK or not games:
        return ""
    t = str(line or "")
    if not t.strip() or BOTTOM.match(t) and not REC.search(t):
        return ""
    if t.lstrip().startswith(("🚑", "🔄", "🧯", "🤒", "📣", "🌟")):   # (who's out / the news - checked elsewhere)
        return ""
    us, them = leg.get("team") or "", leg.get("opp") or ""
    names = [us, them]
    fx = {}

    def F(i):
        if i not in fx:
            fx[i] = team_facts(games, leg, "us" if i == 0 else "them")
        return fx[i]
    if BYE_W.search(t) and leg.get("league") in ("nfl", "ncaaf"):      # (11/16: a bye is a whole week with no game)
        i = _anchor(t, BYE_W.search(t).start(), names)
        f = F(i) if i is not None else None
        if f and not f.get("unseen") and f.get("weeks") is not None and f["weeks"] < 2:
            return f"says a bye for {names[i]} - their last game was {f['rest']} days back, the week before this one"
    if NO_CHECK.search(t):
        return ""
    # streaks
    for rx, kind in ((STREAK_W, "W"), (STREAK_L, "L")):
        for m in rx.finditer(t):
            n = int(next(x for x in m.groups() if x))
            i = _anchor(t, m.start(), names)
            if i is None:
                continue
            f = F(i)
            if not f:
                continue
            if f.get("unseen"):
                return f"a streak for {names[i]}, whose games we don't all hold"
            if f["streak"] != (kind, n):
                real = f"{'won' if f['streak'][0] == 'W' else 'lost'} {f['streak'][1]}" if f["streak"][1] else "no games"
                return f"says {names[i]} {'won' if kind == 'W' else 'lost'} {n} straight - the games say {real}"
    # last 5
    m5 = re.search(r"(\d) of (?:the|their) last (?:5|five)", t)
    if m5:
        i = _anchor(t, m5.start(), names)
        f = F(i) if i is not None else None
        if f and not f.get("unseen") and f["n"] >= 5:
            w, lo, _ = f["last5"]
            n = int(m5.group(1))
            won = re.search(r"\bwon\b|went [\w.' ]+ way|in their favor", t, re.I)
            if (won and n != w) or (re.search(r"dropped|lost", t[:m5.end() + 5], re.I) and n != lo):
                return f"says {n} of the last 5 for {names[i]} - the games say {w}-{lo}"
    # records + scores
    recs = []
    for m in REC.finditer(t):
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        before, after = t[:m.start()], t[m.end():]
        if a == b == 50:                                     # ("close to 50-50" is no record)
            continue
        paren = before.rstrip().endswith("(") or re.match(r"\s*\)", after) is not None and before[-1:] == "("
        if re.search(r"\($", before) and re.match(r"(?:-\d+)?\)", after):
            kind = "rec"                                     # ("Wild (8-5) won 2 in a row" - a record in parens)
        elif re.match(r"\s*(?:team|overall|on the (?:year|season)|this (?:year|season)|record|apiece|squad)", after, re.I):
            kind = "rec"                                     # ("A 3-8 team")
        elif SCORE_AFTER.search(after[:20]) or SCORE_BEFORE.search(before[-45:]) or (max(a, b) > 30 and leg.get("league") != "mlb") \
                or (SCORE_VERB.search(t) and not re.search(r"\b(?:is|are|sit|sits|come in|comes in|at|record)\s*$", before)
                    and not re.match(r"\s*(?:at home|on the road|away|in their|for\b|,|;|\.|\s*$| vs \d| against \d| to \d| to \w+'? \d)", after)):
            #   (11/15 audit: " to \d" - "💪 2-2 to 0-5. Oakland about to get their ass beat." is two RECORDS; the "beat"
            #    made the first one a score, "a 2-2 score that isn't in their last 6 games", and a true line was dropped)
            kind = "score"
        else:
            kind = "rec"
        del paren
        recs.append((m, a, b, c, kind, before, after))
    bare = [r for r in recs if r[4] == "rec" and _anchor(r[5], len(r[5]), names) is None]
    for k_, r in enumerate(recs):
        m, a, b, c, kind, before, after = r
        i = _anchor(t, m.start(), names)
        mm = re.match(r"\s*(?:\(|for (?:the )?)(" + "|".join(re.escape(n) for n in names if n) + r")\b", after)
        ms = re.match(r"\s*(?:win over|loss to|victory over|beating from|tie with) (?:the )?[\w.'& -]{2,30}? for (?:the )?("
                      + "|".join(re.escape(n) for n in names if n) + r")\b", after) if kind == "score" else None
        if mm and kind == "rec":                             # ("10-6 for Mammoth", "2-1 (Elon)")
            i = names.index(mm.group(1))
        elif ms:                                             # (11/17: "a 38-21 loss to the Cowboys for Eagles, a 23-17 loss
            i = names.index(ms.group(1))                     #  to the 49ers for Commanders" - the score is the team's AFTER it)
        elif kind == "rec" and r in bare and len(bare) == 2 and not mm:
            i = bare.index(r)                                # ("💪 7-6 vs 2-7" / "(5-2 / 4-3)" - ours first)
        if i is None:
            continue
        f = F(i)
        if not f:
            continue
        if f.get("unseen"):
            return f"a record / score for {names[i]}, whose games we don't all hold"
        if kind == "rec":
            seg = t[max(0, m.start() - 45):m.end() + 40]
            if LAST5_W.search(seg) or re.search(r"over their last|lately|in their last|last \d+ games", seg, re.I):
                if LAST5_W.search(seg) and f["n"] >= 5 and (a, b) != f["last5"][:2]:
                    return f"says {names[i]} {a}-{b} in the last 5 - the games say {f['last5'][0]}-{f['last5'][1]}"
                continue
            if HOME_W.search(seg) and not ROAD_W.search(seg):
                if (a, b, c) != f["home"] and not (c == 0 and (a, b) == f["home"][:2]):
                    return f"says {names[i]} {a}-{b}" + (f"-{c}" if c else "") + f" at home - the games say {_rs(f['home'])}"
                continue
            if ROAD_W.search(seg) and not HOME_W.search(seg):
                if (a, b, c) != f["road"] and not (c == 0 and (a, b) == f["road"][:2]):
                    return f"says {names[i]} {a}-{b}" + (f"-{c}" if c else "") + f" on the road - the games say {_rs(f['road'])}"
                continue
            if HOME_W.search(seg) or ROAD_W.search(seg):
                continue
            if (a, b, c) not in f["rec"]:
                return f"says {names[i]} {a}-{b}" + (f"-{c}" if c else "") + f" - the games say {_rs(sorted(f['rec'])[0])}"
        else:
            win = max(a, b), min(a, b)

            def sc(x):
                return tuple(sorted(map(int, x.split()[1].split("-")), reverse=True))
            got = [x for x in f["lines"][-6:] if sc(x) == win]
            if LASTGAME.search(before[-80:] + after[:30]) and not re.search(r"last 5|within|inside|in one of|not long ago", t, re.I):
                lastg = f["lines"][-1:]
                if not [x for x in lastg if sc(x) == win]:
                    return f"says {names[i]}'s last game ended {a}-{b} - the games say {lastg[0] if lastg else 'none'}"
            elif not got:
                return f"a {a}-{b} score for {names[i]} that isn't in their last 6 games"
    # rest days
    if re.search(r"\brest\b|days? off|between games|days since|days ago", t, re.I) and not re.search(r"extra|more days|fewer", t, re.I):
        for m in REST_W.finditer(t):
            i = _anchor(t, m.start(), names)
            f = F(i) if i is not None else None
            if not f or f.get("unseen") or f.get("rest") is None:
                continue
            n = int(m.group(1))
            if n not in (f["rest"], f["rest"] - 1) and not re.search(r"both", t[:m.start()], re.I):
                return f"says {names[i]} had {n} days - the games say {f['rest'] - 1}-{f['rest']}"
    return ""


# ---- 4. WHO PLAYS ----------------------------------------------------------------------------------------------------
WHO_CHECK = True
QB_STAT = re.compile(r"\d+ TDs?, \d+ picks? and [\d,]+ yards")
GOALIE_STAT = re.compile(r"save %")
GOALIE_HEDGE = re.compile(r"project|not confirmed|last time out|last starter|if he goes again|expected in net|"
                          r"expected to start|confirmed in net|in net last", re.I)
WHO_GAMES = 8                   # a team's quarterbacks / goalies = the starters of its last 8 box scores


def _recent_starters(rows, team, before, n=WHO_GAMES):
    names, seen = [], set()
    for r in reversed(rows):
        if str(r.get("team")) != str(team) or r.get("start", "") >= before:
            continue
        if r.get("gid") not in seen:
            seen.add(r.get("gid"))
            if len(seen) > n:
                break
        if r["player"] not in names:
            names.append(r["player"])
    return names


GOALIE_SURE_FROM = "2026-11-17"   # 🥅 11/17 THE BREAKDOWN SWEEP: on the 11/1-11/16 cards 18 of the 51 goalie lines with a
#   save % named a man who did NOT start that night - "in net last time out" 11 of 26 wrong, "projected, not confirmed"
#   3 of 13, said flat 4 of 12. A hedge doesn't make a guess true: from the 11/18 games a goalie's numbers show on a card
#   only once the goalie page has CONFIRMED him (the line is kept on the card and shown the minute he's confirmed), and a
#   played game's card only keeps the man the box score says started. Quarterbacks the same once the box score is in.
_STARTED, _BOXP = {}, {}


def started(lg, gid):
    """{team id: the quarterback / goalie the box score says started this game} ({} = no box score yet)."""
    try:
        import sports_players as sp
        rows = sp.CACHE.get(lg) or []
        if not rows and not _STARTED.get("loaded"):
            _STARTED["loaded"] = True
            sp.CACHE.update(sp.load())
            rows = sp.CACHE.get(lg) or []
    except Exception:                                        # noqa: BLE001
        return {}
    key = (lg, id(rows), len(rows))
    if key not in _STARTED:
        idx = {}
        for r in rows:
            if r.get("role", "") in ("QB", "G", ""):
                idx.setdefault(r.get("gid"), {}).setdefault(str(r.get("team")), r.get("player"))
        _STARTED[key] = idx
    return _STARTED[key].get(gid) or {}


def box_played(lg, gid, team):
    """The men who PLAYED in a finished game for one team, by the box score (None = no box score on file)."""
    if lg not in _BOXP:
        by = {}
        try:
            import sports_absences as sa
            for tid, gs in sa._games(lg).items():
                for _, g_, rs in gs[-12:]:
                    for r in rs:
                        if lg in ("nba", "ncaab"):           # (hoops lists the whole bench: only a man with minutes)
                            m = re.search(r'"minutes":"(\d+)', r.get("stats") or "")
                            if not m or int(m.group(1)) <= 0:
                                continue
                        by.setdefault((g_, str(tid)), set()).add(sa._nm(r["player"]))
        except Exception:                                    # noqa: BLE001
            by = {}
        _BOXP[lg] = by
    return _BOXP[lg].get((gid, str(team)))


def played(leg, name, games):
    """True when a man the card lists out is in this game's box score - he played (a finished game only)."""
    g = (games or {}).get(leg.get("game_id"))
    if not g or g.get("status") != "final":
        return False
    try:
        import sports_absences as sa
        for side in ("home", "away"):
            pool = box_played(leg.get("league"), g.get("id"), g[side])
            if pool and sa.match(name, pool):
                return True
    except Exception:                                        # noqa: BLE001
        pass
    return False


OUT_SAID = re.compile(r"\bout\b|\bwithout\b|\bmissing\b|\bdown\b|won'?t suit up|not dressing|\bno\b|gotta play", re.I)


def played_anyway(line, leg, games):
    """'' or why not: a graded card's line that lists a man OUT who is in the game's box score."""
    t = str(line or "")
    if not t.lstrip().startswith(("🚑", "⚠️", "🌟")) or not OUT_SAID.search(t):
        return ""
    g = (games or {}).get(leg.get("game_id"))
    if not g or g.get("status") != "final":
        return ""
    head = re.split(r"questionable:", t, flags=re.I)[0]
    if t.lstrip().startswith("🌟") and " · " in t:           # ("X is in the lineup tonight · Y is out" - the out part)
        head = t.split(" · ", 1)[1]
    for nm in _card_names(list(leg.get("outs") or []) + list(leg.get("absent") or []) + list(leg.get("opp_outs") or [])):
        if nm in head and played(leg, nm, games):
            return f"{nm} listed out - the box score says he played"
    return ""


def who_plays(line, leg, games, where="render"):
    """'' when the line may stand, else why not: a quarterback's numbers for a man the engine can't call the starter, a
    goalie's numbers with nobody confirming him (GOALIE_SURE_FROM), and - once the box score is in - numbers for a man
    who didn't start. Only for lines that carry the man's numbers."""
    if not WHO_CHECK or not games:
        return ""
    t = str(line or "")
    lg = leg.get("league")
    is_qb = lg in ("nfl", "ncaaf") and QB_STAT.search(t)
    is_g = lg == "nhl" and GOALIE_STAT.search(t)
    if not (is_qb or is_g):
        return ""
    g = games.get(leg.get("game_id"))
    if not g or not g.get("start"):
        return ""
    pre = g.get("status") == "pre"
    try:
        import sports_players as sp
        box = started(lg, g.get("id")) if not pre else {}
        rows = sp.CACHE.get(lg) or []
    except Exception:                                        # noqa: BLE001
        return ""
    if not rows:
        return ""
    if box:                                                  # the game's on / over: the man who really started
        for side in ("home", "away"):
            real = box.get(str(g[side]))
            for nm in _recent_starters(rows, g[side], g["start"], n=15):
                if real and nm in t and sd._plain(real) != sd._plain(nm):
                    return f"{nm}'s numbers on the card for {g.get(side + '_name')} - {real} started"
        return ""
    if is_qb:
        if not pre:
            return ""
        try:
            import sports_qb
        except Exception:                                    # noqa: BLE001
            return ""
        if g["start"][:10] < sports_qb.QB_CHART_FROM:
            return ""
        for side in ("home", "away"):
            c = None
            for nm in _recent_starters(rows, g[side], g["start"]):
                if nm not in t:
                    continue
                c = c or sports_qb.call(rows, lg, g[side], g["start"], team_name=g.get(side + "_name") or "")
                if not c["name"] or not sports_qb.same(c["name"], nm):
                    why = {"out": "he's ruled out", "questionable": "he's questionable", "change": "the starter changed",
                           "chart disagrees": "the depth chart has another man first"}.get(c["how"], "unknown")
                    return f"a quarterback's numbers for {nm}, who the engine can't call {g.get(side + '_name')}'s starter ({why})"
        return ""
    sure = g["start"][:10] >= GOALIE_SURE_FROM
    hedged = bool(GOALIE_HEDGE.search(t))
    if hedged and (not sure or where == "pre-post"):         # (a card being written keeps the line - the page shows it
        return ""                                            #  the minute the goalie page confirms him)
    if not pre and not sure:
        return ""
    try:
        import sports_goalies
    except Exception:                                        # noqa: BLE001
        return ""
    for side in ("home", "away"):
        for nm in _recent_starters(rows, g[side], g["start"], n=15):
            if nm not in t:
                continue
            if nm in (leg.get("confirmed") or []):
                continue
            conf = sports_goalies.confirmed(g.get("id"), side) if pre else None
            if not conf or sd._plain(conf.get("name")).split()[-1:] != sd._plain(nm).split()[-1:]:
                return (f"{nm}'s numbers on the card for the {g.get(side + '_name')} with nobody confirming him in net"
                        if hedged else
                        f"{nm} said as tonight's goalie for the {g.get(side + '_name')} with nobody confirming him")
    return ""


# ---- 5. DERIVED FACTS + SENSE (11/17 - THE BREAKDOWN SWEEP) -----------------------------------------------------------
# The owner, 11/17: "My buddy keeps complaining about the breakdowns and says they make no sense and false, outdated
# information of injuries and stuff ... make sure that these breakdowns are always accurate and up to date." The fact
# check above re-reads records / streaks / last scores / rest days. These re-read every OTHER number a card says off the
# game files - points a game (lately and on the year), who played last night, the road-trip count, the last meeting -
# and catch a line that says nothing or contradicts the rest of its card. Same rule: a line that fails comes off.
DERIVED_CHECK = True
_NUM = re.compile(r"(?<![\w.,])[+-]?\d+(?:\.\d+)?(?![\w]|\.\d|,\d)")
PER_GAME = re.compile(r"\ba game\b(?!-)|\bfor ?[,/] ?\d|\d+ for,? ", re.I)
LAST_N = re.compile(r"\blast (\d)\b|\blately\b", re.I)
ON_YEAR = re.compile(r"this (?:year|season)|on the (?:year|season)", re.I)
NOT_STATS = re.compile(r"%|\bTDs?\b|per 48|minutes|\bmin a night|last (?:season|year)|a year ago|\bshots?\b|points? better|"
                       r"\bwent \d|per game\)|\d-\d|rebound|turnover|assist|\byards\b|\bsacks?\b|\bglass\b|free throws?|"
                       r"\b3s\b|threes|three-point|possessions|\bpace\b|penalt|power play|face-?off", re.I)
EVEN_PAIR = re.compile(r"(\d+(?:\.\d+)?) for(?: /|,)? (\d+(?:\.\d+)?) against")   # ("4 for / 4 against; ... 3 for / 3 against")
REST_TALK = re.compile(r"extra day|\bdays? off\b|\bdays?(?: of)? rest\b|fresher legs|fresh legs|better rested|more rest\b|"
                       r"well[- ]rested|\brested\b|more days off", re.I)
ZERO_NET = re.compile(r"(?<![\d.])[+-]0(?:\.0)?(?![\d.])")
H2H_W = re.compile(r"last time these two met|the last meeting|these two already (?:met|played)|^🆚", re.I)
H2H_GARBLE = re.compile(r"\bgot [\w.' ]+ last time these two met, an? \d+-\d+ loss to\b")
_TEAM_RX = r"([A-Z][\w.'&-]*(?: [A-Z0-9][\w.'&-]*){0,3}?)"
B2B_SAID = re.compile(r"(?:\b[Tt]he )?" + _TEAM_RX + r" (?:played|were on the ice) (?:last night|yesterday)|"
                      r"[Ss]econd night (?:in a row|of a back-to-back) for (?:the )?" + _TEAM_RX + r"(?=[,. ]|$)|"
                      r"(?:\b[Tt]he )?" + _TEAM_RX + r" (?:is |are )?on a back-to-back")
B2B_ANY = re.compile(r"played (?:last night|yesterday)|on the ice last night|second night (?:in a row|of a back-to-back)|"
                     r"on a back-to-back", re.I)
ROAD_NTH = re.compile(r"(\d)(?:st|nd|rd|th) road game in 6 days")
ROAD_N = re.compile(r"(\d) road games in (?:the last )?6 days")
_HOOPS_NO = r"(?<!field )\bgoals?\b|\bpucks?\b|\bin net\b(?! rating| margin| points)|\bgoalies?\b|\btouchdowns?\b|\bquarterbacks?\b|\binnings?\b|\bsave %"
_FB_NO = r"\bpucks?\b|\bin net\b|\bgoalies?\b|\bsave %|\binnings?\b|\bgoals a game\b"
SPORT_WORDS = {   # a word from another sport on a card (a quoted headline is left alone)
    "nba": _HOOPS_NO, "ncaab": _HOOPS_NO, "nfl": _FB_NO, "ncaaf": _FB_NO,
    "nhl": r"\btouchdowns?\b|\bquarterbacks?\b|\bpoints a game\b|\binnings?\b|\bunder center\b",
    "mlb": r"\bpucks?\b|\bin net\b|\bgoalies?\b|\btouchdowns?\b|\bquarterbacks?\b|\bsave %"}
HEALTHY = re.compile(r"^✅ .*(?:healthy|[Ff]ull squad|everybody available|full strength|[Nn]obody big missing|"
                     r"[Nn]obody on .* injury report|nobody important sitting)")
GO_WITHOUT = re.compile(r"\b(?:go|goes|going|play|plays) without\b|\bis out\b|\bare out\b|\bwon'?t suit up\b", re.I)


def _strip_names(t, names):
    for n in sorted((x for x in names if x), key=len, reverse=True):
        t = t.replace(n, " ")
    return t


def stats(line, leg, games):
    """'' when every scoring number in a points-a-game line is what the game files say, else why not - the breakdown's
    own arithmetic (sports_breakdown_v24._pts3 / _per_game) on the games before this one."""
    if not DERIVED_CHECK or not games:
        return ""
    t = str(line or "")
    if not PER_GAME.search(t) or NOT_STATS.search(t) or '"' in t or "“" in t:
        return ""
    lastn, year = LAST_N.search(t), ON_YEAR.search(t)
    if not (lastn or year) or (lastn and year) or (lastn and lastn.group(1) and lastn.group(1) not in "23"):
        return ""                                            # (the pool says the last 3 - or 2, early in a season)
    try:
        import sports_breakdown_v24 as v
    except Exception:                                        # noqa: BLE001
        return ""
    us, them = leg.get("team") or "", leg.get("opp") or ""
    if us not in t and them not in t:
        return ""
    ok = set()
    for which in ("us", "them"):
        f = team_facts(games, leg, which)
        if not f:
            return ""
        if f.get("unseen"):
            return f"points a game for {us if which == 'us' else them}, whose games we don't all hold"
        tid = f["tid"]
        if lastn:
            for gs in (f["season"], f["reg"]):
                for n in (3, 2):
                    for p in (v._pts3(gs, tid, n), v._pts3(gs, tid, n, 1)):
                        if p:
                            ok |= {float(p[0]), float(p[1]), round(abs(p[0] - p[1]), 1), float(p[2])}
        else:
            for gs in (f["reg"], f["season"]):
                pg = v._per_game(gs, tid)
                if pg:
                    ok |= {float(round(pg[0])), float(round(pg[1])), round(pg[0], 1), round(pg[1], 1)}
    body = _strip_names(t, [us, them])
    bad = [x for x in (abs(float(y)) for y in _NUM.findall(body)) if not any(abs(x - y) < 0.051 for y in ok)]
    if bad:
        return f"says {bad[0]:g} a game - the game files say otherwise"
    return ""


def sense(line, leg):
    """'' when the line says something, else why it doesn't: a "+0 a game" margin, the garbled last-meeting knock, a word
    from another sport."""
    if not DERIVED_CHECK:
        return ""
    t = str(line or "")
    if PER_GAME.search(t) and ZERO_NET.search(t):
        return "a +0 margin - a number that says nothing"
    if H2H_GARBLE.search(t):
        return "the last-meeting line is garbled (who lost to whom)"
    ev = EVEN_PAIR.findall(t)
    if len(ev) >= 2 and all(a == b for a, b in ev):
        return "both sides dead even on the scoreboard - a line that says nothing"
    rx = SPORT_WORDS.get(leg.get("league"))
    if rx and '"' not in t and "“" not in t and not t.lstrip().startswith(("🧯", "📣")):
        m = re.search(rx, t, re.I)
        if m:
            return f"a word from another sport ('{m.group(0).lower()}')"
    return ""


def _who(name, leg):
    """0 (us) / 1 (them) / None for a team name as a line says it."""
    n = str(name or "").strip()
    for i, x in enumerate((leg.get("team") or "", leg.get("opp") or "")):
        if x and (n == x or n.endswith(" " + x)):
            return i
    return None


def played_last_night(line, leg, games):
    """'' when a back-to-back line names the team that really played last night (inside sports_breakdown_v24.B2B_HOURS
    of this start, by the game files), else why not."""
    if not DERIVED_CHECK or not games:
        return ""
    t = str(line or "")
    if not B2B_ANY.search(t) or '"' in t:
        return ""
    try:
        import sports_breakdown_v24 as v
    except Exception:                                        # noqa: BLE001
        return ""
    fs = [team_facts(games, leg, w) for w in ("us", "them")]
    if any(f is None for f in fs):
        return ""
    names = [leg.get("team") or "", leg.get("opp") or ""]
    if any(f.get("unseen") for f in fs):
        return "a back-to-back for a team whose games we don't all hold"
    b2b = [f.get("hours") is not None and f["hours"] <= v.B2B_HOURS for f in fs]
    said = set()
    for m in B2B_SAID.finditer(t):
        i = _who(next(x for x in m.groups() if x), leg)
        if i is not None:
            said.add(i)
    if not said:                                             # (no team we can pin it on: somebody has to have played)
        return "" if any(b2b) else "says a back-to-back - neither team played last night"
    for i in sorted(said):
        if not b2b[i]:
            h = fs[i].get("hours")
            return (f"says {names[i]} played last night - their last game was "
                    f"{'%.0f hours' % h if h is not None else 'not on file'} before this one")
    return ""


def rest_talk(line, leg, games):
    """'' or why not: REST TALK ONLY ON A BACK-TO-BACK in the every-other-night leagues (11/15, Victor: "Both teams rested
    lol" - sports_breakdown_v24.REST_B2B_ONLY). The breakdown stopped writing it 11/15; this takes it off a card that
    already had it ("Flyers got the extra day: 3 days off to Blue Jackets' 2 days") - no back-to-back, no rest line."""
    if not DERIVED_CHECK or not games:
        return ""
    t = str(line or "")
    if not REST_TALK.search(t) or B2B_ANY.search(t) or '"' in t:
        return ""
    try:
        import sports_breakdown_v24 as v
    except Exception:                                        # noqa: BLE001
        return ""
    if leg.get("league") not in v.REST_B2B_ONLY:
        return ""
    fs = [team_facts(games, leg, w) for w in ("us", "them")]
    if any(f is None or f.get("unseen") for f in fs):
        return ""
    if any(f.get("hours") is not None and f["hours"] <= v.B2B_HOURS for f in fs):
        return ""
    return "rest talk with no back-to-back"


def road_trip(line, leg, games):
    """'' when "3rd road game in 6 days" / "3 road games in 6 days" matches the schedule (sports_context._travel's
    count), else why not."""
    if not DERIVED_CHECK or not games:
        return ""
    t = str(line or "")
    m1, m2 = ROAD_NTH.search(t), ROAD_N.search(t)
    if not (m1 or m2):
        return ""
    try:
        import sports_breakdown_v24 as v
    except Exception:                                        # noqa: BLE001
        return ""
    m = m1 or m2
    names = [leg.get("team") or "", leg.get("opp") or ""]
    i = _anchor(t, m.start(), names)
    if i is None:
        i = 1
    f = team_facts(games, leg, "us" if i == 0 else "them")
    g = games.get(leg.get("game_id"))
    if not f or f.get("unseen") or not g:
        return ""
    tid, start = f["tid"], v._t(g["start"])
    side = leg.get("side") if i == 0 else ("away" if leg.get("side") == "home" else "home")
    neutral = str(g.get("neutral")) in ("1", "True", "true")
    n = 0
    for x in reversed(_team_index(games, leg.get("league")).get(tid, [])):
        if x["start"] >= g["start"]:
            continue
        if (start - v._t(x["start"])).total_seconds() > 6 * 86400:
            break
        n += x["away"] == tid and str(x.get("neutral")) not in ("1", "True", "true")
    if m1:
        if side != "away" or neutral:
            return f"says a road game for {names[i]} - they're not the road team"
        n += 1
    said = int(m.group(1))
    if said != n:
        return f"says {said} road games in 6 days for {names[i]} - the schedule says {n}"
    return ""


def last_meeting(line, leg, games):
    """'' when a last-meeting line's score (and who won it) is the last game these two played, else why not."""
    if not DERIVED_CHECK or not games:
        return ""
    t = str(line or "")
    if not H2H_W.search(t) or '"' in t:
        return ""
    f = team_facts(games, leg, "us")
    g = games.get(leg.get("game_id"))
    if not f or not g or f.get("unseen"):
        return ""
    tid = f["tid"]
    oid = g["away"] if g["home"] == tid else g["home"]
    met = [x for x in _team_index(games, leg.get("league")).get(tid, []) if x["start"] < g["start"]
           and oid in (x["home"], x["away"])]
    if not met:
        return "a last meeting the game files don't have"
    m = REC.search(t)
    if not m:
        return ""
    last = met[-1]
    hs, as_ = int(last["home_score"]), int(last["away_score"])
    if {int(m.group(1)), int(m.group(2))} != {hs, as_} and not re.search(r"this year|head to head", t, re.I):
        return f"says the last meeting ended {m.group(1)}-{m.group(2)} - the game files say {max(hs, as_)}-{min(hs, as_)}"
    we_won = (hs > as_) == (last["home"] == tid)
    us, them = re.escape(leg.get("team") or ""), re.escape(leg.get("opp") or "")
    if re.search(rf"{them} (?:got|beat) (?:the )?{us}", t) and we_won:
        return "says they won the last meeting - we did"
    if re.search(rf"{us} (?:got|beat) (?:the )?{them}|{us} took an? \d+-\d+ win", t) and not we_won:
        return "says we won the last meeting - they did"
    return ""


def derived(line, leg, games):
    """Every derived-fact check on one line: '' or the first reason it can't stand."""
    for fn in (stats, played_last_night, rest_talk, road_trip, last_meeting):
        try:
            w = fn(line, leg, games)
        except Exception as e:                               # noqa: BLE001 - a check that breaks never drops a line
            print(f"card check ({fn.__name__}) failed: {str(e)[:80]}", flush=True)
            w = ""
        if w:
            return w
    return ""


def _card_names(entries):
    out = []
    for x in entries or []:
        s = str(x or "").split(" (")[0].replace(" questionable", "").strip()
        w = s.split()
        if len(w) > 2 and w[0].isupper() and len(w[0]) <= 3:
            s = " ".join(w[1:])
        if s:
            out.append(s)
    return out


def card_sense(leg, lines):
    """What on a card contradicts the rest of it: {line: why}. A "full squad" line beside the card's own list of that
    side's men out; a man named out for the WRONG team; a star "in the lineup" the same card lists out."""
    bad = {}
    if not DERIVED_CHECK:
        return bad
    us, them = leg.get("team") or "", leg.get("opp") or ""
    gone_ = set(leg.get("stale") or [])
    ours = [n for n in _card_names(list(leg.get("outs") or []) + list(leg.get("absent") or [])) if n not in gone_]
    theirs = [n for n in _card_names(leg.get("opp_outs")) if n not in gone_]
    strs = [str(x) for x in lines or [] if isinstance(x, str)]
    body = " ".join(strs)
    us_out_said = any(x.startswith(("⚠️", "🚑", "🌟")) and us in x and GO_WITHOUT.search(x) for x in strs)
    for x in strs:
        if HEALTHY.search(x) and us in x and (us_out_said or any(n in body for n in ours)):
            bad[x] = f"says {us} are at full strength - the same card lists their men out"
        elif x.startswith("🚑") and not x.startswith(f"🚑 {us}") and them in x and us not in x:
            wrong = [n for n in ours if n in x and n not in theirs]
            if wrong:
                bad[x] = f"lists {wrong[0]} out for {them} - he's {us}'s man"
        elif x.startswith("🌟") and "in the lineup" in x:
            gone = [n for n in ours + theirs if n in x.split(" · ")[0].split("in the lineup")[0]]
            if gone:
                bad[x] = f"says {gone[0]} is in the lineup - the same card lists him out"
    return bad


# ---- the whole card ---------------------------------------------------------------------------------------------------
def _dupe(x, seen):
    k = re.sub(r"\W+", " ", str(x)).strip().lower()
    if k in seen:
        return True
    seen.add(k)
    return False


_INJ_WORDS = {"out", "for", "missing", "without", "is", "are", "the", "not", "dressing", "won't", "wont", "suit", "up",
              "go", "goes", "on", "injury", "report", "sitting", "sit", "and", "won", "t", "will", "be", "tonight"}


def chip_repeat(line, leg):
    """A 🚑 line about the other side whose every name is already in the card's '🚑 X missing:' chip."""
    t = str(line or "")
    opp = leg.get("opp") or ""
    if not t.lstrip().startswith("🚑") or not opp or opp not in t or "questionable" in t.lower():
        return False
    chip = " ".join(leg.get("opp_outs") or [])
    if not chip:
        return False
    body = re.sub(r"\([^)]*\)", " ", t.replace(opp, " "))
    toks = [w for w in re.findall(r"[A-Za-z][\w.'-]*", body) if w.lower().strip(".") not in _INJ_WORDS]
    have = set(re.findall(r"[A-Za-z][\w.'-]*", re.sub(r"\([^)]*\)", " ", chip)))
    return bool(toks) and all(w.strip(".") in have or w in have for w in toks)


def check(pk, leg, lines, games=None, why="", where="render"):
    """The card's lines as they may post: every line through the wording / lingo checks and the fact check, the same
    line never twice (nor the one-liner again), a 🚑 line that only repeats the card's 'missing' chip gone. Logs what it
    caught (CAUGHT, the run log, data/sports/pick_audit.json via save)."""
    cx = ctx_of(pk, leg)
    out, seen = [], set()
    if why:
        _dupe(why, seen)
    try:                                                     # (11/17: a line that contradicts the rest of its card)
        contra = card_sense(leg, lines)
    except Exception:                                        # noqa: BLE001
        contra = {}
    for x in lines or []:
        if not isinstance(x, str):
            out.append(x)
            continue
        new, w = wording(x, cx, leg)
        if new and not BOTTOM.match(new):
            fw = facts(new, leg, games)
            if fw:
                new, w = "", "; ".join(y for y in (w, "a fact the game files don't back: " + fw) if y)
        if new:
            pw = who_plays(new, leg, games, where) or played_anyway(new, leg, games)
            if pw:
                new, w = "", "; ".join(y for y in (w, pw) if y)
        if new and not BOTTOM.match(new):                   # (11/17: the derived facts + the sense check)
            dw = sense(new, leg) or derived(new, leg, games) or contra.get(x) or contra.get(new)
            if dw:
                new, w = "", "; ".join(y for y in (w, dw) if y)
        if new and not BOTTOM.match(new):                   # 👍 11/18 (the owner on the Nuggets card: "a few things in
            aw = for_us(new, leg, why)                      #  the breakdown where it doesn't make the Nuggets look good")
            if aw:
                new, w = "", "; ".join(y for y in (w, aw) if y)
        if new and _dupe(new, seen):
            new, w = "", w or "the same line twice on the card"
        if new and where == "render" and chip_repeat(new, leg):
            new, w = "", w or "the 🚑 chip's names again"
        if w:
            note(cx["date"], leg, w, x, where)
        if new:
            out.append(new)
    if not any(BOTTOM.match(str(x)) for x in out if isinstance(x, str)) and any(BOTTOM.match(str(x)) for x in lines or [] if isinstance(x, str)):
        out.append(bottom_line(leg, cx))
    return out


def _no_move(line):
    """The line without its line-movement sentences (the line under a pick never talks the line moving)."""
    lead, parts = _sentences(str(line or ""))
    keep = [x for x in parts if not LINE_MOVE.search(x)]
    return (line, "") if keep == parts else (_join(lead, keep), "line-move talk in the line under the pick")


def check_one(pk, leg, line, games=None, where="render"):
    """The line under the pick: itself, rewritten, or '' (then the card falls back to its first real fact)."""
    if not line:
        return ""
    cx = ctx_of(pk, leg)
    line0 = line
    line, mv = _no_move(line)
    if mv:
        note(cx["date"], leg, mv, line0, where)
    new, w = wording(line, cx, leg)
    if new and not w:
        fw = facts(new, leg, games)
        if fw:
            new, w = "", "a fact the game files don't back: " + fw
    if new and not w:
        pw = who_plays(new, leg, games, where) or played_anyway(new, leg, games)
        if pw:
            new, w = "", pw
    if new and not w:                                        # (11/17: the derived facts + the sense check)
        dw = sense(new, leg) or derived(new, leg, games)
        if dw:
            new, w = "", dw
    if w:
        note(cx["date"], leg, w, line, where)
    return new


def note(day, leg, why, line, where):
    item = f"{leg.get('team')} {leg.get('odds')}: {why}: {str(line)[:110]}"
    CAUGHT.append((day or "", item))
    if (day, item) not in _LOGGED:
        _LOGGED.add((day, item))
        print(f"CARD CHECK ({where}) {day}: {item}", flush=True)


def save(path=None, keep_days=30):
    """data/sports/pick_audit.json: this run's catches under each pick's date ("card_check"), merged, deduped."""
    if not CAUGHT:
        return {}
    if path is None:                                         # (the pick audit's own file - sports_audit.PATH - so a
        import sports_audit                                  #  test run that moves it moves this too)
        path = sports_audit.PATH
    try:
        with open(path) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    changed = False
    for day, item in CAUGHT:
        if not day:
            continue
        cur = st.setdefault(day, {}).setdefault("card_check", [])
        if item not in cur and len(cur) < 300:
            cur.append(item)
            changed = True
    CAUGHT[:] = []
    if changed:
        st = {k: st[k] for k in sorted(st)[-keep_days:]}
        st_ = {k: v for k, v in st.items()}
        try:
            with open(path, "w") as f:
                json.dump(st_, f, indent=1, sort_keys=True)
        except OSError:
            pass
    return st


def pre_post(new, games=None):
    """🧾 Before a pick posts (sports.post_board, after the rule check): every new card's one-liner and breakdown run the
    whole check and are rewritten before anybody sees them. Never holds a pick. Returns {pick key: lines changed}."""
    reset()
    out = {}
    for pk in new or []:
        n = 0
        for leg in pk.get("legs") or []:
            bd = leg.get("breakdown")
            if bd:
                nb = check(pk, leg, bd, games, why="", where="pre-post")
                n += sum(1 for x in bd if x not in nb)
                leg["breakdown"] = nb
            if leg.get("why_line"):
                w = check_one(pk, leg, leg["why_line"], games, where="pre-post")
                if w != leg["why_line"]:
                    n += 1
                    leg["why_line"] = w
        l0 = (pk.get("legs") or [{}])[0]
        out[f"{pk.get('kind')}|{l0.get('game_id')}|{l0.get('side')}|{l0.get('market')}"] = n
    if any(out.values()):
        print(f"CARD CHECK: {sum(out.values())} line(s) rewritten or dropped on {sum(1 for v in out.values() if v)} new "
              f"card(s) before they posted", flush=True)
    try:
        save()
    except Exception as e:                                   # noqa: BLE001 - the log never blocks a post
        print(f"card check save failed: {e}", flush=True)
    return out


def audit(picks, games, since, until=None):
    """Every card posted since `since` (through `until`) as today's renderer + this check would show it: [(date, team,
    the check's catches on it)]. The 11/13 audit's harness and the regression test's."""
    import sports_dashboard as dash
    out = []
    for pk in picks:
        d = pk.get("date") or ""
        if d < since or (until and d > until) or not pk.get("legs"):
            continue
        before = len(CAUGHT)
        dash.WHY_USED.clear()
        dash._pick_card(pk["kind"], pk)
        out.append((d, pk["legs"][0].get("team"), [x for _, x in CAUGHT[before:]]))
    return out


if __name__ == "__main__":                              # python sports_card_check.py [since] - the audit over the posted cards
    import sys
    import sports_card_check as _cc                          # (the module the dashboard imports - not __main__)
    import sports_dashboard as _d
    pk_ = json.load(open(os.path.join(sd.DATA, "picks.json")))
    g_ = sd.load_games()
    _d._GAMES_[0] = g_
    _d._history(pk_)
    rows = _cc.audit(pk_, g_, sys.argv[1] if len(sys.argv) > 1 else "2026-10-25")
    print(sum(len(x[2]) for x in rows), "catches on", len(rows), "cards", datetime.now(timezone.utc).isoformat())


LAST_BY = re.compile(r"\b(won|lost) their last by (\d+)")
WEEK_OFF = re.compile(r"got the week off|had the week off|off (?:a|the|their) bye|coming off a bye", re.I)


def _early_leg(p):
    return {"team": p.get("team"), "opp": p.get("opp"), "odds": p.get("odds"), "market": p.get("market") or "ml",
            "league": p.get("league"), "game_id": p.get("game_id"), "side": p.get("side")}


def early_fact(p, line, games):
    """🔄 11/17 (the breakdown sweep): an early play posts days ahead, and its line was frozen - "Pistons are 6-1, 76ers
    7-1; Pistons won their last by 33" stayed up after both teams played again. '' when every record / last-game margin
    / week-off in the line is what the game files say NOW, else why not."""
    if not DERIVED_CHECK or not games or (p.get("market") or "ml") == "total" or p.get("side") not in ("home", "away"):
        return ""
    t = str(line or "")
    leg = _early_leg(p)
    try:
        w = facts(t, leg, games) or derived(t, leg, games)
    except Exception:                                        # noqa: BLE001
        w = ""
    if w:
        return w
    names = [leg["team"] or "", leg["opp"] or ""]
    for m in LAST_BY.finditer(t):
        i = _anchor(t, m.start(), names)
        f = team_facts(games, leg, "us" if i == 0 else "them") if i is not None else None
        if not f or f.get("unseen") or not f.get("lines"):
            continue
        a, b = map(int, f["lines"][-1].split()[1].split("-"))
        if (m.group(1) == "won") != (a > b) or abs(a - b) != int(m.group(2)):
            return (f"says {names[i]} {m.group(1)} their last by {m.group(2)} - their last game now is "
                    f"{f['lines'][-1]}")
    m = WEEK_OFF.search(t)
    if m and leg["league"] in ("nfl", "ncaaf"):
        i = _anchor(t, m.start(), names)
        f = team_facts(games, leg, "us" if i == 0 else "them") if i is not None else None
        if f and not f.get("unseen") and f.get("weeks") is not None and f["weeks"] < 2:
            return f"says {names[i]} had the week off - they played the week before this one"
    return ""


def early_lines(p, lines, where="render", games=None):
    """🎯 / ⏰ an early play's row lines (its why line and fact lines): an early play always carries units, so it never
    says a lean's words; the owner's banned frames / canned tails come off; the why line never talks line movement;
    and (11/17) a sentence whose record / last-game fact moved since the play posted comes off (early_fact)."""
    if games is None:
        try:
            import sports_dashboard
            games = sports_dashboard._GAMES_[0]
        except Exception:                                    # noqa: BLE001
            games = None
    try:
        import sports_early
        u = sports_early.units(p)
    except Exception:                                        # noqa: BLE001
        u = 0.5
    o = p.get("odds")
    imp = (100 / (o + 100) if o > 0 else -o / (-o + 100)) if isinstance(o, (int, float)) and o else None
    cx = {"units": u or 0.5, "kind": "early", "lean": False, "unit": True, "thin": (u or 0.5) <= 0.5, "lock": False,
          "floor": False, "market": p.get("market") or "ml", "odds": o, "read": p.get("own"), "p": p.get("own"),
          "implied": imp, "date": (p.get("start") or "")[:10]}
    leg = {"team": p.get("team"), "opp": p.get("opp"), "odds": o, "market": cx["market"], "league": p.get("league"),
           "game_id": p.get("game_id"), "side": p.get("side")}
    out = []
    for x in lines or []:
        y, mv = _no_move(x)
        y, w = wording(y, cx, leg) if y else (y, "")
        if y and games and not p.get("result"):              # (a graded play's row is history - left as it posted)
            lead, parts = _sentences(y)
            keep = []
            for sent in parts:
                ew = early_fact(p, sent, games)
                if ew:
                    w = "; ".join(z for z in (w, "a fact that moved since it posted: " + ew) if z)
                else:
                    keep.append(sent)
            if len(keep) != len(parts):
                y = _join(lead, keep)
        if mv or w:
            note(cx["date"], leg, "; ".join(z for z in (mv, w) if z), x, where)
        if y:
            out.append(y)
    return out


# 👍 11/17, the owner on the Capitals card's one-liner ("Capitals been unlucky ... their goalie's let in ..."): "We can't
# be saying nothing bad about the Capitals when we're picking them in the one-liner. We don't ever want to do that with
# our picks." The line right under a pick only ever talks our side UP (or the other side down). A sentence that puts a
# knock on OUR team - cold, unlucky, a skid, who we're missing - never sits there; it belongs in the full breakdown's
# "what scares us" line. Checked on every render (sports_dashboard._leg / _why_fallback) and by the card audit.
NEG_US = re.compile(r"\b(unlucky|snakebit|can'?t buy|leaky|bad bounces|puck luck|slump\w*|cold|skid\w*|losing streak|"
                    r"lost \d+ (?:straight|in a row|of)|dropped \d+|struggl\w*|been bad|ain'?t going in|let in|banged[- ]up|"
                    r"missing|without|short[- ]handed|scares us|risk|loss|losses|lost|losing|took an l|got beat|blown out|"
                    r"dropped|fell)\b", re.I)


def knocks_us(text, leg):
    """Does this line say something bad about OUR side (the pick's team)? A knock clause that names the OTHER team
    (and not us) is fine; any other knock clause in a line about us is a knock on us - the subject carries over
    ("10-8 for Capitals, last time out a 7-4 loss to the Devils")."""
    t = str(text or "")
    team = str((leg or {}).get("team") or "").strip()
    opp = str((leg or {}).get("opp") or "").strip()
    if not t or not team:
        return False

    def names(x):
        out = {x.lower()} if x else set()
        if " " in x:
            out.add(x.split()[-1].lower())               # ("Trail Blazers" -> "blazers")
        return out
    us_n, them_n = names(team), names(opp)
    low_all = t.lower()
    about_us = any(n in low_all for n in us_n)
    if re.search(r"\b(both|each)\b[^.]{0,40}\b(took an l|lost|losses|dropped|fell)\b", t, re.I):
        return about_us                                   # ("Both took an L last time" - that's us too)
    for clause in re.split(r"[.;:!?,\u2014]| - ", t):
        if not NEG_US.search(clause):
            continue
        low = clause.lower()
        us_here, them_here = any(n in low for n in us_n), any(n in low for n in them_n)
        if us_here or (about_us and not them_here):
            return True
    return False
    names = {team.lower()}
    if " " in team:
        names.add(team.split()[-1].lower())               # ("Trail Blazers" -> "blazers")
    if re.search(r"\b(both|each)\b[^.]{0,40}\b(took an l|lost|losses|dropped|fell)\b", t, re.I):
        return True                                       # ("Both took an L last time" - that's us too)
    for clause in re.split(r"[.;:!?,\u2014]| - ", t):
        low = clause.lower()
        if any(n in low for n in names) and NEG_US.search(clause):
            return True
    return False


KNOCK_OK = ("⚠️", "🔄", "✅", "🟡", "🔒", "💎", "🌟")   # the one ⚠️ risk line (and updates / the bottom line) may say a knock


def _sig_numbers(t):
    """The numbers in a line that pin a FACT (3+ digits: a score, a distance, a height) - '1,760', '5,300', '117'."""
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*\d|\d", str(t or "")) if len(n.replace(",", "")) >= 3}


def for_us(line, leg, why=""):
    """👍 11/18, the owner on the Nuggets card ("the breakdown just sucks ... where it doesn't make the Nuggets look good"
    / "This needs to be fixed permanently"): a breakdown makes the case for our side. Every render, a body line is cut
    when it (a) knocks OUR team - a loss, a skid, who we're missing (knocks_us) - only the one ⚠️ risk line may say a
    knock; or (b) only repeats the fact the one-liner already says (its numbers - '5,300 feet', '1,760 miles' - all in
    the one-liner). -> why it was cut, or ''."""
    t = str(line or "")
    if not t or t.startswith(KNOCK_OK):
        return ""
    if knocks_us(t, leg):
        return "a body line that knocks our own side (only the ⚠️ line may)"
    sig = _sig_numbers(t)
    if why and sig and sig <= _sig_numbers(why):
        return "the one-liner's fact said again"
    return ""
