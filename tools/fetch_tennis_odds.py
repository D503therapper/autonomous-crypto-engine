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
COLS = ["tour", "date", "tourney", "location", "series", "court", "surface", "round", "bo", "winner", "loser",
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
        d = {"tour": tour, "date": get("Date")[:10], "series": get("Series") or get("Tier")}
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


def main():
    have = []
    if os.path.exists(OUT):
        with gzip.open(OUT, "rt", newline="") as f:
            have = list(csv.DictReader(f))
    now = datetime.now(timezone.utc).year
    done = {(r["tour"], r["date"][:4]) for r in have if int(r["date"][:4] or 0) < now}
    keep = [r for r in have if int(r["date"][:4] or 0) < now]
    blocked = True                                           # the site blocks (and stalls) servers: the archive only
    for (tour, y), rows in raw_files().items():
        keep = [r for r in keep if not (r["tour"] == tour and r["date"][:4] == str(y))] + rows
        done.add((tour, str(y)))
    for tour in ("atp", "wta"):
        for y in range(FIRST, now + 1):
            if (tour, str(y)) in done:
                continue
            n0 = len(ERRS)
            rows, src = year(tour, y, direct=not blocked)
            print(f"{datetime.now(timezone.utc):%H:%M:%S} {tour} {y}: {'missing' if rows is None else f'{len(rows)} ({src})'}", flush=True)
            if rows is None and ERRS:
                print("   ", ERRS[-1][:200], flush=True)
            if not blocked and any("tennis-data.co.uk/" in e and "archive" not in e and "403" in e for e in ERRS[n0:]):
                print("   the site blocks servers - using the internet archive's copies from here", flush=True)
                blocked = True
            if rows:
                keep = [r for r in keep if not (r["tour"] == tour and r["date"][:4] == str(y))] + rows
                _save(keep)                                  # saved as it goes - a slow run never loses what it got
    _save(keep)
    print(f"saved {len(keep)} matches -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
