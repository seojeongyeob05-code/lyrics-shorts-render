import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupTracks, UNKNOWN_ARTIST } from '../public/groups.js';

const tracks = [
  { id: 1, title: 'B곡', artist: '아이유', album: 'Palette', trackNo: 2, hasCover: false },
  { id: 2, title: 'A곡', artist: '아이유', album: 'Palette', trackNo: 1, hasCover: true },
  { id: 3, title: '봄날', artist: null, album: null },
  { id: 4, title: 'Night Drive', artist: 'City Lights', album: 'Neon', trackNo: 1 },
  { id: 5, title: '모음곡', artist: '정엽', album: 'Neon', trackNo: 2 },
  { id: 6, title: '2번 디스크', artist: '아이유', album: 'Palette', discNo: 2, trackNo: 1 },
];

test('아티스트별로 묶고 한글 → 영문 순, 알 수 없는 아티스트는 맨 뒤에 둔다', () => {
  const groups = groupTracks(tracks, 'artist');
  assert.deepEqual(groups.map((g) => g.name), ['아이유', '정엽', 'City Lights', UNKNOWN_ARTIST]);
  const iu = groups[0];
  assert.deepEqual(iu.tracks.map((t) => t.id), [2, 1, 6]);
  assert.equal(iu.subtitle, '앨범 1개 · 3곡');
  assert.equal(iu.cover.id, 2);
  assert.equal(groups[3].subtitle, '1곡');
  assert.equal(groups[3].cover, null);
});

test('앨범별로 묶을 때 앨범 없는 곡은 빼고, 디스크·트랙 번호 순으로 정렬한다', () => {
  const groups = groupTracks(tracks, 'album');
  assert.deepEqual(groups.map((g) => g.name), ['Neon', 'Palette']);
  assert.deepEqual(groups[1].tracks.map((t) => t.id), [2, 1, 6]);
  assert.equal(groups[1].subtitle, '아이유 · 3곡');
  // 곡마다 아티스트가 다른 앨범(컴필레이션)은 '여러 아티스트'
  assert.equal(groups[0].subtitle, '여러 아티스트 · 2곡');
});

test('빈 라이브러리', () => {
  assert.deepEqual(groupTracks([], 'album'), []);
});
