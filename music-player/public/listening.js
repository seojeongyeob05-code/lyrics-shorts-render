// 들은 횟수 세기와 "최근 추가한 곡"·"많이 들은 곡" 목록.

export const MAX_THRESHOLD = 240; // 아무리 긴 곡도 4분 들으면 한 번으로 센다
export const SMART_LIST_LIMIT = 100;

// 곡의 절반(최대 4분)을 들으면 한 번 들은 것으로 친다. 길이를 모르면 30초.
export function playThreshold(duration) {
  if (!Number.isFinite(duration) || duration <= 0) return 30;
  return Math.min(duration / 2, MAX_THRESHOLD);
}

// 재생 위치가 조금씩 흘러간 시간만 더한다. 탐색바로 건너뛴 구간은 듣지 않은 것으로 본다.
export function createListenTracker(onCount) {
  let last = null;
  let listened = 0;
  let counted = false;
  return {
    tick(position, duration) {
      if (last != null) {
        const delta = position - last;
        if (delta > 0 && delta < 1.5) listened += delta;
      }
      last = position;
      if (!counted && listened >= playThreshold(duration)) {
        counted = true;
        onCount();
      }
    },
    seeked(position) { last = position; },
    reset() {
      last = null;
      listened = 0;
      counted = false;
    },
  };
}

export const recentTracks = (tracks, limit = SMART_LIST_LIMIT) =>
  [...tracks].sort((a, b) => b.createdAt - a.createdAt || b.id - a.id).slice(0, limit);

export const topTracks = (tracks, limit = SMART_LIST_LIMIT) =>
  tracks.filter((t) => t.playCount > 0)
    .sort((a, b) => b.playCount - a.playCount || (b.lastPlayedAt ?? 0) - (a.lastPlayedAt ?? 0))
    .slice(0, limit);

export const recentlyPlayed = (tracks, limit = SMART_LIST_LIMIT) =>
  tracks.filter((t) => t.lastPlayedAt)
    .sort((a, b) => b.lastPlayedAt - a.lastPlayedAt)
    .slice(0, limit);

// "방금", "5분 전", "3시간 전", "어제", "4일 전", 그보다 오래되면 날짜
export function timeAgo(ts, now = Date.now()) {
  if (!ts) return '';
  const min = Math.floor((now - ts) / 60_000);
  if (min < 1) return '방금';
  if (min < 60) return `${min}분 전`;
  if (min < 24 * 60) return `${Math.floor(min / 60)}시간 전`;
  const day = (t) => { const d = new Date(t); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86_400_000; };
  const days = day(now) - day(ts);
  if (days <= 1) return '어제';
  if (days < 7) return `${days}일 전`;
  const d = new Date(ts);
  return `${d.getFullYear()}. ${d.getMonth() + 1}. ${d.getDate()}.`;
}
