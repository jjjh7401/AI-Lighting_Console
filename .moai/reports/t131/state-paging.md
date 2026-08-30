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
