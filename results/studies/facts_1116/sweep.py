"""11/16 FABLE - EVERY FACT TRUE. The sweep: every card posted 11/1-11/15 (data/sports/picks.json breakdown / why_line),
each factual claim pulled out of the words and checked against the game files and the box scores - computed here from
the raw rows, never through the breakdown's own helpers. Verdict per claim: T (true), F (false), U (can't check here).
python results/studies/facts_1116/sweep.py [since] [until]  -> results/studies/facts_1116/sweep.json + a printout."""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import sports_data as sd            # noqa: E402
import sports_roster as sr          # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
SINCE = sys.argv[1] if len(sys.argv) > 1 else "2026-11-01"
UNTIL = sys.argv[2] if len(sys.argv) > 2 else "2026-11-15"
SEASON0 = {"nfl": "2026-08-25", "ncaaf": "2026-08-15", "nba": "2026-10-15", "nhl": "2026-09-27", "ncaab": "2026-10-25",
           "mlb": "2026-03-15"}


def T(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def pday(iso):
    return T(iso).astimezone(PT).date()


def nm(x):
    x = str(x or "").lower().replace(" jr.", "").replace(" jr", "").replace(" iii", "").replace(" ii", "").replace(" iv", "")
    return " ".join(re.sub(r"[^a-z ]", "", x).split())


def same(a, b):
    a, b = nm(a), nm(b)
    if a == b:
        return True
    wa, wb = a.split(), b.split()
    if len(wa) < 2 or len(wb) < 2 or wa[-1] != wb[-1]:
        return False
    k = 1 if min(len(wa[0]), len(wb[0])) == 1 else 2
    return wa[0][:k] == wb[0][:k]


GAMES = sd.load_games()
BY = defaultdict(lambda: defaultdict(list))            # league -> team -> finals, oldest first
for g in GAMES.values():
    if g.get("status") == "final" and str(g.get("home_score", "")).strip() != "" and str(g.get("away_score", "")).strip() != "":
        for s in ("home", "away"):
            BY[g["league"]][g[s]].append(g)
for lg in BY:
    for t in BY[lg]:
        BY[lg][t].sort(key=lambda x: x["start"])
ROST = {}
QB = {}
QBN = {}
GOALIE = []


def roster(lg):
    if lg not in ROST:
        d = defaultdict(lambda: defaultdict(list))
        try:
            rows = sr.load(lg, seasons=[2026]) or sr.load(lg)
        except Exception:                                    # noqa: BLE001
            rows = []
        for r in rows:
            d[r["gid"]][r["team"]].append(r)
        ROST[lg] = d
    return ROST[lg]


def keyrows(lg):
    if lg not in QB:
        import csv
        p = os.path.join(sd.DATA, "players", f"{lg}.csv")
        QB[lg] = sorted(csv.DictReader(open(p)), key=lambda r: r["start"]) if os.path.exists(p) else []
    return QB[lg]


def res(g, tid):
    home = g["home"] == tid
    us, th = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    return us, th, ("W" if us > th else "L" if us < th else "T")


def neutral(g):
    return str(g.get("neutral")) in ("1", "True", "true")


def season(lg, tid, before):
    return [g for g in BY[lg].get(tid, []) if SEASON0[lg] <= g["start"] < before and str(g.get("stype") or "2") != "1"]


def rec(gs, tid):
    w = sum(res(g, tid)[2] == "W" for g in gs)
    lo = sum(res(g, tid)[2] == "L" for g in gs)
    return (w, lo, len(gs) - w - lo)


def facts_of(lg, tid, g):
    s = season(lg, tid, g["start"])
    reg = [x for x in s if str(x.get("stype") or "2") == "2"]
    out = {"rec": rec(reg, tid), "home": rec([x for x in reg if x["home"] == tid and not neutral(x)], tid),
           "road": rec([x for x in reg if x["away"] == tid and not neutral(x)], tid),
           "home_n": rec([x for x in reg if x["home"] == tid], tid), "road_n": rec([x for x in reg if x["away"] == tid], tid),
           "last5": rec(s[-5:], tid), "n": len(s), "games": s}
    st, n = "", 0
    for x in reversed(s):
        r = res(x, tid)[2]
        if not st:
            st = r
        if r != st:
            break
        n += 1
    out["streak"] = (st, n)
    nowin = 0
    for x in reversed(s):
        if res(x, tid)[2] == "W":
            break
        nowin += 1
    out["nowin"] = nowin
    out["rest"] = (pday(g["start"]) - pday(s[-1]["start"])).days if s else None
    out["scores"] = [(max(res(x, tid)[:2]), min(res(x, tid)[:2])) for x in s]
    for k, gs in (("l3", s[-3:]), ("yr", s), ("l5", s[-5:]), ("l10", s[-10:])):
        if gs:
            f = sum(res(x, tid)[0] for x in gs) / len(gs)
            a = sum(res(x, tid)[1] for x in gs) / len(gs)
            out[k] = (f, a)
    # last season
    y0 = SEASON0[lg]
    prev0 = str(int(y0[:4]) - 1) + y0[4:]
    ps = [x for x in BY[lg].get(tid, []) if prev0 <= x["start"] < y0 and str(x.get("stype") or "2") == "2"]
    out["prev"] = rec(ps, tid)
    psa = [x for x in BY[lg].get(tid, []) if prev0 <= x["start"] < y0 and str(x.get("stype") or "2") != "1"]
    out["prev_all"] = rec(psa, tid)
    return out


def played(lg, gid, tid):
    """{normalized name: True} of the men in this game's box score for the team (hoops: minutes > 0), or None."""
    rows = roster(lg).get(gid, {}).get(str(tid))
    if not rows:
        return None
    out = set()
    for r in rows:
        try:
            st = json.loads(r.get("stats") or "{}")
        except ValueError:
            st = {}
        if lg in ("nba", "ncaab"):
            try:
                if float(str(st.get("minutes") or 0).split(":")[0] or 0) <= 0:
                    continue
            except ValueError:
                continue
        if lg == "nhl" and r.get("group") == "goalies" and str(st.get("timeOnIce") or "0:00") in ("0:00", "", "00:00"):
            continue
        out.add(nm(r["player"]))
    return out


VEN = json.load(open(os.path.join(sd.DATA, "venues.json")))
PUB = (json.load(open(os.path.join(sd.DATA, "public.json"))).get("games") or {})


def where(g):
    v = VEN.get(f"{g.get('city') or ''}|{g.get('state') or ''}|{'' if (g.get('country') or 'USA') == 'USA' else g.get('country')}") \
        or VEN.get(f"{g.get('city') or ''}|{g.get('state') or ''}|")
    return (v[0], v[1]) if v else None


def miles(a, b):
    from math import asin, cos, radians, sin, sqrt
    if not a or not b:
        return None
    la1, lo1, la2, lo2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * asin(sqrt(h))


def home_of(lg, tid, before):
    hs = [where(x) for x in BY[lg].get(tid, []) if x["home"] == tid and not neutral(x) and x["start"] < before][-12:]
    hs = [h for h in hs if h]
    return Counter(hs).most_common(1)[0][0] if hs else None


def top_men(lg, tid, before, n=10):
    """The team's top-3 scorers over its last n box games (hoops / hockey), normalized names."""
    tot = Counter()
    gs = [x for x in BY[lg].get(tid, []) if x["start"] < before][-n:]
    for x in gs:
        for r in roster(lg).get(x["id"], {}).get(str(tid), []):
            try:
                st = json.loads(r.get("stats") or "{}")
            except ValueError:
                continue
            try:
                tot[nm(r["player"])] += float(st.get("points") or 0) if lg in ("nba", "ncaab") else float(st.get("goals") or 0) + float(st.get("assists") or 0)
            except ValueError:
                pass
    return [k for k, _ in tot.most_common(3)]


def in_box(name, box):
    return any(same(name, b) for b in box)


AM = re.compile(r"(?<![\d.:/+-])(\d{1,3})-(\d{1,3})(?:-(\d{1,2}))?(?![\d%:/]|\.\d|-\d)")
OUT_LEAD = re.compile(r"(?:without|missing|Out for [^:]+:|Not dressing for [^:]+:|\bout:|is down|are down|gotta play without|"
                      r"go(?:es)? without|playing without|won't have|minus)\s*", re.I)
NAME_POS = re.compile(r"((?:[A-Z][\w.'’-]*\s?){1,4}?)\s*\(([A-Z/]{1,3})\)")
POS_NAME = re.compile(r"\b(QB|RB|WR|TE|LB|CB|S|DE|DT|OT|OL|G|C|F|D|LW|RW|K|P|T|OG|DL|DB|PG|SG|SF|PF|EDGE|NT|FS|SS|LS)\s+((?:[A-Z][\w.'’-]*\s?){1,4}?)(?=,| ·|\.| \(|$| \+)")


def check_card(pk, leg):
    out = []                                                 # (type, verdict, detail, line)
    lg, gid = leg.get("league"), leg.get("game_id")
    g = GAMES.get(gid)
    if not g or leg.get("side") not in ("home", "away"):
        return [("card", "U", "no game file / a total", "")]
    side = leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg.get("team") or g[side + "_name"], leg.get("opp") or g[other + "_name"]
    F = {0: facts_of(lg, tid, g), 1: facts_of(lg, oid, g)}
    ids = {0: tid, 1: oid}
    names = [us, them]
    h2h = [x for x in BY[lg].get(tid, []) if oid in (x["home"], x["away"]) and x["start"] < g["start"]]
    box = {0: played(lg, gid, tid), 1: played(lg, gid, oid)} if g.get("status") == "final" else {0: None, 1: None}
    lines = [("why", leg.get("why_line"))] + [("bd", x) for x in leg.get("breakdown") or []]

    def anchor(t, pos):
        sp = []
        for i, n in enumerate(names):
            sp += [(m.start(), m.end(), i) for m in re.finditer(r"(?<!\w)" + re.escape(n) + r"(?!\w)", t)]
        sp = [x for x in sp if not any(y[0] <= x[0] and x[1] <= y[1] and (y[1] - y[0]) > (x[1] - x[0]) for y in sp)]
        b = [x for x in sp if x[1] <= pos]
        if b:
            return max(b, key=lambda x: x[1])[2]
        a = [x for x in sp if x[0] >= pos]
        return min(a, key=lambda x: x[0])[2] if a else None

    # ---------------- the stored inputs the read weighed (leg fields), against the game files
    radd0 = lambda ty, v, d="": out.append((ty, v, d, "READ INPUT"))   # noqa: E731
    dm = leg.get("dog_more") or {}
    if isinstance(dm.get("record"), list) and len(dm["record"]) >= 2:
        radd0("read input: the side's record", "T" if tuple(dm["record"][:2]) == F[0]["rec"][:2] else "F", f"{us} {dm['record']} vs the games {F[0]['rec']}")
    if dm.get("win_streak") is not None:
        ws = F[0]["streak"][1] if F[0]["streak"][0] == "W" else 0
        radd0("read input: the side's win streak", "T" if int(dm["win_streak"]) == ws else "F", f"{us} {dm['win_streak']} vs the games {ws}")
    if dm.get("last_margin") is not None and F[0]["games"]:
        a_, b_, _ = res(F[0]["games"][-1], tid)
        radd0("read input: the last game's margin", "T" if abs(float(dm["last_margin"]) - (a_ - b_)) < 0.5 else "F", f"{us} {dm['last_margin']} vs the games {a_ - b_}")
    def hrs(j):
        gs = F[j]["games"]
        return (T(g["start"]) - T(gs[-1]["start"])).total_seconds() / 3600 if gs else None
    if leg.get("b2b_me") is not None and hrs(0) is not None and lg == "nhl":
        radd0("read input: we're on a back-to-back", "T" if bool(leg["b2b_me"]) == (hrs(0) <= 30) else "F", f"{us}: {hrs(0):.0f} hours since the last game, the leg says {leg['b2b_me']}")
    if leg.get("rested_vs_b2b") is not None and hrs(0) is not None and hrs(1) is not None and lg in ("nba", "nhl"):
        radd0("read input: rested vs their back-to-back", "T" if bool(leg["rested_vs_b2b"]) == (hrs(1) <= 30 < hrs(0)) else "F",
              f"{hrs(0):.0f} vs {hrs(1):.0f} hours, the leg says {leg['rested_vs_b2b']}")
    if leg.get("home") is not None:
        radd0("read input: home / away", "T" if bool(leg["home"]) == (side == "home") else "F", side)
    for nm_ in leg.get("absent") or []:
        nm2 = re.sub(r"^(?:QB|RB|WR|TE)\s+", "", str(nm_))
        if box[0] is not None:
            radd0("read input: our key man out (absence weight)", "F" if in_box(nm2, box[0]) else "T", f"{nm2} {'PLAYED' if in_box(nm2, box[0]) else 'sat'}")
    for r_ in leg.get("reasons") or []:
        radd = lambda ty, v, d="": out.append((ty, v, d, "REASON: " + r_))   # noqa: E731
        if r_ == "opponent on a back-to-back":
            radd("reason: opponent on a back-to-back", "T" if F[1]["rest"] == 1 else "F", f"{them}: {F[1]['rest']} days since their last game")
        elif r_ == "coming off a bye":
            radd("reason: coming off a bye", "T" if (F[0]["rest"] or 0) >= 13 else "F", f"{us}: {F[0]['rest']} days since their last game")
        elif r_ == "better rested":
            radd("reason: better rested", "T" if (F[0]["rest"] or 0) > (F[1]["rest"] or 0) else "F", f"{F[0]['rest']} vs {F[1]['rest']} days")
        elif r_ == "opponent on a short week":
            radd("reason: opponent on a short week", "T" if (F[1]["rest"] or 9) <= 5 else "F", f"{them}: {F[1]['rest']} days")
        elif r_ == "rolling off a blowout win":
            lg_ = F[0]["games"][-1:]
            mg = (res(lg_[0], tid)[0] - res(lg_[0], tid)[1]) if lg_ else 0
            radd("reason: rolling off a blowout win", "T" if mg >= {"nfl": 14, "ncaaf": 17}.get(lg, 10) else "F", f"{us} last game margin {mg:+d}")
        elif r_ == "hotter recent form":
            radd("reason: hotter recent form", "U", "a model number")
        elif r_ == "better QB play lately":
            act = {r["team"]: r["player"] for r in keyrows(lg) if r["gid"] == gid}
            said = [q for q in re.findall(r"([A-Z][\w.'-]+ [A-Z][\w.'-]+(?: [A-Z][\w.'-]+)?) has \d+ TDs?", " ".join(leg.get("breakdown") or []))]
            if not act:
                radd("reason: better QB play lately", "U", "no box score yet")
            else:
                import sports_players as sp
                rows_ = keyrows(lg)
                bad = []
                for j in (0, 1):
                    was = sp.last_starter(rows_, ids[j], g["start"])
                    if was and act.get(ids[j]) and not same(was, act[ids[j]]):
                        bad.append(f"{names[j]}: weighed {was}, {act[ids[j]]} started")
                radd("reason: better QB play lately", "F" if bad else "T", "; ".join(bad) or f"both QBs the read used started ({list(act.values())})")
        elif r_.startswith("opponent missing key players:"):
            ppl = re.findall(r"(?:QB|RB|WR|TE|G|D|C|F|LW|RW)?\s*((?:[A-Z][\w.'’-]+ ?){2,3})(?=,| \(|$)", r_.split(":", 1)[1])
            for p_ in dict.fromkeys(x.strip() for x in ppl):
                if box[1] is None:
                    radd("reason: opponent missing a named key man", "U", f"{p_}: no box score")
                else:
                    radd("reason: opponent missing a named key man", "F" if in_box(p_, box[1]) else "T", f"{p_} {'PLAYED' if in_box(p_, box[1]) else 'sat'}")
            for pos_, p_ in re.findall(r"\b(QB|RB|WR|TE) ((?:[A-Z][\w.'’-]+ ?){2,3})", r_):
                pass
    for where_, t in lines:
        if not t or not isinstance(t, str):
            continue
        add = lambda ty, v, d="": out.append((ty, v, d, t))   # noqa: E731
        low = t.lower()
        bottom = bool(re.match(r"^\W*(?:✅|🟡)\s*Bottom line", t))
        # ---------------- who's out
        if re.match(r"^\W*(?:🚑|⚠️)", t) and (OUT_LEAD.search(t) or "out:" in low) and "questionable:" not in low.split("out:")[0]:
            seg = t.split("questionable:")[0]
            who_i = None
            m = re.search(r"(?:Out for|Not dressing for)\s+(?:the )?([^:]+):", seg)
            if m:
                who_i = names.index(m.group(1).strip()) if m.group(1).strip() in names else None
            if who_i is None:
                ml = OUT_LEAD.search(seg) or re.search(r"out:", seg)
                who_i = anchor(seg, ml.start() + 1) if ml else None
            ppl = [a.strip() for a, _ in NAME_POS.findall(seg)] or [b.strip() for _, b in POS_NAME.findall(seg)]
            ppl = [p for p in ppl if p and p not in names and len(p) > 2]
            if who_i is not None and ppl:
                bx = box[who_i]
                for p in ppl:
                    if bx is None:
                        add("out", "U", f"{p}: no box score for {names[who_i]}")
                    elif in_box(p, bx):
                        add("out", "F", f"{p} listed out for {names[who_i]} - he PLAYED")
                    else:
                        add("out", "T", p)
            elif ppl:
                add("out", "U", "couldn't tell whose list")
        elif re.match(r"^\W*(?:🚑|🌟|⚠️)", t) and re.search(r"won't suit up for|^\W*🚑 No |(?:is|are) out\b", t):
            seg = t.split("questionable:")[0]
            tn = [n_ for n_ in names if re.search(r"(?<!\w)" + re.escape(n_) + r"(?!\w)", seg)]
            who_i = names.index(tn[0]) if len(tn) == 1 else None
            ppl = [a.strip() for a, _ in NAME_POS.findall(seg)]
            if not ppl:
                mo_ = re.search(r"(?:·|:)\s*([^·:]+?) (?:is|are) out\b", seg) or re.search(r"\b((?:[A-Z][\w.'’-]+ ?){2,4}) is out\b", seg)
                ppl = [x.strip() for x in re.split(r", | and ", mo_.group(1))] if mo_ else []
            ppl = [re.sub(r"^(?:No|Biggest knock on \w+:)\s+", "", p_) for p_ in ppl if p_ and p_ not in names]
            for p_ in ppl:
                if who_i is None or box[who_i] is None:
                    add("out", "U", f"{p_}: couldn't check")
                else:
                    add("out", "F" if in_box(p_, box[who_i]) else "T", f"{p_} listed out for {names[who_i]}" + (" - he PLAYED" if in_box(p_, box[who_i]) else ""))
        if "questionable" in low and re.match(r"^\W*🚑", t):
            add("questionable", "U", "a status, either way is fine")
        # ---------------- healthy claims
        if re.search(r"full squad|everybody available|at full strength|is healthy|nobody (?:big|important|on)|whole squad", low):
            i = anchor(t, len(t)) if anchor(t, len(t)) is not None else 0
            if lg in ("nba", "ncaab", "nhl") and box[i] is not None:
                sat = [m_ for m_ in top_men(lg, ids[i], g["start"]) if not in_box(m_, box[i])]
                add("'full squad' claim", "F" if sat else "T", f"{names[i]}: top-3 scorers who sat: {sat}" if sat else names[i])
            else:
                add("'full squad' claim", "U", "no box score to check it")
        # ---------------- stars in the lineup
        if t.lstrip().startswith("🌟") and "in the lineup" in low:
            m = re.match(r"^\W*([\w .']+?):\s*(.*?)\s+(?:is|are) in the lineup", t)
            if m:
                i = names.index(m.group(1)) if m.group(1) in names else None
                stars = [x.strip() for x in re.split(r" and |, ", re.sub(r"\s*\([^)]*\)", "", m.group(2)))]
                for s_ in stars:
                    if not s_ or i is None or box[i] is None:
                        add("star in lineup", "U", s_)
                    else:
                        add("star in lineup", "T" if in_box(s_, box[i]) else "F", f"{s_} {'played' if in_box(s_, box[i]) else 'DID NOT PLAY'}")
        # ---------------- QB lines
        if lg in ("nfl", "ncaaf"):
            qbn = QBN.setdefault(lg, sorted({r["player"] for r in keyrows(lg) if r["start"] >= SEASON0[lg]}, key=len, reverse=True))
            prev_end = 0
            for m in re.finditer(r"(\d+) TDs?, (\d+) picks? and ([\d,]+) yards in his last (\d+) games?( against FBS teams)?", t):
                head = t[prev_end:m.start()]
                prev_end = m.end()
                found = [(head.rfind(q), q) for q in qbn if q in head]
                if not found:
                    add("QB stats", "U", "couldn't find whose numbers")
                    continue
                name = max(found)[1]
                td, it, yd, n = int(m.group(1)), int(m.group(2)), int(m.group(3).replace(",", "")), int(m.group(4))
                rows = [r for r in keyrows(lg) if r["player"] == name and SEASON0[lg] <= r["start"] < g["start"]]
                team_of = rows[-1]["team"] if rows else None
                i = 0 if team_of == tid else 1 if team_of == oid else None
                if m.group(5):
                    add("QB stats", "U", f"{name}: FBS-only sums not rebuilt here")
                else:
                    lastn = rows[-n:]
                    sums = tuple(int(round(sum(float(r[k] or 0) for r in lastn))) for k in ("td", "int", "yds"))
                    okn = (td, it, yd) == sums and len(lastn) == n
                    add("QB stats", "T" if okn else "F", f"{name} {td}/{it}/{yd} in {n}" + ("" if okn else f" - the box scores say {sums} in {len(lastn)}"))
                act = [r for r in keyrows(lg) if r["gid"] == gid]
                if i is None:
                    add("QB named", "F", f"{name}'s last start was for another team")
                elif not act:
                    add("QB named", "U", f"{name}: no box score yet")
                else:
                    a = next((r["player"] for r in act if r["team"] == ids[i]), None)
                    add("QB named", "T" if a and same(a, name) else "F", f"{name} named for {names[i]} - {a} started")
        # ---------------- goalie lines
        if lg == "nhl":
            for m in re.finditer(r"((?:[A-Z][\w.'’-]+ )+[A-Z][\w.'’-]+)", t):
                name = m.group(1).strip()
                name = re.sub(r"^(?:Good luck scoring on|Pucks keep getting past|Goalies|Yeah|The|What could fuck this up:|The other side's best argument:)\s+", "", name)
                rows = [r for r in keyrows("nhl") if same(r["player"], name)]
                if not rows or name in names:
                    continue
                team_of = [r for r in rows if r["start"] < g["start"]][-1:]
                if not team_of:
                    continue
                i = 0 if team_of[0]["team"] == tid else 1 if team_of[0]["team"] == oid else None
                act = [r for r in keyrows("nhl") if r["gid"] == gid]
                a = next((r["player"] for r in act if i is not None and r["team"] == ids[i]), None)
                after = t[m.end():m.end() + 90].lower()
                before = t[max(0, m.start() - 60):m.start()].lower()
                ctxw = before + " | " + after
                kind = ("projected" if "project" in ctxw else "last starter" if re.search(r"last time out|last starter|if he goes again|in net last", ctxw)
                        else "confirmed" if "confirm" in ctxw or "expected" in ctxw or "likely" in ctxw else "plain")
                if i is None:
                    add(f"goalie named ({kind})", "F", f"{name} isn't on either team")
                elif not act:
                    add(f"goalie named ({kind})", "U", f"{name}: no box")
                else:
                    started = bool(a and same(a, name))
                    GOALIE.append((pk["date"], names[i], name, kind, a, started))
                    if kind == "last starter":
                        prev_g = [r for r in keyrows("nhl") if r["team"] == ids[i] and r["start"] < g["start"]][-1:]
                        okl = bool(prev_g and same(prev_g[0]["player"], name))
                        add("goalie 'in net last time out'", "T" if okl else "F", f"{name} for {names[i]} - last starter {prev_g[0]['player'] if prev_g else None}; tonight {a}")
                    elif kind == "projected":
                        add("goalie 'projected' (a guess, said as one)", "U", f"{name} for {names[i]} - {a} started ({'right' if started else 'WRONG'})")
                    else:
                        add(f"goalie named as tonight's ({kind})", "T" if started else "F", f"{name} for {names[i]} - {a} started")
                ms = re.search(r"(0\.\d{3}) save %(?: \((\d+) goals on (\d+) shots\))? over his last (\d+) starts?", t[m.end():m.end() + 110])
                if ms and not re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", t[m.end():m.end() + ms.start()].replace("Golden Knights", "").replace("Maple Leafs", "").replace("Blue Jackets", "").replace("Red Wings", "")):
                    n = int(ms.group(4))
                    mine = [r for r in rows if r["start"] < g["start"] and r["start"] >= SEASON0["nhl"]][-n:]
                    sa, ga = sum(float(r["sa"] or 0) for r in mine), sum(float(r["ga"] or 0) for r in mine)
                    pct = (sa - ga) / sa if sa else 0
                    ok = len(mine) == n and abs(pct - float(ms.group(1))) < 0.0015 and (not ms.group(2) or (int(ms.group(2)) == ga and int(ms.group(3)) == sa))
                    add("goalie stats", "T" if ok else "F", f"{name} {ms.group(0)} - the box scores say {pct:.3f} ({ga:.0f} on {sa:.0f}) in {len(mine)}")
        # ---------------- streaks
        for rx, kind in ((r"(\d+) straight (?:W'?s|wins)|won (\d+) (?:straight|in a row)|(\d+) wins in a row|(\d+)-game (?:heater|winning streak)|heater - (\d+) straight|haven'?t lost in (\d+)|(\d+) straight for", "W"),
                         (r"(?:dropped|lost) (\d+) (?:straight|in a row)|(\d+) straight L'?s|(\d+) losses in a row|(\d+) L'?s in a row|L'?s\W+(\d+) straight", "L")):
            for m in re.finditer(rx, t, re.I):
                n = int(next(x for x in m.groups() if x))
                i = anchor(t, m.start())
                if i is None:
                    add("streak", "U", "no team")
                    continue
                st = F[i]["streak"]
                add("streak", "T" if st == (kind, n) else "F", f"{names[i]} {kind}{n} - the games say {st[0]}{st[1]}")
        m = re.search(r"hasn'?t won in (\d+)", t)
        if m:
            i = anchor(t, m.start())
            if i is not None:
                add("streak", "T" if F[i]["nowin"] == int(m.group(1)) else "F", f"{names[i]} no win in {m.group(1)} - the games say {F[i]['nowin']}")
        # ---------------- last 5
        m = re.search(r"(?:dropped|lost|won) (\d) of (?:the|their) last (?:5|five)|(\d) of the last 5 went ([\w .']+?)'s? way", t)
        if m:
            if m.group(1):
                i = anchor(t, m.start())
                n = int(m.group(1))
                if i is not None and F[i]["n"] >= 5:
                    v = F[i]["last5"][0 if "won" in m.group(0) else 1]
                    add("last 5", "T" if v == n else "F", f"{names[i]} {m.group(0)} - the games say {F[i]['last5']}")
            else:
                nmx = m.group(3).rstrip("'")
                i = names.index(nmx) if nmx in names else None
                if i is not None:
                    add("last 5", "T" if F[i]["last5"][0] == int(m.group(2)) else "F", f"{names[i]} {m.group(0)} - the games say {F[i]['last5']}")
        # ---------------- records and scores
        if not re.search(r"last (?:season|year)|a year ago|finished", low):
            for m in AM.finditer(t):
                a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
                if (a, b) == (50, 50) or bottom and not re.search(r"loss|win|beat|L to|W over", t[m.end():m.end() + 25] + t[max(0, m.start() - 30):m.start()]):
                    continue
                before, after = t[:m.start()], t[m.end():]
                seg = t[max(0, m.start() - 45):m.end() + 40]
                i = anchor(t, m.start())
                mm = re.match(r"\s*(?:\(|for (?:the )?|at home for (?:the )?|on the road for (?:the )?|away from home this year for )(" + "|".join(re.escape(n) for n in names) + r")\b", after)
                if mm:
                    i = names.index(mm.group(1))
                tok = (a, b, c)
                truths = {}
                for j in (0, 1):
                    f = F[j]
                    truths[(j, "rec")] = tok == f["rec"]
                    truths[(j, "home")] = tok == f["home"]
                    truths[(j, "road")] = tok == f["road"]
                    truths[(j, "last5")] = tok == f["last5"] and f["n"] >= 5
                    truths[(j, "score6")] = c == 0 and (max(a, b), min(a, b)) in f["scores"][-6:]
                    truths[(j, "lastscore")] = c == 0 and (max(a, b), min(a, b)) in f["scores"][-1:]
                    truths[(j, "home_neutral")] = tok == f["home_n"] and tok != f["home"]
                    truths[(j, "road_neutral")] = tok == f["road_n"] and tok != f["road"]
                truths[(0, "h2h")] = truths[(1, "h2h")] = c == 0 and any((max(a, b), min(a, b)) == (max(res(x, tid)[:2]), min(res(x, tid)[:2])) for x in h2h[-3:])
                is_score = bool(re.search(r"^\s*(?:win|loss|L\b|W\b|beating|final|tie)|^\s*(?:@|vs\.?) [A-Z]|^\s*(?:over|by) (?:the )?[A-Z]|^\.\s*That'?s what", after)
                                or re.search(r"(?:\b[WL]|brakes off [\w.' ]+,|(?:smacked|spanked|clapped|embarrassed|beat|beat the|put|blanked|got beat|got smacked|got embarrassed|cheeks clapped) [\w.' ]{0,30}?)\s*$", before)
                                or max(a, b) > 16 and lg != "nhl" or re.search(r"took [\w.' ]{1,25}$", before))
                if re.search(r"last time these two met|last meeting", t, re.I) and is_score:
                    add("h2h score", "T" if truths[(0, "h2h")] else "F", f"{tok} - the meetings: {[res(x, tid)[:2] for x in h2h[-3:]]}")
                    continue
                if is_score:
                    last_w = re.search(r"last time|last game|latest|just (?:beat|took|got|rolled|smacked)|come in off|comes? off|coming off|are off|is off|after an? |how they came in|where they'?re coming from|off an? ", seg, re.I) \
                        and not re.search(r"inside their last|within their last|in one of their last|not long ago", t, re.I)
                    kind = "lastscore" if last_w else "score6"
                    cands = [j for j in (0, 1) if truths[(j, kind)]]
                    if i is not None and truths[(i, kind)]:
                        add("last-game score" if kind == "lastscore" else "recent score", "T", f"{tok}")
                    elif cands:
                        add("last-game score" if kind == "lastscore" else "recent score", "T", f"{tok} (the other team's game)")
                    elif any(truths[(j, "score6")] for j in (0, 1)):
                        add("last-game score", "F", f"{tok} said as the last game - it's an older one; last: {F[i if i is not None else 0]['scores'][-1:]}")
                    elif truths[(0, "h2h")]:
                        add("h2h score", "T", f"{tok}")
                    else:
                        add("recent score", "F", f"{tok} is in neither team's last 6: {F[0]['scores'][-6:]} / {F[1]['scores'][-6:]}")
                    continue
                seg = seg.replace("away from home", "on the road")
                home_w = re.search(r"at home|their (?:own )?building|own building|in the crib|home cooking|home this|\bhome\b", seg, re.I)
                road_w = re.search(r"on the road|away from home|road this|\broad\b|\baway\b|other people", seg, re.I)
                l5_w = re.search(r"last (?:5|five)", seg, re.I)
                kind = "last5" if l5_w else "home" if home_w and not road_w else "road" if road_w and not home_w else "rec"
                label = {"rec": "season record", "home": "home record", "road": "road record", "last5": "last-5 record"}[kind]
                if i is not None and truths[(i, kind)]:
                    add(label, "T", f"{names[i]} {tok}")
                elif i is None and any(truths[(j, kind)] for j in (0, 1)):
                    add(label, "T", f"{tok}")
                elif i is not None and kind in ("home", "road") and truths[(i, kind + "_neutral")]:
                    add(label, "F", f"{names[i]} {tok} counts a neutral-site game - the games say {F[i][kind]}")
                elif any(truths[(1 - i if i is not None else 0, kind)] for _ in (0,)) and i is not None and kind == "rec" and truths[(1 - i, "rec")]:
                    add(label, "T", f"{tok} (anchored to the other name)")
                elif kind == "rec" and any(truths[(j, "rec")] for j in (0, 1)) and len(AM.findall(t)) >= 2:
                    add(label, "T", f"{tok} (two records on the line)")
                elif i is not None:
                    add(label, "F", f"{names[i]} {tok} - the games say {F[i][kind]} (rec {F[i]['rec']}, home {F[i]['home']}, road {F[i]['road']})")
                else:
                    add(label, "U", f"{tok}: no team")
        else:
            for m in AM.finditer(t):
                tok = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
                if max(tok) > 82 or (tok[0], tok[1]) == (50, 50):
                    continue
                ok = any(tok in (F[j]["prev"], F[j]["prev_all"]) for j in (0, 1))
                near = any(abs(tok[0] - F[j][k][0]) + abs(tok[1] - F[j][k][1]) <= 3 for j in (0, 1) for k in ("prev", "prev_all"))
                add("last season's record", "T" if ok else "U" if near else "F", f"{tok} - the files say {F[0]['prev']} / {F[0]['prev_all']} and {F[1]['prev']} / {F[1]['prev_all']}")
        # ---------------- rest
        for m in re.finditer(r"(?:had|on|got) (\d+) days?(?: of)? (?:off|rest)|(\d+) days? (?:off|rest)|on (\d+) days", t):
            n = int(next(x for x in m.groups() if x))
            if re.search(r"more days|extra days|fewer days|more days? off than|fewer days? off than", t):
                break
            i = anchor(t, m.start())
            if i is None or F[i]["rest"] is None:
                continue
            ok = n in (F[i]["rest"], F[i]["rest"] - 1)
            add("rest days", "T" if ok else "F", f"{names[i]} {n} days - the games say {F[i]['rest']} days since the last game")
        m = re.search(r"(\d+) (?:more|extra|fewer) days?(?: of rest| off| to rest)?", t)
        if m and F[0]["rest"] is not None and F[1]["rest"] is not None:
            d = abs(F[0]["rest"] - F[1]["rest"])
            add("rest gap", "T" if d == int(m.group(1)) else "F", f"says {m.group(1)} - the games say {F[0]['rest']} vs {F[1]['rest']}")
        if re.search(r"played (?:yesterday|last night)|second night in a row|second night of a back", low):
            mm_ = re.search(r"played (?:yesterday|last night)|second night in a row|second night of a back", t, re.I)
            i = anchor(t, mm_.start())
            if re.search(r"second night in a row for (?:the )?", t, re.I):
                nm2 = re.search(r"second night in a row for (?:the )?([\w .']+?)(?:,|\.| —| -|$)", t, re.I)
                if nm2 and nm2.group(1).strip() in names:
                    i = names.index(nm2.group(1).strip())
            if i is not None and F[i]["rest"] is not None:
                add("back-to-back", "T" if F[i]["rest"] == 1 else "F", f"{names[i]} - {F[i]['rest']} days since the last game")
        if re.search(r"\bbye\b", low) and lg in ("nfl", "ncaaf"):
            i = anchor(t, low.find("bye"))
            if i is not None and F[i]["rest"] is not None:
                add("bye", "T" if F[i]["rest"] >= 13 else "F", f"{names[i]} - {F[i]['rest']} days since the last game")
        # ---------------- scoring averages
        if re.search(r"a game|a night|for / |for, |last 3|per game|scored, ", t) and not bottom and not re.search(r"last season|a year ago|per 48|save %|straight|overall|on the year,|heater", low) and not re.match(r"^\W*(?:🧳|🥊|📅|📋|💪|🔥|⚖️|🗑️|🧊|🏟️|🚑|⚠️|🌟|🏀|🗓️)", t):
            yr = bool(re.search(r"this (?:year|season)|on the year|on the season", low))
            l3 = bool(re.search(r"last 3|lately", low))
            nums = [(mm_.start(), float(mm_.group(0))) for mm_ in re.finditer(r"(?<![\d.+-])\d{1,3}(?:\.\d)?(?![\d%°-]|\.\d)", t)]
            skip_after = re.compile(r"^\s*(?:straight|of |games?|days?|-|%|mile|°|TDs?|picks?|yards|starts?|guys|road|rd|st|nd|th|wins|in a row|more|extra)")
            for pos, v in nums:
                if skip_after.search(t[pos + len(str(int(v))):][:12]) or re.search(r"last $|\($|[+-]$", t[:pos], re.I) or t[pos:pos + 5] in ("76ers", "49ers"):
                    continue
                if v == 3 and re.search(r"last $", t[:pos]):
                    continue
                okv = False
                for j in (0, 1):
                    for k in (("yr",) if yr and not l3 else ("l3",) if l3 and not yr else ("yr", "l3")):
                        if k in F[j]:
                            for x in F[j][k]:
                                if abs(x - v) < (0.06 if "." in str(v) and lg == "nhl" and v != int(v) else 0.51):
                                    okv = True
                add("scoring average", "T" if okv else "F",
                    f"{v:g} - last 3: {[tuple(round(x, 1) for x in F[j].get('l3', ())) for j in (0, 1)]}, year: {[tuple(round(x, 1) for x in F[j].get('yr', ())) for j in (0, 1)]}")
        # ---------------- road trips / schedule spots
        m = re.search(r"(\d)(?:rd|th|nd) road game in (\d+) days|after (\d) road games in (\d+) days", t)
        if m:
            i = anchor(t, m.start())
            k, d = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
            if i is not None:
                gs = F[i]["games"]
                recent = [x for x in gs if (pday(g["start"]) - pday(x["start"])).days < d]
                away_n = sum(x["away"] == ids[i] for x in recent) + (0 if m.group(3) else int(g["away"] == ids[i]))
                add("schedule spot", "T" if away_n == k else "F", f"{names[i]} {m.group(0)} - the games say {away_n} road games in that window")
        mm_ = re.search(r"(\d[\d,]*)-mile", t)
        if mm_:
            said = int(mm_.group(1).replace(",", ""))
            i = anchor(t, mm_.start())
            here = where(g)
            cands = []
            if i is not None:
                pg = F[i]["games"][-1:]
                if pg:
                    cands.append(miles(where(pg[0]), here))
                    cands.append(miles(where(pg[0]), home_of(lg, ids[i], g["start"])))
                cands.append(miles(home_of(lg, ids[i], g["start"]), here))
            cands = [c for c in cands if c]
            ok = any(abs(c - said) <= max(60, 0.08 * said) for c in cands)
            add("travel miles", "T" if ok else "U" if not cands else "F", f"{said} miles - by the venues: {[round(c) for c in cands]}")
        if re.search(r"\d+% of|% of the|\d+%", t) and re.search(r"bets|money|tickets|action|public|crowd|cash", low):
            pb = PUB.get(gid)
            pcts = [int(x) for x in re.findall(r"(\d{2,3})%", t)]
            if not pb or not pcts:
                add("public split", "U", "no split on file for this game")
            else:
                pool = [v for k_, v in pb.items() if k_.endswith(("_t", "_m")) and isinstance(v, (int, float))]
                ok = all(any(abs(v - x) <= 8 for v in pool) for x in pcts)
                add("public split", "T" if ok else "U", f"{pcts} vs the last split on file {sorted(set(pool))}" + ("" if ok else " (moved since, or not the same pull)"))
        if re.search(r"°", t):
            m = re.search(r"(\d+)\s*°", t)
            wx = g.get("wx_temp")
            add("weather", "T" if wx not in (None, "") and abs(float(wx) - int(m.group(1))) <= 3 else "U", f"{m.group(1)}° vs the game file's {wx}")
        if re.search(r"shooting (?:%|plus)|per 48|4th-down|goal totals say|should be about|All-NBA|All-Star|bowl trip|time zones", t) and not t.lstrip().startswith("🌟"):
            add("derived stat (luck / bench / 4th down)", "U", "not rebuilt here")
        if t.lstrip().startswith(("🧯", "📣", "🤒")):
            add("news line", "U", "read by hand")
    return out


def main():
    picks = json.load(open(os.path.join(sd.DATA, "picks.json")))
    rows = []
    for pk in picks:
        if not SINCE <= pk.get("date", "") <= UNTIL:
            continue
        for leg in pk.get("legs") or []:
            for ty, v, d, line in check_card(pk, leg):
                rows.append({"date": pk["date"], "league": leg.get("league"), "team": leg.get("team"), "kind": pk.get("kind"),
                             "units": pk.get("units"), "type": ty, "verdict": v, "detail": d, "line": line})
    c = defaultdict(Counter)
    for r in rows:
        c[r["type"]][r["verdict"]] += 1
    print(f"{'claim type':42s}  true false can't-check")
    tot = Counter()
    for ty in sorted(c, key=lambda k: -sum(c[k].values())):
        print(f"{ty:42s}  {c[ty]['T']:4d} {c[ty]['F']:5d} {c[ty]['U']:5d}")
        tot.update(c[ty])
    print(f"{'ALL':42s}  {tot['T']:4d} {tot['F']:5d} {tot['U']:5d}")
    gk = Counter((k, s_) for _, _, _, k, _, s_ in set(GOALIE))
    print("\nGOALIES NAMED vs WHO STARTED:", {f"{k} {'right' if s_ else 'wrong'}": v for (k, s_), v in sorted(gk.items())})
    print("\nFALSE:")
    for r in rows:
        if r["verdict"] == "F":
            print(f" {r['date']} {r['league']} {r['team']} [{r['type']}] {r['detail']}\n      {r['line'][:230]}")
    json.dump({"since": SINCE, "until": UNTIL, "counts": {k: dict(v) for k, v in c.items()}, "rows": rows},   # (not kept in the repo - rerun)
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
