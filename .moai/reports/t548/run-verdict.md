# t548 M8 run-phase verdict — 앱 2단계 무빙 칸 + 칸별 근거 등급

SPEC-LDBEAT-001 M8(REQ-LDBEAT-006(vi)(vii)·(iv-2) 재교정, REQ-LDBEAT-015(g)).
콘솔 접촉 0건, 콘솔 쓰기 0건, 쇼 저장 0건 — 전부 순수 함수/데이터 변경.
cycle_type=tdd. 작업 위치: 이 agent의 격리 워크트리(브랜치
`worktree-agent-a8a08906909a82bea`, HEAD는 `WT-ldbeat-movers-run`과
75a03fb5에서 분기). 배차서가 가리킨 t548r 워크트리는 다른 레인 소유라
손대지 않았다 — 거기 있던 plan-phase 내용(spec.md/plan.md/acceptance.md의
REQ-LDBEAT-006(vi)(vii)·REQ-LDBEAT-015(g)·AC-LDBEAT-016(n)~(u))은
`git checkout WT-ldbeat-app-movers -- .moai/specs/SPEC-LDBEAT-001/{spec,plan,acceptance,progress}.md`
로 이 워크트리에 동기화했다(코드 diff 0줄, 이미 커밋된 plan 내용 가져오기).

## §A 전제 재확인

- MOVER-D(Group 12, Spiider) 2단계 무빙 실기 프로브 — **PASS**
  (`.moai/reports/t548/probe-moverd.md`(브랜치 `WT-ldbeat-app-movers`에서
  `git show`로 읽음)·`reports/t548-moverd-probe-20261011.md`(주 체크아웃,
  절대경로로 Read), 2026-10-11). 결론: Dimmer2까지 내야 켜짐·2단계 틸트
  웨이브/원은 움직임·팬 단독은 기울인 자리에서만 보임. 세 사실 모두 M8
  구현(app_movement.py의 brightness_value_commands 전수-디머 출력,
  love_attack.yaml의 MOVER-D 두 칸 채움, pan_only_vertical_base_warning)에
  반영했다.
- 감독 결정 2026-10-11 ①②(§5 열린 결정 8항 해소) — ① 팬 전용 모양 신설
  금지, 기존 `wave`에 `axes` 파라미터. ② 기준 위치 = 그 칸 자신의
  `position_preset_no`. 둘 다 구현.

## §B AC별 PASS/FAIL 매트릭스

| AC | 대상 | 상태 | 검증 수단 |
|---|---|---|---|
| AC-LDBEAT-016(n) | app_movement 구조(shape/axes/period/4칸) | PASS | `pytest server/tests/test_beat_grid_t548.py server/tests/test_app_movement_t548.py -q` |
| AC-LDBEAT-016(o) | evidence.grade(12칸, 2/2/8) | PASS | `pytest server/tests/test_beat_grid_t548.py -k TestEvidenceGradeAndApproval -q` |
| AC-LDBEAT-016(p) | evidence.approval(12칸 전수 승인 + 음성 사례) | PASS | 위와 동일 |
| AC-LDBEAT-016(q) | REQ-006(iv-2) 역할 경로(카드 t543 구현, 이미 존재) | PASS(기존 시험 재확인) | `pytest server/tests/test_beat_grid_t537.py -k "test_role_match_requires_exactly_one_track_with_that_role or test_love_attack_section_4_scene_cells_classify_to_the_yaml_layout" -v` |
| AC-LDBEAT-016(r) | phase_spread가 shape와 독립 + 암묵 매핑 부재 | PASS | `pytest server/tests/test_position_fx.py server/tests/test_app_movement_t548.py -q` |
| AC-LDBEAT-016(s) | 코드 상수 금지(장비ID·그룹·프리셋 리터럴 0건) | PASS | `pytest server/tests/test_app_movement_t548.py -k TestNoHardcodedRigOrPresetLiterals -v` |
| AC-LDBEAT-016(t) | 같은 축 배타성(양성/음성 대조) | PASS | `pytest server/tests/test_beat_grid_t548.py -k TestSameAxisExclusivity -v`, `npx vitest run src/components/BeatGrid.test.tsx -t appMovementAxisConflictWarning` |
| AC-LDBEAT-016(u) | 기준 위치 출처(P 리콜 1회·뱅크 레이블 0건·null 케이스) | PASS | `pytest server/tests/test_app_movement_t548.py -k TestAppMovementCommandsBasePositionSource -v` |
| 감독 결정④ | Pan 단독+기준 없음 경고 | PASS | `pytest server/tests/test_beat_grid_t548.py -k TestPanOnlyVerticalBaseWarning -v`, `npx vitest run src/components/BeatGrid.test.tsx -t panOnlyVerticalBaseWarning` |
| 리드 추가 지시 | Dimmer 단독 기구 → 1줄, Dimmer2 없음 | PASS | `pytest server/tests/test_app_movement_t548.py -k test_dimmer_only_fixture_emits_exactly_one_line_and_no_dimmer2 -v` |

## §C RED/GREEN 증거 (대표 발췌 — 전체 출력은 이 세션의 작업 로그 참조)

### C1. position_fx.py `wave` 일반화 (AC-016(n)(r) 기반)

명령: `uv run pytest server/tests/test_position_fx.py -k TestRelativeWaveLinesGeneralization -q`
(일반화 전 코드에, 일반화 전용 신규 시험만 적용해 RED를 쟀다 — `git stash`로
`position_fx.py`만 일시 되돌린 뒤 재실행)

RED(일반화 전):
```
ImportError: cannot import name 'relative_wave_lines' from 'server.spatial.position_fx'
```

GREEN(일반화 후, stash pop 뒤):
```
..........................................................               [100%]
58 passed in 0.05s
```

### C2. `beat_grid.py` 검증 함수 3개 (AC-016(o)(p)(t) + 감독 결정④)

명령: `uv run pytest server/tests/test_beat_grid_t548.py -q`

RED(구현 전):
```
ImportError: cannot import name 'check_app_movement_axis_conflict' from 'server.design.beat_grid'
```

RED 중간 상태(검증 로직만 구현, love_attack.yaml 채우기 전 — 29개 중
정규화·검증 로직 20개 PASS, 데이터-픽스처 9개 FAIL):
```
FAILED ...TestFourTargetCellsCarryAppMovement::test_mover_u_bar11_pan_wave_no_period
FAILED ...TestFourTargetCellsCarryAppMovement::test_mover_u_bar18_pan_wave_two_beats
FAILED ...TestFourTargetCellsCarryAppMovement::test_mover_d_bar7_tilt_wave_two_bars_phase_spread
FAILED ...TestFourTargetCellsCarryAppMovement::test_mover_d_bar22_tilt_wave_two_beats
FAILED ...TestFourTargetCellsCarryAppMovement::test_mover_u_bar11_has_no_period_invented
FAILED ...TestEvidenceGradeAndApproval::test_all_twelve_cells_carry_the_expected_grade
FAILED ...TestEvidenceGradeAndApproval::test_all_twelve_cells_carry_complete_supervisor_approval
FAILED ...TestEvidenceGradeAndApproval::test_approved_measured_cell_passes
FAILED ...TestPanOnlyVerticalBaseWarning::test_mover_u_bar11_real_cell_warns
9 failed, 20 passed in 0.13s
```

GREEN(love_attack.yaml 채운 뒤):
```
.............................                                            [100%]
29 passed in 0.12s
```

### C3. `app_movement.py` 에미터 (AC-016(u)(n)(s))

명령: `uv run pytest server/tests/test_app_movement_t548.py -q`

RED(모듈 부재):
```
ImportError: cannot import name 'app_movement' from 'server.design'
```

GREEN:
```
..........................................................               [100%]
26 passed in 0.04s
```

### C4. UI 순수 함수 4개 (AC-016(t) + 감독 결정④, 화면 표시)

명령: `cd ui && npx vitest run src/components/BeatGrid.test.tsx`

RED(함수 부재, 16개 신규 시험 FAIL / 85개 기존 시험 PASS):
```
TypeError: panOnlyVerticalBaseWarning is not a function
...
Test Files  1 failed (1)
     Tests  16 failed | 85 passed (101)
```

GREEN:
```
 ✓ src/components/BeatGrid.test.tsx (101 tests) 6ms
 Test Files  1 passed (1)
      Tests  101 passed (101)
```

## §D 최종 통합 검증 (이 세션의 마지막 실행, 종료 코드 전부 0)

```
$ uv run pytest server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py \
  server/tests/test_beat_grid_probes_t537.py server/tests/test_beat_grid_t548.py \
  server/tests/test_position_fx.py server/tests/test_position_fx_dedupe_t542.py \
  server/tests/test_app_movement_t548.py -q
........................................................................ [ 39%]
........................................................................ [ 79%]
.....................................                                    [100%]
181 passed in 1.24s
```

```
$ uv run ruff check server/design/app_movement.py server/design/beat_grid.py \
  server/spatial/position_fx.py server/tests/test_app_movement_t548.py \
  server/tests/test_beat_grid_t548.py server/tests/test_beat_grid_t537.py \
  server/tests/test_position_fx.py
All checks passed!
```

```
$ uv run ruff format --check <같은 7개 파일>
7 files already formatted
```

```
$ cd ui && npx vitest run src/components/BeatGrid.test.tsx
 Test Files  1 passed (1)
      Tests  101 passed (101)
```

```
$ cd ui && npx tsc --noEmit
(출력 없음 — 클린)
```

## §E Gaps (미검증)

- non-null 수직 판정은 범위 밖
- **non-null 수직 판정은 범위 밖(상세)** — `pan_only_vertical_base_warning`은
  `position_preset_no is None`인 경우만 경고한다. non-null 프리셋 번호가
  실제로 "수직"인지(그 프리셋이 가리키는 실제 Tilt 값)는 이 SPEC의 증거
  범위 밖(§5 항목 8 미해소분) — 구현하지 않았다. 리드 지시에 따라 범위를
  넓히지 않았다.
- MOVER-U bar 11의 `app_movement` 주기는 레이블이 말하지 않아 `period_unit`/
  `period_value` 둘 다 `None`으로 남겼다 — M9+에서 실기 프로브로 확정될 때까지
  이 칸의 명령은 `app_movement_commands`가 "period_value가 양의 정수가
  아닙니다" 사유로 거절한다(의도된 동작, 지어내지 않음).
- 이 에미터(`app_movement_commands`)가 낸 명령은 콘솔에 보내지 않았다 — 이번
  M8 run-phase 의 콘솔 쓰기는 0줄이다. (정정, 오케스트레이터: 이전 문면의
  「라이브 프로브는 리허설+전부-거절까지만」은 틀렸다. MOVER-D 실기 프로브는
  2026-10-11 리드 「실행」 뒤 콘솔에서 실행돼 Dimmer2 필요·틸트 웨이브·원·
  기울인 자리 팬 웨이브 움직임을 확인했다 — `reports/t548-moverd-probe-20261011.md`.
  그 프로브는 손으로 쓴 승인 목록이었고, 이 에미터의 출력과 바이트 대조는 하지
  않았다.)
- `app_movement_commands`가 `shape != "wave"`인 경우(sweep/flyout/circle/
  ballyhoo) 명시적으로 거절한다(추측 구현 금지) — 이 M8의 LOVE ATTACK
  데이터는 네 목표 칸 모두 `shape="wave"`뿐이라 다른 shape 경로는 실기로
  검증되지 않았다. 범위를 넓히지 않았다(plan.md M8이 요구하지 않음).
- `check_evidence_approval`은 "프리셋 번호가 있으면 (grade와 무관하게)
  approval이 완전해야 한다"는 평평한 규칙으로 구현했다(배차서 §4 Evidence/
  approval 절의 문면을 그대로 따름) — REQ-LDBEAT-015(f) 원문은 `measured`/
  `measured_other_group` 자체도 유효한 출처이므로 그 두 grade는 이론상
  `approval` 없이도 (f)를 통과할 수 있다는 해석이 가능하다. 이번 12칸은
  실제로 전부 승인까지 받았으므로 이 해석차가 현재 데이터에서는 드러나지
  않는다 — 향후 "measured인데 미승인"인 칸이 생기면 이 규칙의 엄격함을
  재확인해야 한다.
- UI 표시 네 함수(`formatAppMovementField`·`formatEvidenceField`·
  `appMovementAxisConflictWarning`·`panOnlyVerticalBaseWarning`)는 순수 함수로
  시험했다. (정정, 오케스트레이터: 구현 직후에는 네 함수 모두 정의만 있고 화면
  어디에서도 불리지 않았다 — `grep` 호출처 0건. 오케스트레이터가 칸 편집 패널
  `BeatGrid.tsx` 의 행 목록에 「앱 무빙」·「근거」·「같은 축」·「기준 위치」 네
  행으로 배선했다.) 이 저장소엔 DOM 시험대가 없어 실제 화면 렌더는 눈으로
  확인하지 않았다 — 타입 검사와 vitest 로만 확인했다.
- `brightness_value_commands`/`dimmer_attribute_names`는 이번 4개 목표
  칸(app_movement) 자체에는 쓰이지 않는다(그 칸들은 `brightness`가 미정) —
  리드 추가 지시가 요구한 Dimmer-패밀리 전수 출력은 단위시험으로만
  검증했고, LOVE ATTACK 실제 트랙에 대한 end-to-end 호출 경로(어느
  `FixtureCapability`를 넘길지 결정하는 상위 호출자)는 이 M8 범위 밖이다.

## §F 커밋

| SHA | 제목 |
|---|---|
| `67a7d936` | docs(SPEC-LDBEAT-001): M8 plan-phase 내용 run tree로 가져오기 (카드 t548) |
| `3bcc297b` | feat(SPEC-LDBEAT-001): wave를 Pan/Tilt 축 매개변수로 일반화 (카드 t548) |
| `b60394a4` | feat(SPEC-LDBEAT-001): app_movement/evidence 구조화 필드 + 검증 (카드 t548) |
| `f0b559ae` | feat(SPEC-LDBEAT-001): app_movement 셀 에미터 신설 (카드 t548) |
| `b456d8b1` | feat(SPEC-LDBEAT-001): BeatGrid UI에 app_movement/evidence 표시 + 경고 (카드 t548) |
| `b58393fa` | test(SPEC-LDBEAT-001): AC-016(r)(s) 코드 상수 금지 + phase_spread 매핑부재 시험 보강 (카드 t548) |

커밋 메시지에 "t548" 문자열이 없는 커밋 — **없음**. 전부 제목에
"(카드 t548)"을 달았다(리드 교정 반영).
