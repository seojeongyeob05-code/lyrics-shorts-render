import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLyrics, currentLineIndex } from '../public/lyrics.js';

test('LRC 싱크 가사를 시간순으로 읽고 정보 태그는 뺀다', () => {
  const { synced, lines } = parseLyrics('﻿[ti:봄날]\r\n[ar:정엽]\r\n[00:12.50]둘째 줄\r\n[00:01.00]첫째 줄\r\n\r\n[01:02.345]셋째 줄');
  assert.equal(synced, true);
  assert.deepEqual(lines, [
    { time: 1, text: '첫째 줄' },
    { time: 12.5, text: '둘째 줄' },
    { time: 62.345, text: '셋째 줄' },
  ]);
});

test('한 줄에 시간이 여러 개면 각 시간마다 줄을 만들고, 빈 가사 줄(간주)도 유지한다', () => {
  const { lines } = parseLyrics('[00:10][00:30]후렴\n[00:20]\n');
  assert.deepEqual(lines.map((l) => [l.time, l.text]), [[10, '후렴'], [20, ''], [30, '후렴']]);
});

test('offset 태그를 적용한다 (양수면 더 일찍)', () => {
  const { lines } = parseLyrics('[offset:500]\n[00:10.00]가사\n[00:00.20]처음');
  assert.deepEqual(lines.map((l) => l.time), [0, 9.5]);
});

test('시간 표시가 없으면 일반 가사로 그대로 보여 준다', () => {
  const { synced, lines } = parseLyrics('\n\n첫 줄\n\n둘째 줄\n\n');
  assert.equal(synced, false);
  assert.deepEqual(lines.map((l) => l.text), ['첫 줄', '', '둘째 줄']);
  assert.deepEqual(parseLyrics('').lines, []);
  assert.deepEqual(parseLyrics(null).lines, []);
});

test('재생 위치에 맞는 줄을 찾는다', () => {
  const lines = [{ time: 1 }, { time: 5 }, { time: 5 }, { time: 9 }];
  assert.equal(currentLineIndex(lines, 0.5), -1);
  assert.equal(currentLineIndex(lines, 1), 0);
  assert.equal(currentLineIndex(lines, 6), 2);
  assert.equal(currentLineIndex(lines, 100), 3);
  assert.equal(currentLineIndex([], 3), -1);
});

test('파일 태그의 가사를 LRC 텍스트로 바꾼다', async () => {
  const { lyricsFromTags } = await import('../server/tracks.js');
  assert.equal(lyricsFromTags([{ timeStampFormat: 2, syncText: [{ timestamp: 500, text: '첫 줄' }, { timestamp: 61_234, text: '' }] }]),
    '[00:00.50]첫 줄\n[01:01.23]');
  assert.equal(lyricsFromTags([{ timeStampFormat: 0, syncText: [], text: '\n일반 가사\n' }]), '일반 가사');
  assert.equal(lyricsFromTags([]), null);
  assert.equal(lyricsFromTags(undefined), null);
});
