#!/bin/bash
# 11/12 DEEP PROGRAM: both arms of the funnel replay, four chunks at a time (never the repo: rows go to ~/.cache).
# Usage: bash results/studies/deep_1112/run_funnel.sh new|old
ARM=$1
OUT=$HOME/.cache/d503_deep1112/funnel_$ARM
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
ARM=$ARM python3 results/studies/deep_1112/funnel2.py 2023-10-01 2024-07-05 $OUT/fA.jsonl > $OUT/fA.log 2>&1 &
ARM=$ARM python3 results/studies/deep_1112/funnel2.py 2024-07-06 2025-04-10 $OUT/fB.jsonl > $OUT/fB.log 2>&1 &
ARM=$ARM python3 results/studies/deep_1112/funnel2.py 2025-04-11 2026-01-15 $OUT/fC.jsonl > $OUT/fC.log 2>&1 &
ARM=$ARM python3 results/studies/deep_1112/funnel2.py 2026-01-16 2026-11-10 $OUT/fD.jsonl > $OUT/fD.log 2>&1 &
wait
echo done > $OUT/DONE
