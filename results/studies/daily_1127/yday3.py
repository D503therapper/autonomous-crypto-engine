"""11/27 daily studies - why the card check called the Chiefs card's line under the pick "weak" (the 11/26 pick audit).
python results/studies/daily_1127/yday3.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_card_check as cc  # noqa: E402

LINE = "🧤 Chiefs gave it away 7 times in 10 games this year. Bills: 16 in 10. Riding Chiefs."


def main():
    leg = [r for r in json.load(open("data/sports/picks.json")) if r.get("date") == "2026-11-26"][0]["legs"][0]
    print("weak_lead:", repr(cc.weak_lead(LINE, leg)))
    print("PRICE_MATH:", cc.PRICE_MATH.search(LINE))
    print("close_result:", cc.close_result(LINE, leg))
    print("UP_BY_ONE:", cc.UP_BY_ONE.search(LINE))
    for name in ("filler", "knocks_us", "strong_line"):
        try:
            print(name, repr(getattr(cc, name)(LINE, leg)))
        except Exception as e:  # noqa: BLE001
            print(name, "error", e)
    a = json.load(open("data/sports/pick_audit.json"))["2026-11-26"]
    print(json.dumps(a, indent=1, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
