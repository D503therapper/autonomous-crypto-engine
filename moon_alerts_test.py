"""Moon alerts: one phone alert per coin per step (2x, 3x, 5x ...).   python moon_alerts_test.py"""
import run_live


def test_steps_fire_once():
    sent = []
    pos = {"A": {"sym": "BABYCALI", "chain": "solana", "addr": "5Xtx", "entry": 1.0, "px": 1.5, "qty": 100}}
    send = lambda t, m, p: sent.append(t)
    run_live.moon_alerts(pos, send)
    assert sent == []                                            # +50%: nothing yet
    pos["A"]["px"] = 3.4
    run_live.moon_alerts(pos, send)
    assert len(sent) == 1 and "3.4x" in sent[0] and pos["A"]["moon"] == 3
    run_live.moon_alerts(pos, send)
    assert len(sent) == 1                                        # same step: no repeat
    pos["A"]["px"] = 2.5
    run_live.moon_alerts(pos, send)
    assert len(sent) == 1                                        # dipped back: no new alert
    pos["A"]["px"] = 11
    run_live.moon_alerts(pos, send)
    assert len(sent) == 2 and pos["A"]["moon"] == 10
    pos["A"]["px"] = 0
    run_live.moon_alerts(pos, send)                              # bad price: ignored
    assert len(sent) == 2



def test_emoji_title_is_header_safe():
    # 2026-09-30: the AIRPAD 2x alert never reached the phone - an emoji title isn't latin-1
    import base64
    h = run_live._header("\U0001f680 AIRPAD is up 2.1x")
    h.encode("latin-1")
    assert base64.b64decode(h[10:-2]).decode() == "\U0001f680 AIRPAD is up 2.1x"
    assert run_live._header("plain") == "plain"


if __name__ == "__main__":
    test_steps_fire_once()
    print("ok test_steps_fire_once")
    test_emoji_title_is_header_safe()
    print("ok test_emoji_title_is_header_safe")
