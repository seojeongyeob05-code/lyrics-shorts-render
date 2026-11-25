import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkNode } from '../server/node-check.js';
import { lanUrls } from '../server/index.js';

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
