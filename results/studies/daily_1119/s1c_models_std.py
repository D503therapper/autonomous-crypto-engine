"""S1c - the same raw-clock read inside two FITTED models (the 11/19 sweep's open item): sports_nba_open's tz_cross
(the 🏀 NBA opening-line play) and sports_totals' travel (the totals reads). Each model is fit and graded twice -
the raw wall-clock read (TZ_STD False) and standard time (TZ_STD True) - nothing else changed.
NBA open: walk-forward, the model for season S fit on the seasons before S only; graded on S at the CLOSE (log loss, every
side) and at ESPN's OPEN where it is on file (the play: score 4+ points over the open's no-vig number, -150..+300).
Totals: sports_totals.study_league per league (learn / validate / test in time order)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: F401  (chdir to the repo root + sys.path)
import sports_data as sd
import sports_model as sm
import sports_nba_open as no
import sports_totals as st

lines = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


say(__doc__)
games = sd.load_games("nba")
res = {}
for flag in (False, True):
    no.TZ_STD = flag
    tab = no.table(games)
    n_rows = sum(1 for r in tab.values() if r["reg"])
    off = sum(1 for r in tab.values() if r["reg"] and r["a"]["tz_cross"] > 0)
    say(f"\nNBA OPEN, TZ_STD={flag}: {n_rows} regular-season rows, road sides reading 1+ zones crossed: {off}")
    tot_ll, tot_n, plays = 0.0, 0, []
    for S in range(2019, 2027):
        m = no.fit(games, S, path=False, tab=tab)
        if not m:
            continue
        ll, n, pl = 0.0, 0, []
        for gid, row in tab.items():
            if row["season"] != S or not row["reg"] or row["home_win"] is None:
                continue
            mp = no._mp(row["ml_home"], row["ml_away"])
            if mp is not None:
                for side, p_, won in (("home", mp, row["home_win"]), ("away", 1 - mp, 1 - row["home_win"])):
                    q = min(0.999, max(0.001, no.predict(m, no.features(row, side, p_))))
                    ll -= math.log(q if won else 1 - q)
                    n += 1
            g = games[gid]
            oh, oa = sm._num(g.get("ml_home_open")), sm._num(g.get("ml_away_open"))
            mo = no._mp(oh, oa) if oh and oa else None
            if mo is not None:
                for side, p_, won, o in (("home", mo, row["home_win"], oh), ("away", 1 - mo, 1 - row["home_win"], oa)):
                    if no.PRICE_BAND[0] <= o <= no.PRICE_BAND[1] and not -100 < o < 100 and no.score(m, row, side, p_) >= no.SCORE_MIN:
                        pl.append((gid, side, (lib.dec(o) - 1) if won else -1.0))
        tot_ll += ll
        tot_n += n
        plays += pl
        w = dict(zip(no.FEATURES, m["w"][1:]))
        say(f"  season {S}: log loss {ll / max(n, 1):.5f} on {n} sides; plays at the open {len(pl)} "
            f"{sum(p for *_, p in pl):+.1f}u ({(sum(p for *_, p in pl) / len(pl) * 100 if pl else 0):+.1f}%); "
            f"weights t_tz {w['t_tz']:+.4f} o_tz {w['o_tz']:+.4f}")
    res[flag] = (tot_ll / tot_n, plays)
    say(f"  ALL: log loss {tot_ll / tot_n:.5f}; plays {len(plays)} {sum(p for *_, p in plays):+.1f}u "
        f"({sum(p for *_, p in plays) / max(len(plays), 1) * 100:+.1f}%)")
a, b = {(g, s) for g, s, _ in res[False][1]}, {(g, s) for g, s, _ in res[True][1]}
say(f"\nNBA OPEN plays: raw {len(a)}, standard {len(b)}, the same {len(a & b)}; only raw {len(a - b)} "
    f"({sum(p for g, s, p in res[False][1] if (g, s) not in b):+.1f}u), only standard {len(b - a)} "
    f"({sum(p for g, s, p in res[True][1] if (g, s) not in a):+.1f}u); log loss raw {res[False][0]:.5f} vs standard {res[True][0]:.5f}")

for lg in ("nfl", "nba", "nhl", "ncaaf", "ncaab"):
    gm = sd.load_games(lg)
    out = {}
    for flag in (False, True):
        st.TZ_STD = flag
        try:
            rs = st.rows(gm, lg, {}, {})
        except Exception as e:                      # noqa: BLE001
            say(f"\nTOTALS {lg}: {e}")
            break
        j = st.FEATURES.index("travel")
        nonzero = sum(1 for r in rs if r[0][j])
        r = st.study_league(rs) if len(rs) >= st.MIN_ROWS else None
        out[flag] = (len(rs), nonzero, r)
    if len(out) == 2:
        say(f"\nTOTALS {lg}:")
        for flag in (False, True):
            n, nz, r = out[flag]
            if not r:
                say(f"  TZ_STD={flag}: {n} rows - too few")
                continue
            say(f"  TZ_STD={flag}: {n} rows, travel > 0 on {nz}; kept {r['kept']}; test log loss base {r['ll_test_base']} "
                f"kept {r['ll_test_kept']}; travel alone on the validation slice: {r['screen'].get('travel')}; "
                f"top 30% hit {r['hit_top']} roi {r['roi_top']} on {r['n_top']}; proven {r['proven']}")
open(os.path.join(lib.OUT, "s1c_models_std_out.txt"), "w").write("\n".join(lines) + "\n")
