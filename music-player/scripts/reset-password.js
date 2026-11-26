// 비밀번호를 잊었을 때 서버 컴퓨터에서 다시 정한다:  npm run reset-password
// 서버 컴퓨터에 들어올 수 있는 사람만 실행할 수 있으니, 그것을 본인 확인으로 삼는다.
// 바꾼 뒤에는 모든 로그인을 끊어서 다시 로그인하게 한다.
import readline from 'node:readline';
import path from 'node:path';
import { checkNode, hideSqliteWarning } from '../server/node-check.js';

const check = checkNode();
if (!check.ok) {
  console.error(check.message);
  process.exit(1);
}
hideSqliteWarning();

const { loadConfig } = await import('../server/index.js');
const { openDb } = await import('../server/db.js');
const { hashPassword } = await import('../server/auth.js');

const fail = (message) => {
  console.error(message);
  process.exit(1);
};

const config = loadConfig();
const db = openDb(path.join(config.dataDir, 'library.db'));
const users = db.prepare('SELECT id, username FROM users ORDER BY id').all();
if (!users.length) fail('아직 계정이 없습니다. 서버를 켜고 브라우저로 처음 접속하면 계정을 만들 수 있습니다.');

// 터미널에서는 입력하는 비밀번호를 화면에 보이지 않게 한다. 파이프로 넣어도(테스트) 한 줄씩 읽는다.
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: Boolean(process.stdin.isTTY) });
let hidden = false;
rl._writeToOutput = (text) => {
  if (!hidden) rl.output.write(text);
  else if (text.includes('\n') || text.includes('\r')) rl.output.write('\n');
};
const lines = rl[Symbol.asyncIterator]();
async function ask(question, { secret = false } = {}) {
  rl.output.write(question);
  hidden = secret;
  const { value, done } = await lines.next();
  hidden = false;
  if (!process.stdin.isTTY) rl.output.write('\n');
  if (done) fail('입력이 끝나 그만둡니다.');
  return value;
}

let user = users[0];
if (users.length > 1) {
  console.log(`계정: ${users.map((u) => u.username).join(', ')}`);
  const name = (await ask('비밀번호를 바꿀 아이디: ')).trim();
  user = users.find((u) => u.username === name);
  if (!user) fail(`'${name}' 계정이 없습니다.`);
}

console.log(`'${user.username}' 계정의 새 비밀번호를 정합니다. (데이터: ${config.dataDir})`);
const password = await ask('새 비밀번호 (8자 이상): ', { secret: true });
if (password.length < 8) fail('비밀번호는 8자 이상이어야 합니다. 바꾸지 않았습니다.');
const confirm = await ask('한 번 더: ', { secret: true });
if (confirm !== password) fail('두 비밀번호가 서로 다릅니다. 바꾸지 않았습니다.');

db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(hashPassword(password), user.id);
const { changes } = db.prepare('DELETE FROM sessions WHERE user_id = ?').run(user.id);
rl.close();
db.close();
console.log(`비밀번호를 바꿨습니다.${changes ? ` 로그인되어 있던 ${changes}곳은 다시 로그인해야 합니다.` : ''}`);
