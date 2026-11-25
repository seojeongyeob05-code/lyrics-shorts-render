// 서버 시작점. Node.js 버전을 먼저 확인한 뒤에 서버(내장 SQLite 사용)를 불러온다.
import { checkNode } from './node-check.js';

const check = checkNode();
if (!check.ok) {
  console.error(check.message);
  process.exit(1);
}

// 내장 SQLite의 "실험 기능" 경고는 사용자에게 의미가 없어 숨긴다.
const emitWarning = process.emitWarning;
process.emitWarning = (warning, ...args) => {
  const type = typeof args[0] === 'string' ? args[0] : args[0]?.type;
  if (type === 'ExperimentalWarning' && String(warning).includes('SQLite')) return;
  return emitWarning.call(process, warning, ...args);
};

const { startServer } = await import('./index.js');
startServer();
