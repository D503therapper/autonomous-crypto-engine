"""Run replay.py for whole college hoops seasons (Nov 1 - Apr 10), one after another in one process:
  python run_seasons.py 2018 2019      -> rows_2018.jsonl, rows_2019.jsonl (next to this file)"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

for y in sys.argv[1:]:
    y = int(y)
    replay.main(f"{y}-11-01", f"{y + 1}-04-10", os.path.join(HERE, f"rows_{y}.jsonl"))
