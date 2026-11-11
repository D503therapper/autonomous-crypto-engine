"""S6b. AN NBA SPREAD STACK - the college hoops stack's idea carried to the NBA: every NBA edge that has held out of
sample here is an ATS FADE; none is a bet alone. Added up on one game (my side's fades against it, the other side's
for it), does the spread side clear -110?
The three fades, each found in its own study before this one: (1) LUCKY FROM THREE this season (own 3P% - the
opponents' 3P%, +2 points or more, 10+ games, 200+ attempts each way - 11/10: ATS -6.6% on 3,524); (2) THE FASTER
TEAM by 4+ possessions over the last 10 (11/3: -10.5% at the close); (3) THE FIRST HOME GAME after a 4+ game road trip
(S6 here: -10.3% on 776, both halves). Box scores 2016-26; TRAIN seasons to 2021, HELD 2022-26; the closing spread
at its own juice. Caveat said up front: each fade's direction was found on these same seasons.
   python s6b_nba_stack.py"""
from collections import defaultdict
import lib2 as L

o = L.Out("s6b")
B = L.B
FIN = [g for g in B.finals("nba") if g["sp"] is not None and g["stype"] == "2"]
ALL = B.all_finals("nba")
TL = B.team_log(ALL)
BOX = B.box_rows("nba")
SPLIT = 2021


def team_tot(rows):
    t = {"m3": 0.0, "a3": 0.0, "fga": 0.0, "fta": 0.0, "or": 0.0, "to": 0.0}
    for r in rows:
        st = r["st"] or {}
        try:
            m, a = (st.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted") or "0-0").split("-")
            t["m3"] += float(m); t["a3"] += float(a)
            t["fga"] += float((st.get("fieldGoalsMade-fieldGoalsAttempted") or "0-0").split("-")[1])
            t["fta"] += float((st.get("freeThrowsMade-freeThrowsAttempted") or "0-0").split("-")[1])
            t["or"] += float(st.get("offensiveRebounds") or 0)
            t["to"] += float(st.get("turnovers") or 0)
        except (ValueError, IndexError):
            pass
    return t


state = defaultdict(lambda: {"n": 0, "m3": 0.0, "a3": 0.0, "om3": 0.0, "oa3": 0.0, "pace": []})
T = defaultdict(list)
for g in sorted(FIN, key=lambda x: x["start"]):
    s = g["season"]
    f = {}
    for side, t in (("home", g["home"]), ("away", g["away"])):
        stt = state[(s, t)]
        lucky = None
        if stt["n"] >= 10 and stt["a3"] >= 200 and stt["oa3"] >= 200:
            lucky = (stt["m3"] / stt["a3"] - stt["om3"] / stt["oa3"]) >= 0.02
        pace = sum(stt["pace"][-10:]) / len(stt["pace"][-10:]) if len(stt["pace"]) >= 5 else None
        prev = B.before(TL, t, g["start"], 4)
        back = side == "home" and len(prev) == 4 and all(p["away"] == t and p["season"] == s for p in prev)
        f[side] = (lucky, pace, back)
    for side, oside in (("home", "away"), ("away", "home")):
        p = B.ats(g, side)
        if p is None:
            continue
        me, th = f[side], f[oside]
        sc = 0
        parts = []
        if me[0]:
            sc -= 1; parts.append("-3P")
        if th[0]:
            sc += 1; parts.append("+3P")
        if me[1] is not None and th[1] is not None:
            if me[1] - th[1] >= 4:
                sc -= 1; parts.append("-pace")
            if th[1] - me[1] >= 4:
                sc += 1; parts.append("+pace")
        if me[2]:
            sc -= 1; parts.append("-trip")
        if th[2]:
            sc += 1; parts.append("+trip")
        line = g["sp"] if side == "home" else -g["sp"]

        def add(k):
            T[k].append((s, p))
        add("base: every side")
        add(f"stack {sc:+d}" if -2 <= sc <= 2 else ("stack +3" if sc > 0 else "stack -3"))
        if sc >= 1:
            add("STACK +1 or more")
        if sc >= 2:
            add("STACK +2 or more")
            add("   +2: dog" if line > 0 else "   +2: favorite")
            add("   +2: home" if side == "home" else "   +2: road")
        if sc <= -2:
            add("STACK -2 or worse (the fade side)")
        for k in parts:
            add("alone: " + {"+3P": "across a team lucky from three", "-3P": "lucky from three (the fade)", "+pace": "across a team 4+ faster",
                             "-pace": "4+ faster (the fade)", "+trip": "visitor at a team home from a 4+ game trip", "-trip": "home from a 4+ game trip (the fade)"}[k])
        if "+3P" in parts and "+pace" in parts:
            add("pair: across a lucky AND faster team")
        if "+3P" in parts and "-3P" not in parts and "-pace" not in parts:
            add("across a lucky team, nothing against me")
    bx = BOX.get(g["id"])
    if bx and g["home"] in bx and g["away"] in bx:
        th_, ta_ = team_tot(bx[g["home"]]), team_tot(bx[g["away"]])
        pos = ((th_["fga"] - th_["or"] + th_["to"] + 0.44 * th_["fta"]) + (ta_["fga"] - ta_["or"] + ta_["to"] + 0.44 * ta_["fta"])) / 2
        for t, a, b in ((g["home"], th_, ta_), (g["away"], ta_, th_)):
            stt = state[(s, t)]
            stt["n"] += 1
            stt["m3"] += a["m3"]; stt["a3"] += a["a3"]; stt["om3"] += b["m3"]; stt["oa3"] += b["a3"]
            if pos > 60:
                stt["pace"].append(pos)

o(f"== NBA spread stack ({len(FIN)} regular-season games 2016-26; train to {SPLIT}, held 2022-26) ==")
for k in sorted(T):
    r = T[k]
    tr = [(s, p) for s, p in r if s <= SPLIT]
    he = [(s, p) for s, p in r if s > SPLIT]
    ut, uh = L.by_season(tr), L.by_season(he)
    o(f"   {k[:52]:52s} {L.st([p for _, p in r])} | train {L.roi([p for _, p in tr]):+5.1f}% ({ut[0]}/{ut[1]}) | HELD {L.st([p for _, p in he])} ({uh[0]}/{uh[1]} up: {uh[2]})")
o(f"   cells: {len(T)}")
o.save()
