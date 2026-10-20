# 🎵 My Music — 개인 음악 스트리밍 서버

내가 가진 음원 파일(MP3, FLAC 등)을 서버에 올려 두고 브라우저에서 듣는 웹앱입니다.
집 PC나 개인 서버에서 실행하고, 계정 하나로만 접속합니다.

> 직접 구매했거나 이용 권한이 있는 음원만 올려 주세요. 다른 사람에게 공개하거나
> 공유하면 저작권 문제가 생길 수 있습니다.

## 기능

- **로그인**: 처음 접속할 때 계정 하나를 만들고 이후 가입은 막힙니다. 비밀번호는 scrypt로 해시하고, 로그인 실패가 반복되면 잠시 차단합니다.
- **업로드**: 파일 선택 또는 창에 끌어다 놓기. 제목, 아티스트, 앨범, 트랙 번호, 커버 이미지를 태그에서 자동으로 읽습니다 (태그가 없으면 파일명을 제목으로 씀).
- **재생**: HTTP Range 스트리밍이라 탐색바로 원하는 위치로 바로 이동할 수 있습니다.
- **플레이어**: 재생/일시정지, 이전/다음, 셔플, 반복(전체/한 곡), 볼륨·음소거, 스페이스바로 재생 토글
- **재생 대기열**: 다음에 재생 / 대기열에 추가, 드래그로 순서 변경, 빼기. 새로고침해도 대기열과 재생 위치가 유지됩니다.
- **플레이리스트**: 만들기, 이름 변경, 삭제, 곡 추가(⋯ 메뉴 또는 사이드바의 플레이리스트 이름 위로 곡 끌어다 놓기), 드래그로 순서 변경

지원 형식: `mp3 flac m4a aac ogg opus wav webm` (재생 가능 여부는 브라우저에 따라 다를 수 있음)

## 실행

### Docker (권장)

```bash
cd music-player
docker compose up -d --build
```

브라우저에서 `http://localhost:3000`에 접속해 계정을 만드세요.
음원과 DB는 `./data` 폴더에 저장되며, 컨테이너는 uid 1000(node) 사용자로 실행됩니다.
`./data`에 쓰기 권한 오류가 나면 `sudo chown -R 1000:1000 data`를 실행하세요.

### Node.js로 직접 실행

Node.js 22.13 이상이 필요합니다 (내장 `node:sqlite` 사용).

```bash
cd music-player
npm install
npm start          # http://localhost:3000
npm test           # API 테스트
```

## 설정 (환경 변수)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `PORT` | `3000` | 서버 포트 |
| `DATA_DIR` | `./data` | 음원, 커버, DB(`library.db`) 저장 위치 |
| `MAX_UPLOAD_MB` | `200` | 파일 하나의 최대 크기 |
| `COOKIE_SECURE` | `false` | HTTPS로만 접속할 때 `true` |
| `TRUST_PROXY` | `false` | 리버스 프록시 뒤에서 실제 접속 IP를 쓰려면 `true` |

## 외부에서 접속하려면

집 밖에서 접속할 때는 HTTPS를 꼭 쓰세요. 비밀번호가 평문으로 오가면 안 됩니다.
가장 간단한 방법은 [Caddy](https://caddyserver.com/)를 앞에 두는 것입니다.

```
music.example.com {
    reverse_proxy localhost:3000
}
```

이렇게 둘 때는 `COOKIE_SECURE=true`, `TRUST_PROXY=true`를 켜 주세요.
집 회선이라면 공유기 포트포워딩 대신 Tailscale이나 Cloudflare Tunnel을 쓰는 게 더 안전합니다.

## 구조

```
music-player/
├── server/
│   ├── index.js       # 앱 구성, 설정, 에러 처리
│   ├── db.js          # SQLite 스키마
│   ├── auth.js        # 계정, 세션 쿠키, 로그인 제한
│   ├── tracks.js      # 업로드, 메타데이터, 스트리밍, 커버
│   └── playlists.js   # 플레이리스트 CRUD, 순서 변경
├── public/            # 프론트엔드 (빌드 없는 바닐라 JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
└── test/api.test.js
```

## API 요약

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/auth/status` | 로그인 상태, 최초 설정 필요 여부 |
| POST | `/api/auth/setup` · `/login` · `/logout` | 계정 만들기, 로그인, 로그아웃 |
| GET / POST | `/api/tracks` | 곡 목록 / 업로드 (`multipart`, 필드명 `files`) |
| DELETE | `/api/tracks/:id` | 곡 삭제 (파일 포함) |
| GET | `/api/tracks/:id/stream` · `/cover` | 오디오 스트림 (Range 지원), 커버 이미지 |
| GET / POST | `/api/playlists` | 플레이리스트 목록 / 만들기 |
| GET / PATCH / DELETE | `/api/playlists/:id` | 상세(곡 포함), 이름 변경, 삭제 |
| POST | `/api/playlists/:id/tracks` | 곡 추가 `{ trackIds: [] }` |
| DELETE | `/api/playlists/:id/tracks/:entryId` | 곡 빼기 |
| PUT | `/api/playlists/:id/order` | 순서 변경 `{ entryIds: [] }` |
