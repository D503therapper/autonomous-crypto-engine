// Offline tests for the Web Push routes (no network: fetch and KV are mocked). Run: node --test workers/ask/test/
import { test } from "node:test";
import assert from "node:assert/strict";
import { handlePush, vapidKeys, vapidJwt, unb64u, subHash, DASH_URL, WELCOME } from "../src/push.js";

const ORIGINS = ["https://d503therapper.github.io"];
const W = "https://d503-ask.example.workers.dev";
const APPLE = "https://web.push.apple.com/QFakeToken123";
const FCM = "https://fcm.googleapis.com/fcm/send/fake-android";

function memKV() {
  const m = new Map();
  return {
    m,
    async get(k, type) {
      const v = m.get(k);
      if (!v) return null;
      return type === "json" ? JSON.parse(v.value) : v.value;
    },
    async put(k, value, opts = {}) { m.set(k, { value, metadata: opts.metadata }); },
    async delete(k) { m.delete(k); },
    async list({ prefix = "", limit = 1000 } = {}) {
      const keys = [...m.keys()].filter((k) => k.startsWith(prefix)).sort().slice(0, limit)
        .map((name) => ({ name, metadata: m.get(name).metadata }));
      return { keys, list_complete: true };
    },
  };
}

// fetch mock: ntfy answers with `ntfy` messages, push services answer with status[endpoint] (default 201)
function mockFetch({ ntfy = [], status = {} } = {}) {
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    const u = String(url);
    calls.push({ url: u, init });
    if (u.startsWith("https://ntfy.sh/")) {
      const body = ntfy.map((x) => JSON.stringify({ event: "message", time: 1790000000, topic: "d503-live-7b1123", ...x })).join("\n");
      return new Response(body + "\n", { status: 200 });
    }
    return new Response("", { status: status[u] || 201 });
  };
  return calls;
}

async function call(env, method, path, { body, origin = ORIGINS[0], ua = "" } = {}) {
  const waits = [];
  const ctx = { waitUntil: (p) => waits.push(p) };
  const headers = { "Content-Type": "application/json", "User-Agent": ua };
  if (origin) headers.Origin = origin;
  const req = new Request(W + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const res = await handlePush(req, env, ctx, path.split("?")[0], ORIGINS);
  await Promise.all(waits);
  return { status: res.status, json: await res.json().catch(() => null), headers: res.headers };
}

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148";
const ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Mobile Safari/537.36";
const pushCalls = (calls) => calls.filter((c) => !c.url.startsWith("https://ntfy.sh/"));

test("VAPID JWT: header, claims and an ES256 signature that verifies", async () => {
  const kv = memKV();
  const keys = await vapidKeys(kv);
  assert.equal((await vapidKeys(kv)).pub, keys.pub, "made once, then read from KV");
  assert.equal(unb64u(keys.pub).length, 65);
  const now = Math.floor(Date.now() / 1000);
  const jwt = await vapidJwt(keys, APPLE, now);
  const [h, c, s] = jwt.split(".");
  const dec = (x) => JSON.parse(new TextDecoder().decode(unb64u(x)));
  assert.deepEqual(dec(h), { typ: "JWT", alg: "ES256" });
  const claims = dec(c);
  assert.equal(claims.aud, "https://web.push.apple.com");
  assert.ok(claims.exp > now && claims.exp - now <= 12 * 3600, "exp within 12h");
  assert.ok(claims.sub === DASH_URL || claims.sub.startsWith("mailto:"));
  const sig = unb64u(s);
  assert.equal(sig.length, 64, "raw r||s");
  const pub = await crypto.subtle.importKey("raw", unb64u(keys.pub), { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, pub, sig, new TextEncoder().encode(`${h}.${c}`));
  assert.ok(ok, "signature verifies");
  const bad = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, pub, sig, new TextEncoder().encode(`${h}.x${c}`));
  assert.ok(!bad);
  assert.equal(JSON.parse(new TextDecoder().decode(unb64u(jwt.split(".")[1]))).aud, "https://web.push.apple.com");
  const r = await call({ PUSH: kv }, "GET", "/vapid");
  assert.equal(r.json.key, keys.pub);
});

test("/push refuses an id that isn't on the ntfy topic", async () => {
  const kv = memKV();
  await kv.put(`wp:sub:${await subHash(APPLE)}`, JSON.stringify({ endpoint: APPLE }), { metadata: { e: APPLE } });
  const calls = mockFetch({ ntfy: [{ id: "realOne12345", title: "LIVE PLUS MONEY: Bears +150", message: "x" }] });
  const r = await call({ PUSH: kv }, "POST", "/push", { body: { ntfy_id: "fakeId99999", title: "spoofed" }, origin: "" });
  assert.equal(r.status, 404);
  assert.equal(pushCalls(calls).length, 0, "no phone got pinged");
  assert.equal(await kv.get("wp:latest"), null);
  assert.equal((await call({ PUSH: kv }, "POST", "/push", { body: { ntfy_id: "../x" }, origin: "" })).status, 400);
});

test("/push with a real id: title from ntfy, payload-less push to every phone, 410s cleaned up", async () => {
  const kv = memKV();
  for (const e of [APPLE, FCM]) await kv.put(`wp:sub:${await subHash(e)}`, JSON.stringify({ endpoint: e }), { metadata: { e, d: "x" } });
  const calls = mockFetch({ ntfy: [{ id: "older0000001", title: "old" },
    { id: "abcDEF123456", title: "LIVE PLUS MONEY: Bears +150", message: "Bears ML +150 — 14-10, Q3", click: DASH_URL }],
    status: { [FCM]: 410 } });
  const r = await call({ PUSH: kv }, "POST", "/push", { body: { ntfy_id: "abcDEF123456", title: "ignored" }, origin: "" });
  assert.equal(r.status, 202);
  const pushes = pushCalls(calls);
  assert.deepEqual(pushes.map((c) => c.url).sort(), [APPLE, FCM].sort());
  for (const p of pushes) {
    assert.equal(p.init.method, "POST");
    assert.equal(p.init.body, undefined, "payload-less");
    assert.match(p.init.headers.Authorization, /^vapid t=[\w-]+\.[\w-]+\.[\w-]+, k=[\w-]{87}$/);
    assert.equal(p.init.headers.TTL, "600");
    assert.equal(p.init.headers.Urgency, "high");
  }
  assert.equal(await kv.get(`wp:sub:${await subHash(FCM)}`), null, "410 -> deleted");
  assert.ok(await kv.get(`wp:sub:${await subHash(APPLE)}`), "the good one stays");
  const latest = await call({ PUSH: kv }, "GET", "/latest");
  assert.equal(latest.json.title, "LIVE PLUS MONEY: Bears +150");
  assert.equal(latest.json.url, DASH_URL);
  // the same id again: no second round of pushes
  const n = pushCalls(calls).length;
  assert.equal((await call({ PUSH: kv }, "POST", "/push", { body: { ntfy_id: "abcDEF123456" }, origin: "" })).json.already, true);
  assert.equal(pushCalls(calls).length, n);
  const st = await call({ PUSH: kv }, "GET", "/alerts-status");
  assert.equal(st.json.active, 1);
  assert.equal(st.json.events[0].event, "gone");
});

test("subscribe / unsubscribe (dashboard origin only)", async () => {
  const kv = memKV();
  mockFetch();
  const sub = { endpoint: APPLE, keys: { p256dh: "B".repeat(87), auth: "a".repeat(22) } };
  assert.equal((await call({ PUSH: kv }, "POST", "/subscribe", { body: sub, origin: "https://evil.example" })).status, 403);
  assert.equal((await call({ PUSH: kv }, "POST", "/subscribe", { body: { endpoint: "https://evil.example/x" } })).status, 400);
  const r = await call({ PUSH: kv }, "POST", "/subscribe", { body: sub, ua: IPHONE });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGINS[0]);
  const key = `wp:sub:${await subHash(APPLE)}`;
  assert.equal((await kv.get(key, "json")).endpoint, APPLE);
  assert.equal(kv.m.get(key).metadata.e, APPLE);
  assert.equal((await call({ PUSH: kv }, "POST", "/unsubscribe", { body: { endpoint: APPLE }, ua: IPHONE })).status, 200);
  assert.equal(await kv.get(key), null);
  assert.equal((await call({ PUSH: kv }, "GET", "/subscribe")).status, 405);
  // no PUSH namespace: falls back to the LOG one, under its own "wp:" keys
  const log = memKV();
  await call({ LOG: log }, "POST", "/subscribe", { body: sub });
  assert.ok([...log.m.keys()].every((k) => k.startsWith("wp:")));
});

test("welcome push: only the new phone, shown once via /latest?sub=, never twice", async () => {
  const kv = memKV();
  await kv.put(`wp:sub:${await subHash(FCM)}`, JSON.stringify({ endpoint: FCM }), { metadata: { e: FCM } });
  await kv.put("wp:latest", JSON.stringify({ id: "prev", title: "LIVE PLUS MONEY: old", body: "old" }));
  const calls = mockFetch();
  const r = await call({ PUSH: kv }, "POST", "/subscribe", { body: { endpoint: APPLE, keys: {} }, ua: IPHONE });
  assert.equal(r.json.welcome, true);
  const pushes = pushCalls(calls);
  assert.deepEqual(pushes.map((c) => c.url), [APPLE], "only the new subscription");
  assert.equal(pushes[0].init.body, undefined);
  const h = await subHash(APPLE);
  const w = await call({ PUSH: kv }, "GET", `/latest?sub=${h}`);
  assert.ok(WELCOME.some(([t, b]) => t === w.json.title && b === w.json.body), "one of the welcome lines");
  for (const [t, b] of WELCOME) assert.ok(!/real talk|chalk/i.test(t + b));
  assert.equal((await call({ PUSH: kv }, "GET", `/latest?sub=${h}`)).json.title, "LIVE PLUS MONEY: old", "welcome shows once");
  const again = await call({ PUSH: kv }, "POST", "/subscribe", { body: { endpoint: APPLE, keys: {} }, ua: IPHONE });
  assert.equal(again.json.welcome, false, "re-confirming on load: no second welcome");
  assert.equal(pushCalls(calls).length, 1);
});

test("the log + /alerts-status: counts, device, welcome status, no endpoints or keys", async () => {
  const kv = memKV();
  mockFetch({ status: { [FCM]: 403 } });
  await call({ PUSH: kv }, "POST", "/subscribe", { body: { endpoint: APPLE, keys: { auth: "secretAuth" } }, ua: IPHONE });
  await new Promise((r) => setTimeout(r, 3));
  await call({ PUSH: kv }, "POST", "/subscribe", { body: { endpoint: FCM, keys: { auth: "secretAuth" } }, ua: ANDROID });
  await new Promise((r) => setTimeout(r, 3));
  await call({ PUSH: kv }, "POST", "/unsubscribe", { body: { endpoint: APPLE }, ua: IPHONE });
  const st = await call({ PUSH: kv }, "GET", "/alerts-status", { origin: "" });
  assert.equal(st.status, 200);
  assert.equal(st.json.active, 1);
  assert.deepEqual(st.json.by_device, { Android: 1 });
  const ev = st.json.events;
  assert.deepEqual(ev.map((e) => e.event), ["unsubscribe", "subscribe", "subscribe"], "newest first");
  assert.equal(ev[1].device, "Android");
  assert.equal(ev[1].welcome_status, 403);
  assert.equal(ev[1].welcome, "not accepted");
  assert.equal(ev[2].device, "iPhone");
  assert.equal(ev[2].welcome_status, 201);
  assert.equal(ev[2].welcome, "accepted");
  assert.match(ev[2].at_pt, /PT$/);
  const text = JSON.stringify(st.json);
  assert.ok(!text.includes("push.apple.com") && !text.includes("googleapis") && !text.includes("secretAuth"));
  // a welcome the push service refused is dropped, so it can't pop up in place of a live bet later
  assert.equal(await kv.get(`wp:welcome:${await subHash(FCM)}`), null);
});
