"""Run the tennis engine's readers against the live feeds from the runner (ESPN ATP results, Bovada prices)."""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")
import sports_tennis as st  # noqa: E402

now = datetime.now(timezone.utc)
try:
    raw = json.load(urllib.request.urlopen(st.BOVADA, timeout=25))
    paths = sorted({" > ".join(p.get("description", "") for p in g.get("path") or []) for g in raw})
    print("bovada groups:", len(raw))
    for p in paths[:25]:
        print("   ", p)
    ev = next((e for g in raw for e in g.get("events") or []), {})
    print("bovada event sample:", json.dumps({k: ev.get(k) for k in ("description", "startTime", "competitors")})[:400])
    dg = (ev.get("displayGroups") or [{}])[0]
    print("bovada markets:", [(m.get("description"), m.get("period")) for m in dg.get("markets") or []][:4])
    lines = st.bovada()
    print("parsed men's lines:", len(lines))
    for ln in lines[:8]:
        print("   ", ln)
except Exception as e:                                       # noqa: BLE001
    print("BOVADA ERR", e)
rows = []
for d in range(-1, 2):
    rows += st._espn((now + timedelta(days=d)).date()) or []
by = {r["id"]: r for r in rows}
print("espn singles matches:", len(by), "statuses:", sorted({r["status"] for r in by.values()}))
pre = [r for r in by.values() if st._state(r) == "pre"]
print("upcoming:", len(pre))
for r in sorted(pre, key=lambda r: r["start"])[:6]:
    print("   ", r["start"], r["tourney"], r["round"], r["surface"], r["p1_name"], "vs", r["p2_name"])
try:
    matched = [(r["p1_name"], r["p2_name"], st.price(r, lines)) for r in pre if st.price(r, lines)]
    print("priced upcoming:", len(matched), matched[:5])
except NameError:
    pass
