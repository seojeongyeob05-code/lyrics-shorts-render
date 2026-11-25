#!/bin/sh
# 맥·리눅스용 시작 파일. 터미널에서 ./start.sh 로 실행하세요.
# Node.js 버전 확인 → (처음이면) 필요한 파일 설치 → 브라우저 열기 → 서버 실행
cd "$(dirname "$0")" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js가 설치되어 있지 않습니다."
  echo "https://nodejs.org 에서 LTS 버전(22 이상)을 설치한 뒤 다시 실행하세요."
  exit 1
fi
node server/node-check.js || exit 1

if [ ! -d node_modules ]; then
  echo "처음 실행이라 필요한 파일을 설치합니다. 잠시 기다려 주세요..."
  npm install --no-audit --no-fund || { echo "설치에 실패했습니다. 위 메시지를 확인하세요."; exit 1; }
fi

URL="http://localhost:${PORT:-3000}"
if [ -z "$NO_BROWSER" ]; then
  ( sleep 2
    if command -v open >/dev/null 2>&1; then open "$URL"
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
    fi ) >/dev/null 2>&1 &
fi
exec node server/main.js
