#!/bin/bash
# 11/12 DEEP PROGRAM: the OLD arm of the funnel replay on the held-out stretch only (2025-04-11 -> 2026-11-10: chunks C
# and D) - the A/B for the calibration fixes. Chunk D starts now; chunk C waits for the new arm to finish (memory).
OUT=$HOME/.cache/d503_deep1112/funnel_old
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
ARM=old python3 results/studies/deep_1112/funnel2.py 2026-01-16 2026-11-10 $OUT/fD.jsonl > $OUT/fD.log 2>&1 &
until [ -f $HOME/.cache/d503_deep1112/funnel_new/DONE ]; do sleep 20; done
ARM=old python3 results/studies/deep_1112/funnel2.py 2025-04-11 2026-01-15 $OUT/fC.jsonl > $OUT/fC.log 2>&1 &
wait
echo done > $OUT/DONE
