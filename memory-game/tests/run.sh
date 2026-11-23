#!/usr/bin/env bash
# Runs the scripted playthroughs of all five situations and checks each one ends as expected.
# Usage: bash memory-game/tests/run.sh            (playthroughs only)
#        bash memory-game/tests/run.sh --monkey 8 (also 8 randomized runs)
set -u
cd "$(dirname "$0")"
mkdir -p out
node playthrough.js > out/playthrough.log 2>&1
status=0
check() { if grep -qE "$1" out/playthrough.log; then echo "ok    $2"; else echo "FAIL  $2"; status=1; fi; }
check "L1:  지갑을 되찾았다" "상황 1: 지갑 되찾기"
check "L2 good  할머니가 활짝 웃었다" "상황 2: 올바른 주문"
check "L2 mug  할머니가 고개를 갸웃했다" "상황 2: for here 실패 처리"
check "L3 \\{ locker.*택배를 찾았다" "상황 3: 보관함"
check "L3big  택배를 찾았다" "상황 3: 너무 큰 택배"
check "방문객이 무사히 길을 찾았다" "상황 4: 길 안내"
check "청소부가 바로 고치러 갔다" "상황 5: 고장 신고"
check "L5rooms mistakes: 0 " "상황 5: 방 구경은 실수가 아님"
check "phone hscroll false" "휴대폰 폭 가로 넘침 없음"
if grep -E "pageerror|errors \[ ['\"]" out/playthrough.log >/dev/null; then echo "FAIL  페이지 오류가 기록됨"; status=1; else echo "ok    페이지 오류 없음"; fi
if [ "${1:-}" = "--monkey" ]; then
  node monkey.js "${2:-8}" > out/monkey.log 2>&1
  if sed -n '/UNIQUE ERRORS:/,$p' out/monkey.log | grep -q "x "; then echo "FAIL  몽키 테스트 오류 (out/monkey.log)"; status=1; else echo "ok    몽키 테스트 ${2:-8}판 오류 없음"; fi
fi
exit $status
