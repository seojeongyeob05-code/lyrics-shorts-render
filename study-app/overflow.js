// For every lesson, walk all questions and report options/chips whose math is wider than the card (cut off on a 400px phone).
const { chromium } = require('playwright');
(async () => {
  const dir = '/tmp/claude-0/-home-user-lyrics-shorts-render/aab714b1-76a9-5044-8566-031709b1ccd5/scratchpad/';
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 400, height: 860 } });
  await p.goto('file://' + dir + '_wrap.html');
  await p.waitForTimeout(2500);
  const n = (await p.$$('.row')).length;
  const found = [];
  for (let li = 0; li < n; li++) {
    await (await p.$$('.row'))[li].click();
    await p.click('#go');
    const seen = new Set();
    for (let i = 0; i < 80; i++) {
      if (await p.$('#done')) break;
      if (await p.$('#next')) { await p.click('#next'); continue; }
      await p.waitForFunction(() => !document.querySelector('.qtext') || document.querySelector('.qtext mjx-container') || !/\$/.test(document.querySelector('.qtext').textContent), null, { timeout: 4000 }).catch(() => {});
      await p.waitForTimeout(250);
      const q = (await p.textContent('.qtext')).slice(0, 30);
      if (!seen.has(q)) {
        seen.add(q);
        const cut = await p.$$eval('.opt .t, .chip .t', els => els.filter(e => e.scrollWidth > e.clientWidth + 2).map(e => e.textContent.slice(0, 30)));
        if (cut.length) found.push({ lesson: li, q, cut });
      }
      if (await p.$('#ans')) await p.fill('#ans', '1');
      else if (await p.$('#opts')) await p.click('.opt >> nth=0');
      else { const c = await p.$$('#pool .chip'); for (const x of c) await x.click(); }
      await p.click('#check');
    }
    await p.click('#done');
  }
  for (const f of found) console.log(String(f.lesson).padStart(2, '0') + '강 | ' + f.q + ' | ' + f.cut.length + '개 잘림');
  console.log('total questions with cut-off options:', found.length);
  await b.close();
})();
