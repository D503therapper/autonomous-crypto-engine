"""Shared helpers for the 11/11 SPREADS LIKE THE PROS (part 2) studies (results/studies/spreads2_1111).
Read-only on the repo; caches in ~/.cache (never the repo). Builds on daily_1110/lib.py (`B`: finals at the close, the
paid football odds history's FAIR looks - tools/early_football_study.ready_at / fair, no look-ahead)."""
import importlib.util, math, os, statistics, sys

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
os.environ.setdefault("STUDY_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "d503_1111"))
_spec = importlib.util.spec_from_file_location("dlib1110", os.path.join(ROOT, "results", "studies", "daily_1110", "lib.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)                      # (chdirs to ROOT, puts ROOT on sys.path)
sys.path.insert(0, OUT)
import nfl as N                                   # noqa: E402

dec, num = B.dec, B.num
st, roi, by_season, Out = N.st, N.roi, N.by_season, N.Out
TRAIN_F = (2020, 2022)                            # football paid history: train 2020-22, held out 2023-26
SHARP = ("lowvig", "betonlineag", "pinnacle", "circasports", "bookmaker")


def cover(margin_home, line_home, side, price=-110):
    """Profit on 1 for `side` at the HOME team's line `line_home` (the away side holds -line_home); push 0."""
    r = margin_home + line_home
    if side == "away":
        r = -r
    return 0.0 if r == 0 else ((dec(price) - 1) if r > 0 else -1.0)


def football(lg):
    """Games with a FAIR early spread look across 3+ books: B.load_football rows + 'first' (days out, {book: (home
    pts, home price, away pts, away price)}) = the first fair look 1.5-7.5 days out, 'med' its median home line."""
    out = []
    for g in B.load_football(lg):
        f = B.first_fair(g["sp"])
        if not f:
            continue
        g = dict(g)
        g["first"] = f
        g["med"] = statistics.median(v[0] for v in f[1].values())
        out.append(g)
    return out


def held(season):
    return season > TRAIN_F[1]


def line(name, rows, key_s=0, key_p=1):
    """'name  all | train | held (seasons up)' for rows = [(season, profit)]."""
    tr = [p for s, p in rows if not held(s)]
    he = [p for s, p in rows if held(s)]
    up = by_season([(s, p) for s, p in rows if held(s)])
    return (f"{name[:54]:54s} all {st([p for _, p in rows])} | train {st(tr)[:5].strip():>5s} {roi(tr):+6.1f}% | "
            f"HELD {st(he)} ({up[0]}/{up[1]} up: {up[2]})")


def zprop(w, n, p0):
    return (w / n - p0) / math.sqrt(p0 * (1 - p0) / n) if n else 0.0
