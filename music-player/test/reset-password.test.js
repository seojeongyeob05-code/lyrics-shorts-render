import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { openDb } from '../server/db.js';
import { hashPassword, verifyPassword } from '../server/auth.js';

const SCRIPT = new URL('../scripts/reset-password.js', import.meta.url).pathname;
const dirs = [];
after(() => dirs.forEach((d) => fs.rmSync(d, { recursive: true, force: true })));

function makeDataDir(usernames) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'music-player-reset-'));
  dirs.push(dir);
  const db = openDb(path.join(dir, 'library.db'));
  for (const name of usernames) {
    const { lastInsertRowid } = db.prepare('INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, 0)').run(name, hashPassword('oldpass123'));
    db.prepare('INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)').run(`t-${name}`, lastInsertRowid, Date.now() + 1e9);
  }
  db.close();
  return dir;
}

const run = (dir, input) => spawnSync(process.execPath, [SCRIPT], { env: { ...process.env, DATA_DIR: dir }, input, encoding: 'utf8' });
const readUser = (dir, name) => {
  const db = openDb(path.join(dir, 'library.db'));
  const user = db.prepare('SELECT id, password_hash FROM users WHERE username = ?').get(name);
  const sessions = db.prepare('SELECT COUNT(*) AS n FROM sessions WHERE user_id = ?').get(user.id).n;
  db.close();
  return { hash: user.password_hash, sessions };
};

test('계정이 하나면 바로 새 비밀번호를 받아 바꾸고, 모든 로그인을 끊는다', () => {
  const dir = makeDataDir(['정엽']);
  const r = run(dir, 'newpass123\nnewpass123\n');
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /'정엽' 계정의 새 비밀번호/);
  assert.match(r.stdout, /비밀번호를 바꿨습니다\. 로그인되어 있던 1곳은 다시 로그인해야 합니다/);
  assert.doesNotMatch(r.stdout + r.stderr, /newpass123|ExperimentalWarning/); // 비밀번호·경고를 출력하지 않음
  const { hash, sessions } = readUser(dir, '정엽');
  assert.equal(verifyPassword('newpass123', hash), true);
  assert.equal(sessions, 0);
});

test('짧거나 두 번 입력이 다르면 바꾸지 않는다', () => {
  const dir = makeDataDir(['me']);
  for (const [input, message] of [['short\n', /8자 이상/], ['newpass123\nnewpass124\n', /서로 다릅니다/], ['newpass123\n', /입력이 끝나/]]) {
    const r = run(dir, input);
    assert.equal(r.status, 1);
    assert.match(r.stderr, message);
  }
  const { hash, sessions } = readUser(dir, 'me');
  assert.equal(verifyPassword('oldpass123', hash), true);
  assert.equal(sessions, 1);
});

test('계정이 여럿이면 아이디를 묻고, 없는 아이디는 거부한다', () => {
  const dir = makeDataDir(['a', 'b']);
  assert.match(run(dir, 'zzz\n').stderr, /'zzz' 계정이 없습니다/);
  const r = run(dir, 'b\nnewpass123\nnewpass123\n');
  assert.equal(r.status, 0, r.stderr);
  assert.equal(verifyPassword('newpass123', readUser(dir, 'b').hash), true);
  assert.equal(verifyPassword('oldpass123', readUser(dir, 'a').hash), true); // 다른 계정은 그대로
});

test('계정이 아직 없으면 브라우저에서 만들라고 안내한다', () => {
  const r = run(makeDataDir([]), '');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /아직 계정이 없습니다/);
});
