"""Probe: what ESPN's tennis feed says right now about our ungraded matches, day by day (is it stale?)."""
import json
import urllib.request

import sys
sys.path.insert(0, ".")
import sports_tennis as st  # noqa: E402

WANT = {"186251", "186256", "186227", "186229", "186230", "183420", "183374", "183421", "183375"}
for tour in ("atp", "wta"):
    for day in ("20260926", "20260927", "20260928", "20260929"):
        url = f"{st.ESPN.format(tour=tour)}?dates={day}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache"}), timeout=20) as r:
                age = r.headers.get("Age"), r.headers.get("Cache-Control"), r.headers.get("Last-Modified")
                rows = st.parse_espn(json.load(r), tour)
            hits = [(x["id"], x["status"], x["sets1"], x["sets2"], x["winner"]) for x in rows if x["id"].split(":")[-1] in WANT]
            print(tour, day, len(rows), "rows | cache:", age, "|", hits)
        except Exception as e:                               # noqa: BLE001
            print(tour, day, "ERR", e)
