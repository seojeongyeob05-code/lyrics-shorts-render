// Play one lesson to the end (wrong answers on purpose), reload, and check the review queue survives.
// Usage: node persist.js <lesson-row-index>
const { chromium } = require('playwright');
(async () => {
  const dir = '/tmp/claude-0/-home-user-lyrics-shorts-render/aab714b1-76a9-5044-8566-031709b1ccd5/scratchpad/';
  const row = +(process.argv[2] || 1);
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}*{animation:none!important;transition:none!important}</style></head><body>' + require('fs').readFileSync(dir + 'gongsu-daily.html', 'utf8') + '</body></html>';
  require('fs').writeFileSync(dir + '_wrap.html', html);
  const b = await chromium.launch();
  const p = await (await b.newContext({ viewport: { width: 400, height: 860 } })).newPage();
  p.on('pageerror', e => console.log('PAGEERR', e.message));
  await p.goto('file://' + dir + '_wrap.html');
  await p.waitForTimeout(2000);
  console.log('lesson:', (await (await p.$$('.row'))[row].textContent()).trim());
  await (await p.$$('.row'))[row].click();
  await p.click('#go');
  const seen = new Set();
  for (let i = 0; i < 80; i++) {
    if (await p.$('#done')) break;
    if (await p.$('#next')) { await p.click('#next'); continue; }
    seen.add((await p.textContent('.qtext')).slice(0, 40));
    if (await p.$('#ans')) await p.fill('#ans', '999');
    else if (await p.$('#opts')) await p.click('.opt >> nth=0');
    else { const c = await p.$$('#pool .chip'); for (let k = c.length - 1; k >= 0; k--) await c[k].click(); }
    await p.click('#check');
  }
  const missed = await p.$$eval('.mcard', e => e.length);
  await p.click('#done');
  const before = await p.textContent('#review-sub');
  await p.reload();
  await p.waitForTimeout(2000);
  console.log('questions', seen.size, '| missed cards', missed, '| review before/after reload:', before, '/', await p.textContent('#review-sub'));
  await b.close();
})();
