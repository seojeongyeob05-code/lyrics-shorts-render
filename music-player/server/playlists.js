import { Router } from 'express';
import { transaction } from './db.js';
import { toTrackJson } from './tracks.js';

function cleanName(value) {
  const name = typeof value === 'string' ? value.trim() : '';
  return name && name.length <= 100 ? name : null;
}

export function createPlaylistsRouter(db) {
  const router = Router();

  // 다른 사용자의 플레이리스트는 없는 것처럼 404로 응답한다.
  const findOwned = (req, res) => {
    const playlist = db.prepare('SELECT * FROM playlists WHERE id = ? AND user_id = ?')
      .get(Number(req.params.id), req.user.id);
    if (!playlist) res.status(404).json({ error: '플레이리스트를 찾을 수 없습니다' });
    return playlist;
  };

  const entries = (playlistId) => db.prepare(`
    SELECT pt.id AS entry_id, t.* FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id
    WHERE pt.playlist_id = ? ORDER BY pt.position, pt.id
  `).all(playlistId);

  router.get('/', (req, res) => {
    const rows = db.prepare(`
      SELECT p.id, p.name, p.created_at, COUNT(pt.id) AS track_count
      FROM playlists p LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id
      WHERE p.user_id = ? GROUP BY p.id ORDER BY p.created_at
    `).all(req.user.id);
    res.json(rows.map((r) => ({ id: r.id, name: r.name, trackCount: r.track_count })));
  });

  router.post('/', (req, res) => {
    const name = cleanName(req.body?.name);
    if (!name) return res.status(400).json({ error: '이름은 1~100자로 입력하세요' });
    const { lastInsertRowid } = db.prepare('INSERT INTO playlists (user_id, name, created_at) VALUES (?, ?, ?)')
      .run(req.user.id, name, Date.now());
    res.status(201).json({ id: Number(lastInsertRowid), name, trackCount: 0 });
  });

  router.get('/:id', (req, res) => {
    const playlist = findOwned(req, res);
    if (!playlist) return;
    res.json({
      id: playlist.id,
      name: playlist.name,
      tracks: entries(playlist.id).map((row) => ({ ...toTrackJson(row), entryId: row.entry_id })),
    });
  });

  router.patch('/:id', (req, res) => {
    const playlist = findOwned(req, res);
    if (!playlist) return;
    const name = cleanName(req.body?.name);
    if (!name) return res.status(400).json({ error: '이름은 1~100자로 입력하세요' });
    db.prepare('UPDATE playlists SET name = ? WHERE id = ?').run(name, playlist.id);
    res.json({ id: playlist.id, name });
  });

  router.delete('/:id', (req, res) => {
    const playlist = findOwned(req, res);
    if (!playlist) return;
    db.prepare('DELETE FROM playlists WHERE id = ?').run(playlist.id);
    res.status(204).end();
  });

  router.post('/:id/tracks', (req, res) => {
    const playlist = findOwned(req, res);
    if (!playlist) return;
    const ids = Array.isArray(req.body?.trackIds) ? req.body.trackIds.map(Number) : [];
    const exists = db.prepare('SELECT 1 FROM tracks WHERE id = ?');
    if (!ids.length || ids.some((id) => !exists.get(id))) {
      return res.status(400).json({ error: '추가할 곡이 올바르지 않습니다' });
    }
    transaction(db, () => {
      let pos = db.prepare('SELECT COALESCE(MAX(position), -1) AS p FROM playlist_tracks WHERE playlist_id = ?')
        .get(playlist.id).p;
      const insert = db.prepare('INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)');
      for (const id of ids) insert.run(playlist.id, id, ++pos);
    });
    res.status(201).json({ added: ids.length });
  });

  router.delete('/:id/tracks/:entryId', (req, res) => {
    const playlist = findOwned(req, res);
    if (!playlist) return;
    const { changes } = db.prepare('DELETE FROM playlist_tracks WHERE id = ? AND playlist_id = ?')
      .run(Number(req.params.entryId), playlist.id);
    if (!changes) return res.status(404).json({ error: '플레이리스트에 없는 곡입니다' });
    res.status(204).end();
  });

  // 클라이언트가 보낸 entryId 순서대로 position을 다시 매긴다.
  router.put('/:id/order', (req, res) => {
    const playlist = findOwned(req, res);
    if (!playlist) return;
    const order = Array.isArray(req.body?.entryIds) ? req.body.entryIds.map(Number) : [];
    const current = entries(playlist.id).map((e) => e.entry_id);
    const same = order.length === current.length && new Set(order).size === order.length
      && order.every((id) => current.includes(id));
    if (!same) return res.status(400).json({ error: '순서 정보가 현재 목록과 맞지 않습니다' });
    transaction(db, () => {
      const update = db.prepare('UPDATE playlist_tracks SET position = ? WHERE id = ?');
      order.forEach((id, i) => update.run(i, id));
    });
    res.status(204).end();
  });

  return router;
}
