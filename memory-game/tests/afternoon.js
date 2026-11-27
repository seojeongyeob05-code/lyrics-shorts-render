// Plays the story chain 1 -> 5 using the test win hook and checks the afternoon summary.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + require('path').resolve(__dirname, '../index.html'));
  await p.evaluate(() => localStorage.setItem('ag520.played', 'true')); await p.reload();
  await p.click('.lvl[data-level="1"]');
  // use one word so "new words this afternoon" is not empty
  await p.fill('#sayInput', 'hello'); await p.press('#sayInput', 'Enter');
  for (let lv = 1; lv <= 5; lv++) {
    await p.evaluate(() => ag520.win()); await p.waitForTimeout(200);
    const has = await p.$('.afternoon');
    console.log(`after win L${lv}: summary=${!!has}`);
    if (lv < 5) await p.click('#nextStory');
  }
  console.log('summary:', (await p.textContent('.afternoon')).replace(/\s+/g, ' '));
  await p.screenshot({ path: require('path').join(__dirname, 'out', 'afternoon.png') });
  console.log('errors', errs); await b.close();
})();
