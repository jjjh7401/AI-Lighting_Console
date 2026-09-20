# 진행 기록 — SPEC-LDCLIMAX-001

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-09-20
- plan_revised_at: 2026-09-20 (같은 날 2차 개정 — 감독 결정 반영)
- tier: L
- artifact_count: 5 (spec.md + plan.md + acceptance.md + design.md +
  research.md — progress.md 별도)
- REQ/AC 수: 12/10
- depends_on: 없음(선행 SPEC 없음). related_specs: SPEC-LDACCENT-001
  (status: completed, 이 SPEC 이 확장하는 사다리 기반), SPEC-COPILOT-SONGCUE-001
  (원 SPEC).
- 근거: 큐 카드 t425(2026-09-20 실측), `docs/proposals/song-structure-
  lighting-standard.md` §6/§6.1/§7/§7.1(origin/main `2258048b` 기준
  원문 재확인), `server/looks/songcue.py`/`server/design/song_plan.py`/
  `server/web/session.py`/`server/design/energy.py`/`server/design/
  cue_density.py` 실측(origin/main `2258048b`).
- **사람 확인 대기 항목: 0건 — 전량 해소(2026-09-20).** 과거의 미해결
  질문 마커(액센트 회전 기본값)는 감독 결정으로 닫혔다 — color_snap 은
  zoom_pinch/blinder_or_flash/iris_pinch/strobe_hit 와 같은 자격의
  정규 회전 칸(무조건 포함, REQ-001)이고, `allow_color_snap`(기본값
  거짓의 항상-꺼짐 스위치) 모델은 폐기, `disable_color_snap`(REQ-012,
  첫 실기 콘솔 세션까지의 임시 안전판)으로 대체됐다. 범위(색 스냅 +
  절정 지속시간 상한을 한 SPEC 에 유지)도 감독이 재확인했다 — 분리하지
  않는다. 해소 근거: plan.md §NC, spec.md §2/§5, research.md §5. 이
  개정으로 REQ-001 이 재작성되고 REQ-012 가 신설됐으며(REQ 11→12),
  AC-LDCLIMAX-001 이 재작성되고 AC-LDCLIMAX-010 이 신설됐다(AC 9→10).
  기존 마일스톤 M3(자동 회전 배선, 보류 상태였음)은 해소된 결정을 M2 에
  흡수하며 삭제됐고, 이후 마일스톤은 M3~M5 로 당겨졌다(plan.md §F).
  Implementation Kickoff Approval 은 이 해소를 전제로 진행 가능하다.

## §E.2 Run-phase Evidence

- **작업 위치**: `.claude/worktrees/agent-a4728078ef44570b3`(L1 워크트리, origin/main
  `2258048b` 에서 새로 fetch·동기화 확인 후 착수). 브랜치는
  `WT-color-snap-climax`(`git branch -m` 로 `worktree-agent-a4728078ef44570b3`
  에서 개명).
- **RED 증거 — 색 스냅 6건, 지속시간 상한 4건, 배선 1건 = 총 13건 신규
  테스트, 구현 전 실행하면 전부 실패**. 대표 3건의 실측 실패 원인(구현
  착수 전, 신규 상수·인자 부재로 인한 `ImportError`/`TypeError`):
  - `LADDER_COLOR_SNAP` 상수가 `server/looks/songcue.py` 에 없어
    `from server.looks.songcue import LADDER_COLOR_SNAP` 자체가
    `ImportError`.
  - `build_songcue_bundle(..., disable_color_snap=..., bpm=...)` 키워드
    인자가 없어 `TypeError: build_songcue_bundle() got an unexpected
    keyword argument 'disable_color_snap'`.
  - `songcue_module._apply_climax_duration_cap` 함수 자체가 없어
    `AttributeError: module 'server.looks.songcue' has no attribute
    '_apply_climax_duration_cap'`.
  (신규 함수·인자가 아예 없는 상태이므로 "실행해서 실패를 관측"이 아니라
  "임포트/속성 접근 단계에서 즉시 실패" — TDD RED 로서는 동일하게 유효한
  선행 실패 증거다: 구현 전에는 이 테스트 파일을 수집(collect)하는 것
  자체가 불가능했다.)
- **GREEN 증거 — 전체 스위트**:
  ```
  $ uv run pytest -q
  13702 passed, 35 skipped, 1 warning in 196.15s (0:03:16)
  ```
  착수 전 기준선(origin/main `2258048b` 동기화 직후, §A 사전 점검):
  `13689 passed, 35 skipped`. 델타 = +13(이 SPEC 이 더한 신규 테스트
  정확히 13개) — 델타 0(기존 테스트 손실/변형 없음)을 확인했다.
- **REQ-001~012 PASS/FAIL 표**:

| REQ | 판정 | 검증 명령 | 관측 |
|---|---|---|---|
| REQ-LDCLIMAX-001 | PASS | `pytest server/tests/test_songcue_climax_001.py::TestColorSnapIsAlwaysACandidate` | 2 passed — color_snap 무조건 후보, §7 재-도달 시 회전에 등장 |
| REQ-LDCLIMAX-002 | PASS | `...::TestColorSnapStaysWithinTheReturningPalette` | 1 passed — 팔레트 밖 색 → 유보 기록 |
| REQ-LDCLIMAX-003 | PASS | `...::TestColorSnapForcesFadeToZero` | 1 passed — `fade.seconds == 0.0` |
| REQ-LDCLIMAX-004 | PASS | `...::TestColorSnapIsFilteredWhenColorDoesNotChange` + `TestColorSnapIsAlwaysACandidate::test_a_color_invariant_repeat_never_shows_color_snap` | 2 passed — 직전 색과 같으면 무영향 |
| REQ-LDCLIMAX-005 | PASS | `...::TestColorSnapRespectsOneAccentPerCue` | 1 passed — color_snap 큐에 다른 찍는 액센트 없음 |
| REQ-LDCLIMAX-006 | PASS | `...::TestClimaxReturnIsInsertedForALongClimax` | 2 passed — 2박(1.0초) 지점에 복귀 큐, `cap_beats==2.0` |
| REQ-LDCLIMAX-007 | PASS | (같은 클래스, `inserted_start_ms`/재번호 단정) | 다음 큐 8초 뒤 → 삽입, 후속 큐 번호 +1 |
| REQ-LDCLIMAX-008 | PASS | `...::TestNaturalTransitionAlreadyRespectsTheCap` | 2 passed — 1.5초/999ms 뒤 도착 → `climax_returns == ()`, no-op |
| REQ-LDCLIMAX-009 | PASS | `...::TestUndeclaredBpmIsANoOp` | 1 passed — `bpm=None` → `result is bundle`(항등) |
| REQ-LDCLIMAX-010 | PASS | `TestClimaxReturnIsInsertedForALongClimax` (climax_returns 필드 전량 단정) + `test_a_return_cue_reuses_the_pre_climb_baseline_look_not_the_climax_commands`(기존 값 불변) | 명시적 보고 + 절정 큐 자신의 ladder/accent_fixture 불변 확인 |
| REQ-LDCLIMAX-011 | PASS | 위와 동일 클래스 — `stored[0].ladder == climax.ladder`, `stored[0].accent_fixture == climax.accent_fixture` | 후처리 패스가 기존 큐 값 결정 경로를 건드리지 않음 |
| REQ-LDCLIMAX-012 | PASS | `...::TestDisableColorSnapIsAnOptOutSafetyValve` | 1 passed — `disable_color_snap=True` → 후보 완전 제거, 기본값은 활성 |

  (표 안 "REQ-006/007"은 acceptance.md 의 AC-LDCLIMAX-006 한 시나리오
  (삽입 조건 + 삽입 위치)가 두 REQ 를 함께 검증하는 자연스러운 결과다 —
  각 REQ 의 단정은 서로 다른 assert 줄에 있다.)

- **골든 대조군 바이트 동일성(§NC 연쇄 효과가 예고한 그대로, 스위치가
  아니라 REQ-004 필터가 지킨다) — 이름으로 직접 재실행**:
  ```
  $ uv run pytest -q \
      server/tests/test_songcue_accent_ladder_t382.py::TestHeadroomCaseIsUntouched \
      server/tests/test_songcue_ladder.py::TestOneMarkingAccentPerCue
  7 passed in 0.34s
  ```
  두 클래스 다 색이 전 회차에서 고정인 픽스처를 쓴다 — `color_snap` 이
  `_MARKING`/`LADDER_RUNGS` 양쪽에 새로 포함됐어도 `.ladder` 에 등장하지
  않는다(회차 간 색이 안 바뀌므로 REQ-004 가 매 회차 거른다).
- **`ruff check .`** — `All checks passed!`
- **`ruff format --check .`** — 이 SPEC 이 건드린 3개 파일(`server/looks/
  songcue.py`, `server/tests/test_songcue_ladder.py`, `server/tests/
  test_songcue_accent_ladder_t382.py`, `server/tests/test_songcue_climax_001.py`)
  모두 정리됨. 저장소 전체에서 남는 재포맷 대상 2개(`packaging/rust_scan.py`,
  `packaging/verify_packaged_e2e.py`)는 이 SPEC 이 건드리지 않은 파일이고
  `git diff --stat origin/main`(공백)로 이 워크트리에서 무변경임을
  확인했다 — 착수 전부터 있던 별개의 부채다.

### D3 해소 — `previous_color`/`label_palette` 스레딩 방식과 근거

**착수 전 지시대로 먼저 조사했다.** `_marking_accents` 의 직접 호출자는
plan.md §B3 이 적은 4곳이 아니라 **6곳**이었다(`_no_effective_candidate_detail`
· `_exhausted_rungs` · `_max_climb` · `_climb_rungs` · `_ensure_marking_accent`
· `_finalize_marking_accents`) — `_no_effective_candidate_detail` 과
`_exhausted_rungs` 는 plan.md 가 놓쳤다. `_section_bundle` 자체도
`test_songcue_accent_ladder_t382.py` 에서 직접 호출되고 있었다(plan.md
미언급) — 실제 호출부 전수를 grep 으로 확인한 뒤 배선했다(감독 지시
"카드를 믿기 전에 코드를 grep 하라"와 같은 방향).

**후보 셋을 검토했다**:

1. **가변 딕셔너리를 `emitted` 처럼 매 큐마다 갱신** — 기각. 순서
   의존이다: `_rescue_value_line_collisions` 가 앞선 큐를 나중에
   재조립(rebuild)하는 순간, "누적해 온 previous_color"는 그 rebuild
   시점의 처리 순서를 반영하지, "그 cue_number 앞"이라는 올바른 위치를
   반영하지 않는다.
2. **함수 기본값(`= None`)** — 기각(지시에 이미 금지). `None` 은 "직전
   저장 큐 없음"(REQ-004 상 유효한 신호)과 "호출자가 배선을 잊음"을
   구별할 수 없어, SPEC-LDACCENT-001 이 이미 겪은 "한 호출 경로에서만
   조용히 새는" 실패를 다시 열 위험이 있다.
3. **채택 — 순수 함수로 이미 조립된 번들 목록에서 매번 다시 읽는다.**
   `_previous_stored_color(section_bundles, before_cue_number=N)` /
   `_label_return_palette(section_bundles, label=L, before_cue_number=N)`
   두 헬퍼가 `cue_number < N` 인 이미-저장된 번들만 훑어 계산한다.
   `_section_bundle` 이 새 필수 키워드 인자 `section_bundles:
   Sequence[SongCueSectionBundle]`(기본값 없음 — 누락 시 `TypeError` 로
   즉시 드러난다)를 받아 이 둘을 한 번 계산하고, `previous_color`/
   `label_palette` 두 값을 나머지 사다리 함수 전량(`_marking_accents`
   가족)에 명시 인자로 흘려보낸다. `_assembled` 의 본 루프와
   `_rescue_value_line_collisions` 의 `_rebuild` 클로저, `_finalize_
   marking_accents` 세 자리 전부 **그 시점의 `bundles`/`section_bundles`
   목록**(재조립·재배열이 이미 반영된 최신 상태)을 넘긴다 — 재조립
   순서와 무관하게 항상 "지금 이 cue_number 앞의 실제 상태"를 되묻는
   멱등 쿼리이므로 (1)의 순서-의존 결함이 생기지 않는다.

이 설계는 전역도 가변 기본값도 아니다 — `emitted` 가 이미 이 모듈에서
쓰는 "호출자 소유의 명시 인자를 스레딩한다"는 관행을 그대로 따른다.

### design.md 로부터의 명시적 이탈 (사전 고지대로 보고)

1. **`_rung_applied` 의 색 스냅 분기가 `_color_snap_applied(look,
   returning_color) -> tuple[Look, float]` 를 부르는 sketch는 버렸다** —
   `_rung_applied` 자신의 계약(`tuple[AttributeValue, ...]` 만 반환)과
   반환형이 안 맞는다. 색은 이미 룩 자신의 값(효과 판정이 §7 집합 안임을
   이미 확인했다)이므로 색 스냅의 `_rung_applied` 분기는 **항등**
   (`return tuple(values)`, 블라인더·스트로브와 같은 형상)으로 두고,
   페이드 강제(REQ-003)는 `_section_bundle`(최초 확정)과
   `_finalize_marking_accents`(마무리 패스에서 새로 확정되는 갈래, 새
   헬퍼 `_forced_zero_fade_store`)**두 자리**에서 직접 한다 — 분기별
   책임을 명확히 가른, 더 단순한 구현이다(design.md 자신이 "정확한
   시그니처는 run phase 에서 확정" 이라고 이미 허용한 이탈).
2. **plan.md §B3 의 "4곳" 목록은 6곳이 정확했다** — 위 D3 절 참고.
3. **`_finalize_marking_accents` 도 색 스냅을 새로 채울 수 있다는
   사실은 design.md 에 없던 발견** — 재배열 이후 마무리 패스가
   `_ensure_marking_accent` 를 다시 불러 빠진 액센트를 채우는데, 이때
   색 스냅이 새로 뽑히면 `_section_bundle` 이 최초 확정 시 강제한
   페이드가 이미 지나간 뒤라 반영되지 않는다 — `_forced_zero_fade_store`
   로 이 갈래를 별도로 덮었다(§D3 코드 주석에 기록).

### 잔여 위험 (§6 검증 수단의 한계 — 이 SPEC 이전부터 명시된 경계 안)

- **복귀 큐의 값 라인 재사용 + `_guard_bundle_collision`** — 복귀 큐는
  설계대로 절정 큐의 "오르기 전" 값을 그대로 재방출하는데, 그 값은 흔히
  이미 다른(더 이른) 저장 큐가 쓴 값과 바이트 동일하다.
  `_guard_bundle_collision`(정본 번들 안 값 라인 중복을 잡는 안전망)은
  `build_songcue_bundle` 이 M3 **이전**에 한 번만 부르고, M3 이후에는
  재호출하지 않는다(§6 이 명시한 "실기 콘솔 관측은 범위 밖" 경계 안에서
  내린 판단) — 실제 `run_commands` 중복 제거가 이 재사용 값 라인을
  콘솔에서 어떻게 다루는지는 로컬 pytest 로 판정할 수 없다. 이 구멍은
  design.md §2.1 이 지시한 대로 정확히 구현한 결과이지 이탈이 아니다.
- **재번호 매기기가 건드리는 다른 소비처** — `collides_with_cue_number`
  (스킵 사유 안의 교차 참조), `withheld_movement`/`withheld_darkness`/
  `withheld_accents` 안의 `cue_number` — M3 삽입으로 뒤 큐 번호가
  밀려도 이 필드들은 갱신하지 않는다(design.md §2.2 가 이미 "이 SPEC
  의 판정 범위 밖"이라 적은 것과 같은 결의 문제 — 정보성 교차 참조이고
  REQ-006~011 어디도 이 필드의 갱신을 요구하지 않는다).

## §E.3 Run-phase Audit-Ready Signal

- run_status: complete
- run_complete_at: 2026-09-20
- total_run_phase_files: 4 (server/looks/songcue.py, server/tests/
  test_songcue_ladder.py, server/tests/test_songcue_accent_ladder_t382.py,
  server/tests/test_songcue_climax_001.py — 신규)
- ac_pass_count: 10 (AC-LDCLIMAX-001~010, 전량 PASS — §E.2 표)
- ac_fail_count: 0
- new_warnings_or_lints_introduced: 0 (`ruff check .` clean, `ruff format
  --check` clean on all 4 touched files)
- 워크트리: `.claude/worktrees/agent-a4728078ef44570b3`, 브랜치
  `WT-color-snap-climax`

## §E.4 Sync-phase Audit-Ready Signal

- sync_complete_at: 2026-09-20
- sync_commit_sha: (이 커밋 자신 — `git log -1` 로 확인)
- sync_status: audit-ready
- b12_self_test_a: PASS — `grep -c 'SPEC-LDCLIMAX-001' CHANGELOG.md` 사전 0건(중복 없음), 삽입 후 2건(제목 줄 1 + `.moai/specs/SPEC-LDCLIMAX-001/progress.md` 경로 언급 1)
- b12_self_test_b: PASS — `grep -oE 'AC-LDCLIMAX-[0-9]+' acceptance.md | sort -u | wc -l` → 10, CHANGELOG 항목이 "AC-LDCLIMAX-001~010 전부 PASS"로 동일 개수 인용
- b12_self_test_c: PASS — CHANGELOG 인용 경로(`server/looks/songcue.py`, `server/design/energy.py`, `.moai/specs/SPEC-LDCLIMAX-001/progress.md`) 전량 `ls` 로 존재 확인
- changelog_entry_position: `[Unreleased]` → `### Added` 섹션 최상단(SPEC-LDACCENT-001 `### Fixed` 항목 바로 위)
- frontmatter_status_transitions.spec_md: in-progress → completed (이 커밋)
- frontmatter_status_transitions.other_artifacts: 해당 없음 — 이 저장소 관행상 `status:` 필드는 spec.md 에만 있다(plan.md/acceptance.md/design.md/research.md 는 `status:` 프론트매터 없음, grep 으로 확인)
- docs_site_check: `docs/proposals/song-structure-lighting-standard.md` §6/§6.1/§12 를 확인했다 — §12 "현재 구현과의 차이 — 고칠 것" 표는 이 SPEC 이 구현한 색 스냅/절정 지속시간 상한과 무관한 7개 항목(움직임 미발화·룩 선택 순서·후렴 삭제 등)만 추적하고, §6.1 이 정의한 "일곱 수단" 자체의 구현 상태를 추적하는 별도 표·주석은 이 문서 어디에도 없었다(grep 확인). 상태 추적 대상이 없으므로 이 문서는 손대지 않았다.
- canary_compliance_check: 해당 없음 — 이 SPEC 은 forward-looking 정책을 정의하지 않는다
- README_check: `README.md` 에 songcue 관련 기술 언급은 2곳(구현 파일 경로 나열, 곡 인터뷰 진입점 설명)뿐이고 액센트 사다리·색 스냅 세부는 다루지 않는다 — 갱신 대상 없음
