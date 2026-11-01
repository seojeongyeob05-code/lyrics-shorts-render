import crypto from 'node:crypto';
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
      INSERT INTO tracks (title, artist, album, track_no, disc_no, duration, filename, mime, size, cover, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const added = [];
    for (const file of req.files ?? []) {
      const ext = path.extname(file.filename);
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
      );
      added.push(toTrackJson(getTrack(lastInsertRowid)));
    }
    res.status(201).json({ added, rejected: req.rejected ?? [] });
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
