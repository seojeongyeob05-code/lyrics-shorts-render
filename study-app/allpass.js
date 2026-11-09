const { chromium } = require('playwright');
(async () => {
  const dir = '/tmp/claude-0/-home-user-lyrics-shorts-render/aab714b1-76a9-5044-8566-031709b1ccd5/scratchpad/';
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}*{animation:none!important;transition:none!important}</style></head><body>' + require('fs').readFileSync(dir + 'gongsu-daily.html', 'utf8') + '</body></html>';
  require('fs').writeFileSync(dir + '_wrap.html', html);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 400, height: 860 } });
  p.on('pageerror', e => console.log('PAGEERR', e.message));
  await p.goto('file://' + dir + '_wrap.html');
  await p.waitForTimeout(2500);
  const n = (await p.$$('.row')).length;
  let bad = 0;
  for (let li = 0; li < n; li++) {
    const rows = await p.$$('.row');
    await rows[li].click();
    await p.click('#go', { timeout: 3000 });
    let steps = 0, ok = false;
    for (let i = 0; i < 80; i++) {
      if (await p.$('#done')) { ok = true; break; }
      if (await p.$('#next')) { await p.click('#next', { timeout: 3000 }); continue; }
      if (await p.$('#ans')) await p.fill('#ans', '1');
      else if (await p.$('#opts')) await p.click('.opt >> nth=0', { timeout: 3000 });
      else { const c = await p.$$('#pool .chip'); for (const x of c) await x.click({ timeout: 3000 }); }
      if (!(await p.$('#gloss[hidden]'))) { console.log('GLOSS OPENED in lesson', li); bad++; await p.click('#gloss-close'); }
      await p.click('#check', { timeout: 3000 }); steps++;
    }
    const merr = await p.$$eval('mjx-merror', e => e.length);
    if (!ok || merr) { console.log('lesson', li, 'finished', ok, 'mathErrors', merr); bad++; }
    await p.click('#done', { timeout: 3000 });
  }
  console.log('lessons', n, 'problems', bad);
  await b.close();
})();
