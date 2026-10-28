"""Regression tests (2026-10-01): the engine froze at 08:06 UTC with no output; git calls had no time limit and
nothing restarted a hung loop."""
import time

import run_live


def test_watchdog_fires_when_loop_stalls():
    fired = []
    run_live._tick[0] = time.time() - 10
    t = run_live.watchdog(limit=5, exit_fn=lambda: fired.append(1), every=0.05)
    t.join(timeout=2)
    assert fired == [1]


def test_watchdog_quiet_while_ticking():
    fired = []
    run_live._tick[0] = time.time()
    run_live.watchdog(limit=5, exit_fn=lambda: fired.append(1), every=0.05)
    time.sleep(0.3)
    assert not fired


def test_hung_git_is_bounded():
    old = run_live.GIT_TIMEOUT
    run_live.GIT_TIMEOUT = 1
    try:
        t0 = time.time()
        assert run_live.sh("sleep 5") == 124 and time.time() - t0 < 3
        assert run_live.sh("true") == 0
    finally:
        run_live.GIT_TIMEOUT = old


def test_git_unjam_clears_stale_lock_and_rebase():
    # 13:06 2026-10-01: no hourly save after a time-limited git was killed mid-pull (lock + rebase left behind)
    import os, subprocess, tempfile
    d = tempfile.mkdtemp()
    cwd = os.getcwd()
    try:
        os.chdir(d)
        subprocess.run("git init -q && git -c user.name=t -c user.email=t@t commit -q --allow-empty -m x", shell=True, check=True)
        open(".git/index.lock", "w").close()
        os.utime(".git/index.lock", (time.time() - 600, time.time() - 600))
        os.makedirs(".git/rebase-merge")
        open("f", "w").write("1")
        assert subprocess.run("git add f", shell=True, stderr=subprocess.DEVNULL).returncode != 0   # jammed
        run_live.git_unjam()
        assert not os.path.exists(".git/index.lock") and not os.path.isdir(".git/rebase-merge")
        assert subprocess.run("git add f", shell=True).returncode == 0
        open(".git/index.lock", "w").close()                       # a fresh lock (a git still running) stays
        run_live.git_unjam()
        assert os.path.exists(".git/index.lock")
    finally:
        os.chdir(cwd)


def test_flush_log_copies_only_new_lines():
    # 13:06 2026-10-01: a tracked run.log written every second broke the hourly pull; the live log is untracked now
    import os, tempfile
    d = tempfile.mkdtemp()
    live, out, off = (os.path.join(d, n) for n in ("live", "out", "off"))
    open(out, "w").write("old\n")
    open(live, "w").write("a\nb\n")
    run_live.flush_log(live, out, off)
    open(live, "a").write("c\n")
    run_live.flush_log(live, out, off)
    run_live.flush_log(live, out, off)                      # nothing new: nothing added
    assert open(out).read() == "old\na\nb\nc\n"
    open(live, "w").write("x\n")                            # a new run's fresh live log
    run_live.flush_log(live, out, off)
    assert open(out).read().endswith("c\nx\n")


def test_force_sync_publishes_our_paths_without_a_merge():
    # 10-28 15:22-21:13: every hourly pull --rebase failed for six hours; the fallback publishes our changed paths
    # on top of the remote branch with plumbing (no merge), our version on our paths, theirs everywhere else
    import os, subprocess, tempfile
    r = tempfile.mkdtemp()
    cwd = os.getcwd()

    def sh(c, d):
        subprocess.run(c, shell=True, check=True, cwd=d, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def put(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(data)
    try:
        sh("git init -q --bare -b main remote.git && git clone -q remote.git a", r)
        a, b = os.path.join(r, "a"), os.path.join(r, "b")
        sh("git config user.email t@t && git config user.name t", a)
        for p, v in (("data/dex/eq.csv", b"1\n"), ("data/blob.bin", b"\x00\x01"), ("data/sports/s.json", b"{}"),
                     ("data/gone.txt", b"x")):
            put(os.path.join(a, p), v)
        sh("git add -A && git commit -qm init && git push -q origin main && cd .. && git clone -q remote.git b", a)
        sh("git config user.email t@t && git config user.name t", b)
        put(os.path.join(b, "data/blob.bin"), b"\x00\x02")                # another session pushes first
        put(os.path.join(b, "data/sports/s.json"), b'{"a":1}')
        sh("git commit -qam other && git push -q origin main", b)
        put(os.path.join(a, "data/blob.bin"), b"\x00\x03")                # the engine's unpushed hour
        put(os.path.join(a, "data/dex/eq.csv"), b"1\n2\n")
        os.remove(os.path.join(a, "data/gone.txt"))
        sh("git add -A && git commit -qm engine", a)
        os.chdir(a)
        assert run_live.force_sync()
        sh("git fetch -q && git reset -q --hard origin/main", b)
        rd = lambda p: open(os.path.join(b, p), "rb").read()
        assert rd("data/dex/eq.csv") == b"1\n2\n" and rd("data/blob.bin") == b"\x00\x03"   # ours on our paths
        assert rd("data/sports/s.json") == b'{"a":1}'                                     # theirs elsewhere
        assert not os.path.exists(os.path.join(b, "data/gone.txt"))
        head = subprocess.run("git rev-parse HEAD origin/main", shell=True, capture_output=True, text=True).stdout.split()
        assert head[0] == head[1]                                       # local branch now matches the remote
        assert run_live.force_sync()                                    # nothing left to publish
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    for f in (test_watchdog_fires_when_loop_stalls, test_watchdog_quiet_while_ticking, test_hung_git_is_bounded,
              test_git_unjam_clears_stale_lock_and_rebase, test_flush_log_copies_only_new_lines,
              test_force_sync_publishes_our_paths_without_a_merge):
        f()
        print("ok", f.__name__)
