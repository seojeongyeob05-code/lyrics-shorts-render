# lyrics-shorts-render
쇼츠메이커(수동)

가사(LRC) + 음원 + 배경으로 세로형 가사 쇼츠를 렌더링하는 도구. 진행 계획은 [ROADMAP.md](ROADMAP.md), 일지는 [DEVLOG.md](DEVLOG.md).

## 사용법

필요한 것: Python 3.10+, Pillow, ffmpeg

```
# 0:45부터 30초짜리 쇼츠 만들기
python3 -m shorts render song.lrc --audio song.mp3 --bg bg.jpg --start 0:45 --duration 30 -o out.mp4

# 0:50 장면을 PNG로 미리보기
python3 -m shorts frame song.lrc --bg bg.jpg --at 0:50
```

- 시간은 `45`, `0:45`, `1:02.5` 모두 가능
- `--duration`을 빼면 곡 끝까지(음원이 없으면 마지막 가사 줄까지)
- 폰트는 한글 폰트를 자동으로 찾음. 직접 지정: `--font 경로` 또는 환경변수 `SHORTS_FONT`

## 테스트

```
python3 -m unittest discover -s tests -t .
```
