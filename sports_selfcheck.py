"""END-OF-DAY SELF-CHECK: every pick we posted, graded against the chance we said it had.

Every graded leg (posted cards in data/sports/picks.json plus the live plus-money bets in data/sports/live_log.json)
is put in groups: by sport, by market (moneyline / spread / total), by price range, by label (lock, value, dog,
parlay leg, live), by drama (the other side has drama / our side has drama / none) and live vs pregame. For each
group: how many, the chance we said on average, how often it really hit.

The same rule the live feature uses on itself (sports_live.self_tune): a group only changes anything once it has
40+ graded legs. If it's hitting 8+ points below what we said, new picks in that group need extra edge (+1 point
of edge per 4 points it's short, at most +4). When it's hitting at or above what we said, the extra eases back
toward zero a point at a time. Under 40 legs it's reported, never acted on. Saved to data/sports/selfcheck.json.

Forward-only tags are graded too, REPORT ONLY (they never raise the bar): the context facts around the game
(ctx:us:<flag> / ctx:them:<flag> / ctx:game:<flag>, from sports_context) and the pregame talk from the news
(talk:ours:<kind> / talk:theirs:<kind>, from sports_news TALK_KINDS)."""
import json
import os
from datetime import datetime, timezone

import sports_data as sd

PATH = os.path.join(sd.DATA, "selfcheck.json")
PICKS = os.path.join(sd.DATA, "picks.json")
LIVE = os.path.join(sd.DATA, "live_log.json")
MIN_N = 40              # graded legs before a group can change anything
SHORT = 0.08            # hitting this far below what we said = raise the bar
STEP_PTS = 0.04         # +0.01 extra edge per 4 points short...
STEP = 0.01
CAP = 0.04              # ...at most +0.04
LABELS = {"lock": "lock", "dog": "dog", "solo": "value"}          # anything else on a card is a parlay leg


def price(odds):
    """The price range an American price falls in."""
    try:
        o = int(float(odds))
    except (TypeError, ValueError):
        return None
    if o <= -150:
        return "<= -150"
    if -149 <= o <= -101:
        return "-149..-101"
    if -100 <= o <= 100:
        return "pick'em"
    if o <= 179:
        return "+101..+179"
    return "+180+"


def drama(leg):
    out = []
    if leg.get("our_drama"):
        out.append("ours")
    if leg.get("their_drama"):
        out.append("theirs")
    return out or ["none"]


def keys(leg, label=None, live=False):
    """Every group a leg (or a candidate) belongs to."""
    out = ["all"]
    if leg.get("league"):
        out.append(f"league:{leg['league']}")
    if leg.get("market"):
        out.append(f"market:{leg['market']}")
    pr = price(leg.get("odds"))
    if pr:
        out.append(f"price:{pr}")
    if label:
        out.append(f"label:{label}")
    out += [f"drama:{d}" for d in drama(leg)]
    out.append("source:live" if live else "source:pregame")
    # report-only groups (graded, never acted on): the context facts around the game and the pregame talk
    out += [f"ctx:{t}" for t in leg.get("ctx_tags") or []]
    out += [f"talk:ours:{t['kind']}" for t in leg.get("talk_ours") or []]
    out += [f"talk:theirs:{t['kind']}" for t in leg.get("talk_theirs") or []]
    return out


REPORT_ONLY = ("ctx:", "talk:")      # forward-only tags: graded for the record, they never raise the bar


def legs(cards, live):
    """[(group keys, said, hit)] for every graded pick with a said chance (pushes and ungraded skipped)."""
    out = []
    for c in cards or []:
        label = LABELS.get(c.get("kind"), "parlay leg")
        for leg in c.get("legs") or []:
            if leg.get("result") in ("won", "lost") and leg.get("p"):
                out.append((keys(leg, label), float(leg["p"]), leg["result"] == "won"))
    for e in ((live or {}).get("plays") or {}).values():
        if e.get("result") in ("won", "lost") and e.get("p"):
            out.append((keys({**e, "market": "ml"}, "live", live=True), float(e["p"]), e["result"] == "won"))
    return out


def verdict(n, said, hit):
    if n < MIN_N:
        return f"only {n} graded - report only"
    if hit < said - SHORT:
        return "hitting well below what we said - bar raised"
    if hit >= said:
        return "hitting at or above what we said"
    return "a little below what we said - within noise"


def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def study(cards=None, live=None, path=PATH):
    cards = _load(PICKS, []) if cards is None else cards
    live = _load(LIVE, {}) if live is None else live
    prev = _load(path, {}).get("extra_edge") or {}
    by = {}
    for ks, p, y in legs(cards, live):
        for k in ks:
            by.setdefault(k, []).append((p, y))
    groups, extra = {}, {}
    for k, rs in sorted(by.items()):
        n = len(rs)
        said = sum(p for p, _ in rs) / n
        hit = sum(y for _, y in rs) / n
        e = prev.get(k, 0.0)
        if k.startswith(REPORT_ONLY):                 # forward-only tags: graded for the record only
            e = 0.0
            groups[k] = {"n": n, "said": round(said, 3), "hit": round(hit, 3), "extra_edge": 0.0,
                         "verdict": verdict(n, said, hit).replace(" - bar raised", "") + " (report only: forward-only tag)"}
            continue
        if n >= MIN_N:
            short = said - hit
            if short >= SHORT:
                e = min(CAP, STEP * int(short / STEP_PTS + 1e-9))
            elif hit >= said:
                e = max(0.0, e - STEP)
        if e > 0:
            extra[k] = round(e, 3)
        groups[k] = {"n": n, "said": round(said, 3), "hit": round(hit, 3), "verdict": verdict(n, said, hit),
                     "extra_edge": round(e, 3)}
    for k, e in prev.items():                     # a group with no graded legs now keeps what it had
        if k not in groups and e > 0:
            extra[k] = e
    no_p = sum(1 for e in ((live or {}).get("plays") or {}).values() if e.get("result") in ("won", "lost") and not e.get("p"))
    res = {"groups": groups, "extra_edge": extra, "live_without_p": no_p, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    with open(path + ".tmp", "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return res


def load():
    return _load(PATH, {})


def extra_edge(st, cand):
    """The extra edge a candidate needs: the most any group it belongs to asks for (0 if none)."""
    ex = (st or {}).get("extra_edge") or {}
    if not ex:
        return 0.0
    label = cand.get("label") or (LABELS.get(cand.get("kind"), "parlay leg") if cand.get("kind") else None)
    return max([ex.get(k, 0.0) for k in keys(cand, label, live=bool(cand.get("live")))] + [0.0])


def summary(st):
    g = (st or {}).get("groups") or {}
    a = g.get("all")
    if not a:
        return ["self-check: nothing graded yet"]
    lines = [f"self-check: {a['n']} graded picks - we said {a['said']:.0%}, they hit {a['hit']:.0%} ({a['verdict']})"]
    for k, v in sorted(g.items(), key=lambda kv: -kv[1]["n"]):
        if k != "all":
            lines.append(f"  {k}: {v['n']} graded, said {v['said']:.0%}, hit {v['hit']:.0%} - {v['verdict']}")
    if st.get("live_without_p"):
        lines.append(f"  ({st['live_without_p']} graded live bets were logged without a said chance - left out)")
    ex = (st or {}).get("extra_edge") or {}
    lines.append("extra edge now needed: " + (", ".join(f"{k} +{v:.0%}" for k, v in sorted(ex.items())) or "none"))
    return lines


if __name__ == "__main__":
    for x in summary(study()):
        print(x)
