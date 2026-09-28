// 🔔 LIVE BET ALERTS - native Web Push for the dashboard (no app, no account, no secrets to set by hand).
//   GET  /vapid          the VAPID public key (the P-256 keypair is made on first use and kept in KV)
//   POST /subscribe      {endpoint, keys}  - a phone turns alerts on (dashboard origin only) + gets a welcome push
//   POST /unsubscribe    {endpoint}        - and off
//   POST /push           {ntfy_id}         - the engine: "this ntfy message just went out, ring the phones"
//   GET  /latest[?sub=h] what to show: that phone's pending welcome, else the newest verified alert (the SW asks)
//   GET  /alerts-status  counts + the last 20 joins/leaves (no endpoints, no keys) - for the owner's assistant
// /push trusts nothing in the request but the id: the Worker looks that id up on our ntfy topic and takes the title
// and message from ntfy itself. The pushes carry no payload (so no encryption); the phone asks /latest what it was.

export const NTFY_TOPIC = "d503-live-7b1123";
export const NTFY = `https://ntfy.sh/${NTFY_TOPIC}`;
export const DASH_URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/";
export const ROUTES = new Set(["/vapid", "/subscribe", "/unsubscribe", "/push", "/latest", "/alerts-status"]);
export const PREFIX = "wp:";                      // every key this writes (the question log is "q:...")
const SUB = `${PREFIX}sub:`;
const LOG = `${PREFIX}log:`;
const JWT_TTL = 12 * 3600;                        // VAPID tokens live 12h (the spec caps it at 24h)
const CONCURRENCY = 8;
// push services a subscription may point at (the Worker only ever POSTs to these)
const PUSH_HOSTS = [/\.push\.apple\.com$/, /^fcm\.googleapis\.com$/, /^android\.googleapis\.com$/,
  /^updates\.push\.services\.mozilla\.com$/, /^push\.services\.mozilla\.com$/, /\.notify\.windows\.com$/];

// the first thing a phone gets after tapping Allow - one at random, in our voice
export const WELCOME = [
  ["🔒 D503 SPORTS ENGINE", "You're locked in 🔥 When the algorithm spots a live bet, you'll know first. Let's go to work. 🧠"],
  ["🔔 D503 ALERTS: ON", "Tap in, you're on the list 🔥 Live plus money hits your phone the second the engine sees it. Trust the algorithm. 🧠"],
  ["🧠 THE ALGORITHM GOT YOU", "Alerts are live ✅ Next time the books get sleepy mid-game, you hear about it first. We finna see. 👀"],
  ["🔥 WELCOME TO THE CREW", "You're in 🔒 The engine watches every live game - when there's value, your phone buzzes. Let's eat. 🍽️"],
  ["📡 D503 LIVE ALERTS", "Locked and loaded 💯 No app, no account - just the live bets, straight to you. Go to work. 💪"],
  ["🔒 YOU'RE LOCKED IN", "The line makers trippin' and now you'll catch 'em in real time 📲 Stay ready. Trust the algorithm. 🧠"],
  ["⚡ D503 SPORTS ENGINE", "All set 🔥 When the algorithm triggers a live bet, this is where it lands. We ain't scared. Let's go. 🚀"],
  ["🐻 D503 IS WATCHING", "You're on 🔔 Every live game, every play - the moment there's plus money, you know first. Handle business. 💰"],
];

// ---- small helpers -------------------------------------------------------------------------------------------
export function b64u(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = "";
  for (const x of b) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function unb64u(s) {
  const t = String(s).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(t + "===".slice((t.length + 3) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

const enc = (x) => new TextEncoder().encode(x);

// a subscription's id: the endpoint's SHA-256, base64url (the service worker works out the same one for ?sub=)
export async function subHash(endpoint) {
  return b64u(await crypto.subtle.digest("SHA-256", enc(endpoint)));
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers: { ...headers, "Content-Type": "application/json",
    "Cache-Control": "no-store" } });
}

export function validEndpoint(endpoint) {
  try {
    const u = new URL(endpoint);
    return u.protocol === "https:" && endpoint.length <= 2048 && PUSH_HOSTS.some((re) => re.test(u.hostname));
  } catch {
    return false;
  }
}

export function device(ua) {
  const u = String(ua || "");
  if (/iPhone|iPod/.test(u)) return "iPhone";
  if (/iPad/.test(u)) return "iPad";
  if (/Android/.test(u)) return "Android";
  return "other";
}

function ptTime(d) {
  try {
    return d.toLocaleString("en-US", { timeZone: "America/Los_Angeles", month: "short", day: "numeric",
      hour: "numeric", minute: "2-digit" }) + " PT";
  } catch {
    return d.toISOString();
  }
}

// ---- VAPID ------------------------------------------------------------------------------------------------------
// {pub: base64url raw public key (65 bytes), jwk: the private key}. Made once, on first use, then read from KV.
export async function vapidKeys(kv) {
  const have = await kv.get(`${PREFIX}vapid`, "json");
  if (have && have.pub && have.jwk) return have;
  const pair = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const jwk = await crypto.subtle.exportKey("jwk", pair.privateKey);
  const pub = b64u(await crypto.subtle.exportKey("raw", pair.publicKey));
  const keys = { pub, jwk: { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y, d: jwk.d }, made: new Date().toISOString() };
  await kv.put(`${PREFIX}vapid`, JSON.stringify(keys));
  return keys;
}

// the VAPID JWT (RFC 8292): ES256 over header.claims, aud = the push service's origin
export async function vapidJwt(keys, endpoint, now = Math.floor(Date.now() / 1000)) {
  const header = b64u(enc(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const claims = b64u(enc(JSON.stringify({ aud: new URL(endpoint).origin, exp: now + JWT_TTL, sub: DASH_URL })));
  const key = await crypto.subtle.importKey("jwk", { ...keys.jwk, ext: true }, { name: "ECDSA", namedCurve: "P-256" },
    false, ["sign"]);
  // WebCrypto's ECDSA signature is already raw r||s (64 bytes) - exactly what JWS ES256 wants
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, enc(`${header}.${claims}`));
  return `${header}.${claims}.${b64u(sig)}`;
}

// ---- ntfy: the only source of truth for what an alert says ----------------------------------------------------
export async function ntfyMessages(since = "15m") {
  const r = await fetch(`${NTFY}/json?poll=1&since=${encodeURIComponent(since)}`, { headers: { Accept: "application/x-ndjson" } });
  if (!r.ok) throw new Error(`ntfy HTTP ${r.status}`);
  const out = [];
  for (const line of (await r.text()).split("\n")) {
    if (!line.trim()) continue;
    try {
      const m = JSON.parse(line);
      if (m && m.event === "message" && m.id) out.push(m);
    } catch { /* a bad line: skip it */ }
  }
  return out;
}

function toAlert(m) {
  const click = typeof m.click === "string" && m.click.startsWith(DASH_URL) ? m.click : DASH_URL;
  return { id: m.id, title: String(m.title || "D503 Sports Engine 🔥").slice(0, 120),
    body: String(m.message || "").slice(0, 400), url: click, time: m.time || Math.floor(Date.now() / 1000) };
}

// ---- the join/leave log (no endpoints, no keys) ---------------------------------------------------------------
async function logEvent(kv, ev) {
  const at = new Date();
  const e = { at: at.toISOString(), at_pt: ptTime(at), ...ev };
  const newestFirst = String(1e13 - at.getTime()).padStart(13, "0");      // KV lists keys in order: newest first
  await kv.put(`${LOG}${newestFirst}:${Math.random().toString(36).slice(2, 8)}`, JSON.stringify(e),
    { expirationTtl: 90 * 86400 }).catch(() => {});
}

// ---- sending --------------------------------------------------------------------------------------------------
// one payload-less push; returns the push service's status (0 = never got there). 404/410 = gone -> key deleted.
async function pushOne(kv, keys, sub, jwts, ttl) {
  try {
    const aud = new URL(sub.endpoint).origin;
    if (!jwts.has(aud)) jwts.set(aud, vapidJwt(keys, sub.endpoint));
    const r = await fetch(sub.endpoint, { method: "POST", headers: {
      Authorization: `vapid t=${await jwts.get(aud)}, k=${keys.pub}`, TTL: String(ttl), Urgency: "high",
      "Content-Length": "0" } });
    if (r.status === 404 || r.status === 410) {
      await kv.delete(sub.key);
      await logEvent(kv, { event: "gone", device: sub.device || "?", status: r.status });
    } else if (!r.ok) console.log("push failed", r.status, aud);
    return r.status;
  } catch (e) {
    console.log("push error", String(e).slice(0, 120));
    return 0;
  }
}

async function allSubs(kv) {
  const subs = [];
  let cursor;
  do {
    const page = await kv.list({ prefix: SUB, cursor });
    for (const k of page.keys) {
      let meta = k.metadata || {};
      if (!meta.e) {
        const v = (await kv.get(k.name, "json")) || {};
        meta = { e: v.endpoint, d: v.device };
      }
      if (meta.e) subs.push({ key: k.name, endpoint: meta.e, device: meta.d });
    }
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  return subs;
}

// a payload-less push to every phone, a few at a time
export async function sendAll(kv, keys, { ttl = 600 } = {}) {
  const subs = await allSubs(kv);
  const jwts = new Map();                         // one token per push service
  const stats = { sent: 0, gone: 0, failed: 0 };
  let i = 0;
  async function worker() {
    while (i < subs.length) {
      const st = await pushOne(kv, keys, subs[i++], jwts, ttl);
      if (st === 404 || st === 410) stats.gone++;
      else if (st >= 200 && st < 300) stats.sent++;
      else stats.failed++;
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, subs.length) }, worker));
  return stats;
}

// ---- the routes ---------------------------------------------------------------------------------------------
export async function handlePush(request, env, ctx, path, origins) {
  const origin = request.headers.get("Origin") || "";
  const cors = {
    "Access-Control-Allow-Origin": origins.includes(origin) ? origin : origins[0],
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
  if (request.method === "OPTIONS") return new Response(null, { headers: cors });
  const kv = env.PUSH || env.LOG;
  if (!kv) return json({ error: "alerts not set up" }, 503, cors);
  const want = ["/vapid", "/latest", "/alerts-status"].includes(path) ? "GET" : "POST";
  if (request.method !== want) return json({ error: `${want} only` }, 405, cors);
  const later = (p) => (ctx && ctx.waitUntil ? ctx.waitUntil(p) : p);

  if (path === "/vapid") return json({ key: (await vapidKeys(kv)).pub }, 200, cors);

  if (path === "/latest") {
    const h = new URL(request.url).searchParams.get("sub") || "";
    if (/^[A-Za-z0-9_-]{20,64}$/.test(h)) {       // this phone's welcome, shown once
      const w = await kv.get(`${PREFIX}welcome:${h}`, "json");
      if (w) {
        await kv.delete(`${PREFIX}welcome:${h}`);
        return json(w, 200, cors);
      }
    }
    // the newest ntfy message that /push verified. Each verified id has its own key, and a phone's edge has never
    // read that brand-new key, so it comes back fresh (a single "latest" key can be up to a minute stale elsewhere).
    try {
      const recent = (await ntfyMessages("15m")).reverse().slice(0, 5);
      for (const m of recent) {
        const hit = await kv.get(`${PREFIX}msg:${m.id}`, "json");
        if (hit) return json(hit, 200, cors);
      }
    } catch { /* ntfy down: fall back to the saved one */ }
    return json((await kv.get(`${PREFIX}latest`, "json")) || {}, 200, cors);
  }

  if (path === "/alerts-status") {
    const subs = await allSubs(kv);
    const by = {};
    for (const s of subs) by[s.device || "?"] = (by[s.device || "?"] || 0) + 1;
    const logs = (await kv.list({ prefix: LOG, limit: 20 })).keys.map((k) => k.name);
    const events = (await Promise.all(logs.map((k) => kv.get(k, "json")))).filter(Boolean);
    const latest = await kv.get(`${PREFIX}latest`, "json");
    return json({ active: subs.length, by_device: by, last_alert: latest ? { title: latest.title, time: latest.time } : null,
      events }, 200, cors);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "bad request" }, 400, cors);
  }

  if (path === "/subscribe" || path === "/unsubscribe") {
    if (!origins.includes(origin)) return json({ error: "not allowed" }, 403, cors);
    const endpoint = String((body && body.endpoint) || "");
    if (!validEndpoint(endpoint)) return json({ error: "bad subscription" }, 400, cors);
    const h = await subHash(endpoint);
    const key = `${SUB}${h}`;
    const dev = device(request.headers.get("User-Agent"));
    if (path === "/unsubscribe") {
      await kv.delete(key);
      later(logEvent(kv, { event: "unsubscribe", device: dev }));
      return json({ ok: true }, 200, cors);
    }
    const fresh = !(await kv.get(key));           // a phone re-confirming on load gets no second welcome
    const keys = (body && body.keys) || {};
    const sub = { endpoint, device: dev, keys: { p256dh: String(keys.p256dh || ""), auth: String(keys.auth || "") },
      at: new Date().toISOString() };
    await kv.put(key, JSON.stringify(sub), endpoint.length <= 900 ? { metadata: { e: endpoint, d: dev } } : {});
    if (!fresh) return json({ ok: true, welcome: false }, 200, cors);
    const [title, text] = WELCOME[Math.floor(Math.random() * WELCOME.length)];
    await kv.put(`${PREFIX}welcome:${h}`, JSON.stringify({ id: `welcome-${h.slice(0, 8)}`, title, body: text,
      url: DASH_URL, welcome: true }), { expirationTtl: 600 });
    later((async () => {
      const status = await pushOne(kv, await vapidKeys(kv), { key, endpoint, device: dev }, new Map(), 600);
      if (!(status >= 200 && status < 300)) await kv.delete(`${PREFIX}welcome:${h}`);   // never shown in place of a live bet
      await logEvent(kv, { event: "subscribe", device: dev, welcome_status: status,
        welcome: status >= 200 && status < 300 ? "accepted" : "not accepted" });
    })());
    return json({ ok: true, welcome: true }, 200, cors);
  }

  // POST /push {ntfy_id}
  const id = String((body && body.ntfy_id) || "");
  if (!/^[A-Za-z0-9]{6,32}$/.test(id)) return json({ error: "bad ntfy_id" }, 400, cors);
  let msgs;
  try {
    msgs = await ntfyMessages("15m");
  } catch {
    return json({ error: "ntfy unreachable" }, 502, cors);
  }
  const m = msgs.find((x) => x.id === id);
  if (!m) return json({ error: "no such message on the topic" }, 404, cors);
  if (await kv.get(`${PREFIX}msg:${id}`)) return json({ ok: true, already: true }, 200, cors);   // no replays
  const alert = toAlert(m);
  await kv.put(`${PREFIX}msg:${id}`, JSON.stringify(alert), { expirationTtl: 86400 });
  await kv.put(`${PREFIX}latest`, JSON.stringify(alert));
  const keys = await vapidKeys(kv);
  const job = sendAll(kv, keys).then((s) => console.log("pushed", id, JSON.stringify(s)));
  if (ctx && ctx.waitUntil) ctx.waitUntil(job);
  else await job;
  return json({ ok: true, id }, 202, cors);
}
