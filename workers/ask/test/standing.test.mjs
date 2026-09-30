import { test } from "node:test";
import assert from "node:assert/strict";
import { standing } from "../src/index.js";

test("standing: the exact math on our live picks (9/29: 'needs two goals to tie' when down one)", () => {
  const sc = { away: "Canucks", home: "Oilers", a: 5, h: 4, clock: "9:37 - 3rd", live: true };
  const pl = standing({ team: "Oilers", league: "nhl", market: "spread", line: -1.5, side: "home" }, sc);
  assert.match(pl, /down 4-5/);
  assert.match(pl, /finish ahead by 2\+ to cash -1\.5: a 3-goal swing from here; 1 goal just ties it/);
  const ml = standing({ team: "Oilers", league: "nhl", market: "ml", side: "home" }, sc);
  assert.match(ml, /1 goal ties it, 2 goals wins it/);
  const dog = standing({ team: "Blackhawks", league: "nhl", market: "spread", line: 1.5, side: "away" },
    { away: "Blackhawks", home: "Golden Knights", a: 1, h: 2, clock: "5:53 - 2nd", live: true });
  assert.match(dog, /covering \+1\.5 right now/);
  const lead = standing({ team: "Padres", league: "mlb", market: "ml", side: "home" }, { a: 0, h: 7, clock: "Bot 7th", live: true });
  assert.match(lead, /up 7-0 .* winning - hold on/);
});
