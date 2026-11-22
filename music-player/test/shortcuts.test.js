import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findShortcut, SHORTCUTS } from '../public/shortcuts.js';

const key = (key, code, mods = {}) => ({ key, code, shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, ...mods });

test('기본 단축키를 찾는다', () => {
  assert.equal(findShortcut(key(' ', 'Space')), 'togglePlay');
  assert.equal(findShortcut(key('ArrowLeft', 'ArrowLeft')), 'seekBack');
  assert.equal(findShortcut(key('ArrowRight', 'ArrowRight')), 'seekForward');
  assert.equal(findShortcut(key('ArrowLeft', 'ArrowLeft', { shiftKey: true })), 'prev');
  assert.equal(findShortcut(key('ArrowRight', 'ArrowRight', { shiftKey: true })), 'next');
  assert.equal(findShortcut(key('/', 'Slash')), 'search');
  assert.equal(findShortcut(key('?', 'Slash', { shiftKey: true })), 'help');
});

test('한글 입력 상태에서도 글자 단축키가 된다', () => {
  assert.equal(findShortcut(key('m', 'KeyM')), 'mute');
  assert.equal(findShortcut(key('ㅡ', 'KeyM')), 'mute');
  assert.equal(findShortcut(key('ㄴ', 'KeyS')), 'shuffle');
  assert.equal(findShortcut(key('ㄱ', 'KeyR')), 'repeat');
  assert.equal(findShortcut(key('ㅣ', 'KeyL')), 'lyrics');
  assert.equal(findShortcut(key('ㅂ', 'KeyQ')), 'queue');
});

test('Ctrl·⌘·Alt와 함께 누르면 브라우저 단축키를 가로채지 않는다', () => {
  assert.equal(findShortcut(key('r', 'KeyR', { ctrlKey: true })), null); // 새로고침
  assert.equal(findShortcut(key('l', 'KeyL', { metaKey: true })), null); // 주소창
  assert.equal(findShortcut(key('ArrowLeft', 'ArrowLeft', { altKey: true })), null); // 뒤로 가기
  assert.equal(findShortcut(key('M', 'KeyM', { shiftKey: true })), null);
  assert.equal(findShortcut(key('x', 'KeyX')), null);
});

test('안내에 쓸 이름과 키가 모두 있고, 동작 이름이 겹치지 않는다', () => {
  for (const s of SHORTCUTS) assert.ok(s.label && s.keys.length, s.action);
  assert.equal(new Set(SHORTCUTS.map((s) => s.action)).size, SHORTCUTS.length);
});

test('Shift+↑/↓는 볼륨, 그냥 ↑/↓는 목록 스크롤을 위해 비워 둔다', () => {
  assert.equal(findShortcut(key('ArrowUp', 'ArrowUp', { shiftKey: true })), 'volumeUp');
  assert.equal(findShortcut(key('ArrowDown', 'ArrowDown', { shiftKey: true })), 'volumeDown');
  assert.equal(findShortcut(key('ArrowUp', 'ArrowUp')), null);
  assert.equal(findShortcut(key('ArrowDown', 'ArrowDown')), null);
});

test('볼륨 한 칸 조절: 0~100% 안에서, 5% 단위로 맞춘다', async () => {
  const { stepVolume } = await import('../public/shortcuts.js');
  assert.equal(stepVolume(0.5, 1), 0.55);
  assert.equal(stepVolume(0.5, -1), 0.45);
  assert.equal(stepVolume(0.98, 1), 1);
  assert.equal(stepVolume(0.02, -1), 0);
  assert.equal(stepVolume(0.63, 1), 0.7); // 어중간한 값은 다음 칸으로 맞춤 (0.63+0.05=0.68 → 0.70)
  let v = 0;
  for (let i = 0; i < 20; i++) v = stepVolume(v, 1);
  assert.equal(v, 1); // 0.05씩 20번 = 정확히 100%
});
