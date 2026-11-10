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

### 노래방식 하이라이트

Enhanced LRC처럼 단어 앞에 `<분:초.소수>`를 붙이면 부르는 만큼 글자가 채워집니다.

```
[00:12.00]<00:12.00>바람이 <00:12.80>불어오는 <00:13.90>곳<00:14.60>
```

## 테스트

```
python3 -m unittest discover -s tests -t .
```
