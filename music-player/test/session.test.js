import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createApp, loadConfig } from '../server/index.js';

const DAY = 24 * 60 * 60 * 1000;
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-session-'));
const { app, db } = createApp(loadConfig({ DATA_DIR: dir, AUTO_BACKUP_KEEP: '0' }));
const server = await new Promise((resolve) => { const s = app.listen(0, () => resolve(s)); });
const base = `http://127.0.0.1:${server.address().port}`;
after(() => { server.close(); fs.rmSync(dir, { recursive: true, force: true }); });

const res = await fetch(`${base}/api/auth/setup`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'me', password: 'password123' }),
});
const cookie = res.headers.get('set-cookie').split(';')[0];
const tokenHash = crypto.createHash('sha256').update(cookie.split('=')[1]).digest('hex');
const expiresAt = () => db.prepare('SELECT expires_at FROM sessions WHERE token_hash = ?').get(tokenHash)?.expires_at;
const setExpiresAt = (t) => db.prepare('UPDATE sessions SET expires_at = ? WHERE token_hash = ?').run(t, tokenHash);
const status = () => fetch(`${base}/api/auth/status`, { headers: { cookie } });

test('로그인 직후(남은 기간이 넉넉함)에는 세션을 늘리지 않아 DB를 매번 쓰지 않는다', async () => {
  const before = expiresAt();
  const r = await status();
  assert.equal((await r.json()).user.username, 'me');
  assert.equal(r.headers.get('set-cookie'), null);
  assert.equal(expiresAt(), before);
});

test('남은 기간이 절반(15일) 아래면 쓰는 순간 30일로 다시 늘리고 쿠키도 새로 준다', async () => {
  setExpiresAt(Date.now() + 2 * DAY);
  const r = await status();
  assert.equal((await r.json()).user.username, 'me');
  const renewed = expiresAt();
  assert.ok(Math.abs(renewed - (Date.now() + 30 * DAY)) < 60_000, `expires_at ${renewed}`);
  const setCookie = r.headers.get('set-cookie');
  assert.ok(setCookie.startsWith(cookie + ';'), setCookie); // 같은 토큰을 다시 줌
  assert.match(setCookie, /Max-Age=2592000/);
  assert.match(setCookie, /HttpOnly/);
});

test('이미 만료된 세션은 늘리지 않고 로그인이 필요하다', async () => {
  setExpiresAt(Date.now() - 1000);
  const r = await status();
  assert.equal((await r.json()).user, null);
  assert.equal(r.headers.get('set-cookie'), null);
  assert.ok(expiresAt() < Date.now());
  assert.equal((await fetch(`${base}/api/tracks`, { headers: { cookie } })).status, 401);
});
