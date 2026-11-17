import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toM3u, parseM3u, matchEntries, decodeText } from '../public/m3u.js';

const library = [
  { id: 1, title: '봄날', artist: 'BTS', duration: 274.4 },
  { id: 2, title: 'Night Drive', artist: 'City Lights', duration: 180 },
  { id: 3, title: '봄날의 노래', artist: null, duration: 4 },
  { id: 4, title: 'Intro', artist: 'A', duration: 60 },
  { id: 5, title: 'Intro', artist: 'B', duration: 60 },
  { id: 6, title: 'AC/DC: Live?', artist: null, duration: 10 },
];

test('내보내기: EXTINF에 길이와 "아티스트 - 제목"을 쓰고, 경로에는 쓸 수 없는 문자를 바꾼다', () => {
  assert.equal(toM3u([library[0], library[2], library[5]]),
    '#EXTM3U\n#EXTINF:274,BTS - 봄날\nBTS - 봄날\n#EXTINF:4,봄날의 노래\n봄날의 노래\n#EXTINF:10,AC/DC: Live?\nAC_DC_ Live_\n');
});

test('내보낸 파일을 다시 가져오면 같은 곡, 같은 순서 (반복 포함)', () => {
  const tracks = [library[1], library[0], library[2], library[1]];
  const { ids, unmatched } = matchEntries(parseM3u(toM3u(tracks)), library);
  assert.deepEqual(ids, [2, 1, 3, 2]);
  assert.deepEqual(unmatched, []);
});

test('다른 플레이어의 파일: 윈도 경로, EXTINF 없음, BOM, CRLF, 빈 줄, 대소문자', () => {
  const text = '﻿#EXTM3U\r\n#EXTINF:180,city lights - night drive\r\nD:\\Music\\x.mp3\r\n\r\nC:\\Music\\BTS - 봄날.flac\r\n/home/me/music/%EB%B4%84%EB%82%A0%EC%9D%98%20%EB%85%B8%EB%9E%98.mp3\r\n';
  const entries = parseM3u(text);
  assert.equal(entries.length, 3);
  assert.deepEqual(matchEntries(entries, library).ids, [2, 1, 3]);
});

test('제목만 같은 곡이 여럿이면 짝짓지 않고, 없는 곡은 따로 알려 준다', () => {
  const entries = parseM3u('#EXTINF:60,Intro\nintro.mp3\n#EXTINF:60,B - Intro\nb.mp3\n#EXTINF:1,없는 가수 - 없는 노래\nx.mp3\n#EXTINF:1,모르는 가수 - Night Drive\ny.mp3');
  const { ids, unmatched } = matchEntries(entries, library);
  assert.deepEqual(ids, [5, 2]); // "B - Intro"는 정확히, "모르는 가수 - Night Drive"는 유일한 제목으로
  assert.deepEqual(unmatched, ['Intro', '없는 가수 - 없는 노래']);
});

test('UTF-8이 아니면 EUC-KR로 읽는다', () => {
  assert.equal(decodeText(new TextEncoder().encode('봄날')), '봄날');
  assert.equal(decodeText(new Uint8Array([0xba, 0xbd, 0xb3, 0xaf])), '봄날');
});
