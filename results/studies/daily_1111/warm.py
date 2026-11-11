"""Warm the scratch caches (finals / all finals / box rows) for the given leagues - nothing written to the repo."""
import sys

import lib

for lg in sys.argv[1:]:
    lib.finals(lg)
    lib.all_finals(lg)
    if lg != "ncaab":
        lib.box_rows(lg)
    print(lg, "ok", flush=True)
