# 인수 기준 — 쓰기 경로 무결성

base `origin/main` = `b1a630e` · 판정 원칙: **성공은 구조에 걸고 라이브는 보조 증거다**(REQ-WRITEGATE-014).

## A. 시나리오 (Given–When–Then)

### 시나리오 1 — 요청하지 않은 좌표 기록에 사람이 끼어든다

- **Given** 게이트가 승인 포트와 백업 매니저를 갖고 정상 가동 중이다.
- **When** 좌표 기록 번들(`Set Fixture 11 Posx '-3.5'` 외 5줄)이 스크리닝에 들어간다.
- **Then** 번들이 `risky`로 분류되고 승인 카드 1건이 뜨며 `before_risky_execution()`이 1회 호출된다. 승인 이전 콘솔 송신은 **0건**이다.

### 시나리오 2 — 거부가 곧 답이다

- **Given** 승인 포트가 거부를 반환한다(또는 승인 채널이 아예 없어 `DenyAllApprovalPort`가 기본값이다).
- **When** 같은 번들이 들어온다.
- **Then** 콘솔 송신 0건, `status="rejected"`, 그리고 SPATIAL의 복원 번들이 회신에 그대로 실린다. 쇼파일 잔여 0.

### 시나리오 3 — 손으로 쓴 줄도 같은 판정을 받는다

- **Given** 모델이 조립기를 거치지 않고 `run_commands`에 직접 커맨드라인을 넣는다.
- **When** 그 줄이 `Set Fixture 1 Thru 18 Posz '5.0'`(범위 기록 — 조립기는 만들 수 없는 형태)이다.
- **Then** 동일하게 `risky`로 분류되어 카드가 뜬다. 발화 주체는 판정에 영향을 주지 않는다.

### 시나리오 4 — 인용부호 안에 숨겨도 잡힌다

- **Given** 매크로 저작 커맨드가 명령 텍스트를 인용된 프로퍼티 값으로 영속화한다.
- **When** 그 값이 `Set Fixture 11 Posx '5.0'`이다.
- **Then** 기존 재귀 분류가 이를 잡아 `risky`로 판정한다 — 바깥 동사가 무엇이든 무관하다.

### 시나리오 5 — 프로그래머 상태는 방해받지 않는다

- **Given** 연출 경로가 MAtricks로 페이저 위상을 건다.
- **When** `Set Selection MAtricks 'PhaseFromX' 0`이 발화된다.
- **Then** 분류는 `safe`로 **불변**이고 카드는 뜨지 않는다. 인용 토큰은 키워드 매칭 대상이 아니다.

### 시나리오 6 — 측정 코퍼스는 문면 그대로다

- **Given** 21 시나리오 측정 코퍼스가 *"non-risky verbs only"*를 불변식으로 선언한다.
- **When** 폐쇄집합 개정 후 M6a 목 런을 돌린다.
- **Then** `gate_anomalies == {}`이고 `corpus.yaml`의 byte-diff는 **0**이다. 대표 작업 10종 중 교체된 것은 없다.

### 시나리오 7 — 넓힌 예외는 여전히 좁다

- **Given** 트립와이어에 `blacklist.yaml` 항목 1건이 비준 추가됐다.
- **When** 누군가 `server/safety/` 아래 **다른** 파일을 건드리거나, `blacklist.yaml`에서 `version: 1` 외의 행을 지운다.
- **Then** 트립와이어는 **여전히 실패한다**. 그랜트는 판정 방식을 바꾸지 않고 허용 범위만 1건 넓힌다.

## B. 인수 기준

### AC-WRITEGATE-001 — 패치 쓰기의 risky 분류

**When** 픽스처 패치 쓰기 커맨드가 게이트 스크리닝에 들어가면, the 게이트 **shall** `risky=True`로 분류한다.

- 대상 요구: REQ-WRITEGATE-001 · 002 · 004
- **통과 판정**: 단위 — 아래 전건이 `risky=True` · `category="blacklisted"` · `matched_entry`가 신규 엔트리를 지목:
  `Set Fixture 11 Posx '-3.5'` / `Set Fixture 11 Posx -3.5`(부호 소실형) / `Set Fixture 11 Posx - 3.5`(무동작형) / `Set Fixture 11 Pos -3.5`(3자 축약) / `Set Fixture 1 Thru 18 Posz '5.0'`(범위) / `Set Fixture 11 Rotx '90.0'`(방향축) / `Set Fix 11 Posx '1.0'`(동사 축약)
- **뮤테이션**: `blacklist.yaml`에서 신규 엔트리 1건을 제거하면 전건이 RED여야 한다. **변이 표적은 분류 규칙 자체**이며 테스트 리그가 아니다.
- 비공허성: 개정 **전** base에서 같은 단정이 전건 RED임이 확인돼야 한다(현재 `safe`이므로 성립 — `research.md` §1).

### AC-WRITEGATE-002 — 승인 카드 + 백업 규칙 ③

**When** 좌표 기록 번들이 risky로 분류되면, the 게이트 **shall** 승인 카드를 띄우고 `before_risky_execution()`을 발동한다.

- 대상 요구: REQ-WRITEGATE-002 · REQ-SPATIAL-020(규칙 ③ 연동 절) · REQ-SPATIAL-024(승인 흐름 절)
- **통과 판정**: 단위 — 모의 백업 훅으로 `before_risky_execution()` 호출 **1회** 확인 + `ApprovalRequest.items`가 번들의 각 줄을 `risk_reasons`와 함께 운반. 승인 전 기록 콘솔 송신 **0건**.
- **뮤테이션**: 백업 발동 경로를 제거하면 RED.

### AC-WRITEGATE-003 — 거부 시 송신 0건 · 복원 번들 보존

**When** 승인이 거부되거나 승인 채널이 없으면, the 기록 경로 **shall** 콘솔 송신 0건으로 종료하고 복원 번들을 회신에 싣는다.

- 대상 요구: REQ-WRITEGATE-002 · ASSUMPTION-70
- **통과 판정**: 단위 — `DenyAllApprovalPort` 기본값과 명시 거부 두 경우 모두 `console.executed == []`, `status="rejected"`, 복원 번들 길이가 대상수×3.
- 안전 비대칭 확인: **승인 채널 미배선이 "사전 승인"으로 읽히지 않는다.**

### AC-WRITEGATE-004 — 간접 경로가 수정 0으로 덮인다

**When** 패치 쓰기가 매크로 본문 또는 배포 대상 Lua 소스에 담기면, the 시스템 **shall** 각각 expand-or-hold와 배포 스캔에서 이를 잡는다.

- 대상 요구: REQ-WRITEGATE-005
- **통과 판정**: 단위 — (a) 본문에 패치 쓰기를 담은 매크로를 `Go Macro 9`로 호출하면 `hold` (b) `Cmd("Set Fixture 11 Posx '5.0'")`를 담은 Lua 소스가 배포 스캔에서 `kind="blacklisted"` 보고. **추가로** `server/safety/expand.py`와 `server/deploy/scan.py`의 byte-diff가 **0**임을 단정한다 — 신규 `category` 도입을 회피했다는 사실 자체가 테스트로 남는다.
- **뮤테이션**: 분류를 신규 category 값으로 바꾸면 (a)(b) 둘 다 RED여야 한다(조용히 열리는 것이 아니라 시끄럽게 실패해야 한다).

### AC-WRITEGATE-005 — 분류 불변 회귀 (범위 봉쇄)

The 개정 **shall not** 아래의 분류를 변경한다.

- 대상 요구: REQ-WRITEGATE-006 · 008
- **통과 판정**: 단위 — 전건 `risky=False`:
  `Store Group 3` · `Store Preset 4.1` · `Store Cue 12` · `Store Page 3` · `Store Macro 21` · `Assign Sequence 4 Page 1.201` · `Copy Page 1 At Page 4` · `Label Group 3 '…'` · `Fixture 1 Thru 12` · `Group 4` · `At 100` · `Set Selection MAtricks 'PhaseFromX' 0` · `Set Macro 1.1 Property 'Command' 'Group 11 At 0'`
- DEPLOY 정캐논 안전 픽스처(`Store Group 3`)가 `SAFE_SOURCE`로 계속 통과함을 확인한다.

### AC-WRITEGATE-006 — 측정 코퍼스 불변식 문면 보존

The 개정 **shall not** `server/measurement/**`를 수정한다.

- 대상 요구: REQ-WRITEGATE-007
- **통과 판정**: `git diff --stat <BASE>..HEAD -- server/measurement/`가 **빈 출력** + 기존 `test_measurement_runner.py::test_happy_path_produces_no_gate_anomalies` 그린(`gate_anomalies == {}`).
- 근거 기록: `corpus.yaml`에 `Set` 토큰 0개(전수 grep). 대표 작업 10종 무교체.

### AC-WRITEGATE-007 — 심어둔 트립와이어의 교체 (삭제 아님)

**When** 분류가 착지하면, the `test_a_coordinate_bundle_is_not_yet_classified_risky` **shall** 승인 흐름 단정으로 교체된다.

- 대상 요구: REQ-WRITEGATE-012
- **통과 판정**: 해당 테스트 이름이 사라지고 그 자리에 AC-WRITEGATE-001·002의 단정이 있다. **동일 테스트가 고정하던 MAtricks 불변(`Set Selection MAtricks 'PhaseFromX' 0` → `risky=False`)은 유지된다** — 트립와이어를 걷을 때 함께 딸린 보호까지 걷는 것이 이 종류의 전형적 사고다.
- 근거: 그 테스트의 실패 메시지가 스스로 지시한 처리다 — *"must be replaced by the approval-flow assertions it was standing in for"*.

### AC-WRITEGATE-008 — 예외 목록 개정의 비준과 3겹 고정

**Where** `server/safety/` 접촉이 구조적으로 불가피한 경우, the 트립와이어 개정 **shall** 3겹 고정을 갖추고 비준 표기를 동반한다.

- 대상 요구: REQ-WRITEGATE-009 · 010
- **통과 판정**: (a) `_SAFETY_EXPECTED_DELETIONS`에 `"server/safety/blacklist.yaml": 1` (b) `_SAFETY_ALLOWED_DELETED_LINES`에 `("version: 1",)` (c) 날짜 · SPEC id · 허용 사유 · `user-approved` · *"그 밖의 것은 여전히 실패한다"*를 담은 그랜트 주석 — **같은 파일의 기존 2건과 동일 형식**.
- **비공허성**: 그랜트가 판정을 무력화하지 않음을 확인한다 — `server/safety/` 아래 임의의 다른 파일을 건드리면 여전히 RED, `blacklist.yaml`에서 다른 행을 지우면 여전히 RED.
- 무접촉 대안 기각 기록: `plan.md §B.2`의 A·B·C·D 4건과 기각 사유가 문서에 남아야 한다 — *"넓히기 전 넓히지 않는 설계를 먼저 찾았다"*는 절차 증거.

### AC-WRITEGATE-009 — `[DEFERRED]` 2건 해소

The 본 SPEC **shall** `AC-SPATIAL-031`과 `REQ-SPATIAL-024` 승인 흐름 절의 `[DEFERRED]`를 해소한다.

- 대상 요구: REQ-WRITEGATE-011
- **통과 판정**: SPATIAL `acceptance.md`·`spec.md`·`plan.md`에서 해당 표기가 제거되고, `AC-SPATIAL-031`이 **뮤테이션 대상으로 복귀**한다(되돌렸을 때 *"없는 코드는 변이시킬 수 없다"*로 제외됐던 것). `REQ-SPATIAL-024`는 두 뜻으로 읽히지 않게 다시 쓰인다.
- 측정 (기준선 실측 · base `b1a630e`): `grep -c 'DEFERRED' .moai/specs/SPEC-COPILOT-SPATIAL-001/*.md` → `acceptance.md:8` · `plan.md:5` · `progress.md:12` · `spec.md:6`. 해소 후 `acceptance.md`·`spec.md`·`plan.md`의 합계가 감소해야 한다. `progress.md`는 **감소 대상이 아니다** — 되돌림의 역사 기록이므로 보존된다.

### AC-WRITEGATE-010 — 폐쇄집합 개정 절차의 기록

The 본 SPEC **shall** `blacklist.yaml` 리터럴의 **첫 개정 사례**로서 절차를 문서에 남긴다.

- 대상 요구: REQ-WRITEGATE-001
- **통과 판정**: version 1→2 범프 + `blacklist.yaml` 헤더에 개정 근거 주석(관측된 54건 인용) + `CHANGELOG.md` 항목. 절차는 EXECREF-001의 `RECOGNIZED_REFERENCE_TYPES` 개정과 동일 무게로 표기된다.
- 근거: OVERLAP `research.md:365-367` — *"확장 선례 0건. 이 SPEC이 선례를 만든다 → 절차를 문서화하는 것 자체가 산출물이어야 한다."*

### AC-WRITEGATE-011 — 전 스위트 그린 + 파탄 집합 정합

The 변경 집합 **shall** 실측된 5건 외에 어떤 테스트도 깨뜨리지 않는다.

- **통과 판정**: `uv run --frozen pytest server/tests/` 전건 그린. 개정 전 실측 기준선은 `4 failed, 4716 passed, 7 skipped`(미커밋) + `test_overlap_preserve` 1건(커밋 후)이며, 6건째 파탄이 나타나면 **원인을 규명하기 전에 진행하지 않는다.**
- 측정 범위 명시: `test_overlap_preserve.py`는 `_PRECHK_BASE..HEAD` **커밋 범위**를 읽으므로 **미커밋 상태에서는 관측되지 않는다.** 검증은 커밋 후에 한다.

### AC-WRITEGATE-012 — 라이브 판정 (보조 증거)

**When** M2 라이브 세션이 실행되면, the 판정 **shall** 폐쇄 어휘로 기록되고 카드 관측·거부 관측·승인 후 기록 완료를 분리 기록한다.

- 대상 요구: REQ-WRITEGATE-013 · 014 · ASSUMPTION-68
- **통과 판정**: `progress.md §E`에 (a) 카드 표시 여부 (b) 거부 시 송신 0건 (c) 승인 후 재조회 일치. **`ok` 단독을 증거로 쓰지 않는다** — 값 대조로 판정한다.
- **이 AC는 다른 AC의 전제가 아니다.** NEGATIVE여도 AC-001~011의 구조적 판정은 독립적으로 성립한다.

## C. 비협상 항목

| AC | 왜 협상 불가인가 |
|---|---|
| AC-WRITEGATE-003 | 승인 채널 미배선이 "사전 승인"으로 읽히면 게이트가 무의미해진다 |
| AC-WRITEGATE-004 | 간접 경로를 조용히 여는 것이 M6c-2 Finding 1과 동일한 결함 계열이다 |
| AC-WRITEGATE-005 | 범위 분리 결정의 실체. 이것이 깨지면 사용자가 고른 갈래가 아니다 |
| AC-WRITEGATE-006 | 코퍼스 문면 보존이 범위 분리를 택한 이유 자체다 |
| AC-WRITEGATE-007 | 트립와이어를 걷으며 딸린 보호까지 걷는 것이 전형적 사고다 |
| AC-WRITEGATE-008 | 넓히기가 판정 방식 변경으로 번지면 타 SPEC의 계약을 단독 파기한 것이 된다 |
