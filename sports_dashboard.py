"""Phone dashboard for THE D503 SPORTS ENGINE (docs/sports/index.html).
Top: today's board (2-leg, 3-leg, lock, dog). Below: results, record, and what the engine learned.
Self-contained HTML (inline CSS/SVG, tiny JS for the "updated X min ago" light)."""
import html
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd

PT = ZoneInfo("America/Los_Angeles")
REPO = "D503therapper/autonomous-crypto-engine"
PAGE = "docs/sports/index.html"
LOOK = {   # kind -> label, accent, second accent
    "two":   ("2-LEG OF THE DAY", "#2f8bff", "#22d3ee"),
    "three": ("3-LEG OF THE DAY", "#ffc233", "#ff8a00"),
    "lock":  ("LOCK OF THE DAY", "#22e39a", "#0fb87a"),
    "dog":   ("DOG OF THE DAY", "#ff5a1f", "#ff2a2a"),
}
ICON = {"two": "⚡", "three": "👑", "lock": "🔒", "dog": "🐺"}
E = html.escape


def _am(a):
    return f"+{a}" if a > 0 else str(a)


def _money(x, sign=False):
    s = ("+" if x >= 0 else "−") if sign else ("" if x >= 0 else "−")
    return f"{s}${abs(x):,.0f}"


def _time(iso):
    t = datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT)
    return t.strftime("%-I:%M %p").replace(":00 ", " ") + " PT"


def _chip(status):
    txt = {"open": "LOCKED IN 🔒", "won": "CASHED ✓", "lost": "LOST", "push": "PUSH"}[status]
    return f'<span class="chip {status}">{txt}</span>'


def _leg(leg):
    lg = sd.LEAGUES[leg["league"]]
    mk = "ML" if leg["market"] == "ml" else f'{leg["line"]:+g}'
    res = leg.get("result")
    mark = {"won": '<b class="lw">✓</b>', "lost": '<b class="ll">✗</b>', "push": '<b class="lp">P</b>',
            "void": '<b class="lp">V</b>'}.get(res, "")
    why = " · ".join(E(r) for r in leg.get("reasons") or [])
    outs = f'<div class="outs">🚑 {E(leg["opp"])} missing: {E(", ".join(leg["opp_outs"]))}</div>' if leg.get("opp_outs") else ""
    return f"""<div class="leg">
  <div class="lt"><span class="lgb">{lg[3]} {lg[2]}</span><span class="tm">{_time(leg["start"])}</span></div>
  <div class="lm"><span class="pick">{mark}{E(leg["team"])} <em>{mk}</em></span><span class="od">{_am(leg["odds"])}</span></div>
  <div class="ls">{"vs" if leg["home"] else "@"} {E(leg["opp"])}</div>
  {f'<div class="why">{why}</div>' if why else ""}{outs}
  {f'<div class="fin">{E(leg["score"])}</div>' if leg.get("score") else ""}
</div>"""


def _pick_card(kind, pk):
    label, c1, c2 = LOOK[kind]
    if not pk:
        return f"""<section class="pk" style="--c1:{c1};--c2:{c2}"><div class="pk-h"><span class="pk-i">{ICON[kind]}</span>
<span class="pk-l">{label}</span></div><div class="nopick">No play today — nothing on the slate fits the rules.</div></section>"""
    if pk["status"] == "waiting":
        why = " · ".join(E(w) for w in pk.get("waiting") or [])
        return f"""<section class="pk waiting" style="--c1:{c1};--c2:{c2}"><div class="pk-h"><span class="pk-i">{ICON[kind]}</span>
<span class="pk-l">{label}</span><span class="chip waiting">PICK COMING</span></div>
<div class="lock">⏳ Waiting on: {why}</div><div class="lock">Posted by {_time(pk["deadline"])} at the latest — once it's up, it's final.</div></section>"""
    win = pk["stake"] * (pk["dec"] - 1)
    legs = "".join(_leg(leg) for leg in pk["legs"])
    return f"""<section class="pk {pk["status"]}" style="--c1:{c1};--c2:{c2}">
  <div class="pk-h"><span class="pk-i">{ICON[kind]}</span><span class="pk-l">{label}</span>{_chip(pk["status"])}</div>
  <div class="pk-o"><span class="big">{_am(pk["american"])}</span>
    <span class="pay">$100 wins <b>${win:,.0f}</b></span></div>
  {legs}
</section>"""


def render(picks, model, games, series, start_bank, updated_ms):
    now = datetime.now(PT)
    today = now.date().isoformat()
    todays = {p["kind"]: p for p in picks if p["date"] == today}
    board_date = now.strftime("%A, %B %-d")
    drop = '<div class="drop">🎯 Picks go up as soon as the engine is sure — from <b>6 PM PT</b> the night before. Once posted, they\'re final.</div>'
    board = "".join(_pick_card(k, todays.get(k)) for k in LOOK) if todays else drop
    tmr = (now + timedelta(days=1)).date()
    tomorrows = {p["kind"]: p for p in picks if p["date"] == tmr.isoformat()}
    tomorrow = (f'<div class="sec"><h2><i>●</i> TOMORROW\'S BOARD</h2><span>{tmr:%A, %B %-d}</span></div>'
                + "".join(_pick_card(k, tomorrows[k]) for k in LOOK if k in tomorrows)) if tomorrows else ""

    done = [p for p in picks if p["status"] in ("won", "lost", "push")]
    done.sort(key=lambda p: (p["date"], p.get("settled", "")))

    def wl(ps):
        w, l_, pu = (sum(p["status"] == k for p in ps) for k in ("won", "lost", "push"))
        return f"{w}-{l_}" + (f"-{pu}" if pu else ""), (w / (w + l_) if w + l_ else None)

    def streak(ps):
        if not ps:
            return ""
        last, n = ps[-1]["status"], 0
        for p in reversed(ps):
            if p["status"] != last:
                break
            n += 1
        return f'{"W" if last == "won" else "L" if last == "lost" else "P"}{n}'
    m0 = datetime(now.year, now.month, 1, tzinfo=PT).date().isoformat()
    rec_all, hit_all = wl(done)
    rec_day, _ = wl([p for p in done if p["date"] == today])
    rec_month, hit_month = wl([p for p in done if p["date"] >= m0])
    first = min((p["date"] for p in picks), default=today)
    hot = streak(done)

    def tile(label, sub, val, foot, hue, cls="w"):
        return (f'<div class="tile" style="--h:{hue}"><div class="tl">{label}</div><div class="ts">{sub}</div>'
                f'<div class="tv {cls}">{val}</div><div class="ts" style="color:{hue}">{foot}</div></div>')
    tiles = (tile("This month", now.strftime("%B"), rec_month, f"{hit_month:.0%} hit" if hit_month is not None else "&nbsp;", "#2f8bff")
             + tile("Hit rate", f"since {datetime.fromisoformat(first):%b %-d}", f"{hit_all:.0%}" if hit_all is not None else "—", "all plays", "#22e39a")
             + tile("Streak", "current", hot or "—", "🔥 heater" if hot.startswith("W") and len(hot) > 1 and int(hot[1:]) >= 3 else "&nbsp;",
                    "#ffc233", "up" if hot.startswith("W") else "dn" if hot.startswith("L") else "w"))
    strip = "".join(f'<i class="{p["status"]}" title="{E(p["date"])}"></i>' for p in done[-40:]) or '<span class="empty">results show up here</span>'

    # record per pick type
    rec = []
    for kind, (label, c1, c2) in LOOK.items():
        ps = [p for p in done if p["kind"] == kind]
        r, h = wl(ps)
        st = streak(ps)
        rec.append(f'<div class="rc" style="--c1:{c1};--c2:{c2}"><div class="rc-t">{ICON[kind]} {label.replace(" OF THE DAY", "")}</div>'
                   f'<div class="rc-r">{r}</div><div class="rc-p">{f"{h:.0%} hit" if h is not None else "&nbsp;"}</div>'
                   f'<div class="rc-s">{("streak " + st) if st else "no results yet"}</div></div>')

    # recent results
    rows = []
    for p in list(reversed(done))[:14]:
        label, c1, _ = LOOK[p["kind"]]
        legs = " + ".join(f'{E(l["team"])}{"" if l["market"] == "ml" else " " + format(l["line"], "+g")}' for l in p["legs"])
        tag = {"won": "WON", "lost": "LOST", "push": "PUSH"}[p["status"]]
        rows.append(f'<div class="rr"><span class="rk" style="color:{c1}">{ICON[p["kind"]]}</span><div class="rd"><div class="rl">{legs}</div>'
                    f'<div class="rm">{datetime.fromisoformat(p["date"]):%b %-d} · {label.title()} · {_am(p["american"])}</div></div>'
                    f'<span class="chip {p["status"]}">{tag}</span></div>')
    results = "".join(rows) or '<div class="empty">First results land after the first board settles.</div>'

    # the brain, in a nutshell: how the engine improved itself today
    params = model.get("params", {})
    base = model.get("today") or {}
    lines = []
    if base.get("date") == today:
        new = max(0, model.get("finals_seen", 0) - base.get("finals", 0))
        lines.append(f"Studied <b>{new:,}</b> new final score{'s' if new != 1 else ''} today and retrained on all of them.")

    def acc(ps):
        n = sum(p.get("eval_games", 0) for p in ps.values())
        return sum(p["accuracy"] * p.get("eval_games", 0) for p in ps.values()) / n if n else None
    now_acc = acc(params)
    if now_acc is not None:
        was = base.get("acc") or {}
        common = {lg: params[lg] for lg in was if lg in params}
        start = (sum(was[lg] * common[lg].get("eval_games", 0) for lg in common)
                 / max(1, sum(p.get("eval_games", 0) for p in common.values()))) if common else None
        delta = f' <span class="{"up" if now_acc >= start else "dn"}">({(now_acc - start) * 100:+.1f} pts today)</span>' if start else ""
        lines.append(f"Picks the winner <b>{now_acc:.1%}</b> of the time across {len(params)} leagues{delta}.")
    changes = [f"{sd.LEAGUES[e['league']][2]}: {E(e['change'])}" for e in model.get("log", [])
               if e["date"] == today and e["change"] not in ("no change", "first tune")]
    if changes:
        lines.append("Adjusted: " + " · ".join(changes[:3]) + (f" (+{len(changes) - 3} more)" if len(changes) > 3 else ""))
    elif params:
        lines.append("No rule changes needed — its current settings are still the best fit.")
    legs = [l for p in picks for l in p["legs"] if l.get("result") in ("won", "lost")]
    if legs:
        said = sum(l["p"] for l in legs) / len(legs)
        got = sum(l["result"] == "won" for l in legs) / len(legs)
        lines.append(f"Self-check: said <b>{said:.0%}</b> of its legs would win — <b class=\"{'up' if got >= said else 'dn'}\">{got:.0%}</b> did.")
    if not lines:
        lines.append("Warming up — studying past seasons before the first board.")
    brain = '<div class="br self"><div class="bn">🧠 Today in a nutshell</div>' + "".join(f'<div class="bs nut">{x}</div>' for x in lines) + "</div>"
    tuned = model.get("tuned_on", "—")

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="refresh" content="300">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="D503 Sports">
<meta name="theme-color" content="#05070b">
<title>THE D503 · Sports Engine</title>
<link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="icon" href="icon-512.png"><link rel="manifest" href="manifest.webmanifest">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Teko:wght@600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#040609;--card:#0b0f17;--card2:#101723;--line:#1b2433;--text:#f2f5fb;--muted:#22d3ee;--up:#22e39a;--dn:#ff3b3b;--gold:#ffc233;--accent:#ffc233}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}}
body{{font:15px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",system-ui,sans-serif;min-height:100vh;
  background:radial-gradient(640px 400px at 10% -120px,rgba(255,194,51,.22),transparent 70%),
             radial-gradient(640px 420px at 100% -80px,rgba(255,90,31,.20),transparent 70%),
             repeating-linear-gradient(135deg,rgba(255,255,255,.018) 0 2px,transparent 2px 7px),var(--bg)}}
main{{max-width:520px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 18px) 16px 34px;overflow:hidden}}
.head{{position:relative;margin:6px 0 18px;display:flex;align-items:center;gap:12px}}
.logo{{width:62px;height:62px;border-radius:15px;flex:none;box-shadow:0 10px 28px -8px rgba(227,18,27,.8)}}
.title{{font-family:"Anton",Impact,sans-serif;font-style:italic;font-size:44px;line-height:1;letter-spacing:.01em;color:#fff;text-shadow:3px 4px 0 #000,0 0 22px rgba(227,18,27,.55)}}
.the{{font-size:22px;color:#e3121b;vertical-align:6px;margin-right:2px;text-shadow:2px 3px 0 #000}}
.tag{{margin-top:6px;font-family:"Teko","Arial Narrow",sans-serif;font-weight:600;font-size:17px;line-height:1;letter-spacing:.3em;color:#ffc233;
  background:linear-gradient(180deg,#fff0b0,#ffc233 45%,#d18a00 55%,#ffd35c);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
  filter:drop-shadow(0 0 8px rgba(255,170,40,.45))}}
.live{{position:absolute;top:0;right:0;white-space:nowrap;display:flex;align-items:center;gap:7px;font-size:12px;font-weight:700;color:var(--up);
  background:rgba(34,227,154,.08);border:1px solid rgba(34,227,154,.35);padding:6px 10px;border-radius:999px}}
.dot{{width:8px;height:8px;border-radius:50%;background:var(--up);animation:pulse 2s infinite}}
.dot.stale{{background:#f5b73b;animation:none}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(34,227,154,.6)}}70%{{box-shadow:0 0 0 10px rgba(34,227,154,0)}}100%{{box-shadow:0 0 0 0 rgba(34,227,154,0)}}}}
.sec{{display:flex;align-items:baseline;justify-content:space-between;margin:22px 2px 10px}}
.sec h2{{margin:0;font-size:13px;font-weight:900;letter-spacing:.2em;color:#fff}}
.sec h2 i{{font-style:normal;color:var(--gold);text-shadow:0 0 10px rgba(255,194,51,.6)}}
.sec span{{font-size:12px;color:var(--gold);font-weight:600}}
.board{{position:relative;padding-top:52px}}
.trust{{position:absolute;top:0;left:50%;transform:translateX(-50%) rotate(-5deg);white-space:nowrap;z-index:3;
  font-weight:900;font-style:italic;font-size:19px;letter-spacing:.12em;padding:7px 26px;color:#0a0a0a;
  background:linear-gradient(90deg,#ffe08a,#ffc233 40%,#ff8a00);clip-path:polygon(4% 0,100% 0,96% 100%,0 100%);
  box-shadow:0 10px 30px -8px rgba(255,160,40,.7);text-shadow:0 1px 0 rgba(255,255,255,.35)}}
.trust:after{{content:"";position:absolute;inset:3px 6%;border-top:1px solid rgba(0,0,0,.35);border-bottom:1px solid rgba(0,0,0,.35);pointer-events:none}}
.drop{{text-align:center;font-weight:700;color:#fff;background:var(--card);border:1px dashed rgba(255,194,51,.55);border-radius:16px;padding:14px;margin-bottom:12px}}
.drop b{{color:var(--gold)}}
.pk{{position:relative;background:linear-gradient(165deg,color-mix(in srgb,var(--c1) 16%,var(--card2)) 0%,var(--card) 55%);border:1px solid color-mix(in srgb,var(--c1) 55%,transparent);
  border-radius:22px;padding:16px 16px 10px;margin-bottom:14px;overflow:hidden;box-shadow:0 18px 50px -22px var(--c1),inset 0 1px 0 rgba(255,255,255,.05)}}
.pk::before{{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.pk.won{{box-shadow:0 0 0 1px var(--up),0 18px 50px -18px var(--up)}} .pk.lost{{opacity:.72}}
.pk-h{{display:flex;align-items:center;gap:10px}}
.pk-i{{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;font-size:18px;background:linear-gradient(135deg,var(--c1),var(--c2));box-shadow:0 6px 18px -6px var(--c1)}}
.pk-l{{flex:1;font-weight:900;font-size:14px;letter-spacing:.14em;color:var(--c1);text-shadow:0 0 12px color-mix(in srgb,var(--c1) 55%,transparent)}}
.chip{{font-size:10.5px;font-weight:900;letter-spacing:.1em;padding:4px 8px;border-radius:999px;white-space:nowrap}}
.lock{{font-size:12.5px;font-weight:800;color:var(--gold);margin:2px 0 4px}}
.pk.waiting{{border-style:dashed}}
.chip.waiting{{color:#0a0a0a;background:var(--gold)}}
.chip.open{{color:#fff;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2)}}
.chip.won{{color:#04110b;background:var(--up)}} .chip.lost{{color:#fff;background:var(--dn)}} .chip.push{{color:#000;background:var(--gold)}}
.pk-o{{display:flex;align-items:center;justify-content:space-between;margin:12px 0 6px}}
.big{{font-size:42px;font-weight:900;letter-spacing:-.02em;line-height:1;color:#fff;font-variant-numeric:tabular-nums;text-shadow:0 0 24px color-mix(in srgb,var(--c1) 60%,transparent)}}
.pay{{text-align:right;font-size:14px;color:#fff;font-weight:600}} .pay b{{color:var(--c1);font-size:18px}} .pay span{{color:var(--c1);font-size:12px}}
.leg{{border-top:1px solid rgba(255,255,255,.07);padding:10px 0 8px}}
.lt{{display:flex;justify-content:space-between;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--c1)}}
.lgb{{color:#fff}}
.lm{{display:flex;justify-content:space-between;align-items:baseline;margin-top:3px}}
.pick{{font-size:18px;font-weight:850;color:#fff}} .pick em{{font-style:normal;color:var(--c1);font-weight:900;margin-left:2px}}
.od{{font-size:17px;font-weight:900;color:#fff;font-variant-numeric:tabular-nums}}
.ls{{font-size:12.5px;color:#fff;margin-top:2px}} .ls b{{color:#fff}}
.ep{{color:var(--up);font-weight:800}} .en{{color:#ff8a5c;font-weight:800}}
.why{{font-size:12px;color:#e8c77a;margin-top:4px}}
.outs{{font-size:11.5px;color:#ff8a5c;margin-top:3px}}
.fin{{font-size:12px;color:#fff;opacity:.75;margin-top:3px}}
.lw{{color:var(--up);margin-right:6px}} .ll{{color:var(--dn);margin-right:6px}} .lp{{color:var(--gold);margin-right:6px}}
.nopick{{color:var(--muted);font-weight:600;font-size:13px;padding:12px 0 6px}}
.hero{{position:relative;background:linear-gradient(160deg,#131a28 0%,var(--card) 60%);border:1px solid rgba(255,194,51,.28);border-radius:24px;padding:20px 20px 8px;overflow:hidden;
  box-shadow:0 20px 60px -24px rgba(255,160,40,.45)}}
.lbl{{color:#fff;font-size:12px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}
.total{{font-size:42px;font-weight:800;letter-spacing:-.02em;margin:4px 0 8px;font-variant-numeric:tabular-nums}}
.pill{{display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:14px;padding:5px 11px;border-radius:999px;
  background:color-mix(in srgb,var(--p) 16%,transparent);color:var(--p);font-variant-numeric:tabular-nums}}
.pill small{{color:#fff;font-weight:900;font-size:11px;letter-spacing:.08em}}
.month{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}}
.tile{{background:linear-gradient(180deg,color-mix(in srgb,var(--h) 14%,transparent),rgba(255,255,255,.02));border:1px solid color-mix(in srgb,var(--h) 45%,transparent);
  border-radius:14px;padding:10px 9px;min-width:0;overflow:hidden;box-shadow:0 6px 22px -12px var(--h)}}
.tl{{color:#fff;font-size:9.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}}
.ts{{font-size:11px;font-weight:700;color:#fff;margin-top:1px;white-space:nowrap}} .ts.up{{color:var(--up)}} .ts.dn{{color:var(--dn)}}
.tv{{font-size:clamp(13px,4.2vw,17px);font-weight:800;margin-top:6px;white-space:nowrap}}
.ar{{font-size:.7em;margin-right:3px;vertical-align:1px}}
.up{{color:var(--up)}} .dn{{color:var(--dn)}} .w{{color:#fff}}
.strip{{display:flex;flex-wrap:wrap;gap:4px;margin:14px 0 12px}}
.strip i{{width:12px;height:12px;border-radius:3px;background:#2f8bff}}
.strip i.won{{background:var(--up);box-shadow:0 0 8px rgba(34,227,154,.6)}} .strip i.lost{{background:var(--dn)}} .strip i.push{{background:var(--gold)}}
.recs{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.rc{{position:relative;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px;overflow:hidden}}
.rc::before{{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.rc-t{{font-size:11px;font-weight:900;letter-spacing:.12em;color:var(--c1)}}
.rc-r{{font-size:26px;font-weight:900;color:#fff;margin-top:4px;font-variant-numeric:tabular-nums}}
.rc-p{{font-weight:800;color:var(--c1)}} .rc-s{{font-size:11.5px;color:var(--c2);font-weight:700;margin-top:2px}}
.list{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:4px 14px}}
.rr{{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}} .rr:last-child{{border:0}}
.rk{{font-size:18px}} .rd{{flex:1;min-width:0}}
.rl{{font-weight:750;color:#fff;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rm{{font-size:11.5px;color:var(--muted);font-weight:600}}
.rv{{font-weight:900;font-variant-numeric:tabular-nums}}
.empty{{color:var(--muted);font-weight:600;font-size:13px;padding:12px 0}}
.br{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 14px;margin-bottom:10px}}
.br.self{{border-color:rgba(255,194,51,.35)}}
.bh{{display:flex;justify-content:space-between;align-items:center}}
.bn{{font-weight:900;color:#fff;font-size:15px}} .bt{{font-size:12px;color:var(--muted);font-weight:700}} .bt b{{color:var(--gold)}}
.bs{{font-size:12.5px;color:#fff;margin-top:3px}} .bs b{{color:#fff}} .bs b.up,.bs .up{{color:var(--up)}} .bs b.dn,.bs .dn{{color:var(--dn)}}
.fxs{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:9px}}
.fx{{position:relative;font-size:10px;font-weight:800;color:#fff;letter-spacing:.04em;padding-top:8px;text-align:center}}
.fx i{{position:absolute;top:0;left:0;height:4px;border-radius:4px;box-shadow:0 0 8px currentColor}}
.fx::before{{content:"";position:absolute;top:0;left:0;right:0;height:4px;border-radius:4px;background:rgba(255,255,255,.08)}}
.bc{{font-size:11.5px;color:#e8c77a;margin-top:8px}}
.nut{{font-size:13.5px;margin-top:7px;padding-left:14px;position:relative}} .nut:before{{content:"▸";position:absolute;left:0;color:var(--gold)}}
.foot{{text-align:center;color:#ffe08a;font-size:12px;margin-top:22px;line-height:1.6}}
.foot b{{color:#fff}} .foot a{{color:#22d3ee;text-decoration:none;font-weight:700}}
</style></head><body><main>
<header class="head">
  <img class="logo" src="icon-512.png" alt="">
  <div><div class="title"><span class="the">THE</span> D503</div>
  <div class="tag">SPORTS ENGINE</div></div>
  <div class="live"><span class="dot" id="dot"></span><span id="ago">Live</span></div>
</header>
<div class="sec"><h2><i>●</i> TODAY'S BOARD</h2><span>{E(board_date)}</span></div>
<div class="board"><div class="trust">TRUST THE ALGORITHM!</div>{board}</div>
{tomorrow}

<div class="sec"><h2><i>●</i> THE RESULTS</h2><span>every play, graded</span></div>
<section class="hero">
  <div class="lbl">Overall record</div>
  <div class="total">{rec_all}</div>
  <span class="pill" style="--p:#ffc233">{rec_day} <small>TODAY</small></span>
  <div class="month">{tiles}</div>
  <div class="strip">{strip}</div>
</section>
<div class="sec"><h2><i>●</i> RECORD BY PLAY</h2><span>{len(done)} graded</span></div>
<div class="recs">{"".join(rec)}</div>
<div class="sec"><h2><i>●</i> RECENT TICKETS</h2></div>
<div class="list">{results}</div>
<div class="sec"><h2><i>●</i> THE BRAIN</h2><span>retrained {E(tuned)}</span></div>
{brain}
<div class="foot"><b>THE D503 SPORTS ENGINE</b><br>
Ratings · form · rest · injuries · line moves — retrained after every final score.<br>
Picks only — no bets placed · refreshes hourly · <a href="../">crypto engine →</a></div>
</main>
<script>
(function(){{var t={int(updated_ms)},m=Math.max(0,Math.round((Date.now()-t)/60000));
var s=m<1?"just now":m<60?m+" min ago":Math.floor(m/60)+"h "+(m%60)+"m ago";
document.getElementById("ago").textContent="Live · "+s;
if(m>150)document.getElementById("dot").className="dot stale";
fetch("https://api.github.com/repos/{REPO}/contents/{PAGE}?ref=main",
  {{headers:{{Accept:"application/vnd.github.raw"}},cache:"no-store"}})
 .then(function(r){{return r.ok?r.text():""}})
 .then(function(h){{var x=/var t=(\\d+),m=/.exec(h);
   if(x&&+x[1]>t){{document.open();document.write(h);document.close();}}}})
 .catch(function(){{}});}})();
</script></body></html>"""


def write(picks, model, games, series, start_bank, path=PAGE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(render(picks, model, games, series, start_bank, int(time.time() * 1000)))
