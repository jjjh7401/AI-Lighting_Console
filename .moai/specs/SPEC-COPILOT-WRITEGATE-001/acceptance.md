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
- 비공허성(**증거 범위 명시**): `research.md` §1이 개정 **전** base에서 실측한 것은 **3형태**다 — `Set Fixture 11 Posx '-3.5'` · `Set Fixture 1 Thru 18 Posz '5.0'` · `Set Fixture 11 Rotx '90.0'`가 전부 `safe`였다. 나머지 4형태(부호 소실 · 무동작 · 3자 축약 · 동사 축약)는 **후보 룰셋에 대해서만** 측정됐고 base 실측이 없다. base 폐쇄집합에 `Set*` 엔트리가 **1건도 없었으므로** 어떤 형태도 매칭될 수 없다 — 전건 성립은 참이지만 그것은 **도출이지 실측이 아니다.** 전건을 덮지 않는 증거를 전건 증거로 인용하지 않는다.

### AC-WRITEGATE-002 — 승인 카드 + 백업 규칙 ③

**When** 좌표 기록 번들이 risky로 분류되면, the 게이트 **shall** 승인 카드를 띄우고 `before_risky_execution()`을 발동한다.

- 대상 요구: REQ-WRITEGATE-002 · REQ-SPATIAL-020(규칙 ③ 연동 절) · REQ-SPATIAL-024(승인 흐름 절)
- **통과 판정**: 단위 — 모의 백업 훅으로 `before_risky_execution()` 호출 **1회** 확인 + `ApprovalRequest.items`가 번들의 각 줄을 `risk_reasons`와 함께 운반. 승인 전 기록 콘솔 송신 **0건**.
- **뮤테이션**: 백업 발동 경로를 제거하면 RED. **실측 완료(프로브 후 전부 되돌림)** — `gate.py:365`의 `before_risky_execution()`을 `pass`로 만들면 `test_the_bundle_raises_one_card_and_takes_a_showfile_snapshot`이 *"backup rule ③ fires on the risky path"*로 RED. 결합을 두 방향에서 더 조인다: `gate.py:334`를 `approved = True`로 만들면 승인 테스트 **3건 전부** RED, `gate.py:331`의 `for f in held`를 `held[:1]`로 좁히면 *"every line of the bundle is on the card"* **1건만** RED(`1 failed, 145 passed`) — 카드 **완전성** 결합이 카드 **개수** 결합과 독립임을 보이는 외과적으로 좁은 사살이다.

### AC-WRITEGATE-003 — 거부 시 송신 0건 · 복원 번들 보존

**When** 승인이 거부되거나 승인 채널이 없으면, the 기록 경로 **shall** 콘솔 송신 0건으로 종료하고 복원 번들을 회신에 싣는다.

- 대상 요구: REQ-WRITEGATE-002 · ASSUMPTION-70
- **통과 판정**: 단위 — `DenyAllApprovalPort` 기본값과 명시 거부 두 경우 모두 `console.executed == []`, `status="rejected"`, 복원 번들 길이가 대상수×3. **판별력 보강(갭 기록)**: `status="rejected"`는 지금까지 손으로 만든 `RejectingGate` 스텁에 대해서만 단정됐고 **실제 `SafetyGate`에 대해서는 한 번도 확인된 적이 없다.** 따라서 `test_an_unwired_approval_channel_is_not_read_as_pre_approved`에 `assert payload["gate_status"] == "rejected"`를 함께 단정한다 — 쓰기 0건 + `succeeded: False` 쌍은 **거부 아닌 5경로**(스코프 거부 · 문법 차단 · 헬스 차단 · `blocked_backup_failed` · LiveLock 강등)가 똑같이 만들어내므로 그 쌍만으로는 *"승인이 거부됐다"*를 판별하지 못한다.
- 안전 비대칭 확인: **승인 채널 미배선이 "사전 승인"으로 읽히지 않는다.**

### AC-WRITEGATE-004 — 간접 경로가 수정 0으로 덮인다

**When** 패치 쓰기가 매크로 본문 또는 배포 대상 Lua 소스에 담기면, the 시스템 **shall** 각각 expand-or-hold와 배포 스캔에서 이를 잡는다.

- 대상 요구: REQ-WRITEGATE-005
- **통과 판정**: 단위 — (a) 본문에 패치 쓰기를 담은 매크로를 `Go Macro 9`로 호출하면 `hold` (b) `Cmd("Set Fixture 11 Posx '5.0'")`를 담은 Lua 소스가 배포 스캔에서 `kind="blacklisted"` 보고. 여기에 **category 어휘 불변식**을 더한다 — 관측된 전 형태의 `category`가 `{safe, blacklisted, invoking}`을 벗어나지 않음(`test_no_new_category_value_was_introduced`). **바이트 단정은 하지 않는다**: 테스트가 고정하는 것은 diff가 아니라 **거동**이다. `server/safety/expand.py`의 byte-diff는 실제로 고정되지만 그것은 본 SPEC이 추가한 단정이 아니라 **선재 OVERLAP 게이트**(`test_overlap_preserve.py::test_exactly_the_expected_files_changed`)가 부수적으로 거는 것이고, `server/deploy/`는 **저장소 어느 preserve 목록에도 없다**(`_PRESERVE_PATHS` 10항목 — `test_the_list_has_ten_entries`가 고정 · `_SAFETY_DIR`는 `server/safety/`뿐). 즉 **`server/deploy/scan.py`의 byte-diff는 무보호**이며 그 자리를 지키는 상비 통제는 아래 뮤테이션이다.
- **뮤테이션**: 분류를 신규 category 값으로 바꾸면 (a)(b) 둘 다 RED여야 한다(조용히 열리는 것이 아니라 시끄럽게 실패해야 한다). **실측 완료(되돌림)** — `classify.py:188`의 `category="blacklisted"`를 `"patch_write"`로 바꾸면 **4 failed**: `test_a_macro_body_carrying_a_patch_write_is_held` · `test_a_deployable_lua_source_carrying_a_patch_write_is_refused` · `test_no_new_category_value_was_introduced` · `test_a_patch_write_reports_the_existing_blacklisted_category`. 간접 두 경로가 요구대로 정확히 RED가 됐다.

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
- **보호 범위 정직 표기**: 위 `git diff`는 **손으로 돌리는 명령**이고, `server/measurement/**`의 byte-diff 0에는 **상시 가드가 없다** — `server/measurement/`는 `_PRESERVE_PATHS` 어느 항목에도 없고 `server/tests/` 어디에도 이 경로를 향한 diff 단정이 없다. 상시로 지켜지는 것은 바이트가 아니라 **의미**이며 그 가드는 `test_writegate.py::test_the_measurement_corpus_cannot_collide_with_this_entry`다(코퍼스 소스에서 직접 충돌 부재를 확인한다). 이 테스트는 `mock.commands`가 없는 시나리오를 건너뛰어 **21 중 4건**(`plugin` 2 · `query` 2)이 미검사였으므로, `plugin` 종 2건의 본문까지 덮도록 확장한다.
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
- **비공허성**: 그랜트가 판정을 무력화하지 않음을 확인한다 — `server/safety/` 아래 임의의 다른 파일을 건드리면 여전히 RED, `blacklist.yaml`에서 다른 행을 지우면 여전히 RED. **프로브 4건 실측 완료(전부 되돌림)**: (a) `server/safety/classify.py`에 주석 1행을 덧붙여 커밋 → `test_exactly_the_expected_files_changed` RED(*"Extra items in the left set: 'server/safety/classify.py'"*) — **파일 동일성** 층이 산다 (b) `blacklist.yaml`에서 `- "Format"`을 **한 행 더** 지워 커밋(numstat `31 2`) → `test_the_deletion_counts_match` RED — **개수** 층이 산다 (c) 지우는 행을 `version: 1` 대신 `- "Format"` **한 행으로 바꿔** 커밋(numstat `30 1`) → 개수 테스트는 `1 == 1`로 **통과**하고 `test_the_deletions_are_exactly_the_pinned_lines`가 RED — 실효 층은 개수가 아니라 **문면**이다 (d) 엔트리를 **순수 추가**로 밀입국시키면 `test_overlap_preserve.py`는 **GREEN이다** — 그랜트가 지배하는 것은 **삭제와 파일 동일성**이지 추가가 아니다. 그 자리의 보상 통제는 `test_safety_ruleset.py::test_blacklist_is_exactly_the_shipped_closed_set`(실측 RED)이며, **그랜트 주석이 이미 그 통제를 정확히 지목하고 있다.**
- 대안 기각 기록: `plan.md §B.2`에 **평가·기각 4건**(A·B·C·D)과 기각 사유가 남아야 하고, 그중 **진짜 무접촉은 2건**이다 — A(`gate.py` 단독)와 B(툴 계층 seam)만 트립와이어 비용 **0**이고, C는 **2행** · D는 **1행** 비용을 §B.2의 비용 열이 스스로 적고 있다(`research.md` §7도 *"검토하고 기각한 **무접촉** 대안 **2건**"*으로 A·B만 센다). 기각 사유 기록 요구는 4건 전부에 그대로 적용된다 — *"넓히기 전 넓히지 않는 설계를 먼저 찾았다"*는 절차 증거.

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
- 수집 개수 정합: base `b1a630e` **4723 collected** → HEAD `6f8d1fa` **4763 collected**, 델타 **+40**이다 — 손으로 쓴 **36건** + `test_safety_corpus.py::TestBlacklistFnCorpus`의 SSOT 파라미터화(`:58-59` · `:75`, `@pytest.mark.parametrize("entry", load_ruleset().blacklist)`)가 신규 엔트리에서 **자동 파생한 4건**(`test_no_send_without_approval[0|1|2-Set Fixture]` 3건 + `test_execution_port_also_refuses_unapproved_blacklisted_commands[Set Fixture]` 1건). **"+36"만으로는 `4716 passed` → `4756 passed, 7 skipped`가 맞춰지지 않는다.** 다만 파생 4건의 **뮤테이션 압력은 0**이다 — 엔트리 삭제 뮤턴트에서 이들은 실패하는 것이 아니라 **수집에서 사라진다**(4763 → 4759). AC-WRITEGATE-001의 뮤테이션 증거로 셀 수 있는 것은 손으로 쓴 단정뿐이다.

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
