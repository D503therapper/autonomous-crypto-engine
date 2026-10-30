"""🚑 WHO PLAYS WHEN HE'S QUESTIONABLE (the owner, 10/30 - his brother Ricky: "Rui gonna play, he was never not gonna
play ... some guys are always questionable ... there's data on that"). The 10/30 study (SPORTS_FINDINGS "10/30 -
QUESTIONABLE PLAYERS (Ricky's ask)", results/studies/questionable_1030/): every NBA official injury report version
2018-19..2025-26 (87,427 listings) joined to our ESPN box scores - who actually played.

  NBA, questionable on the 1:30 PM ET report (what the engine sees at 8 AM PT): 48.8% played of 12,019; a KEY man
  (the engine's top-3 scorer / starter) 54.5% of 6,380; the top scorer 58.0%. Every season 47-52%. It's a coin flip,
  not "almost always". Probable 89% (key men 95%), doubtful 3.9%, out 0.8%.
  The market: a team bet at the OPEN with a key man who then turned up questionable gave up 5.0% vs the close (a normal
  bet 2.3%); when he sat, 8.4%. Waiting for the news SAVES money on the coin flips - the hold stays.
  But some men really do play through it. A key man with 10+ questionable listings before and 85%+ of them played
  (strictly prior history) played 72.6% of 73 (2018-19..2022-23) and 85.1% of 87 (2023-24..2025-26 held out) - about 4
  in 5, never the 95% Ricky hears. For HIM the hold costs more than it saves (a 4-in-5 play chance: betting through with
  the absence penalty weighted by his 1-in-5 chance to sit beats waiting whenever the read has an edge) - so he's
  treated as PLAYING: no hold, and USUALLY_PLAYS is his chance in the read (sports_absences.penalty weighs the 20%).

The table (data/sports/nba_questionable.json) is built by results/studies/questionable_1030/nba_rates.py from the
official reports: {normalized name: [times questionable at 1:30 PM, times he played]} over the regular seasons.
This season's listings aren't in it (the public archive ends with 2025-26) - a man new to the list is not "usually
plays" and keeps the hold."""
import json
import os

import sports_data as sd

PATH = os.path.join(sd.DATA, "nba_questionable.json")
USUALLY_N = 10            # 10+ questionable listings in his history...
USUALLY_RATE = 0.85       # ...85%+ of them he played
USUALLY_PLAYS = 0.80      # what that history means going forward (72.6% train / 85.1% held out - 4 in 5)
_T = {}


def table():
    """{normalized name: [listed, played]} - {} when the file is missing (nobody 'usually plays': the hold stays)."""
    if "t" not in _T:
        try:
            with open(PATH) as f:
                _T["t"] = (json.load(f) or {}).get("players") or {}
        except (OSError, ValueError):
            _T["t"] = {}
    return _T["t"]


def history(name, tbl=None):
    """(times questionable, times played) for this man - exact name, else the one close match (sports_absences.match)."""
    import sports_absences as sa
    t = table() if tbl is None else tbl
    n = sa._nm(name)
    if n in t:
        return tuple(t[n][:2])
    w = n.split()
    if len(w) >= 2:
        pool = {k for k in t if k.split()[-1:] == w[-1:]}
        if pool and sa.match(name, pool):
            k = next(k for k in pool if sa.match(name, {k}))
            return tuple(t[k][:2])
    return (0, 0)


def usually_plays(name, tbl=None):
    """Is this man one who plays through a questionable tag (USUALLY_N+ listings, USUALLY_RATE+ played)?"""
    n, p = history(name, tbl)
    return n >= USUALLY_N and p / n >= USUALLY_RATE


def probable_note(name):
    """ESPN often files a probable man as 'day-to-day' with the word in the note ('probable', 'expected to play'):
    the official reports say a probable key man plays 94.7% (2,625) - never a reason to hold the board."""
    try:
        import sports_nba_roster as nr
        d = ((getattr(sd, "INJ_NOTES", {}) or {}).get("nba") or {}).get(sd._plain(name)) or {}
        return bool(d) and nr.play_chance(d.get("status"), d.get("note")) >= nr.PLAY["probable"]
    except Exception:                                    # noqa: BLE001 - no note = no claim
        return False


def plays_through(name, tbl=None):
    """🏀 a questionable / day-to-day NBA man the board treats as PLAYING (no hold): a probable note, or the history."""
    return probable_note(name) or usually_plays(name, tbl)
