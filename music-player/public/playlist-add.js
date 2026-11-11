// 플레이리스트에 곡을 넣기 전에 이미 들어 있는 곡을 가려낸다.
// 한 번에 고른 곡 안에서 같은 곡이 여러 번 나오면(플레이리스트 화면에서 고른 경우 등) 한 번만 센다.
export function planPlaylistAdd(existingIds, trackIds) {
  const existing = new Set(existingIds);
  const unique = [...new Set(trackIds)];
  const fresh = unique.filter((id) => !existing.has(id));
  return { all: unique, fresh, duplicates: unique.length - fresh.length };
}
