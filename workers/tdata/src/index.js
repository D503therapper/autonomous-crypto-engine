// Fetches one tennis-data.co.uk season file: GET /2024/2024.xlsx (ATP) or /2024w/2024.xlsx (WTA). Nothing else.
const OK = /^\/(\d{4})w?\/\1\.xlsx?$/;

export default {
  async fetch(req) {
    const path = new URL(req.url).pathname;
    if (req.method !== "GET" || !OK.test(path)) return new Response("not found", { status: 404 });
    let last = null;
    for (const base of ["https://www.tennis-data.co.uk", "http://www.tennis-data.co.uk"]) {
      const r = await fetch(base + path, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
          "Accept": "*/*",
          "Referer": "http://www.tennis-data.co.uk/alldata.php",
        },
        cf: { cacheTtl: 86400, cacheEverything: true },
      });
      if (r.ok) return new Response(r.body, { headers: { "Content-Type": "application/octet-stream" } });
      last = r.status;
      if (r.status === 404) break;
    }
    return new Response(`upstream ${last}`, { status: last === 404 ? 404 : 502 });
  },
};
