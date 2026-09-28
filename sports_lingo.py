"""THE LINGO MIXER: an endless supply of our lines. A line = an opener + an ending, mixed per game, so the same thing
never reads the same way twice. Feed the options into sports_breakdown.Voice.say() - it still keeps every phrase to
once per dashboard (the slang families) and never repeats a wording on the board.

Add openers/endings any time - every one added multiplies the supply."""
import random

# a player who's really good (he's our side)
GOOD_OPEN = [
    "{p} is nice.", "{p} nice nice.", "{p} is different.", "{p} is a problem.", "{p} been cooking.",
    "{p} is HIM.", "{p} is built different.", "Y'all know {p} is nice.", "{p}? Nice nice.", "{p} on another level.",
    "{p} ain't regular.", "Don't sleep on {p}.",
    "{p} got that dog in {him}.", "{p} came to work.", "{p} locked in.", "{p} been dialed in.", "{p} a bad man.",
    "{p} got it rolling.", "{p} stay ready.", "{p} got the juice right now.", "Give me {p} all day.",
    "{p} the real deal.", "{p} on a heater.", "{p} carrying.",
]
GOOD_END = [
    "Watch {him} work.", "{o} got no answer for {him}.", "{He} about to go off.", "{He} ain't playing no games today.",
    "{o} in for a long day.", "Light work for {him}.", "That's a problem for {o}.", "{o} better pray.",
    "{He} gon' eat.", "Just watch.", "{He} been waiting on this one.", "{o} can't hang with {him}.",
    "{He} finna put on a show.", "It's gon' be a long night for {o}.", "{o} ain't ready.",
    "{He} run this.", "Easy work.", "{He} about to make {o} look silly.", "Too much for {o}.",
    "{He} built for this matchup.", "{o} gon' be seeing {him} in their sleep.", "{He} don't miss in spots like this.",
    "Mark it down.", "{He} gon' handle {o} light.", "{o} got nobody to guard {him}.", "{He} feeling it lately.",
    "{o} already know what time it is.", "{He} been on one.", "Different breed.", "{o} in trouble.",
    "{He} gon' make it look easy.", "{o} gon' feel {him} all game.", "{He} got {o} number.", "{He} ain't scared of nobody.",
    "{o} can't stop {him}, only hope to contain.", "{He} bringing the heat tonight.", "{o} gon' need a miracle.",
    "{He} gon' take over.", "Book it.", "Say less.", "{o} picked the wrong night.", "{He} got something to prove.",
    "{He} stay money.", "{o} ain't seen nothing like {him}.", "It's {his} world, {o} just living in it.",
    "{He} gon' remind everybody tonight.", "Clock in, clock out.", "{o} better bring backup.",
    "{He} gon' feast.", "{o} can't keep up.",
]

# the other side has been bad (never "chalk")
BAD_OPEN = [
    "{o} been complete ass.", "{o} ain't it right now.", "{o} been sliding.", "{o} can't get out their own way.",
    "{o} been struggling bad.", "{o} look lost.", "{o} been a mess lately.", "Nothing going right for {o}.",
]
BAD_END = [
    "We taking advantage.", "Somebody gotta pay for that.", "We eating off it.", "Tonight ain't changing that.",
    "They about to get exposed again.", "We riding against 'em.", "No reason to trust 'em now.",
    "That's our edge.", "Keep fading 'em.", "They due for another L.",
]


def _mix(opens, ends, seed, n, **kw):
    rnd = random.Random(str(seed))
    combos = [(a, b) for a in opens for b in ends]
    rnd.shuffle(combos)
    out = []
    cap = lambda s: s[:1].upper() + s[1:]
    for a, b in combos[:n]:
        out.append(f"{cap(a.format(**kw))} {cap(b.format(**kw))}")
    return out


def good(player, opp, seed, he="he", n=24):
    """n fresh 'player is nice' lines for this game (pass them to Voice.say as the options)."""
    him, He, his = ("her" if he == "she" else "him"), he.capitalize(), ("her" if he == "she" else "his")
    return _mix(GOOD_OPEN, GOOD_END, seed, n, p=player, o=opp, he=he, He=He, him=him, his=his)


def bad(opp, seed, n=12):
    """n fresh 'the other side has been bad' lines."""
    return _mix(BAD_OPEN, BAD_END, seed, n, o=opp)


def supply():
    """How many different lines each mixer can make right now."""
    return {"good": len(GOOD_OPEN) * len(GOOD_END), "bad": len(BAD_OPEN) * len(BAD_END)}


# ---- REVIEWS: a line on every graded pick in Past Results. A middle that fits what happened + a closer, mixed per
# pick, so the same review never reads the same way twice ({t} = our side, {o} = the other side, {x} = the number)
REVIEW_MID = {
    ("fav", "won"): ["{t} handled business{s}.", "{t} did what favorites do{s}.", "Laid the price and {t} took care of it{s}.",
                     "{t} was too much for {o}{s}.", "{t} went to work on {o}{s}.", "{t} smacked that{s}.",
                     "{o} never had a chance{s}.", "{t} made it look easy{s}."],
    ("fav", "lost"): ["{t} shit the bed as the favorite{s}.", "{t} was supposed to handle {o} and fumbled it{s}.",
                      "Favorite folded — {o} had other plans{s}.", "{t} was booty cheeks when it counted{s}.",
                      "{t} laid an egg{s}.", "{o} cheeks clapped {t}{s}. Didn't see that coming.",
                      "We had {t} and they never showed up{s}."],
    ("dog", "won"): ["Dog barked — {t} took down {o}{s}.", "{t} came in as the dog and ate{s}.",
                     "Nobody believed in {t} but us{s}.", "Plus money and {t} delivered{s}.",
                     "The value was real — {t} got it done{s}.", "{t} made the line makers look silly{s}."],
    ("dog", "lost"): ["{t} had the value, just didn't have the juice{s}.", "Dog didn't bark this time{s}.",
                      "The price was right, {t} wasn't{s}.", "{t} gave us nothing{s}.", "{o} held off our dog{s}.",
                      "{t} came up short{s}."],
    ("spread", "won"): ["{t} covered the {x}{s}.", "{t} with the {x}? Covered{s}.", "Took the points with {t} and they covered{s}.",
                        "{t} stayed inside the number{s}.", "The {x} was the right side{s}."],
    ("spread", "lost"): ["{t} couldn't cover the {x}{s}.", "{t} fell on the wrong side of the {x}{s}.",
                         "The {x} wasn't enough for {t}{s}.", "{t} didn't get there against the number{s}."],
    ("live_back", "won"): ["We trusted the comeback and {t} delivered{s}.", "{t} was down and we rode it anyway — paid{s}.",
                           "The algorithm called the comeback. {t} came through{s}.", "Never count a live dog out — {t} came back{s}.",
                           "{t} climbed out the hole{s}."],
    ("live_back", "lost"): ["The algorithm was confident on the comeback but was off this time, SMH{s}.",
                            "We thought {t} was coming back, but they shit the bed{s}.",
                            "{t} had the window and never climbed through it{s}.", "Comeback never came — {t} ran outta time{s}.",
                            "{t} had a shot and fumbled the bag{s}.", "We saw the comeback coming. {t} didn't{s}."],
    ("live_up", "won"): ["{t} held on and cashed{s}.", "Got {t} at plus money with a lead and they closed{s}.",
                         "{t} kept the foot on the gas{s}."],
    ("live_up", "lost"): ["{t} had it and blew it{s}.", "{t} let {o} back in{s}. Brutal.", "{t} choked the lead{s}."],
    ("big", "won"): ["{t} ran {o} off the field{s}.", "{t} beat {o} like they stole something{s}.", "Blowout. {t} cooked {o}{s}.",
                     "{o} got cheeks clapped{s}. Not even close.", "{t} put a whooping on {o}{s}."],
    ("big", "lost"): ["Damn, we were confident in {t}. {o} ended up smacking{s}.", "{o} ran us off the field{s}. Ugly.",
                      "{t} got cheeks clapped{s}. No excuses.", "Not even close — {o} smacked {t}{s}.",
                      "{t} got cooked{s}. Wasn't their day."],
    ("close", "won"): ["Sweated it out but {t} got there{s}.", "Nail-biter, but {t} held on{s}.", "Too close for comfort — still a W{s}.",
                       "{t} made us sweat{s}, but we cashed."],
    ("close", "lost"): ["{t} lost by a hair{s}. So close.", "One play away{s}. Brutal.", "{t} came up just short{s}. That one stings.",
                        "Coin flip went the wrong way{s}. {t} almost had it."],
    ("conf", "lost"): ["The algorithm was confident in {t} and they folded{s}.", "We felt good about {t}. {o} didn't care{s}.",
                       "Damn, we were sure about {t}{s}. Not this time."],
    ("parlay", "won"): ["Every leg hit — the whole ticket cashed.", "Clean sweep, every leg came through.",
                        "All legs green. Ticket cashed."],
    ("parlay", "lost"): ["{x} sunk the ticket.", "One leg away — {x} did us dirty.", "{x} was the leg that got us.",
                         "Had it till {x} folded."],
}
REVIEW_END = {
    "won": ["Trust the algorithm.", "On to the next.", "Keep eating.", "Told y'all.", "Easy money.", "We eating.",
            "Say less.", "Bag secured.", "Light work.", "Another one.", ""],
    "lost": ["On to the next.", "We bounce back.", "Every L stays up — we don't hide nothing.", "Next one's ours.",
             "Run it back.", "Is what it is.", "Our bad.", "SMH.", "Can't win em all.", ""],
}


def review(kind, result, seed, used, **kw):
    """One review for a graded pick, never repeating a wording already used on the page (used: a set, shared)."""
    mids = REVIEW_MID.get((kind, result)) or []
    ends = REVIEW_END.get(result) or [""]
    if not mids:
        return ""
    rnd = random.Random(str(seed))
    combos = [(a, b) for a in range(len(mids)) for b in range(len(ends))]
    rnd.shuffle(combos)
    best = None
    for a, b in combos:                  # a middle AND a closer nobody else used, else just a fresh middle, else anything
        if ends[b] and ends[b].rstrip(".!").lower() in mids[a].lower():
            continue                     # (never "SMH. SMH.")
        score = ((kind, result, a) not in used) * 2 + ((result, "end", b) not in used or not ends[b])
        if best is None or score > best[0]:
            best = (score, a, b)
        if score == 3:
            break
    _, a, b = best
    used.add((kind, result, a))
    used.add((result, "end", b))
    kw.setdefault("s", "")
    line = mids[a].format(**kw)
    line = line[:1].upper() + line[1:]
    line = line.replace(". the ", ". The ").replace("— the ", "— the ")
    return f"{line} {ends[b]}".strip()


if __name__ == "__main__":
    print(supply())
    for x in good("Skenes", "the Cubs", "demo", n=6):
        print(" ", x)
