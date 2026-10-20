import fs from 'node:fs';
import path from 'node:path';
import express from 'express';
import multer from 'multer';
import { openDb } from './db.js';
import { createAuth } from './auth.js';
import { createTracksRouter } from './tracks.js';
import { createPlaylistsRouter } from './playlists.js';

const ROOT = path.resolve(import.meta.dirname, '..');

export function loadConfig(env = process.env) {
  const dataDir = path.resolve(env.DATA_DIR || path.join(ROOT, 'data'));
  return {
    port: Number(env.PORT) || 3000,
    dataDir,
    musicDir: path.join(dataDir, 'music'),
    coverDir: path.join(dataDir, 'covers'),
    maxUploadMb: Number(env.MAX_UPLOAD_MB) || 200,
    secureCookie: env.COOKIE_SECURE === 'true',
    trustProxy: env.TRUST_PROXY === 'true',
    sessionDays: 30,
  };
}

export function createApp(config) {
  fs.mkdirSync(config.musicDir, { recursive: true });
  fs.mkdirSync(config.coverDir, { recursive: true });
  const db = openDb(path.join(config.dataDir, 'library.db'));
  const auth = createAuth(db, config);
  auth.purgeExpired();

  const app = express();
  app.disable('x-powered-by');
  if (config.trustProxy) app.set('trust proxy', 1);

  app.use(express.json({ limit: '1mb' }));
  app.use(auth.loadUser);

  app.use('/api/auth', auth.router);
  app.use('/api/tracks', auth.requireAuth, createTracksRouter(db, config));
  app.use('/api/playlists', auth.requireAuth, createPlaylistsRouter(db));
  app.use('/api', (_req, res) => res.status(404).json({ error: '없는 API입니다' }));

  app.use(express.static(path.join(ROOT, 'public')));

  app.use((err, _req, res, _next) => {
    if (err instanceof multer.MulterError) {
      const message = err.code === 'LIMIT_FILE_SIZE'
        ? `파일 하나는 ${config.maxUploadMb}MB를 넘을 수 없습니다`
        : `업로드 오류: ${err.message}`;
      return res.status(err.code === 'LIMIT_FILE_SIZE' ? 413 : 400).json({ error: message });
    }
    console.error(err);
    res.status(err.status || 500).json({ error: '서버 오류가 발생했습니다' });
  });

  return { app, db, purgeExpired: auth.purgeExpired };
}

if (process.argv[1] === import.meta.filename) {
  const config = loadConfig();
  const { app, purgeExpired } = createApp(config);
  setInterval(purgeExpired, 60 * 60 * 1000).unref();
  app.listen(config.port, () => {
    console.log(`음악 서버 실행 중: http://localhost:${config.port}  (데이터: ${config.dataDir})`);
  });
}
