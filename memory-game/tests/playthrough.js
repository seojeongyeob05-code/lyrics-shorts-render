const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const URL = 'file://' + require('path').resolve(__dirname, '../index.html');
async function setup(b, level, vp = { width: 1280, height: 900 }) {
  const p = await b.newPage({ viewport: vp });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
  await p.goto(URL); await p.click(`.lvl[data-level="${level}"]`);
  await p.evaluate(() => document.activeElement.blur());
  return { p, errs };
}
async function goNear(p, who) {
  await p.evaluate(() => document.activeElement.blur());
  const keys = await p.evaluate(who => {
    const S = ag520.state(), M = ag520.map, W = 15, H = 12;
    const occ = new Set(Object.values(S.npcs).map(([x, y]) => x + ',' + y));
    const [tx, ty] = S.npcs[who];
    const goal = new Set([[0, 1], [1, 0], [0, -1], [-1, 0]].map(([dx, dy]) => (tx + dx) + ',' + (ty + dy)));
    const prev = { [S.x + ',' + S.y]: null }, q = [[S.x, S.y]]; let end;
    while (q.length) { const [x, y] = q.shift(); if (goal.has(x + ',' + y)) { end = x + ',' + y; break; }
      for (const [dx, dy, k] of [[0, -1, 'ArrowUp'], [1, 0, 'ArrowRight'], [0, 1, 'ArrowDown'], [-1, 0, 'ArrowLeft']]) {
        const nx = x + dx, ny = y + dy, key = nx + ',' + ny;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H || M[ny][nx] === '#' || occ.has(key) || ag520.blocked(nx, ny) || key in prev) continue;
        prev[key] = [x + ',' + y, k]; q.push([nx, ny]); } }
    const out = []; let cur = end; while (prev[cur]) { out.unshift(prev[cur][1]); cur = prev[cur][0]; } return out;
  }, who);
  if (keys.length) { await p.keyboard.press(keys[0]); if (keys.length > 1 && (p._steps = (p._steps || 0) + 1) < 60) return goNear(p, who); }
  p._steps = 0;
}
const say = async (p, t) => { await p.fill('#sayInput', t); await p.press('#sayInput', 'Enter'); };
const lastNpc = p => p.evaluate(() => [...document.querySelectorAll('.msg.npc .en')].pop()?.dataset.full || '');
(async () => {
  const b = await chromium.launch();
  // Level 1 win
  { const { p, errs } = await setup(b, 1);
    await goNear(p, 'guard');
    const S = await p.evaluate(() => { const s = ag520.state(); return { color: s.color, content: s.content }; });
    await say(p, 'yes'); await p.click('#gestures .chip:nth-child(2)'); await say(p, 'color ' + S.color);
    await p.click('.chip.tool'); await p.waitForTimeout(1500);
    await p.screenshot({ path: require('path').join(__dirname, 'out', 'v-mid.png') });
    await say(p, { card: 'student card', photo: 'photo', ticket: 'ticket' }[S.content]);
    await p.waitForTimeout(300); console.log('before sign:', await lastNpc(p));
    await say(p, 'what?'); console.log('wrong:', await lastNpc(p));
    await p.click('#gestures .chip:nth-child(7)'); console.log('gesture7 =', await p.textContent('#gestures .chip:nth-child(7)'));
    await p.waitForTimeout(1500);
    console.log('L1:', (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 60), errs);
    await p.close(); }
  // Level 2 good + mug
  for (const mode of ['good', 'mug']) { const { p, errs } = await setup(b, 2);
    await goNear(p, 'grandma');
    const o = await p.evaluate(() => ag520.state().order);
    await goNear(p, 'barista');
    await say(p, o.drink); await say(p, o.size); await say(p, o.milk); await say(p, mode === 'good' ? 'to go' : 'for here');
    await goNear(p, 'grandma'); await p.waitForTimeout(1500);
    console.log(await p.evaluate(() => [...document.querySelectorAll('.msg')].slice(-8).map(m => m.className + ': ' + (m.querySelector('.en')?.dataset.full || m.textContent).slice(0, 90)).join('\n')), await p.evaluate(() => { const s = ag520.state(); return [s.x, s.y, s.t, JSON.stringify(s.npcs)]; }));
    console.log('L2', mode, (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 40), errs);
    await p.close(); }
  // Level 3: wrong (teen/ty) locker, then correct
  { const { p, errs } = await setup(b, 3);
    for (let i = 0; i < 20 && (await p.evaluate(() => ag520.state().bigParcel)); i++) { await p.click('#levelBtn'); await p.click('.lvl[data-level="3"]'); }
    const st = await p.evaluate(() => ({ locker: ag520.state().locker, code: ag520.state().code }));
    const wrong = st.locker % 10 === 0 ? st.locker / 10 + 10 : (st.locker - 10) * 10;
    await goNear(p, 'locker'); console.log('L3 greet:', await lastNpc(p));
    await say(p, String(wrong)); await say(p, '1234'); console.log('L3 wrong:', await lastNpc(p));
    await say(p, 'locker ' + st.locker); await say(p, st.code.split('').join(' '));
    await p.waitForTimeout(1500);
    console.log('L3', st, (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 120), errs);
    console.log('L3 mistakes', await p.evaluate(() => ag520.state().mistakes.map(m => m.cat + ' | ' + m.explain.slice(0, 70))));
    await p.screenshot({ path: require('path').join(__dirname, 'out', 'v-l3.png') });
    await p.close(); }
  // Level 3 big-parcel variant: locker first (wrong), then guard with apartment number in words
  { const { p, errs } = await setup(b, 3);
    for (let i = 0; i < 20 && !(await p.evaluate(() => ag520.state().bigParcel)); i++) { await p.click('#levelBtn'); await p.click('.lvl[data-level="3"]'); }
    const apt = await p.evaluate(() => ag520.state().apt);
    console.log('L3big note:', await p.evaluate(() => [...document.querySelectorAll('.msg.place')].pop().textContent.slice(0, 90)));
    await goNear(p, 'locker'); await say(p, '13'); console.log('L3big locker:', await lastNpc(p));
    await goNear(p, 'guard'); await say(p, 'package'); console.log('L3big guard:', await lastNpc(p));
    await say(p, '999'); console.log('L3big wrong apt:', await lastNpc(p));
    const ONES = ['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen'];
    const words = ONES[Math.floor(apt / 100)] + ' oh ' + ONES[apt % 100];
    await say(p, words); console.log('L3big apt', apt, words, '->', await lastNpc(p));
    await say(p, 'sure'); await p.waitForTimeout(1500);
    console.log('L3big', (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 140), errs);
    console.log('L3big mistakes', await p.evaluate(() => ag520.state().mistakes.map(m => m.cat + ' | ' + m.act)));
    await p.close(); }
  // Level 4: one wrong direction, one gesture, then words
  { const { p, errs } = await setup(b, 4);
    const st = await p.evaluate(() => { const S = ag520.state(); return { vq: S.vq, slots: S.vq.map(q => S.slotOf[q]) }; });
    const phrase = { a: 'ahead on your left', b: 'straight ahead', c: 'ahead on your right', d: 'on your left', e: 'on your right' };
    const wrong = { a: 'on your right', b: 'on your left', c: 'on your left', d: 'on your right', e: 'on your left' };
    await goNear(p, 'visitor'); console.log('L4 greet:', await lastNpc(p));
    await say(p, wrong[st.slots[0]]); console.log('L4 wrong:', await lastNpc(p));
    await say(p, phrase[st.slots[0]]); console.log('L4 ok1:', await lastNpc(p));
    await p.click('#gestures .chip:nth-child(3)'); const lbl = { a: '↖', b: '↑', c: '↗', d: '←', e: '→' }[st.slots[1]];
    await p.locator('#pointer .chip', { hasText: lbl }).click(); console.log('L4 gesture:', await lastNpc(p));
    await say(p, 'it is ' + phrase[st.slots[2]]); await p.waitForTimeout(1500);
    console.log('L4', st, (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 160), errs);
    console.log('L4 mistakes', await p.evaluate(() => ag520.state().mistakes.map(m => m.cat + ' | ' + m.explain.slice(0, 80))));
    await p.close(); }
  // Level 5: report the broken thing to the janitor, with one wrong object first
  { const { p, errs } = await setup(b, 5);
    const fix = await p.evaluate(() => ag520.state().fix);
    const OBJ = { leak: 'sink', flicker: 'light', clog: 'toilet' }, WORD = { leak: 'leaking', flicker: 'flickering', clog: 'clogged' };
    const other = Object.values(OBJ).find(o => o !== OBJ[fix]);
    await goNear(p, 'janitor'); console.log('L5 greet:', await lastNpc(p));
    await say(p, 'something is broken'); console.log('L5 broken:', await lastNpc(p));
    await say(p, 'restroom'); console.log('L5 place:', await lastNpc(p));
    await say(p, 'the ' + other); console.log('L5 wrong obj:', await lastNpc(p));
    await say(p, 'the ' + OBJ[fix]); console.log('L5 obj:', await lastNpc(p));
    await say(p, 'it is ' + WORD[fix]); await p.waitForTimeout(1500);
    console.log('L5', fix, (await p.textContent('#sheet')).replace(/\s+/g, ' ').slice(0, 140), errs);
    console.log('L5 mistakes', await p.evaluate(() => ag520.state().mistakes.map(m => m.cat + ' | ' + m.explain.slice(0, 60))));
    await p.close(); }
  // Level 5: exploring rooms is not a mistake
  { const { p, errs } = await setup(b, 5);
    for (const target of ['a', 'b', 'c', 'd', 'e']) {
      for (let st = 0; st < 40; st++) {
        const k = await p.evaluate(t => { const S = ag520.state(), M = ag520.map; if (M[S.y][S.x] === t) return null;
          const occ = new Set(Object.values(S.npcs).map(([x, y]) => x + ',' + y)); const prev = { [S.x + ',' + S.y]: null }, q = [[S.x, S.y]]; let end;
          while (q.length) { const [x, y] = q.shift(); if (M[y][x] === t) { end = x + ',' + y; break; }
            for (const [dx, dy, k] of [[0, -1, 'ArrowUp'], [1, 0, 'ArrowRight'], [0, 1, 'ArrowDown'], [-1, 0, 'ArrowLeft']]) { const nx = x + dx, ny = y + dy, key = nx + ',' + ny;
              if (nx < 0 || ny < 0 || nx >= 15 || ny >= 12 || M[ny][nx] === '#' || occ.has(key) || ag520.blocked(nx, ny) || key in prev) continue; prev[key] = [x + ',' + y, k]; q.push([nx, ny]); } }
          if (!end) return null; let cur = end, first = null; while (prev[cur]) { first = prev[cur][1]; cur = prev[cur][0]; } return first; }, target);
        if (!k) break; await p.evaluate(() => document.activeElement.blur()); await p.keyboard.press(k);
      }
    }
    console.log('L5rooms mistakes: ' + (await p.evaluate(() => ag520.state().mistakes.length)), errs);
    await p.close(); }
  // Phone layout + start screen
  { const { p, errs } = await setup(b, 1, { width: 390, height: 844 });
    for (const k of ['ArrowUp', 'ArrowUp', 'ArrowRight']) await p.keyboard.press(k);
    await p.waitForTimeout(1200);
    await p.screenshot({ path: require('path').join(__dirname, 'out', 'v-phone.png'), fullPage: true });
    console.log('phone hscroll', await p.evaluate(() => document.documentElement.scrollWidth > innerWidth), errs);
    await p.close(); }
  { const p = await b.newPage({ viewport: { width: 1280, height: 900 } }); await p.goto(URL); await p.waitForTimeout(500); await p.screenshot({ path: require('path').join(__dirname, 'out', 'v-intro.png') }); await p.close(); }
  await b.close();
})();
