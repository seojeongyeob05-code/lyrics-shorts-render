# lyrics-shorts-render
쇼츠메이커(수동)

## 가상 성대 · 발성 물리엔진 쇼츠

근육 값을 바꾸면 물리 시뮬레이션이 실제로 소리를 만들고, 그 과정을 9:16 영상(1080×1920, 30fps)으로 그립니다.

```
pip install -r requirements.txt     # ffmpeg 필요
python3 make_short.py scenarios/default.json -o out/short.mp4
python3 make_short.py scenarios/default.json --stills 3,20,45   # 특정 시점 PNG만 확인
```

## 발성 분석 (메인 기능)

녹음 한 개를 넣으면 물리엔진을 거꾸로 돌려 근육 사용을 추정하고, 어디서 힘이 새는지 진단한 뒤,
같은 음정을 교정한 근육 값으로 다시 합성해 들려줍니다.

```
python3 analyze_voice.py 내녹음.m4a              # mp3/m4a/wav 등 ffmpeg 가 읽는 형식
python3 analyze_voice.py 내녹음.m4a --no-video   # 리포트와 소리만
```

결과 (`out/analysis/<파일이름>/`)
- `report.md`, `report.json`: 균형 점수, 음역, 근육 추정값 → 교정값, 문제별 근거·원인·연습법
- `card.png`: 결과 카드
- `fitted.wav`: 내 녹음을 물리엔진으로 다시 계산한 소리, `corrected.wav`: 같은 음정을 교정한 소리
- `analysis.mp4`: 결과 카드 → 내 소리(근육 추정 시각화) → 고친 소리 (9:16)

### 동작 방식 (`voiceanalysis/`)
1. `features.py`: 10 ms 마다 음높이(YIN), 크기, HNR, H1–H2, CPP, 스펙트럼 기울기를 재고 음(note) 단위로 나눔
2. `inverse.py`: 근육 값 격자(ct·ta·lca·ps × 목소리 높이 4종, 3600개)를 엔진으로 합성해 같은 특징을 잰
   역추정 표(`data/inverse_table.npz`)에서, 음마다 같은 음높이 근처에서 특징이 가장 비슷한 조합을 찾음.
   ct 는 장력 식을 거꾸로 풀어 음높이에서 계산
3. `diagnose.py`: 바람 샘 / 눌림 / 고음을 숨으로 밀기 / 고음에서 두꺼운 성대 / 음 흔들림 / 프레이즈 끝 힘 빠짐
4. `analyze.py`: 교정 근육 궤적을 만들고, 합성 결과의 음높이를 재서 ct 를 고쳐 다시 합성 (원래 음정 유지)

표를 다시 만들려면 `python3 -c "from voiceanalysis.inverse import build_table; build_table()"` (약 30초).
검증: `python3 tests/test_analysis.py` — 습관을 알고 합성한 목소리 4개(건강/바람/밀기/눌림)를 맞히는지 확인.

한계: 모델은 '아' 모음 기준이라 가사가 많은 노래보다 '아~' 음계나 모음 위주 노래에서 더 정확합니다.
녹음 기기마다 크기가 달라 폐압은 녹음 안의 상대적인 변화로만 추정합니다. 의학적 진단이 아닙니다.

### 소리 엔진 (`vocalsim/`)
- `muscles.py`: 근육 활성도를 성대 파라미터로 바꿈 (Titze & Story 규칙을 단순화)
  - `ct` 윤상갑상근: 성대를 늘임 → 음높이 상승
  - `ta` 갑상피열근: 성대를 두껍게 → 닫히는 시간 증가, 굵은 소리
  - `lca` 외측윤상피열근: 성대를 모음 → 낮으면 바람 섞인 소리, 높으면 눌린 소리
  - `ps` 폐압 (cmH₂O): 크기, 음높이 약간 상승
- `engine.py`: Ishizaka-Flanagan / Steinecke-Herzel 2질량 성대 모델 (충돌 포함)
  + 베르누이 성문 기류 + 레이놀즈 수 기반 난류 잡음 + 44구간 Kelly-Lochbaum 성도 + 입술 방사. numba로 가속
- `tract.py`: 모음별 성도 지름 (Pink Trombone 혀 모델). `a e i o u`

### 시나리오 (`scenarios/*.json`)
구간마다 `dur`(초), `focus`(`ct`/`ta`/`lca`/`ps`, 상단 슬라이더), `title`, `sub`, 그리고
`keys`(`[구간 내 시각, {파라미터: 값}]`, 코사인 보간; `ps: 0`이면 들숨), `captions`(`[시작, 끝, "자막"]`)를 씁니다.
`vowel`, `vib`(비브라토, 반음 단위)도 키로 바꿀 수 있습니다.

### 화면 구성 (`render/`)
상단 근육 슬라이더와 음높이·크기, 성도 2D 도식과 관 단면 도식, 슬로모션 성대(위에서 본 모습과 2질량 단면),
폐·횡격막과 근육 활성 막대, 스펙트로그램, 자막.

폰트: Pretendard (SIL OFL 1.1, `fonts/LICENSE-Pretendard.txt`)
