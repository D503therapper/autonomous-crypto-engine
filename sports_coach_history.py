"""COACH HISTORY (the owner, 10/1: "complete the studies on the coaches and the managers - there's a lot to that").
ESPN's per-season coach list is bad history (today's coach copied back through every season). This reads the REAL
head coach / manager of every NFL, NBA, NHL and MLB team, season by season since 2000, from each team-season page's
infobox on Wikipedia ("2019 Kansas City Chiefs season" -> head_coach), through Wikipedia's public API with a plain
User-Agent that says who we are (Wikipedia's rule). A mid-season change lists every coach that season, in order.
Runs in GitHub Actions (coach_history.yml - this sandbox can't reach Wikipedia). Saves data/sports/coach_history.json:
{league: {team: {season: [coach, ...]}}}; experience() counts each coach's head-coaching seasons before a season."""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import sports_data as sd

PATH = os.path.join(sd.DATA, "coach_history.json")
API = ("https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=wikitext&section=0&redirects=1"
       "&page={page}")
UA = "D503-sports-engine/1.0 (https://github.com/D503therapper/autonomous-crypto-engine; coaching study)"
FIRST = 2000
FIELD = {"nfl": ("head_coach", "coach"), "nba": ("head_coach", "coach"), "nhl": ("head_coach", "coach"),
         "mlb": ("manager",)}

# Every team, with the names it played under (newest first) - a season page uses the name of that season.
TEAMS = {
    "nfl": ["Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills", "Carolina Panthers",
            "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys", "Denver Broncos",
            "Detroit Lions", "Green Bay Packers", "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars",
            "Kansas City Chiefs", "Las Vegas Raiders|Oakland Raiders", "Los Angeles Chargers|San Diego Chargers",
            "Los Angeles Rams|St. Louis Rams", "Miami Dolphins", "Minnesota Vikings", "New England Patriots",
            "New Orleans Saints", "New York Giants", "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers",
            "San Francisco 49ers", "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans",
            "Washington Commanders|Washington Football Team|Washington Redskins"],
    "nba": ["Atlanta Hawks", "Boston Celtics", "Brooklyn Nets|New Jersey Nets", "Charlotte Hornets|Charlotte Bobcats",
            "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons",
            "Golden State Warriors", "Houston Rockets", "Indiana Pacers", "Los Angeles Clippers", "Los Angeles Lakers",
            "Memphis Grizzlies|Vancouver Grizzlies", "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves",
            "New Orleans Pelicans|New Orleans Hornets|New Orleans/Oklahoma City Hornets", "New York Knicks",
            "Oklahoma City Thunder|Seattle SuperSonics", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
            "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz",
            "Washington Wizards"],
    "nhl": ["Anaheim Ducks|Mighty Ducks of Anaheim", "Boston Bruins", "Buffalo Sabres", "Calgary Flames",
            "Carolina Hurricanes", "Chicago Blackhawks", "Colorado Avalanche", "Columbus Blue Jackets", "Dallas Stars",
            "Detroit Red Wings", "Edmonton Oilers", "Florida Panthers", "Los Angeles Kings", "Minnesota Wild",
            "Montreal Canadiens", "Nashville Predators", "New Jersey Devils", "New York Islanders", "New York Rangers",
            "Ottawa Senators", "Philadelphia Flyers", "Pittsburgh Penguins", "San Jose Sharks", "Seattle Kraken",
            "St. Louis Blues", "Tampa Bay Lightning", "Toronto Maple Leafs",
            "Utah Mammoth|Utah Hockey Club|Arizona Coyotes|Phoenix Coyotes", "Vancouver Canucks",
            "Vegas Golden Knights", "Washington Capitals", "Winnipeg Jets|Atlanta Thrashers"],
    "mlb": ["Arizona Diamondbacks", "Atlanta Braves", "Baltimore Orioles", "Boston Red Sox", "Chicago Cubs",
            "Chicago White Sox", "Cincinnati Reds", "Cleveland Guardians|Cleveland Indians", "Colorado Rockies",
            "Detroit Tigers", "Houston Astros", "Kansas City Royals",
            "Los Angeles Angels|Los Angeles Angels of Anaheim|Anaheim Angels", "Los Angeles Dodgers", "Miami Marlins|Florida Marlins",
            "Milwaukee Brewers", "Minnesota Twins", "New York Mets", "New York Yankees", "Athletics|Oakland Athletics",
            "Philadelphia Phillies", "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants",
            "Seattle Mariners", "St. Louis Cardinals", "Tampa Bay Rays|Tampa Bay Devil Rays", "Texas Rangers",
            "Toronto Blue Jays", "Washington Nationals|Montreal Expos"],
}


def page(league, name, season):
    if league in ("nba", "nhl"):
        nxt = str(season + 1)[2:] if season + 1 != 2000 else "2000"
        return f"{season}–{nxt} {name} season"
    return f"{season} {name} season"


def fetch(title):
    req = urllib.request.Request(API.format(page=urllib.parse.quote(title)), headers={"User-Agent": UA})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
            if d.get("error"):
                return None                                  # no such page
            return ((d.get("parse") or {}).get("wikitext") or {}).get("*") or ""
        except Exception as e:                               # noqa: BLE001
            if i == 2:
                print(f"   {title}: {str(e)[:80]}")
                return ""
            time.sleep(2)


def _clean(t):
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->", "", t, flags=re.S)
    return t


def coaches(wikitext, league):
    """The infobox's head coach / manager field -> [names in order] (a mid-season change lists them all)."""
    t = _clean(wikitext or "")
    for f in FIELD[league]:
        m = re.search(r"^\s*\|\s*" + f + r"\s*=(.*?)(?=^\s*\||^\}\})", t, re.M | re.S)
        if not m:
            continue
        v = m.group(1)
        names = re.findall(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", v)
        if not names:
            names = [x.strip() for x in re.split(r"<br\s*/?>|,|\n", re.sub(r"\{\{[^}]*\}\}", "", v)) if x.strip()]
        out = []
        for n in names:
            n = re.sub(r"\s*\(.*?\)", "", n).strip()
            if n and not re.search(r"\d|season|interim|fired|resign", n, re.I) and n not in out:
                out.append(n)
        if out:
            return out
    return []


def run(leagues=("nfl", "nba", "nhl", "mlb"), last=None, minutes=40, path=PATH):
    from datetime import datetime, timezone
    last = last or datetime.now(timezone.utc).year
    try:
        with open(path) as f:
            out = json.load(f)
    except (OSError, ValueError):
        out = {}
    stop = time.time() + minutes * 60
    for lg in leagues:
        for names in TEAMS[lg]:
            alias = names.split("|")
            team = alias[0]
            have = out.setdefault(lg, {}).setdefault(team, {})
            for season in range(FIRST, last + 1):
                if str(season) in have and season < last - 1:
                    continue                                 # (past seasons don't change - the last two get re-read)
                if time.time() > stop:
                    print("   out of time - the next run picks up here")
                    _save(out, path)
                    return out
                got = None
                for nm in alias:
                    w = fetch(page(lg, nm, season))
                    if w:
                        got = coaches(w, lg)
                        if got:
                            break
                    time.sleep(0.25)                         # (gentle on Wikipedia)
                if got:
                    have[str(season)] = got
            print(f"   {lg} {team}: {len(have)} seasons", flush=True)
            _save(out, path)
    return out


def _save(out, path):
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, indent=0, sort_keys=True)
    os.replace(path + ".tmp", path)


def load(path=PATH):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def experience(hist, league):
    """{(team, season): (coach, head-coaching seasons he had in this league BEFORE this one, first year with this team,
    changed mid-season)} - for the season's opening coach."""
    seasons = {}                                             # coach -> sorted seasons he coached anybody
    for team, by in hist.get(league, {}).items():
        for s, names in by.items():
            for n in names:
                seasons.setdefault(n, set()).add(int(s))
    out = {}
    for team, by in hist.get(league, {}).items():
        for s, names in by.items():
            if not names:
                continue
            c, s_ = names[0], int(s)
            prior = sum(1 for x in seasons.get(c, ()) if x < s_)
            first = (by.get(str(s_ - 1)) or [None])[-1] != c
            out[(team, s_)] = (c, prior, first, len(names) > 1)
    return out


if __name__ == "__main__":
    run(minutes=int(sys.argv[1]) if len(sys.argv) > 1 else 40)
