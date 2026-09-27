"""The full breakdown behind a pick: the facts the engine weighed, in plain words, frozen at posting time.
Shown on the dashboard behind a "Full breakdown" tap."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_model as sm
import sports_players as sp

PT = ZoneInfo("America/Los_Angeles")
VERSION = 13          # bump when the wording changes: posted plays get their breakdown rewritten (never the pick)


def _t(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _am(a):
    return f"+{a}" if a > 0 else str(a)


def _team_games(fin, tid):
    return [g for g in fin if tid in (g["home"], g["away"])]


def _line(g, tid):
    """'W 27-20 vs Lions' from tid's point of view."""
    home = g["home"] == tid
    us, them = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    opp = g["away_name"] if home else g["home_name"]
    res = "W" if us > them else "L" if us < them else "T"
    return f"{res} {us}-{them} {'vs' if home else '@'} {opp}"


def _season(games_of_team, before):
    """This season's games: walk back until a break of 75+ days (the off-season)."""
    out = []
    last = before
    for g in reversed(games_of_team):
        t = _t(g["start"])
        if (last - t).days > sm.BREAK_DAYS:
            break
        out.append(g)
        last = t
    return list(reversed(out))


def _record(gs, tid):
    w = sum(1 for g in gs if _line(g, tid).startswith("W"))
    lo = sum(1 for g in gs if _line(g, tid).startswith("L"))
    t = len(gs) - w - lo
    return f"{w}-{lo}" + (f"-{t}" if t else "")


def _streak(gs, tid):
    """'won 5 straight' / 'lost 3 straight' / ''."""
    if not gs:
        return ""
    last = _line(gs[-1], tid)[0]
    n = 0
    for x in reversed(gs):
        if _line(x, tid)[0] != last:
            break
        n += 1
    if n < 2 or last == "T":
        return ""
    return f"{'won' if last == 'W' else 'lost'} {n} straight"


def _names(rows, k=3):
    names = [n for n, _, _ in rows[:k]]
    more = len(rows) - len(names)
    return ", ".join(names) + (f" +{more} more" if more > 0 else "")


class Voice:
    """Picks a way to say each line: different wording from game to game and day to day, and never the same
    wording twice on one board (share one `used` set across a board's breakdowns)."""

    def __init__(self, seed, used=None):
        self.seed, self.used, self.mine = seed, used if used is not None else set(), []

    def say(self, key, options):
        """A fresh way to say it, or "" (the line is dropped) when every way is already taken on this board."""
        start = sum(map(ord, f"{self.seed}|{key}")) % len(options)
        for i in range(len(options)):
            n = (start + i) % len(options)
            tag = f"{key}:{n}"
            if tag not in self.used:
                self.used.add(tag)
                self.mine.append(tag)
                return options[n]
        return ""


def breakdown(leg, games, elo, injuries, used=None):
    """A plain-talk case for one leg: a list of short bullets ending with the bottom line."""
    g = games[leg["game_id"]]
    lg, side = leg["league"], leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg["team"], leg["opp"]
    start = _t(g["start"])
    fin = [x for x in sm.finals(games, lg) if _t(x["start"]) < start]
    ours, theirs = _team_games(fin, tid), _team_games(fin, oid)
    s_ours, s_theirs = _season(ours, start), _season(theirs, start)
    v = Voice(f"{g['id']}|{start:%Y-%m-%d}|{side}", used)
    pro = lg in ("nfl", "nba", "mlb", "nhl")
    the_us, the_them = (f"the {us}", f"the {them}") if pro else (us, them)
    if ours and theirs and (start - _t(ours[-1]["start"])).days - (start - _t(theirs[-1]["start"])).days < 2:
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "better rested"]
    out, said = [], set()          # said: reasons already used as a "because", so no line repeats another
    leg["bd_tags"] = v.mine        # which wordings this breakdown used (so the rest of the board avoids them)

    # form
    rec_u = _record(s_ours, tid) if s_ours else None
    heat = _streak(ours, tid)
    n_hot = int(heat.split()[1]) if heat.startswith("won") else 0
    if rec_u and n_hot >= 2:
        said.add("hotter recent form")
        out.append(v.say("hot", [f"🔥 {us} are {rec_u} and on a {n_hot}-game heater.",
                                  f"🔥 {us} ({rec_u}) have won {n_hot} straight and they're rolling.",
                                  f"🔥 {us} are rolling — {n_hot} wins in a row, {rec_u} on the year.",
                                  f"🔥 {us} can't stop winning: {n_hot} straight, {rec_u} overall.",
            f"🔥 {us} are cooking — {n_hot} straight W's, {rec_u} overall.",
            f"🔥 Heat check: {us} have won {n_hot} in a row ({rec_u})."]))
    elif rec_u:
        out.append(v.say("rec", [f"📋 {us} come in at {rec_u}.", f"📋 {us} are sitting at {rec_u}.",
                                  f"📋 {rec_u} so far for {us}.",
            f"📋 {us} roll in at {rec_u}.",
            f"📋 Record check: {us} {rec_u}.",
            f"📋 {us} are {rec_u} right now."]))
    if s_theirs:
        rec_t = _record(s_theirs, oid)
        cold = _streak(theirs, oid)
        n_cold = int(cold.split()[1]) if cold.startswith("lost") else 0
        w_t = sum(1 for x in s_theirs if _line(x, oid).startswith("W"))
        rating_t = elo[lg].r.get(oid, 1500.0) if elo.get(lg) is not None else 1500.0
        trash = (len(s_theirs) >= 3 and w_t / len(s_theirs) < 0.35) or n_cold >= 3 or rating_t < 1420
        if n_cold >= 2 and not trash:                   # the trash-talk line below covers the really bad ones
            out.append(v.say("cold", [f"🧊 {them} are {rec_t} and ice cold — {n_cold} straight L's.",
                                       f"🧊 {them} have dropped {n_cold} in a row ({rec_t}).",
                                       f"🧊 {n_cold} straight losses for {them}. Not a good look.",
                                       f"🧊 {them} ({rec_t}) keep taking L's — {n_cold} straight.",
            f"🧊 {them} ({rec_t}) are in a slump — {n_cold} straight.",
            f"🧊 {them} forgot how to win: {n_cold} straight L's."]))

    # strength
    e = elo.get(lg)
    if e is not None:
        home_edge = 0 if str(g.get("neutral")) == "1" else (e.hfa if side == "home" else -e.hfa)
        gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0) + home_edge      # same yardstick as the card's reasons
        said.add("the stronger team")                   # said here either way (better / even / worse): not again later
        if gap > 60:
            out.append(v.say("better", [f"💪 {us} are straight up the better team right now.",
                                         f"💪 This is a mismatch — {us} are just better.",
                                         f"💪 {us} are the better squad and it's not that close.",
                                         f"💪 On talent and results, {us} have the edge all day.",
            f"💪 {us} are the better squad, period.",
            f"💪 {us} got more dog in them than {them} right now.",
            f"💪 Talent gap goes {us}' way — big time."]))
        elif gap > 15:
            out.append(v.say("better_s", [f"💪 {us} are the better squad, even if it's closer than it looks.",
                                           f"💪 {us} have the edge on paper — not a blowout, but it's there.",
                                           f"💪 Slight edge {us} on who's actually better.",
            f"💪 {us} have a little more juice than {them}.",
            f"💪 Close-ish on paper, but {us} are better.",
            f"💪 {us} got the upper hand, not by a mile but it's there."]))
        elif gap < -15:
            out.append(v.say("worse", [f"🐺 {them} look better on paper — that's exactly why we're getting this juicy price on {us}.",
                                        f"🐺 Everybody's on {them}. That's how we get {us} at this number.",
                                        f"🐺 {them} are the name brand here, but the price on {us} is too good to pass.",
            f"🐺 On paper it's {them}. On the field? We like {us} at this price.",
            f"🐺 {them} get all the love — that's why {us} are sitting at this number."]))
        else:
            out.append(v.say("even", ["⚖️ Pretty even matchup, so we're riding the better number.",
                                       "⚖️ These two are close, so the price is what makes the play.",
                                       "⚖️ Evenly matched on paper — the value's on our side.",
            "⚖️ Coin-flip matchup on paper. The number makes it ours.",
            "⚖️ Dead even talent-wise — the price is the play.",
            "⚖️ No clear better team, so we take the better number."]))

    # talk our talk when the other side's been bad (only when the numbers back it up)
    if s_theirs:
        w = sum(1 for x in s_theirs if _line(x, oid).startswith("W"))
        rating_them = e.r.get(oid, 1500.0) if e is not None else 1500.0
        n_cold = int(_streak(theirs, oid).split()[1]) if _streak(theirs, oid).startswith("lost") else 0
        if (len(s_theirs) >= 3 and w / len(s_theirs) < 0.35) or n_cold >= 3 or rating_them < 1420:
            rec = _record(s_theirs, oid)
            out.append(v.say("trash", [f"🗑️ {them} have been complete ass lately — {rec} and it ain't getting prettier.",
                                        f"🗑️ Straight up, {them} are trash right now ({rec}).",
                                        f"🗑️ {them} can't get out of their own way ({rec}).",
                                        f"🗑️ {them} are a mess right now. {rec} says it all.",
                                        f"🗑️ Nothing about {them} scares us ({rec}).",
            f"🗑️ {them} been looking like a JV squad ({rec}).",
            f"🗑️ {them} are straight garbage right now ({rec}).",
            f"🗑️ Watching {them} lately hurts ({rec})."]))

    # last games: just the latest scores - the form/streak lines above already cover runs
    if ours:
        last_us = _line(ours[-1], tid)
        both = f"{us} {last_us}" + (f" · {them} {_line(theirs[-1], oid)}" if theirs else "")
        out.append(v.say("latest", [f"📅 Latest: {both}.", f"📅 Last time out: {both}.", f"📅 Most recent games: {both}.",
                                     f"📅 Where they're coming from: {both}.", f"📅 Last week's tape: {both}." if lg in ("nfl", "ncaaf")
                                     else f"📅 Last outing: {both}.", f"📅 Previous game: {both}.", f"📅 Fresh off: {both}."]))

    # head to head
    h2h = [x for x in ours if oid in (x["home"], x["away"])]
    if h2h:
        last3 = h2h[-3:]
        w = sum(1 for x in last3 if _line(x, tid).startswith("W"))
        if 2 * w >= len(last3) and len(last3) > 1:
            out.append(v.say("h2h", [f"🆚 {us} own this matchup — won {w} of the last {len(last3)}.",
                                      f"🆚 {us} have had {them}'s number: {w} of the last {len(last3)}.",
                                      f"🆚 History's on our side — {w} of the last {len(last3)} meetings went {us}' way.",
            f"🆚 {us} been owning {them} lately — {w} of the last {len(last3)}.",
            f"🆚 {them} can't figure {us} out: {w} of {len(last3)} to {us}."]))
        elif w == 1 and len(last3) == 1:
            out.append(v.say("h2h1", [f"🆚 {us} got 'em last time: {_line(h2h[-1], tid)}.",
                                       f"🆚 Last meeting went {us}' way ({_line(h2h[-1], tid)}).",
            f"🆚 {us} handled {them} last time ({_line(h2h[-1], tid)}).",
            f"🆚 Last time these two met, {us} took it ({_line(h2h[-1], tid)})."]))

    # the key players: QB / starting pitcher / goalie (the fun part)
    rows = sp.CACHE.get(lg) or []
    role = sp.ROLE.get(lg)
    if rows and role:
        def who(team_side, tid_):
            if role == "SP":
                return g.get("sp_" + team_side) or None
            return sp.last_starter(rows, tid_, g["start"])
        for team_side, t_id, ours_ in ((other, oid, False), (side, tid, True)):
            name = who(team_side, t_id)
            if not name:
                continue
            txt, mood = sp.form_line(lg, name, rows, g["start"])
            if not txt:
                continue
            if not ours_ and mood == "cold":
                out.append(v.say(role + "_cold", {
                    "QB": [f"🗑️ {name} has been complete booty cheeks — {txt}.",
                           f"🗑️ {name} has been throwing it to the other team — {txt}.",
                           f"🗑️ {name} looks lost out there: {txt}."],
                    "SP": [f"💣 {name} has been getting shelled — {txt}.",
                           f"💣 {name} has been getting lit up: {txt}.",
                           f"💣 Hitters are teeing off on {name} — {txt}."],
                    "G": [f"🥅 {name} has been leaky as hell — {txt}.",
                          f"🥅 {name} can't stop a beach ball right now: {txt}.",
                          f"🥅 Pucks keep getting past {name} — {txt}."]}[role]))
            elif ours_ and mood == "hot":
                out.append(v.say(role + "_hot", {
                    "QB": [f"🎯 {name} has been cooking — {txt}.",
                           f"🎯 {name} is locked in: {txt}.",
                           f"🎯 {name} is slinging it — {txt}."],
                    "SP": [f"🔥 {name} has been dealing — {txt}.",
                           f"🔥 {name} is on a roll: {txt}.",
                           f"🔥 Nobody's touching {name} lately — {txt}."],
                    "G": [f"🧱 {name} has been a brick wall — {txt}.",
                          f"🧱 {name} is standing on his head: {txt}.",
                          f"🧱 Good luck scoring on {name} — {txt}."]}[role]))

    # situational spots the engine learned from 10 seasons of games
    rsn = leg.get("reasons") or []
    if "revenge game" in rsn:
        out.append(v.say("revenge", [f"😤 Revenge game — {us} lost the last meeting and they haven't forgotten.",
                                      f"😤 {us} owe {them} one from last time. Payback's coming.",
                                      f"😤 Get-back game for {us}. They took an L to {them} last time.",
                                      f"😤 {us} been waiting on this rematch."]))
        said.add("revenge game")
    if "letdown spot for the opponent" in rsn:
        out.append(v.say("letdown", [f"🪤 Letdown spot for {them} — fresh off a blowout win, they're gonna come out flat.",
                                      f"🪤 {them} just blew somebody out. Classic letdown game.",
                                      f"🪤 {them} are riding high off a big W. That's when teams slip.",
                                      f"🪤 Trap game for {them} after that blowout."]))
        said.add("letdown spot for the opponent")
    if "rolling off a blowout win" in rsn:
        out.append(v.say("momentum", [f"🚀 {us} just blew somebody out — teams like that keep rolling.",
                                       f"🚀 {us} are coming in hot off a blowout. Momentum's real.",
                                       f"🚀 Blowout last time out for {us}. They're feeling themselves."]))
        said.add("rolling off a blowout win")
    if "coming off a bye" in rsn:
        out.append(v.say("bye", [f"🛌 {us} are fresh off a bye — rested and game-planned up.",
                                  f"🛌 Extra week to prep for {us}. That matters.",
                                  f"🛌 Bye week in the rearview for {us}. Fresh legs, full playbook."]))
        said.add("coming off a bye")
    if "opponent on a short week" in rsn:
        out.append(v.say("short", [f"⏱️ {them} are on a short week. Not much time to prep.",
                                    f"⏱️ Short week for {them} — tired bodies, rushed game plan.",
                                    f"⏱️ {them} barely had time to recover. Short week."]))
        said.add("opponent on a short week")

    # home / road
    if side == "home":
        out.append(v.say("home", [f"🏟️ {us} are at home, about to go to work.",
                                   f"🏟️ {us} get to do it in front of their own crowd.",
                                   f"🏟️ Home game for {us} — their building, their rules.",
                                   f"🏟️ {us} are home tonight and ready to handle business.",
            f"🏟️ {us} got the home crowd behind them.",
            f"🏟️ Home game — {us} don't lose many in their own house.",
            f"🏟️ {us} at home, fans rocking. We like it."]))
    else:
        out.append(v.say("road", [f"🧳 {us} are on the road — doesn't scare us.",
                                   f"🧳 Road game for {us}, but they travel just fine.",
                                   f"🧳 {us} walk into a hostile building — we're not worried.",
                                   f"🧳 Away game for {us}. The numbers still like them.",
            f"🧳 {us} on the road, but this team doesn't care where they play.",
            f"🧳 Away game — {us} bring their own energy.",
            f"🧳 {us} hit the road. Doesn't matter to us."]))

    # rest
    if ours and theirs:
        d_us, d_them = (start - _t(ours[-1]["start"])).days, (start - _t(theirs[-1]["start"])).days
        if d_them <= 1 < d_us:
            out.append(v.say("b2b", [f"😴 {them} played yesterday — tired legs. {us} are fresh.",
                                      f"😴 {them} are on a back-to-back; {us} had the night off.",
                                      f"😴 Short rest for {them}, full tank for {us}.",
            f"😴 {them} are running on fumes — played last night.",
            f"😴 Back-to-back for {them}. Tired legs, cold shooting."]))
        elif d_us - d_them >= 2:
            gap_d = d_us - d_them
            out.append(v.say("rest", [f"🛌 {us} had {gap_d} more days off than {them}.",
                                       f"🛌 Rest edge: {us} got {gap_d} extra days to recover.",
                                       f"🛌 {us} come in with {gap_d} more days of rest.",f"🛌 {us} are the more rested squad.", f"🛌 {us} had extra days to get right.",
                                       f"🛌 Rest edge goes to {us}.",
            f"🛌 {us} are well-rested and ready.",
            f"🛌 Extra rest for {us} — fresh legs."]))

    # pitchers
    if lg == "mlb" and (g.get("sp_home") or g.get("sp_away")):
        ps, po = g.get("sp_" + side) or "TBA", g.get("sp_" + other) or "TBA"
        out.append(v.say("bump", [f"⚾ On the bump: {ps} for {us}, {po} for {them}.",
                                   f"⚾ Pitching matchup: {ps} ({us}) vs {po} ({them}).",
                                   f"⚾ {ps} takes the ball for {us}; {them} go with {po}.",
            f"⚾ {ps} gets the ball for {us} against {po}.",
            f"⚾ It's {ps} for {us}, {po} for {them}."]))

    # injuries
    inj = (injuries or {}).get(lg)
    if inj:
        ours_out, theirs_out = sd.team_injuries(inj, tid, us), sd.team_injuries(inj, oid, them)
        key_them = sd.team_key_out(inj, oid, them, lg)
        if key_them:
            pos, nm = key_them[0][1], key_them[0][0]
            out.append(v.say("keyout", [f"🚑 {them} are rolling without their starting {pos} ({nm}).",
                                         f"🚑 No {nm} for {them} — that's their starting {pos}.",
                                         f"🚑 {them} are down their starting {pos}, {nm}."]))
        if theirs_out and len(theirs_out) > len(ours_out):
            out.append(v.say("banged", [f"🚑 {them} are hella banged up ({_names(theirs_out)}).",
                                         f"🚑 {them}' injury list is stacking up: {_names(theirs_out)}.",
                                         f"🚑 {them} are missing bodies — {_names(theirs_out)}.",
            f"🚑 {them} are dealing with injuries: {_names(theirs_out)}.",
            f"🚑 {them} are short-handed ({_names(theirs_out)})."]))
        elif not ours_out:
            out.append(v.say("healthy", [f"✅ {us} are healthy — nobody important sitting.",
                                          f"✅ Full squad for {us}.", f"✅ {us} have everybody available.",
            f"✅ {us} are at full strength.",
            f"✅ Nobody big missing for {us}."]))

    # sharp money
    op, now = sm._int(g.get(f"ml_{side}_open")), sm._int(g.get(f"ml_{side}"))
    if op is not None and now is not None and op != now and sd.implied(now) > sd.implied(op):
        out.append(v.say("sharp", [f"💰 Sharp money is on us: {us} opened {_am(op)}, now {_am(now)}.",
                                    f"💰 The pros are hammering {us} — {_am(op)} at open, {_am(now)} now.",
                                    f"💰 The line moved our way ({_am(op)} → {_am(now)}). Smart money agrees.",
                                    f"💰 Money's been pouring in on {us}: {_am(op)} to {_am(now)}.",
            f"💰 Big money moved {us} from {_am(op)} to {_am(now)}. We like the company.",
            f"💰 {us} went from {_am(op)} to {_am(now)} — the pros see it too."]))

    # sharp money going the other way and we still like our side: say it our way, with a quick reason
    op_o, now_o = sm._int(g.get(f"ml_{other}_open")), sm._int(g.get(f"ml_{other}"))
    if op is not None and now is not None and sm.logit(sd.implied(op)) - sm.logit(sd.implied(now)) >= 0.08:
        move = f" ({_am(op_o)} → {_am(now_o)})" if op_o is not None and now_o is not None else ""
        why = next((WHY[r].format(us=us, them=them) for r in leg.get("reasons") or [] if r in WHY and r not in said),
                   NO_WHY)
        said.update(r for r in leg.get("reasons") or [] if WHY.get(r, "").format(us=us, them=them) == why)
        out.append(_nowhy(v.say("fade", [
            f"💸 Sharp money's been coming in on {the_them}{move}, but they must be some clowns. We're on {the_us} — {why}.",
            f"💸 The so-called sharps are all over {the_them}{move}. We're fading the clowns and taking {the_us} — {why}.",
            f"💸 Line's moving toward {the_them}{move}. Let 'em — we still like {the_us}, {why}.",
            f"💸 Money's pouring in on {the_them}{move}. They must've lost their minds — we got {the_us}, {why}.",
            f"💸 Everybody's jumping on {the_them}{move}. They're tweaking — we're riding {the_us}, {why}.",
            f"💸 The market's leaning {the_them}{move}. Somebody's about to learn a lesson — we're on {the_us}, {why}."])))

    # the public: fading them or riding with them
    pub = public_side(leg, g)
    why_pub = next((WHY[r].format(us=us, them=them) for r in leg.get("reasons") or [] if r in WHY and r not in said),
                   NO_WHY)
    if pub == "fade":
        out.append(_nowhy(v.say("pub_fade", [
            f"🤡 {_cap(the_them)} are the clear favorite and the public's all over 'em. Don't be a sheep — we're on {the_us}, {why_pub}.",
            f"🤡 The public is all over {the_them}. Dummies are about to lose their money — we're on {the_us}, {why_pub}.",
            f"🤡 Everybody and their mama is on {the_them}. Not us — we got {the_us}, {why_pub}.",
            f"🤡 The sheep are lining up for {the_them}. We're not sheep — we're on {the_us}, {why_pub}.",
            f"🤡 Crowd's on {the_them}. We're riding {the_us} and the engine — {why_pub}.",
            f"🤡 Public's hammering {the_them} like it's free money. It ain't — we got {the_us}, {why_pub}.",
            f"🤡 All the casuals love {the_them}. We're not casuals — {the_us} all day, {why_pub}."])))
    elif pub == "ride":
        out.append(_nowhy(v.say("pub_ride", [
            f"🤝 Riding with the public on {the_us} — sometimes the public gotta win, {why_pub}.",
            f"🤝 Public's on {the_us} too, and this time they're not dummies — {why_pub}.",
            f"🤝 Even a broken clock is right twice a day — the public got {the_us} right, {why_pub}.",
            f"🤝 We're with the crowd on {the_us} and not ashamed of it — {why_pub}.",
            f"🤝 Public side on {the_us}, but we got our own reasons — {why_pub}.",
            f"🤝 We're riding with the crowd on {the_us}. Sometimes they get it right — {why_pub}."])))

    # bottom line
    need, have = 1 / leg["dec"], leg["p"]
    bet = f"{us} {leg['line']:+g}" if leg["market"] == "spread" else us
    price = f"{bet} ({_am(leg['odds'])})"
    if _odds_words(need) != _odds_words(have):
        out.append(v.say("bottom", [
            f"✅ Bottom line: Vegas has {price} priced like {_odds_words(need)}. The engine sees {_odds_words(have)}. That's the value — trust the algorithm.",
            f"✅ Bottom line: the book treats {price} like {_odds_words(need)}; we've got it closer to {_odds_words(have)}. Easy call.",
            f"✅ Bottom line: {price} should be more like {_odds_words(have)}, and Vegas is pricing {_odds_words(need)}. We'll take that all day.",
            f"✅ Bottom line: {_odds_words(have)} in our book vs {_odds_words(need)} at the window for {price}. Trust the algorithm.",
            f"✅ Bottom line: Vegas says {_odds_words(need)} on {price}, the engine says {_odds_words(have)}. Easy money if the engine's right.",
            f"✅ Bottom line: {price} is priced like {_odds_words(need)} — we see {_odds_words(have)}. That gap is the whole play.",
            f"✅ Bottom line: book says {_odds_words(need)}, we say {_odds_words(have)}. We ride {price}.",
            f"✅ Bottom line: {_odds_words(have)} for us vs {_odds_words(need)} at the window on {price}. Value all day."]))
    else:
        out.append(v.say("bottom_s", [
            f"✅ Bottom line: Vegas has {price} priced like {_odds_words(need)}, but everything above tips it our way. Small edge, real edge.",
            f"✅ Bottom line: close to {_odds_words(need)} at the book, but the details break our way on {price}.",
            f"✅ Bottom line: {price} isn't a slam dunk, it's a smart number — and the little things all point our way.",
            f"✅ Bottom line: {price} is a thin edge, but it's an edge — and the details back it.",
            f"✅ Bottom line: no blowout expected on {price}, just a smart number with everything tilting our way.",
            f"✅ Bottom line: {price} ain't flashy. It's just the right side.",
            f"✅ Bottom line: the book has {price} close, but the small stuff breaks our way."]))
    lines = [x for x in out if x]
    if len(lines) > 2:
        import random
        rnd = random.Random(f"{g['id']}|{start:%Y-%m-%d}|{side}|shape")
        body, bottom = lines[:-1], lines[-1]
        keep = max(4, len(body) - rnd.randint(0, 2))          # not every pick gets every line
        must = {i for i, x in enumerate(body) if x[:1] in "🤡🤝💸🚑" or x.startswith("🗑️")}   # the spicy stuff stays
        drop = [i for i in range(len(body)) if i not in must]
        rnd.shuffle(drop)
        gone = set(drop[:max(0, len(body) - keep)])
        body = [x for i, x in enumerate(body) if i not in gone]
        rnd.shuffle(body)
        lines = body + [bottom]
    return lines


WHY = {   # the pick's reasons, said as a quick "because"
    "the stronger team": "they're the better team",
    "hotter recent form": "they're the hotter team",
    "better rested": "they got extra days of rest",
    "opponent on a back-to-back": "{them} are on tired legs",
    "opponent missing key players": "{them} are banged up",
    "revenge game": "they owe these guys one",
    "rolling off a blowout win": "they're rolling off a blowout",
    "letdown spot for the opponent": "{them} are due for a letdown",
    "coming off a bye": "they're fresh off a bye",
    "opponent on a short week": "{them} are on a short week",
    "better starting pitcher": "we've got the better arm on the mound",
    "better QB play lately": "our QB's been playing better",
    "hotter goalie": "our goalie's been hotter",
}


NO_WHY = "\u00a7"     # placeholder: no fresh reason left, so the line ends on our side instead of a filler "because"


def _nowhy(line):
    import re
    return re.sub(r"[\s\u2014:.,]*\u00a7\.?$", ".", line) if NO_WHY in line else line


def _cap(x):
    return x[:1].upper() + x[1:]


def public_side(leg, g):
    """'fade' when we're on the dog against a clear favorite (the public loves favorites), 'ride' when we're on the
    favorite, None near pick'em. Real ticket counts are paywalled, so the favorite stands in for the public."""
    if leg["market"] != "ml":
        return None
    other = "away" if leg["side"] == "home" else "home"
    ours, theirs = sm._int(g.get(f"ml_{leg['side']}")), sm._int(g.get(f"ml_{other}"))
    if ours is None or theirs is None:
        return None
    if ours >= 105 and theirs <= -125:
        return "fade"
    if ours <= -125:
        return "ride"
    return None


def _odds_words(p):
    """0.5 -> 'a coin flip', 0.62 -> 'about 6 in 10', 0.3 -> 'about 3 in 10'."""
    if abs(p - 0.5) < 0.03:
        return "a coin flip"
    n = round(p * 10)
    if n <= 1:
        return f"about 1 in {round(1 / p)}"
    return f"about {n} in 10"
