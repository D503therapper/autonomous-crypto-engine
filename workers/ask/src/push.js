// 🔔 LIVE BET ALERTS - native Web Push for the dashboard (no app, no account, no secrets to set by hand).
//   GET  /vapid          the VAPID public key (the P-256 keypair is made on first use and kept in KV)
//   POST /subscribe      {endpoint, keys}  - a phone turns alerts on (dashboard origin only) + gets a welcome push
//   POST /unsubscribe    {endpoint}        - and off
//   POST /push           {ntfy_id}         - the engine: "this ntfy message just went out, ring the phones"
//   GET  /latest[?sub=h] what to show: that phone's pending welcome, else the newest verified alert (the SW asks)
//   GET  /alerts-status  counts + the last 20 joins/leaves (no endpoints, no keys) - for the owner's assistant
// /push trusts nothing in the request but the engine's key (or an id it looks up on our ntfy topic itself).
// Each push carries its own alert, encrypted for that phone (RFC 8291) - 9/29: a payload-less push made the phone ask
// /latest, whose one "latest" key can read a minute stale at the phone's edge, so a new bet rang as the one before it.
// /latest stays only for a phone whose push arrives without the text, and then only an alert under 10 minutes old.

export const NTFY_TOPIC = "d503-live-7b1123";
export const NTFY = `https://ntfy.sh/${NTFY_TOPIC}`;
export const DASH_URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/";
export const ROUTES = new Set(["/vapid", "/subscribe", "/unsubscribe", "/push", "/latest", "/alerts-status"]);
export const PREFIX = "wp:";                      // every key this writes (the question log is "q:...")
const SUB = `${PREFIX}sub:`;
const LOG = `${PREFIX}log:`;
const JWT_TTL = 12 * 3600;                        // VAPID tokens live 12h (the spec caps it at 24h)
const CONCURRENCY = 8;
const LATEST_MAX_S = 600;                      // /latest: only an alert this fresh (the push TTL is 10 min too)
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

// ---- the push's own text, encrypted for one phone (RFC 8291, aes128gcm) --------------------------------------
async function hkdf(salt, ikm, info, len) {
  const k = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info }, k, len * 8));
}

const cat = (...xs) => {
  const out = new Uint8Array(xs.reduce((n, x) => n + x.length, 0));
  let i = 0;
  for (const x of xs) { out.set(x, i); i += x.length; }
  return out;
};

export async function encryptPayload(p256dh, auth, text, { salt, pair } = {}) {
  const ua = unb64u(p256dh), secret = unb64u(auth);
  if (ua.length !== 65 || secret.length < 16) throw new Error("bad phone keys");
  pair = pair || await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const as = new Uint8Array(await crypto.subtle.exportKey("raw", pair.publicKey));
  const uaKey = await crypto.subtle.importKey("raw", ua, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: uaKey }, pair.privateKey, 256));
  const ikm = await hkdf(secret, shared, cat(enc("WebPush: info\0"), ua, as), 32);
  salt = salt || crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, enc("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, enc("Content-Encoding: nonce\0"), 12);
  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, cat(enc(text), new Uint8Array([2]))));
  const head = new Uint8Array(21);
  head.set(salt, 0);
  new DataView(head.buffer).setUint32(16, 4096);
  head[20] = as.length;
  return cat(head, as, ct);
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
async function pushOne(kv, keys, sub, jwts, ttl, alert) {
  try {
    const aud = new URL(sub.endpoint).origin;
    if (!jwts.has(aud)) jwts.set(aud, vapidJwt(keys, sub.endpoint));
    const headers = { Authorization: `vapid t=${await jwts.get(aud)}, k=${keys.pub}`, TTL: String(ttl), Urgency: "high" };
    let body = null;
    if (alert && sub.p256dh && sub.auth) {                   // the alert rides in the push itself (never a lookup)
      try {
        body = await encryptPayload(sub.p256dh, sub.auth, JSON.stringify(alert));
        headers["Content-Encoding"] = "aes128gcm";
        headers["Content-Type"] = "application/octet-stream";
      } catch { body = null; }                               // (bad keys on file: the old way, the phone asks /latest)
    }
    if (!body) headers["Content-Length"] = "0";
    const r = await fetch(sub.endpoint, body ? { method: "POST", headers, body } : { method: "POST", headers });
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
      if (!meta.e || !meta.p) {                               // (older phones: the keys live in the value)
        const v = (await kv.get(k.name, "json")) || {};
        meta = { e: v.endpoint, d: v.device, p: (v.keys || {}).p256dh, a: (v.keys || {}).auth };
      }
      if (meta.e) subs.push({ key: k.name, endpoint: meta.e, device: meta.d, p256dh: meta.p, auth: meta.a });
    }
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  return subs;
}

// a payload-less push to every phone, a few at a time
export async function sendAll(kv, keys, { ttl = 600, alert = null } = {}) {
  const subs = await allSubs(kv);
  const jwts = new Map();                         // one token per push service
  const stats = { sent: 0, gone: 0, failed: 0 };
  let i = 0;
  async function worker() {
    while (i < subs.length) {
      const st = await pushOne(kv, keys, subs[i++], jwts, ttl, alert);
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
    let best = (await kv.get(`${PREFIX}latest`, "json")) || {};   // (alerts straight from the engine land here)
    try {
      const recent = (await ntfyMessages("15m")).reverse().slice(0, 5);
      for (const m of recent) {
        const hit = await kv.get(`${PREFIX}msg:${m.id}`, "json");
        if (hit && (hit.time || 0) > (best.time || 0)) { best = hit; break; }
      }
    } catch { /* ntfy unreachable from here: the saved one */ }
    if (!best.time || Date.now() / 1000 - best.time > LATEST_MAX_S) best = {};   // never an old bet as a new one
    return json(best, 200, cors);
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
    const meta = { e: endpoint, d: dev, p: sub.keys.p256dh, a: sub.keys.auth };   // (metadata caps at 1024 bytes)
    await kv.put(key, JSON.stringify(sub), JSON.stringify(meta).length <= 1000 ? { metadata: meta } : {});
    if (!fresh) return json({ ok: true, welcome: false }, 200, cors);
    const [title, text] = WELCOME[Math.floor(Math.random() * WELCOME.length)];
    await kv.put(`${PREFIX}welcome:${h}`, JSON.stringify({ id: `welcome-${h.slice(0, 8)}`, title, body: text,
      url: DASH_URL, welcome: true }), { expirationTtl: 600 });
    later((async () => {
      const status = await pushOne(kv, await vapidKeys(kv), { key, endpoint, device: dev, p256dh: sub.keys.p256dh, auth: sub.keys.auth },
        new Map(), 600, { id: `welcome-${h.slice(0, 8)}`, title, body: text, url: DASH_URL, welcome: true });
      if (!(status >= 200 && status < 300)) await kv.delete(`${PREFIX}welcome:${h}`);   // never shown in place of a live bet
      await logEvent(kv, { event: "subscribe", device: dev, welcome_status: status,
        welcome: status >= 200 && status < 300 ? "accepted" : "not accepted" });
    })());
    return json({ ok: true, welcome: true }, 200, cors);
  }

  // POST /push {key, title, body}: straight from the engine (its key proves it) - no ntfy lookup, which Cloudflare can
  // be blocked from (a live bet alert died that way, 9/28). Or the old way, POST /push {ntfy_id}: checked on the topic.
  let alert;
  if (body && body.key && env && env.PUSH_KEY && body.key === env.PUSH_KEY) {
    const id = `d${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    alert = { id, title: String(body.title || "D503 Sports Engine 🔥").slice(0, 120), body: String(body.body || "").slice(0, 400),
      url: DASH_URL, time: Math.floor(Date.now() / 1000) };
    if (body.dry) return json({ ok: true, dry: true }, 200, cors);
  } else {
    const id = String((body && body.ntfy_id) || "");
    if (!/^[A-Za-z0-9]{6,32}$/.test(id)) return json({ error: "bad ntfy_id" }, 400, cors);
    let msgs;
    try {
      msgs = await ntfyMessages("15m");
    } catch {
      await logEvent(kv, { event: "alert failed", device: "ntfy unreachable from Cloudflare" });
      return json({ error: "ntfy unreachable" }, 502, cors);
    }
    const m = msgs.find((x) => x.id === id);
    if (!m) return json({ error: "no such message on the topic" }, 404, cors);
    if (await kv.get(`${PREFIX}msg:${id}`)) return json({ ok: true, already: true }, 200, cors);   // no replays
    alert = toAlert(m);
  }
  const id = alert.id;
  await kv.put(`${PREFIX}msg:${id}`, JSON.stringify(alert), { expirationTtl: 86400 });
  await kv.put(`${PREFIX}latest`, JSON.stringify(alert));
  const keys = await vapidKeys(kv);
  const job = sendAll(kv, keys, { alert }).then(async (s) => {         // every alert sent goes in the log (who got it, who didn't)
    console.log("pushed", id, JSON.stringify(s));
    await logEvent(kv, { event: "alert", device: String(alert.title || "").slice(0, 60), sent: s.sent, gone: s.gone, failed: s.failed });
  });
  if (ctx && ctx.waitUntil) ctx.waitUntil(job);
  else await job;
  return json({ ok: true, id }, 202, cors);
}
