import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import express from 'express';
import multer from 'multer';
import { openDb } from './db.js';
import { createAuth } from './auth.js';
import { backfillHashes, createTracksRouter } from './tracks.js';
import { createPlaylistsRouter } from './playlists.js';
import { createBackupRouter, runAutoBackup } from './backup.js';

const ROOT = path.resolve(import.meta.dirname, '..');

export function loadConfig(env = process.env) {
  const dataDir = path.resolve(env.DATA_DIR || path.join(ROOT, 'data'));
  return {
    port: Number(env.PORT) || 3000,
    dataDir,
    musicDir: path.join(dataDir, 'music'),
    coverDir: path.join(dataDir, 'covers'),
    maxUploadMb: Number(env.MAX_UPLOAD_MB) || 200,
    maxUploadFiles: 100, // 요청 하나에 담을 수 있는 파일 수. 브라우저는 더 작게 나눠 보낸다.
    secureCookie: env.COOKIE_SECURE === 'true',
    trustProxy: env.TRUST_PROXY === 'true',
    sessionDays: 30,
    backupDir: path.join(dataDir, 'backups'),
    autoBackupKeep: env.AUTO_BACKUP_KEEP === undefined ? 7 : Math.max(0, Number(env.AUTO_BACKUP_KEEP) || 0),
  };
}

export function createApp(config) {
  fs.mkdirSync(config.musicDir, { recursive: true });
  fs.mkdirSync(config.coverDir, { recursive: true });
  const db = openDb(path.join(config.dataDir, 'library.db'));
  // 첫 계정을 만들면 바로 첫 자동 백업을 남긴다 (매시간 확인을 기다리지 않도록)
  const auth = createAuth(db, config, {
    onUserCreated: () => runAutoBackup(db, config.backupDir, { keep: config.autoBackupKeep }),
  });
  auth.purgeExpired();

  const app = express();
  app.disable('x-powered-by');
  if (config.trustProxy) app.set('trust proxy', 1);

  // 백업 복원은 내용이 커서 자기 라우터에서 더 큰 한도로 읽는다.
  const json = express.json({ limit: '1mb' });
  app.use((req, res, next) => (req.path === '/api/backup/restore' ? next() : json(req, res, next)));
  app.use(auth.loadUser);

  app.use('/api/auth', auth.router);
  app.use('/api/tracks', auth.requireAuth, createTracksRouter(db, config));
  app.use('/api/playlists', auth.requireAuth, createPlaylistsRouter(db));
  app.use('/api/backup', auth.requireAuth, createBackupRouter(db, config));
  app.use('/api', (_req, res) => res.status(404).json({ error: '없는 API입니다' }));

  app.use(express.static(path.join(ROOT, 'public')));

  app.use((err, _req, res, _next) => {
    if (err instanceof multer.MulterError) {
      const messages = {
        LIMIT_FILE_SIZE: `파일 하나는 ${config.maxUploadMb}MB를 넘을 수 없습니다`,
        LIMIT_FILE_COUNT: `한 번에 올릴 수 있는 파일 수(${config.maxUploadFiles}개)를 넘었습니다`,
      };
      const message = messages[err.code] ?? `업로드 오류: ${err.message}`;
      return res.status(err.code === 'LIMIT_FILE_SIZE' ? 413 : 400).json({ error: message });
    }
    if (err.type === 'entity.too.large') return res.status(413).json({ error: '보낸 내용이 너무 큽니다' });
    if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON 형식이 올바르지 않습니다' });
    console.error(err);
    res.status(err.status || 500).json({ error: '서버 오류가 발생했습니다' });
  });

  return { app, db, purgeExpired: auth.purgeExpired };
}

// 같은 와이파이(공유기)에 있는 휴대폰 등에서 접속할 주소들
export function lanUrls(port, interfaces = os.networkInterfaces()) {
  return Object.values(interfaces).flat()
    .filter((a) => a && (a.family === 'IPv4' || a.family === 4) && !a.internal)
    .map((a) => `http://${a.address}:${port}`);
}

export function startServer(config = loadConfig()) {
  const { app, db, purgeExpired } = createApp(config);
  backfillHashes(db, config.musicDir).then((n) => n && console.log(`기존 곡 ${n}개의 중복 검사용 해시를 계산했습니다`));
  setInterval(purgeExpired, 60 * 60 * 1000).unref();
  // 켤 때 한 번, 그 뒤로 한 시간마다 확인해서 날짜가 바뀌었으면 자동 백업
  const autoBackup = () => runAutoBackup(db, config.backupDir, { keep: config.autoBackupKeep })
    .then((files) => files.forEach((f) => console.log(`자동 백업: ${f}`)))
    .catch((err) => console.error('자동 백업 실패:', err));
  autoBackup();
  setInterval(autoBackup, 60 * 60 * 1000).unref();
  // Express 5는 포트 오류 때도 이 콜백을 부르므로 err가 있으면 아래 'error' 처리에 맡긴다.
  const server = app.listen(config.port, (err) => {
    if (err) return;
    console.log(`음악 서버 실행 중: http://localhost:${config.port}  (데이터: ${config.dataDir})`);
    const lan = lanUrls(config.port);
    if (lan.length) console.log(`같은 와이파이의 휴대폰·다른 PC에서는: ${lan.join('  ')}`);
    console.log('끄려면 이 창에서 Ctrl+C를 누르세요.');
  });
  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`${config.port}번 포트를 이미 다른 프로그램이 쓰고 있습니다. 음악 서버가 이미 켜져 있는지 확인하거나, PORT=3001 처럼 다른 번호로 실행하세요.`);
      process.exit(1);
    }
    throw err;
  });
  return server;
}

if (process.argv[1] === import.meta.filename) startServer();
