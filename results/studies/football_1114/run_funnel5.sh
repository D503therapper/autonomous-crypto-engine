#!/bin/bash
# 11/14 FOOTBALL PROFIT STUDIES - the football replay board on today's code, four chunks at once (rows go to
# ~/.cache/d503_fb1114/rows, never the repo; the tuned params to ~/.cache/d503_fb1114/params - a FRESH dir: another
# study's cached params were tuned on other dials). A chunk killed for memory resumes from its last whole day.
# Usage: bash results/studies/football_1114/run_funnel5.sh
OUT=$HOME/.cache/d503_fb1114/rows
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
chunk() {   # name start end
  local n=$1 s=$2 e=$3 part=0
  while true; do
    python3 results/studies/football_1114/funnel5.py $s $e $OUT/f${n}${part}.jsonl >> $OUT/f${n}.log 2>&1 && break
    s=$(python3 results/studies/football_1114/resume.py $OUT/f${n}${part}.jsonl $s)
    part=$((part + 1))
    echo "resume $n from $s" >> $OUT/f${n}.log
    sleep 20
  done
}
chunk A 2018-08-20 2020-07-31 &
chunk B 2020-08-01 2022-07-31 &
chunk C 2022-08-01 2024-07-31 &
chunk D 2024-08-01 2026-11-13 &
wait
echo done > $OUT/DONE
