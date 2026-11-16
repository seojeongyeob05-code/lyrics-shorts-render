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
