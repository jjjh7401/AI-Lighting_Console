# SPEC-COPILOT-CLASSIFYGAP-001 — 진행 기록

카드 t299. **Phase 1 완료(PR #369 머지) · Phase 2 는 감독 판단 대기로 미완**.

- **Phase 1** — `Store Group` · `Store Timecode` 를 폐집합에 넣었다(v4 → v5).
  base `59ac394`, 전체 초록. 증거는 `reports/classifygap-t299-p1/`.
- **Phase 2** — `Store Sequence` 를 넣었고(v5 → v6), 그 확대가 드러낸 **중복 카드
  결함**까지 닫았다. base `ca34ebe`. 전체 스위트 `12012 passed · 31 skipped ·
  0 failed`, exit 0. plan.md §A-3 의
  `[NEEDS CLARIFICATION: 큐시트 이중 카드]` 는 감독 결정(갈래 2 — 반영 자리를
  봉합으로)으로 닫혔다. 증거는 `reports/classifygap-t299-p2/`.
- **Phase 3** — `Store Cue`. 미착수.

## §E.1 Plan-phase Audit-Ready Signal

- **SPEC ID 정규식 자체검사**: 실행됨, 출력 `PASS`
- **중복 ID 검사**: `.moai/specs` 에 `classifygap` 없음
- **프로브 재실행**: 배차서 진단이 낡지 않았음을 이 트리(`e0a2263`)에서 확인.
  네 명령 전부 `matched_entry=None`
- **비용 재측정**: 전체 스위트 8회. 기준선 12002 passed / 0 failed,
  항목별 6 · 13 · 33 · 62, 네 항목 동시 71(고유 54)
- **대조군**: 원본 바이트 동일 복사 → 1 failed / 12001 passed (인공물 1건 확정)
- **봉합 충돌 관측**: 봉합 + 확대 동시 투입 시 승인 요청 1건, 사유 병기 확인
- **산출물**: `reports/classifygap-t299/` (추적됨 — `.moai/state/` 는 gitignore 대상이라
  새 체크아웃에서 못 읽는다. e0a2263 이 세운 관례를 따랐다)
- **열린 판단 3건**: `plan.md` §A 의 `[NEEDS CLARIFICATION]` — 술어 소유 ·
  비용 수락 범위 · 큐시트 이중 카드. **감독 승인 전에는 run 진입 금지**
- 산출물: `spec.md` · `plan.md` · `acceptance.md` · `progress.md`

## §E.2 Run-phase Evidence

Phase 1 회차. base `origin/main` `59ac394`, 브랜치 `WT-classify-widen-p1`,
인터프리터는 이 트리의 것(`uv run`, 3.11.15). 산출물 전체는 추적되는
`reports/classifygap-t299-p1/`(README 에 파일별 설명).

### 단계 분할 전제 재확인 (감독 결정의 근거)

배차서의 항목별 파일 분포는 트리 `e0a2263` 에서 계측 플러그인으로 잰 값이다.
이 트리(`59ac394`)에서 두 항목을 실제로 넣고 다시 재니 파일 분포가 8개 파일이고,
위험 신호 파일 셋(`test_web_cue_sheet_apply.py` · `test_seeded_song_apply.py` ·
`test_fx_boundary.py`)은 **한 건도 없다**. 단계 분할 전제는 유효하다.

측정 명령·출력: `grep -cE 'test_web_cue_sheet_apply|test_seeded_song_apply|test_fx_boundary' reports/classifygap-t299-p1/03_cost_p1_combined.txt` → `0`.

다만 배차서 표의 `Store Group` 행은 파일 5개를 들었는데 실제 회차는 7개였다
(`test_deploy_gate_e2e.py` · `test_deploy_pipeline.py` 누락). 누락된 둘도 같은
계열(DEPLOY 의 `SAFE_SOURCE` 리터럴)이라 분할 판단은 안 바뀐다.

### AC 판정표

| AC | 판정 | 검증 명령 | 실제 출력 |
|---|---|---|---|
| AC-CG-001 (네 명령 보류) | **PARTIAL** — 2/4 | `uv run python reports/classifygap-t299-p1/probe_p1.py` | `'Store Group 3' -> matched_entry='Store Group' … risky=True` · `'Store Timecode 9' -> matched_entry='Store Timecode' … risky=True` · `'Store Sequence 210 Cue 3 /Merge' -> matched_entry=None … risky=False` · `'Store Cue 1' -> matched_entry=None … risky=False` |
| AC-CG-002 (프로그래머 트래픽 9문장) | **PASS** | 같은 프로브 `[D]` | `=> risky 로 잘못 판정된 문장: 0 []` |
| AC-CG-003 (흐름 단위 카드 0장) | **PASS** | 같은 프로브 `[E]` | `approval requests: 0` · `cleared: True  status='cleared'` |
| AC-CG-004 (봉합과 겹쳐도 카드 1장 + 사유 병기) | **PASS** | 같은 프로브 `[F]` | `approval requests: 1` · `items in request : 3` · 각 항목이 `('SEAL-REASON', "blacklisted command (matches closed-set entry 'Store Group')")` 형태로 사유 둘을 싣는다 |
| AC-CG-005 (seal-only 감소) | **FAIL — Phase 1 로는 원리적으로 불가** | `uv run python reports/classifygap-t299-p1/probe_seal_defence.py` | `seal-only (실측)  : 7` · `seal-only (표)    : 7` · `귀속이 움직인 자리: []` |
| AC-CG-006 (봉합 그대로, 0건 제거) | **PASS** | `05_seal_defence_after.txt` 가 열 자리 전부를 구동했고 카드가 떴다 | 자리 10개 전부 출력됨. `test_writegate_session_sites.py` 무수정(diff 0줄) |
| AC-CG-007 (동사 확대 안 함) | **PASS** | `uv run python reports/classifygap-t299-p1/probe_p1.py` 첫 줄 | `blacklist : [… 'Store Preset', 'Store Group', 'Store Timecode']` — 단독 `'Store'` 없음. `test_web_session.py::TestHappyPath::test_korean_instruction_executes_and_reports_in_korean` 은 최종 스위트에서 통과 |
| AC-CG-008 (리비전 문서화) | **PASS** | `uv run pytest -q server/tests/test_safety_ruleset.py` (최종 스위트에 포함) | `version: 5`, `v4 -> v5` 항목이 `REVISION HISTORY` 블록 안에 있고 `SPEC-COPILOT-CLASSIFYGAP-001` 을 명시. 3중 핀 통과 |
| AC-CG-009 (전체 초록 + 전체 수 병기) | **PASS** | `uv run pytest -q server/tests` | `12011 passed, 19 skipped, 1 warning in 161.17s` · `exit=0` (전체 12030) |
| AC-CG-010 (2번 종류 0건) | **PASS (Phase 1 범위 안에서)** | `03_cost_p1_combined.txt` 의 14건 전수 분류 | 14건 전부 1번(폐집합 핀·눈감음 핀) 또는 「안전한 예」 리터럴. 쇼파일을 안 고치는 흐름이 승인을 요구하게 된 자리 0건 |

### AC-CG-005 가 실패한 이유 (추론이 아니라 실측)

`05_seal_defence_after.txt` 가 자리마다 나가는 명령을 찍는다. seal-only 일곱
자리가 실어 나르는 쇼파일 쓰기는 전부 `Store Sequence` · `Assign Sequence` ·
`Copy Sequence` 다 — `Store Group` 도 `Store Timecode` 도 **한 자리도 없다**.

| 자리 | 나가는 쇼파일 쓰기 |
|---|---|
| `_position_fx_sequence` | `Store Sequence 201 Cue 1 'Circle'` |
| `_offer_fx_executor_assignment` | `Assign Sequence 201 At Executor 101` |
| `_phaser_recall_sequence` | `Store Sequence 201 Cue 1 'Breathe Warm' CueFade 2` |
| `_position_cue_store` | `Store Sequence 101 Cue 1 'Pos 2.28' CueFade 5` |
| `_position_cue_sheet` | `Store Sequence 110 Cue 1 …` · `… Cue 2 …` |
| `_merge_timeline_cue_position` | `Store Sequence 210 Cue 1 /Merge` |
| `_setlist_mode` | `Copy Sequence 300 At 210` · `Assign Sequence 210 At Executor 101` |

즉 Phase 1 의 두 항목으로는 이 표를 움직일 수 없다. AC-CG-005 는 **Phase 2
(`Store Sequence`)로 이월**되며, 위 표에서 다섯 자리가 `Store Sequence` 를
실어 나르므로 Phase 2 가 7 → 2 로 줄일 후보다 — 다만 그것은 위 실측 목록에서
한 걸음 나간 **파생 추정이고, 실측이 아니다**(Phase 2 룰셋으로 재야 확정된다).
남는 두 자리(`_offer_fx_executor_assignment` · `_setlist_mode`)는
`Assign Sequence` · `Copy Sequence` 만 실어 나르고 그 둘은 이 SPEC §F 가
명시적으로 범위 밖에 둔 명령이므로, Phase 2·3 을 다 해도 seal-only 는 0 이
안 된다. §F 의 「각자 후속 카드를 갖는다」가 그 자리를 가리킨다.

### 확대가 옳다는 근거 (귀속)

확대 **전** 같은 프로브에서 두 명령이 `matched_entry=None / risky=False` 였고
(`01_probe_before.txt`), 확대 **후** `risky=True` 로 바뀌었다
(`02_probe_after.txt`). 두 회차의 차이는 `blacklist.yaml` 한 파일뿐이다.

프로브를 `load_ruleset()` 기본 인자에 의존하도록 쓴 것은 plan 단계의 관측을
따른 것이다 — `load_ruleset` 의 기본값은 `def` 시점에 묶이므로 모듈 속성만
갈아끼우면 안 먹는다. 이 회차는 갈아끼우지 않고 **배치된 파일을 그대로** 고쳤기
때문에 그 함정에 걸리지 않는다(그래서 plan 단계의 인공물 2건도 안 난다).

### 뮤테이션

`Store Timecode` 한 줄만 되돌리면 `3 failed / 12004 passed / 19 skipped`
(전체 12026, `06_mutation_revert_timecode.txt`):

1. `test_safety_classify::test_direct_blacklist_commands_are_blacklisted[Store Timecode 9-Store Timecode]` — **분류를 관측하는 유일한 단언**
2. `test_safety_ruleset::test_blacklist_is_exactly_the_shipped_closed_set` — 멤버십
3. `test_writegate_merge_gap::test_the_blacklist_carries_no_entry_that_could_match_a_sequence_store` — Store 계열 목록

1번은 이 회차가 새로 넣은 핀이다. 없었다면 항목을 지워도 장부 두 줄만 빨개지고
「카드가 안 뜨게 됐다」는 아무 검사도 말하지 않았다.

### 손댄 파일 (10 + SPEC 산출물 2)

측정 명령·출력: `git diff --stat` → `12 files changed, 407 insertions(+), 23 deletions(-)`
(아래 10개 + `spec.md` 상태 전이 + `progress.md` 이 문서).

- `server/safety/blacklist.yaml` — v4 → v5, 항목 둘 추가, 헤더에 실측 비용·뮤테이션 기록
- `server/measurement/corpus.yaml` — 헤더의 narrowing 고지 갱신(group-create 3건 합류)
- `server/tests/test_safety_ruleset.py` — 폐집합 핀 10→12, 버전 핀 4→5
- `server/tests/test_safety_classify.py` — v5 held-forms 핀 2행 추가
- `server/tests/test_writegate.py` — `UNCHANGED_SAFE` 에서 `Store Group 3` 제거(개별 근거 기재), `RATIFIED_CORPUS_COLLISIONS` +3, 비공허성 리터럴 2곳 교체
- `server/tests/test_writegate_merge_gap.py` — 「못을 반쯤 뽑은 기록」 추가, `store_entries` 목록 갱신
- `server/tests/test_showfile_replacement_gate.py` — `UNCHANGED` 리터럴 교체 + 비공허성 짝 교체
- `server/tests/test_deploy_pipeline.py` — `SAFE_SOURCE` 를 비-`Store` 명령으로 교체(`test_deploy_gate_e2e.py` 가 import)
- `server/tests/test_deploy_scan.py` — 같은 이유의 리터럴 교체
- `server/tests/test_bulkgate_declaration.py` — `SONGCUE_BUNDLE` 이 이제 **섞인**
  번들이 됨을 기록하고, 선언 축을 재는 두 검사의 대상을 남은 구멍
  (`SONGCUE_BUNDLE_STILL_UNCLASSIFIED`)으로 옮겼다. 단언은 바이트 그대로다 —
  대상만 이동했고, 이동 근거를 각 검사 docstring 에 적었다

`server/safety/*.py` 코드는 **한 줄도 안 고쳤다**(제약). `console/lua/` ·
`server/looks/library/` 미접촉, 포트 8000 미접촉.

---

## §E.2 Run-phase Evidence — Phase 2 (`Store Sequence`)

base `origin/main` `ca34ebe`(Phase 1 = PR #369 머지분), 브랜치
`WT-classify-widen-p2`, 인터프리터는 이 트리의 것(`uv run`, 3.11.15,
`server` 패키지도 이 워크트리). 산출물 전체는 추적되는
`reports/classifygap-t299-p2/`(README 에 파일별 설명).

### 확대 전/후 분류 (`01_probe_before.txt` · `04_probe_after.txt`)

배차서가 지정한 다섯 명령, 같은 프로브·같은 순서. 두 회차의 차이는
`blacklist.yaml` 한 파일뿐이다.

| 명령 | 확대 전 | 확대 후 |
|---|---|---|
| `Store Group 3` | `Store Group` / risky | `Store Group` / risky (Phase 1 회귀 없음) |
| `Store Timecode 9` | `Store Timecode` / risky | `Store Timecode` / risky (같음) |
| `Store Sequence 210 Cue 3 /Merge` | `None` / safe | **`Store Sequence` / risky** |
| `Store Cue 1` | `None` / safe | `None` / safe (**Phase 3, 미접촉**) |
| `Fixture 1 At 50` | `None` / safe | `None` / safe (**안 걸려야 하고 안 걸린다**) |

음성 대조군 9문장 전부 `risky=False`(잘못 판정 0건), 흐름 단위로도 승인 요청
0건 · `cleared=True`. 봉합과 겹치면 요청은 **정확히 1건**이고 사유가 병기된다.

### Phase 2 자체 비용 (`00_baseline_ca34ebe.txt` · `03_cost_p2.txt`)

| 회차 | 결과 | 전체 |
|---|---|---|
| 기준선 (확대 전) | `12011 passed · 19 skipped · 0 failed`, exit 0 | 12030 |
| `Store Sequence` 투입 | `32 failed · 11983 passed · 19 skipped` | 12034 |

plan 단계는 이 항목 단독을 **33** 으로 쟀다(트리 `e0a2263`, 계측 플러그인, 전체
12021). 이 트리의 실측은 **32** 다 — 33 을 옮겨 쓰지 않았다. 분모는 v5 가 이미
움직였고(항목 하나 = 테스트 4개), 계측 플러그인 인공물도 안 섞인다.

파일별 분포: `writegate_session_sites` 15 · `writegate_merge_gap` 5 ·
`web_cue_sheet_apply` 4 · `seeded_song_apply` 3 · `safety_ruleset` 2 ·
`bulkgate_declaration` 2 · `fx_boundary` 1.

### 위험 신호 8건의 판정

plan 단계 §D.2 가 종류 2 후보로 든 8건이 **전부** 이 회차에 왔다(배차서는 7 로
적었는데 `test_fx_boundary.py` 1건이 더 있다).

| 테스트 | 건수 | 판정 |
|---|---|---|
| `test_fx_boundary::…_fx_bundle…` | 1 | **갱신 대상** — 근거 아래 |
| `test_web_cue_sheet_apply` | 4 | **중복 카드 결함** — 갱신 금지, 감독 판단 대기 |
| `test_seeded_song_apply` | 3 | 같은 자리·같은 결함 |

**「확대가 틀렸다」로 판정한 것은 0건이다.** 8건 중 1건은 갱신 대상이고 7건은
갱신도 신호도 아닌 제3의 것 — 중복 카드다.

#### FX 1건을 갱신 대상으로 판정한 근거 (추론이 아니라 실측 둘)

1. **이 저장소의 봉합 술어가 이미 같은 답을 한다.** FX 번들 17줄 중 걸리는 줄은
   `Store Sequence 90 Cue 1 'M6'` 하나이고, 같은 번들에
   `write_reason.showfile_write_risk` 를 물으면
   `쇼파일 쓰기 — Sequence 90 에 큐 1건을 저장합니다` 를 답한다
   (`08_fx_bundle_probe.txt`). FX 시퀀스 저장을 쇼파일 쓰기로 보는 판단은 이
   리비전이 만든 것이 아니라 이미 비준돼 있었다.
2. **감독이 보는 카드 수는 늘지 않는다.** FX 디스패치 자리
   (`_position_fx_sequence`)는 이미 봉합돼 있고, v6 은 그 자리를 seal-only 에서
   redundant 로 바꾼다(`07`). 레지스트리를 지나는 FX 회차 검사들은 그대로
   통과한다(`test_fx_boundary.py` 40 passed).

갱신은 성질을 **좁혀서** 다시 못 박았다: 보류되는 줄은 시퀀스 저장 한 줄뿐이고
프로그래머 값 줄은 하나도 안 걸린다. 비공허성 짝도 같이 넣었다(번들이 10줄
이상이고 걸리는 것이 정확히 1줄).

### 큐시트 이중 카드 — 확대가 드러낸 결함 (`02` · `06`)

한 동작(초안 반영)에 승인 요청이 **1장 → 2장**이 된다. 실측이다.

| | 확대 전 | 확대 후 |
|---|---|---|
| 승인 요청 | **1장** (항목 5개) | **2장** |
| 카드 1 | `쇼파일 쓰기 — Sequence 210 의 큐 내용을 바꿉니다 …` (항목 5) | 같음 |
| 카드 2 | — | `blacklisted command (matches closed-set entry 'Store Sequence')` (항목 1) |
| 감사 로그 | `[('approved','draft_apply')]` | `[('approved','draft_apply'), ('approved', None)]` |

`request_id` 가 `approval-1`·`approval-2` 로 서로 다르다 — 같은 카드의 재전송이
아니라 서로 다른 요청이고, **둘째 장은 감독이 첫 장에서 이미 승인한 그 명령을
다시 묻는다**.

기전: 첫 장은 `session.py::_accept_draft_apply_batch`(:8980)가 자기 채널로 받는
수락, 둘째 장은 분류 층이 만든다. `ExecutionContext.approval_owned_by_caller` 는
*봉합* 카드만 막고 분류 카드는 막지 않는다(`gate.py:399·415`). 스위트의 폴러는
첫 장만 승인하고 돌아가므로(두 파일 모두 `_run_with_auto_approval`) 둘째 장이
타임아웃 거절되고 `console.executed == []` 가 된다 — 일곱 검사가 빨개지는
기전이 전부 이것 하나다.

중복 카드는 감독이 카드를 안 읽게 만드는 바로 그 사고이므로 절충이 아니라
결함이다. 그래서 이 7건을 갱신하지 않고 **원인을 고쳤다**.

### 결함 수정 — 묻는 주체를 하나로 (감독 결정: 갈래 2)

**억제가 아니라 제거.** `approval_owned_by_caller` 가 분류 카드까지 막게 하면
호출자가 최후 방어층의 눈을 감길 권한을 갖는다(fail-closed 의 반대). 그래서 두
번째 질문자를 없앴다:

- `session.py::_accept_draft_apply_batch`(자기 `ApprovalRequest` + 자기 채널
  `request_approval`)를 **삭제**했다.
- 대신 `showfile_write_risk(list(plan.commands), kind="draft_apply")` 로 선언을
  만들어 `ExecutionContext(risk=risk)` 로 넘긴다. 사유는 손으로 적지 않고 **나갈
  명령에서 서버가** 읽는다(t323 규율, 열 자리 봉합과 같은 함수).
- `approval_owned_by_caller=True` 를 **뗐다** — 승인을 호출자가 소유하지 않게 됐고,
  남겨두면 봉합 카드가 꺼져 카드가 0장이 된다.
- 선언이 `None` 이면 실행하지 않고 거절한다(fail-closed). 여기 오는 번들은
  `Store Sequence …` 를 반드시 싣지만, 못 읽으면 승인 없이 쇼파일을 고치게 되므로.
- 승인 거절은 「완료되지 않았다」와 다른 사건이라 그 문면으로 답한다. `rejected`
  는 게이트에서 승인 거절 경로에만 붙는다(다른 실패는 `blocked*` · `locked`).

**코드가 줄었다**: `git diff --stat server/web/session.py` → `32 insertions(+),
60 deletions(-)` = 순 **-28줄**. 플래그를 얹은 것이 아니라 중복 질문자를 지웠다.

측정 (`11` · `12`):

| | 확대 후(수정 전) | 수정 후 |
|---|---|---|
| 승인 요청 | **2장** | **1장** (항목 5) |
| `Store Sequence` 줄의 사유 | 카드마다 하나씩 | **둘 병기** — 선언 사유 + `blacklisted command (matches closed-set entry 'Store Sequence')` |
| 감사 로그(수락) | `[('approved','draft_apply'), ('approved', None)]` | `[('approved','draft_apply')]` — `kind` 보존 |
| 감사 로그(거절) | — | `[('rejected','draft_apply')]`, 콘솔 **0건** |

위험 신호 7건은 **두 파일 무수정**으로 초록이 됐다
(`git diff --stat server/tests/test_web_cue_sheet_apply.py
server/tests/test_seeded_song_apply.py` → 출력 없음). 결함이 사라지면 그래야 하고,
그것이 이 수정이 옳다는 독립 관측이다.

### 봉합 뮤테이션 — 이 자리는 방어가 셋이다 (`16` · `17`)

반영 자리의 `risk` 를 `None` 으로 되돌리면 **2 failed / 12010 passed / 31 skipped**
(전체 12043). 둘 다 `kind` 관측이다:

1. `test_web_cue_sheet_apply::test_the_acceptance_is_written_to_the_audit_log`
2. `test_writegate_session_sites::…::test_the_audit_names_this_site[_cue_sheet_draft_apply]`

**카드는 사라지지 않는다.** `17` 이 그 이유를 찍는다 — 카드는 여전히 1장 · 항목 5 ·
사유 둘이고, 감사 로그의 `kind` 만 `draft_apply` → **`model_run_commands`** 로
바뀐다. `tools.py::dispatch_run_commands` 가 `risk is None` 이고
`approval_owned_by_caller` 도 아니면 **선언을 스스로 만든다**(t323 모델 통로 받침,
같은 `showfile_write_risk`).

즉 이 자리의 방어는 셋이다: 명시 선언 → 레지스트리 자동 선언 → 분류 층. 명시
선언의 고유 기여는 이제 카드가 아니라 **`kind` 귀속**이고 2건이 그것을 관측한다.
Phase 1·2 항목 뮤테이션의 「분류를 관측하는 단언이 하나뿐」과는 **다른 모양**이므로
같은 문장으로 보고하지 않는다.

### 받침이 실제로 받친다 — AC-CG-005 (`07_seal_defence_after.txt`)

`SEAL_DEFENCE` 귀속 재측정: **seal-only 7 → 2**, 다섯 자리가 움직였다.

| 자리 | 표 | 실측 | 나가는 쇼파일 쓰기 |
|---|---|---|---|
| `_position_fx_sequence` | seal-only | **redundant** | `Store Sequence 201 Cue 1 'Circle'` |
| `_phaser_recall_sequence` | seal-only | **redundant** | `Store Sequence 201 Cue 1 'Breathe Warm' CueFade 2` |
| `_position_cue_store` | seal-only | **redundant** | `Store Sequence 101 Cue 1 'Pos 2.28' CueFade 5` |
| `_position_cue_sheet` | seal-only | **redundant** | `Store Sequence 110 Cue 1 …` · `… Cue 2 …` |
| `_merge_timeline_cue_position` | seal-only | **redundant** | `Store Sequence 210 Cue 1 /Merge` |
| `_offer_fx_executor_assignment` | seal-only | seal-only | `Assign Sequence 201 At Executor 101` |
| `_setlist_mode` | seal-only | seal-only | `Copy Sequence 300 At 210` · `Assign Sequence …` |

Phase 1 은 이 다섯을 「7 → 2 로 줄일 **후보**」로 적으면서 그것이 파생 추정이고
실측이 아니라고 명시했다. 이 회차가 자리별로 실측해 확정했다 — 예측이 맞았다.
남는 둘은 `Assign`·`Copy` 만 실어 나르고 SPEC §F 가 범위 밖에 뒀으므로,
Phase 2·3 을 다 해도 seal-only 는 0 이 안 된다(Phase 1 기록과 같은 결론).

**결함 수정 뒤 재측정 (`13`) — 자리가 하나 늘었다.** 반영 자리가 자기 승인 채널을
버리고 봉합이 됐으므로 `SITES` 에 열한 번째 자리로 들어왔다. 손으로 더하지 않고
`probe_seal_defence_p2.py` 의 출력을 그대로 표에 옮겼다.

| | 수정 전 | 수정 후 |
|---|---|---|
| 자리 수 | 10 | **11** (`_cue_sheet_draft_apply` 추가) |
| seal-only | 2 | **2 / 11** |
| 새 자리의 귀속 | (표 없음) | **redundant** — 분류 층이 이미 그 줄을 잡는다 |

새 자리가 `redundant` 인 것이 이 SPEC 의 목적 그대로다: 봉합이 떨어져도 분류 층이
받아낸다. 그래서 `skipped` 가 19 → 31 로 늘었다 — seal-only 전용 관측 둘이
redundant 자리에서 skip 되고, redundant 자리가 3 → 9 가 됐다.

### 뮤테이션 (`09_mutation_revert_sequence.txt`)

`Store Sequence` 한 줄만 되돌리면 `2 failed · 12010 passed · 19 skipped`
(전체 12031). 둘 중 **분류를 관측하는 것은 하나뿐**이다:

1. `test_safety_classify::test_direct_blacklist_commands_are_blacklisted`
   `[Store Sequence 210 Cue 3 /Merge]` — **이 회차가 새로 넣은 핀**
2. `test_safety_ruleset::test_every_shipped_revision_is_documented_in_the_file`
   — 버전 장부 핀(분류를 안 본다)

이 핀을 안 넣었다면 항목을 지워도 장부 한 줄만 빨개지고 「카드가 안 뜨게 됐다」는
아무 검사도 말하지 않았다. Phase 1 이 같은 자리에서 배운 성질이라 같은
파라미터 목록에 이어 넣었다(그 목록이 이 SPEC 의 분류 관측 지점이다).

### 손댄 파일 (9 + 미추적 증거 디렉터리)

측정 명령: `git diff --stat` → `8 files changed, 434 insertions(+),
202 deletions(-)` (아래 8개) + 미추적 `reports/classifygap-t299-p2/`.
`test_safety_classify.py` 는 앞선 커밋 `3e6dabc` 에 이미 들어갔다.

데이터·구현 (2)

- `server/safety/blacklist.yaml` — v5 → v6, 항목 하나 추가. 헤더에 실측 비용·
  귀속 이동·뮤테이션·드러난 결함과 그 처리를 기록
- `server/web/session.py` — 중복 질문자 제거. `_accept_draft_apply_batch` 삭제,
  `BatchRisk` 선언 + fail-closed 가드 + 승인거절 분기. 순 **-28줄**

핀 갱신 (6, 각각 개별 근거를 docstring/주석에 적었다)

- `server/tests/test_safety_classify.py` — v6 분류 관측 핀 1행(커밋 `3e6dabc`)
- `server/tests/test_fx_boundary.py` — FX 핀을 좁혀 갱신 + 비공허성 짝 추가
- `server/tests/test_safety_ruleset.py` — 폐집합 12→13, 버전 5→6
- `server/tests/test_writegate_merge_gap.py` — **못을 뽑았다**: 세 파라미터 핀과
  `/Merge` 대 `/Overwrite` 비대칭 핀, `"Store Sequence" not in blacklist` 단언을
  전부 뒤집고 이름까지 바꿨다. 뒤집는 근거를 모듈 docstring 에 이어 적었다
- `server/tests/test_writegate_session_sites.py` — `SITES` 에 열한 번째 자리
  추가(구동기 + kind), `SEAL_DEFENCE` 재측정값으로 갱신
- `server/tests/test_bulkgate_declaration.py` — 선언 축 대상을
  `PROGRAMMER_ONLY_BUNDLE`(비-`Store`)로 옮기고, Phase 1 이 잃은 A/B 를 한 번들로
  복원(비공허성 짝 추가)

문서 (1)

- `.moai/specs/SPEC-COPILOT-CLASSIFYGAP-001/progress.md` — 이 문서

`server/safety/*.py` 코드는 **한 줄도 안 고쳤다**(제약). `console/lua/` ·
`server/looks/library/` · `ui/` 미접촉, 포트 8000 미접촉.

**리터럴 교체 규율.** `test_bulkgate_declaration.py` 의 대상을 다른 `Store`
오브젝트로 옮기지 않았다 — Phase 1 이 남은 구멍(`Store Sequence`)으로 옮겼다가 한
리비전 만에 다시 잃었기 때문이다. 폐집합은 쇼파일 **쓰기** 오브젝트만 담으므로,
프로그래머 값 계열로 옮기면 어떤 리비전도 다시 잡지 않는다.

### 최종 스위트 (`14_suite_final.txt`)

```
12012 passed, 31 skipped, 1 warning in 178.91s (0:02:58)
exit=0
```

(전체 12043) `skipped` 19 → 31 의 근거는 위 `SEAL_DEFENCE` 절에 적었다 — 자리 수와
redundant 비율이 바뀌면 skip 조건이 걸리는 자리도 바뀐다. 초록만 보고 넘기면
안 되는 숫자라 함께 적는다.

---

## §E.3 Run-phase Audit-Ready Signal — Phase 2

```yaml
run_complete_at: 2026-09-07
run_commit_sha: "3e6dabc (확대·측정) + c5d6e64 (중복 카드 수정)"
run_status: complete
phase: "Phase 2 of 3 (Store Sequence + 중복 카드 결함 수정)"
base: ca34ebe
branch: WT-classify-widen-p2
interpreter: "uv run / 3.11.15 (this worktree)"
suite_baseline: "12011 passed / 19 skipped / 0 failed (12030 total)"
suite_widening_cost: "32 failed / 11983 passed / 19 skipped (12034 total)"
suite_final_green: "12012 passed / 31 skipped / 0 failed (12043 total), exit 0"
skipped_delta_explained: "19 -> 31 — seal-only 7->2 로 skip 조건 자리가 늘었다"
mutation_revert_one_entry: "2 failed / 12010 passed / 19 skipped (12031 total)"
mutation_entry_classification_observers: 1
mutation_seal_risk_none: "2 failed / 12010 passed / 31 skipped (12043 total)"
mutation_seal_observers: 2        # 둘 다 `kind` 귀속 관측
mutation_seal_card_survives: true # 레지스트리 자동 선언(t323)이 카드를 유지한다
seal_sites_before: 10
seal_sites_after: 11              # `_cue_sheet_draft_apply` 가 봉합 자리가 됐다
seal_only_before: 7
seal_only_after: 2
seal_sites_actually_moved: 5
cuesheet_cards_before_widening: 1
cuesheet_cards_after_widening: 2  # 결함
cuesheet_cards_after_fix: 1       # 항목 5, 사유 둘 병기
cuesheet_reject_console_writes: 0
audit_kind_preserved: "draft_apply (수락·거절 양쪽)"
risk_signal_tests_fixed_without_edit: 7
negative_control_false_positives: 0
flow_level_cards_on_programmer_traffic: 0
phase3_target_still_open: true    # 'Store Cue 1' -> matched_entry=None
type2_signals_found: 0
session_py_net_lines: -28
ruff_check: "All checks passed! (server/ 및 reports/classifygap-t299-p2/)"
ruff_format: "549 files already formatted"
live_desk_contact: 0
server_safety_py_modified: false
evidence_dir: reports/classifygap-t299-p2/
resolved:
  what: "큐시트 초안 반영 한 동작에 승인 카드가 2장 뜨던 결함"
  how: "두 번째 질문자 제거 — `_accept_draft_apply_batch` 삭제, `BatchRisk` 선언으로 게이트가 유일한 질문자"
  not_how: "`approval_owned_by_caller` 로 분류 카드를 억제하지 않았다(fail-closed 반대 방향)"
  plan_marker: "plan.md §A-3 [NEEDS CLARIFICATION: 큐시트 이중 카드] — 감독 결정으로 닫힘(갈래 2)"
  evidence: "reports/classifygap-t299-p2/11_cuesheet_cards_after_fix.txt · 12_cuesheet_reject.txt"
open_for_operator:
  - "Phase 3(`Store Cue`) 착수 — 남은 유일한 구멍"
  - "seal-only 둘(`Assign Sequence`·`Copy Sequence`)은 SPEC §F 범위 밖 — 후속 카드 필요"
gaps:
  - "명시 선언과 레지스트리 자동 선언을 동시에 없앤 뮤테이션은 안 쟀다"
  - "`session.py:9999`(`_song_finalize`) 자리의 카드 수는 안 셌다"
  - "FX 흐름 단위 카드 수는 간접 증거뿐(레지스트리 검사 통과)"
  - "UI 렌더는 안 쟀다 — 서버 `approval_request` 이벤트 수로만 셌다"
```
run_status: partial-by-design
phase: "Phase 1 of 3 (Store Group + Store Timecode)"
base: 59ac394
branch: WT-classify-widen-p1
interpreter: "uv run / 3.11.15 (this worktree)"
ac_pass_count: 8          # 002 003 004 006 007 008 009 010
ac_partial_count: 1       # 001 — 2 of 4 commands (staging decision)
ac_fail_count: 1          # 005 — not satisfiable by Phase 1; deferred to Phase 2
suite_baseline: "12002 passed / 19 skipped / 0 failed (12021 total)"
suite_widening_cost: "14 failed / 11996 passed / 19 skipped (12029 total)"
suite_final: "12011 passed / 19 skipped / 0 failed (12030 total), exit 0"
mutation_revert_one_entry: "3 failed / 12004 passed / 19 skipped (12026 total)"
seal_only_before: 7
seal_only_after: 7
ruff_check: "All checks passed! (server/ 및 reports/classifygap-t299-p1/)"
ruff_format: "초기 회차에서 프로브 스크립트 2건 미포맷 — 아래 lint_scope_correction 참조"
make_test_fast: "exit 0 (재실행)"
lint_scope_correction: |
  첫 push 가 pre-push 게이트에서 막혔다. 내가 돌린 것은 `uv run ruff check server/`
  였고 게이트가 재는 것은 `test_overlap_preserve.py::TestTouchedFilesPassLint` —
  **git diff 로 대상을 고르는** 검사다. 그래서 `reports/` 아래 프로브 스크립트 2건이
  내 회차에는 안 보였다. `uv run ruff format` 으로 두 파일을 포맷했고(공백만 변경),
  포맷 뒤 두 프로브를 다시 돌려 출력이 바이트 동일함을 확인했다
  (`diff /tmp/*_recheck.txt <해당 증거파일>` → 차이 없음). 그 뒤 `make -s test-fast`
  exit 0. 내 트리에서 초록인 것이 게이트에서 초록인 것과 같지 않았던 사례다.
type2_signals_found: 0
live_desk_contact: 0
new_warnings_or_lints_introduced: 0
server_safety_py_modified: false
evidence_dir: reports/classifygap-t299-p1/
open_for_operator:
  - "AC-CG-005 는 Phase 1 로는 만족 불가 — Phase 2 로 이월(근거: §E.2 자리별 명령 표)"
  - "Phase 2·3 을 다 해도 seal-only 는 0 이 안 된다(Assign/Copy 는 §F 범위 밖)"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
