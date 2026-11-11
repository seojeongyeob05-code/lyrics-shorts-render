import { test } from 'node:test';
import assert from 'node:assert/strict';
import { planPlaylistAdd } from '../public/playlist-add.js';

test('이미 있는 곡과 새 곡을 나눈다 (순서 유지)', () => {
  assert.deepEqual(planPlaylistAdd([1, 2], [3, 2, 4]), { all: [3, 2, 4], fresh: [3, 4], duplicates: 1 });
});

test('고른 곡 안의 중복은 한 번만 센다', () => {
  assert.deepEqual(planPlaylistAdd([], [5, 5, 6]), { all: [5, 6], fresh: [5, 6], duplicates: 0 });
  assert.deepEqual(planPlaylistAdd([5], [5, 5]), { all: [5], fresh: [], duplicates: 1 });
});

test('빈 플레이리스트에는 모두 새 곡', () => {
  assert.deepEqual(planPlaylistAdd([], [1, 2]), { all: [1, 2], fresh: [1, 2], duplicates: 0 });
});
