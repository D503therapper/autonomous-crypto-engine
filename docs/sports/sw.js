// 🔔 D503 live bet alerts - written by sports_dashboard.py
const API = "https://d503-ask.issatruestoryofficial.workers.dev";
const DASH = "https://d503therapper.github.io/autonomous-crypto-engine/sports/";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
async function myHash() {           // the Worker keys this phone by the SHA-256 of its endpoint (for its welcome)
  try {
    const s = await self.registration.pushManager.getSubscription();
    if (!s) return "";
    const d = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s.endpoint)));
    let b = "";
    for (const x of d) b += String.fromCharCode(x);
    return btoa(b).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  } catch (e) {
    return "";
  }
}
async function alertNow(e) {
  let m = {};
  try { m = (e && e.data && e.data.json()) || {}; } catch (x) { m = {}; }   // the alert rides in the push itself
  if (!m.title) try {                                     // (an old-style empty push: ask the Worker - it only answers
    if (!API) throw new Error("no worker");               // with an alert under 10 minutes old)
    const ctl = new AbortController();
    const to = setTimeout(() => ctl.abort(), 6000);
    const h = await myHash();
    const r = await fetch(API + "/latest" + (h ? "?sub=" + h : ""), { cache: "no-store", signal: ctl.signal });
    clearTimeout(to);
    if (r.ok) m = await r.json();
  } catch (e) { /* the fallback below still shows */ }
  return self.registration.showNotification(m.title || "🔥 D503 LIVE BET", {
    body: m.body || "The algorithm just triggered a live bet. Tap to see it. 📡",
    tag: m.id || "d503-live",
    renotify: !m.id,                                      // the same alert twice (a phone signed up twice): the 2nd
    //                                                       quietly replaces the 1st - never two rings (the owner, 9/30)
    icon: "icon-512.png?v=8",
    badge: "icon-512.png?v=8",
    data: { url: m.url && m.url.indexOf(DASH) === 0 ? m.url : DASH },
  });
}
self.addEventListener("push", (e) => e.waitUntil(alertNow(e)));
self.addEventListener("pushsubscriptionchange", (e) => e.waitUntil((async () => {   // the phone swapped its sign-up:
  const old = e.oldSubscription;                          // drop the old one so alerts don't come in twice
  if (old && API) await fetch(API + "/unsubscribe", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint: old.endpoint }) }).catch(() => {});
  const s = e.newSubscription;
  if (s && API) await fetch(API + "/subscribe", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(s.toJSON()) }).catch(() => {});
})()));
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || DASH;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    for (const c of cs) if (c.url.indexOf(DASH) === 0 && "focus" in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});
