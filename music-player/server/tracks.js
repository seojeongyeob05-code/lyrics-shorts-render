import crypto from 'node:crypto';
import { createReadStream } from 'node:fs';
import fs from 'node:fs/promises';
import path from 'node:path';
import { Router } from 'express';
import multer from 'multer';
import { parseFile } from 'music-metadata';

export const AUDIO_TYPES = new Map([
  ['.mp3', 'audio/mpeg'],
  ['.flac', 'audio/flac'],
  ['.m4a', 'audio/mp4'],
  ['.aac', 'audio/aac'],
  ['.ogg', 'audio/ogg'],
  ['.opus', 'audio/ogg'],
  ['.wav', 'audio/wav'],
  ['.webm', 'audio/webm'],
]);

const COVER_EXT = { 'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif' };

export function toTrackJson(row) {
  return {
    id: row.id,
    title: row.title,
    artist: row.artist,
    album: row.album,
    trackNo: row.track_no,
    discNo: row.disc_no,
    duration: row.duration,
    hasCover: Boolean(row.cover),
    hasLyrics: Boolean(row.lyrics),
    createdAt: row.created_at,
  };
}

// 브라우저가 multipart 파일명을 UTF-8로 보내도 latin1로 해석되는 경우가 있어 되돌린다.
// macOS는 한글을 자모 분리(NFD) 형태로 보내므로 NFC로 합쳐 검색·정렬이 되게 한다.
function decodeName(name) {
  const fixed = Buffer.from(name, 'latin1').toString('utf8');
  return (fixed.includes('�') ? name : fixed).normalize('NFC');
}

const tagText = (value) => value?.trim().normalize('NFC') || null;

// 파일 내용의 SHA-256. 같은 파일을 다시 올렸는지 확인하는 데 쓴다.
export async function hashFile(filePath) {
  const hash = crypto.createHash('sha256');
  for await (const chunk of createReadStream(filePath)) hash.update(chunk);
  return hash.digest('hex');
}

// 중복 검사 기능 이전에 올라간 곡의 해시를 백그라운드에서 채운다.
export async function backfillHashes(db, musicDir) {
  const missing = db.prepare('SELECT id, filename FROM tracks WHERE hash IS NULL').all();
  const update = db.prepare('UPDATE tracks SET hash = ? WHERE id = ?');
  for (const { id, filename } of missing) {
    try {
      update.run(await hashFile(path.join(musicDir, filename)), id);
    } catch {
      // 파일이 없거나 읽을 수 없으면 건너뛴다.
    }
  }
  return missing.length;
}

export const MAX_LYRICS = 100_000;

function lrcTimestamp(ms) {
  const cs = Math.round(ms / 10);
  const pad = (n) => String(n).padStart(2, '0');
  return `[${pad(Math.floor(cs / 6000))}:${pad(Math.floor(cs / 100) % 60)}.${pad(cs % 100)}]`;
}

// 파일 태그에 들어 있는 가사를 LRC 텍스트로 바꾼다. 싱크 가사가 있으면 그것을, 없으면 일반 가사를 쓴다.
export function lyricsFromTags(tags = []) {
  const synced = tags.find((t) => t.syncText?.length && t.timeStampFormat === 2); // 2 = 밀리초
  if (synced) return synced.syncText.map((l) => lrcTimestamp(l.timestamp ?? 0) + (l.text ?? '')).join('\n');
  const plain = tags.find((t) => t.text?.trim());
  return plain ? plain.text.trim().slice(0, MAX_LYRICS) : null;
}

async function readMetadata(filePath) {
  try {
    const { common, format } = await parseFile(filePath);
    return { common, duration: format.duration ?? null };
  } catch {
    return { common: {}, duration: null };
  }
}

export function createTracksRouter(db, config) {
  const { musicDir, coverDir } = config;
  const router = Router();

  const upload = multer({
    storage: multer.diskStorage({
      destination: musicDir,
      filename: (_req, file, cb) => cb(null, crypto.randomUUID() + path.extname(file.originalname).toLowerCase()),
    }),
    limits: { fileSize: config.maxUploadMb * 1024 * 1024, files: 100 },
    fileFilter: (req, file, cb) => {
      file.originalname = decodeName(file.originalname);
      const ok = AUDIO_TYPES.has(path.extname(file.originalname).toLowerCase());
      if (!ok) (req.rejected ??= []).push(file.originalname);
      cb(null, ok);
    },
  });

  const getTrack = (id) => db.prepare('SELECT * FROM tracks WHERE id = ?').get(Number(id));

  router.get('/', (_req, res) => {
    const rows = db.prepare(`
      SELECT * FROM tracks
      ORDER BY COALESCE(artist, '') COLLATE NOCASE, COALESCE(album, '') COLLATE NOCASE,
               COALESCE(disc_no, 0), COALESCE(track_no, 0), title COLLATE NOCASE
    `).all();
    res.json(rows.map(toTrackJson));
  });

  router.post('/', upload.array('files'), async (req, res) => {
    const insert = db.prepare(`
      INSERT INTO tracks (title, artist, album, track_no, disc_no, duration, filename, mime, size, cover, created_at, hash, lyrics)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const findByHash = db.prepare('SELECT id, title FROM tracks WHERE hash = ?');
    const added = [];
    const duplicates = [];
    for (const file of req.files ?? []) {
      const ext = path.extname(file.filename);
      // 내용이 같은 파일이 이미 있으면 새로 받은 파일은 지우고 건너뛴다 (같은 요청 안의 중복도 포함).
      const hash = await hashFile(file.path);
      const existing = findByHash.get(hash);
      if (existing) {
        await fs.rm(file.path, { force: true });
        duplicates.push({ name: file.originalname, existing: { id: existing.id, title: existing.title } });
        continue;
      }
      const { common, duration } = await readMetadata(file.path);

      let cover = null;
      const pic = common.picture?.[0];
      if (pic && COVER_EXT[pic.format]) {
        cover = path.basename(file.filename, ext) + COVER_EXT[pic.format];
        await fs.writeFile(path.join(coverDir, cover), pic.data);
      }

      const title = tagText(common.title) || path.basename(file.originalname, path.extname(file.originalname));
      const { lastInsertRowid } = insert.run(
        title,
        tagText(common.artist),
        tagText(common.album),
        common.track?.no ?? null,
        common.disk?.no ?? null,
        duration,
        file.filename,
        AUDIO_TYPES.get(ext),
        file.size,
        cover,
        Date.now(),
        hash,
        lyricsFromTags(common.lyrics),
      );
      added.push(toTrackJson(getTrack(lastInsertRowid)));
    }
    res.status(201).json({ added, duplicates, rejected: req.rejected ?? [] });
  });

  // 곡 정보 수정. 제목은 필수, 아티스트·앨범은 비우면 '알 수 없음'으로 돌아간다. 파일 태그는 건드리지 않는다.
  router.patch('/:id', (req, res) => {
    const track = getTrack(req.params.id);
    if (!track) return res.status(404).json({ error: '곡을 찾을 수 없습니다' });
    const fields = {};
    for (const key of ['title', 'artist', 'album']) {
      if (!(key in (req.body ?? {}))) continue;
      const value = req.body[key];
      if (value !== null && typeof value !== 'string') return res.status(400).json({ error: '값이 올바르지 않습니다' });
      const text = tagText(value ?? '');
      if (text && text.length > 200) return res.status(400).json({ error: '200자를 넘을 수 없습니다' });
      fields[key] = text;
    }
    if ('title' in fields && !fields.title) return res.status(400).json({ error: '제목은 비울 수 없습니다' });
    if (!Object.keys(fields).length) return res.status(400).json({ error: '바꿀 내용이 없습니다' });
    const sets = Object.keys(fields).map((k) => `${k} = ?`).join(', ');
    db.prepare(`UPDATE tracks SET ${sets} WHERE id = ?`).run(...Object.values(fields), track.id);
    res.json(toTrackJson(getTrack(track.id)));
  });

  router.get('/:id/lyrics', (req, res) => {
    const track = getTrack(req.params.id);
    if (!track) return res.status(404).json({ error: '곡을 찾을 수 없습니다' });
    res.json({ lyrics: track.lyrics ?? null });
  });

  // 가사 저장. 빈 값이나 null이면 가사를 지운다.
  router.put('/:id/lyrics', (req, res) => {
    const track = getTrack(req.params.id);
    if (!track) return res.status(404).json({ error: '곡을 찾을 수 없습니다' });
    const value = req.body?.lyrics;
    if (value != null && typeof value !== 'string') return res.status(400).json({ error: '가사는 문자열이어야 합니다' });
    const lyrics = value?.replace(/\r\n?/g, '\n').trim().normalize('NFC') || null;
    if (lyrics && lyrics.length > MAX_LYRICS) return res.status(400).json({ error: '가사가 너무 깁니다' });
    db.prepare('UPDATE tracks SET lyrics = ? WHERE id = ?').run(lyrics, track.id);
    res.json(toTrackJson(getTrack(track.id)));
  });

  router.delete('/:id', async (req, res) => {
    const track = getTrack(req.params.id);
    if (!track) return res.status(404).json({ error: '곡을 찾을 수 없습니다' });
    db.prepare('DELETE FROM tracks WHERE id = ?').run(track.id);
    await fs.rm(path.join(musicDir, track.filename), { force: true });
    if (track.cover) await fs.rm(path.join(coverDir, track.cover), { force: true });
    res.status(204).end();
  });

  // sendFile이 Range 요청을 처리하므로 탐색바로 구간 이동이 된다.
  router.get('/:id/stream', (req, res, next) => {
    const track = getTrack(req.params.id);
    if (!track) return res.status(404).json({ error: '곡을 찾을 수 없습니다' });
    res.sendFile(track.filename, {
      root: musicDir,
      headers: { 'Content-Type': track.mime, 'Cache-Control': 'private, max-age=86400' },
    }, (err) => err && !res.headersSent && next(err));
  });

  router.get('/:id/cover', (req, res, next) => {
    const track = getTrack(req.params.id);
    if (!track?.cover) return res.status(404).end();
    res.sendFile(track.cover, {
      root: coverDir,
      headers: { 'Cache-Control': 'private, max-age=604800' },
    }, (err) => err && !res.headersSent && next(err));
  });

  return router;
}
