// 🤔 GOT A QUESTION? - the AI version. The dashboard POSTs {q, history}; this adds the engine's data sheet and asks
// Claude, which answers in our voice from the engine's facts only. The API key never leaves Cloudflare.
import Anthropic from "@anthropic-ai/sdk";

const BRAIN_URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/brain.json";
const LIVE_URL = "https://raw.githubusercontent.com/D503therapper/autonomous-crypto-engine/live-data/live.json";
const ORIGINS = ["https://d503therapper.github.io"];
const PER_HOUR = 30;                     // questions per person per hour (a spammer can't burn the credits)

const SYSTEM = `You are THE D503 SPORTS ENGINE's question box. You run the engine and know it inside out.
Latency-sensitive: begin your visible answer immediately.

HOW YOU TALK
- Talk like the owner and his crew: casual, confident, a little trash talk, never corporate, never robotic, never repetitive.
- Their lingo (use it naturally, don't force every phrase): "tap in", "we gon' see", "we finna see", "I won't let y'all down",
  "teams always be coming back", "the line makers trippin'", "about to smack that ass" (a team about to beat someone bad),
  "cheeks clapped" (someone got beat bad), "complete ass" (a team that sucks), "trust the algorithm".
- Never say "chalk". Never call a big favorite "priced like it's close".
- Plain text only - no markdown, no asterisks, no # headings (the box shows raw text). Emojis are fine.
- Short: 2-6 sentences unless they ask for a breakdown. Plain words - no jargon. If you mention value, explain it the plain
  way ($100 examples: +164 means $100 wins $164, so they only need to win about 38 of 100 to break even).

WHAT YOU KNOW - ONLY the data sheet below (and the live plus money list in the question). Never make up a score, injury,
line, record or pick. If it isn't in the data sheet, say so in our voice ("my bad, the engine ain't got that one yet") and
say what you do know.

THE ENGINE'S RULES (explain them when asked)
- Picks only, paper picks. We don't place bets for anybody.
- The daily card: Lock of the Day (minus money only, -101 to -120 first, up to -150), Dog of the Day (plus money value),
  2-leg, 3-leg, 4-leg parlays (accuracy first). One-game days (Monday/Thursday night) get one Pick of the Day.
- Minus money = LOCK, plus money = VALUE. Leans and live plus money have their own records and are NEVER in our record.
- If we posted it, it counts. Every W and every L stays up - we don't hide nothing. Posted picks never change.
- No player props, ever ("we don't do no player props"). Over/unders only in sports where the study proved an edge.
- Injuries come first: a star who's questionable holds the game; a starter who's out means the engine goes by the book's line.
- "Every game's read" entries are the engine's lean on games that are NOT our picks - say so if you use one.
- Records: use the "records" block exactly as written - those are the numbers on the dashboard.
- The studies (underdogs + favorites, trends, rigged/fade-the-public, spread vs moneyline, self-check) tell what's been
  PROVEN on games the engine never saw. "Watch only" / not proven means it's info, not a bet - be straight about that.

Never give real-money betting advice beyond what the engine picked; if someone asks how much to bet, tell them to bet
what they can afford to lose - it's entertainment.`;

const hits = new Map();                  // best effort, per Cloudflare instance

// Only send the parts of the data sheet a question needs (the whole sheet costs ~2x). The core always goes: records,
// today's + tomorrow's board, recent results, what the studies proved. Games, splits, tennis and the detailed study
// tables ride along when the question (or the last few) points at them. Can't tell what it's about -> the whole sheet.
const SPORT = { nfl: /nfl|football/, ncaaf: /college football|ncaaf|cfb/, nba: /nba|basketball/, ncaab: /college (hoops|basketball)|ncaab|cbb/,
  mlb: /mlb|baseball/, nhl: /nhl|hockey/ };
const WORDS = (x) => String(x || "").toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length >= 4);

function trim(brain, text) {
  const t = text.toLowerCase();
  const core = {};
  for (const k of ["updated", "today", "tomorrow", "records", "board (today + tomorrow)", "recent graded picks"]) core[k] = brain[k];
  const st = brain.studies || {};
  const light = {};
  for (const [k, v] of Object.entries(st)) {
    if (k === "underdogs + favorites") {
      light[k] = Object.fromEntries(Object.entries(v || {}).map(([lg, x]) => [lg, {
        "proven dog spots": x["proven dog spots"], "trap dog spots (never taken)": x["trap dog spots (never taken)"],
        "favorites/dogs price check proven": x["favorites/dogs price check proven"] }]));
    } else light[k] = v;
  }
  core.studies = light;
  const extra = {};
  let matched = false;
  const reads = brain["every game's read (not our picks)"] || [];
  const games = reads.filter((g) => [g.away, g.home].some((n) => WORDS(n).some((w) => t.includes(w))));
  const sports = Object.keys(SPORT).filter((lg) => SPORT[lg].test(t));
  const slate = /tonight|today|tomorrow|slate|games|who wins|what'?s good|lean|best bet|value|spread|moneyline|\bover\b|\bunder\b|o\/u|total/.test(t);
  let pick = games;
  if (sports.length) pick = pick.concat(reads.filter((g) => sports.includes(g.league)));
  else if (slate && !games.length) pick = reads;
  if (pick.length) {
    extra["every game's read (not our picks)"] = [...new Set(pick)];
    matched = true;
  }
  const splits = brain["public betting splits (% of bets / % of money)"] || {};
  const ids = new Set((extra["every game's read (not our picks)"] || []).map((g) => g.id));
  if (/public|bets|money|fade|sharp|rigged|vegas|split|who'?s betting/.test(t)) {
    extra["public betting splits (% of bets / % of money)"] = ids.size
      ? Object.fromEntries(Object.entries(splits).filter(([id]) => ids.has(id))) : splits;
    matched = true;
  } else if (ids.size) {
    extra["public betting splits (% of bets / % of money)"] = Object.fromEntries(Object.entries(splits).filter(([id]) => ids.has(id)));
  }
  const tennis = brain["tennis reads"] || [];
  if (/tennis|atp|wta|\bset\b|serve/.test(t) || tennis.some((g) => [g.away, g.home].some((n) => WORDS(n).some((w) => t.includes(w))))) {
    extra["tennis reads"] = tennis;
    matched = true;
  }
  if (/study|studies|price check|favorite|underdog|\bdogs?\b|trap|proven|prove/.test(t)) {
    extra["underdog + favorite study, full tables"] = st["underdogs + favorites"];
    matched = true;
  }
  if (/record|how we doing|how are we|streak|lock|parlay|leg|pick|board|why|live|plus money/.test(t)) matched = true;
  return matched ? { core, extra } : { core: brain, extra: {} };
}

function reply(body, status, cors) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
}

async function getJson(url, ttl) {
  try {
    const r = await fetch(url, { cf: { cacheTtl: ttl, cacheEverything: true } });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": ORIGINS.includes(origin) ? origin : ORIGINS[0],
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      Vary: "Origin",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "POST") return reply({ error: "POST only" }, 405, cors);
    if (!ORIGINS.includes(origin)) return reply({ error: "not allowed" }, 403, cors);

    const ip = request.headers.get("CF-Connecting-IP") || "?";
    const hour = Math.floor(Date.now() / 3600000);
    const seen = hits.get(ip);
    const n = seen && seen.hour === hour ? seen.n + 1 : 1;
    hits.set(ip, { hour, n });
    if (n > PER_HOUR) {
      return reply({ answer: "Slow down, slow down 😂 you hit the limit for this hour. Come back in a lil bit." }, 200, cors);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return reply({ error: "bad request" }, 400, cors);
    }
    const q = String(body.q || "").trim().slice(0, 500);
    if (!q) return reply({ error: "empty question" }, 400, cors);
    const history = (Array.isArray(body.history) ? body.history : [])
      .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content.slice(0, 1500) }));
    while (history.length && history[0].role !== "user") history.shift();

    const [brain, live] = await Promise.all([getJson(BRAIN_URL, 60), getJson(LIVE_URL, 10)]);
    if (!brain) {
      return reply({ answer: "My bad — can't pull up the engine's data right this second. Try again in a minute. 🛠️" }, 200, cors);
    }

    const sheet = trim(brain, [q, ...history.filter((m) => m.role === "user").map((m) => m.content)].join(" \n "));
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const model = env.MODEL || "claude-haiku-4-5";
    // Haiku (the cheapest) answers straight up; the bigger models get adaptive thinking + the refusal fallback
    const extra = model.startsWith("claude-haiku")
      ? {}
      : {
          betas: ["server-side-fallback-2026-07-01"],
          fallbacks: "default",
          thinking: { type: "adaptive" },
          output_config: { effort: env.EFFORT || "low" },
        };
    try {
      const response = await client.beta.messages.create({
        model,
        max_tokens: 4000,
        ...extra,
        system: [
          { type: "text", text: SYSTEM },
          {
            type: "text",
            text: `THE ENGINE'S DATA SHEET (as of ${brain.updated}):\n${JSON.stringify(sheet.core)}`,
            cache_control: { type: "ephemeral" },
          },
          ...(Object.keys(sheet.extra).length
            ? [{ type: "text", text: `MORE FROM THE DATA SHEET (for this question):\n${JSON.stringify(sheet.extra)}`,
                 cache_control: { type: "ephemeral" } }]
            : []),
        ],
        messages: [
          ...history,
          {
            role: "user",
            content: `${q}\n\n[live plus money on the board right now: ${JSON.stringify((live && live.plays) || [])}]`,
          },
        ],
      });
      if (response.stop_reason === "refusal") {
        return reply({ answer: "Can't go there on that one. Ask me about the games, the picks, or the record. 🤝" }, 200, cors);
      }
      const answer = response.content
        .filter((b) => b.type === "text")
        .map((b) => b.text)
        .join("")
        .trim();
      return reply({ answer: answer || "My bad — blanked on that one. Ask me again. 🛠️" }, 200, cors);
    } catch (err) {
      if (err instanceof Anthropic.RateLimitError) {
        return reply({ answer: "Too many people asking at once 😅 give it a few seconds and try again." }, 200, cors);
      }
      if (err instanceof Anthropic.APIError) {
        console.log("anthropic error", err.status, err.message);
        return reply({ error: "ai unavailable" }, 502, cors);
      }
      console.log("error", String(err));
      return reply({ error: "ai unavailable" }, 502, cors);
    }
  },
};
