#!/bin/bash
# 11/17 UNDERDOG EDGE STUDY - R3: the replay board on today's code, every moneyline row with the dog score's parts, four
# chunks at once (rows -> ~/.cache/d503_dogs1117/rows, never the repo). A chunk killed for memory resumes from its last
# whole day. Usage: bash results/studies/dogs_1117/run_funnel6.sh
OUT=$HOME/.cache/d503_dogs1117/rows
mkdir -p $OUT
cd "$(dirname "$0")/../../.."
chunk() {   # name start end
  local n=$1 s=$2 e=$3 part=0
  while true; do
    python3 results/studies/dogs_1117/funnel6.py $s $e $OUT/f${n}${part}.jsonl >> $OUT/f${n}.log 2>&1 && break
    s=$(python3 results/studies/football_1114/resume.py $OUT/f${n}${part}.jsonl $s)
    part=$((part + 1))
    echo "resume $n from $s" >> $OUT/f${n}.log
    sleep 20
  done
}
chunk A 2023-10-01 2024-07-05 &
chunk B 2024-07-06 2025-04-10 &
chunk C 2025-04-11 2026-01-15 &
chunk D 2026-01-16 2026-11-15 &
wait
echo done > $OUT/DONE
