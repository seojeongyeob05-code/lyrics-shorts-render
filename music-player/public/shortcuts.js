// 키보드 단축키 표. 화면의 단축키 안내도 이 표로 그린다.
// 글자 키는 e.code(자판 위치)로 비교한다. 한글 입력 상태에서 M을 누르면 e.key는 'ㅡ'이기 때문.
const withModifier = (e) => e.ctrlKey || e.metaKey || e.altKey;
const plainKey = (code) => (e) => !withModifier(e) && !e.shiftKey && e.code === code;

export const SHORTCUTS = [
  { action: 'togglePlay', keys: ['Space'], label: '재생 / 일시정지', match: (e) => !withModifier(e) && e.code === 'Space' },
  { action: 'seekBack', keys: ['←'], label: '5초 뒤로', match: (e) => !withModifier(e) && !e.shiftKey && e.key === 'ArrowLeft' },
  { action: 'seekForward', keys: ['→'], label: '5초 앞으로', match: (e) => !withModifier(e) && !e.shiftKey && e.key === 'ArrowRight' },
  { action: 'prev', keys: ['Shift', '←'], label: '이전 곡', match: (e) => !withModifier(e) && e.shiftKey && e.key === 'ArrowLeft' },
  { action: 'next', keys: ['Shift', '→'], label: '다음 곡', match: (e) => !withModifier(e) && e.shiftKey && e.key === 'ArrowRight' },
  { action: 'mute', keys: ['M'], label: '음소거 켜기/끄기', match: plainKey('KeyM') },
  { action: 'shuffle', keys: ['S'], label: '셔플 켜기/끄기', match: plainKey('KeyS') },
  { action: 'repeat', keys: ['R'], label: '반복 바꾸기 (안 함 → 전체 → 한 곡)', match: plainKey('KeyR') },
  { action: 'lyrics', keys: ['L'], label: '가사 패널 열기/닫기', match: plainKey('KeyL') },
  { action: 'queue', keys: ['Q'], label: '재생 대기열 열기/닫기', match: plainKey('KeyQ') },
  { action: 'search', keys: ['/'], label: '검색', match: (e) => !withModifier(e) && e.key === '/' },
  { action: 'help', keys: ['?'], label: '단축키 안내', match: (e) => !withModifier(e) && e.key === '?' },
];

// 다른 곳에서 처리하지만 안내에는 보여 줄 단축키
export const OTHER_SHORTCUTS = [
  { keys: ['Ctrl/⌘', 'A'], label: '곡 목록에서 모두 선택' },
  { keys: ['Esc'], label: '선택 해제 · 검색어 지우기 · 창 닫기' },
  { keys: ['Enter'], label: '싱크 맞추기 창에서 지금 줄 찍기' },
];

export function findShortcut(event) {
  return SHORTCUTS.find((s) => s.match(event))?.action ?? null;
}
