#!/bin/bash
# 11/12 DAILY - football's money check: both arms of the football-day replay, four chunks at a time (rows go to
# ~/.cache/d503_daily1112, never the repo). Usage: bash results/studies/daily_1112/run_funnel3.sh new|old
ARM=$1
OUT=$HOME/.cache/d503_daily1112/$ARM
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
ARM=$ARM python3 results/studies/daily_1112/funnel3.py 2023-10-01 2024-07-05 $OUT/fA.jsonl > $OUT/fA.log 2>&1 &
ARM=$ARM python3 results/studies/daily_1112/funnel3.py 2024-07-06 2025-04-10 $OUT/fB.jsonl > $OUT/fB.log 2>&1 &
ARM=$ARM python3 results/studies/daily_1112/funnel3.py 2025-04-11 2026-01-15 $OUT/fC.jsonl > $OUT/fC.log 2>&1 &
ARM=$ARM python3 results/studies/daily_1112/funnel3.py 2026-01-16 2026-11-10 $OUT/fD.jsonl > $OUT/fD.log 2>&1 &
wait
echo done > $OUT/DONE
