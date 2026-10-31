import json, math, os
D = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(D, "gap_rows.json")))
print("rows", len(rows), "by fbs:", {k: sum(r["fbs"] == k for r in rows) for k in (0, 1, 2, None)})


def cell(name, sel):
    out = []
    for half, f in (("train 20-23", lambda r: r["season"] <= 2023), ("held 24-26", lambda r: r["season"] >= 2024)):
        xs = [r for r in rows if sel(r) and f(r)]
        n = len(xs)
        if not n:
            out.append(f"{half} 0")
            continue
        w = sum(r["won"] for r in xs)
        roi = sum((r["dec"] - 1) if r["won"] else -1 for r in xs) / n
        exp = sum(r["nv"] for r in xs)
        var = sum(r["nv"] * (1 - r["nv"]) for r in xs)
        z = (w - exp) / math.sqrt(var) if var else 0
        out.append(f"{half} {w}-{n - w} {roi:+.1%} z{z:+.1f}")
    by = {}
    for r in rows:
        if sel(r):
            by.setdefault(r["season"], []).append((r["dec"] - 1) if r["won"] else -1)
    ss = " ".join(f"{s % 100}:{sum(v) / len(v):+.0%}/{len(v)}" for s, v in sorted(by.items()))
    print(f"{name:52} {' | '.join(out)} || {ss}")


dog = lambda r: 100 <= r["odds"] <= 350
gap = lambda r: r["own"] - r["nv"]
backed = lambda r: r["elo"] is not None and r["elo"] >= 0
for lab, fk in (("ALL", lambda r: True), ("FBS v FBS", lambda r: r["fbs"] == 2), ("FBS v FCS", lambda r: r["fbs"] == 1),
                ("FCS v FCS", lambda r: r["fbs"] == 0)):
    print(f"\n== {lab} ==")
    cell("every dog +100..+350", lambda r: dog(r) and fk(r))
    cell("gap 15+ rating-backed (the 🔍 rule)", lambda r: dog(r) and fk(r) and gap(r) >= 0.15 and backed(r))
    cell("gap 10-15 rating-backed", lambda r: dog(r) and fk(r) and 0.10 <= gap(r) < 0.15 and backed(r))
    cell("gap 15-20 rating-backed", lambda r: dog(r) and fk(r) and 0.15 <= gap(r) < 0.20 and backed(r))
    cell("gap 20+ rating-backed", lambda r: dog(r) and fk(r) and gap(r) >= 0.20 and backed(r))
    cell("gap 5-10 rating-backed", lambda r: dog(r) and fk(r) and 0.05 <= gap(r) < 0.10 and backed(r))
    cell("gap 15+ NOT backed", lambda r: dog(r) and fk(r) and gap(r) >= 0.15 and not backed(r))
    cell("slight fav -101..-150", lambda r: -150 <= r["odds"] <= -101 and fk(r))
    cell("slight fav, raw gap 5+", lambda r: -150 <= r["odds"] <= -101 and fk(r) and gap(r) >= 0.05)
    cell("slight fav, raw gap 10+", lambda r: -150 <= r["odds"] <= -101 and fk(r) and gap(r) >= 0.10)
