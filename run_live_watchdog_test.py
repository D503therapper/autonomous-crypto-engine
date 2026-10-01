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


if __name__ == "__main__":
    for f in (test_watchdog_fires_when_loop_stalls, test_watchdog_quiet_while_ticking, test_hung_git_is_bounded):
        f()
        print("ok", f.__name__)
