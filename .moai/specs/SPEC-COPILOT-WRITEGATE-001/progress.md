# 진행 기록 — 쓰기 경로 무결성

base `origin/main` = `b1a630e` · branch `spec/writepath-001` · worktree `writepath`

**상태**: **M0·M1·M3 완료 · M2(라이브) 미실행.** 전 스위트 `4756 passed, 7 skipped` · 뮤테이션 확인 완료 · `server/` 변경 5파일 · 머지 전 독립 리뷰 4인 소인 완료.

## A. 마일스톤

| 마일스톤 | 상태 | 산출 |
|---|---|---|
| **M0** 결정 게이트 | **완료** | ASSUMPTION-69 판정 — §E.1 |
| **M1** 분류 + 회귀 | **완료** | `11e3888` · 파탄 5건 처리 · 수집 **+40건**(직접 작성 36 + SSOT 파라미터화 자동 파생 4) · 뮤테이션 21건 사살 |
| **M2** 라이브 1턴 | **미실행** | `SKIP: CONDITION_NOT_MET` — §E.2 |
| **M3** 문서 동기화 | **완료** | SPATIAL `[DEFERRED]` 해소 · `CHANGELOG` 선례 기록 |
| **리뷰** 독립 4인 | **완료** | P0 1건 · P1 9건 · P2 12건 소인 — §D |

## B. M1 실행 기록

### B.1 변경 집합

| 파일 | 성격 | 삭제 |
|---|---|---|
| `server/safety/blacklist.yaml` | 폐쇄집합 개정 v1→v2 + 엔트리 1건 + REVISION HISTORY | **1** (`version: 1`) |
| `server/tests/test_safety_ruleset.py` | 고정값 6→7 + 개정 문서화 불변식 신설 | — |
| `server/tests/test_spatial_arrange.py` | 트립와이어 교체 + 승인 포트 배선 + 승인 흐름 4건 | — |
| `server/tests/test_writegate.py` | **신규** — AC-001~006 | — |
| `server/tests/test_overlap_preserve.py` | 비준 그랜트 3겹 | — |

**코드 변경 0행.** `classify.py` · `ruleset.py` · `gate.py` · `expand.py` · `server/spatial/**` · `server/orchestrator/tools.py` · `server/measurement/**` 전부 무수정.

리뷰 소인으로 추가된 파일: `server/prechk/macro.py` · `server/tests/test_prechk_macro.py` · `README.md`(전부 인용·계수 정정, 동작 무변경).

### B.2 파탄 5건 — 전부 예측대로

문면의 *"기존 테스트 10건"*은 과대 계상이었다(되돌린 시점의 집계). plan-phase에서 실측한 5건이 그대로 나왔고 6건째는 없었다.

| # | 대상 | 처리 |
|---|---|---|
| 1 | `test_blacklist_is_exactly_the_six_initial_entries` | 고정값 개정 → `..._the_shipped_closed_set`, 6→7 |
| 2 | `test_a_coordinate_bundle_is_not_yet_classified_risky` | **교체**(삭제 아님). MAtricks 불변 이월 |
| 3 | `test_the_unlocked_control_actually_writes` | 승인 포트 주입 |
| 4 | `test_the_bundle_is_screened_before_anything_is_executed` | 승인 포트 주입 |
| 5 | `test_exactly_the_expected_files_changed` | 비준 그랜트 |

**측정 함정 재확인**: 5는 `_PRECHK_BASE..HEAD` **커밋 범위**를 읽으므로 미커밋 상태에서 보이지 않았다. 커밋 전 `4 failed`였고, 커밋 후 그랜트가 없으면 **`+1 failed`**다 — 파일집합 테스트 하나뿐이다. `test_the_deletion_counts_match`는 `_SAFETY_EXPECTED_DELETIONS.items()`를, `test_the_deletions_are_exactly_the_pinned_lines`는 `_SAFETY_ALLOWED_DELETED_LINES.items()`를 각각 순회하므로 **자기 딕트에 없는 경로는 애초에 들여다보지 않는다.**

⚠ **초안은 여기에 `+3 failed`(파일집합·삭제수·삭제행)라 적고 *"plan이 예고한 그대로다"*를 덧붙였는데 둘 다 틀렸다**: 수는 1이고, `plan.md §C`는 애초에 **1을 정확히 예고하고 그 이유까지 적어뒀다**(`1 failed, 30 passed` 실측 출력 포함). 측정 규율을 논하는 절이 스스로 오측하고, 그 오측을 계획서의 공로로 돌린 사례로 남긴다. 리뷰어가 잡았다.

### B.3 신규 단정 — 직접 작성 36건 + 자동 파생 4건 = 수집 +40

수집 수 실측: base `b1a630e` **4723** → HEAD **4763**. 직접 작성 36건, **자동 파생 4건**. `test_safety_corpus.py`가 `@pytest.mark.parametrize("entry", load_ruleset().blacklist)`로 폐쇄집합을 순회하므로(`:58-59`·`:75`) 신규 엔트리가 `test_no_send_without_approval[0|1|2-Set Fixture]` + `test_execution_port_also_refuses_unapproved_blacklisted_commands[Set Fixture]`를 자동 획득한다 — `blacklist.yaml` 헤더가 약속한 *"a revision here auto-extends the FN corpora"*가 실제로 성립한 지점이다.

⚠ **그 4건은 뮤테이션 압력에 기여하지 않는다**: 엔트리를 지우면 파라미터가 사라지므로 **RED가 되는 게 아니라 수집에서 빠진다**(4763 → 4759). 실물 `SafetyGate` + deny-all 포트로 FN=0을 종단 검증하는 4건이 판별 신호로는 0인 셈이다. 초안이 "신규 36건"만 적어 4716 → 4756이 재구성되지 않았던 원인이기도 하다.

- `TestPatchWritesAreRisky` — 위험 형태 9종 + 범위형 unspecified-target 비오염 + 카드 사유 명기
- `TestScopeIsHeldExactly` — 불변 13종 + **파싱된** 코퍼스 전건 무충돌(플러그인 본문 포함) + 비공허성
- `TestIndirectRoutes` — 매크로 본문 hold · Lua 배포 스캔 refuse · `SAFE_SOURCE` 통과(비공허성) · 인용 프로퍼티 밀반입 hold
- `TestClassificationVocabularyIsUnchanged` — 신규 category 값 부재
- `test_spatial_arrange` — 카드 1건 + 규칙 ③ 스냅샷 · 거부 시 송신 0 + 복원 번들 보존 · 미배선 채널이 사전승인으로 읽히지 않음(`gate_status` 판별 포함)
- `test_safety_ruleset` — 모든 출하 버전이 파일 안에 **사유와 함께** 문서화됨

### B.4 뮤테이션 — 원인에 걸었다

| 뮤턴트 | 결과 |
|---|---|
| `blacklist.yaml` 엔트리 1건 제거 | **21건 RED**(`test_writegate` 16 · `test_spatial_arrange` 4 · `test_safety_ruleset` 1) |
| `classify.py` `category="blacklisted"` → `"patch_write"` | **4건 RED** — 간접 경로 (a) 매크로 본문 · (b) Lua 배포가 **둘 다** 죽는다(AC-004 요구) + 어휘 단정 2건 |
| `gate.py` `before_risky_execution()` → `pass` | 카드+스냅샷 테스트 RED (AC-002 요구) |
| `gate.py` `approved = True` | 승인 테스트 3건 RED |
| `gate.py` `for f in held` → `held[:1]` | **1건만** RED — 카드 완전성 결합이 카드 개수 결합과 독립임을 증명 |

- 위험 형태 9종이 **각자의 사유 문구를 달고** 죽는다 — 어느 형태가 열렸는지 실패 메시지가 지목한다.
- **불변 13종은 살아남는다** — 변별력 확인. 엔트리와 무관한 단정이 엔트리 제거로 죽으면 그건 리그에 건 뮤테이션이라는 뜻이다.
- 변이 표적은 **폐쇄집합 리터럴과 게이트 배선**이며 테스트 픽스처가 아니다.

### B.5 설계 대안 — 넓히지 않는 설계를 먼저 찾았다

사용자 지시(*"먼저 안 건드리는 설계를 찾고, 불가피하면 비준"*)를 실행한 기록. **4건 평가·기각, 그중 진짜 무접촉은 2건.**

| 대안 | 트립와이어 비용 | 기각 사유 |
|---|---|---|
| A. `gate.py`만 수정 | **0 (무접촉)** | `classify.py` @MX:ANCHOR가 제2 분류기 금지. 구체적 손실: 인용 프로퍼티 재귀는 `classify_command`를 재귀 호출하므로 **밀반입 케이스를 놓친다**(§B.3에서 실제로 단정한 경로) |
| B. 툴 계층 승인 seam | **0 (무접촉)** | `before_risky_execution()`을 발동시킬 수 없다 — AC-031 요구의 절반 미달. 승인 창구가 셋이 된다 |
| C. 신규 `category` 값 | 2행 | `expand.py`·`deploy/scan.py`에서 **조용히 열린다**. FN 구멍 2개 신설 — §B.4의 뮤테이션이 이를 실측으로 확인했다 |
| D. 프로퍼티 이름 열거 | 1행 | 열린목록 금지 위반 |

**트립와이어 0건짜리 대안이 둘 다 실재했고, 정확성을 위해 거절했다.** 그 판단과 근거를 그랜트 주석 본문에 남겼다 — 다음 사람이 "왜 더 싼 길을 안 갔나"를 되묻지 않도록.

## C. 남은 부채 (정직하게)

| 항목 | 상태 |
|---|---|
| **배포 플러그인의 Lua 직접 대입** | **열린 채로 남는다.** `deploy/scan.py`는 `Cmd()` 리터럴만 본다 — 직접 대입은 finding도 `dynamic_call`도 만들지 않고, `destructive=False`로 등록돼 호출 시 카드도 규칙 ③도 없다. 룰북 `30_plugin_patterns.md:13-19`가 **바로 이 경로를 패치 방법으로 가르친다.** 사람의 1회 소스 리뷰가 남은 방어선이며, `deploy/scan.py:10-16`이 REQ-MVP-027로 **이미 규범 선언**한 잔여 위험이다 |
| **`Set Layout … 'PositionX'`** | **열린 채로 남는다.** 저장소가 문서화한 두 번째 좌표 쓰기(포럼 moderator 확인). Layout 축 자체가 SPATIAL `[DEFERRED]` |
| 손으로 쓴 `Store Group` | **열린 채로 남는다.** 사용자 결정 범위 분리. 관측 사고가 아니라 가설(54건은 전부 좌표 기록) |
| 툴 계층 승인 seam 정리 | `Store` 축이 열린 뒤에만 가능. 본 SPEC은 부채를 **늘리지 않는 것**까지 이행 |
| 라이브 카드 렌더 확인 | §E.2 — 사용자 입회 필요 |
| 엔트리의 동사·주소 축 미검증 | `Set`이 유일한 패치 쓰기 동사라는 **가정** 위에 서 있다. `Edit Fixture …`·`Set Stage 1.Fixtures.1 …` 등은 파싱은 되나 MA3 수용 여부 미확인 — `blacklist.yaml` 주석에 명기 |

## D. 머지 전 독립 리뷰 4인 — 무엇을 잡았나

파일 무교차 4축 + *"반증을 시도하라"*. **분류 자체는 4축 전부에서 반증을 견뎠고, 깨진 것은 주장과 숫자였다.**

**견딘 것 (반증 실패)**
- **과차단 0건** — 저장소 전역 리터럴 181,990개 차등 스윕(v2 vs 엔트리 제거한 합성 v1): 판정 변화 44건 중 41건이 문자 그대로 `Set Fix*` 패치 쓰기, 2건이 의도된 밀반입 예제, 1건이 마크다운 추출 아티팩트.
- **그랜트가 게이트를 약화시키지 않았다** — 3/3 프로브 RED. 특히 (c) 삭제 수는 1==1로 통과하는데 **삭제 텍스트 층이 잡았다** — 3겹 중 텍스트 층이 실효 층임이 실측됐다.
- **타 SPEC AC 위반 0건** · **비준 절차 누락 0건** — `CONTRACT.md`는 커밋 1건, `test_overlap_preserve.py`는 7건이고 앞선 그랜트 2건도 `CONTRACT.md`를 건드리지 않았다. 선례 그대로 따랐다.
- **신규 36건 전부 비공허** · `real_gate(approve=True)` 기본값이 무엇도 공허화하지 않았다(기본값을 뒤집으면 정확히 §B.2의 2건만 실패).

**깨진 것 (전부 소인)**
| 등급 | 지적 | 소인 |
|---|---|---|
| **P0** | `REQ-WRITEGATE-005`가 "배포 대상 Lua 소스"를 통째로 덮는다고 읽혔다 — 실제로는 `Cmd()` 리터럴 한정 | REQ 문면을 `Cmd()` 한정으로 좁히고 Lua 직접 대입을 §D Out of Scope로 명시 |
| P1 | 성공 기준의 절대적 *"0건"* — `Set Layout … 'PositionX'`가 반례 | "**픽스처 패치 행** 커맨드라인 경로 0건"으로 한정 + Layout Out of Scope 신설 |
| P1 | **descope 숫자 오류** — `Store` 13/21·7/10이라 적었으나 실측 10/21·5/10, `Store Group`은 3/21·1/10 | 3개 파일 정정 + 오류 출처(광역 정규식의 커맨드 13개를 시나리오 수로 이기) 명기 |
| P1 | 개정 문서화 불변식이 **무력화 가능** — 사유 12행을 빈 마커 2행으로 바꿔도 통과 | 마커가 REVISION HISTORY 블록 **안**에 있고 `SPEC-COPILOT-` id를 실을 것을 요구 |
| P1 | `blacklist.yaml` 라인 이동으로 **살아있는 코드 인용 4건**이 다른 폐쇄집합을 가리켰다(`Off`→`Off Everything`) | 라인 번호를 버리고 **키 경로**(`invoking_verbs.verbs`)로 전환 — 다시 밀리지 않는다 |
| P1 | AC-004의 byte-diff 0 단정이 **존재하지 않았다**; `deploy/scan.py`는 어떤 preserve 목록에도 없다 | AC를 행위 단정으로 정정 + `scan.py` 무보호를 명시, 뮤테이션을 상시 통제로 |
| P1 | AC-002/004/008의 뮤테이션·비공허성이 **미이행** | 전부 실제 실행하고 결과를 기록(§B.4 · AC 본문) |
| P1 | `progress.md`가 파탄 수를 `+3`으로 오측하고 계획서 공로로 돌렸다 | §B.2 정정 |
| P1 | SPATIAL `spec.md`가 승인 카드를 *"YES — 뜬다"* 기계 검증으로 적었다 — 검증된 것은 카드가 **요청된다**는 것 | *"YES(기계) — 요청된다 / 라이브 렌더 미검증"*으로 정정. 그 표 자신이 금지한 행위였다 |
| P1 | `REQ-SPATIAL-024` 재작성이 **반대 방향으로** 과잉 주장 — 도달 불가한 응답기 채널까지 무조건 보장 | 커맨드라인 한정으로 범위 명시 + 잔여 3경로 포인터. 두 뜻 교훈은 보존 |
| P2 ×12 | 인용 드리프트, README 계수, MAtricks 기전 오기, `gate_status` 판별 누락, 코퍼스 검사가 4/21 스킵, 픽스처 라벨 오기, `_would_be_held` 계약 문구, §E 로케이터, CHANGELOG M2 누락 등 | 전부 소인 |

**리뷰가 값을 증명한 방식**: P0은 **두 경로로 독립 수렴**했다 — 내가 `deploy/scan.py`를 읽다 의심하고, `RevClassify`가 룰북이 그 경로를 *가르친다*는 결정적 증거까지 찾았다. PR #24에서 P0이 리뷰어 2인 독립 수렴이었던 것과 같은 형태다.

**교훈 1 — 자기 비판의 재범**: 나는 SPATIAL에 *"10건은 과대 계상"*과 *"두 뜻으로 읽히는 요구"*를 고치게 만든 뒤, **같은 턴에 같은 두 실수를 저질렀다**(13/21 과대계상, `Cmd()` 한정을 전체로 적음). 남의 문서에서 결함을 규정하는 능력과 자기 문서에서 그것을 피하는 능력은 별개다.

**교훈 2 — 내가 편집한 파일의 인용이 썩는다**: 드리프트 5건 전부 **이 SPEC 자신의 삽입**이 원인이었다(`blacklist.yaml` 주석, 그랜트 블록, SPATIAL HISTORY 행). 참조만 한 파일의 인용은 하나도 썩지 않았다. 그래서 라인 번호를 키 경로·테스트 이름으로 바꿨다 — 저장소가 손으로 적은 계수에 대해 이미 내린 판단(*"계수를 손으로 적으면 다시 틀린다"*)의 인용 버전이다.

## E. 판정 (폐쇄 어휘)

> `REQ-WRITEGATE-013`·`AC-WRITEGATE-012`가 판정 기록 위치를 **§E**로 지정한다. 형제 SPEC들이 §E를 grep해 판정 행을 찾으므로 절 번호가 곧 로케이터다.

### E.1 ASSUMPTION-69 — 과잉매칭 범위의 운영 수용성

`GO: ASSUMPTION-69` — 엔트리를 객체(`Set Fixture`)로 두어 과잉매칭을 **수용**한다.

- 실측 범위: `Set Fixture 11 Name 'Spot 11'` · `Set Fixture 11 Patch '1.101'` 도 `risky=True`가 된다. 좌표 전용이 아니다.
- 근거 ①: `classify.py` 모듈 docstring이 비대칭을 정책으로 못박는다 — *"Over-matching is resolved by human approval; under-matching would be a safety false negative."*
- 근거 ②: 픽스처 패치 행은 예외 없이 **쇼파일 상태**다. 좌표든 이름이든 패치 주소든 사람이 봐야 한다.
- 근거 ③: 프로퍼티 이름 열거(`Posx`/`Posy`/…)는 `blacklist.yaml`의 *"open-ended lists are prohibited by spec"* 에 걸린다.
- ⚠ **리뷰 후 한정**: 이 엔트리는 **프로퍼티 차원만** 닫는다. 동사(`Set`)와 주소(`Fixture`) 두 차원은 증거가 변화시키지 않았고, `Edit Fixture …`·`Set Stage 1.Fixtures.1 …`·`Set Posx …`는 파싱되며 오늘 `safe`다 — MA3 수용 여부 미확인이므로 **입증된 구멍이 아니라 미검증 후보**다. *"닫혀 있고 완전하다"*는 초안 표현은 과했고 `blacklist.yaml` 주석에서 정정했다.
- **판정 주체**: **에이전트가 내렸다**(사용자 "계속 진행" 지시 하의 보수적·안전측 선택). 되돌릴 수 있으며, 라이브에서 카드 피로가 관측되면 엔트리 형상을 재설계한다 — 그때도 열린목록 제약은 유지된다.

### E.2 ASSUMPTION-68 — 라이브 승인 카드

`SKIP: CONDITION_NOT_MET` — **의도적 미실행.**

- 전제는 성립한다: onPC 가동 확인(`lsof -nP -iUDP:9005` → PID 1106 `app_gma3 HOSTTYPE=onPC`), 우리 앱 프로세스 부재, 하네스 2종 추적됨.
- **미실행 사유**: M2는 사용자의 **실제 쇼파일에 좌표를 기록**한다. 사용자가 자리에 없는 상태에서 그 쓰기를 실행하는 것은 **이 SPEC이 막으려는 바로 그 행위**다 — 54건도 *"의도는 합리적이었으나 그 사이에 사람이 없었다"*였다. 승인 카드를 검증하려고 무승인 쓰기를 하는 것은 자기모순이다.
- **막히지 않는다**: `REQ-WRITEGATE-014`가 성공 기준을 **구조에만** 걸었다. AC-001~011은 M2 없이 충족됐고, 분류·승인 **요청**·백업 발동·거부 시 송신 0건은 실물 `SafetyGate`로 검증됐다.
- **남은 미지는 정확히 하나**: 카드가 **화면에 렌더되는가**. 단위 테스트가 증명하는 것은 `request_approval`이 채워진 요청으로 **호출된다**는 것까지다 — 이 구분을 SPATIAL 검증 천장 표에도 반영했다(리뷰 P1).
- **재개 조건**: 사용자 입회 + 쇼파일 백업 확인. 관측 (a) 카드 표시 (b) 거부 시 송신 0건 (c) 승인 후 재조회 값 일치 — `ok` 단독은 증거로 쓰지 않는다.

## F. 후속 SPEC이 물려받는 것

폐쇄집합 개정 절차의 **첫 실행 사례**가 생겼다. 후속(`Store Group` 축)은 절차를 재발명하지 않고 두 가지만 다루면 된다:

1. 엔트리 추가 + version 3 범프 + REVISION HISTORY 한 줄 — `test_safety_ruleset`의 신설 불변식이 마커를 블록 안에, `SPEC-COPILOT-` id와 함께 요구한다.
2. **코퍼스 갈래 결정** — 실측: 엔트리 `Store`는 21 시나리오 중 **10건**(대표 **5종**), `Store Group`은 **3건**(대표 **1종**)과 충돌하고, `Store Group`은 DEPLOY 테스트 **3건**을 깨뜨린다. `test_writegate.py::test_the_measurement_corpus_cannot_collide_with_this_entry`가 **파싱된 코퍼스 전건**(커맨드 + 플러그인 본문)을 검사하므로, 갈래를 정하지 않고 엔트리를 넣으면 그 테스트가 충돌 시나리오를 **이름까지 지목하며** 막는다. 그게 그 테스트를 그 형태로 쓴 이유다.

그리고 **§C의 두 잔여 경로**(Lua 직접 대입 · Layout 요소)는 `Store` 축과 별개 SPEC이다 — 전자는 Lua AST 수준 스캔이나 패치 쓰기 능력 플래그가 필요하고, 후자는 SPATIAL Layout 축과 함께 열려야 한다.
