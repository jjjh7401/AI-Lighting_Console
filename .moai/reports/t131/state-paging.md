# t131 첫 발 — 실기 `state offset=N` 은 산다. 다만 회귀 대상이 사라졌다

트리 `.claude/worktrees/t131` · 브랜치 `WT-state-paging` · base `5498415` (착수 시점 재확인)
콘솔 `app_gma3` **pid 38706** (아침과 동일 — 재기동 없음) · **읽기 전용, 콘솔 쓰기 0줄**

## 1. 주장

1. **실기 1.6.2 는 `state` 페이징을 존중한다.** 소스 근거였던 것이 실측으로 승격됐다.
2. **`childCount` 는 오프셋에 따라 변하지 않는다** — 계기 함정 가설을 반증했다.
3. 🔴 **카드가 지정한 회귀 대상(20개짜리 딤 풀)이 없어졌다.** 로드된 쇼가 또 바뀌었고,
   지금 딤 풀은 7건 · `truncated: false` 다.
4. 🔴 **바뀐 쪽이 오히려 프로젝트의 실제 작업 쇼다** — `Groups` 18 이 08-26 survey 의
   기준선(t66 이 올린 18)과 일치한다.

## 2. 증거

### 2.0 계기 신뢰성

    responder_roundtrip --skip-exec --expect-version 1.6.2
    -> [PASS] ping: ok · live version=1.6.2 plugin=CopilotResponder

    t95_state_dump --path 'DataPool/ZZZNoSuchPoolXYZ' --offset 5      (날조 대조군)
    -> state failed: path segment not found: 'ZZZNoSuchPoolXYZ' (in DataPool/ZZZNoSuchPoolXYZ)  [exit 1]

대조군 문면에 **오프셋 토큰이 경로에 안 붙어 있다** — 파싱됐다는 첫 신호다.
1.6.1 이었다면 `'ZZZNoSuchPoolXYZ offset=5'` 로 답했다.

### 2.1 첫 발 — 페이징 실측

    t95_state_dump --path 'DataPool/PresetPools/1' --offset 19
    -> "offset": 19 · "ok": true · "path": "DataPool/PresetPools/1" · "children": []

**`offset: 19` 이 그대로 에코됐다.** `console.py:669` 독스트링이 정한 판정 기준
(페이징 응답기는 offset 을 되돌려 준다 · 에코가 없으면 진전 없음)을 통과한다.
`state` 페이징이 1.6.0부터 있다는 lua 주석(`copilot_responder.lua:230`)이
**소스 근거에서 실측으로 승격**됐다.

### 2.2 `childCount` 는 오프셋 상대값이 아니다 (가설 반증)

offset 19 가 `childCount: 7` 을 답해서 이 값이 창 기준 상대값인지 의심했다.
같은 경로를 offset 0 으로 다시 쐈다:

    offset 19 -> childCount 7 · children 0 · truncated false
    offset 0  -> childCount 7 · children 7 · truncated false

두 오프셋에서 **같다.** 상대값 가설은 반증됐다 — 풀이 실제로 7건인 것이다.

### 2.3 쇼가 또 바뀌었다. 이번엔 우리 쇼다

| 경로 | 08-26 survey | 08-30 아침 (t96) | 08-30 지금 |
|---|---|---|---|
| `DataPool/PresetPools/1` | 6 | **20** (`Dim 10`…`Breathe Soft`) | **7** (`풀`·`쇼 하이 OLD`·`미드`·`로우`·`잔광`·`아웃`·`쇼 하이`) |
| `DataPool/Groups` | **18** (t66) | 5 (`All Fixtures`…) | **18** (`ALL`·`KEY`·`FOH`·`BACK`·`SIDE-L`·`SIDE-R`·`SIDE-ALL`·`WASH-*`·`MOVER-*`) |

아침 쇼는 영문 이름의 낯선 쇼였다. 지금은 **한글 프리셋 + 우리 그룹 18개** —
08-26 기준선과 일치한다. 프로젝트의 실제 작업 쇼가 로드된 상태다.

## 3. 카드에 대한 영향

- **첫 발은 성공했고 그 값은 남는다.** 페이징 실측은 쇼와 무관하다.
- 🔴 **배차서의 회귀 대상은 없어졌다.** 「지금 쇼의 20개짜리 딤 풀」로 절단이 풀리는지
  보려 했으나, 지금 딤 풀은 7건이라 24 캡 아래이고 `truncated: false` 다.
  **절단 자체가 재현되지 않는다.**
- 결함(호출부에 페이징 루프 없음, `tools.py:4870`)은 **여전히 실재한다** — 쇼와 무관한
  코드 결함이다. 다만 **실기 회귀 검증을 이 쇼에서는 못 한다.**

## 4. 안 잰 것

| 축 | 왜 |
|---|---|
| 지금 쇼에서 절단되는 풀이 있는가 | 안 훑었다. `Patch/Stages/1/Fixtures` 가 후보지만 확인 안 함 |
| 쇼를 언제·누가 바꿨나 | 관측은 풀 내용 차이뿐. 감독의 붙여넣기 작업 중일 가능성이 있으나 미확인 |
| 이 쇼가 08-26 의 그 쇼 자체인지 | Groups 18 일치는 강한 신호지만 동일성 증명은 아니다. 딤은 6→7 로 하나 늘었다 |
| 오프셋 경계 동작 | 캡을 넘는 풀에서 창이 실제로 이어지는지는 절단되는 풀이 있어야 잰다 |
| `--offset` 플래그의 테스트 | 아직 안 썼다. 구현 단계 몫 |

## 5. 잔여 위험

- 🔴 **지금 로드된 쇼는 실제 작업 쇼로 보인다.** 이 쇼에 대한 쓰기는 아침의 낯선
  쇼에 쓰는 것과 위험도가 다르다. 쓰기 창은 감독 승인 없이는 안 된다.
- 쇼가 오늘만 세 상태를 거쳤다(6 → 20 → 7). **어떤 카드든 풀 내용을 전제로 삼으면
  그 전제는 시간 단위로 노화한다.** 착수 시점에 다시 재는 것이 규약이 돼야 한다.
- 이 회차 콘솔 쓰기 0줄. 되돌릴 것이 없다.

---

## 6. 추가 (같은 회차) — 회귀 대상을 찾았고, 페이징이 끝까지 걷는다

3절에서 「회귀 대상이 없어졌다」로 닫았는데, 같은 쇼 안에서 다른 절단 사례를 찾았다.
읽기라 리드 승인 범위 안이다.

    t95_state_dump --path 'Patch/Stages/1/Fixtures'
    -> childCount 86 · children 19 · truncated true

    t95_state_dump --path 'Patch/Stages/1/Fixtures' --offset 19
    -> childCount 86 · children 18 · truncated true · "offset": 19
       첫 이름 BLIND 606 · STROBE 611 · STROBE 612   (1창과 다른 내용)

**세 가지가 한꺼번에 확인된다:**

1. **창이 실제로 전진한다** — 2창의 내용이 1창과 다르다. 에코만 오는 것이 아니라
   페이로드가 이어진다.
2. **`childCount` 는 절대 총계다** — 두 창 모두 86. 2.2 절의 반증(오프셋 상대값 아님)이
   절단되는 풀에서도 성립한다. 스키마의 「`node.childCount` 는 true total」이 맞다.
3. **`truncated` 는 창 기준이다** — 2창에서도 true 다. 즉 「더 남았다」는 뜻이지
   「이 풀이 절단됐다」는 고정 속성이 아니다. 종료 판정은 `truncated` 가 false 가
   되거나 창이 비는 지점이다.

### 3절 정정

「회귀 대상이 사라졌다」는 **딤 풀에 한정해서만** 맞다. 실기 회귀 검증은
`Patch/Stages/1/Fixtures`(86건)로 가능하다. 앞의 (B)·(C) 갈래는 불필요하다 —
콘솔 쓰기 없이 (A) 로 닫힌다.

### 여전히 안 잰 것

- **끝까지 페이징했을 때 86건이 다 모이는가.** 2창까지만 봤다(19+18=37).
  전수 순회는 구현 단계에서 루프와 함께 잰다.
- 창 크기가 왜 19/18 로 다른가. 페이로드 예산이라 내용에 따라 변하는 것으로
  보이지만 **안 쟀다.** 「N개씩 온다」로 못박는 검사를 만들면 안 된다.

---

## 7. 정정 — 절단 축이 둘이고, 회귀 단언을 잘못 잡을 뻔했다

리드가 6절을 읽고 두 가지를 지적했다. 둘 다 받는다.

### 7.1 절단은 개수 캡 **또는** 페이로드 예산으로 난다

6절 말미에 「창 크기가 19/18 로 다른 이유는 안 쟀다」고 적었는데, 축이 이미 알려져 있다.

| 축 | 값 | 출처 |
|---|---|---|
| 개수 캡 | `max_children = 24` | `console/lua/copilot_responder.lua:33` — 리드가 정본에서 읽음 |
| 페이로드 예산 | 절단 경계 `[1200, 1208)` 바이트 | **t12 실측이라고 전달된 값 — 내가 안 쟀다** |

전달된 t12 실측 예시: `Root 22→18/1200B` · `Fixtures 86→19/1158B` · `DataPool 16→16/1013B`.

**내가 찾은 `Fixtures 86→19` 는 개수 캡 24 로 설명이 안 된다** — 19 는 24보다 작다.
따라서 바이트 예산 축에 걸린 것이다. 창 크기가 19/18 로 흔들린 것도 같은 이유다:
이름 길이에 따라 한 창에 실리는 개수가 달라진다.

**후보를 「자식 25개 이상」으로만 좁히면 이름이 긴 20개짜리 풀을 놓친다.**
절단 후보를 훑을 때는 `truncated: true` 인 응답의 `childCount` 와 그때 실제로 실린
개수를 **나란히** 적어야 어느 축에 걸렸는지가 그 자리에서 읽힌다.

### 7.2 🔴 회귀 단언은 `truncated: false` 가 아니라 「모은 개수 == childCount」다

내가 6절에서 종료 판정을 「`truncated` 가 false 가 되거나 창이 비는 지점」이라고
적었다. **회귀 검사의 단언으로 쓰면 공허하다** — 첫 페이지만 쓰고 `truncated` 만
지우는 구현도 통과한다. 「안 잘렸다」는 「이어 붙였다」가 아니다.

단언은 **`len(모은 자식) == childCount`** 여야 한다. 이 저장소가 이미 겪은
「검사 자신이 공허할 수 있다」 계열이고, 내가 그 함정에 반 발 들어가 있었다.

구현 단계의 검사 설계는 이 단언을 축으로 잡는다. 그리고 **그 단언 자체를 뮤테이션**한다
(첫 페이지만 반환하도록 루프를 잘라 보고, 검사가 실제로 빨개지는지 확인).

### 7.3 저장소가 이미 갖고 있었다 (아홉 번째)

카드는 「호출부에 페이징 루프를 넣는다」로 컸는데, 실제 구멍은 **CLI 노출 한 곳**이었다.
`query_state` 는 `console.py:669` 에서 이미 `offset` 을 받아 `build_state_query` 에
넘기고 있었고, 독스트링이 판정 기준까지 적어 두었다. 짓기 전에 찾았어야 할 자리다.

남은 진짜 구멍은 하나다 — `server/orchestrator/tools.py:4870` 이 그 매개변수를
**안 쓰는** 것.

---

## 8. 구현 회차 — 루프가 붙었고, 실기에서 끝까지 걷는다

트리 `.claude/worktrees/t131` · 브랜치 `WT-state-paging` · base `215d236`
콘솔 `app_gma3` **pid 38706** (첫 회차와 동일 — 재기동 없음) · **콘솔 쓰기 0줄**

### 8.1 주장

1. **호출부가 이제 끝까지 걷는다.** `import_lxseq_presets` 의 프리셋 풀 판독이
   페이징을 탄다.
2. **실기에서 86건이 전부 모인다** — §6 이 「안 쟀다」고 남긴 축이 닫혔다.
3. **창 크기는 균일하지 않다**: `19 · 18 · 18 · 18 · 13`. 어느 것도 24가 아니다.
   §7.1 의 「바이트 예산 축」이 실증됐다.
4. 🔴 **§7.3 을 정정한다.** 「새 능력 불필요, 구멍 하나」는 맞지만 **짓는 것도
   불필요했다** — 완성된 페이징 루프가 이미 `server/web/presets_api.py:230` 에
   있었다(무진전 방어 · 테스트 포함). 「저장소가 이미 갖고 있다」 **열 번째**다.
5. **결함의 결과는 오발이 아니라 능력 상실이었다.** 첫 창만 읽으면
   `truncated: True` → `server/rig/section.py:91` 이 `section_truncated` 로
   **fail-closed** 한다. 큰 풀에서 임포트가 통째로 거절됐다. 안전한 방향으로
   틀렸지만, 틀린 것은 맞다.

### 8.2 증거 — 실기

계기 신뢰성부터. 날조 대조군이 **거절**한다(계기가 멀지 않았다):

    t131_paged_walk --path 'Patch/Stages/1/ZZZNoSuchNodeXYZ' --listen-port 9005
    -> state failed: path segment not found: 'ZZZNoSuchNodeXYZ' (in Patch/Stages/1/ZZZNoSuchNodeXYZ)

착수 시점 쇼 지문 재측정 (전제는 노화한다 — 오늘만 쇼가 세 번 바뀌었다):

    t95_state_dump --path 'DataPool/Groups'        -> childCount 18 · children 18 · truncated False
    t95_state_dump --path 'DataPool/PresetPools/1' -> childCount 7  · truncated False
       ['풀','쇼 하이 OLD','미드','로우','잔광','아웃','쇼 하이']

첫 회차(08-30 저녁)와 **동일**하다. 같은 쇼다.

본 측정 — 끝까지 걷기:

    t131_paged_walk --path 'Patch/Stages/1/Fixtures' --listen-port 9005
    -> childCount    : 86
       collected     : 86
       truncated     : False
       offsets sent  : [0, 19, 37, 55, 73]
       window sizes  : [19, 18, 18, 18, 13]
       VERDICT       : COMPLETE

대조군 — 안 잘린 작은 풀은 후속 조회를 **안 쏜다**(왕복 낭비 없음):

    t131_paged_walk --path 'DataPool/PresetPools/1' --listen-port 9005
    -> collected 7 / childCount 7 · offsets sent [0] · VERDICT COMPLETE

### 8.3 증거 — 뮤테이션 6/6 전멸

§7.2 가 지정한 대로 **단언 자체를** 쏘았다. 검사는 고친 뒤에 썼으므로, 뮤테이션
없이는 「초록」이 아무 증거도 아니다.

| # | 뮤테이션 | 결과 |
|---|---|---|
| M1 | 🔴 첫 창만 쓰고 `truncated` 만 지운다 (§7.2 가 경고한 공허한 구현) | **KILL** 7건 |
| M2 | 호출부를 페이징 없는 원래 코드로 되돌린다 | **KILL** 3건 |
| M3 | `presets_api` 위임을 옛 사본으로 되살린다 | **KILL** 3건 |
| M4 | 무진전 방어(offset 에코 검사)를 지운다 | **KILL** 1건 |
| M5 | 「한 창에 24개씩 온다」 고정 창을 가정한다 | **KILL** 4건 |
| M6 | 페이지 상한 경계를 한 칸 옮긴다 (`PAGE_CAP + 1`) | **KILL** 1건 |

M1 이 이 표의 이유다. 단언을 `truncated is False` 로 잡았다면 M1 은 **살아남는다**
— 「안 잘렸다」와 「이어 붙였다」는 다른 말이기 때문이다. 단언을
`len(모은 자식) == childCount` 로 잡아서 잡혔다.

복원은 `git checkout` 이 아니라 백업+체크섬으로 했다(미커밋분 보호). 세 파일의
sha256 이 뮤테이션 전후로 동일함을 확인했다.

### 8.4 증거 — 기계 검증

    pytest server/tests -q          -> 10483 passed, 12 skipped  (147s)
    ruff check server               -> All checks passed!
    ruff format --check server      -> 458 files already formatted

기준선(착수 시점)도 초록이었다 — 이 초록이 내 변경 덕이라는 주장은 하지 않는다.
카드가 여는 것은 **거절되던 갈래**이고, 그것은 §8.2·§8.3 이 잰다.

### 8.5 바뀐 것

| 파일 | 무엇 |
|---|---|
| `server/rig/paging.py` | **신규** — 페이징 규율의 유일한 자리. 본문은 `presets_api` 사본을 그대로 옮긴 것 |
| `server/web/presets_api.py` | 사본 삭제 → 위임(이름 유지, 기존 테스트 29건 그대로 바인딩) |
| `server/orchestrator/tools.py` | 🔴 카드의 구멍 — 프리셋 풀 판독이 페이징을 탄다 |
| `server/tests/test_state_paging_callsite.py` | **신규** — 회귀 12건 |
| `server/tools/t131_paged_walk.py` | **신규** — 실기 완전성 프로브(읽기 전용). §8.2 를 다음 사람이 다시 잴 수 있게 |

### 8.6 결함 계열 — 잰 것, 그리고 손대지 않은 것

`query_state` 호출부는 운영 코드에 **40여 곳**이다. 그중 단면을 만들어
`section_refusal` 계열 술어에 넘기는 자리를 추렸다:

| 자리 | 상태 |
|---|---|
| `tools.py` `import_lxseq_presets` 프리셋 풀 | 🟢 이 카드가 고쳤다 |
| `tools.py` fx 경로 프리셋 풀 (`select_preset_number` 앞) | ⬜ **안 건드렸다** — 같은 모양이지만 `test_fx_tool.py:1152` 가 `preset_pool_truncated` 거절을 **비준**하고 있다. 카드 범위 밖이고, 비준된 검사를 흔드는 일이라 별도 판단이 필요하다 |
| `tools.py` 그룹 풀 (`read_group_pool`) | ⬜ 안 쟀다 — 단면 경로가 다르다(`groups_from_snapshot`) |
| `web/session.py` `_paged_pool_children` | 🟡 세 번째 사본이 여기 남아 있다. 강등 방향이 달라(부분→`None`) 단순 위임이 안 된다 |

「점-수정은 결함 계열을 못 말린다」에 따라 표를 만들었다. 표는 **처방이 아니라
측정**이다 — 남은 세 자리는 각각 별도 결정이 필요하다.

### 8.7 안 잰 것

| 축 | 왜 |
|---|---|
| 큰 프리셋 풀에서의 실기 임포트 | 지금 딤 풀이 7건이라 절단이 재현 안 된다. 24건 넘는 풀을 만드는 것은 **콘솔 쓰기**라 리드 승인 밖이다. 페이징 자체는 86건 풀(`Fixtures`)로 실측했다 |
| 페이로드 예산 경계 `[1200,1208)` | 전달받은 t12 값을 그대로 썼다. **내가 안 쟀다** |
| 페이지 상한(11창 · 최대 264슬롯)을 넘는 실기 풀 | 그런 풀이 이 쇼에 없다. 넘으면 `truncated` 로 남아 fail-closed 된다 |
| `session.py` 사본의 동작 | 안 건드렸고 안 쟀다 |

### 8.8 잔여 위험

- **`TypeError` 갈래가 넓다.** 포트 안쪽에서 다른 이유로 난 `TypeError` 도
  「페이징을 모른다」로 읽혀 첫 창만 쓰게 된다. 옮겨 온 기존 동작 그대로 두었다
  — 좁히면 `presets_api` 의 동작이 바뀐다.
- **완전성은 응답기의 `childCount` 를 믿는다.** 그 값이 거짓이면 이 판정도 거짓이다.
  이 쇼에서는 두 오프셋에서 같은 값이 왔다(§2.2·§6).
- 이 회차 **콘솔 쓰기 0줄.** 되돌릴 것이 없다.
