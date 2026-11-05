# NPC 초상화 생성 프롬프트

이미지 생성 AI(GPT 등)에 넣어 NPC 대화용 흉상 초상화를 만들기 위한 프롬프트.

## 쓰는 법
1. 경비원 `neutral` 한 장을 먼저 만들어 그림체를 확정한다.
2. 나머지 캐릭터는 확정된 이미지를 첨부하고 "같은 그림체로"를 덧붙인다. 스타일 블록은 매번 그대로 쓴다.
3. 표정 변형은 기본 표정 이미지를 첨부하고 "같은 캐릭터, 표정만 바꿔서"로 요청한다.
4. 파일 이름: `<캐릭터>_<표정>.png` (예: `guard_neutral.png`), 투명 배경 PNG.
5. 옷 색깔(경비원 검은 모자, 청소부 파란 앞치마, 할머니 보라 스카프, 카페 직원 검은 앞치마)은 게임 속 "가리키기" 퍼즐과 대사에 쓰이므로 반드시 지킨다.

## 공통 스타일 블록
```
Pixel art character bust portrait for a Korean-made 2D life-sim game, in the style of high-quality modern JRPG dialogue portraits.
Chest-up framing, character turned slightly to the left (3/4 view), looking toward the viewer.
Native resolution 128x128 pixels, upscaled 4x with nearest-neighbor (crisp square pixels, no blur, no anti-aliasing).
Limited palette of about 32 colors, 1-pixel dark brown outline, soft cel shading with 2-3 tones per color, small highlight on hair and eyes.
Neutral soft indoor lighting from the upper left. Fully transparent background (PNG with alpha). No text, no border, no frame, no watermark.
Setting: residents and staff of "Maple Court", a modern apartment building in an English-speaking town, autumn evening.
```

## 1. 경비원 (guard)
```
[STYLE BLOCK]
Character: security guard, man in his late 40s, short dark hair with a little gray at the temples, neat mustache.
Wears a BLACK peaked cap with a small silver badge, navy blue uniform shirt, shoulder walkie-talkie, wristwatch.
Personality: professional and a bit strict, but kind underneath.
Expression: [neutral, polite "Can I help you?" face]
```
표정: `neutral` / `puzzled`(한쪽 눈썹을 올리고 못 알아들은 얼굴) / `smile`(지갑을 돌려주는 따뜻한 미소)

## 2. 청소부 (janitor)
```
[STYLE BLOCK]
Character: building janitor, cheerful woman in her mid 50s, curly brown hair tied back under a patterned headscarf, rosy cheeks.
Wears a BLUE work apron over a gray long-sleeve shirt, yellow rubber gloves, a mop handle visible at the shoulder.
Personality: warm, chatty, motherly, calls everyone "honey".
Expression: [concerned, kind look, as if asking "Did you lose something?"]
```
표정: `worried` / `pointing`(옆을 가리키며 길 안내) / `laugh`

## 3. 옆집 할머니 Mrs. Park (grandma)
```
[STYLE BLOCK]
Character: elderly Korean-American grandmother in her 70s, short permed silver hair, round glasses on a beaded chain.
Wears a soft PURPLE scarf and a cream knitted cardigan, holding a small teacup.
Personality: gentle, patient, speaks slowly, the safe and kind neighbor.
Expression: [warm grandmotherly smile, eyes slightly crinkled]
```
표정: `smile` / `explain`(검지를 들고 단어 설명) / `delighted`(음료를 받고 활짝)

## 4. 카페 직원 (barista)
```
[STYLE BLOCK]
Character: young barista in their early 20s, energetic, messy bun hairstyle with a pencil stuck in it, small hoop earrings, freckles.
Wears a BLACK apron with a tiny coffee-bean logo over a rolled-up mustard shirt, holding a paper coffee cup with a lid.
Personality: always busy and fast-talking, friendly but rushed.
Expression: [quick customer-service smile, slightly out of breath]
```
표정: `rushed` / `confused`(몸을 앞으로 기울이고 못 알아들은 얼굴) / `cheerful`(컵을 건네며 밝게)
