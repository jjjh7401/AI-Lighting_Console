# SPEC-COPILOT-CLASSIFYGAP-001 — 수락 기준

> 이 문서는 **검증 층**이다. 각 항목은 Given-When-Then 이고 이진 판정이 가능하다.
> 요구사항(GEARS)은 `spec.md` §E 가 든다.

---

## §D 수락 기준표

### AC-CG-001 — 네 명령이 보류된다 (REQ-CG-001)

- **Given** 확대된 폐집합 리비전이 배치된 트리에서
- **When** `classify_command(validate(c).parsed, load_ruleset())` 을
  `Store Sequence 210 Cue 3 /Merge`, `Store Cue 1`, `Store Group 3`,
  `Store Timecode 9` 각각에 대해 실행하면
- **Then** 네 결과 모두 `risky is True` 이고 `matched_entry is not None` 이다.

### AC-CG-002 — 음성 대조군: 프로그래머 트래픽에 카드가 안 뜬다 (REQ-CG-006)

이 항목이 이 SPEC 의 **핵심 실패 방지 장치**다. 안 고치는 번들에 카드를 띄우면
감독은 카드를 안 읽게 되고, 그게 진짜 쓰기를 통과시킨다.

- **Given** 확대된 폐집합 리비전이 배치된 트리에서
- **When** 아래 아홉 문장을 분류하면
  ```
  Fixture 20 ; Attribute 'Pan' At 12
  At 100
  Group 4
  Fixture 1 Thru 12
  Set Selection MAtricks 'PhaseFromX' 0
  Label Group 3 'Vocals'
  Go+ Sequence 5
  Off Fixture 11
  ChangeDestination Root
  ```
- **Then** 아홉 개 모두 `risky is False` 이고 `matched_entry is None` 이다.

> 확대 **전** 기준값은 이미 측정돼 있다 — 위 아홉 문장은 `bl_widen_min` 룰셋에서도
> 전부 `None / risky=False` 였다. 이 AC 는 그 성질이 최종 리비전에서도
> 유지되는지를 본다.

### AC-CG-003 — 흐름 단위 음성 대조군: 승인 카드 0장 (REQ-CG-006)

명령 단위 판정(AC-CG-002)만으로는 부족하다. 이 항목은 **흐름**을 본다.

- **Given** 확대된 리비전 + 실제 `SafetyGate`(승인 요청을 세는 포트)
- **When** 쇼파일을 고치지 않는 흐름 — 프로그래머 값 설정과 조회만 하는 번들 —
  을 `screen()` 에 통과시키면
- **Then** 승인 요청은 **0건**이고 `decision.cleared is True` 다.

### AC-CG-004 — 봉합과 겹쳐도 카드는 한 장 (REQ-CG-002, REQ-CG-003)

- **Given** 확대된 리비전 + 봉합 선언(`BatchRisk`)이 붙은 번들
- **When** 그 번들에 새로 블랙리스트가 된 명령이 들어 있는 상태로 `screen()` 하면
- **Then** `ApprovalRequest` 는 **정확히 1건**이고, 각 항목의 `risk_reasons` 에
  봉합 사유와 분류 사유가 **둘 다** 실려 있다.

> plan 단계에서 확대된 룰셋으로 미리 관측한 값(§D.1 증거) — 요청 1건, 항목 3개,
> 사유 병기 확인. 이 AC 는 최종 리비전에서 그 성질이 유지되는지를 본다.

### AC-CG-005 — 받침이 실제로 받친다 (REQ-CG-004)

- **Given** 확대된 리비전
- **When** `test_writegate_session_sites.py` 의 `SEAL_DEFENCE` 귀속을 재측정하면
- **Then** `seal-only` 로 판정되는 자리 수가 확대 전(**7**)보다 **적다**.

> 이 수가 줄지 않으면 확대는 안전을 하나도 안 늘린 것이다 — 비용만 낸 셈이므로
> 이 AC 는 must-pass 다.

### AC-CG-006 — 봉합은 그대로 (REQ-CG-008)

- **Given** 확대된 리비전
- **When** 열 자리 디스패치의 `BatchRisk` 선언 유무를 세면
- **Then** 확대 전과 **같은 열 자리** 전부에 선언이 남아 있다(0건 제거).

### AC-CG-007 — 동사 확대를 하지 않았다 (REQ-CG-007)

- **Given** 확대된 리비전의 `blacklist.yaml`
- **When** blacklist 항목을 읽으면
- **Then** 단독 `"Store"` 항목이 **없다**. 그리고 `Store` 동사만으로 성립하는
  평범한 대화 회차 —
  `test_web_session.py::TestHappyPath::test_korean_instruction_executes_and_reports_in_korean`
  — 가 통과한다.

### AC-CG-008 — 리비전이 문서화됐다 (REQ-CG-005)

- **Given** 확대된 `blacklist.yaml`
- **When** `version` 과 `REVISION HISTORY` 블록을 읽으면
- **Then** 버전이 4 → 5 로 올라가 있고, `v4 -> v5` 항목이 `REVISION HISTORY`
  블록 **안에** 있으며 비준 SPEC 이름(`SPEC-COPILOT-CLASSIFYGAP-001`)과 항목별
  실측 비용, 그 시점의 전체 테스트 수를 함께 적고 있다.
  `test_safety_ruleset.py` 의 3중 핀이 통과한다.

### AC-CG-009 — 전체 스위트가 초록이고 갱신이 개별 근거를 갖는다 (REQ-CG-009)

- **Given** §D.2 분류표에 따른 갱신이 끝난 트리
- **When** `uv run pytest -q server/tests` 를 실행하면
- **Then** `0 failed` 이고, 전체 수가 보고에 함께 적혀 있다. 그리고 갱신된 테스트
  **각각**에 왜 갱신이 옳은지가 주석 또는 커밋 메시지로 남아 있다.

### AC-CG-010 — 2번 종류가 0건이다 (REQ-CG-009)

- **Given** §D.2 분류표
- **When** 2번(확대가 틀렸다는 신호)으로 판정된 항목을 세면
- **Then** **0건**이다. 1건이라도 남아 있으면 이 SPEC 은 수락되지 않는다 —
  술어를 좁히거나 그 자리를 봉합으로 처리한 뒤 다시 측정한다.

---

## §D.1 증거 (plan 단계에서 관측된 것)

기준선 — `uv run pytest -q server/tests`:

```
12002 passed, 19 skipped, 1 warning in 202.48s (0:03:22)
exit=0
```

항목별 확대 비용(같은 명령, 넓힌 룰셋):

| 넣은 항목 | 실패 | 통과 |
|---|---|---|
| `Store Timecode` | 6 | 12000 |
| `Store Group` | 13 | 11993 |
| `Store Sequence` | 33 | 11973 |
| `Store Cue` | 62 | 11944 |
| 네 항목 전부 | 71 (고유 54) | 11947 |

대조군(원본 바이트 동일 복사, 다른 경로):

```
1 failed, 12001 passed, 19 skipped
FAILED test_safety_ruleset.py::TestShippedRuleset::test_default_path_is_the_ssot_yaml_under_server_safety
```

봉합 + 확대 동시 투입 게이트 프로브:

```
sealed + widened -> approval requests = 1
items in that single request = 3
   Store Sequence 210 Cue 3 /Merge | ('SEAL-REASON', "…entry 'Store Sequence'")
   Store Timecode 9               | ('SEAL-REASON', "…entry 'Store Timecode'")
   Fixture 20 ; Attribute 'Pan' At 12 | ('SEAL-REASON',)
```

산출물: `reports/classifygap-t299/` (추적됨). 각 회차 파일의 `FAILED` 줄 수가
위 표의 숫자와 일치한다 — 표가 스스로 검산된다.

---

## §D.2 깨지는 테스트 전수 분류 (고유 함수 54 / 파라미터 71)

종류: **1** 갱신 대상 · **2** 확대가 틀렸다는 신호 · **3** 계측 인공물.

### 종류 1 — 갱신 대상 (44)

#### 폐집합·눈감음 핀 (이 SPEC 이 뒤집는 대상)

| 테스트 | 파라미터 | 근거 |
|---|---|---|
| `test_writegate_merge_gap.py::test_a_sequence_cue_write_raises_no_approval_card_today` | 3 | 이름 그대로 **오늘의 눈감음**을 고정한 핀. 이 SPEC 의 목적이 이것을 뒤집는 것이다 |
| `test_writegate_merge_gap.py::test_the_blacklist_carries_no_entry_that_could_match_a_sequence_store` | 1 | `"Store Sequence" not in blacklist` 단언. BULKGATE 는 이를 **지켰고**, 이 SPEC 이 근거와 함께 푼다 |
| `test_writegate_merge_gap.py::test_the_same_write_with_overwrite_does_raise_a_card` | 1 | `/Overwrite` 는 카드, `/Merge` 는 무카드 — 이 비대칭이 사라지는 것이 곧 수정이다 |
| `test_safety_ruleset.py::test_blacklist_is_exactly_the_shipped_closed_set` | 1 | 폐집합 핀. 모든 비준 리비전이 갱신하도록 설계됐다 |
| `test_showfile_replacement_gate.py::TestNoCollateralWidening::test_classification_did_not_move` | 2 | RESTORE-001 의 부수피해 0 핀. 이 SPEC 은 분류를 **의도적으로** 움직이므로 재비준 |
| `test_showfile_replacement_gate.py::TestNonVacuity::test_the_probe_can_report_safe` | 1 | 위 핀의 비공허성 짝 |
| `test_writegate.py::TestScopeIsHeldExactly::test_the_form_stays_non_risky` | 2 | `UNCHANGED_SAFE` 튜플. 줄마다 개별 근거 필요 |
| `test_writegate.py::TestScopeIsHeldExactly::test_the_measurement_corpus_cannot_collide_with_this_entry` | 1 | `RATIFIED_CORPUS_COLLISIONS` 재비준 |
| `test_writegate.py::TestScopeIsHeldExactly::test_the_corpus_collision_check_can_actually_fail` | 1 | 위의 비공허성 짝 |
| `test_writegate.py::TestIndirectRoutes::test_the_deploy_scan_still_passes_a_genuinely_safe_source` | 1 | 「진짜 안전한 소스」 리터럴이 `Store Group 3` — 다른 리터럴로 교체 |

#### 방어 귀속표 (재측정 전제로 설계됨)

| 테스트 | 파라미터 | 근거 |
|---|---|---|
| `test_writegate_session_sites.py::…::test_the_recorded_defence_class_still_holds` | 5 | 실패 메시지가 스스로 「`SEAL_DEFENCE` 표를 다시 재서 갱신해 주세요」라고 적는다. **AC-CG-005 의 성공 지표이기도 하다** |
| `test_writegate_session_sites.py::…::test_a_seal_only_bundle_clears_the_whole_pipeline_with_no_card` | 5 | `seal-only` 전제가 해소되는 자리에서 대상이 사라진다(스킵 조건) |
| `test_writegate_session_sites.py::…::test_a_seal_only_site_loses_every_card_without_its_declaration` | 5 | 같은 전제 |

#### 안전 리터럴 픽스처 (Store 계열을 「안전한 예」로 쓰던 배관 테스트)

| 파일 | 고유 | 파라미터 | 근거 |
|---|---|---|---|
| `test_safety_gate.py` (clearance·lock·health·responder·concurrency·unconfirmed) | 14 | 14 | 재는 축이 게이트 배관이고 Store 리터럴은 「안전한 예」로만 쓰인다. 리터럴 교체 |
| `test_safety_classify.py` (`test_plain_store_is_safe` 외) | 6 | 7 | 같은 성질. `test_store_with_quoted_overwrite_text_is_safe` 는 인용 성질을 재는데 리터럴이 `Store Cue …` 라 혼입 |
| `test_deploy_scan.py` (3) · `test_deploy_pipeline.py` (1) · `test_deploy_gate_e2e.py` (1) | 5 | 5 | `Store Group 3` 이 DEPLOY 의 정본 SAFE 리터럴. `UNCHANGED_SAFE` 주석이 이미 예고한 충돌 |
| `test_safety_expand.py` (2) · `test_safety_corpus.py` (1) | 3 | 3 | 전개 대상 본문이 Store 리터럴 |
| `test_safety_bootstrap.py` (1) · `test_safety_e2e_audit.py` (1) | 2 | 2 | 왕복·감사 완전성 테스트의 운반용 리터럴 |
| `test_bulkgate_declaration.py` (2) | 2 | 2 | 「선언 없는 안전 번들」의 리터럴이 Store 계열 |

> `test_deploy_scan.py::test_quoted_object_name_never_matches` 는 특히
> 주의해서 갱신한다: 인용된 `'Delete'` 가 안 걸리는 성질을 재는데, 확대 후
> `Store Cue` 가 **비인용부**에서 걸려 성질이 가려진다. `UNCHANGED_SAFE` 의
> `Set Selection MAtricks` 주석이 같은 함정을 이미 기록해 뒀다.

### 종류 2 — 확대가 틀렸다는 신호일 가능성 (8) — **run 단계 판정 필요**

이 여덟 개가 §plan.md §A-2·A-3 의 열린 판단이다. **일괄 갱신 금지.**

| 테스트 | 파라미터 | 왜 신호일 수 있는가 |
|---|---|---|
| `test_fx_boundary.py::…::test_a_real_fx_bundle_clears_the_real_gate_with_no_hold` | 1 | FX 번들이 `sequence 90+index` 에 저장한다. FX 만들 때마다 카드가 뜨면 감독은 카드를 안 읽게 된다. **[NEEDS CLARIFICATION: FX 번들이 쇼파일 쓰기인가]** |
| `test_seeded_song_apply.py::test_the_seeded_song_applies_end_to_end_when_the_director_names_the_sequence` | 1 | 곡 반영은 이미 봉합돼 있다. 여기서 깨지면 이 경로가 봉합 밖이라는 뜻 |
| `test_seeded_song_apply.py::test_a_colour_change_reaches_the_desk_as_a_colour_command` | 1 | 색 변경이 쇼파일 쓰기인지 프로그래머 값인지가 판정 축 |
| `test_seeded_song_apply.py::test_a_fade_change_reaches_the_desk_as_a_fade_command` | 1 | 같은 축 |
| `test_web_cue_sheet_apply.py::test_an_accepted_batch_is_asked_once_not_once_per_command` | 1 | **가장 강한 신호.** 이름 그대로 「한 번만 묻는다」를 지키는 핀이고, 이 자리는 `approval_owned_by_caller=True` 로 자기 승인 채널을 갖는다 → 감독이 카드를 두 번 볼 수 있는 유일한 경로 |
| `test_web_cue_sheet_apply.py::test_apply_sends_only_the_changed_cue_through_the_preview_gate` | 1 | 같은 자리 |
| `test_web_cue_sheet_apply.py::test_applying_twice_does_not_resend_the_same_cue` | 1 | 같은 자리 |
| `test_web_cue_sheet_apply.py::test_the_acceptance_is_written_to_the_audit_log` | 1 | 같은 자리 |

> 이 8이 t292 가 보고한 8과 **같은 집합이 아니다.** 수가 겹치는 것은 우연이고,
> t292 의 8은 `Store Sequence` 단독 확대의 당시 값(룩 생성 4 · FX 2 ·
> 씬 컴파일 1 · 룰셋 핀 1)이다.

### 종류 3 — 계측 인공물 (2)

| 테스트 | 근거 |
|---|---|
| `test_safety_ruleset.py::test_default_path_is_the_ssot_yaml_under_server_safety` | 대조군이 지목. 내 플러그인이 `DEFAULT_RULESET_PATH` 를 `server/safety/` 밖으로 옮긴 탓 |
| `test_safety_ruleset.py::test_every_shipped_revision_is_documented_in_the_file` | 스크래치 리비전 주석이 `REVISION HISTORY` 블록 밖에 있고 비준 SPEC 이름이 없다. 제대로 쓴 리비전(AC-CG-008)은 통과한다 |

---

## §D.3 품질 게이트

- `uv run ruff check` 통과
- `uv run pytest -q server/tests` → `0 failed`, 전체 수 병기
- 인터프리터는 이 트리의 것(`uv run`). 프로브 결과에는 인터프리터를 함께 적는다

## §D.4 완료 정의 (Definition of Done)

1. AC-CG-001 ~ AC-CG-010 전부 통과. **AC-CG-002 · AC-CG-003 · AC-CG-005 ·
   AC-CG-010 은 must-pass** — 하나라도 실패하면 이 SPEC 은 수락되지 않는다.
2. §D.2 의 종류 2 여덟 항목이 판정되어 0건으로 해소됐다.
3. `blacklist.yaml` v5 헤더에 항목별 비용과 그 시점 전체 수가 기록됐다.
4. 남는 구멍(`Store Page` · `Store Macro` · `Assign Sequence` ·
   `Copy Sequence`)이 후속 카드로 등재됐다.
5. 커밋 메시지가 t299 를 명시하고 `🗿 MoAI` 로 끝난다.

## §D.5 이 SPEC 이 검증하지 않는 것

- **실기 검증 없음.** 실제 콘솔에 대고 쏘지 않는다. 승인 카드가 뜨는 조건은
  전부 오프라인에서 관측된다.
- **`Store Page`·`Store Macro`·`Assign`·`Copy` 의 확대 비용 미측정.** 이
  SPEC 의 네 명령에 들지 않아 개별 측정을 하지 않았다.
- **네 항목 축소 변형의 조합 비용 미측정.** `Store Sequence` + `Store Timecode`
  만 넣는 변형은 개별 값(33·6)만 있고 동시 투입값을 재지 않았다. 겹침이 있으므로
  합으로 추정하면 틀린다.
