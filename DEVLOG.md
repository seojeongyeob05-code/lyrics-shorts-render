# 개발 일지

## 2026-10-31 — 1일차: LRC 파서
- `shorts/lrc.py`: LRC 파싱(메타 태그, 다중 타임스탬프, offset, 소수 자릿수 1~3), 줄 끝 시각 계산, `line_at(t)`, 구간 `clip()`
- 테스트: `python3 -m unittest discover -s tests -t .` (8개 통과)
- 다음: Pillow로 프레임 한 장 그리기

## 2026-11-01 — 2일차: 프레임 렌더러
- `shorts/frame.py`: `Style`(크기·색·폰트 설정), `cover_fit()`(배경 이미지를 비율 유지로 꽉 채우고 가운데 자르기), `FrameRenderer.render(lyrics, t)` — 현재 줄은 세로 가운데에 밝게, 다음 줄은 아래에 흐리게. 첫 줄 전처럼 가사가 비는 구간에는 곧 나올 줄만 미리 보여줌
- 테스트 7개 추가(전체 15개 통과)
- 정리: 1일차에 실수로 커밋된 `__pycache__` 제거, `.gitignore` 추가
- 메모: 아직 Pillow 기본 폰트라 한글이 안 나옴. 이 컨테이너엔 한글 폰트가 없음
- 다음: 3단계 — 한글 폰트(경로 지정 + 시스템 폰트 자동 탐색, 없으면 명확한 에러) + 화면 폭을 넘는 줄 자동 줄바꿈

## 2026-11-02 — 3일차: 한글 폰트 + 자동 줄바꿈
- `shorts/text.py`
  - `find_korean_font()`: `SHORTS_FONT` 환경변수 → `fc-list :lang=ko` → 흔한 경로 순으로 찾음. 나눔/Noto CJK/맑은 고딕 등 자막에 어울리는 폰트와 굵은 글꼴을 우선, unifont 같은 비트맵 폰트는 뒤로
  - `wrap()`: 화면 폭(기본 86%)을 넘으면 공백 단위로 줄바꿈, 한 단어가 너무 길면 글자 단위로 자름
- `frame.py`: 폰트 자동 탐색 사용, 한 가사가 여러 줄이 되면 블록째 세로 가운데 정렬하고 다음 줄은 그 아래에 배치
- 테스트 8개 추가(전체 23개 통과). 한글 렌더 테스트는 폰트가 없는 환경에선 건너뜀
- 메모: 이 컨테이너는 외부 폰트 다운로드가 막혀 있어 wqy-zenhei로 확인함. 실제 사용 시엔 `SHORTS_FONT=나눔고딕Bold.ttf` 같은 식으로 지정 권장
- 다음: 4단계 — 프레임을 ffmpeg 파이프로 흘려 mp4 만들고 음원 합치기

## 2026-11-03 — 4일차: mp4 출력 + 음원 합치기
- `shorts/video.py`
  - `render_video(lyrics, out, duration, renderer, opts, audio, audio_start)`: 프레임을 raw RGB로 ffmpeg 표준입력에 흘려 H.264 mp4(yuv420p, faststart) 생성. 음원이 있으면 `audio_start`초부터 잘라 AAC로 함께 넣음
  - 화면에 보이는 줄이 같으면 직전 프레임을 재사용(`FrameRenderer.state_key`) → 10초·300프레임 중 실제로 그린 건 6장, 1080x1920 렌더 약 2.6초
  - ffmpeg가 실패하면 에러 메시지를 담아 `RuntimeError`
- 테스트 6개 추가(전체 29개 통과): 명령 구성, 상태 키, 실제 인코딩(영상만/음원 구간 포함/실패 보고)
- 정리: 파이프 닫기 누락으로 인한 ResourceWarning, Pillow 14에서 사라질 `getdata()` 사용 제거
- 다음: 5단계 — CLI(`python -m shorts render song.lrc --audio a.mp3 --bg bg.jpg --start 0:45 --duration 30`). `--start`가 있으면 `Lyrics.clip()` + `audio_start`로 이어 붙이면 되므로 6단계(구간 자르기)도 거의 같이 끝날 듯

## 2026-11-04 — 5일차: CLI + 구간 렌더
- `shorts/cli.py`, `python -m shorts`
  - `render`: `--audio`, `--bg`, `--font`, `--start`, `--duration`, `--fps`, `-o`. 음원이 있으면 ffprobe로 곡 길이를 읽어 마지막 줄 끝과 `--duration` 상한으로 씀. `--start` 구간은 `Lyrics.clip()` + 음원 `audio_start`로 맞춤 → 로드맵 6단계(구간 자르기)도 함께 완료
  - `frame`: 특정 시각 한 장면을 PNG로 미리보기 (영상 뽑기 전에 배경/폰트 확인용)
  - 시간 표기 `45` / `0:45` / `1:02.5` 지원, 잘못된 입력·곡 길이를 넘는 시작점은 알기 쉬운 에러로
- README에 사용법 추가
- 테스트 6개 추가(전체 35개 통과). 12초 하이라이트 1080x1920 렌더 약 2.5초
- 다음: 7단계 — 효과. 우선 줄이 바뀔 때 짧은 페이드(이게 들어가면 프레임 재사용 키에 "전환 중" 상태가 추가돼야 함)와 하단 진행 바
