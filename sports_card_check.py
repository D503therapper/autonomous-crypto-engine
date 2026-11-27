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
  6. THE CARD AS A WHOLE (11/19, the Warriors card - results/studies/cards_1119b; card_state / coherent_line /
     one_coherent, from COHERENT_FROM)
     - an injury argument (🚑 / 📉 / "short-handed") only when the other side is clearly more short-handed than ours by
       the same box-score yardstick (hurt / inj_ok / man_weight)
     - a man who is out never praised, counted or cited (any line, any 🏀 / 🌟 part)
     - our own men out said once, plain, in the card's 🚑 header (out_chips - both teams) - never in the write-up
     - no size words that run our own pick down (SELF_KNOCK); nothing that fights its card ("deep squad" with our men
       out); the line under the pick says OUR side first (side_first)
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
_CALL = re.compile(r"about to|fin to|finna|gonna|going to|\bwill\b|ain'?t a question|no hesitation|\ball day\b|easy call|"
                   r"done talking|fin to handle", re.I)


def _past_game(sentence):
    """Is the blowout wording about a game that was PLAYED ("The Steelers got their cheeks clapped 38-18 by the Bengals
    inside their last 5")? 11/19 sweep: the long-dog rule cut that true line off an Eagles +180 card - the rule is for
    a CALL on tonight ("about to beat the brakes off 'em"), never for a score that happened."""
    return bool(re.search(r"(?<![\d+-])\d{1,3}-\d{1,3}(?![\d-])", sentence)) and not _CALL.search(sentence)


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
        if v.NO_OUR_NUMBER:                                  # (11/19, the owner: never our number against the line makers')
            return None
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
        elif not cx.get("lean") and SURE.search(s0) and long_dog_cx(cx) and not _past_game(s0):
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
    _MAT.clear()
    _D1S.clear()


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


_SITE_FOR = r"(?:at home|on the road|away from home|in their (?:own )?building|overall|on the (?:year|season)|this (?:year|season)|so far)"


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
    if m5 and re.search(r"\bby \d+ or more\b|\bby \d+\+", t):
        m5 = None                                            # (11/23: "won 3 of their last 5 games by 10 or more" counts the
        #                                                      BIG wins, not the wins - read as a record it was cut as false
        #                                                      on a 4-1 team, and a true line left four cards shorter)
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
        elif re.match(r"\s*(?:fool you|looks? even|on paper)", after, re.I) or re.search(r"(?:don'?t let|records? (?:look|say)[\w ]*?)\s*$", before, re.I):
            kind = "rec"                                     # (11/19 sweep: "Don't let 5-5 fool you — Iowa State took those
            #   L's from Iowa, Utah ..." - "took" made the RECORD a score "that isn't in their last 6 games"; a true line cut)
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
        mm = re.match(r"\s*(?:\((?:the )?|(?:" + _SITE_FOR + r"\s+)?for (?:the )?)(" + "|".join(re.escape(n) for n in names if n) + r")\b", after)
        #   (11/19 sweep: "Knicks about to get their ass beat — 7-2 at home for the Timberwolves" - the record is the team's
        #    AFTER it; the nearest name before it was the Knicks, "the games say 4-3", and a true one-liner was dropped)
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
            wide = re.search(r"this (?:year|season)|last 3 (?:at home|on the road)|both saw|same opponent", t, re.I)
            #   (📖 11/19: a matchup line names a game from anywhere in the season - "got run in their own building
            #    twice already this year - 7-2 by the Blues" - so its score is checked against the whole season)
            got = [x for x in (f["lines"] if wide else f["lines"][-6:]) if sc(x) == win]
            if LASTGAME.search(before[-80:] + after[:30]) and not re.search(r"last 5|within|inside|in one of|not long ago", t, re.I) \
                    and not t.lstrip().startswith("🆚"):     # (11/22: "took the last one from the Senators this year - a 3-1
                #   win on 10/17" is the last MEETING, not their last game - last_meeting reads the 🆚 line)
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
ON_YEAR = re.compile(r"this (?:year|season)|on the (?:year|season)|against D1 teams", re.I)
NOT_STATS = re.compile(r"%|\bTDs?\b|per 48|minutes|\bmin a night|last (?:season|year)|a year ago|\bshots?\b|points? better|"
                       r"\bwent \d|per game\)|\d-\d|rebound|turnover|assist|\byards\b|\bsacks?\b|\bglass\b|free throws?|"
                       r"\b3s\b|threes|three-point|possessions|\bpace\b|penalt|power play|face-?off", re.I)
EVEN_PAIR = re.compile(r"(\d+(?:\.\d+)?) for(?: /|,)? (\d+(?:\.\d+)?) against")   # ("4 for / 4 against; ... 3 for / 3 against")
REST_TALK = re.compile(r"extra day|\bdays? off\b|\bdays?(?: of)? rest\b|fresher legs|fresh legs|better rested|more rest\b|"
                       r"well[- ]rested|\brested\b|more days off|days to rest|(?:more|less|fewer|extra) (?:time|days|nights) (?:to rest|off)", re.I)
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


_D1S = {}


def d1_set(games):
    """College hoops' Division I teams off the whole games file (sports_model.ncaab_d1), once a games file."""
    key = (id(games), len(games or {}))
    if _D1S.get("key") != key:
        try:
            import sports_model as _sm
            _D1S["key"], _D1S["set"] = key, _sm.ncaab_d1(_finals(games, "ncaab"))
        except Exception:                                    # noqa: BLE001 - can't tell = every team counts
            _D1S["key"], _D1S["set"] = key, None
    return _D1S.get("set")


def d1_only(games, gs, tid, leg):
    """A college hoops team's games without its non-D1 tune-ups (every other league: as is)."""
    if (leg or {}).get("league") != "ncaab":
        return gs
    d1 = d1_set(games)
    if d1 is None:
        return gs
    return [x for x in gs or [] if str(x["away"] if x["home"] == tid else x["home"]) in d1]


Q_SAME = "the same stat about the same team twice on the card"
SAME_BV = 83                    # ... on cards the sell writer wrote (breakdown VERSION 83+; a card with no stamp is a fresh
#                                 one). An older card whose game already started can't be re-written - cutting its second
#                                 scoreboard line on the page would only leave it shorter (the 11/22 Robert Morris card).


def same_on(leg):
    """Does the one-stat-a-team cut apply to this card? (sports_card_sell.SELL, and a card written by VERSION 83+)"""
    try:
        import sports_card_sell as _cs
        bv = (leg or {}).get("bv")
        return bool(_cs.SELL) and (bv is None or bv >= SAME_BV)
    except Exception:                                        # noqa: BLE001
        return False
Q_RATINGS = "says 'our ratings' / 'the ratings like' instead of a fact"
RATINGS_TALK = re.compile(r"\b(?:our|the) ratings (?:have|like|got|make|say|put)\b|\bour ratings\b|\bratings like\b", re.I)
Q_BOX = "a box-score number the files don't back"


def sell_numbers(line, leg, games):
    """🗣️ 11/22 THE CARD SELLS THE PICK: a box-score matchup line (sports_card_sell) says only numbers the two teams' box
    scores hold - re-derived here on every render. -> why it can't stand, or ''."""
    if not games:
        return ""
    try:
        import sports_card_sell as cs
        if str(line or "").startswith("🧭"):                 # 🧭 11/23: a schedule line, re-derived the same way
            return sched_numbers(line, leg, games)
        if str(line or "").startswith("🪑"):                 # 🪑 the man who sat: the name and number the leg carries
            who = cs.top_out_who(leg)
            if not who or str(who[0]) not in str(line):
                return f"{Q_BOX}: a top scorer the leg doesn't carry"
            return ""
        if not cs.is_sell(line):
            return ""
        fu, ft = team_facts(games, leg, "us"), team_facts(games, leg, "them")
        if not fu or not ft or fu.get("unseen") or ft.get("unseen"):
            return ""
        bad = cs.numbers_wrong(line, leg.get("team") or "", leg.get("opp") or "", leg.get("league"),
                               d1_only(games, fu["season"], fu["tid"], leg), d1_only(games, ft["season"], ft["tid"], leg),
                               fu["tid"], ft["tid"])
    except Exception:                                        # noqa: BLE001 - the check never breaks a card
        return ""
    return f"{Q_BOX}: {bad}" if bad else ""


def sched_numbers(line, leg, games):
    """🧭 11/23: a schedule line (who they beat, who beat us, the night they were a big favorite, the spread count, the
    road games) against the game files - sports_card_sell.sched_wrong. -> why it can't stand, or ''."""
    try:
        import sports_card_sell as cs
        import sports_breakdown_v24 as v
        g = (games or {}).get(leg.get("game_id"))
        fu, ft = team_facts(games, leg, "us"), team_facts(games, leg, "them")
        if not g or not fu or not ft or fu.get("unseen") or ft.get("unseen"):
            return ""
        lg = leg.get("league")
        fk = (id(games), len(games), lg, g["start"])
        if fk not in _FIN_BEFORE:
            if len(_FIN_BEFORE) > 64:
                _FIN_BEFORE.clear()
            _FIN_BEFORE[fk] = [x for x in _finals(games, lg) if x["start"] < g["start"]]
        d1 = d1_set(games)
        bad = cs.sched_wrong(line, leg.get("team") or "", leg.get("opp") or "",
                             d1_only(games, fu["season"], fu["tid"], leg), d1_only(games, ft["season"], ft["tid"], leg),
                             fu["tid"], ft["tid"], _FIN_BEFORE[fk],
                             (lambda t: d1 is not None and str(t) not in d1), s_theirs=ft["season"])
    except Exception:                                        # noqa: BLE001 - the check never breaks a card
        return ""
    return f"{Q_BOX}: {bad}" if bad else ""


def stats(line, leg, games):
    """'' when every scoring number in a points-a-game line is what the game files say, else why not - the breakdown's
    own arithmetic (sports_breakdown_v24._pts3 / _per_game) on the games before this one."""
    if not DERIVED_CHECK or not games:
        return ""
    t = str(line or "")
    if not PER_GAME.search(t) or NOT_STATS.search(t) or '"' in t or "“" in t:
        return ""
    try:
        import sports_card_sell as _cs
        if _cs.is_sell(t):                                   # (a box-score line: sell_numbers reads it)
            return ""
    except Exception:                                        # noqa: BLE001
        pass
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
        d1s, d1r = d1_only(games, f["season"], tid, leg), d1_only(games, f["reg"], tid, leg)   # (11/22: college hoops
        if lastn:                                            #  form reads D1 games only - both readings stand)
            for gs in (f["season"], f["reg"], d1s, d1r):
                for n in (3, 2):
                    for p in (v._pts3(gs, tid, n), v._pts3(gs, tid, n, 1)):
                        if p:
                            ok |= {float(p[0]), float(p[1]), round(abs(p[0] - p[1]), 1), float(p[2])}
        else:
            for gs in (f["reg"], f["season"], d1r, d1s):
                pg = v._per_game(gs, tid)
                if pg:
                    ok |= {float(round(pg[0])), float(round(pg[1])), round(pg[0], 1), round(pg[1], 1),
                           round(abs(pg[0] - pg[1]), 1), float(round(abs(pg[0] - pg[1])))}   # (11/18: the season margin)
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


Q_MORAL = "a moral victory (a close loss sold as a reason)"


def moral_victory(line, leg=None):
    """❌ 11/24 (Victor on the ⭐ Illinois St +100 card: "he said Illinois state good becuz it lost to st Mary's and Santa
    Clara ... lol"): a line that sells a side with a game it LOST - "finished within 3 of", "only lost by", "hung with",
    "took them to the wire" (sports_card_sell.MORAL). Cut on every render, every card, the line under the pick too."""
    t = str(line or "")
    if not t or BOTTOM.match(t) or t.startswith(("⚠️", "🔄")):
        return False
    try:
        import sports_card_sell as _cs
        return _cs.moral(t) or _cs.lost_to(t, (leg or {}).get("team") or "")   # (and "the teams that beat us are good")
    except Exception:                                        # noqa: BLE001
        return False


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
    stars = [0]
    coh = coherent_on(leg, cx.get("date"))                   # 🧩 11/19: the card judged as a whole (cards_1119b)
    st = card_state(leg, games) if coh else None

    def one(x):
        """One line through every check -> (the line as it may post or '', what was caught)."""
        try:                                                 # 🚫 11/19: never our price against the line makers'
            import sports_card_guard as _gd
            x1, sw = _gd.scrub(x)
        except Exception:                                    # noqa: BLE001
            x1, sw = x, ""
        if sw and not x1:
            return "", Q_PRICE
        if moral_victory(x1, leg):                           # ❌ 11/24: a close loss is never a reason
            return "", Q_MORAL
        new, w = wording(x1, cx, leg)
        if sw:
            w = "; ".join(y for y in (Q_PRICE if "price" in sw else sw, w) if y)
        if new and coh:                                      # 🧩 11/19: no injury argument when we're as short, no
            try:                                             #  man who's out said as playing, our own outs only in the
                new, kw = coherent_line(new, leg, cx, st)    #  header, no self-knock, nothing that fights the card
            except Exception:                                # noqa: BLE001 - the check never breaks a card
                kw = ""
            if kw:
                w = "; ".join(y for y in (w, kw) if y)
        if new and STORY_CHECK and str(new).startswith("💯"):   # 📖 11/19: one scorer line a card
            stars[0] += 1
            if stars[0] > 1:
                return "", "; ".join(y for y in (w, Q_STAR2) if y)
        if new and not BOTTOM.match(new):
            fw = facts(new, leg, games)
            if fw:
                new, w = "", "; ".join(y for y in (w, "a fact the game files don't back: " + fw) if y)
        if new:
            pw = who_plays(new, leg, games, where) or played_anyway(new, leg, games)
            if pw:
                new, w = "", "; ".join(y for y in (w, pw) if y)
        if new and not BOTTOM.match(new):                   # (11/17: the derived facts + the sense check)
            dw = sense(new, leg) or derived(new, leg, games) or contra.get(x) or contra.get(new) \
                or sell_numbers(new, leg, games)             # (🗣️ 11/22: a box-score line's numbers, re-derived)
            if dw:
                new, w = "", "; ".join(y for y in (w, dw) if y)
        if new and not BOTTOM.match(new):                   # 👍 11/18 (the owner on the Nuggets card: "a few things in
            aw = for_us(new, leg, why)                      #  the breakdown where it doesn't make the Nuggets look good")
            if aw:
                new, w = "", "; ".join(y for y in (w, aw) if y)
        if new and not BOTTOM.match(new):                   # 🧹 11/18 (cards_1118): who's out = men who matter, in
            try:                                            #  every league - a non-key name comes off the line, a line
                new2, mw = absent_matters(new, leg, games)  #  of only non-key men goes
            except Exception:                               # noqa: BLE001
                new2, mw = new, ""
            if mw:
                new, w = new2, "; ".join(y for y in (w, mw) if y)
        if new and _dupe(new, seen):
            new, w = "", w or "the same line twice on the card"
        if new and where == "render" and chip_repeat(new, leg):
            new, w = "", w or "the 🚑 chip's names again"
        return new, w

    for x in lines or []:
        if not isinstance(x, str):
            out.append(x)
            continue
        new, w = one(x)
        if w:
            note(cx["date"], leg, w, x, where)
        if new:
            out.append(new)
    try:                                                     # 🧹 11/18 (cards_1118): nothing said twice on a card - the
        kept = said_twice(leg, out, why, games)              #  one-liner's fact again, the same game in two lines
        for x in out:
            if isinstance(x, str) and x not in kept:
                note(cx["date"], leg, Q_REPEAT, x, where)
        out = kept
    except Exception:                                        # noqa: BLE001 - the check never breaks a card
        pass
    try:                                                     # 🗣️ 11/22 NO REPEATS (the Robert Morris card: "New Mexico St
        import sports_card_sell as _cs                       #  this season: 78 points a game allowed, 66 scored" above
        kept, gone = _cs.dedupe(out, leg.get("team") or "", leg.get("opp") or "", why, leg=leg) if same_on(leg) else (out, [])   # "outscored 72 to 63
        for x in gone:                                       #  over their last 3"): the same stat about the same team
            note(cx["date"], leg, Q_SAME, x, where)          #  is one fact - the first said stays
        out = kept
    except Exception:                                        # noqa: BLE001
        pass
    try:                                                     # 🧱 11/18 (night): a cut is never the end - the card's
        out = refill(leg, out, one, cx, why, games)          #  spare facts come in until it's back at its floor
    except Exception:                                        # noqa: BLE001 - the check never breaks a card
        pass
    if not any(BOTTOM.match(str(x)) for x in out if isinstance(x, str)) and any(BOTTOM.match(str(x)) for x in lines or [] if isinstance(x, str)):
        out.append(bottom_line(leg, cx))
    return out


def card_floor(cx):
    """The fact lines a card posts with when the facts exist: 6 a unit play, 5 a lean (sports_breakdown_v24.FLOOR_*)."""
    import sports_breakdown_v24 as v24
    return v24.FLOOR_LEAN if cx.get("lean") else v24.FLOOR_UNIT


def refill(leg, out, one, cx, why="", games=None):
    """🧱 11/18 (night) THE STANDING REFILL (the owner, after the page cut the Nuggets card's knocks and left three
    lines: "it's just short and fucking vague ... This is a fucking permanent bug" / "permanent fix for everything going
    forward"). The write-up keeps the real facts for our side it didn't need (leg["spare"], sports_breakdown_v24
    .fill_facts / deep_facts). Whenever a card comes out of the check under its floor - a line cut for the news, a
    knock, a repeat, the line that moved up to be the one-liner - the spares come in, each one through the SAME checks
    as any card line, until the card is back at its floor. Never filler: no spare left = the card stays short and the
    audit names it (tools/card_audit.py)."""
    spare = [x for x in leg.get("spare") or [] if isinstance(x, str) and x.strip()]
    floor = card_floor(cx)
    if not spare or fact_lines(out) >= floor or not any(BOTTOM.match(str(x)) for x in out if isinstance(x, str)):
        return out
    try:
        import sports_dashboard as dash
        import sports_card_guard
    except Exception:                                        # noqa: BLE001
        return out
    for x in spare:
        if fact_lines(out) >= floor:
            break
        if x in out or x == why:
            continue
        try:
            if dash.stale_in(x, leg) or not dash.latest_ok(x):   # (a man whose status moved since the card was written)
                continue
            got = sports_card_guard.clean([x], leg.get("league"), leg.get("team", ""), leg.get("opp", ""))
        except Exception:                                    # noqa: BLE001
            continue
        new = one(dash.pct_ok(got[0]))[0] if got else ""
        if not new or new in out:
            continue
        at = next((i for i, y in enumerate(out) if isinstance(y, str) and (y.startswith("⚠️") or BOTTOM.match(y))), len(out))
        cand = out[:at] + [new] + out[at:]
        try:
            if len(said_twice(leg, cand, why, games)) != len(cand):
                continue                                     # (it says what the card already says)
            import sports_card_sell as _cs
            if same_on(leg) and _cs.dedupe(cand, leg.get("team") or "", leg.get("opp") or "", why, leg=leg)[1]:
                continue                                     # (🗣️ 11/22: the same stat about the same team again)
        except Exception:                                    # noqa: BLE001
            continue
        out = cand
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
    if moral_victory(line, leg):                             # ❌ 11/24: a close loss never sits under a pick
        note(cx["date"], leg, Q_MORAL, line, where)
        return ""
    line0 = line
    line, mv = _no_move(line)
    if mv:
        note(cx["date"], leg, mv, line0, where)
    try:                                                     # 🚫 11/19: never our price against the line makers'
        import sports_card_guard as _gd
        line1, sw = _gd.scrub(line)
    except Exception:                                        # noqa: BLE001
        line1, sw = line, ""
    if sw:
        note(cx["date"], leg, Q_PRICE if "price" in sw else sw, line, where)
        line = line1
        if not line:
            return ""
    wl_ = weak_lead(line, leg, where)                        # 📖 11/19: a matchup fact leads, never filler
    if wl_:
        if where != "fallback":
            note(cx["date"], leg, wl_, line, where)
        return ""
    new, w = wording(line, cx, leg)
    #   (11/19 sweep: every check below ran only when the wording check had caught NOTHING - a line whose tail got cut
    #    ("... Close to 50-50 for us, Penguins by a nose.") skipped the fact check, the who-plays check and the rest
    #    rule, and "The Blues had 3 fewer days off than the Penguins" stayed up in hockey. Every check, every time.)
    def add(w2):
        return "; ".join(y for y in (w, w2) if y)
    if new:
        fw = facts(new, leg, games)
        if fw:
            new, w = "", add("a fact the game files don't back: " + fw)
    if new:
        pw = who_plays(new, leg, games, where) or played_anyway(new, leg, games)
        if pw:
            new, w = "", add(pw)
    if new:                                                  # (11/17: the derived facts + the sense check)
        dw = sense(new, leg) or derived(new, leg, games)
        if dw:
            new, w = "", add(dw)
    if new:                                                  # 🧹 11/18 (cards_1118): the one-liner names only men who
        try:                                                 #  matter, and never talks jargon
            new2, mw = absent_matters(new, leg, games)
            if mw:
                new, w = new2, add(mw)
        except Exception:                                    # noqa: BLE001
            pass
        if new and CARD_JARGON.search(new) and '"' not in new:
            new, w = "", add(Q_JARGON)
    if new and coherent_on(leg, cx.get("date")):             # 🧩 11/19: the line under the pick against the whole card -
        try:                                                 #  and it says OUR side first
            new, kw = one_coherent(new, leg, cx, card_state(leg, games), bool(cx.get("lean")))
        except Exception:                                    # noqa: BLE001
            kw = ""
        if kw and (kw != Q_SIDE or where != "fallback"):
            w = add(kw)
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
        try:                                                 # 🚫 11/19: never our price against the line makers'
            import sports_card_guard as _gd
            y, sw = _gd.scrub(y) if y else (y, "")
            if sw and y and not re.sub(r"[\W_]+", "", y):
                y = ""
            if sw:
                mv = "; ".join(z for z in (mv, Q_PRICE if "price" in sw else sw) if z)
        except Exception:                                    # noqa: BLE001
            pass
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
        if y and not p.get("result"):                                              # 🧹 11/18 (cards_1118): an early row argues for our side too
            y2, qw = early_for_us(y, leg, games)
            if qw:
                y, w = y2, "; ".join(z for z in (w, qw) if z)
        if y and coherent_on(leg, cx["date"]):               # 🧩 11/19: an early row never runs its own play down either
            lead, parts = _sentences(y)
            keep = [sent for sent in parts if not SELF_KNOCK.search(sent)]
            if len(keep) != len(parts):
                y, w = _join(lead, keep), "; ".join(z for z in (w, Q_SELF) if z)
        if mv or w:
            note(cx["date"], leg, "; ".join(z for z in (mv, w) if z), x, where)
        if y:
            out.append(y)
    return out


_PROJ = re.compile(r"- (\d+(?:\.\d+)?) with everybody, the number'?s (\d+(?:\.\d+)?)")
_LIVE_REC = re.compile(r"(?:\s*[-,]\s*)?(?:\bWe'?re )?\b(\d+)-(\d+) (?:on this play )?since we started betting it")
_SS = re.compile(r"\b([A-Z][\w.]*s)'s\b")


def early_for_us(line, leg, games=None):
    """(the early row's line as it may stand, why): a clause that knocks OUR side comes off ("Grizzlies lost their last
    by 31" under a Grizzlies pick), so does rest talk with no back-to-back ("2 days off to Clippers's 4"), a LOSING live
    record of the play itself ("0-1 since we started betting it" - the records live in the records), and "Mavericks's"
    reads "Mavericks'"."""
    t = str(line or "")
    why = []
    t2 = _SS.sub(r"\1'", t)
    if t2 != t:
        t, why = t2, ["a possessive nobody writes ('s's)"]
    m = _LIVE_REC.search(t)
    if m and int(m.group(1)) < int(m.group(2)):
        t = (t[:m.start()] + t[m.end():]).strip()
        t = re.sub(r"^[.\s]+$", "", t)
        why.append(Q_KNOCK + " - a losing live record of the play")
    m = _PROJ.search(t)
    if m and leg.get("side") == "over" and float(m.group(1)) < float(m.group(2)):
        return "", "; ".join(why + [Q_KNOCK + " - a projection under the number on an over"])
    if re.search(r"should score about \d+ against", t):   # (11/19, the owner: "we can't say that we're better at pricing
        return "", "; ".join(why + ["our number against the line makers' - a scoring projection"])   # the lines than
    #                                                        the fucking line makers" - no projection vs the number at all)
    lead, parts = _sentences(t)
    keep, cut = [], False
    for sent in parts:
        end = "." if sent.rstrip().endswith(".") else ""
        cl = [c for c in sent.rstrip().rstrip(".").split("; ")]
        ok = [c for c in cl if not knocks_us(c, leg) and not (b2b_league(leg) and REST_TALK.search(c) and not B2B_ANY.search(c))
              and not _early_noise(c)]
        if len(ok) != len(cl):
            cut = True
            if ok:
                keep.append("; ".join(ok) + end)
        else:
            keep.append(sent)
    if cut:
        t = _join(lead, keep)
        why.append(Q_KNOCK)
    return t, "; ".join(why)


# 💸 11/21, the owner on the Tulane +195 early card ("🧠 Tulane at +195 is a gift on our read. Early money already came in
# on Tulane."): "it says money came in on Tulane ... but if you look at the line, it went the other way." The money talk
# was true the day it posted (+425 -> +195) and stale the day he read it (+205); it is line-move talk, which the owner
# banned on every card (10/23), and "a gift on our read" is our number against the books' (11/19). Both come off every
# early row on render.
_MONEY_TALK = re.compile(r"\bmoney (?:already )?(?:came|come|coming|is coming|has come|'s come|poured|pouring) in\b|"
                         r"\b(?:early|sharp|smart|big) money\b|\bsteam\w*\b|\bhammered\b|\bbet (?:it )?down\b", re.I)


def _early_noise(clause):
    """A clause an early row never says: money / line-move talk, or our number against the books'."""
    if _MONEY_TALK.search(clause):
        return True
    try:
        import sports_owner_lingo as ol
        return any(re.search(p, clause, re.I) for p in ol.PRICE_CLAIM)
    except Exception:                                        # noqa: BLE001
        return False

def b2b_league(leg):
    try:
        import sports_breakdown_v24 as v
        return v.b2b_only(leg.get("league"))
    except Exception:                                        # noqa: BLE001
        return False


# 👍 11/17, the owner on the Capitals card's one-liner ("Capitals been unlucky ... their goalie's let in ..."): "We can't
# be saying nothing bad about the Capitals when we're picking them in the one-liner. We don't ever want to do that with
# our picks." The line right under a pick only ever talks our side UP (or the other side down). A sentence that puts a
# knock on OUR team - cold, unlucky, a skid, who we're missing - never sits there; it belongs in the full breakdown's
# "what scares us" line. Checked on every render (sports_dashboard._leg / _why_fallback) and by the card audit.
NEG_US = re.compile(r"\b(unlucky|snakebit|can'?t buy|leaky|bad bounces|puck luck|slump\w*|cold|skid\w*|losing streak|"
                    r"lost \d+ (?:straight|in a row|of)|dropped \d+|struggl\w*|been bad|ain'?t going in|let in|banged[- ]up|"
                    r"missing|without|short[- ]handed|scares us|risk|loss|losses|lost|losing|took an l|got beat|blown out|"
                    r"dropped|fell)\b", re.I)


_GENERIC = {"state", "tech", "city", "college", "university", "united", "southern", "northern", "eastern", "western"}
_NOT_NEG = re.compile(r"\b(?:hasn'?t|haven'?t|ain'?t|not|never|didn'?t|don'?t|won'?t|without an?)\s+(?:lost|lose|losing|loss|dropped|drop|fell|fall)\b", re.I)


def _named(mine, other, s):
    """Is one of `mine`'s names in s (lower case) - not counting a hit that sits inside the other team's longer name?
    (11/19 sweep: Oregon vs Oregon St, Texas vs Texas Tech, Florida vs Florida St, Iowa vs Iowa State, Miami vs
    Miami OH, New Mexico vs New Mexico St - "Oregon St have lost 5 straight" read as a knock on OREGON, and every
    line about the other side's losses came off our card. A NAME, never a piece of a word or of another name.)"""
    spans = [m.span() for o in other for m in re.finditer(rf"(?<![a-z]){re.escape(o)}(?![a-z])", s)]
    for n in mine:
        for m in re.finditer(rf"(?<![a-z]){re.escape(n)}(?![a-z])", s):
            if not any(a <= m.start() and m.end() <= b and (b - a) > (m.end() - m.start()) for a, b in spans):
                return True
    return False


def knocks_us(text, leg):
    """Does this line say something bad about OUR side (the pick's team)? A knock clause that names the OTHER team
    (and not us) is fine; any other knock clause in a line about us is a knock on us - the subject carries over
    ("10-8 for Capitals, last time out a 7-4 loss to the Devils")."""
    t = str(text or "")
    team = str((leg or {}).get("team") or "").strip()
    opp = str((leg or {}).get("opp") or "").strip()
    if not t or not team:
        return False

    def names(x, other=""):
        out = {x.lower()} if x else set()
        if " " in x and x.split()[-1].lower() not in other.lower() and len(x.split()[-1]) >= 4 and x.split()[-1].lower() not in _GENERIC:   # (11/18: "Kansas St" vs "Oklahoma St" - the
            out.add(x.split()[-1].lower())               #  shared last word names nobody; "Trail Blazers" -> "blazers")
        return out
    us_n, them_n = names(team, opp), names(opp, team)
    t = _NOT_NEG.sub(" ", t)                              # (11/18: "hasn't lost in 3" is no knock)
    low_all = t.lower()
    has = lambda n, s: re.search(rf"(?<![a-z]){re.escape(n)}(?![a-z])", s) is not None   # noqa: E731 (11/18: a NAME, never
    #   a piece of a word - "New Mexico St" -> "st" sat inside "lost" and every loss on the card read as ours)
    here = _named
    about_us = here(us_n, them_n, low_all)
    if re.search(r"\b(both|each)\b[^.]{0,40}\b(took an l|lost|losses|dropped|fell)\b", t, re.I):
        return about_us                                   # ("Both took an L last time" - that's us too)
    for clause in re.split(r"[.;:!?,\u2014\u00b7]| - ", t):   # (11/19: "·" parts a two-game line - "Panthers got a 20-17
        if not NEG_US.search(clause):                         #  win over the Saints · Ravens took a 23-20 loss ...")
            continue
        low = clause.lower()
        us_here, them_here = here(us_n, them_n, low), here(them_n, us_n, low)
        if us_here or (about_us and not them_here):
            return True
    return False


KNOCK_OK = ("⚠️", "🔄", "✅", "🟡", "🔒", "💎", "🌟")   # the one ⚠️ risk line (and updates / the bottom line) may say a knock


def _sig_numbers(t):
    """The numbers in a line that pin a FACT (3+ digits: a score, a distance, a height) - '1,760', '5,300', '117'."""
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*\d|\d", str(t or "")) if len(n.replace(",", "")) >= 3}


# 📖 11/19 THE STORY OF THE GAME (results/studies/cards_1119 - the owner on the Flyers +150 card: "this guy's in gold and
# this guy's in gold. Don't tell us shit. It's like, oh, we price flyers at this. Don't tell us shit ... the breakdowns
# are just trash" / "permanently fix these fucking breakdowns"). Filler dressed as a fact is cut on every render:
#   Q_FILLER  price math in the body ("💵 We price Flyers at +123", "winning about 4 times in 10 is all we need"),
#             "at full strength" by itself, a record up by one ("3-2 over their last 5", "won 3 of their last 5")
#   Q_STAR2   a second scorer line (💯) - one a card, the last thing a card reaches for
#   Q_PRICE   a sentence that says our own price or that the book has it wrong (the owner, 11/19: "we can't say that
#             we're better at pricing the lines than the fucking line makers") - sports_card_guard.scrub
#   Q_LEAD    the line under the pick is a scorer's points / the price / a close last result / a record up by one
Q_FILLER = "filler dressed as a fact (price math, 'full strength' alone, a record up by one)"
Q_STAR2 = "a second scorer line on the card"
Q_PRICE = "says our price against the book's"
Q_LEAD = "a weak line under the pick (a scorer's points / the price / a close result / a record up by one)"
PRICE_MATH = re.compile(r"^\W*💵|\btimes? in (?:10|3|4)\b|for (?:the|this) bet to pay|\bis all (?:we need|it takes)\b", re.I)
GAME_COUNT = re.compile(r"\btimes? in \d+ games\b", re.I)   # (11/27: "gave it away 7 times in 10 games" is a COUNT, not the price)


def price_math(line):
    """💵 Price math dressed as a fact ("winning about 4 times in 10 is all we need") - NEVER a count over a team's games.
    11/27 (the 11/26 Chiefs +130 card): "🧤 Chiefs gave it away 7 times in 10 games this year. Bills: 16 in 10." - the
    card's best matchup fact, a true line - matched "times in 10", so the page cut it as the line under the pick AND as
    a body line (every football turnover / sack line of a team 3, 4 or 10 games in went the same way: the whole NFL in
    week 12). A line that counts something over games is a fact; the 💵 line and the price wordings still go."""
    t = str(line or "")
    if not PRICE_MATH.search(t):
        return False
    return t.lstrip().startswith("💵") or not GAME_COUNT.search(t)
UP_BY_ONE = re.compile(r"\b(?:3-2|2-3)\b|\b(?:won|dropped|lost) 3 of (?:their|the) last 5\b|\b3 of the last 5\b|"
                       r"\b3 wins in (?:their|the) last 5\b", re.I)
STORY_CHECK = True


def filler(line, leg=None):
    """Is this body line filler dressed as a fact (see Q_FILLER)? -> why, or ''."""
    t = str(line or "")
    if not STORY_CHECK or not t or BOTTOM.match(t) or t.startswith(("⚠️", "🔄", "✅ Update", "🌟", "🔒", "💎")):
        return ""
    if price_math(t):
        return Q_FILLER
    if HEALTHY.search(t):
        return Q_FILLER
    if t.startswith("🗓") and UP_BY_ONE.search(t):
        return Q_FILLER
    if t.startswith("📋"):                                   # ("📋 Louisiana Tech sits 3-2 so far." - one record, up by one)
        recs = re.findall(r"(?<![\d-])(\d{1,2})-(\d{1,2})(?![\d-])", t)
        if len(recs) == 1 and int(recs[0][0]) - int(recs[0][1]) == 1 and not re.search(r"\bwin\b|\bbeat\b|\bloss\b", t):
            return Q_FILLER
    return ""


def close_result(line, leg):
    """A 📅 last-game line whose score was close (under sports_breakdown_v24.REAL_LOSS) - it never leads a card."""
    t = str(line or "")
    if not t.startswith("📅"):
        return False
    try:
        import sports_breakdown_v24 as v24
        need = v24.REAL_LOSS.get((leg or {}).get("league"))
        gaps = [abs(int(a) - int(b)) for a, b in re.findall(r"(?<![\d-])(\d{1,3})-(\d{1,3})(?![\d-])", t)]
        return bool(need and gaps and max(gaps) < need)
    except Exception:                                        # noqa: BLE001
        return False


def strong_line(x, leg):
    """A body line that can lead a card: a team-level matchup fact for our side."""
    t = str(x or "")
    if not t or BOTTOM.match(t) or t.startswith(("⚠️", "🔄", "✅", "🟡", "🔒", "💎", "🌟", "💯", "💵", "🏀")):
        return False
    return not (filler(t, leg) or close_result(t, leg) or knocks_us(t, leg))


def weak_lead(line, leg, where="render"):
    """The line under the pick is never the price, a close last result or a record up by one - and a scorer's points
    only when the card holds no team-level fact (sports_breakdown_v24.lead_line at the pool; this is the page's stop)."""
    t = str(line or "")
    if not STORY_CHECK or not t:
        return ""
    if price_math(t) or close_result(t, leg) or (t.startswith("🗓") and UP_BY_ONE.search(t)):
        return Q_LEAD
    if t.startswith("💯") and where != "fallback" and any(strong_line(x, leg) for x in (leg or {}).get("breakdown") or []):
        return Q_LEAD
    return ""


def for_us(line, leg, why=""):
    """👍 11/18, the owner on the Nuggets card ("the breakdown just sucks ... where it doesn't make the Nuggets look good"
    / "This needs to be fixed permanently"): a breakdown makes the case for our side. Every render, a body line is cut
    when it (a) knocks OUR team - a loss, a skid, who we're missing (knocks_us) - only the one ⚠️ risk line may say a
    knock; or (b) only repeats the fact the one-liner already says (its numbers - '5,300 feet', '1,760 miles' - all in
    the one-liner). -> why it was cut, or ''."""
    t = str(line or "")
    if t and HEALTHY.search(t) and filler(t, leg):          # (📖 11/19: "at full strength" alone - a ✅ line, cut all the same)
        return Q_FILLER
    if not t or t.startswith(KNOCK_OK):
        return ""
    if knocks_us(t, leg) or our_bad_numbers(t, leg):
        return Q_KNOCK
    if RATINGS_TALK.search(t) and '"' not in t and "“" not in t:   # (🗣️ 11/22: a card says the fact, never "our ratings")
        return Q_RATINGS
    sig = _sig_numbers(t)
    if why and sig and sig <= _sig_numbers(why):
        return "the one-liner's fact said again"
    if OPP_UP.search(t) or their_good_news(t, leg):
        return Q_OPP
    if NOTHING.search(t) and "plus money" not in t.lower():
        return Q_NOTHING
    if even_site(t, leg):
        return Q_NOTHING
    if CARD_JARGON.search(t) and '"' not in t and "“" not in t:
        return Q_JARGON
    return filler(t, leg)


# 🧹 11/18 CARD QUALITY (results/studies/cards_1118 - the owner: "I've talked to you about our breakdowns making mistakes
# and being stupid and not right. This needs to be fixed permanently"). The audit of every card 11/1-11/18 re-written by
# the engine found five kinds of bad line the fact checks above can't see (every one of them TRUE - and still wrong on a
# card). Each has a rule here, run on every render, and a count in tools/card_audit.py's card-quality score:
#   Q_KNOCK    a body line that knocks OUR side - a loss, a skid, a losing record, our own bad numbers
#   Q_OPP      a body line that argues for THEM - "the Kraken won their last one too", "so they feeling themselves too",
#              "Both teams are rolling", their heater / their win in our body
#   Q_NOTHING  a line that says nothing for our side - "1-1 at home", "A wash on the records", "Dead even on the record"
#   Q_REPEAT   said twice - the one-liner's fact again, the same game in two lines, the same men out twice
#   Q_JARGON   a stat nobody uses or a formula's answer - "per 48 minutes", "a +2.3 team a game", "-7 a game", "should be
#              about 13 points better than their record"
#   Q_ABSENT   a man named OUT who doesn't matter (sports_absences.who_matters - every league) or who has been out so
#              long it's old news
Q_KNOCK = "a body line that knocks our own side (only the ⚠️ line may)"
Q_OPP = "a body line that argues for the other side"
Q_NOTHING = "a line that says nothing for our side"
Q_REPEAT = "said twice on the card"
Q_JARGON = "jargon / a stat a bettor doesn't use"
Q_ABSENT = "names a man out who doesn't matter"
QUALITY = {"filler": (Q_FILLER, Q_STAR2, Q_PRICE, Q_LEAD), "knocks us": (Q_KNOCK,), "argues for them": (Q_OPP,), "says nothing": (Q_NOTHING,),
           "repeats": (Q_REPEAT, Q_SAME, "the one-liner's fact said again", "the same line twice on the card",
                       "the 🚑 chip's names again"),
           "jargon": (Q_JARGON, Q_RATINGS), "non-key absence": (Q_ABSENT,)}
OPP_UP = re.compile(r"won their last one too|feeling themselves|both won last|both teams are rolling|heater vs heater|"
                    r"neither team has lost|both feeling good|\bare off an? [\w.' -]*\bwin\b[^.]* themselves", re.I)
NOTHING = re.compile(r"a wash (?:on the records|in net)|dead even on the record|nothing in it on paper|"
                     r"nothing between 'em on the records|same record, |same spot in the standings|both took an l|"
                     r"both pissed off|one of 'em gets right", re.I)
CARD_JARGON = re.compile(r"per 48\b|\bPDO\b|[+-]\d+(?:\.\d+)? team a game|\b(?:is|are) [+-]\d+(?:\.\d+)? a game\b|"
                         r"points? better than (?:their|its|this) record|\bgoal totals say\b|points under what their goals|"
                         r"\bno-vig\b|\bnet rating\b|per 100 possessions|\bexpected goals\b|\bxG\b|"
                         r"\befficiency (?:read|rating|margin)\b|\bregress(?:es|ion)?\b|\bPythag|in point margin|"
                         r"[+-]\d+(?:\.\d+)? scoring edge", re.I)
_SITE_REC = re.compile(r"(?<![\d-])(\d{1,2})-(\d{1,2})(?![\d-])")
_SITE_W = re.compile(r"at home|on the road|away from home|own building|in their building|the crib", re.I)
_PUT_UP = re.compile(r"\b(?:score|scores|put up|puts up|average|averages)\b[^.;\d]{0,12}(\d+(?:\.\d+)?)[^.;]*?"
                     r"\b(?:give up|gives up|allow|allows|allowed)\b[^.;\d]{0,6}(\d+(?:\.\d+)?)", re.I)
_WIN_SAID = re.compile(r"\b(?:won|win|wins|victory|beat|heater|rolling)\b", re.I)


def _names_of(team):
    t = str(team or "").strip().lower()
    return {t, t.split()[-1]} if t else set()


def our_bad_numbers(line, leg):
    """A body line that puts OUR bad numbers up: "Flyers score 3.3 and give up 4 a game" (we score less than we allow), a
    LOSING record of ours said alone ("E Michigan sits 4-5 so far"), a losing home / road record of ours."""
    t = str(line or "")
    us, them = str(leg.get("team") or ""), str(leg.get("opp") or "")
    if not us or us not in t:
        return False
    for clause in re.split(r"[.;]", t):
        if us in clause and (not them or them not in clause):
            m = _PUT_UP.search(clause)
            if m and float(m.group(1)) < float(m.group(2)):
                return True
    if t.startswith(("📋", "🏟", "🧳")) and (not them or them not in t):
        for a, b in _SITE_REC.findall(t):
            if int(a) < int(b) and int(a) + int(b) <= 90 and not re.search(r"last 5", t):
                return True
    return False


def even_site(line, leg):
    """"1-1 at home this year for Suns", "2-2 away from home this year for Capitals": our .500 record somewhere."""
    t = str(line or "")
    us, them = str(leg.get("team") or ""), str(leg.get("opp") or "")
    if not t.startswith(("🏟", "🧳")) or not us or us not in t or (them and them in t) or not _SITE_W.search(t):
        return False
    return any(a == b for a, b in _SITE_REC.findall(t))


def their_good_news(line, leg):
    """A 📅 / 🔥 body line that is only about THEM and says they won / are hot."""
    t = str(line or "")
    us, them = str(leg.get("team") or ""), str(leg.get("opp") or "")
    if not t.startswith(("📅", "🔥")) or not them or them not in t:
        return False
    low = t.lower()
    mine = {n for n in _names_of(us) if n == us.lower() or (len(n) >= 4 and n not in _GENERIC and n not in them.lower())}
    if _named(mine, {them.lower()}, low) or not _named({them.lower()}, {us.lower()}, low):
        return False                                         # (11/19 sweep: was `n in low` - "st" inside "straight" read
        #                                                      as Kansas St, "oregon" inside "oregon st" as Oregon)
    return bool(_WIN_SAID.search(t)) and not re.search(r"\bloss\b|\blost\b|\bL\b|\bbeating from\b|straight L|losses|hot seat|"
                                                       r"feeling the heat|fishbowl|jobs on the line", t)


_MAT = {}


def _matters(lg, tid, name, before):
    k = (lg, str(tid), name, before)
    if k not in _MAT:
        if len(_MAT) > 5000:
            _MAT.clear()
        try:
            import sports_absences
            _MAT[k] = sports_absences.matters(None, lg, tid, name, before)
        except Exception:                                    # noqa: BLE001
            _MAT[k] = None
    return _MAT[k]


ABSENT_CHECK = True
_OUT_LINE = re.compile(r"\bout\b|\bwithout\b|\bmissing\b|\bdown\b|won'?t suit up|not dressing|\bno\b|gotta play|"
                       r"banged up|short-handed|injur|trainer'?s room", re.I)


def _drop_name(t, nm):
    """The line without one man: his name, a position before or after it, and the comma that hung on him."""
    t2 = re.sub(rf"(?:\b[A-Z]{{1,3}} )?{re.escape(nm)}(?: \([^)]*\))?", "\x00", t, count=1)
    t2 = re.sub(r",\s*\x00|\x00\s*,\s*|\s+and\s+\x00|\x00\s+and\s+", lambda m: " " if m.group(0).lstrip().startswith("\x00") else "", t2)
    t2 = t2.replace("\x00", "")
    return re.sub(r"\s{2,}", " ", t2).replace(" .", ".").replace(" ,", ",").replace("( ", "(").strip()


def absent_matters(line, leg, games):
    """(the line as it may stand, why) - a 🚑 line, the ⚠️ knock or a one-liner that names men OUT keeps only the ones who
    matter (sports_absences.matters: NBA top-3 scorer / starter, college hoops top-5 minutes, hockey top-6 forward /
    top-4 D / the #1 goalie, football a regular - and never a man who sat the team's last 5 box scores, 2 in football).
    Every man named gone = the line goes. No box scores for the team = nothing is claimed, the line stands."""
    t = str(line or "")
    if not ABSENT_CHECK or not games or not t or not _OUT_LINE.search(t) or t.startswith(("🔄", "✅", "🌟", "🏀")):
        return t, ""
    if "questionable" in t.lower() and t.startswith("🚑"):
        return t, ""                                         # (the 🚑 chip's game-time men are the board's business)
    g = (games or {}).get(leg.get("game_id"))
    side = leg.get("side")
    if not g or side not in ("home", "away") or not g.get("start"):
        return t, ""
    other = "away" if side == "home" else "home"
    lg = leg.get("league")
    named = []
    for tid, lst in ((g.get(side), list(leg.get("outs") or []) + list(leg.get("absent") or [])),
                     (g.get(other), leg.get("opp_outs") or [])):
        for nm in dict.fromkeys(_card_names(lst)):
            if nm and nm in t and not any(nm == n for n, _ in named):
                named.append((nm, tid))
    if not named:
        return t, ""
    bad = [nm for nm, tid in named if _matters(lg, tid, nm, g["start"]) is False]
    if not bad:
        return t, ""
    if len(bad) == len(named):
        return "", f"{Q_ABSENT}: {', '.join(bad[:3])}"
    new = t
    for nm in bad:
        new = _drop_name(new, nm)
    if HOLE_SAID.search(new):                                # 🧱 11/19: "Both starting tackles out - backups protecting
        new = HOLE_SAID.sub("", new).strip()                 # the QB." stands only with every man it was said of
        new = new if new.endswith((".", "!", "?")) else new + "."
    return new, f"{Q_ABSENT}: {', '.join(bad[:3])} (the name came off the line)"


HOLE_SAID = re.compile(r"\s*(?:- )?(?:both starting (?:tackles|corners) out|\d+ starting offensive linemen out|"
                       r"\d+ starters out (?:of the secondary|up front on defense))[^.]*\.?", re.I)


def said_twice(leg, lines, why, games):
    """The card's lines with nothing said twice (sports_breakdown_v24.no_repeats - the generator's own rule, run again on
    every render so an older card or a new pool line can't bring a repeat back)."""
    import sports_breakdown_v24 as v
    known, recs = set(), []
    for which in ("us", "them"):
        f = team_facts(games, leg, which) if games else None
        if not f or f.get("unseen"):
            continue
        for x in (f.get("season") or [])[-5:]:
            try:
                known.add(tuple(sorted((int(x["home_score"]), int(x["away_score"])), reverse=True)))
            except (KeyError, TypeError, ValueError):
                pass
        recs += [f"{r[0]}-{r[1]}" for r in f.get("rec") or ()]
    return v.no_repeats(list(lines), why, known, recs, leg.get("team") or "")


# ---- 🧩 11/19 EVERY CARD MAKES SENSE AS A WHOLE (results/studies/cards_1119b) ---------------------------------------------
# The owner, 11/19, on the Warriors +180 card: "The Grizzlies breakdown on the one-liner, it says like 3 fucking key guys
# are out for the Grizzlies, but give me the fucking [Warriors]. Makes no fucking sense. Fucking fix this shit." Every line
# on that card passed its own check - and the card as a whole was nonsense: it sold "the Grizzlies are short-handed" while
# OUR side sat Curry, Green and Butler; it said "Stephen Curry is cooking" under a line that listed him OUT; "deep squad"
# beside our own men out; a header and a bottom line that ran our own pick down ("not a great one"); and a line under
# the pick that opened on the OTHER team's name. The card is judged as a whole here, on every render and before a post:
#   Q_INJ     an injury argument (🚑 / 📉 / "short-handed") is made only when the other side is CLEARLY more
#             short-handed than ours by the same yardstick - who matters by the box scores (hurt / inj_ok)
#   Q_PLAYS   a man who is out is never praised, counted or cited in an on / off stat (any line, any 🏀 / 🌟 part)
#   Q_OURS    our own men out are said ONCE, as plain information, in the card's 🚑 header (both teams, no comment) -
#             never in the write-up, the line under the pick, the bottom line or the 🌟 line (out_chips)
#   Q_SELF    the bottom line / the size line never runs our own pick down ("not a great one", "don't get crazy")
#   Q_FIGHTS  no line fights the rest of its card ("deep squad" / "9 guys play real minutes" with our top men out)
#   Q_SIDE    the line under the pick says OUR side first ("Give me Warriors: ...") - nobody guesses which side we're on
# A failing line is rewritten or dropped and the best true fact for our side leads instead - never a pick held.
COHERENT = True
COHERENT_FROM = "2026-11-19"
HURT_CLEAR = 2.0                # "clearly more short-handed": their men out outweigh ours by this much (one key man more,
#                                 or two regulars more) - with nobody who matters out on our side, any of theirs counts
MAN_KEY = {"nba": 3.0, "nhl": 3.0, "qb": 4.0, "skill": 2.0}   # a top-3 scorer / a #1 goalie; the QB; the lead back / a top-2 catcher
Q_INJ = "an injury argument while our side is as short-handed (or worse)"
Q_PLAYS = "names a man who is out as playing / producing"
Q_OURS = "our own men out inside the write-up (the 🚑 header says it once)"
Q_SELF = "runs our own pick down"
Q_FIGHTS = "fights the rest of its card"
Q_SIDE = "the line under the pick didn't say our side first"
QUALITY["incoherent"] = (Q_INJ, Q_PLAYS, Q_OURS, Q_SELF, Q_FIGHTS, Q_SIDE)
SELF_KNOCK = re.compile(
    r"not a great one|not a great|not a monster|no monster edge|no big edge|not a big edge|just the best dog left|best dog left|"
    r"best dog we (?:could find|found)|best dog on the (?:slate|board)|best of every dog|angles are mixed|don'?t (?:get|go) crazy|small swing|and we'?ll see|no gift in|"
    r"not (?:on )?a gift|price is about (?:fair|right)|priced about right|about fair|nothing extra in it|not a big one|"
    r"still (?:proving|earning)|till it proves|till the live record|builds its live record", re.I)
INJ_TALK = re.compile(r"short[- ]handed|banged[- ]up|missing bodies|trainer'?s room|injury list|dealing with injuries|"
                      r"missing key|their backup|down their starting", re.I)
GONE_SAID = re.compile(r"\bout\b|\bwithout\b|\bmissing\b|won'?t suit up|not dressing|\bno\b|gotta play|gotta find|\blose\b|"
                       r"\bloses\b|\bgone\b|\bshelf\b|\bIR\b|injured|suspend|\bsat\b|sits\b|sidelined", re.I)
DEEP_SAID = re.compile(r"deep squad|guys play real minutes|full strength|full squad|healthy|everybody available", re.I)
_OUT_UPDATE = re.compile(r"^🔄 Update: (.+?) is (?:out|OUT now) for (?:the )?(.+?)(?: too)?\.$")
_ROSTER = {}
_KEYS = {}


def coherent_on(leg, day=None):
    """Is this card judged as a whole (COHERENT_FROM - the pick's day or the game's)?"""
    d = max(str(day or ""), str((leg or {}).get("start") or "")[:10])
    return bool(COHERENT) and d >= COHERENT_FROM


def _roster(lg, tid, before):
    """The normalized names in a team's last 10 box scores (whose man is he?)."""
    k = (lg, str(tid), before)
    if k not in _ROSTER:
        if len(_ROSTER) > 2000:
            _ROSTER.clear()
        try:
            import sports_absences as sa
            _ROSTER[k] = {sa._nm(r["player"]) for _, _, rs in sa._real(None, lg, tid, before)[-10:] for r in rs}
        except Exception:                                    # noqa: BLE001
            _ROSTER[k] = set()
    return _ROSTER[k]


def _key_men(lg, tid, before):
    k = (lg, str(tid), before)
    if k not in _KEYS:
        if len(_KEYS) > 2000:
            _KEYS.clear()
        try:
            import sports_absences as sa
            _KEYS[k] = sa.key_players({}, lg, tid, before) or {}
        except Exception:                                    # noqa: BLE001
            _KEYS[k] = {}
    return _KEYS[k]


def man_weight(lg, tid, name, pos, before):
    """How much one man out counts, by the box scores: 0 = doesn't matter / gone so long the results hold it; 1 = a
    regular (sports_absences.matters) or a man the files can't place; 3 = a top-3 scorer (NBA / hockey) or the #1
    goalie; 4 = the quarterback; 2 = the lead back / a top-2 catcher."""
    m = _matters(lg, tid, name, before)
    if m is False:
        return 0.0
    w = 1.0
    try:
        import sports_absences as sa
        kp = _key_men(lg, tid, before)
        hit = lambda ps: bool(sa.match(name, {sa._nm(p) for p in ps if p}))   # noqa: E731
        if lg in ("nba", "nhl") and hit(kp.get("top") or []):
            w = MAN_KEY[lg]
        elif lg == "nhl" and str(pos or "").upper() == "G" and m:
            w = MAN_KEY["nhl"]
        elif lg in ("nfl", "ncaaf"):
            if hit([kp.get("qb")]) or (str(pos or "").upper() == "QB" and m):
                w = MAN_KEY["qb"]
            elif hit([kp.get("rb")] + list(kp.get("wr") or [])):
                w = MAN_KEY["skill"]
    except Exception:                                        # noqa: BLE001
        pass
    return w


def _name_pos(entries):
    out = {}
    for x in entries or []:
        s = str(x or "")
        nm = (_card_names([s]) or [""])[0]
        m = re.search(r"\(([A-Za-z/]{1,4})\)", s)
        if nm:
            out.setdefault(nm, m.group(1) if m else "")
    return out


def out_men(leg, games=None):
    """({name: pos} ours, {name: pos} theirs, {names nobody could place}) - every man OUT tonight the card knows of:
    its who's-out lists, the absence penalty's men, the men ruled out after it posted (added_outs / the 🔄 update lines)
    and every name the report has out (rep_status) - never a man whose status moved back (stale and not 'out' now)."""
    rep = leg.get("rep_status") or {}
    stale = set(leg.get("stale") or [])
    gone = lambda n: rep.get(n) == "out" if n in rep else n not in stale     # noqa: E731
    ours = {n: p for n, p in _name_pos(list(leg.get("outs") or []) + list(leg.get("absent") or [])).items() if gone(n)}
    theirs = {n: p for n, p in _name_pos(leg.get("opp_outs")).items() if gone(n)}
    us, opp = str(leg.get("team") or ""), str(leg.get("opp") or "")
    said = {}
    for x in leg.get("fresh") or []:
        m = _OUT_UPDATE.match(str(x))
        if m:
            said[m.group(1)] = m.group(2)
    extra = [n for n in list(leg.get("added_outs") or []) + [n for n, c in rep.items() if c == "out"]
             if n not in ours and n not in theirs and gone(n)]
    lost = set()
    g = (games or {}).get(leg.get("game_id")) if games else None
    side = leg.get("side")
    other = "away" if side == "home" else "home"
    for n in dict.fromkeys(extra):
        tn = said.get(n)
        if tn and tn == us:
            ours[n] = ""
        elif tn and tn == opp:
            theirs[n] = ""
        else:
            placed = False
            if g and side in ("home", "away") and g.get("start"):
                try:
                    import sports_absences as sa
                    a = sa.match(n, _roster(leg.get("league"), g.get(side), g["start"]))
                    b = sa.match(n, _roster(leg.get("league"), g.get(other), g["start"]))
                    if a != b:
                        (ours if a else theirs)[n] = ""
                        placed = True
                except Exception:                            # noqa: BLE001
                    pass
            if not placed:
                lost.add(n)
    return ours, theirs, lost


def hurt(leg, games=None):
    """(ours, theirs) - how short-handed each side is tonight, the same yardstick both ways (man_weight)."""
    ours, theirs, _ = out_men(leg, games)
    g = (games or {}).get(leg.get("game_id")) if games else None
    side = leg.get("side")
    if not g or side not in ("home", "away") or not g.get("start"):
        return float(len(ours)), float(len(theirs))          # (no game file: every listed man counts the same)
    other = "away" if side == "home" else "home"
    lg = leg.get("league")
    w = lambda men, tid: sum(man_weight(lg, tid, n, p, g["start"]) for n, p in men.items())   # noqa: E731
    return w(ours, g.get(side)), w(theirs, g.get(other))


def inj_ok(leg, games=None):
    """May this card argue "they're short-handed"? Only when the other side is CLEARLY more short-handed than ours."""
    try:
        o, t = hurt(leg, games)
    except Exception:                                        # noqa: BLE001
        return True
    return o <= 0 or t - o >= HURT_CLEAR


_SUFFIX = re.compile(r"\s+(?:Jr\.?|Sr\.?|II|III|IV)$")


def _has(names, t):
    """The names (as listed, or without a Jr. / III) that stand in t."""
    out = []
    for n in names:
        if not n:
            continue
        for k in dict.fromkeys((n, _SUFFIX.sub("", n))):
            if k and re.search(rf"(?<![\w]){re.escape(k)}(?![\w])", t):
                out.append(n)
                break
    return out


def inj_arg(line, leg, theirs=()):
    """Does this line argue the OTHER side is short-handed (a 🚑 line about them, a man of theirs said gone, the words)?"""
    t = str(line or "")
    us, opp = str(leg.get("team") or ""), str(leg.get("opp") or "")
    if not t or t.startswith("🔄") or t.startswith(f"🚑 {us} "):
        return False
    if t.startswith("🚑") and opp and opp in t:
        return True
    if _has(theirs, t) and GONE_SAID.search(t):
        return True
    return bool(INJ_TALK.search(t)) and (not us or opp in t or us not in t)


def our_outs_line(line, leg, ours=()):
    """A write-up line that is our own men out: the 🚑 line for our side, the ⚠️ knock naming them, a "both teams are down"
    line, a 🔄 "X is out for <us> too" update (the header carries all of it)."""
    t = str(line or "")
    us = str(leg.get("team") or "")
    if not t or not us:
        return False
    if re.match(rf"^🚑 (?:The )?{re.escape(us)} (?:out\b|questionable\b|(?:is|are) (?:out|missing|without|down)\b|go(?:es)? without\b)", t):
        return True                                          # ("🚑 Warriors out: ..." - never "🚑 Warriors the side: ...")
    m = _OUT_UPDATE.match(t)
    if m:
        return True                                          # (either side: the header's two lists carry the name)
    if t.startswith(("⚠️", "🚑")) and _has(ours, t):
        return True
    return False


def out_plays(line, leg, men):
    """(the line as it may stand, why) - a man who is OUT is never said as playing: a 🏀 / 🌟 part naming him goes (his
    "is out" part too - the header says it), any other line naming him goes unless it says he's gone."""
    t = str(line or "")
    if not t or not men or t.startswith(("🔄", "🚑", "⚠️")) or BOTTOM.match(t):
        return t, ""
    hit = _has(men, t)
    if not hit:
        return t, ""
    if t.startswith(("🏀", "🌟")) and ": " in t:
        head, rest = t.split(": ", 1)
        parts = rest.rstrip(".").split(" · ")
        keep = [p for p in parts if not _has(men, p)]
        if len(keep) == len(parts):
            return t, ""
        said_out = all(re.search(r"\b(?:is|are) out\b", p) for p in parts if _has(men, p))
        return (f"{head}: {' · '.join(keep)}." if keep else ""), (Q_OURS if said_out else f"{Q_PLAYS}: {hit[0]}")
    if GONE_SAID.search(t):
        return t, ""
    return "", f"{Q_PLAYS}: {hit[0]}"


def fights(line, leg, ours_w):
    """(the line as it may stand, why) - "deep squad" / "N guys play real minutes" / "full strength" said of OUR side
    while our own men who matter are out."""
    t = str(line or "")
    us = str(leg.get("team") or "")
    if not t or ours_w < HURT_CLEAR or not DEEP_SAID.search(t) or (us and us not in t):
        return t, ""
    if t.startswith("🏀") and ": " in t:
        head, rest = t.split(": ", 1)
        keep = [p for p in rest.rstrip(".").split(" · ") if not DEEP_SAID.search(p)]
        return (f"{head}: {' · '.join(keep)}." if keep else ""), Q_FIGHTS
    return "", Q_FIGHTS


def bottom_coherent(line, leg, cx, ok_inj):
    """(the bottom line as it may stand, why) - never a sentence that runs our own pick down, never "they're
    short-handed" when we are as short; what's left is the pick, its price and a plain size word."""
    t = str(line or "")
    if not BOTTOM.match(t):
        return t, ""
    lead, parts = _sentences(t)
    keep, whys = parts[:1], []
    for s in parts[1:]:
        if SELF_KNOCK.search(s) and not cx.get("lean"):      # (a lean's "no units - the price is about fair" is what a lean is)
            whys.append(Q_SELF)
        elif not ok_inj and INJ_TALK.search(s):
            whys.append(Q_INJ)
        else:
            keep.append(s)
    why = "; ".join(dict.fromkeys(whys))
    if not why:
        return t, ""
    if len(keep) == 1 and not cx.get("lean"):
        us = str(leg.get("team") or "")
        keep.append(f"Half a unit on {us}." if cx.get("thin") and us and cx.get("market") != "total"
                    else "Half a unit." if cx.get("thin") else "That's the bet.")
    return _join(lead, keep), why


SIDE_HEADS = ("{us} the side", "We on {us}", "Give me {us}", "Riding {us}")
SIDE_HEADS_LEAN = ("We lean {us}", "Lean {us}")
_PICK_TAIL = re.compile(r"^(?:(?:give me|we on|we riding|riding|ride|we got|we lean|we like|we tilt|lean|slight lean|fuck it,?) \x00"
                        r"|\x00 (?:the side|the side here|all day|is the side|are the side))[.!]?$", re.I)   # (a pick, said plain)
_TAIL_SPLIT = re.compile(r"(?<=[.!?])\s+|\s+—\s+|,\s+(?=[^,]*$)")


def _first(name, other, t):
    """Where `name` first stands in t on its own (never inside the other team's longer name): an index or -1."""
    spans = [m.span() for m in re.finditer(rf"(?<![\w]){re.escape(other)}(?![\w])", t)] if other else []
    for m in re.finditer(rf"(?<![\w]){re.escape(name)}(?![\w])", t):
        if not any(a <= m.start() and m.end() <= b and (b - a) > (m.end() - m.start()) for a, b in spans):
            return m.start()
    return -1


def side_first(line, leg, lean=False):
    """🧩 The line under the pick says OUR side first. "🚑 Grizzlies gotta play without Ty Jerome, Zach Edey. Give me
    Warriors." read to the owner as a Grizzlies pick; a line that opens on the other team (or never names us) opens on
    us instead - its own tail moved up front ("🚪 Give me Warriors: 120+ points allowed in 3 of the last 5 for
    Grizzlies."), or a plain head when it has none. -> the line (unchanged when it already says us first)."""
    t = str(line or "").strip()
    us, opp = str(leg.get("team") or "").strip(), str(leg.get("opp") or "").strip()
    if not t or not us or leg.get("market") == "total":
        return t
    m = re.match(r"^(\W*\s*)", t)
    lead, body = (m.group(1) if m else ""), t[len(m.group(1)) if m else 0:]
    iu, io = _first(us, opp, body), (_first(opp, us, body) if opp else -1)
    if iu >= 0 and (io < 0 or iu < io):
        return t
    head = ""
    ld = re.match(r"^([^—]{1,45}?)\s+—\s+(.+)$", body)       # ("Say less — the Avalanche is without ..." - a kicker up
    if ld and len(ld.group(1).split()) <= 6 and not re.search(r"\d", ld.group(1)) \
            and _first(us, opp, ld.group(1)) < 0 and (not opp or _first(opp, us, ld.group(1)) < 0):
        body = ld.group(2)[:1].upper() + ld.group(2)[1:]     #  front that names nobody gives way to our side's name)
    cut = [x for x in _TAIL_SPLIT.split(body) if x and x.strip()]
    if len(cut) > 1:
        tail = cut[-1].strip()
        if _first(us, opp, tail) >= 0 and (not opp or _first(opp, us, tail) < 0) and len(tail.split()) <= 6 \
                and not re.search(r"\d", tail) and _PICK_TAIL.search(tail.replace(us, "\x00")):
            head = tail.rstrip(".!? ")
            body = body[:body.rfind(cut[-1])].rstrip(" ,—-").rstrip()
            if body and body[-1] not in ".!?":
                body += "."
    if not head:
        try:                                              # (11/21 pre-board: "Lean LSU N Orleans:" on a 1u play -
            import sports as _s                           #  leans are gone, the owner 11/16)
            lean = lean and not getattr(_s, "LEANS_GONE", True)
        except Exception:                                 # noqa: BLE001
            lean = False
        pool = SIDE_HEADS_LEAN if lean else SIDE_HEADS
        head = pool[sum(map(ord, us + opp)) % len(pool)].format(us=us)
    head = head[:1].upper() + head[1:]
    if body[:4] == "The ":
        body = "the " + body[4:]
    return f"{lead}{head}: {body}"


def coherent_line(line, leg, cx, st):
    """One breakdown line against the whole card (st = card_state): (the line as it may stand or '', why)."""
    t = str(line or "")
    if not t:
        return t, ""
    if BOTTOM.match(t):
        return bottom_coherent(t, leg, cx, st["inj_ok"])
    if our_outs_line(t, leg, st["ours"]):
        return "", Q_OURS
    new, w = out_plays(t, leg, st["men"])
    if w:
        t = new
        if not t:
            return "", w
    if not st["inj_ok"] and inj_arg(t, leg, st["theirs"]):
        return "", Q_INJ
    new, w2 = fights(t, leg, st["ours_w"])
    if w2:
        return new, "; ".join(y for y in (w, w2) if y)
    return t, w


def card_state(leg, games=None):
    """The whole situation a card is judged against: who's out on both sides, how much each side's absences weigh."""
    try:
        ours, theirs, lost = out_men(leg, games)
    except Exception:                                        # noqa: BLE001
        ours, theirs, lost = {}, {}, set()
    try:
        ow, tw = hurt(leg, games)
    except Exception:                                        # noqa: BLE001
        ow, tw = 0.0, 0.0
    return {"ours": list(ours), "theirs": list(theirs), "men": list(ours) + list(theirs) + list(lost),
            "ours_w": ow, "theirs_w": tw, "inj_ok": ow <= 0 or tw - ow >= HURT_CLEAR}


def one_coherent(line, leg, cx, st, lean=False):
    """The line under the pick against the whole card: ('' = it can't lead, why) or (the line saying our side first, why)."""
    t = str(line or "")
    if not t:
        return t, ""
    if our_outs_line(t, leg, st["ours"]):
        return "", Q_OURS
    new, w = out_plays(t, leg, st["men"])
    if w:
        return "", w
    if not st["inj_ok"] and inj_arg(t, leg, st["theirs"]):
        return "", Q_INJ
    if SELF_KNOCK.search(t) and not lean:
        return "", Q_SELF
    new = side_first(t, leg, lean)
    return new, (Q_SIDE if new != t else "")


def coherent(leg, why, lines, games=None, day=None, cx=None):
    """🧩 The card as a whole -> (the line under the pick, the lines, [(why, line)] caught). Used by the write-up before it
    is saved (sports_breakdown_v24.breakdown) - the same rules the page runs on every render (check / check_one)."""
    if not coherent_on(leg, day):
        return why, lines, []
    cx = cx or {"lean": bool(leg.get("is_lean")), "thin": False, "market": leg.get("market")}
    st = card_state(leg, games)
    caught, out = [], []
    for x in lines or []:
        if not isinstance(x, str):
            out.append(x)
            continue
        new, w = coherent_line(x, leg, cx, st)
        if w:
            caught.append((w, x))
        if new:
            out.append(new)
    w1, ww = one_coherent(why, leg, cx, st, bool(cx.get("lean")))
    if ww:
        caught.append((ww, why))
    return w1, out, caught


def out_chips(leg, games=None, graded=False):
    """🚑 The card's injury header - BOTH teams, plain, no comment: [(team, [names])], theirs then ours. Our own men out
    are said here once and nowhere in the write-up (the owner's FULL injury data rule + "no bad shit in the
    breakdowns")."""
    stale = set(leg.get("stale") or [])
    rep = leg.get("rep_status") or {}
    ok = lambda x: not any(n and n in str(x) for n in stale if rep.get(n) != "out")   # noqa: E731
    theirs = [str(x) for x in leg.get("opp_outs") or [] if ok(x)]
    ours = [str(x) for x in leg.get("outs") or [] if ok(x)]
    us, opp = str(leg.get("team") or ""), str(leg.get("opp") or "")
    for x in leg.get("fresh") or []:
        m = _OUT_UPDATE.match(str(x))
        if not m:
            continue
        lst = ours if m.group(2) == us else theirs if m.group(2) == opp else None
        if lst is not None and not any(m.group(1) in y for y in lst):
            lst.append(m.group(1))
    if graded:
        theirs = [x for x in theirs if not played(leg, (_card_names([x]) or [""])[0], games)]
        ours = [x for x in ours if not played(leg, (_card_names([x]) or [""])[0], games)]
    q = ""
    for x in leg.get("breakdown") or []:                     # (our game-time men: the 🚑 line's "questionable:" half)
        s = str(x)
        if s.startswith(f"🚑 {us} ") and "questionable:" in s:
            q = s.split("questionable:", 1)[1].strip().rstrip(".")
            break
    q = q or str(leg.get("our_q") or "")
    # 🟢 11/23 DOUBLE-CHECKED (Victor: "It said Darren Waller was out for Panthers and he was playing"): the ❓ line is
    # the men still a game-time call RIGHT NOW - a man the game-day read cleared (active / starting / playing), a man
    # ruled out since (he is on the 🚑 line by his own update) and a man off the report come off it; their side's
    # game-time men (a man two sources disagree on - sports.source_check) get the same line
    return [(opp, theirs, q_left(leg, str(leg.get("opp_q") or ""))), (us, ours, q_left(leg, q))]


def q_left(leg, q):
    """The questionable line with every man whose status has been settled since taken off it."""
    if not q:
        return ""
    rep = leg.get("rep_status") or {}
    gone = set(leg.get("stale") or []) | set(leg.get("gameday") or {}) | {n for n, c in rep.items() if c in ("out", "in")}
    parts = [p_.strip() for p_ in re.split(r",\s*(?![^()]*\))", str(q)) if p_.strip()]
    keep = [p_ for p_ in parts if not any(n and n in p_ for n in gone)]
    if keep and all(re.fullmatch(r"\+\d+ more", p_) for p_ in keep):
        return ""
    return ", ".join(keep)


THIN_BODY = 2          # a unit play's card with fewer fact lines than this (after every cut) is a thin card


def kind_of(why):
    """Which card-quality kind a check's catch is ('' = not a quality catch - a fact / wording / freshness one)."""
    w = str(why or "")
    return next((k for k, pats in QUALITY.items() if any(p in w for p in pats)), "")


def quality(leg, why, lines, games=None):
    """🧹 THE CARD-QUALITY READ of one card (its one-liner + its breakdown lines, as given): [(kind, line)] for every
    line that knocks us / argues for them / says nothing / repeats / talks jargon / names a man out who doesn't
    matter. [] = a clean card. tools/card_audit.py scores a card on it; the check itself (check / check_one) cuts the
    same lines on every render."""
    out = []
    wl = str(why or "")
    if wl:
        if knocks_us(wl, leg):
            out.append(("knocks us", wl))
        elif CARD_JARGON.search(wl) and '"' not in wl:
            out.append(("jargon", wl))
        else:
            try:
                if absent_matters(wl, leg, games)[1]:
                    out.append(("non-key absence", wl))
            except Exception:                                # noqa: BLE001
                pass
    coh = None
    try:                                                     # 🧩 11/19: the card as a whole (cards_1119b)
        if coherent_on(leg):
            coh = card_state(leg, games)
            cx_ = {"lean": bool(leg.get("is_lean")), "thin": False, "market": leg.get("market")}
            if wl and not out:
                kw = one_coherent(wl, leg, cx_, coh, cx_["lean"])[1]
                if kw:
                    out.append(("incoherent", wl))
    except Exception:                                        # noqa: BLE001
        coh = None
    body, seen = [], set()
    if wl:
        _dupe(wl, seen)
    try:
        import sports_card_guard as _gd
    except Exception:                                        # noqa: BLE001
        _gd = None
    if wl and (weak_lead(wl, {**(leg or {}), "breakdown": lines}) or (_gd and _gd.scrub(wl)[1])):
        out.append(("filler", wl))
    n_star = 0
    for x in lines or []:
        if isinstance(x, str) and _gd and _gd.scrub(x)[1]:   # (a price claim / "that's just facts" - the bottom line too)
            out.append(("filler", x))
            continue
        if isinstance(x, str) and coh is not None:
            try:
                if coherent_line(x, leg, cx_, coh)[1]:
                    out.append(("incoherent", x))
                    continue
            except Exception:                                # noqa: BLE001
                pass
        if not isinstance(x, str) or BOTTOM.match(x):
            continue
        if x.startswith("💯"):
            n_star += 1
            if n_star > 1:
                out.append(("filler", x))
                continue
        k = kind_of(for_us(x, leg, wl))
        if not k:
            try:
                k = "non-key absence" if absent_matters(x, leg, games)[1] else ""
            except Exception:                                # noqa: BLE001
                k = ""
        if not k and _dupe(x, seen):
            k = "repeats"
        if k:
            out.append((k, x))
        else:
            body.append(x)
    try:
        kept = said_twice(leg, body, wl, games)
        out += [("repeats", x) for x in body if x not in kept]
        import sports_card_sell as _cs                       # (🗣️ 11/22: the same stat about the same team twice)
        if same_on(leg):
            out += [("repeats", x) for x in _cs.dedupe(kept, leg.get("team") or "", leg.get("opp") or "", wl, leg=leg)[1]]
    except Exception:                                        # noqa: BLE001
        pass
    return out


def says_why(leg, why, lines):
    """🗣️ 11/22 THE CARD SELLS THE PICK: (reason-backed lines, matchup lines) on a card - the line under the pick counts.
    sports_card_sell.reason_backed says which is which."""
    import sports_card_sell as _cs
    ks = [_cs.reason_backed(x, leg) for x in ([why] if why else []) + [y for y in lines or [] if isinstance(y, str) and not BOTTOM.match(y)]]
    return ks.count("reason"), ks.count("matchup")


def fact_lines(lines):
    """How many lines of a card's breakdown argue the case (not the ⚠️ / bottom / update / roster lines)."""
    return sum(1 for x in lines or [] if isinstance(x, str) and not BOTTOM.match(x)
               and not x.startswith(("⚠️", "🔄", "✅ Update", "🌟", "🟡", "🔒", "💎")))
