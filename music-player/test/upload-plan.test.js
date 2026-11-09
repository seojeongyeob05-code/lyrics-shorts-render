import { test } from 'node:test';
import assert from 'node:assert/strict';
import { planUploads, mergeResults } from '../public/upload-plan.js';

const MB = 1024 * 1024;
const file = (name, mb = 1) => ({ name, size: mb * MB });
const names = (batches) => batches.map((b) => b.map((f) => f.name));

test('파일 수 한도에 맞춰 여러 묶음으로 나눈다', () => {
  const files = Array.from({ length: 45 }, (_, i) => file(`${i}.mp3`));
  const { batches, tooLarge } = planUploads(files, { batchFiles: 20 });
  assert.deepEqual(batches.map((b) => b.length), [20, 20, 5]);
  assert.deepEqual(tooLarge, []);
  assert.deepEqual(batches.flat(), files); // 순서 유지, 빠짐 없음
});

test('용량 한도에 맞춰 나누고, 한도보다 큰 파일 하나는 혼자 보낸다', () => {
  const files = [file('a.mp3', 60), file('b.mp3', 60), file('c.flac', 150), file('d.mp3', 10)];
  const { batches } = planUploads(files, { batchBytes: 100 * MB });
  assert.deepEqual(names(batches), [['a.mp3'], ['b.mp3'], ['c.flac'], ['d.mp3']]);
});

test('파일 하나 최대 크기를 넘는 파일은 따로 빼서 알려 준다', () => {
  const { batches, tooLarge } = planUploads([file('ok.mp3', 5), file('huge.wav', 300)], { maxFileBytes: 200 * MB });
  assert.deepEqual(names(batches), [['ok.mp3']]);
  assert.deepEqual(tooLarge.map((f) => f.name), ['huge.wav']);
});

test('같은 이름의 음원과 .lrc는 떨어져 있어도 같은 묶음에 넣는다', () => {
  const files = [file('봄날.mp3'), file('a.mp3'), file('b.mp3'), file('봄날.LRC', 0.01), file('c.mp3')];
  const { batches } = planUploads(files, { batchFiles: 2 });
  assert.deepEqual(names(batches), [['봄날.mp3', '봄날.LRC'], ['a.mp3', 'b.mp3'], ['c.mp3']]);
});

test('빈 목록', () => {
  assert.deepEqual(planUploads([]), { batches: [], tooLarge: [] });
});

test('묶음별 결과를 합친다', () => {
  const merged = mergeResults([
    { added: [{ id: 1 }], duplicates: [], rejected: ['x.txt'], lyrics: { attached: [{ trackId: 1 }], unmatched: [] } },
    { added: [{ id: 2 }], duplicates: [{ name: 'd.mp3' }], rejected: [] },
  ]);
  assert.deepEqual(merged, {
    added: [{ id: 1 }, { id: 2 }],
    duplicates: [{ name: 'd.mp3' }],
    rejected: ['x.txt'],
    lyrics: { attached: [{ trackId: 1 }], unmatched: [] },
  });
});
