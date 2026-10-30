"""STUDY 4 (10/30) - A BOOK TAKES THE GAME OFF THE BOARD (book-by-book, paid odds history, NFL + college football).
When a book that posted a game's moneyline at one look is GONE at the next look while 5+ other books still post it, that
book usually pulled it on news (a QB / star status, weather). The move that comes with a pull is a NEWS move, not a money
move - the 10/8 / 10/10 move studies (drift, jump, steam, first mover) never split the two.
  (a) how often it happens, and how big the move is with a pull vs without one;
  (b) FOLLOW the news: bet the side the median no-vig moved 1.5+ points toward at the look where the book is gone, at
      that look's median price (moneyline +100..+350 dogs / -101..-150 favorites / and every price -400..+350);
  (c) the same-size moves with NO pull (control);
  (d) does the pulled book come back with a price that agrees (the market settles there)?
TRAIN 2020-23, HELD OUT 2024 / 2025 / 2026. Pure market bets (no engine read), every look 0.03-8 days out."""
import json
import os

import lib

TRAIN, HELD = (2020, 2023), [2024, 2025, 2026]


def scan(lg):
    games = lib.load_football(lg)
    out = []
    for g in games:
        looks = g["all_ml"]                        # oldest first (days out descending)
        for i in range(1, len(looks)):
            d0, b0 = looks[i - 1]
            d1, b1 = looks[i]
            if d1 < 0.1 or len(b1) < 5:
                continue
            gone = [b for b in b0 if b not in b1]
            common = [b for b in b0 if b in b1]
            if len(common) < 4:
                continue
            p0 = lib.ml_med({b: b0[b] for b in common})[2]
            h1, a1, p1 = lib.ml_med(b1)
            mv = p1 - p0
            back = None
            if gone and i + 1 < len(looks):
                b2 = looks[i + 1][1]
                hits = [b for b in gone if b in b2]
                if hits:
                    back = lib.nv(*b2[hits[0]]) - p0
            out.append({"season": g["season"], "pull": bool(gone), "n_gone": len(gone), "mv": mv, "h": h1, "a": a1,
                        "margin": g["margin"], "days": d1, "back": back, "id": g["id"]})
    return out


def main():
    lines, res = [], {}
    for lg in ("nfl", "ncaaf"):
        ev = scan(lg)
        pulls = [e for e in ev if e["pull"]]
        lines.append(f"\n=== {lg.upper()}: {len(ev)} look-to-look steps, {len(pulls)} with a book gone "
                     f"({len({e['id'] for e in pulls})} games) ===")
        for nm, cell in (("with a pull", pulls), ("no pull", [e for e in ev if not e["pull"]])):
            mvs = [abs(e["mv"]) for e in cell]
            big = sum(1 for m in mvs if m >= 0.015)
            lines.append(f"{nm:12s}: mean |move| {100*sum(mvs)/max(1,len(mvs)):.2f} pts, 1.5+ pts {big} of {len(mvs)} ({100*big/max(1,len(mvs)):.1f}%)")
        backs = [e for e in pulls if e["back"] is not None and abs(e["mv"]) >= 0.015]
        if backs:
            agree = sum(1 for e in backs if e["back"] * e["mv"] > 0)
            lines.append(f"pulled book back next look after a 1.5+ move: {len(backs)}, its price on the moved side {agree} ({100*agree/len(backs):.0f}%)")
        for cut in (0.015, 0.03):
            for nm, cell in (("PULL", [e for e in pulls if abs(e["mv"]) >= cut]),
                             ("PULL 2+ books", [e for e in pulls if abs(e["mv"]) >= cut and e["n_gone"] >= 2]),
                             ("no pull", [e for e in ev if not e["pull"] and abs(e["mv"]) >= cut])):
                for tag, lo, hi in (("dog +100..+350", 2.0, 4.5), ("fav -101..-150", 1.6667, 2.0), ("any -400..+350", 1.25, 4.5)):
                    bets = []
                    for e in cell:
                        home = e["mv"] > 0
                        d = e["h"] if home else e["a"]
                        if lo <= d <= hi:
                            bets.append((e["season"], lib.profit((e["margin"] > 0) == home, d)))
                    s = lib.summ(bets, TRAIN, HELD)
                    res[f"{lg} {nm} move {cut} follow {tag}"] = s
                    lines.append(lib.fmt(f"{lg} {nm} move {cut*100:.1f}+ FOLLOW {tag}", s))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(lib.OUT, "s4_out.txt"), "w").write(txt + "\n")
    json.dump(res, open(os.path.join(lib.OUT, "s4_out.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
