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
  return { call, upload, dir, logout: () => { cookie = ''; } };
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

test('자동 백업: 하루 한 번, 최근 N개만 보관, 다른 파일은 건드리지 않음', async () => {
  const { openDb } = await import('../server/db.js');
  const { runAutoBackup, localDate } = await import('../server/backup.js');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-auto-'));
  cleanups.push(() => fs.rmSync(dir, { recursive: true, force: true }));
  const db = openDb(path.join(dir, 'library.db'));
  db.prepare("INSERT INTO users (username, password_hash, created_at) VALUES ('me', 'x', 0)").run();
  db.prepare("INSERT INTO tracks (title, filename, mime, size, created_at, hash, lyrics) VALUES ('곡', 'a.wav', 'audio/wav', 1, 0, 'h1', '[00:01.00]가사')").run();
  db.prepare("INSERT INTO playlists (user_id, name, created_at) VALUES (1, '목록', 0)").run();
  db.prepare('INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (1, 1, 0)').run();

  const backupDir = path.join(dir, 'backups');
  const userDir = path.join(backupDir, 'user-1');
  const day = (n) => new Date(2026, 10, n, 12).getTime(); // 2026-11-n 낮 12시 (서버 시간)

  const first = await runAutoBackup(db, backupDir, { keep: 7, now: day(1) });
  assert.deepEqual(first.map((f) => path.basename(f)), ['my-music-backup-2026-11-01.json']);
  const saved = JSON.parse(fs.readFileSync(first[0], 'utf8'));
  assert.equal(saved.format, 'my-music-backup');
  assert.deepEqual(saved.tracks.map((t) => [t.hash, t.lyrics]), [['h1', '[00:01.00]가사']]);
  assert.deepEqual(saved.playlists, [{ name: '목록', tracks: ['h1'] }]);

  // 같은 날 다시 돌면 건너뜀
  assert.deepEqual(await runAutoBackup(db, backupDir, { keep: 7, now: day(1) + 3600_000 }), []);

  fs.writeFileSync(path.join(userDir, 'my-notes.txt'), '직접 둔 파일');
  for (let n = 2; n <= 10; n++) await runAutoBackup(db, backupDir, { keep: 7, now: day(n) });
  const files = fs.readdirSync(userDir).sort();
  assert.deepEqual(files, [
    ...[4, 5, 6, 7, 8, 9].map((n) => `my-music-backup-2026-11-${String(n).padStart(2, '0')}.json`),
    'my-music-backup-2026-11-10.json',
    'my-notes.txt',
  ]);
  assert.ok(!files.some((f) => f.endsWith('.tmp')));

  // 0이면 끔
  assert.deepEqual(await runAutoBackup(db, backupDir, { keep: 0, now: day(11) }), []);
  assert.ok(!fs.existsSync(path.join(userDir, 'my-music-backup-2026-11-11.json')));
  assert.equal(localDate(day(3)), '2026-11-03');
  db.close();
});

test('자동 백업 목록과 바로 복원, 다른 경로는 읽지 못함', async () => {
  const s = await startServer();
  const [a] = await s.upload([['a.wav', 1]]);
  assert.deepEqual(await (await s.call('GET', '/api/backup/auto')).json(), []); // 아직 없음

  // 그제와 어제의 자동 백업이 있다고 치고 파일을 둔다 (어제 것은 가사가 있음)
  await s.call('PUT', `/api/tracks/${a.id}/lyrics`, { lyrics: '[00:00.10]어제 가사' });
  const yesterday = await (await s.call('GET', '/api/backup')).json();
  const userDir = path.join(s.dir, 'backups', 'user-1');
  fs.mkdirSync(userDir, { recursive: true });
  fs.writeFileSync(path.join(userDir, 'my-music-backup-2026-11-18.json'), JSON.stringify({ ...yesterday, tracks: [] }));
  fs.writeFileSync(path.join(userDir, 'my-music-backup-2026-11-19.json'), JSON.stringify(yesterday));
  fs.writeFileSync(path.join(userDir, 'notes.txt'), '목록에 안 나와야 함');
  fs.writeFileSync(path.join(s.dir, 'secret.json'), JSON.stringify(yesterday));

  const list = await (await s.call('GET', '/api/backup/auto')).json();
  assert.deepEqual(list.map((b) => b.date), ['2026-11-19', '2026-11-18']); // 최신순
  assert.ok(list.every((b) => b.size > 0 && b.name.startsWith('my-music-backup-')));

  // 가사를 잃은 뒤 어제 자동 백업으로 복원
  await s.call('PUT', `/api/tracks/${a.id}/lyrics`, { lyrics: null });
  const res = await s.call('POST', '/api/backup/auto/my-music-backup-2026-11-19.json/restore');
  assert.equal(res.status, 200);
  assert.deepEqual((await res.json()).tracks, { restored: 1, missing: 0 });
  assert.equal((await (await s.call('GET', `/api/tracks/${a.id}/lyrics`)).json()).lyrics, '[00:00.10]어제 가사');

  assert.equal((await s.call('POST', '/api/backup/auto/my-music-backup-2026-01-01.json/restore')).status, 404);
  for (const name of ['notes.txt', '..%2F..%2Fsecret.json', '..%2Fsecret.json', 'my-music-backup-2026-11-19.json%00']) {
    assert.equal((await s.call('POST', `/api/backup/auto/${name}/restore`)).status, 400, name);
  }
  fs.writeFileSync(path.join(userDir, 'my-music-backup-2026-11-17.json'), '{broken');
  assert.equal((await s.call('POST', '/api/backup/auto/my-music-backup-2026-11-17.json/restore')).status, 400);

  s.logout();
  assert.equal((await s.call('GET', '/api/backup/auto')).status, 401);
});
