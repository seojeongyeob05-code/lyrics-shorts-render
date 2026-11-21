// Plays every lesson to the end (always picking the first option) and reports console errors.
const { chromium } = require('playwright'); const wrap = require('./_wrap');
(async () => {
  const b = await chromium.launch({ executablePath: wrap.CHROMIUM });
  const p = await b.newPage({ viewport: { width: 400, height: 860 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(wrap()); await p.waitForTimeout(800);
  const total = await p.$$eval('.row', x => x.length);
  for (let k = 0; k < total; k++) {
    await p.locator('.row:not(.done)').first().click();
    await p.click('#go');
    for (let s = 0; s < 60; s++) {
      await p.waitForTimeout(80);
      if (await p.$('#done')) { await p.click('#done'); break; }
      if (await p.$('#opts')) { await p.click('.opt >> nth=0'); await p.click('#check'); }
      else if (await p.$('#pool')) { const n = await p.$$eval('#pool .chip', x => x.length); for (let i = 0; i < n; i++) await p.click('#pool .chip:not(.used) >> nth=0'); await p.click('#check'); }
      await p.click('#next');
    }
  }
  console.log('lessons done', await p.$$eval('.row.done', x => x.length), '/', total, 'errors', errs, 'scrollWidth', await p.evaluate(() => document.documentElement.scrollWidth));
  await b.close();
})();
