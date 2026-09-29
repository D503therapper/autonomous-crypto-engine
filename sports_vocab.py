"""OUR VOCABULARY: the words and phrases every write-up is built from (breakdowns, reviews, live lines, notes).

The owner: "a whole ass vocabulary - thousands of phrases and words. If it was me, I'd use the same words here and
there, but the phrases be changing around." So a line is never one fixed sentence: it's a skeleton with slots, and
each slot draws from a pool of ways to say that piece. `variants()` rolls a line out many ways; Voice.say (in
sports_breakdown) keeps whichever one repeats no 4-word run from the board or from yesterday.

Template syntax:
  {me} {them} {he} {him} {his} {He} ...  values passed in (the names, pronouns, numbers)
  {book} {algo} {kick} ...                a slot from SLOTS below ({Book} = capitalized)
  [a|b|c]                                 an inline pick (one of a / b / c; [a|] = maybe say a)
Never: "real talk", "chalk" (the owner's rule) - test_vocab checks it."""
import random
import re

SLOTS = {
    # who's who
    # singular only (every entry takes "says / has / thinks"): no "the bookies", no "our numbers"
    "book": ["the book", "Vegas", "the sportsbook", "the line", "the market", "the number", "the house", "the price",
             "the oddsmaker"],
    "algo": ["the algorithm", "the engine", "our model", "the math", "our read", "the data", "our projection",
             "the model", "our math"],
    # the pick, said with confidence
    "ride": ["riding", "rolling with", "backing", "going with", "siding with", "taking", "on", "all over",
             "locked in on", "betting on", "sticking with", "in on"],
    "sure": ["no hesitation", "all day", "zero doubt", "no second guessing", "easy decision", "no debate",
             "no question", "without blinking", "top to bottom", "with our whole chest", "no overthinking",
             "and it ain't close", "hands down", "every time"],
    "better": ["the better player", "the better team", "the sharper side", "the stronger side", "the real deal",
               "a tier above", "levels above", "the class of this matchup"],
    "cheap": ["too cheap", "a discount", "mispriced", "short", "off", "light", "a bargain", "priced wrong",
              "undervalued", "disrespectful", "a steal", "not respecting the matchup"],
    "wins": ["wins this", "gets the W", "takes it", "closes it out", "handles business", "gets it done",
             "comes out on top", "finishes the job", "takes care of it", "walks away with it", "punches the ticket"],
    "beat": ["handle", "take care of", "get past", "run through", "outlast", "put away", "cook", "dust", "outclass",
             "handle light", "get the better of", "take down", "wear down", "outwork"],
    "more": ["way more often than not", "more often than the price says", "a lot more than the book thinks",
             "more than people think", "most nights", "more than this number implies", "way more than that"],
    # the edge
    "gap": ["That gap is the money.", "That's the edge.", "That's the difference.", "That gap is why we're here.",
            "Numbers don't lie.", "That's value.", "That spread between us and them is the whole reason.",
            "That's where the money's at.", "Math is math.", "That's a real gap."],
    "edge_noun": ["edge", "value", "gap", "cushion", "angle", "advantage"],
    # sayings after a line (optional flavor; short ones repeat, that's fine)
    "kick": ["", "", "", "", "", "Let's eat.", "Nice nice.", "Cook.", "Easy work.", "Run it.", "We outside.",
             "Say less.", "Book it.", "Light work.", "Tuck in.", "Get in.", "Bet.", "We're good.", "Pull up.",
             "Period.", "Facts.", "Simple.", "Done deal.", "Don't overthink it.", "You already know.",
             "Stamp it.", "Buckle up.", "We live.", "Clean.", "Straight up.", "On sight."],
    # how a matchup looks
    "hot": ["rolling", "on a heater", "cooking", "hot", "in a groove", "stacking W's", "on fire", "feeling it",
            "locked in", "playing out of their mind"],
    "cold": ["ice cold", "struggling", "sliding", "in a funk", "stuck in the mud", "dropping games",
             "searching for answers", "limping in", "off"],
    "tired": ["tired legs", "heavy legs", "legs on empty", "a gas tank on E", "dead legs", "no juice",
              "a sore body", "worn down"],
    "crowd": ["the crowd", "the building", "the home fans", "the whole stadium", "the people", "the home folks"],
    # result words (reviews)
    "won_v": ["cashed", "hit", "came through", "got there", "delivered", "paid", "landed", "cleared", "went green",
              "banked"],
    "lost_v": ["missed", "fell short", "didn't get there", "came up short", "went red", "slipped",
               "didn't land", "got away"],
    "clean": ["clean", "no sweat", "stress free", "never in doubt", "smooth", "easy", "comfortable", "cruise control"],
    "sweat": ["a sweat", "a nail-biter", "tight", "a grind", "close", "heart-attack stuff", "down to the wire",
              "a coin-flip finish"],
    "shrug": ["It happens.", "On to the next.", "Part of it.", "Can't win em all.", "Reset and run it.",
              "Shake it off.", "Tomorrow's another slate.", "Next one.", "Short memory.",
              "Numbers stay the numbers.", "Chin up.", "We keep stacking."],
}

_INLINE = re.compile(r"\[([^\[\]]*)\]")
_SLOT = re.compile(r"\{(\w+)\}")


def _fill(t, rng, kw):
    for _ in range(4):                                   # slots can hold [..|..] and {..} themselves
        t = _INLINE.sub(lambda m: rng.choice(m.group(1).split("|")), t)
        def slot(m):
            k = m.group(1)
            if k in kw:
                return str(kw[k])
            pool = SLOTS.get(k.lower())
            if pool is None:
                return m.group(0)
            x = rng.choice(pool)
            return x[:1].upper() + x[1:] if k[:1].isupper() else x
        t2 = _SLOT.sub(slot, t)
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([.,!?])", r"\1", t)
    return t[:1].upper() + t[1:] if t else t


def variants(templates, seed, n=60, **kw):
    """Up to n different ways to say a line (for Voice.say), rolled from the templates with this seed."""
    rng = random.Random(str(seed))
    out, seen = [], set()
    for _ in range(n * 8):
        x = _fill(rng.choice(templates), rng, kw)
        if x and x not in seen:
            seen.add(x)
            out.append(x)
            if len(out) >= n:
                break
    return out


def one(templates, seed, **kw):
    """Just one roll (for lines that don't go through Voice)."""
    return _fill(random.Random(str(seed)).choice(templates), random.Random(f"{seed}|f"), kw)


def supply(templates):
    """Roughly how many different lines these templates can make (slots and inline picks multiplied out)."""
    total = 0
    for t in templates:
        c = 1
        for m in _INLINE.finditer(t):
            c *= len(m.group(1).split("|"))
        for m in _SLOT.finditer(t):
            pool = SLOTS.get(m.group(1).lower())
            if pool:
                c *= len(set(pool))
        total += c
    return total
