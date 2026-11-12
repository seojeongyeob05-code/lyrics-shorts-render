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
