# SPEC-COPILOT-GROUPGEN-001 — 수용 기준 (acceptance)

status: draft (v0.1.2, plan-phase — plan-audit MAJOR-2 반영). `AC-GROUPGEN-001`~`030`을
`REQ-GROUPGEN-001`~`030`에 1:1 대응시키고, 게이트 분기·회귀·경계 판정용으로
`AC-GROUPGEN-031`~`035`를 추가한다(계약 §5 — 추가분은 031부터).
**`AC-GROUPGEN-036`은 `REQ-GROUPGEN-031`(D-Q4 `server/safety` 정식 게이트 확장)에 1:1 대응한다** —
REQ 신규 번호와 AC 추가 번호가 독립적으로 031을 소진해 커버리지 공백이 생겼던 것을 coordinator가
plan-phase 감사에서 잡아 메웠다. **REQ 031 ↔ AC 036이며 번호가 일치하지 않는다는 점에 주의할 것.**
**`AC-GROUPGEN-037`(임의 작명 금지 뮤테이션)** 은 plan-audit MAJOR-2로 추가됐다 —
`plan.md` §B M5가 요구한 뮤테이션 5항목 중 "임의 작명 금지"가 정적 grep만 갖고 있어
뮤테이션 대상이 없던 결함을 닫는다. REQ-015~019에 걸치는 횡단 AC다.
검증 천장(spec.md §C.1)을 넘는 AC는 만들지 않는다: 그룹 멤버십이 의도한 픽스처인가(게이트 A GO 조건부) ·
종류 축의 이종 리그 거동(합성 golden 필수) · 그룹이 연출에서 "맞게" 동작하는가(사람 관측만)는
**LIVE** 또는 **SKIP: CONDITION_NOT_MET**으로 표기하며 기계 검증 AC를 달지 않는다.

## §A. 완료 정의 (Definition of Done)

1. AC-GROUPGEN-001~009 · 013~026 · 028~030 · 031~037 — 전부 기계 검증(pytest/grep) 그린
   (031·032는 LIVE — 아래 4항).
2. AC-GROUPGEN-010~012 · 027 — `[DESCOPED-v1]`로 표기되고 §D의 복원 조건이 문서화됨(코드 검증 대상 아님).
3. AC-GROUPGEN-014 — `[Optional]`. 제안 UX가 존재하면 그린, 존재하지 않으면 REQ-014가 애초에
   `[Optional]`이므로 미구현이 SPEC 실패가 아님(design.md가 채택 여부를 확정).
4. M0 라이브 프로브(AC-GROUPGEN-023 · 029 · 031 · 032)는 **LIVE** 항목이며 게이트 A/B/C의 GO/NEGATIVE
   양 분기 서술을 모두 갖는다. 미프로브 상태의 AC는 `SKIP: CONDITION_NOT_MET` 행을 받는다(REQ-029).
5. 신규 런타임 의존성 0(AC-GROUPGEN-035 회귀 스위프에 포함).
6. `server/spatial/topology.py` transport·게이트 import 0(AC-GROUPGEN-006) + PRESERVE 대상 무변경
   (AC-GROUPGEN-005 · 033).

## §B. 게이트 분기 규율 (계약 §3 — 모든 AC 공통)

| 게이트 | GO 분기 AC | NEGATIVE 분기 AC |
|---|---|---|
| A. 멤버십 판독 채널 | AC-GROUPGEN-023 (GO 행) | AC-GROUPGEN-023 (NEGATIVE 행 — 제안 전용 강등) |
| B. `Store Group <n>` 생성 | AC-GROUPGEN-031 (GO 행) | AC-GROUPGEN-031 (NEGATIVE 행 — SPEC 전체 중단) |
| C. 점유 슬롯 덮어쓰기 | AC-GROUPGEN-032 (GO 행 — 차단 규칙 확정) | AC-GROUPGEN-032 (NEGATIVE 행 — 차단이 더욱 절대적, 강화이지 실패 아님) |
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
| **AC-GROUPGEN-022** | REQ-022 | `pytest server/tests/test_group_write.py::test_occupied_slot_write_is_statically_blocked` — **뮤테이션 필수**: 점유 슬롯 정적 차단 코드를 제거하면 이 테스트가 반드시 RED | 슬롯 `1`·`11`·`12`·`13`·`15`(실측 점유) 대상 기록 시도 → 사전 차단(콘솔 송신 이전에 거부). 차단 로직 제거 뮤테이션 시 테스트 RED |
| **AC-GROUPGEN-023** | REQ-023 (게이트 A) | **LIVE + pytest 혼합**. GO 분기: `pytest server/tests/test_group_write.py::test_membership_verified_via_requery_not_ok_flag` — **뮤테이션 필수**: 재조회 검증 호출을 제거하면 RED. NEGATIVE 분기: M0 P1/P5 라이브 프로브 결과가 채널 부재로 판정되면 `pytest server/tests/test_group_write.py::test_gate_a_negative_downgrades_to_proposal_only` | GO: `ok:true`만으로 통과하는 코드 경로가 없고, 채택 채널로의 재조회 결과가 assert됨(가드 제거 뮤테이션 시 RED). NEGATIVE: 게이트 A가 NEGATIVE로 확정되면 자동 생성 축이 중단되고 산출물이 발화 목록(제안) 전용으로 강등됨을 코드가 보장 — 이 AC 자체는 GO/NEGATIVE 중 M0 실측 결과에 해당하는 분기만 실행되고 나머지는 `SKIP: CONDITION_NOT_MET`(REQ-029 규율) |
| **AC-GROUPGEN-024** | REQ-024 | `pytest server/tests/test_group_write.py::test_truncated_fixture_list_refuses_or_warns` — `childCount 19` vs 반환 `18`(절단) 시나리오 재현 | 절단된 픽스처 목록에서 그룹 생성이 거부되거나 명시 경고(`truncated: true` 플래그 + 경고 메시지)를 동반. 조용한 통과(경고 없음)는 FAIL |
| **AC-GROUPGEN-025** | REQ-025 | `pytest server/tests/test_group_write.py::test_spoken_slots_equal_measured_empty_slots` — 발화 커맨드로 나가는 슬롯 번호 집합과 재조회 빈 슬롯 집합(`2~10·14·16+`)을 정적으로 비교 | 두 집합이 정확히 일치. 기존 슬롯(`1·11·12·13·15`) 접촉 0(정적 단언 — 발화 문자열에 해당 번호 부재) |
| **AC-GROUPGEN-026** | REQ-026 | `pytest server/tests/test_group_write.py::test_livelock_active_downgrades_all_stages_to_proposal` | LiveLock 활성 시 콘솔 송신 커맨드 수 == 0(멤버십 판독 시도 포함 전 단계가 제안으로 강등) |
| **AC-GROUPGEN-027** | REQ-027 | **[DESCOPED-v1]** — 교차 미구현이므로 코드 검증 대상 아님 | §D 참조. 복원 조건: D-Q9 보수 결정이 향후 SPEC에서 뒤집혀 위상×종류 교차가 채택될 때, 상한 기계와 함께 재도입 |
| **AC-GROUPGEN-028** | REQ-028 | `pytest server/tests/test_tools.py -q`(툴 개수 고정 테스트, §7 항목 참조) + `grep -n "def arrange_fixtures\|def propose_" server/orchestrator/tools.py` — 읽기/제안 툴과 쇼파일 변형 툴이 별개 함수/스키마인지 확인 | 읽기(제안) 1개 + 쇼파일 변형 1개, 총 2개 신규 툴이 서로 다른 승인 카드 분류 경로를 가짐(한 툴에 병합되지 않음) |
| **AC-GROUPGEN-029** | REQ-029 | `grep -A 20 "§E.2" .moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md \| grep -c "^- GO:\|^- NEGATIVE:\|^- SKIP: CONDITION_NOT_MET"` | M0 판정 기록이 폐쇄 어휘(`GO:`/`NEGATIVE:`/`SKIP: CONDITION_NOT_MET`) + 행두 접두 형식으로 `progress.md §E.2`에 존재. 미프로브 전제(예: ASSUMPTION-67)는 `SKIP: CONDITION_NOT_MET` 행을 받음 — 행 자체가 없으면 FAIL |
| **AC-GROUPGEN-030** | REQ-030 | `pytest server/tests/test_fixture_type_lookup.py::test_homogeneous_rig_yields_zero_type_axis_output` — 실측 동종 리그(`FixtureTypes` childCount 1)를 그대로 fixture로 사용 | 종류 축 산출 그룹 수 == 0이며, 그 사실이 반환 구조체의 명시 필드(예: `type_axis_groups: [], reason: "homogeneous_rig"`)로 보고됨(조용한 0이 아님) |
| **AC-GROUPGEN-031** | (게이트 B — Store Group 생성) | **LIVE**. M0 P3 프로브: 빈 슬롯 1개(예: 14)에 `Store Group <n>` 발화 후 재조회 | GO: 그룹이 실제로 생성됨(재조회로 확인) → M3 진행. NEGATIVE: 그룹이 생성되지 않거나 재조회 실패 → **SPEC 전체 중단**을 `progress.md §E.2`에 `NEGATIVE:` 행으로 기록하고 이후 마일스톤 전부 미실행 처리 |
| **AC-GROUPGEN-032** | (게이트 C — 점유 슬롯 덮어쓰기) | **LIVE**. M0 P6 프로브: 이미 점유된 슬롯(프로브 전용 슬롯을 P3로 먼저 점유시킨 뒤)에 다른 픽스처로 재발화 | GO(차단 규칙 확정): 콘솔이 거부하거나, 조용히 덮어쓴다는 실측이 나오면 이는 NEGATIVE가 아니라 **REQ-022 정적 차단의 근거를 강화**하는 결과로 기록(코드 차단은 AC-GROUPGEN-022가 별도로 담보하므로 이 AC는 실측 사실 자체를 `progress.md §E.2`에 `GO:`/`NEGATIVE:` 행으로 남기는 것이 판정 기준) |
| **AC-GROUPGEN-033** | (경계 — 룰북 무변경) | `git diff --stat -- server/rulebook/assets/v2.4.2/` → 빈 출력 **AND** `sha256sum server/rulebook/assets/v2.4.2/*.md`를 착수 시점 스냅샷과 비교 | `00~32` 전체 byte-diff 0(신설·수정 0건). v1은 룰북 신설을 하지 않는다(D-Q7) |
| **AC-GROUPGEN-034** | (경계 — 회귀 기준선) | `pytest -q`(전체) + `npx vitest run`(전체) — **기준선은 run-phase 킥오프 시점에 재측정**한 결과이며, plan-phase 참고 수치(2026-08-03 pytest 4511 passed·5 skipped, vitest 350)를 그대로 재사용하지 않는다 | run-phase 킥오프 시점 재측정 기준선 대비 신규 실패 0건. 커밋 메시지 또는 progress.md에 재측정 시각·수치가 기록됨(참고 수치와 구별되는 별도 라벨) |
| **AC-GROUPGEN-035** | (경계 — 타 SPEC 불변식 트립와이어) | `pytest server/tests/test_overlap_preserve.py server/tests/test_songcue_bundle.py -q`(파일명은 저장소의 실제 트립와이어 테스트 명칭 기준, `tools.py` 변경 시 재점검) | 전량 그린. `server/orchestrator/tools.py` 개정(REQ-028)이 이 두 트립와이어를 깨지 않음(SPATIAL §E.2.19 선례 재확인) |
| **AC-GROUPGEN-036** | **REQ-031** (D-Q4 — `server/safety` 정식 게이트 확장) | ① `pytest server/tests/test_safety_group_write_gate.py -q` — `Store Group <n>` · `Label Group <n> '…'`이 게이트에서 **`risky`로 분류**되고 승인 카드가 정규 경로로 발행됨을 단언. ② **의미론 무변경 회귀**: `pytest server/tests/test_safety_console.py server/tests/test_safety_screen.py -q`(3-stage screen · expand-or-hold · LiveLock · 백업 · 감사) → 기존 테스트 **무수정 PASS**. ③ **경계 한정 정적 검사**: `git diff -- server/safety/` 의 헝크가 그룹 쓰기 참조 타입 인식·분류에만 닿는지 육안 + `grep -c` 대조 — screen 단계 수·expand-or-hold 분기·LiveLock 조건에 대한 diff 0. ④ **뮤테이션**: 게이트에서 그룹 쓰기 참조 타입 인식을 제거하면 ①이 반드시 빨개진다 | ①②③④ 전부 충족. **승인 없이 그룹 쓰기가 콘솔에 도달하는 코드 경로 0건**(함정 8 재발 방지 — 요청하지 않은 좌표 기록 54건이 통과한 사고가 복구 불가 자산에서 반복되면 되돌릴 수 없다). ⚠ 승인 요구는 **툴 설명문이 아니라 게이트 구조**로 강제되어야 한다(함정 6 — SPATIAL이 설명문에 명령형으로 적었으나 모델이 무시했다). 설명문만 있고 구조 강제가 없으면 **FAIL** |
| **AC-GROUPGEN-037** | REQ-015 · 016 · 017 · 018 · 019 (**임의 작명 금지 — 뮤테이션**) | `pytest server/tests/test_naming.py::test_no_group_name_is_ever_constructed_from_arbitrary_input` — **뮤테이션 필수**. AC-013/015/016/018/019의 정적 grep은 *"현재 상수 목록에 금지어가 없다"*만 증명하고 *"작명 로직이 임의 문자열을 만들 수 없다"*는 증명하지 못한다(plan.md §B M5가 요구한 5번째 항목). 따라서 **동적 계약**을 건다: ① `naming.py`의 모든 공개 명명 함수가 반환하는 문자열은 `"GEO " + <폐쇄 집합 원소>` 또는 `"GEO " + <문서화된 번호 폴백>`(`Electric N`·`Ring N`·`Level N`) 중 하나임을 **전수 대조**한다 — 반환값을 폐쇄 집합 ∪ 폴백 정규식으로 검증. ② **적대적 입력**: 픽스처 이름에 `"Copilot MMX 3"`·`"'; Label Group 1 'x"`·빈 문자열·유니코드를 넣은 golden을 태워도 반환 이름이 입력 문자열의 어떤 부분도 포함하지 않음을 assert(`assert fixture_name_fragment not in produced_name`). ③ **뮤테이션**: 폐쇄 집합 조회를 f-string 보간(예: `f"GEO {bucket_label}"` where `bucket_label`이 입력 파생)으로 바꾸면 ①②가 **반드시 RED**가 된다 | ①②③ 전부 충족. **입력에서 파생된 문자열이 그룹 이름에 도달하는 코드 경로 0건.** 버킷 수가 폐쇄 어휘를 초과하면 임의 작명이 아니라 **문서화된 번호 폴백**(REQ-017 — 방향 명시)으로 내려간다. ⚠ 이 AC가 없으면 plan.md M5의 뮤테이션 5항목 중 1개가 미이행이다 — 정적 grep만으로는 통과시킬 수 없다 |

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

- **Tested**: 신규 코드(topology.py · naming.py · fixture_type.py) 커버리지 85%+ 목표. **뮤테이션 필수 5항목**(plan.md §B M5와 1:1) — 절단 거부 `AC-021` · 점유 슬롯 차단 `AC-022` · 멤버십 검증 `AC-023` · 위상 오분류(동심원→행) `AC-003` · **임의 작명 금지 `AC-037`** — 은 각각 가드 제거 시 반드시 RED임을 별도 테스트로 증명. 안전 게이트 인식 제거 뮤테이션(`AC-036` ④)도 동일 규율.
- **Readable/Unified**: 기존 `server/spatial/` 스타일·네이밍 준수(ruff 통과, 신규 결함 0 — 기존 부채 3건은 무관).
- **Secured**: 점유 슬롯 차단(AC-022)·절단 거부(AC-021)·게이트 A NEGATIVE 강등(AC-023)이 fail-closed 경계를 넘지 않음을 개별 증명. `ok:true`는 어떤 AC에서도 유일 증거로 쓰이지 않는다.
- **Trackable**: Conventional Commits + SPEC ID 참조(`feat(SPEC-COPILOT-GROUPGEN-001): …`). `[DESCOPED-v1]` 4건과 복원 조건이 커밋 본문 또는 spec.md §D에 명시.
