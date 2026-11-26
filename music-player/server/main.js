// 서버 시작점. Node.js 버전을 먼저 확인한 뒤에 서버(내장 SQLite 사용)를 불러온다.
import { checkNode, hideSqliteWarning } from './node-check.js';

const check = checkNode();
if (!check.ok) {
  console.error(check.message);
  process.exit(1);
}

hideSqliteWarning();

const { startServer } = await import('./index.js');
startServer();
