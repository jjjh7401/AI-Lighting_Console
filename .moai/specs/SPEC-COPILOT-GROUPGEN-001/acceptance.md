# SPEC-COPILOT-GROUPGEN-001 — 수용 기준 (acceptance)

## HISTORY

| version | date | 변경 |
|---|---|---|
| 0.2.0 | 2026-08-04 | M0 라이브 실측(`progress.md` §E.2) + 게이트 A 정책 (c) 채택 반영. AC-023을 GO=`SKIP: CONDITION_NOT_MET`(도달 불가) / NEGATIVE=정책 (c) 4층 검증으로 재작성. AC-022 판정 근거를 모달/비결정 실측으로 갱신. AC-031(GO/게이트 B)·AC-032(NEGATIVE-강화/게이트 C) 상태를 M0 판정으로 갱신. §F 뮤테이션 필수 목록에 (c) ③ 고지 필드 검증을 반영(5→6항목, plan.md와의 개수 정합 명시) |
| 0.1.2 | 2026-08-04 | plan-audit MAJOR-2 반영(AC-037 신설). 최초 버전 |

status: v0.2.0, run-phase M0 완료 반영(문서 전용 개정 — 코드 diff 0). `AC-GROUPGEN-001`~`030`을
`REQ-GROUPGEN-001`~`030`에 1:1 대응시키고, 게이트 분기·회귀·경계 판정용으로
`AC-GROUPGEN-031`~`035`를 추가한다(계약 §5 — 추가분은 031부터).
**`AC-GROUPGEN-036`은 `REQ-GROUPGEN-031`/`031a`/`031b`(**툴 계층 승인 강제** — v0.3.0 개정, `server/safety/**` byte-diff 0)에 대응한다** —
REQ 신규 번호와 AC 추가 번호가 독립적으로 031을 소진해 커버리지 공백이 생겼던 것을 coordinator가
plan-phase 감사에서 잡아 메웠다. **REQ 031 ↔ AC 036이며 번호가 일치하지 않는다는 점에 주의할 것.**
**`AC-GROUPGEN-037`(임의 작명 금지 뮤테이션)** 은 plan-audit MAJOR-2로 추가됐다 —
`plan.md` §B M5가 요구한 뮤테이션 5항목 중 "임의 작명 금지"가 정적 grep만 갖고 있어
뮤테이션 대상이 없던 결함을 닫는다. REQ-015~019에 걸치는 횡단 AC다.
검증 천장(spec.md §C.1)을 넘는 AC는 만들지 않는다: 그룹 멤버십이 의도한 픽스처인가(게이트 A GO 조건부) ·
종류 축의 이종 리그 거동(합성 golden 필수) · 그룹이 연출에서 "맞게" 동작하는가(사람 관측만)는
**LIVE** 또는 **SKIP: CONDITION_NOT_MET**으로 표기하며 기계 검증 AC를 달지 않는다.

## §A. 완료 정의 (Definition of Done)

1. AC-GROUPGEN-001~009 · 013~022 · 024~026 · 028~030 · 033~037 — 전부 기계 검증(pytest/grep) 그린
   (023·031·032는 LIVE — 아래 4항; 023의 NEGATIVE 열은 M3 구현 후 pytest 그린으로 확정).
2. AC-GROUPGEN-010~012 · 027 — `[DESCOPED-v1]`로 표기되고 §D의 복원 조건이 문서화됨(코드 검증 대상 아님).
3. AC-GROUPGEN-014 — `[Optional]`. 제안 UX가 존재하면 그린, 존재하지 않으면 REQ-014가 애초에
   `[Optional]`이므로 미구현이 SPEC 실패가 아님(design.md가 채택 여부를 확정).
4. M0 라이브 프로브(AC-GROUPGEN-023 · 029 · 031 · 032)는 **LIVE** 항목이며 게이트 A/B/C의 GO/NEGATIVE
   양 분기 서술을 모두 갖는다. **M0 완료(v0.2.0)**: AC-023 GO=`SKIP: CONDITION_NOT_MET`(도달 불가
   확정) · AC-031 GO 확정(PASS) · AC-032 NEGATIVE-강화로 기록됨(§B). 미프로브 상태의 AC는
   `SKIP: CONDITION_NOT_MET` 행을 받는다(REQ-029).
5. 신규 런타임 의존성 0(AC-GROUPGEN-035 회귀 스위프에 포함).
6. `server/spatial/topology.py` transport·게이트 import 0(AC-GROUPGEN-006) + PRESERVE 대상 무변경
   (AC-GROUPGEN-005 · 033).

## §B. 게이트 분기 규율 (계약 §3 — 모든 AC 공통)

| 게이트 | GO 분기 AC | NEGATIVE 분기 AC |
|---|---|---|
| A. 멤버십 판독 채널 | **`SKIP: CONDITION_NOT_MET`(v0.2.0 확정, M0 §E.2.8 — 도달 불가 분기)** | AC-GROUPGEN-023 (정책 (c) 4층 검증 — §10) |
| B. `Store Group <n>` 생성 | AC-GROUPGEN-031 (GO 행 — **PASS/GO 확정**, M0 §E.2.3) | AC-GROUPGEN-031 (NEGATIVE 행 — SPEC 전체 중단, 미발동) |
| C. 점유 슬롯 덮어쓰기 | AC-GROUPGEN-032 (GO 행 — 차단 규칙 확정) | AC-GROUPGEN-032 (NEGATIVE 행 — **NEGATIVE-강화로 기록됨**, M0 §E.2.4 — 차단이 더욱 절대적, 강화이지 실패 아님) |
| D. 절단 시 슬롯 안전 | AC-GROUPGEN-021 (거부, 분기 없음) | — |

`ok:true`는 증거로 쓰지 않는다 — GO 판정은 전부 **재조회**로 증명한다(REQ-023 · 계약 §6.1).

## §C. AC 표 — REQ 1:1 대응

| AC | 대응 REQ | 검증 수단 | 판정 기준 |
|---|---|---|---|
| **AC-GROUPGEN-001** | REQ-001 | `pytest server/tests/test_topology.py::test_classify_returns_all_six_topology_tokens` — golden 6종(1×N 바 · 3×10 그리드 · 2겹 동심원 · 좌우 2분할 · 3층 수직 · x=0 대칭쌍) 각각을 `topology.classify()`에 입력 | 각 golden이 `{depth_rows, lateral_split, concentric, vertical_levels, grid, bilateral_pairs}` 중 대응 토큰을 정확히 반환. `import server.bridge`·`import pythonosc`가 `topology.py` 상단에 없음을 `grep -c "^import\|^from" server/spatial/topology.py \| grep -c "bridge\|osc"` → `0`으로 동반 확인 |
| **AC-GROUPGEN-002** | REQ-002 | `pytest server/tests/test_topology.py::test_classify_is_deterministic` — 동일 golden을 10회 반복 호출 | 10회 출력이 전부 동일(해시 비교). 동률·모호 케이스는 임의 선택이 아니라 명시 신호(`ambiguous: true` 필드)로 표현됨을 별도 assert |
| **AC-GROUPGEN-003** | REQ-003 | `pytest server/tests/test_topology.py::test_concentric_and_grid_are_structurally_distinct` — **비공허성 뮤테이션**: `depth_rows` 검출기만 남기고 나머지를 스텁 처리한 분류기를 별도로 구성해 2겹 동심원 golden에 태우면 **반드시 실패**해야 함(`rows=9` 오독 재현 금지 회귀) | (a) 실제 분류기는 2겹 동심원 golden → `concentric`, 3×10 그리드 golden → `grid`를 서로 다른 토큰으로 반환. (b) "항상 `depth_rows`를 답하는" 스텁 분류기를 같은 golden 세트에 태우면 이 테스트가 RED가 됨(즉 실제 분류기가 신호를 갖고 있음을 뮤테이션으로 증명) |
| **AC-GROUPGEN-004** | REQ-004 | `pytest server/tests/test_topology.py::test_ambiguous_arrangement_returns_none_with_low_confidence` — 불규칙/전대 동일좌표 golden 입력 | 반환 위상이 `None`이고 `low_confidence: true`. 위상을 조용히 단정(임의 토큰 반환)하면 FAIL |
| **AC-GROUPGEN-005** | REQ-005 | `git diff --stat -- server/spatial/rows.py server/spatial/sorting.py server/spatial/presets.py server/spatial/choreography.py` → 빈 출력 **AND** `pytest server/tests/test_spatial_rows.py server/tests/test_spatial_sorting.py server/tests/test_spatial_presets.py server/tests/test_spatial_choreography.py -q`(SPATIAL 기존 스위트, 파일명은 실제 저장소 명칭 기준) | diff 0줄 **AND** SPATIAL 전량 무수정 PASS(신규 실패 0) |
| **AC-GROUPGEN-006** | REQ-006 | `pytest server/tests/test_architecture.py -q`(전역 스캔, 예외 명단 추가 없이 자동 포섭) | 그린. `grep -rn "server\.bridge\|pythonosc\|server\.safety" server/spatial/topology.py` → 매치 0(경계 grep 병행 확인) |
| **AC-GROUPGEN-007** | REQ-007 | `git diff main -- pyproject.toml requirements*.txt package.json`(또는 저장소의 의존성 선언 파일) → 빈 출력 **AND** `grep -n "^import\|^from" server/spatial/topology.py` 육안 확인(표준 `math`/`typing` 외 없음) | 신규 의존성 선언 0줄. import 대상이 표준 라이브러리 + 저장소 내부 모듈뿐 |
| **AC-GROUPGEN-008** | REQ-008 | `pytest server/tests/test_fixture_type_lookup.py::test_two_hop_lookup_returns_manufacturer_and_name` — `fixturetype`→`Patch/FixtureTypes/<n>`→`name`/`ShortName`/`Manufacturer` 2-hop을 실측값(`'FixtureType 1'`·`'RMMXSm1'`·`'Robe'`)으로 고정한 fixture로 검증 | 반환 구조체가 실측 3개 필드를 정확히 채움. 2-hop 중 1-hop만 밟는 회귀가 있으면 FAIL |
| **AC-GROUPGEN-009** | REQ-009 | `pytest server/tests/test_fixture_type_lookup.py::test_manufacturer_and_typename_use_raw_structured_fields` — 반환값과 fixture 원본 문자열을 바이트 단위 비교 | 문자열 가공(대소문자 변환·트림·치환 등) 0건 — 원본과 완전 일치 |
| **AC-GROUPGEN-010** | REQ-010 | **[DESCOPED-v1]** — 코드 검증 대상 아님 | §D 참조. 복원 조건: 별도 SPEC이 GDTF `Categories` 대체 근거(합성 이종 리그 golden 확보)를 마련할 때 |
| **AC-GROUPGEN-011** | REQ-011 | **[DESCOPED-v1]** — REQ-010에 종속, 동반 이관 | §D 참조. REQ-010 복원과 동시에만 복원 가능 |
| **AC-GROUPGEN-012** | REQ-012 | **[DESCOPED-v1]** — REQ-010(카테고리 판정)이 없으면 `Blinder` 식별 수단 자체가 없다 | §D 참조. **선결 조건: REQ-010 복원.** REQ-012만 단독 복원 불가(카테고리 축 부재 시 Blinder를 구별할 근거 자체가 없음을 design.md/§D가 명시) |
| **AC-GROUPGEN-013** | REQ-013 | `grep -n '"Left"\|"Right"' server/spatial/naming.py` → 매치가 전부 `Stage Left`/`Stage Right`/`Stage Centerline` 같은 접두 결합 문자열 내부에만 존재(맨 `Left`/`Right` 리터럴 부재) | 폐쇄 어휘 상수 전수 조사에서 기준 없는 `Left`/`Right` 단독 토큰 0건 |
| **AC-GROUPGEN-014** | REQ-014 | **[Optional]** `pytest server/tests/test_naming_clusters.py::test_name_cluster_proposal_excludes_default_pattern`(design.md가 채택 시) — `ShortName + " " + n` 자동 작명 패턴은 클러스터 제안에서 제외됨 | 채택 시: 제안 목록에 `ShortName+n` 패턴 클러스터가 나타나지 않음. 미채택 시: 이 AC는 `SKIP: CONDITION_NOT_MET`(design.md가 UX 비채택을 명시한 경우) |
| **AC-GROUPGEN-015** | REQ-015 | `grep -n "Downstage\|Upstage\|Center\b" server/spatial/naming.py` 존재 **AND** `grep -n '"Front"\|"Back"' server/spatial/naming.py` → 매치 0 | 깊이 축 어휘가 `Downstage`/`Center`/`Upstage`뿐이고 `Front`/`Back` 리터럴이 명명 상수에 부재 |
| **AC-GROUPGEN-016** | REQ-016 | AC-GROUPGEN-013과 동일 grep 재사용 + `pytest server/tests/test_naming.py::test_lateral_names_carry_stage_reference_frame` | 좌우 어휘가 항상 `Stage `접두를 동반(`Stage Left`/`Stage Right`가 아니라 계약 §5 폐쇄 어휘 `Stage Right`/`Stage Left`/`Stage Centerline` 정확히 사용) |
| **AC-GROUPGEN-017** | REQ-017 | `pytest server/tests/test_naming.py::test_electric_fallback_orders_downstage_to_upstage` — 4+ 폭 깊이 golden에서 `Electric 1..N` 생성 후 좌표 y값과 번호 순서 비교 | `Electric 1`이 가장 downstage(가장 작은/큰 y, 좌표계 정의에 따름), `Electric N`이 가장 upstage. 문서(design.md 또는 naming.py 독스트링)에 방향 규칙 명시 |
| **AC-GROUPGEN-018** | REQ-018 | `grep -c '^"GEO ' server/spatial/naming.py`(또는 상수 정의부 전수 조사) | 자동 생성 그룹 이름 전부가 `"GEO "`로 시작. 접두 없는 그룹명 생성 코드경로 0건 |
| **AC-GROUPGEN-019** | REQ-019 | `grep -inE "front light|backlight|sidelight|key|fill|wash|special" server/spatial/naming.py` → 매치 0(주석/문서 설명 제외, 상수 리터럴만 대상) | 기능/시스템 어휘가 명명 상수에 부재 |
| **AC-GROUPGEN-020** | REQ-020 | `pytest server/tests/test_group_write.py::test_slot_selected_from_requeried_pool_not_counted` — 실측 비연속 풀(`1·11·12·13·15`)을 모킹해 다음 슬롯이 "카운트"가 아니라 재조회 결과에서 도출됨을 검증(`_select_cue_number` 패턴 재사용 여부를 코드 경로로 확인) | 슬롯 후보가 재조회한 빈 슬롯 집합(`2~10·14·16+`)에서만 선택됨. 순번 카운팅 코드(예: `max(pool)+1`) 발견 시 FAIL |
| **AC-GROUPGEN-021** | REQ-021 (게이트 D) | `pytest server/tests/test_group_write.py::test_truncated_pool_refuses_slot_allocation` — **뮤테이션 필수**: 절단 거부 가드를 제거하면 이 테스트가 반드시 RED | 절단된 풀(`truncated: true`)에서 슬롯 할당 시도 → `SceneCompilationError` 계열 거부. 가드 제거 뮤테이션 시 테스트 RED(가드가 실제로 걸려 있음을 증명) |
| **AC-GROUPGEN-022** | REQ-022 | `pytest server/tests/test_group_write.py::test_occupied_slot_write_is_statically_blocked` — **뮤테이션 필수**: 점유 슬롯 정적 차단 코드를 제거하면 이 테스트가 반드시 RED. **판정 근거(v0.2.0 갱신, M0 §E.2.4 실측)**: 당초 "조용한 덮어쓰기" 가설이 아니라, 콘솔이 **GUI 확인 다이얼로그**를 띄우고 무인이면 `ok:false`/사람이 OK를 누르면 덮이는 **비결정적** 거동이 실측 확정됐다 — 정적 차단이 없으면 라이브 공연 중 무인 발화가 콘솔을 모달로 블로킹할 수 있다(§C.3 항목 9) | 슬롯 `1`·`11`·`12`·`13`·`15`(실측 점유) 대상 기록 시도 → 사전 차단(콘솔 송신 이전에 거부, 다이얼로그 자체를 띄우지 않음). 차단 로직 제거 뮤테이션 시 테스트 RED |
| **AC-GROUPGEN-023** | REQ-023 (게이트 A) | **v0.2.0 재작성 — M0 §E.2.8 확정 반영**. **GO 열: `SKIP: CONDITION_NOT_MET`**(도달 불가 분기 — MA3가 멤버십을 오브젝트·속성 표면에 미노출함이 증명됐다. 접근자 경로 `COUNT`가 실사용 그룹 4개 전부 `0`, 같은 배치 날조 대조군은 `ok:false`이므로 그 `0`은 실제 판독값이다. GO 분기 코드는 작성하지 않는다). **NEGATIVE 열: 정책 (c) 4층 검증**(design.md §10) — ① **안전**: `pytest server/tests/test_group_write.py::test_occupied_slot_write_is_statically_blocked`(AC-022 재사용) + `test_truncated_pool_refuses_slot_allocation`(AC-021 재사용) + AC-036(승인 카드 경유) 전부 그린. ② **자동 검증**: `pytest server/tests/test_group_write.py::test_slot_exists_verified_via_requery`(슬롯 존재 `state` 재조회) + `test_group_name_verified_via_requery`(**이름** `prop NAME` 재조회 — `"GroupgenProbe"` 실증 패턴 재현) + `test_spoken_slots_equal_measured_empty_slots`(AC-025 재사용, 발화 슬롯==실측 빈 슬롯). ③ **정직한 고지**: `pytest server/tests/test_group_write.py::test_return_payload_declares_membership_unverified` — **뮤테이션 필수**: 반환 구조체의 `unverified` 필드(예: `unverified: ("membership",)`)를 채우는 코드를 제거하면 이 테스트가 반드시 RED(구조적 필드이지 docstring이 아님을 증명). ④ **사람 확인 경로**: `pytest server/tests/test_group_write.py::test_return_includes_group_n_confirmation_command` — 반환값에 `Group <n>` 1줄 확인 커맨드가 실림 | GO 열은 코드 검증 대상이 아니다(`SKIP: CONDITION_NOT_MET` — REQ-029 규율). NEGATIVE 열은 ①②③④ 전부 충족해야 PASS. **`ok:true`는 멤버십 검증의 증거로 쓰지 않는다** — ②는 슬롯 존재·이름의 재조회 증거이지 멤버십의 증거가 아니며, 멤버십은 ③에서 **검증하지 않았다고 명시**한다(침묵·`ok:true` 대체 금지). ③이 없으면 이 AC는 FAIL |
| **AC-GROUPGEN-024** | REQ-024 (정정, v0.3.0 W6) | **쓰기 경로**: `pytest server/tests/test_groupgen_write.py::test_build_group_write_plan_proceeds_on_truncated_fixture_list`(라이브 형상 회귀 — `childCount 39`·반환 18·`truncated:true`에서 명시 `fids` 쓰기가 거부되지 않고 진행) + `test_groupgen_write.py::test_build_group_write_plan_structurally_flags_fixture_list_truncation`(**뮤테이션 필수** — `fixture_list_truncated` 필드 채우는 코드를 제거하면 RED) + `pytest server/tests/test_groupgen_tools.py::TestCreateArrangementGroupsRefusals::test_truncated_fixture_container_never_blocks_an_explicit_fids_write`(툴 계층 라이브 형상 회귀 — 승인 후 실제 발화됨 + 반환 payload에 `fixture_list_truncated`/`fixture_list_truncated_reason` 실림). **판별 경로**: `pytest server/tests/test_groupgen_tools.py::TestClassifyArrangementTopology::test_truncated_rig_read_reports_partial_coverage_and_lowconfidence_flag`(**뮤테이션 필수** — `topology_partial` 채우는 코드를 제거하면 RED) + `test_species_axis_groups_are_independent_of_rig_read_coverage`(종류 축은 커버리지와 무관함을 확인) | **쓰기 경로**: 절단된 픽스처 목록에서도 명시 `fids` 그룹 생성이 **거부되지 않고 진행**되며, `GroupWritePlan.fixture_list_truncated`(구조적 필드) + 반환 payload의 동일 필드로 절단 사실이 고지됨. **판별 경로**: `payload["coverage"] == {"judged": N, "of": M, "complete": bool}` 존재 + 불완전 시 `topology_partial: true`(기하 축 `suggested_groups` 항목에도 동일 표기) + 이유 문장 비어있지 않음. 종류 축 그룹은 `topology_partial` 키를 갖지 않음. **[HARD] REQ-021(그룹 풀 절단 → 슬롯 할당 거부)은 무변경** — `test_select_group_slot_rejects_truncated_pool`/`test_truncated_group_pool_refuses_the_whole_call` 계속 그린. `guard_fixture_list_truncation` 함수와 그 단위 테스트(`test_guard_fixture_list_truncation_*`)는 삭제되지 않고 존속 |
| **AC-GROUPGEN-038** | REQ-024 (정정 보조) | `pytest server/tests/test_groupgen_write.py -k guard_fixture_list_truncation` | `guard_fixture_list_truncation` 함수가 여전히 존재하고 단독 호출 시 절단을 거부함(자동 선택 경로를 위해 보존됨 — `build_group_write_plan` 내부에서는 더 이상 호출되지 않음) |
| **AC-GROUPGEN-025** | REQ-025 | `pytest server/tests/test_group_write.py::test_spoken_slots_equal_measured_empty_slots` — 발화 커맨드로 나가는 슬롯 번호 집합과 재조회 빈 슬롯 집합(`2~10·14·16+`)을 정적으로 비교 | 두 집합이 정확히 일치. 기존 슬롯(`1·11·12·13·15`) 접촉 0(정적 단언 — 발화 문자열에 해당 번호 부재) |
| **AC-GROUPGEN-026** | REQ-026 | `pytest server/tests/test_group_write.py::test_livelock_active_downgrades_all_stages_to_proposal` | LiveLock 활성 시 콘솔 송신 커맨드 수 == 0(멤버십 판독 시도 포함 전 단계가 제안으로 강등) |
| **AC-GROUPGEN-027** | REQ-027 | **[DESCOPED-v1]** — 교차 미구현이므로 코드 검증 대상 아님 | §D 참조. 복원 조건: D-Q9 보수 결정이 향후 SPEC에서 뒤집혀 위상×종류 교차가 채택될 때, 상한 기계와 함께 재도입 |
| **AC-GROUPGEN-028** | REQ-028 | `pytest server/tests/test_tools.py -q`(툴 개수 고정 테스트, §7 항목 참조) + `grep -n "def arrange_fixtures\|def propose_" server/orchestrator/tools.py` — 읽기/제안 툴과 쇼파일 변형 툴이 별개 함수/스키마인지 확인 | 읽기(제안) 1개 + 쇼파일 변형 1개, 총 2개 신규 툴이 서로 다른 승인 카드 분류 경로를 가짐(한 툴에 병합되지 않음) |
| **AC-GROUPGEN-029** | REQ-029 | `grep -A 20 "§E.2" .moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md \| grep -c "^- GO:\|^- NEGATIVE:\|^- SKIP: CONDITION_NOT_MET"` | M0 판정 기록이 폐쇄 어휘(`GO:`/`NEGATIVE:`/`SKIP: CONDITION_NOT_MET`) + 행두 접두 형식으로 `progress.md §E.2`에 존재. 미프로브 전제(예: ASSUMPTION-67)는 `SKIP: CONDITION_NOT_MET` 행을 받음 — 행 자체가 없으면 FAIL |
| **AC-GROUPGEN-030** | REQ-030 | `pytest server/tests/test_fixture_type_lookup.py::test_homogeneous_rig_yields_zero_type_axis_output` — 실측 동종 리그(`FixtureTypes` childCount 1)를 그대로 fixture로 사용 | 종류 축 산출 그룹 수 == 0이며, 그 사실이 반환 구조체의 명시 필드(예: `type_axis_groups: [], reason: "homogeneous_rig"`)로 보고됨(조용한 0이 아님) |
| **AC-GROUPGEN-031** | (게이트 B — Store Group 생성) | **LIVE — 완료(v0.2.0)**. M0 P3 프로브 실측: 빈 슬롯 14에 `exec Store Group 14` → `ok:true "OK"` **AND** `state DataPool/Groups` 재조회 `childCount 5→6`·슬롯 14 출현 **AND** `exec Label Group 14 'GroupgenProbe'` → `ok:true` **AND** `prop DataPool/Groups/14 Name` 재조회 → `"GroupgenProbe"`(`progress.md` §E.2.3 인용) | **PASS/GO 확정.** 그룹이 실제로 생성됨(풀 재조회 + 이름 재조회로 확인 — `ok:true` 단독이 아니다) → **M3 진행 가능.** NEGATIVE 열은 발동하지 않았으므로 미실행(코드 자체는 여전히 M3 구현 대상) |
| **AC-GROUPGEN-032** | (게이트 C — 점유 슬롯 덮어쓰기) | **LIVE — 완료(v0.2.0)**. M0 P6 프로브 실측: 점유 슬롯 14(P3로 선점)에 다른 픽스처(5~7)로 재발화 → `exec Store Group 14` → `ok:false "User Canceled Command"` **AND** `prop DataPool/Groups/14 Name` 재조회 → 기존 `"GroupgenProbe"` 유지(덮이지 않음) **AND** `state DataPool/Groups` `childCount 6` 유지(`progress.md` §E.2.4 인용) | **NEGATIVE-강화로 기록됨.** 콘솔은 거부하지 않고 **GUI 확인 다이얼로그**를 띄웠으며 무인 발화는 취소로 귀결됐다 — 조용한 덮어쓰기도 즉각 거부도 아닌 **조작자 의존 비결정** 거동이다. 이는 NEGATIVE가 아니라 **REQ-022 정적 차단의 근거를 강화**하는 결과다(코드 차단은 AC-GROUPGEN-022가 별도로 담보). `progress.md §E.2.4`에 `NEGATIVE:` 행(강화)으로 기록됨이 판정 기준이며, 모달 위험(§C.3 항목 9) 관측도 함께 기록됨 |
| **AC-GROUPGEN-033** | (경계 — 룰북 무변경) | `git diff --stat -- server/rulebook/assets/v2.4.2/` → 빈 출력 **AND** `sha256sum server/rulebook/assets/v2.4.2/*.md`를 착수 시점 스냅샷과 비교 | `00~32` 전체 byte-diff 0(신설·수정 0건). v1은 룰북 신설을 하지 않는다(D-Q7) |
| **AC-GROUPGEN-034** | (경계 — 회귀 기준선) | `pytest -q`(전체) + `npx vitest run`(전체) — **기준선은 run-phase 킥오프 시점에 재측정**한 결과이며, plan-phase 참고 수치(2026-08-03 pytest 4511 passed·5 skipped, vitest 350)를 그대로 재사용하지 않는다 | run-phase 킥오프 시점 재측정 기준선 대비 신규 실패 0건. 커밋 메시지 또는 progress.md에 재측정 시각·수치가 기록됨(참고 수치와 구별되는 별도 라벨) |
| **AC-GROUPGEN-035** | (경계 — 타 SPEC 불변식 트립와이어) | `pytest server/tests/test_overlap_preserve.py server/tests/test_songcue_bundle.py -q`(파일명은 저장소의 실제 트립와이어 테스트 명칭 기준, `tools.py` 변경 시 재점검) | 전량 그린. `server/orchestrator/tools.py` 개정(REQ-028)이 이 두 트립와이어를 깨지 않음(SPATIAL §E.2.19 선례 재확인) |
| **AC-GROUPGEN-036** | **REQ-031 · 031a · 031b** (개정 v0.3.0 — **툴 계층 승인 강제**) | ① `pytest server/tests/test_groupgen_tools.py -q` — 승인 O → 발화됨 / 승인 X → **콘솔 송신 0** + 계획만 반환 / 승인 포트 부재·미확인 → 송신 0(fail-closed). ② **뮤테이션 필수**: `create_arrangement_groups`에서 승인 확인을 제거하면 ①이 반드시 RED. ③ **REQ-031a 경계**: `git diff --stat -- server/safety/` → **빈 출력**(byte-diff 0). 추가로 `pytest server/tests/ -k safety -q` 전량 **무수정 PASS**. ④ **REQ-031b 고지**: `spec.md` §C.1에 *"본 SPEC의 툴을 경유하지 않는 그룹 생성은 무승인"*이 명시돼 있음을 grep으로 확인 | ①②③④ 전부 충족. **툴을 경유하는 그룹 쓰기 중 승인 없이 콘솔에 도달하는 코드 경로 0건.** ⚠ 강제는 **툴 설명문이 아니라 코드 구조**여야 한다 — docstring 에 "승인을 받으세요"만 있고 구조 강제가 없으면 **FAIL**(함정 6: SPATIAL이 설명문에 명령형으로 적었으나 모델이 무시했다. 단 함정 6은 *모델에게 주는 설명문*에 관한 것이며 코드가 송신을 거부하는 것은 구조적 강제다). ⚠ **범위 밖 구멍은 닫지 않는다**: 채팅 경로의 직접 `Store Group` 발화는 여전히 무승인이며, 이를 닫으려면 `server/measurement/corpus.yaml`(헤더 불변식 *"non-risky verbs only"* + `group_create` = AC-MVP-001 대표작업) 등 MVP 소유 자산을 바꿔야 한다 → **별도 SPEC**. `design.md` §7.4 참조 |
| **AC-GROUPGEN-037** | REQ-015 · 016 · 017 · 018 · 019 (**임의 작명 금지 — 뮤테이션**) | `pytest server/tests/test_naming.py::test_no_group_name_is_ever_constructed_from_arbitrary_input` — **뮤테이션 필수**. AC-013/015/016/018/019의 정적 grep은 *"현재 상수 목록에 금지어가 없다"*만 증명하고 *"작명 로직이 임의 문자열을 만들 수 없다"*는 증명하지 못한다(plan.md §B M5가 요구한 5번째 항목). 따라서 **동적 계약**을 건다: ① `naming.py`의 모든 공개 명명 함수가 반환하는 문자열은 `"GEO " + <폐쇄 집합 원소>` 또는 `"GEO " + <문서화된 번호 폴백>`(`Electric N`·`Ring N`·`Level N`) 중 하나임을 **전수 대조**한다 — 반환값을 폐쇄 집합 ∪ 폴백 정규식으로 검증. ② **적대적 입력**: 픽스처 이름에 `"Copilot MMX 3"`·`"'; Label Group 1 'x"`·빈 문자열·유니코드를 넣은 golden을 태워도 반환 이름이 입력 문자열의 어떤 부분도 포함하지 않음을 assert(`assert fixture_name_fragment not in produced_name`). ③ **뮤테이션**: 폐쇄 집합 조회를 f-string 보간(예: `f"GEO {bucket_label}"` where `bucket_label`이 입력 파생)으로 바꾸면 ①②가 **반드시 RED**가 된다 | ①②③ 전부 충족. **입력에서 파생된 문자열이 그룹 이름에 도달하는 코드 경로 0건.** 버킷 수가 폐쇄 어휘를 초과하면 임의 작명이 아니라 **문서화된 번호 폴백**(REQ-017 — 방향 명시)으로 내려간다. ⚠ 이 AC가 없으면 plan.md M5의 뮤테이션 5항목 중 1개가 미이행이다 — 정적 grep만으로는 통과시킬 수 없다 |
| **AC-GROUPGEN-039** | REQ-001 · 002 · 003 · 004 (**M6 라이브 — 같은 지시, 세 배치**) | **LIVE — 완료(2026-08-04)**. 하네스 `.moai/reports/m0-probe/groupgen_m6_e2e.py`가 실물 게이트 스택(`build_console_stack` → `build_toolset(bundle_gate=, group_approval_port=)`)으로 **`registry.dispatch`** 에 진입해, `arrange_fixtures`로 배치를 쓴 뒤 `classify_arrangement_topology`를 호출했다. 기대 위상을 **실행 전에 하네스에 적어** 사후 합리화를 막았다 | **4/4 판정 GO**(progress.md §E.2.9.1): 3×6 그리드 → **`grid`** `depth[6,6,6]`+`lateral[3×6]` · 2겹 동심원 → **`concentric`** `[6,12]` · 좌우 분할 → **`lateral_split`** `[9,9]` · 전대 원점 → **`None`+저신뢰**(REQ-004 — 위상을 발명하지 않는다). `grid` 불변식(`fids_by_bucket==[]` ∧ `grid_axes` not-None) 라이브 준수. **어휘가 위상마다 달라졌다**: `GEO Downstage/Center/Upstage`+`Stage Right N/Stage Left N` · `GEO Inner/Outer` · `GEO Stage Right/Stage Left`. 리깅 하드웨어 어휘 **0건** |
| **AC-GROUPGEN-040** | REQ-023 · 025 · 031 (**M6 라이브 — 정책 (c) 종단**) | **LIVE — 완료(2026-08-04)**. 동심원 배치에서 `create_arrangement_groups` 1회. 툴 반환을 믿지 않고 **bridge 직결 프로브로 교차 확인** | `status: created` · **승인 요청 번들 정확히 1회**(툴 계층 게이트 경유) · `verified_steps`가 `slot 2 GEO Inner(fid 20~25)` / `slot 3 GEO Outer(fid 26~37)`를 `slot_exists`+`name_verified` **재조회**로 확인 · `unverified:["membership"]` 및 `fixture_list_truncated:true` **구조적 고지** · `human_check_commands:["Group 2","Group 3"]` 동봉. **독립 교차**: 풀 `childCount 5→7`, 기존 `1·11·12·13·15` 무접촉. 정리 후 `5`로 복귀 + 슬롯 2·3 *not found* → **그룹 축 순변화 0** |
| **AC-GROUPGEN-041** | (**검증 천장 — 사람 무대 관측**) | **LIVE — GO(2026-08-04, 사용자 직접 확인)**. 기계로는 확인 **불가**(spec.md §C.1 · 멤버십 미노출 §E.2.8) — `ClearAll` → `Group 2` → `ClearAll` → `Group 3` → `ClearAll`을 콘솔에서 실행하고 무대를 눈으로 관측 | **GO**: `Group 2` → 내륜 **6대만**, `Group 3` → 외륜 **12대만**. 의도대로 갈렸다. 정책 (c)의 잔여 위험(*"이름은 맞는데 멤버가 다를 수 있다"*)이 **이 배치에 대해 해소**됐다. **증거 등급 (세션)** — 라이브 관측이며 저장소 아티팩트로 재확인할 수단이 없다. **상향하지 않는다** |
| **AC-GROUPGEN-042** | REQ-003 (**M6가 잡은 경합 결함 2건 — 뮤테이션**) | `pytest server/tests/test_topology.py::test_mirrored_left_right_rig_is_lateral_not_nine_rings` · `::test_bilateral_pairs_is_reported_but_never_selected` · `::test_a_genuine_two_ring_rig_still_wins_as_concentric` | 3/3 그린. **뮤테이션 RED 증명**: 미러 아티팩트 강등 제거 → **1 failed** · `bilateral`을 `scored`에 재투입 → **2 failed**. **비공허성**: 진짜 2겹 동심원(6·12)은 여전히 `concentric` — 강등은 *"모든 반지름 버킷이 정확히 2 ∧ `bilateral_pairs` 고신뢰"* 에서만 발화한다. ⚠ 이 두 결함은 **단위 테스트로는 원리적으로 나올 수 없었다** — 라이브 배치가 만든 대칭이 드러냈다 |

## §D. `[DESCOPED-v1]` 복원 조건 (v1 범위 밖 이관 4건)

| REQ | 이관 사유 | 복원 조건 |
|---|---|---|
| REQ-GROUPGEN-010 | GDTF `Categories` 필드 부재로 타입명 문자열 토큰 매칭이 유일 근거이며 이는 추측이다(D-Q9/Q11 사용자 승인) | 별도 SPEC이 합성 이종 리그 golden을 확보하고, 토큰 매칭의 오탐률을 실측 근거로 제시할 때 |
| REQ-GROUPGEN-011 | REQ-010에 종속(무매칭/다중매칭 판정은 카테고리 축이 있어야 의미를 가짐) | REQ-010과 **동반 복원만 가능** — 단독 복원 불가 |
| REQ-GROUPGEN-012 | 카테고리 판정(REQ-010) 없이는 `Blinder`를 식별할 **수단 자체가 없다**. 이 연쇄를 놓치면 "블라인더를 분리한다"는 지킬 수 없는 약속이 남는다 | **선결 조건: REQ-010 복원.** REQ-010이 복원되어 카테고리 축이 실제로 산출되기 전에는 REQ-012를 독립적으로 구현할 방법이 없음(식별 근거 부재) |
| REQ-GROUPGEN-027 | 위상×종류 교차가 v1에 미구현(D-Q9 보수 결정)이므로 폭발 제어 자체가 대상을 잃음 | 향후 SPEC이 교차 그룹을 채택할 때 상한 기계·초과 시 거동과 함께 재도입. 빈 슬롯 유한성(`2~10·14·16+`) 제약이 여전히 적용됨 |

## §E. 엣지 케이스

1. **깊이 축과 좌우 축의 `Center` 충돌** — 두 축 모두 3분할 시 `Center`를 쓰면 서로 다른 픽스처 집합을 같은 이름으로 가리킨다. 좌우 중앙은 `Centerline`으로 확정(D-Q2)하여 회귀 픽스처로 고정할 것 — `pytest server/tests/test_naming.py::test_center_vs_centerline_disambiguation`.
2. **9칸 그리드 어휘는 정의하되 v1 미발화** — `DSR…USL` 상수가 `naming.py`에 폐쇄 집합으로 존재하되 어떤 산출 경로도 이를 호출하지 않음을 `grep -rn "DSR\|USL" server/spatial/ server/orchestrator/` 로 정적 확인(호출부 부재).
3. **`bilateral_pairs`는 분류되지만 그룹이 되지 않는다(D-Q10)** — `topology.classify()`는 대칭 쌍을 반환하되, `naming.py`/그룹 쓰기 경로가 이를 소비하지 않음을 `grep -n "bilateral_pairs" server/spatial/naming.py server/orchestrator/tools.py` → 매치 0으로 확인.
4. **명칭 축(C2) 제안은 확정 경로가 없다(D-Q12)** — 읽기 툴 출력에만 실리고, 그룹 생성 API로 이어지는 코드 경로가 없음을 정적 확인.
5. **동종 리그의 카테고리 축도 산출 0** — REQ-030이 종류 축 전체(제조사·타입명·카테고리)에 적용됨을 명시(AC-GROUPGEN-030 확장 케이스).
6. **onPC 콘솔 무접촉 요구(plan-phase)** — 본 `acceptance.md` 저작 자체는 라이브 프로브를 하지 않는다. AC-GROUPGEN-023·029·031·032의 LIVE 판정은 M0(run-phase)에서 채워진다.

## §F. 품질 게이트

- **Tested**: 신규 코드(topology.py · naming.py · fixture_type.py) 커버리지 85%+ 목표. **뮤테이션 필수 6항목(v0.2.0 갱신 — 5→6)** — 절단 거부 `AC-021` · 점유 슬롯 차단 `AC-022` · 멤버십 검증 `AC-023`(정책 (c) NEGATIVE 열) · 위상 오분류(동심원→행) `AC-003` · **임의 작명 금지 `AC-037`** · **정직한 고지 필드 `AC-023`③**(`test_return_payload_declares_membership_unverified` — 반환 구조체의 `unverified` 필드를 제거하면 반드시 RED) — 은 각각 가드 제거 시 반드시 RED임을 별도 테스트로 증명. 안전 게이트 인식 제거 뮤테이션(`AC-036` ④)도 동일 규율.
  **⚠ plan.md와의 개수 정합 참고**: `plan.md` §B M5는 뮤테이션 필수 **5항목**을 약속했다(plan.md는 이 워커의 소유가 아니므로 수정하지 않는다). v0.1.2에서 `AC-037`(임의 작명 금지) 신설로 4→5 정합을 맞췄고, 본 개정(v0.2.0)은 게이트 A NEGATIVE 열이 정책 (c)로 확정되며 "정직한 고지" 층이 뮤테이션 대상 데이터 계약으로 신설된 데 따라 **acceptance.md 자체 판단으로 5→6**을 채택했다. 이는 plan.md M5의 원래 5항목을 **대체하는 것이 아니라 확장**이다 — 정직한 고지는 함정 6(*"툴 설명문은 지시일 뿐 강제가 아니다"*)의 직접 재발 방지 항목이며 정적 grep으로는 증명되지 않으므로(§10 정책 (c) 표), 뮤테이션 목록에서 누락하면 정책 (c)의 3층("정직한 고지")이 구조가 아니라 설명문으로 남는다. `plan.md`를 개정하지 않고 이 불일치를 acceptance.md 안에 명시하는 것으로 갈음한다.
- **Readable/Unified**: 기존 `server/spatial/` 스타일·네이밍 준수(ruff 통과, 신규 결함 0 — 기존 부채 3건은 무관).
- **Secured**: 점유 슬롯 차단(AC-022)·절단 거부(AC-021)·게이트 A NEGATIVE 강등(AC-023)이 fail-closed 경계를 넘지 않음을 개별 증명. `ok:true`는 어떤 AC에서도 유일 증거로 쓰이지 않는다.
- **Trackable**: Conventional Commits + SPEC ID 참조(`feat(SPEC-COPILOT-GROUPGEN-001): …`). `[DESCOPED-v1]` 4건과 복원 조건이 커밋 본문 또는 spec.md §D에 명시.
