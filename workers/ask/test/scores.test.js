import { test } from "node:test";
import assert from "node:assert/strict";
import { handleScores } from "../src/scores.js";

const NFL = { events: [{ id: "401872963", competitions: [{ status: { type: { state: "in", shortDetail: "8:42 - 3rd" } },
  competitors: [{ homeAway: "home", score: "17", team: { shortDisplayName: "Bears" } }, { homeAway: "away", score: "10", team: { shortDisplayName: "Eagles" } }] }] }] };
const ATP = { events: [{ groupings: [{ competitions: [{ id: "186239", status: { type: { state: "in" } }, competitors: [
  { athlete: { displayName: "Adolfo Daniel Vallejo" }, linescores: [{ value: 4 }, { value: 2 }], points: "15" },
  { athlete: { displayName: "Jaime Faria" }, linescores: [{ value: 6 }, { value: 3 }], points: "30", possession: true }] }] }] }] };

test("scores: team score + clock, tennis scoreboard from player 1's side", async () => {
  globalThis.caches = { default: { match: async () => null, put: async () => {} } };
  globalThis.fetch = async (u) => ({ ok: true, text: async () => JSON.stringify(u.includes("tennis/atp") ? ATP : NFL) });
  const req = new Request("https://x.workers.dev/scores?ids=nfl:401872963,tennis:atp:186239,nfl:1", { headers: { Origin: "https://d503therapper.github.io" } });
  const r = await handleScores(req, {}, { waitUntil() {} }, ["https://d503therapper.github.io"]);
  const d = await r.json();
  assert.deepEqual(d["nfl:401872963"], { away: "Eagles", home: "Bears", a: 10, h: 17, clock: "8:42 - 3rd", live: true });
  const t = d["tennis:atp:186239"];
  assert.deepEqual(t.n, ["Vallejo", "Faria"]);
  assert.deepEqual(t.sets, [[4, 6], [2, 3]]);
  assert.deepEqual(t.pts, ["15", "30"]);
  assert.equal(t.srv, 1); assert.equal(t.done, 1); assert.equal(t.live, true);
  assert.equal(d["nfl:1"], undefined);
});

test("scores: a rain delay mid-match keeps the score up", async () => {
  const DLY = { events: [{ groupings: [{ competitions: [{ id: "7", status: { type: { state: "pre", name: "STATUS_DELAYED", detail: "Rain Delay" } }, competitors: [
    { athlete: { displayName: "Rinky Hijikata" }, linescores: [{ value: 6 }, { value: 2 }] },
    { athlete: { displayName: "Some Guy" }, linescores: [{ value: 3 }, { value: 1 }] }] }] }] }] };
  globalThis.caches = { default: { match: async () => null, put: async () => {} } };
  globalThis.fetch = async () => ({ ok: true, status: 200, text: async () => JSON.stringify(DLY) });
  const r = await handleScores(new Request("https://x.workers.dev/scores?ids=tennis:atp:7"), {}, { waitUntil() {} }, ["https://d503therapper.github.io"]);
  const t = (await r.json())["tennis:atp:7"];
  assert.equal(t.delayed, true); assert.equal(t.live, true); assert.deepEqual(t.sets, [[6, 3], [2, 1]]);
});

test("scores: a match on the NEXT day's scoreboard (Asia) is still found", async () => {
  const today = { events: [] };
  const tmr = { events: [{ groupings: [{ competitions: [{ id: "186238", status: { type: { state: "in" } }, competitors: [
    { athlete: { displayName: "Rinky Hijikata" }, linescores: [{ value: 3 }] },
    { athlete: { displayName: "Stefanos Tsitsipas" }, linescores: [{ value: 2 }] }] }] }] }] };
  globalThis.caches = { default: { match: async () => null, put: async () => {} } };
  globalThis.fetch = async (u) => ({ ok: true, status: 200, text: async () => JSON.stringify(u.includes("dates=") ? tmr : today) });
  const r = await handleScores(new Request("https://x.workers.dev/scores?ids=tennis:atp:186238"), {}, { waitUntil() {} }, ["https://d503therapper.github.io"]);
  const t = (await r.json())["tennis:atp:186238"];
  assert.ok(t && t.live); assert.deepEqual(t.sets, [[3, 2]]);
});

test("scores: hockey's break between periods says intermission", async () => {
  const { clockText } = await import("../src/scores.js");
  assert.equal(clockText("nhl", { shortDetail: "End of 1st" }), "1st Intermission");
  assert.equal(clockText("nhl", { shortDetail: "End of 2nd" }), "2nd Intermission");
  assert.equal(clockText("nhl", { shortDetail: "End of 3rd" }), "End of 3rd");
  assert.equal(clockText("nhl", { shortDetail: "6:12 - 2nd" }), "6:12 - 2nd");
  assert.equal(clockText("nfl", { shortDetail: "Halftime" }), "Halftime");
  assert.equal(clockText("nfl", { shortDetail: "End of 1st" }), "End of 1st");
});

test("scores: a tennis match ESPN still calls 'pre' after games are played is live, never final", async () => {
  const { handleScores } = await import("../src/scores.js");
  const LAG = { events: [{ groupings: [{ competitions: [{ id: "9", status: { type: { state: "pre", name: "STATUS_SCHEDULED" } }, competitors: [
    { athlete: { displayName: "Tommy Paul" }, linescores: [{ value: 2 }] },
    { athlete: { displayName: "Alejandro Tabilo" }, linescores: [{ value: 1 }] }] }] }] }] };
  globalThis.caches = { default: { match: async () => null, put: async () => {} } };
  globalThis.fetch = async () => ({ ok: true, text: async () => JSON.stringify(LAG) });
  const req = new Request("https://x.workers.dev/scores?ids=tennis:atp:9", { headers: { Origin: "https://d503therapper.github.io" } });
  const d = await (await handleScores(req, {}, { waitUntil() {} }, ["https://d503therapper.github.io"])).json();
  assert.equal(d["tennis:atp:9"].live, true);
});
