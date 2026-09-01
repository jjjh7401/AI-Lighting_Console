# t230 — 콘솔의 18큐는 무엇을 담고 있는가

**판정: (B) 가 반증됐다 — 18큐는 빈 채로 무대에 서지 않는다.**
그러나 카드의 (A)「프리셋 참조를 들고 있다」는 **확인되지 않았다.** 그리고
지금 증거와 똑같이 양립하는 **셋째 갈래 (C)** 가 있다 — 카드에도 배차서에도
이름이 없던 갈래다.

> 🔴 **이 문서에는 이 카드 범위 밖의 경고가 하나 있다** — 「§4.2 자식 목록이
> 조용히 잘린다」. 이 채널로 잰 **모든 과거 목록**이 의심 대상이다. 카드
> 제목만 보고 지나치지 마라.

- 트리: `.claude/worktrees/t230` · 브랜치 `WT-cue-content-read`
- base: `origin/main` = `24f11e5` (착수 시점 재확인)
- 측정: 2026-09-01, 응답기 live version=1.6.2 plugin=CopilotResponder
- **콘솔 쓰기 0건.** `query_state` 와 `query_properties` 만 썼다.
  시퀀스 2·3 은 읽기만 했고 `Patch/Stages` 경로는 밟지 않았다.

---

## 1. 주장 (Claim)

### 1.1 두 축, 그리고 그것을 합치지 않기

| 축 | 판정 | 근거 |
|---|---|---|
| 18큐가 **비어 있나** | 🟢 **아니다 — 18/18 이 데이터를 들고 있다** | `OWNDATAPRESENT true` + `MEMORYFOOTPRINT` 3048–9136 |
| 그 데이터가 **프리셋 참조인가** | 🔴 **이 채널로는 못 잰다** | 후보 필드 둘이 **채워진 큐에서도** 빈값 |

`OWNDATAPRESENT` 가 답하는 것은 **「비어 있지 않다」뿐이다.** 「우리가 넣으려던
그것이 들어 있다」가 아니다. 두 문장은 다르고, 이 채널은 앞것만 답한다.

### 1.2 갈래는 둘이 아니라 셋이다

카드는 (A)/(B) 둘로 물었다. 지금 증거로 (B) 는 죽지만, **살아남는 갈래가
하나가 아니라 둘**이다:

| 갈래 | 상태 | 다음 작업이 어떻게 갈리나 |
|---|---|---|
| **(A)** 18큐가 **프리셋 참조**를 들고 있다 | ⬜ **미확인** | 우리는 이미 채워진 자리를 채우려 하고 있었다 — 프리셋 재작업은 **불필요**하고, 재발사는 같은 참조를 덮는 무해한 반복이다 |
| **(B)** 그 자리가 **비어 있다** | 🟢 **반증됨** | (해당 없음) 18큐가 반쪽인 채 무대에 서는 시나리오는 사라졌다 |
| **(C)** 큐가 **생값**을 들고 있고 참조는 없다 | ⬜ **미확인 · 증거와 완전히 양립** | 프리셋 작업은 지금 무대에 선 것을 **안 바꾼다.** 그리고 재발사하면 **생값을 덮어쓴다** — 되돌릴 수단이 없다 |

🔴 **(C) 가 이 카드의 진짜 산출물이다.** 카드에도 배차서에도 이름이 없었고,
지금 증거는 (A) 와 (C) 를 **전혀 가르지 않는다** — `OWNDATAPRESENT` 는 둘 다
`true` 를 답한다. (A) 로 단정하면 §2.3 에서 「못 쟀다」고 적은 바로 그 축을
결론에서 쓰는 것이 된다.

**함의의 무게가 다르다**: (A) 면 다음 작업은 낭비에 그치지만, (C) 면 다음
발사가 **무대에 선 값을 파괴한다.** 그래서 이 갈래를 가르기 전에 큐에 쓰지
않는 것이 안전한 기본값이다.

---

## 2. 증거 (Evidence)

### 2.1 계기가 실제로 갈라지는가 — 대조군이 같은 측정 안에 있다

`OWNDATAPRESENT` 는 68개 파트 중 **48 true / 20 false** 로 갈린다. 그리고 빈
쪽의 `MEMORYFOOTPRINT` 가 한 값으로 모인다:

    OffCue / CueZero / Cue 1   OWNDATAPRESENT false   mem 2521   ← 빈 파트 기준선
    T215 ALT                   OWNDATAPRESENT false   mem 2544   ← 기준선 근처
    내용 있는 파트             OWNDATAPRESENT true    mem 3048–9136

즉 **음성 대조군(2521)과 양성 대조군(3000+)이 같은 표에 함께 있다.** 이
계기가 「전부 true」나 「전부 false」를 답하는 계기가 아니라는 것이 그 표
자체로 증명된다.

### 2.2 정본 시퀀스 3 — 18/18 이 데이터를 들고 있다

`DataPool/Sequences/3` = `Sugar r3`, childCount **21** = 시스템 3 + 우리 18.

    cueNo  10  true  4580     cueNo 100  true  3064
    cueNo  20  true  3368     cueNo 110  true  4160
    cueNo  30  true  3896     cueNo 120  true  3048
    cueNo  40  true  4504     cueNo 130  true  5744
    cueNo  50  true  6208     cueNo 140  true  3768
    cueNo  60  true  5432     cueNo 150  true  5748
    cueNo  70  true  7728     cueNo 160  true  6600
    cueNo  80  true  3896     cueNo 170  true  9136
    cueNo  90  true  5872     cueNo 180  true  6312

    시스템 3개(OffCue·CueZero·Cue 1) : false / 2521

**18개 전부 true 이고 전부 기준선을 크게 넘는다.** 빈 큐는 하나도 없다.

부수 관측: 시퀀스 2 `Sugar` 도 같은 18큐가 전부 true 이고 footprint 가 거의
같다(Q160 만 6568 vs 6600 — 이름 길이 차로 설명된다). 두 시퀀스가 같은 내용을
들고 있다는 것과 정합적이다. **동일성은 안 쟀다.**

### 2.3 프리셋 참조 축 — 후보 필드가 아무것도 안 가른다

`Part` 클래스는 필드 **195개**를 연다. 그중 참조를 담을 만한 이름 셋을 읽었다:

| 필드 | 68개 파트에서 | 판정 |
|---|---|---|
| `PRESETDATA` | 전부 `""` (읽기 성공) | 채워진 48개에서도 빈값 — **안 가른다** |
| `REFERENCES` | 전부 `""` (읽기 성공) | 같음 — **안 가른다** |
| `STOREDDATA` | 전부 `property not readable` | 이 채널로 안 열린다 |

**핵심**: 이 셋은 `OWNDATAPRESENT true` 인 48개 파트에서도 똑같이 비어 있다.
데이터가 **있는 것이 확실한** 자리에서 빈값을 답하므로, 이 필드들의 빈값은
「참조가 없다」의 증거가 **아니다.** 계기가 그 축을 안 재는 것이다.

`Cue` 클래스도 확인했다 — 필드 **23개**뿐이고 참조를 담을 이름이 없다
(`DEPENDENCYEXPORT`·`MIBPREFERENCE` 둘 다 무관).

### 2.4 날조 대조군 — 빈값이 진짜 빈값인지

카드 함정 1(「없는 꼬리 키워드는 `ok` 를 준다」)을 그대로 쐈다:

    PRESETDATA     ok=True   ''
    ZORBLEDATA     ok=False  property not readable: ZORBLEDATA
    REFERENCES     ok=True   ''
    QQQNOTAFIELD   ok=False  property not readable: QQQNOTAFIELD

날조 이름은 **거절된다.** 그러므로 `PRESETDATA`·`REFERENCES` 는 실재하는
필드이고 그 빈값은 응답기가 실제로 답한 값이다 — 「아무거나 물어도 빈값이
온다」가 아니다. **빈값은 진짜지만, 채워진 큐에서도 비어 있으니 그 축의
증거가 못 된다**(2.3).

경로 부재 대조군도 함께 쐈다:

    DataPool/Zorble          -> state failed: path segment not found: 'Zorble'
    DataPool/Sequences/999   -> state failed: path segment not found: '999'

부재는 **명시적 오류**로 온다. 그래서 성공 응답의 빈 목록은 부재와 구별된다.

---

## 3. 기준 귀속 (Baseline-attribution)

전부 이 트리·이 회차에서 직접 실행했다.

| 주장 | 명령 | 결과 |
|---|---|---|
| 응답기 생존 | `responder_roundtrip.py --listen-port 9005 --skip-exec --wait 5` | `result: PASS`, 1.6.2, Sequences childCount 6 |
| 시퀀스 전수 | `t230_cue_content_survey.py` | 6 시퀀스 · 65 큐 · 68 파트 |
| 필드 목록 | `introspect_probe.py --path DataPool/Sequences/3/4/1 --all-pages` | Part 195 필드 |
| Cue 필드 | `introspect_probe.py --path DataPool/Sequences/3/4 --all-pages` | Cue 23 필드 |
| 날조 대조군 | `introspect_probe.py --names PRESETDATA,ZORBLEDATA,REFERENCES,QQQNOTAFIELD` | 위 2.4 |

증거 원본: `.moai/reports/t230/probes/` (`survey.json` · `survey2.json` ·
`part_introspect.json` · `cue_introspect.json`).
프로브: `server/tools/t230_cue_content_survey.py` (읽기 전용).

`uv sync --group dev` 를 진입 직후 돌렸다. 주 체크아웃 venv 를 빌리지 않았다.

---

## 4. 계기 함정 셋 — 다음 사람이 밟는다

### 🔴 4.1 응답기는 **9005 포트로만** 답한다

    --listen-port 9007  ->  ping timeout, state timeout, result: FAIL
    --listen-port 9005  ->  result: PASS (같은 순간, 같은 콘솔)

포트를 바꾼 쪽이 받는 것은 부분 실패가 아니라 **전면 침묵**이다. 그것을
「콘솔이 죽었다」로 읽으면 살아 있는 콘솔을 죽었다고 보고하게 된다. 이 회차에
내가 첫 조회에서 그럴 뻔했다 — 리드가 쓴 포트로 다시 쏴서 갈렸다.

**따름**: 레인이 여럿이면 이 포트는 **공유 자원 하나**다. 겹치면 서로의 응답을
가져간다. 조회 창은 겹치지 않게 잡아야 한다.

**후속(같은 PR, CI 가 잡았다)**: 이 조사 도구가 포트를 `receive_port=9005` 로
**박아 두고** 있었다. t61 이 세운 가드
(`test_probe_port_discipline.py::test_they_all_use_the_single_shared_declaration`)가
CI 에서 정확히 그것을 잡았다 — 「공용 선언을 **부르지** 않는 도구」. 위 사고를
겪고 문서에 적은 그 회차에, 같은 사고의 원인을 도구에 그대로 남겨 둔 것이다.
고쳤다: `add_listen_port_argument(parser)` 로 포트를 **인자**로 받고
(`--listen-port` 는 기본값 없는 필수), `preflight` 로 침묵에 이름을 붙인다.
재측정 — 고치기 전 이 검사는 `1 failed`, 고친 뒤 `7 passed`. 실기 스모크에서
`preflight.verdict = responder_ok`, 시퀀스 6개 전부 `childCount == listed`.

### 🔴 4.2 `query_state` 의 자식 목록은 잘린다 — 그리고 조용하다

> **이 항목은 이 카드 범위 밖이다.** 전파용 전문은 아래 § 독립 경고 에 있다.

    childCount 21 인 시퀀스가 한 번에 13개(seq 3) / 17개(seq 2)만 답했다.

`truncated: true` 가 오는데, 그것을 안 보면 **큐 8개가 조용히 사라진다.**
같은 childCount 21 이 시퀀스마다 다른 수로 잘린 이유는 이름 바이트다 — seq 3 은
한글 이름이라 더 일찍 잘린다. **이 회차의 1차 훑기가 실제로 이 함정을 밟았고,
보고 직전에 `childCount` 와 목록 길이를 대조해서 잡았다.**

처방: `offset` 으로 소진할 때까지 페이징하고, **받은 개수만큼** 전진한다
(고정 보폭은 이름을 건너뛴다). 페이징 후 6/6 시퀀스가 `childCount == 목록 길이`.

### 4.3 `childCount 0` 은 부재가 아니다 (카드 함정 2 — 재확인)

`Part` 는 `childCount 0` 인데 필드 195개를 열고 `OWNDATAPRESENT true` 를
답한다. 자식이 없다는 것과 내용이 없다는 것은 다른 말이다.

---

## 🔴 독립 경고 — 이 채널로 잰 **모든 목록**이 의심 대상이다

> 이 절은 t230 의 결론과 **무관하게** 읽어라. 카드 제목만 보고 지나치면
> 다음 사람이 같은 값을 다시 틀리게 센다.

### 무엇이 관측됐나

`query_state` 는 자식 목록을 **응답기 payload 예산에서 자르고**, 잘렸다는
사실을 목록 안에서는 알려주지 않는다. 실측(2026-09-01, 응답기 1.6.2):

    DataPool/Sequences/3   childCount 21  ->  한 번에 13개만 반환
    DataPool/Sequences/2   childCount 21  ->  한 번에 17개만 반환

같은 `childCount 21` 이 시퀀스마다 **다른 수로** 잘린다. 이름이 한글이면
1자 3바이트라 예산을 더 빨리 먹기 때문이다 — seq 3 은 큐 이름이 한글이라
seq 2 보다 4개 일찍 잘렸다.

### 왜 조용한가

`truncated: true` 는 응답에 실려 온다. 그러나 **소비자가 그 플래그를 안 보면**
잘린 목록이 완전한 목록과 바이트 수준에서 구별되지 않는다. 개수를 세는 쪽은
`childCount` 를 보고 「21개」라 적고, 목록을 쓰는 쪽은 13개만 쓴다 — 두 수가
같은 보고서 안에 있어도 아무도 대조하지 않으면 안 걸린다.

**이 회차의 1차 훑기가 실제로 이 함정을 밟았다.** 보고 직전에
`childCount == len(children)` 을 대조해서 잡았고, 안 잡았으면 큐 8개가 사라진
채로 「전수했다」고 적을 뻔했다.

### 무엇이 의심 대상인가

**이 채널(`query_state`)로 자식 목록을 읽은 모든 과거 측정.** 특히:

- 목록 길이를 그대로 「전부」로 적은 보고
- 같은 풀을 다른 시점에 세어 **드리프트**를 주장한 보고 — 두 측정의 이름
  바이트가 다르면 잘린 위치도 달라져, **없는 드리프트가 생긴다**
- `childCount` 만 적고 목록은 안 실은 보고 — 대조할 방법이 사라진다

### 처방

1. `offset` 으로 소진할 때까지 페이징한다.
2. **받은 개수만큼** 전진한다. 고정 보폭은 이름을 건너뛴다.
3. 매번 `childCount == len(children)` 를 **단언**한다. 어긋나면 그 수를 쓰지 마라.
4. `truncated` 가 참인데 창이 비어 오면 멈추고 사유를 남긴다(무한 루프 방지).

구현 참조: `server/tools/t230_cue_content_survey.py` 의 `read_children`.
페이징 후 6/6 시퀀스가 `childCount == 목록 길이` 를 만족했다.

---

## 5. 미검증 (Gaps)

- **프리셋 참조 여부를 안 쟀다** — 못 쟀다. 2.3 이 그 이유다.
- **생값인지 참조인지도 안 갈랐다.** `OWNDATAPRESENT` 는 「자기 데이터가 있다」
  까지만 말하고 그 데이터의 **종류**를 말하지 않는다.
- **18큐의 내용이 시트와 일치하는지 안 쟀다.** footprint 가 큐마다 다른 것은
  내용이 다르다는 뜻이지, **맞다**는 뜻이 아니다.
- **시퀀스 2 와 3 의 동일성을 안 쟀다.** footprint 가 거의 같다는 것까지다.
- **응답기 verb 전수를 안 훑었다.** `state`·`props`·`introspect` 셋만 썼다.
  다른 verb 로 큐 내용이 열릴 가능성은 배제하지 못했다.
- **한 콘솔 · 한 쇼파일 · 이 회차 한 번.**

---

## 6. 잔여 위험 (Residual-risk)

- `MEMORYFOOTPRINT` 를 「내용 크기」로 읽는 것은 **대리 지표**다. 2521 이 빈
  파트라는 것은 시스템 큐 5개가 전부 그 값이라는 관측에서 왔지, 문서에서
  온 것이 아니다.
- `OWNDATAPRESENT` 의 의미를 콘솔 문서로 확인하지 않았다. 이름과 관측된
  갈라짐이 근거의 전부다.
- 이 측정 동안 다른 레인이 같은 콘솔에 쓰기를 했다면 값이 움직였을 수 있다.
  겹치지 않게 잡았지만 **잠금은 없다.**

---

## 7. 감독께 — GUI 에서 무엇을 보면 되나 (한 줄이 안 되어 셋)

프리셋 참조 축은 이 채널로 못 여니 GUI 확인이 유일한 길이다. 이것이 §1.2 의
**(A) 와 (C) 를 가르는 유일한 수단**이고, 갈리기 전에는 큐에 쓰지 않는 것이
안전한 기본값이다 — (C) 면 재발사가 무대에 선 생값을 덮는다.

1. **Sequence 3 `Sugar r3` 의 시트를 연다** (Sequence Sheet). 큐 18개가
   Q010~Q180 로 보인다 — 그 목록 자체는 이미 확인했다.
2. **한 큐를 열어 값 칸을 본다.** 셀에 `COL.01` 같은 **프리셋 이름**이 보이면
   참조로 들어간 것이고, 숫자만 보이면 생값으로 들어간 것이다. 이 갈래가
   카드의 (A)/(B) 를 실제로 가른다.
3. 참조라면 **어느 프리셋 풀을 가리키는지**까지 봐 주시면, 다음 회차가
   「이미 채워진 자리」를 다시 채우지 않게 된다.

확인 결과만 알려주시면 이 verdict 에 붙이겠습니다. **콘솔은 안 건드렸습니다.**

---

## 계보

- t209 — 이 18큐를 넣은 회차.
- t227 — 멱등층을 비켜 재려고 없는 시퀀스 이름을 쓴 회차.
- AC-LXSEQ4-013 — 되읽기 채널이 번호·이름까지라는 한계 문서화. **이 회차가
  그 한계를 한 칸 넓혔다**: 내용의 **유무**는 열린다. 종류는 여전히 안 열린다.
- `lesson-ask-what-the-instrument-counts` — 4.1·4.2 가 이 계열이다.
- `lesson-one-control-bounds-the-conclusion` — 2.1 의 대조군이 같은 표 안에
  있는 것이 이 회차의 뼈대다.
