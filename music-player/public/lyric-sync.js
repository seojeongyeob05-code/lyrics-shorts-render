// 가사 싱크 맞추기: 노래를 들으며 각 줄이 시작될 때 시간을 찍어 LRC를 만든다.

export function lrcTime(seconds) {
  const cs = Math.max(0, Math.round(seconds * 100));
  const pad = (n) => String(n).padStart(2, '0');
  return `[${pad(Math.floor(cs / 6000))}:${pad(Math.floor(cs / 100) % 60)}.${pad(cs % 100)}]`;
}

// parseLyrics 결과의 줄로 시작한다. 이미 싱크된 가사면 기존 시간을 그대로 두고 고칠 수 있다.
export function createSync(lines) {
  const items = lines.map((l) => ({ text: l.text, time: l.time ?? null }));
  const first = items.findIndex((l) => l.time == null);
  return { lines: items, target: first === -1 ? items.length : first };
}

// 지금 줄에 시간을 찍고 다음 줄로 넘어간다.
export function stamp(sync, seconds) {
  if (sync.target >= sync.lines.length) return sync;
  const lines = sync.lines.map((l, i) => (i === sync.target ? { ...l, time: Math.round(seconds * 100) / 100 } : l));
  return { lines, target: sync.target + 1 };
}

// 바로 앞 줄로 돌아가 그 줄의 시간을 지운다.
export function undo(sync) {
  if (sync.target === 0) return sync;
  const target = sync.target - 1;
  return { lines: sync.lines.map((l, i) => (i === target ? { ...l, time: null } : l)), target };
}

export const jumpTo = (sync, index) => ({ ...sync, target: Math.max(0, Math.min(index, sync.lines.length)) });

export const missingCount = (sync) => sync.lines.filter((l) => l.time == null).length;

// 시간을 찍은 줄만 시간순으로 LRC로 만든다.
export function toLrc(sync) {
  return sync.lines
    .filter((l) => l.time != null)
    .sort((a, b) => a.time - b.time)
    .map((l) => `${lrcTime(l.time)}${l.text}`)
    .join('\n');
}
