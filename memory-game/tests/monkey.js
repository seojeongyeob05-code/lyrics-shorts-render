const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const WORDS = ['hello', 'wallet', 'I lost my wallet', 'black', 'brown', 'red', 'blue', 'card', 'photo', 'ticket', 'yes', 'no', 'sure', 'Minji Kim', 'latte', 'small', 'large', 'oat', 'almond', 'to go', 'for here', 'thirteen', '30', 'four seven two nine', '1204', 'twelve oh four', 'where is the restroom', 'next to the gym', 'on your left', 'straight ahead', 'ahead on your right', 'what is security?', 'security', '지갑', '', '   ', 'thank you', 'coffee', 'help', 'package', 'locker 14', 'right there', '<b>x</b>', 'it is "quoted"', 'a'.repeat(300)];
(async () => {
  const b = await chromium.launch();
  const all = new Map();
  const runs = +(process.argv[2] || 24);
  for (let run = 0; run < runs; run++) {
    const vp = run % 3 === 0 ? { width: 390, height: 844 } : { width: 1280, height: 900 };
    const p = await b.newPage({ viewport: vp });
    const errs = [];
    p.on('pageerror', e => errs.push(e.message + ' @ ' + (e.stack || '').split('\n')[1]));
    p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
    await p.goto('file://' + require('path').resolve(__dirname, '../index.html'));
    if (run % 4 === 0) await p.evaluate(() => { const now = Date.now(); localStorage.setItem('ag520.journal', JSON.stringify({ wallet: { seen: true, known: true, box: 0, due: now - 1, missed: now - 1 }, quarter: { seen: true, known: true, box: 2, due: now - 1 } })); });
    await p.reload();
    let seed = run * 7919 + 1;
    const rnd = n => { seed = (seed * 48271) % 2147483647; return seed % n; };
    const level = 1 + (run % 4);
    try {
      await p.click(`.lvl[data-level="${level}"]`, { timeout: 2000 });
      for (let step = 0; step < 260; step++) {
        const overlayOpen = !(await p.evaluate(() => document.getElementById('overlay').hidden));
        if (overlayOpen) {
          const btn = (await p.$('#typeInput')) ? null : ((await p.$('#again')) || (await p.$('#skip')) || (await p.$('#go')) || (await p.$('#close')) || (await p.$('#sheet .lvl[data-level]')));
          if (await p.$('#typeInput')) { await p.fill('#typeInput', WORDS[rnd(WORDS.length)]); await p.press('#typeInput', 'Enter'); await p.waitForTimeout(2000); continue; }
          if (btn) await btn.click().catch(() => {}); else break;
          continue;
        }
        const r = rnd(100);
        if (r < 45) { await p.evaluate(() => document.activeElement && document.activeElement.blur()); await p.keyboard.press(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'][rnd(4)]); }
        else if (r < 70) { await p.fill('#sayInput', WORDS[rnd(WORDS.length)]); await p.press('#sayInput', 'Enter'); }
        else if (r < 82) {
          const chips = await p.$$('#gestures .chip'); await chips[rnd(chips.length)].click().catch(() => {});
          const pc = await p.$$('#pointer:not([hidden]) .chip'); if (pc.length) await pc[rnd(pc.length)].click().catch(() => {});
        }
        else if (r < 86) { const sw = await p.$('.swap'); if (sw) await sw.click(); }
        else if (r < 88) { await p.click('#journalBtn').catch(() => {}); }
        else if (r < 90) { await p.click('#levelBtn').catch(() => {}); }
        else if (r < 92) { await p.click('#log').catch(() => {}); }
        else { await p.click('.pad .' + ['up', 'down', 'left', 'right'][rnd(4)]).catch(() => {}); }
      }
    } catch (e) { errs.push('driver: ' + e.message.split('\n')[0]); }
    const st = await p.evaluate(() => { const S = ag520.state(); return S ? `L${S.level} loop${S.loop} t=${S.t} done=${S.done} won=${!!S.won}` : 'no state'; }).catch(e => 'eval fail ' + e.message);
    for (const e of errs) all.set(e, (all.get(e) || 0) + 1);
    console.log(`run ${run} L${level} ${vp.width}px: ${errs.length} errors | ${st}`);
    await p.close();
  }
  console.log('\nUNIQUE ERRORS:');
  for (const [e, n] of all) console.log(n + 'x ' + e);
  await b.close();
})();
