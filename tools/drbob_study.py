"""DR. BOB vs THE ENGINE (10/6, the owner: "run a blind study test on all the games that the engine sides with Bob Stoll
and see if we're profitable on the games that we side with him" - and should his agreeing raise our confidence / units?).

Data: Bob Stoll's archived free NFL analysis pages (web.archive.org snapshots of drbobsports.com/nfl-analysis, one text
file per snapshot, fetched beforehand into a folder - the first line is the URL with the snapshot time). Every free SIDE
he posted (Lean / Strong Opinion / N-Star Best Bet, plus the bare "TEAM (-3) over OTHER" headline) is read with the number
he gave, matched to our NFL game (same two teams, kickoff within a day of his listed date) and counted ONCE (first
snapshot that shows it). Only picks on games that kicked off AFTER the snapshot count - a page captured after the game
is hindsight. Totals, team totals, teasers, first halves and props are skipped (sides only - that's what the engine reads).

The engine's read is BLIND: the spread model (sports_model.tune: Elo + situational weights 'sw') is fit on the 3 seasons
before the one being graded, the Elo ratings run chronologically, and the game-day injury inputs are zeroed (only what
is known midweek). The engine's side on a game = the side its own margin read likes against the CLOSING spread
(data/sports/games spread_home - the real close, no look-ahead).

Graded ATS at the closing line (-110 flat) and at Bob's own number (his price where he gave one, else -110):
  (a) engine and Bob on the SAME side, (b) opposite sides, (c) Bob alone, (d) the engine alone on every NFL game with a
  closing spread in the same weeks (its baseline), per season, with the standard error. Report only: nothing here
  touches a pick, a weight or a unit. Prints the report and writes results/drbob_study.json.

Run: python tools/drbob_study.py [folder with Bob's page texts]"""
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

DEFAULT_DIR = os.environ.get("DRBOB_PAGES", "")
OUT = os.path.join("results", "drbob_study.json")
SEASONS = (2020, 2021, 2022, 2023, 2024, 2025)
JUICE = 1 + 100 / 110                                              # -110
KICK = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\w{3}) (\d{1,2}) ")
TIER = re.compile(r"^(?P<tier>Lean|Strong Opinion|(?P<stars>\d)-Star Best Bet)\s*[–-]\s*(?P<rest>.*)$")
SIDE = re.compile(r"^\*{0,2}(?P<who>[A-Za-z .'&]+?)\s*\((?P<line>[+-]?\d+(?:\.5)?|pk|PK|pick)(?:/[+-]?\d+(?:\.5)?)?"
                  r"(?:\s+(?P<px>[+-]\d{3}))?\)(?P<tail>.*)$")
TOT = re.compile(r"^\*{0,2}(Over|Under|First Half|Team Total)", re.I)
BARE = re.compile(r"^(?P<who>[A-Z][A-Za-z .'&]+?)\s*\((?P<line>[+-]\d+(?:\.5)?)(?:/[+-]?\d+(?:\.5)?)?(?:\s+(?P<px>[+-]\d{3}))?\)"
                  r" over (?P<other>[A-Z][A-Za-z .'&]+)$")
MODEL = re.compile(r"[Oo]ur model (?:makes (?:the )?(?P<a>[A-Za-z .'&]+?) a (?P<pa>\d+(?:\.\d)?)-point favorite"
                   r"|favors (?:the )?(?P<b>[A-Za-z .'&]+?) by (?P<pb>\d+(?:\.\d)?) points?)")
SKIP = {"ny", "la", "the", "new", "york", "los", "angeles", "bay", "city", "san", "st", "louis", "las", "vegas", "green",
        "tampa", "kansas", "england"}
NICK = {"cincy": "cincinnati", "niners": "francisco", "pats": "patriots", "bucs": "buccaneers", "skins": "washington",
        "jags": "jacksonville", "fins": "miami", "jets": "jets", "giants": "giants", "rams": "rams", "chargers": "chargers"}


def _team(short, away, home):
    """'NY GIANTS' / 'Cleveland' / 'Los Angeles' / 'New York' -> 'away' or 'home' by the full names in his game header."""
    w = {NICK.get(x, x) for x in re.findall(r"[a-z0-9]+", short.lower())}
    core = w - SKIP
    for words in (core, w):
        hits = [s for s, full in (("away", away), ("home", home)) if words & set(re.findall(r"[a-z0-9]+", full.lower()))]
        if len(hits) == 1:
            return hits[0]
        if words:
            break
    return None


def _snap(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [x.rstrip("\n") for x in f]
    m = re.search(r"web\.archive\.org/web/(\d{14})/https?://(?:www\.)?drbobsports\.com/nfl-analysis", lines[0] if lines else "")
    if not m:
        return None, []
    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc), lines


def parse(lines, year):
    """[{away, home, date, picks: [{side, line, price, tier}], model: (side, pts) | None}] from one snapshot's text."""
    games = []
    for i, x in enumerate(lines):
        if x.strip() != "@" or i == 0 or i + 2 >= len(lines) or not KICK.match(lines[i + 2]):
            continue
        m = KICK.match(lines[i + 2])
        try:
            d = datetime.strptime(f"{m.group(2)} {m.group(3)} {year}", "%b %d %Y").date()
        except ValueError:
            continue
        games.append({"away": lines[i - 1].strip(), "home": lines[i + 1].strip(), "date": d.isoformat(), "at": i,
                      "picks": [], "model": None})
    for n, g in enumerate(games):
        end = games[n + 1]["at"] - 1 if n + 1 < len(games) else len(lines)
        for x in lines[g["at"]:end]:
            x = x.strip()
            t = TIER.match(x)
            if t:
                tier = "best_bet" if t.group("stars") else ("strong" if t.group("tier") == "Strong Opinion" else "lean")
                if "Teaser" in t.group("tier") or "Teaser" in x.split("–")[0]:
                    continue
                first = re.split(r"\s+[–-]\s+", t.group("rest"))[0]
                if TOT.match(first):
                    continue                                       # a total: what follows the dash is the game, not a side
                s = SIDE.match(first)
                if s and "team total" not in x.lower() and "teaser" not in x.lower() and _team(s.group("who"), g["away"], g["home"]):
                    ln = s.group("line").lower()
                    g["picks"].append({"side": _team(s.group("who"), g["away"], g["home"]), "tier": tier,
                                       "stars": int(t.group("stars")) if t.group("stars") else 0,
                                       "line": 0.0 if ln in ("pk", "pick") else float(ln),
                                       "price": int(s.group("px")) if s.group("px") else None})
                continue
            b = BARE.match(x)
            if b and _team(b.group("who"), g["away"], g["home"]) and _team(b.group("other"), g["away"], g["home"]):
                g["picks"].append({"side": _team(b.group("who"), g["away"], g["home"]), "tier": "headline", "stars": 0,
                                   "line": float(b.group("line")), "price": int(b.group("px")) if b.group("px") else None})
                continue
            mm = MODEL.search(x)
            if mm and g["model"] is None:
                who, pts = (mm.group("a"), mm.group("pa")) if mm.group("a") else (mm.group("b"), mm.group("pb"))
                side = _team(who, g["away"], g["home"])
                if side:
                    g["model"] = [side, float(pts)]
        del g["at"]
    return games


def _ours(games, bob):
    """Our NFL game for his: his 'New York Giants' = our 'Giants' ('Washington Football Team' = 'Washington')."""
    def hit(full, short):
        return (short or "").lower() in set(re.findall(r"[a-z0-9]+", full.lower()))
    d = datetime.fromisoformat(bob["date"]).date()
    for g in games.values():
        if g.get("league") != "nfl" or not g.get("start") or (g.get("stype") or "?") not in sd.REAL:
            continue
        if hit(bob["home"], g.get("home_name")) and hit(bob["away"], g.get("away_name")):
            st = datetime.strptime(g["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(sd.PT_)
            if abs((st.date() - d).days) <= 1:
                return g
    return None


def collect(folder, games):
    """Every free side pick, once, matched to our game -> [{gid, side, line, price, tier, seen, season, ...}], notes."""
    picks, notes = {}, {"pages": 0, "pages_with_picks": 0, "after_kick": 0, "unmatched": 0, "raw": 0}
    files = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".txt"))
    snaps = []
    for path in files:
        ts, lines = _snap(path)
        if ts:
            snaps.append((ts, lines, os.path.basename(path)))
    for ts, lines, name in sorted(snaps):
        notes["pages"] += 1
        page = parse(lines, ts.year)
        got = 0
        for b in page:
            g = _ours(games, b)
            if b["picks"] and not g:
                notes["unmatched"] += len(b["picks"])
                continue
            for p in b["picks"]:
                notes["raw"] += 1
                kick = datetime.strptime(g["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                late = kick <= ts                                 # the page was saved after the game (his pre-game text,
                notes["after_kick"] += late                       # but nothing proves it wasn't touched): never 'strict'
                key = (g["id"], p["side"])
                if key in picks:
                    continue
                got += 1
                season = int(g["start"][:4]) - (1 if g["start"][5:7] in ("01", "02") else 0)
                picks[key] = {"gid": g["id"], "side": p["side"], "line": p["line"], "price": p["price"], "tier": p["tier"], "late": late,
                              "stars": p["stars"], "seen": ts.strftime("%Y-%m-%dT%H:%MZ"), "page": name, "season": season,
                              "away": g.get("away_name"), "home": g.get("home_name"), "start": g["start"],
                              "bob_model": (b["model"][1] if b["model"][0] == p["side"] else -b["model"][1]) if b["model"] else None}
        notes["pages_with_picks"] += bool(got)
    return list(picks.values()), notes


def engine_reads(games):
    """{game id: the engine's BLIND home margin read} - params fit on the 3 seasons before, injuries zeroed."""
    out = {}
    fin = sm.finals(games, "nfl")
    for season in SEASONS:
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        p = sm.tune(learn, "nfl")
        if not p or "sw" not in p:
            continue
        _, played = sm.replay(fin, p["k"], p["hfa"], "nfl")
        for g, f, *_ in played:
            if lo <= g["start"] < hi:
                out[g["id"]] = sum(a * b for a, b in zip(p["sw"], sm._spread_x({**f, "inj": 0.0, "key": 0.0})))
    return out


def _week(start):
    """An NFL week runs Thursday to Monday: shift 2 days back so one week shares one ISO week."""
    d = datetime.strptime(start, "%Y-%m-%dT%H:%MZ") - timedelta(days=2)
    return d.isocalendar()[:2]


def grade_side(g, side, line):
    """ATS at `line` (this side's number, + = getting points) -> 'won' / 'lost' / 'push' / None."""
    try:
        mg = float(g["home_score"]) - float(g["away_score"])
    except (KeyError, ValueError, TypeError):
        return None
    d = (mg if side == "home" else -mg) + line
    return "won" if d > 0 else "lost" if d < 0 else "push"


def _dec(px):
    if px is None or not (-200 < px <= -100 or 100 <= px < 200):
        return JUICE
    return 1 + (px / 100 if px > 0 else 100 / -px)


def summary(rows, key="res_close", dec="dec_close"):
    """W-L-P, win %, ROI, units (1u each), SE of the win % and ROI, seasons up."""
    w = sum(1 for r in rows if r[key] == "won")
    l = sum(1 for r in rows if r[key] == "lost")
    p = sum(1 for r in rows if r[key] == "push")
    n = w + l
    units = sum((r[dec] - 1) if r[key] == "won" else -1 if r[key] == "lost" else 0 for r in rows)
    by = {}
    for r in rows:
        by.setdefault(r["season"], []).append(r)
    seasons = {}
    for s, rs in sorted(by.items()):
        sw, sl = sum(1 for r in rs if r[key] == "won"), sum(1 for r in rs if r[key] == "lost")
        su = sum((r[dec] - 1) if r[key] == "won" else -1 if r[key] == "lost" else 0 for r in rs)
        seasons[s] = f"{sw}-{sl} {su:+.1f}u"
    pct = w / n if n else None
    return {"record": f"{w}-{l}-{p}", "bets": n, "win_pct": round(100 * pct, 1) if n else None,
            "se_pct": round(100 * math.sqrt(0.25 / n), 1) if n else None,
            "units": round(units, 1), "roi_pct": round(100 * units / (n + p), 1) if n + p else None,
            "seasons_up": f"{sum(1 for v in seasons.values() if float(v.split()[1][:-1]) > 0)}/{len(seasons)}",
            "by_season": seasons}


def run(folder, strict=True):
    """strict: only picks from pages saved BEFORE kickoff. False: every parsed pick (pages saved the day after, too)."""
    games = sd.load_games("nfl")
    picks, notes = collect(folder, games)
    reads = engine_reads(games)
    rows = []
    for p in picks:
        g = games[p["gid"]]
        close = sm._num(g.get("spread_home"))
        ours = reads.get(p["gid"])
        if close is None or ours is None or g.get("status") != "final" or (strict and p["late"]):
            continue
        sg = 1 if p["side"] == "home" else -1
        cl = close * sg                                             # his side's closing number (+ = getting points)
        edge = sg * ours + cl                                        # the engine's read of his side vs the close
        rows.append({**p, "close": cl, "edge": round(edge, 2), "engine_same": edge > 0,
                     "res_close": grade_side(g, p["side"], cl), "dec_close": JUICE,
                     "res_bob": grade_side(g, p["side"], p["line"]), "dec_bob": _dec(p["price"]),
                     "week": _week(g["start"])})
    weeks = {(r["season"], r["week"]) for r in rows}
    base = []
    for gid, ours in reads.items():
        g = games[gid]
        close = sm._num(g.get("spread_home"))
        if close is None or g.get("status") != "final":
            continue
        season = int(g["start"][:4]) - (1 if g["start"][5:7] in ("01", "02") else 0)
        if (season, _week(g["start"])) not in weeks or ours + close == 0:
            continue
        side = "home" if ours + close > 0 else "away"
        sg = 1 if side == "home" else -1
        base.append({"season": season, "edge": abs(ours + close), "res_close": grade_side(g, side, close * sg),
                     "dec_close": JUICE, "bob": any(r["gid"] == gid for r in rows)})
    same = [r for r in rows if r["engine_same"]]
    opp = [r for r in rows if not r["engine_same"]]
    out = {"notes": notes, "strict": strict, "picks": len(rows), "per_season": {s: sum(1 for r in rows if r["season"] == s) for s in SEASONS},
           "tiers": {t: sum(1 for r in rows if r["tier"] == t) for t in ("lean", "strong", "best_bet", "headline")},
           "bob_alone": {"close": summary(rows), "his_number": summary(rows, "res_bob", "dec_bob")},
           "same_side": {"close": summary(same), "his_number": summary(same, "res_bob", "dec_bob")},
           "opposite": {"close": summary(opp), "his_number": summary(opp, "res_bob", "dec_bob")},
           "same_side_edge_2plus": summary([r for r in same if r["edge"] >= 2]),
           "same_side_edge_under_2": summary([r for r in same if r["edge"] < 2]),
           "opposite_edge_2plus": summary([r for r in opp if r["edge"] <= -2]),
           "bob_best_bets_and_strong": {"all": summary([r for r in rows if r["tier"] in ("best_bet", "strong")]),
                                        "same": summary([r for r in same if r["tier"] in ("best_bet", "strong")]),
                                        "opp": summary([r for r in opp if r["tier"] in ("best_bet", "strong")])},
           "bob_leans_only": {"all": summary([r for r in rows if r["tier"] == "lean"]),
                              "same": summary([r for r in same if r["tier"] == "lean"]),
                              "opp": summary([r for r in opp if r["tier"] == "lean"])},
           "engine_alone_same_weeks": {"all": summary(base), "edge_2plus": summary([b for b in base if b["edge"] >= 2]),
                                       "games_bob_skipped": summary([b for b in base if not b["bob"]])},
           "bob_model_vs_engine": _models(rows), "rows": rows}
    return out


def _models(rows):
    """Where he printed his model's number: does it agree with the engine's margin read on his side?"""
    both = [r for r in rows if r.get("bob_model") is not None]
    if not both:
        return None
    agree = [r for r in both if (r["bob_model"] + r["close"] > 0) == r["engine_same"]]
    return {"with_his_model_number": len(both), "models_agree_vs_close": len(agree),
            "agree": summary(agree), "disagree": summary([r for r in both if r not in agree])}


def _line(name, s):
    return (f"  {name:<44} {s['record']:>9}  {s['win_pct'] if s['win_pct'] is not None else '-':>5}% (SE {s['se_pct']})"
            f"  {s['units']:+.1f}u  ROI {s['roi_pct'] if s['roi_pct'] is not None else '-'}%  seasons up {s['seasons_up']}")


def report(out):
    n = out["notes"]
    print(f"\n=== {'STRICT: pages saved before kickoff' if out['strict'] else 'ALL parsed picks (pages saved after the game too)'} ===")
    print(f"Dr. Bob free NFL sides, archived pages: {n['pages']} snapshots, {n['pages_with_picks']} with picks; "
          f"{out['picks']} sides graded ({n['raw']} parsed, {n['after_kick']} from pages saved after kickoff; {n['unmatched']} unmatched)")
    print("  per season:", out["per_season"], " tiers:", out["tiers"])
    print("ATS at the CLOSE (-110):")
    for k, name in (("bob_alone", "Bob alone"), ("same_side", "engine SAME side as Bob"), ("opposite", "engine OPPOSITE Bob")):
        print(_line(name, out[k]["close"]))
        print(_line("   ... at his own number / price", out[k]["his_number"]))
    print(_line("same side, engine edge 2+ pts", out["same_side_edge_2plus"]))
    print(_line("same side, engine edge under 2", out["same_side_edge_under_2"]))
    print(_line("opposite, engine edge 2+ against him", out["opposite_edge_2plus"]))
    for k, name in (("bob_best_bets_and_strong", "his Best Bets + Strong Opinions"), ("bob_leans_only", "his Leans only")):
        print(_line(name, out[k]["all"]))
        print(_line("   ... engine same side", out[k]["same"]))
        print(_line("   ... engine opposite", out[k]["opp"]))
    e = out["engine_alone_same_weeks"]
    print(_line("ENGINE ALONE, every game those weeks", e["all"]))
    print(_line("   ... edge 2+ pts", e["edge_2plus"]))
    print(_line("   ... games Bob did not post", e["games_bob_skipped"]))
    m = out["bob_model_vs_engine"]
    if m:
        print(f"His model's number printed on {m['with_his_model_number']} picks; agrees with the engine vs the close on {m['models_agree_vs_close']}")
        print(_line("   both models on his side", m["agree"]))
        print(_line("   his model, not ours", m["disagree"]))


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    if not folder or not os.path.isdir(folder):
        sys.exit("give the folder with Dr. Bob's archived page texts (or set DRBOB_PAGES)")
    both = {"strict": run(folder, True), "all": run(folder, False)}
    for o in both.values():
        report(o)
    os.makedirs("results", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(both, f, indent=1, default=str)
    print("saved", OUT)
