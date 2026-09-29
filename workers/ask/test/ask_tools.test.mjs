import { test } from "node:test";
import assert from "node:assert/strict";
import { espnScoreboard } from "../src/index.js";

// 9/29: the question box couldn't see a live tennis match - its ESPN tool used the address ESPN blocks for Cloudflare,
// and read tennis one level too high (no matches, no set scores).
test("ask tool: ESPN tennis scoreboard - web door first, matches + set scores, next day's board too", async () => {
  const WTA = { events: [{ name: "Beijing", groupings: [{ competitions: [{ id: "186212", date: "2026-09-29T05:00Z",
    status: { type: { detail: "2nd Set" } }, competitors: [
      { homeAway: "home", athlete: { displayName: "Elvina Kalieva" }, linescores: [{ value: 7 }, { value: 2 }] },
      { homeAway: "away", athlete: { displayName: "Han Shi" }, linescores: [{ value: 6 }, { value: 2 }] }] }] }] }] };
  const asked = [];
  globalThis.fetch = async (u) => {
    asked.push(u);
    if (u.startsWith("https://site.api.espn.com")) return { ok: false, status: 403 };
    return { ok: true, json: async () => WTA };
  };
  const out = await espnScoreboard({ league: "wta", date: "2026-09-28", team: "Han Shi" });
  assert.ok(asked[0].startsWith("https://site.web.api.espn.com"));
  assert.ok(asked.some((u) => u.includes("dates=20260929")));            // Asia's matches: the next day's board
  assert.equal(out.length, 1);                                            // (the same match on both boards: once)
  assert.match(out[0].game, /Elvina Kalieva vs Han Shi/);
  assert.deepEqual(out[0].teams.map((t) => t.score), ["7-2", "6-2"]);
});
