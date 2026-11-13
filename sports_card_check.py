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
    r"\bno money on it\b|not by enough for units|too close for units", re.I)
UNIT_TALK = re.compile(
    r"\btap in\b|\block it in\b|half a unit|\bfull unit\b|(?<!no )\bunits? on (?:it|this|him|them)\b|\bbigger bet\b|"
    r"\bbig bet\b|\bload up\b|\beasy money\b|\bfree money\b|\bhammer\b|\bsmash\b|trust the algorithm|"
    r"\bwhole hood\b|\bmax play\b|\bwe riding\b|\bstill riding\b|\blet'?s eat\b", re.I)
HYPE = re.compile(r"\ball day\b|\bhammer\b|\bload up\b|\bmax play\b|\bbig(?:ger)? bet\b|\block it in\b|\bfree money\b|"
                  r"\beasy money\b|\bcan'?t lose\b|\bsmash\b|\bwe going big\b", re.I)
LOCK_TALK = re.compile(r"\block it in\b|\bour lock\b|\bthis (?:is )?a lock\b|\bit'?s a lock\b|\ba lock\b(?! of)", re.I)
NOT_LOCK = re.compile(r"\b(?:not|no|never) (?:a |the )?lock\b", re.I)
COIN = re.compile(r"coin[- ]flip|\b50-50\b|close to even|\btoss-up\b|could go either way|either way|"
                  r"near even\b|about even\b|by a nose\b", re.I)
COIN_BAND = (0.42, 0.58)        # a moneyline side may be called a coin flip only when its read AND its price sit here
#   (the 11/13 audit: "close to a coin flip - Seahawks by a hair" at -148 / a STRONG LEAN read of 60%; "our read says
#    coin flip" on the Panthers +164 at a 36.6% read; "Toss-up, close to even" on the Pacers -148. sports_breakdown_v24
#    .COIN_FLIP keeps the generator's band; this is the last stop for every card, posted ones too)
BOTTOM = re.compile(r"^\W*(?:✅|🟡)\s*Bottom line:")
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
A_AN = re.compile(r"\b([Aa]) (8|11|18|8\d|8\d\d|11\d)(?=[-\s])")
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
    keep = []
    for i, s in enumerate(parts):
        why = ""
        s0 = s.strip()
        if bottom and i == 0:                                # ("Bottom line: Celtics (-124)." - the head stays)
            keep.append(s)
            continue
        if cx.get("unit") and LEAN_TALK.search(s0):
            why = "a lean's words on a unit play"
        elif cx.get("unit") and COIN.search(s0) and not re.search(r"\bprice\b|\bnumber\b", s0, re.I):
            why = "a coin-flip line on a unit play"          # ("Could go either way." on the 1u Celtics -124)
        elif cx.get("lean") and UNIT_TALK.search(s0):
            why = "a unit play's words on a lean"
        elif cx.get("thin") and HYPE.search(s0):
            why = "hype on a thin ½u play"
        elif not cx.get("lock") and LOCK_TALK.search(s0) and not NOT_LOCK.search(s0):
            why = "Lock words on a pick that isn't the Lock"
        elif COIN.search(s0) and not coin_ok(cx):
            why = "a coin flip said of a side that isn't one"
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
    out = _join(lead, keep) if keep != parts else t
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
    if out and WARM.search(out):
        whys.append("a climate claim (the 11/12 rule says it with the degrees or not at all)")
        out = "" if not re.search(r"\d+\s*°|\d+ degrees", out) else out
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
    start = v._t(g["start"])
    fin = [x for x in _finals(games, lg) if v._t(x["start"]) < start]
    if not v.seen_all(fin, tid, start, lg):
        return {"unseen": True}
    s = v._season(v._team_games(fin, tid), start)
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
    return {"rec": {rec([v._line(x, tid) for x in reg]), rec(lines)}, "home": rec(home), "road": rec(road),
            "last5": rec(lines[-5:]), "streak": streak, "lines": lines, "rest": v._days(start, v._t(s[-1]["start"])) if s else None,
            "n": len(s)}


REC = re.compile(r"(?<![\d.:/+-])(\d{1,3})-(\d{1,3})(?:-(\d{1,2}))?(?![\d%:/]|\.\d|-\d)")
SCORE_AFTER = re.compile(r"^\s*(?:win|loss|victory|beating|final|in overtime|in a shootout|(?:@|vs\.?) (?-i:[A-Z])|\.\s*that'?s what|(?:over|by) (?:the )?(?-i:[A-Z]))", re.I)
SCORE_BEFORE = re.compile(r"(?:(?-i:\b[WL])|\ban?|\bput|\bby|\bbrakes off [\w.' ]+,|"
                          r"(?:smacked|spanked|clapped|embarrassed|cooked|buried|beat|took|blanked|whipped|handled) [\w.' ]{0,30}?|"
                          r"\bwon|\blost|\bended)\s*$", re.I)
SCORE_VERB = re.compile(r"spank|smack|\bbeat\b|beat the brakes|clapped|embarrass|\bput\b|did to|cooked|buried|"
                        r"\btook\b|\bwin over\b|\bloss to\b|\bwon\b|\blost\b|beating", re.I)
NO_CHECK = re.compile(r"last (?:season|year)|a year ago|year ago|since 20\d\d|these two met|all-time|\bATS\b|against the "
                      r"spread|as a dog|as a favorite|\bin (?:one|two)-score|\bh2h\b|head[- ]to[- ]head|last meeting|"
                      r"\bseries\b|\bbowl\b|\bcareer\b|\bstarts?\b|\bsave %|\bTDs?\b|\bpicks?\b|\byards\b|minutes|per 48|"
                      r"\bsince\b|\bquarter\b|\bperiods?\b", re.I)
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
    if t.lstrip().startswith(("🚑", "🔄", "🧯", "🤒", "📣", "🌟", "🏀", "🥅", "🧱", "🎯", "🗑️ ")) and not REC.search(t.split("—")[0]):
        return ""
    us, them = leg.get("team") or "", leg.get("opp") or ""
    names = [us, them]
    fx = {}

    def F(i):
        if i not in fx:
            fx[i] = team_facts(games, leg, "us" if i == 0 else "them")
        return fx[i]
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
        elif SCORE_AFTER.search(after[:20]) or SCORE_BEFORE.search(before[-45:]) or max(a, b) > 30 \
                or (SCORE_VERB.search(t) and not re.search(r"\b(?:is|are|sit|sits|come in|comes in|at|record)\s*$", before)
                    and not re.match(r"\s*(?:at home|on the road|away|in their|for\b|,|;|\.|\s*$| vs \d| against \d| to \w+'? \d)", after)):
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
        if mm and kind == "rec":                             # ("10-6 for Mammoth", "2-1 (Elon)")
            i = names.index(mm.group(1))
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
    for x in lines or []:
        if not isinstance(x, str):
            out.append(x)
            continue
        new, w = wording(x, cx, leg)
        if new and not BOTTOM.match(new):
            fw = facts(new, leg, games)
            if fw:
                new, w = "", "; ".join(y for y in (w, "a fact the game files don't back: " + fw) if y)
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


def check_one(pk, leg, line, games=None, where="render"):
    """The line under the pick: itself, rewritten, or '' (then the card falls back to its first real fact)."""
    if not line:
        return ""
    cx = ctx_of(pk, leg)
    new, w = wording(line, cx, leg)
    if new and not w:
        fw = facts(new, leg, games)
        if fw:
            new, w = "", "a fact the game files don't back: " + fw
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
