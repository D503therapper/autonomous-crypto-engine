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
    "beat the brakes off": "a mismatch we see coming ('the Bears are about to beat the brakes off the Eagles')",
    "smack that ass": "a blowout we see coming",
    "smacked": "a WIN - our bet smacked ('+200 moneyline, we smacked'), or our team smacked (9/30); also the other "
               "side getting beat bad",
    "fought hard": "the loser battled but still lost (the review)",
    "got cooked": "whoever LOST got cooked - our side on a miss ('Blockx got cooked'); never 'Cook.' after a win (9/29)",
    "shit the bed": "our side blew it (a loss review)",
    "complete ass": "the other side's been terrible",
    "washed": "an old, out-of-his-prime player who's cold now ('Aaron Rodgers is washed', 10/1) - only a long-time "
              "starter (sports_breakdown_v24.VET_STARTS) with his bad numbers right there",
    "booty cheeks": "the other side's been terrible",
    "rocking with the sharps": "now and then when the price moved our way - never every card (we're our own engine)",
    "like they stole something": "a blowout win's review (the owner loved it, 9/29 - keep it)",
    "somebody give this man his flowers": "one of OUR players went off in a win ('Trevor Lawrence went crazy. Somebody "
                                           "give this man his flowers. Cash it, baby.') - always HIS flowers (9/30)",
    "cash it, baby": "right after the flowers line, on a win",
    # taking the shot (the owner, 10/1 - "the motto")
    "scared money don't make no money": "a dog / plus-money WIN - we took the shot and it paid",
    "you can't win if you don't play": "a dog LOSS - we took the shot, no regrets (never a lean)",
    "no risk, no reward": "a dog / plus-money WIN (the owner, 10/1 - 'big risk, big reward')",
    # the crew
    "the homies": "the people on the board with us",
}

# words he's said NOT to use (the dashboard never says these)
SHOW_PCT_OVER = 100   # the owner, 10/7: "we don't need to see win percentages ever" (was 55 - 9/30); a pick's win
#                       chance is always said in words. Records (W-L · %) are records, not win %s - they stay.

NEVER = ("real talk", "chalk", "guaranteed", "broken clock", "circled on both calendars", "leaky",
         "class of this", "give him flowers", "give this man flowers", "give her flowers", "only one that counts", "only this one matters", "what counts", "clean slate tonight")   # (10/1: "that don't make no sense")   # (9/30: it's always
#                                                                        "somebody give this man HIS flowers")   # (9/29: "class of the match" - he's never heard it said)

# where the write-ups live (what the test searches)
SOURCES = ("sports_lingo.py", "sports_breakdown_v24.py", "sports_tennis.py", "sports_dashboard.py",
           "sports_decider.py")
