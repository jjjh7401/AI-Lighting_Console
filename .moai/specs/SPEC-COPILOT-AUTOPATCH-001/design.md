# SPEC-COPILOT-AUTOPATCH-001 — 설계 (design)

status: draft (v0.1.5, 2026-08-06) · Tier L · 설계 슬롯 5건 전부 종결 · 미결 0 · plan-audit 1~9회차 지적 반영 · §6.2 폐지(acceptance.md 단일 출처화)

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
| `server/vwx/apply.py` | 신규 | **[v0.1.3]** 실행 전달(사람) · 멱등 · 검증 읽기 오케스트레이션. **패치 실행 발화 없음** |
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
  "fid_range_visually_confirmed_empty": boolean,
                               # REQ-AUTOPATCH-026 / AC-AUTOPATCH-027.
                               # ASSUMPTION-71 부정·INCONCLUSIVE 분기에서 **필수**,
                               # 생략 시 실행 거부. GO 분기에서는 요구하지 않는다.
                               # `selected`·`dry_run` 과 **독립된 필드**여야 한다 —
                               # 항목 선택이나 dry_run=false 가 이 확인을 함축하지 않는다.
  "type_aliases": object,      # VW 이름 -> 콘솔 라이브러리 이름 (선택)
  "names": object,             # [M7] 후보 식별자 -> 생성할 픽스처 이름.
                               # 없으면 그 항목은 `fixture_name_missing`으로 **제외**된다 —
                               # 이 계층은 이름을 지어내지 않는다. 도면에 픽스처 이름 열이
                               # 없어서(1단계 `DesignedFixture`에 대응 필드 부재) 호출자가
                               # 줘야 하며, 이것 없이는 툴이 구조적으로 아무것도 만들지 못한다.
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
   ▼  명시 전달 요청 (dry_run=false)
멱등 재조회 (apply)        ── 이미 존재하는 항목 건너뜀 [읽기]
   │
   ▼
실행 전달 (apply)          ── 검토용 Lua 소스 + 실행 절차를 **사람에게 제시** [쓰기 0]
   │                          ※ [v0.1.3] 서버는 패치를 실행하지 않는다 —
   │                            ASSUMPTION-76 NEGATIVE (progress.md §E.2 M0 5차).
   │                            deploy_plugin / run_commands(["Plugin 'X'"]) 자동 발화 **0건**.
   │
   ▼  **G2** 사람이 콘솔에서 실행 (실행 버튼은 사람이 누른다)
   │     ※ **G1**은 이 화살표 **바로 위의 '실행 전달' 칸**이다 — 전달물이 나온 경우에만
   │       성립하므로 드라이런 종단 가지(위 점선)는 G1이 아니다(AC-AUTOPATCH-026① 경계).
   │       아래가 **G3**(서버 검증), 세션 후 생성물 제거·확인 기록이 **G4**다.
   │       M8은 이 넷을 **관문별로 나눠 판정**한다(AC-AUTOPATCH-026 v0.1.5)
   │
   ▼
검증 읽기 (apply)          ── precheck_patch 재조회 · 건별 확인
   │
   ├─ 일치      → 성공 보고
   ├─ 불일치    → 구조화 보고 · 자동 보정 0
   └─ 0건 생성  → 실행 여부·절차 재확인 안내 (편집기 안내는 v0.1.3에서 근거를 잃었다 —
                  ASSUMPTION-75 NEGATIVE · ASSUMPTION-76 NEGATIVE)
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

**폐지(round5 N7/N8/N10, `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round5.md` 권고).**
이 절은 `acceptance.md` 각 AC의 "검증 방법" 필드를 손으로 복사한 사본이었다 — 사본이 둘이면
한쪽만 고치는 편집마다 드리프트가 생긴다(round3~5에 걸쳐 4연속 결함으로 실증됨). **유일한
출처는 `acceptance.md`의 각 AC 항목 자체의 "검증 방법" 줄이다.** 테스트 파일을 알아야 하면
거기서 읽는다 — 이 표를 복원하지 않는다.

### §6.3 비공허성 대조군 (필수 **10건** — v0.1.4 round7 반영에서 8 → 10)

| 주장 | 심을 것 |
|---|---|
| 도면 재판독 0건 | 판독 호출을 심어 기록기가 잡는지 |
| 추정 FID 배정 0건 | 최대슬롯+1 로직 |
| 슬롯 참조 0건 | `record.slot` 참조 |
| 동등 확정 0건 | 문자열 `==` 확정 경로 |
| 표시문자열 파싱 0건 | 모드명에서 숫자 추출 |
| **CD 0건** | `ChangeDestination`을 담은 가짜 산출물 |
| **쓰기 0건(두 모드 모두)** | **`server/vwx/` 사본에 콘솔 쓰기를 되살려 심고 같은 기록기가 잡는지** (AC-AUTOPATCH-019②. v0.1.3 전에는 "실행 경로에서 잡는지"였으나 반자동 모델에서 실행 경로가 쓰기를 하지 않아 성립 불가 — round7 N16) |
| **[신설 v0.1.4/round7] 패치 실행 발화 0건** | 실행 발화를 되살린 모듈 사본에서 `RecordingExecutionPort`가 잡는지 (AC-AUTOPATCH-015②③) |
| **[신설 v0.1.4/round7] 별도 배포 호출 0건** | 우회 배포를 심은 모듈 사본에서 잡히는지 (AC-AUTOPATCH-017①) |
| PRESERVE 0-diff | PRESERVE 대상에 변경을 심었다 되돌리기 |

대조군 없는 "0건" 주장은 인수 불가다(acceptance.md §A · §F 항목 7).

**이 표의 범위 (v0.1.4 명시)**: 위 10건은 **구조적·설계 수준**의 대조군 목록이다.
`acceptance.md` §F 항목 7이 요구하는 것은 **모든 "0건" 주장 AC 항목에 대조군이 붙어 있을 것**이며,
그 강제는 **각 AC 자신의 "기대 결과" 줄**에서 이뤄진다(단일 출처 — §6.2를 폐지한 것과 같은 이유로
여기에 사본을 두지 않는다). v0.1.4에서 AC-007③·013③·**014③(a)**·016③·017②·021② **6건**에
대조군을 추가해
**§F 항목 7이 전수 성립**하도록 맞췄다(round8 감사 N37 + **round9 감사 N47** — N37의 5건만으로는
부족했고 AC-014③(a)가 마지막 반례였다).

---

## §7. 안티패턴 — 하지 말 것

1. **`ChangeDestination`을 "필요할 때만" 넣기** — 조건부 예외 없음. **[v0.1.3 근거 교체]**
   근거는 룰북의 "CD가 실패 원인"이 **아니다**(그 인과는 반증됐다 — research.md §2 주석).
   실측 근거는 **CD가 플러그인의 목적지에 아무 효과가 없다**는 것이며, 따라서 생성 어휘에
   둘 이유가 없다(REQ-AUTOPATCH-017의 새 근거).
2. **서버가 패치 실행을 스스로 발화하기** — **[v0.1.3 교체]** 이전 판은 "`run_commands` 배열은
   길이 1이다"였으나 그 요구는 폐기됐다(REQ-AUTOPATCH-018 · AC-AUTOPATCH-015④).
   반자동 모델에서 서버는 패치를 실행하지 않는다. 서버가 어떤 이유로든 콘솔에 문장을 보낼 때는
   **REQ-AUTOPATCH-021의 단일 통로**(`run_commands` → `bundle_gate.screen()`)를 지킨다.
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
