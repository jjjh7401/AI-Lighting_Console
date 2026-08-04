# SPEC-COPILOT-SPATIAL-001 — 설계 (design)

status: draft (v0.2.0, 2026-08-03) · Tier L · 본 문서는 spec.md 요구의 실현 형상을 소유한다. M0 판정으로 개정될 절은 명시 표기했다.

## §1. 아키텍처 — 두 방향, 한 관문

```
[READ]  콘솔 패치/Layout ──(M0 확정 채널)──▶ 판독 툴 ──▶ server/spatial/ 분석(순수)
                                                             │  행 검출·정렬·신뢰 신호
                                                             ▼
        자연어 공간 한정어 ──▶ 폐쇄 정렬 어휘 매칭 ──▶ 선택 순서 사슬 + 페이저/MAtricks
                                                             │  (좌표는 커맨드에 없다)
                                                             ▼
                                                  run_commands → gate.screen() (기존 단일 관문)

[WRITE] 사용자 명시 요청 ──▶ 프리셋 좌표 계산(순수) ──▶ 원좌표 백업 ──▶ 기록 ──▶ 재조회 검증
                                                        (전부 게이트 관문 경유 + 승인 흐름)
```

- 신규 패키지 `server/spatial/`: 순수 분석만. transport·게이트 import 0(REQ-SPATIAL-013) — `server/looks/busking.py`가 세운 순수 모듈 경계와 동형.
- 툴 표면(안, §F D-4 확정 대기): `get_spatial_context`(READ) / `arrange_fixtures`(WRITE). 콘솔 접촉은 툴 계층에서만.
- executor layout(`server/looks/layout.py`)과는 **이름만 겹치는 다른 축** — 본 SPEC 식별자는 전부 `spatial` 접두(spec.md §A.2).

## §2. READ 데이터 흐름 — 채널 2후보 (M0 판정 대상, plan.md §F D-1)

### §2.1 후보 A — 기존 `prop` 루프 (Lua 무변경)

`build_prop_result`(responder :643)의 경로 해석은 범용이므로 LivePatch 경로 + `posx`가 **오늘의 응답기로** 판독될 수 있다. 성립하면 콘솔 재배포 0·와이어 확장 0.

- 비용: 픽스처당 3~4왕복(x/y/z[+fid 확인]) — 30대면 **90+왕복**. 기존 드릴다운 캡 16(tools.py:173)이 세운 "왕복 예산은 유한하다" 규율과 정면 충돌. 게이트 감사도 왕복당 1건씩 쌓인다.
- 적합 영역: M0 프로브(소수 표적), 소규모 리그, WRITE 검증 재조회(대상 한정).

### §2.2 후보 B — 신규 벌크 동사 (Lua EXTEND)

`spatial <id> <stage-path>` 한 요청 → 픽스처별 `{fid, x, y, z}` 배열 회신. 1~2왕복.

- 비용: 응답기 분기 가산 + `PROTOCOL.md` Revision note + `server/bridge/protocol.py` 빌더 + lupa 테스트 + 재배포 + **M.VERSION 조율**(INTROSPECT-001의 1.6.0 예약 — plan.md §F D-5).
- 회신 예산: §7 산술 — 30대는 절단 경계에 있다. `build_snapshot`의 뒤에서-제거 + `truncated` 패턴 재사용.

**권고**: M0에서 후보 A로 프로브·실측을 마친 뒤, 리그 전대 판독의 실측 왕복 비용이 예산 규율을 깨면 후보 B 채택. **실측 없이 와이어를 늘리지 않는다.**

### §2.3 데이터 스키마 (툴 회신 — 채널과 무관하게 고정)

```
{
  "source": "patch3d" | "layout",          # 출처 명시 (REQ-SPATIAL-002)
  "fixtures": [ {"fid": 11, "name": "PAR 1", "x": -4.5, "y": 0.0, "z": 3.0}, … ],
  "unreadable": [ {"name": "PAR 7", "reason": "property not readable: posx"}, … ],
  "truncated": false, "roundtrip_capped": false
}
```

- `unreadable`은 발명 금지(REQ-SPATIAL-004)의 형상이다 — 부재는 항목으로 존재한다.
- 값 절단(개별 값 축약)과 항목 탈락(`truncated`)은 **다른 신호**다(INTROSPECT 규율 공유).

## §3. 공간 분석 알고리즘 (`server/spatial/` — 순수)

### §3.1 행 검출 — y축 갭 클러스터링

표준 라이브러리 산술만 쓴다(신규 의존성 0 — sklearn 금지). 알고리즘: y값 정렬 → 인접 갭 계산 → **갭 임계**(예: 최대 갭과 중앙값 갭의 비율 기반, 상수는 구현 시 golden으로 고정) 초과 지점에서 행 분할.

- 1×30: y 분산 ≈ 0 → 1행. 3×10: 갭 2개 뚜렷 → 3행. 이 두 golden이 AC-SPATIAL-009의 재료다.
- **저신뢰 판정**: 갭 구조가 뚜렷하지 않으면(비율 임계 미달) 행 수를 단정하지 않고 저신뢰 신호 + 1행 폴백을 **표시된 채로** 반환(REQ-SPATIAL-012).

### §3.2 정렬 어휘 (폐쇄 — REQ-SPATIAL-015의 표적)

> ⚠ **기준: `left`/`right`는 house(객석)다** `[실측, 소급 발견 — spec.md §C.4 · progress.md §E.2.21]`
> MA3 공식 축 의미는 **+x = stage left**(*"Stage right will be negative numbers"*)이고, 무대 관례상
> **stage left/right(배우 기준)와 house left/right(객석 기준)는 정반대**다. x 오름차순은 최소 x부터이므로
> **`left_to_right` = house left → house right = stage RIGHT → stage LEFT** 다. 조명 디자이너가
> *"stage left에서 stage right로"* 라고 하면 **이 정렬의 역방향**을 뜻한다. 한국어 "왼쪽/오른쪽"도 house 기준이다.
> 동작·라이브 판정은 전부 유효하다(P8 관측에서 사용자가 본 "왼쪽"이 최소 x였다) — **낱말이 기준을 말하지 않는 것**이 결함이며,
> 출하된 폐쇄 집합이라 개명하지 않는다. 후속 SPEC은 기준을 이름에 박아 대응한다(GROUPGEN-001 `GEO Stage Right N`).

| 어휘 | 정의 | 한정어 예 | 무대 기준 환산 |
|---|---|---|---|
| `left_to_right` | x 오름차순 (행 내) | "왼쪽에서 오른쪽" | stage right → stage left |
| `right_to_left` | x 내림차순 | "오른쪽에서 왼쪽" | stage left → stage right |
| `center_out` | 행 중심 \|x−cx\| 오름차순 | "가운데부터 바깥으로" | 기준 무관 (대칭) |
| `diagonal` | 행 순 × 행 내 x 순의 사선 결합 | "대각선으로" | 행 순 + 위 좌우 환산 |

- **결정론 2차 키**: 좌표 동률은 fid 오름차순으로 안정 정렬 — "임의"가 아니라 **문서화된 키**다(AC-SPATIAL-010과 §D edge의 화해 지점).
- 다행 리그의 행간 순서: y 오름차순을 기본으로 하고 스키마에 명시. ⚠ `SPATIAL_ROW_ORDER = "y_ascending"`의 서술 *"stage front to back"* 은 **의미는 맞고 낱말이 비표준**이다 — 표준 어휘는 **`Downstage → Upstage`**(+y = upstage). 상수명·동작은 유지하고 어휘만 여기서 정정 기록한다.

### §3.3 왜 MAtricks가 아니라 정렬인가 (그리고 언제 둘을 함께 쓰는가)

MAtricks `X`/`XWings`는 **선택 그리드 위의** 재성형이다 — 그리드 자체가 배치와 무관하면 재성형도 배치와 무관하다. 정렬 선택이 그리드를 배치 순서로 세우고, 그 위에 MAtricks가 얹힌다(예: 3행 리그의 행별 웨이브 = 행 그룹별 선택 + `PhaseFromX/ToX`). 기존 검증 문법(31 룰북)은 전부 재사용, 신규 문법은 선택 사슬뿐이다.

## §4. 연출 발화 형상 (M0 ASSUMPTION-57/58 GO 전제 — 판정 전 가안)

```
ChangeDestination Root
ClearAll
Fixture <fid₁> + Fixture <fid₂> + … + Fixture <fidₙ>     # 정렬 순서의 가산 선택 — M0 판정 대상
Attribute 'Dimmer' At 100
Attribute 'Dimmer' At Phase 0 Thru 360                    # 기존 검증 문법 (31:69)
…
ClearAll
```

- 가산 선택 문법·순서 보존은 **미측정**(ASSUMPTION-57/58) — M0가 두 순서 대조 + 사람 관측으로 판정한다.
- 커맨드 전문에 좌표 실수값 0(AC-SPATIAL-014 정적 검사). 선택 사슬 30줄 ≈ 2s(66ms/line) — 허용 범위, §7.
- 씬/이펙트 계층과의 결합은 **읽기 import + 신규 표면**에서만(REQ-SPATIAL-018) — 기존 `compile_scene` 등은 무변경.

## §5. M0 프로브 사다리 (표적 분리 명단 포함)

**규율**: 프로브별 별도 표적(SCENE M0 승계 결함 금지) · write는 원상복구까지 한 프로브 · 판정 전 대조군 선행 · 판정은 폐쇄 어휘로 §E.2 기록.

| # | 프로브 | 표적 | 내용 | 판정 대상 |
|---|---|---|---|---|
| P1 | READ 대소문자 사다리 | 픽스처 A | `prop` + LivePatch 경로 + `posx`/`PosX`/`POSX`/`Posx` 순차 | ASSUMPTION-53 |
| P2 | READ 날조 대조군 | 픽스처 A | 존재하지 않는 `poszz` 판독 — 실패해야 채널 변별. `ok`면 그 자체를 기록, 값 대조로 대체 | REQ-SPATIAL-026 (c) |
| P3 | READ 전축 | 픽스처 B | 채택 변형으로 x/y/z(+rot* 판독만) — 물리적으로 아는 좌표와 값 대조 | ASSUMPTION-53 |
| P4 | WRITE 채널 (a) | 픽스처 C | 커맨드라인 `Set` 계열 후보로 posz 기록 → 재조회 | ASSUMPTION-54 |
| P5 | WRITE 채널 (b) | 픽스처 D | (P4 실패 시) 일회용 프로브 플러그인 Lua 대입 → 재조회 | ASSUMPTION-54 |
| P6 | WRITE 날조 대조군 + 복구 | 픽스처 C/D | 날조 프로퍼티 기록 시도 → 실좌표 무변화 확인 → **원값 재기록 → 재조회 일치** | REQ-SPATIAL-026 (c)(d) |
| P7 | Layout pool | 레이아웃 1 | children 반복 판독 — 요소·할당·PositionX. 레이아웃 부재 쇼면 `SKIP:` | ASSUMPTION-55 |
| P8 | FID + 선택 순서 (사람) | 픽스처 E~H | `Fixture <fid>` 선택 확인 → 두 순서 + 딤머 페이저 → 방향 관측 → `ClearAll` | ASSUMPTION-57/58 |
| P9 | 예산 실측 | 전대 | 리그 전대 판독의 왕복 수·회신 크기·절단 여부 | ASSUMPTION-60, D-1 재료 |

- **쇼파일 잔여 0 원칙**: 좌표 revert는 재기록으로 가능(`Delete` 불요), 프로그래머 상태는 `ClearAll`. SCENE M0의 "시퀀스 7개 GUI 삭제" 부채를 만들지 않는다. P5의 프로브 플러그인은 Import가 필요하면 사용자 GUI 삭제 1건이 남는다 — 이 비용은 plan.md §F D-2 결정에 포함.
- **표적 공유의 안전 근거**: P1/P2의 픽스처 A 공유는 안전하다 — READ는 콘솔 상태를 점유하지 않는다(SCENE M0의 표적 공유 결함은 대조군 write가 표적 *상태를 점유*한 사례). P6는 독립 프로브가 아니라 **P4/P5 write 왕복의 복구 마감 구간**이다 — "write 프로브는 원상복구까지가 한 프로브"(REQ-SPATIAL-026 (d))의 실현이지 표적 공유 위반이 아니다.

## §6. WRITE 안전 설계

1. **원좌표 백업이 1급 산출물**: 기록 전 대상 전 픽스처의 `(fid, x, y, z)`를 판독·기록. `server/safety/backup.py`의 restore SEND 부재(T-B2)로 showfile 스냅샷은 **되돌릴 수단이 아니다** — 복원은 **원좌표 재기록 번들**로만 성립한다(REQ-SPATIAL-020의 존재 이유).
2. **번들 구조**: `[백업 판독] → 승인 게이트 → [기록] → [재조회 검증]` — 검증 불일치는 명시 실패 + 복원 번들 안내. stop-on-first-failure에서 부분 기록이 남아도 복원 번들이 전 대상을 담으므로 복구 가능(§D edge).
3. **승인 흐름**: 좌표 기록은 쇼파일 변형이므로 기존 승인 카드 경로를 탄다. showfile 백업 규칙 ③(위험 커맨드 직전)이 함께 발동.
4. **범위 봉쇄**: 발화 번들의 fid 집합 == 사용자 명시 대상 집합(정적 단언 가능). rot* 기록 0.
5. **LiveLock**: 백업 판독 포함 전 단계가 제안 강등(콘솔 송신 0).
6. **프리셋 파라미터 계약**: grid/row/circle의 간격(spacing)·원점(origin)·방향(orientation)은 사용자 요청에서 파싱하며, 미지정 시 **문서화된 기본값**을 적용한다. 기본값은 golden 테스트로 고정된다(AC-SPATIAL-018의 간격·원점 포함 판정이 그 재료다).

## §7. 예산 산술 (ASSUMPTION-60 / D-1 결정 재료)

- **회신(벌크 채택 시)**: 픽스처당 `{"fid":nn,"x":-4.5,"y":0.0,"z":3.0}` ≈ 40~50바이트. 30대 ≈ 1200~1500 + 봉투 ≈ **1900 경계 부근** — 절단 설계가 장식이 아니다. 절단 테스트 재료는 반드시 상한 초과 크기로(뮤테이션 규율).
- **왕복(prop 루프 시)**: 30대 × 3속성 = 90왕복. 드릴다운 캡 16의 5.6배 — 캡 규율 위반이 D-1의 결정 압력이다.
- **발화(선택 사슬)**: 30줄 ≈ 2s(66ms/line, 87줄/5.77s 기준선 전재) — 씬 번들 대비 여유.
- **요청(벌크)**: `Plugin "CopilotResponder" "spatial <id> <path>"` ≪ 2048 — 요청 축은 여유.

## §8. 알려진 천장

1. **효과는 사람만 본다** — 선택 순서가 방향을 정하는지(ASSUMPTION-58), 배치 생성의 시각 결과가 맞는지는 기계 채널이 없다. 리포트는 이 한계를 무조건 싣는다(FXLIB `EFFECT_EVIDENCE_NOTICE` 동형 상수 + 상수 동일성 테스트).
2. **GUI 레이아웃 전환 불가** — Layout 기록을 해도 화면에 띄우는 것은 사용자다(research §1.1). WRITE의 가시 피드백은 3D 뷰어(패치 좌표)가 주 채널.
3. **`ok`의 변별력은 축마다 다르다** — SCENE M0 실측. 본 SPEC은 판독·기록 두 축 모두 날조 대조군으로 변별력을 먼저 세운다.
4. **선택 순서의 콘솔측 영속성 미보장** — 선택은 프로그래머 상태이고 `ClearAll`로 사라진다. 매 발화가 순서를 다시 세운다(Gridstore 영속화는 §D 제외·ASSUMPTION-59).
5. **좌표의 신선도** — 판독 후 사용자가 GUI로 패치를 바꾸면 맵은 낡는다. TOCTOU 완화는 범위 밖, 기존 상태 조회 seam의 일반 계약을 상속한다.
