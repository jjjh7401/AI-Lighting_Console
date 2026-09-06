---
id: SPEC-COPILOT-BULKGATE-001
title: "곡 하나가 명령 28개로 나가는데 승인 카드가 없다 — 번들 위험 선언을 게이트에 붙인다"
version: "0.1.0"
status: draft
created: 2026-09-07
updated: 2026-09-07
author: manager-spec (plan session, t291·t292·t294·t296 후속)
priority: P0
phase: "v1.8.3 target"
module: "server/safety/gate.py, server/safety/approval.py, server/orchestrator/tools.py, server/tests/test_write_dispatch_census.py, server/tests/test_writegate_merge_gap.py"
lifecycle: spec-anchored
tags: "write-gate, approval, showfile-write, songcue, batch-risk, dispatch-census, fail-closed, blast-radius"
tier: M
related_specs: [SPEC-COPILOT-WRITEGATE-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-UNREQ-001, SPEC-COPILOT-MUSICSYNC-001]
---

# SPEC-COPILOT-BULKGATE-001 — 곡 하나가 쇼파일을 고치는데 감독은 「주의」 배지만 본다

> **이 SPEC 이 닫는 구멍**: 감독이 곡 파일 하나를 올리면 **명령 28개**가 콘솔로 나가고, 그 안에 `Store Sequence 210 Cue 1..4` 와 `Store Timecode 9` 가 들어 있는데, 화면에 뜨는 것은 「주의」 배지가 붙은 미리보기 카드뿐이고 **승인 컨트롤이 없다.**
>
> 2026-09-07 브라우저 실측(가짜 콘솔): 곡 1개 업로드 → 「명령 28개 — 실행 완료 25 · 건너뜀 3」. 감사 로그에 `approved` 항목은 남지 않는다.
>
> 카드 t292 가 같은 계열의 **다른 통로 하나**(초안 반영)를 닫았다. 이 SPEC 이 닫는 것은 **더 큰 쪽**인 곡→콘솔 대량 경로이며, 동시에 **네 번째·다섯 번째 통로가 또 조용히 열리는 구조**를 검사로 막는다.

> **콘솔 예산.** 실기 grandMA3 발사는 이 SPEC 의 산출물이 아니다(§4). run 단계의 실측은 가짜 콘솔(`server/tests/fake_console.py`)과 브라우저에서 이뤄진다.

## HISTORY

| 날짜 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-07 | 0.1.0 | 최초 작성 (Tier M) | t291·t294·t296 감사 실측 · t292 비용 실측과 부분 봉합 · 2026-09-07 브라우저 실측 |

---

## §1 왜 (WHY)

### 1.1 관측된 손해 — 네 번 같은 모양으로 쟀다

| 회차 | 경로 | 감사 로그 |
|---|---|---|
| t291 | 초안 반영 (`_cue_sheet_draft_apply`) | `executed N, blocked 0, approved 0` |
| t294 | 같은 경로 | 같음 |
| t296 | 같은 경로 | 같음 |
| **2026-09-07 브라우저** | **곡→콘솔 대량 반영** | 명령 28개 · 실행 완료 25 · 건너뜀 3 · 승인 컨트롤 없음 |

앞의 세 회차는 **초안 반영**이라는 좁은 통로를 쟀고, 카드 t292 가 그 통로를 닫았다 — `_accept_draft_apply_batch`(`server/web/session.py:8887`)가 디스패치 **직전**에 묶음 단위 수락을 한 번 받고, `ApprovalChannel` 을 그대로 재사용하며, 감사 로그에 `approved`/`rejected` 를 남긴다.

**곡→콘솔 경로는 그대로 열려 있다.** 그리고 이쪽이 노출이 더 크다: 초안 반영은 감독이 이미 큐시트를 고친 뒤 「반영해」라고 말한 결과지만, 곡 업로드는 **한 번의 업로드가 시퀀스 하나와 타임코드 슬롯 하나를 통째로 만든다.**

### 1.2 왜 게이트가 안 잡는가 — 게이트는 멀쩡하다

`server/safety/classify.py` 는 명령 **텍스트**로 분류하고, `server/safety/blacklist.yaml` 의 `Store` 항목은 둘뿐이며 둘 다 오브젝트/옵션 기준이다(`Store /overwrite`, `Store Preset`). `Sequence` 도 `Timecode` 도 그 목록에 없다.

이 트리(`b7b030a`)에서 확인한 판정 고정(`server/tests/test_writegate_merge_gap.py:37-50`):

```python
UNCARDED_SEQUENCE_WRITES = (
    "Store Sequence 210 Cue 1 /Merge",
    "Store Sequence 210 Cue 1",
    "Store Sequence 210",
)
# → verdict.category == "safe", verdict.risky is False, verdict.matched_entry is None
```

같은 파일이 게이트 자체는 건강함을 함께 못박는다(`:66-70`): `Set Fixture 11 Posx '5.0'` → `Set Fixture`, `Store Preset 4.1` → `Store Preset`, `Delete Sequence 210` → `Delete`. **게이트가 죽은 게 아니라 이 오브젝트가 목록에 없다.**

### 1.3 왜 「목록에 넣는다」로 안 고쳤는가 — 비용을 재고 거절했다

카드 t292 가 분류 확대 경로를 재고 숫자와 함께 거절했다.

| 잰 것 | 값 | 출처 |
|---|---|---|
| `Store Sequence` 를 `blacklist.yaml` 에 넣는 **코퍼스** 비용 | **0** — 코퍼스에 그런 줄이 없다 | t292 실측 |
| **스위트** 비용 | **13건 실패** | t292 실측 |
| 그중 이 구멍을 위해 존재하는 핀 | 5건 (`test_writegate_merge_gap.py`) | t292 실측 |
| **그중 범위 밖 부수 피해** | **8건** | t292 실측 |

부수 피해 8건의 내역(파일별):

| 파일 | 건수 | 무엇이 붉어지는가 |
|---|---|---|
| `server/tests/test_safety_ruleset.py` | 1 | 룰셋 내용 핀 |
| `server/tests/test_web_session.py::TestLastCreatedSessionTracking` | 4 | **룩 생성** |
| `server/tests/test_fx_boundary.py` | 2 | **FX 인스턴스화** |
| `server/tests/test_scene_boundary.py` | 1 | **씬 컴파일** |

즉 분류를 넓히면 **이 통로만이 아니라 룩 생성·FX·씬 컴파일에도 승인 카드가 붙는다.** 그것은 테스트 픽스처 변경이 아니라 **제품 동작 변경**이다.

같은 축의 판단이 이 저장소에서 이미 두 번 내려졌고, 그 기록이 `blacklist.yaml` 헤더에 남아 있다(`:69-96`):

- 2026-08-05 사용자 결정으로 `Store` **동사** 확대가 철회됐다.
- 카드 t86 이 그 비용을 재측정했고, 결정은 유지된 정도가 아니라 **과소평가된 숫자 위에 내려져 있었다** — 전량 스위트 기준 `Store` 67건 대 `Label` 17건, 약 4배 차이. `Store` 하나만 넣어도 `test_web_session::TestHappyPath::test_korean_instruction_executes_and_reports_in_korean` 이 무너진다. 「평범한 대화 한 턴이 승인 카드를 띄운다」는 상태다.
- 그래서 v4 는 **동사가 아니라 오브젝트 하나**(`Store Preset`)만 넓혔다.

같은 헤더가 인용 규율도 남긴다(`:90-96`): **분모가 움직인다.** `test_writegate.py` 가 이 파일의 블랙리스트를 순회하므로 항목 하나를 넣을 때마다 검사 4개가 생긴다. 「13건 실패」는 고정 분모 위의 값이 아니다.

**그리고 PRESERVE 가드는 장애물이 아니다.** t292 가 별도로 확인했다 — `test_overlap_preserve.py` 는 **삭제 줄**을 판정하므로 `blacklist.yaml` 에 항목을 **추가**하는 것은 `test_overlap_preserve` 를 통과한다. 막고 있는 것은 가드가 아니라 **폭발 반경**이다.

### 1.4 진짜 문제 — 좁은 봉합이 네 개 있고, 다섯 번째가 열려 있다

이 트리에서 프로덕션 코드의 승인 호출을 전수로 셌다(`grep -rn "request_approval(" server/ | grep -v /tests/`):

| # | 자리 | 무엇을 지키나 |
|---|---|---|
| 1 | `server/safety/gate.py:355` | 게이트 자신의 3단계 — **명령 텍스트가 risky 로 분류될 때만** |
| 2 | `server/orchestrator/tools.py:5603` (`import_lxseq_presets`) | 프리셋 쓰기 |
| 3 | `server/orchestrator/tools.py:6534` (`import_lxseq_cues`) | 큐 쓰기 |
| 4 | `server/orchestrator/tools.py:9486` (`create_arrangement_groups`) | 그룹 쓰기 |
| 5 | `server/web/session.py:8925` (`_accept_draft_apply_batch`) | 초안 반영 (t292) |

2~5 는 전부 **같은 이유로 각자 따로 만든 봉합**이다. `create_arrangement_groups` 의 주석이 그 이유를 적는다(`tools.py:9193-9196`): "Store Group/Label Group are classified safe there and would otherwise never see ANY approval stage".

그리고 디스패치 자리는 훨씬 많다. 같은 회차 실측:

```
grep -c 'name="run_commands"' server/web/session.py          →  16
grep -c 'name="run_commands"' server/orchestrator/tools.py   →  12
```

**프로덕션 디스패치 자리 28개, 그중 승인 봉합이 붙은 것은 4개다.** 곡→콘솔 경로(`tools.py:3108`)는 나머지 24개 중 하나이고, t292 자신의 보고가 이 구조를 이미 지목했다 — 나중에 추가되는 쓰기 경로는 아무것도 물려받지 않는다.

그러므로 이 SPEC 이 답해야 할 것은 두 가지다: **① 곡→콘솔 경로를 닫는다. ② 여섯 번째 경로가 조용히 열리지 못하게 한다.** ①만 하면 다섯 번째 봉합을 하나 더 만드는 것에 지나지 않는다.

---

## §2 무엇을 (WHAT)

게이트의 **단일 관문**(`SafetyGate.screen`)에 **번들 단위 위험 선언**을 받는 통로를 하나 낸다. 호출자는 「이 묶음은 쇼파일을 고친다」를 선언하고, 게이트는 명령 텍스트를 다시 분류하지 않은 채 그 묶음 전체를 보류로 다루어 **카드 한 장**을 띄운다.

곡→콘솔 경로(`prepare_songcue`)가 그 선언을 붙인다. 그리고 **디스패치 자리 전수 조사 검사**를 세워, 새 쓰기 경로가 분류도 봉합도 없이 추가되면 검사가 붉어지게 한다.

`server/safety/blacklist.yaml` 은 **한 바이트도 바뀌지 않는다.** 명령 텍스트의 분류는 오늘과 같고, 그래서 §1.3 의 부수 피해 8건은 **발생하지 않는다.**

---

## §3 요구사항 (GEARS)

### 3.1 선언 통로 — 게이트의 관문에 붙인다

- **REQ-BULKGATE-001** [Ubiquitous] — the `server/safety/gate.py` **shall** frozen dataclass `BatchRisk`(필드 `reason: str`, `kind: str`)를 얻고, `SafetyGate.screen` 은 키워드 전용 인자 `risk: BatchRisk | None = None` 을 얻는다. 기본값 `None` 에서 이 메서드의 동작은 **바이트 동일**하다 — 오늘의 호출자 전부가 영향을 받지 않는다.
- **REQ-BULKGATE-002** [Event-driven] — **When** `screen` 이 `None` 이 아닌 `risk` 를 받으면, the 게이트 **shall** 명령 하나하나의 분류 결과와 무관하게 **번들 전체**를 보류로 다루고, 그 번들의 모든 명령을 담은 `ApprovalRequest` 를 **정확히 하나** 만든다. 이미 risky 로 분류된 명령이 섞여 있어도 요청은 하나다 — 승인은 이미 전부-또는-전무이므로(`server/safety/approval.py:28`) 카드가 둘로 갈라지지 않는다.
- **REQ-BULKGATE-003** [Ubiquitous] — the 승인 결과 **shall** 감사 로그에 `approved` 또는 `rejected` 사건으로 남고, `kind` 에 `risk.kind` 를 실어 어느 통로의 판단이었는지 구별된다. 형태는 t292 가 세운 것과 같다(`log_approved(commands, held=commands, kind="draft_apply")`).
- **REQ-BULKGATE-004** [Unwanted] — the 선언 **shall not** 모델이 만질 수 있는 자리에 놓인다. `ToolCall.arguments` 의 어떤 키도 `risk` 를 설정하거나 해제하지 못하며, 선언은 `build_toolset` 내부 `run_commands` 클로저의 **키워드 인자로만** 흐른다. 모델이 `arguments` 에 `risk` 를 실어 보내면 그 키는 무시되고 선언은 생기지 않는다.
- **REQ-BULKGATE-005** [Event-driven] — **When** 승인이 거절되거나(거절·시간 초과·채널 미결선) 답이 오지 않으면, the 게이트 **shall** 비청산(`cleared=False`) 판정을 돌려주고 **명령은 0건 나간다**. 이 실패 안전은 기존 경로를 물려받는다(`DenyAllApprovalPort`, `ApprovalChannel` 의 4중 거절) — 새로 만들지 않는다.

### 3.2 곡→콘솔 경로

- **REQ-BULKGATE-006** [Ubiquitous] — the `prepare_songcue`(`server/orchestrator/tools.py:2784`) **shall** `bundle.commands + timing.commands` 로 `run_commands` 에 재진입할 때 `BatchRisk` 를 함께 넘긴다. 새 디스패치 경로를 만들지 않는다 — 오늘과 같은 `run_commands` 재진입이며 게이트·LiveLock·중복 제거·감사가 전부 그대로 붙는다.
- **REQ-BULKGATE-007** [Ubiquitous] — the `reason` 문면 **shall** 감독이 무엇을 수락하는지 적는다: 시퀀스 번호, 큐 건수, 타임코드 슬롯 번호, 그리고 **이 앱에 복원 경로가 없다**는 사실. 「위험한 명령입니다」 같은 문장은 이 요구를 충족하지 않는다.
- **REQ-BULKGATE-008** [Event-driven] — **When** 감독이 묶음을 수락하면, the 앱 **shall** 그 묶음을 **한 번에** 발사하고 명령마다 다시 묻지 않는다. 28개 명령에 카드 28장이 뜨는 동작은 금지된다.
- **REQ-BULKGATE-009** [Event-driven] — **When** 감독이 거절하면, the 앱 **shall** 「콘솔에 0건 나갔다」를 문면으로 보고하고 **부분 반영을 주장하지 않는다**. 초안·확정 구간·타임라인 어느 쪽도 소실되지 않는다.

### 3.3 여섯 번째 경로를 잡는 자리

- **REQ-BULKGATE-010** [Ubiquitous] — the `server/tests/test_write_dispatch_census.py`(신규) **shall** `server/orchestrator/tools.py` 와 `server/web/session.py` 의 `name="run_commands"` 디스패치 자리를 정적으로 전수 열거하고, 각 자리가 모듈 수준 표 **둘 중 정확히 하나**에 등재돼 있음을 단언한다 — `SHOWFILE_WRITE_DISPATCHES`(쇼파일을 고치므로 봉합이 필요한 자리)와 `REVIEWED_NON_WRITE_DISPATCHES`(사람이 읽고 아니라고 판정한 자리, 사유 문자열 필수).
- **REQ-BULKGATE-011** [Event-driven] — **When** 어느 표에도 없는 디스패치 자리가 발견되면, the 검사 **shall** 실패하고 그 파일·행 번호를 실패 문면에 담는다. 이것이 여섯 번째 경로를 잡는 기제다 — 새 호출자를 추가한 사람이 「쇼파일을 고치는가」를 **분류하기 전에는 초록이 되지 않는다**.
- **REQ-BULKGATE-012** [Ubiquitous] — the 검사 **shall** `SHOWFILE_WRITE_DISPATCHES` 의 각 자리에 대해, 그 자리를 감싸는 함수 본문 안에 봉합이 있음을 단언한다 — `risk=` 선언, `request_approval(`, 또는 `_accept_` 로 시작하는 수락 헬퍼 호출 중 하나.
- **REQ-BULKGATE-013** [Ubiquitous] — the 검사의 **한계** **shall** 자기 독스트링에 적힌다: 이것은 `test_architecture.py` 와 같은 계열의 **정적 텍스트 주사**이며, 변수에 담아 간접 호출하는 형태는 못 잡는다. 잡지 못하는 것을 잡는다고 적지 않는다.

### 3.4 움직이지 않아야 하는 것

- **REQ-BULKGATE-014** [Unwanted] — the 이 SPEC **shall not** `server/safety/blacklist.yaml` 의 항목을 더하거나 빼거나 고친다. 명령 텍스트의 분류는 오늘과 같고, `server/safety/classify.py`·`ruleset.py`·`grammar.py` 도 바뀌지 않는다.
- **REQ-BULKGATE-015** [Unwanted] — the 이 SPEC **shall not** §1.3 의 부수 피해 8건을 건드린다. `test_safety_ruleset.py`·`test_web_session.py::TestLastCreatedSessionTracking`·`test_fx_boundary.py`·`test_scene_boundary.py` 는 **편집 0건으로 초록**이어야 하며, 룩 생성·FX 인스턴스화·씬 컴파일에 승인 카드가 새로 붙지 않는다.
- **REQ-BULKGATE-016** [Ubiquitous] — the `server/tests/test_writegate_merge_gap.py` 의 **단언들** **shall** 바이트 동일하게 유지된다 — 분류가 안 움직이므로 그 단언은 여전히 참이다. 대신 **모듈 독스트링**이 종결 기록을 얻는다: 전(이 노출은 열려 있고 고칠 자리는 `blacklist.yaml` 이라고 적혀 있었다) / 후(노출은 디스패치 층의 번들 선언으로 닫혔고, 분류는 의도적으로 그대로 두었으며 그 이유는 부수 피해 8건이다). 단언은 그대로 두고 문면만 고치는 이 조합이 **의도적**임을 그 독스트링이 명시한다.

---

## §4 범위 제외 (Exclusions)

이 절은 **만들지 않을 것**을 적는다. 아래 항목은 out of scope 이며, 이 SPEC 의 어떤 마일스톤도 이들을 건드리지 않는다.

### Out of Scope — 명령 분류의 확대

- `server/safety/blacklist.yaml` 에 `Store Sequence`·`Store Timecode`·`Store` 를 넣지 않는다. §1.3 의 비용(부수 피해 8건)이 이 SPEC 이 그 길을 안 가는 이유다.
- `server/safety/classify.py` 의 매칭 규칙, `grammar.py` 의 문법, `ruleset.py` 의 로더는 손대지 않는다.
- `Store Group`·`Store Cue`·`Store Page`·`Store Macro`·`Assign`·`Copy`·`Label` 계열의 분류는 오늘 그대로 `safe` 이며 그 비준(`test_writegate.py::UNCHANGED_SAFE`)은 유지된다.

### Out of Scope — 기존 봉합 넷의 통합

- `import_lxseq_presets`·`import_lxseq_cues`·`create_arrangement_groups`·`_accept_draft_apply_batch` 를 새 선언 통로로 옮기지 않는다. 넷 다 오늘 **동작하고 있고**, 옮기는 것은 동작 변경 위험을 지금 필요 없는 곳에서 지는 일이다.
- 다만 전수 조사 검사(REQ-010)는 이 넷을 `SHOWFILE_WRITE_DISPATCHES` 에 등재하고 봉합의 존재를 확인한다 — 통합은 안 하되 **셈에서 빠뜨리지는 않는다**.

### Out of Scope — 새 UI 와 새 채널

- `ui/src/components/ApprovalCard.tsx` 를 새로 만들거나 다른 카드로 대체하지 않는다. 이미 이 카드가 `ApprovalRequest` 를 그린다.
- `server/web/approval_bridge.py` 의 `ApprovalChannel` 을 고치지 않는다. 결선·시간 초과·연결 끊김의 실패 안전은 이미 그 파일이 갖고 있고, 이 SPEC 은 그것을 **소비**한다.
- 명령별 승인, 부분 승인, 승인 이력 화면은 만들지 않는다.

### Out of Scope — 실기 콘솔과 복원 경로

- 실기 grandMA3 에서 곡 반영을 발사해 확인하는 회차는 이 SPEC 의 산출물이 아니다. 검증은 가짜 콘솔과 브라우저에서 이뤄지며, 실기 확인은 sync 단계의 별도 카드로 올린다.
- 시퀀스·타임코드의 **복원 경로**는 만들지 않는다. 없다는 사실은 `reason` 문면이 감독에게 알리는 내용이지(REQ-007), 이 SPEC 이 고치는 대상이 아니다(`server/safety/gate.py:304-313` 의 미구현 기록 참조).

### Out of Scope — 세 번째 통로의 사후 조사

- 전수 조사 검사가 처음 돌 때 등재되지 않은 자리가 여럿 나올 수 있다(§1.4: 디스패치 28 대 봉합 4). run 단계는 그 자리들을 **분류만** 하고(쓰기인가 아닌가), 쓰기로 분류된 자리에 봉합을 새로 다는 일은 **이 SPEC 밖**이다 — 각자 자기 카드를 갖는다. 이 SPEC 이 봉합을 다는 자리는 곡→콘솔 하나뿐이다.

---

## §5 제약 (Constraints)

- **분류는 안 움직인다.** 이 SPEC 의 전체 설계가 그 제약 위에 서 있다. 분류를 넓히는 편집이 등장하면 그것은 다른 SPEC 이다.
- **선언은 모델이 못 만진다.** REQ-004 는 편의 조항이 아니라 안전 조항이다 — 모델이 끌 수 있는 안전장치는 안전장치가 아니다. 이 성질은 주석이 아니라 **검사로** 고정한다.
- **카드는 묶음당 한 장.** 28개 명령에 28장이 뜨면 감독은 읽지 않고 누른다. 그 상태는 승인이 아니라 승인의 외형이다.
- **거절은 0건 발사.** 부분 발사 경로를 만들지 않는다. `ApprovalRequest` 가 이미 전부-또는-전무이고, t292 가 같은 규율로 닫았다.
- **전수 조사 검사는 정적이다.** 간접 호출을 못 잡는다는 사실을 그 파일이 스스로 적는다(REQ-013). 잡는 범위를 과장하면 그 검사 자체가 공허해진다.
- **분모를 함께 적는다.** `blacklist.yaml:90-96` 의 규율 — 실패 건수를 인용할 때 전체 건수를 나란히 적는다. §1.3 의 「13건」도 그 규율 아래 t292 의 값을 옮긴 것이며, run 단계가 이 트리에서 재보는 것은 **분류를 안 넓힌 상태의 초록**이지 그 13건이 아니다.

---

## §6 성공 기준

- `acceptance.md` 의 AC-BULKGATE-001..012 전부 통과.
- `server/tests` 전량 초록, 새 회귀 0건. 특히 §1.3 의 부수 피해 8건이 **편집 없이** 초록.
- 곡→콘솔 회차 한 번에서 감사 로그에 `approved` 1건이 남고, 거절 회차에서 `rejected` 1건 · 콘솔 전송 0건.
- 전수 조사 검사가 등재되지 않은 디스패치 자리에서 **실패**함을 심은 변경으로 실측하고 되돌린다.
- `server/safety/blacklist.yaml` diff 0.
- 브라우저 실측 한 회차: 곡 업로드 → 승인 카드 등장 → 수락 → 명령 발사, 그리고 거절 → 0건.
