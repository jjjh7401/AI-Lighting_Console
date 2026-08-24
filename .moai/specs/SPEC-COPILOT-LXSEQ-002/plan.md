# SPEC-COPILOT-LXSEQ-002 — 구현 계획 (plan)

문서 상태: draft (v0.1.1, 2026-08-24). Tier M. 칸반 카드 t18 (4단계 중 2단계). 마일스톤 5개(M0에서 M4까지), 결정 등록부 **11건(K에서 U까지)**, **열린 결정 0건**(A.4의 둘은 2026-08-24 감독 착수 승인으로 결정 T·U 가 되어 A.3 으로 옮겨졌다). REQ 16건, AC 16건(실기 1건), ASSUMPTION 3건(80에서 82까지). 진행: M0 는 4항 중 3항 충족 — 전량 baseline 만 남았다(progress.md 6.4).

> **참조 규약.** 정본(spec.md, acceptance.md)은 줄번호로 인용하지 않고 REQ-LXSEQ2-001, AC-LXSEQ2-001, ASSUMPTION-80 같은 안정 토큰만 쓴다. 코드, 룰북, 입력 데이터, 타 SPEC 아티팩트는 파일과 줄 좌표를 쓴다.

---

## A. 맥락과 우선순위 — 바뀔 가능성이 큰 결정부터

### A.1 가장 먼저 읽을 것 — 이 SPEC에서 결정이 뒤집힐 수 있는 지점

| 순위 | 결정 | 왜 앞에 두나 | 어디서 닫히나 |
|---|---|---|---|
| 1 | **슬롯 번호의 권위가 시트인가 콘솔인가.** 시트는 GroupNo 1부터 18까지를 선언하는데 `build_group_write_plan` 은 요청 번호를 무시하고 `measure_empty_slots` 오름차순을 쓴다 | 빈 풀에서는 두 값이 우연히 같아 문제가 안 보인다. 점유가 하나라도 있으면 조용히 어긋나고, 곡 파일이 그룹 번호를 참조하므로 번호가 밀리면 쇼가 깨진다 | 결정 T — **닫힘**(감독 답 2026-08-24) |
| 2 | **입력이 파일 하나인가 둘인가.** 멤버십을 콘솔에서 읽는 길은 픽스처 열거가 86에서 19로 잘려 막혀 있다(카드 t46) | 시트 종류 레지스트리는 파일 하나를 핸들러 하나로 보내는 모형이라, 인자 둘은 그 모형과 마찰한다 | 결정 U — **닫힘**(감독 답 2026-08-24) |
| 3 | **Members 열을 해석하지 않는다.** 멤버십은 패치표 라벨에서, 파생 6종은 코드의 닫힌 규칙에서 | 한 열에 문법이 넷이고, 오해석이 조용히 잘못된 그룹을 만든다(spec.md A.2 첫째) | 결정 K — 닫힘 |
| 4 | **배치를 기본 12와 파생 6으로 나눈다.** 한 호출로 18개는 못 쓴다 | 실측 강제다. DEFAULT_GROUP_PLAN_CAP 이 16이고 툴이 max_plan_size 를 노출하지 않는다(spec.md A.2 둘째) | 결정 M — 닫힘 |
| 5 | **발화 전에 번들 바이트를 재고 예산을 넘으면 그 그룹을 건너뛴다.** | ALL 의 선택 줄이 1201바이트이고 상한까지의 여백은 미측정이다. 실패가 조용하고 멤버십은 되읽히지 않아 이 게이트가 유일한 탐지 지점이다(spec.md A.2 셋째) | 결정 N — 닫힘 |
| 6 | 툴 수 1종, 쓰기 경로 위임 하나 | 001의 선례를 그대로 따른다 | 결정 Q, R — 닫힘 |
| 7 | 파일 구조, 테스트 파일명, 등재 지점, 사본 계약 | 기계적 | 결정 L, O, P, S — 닫힘 |

### A.2 빌드 순서 vs 무엇이 무엇을 막는가

빌드 순서는 M0에서 M4까지다. 강한 순차 사슬이다. 파서 산출이 매퍼 입력이고, 매퍼 산출이 툴 위임 인자이며, 그다음이 라이브다.

| 항목 | 막는 대상 | 성격 | 부정 시 처리 |
|---|---|---|---|
| (닫힘) 결정 T 슬롯 권위 | M2 슬롯 대조 로직, M4 실기 절차 | 2026-08-24 감독 답으로 닫힘 — 마커 0건 | 해당 없음. 답은 progress.md의 착수 승인 절에 있다 |
| (닫힘) 결정 U 입력 파일 수 | M3 툴 인자 집합, 레지스트리 행 모양 | 2026-08-24 감독 답으로 닫힘 — 마커 0건 | 해당 없음. 비대칭의 모양은 카드 t53이 결정한다 |
| ASSUMPTION-80 그룹 풀이 비었다 | M4만 | 동작 축소 아님. REQ-009가 0배치를 낸다 | 사용자가 풀을 비우거나 감독이 슬롯 권위를 다시 정한다 |
| ASSUMPTION-81 번들이 상한 안이다 | M4 ALL 그룹만 | 그 그룹이 `bundle_over_budget` 으로 건너뛰어진다 | 상한 실측 후 예산 조정. 코드 변경 없음 |
| ASSUMPTION-82 픽스처 이름이 라벨에 FID 꼴 | M4 사람 확인 절차만 | 대조가 어려워질 뿐 계획은 성립 | 사용자가 콘솔에서 직접 확인 |

### A.3 결정 현황 — 해소 9건 (K에서 S까지)

| 결정 | 이름 | 확정 내용 | 반영 M |
|---|---|---|---|
| **K** | Members 열 미해석 | 파서는 Members 를 원문 보존만 하고 멤버십 판정에 쓰지 않는다. 한 열에 문법이 넷이라(라벨에 개수 / 라벨 합집합 / 전체에서 제외 / 다른 그룹에 대한 술어) 한 파서로 받으면 규칙마다 파서가 늘고 오해석이 조용히 잘못된 그룹을 만든다. 대신 개수를 적은 행에 한해 **교차검증**에만 쓴다(REQ-007) | M1, M2 |
| **L** | 파생 6종 닫힌 어휘 | ALL, SIDE-ALL, WASH-ALL, MOVER-ALL, ODD, EVEN 여섯만. 규칙 표는 `group_mapper.py` 가 소유한다. 이 여섯도 패치 라벨도 아닌 Name 은 `unknown_group_name` 으로 건너뛴다. 데이터에서 규칙을 유추하는 경로는 만들지 않는다 | M2 |
| **M** | 배치 분할 | **기본 12 먼저, 파생 6 나중.** 실측 강제다 — `server/groupgen/write.py:66` 의 DEFAULT_GROUP_PLAN_CAP 이 16이고 `server/orchestrator/tools.py:7101` 의 호출이 max_plan_size 를 넘기지 않아 18개는 GROUP_PLAN_TOO_LARGE 로 거부된다. 툴에 인자를 새로 뚫지 않는다(spec.md C.3) | M2, M3 |
| **N** | 발화 전 바이트 예산 게이트 | 조립된 번들의 인코딩 길이를 발화 **전에** 재고, 선언된 예산을 넘으면 그 그룹만 `bundle_over_budget` 으로 건너뛴다. 예산 값은 M2에서 실측으로 정한다. **이 게이트 자체를 뮤테이션으로 검산한다** — 예산을 1201 아래로 낮췄을 때 AC가 실제로 빨개지지 않으면 그 게이트는 공허하다(리드 지시, 2026-08-24) | M2, M3 |
| **O** | 미검증 고지 문면 | 멤버십은 **미측정**이라 적는다. 「원리적 불가」와 「읽을 수 없다」는 어느 산출물에도 넣지 않는다. `build_group_write_plan` 이 이미 고친 문면을 반환하므로(`server/groupgen/write.py:412-422`) 002는 그것을 그대로 실어 나르고 새 문장을 짓지 않는다 | M2, M3 |
| **P** | 시트 레지스트리 group 행 | `server/sheets/registry.py` 에 GROUP_ROW 를 **현재 모양 그대로** 추가한다. 열 집합 술어를 쓰고, 핸들러 태그는 툴이다. 모양 변경은 카드 t53 소유이므로 002는 손대지 않는다. t51의 함께 자라는 검사가 동반 4지점을 기계적으로 요구한다 | M3 |
| **Q** | 툴 수 | **1종** `import_lxseq_groups`, action 은 preview 또는 apply(기본 preview). 001의 결정 C와 같은 이유다 — 2종이면 계획을 모델 컨텍스트로 왕복시키고, 두 호출 사이에 콘솔이 바뀌어도 모른다. apply 는 내부에서 계획을 **다시** 만들어 그 시점 풀 상태로 슬롯을 판정한다 | M3 |
| **R** | 쓰기 경로 | `create_arrangement_groups` 핸들러에 내부 ToolCall로 위임. 신규 Lua, `run_commands` 직접 호출, `server/groupgen/write.py` 직접 호출 전부 0건. AST 스캔으로 단언한다 | M3 |
| **S** | 테스트 입력 | 실물 CSV 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv` 가 계약이다. plan-phase에서 복사해 이 카드 커밋에 포함했다. sha256 은 `bc7aced27b0bc06938f2aed2b52c2cff8e2e6ec362ceac154694d5ef64af0172`, 19줄(헤더 1에 데이터 18). 정본은 `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.group.csv` 이며 001의 패치 CSV와 달리 **git 추적 중**이다. 오프라인 테스트와 AC는 사본만 읽는다 | 사본 확인 M0, 소비 M1에서 M3까지 |
| **T** | 슬롯 번호의 권위 (감독 답 2026-08-24) | **권고(가) 채택.** 측정된 빈 슬롯 순열이 시트의 GroupNo 순열과 다르면 **계획을 내지 않고 `slot_number_divergence` 대조표를 보고한다**(REQ-009). 기각(나) 엔진이 잰 슬롯을 그대로 쓰고 매핑표만 보고 — 번호가 밀린 것을 사람이 알아채야 하고 멤버십은 되읽히지 않아 사후 확인 수단이 약하다. 기각(다) `create_arrangement_groups` 에 슬롯 지정 인자 신설 — 001의 「신규 툴 밖 0-diff」를 깬다 | M2, M4 |
| **U** | 입력 파일 수 (감독 답 2026-08-24) | **권고(가) 채택. 인자 둘** — 그룹 시트 바이트와 패치 시트 바이트. 기각(나) 콘솔 픽스처 이름에서 라벨 판독 — 열거가 86에서 19로 잘려 「18대짜리 19대 그룹」이 조용히 영속한다(카드 t46). 기각(다) FID 산술 유추 — 추측이며 실측 우선 원칙에 어긋난다. **레지스트리 모형과의 비대칭은 만들되 그 모양을 못박지 않는다** — 카드 t53이 결정한다(감독 답에 명시) | M3 |

### A.4 열린 결정 — 전부 닫힘 (2026-08-24 감독 착수 승인 · 마커 0건)

두 항목은 결정 T와 U(A.3)로 옮겼다. **둘 다 권고안이 그대로 채택됐다.** 아래는 잔여 메모만 남긴다.

1. **슬롯 번호의 권위 → 결정 T.** 권고(가) 채택. 잔여 메모: 오늘 그룹 풀이 비어 있어(ASSUMPTION-80) 시트 순열과 측정 순열이 우연히 같다. **그래서 REQ-009는 오늘 조건에서 한 번도 발동하지 않는다** — M2 테스트는 반드시 점유가 있는 풀 단면을 넣어 발동시켜야 하고(AC-010), 발동을 못 보고 통과한 것은 그 요구를 검증한 것이 아니다.
2. **입력 파일 수 → 결정 U.** 권고(가) 채택, 인자 둘. 잔여 메모: 시트 종류 레지스트리는 파일 하나를 핸들러 하나로 보내는 모형이므로, 그룹 시트는 첨부 경로로 들어오고 패치 시트는 툴 인자로 들어오는 **비대칭**이 생긴다. 감독 답이 그 비대칭의 모양을 **카드 t53에 위임**했다. 002는 비대칭을 만들되 레지스트리 행의 형식을 바꾸지 않는다(결정 P와 같은 자세).

### A.5 PRESERVE 재확인

| 항목 | 방침 |
|---|---|
| `console/lua/**` 와 `server/safety/**` | 쓰기 경로를 새로 만들지 않으므로 접촉 0건 |
| `server/groupgen/**` | **소비만.** `build_group_write_plan` 을 툴 계층이 부르고 002는 그 반환값을 실어 나른다. 파일 변경 0 |
| `server/spatial/**` | 소비만. `build_spatial_selection_chain` 은 툴 계층 안에서 이미 불린다. 002가 직접 부르지 않는다 |
| `server/orchestrator/tools.py` 기존 핸들러 | `create_arrangement_groups` 본문 0-diff. 신규 툴이 내부 ToolCall로 부른다 |
| `server/sheets/registry.py` | **행 1개 추가만.** 술어 형식, 핸들러 태그 구조, `discriminate` 논리 무변경 |
| `server/web/session.py` | 행 계수기 항목 1개 추가만 |
| `server/tests/test_tools.py` | 툴 수 상수 한 줄 |

---

## B. 마일스톤 M0에서 M4까지

각 마일스톤은 착수 직전 baseline을 직접 잰다. plan-phase 기준선은 기록일 뿐 이월하지 않는다.

### M0 — 기존 계약 확인, 입력 정본 고정 (cycle_type=none, 코드 변경 0)

- **요구와 설계 지시**: `create_arrangement_groups` 의 인자 계약(`groups` 목록의 name과 fids, `topology_partial`, `acknowledged_unread_fids`)과 `build_group_write_plan` 의 반환 필드(steps, unverified, unverified_reason, human_check_commands, fixture_list_truncated)를 run-phase 착수 시점의 소스와 **다시** 대조해 드리프트를 progress.md에 기록한다. 줄번호는 흔들리므로 토큰 앵커로 재확인한다. **DEFAULT_GROUP_PLAN_CAP 값이 여전히 16인지 직접 읽는다** — 결정 M의 배치 분할이 이 값에 걸려 있다. **입력 사본 확인**: `test -f` 로 존재를 확인하고 `shasum -a 256` 이 `bc7aced27b0bc06938f2aed2b52c2cff8e2e6ec362ceac154694d5ef64af0172` 인지, 19줄인지, 헤더가 4열인지 확인만 한다. 없거나 다르면 **명시적 FAIL**이며 건너뛰기가 아니다. 전체 스위트 baseline을 잰다. 열린 결정 2건의 Kickoff 답이 progress.md의 M0 절에 있는지 확인한다.
- **baseline**: 코드 baseline 없음. 사본 존재, sha256 일치, 19줄, 헤더 4열을 직접 확인.
- **뮤테이션**: ① 계약 대조 없이 M1으로 가면 AC-LXSEQ2-001이 죽어야 한다. ② 사본 sha256이 다르거나 사본이 없으면 AC-LXSEQ2-001의 둘째 항이 명시적으로 죽어야 한다(건너뛰기 아님). ③ DEFAULT_GROUP_PLAN_CAP 을 17 이상으로 바꾼 트리에서 AC-LXSEQ2-011의 배치 분할 근거가 무효가 되는지 확인한다 — 무효가 되지 않으면 그 AC는 상한을 재고 있지 않다.
- **파일**: 코드 변경 0. 사본은 plan-phase 커밋에 이미 포함. 기록은 progress.md의 M0 절.
- **AC**: AC-LXSEQ2-001.

### M1 — 파서 (cycle_type=tdd)

- **요구와 설계 지시**: REQ-LXSEQ2-001에서 003까지 구현. `server/lxseq/group_parser.py` — BOM 흡수, 헤더 이름 매칭(위치 금지), 4열 누락 시 파일 단위 실패, 행 검증 5부류(`groupno_not_int`, `groupno_out_of_range`, `groupno_duplicate`, `name_empty`, `name_has_quote`), Members 원문 보존. 순수 함수이며 콘솔과 네트워크 접촉 0. `name_has_quote` 는 `_label_command`(`server/groupgen/write.py:313`)가 작은따옴표와 큰따옴표를 각각 거부하는 것의 **거울**이다 — 툴 계층에서 ValueError로 터지기 전에 파서가 행 단위로 걸러 낸다.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 위치 기반으로 열을 읽으면(열 순서를 섞은 CSV) AC-LXSEQ2-002가 죽어야 한다. ② BOM 흡수를 **두 자리 동시에** 끄면 AC-LXSEQ2-002가 죽어야 한다 — 자리는 `parse_group_csv` 머리와 `_normalize_header` 둘이고 **서로를 가리므로 단일 자리 뮤테이션은 판별력이 없다**(M1 실측: 각각 0건 갈림, 동시 3건 갈림). 단일 자리의 안전은 검사가 아니라 리뷰가 보증한다. ③ 거부 행에서 예외를 던지면 AC-LXSEQ2-003이 죽어야 한다. ④ Members 를 파싱해 멤버십에 쓰면 AC-LXSEQ2-004가 죽어야 한다.
- **파일**: 신규 `server/lxseq/group_parser.py`. 테스트 `server/tests/test_lxseq_group_parser.py`.
- **AC**: AC-LXSEQ2-002, AC-LXSEQ2-003, AC-LXSEQ2-004.

### M2 — 매퍼 (cycle_type=tdd)

- **요구와 설계 지시**: REQ-LXSEQ2-004에서 011까지 구현. `server/lxseq/group_mapper.py` — 패치 레코드에서 라벨별 FID 표를 만들고, 파생 6종의 닫힌 규칙 표를 소유하며, 콘솔 FID 실측과 그룹 풀 단면을 **주입받아** 배치 둘을 낸다. 순서는 기본 12가 먼저다. 슬롯 대조(REQ-009), 개수 교차검증(REQ-007), 번들 바이트 예산(REQ-011)이 전부 여기 산다. 바이트 예산 값은 **이 마일스톤에서 실측으로 정한다** — ALL 의 선택 줄 1201바이트를 재확인하고, 조립된 번들의 인코딩 길이를 실제로 재어 예산을 선언한다. 쓰기 수단의 이름과 명령 문자열은 0건이며 AST 스캔으로 단언한다.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① Name 이 닫힌 어휘 밖인데 건너뛰지 않고 추측하면 AC-LXSEQ2-005가 죽어야 한다. ② 파생 규칙 하나(예: ODD의 홀짝 판정)를 뒤집으면 AC-LXSEQ2-007이 죽어야 한다. ③ 콘솔에 없는 FID를 그룹에 넣으면 AC-LXSEQ2-009가 죽어야 한다. ④ FID 실측이 불완전한데 배치를 내면 AC-LXSEQ2-009가 죽어야 한다. ⑤ 측정 슬롯과 GroupNo 가 어긋나는데 계획을 내면 AC-LXSEQ2-010이 죽어야 한다. ⑥ 배치를 하나로 합치면(18개) AC-LXSEQ2-011이 죽어야 한다. ⑦ **바이트 예산을 1201 아래로 낮췄을 때 AC-LXSEQ2-012가 빨개져야 한다** — 안 빨개지면 그 게이트는 공허하며, 이 뮤테이션이 게이트의 유일한 비공허성 증거다(결정 N, 리드 지시). ⑧ 개수 교차검증을 끄고 Members 개수와 실제 FID 수가 다른 행을 통과시키면 AC-LXSEQ2-008이 죽어야 한다. ⑨ 기본 12종의 FID를 패치 라벨 표가 아니라 FID_BASE 산술(시작 번호에 순번을 더하는 방식)로 만들면 AC-LXSEQ2-006이 죽어야 한다 — 두 방식이 이 쇼파일에서는 같은 값을 내므로, 이 뮤테이션이 「멤버십의 출처가 실제로 라벨 표인가」를 가르는 유일한 지점이다.
- **파일**: 신규 `server/lxseq/group_mapper.py`. 테스트 `server/tests/test_lxseq_group_mapper.py`.
- **AC**: AC-LXSEQ2-005부터 AC-LXSEQ2-012까지.

### M3 — 툴 등재, 레지스트리 행, 동반 4지점 (cycle_type=tdd)

- **요구와 설계 지시**: REQ-LXSEQ2-012에서 016까지 구현. `tools.py` 에 `import_lxseq_groups` 를 순수 추가하고(인자는 Kickoff 답 ②에 따라 확정), `SHEET_KIND_ACTIONS` 에 group 항목을 넣고, 래퍼 스키마의 passthrough 인자와 action enum 을 동조시킨다. `server/sheets/registry.py` 에 GROUP_ROW 를 추가한다 — 열 집합 술어(GroupNo, Name, Members, Purpose)와 툴 태그. `server/web/session.py` 에 행 계수기를 추가한다. preview 는 파싱, 매핑, 풀 읽기, 배치 산출까지 하고 쓰기 0이다. apply 는 같은 계획을 **그 호출에서 다시** 만든 뒤 배치를 순서대로 `create_arrangement_groups` 내부 ToolCall로 위임하고, 첫 배치가 실패하면 멈춘다. 미검증 고지는 하위 툴 반환값을 그대로 전달하며 002가 문장을 새로 짓지 않는다.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 동반 4지점 중 하나를 빼면 t51의 함께 자라는 검사가 죽어야 한다(각 지점을 하나씩 뺀 4회). ② preview 에서 콘솔 쓰기가 한 번이라도 일어나면 AC-LXSEQ2-013이 죽어야 한다. ③ 첫 배치가 실패했는데 둘째 배치를 실행하면 AC-LXSEQ2-013이 죽어야 한다. ④ 미검증 고지 문면에서 unverified 목록을 비우면 AC-LXSEQ2-015가 죽어야 한다. ⑤ 산출물 어디든 「원리적 불가」 문자열을 넣으면 AC-LXSEQ2-015가 죽어야 한다. ⑥ PRESERVE 경로에 변경을 주입하면 acceptance.md D절의 PRESERVE 무변경 조건이 적발해야 한다.
- **파일**: 수정 `server/orchestrator/tools.py`, `server/sheets/registry.py`, `server/web/session.py`, `server/tests/test_tools.py`(상수 1). 테스트 `server/tests/test_lxseq_group_tool.py`.
- **AC**: AC-LXSEQ2-013, AC-LXSEQ2-014, AC-LXSEQ2-015.

### M4 — onPC 실기 확인 (cycle_type=none, 사용자 수행 라이브 세션 1회)

- **요구와 설계 지시**: 사용자가 onPC 2.4.2에서 001의 패치가 이미 들어간 상태(픽스처 86대)로 시작한다. **그룹 풀은 비어 있어야 한다**(ASSUMPTION-80, 실측 childCount 0). 입력 전달은 001의 M4 선례를 따른다 — 로컬 하네스 스크립트가 정본 CSV를 읽어 base64로 핸들러를 직접 호출하며, 서버는 파일 경로를 받지 않는다. ① preview 로 배치 2개(12와 6), 슬롯 대조 결과, 건너뛴 행, 번들 바이트 목록을 확인한다. ② apply 로 배치마다 `status: created` 를 관측한다. ③ `human_check_commands` 를 콘솔에서 실행해 사람이 눈으로 확인한다. ④ 같은 파일로 preview 를 다시 부르면 18슬롯이 전부 점유이므로 `GROUP_SLOT_OCCUPIED` 로 0배치가 된다. ASSUMPTION-80, 81, 82를 판정한다. 제품 코드 변경 0이며 결함이 나오면 M1에서 M3까지 재개방한다(블로커 보고).
- **baseline**: M3 최종 스위트. 콘솔은 픽스처 86대에 그룹 0개.
- **뮤테이션**: ① 점유 슬롯을 대상으로 apply 를 부르는 경로가 있으면 AC-LXSEQ2-016이 죽어야 한다.
- **파일**: 제품 코드 변경 0. 검증 도구는 001의 `server/tools/lxseq_e2e.py` 계열을 따른 신규 스크립트이며 소유는 M4다. 기록은 progress.md의 M4 절(명령, 관측값, 스크린샷 경로).
- **AC**: AC-LXSEQ2-016.

---

## C. 라이브 세션 회계

**1회(M4), 사용자 수행.** 감독 결정 ②("각 단계 onPC 실기 검증")의 직접 요구다. M0에서 M3까지는 전부 오프라인이다. 녹화된 그룹 풀 단면, 가짜 state 포트와 approval 포트, 001의 패치 CSV 사본으로 검증한다. 라이브 AC는 AC-LXSEQ2-016 하나다.

**선행 조건 하나가 사용자 쪽에 있다.** M4는 001의 패치가 콘솔에 이미 들어가 있어야 한다(픽스처 86대). 그룹만 있고 픽스처가 없으면 선택 줄이 아무것도 고르지 못하고, Store 는 빈 프로그래머에 대해 실행되며, 콘솔은 그래도 ok 를 답한다. 멤버십은 되읽히지 않으므로 그 결과는 **적발되지 않는다.** M4 절차의 첫 줄이 픽스처 수 확인인 이유다.

---

## D. 제약

1. **순수 함수 우선.** `server/lxseq/` 는 바이트에서 레코드로, 레코드에서 배치로. 콘솔 읽기는 주입된 포트로만 하고 쓰기는 0이다.
2. **테스트 파일명 고정.** `server/tests/test_lxseq_group_parser.py`, `test_lxseq_group_mapper.py`, `test_lxseq_group_tool.py`.
3. **실패 모드 분리.** 행 거부, 이름 미해결, 개수 불일치, FID 부재, 슬롯 어긋남, 번들 초과를 한 카운터에 합치지 않는다. 여섯은 서로 다른 사실이고, 합치면 어느 것이 일어났는지 보고에서 사라진다.
4. **0건은 비공허성 동반.** "건너뛴 행 0"이나 "쓰기 0"을 단언할 때 스캔 대상이 비어 있지 않음을 함께 단언한다.
5. **AST 스캔.** import 경계와 금지 식별자는 raw grep이 아니라 AST 식별자 스캔으로 잰다(`test_architecture.py` 패턴).
6. **status 재명명 금지.** `create_arrangement_groups` 가 낸 status 문자열을 그대로 전달한다.
7. **문면 금지어와 그 검사 범위.** 하향 이전 단정형 문면은 run 단계 산출물 — `server/lxseq/` 의 코드와 주석, 툴 설명문과 `guidance`, 페이로드 문자열 — 어디에도 넣지 않는다. grep 으로 기계 검사한다(AC-LXSEQ2-015). **검사 범위에서 SPEC 문서 넷은 제외한다** — 금지어를 정의하려면 인용해야 하므로 포함시키면 검사가 구조적으로 0을 못 낸다. 범위를 넓히고 싶어지면 그 순간 검사가 무의미해진다는 것을 먼저 떠올릴 것.
8. **안 갈린 뮤테이션을 「통과」로 적지 않는다.** 뮤테이션을 심었는데 AC가 안 빨개지면 그것은 통과가 아니라 **판별력 없음**이다. 사유를 두 갈래로 갈라 적는다 — **교체 불가**(그 코드를 바꿀 방법이 없다)와 **교체는 되는데 관측 불가**(정상 경로에서 두 선택지의 행동이 같아 어느 AC도 차이를 못 본다). 뒤엣것이 훨씬 흔하다. 판별력 없는 자리는 「그 성질은 리뷰로만 보증됨」으로 등급을 낮춰 적고, 검사가 보증한 것처럼 두지 않는다. 근거: run 레인 실측 2026-08-24 — 15자리 중 14자리가 판정이 옳은데도 관측 불가로 안 갈렸다.
9. **시간 추정 없음.** 우선순위와 순서만 적는다.

---

## E. 후속 SPEC 예약 (이름만, 본 SPEC 범위 아님)

| 단계 | 예약 ID | 입력 |
|---|---|---|
| 3 — 프리셋/FX | `SPEC-COPILOT-LXSEQ-003` | PRESET 시트들과 FX 시트, 기존 FXLIB 및 LOOKLIB 툴 |
| 4 — 시퀀스/큐 | `SPEC-COPILOT-LXSEQ-004` | 곡 파일 CUE-EX CSV, 기존 SONGCUE 및 SCENE 툴 |

> 3단계 착수 메모(본 SPEC 범위 밖, 조사하지 않았다): 프리셋 풀은 `prop COUNT` 가 1000을 답하지만 그것은 **용량이지 내용이 아니다**(RESTORE-001 survey D.8). 프리셋 내용의 판독 가능성은 그룹 멤버십과 같은 사유로 **미측정**이며(같은 문서 A.5), 3단계는 그 등급을 다시 확인하고 출발할 것.

---

## F. 테스트 골격

| 파일 | 소유 AC | 핵심 fixture |
|---|---|---|
| `server/tests/test_lxseq_group_parser.py` | AC-LXSEQ2-002, 003, 004 | 실물 그룹 CSV 사본, 열 순서 섞음, BOM 없음, GroupNo 비정수, 범위 밖, 중복, 빈 이름, 따옴표 든 이름 |
| `server/tests/test_lxseq_group_mapper.py` | AC-LXSEQ2-005부터 012까지 | 001 패치 CSV 사본에서 만든 라벨 표, 닫힌 어휘 밖 이름, 파생 6종 각각, FID 실측(전수와 불완전), 그룹 풀 단면(빈 풀, 부분 점유, 절단), 번들 바이트(예산 안과 밖), AST 스캔 |
| `server/tests/test_lxseq_group_tool.py` | AC-LXSEQ2-013부터 015까지 | `build_toolset` 가짜 포트(호출 기록), 파리티, preview 쓰기 0, apply 배치 순차와 중단, 재실행 시 전량 점유, 미검증 고지 전달, 금지어 grep |
| `server/tests/test_sheet_kind_consumers.py` (기존, t51 소유) | AC-LXSEQ2-016의 배선 부분 | group 행 추가가 동반 4지점을 기계적으로 요구하는지. **이 파일은 002가 만들지 않는다** — 이미 있고, 002는 그 그물에 걸리는 쪽이다 |
| (라이브, 사용자) 신규 검증 도구 | AC-LXSEQ2-016 | onPC 2.4.2, 픽스처 86대, 그룹 풀 0개 |

---

## G. Phase 4 Mode Selection — 사전 평가 (권고, 확정은 progress.md의 F절)

- **tier** M. **scope** 약 9파일(신규 2, 테스트 3, 수정 4에 fixture 1은 plan-phase 커밋에 선반영). **domain** 1(Python 백엔드). **언어** Python과 markdown. **parallel benefit** LOW — M1에서 M2, M3으로 이어지는 데이터 사슬이다.
- 평가: `direct` 미선택(신규 모듈과 툴 배선). `fanout` 미선택(도메인 1). `sweep` 미선택(기계 변환 아님). **`serial` 선택.**
- **Decision: serial** (권고).
- **사용자 접점(Kickoff)**: A.4의 두 결정은 **2026-08-24 감독 착수 승인으로 닫혔다**(결정 T, U). 남은 접점은 M4 라이브 세션 일정 하나다 — 콘솔에 001의 패치 86대가 들어가 있고 그룹 풀이 비어 있어야 한다.
