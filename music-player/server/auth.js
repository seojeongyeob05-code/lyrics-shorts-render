import crypto from 'node:crypto';
import { Router } from 'express';

const COOKIE = 'mp_session';
const DAY = 24 * 60 * 60 * 1000;

export function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(password, salt, 64);
  return `${salt.toString('hex')}:${hash.toString('hex')}`;
}

export function verifyPassword(password, stored) {
  const [saltHex, hashHex] = stored.split(':');
  const expected = Buffer.from(hashHex, 'hex');
  const actual = crypto.scryptSync(password, Buffer.from(saltHex, 'hex'), expected.length);
  return crypto.timingSafeEqual(actual, expected);
}

const sha256 = (s) => crypto.createHash('sha256').update(s).digest('hex');

function readCookie(req, name) {
  for (const part of (req.headers.cookie || '').split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return decodeURIComponent(v.join('='));
  }
  return null;
}

// 로그인 실패를 IP별로 세어 무차별 대입을 늦춘다 (15분에 10회).
function createLoginLimiter({ max = 10, windowMs = 15 * 60 * 1000 } = {}) {
  const hits = new Map();
  return {
    blocked(ip) {
      const h = hits.get(ip);
      if (!h || h.resetAt < Date.now()) return false;
      return h.count >= max;
    },
    fail(ip) {
      const h = hits.get(ip);
      if (!h || h.resetAt < Date.now()) hits.set(ip, { count: 1, resetAt: Date.now() + windowMs });
      else h.count++;
    },
    reset(ip) {
      hits.delete(ip);
    },
  };
}

export function createAuth(db, config) {
  const limiter = createLoginLimiter();

  function startSession(res, userId) {
    const token = crypto.randomBytes(32).toString('hex');
    const maxAge = config.sessionDays * DAY;
    db.prepare('INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)')
      .run(sha256(token), userId, Date.now() + maxAge);
    res.cookie(COOKIE, token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: config.secureCookie,
      maxAge,
      path: '/',
    });
  }

  // 모든 요청에서 세션 쿠키를 확인해 req.user를 채운다.
  function loadUser(req, _res, next) {
    const token = readCookie(req, COOKIE);
    if (token) {
      req.user = db.prepare(`
        SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > ?
      `).get(sha256(token), Date.now());
    }
    next();
  }

  function requireAuth(req, res, next) {
    if (!req.user) return res.status(401).json({ error: '로그인이 필요합니다' });
    next();
  }

  function purgeExpired() {
    db.prepare('DELETE FROM sessions WHERE expires_at <= ?').run(Date.now());
  }

  function validate(body) {
    const username = typeof body?.username === 'string' ? body.username.trim() : '';
    const password = typeof body?.password === 'string' ? body.password : '';
    if (!/^[\w.\-가-힣]{2,32}$/.test(username)) return { error: '아이디는 2~32자의 한글, 영문, 숫자, _ . - 만 쓸 수 있습니다' };
    if (password.length < 8) return { error: '비밀번호는 8자 이상이어야 합니다' };
    return { username, password };
  }

  const router = Router();
  const userCount = () => db.prepare('SELECT COUNT(*) AS n FROM users').get().n;

  router.get('/status', (req, res) => {
    res.json({ setupRequired: userCount() === 0, user: req.user ?? null });
  });

  // 최초 1회만: 첫 계정을 만들고 이후 가입은 막는다.
  router.post('/setup', (req, res) => {
    if (userCount() > 0) return res.status(403).json({ error: '이미 계정이 만들어져 있습니다' });
    const v = validate(req.body);
    if (v.error) return res.status(400).json({ error: v.error });
    const { lastInsertRowid } = db.prepare('INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)')
      .run(v.username, hashPassword(v.password), Date.now());
    startSession(res, Number(lastInsertRowid));
    res.status(201).json({ user: { id: Number(lastInsertRowid), username: v.username } });
  });

  router.post('/login', (req, res) => {
    if (limiter.blocked(req.ip)) return res.status(429).json({ error: '로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요' });
    const username = String(req.body?.username ?? '').trim();
    const password = String(req.body?.password ?? '');
    const user = db.prepare('SELECT id, username, password_hash FROM users WHERE username = ?').get(username);
    if (!user || !verifyPassword(password, user.password_hash)) {
      limiter.fail(req.ip);
      return res.status(401).json({ error: '아이디 또는 비밀번호가 올바르지 않습니다' });
    }
    limiter.reset(req.ip);
    startSession(res, user.id);
    res.json({ user: { id: user.id, username: user.username } });
  });

  router.post('/logout', (req, res) => {
    const token = readCookie(req, COOKIE);
    if (token) db.prepare('DELETE FROM sessions WHERE token_hash = ?').run(sha256(token));
    res.clearCookie(COOKIE, { path: '/' });
    res.status(204).end();
  });

  return { router, loadUser, requireAuth, purgeExpired };
}
