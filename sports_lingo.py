"""THE LINGO MIXER: an endless supply of our lines - the "player is nice" mixer, the reviews on every graded pick in
Past Results, the live bet lines, the tennis recaps and the board notes.

The owner: "a whole ass vocabulary - thousands of phrases and words. If it was me I'd use the same words here and
there but the phrases be changing around." So no line here is a fixed sentence: each one is a pile of skeletons with
slots ({book} {algo} {won_v} ... from sports_vocab.SLOTS), inline picks ([a|b|c]) and our own pools (%wk% ...), rolled
per game / per pick / per play with a stable seed. `pick()` keeps whichever roll repeats no 4-word run already on the
page (names -> _, numbers -> #), so a whole section reads fresh top to bottom.

Two owner rules baked in:
  - variety never makes a line longer: every key has a size cap (characters, sentences) = the longest version of that
    line before the mixer, and every roll over it is thrown out (names / numbers count as one character).
  - never "real talk", never "chalk"; no hype on a lean (no "trust the algorithm", no "let's eat" on a lean)."""
import random
import re

from sports_vocab import SLOTS, variants
from sports_vocab import supply as _supply

BANNED = re.compile(r"real talk|chalk", re.I)
LEAN_BAN = re.compile(r"trust the algorithm|lock it in|free money|easy money|hammer|smash|we eating|let'?s eat|bag|"
                      r"money energy|can'?t lose|guaranteed|told y'all|say less|stamp it|book it|light work|"
                      r"levels to this|cook\b|tail it", re.I)

# our own pools: "%name%" in a template -> [a|b|c] (never put one inside [..] - no nesting)
PAL = {
    "wk": ["Told y'all.", "Nice nice.", "Light work.", "Let's eat.", "Another one.", "Paid.", "Bag secured.",
           "Say less.", "Levels to this.", "Easy money.", "We eating.", "Stamp it.", "Keep stacking.", "Money.",
           "Run it back.", "That's how it's done.", "Get in.", "", "", ""],
    "lk": ["Our bad.", "That's on us.", "Is what it is.", "It happens.", "Next one.", "SMH.", "No excuses.",
           "We own it.", "Every L stays up.", "We bounce back.", "Short memory.", "On to the next.", "Tip the cap.",
           "Can't win em all.", "Part of it.", "Chin up.", "Bad read.", "", ""],
    "go": ["Get in", "Tail it", "Hammer it", "Let's eat", "We buying", "Say less", "Take it", "Buy the dip"],
    "go_": ["get in", "tail it", "hammer it", "let's eat", "we buying", "say less", "take it", "buy the dip"],
    "dn": ["down", "down", "behind by", "trailing by", "in a hole by"],
    "Dn": ["Down", "Down", "Behind by", "Trailing by", "In a hole by"],
    "pm": ["plus money", "plus money", "plus odds", "a plus price", "a plus number", "dog money"],
    "Pm": ["Plus money", "Plus money", "Plus odds", "A plus price", "A plus number", "Dog money"],
    "ball": ["the ball", "the rock", "the ball back", "possession", "the rock back"],
    "price": ["the price", "the number", "the line", "the live line", "the live number"],
    "Price": ["The price", "The number", "The line", "The live line", "The live number"],
    "ours": ["our numbers", "our math", "our sheet", "our model", "the model"],
    "over": ["far from over", "nowhere near over", "not close to over", "still live", "a long way from done"],
    "sale": ["on sale", "at a discount", "cheaper", "on clearance", "marked down"],
    "serve": ["first serve", "first ball", "first point", "opening serve"],
    "bp": ["the better player", "the better player out there", "the stronger player",
           "the better talent"],
    "bt": ["the better team", "the better squad", "the stronger side", "the better roster", "the better club"],
}
_PAL = re.compile(r"%(\w+)%")


def T(*lines):
    """Templates, with our pools expanded."""
    return [_PAL.sub(lambda m: "[" + "|".join(PAL[m.group(1)]) + "]", x) for x in lines]


# ---- the machinery -------------------------------------------------------------------------------------------------
_SENT = re.compile(r"[.!?](?=\s|$)")


def _size(s):
    """(characters, sentences) - a filled-in name or number counts as one character."""
    return len(s), len(_SENT.findall(s))


def _put(s, tok, kw):
    """Swap the placeholders for the real values - capitalized where one starts a sentence."""
    for k, c in tok.items():
        v, cur = str(kw[k]), s
        def rep(m, v=v, cur=cur):
            pre = cur[:m.start()].rstrip()
            start = not pre or pre[-1] in ".!?" or not re.search(r"[A-Za-z0-9]", pre)
            return v[:1].upper() + v[1:] if start else v
        s = re.sub(re.escape(c), rep, cur)
    return s


def roll(templates, seed, cap, n=40, lower=False, ban=None, **kw):
    """Up to n different lines from these templates (seeded, so the same seed always rolls the same list), none of
    them over the cap (chars, sentences). lower=True: the line continues a sentence (starts lowercase)."""
    tok = {k: chr(0xE000 + i) for i, k in enumerate(kw)}
    out = []
    for r in variants(templates, seed, n * 3, **tok):
        if lower and r[:1].isalpha() and not r[1:2].isupper():
            r = r[:1].lower() + r[1:]
        c, s = _size(r)
        if c > cap[0] or s > cap[1]:
            continue
        line = _put(r, tok, kw)
        line = re.sub(r"(?<!\.)\.\.(?!\.)", ".", line)            # "Bain Jr.." -> "Bain Jr."
        if BANNED.search(line) or (ban is not None and ban.search(line)):
            continue
        out.append(line)
        if len(out) >= n:
            break
    return out


def _grams(text, names):
    import sports_breakdown as sb                                  # (it imports us: import it late)
    return {g for g in sb.grams(text, names) if any(w not in ("_", "#") for w in g[2:].split())}


def fresh(options, used, names=(), _clash=None):
    """The first option that repeats no 4-word run already in `used` (else the one that repeats the fewest); its runs
    go into `used`. Runs made only of names and numbers don't count (every score line has those)."""
    best = None
    for o in options:
        g = _grams(o, names)
        clash = len(g & used)
        if not clash:
            best = (0, o, g)
            break
        if best is None or clash < best[0]:
            best = (clash, o, g)
    if best is None or (_clash is not None and best[0]):
        return ""                                            # (_clash: say nothing - the caller rolls more)
    used |= best[2]
    return best[1]


def say(key, seed, used=None, n=40, lean=False, **kw):
    """One line for LINES[key], rolled with this seed, fresh against `used` (a set of 4-word runs, shared)."""
    cap, lower, templates = LINES[key]
    opts = roll(templates, seed, cap, n, lower, LEAN_BAN if lean else None, **kw)
    names = [str(v) for v in kw.values() if str(v).strip() and not re.fullmatch(r"[+-]?[\d.,%]+", str(v))]
    return fresh(opts, set() if used is None else used, names)


def _num(s):
    return bool(re.fullmatch(r"[+-]?[\d.,%]+", str(s)))


# ---- a player who's really good (he's our side) ---------------------------------------------------------------------
GOOD_OPEN = T(
    "{p} is [nice|different|a problem|{HIM}|built different|the real deal|a menace|the truth].",
    "{p} [nice nice|been cooking|locked in|been dialed in|came to work|stay ready|on a heater|carrying|ain't regular].",
    "{p} [on another level|on one lately|in a groove|stay cooking|been that|a dog].",
    "Y'all know {p} is [nice|different|a problem|built different].",
    "Don't [sleep on|overthink|fade] {p}.",
    "{p} got [that dog in {him}|the juice right now|range for days|a motor on {him}|that clutch gene].",
    "Give me {p} [all day|every time|no hesitation|with my whole chest|twice].",
    "{p}? [Nice nice|Different|Levels to this|Built different|Problem].",
    "Levels to this, and {p} [up top|on the top floor|at the top].",
    "We know what {p} [brings|is about|can do|been doing].",
    "{p} been [showing out|putting in work|handling business|on a tear] lately.",
    "Everybody [know|saw] what {p} [been doing|is about].",
    "[Say what you want|Say less|Facts], {p} is [nice|different|{HIM}].",
    "{p} [the one|a cheat code|a walking bucket|pure problems] right now.",
    "Real ones know {p} [nice|different|a problem].",
)
GOOD_END = T(
    "Watch {him} [work|do {his} thing|go].",
    "{o} [got no answer for|can't hang with|ain't seen nothing like|got nobody for|can't stop] {him}.",
    "{He} [about to|finna|gon'] [go off|eat|feast|take over|put on a show|go to work].",
    "{He} [about to|finna|gon'] [handle {o} light|make {o} look silly|make it look easy].",
    "{o} [in for a long day|in trouble|ain't ready|better pray|can't keep up|gon' need a miracle|picked the wrong day].",
    "[Light work|Easy work|Clock in, clock out|Different breed|Mark it down|Levels to this|Say less|Book it|Just watch].",
    "{He} [been|stay] [on one|money|ready|dialed in|locked in|feeling it].",
    "{He} [built for|made for|lives for] [this matchup|spots like this|days like this|this stage].",
    "{He} [ain't scared of nobody|got something to prove|don't miss in spots like this|been waiting on this one].",
    "That's [a problem|bad news|trouble|a long day] for {o}.",
    "It's {his} world, {o} just living in it.",
    "{o} [already know what time it is|gon' feel {him} all game|gon' remember this one].",
    "{He} run this. {o} [know it|gon' learn|ain't ready].",
    "{He} got {o} number.",
    "[Too much|Too nice|Too different] for {o}.",
    "{He} gon' remind everybody [today|tonight|real quick].",
    "No answer for {him} [today|over there|on that side].",
)
BAD_OPEN = T(
    "{o} [been|look] [complete ass|lost|a mess lately|sliding|struggling bad|ice cold|stuck in the mud].",
    "{o} ain't it right now.",
    "{o} can't get out their own way.",
    "Nothing going right for {o}.",
    "{o} [been dropping games|keep finding ways to lose|been searching for answers|been limping].",
    "{o} [look|been] [cooked|shook|flat|off] lately.",
    "Wheels fell off for {o}.",
    "{o} [on a skid|in a funk|in a rut] right now.",
)
BAD_END = T(
    "We [taking advantage|eating off it|riding against 'em|fading 'em].",
    "Somebody gotta pay for that.",
    "[Tonight|Today] ain't changing that.",
    "They about to get exposed again.",
    "No reason to trust 'em now.",
    "That's our [edge|angle|spot].",
    "[Keep fading|Keep betting against|Stay against] 'em.",
    "They due for another L.",
    "[Blood in the water|Kick 'em while they down|We know how this goes].",
    "Make 'em pay.",
)


def _pairs(opens, ends):
    return [f"{a} {b}" for a in opens for b in ends]


GOOD = _pairs(GOOD_OPEN, GOOD_END)
BAD = _pairs(BAD_OPEN, BAD_END)


def good(player, opp, seed, he="he", n=24):
    """n fresh 'player is nice' lines for this game (pass them to Voice.say as the options)."""
    him, He, his = ("her" if he == "she" else "him"), he.capitalize(), ("her" if he == "she" else "his")
    kw = dict(p=player, o=opp, he=he, him=him, his=his, He=He, HIM=him.upper())
    return roll(GOOD, seed, (64, 3), n, **kw)


def bad(opp, seed, n=12):
    """n fresh 'the other side has been bad' lines."""
    return roll(BAD, seed, (63, 2), n, o=opp)


# ---- REVIEWS: a line on every graded pick in Past Results ------------------------------------------------------------
# {t} our side, {o} the other side, {x} the number, {pr}/{pro}/{pos} = they/them/their (he/him/his, she/her/her)
REVIEWS = {
    # how it went (the owner, 9/28: "if we're down big and come back, say so; if we got lucky, say so - a win is a win")
    ("comeback", "won"): (96, 3, T(
        "Down {d} and {t} [came all the way back|stormed back|refused to die]. We cashed, baby. %wk%",
        "{t} [were|was] down {d}. [Didn't matter.|Still got there.|Comeback kids.] %wk%",
        "[Major|Big|Crazy] comeback: {t} [erased|wiped out|climbed out of] a {d}-point hole. [Cashed.|We ate.] %wk%",
        "We were cooked, down {d}. Then {t} [woke up|flipped the switch|turned it on]. %wk%",
        "{d} down and {t} [still cashed|still got it done]. Never count 'em out. %wk%",
        "Heart attack [ticket|pick]: {t} [came back from|overcame] {d} down. Paid. %wk%",
        "{o} had us down {d}. {t} [said not tonight|ran it back|finished the job]. %wk%",
        "From down {d} to cashed. {t} [with the comeback|pulled it off]. %wk%",
        "Down {d}? [No sweat.|Light work.|We don't panic.] {t} came back and cashed. %wk%",
    )),
    ("collapse", "lost"): (96, 3, T(
        "{t} [were|was] up {d} and [blew it|let it slip|gave it away]. That one hurts. %lk%",
        "Up {d} and {t} [still found a way to lose|choked|folded]. %lk%",
        "{t} had a {d}-point lead and [shit the bed|fumbled the bag|let {o} back in]. %lk%",
        "We were up {d}. {o} [came all the way back|stole it]. Brutal. %lk%",
        "Blown lead: {t} up {d}, then [nothing|lights out]. %lk%",
        "{t} [coughed up|blew] a {d}-point lead. [Sick.|Pain.|Rough one.] %lk%",
        "Had it in the bag, up {d}. {t} [gave it back|let it go]. %lk%",
    )),
    ("lucky", "won"): (96, 3, T(
        "We got lucky as hell on this one, but we cashed, baby. A win is a win. %wk%",
        "[Sweated it|Heart in our throat] the whole way. {t} [snuck in|squeaked it] by a hair. Cashed. %wk%",
        "Covered by the skin of our teeth. {t} [got there|did just enough]. We'll take it. %wk%",
        "Lucky? Maybe. Cashed? Absolutely. {t} [by a hair|just barely]. %wk%",
        "That was way too close. {t} [squeaked by|snuck it in]. A win is a win. %wk%",
        "We got the bounce on this one. {t} [barely|just] covered. Paid is paid. %wk%",
        "{t} made us sweat for it, but it cashed. %wk%",
        "Thank God. {t} got there by [a hair|a whisker|inches]. We cashed. %wk%",
    )),
    # 🤡 we faded the public (the owner, 9/28: "we knew it - the public's a bunch of clowns")
    ("fade", "won"): (86, 3, T(
        "Faded the public on {t} and cashed. [The public stays|The squares stay|The sheep stay] clowns. %wk%",
        "We knew it. [Everybody|The public|The whole world] was on {o}, and {t} cashed.",
        "The public loved {o}. We took {t}. [Clowns.|Sheep gonna sheep.|We knew it.]",
        "The squares ran to {o}. {t} [made 'em pay|cashed for us]. %wk%",
        "[Told y'all|We knew it]: fading the public on {t} paid. %wk%",
        "Everybody and their mama on {o}. {t} [said nah|got it done]. %wk%",
        "The herd went {o}, we went {t}. [Herd lost.|Clowns.|Pay up.]",
        "{t} over the public's side. [We knew it.|Called it.|Easy fade.] %wk%",
        "Fade the public, get paid: {t}. %wk%",
        "The clowns loved {o}. {t} [humbled 'em|cooked 'em|sent 'em home]. %wk%",
        "Public [money|tickets] on {o}, our money on {t}. [Guess who ate.|We ate.] %wk%",
        "[Casuals|Squares] on {o} again. {t} [cashed|hit]. Stay fading. %wk%",
    )),
    ("fade", "lost"): (86, 3, T(
        "Faded the public on {t}, and the public got this one. %lk%",
        "The squares hit one — {o} came through. %lk%",
        "Even the public's right sometimes. {t} [didn't get there|fell short]. %lk%",
        "We went against the crowd with {t}. {o} [got it done|won it]. %lk%",
        "The herd won this round on {o}. %lk%",
        "The fade didn't land. {t} [came up short|slipped]. %lk%",
        "{o} bailed out the public this time. %lk%",
        "Public got lucky on {o}. {t} [came up short|didn't show]. %lk%",
        "Wrong night to fade the crowd. {o} [had it|got the W]. %lk%",
        "The clowns cashed one on {o}. Still fading. %lk%",
        "[Faded|Went against] the [crowd|herd|squares] and {o} [made us pay|got there]. %lk%",
        "The public [ate|cashed] this time on {o}. [We still fade 'em.|Rare one.|Happens.] %lk%",
        "{t} [left us hanging|let us down] against the public side. %lk%",
    )),
    ("fav", "won"): (59, 2, T(
        "{t} [handled business|took care of business|did what favorites do|took care of it|got the job done] "
        "[vs|against] {o}. %wk%",
        "Laid the price, {t} [paid it off|made it worth it|delivered|took care of it]. %wk%",
        "{o} [never had a chance|had no answer|couldn't hang|got handled]. %wk%",
        "Favorite [did its job|held up|came through|took care of it]: {t} over {o}.",
        "{t} [went to work on|took care of|handled|got past|ran through] {o}. %wk%",
        "No drama. {t} [cashed|got it done|handled {o}].",
        "Paid the juice on {t} and it [cashed|hit|came home]. %wk%",
        "Took the favorite, got the W. {t} [over|past] {o}.",
        "{t} [smacked that|made it look easy|made light work of {o}]. %wk%",
        "Minus money, [no stress|no sweat|clean ticket]: {t} [got it done|won it].",
        "{t} [got the W|took the W|won it] like the favorite should. %wk%",
        "Business handled: {t} over {o}. %wk%",
    )),
    ("fav", "lost"): (86, 3, T(
        "{t} [shit the bed|laid an egg|fumbled it|folded|never showed up] as the favorite. %lk%",
        "We laid the price on {t} and {o} [had other plans|flipped the script|didn't care|ran with it]. %lk%",
        "Favorite [folded|fumbled|went down] — {o} [took it|got the W|stole one]. %lk%",
        "{t} had one job [vs|against] {o} and [fumbled it|blew it|didn't do it]. %lk%",
        "{o} [clipped|stunned|got past|took down] {t}. [Didn't see that coming.|Wrong side.|Bad read.] %lk%",
        "Paid the juice on {t} for nothing. {o} [won it|got the W|had it]. %lk%",
        "We had the favorite and still [took the L|went red|got burnt]. %lk%",
        "[Ugly|Rough|Not our day]. {t} [dropped it|lost it|let it slip] to {o}. %lk%",
        "{t} [looked flat|never got going|played scared] and {o} [made {pro} pay|took advantage|cashed in]. %lk%",
        "No excuse on this one: {t} [lost|went down|got beat] as the favorite. %lk%",
        "{t} [got caught slipping|slipped up|tripped] against {o}. %lk%",
        "Laid the juice, got nothing. {o} over {t}. %lk%",
    )),
    ("dog", "won"): (57, 2, T(
        "Dog barked — {t} [took down|got past|beat|stunned] {o}. %wk%",
        "{t} came in as the dog and [ate|cooked|got fed|feasted]. %wk%",
        "Plus money and {t} [came through|got there|delivered|got it done]. %wk%",
        "Nobody [believed in|was on|rode with] {t} but us. [Paid.|Cashed.|Nice nice.]",
        "The value was real: {t} [got it done|came through|cashed]. %wk%",
        "{t} made {book} look silly. %wk%",
        "Underdog [energy|money|season]: {t} over {o}. %wk%",
        "{o} got [upset|got|clipped] by {t}. %wk%",
        "Took the plus money, {t} [delivered|paid us|did the rest]. %wk%",
        "{Book} slept on {t}. We didn't. %wk%",
        "{t} [shocked|stunned|upset] {o}. [Plus money|The dog|The value] [hit|cashed].",
        "We got paid [on the dog|at plus money]: {t} over {o}.",
    )),
    ("dog", "lost"): (87, 2, T(
        "{t} had the value, just [not the juice|not the legs|not enough]. %lk%",
        "Dog didn't bark this time — {o} [held on|got it done|took it]. %lk%",
        "The price was right, the result [wasn't|didn't follow|didn't come]. %lk%",
        "{t} gave us [nothing|nada|zero] [against {o}|today|this time]. %lk%",
        "{o} [held off|handled|took care of|got past] our dog. %lk%",
        "Plus money [for a reason|went the other way] this time. %lk%",
        "Right price, wrong result. {t} [came up short|fell short|couldn't finish] [vs|against] {o}.",
        "We took the shot on {t} and it [missed|didn't land|went red]. %lk%",
        "{t} [hung around|kept it interesting] but {o} [closed it|won it|got there]. %lk%",
        "Value bet, no payoff: {t} [lost|went down] to {o}. %lk%",
        "Dog stayed on the porch. {o} over {t}. %lk%",
        "Swung at the plus money on {t}, [whiffed|missed]. %lk%",
    )),
    ("spread", "won"): (62, 3, T(
        "{t} covered. %wk%",
        "[Cover|Covered|Cashed]: {t} [took care of it|got it done|did enough]. %wk%",
        "{t} [handled the spread|beat the spread|covered with room]. %wk%",
        "Spread [ticket|pick] on {t}? [Green|Paid|Money]. %wk%",
        "{t} [kept it within|stayed within] reach and we cashed. %wk%",
        "{o} couldn't [shake|pull away from] {t}. Covered. %wk%",
        "The points [did their job|came through|paid off] with {t}. %wk%",
        "{t} made the spread look easy. %wk%",
        "Took {t} with the points. [Right call.|Paid.|Cashed.]",
        "{t} [got us the cover|delivered the cover]. %wk%",
        "{t} covered the {x}. %wk%",
        "{t} [at|with] the {x}? Covered. %wk%",
        "Took the points with {t} and [it covered|we cashed]. %wk%",
        "{t} stayed [inside|on the right side of] the number. %wk%",
        "The {x} was the right side. %wk%",
        "{t} [beat|handled] the number. {x} [cashed|hit|paid].",
        "Spread [bet|pick] {won_v}: {t} {x}. %wk%",
        "Number was [right|good|solid]: {t} {x} [cashed|got there].",
        "{t} did enough to cover the {x}. %wk%",
        "{t} got us the cover at {x}. %wk%",
        "Cover secured, {t} {x}. %wk%",
        "{x} with {t}? [Money|Green|Covered]. %wk%",
    )),
    ("outright", "lost"): (81, 2, T(    # 9/29: "The Oilers couldn't cover" - they lost the whole game. Say that.
        "{t} didn't just miss the cover — they lost the [whole game|game outright] to {o}. %lk%",
        "Forget the spread. {o} beat {t} [straight up|outright|flat out]. %lk%",
        "{t} got cooked. Lost the [whole game|game], not just the spread. %lk%",
        "{t} shit the bed — [lost to {o} outright|dropped the whole game to {o}]. %lk%",
        "Not even close: {t} lost the game [outright|straight up]. %lk%",
        "{o} won it [straight up|outright]. {t} never had a shot at the cover. %lk%",
        "{t} lost the [game|whole thing], so the spread was dead. %lk%",
        "Straight-up L. {o} [beat|handled|took care of] {t}. %lk%",
        "{t} [never led when it counted|got outplayed] and lost it outright. %lk%",
        "Covering was the least of it — {t} lost to {o}. %lk%",
    )),
    ("spread", "lost"): (81, 2, T(
        "{t} couldn't cover. %lk%",
        "Spread [ticket|pick] on {t} [went red|missed|didn't land]. %lk%",
        "{o} [pulled away|ran away with it] from {t}. %lk%",
        "{t} [came up short on the spread|fell short of the cover]. %lk%",
        "The points weren't enough with {t}. %lk%",
        "{t} [let it get away|got blown past the number]. %lk%",
        "No cover from {t}. %lk%",
        "{t} [didn't hold the spread|lost the spread battle]. %lk%",
        "{t} couldn't cover the {x}. %lk%",
        "{t} [ended up|landed] on the wrong side of the {x}. %lk%",
        "The {x} wasn't enough [for {t}|this time]. %lk%",
        "{t} didn't [get there against|beat|cover] the number. %lk%",
        "No cover. {t} {x} [missed|went red|came up short]. %lk%",
        "The number [beat us|got us|won]. {t} {x} [didn't cover|missed].",
        "{t} [needed|had] the {x} and still [fell short|came up short|missed]. %lk%",
        "Wrong side of the {x} with {t}. %lk%",
        "{o} [beat|covered] the number against {t}. %lk%",
        "Spread [pick|bet] {lost_v}: {t} {x}. %lk%",
        "{x} on {t} [didn't hold|wasn't it|fell short]. %lk%",
    )),
    ("live_back", "won"): (72, 3, T(
        "We [trusted|rode|backed] the comeback and {t} [delivered|came through|did it]. %wk%",
        "Down when we got in, {t} [came back|climbed out the hole|rallied] anyway. %wk%",
        "{Algo} called the comeback. {t} [came through|got there|delivered|got it done]. %wk%",
        "Never count a live dog out — {t} came back. %wk%",
        "{t} climbed out the hole. %wk%",
        "Comeback [complete|secured]: {t} [over|past] {o}. %wk%",
        "{t} [rallied|flipped it|turned it around] after we got in. %wk%",
        "Bought the dip on {t} and it [paid|cashed|hit]. %wk%",
        "Trailing when it went up, {t} [still won it|found a way|got it done]. %wk%",
        "{o} [let {pro} back in|couldn't close|blew the lead]. %wk%",
        "Live dog [ate|barked|cashed]: {t} came back on {o}. %wk%",
        "From behind and still {won_v}: {t}. %wk%",
    )),
    ("live_back", "lost"): (114, 3, T(
        "{Algo} [liked|backed|was on] the comeback but [missed|was off] this time. %lk%",
        "We thought {t} had a comeback in {pro}. Didn't happen. %lk%",
        "{t} had the window and never climbed through it. %lk%",
        "Comeback never came — {t} ran outta time. %lk%",
        "{t} had a shot and fumbled the bag. %lk%",
        "We saw the comeback coming. {t} didn't. %lk%",
        "Bought the dip on {t} and it kept dipping. %lk%",
        "{o} [held on|closed the door|kept {t} at bay]. [Comeback|Our live bet] {lost_v}. %lk%",
        "{t} [never got the stops|never made the run|stayed stuck] we needed. %lk%",
        "Live comeback [didn't land|went red|missed]: {o} [held on|closed it out]. %lk%",
        "Rode {t} from behind, [no dice|no luck|no comeback]. %lk%",
        "Hole was too deep for {t} [today|this time]. %lk%",
    )),
    ("live_up", "won"): (70, 2, T(
        "{t} held on and cashed. %wk%",
        "Got {t} at plus money with a lead and [it held|we cashed]. %wk%",
        "{t} kept the foot on the gas. %wk%",
        "Up when we got in, {t} [closed it|finished it|shut the door]. %wk%",
        "{t} [protected|held] the lead. %wk%",
        "Lead held. {t} [over|past] {o}.",
        "{o} [never caught up|couldn't close the gap]. %wk%",
        "Front-runner at plus money — {t} [cashed|delivered]. %wk%",
        "{t} [shut the door on|held off] {o}. %wk%",
        "Plus money on the team ahead, and [it held|it cashed]. %wk%",
        "Had the lead at plus money, kept it: {t}. %wk%",
    )),
    ("live_up", "lost"): (67, 3, T(
        "{t} had it and blew it. %lk%",
        "{t} let {o} back in. [Brutal.|Ugly.|Pain.]",
        "{t} choked the lead. %lk%",
        "Lead [gone|blown|slipped away]. {o} [came back|stormed back|rallied]. %lk%",
        "{o} [came back on|rallied past|caught] {t}. %lk%",
        "Had the lead, lost the bet. %lk%",
        "{t} [couldn't close|let it slip|coughed it up]. %lk%",
        "Got in with the lead, still lost. %lk%",
        "{t} took the foot off the gas. %lk%",
        "The lead didn't hold. %lk%",
        "Blown lead on {t}. [Pain.|Brutal.|Ugly.] %lk%",
    )),
    ("big", "won"): (59, 3, T(
        "{t} ran {o} out the building. %wk%",
        "{t} beat {o} like they stole something.",
        "Blowout. {t} cooked {o}. %wk%",
        "{o} got cheeks clapped. [Not even close.|Ugly.] %wk%",
        "{t} put a whooping on {o}. %wk%",
        "Not close. {t} [smoked|dusted|buried|cooked] {o}.",
        "{t} [smoked|buried|embarrassed] {o}. %wk%",
        "Laugher. {t} over {o}. %wk%",
        "{o} [never showed up|got run out the gym]. %wk%",
        "{t} [won by a mile|won going away]. %wk%",
        "Blowout W: {t} [ran through|smoked] {o}.",
        "{t} [bullied|dog-walked] {o}. %wk%",
    )),
    ("big", "lost"): (93, 3, T(
        "Damn, we were confident in {t}. {o} [ended up smacking|ran away with it]. %lk%",
        "{o} ran us out the building. [Ugly.|No excuses.] %lk%",
        "{t} got cheeks clapped. No excuses.",
        "Not even close — {o} smacked {t}. %lk%",
        "{t} got cooked. [Wasn't {pos} day.|Our bad.]",
        "Blowout, wrong way. {o} [buried|smoked|rolled] {t}. %lk%",
        "{t} [got smoked|got embarrassed|got ran over]. [That's on us.|No hiding it.]",
        "We missed bad on this one. {o} [dominated|ran it up]. %lk%",
        "[Ugly|Brutal|Rough] one. {o} [handled|rolled|dusted] {t}. %lk%",
        "{t} [never showed up|got blown out]. %lk%",
        "{o} [put a whooping on|ran through] {t}. [Bad read|Wrong side], our bad.",
        "Wrong side of a blowout. {o} over {t}. %lk%",
    )),
    ("close", "won"): (56, 2, T(
        "[Sweated it out|Sweated it|Had us sweating] but {t} got there. %wk%",
        "[Nail-biter|Heart-stopper|Squeaker], but {t} [held on|hung on|survived]. %wk%",
        "Too close for comfort — still a W. %wk%",
        "{t} made us sweat, but we [cashed|got paid|got there].",
        "[Down to the wire|Coin-flip finish], {t} [held on|got there].",
        "{t} [squeaked by|snuck past|edged] {o}. %wk%",
        "Close one, but {t} [came through|got there|delivered|got it done]. %wk%",
        "Heart-attack finish, {t} [came through|got there|delivered|got it done].",
        "{t} won ugly, [still a W|still counts|still cashed]. %wk%",
        "Tight. But a W is a W. %wk%",
        "{o} made it close. {t} [still cashed|held on].",
        "[Photo finish|Close call|Sweaty one], {t} [by a hair|just enough|by a nose].",
    )),
    ("close", "lost"): (89, 3, T(
        "{t} lost by a hair. [So close.|That one stings.] %lk%",
        "One play away. [Brutal.|Pain.] %lk%",
        "{t} came up just short. That one stings.",
        "Coin flip went the wrong way. {t} almost had it.",
        "[So close|Inches]. {o} [edged|squeaked by|snuck past] {t}. %lk%",
        "{t} [lost a nail-biter|lost it late|dropped a close one] to {o}. %lk%",
        "Down to the wire and {o} [got there|made the last play]. %lk%",
        "Heartbreaker. {t} [fell just short|came up a play short]. %lk%",
        "{t} had it right there. {o} [closed it|finished]. %lk%",
        "Lost by a whisker. %lk%",
        "Close ain't cashed. {t} [fell short|came up short] [vs|against] {o}.",
    )),
    ("conf", "lost"): (92, 3, T(
        "{Algo} was confident in {t}. [Didn't matter.|Wrong.] %lk%",
        "We felt good about {t}. {o} didn't care. %lk%",
        "Damn, we were sure about {t}. Not this time.",
        "We [liked|loved] {t} [a lot|big] here and it [missed|went red]. %lk%",
        "High confidence, wrong result. {t} [lost|went down] to {o}. %lk%",
        "This one hurts: we were on {t} [heavy|strong] and {o} [won|took it]. %lk%",
        "Our [strong|big] read on {t} [missed|was wrong]. %lk%",
        "{Algo} [had|gave] {t} [a big edge|a real chance|the nod] and {o} [spoiled it|won anyway]. %lk%",
        "We [believed|trusted] {t} [here|all the way]. {o} [had other plans|flipped it]. %lk%",
        "Confident pick, [no cash|red ink|no payday]. {o} over {t}. %lk%",
        "Big confidence, big miss on {t}. %lk%",
    )),
    ("parlay", "won"): (61, 3, T(
        "Every leg [hit|cashed|came through] — ticket {won_v}. %wk%",
        "All legs green. Ticket cashed. %wk%",
        "Clean sweep, every leg came through. %wk%",
        "[Went|Swept] [perfect|clean] on the legs. Ticket [paid|cashed].",
        "Parlay [cashed|hit|paid]. [Every leg|All legs] [green|home]. %wk%",
        "Nobody fumbled. Every leg {won_v}. %wk%",
        "[Full|Whole] ticket [hit|cashed]. %wk%",
        "Every leg did its job. Ticket paid. %wk%",
        "Ticket's [a winner|green|good], no leg missed. %wk%",
        "No leg left behind. %wk%",
        "Parlay [money|season]. All legs hit.",
    )),
    ("parlay", "lost"): (72, 2, T(
        "{x} sunk the ticket. %lk%",
        "{x} did us dirty. %lk%",
        "Had it till {x} folded. %lk%",
        "{x} [killed|busted|broke] the ticket. %lk%",
        "Ticket [busted|died|went red] on {x}. %lk%",
        "{x} [let us down|cost us the ticket|broke the parlay]. %lk%",
        "Parlay [missed|went red|busted]: {x} [didn't come through|fell short|missed]. %lk%",
        "Blame {x}. [Ticket's dead.|Parlay's done.]",
        "Couldn't get {x} home. %lk%",
        "The ticket [died|went down] with {x}. %lk%",
        "Parlay killer: {x}. %lk%",
    )),
    ("push", "x"): (70, 2, T(
        "{t} landed right on the {x}. [Push, money back.|Push.|Wash.]",
        "Dead on the number ({x}). [Push|Wash], stake back.",
        "Push on {t} {x} — [money back|nobody wins|stake back].",
        "Right on the {x}. [Push|Wash], money back.",
        "No harm: {t} {x} pushed.",
        "[Push|Wash]. {t} {x} [landed on the number|hit it on the nose].",
        "Money back — {t} {x} pushed.",
        "The {x} landed exactly. [Push|Wash].",
        "{t} {x} [ended|finished] dead even. Push.",
        "Exactly the number. [Push|Wash] on {t} {x}.",
    )),
    ("push", ""): (70, 2, T(
        "Push, money back.",
        "[Push|Wash] — stake back, no harm.",
        "Nobody won that one. Money back.",
        "Dead even. [Push|Wash].",
        "[Push|Wash] on {t}. Stake back.",
        "No harm, no foul. [Push|Wash].",
        "Money back on {t}. [Push|Wash].",
        "Even steven on {t}. Push.",
        "[Push|Wash]. We get it back.",
        "{t} pushed. [Stake back|Money back].",
    )),
    ("total", "won"): (62, 2, T(
        "{t} [came through|got there|delivered|got it done]. %wk%",
        "{t}? [Cashed|Hit|Money]. %wk%",
        "Called the total: {t}. %wk%",
        "Scoring read [hit|was right|cashed]: {t}. %wk%",
        "{Algo} [nailed|had] the total. {t} [came through|got there|delivered|got it done].",
        "{t} got home. %wk%",
        "Total [pick|call] {won_v} — {t}. %wk%",
        "[Good|Right] read on the total. {t} [came through|got there|delivered|got it done].",
        "{t}, [cashed|paid|done]. %wk%",
        "The number was {t}, and it {won_v}.",
    )),
    ("total", "lost"): (81, 2, T(
        "{t} [fell short|came up short|didn't get there]. %lk%",
        "Missed the total. {t} [didn't get there|went red]. %lk%",
        "{Algo} [misread|missed on] the total. {t} [fell short|came up short|didn't get there].",
        "Wrong side of the total: {t}. %lk%",
        "Scoring read [missed|was off]. {t} [fell short|came up short|didn't get there].",
        "{t} didn't get home. %lk%",
        "Total pick [missed|went red]: {t}. %lk%",
        "{t}? [Nope|Missed|No dice]. %lk%",
        "Bad read on the total — {t} [fell short|came up short|didn't get there]. %lk%",
        "Scoring didn't go our way. {t} [fell short|came up short|didn't get there].",
    )),
}


def review(kind, result, seed, used, lean=False, **kw):
    """One review for a graded pick: a line that fits what happened, rolled by this pick's seed (stable run to run),
    repeating no 4-word run already in `used` (a set shared across the whole Past Results section).
    lean=True: no hype (a lean had no edge). result "push": the money-back line."""
    if result == "push":
        key = ("push", "")                                   # (no numbers in a review)
    else:
        key = (kind, result)
    if key not in REVIEWS:
        return ""
    chars, sents, templates = REVIEWS[key]
    templates = [x for x in templates if "{x}" not in x] or templates   # no spread numbers in a review (the owner)
    kw.setdefault("pr", "they")
    kw.setdefault("pro", "them")
    kw.setdefault("pos", "their")
    kw.pop("s", None)
    kw = {k: v for k, v in kw.items() if re.search(r"\{%s\}" % k, " ".join(templates), re.I)}
    names = [n.strip() for v in kw.values() if not _num(v) for n in str(v).split(" and ") if n.strip()]
    for n in (30, 200):                                      # (names: "the Jets", "Over 44.5", "+3.5 games")
        opts = roll(templates, seed, (chars, sents), n, False, LEAN_BAN if lean else None, **kw)
        line = fresh(opts, used, names, _clash=True if n == 30 else None)
        if line:
            return line
    return ""


# ---- the live bets list on the dashboard (today's) -------------------------------------------------------------------
# a story = score + " " + what we thought + " — " + how it went. Caps are the old longest line of each piece.
LINES = {
    "ls:score": ((21, 1), False, T(
        '{an} {a}, {hn} {h} {w}.',
        'It was {an} {a}, {hn} {h} {w}.',
        '[Score was|Score read|Board read|Board said] {an} {a}, {hn} {h} {w}.',
        '{an} had {a}, {hn} had {h} {w}.',
        '[Got in|In|Posted|Bet in|Went in] at {an} {a}, {hn} {h} {w}.',
        '{w}: {an} {a}, {hn} {h}.',
        '{an} {a}, {hn} {h}, {w}.',
        '[Score|Board|Tally]: {an} {a}, {hn} {h} {w}.',
        '{w} it [was|read|sat at|stood] {an} {a}, {hn} {h}.',
        '{w}, [it was|we saw|board said] {an} {a}, {hn} {h}.',
        '{an} {a}-{h} {hn}, {w}.',
        '[At|Got in at|Posted at] {an} {a}-{h} {hn} {w}.',
    )),
    "ls:thought": ((20, 0), False, T(
        'We [thought|figured|said|knew|felt|swore] {us} would {what}',
        'We [had|liked|backed|rode|took|trusted] {us} to {what}',
        'We bet {us} would {what}',
        '{Algo} had {us} to {what}',
        '[Our read|Our call|The call]: {us} {what}',
        'Our money said {us} would {what}',
        '[Called|Picked|Tabbed] {us} to {what}',
        'We saw {us} [able|ready|set] to {what}',
        'We [said|swore] {us} could {what}',
        '[Figured|Thought] {us} could {what}',
    )),
    "ls:riding": ((19, 0), False, T(
        "We're [riding|on|with|rolling with] {us} to {what}",
        'We [like|got|need|want] {us} to {what}',
        '[Backing|Tailing|Riding|Taking] {us} to {what}',
        '{Algo} [likes|wants|has] {us} to {what}',
        '[Counting on|Banking on|Trusting] {us} to {what}',
        'We backing {us} to {what}',
        'Betting {us} can {what}',
        'In on {us} to {what}',
        '[Need|Want] {us} to {what}',
        '[Our|The] bet: {us} {what}',
    )),
    "ls:won_ran": ((99, 3), True, T(
        "the line ran all the way to +{best} and [they still cashed|it still cashed|we still got paid]. [Let's go|Levels to this|Told y'all|Nice nice]. 💰",
        "[books|the book|Vegas] pushed it out to +{best} and we held. [Cashed|Paid|Green]. [Trust the algorithm|Told y'all|Levels]. 💰",
        "it got as long as +{best} and they [got it done|came through|finished] anyway. [Told y'all|Let's go|Nice nice]. 💰",
        "the price drifted to +{best}, we held, [cashed|paid|got paid]. [Let's go|Levels to this]. 💰",
        "+{best} at one point and it still {won_v}. [Levels to this|Nice nice|Told y'all]. 💰",
        "the line hit +{best} on the way and they still {won_v}. [Let's go|Easy money]. 💰",
        "{book} had it at +{best} at one point. [Didn't matter|Still cashed|Still paid]. [Levels|Let's go]. 💰",
        'even at +{best} [nobody believed|{book} doubted it|folks bailed] — they {won_v}. 💰',
        'it stretched to +{best} and we never [flinched|blinked|budged]. [Paid|Cashed|Green]. 💰',
        "that [price|line|number] ran to +{best} and they still [got there|did it|came through]. [Let's go|Told y'all|Nice nice]. 💰",
    )),
    "ls:won": ((45, 2), True, T(
        "and they [did|delivered|got it done|came through|handled it|pulled it off]. [Cashed|Paid|Nice nice|Told y'all|Levels]. 💰",
        "and they {won_v}. [Told y'all|Nice nice|Let's eat|Paid|Levels]. 💰",
        "and [it hit|it cashed|we got paid|it paid|it went green]. [Told y'all|Light work|Nice nice]. 💰",
        'and they smacked that ass. 💰',
        'and [yup|bet|facts], they {won_v}. 💰',
        "and that's [exactly|just|precisely] what happened. 💰",
        'and they [pulled it off|made it happen|got there]. [Paid]. 💰',
        "and it [paid|went green|cashed]. [Let's eat|Light work|Say less]. 💰",
        '[called it|nailed it]. [Cashed|Paid|Green]. 💰',
        'and sure enough, they [did|got it done]. 💰',
        'which they did. [Cashed|Paid|Nice nice]. 💰',
    )),
    "ls:lost": ((49, 2), True, T(
        "they [shit the bed|never showed up|fumbled the bag|folded|came up short|laid an egg]. [Our bad|Is what it is|That's on us|Bad call|No excuses].",
        "they got cooked. [Our bad|That's on us|No excuses].",
        "they {lost_v}. [Our bad|Is what it is|That's on us|Bad call|We own it].",
        "it didn't happen. [Our bad|Bad call|Next one's ours|That's on us].",
        'nope. [Wrong read|Bad call|Missed it], [our bad|on us].',
        "didn't happen. [That's on us|No excuses|Our bad].",
        "they [never got there|ran out of time|ran outta road]. [Next one's ours|Our bad].",
        'swing and a miss. [Our bad|Is what it is|On us].',
        "we were wrong. [Next one's ours|It happens|We own it|Our bad].",
        'it went red. [Our bad|Short memory|We own it].',
        'they were booty cheeks. [Is what it is|Our bad].',
        "no dice. [That's on us|Our bad].",
    )),
    "ls:pending": ((38, 2), True, T(
        "we gon' see.",
        "they about to [go to work|get busy|handle business]. We gon' see.",
        "[now|so] we gon' see.",
        "[let's ride|light work|let's eat]. We [gon'|finna] see.",
        "they cooking soon. We [gon'|finna] see.",
        'we finna see.',
        "{book} is sleeping. We [gon'|finna] see.",
        "[hold tight|buckle up|stay tuned|sit tight], we gon' see.",
        "fingers crossed. We gon' see.",
        "we'll know [soon|in a bit]. [Let's ride].",
        "clock's ticking. We [gon'|finna] see.",
        "hammer time. We [gon'|finna] see.",
        "don't be a sheep. We gon' see.",
    )),
    # 🎾 live bets: the score from our player's side ({at}) + how it went
    "tn:score": ((26, 1), False, T(
        '{at} when it went up.',
        'It was {at}.',
        'We got in at {at}.',
        '[In|Got in|Bet in|Went in] at {at}.',
        '[Posted|Went up|Jumped in|Hopped in] at {at}.',
        '{at} at post.',
        '[Score at post|Entry|At post]: {at}.',
        '{at} when we [bet it|got in|jumped in].',
        'We [hopped|jumped|got] in at {at}.',
        'Score was {at}.',
        'It [read|stood at|sat at] {at}.',
        '{at} on the board.',
    )),
    "tn:won": ((41, 2), False, T(
        "{me} [turned it around|got it done|came through|flipped it|found a way|closed it out]. [Cashed|Paid|Told y'all|Nice nice|Levels]. 💰",
        '{me} came through — {he} was never out of it. 💰',
        '[Cashed|Paid] — {me} [came back|turned it|did it|got there]. 💰',
        '{me} [won it|got the W|took it]. [Levels to this|Light work|Nice nice]. 💰',
        '{me} [did {his} thing|took care of business|handled it]. 💰',
        '[Paid|Cashed]. {me} [pulled it off|finished the job|closed]. 💰',
        '{me} said [not today|nah]. [Cashed|Paid]. 💰',
        'Never out of it. {me} [won|got there|closed]. 💰',
        '{me} [dug out|climbed out the hole|bounced back]. 💰',
        'W for {me}. [Cashed|Paid]. 💰',
    )),
    "rc:battle": ((110, 3), False, T(   # our player won in straight sets, but the other one made a set a real fight
        "{opp} fought hard but still got {his} cheeks clapped {sets}. Easy money. Trust the fucking algorithm, baby. 💰",
        "{opp} [battled|scrapped|hung around] but {who} still [swept|took] it {sets}. Easy money. Trust the algorithm. 💰",
        "{opp} made {who} work for it — still {sets}, still [cashed|paid]. Trust the algorithm, baby. 💰",
        "Tough fight from {opp}, didn't matter. {who} {sets}. [Easy money|Light work]. 💰",
        "{opp} gave {who} a scare, then got sent home {sets}. [Easy money|Cashed]. Trust the algorithm. 💰",
    )),
    "tn:lost": ((40, 2), False, T(
        "{me} [couldn't close the gap|ran out of road|never found the turn|couldn't flip it|came up short|ran outta gas]. [Is what it is|Our bad|Next one's ours|It happens].",
        'No comeback from {me}. [Our bad|It happens].',
        '{me} [fought|battled|scrapped] but lost. [Our bad|It happens].',
        '{me} never got going. [Our bad|On us].',
        "Didn't happen for {me}. [Our bad].",
        "{me} [dropped it|lost it]. [That's on us|Our bad|We own it].",
        'Not {his} day. [Our bad|It happens].',
        "L on {me}. [Next one's ours|Short memory].",
        '{me} fell short. [It happens|Our bad].',
        'Wrong read on {me}. [We own it|Our bad].',
        '{me} got cooked. [Our bad|That one\'s on us].',
        '{me} shit the bed. [Our bad|No excuses].',
    )),
    "lv:hold": ((34, 2), False, T(      # a live bet still going: no score, no read on how it's going - just the hold.
        #                                 9/29: "sticking with X till it's done" twice in one night read like a machine -
        #                                 every line a different shape, and only one or two end in "we finna see"
        "Locked in on {me}. We [gon'|finna] see.",
        "[Riding|Rolling|Sticking] with {me} till it's done.",
        "Ticket's in on {me}. Now we watch.",
        "We on {me}. Holding till the end.",
        "{me} is the call. We ride it out.",
        "{me} it is. Holding [tight|steady] till it's over.",
        "No moves, just {me}. Let it play.",
        "Money's down on {me}. Let's eat.",
        "Tapped in on {me}. Let it play out.",
        "Our money's with {me}. Let it ride.",
        "{me} for the win. Trust the algorithm.",
        "Backing {me} the rest of the way.",
        "Plus money on {me}. We'll take that shot.",
        "The numbers liked {me} here. Sitting back now.",
        "{me}'s the play. No sweat, let it run.",
        "Grabbed {me} live. Now it plays out.",
        "{me} got the nod. Let's see it through.",
        "Down with {me} to the last point.",
        "{me} at a live price. We here for it.",
        "Put it on {me}. Easy does it from here.",
    )),
    "tn:pend": ((34, 2), False, T(
        "We like {me} from here — we [gon'|finna] see.",
        "[Riding|Rolling|Sticking] with {me}. We [gon'|finna] see.",
        "{me}'s still [swinging|in it|fighting]. We gon' see.",
        "{me} got work to do. We [gon'|finna] see.",
        "{me} still in it. We [gon'|finna] see.",
        "Come on {me}. We [gon'|finna] see.",
        "Still live with {me}. [Let's go].",
        "{me}'s [cooking|heating up]. We gon' see.",
        "[Let's go|Come on], {me}. We [gon'|finna] see.",
        'All eyes on {me} [now|here].',
        "{me} to finish it. We gon' see.",
        "Need {me} to [close|finish]. We gon' see.",
    )),
    # 🎾 the result on top of a graded tennis pick ({sc} = " (6-4, 6-3)" from our player's side, or "")
    "rc:cover": ((64, 2), False, T(   # (no scores, no spread numbers in a review - the owner, 9/28)
        '💰 {who} [lost the match|dropped the match|took the L] but kept it close enough. [Cashed.|Paid.|Money.]',
        '💰 Lost the match, won us the bet — {who} kept it close.',
        '💰 {who} [kept it close|hung around|made it tight|stayed close]. The games [came through|got there|delivered].',
        '💰 L on the court, W on the ticket. {who} [came through|got there|delivered].',
        "💰 {who} [lost|fell|went down] but the games [cashed|paid|hit]. That's why we took the games.",
        '💰 Took the games for a reason: {who} [lost|fell] and we still [covered|cashed].',
        '💰 {who} [covered|cashed|paid] even in the loss.',
        '💰 Match went the other way, but {who} [covered|cashed] for us.',
        '💰 {who} [fell|lost] and [still covered|still got us paid|still cashed].',
        '💰 Covered. {who} lost the match, not the bet.',
    )),
    "rc:won": ((39, 2), False, T(
        "💰 {who} [got it done|handled business|came through|went to work|took care of it|smacked that]{sc}. [Cashed.|Paid.|Told y'all.|Nice nice.|Easy money.|Light work.]",
        '💰 [Cashed|Paid|Money] — {who} [went to work|did it|won it|handled it]{sc}.',
        "💰 {who} [came through|got there|delivered|got it done]{sc}. [Let's eat.|Paid.|Nice nice.]",
        '💰 W for {who}{sc}. [Paid.|Cashed.]',
        '💰 {who} [won|took it|closed it]{sc}. [Paid.|Cashed.]',
        '💰 [Easy work|Light work|Clean work] from {who}{sc}.',
        '💰 {who} delivered{sc}. [Nice nice.|Say less.|Paid.]',
        '💰 {who} did {his} thing{sc}.',
        '💰 [Paid|Cashed|Green]: {who}{sc}.',
        '💰 {who} [cooked|ate]{sc}. [Money.|Paid.]',
    )),
    "rc:lost": ((54, 2), False, T(
        "😤 {who} [shit the bed|fumbled it|never showed up|folded|came up short|got cooked|didn't have it]{sc}. [Is what it is.|Our bad.|Bad call, our bad.|Next one's ours.|That's on us.|No excuses.]",
        "😤 That one's on us — {who} [folded|lost|fell]{sc}. We don't hide nothing.",
        '😤 {who} was booty cheeks today{sc}. [Our bad.|On us.]',
        "😤 Missed{sc}. {who} didn't have it today. [Our bad.|On us.]",
        '😤 L for {who}{sc}. [It happens.|On to the next.|Our bad.]',
        '😤 {who} [dropped it|lost it]{sc}. [Wrong call|Bad read], our bad.',
        "😤 Not {his} day{sc}. [We own it.|That's on us.|Our bad.]",
        "😤 {who} went down{sc}. [Short memory.|Next one's ours.]",
        '😤 Red ticket{sc}: {who} [lost|fell short]. [Our bad.]',
        '😤 {who} ran outta gas{sc}. [Our bad.|Is what it is.]',
    )),
}


def live_story(result, seed, used, ran=False, **kw):
    """(score, thought, end) of a live bet on the list - kw: an a hn h w us what best."""
    score = say("ls:score", seed, used, an=kw["an"], a=kw["a"], hn=kw["hn"], h=kw["h"], w=kw["w"])
    k = "ls:thought" if result in ("won", "lost") else "ls:riding"
    thought = say(k, seed, used, us=kw["us"], what=kw["what"])
    if result == "won" and ran:
        end = say("ls:won_ran", seed, used, best=kw["best"])
    elif result in ("won", "lost"):
        end = say(f"ls:{result}", seed, used)
    else:
        end = say("ls:pending", seed, used)
    return f"{score} {thought} — {end}"


# ---- LIVE PLAYS (sports_live): the short line + the tap-to-open breakdown -------------------------------------------
LINES.update({
    "lv:ball": ((87, 4), False, T(
        "{i} {us} %dn% {m} but they got %ball% and they're marching. [Hammer it|Get in|Let's eat].",
        "{i} %Dn% {m}? Who cares. {us} got %ball% and {them} can't stop nobody.",
        "{i} {us} %dn% {m} with the ball in their hands. {Book} is sleeping — %go_%.",
        "{i} {them} up {m} and the dummies think it's over. {us} got %ball%.",
        "{i} {us} %dn% {m}, ball in hand, %pm%. [Say less|Get in|Easy decision].",
        "{i} %Dn% {m} but driving. {us} [about to|finna] [cut into it|punch back|go to work].",
        "{i} {us} got %ball% %dn% {m}. {Book} ain't ready.",
        "{i} {us} %dn% {m}, but they're [on the move|marching|driving]. %go%.",
        "{i} {us} only %dn% {m} with the ball. This price is {cheap}.",
        "{i} {them} up {m}, but {us} got %ball%. %go%.",
        "{i} Ball's with {us}, down just {m}. [Points coming|Here we go]. %go%.",
    )),
    "lv:better": ((105, 3), False, T(
        "{i} {us} %dn% {m}? Rough start, but they're %bt% and we get 'em at %pm%. %go%.",
        "{i} Everybody jumping off {us} %dn% {m}. Not us. Better team, %pm% — let's eat.",
        "{i} {us} been booty cheeks so far, %dn% {m}. That don't last. [Way better team|Better squad] — they about to go to work.",
        "{i} %Dn% {m} ain't done. {us} got way too much for {them}, and {book} is handing us %pm%.",
        "{i} {them} up {m} and they must think they're good. They ain't. {us} about to smack that ass.",
        "{i} Slow start, %dn% {m}. {us} still the [better team|stronger side]. %go%.",
        "{i} {us} %dn% {m}? The better team don't stay down. [Levels to this|Let's eat].",
        "{i} We had {us} as %bt% before this started. %Dn% {m} don't change that. %go%.",
        "{i} Better team, bad start, %pm%. {us} %dn% {m} — [let's eat|we eating|get in].",
        "{i} {us} %dn% {m} and {book} is panicking. We're not. [Levels to this|Buy the dip].",
        "{i} {us} %dn% {m}, but talent wins out. %Pm% on %bt% is {cheap}.",
    )),
    "lv:momentum": ((85, 3), False, T(
        "{i} {us} %dn% {m} but they just took the last {per}. The comeback's loading — %go_%.",
        "{i} {us} been climbing back and %price% still says they're dead. They're not. %go%.",
        "{i} {us} won the last {per} and they're only %dn% {m}. %go%.",
        "{i} %Dn% {m}, but {us} [won|took|owned] the last {per}. [Buy the dip|Get in|We cooking].",
        "{i} {us} heating up — took the last {per}, down just {m}.",
        "{i} The last {per} was all {us}. %Dn% {m} with the arrow pointing up. %go%.",
        "{i} {us} got the momentum after taking the last {per}. %Dn% {m} is nothing.",
        "{i} Comeback loading: {us} took the last {per}, %dn% {m}. %go%.",
        "{i} {them} up {m} but they lost the last {per}. {us} coming.",
        "{i} {us} woke up — won the last {per}. %Dn% {m} and %pm%? [Say less|Get in].",
    )),
    "lv:trail_nhl": ((83, 2), False, T(
        "{i} {them} might've got the first goal, but {us} about to bounce back and smack that ass.",
        "{i} {us} %dn% {m}, plenty of hockey left and %price% is too juicy. %go%.",
        "{i} %Dn% {m} with plenty of hockey left? {us} at %pm% is {cheap}.",
        "{i} {us} %dn% {m}. One bounce and it's a new game. %go%.",
        "{i} Plenty of time on the clock and {us} only %dn% {m}. %go%.",
        "{i} Hockey's weird, %dn% {m} ain't dead. {us} at this price? [Say less|Tail it].",
        "{i} {us} %dn% {m}, but goals come in bunches. %go%.",
        "{i} {them} up {m} and {book} thinks it's over. It ain't.",
        "{i} {us} %dn% {m}, lots of hockey left. This price is {cheap}.",
        "{i} {us} trailing {m}, still plenty of time. [Get in|We buying].",
    )),
    "lv:trail": ((86, 3), False, T(
        "{i} {us} %dn% {m}. Teams in this spot come back {more}. Buy the dip.",
        "{i} The dummies are about to sell {us} %dn% {m}. We buying. [Trust the algorithm|Get in].",
        "{i} {us} %dn% {m}, and the comeback price is {cheap}. %go%.",
        "{i} %Dn% {m} ain't dead. {us} at %pm%? [Say less|We buying].",
        "{i} {us} %dn% {m}. {Book} is selling, we buying.",
        "{i} Everybody bailing on {us} %dn% {m}. We're buying the dip.",
        "{i} {us} %dn% {m}, but this spot comes back {more}.",
        "{i} {us} trailing {m}? Plenty of game left. %go%.",
        "{i} {them} up {m}, but it's %over%. {us} at this price is {cheap}.",
        "{i} %Dn% {m}, {us} got time. %Price% don't respect that.",
        "{i} {us} %dn% {m} — history says this ain't over. %go%.",
    )),
    "lv:up": ((76, 3), False, T(
        "{i} {us} up {m} and STILL %pm%? {Book} is sleeping — take it before it moves.",
        "{i} {us} up {m} and {book} got them as the dog. That's a gift. [Hammer it|Take it].",
        "{i} Up {m} at %pm%? {us} all day. {Book} is cooked on this one.",
        "{i} {us} leading by {m} at %pm%. [Say less|Easy decision|Tail it].",
        "{i} %Pm% on the team that's up {m}? [Say less|Don't overthink it].",
        "{i} {us} ahead {m}, still the dog. That's {cheap}.",
        "{i} {us} up {m} and nobody's respecting it. We are.",
        "{i} Leading by {m} and still %pm%. %go% before {book} wakes up.",
        "{i} {us} up {m}. %Price% says dog. We say [let's eat|tap in].",
        "{i} {them} %dn% {m} and somehow favored. We taking {us}.",
    )),
    "lv:tied": ((79, 3), False, T(
        "{i} All tied up and {us} still %pm%. {Book} got this wrong — %go_%.",
        "{i} Dead even and the live line's got {us} as the dog. The numbers don't. %go%.",
        "{i} Tied game, {us} at %pm%. That's {cheap}.",
        "{i} Even score, {us} at %pm%? [Say less|Tail it|Get in].",
        "{i} Level game and {us} still the dog. We'll take that [all day|every time].",
        "{i} Tied up. {us} the side at %pm%. [Let's eat|Get in].",
        "{i} Nobody's ahead, but {book} has {us} as the dog. [Wrong|Mistake]. %go%.",
        "{i} Tie game. %Pm% on {us} is {cheap}.",
        "{i} Score's even and {us} still %pm%. [Let's eat].",
        "{i} Knotted up, {us} priced like the dog. [We buying|Take it].",
    )),
    "bd:hist_trail": ((139, 3), False, T(
        "📚 We did our homework: {ng} games where {who} were down about {d} {spot} — {rate} of 'em came back and won. [This price|This number|The line] only needs {be}.",
        "📚 %Dn% {d} ain't dead. In {ng} games like this, {who} came back {rate} of the time. {Book} [has it at|says|prices it like] {be}.",
        "📚 [History don't lie|The study don't lie|Receipts don't lie]: {rate} of {who} down {d} {spot} still won ({ng} games). At this number you only need {be}.",
        '📚 The comeback study says {who} in this spot win {rate} of the time ({ng} games). %Price% needs {be}.',
        "📚 {ng} games, same spot: {who} down about {d} {spot} won {rate}. Break-even here is {be}. [That's the edge.|Math is math.|That's value.]",
        '📚 Receipts: {who} down {d} {spot} came back to win {rate} of {ng} games. We only need {be} at [this price|this number].',
        '📚 We ran it [back|through] {ng} games. {who} down {d} {spot} won {rate} — %price% needs {be}.',
        '📚 {rate} of {who} in this exact spot (down {d} {spot}) came back. [Sample|Games]: {ng}. Break-even: {be}.',
        '📚 Down about {d} {spot}? {who} win that {rate} of the time over {ng} games. [This number|This price] needs {be}.',
        "📚 The study don't flinch: {ng} games, {who} down {d} {spot}, {rate} came back. {Book} [says|has it at] {be}.",
        '📚 Comebacks from down {d} {spot}: {rate} across {ng} games. We need {be}. {gap}',
    )),
    "bd:hist_up": ((106, 3), False, T(
        '📚 {ng} games like this: {who} up about {d} {spot} [closed it out|finished it|held on] {rate} of the time. [This price|This number|The line] only needs {be}.',
        '📚 {us} up {d} and still %pm%? {who} in this spot [finish the job|close it out|hold on] {rate} of the time ({ng} games).',
        '📚 [History says|The study says|Receipts say] {who} up {d} {spot} hold on {rate} of the time ({ng} games). We only need {be}.',
        '📚 {who} up {d} {spot} won {rate} of {ng} games. [Break-even here|Break-even|The price needs]: {be}.',
        '📚 Leads like this [hold|stick|last]: {rate} over {ng} games. %Price% needs {be}.',
        '📚 Up about {d} {spot}, {who} [close it|finish it|hang on] {rate} of the time ({ng} games). We need {be}.',
        '📚 {ng}-game sample, same spot: {rate} held on. [This number|This price|The line] only asks {be}.',
        '📚 Receipts: {who} up {d} {spot} [finished it|closed it|held on] {rate} of the time. We need {be}.',
        '📚 {rate} of {who} up {d} {spot} closed it out ({ng} games). {gap}',
        '📚 The study: {ng} games, {who} up {d} {spot}, {rate} won. [Price needs|Break-even:|We need] {be}.',
    )),
    "bd:better": ((86, 2), False, T(
        "💪 {us} came in as the favorite. One bad stretch don't make 'em [trash|frauds|washed].",
        "💪 {us} %bt%, period. The scoreboard's just late to the party.",
        '💪 {them} got [lucky|hot] early. {us} %bt% and they about to go to work.',
        '💪 Real ones know {us} better than {them}. {Book} is panicking over a few plays.',
        "💪 {us} [came in favored|had the better number pregame|were favored coming in]. [A slow start|One bad stretch|A few plays] don't change that.",
        '💪 On %ours%, {us} got more than {them}. [It shows eventually|Talent shows up|Give it time].',
        '💪 {us} still %bt%. [The score catches up|Scoreboard catches up|It evens out] eventually.',
        '💪 Better roster, worse start. {us} got [time|the talent|the horses] to flip it.',
        "💪 {them} ain't better than {us}. They just started [hot|lucky].",
        "💪 {us} favored pregame for a reason. [Talent wins out|That don't disappear|Class shows].",
        "💪 Talent gap favors {us}. [Scoreboard just ain't caught up|Give it time|It'll show].",
    )),
    "bd:pre": ((79, 2), False, T(
        "🧠 {Algo} was already on {us} before the game. Now we get 'em %sale%.",
        '🧠 We liked {us} pregame — %price% just made it [juicier|sweeter|better]. Double dip.',
        "🧠 {Algo} had value on {us} before the game even started. Now it's even better.",
        '🧠 Pregame we were on {us}. [Live price|Live number|Now]? [Even better|Juicier|Sweeter].',
        '🧠 Same side as pregame: {us}. [Better price|Better number|Cheaper] now.',
        "🧠 Had {us} pregame. Now they're %sale%. [Double dip|Tail it|Say less].",
        '🧠 We were already on {us}. The live number just [sweetened|juiced] it.',
        '🧠 Value on {us} pregame, more value now. [Say less|Double dip|Tail it].',
        '🧠 {us} our side coming in. Now %sale%.',
        '🧠 Pregame read had {us}. Live price is {cheap}.',
    )),
    "bd:half": ((69, 2), False, T(
        "🏈 And {us} get the ball to start the 2nd half. That's a [free possession|bonus drive|free shot].",
        '🏈 {us} receive the 2nd-half kickoff — first crack at it after the break.',
        "🏈 Ball's theirs coming out of halftime. {Algo} counted that.",
        '🏈 {us} get the ball out of the half. [Extra possession|Free drive|Bonus drive].',
        '🏈 2nd half starts with {us} on offense. [Free possession|Bonus drive|Extra shot].',
        '🏈 Coming out of the half, {us} got the ball first.',
        '🏈 First drive of the 2nd half belongs to {us}.',
        '🏈 {us} get the opening drive after the break. {Algo} counted that.',
        "🏈 Halftime flip: {us} receive. That's a [free shot|bonus drive|free possession].",
        '🏈 [Bonus|Free|Extra] possession: {us} receive after the break.',
    )),
    "bd:ball": ((59, 2), False, T(
        '🏈 They got %ball% ({txt}). [Points are coming|Points loading|Six loading].',
        "🏈 Ball's in their hands at {txt}. Next score is theirs to take.",
        "🏈 {us} got %ball% ({txt}) and {them} can't stop nobody.",
        '🏈 {us} [driving|marching|moving]: {txt}. [Points loading|Six loading|Points coming].',
        '🏈 Ball at {txt}. {us} knocking on the door.',
        '🏈 {txt} and {us} got it. [Points coming|Scoring chance].',
        '🏈 {us} on the move at {txt}. [Six loading|Points loading].',
        "🏈 Possession {us}, {txt}. [Next score's theirs|Points coming].",
        '🏈 {us} got %ball% at {txt}. [Points loading].',
        '🏈 Drive alive: {us}, {txt}.',
    )),
    "bd:momentum": ((52, 2), False, T(
        '🔥 {us} [took|won|owned] the last {per} {w}-{l}. They [cooking|rolling|heating up] now.',
        '🔥 {us} [won|took] the last {per} {w}-{l}. {them} in trouble.',
        '🔥 Last {per}: {us} {w}-{l}. [Heating up|Cooking|Rolling].',
        '🔥 {us} {w}-{l} in the last {per}. [Momentum|Heat check].',
        '🔥 {w}-{l} last {per}, {us} [rolling|on a heater|cooking].',
        '🔥 {us} [owned|took|ran] the last {per}, {w}-{l}.',
        '🔥 {us} flipped it: {w}-{l} last {per}.',
        '🔥 {us} rolling — last {per} went {w}-{l}.',
        '🔥 {us} woke up: {w}-{l} last {per}.',
        '🔥 {w}-{l} in the last {per}. {us} [cooking|locked in|rolling].',
    )),
    "bd:bottom": ((79, 3), False, T(
        "🎯 The numbers are on our side and {book} is asleep. [Trust the algorithm|Get in].",
        "🎯 This is the spot. Get in before the line catches up. Let's fucking go.",
        "🎯 Value like this don't last — {book} gonna wake up. We're on it.",
        "🎯 Don't be a sheep. The dummies are selling, we buying.",
        "🎯 {Algo} says value. [Tail it|Get in|Let's eat].",
        "🎯 Price is {cheap} right now. [Get in|Tail it] before it moves.",
        "🎯 Window's open. [Get in|Tail it] before {book} catches up.",
        "🎯 Edge is live. [We're on it|We in]. [Let's eat].",
        "🎯 %Pm% with real value. [Say less|Tail it|Let's eat].",
        "🎯 {Algo} and the score agree: this price is {cheap}.",
        "🎯 The {edge_noun} is right there. [Grab it|Take it] before it's gone.",
    )),
    # 🎾 live tennis ({sit} = "dropped the first set, but she's up 3-1 in the 2nd" - always from our player's side)
    "tl:dd": ((110, 3), False, T(
        "🔁 Double down — we had {him} pregame, {he} {sit}, now {he}'s {o} and %ours% says that's too long.",
        '🔁 Double down. {me} was our pick before the %serve%. {he} {sit} and {book} let {him} drift to {o}.',
        '🔁 Double down on {me}: {he} {sit}, %price% went to {o}, and the numbers still like {him} way more than that.',
        "🔁 Double down. We had {me} pregame and we're not jumping off. {he} {sit} — {o} is too long.",
        '🔁 Double down on {me}. {he} {sit}, and {o} is {cheap}.',
        '🔁 Double down: our pregame pick {me} {sit}. At {o}? [Say less|Back in|We reloading|Run it back].',
        '🔁 Double down. {me} {sit}, %price% drifted to {o}. [We reloading|Back in|Same side, better number].',
        '🔁 We had {me} pregame. {he} {sit}. Now {o}? Double down.',
        '🔁 Double down time: {me} {sit}. {o} for our pregame pick is {cheap}.',
        '🔁 Going back to {me} — double down at {o}. {he} {sit}.',
    )),
    "tl:trail": ((85, 3), False, T(
        "🎾 {me} {sit}, and {book} overreacted: {o} for a player we had as the favorite.",
        "🎾 {me} came in as %bp% on %ours%. {he} {sit} — {o} is too big a price for that.",
        "🎾 {Book} is pricing {me} like it's over at {o}. {he} {sit}. It ain't over.",
        "🎾 {me} {sit}. Everybody's jumping off — we're jumping on at {o}.",
        "🎾 {me} at {o}? {he} {sit}, but {he}'s still %bp% out there. %go%.",
        "🎾 {me} {sit}. {o} is {cheap} for %bp%.",
        "🎾 Buy the dip: {me} {sit}, now {o}.",
        "🎾 {me} {sit}, but one break flips it. {o}? %go%.",
        "🎾 {me} {sit}. We had {him} favored. {o} is a gift.",
        "🎾 Panic price on {me}: {o}. {he} {sit}, %over%.",
        "🎾 {o} on {me}, who {sit}. [Buy the dip|We buying].",
    )),
    "tl:level": ((75, 3), False, T(
        "🎾 {me} {sit} and still %pm% at {o}? We'll take that all day.",
        "🎾 {me} {sit} and {book} still got {him} as the dog ({o}). The numbers say otherwise.",
        "🎾 {o} on {me}, who {sit}? %Price% is behind the match. %go%.",
        "🎾 {me} {sit}, yet {o}? [Say less|Tail it|Get in].",
        "🎾 {me} {sit}. %Pm% at {o} is {cheap}.",
        "🎾 {me} {sit} and priced like the dog at {o}. [We'll take it|Easy decision].",
        "🎾 {o} for {me}? {he} {sit}. [Get in|Tail it].",
        "🎾 %Price% ({o}) ain't caught up: {me} {sit}.",
        "🎾 {me} {sit}, and we get {him} at {o}. [Let's eat].",
        "🎾 {me} {sit}. {Book} still says {o}. We say [get in|tail it].",
        "🎾 {me} at {o} while {he} {sit}? [Light work|Say less].",
    )),
    "tl:ours": ((81, 2), False, T(
        '🧠 {me} was one of our tennis picks today — {algo} liked {him} before the %serve%.',
        '🧠 We posted {me} pregame. Same player, [way better|much better|juicier] price now.',
        '🧠 {me} was already on our tennis card. Now %price% is doing us a favor.',
        '🧠 {me} was our pregame pick. [Same read|Still our side], [better number|better price|juicier price].',
        '🧠 We had {me} before the %serve%. Now we get {him} %sale%.',
        '🧠 {me} on our card today. The live number just [sweetened it|made it better|got juicier].',
        '🧠 Pregame pick: {me}. Live price: [even better|juicier|sweeter].',
        '🧠 {Algo} was on {me} before the match. [Still on {him}|Still is|Same read now].',
        '🧠 Same side as our pregame card — {me}. [Better number now|Price got better|Cheaper now].',
        "🧠 Our card had {me} pregame. Now {he}'s %sale%.",
    )),
    "tl:strong": ((70, 1), False, T(
        '💪 On %ours% {me} came in at {sp}% to win this match.',
        '💪 Before the %serve% {algo} had {me} winning this {sp}% of the time.',
        '💪 {me} was %bp% coming in — {sp}% on %ours%.',
        '💪 [Pregame|Coming in], we had {me} at {sp}% to win it.',
        '💪 {me} came in a {sp}% favorite on %ours%.',
        '💪 {Algo} made {me} {sp}% to win before a ball was hit.',
        '💪 {sp}% pregame for {me} on %ours%.',
        '💪 Coming in, {me} won this {sp}% of the time on %ours%.',
        '💪 [Our pregame number|Our number coming in|The pregame read] on {me}: {sp}%.',
        '💪 We had {me} at {sp}% before it started.',
    )),
    "tl:state": ((81, 2), False, T(
        '🎾 Score check: {me} {sit}{serve}. {he} holds serve {hp}% of the time on %ours% — %over%.',
        '🎾 {me} {sit}{serve}. A player who holds {hp}% of {his} service games is still [very much in this|right there|in it].',
        '🎾 Where it stands: {me} {sit}{serve}. {he} holds {hp}% of the time — one break changes everything.',
        "🎾 {me} {sit}{serve}. With a {hp}% hold rate, {he}'s [still right there|far from done|still live].",
        '🎾 {me} {sit}{serve}. {he} holds {hp}% — [plenty of tennis left|one break flips it|far from over|still live].',
        '🎾 [Right now|As we speak|Currently] {me} {sit}{serve}. Holds {hp}% on %ours%.',
        "🎾 [Score|Status]: {me} {sit}{serve}. {hp}% hold rate says [it ain't over|far from over|still live|not done].",
        '🎾 {me} {sit}{serve}, and {he} holds {hp}% of the time. [Still in it|Still live|Far from over|Not done].',
        "🎾 {me} {sit}{serve}. [Serve's a weapon|That serve travels]: {hp}% holds.",
        '🎾 [State of play|Where we at]: {me} {sit}{serve}. {he} holds {hp}%.',
    )),
    "tl:math": ((102, 2), False, T(
        "📐 The point-by-point model (sets, games, points, who's serving) gives {him} {pct}% from here. {o} only needs {be}%.",
        '📐 Run every point from this score: {me} wins it {pct}% of the time. %Price% needs {be}%.',
        '📐 Our tennis model plays it out point by point from right here: {pct}% for {me}. Break-even at {o} is {be}%.',
        '📐 From this exact score, {algo} has {me} at {pct}%. {o} needs {be}%.',
        '📐 {pct}% from here on %ours%. At {o}, we only need {be}%.',
        '📐 [Sim it|Play it out|Run it] from this score and {me} wins {pct}%. Break-even at {o}: {be}%.',
        '📐 {me} from here: {pct}%. %Price% only asks {be}%.',
        "📐 [Our model|The model|The math] gives {me} {pct}% from this spot. {o} implies {be}%. That's the {edge_noun}.",
        "📐 {pct}% to win from here vs {be}% break-even at {o}. [Math is math|Numbers don't lie].",
        '📐 Play out every point from here: {me} {pct}%, price {be}%.',
    )),
    "tl:bottom": ((65, 2), False, T(
        "🎯 The numbers are ahead of {book} on this one. [We're on it|We in|Tail it].",
        "🎯 %Price% hasn't caught up to the match. [Get in|Tail it] before it does.",
        "🎯 Live tennis swings fast — this is the window. [We're in|Get in|Tail it].",
        "🎯 Window's open. [Get in|Tail it|We in].",
        "🎯 {Book} is a step behind. [We're on it|Tail it|Get in].",
        '🎯 One break changes everything. [We in|Tail it].',
        "🎯 Price is {cheap}. [We're on it|Get in|Tail it].",
        "🎯 {Algo} says go. [Let's eat|We in|Tail it].",
        "🎯 Numbers over feelings. [We're on it|Tail it|Get in].",
        '🎯 This is the spot. [Get in|We in|Tail it].',
        "🎯 Levels to this. [We're on it|Tail it|Get in].",
    )),
})


# ---- BOARD NOTES: a short board / a leans-only day says so up top ---------------------------------------------------
NOTES = {
    "short1": T(
        "[Just|Only] one [play|pick|spot] [today|on the board today].", "One [pick|play] today, that's it.",
        "Only one made the cut today.", "One and done today.", "Just the one today.", "One spot today.",
        "It's a one-pick kinda day.", "One [play|pick] on the card today.", "We got one [today|for y'all today].",
        "One bullet in the chamber today.", "Board's got one play today.", "One [shot|swing] today, that's all.",
    ),
    "shortn": T(
        "[Only|Just] {cnt} [plays|picks|spots] today.", "{cnt} plays today, not the usual 5.",
        "Short board today — {cnt} plays.", "{cnt} spots made it today.", "Light card today: {cnt} plays.",
        "Trimmed-down board: {cnt} plays.", "{cnt} [picks|plays] [on the card|on the board] today, that's [all|it].",
        "Board's [thin|light|short] today: {cnt} [plays|picks].", "We only got {cnt} [today|on the card].",
        "{cnt} made the cut today.", "{cnt} [plays|picks], not 5. On purpose.",
    ),
    "short_why": T(
        "{Algo} only found {it} with a real edge.", "[Everything else|The rest] was a coin flip or overpriced.",
        "Nothing else cleared the bar.", "The rest of the slate didn't give us value.",
        "{Book} got the rest priced tight.", "The rest ain't worth the risk on our numbers.",
        "That's all the value on the board.", "{Algo} passed on the rest.",
        "The other games didn't give us a reason.", "{Algo} only liked {it}.",
        "The rest of the games? [No edge|Priced right|Coin flips].", "Everything else [came up short|was a pass].",
        "No parlays — the legs ain't strong enough and we don't force it.", "No parlay tonight. We don't stack coin flips.",
    ),
    "close": T(
        "We don't force picks just to have picks.", "We ain't filling the board with junk.", "Quality over quantity.",
        "No filler over here.", "We ride what the numbers like and leave the rest.", "The pros pick their spots.",
        "Patience pays.", "Less is more today.", "We wait on our spots.", "That's how you stay up.",
        "Not every game deserves our money.", "Forcing it is how bankrolls die.", "We don't chase.",
        "Sitting out is a play too.", "Discipline over everything.", "Smart money waits.",
        "We only swing at our pitch.", "No reaching today.", "If it ain't there, it ain't there.",
        "Tomorrow's another slate.", "We ain't clowns betting blind.", "We're not out here betting just to bet.",
        "Blind betting is for the clowns.",
        "No action for action's sake.", "[Levels to this|Nice nice]. We [wait|pick our spots].",
    ),
    "lean_open": T(
        "No locks and no value picks today.", "Zero locks, zero value today.", "No locks today, no value either.",
        "No locks. No value picks.", "[Nothing|Not one game] made the board as a lock or value today.",
        "No locks, no value [on the board|today].", "[Zero|No] locks and [zero|no] value plays today.",
        "Today's board: no locks, no value.", "No lock, no value pick — [none|not one] today.",
    ),
    "lean_why": T(
        "{Algo} checked every game and didn't find an edge on any of them.",
        "Every game got looked at — nothing gave us an edge.", "{Book} got everything priced right today.",
        "Nothing cleared the value bar.", "Every line on the slate is about where it should be.",
        "{Algo} went through the whole slate and nothing jumped out.",
        "No spot today where our numbers beat the price.", "{Book} was sharp on every game today.",
        "Whole slate checked, [no edge anywhere|nothing worth our money].",
    ),
    "lean_tail": T(
        "It's leans only today — just which way {algo} leans:", "Leans only — just which way {algo} leans:",
        "Here's how {algo} leans, that's it:", "Just leans today — a lean ain't a lock:",
        "Leans only. Take 'em for what they are:", "All we got is leans — here's where {algo} tilts:",
        "Leans only, [no more|nothing more]. Which way {algo} leans:", "Just the leans — where {algo} tilts:",
        "Leans, not picks. Which way {algo} leans:",
    ),
    # 🐺 no Dog of the Day: no underdog with a proven edge today (the owner, 9/28: say so, don't force one)
    "dog_open": T(
        "No Dog of the Day today.", "No dog today.", "Dog's off today.", "No bark today.", "No Dog of the Day.",
        "Dog of the Day's [sitting|staying] home today.", "[Zero|No] dogs today.", "The dog's [off|resting] today.",
        "No underdog [pick|play] today.", "Dog spot's empty today.", "We ain't got a dog today.",
    ),
    "dog_why": T(
        "No underdog's worth the risk.", "{Algo} checked every underdog and none of them earned it.",
        "Every dog on the board is priced right.", "No dog with a real edge on the slate.",
        "The underdogs are priced tight.", "Not one dog has a proven angle today.",
        "The dogs today ain't worth our money.", "Nothing plus money cleared the bar.",
        "{Algo} couldn't find a dog it trusts.", "The underdogs are priced about right — no edge.",
        "No plus-money spot where our numbers [beat|top] the price.",
    ),
}
NOTE_CAP = {"short": (129, 3), "lean": (246, 5), "dog": (129, 3)}


def _part(key, seed, n=30, lean=False, **kw):
    return roll(NOTES[key], seed, (400, 2), n, False, LEAN_BAN if lean else None, **kw)


def _note(parts, cap):
    """The first combination of the parts (in seed order) that fits the cap."""
    for i in range(30):
        x = " ".join(p[(i * (j + 1)) % len(p)] for j, p in enumerate(parts))
        c, s = _size(x)
        if c <= cap[0] and s <= cap[1]:
            return x
    return " ".join(p[0] for p in parts)


def short_note(n, seed):
    """The top note on a short board of n plays (1-4)."""
    s = f"short{seed}{n}"
    first = _part("short1", s) if n == 1 else _part("shortn", s, cnt=n)
    it = "that one" if n == 1 else "those"
    return _note([first, _part("short_why", s + "w", it=it), _part("close", s + "c")],     # (cap: names count as one)
                 (NOTE_CAP["short"][0] + len(it) - 1 + len(str(n)) - 1, NOTE_CAP["short"][1]))


def dog_note(seed, _fresh=True):
    """The note where the Dog of the Day would go, on a day with no dog worth it. Never a sentence from yesterday's."""
    s = f"dog{seed}"
    parts = [_part("dog_open", s), _part("dog_why", s + "w"), _part("close", s + "c")]
    avoid = set()
    if _fresh:
        try:                                              # yesterday's note (seed = the date)
            from datetime import date, timedelta
            y = (date.fromisoformat(str(seed)[:10]) - timedelta(days=1)).isoformat()
            avoid = {x.strip() for x in re.split(r"(?<=[.!?])\s+", dog_note(y, _fresh=False))}
        except ValueError:
            pass
    parts = [[x for x in p if x.strip() not in avoid] or p for p in parts]
    return _note(parts, NOTE_CAP["dog"])


def lean_note(seed):
    """The top note on a leans-only day: no locks / no value, just which way the algorithm leans (no hype)."""
    s = f"lean{seed}"
    return _note([_part("lean_open", s, lean=True), _part("lean_why", s + "w", lean=True),
                  _part("close", s + "c", lean=True), _part("lean_tail", s + "t", lean=True)], NOTE_CAP["lean"])


# ---- how much we can say ---------------------------------------------------------------------------------------------
def supply():
    """How many different lines each mixer can make (before the size caps)."""
    out = {"good": _supply(GOOD), "bad": _supply(BAD)}
    for (k, r), (_, _, t) in REVIEWS.items():
        out[f"review {k} {r}"] = _supply(t)
    for k, (_, _, t) in LINES.items():
        out[k] = _supply(t)
    return out


def note_supply():
    s = {k: _supply(v) for k, v in NOTES.items()}
    return {"short one": s["short1"] * s["short_why"] * s["close"], "short n": s["shortn"] * s["short_why"] * s["close"],
            "leans": s["lean_open"] * s["lean_why"] * s["close"] * s["lean_tail"]}


def caps():
    """{key: (chars, sentences)} - the longest each line may be (the old longest version of it)."""
    out = {f"review {k} {r}": (c, s) for (k, r), (c, s, _) in REVIEWS.items()}
    out.update({k: cap for k, (cap, _, _) in LINES.items()})
    out.update(good=(64, 3), bad=(63, 2))
    return out


if __name__ == "__main__":
    for k, v in sorted(supply().items()):
        print(f"{k:24} {v:,}")
    for x in good("Skenes", "the Cubs", "demo", n=6):
        print(" ", x)
