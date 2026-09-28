"""stdin -> stdout and appended to a file, reopening the file for every line (unlike `tee -a`), so the log keeps
growing after `git pull --rebase` replaces the file on disk.   cmd 2>&1 | python3 -u tools/append_log.py data/run.log"""
import sys

path = sys.argv[1]
for line in sys.stdin:
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(path, "a") as f:
        f.write(line)
