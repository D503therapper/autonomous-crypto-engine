"""THE OWNER'S LINGO - how he actually talks, so the whole dashboard sounds like him (the owner, 9/29: "always remember
how I talk to you with my lingo and my slang and add it into the engine").

Every phrase here is one he's used himself. Each one must be live somewhere in the write-ups (sports_test checks), and
where it fits matters as much as the words: "facts" goes after a claim ("better team - that's just facts"), never
after a number; "cheeks clapped" is for a real beatdown, not a coin flip. New slang he uses in chat gets added here
AND into the pools where it fits (CLAUDE.md says so, so every session does it)."""

OWNER = {
    # hype on a pick
    "trust the algorithm": "our call, any card",
    "lock it in": "a lock's bottom line",
    "free money": "a lock (confident, never 'guaranteed')",
    "easy money": "a clean win / a lock",
    "tap in": "get on the pick",
    "we eating": "a pick we love",
    "let's eat": "a pick we love",
    "super value": "a lock at plus money",
    "that's just facts": "after a claim ('just the better team')",
    # the other side getting beat
    "cheeks clapped": "a beatdown (tennis straight sets, a blowout)",
    "smack that ass": "a blowout we see coming",
    "smacked": "the other side got beat bad",
    "fought hard": "the loser battled but still lost (the review)",
    "complete ass": "the other side's been terrible",
    "booty cheeks": "the other side's been terrible",
    # the crew
    "the homies": "the people on the board with us",
}

# words he's said NOT to use (the dashboard never says these)
NEVER = ("real talk", "chalk", "guaranteed", "broken clock", "circled on both calendars", "leaky")

# where the write-ups live (what the test searches)
SOURCES = ("sports_lingo.py", "sports_breakdown_v24.py", "sports_tennis.py", "sports_dashboard.py")
