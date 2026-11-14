#!/bin/bash
# 11/14 COLLEGE HOOPS PROFIT STUDIES - the replay on today's code: one chunk a season, two at a time (a neighbour job shares the memory) (rows go to
# ~/.cache/d503_cbb1114/rows, never the repo). Usage: bash results/studies/leans_1113/run_funnel4.sh
OUT=$HOME/.cache/d503_cbb1114/rows
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
for Y in 2026 2023 2018 2024 2019 2025 2020 2021 2022; do
  echo "$Y-11-01 $((Y + 1))-04-10 $OUT/s$Y.jsonl $OUT/s$Y.log"
done | xargs -P 2 -L 1 sh -c 'python3 results/studies/cbb_profit_1114/funnel5.py $0 $1 $2 > $3 2>&1'
echo done > $OUT/DONE
