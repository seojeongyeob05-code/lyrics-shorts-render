// 곡을 아티스트별·앨범별로 묶는다.
export const UNKNOWN_ARTIST = '알 수 없는 아티스트';
export const VARIOUS_ARTISTS = '여러 아티스트';

const collator = new Intl.Collator('ko', { sensitivity: 'base', numeric: true });

const byDiscAndTrack = (a, b) => (a.discNo ?? 0) - (b.discNo ?? 0)
  || (a.trackNo ?? 0) - (b.trackNo ?? 0)
  || collator.compare(a.title, b.title);

// 앨범은 이름으로만 묶는다. 컴필레이션처럼 곡마다 아티스트가 달라도 한 앨범으로 보이게 하기 위해서다.
export function groupTracks(tracks, kind) {
  const groups = new Map();
  for (const track of tracks) {
    const name = kind === 'artist' ? (track.artist || UNKNOWN_ARTIST) : track.album;
    if (!name) continue; // 앨범 정보가 없는 곡은 앨범 목록에 넣지 않음
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name).push(track);
  }
  return [...groups].map(([name, list]) => {
    const sorted = kind === 'album'
      ? [...list].sort(byDiscAndTrack)
      : [...list].sort((a, b) => collator.compare(a.album || '￿', b.album || '￿') || byDiscAndTrack(a, b));
    const artists = [...new Set(list.map((t) => t.artist || UNKNOWN_ARTIST))];
    const albums = new Set(list.map((t) => t.album).filter(Boolean));
    return {
      name,
      tracks: sorted,
      cover: sorted.find((t) => t.hasCover) ?? null,
      subtitle: kind === 'album'
        ? `${artists.length > 1 ? VARIOUS_ARTISTS : artists[0]} · ${list.length}곡`
        : `${albums.size ? `앨범 ${albums.size}개 · ` : ''}${list.length}곡`,
    };
  }).sort((a, b) => (a.name === UNKNOWN_ARTIST) - (b.name === UNKNOWN_ARTIST) || collator.compare(a.name, b.name));
}
