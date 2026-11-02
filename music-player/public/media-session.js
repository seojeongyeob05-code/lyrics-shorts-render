// Media Session API: 키보드 미디어 키, OS 미디어 컨트롤(Windows 볼륨 오버레이, macOS 제어 센터 등)과 연결한다.
const SEEK_STEP = 10;

export function trackMetadata(track, origin = '') {
  if (!track) return null;
  return {
    title: track.title,
    artist: track.artist || '알 수 없는 아티스트',
    album: track.album || '',
    artwork: track.hasCover ? [{ src: `${origin}/api/tracks/${track.id}/cover` }] : [],
  };
}

export function setupMediaSession({ audio, getTrack, onPlay, onPause, onNext, onPrev }) {
  const session = globalThis.navigator?.mediaSession;
  if (!session) return { update() {} };

  const handlers = {
    play: onPlay,
    pause: onPause,
    stop: onPause,
    nexttrack: onNext,
    previoustrack: onPrev,
    seekto: (d) => { audio.currentTime = d.seekTime; },
    seekforward: (d) => { audio.currentTime = Math.min(audio.currentTime + (d.seekOffset || SEEK_STEP), audio.duration || 0); },
    seekbackward: (d) => { audio.currentTime = Math.max(audio.currentTime - (d.seekOffset || SEEK_STEP), 0); },
  };
  for (const [action, handler] of Object.entries(handlers)) {
    try { session.setActionHandler(action, handler); } catch { /* 브라우저가 지원하지 않는 동작 */ }
  }

  const updatePosition = () => {
    if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
    try {
      session.setPositionState({
        duration: audio.duration,
        position: Math.min(audio.currentTime, audio.duration),
        playbackRate: audio.playbackRate || 1,
      });
    } catch { /* 위치 정보 미지원 */ }
  };
  ['loadedmetadata', 'seeked', 'ratechange', 'play', 'pause'].forEach((e) => audio.addEventListener(e, updatePosition));

  let shownId;
  return {
    // 곡이 바뀔 때만 메타데이터를 새로 만들고, 재생 상태는 매번 맞춘다.
    update() {
      const track = getTrack();
      if (track?.id !== shownId) {
        shownId = track?.id;
        const meta = trackMetadata(track, location.origin);
        session.metadata = meta ? new MediaMetadata(meta) : null;
      }
      session.playbackState = !track ? 'none' : audio.paused ? 'paused' : 'playing';
    },
  };
}
