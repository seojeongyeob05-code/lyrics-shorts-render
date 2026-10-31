# 개발 일지

## 2026-10-31 — 1일차: LRC 파서
- `shorts/lrc.py`: LRC 파싱(메타 태그, 다중 타임스탬프, offset, 소수 자릿수 1~3), 줄 끝 시각 계산, `line_at(t)`, 구간 `clip()`
- 테스트: `python3 -m unittest discover -s tests -t .` (8개 통과)
- 다음: Pillow로 프레임 한 장 그리기
