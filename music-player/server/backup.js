import fs from 'node:fs/promises';
import path from 'node:path';
import express, { Router } from 'express';
import { transaction } from './db.js';

// 라이브러리 백업: 음원 파일은 빼고, 사용자가 직접 만든 정보(곡 정보 수정, 가사, 들은 횟수, 플레이리스트)를 담는다.
// 곡은 파일 내용 해시로 가리키므로, 음원을 다시 올린 뒤 복원해도 같은 곡을 찾는다.
export const BACKUP_FORMAT = 'my-music-backup';
export const BACKUP_VERSION = 1;
const MAX_BACKUP = '20mb';

const textOrNull = (v, max) => (typeof v === 'string' && v.trim() ? v.trim().normalize('NFC').slice(0, max) : null);

export function buildBackup(db, userId, now = Date.now()) {
  const tracks = db.prepare(`
      SELECT hash, title, artist, album, lyrics, play_count, last_played_at FROM tracks
      WHERE hash IS NOT NULL ORDER BY id
    `).all().map((t) => ({
      hash: t.hash,
      title: t.title,
      artist: t.artist,
      album: t.album,
      lyrics: t.lyrics,
      playCount: t.play_count,
      lastPlayedAt: t.last_played_at,
    }));
  const playlists = db.prepare('SELECT id, name FROM playlists WHERE user_id = ? ORDER BY created_at').all(userId)
    .map((p) => ({
      name: p.name,
      tracks: db.prepare(`
        SELECT t.hash FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id
        WHERE pt.playlist_id = ? AND t.hash IS NOT NULL ORDER BY pt.position, pt.id
      `).all(p.id).map((r) => r.hash),
    }));
  return { format: BACKUP_FORMAT, version: BACKUP_VERSION, exportedAt: now, tracks, playlists };
}

// 서버 시간 기준 날짜 (YYYY-MM-DD)
export function localDate(now = Date.now()) {
  const d = new Date(now);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const BACKUP_FILE = /^my-music-backup-(\d{4}-\d{2}-\d{2})\.json$/;

// 자동 백업: 계정마다 backups/user-<id>/ 에 하루 하나씩 저장하고 최근 keep개만 남긴다.
// 오늘 파일이 이미 있으면 건너뛴다. 임시 파일에 쓴 뒤 이름을 바꿔, 쓰다 끊겨도 깨진 백업이 남지 않는다.
export async function runAutoBackup(db, backupDir, { keep, now = Date.now() } = {}) {
  const written = [];
  if (!keep) return written;
  for (const { id } of db.prepare('SELECT id FROM users ORDER BY id').all()) {
    const dir = path.join(backupDir, `user-${id}`);
    await fs.mkdir(dir, { recursive: true });
    const file = path.join(dir, `my-music-backup-${localDate(now)}.json`);
    const exists = await fs.access(file).then(() => true, () => false);
    if (!exists) {
      const tmp = `${file}.tmp`;
      await fs.writeFile(tmp, JSON.stringify(buildBackup(db, id, now)));
      await fs.rename(tmp, file);
      written.push(file);
    }
    const old = (await fs.readdir(dir)).filter((f) => BACKUP_FILE.test(f)).sort().slice(0, -keep);
    await Promise.all(old.map((f) => fs.rm(path.join(dir, f), { force: true })));
  }
  return written;
}

export function createBackupRouter(db) {
  const router = Router();

  router.get('/', (req, res) => {
    res.set('Content-Disposition', `attachment; filename="my-music-backup-${localDate()}.json"`);
    res.json(buildBackup(db, req.user.id));
  });

  // 복원: 지금 라이브러리에 있는 곡에만 적용한다. 백업에 비어 있는 값(가사 등)은 지금 값을 지우지 않고,
// 들은 횟수는 더 큰 쪽을 남긴다. 같은 이름의 플레이리스트가 이미 있으면 건너뛴다.
  router.post('/restore', express.json({ limit: MAX_BACKUP }), (req, res) => {
    const backup = req.body;
    if (backup?.format !== BACKUP_FORMAT || !Array.isArray(backup.tracks) || !Array.isArray(backup.playlists)) {
      return res.status(400).json({ error: '이 앱의 백업 파일이 아닙니다' });
    }
    if (backup.version > BACKUP_VERSION) {
      return res.status(400).json({ error: '더 새로운 버전에서 만든 백업이라 복원할 수 없습니다' });
    }

    const idByHash = new Map(db.prepare('SELECT id, hash FROM tracks WHERE hash IS NOT NULL').all().map((r) => [r.hash, r.id]));
    const updateTrack = db.prepare(`
      UPDATE tracks SET title = ?, artist = COALESCE(?, artist), album = COALESCE(?, album), lyrics = COALESCE(?, lyrics),
        play_count = MAX(play_count, ?), last_played_at = MAX(COALESCE(last_played_at, 0), ?)
      WHERE id = ?
    `);
    const existingNames = new Set(db.prepare('SELECT name FROM playlists WHERE user_id = ?').all(req.user.id).map((p) => p.name));
    const insertPlaylist = db.prepare('INSERT INTO playlists (user_id, name, created_at) VALUES (?, ?, ?)');
    const insertEntry = db.prepare('INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)');

    const result = {
      tracks: { restored: 0, missing: 0 },
      playlists: { created: [], skipped: [] },
    };
    transaction(db, () => {
      for (const t of backup.tracks) {
        const id = idByHash.get(t?.hash);
        const title = textOrNull(t?.title, 200);
        if (!id || !title) { result.tracks.missing++; continue; }
        const lastPlayed = Number.isFinite(t.lastPlayedAt) ? t.lastPlayedAt : 0;
        updateTrack.run(title, textOrNull(t.artist, 200), textOrNull(t.album, 200), textOrNull(t.lyrics, 100_000),
          Math.max(0, Math.floor(Number(t.playCount) || 0)), lastPlayed, id);
        result.tracks.restored++;
      }
      for (const p of backup.playlists) {
        const name = textOrNull(p?.name, 100);
        if (!name) continue;
        if (existingNames.has(name)) { result.playlists.skipped.push(name); continue; }
        const ids = (Array.isArray(p.tracks) ? p.tracks : []).map((h) => idByHash.get(h)).filter(Boolean);
        const { lastInsertRowid } = insertPlaylist.run(req.user.id, name, Date.now());
        ids.forEach((id, i) => insertEntry.run(lastInsertRowid, id, i));
        existingNames.add(name);
        result.playlists.created.push({ name, trackCount: ids.length, missing: (p.tracks?.length ?? 0) - ids.length });
      }
    });
    res.json(result);
  });

  return router;
}
