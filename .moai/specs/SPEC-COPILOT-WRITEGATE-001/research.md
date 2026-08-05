# 인수 조사 — 쓰기 경로 무결성

base `origin/main` = `b1a630e` · worktree `writepath` · branch `spec/writepath-001` · 2026-08-05

이 문서는 **실측 기록**이다. 계획 판단의 근거는 전부 여기에서 나오고, 추정은 `[INFERENCE]`로 표기한다.

## 1. 닫으려는 구멍 — 관측된 사고

`Set Fixture … Pos*`가 `safe`로 분류되어 **승인 카드 없이** 콘솔에 도달한다.

- 관측: SPATIAL M6 라이브에서 **요청하지 않은 좌표 기록 54건**이 무승인 실행(SPATIAL `progress.md` §E.2.20, `:513`). 모델이 이전 턴의 미완 목표를 이어 완성했고 **그 사이에 사람이 없었다.**
- 같은 턴의 `Go+ Page 1.202`는 카드를 정상 표시 → **게이트는 건강하고 좌표 기록만 그물을 통과한다.**
- 정확한 기전: `gate.py:468` `hold = verdict.risky` → `classify_command`가 블랙리스트·invoking 어느 분기도 타지 않고 `classify.py:241` 종단 `RiskFinding(category="safe", risky=False)`로 떨어진다 → `held`가 비어 승인 블록(`gate.py:325-352`)과 백업 규칙 ③(`gate.py:362-365`)이 **둘 다 건너뛰어진다.**

실측 확인(본 세션):

| 커맨드 | 현재 분류 |
|---|---|
| `Set Fixture 11 Posx '-3.5'` | `safe` · `risky=False` |
| `Set Fixture 1 Thru 18 Posz '5.0'` | `safe` · `risky=False` |
| `Set Fixture 11 Rotx '90.0'` | `safe` · `risky=False` |

## 2. 발화 주체는 둘이다 — 분류가 유일한 공통 관문

| 경로 | 발화자 | 실측 |
|---|---|---|
| **조립기** | `arrange_write_commands` (`tools.py:917-926`), 템플릿 `tools.py:843` `"Set Fixture {fid} {axis} '{value}'"` | 관측된 54건이 이 경로(모델이 `arrange_fixtures`를 fid 부분집합으로 4회 호출 — SPATIAL `progress.md:482-484`, 18대×3축=54) |
| **모델 직접 작성** | `run_commands` = `TOOL_NAMES[0]` (`tools.py:128`)에 임의 커맨드라인 | 룰북(`32_spatial_design.md`)이 **산문으로만** 금지. SPATIAL `spec.md` §C.1 검증 천장 표의 *"절단된 리그에서 모델이 불완전성을 고지하는가"* 행이 한계를 자백한다 — *"툴 설명은 지시일 뿐 강제가 아니다"*. 행 제목으로 가리킨다: 본 SPEC이 SPATIAL `spec.md`에 HISTORY 행을 삽입해 이 문구가 `:135`→`:138`로 밀렸고, 같은 파일이 지금도 편집 중이다 |

두 경로는 `run_commands` 클로저의 `bundle_gate.screen(commands)`(`tools.py:1142-1143`)에서 합류하고, 거기서 `SafetyGate.screen(Sequence[str])`(`gate.py:301`)로 들어간다.

**결론**: 조립기 핸들러에만 승인을 달면 직접 작성 경로가 남는다. **커맨드 문면 분류만이 두 경로를 동시에 덮는다.**

## 3. 저장소는 이미 이 패턴을 우회로로 가드하고 있다 — 그게 부채다

`build_toolset(group_approval_port=...)` (`tools.py:1071`, 문서화 `:1113-1121`):

> `group_approval_port` (SPEC-COPILOT-GROUPGEN-001 §7 — the tool-layer approval seam) is the ONLY route `create_arrangement_groups` has to a console send: it reuses `server.safety.approval.ApprovalPort` … **because `Store Group`/`Label Group` classify as `safe`** (design.md §7.3, `server/safety/**` stays byte-diff 0) and so never reach the gate's own approval stage on their own.

즉 **게이트가 쓰기를 분류하지 못해서 툴 계층에 제2의 승인 창구가 생겼다.** GROUPGEN은 `server/safety/**` byte-diff 0을 지키려고 그렇게 했고, 그 대가로 승인 창구가 둘이 됐다(`REQ-MVP-011/029`의 *"exactly ONE screening path"* 정신과 어긋난다). 그리고 그 우회로는 **`create_arrangement_groups` 핸들러만** 덮으므로 손으로 쓴 `Store Group`은 여전히 무승인이다.

본 SPEC은 그 부채를 **좌표 축에 대해 반복하지 않는다**(REQ-WRITEGATE-003). 툴 계층 우회로를 하나 더 만드는 대신 게이트 분류를 고친다.

## 4. 되돌려진 첫 시도의 정체 — 정확히 무엇이 막았는가

SPATIAL `progress.md` §E.2.14(`:289-311`):

- `:294-296` — **`SafetyGate.screen(commands)`는 커맨드 시퀀스만 받는다 — 호출자가 risky를 선언할 seam이 없다.** 게이트가 risky를 판정하는 유일한 경로는 폐쇄집합이다.
- `:298-299` — 첫 구현은 `blacklist.yaml` v1→v2에 `"Set Fixture"`를 넣었고 **기능 테스트 3건 + 뮤테이션 RED를 통과했다.** 설계는 옳았다.
- `:302-306` — 막은 것은 두 개의 **경계** 가드였다: (a) SPATIAL `spec.md §C.2`의 `server/safety/**` PRESERVE 선언, (b) `test_overlap_preserve.py::TestSafetyChokepointFileSet` — `blacklist.yaml`이 5번째 파일로 추가되며 실패.
- `:311` — 되돌린 파일: `blacklist.yaml`, `test_safety_ruleset.py`, `test_safety_gate.py`.

**판정**: 되돌림의 이유는 **분류 설계의 오류가 아니라 경계 소유권**이었다. 본 SPEC은 `server/safety/`를 소유하므로 (a)가 소멸하고, (b)는 비준으로 처리한다(§7).

## 5. 실측 — 후보 폐쇄집합 엔트리 1건의 전수 거동

임시 룰셋 파일(`load_ruleset(tmp)`, 저장소 무수정)로 `version: 2` + 엔트리 `"Set Fixture"` 1건을 넣고 19건 전수 대조. **불일치 0건.**

| 반드시 HOLD | 결과 | 비고 |
|---|---|---|
| `Set Fixture 11 Posx '-3.5'` | `risky=True` `blacklisted` `entry='Set Fixture'` | 정규 형태 |
| `Set Fixture 11 Posx -3.5` | `risky=True` | **부호 소실 형태**(OK 반환하며 3.5 저장) |
| `Set Fixture 11 Posx - 3.5` | `risky=True` | **조용한 무동작 형태** |
| `Set Fixture 11 Pos -3.5` | `risky=True` | 3자 접두 축약 |
| `Set Fixture 1 Thru 18 Posz '5.0'` | `risky=True`, `unspecified_target=False` | **범위 기록** — 조립기는 못 만들고 손으로만 쓸 수 있는 최대 폭발반경 형태 |
| `Set Fixture 11 Rotx '90.0'` | `risky=True` | 방향 축(REQ-SPATIAL-022c가 v1 기록 금지) |
| `Set Fix 11 Posx '1.0'` | `risky=True` | 동사·키워드 축약 |
| `Set Macro 1.1 Property 'Command' "Set Fixture 11 Posx '5.0'"` | `risky=True` | **매크로 프로퍼티 밀반입** — 기존 재귀(`classify.py:201-222`)가 공짜로 잡는다 |

| 반드시 STAY (분류 불변) | 결과 |
|---|---|
| `Set Selection MAtricks 'PhaseFromX' 0` | `safe` — `PhaseFromX`가 **인용 토큰**이라 키워드 매칭 대상이 아니다(`classify.py:77-78`) |
| `Set Macro 1.1 Property 'Command' "Group 'Vocals' At Full"` | `safe` |
| `Set Macro 1.1 Property 'Command' 'Group 11 At 0'` | `safe` |
| `Store Group 3` · `Store Preset 4.1` · `Assign Sequence 4 Page 1.201` · `Copy Page 1 At Page 4` · `Fixture 1 Thru 12` · `Group 4` · `At 100` · `Label Group 3 '…'` | 전부 `safe` |

## 6. 실측 — 전 스위트 파탄 집합 (AC-SPATIAL-031이 적은 "10건"의 실제 값)

후보 개정을 실제로 적용하고 `uv run --frozen pytest server/tests/` 전건 실행 후 **되돌렸다**(`git reset --hard origin/main`, byte-diff 0 확인).

```
4 failed, 4716 passed, 7 skipped in 101.23s   ← 미커밋 상태
+ 1 failed (test_overlap_preserve)            ← 커밋 후에만 관측된다
```

**총 5건.** 문면의 "10건"은 과대 계상이었다 — 되돌린 시점의 집계이며 본 설계와 다르다.

| # | 테스트 | 성격 | 처리 |
|---|---|---|---|
| 1 | `test_safety_ruleset.py::test_blacklist_is_exactly_the_six_initial_entries` | **의도된 마찰** — 문면이 *"any change creates review friction on purpose"*(`:3-7`)라고 선언 | 6→7 고정값 개정 |
| 2 | `test_overlap_preserve.py::TestSafetyChokepointFileSet::test_exactly_the_expected_files_changed` | 상시 불변식 게이트, **타 SPEC 소유(OVERLAP-001)** | 비준 그랜트(§7) |
| 3 | `test_spatial_arrange.py::test_a_coordinate_bundle_is_not_yet_classified_risky` | **일부러 심은 트립와이어** — 실패 메시지가 *"AC-SPATIAL-031 has landed, so this deferred-gap tripwire must be replaced by the approval-flow assertions it was standing in for"* | 승인 흐름 단정으로 **교체** |
| 4 | `test_spatial_arrange.py::TestLiveLockDemotion::test_the_unlocked_control_actually_writes` | 하네스 낡음 — 기본 `DenyAllApprovalPort`가 **올바르게** 막았다 | 승인 포트 주입 |
| 5 | `test_spatial_arrange.py::TestGateChokepoint::test_the_bundle_is_screened_before_anything_is_executed` | 동일 | 승인 포트 주입 |

4·5는 SPATIAL `progress.md:337-341`이 첫 시도에서 이미 겪고 원인까지 적어둔 것과 동일하다 — *"제품 동작이 옳고 픽스처가 낡은 경우였다."*

### 파탄하지 않은 것 — 범위 분리가 실제로 작동한다는 증거

- **측정 코퍼스 전건 그린.** `corpus.yaml`에 `Set` 토큰이 **0개**(전수 grep). 21 시나리오의 어휘는 `Fixture/Store/Label/At/Assign/Copy/Group/Page`뿐이라 `Set Fixture` 규칙과 교집합이 없다. `test_measurement_runner.py:66-71`의 `report["gate_anomalies"] == {}`가 그대로 통과했다 — 코퍼스 `:10`의 *"non-risky verbs only"* 불변식을 **문면 수정 없이** 지킨다.
- **FN 코퍼스가 공짜로 자랐다.** `test_safety_corpus.py:58,75`가 `load_ruleset().blacklist`를 동적 파라미터화하므로 신규 엔트리가 `직접/번들/간접-매크로` 3변형을 자동 획득하고 **전부 통과**했다. `blacklist.yaml:2-5` 헤더가 약속한 *"a revision here auto-extends the FN corpora"*가 실제로 성립한다.
- **DEPLOY 무영향.** `Store Group 3`을 정캐논 안전 픽스처로 쓰는 3파일(`test_deploy_pipeline.py:26` `SAFE_SOURCE` 등) 전건 그린 — `Store`를 건드리지 않았으므로.
- **네임패밀리 트립와이어 9건 전건 그린**(`did_not_grow|is_unchanged|is_still_the_two`).

## 7. 예외 목록 개정 — 절차를 발명하지 않는다

사용자 지시는 *"먼저 안 건드리는 설계를 찾고, 불가피하면 비준 AC"*였다. 찾았고, **불가피하다**:

- `test_overlap_preserve.py`는 `_PRECHK_BASE..HEAD` **커밋 범위**의 `server/safety/` 변경 **파일 집합**을 고정한다 — `TestSafetyChokepointFileSet::test_exactly_the_expected_files_changed`(현재 `:467-469`). 내용이 아니라 *어느 파일을 건드렸는가*에 민감하다. 착수 시점 `:436-438`이었고 본 SPEC이 그 파일에 그랜트 주석 블록(`:153-174`)을 삽입하며 +31행 밀렸다 — **테스트 이름이 정본이고 행 번호는 보조**다.
- `screen()`에 호출자측 risky 선언 seam이 없다(§4)는 것은 곧 **어떤 설계든 `server/safety/` 아래 최소 한 파일을 건드린다**는 뜻이다. 회피 불가.

검토하고 **기각한** 무접촉 대안 2건:

| 대안 | 왜 기각인가 |
|---|---|
| **A. `gate.py`에만 추가**(이미 허용된 행이라 파일집합 불변, 삭제 0이라 카운트도 불변 → 트립와이어 0건) | `classify.py:169-172` @MX:ANCHOR가 *"a second classifier would fork the closed-set interpretation"*라고 금지한다. 더 구체적으로: 매크로 프로퍼티 밀반입 재귀(`classify.py:201-222`)는 `classify_command`를 재귀 호출하므로 게이트 계층 탐지기는 §5의 밀반입 케이스를 **놓친다.** 문서화된 아키텍처 불변식을 트립와이어 1행과 교환하는 나쁜 거래 |
| **B. 툴 계층 승인 seam**(GROUPGEN `group_approval_port` 방식) | `server/safety/` byte-diff 0이지만 (a) `before_risky_execution()`을 **발동시킬 수 없다**(백업 매니저는 게이트 내부, `gate.py:362-365`) — AC-SPATIAL-031이 명시 요구하는 절반을 못 채운다, (b) 승인 창구가 셋이 된다, (c) §3의 부채를 좌표 축에 복제한다 |

**따라서 비준 경로.** 그리고 절차도 발명하지 않는다 — **바로 그 파일이 이미 날짜·소유자·승인 표기를 갖춘 그랜트 블록 2건을 담고 있다**:

- `test_overlap_preserve.py:64-77` — *"2026-08-03 granted exception — SPEC-COPILOT-SPATIAL-001 M3 adds ONE rulebook asset … (user-approved)"*
- `test_overlap_preserve.py:88-95` — *"2026-08-02 granted exception — the upstream vocabulary extension … user-approved, lightweight track"*

세 번째 그랜트는 이 두 개의 형식을 그대로 따른다.

폐쇄집합 개정 자체의 절차도 기성이다:

- `blacklist.yaml:2-5` — *"they change ONLY via a revision of this file with a version bump"*
- 실행 선례 1건: `classify.py:32-43` @MX:NOTE — EXECREF-001이 `RECOGNIZED_REFERENCE_TYPES`에 `"Executor"`를 추가하며 *"weighted the same as a blacklist.yaml revision (a false-negative review backs the change)"*. 정본 요구는 EXECREF `spec.md:73`.
- 다만 OVERLAP `research.md:365-367`이 적었듯 **`blacklist.yaml` 리터럴 자체는 한 번도 개정된 적이 없다** — 본 SPEC이 그 첫 사례이므로 절차 기록이 산출물의 일부다.

## 8. `Set Fixture` 1건인 이유 (엔트리 형상 판단)

- **프로퍼티 이름 열거는 폐쇄집합 규율 위반이다.** `Posx/Posy/Posz/Rotx/Roty/Rotz`를 엔트리로 세우면 *"다음 프로퍼티는?"*이 열리는데, `blacklist.yaml:3-4`가 *"open-ended lists are prohibited by spec"*이라고 못박는다. `Set Fixture`는 닫혀 있고 완전하다 — **픽스처 패치를 쓰는 모든 커맨드는 사람이 봐야 한다.**
- **과잉매칭은 설계된 방향이다.** `classify.py:5-10`: *"Over-matching is resolved by human approval; under-matching would be a safety false negative."* `Set Fixture 11 Name '…'` 같은 비좌표 패치 쓰기까지 카드가 뜨는 것은 손실이 아니라 정책과 일치한다(ASSUMPTION-69).
- **`category="blacklisted"`를 유지해야 한다** — 신규 category 값을 도입하면 두 소비처가 **조용히 열린다**: `expand.py:110-124`(매크로 본문 확장)와 `deploy/scan.py:138-159`(Lua 배포 스캔)는 `"blacklisted"`/`"invoking"`만 분기하고 나머지는 통과시킨다. 기존 category를 쓰면 매크로 본문·플러그인 소스 경로가 **수정 0으로** 덮인다.

## 9. ASSUMPTION

| ID | 내용 | 상태 |
|---|---|---|
| **ASSUMPTION-68** | 개정된 폐쇄집합이 **라이브 onPC**에서 좌표 기록에 실제 승인 카드를 띄우고, 승인 후 기록이 정상 완료된다 | **기계 검증 완료 · 라이브 미검증** — M2가 판정 |
| **ASSUMPTION-69** | `Set Fixture` 과잉매칭 범위(비좌표 픽스처 패치 쓰기까지 카드)가 운영상 수용 가능하다 | **미검증** — M0 결정 게이트에서 사용자 확인 |
| **ASSUMPTION-70** | `arrange_fixtures`가 승인 카드를 받은 뒤에도 기존 4중 방어(원좌표 백업·재조회·복원 번들·범위 봉쇄)가 무변경으로 작동한다 | **부분 검증** — 실측 5건 중 4·5가 하네스 문제임을 확인. M1 회귀가 판정 |

## 10. 확인 명령

**행 번호는 as-of 열이 말하는 리비전 기준이다.** base 행은 `git show b1a630e:` 형태로 적어 지금도 그대로 재현된다 — 본 SPEC 자신의 삽입이 `test_overlap_preserve.py` 앵커를 +31행 밀었고, 심어둔 트립와이어는 M1이 제거했기 때문에 base 행 번호를 현재 파일에 대고 실행하면 전부 빗나간다.

| 대상 | as-of | 명령 | 기대 |
|---|---|---|---|
| 분류 프로브 (구멍 → 폐쇄) | HEAD | `uv run python -c "from server.safety.grammar import validate; from server.safety.classify import classify_command; from server.safety.ruleset import load_ruleset; print(classify_command(validate(\"Set Fixture 11 Posx '-3.5'\").parsed, load_ruleset()))"` | `risky=True category='blacklisted'`. **같은 명령이 base `b1a630e`에서는 `risky=False category='safe'`였다** — 그 착수 시점 실측이 §1 표이고, 이 한 행의 반전이 본 SPEC 전체다 |
| 코퍼스 무충돌 | HEAD | `grep -c 'Set' server/measurement/corpus.yaml` | `0` |
| 트립와이어 파일집합 (착수 시점) | base `b1a630e` | `git show b1a630e:server/tests/test_overlap_preserve.py \| sed -n '151,156p'` | `_SAFETY_EXPECTED_DELETIONS` 4항목 — `blacklist.yaml` 없음 |
| 트립와이어 파일집합 (현재) | HEAD | `sed -n '175,181p' server/tests/test_overlap_preserve.py` | 5항목 — `blacklist.yaml: 1` 추가됨 |
| 심어둔 트립와이어 (착수 시점) | base `b1a630e` | `git show b1a630e:server/tests/test_spatial_arrange.py \| sed -n '935,951p'` | `test_a_coordinate_bundle_is_not_yet_classified_risky` — `assert finding.risky is False` + 교체 지시 메시지 |
| 심어둔 트립와이어 (현재) | HEAD | `grep -rn 'def test_a_coordinate_bundle_is_not_yet_classified_risky' server/` | **0건** — M1이 예고대로 제거·교체했다 |
| 그랜트 선례 | base·HEAD 동일 | `sed -n '64,95p' server/tests/test_overlap_preserve.py` | 날짜·SPEC·user-approved 표기 2건 |
