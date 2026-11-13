"""🛡️ THE CARD GUARD (the owner, 10/1: "wire everything into the engine so it can't be making all these mistakes and then
I gotta go tell you to fix it"). Every line a card says - the write-up, the line under the pick, the review - passes
through here before it posts. A line that repeats a mistake the owner already caught is dropped (and logged), never
posted. The bottom line is never dropped - it's cut back to the pick and its price.

Each rule is one of his corrections:
  - jargon: "50 in 100, the price needs 48" (10/1 - technical jargon, plain words only)
  - the wrong sport's position word: "the Browns without goalie Teven Jenkins" (10/1 - a football G is a guard)
  - a name the books haven't set: "TBA gets the ball" (10/1 audit)
  - filler with no fact: "they travel just fine", "just the better team", "division rivals", "no love lost" (10/1)
  - the NEVER words (sports_owner_lingo.NEVER): "real talk", "chalk", "what counts"...
  - a broken template: "None", "{", "}", "nan"
"""
import re

import sports_owner_lingo

JARGON = re.compile(r"\b\d{1,3}\s*(?:times\s+)?in\s+100\b|\bprice\s+(?:only\s+)?needs\b|\bbreak[- ]even\b|"
                    r"\bPDO\b|\bdog check\b|\bdog score\b|\bCorsi\b|\bxG\b|\bFenwick\b|\bEV\b|\bno-vig\b|\bvig\b", re.I)
#   (10/29, the owner: "the lingo still sucks" - stat-head words never post on a card: PDO, the dog check / dog score,
#    Corsi / xG, "the vig" - the card says it in plain words or not at all)
UNSET = re.compile(r"\bTBA\b|\bTBD\b")
FILLER = re.compile(r"travel just fine|just the better team|they'?re just better|division rivals|no love lost|"
                    r"everything above tips|everything above is why|and it ain'?t close|our own reasons\.|different reasons\.|got there on our own|"
                    r"the rest is on the field|"
                    # (10/21, the owner: "the descriptions and the breakdowns just suck ... very vague" - the zero-fact
                    #  verdict and record lines, so they can't come back)
                    r"numbers did the talking|winning this one\. we riding|that'?s the engine talking|"
                    r"already did our homework|gon'? see what they do with it|the homework'?s done|did the digging already|"
                    r"we know the rest\.|now go prove it|see what it'?s worth|record don'?t cash tickets|"
                    r"the more rested squad|well-rested and ready|extra days to get right|rest edge goes to|"
                    r"sometimes the public gotta win|public'?s usually (wrong|on the wrong side)|for once the casuals|"
                    r"crowd can'?t make up its mind|nobody knows nothing|"
                    # (11/12, Victor on the Giants card: "where does it get that info?" - a 4th-down claim with no plays
                    #  behind it; the line says the real counts now, sports_go4.card_line)
                    r"goes for it on 4th down way more|keep the offense out there way more often|"
                    r"goes for it on 4th down a lot more than|"
                    r"^\W*🧠\s*(the engine|our read|we'?ve got|we like|close to 50-50|the numbers)\b", re.I)
#   (10/2: "we got our own reasons." with no reason after it is filler - the owner's never-vague rule; 10/5: "Guardians
#   are 85-77 right now - the rest is on the field" just repeats the record the line above already said; 10/21: a 🧠 line
#   that opens with the verdict instead of a fact - "🧠 The engine's got Trail Blazers winning this one" - is filler)
BROKEN = re.compile(r"\bNone\b|\bnan\b|[{}]")
ZONES = re.compile(r"few time zones|several time zones|time zones and all|jet-lag game", re.I)
SPLITS = re.compile(r"\b\d{1,3}% of (?:the |all )?(?:[a-z]+ )?(?:bets|tickets|action|money|cash|crowd|public)\b|public's team"
                    r"|only \d{1,3}% of the public|public side is|public is all over|public's got \d|public's with us"
                    r"|public's on ", re.I)   # (the owner, 11/12: "97% the action is on whatever ... doesn't tell you
#                                               anything" - no betting-split line on any card, posted ones included)
#   (11/12 audit: "Long trip for Marquette, time zones and all" - Milwaukee to Ann Arbor is ONE zone; the body-clock
#    factor fires at one zone, so a card written before the fix never claims a long trip or several zones)
WRONG_POS = {   # words that can't belong to the sport
    "nfl": re.compile(r"\bwalking bucket\b|\bgoalie|\bgoaltend|\bpitcher\b|\bdefenseman\b", re.I),
    "ncaaf": re.compile(r"\bwalking bucket\b|\bgoalie|\bgoaltend|\bpitcher\b|\bdefenseman\b", re.I),
    "nba": re.compile(r"\bgoalie|\bgoaltend|\bquarterback\b|\bpitcher\b|\bdefenseman\b", re.I),
    "ncaab": re.compile(r"\bgoalie|\bgoaltend|\bquarterback\b|\bpitcher\b|\bdefenseman\b", re.I),
    "nhl": re.compile(r"\bwalking bucket\b|\bquarterback\b|\bpitcher\b|\bpoint guard\b", re.I),
    "mlb": re.compile(r"\bwalking bucket\b|\bgoalie|\bgoaltend|\bquarterback\b|\bdefenseman\b", re.I),
}
DROPPED = []    # this run's dropped lines (the run log prints them - so a new kind of slip gets caught and wired in)


def problem(line, league=None):
    """Why this line can't post, or ''."""
    t = str(line or "")
    if not t.strip():
        return ""
    low = t.lower()
    if t.lstrip().startswith("🆚"):                           # (the owner, 10/5: the head-to-head study was dead in every
        return "head-to-head history"                        #  sport - "they own this matchup" made picks sound stronger)
    if t.lstrip().startswith("🥅 In net"):                  # (the owner, 10/6: no goalie confirmations on the cards)
        return "goalie confirmation"
    if any(w in low for w in sports_owner_lingo.NEVER):
        return "a NEVER word"
    if JARGON.search(t):
        return "jargon"
    if UNSET.search(t):
        return "a name not set yet"
    if FILLER.search(t):
        return "filler with no fact"
    if BROKEN.search(t):
        return "a broken template"
    if ZONES.search(t):
        return "a time-zone claim it can't see"
    if SPLITS.search(t):
        return "a betting-split line"
    if t.lstrip().startswith("🧯"):                           # (the owner, 10/5: a retired player's death is not the
        import sports_news                                    #  team's "personal stuff")
        if sports_news.obituary(t):
            return "a former player's death isn't team drama"
    rx = WRONG_POS.get(league)
    if rx and rx.search(t):
        return "the wrong sport's position word"
    return ""


def _bottom_safe(line):
    """A bottom line that tripped a rule: cut back to the pick and its price ('✅ Bottom line: Steelers (-148).')."""
    m = re.match(r"(✅ Bottom line:[^()]*\([+-]?\d+\))", line)
    return (m.group(1) + ".") if m else "✅ Bottom line: the pick's up."


_AGREE = {"are": "is", "have": "has", "were": "was", "aren't": "isn't", "haven't": "hasn't", "weren't": "wasn't",
          "don't": "doesn't", "go": "goes", "do": "does"}
for _v in ("take", "come", "get", "keep", "sit", "play", "win", "lose", "allow", "give", "hold", "cover",
           "need", "look", "travel", "handle", "drop", "pack", "outscore", "average", "walk", "roll", "bring", "carry",
           "make", "stay", "grade", "want", "know"):
    _AGREE[_v] = _v + "s"                                    # ("Iowa State take care of home" -> "takes"; never a verb
    #                                                          that is also its own past tense - put, beat, run - or a
    #                                                          noun that follows a name - score, head (coach), run (game))
#   (10/30 weekend sweep - the owner's 10/27 rule, "Wild holds", "Mammoth is leaking": team verbs agree. The 10/29 sweep
#    fixed the tails, the risk line and the bottom lines at the pool; the ~70 body pools still say "{us} are healthy" /
#    "{us} have dropped 2 straight" - right for the Bruins, wrong for Iowa State, Fresno St, Delaware and the Lightning.
#    A Saturday board is mostly college names. The guard is the last stop every card passes, so the fix lives here: a
#    singular name's "are / have / were" becomes "is / has / was". "been" stays - "Iowa State been the better team" is
#    how he talks.)


def agree(line, *teams):
    """The line with every team verb agreeing with its name: 'Iowa State are 3-4' -> 'Iowa State is 3-4', 'the
    Lightning have won' -> 'the Lightning has won'; a plural name ('the Bruins are') is untouched."""
    t = str(line or "")
    try:
        from sports_breakdown_v24 import vb
    except Exception:                                        # noqa: BLE001 - no verb table = no change
        return t
    for team in teams:
        team = str(team or "").strip()
        if not team or vb(team, "are", "is") == "are":
            continue
        rx = re.compile(r"(\b" + re.escape(team) + r") (" + "|".join(re.escape(k) for k in _AGREE) + r")\b(?![-'])")
        others = [str(o or "").strip() for o in teams if str(o or "").strip() and str(o or "").strip() != team]

        def fix(m, t_=t, others_=others):                    # (11/4 audit: "UConn and North Carolina walks in" - the
            head = t_[:m.start()]                            #  tail of "<the other team> and <team>" is a plural subject)
            if any(head.endswith(f"{o} and ") or head.endswith(f"{o} & ") for o in others_):
                return m.group(0)
            return m.group(1) + " " + _AGREE[m.group(2)]
        t = rx.sub(fix, t)
    return t


# 11/12 (the owner: "the lingo just keeps sounding so retarded"): the canned tail sentences that ride on the end of a
# fact line and say nothing - "⚠️ Blackhawks have dropped 6 straight. We see it. Ain't scared of it." keeps the fact and
# loses the tail. Whole sentences only; a line left with no fact goes.
TAILS = re.compile(
    r"^(?:we see it|ain'?t scared of it|not us|we'?ll take (?:it|that|that matchup|our chances)|bodies missing over there|"
    r"that'?s real depth gone|we ain'?t blind to it - we just like our side more|we been better|we finna see|"
    r"road trips ain'?t their thing|road trips been rough on 'em|they win in other people'?s houses|true|"
    r"still ain'?t enough to flip us|that'?s who we'?re going against|scoreboard says us|we on the other side|"
    r"we eating|hostile crowd\?|they don'?t care|they been getting it done|both feeling good, one leaves pissed|"
    r"that don'?t last|that part don'?t help us, not gonna lie|let the public have 'em|aggressive wins|"
    r"short-handed against us|we'?ll live with it|we know it, and we still like the side|somebody'?s streak ends (?:tonight|today)|"
    r"bus-trip team|that snaps back|ask the teams that came through|say less|they don'?t travel|they hate leaving the house|"
    r"their own crowd'?s been watching 'em lose|tough out in their own house|the books are sleeping on that|"
    r"one of 'em gets right (?:tonight|today)|both got something to prove|our d shows up|fun to ride, not a money play|"
    r"keep stacking|the public'?s eating with us on this one|same side as the public on this one|"
    r"(?-i:Still [A-Z][\w.' -]{1,30}))[.!?]?$", re.I)
_SENTS = re.compile(r"(?<=[.!?])\s+")


def strip_tails(line):
    """The line without its filler tail sentences ('' when nothing with a fact is left)."""
    t = str(line or "")
    if not t.strip():
        return t
    m = re.match(r"^(\W*\s*)", t)
    lead = m.group(1) if m else ""
    parts = _SENTS.split(t[len(lead):])
    keep = [x for x in parts if not TAILS.match(x.strip())]
    if len(keep) == len(parts):
        return t
    body = " ".join(keep).strip()
    return (lead + body) if body else ""


def clean(lines, league=None, who="", opp=""):
    """The card's lines with every one that repeats a known mistake taken out (the bottom line cut back, never lost),
    the team verbs agreeing with the names (agree - ours and the opponent's), the filler tails cut (strip_tails)."""
    out = []
    for x in [strip_tails(y) if isinstance(y, str) else y for y in lines or []]:
        if isinstance(x, str) and not x.strip():
            continue
        why = problem(x, league)
        if not why:
            out.append(agree(x, who, opp) if isinstance(x, str) else x)
            continue
        DROPPED.append(f"{who}: {why}: {str(x)[:90]}")
        print(f"CARD GUARD ({why}) dropped for {who}: {str(x)[:90]}", flush=True)
        if str(x).startswith("✅ Bottom line:"):
            out.append(agree(_bottom_safe(str(x)), who, opp))
    return out


def one(line, league=None, who="", opp=""):
    """A single line (the line under the pick, a review): itself, or '' when it repeats a known mistake."""
    kept = clean([line], league, who, opp) if line else []
    return kept[0] if kept else ""
