import { test, after } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import { checkNode } from '../server/node-check.js';
import { lanUrls, createApp, loadConfig } from '../server/index.js';

test('Node.js 22.13 이상만 통과하고, 낮으면 한국어로 안내한다', () => {
  for (const v of ['22.13.0', '22.22.0', '23.0.0', '24.1.2']) assert.equal(checkNode(v).ok, true, v);
  for (const v of ['22.12.0', '20.18.1', '18.20.8']) {
    const r = checkNode(v);
    assert.equal(r.ok, false, v);
    assert.match(r.message, new RegExp(`Node\\.js ${v.replace(/\./g, '\\.')} 버전에서는`));
    assert.match(r.message, /22\.13 이상이 필요합니다/);
  }
});

test('같은 와이파이에서 접속할 주소: 내부(127.0.0.1)와 IPv6는 빼고 IPv4만', () => {
  const interfaces = {
    lo: [{ address: '127.0.0.1', family: 'IPv4', internal: true }, { address: '::1', family: 'IPv6', internal: true }],
    wlan0: [{ address: '192.168.0.12', family: 'IPv4', internal: false }, { address: 'fe80::1', family: 'IPv6', internal: false }],
    eth0: [{ address: '10.0.0.5', family: 4, internal: false }], // 예전 Node는 family가 숫자
  };
  assert.deepEqual(lanUrls(3000, interfaces), ['http://192.168.0.12:3000', 'http://10.0.0.5:3000']);
  assert.deepEqual(lanUrls(3000, { lo: interfaces.lo }), []);
});

test('휴대폰 홈 화면에 추가: manifest와 아이콘을 로그인 없이 제공한다', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-pwa-'));
  const { app } = createApp(loadConfig({ DATA_DIR: dir, AUTO_BACKUP_KEEP: '0' }));
  const server = await new Promise((resolve) => { const s = app.listen(0, () => resolve(s)); });
  after(() => { server.close(); fs.rmSync(dir, { recursive: true, force: true }); });
  const base = `http://127.0.0.1:${server.address().port}/`;

  const res = await fetch(base + 'manifest.webmanifest');
  assert.equal(res.status, 200);
  assert.match(res.headers.get('content-type'), /^application\/manifest\+json/);
  const manifest = await res.json();
  assert.equal(manifest.display, 'standalone');
  assert.equal(manifest.start_url, '/');
  assert.ok(manifest.icons.some((i) => i.sizes === '192x192') && manifest.icons.some((i) => i.sizes === '512x512'));
  assert.ok(manifest.icons.some((i) => i.purpose === 'maskable'));
  for (const icon of manifest.icons) {
    const r = await fetch(base + icon.src);
    assert.equal(r.status, 200, icon.src);
    assert.equal(r.headers.get('content-type').split(';')[0], icon.type, icon.src);
  }
  const html = await (await fetch(base)).text();
  assert.match(html, /<link rel="manifest" href="manifest\.webmanifest">/);
  assert.match(html, /<link rel="apple-touch-icon" href="icons\/apple-touch-icon\.png">/);
});
