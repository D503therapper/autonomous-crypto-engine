#!/bin/sh
# Re-make every report from the cached runs (python run_full.py final '{}' ; python run_full.py final_lag2 '{"lag": 2}').
cd "$(dirname "$0")" || exit 1
C="${STUDY_CACHE:-$HOME/.cache/d503_studies}"
python3 analyze.py "$C/deep_final.pkl" final a_final_out.txt > /dev/null &
python3 hunt.py "$C/deep_final.pkl" hunt_final_out.txt > /dev/null &
python3 open_clv.py "$C/deep_final_lag2.pkl" open_clv_lag2_out.txt > /dev/null &
python3 open_anchor.py "$C/deep_final_lag2.pkl" open_anchor_lag2_out.txt > /dev/null &
wait
