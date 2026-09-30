# D503 Sports Engine: the owner's standing rules

A picks-only sports dashboard (GitHub Pages) for the owner and his friends. These rules come from the owner and hold in
every session:

- **Picks only. Never change a posted pick** without the owner's explicit OK.
- **Everything in his lingo** (`sports_owner_lingo.py`). Never repetitive across the board or day to day, never robotic,
  no marketing tone. Plain words ("goalie", not "G"), no confusing sayings. Never "real talk" or "chalk" (see `NEVER`).
- **When the owner uses new slang in chat, add it to `sports_owner_lingo.py` and into the write-up pools where it fits.**
  Use it the way he does ("that's just facts" after a claim, never after a number).
- **Never lengthen write-ups.** Accuracy over everything. No secrets in the repo. No borrowed keys or disguises to get
  past a site's blocks.
- Leans count in the record from 9/29. Live plus money and tennis keep their own records. The -150 rule stays.
- The main board and tennis post at 8 AM PT on game day. iPhone and Android look the same.
- Fix bugs so they don't come back: every fix gets a regression test in `sports_test.py`
  (`timeout 900 python sports_test.py`, all green before any push).
- Once the owner OKs something, publish it without asking again. Show a preview for new visual changes.
- Commit to main and to the `claude/...` branch; don't open a PR unless asked.
