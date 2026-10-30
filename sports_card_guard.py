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
                    r"^\W*🧠\s*(the engine|our read|we'?ve got|we like|close to 50-50|the numbers)\b", re.I)
#   (10/2: "we got our own reasons." with no reason after it is filler - the owner's never-vague rule; 10/5: "Guardians
#   are 85-77 right now - the rest is on the field" just repeats the record the line above already said; 10/21: a 🧠 line
#   that opens with the verdict instead of a fact - "🧠 The engine's got Trail Blazers winning this one" - is filler)
BROKEN = re.compile(r"\bNone\b|\bnan\b|[{}]")
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
        t = rx.sub(lambda m: m.group(1) + " " + _AGREE[m.group(2)], t)
    return t


def clean(lines, league=None, who="", opp=""):
    """The card's lines with every one that repeats a known mistake taken out (the bottom line cut back, never lost),
    the team verbs agreeing with the names (agree - ours and the opponent's)."""
    out = []
    for x in lines or []:
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
