# SPEC-COPILOT-CLASSIFYGAP-001 — 진행 기록

카드 t299. **세 단계 전부 완료** — 이 SPEC 이 닫으려던 네 명령이 다 닫혔다
(`blacklist.yaml` v4 → v7).

- **Phase 1** — `Store Group` · `Store Timecode` 를 폐집합에 넣었다(v4 → v5).
  base `59ac394`, 전체 초록. PR #369 머지. 증거는 `reports/classifygap-t299-p1/`.
- **Phase 2** — `Store Sequence` 를 넣었고(v5 → v6), 그 확대가 드러낸 **중복 카드
  결함**까지 닫았다. base `ca34ebe`. 전체 스위트 `12012 passed · 31 skipped ·
  0 failed`, exit 0. PR #370 머지. plan.md §A-3 의
  `[NEEDS CLARIFICATION: 큐시트 이중 카드]` 는 감독 결정(갈래 2 — 반영 자리를
  봉합으로)으로 닫혔다. 증거는 `reports/classifygap-t299-p2/`.
- **Phase 3** — `Store Cue` 를 넣었다(v6 → v7). base `e158e44`. 실측 비용 **33**
  (plan 예측 62 를 옮겨 쓰지 않았다). 전체 스위트 `12017 passed · 31 skipped ·
  0 failed`, exit 0. 종류 2 신호 0건, `[NEEDS CLARIFICATION]` 0건. 증거는
  `reports/classifygap-t299-p3/`.

**남는 것은 이 SPEC 의 범위 밖이다.** `SEAL_DEFENCE` 의 seal-only 둘
(`_offer_fx_executor_assignment` · `_setlist_mode`)은 `Assign Sequence` ·
`Copy Sequence` 만 실어 나르고 §F 가 그 둘을 범위 밖에 뒀으므로 **이 SPEC 으로는
0 이 될 수 없다**(Phase 3 에서 자리별로 재서 확정). 카드 **t325** 가 받는다.
전체 수락 기준표는 아래 §E.2.F.

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
run_commit_sha: pending-backfill-t299-p2
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

### Phase 1 신호 (앞선 회차 기록)

> **형식 수리 (Phase 3 회차).** 아래 Phase 1 블록은 여는 펜스가 없어서 산문으로
> 렌더되고 있었고, 끝의 ``` 가 닫히지 않은 펜스를 열고 있었다. 내용은 바이트
> 그대로 두고 제목과 여는 펜스만 넣었다 — §E.3 는 이 에이전트가 소유하는
> 구획이라 형식 수리를 여기서 한다.

```yaml
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

---

## §E.2 Run-phase Evidence — Phase 3 (`Store Cue`, 마지막 구멍)

base `origin/main` `e158e44`(Phase 2 = PR #370 머지분), 브랜치
`WT-classify-widen-p3`, 인터프리터는 이 트리의 것(`uv run`, 3.11.15, `server`
패키지도 이 워크트리). 산출물 전체는 추적되는
`reports/classifygap-t299-p3/`(README 에 파일별 설명).

### 확대 전/후 분류 (`01_probe_before.txt` · `04_probe_after.txt`)

배차서가 지정한 여섯 명령, 같은 프로브·같은 순서. 두 회차의 차이는
`blacklist.yaml` 한 파일뿐이다.

| 명령 | 확대 전 | 확대 후 |
|---|---|---|
| `Store Group 3` | `Store Group` / risky | 같음 (Phase 1 회귀 없음) |
| `Store Timecode 9` | `Store Timecode` / risky | 같음 (회귀 없음) |
| `Store Sequence 210 Cue 3 /Merge` | `Store Sequence` / risky | 같음 (Phase 2 회귀 없음) |
| `Store Cue 1` | `None` / safe | **`Store Cue` / risky** |
| `Fixture 1 At 50` | `None` / safe | `None` / safe (**안 걸려야 하고 안 걸린다**) |
| `Group 4` | `None` / safe | `None` / safe (**안 걸려야 하고 안 걸린다**) |

AC-CG-001 이 **3/4 → 4/4** 가 됐다. 음성 대조군 9문장 전부 `risky=False`(잘못 판정
0건), 흐름 단위로도 승인 요청 0건 · `cleared=True`. 봉합과 겹치면 요청은 정확히
1건이고 사유가 병기된다.

**프로브 라벨 하나를 고쳤다.** `[E-2]`(아홉 문장 전부를 흐름으로)는 카드가 0 이
아니라 1이다 — `Go+ Sequence 5` · `Off Fixture 11` 이 호출 동사(`category='invoking'`)
라서 expand-or-hold 규칙(REQ-MVP-026)으로 보류되기 때문이고, 확대와 무관하다.
처음 돌린 판이 그것을 「AC-CG-003 위반」처럼 읽히게 적어서, 라벨을 참고 측정으로
바꾸고 확대 전을 다시 돌렸다. AC-CG-003 의 번들은 `[E]` 다.

### Phase 3 자체 비용 (`00_baseline_e158e44.txt` · `03_cost_p3.txt`)

| 회차 | 결과 | 전체 |
|---|---|---|
| 기준선 (확대 전) | `12012 passed · 31 skipped · 0 failed`, exit 0 | 12043 |
| `Store Cue` 투입 | `33 failed · 11983 passed · 31 skipped` | 12047 |

**plan 단계는 이 항목 단독을 62 로 쟀다**(트리 `e0a2263`, 계측 플러그인, 전체
12021). 이 트리의 실측은 **33** 이다 — 62 를 옮겨 쓰지 않았다. 차이가 큰 이유는
전제가 셋 달라진 것이다: 분모가 v5·v6 으로 두 번 움직였고, Phase 1·2 가 「안전한
예」 리터럴 여럿을 이미 비-`Store` 명령으로 옮겼고, 계측 플러그인 인공물이 이
회차에는 안 섞인다.

파일별 분포: `safety_gate` 14 · `safety_classify` 6 · `writegate` 2 ·
`safety_ruleset` 2 · `safety_expand` 2 · `deploy_scan` 2 · `writegate_merge_gap` 1 ·
`showfile_replacement_gate` 1 · `safety_e2e_audit` 1 · `safety_corpus` 1 ·
`safety_bootstrap` 1.

### 33건의 판정 — 종류 2 는 0건

| 종류 | 건수 | 처리 |
|---|---|---|
| 1 — 갱신 대상 | **33** | 개별 근거를 주석/docstring 에 적고 갱신 |
| 2 — 확대가 틀렸다는 신호 | **0** | — |
| 3 — 계측 인공물 | **0** | 계측 플러그인 미사용 |
| `[NEEDS CLARIFICATION]` | **0** | 감독 판단이 필요한 자리가 없었다 |

**33건 전부가 같은 모양이었다**: `Store Cue <n>` 을 「안전한 예 / 깨끗한 본문 /
benign 본문」 리터럴로 쓰던 배관 검사, 또는 폐집합·버전·코퍼스 장부 핀. 쇼파일을
안 고치는 흐름이 승인을 요구하게 된 자리는 하나도 없다.

**plan 단계가 종류 2 후보로 든 파일들이 이 회차에 한 건도 없다.** 측정 명령·출력:
`grep -cE 'web_cue_sheet_apply|seeded_song_apply|fx_boundary|writegate_session_sites' reports/classifygap-t299-p3/03_cost_p3.txt` → `0`.
그 자리들이 실어 나르는 쇼파일 쓰기는 `Store Sequence <N> Cue <M>` 이고 v6 이 이미
잡았으므로 이 확대가 새로 건드릴 것이 없고, Phase 2 가 큐시트 반영의 중복 질문자를
제거해 그 자리가 이미 봉합이 됐다.

**배차서 전제 하나가 이 회차에는 안 통했다.** 배차서는 「plan 단계의 8 신호가 전부
Phase 2 에 왔다 — 새 신호는 새 정보다」라고 적었고, 이 회차의 새 신호 수는 0 이다.

### 확대가 옳다는 근거 (귀속) — 두 층이 이미 같은 답을 하고 있었다

확대 **전** 같은 프로브에서 `Store Cue 1` 이 `matched_entry=None / risky=False`
였고, 확대 **후** `risky=True` 로 바뀌었다. 두 회차의 차이는 `blacklist.yaml`
한 파일뿐이다.

그리고 이 판단은 이 리비전이 새로 만든 것이 아니다. `write_reason.py` 의
`_STORE_CUE`(카드 t323)가 같은 줄을 이미 「쇼파일 쓰기」로 읽고 있었다 — 즉 봉합
층과 분류 층이 같은 명령에 대해 서로 다른 답을 하고 있었고, 이 리비전이 그
불일치를 없앤다. 측정 명령·출력:
`grep -n '_STORE_CUE' server/orchestrator/write_reason.py` → `47:_STORE_CUE = re.compile(r"\bStore Cue (\d+(?:\.\d+)?)")`.

### 배차서 전제 정정 — 「두 번째 사유가 실린다」는 이 배치에서 안 성립한다 (`08`)

배차서는 「your widening adds a second matching entry to the same bundle. It must
stay 1」이라고 적었다. **카드 1장 유지는 맞지만 기전이 다르고**, 그 차이가 배치
결정을 좌우한다. 합성 룰셋 셋으로 잰 값:

| 룰셋 | `Store Sequence 210 Cue 10 /Merge` 의 `matched_entry` |
|---|---|
| ① 배치된 순서 (`Store Sequence` 앞) | `'Store Sequence'` |
| ② `Store Cue` **만** 든 룰셋 | `'Store Cue'` — 항목이 그 줄에 **닿는다** |
| ③ `Store Cue` 를 앞으로 뒤집은 순서 | `'Store Cue'` — 귀속이 **바뀐다** |

항목 수준에서는 두 번째 일치가 성립하지만 `classify.py::_match_blacklist` 가 **첫**
일치에서 즉시 돌아오므로 두 번째 사유는 카드에 실리지 않는다. 그래서 이 배치의
성질은 「사유 병기」가 아니라 「v6 귀속 보존」이고, 항목을 목록 **끝**에 둔 것이 그
조건이다. 주석으로만 두면 누가 위로 옮겨도 아무것도 붉어지지 않으므로
`test_the_entry_order_preserves_the_sequence_attribution` 을 새로 넣어 검사로 지킨다.

### 큐시트 카드 수 — 확대 전후 모두 1장 (`02` · `06` · `12` · `13`)

| | 확대 전 | 확대 후 | 갱신 후 |
|---|---|---|---|
| 승인 요청 | **1장** (항목 5) | **1장** (항목 5) | **1장** (항목 5) |
| `Store Sequence` 줄의 귀속 | `'Store Sequence'` | 같음 | 같음 |
| 감사 로그(수락) | `[('approved','draft_apply')]` | 같음 | 같음 |

거절하면 콘솔 **0건**, 감사 로그 `[('rejected','draft_apply')]`, 답장은
「승인받지 못해 … 콘솔에는 아무것도 쓰지 않았습니다」(`13`). Phase 2 가 낸 비용
(이중 카드)에 해당하는 것이 이 회차에는 **없다**.

### 받침 재측정 — 이 회차는 `SEAL_DEFENCE` 를 움직이지 않는다 (`07`)

**손으로 고치지 않았다.** `probe_seal_defence_p3.py` 가 자리별로 재고, 그 출력이
배치된 `test_writegate_session_sites.py::SEAL_DEFENCE` 와 **줄 단위로 일치**한다.
그래서 그 파일의 diff 는 없다 —
측정 명령·출력: `git diff --stat -- server/tests/test_writegate_session_sites.py` → 출력 없음.

| | Phase 2 뒤 | Phase 3 뒤 (실측) |
|---|---|---|
| 자리 수 | 11 | 11 |
| seal-only | 2 | **2 / 11** |

**감독이 물은 것에 대한 답 — 이 회차는 남은 두 자리 중 어느 것도 움직이지 않는다.**
파생이 아니라 자리별 실측이다:

| 자리 | 실측 | 나가는 쇼파일 쓰기 |
|---|---|---|
| `_offer_fx_executor_assignment` | seal-only (변화 없음) | `Assign Sequence 201 At Executor 101` |
| `_setlist_mode` | seal-only (변화 없음) | `Copy Sequence 300 At 210` · `Assign Sequence 210 At Executor 101` |

둘이 실어 나르는 것이 `Assign Sequence` · `Copy Sequence` 뿐이고 SPEC §F 가 그
둘을 범위 밖에 뒀으므로, `Store Cue` 를 넣어도 이 표는 움직일 수 없다. 카드
**t325** 가 그 둘을 받는다.

### 뮤테이션 — 모양이 Phase 1·2 와 다르다 (`09`)

`Store Cue` 한 줄만 되돌리면 **6 failed / 12007 passed / 31 skipped**(전체 12044).
Phase 1·2 는 「분류를 관측하는 단언이 하나뿐」이었지만 이 회차는 **셋**이다 —
배차서가 「어느 선례와도 같다고 가정하지 말라」고 한 그 지점이다.

| # | 빨개지는 검사 | 무엇을 관측하나 |
|---|---|---|
| 1 | `test_safety_classify::test_direct_blacklist_commands_are_blacklisted[Store Cue 1]` | **분류** (표준 핀) |
| 2 | `test_deploy_scan::test_quoted_object_name_never_matches` | **분류** (이 회차가 넣은 비공허성 짝) |
| 3 | `test_writegate_merge_gap::test_the_entry_order_preserves_the_sequence_attribution` | **분류** (이 회차가 넣은 비공허성 짝) |
| 4 | `test_safety_ruleset::test_blacklist_is_exactly_the_shipped_closed_set` | 장부 (멤버십·개수) |
| 5 | `test_writegate::test_the_measurement_corpus_cannot_collide_with_this_entry` | 장부 (코퍼스 충돌) |
| 6 | `test_writegate_merge_gap::test_the_blacklist_now_carries_every_store_object_this_spec_scoped` | 장부 (Store 계열 목록) |

분류 관측이 셋이 된 것은 이 회차가 비공허성 짝을 둘 더 넣었기 때문이고 의도한
결과다. 버전 핀(`version == 7`)은 이 뮤테이션에서 **안** 빨개진다(항목만 되돌렸으므로)
— 그래서 6건 전부가 항목 자체에 귀속된다.

### 빨개지지 않았는데 갱신한 것 하나 — 조용히 공허해지는 자리

`test_safety_classify::test_option_abbreviation_still_matches` 는 33건에 **없다**
(초록이었다). 그러나 옛 형태(`Store Cue 5 /o` 의 `category == "blacklisted"` 단언)는
v7 이후 **옵션을 아예 못 읽어도** 오브젝트가 걸려 초록이 된다 — 재려던 축이 다른
축에 가려지는 모양이다. 리터럴을 폐집합 밖 오브젝트로 옮기고
`matched_entry == "Store /overwrite"` 를 단언하게 바꿨다. 비용에는 안 들어가지만
갱신하지 않으면 방어가 조용히 사라지는 자리라 함께 적는다.

### 리터럴 교체 규율 — 예외 하나와 그 근거

「안전한 예」 리터럴은 **프로그래머 값**(`Fixture <n> At 50` 등)으로 옮겼다. 폐집합은
쇼파일 **쓰기** 오브젝트만 담으므로 어떤 리비전도 그쪽을 다시 잡지 않는다. Phase 1 이
하나를 당시 남은 구멍(`Store Sequence`)으로 옮겼다가 한 리비전 만에 다시 잃은 사고를
되풀이하지 않기 위한 규율이다.

**예외 하나.** `test_safety_classify.py` 의 옵션 축 검사 셋은 재는 축이 「`Store` 를
위험하게 만드는 것은 동사가 아니라 `/overwrite` **옵션**」이라서 `Store` 가 아닌
명령으로는 축 자체가 사라진다. 그래서 폐집합 밖의 `Store` 오브젝트(`Store Page 3`)를
쓰고, 그 전제를 `_OPTION_AXIS_OBJECT` 한 곳에서 읽게 한 뒤
`test_the_option_axis_literal_is_still_outside_the_closed_set` 으로 따로 지킨다.
후속 카드가 `Store Page` 를 넣는 날 실패 메시지가 「축이 깨졌다」가 아니라
「리터럴의 전제가 깨졌으니 이렇게 옮겨라」를 직접 말한다. **그 대가를 숨기지 않는다**
— `Store Page` 를 넣는 카드는 이 리터럴 이동을 함께 계획해야 한다.

### 손댄 파일 (13 + SPEC 산출물 1 + 추적되는 증거 디렉터리)

측정 명령·출력: `git diff --stat` → `14 files changed, 829 insertions(+), 80 deletions(-)`
— 아래 13개 + `progress.md` 이 문서(355행). 여기에 추적되는 미커밋 디렉터리
`reports/classifygap-t299-p3/` 가 더해진다(`git diff` 는 미추적 파일을 안 센다).

파일별: `blacklist.yaml` 107 · `test_safety_gate.py` 94 · `test_writegate_merge_gap.py` 90 ·
`test_safety_classify.py` 88 · `test_writegate.py` 34 · `test_safety_e2e_audit.py` 28 ·
`test_deploy_scan.py` 27 · `test_safety_ruleset.py` 24 · `test_safety_expand.py` 18 ·
`corpus.yaml` 14 · `test_safety_bootstrap.py` 12 ·
`test_showfile_replacement_gate.py` 10 · `test_safety_corpus.py` 8.

데이터 (2)

- `server/safety/blacklist.yaml` — v6 → v7, 항목 하나 추가(목록 **끝**). 헤더에
  실측 비용·순서 결정·뮤테이션 모양·받침 무변화를 기록
- `server/measurement/corpus.yaml` — 헤더의 narrowing 고지 갱신(cue-store 2건 합류,
  누적 7/21 시나리오 · 대표 과제 유형 3종이 무인 운전 밖)

핀 갱신 (11, 각각 개별 근거를 주석/docstring 에 적었다)

- `server/tests/test_safety_ruleset.py` — 폐집합 13→14, 버전 6→7
- `server/tests/test_safety_classify.py` — v7 분류 관측 핀 1행 추가 · 옵션 축
  리터럴을 `_OPTION_AXIS_OBJECT` 로 추출 + 전제 검사 신설 · 옵션 축약 검사를
  `matched_entry` 단언으로 강화 · 나머지 리터럴 프로그래머 값으로 이동
- `server/tests/test_writegate.py` — `UNCHANGED_SAFE` 에서 `Store Cue 12` 제거
  (개별 근거 기재), `RATIFIED_CORPUS_COLLISIONS` +2
- `server/tests/test_writegate_merge_gap.py` — **못을 뽑았다**: `Store Cue not in
  blacklist` 단언을 뒤집고 이름까지 바꿨다(검사가 자기 갱신을 예고해 뒀다).
  순서 보존 검사를 신설
- `server/tests/test_showfile_replacement_gate.py` — `UNCHANGED` 에서 `Store Cue 12`
  제거(Phase 1 이 같은 튜플에 적은 논거를 두 번째로 적용)
- `server/tests/test_safety_gate.py` — `safe_line()`/`SAFE_LINE` 도입, 빨개진 검사
  14개 본문 안에서만 운반용 리터럴 34줄 치환
- `server/tests/test_safety_expand.py` — `_CLEAN_BODY_LINE` 도입(2곳)
- `server/tests/test_safety_corpus.py` — 깨끗한 본문 리터럴 이동
- `server/tests/test_safety_bootstrap.py` — UDP 왕복 운반용 리터럴 이동
- `server/tests/test_safety_e2e_audit.py` — 안전 번들·잠금 단계 리터럴 이동
  (**연쇄 기전 기록**: 안전 번들이 위험해지면 `ScriptedApproval` 의 첫 `True` 를
  먹어서 3단계가 `False` 를 받는다 — 빨개진 줄은 3단계였지만 원인은 2단계다)
- `server/tests/test_deploy_scan.py` — 줄번호 보고 검사 리터럴 이동 · 인용 검사를
  **더 날카롭게** 갱신(옛 형태는 인용 규칙을 꺼도 초록이었다) + 비공허성 짝 추가

`server/safety/*.py` 코드는 **한 줄도 안 고쳤다**(제약). 측정 명령·출력:
`git diff --stat -- 'server/safety/*.py'` → 출력 없음.
`console/lua/` · `server/looks/library/` · `ui/` 미접촉(`git diff --stat --` 출력 없음),
포트 8000 미접촉(`git diff -- server/ | grep -c 8000` → 0).

### 최종 스위트 (`10_suite_final.txt`)

```
12017 passed, 31 skipped, 1 warning in 164.00s (0:02:44)
exit=0
```

전체 12048. **12047 → 12048 의 산수**(초록만 보고 넘기면 안 되는 숫자라 함께 적는다):
항목 하나가 `test_writegate.py` 에서 테스트를 4개 만들고(12043 + 4 = 12047), 이
회차가 검사를 셋 더하고 둘 뺐다 → 순 +1.

- 더한 셋: `test_the_option_axis_literal_is_still_outside_the_closed_set` ·
  `test_the_entry_order_preserves_the_sequence_attribution` ·
  `test_direct_blacklist_commands_are_blacklisted[Store Cue 1]`
- 뺀 둘: `test_the_form_stays_non_risky[Store Cue 12-…]` ·
  `test_classification_did_not_move[Store Cue 12]` (두 튜플에서 그 줄을 뺐으므로
  파라미터가 사라진다)

`skipped` 는 31 로 **안 움직였다** — `SEAL_DEFENCE` 의 자리 수와 redundant 비율이
그대로이므로 skip 조건이 걸리는 자리도 그대로다.

---

## §E.2.F SPEC 전체 수락 기준표 (네 단계 합산 — 이 SPEC 의 마감 측정)

> **Phase 4 갱신 (sync-phase, 2026-09-07, manager-docs).** 아래 표의 본문
> 행은 **Phase 1~3 시점(v7) 그대로 보존**한다(이력 왜곡 금지). Phase 4
> (카드 t325, PR #373, `blacklist.yaml` v7 → v8, main `197eb69`)가
> AC-CG-005 를 `seal-only 2 → 0` 으로 마저 닫았다 — 이 sync 세션이 최종
> 트리(`197eb69`)에서 재측정해 확인했다: 전체 스위트
> `12032 passed / 35 skipped / 0 failed`(`uv run python -m pytest server/tests -q`),
> `SEAL_DEFENCE`(`test_writegate_session_sites.py`) 11 항목 전부
> `redundant`(seal-only 0), 뮤테이션(두 항목 되돌림) `9 failed / 12015 passed / 35 skipped`
> — `_offer_fx_executor_assignment`·`_setlist_mode` 두 자리가 직접 죽는다.
> 증거: `reports/classifygap-t325-p4/`(run-phase) +
> `reports/classifygap-close/{full_suite.txt,ac005_targeted.txt,mutation.txt}`(sync-phase 재측정).

각 판정은 **최종 트리**(v7, 갱신 후)에서 다시 잰 값이거나, 해당 단계의 추적되는
증거 파일이다. 「이월」로 적힌 것은 그 단계에서 만족 불가였음을 자체 기록이
명시한 항목이다.

| AC | 최종 판정 | 어느 단계에서 충족됐나 | 검증 명령 | 실제 출력 / 증거 |
|---|---|---|---|---|
| AC-CG-001 (네 명령 보류) | **PASS** | Phase 3 (P1 2/4 → P2 3/4 → P3 4/4) | `uv run python reports/classifygap-t299-p3/probe_p3.py` `[B]` | `Store Group 3`·`Store Timecode 9`·`Store Sequence 210 Cue 3 /Merge`·`Store Cue 1` 전부 `PASS` · `=> AC-CG-001: 4/4` (`11_probe_final.txt`) |
| AC-CG-002 (프로그래머 9문장) **must-pass** | **PASS** | 세 단계 모두 | 같은 프로브 `[D]`·`[D-2]` | `=> risky 로 잘못 판정된 문장: 0 []` (아홉 문장 + 배차서 두 문장 모두 0) |
| AC-CG-003 (흐름 단위 카드 0장) **must-pass** | **PASS** | 세 단계 모두 | 같은 프로브 `[E]` | `approval requests: 0` · `cleared : True  status='cleared'` |
| AC-CG-004 (봉합과 겹쳐도 1장 + 사유 병기) | **PASS** | 세 단계 모두 | 같은 프로브 `[F]` | `approval requests: 1` · `items in request : 3` · `Store Cue 1` 과 `Store Sequence …` 각각 `('SEAL-REASON', "blacklisted command (matches closed-set entry '…')")` |
| AC-CG-005 (seal-only 감소) **must-pass** | **PASS** | **Phase 2** (7 → 2) → **Phase 4** (2 → 0, 카드 t325) | Phase 1-3: `uv run python reports/classifygap-t299-p3/probe_seal_defence_p3.py`. Phase 4: `uv run python reports/classifygap-t325-p4/probe_seal_defence_p4.py` + sync 재측정 `uv run python -m pytest server/tests/test_writegate_session_sites.py -q` | Phase 3 시점: `seal-only (실측) : 2 / 11`. Phase 4 뒤(sync 재측정, main `197eb69`): `SEAL_DEFENCE` 11/11 `redundant`, `56 passed, 22 skipped` — seal-only 0 |
| AC-CG-006 (봉합 그대로, 0건 제거) | **PASS** | 세 단계 모두 | `git diff --stat -- server/web/session.py` (Phase 3) + `SITES` 개수 | Phase 3 diff 출력 없음 · `sites: 11` / `seal_defence rows: 11` — 11 자리 전부 선언 보유, 제거 0건 |
| AC-CG-007 (동사 확대 안 함) | **PASS** | 세 단계 모두 | `load_ruleset()` 목록 + 평범한 대화 회차 | `bare Store present: False` · `test_web_session.py::TestHappyPath::test_korean_instruction_executes_and_reports_in_korean` → `1 passed` |
| AC-CG-008 (리비전 문서화) | **PASS** | 각 단계가 자기 리비전을 기록 | `uv run pytest -q server/tests/test_safety_ruleset.py` | `23 passed` — `version: 7`, `v4 -> v5`·`v5 -> v6`·`v6 -> v7` 세 항목이 `REVISION HISTORY` 블록 **안**에 있고 각각 `SPEC-COPILOT-CLASSIFYGAP-001` 을 명시. 3중 핀 통과 |
| AC-CG-009 (전체 초록 + 전체 수 병기 + 개별 근거) | **PASS** | Phase 3 (각 단계도 자기 회차에서 초록) | `uv run pytest -q server/tests` | `12017 passed, 31 skipped, 1 warning`, `exit=0` (전체 12048). 갱신된 검사 각각에 근거를 주석/docstring 으로 기재 |
| AC-CG-010 (종류 2 = 0건) **must-pass** | **PASS** | 세 단계 모두 | 각 단계 비용 파일의 전수 분류 | Phase 1 **0** / Phase 2 **0** / Phase 3 **0** — 누적 0건 |
| (Phase 4 추가행) 전체 스위트 최종 재확인 | **PASS** | Phase 4 (카드 t325) + sync 재측정 | `uv run python -m pytest server/tests -q` (이 worktree, main `197eb69`) | `12032 passed, 35 skipped, 1 warning`, exit 0 — Phase 3 의 `12017/31` 대비 +15 passed / +4 skipped (Phase 4 신규 검사 순증) |

**must-pass 넷(002·003·005·010) 전부 PASS.** §D.4 완료 정의 대조:

1. AC-CG-001~010 전부 PASS ✓
2. §D.2 종류 2 여덟 항목 판정 완료 ✓ — Phase 2 가 8건 전부 판정했고(갱신 대상 1 +
   중복 카드 결함 7) 0건으로 해소, Phase 3 의 새 신호 0건
3. 각 리비전 헤더에 항목별 비용과 그 시점 전체 수 기록 ✓ (v5·v6·v7)
4. 남는 구멍이 후속 카드로 등재 — **해소됨**: 카드 t325(PR #373, `blacklist.yaml` v7→v8, main `197eb69`)가 `Assign Sequence`·`Copy Sequence` 를 받아 AC-CG-005 의 남은 seal-only 둘을 0 으로 닫았다(sync-phase 재측정으로 확인, 아래 §E.4). `Store Page`·`Store Macro` 는 여전히 이 SPEC 범위 밖 — 별도 후속 카드 필요
5. 커밋 메시지가 t299 명시 + `🗿 MoAI` 종료 ✓

---

## §E.3 Run-phase Audit-Ready Signal — Phase 3

```yaml
run_complete_at: 2026-09-07
run_commit_sha: pending-backfill-t299-p3
run_status: complete
phase: "Phase 3 of 3 (Store Cue — 이 SPEC 의 마지막 구멍)"
base: e158e44
branch: WT-classify-widen-p3
interpreter: "uv run / 3.11.15 (this worktree)"
suite_baseline: "12012 passed / 31 skipped / 0 failed (12043 total)"
suite_widening_cost: "33 failed / 11983 passed / 31 skipped (12047 total)"
suite_final_green: "12017 passed / 31 skipped / 0 failed (12048 total), exit 0"
plan_predicted_cost: 62          # 트리 e0a2263, 계측 플러그인 — 옮겨 쓰지 않았다
measured_cost: 33
cost_gap_explained: "분모 2회 이동(v5·v6) + Phase 1·2 의 리터럴 선이동 + 플러그인 인공물 부재"
total_delta_explained: "12047 -> 12048: 검사 3 추가 - 2 제거 = 순 +1"
skipped_delta: "31 -> 31 (무변화) — SEAL_DEFENCE 자리 수/redundant 비율이 그대로"
mutation_revert_one_entry: "6 failed / 12007 passed / 31 skipped (12044 total)"
mutation_classification_observers: 3   # Phase 1·2 는 1 — 모양이 다르다
mutation_ledger_observers: 3
mutation_version_pin_fired: false      # 항목만 되돌렸으므로
seal_sites: 11
seal_only_before: 2
seal_only_after: 2
seal_sites_moved_by_this_phase: 0
seal_defence_table_hand_edited: false  # 재서 옮겼고, 옮길 것이 없었다
seal_defence_table_diff: "출력 없음 (git diff --stat -- server/tests/test_writegate_session_sites.py)"
cuesheet_cards_before_widening: 1
cuesheet_cards_after_widening: 1
cuesheet_cards_after_pin_updates: 1
cuesheet_reject_console_writes: 0
audit_kind_preserved: "draft_apply (수락·거절 양쪽)"
type2_signals_found: 0
needs_clarification_left_failing: 0
risk_signal_files_from_plan_phase_present: 0
entry_position: "목록 끝 — 첫 일치 규칙 때문에 v6 귀속(`Store Sequence`)이 보존된다"
entry_order_guarded_by_test: true      # test_the_entry_order_preserves_the_sequence_attribution
green_but_updated_anyway: 1            # test_option_abbreviation_still_matches (가려질 수 있게 됐다)
negative_control_false_positives: 0
flow_level_cards_on_programmer_traffic: 0
ruff_check: "All checks passed! (server/ 및 reports/classifygap-t299-p3/)"
ruff_format: "1 file reformatted (probe_entry_order.py, 공백만) — 포맷 뒤 출력 바이트 동일 확인"
touched_files_lint_gate: "test_overlap_preserve.py 57 passed"
live_desk_contact: 0
server_safety_py_modified: false
new_warnings_or_lints_introduced: 0
evidence_dir: reports/classifygap-t299-p3/
dispatch_premise_corrected:
  what: "「확대가 같은 번들에 두 번째 일치 항목을 더한다 → 사유 병기」"
  measured: "항목은 그 줄에 닿지만 `_match_blacklist` 가 첫 일치에서 돌아와 두 번째 사유는 안 실린다"
  consequence: "성질은 「사유 병기」가 아니라 「v6 귀속 보존」이고, 그것이 항목을 목록 끝에 둔 이유다"
  evidence: "reports/classifygap-t299-p3/08_entry_order.txt"
formatting_repair:
  what: "§E.3 Phase 1 블록에 여는 펜스가 없어 산문으로 렌더되고 끝의 ``` 가 미닫힘 펜스를 열고 있었다"
  how: "내용 바이트 그대로 두고 제목 + 여는 펜스만 추가"
open_for_operator:
  - "[RESOLVED, sync-phase 2026-09-07] AC-CG-005 의 남은 seal-only 둘 — 카드 t325(PR #373)가 `Assign Sequence`·`Copy Sequence` 를 받아 닫았다. sync 재측정: `SEAL_DEFENCE` 11/11 redundant, seal-only 0"
  - "`Store Page`·`Store Macro` 후속 카드는 `test_safety_classify._OPTION_AXIS_OBJECT` 이동을 함께 계획해야 한다 — 여전히 열려 있음"
  - "코퍼스 무인 운전 상실 누적: 7/21 시나리오, 대표 과제 유형 3종(group_create·preset_store·cue_store) — 여전히 열려 있음"
gaps:
  - "실기 검증 0건 — 콘솔 오프라인, 포트 8000 미접촉"
  - "`Store Page`·`Store Macro`·`Assign`·`Copy` 확대 비용 미측정(§F 범위 밖)"
  - "UI 렌더 미측정 — 서버 `approval_request` 이벤트 수로만 셌다"
  - "명시 선언과 레지스트리 자동 선언을 동시에 없앤 뮤테이션 미측정(Phase 2 와 동일하게 범위 밖)"
  - "`TestExecutorRenameInvariance` 의 두 파라미터가 바이트 동일해 before/after 를 구분 못 한다 — 관측·기록했으나 고치지 않았다(범위 밖)"
  - "`_retarget_gate_literals.py` 가 치환한 34줄을 손으로 한 줄씩 재검토하지는 않았다 — 대상 함수 본문 한정 + 최종 스위트 초록 + 뮤테이션으로 간접 확인"
```

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_complete_at: 2026-09-07
sync_commit_sha: pending-backfill-classifygap-close
sync_status: complete
base: 197eb69
worktree: WT-classifygap-close (.claude/worktrees/agent-a19db2ff3cfddc124)
interpreter: "uv run / this worktree (never primary checkout .venv)"
phases_covered: "1-4 (t299 P1-P3 + t325 P4), 이 SPEC 의 마지막 sync 닫힘"
suite_full_reexecution: "12032 passed / 35 skipped / 0 failed, exit 0 (reports/classifygap-close/full_suite.txt)"
ac005_targeted_reexecution: "server/tests/test_writegate_session_sites.py — 56 passed, 22 skipped (reports/classifygap-close/ac005_targeted.txt)"
mutation_revert_two_entries: "9 failed / 12015 passed / 35 skipped — 두 SEAL_DEFENCE 자리(_offer_fx_executor_assignment, _setlist_mode)가 직접 죽는다 (reports/classifygap-close/mutation.txt)"
mutation_restore_verified: "복원 후 diff 재확인 결과 server/safety/blacklist.yaml 변경분 없음(클린 복원)"
blacklist_version: 8
seal_only_final: 0
b12_self_test_a: "CHANGELOG 중복 검사 결과 0건 (사전 중복 없음, 이 커밋이 최초 진입)"
b12_self_test_b: "AC-ID 패턴 카운트 결과 10 (AC-CG-001~010, §E.2.F 표와 일치)"
b12_self_test_c: "CHANGELOG 신규 엔트리가 인용하는 모든 경로 사전 확인 완료 — server/safety/blacklist.yaml, server/tests/test_writegate_session_sites.py, reports/classifygap-t325-p4/, reports/classifygap-close/"
changelog_entry_position: "[Unreleased] > Added, 기존 최신 항목 위(SPEC-COPILOT-SONGCONFIRM-001 항목 앞)"
frontmatter_status_transitions:
  spec_md: "in-progress -> completed (updated 필드는 이미 2026-09-07이라 불변)"
  progress_md_e4: "이 블록으로 채움 (pending -> complete)"
canary_compliance_check:
  applicable: false
  reason: "이 SPEC 은 forward-looking 정책을 정의하지 않는다 — 순수 방어 확대 SPEC"
mx_tag_validation: "이 sync 세션에서 신규 @MX 주석 부여 없음 — 대상 파일(blacklist.yaml, test_writegate_*.py)이 코드가 아닌 데이터/테스트 파일이라 @MX 태그 대상 함수 신설 없음"
gaps:
  - "실기 검증 0건 — 콘솔 오프라인, 포트 8000 미접촉 (SPEC §D.5 명시 범위 밖, run-phase부터 불변)"
  - "이 sync 세션은 코드 변경을 하지 않았다 — spec.md/plan.md/acceptance.md 본문은 무편집(정책상 금지), progress.md/spec.md frontmatter/CHANGELOG.md만 편집"
  - "abandoned 중복 t325 워크트리(뮤테이션 적용 상태)는 손대지 않음 — 운영자 처분 대상"
  - "Store Page, Store Macro 확대 비용 — 여전히 미측정(§D.5 명시 범위 밖)"
residual_risk:
  - "sync_commit_sha는 이 파일을 쓰는 시점엔 아직 커밋 전이라 placeholder — 실제 커밋 후 SHA로 back-fill되지 않음(다음 세션이 이력 조회로 실측 가능)"
  - "PR #373 CI 결과는 이 sync 세션에서 재확인하지 않았다 — main에 머지된 상태이므로 green으로 간주하나 직접 관측하지 않았다"
```

