# lyrics-shorts-render
쇼츠메이커(수동)

## 가상 성대 · 발성 물리엔진 쇼츠

근육 값을 바꾸면 물리 시뮬레이션이 실제로 소리를 만들고, 그 과정을 9:16 영상(1080×1920, 30fps)으로 그립니다.

```
pip install -r requirements.txt     # ffmpeg 필요
python3 make_short.py scenarios/default.json -o out/short.mp4
python3 make_short.py scenarios/default.json --stills 3,20,45   # 특정 시점 PNG만 확인
```

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
