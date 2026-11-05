// LRC 가사 파싱. "[01:23.45]가사" 형식이면 싱크 가사로, 시간 표시가 없으면 일반 가사로 다룬다.
const TIME_TAG = /\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]/g;
const META_TAG = /^\[([a-z#]+):(.*)\]$/i;

export function parseLyrics(text) {
  const raw = String(text ?? '').replace(/^﻿/, '').split(/\r?\n/);
  let offsetMs = 0;
  const timed = [];

  raw.forEach((line, order) => {
    const trimmed = line.trim();
    const meta = trimmed.match(META_TAG);
    if (meta && !/^\d/.test(meta[1])) {
      if (meta[1].toLowerCase() === 'offset') offsetMs = Number(meta[2]) || 0;
      return; // [ti:], [ar:] 같은 정보 태그는 표시하지 않음
    }
    const times = [...trimmed.matchAll(TIME_TAG)];
    if (!times.length) return;
    const lyric = trimmed.replace(TIME_TAG, '').trim();
    for (const [, m, s, frac = '0'] of times) {
      const fraction = Number(frac) / 10 ** frac.length;
      timed.push({ time: Number(m) * 60 + Number(s) + fraction, text: lyric, order });
    }
  });

  if (timed.length) {
    // LRC의 offset은 양수면 가사를 더 일찍 보여 준다.
    const lines = timed
      .sort((a, b) => a.time - b.time || a.order - b.order)
      .map(({ time, text: t }) => ({ time: Math.max(0, time - offsetMs / 1000), text: t }));
    return { synced: true, lines };
  }

  const lines = raw.map((l) => l.trim());
  while (lines.length && !lines[0]) lines.shift();
  while (lines.length && !lines.at(-1)) lines.pop();
  return { synced: false, lines: lines.map((t) => ({ time: null, text: t })) };
}

// 재생 위치에 해당하는 줄 번호 (아직 첫 줄 전이면 -1).
export function currentLineIndex(lines, seconds) {
  let lo = 0;
  let hi = lines.length - 1;
  let found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (lines[mid].time <= seconds) { found = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return found;
}
