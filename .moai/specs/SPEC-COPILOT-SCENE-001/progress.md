# SPEC-COPILOT-SCENE-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 타 SPEC 아티팩트**에만 쓰고, **각 마일스톤 착수 직전 재실측**한다. 요구·인수 토큰은 슬러그 포함 완전형만(축약 0건). 근거 등급 `[코드]` · `[문서]` · `[실측]` · `[미확정]` — **`[실측]`은 라이브 콘솔 직접 관측만**이며, 룰북의 "validated live" 선언은 `[문서]`다.

## §0 인수인계 — 여기서 시작한다 (2026-08-01)

### 한 문단

**무엇**: 씬 컴파일러 — **룩(정적 값) + 이펙트(스텝 열) + 타이밍을 하나의 큐로** 합성한다. LOOKLIB(정지 화면 어휘)·FXLIB(시간축 어휘)이 세운 "의도→메모리 파이프라인"의 **2단계**이며, FXLIB이 `spec.md:42`·`:70`·`:140` 세 곳에서 명시적으로 예약해 둔 좌석이다. 신규 패키지 `server/scene/`에 스키마·로더·2축 매칭·결합 컴파일러·리포트를 세우고, 툴 2종(`find_scene`·`compile_scene`)을 기존 `run_commands`→`gate.screen()` 경로로만 배선한다.

**상태**: **plan-phase 완료 (v0.1.0, draft).** REQ **20** · AC **22** · ASSUMPTION **5(41~45)** · clarification 마커 **0** · 결정 **A~J 전부 해소** · 라이브 세션 2회(M0·M8) 예정. 다음 단계 = **plan-audit(Tier L 문턱 0.85)** → **M0 라이브 프로브**.

**이 SPEC의 한 줄**: `/CueOnly`는 **이 저장소에서 한 번도 발화된 적이 없다** — 그래서 "접수됐다"와 "트래킹이 막혔다"를 절대 뭉치지 않는 것이 전체 설계의 축이다.

### 읽는 순서

1. **`design.md` §3(결합 순서) · §4(가드 정책)** — 가장 중요한 두 절이다. **병렬 브리프에 문면 그대로 주입되는 공유 계약**이며, 왜 룩이 먼저인지(강제 근거)와 왜 1차 가드가 raise인지(3선례 중 선택)가 여기 있다.
2. `spec.md` §A(개요 · 사전 확정 D1~D4) → **§C.1(검증 천장)** → §C.2(ASSUMPTION-41~45) → §D(제외 16항)
3. `plan.md` §A.2(차단 표) → §A.4(결정 A~J) → **§F(병렬 분석 — 교집합 실증 + 공유 계약 SC-1/SC-2)** → §B(M0~M8)
4. `acceptance.md` §C.0/§C.0a(역추적 · 배정 — 합 **22**·중복 0·누락 0) → **AC-SCENE-015(3주장 분리 — 이 SPEC의 중심 AC)**
5. `research.md` **§2(`/CueOnly` 전수 grep)** · §4(가드 3선례) · §5(SONGCUE 상속 부채) · §6(검증 천장 근거)

### 함정 (다음 소유자가 알아야 할 것)

1. **`/CueOnly`는 발화 이력 0건이다.** 전수 grep 결과 코드 0건 / 룰북 산문 2곳(`31_choreography_patterns.md:59`, `:132-133`)뿐이다. ASSUMPTION-41(접수)이 M0 1순위이고, **그 판정 없이는 M4를 저작할 수 없다.**
2. **41 부정은 "정직한 축소"가 아니라 중단이다.** 통상 부정 실측은 유효한 완료지만, D1은 **사용자 확정 정책**이므로 에이전트가 무플래그 폴백을 골라 진행하면 결정 월권이다 — **블로커 보고**가 정답이다(plan.md §A.3 예외).
3. **접수 ≠ 트래킹 차단.** 트래킹 전파는 **관측 주체가 없다**(`ui/src/components/ExecutionPreviewCard.tsx:61`). 큐 재조회로 확인되는 것은 **큐의 존재**뿐이며 그것을 트래킹 증거로 제시하면 AC-SCENE-015가 실패한다.
4. **룩이 먼저인 것은 취향이 아니라 강제다.** `MIN_STEPS = 2`(`server/fx/schema.py:66`) + `Step 1` 미발화(`server/fx/instantiate.py:326-342`) → **스텝 1 = 현재 프로그래머 상태 = 룩의 자리**. 순서를 뒤집으면 룩이 페이저의 **종점**이 되고, **런타임은 아무 신호도 내지 않는다**(design.md §3.2).
5. **`/Merge` 금지는 비직관적이다.** `/Merge`는 파괴적이지 않다. 금지 이유는 새 큐 번호에서 **동작이 무플래그와 동일한데**(SONGCUE `progress.md:337-344` 실측) **기존 번호의 `Not allowed` 안전망만 꺼지기 때문**이다 — 실익 0에 방어선만 잃는다.
6. **값 라인 dedupe는 지시 턴 경계다.** `executed_ok`가 툴 호출을 넘어 축적된다(`tools.py:699-703` 주석 원문 "in a prior tool call"). 면제는 `Clear`/`ClearAll`/bare 선택 3종뿐(`:327-331`). **씬 번들은 룩+fx 값 라인을 함께 담아 fx보다 충돌 표면이 넓다.** v1은 지시 턴당 컴파일 1회가 운용 경계다.
7. **면제 집합 사본을 만들지 말 것.** `is_programmer_state`가 fx `__all__` 등재 **공개 API**다(`server/fx/instantiate.py:144`). 호출하면 되고, 사본을 만들면 fx가 `test_fx_boundary.py:256-379`에 진 동치 단언 의무를 새로 상속한다.
8. **비공개 함수 import는 적법하다 — 선례 2건.** `server/looks/busking.py:30`·`songcue.py:11`이 `_values_line`을 import하며 이유를 주석으로 남겼다: "**여기서 다시 조립하면 두 곳이 갈라진다**". 씬도 같은 계산이다(결정 D). 단 **패키지 간** 결합이므로 `test_scene_boundary.py`의 산출 형상 고정이 안전벨트다.
9. **fx의 Store는 재사용 불가.** `_CUE_NUMBER = 1` 상수 고정(`server/fx/instantiate.py:96`) + `/CueOnly` 부재 — 두 축 모두 씬 정책과 다르다. 씬은 **값 라인만** 상류에서 받고 조립·Store는 자기가 한다(결정 I).
10. **`select_sequence_number`는 두 벌 있다.** fx 판(`instantiate.py:218` — 공개, `requested=` 지원, 점유 거부)과 songcue 판(`songcue.py:286`). **씬은 fx 판을 쓴다. 세 번째 판을 만들지 말 것.**
11. **효과는 기계로 확인할 수 없다.** 큐 내용·`CueFade`·픽스처 실시간 값 어느 쪽도 안 읽힌다(spec.md §C.1). 형상 결함은 런타임에서 **아무 신호도 내지 않으므로 테스트가 유일한 그물이다.** `ok`를 성공으로 읽는 순간 이 SPEC은 실패한다.
12. **SONGCUE는 오늘 무플래그로 쓴다.** 즉 그 큐들의 값은 트래킹되고 있고, 그 사실은 문서·단언·측정 어디에도 없다(research.md §5). **기록하되 고치지 않는다** — `server/looks/**`는 PRESERVE다(결정 J). 이것을 "결함"이라 부르지 말 것: 확인된 사실은 *"결정 기록이 없다"* 뿐이다.
13. **`Delete`는 블랙리스트다.** M0 프로브가 만든 시퀀스(191~194)를 툴 경로로 지울 수 없다 — 사용자가 GUI에서 직접 삭제하고 그 사실을 기록한다.
14. **`Goto Cue`는 게이트가 모른다.** `RECOGNIZED_REFERENCE_TYPES`(`server/safety/classify.py:44`)에 `Cue`가 없다 — 큐 이동 축을 열려면 게이트 어휘 확장이 필요하므로 §D로 제외했다.

### 기계 확인 (인수인계 무결성)

```bash
ls .moai/specs/SPEC-COPILOT-SCENE-001/                                        # → 6파일
grep -c "REQ-SCENE-" .moai/specs/SPEC-COPILOT-SCENE-001/spec.md               # ≥ 20
grep -c "^### AC-SCENE-" .moai/specs/SPEC-COPILOT-SCENE-001/acceptance.md     # = 22
grep -cE "ASSUMPTION-4[1-5]" .moai/specs/SPEC-COPILOT-SCENE-001/spec.md       # ≥ 5
grep -c "CueOnly" .moai/specs/SPEC-COPILOT-SCENE-001/design.md                # ≥ 5

# 본 SPEC의 근본 사실 — 착수 시 반드시 재확인 (0건이어야 정상)
grep -rn "CueOnly" server/ ui/src/ console/ | grep -v rulebook | wc -l        # = 0

# 상류 계약 재실측 (드리프트 관례)
grep -n "MIN_STEPS" server/fx/schema.py                                       # MIN_STEPS = 2
grep -n "_CUE_NUMBER" server/fx/instantiate.py                                # = 1 (씬은 재사용 불가)
grep -n "is_programmer_state\|collided_lines" server/fx/instantiate.py        # 공개 API 확인

uv run pytest server/tests/ -q                    # 킥오프 baseline — 직접 실측(이월 금지)
```

### 다음 소유자 킥오프 킷

- **plan-audit 준비물**: Tier L 문턱 **0.85**. 감사가 볼 곳 — ① `/CueOnly` 미검증성이 전 표면에 정합하게 반영됐는가(spec §A D1 · §C.2 · design §6 · research §2 · AC-SCENE-015/019), ② 결합 순서의 **강제 근거**가 취향 서술로 약화되지 않았는가(design §3.2), ③ 1차 가드 정책 선택이 3선례 비교로 논증됐는가(design §4.1 · research §4), ④ §F 병렬 분석이 **교집합 실증 + 공유 계약 식별**을 둘 다 담았는가, ⑤ AC 22건이 §C.0/§C.0a 양쪽에서 중복 0·누락 0인가.
- **M0 착수 준비물**: `plan.md §B M0`의 프로브 A~E **5종 전문**(날조 대조군 · `/CueOnly` 접수 · 룩+fx 결합 · 트래킹 A/B · 충돌 승자). 실물 onPC 세션 + 사용자 GUI 관측 필요. 프로브 시퀀스 191~194는 세션 종료 시 사용자가 GUI로 삭제.
- **M4 착수 준비물(병렬 시)**: `design.md §3` 전문 + `design.md §4` 전문을 **요약 없이** 브리프에 주입(plan.md §F.3 SC-1/SC-2). 요약본을 만들면 요약이 세 번째 해석이 된다.
- **Kickoff 결정 없음**: 결정 **A~J** 전부 해소, clarification 0, 승인 대기 0 — 재질의할 것이 없다.

## Plan-phase log

### v0.1.0 (최초 작성 — 2026-08-01)

- 아티팩트 6종 동시 생성(spec/plan/acceptance/design/research/progress). 출처: **FXLIB이 예약한 후속 좌석**(`spec.md:42`, `:70`, `:140` — research.md §1) + 사용자 결정 4건(D1~D4, 2026-08-01 증거 리포트 후 확정).
- 사용자 확정 D1~D4 반영: 트래킹 정책(전 큐 `/CueOnly`) / 결합 순서(룩 먼저·충돌은 이펙트 우선) / `/Merge` 미사용·신규 큐 번호 전용 / Tier L. clarification 마커 0건으로 닫힘.
- 조사: 코디네이터 직접 판독. **핵심 실측 1건** — `/CueOnly`·`Block Sequence`·`Unblock` 전수 grep에서 코드 발화 **0건**(룰북 산문 2곳만) 확인, 이것이 ASSUMPTION-41을 M0 1순위로 만든 근거다.
- 상류 API 표면 직접 확인: `is_programmer_state`·`collided_lines`·`select_sequence_number`가 fx `__all__` 등재 **공개**임을 판독 → **면제 집합 사본 0**(결정 E)과 **2차 가드 재사용**(결정 G)이 가능해졌다. 비공개 함수 크로스 import는 저장소 선례 2건 확인(`busking.py:30`, `songcue.py:11`).
- 가드 정책 3선례 비교(fx=raise / busking=skip / songcue=skip+원장) 후 **fx 정책 채택** — 결정 변수는 산출물 형태(씬은 단일 Store라 잔여가 없다).
- baseline 직접 실측: `uv run pytest server/tests/ -q` → **3432 passed, 5 skipped** (`main`=`e4bc78e`, clean).
- SPEC ID 사전 검증: `SPEC-COPILOT-SCENE-001` — 정규식 분해 `SPEC ✓ | COPILOT ✓ | SCENE ✓ | 001 ✓ → PASS` (Bash 실행 검증).
- 아티팩트 커밋 SHA는 자기참조 불가이므로 `pending-backfill`.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-08-01T02:57:13Z
- plan_status: audit-ready
- tier: L (plan-auditor 문턱 0.85)
- artifacts: spec.md · plan.md · acceptance.md · design.md · research.md · progress.md (6종)
- tokens: REQ 20 · AC 22 · ASSUMPTION 41~45(5) · 결정 A~J(10, 전부 해소) · clarification 마커 0 · 승인 대기 0
- live_sessions_planned: 2 (M0 프로브 · M8 종단)
- baseline_measured: pytest 3432 passed / 5 skipped @ `main` `e4bc78e` (2026-08-01, 직접 실행)
- commit_sha: pending-backfill

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
