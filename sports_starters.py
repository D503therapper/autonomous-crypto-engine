"""🧱 THE STARTERS A BOX SCORE CAN'T SHOW (11/19 FABLE - the owner on the Colts +525 at the Texans, both starting tackles
out: "The starting fucking edges are key because then there's no pass protection ... This is not okay that we're not
looking at this.").

The engine's "who plays" was the box score: the QB, the top 2 ball carriers, top 4 catchers, top 11 tacklers
(sports_absences.regulars). An offensive lineman never shows up in a box score, a corner who covers well makes few
tackles, a pass rusher makes fewer - so the Colts missing both tackles, a starting corner and a defensive tackle counted
as LESS banged up than the Texans. This is the rest of the lineup.

THE SOURCE: nflverse's public snap counts (one season file from its public release - the same files the 11/11 book
study 8 and results/studies/oline_1119 ran on). A plain download under our own name (sports_http.UA), never a
disguise; when it answers empty or refuses it goes QUIET in source_status.json ("nflverse_snaps") and the engine falls
back to ESPN's depth chart's first string (sports_qb reads the chart already - "first"), then to the box score alone.

WHO STARTS (the rule the study was run on): a man who, in 2+ of his team's last 4 games, played
    70%+ of the OFFENSE's snaps    - tackles / guards / centers (and a tight end)
    70%+ of the DEFENSE's snaps    - corners / safeties / linebackers
    50%+ of the DEFENSE's snaps    - the men up front (defensive ends / tackles: they rotate)
(by the game, never an average: Bernhard Raimann went down 10% into his last game and Jalen Travis 41% into his - a
game a man leaves hurt must not unmake a starter)
Only the starters are kept (data/sports/nfl_snaps.json - written by the live run, a few KB). A file is used for a game
only when the team's last game in it is BEFORE the game and at most STALE_DAYS old - never a look-ahead in a replay,
never a September lineup in November. College: no snap counts exist; the depth chart's first string where ESPN keeps
one (almost never), else the box score's tacklers as before - an offensive line we cannot see is UNKNOWN, never
"healthy" and never a claim.

Never a request from a test (ON[0] / `get`)."""
import csv
import io
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import sports_data as sd
import sports_http as sh

PATH = os.path.join(sd.DATA, "nfl_snaps.json")
URL = "https://" + "github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{y}.csv"
ON = [True]
REFRESH_H = 12                   # the season file is re-read at most this often (it changes once a week)
STALE_DAYS = 16                  # a team's last game in the file older than this (a bye + a late file) = no file
LAST, NEED = 4, 2                # a team's last 4 games; a starter played a starter's share in 2+ of them
GROUP = {"T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL", "TE": "TE",
         "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
         "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB", "DB": "DB"}
OFFENSE = {"OL", "TE"}
MIN_SHARE = {"OL": 0.70, "TE": 0.70, "DB": 0.70, "LB": 0.70, "DL": 0.50}
ESPN_ID = {"ARI": "22", "ATL": "1", "BAL": "33", "BUF": "2", "CAR": "29", "CHI": "3", "CIN": "4", "CLE": "5", "DAL": "6",
           "DEN": "7", "DET": "8", "GB": "9", "HOU": "34", "IND": "11", "JAX": "30", "KC": "12", "LA": "14", "LAR": "14",
           "LAC": "24", "LV": "13", "OAK": "13", "MIA": "15", "MIN": "16", "NE": "17", "NO": "18", "NYG": "19", "NYJ": "20",
           "PHI": "21", "PIT": "23", "SEA": "26", "SF": "25", "TB": "27", "TEN": "10", "WAS": "28"}
# the depth chart's spots (ESPN's keys) -> the snap counts' position names
CHART_POS = {"lt": "T", "rt": "T", "lg": "G", "rg": "G", "c": "C", "te": "TE", "lcb": "CB", "rcb": "CB", "cb": "CB",
             "ss": "S", "fs": "S", "lde": "DE", "rde": "DE", "de": "DE", "ldt": "DT", "rdt": "DT", "dt": "DT", "nt": "NT",
             "wlb": "LB", "mlb": "LB", "slb": "LB", "lilb": "LB", "rilb": "LB", "lolb": "LB", "rolb": "LB", "lb": "LB"}
# plain words for the card (the owner: "goalie", not "G")
WORD = {"T": "tackle", "OT": "tackle", "G": "guard", "OG": "guard", "C": "center", "OL": "offensive lineman",
        "TE": "tight end", "CB": "corner", "S": "safety", "SS": "safety", "FS": "safety", "DB": "defensive back",
        "DE": "defensive end", "DT": "defensive tackle", "NT": "defensive tackle", "DL": "defensive lineman",
        "LB": "linebacker", "OLB": "linebacker", "ILB": "linebacker", "MLB": "linebacker"}
_CACHE = {}


def _nm(x):
    import sports_absences
    return sports_absences._nm(x)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def reduce(rows):
    """nflverse snap-count rows (dicts) -> {espn team id: {"last": the date of its last game in the file, "games": n,
    "men": {normalized name: [name, position, group, share, games played]}}} - the starters only (the rule on top)."""
    by = {}                                                  # team -> {(date, game): {name: (pos, grp, share)}}
    for r in rows:
        pos = str(r.get("position") or "").upper()
        tid = ESPN_ID.get(str(r.get("team") or "").upper())
        day = str(r.get("pfr_game_id") or "")[:8]
        if pos not in GROUP or not tid or len(day) != 8 or not day.isdigit():
            continue
        g = GROUP[pos]
        sh_ = _f(r.get("offense_pct") if g in OFFENSE else r.get("defense_pct"))
        by.setdefault(tid, {}).setdefault(f"{day[:4]}-{day[4:6]}-{day[6:]}", {})[str(r.get("player") or "")] = (pos, g, sh_)
    out = {}
    for tid, days in by.items():
        last = sorted(days)[-LAST:]
        if len(last) < NEED:
            continue
        seen = {}
        for d in last:
            for name, (pos, g, sh_) in days[d].items():
                if sh_ >= MIN_SHARE[g] and name:
                    seen.setdefault(name, []).append((pos, g, sh_))
        men = {}
        for name, xs in seen.items():
            if len(xs) < NEED:
                continue
            men[_nm(name)] = [name, xs[-1][0], xs[-1][1], round(sum(x[2] for x in xs) / len(xs), 3), len(xs)]
        out[tid] = {"last": last[-1], "games": len(last), "men": men}
    return out


def load():
    if "d" not in _CACHE:
        try:
            with open(PATH) as f:
                _CACHE["d"] = json.load(f)
        except (OSError, ValueError):
            _CACHE["d"] = {}
    return _CACHE["d"]


def sync(now=None, get=None):
    """Read this season's snap counts (at most every REFRESH_H hours) and save the starters. Fails soft: a failed or
    empty read keeps the last file (it goes stale on its own - STALE_DAYS) and says so in source_status.json.
    `get` = a function(url) -> the CSV text (the tests). -> teams read this run (0 = nothing new)."""
    now = now or datetime.now(timezone.utc)
    if not ON[0] and get is None:
        return 0
    d = load()
    try:
        if get is None and d.get("at") and (now - datetime.strptime(d["at"][:16], "%Y-%m-%dT%H:%M").replace(
                tzinfo=timezone.utc)).total_seconds() < REFRESH_H * 3600:
            return 0
    except ValueError:
        pass
    season = now.year if now.month >= 8 else now.year - 1
    url = URL.format(y=season)
    try:
        if get is not None:
            text = get(url)
        else:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": sh.UA}), timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
        teams = reduce(csv.DictReader(io.StringIO(text or "")))
    except Exception as e:                                   # noqa: BLE001 - a failed read is unknown, never a guess
        sh.note("nflverse_snaps", False, err=sh.err_text(e),
                how="plain download - the season's snap counts (who starts on the lines / in the secondary); quiet = "
                    "the depth chart's first string, else the box score alone")
        return 0
    sh.note("nflverse_snaps", bool(teams), n=len(teams),
            how="plain download - the season's snap counts (who starts on the lines / in the secondary)"
            + ("" if teams else "; it came back with no teams - the depth chart's first string, else the box score alone"))
    if not teams:
        return 0
    d = {"at": now.strftime("%Y-%m-%dT%H:%MZ"), "season": season, "teams": teams}
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH + ".tmp", "w") as f:
            json.dump(d, f, sort_keys=True, separators=(",", ":"))
        os.replace(PATH + ".tmp", PATH)
    except OSError:
        pass
    _CACHE["d"] = d
    return len(teams)


def _chart(league, team, before):
    """The depth chart's first string (sports_qb's "first": {spot: name}) when the chart was read inside the 8 days
    before the game - {normalized name: (name, position, group)} or None."""
    try:
        import sports_qb
        v = (sports_qb.load().get(league) or {}).get(str(team)) or {}
        first, at = v.get("first") or {}, str(v.get("at") or "")
        if not first or not at:
            return None
        t0 = datetime.strptime(at[:16], "%Y-%m-%dT%H:%M")
        t1 = datetime.strptime(str(before)[:16], "%Y-%m-%dT%H:%M")
        if not timedelta(0) <= t1 - t0 <= timedelta(days=8):
            return None
    except Exception:                                        # noqa: BLE001
        return None
    out = {}
    for spot, name in first.items():
        pos = CHART_POS.get(str(spot).lower())
        if pos and name:
            out[_nm(name)] = (name, pos, GROUP[pos])
    return out or None


def starters(league, team, before):
    """{normalized name: (name, position, group)} - the team's starters a box score can't show, going into a game that
    starts `before` (ISO). None = we can't see them (no fresh snap counts, no depth chart): nothing is claimed."""
    before = str(before or "")
    if league not in ("nfl", "ncaaf") or len(before) < 10:
        return None
    if league == "nfl":
        t = (load().get("teams") or {}).get(str(team))
        if t and t.get("men"):
            try:
                age = (datetime.strptime(before[:10], "%Y-%m-%d") - datetime.strptime(t["last"], "%Y-%m-%d")).days
            except (KeyError, ValueError):
                age = None
            if age is not None and 0 < age <= STALE_DAYS:
                return {k: (v[0], v[1], v[2]) for k, v in t["men"].items()}
    return _chart(league, team, before)


def find(st, name):
    """The starter this report name is, (name, position, group), or None."""
    if not st:
        return None
    import sports_absences
    n = sports_absences._nm(name)
    if n in st:
        return st[n]
    hit = [k for k in st if sports_absences.match(name, {k})]
    return st[hit[0]] if len(hit) == 1 else None


def word(pos):
    """'starting tackle' / 'starting corner' ... for a snap-count position ('' when we have no plain word)."""
    w = WORD.get(str(pos or "").upper())
    return f"starting {w}" if w else ""


def holes(men):
    """The plain-words line for a list of starters who are OUT ([(name, position, group)]) - said only when the hole is
    more than one man deep (one missing lineman is in the price - results/studies/oline_1119): '' otherwise."""
    pos = [str(m[1]).upper() for m in men]
    grp = [m[2] for m in men]
    t, ol = sum(1 for p in pos if p in ("T", "OT")), grp.count("OL")
    cb, db = pos.count("CB"), grp.count("DB")
    said = []
    if t >= 2:
        said.append("both starting tackles out - backups protecting the QB")
    elif ol >= 2:
        said.append(f"{ol} starting offensive linemen out - backups protecting the QB")
    if cb >= 2:
        said.append("both starting corners out")
    elif db >= 2:
        said.append(f"{db} starters out of the secondary")
    if grp.count("DL") >= 2:
        said.append(f"{grp.count('DL')} starters out up front on defense")
    return "; ".join(said)
