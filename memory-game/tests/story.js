const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 844 } });
const errs = []; p.on('pageerror', e => errs.push(e.message));
await p.goto('file://' + require('path').resolve(__dirname, '../index.html'));
await p.evaluate(() => localStorage.setItem('ag520.played', 'true')); await p.reload();
await p.click('.lvl[data-level="1"]');
// force a win quickly via the guard flow shortcut: set state and call win through the sign step
await p.evaluate(() => { const S = ag520.state(); S.guardStage = 3; S.npcs.guard = [S.x, S.y - 1]; });
await p.fill('#sayInput', 'sure'); await p.press('#sayInput', 'Enter'); await p.waitForTimeout(1200);
console.log('win sheet:', (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 200));
await p.screenshot({ path: require('path').join(__dirname, 'out', 'story.png') });
await p.click('#nextStory'); await p.waitForTimeout(300);
console.log('now level', await p.evaluate(() => ag520.state().level), '| first sys:', await p.evaluate(() => document.querySelector('.msg.sys').textContent));
await p.evaluate(() => document.activeElement.blur()); await p.keyboard.press('ArrowUp'); await p.keyboard.press('ArrowRight'); await p.waitForTimeout(200);
console.log('story grandma:', await p.evaluate(() => [...document.querySelectorAll('.msg.npc .en')][0].dataset.full.slice(0, 60)));
await p.click('#levelBtn'); await p.click('#sheet .lvl[data-level="2"]');
await p.evaluate(() => document.activeElement.blur()); await p.keyboard.press('ArrowUp'); await p.keyboard.press('ArrowRight'); await p.waitForTimeout(200);
console.log('list grandma:', await p.evaluate(() => [...document.querySelectorAll('.msg.npc .en')][0].dataset.full.slice(0, 60)));
console.log('errors', errs); await b.close(); })();
