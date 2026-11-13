#!/bin/bash
# 11/13 FABLE - the college hoops lean replay on today's code: one chunk a season, four at a time (rows go to
# ~/.cache/d503_leans1113/rows, never the repo). Usage: bash results/studies/leans_1113/run_funnel4.sh
OUT=$HOME/.cache/d503_leans1113/rows
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
for Y in 2018 2019 2020 2021 2022 2023 2024 2025 2026; do
  echo "$Y-11-01 $((Y + 1))-04-10 $OUT/s$Y.jsonl $OUT/s$Y.log"
done | xargs -P 4 -L 1 sh -c 'python3 results/studies/leans_1113/funnel4.py $0 $1 $2 > $3 2>&1'
echo done > $OUT/DONE
