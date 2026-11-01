import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matchesQuery, toChosung } from '../public/search.js';

const track = { title: '봄날의 노래', artist: 'City Lights', album: 'Neon' };

test('제목·아티스트·앨범에서 대소문자와 공백을 무시하고 찾는다', () => {
  assert.ok(matchesQuery(track, '봄날'));
  assert.ok(matchesQuery(track, '봄날의노래'));
  assert.ok(matchesQuery(track, 'city lights'));
  assert.ok(matchesQuery(track, 'NEON'));
  assert.ok(matchesQuery(track, '  '));
  assert.ok(!matchesQuery(track, '가을'));
});

test('초성만 입력하면 초성으로 찾는다', () => {
  assert.equal(toChosung('봄날의 노래'), 'ㅂㄴㅇ ㄴㄹ');
  assert.ok(matchesQuery(track, 'ㅂㄴ'));
  assert.ok(matchesQuery(track, 'ㄴㄹ'));
  assert.ok(!matchesQuery(track, 'ㄱㅇ'));
});

test('서로 다른 필드에 걸친 문자열은 일치로 보지 않는다', () => {
  assert.ok(!matchesQuery(track, 'lightsneon'));
});

test('자모가 분리된(NFD) 제목도 찾는다', () => {
  assert.ok(matchesQuery({ title: '봄날의 노래'.normalize('NFD') }, '봄날'));
});

test('아티스트나 앨범이 없어도 동작한다', () => {
  assert.ok(matchesQuery({ title: 'Night Drive', artist: null, album: undefined }, 'night'));
});
