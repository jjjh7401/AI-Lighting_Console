# SPEC-COPILOT-SCENE-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 타 SPEC 아티팩트**에만 쓰고, **각 마일스톤 착수 직전 재실측**한다. 요구·인수 토큰은 슬러그 포함 완전형만(축약 0건). 근거 등급 `[코드]` · `[문서]` · `[실측]` · `[미확정]` — **`[실측]`은 라이브 콘솔 직접 관측만**이며, 룰북의 "validated live" 선언은 `[문서]`다.

## §0 인수인계 — 여기서 시작한다 (2026-08-01)

### 한 문단

**무엇**: 씬 컴파일러 — **룩(정적 값) + 이펙트(스텝 열) + 타이밍을 하나의 큐로** 합성한다. LOOKLIB(정지 화면 어휘)·FXLIB(시간축 어휘)이 세운 "의도→메모리 파이프라인"의 **2단계**이며, FXLIB이 `spec.md:42`·`:70`·`:140` 세 곳에서 명시적으로 예약해 둔 좌석이다. 신규 패키지 `server/scene/`에 스키마·로더·2축 매칭·결합 컴파일러·리포트를 세우고, 툴 2종(`find_scene`·`compile_scene`)을 기존 `run_commands`→`gate.screen()` 경로로만 배선한다.

**상태**: **plan-audit iter-3 PASS 0.90(문턱 0.85) · v0.2.2(iter-3 비차단 N1~N9 fix-forward) · M0 실행 완료(정리 잔여 1건 — AC-SCENE-019 미완결) · **M1~M4 완료**(M2/M3/M4는 Orca 병렬 웨이브 `run_21629800d19e`).** REQ **21** · AC **24** · ASSUMPTION **5(41~45 — 41·42는 판정 후 moot)** · clarification 마커 **0** · 결정 **A~K 전부 해소** · 라이브 세션 2회 중 **1회 소진(M0)**. AC **15/24** 충족 · 뮤테이션 누적 **30/30 killed**(survived 0). 다음 단계 = **M5(리포트 — 주장 분리 + 미주장 열거)** — 여기서부터 다시 **순차**이며 진행 모드는 **반자율(마일스톤마다 확인, §F)**.

**이 SPEC의 한 줄 (v0.2.0 개정)**: 트래킹 정책이 **M0 실측으로 한 번 뒤집혔다** — `/CueOnly`(미발화 커맨드)를 버리고 **속성 집합 균일화 + 미주장 속성 전수 열거**를 택했다. 그러나 **관측 천장은 그대로다**: "균일 집합을 발화했다"와 "트래킹이 무해해졌다"를 절대 뭉치지 않는 것이 여전히 전체 설계의 축이다.

### 읽는 순서

1. **`design.md` §3(결합 순서) · §4(가드 정책) · §6(트래킹 정책 — 개정본)** — 가장 중요한 세 절이다. **병렬 브리프에 문면 그대로 주입되는 공유 계약**이며, 왜 룩이 먼저인지(강제 근거), 왜 1차 가드가 raise인지(3선례 중 선택), 왜 `/CueOnly`가 폐기됐고 균일 집합이 그 자리를 받는지(§6.0~§6.4)가 여기 있다. **§6.2(관측 천장은 바뀌지 않았다)를 건너뛰지 말 것** — 개정의 최대 위험이 그 절에 있다.
2. `spec.md` §A(개요 · D1 개정본 · D2~D4) → **§C.1 + §C.1a(검증 천장 + M0가 추가한 콘솔 제약 2건)** → §C.2(ASSUMPTION-41~45 판정) → §D(제외 **16**항 — Pan/Tilt 이월 · Zoom/Iris 채움 금지 2항이 개정 신설)
3. `plan.md` §A.2(**M0 판정 결과 표 + 교훈 3건**) → §A.4(결정 A~K) → **§F(병렬 분석 — 교집합 실증 + 공유 계약 SC-1/SC-2/**SC-3**)** → §B(M0 완료 기록 ~ M8)
4. `acceptance.md` §C.0/§C.0a(역추적 · 배정 — 합 **24**·중복 0·누락 0) → **AC-SCENE-015(주장 분리 — 이 SPEC의 중심 AC)** → **AC-SCENE-023, AC-SCENE-024(개정 신설 — 균일성 · 미주장 열거)**
5. `research.md` **§2(`/CueOnly` 전수 grep — 폐기된 정책의 조사 기록)** · §4(가드 3선례) · §5(SONGCUE 상속 부채) · §6(검증 천장 근거)
6. **개정 근거 조사**: `.moai/reports/scene-uniform-attribute-set-proposal.md`(룩 라이브러리 속성 매트릭스 · 4옵션 비교 · Pan/Tilt 구멍) · **판정 정본**: 본 문서 **§E.2**

### 함정 (다음 소유자가 알아야 할 것)

1. **`/CueOnly`는 폐기됐다 — 그리고 그 폐기 방식이 이 SPEC의 가장 중요한 이력이다.** M0에서 **날조 플래그 `/CueOnlyy`가 `ok`를 받고 저장까지 됐다.** 즉 콘솔은 미지 store 플래그를 조용히 접수하며, **`ok`도 재조회도 플래그 철자에 대해 비변별**이다. 그래서 씬은 **어떤 store 플래그도 달지 않는다**(REQ-SCENE-013 (e)). 이 사실을 모르고 "플래그 하나쯤 붙여도 `ok` 나오면 되는 것 아닌가"로 되돌아가면 **런타임 신호가 0인 결함 표면**을 다시 연다.
2. **부정 판정에서 폴백하지 않은 것이 정답이었다.** 41이 `CONDITION_NOT_MET`으로 닫혔을 때 에이전트가 무플래그로 조용히 진행했다면 사용자는 **정책이 바뀐 사실조차 몰랐을 것**이다. 실제로는 중단·블로커 보고 → 사용자 재결정 → D1 개정으로 이어졌다. 이 규율은 v0.2.0에서 **REQ-SCENE-021 (b)로 요구화**됐다.
3. **발화 ≠ 효과 — 정책이 바뀌어도 이 함정은 그대로다.** 트래킹 전파는 **관측 주체가 없다**(`ui/src/components/ExecutionPreviewCard.tsx:61`). "균일 집합을 발화했다"는 정적으로 확인되지만 **"그래서 트래킹이 무해해졌다"는 관측 불가**다. 둘을 같은 문단에 쓰면 AC-SCENE-015가 실패한다(design.md §6.2).
3a. **균일화가 닫지 못하는 축이 있다 — Pan/Tilt.** 룩은 Pan/Tilt를 **구조적으로** 가질 수 없고(`server/looks/loader.py:105-110`), fx 12개 중 **8개가 Pan/Tilt 전용**이다. movement 씬 뒤에는 위치가 트래킹되며 룩 값 라인이 덮을 수단이 없다. **이것을 적지 않으면 "구조적 회피"라는 서술 자체가 과잉 주장**이 되므로, spec.md §D에 명시 제외하고 미주장 열거(REQ-SCENE-014 (d))가 매 컴파일마다 노출한다.
3b. **큐 생성은 실질 append-only다.** 기존 큐보다 낮은 번호의 나중 저장은 플래그 무관 거부된다(M0 실측). ⚠️ 룰북 `:56`의 소수 번호 삽입 서술과 **표면상 충돌**하며 **소수 삽입은 미측정**이다 — "삽입 일반 불가"로 확대 해석 금지.
3c. **거부 메시지 리터럴을 단정 근거로 쓰지 말 것.** 점유 큐 재저장은 `User Canceled Command`, 역순 저장은 `Not allowed`였다 — 원인마다 다르다.
4. **룩이 먼저인 것은 취향이 아니라 강제다.** `MIN_STEPS = 2`(`server/fx/schema.py:66`) + `Step 1` 미발화(`server/fx/instantiate.py:326-342`) → **스텝 1 = 현재 프로그래머 상태 = 룩의 자리**. 순서를 뒤집으면 룩이 페이저의 **종점**이 되고, **런타임은 아무 신호도 내지 않는다**(design.md §3.2).
5. **`/Merge` 금지는 비직관적이다.** `/Merge`는 파괴적이지 않다. 금지 이유는 새 큐 번호에서 **동작이 무플래그와 동일한데**(`SPEC-COPILOT-SONGCUE-001/progress.md:337-344` 실측) **기존 번호의 `Not allowed` 안전망만 꺼지기 때문**이다 — 실익 0에 방어선만 잃는다.
6. **값 라인 dedupe는 지시 턴 경계다.** `executed_ok`가 툴 호출을 넘어 축적된다(`tools.py:699-703` 주석 원문 "in a prior tool call"). 면제는 `Clear`/`ClearAll`/bare 선택 3종뿐(`:327-331`). **씬 번들은 룩+fx 값 라인을 함께 담아 fx보다 충돌 표면이 넓다.** v1은 지시 턴당 컴파일 1회가 운용 경계다.
7. **면제 집합 사본을 만들지 말 것.** `is_programmer_state`가 fx `__all__` 등재 **공개 API**다(`server/fx/instantiate.py:144`). 호출하면 되고, 사본을 만들면 fx가 `test_fx_boundary.py:256-379`에 진 동치 단언 의무를 새로 상속한다.
8. **비공개 함수 import는 적법하다 — 선례 2건.** `server/looks/busking.py:30`·`songcue.py:11`이 `_values_line`을 import하며 이유를 주석으로 남겼다: "**여기서 다시 조립하면 두 곳이 갈라진다**". 씬도 같은 계산이다(결정 D). 단 **패키지 간** 결합이므로 `test_scene_boundary.py`의 산출 형상 고정이 안전벨트다.
9. **fx의 Store는 재사용 불가 — 단, 개정으로 논거 하나가 약해졌다.** `_CUE_NUMBER = 1` 상수 고정(`server/fx/instantiate.py:96`)은 그대로지만, `/CueOnly` 부재는 이제 **차이가 아니다**(씬도 무플래그). 더 근본적인 이유는 **fx 번들에 룩 값 라인을 끼울 자리가 없다**는 것이다(`:475-477`이 `Group` 다음 곧바로 스텝 열). 씬은 **값 라인만** 상류에서 받고 조립·Store는 자기가 한다(결정 I).
10. **`select_sequence_number`는 두 벌 있다.** fx 판(`instantiate.py:218` — 공개, `requested=` 지원, 점유 거부)과 songcue 판(`songcue.py:286`). **씬은 fx 판을 쓴다. 세 번째 판을 만들지 말 것.**
11. **효과는 기계로 확인할 수 없다.** 큐 내용·`CueFade`·픽스처 실시간 값 어느 쪽도 안 읽힌다(spec.md §C.1). 형상 결함은 런타임에서 **아무 신호도 내지 않으므로 테스트가 유일한 그물이다.** `ok`를 성공으로 읽는 순간 이 SPEC은 실패한다.
12. **SONGCUE는 오늘 무플래그로 쓴다 — 개정으로 대비가 축소됐다.** 씬도 무플래그가 됐으므로 **플래그 정책의 분기는 사라졌다.** 남는 대비는 하나: **SONGCUE는 균일 집합을 강제하지 않는다.** **기록하되 고치지 않는다** — `server/looks/**`는 PRESERVE다(결정 J). 이것을 "결함"이라 부르지 말 것: 확인된 사실은 *"결정 기록이 없다"* 뿐이다.
13. **`Delete`는 블랙리스트다.** M0 프로브가 만든 시퀀스 **191·192·193·194·195·196·197**을 툴 경로로 지울 수 없다 — 사용자가 GUI에서 직접 삭제하고 그 사실을 기록한다. **아직 미이행이다.**
14. **`Goto Cue`는 게이트가 모른다.** `RECOGNIZED_REFERENCE_TYPES`(`server/safety/classify.py:44`)에 `Cue`가 없다 — 큐 이동 축을 열려면 게이트 어휘 확장이 필요하므로 §D로 제외했다.
15. **뮤테이션 재료를 잘못 고르면 뮤테이션이 통과한다 (승계 필수 2건).** ① **충돌 열거 비공허성을 movement fx로 세우면 정답도 ∅이라 통과해 버린다** — dimmer/color fx로만 세운다. ② **균일 집합 순서 뮤테이션은 픽스처 주입이 필수다** — 오늘 자산 32/32가 이미 정렬돼 있어 정렬 제거가 자산만으로는 잡히지 않는다.
16. **균일 집합은 자산이 우연히 보장하고 있다.** 32/32가 이미 코어 4를 이 순서로 담고 있어 도입 시점의 정렬은 **바이트 무변화**다. 그래서 강제 코드를 빼도 **오늘은 아무 일도 일어나지 않는다** — 미래 저작에서 조용히 깨진다. 이것이 정렬·강제 지점에 `@MX:ANCHOR`가 붙는 이유다.

### 기계 확인 (인수인계 무결성)

```bash
ls .moai/specs/SPEC-COPILOT-SCENE-001/                                        # → 6파일
grep -c "^- \*\*REQ-SCENE-" .moai/specs/SPEC-COPILOT-SCENE-001/spec.md        # = 21
grep -c "^### AC-SCENE-" .moai/specs/SPEC-COPILOT-SCENE-001/acceptance.md     # = 24
grep -c "^### Out of Scope" .moai/specs/SPEC-COPILOT-SCENE-001/spec.md        # = 16
grep -cE "ASSUMPTION-4[1-5]" .moai/specs/SPEC-COPILOT-SCENE-001/spec.md       # ≥ 5

# 개정 후 근본 사실 — 씬은 store 플래그를 쓰지 않는다
grep -n "CueOnly" .moai/specs/SPEC-COPILOT-SCENE-001/design.md | grep -c "§6" # 폐기 기록은 §6.0에

# 균일 집합의 전제 재실측 (개정 핵심 — 전부 오늘 참이어야 정상)
uv run python -c "from server.looks.schema import CONFIRMED_ATTRIBUTES, KNOWN_ATTRIBUTES; \
print(CONFIRMED_ATTRIBUTES); print(len(KNOWN_ATTRIBUTES))"
# → ('Dimmer', 'ColorRGB_R', 'ColorRGB_G', 'ColorRGB_B') / 8
uv run pytest server/tests/test_looks_library.py -q \
  -k "specifies_a_colour or specifies_an_intensity or names_all_three"        # 3 passed

# 상류 계약 재실측 (드리프트 관례)
grep -n "MIN_STEPS" server/fx/schema.py                                       # MIN_STEPS = 2
grep -n "_CUE_NUMBER" server/fx/instantiate.py                                # = 1 (씬은 재사용 불가)
grep -n "is_programmer_state\|collided_lines" server/fx/instantiate.py        # 공개 API 확인

uv run pytest server/tests/ -q                    # 킥오프 baseline — 직접 실측(이월 금지)
```

### 다음 소유자 킥오프 킷

- **plan-audit 재실행 준비물 (v0.2.1 — iter-3, 하드캡)**: Tier L 문턱 **0.85**. **iter-3은 iter-2가 열거한 결함 델타(D1~D16)에 한정된 재감사다.** 감사가 볼 곳 — ① **개정 논거가 M0 실측(§E.2)과 정합한가**(spec §A D1 · §C.1a · §C.2 · design §6.0 · plan §A.2), ② **관측 천장이 바뀌지 않았다는 사실**이 리포트 규율에 반영됐는가(design §6.2 · AC-SCENE-015 — 개정의 최대 위험), ③ **Pan/Tilt 이월이 은폐되지 않고 §D + 미주장 열거로 노출되는가**, ④ 결합 순서의 **강제 근거**가 취향 서술로 약화되지 않았는가(design §3.2 — 44 `GO`로 실측 확정), ⑤ 1차 가드 정책 선택이 3선례 비교로 논증됐는가(design §4.1 · research §4), ⑥ §F 병렬 분석이 **교집합 실증 + 공유 계약(SC-1/SC-2/SC-3)** 을 담았는가, ⑦ **AC 24건 · REQ 21건**이 §C.0/§C.0a 양쪽에서 중복 0·누락 0인가, ⑧ iter-1 minor 결함 6건(D2~D7)이 실제로 닫혔는가.
- **M1 착수 준비물**: M0는 완료됐다(§E.2). **재측정 금지** — 41/44 판정을 M1 이후에 덮어쓰지 않는다. 착수 직전 baseline은 직접 실측(이월 금지).
- **M4 착수 준비물(병렬 시)**: `design.md §3` · `§4` · **`§6`** 전문을 **요약 없이** 브리프에 주입(plan.md §F.3 SC-1/SC-2/SC-3). 요약본을 만들면 요약이 세 번째 해석이 된다.
- **미이행 잔여 1건**: M0 프로브 시퀀스 **191·192·193·194·195·196·197** 쇼파일 잔존. `Delete` 블랙리스트로 툴 경로 제거 불가 — **사용자 GUI 삭제 후 §E.2에 기록**. 닫히기 전에는 AC-SCENE-019가 완결이 아니다.
- **Kickoff 결정 없음**: 결정 **A~K** 전부 해소, clarification 0, 승인 대기 0 — 재질의할 것이 없다. (D1은 2026-08-01 사용자 재확정으로 닫혔다.)

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

### v0.2.0 (개정 — 2026-08-01, M0 실측 후)

- **개정 사유**: M0 라이브 프로브가 **D1(전 큐 `/CueOnly`)을 무너뜨렸다.** 근거 2건 전부 `[실측]` — ① 날조 플래그 `/CueOnlyy`가 `ok`+저장까지 되어 접수 판정의 **두 기계 채널(`ok`·재조회)이 동시에 소진**, ② 큐 생성이 **실질 append-only**라 `/CueOnly`의 보정 대상("다음 큐")이 저장 시점에 존재할 수 없음. 판정 정본은 §E.2다 — **append-only**로 다룬다: 기록된 판정을 고쳐 쓰지 않고, 이후 추가분(v0.2.1의 ASSUMPTION-43 판정 절·판정 접두 행 블록, iter-3 N4의 정정 절)은 **자기 출처와 측정 순서를 밝힌 채 덧붙인다**.
- **사용자 재결정 (2026-08-01, AskUserQuestion)**: **옵션 D — 코어 4 균일 집합 + 미주장 속성 전수 열거.** `/CueOnly`를 포함한 store 플래그를 일절 쓰지 않는다. `Zoom`/`Iris`는 균일 보장 밖(방향 미측정 — 채움값 발명 금지). Pan/Tilt 이월은 v1에서 닫지 않고 §D에 명시 + 매 컴파일 열거로 노출.
- **개정 근거 조사**: `.moai/reports/scene-uniform-attribute-set-proposal.md` — 룩 라이브러리 32개 전수 파싱(코어 4 = 32/32, 유니온 = 6, 형상 4가지, Zoom 16/32 · Iris 8/32), LOOKLIB이 이미 코어 4를 3개 테스트로 강제 중임을 확인 ⇒ **자산 편집 0건 · PRESERVE 무교차**.
- **본 개정에서 직접 측정한 것 `[측정]`**: ① 32개 룩 전수의 attribute 선언 순서가 **32/32 코어 4 우선 일치**(순서 위반 0건), ② 균일 정렬이 오늘 자산에 대해 **바이트 무변화**(32/32 동일 문자열), ③ 값 라인 최대 길이 **171바이트**(MA3 명령줄 천장 ~2048 대비 8.3%), ④ `KNOWN_ATTRIBUTES` = 정확히 8원소, `CONFIRMED_ATTRIBUTES` = 코어 4 동일 순서.
- **동반 반영**: plan-audit iter-1(PASS 0.91)의 minor 결함 **6건 전부 해소** — D2(REQ-SCENE-010 트리거/익스큐터 꼬리) · D3(design §10 AC 범위) · D4(§C.0 축약 토큰 → 완전형) · D5(AC-SCENE-008 GEARS 주어) · D6(제외 항목 수) · D7(ASSUMPTION 기록 의무 REQ 앵커 + ASSUMPTION-43 AC 커버리지).
- **토큰 변동**: REQ 20 → **21**(REQ-SCENE-021 라이브 판정 기록 의무 신설) · AC 22 → **24**(AC-SCENE-023 균일 집합 / AC-SCENE-024 미주장 열거 신설) · 결정 A~J(10) → **A~K(11)**(K = 열거 유니버스 = 상류 상수 읽기 import) · ASSUMPTION 41·42 **moot**(삭제하지 않고 이력 보존) · 공유 계약 SC-1/SC-2 → **SC-1/SC-2/SC-3**.
- **불변 확인**: D2(룩 먼저 · 충돌은 이펙트 우선) · D3(`/Merge` 미사용 · 신규 큐 번호 전용)는 **개정되지 않았고 ASSUMPTION-44/45 `GO`로 강화**됐다. §F 슬라이스 쓰기 집합 교집합 ∅ 증명도 불변(SC-3은 파일이 아니라 계약을 추가한다).
- **귀결**: plan-artifact 해시 변경 ⇒ **plan-audit 재실행 강제.**

### v0.2.1 (iter-2 감사 결함 수정 — 2026-08-01)

- **성질**: **정책 무변경.** plan-audit iter-2(FAIL 0.80 — 문턱 0.85)가 열거한 **결함 16건(D1~D16)만**을 범위로 삼은 문서 정합성 개정이다. **요구·인수·결정·마일스톤을 신설하지 않았고**, 새 측정도 하지 않았다(기록된 M0 측정치만 사용). iter-2 회귀(0.91 → 0.80)의 절반이 "토큰을 늘리며 그 토큰을 세는 표면을 쓸지 않은" 실패 모드였으므로, 본 개정은 **개수 정합성 일괄 소인(sweep)** 을 마지막 단계로 수행했다.
- **major 5건**: ① **D1** — AC-SCENE-019가 스스로 명시한 `grep -E '^(GO|DESCOPE|SKIP|REOPEN):' progress.md` 가 **0건**을 반환하고 있었다(판정 어휘가 H4 헤딩·볼드 코드 스팬 안에만 있어 `^` 앵커에 걸리지 않았다). **정규식을 약화시키지 않고** §E.2 말미에 행두 접두 행 **6행**을 신설했고, 그 grep을 실행해 **6건**을 실측했다. ② **D2** — REQ-SCENE-021이 어휘 5종과 접두어 4종을 매핑 없이 동시 강제하고 있었고 `INCONCLUSIVE`(ASSUMPTION-42가 실제로 받은 판정)에 대응 접두어가 **어느 SPEC에도 없었다.** 매핑 표를 **인라인**하고 `INCONCLUSIVE` → `DESCOPE:` + `verdict=` 키를 신설했다. ③ **D3** — M4 착수 게이트가 moot된 `ASSUMPTION-41 GO`를 요구해 **최대 마일스톤이 영구 차단**돼 있었다. `ASSUMPTION-44 GO`로 교체했다. ④ **D4** — AC-SCENE-019와 DoD 2가 요구하는 **ASSUMPTION-43 판정 기록이 §E.2에 없었다.** 폐쇄 어휘 `GO`(v1 범위 한정)로 판정 절을 신설하고 `truncated: True` 실측을 정본에 기록했다. ⑤ **D5** — `plan.md §F.3` SC-3 행이 표 밖으로 이탈해 렌더링되지 않았고 "공유 계약은 둘"이 7줄 뒤 "3개"와 모순이었다.
- **minor 11건(D6~D16)**: 미주장 열거 정의를 상류 상수 기준으로 통일(D6) · §E.2 M0 헤딩 스테일(D7) · ASSUMPTION-45 "미관측" 요약 행 스테일(D8) · 정리 의무 블록 2개의 시퀀스 목록 불일치(D9) · M4 개수 스테일 2곳(D10) · §F.4 "6항 vs 7개" (D11) · `research.md` 결정 등록부 `A~J`(D12) · DoD 번호 순서 1·2·…·6·8·7(D13) · 존재하지 않는 `spec-compact` 선언(D14) · `related_specs` 선택 근거 명기(D15) · "M0 완료" 무조건 서술에 정리 잔여 단서 부기(D16).
- **개수 소인 결과(실측)**: `REQ 21` · `AC 24` · `Out of Scope 16` · **접두 행 6**(직전 0). 산문 개수 주장은 전부 이 기계값에 맞췄다.
- **불변 확인**: D1(균일 집합 + 미주장 열거) · D2(룩 먼저 · 충돌은 이펙트 우선) · D3(`/Merge` 미사용) · D4(Tier L) **전부 무변경**. ASSUMPTION-44/45는 `GO` 그대로, 41/42는 moot 그대로다.

### v0.2.2 (iter-3 비차단 지적 9건 fix-forward — 2026-08-01, M1 커밋에 배치)

- **성질**: **정책·요구·인수 무변경 · 재감사 불요.** plan-audit iter-3은 **PASS 0.90**(Tier L 문턱 0.85, 추세 0.91 → 0.80 → 0.90)으로 닫혔고, 감사가 새로 연 **N1~N9는 전부 비차단 문서 정합성 지적**이다(리포트 자신이 "None is blocking"으로 분류). 차단이 아니므로 별도 개정 사이클을 돌리지 않고 **M1 구현 커밋에 함께 배치**했다 — SHOWUI v0.2.1이 세운 fix-forward 선례와 같은 처리다.
- **처리**: N1(썩은 `plan.md` 줄 앵커 3건 → 절 앵커) · N2(맨 `progress.md:NNN` 인용 11곳 → `SPEC-COPILOT-<X>-001/` 완전형) · **N3·N7**(REQ-SCENE-021의 "접두 행을 갖는 명시적 섹션"이 실제 기록 형태와 구조적으로 어긋나던 것을 두 조건 — *판정 절의 존재* + *행두 접두 행의 기계 판독 가능성* — 으로 재진술하고 `REOPEN_SCOPE`를 범위 문장에 명시) · N5(v0.2.1 HISTORY "전 surface" 과잉 주장 정정) · N6(`research.md §9`에 M0 이전 스냅샷 승계 포인터 신설) · N8(AC-SCENE-024 케이스 ②를 **Zoom-only** 재료로 좁힘) · N9("무수정 보존" → **append-only**로 재진술). **N4는 v0.2.1 시점에 이미 닫혔다**(196·197 실제 재조회 + 측정 순서 명기).
- **N3을 "요구 완화"로 읽지 말 것**: 접두 행의 **물리적 배치 자유**만 인정했고, `^` 앵커 grep 판독 가능성과 한 판정당 정확히 1행이라는 조건은 그대로다. AC-SCENE-019가 금지하는 **정규식 완화는 하지 않았다** — 소인 후 재실행에서 여전히 **6행 · exit 0**이다.
- **개수 소인 결과(실측, 소인 후)**: `REQ 21` · `AC 24` · `Out of Scope 16` · **접두 행 6** · **맨 `progress.md:NNN` 인용 0건**. 토큰 변동 **0**.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-08-01T02:57:13Z (v0.1.0)
- plan_amended_at: 2026-08-01 (v0.2.0 — D1 개정 + audit iter-1 결함 6건 폴드인)
- plan_amended_at: 2026-08-01 (v0.2.1 — audit iter-2 결함 16건 수정, 정책 무변경)
- plan_amended_at: 2026-08-01 (v0.2.2 — iter-3 비차단 N1~N9 fix-forward, 정책 무변경, M1 커밋에 배치)
- plan_status: **audited — PASS 0.90** (iter-3, 2026-08-01 · 리포트 `.moai/reports/plan-audit/SPEC-COPILOT-SCENE-001-review-3.md`, gitignore 대상이라 저장소에는 없다). 재감사 불요
- tier: L (plan-auditor 문턱 0.85)
- artifacts: spec.md · plan.md · acceptance.md · design.md · research.md · progress.md (6종)
- tokens: REQ **21** · AC **24** · ASSUMPTION 41~45(5 — 41·42 판정 후 moot) · 결정 **A~K(11, 전부 해소)** · clarification 마커 0 · 승인 대기 0
- live_sessions: 2 계획 / **1 소진(M0 — 실행 완료, 정리 잔여 1건 ⇒ AC-SCENE-019 미완결)** / 1 잔여(M8 종단)
- baseline_measured: pytest 3432 passed / 5 skipped @ `main` `e4bc78e` (2026-08-01, 직접 실행)
- open_items: M0 프로브 시퀀스 191~197 쇼파일 정리 **미이행**(사용자 GUI 삭제 필요)
- commit_sha: pending-backfill

## §E.2 Run-phase Evidence

### M0 — 라이브 프로브 (2026-08-01, 완료 — 본 절 하단 "M0 종결" 표가 최종 판정)

세션 조건: onPC `127.0.0.1:8000`, 응답기 수신 `9005`, **CopilotResponder v1.5.0**, 프로브 착수 시 `DataPool/Sequences` childCount **17**, `DataPool/Groups` = {1 Copilot Grp, 11 Back, 12 Front, 13 All}. 프로브 그룹은 **13 (All)**. 게이트 미경유(bridge 직결, `server.tools` 개발 도구) — 감사 로그 없음.

프로브 대상 시퀀스 191~195는 발화 직전 전부 공석 확인(`path segment not found`).

#### 🔴 CONDITION_NOT_MET: ASSUMPTION-41 (`/CueOnly` 접수) — 기계 채널 소진

**프로브 A(날조 대조군)가 플랜이 예상한 분기를 밟았고, 플랜의 대비책까지 무너졌다.**

| # | 발화 | 결과 |
|---|---|---|
| A | `Store Sequence 191 Cue 1 'SCN PROBE0' /CueOnlyy` (고의 오타 플래그) | **ok** — 기대는 not-ok였다 |
| A-재조회 | `state DataPool/Sequences/191` | **큐 실존** — `{"class":"Cue","cueNo":1,"name":"SCN PROBE0"}`, childCount 17→18 |
| A' | `Store Sequence 191 Cue 1 'SCN OCCUPIED'` (무플래그, **점유된 큐**) | **FAIL — `User Canceled Command`** |

판정 근거 3단:

1. **`ok` 채널은 일반적으로는 변별력이 있다.** A'가 거부됐다 — 콘솔은 거부할 것을 거부한다. 따라서 "`ok`는 이 콘솔에서 아무 의미 없다"는 과잉 일반화는 틀렸다.
2. **그러나 미지 store 플래그에 한해 관대하다.** `/CueOnlyy`는 존재하지 않는 플래그인데 거부되지 않았고 저장까지 됐다.
3. **재조회도 변별하지 못한다.** 날조 플래그가 만든 큐는 기대한 이름·`cueNo`를 그대로 갖는다 — 진짜 `/CueOnly`가 만들 큐와 재조회 상으로 구별 불가다.

⇒ **M0 플랜(v0.1.0)이 적어 둔 대비책**("`ok`가 증거력이 없으면 **판정은 재조회에만 의존해야 한다**")은 **성립하지 않는다.** 재조회 역시 비변별적이다. ASSUMPTION-41은 **두 기계 채널 모두에서 판정 불능**이며, 이는 M0 설계가 예상하지 못한 상태다.

`Cmd()` 응답과 재조회 외에 접수를 읽을 제3 경로는 없다: `/CueOnly`는 큐 프로퍼티가 아니라 **저장 시점의 인접 큐 내용 조작 동작**이므로 `prop`으로 읽을 대상이 존재하지 않고, 큐 내용 자체는 어떤 경로로도 반환되지 않는다(spec.md §C.1).

**귀결**: 접수(41)를 기계로 세울 수 없다. 남은 유일한 단서는 **효과**(프로브 D, 사람 GUI)인데, 뮤테이션 ④가 접수와 효과의 판정 병합을 금지한다. 따라서 41은 `GO`로 올릴 수 없고 `CONDITION_NOT_MET`이며, `plan.md §A.3`(정직한 축소 원칙의 예외 — 사용자 확정 정책의 전제가 무너지면 축소가 아니라 중단이다)에 따라 **run-phase 중단 + 블로커 보고**다.

부수 관측: 거부 메시지가 SONGCUE M0의 `Not allowed`가 아니라 `User Canceled Command`였다. 확인 팝업이 떴다가 취소된 형상으로 보이며, 쇼파일 불변이라는 결론은 같으나 **메시지 리터럴을 단정에 쓰면 안 된다**는 뜻이다.

#### 프로브 A 설계 결함 (승계 필수)

plan.md의 프로브 A와 프로브 B가 **같은 `Sequence 191 Cue 1`을 대상**으로 삼는다. 대조군이 표적을 점유해 버리므로 설계대로는 B를 실행할 수 없다. 실제 발화에서는 이 충돌을 이용해 A'(점유 큐 무플래그 Store)를 추가 발화했고, 그것이 §1 판정의 핵심 근거가 됐다 — 결함이 관측을 도운 우연이며, 후속 SPEC은 프로브별 시퀀스를 분리해야 한다.

#### 기계 발화 결과 (효과 증거 아님)

| 프로브 | 시퀀스 | 커맨드 | 결과 |
|---|---|---|---|
| C — 룩+fx 결합 (ASSUMPTION-44) | 192 `SCN COMBINED` | 11 | **11/11 ok**, 큐 실존 |
| D-A — /CueOnly 있음 (ASSUMPTION-42) | 193 `SCN TRK A1/A2` | 10 | **10/10 ok**, childCount 4 |
| D-B — 무플래그 대조 | 194 `SCN TRK B1/B2` | 9 | **9/9 ok**, childCount 4 |
| E — 충돌 승자 (ASSUMPTION-45) | 195 `SCN CONFLICT` | 10 | **10/10 ok**, 큐 실존 |

**이 `ok` 합계는 효과의 증거가 아니다.** FXLIB M0가 39/39 `ok`에 모션 0을 겪은 선례가 정확히 이 형태다. C·D·E의 판정은 GUI 관측 없이는 내려지지 않는다.

#### GO: ASSUMPTION-44 (룩 + fx 결합) — 사람 GUI 관측

프로브 C(Seq 192 `SCN COMBINED`) Cue 1 실행 결과, 사용자 관측: **파란색이 유지된 채 딤머가 순차 웨이브.** 기대 형상과 일치한다. **판정 GO.**

⇒ `design.md §3.1` 결합 순서 골격(룩 값 라인 → fx 스텝 열 → 위상/속도 → Store)이 실측으로 받쳐졌다. 룩의 정지 값이 스텝 축에 흡수되지 않고 베이스로 남는다. M4 번들 형상은 이 축에서 진행 가능하다.

#### INCONCLUSIVE: ASSUMPTION-42 (트래킹 차단 효과) — 대조군이 갈리지 않음

프로브 D 사용자 관측: **A군(Seq 193, `/CueOnly`)과 B군(Seq 194, 무플래그)이 동일 — 둘 다 Cue 2에서 딤머가 남았다.**

B군이 남았다는 것은 **전방 트래킹이 이 콘솔에서 실재함**을 확인해 준다(대조군이 이론대로 거동했으므로 관측 설계 자체는 유효하다). 그런데 A군도 같았다 — **`/CueOnly`가 트래킹을 막지 못했다.**

#### 후속 프로브 D'' — 저장 순서 역전 시도, 그리고 그 실패가 낳은 발견

D의 A=B를 세 갈래(반대 방향 측정 / 플래그 무효 / 관측 설계 오류) 중 하나로 좁히려고, **큐 2를 먼저 만들고 큐 1을 나중에 `/CueOnly`로 저장**하는 형태를 설계했다(그러면 저장 시점에 보정 대상인 뒤 큐가 존재한다).

| 발화 | 결과 |
|---|---|
| `Store Sequence 196 Cue 2 'D2 A2'` | ok |
| `Store Sequence 196 Cue 1 'D2 A1' /CueOnly` | **FAIL — `Not allowed`** |
| `Store Sequence 197 Cue 2 'D2 B2'` | ok |
| `Store Sequence 197 Cue 1 'D2 B1'` (무플래그 대조) | **FAIL — `Not allowed`** |

**설계는 실패했으나 그 실패가 더 중요한 사실을 냈다: 이미 존재하는 큐보다 낮은 번호의 큐를 나중에 저장할 수 없다.** 플래그 유무와 무관하게 거부된다.

⇒ **이 시스템의 큐 생성은 실질적으로 append-only다.** 그러면 저장 시점에 "다음 큐"가 존재하는 상황 자체가 만들어지지 않고, 룰북이 정의한 `/CueOnly`의 동작(“stops the change tracking **into the next cue**” — `31_choreography_patterns.md:59`, `:132`)은 **보정할 대상을 영원히 갖지 못한다.** D의 A=B는 이것으로 설명된다.

⚠️ 단, 이 발견은 룰북 `:56`의 서술("Cue numbers carry decimals — insert between existing cues with `1.5`, `1.55`")과 **표면상 충돌한다.** 소수 번호 삽입은 별도 경로일 수 있고 미측정이다. 정수 번호 역순 저장이 거부된다는 것만이 실측이며, "삽입 일반이 불가하다"로 확대 해석하면 안 된다.

#### 거부 메시지 2종 — 원인이 다르다

| 상황 | 메시지 |
|---|---|
| 점유된 큐에 재저장 (191 Cue 1) | `User Canceled Command` |
| 존재하는 큐보다 낮은 번호 저장 (196/197 Cue 1) | `Not allowed` |

SONGCUE M0가 기록한 것은 `Not allowed`다. 두 메시지가 다른 원인에 대응하므로, **거부 메시지 리터럴을 단정의 근거로 쓰면 안 된다.**

#### GO: ASSUMPTION-43 (큐 번호 Store 가능성) — 기계 채널, v1 범위로 좁혀 판정

> 기록 시각: 2026-08-01(본 절 신설은 plan-audit iter-2 결함 D4의 수정이며, 아래 세 측정치는 전부 **위 프로브 기록에서 이미 발화된 것**이다 — 새 측정을 하지 않았다).

판정 대상을 **v1이 실제로 쓰는 범위(정수 · 신규 · 오름 번호)** 로 좁혀 `GO`로 닫는다. 좁히지 않은 원형("**임의** 큐 번호")은 아래 ②에서 부정이 실측됐고 소수 번호는 미측정이므로, 원형 그대로는 `GO`가 아니다.

| # | 측정된 하위 결과 | 증거 | 귀결 |
|---|---|---|---|
| ① | **신규 정수 큐 번호 Store 성립** | 프로브 C·D·E가 공석 시퀀스 192~195에 `Cue 1`을, D″가 196·197에 `Cue 2`를 각각 `ok`로 저장하고 재조회로 실존 확인. SONGCUE가 `Cue 2`를 라이브로 성립시킨 선례와 일치(`SPEC-COPILOT-SONGCUE-001/progress.md:337-344`) | v1이 쓰는 축은 열려 있다 |
| ② | **역순 저장 거부** | `Store Sequence 196 Cue 1 'D2 A1' /CueOnly` → **`Not allowed`**, `Store Sequence 197 Cue 1 'D2 B1'`(무플래그 대조) → **`Not allowed`** (본 절 "후속 프로브 D″" 표) | "임의" 번호는 성립하지 않는다 — 큐 생성은 실질 append-only |
| ③ | **`truncated: True` 실측** | `DataPool/Sequences` 재조회에서 childCount **24** 에 반환 **18** + `truncated: True`. (프로브 착수 시점 childCount는 17이었고, 프로브가 191~197을 만들며 24까지 올라간 뒤 관측됐다) | REQ-SCENE-013 (d)의 `truncated` 자동배정 거부 가드가 **가상의 방어가 아니라 실재 조건에 대한 방어**임이 확인됨 |

**막는 대상: 없음.** ①이 v1 경로를 열고, ②·③은 v1이 이미 채택한 제약(오름 정수 번호 · `truncated` 시 자동배정 거부)과 정확히 일치한다. 소수 큐 번호는 여전히 **미측정**이며 §D 제외 근거는 그 미측정이다 — ②를 "삽입 일반 불가"로 확대 해석해 제외 근거로 쓰지 않는다.

##### 정정 — ①의 근거가 신설 시점에 절반만 성립했다 (plan-audit iter-3 N4)

**신설 당시 ①은 과잉 주장이었다.** 문면은 "192~197을 재조회로 실존 확인"이었으나, 실제 프로브 세션에서 재조회한 것은 **192·193·194·195뿐**이고 **196·197은 `ok`만 기록돼 있었다.** `ok`를 실존 증거로 쓰는 것은 이 SPEC의 `§C.1`이 정확히 금지하는 혼동이며, iter-3 감사(N4)가 이를 잡았다.

문면을 약화시키는 대신 **실제로 다시 측정했다** — 2026-08-01, iter-3 감사 지적 이후:

| 대상 | 명령 | 관측 |
|---|---|---|
| Seq 196 | `state 'DataPool/Sequences/196'` | `ok` · `{'childCount': 3, 'class': 'Sequence', 'name': 'Sequence 196'}` |
| Seq 197 | `state 'DataPool/Sequences/197'` | `ok` · `{'childCount': 3, 'class': 'Sequence', 'name': 'Sequence 197'}` |

childCount 3 = `OffCue` + `CueZero` + `Cue 2` — D″가 저장한 큐가 실존한다. **이로써 ①의 문면이 사후적으로 참이 됐다.**

**측정 순서를 명시해 둔다**: 이 두 행은 판정 절 신설 **이후**, 감사 지적을 받고 잰 것이다. 원래 판정이 이 근거 위에 서 있었던 것이 아니다. 순서를 감추면 "인용은 있는데 기록이 없다"(D4가 잡은 결함)와 같은 종류의 부정직이 된다.

본 판정의 기계 판독용 접두 행은 §E.2 말미의 **"판정 접두 행"** 블록이 소유한다(한 판정당 정확히 1행 — REQ-SCENE-021 매핑 표).

#### 판정 요약 (41과 42는 뮤테이션 ④에 따라 분리 기록)

| ASSUMPTION | 판정 | 채널 |
|---|---|---|
| 41 `/CueOnly` **접수** | **CONDITION_NOT_MET** | 기계 채널 소진 — 거부 신호는 없었으나 접수를 입증할 경로도 없음 |
| 42 `/CueOnly` **효과** | **INCONCLUSIVE → 실질 무효** | 사람 GUI. append-only 제약상 보정 대상이 존재하지 않음 |
| 43 큐 번호 Store | **GO** (v1 범위 = 정수·신규·오름) | 기계 — 재조회 |
| 44 룩+fx 결합 | **GO** | 사람 GUI |
| 45 충돌 승자 | 미관측 (Seq 195 대기) → **이후 `GO`(본 절 하단 "GO: ASSUMPTION-45" 및 M0 종결 표가 최종)** | 사람 GUI |

⇒ **D1(전 큐 `/CueOnly`)은 이 시스템의 사용 형태에서 관측 가능한 이득이 없다.** 정책은 사용자 확정 사항이므로 대체 결정은 사용자 몫이다(`plan.md §A.3` — 에이전트의 결정 월권 금지). **run-phase 중단 + 블로커 보고 상태.**

#### GO: ASSUMPTION-45 (충돌 승자) — 사람 GUI 관측

프로브 E(Seq 195 `SCN CONFLICT`, 룩 `Dimmer At 80` + fx `Dimmer` 스텝 100/0) 실행 결과, 사용자 관측: **딤머가 펄스한다 — 이펙트 승.** **판정 GO.** `design.md §3.3`의 "충돌 시 이펙트 우선 + 리포트 전수 열거" 규칙이 유지된다. 열거 자체는 정적 계산이므로 이 관측과 무관하게 정확하다.

---

### M0 종결 — 판정 5건 + 정책 개정 1건 (2026-08-01)

| ASSUMPTION | 판정 | 채널 | 후속 |
|---|---|---|---|
| 41 `/CueOnly` 접수 | **CONDITION_NOT_MET → moot** | 기계 채널 소진 | D1 개정으로 `/CueOnly` 미사용 확정 ⇒ 이 가정 자체가 사라짐 |
| 42 `/CueOnly` 효과 | **INCONCLUSIVE → moot** | 사람 GUI (A=B) | 동상 |
| 43 큐 번호 Store | **GO** (v1 범위 = 정수·신규·오름) | 기계 — 재조회 | 역순은 부정 실측 · 소수는 미측정 ⇒ 둘 다 §D 제외. `truncated` 가드 실재 확인 |
| 44 룩+fx 결합 | **GO** | 사람 GUI | `design.md §3.1` 골격 확정 |
| 45 충돌 승자 | **GO** | 사람 GUI | `design.md §3.3` 규칙 확정 |

**`REOPEN: D1 트래킹 정책 개정`** — 사용자 재결정(2026-08-01, AskUserQuestion): **속성 집합 균일화(구조적 회피)**. `/CueOnly`를 포함한 store 플래그를 일절 쓰지 않고, 모든 씬이 동일한 속성 집합을 빠짐없이 채우게 하여 트래킹이 샐 자리 자체를 제거한다. 앞 씬이 설정한 속성을 뒤 씬이 명시적으로 덮으므로 트래킹이 존재해도 결과가 동일하다.

이 개정의 성질:
- **신규 미발화 커맨드 0개** — `/CueOnly`처럼 발화 실적 없는 커맨드를 도입하지 않으므로 미측정 위험이 0이다. FXLIB이 "신규 시퀀스 Cue 1만"으로 택한 구조적 회피와 같은 계열이다.
- **기계 검증 가능** — "모든 씬의 값 라인 속성 집합이 동일하다"는 정적으로 단정할 수 있다. 트래킹 효과를 관측할 필요가 없어진다(관측 불가 축을 우회한다).
- **대가 2건** — (a) 씬마다 값 라인이 늘어 지시 턴 dedupe 충돌 위험이 커진다(가드 정책 §4가 더 중요해진다). (b) **룩 라이브러리의 속성 어휘가 룩마다 제각각이므로 균일 집합의 정의가 선행되어야 한다** — 이것이 개정의 실질 범위다.

**영향 아티팩트**: `spec.md`(D1 서술·REQ-SCENE-010, REQ-SCENE-011, REQ-SCENE-014·§C.1 검증 천장·§D), `plan.md`(결정 A·ASSUMPTION 표·M0/M4 기술), `design.md`(§3 골격에서 `/CueOnly` 제거, §4 가드 비중 상향), `acceptance.md`(`/CueOnly` 관련 AC 대체 + 속성 집합 동일성 AC 신설). **소유권상 manager-spec 재위임 대상이며**(manager-develop은 SPEC 본문 수정 금지), 개정으로 plan-artifact 해시가 바뀌므로 **plan-audit 재실행이 강제된다**.

**정리 의무 (미이행)**: 프로브 시퀀스 **191·192·193·194·195·196·197**이 쇼파일에 잔존. `Delete` 블랙리스트로 툴 경로 제거 불가 — 사용자 GUI 삭제 필요.

#### 정리 의무 (미이행) — 기록 자리

> 위 M0 종결 절의 같은 의무이며 **별개 항목이 아니다.** 이 절은 사용자 GUI 삭제 사실을 적을 자리다.

프로브가 만든 **시퀀스 191·192·193·194·195·196·197**이 쇼파일에 남아 있다(**7개** — 196·197은 후속 프로브 D″가 만든 것이다). `Delete`는 블랙리스트라 툴 경로로 제거 불가 — 사용자가 GUI에서 직접 삭제하고 그 사실을 여기에 기록해야 한다. **이 항목이 닫히기 전에는 AC-SCENE-019가 완결이 아니다.**

#### 판정 접두 행 (기계 판독 정본 — REQ-SCENE-021 매핑 표 적용)

> **행두(column 0)에서 시작하는 이 6행이 `grep -E '^(GO|DESCOPE|SKIP|REOPEN):'` 의 판독 대상이다.** 위 각 판정 절의 산문이 근거이고, 이 블록은 그 판정들의 기계 판독 색인이다 — **한 판정당 정확히 1행**이며 같은 대상이 두 행을 갖지 않는다. 형태는 PRECHK 선례(`SPEC-COPILOT-PRECHK-001/progress.md`의 연속 6행)와 같은 배치이고, 어휘→접두어 대응은 `spec.md` REQ-SCENE-021의 인라인 매핑 표가 정본이다. (이 블록은 plan-audit iter-2 결함 D1의 수정으로 신설됐다 — 판정 내용은 위 절들에서 이미 확정된 것이며 **새 측정을 하지 않았다.** 이전에는 판정 어휘가 H4 헤딩·볼드 코드 스팬 안에만 있어 `^` 앵커 grep이 0건을 반환했다.)

SKIP: ASSUMPTION-41 precondition=접수를 판정할 기계 채널의 변별력 날조 대조군 /CueOnlyy 가 ok 를 받고 저장까지 되어 ok 채널이 소진됐고, 그 큐가 기대한 이름과 cueNo 를 그대로 가져 재조회 채널도 소진됐다. Cmd 응답과 재조회 외에 접수를 읽을 제3 경로가 없다 — /CueOnly 는 큐 프로퍼티가 아니라 저장 시점 동작이라 prop 으로 읽을 대상이 존재하지 않는다
DESCOPE: ASSUMPTION-42 verdict=INCONCLUSIVE A군(Seq 193, /CueOnly)과 B군(Seq 194, 무플래그)이 사람 GUI 관측에서 동일하게 Cue 2 에 딤머 잔존 — 대조군이 갈리지 않아 판정이 서지 않는다. B군 잔존은 전방 트래킹의 실재를 확인해 주므로 관측 설계 자체는 유효했다. A=B 의 설명은 후속 프로브 D″가 실측한 append-only 제약이며, 보정 대상인 다음 큐가 저장 시점에 존재할 수 없다. D1 개정으로 축 자체가 내려갔다
GO: ASSUMPTION-43 literal=Store Sequence 196 Cue 2 'D2 A2' effect=신규 시퀀스의 정수 큐 번호 Store 가 ok 와 재조회 실존으로 성립(192~197). 같은 세션에서 경계 2건 동시 실측 — 역순 저장은 플래그 무관 Not allowed 거부(196/197 Cue 1), DataPool/Sequences 재조회가 childCount 24 에 반환 18 이고 truncated: True. v1 범위(정수·신규·오름)에 한해 GO 이며 역순과 소수는 v1 범위 밖이다
GO: ASSUMPTION-44 literal=프로브 C 번들 11줄 Seq 192 'SCN COMBINED'(룩 값 라인 → fx 스텝 열 → 위상 → 속도 → Store) effect=사람 GUI 관측에서 파란색이 유지된 채 딤머가 순차 웨이브 — 룩의 정지 값이 스텝 축에 흡수되지 않고 베이스로 남았다. design.md §3.1 결합 순서 골격이 실측으로 확정됐다
GO: ASSUMPTION-45 literal=프로브 E 번들 10줄 Seq 195 'SCN CONFLICT'(룩 Dimmer At 80 + fx Dimmer 스텝 100/0) effect=사람 GUI 관측에서 딤머가 펄스 — 이펙트 승. design.md §3.3 의 충돌 시 이펙트 우선 규칙이 확정됐다. 열거 자체는 정적 계산이므로 이 관측과 무관하게 정확하다
REOPEN: D1 트래킹 정책 사용자 재결정(2026-08-01, AskUserQuestion)으로 전 큐 /CueOnly 를 폐기하고 속성 집합 균일화와 미주장 속성 전수 열거로 대체했다. ASSUMPTION-41 의 CONDITION_NOT_MET 이 plan.md §A.3 예외를 발동시켜 run-phase 가 중단되고 블로커가 보고된 결과이며, 에이전트가 대체 정책을 고르지 않았다

---

### M1 — 씬 스키마 + 로더 (2026-08-01, 완료 · cycle_type=tdd)

**착수 baseline (직접 실측 — plan-phase 수치 이월 금지)**: `.venv/bin/python -m pytest server/tests/ -q` → **3432 passed / 5 skipped**, 기반 `main` = `3c701b1`(clean, 미푸시). M0 판정 접두 행 존재 확인: `grep -cE '^(GO|DESCOPE|SKIP|REOPEN):' progress.md` → **6**, exit 0.

**산출**: `server/scene/__init__.py` · `server/scene/schema.py` · `server/scene/loader.py` · `server/tests/test_scene_schema.py`(**94 tests**). `server/orchestrator/tools.py` 무변경(툴 배선은 M6).

**해석 기록 — 요구 2건이 표면상 충돌해 소유권을 분리했다.** REQ-SCENE-001은 타이밍 축(`cue_number`/`sequence_number`/`trig_type`/`trig_time`)을 **씬 스키마의 축**으로 정의하고, REQ-SCENE-004·AC-SCENE-004는 **시퀀스·큐 번호가 호출 인자이지 정적 자산 필드가 아니다**라고 못 박는다. 동시에 REQ-SCENE-006은 **`cue_number` 범위 검사를 로더에 배정**한다. 세 요구를 전부 만족하는 형태는 하나뿐이다:

| 타입 | 축 | 근거 |
|---|---|---|
| `Scene` (정적 자산) | `scene_id` · `display_name` · `label` · `look_id?` · `fx_id?` · `aliases` · `mood_keywords` · `trig_type?` · `trig_time?` | 시퀀스·큐 번호 필드가 **존재하지 않는다** ⇒ 자산에 넣으면 **미지 필드로 거부**된다(REQ-SCENE-004의 기계 집행). `trig_type`은 자산 축이다 — REQ-SCENE-006 검증 ⑤(미지 `trig_type` 거부)가 **로더 검사**이므로 자산이 그 필드를 갖는다는 것이 요구의 전제다 |
| `SceneTiming` (호출 인자) | `sequence_number?` · `cue_number?` · `trig_type?` · `trig_time?` | 전부 선택. 범위 검증은 `loader.parse_timing()`이 수행한다 — 자산 스키마와 타이밍 인자 스키마를 **한 모듈이 소유**해 "적법한 큐 번호"의 정의가 한 벌만 존재한다 |

**해석 기록 2 — 라벨은 필수·ASCII·인용 가능**이다. `spec.md §A`의 씬 축 표가 라벨을 ASCII로 규정하고 Store 리터럴에 인라인한다. fx는 `_label_of`에서 `display_name` 폴백을 두지만(`server/fx/instantiate.py:264-275`), **씬의 `display_name`은 한국어**이므로 같은 폴백을 두면 ASCII 규율이 첫 호출에서 깨진다. 따라서 폴백 없이 필수로 두고, fx의 `LABEL_UNQUOTABLE`과 같은 인용 불가 문자(`'`·개행) 거부를 로더가 함께 수행한다.

**해석 기록 3 — `server/scene/library/`는 M1이 만들지 않는다.** 자산은 §F.2 병렬 슬라이스 A(M2)의 쓰기 집합이다. `load_library_from_dir`의 기본 인자는 그 디렉터리를 가리키며 **부재 시 명시 에러**(`scene library directory not found`)를 낸다 — 조용한 빈 라이브러리를 서빙하지 않는다.

**뮤테이션 4항 — 전부 killed** (각 항목은 소스를 실제로 변형해 실행하고 원복했다):

| # | 주입 | 결과 | 죽은 테스트 (대표) |
|---|---|---|---|
| ① | 미지 필드 검사 무력화(`if unknown:` → `if False:`) | **killed** — 9 failed / 75 passed | `test_an_unknown_scene_key_is_refused` · `test_a_per_show_key_is_refused_as_an_unknown_field[group / fid / executor / sequence_number / cue_number …]` (8건) |
| ② | `look_id`/`fx_id` 동시 부재 통과 | **killed** — 2 failed / 82 passed | `test_a_scene_with_neither_reference_is_refused` · `test_an_explicit_null_pair_is_refused_too` |
| ③ | `Scene`에 per-show 필드(`executor` — 선택 정수) 추가 | **killed** — 2 failed / 82 passed | `test_the_scene_field_set_is_exactly_the_authored_axes` · `test_no_per_show_axis_exists_on_the_scene_dataclass[executor]` |
| ④ | 소문자 `trig_type` 통과(`token.title()` 허용) | **killed** — 9 failed / 75 passed | `test_a_lowercase_token_is_refused[Go / Time / Follow / Sound / BPM]` · `test_an_all_caps_token_is_refused[…]` |

뮤테이션 ③은 **AC-SCENE-004의 M1측 절반**이다(자산측 전수는 M2 `test_scene_library.py`). ④의 재료 규율 1건을 기록한다: `BPM`은 `upper()`가 자기 자신이므로 대문자 변형 파라미터에서 **구조적으로 제외**했다 — 넣으면 `test_every_closed_token_is_accepted`와 정반대를 단언하게 되고, 실제로 첫 실행에서 그 형태로 실패했다.

**검증 (착수 후 실측)**: 전체 `pytest server/tests/ -q` → **3526 passed / 5 skipped** (신규 94, **신규 실패 0**). `ruff check` OK · `ruff format --check` 클린. 커버리지 `--cov=server.scene` → **100%** (문턱 85%). `test_architecture.py` 그린 — `server/scene/`는 `SERVER_DIR.rglob("*.py")` 전역 스캔에 **자동 포섭**되며 예외 명단(`_NAMED_TOOL_EXEMPTIONS`)에 아무것도 추가하지 않았다(REQ-SCENE-019 · AC-SCENE-017의 M1측 확인 — AST 식별자 스캔 전체는 M7 몫).

**PRESERVE 게이트**: `git diff --stat 3c701b1..HEAD -- server/looks server/fx console/lua server/rulebook/assets server/safety` → **빈 출력**. M1은 상류를 **import조차 하지 않는다**(스키마·로더는 순수 자기 정의) — 상류 읽기 import는 M4(값 라인)·M7(상수 동치)에서 시작된다.

**AC 상태**: AC-SCENE-001 **충족**(위반 5종 각각 독립 테스트 — 미지 필드 / 중복 id / 참조 동시 부재 / 수치 범위 / 미지·소문자 `trig_type`), AC-SCENE-002 **충족**(거부 1케이스 + 적법 3케이스 대조군 — 둘 다 / 룩만 / fx만).

**승계 — 닫히지 않은 항목**: M0 프로브 시퀀스 **191~197** 쇼파일 잔존(위 "정리 의무" 절). M1은 순수 파이썬·콘솔 무접촉이므로 이 잔여에 영향받지 않으나, **AC-SCENE-019는 여전히 미완결**이다.

---

### M2 · M3 · M4 — 병렬 웨이브 (2026-08-01, 완료 · Orca Run `run_21629800d19e`)

형상·계약·회수 규칙은 `§F 모드 변경` 절이 소유한다. 본 절은 **결과**다.

**착수 baseline**: `a1faae3`(M1) · `pytest server/tests/test_scene_schema.py -q` → 94 passed. 세 워커가 각자 이 전제를 직접 확인하고 착수했다(각 `worker_done` Baseline-attribution).

| 슬라이스 | 산출 | 테스트 | 뮤테이션 | 커밋 |
|---|---|---|---|---|
| **A · M2** 라이브러리 | `server/scene/library/core.yaml`(씬 5) | `test_scene_library.py` **12** | **3/3 killed** | `2d9ca9b` |
| **B · M3** 매칭 | `server/scene/matching.py` | `test_scene_matching.py` **18** | **3/3 killed** | `3c9c29b` |
| **C · M4** 컴파일 | `server/scene/compile.py` | `test_scene_compile.py` **117**(89 슬라이스 + 28 이음매) | **20/20 killed** | `23ce415` |

**survived 0.** M4 뮤테이션 ⑰은 규율을 **실측으로 입증**했다 — 정렬 로직을 제거하자 32개 자산 전수 스윕은 **전부 통과한 채** 반전 픽스처 테스트만 죽었다. "픽스처 주입 필수"(§F.4-7 ②)가 가정이 아니라 관측이 됐다.

**라이브러리 커버리지(AC-SCENE-003 실측)**: 결합 3 · 룩 단독 1 · fx 단독 1 · **충돌 witness 1**(`worship-golden-pulse`, `Dimmer` — dimmer fx라 교집합이 실제로 비어 있지 않다) · movement 3. 전 엔트리 한국어 무드 키워드 ≥ 1. `look_id`/`fx_id` 전건이 상류 LOOKLIB(32)·FXLIB(12) 실제 로드로 해석 — 끊긴 참조 0.

#### 이음매 검증 — 코디네이터가 회수한 몫 (워커가 볼 수 없는 구간)

병렬 창에서 M2 자산은 M4가 저작될 때 **존재하지 않았다.** 두 워커 모두 이 구멍을 Gaps에 정직하게 적었고, 코디네이터가 닫았다.

1. **실물 자산 × 실물 빌더 (신규 28 테스트, `test_scene_compile.py` 말미)** — 출하된 씬 5건을 상류 룩/fx로 해석해 실제로 컴파일하고 전수 단정: Store 정확 1회 + **라벨 종료 따옴표 뒤 토큰 0** · `/merge`·`/overwrite`·`/cueonly`·`/trig=` 0건(소문자 비교) · `Step 1` 0건 · 금지 `At Step` 형태 0건 · 단독 `Step` 수 == `len(steps)-1` · 룩 보유 씬의 값 라인이 **균일 4개를 이 순서로** + 나머지 ⊆ {Zoom, Iris} · 충돌/미주장 열거가 **정확히** 교집합/차집합. 이로써 AC-SCENE-009/010/012/023이 픽스처가 아니라 **"라이브러리 전 씬 전수"** 라는 문면 그대로 닫혔다.
   - **비공허성 실측**: Store 라인에 `/CueOnly`를 주입하자 5개 자산 케이스가 **전부 죽었다**(주입 후 원복 확인).
   - **값 라인 식별자 규율(발견)**: "`;` 체인이면 룩 값 라인"은 **틀렸다** — `_speed_line`도 `;` 체인이다(`Attribute 'Pan' At Speed 112 ; …`). 판별식은 *모든 세그먼트가 절대값 형태(`At <수>`)인 `;` 체인*이다. 이 오판은 이음매 테스트를 처음 세울 때 실제로 발생했고 fx 단독 씬에서 잡혔다.
2. **M3 드리프트 정정 (`task_ea9ff7620253`)** — `server/scene/matching.py`의 `_PATTERN_ALIASES`가 상류 공개 상수 `server.fx.matching.PATTERN_ALIASES`와 **오늘 27/27 완전 동일한 사본**임을 실측했다(대칭차 `[]`). **오늘 같기 때문에 증상이 0이고**, 상류가 별칭을 하나 더하면 씬 매칭만 조용히 몸란다 — 결정 E·K와 AP-6이 경계한 세 번째 사본이다. 사본을 지우고 **읽기 import**로 교체했다(정정도 슬라이스 소유자에게 되돌려 디스패치했다 — 코디네이터가 남의 파일을 고치지 않는다).
   - **반대로 정상이라 판정한 것**: `_PARTICLES`/`_ENDINGS`/`_term_pattern` 중복은 **위반이 아니다** — `server/looks/matching.py`와 `server/fx/matching.py`가 각자 자기 본을 가진 확립된 선례다. 사본이라고 다 같은 사본이 아니다.
   - fx 패턴을 `fx_id` 토큰에서 추론하는 설계는 유지했다(매칭기는 `FxLibrary`를 받지 않는다). 대신 **출하 fx 12개 전수에 대해 `entry.pattern`이 `entry.fx_id` 토큰에 실제로 들어 있음**을 단정하는 가드를 신설 — 추론이 깨지는 날 매칭기가 조용히 어휘를 잃는 대신 그 테스트가 먼저 죽는다.

**검증 (웨이브 종료 후 코디네이터 실측)**: 전체 `pytest server/tests/ -q` → **3673 passed / 5 skipped** (M1 기준선 3526 대비 **신규 147, 신규 실패 0**). `ruff check`/`format --check` 전 신규 파일 클린. `server/scene` 커버리지 **99%**(문턱 85% — 미도달 2줄은 `compile.py:219`·`matching.py:302`). `test_architecture.py` 4 passed, 예외 명단 무변경. **PRESERVE 게이트**: `git diff --stat 3c701b1..HEAD -- server/looks server/fx console/lua server/rulebook/assets server/safety` → **빈 출력**.

**AC 상태**: AC-SCENE-003 · AC-SCENE-004(M2) · AC-SCENE-006 · AC-SCENE-007 · AC-SCENE-008(M3) · AC-SCENE-005 · AC-SCENE-009 · AC-SCENE-010 · AC-SCENE-011 · AC-SCENE-012 · AC-SCENE-013 · AC-SCENE-014 · AC-SCENE-023(M4) **충족**. 누적 **15/24**(M0 AC-SCENE-019는 정리 잔여로 미완결).

**남은 것**: M5(리포트 — AC-SCENE-015/016/024) · M6(툴 배선 — AC-SCENE-018) · M7(회귀·경계 — AC-SCENE-017/020/022, **상류 상수 동치 2건 포함**) · M8(종단 라이브 — AC-SCENE-021). M4가 M7에 명시 위임한 2건(`SCENE_UNIFORM_ATTRIBUTES == CONFIRMED_ATTRIBUTES` 동치 · `KNOWN_ATTRIBUTES` 8원소 형상 고정)은 아직 **미검증**이다.

## §E.3 Run-phase Audit-Ready Signal

- run_started_at: 2026-08-01 (M1)
- baseline_measured: pytest **3432 passed / 5 skipped** @ `main` `3c701b1` (착수 직전 직접 실행 — 이월 없음)
- milestones_done: **M0**(라이브 프로브, 정리 잔여 1건) · **M1**(스키마 + 로더) · **M2**(라이브러리) · **M3**(2축 매칭) · **M4**(결합·가드·번호) — M2/M3/M4는 Orca 병렬 웨이브 `run_21629800d19e`
- milestones_open: M5 · M6 · M7 · M8
- ac_closed: AC-SCENE-001 · 002 · 003 · 004 · 005 · 006 · 007 · 008 · 009 · 010 · 011 · 012 · 013 · 014 · 023 (**15/24**)
- ac_open: AC-SCENE-019(M0 정리 잔여) · 015 · 016 · 017 · 018 · 020 · 021 · 022 · 024
- current_measured: pytest **3673 passed / 5 skipped** (M1 기준선 3526 대비 신규 147, **신규 실패 0**) · `server/scene` 커버리지 **99%** (문턱 85%) · ruff check/format 클린 · `test_architecture.py` 4 passed, 예외 명단 무변경
- mutations: M1 **4/4** · M2 **3/3** · M3 **3/3** · M4 **20/20** killed (누적 **30/30**, survived 0)
- seam_verified: 실물 씬 자산 5건 × 실물 빌더 전수(28 테스트) — `/CueOnly` 주입으로 비공허성 실측. M3 별칭 사본 드리프트 1건 검출·정정(`task_ea9ff7620253`)
- preserve_gate: `git diff --stat 3c701b1..HEAD -- server/looks server/fx console/lua server/rulebook/assets server/safety` → **빈 출력**
- open_items: ① M0 프로브 시퀀스 191~197 쇼파일 정리 **미이행**(사용자 GUI 삭제 필요) ⇒ AC-SCENE-019 미완결 ② M4가 M7에 위임한 상류 상수 결합 2건 미검증
- commit_sha: M1 `a1faae3` · M2 `2d9ca9b` · M4 `23ce415` · M3 `3c9c29b`

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F Phase 4 Mode Selection

기록 시각: 2026-08-01 · 기록자: 오케스트레이터 (첫 run-phase 스폰 전)

### 입력 파라미터

| 항목 | 값 |
|---|---|
| tier | L |
| scope (파일 수) | ~14 |
| 도메인 수 | 1 (Python 서버 — `server/scene/` 신규 + `server/orchestrator/tools.py` 배선) |
| 파일 언어 구성 | 100% Python (+ YAML 라이브러리 자산) |
| concurrency benefit | LOW — 코딩 중심, M4가 압도적 비중 |
| Agent Teams 전제 | 해당 없음 (Mode 3 RETIRED) |

### 모드 평가

| 모드 | 선택 | 사유 |
|---|---|---|
| 1 trivial | 미선택 | 의미 변경 있는 다중 마일스톤 구현 |
| 2 background | 미선택 | 쓰기 작업 — 읽기 전용 아님 |
| 3 agent-team | 미선택 | RETIRED (tombstone) |
| 4 parallel | 미선택 | 도메인 1개 < 문턱 3, 그리고 코딩 중심 — Anthropic coding-task parallelism caveat |
| 5 sub-agent | **선택** | 순차 마일스톤 위임. 기본 폴백이자 코딩 작업의 안전 기본값 |
| 6 workflow | 미선택 | 파일 ~14 < 문턱 ~30, 그리고 기계적 단일 변환 규칙이 아님(신규 코드) |

### Decision: sub-agent

### 근거

plan.md §G가 사전 평가로 동일하게 sub-agent(Mode 5)를 권고했고 오케스트레이터가 확정한다. §F.2가 M2/M3/M4의 쓰기 집합 교집합 ∅을 증명해 Mode 4 병렬 창이 열려 있으나, §F.5가 스스로 미채택을 권고한다 — M4가 세 슬라이스 중 압도적으로 크므로(**AC 8건, 뮤테이션 20항**) 벽시계가 M4에 지배되어 병렬 이득이 가려진다. 사용자도 순차를 명시 선택했다. Anthropic의 coding-task parallelism caveat("most coding tasks involve fewer truly parallelizable tasks than research")이 이 선택을 지지한다.

### 경계 사례

도메인 수 1은 Mode 4 문턱(3)에 명확히 미달하여 경계 사례가 아니다. 파일 수 ~14는 Mode 6 문턱(~30)의 절반 이하로 역시 경계가 아니다. **§F.2의 교집합 ∅ 증명이 성립함에도 Mode 4를 선택하지 않은 것**만이 기록할 가치가 있는 판단이며, 그 근거는 위 문단의 M4 지배성이다.

### 진행 모드 (Implementation Kickoff Approval 산출)

- 승인: 획득 (2026-08-01, AskUserQuestion)
- 진행 모드: **반자율 — 마일스톤마다 확인**. 각 M 완료 시 5섹션 증거 보고(Claim / Evidence / Baseline-attribution / Gaps / Residual-risk) 후 다음 M 진입 전 사용자 확인.
- M0 착수 조건: 사용자가 콘솔 접근 가능함을 확인함.

### 모드 변경 — M2/M3/M4 구간 한정 Mode 4 병렬 (2026-08-01, M1 완료 후)

사용자가 **"오케스트레이션 스킬을 사용해서 병렬로"** 를 명시 지시했다. 위 Decision(sub-agent)은 **M1까지의 판단이며 철회하지 않는다** — 바뀐 것은 `plan.md §F.5`가 조건부로 열어 둔 **병렬 창(M2/M3/M4)의 채택 여부**이고, M5 이후는 여전히 순차다.

**§F.5 채택 조건 3건 — 착수 시점에 전부 충족 확인**:

| 조건 | 확인 |
|---|---|
| M1이 닫혔다 | 커밋 `a1faae3` · `test_scene_schema.py` 94 passed |
| SC-1/SC-2/SC-3을 `design.md` **전문 인용**으로 주입 가능 | `.moai/reports/handoff/scene/00-공통-브리프.md`에 `design.md` §3(60-122) · §4(123-167) · §6(185-281)을 **스크립트로 바이트 추출**해 삽입(요약·재서술 0). 정본은 여전히 design.md이며 그 사실을 브리프가 명시한다 |
| 쓰기 집합 서로소 | `git status --porcelain server/scene/ server/tests/` 빈 출력에서 착수. A={library/*.yaml, test_scene_library.py} · B={matching.py, test_scene_matching.py} · C={compile.py, test_scene_compile.py} — 교집합 ∅(§F.2) |

**미채택 논거였던 "M4 지배성"은 사라지지 않았다** — 벽시계는 여전히 M4가 지배한다. 사용자 지시가 그 트레이드오프를 받아들인 것이며, 이 기록은 판단이 바뀐 이유를 **논거의 소멸이 아니라 지시**로 정직하게 남긴다.

**형상**: Orca 오케스트레이션(`orca orchestration`) — Run `run_21629800d19e`, 워커 3인 전부 **현재 워크트리**(신규 워크트리 0 — 쓰기 집합이 서로소라 격리 요구가 성립하지 않는다).

| 슬라이스 | Task | Dispatch | 에이전트 | 터미널 |
|---|---|---|---|---|
| A · M2 라이브러리 | `task_8e211c795214` | `ctx_1ffeac4c7ab3` | codex | `term_feddcaed` |
| B · M3 매칭 | `task_a9cae25086d8` | `ctx_4219f583a4a1` | codex | `term_17d9f6eb` |
| C · M4 컴파일 | `task_c31261ff66be` | `ctx_e606904f4b5e` | claude | `term_1a69f3f1` |

**오케스트레이터가 회수한 3가지**(`TEMPLATE-병렬웨이브-파이프라인.md:33-37` — FXLIB 실증): ① **커밋** — 워커는 워킹 트리에 산출물만 남긴다(동시 커밋은 git 인덱스 경합). ② **공유 파일 쓰기** — 워커는 `.moai/specs/**`에 쓰지 않고 `worker_done` 본문으로 보고한다(본 문서의 3자 충돌 방지). ③ **이음매 검증** — 워커는 각자 인메모리 픽스처를 쓰므로 슬라이스 경계는 아무도 보지 않는다. 전체 회귀·경계·이음매(M2 자산 × M4 빌더 전수)는 웨이브 종료 후 오케스트레이터가 1회 수행한다.

**추가 제약(본 웨이브 신설)**: 워커는 **전체 pytest를 돌리지 않는다** — 형제 슬라이스의 미완성 파일을 밟기 때문이다. 자기 테스트 파일만 실행한다.
