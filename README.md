# lyrics-shorts-render
쇼츠메이커(수동)

가사(LRC) + 음원 + 배경으로 세로형 가사 쇼츠를 렌더링하는 도구. 진행 계획은 [ROADMAP.md](ROADMAP.md), 일지는 [DEVLOG.md](DEVLOG.md).

## 사용법

필요한 것: Python 3.10+, Pillow, numpy, ffmpeg

```
# 0:45부터 30초짜리 쇼츠 만들기
python3 -m shorts render song.lrc --audio song.mp3 --bg bg.jpg --start 0:45 --duration 30 -o out.mp4

# 0:50 장면을 PNG로 미리보기
python3 -m shorts frame song.lrc --bg bg.jpg --at 0:50
```

- 곡 제목·가수는 LRC의 `[ti:]`/`[ar:]`를 화면 위쪽에 표시. `--title`/`--artist`로 바꾸고, 빈 문자열(`--title ""`)이면 숨김
- `--cover 앨범아트.jpg`: 곡 정보와 가사 사이에 앨범 아트. 모양은 스타일의 `cover_shape`(`rounded`/`circle`/`square`), 크기 `cover_size`, 위치 `cover_y`
- `--preview`: 절반 해상도·15fps로 5배쯤 빠르게 뽑아 보기(`노래.preview.mp4`). 확인 후 옵션을 빼고 다시 렌더
- 시간은 `45`, `0:45`, `1:02.5` 모두 가능
- 여러 구간 한 번에: `--start 0:45,1:30 --duration 20` → `노래-1.mp4`, `노래-2.mp4` (길이도 `20,15`처럼 구간마다 줄 수 있음)
- `--duration`을 빼면 곡 끝까지(음원이 없으면 마지막 가사 줄까지)
- 폰트는 한글 폰트를 자동으로 찾음. 직접 지정: `--font 경로` 또는 환경변수 `SHORTS_FONT`

### 자막 파일로 내보내기

```
python3 -m shorts export 노래.lrc                    # 노래.srt (유튜브·대부분의 편집기)
python3 -m shorts export 노래.json --format ass      # 노래.ass (글꼴·색·위치, 노래방 채우기 효과)
python3 -m shorts export 노래.lrc --start 0:45 --duration 20   # 렌더한 쇼츠 구간과 시각 맞추기
```

ASS는 스타일(`--style`)의 화면 크기·글자 크기·색·테두리·가사 위치를 따르고, 단어 타이밍이 있는 줄은
`\kf` 태그로 왼쪽부터 채워집니다(VLC, Aegisub, ffmpeg `ass` 필터 등에서 보임).

### 쇼츠 앱에 가려지는 자리 확인

```
python3 -m shorts frame 노래.json --at 0:50 --guide
```

위쪽 메뉴, 오른쪽 버튼 줄(좋아요·댓글·공유), 아래쪽 제목·설명 자리를 반투명 빨강으로 표시합니다
(1080x1920 기준 대략적인 위치). `render`/`frame`은 가사·곡 정보·앨범 아트·진행 바가 그 자리에 걸리면
`주의:` 메시지로 알려줍니다.

### 곡 설정 파일 하나로

옵션이 길어지면 JSON 하나에 적어 두고 그 파일로 렌더합니다. 경로는 JSON 파일 위치 기준이고,
명령줄 옵션을 함께 주면 그쪽이 우선입니다. 예시: `examples/demo/demo.json`

```json
{
  "lyrics": "노래.lrc",
  "audio": "노래.mp3",
  "bg": "배경.jpg",
  "cover": "앨범.jpg",
  "style": "photo",
  "title": "제목", "artist": "가수",
  "start": ["0:45", "1:30"],
  "duration": 20
}
```

```
python3 -m shorts render 노래.json             # 노래-1.mp4, 노래-2.mp4
python3 -m shorts render 노래.json --preview   # 빠른 확인
python3 -m shorts frame 노래.json --at 0:50    # 한 장면
```

`style`에는 프리셋 이름, 스타일 파일, 또는 `{"extends": "neon", "font_size": 80}`처럼 직접 적을 수 있습니다.

### 가사 타이밍 만들기 (LRC가 없을 때)

`tools/lrc-sync.html`을 브라우저로 엽니다(폰도 됨). 음원을 고르고 가사를 붙여넣은 뒤,
노래를 들으며 각 줄이 시작될 때 **다음 줄 시작**을 탭하면 LRC가 만들어집니다.
`쉼`은 앞 줄을 끝내는 표시, 반응 지연 보정(기본 0.15초)만큼 앞당겨 기록합니다.
**탭 단위 → 단어마다(노래방)**로 바꾸면 단어마다 탭해서 노래방 하이라이트용 LRC(`<시각>단어`)를 만듭니다.
파일은 브라우저 밖으로 나가지 않고, 작업 중인 내용은 브라우저에 저장돼 다시 열어도 남아 있습니다.

### 스타일

```
python3 -m shorts styles                       # 내장 프리셋 목록
python3 -m shorts render song.lrc --bg photo.jpg --style photo   # 사진 배경: 흐리게·어둡게 + 천천히 확대 + 글자 테두리
python3 -m shorts render song.lrc --style neon
python3 -m shorts render song.lrc --style my-theme.json
```

내 테마는 바꾸고 싶은 값만 JSON으로 적으면 됩니다. 항목 이름은 `shorts/frame.py`의 `Style` 참고.

```json
{
  "extends": "neon",
  "text_color": "#FFE066",
  "font_size": 84,
  "center_y": 0.62,
  "font_path": "fonts/NanumSquareRoundEB.ttf"
}
```

### 줄 바뀜 효과

스타일의 `transition`: `"fade"`(기본, 사라졌다 나타남) 또는 `"slide"`(다음 줄 미리보기 자리에서
위로 올라옴). 시간은 `fade`(초).
`"reveal": "typewriter"`를 함께 쓰면 현재 줄이 한 글자씩 나타납니다(속도 `reveal_cps`, 줄 길이의 60% 안에 다 나옴).

### 음악 반응 막대

스타일에 `"visualizer": true`를 넣고 `--audio`와 함께 렌더하면 진행 바 위에 저음→고음 막대가
음악에 맞춰 움직입니다. 막대 수 `viz_bands`, 높이 `viz_height`, 색 `viz_color`.

```json
{"extends": "sunset", "visualizer": true, "viz_color": "#FFF6E8"}
```

### 노래방식 하이라이트

Enhanced LRC처럼 단어 앞에 `<분:초.소수>`를 붙이면 부르는 만큼 글자가 채워집니다.

```
[00:12.00]<00:12.00>바람이 <00:12.80>불어오는 <00:13.90>곳<00:14.60>
```

## 테스트

```
python3 -m unittest discover -s tests -t .
```
