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


if __name__ == "__main__":
    for f in (test_watchdog_fires_when_loop_stalls, test_watchdog_quiet_while_ticking, test_hung_git_is_bounded,
              test_git_unjam_clears_stale_lock_and_rebase):
        f()
        print("ok", f.__name__)
