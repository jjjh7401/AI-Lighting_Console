---
id: SPEC-COPILOT-CLASSIFYGAP-001
title: "곡→콘솔 경로가 쓰는 명령 네 개가 분류 층에 안 걸린다 — 봉합 뒤에 받침을 놓는다"
version: "0.1.0"
status: draft
created: 2026-09-07
updated: 2026-09-07
author: manager-spec (plan session, 카드 t299 — t292·t317~t323 후속)
priority: P1
phase: "v1.8.4 target"
module: "server/safety/blacklist.yaml, server/safety/classify.py, server/tests/test_writegate_merge_gap.py, server/tests/test_writegate_session_sites.py, server/tests/test_writegate.py, server/tests/test_safety_ruleset.py"
lifecycle: spec-anchored
tags: "write-gate, classification, blacklist, showfile-write, backstop, seal-attribution, false-positive-cost, closed-set-revision"
tier: M
related_specs: [SPEC-COPILOT-BULKGATE-001, SPEC-COPILOT-WRITEGATE-001, SPEC-COPILOT-UNREQ-001, SPEC-COPILOT-RESTORE-001]
---

# SPEC-COPILOT-CLASSIFYGAP-001 — 마지막 방어선이 쇼파일 쓰기를 쇼파일 쓰기로 못 본다

> **이 SPEC 이 닫으려는 구멍**: 곡→콘솔 흐름이 실제로 쓰는 명령 네 개 —
> `Store Sequence … Cue … /Merge`, `Store Cue`, `Store Group`, `Store Timecode` —
> 가 분류 층에서 **하나도** 블랙리스트에 안 걸린다. 같은 층이 `Store Preset` 과
> `Delete` 는 잡는다. 오늘 이 명령들을 막는 것은 호출 자리마다 손으로 붙인
> **봉합(`BatchRisk` 선언)** 뿐이고, t321 실측에 따르면 **열 자리 중 일곱**은
> 그 봉합이 유일한 방어다.

## HISTORY

| 날짜 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-07 | 0.1.0 | 최초 작성 (plan only) | 이 트리(`e0a2263`)에서 직접 실측한 분류 프로브 + 8회 전체 스위트 측정 |

---

## §A 배경 — 왜 봉합만으로는 부족한가

t317~t323 이 쇼파일 쓰기 디스패치 자리 열 곳에 `BatchRisk` 선언을 붙여 닫았고,
t321 이 그 방어 귀속을 쟀다. 결과가 `server/tests/test_writegate_session_sites.py`
의 `SEAL_DEFENCE` 표다 — **seal-only 일곱, redundant 셋**. seal-only 는
「분류 층이 이 번들을 못 잡으므로 봉합이 떨어지면 카드가 아예 안 뜬다」는 뜻이다.

즉 오늘의 안전은 **자리마다 봉합이 빠짐없이 붙어 있다는 사실**에 전부 걸려 있다.
새 디스패치 자리가 하나 생기고 작성자가 선언을 잊으면, 그 자리는 카드 없이
콘솔에 닿는다. 분류 층은 원래 그 실수를 받아내는 받침인데, 지금은 눈을 감고 있다.

이 SPEC 은 봉합을 대체하지 않는다. **봉합 뒤에 받침을 놓는다.**

## §B 실측 — 구멍은 지금도 열려 있다

카드 배차서의 진단이 낡았을 가능성을 먼저 지웠다. 이 트리에서 도메인 자신의
분류기로 다시 쟀다(grep 아님).

```
interpreter: 3.11.15
server pkg : …/.claude/worktrees/agent-aa3e0d9b63f90e338/server/__init__.py
ruleset ver: 4

'Store Sequence 210 Cue 3 /Merge'   -> None
'Store Cue 1'                       -> None
'Store Group 3'                     -> None
'Store Timecode 9'                  -> None
'Store Preset 4.101'                -> 'Store Preset'
'Delete Sequence 5'                 -> 'Delete'
```

네 명령 모두 `category='safe'`, `risky=False`, `reasons=()`. 구멍은 닫히지
않았다. 이 SPEC 은 유효하다.

### 왜 `Store Preset` 은 걸리고 이것들은 안 걸리는가

`blacklist.yaml` v4 의 Store 계열 항목은 `Store /overwrite` 와 `Store Preset`
둘뿐이다. `_match_blacklist` 는 항목의 첫 낱말을 동사에, 나머지를 인자에
맞추므로, `Store` 동사에 `Preset` 이 아닌 대상이 오면 아무 항목도 안 맞는다.
`Store` 동사 전체를 넣는 확대는 2026-08-05 사용자 결정과 카드 t86 에서 이미
두 번 거절됐고, 그 거절은 이 SPEC 도 지킨다(§F 참조).

## §C 비용 실측 — 배차서의 「8건」은 낡았다

배차서는 t292 측정을 인용해 「확대하면 테스트 8건이 깨진다」고 적었다. 그 숫자는
**당시 `Store Sequence` 한 항목만** 넣고 쟀을 때의 값이다(룩 생성 4 · FX 2 ·
씬 컴파일 1 · 룰셋 핀 1). 이 트리에서 같은 한 항목을 다시 재면 **33건**이다.

분모가 움직였기 때문이다 — t292 이후 BULKGATE-001(t317~t323)이
`test_writegate_session_sites.py`(15) 와 `test_bulkgate_declaration.py`(2) 를
새로 넣었다. `blacklist.yaml` v4 헤더가 스스로 경고해 둔 그대로다:
「\[READ THIS BEFORE QUOTING ANY FAILURE COUNT\] The denominator MOVES.」

측정 절차는 `server/safety/` 를 **한 글자도 고치지 않고** 수행했다.
`load_ruleset` 의 기본 인자를 스크래치 파일로 갈아끼우는 pytest 플러그인을 써서
넓힌 룰셋으로 전체 스위트를 돌렸다(§plan.md §C 에 절차 전문).

기준선: **12002 passed, 19 skipped, 0 failed** (exit 0).

| 넣은 항목 | 실패 | 통과 |
|---|---|---|
| `Store Timecode` 만 | 6 | 12000 |
| `Store Group` 만 | 13 | 11993 |
| `Store Sequence` 만 | **33** | 11973 |
| `Store Cue` 만 | **62** | 11944 |
| 네 항목 전부 | **71** (고유 함수 54) | 11947 |

항목끼리 겹친다(`Store Cue` 는 `Store Sequence 210 Cue 3` 도 잡는다). 그래서
개별 합(114)이 동시 투입(71)보다 크다.

**대조군**: 원본 `blacklist.yaml` 을 바이트 동일하게 복사해 다른 경로에 두고
같은 플러그인으로 돌리면 **1 failed / 12001 passed**. 그 1건이 내 계측기가 만든
유일한 인공물(`test_default_path_is_the_ssot_yaml_under_server_safety`)이다.
계측기가 눈먼 도구는 아니라는 근거이기도 하다.

## §D 이 SPEC 이 답해야 하는 설계 질문

### D-1 판별 술어 — 무엇이 쓰기이고 무엇이 프로그래머 트래픽인가

`server/orchestrator/write_reason.py` 의 `showfile_write_risk` /
`describe_showfile_write` 가 이미 작동하는 답을 갖고 있다. 열 자리 봉합과
모델 통로(t323)가 그것을 쓴다. 술어의 재료는 정규식 열두 개이고, 대상은
`Store Preset` · `Store Sequence … Cue` · `Store Cue` · `Store Group` ·
`Store Page` · `Store Macro` · `Store Sequence`(bare) · `Store Timecode` ·
`Set Fixture … Pos*` · `Assign Sequence … At Executor` · `Copy Sequence` 다.

그 모듈의 docstring 이 술어의 요점을 이미 못 박아 뒀다: 표에 없는 번들 —
`Fixture 20 ; Attribute 'Pan' At 12` 같은 프로그래머 값 — 은 쇼파일을 안 고치므로
**없다고 답한다**. 「안 고치는 번들에 카드를 띄우면 감독은 곧 카드를 안 읽게 되고,
그게 진짜 쓰기를 통과시킨다.」 이 SPEC 의 중심 설계 판단도 같은 문장 위에 선다.

재사용할지 따로 세울지는 **run 단계가 근거와 함께 정한다.** 재사용의 값은 두
층이 같은 답을 말한다는 것이고, 대가는 방향이 반대라는 점이다:
`write_reason` 은 **번들 단위 문면 생성기**이고 분류 층은 **명령 단위 폐집합
판정기**다. `blacklist.yaml` 헤더가 지키는 성질(폐집합, 리비전마다 버전 상승과
근거 기록)은 정규식 모듈로는 표현되지 않는다.

### D-2 봉합과의 관계 — 대체인가, 받침인가, 중복인가

**받침이다.** 그리고 카드가 두 장 되는 문제는 **이미 풀려 있다** — 실측으로
확인했다. `SafetyGate.screen` 은 선언이 있으면 분류 결과를 흡수해 요청을
**정확히 하나** 만들고, 봉합 사유를 앞에 붙이면서 분류 사유를 잃지 않는다.

넓힌 룰셋 + 봉합을 같이 넣고 실제 게이트를 돌린 결과:

```
sealed + widened -> approval requests = 1
items in that single request = 3
   Store Sequence 210 Cue 3 /Merge | ('SEAL-REASON', "blacklisted command (matches closed-set entry 'Store Sequence')")
   Store Timecode 9               | ('SEAL-REASON', "blacklisted command (matches closed-set entry 'Store Timecode')")
   Fixture 20 ; Attribute 'Pan' At 12 | ('SEAL-REASON',)
```

따라서 t323 의 `ExecutionContext.approval_owned_by_caller` 는 **이 충돌에
해당하지 않는다.** 그 플래그는 디스패치 층에서 *봉합 자체*가 두 번 생기는 것을
막는 장치이고, 분류 층이 카드를 더 만드는 문제가 아니다. 다만 그 플래그를 켠
호출자(`_cue_sheet_draft_apply`, `server/web/session.py:9049·9999`)는 **자기
승인 채널을 따로 갖는다** — 그 자리에서 분류 층이 새로 보류를 만들면 감독이
카드를 두 번 보는 유일한 경로가 된다. §E 의 검증이 그 자리를 겨눈다.

### D-3 깨지는 테스트 — 갱신할 것과 확대가 틀렸다고 말하는 것

§C 의 54개(고유 함수) 전수 분류는 `acceptance.md` §D.2 가 표로 들고 있다.
분류 원칙은 셋이다.

1. **갱신 대상** — 동작이 의도대로 바뀌어서 깨지는 것. 폐집합 핀, 오늘의
   눈감음을 고정한 핀, `SEAL_DEFENCE` 귀속표가 여기 든다. 특히 귀속표는
   실패 메시지가 스스로 「표를 다시 재서 갱신해 주세요」라고 적어 둔,
   **재측정을 전제로 설계된** 핀이다.
2. **확대가 틀렸다는 신호** — 쇼파일을 안 고치는 흐름이 승인을 요구하게 되는 것.
   룩 생성·FX·큐시트 반영이 후보다. 이쪽은 일괄 갱신하지 않는다.
3. **계측 인공물** — 내 측정 하네스가 만든 것. 대조군이 지목한 2건.

[NEEDS CLARIFICATION] 는 `plan.md` 가 들고 있다 — 특히 FX 번들과 큐시트 반영이
2번인지 1번인지는 문면만으로 못 정한다.

## §E 요구사항 (GEARS)

### 기능 요구

- **REQ-CG-001** (Ubiquitous) — 분류 층은 곡→콘솔 흐름이 쓰는 쇼파일 쓰기 명령
  네 개(`Store Sequence … Cue …`, `Store Cue`, `Store Group`, `Store Timecode`)를
  `risky=True` 로 판정해야 한다.

- **REQ-CG-002** (Where, 능력 게이트) — 봉합 선언이 붙은 번들에서, 분류 층이
  같은 번들의 명령을 보류로 판정하는 경우에도, 게이트는 승인 요청을
  **정확히 하나만** 만들어야 한다.

- **REQ-CG-003** (When, 사건 기반) — 분류 층이 명령을 블랙리스트로 판정할 때,
  게이트는 봉합 사유와 분류 사유를 **둘 다** 승인 카드 문면에 실어야 한다.

- **REQ-CG-004** (Ubiquitous) — 확대 뒤에도 `SEAL_DEFENCE` 표의 seal-only 자리
  수는 확대 전보다 줄어들어야 한다(받침이 실제로 받친다는 관측).

- **REQ-CG-005** (While, 상태 기반) — 폐집합 리비전이 올라가 있는 동안,
  `blacklist.yaml` 은 버전을 올리고 `v<N-1> -> v<N>` 항목에 비준 SPEC 이름과
  측정 비용을 기록해야 한다.

### 불원 요구 (shall not)

- **REQ-CG-006** — 분류 층은 프로그래머 값 설정·선택·조회 명령을 `risky=True`
  로 판정해서는 안 된다. 대상 문장은 최소한 다음을 포함한다:
  `Fixture 20 ; Attribute 'Pan' At 12`, `At 100`, `Group 4`,
  `Fixture 1 Thru 12`, `Set Selection MAtricks 'PhaseFromX' 0`,
  `Label Group 3 'Vocals'`, `Go+ Sequence 5`, `Off Fixture 11`,
  `ChangeDestination Root`.

- **REQ-CG-007** — 이 SPEC 은 `Store` **동사 전체**를 블랙리스트에 넣어서는
  안 된다. 2026-08-05 사용자 결정과 카드 t86 이 비용 근거로 두 번 거절했고,
  t86 재측정에서 동사 확대는 평범한 대화 한 회차에도 승인 카드를 띄웠다.

- **REQ-CG-008** — 이 SPEC 은 `SEAL_DEFENCE` 표를 「redundant 로 바꾸기 위해」
  봉합을 떼어내서는 안 된다. 받침을 놓는 SPEC 이 방어를 하나 줄이면 순 손실이다.

### 비기능 요구

- **REQ-CG-009** (Ubiquitous) — 확대로 깨지는 테스트는 항목별 기여도와 함께
  분류되어야 하며, 일괄 갱신은 금지된다. 각 갱신은 개별 근거를 갖는다.

- **REQ-CG-010** (When, 사건 기반) — 확대 비용을 인용할 때, 실패 수는 그 시점의
  전체 수와 함께 기록되어야 한다(분모가 움직인다).

## §F 범위 제외

### Out of Scope — `Store` 동사 확대

- `Store` 동사 자체를 폐집합에 넣는 확대는 이 SPEC 의 범위가 아니다. 두 번 거절된
  결정이고, REQ-CG-007 이 이를 금지로 못 박는다.
- `Store Page` · `Store Macro` · `Assign Sequence` · `Copy Sequence` 는 이
  SPEC 이 닫는 네 명령에 들지 않는다. `write_reason.py` 는 이들을 쓰기로 세지만,
  실측 근거(t291 실패 관측)가 가리키는 것은 네 개뿐이다. 각자 후속 카드를 갖는다.

### Out of Scope — 봉합 제거·이설

- 열 자리 `BatchRisk` 봉합을 떼거나 옮기는 일은 하지 않는다(REQ-CG-008).
- `ExecutionContext.approval_owned_by_caller` 의 의미를 바꾸지 않는다. §D-2 가
  이 플래그는 이 충돌의 장치가 아니라고 실측으로 확인했다.

### Out of Scope — `Label` 계열

- `Label Group` · `Label Preset` 은 「라벨링은 패치 쓰기가 아니다」라는 **의미
  판단**으로 제외돼 있다. 비용 측정으로 뒤집을 수 있는 종류의 결정이 아니므로
  이 SPEC 은 손대지 않는다.

### Out of Scope — 실기 검증

- 실제 콘솔(포트 8000)에 대고 쏘는 확인은 이 SPEC 의 범위가 아니다. 이 SPEC 이
  바꾸는 것은 승인 카드가 뜨는 조건이고, 그 판정은 전부 오프라인에서 관측된다.

### Out of Scope — 문법 층·expand 층

- `grammar.py` 와 `expand.py` 는 건드리지 않는다. t322 실측이 seal-only 번들에서
  문법 실패 0건, `invoking` 분류 0건임을 이미 기록했다 — 이 구멍은 분류 층의
  것이다.

---

## §G 교차 참조

- `SPEC-COPILOT-BULKGATE-001` — 봉합을 붙인 SPEC. 이 SPEC 이 그 뒤에 받침을 놓는다.
- `SPEC-COPILOT-UNREQ-001`(t86) — `Store Preset` 을 넣은 리비전. 비용 측정 절차와
  「동사 확대 거절」의 근거를 세웠다.
- `SPEC-COPILOT-WRITEGATE-001` — `Set Fixture` 를 넣은 첫 리비전.
- `server/tests/test_writegate_merge_gap.py` — 오늘의 눈감음을 고정한 핀. 이 SPEC
  이 뒤집는 대상.
- `server/tests/test_writegate_session_sites.py` — `SEAL_DEFENCE` 귀속표.
