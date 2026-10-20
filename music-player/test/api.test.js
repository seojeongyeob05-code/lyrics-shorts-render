import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createApp, loadConfig } from '../server/index.js';

// 1초짜리 무음 WAV (8kHz, 16bit, mono)
function makeWav(seconds = 1, rate = 8000) {
  const data = rate * seconds * 2;
  const buf = Buffer.alloc(44 + data);
  buf.write('RIFF', 0);
  buf.writeUInt32LE(36 + data, 4);
  buf.write('WAVEfmt ', 8);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24);
  buf.writeUInt32LE(rate * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write('data', 36);
  buf.writeUInt32LE(data, 40);
  return buf;
}

let server;
let base;
let dataDir;
let cookie = '';

async function call(method, url, { body, form, headers = {} } = {}) {
  const res = await fetch(base + url, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), cookie, ...headers },
    body: form ?? (body ? JSON.stringify(body) : undefined),
  });
  const setCookie = res.headers.get('set-cookie');
  if (setCookie) cookie = setCookie.split(';')[0];
  return res;
}

before(async () => {
  dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-test-'));
  const { app } = createApp(loadConfig({ DATA_DIR: dataDir }));
  await new Promise((resolve) => { server = app.listen(0, resolve); });
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => {
  server?.close();
  fs.rmSync(dataDir, { recursive: true, force: true });
});

test('계정 설정 전에는 API가 막혀 있고 최초 계정만 만들 수 있다', async () => {
  assert.equal((await call('GET', '/api/tracks')).status, 401);
  const status = await (await call('GET', '/api/auth/status')).json();
  assert.equal(status.setupRequired, true);

  assert.equal((await call('POST', '/api/auth/setup', { body: { username: 'me', password: 'short' } })).status, 400);
  const res = await call('POST', '/api/auth/setup', { body: { username: 'me', password: 'password123' } });
  assert.equal(res.status, 201);
  assert.ok(cookie.startsWith('mp_session='));

  const saved = cookie;
  cookie = '';
  assert.equal((await call('POST', '/api/auth/setup', { body: { username: 'other', password: 'password123' } })).status, 403);
  cookie = saved;
});

test('로그아웃 후 잘못된 비밀번호는 거부되고 올바르면 로그인된다', async () => {
  assert.equal((await call('POST', '/api/auth/logout')).status, 204);
  cookie = '';
  assert.equal((await call('POST', '/api/auth/login', { body: { username: 'me', password: 'wrong-password' } })).status, 401);
  assert.equal((await call('POST', '/api/auth/login', { body: { username: 'me', password: 'password123' } })).status, 200);
  const status = await (await call('GET', '/api/auth/status')).json();
  assert.equal(status.user.username, 'me');
});

let trackId;

test('업로드: 오디오만 받고 한글 파일명을 제목으로 쓴다', async () => {
  const form = new FormData();
  form.append('files', new Blob([makeWav()], { type: 'audio/wav' }), '봄날의 노래.wav');
  form.append('files', new Blob(['not audio'], { type: 'text/plain' }), 'memo.txt');
  const res = await call('POST', '/api/tracks', { form });
  assert.equal(res.status, 201);
  const { added, rejected } = await res.json();
  assert.equal(added.length, 1);
  assert.deepEqual(rejected, ['memo.txt']);
  assert.equal(added[0].title, '봄날의 노래');
  assert.ok(Math.abs(added[0].duration - 1) < 0.01);
  trackId = added[0].id;

  const list = await (await call('GET', '/api/tracks')).json();
  assert.equal(list.length, 1);
});

test('스트리밍은 Range 요청을 지원한다', async () => {
  const full = await call('GET', `/api/tracks/${trackId}/stream`);
  assert.equal(full.status, 200);
  assert.equal(full.headers.get('content-type'), 'audio/wav');
  assert.equal((await full.arrayBuffer()).byteLength, 44 + 16000);

  const part = await call('GET', `/api/tracks/${trackId}/stream`, { headers: { Range: 'bytes=0-99' } });
  assert.equal(part.status, 206);
  assert.equal((await part.arrayBuffer()).byteLength, 100);
});

test('플레이리스트: 추가, 순서 변경, 제거', async () => {
  const pl = await (await call('POST', '/api/playlists', { body: { name: '출근길' } })).json();
  assert.equal((await call('POST', `/api/playlists/${pl.id}/tracks`, { body: { trackIds: [trackId, trackId] } })).status, 201);
  assert.equal((await call('POST', `/api/playlists/${pl.id}/tracks`, { body: { trackIds: [9999] } })).status, 400);

  let detail = await (await call('GET', `/api/playlists/${pl.id}`)).json();
  assert.equal(detail.tracks.length, 2);
  const [a, b] = detail.tracks.map((t) => t.entryId);

  assert.equal((await call('PUT', `/api/playlists/${pl.id}/order`, { body: { entryIds: [b, a] } })).status, 204);
  assert.equal((await call('PUT', `/api/playlists/${pl.id}/order`, { body: { entryIds: [b] } })).status, 400);
  detail = await (await call('GET', `/api/playlists/${pl.id}`)).json();
  assert.deepEqual(detail.tracks.map((t) => t.entryId), [b, a]);

  assert.equal((await call('DELETE', `/api/playlists/${pl.id}/tracks/${b}`)).status, 204);
  const lists = await (await call('GET', '/api/playlists')).json();
  assert.equal(lists[0].trackCount, 1);
});

test('곡을 삭제하면 파일과 플레이리스트 항목도 사라진다', async () => {
  assert.equal((await call('DELETE', `/api/tracks/${trackId}`)).status, 204);
  assert.equal((await call('GET', `/api/tracks/${trackId}/stream`)).status, 404);
  assert.deepEqual(fs.readdirSync(path.join(dataDir, 'music')), []);
  const lists = await (await call('GET', '/api/playlists')).json();
  assert.equal(lists[0].trackCount, 0);
});
