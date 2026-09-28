"""🎾 Tennis closing odds history (tennis-data.co.uk): every ATP + WTA tour-level match since 2012 with its result and
the closing prices from Pinnacle (the sharpest book), Bet365, and the best / average price across books.

Saved compact to data/sports/tennis/hist_odds.csv.gz for the tennis edge study. Past years never change, so they're
only fetched once; the current year is refreshed every run."""
import csv
import gzip
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUT = os.path.join("data", "sports", "tennis", "hist_odds.csv.gz")
RAW = os.path.join("data", "sports", "tennis", "raw")   # season files uploaded by hand (2024.xlsx = ATP, 2024w.xlsx = WTA)
FIRST = 2012
COLS = ["tour", "season", "date", "tourney", "location", "series", "court", "surface", "round", "bo", "winner", "loser",
        "wrank", "lrank", "wpts", "lpts", "w1", "l1", "w2", "l2", "w3", "l3", "w4", "l4", "w5", "l5", "wsets", "lsets",
        "comment", "psw", "psl", "b365w", "b365l", "maxw", "maxl", "avgw", "avgl"]
SRC = {"tourney": "Tournament", "location": "Location", "court": "Court", "surface": "Surface", "round": "Round",
       "bo": "Best of", "winner": "Winner", "loser": "Loser", "wrank": "WRank", "lrank": "LRank", "wpts": "WPts",
       "lpts": "LPts", "wsets": "Wsets", "lsets": "Lsets", "comment": "Comment", "psw": "PSW", "psl": "PSL",
       "b365w": "B365W", "b365l": "B365L", "maxw": "MaxW", "maxl": "MaxL", "avgw": "AvgW", "avgl": "AvgL"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}


ERRS = []


def _get(url):
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return r.read()
        except Exception as e:                               # noqa: BLE001
            ERRS.append(f"{url}: {e}")
            if "404" in str(e) or "403" in str(e):
                return None
            time.sleep(3)
    return None


def _rows(blob, ext):
    """(header, rows) from an .xlsx or .xls file."""
    if ext == "xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
        it = wb.worksheets[0].iter_rows(values_only=True)
        head = [str(h or "").strip() for h in next(it)]
        return head, [list(r) for r in it]
    import xlrd
    sh = xlrd.open_workbook(file_contents=blob).sheet_by_index(0)
    head = [str(h).strip() for h in sh.row_values(0)]
    rows = []
    for i in range(1, sh.nrows):
        r = sh.row_values(i)
        dc = head.index("Date") if "Date" in head else -1
        if dc >= 0 and isinstance(r[dc], float):
            r[dc] = xlrd.xldate_as_datetime(r[dc], 0)
        rows.append(r)
    return head, rows


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else f"{v:g}"
    return str(v).strip()


def _parse(blob, ext, tour):
    head, rows = _rows(blob, ext)
    ix = {h: i for i, h in enumerate(head)}
    out = []
    for r in rows:
        get = lambda h: _cell(r[ix[h]]) if h in ix and ix[h] < len(r) else ""
        if not get("Winner"):
            continue
        d = {"tour": tour, "date": get("Date")[:10], "series": get("Series") or get("Tier")}   # season set by the caller
        for k, h in SRC.items():
            d[k] = get(h)
        for n in range(1, 6):
            d[f"w{n}"], d[f"l{n}"] = get(f"W{n}"), get(f"L{n}")
        out.append(d)
    return out


def raw_files():
    """{(tour, year): rows} from the hand-uploaded season files in data/sports/tennis/raw."""
    out = {}
    for fn in sorted(os.listdir(RAW)) if os.path.isdir(RAW) else []:
        base, _, ext = fn.rpartition(".")
        y, tour = base.rstrip("wW"), ("wta" if base.lower().endswith("w") else "atp")
        if ext.lower() in ("xls", "xlsx") and y.isdigit():
            with open(os.path.join(RAW, fn), "rb") as f:
                out[(tour, int(y))] = _parse(f.read(), ext.lower(), tour)
            print(f"{tour} {y}: {len(out[(tour, int(y))])} (uploaded file)", flush=True)
    return out


def _latest_capture(path):
    """The internet archive's newest good copy of a file: (timestamp, original url) or None."""
    q = urllib.parse.quote(path, safe="/.")
    blob = _get(f"https://web.archive.org/cdx/search/cdx?url={q}&filter=statuscode:200&output=json&fl=timestamp,original")
    try:
        rows = json.loads(blob or b"[]")[1:]
    except ValueError:
        return None
    return max(rows) if rows else None


def year(tour, y, direct=True):
    """(rows, source) for one season: the site itself, else the internet archive's newest copy (the site blocks servers)."""
    path = f"tennis-data.co.uk/{y}{'w' if tour == 'wta' else ''}/{y}"
    for ext in ("xlsx", "xls"):
        if direct:
            blob = _get(f"http://www.{path}.{ext}")
            if blob:
                return _parse(blob, ext, tour), "site"
        cap = _latest_capture(f"{path}.{ext}")
        if cap:
            blob = _get(f"https://web.archive.org/web/{cap[0]}id_/{cap[1]}")
            if blob:
                try:
                    return _parse(blob, ext, tour), f"archive {cap[0][:8]}"
                except Exception as e:                       # noqa: BLE001 - not a real season file
                    ERRS.append(f"{cap}: unreadable ({e})")
    return None, None


def _save(keep):
    keep.sort(key=lambda r: (r["date"], r["tour"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT + ".tmp", "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(keep)
    os.replace(OUT + ".tmp", OUT)


def _season(r):
    """The season file a match came from (a season's first events start in late December of the year before)."""
    if r.get("season"):
        return int(r["season"])
    y, m, d = (int(x) for x in r["date"][:10].split("-"))
    return y + 1 if (m == 12 and d >= 20) else y


def main(budget_s=20 * 60):
    t0 = time.time()
    have = []
    if os.path.exists(OUT):
        with gzip.open(OUT, "rt", newline="") as f:
            have = list(csv.DictReader(f))
    for r in have:
        r["season"] = str(_season(r))
    now = datetime.now(timezone.utc)
    count = {}
    for r in have:
        count[(r["tour"], int(r["season"]))] = count.get((r["tour"], int(r["season"])), 0) + 1
    # a season is in once we hold its file (1000+ matches); the current one is refreshed on Mondays
    done = {k for k, n in count.items() if n >= 1000 and (k[1] < now.year or now.weekday() != 0)}
    keep = list(have)

    def put(tour, y, rows):
        nonlocal keep
        for r in rows:
            r["season"] = str(y)
        keep = [r for r in keep if not (r["tour"] == tour and r["season"] == str(y))] + rows

    for (tour, y), rows in raw_files().items():
        put(tour, y, rows)
        done.add((tour, y))
    for y in range(FIRST, now.year + 1):
        for tour in ("atp", "wta"):
            if (tour, y) in done:
                continue
            if time.time() - t0 > budget_s:
                print("out of time - the next run picks up from here", flush=True)
                break
            rows, src = year(tour, y, direct=False)          # the site blocks (and stalls) servers: the archive only
            print(f"{datetime.now(timezone.utc):%H:%M:%S} {tour} {y}: {'missing' if rows is None else f'{len(rows)} ({src})'}", flush=True)
            if rows is None and ERRS:
                print("   ", ERRS[-1][:200], flush=True)
            if rows:
                put(tour, y, rows)
                _save(keep)                                  # saved as it goes - a slow run never loses what it got
    _save(keep)
    have_s = sorted({(r["tour"], r["season"]) for r in keep})
    print(f"saved {len(keep)} matches -> {OUT}; seasons: {', '.join(f'{a}{b[2:]}' for a, b in have_s)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
