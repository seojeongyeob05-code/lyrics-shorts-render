// Plays one lesson in a phone-width headless browser and answers chosen questions correctly.
// usage: node lesson.js "<lesson row text, e.g. 13장 화학 평형>" '{"<question substring>":"<exact correct option>"}'
// Include the chapter title in the row text: "22장 " alone also matches lesson 2, whose row reads "2" + "2장…".
const { chromium } = require('playwright'); const wrap = require('./_wrap');
(async () => {
  const [rowText, wantJson] = process.argv.slice(2);
  const want = JSON.parse(wantJson || '{}');
  const b = await chromium.launch({ executablePath: wrap.CHROMIUM });
  const p = await b.newPage({ viewport: { width: 400, height: 860 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(wrap()); await p.waitForTimeout(800);
  await p.locator('.row', { hasText: rowText }).first().click(); await p.waitForTimeout(300);
  const head = [await p.$$eval('.concept li', x => x.length), await p.$eval('.concept .eyebrow', e => e.textContent)];
  await p.click('#go');
  const log = [];
  for (let s = 0; s < 40; s++) {
    await p.waitForTimeout(150);
    if (await p.$('#done')) { await p.click('#done'); break; }
    const q = await p.$eval('.qtext', e => e.textContent).catch(() => '');
    const k = Object.keys(want).find(k => q.includes(k));
    if (await p.$('#opts')) {
      const i = k ? await p.$$eval('.opt .t', (xs, a) => xs.findIndex(x => x.textContent.trim() === a), want[k]) : 0;
      await p.click('.opt >> nth=' + Math.max(0, i)); await p.click('#check');
      if (k) log.push([k, i, await p.$eval('.verdict', e => e.textContent)]);
    } else if (await p.$('#pool')) {
      const n = await p.$$eval('#pool .chip', x => x.length);
      for (let i = 0; i < n; i++) await p.click('#pool .chip:not(.used) >> nth=0');
      await p.click('#check');
    }
    await p.click('#next');
  }
  console.log(JSON.stringify({ head, log, errs, scrollWidth: await p.evaluate(() => document.documentElement.scrollWidth) }));
  await b.close();
})();
