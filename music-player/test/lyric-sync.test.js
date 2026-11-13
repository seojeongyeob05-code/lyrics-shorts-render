import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lrcTime, createSync, stamp, undo, jumpTo, missingCount, toLrc } from '../public/lyric-sync.js';
import { parseLyrics } from '../public/lyrics.js';

test('시간을 LRC 형식으로 바꾼다', () => {
  assert.equal(lrcTime(0), '[00:00.00]');
  assert.equal(lrcTime(61.234), '[01:01.23]');
  assert.equal(lrcTime(59.999), '[01:00.00]');
  assert.equal(lrcTime(-1), '[00:00.00]');
});

test('일반 가사로 시작해 줄마다 찍고, 되돌리고, LRC로 만든다', () => {
  let s = createSync(parseLyrics('첫 줄\n둘째 줄\n셋째 줄').lines);
  assert.equal(s.target, 0);
  assert.equal(missingCount(s), 3);
  s = stamp(s, 1.004);
  s = stamp(s, 4.5);
  assert.equal(s.target, 2);
  s = undo(s);
  assert.equal(s.target, 1);
  assert.equal(s.lines[1].time, null);
  s = stamp(s, 5);
  s = stamp(s, 9.25);
  s = stamp(s, 12); // 마지막 줄 뒤에서는 아무 일도 없음
  assert.equal(missingCount(s), 0);
  assert.equal(toLrc(s), '[00:01.00]첫 줄\n[00:05.00]둘째 줄\n[00:09.25]셋째 줄');
});

test('이미 싱크된 가사는 시간이 유지되고, 원하는 줄로 가서 다시 찍을 수 있다', () => {
  let s = createSync(parseLyrics('[00:01.00]가\n[00:03.00]나').lines);
  assert.equal(s.target, 2); // 모두 찍혀 있음
  s = jumpTo(s, 1);
  s = stamp(s, 2.5);
  assert.equal(toLrc(s), '[00:01.00]가\n[00:02.50]나');
});

test('순서가 뒤바뀌게 찍어도 시간순으로 저장하고, 안 찍은 줄은 뺀다', () => {
  let s = createSync([{ text: 'A' }, { text: 'B' }, { text: 'C' }]);
  s = stamp(jumpTo(s, 1), 2);
  s = stamp(jumpTo(s, 0), 5);
  assert.equal(missingCount(s), 1);
  assert.equal(toLrc(s), '[00:02.00]B\n[00:05.00]A');
});

test('원래 상태를 바꾸지 않는다', () => {
  const s = createSync([{ text: 'A' }]);
  stamp(s, 1);
  assert.equal(s.lines[0].time, null);
  assert.equal(s.target, 0);
});
