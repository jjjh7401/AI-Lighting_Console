# SPEC-COPILOT-CLASSIFYGAP-001 — 진행 기록

카드 t299. **Phase 1 만 수행했다** — 네 명령 중 `Store Group` · `Store Timecode`
둘만 폐집합에 넣었다. `Store Sequence`(Phase 2)와 `Store Cue`(Phase 3)는 열린
채로 남아 있고 각자 후속 카드를 갖는다. 감독의 단계 분할 결정이며, 그 전제
(위험 신호 파일이 Phase 1 집합에 없다)를 이 회차에서 재확인했다.

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

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-07
run_commit_sha: pending-backfill-t299-p1
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
ruff: "All checks passed!"
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
