# t248 — 🔴 t246 의 결론이 반증됐다. 채널은 눈멀지 않았고, 내가 틀린 필드를 봤다.

기준: 워크트리 `.claude/worktrees/t248` · 브랜치 `WT-fixture-addressing` · base `origin/main fa0a2f6`
2026-09-02 · **콘솔 쓰기 정확히 4건** (`Fixture 501` · `Clear` · `Fixture 27` · `Clear` — 승인된 그 넷뿐)
원문 로그: `.moai/reports/t248/evidence-raw.txt`

## 0. 🔴 첫 줄 — t246 반증

`Fixture 501` 을 쏘자 `Selection` 의 **`COUNTTOTALSELECTED` 가 0 → 1** 로 움직였다
(`COUNTFULLYSELECTED` 도 0 → 1). `Clear` 로 1 → 0 으로 돌아왔다.

**t246 이 「이 채널은 프로그래머 점유를 비추지 못한다」로 내린 판정은 틀렸다.**
채널은 처음부터 비추고 있었다. t246 이 본 `childCount` 가 **틀린 필드**였을 뿐이다.
`childCount` 는 이 회차에서도 선택 전후로 0 그대로다.

그리고 t242 verdict §7 의 「`SelectionCount()` **새 동사**가 유일한 경로다」도
틀렸다 — 그 정보는 새 동사 없이 **지금 `prop` 으로 읽힌다**.

두 판정서가 같은 사실 하나에 걸려 있다. 정정은 §8 에 적는다.

## 1. 무엇이 갈렸나 — 세 축이 한 회차에 닫혔다

| 물음 | 답 | 근거 |
|---|---|---|
| 이 채널이 프로그래머 점유를 비추는가 | **비춘다** | `COUNTTOTALSELECTED` 0→1→0 |
| `Fixture <n>` 은 FID 를 겨누는가 슬롯을 겨누는가 | **FID** | `Fixture 27`(FID 부재·슬롯 실재) → `Illegal object` 거절 |
| 콘솔이 픽스처 피연산자를 검증하는가 | **한다** | 〃 |

셋째가 덤으로 붙었고, 그게 첫째를 떠받친다 — 피연산자가 검증되므로
`Fixture 501` 의 `exec: ok` 는 **이번에는** 빈 신호가 아니다(§6).

## 2. 절차와 회신 원문

### (0) 음성 대조군 + 버전
```
--expect-version 1.6.3 --path ZZZNOTREALROOT9
  [PASS] ping: ok
  [FAIL] state: responder error: path segment not found: 'ZZZNOTREALROOT9'
```

### (1) 사전 판독 — 쓰기 전
```
[Selection]        NAME='Selection'   (양성 대조군 ok)
    COUNT=0 · COUNTTOTALSELECTED=0 · COUNTFULLYSELECTED=0 · ACTIVE=false
    state: childCount 0
[ProgrammerPart]   NAME='Part Zero'   (양성 대조군 ok)
    COUNT=0 · (나머지 셋은 이 노드에 없다)
    state: childCount 0
```

### (2) 🔴 쓰기 1/4 — `Fixture 501`
```
  [PASS] exec: ok
```

### (3) 되읽기 — **판별자**
```
[Selection]
    COUNT                = 0        ← 안 움직임
    COUNTTOTALSELECTED   = 1        ← 🔴 움직였다
    COUNTFULLYSELECTED   = 1        ← 🔴 움직였다
    ACTIVE               = false    ← 안 움직임
    state: childCount 0             ← 안 움직임 (t246 이 본 필드)
[ProgrammerPart]  COUNT = 0 · childCount 0     ← 안 움직임
```

### (4) 🔴 쓰기 2/4 — `Clear`
```
  [PASS] exec: ok
```

### (5) 되읽기
```
[Selection]  COUNTTOTALSELECTED = 0 · COUNTFULLYSELECTED = 0     ← 1 → 0 복귀
```

### (6) 🔴 쓰기 3/4 — `Fixture 27`
```
  [FAIL] exec: responder error: Illegal object
```

### (7) 되읽기
```
[Selection]  넷 전부 (1) 과 동일 — 아무 일도 안 났다
```

### (8) 🔴 쓰기 4/4 — `Clear`
```
  [PASS] exec: ok
```

### (9) 최종 + (10) 계기 생존
```
[Selection]  넷 전부 (1) 과 동일 · [ProgrammerPart] 동일
ZZZNOTREALROOT9  -> path segment not found     ← 계기, 끝까지 생존
ping             -> 1.6.3
```

## 3. `Fixture 27` 은 표의 어느 행도 아니었다

t246 §5.1 은 결과를 「움직인다 / 안 움직인다」 둘로 세웠고, 「안 움직인다」가
두 뜻을 겸해 아무것도 확정 못 한다고 적었다. **실제로 온 것은 셋째 결과다 —
회신 자체가 `Illegal object` 였다.**

그래서 애매함이 없다. 콘솔이 그 피연산자를 **거절했다**는 것은
`Fixture <n>` 이 **검증되는 이름공간**을 겨눈다는 뜻이고, FID 27 은 부재·슬롯 27 은
실재이므로 그 이름공간은 **FID** 다.

🔴 **판정표를 세울 때 「회신이 거절일 수 있다」를 후보에 안 넣은 것이 내 설계
결함이다.** 되읽기 결과만 두 갈래로 세우고 **실행 자체가 거부되는 갈래**를
빠뜨렸다. t215 가 이미 세 축 중 둘에서 거절을 관측했는데도 내 표에는 그 형태가
없었다.

## 4. FID 는 읽힌다 — 추론 둘이 관측이 됐다

t246 §5.1 이 「추론」으로 표시한 두 줄을 이 회차가 닫았다. **쓰기 0으로.**

```
introspect Patch/Stages/1/Fixtures/27  ->  FID 속성 실재 (CID·IDTYPE·GUID 등과 함께)
prop FID      -> "501"          (number)
prop NAME     -> "MOVER-U 501"
prop IDTYPE   -> "Fixture"
86 슬롯 전수 FID 판독: 86/86 숫자 · 최소 101 · 최대 622 · FID 27 부재
```

| t246 §5.1 이 「추론」으로 적은 것 | 이 회차 |
|---|---|
| 「`MOVER-U 501` 의 FID 가 501」 (이름 끝자리) | **관측** — `prop FID = "501"` |
| 「FID 27 이 없다」 (정본 문면) | **관측** — 86 전수 최소 FID 101 |

## 5. 🔴 계기 함정 — 망가진 계기가 정답과 같은 문자열을 냈다

FID 전수 판독 **1회차에서 파서가 응답 키를 `fields` 로 읽었다.** 실제 키는
`reads` 다. 86개 전부 `?` 로 나왔는데, 프로그램은 이렇게 출력했다:

```
read      : 86
numeric   : 0
FID 27    : ABSENT        <- 🔴 고친 뒤의 정답과 글자가 같다
```

**그대로 믿었으면 우연히 맞았을 것이고, 그건 증거가 아니었다.** 「없는 것」과
「못 읽은 것」이 같은 문자열로 나온다.

이 저장소에 「계기가 무엇을 세는지 먼저 물어라」가 이미 있지만, **틀린 계기가
우연히 맞는 답을 내는 형태**는 이번이 처음 기록이다. 그 경우 계기 결함은
**결과가 틀려서 들키지 않는다** — 결과가 맞아서 안 들킨다.

### 대응 — 양성 대조군을 계기에 박았다

이 회차의 판독 계기는 매 스냅샷마다 **반드시 값이 있는 필드**(`NAME`)를 같이
읽고, 비면 판독 전체를 `INSTRUMENT-FAIL` 로 세운다. 위 로그의 모든 스냅샷에
`양성대조군 NAME='Selection' -> ok` 가 붙어 있는 이유다.

**계기가 죽어서 0 을 답하는 것과, 살아서 0 을 답하는 것은 다른 사건이다.**
양성 대조군이 없으면 그 둘이 같은 출력으로 나온다.

## 6. `exec: ok` 에 대해 — t246 의 경계는 여전히 옳다

t246 §5 는 `exec: ok` 가 실행의 증거가 아니라고 적었다(`classify_result` 가
`result == nil` 에 `true` 를 답한다). **그 문장은 지금도 옳다.**

다만 이 회차는 그것에 의존하지 않았다 — 판정은 전부 되읽기로 내렸고,
`Fixture 27` 에서는 `exec` 가 **`ok` 가 아니라 `Illegal object`** 를 답해
그 자체가 신호였다.

부수적으로 **피연산자 축이 검증된다**는 것이 밝혀졌으므로, `Fixture <n>` 계열에
한해 `exec: ok` 는 이전보다 강한 신호다. 🔴 그러나 이것을 **다른 명령 계열로
일반화하지 마라** — t215 C2 가 꼬리 키워드 축에서 `ok` + 무효과를 관측했다.

## 7. 안 잰 것

| 미측정 | 왜 |
|---|---|
| `COUNT` 와 `ACTIVE` 가 무엇을 세는가 | 선택에는 안 움직였다. **무엇에는 움직이는지 모른다** — 「이 필드는 죽었다」로 읽지 마라 |
| `COUNTTOTALSELECTED` 와 `COUNTFULLYSELECTED` 의 차이 | 이 회차에서는 둘 다 1 이었다. 부분 선택에서 갈릴 것으로 보이나 안 쟀다 |
| 여러 픽스처 선택 시 정확히 세는가 | 1개만 쐈다. `Fixture 501 + 502` 류는 승인 밖 |
| `ProgrammerPart` 가 값 적재를 비추는가 | 값을 한 번도 안 실었다(설계상). `COUNT` 는 선택에 안 움직였다 |
| t246 의 `Fixture 501` 이 그때도 선택했는가 | 그때 `COUNTTOTALSELECTED` 를 안 읽었다. **소급 판독은 불가능하다** |

## 8. 🔴 정정이 필요한 머지된 판정서 둘 — 한 번에 고쳐야 한다

| 문서 | 틀린 문장 | 정정 |
|---|---|---|
| `t246/verdict.md` §0·§6 | 「이 채널은 프로그래머 점유의 판별자가 되지 못한다 — 갈래 B」 | **반증.** 채널은 비춘다. 틀린 필드(`childCount`)를 봤다 |
| `t242/verdict.md` §7 갈래 B | 「`SelectionCount()` **새 동사**가 유일한 경로다」 | **틀렸다.** 새 동사 없이 `prop COUNTTOTALSELECTED` 로 읽힌다 |

두 문서가 **같은 사실 하나**에 걸려 있다. 따로 고치면 두 번 낡는다 —
**한 커밋으로 정정하는 것을 권한다.** 이 카드는 그 정정을 하지 않는다(범위 밖).

## 9. 이 카드가 안 한 것

- 콘솔 쓰기는 `Fixture 501` · `Clear` · `Fixture 27` · `Clear` **넷뿐**이다.
  값은 한 번도 안 실었다 — `Attribute … At …` 류 0건
- 머지 안 했다 — 리드가 확인하고 한다
- t246·t242 정정을 이 브랜치에서 하지 않았다 (§8 은 권고이지 실행이 아니다)
