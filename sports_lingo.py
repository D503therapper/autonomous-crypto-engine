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


if __name__ == "__main__":
    print(supply())
    for x in good("Skenes", "the Cubs", "demo", n=6):
        print(" ", x)
