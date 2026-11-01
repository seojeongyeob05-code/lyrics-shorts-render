// 곡 검색: 제목·아티스트·앨범에서 찾는다. 공백과 대소문자는 무시하고, 초성만 입력하면 초성끼리 비교한다.
const CHOSUNG = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
const HANGUL_START = 0xac00;
const HANGUL_COUNT = 11172;

export function toChosung(text) {
  return [...text].map((ch) => {
    const code = ch.charCodeAt(0) - HANGUL_START;
    return code >= 0 && code < HANGUL_COUNT ? CHOSUNG[Math.floor(code / 588)] : ch;
  }).join('');
}

// macOS에서 온 파일명은 자모가 분리된(NFD) 상태일 수 있어 NFC로 합친다.
const normalize = (text) => (text || '').normalize('NFC').toLowerCase().replace(/\s+/g, '');

export function matchesQuery(track, query) {
  const q = normalize(query);
  if (!q) return true;
  // 필드 사이에 공백이 아닌 구분자를 둬 서로 다른 필드에 걸친 일치를 막는다.
  const haystack = [track.title, track.artist, track.album].map(normalize).join('\u0001');
  if (haystack.includes(q)) return true;
  return [...q].every((ch) => CHOSUNG.includes(ch)) && toChosung(haystack).includes(q);
}
