#!/bin/bash
# the exam walk-forward rows, one league at a time (memory)
cd "$(dirname "$0")/../../.."
for lg in nfl nba nhl ncaab mlb; do python results/studies/sizing_1115/e1_exam_rows.py $lg 2019 > ~/.cache/d503_sizing1115/e1_$lg.log 2>&1; done
