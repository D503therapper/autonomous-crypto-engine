// 📡 LIVE SCORES for the dashboard's pending picks, straight from ESPN about once a second (cached at the edge for 1s,
// so however many phones are watching, ESPN sees one call a second per league). GET /scores?ids=nfl:401872963,tennis:atp:186239
// -> {"nfl:401872963": {away, home, a, h, clock, live}, "tennis:atp:186239": {tennis, n, sets, pts, srv, done, live}}
// Tennis comes back from player 1's side; the page flips it to our player's side.

const PATHS = {
  nfl: "football/nfl", ncaaf: "football/college-football", nba: "basketball/nba", mlb: "baseball/mlb",
  nhl: "hockey/nhl", ncaab: "basketball/mens-college-basketball", atp: "tennis/atp", wta: "tennis/wta",
};
const EXTRA = { ncaaf: "?groups=80&limit=1000", ncaab: "?groups=50&limit=1000" };

const DBG = {};
const HOSTS = ["https://site.web.api.espn.com", "https://site.api.espn.com"];   // (the first one lets Cloudflare in)
async function board(key, ctx) {
  if (key === "atp" || key === "wta") {                    // tennis runs round the clock: a match in Asia sits on
    const ymd = (d) => new Date(Date.now() + d * 86400000).toISOString().slice(0, 10).replace(/-/g, "");   // the next
    const days = await Promise.all([0, 1].map((d) => boardAt(key, ctx, `?dates=${ymd(d)}`).catch(() => null)));   // day's
    const evs = [];                                                                                       // scoreboard
    for (const d of [await boardAt(key, ctx, "").catch(() => null), ...days]) if (d) evs.push(...(d.events || []));
    return evs.length ? { events: evs } : null;
  }
  return boardAt(key, ctx, EXTRA[key] || "");
}

async function boardAt(key, ctx, q) {
  const path = `/apis/site/v2/sports/${PATHS[key]}/scoreboard${q}`;
  const cache = caches.default;
  const ck = "https://d503-cache" + path;
  const hit = await cache.match(ck);
  if (hit) return hit.json();
  const tries = [];
  for (const [i, host] of HOSTS.entries()) {                 // ESPN turns some servers away: other doors, browser-like
    const bust = `${q ? "&" : "?"}_=${Math.floor(Date.now() / 1000)}`;   // ESPN's own servers hand out older copies
    const r = await fetch(host + path + bust, { headers: {                // (a score flipped 1-3, 1-2, 1-3): a fresh one
      "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
      Accept: "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      Referer: "https://www.espn.com/", Origin: "https://www.espn.com" }, });
    tries.push(`${host.slice(8, 20)} ${r.status}`);
    if (!r.ok) continue;
    DBG[key] = tries.join(" | ");
    const body = await r.text();
    ctx.waitUntil(cache.put(ck, new Response(body, { headers: { "Cache-Control": "max-age=1", "Content-Type": "application/json" } })));
    return JSON.parse(body);
  }
  DBG[key] = tries.join(" | ");
  return null;
}

// ESPN's clock, said plain (the owner, 9/29: we see if it's an intermission and all that). Hockey's break between
// periods comes through as "End of 1st" - that's the 1st intermission.
export function clockText(key, st) {
  const t = String(st.shortDetail || st.detail || "");
  const m = /^End of (1st|2nd)$/i.exec(t);
  if (key === "nhl" && m) return `${m[1]} Intermission`;
  return t;
}

function team(ev, key) {
  const comp = (ev.competitions || [])[0] || {};
  const st = ((comp.status || ev.status || {}).type) || {};
  const t = {};
  for (const c of comp.competitors || []) t[c.homeAway] = c;
  if (!t.home || !t.away) return null;
  const nm = (c) => (c.team && (c.team.shortDisplayName || c.team.name || c.team.displayName)) || "?";
  if (st.state === "pre") return null;
  const done = !!st.completed || st.state === "post";
  return { away: nm(t.away), home: nm(t.home), a: +t.away.score || 0, h: +t.home.score || 0,
           clock: done ? "Final" : clockText(key, st), live: !done };
}

const PTS = { "0": 0, "15": 1, "30": 2, "40": 3, "A": 4, "AD": 4, "ADV": 4 };
function points(x) {
  for (const k of ["points", "currentPoints", "gameScore", "currentGameScore", "point"]) {
    const v = x[k];
    if (v !== undefined && v !== null && v !== "") return typeof v === "object" ? String(v.displayValue ?? v.value ?? "") : String(v);
  }
  const ls = x.linescores || [];
  const last = ls[ls.length - 1];
  if (last && typeof last === "object") for (const k of ["points", "currentPoints", "gamePoints"]) if (last[k] !== undefined && last[k] !== null && last[k] !== "") return String(last[k]);
  return null;
}
function serving(x) {
  for (const k of ["possession", "serving", "isServing", "server", "serve"]) if (x[k] !== undefined && x[k] !== null) return !!x[k];
  return false;
}

function match(c) {
  const comps = c.competitors || [];
  if (comps.length !== 2) return null;
  const st = ((c.status || {}).type) || {};
  const played = comps.some((x) => (x.linescores || []).some((l) => +l.value > 0));
  if (st.state === "pre" && !played) return null;          // not started yet (a delay mid-match still shows the score)
  const delayed = /DELAY|SUSPEND|RAIN/i.test(`${st.name || ""} ${st.description || ""} ${st.detail || ""}`) && st.state !== "post";
  const name = (x) => { const a = x.athlete || {}; const n = String(a.displayName || a.fullName || "?").split(" "); return n[n.length - 1]; };
  const s = comps.map((x) => (x.linescores || []).map((l) => Math.round(+l.value || 0)));
  const sets = s[0].map((g, i) => [g, s[1][i] ?? 0]);
  const fin = ([a, b]) => Math.max(a, b) >= 6 && (Math.abs(a - b) >= 2 || Math.max(a, b) === 7);
  let done = 0;
  while (done < sets.length && fin(sets[done])) done++;
  const live = st.state === "in" || (delayed && played);
  let pts = null;
  const p = comps.map(points);
  if (live && p[0] !== null && p[1] !== null) {
    const tb = sets[done] && sets[done][0] === 6 && sets[done][1] === 6;
    pts = tb ? p : p.map((v) => (PTS[String(v).toUpperCase()] !== undefined ? (String(v).toUpperCase().startsWith("A") ? "AD" : String(v)) : null));
    if (pts.some((v) => v === null)) pts = null;
  }
  const sv = comps.map(serving);
  const srv = sv[0] && !sv[1] ? 0 : sv[1] && !sv[0] ? 1 : null;
  return { tennis: true, p1: true, n: comps.map(name), sets, pts, srv, done, live, delayed };
}

export async function handleScores(request, env, ctx, origins) {
  const origin = request.headers.get("Origin") || "";
  const cors = { "Access-Control-Allow-Origin": origins.includes(origin) ? origin : origins[0], Vary: "Origin",
                 "Access-Control-Allow-Methods": "GET, OPTIONS", "Cache-Control": "no-store" };
  if (request.method === "OPTIONS") return new Response(null, { headers: cors });
  const ids = (new URL(request.url).searchParams.get("ids") || "").split(",").map((x) => x.trim()).filter(Boolean).slice(0, 40);
  const want = {};
  for (const id of ids) {
    const parts = id.split(":");
    const key = parts[0] === "tennis" ? parts[1] : parts[0];
    if (!PATHS[key]) continue;
    (want[key] = want[key] || []).push(id);
  }
  const out = {};
  const debug = new URL(request.url).searchParams.has("debug");
  await Promise.all(Object.keys(want).map(async (key) => {
    let d;
    try { d = await board(key, ctx); } catch (e) { DBG[key] = `error ${String(e).slice(0, 80)}`; d = null; }
    if (debug && d) DBG[key + "_events"] = (d.events || []).map((e) => e.id).slice(0, 30).join(",");
    if (!d) return;
    const need = new Set(want[key]);
    for (const ev of d.events || []) {
      if (key === "atp" || key === "wta") {
        for (const g of ev.groupings || []) for (const c of g.competitions || []) {
          const id = `tennis:${key}:${c.id}`;
          if (need.has(id)) { const m = match(c); if (m) out[id] = m; }
        }
      } else {
        const id = `${key}:${ev.id}`;
        if (need.has(id)) { const t = team(ev, key); if (t) out[id] = t; }
      }
    }
  }));
  if (debug) out._debug = { ...DBG, want };
  return new Response(JSON.stringify(out), { headers: { ...cors, "Content-Type": "application/json" } });
}
