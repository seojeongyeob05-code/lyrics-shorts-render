// 플레이리스트를 .m3u8로 내보내고, 다른 플레이어에서 만든 .m3u/.m3u8을 라이브러리 곡과 짝지어 가져온다.
// 서버의 파일 이름은 임의 문자열이라, 곡은 "아티스트 - 제목"으로 짝짓는다.

const label = (t) => (t.artist ? `${t.artist} - ${t.title}` : t.title);

export function toM3u(tracks) {
  const lines = ['#EXTM3U'];
  for (const t of tracks) {
    lines.push(`#EXTINF:${Math.round(t.duration ?? -1)},${label(t)}`);
    lines.push(label(t).replace(/[\\/:*?"<>|]/g, '_'));
  }
  return `${lines.join('\n')}\n`;
}

// 텍스트 파일은 UTF-8이 아니면 EUC-KR(CP949)로 읽는다.
export function decodeText(buffer) {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buffer);
  } catch {
    return new TextDecoder('euc-kr').decode(buffer);
  }
}

// 항목마다 { info: EXTINF의 이름 부분, path } 를 돌려준다. EXTINF가 없는 단순 목록도 읽는다.
export function parseM3u(text) {
  const entries = [];
  let info = null;
  for (const raw of text.replace(/^\uFEFF/, '').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('#EXTINF:')) {
      const comma = line.indexOf(',');
      info = comma === -1 ? null : line.slice(comma + 1).trim() || null;
    } else if (!line.startsWith('#')) {
      entries.push({ info, path: line });
      info = null;
    }
  }
  return entries;
}

const norm = (s) => (s || '').normalize('NFC').toLowerCase().replace(/\s+/g, ' ').trim();

// 경로에서 파일 이름만, 확장자 없이 ("C:\\Music\\가수 - 노래.mp3" → "가수 - 노래")
function baseName(p) {
  const name = p.split(/[\\/]/).pop();
  try { return decodeURIComponent(name).replace(/\.[^.]+$/, ''); } catch { return name.replace(/\.[^.]+$/, ''); }
}

// 항목을 라이브러리 곡 id로 바꾼다. "아티스트 - 제목"이 정확히 맞는 곡을 먼저 찾고,
// 없으면 제목이 같은 곡이 딱 하나일 때만 그 곡으로 본다.
export function matchEntries(entries, library) {
  const byLabel = new Map();
  const byTitle = new Map();
  for (const t of library) {
    byLabel.set(norm(label(t)), t.id);
    const key = norm(t.title);
    byTitle.set(key, byTitle.has(key) ? null : t.id);
  }
  const find = (text) => {
    if (!text) return undefined;
    const key = norm(text);
    if (byLabel.has(key)) return byLabel.get(key);
    if (byTitle.get(key)) return byTitle.get(key);
    const dash = key.indexOf(' - ');
    if (dash !== -1 && byTitle.get(key.slice(dash + 3))) return byTitle.get(key.slice(dash + 3));
    return undefined;
  };
  const ids = [];
  const unmatched = [];
  for (const e of entries) {
    const id = find(e.info) ?? find(baseName(e.path));
    if (id) ids.push(id);
    else unmatched.push(e.info || baseName(e.path));
  }
  return { ids, unmatched };
}
