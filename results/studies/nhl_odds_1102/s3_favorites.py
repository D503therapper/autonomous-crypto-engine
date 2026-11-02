"""STUDY 3 - HOCKEY FAVORITES -101..-150 on 2020-21..2022-23 at the MORNING price (and the open / the close): where they win
or lose against the price, the value play's rule (the own read - the line + b2b / rest - over the price, sports.own_beats),
the Lock (56%+ with the own read over the price, never -119..-101), LEAN_NHL_FAV_BAND (no hockey favorite lean at
-150..-130 - the 10/28 audit's -12.5% on 376, 0 of 4 seasons, on the 2023-26 replay at the close), and whether the
open -> morning move on the favorite matters."""
import json
import lib

D = lib.build()
ROWS = [r for r in D["rows"] if lib.in_seasons(r)]
out = []


def P(s):
    print(s); out.append(s)


def favs(at):
    xs = []
    for r in ROWS:
        ss = lib.sides(r, at)
        if not ss:
            continue
        for x in ss:
            if -150 <= x["am"] <= -101:
                mv = None
                if r["open"] and r["morning"]:
                    m = r["morning"]["p"] - r["open"]["p"]
                    mv = m if x["side"] == "h" else -m        # + = the money came TO this favorite open -> morning
                x["mv"] = mv
                xs.append(x)
    return xs


def S(xs):
    return lib.st([(x["r"]["season"], x["profit"], 1) for x in xs])


def close_S(xs):
    bets = []
    for x in xs:
        r = x["r"]
        d = lib.dec(r["ch"] if x["side"] == "h" else r["ca"])
        bets.append((r["season"], (d - 1) if x["won"] else -1.0, 1))
    return lib.st(bets)


for at in ("morning", "open", "close"):
    P(f"\n===== {at.upper()} =====")
    xs = favs(at)
    P(lib.line("every favorite -101..-150", S(xs)))
    for lo, hi in ((-150, -130), (-129, -120), (-119, -101)):
        ys = [x for x in xs if lo <= x["am"] <= hi]
        P(lib.line(f"  {lo}..{hi}", S(ys)))
        P(lib.line(f"    home", S([x for x in ys if x["home"]])))
        P(lib.line(f"    road", S([x for x in ys if not x["home"]])))
        P(lib.line(f"    own read over the price (value-play rule)", S([x for x in ys if x["own"] > 1 / x["dec"]])))
        P(lib.line(f"    rested vs a b2b dog", S([x for x in ys if x["ob2b"] and not x["b2b"]])))
        P(lib.line(f"    no b2b either side", S([x for x in ys if not x["ob2b"] and not x["b2b"]])))
        P(lib.line(f"    the favorite ON a b2b", S([x for x in ys if x["b2b"]])))
    P(lib.line("THE LOCK cell: -150..-127, own read 56%+ AND over the price", S([x for x in xs if -150 <= x["am"] <= -127 and x["own"] >= 0.56 and x["own"] > 1 / x["dec"]])))
    P(lib.line("value-play rule anywhere -101..-150 (own over the price)", S([x for x in xs if x["own"] > 1 / x["dec"]])))
    P(lib.line("  ...value-play rule, -120..-150 only", S([x for x in xs if x["own"] > 1 / x["dec"] and x["am"] <= -120])))
    if at == "morning":
        P("-- the open -> morning move on the favorite (no-vig points; + = money came TO the favorite)")
        ys = [x for x in xs if x["mv"] is not None]
        P(lib.line(" favorites with both looks", S(ys)))
        for lo, hi, nm in ((0.03, 1, "came TO it 3+"), (0.015, 0.03, "came to it 1.5-3"), (-0.015, 0.015, "flat"),
                           (-0.03, -0.015, "left it 1.5-3"), (-1, -0.03, "LEFT it 3+")):
            zs = [x for x in ys if lo <= x["mv"] < hi]
            P(lib.line(f"  {nm}", S(zs)))
            P(lib.line(f"    ...graded at the close", close_S(zs)))
        for lo, hi in ((-150, -130), (-129, -101)):
            zs = [x for x in ys if lo <= x["am"] <= hi]
            P(lib.line(f"  {lo}..{hi} LEFT it 2+", S([x for x in zs if x["mv"] <= -0.02])))
            P(lib.line(f"  {lo}..{hi} came TO it 2+", S([x for x in zs if x["mv"] >= 0.02])))
    if at == "morning":
        P("-- the LEAN question: the -150..-130 favorite as the who-wins pick (win rate vs what the price needs)")
        for lo, hi in ((-150, -130), (-129, -101)):
            ys = [x for x in xs if lo <= x["am"] <= hi]
            n = len(ys); w = sum(x["won"] for x in ys); need = sum(1 / x["dec"] for x in ys) / max(n, 1)
            P(f"  {lo}..{hi}: won {w}/{n} = {100 * w / max(n, 1):.1f}% vs the price's {100 * need:.1f}%")

json.dump(out, open(f"{lib.OUT}/s3_out.json", "w"), indent=0)
open(f"{lib.OUT}/s3_out.txt", "w").write("\n".join(out) + "\n")
