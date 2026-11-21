# chem-daily 테스트

Playwright(전역 설치)와 미리 설치된 Chromium(`/opt/pw-browsers/chromium`)을 씁니다.

```bash
cd chem/tests
node check-bank.js                                    # 문제 은행 형식 점검 (브라우저 없음)
NODE_PATH=$(npm root -g) node lesson.js '13장 화학 평형' '{"높은 산":"<정답 보기 그대로>"}'
NODE_PATH=$(npm root -g) node all.js                  # 22개 레슨 끝까지 풀기 (몇 분 걸림)
```
