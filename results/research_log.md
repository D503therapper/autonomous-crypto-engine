# Research log

Daily deep-study notes. Newest first. Open questions at the top get studied next.

## Open questions

### Runner exits (asked by the owner 2026-09-26)
Goal: never lose a big gain, and never sell a coin that is on its way to 100x. These pull in
opposite directions, so settle it with data (listings_study.py histories, plus dex_exit_study for DEX):

1. **Break-even floor.** Once a coin is up 50% (config.MOON "ride"), never sell below entry.
   Does it beat the current rule (50% trail from the high only)?
2. **Wider trail for the biggest winners.** For example 50% until 5x, then 60% (a 100x coin often
   has 50-70% pullbacks on the way up). Does it catch more of the giant runs without losing more elsewhere?
3. Score each option on: average profit per trade, the share of the top-3 trades we captured,
   and how many runners that went on to 10x+ were sold before 3x.

Switch config.MOON or EARLY_MOVER only if the walk-forward (unseen months) result is better.
Report the answer to the owner in plain words.
