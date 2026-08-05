# 진행 기록 — 쓰기 경로 무결성

base `origin/main` = `b1a630e` · branch `spec/writepath-001` · worktree `writepath`

**상태**: **M0·M1·M3 완료 · M2(라이브) 미실행.** 전 스위트 `4756 passed, 7 skipped` · 뮤테이션 확인 완료 · `server/` 변경 5파일.

## A. 마일스톤

| 마일스톤 | 상태 | 산출 |
|---|---|---|
| **M0** 결정 게이트 | **완료** | ASSUMPTION-69 판정 — §B.1 |
| **M1** 분류 + 회귀 | **완료** | `11e3888` · 파탄 5건 처리 · 신규 36건 · 뮤테이션 21건 사살 |
| **M2** 라이브 1턴 | **미실행** | `SKIP: CONDITION_NOT_MET` — §B.2 |
| **M3** 문서 동기화 | **완료** | SPATIAL `[DEFERRED]` 해소 · `CHANGELOG` 선례 기록 |

## B. 판정 (§E 폐쇄 어휘)

### B.1 ASSUMPTION-69 — 과잉매칭 범위의 운영 수용성

`GO: ASSUMPTION-69` — 엔트리를 객체(`Set Fixture`)로 두어 과잉매칭을 **수용**한다.

- 실측 범위: `Set Fixture 11 Name 'Spot 11'` · `Set Fixture 11 Patch '1.101'` 도 `risky=True`가 된다. 좌표 전용이 아니다.
- 근거 ①: `classify.py` 모듈 docstring이 비대칭을 정책으로 못박는다 — *"Over-matching is resolved by human approval; under-matching would be a safety false negative."*
- 근거 ②: 픽스처 패치 행은 예외 없이 **쇼파일 상태**다. 좌표든 이름이든 패치 주소든 사람이 봐야 한다.
- 근거 ③: 프로퍼티 이름 열거(`Posx`/`Posy`/…)는 `blacklist.yaml:3-4`의 *"open-ended lists are prohibited by spec"* 에 걸린다. `Set Fixture`는 닫혀 있고 완전하다.
- **판정 주체**: 이 판정은 **에이전트가 내렸다**(사용자 "계속 진행" 지시 하에서 보수적·안전측 선택). 되돌릴 수 있는 결정이며, 라이브에서 카드 피로가 관측되면 엔트리 형상을 재설계한다 — 그때도 열린목록 제약은 유지된다.

### B.2 ASSUMPTION-68 — 라이브 승인 카드

`SKIP: CONDITION_NOT_MET` — **의도적 미실행.**

- 전제는 성립한다: onPC 가동 확인(`lsof -nP -iUDP:9005` → PID 1106 `app_gma3 HOSTTYPE=onPC`), 우리 앱 프로세스 부재, 하네스 2종 추적됨.
- **미실행 사유**: M2는 사용자의 **실제 쇼파일에 좌표를 기록**한다. 사용자가 자리에 없는 상태에서 그 쓰기를 실행하는 것은 **이 SPEC이 막으려는 바로 그 행위**다 — §E.2.20의 54건도 "의도는 합리적이었으나 그 사이에 사람이 없었다"였다. 승인 카드를 검증하려고 무승인 쓰기를 하는 것은 자기모순이다.
- **막히지 않는다**: `REQ-WRITEGATE-014`가 성공 기준을 **구조에만** 걸었고 라이브는 보조 증거로 규정했다. AC-WRITEGATE-001~011은 M2 없이 독립적으로 충족됐다. 남은 미지는 *"카드 UI가 실제로 렌더되는가"* 한 가지이며, 분류·승인 요청·백업 발동·거부 시 송신 0건은 실제 `SafetyGate`로 전부 검증됐다.
- **재개 조건**: 사용자 입회 + 쇼파일 백업 확인. 관측 항목은 (a) 카드 표시 (b) 거부 시 송신 0건 (c) 승인 후 재조회 값 일치 — `ok` 단독은 증거로 쓰지 않는다.

## C. M1 실행 기록

### C.1 변경 집합

| 파일 | 성격 | 삭제 |
|---|---|---|
| `server/safety/blacklist.yaml` | 폐쇄집합 개정 v1→v2 + 엔트리 1건 + REVISION HISTORY | **1** (`version: 1`) |
| `server/tests/test_safety_ruleset.py` | 고정값 6→7 + 개정 문서화 불변식 신설 | — |
| `server/tests/test_spatial_arrange.py` | 트립와이어 교체 + 승인 포트 배선 + 승인 흐름 4건 | — |
| `server/tests/test_writegate.py` | **신규** — AC-001~006 32건 | — |
| `server/tests/test_overlap_preserve.py` | 비준 그랜트 3겹 | — |

**코드 변경 0행.** `classify.py` · `ruleset.py` · `gate.py` · `expand.py` · `server/spatial/**` · `server/orchestrator/tools.py` · `server/measurement/**` 전부 무수정.

### C.2 파탄 5건 — 전부 예측대로

문면의 *"기존 테스트 10건"*은 과대 계상이었다(되돌린 시점의 집계). plan-phase에서 실측한 5건이 그대로 나왔고 6건째는 없었다.

| # | 대상 | 처리 |
|---|---|---|
| 1 | `test_blacklist_is_exactly_the_six_initial_entries` | 고정값 개정 → `..._the_shipped_closed_set`, 6→7 |
| 2 | `test_a_coordinate_bundle_is_not_yet_classified_risky` | **교체**(삭제 아님). MAtricks 불변 이월 |
| 3 | `test_the_unlocked_control_actually_writes` | 승인 포트 주입 |
| 4 | `test_the_bundle_is_screened_before_anything_is_executed` | 승인 포트 주입 |
| 5 | `test_exactly_the_expected_files_changed` | 비준 그랜트 |

**측정 함정 재확인**: 5는 `_PRECHK_BASE..HEAD` **커밋 범위**를 읽으므로 미커밋 상태에서 보이지 않았다. 커밋 전 `4 failed`, 커밋 후 그랜트 없으면 `+3 failed`(파일집합·삭제수·삭제행). plan이 예고한 그대로다.

### C.3 신규 단정 36건

- `TestPatchWritesAreRisky` — 위험 형태 9종 + 범위형 unspecified-target 비오염 + 카드 사유 명기
- `TestScopeIsHeldExactly` — 불변 13종 + **파싱된** 코퍼스 전건 무충돌 + 비공허성
- `TestIndirectRoutes` — 매크로 본문 hold · Lua 배포 스캔 refuse · `SAFE_SOURCE` 통과(비공허성) · 인용 프로퍼티 밀반입 hold
- `TestClassificationVocabularyIsUnchanged` — 신규 category 값 부재
- `test_spatial_arrange` — 카드 1건 + 규칙 ③ 스냅샷 · 거부 시 송신 0 + 복원 번들 보존 · 미배선 채널이 사전승인으로 읽히지 않음
- `test_safety_ruleset` — 모든 출하 버전이 파일 안에 문서화됨

### C.4 뮤테이션 — 원인에 걸었다

`blacklist.yaml`에서 엔트리 1건 제거 → **21건 RED**(`test_writegate` 16 · `test_spatial_arrange` 4 · `test_safety_ruleset` 1).

- 위험 형태 9종이 **각자의 사유 문구를 달고** 죽는다 — 어느 형태가 열렸는지 실패 메시지가 지목한다.
- 간접 경로 3종(매크로 본문 · Lua 배포 · 인용 밀반입)이 함께 죽는다.
- **불변 13종은 살아남는다** — 변별력 확인. 엔트리와 무관한 단정이 엔트리 제거로 죽으면 그건 리그에 건 뮤테이션이라는 뜻이다.
- 변이 표적은 **폐쇄집합 리터럴**이며 테스트 픽스처가 아니다.

### C.5 설계 대안 — 넓히지 않는 설계를 먼저 찾았다

사용자 지시(*"먼저 안 건드리는 설계를 찾고, 불가피하면 비준"*)를 실행한 기록. 4건 검토, 4건 기각.

| 대안 | 트립와이어 비용 | 기각 사유 |
|---|---|---|
| `gate.py`만 수정 | **0** | `classify.py` @MX:ANCHOR가 제2 분류기 금지. 구체적 손실: 인용 프로퍼티 재귀는 `classify_command`를 재귀 호출하므로 **밀반입 케이스를 놓친다**(C.3에서 실제로 단정한 경로) |
| 툴 계층 승인 seam | **0** | `before_risky_execution()`을 발동시킬 수 없다 — AC-031 요구의 절반 미달. 승인 창구가 셋이 된다 |
| 신규 `category` 값 | 2행 | `expand.py`·`deploy/scan.py`에서 **조용히 열린다**. FN 구멍 2개 신설 |
| 프로퍼티 이름 열거 | 1행 | 열린목록 금지 위반 |

**트립와이어 0건짜리 대안이 실재했고, 정확성을 위해 거절했다.** 그 판단과 근거를 그랜트 주석 본문에 남겼다 — 다음 사람이 "왜 더 싼 길을 안 갔나"를 되묻지 않도록.

## D. 남은 부채 (정직하게)

| 항목 | 상태 |
|---|---|
| 손으로 쓴 `Store Group`의 무승인 경로 | **열린 채로 남는다.** 사용자 결정 범위 분리. 관측 사고가 아니라 가설(54건은 전부 좌표 기록) |
| 툴 계층 승인 seam(`group_approval_port`) 정리 | `Store` 축이 열린 뒤에만 가능. 본 SPEC은 부채를 **늘리지 않는 것**까지 이행 |
| 라이브 카드 렌더 확인 | §B.2 — 사용자 입회 필요 |
| SPATIAL Layout 축 `[DEFERRED]` | 본 SPEC 무관. 잔존 표기 11건은 전부 조건부 분기·이력 행이며 stale 아님(감사 완료) |

## E. 후속 SPEC이 물려받는 것

폐쇄집합 개정 절차의 **첫 실행 사례**가 생겼다. 후속(`Store Group` 축)은 절차를 재발명하지 않고 두 가지만 다루면 된다:

1. 엔트리 추가 + version 3 범프 + REVISION HISTORY 한 줄(`test_safety_ruleset`의 신설 불변식이 이를 강제한다).
2. **코퍼스 갈래 결정** — `Store`는 21 시나리오 중 13건·대표 10종 중 7종과 충돌한다. `test_writegate.py::test_the_measurement_corpus_cannot_collide_with_this_entry`가 **파싱된 코퍼스 전건**을 검사하므로, 갈래를 정하지 않고 엔트리를 넣으면 그 테스트가 충돌 시나리오를 이름까지 지목하며 막는다. 그게 그 테스트를 그 형태로 쓴 이유다.
