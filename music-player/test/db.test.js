import { test } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { openDb } from '../server/db.js';
import { backfillHashes } from '../server/tracks.js';

test('예전 DB를 열면 hash 컬럼이 추가되고 기존 곡의 해시를 채운다', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-db-'));
  try {
    const file = path.join(dir, 'library.db');
    // hash 컬럼이 생기기 전의 스키마
    const old = new DatabaseSync(file);
    old.exec(`CREATE TABLE tracks (
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, artist TEXT, album TEXT, track_no INTEGER, disc_no INTEGER,
      duration REAL, filename TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, cover TEXT, created_at INTEGER NOT NULL)`);
    const insert = old.prepare("INSERT INTO tracks (title, filename, mime, size, created_at) VALUES (?, ?, 'audio/wav', 4, 0)");
    insert.run('있는 파일', 'a.wav');
    insert.run('사라진 파일', 'missing.wav');
    old.close();
    fs.writeFileSync(path.join(dir, 'a.wav'), 'abcd');

    const db = openDb(file);
    const columns = db.prepare('PRAGMA table_info(tracks)').all().map((c) => c.name);
    for (const name of ['hash', 'lyrics', 'play_count', 'last_played_at']) assert.ok(columns.includes(name), name);
    assert.equal(db.prepare('SELECT play_count FROM tracks WHERE id = 1').get().play_count, 0);
    assert.equal(await backfillHashes(db, dir), 2);

    const rows = db.prepare('SELECT title, hash FROM tracks ORDER BY id').all();
    assert.equal(rows[0].hash, crypto.createHash('sha256').update('abcd').digest('hex'));
    assert.equal(rows[1].hash, null);
    db.close();

    // 다시 열어도 문제없다 (마이그레이션은 한 번만 적용)
    openDb(file).close();
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
