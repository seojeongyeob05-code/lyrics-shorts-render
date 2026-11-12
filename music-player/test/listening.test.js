import { test } from 'node:test';
import assert from 'node:assert/strict';
import { playThreshold, createListenTracker, recentTracks, topTracks } from '../public/listening.js';

test('절반을 들으면 한 번, 아무리 길어도 4분이면 한 번', () => {
  assert.equal(playThreshold(200), 100);
  assert.equal(playThreshold(1200), 240);
  assert.equal(playThreshold(NaN), 30);
  assert.equal(playThreshold(0), 30);
});

// 0.25초 간격으로 재생 위치가 흘러가는 것을 흉내 낸다.
function play(tracker, from, to, duration) {
  for (let t = from; t <= to + 1e-9; t += 0.25) tracker.tick(t, duration);
}

test('절반을 듣는 순간 한 번만 센다', () => {
  let count = 0;
  const tracker = createListenTracker(() => count++);
  play(tracker, 0, 4.75, 10);
  assert.equal(count, 0);
  play(tracker, 5, 10, 10);
  assert.equal(count, 1); // 끝까지 들어도 한 번
});

test('탐색바로 건너뛴 구간은 듣지 않은 것으로 본다', () => {
  let count = 0;
  const tracker = createListenTracker(() => count++);
  play(tracker, 0, 1, 10);
  tracker.tick(9, 10); // 끝 부분으로 점프
  play(tracker, 9, 10, 10);
  assert.equal(count, 0);
  // seeked로 알려 주면 짧은 이동도 빼고 센다
  tracker.reset();
  play(tracker, 0, 2, 10);
  tracker.seeked(3);
  play(tracker, 3, 4, 10);
  assert.equal(count, 0);
});

test('reset하면 같은 곡을 다시 들을 때 또 센다 (한 곡 반복)', () => {
  let count = 0;
  const tracker = createListenTracker(() => count++);
  play(tracker, 0, 3, 4);
  tracker.reset();
  play(tracker, 0, 3, 4);
  assert.equal(count, 2);
});

const tracks = [
  { id: 1, createdAt: 100, playCount: 3, lastPlayedAt: 50 },
  { id: 2, createdAt: 300, playCount: 0, lastPlayedAt: null },
  { id: 3, createdAt: 200, playCount: 3, lastPlayedAt: 90 },
  { id: 4, createdAt: 300, playCount: 7, lastPlayedAt: 10 },
];

test('최근 추가한 곡: 새로 올린 순, 개수 제한', () => {
  assert.deepEqual(recentTracks(tracks).map((t) => t.id), [4, 2, 3, 1]);
  assert.deepEqual(recentTracks(tracks, 2).map((t) => t.id), [4, 2]);
});

test('많이 들은 곡: 들은 횟수 순, 같으면 최근에 들은 순, 안 들은 곡 제외', () => {
  assert.deepEqual(topTracks(tracks).map((t) => t.id), [4, 3, 1]);
});
