"""11/20 - EARLY PLAYS, the hammered spot against its own study: WHEN does the live play fire, and off WHICH number?
The study's cell (early_1111 s3 / s6d, the paid history): a dog whose no-vig price came 4+ points to it between the
first FAIR look (Tuesday) and a look two days later. The live spot (sports_early.spot_scan): 4+ points since
first_fair() - the first row our line tape holds at or after the fair moment (the tape keeps a row only when a price
changes). This prints, for every live hammered play, the tape around the fair moment: the last number BEFORE it (the
look-ahead number hung before the teams' last games), the first row after it (the spot's baseline), and the number we
posted on - so the move the spot calls "money" can be split into the book's own re-hang and what came after.
Reads data/sports/early.json + data/sports/line_history (nothing fetched).
Usage: python3 results/studies/early_thin_1120/e1_hammered_tape.py > results/studies/early_thin_1120/e1_hammered_tape.out"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
import sports_data as sd  # noqa: E402


def imp(o):
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def nv(mine, other):
    return 100 * imp(mine) / (imp(mine) + imp(other))


tape = {}
for fn in sorted(f for f in os.listdir(sd.LINE_HIST_DIR) if f.endswith(".jsonl")):
    for x in open(os.path.join(sd.LINE_HIST_DIR, fn)):
        try:
            r = json.loads(x)
        except ValueError:
            continue
        tape.setdefault(r.get("g"), []).append(r)
for v in tape.values():
    v.sort(key=lambda r: r.get("t", ""))

st = json.load(open(os.path.join(sd.DATA, "early.json")))
rows = [(p, "") for p in st["picks"]] + [(p, " (pulled)") for p in st.get("pulled") or []]
tot = []
for p, tag in rows:
    if "hammered" not in (p.get("spots") or [p.get("spot")]):
        continue
    side = p["side"]
    me, ot = ("h", "a") if side == "home" else ("a", "h")
    fair, post = p.get("fair_at"), p.get("posted")
    tp = [r for r in tape.get(p["game_id"], []) if isinstance(r.get(me), (int, float, str)) and r.get(me) not in (None, "") and r.get(ot) not in (None, "")]
    try:
        tp = [(r["t"], int(float(r[me])), int(float(r[ot]))) for r in tp]
    except (TypeError, ValueError):
        tp = []
    before = [x for x in tp if fair and x[0] < fair]
    after = [x for x in tp if fair and fair <= x[0] <= post]
    print(f"{p.get('team')} {p['odds']:+d} [{p.get('spot')}]{tag} - fair {fair}, posted {post}, {p.get('result') or 'open'}")
    if not fair or not tp:
        print("   no tape")
        continue
    stale = before[-1] if before else None
    base = after[0] if after else None
    now_nv = nv(p["odds"], p["opp_odds"]) if p.get("opp_odds") else None
    if stale:
        print(f"   the number BEFORE the fair moment (look-ahead): {stale[1]:+d} at {stale[0]} = {nv(stale[1], stale[2]):.1f}%")
    for x in after[:6]:
        print(f"   tape {x[0]}: {x[1]:+d} = {nv(x[1], x[2]):.1f}%")
    if base and now_nv is not None:
        b = nv(base[1], base[2])
        s = nv(stale[1], stale[2]) if stale else None
        hrs = (sd.parse_t(post) - sd.parse_t(base[0])).total_seconds() / 3600 if hasattr(sd, "parse_t") else None
        print(f"   the spot's baseline {base[1]:+d} ({b:.1f}%) -> posted {p['odds']:+d} ({now_nv:.1f}%): {now_nv - b:+.1f} pts"
              + (f"; the look-ahead number was {s:.1f}% - the baseline sat {b - s:+.1f} from it" if s is not None else ""))
        tot.append((p.get("team"), base[0], post, now_nv - b, (b - s) if s is not None else None, len(after)))
print()
for t in tot:
    print(t)
