import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createApp, loadConfig } from '../server/index.js';

function makeWav(seconds, rate = 8000) {
  const data = rate * seconds * 2;
  const buf = Buffer.alloc(44 + data);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + data, 4); buf.write('WAVEfmt ', 8);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
  buf.write('data', 36); buf.writeUInt32LE(data, 40);
  return buf;
}

const cleanups = [];
after(() => cleanups.forEach((fn) => fn()));

// 데이터 폴더가 따로인 서버 하나를 띄우고 로그인까지 해 둔다.
async function startServer() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-backup-'));
  const { app } = createApp(loadConfig({ DATA_DIR: dir }));
  const server = await new Promise((resolve) => { const s = app.listen(0, () => resolve(s)); });
  cleanups.push(() => { server.close(); fs.rmSync(dir, { recursive: true, force: true }); });
  const base = `http://127.0.0.1:${server.address().port}`;
  let cookie = '';
  const call = async (method, url, body, { raw } = {}) => {
    const isForm = body instanceof FormData;
    const res = await fetch(base + url, {
      method,
      headers: { cookie, ...(body && !isForm ? { 'Content-Type': 'application/json' } : {}) },
      body: isForm ? body : raw ?? (body ? JSON.stringify(body) : undefined),
    });
    const set = res.headers.get('set-cookie');
    if (set) cookie = set.split(';')[0];
    return res;
  };
  await call('POST', '/api/auth/setup', { username: 'me', password: 'password123' });
  const upload = async (files) => {
    const form = new FormData();
    for (const [name, seconds] of files) form.append('files', new Blob([makeWav(seconds)], { type: 'audio/wav' }), name);
    return (await (await call('POST', '/api/tracks', form)).json()).added;
  };
  return { call, upload, logout: () => { cookie = ''; } };
}

test('백업 → 데이터를 잃음 → 음원을 다시 올리고 복원', async () => {
  // 원래 서버: 곡 정보 수정, 가사, 들은 횟수, 플레이리스트
  const old = await startServer();
  const [a, b] = await old.upload([['a.wav', 1], ['b.wav', 2]]);
  await old.call('PATCH', `/api/tracks/${a.id}`, { title: '봄날', artist: '정엽', album: '봄' });
  await old.call('PUT', `/api/tracks/${a.id}/lyrics`, { lyrics: '[00:00.50]봄이 오면' });
  await old.call('POST', `/api/tracks/${b.id}/plays`);
  await old.call('POST', `/api/tracks/${b.id}/plays`);
  for (const [name, ids] of [['출근길', [a.id, b.id, a.id]], ['잠들기 전', [b.id]]]) {
    const pl = await (await old.call('POST', '/api/playlists', { name })).json();
    await old.call('POST', `/api/playlists/${pl.id}/tracks`, { trackIds: ids });
  }
  const res = await old.call('GET', '/api/backup');
  assert.equal(res.status, 200);
  assert.match(res.headers.get('content-disposition'), /attachment; filename="my-music-backup-\d{4}-\d{2}-\d{2}\.json"/);
  const backup = await res.json();
  assert.equal(backup.format, 'my-music-backup');
  assert.equal(backup.tracks.length, 2);
  assert.deepEqual(backup.playlists.map((p) => p.tracks.length), [3, 1]);
  backup.tracks.push({ hash: 'nope', title: '없는 곡' });

  // 새 서버: 같은 음원을 다시 올림 (파일 이름은 달라도 내용이 같음). b에는 새로 가사를 넣어 둠
  const fresh = await startServer();
  const [a2, b2] = await fresh.upload([['다른 이름 a.wav', 1], ['다른 이름 b.wav', 2]]);
  await fresh.call('PUT', `/api/tracks/${b2.id}/lyrics`, { lyrics: '새로 넣은 가사' });
  await fresh.call('POST', '/api/playlists', { name: '잠들기 전' }); // 이미 있는 이름

  const restored = await (await fresh.call('POST', '/api/backup/restore', backup)).json();
  assert.deepEqual(restored, {
    tracks: { restored: 2, missing: 1 },
    playlists: { created: [{ name: '출근길', trackCount: 3, missing: 0 }], skipped: ['잠들기 전'] },
  });

  const tracks = await (await fresh.call('GET', '/api/tracks')).json();
  const ra = tracks.find((t) => t.id === a2.id);
  const rb = tracks.find((t) => t.id === b2.id);
  assert.deepEqual([ra.title, ra.artist, ra.album, ra.hasLyrics], ['봄날', '정엽', '봄', true]);
  assert.equal(rb.playCount, 2);
  assert.equal((await (await fresh.call('GET', `/api/tracks/${b2.id}/lyrics`)).json()).lyrics, '새로 넣은 가사'); // 백업에 없던 가사는 지우지 않음
  const playlists = await (await fresh.call('GET', '/api/playlists')).json();
  const commute = playlists.find((p) => p.name === '출근길');
  const detail = await (await fresh.call('GET', `/api/playlists/${commute.id}`)).json();
  assert.deepEqual(detail.tracks.map((t) => t.id), [a2.id, b2.id, a2.id]);

  // 같은 백업을 한 번 더 복원해도 들은 횟수가 늘거나 플레이리스트가 중복되지 않음
  const again = await (await fresh.call('POST', '/api/backup/restore', backup)).json();
  assert.deepEqual(again.playlists, { created: [], skipped: ['출근길', '잠들기 전'] });
  assert.equal((await (await fresh.call('GET', '/api/tracks')).json()).find((t) => t.id === b2.id).playCount, 2);
});

test('복원: 잘못된 파일 거부, 1MB가 넘는 백업도 받음, 로그인 필요', async () => {
  const s = await startServer();
  assert.equal((await s.call('POST', '/api/backup/restore', { hello: 1 })).status, 400);
  assert.equal((await s.call('POST', '/api/backup/restore', { format: 'my-music-backup', version: 99, tracks: [], playlists: [] })).status, 400);
  assert.equal((await s.call('POST', '/api/backup/restore', null, { raw: '{oops' })).status, 400);

  const big = { format: 'my-music-backup', version: 1, tracks: Array.from({ length: 3000 }, (_, i) => ({ hash: `h${i}`, title: 'x'.repeat(500) })), playlists: [] };
  const res = await s.call('POST', '/api/backup/restore', big);
  assert.equal(res.status, 200);
  assert.deepEqual((await res.json()).tracks, { restored: 0, missing: 3000 });
  // 다른 API의 1MB 한도는 그대로
  assert.equal((await s.call('PUT', '/api/tracks/1/lyrics', { lyrics: 'x'.repeat(1_100_000) })).status, 413);

  s.logout();
  assert.equal((await s.call('GET', '/api/backup')).status, 401);
  assert.equal((await s.call('POST', '/api/backup/restore', { format: 'my-music-backup', tracks: [], playlists: [] })).status, 401);
});
