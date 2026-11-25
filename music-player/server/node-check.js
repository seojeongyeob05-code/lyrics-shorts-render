// 서버가 쓰는 내장 SQLite(node:sqlite)는 Node.js 22.13 이상에만 있다.
// 낮은 버전에서 영어 오류로 꺼지지 않도록, 서버를 불러오기 전에 확인하고 한국어로 안내한다.
// 이 파일은 오래된 Node에서도 실행되도록 최신 문법을 쓰지 않는다.
import { pathToFileURL } from 'node:url';

export const REQUIRED = [22, 13];

export function checkNode(version = process.versions.node) {
  const [major, minor] = version.split('.').map(Number);
  const ok = major > REQUIRED[0] || (major === REQUIRED[0] && minor >= REQUIRED[1]);
  if (ok) return { ok: true };
  return {
    ok: false,
    message: [
      `Node.js ${version} 버전에서는 이 음악 서버를 실행할 수 없습니다.`,
      `Node.js ${REQUIRED.join('.')} 이상이 필요합니다.`,
      'https://nodejs.org 에서 LTS 버전(22 이상)을 설치한 뒤 다시 실행하세요.',
    ].join('\n'),
  };
}

// start.sh / 시작하기.bat 에서 "node server/node-check.js"로 바로 실행할 때
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = checkNode();
  if (!result.ok) {
    console.error(result.message);
    process.exit(1);
  }
}
