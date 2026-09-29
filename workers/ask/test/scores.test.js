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
