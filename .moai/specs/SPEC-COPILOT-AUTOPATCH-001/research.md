# SPEC-COPILOT-AUTOPATCH-001 — 조사 (research)

status: draft (v0.1.0, 2026-08-05) · Tier L · 읽기 전용 조사. 코드 변경 0.

> **증거 등급**: `[코드]` 이 저장소의 소스에서 직접 확인 · `[문서]` 룰북·벤더 문서 ·
> `[실측]` 라이브 세션 또는 실행 결과 · `[미확정]` 근거 없음, 가정으로 승격 필요.
> 본 조사는 라이브 세션 **이전**에 수행되었다 — `[실측]` 항목은 1단계 세션에서 얻은 것이며,
> 본 SPEC 고유의 실측은 M0가 만든다.

---

## 1. 출처와 범위 확정 경로

`.moai/reports/ma3-copilot-overview.html` §7 P0 항목이 Vectorworks 연계를 3단계로 나눴고,
그중 **2단계**가 본 SPEC이다 `[문서]`:

> 2단계 — 자동 패치 생성: 차이 리포트에서 사람이 승인하면, 라이브 검증이 끝난 Lua 패치 기법
> (`AddFixtures`)으로 부족한 픽스처를 콘솔에 자동 패치합니다.

1단계 `SPEC-COPILOT-VWX-001` §D가 이 범위를 명시적으로 배제하며 후속으로 넘겼다 `[코드]`
(`.moai/specs/SPEC-COPILOT-VWX-001/spec.md` `### Out of Scope — Lua AddFixtures 자동 패치`).

**따라서 본 SPEC의 입력은 확정되어 있다** — 1단계가 이미 만들어 검증까지 끝낸
`missing_in_console` 목록이다. 도면 판독·콘솔 실측을 다시 하지 않는다.

---

## 2. 패치 기법 — 룰북이 정본이고 라이브 검증을 마쳤다

`server/rulebook/assets/v2.4.2/30_plugin_patterns.md` `[문서]`

| 사실 | 위치 |
|---|---|
| 커맨드라인으로 픽스처를 **만들 수 없다**. Lua `AddFixtures` 전용 | `:8-9`, `:13` |
| 정확히 2단계: `deploy_plugin` → `run_commands(["Plugin 'X'"])` | `:13-18` |
| 2번 호출에는 **그 명령 하나만**, **작은따옴표**(큰따옴표 거부) | `:17-18` |
| **`ChangeDestination`/`CD` 절대 금지** — 플러그인 안에서도, `run_commands`로도 | `:20-29` |
| CD를 보내면 패치가 `nil` 반환 · 아무것도 생성 안 함 | `:25-27` |
| 실패 시 정답은 "Patch > Fixtures 편집기를 먼저 열라" 안내 | `:28-29` |
| 필드: `mode`(필수) · `amount`(필수) · `fid` · `idtype` · `name` · `patch` | `:31-38` |
| `mode`는 `Patch().FixtureTypes["…"].DMXModes["…"]` 핸들. 공백 이름은 대괄호 | `:32-34` |
| 성공 시 non-nil, **nil = 실패** | `:34` |
| **모드의 DMX footprint 만큼 간격** | `:37-38` |
| 워크된 예제 — 단일 유니버스, stride 42 | `:40-53` |

이 규약은 "실기에서 통한 문법만 쓴다"는 룰북 원칙 아래 라이브 보정을 거친 것이다 `[문서]`.

**조사가 발견한 공백**: 예제는 **단일 유니버스**(`"1." .. addr`)만 보여준다. `patch` 배열에
**서로 다른 유니버스**를 섞어 넣었을 때의 거동은 문서화되어 있지 않다 `[미확정]`
→ `ASSUMPTION-73`으로 승격, M0 측정 대상.

---

## 3. FID — 이 SPEC의 최대 난제

### 3.1 왜 어려운가 `[코드]`

`AddFixtures`는 `fid`를 요구한다(`30_plugin_patterns.md:35`). 그런데 콘솔의 **기존 FID를 읽을 수 없다**:

- `server/prechk/inventory.py:57` — `PROPERTY_WHITELIST = ("Patch","FixtureType","Mode","Name")`.
  네 개뿐이다.
- `server/prechk/inventory.py:33-37` — FID가 화이트리스트에서 **일부러** 빠진 이유:
  캘리브레이션 쇼파일에서 슬롯과 fixture id가 우연히 일치해서 **어떤 라이브 세션도 올바른 FID 프로브와
  슬롯 프로브를 구별할 수 없다**(`console/lua/PROTOCOL.md:305-324`). 그래서 이 모듈은 모든 것을
  **슬롯 + 이름**으로 키잉하고 fixture id는 `fid_note`(기본 `미확정`)로만 렌더한다(REQ-PRECHK-005).
- `server/prechk/inventory.py:74-76` — `ABSENT_VALUE_TEXTS = {"None"}`가 **`CID`에서 측정**되었다.
  즉 CID는 프로브된 적이 있고 문자열 `"None"`을 답했다 `[실측]`.

### 3.2 틀리면 어떻게 되는가 `[문서]`

룰북이 두 번 경고한다:
- `server/rulebook/assets/v2.4.2/20_korean_terms.md:34-36` — "픽스처의 번호는 stage-patch 슬롯이지
  fixture id가 **아니다** — 번호로 픽스처를 지정하기 전에 `query_state`로 FID를 확인하라."
- `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:203-209` — "**MA3는 조용히 받아들이고**
  그 FID를 가진 엉뚱한 픽스처에 룩을 저장한다."

읽기 전용이던 1단계에서는 이 위험이 **보고 문구**의 문제였다. 쓰기를 하는 2단계에서는
**쇼파일이 망가지는** 문제다.

### 3.3 가능한 경로 3가지 `[미확정]`

| 경로 | 전제 | 위험 |
|---|---|---|
| (a) FID 가독을 실측하고 충돌 사전검사 | `ASSUMPTION-71` GO | 실측이 INCONCLUSIVE로 끝날 가능성이 실재한다(슬롯≠FID 픽스처가 쇼파일에 없으면 판정 불가) |
| (b) 사용자가 빈 FID 범위를 명시 | 사용자가 자기 쇼파일을 안다 | 사용자가 틀리면 조용히 충돌한다 |
| (c) CID / 다른 `idtype` 축 사용 | CID 가독 + MA3 규약 | CID는 `"None"`을 답한 적이 있어 미배정이 기본으로 보인다. 규약 조사 추가 필요 |

**본 SPEC의 선택**: (b)를 **기반**으로 하고 (a)를 **가산 안전망**으로 둔다.
(b) 단독으로도 성립해야 M0가 부정으로 나와도 기능이 존재한다. (c)는 조사 부족으로 이번 범위 밖.

---

## 4. FixtureType · DMXMode 핸들 해석

### 4.1 요구되는 것 `[문서]`

`mode = Patch().FixtureTypes["Robin MMX Spot"].DMXModes["Mode 1"]` —
**콘솔 쇼파일 라이브러리에 그 이름이 정확히 실존해야** 한다(`30_plugin_patterns.md:32-34`).

### 4.2 우리가 가진 것 `[코드]`

- 열거 경로는 존재한다: `server/orchestrator/tools.py:202` `"fixture_types": "Patch/FixtureTypes"`.
- 모드까지의 경로도 언급되어 있다: `server/prechk/patch.py:22` —
  `Patch/FixtureTypes/<t>/DMXModes/<m>/DMXChannels`. 다만 **실측되지 않았다** `[미확정]`
  → `ASSUMPTION-72`.

### 4.3 왜 문자열 비교로 안 되는가 `[코드]`

`server/prechk/patch.py:14-22` — `ASSUMPTION-27`은 **부정**이다. 픽스처에서 자기 채널 점유폭으로
가는 12개 후보 경로를 전부 조사했고 **전부 반증**되었는데, 이유는 `FixtureType`·`Mode`가
**표시 문자열**이기 때문이다. 표시명에서 인덱스를 파싱하는 것은 슬롯을 FID로 읽는 것과 같은 실수다.

### 4.4 Vectorworks 쪽 이름 `[실측]`

1단계 실물 샘플에서 관측된 값:

| VW 컬럼 | 값 예시 |
|---|---|
| `Fixture Type` | `Robe MegaPointe` · `ETC Source Four 26deg` · `Chroma-Q Color Force II 72` |
| `GDTF Fixture` | `Robe Lighting@MegaPointe` · `ETC@Source Four 26deg` · `Chroma-Q@Color Force II 72` |
| `Fixture Mode` | `Mode 1 39ch` · `Dimmer` · `8 Cell RGBW` · `Extended 115ch` · `Mode 4 25ch` |

MA3 라이브러리 이름은 **제3의 표기**일 수 있다. 룰북 예제의 `"Robin MMX Spot"`은 MA3 표기이고
Vectorworks라면 `Robe Robin MMX Spot` 계열로 나올 것이다 `[미확정]`.
→ **퍼지 매칭 + 사용자 확인 + 별칭 저장**이 유일하게 정직한 경로다.

모드 문자열은 더 나쁘다 — `8 Cell RGBW`처럼 **셀 수가 이름에 박혀 있는** 경우가 있지만
그걸 파싱하는 것은 §4.3이 금지한 바로 그 실수다. 점유폭은 **1단계가 읽은 `DMX Footprint` 값**과
**콘솔 라이브러리에서 읽은 채널 수**를 비교해야 하며, 후자가 `ASSUMPTION-72`에 걸려 있다.

---

## 5. 비가역성

`.moai/reports/ma3-copilot-overview.html` §7 P2 `[문서]`:

> 자동 백업(⑤)은 이미 찍히지만 **복원 경로가 없습니다**. 특히 그룹 풀은 콘솔에서 내용을 되읽을 수
> 없어 덮어쓰면 복구 불가라는 것이 라이브에서 확인됐습니다.

패치는 픽스처를 **생성**한다. 잘못 만든 픽스처는 사람이 콘솔에서 지워야 한다.
그래서 본 SPEC의 요구사항 절반 이상이 기능이 아니라 **통제 장치**다 —
드라이런 기본 · 항목 단위 승인 · 멱등 · 검증 읽기 · 자동 보정 금지 · 비가역 경고.

**설계 원칙**: 실패했을 때 손해가 커지는 방향으로 자동화하지 않는다. 막히면 사람에게 돌려준다.

---

## 6. 1단계에서 물려받는 것

`SPEC-COPILOT-VWX-001` v0.1.7 산출물 `[코드]` `[실측]`:

| 물려받는 것 | 무엇을 뜻하나 |
|---|---|
| `missing_in_console` 목록 | 패치 후보. 유니버스 · 주소 · 타입 · 이름을 포함 |
| 멀티셀 접기 | 도면 8행 = **1대**. 실물 샘플에서 8셀 ColorForce가 1대로 접히는 것을 확인 |
| 액세서리 분류 | DMX 소비 액세서리는 **별도 장비**, 비DMX는 **제외** |
| 미패치 제3분류 | 도면 주소 0인 장비는 "콘솔에 없음"과 **다른 부류** — 패치 대상이 아니다 |
| 주소 근거 등급 | `universe_address_direct` vs `absolute_back_calculated`. 역산된 주소로 패치할 때 위험도가 다르다 |
| 다중 시스템 미매핑 | 콘솔 조인 자체가 미수행 → 패치 입력이 성립하지 않는다 |
| `DMX Footprint` | 모드 점유폭 대조의 설계 측 근거 |
| 스코프 한정 | 판독 탈락이 있었으면 리포트가 그 사실을 들고 있다 |

**주의**: 주소 근거가 `absolute_back_calculated`인 항목은 "Universes pane이 기본 연속 512블록"이라는
**선언된 전제** 위에 있다. 그 전제가 틀리면 **엉뚱한 유니버스에 패치**된다.
→ 설계에서 이 등급을 승인 화면에 노출할지 판단해야 한다(design.md §5 슬롯 D).

---

## 7. 재사용 계약과 PRESERVE 합집합

| 재사용 | 진입점 | 계약 |
|---|---|---|
| 배포 안전 파이프라인 | `server/orchestrator/tools.py:1266` `deploy_plugin` | 컴파일 + 정적 스캔 + 사람 리뷰 |
| 콘솔 쓰기 단일 통로 | `run_commands` → `bundle_gate.screen()` | AST 스캔이 우회를 금지(`server/tests/test_prechk_tool.py:330-343`) |
| 인벤토리 읽기 | `server/prechk/inventory.py:348` `read_inventory` | 검증 읽기에 재사용. **변경 금지** |
| 주소 정규화 | `server/prechk/patch.py:100-147` `normalize_address` | 두 정수 아니면 없음. 기본값 날조 금지 |
| 판정 평가 | `server/prechk/patch.py:684` `evaluate_patch` | 검증 읽기 판정에 재사용 |
| 타입 라이브러리 열거 | `server/orchestrator/tools.py:202` | 후보 집합 |
| 툴 등록 절차 | `server/preshow/TOOLS_REGISTRATION.md` | 5지점 + dispatch 검증 |
| 아키텍처 경계 | `server/tests/test_architecture.py:33,49` | `server.bridge`·`pythonosc` import 금지 |

**PRESERVE 합집합** — 1단계가 잠근 것을 그대로 승계한다:
`console/lua/**` · `server/safety/**` · `server/prechk/**`(8파일 전량) · `server/paperwork/**` ·
`server/looks/**`.

`server/vwx/**`는 1단계가 만든 것이고 본 SPEC이 확장한다 — PRESERVE가 아니지만
**공개 payload 계약은 무변경**이다(AC-AUTOPATCH-025).

---

## 8. 조사가 남긴 미확정 (ASSUMPTION으로 승격)

| # | 미확정 | 승격 |
|---|---|---|
| 1 | FID가 프로퍼티로 읽히는가 | `ASSUMPTION-71` |
| 2 | `Patch/FixtureTypes`가 DMXModes·채널 수까지 드릴다운되는가 | `ASSUMPTION-72` |
| 3 | `patch` 배열에 다중 유니버스를 섞을 수 있는가 | `ASSUMPTION-73` |
| 4 | 패치 직후 재조회에서 신규 픽스처가 관측되는가 | `ASSUMPTION-74` |
| 5 | Patch 편집기 미개방 상태를 사전 감지할 수 있는가 | `ASSUMPTION-75` |

다섯 건 모두 **M0 라이브 세션**이 판정한다. 판정 전에는 M2·M3·M6의 설계를 확정하지 않는다 —
`SPEC-COPILOT-PRECHK-001`의 probe-before-authoring 규율을 그대로 따른다.
