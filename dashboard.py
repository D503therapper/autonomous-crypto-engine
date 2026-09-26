"""Phone dashboard (docs/index.html): dark trading-app look, total balance with a chart,
one card per market with its own sparkline, open positions and latest trade.
Self-contained HTML (inline CSS/SVG, tiny JS for the "updated X min ago" light)."""
import csv
import html
import os
import time

import config


def _series(path, n=120):
    """(ms, equity) points from an equity.csv, downsampled to about n points."""
    if not os.path.exists(path):
        return []
    pts = []
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                t = time.mktime(time.strptime(row["time"], "%Y-%m-%d %H:%M")) - time.timezone
                pts.append((t * 1000, float(row["equity"])))
            except (KeyError, ValueError):
                pass
    step = max(1, len(pts) // n)
    out = pts[::step]
    if pts and out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def _last_trade(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def _combine(series_list):
    """Sum several accounts' equity on a shared timeline (each carries its last value forward)."""
    times = sorted({t for s in series_list for t, _ in s})
    out, idx, last = [], [0] * len(series_list), [config.STARTING_CASH_USD] * len(series_list)
    for t in times:
        for k, s in enumerate(series_list):
            while idx[k] < len(s) and s[idx[k]][0] <= t:
                last[k] = s[idx[k]][1]
                idx[k] += 1
        out.append((t, sum(last)))
    step = max(1, len(out) // 160)
    return out[::step] + ([out[-1]] if out and out[::step][-1] != out[-1] else [])


def _svg(points, w, h, color, uid, base=None, pad=4):
    """Area chart; flat line when there's too little history."""
    if len(points) < 2:
        y = h / 2
        return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><line x1="0" y1="{y}" x2="{w}" '
                f'y2="{y}" stroke="{color}" stroke-width="2" stroke-dasharray="4 5" opacity=".5"/></svg>')
    ts, vs = [p[0] for p in points], [p[1] for p in points]
    lo, hi = min(vs + ([base] if base else [])), max(vs + ([base] if base else []))
    span_v, span_t = (hi - lo) or 1.0, (ts[-1] - ts[0]) or 1.0
    xy = [((t - ts[0]) / span_t * w, pad + (hi - v) / span_v * (h - 2 * pad)) for t, v in points]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = f"0,{h} {line} {w},{h}"
    ref = ""
    if base is not None:
        by = pad + (hi - base) / span_v * (h - 2 * pad)
        ref = f'<line x1="0" y1="{by:.1f}" x2="{w}" y2="{by:.1f}" stroke="#ffffff" stroke-opacity=".12" stroke-dasharray="3 5"/>'
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><defs><linearGradient id="g{uid}" x1="0" '
            f'x2="0" y1="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity=".35"/><stop offset="1" '
            f'stop-color="{color}" stop-opacity="0"/></linearGradient></defs>{ref}<polygon points="{area}" '
            f'fill="url(#g{uid})"/><polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="3.5" fill="{color}"/></svg>')


def _money(x):
    return f"${x:,.2f}"


def _chg(x, base):
    sign = "+" if x >= 0 else "−"
    return f"{sign}${abs(x):,.2f} ({sign}{abs(x) / base:.1%})" if base else f"{sign}${abs(x):,.2f}"


def render(cards, updated_ms):
    """cards: [{name, icon, equity, series, positions, last, extra}] -> HTML string."""
    start = config.STARTING_CASH_USD
    official = [c for c in cards if c.get("official")]
    total = sum(c["equity"] for c in official)
    base = start * len(official)
    pl = total - base
    up = pl >= 0
    accent = "#22e39a" if up else "#ff5c7a"
    # every official account counts (one with no history yet is flat at its starting $500)
    total_series = _combine([c["series"] for c in official]) if official else []
    blocks = []
    for i, c in enumerate(cards):
        d = c["equity"] - start
        col = "#22e39a" if d >= 0 else "#ff5c7a"
        last = c.get("last")
        last_txt = "No trades yet — watching the market"
        if last:
            side = "Bought" if last.get("side") == "BUY" else "Sold"
            pnl = last.get("pnl")
            pnl_txt = ""
            if pnl not in (None, "", "None"):
                p = float(pnl)
                pnl_txt = f' <b class="{"up" if p >= 0 else "dn"}">{"+" if p >= 0 else "−"}${abs(p):,.2f}</b>'
            last_txt = f'{side} {html.escape(last.get("coin", ""))} · {html.escape(last.get("time", ""))} UTC{pnl_txt}'
        extra = f'<div class="badge {c["extra_cls"]}">{html.escape(c["extra"])}</div>' if c.get("extra") else ""
        blocks.append(f"""
<section class="card" style="--c1:{c.get("c1", "#3b82ff")};--c2:{c.get("c2", "#22d3ee")}">
  <div class="card-top">
    <div class="id"><span class="ico">{c["icon"]}</span><div><div class="nm">{html.escape(c["name"])}</div>
      <div class="sub">{c["positions"]} open position{"s" if c["positions"] != 1 else ""}{" · test account" if not c.get("official") else ""}</div></div></div>
    <div class="val"><div class="bal">{_money(c["equity"])}</div><div class="chg {"up" if d >= 0 else "dn"}">{_chg(d, start)}</div></div>
  </div>
  <div class="spark">{_svg(c["series"], 300, 54, col, i, base=start)}</div>
  <div class="foot-row"><span class="last">{last_txt}</span>{extra}</div>
</section>""")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="refresh" content="300">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="D503">
<meta name="theme-color" content="#07090f">
<title>The D503 · Autonomous Trading Engine</title>
<link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="icon" href="apple-touch-icon.png">
<style>
:root{{--bg:#05070d;--card:#0c111b;--card2:#111a2b;--line:#1a2438;--text:#eef3ff;--muted:#7f8aa3;--up:#22e39a;--dn:#ff4d6d;--blue:#3b82ff;--cyan:#22d3ee;--accent:{accent}}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}}
body{{font:15px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Display","Inter",system-ui,sans-serif;
  background:radial-gradient(700px 420px at 15% -140px,rgba(59,130,255,.35),transparent 70%),
             radial-gradient(700px 420px at 95% -60px,color-mix(in srgb,var(--accent) 28%,transparent),transparent 70%),var(--bg);min-height:100vh}}
main{{max-width:520px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 18px) 16px 32px}}
.head{{position:relative;margin:6px 0 22px}}
.title{{font-weight:900;font-size:40px;letter-spacing:-.02em;line-height:1}}
.title .the{{font-size:20px;font-weight:800;letter-spacing:.2em;color:var(--muted);vertical-align:middle}}
.title .d503{{background:linear-gradient(95deg,#3b82ff 0%,#22d3ee 45%,#22e39a 100%);-webkit-background-clip:text;
  background-clip:text;color:transparent;filter:drop-shadow(0 6px 22px rgba(59,130,255,.45))}}
.tagline{{margin-top:8px;font-size:11.5px;font-weight:800;letter-spacing:.28em;color:#c9d6ff;opacity:.85}}
.head .live{{position:absolute;top:2px;right:0}}
.moon{{position:absolute;top:16px;right:-54px;transform:rotate(12deg);padding:6px 60px;font-weight:900;font-size:11.5px;
  letter-spacing:.1em;color:#fff;white-space:nowrap;text-shadow:0 0 8px rgba(255,255,255,.55),0 1px 2px rgba(0,0,0,.4);
  background:linear-gradient(90deg,#16c784,#22d3ee,#3b82ff,#7c3aed);box-shadow:0 8px 24px -6px rgba(34,211,238,.6);z-index:2}}
.hero.hero{{padding-top:74px}}   /* the corner ribbon sits in this space; it never covers the numbers */
.brand{{white-space:nowrap;font-weight:800;letter-spacing:.14em;font-size:11px;background:linear-gradient(90deg,var(--blue),var(--cyan));-webkit-background-clip:text;background-clip:text;color:transparent}}
.live{{white-space:nowrap;display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);background:var(--card);border:1px solid var(--line);padding:6px 10px;border-radius:999px}}
.dot{{width:8px;height:8px;border-radius:50%;background:var(--up);box-shadow:0 0 0 0 var(--up);animation:pulse 2s infinite}}
.dot.stale{{background:#f5b73b;animation:none}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(34,227,154,.6)}}70%{{box-shadow:0 0 0 10px rgba(34,227,154,0)}}100%{{box-shadow:0 0 0 0 rgba(34,227,154,0)}}}}
.hero{{position:relative;background:linear-gradient(160deg,#0f1a33 0%,var(--card) 60%);border:1px solid rgba(59,130,255,.35);border-radius:24px;padding:22px 20px 8px;margin-bottom:14px;overflow:hidden;
  box-shadow:0 0 0 1px rgba(59,130,255,.08),0 20px 60px -20px rgba(59,130,255,.45)}}
.lbl{{color:var(--muted);font-size:13px;letter-spacing:.02em}}
.total{{font-size:44px;font-weight:750;letter-spacing:-.02em;margin:4px 0 8px;font-variant-numeric:tabular-nums}}
.pill{{display:inline-flex;align-items:center;gap:6px;font-weight:650;font-size:14px;padding:5px 11px;border-radius:999px;
  background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent);font-variant-numeric:tabular-nums}}
.hero .chart{{height:110px;margin:14px -20px 0}}
.hero .chart svg,.spark svg{{width:100%;height:100%;display:block}}
.card{{position:relative;background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);border-radius:20px;padding:16px 16px 12px;margin-bottom:12px;overflow:hidden}}
.card::before{{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.card-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}
.id{{display:flex;gap:12px;align-items:center}}
.ico{{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;font-size:20px;color:#fff;font-weight:800;
  background:linear-gradient(135deg,var(--c1),var(--c2));box-shadow:0 8px 20px -8px var(--c1)}}
.nm{{font-weight:700;font-size:17px}}
.sub{{color:var(--muted);font-size:12.5px;margin-top:1px}}
.val{{text-align:right}}
.bal{{font-weight:700;font-size:19px;font-variant-numeric:tabular-nums}}
.chg{{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:2px}}
.up{{color:var(--up)}} .dn{{color:var(--dn)}}
.spark{{height:54px;margin:12px 0 8px}}
.foot-row{{display:flex;justify-content:space-between;align-items:center;gap:8px;border-top:1px solid var(--line);padding-top:10px}}
.last{{color:var(--muted);font-size:12.5px}}
.last b{{font-weight:650}}
.badge{{font-size:12px;font-weight:650;padding:4px 9px;border-radius:999px;white-space:nowrap}}
.badge.ok{{background:rgba(34,227,154,.12);color:var(--up)}}
.badge.bad{{background:rgba(255,92,122,.14);color:var(--dn)}}
.foot{{text-align:center;color:var(--muted);font-size:12px;margin-top:18px}}
</style></head><body><main>
<header class="head">
  <div class="title"><span class="the">THE</span> <span class="d503">D503</span></div>
  <div class="tagline">AUTONOMOUS TRADING ENGINE</div>
  <div class="live"><span class="dot" id="dot"></span><span id="ago">Live</span></div>
</header>
<section class="hero">
  <div class="moon">TO THE MOON BABY! 🚀</div>
  <div class="lbl">Total balance</div>
  <div class="total">{_money(total)}</div>
  <span class="pill">{"▲" if up else "▼"} {_chg(pl, base)}</span>
  <div class="chart">{_svg(total_series, 360, 110, accent, "t", base=base)}</div>
</section>
{"".join(blocks)}
<div class="foot">THE D503 · each account started with {_money(start)} · refreshes every 5 min</div>
</main>
<script>
(function(){{var t={int(updated_ms)},m=Math.max(0,Math.round((Date.now()-t)/60000));
var s=m<1?"just now":m<60?m+" min ago":Math.floor(m/60)+"h "+(m%60)+"m ago";
document.getElementById("ago").textContent="Live · "+s;
if(m>90)document.getElementById("dot").className="dot stale";}})();
</script></body></html>"""


def write(cards, path="docs/index.html"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(render(cards, int(time.time() * 1000)))
