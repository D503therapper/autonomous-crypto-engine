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

JARGON = re.compile(r"\b\d{1,3}\s*(?:times\s+)?in\s+100\b|\bprice\s+(?:only\s+)?needs\b|\bbreak[- ]even\b", re.I)
UNSET = re.compile(r"\bTBA\b|\bTBD\b")
FILLER = re.compile(r"travel just fine|just the better team|they'?re just better|division rivals|no love lost|"
                    r"everything above tips|and it ain'?t close|our own reasons\.|different reasons\.|got there on our own|"
                    r"the rest is on the field", re.I)
#   (10/2: "we got our own reasons." with no reason after it is filler - the owner's never-vague rule; 10/5: "Guardians
#   are 85-77 right now - the rest is on the field" just repeats the record the line above already said)
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


def clean(lines, league=None, who=""):
    """The card's lines with every one that repeats a known mistake taken out (the bottom line cut back, never lost)."""
    out = []
    for x in lines or []:
        why = problem(x, league)
        if not why:
            out.append(x)
            continue
        DROPPED.append(f"{who}: {why}: {str(x)[:90]}")
        print(f"CARD GUARD ({why}) dropped for {who}: {str(x)[:90]}", flush=True)
        if str(x).startswith("✅ Bottom line:"):
            out.append(_bottom_safe(str(x)))
    return out


def one(line, league=None, who=""):
    """A single line (the line under the pick, a review): itself, or '' when it repeats a known mistake."""
    kept = clean([line], league, who) if line else []
    return kept[0] if kept else ""
