# SPEC-COPILOT-AUTOPATCH-001 — 설계 (design)

status: draft (v0.1.1, 2026-08-05) · Tier L · 설계 슬롯 5건 전부 종결 · 미결 0 · 독립 plan-audit 1회차 지적 반영

---

## §1. 의도

1단계가 "무엇이 다른가"를 답했다. 본 설계는 **"그중 사람이 고른 것만, 되돌릴 수 없다는 걸 알면서,
정확히 그것만 만든다"** 를 구조로 만든다.

설계의 중심은 기능이 아니라 **통제 흐름**이다. 되돌리기가 없는 시스템에서 자동화의 가치는
"사람이 판단할 것을 정확히 좁혀 주는 것"이지 "사람 없이 하는 것"이 아니다.

---

## §2. 변경 표면

### §2.1 신규 · 변경 파일

| 파일 | 신규/변경 | 역할 |
|---|---|---|
| `server/vwx/patchplan.py` | 신규 | 후보 정규화 · 선택 · FID 배정 · 주소 계획 |
| `server/vwx/typemap.py` | 신규 | 라이브러리 열거 · 퍼지 매칭 · 별칭 저장 |
| `server/vwx/luagen.py` | 신규 | `AddFixtures` Lua 소스 생성 (CD 어휘 부재를 구조로 보장) |
| `server/vwx/apply.py` | 신규 | 배포 · 실행 · 멱등 · 검증 읽기 오케스트레이션 |
| `server/vwx/verdicts.py` | 신규 | 본 SPEC 판정 어휘 레지스트리 (`server/prechk/verdicts.py`는 PRESERVE) |
| `server/vwx/report.py` | 변경 | 패치 결과 보고 절 추가 (1단계 출력 계약 무변경) |
| `server/orchestrator/tools.py` | 변경 | 신규 툴 `apply_vectorworks_patch` 5지점 등록 |
| `server/tests/test_autopatch_*.py` | 신규 7종 | plan.md §E 테스트 골격 |

**변경하지 않는 것**: `server/prechk/**` · `server/safety/**` · `console/lua/**` ·
`server/paperwork/**` · `server/looks/**` · `server/vwx/{reader,columns,address,rig,diff}.py`의 공개 계약.

### §2.2 모듈 배치 — 왜 새 패키지가 아닌가

입력이 1단계 산출물이고 타입·주소·근거등급 어휘를 공유한다. 새 패키지를 만들면 그 어휘가 두 벌이 되고,
1단계가 어휘를 바꿀 때 두 곳을 고쳐야 한다. `server/vwx/` 안에 두면 어휘가 한 벌로 유지된다.
(결정 A)

### §2.3 툴 등록 지점

`server/preshow/TOOLS_REGISTRATION.md`의 5지점:
① `server.vwx` import · ② `TOOL_NAMES`에 `apply_vectorworks_patch` ·
③ `build_toolset` 안 핸들러 def · ④ `ToolDefinition` append · ⑤ `handlers` dict.
검증은 **dispatch로** 한다(dict 조회 금지).

파라미터 스키마(초안):

```
{
  "report": object,            # 1단계 리포트 payload (필수)
  "selected": array[string],   # 항목 식별자. 생략 시 빈 배열 = 대상 0건
  "fid_range": {"start": int, "end": int},   # 생략 시 실행 거부
  "type_aliases": object,      # VW 이름 -> 콘솔 라이브러리 이름 (선택)
  "dry_run": boolean           # 생략 시 true
}
```

리그 식별자(슬롯 등)는 스키마에 넣지 않는다(PRECHK 관례 계승).

### §2.4 PRESERVE 위반 0 표

| 대상 | 본 SPEC이 하는 일 | 위반 없음 근거 |
|---|---|---|
| `server/prechk/inventory.py` | `read_inventory` 호출만 | 검증 읽기는 소비. 화이트리스트 확장 안 함 |
| `server/prechk/patch.py` | `normalize_address` · `evaluate_patch` 호출만 | 주소 계약 재사용 |
| `server/prechk/verdicts.py` | **건드리지 않음** | 신규 어휘는 `server/vwx/verdicts.py`에 |
| `server/safety/**` | 통과만 | `run_commands` 경유 |
| `console/lua/**` | 무접촉 | 플러그인 소스는 런타임 생성물이지 저장소 자산이 아니다 |

---

## §3. 흐름

```
1단계 리포트
   │
   ├─[거부] diffs.performed == false  또는  multi_system_mapping_absent
   ▼
후보 정규화 (patchplan)  ── 기본 선택 0건
   │
   ▼  사용자 선택 + fid_range
FID 배정 (patchplan)
   ├─ ASSUMPTION-71 GO   → 충돌 사전검사 → 충돌 항목 제외
   └─ 부정/INCONCLUSIVE  → 사전검사 descope + 축소 명시
   │
   ▼
타입·모드 해석 (typemap)   ── Patch/FixtureTypes 열거 [읽기]
   ├─ 부재 → 항목 하드 스톱 (GDTF 임포트 선행 필요)
   └─ ASSUMPTION-72 GO → 점유폭 대조 / 부정 → descope
   │
   ▼
주소 계획 (patchplan)      ── 도면 주소 우선 · 점유폭 간격 · 점유 주소 제외 [읽기]
   │
   ▼
Lua 생성 (luagen)          ── CD 어휘 없음
   │
   ├───────────── dry_run(기본) ──→ 소스 전문 + 대상 표 + 비가역 경고 ──→ 끝 [쓰기 0]
   │
   ▼  명시 실행
멱등 재조회 (apply)        ── 이미 존재하는 항목 건너뜀 [읽기]
   │
   ▼
deploy_plugin              ── 컴파일 + 정적 스캔 + 사람 리뷰
   │
   ▼
run_commands(["Plugin 'X'"])   ── 단일 명령 · bundle_gate.screen()
   │
   ▼
검증 읽기 (apply)          ── precheck_patch 재조회 · 건별 확인
   │
   ├─ 일치      → 성공 보고
   ├─ 불일치    → 구조화 보고 · 자동 보정 0
   └─ 0건 생성  → "Patch > Fixtures 편집기를 먼저 열라" 안내
```

**드라이런과 실행의 유일한 차이**는 점선 아래 구간의 실행 여부다. 드라이런은 그 위 전부를 실제로
수행하므로(읽기만) 소스와 표가 **실행될 것과 동일**하다 — "드라이런은 됐는데 실행은 다르더라"가
발생하지 않는다.

---

## §4. 위험 검토

| # | 위험 | 완화 | 잔여 |
|---|---|---|---|
| R1 | FID 충돌로 엉뚱한 픽스처를 덮음 | 사용자 범위 강제 + (GO 시) 충돌 사전검사 + 배정 전수 나열 + **(부정 시) REQ-AUTOPATCH-026의 구조화된 별도 확인 필드** | **수용된 잔여 위험, 사인오프 필요.** 부정 분기에서는 멱등 검사(주소·타입·모드)도 검증 읽기(유니버스·주소·타입)도 FID 충돌을 탐지하지 못한다 — 사용자가 준 범위가 틀리면 막을 수단이 없다. 그래서 산문 경고가 아니라 **건별 감사 가능한 확인 필드**를 요구한다 |
| R2 | 라이브러리 이름 오매칭으로 다른 장비를 패치 | 열거 기반 후보 + 퍼지 + **사용자 확인** + 별칭 저장 | 사용자가 잘못 확인하면 막을 수 없다. 확정 내역을 드라이런 표에 노출 |
| R3 | 되돌릴 수 없음 | 드라이런 기본 · 항목 승인 · 멱등 · 검증 읽기 · 자동 보정 0 | 생성물 제거는 사람 몫. 경고로만 대응 |
| R4 | 멀티셀 모드 오선택으로 주소 계획 붕괴 | 점유폭 대조(GO 시) + 불일치 사전 제시 | `ASSUMPTION-72` 부정이면 사용자 확인 단독 |
| R5 | 역산된 주소(`absolute_back_calculated`)로 엉뚱한 유니버스에 패치 | **슬롯 D** — 승인 화면에 근거 등급 노출. **강제 경로**: REQ-AUTOPATCH-003이 `address_basis`를 드라이런 표 필수 열로 규정하고 AC-AUTOPATCH-004③이 역산 전제 문구를 비공허하게 검증한다(설계 주장이 요구로 승격됨) | 전제가 틀린 쇼파일에서는 근본적으로 막을 수 없다 |
| R6 | 드라이런이 실제로는 쓰는 경로 | `RecordingExecutionPort`로 쓰기 0건 검증 + 비공허 대조군 | 없음 |
| R7 | 플러그인 무오류 종료를 성공으로 오인 | 검증 읽기 필수 | `ASSUMPTION-74` 부정 시 "확인 불가" 보고 |
| R8 | **미리보기와 실행이 구조적으로 묶여 있지 않다** — 호출자가 드라이런 없이 첫 호출부터 `dry_run=false`로 실행할 수 있다 | 없음(구조적 결속 미도입) | **수용된 잔여 위험.** 승인은 툴 호출 경계가 아니라 **오케스트레이터/사람 대화 계층**에서 강제되며, 이는 이 저장소의 다른 쓰기 툴(`run_commands`·`deploy_plugin`)과 동일한 패턴이다. 툴 호출 수준의 plan-hash/preview-token 결속은 도입하지 않는다 — 이 SPEC만 다른 규약을 쓰면 일관성이 깨지고, 게이트는 이미 `bundle_gate`가 담당한다 |

---

## §5. 설계 슬롯

| 슬롯 | 질문 | 결정 | 상태 |
|---|---|---|---|
| A | 드라이런과 실행을 별도 툴로 나눌 것인가 | **아니다.** 한 툴 + `dry_run` 인자. 승인 상태가 툴 경계를 넘어 흐르지 않게 한다 | 종결 |
| B | 신규 판정 어휘를 어디에 둘 것인가 | `server/vwx/verdicts.py` 신규. `server/prechk/verdicts.py`는 PRESERVE라 확장 불가 | 종결 |
| C | CD 금지를 어떻게 보장할 것인가 | 사후 문자열 검사가 아니라 **생성 어휘에 애초에 없게** 한다. 생성기는 `AddFixtures` 호출만 만들 수 있는 좁은 API를 노출하고, 자유 문자열 삽입 지점을 두지 않는다. 문자열 스캔은 **이중 안전망**으로만 둔다 | 종결 |
| D | 역산된 주소(`absolute_back_calculated`)를 패치에 쓸 것인가 | **쓴다. 단 승인 화면에 근거 등급을 노출**하고, 리그에 역산이 하나라도 섞이면 전제 문구를 승인 화면에 함께 띄운다. 금지하면 절대주소 단독 파일 사용자가 2단계를 통째로 못 쓴다 — 1단계가 같은 이유로 역산을 채택했고 그 선례를 따른다 | 종결 |
| E | 실패한 항목이 있을 때 나머지를 진행할 것인가 | **진행한다.** 항목 단위 승인이므로 항목 단위 실패가 자연스럽다. 단 실패·건너뜀·성공을 **건별로** 보고하고, 부분 성공을 전체 성공으로 적지 않는다 | 종결 |

**미결 0건.** 명료화 마커(clarification marker) 0건 — 본 SPEC의 어느 아티팩트에도 그 마커가 없다.

---

## §6. 테스트 설계

### §6.1 픽스처

- 1단계 실물 픽스처를 재사용한다(`server/tests/fixtures/vwx/`) — 새 도면 픽스처를 만들지 않는다.
- 콘솔 라이브러리 더블: `Patch/FixtureTypes` 열거 + DMXModes 드릴다운을 흉내내는 `RigPort` 확장.
  `ASSUMPTION-72` 부정 분기를 위해 **드릴다운이 실패하는 더블**도 함께 둔다.
- `RecordingExecutionPort`로 쓰기 호출을 전수 기록한다.

### §6.2 AC → 테스트 파일

| AC | 파일 |
|---|---|
| 002 · 003 · 004 | `test_autopatch_candidates.py` |
| 005 · 006 · 007 · 008 | `test_autopatch_fid.py` |
| 009 · 010 · 011 · 012 | `test_autopatch_types.py` |
| 013 · 014 · 015 · 016 | `test_autopatch_lua.py` |
| 017 · 018 · 019 | `test_autopatch_execute.py` |
| 020 · 021 · 022 | `test_autopatch_verify.py` |
| 023 | `test_autopatch_tool.py` |
| 024 · 025 | 게이트 커맨드 + 기존 `test_vwx_*.py` 전수 |
| 001 · 026 | 라이브 세션 (`progress.md` §E.2 기록) |

### §6.3 비공허성 대조군 (필수 8건)

| 주장 | 심을 것 |
|---|---|
| 도면 재판독 0건 | 판독 호출을 심어 기록기가 잡는지 |
| 추정 FID 배정 0건 | 최대슬롯+1 로직 |
| 슬롯 참조 0건 | `record.slot` 참조 |
| 동등 확정 0건 | 문자열 `==` 확정 경로 |
| 표시문자열 파싱 0건 | 모드명에서 숫자 추출 |
| **CD 0건** | `ChangeDestination`을 담은 가짜 산출물 |
| 드라이런 쓰기 0건 | 실행 경로에서 같은 기록기가 쓰기를 잡는지 |
| PRESERVE 0-diff | PRESERVE 대상에 변경을 심었다 되돌리기 |

대조군 없는 "0건" 주장은 인수 불가다(acceptance.md §A).

---

## §7. 안티패턴 — 하지 말 것

1. **`ChangeDestination`을 "필요할 때만" 넣기** — 룰북이 무조건 금지한다. 조건부 예외 없음.
2. **`run_commands`에 플러그인 실행과 다른 명령을 함께 보내기** — 그 배열은 길이 1이다.
3. **표시 문자열에서 모드 채널 수 파싱** — `ASSUMPTION-27` 부정이 이미 반증했다.
4. **슬롯을 FID로 쓰기** — 룰북이 두 번 경고했다.
5. **플러그인 무오류 종료를 성공으로 간주** — `AddFixtures`는 실패 시 `nil`을 반환할 뿐이다.
6. **실패 시 자동 재시도·자동 보정** — 되돌릴 수 없는 쓰기에서 손해를 키운다.
7. **도면 주소가 점유되었을 때 빈 주소로 옮겨 붙이기** — 사람이 결정할 일이다.
8. **드라이런에서 콘솔에 쓰기** — 읽기만 허용된다.
9. **`server/prechk/`를 고쳐서 FID를 읽게 만들기** — PRESERVE이며, 화이트리스트가 좁은 데는 실측된 이유가 있다.
10. **부분 성공을 성공으로 보고** — 건별 보고가 정본이다.

---

## §8. 교차 참조

- 1단계: `.moai/specs/SPEC-COPILOT-VWX-001/{spec,design,progress}.md`
- 패치 기법: `server/rulebook/assets/v2.4.2/30_plugin_patterns.md:11-53`
- FID 금지 근거: `server/prechk/inventory.py:33-37,57` · `console/lua/PROTOCOL.md:305-324`
- 표시문자열 반증: `server/prechk/patch.py:14-22`
- 배포 파이프라인: `server/orchestrator/tools.py:1266`
- 경계 스캔: `server/tests/test_prechk_tool.py:330-343` · `server/tests/test_architecture.py:33,49`
- 툴 등록: `server/preshow/TOOLS_REGISTRATION.md`
- 보고 교리: `.moai/specs/SPEC-COPILOT-OVERLAP-001/design.md:148`
