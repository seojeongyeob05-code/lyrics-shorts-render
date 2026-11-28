// Plays the story chain 1 -> 5 using the test win hook and checks the afternoon summary.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + require('path').resolve(__dirname, '../index.html'));
  await p.evaluate(() => localStorage.setItem('ag520.played', 'true')); await p.reload();
  await p.click('.lvl[data-level="1"]');
  // use one word so "new words this afternoon" is not empty
  // walk next to the guard and say a journal word that he understands
  for (let st = 0; st < 40; st++) {
    const k = await p.evaluate(() => { const S = ag520.state(), M = ag520.map; const [tx, ty] = S.npcs.guard; const goal = new Set([[0,1],[1,0],[0,-1],[-1,0]].map(([dx,dy]) => (tx+dx)+','+(ty+dy))); if (goal.has(S.x+','+S.y)) return null;
      const occ = new Set(Object.values(S.npcs).map(([x, y]) => x + ',' + y)); const prev = { [S.x+','+S.y]: null }, q = [[S.x, S.y]]; let end;
      while (q.length) { const [x, y] = q.shift(); if (goal.has(x+','+y)) { end = x+','+y; break; } for (const [dx, dy, k] of [[0,-1,'ArrowUp'],[1,0,'ArrowRight'],[0,1,'ArrowDown'],[-1,0,'ArrowLeft']]) { const nx = x+dx, ny = y+dy, key = nx+','+ny; if (nx<0||ny<0||nx>=15||ny>=12||M[ny][nx]==='#'||occ.has(key)||ag520.blocked(nx,ny)||key in prev) continue; prev[key] = [x+','+y, k]; q.push([nx, ny]); } }
      let cur = end, f = null; while (prev[cur]) { f = prev[cur][1]; cur = prev[cur][0]; } return f; });
    if (!k) break; await p.evaluate(() => document.activeElement.blur()); await p.keyboard.press(k);
  }
  await p.fill('#sayInput', 'I lost my wallet'); await p.press('#sayInput', 'Enter');
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
