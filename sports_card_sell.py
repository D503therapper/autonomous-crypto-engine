"""🗣️ THE CARD SELLS THE PICK (the owner, 11/22, after four card passes: "The breakdowns are short and vague" / "the
breakdowns basically need to sell our picks why we taking them and needs to be in our lingo").

The 11/22 cards that set him off - Robert Morris +102 1u and Nicholls +195 1u, the college hoops dog slot - carried 3-4
lines, two of them the same scoreboard stat said twice, and not one word of what the engine's read saw: the matchup on
the floor. The read stands on how the two teams really play (who shoots it, who rebounds, who turns it over, who gets
to the line, whose threes are running hot) and the card only ever said who lost last.

This module is the part of the write-up that says it. Every line is a real number off the TEAM box scores we hold
(data/sports/teamstats/<league>.jsonl - both teams' lines for every game) and the game files, said only when it argues
for OUR side, the way a bettor says it:

    profile(lg, games, tid)   one team's season off its box scores - shooting, the glass, turnovers, the line, the
                              paint, shots on net, the power play, the ground game ... (college hoops: D1 games only)
    sell_facts(...)           the card's reason-backed lines, best first: each reason the leg carries (the dog read's
                              parts, the study angles, the stack, the gap) said as a checkable matchup fact, then the
                              rest of the real gaps on the floor
    lead_of(...)              a body line as the line under the pick: our side first, then the fact
    same_stat(a, b)           two lines that say the same stat about the same team (the season's points and the last
                              3's points) - one fact, said once (sports_card_check runs it on every render)

Never "our ratings say", never our number against the books', never a study's win rate as the line (the owner, 11/19:
"we can't say that we're better at pricing the lines than the fucking line makers"). A stat we can't see = no line.
"""
import glob
import json
import os
import re

import sports_data as sd

SELL = True                  # the switch (False = the 11/19 card)
MIN_BOX = {"ncaab": 3, "nba": 5, "nhl": 6, "nfl": 4, "ncaaf": 4}   # box games a team needs before its numbers are said
_BOX = {}                    # league -> (stamp, {game id: {team id: its raw box line}})
DATA = None                  # (the tests point it at a temp folder)


def _files(lg, data=None):
    data = data or DATA or sd.DATA
    return [os.path.join(data, "teamstats", f"{lg}.jsonl")] + sorted(glob.glob(os.path.join(data, "teamstats", lg, "*.jsonl")))


def load(lg, data=None):
    """{game id: {team id: the box line}} for one league (cached on the files' sizes)."""
    files = _files(lg, data)
    stamp = tuple((f, os.path.getsize(f)) for f in files if os.path.exists(f))
    hit = _BOX.get(lg)
    if hit and hit[0] == stamp:
        return hit[1]
    out = {}
    for fn in files:
        try:
            fh = open(fn)
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    tm = {str(k): v for k, v in (d.get("teams") or {}).items() if isinstance(v, dict)}
                    if len(tm) == 2:
                        out[str(d["gid"])] = tm
                except (KeyError, ValueError, TypeError, AttributeError):
                    continue
    _BOX[lg] = (stamp, out)
    return out


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _pair(x, sep="-"):
    """'27-64' -> (27.0, 64.0); None when it isn't one."""
    try:
        a, b = str(x).split(sep)[:2]
        return float(a), float(b)
    except (TypeError, ValueError):
        return None


def _hoops(t):
    fg = _pair(t.get("fieldGoalsMade-fieldGoalsAttempted"))
    tp = _pair(t.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
    ft = _pair(t.get("freeThrowsMade-freeThrowsAttempted"))
    reb, oreb = _n(t.get("totalRebounds")), _n(t.get("offensiveRebounds"))
    to = _n(t.get("totalTurnovers") if t.get("totalTurnovers") not in (None, "") else t.get("turnovers"))
    if not fg or not tp or not ft or reb is None or to is None:
        return None
    return {"fgm": fg[0], "fga": fg[1], "tpm": tp[0], "tpa": tp[1], "ftm": ft[0], "fta": ft[1], "reb": reb,
            "oreb": oreb or 0.0, "to": to, "paint": _n(t.get("pointsInPaint")), "fast": _n(t.get("fastBreakPoints")),
            "ast": _n(t.get("assists")), "stl": _n(t.get("steals")), "blk": _n(t.get("blocks"))}


def _hockey(t):
    sh = _n(t.get("shotsTotal"))
    if sh is None:
        return None
    return {"shots": sh, "ppg": _n(t.get("powerPlayGoals")) or 0.0, "ppo": _n(t.get("powerPlayOpportunities")) or 0.0,
            "fo": _n(t.get("faceoffPercent")), "give": _n(t.get("giveaways")), "take": _n(t.get("takeaways")),
            "pim": _n(t.get("penaltyMinutes")), "hits": _n(t.get("hits"))}


def _football(t):
    yds, rush = _n(t.get("totalYards")), _n(t.get("rushingYards"))
    if yds is None or rush is None:
        return None
    third = _pair(t.get("thirdDownEff"))
    sk = _pair(t.get("sacksYardsLost"))
    return {"yds": yds, "rush": rush, "pass": _n(t.get("netPassingYards")), "to": _n(t.get("turnovers")) or 0.0,
            "third_m": third[0] if third else None, "third_a": third[1] if third else None,
            "sacked": sk[0] if sk else None}


_READ = {"ncaab": _hoops, "nba": _hoops, "nhl": _hockey, "nfl": _football, "ncaaf": _football}


def profile(lg, gs, tid, last=None, data=None):
    """One team's numbers over the games in `gs` that we hold BOTH box lines for (`last`: only its last N of them):
    sums and the game count, both ways ("x": ours, "o_x": the other team's in the same games) - None under MIN_BOX."""
    rd = _READ.get(lg)
    if not rd or not gs:
        return None
    box = load(lg, data)
    tid = str(tid)
    rows = []
    for g in gs:
        b = box.get(str(g.get("id") or ""))
        if not b or tid not in b or len(b) != 2:
            continue
        oid = next(k for k in b if k != tid)
        mine, his = rd(b[tid]), rd(b[oid])
        if not mine or not his:
            continue
        try:
            home = str(g.get("home")) == tid
            pf = float(g["home_score"] if home else g["away_score"])
            pa = float(g["away_score"] if home else g["home_score"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append((mine, his, pf, pa))
    if last:
        rows = rows[-last:]
    if len(rows) < (min(last, MIN_BOX.get(lg, 5)) if last else MIN_BOX.get(lg, 5)):
        return None
    out = {"n": len(rows), "pf": sum(r[2] for r in rows), "pa": sum(r[3] for r in rows)}
    for k in rows[0][0]:
        mv = [r[0].get(k) for r in rows]
        ov = [r[1].get(k) for r in rows]
        if any(x is None for x in mv) or any(x is None for x in ov):
            continue
        out[k], out["o_" + k] = sum(mv), sum(ov)
    return out


def per(p, k):
    """A game's worth of one stat (None when the profile doesn't hold it)."""
    return p[k] / p["n"] if p and p.get(k) is not None and p.get("n") else None


def pct(p, made, att):
    """A percentage off two sums, 0-100 (None with no attempts)."""
    return 100.0 * p[made] / p[att] if p and p.get(att) else None


# ---------------------------------------------------------------------------------------------------------------------
# the lines. Each maker returns (key, [ways], reason?, weight); `reason` marks the ones the leg's own reasons point at
# (the dog read's parts, the study angles, the stack) - those open the body and the best of them leads the card.
# ---------------------------------------------------------------------------------------------------------------------
GLASS_GAP = {"ncaab": 5.0, "nba": 4.0}       # rebounds a game between the two margins before the glass is a line
GLASS_ONE = {"ncaab": 4.0, "nba": 3.0}       # ... or one side's own margin this big
TO_GAP = {"ncaab": 2.5, "nba": 1.5}          # turnovers a game: theirs committed over ours committed
TO_MANY = {"ncaab": 13.0, "nba": 15.0}       # ... and theirs at least this many a game
TO_FORCE = {"ncaab": 14.5, "nba": 15.5}      # takeaways a game worth saying
FG_GAP = 3.0                                 # shooting: points of field-goal % between the two teams
D_FG = {"ncaab": 41.0, "nba": 45.5}          # a defense that holds teams under this from the field is a line
D_BAD = {"ncaab": 47.0, "nba": 48.5}         # a defense that lets teams shoot this or better
O_BAD = {"ncaab": 40.5, "nba": 44.5}         # an offense shooting this or worse
THREE_RUN = 6.0                              # their threes the last 5 this many points over their season = running hot
THREE_OPP_LOW = {"ncaab": 29.0, "nba": 33.0}   # teams shooting this or worse from three against them = luck, not defense
THREE_GOOD = 36.0
FT_GAP = {"ncaab": 5.0, "nba": 3.0}          # free throws a game: ours taken over theirs taken
PAINT_GAP = {"ncaab": 8.0, "nba": 6.0}
FAST_GAP = {"ncaab": 6.0, "nba": 5.0}        # fast-break points a game: what they give up over what they get
STEALS = {"ncaab": 8.5, "nba": 9.0}           # steals a game worth saying
AST_LOW = {"ncaab": 10.5, "nba": 23.0}       # assists a game: a team that doesn't move the ball
SHOT_GAP = 3.0                               # hockey: shots a game, the two margins apart
PP_MIN = 20                                  # hockey: a power play / a kill said as a count needs this many chances
RUSH_BIG = 125.0                             # football: yards a game on the ground worth saying / worth giving up
PASS_BIG = (240.0, 215.0)                    # ... through the air: ours thrown, theirs allowed
FB_TO_GAP = 4                                # football: giveaways on the year, theirs over ours
SCHED_EDGE = 50.0                            # 🏫 college (SCHEDULE_FAIR - "We can't be looking like some clowns", the Oakland
#   0-5 card): two teams' numbers are set against each other only when their schedules were about as tough - the
#   average rating of the teams THEY played no more than this far above the teams WE played. Past it the only line left
#   is one that isn't about the schedule (their threes running hot).


def _r(x):
    return f"{x:.0f}"


def _pos(name):
    return f"{name}'" if str(name).endswith("s") else f"{name}'s"


def sched(gs, tid, e):
    """The average rating of the teams tid played in `gs` (None with no ratings / no games)."""
    if e is None or not gs:
        return None
    tid = str(tid)
    rs = [e.r.get(g["away"] if str(g["home"]) == tid else g["home"], 1500.0) for g in gs]
    return sum(rs) / len(rs) if rs else None


def fair_cmp(gu, gt, tid, oid, e):
    """May the two teams' numbers be set against each other? (their schedule not SCHED_EDGE+ tougher than ours)"""
    a, b = sched(gu, tid, e), sched(gt, oid, e)
    return a is None or b is None or b - a <= SCHED_EDGE


def hoops_lines(lg, us, them, pu, pt, pt5, leg, d1="", cmp_ok=True):
    """College hoops / NBA: the matchup on the floor off both teams' box scores. -> [(key, ways, reason?, weight)]"""
    out = []
    if not pu or not pt:
        return out
    vs = " against D1 teams" if d1 else " this year"
    T, yr = ("D1 teams", "") if d1 else ("Teams", " this year")   # ("Teams shoot 54% on X against D1 teams" reads wrong)
    fired = " ".join(str(x) for x in (leg.get("ncaab_fired") or [])).lower()
    rs = " ".join(str(x) for x in (leg.get("reasons") or [])).lower()
    parts = leg.get("dog_read_parts") or {}
    facts = set(parts.get("facts") or []) | set(leg.get("dog_good") or [])
    backed = (parts.get("ratings") or 0) > 0 or (leg.get("eff_p") or 0) >= 0.5 or \
        (leg.get("market") == "ml" and (leg.get("odds") or 0) < 0) or "stronger team" in rs
    # 4. three-point luck: their threes running hot / teams missing everything against them - said as it coming back
    t3_s, t3_5 = pct(pt, "tpm", "tpa"), pct(pt5, "tpm", "tpa") if pt5 else None
    o3_t = pct(pt, "o_tpm", "o_tpa")
    luck_r = (leg.get("opp_tp_net") or 0) >= 0.05 or bool(leg.get("opp_hot_deep"))
    if t3_s is not None and t3_5 is not None and pt["n"] >= 7 and t3_5 - t3_s >= THREE_RUN and t3_s <= 37:
        out.append(("three_luck", [f"👌 {them} hit {_r(t3_5)}% from three their last {pt5['n']} - way over their {_r(t3_s)}% on the year. That don't last.",
                                   f"👌 {them} been living on the three: {_r(t3_5)}% their last {pt5['n']}, {_r(t3_s)}% on the season. They're due to cool off.",
                                   f"👌 {_r(t3_5)}% from deep the last {pt5['n']} games for {them}, who shoot {_r(t3_s)}% on the year. That comes back down."],
                    luck_r, 8.0 + (t3_5 - t3_s) / 6))
    elif o3_t is not None and pt.get("o_tpa", 0) >= 60 and o3_t <= THREE_OPP_LOW[lg] and luck_r:
        m_, a_ = _r(pt["o_tpm"]), _r(pt["o_tpa"])
        out.append(("three_luck", [f"👌 {T} are {m_} for {a_} from three against {them}{yr} - {_r(o3_t)}%. Nobody guards the arc that good. Those start falling.",
                                   f"👌 {them} been getting lucky: {T.lower() if not d1 else T} are {m_} for {a_} from three against 'em{yr}. Open looks don't keep missing.",
                                   f"👌 {_r(o3_t)}% from deep is all {T.lower() if not d1 else T} hit on {them}{yr} ({m_} for {a_}). That's cold shooting, not defense - it evens out."],
                    True, 8.0))
    if not cmp_ok:
        return out
    # 1. the glass
    ru, rt = (pu["reb"] - pu["o_reb"]) / pu["n"], (pt["reb"] - pt["o_reb"]) / pt["n"]
    glass_r = "glass" in fired or bool(leg.get("hoops_inside")) or "rebound" in rs or "the glass" in rs
    if ru - rt >= GLASS_GAP[lg] and ru >= 1 and rt <= -1:
        out.append(("glass", [f"🧲 {us} out-rebound teams by {_r(ru)} a game{vs}. {them} get beat on the glass by {_r(-rt)}.",
                              f"🧲 The glass is ours: {us} plus {_r(ru)} rebounds a game{vs}, {them} minus {_r(-rt)}.",
                              f"🧲 {them} get out-rebounded by {_r(-rt)} a game{vs} and {us} win the boards by {_r(ru)}. Second chances all night."],
                    glass_r, 9.0 + (ru - rt) / 4))
    elif rt <= -GLASS_ONE[lg] and ru > rt + 2:
        out.append(("glass", [f"🧲 {them} get beat on the glass by {_r(-rt)} a game{vs}.",
                              f"🧲 {them} can't rebound - out-rebounded by {_r(-rt)} a game{vs}.",
                              f"🧲 {T} grab {_r(-rt)} more boards a game than {them}{yr}. That's extra shots for {us}."],
                    glass_r, 7.0 - rt / 4))
    elif ru >= GLASS_ONE[lg] and ru > rt + 2:
        out.append(("glass", [f"🧲 {us} out-rebound teams by {_r(ru)} a game{vs}.",
                              f"🧲 {us} own the glass - plus {_r(ru)} rebounds a game{vs}.",
                              f"🧲 {_r(ru)} more boards a game than the other team for {us}{vs}. They clean it up."],
                    glass_r, 7.0 + ru / 4))
    # 2. turnovers: theirs committed against ours / against what we force
    tu, tt = pu["to"] / pu["n"], pt["to"] / pt["n"]
    fu = pu["o_to"] / pu["n"]
    to_r = (leg.get("to_net") or 0) >= 0.02 or "turnover" in fired or "turnover" in rs
    if tt - tu >= TO_GAP[lg] and tt >= TO_MANY[lg] and _r(tt) != _r(tu):
        out.append(("to", [f"🧤 {them} cough it up {_r(tt)} times a game{vs}. {us}: {_r(tu)}.",
                           f"🧤 {_r(tt)} turnovers a game for {them}{vs}, {_r(tu)} for {us}. Free possessions.",
                           f"🧤 {them} turn it over {_r(tt)} times a night{vs} and {us} take care of it ({_r(tu)})."],
                    to_r, 7.5 + (tt - tu) / 3))
    elif fu >= TO_FORCE[lg] and tt >= TO_MANY[lg] and fu > tu + 1:
        out.append(("to", [f"🧤 {us} force {_r(fu)} turnovers a game{vs} and {them} already give it away {_r(tt)} times a night.",
                           f"🧤 {them} turn it over {_r(tt)} times a game{vs}. {us} take it away {_r(fu)} times a night.",
                           f"🧤 {_r(fu)} takeaways a game for {us}{vs}, and {them} cough it up {_r(tt)} times a night."],
                    to_r, 7.0 + (fu + tt - 27) / 3))
    # 3. the shooting matchup: what we hold teams to / what they let teams shoot / what they shoot
    fgu, fgt = pct(pu, "fgm", "fga"), pct(pt, "fgm", "fga")
    dfu, dft = pct(pu, "o_fgm", "o_fga"), pct(pt, "o_fgm", "o_fga")
    def_r = "def_first_vs_bad_off" in facts or "def_first_vs_bad_offense" in facts
    ppg_t, ppg_u_a = pt["pf"] / pt["n"], pu["pa"] / pu["n"]
    if None not in (fgu, fgt, dfu, dft):
        if dfu <= D_FG[lg] and dfu + 1 <= dft and fgt <= dfu + 4:
            out.append(("defense", [f"🛡️ {us} hold teams to {_r(dfu)}% shooting{vs}. {them} shoot {_r(fgt)}%.",
                                    f"🛡️ {us} guard: teams shoot {_r(dfu)}% against 'em{vs} and score {_r(ppg_u_a)} a game. {them} only put up {_r(ppg_t)}.",
                                    f"🛡️ {them} shoot {_r(fgt)}% from the field{vs} and now they get the {us} defense, holding teams to {_r(dfu)}%."],
                        def_r or backed, 9.5 if def_r else 7.5 + (dft - dfu) / 4))
        if fgu - fgt >= FG_GAP and dft >= dfu and dft >= 44:
            out.append(("shooting", [f"🪣 {us} shoot {_r(fgu)}% from the field{vs}; {them} let teams shoot {_r(dft)}%.",
                                     f"🪣 {them} let teams hit {_r(dft)}% of their shots{vs}. {us} shoot {_r(fgu)}%.",
                                     f"🪣 {_r(fgu)}% shooting for {us}{vs}, and the {them} defense gives up {_r(dft)}%. Buckets."],
                        backed, 7.5 + (fgu - fgt) / 3))
        elif dft >= D_BAD[lg] and dft - dfu >= 2:
            out.append(("shooting", [f"🪣 {T} shoot {_r(dft)}% on {them}{yr}. That defense ain't stopping nobody.",
                                     f"🪣 {them} let teams hit {_r(dft)}% of their shots{vs}.",
                                     f"🪣 {_r(dft)}% shooting allowed by {them}{vs}. {us} get good looks all game."],
                        backed, 7.0 + (dft - 45) / 3))
        elif fgt <= O_BAD[lg] and fgu - fgt >= 1:
            out.append(("shooting", [f"🪣 {them} shoot {_r(fgt)}% from the field{vs}. Bricks.",
                                     f"🪣 {them} can't shoot it - {_r(fgt)}% from the field{vs}.",
                                     f"🪣 {_r(fgt)}% shooting{vs} for {them}. They struggle to score."],
                        backed or def_r, 7.0 + (42 - fgt) / 3))
    # 5. our threes against what they give up
    u3 = pct(pu, "tpm", "tpa")
    u3m = pu["tpm"] / pu["n"]
    if u3 is not None and o3_t is not None and u3 >= THREE_GOOD and o3_t >= THREE_GOOD and pu["tpa"] >= 50 \
            and not any(k == "three_luck" for k, *_ in out):
        out.append(("threes", [f"👌 {us} hit {_r(u3)}% from three{vs} and {them} let teams shoot {_r(o3_t)}% from out there.",
                               f"👌 {them} give up {_r(o3_t)}% from three{vs}. {us} make {_r(u3m)} a game at {_r(u3)}%.",
                               f"👌 {_r(u3m)} threes a game at {_r(u3)}% for {us}{vs} - and {them} can't guard the arc ({_r(o3_t)}% allowed)."],
                    backed, 7.0 + (u3 + o3_t - 72) / 4))
    # 6. the free-throw line
    ftu, ftt = pu["fta"] / pu["n"], pt["fta"] / pt["n"]
    oft_t = pt["o_fta"] / pt["n"]
    if ftu - ftt >= FT_GAP[lg] and oft_t >= ftt:
        out.append(("line", [f"🎁 {us} get to the line {_r(ftu)} times a game{vs}; {them} {_r(ftt)}.",
                             f"🎁 Free throws a game{vs}: {_r(ftu)} for {us}, {_r(ftt)} for {them}. Free points.",
                             f"🎁 {them} put teams on the line {_r(oft_t)} times a game{vs} and {us} live there ({_r(ftu)} a night)."],
                    False, 6.0 + (ftu - ftt) / 4))
    # 7. the paint
    if pu.get("paint") is not None and pt.get("paint") is not None:
        pa_u, pa_t = pu["paint"] / pu["n"], pt["paint"] / pt["n"]
        gave = pt["o_paint"] / pt["n"]
        in_r = bool(leg.get("hoops_inside")) or "wins inside" in rs
        if pa_u - pa_t >= PAINT_GAP[lg] and gave > pa_t and _r(gave) != _r(pa_t):
            out.append(("paint", [f"🎨 {us} score {_r(pa_u)} a game in the paint{vs}. {them} give up {_r(gave)} in there.",
                                  f"🎨 Points in the paint a game{vs}: {us} {_r(pa_u)}, {them} {_r(pa_t)}.",
                                  f"🎨 {them} give up {_r(gave)} a game in the paint{vs} and {us} get {_r(pa_u)} down there every night."],
                        in_r, 6.0 + (pa_u - pa_t) / 6))
        elif gave - pa_t >= PAINT_GAP[lg] + 2 and pa_u > pa_t:
            out.append(("paint", [f"🎨 {them} get outscored {_r(gave)} to {_r(pa_t)} in the paint{vs}.",
                                  f"🎨 In the paint{vs}: {_r(pa_t)} a game for {them}, {_r(gave)} against. Soft inside.",
                                  f"🎨 {T} score {_r(gave)} a game in the paint on {them}{yr}. They only get {_r(pa_t)} back."],
                        in_r, 6.0 + (gave - pa_t) / 6))
    # 7a. the paint wall (11/23 board check - the Pacers +160 card: the 11/22 paint weight moved the dog score and the
    #     card had no line that said so): OUR team is in the league's best fifth at keeping points out of the paint
    #     (sports.mark_nba_paint -> leg["paint_shut"]) - the share of the points it gives up that come in there
    if lg == "nba" and leg.get("paint_shut") is True and pu.get("o_paint") and pu.get("pa") and pt.get("paint") is not None \
            and not any(k == "paint" for k, *_ in out):
        sh, in_t = 100.0 * pu["o_paint"] / pu["pa"], pt["paint"] / pt["n"]
        out.append(("paint", [f"🎨 {us} wall off the rim: only {_r(sh)}% of the points they give up come in the paint{vs}, one of the lowest shares in the league. {them} get {_r(in_t)} a game in there.",
                              f"🎨 Only {_r(sh)}% of what teams score on {us} comes in the paint{vs} - one of the lowest shares in the league. {them} score {_r(in_t)} a night in there.",
                              f"🎨 {them} get {_r(in_t)} points a game in the paint{vs}. {us} don't give that up: just {_r(sh)}% of the points against 'em come in there, one of the lowest shares in the league."],
                    True, 8.5))
    # 7b. hands: our steals (a defense that takes the ball)
    if pu.get("stl") is not None and pt.get("stl") is not None and not any(k == "to" for k, *_ in out):
        st_u, st_t = pu["stl"] / pu["n"], pt["stl"] / pt["n"]
        if st_u >= STEALS[lg] and st_u - st_t >= 1.5:
            out.append(("steals", [f"🥷 {us} come up with {_r(st_u)} steals a game{vs}. {them}: {_r(st_t)}.",
                                   f"🥷 {_r(st_u)} steals a game for {us}{vs}. They get in your pocket.",
                                   f"🥷 {us} take it right from you - {_r(st_u)} steals a game{vs}, {_r(st_t)} for {them}."],
                        def_r, 6.2 + (st_u - st_t) / 4))
    # 8. the break
    if pu.get("fast") is not None and pt.get("fast") is not None:
        fb_t, fb_a, fb_u = pt["fast"] / pt["n"], pt["o_fast"] / pt["n"], pu["fast"] / pu["n"]
        if fb_a - fb_t >= FAST_GAP[lg] and fb_u >= fb_t and _r(fb_a) != _r(fb_t):
            out.append(("fast", [f"💨 {them} get outscored {_r(fb_a)} to {_r(fb_t)} on the fast break{vs}.",
                                 f"💨 On the break{vs}: {_r(fb_t)} points a game for {them}, {_r(fb_a)} against. They don't get back.",
                                 f"💨 {T} get {_r(fb_a)} fast-break points a game on {them}{yr}. {them} get {_r(fb_t)}."],
                        False, 5.6 + (fb_a - fb_t) / 6))
    # 9. the ball doesn't move
    if pu.get("ast") is not None and pt.get("ast") is not None:
        as_t, as_u = pt["ast"] / pt["n"], pu["ast"] / pu["n"]
        if as_t <= AST_LOW[lg] and as_u - as_t >= 3:
            out.append(("assists", [f"🤝 {them} get {_r(as_t)} assists a game{vs}. {us}: {_r(as_u)}. One team moves the ball.",
                                    f"🤝 Assists a game{vs}: {_r(as_u)} for {us}, {_r(as_t)} for {them}. They play one-on-one.",
                                    f"🤝 Only {_r(as_t)} assists a game for {them}{vs} - everybody for himself. {us} get {_r(as_u)}."],
                        False, 5.5 + (as_u - as_t) / 6))
    return out


def hockey_lines(us, them, pu, pt, leg):
    out = []
    if not pu or not pt:
        return out
    su, st = (pu["shots"] - pu["o_shots"]) / pu["n"], (pt["shots"] - pt["o_shots"]) / pt["n"]
    luck_r = leg.get("pdo") is not None and leg.get("pdo") <= 0.99
    if su - st >= SHOT_GAP and su >= 0.5 and st <= -0.5 and _r(su) != "0" and _r(-st) != "0":
        out.append(("shots", [f"🏹 {us} outshoot teams by {_r(su)} a night this year. {them} get outshot by {_r(-st)}.",
                              f"🏹 Shots on net this year: {us} plus {_r(su)} a game, {them} minus {_r(-st)}. We carry the play.",
                              f"🏹 {them} get outshot by {_r(-st)} a night this year and {us} put {_r(pu['shots'] / pu['n'])} on net a game."],
                    luck_r, 7.5 + (su - st) / 4))
    elif st <= -3 and su > st + 1:
        out.append(("shots", [f"🏹 {them} get outshot by {_r(-st)} a night this year ({_r(pt['o_shots'] / pt['n'])} against, {_r(pt['shots'] / pt['n'])} for).",
                              f"🏹 Teams put {_r(pt['o_shots'] / pt['n'])} shots a night on {them} this year and they only get {_r(pt['shots'] / pt['n'])} back."],
                    luck_r, 6.5 - st / 4))
    # special teams, as counts: our power play against their kill
    if pu["ppo"] >= PP_MIN and pt["o_ppo"] >= PP_MIN:
        ppu, pkt = 100.0 * pu["ppg"] / pu["ppo"], 100.0 * pt["o_ppg"] / pt["o_ppo"]
        if ppu >= 21 and pkt >= 21:
            out.append(("pp", [f"⚡ {us} scored on {_r(pu['ppg'])} of {_r(pu['ppo'])} power plays this year. {them} gave up {_r(pt['o_ppg'])} goals on {_r(pt['o_ppo'])} kills.",
                               f"⚡ {them} let in {_r(pt['o_ppg'])} power-play goals on {_r(pt['o_ppo'])} kills this year - and {us} cashed {_r(pu['ppg'])} of {_r(pu['ppo'])} with the man up.",
                               f"⚡ Man up, {us} are {_r(pu['ppg'])} for {_r(pu['ppo'])} this year. {them} been leaking on the kill: {_r(pt['o_ppg'])} against in {_r(pt['o_ppo'])}."],
                        False, 7.0 + (ppu + pkt - 42) / 6))
        elif pkt >= 24:
            out.append(("pp", [f"⚡ {them} gave up {_r(pt['o_ppg'])} power-play goals on {_r(pt['o_ppo'])} kills this year. Take a penalty against {us} and it costs.",
                               f"⚡ {_r(pt['o_ppg'])} goals against on {_r(pt['o_ppo'])} kills for {them} this year. That penalty kill is leaking."],
                        False, 6.5 + (pkt - 24) / 5))
    if pt["ppo"] >= PP_MIN and pu["o_ppo"] >= PP_MIN and not any(k == "pp" for k, *_ in out):
        ppt, pku = 100.0 * pt["ppg"] / pt["ppo"], 100.0 * pu["o_ppg"] / pu["o_ppo"]
        if ppt <= 16 and pku <= 20:
            out.append(("pp", [f"⚡ {them} scored on just {_r(pt['ppg'])} of {_r(pt['ppo'])} power plays this year. {us} killed {_r(pu['o_ppo'] - pu['o_ppg'])} of {_r(pu['o_ppo'])}.",
                               f"⚡ {_pos(them)} power play is {_r(pt['ppg'])} for {_r(pt['ppo'])} this year, and {us} killed {_r(pu['o_ppo'] - pu['o_ppg'])} of {_r(pu['o_ppo'])}. No help coming there."],
                        False, 6.0 + (16 - ppt) / 5))
    return out


def football_lines(us, them, pu, pt, leg):
    out = []
    if not pu or not pt:
        return out
    ru, rt_a = pu["rush"] / pu["n"], pt["o_rush"] / pt["n"]
    ru_a, rt = pu["o_rush"] / pu["n"], pt["rush"] / pt["n"]
    if ru >= RUSH_BIG and rt_a >= RUSH_BIG:
        out.append(("ground", [f"🏃 {us} run for {_r(ru)} yards a game this year and {them} give up {_r(rt_a)} on the ground.",
                               f"🏃 {them} let teams run for {_r(rt_a)} a game this year. {us} put up {_r(ru)} a game on the ground.",
                               f"🏃 {_r(ru)} rushing yards a game for {us}; {_r(rt_a)} allowed a game by {them}. We run it down their throat."],
                    False, 7.5 + (ru + rt_a - 250) / 40))
    elif ru_a <= 100 and rt <= 105:
        out.append(("ground", [f"🏃 {them} only run for {_r(rt)} yards a game this year and {us} hold teams to {_r(ru_a)} on the ground.",
                               f"🏃 {us} give up {_r(ru_a)} rushing yards a game this year. {them} get {_r(rt)} a game. One-dimensional."],
                    False, 7.0))
    if pu.get("pass") is not None and pt.get("o_pass") is not None:
        au, at_a, at = pu["pass"] / pu["n"], pt["o_pass"] / pt["n"], pt["pass"] / pt["n"]
        if au >= PASS_BIG[0] and at_a >= PASS_BIG[1] and au - at >= 30:
            out.append(("air", [f"🎈 {us} throw for {_r(au)} yards a game this year and {them} give up {_r(at_a)} through the air.",
                                f"🎈 Through the air this year: {_r(au)} yards a game for {us}, {_r(at)} for {them}.",
                                f"🎈 {them} let teams throw for {_r(at_a)} a game this year. {us} put up {_r(au)} a game passing."],
                        False, 7.0 + (au - at) / 40))
    gu, gt = pu["to"], pt["to"]
    if gt * pu["n"] - gu * pt["n"] >= FB_TO_GAP * min(pu["n"], pt["n"]) / 2 and gt - gu >= 3 and gt / pt["n"] >= 1.3:
        out.append(("fb_to", [f"🧤 {them} turned it over {_r(gt)} times in {pt['n']} games this year. {us}: {_r(gu)} in {pu['n']}.",
                              f"🧤 {_r(gt)} giveaways in {pt['n']} games for {them} this year, {_r(gu)} in {pu['n']} for {us}. They hand you the ball.",
                              f"🧤 {us} gave it away {_r(gu)} times in {pu['n']} games this year. {them}: {_r(gt)} in {pt['n']}."],
                    False, 7.5 + (gt - gu) / 4))
    yu, yt_a = pu["yds"] / pu["n"], pt["o_yds"] / pt["n"]
    yt = pt["yds"] / pt["n"]
    if yu - yt >= 40 and yt_a >= 340:
        out.append(("yards", [f"📏 {us} gain {_r(yu)} yards a game this year. {them}: {_r(yt)}, and they give up {_r(yt_a)}.",
                              f"📏 Yards a game this year: {us} {_r(yu)}, {them} {_r(yt)}. {them} also let teams go for {_r(yt_a)}."],
                    False, 6.5 + (yu - yt) / 40))
    if pu.get("third_a") and pt.get("o_third_a"):
        cu, at_ = 100.0 * pu["third_m"] / pu["third_a"], 100.0 * pt["o_third_m"] / pt["o_third_a"]
        if cu >= 41 and at_ >= 41:
            out.append(("third", [f"🔗 Third down this year: {us} converted {_r(pu['third_m'])} of {_r(pu['third_a'])}; {them} let teams convert {_r(pt['o_third_m'])} of {_r(pt['o_third_a'])}.",
                                  f"🔗 {them} can't get off the field - {_r(pt['o_third_m'])} of {_r(pt['o_third_a'])} third downs converted against 'em this year. {us} moved the chains on {_r(pu['third_m'])} of {_r(pu['third_a'])}."],
                        False, 6.5 + (cu + at_ - 82) / 8))
    if pu.get("third_a") and pt.get("third_a") and not any(k == "third" for k, *_ in out):
        ct, au_ = 100.0 * pt["third_m"] / pt["third_a"], 100.0 * pu["o_third_m"] / pu["o_third_a"]
        if ct <= 36 and au_ <= 38:
            out.append(("third", [f"🔗 {them} converted just {_r(pt['third_m'])} of {_r(pt['third_a'])} third downs this year. {us} let teams convert {_r(pu['o_third_m'])} of {_r(pu['o_third_a'])}.",
                                  f"🔗 Third down this year: {them} are {_r(pt['third_m'])} for {_r(pt['third_a'])}, and {us} get off the field ({_r(pu['o_third_m'])} of {_r(pu['o_third_a'])} allowed)."],
                        False, 6.5 + (38 - ct) / 6))
    if pt.get("sacked") is not None and pu.get("o_sacked") is not None:
        st_, su_ = pt["sacked"], pu["o_sacked"]
        if st_ / pt["n"] >= 2.5 and su_ / pu["n"] >= 2.3:
            out.append(("sacks", [f"💥 {_pos(them)} quarterback got sacked {_r(st_)} times in {pt['n']} games this year. {us} got home {_r(su_)} times in {pu['n']}.",
                                  f"💥 {us} have {_r(su_)} sacks in {pu['n']} games this year and {them} already gave up {_r(st_)}. That pocket's collapsing."],
                        False, 7.0))
    return out


STAT_OF = (   # the stat a line is about - two lines on a card that say the same one about the same team are one fact
    ("glass", re.compile(r"rebound|the glass|\bboards\b", re.I)),
    ("turnover", re.compile(r"turnover|cough|takeaway|giveaway|turn(?:ed|s)? it over|g[ai]ve it away|\bsteals\b", re.I)),
    ("three", re.compile(r"from three|\bthrees\b|from deep|the arc", re.I)),
    ("paint", re.compile(r"in the paint", re.I)),
    ("line", re.compile(r"to the line|free throws|on the line", re.I)),
    ("shooting", re.compile(r"% shooting|from the field|of their shots|shoot \d+%", re.I)),
    ("shots", re.compile(r"shots on net|outshoo?t|shots a night|shots a game", re.I)),
    ("power play", re.compile(r"power[- ]play|on the kill|man up|\bkills\b", re.I)),
    ("ground", re.compile(r"on the ground|rushing yards|\brun for\b|ran for", re.I)),
    ("break", re.compile(r"fast[- ]break|on the break", re.I)),
    ("assists", re.compile(r"\bassists\b", re.I)),
    ("air", re.compile(r"through the air|\bthrow for\b|a game passing", re.I)),
    ("third", re.compile(r"third downs?", re.I)),
    ("sacks", re.compile(r"\bsacks?\b|sacked|got home", re.I)),
    ("yards", re.compile(r"yards a game", re.I)),
)
_SCORE = re.compile(r"points? a game|goals? a game|\ba game\b|a night\b|outscor|scoreboard|\d+(?:\.\d)? (?:scored|allowed|against|for)\b", re.I)
_SC_O = re.compile(r"\bscor(?:e|es|ed|ing)\b|put(?:s|ting)? up|\bmanages?\b|\boffense\b|can only find|\bfor\b(?=[,;. ])", re.I)
_SC_D = re.compile(r"\ballow(?:s|ed)?\b|g[ai]v(?:e|es|en|ing) up|\bagainst\b|\bleaking\b|holds? teams|\bdefense\b|\bour d\b", re.I)
STAT_EM = ("🧲", "🧤", "🥷", "🛡", "🪣", "👌", "🎁", "🎨", "💨", "🤝", "🏹", "⚡", "🏃", "🎈", "📏", "🔗", "💥", "📊")
SELL_EM = ("🧤", "🥷", "🪣", "🎁", "🎨", "💨", "🤝", "⚡", "🎈", "📏", "🔗", "🏆")   # the lines only this module writes


def stat_of(line):
    """The stat a card line is about ("score", "glass", ...) or None - only for the stat lines (a last game's score,
    a record, a streak, a count of big nights are games, not season stats)."""
    t = str(line or "")
    if not t.startswith(STAT_EM):
        return None
    for k, rx in STAT_OF:
        if rx.search(t):
            return k
    if t.startswith(("📊", "🛡")) and "%" not in t and _SCORE.search(t):
        # the scoreboard: what a team scores ("score_o"), what it allows ("score_d"), or both / the margin ("score")
        low = re.sub(r"against d1 teams", "", t, flags=re.I)
        o, d = bool(_SC_O.search(low)), bool(_SC_D.search(low))
        if re.search(r"outscor|win by|lose by|winning by|plus \d|minus \d", low, re.I) or (o and d):
            return "score"
        return "score_o" if o else "score_d" if d else "score"
    return None


def _whose(line, us, them):
    """Which team a stat line is about: 'us', 'them', 'both' (None when neither is named)."""
    t = str(line or "")
    a = bool(us and re.search(rf"(?<![\w]){re.escape(us)}(?![\w])", t))
    b = bool(them and re.search(rf"(?<![\w]){re.escape(them)}(?![\w])", t))
    if a and b and us in them:                            # ("Oregon" inside "Oregon St": only the longer name is there)
        a = bool(re.search(rf"(?<![\w]){re.escape(us)}(?![\w])", t.replace(them, "")))
    if a and b and them in us:
        b = bool(re.search(rf"(?<![\w]){re.escape(them)}(?![\w])", t.replace(us, "")))
    return "both" if a and b else "us" if a else "them" if b else None


def same_stat(a, b, us, them):
    """Two card lines that say the same stat about the same team - "New Mexico St this season: 78 points a game allowed,
    66 scored" and "New Mexico St have been outscored 72 to 63 a game over their last 3". One fact, said once."""
    ka, kb = stat_of(a), stat_of(b)
    if not ka or not kb:
        return False
    if ka != kb and not (ka.startswith("score") and kb.startswith("score") and "score" in (ka, kb)):
        return False                                      # (what we score and what we allow are two facts; the margin
        #                                                   line says both, so it is either one again)
    wa, wb = _whose(a, us, them), _whose(b, us, them)
    if not wa or not wb:
        return False
    return wa == wb or "both" in (wa, wb)


def dedupe(lines, us, them, why=""):
    """Drop a later stat line that repeats an earlier one's stat for the same team (the line under the pick counts as
    the first). The order is the card's - the first said stays. -> (kept, dropped)"""
    kept, gone, seen = [], [], [why] if why else []
    for x in lines or []:
        if isinstance(x, str) and stat_of(x) and any(same_stat(y, x, us, them) for y in seen):
            gone.append(x)
            continue
        kept.append(x)
        if isinstance(x, str):
            seen.append(x)
    return kept, gone


def sig(line):
    """A line's fingerprint - its emoji and its numbers - so a line the guard re-worded is still known as itself."""
    t = str(line or "")
    return (t[:1] + "|" + ",".join(re.findall(r"\d+(?:\.\d+)?", t)))[:80]


BEST_WIN_OVER = 25.0         # 🏆 a win worth naming: over a team rated this far above tonight's opponent ...
BEST_WIN_MIN = 1500.0        # ... and no worse than an average team


def best_win(lg, gu, tid, oid, e, us, them):
    """🏆 Our best win this season, when it came over a team rated above tonight's opponent - said as the game it was
    (the score, the team), never as a rating."""
    if e is None or lg not in ("ncaab", "ncaaf") or not gu:
        return None
    tid = str(tid)
    best = None
    for g in gu:
        try:
            home = str(g["home"]) == tid
            pf, pa = int(g["home_score"] if home else g["away_score"]), int(g["away_score"] if home else g["home_score"])
        except (KeyError, TypeError, ValueError):
            continue
        opp = g["away"] if home else g["home"]
        if pf <= pa or str(opp) == str(oid):
            continue
        r = e.r.get(opp, 1500.0)
        if r >= max(BEST_WIN_MIN, e.r.get(oid, 1500.0) + BEST_WIN_OVER) and (best is None or r > best[0]):
            best = (r, g["away_name"] if home else g["home_name"], pf, pa, home, str(g.get("neutral")) == "1")
    if not best:
        return None
    _, nm, pf, pa, home, neutral = best
    where = "" if neutral else " at home" if home else " on the road"
    return ("best_win", [f"🏆 {us} already beat {nm} this year, {pf}-{pa}{where}.",
                         f"🏆 {us} got a {pf}-{pa} win over {nm}{where} this year. They can play with real teams.",
                         f"🏆 A {pf}-{pa} win over {nm}{where} is already on the board for {us} this year."], False, 7.2)


def sell_facts(leg, v, g, us, them, tid, oid, lg, s_ours, s_theirs, real=None, e=None, fair=False):
    """The card's sell lines, best first: [(line, is_reason, key, every way to say it)] - `real(games, tid)` strips a college hoops team's
    non-D1 tune-ups (sports_breakdown_v24._real); `fair`: the league is one where schedules differ wildly (college)."""
    if not SELL or lg not in _READ:
        return []
    gu = real(s_ours, tid) if real else s_ours
    gt = real(s_theirs, oid) if real else s_theirs
    d1 = "d1" if lg == "ncaab" else ""
    try:
        pu, pt = profile(lg, gu, tid), profile(lg, gt, oid)
    except Exception:                                     # noqa: BLE001 - a box file we can't read is no line, never a crash
        return []
    cmp_ok = not fair or fair_cmp(gu, gt, tid, oid, e)
    made = []
    try:
        if lg in ("ncaab", "nba"):
            pt5 = profile(lg, gt, oid, last=5)
            made = hoops_lines(lg, us, them, pu, pt, pt5, leg, d1, cmp_ok)
        elif lg == "nhl":
            made = hockey_lines(us, them, pu, pt, leg)
        elif cmp_ok:
            made = football_lines(us, them, pu, pt, leg)
        bw = best_win(lg, gu, tid, oid, e, us, them)
        if bw:
            made.append(bw)
        who = leg.get("opp_top_out_who")                  # 11/23 board check (the Washington +11.5 stack play: its one
        if lg == "ncaab" and leg.get("opp_top_out") and who and who[0]:   # named reason - BYU's top scorer sat out their
            nm, ppg = who[0], who[1]                      # last game - was nowhere on the card: CARD AUDIT "NO WHY")
            made.append(("topout", [f"🪑 {_pos(them)} top scorer {nm} ({ppg} a game) sat out their last game.",
                                    f"🪑 {nm} is {_pos(them)} top scorer at {ppg} a game and he didn't play their last one.",
                                    f"🪑 {them} played their last game without {nm}, their top scorer ({ppg} a game)."],
                         True, 9.6))
    except Exception:                                     # noqa: BLE001
        made = []
    made.sort(key=lambda m: (not m[2], -m[3]))
    out = []
    for key, ways, reason, _w in made:
        line = v.say("sell_" + key, ways, fact=True) if v is not None else ways[0]
        if line:
            out.append((line, bool(reason), key, list(ways)))
    return out


LEAD_MAX = 150


def lead_of(line, us, lean=False, seed=""):
    """A body line as the line under the pick: our side first, then the fact (one line - past LEAD_MAX its first
    sentence). None when even that runs long."""
    em, _, rest = str(line or "").partition(" ")
    if not rest:
        return None
    heads = [f"We lean {us}:", f"Lean {us}:"] if lean else [f"Give me {us}:", f"We on {us}:", f"{us} the side:", f"Riding {us}:"]
    head = heads[sum(map(ord, str(seed))) % len(heads)]
    if rest.startswith(us + " "):                         # (the fact already opens on us: a tail, not a head)
        tails = [f"We lean {us}."] if lean else [f"Give me {us}.", f"We on {us}.", f"{us} the side.", f"Riding {us}."]
        t = f"{em} {rest} {tails[sum(map(ord, str(seed))) % len(tails)]}"
        if len(t) <= LEAD_MAX:
            return t
        return f"{em} {rest}" if len(f"{em} {rest}") <= LEAD_MAX else None
    t = f"{em} {head} {rest}"
    if len(t) > LEAD_MAX:
        first = re.split(r"(?<=[.!?])\s+", rest)[0]
        t = f"{em} {head} {first}"
    return t if len(t) <= LEAD_MAX else None


# ---------------------------------------------------------------------------------------------------------------------
# the standing check (sports_card_check runs these on every render)
# ---------------------------------------------------------------------------------------------------------------------
_PAIRS = (("fgm", "fga"), ("tpm", "tpa"), ("o_fgm", "o_fga"), ("o_tpm", "o_tpa"), ("ppg", "ppo"), ("o_ppg", "o_ppo"))
_MARGINS = (("reb", "o_reb"), ("shots", "o_shots"))
SEASON_SAID = re.compile(r"against D1 teams|this year|on the year|on the season", re.I)
WINDOW_SAID = re.compile(r"over (?:their|the) last \d|last \d+ games|a night over", re.I)


KEYS_OF = {   # the box-score numbers a line about one stat may say (its own stat's - never any number in the box)
    "glass": ("reb", "oreb"), "turnover": ("to", "stl"), "three": ("tpm", "tpa"), "paint": ("paint",), "line": ("fta", "ftm"),
    "shooting": ("fgm", "fga", "pf", "pa"), "shots": ("shots",), "power play": ("ppg", "ppo"), "ground": ("rush",),
    "break": ("fast",), "assists": ("ast", "fgm"), "air": ("pass",), "third": ("third_m", "third_a"), "sacks": ("sacked",),
    "yards": ("yds",)}


def allowed(*profiles, stat=None):
    """Every number a sell line may carry, off the profiles it was built from (`stat`: only that stat's numbers)."""
    ok = set()
    want = KEYS_OF.get(stat)
    for p in profiles:
        if not p:
            continue
        n = p["n"]
        ok.add(n)
        for k, val in p.items():
            if k != "n" and (want is None or k.replace("o_", "", 1) in want):
                ok.add(round(val))
                ok.add(round(val / n))
        for a, b in _PAIRS:
            if p.get(b) and (want is None or a.replace("o_", "", 1) in want):
                ok.add(round(100.0 * p[a] / p[b]))
        for a, b in _MARGINS:
            if p.get(a) is not None and p.get(b) is not None and (want is None or a in want):
                ok.add(round(abs(p[a] - p[b]) / n))
        if p.get("o_paint") and p.get("pa") and (want is None or "paint" in want):
            ok.add(round(100.0 * p["o_paint"] / p["pa"]))    # (11/23: the paint's share of the points a team gives up)
        if p.get("o_ppo") is not None and p.get("o_ppg") is not None and (want is None or "ppo" in want):
            ok.add(round(p["o_ppo"] - p["o_ppg"]))
    return ok


def is_sell(line):
    """A box-score matchup line this module wrote (a season number, not another pool's last-N count)."""
    t = str(line or "")
    if t.startswith("🏆"):
        return False                                      # (a game with its score: the fact check reads it)
    if t.startswith(SELL_EM):
        return True
    return t.startswith(STAT_EM) and not t.startswith("📊") and bool(SEASON_SAID.search(t)) and not WINDOW_SAID.search(t) \
        and not str(stat_of(t) or "score").startswith("score")


def numbers_wrong(line, us, them, lg, gu, gt, tid, oid):
    """'' when every number in a sell line is what the box scores say for these two teams, else the first that isn't."""
    if not is_sell(line):
        return ""
    try:
        ps = (profile(lg, gu, tid), profile(lg, gt, oid), profile(lg, gt, oid, last=5))
    except Exception:                                     # noqa: BLE001
        return ""
    if not ps[0] and not ps[1]:
        return "box-score numbers for teams we hold no box scores on"
    ok = allowed(*ps, stat=stat_of(line))
    t = str(line)
    for nm in sorted((x for x in (us, them) if x), key=len, reverse=True):
        t = t.replace(nm, " ")
    t = t.replace("D1", " ")
    for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])", t):
        if "." in x or round(float(x)) not in ok:
            return x
    return ""


def reason_backed(line, leg):
    """What a card line is, for the count the owner asked for (11/22 - "the breakdowns basically need to sell our picks
    why we taking them"): "reason" - it says a reason the leg carries (a sold line the engine's reasons point at, the
    men they're missing, the back-to-back, the favorite's last loss, the puck luck, the trip); "matchup" - a checkable
    matchup fact for our side (the box-score edges, the game these two already played, a common opponent); "" - form /
    a record / a scorer."""
    t = str(line or "")
    if not t:
        return ""
    rs = " ".join(str(x) for x in (leg.get("reasons") or [])).lower()
    if sig(t) in set(leg.get("sold") or []):
        return "reason"
    if t.startswith(("🚑", "📉")) and ("missing key players" in rs or "banged-up" in rs):
        return "reason"
    if t.startswith(("😴", "⏳", "😮")) and ("back-to-back" in rs or leg.get("rested_vs_b2b")):
        return "reason"
    if t.startswith("🛌") and ("rested" in rs or "bye" in rs):
        return "reason"
    if t.startswith(("🍀", "🏹")) and leg.get("pdo") is not None:
        return "reason"
    if t.startswith(("🥊", "📅")) and (leg.get("dog_ctx") or {}).get("opp_won") is False \
            and leg.get("league") in ("nfl", "ncaaf", "ncaab") and (leg.get("odds") or 0) > 0 and str(leg.get("opp") or "\x00") in t:
        return "reason"
    if t.startswith("🧳") and any(c.get("k") == "trip" and c.get("who") == "them" for c in leg.get("ctx") or []):
        return "reason"
    if t.startswith("🎯") and "qb play" in rs:
        return "reason"
    if t.startswith("🧱") and "goalie" in rs:
        return "reason"
    if t.startswith("🚀") and "blowout win" in rs:
        return "reason"
    if "altitude" in rs and re.search(r"feet up|thin air|altitude", t, re.I):
        return "reason"
    if t.startswith("📅") and "tune-up" in rs and "non-D1" in t:
        return "reason"                                   # (the tune-up angle: ours off a non-D1 game, theirs off a real one)
    if t.startswith("📋") and "Division I" in t:
        return "matchup"
    if t.startswith(("🆚", "🔁", "🏆", "🧾", "🎬")) or is_sell(t) or (t.startswith(STAT_EM) and not t.startswith("📊")):
        return "matchup"
    return ""


def lead_from(sold_line, us, lean=False, seed=""):
    """The line under the pick off one sell line: the wording that opens on OUR side when there is one (a tail goes on),
    else one without a colon of its own (a head goes on). None when nothing fits on one line."""
    line, ways = sold_line[0], list(sold_line[3]) if len(sold_line) > 3 else []
    opens = [w for w in ways if w.partition(" ")[2].startswith(us + " ")]
    plain = [w for w in ways if w not in opens and ":" not in w]
    for w in opens + plain + [line]:
        if w not in opens and ":" in w.partition(" ")[2][:60] and w is not line:
            continue
        t = lead_of(w, us, lean, seed)
        if t and t.count(":") <= 1:
            return t
    return lead_of(line, us, lean, seed)
