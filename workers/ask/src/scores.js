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
  const live = st.state !== "post";                       // started (games on the board) and not over = live - ESPN
  //                                                           lags tennis and can still say "pre" mid-match (9/29: a
  //                                                           match read FINAL while it was being played)
  let pts = null;
  const p = comps.map(points);
  if (live && p[0] !== null && p[1] !== null) {
    const tb = sets[done] && sets[done][0] === 6 && sets[done][1] === 6;
    pts = tb ? p : p.map((v) => (PTS[String(v).toUpperCase()] !== undefined ? (String(v).toUpperCase().startsWith("A") ? "AD" : String(v)) : null));
    if (pts.some((v) => v === null)) pts = null;
  }
  const sv = comps.map(serving);
  const srv = sv[0] && !sv[1] ? 0 : sv[1] && !sv[0] ? 1 : null;
  // ESPN's points sit frozen (9/29: "0-15 sitting there forever") - the points only ever come from the book below
  return { tennis: true, p1: true, n: comps.map(name), sets, pts: null, espn_pts: pts, srv, done, live, delayed };
}

// 🎾 THE BOOK'S POINT-BY-POINT (BetRivers / Kambi in-play): every point, who's serving, games per set - seconds ahead
// of ESPN, which mostly has no points at all (the owner, 9/29: "15, 30, 40 ... accurate down to the second").
const KAMBI_TN = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/tennis/all/all/all/in-play.json?lang=en_US&market=US";
export const BOOK = { at: 0, n: 0, err: "" };             // (the hourly check reads these through ?debug)

async function kambiTennis(ctx) {
  const cache = caches.default, ck = "https://d503-cache/kambi-tennis-inplay";
  const hit = await cache.match(ck);
  if (hit) return hit.json();
  try {
    const r = await fetch(`${KAMBI_TN}&_=${Math.floor(Date.now() / 1000)}`, { headers: { Accept: "application/json",
      "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148" } });
    if (!r.ok) { BOOK.err = `HTTP ${r.status}`; return null; }
    const body = await r.text();
    ctx.waitUntil(cache.put(ck, new Response(body, { headers: { "Cache-Control": "max-age=1", "Content-Type": "application/json" } })));
    const d = JSON.parse(body);
    BOOK.at = Date.now(); BOOK.n = (d.events || []).length; BOOK.err = "";
    return d;
  } catch (e) {
    BOOK.err = String(e).slice(0, 80);
    return null;
  }
}

const toks = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
  .replace(/[^a-z\s-]/g, " ").split(/[\s-]+/).filter(Boolean);
function samePlayer(a, b) {                                // same last name, either name order ("Ma YeXin" = "Yexin Ma")
  const A = toks(a), B = toks(b);
  return !!(A.length && B.length && (B.includes(A[A.length - 1]) || A.includes(B[B.length - 1])));
}
const setOver = ([a, b]) => Math.max(a, b) >= 7 || (Math.max(a, b) >= 6 && Math.abs(a - b) >= 2);

// the book's live score for ESPN's match (p1 = ESPN's first player): {sets, pts, srv, done} or null - never a guess
export function bookScore(d, p1, p2, bo = 3) {
  for (const e of (d && d.events) || []) {
    const ev = e.event || {}, ld = e.liveData || {};
    const st = ((ld.statistics || {}).sets) || {}, h = st.home || [], a = st.away || [];
    if (!h.length || h.length !== a.length) continue;
    let homeP1;
    if (samePlayer(ev.homeName, p1) && samePlayer(ev.awayName, p2)) homeP1 = true;
    else if (samePlayer(ev.homeName, p2) && samePlayer(ev.awayName, p1)) homeP1 = false;
    else continue;
    let sets = h.map((x, i) => [+x, +a[i]]).filter(([x, y]) => x >= 0 && y >= 0);
    while (sets.length > 1 && sets[sets.length - 1][0] === 0 && sets[sets.length - 1][1] === 0 &&
           (!setOver(sets[sets.length - 2]) || (sets[sets.length - 2][0] === 0 && sets[sets.length - 2][1] === 0))) sets.pop();
    if (sets.length && setOver(sets[sets.length - 1]) && sets.length < bo) sets.push([0, 0]);
    const sw = (t) => (homeP1 ? [t[0], t[1]] : [t[1], t[0]]);
    const sc = ld.score || {};
    const pts = sc.home != null && sc.away != null ? sw([String(sc.home), String(sc.away)]) : null;
    const hs = st.homeServe;
    const srv = typeof hs === "boolean" ? (hs === homeP1 ? 0 : 1) : null;
    return { sets: sets.map(sw), pts, srv, done: Math.max(0, sets.length - 1) };
  }
  return null;
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
  const out = {}, full = {};
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
          if (need.has(id)) {
            const m = match(c);
            if (m) {
              out[id] = m;
              const nm = (x) => ((x || {}).athlete || {}).displayName || (x || {}).displayName || "";
              full[id] = (c.competitors || []).map(nm);
            }
          }
        }
      } else {
        const id = `${key}:${ev.id}`;
        if (need.has(id)) { const t = team(ev, key); if (t) out[id] = t; }
      }
    }
  }));
  const tn = Object.keys(full).filter((id) => out[id] && out[id].live);
  if (tn.length) {                                          // 🎾 the book's points + who's serving, when it's as far along
    const kd = await kambiTennis(ctx);
    const games = (x) => (x.sets || []).reduce((t, [a, b]) => t + a + b, 0);
    for (const id of tn) {
      const b = bookScore(kd, full[id][0], full[id][1]);
      if (b && games(b) >= games(out[id])) out[id] = { ...out[id], ...b, src: "book" };
    }
  }
  if (debug) out._debug = { ...DBG, want, book: BOOK };
  return new Response(JSON.stringify(out), { headers: { ...cors, "Content-Type": "application/json" } });
}
