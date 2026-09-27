"""Weather + elevation for every game, from Open-Meteo (free, no key).

- Each stadium's city is geocoded once (cached in data/sports/venues.json): latitude, longitude, elevation.
- Outdoor games get game-day weather: mean temperature (F), max wind (mph), rain/snow (mm) - history from
  the archive, upcoming games from the forecast. Indoor arenas and domes only get elevation.
Stored on each game (elev, wx_temp, wx_wind, wx_rain) so the model can learn what they're worth."""
import json
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import sports_data as sd

GEO = "https://geocoding-api.open-meteo.com/v1/search?name={q}&count=10&language=en&format=json"
ARCHIVE = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={a}&end_date={b}"
           "&daily=temperature_2m_mean,wind_speed_10m_max,precipitation_sum&temperature_unit=fahrenheit"
           "&wind_speed_unit=mph&timezone=UTC")
FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&forecast_days=16"
            "&daily=temperature_2m_mean,wind_speed_10m_max,precipitation_sum&temperature_unit=fahrenheit"
            "&wind_speed_unit=mph&timezone=UTC")
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
          "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
          "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
          "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
          "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
          "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
          "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
          "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
          "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
          "WI": "Wisconsin", "WY": "Wyoming", "ON": "Ontario", "QC": "Quebec", "BC": "British Columbia", "AB": "Alberta",
          "MB": "Manitoba"}
PATH = os.path.join(sd.DATA, "venues.json")


def _get(url):
    for i in range(2):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                return json.load(r)
        except Exception as e:                            # noqa: BLE001
            if i == 1:
                sd.ERRORS.append(f"weather: {str(e)[:100]}")
                return None
            time.sleep(2)


def geocode(city, state, country):
    """(lat, lon, elevation_m, timezone) for a stadium's city, or None."""
    if not city:
        return None
    d = _get(GEO.format(q=urllib.parse.quote(city)))
    res = (d or {}).get("results") or []
    if not res:
        return None
    want = STATES.get(state, state)

    def score(r):
        return ((r.get("admin1") or "").lower() == (want or "").lower(),
                (country in ("", "USA", "United States")) == (r.get("country_code") == "US"),
                r.get("population") or 0)
    r = max(res, key=score)
    return r["latitude"], r["longitude"], r.get("elevation") or 0.0, r.get("timezone") or ""


def _key(g):
    return f'{g.get("city", "")}|{g.get("state", "")}|{g.get("country", "")}'


def sync(games, budget_s=240):
    """Fill elevation for every game and weather for outdoor games (a batch of venues per run)."""
    venues = {}
    if os.path.exists(PATH):
        with open(PATH) as f:
            venues = json.load(f)
    deadline = time.time() + budget_s
    need = sorted(k for k in {_key(g) for g in games.values() if g.get("city")}
                  if k not in venues or (venues[k] and len(venues[k]) < 4))          # new, or cached before time zones
    for k in need:
        if time.time() > deadline:
            break
        city, state, country = k.split("|")
        venues[k] = geocode(city, state, country)
    # elevation + the stadium's UTC offset (for body-clock travel) on every game
    from zoneinfo import ZoneInfo
    for g in games.values():
        v = venues.get(_key(g))
        if v and g.get("elev", "") == "":
            g["elev"] = round(v[2])
        if v and len(v) > 3 and v[3] and g.get("tzo", "") == "":
            try:
                at = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                g["tzo"] = round(at.astimezone(ZoneInfo(v[3])).utcoffset().total_seconds() / 3600, 1)
            except Exception:                                  # noqa: BLE001
                pass
    # weather: outdoor games missing it, grouped by venue (one request per venue per date span)
    todo = defaultdict(list)
    today = datetime.now(timezone.utc).date()
    for g in games.values():
        if str(g.get("indoor")) == "1" or not venues.get(_key(g)) or (g.get("wx_temp", "") != "" and g["status"] != "pre"):
            continue
        d = datetime.strptime(g["start"][:10], "%Y-%m-%d").date()
        if d > today + timedelta(days=14):
            continue
        todo[_key(g)].append((d, g))
    filled = 0
    for k, items in todo.items():
        if time.time() > deadline:
            break
        lat, lon = venues[k][0], venues[k][1]
        days = {}
        past = [d for d, _ in items if d < today - timedelta(days=5)]
        if past:
            data = _get(ARCHIVE.format(lat=lat, lon=lon, a=min(past), b=max(past)))
            days.update(_daily(data))
        if any(d >= today - timedelta(days=5) for d, _ in items):
            days.update(_daily(_get(FORECAST.format(lat=lat, lon=lon))))
        for d, g in items:
            w = days.get(d.isoformat())
            if w and None not in w:
                g["wx_temp"], g["wx_wind"], g["wx_rain"] = round(w[0]), round(w[1]), round(w[2], 1)
                filled += 1
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(venues, f, indent=0, sort_keys=True)
    return filled, len(need)


def _daily(data):
    dl = (data or {}).get("daily") or {}
    return {t: (a, b, c) for t, a, b, c in zip(dl.get("time", []), dl.get("temperature_2m_mean", []),
                                              dl.get("wind_speed_10m_max", []), dl.get("precipitation_sum", []))}
