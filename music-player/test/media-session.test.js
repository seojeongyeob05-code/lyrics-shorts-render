import { test } from 'node:test';
import assert from 'node:assert/strict';
import { trackMetadata, setupMediaSession } from '../public/media-session.js';

test('곡 정보로 OS에 보낼 메타데이터를 만든다', () => {
  assert.deepEqual(trackMetadata({ id: 3, title: 'Night Drive', artist: 'City Lights', album: 'Neon', hasCover: true }, 'http://x'), {
    title: 'Night Drive',
    artist: 'City Lights',
    album: 'Neon',
    artwork: [{ src: 'http://x/api/tracks/3/cover' }],
  });
});

test('아티스트·앨범·커버가 없어도 빈칸 없이 채운다', () => {
  assert.deepEqual(trackMetadata({ id: 1, title: '봄날의 노래', artist: null, album: null, hasCover: false }), {
    title: '봄날의 노래',
    artist: '알 수 없는 아티스트',
    album: '',
    artwork: [],
  });
  assert.equal(trackMetadata(undefined), null);
});

test('Media Session을 지원하지 않는 환경에서는 아무것도 하지 않는다', () => {
  const session = setupMediaSession({ audio: {}, getTrack: () => null });
  assert.doesNotThrow(() => session.update());
});
