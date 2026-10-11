# 카드 t577 run 판정 — M10 승인 시점을 편집에서 「⇪ 콘솔에 반영」으로 이동

SPEC-LDBEAT-001 REQ-LDBEAT-015(h-1)~(h-6) · AC-LDBEAT-016(v-1)~(v-5) · plan.md M10.
cycle_type: tdd. 콘솔 접촉: **0건**(FakeConsole/가짜 데이터만, 실기 응답기 미사용).

## 0. 선행 작업 — worktree 의 SPEC 문서 상태 교정 + main 동기화

이 워크트리는 카드 t578 머지(`63de8d95`, PR #619) 바로 뒤 지점에서 만들어졌는데,
카드 t577의 plan-phase 문서 커밋(`570df473`·`072c391f`, `WT-approval-at-apply`
브랜치)은 그 지점과 형제 커밋이라 자동으로 들어와 있지 않았다 — spec.md가
REQ-LDBEAT-015(h)를 옛 단일 절(재사용 금지만)로 갖고 있어 과제 계약과 불일치했다.
`git merge --no-ff 570df473`(문서 3개 변경, 코드 0줄)로 그 두 커밋을 병합해
REQ-015(h-1)~(h-6)·AC-016(v-1)~(v-5)·plan.md M10을 교정했다 — 병합 커밋
`358f3373`.

오케스트레이터 지시(작업 중 수신) — `git fetch origin main` 결과
`origin/main == 63de8d95`이고, 이는 이미 이 워크트리 HEAD의 조상이었다
(`git merge-base --is-ancestor origin/main HEAD` 참 — 병합할 새 커밋 없음).
origin/main 은 이 워크트리가 이미 반영한 지점에 머물러 있었다 — 추가 병합 불필요.

## 1. AC-LDBEAT-016(v-1)~(v-5) — PASS/FAIL 표

| AC | Given | 시험 | Status | 실제 결과 |
|---|---|---|---|---|
| (v-1) 승인 없는 새 번호 — 거절 아님, 승인 대기 | 완전한 `evidence.approval` 없이 새 프리셋 번호를 넣는 편집 | `test_apply_time_approval_t577.py::TestPendingAcceptanceAtEditTime::test_new_number_without_evidence_is_accepted_and_observed_pending` + `test_beat_grid_edit_t551.py::TestEvidenceApprovalReuse::test_new_effect_preset_number_without_approval_is_pending` | **PASS** | `BeatGridEditError` 없이 `(updated, report)` 반환, `check_evidence_approval(cue)`가 non-None(승인 대기), report에 "승인 대기" 포함 |
| (v-2) 저장된 승인 재사용 금지(h-5) | 이미 `evidence.approval`이 있는 칸에, 그 저장된 승인을 새 번호의 근거로 재사용하려는 편집(같은 `changes`에 새 `evidence` 없음) | `TestStoredApprovalIsNotReused::test_cell_with_a_stored_approval_stays_pending_for_a_fresh_new_number` + `test_beat_grid_bright_default_t555.py::test_cell_brightness_approval_does_not_admit_new_effect_number`/`..._dimmer_number` | **PASS** | 거절되지 않고 승인 대기로 남음; `check_evidence_approval(cue)`가 non-None — 저장된 승인이 새 번호를 통과시키지 않음(실측으로 저장 경로의 숨은 버그 1건을 잡고 고쳤다, §3 참조) |
| (v-3) 승인 카드 열거 + 승인 뒤 기록 | 승인 대기 칸·필드가 있는 상태에서 「⇪ 콘솔에 반영」 승인 카드 구성 → 감독 승인 | `TestApprovalCardEnumeratesPendingAndRecordsEvidence::test_risk_reason_lists_the_pending_preset_number` + `::test_approval_writes_evidence_only_on_the_enumerated_cell` + `::test_declined_card_writes_no_evidence_and_sends_nothing` | **PASS** | `risk_reasons`에 "새로 만드는 프리셋 1개: BACK 1마디 효과 프리셋 4.21" 포함; 승인 뒤 그 칸에 `evidence.approval{by:"supervisor",date,source}` 기록 + `check_evidence_approval`이 None(통과); 거절 시 evidence 기록 0건 + 콘솔 접촉 0건 |
| (v-4) 카드 밖 번호 — 0 송신, 승인 대기 유지 | 카드 구성 뒤 추가된 새 번호(별도 편집) | `TestNumbersAddedAfterCardConstructionStayPending::test_apply_pending_approval_only_touches_the_enumerated_set` | **PASS** | `apply_pending_approval(later_grid, pending=[BACK만], ...)` 호출 결과 SIDE-ALL 5마디 칸은 `evidence`가 바이트 그대로(`None`) — 여전히 승인 대기(`check_evidence_approval`이 non-None). 실제 세션에서 "0 송신"은 `emit_beat_grid_write_bundle`이 호출 시점 스냅샷(`grid`)으로만 커맨드를 만드는 기존 메커니즘이 자연히 보장(코드 변경 없음, plan.md M10 3단계 서술 그대로) |
| (v-5) 승인=송신 비교 불변(REQ-011, h-6) | 승인 대기 칸이 있는 상태에서 반영 1회 | `TestApprovalVsSentUnaffected::test_approval_vs_sent_still_matches_with_a_pending_cell_present` | **PASS** | `status["approval_vs_sent"]["match"] is True` — evidence 기록은 커맨드 바이트에 영향 0 |

## 2. 기존 거절 재현 시험 갱신(편집 시점 → 반영 시점/승인 대기)

| 파일 | 시험 | 이전 | 이후 |
|---|---|---|---|
| `test_beat_grid_bright_default_t555.py` | `test_cell_brightness_approval_does_not_admit_new_effect_number` | `pytest.raises(BeatGridEditError)` + "REQ-LDBEAT-015" 메시지 단언 | 예외 없이 통과 + `check_evidence_approval(cue) is not None` + report에 "승인 대기" |
| 〃 | `test_cell_brightness_approval_does_not_admit_new_dimmer_number` | 〃 | 〃 (디머 효과 `preset_no` 경로) |
| `test_beat_grid_edit_t551.py` | `TestEvidenceApprovalReuse::test_new_effect_preset_number_without_approval_is_rejected` → `..._is_pending`으로 이름 변경 | MOVER-U bar 11(기존 app_movement=Pan)에서 거절 단언 | 자리를 BACK bar 3(app_movement 없음)으로 옮겨 순수 승인-완전성만 가린다 — 거절이 없어지자 **원래 숨겨져 있던** MOVER-U bar 11의 축 충돌(REQ-006(vi-7))이 먼저 걸린다는 것을 실측(아래 §4)으로 확인했고, 그 경로는 `TestShapeVocabularyAndUnverifiedFlag::test_same_axis_conflict_with_effect_preset_is_rejected`(324행)가 이미 별도로 덮는다 |
| `test_session_beat_grid_edit_t551.py` | `TestSentenceNameLookup::test_effect_name_resolves_and_derives_effect_kind_from_the_matched_pool` | `event["summary"]`에 "거절" 단언, `store.latest == before` | `event["summary"]`에 "수정", `event["text"]`에 "승인 대기", `store.latest != before`(초안에 반영됨), MOVER-U bar14의 `effect_preset_no == "2.61"` 확인 |

갱신한 시험은 모두 **행동이 아니라 발화 시점만 바뀐다**(plan.md M10 4단계 그대로) — 저장된
승인이 새 번호를 통과시키지 않는다는 불변은 모든 갱신 시험에서 그대로 재확인된다.

## 3. 구현 요약 — 승인 대기 상태를 어떻게 만들었나

- **"승인 대기"는 새 필드가 아니라 파생 상태다**(plan.md M10 1단계 그대로) —
  `server/design/beat_grid.py` `pending_preset_fields(cue)`가
  `check_evidence_approval(cue)`(기존, REQ-015(f)/(g))와 네 프리셋 번호 필드
  (`brightness.preset_no`·`position_preset_no`·`color_preset_no`·`effect_preset_no`)
  의 교차로 파생한다. `pending_preset_approvals(grid)`가 그리드 전수를 돌아 승인
  대기 칸·필드를 `{group_name, bar, field, field_label, value}` 목록으로 만든다.
- **`server/design/beat_grid_edit.py` `apply_beat_grid_edit`**: 기존 두 분기
  (`effect_preset_no`, 디머 효과 `preset_no`)의 `raise BeatGridEditError(approval_reason)`을
  제거하고, `check_evidence_approval(fresh_approval_cue)`가 non-None이면
  `pending_fields` 리스트에 그 필드 이름을 쌓는다. `position_preset_no`·
  `color_preset_no`도 같은 모양으로 새로 추가했다(이전까지 이 승인 완전성
  판정 경로에 전혀 없던 틈 — plan.md 1단계가 지목한 그대로). `pending_fields`가
  비어 있지 않으면 report에 "⚠ 승인 대기 — ..." 한 줄을 추가한다.
  - **실측으로 잡은 결함(이 run-phase 자체 발견)**: 처음 구현에서는 `merged`
    (실제로 저장되는 칸)가 **base의 낡은 evidence를 그대로 들고** 있어, 저장된
    승인이 새 번호를 "거절하지는 않지만 몰래 승인된 것으로" 보이게 하는 버그가
    났다(`test_cell_brightness_approval_does_not_admit_new_dimmer_number`가 RED로
    잡았다 — `check_evidence_approval(cue)`가 거짓으로 `None`을 돌려줌). 고침:
    `pending_fields`가 비어 있지 않으면 `merged["evidence"]`를
    `fresh_approval_cue`가 본 값(통상 `None`)으로 덮어쓴다 — REQ-015(h-5)는
    판정 단계뿐 아니라 **저장**에도 적용돼야 한다는 것을 이 실측이 확인했다.
- **`server/web/session.py` `beat_grid_apply`**: 호출 시작 시점의 `grid`로
  `pending_before = pending_preset_approvals(grid)`를 한 번 계산해 (a) 승인
  카드 `risk_reason`에 "새로 만드는 프리셋 N개: ..."를 추가하고, (b) `_dispatch_declared`
  승인이 **통과한 뒤**(`executed.result.is_error`가 거짓인 뒤, `verdict` 계산
  전) `apply_pending_approval(grid, pending_before, by="supervisor", date=until,
  source=f"beat_grid_apply:{batch.sha256}")`로 그 칸들에만 `evidence.approval`을
  기록하고 `store.latest`에 다시 써넣는다. 카드 밖 번호(카드 구성 뒤 추가분)는
  `pending_before`에 없으므로 자연히 기록 대상 밖이다 — `emit_beat_grid_write_bundle`
  이 애초에 같은 스냅샷으로 커맨드를 만들었으므로 송신 집합도 이미 그 밖이다
  (코드 변경 없이 기존 스냅샷 메커니즘이 보장, plan.md 3단계 서술).
- **UI**: `ui/src/protocol.ts`의 `BeatGridCue.pending_preset_fields?: string[]`는
  서버 `attach_beat_grid_runtime_extras`가 매 서빙마다 다시 계산해 붙이는 뷰
  전용 필드다(저장 값 아님). `ui/src/components/BeatGrid.tsx`
  `pendingApprovalBadge(cue)`가 그 리스트를 그대로 읽어 "⚠ 승인 대기(...)"
  배지를 타임라인 큐 막대에 단다(기존 "⚠ 번호대 미확인"/"⚠ 실기 미확인"과
  같은 접두 관례). 승인 카드 자체의 텍스트("새로 만드는 프리셋 N개")는
  `BeatGridTopBar.tsx`를 따로 손대지 않았다 — 기존 범용 `ApprovalCard.tsx`가
  `BatchRisk.reason`에서 온 `risk_reasons`를 이미 그대로 렌더하므로, 서버가
  문구를 구성하는 것만으로 충분하다(실측: `ui/src/components/ApprovalCard.tsx:102`).

## 4. 검증 명령 + 결과(발췌)

```
$ uv run python -m pytest server/tests/test_apply_time_approval_t577.py \
    server/tests/test_beat_grid_bright_default_t555.py \
    server/tests/test_beat_grid_edit_t551.py \
    server/tests/test_session_beat_grid_edit_t551.py -v
...
============================== 83 passed in 1.28s ==============================
```

```
$ uv run python -m pytest server/tests/ -k "beat_grid or t577" -q
441 passed, 14869 deselected, 1 warning in 8.88s
```

```
$ uv run ruff check server/design/beat_grid.py server/design/beat_grid_edit.py \
    server/web/session.py server/tests/test_beat_grid_bright_default_t555.py \
    server/tests/test_beat_grid_edit_t551.py server/tests/test_session_beat_grid_edit_t551.py \
    server/tests/test_apply_time_approval_t577.py
All checks passed!
```

```
$ npx tsc --noEmit        # ui/
(출력 없음 — 통과)
```

```
$ npx vitest run src/components/BeatGrid.test.tsx src/components/BeatGridTopBar.test.tsx
 ✓ src/components/BeatGridTopBar.test.tsx (16 tests) 9ms
 ✓ src/components/BeatGrid.test.tsx (151 tests) 13ms
 Test Files  2 passed (2)
      Tests  167 passed (167)
```

RED 증거(초기 구현, 수정 전 실제 실패 — 반영 시점 거절로 갱신하기 전의
`test_cell_brightness_approval_does_not_admit_new_effect_number`/`..._dimmer_number`):

```
$ uv run python -m pytest server/tests/test_beat_grid_bright_default_t555.py -q
....FF.
FAILED ...test_cell_brightness_approval_does_not_admit_new_effect_number
  Failed: DID NOT RAISE BeatGridEditError
FAILED ...test_cell_brightness_approval_does_not_admit_new_dimmer_number
  Failed: DID NOT RAISE BeatGridEditError
2 failed, 5 passed in 0.16s
```

(저장 evidence 덮어쓰기 패치 전 — §3이 서술한 "숨은 버그"를 잡은 중간 RED,
실제 캡처 그대로):

```
$ uv run python -m pytest server/tests/test_beat_grid_bright_default_t555.py -q
________ test_cell_brightness_approval_does_not_admit_new_dimmer_number ________
>       assert check_evidence_approval(cue) is not None, "저장된 밝기 승인이 새 번호를 통과시켰다"
E       AssertionError: 저장된 밝기 승인이 새 번호를 통과시켰다
E       assert None is not None
E        +  where None = check_evidence_approval({'bar': 3, ..., 'brightness':
             {'mode': 'dimmer_effect', 'value_percent': None, 'preset_no': '1.22'}, ...})
FAILED ...test_cell_brightness_approval_does_not_admit_new_effect_number
FAILED ...test_cell_brightness_approval_does_not_admit_new_dimmer_number
2 failed, 5 passed in 0.14s
```

## 5. 변경 파일

```
server/design/beat_grid.py                          | +140 (pending_preset_fields/
                                                        pending_preset_approvals/
                                                        apply_pending_approval 신설,
                                                        attach_beat_grid_runtime_extras 확장)
server/design/beat_grid_edit.py                      | +58/-16 (편집 시점 즉시 거절 제거,
                                                        position/color 필드 포함, 저장
                                                        evidence 덮어쓰기)
server/web/session.py                                | +46 (beat_grid_apply — 열거+기록)
server/tests/test_apply_time_approval_t577.py        | 신설 330행 (v-1)~(v-5)
server/tests/test_beat_grid_bright_default_t555.py   | 갱신(거절→승인 대기 재현)
server/tests/test_beat_grid_edit_t551.py             | 갱신(거절→승인 대기 재현)
server/tests/test_session_beat_grid_edit_t551.py     | 갱신(거절→승인 대기 재현)
ui/src/protocol.ts                                   | +8 (BeatGridCue.pending_preset_fields)
ui/src/components/BeatGrid.tsx                        | +20 (pendingApprovalBadge + 렌더)
ui/src/components/BeatGrid.test.tsx                   | +27 (pendingApprovalBadge 시험 4건)
ui/src/styles.css                                     | +8 (.beat-grid-pending-approval-warn)
```

커밋(이 브랜치, `worktree-agent-ab462ece6a999db70` — 오케스트레이터가 push/병합):

- `358f3373` docs: merge SPEC-LDBEAT-001 t577 plan revision
- `d8b9b0f1` wip(t577): M10 step 1 (중간 커밋)
- `9d2803d6` feat(SPEC-LDBEAT-001): 승인 시점을 편집에서 「⇪ 콘솔에 반영」으로 이동 — REQ-015(h-1~h-6)
- `d827ca4e` feat(SPEC-LDBEAT-001): 승인 대기 UI 배지 + 세션 레벨 AC-016(v-1)~(v-5) 시험

## 6. 안 잰 것 (Gaps)

- **실기 콘솔 접촉 0건** — 이 카드는 `beat_grid_apply`의 기존 승인=송신
  경로(이미 M4/t563/t572가 실기로 검증한 부분)를 재사용할 뿐, evidence 기록
  로직 자체는 FakeConsole로만 쟀다. 실제 "⇪ 콘솔에 반영" 승인 카드가 보여주는
  문구가 실제 운영 UI(브라우저)에서 어떤 모양으로 렌더되는지는 수동 캡처하지
  않았다 — `ApprovalCard.tsx`가 `risk_reasons`를 그대로 렌더한다는 것은 소스
  읽기로만 확인했다(§3 인용).
- **`BeatGridTopBar.tsx` 승인 다이얼로그 자체의 변경 없음** — plan.md M10
  4단계가 "연동 확인"을 요구했는데, 조사 결과 feature-specific 와이어링이
  필요 없었다(범용 `ApprovalCard.tsx`가 이미 `risk_reasons`를 보여준다) — 이
  판단이 맞는지는 다음 sync-phase 또는 수동 UI 확인에서 재확인 권고.
  `BeatGridTopBar.test.tsx`는 이 카드의 변경과 무관하게 전부 그대로 통과했다
  (16/16, 회귀 없음).
- **(v-4)의 "0 송신"은 통합 레벨로 재현하지 않았다** — `apply_pending_approval`
  단위 시험으로 "카드 밖 번호에 evidence가 안 적힌다"만 확인했고, 실제
  `beat_grid_apply` 세션 호출 안에서 "카드 구성 시점과 반영 시점 사이에 새
  편집이 끼어드는" 동시성 시나리오는 synchronous 단일 호출 구조상 재현 지점이
  없다(plan.md 3단계가 서술한 대로 기존 스냅샷 메커니즘이 구조적으로
  막는다) — 재현 불가능이 아니라 "재현할 중간 지점이 코드에 없다"는 것이
  이 run-phase의 관찰이다.
- **다른 lane의 동시 작업과의 충돌 여부** — `git fetch origin main` 결과
  origin/main이 이 워크트리 HEAD의 조상임을 확인했을 뿐, 이 lane 작업 동안
  다른 lane이 `server/design/beat_grid*.py`·`server/web/session.py`를 건드렸는지
  는 재확인하지 않았다(오케스트레이터가 머지 시점에 재확인 권고).

## 7. 리드 세션 검수에서 잡은 결함 1건과 수정 (카드 t577, 오케스트레이터 직접)

- **재현(수정 전 RED)**: `uv run python -m pytest server/tests/test_apply_time_approval_t577.py -k EditDuringApprovalWait` → `2 failed`.
  - `test_number_changed_after_the_card_is_not_approved`: `AssertionError: assert '4.21' == '4.29'` — 승인 창이 떠 있는 동안 4.29 로 바꾼 번호가 승인 뒤 4.21 로 되돌아갔다.
  - `test_other_edits_made_during_the_wait_are_kept`: `StopIteration` — 그 사이 연 BACK 2마디 칸이 사라졌다.
- **원인**: `beat_grid_apply` 가 승인 뒤 카드 구성 시점의 `grid` 스냅샷에 승인을 적어 `store.latest` 로 통째로 되돌려 썼고, `apply_pending_approval` 은 칸을 (트랙, 마디)로만 찾고 값은 대조하지 않았다 — 카드에 없던 번호가 승인될 수 있었다(h-4 위반) + 대기 중 편집 소실.
- **수정**: `server/web/session.py` — 승인 뒤 **지금** 저장된 격자를 다시 읽어 그 위에 적는다. `server/design/beat_grid.py` `apply_pending_approval` — 칸의 현재 승인 대기 (필드, 값) 집합이 카드가 보여준 집합과 정확히 같을 때만 승인을 적고, 다르면 승인 대기로 남긴다.
- **수정 뒤**: 같은 파일 `9 passed`. 뮤테이션 — 값 대조 줄을 `if False:` 로 바꾸면 `1 failed, 8 passed`(바로 그 시험), 되돌리면 통과.
- **합친 트리 검증**(origin/main `a2cc872d` 병합 커밋 `66fa9f54` 위): `uv run python -m pytest server/tests/ -k "beat_grid or t577 or t573 or t579"` → `477 passed, 14869 deselected`; `ruff check` 변경 파일 → `All checks passed!`; `npx tsc --noEmit` exit 0; `npx vitest run src/components/BeatGrid.test.tsx src/components/BeatGridTopBar.test.tsx` → `168 passed`.
- **병합 충돌 1건**: `ui/src/components/BeatGrid.tsx` 배지 자리 — main(t579)의 새 「실기 미확인」 판정(`unverifiedCells`)을 쓰고, 그 옆에 「승인 대기」 배지를 유지.
- **여전히 안 잰 것**: 실기 콘솔, 브라우저에서 승인 창 문구 눈 확인.
