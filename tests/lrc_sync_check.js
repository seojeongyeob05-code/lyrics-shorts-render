// tools/lrc-sync.html을 실제 브라우저에서 열어 탭 동작을 흉내 내고 결과를 JSON으로 출력한다.
// tests/test_sync_tool.py가 실행한다. 사용: node lrc_sync_check.js <html 경로>
const { chromium } = require("playwright");
const path = require("path");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.goto("file://" + path.resolve(process.argv[2]));

  const out = {};
  out.format = await page.evaluate(() =>
    [0, 1.234, 59.999, 61.5, 600.005, -3].map(LrcSync.formatTime));

  // 가사 입력 → 탭(지연 보정 0.15초) → 쉼 → 마지막 줄
  await page.fill("#lyrics", "  첫 줄  \n\n둘째 줄\n셋째 줄\n");
  await page.dispatchEvent("#lyrics", "input");
  out.tapLabel = await page.textContent("#tap");
  out.afterTaps = await page.evaluate(() => {
    app.tap(1.15); app.tap(3.65); app.gap(6.15); app.tap(8.15);
    return app.lrc();
  });
  out.tapDisabled = await page.isDisabled("#tap");
  out.extraTap = await page.evaluate(() => app.tap(9));  // 줄이 다 찼으면 무시

  // 취소는 마지막 탭부터
  out.afterUndo = await page.evaluate(() => { app.undo(); app.undo(); return app.lrc(); });

  // 다시 열어도 작업이 남아 있다(localStorage)
  await page.reload();
  out.afterReload = await page.evaluate(() => app.lrc());

  // 가사를 고치면 바뀐 줄부터의 탭은 지워진다
  out.afterEdit = await page.evaluate(() => { app.setLyrics("첫 줄\n바뀐 둘째 줄\n셋째 줄"); return app.lrc(); });

  // 키보드: Space = 탭, Backspace = 취소 (재생 위치 0초 → 보정 후 0초)
  await page.evaluate(() => app.reset());
  await page.click("h1");
  await page.keyboard.press("Space");
  out.afterKey = await page.evaluate(() => app.lrc());
  await page.keyboard.press("Backspace");
  out.afterKeyUndo = await page.evaluate(() => app.lrc());

  // 폰 화면에서 가로 스크롤이 생기지 않는다
  out.overflowX = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  out.errors = errors;
  console.log(JSON.stringify(out));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
