"""Phone dashboard for THE D503 SPORTS ENGINE (docs/sports/index.html).
Top: today's board (2-leg, 3-leg, lock, dog). Below: results, record, and what the engine learned.
Self-contained HTML (inline CSS/SVG, tiny JS for the "updated X min ago" light)."""
import html
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd

PT = ZoneInfo("America/Los_Angeles")
REPO = "D503therapper/autonomous-crypto-engine"
PAGE = "docs/sports/index.html"
LOOK = {   # kind -> label, accent, second accent
    "two":   ("2-LEG OF THE DAY", "#2f8bff", "#22d3ee"),
    "three": ("3-LEG OF THE DAY", "#ffc233", "#ff8a00"),
    "lock":  ("LOCK OF THE DAY", "#22e39a", "#0fb87a"),
    "dog":   ("DOG OF THE DAY", "#ff5a1f", "#ff2a2a"),
    "eight": ("8-LEG OF THE DAY", "#b36bff", "#ff4fd8"),
}
BIG_HIT = 300                 # +300 and up that cashes gets the big brag
ICON = {"two": "⚡", "three": "👑", "eight": "🎰", "lock": "🔒", "dog": "🐺"}
E = html.escape


def _am(a):
    return f"+{a}" if a > 0 else str(a)


def _money(x, sign=False):
    s = ("+" if x >= 0 else "−") if sign else ("" if x >= 0 else "−")
    return f"{s}${abs(x):,.0f}"


def _time(iso):
    t = datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT)
    return t.strftime("%-I:%M %p").replace(":00 ", " ") + " PT"


def _chip(status):
    txt = {"open": "🔒 LOCKED", "won": "CASHED ✓", "lost": "LOST", "push": "PUSH"}[status]
    return f'<span class="chip {status}">{txt}</span>'


def _the(team, league):
    """Pro teams get "the" ("the Bills"), college teams don't ("Alabama")."""
    return f"the {team}" if league in ("nfl", "nba", "mlb", "nhl") else team


def _cap(x):
    return x[:1].upper() + x[1:]


def _pick(key, options, used, k):
    """A way to say it that nobody else in this list used yet (falls back to rotating when they're all taken)."""
    for i in range(len(options)):
        n = (k + i) % len(options)
        if (key, n) not in used:
            used.add((key, n))
            return options[n]
    return options[k % len(options)]


def _live_story(e, used=None):
    """A live bet in plain talk and our lingo: the score + quarter when it went up, and how it played out.
    No two bets in the list share a phrase."""
    used = set() if used is None else used
    lg = e.get("league", "")
    m = re.match(r"(.+?) (\d+) @ (.+?) (\d+)$", str(e.get("score_at_post") or ""))
    if not m:
        return ""
    away, a_s, home, h_s = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    ours_away = e.get("side") == "away"
    us = _the(e["team"], lg)
    mine, theirs = (a_s, h_s) if ours_away else (h_s, a_s)
    per = re.search(r"(\d+)", str(e.get("clock_at_post") or ""))
    n = int(per.group(1)) if per else 0
    unit = {"nhl": "period", "ncaab": "half", "mlb": "inning"}.get(lg, "quarter")
    w = f"in the {({1: '1st', 2: '2nd', 3: '3rd'}.get(n, f'{n}th'))} {unit}" if n else "mid-game"
    k = sum(map(ord, e["team"] + str(e.get("odds"))))
    an, hn = _the(away, lg), _the(home, lg)
    score = _pick("score", [f"{_cap(an)} had {a_s}, {hn} had {h_s} {w}.", f"It was {an} {a_s}, {hn} {h_s} {w}.",
                            f"{_cap(an)} {a_s}, {hn} {h_s} {w}.", f"Score was {an} {a_s}, {hn} {h_s} {w}."], used, k)
    what = "come back" if mine < theirs else "hold on" if mine > theirs else "take it"
    res = e.get("result")
    if res in ("won", "lost"):
        thought = _pick("thought", [f"We thought {us} would {what}", f"We figured {us} would {what}", f"We said {us} would {what}",
                                    f"We knew {us} could {what}"], used, k)
    else:
        thought = _pick("riding", [f"We're riding {us} to {what}", f"We like {us} to {what}", f"We got {us} to {what}",
                                   f"We're on {us} to {what}", f"We backing {us} to {what}", f"We're with {us} to {what}",
                                   f"We think {us} {'come back' if what == 'come back' else what}"], used, k)
    best = e.get("best_odds") or e.get("odds") or 0
    if res == "won" and best >= (e.get("odds") or 0) + 40:        # the line ran long while it was up - and it cashed
        end = _pick("won_ran", [f"the line ran all the way to +{best} and they still cashed. The algorithm was right — let's fucking go. 💰",
                                f"books pushed it out to +{best} and we held. Cashed. Trust the algorithm. 💰",
                                f"it got as long as +{best} and they got it done anyway. Told y'all. 💰"], used, k)
    elif res == "won":
        end = _pick("won", ["and they did. Cashed. 💰", "and they got it done. Told y'all. 💰", "and they smacked that ass. 💰",
                            "and they came through. Trust the algorithm. 💰", "and they cashed. Fuck yeah. 💰"], used, k)
    elif res == "lost":
        end = _pick("lost", ["they shit the bed. Is what it is.", "they shit the bed. Bad call, our bad.",
                             "they were booty cheeks. Is what it is.", "they fumbled the bag. We run it back.",
                             "they never showed up. Bad call — next one's ours."], used, k)
    else:
        end = _pick("pending", ["we gon' see.", "they about to go to work. We gon' see.", "trust the algorithm. We gon' see.",
                                "hammer time. We gon' see.", "they cooking soon. We gon' see.", "don't be a sheep. We gon' see.",
                                "the book's sleeping. We gon' see.", "let's eat. We gon' see."], used, k)
    return f"{score} {thought} — {end}"


def _wl_words(ps, h):
    """'3 won · 4 lost · 43%' - so a 3-4 record can't be read as '3 of 4'."""
    if h is None:
        return "&nbsp;"
    w, l_ = sum(p["status"] == "won" for p in ps), sum(p["status"] == "lost" for p in ps)
    return f"{w} won · {l_} lost · {h:.0%}"


def _rot(k, options):
    """The day's line from a rotation: consecutive days never get the same one."""
    return options[k % len(options)]


def _breakdown(leg):
    secs = leg.get("breakdown")
    if not secs:
        return ""
    body = "".join(f"<p>{E(x)}</p>" for x in secs if isinstance(x, str))
    return f'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">{body}</div></details>'


def _leg(leg):
    lg = sd.LEAGUES[leg["league"]]
    mk = "ML" if leg["market"] == "ml" else f'{leg["line"]:+g}'
    res = leg.get("result")
    mark = ""
    badge = {"won": '<span class="lr won">✅ HIT</span>', "lost": '<span class="lr lost">❌ MISS</span>',
             "push": '<span class="lr push">PUSH</span>', "void": '<span class="lr push">VOID</span>'}.get(res, "")
    why = " · ".join(E(r) for r in leg.get("reasons") or [])
    pub = leg.get("public")
    tag = ('<span class="pub fade">🤡 FADING THE PUBLIC</span>' if pub == "fade" else
           '<span class="pub ride">🤝 RIDING WITH THE PUBLIC</span>' if pub == "ride" else "")
    outs = f'<div class="outs">🚑 {E(leg["opp"])} missing: {E(", ".join(leg["opp_outs"]))}</div>' if leg.get("opp_outs") else ""
    return f"""<div class="leg {res or ''}">
  <div class="lt"><span class="lgb">{lg[3]} {lg[2]}</span>{badge or f'<span class="tm">{_time(leg["start"])}</span>'}</div>
  <div class="lm"><span class="pick">{mark}{E(leg["team"])} <em>{mk}</em></span><span class="od">{_am(leg["odds"])}</span></div>
  <div class="ls">{"vs" if leg["home"] else "@"} {E(leg["opp"])}</div>
  {f'<div class="why">{why}</div>' if why else ""}{f'<div class="pubs">{tag}</div>' if tag else ""}{outs}{_breakdown(leg)}
  {f'<div class="fin">Final: {E(leg["score"])}</div>' if leg.get("score") else ""}
</div>"""


def _pick_card(kind, pk):
    label, c1, c2 = LOOK[kind]
    if not pk:
        return f"""<section class="pk" style="--c1:{c1};--c2:{c2}"><div class="pk-h"><span class="pk-i">{ICON[kind]}</span>
<span class="pk-l">{label}</span></div><div class="nopick">No play today — nothing on the slate has real value. We don't force it.</div></section>"""
    if pk["status"] == "waiting":
        why = " · ".join(E(w) for w in pk.get("waiting") or [])
        return f"""<section class="pk waiting" style="--c1:{c1};--c2:{c2}"><div class="pk-h"><span class="pk-i">{ICON[kind]}</span>
<span class="pk-l">{label}</span><span class="chip waiting">PICK COMING</span></div>
<div class="lock">⏳ Waiting on: {why}</div><div class="lock">Posted by {_time(pk["deadline"])} at the latest — once it's up, it's final.</div></section>"""
    win = pk["stake"] * (pk["dec"] - 1)
    legs = "".join(_leg(leg) for leg in pk["legs"])
    stamp = {"won": '<div class="stamp won">CASHED</div>', "lost": '<div class="stamp lost">LOST</div>',
             "push": '<div class="stamp push">PUSH</div>'}.get(pk["status"], "")
    hits = sum(l.get("result") == "won" for l in pk["legs"])
    left = sum(not l.get("result") for l in pk["legs"])
    track = (f'<div class="track">🔥 {hits} of {len(pk["legs"])} legs hit — {left} to go</div>'
             if pk["status"] == "open" and len(pk["legs"]) > 1 and hits and left else "")
    return f"""<section class="pk {pk["status"]}" style="--c1:{c1};--c2:{c2}">
  <div class="pk-h"><span class="pk-i">{ICON[kind]}</span><span class="pk-l">{label}</span>{'<span class="chip lean">🟡 LEAN</span>' if pk.get("lean") else '<span class="chip val">🔥 VALUE</span>'}{_chip(pk["status"])}</div>
  <div class="pk-o"><span class="big">{_am(pk["american"])}</span>
    <span class="pay">$100 wins <b>${win:,.0f}</b></span></div>
  {f'<div class="stamp-row">{stamp}</div>' if stamp else ""}{track}{legs}
</section>"""


def _tennis():
    """🎾 TENNIS BONUS: collapsed at the very bottom (tap to open) - the latest slate, its parlay, its own record."""
    try:
        with open(os.path.join(sd.DATA, "tennis", "picks.json")) as f:
            slates = json.load(f)
    except (OSError, ValueError):
        slates = []
    if not slates:
        return ""
    s = slates[-1]
    legs = {l["id"]: l for l in s["picks"]}
    r = {"won": 0, "lost": 0, "p_won": 0, "p_lost": 0}
    for x in slates:
        for l in x["picks"]:
            r["won"] += l["result"] == "won"
            r["lost"] += l["result"] == "lost"
        if x.get("parlay"):
            r["p_won"] += x["parlay"]["status"] == "won"
            r["p_lost"] += x["parlay"]["status"] == "lost"
    badge = {"won": '<span class="lr won">✅ HIT</span>', "lost": '<span class="lr lost">❌ MISS</span>',
             "void": '<span class="lr push">VOID</span>'}

    def row(l):
        bd = "".join(f"<p>{E(x)}</p>" for x in l.get("breakdown") or [])
        return f"""<div class="leg {l['result'] or ''}">
  <div class="lt"><span class="lgb">🎾 {"Women's Tennis" if l.get("tour") == "wta" else "Men's Tennis"} · {E(l['tourney'])}</span>{badge.get(l['result']) or f'<span class="tm">{_time(l["start"])}</span>'}</div>
  <div class="lm"><span class="pick">{E(l['player'])} <em>{f"{l['hcp']:+g} games" if l.get("market") == "spread" else "ML"}</em></span><span class="od">{_am(l['odds'])}</span></div>
  <div class="ls">vs {E(l['opp'])} · {E(l['round'])} · {E({"hard": "Hard court", "clay": "Clay", "grass": "Grass"}.get(l['surface'], l['surface']))}</div>
  {f'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">{bd}</div></details>' if bd else ""}
  {f'<div class="fin">Final: {E(l["score"])}</div>' if l.get("score") else ""}
</div>"""
    par = s.get("parlay")
    par_html = ""
    if par:
        stamp = {"won": '<div class="stamp won">CASHED</div>', "lost": '<div class="stamp lost">LOST</div>'}.get(par["status"], "")
        par_html = f"""<section class="pk {par['status']}" style="--c1:#c6f000;--c2:#1fd17a">
  <div class="pk-h"><span class="pk-i">🎾</span><span class="pk-l">TENNIS PARLAY OF THE DAY</span>{_chip(par["status"])}</div>
  <div class="pk-o"><span class="big">{_am(par['american'])}</span><span class="pay">$100 wins <b>${100 * (par['dec'] - 1):,.0f}</b></span></div>
  {f'<div class="stamp-row">{stamp}</div>' if stamp else ""}{"".join(row(legs[i]) for i in par["legs"] if i in legs)}
</section>"""
    day = datetime.strptime(s["date"], "%Y-%m-%d").strftime("%A, %B %-d")
    groups = ""
    for title, ls in (("MEN'S TENNIS", [l for l in s["picks"] if l.get("tour", "atp") != "wta"]),
                      ("WOMEN'S TENNIS", [l for l in s["picks"] if l.get("tour") == "wta"])):
        if ls:
            groups += (f'<section class="pk" style="--c1:#c6f000;--c2:#1fd17a"><div class="pk-h"><span class="pk-i">🎾</span>'
                       f'<span class="pk-l">{title}</span></div>{"".join(row(l) for l in ls)}</section>')
    return f"""<details class="tn"><summary><span class="tn-t">🎾 TENNIS BONUS</span>
<span class="tn-s">{len(s['picks'])} picks + parlay · {r['won']}-{r['lost']} · tap to open</span></summary>
<div class="tn-b"><div class="tn-d">{E(day)} · parlays {r['p_won']}-{r['p_lost']}</div>{par_html}
{groups}</div></details>"""


def render(picks, model, games, series, start_bank, updated_ms):
    now = datetime.now(PT)
    today = now.date().isoformat()
    todays = {p["kind"]: p for p in picks if p["date"] == today}
    board_date = now.strftime("%A, %B %-d")
    drop = '<div class="drop">🎯 Picks go up as soon as the engine is sure — from <b>6 PM PT</b> the night before. Once posted, they\'re final.</div>'
    board = "".join(_pick_card(k, todays.get(k)) for k in LOOK) if todays else drop
    tmr = (now + timedelta(days=1)).date()
    tomorrows = {p["kind"]: p for p in picks if p["date"] == tmr.isoformat()}
    tomorrow = (f'<div class="sec"><h2><i>●</i> TOMORROW\'S BOARD</h2><span>{tmr:%A, %B %-d}</span></div>'
                + "".join(_pick_card(k, tomorrows[k]) for k in LOOK if k in tomorrows)) if tomorrows else ""

    graded_all = [p for p in picks if p["status"] in ("won", "lost", "push")]
    done = [p for p in graded_all if not p.get("lean")]          # the main record is value picks only
    leans_done = [p for p in graded_all if p.get("lean")]
    done.sort(key=lambda p: (p["date"], p.get("settled", "")))

    def wl(ps):
        w, l_, pu = (sum(p["status"] == k for p in ps) for k in ("won", "lost", "push"))
        return f"{w}-{l_}" + (f"-{pu}" if pu else ""), (w / (w + l_) if w + l_ else None)

    def streak(ps):
        if not ps:
            return ""
        last, n = ps[-1]["status"], 0
        for p in reversed(ps):
            if p["status"] != last:
                break
            n += 1
        return f'{"W" if last == "won" else "L" if last == "lost" else "P"}{n}'
    m0 = datetime(now.year, now.month, 1, tzinfo=PT).date().isoformat()
    rec_all, hit_all = wl(done)
    rec_day, _ = wl([p for p in done if p["date"] == today])
    rec_month, hit_month = wl([p for p in done if p["date"] >= m0])
    first = min((p["date"] for p in picks), default=today)
    hot = streak(done)

    def tile(label, sub, val, foot, hue, cls="w"):
        return (f'<div class="tile" style="--h:{hue}"><div class="tl">{label}</div><div class="ts">{sub}</div>'
                f'<div class="tv {cls}">{val}</div><div class="ts" style="color:{hue}">{foot}</div></div>')
    tiles = (tile("This month", now.strftime("%B"), rec_month, f"{hit_month:.0%} hit" if hit_month is not None else "&nbsp;", "#2f8bff")
             + tile("Hit rate", f"since {datetime.fromisoformat(first):%b %-d}", f"{hit_all:.0%}" if hit_all is not None else "—", "all plays", "#22e39a")
             + tile("Streak", "current", hot or "—", "🔥 heater" if hot.startswith("W") and len(hot) > 1 and int(hot[1:]) >= 3 else "&nbsp;",
                    "#ffc233", "up" if hot.startswith("W") else "dn" if hot.startswith("L") else "w"))
    strip = "".join(f'<i class="{p["status"]}" title="{E(p["date"])}"></i>' for p in done[-40:]) or '<span class="empty">results show up here</span>'

    # live bets: their own record
    live = {}
    try:
        with open(os.path.join(sd.DATA, "live_log.json")) as f:
            live = json.load(f).get("plays", {})
    except (OSError, ValueError):
        pass
    lw, ll = sum(e.get("result") == "won" for e in live.values()), sum(e.get("result") == "lost" for e in live.values())
    live_card = (f'<div class="rc" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="rc-t">🔴 LIVE BETS</div><div class="rc-r">{lw}-{ll}</div>'
                 f'<div class="rc-p">{f"{lw} won · {ll} lost · {lw / (lw + ll):.0%}" if lw + ll else "&nbsp;"}</div>'
                 f'<div class="rc-s">{"&nbsp;" if lw + ll else "no results yet"}</div></div>')
    # today's live bets (and last night's): what they were, and whether they cashed
    ld = datetime.now(PT).date()
    days_ = {ld.isoformat(), (ld - timedelta(days=1)).isoformat()}
    lrows = sorted((e for e in live.values() if e.get("date") in days_), key=lambda e: e["posted"], reverse=True)[:8]
    badge_ = {"won": '<span class="lr won">✅ CASHED</span>', "lost": '<span class="lr lost">❌ LOST</span>'}
    pending_ = '<span class="tm">⏳ still going</span>'
    used_ = set()                                            # no two bets in the list share a phrase
    stories = {id(e): _live_story(e, used_) for e in lrows}
    live_list = ("" if not lrows else
                 '<section class="pk" style="--c1:#ff3b3b;--c2:#ff8a00;margin-top:14px"><div class="pk-h"><span class="pk-i">🔴</span>'
                 '<span class="pk-l">LIVE BETS TODAY</span></div>' + "".join(
                     f'<div class="leg {e.get("result") or ""}"><div class="lt"><span class="lgb">{sd.LEAGUES.get(e["league"], ("", "", "", "🏟️"))[3]} '
                     f'{E(sd.LEAGUES.get(e["league"], ("", "", e["league"].upper()))[2])}</span>'
                     f'{badge_.get(e.get("result"), pending_)}</div>'
                     f'<div class="lm"><span class="pick">{E(e["team"])} <em>ML</em></span><span class="od">{_am(e["odds"])}</span></div>'
                     f'<div class="ls">{E(stories[id(e)])}</div></div>'
                     for e in lrows) + "</section>")
    lw_, ll_ = sum(p["status"] == "won" for p in leans_done), sum(p["status"] == "lost" for p in leans_done)
    lean_card = ("" if not leans_done else
                 f'<div class="rc" style="--c1:#ffc233;--c2:#e8c77a"><div class="rc-t">🟡 LEANS</div><div class="rc-r">{lw_}-{ll_}</div>'
                 f'<div class="rc-p">{f"{lw_} won · {ll_} lost · {lw_ / (lw_ + ll_):.0%}" if lw_ + ll_ else "&nbsp;"}</div>'
                 f'<div class="rc-s">own record</div></div>')
    # record per pick type
    rec = []
    for kind, (label, c1, c2) in LOOK.items():
        ps = [p for p in done if p["kind"] == kind]
        r, h = wl(ps)
        st = streak(ps)
        rec.append(f'<div class="rc" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{ICON[kind]} {label.replace(" OF THE DAY", "")}</div>'
                   f'<div class="rc-r">{r}</div><div class="rc-p">{_wl_words(ps, h)}</div>'
                   f'<div class="rc-s">{("streak " + st) if st else "no results yet"}</div></div>')


    # the brain, in a nutshell - only what actually happened, in our voice, rotating day to day
    params = model.get("params", {})
    k = now.toordinal()
    lines = []
    graded = [p for p in done if p.get("settled", "")[:10] >= (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d")
              and p["date"] in (today, (now - timedelta(days=1)).date().isoformat())]
    w_, l_ = sum(p["status"] == "won" for p in graded), sum(p["status"] == "lost" for p in graded)
    yday = (now - timedelta(days=1)).date().isoformat()
    live_today = any(e.get("result") in ("won", "lost") and e.get("date") in (today, yday) for e in live.values())
    if w_ + l_ == 0 and live_today:
        pass                                                      # the live results below speak for the day
    elif w_ + l_ == 0:
        lines.append(["⏳ Nothing graded yet today — games still cooking.", "⏳ Tickets are still live. Check back after the games.",
                      "⏳ No results in yet. Sit tight."][k % 3])
    elif l_ == 0:
        lines.append(_rot(k, [f"🔥 {w_}-0. We crushed today — fuck yeah, let's go!",
                              f"🔥 {w_}-0. Today was a grace from baby Jesus himself. Let's fucking go!",
                              f"🔥 Clean sweep, {w_}-0. We smacked today. Let's go!",
                              f"🔥 {w_}-0. Didn't miss a single one. Trust the algorithm.",
                              f"🔥 {w_}-0. Today was a grace from Jesus. Let's fucking go!",
                              f"🔥 Perfect day, {w_}-0. Books are crying right now."]))
    elif w_ >= l_:
        lines.append(_rot(k, [f"✅ {w_}-{l_}. We crushed today — let's fucking go!",
                              f"✅ {w_}-{l_}. We smacked today. Let's go!",
                              f"✅ Went {w_}-{l_}. Cashing tickets.",
                              f"✅ {w_}-{l_} on the day. We eat.",
                              f"✅ {w_}-{l_}. Told y'all. Trust the algorithm.",
                              f"✅ {w_}-{l_}. Today was a grace from Jesus. Fuck yeah!",
                              f"✅ {w_}-{l_}. Another W in the books. Let's go!",
                              f"✅ {w_}-{l_}. Fed the whole squad today."]))
    else:
        lines.append(_rot(k, [f"😤 {w_}-{l_}. Our picks were fucking ass today. We gon' do better tomorrow.",
                              f"😤 {w_}-{l_}. Our picks were fucking ass today. We gon' bounce back. I won't let y'all down.",
                              f"😤 {w_}-{l_}. Not our day — the engine's already studying the tape.",
                              f"😤 Took some L's today ({w_}-{l_}). Shake it off. We gon' be right back.",
                              f"😤 {w_}-{l_}. Today was trash, no sugarcoating it. Tomorrow we eat.",
                              f"😤 {w_}-{l_}. Vegas got us today. Enjoy it while it lasts.",
                              f"😤 {w_}-{l_}. Rough one. Head up — we run it back tomorrow.",
                              f"😤 {w_}-{l_}. Bad day at the office. The algorithm's taking notes."]))
    # big hits (+300 and up, board or live): they get their own brag, right under the day's record
    big = [(p["american"], (E(_the(p["legs"][0]["team"], p["legs"][0]["league"])) if len(p["legs"]) == 1
                            else "the " + LOOK[p["kind"]][0].replace(" OF THE DAY", "").lower()), "")
           for p in graded if p["status"] == "won" and p.get("american", 0) >= BIG_HIT]
    big += [(e["odds"], E(_the(e["team"], e.get("league"))), " live") for e in live.values()
            if e.get("result") == "won" and e.get("odds", 0) >= BIG_HIT and e.get("date") in (today, yday)]
    for i, (o, what, how) in enumerate(sorted(big, reverse=True)[:2]):
        lines.insert(1 + i, _rot(k + o, [f"💰 DAMN. We smacked a +{o}{how} — {what}. I tried to fucking tell y'all. Let's go!",
                                         f"💰 +{o}{how}. CASHED. {_cap(what)} came through and I told y'all all day. Let's fucking go!",
                                         f"💰 Y'all doubted {what} at +{o}{how}? Smacked it. Trust the algorithm. LET'S GO!",
                                         f"💰 {_cap(what)} at +{o}{how}. Books are in shambles. I tried to fucking tell y'all!"]))
    big_live = {(e["team"], e["odds"]) for e in live.values() if e.get("odds", 0) >= BIG_HIT}
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%MZ")
    fresh = {}
    for g in (games or {}).values():
        if g.get("status") == "final" and g.get("start", "") >= cutoff and (g.get("stype") or "?") in sd.REAL:
            fresh[g["league"]] = fresh.get(g["league"], 0) + 1
    if fresh:
        parts = [f"{n} {sd.LEAGUES[lg][2]}" for lg, n in sorted(fresh.items(), key=lambda x: -x[1])]
        what = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
        lines.append([f"🎥 Studied the tape on last night's {what} games.", f"🎥 Broke down the film from {what} games.",
                      f"🎥 Ran back {what} games and got sharper."][k % 3])
    n = sum(p.get("eval_games", 0) for p in params.values())
    if n:
        a_ = sum(p["accuracy"] * p.get("eval_games", 0) for p in params.values()) / n
        lines.append([f"🎯 Calling winners at a {a_:.1%} clip.", f"🎯 Hitting on {a_:.1%} of winners.",
                      f"🎯 {a_:.1%} of winners called straight up."][k % 3])
    legs = [l for p in picks for l in p["legs"] if l.get("result") in ("won", "lost")]
    if legs:
        said = sum(l["p"] for l in legs) / len(legs)
        got = sum(l["result"] == "won" for l in legs) / len(legs)
        lines.append(f"🧾 Receipts: said {said:.0%} of our legs would hit — <b class=\"{'up' if got >= said else 'dn'}\">{got:.0%}</b> did.")
    for e in sorted((e for e in live.values() if e.get("result") == "won" and e.get("date") in (today, yday)
                     and (e["team"], e["odds"]) not in big_live),                  # big ones already got the brag
                    key=lambda e: e["posted"])[-2:]:
        o = f"+{e['odds']}" if e["odds"] > 0 else str(e["odds"])
        t = E(_the(e["team"], e.get("league")))
        lines.append(_rot(k + len(e["team"]), [f"🔴 We smacked {t} live bet ({o}). The algorithm never lies.",
                                               f"🔴 Live bet cashed: {t} at {o}. Told y'all — teams always be coming back.",
                                               f"🔴 {_cap(t)} live at {o}? Cashed. Trust the algorithm.",
                                               f"🔴 Caught {t} live at {o} and they came through. Fuck yeah, let's go!",
                                               f"🔴 {_cap(t)} live at {o} — CASHED. Everybody was jumping off, we jumped on."]))
    for e in sorted((e for e in live.values() if e.get("result") == "lost" and e.get("date") in (today, yday)),
                    key=lambda e: e["posted"])[-2:]:
        o = f"+{e['odds']}" if e["odds"] > 0 else str(e["odds"])
        t = E(_the(e["team"], e.get("league")))
        lines.append(_rot(k + len(e["team"]), [f"🔴 {_cap(t)} live bet ({o}) shit the bed. Bad call — is what it is.",
                                               f"🔴 {_cap(t)} live at {o} was booty cheeks. Our bad. We run it back.",
                                               f"🔴 Live L: {t} at {o}. Comeback never came. Is what it is — the algorithm's taking notes.",
                                               f"🔴 {_cap(t)} live at {o} came up short. Bad call, shake it off — next one's ours."]))
    if not done and not any(x.startswith("🔴") for x in lines):   # no finished day yet: nothing to brag or cry about
        lines = ["👀 We gon' see."]
    elif lines:                                               # results are in: remind everybody we're just getting started
        first = min((p["date"] for p in picks), default=today)
        young = (now.date() - datetime.strptime(first, "%Y-%m-%d").date()).days < 60
        lines.append(_rot(k, [
            "🧪 Real talk: we just got this thing started. The algorithm's training every single day — it's only getting sharper.",
            "🧪 We're brand new out here. Every game makes the engine smarter. Give it time — we about to be dangerous.",
            "🧪 Day by day, the algorithm's leveling up. Wins or L's, it's learning from all of it. Trust the process.",
            "🧪 This engine is still a baby and it's already cooking. Wait till it grows up.",
            "🧪 Still training the algorithm and improving every day. The best is coming — stay locked in.",
            "🧪 Every result goes back into the brain. We getting better and better — y'all gonna see.",
            "🧪 We just started and we're analyzing EVERYTHING — every game, every line, every comeback. The engine improves daily.",
            "🧪 Heads up: we're still new. The algorithm breaks down every result and upgrades itself every day. Stick with us."] if young else [
            "🧪 The algorithm studies every result and gets sharper every day. We never stop improving.",
            "🧪 Engine's still leveling up daily. Every W and every L makes it smarter.",
            "🧪 We keep training this thing every single day. Better tomorrow than today — that's the deal.",
            "🧪 Always improving. The algorithm learns from every game — trust the process."]))
    brain = '<div class="br self"><div class="bn">🧠 Today in a nutshell</div>' + "".join(f'<div class="bs nut">{x}</div>' for x in lines) + "</div>"
    tuned = model.get("tuned_on", "—")

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="refresh" content="300">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="D503 Sports">
<meta name="theme-color" content="#05070b">
<title>THE D503 · Sports Engine</title>
<meta property="og:type" content="website">
<meta property="og:title" content="THE D503 SPORTS ENGINE">
<meta property="og:description" content="Daily 2-Leg, 3-Leg, Lock &amp; Dog of the Day. Trust the algorithm.">
<meta property="og:url" content="https://d503therapper.github.io/autonomous-crypto-engine/sports/">
<meta property="og:image" content="https://d503therapper.github.io/autonomous-crypto-engine/sports/og.png?v=8">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="description" content="Daily 2-Leg, 3-Leg, Lock &amp; Dog of the Day. Trust the algorithm.">
<link rel="apple-touch-icon" href="apple-touch-icon.png?v=8"><link rel="icon" href="icon-512.png?v=8"><link rel="manifest" href="manifest.webmanifest">
<style>
:root{{--bg:#040609;--card:#0b0f17;--card2:#101723;--line:#1b2433;--text:#f2f5fb;--muted:#22d3ee;--up:#22e39a;--dn:#ff3b3b;--gold:#ffc233;--accent:#ffc233}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}}
body{{font:15px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",system-ui,sans-serif;min-height:100vh;
  background:radial-gradient(640px 400px at 10% -120px,rgba(255,194,51,.22),transparent 70%),
             radial-gradient(640px 420px at 100% -80px,rgba(255,90,31,.20),transparent 70%),
             repeating-linear-gradient(135deg,rgba(255,255,255,.018) 0 2px,transparent 2px 7px),var(--bg)}}
main{{max-width:520px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 18px) 16px 34px;overflow:hidden}}
.head{{position:relative;margin:6px 0 18px}}
.title{{font-weight:900;font-size:40px;letter-spacing:-.02em;line-height:1}}
.the{{font-size:20px;font-weight:800;letter-spacing:.2em;color:#ff2a2a;vertical-align:middle;text-shadow:0 0 14px rgba(255,42,42,.7)}}
.d503{{background:linear-gradient(95deg,#3b82ff 0%,#22d3ee 45%,#22e39a 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 6px 22px rgba(59,130,255,.45))}}
.tag{{margin-top:8px;font-size:12.5px;font-weight:900;letter-spacing:.34em;background:linear-gradient(90deg,#ffe08a,#ffc233 35%,#ff8a00 75%,#ff5a1f);
  -webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 0 10px rgba(255,160,40,.5))}}
.live{{position:absolute;top:2px;right:0;white-space:nowrap;display:flex;align-items:center;gap:7px;font-size:12px;font-weight:700;color:var(--up);
  background:rgba(34,227,154,.08);border:1px solid rgba(34,227,154,.35);padding:6px 10px;border-radius:999px}}
.dot{{width:8px;height:8px;border-radius:50%;background:var(--up);animation:pulse 2s infinite}}
.dot.stale{{background:#f5b73b;animation:none}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(34,227,154,.6)}}70%{{box-shadow:0 0 0 10px rgba(34,227,154,0)}}100%{{box-shadow:0 0 0 0 rgba(34,227,154,0)}}}}
.sec{{display:flex;align-items:baseline;justify-content:space-between;margin:22px 2px 10px}}
.sec h2{{margin:0;font-size:13px;font-weight:900;letter-spacing:.2em;color:#fff}}
.sec h2 i{{font-style:normal;color:var(--gold);text-shadow:0 0 10px rgba(255,194,51,.6)}}
.sec span{{font-size:12px;color:var(--gold);font-weight:600}}
.board{{position:relative}}
.trust-wrap{{display:flex;justify-content:center;margin:14px 0 4px}}
.trust{{font-weight:900;font-style:italic;font-size:22px;letter-spacing:.14em;color:#fff;padding:0 6px 8px;position:relative}}
.trust:after{{content:"";position:absolute;left:0;right:0;bottom:0;height:5px;background:#e3121b;transform:skewX(-20deg)}}
.drop{{text-align:center;font-weight:700;color:#fff;background:var(--card);border:1px dashed rgba(255,194,51,.55);border-radius:16px;padding:14px;margin-bottom:12px}}
.drop b{{color:var(--gold)}}
.pk{{position:relative;background:linear-gradient(165deg,color-mix(in srgb,var(--c1) 16%,var(--card2)) 0%,var(--card) 55%);border:1px solid color-mix(in srgb,var(--c1) 55%,transparent);
  border-radius:22px;padding:16px 16px 10px;margin-bottom:14px;overflow:hidden;box-shadow:0 18px 50px -22px var(--c1),inset 0 1px 0 rgba(255,255,255,.05)}}
.pk::before{{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.pk.won{{box-shadow:0 0 0 2px var(--up),0 18px 50px -14px var(--up)}}
.pk.lost>*:not(.stamp-row){{opacity:.5}}
.stamp-row{{display:flex;justify-content:center;margin:6px 0 12px}}
.stamp{{transform:rotate(-6deg);font-weight:900;font-size:34px;letter-spacing:.16em;padding:4px 22px;border:4px solid currentColor;
  border-radius:10px;background:rgba(0,0,0,.3)}}
.stamp.won{{color:var(--up);text-shadow:0 0 16px rgba(34,227,154,.7);box-shadow:0 0 22px rgba(34,227,154,.35)}}
.stamp.lost{{color:var(--dn);text-shadow:0 0 16px rgba(255,59,59,.6)}}
.stamp.push{{color:var(--gold)}}
.track{{font-size:13px;font-weight:900;letter-spacing:.04em;color:var(--gold);margin:2px 0 4px}}
.leg.won{{border-left:4px solid var(--up);padding-left:10px;margin-left:-14px;background:linear-gradient(90deg,rgba(34,227,154,.10),transparent 60%)}}
.leg.lost{{border-left:4px solid var(--dn);padding-left:10px;margin-left:-14px;background:linear-gradient(90deg,rgba(255,59,59,.10),transparent 60%)}}
.leg.lost .pick{{text-decoration:line-through;text-decoration-color:var(--dn);text-decoration-thickness:3px}}
.lr{{font-size:11.5px;font-weight:900;letter-spacing:.1em;padding:3px 8px;border-radius:999px}}
.lr.won{{color:#04110b;background:var(--up)}} .lr.lost{{color:#fff;background:var(--dn)}} .lr.push{{color:#000;background:var(--gold)}}
.pk-h{{display:flex;align-items:center;gap:10px}}
.pk-i{{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;font-size:18px;background:linear-gradient(135deg,var(--c1),var(--c2));box-shadow:0 6px 18px -6px var(--c1)}}
.pk-l{{flex:1;font-weight:900;font-size:14px;letter-spacing:.14em;color:var(--c1);text-shadow:0 0 12px color-mix(in srgb,var(--c1) 55%,transparent)}}
.chip{{font-size:10.5px;font-weight:900;letter-spacing:.1em;padding:4px 8px;border-radius:999px;white-space:nowrap}}
.lock{{font-size:12.5px;font-weight:800;color:var(--gold);margin:2px 0 4px}}
.pk.waiting{{border-style:dashed}}
.chip.waiting{{color:#0a0a0a;background:var(--gold)}}
.chip.open{{color:#fff;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2)}}
.chip.won{{color:#04110b;background:var(--up)}} .chip.lost{{color:#fff;background:var(--dn)}} .chip.push{{color:#000;background:var(--gold)}}
.pk-o{{display:flex;align-items:center;justify-content:space-between;margin:12px 0 6px}}
.big{{font-size:42px;font-weight:900;letter-spacing:-.02em;line-height:1;color:#fff;font-variant-numeric:tabular-nums;text-shadow:0 0 24px color-mix(in srgb,var(--c1) 60%,transparent)}}
.pay{{text-align:right;font-size:14px;color:#fff;font-weight:600}} .pay b{{color:var(--c1);font-size:18px}} .pay span{{color:var(--c1);font-size:12px}}
.leg{{border-top:1px solid rgba(255,255,255,.07);padding:10px 0 8px}}
.lt{{display:flex;justify-content:space-between;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--c1)}}
.lgb{{color:#fff}}
.lm{{display:flex;justify-content:space-between;align-items:baseline;margin-top:3px}}
.pick{{font-size:18px;font-weight:850;color:#fff}} .pick em{{font-style:normal;color:var(--c1);font-weight:900;margin-left:2px}}
.od{{font-size:17px;font-weight:900;color:#fff;font-variant-numeric:tabular-nums}}
.ls{{font-size:12.5px;color:#fff;margin-top:2px}} .ls b{{color:#fff}}
.ep{{color:var(--up);font-weight:800}} .en{{color:#ff8a5c;font-weight:800}}
.why{{font-size:12px;color:#e8c77a;margin-top:4px}}
.pubs{{margin-top:6px}} .pub{{display:inline-block;font-size:11px;font-weight:900;letter-spacing:.1em;padding:4px 9px;border-radius:999px}}
.pub.fade{{color:#fff;background:linear-gradient(90deg,#7c3aed00,#e3121b33);border:1px solid #ff3b3b}} .pub.ride{{color:#22e39a;border:1px solid #22e39a;background:rgba(34,227,154,.1)}}
.lv{{color:#ff3b3b !important;animation:blink 1.2s infinite}} @keyframes blink{{50%{{opacity:.2}}}}
.nolive{{font-size:14px;font-weight:700;color:#fff;line-height:1.45}} .pk.lvi{{padding-top:16px;padding-bottom:16px}}
.tn{{margin:22px 0 6px;border:1px solid #c6f00066;border-radius:18px;background:linear-gradient(165deg,#c6f00014,var(--card))}}
.tn summary{{list-style:none;cursor:pointer;padding:16px 18px;display:flex;flex-direction:column;gap:4px}}
.tn summary::-webkit-details-marker{{display:none}}
.tn-t{{font-weight:900;letter-spacing:.14em;color:#c6f000;font-size:15px}} .tn-s{{font-size:12.5px;color:#fff;font-weight:700}}
.tn[open] .tn-s{{color:#c6f000}} .tn-b{{padding:0 12px 14px}} .tn-d{{font-size:12px;color:#e8c77a;font-weight:700;margin:0 6px 10px}}
.chip.lean{{background:#ffc233;color:#111;margin-right:6px}} .chip.val{{background:#ff5a1f;color:#fff;margin-right:6px}}
.pk.lvc{{box-shadow:0 0 0 2px #ff3b3b,0 18px 50px -14px #ff3b3b}} .chip.livechip{{color:#fff;background:#ff3b3b}}
.bd{{margin-top:8px;border:1px solid color-mix(in srgb,var(--c1) 45%,transparent);border-radius:12px;background:rgba(0,0,0,.25)}}
.bd summary{{list-style:none;cursor:pointer;padding:8px 12px;font-size:13px;font-weight:800;color:var(--c1);letter-spacing:.04em}}
.bd summary::-webkit-details-marker{{display:none}}
.bd summary:after{{content:"▾";float:right;transition:transform .2s}} .bd[open] summary:after{{transform:rotate(180deg)}}
.bd-s{{padding:2px 12px 8px}} .bd-t{{font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);margin-top:4px}}
.bd-s p{{margin:6px 0;font-size:13.5px;color:#fff;line-height:1.45}} .bd-s p:last-child{{color:var(--gold);font-weight:700}}
.outs{{font-size:11.5px;color:#ff8a5c;margin-top:3px}}
.fin{{font-size:12px;color:#fff;opacity:.75;margin-top:3px}}
.lw{{color:var(--up);margin-right:6px}} .ll{{color:var(--dn);margin-right:6px}} .lp{{color:var(--gold);margin-right:6px}}
.nopick{{color:var(--muted);font-weight:600;font-size:13px;padding:12px 0 6px}}
.hero{{position:relative;background:linear-gradient(160deg,#131a28 0%,var(--card) 60%);border:1px solid rgba(255,194,51,.28);border-radius:24px;padding:20px 20px 8px;overflow:hidden;
  box-shadow:0 20px 60px -24px rgba(255,160,40,.45)}}
.lbl{{color:#fff;font-size:12px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}
.total{{font-size:42px;font-weight:800;letter-spacing:-.02em;margin:4px 0 8px;font-variant-numeric:tabular-nums}}
.pill{{display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:14px;padding:5px 11px;border-radius:999px;
  background:color-mix(in srgb,var(--p) 16%,transparent);color:var(--p);font-variant-numeric:tabular-nums}}
.pill small{{color:#fff;font-weight:900;font-size:11px;letter-spacing:.08em}}
.month{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}}
.tile{{background:linear-gradient(180deg,color-mix(in srgb,var(--h) 14%,transparent),rgba(255,255,255,.02));border:1px solid color-mix(in srgb,var(--h) 45%,transparent);
  border-radius:14px;padding:10px 9px;min-width:0;overflow:hidden;box-shadow:0 6px 22px -12px var(--h)}}
.tl{{color:#fff;font-size:9.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}}
.ts{{font-size:11px;font-weight:700;color:#fff;margin-top:1px;white-space:nowrap}} .ts.up{{color:var(--up)}} .ts.dn{{color:var(--dn)}}
.tv{{font-size:clamp(13px,4.2vw,17px);font-weight:800;margin-top:6px;white-space:nowrap}}
.ar{{font-size:.7em;margin-right:3px;vertical-align:1px}}
.up{{color:var(--up)}} .dn{{color:var(--dn)}} .w{{color:#fff}}
.strip{{display:flex;flex-wrap:wrap;gap:4px;margin:14px 0 12px}}
.strip i{{width:12px;height:12px;border-radius:3px;background:#2f8bff}}
.strip i.won{{background:var(--up);box-shadow:0 0 8px rgba(34,227,154,.6)}} .strip i.lost{{background:var(--dn)}} .strip i.push{{background:var(--gold)}}
.recs{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.rc{{position:relative;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px;overflow:hidden}}
.rc::before{{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.rc-t{{font-size:11px;font-weight:900;letter-spacing:.12em;color:var(--c1)}}
.rc-r{{font-size:26px;font-weight:900;color:#fff;margin-top:4px;font-variant-numeric:tabular-nums}}
.rc-p{{font-weight:800;color:var(--c1);font-size:13px}} .rc-s{{font-size:11.5px;color:var(--c2);font-weight:700;margin-top:2px}}
.list{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:4px 14px}}
.rr{{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}} .rr:last-child{{border:0}}
.rk{{font-size:18px}} .rd{{flex:1;min-width:0}}
.rl{{font-weight:750;color:#fff;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rm{{font-size:11.5px;color:var(--muted);font-weight:600}}
.rv{{font-weight:900;font-variant-numeric:tabular-nums}}
.empty{{color:var(--muted);font-weight:600;font-size:13px;padding:12px 0}}
.br{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 14px;margin-bottom:10px}}
.br.self{{border-color:rgba(255,194,51,.35)}}
.bh{{display:flex;justify-content:space-between;align-items:center}}
.bn{{font-weight:900;color:#fff;font-size:15px}} .bt{{font-size:12px;color:var(--muted);font-weight:700}} .bt b{{color:var(--gold)}}
.bs{{font-size:12.5px;color:#fff;margin-top:3px}} .bs b{{color:#fff}} .bs b.up,.bs .up{{color:var(--up)}} .bs b.dn,.bs .dn{{color:var(--dn)}}
.fxs{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:9px}}
.fx{{position:relative;font-size:10px;font-weight:800;color:#fff;letter-spacing:.04em;padding-top:8px;text-align:center}}
.fx i{{position:absolute;top:0;left:0;height:4px;border-radius:4px;box-shadow:0 0 8px currentColor}}
.fx::before{{content:"";position:absolute;top:0;left:0;right:0;height:4px;border-radius:4px;background:rgba(255,255,255,.08)}}
.bc{{font-size:11.5px;color:#e8c77a;margin-top:8px}}
.nut{{font-size:13.5px;margin-top:7px;padding-left:14px;position:relative}} .nut:before{{content:"▸";position:absolute;left:0;color:var(--gold)}}
.foot{{text-align:center;color:#ffe08a;font-size:12px;margin-top:22px;line-height:1.6}}
.foot b{{color:#fff}} .foot a{{color:#22d3ee;text-decoration:none;font-weight:700}}
</style></head><body><main>
<header class="head">
  <div class="title"><span class="the">THE</span> <span class="d503">D503</span></div>
  <div class="tag">SPORTS ENGINE</div>
  <div class="live"><span class="dot" id="dot"></span><span id="ago">Live</span></div>
</header>
<div class="trust-wrap"><div class="trust">TRUST THE ALGORITHM</div></div>
<div id="live"><div class="sec"><h2><i class="lv">●</i> LIVE BETS</h2><span>updates every 10 sec</span></div>
<section class="pk lvi" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="nolive">📡 Checking the live games…</div></section></div>
<div class="sec"><h2><i>●</i> TODAY'S BOARD</h2><span>{E(board_date)}</span></div>
<div class="board">{board}</div>
{tomorrow}

{_tennis()}
<div class="sec"><h2><i>●</i> THE RESULTS</h2><span>every play, graded</span></div>
<section class="hero">
  <div class="lbl">Overall record</div>
  <div class="total">{rec_all}</div>
  <span class="pill" style="--p:#ffc233">{rec_day} <small>TODAY</small></span>
  <div class="month">{tiles}</div>
  <div class="strip">{strip}</div>
</section>
<div class="sec"><h2><i>●</i> RECORD BY PLAY</h2><span>{len(done)} graded</span></div>
<div class="recs">{"".join(rec)}{live_card}{lean_card}</div>
{live_list}
<div class="sec"><h2><i>●</i> THE BRAIN</h2><span>retrained {E(tuned)}</span></div>
{brain}
<div class="foot"><b>THE D503 SPORTS ENGINE</b><br>
Ratings · form · rest · injuries · line moves — retrained after every final score.<br>
Picks only — no bets placed · refreshes hourly</div>
</main>
<script>
(function(){{   // 🔴 LIVE VALUE: checks live.json every 10 seconds; a play disappears the moment its value is gone
function esc(x){{return String(x).replace(/[&<>"]/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
var last="";
function idle(n){{return '<section class="pk lvi" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="nolive">'+(n<0?
  '📡 Checking the live games…':n>0?
  '👀 No live bets right now. '+n+' game'+(n>1?'s':'')+' going — the algorithm’s watching every play for value.':
  '😴 No live bets available — no games going right now.')+'</div></section>';}}
function draw(d){{var el=document.getElementById("live");if(!el)return;var ps=(d&&d.plays)||[],n=d?(d.live_games||0):-1;
 var key=JSON.stringify(ps)+n;if(key===last)return;last=key;          // unchanged: leave it (an open breakdown stays open)
 el.innerHTML='<div class="sec"><h2><i class="lv">●</i> LIVE BETS</h2><span>updates every 10 sec</span></div>'+(ps.length?ps.map(function(p){{
  return '<section class="pk lvc" style="--c1:#ff3b3b;--c2:#ff8a00"><div class="pk-h"><span class="pk-i">'+esc(p.emoji)+'</span><span class="pk-l">LIVE BET</span><span class="chip livechip">'+(p.paused?'⏸ LINE PAUSED':'🔴 LIVE')+'</span></div>'+
   
   '<div class="leg"><div class="lt"><span class="lgb">'+esc(p.emoji)+' '+esc(p.sport)+'</span><span class="tm">'+esc(p.clock)+'</span></div>'+
   '<div class="lm"><span class="pick">'+esc(p.team)+' <em>ML</em></span><span class="od">+'+esc(p.odds)+'</span></div>'+
   '<div class="ls">'+esc(p.score)+(p.ball?' · '+esc(p.ball):'')+'</div><div class="why">'+esc(p.line)+'</div>'+
   ((p.breakdown||[]).length?'<details class="bd"><summary>🔍 Full breakdown</summary><div class="bd-s">'+p.breakdown.map(function(x){{return"<p>"+esc(x)+"</p>"}}).join("")+'</div></details>':'')+
   '</div></section>';}}).join(""):idle(n));}}
function show(d){{var age=d?Date.now()-d.updated:1e12;   // plays must be fresh; a "nothing on" board holds till the next watch
 if(d&&(age<10*60000||(!(d.plays||[]).length&&!d.live_games&&age<45*60000)))draw(d);else draw(null);}}
function raw(){{return fetch("https://raw.githubusercontent.com/{REPO}/live-data/live.json?t="+Date.now(),{{cache:"no-store"}}).then(function(r){{return r.ok?r.json():null}});}}
function poll(){{if(document.hidden)return;   // only while the app's on screen; "nothing changed" answers (304) don't count against GitHub's limit
 fetch("https://api.github.com/repos/{REPO}/contents/live.json?ref=live-data",{{headers:{{Accept:"application/vnd.github.raw"}},cache:"no-cache"}})
 .then(function(r){{return r.ok?r.json():raw()}}).catch(raw).then(show).catch(function(){{}});}}
poll();setInterval(poll,10000);document.addEventListener("visibilitychange",poll);}})();
(function(){{var t={int(updated_ms)},m=0;   // the whole page stays fresh while it's open
try{{var y=sessionStorage.getItem("d503y");if(y!==null){{sessionStorage.removeItem("d503y");window.scrollTo(0,+y);}}}}catch(e){{}}
function tick(){{m=Math.max(0,Math.round((Date.now()-t)/60000));
 var s=m<1?"just now":m<60?m+" min ago":Math.floor(m/60)+"h "+(m%60)+"m ago";
 document.getElementById("ago").textContent="Live · "+s;
 if(m>150)document.getElementById("dot").className="dot stale";}}
function check(){{if(document.hidden)return;              // a newer page? swap it in (not while a breakdown is open)
 fetch("https://api.github.com/repos/{REPO}/contents/{PAGE}?ref=main",{{headers:{{Accept:"application/vnd.github.raw"}},cache:"no-cache"}})
 .then(function(r){{return r.ok?r.text():""}})
 .then(function(h){{var x=/var t=(\d+),m=/.exec(h);
   if(x&&+x[1]>t&&!document.querySelector("details[open]")){{
     try{{sessionStorage.setItem("d503y",String(window.scrollY));}}catch(e){{}}
     location.replace(location.pathname+"?v="+x[1]);}}}})
 .catch(function(){{}});}}
tick();setInterval(tick,30000);check();setInterval(check,60000);document.addEventListener("visibilitychange",check);}})();
</script></body></html>"""


def write(picks, model, games, series, start_bank, path=PAGE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(render(picks, model, games, series, start_bank, int(time.time() * 1000)))
