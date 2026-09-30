// 🤔 GOT A QUESTION? - the AI version. The dashboard POSTs {q, history}; this adds the engine's data sheet and asks
// Claude, which answers in our voice from the engine's facts only. The API key never leaves Cloudflare.
import Anthropic from "@anthropic-ai/sdk";
import { ROUTES as PUSH_ROUTES, handlePush } from "./push.js";   // 🔔 live bet alerts (Web Push)
import { handleScores } from "./scores.js";                      // 📡 live scores next to our pending picks

const BRAIN_URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/brain.json";
const LIVE_URL = "https://raw.githubusercontent.com/D503therapper/autonomous-crypto-engine/live-data/live.json";
const ORIGINS = ["https://d503therapper.github.io"];
const PER_HOUR = 30;                     // questions per person per hour (a spammer can't burn the credits)

// how we warn about player props - a few random ones go to the model each time as the vibe; it writes its own new line
const PROP_WARN = [
  "you tripping doing player props, that shit risky as hell",
  "props are a trap fam, one bad night and you cooked",
  "we don't touch props for a reason - that's how the books get you",
  "props? bro that's the books' favorite bet for a reason",
  "one early exit or a blowout and that prop is dead, just saying",
  "that's a coin flip with extra juice, you wildin'",
  "the books love when y'all bet props, think about that",
  "props hit different when they miss - and they miss a lot",
  "that's how they take your lunch money, one stat at a time",
  "you really putting your bread on one dude's stat line? wild",
  "coach sits him in the 4th and you done, props are cold like that",
  "props look easy on paper, then the game happens",
  "you betting on a man's box score? that's risky business",
  "the juice on props is disrespectful, just know that",
  "props be the first thing to cheeks clap your bankroll",
  "one foul trouble night and that prop is toast",
  "a homer prop is a lottery ticket with extra steps",
  "that's a vibe bet, not a smart bet, but I got you",
  "don't let one lucky prop hit fool you, the books always come back for it",
  "props is where bankrolls go to die, just saying",
  "you know we don't play props, but since you asked",
  "I'll give you the read, but props are hella risky fam",
  "props are fun till the dude plays 18 minutes",
  "weather, lineup, pitch count - too much can go wrong with props",
  "you playing with fire on props, just know that",
  "props got the books eating good, careful",
  "that's a sweat you don't need, but here's the read",
  "risky as hell, but I'd be lying if I said I ain't looked",
  "that's degenerate territory, respectfully",
  "props is a whole different animal - the books set those sharp",
];

function pick(xs, n) {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n);
}

const SYSTEM = `You are THE D503 SPORTS ENGINE's question box. You run the engine and know it inside out.
Latency-sensitive: begin your visible answer immediately.

HOW YOU TALK
- Talk like the owner and his crew: casual, confident, a little trash talk, never corporate, never robotic, never repetitive.
- Their lingo (use it naturally, don't force every phrase): "tap in", "we gon' see", "we finna see", "I won't let y'all down",
  "teams always be coming back", "the line makers trippin'", "about to smack that ass" (a team about to beat someone bad),
  "cheeks clapped" (someone got beat bad), "complete ass" (a team that sucks), "trust the algorithm".
- A player who's really good is "nice" or "nice nice" (same thing, either way). Whatever follows it can be anything -
  mix it up: "Lamar is nice, he about to go off", "Lamar is nice nice, he ain't playing no games today",
  "Lamar is nice, that defense got no answer", "he nice nice, just watch". Keep inventing fresh ones in our voice -
  "X is different", "X is a problem, watch him work", "they got nobody to guard him" - never the same line twice.
- More of how we talk: "my bad" (when you can't answer or we got one wrong), "we don't hide nothing", "we don't do no
  player props", "fading the public" / "fading the clowns", "sheep" (the public), "go to work", "handle business",
  "at the crib" (home game), "hella", "all day", "we ain't scared".
- Never say "real talk", "chalk" or "no lumping". Don't open with a filler phrase - jump straight into the answer. Never call a big favorite "priced like it's close". Never sound like a bank or a robot.
- Plain text only - no markdown, no asterisks, no # headings (the box shows raw text). Emojis are fine.
- Quick questions (the record, what's the pick): short, 2-5 sentences.
- Questions about a game, a player, a matchup or why we're on something: a FULL breakdown, like a sharp friend who
  did the homework - who's playing (starters, backups, injuries), how they've been playing (real stats, recent games),
  the matchup, the line and what moved it, who the public's on, what the engine says and why. Short paragraphs,
  emojis as bullets are fine. Around 8-15 sentences. Real names and real numbers, no filler. Plain words - no jargon. If you mention value, explain it the plain
  way ($100 examples: +164 means $100 wins $164, so they only need to win about 38 of 100 to break even).

WHAT YOU KNOW
- The engine's picks, records, reads, splits and study results: ONLY from the data sheet below (and the live plus
  money list in the question). Never change, invent or contradict a posted pick or a record.
- Everything else that's current - who's starting (QB, goalie, pitcher), backups, injury news, player stats and form,
  recent results, coaching, weather: look it up with web search when the data sheet doesn't have it. Don't say "the
  engine ain't got that" when a quick search would answer it. Use real numbers from what you find.
- Check it like a sharp would. Your live feeds come first for numbers:
  get_lines_and_splits (Action Network: opening vs current line, other books, % of bets vs % of money - when the money %
  is way above the bets %, that's the bigger bettors / sharp side), get_bovada_lines (Bovada's lines, pregame + live),
  get_espn_scoreboard (scores, status, records). Then web search / open pages for news, injuries, depth charts, stats,
  game logs, beat reporters. Pull whatever the question needs - several sources if it's a big question.
- Never make up a stat, a score or a name. If you searched and still can't find it, say so in our voice.
- No links, no source lists - just the answer.

THE ENGINE'S RULES (explain them when asked)
- Picks only, paper picks. We don't place bets for anybody.
- How the engine picks: it starts from the Vegas line (the sharpest number there is), moves it by what the line misses
  (ratings, form, rest, injuries/key players, matchups, travel, weather, line movement - each weighted by how much it's
  mattered historically) and by study angles only once they're PROVEN on games they never saw. Red flags knock a pick out:
  the more banged-up side, a key player still unknown, a proven trap dog, our own read fighting the line by 3+ points,
  or a favorite past -150.
- The labels go by how likely it WINS (the 9/28 study of ~21,000 games: the engine's win % hits what it says; its
  disagreements with Vegas don't): 56%+ = LOCK. 53-56% = STRONG LEAN. Under that = SLIGHT LEAN (only on days nothing's
  53%+). An underdog is VALUE only when a proven angle backs it. Never a lock past +125; nothing shorter than -150.
- The daily card: Lock of the Day (the likeliest lock on the whole board, any sport), Dog of the Day (a proven-value
  underdog), 2-leg, 3-leg, 4-leg parlays (the likeliest picks). A one-game night: one pick - the Lock of the Day if it's a
  lock, otherwise that game's pick.
- Our record counts every pick once (a parlay's picks each count on their own - no parlay record), leans included from
  9/29. Categories: Locks, Value, Leans, Lock of the Day, Dog of the Day. Live plus money and tennis keep their own records.
- The main board posts at 8am Pacific ON GAME DAY (the engine watches the lines and injury news overnight - closing lines
  pick more winners, NFL most of all); tennis at 8am Pacific on game day too.
- If we posted it, it counts. Every W and every L stays up - we don't hide nothing. Posted picks never change.
- The engine never posts player props - they're never picks and never in our record. Over/unders only in sports where the
  study proved an edge.
- Preseason vs regular season: each game's "season" says it. Never guess it from records - 0-0 / 0-0-0 just means
  opening night of the regular season.
- Our picks in live games: "our picks right now" has the exact score and what each pick still needs (goals to tie,
  the swing a spread needs). Use those words as-is - never do that math yourself.
- Injuries come first: a star who's questionable holds the game; a starter who's out means the engine goes by the book's line.
- "Every game's read" entries are the engine's lean on games that are NOT our picks - say so if you use one.
- Tennis: the engine posts its OWN tennis picks every day (men's and women's, straights + a parlay) with their own
  record - they're in "tennis picks (own record, not ours)". Answer anything about them straight from there. "Tennis
  reads" are just leans on other matches, not picks.
- Records: use the "records" block exactly as written - those are the numbers on the dashboard.
- The studies (underdogs + favorites, trends, rigged/fade-the-public, spread vs moneyline, self-check) tell what's been
  PROVEN on games the engine never saw. "Watch only" / not proven means it's info, not a bet - be straight about that.

ANSWER ANYTHING
- Answer whatever they ask - player props, home run bets, anytime TDs, points/rebounds, strikeouts, first basket, a
  random bet their homie is on, any sport, any question. Never dodge, never say "we don't do that". Do the homework like
  any other question: look it up and give the real read (recent game logs, the matchup, the line if you can find it,
  weather/park for homers, who's hurt) and say straight up how you'd see it.
- But on ANY player prop, always keep it real that props are risky, in our voice - something like "you tripping doing
  player props, that shit risky as hell", "props are a trap fam, one bad night and you cooked", "we don't touch props
  for a reason - that's how they get you". Say it fresh every time, never the same line twice. Make clear it's your
  read, not an engine pick.

Never give real-money betting advice beyond what the engine picked; if someone asks how much to bet, tell them to bet
what they can afford to lose - it's entertainment.`;

const hits = new Map();                  // best effort, per Cloudflare instance

// ---- live data tools: the same feeds the engine uses, so the answer has exact numbers --------------------------
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36";
const LEAGUES = ["nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl"];
const ESPN_PATH = { nfl: "football/nfl", ncaaf: "football/college-football", nba: "basketball/nba",
  ncaab: "basketball/mens-college-basketball", mlb: "baseball/mlb", nhl: "hockey/nhl", atp: "tennis/atp", wta: "tennis/wta" };
const BOVADA_PATH = { nfl: "football/nfl", ncaaf: "football/college-football", nba: "basketball/nba",
  ncaab: "basketball/college-basketball", mlb: "baseball/mlb", nhl: "hockey/nhl" };
const AN_EXTRA = { ncaaf: "&division=FBS", ncaab: "&division=D1" };

const TOOLS = [
  { name: "get_lines_and_splits",
    description: "Action Network, live: for every game in a league on a date - the opening line, the consensus line now and " +
      "the other sportsbooks' prices (moneyline, spread, total), plus the public betting splits (% of bets and % of money on " +
      "each side). Use it for line movement, sharp vs public money, and 'what are other books saying'.",
    input_schema: { type: "object", properties: {
      league: { type: "string", enum: LEAGUES },
      date: { type: "string", description: "YYYY-MM-DD (Pacific). Leave out for today." },
      team: { type: "string", description: "Optional: only games with this team (any part of the name)." } },
      required: ["league"] } },
  { name: "get_bovada_lines",
    description: "Bovada's current lines (moneyline, spread, total) for a league - pregame and live games.",
    input_schema: { type: "object", properties: {
      league: { type: "string", enum: LEAGUES },
      team: { type: "string", description: "Optional: only games with this team." } },
      required: ["league"] } },
  { name: "get_espn_scoreboard",
    description: "ESPN scoreboard for a date: every game's status (scheduled / live / final), score, clock, team records.",
    input_schema: { type: "object", properties: {
      league: { type: "string", enum: [...LEAGUES, "atp", "wta"] },
      date: { type: "string", description: "YYYY-MM-DD. Leave out for today." },
      team: { type: "string", description: "Optional: only games with this team / player." } },
      required: ["league"] } },
];

function ptDate(d) {
  return d || new Date(Date.now() - 7 * 3600000).toISOString().slice(0, 10);
}
const has = (team, ...names) => !team || names.some((n) => String(n || "").toLowerCase().includes(String(team).toLowerCase()));

async function fetchJson(url) {
  const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function linesAndSplits({ league, date, team }) {
  const d = ptDate(date).replaceAll("-", "");
  const j = await fetchJson(`https://api.actionnetwork.com/web/v2/scoreboard/${league}?bookIds=15,30,68,69,71,75,79,123&date=${d}${AN_EXTRA[league] || ""}`);
  return (j.games || []).map((g) => {
    const t = Object.fromEntries((g.teams || []).map((x) => [x.id, x.full_name || x.display_name]));
    const home = t[g.home_team_id], away = t[g.away_team_id];
    if (!has(team, home, away)) return null;
    const books = {};
    for (const [id, m] of Object.entries(g.markets || {})) {
      const ev = (m && m.event) || {};
      const name = id === "15" ? "consensus now" : id === "30" ? "opening line" : `book ${id}`;
      const row = {};
      for (const [mk, key] of [["moneyline", "ml"], ["spread", "spread"], ["total", "total"]]) {
        for (const o of ev[mk] || []) {
          const side = o.side;
          row[`${key}_${side}`] = mk === "moneyline" ? o.odds : `${o.value} (${o.odds})`;
          const bi = o.bet_info || {};
          if (id === "15" && bi.tickets) row[`${key}_${side}_public`] = `${bi.tickets.percent}% of bets, ${bi.money ? bi.money.percent : "?"}% of money`;
        }
      }
      if (Object.keys(row).length) books[name] = row;
    }
    return { game: `${away} @ ${home}`, start: g.start_time, status: g.status, books };
  }).filter(Boolean).slice(0, 25);
}

async function bovadaLines({ league, team }) {
  const j = await fetchJson(`https://www.bovada.lv/services/sports/event/v2/events/A/description/${BOVADA_PATH[league]}?marketFilterId=def&lang=en`);
  const out = [];
  for (const grp of Array.isArray(j) ? j : []) {
    for (const ev of grp.events || []) {
      const names = (ev.competitors || []).map((c) => c.name);
      if (!has(team, ...names)) continue;
      const markets = {};
      for (const dg of ev.displayGroups || []) {
        for (const mk of dg.markets || []) {
          const per = mk.period || {};
          if (!per.main) continue;
          markets[`${mk.description}${per.live ? " (LIVE)" : ""}`] = (mk.outcomes || []).map((o) =>
            `${o.description} ${o.price && o.price.handicap ? o.price.handicap + " " : ""}${(o.price || {}).american || ""}`.trim());
        }
      }
      out.push({ game: ev.description, start: new Date(ev.startTime).toISOString(), live: !!ev.live, markets });
    }
  }
  return out.slice(0, 25);
}

async function espnScoreboard({ league, date, team }) {
  // ESPN turns Cloudflare away at site.api (9/29: every lookup failed and the AI couldn't see a match) - the web door
  // first, browser-like. Tennis lives a level down (groupings -> competitions) and Asia's matches sit on the next day.
  const day = ptDate(date).replaceAll("-", "");
  const next = new Date(Date.parse(`${ptDate(date)}T12:00:00Z`) + 86400000).toISOString().slice(0, 10).replaceAll("-", "");
  const tennis = league === "atp" || league === "wta";
  const q = (d) => `/apis/site/v2/sports/${ESPN_PATH[league]}/scoreboard?dates=${d}${league === "ncaab" ? "&groups=50" : ""}`;
  const boards = [];
  for (const d of tennis ? [day, next] : [day]) {
    for (const host of ["https://site.web.api.espn.com", "https://site.api.espn.com"]) {
      try {
        const r = await fetch(host + q(d), { headers: { "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
          Accept: "application/json", Referer: "https://www.espn.com/", Origin: "https://www.espn.com" } });
        if (r.ok) { boards.push(await r.json()); break; }
      } catch (e) { /* the other door */ }
    }
  }
  if (!boards.length) throw new Error("ESPN didn't answer");
  const out = [], seen = new Set();
  for (const j of boards) {
    for (const ev of j.events || []) {
      const comps = tennis ? (ev.groupings || []).flatMap((g) => g.competitions || []) : (ev.competitions || [ev]);
      for (const c of comps) {
        if (seen.has(c.id)) continue;
        seen.add(c.id);
        const teams = (c.competitors || []).map((x) => ({ name: (x.team || x.athlete || {}).displayName, home: x.homeAway,
          score: tennis ? (x.linescores || []).map((l) => l.value).join("-") : x.score,       // tennis: games per set
          record: ((x.records || [])[0] || {}).summary, winner: x.winner }));
        if (!has(team, ...teams.map((x) => x.name))) continue;
        out.push({ game: tennis ? teams.map((x) => x.name).join(" vs ") + ` (${ev.name || ""})` : ev.name || c.notes,
          start: c.date || ev.date, status: ((c.status || ev.status || {}).type || {}).detail, teams });
      }
    }
  }
  return out.slice(0, 60);
}

async function runTool(name, input) {
  const i = input || {};
  if (name === "get_lines_and_splits") return linesAndSplits(i);
  if (name === "get_bovada_lines") return bovadaLines(i);
  if (name === "get_espn_scoreboard") return espnScoreboard(i);
  throw new Error(`unknown tool ${name}`);
}

// Only send the parts of the data sheet a question needs (the whole sheet costs ~2x). The core always goes: records,
// today's + tomorrow's board, recent results, what the studies proved. Games, splits, tennis and the detailed study
// tables ride along when the question (or the last few) points at them. Can't tell what it's about -> the whole sheet.
const SPORT = { nfl: /nfl|football/, ncaaf: /college football|ncaaf|cfb/, nba: /nba|basketball/, ncaab: /college (hoops|basketball)|ncaab|cbb/,
  mlb: /mlb|baseball/, nhl: /nhl|hockey/ };
const WORDS = (x) => String(x || "").toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length >= 4);

function trim(brain, text) {
  const t = text.toLowerCase();
  const core = {};
  for (const k of ["updated", "today", "tomorrow", "records", "board (today + tomorrow)", "recent graded picks",
                   "tennis picks (own record, not ours)"]) core[k] = brain[k];
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

// Where each of OUR pending picks stands right now, worked out exactly (9/29: the AI read "down 5-4" right, then said
// the Oilers needed two goals to tie - it does the math, so it never recounts): the live score from the engine's own
// live board, and what the pick still needs.
export function standing(leg, sc) {
  if (!leg || !sc || !leg.side || !["home", "away"].includes(leg.side)) return null;
  const us = leg.side === "home" ? +sc.h : +sc.a, them = leg.side === "home" ? +sc.a : +sc.h;
  const m = us - them, unit = leg.league === "nhl" ? "goal" : leg.league === "mlb" ? "run" : "point";
  const n = (k) => `${k} ${unit}${k === 1 ? "" : "s"}`;
  const where = m > 0 ? `up ${us}-${them}` : m < 0 ? `down ${us}-${them}` : `tied ${us}-${them}`;
  const clock = sc.live ? ` (${sc.clock})` : " (final)";
  let need;
  if (leg.market === "spread" && leg.line != null) {
    const L = +leg.line, finish = Math.floor(-L) + 1;          // -1.5 -> win by 2+; +1.5 -> lose by 1 or better
    const lead = m + L;                                         // > 0 = covering right now
    if (L < 0) need = lead > 0 ? `covering ${leg.line} right now (needs to finish ahead by ${finish}+)` :
      `needs to finish ahead by ${finish}+ to cash ${leg.line}: a ${finish - m}-${unit} swing from here` +
      (m < 0 ? `; ${n(-m)} just ties it` : "");
    else need = lead > 0 ? `covering ${leg.line > 0 ? "+" : ""}${leg.line} right now` :
      `needs a ${Math.ceil(-lead)}-${unit} swing to get back inside ${leg.line > 0 ? "+" : ""}${leg.line}`;
  } else if (leg.market === "ml") {
    need = m > 0 ? `winning - hold on` : m === 0 ? `tied - needs the win` : `${n(-m)} ties it, ${n(-m + 1)} wins it` +
      (leg.league === "nhl" || leg.league === "mlb" ? " in regulation (a tie goes to extras)" : "");
  } else return null;
  return `${leg.team} ${where}${clock} - ${need}`;
}

function liveStanding(brain, live) {
  const sc = (live && live.scores) || {};
  const out = [];
  for (const p of brain["board (today + tomorrow)"] || []) {
    for (const l of p.legs || []) {
      if (l.result || !l.game_id || !sc[l.game_id]) continue;
      const s = standing(l, sc[l.game_id]);
      if (s && !out.includes(s)) out.push(s);
    }
  }
  return out;
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

export { espnScoreboard };
export default {
  async fetch(request, env, ctx) {
    const path = new URL(request.url).pathname.replace(/\/+$/, "");
    if (PUSH_ROUTES.has(path)) return handlePush(request, env, ctx, path, ORIGINS);
    if (path === "/scores") return handleScores(request, env, ctx, ORIGINS);
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
      return reply({ answer: "D told you not to ask stupid ass questions. You hit your 30 per hour limit. What the fuck? Way too many questions fam." }, 200, cors);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return reply({ error: "bad request" }, 400, cors);
    }
    const q = String(body.q || "").trim().slice(0, 500);
    if (!q) return reply({ error: "empty question" }, 400, cors);
    if (env.LOG) {   // the question log (just the question + when - no names, no IPs), kept 60 days
      const at = new Date().toISOString();
      ctx.waitUntil(env.LOG.put(`q:${at}:${Math.random().toString(36).slice(2, 8)}`, q,
        { expirationTtl: 60 * 86400 }).catch(() => {}));
    }
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
    const now = liveStanding(brain, live);                     // our pending picks, exactly where they stand
    if (now.length) sheet.core["our picks right now (exact - use these words, never recount the score)"] = now;
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
    const tools = [                                          // live feeds + search the web + open the pages it finds
      ...TOOLS,
      { type: "web_search_20260209", name: "web_search", max_uses: 6 },
      { type: "web_fetch_20260209", name: "web_fetch", max_uses: 4, max_content_tokens: 12000 },
    ];
    try {
      const params = {
        model,
        max_tokens: 6000,
        ...extra,
        tools,
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
          { type: "text", text: `IF THIS IS A PLAYER PROP QUESTION, the vibe for the warning (examples only - write your OWN new line in this voice, never copy these word for word): ${pick(PROP_WARN, 3).join(" / ")}` },
        ],
        messages: [
          ...history,
          {
            role: "user",
            content: `${q}\n\n[live plus money on the board right now: ${JSON.stringify((live && live.plays) || [])}]` +
              `\n[tonight's live bets we're in (team, the price we took, result - null = still going): ${
                JSON.stringify(((live && live.today) || []).map((t) => ({ team: t.team, odds: t.odds, result: t.result, sport: t.sport })))}]`,
          },
        ],
      };
      let response;
      try {
        response = await client.beta.messages.create(params);
      } catch (e) {                                          // a hiccup on the full call (web tools, the bigger model):
        if (e instanceof Anthropic.RateLimitError) throw e;  // one more try, lean - our own feeds only (9/29: the box
        console.log("retry lean", e && e.status, String(e && e.message).slice(0, 160));   // went to the fallback twice)
        params.tools = TOOLS;
        for (const k of ["betas", "fallbacks", "thinking", "output_config"]) delete params[k];
        response = await client.beta.messages.create(params);
      }
      const t0 = Date.now();
      for (let i = 0; i < 8; i++) {
        if (Date.now() - t0 > 45000) break;                  // (the page gives up at 90s: answer with what we have)                         // run its lookups until it has the answer
        if (response.stop_reason === "pause_turn") {        // a long search: let it keep going
          params.messages = [...params.messages, { role: "assistant", content: response.content }];
        } else if (response.stop_reason === "tool_use") {   // our live feeds: fetch them and hand back the numbers
          const uses = response.content.filter((b) => b.type === "tool_use");
          const results = await Promise.all(uses.map(async (u) => {
            try {
              return { type: "tool_result", tool_use_id: u.id, content: JSON.stringify(await runTool(u.name, u.input)).slice(0, 24000) };
            } catch (e) {
              return { type: "tool_result", tool_use_id: u.id, content: `couldn't load it: ${String(e).slice(0, 200)}`, is_error: true };
            }
          }));
          params.messages = [...params.messages, { role: "assistant", content: response.content }, { role: "user", content: results }];
        } else break;
        response = await client.beta.messages.create(params);
      }
      if (response.stop_reason === "refusal") {
        return reply({ answer: "Can't go there on that one. Ask me about the games, the picks, or the record. 🤝" }, 200, cors);
      }
      const blocks = response.content;
      const types = blocks.map((b) => b.type);                                        // skip "let me look that up"
      const lastSearch = Math.max(types.lastIndexOf("web_search_tool_result"), types.lastIndexOf("web_fetch_tool_result"));
      const answer = blocks
        .slice(lastSearch + 1)
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
        return reply({ error: "ai unavailable", why: `${err.status} ${String(err.message).slice(0, 160)}` }, 502, cors);
      }
      console.log("error", String(err));
      return reply({ error: "ai unavailable", why: String(err).slice(0, 160) }, 502, cors);   // (the hourly check reads it)
    }
  },
};
