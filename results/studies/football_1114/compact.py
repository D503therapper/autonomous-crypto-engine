"""Compact view of a lib.fmt table: ALL | TRAIN (seasons up) | HELD (held seasons up). Usage: python compact.py out.txt"""
import re
import sys

for ln in open(sys.argv[1]):
    ln = ln.rstrip()
    m = re.match(r'(.{58}) ALL (.*?)\| TRAIN (.*?) up (\S+) \|(.*)\| HELD (.*)$', ln)
    if m:
        seas = re.findall(r'(20\d\d)\s+(\d+)\s+([+-][\d.]+)%', m.group(5))
        up = sum(1 for s in seas if float(s[2]) > 0)
        print(f"{m.group(1).strip()[:56]:56s} ALL {m.group(2).strip()} | TR {m.group(3).strip()} up {m.group(4)} | HELD {m.group(6).strip()} up {up}/{len(seas)}")
    else:
        print(ln[:250])
