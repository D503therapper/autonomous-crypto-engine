// 📱 THE PHONE LAYOUT CHECK (the owner, 11/17: the WE GOT IN EARLY box was "cropped out on the side" - "We never want
// this type of bug to happen again, ever"). Loads the built dashboard at real phone widths (small Android / iPhone SE
// up to big iPhones), opens every closed section, and fails if ANYTHING runs past the screen's edge - a box, a price, a
// word - unless it sits inside a box made to scroll sideways. Writes data/sports/layout_check.json; exit 1 on a problem.
// Usage: node tools/layout_check.js [page.html] [out.json]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const page_ = path.resolve(process.argv[2] || 'docs/sports/index.html');
const out = process.argv[3] || 'data/sports/layout_check.json';
const WIDTHS = [320, 360, 390, 430];
(async () => {
  let browser;
  try { browser = await chromium.launch(); }
  catch (e) { browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] }); }
  const problems = [];
  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    await p.route(/^https?:/, r => r.abort());          // the page as built - no network, no live refresh
    await p.goto('file://' + page_, { waitUntil: 'load' });
    await p.waitForTimeout(800);
    await p.evaluate(() => { document.querySelectorAll('details').forEach(d => d.open = true); });
    await p.waitForTimeout(300);
    const found = await p.evaluate((w) => {
      // a box made to scroll sideways (overflow-x auto / scroll) is fine; a box that CLIPS (hidden / clip) crops what
      // runs past it - that is the bug (11/17: the 🎯 price column cut off by the card's edge)
      const edge = e => { let L = -1, R = w + 1;
        for (let x = e.parentElement; x && x !== document.documentElement; x = x.parentElement) {
          const o = getComputedStyle(x).overflowX;
          if (o === 'auto' || o === 'scroll') return null;
          if (o === 'hidden' || o === 'clip') { const q = x.getBoundingClientRect(); L = Math.max(L, q.left - 1); R = Math.min(R, q.right + 1); }
        } return [L, R]; };
      const bad = [];
      for (const e of document.querySelectorAll('body *')) {
        const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
        if (r.width < 2 || r.height < 2 || cs.visibility === 'hidden' || cs.display === 'none' || cs.position === 'fixed' || cs.position === 'absolute') continue;
        if (!(e.textContent || '').trim() && !['img', 'svg', 'canvas', 'button', 'input'].includes(e.tagName.toLowerCase())) continue;
        const lr = edge(e);
        if (!lr) continue;
        if (r.right > lr[1] || r.left < lr[0]) {
          if ([...e.children].some(c => { const q = c.getBoundingClientRect(); return q.width > 1 && (q.right > lr[1] || q.left < lr[0]); })) continue;   // report the deepest
          bad.push({ tag: e.tagName.toLowerCase(), cls: String(e.className || '').slice(0, 40), left: Math.round(r.left), right: Math.round(r.right),
                     box: [Math.round(lr[0]), Math.round(lr[1])], text: (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 70) });
        }
      }
      return { page_wide: document.documentElement.scrollWidth, bad: bad.slice(0, 20) };
    }, w);
    if (found.page_wide > w + 1 || found.bad.length)
      problems.push({ width: w, page_wide: found.page_wide, offenders: found.bad });
    await ctx.close();
  }
  await browser.close();
  const res = { at: new Date().toISOString().slice(0, 16) + 'Z', page: path.relative(process.cwd(), page_), widths: WIDTHS,
                ok: problems.length === 0, problems };
  try { fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify(res, null, 1)); } catch (e) {}
  if (problems.length) {
    for (const pr of problems) for (const o of pr.offenders.slice(0, 5))
      console.log(`LAYOUT CHECK: at ${pr.width}px <${o.tag} class="${o.cls}"> runs ${o.left}..${o.right}px past its box ${o.box[0]}..${o.box[1]}: "${o.text}"`);
    process.exit(1);
  }
  console.log(`layout check: clean at ${WIDTHS.join(' / ')}px`);
})().catch(e => { console.log('layout check could not run: ' + String(e).slice(0, 200)); process.exit(2); });
