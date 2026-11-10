import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clickSelection, pruneSelection } from '../public/selection.js';

const keys = [10, 20, 30, 40, 50];
const list = (set) => [...set].sort((a, b) => a - b);

test('누르면 켜지고 다시 누르면 꺼지며, 누른 행이 기준이 된다', () => {
  let r = clickSelection(new Set(), keys, 1);
  assert.deepEqual(list(r.selected), [20]);
  assert.equal(r.anchor, 20);
  r = clickSelection(r.selected, keys, 1, { anchor: r.anchor });
  assert.deepEqual(list(r.selected), []);
});

test('Shift는 기준 행부터 누른 행까지 선택한다 (위·아래 모두)', () => {
  let r = clickSelection(new Set(), keys, 1);
  r = clickSelection(r.selected, keys, 3, { range: true, anchor: r.anchor });
  assert.deepEqual(list(r.selected), [20, 30, 40]);
  assert.equal(r.anchor, 20);
  r = clickSelection(new Set(), keys, 0, { range: true, anchor: 30 });
  assert.deepEqual(list(r.selected), [10, 20, 30]);
});

test('기준이 없거나 사라졌으면 Shift도 한 행만 켠다', () => {
  assert.deepEqual(list(clickSelection(new Set(), keys, 2, { range: true }).selected), [30]);
  assert.deepEqual(list(clickSelection(new Set(), keys, 2, { range: true, anchor: 99 }).selected), [30]);
});

test('원래 선택을 바꾸지 않는다', () => {
  const before = new Set([10]);
  clickSelection(before, keys, 1);
  assert.deepEqual(list(before), [10]);
});

test('보이지 않게 된 행은 선택에서 뺀다', () => {
  assert.deepEqual(list(pruneSelection(new Set([10, 30, 99]), [30, 40])), [30]);
});
