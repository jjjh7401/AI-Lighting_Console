---
id: SPEC-COPILOT-SCENE-001
title: "씬 컴파일러 — 룩 + 이펙트 + 타이밍을 하나의 큐로 (Scene Compiler)"
version: "0.2.3"
status: draft
created: 2026-08-01
updated: 2026-08-01
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 — 씬 합성 (의도→메모리 파이프라인 2단계)"
module: "server/scene/ (신규), server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "scene-compiler, look-fx-merge, uniform-attributes, unasserted-enumeration, tracking, sequence-cue, trigger, nl-matching, safety-gate, value-line-guard"
tier: L
related_specs: [SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-PRECHK-001]
---

# SPEC-COPILOT-SCENE-001 — 씬 컴파일러

> **이 SPEC의 자리는 선행 SPEC이 명시적으로 비워 두었다.** FXLIB이 세 곳에서 이 좌석을 예약했다: `SPEC-COPILOT-FXLIB-001/spec.md:42`("프리셋 저장은 명시적 비목표다 … **그 축은 씬 컴파일러 후속 SPEC의 몫이다**"), `:140`(§D 제외 범위 — "**이 축은 씬 컴파일러 후속 SPEC의 몫이다**"), `:70`(REQ-FXLIB-001 — "**후속 소비자(씬 컴파일러·큐리스트 이펙트 축)가 소비 가능한 형상이어야 한다**"). 본 SPEC은 그 예약을 이행한다. 출처 서술과 인용 전문은 plan.md §A가 소유한다.
>
> **파이프라인의 위치**: LOOKLIB(정지 화면 어휘) · FXLIB(시간축 어휘)이 **1단계 — 의도**를 세웠다. 본 SPEC은 **2단계 — 메모리**다: 두 어휘를 하나의 큐로 합성해 콘솔의 기억(시퀀스·큐)에 새긴다. 두 계층과 같은 2단 형상(**match(순수·라이브러리 한정) → instantiate/compile(리그 바인딩·문자열 전용)**)을 미러한다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-08-01 | manager-spec | 최초 작성 (draft, Tier L). 출처: FXLIB이 예약한 후속 좌석(spec.md:42, :70, :140) + 사용자 결정 4건(2026-08-01, 증거 리포트 후 확정 — 재질의 금지): **D1** 트래킹 정책 = 전 큐 `/CueOnly`, **D2** 결합 순서 = 룩 먼저·충돌은 이펙트 우선, **D3** `/Merge` 미사용·신규 큐 번호 전용, **D4** Tier L. 조사: 코디네이터 직접 판독(`/CueOnly` 전수 grep · fx/looks 소스 · dedupe 경계 · 게이트 어휘 · 선행 SPEC 실측 기록). REQ **20건** · AC **22건** · ASSUMPTION **41~45(5건)** · clarification 마커 **0건** · 라이브 세션 **2회(M0·M8)**. 아티팩트 6종 동시 생성. |
| 0.2.0 | 2026-08-01 | manager-spec | **개정 — D1 폐기 후 옵션 D 채택.** 사유: **M0 라이브 프로브가 D1을 무너뜨렸다**(정본 기록 `progress.md §E.2`). ① ASSUMPTION-41(`/CueOnly` 접수)은 **기계 채널 소진** — 날조 플래그 `/CueOnlyy`가 `ok` + 저장까지 되어 `ok`도 재조회도 비변별로 판명. ② ASSUMPTION-42는 A/B 대조에서 **A=B**(둘 다 이월) — 후속 프로브가 **큐 생성이 실질 append-only**임을 실측해, 룰북이 정의한 `/CueOnly`의 보정 대상(“다음 큐”)이 저장 시점에 **존재할 수 없음**을 설명했다. ⇒ **`/CueOnly` 완전 제거**, 트래킹 정책을 **속성 집합 균일화 + 미주장 속성 전수 열거**(옵션 D)로 대체. 근거 조사: `.moai/reports/scene-uniform-attribute-set-proposal.md`. 반대로 ③ ASSUMPTION-44(룩+fx 결합) · ④ ASSUMPTION-45(충돌 승자)는 **사람 GUI 관측으로 GO** — D2/D3는 개정 없이 **강화**됐다. 동반 반영: plan-audit iter-1(PASS 0.91) minor 결함 6건 해소. 토큰 변동 REQ 20→**21**(REQ-SCENE-021 신설) · AC 22→**24**(AC-SCENE-023, AC-SCENE-024 신설) · ASSUMPTION 41·42 **moot**. **plan-artifact 해시 변경 ⇒ plan-audit 재실행 강제.** |
| 0.2.1 | 2026-08-01 | manager-spec | **iter-2 감사 결함 16건 수정 (정책 무변경).** plan-audit iter-2(FAIL 0.80)가 열거한 D1~D16만을 범위로 삼은 **문서 정합성 개정**이며 — 요구·인수·결정·마일스톤을 **신설하지 않는다**. major 5건: ① **AC-SCENE-019의 자기 검증 grep이 0건을 반환하던 문제** — `progress.md §E.2`에 **행두(column 0) 접두 행 6행**을 신설했고, AC가 명시한 grep을 실행해 **6건**을 실측했다. ② **REQ-SCENE-021에 판정 어휘 → 접두 행 매핑 표를 인라인**하고, 어느 접두어에도 대응이 없던 `INCONCLUSIVE` 행을 신설했다(교차 SPEC 포인터 의존 제거). ③ M4 착수 게이트가 **moot된 ASSUMPTION-41의 `GO`** 를 요구해 영구 차단이던 것을 **ASSUMPTION-44 `GO`** 로 교체했다. ④ `progress.md §E.2`에 **ASSUMPTION-43 판정 절을 신설**(폐쇄 어휘 `GO` — v1 범위 한정; `truncated: True` 실측을 정본에 기록)하고, 폐쇄 어휘 밖이던 "부분 검증"을 **정본 4 surface(spec·plan·acceptance·progress)에서** 교체했다 — 조사 스냅샷 `research.md §9`는 **M0 이전** 기록이므로 남겼고, 대신 iter-3에서 그 표에 승계 포인터를 달았다(N5·N6). ⑤ `plan.md §F.3` 공유 계약 표의 **SC-3 행 이탈**과 "둘/셋" 모순을 수정했다. minor 11건(D6~D16)은 개수·번호·헤딩·스테일 요약 일괄 정합. |
| 0.2.2 | 2026-08-01 | manager-develop | **iter-3 비차단 지적 9건(N1~N9) fix-forward — 정책·요구·인수 무변경, 재감사 불요.** plan-audit iter-3은 **PASS 0.90**(Tier L 문턱 0.85)이었고 N1~N9는 전부 문서 정합성 지적이다(감사 리포트 자신이 "None is blocking"으로 분류). M1 커밋에 배치했다. **N1** `progress.md §E.2`의 썩은 `plan.md` 줄 앵커 3건을 **절 앵커**(`§A.3`)와 출처 서술로 교체 — 줄 앵커는 다시 썩지만 절 앵커는 썩지 않는다. **N2** 타 SPEC을 가리키던 맨 `progress.md:NNN` 인용 11곳을 `SPEC-COPILOT-<X>-001/progress.md:NNN` 완전형으로 정규화(자기 문서 안에서 자기 `progress.md`로 해석되던 모호성 제거). **N3·N7** REQ-SCENE-021이 "접두 행을 **갖는** 명시적 섹션"을 요구해 **실제 기록 형태(§E.2 말미 통합 색인 블록)와 구조적으로 어긋나던 것**을 해소 — 요구를 완화한 것이 아니라 *판정 절의 존재*와 *행두 접두 행의 기계 판독 가능성*이라는 두 조건으로 정확히 재진술했고, `REOPEN_SCOPE`(사용자 재결정)를 범위 문장에 명시했다. **N5** v0.2.1 HISTORY의 "전 surface에서 교체" 과잉 주장을 실제 4 surface로 정정. **N6** `research.md §9`(M0 이전 스냅샷)에 승계 포인터 신설. **N8** AC-SCENE-024 케이스 ②의 재료를 **Zoom-only 룩**으로 좁힘 — Zoom 보유 16개 중 7개가 Iris도 가져 기대값이 `∅`가 되면 케이스가 무의미해진다(측정 재확인: Zoom 16 · Iris 8 · 양쪽 7). **N9** `progress.md`의 "무수정 보존"을 **append-only**로 정확히 재진술(v0.2.1·iter-3 추가분은 출처와 측정 순서를 밝힌 채 덧붙여졌다). **N4는 v0.2.1 시점에 이미 닫혔다** — 196·197을 실제로 재조회해 `§E.2`에 측정 순서와 함께 기록했다. 토큰 변동 0(REQ **21** · AC **24** · Out of Scope **16** · 접두 행 **6**). |
| 0.2.3 | 2026-08-01 | manager-develop | **M8 종단 라이브 반영 — 판정 어휘 대상 1종 확장 + 인수 실행 결과 기록.** REQ-SCENE-021의 `<대상>`에 **`AC-SCENE-nnn`을 추가**했다: M0의 판정 대상은 전부 미검증 전제(ASSUMPTION)였으나 **M8의 판정 대상은 인수 기준 그 자체**이며, 그 축에 ASSUMPTION 토큰을 새로 발급하는 것은 없는 전제를 만들어 내는 일이다. v0.2.1이 `INCONCLUSIVE` 행을 신설했을 때와 같은 종류의 확장이며 **접두어 4종·행두 앵커·한 판정당 1행 규율은 무변경**이다. 동반: AC-SCENE-019의 정리 기록을 **이행 완료**로 닫고(191~197 삭제 후 재조회 실측 — childCount 24→17, truncated True→False), AC-SCENE-021에 **실행 결과 `GO`**를 기록했다. 접두 행 grep은 **6행 → 8행**(M0분 6행 무변경 + `GO: AC-SCENE-019` · `GO: AC-SCENE-021`). **요구·인수를 신설하지 않았고 정책은 무변경이다.** M8이 발견한 비차단 결함 1건(SPEC 표제 문장이 상류 어휘 부재로 매칭되지 않음 — FXLIB 어미 `하는` · LOOKLIB `파란` 별칭)은 **고치지 않고 기록만** 했다(M8 규율: 코드 변경 0, 결함은 별도 커밋). 토큰 변동 0(REQ **21** · AC **24** · Out of Scope **16**). |

## A. 개요

**씬(Scene)** 은 하나의 큐다. 그 큐 안에는 세 가지가 함께 들어간다:

1. **룩** — 정적 attribute 값(색·딤머·포지션). 출처는 `server/looks/` 라이브러리.
2. **이펙트** — 시간축 페이저(스텝 열 + 위상 + 속도 + MAtricks 분할). 출처는 `server/fx/` 라이브러리.
3. **타이밍** — 시퀀스 번호·큐 번호·트리거(`TrigType` / `TrigTime`)·라벨.

지금 이 세 가지는 **서로 다른 툴이 서로 다른 큐를 만든다**. `instantiate_look`은 프리셋을 만들고, `instantiate_fx`는 `Cue 1` 고정의 시퀀스를 만들고, `prepare_songcue`는 큐리스트를 만든다. 사용자가 "파란 백라이트가 천천히 웨이브하는 씬"을 원하면 지금은 그 씬이 **하나의 큐로 존재할 수 없다**. 본 SPEC은 그 합성을 하는 단일 툴(`compile_scene`)을 세운다.

아키텍처 전제: **LOOKLIB·FXLIB 파이프라인의 세 번째 미러**. 씬 데이터는 신규 패키지 `server/scene/`의 자기 소유 스키마이고, 커맨드는 문자열로만 구성되며, 실행은 기존 `run_commands` → `gate.screen()` 단일 관문만 쓴다. `server/looks/**` · `server/fx/**` · `console/lua/**` · `server/rulebook/assets/**` · `server/safety/**`는 전부 **PRESERVE**이며 **읽기 import만** 한다(plan.md §A.5).

### 사전 확정 사실 (사용자 확정 D1~D4 — 재질의 금지. D1은 2026-08-01 M0 실측 후 개정, 나머지는 최초 확정 그대로)

#### D1 — 트래킹 정책: 속성 집합 균일화 + 미주장 속성 전수 열거 (개정 — `/CueOnly` 폐기)

**폐기된 것부터 적는다.** 최초 D1은 *"모든 Store에 `/CueOnly`를 단다"* 였다. **M0 라이브 프로브가 그 정책을 무너뜨렸고**(정본 기록 `progress.md §E.2`), 사용자가 대체 정책을 확정했다. 폐기 근거 2건은 전부 `[실측]`이다:

1. **접수를 세울 기계 채널이 없다.** 날조 대조군으로 발화한 **존재하지 않는 플래그** `/CueOnlyy`가 `ok`를 받고 **저장까지 됐다**. 그 큐는 기대한 이름·`cueNo`를 그대로 갖는다 — 진짜 `/CueOnly`가 만들 큐와 재조회로 구별 불가다. 즉 `ok`도 재조회도 **플래그 철자에 대해 비변별**이며, 최초 계획의 대비책("`ok`가 무력하면 재조회에 의존한다")도 성립하지 않는다.
2. **보정 대상이 존재할 수 없다.** 후속 프로브가 **이미 존재하는 큐보다 낮은 번호의 큐를 나중에 저장할 수 없음**을 실측했다(플래그 유무 무관 거부). 큐 생성이 **실질 append-only**이므로 저장 시점에 "다음 큐"가 있는 상황 자체가 만들어지지 않고, 룰북이 정의한 `/CueOnly`의 동작(*"stops the change tracking **into the next cue**"* — `31_choreography_patterns.md:59`, `:132`)은 보정할 대상을 영원히 갖지 못한다. A/B 대조에서 A군(`/CueOnly`)과 B군(무플래그)이 **동일하게 이월된 것**이 이것으로 설명된다.

**따라서 씬 컴파일러는 `/CueOnly`를 포함해 어떤 store 플래그도 발화하지 않는다.** 대신 트래킹이 샐 자리를 **구조적으로 좁히고, 좁히지 못한 자리는 매 컴파일마다 이름으로 노출한다.**

**(가) 균일 집합 — 코어 4**

```
SCENE_UNIFORM_ATTRIBUTES = ("Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B")
```

**룩을 담은 모든 씬의 룩 값 라인은 이 4개를 반드시, 이 순서로 포함한다.** 앞 씬이 설정한 속성을 뒤 씬이 명시적으로 덮으므로, 트래킹이 존재해도 이 4개 축에서는 결과가 같다.

이 집합은 발명이 아니라 **이미 참인 사실의 승격**이다 `[측정]`: 룩 라이브러리 32개 룩 전수에서 이 4개는 **32/32(100%)** 이고, 선언 순서까지 32/32가 위 순서다. 게다가 LOOKLIB이 이미 같은 교리를 세 테스트로 강제하고 있다(`server/tests/test_looks_library.py:231-237, :239-246, :248-252`), 그리고 그 근거 주석이 **트래킹 상속 논증 그 자체**다 — *"a look with no colour is a look whose colour is whatever the programmer left active — the same silent inheritance the rule above guards against"*. 즉 **자산 편집 0건**으로 성립한다.

**(나) `Zoom` · `Iris`는 균일 보장 밖 — 채움값을 발명하지 않는다**

두 속성은 등재율이 각각 16/32 · 8/32이고, **범위의 어느 끝이 무엇인지 콘솔에서 측정된 적이 없다** — 라이브러리 저자가 그 사실을 명문화해 두었다(`server/looks/library/worship.yaml:25-27`: *"it did not measure which end of each range is which"*). 룩이 선언한 경우에만 값 라인에 실리고, 선언하지 않은 룩에 씬 컴파일러가 값을 채워 넣지 않는다. `/CueOnly`를 버린 이유가 "미측정 축을 기본 경로에 넣지 않는다"였는데, 채움값 발명은 **같은 위험을 커맨드에서 값으로 옮기는 것**일 뿐이다(§D).

**(다) 미주장 속성 전수 열거 — 닫지 못한 자리를 이름으로 노출한다**

컴파일 결과는 **이 씬이 주장하지 않는 속성**을 전수 열거해 리포트에 싣는다:

```
미주장 = KNOWN_ATTRIBUTES − (룩이 낸 속성 ∪ fx가 구동하는 속성)
```

**유니버스의 정의는 상류 상수 `server.looks.schema.KNOWN_ATTRIBUTES`이지 오늘의 라이브러리 내용이 아니다.** 오늘 그 상수는 정확히 8개(`Dimmer` · `ColorRGB_R/G/B` · `Zoom` · `Iris` · `Pan` · `Tilt`)이고 이는 우연히 *유니온6 ∪ {Pan, Tilt}* 와 같지만, **그 등식은 예시일 뿐 정의가 아니다** — 라이브러리에서 `Iris` 보유 룩(오늘 8/32)이 전부 사라지면 유니온6은 줄어드는 반면 유니버스는 줄지 않아야 한다. 씬은 이 상수를 **읽기 import**로 소비하며 사본을 만들지 않는다(결정 E와 동형). "룩이 낸 속성 ∪ fx가 구동하는 속성"은 룩 값 라인의 속성 집합과 이펙트가 구동하는 속성 집합의 합집합이다.

이 계산은 **정적이며 콘솔 질의를 요구하지 않는다** — `§3.3`의 충돌 열거와 정확히 동형이다. 열거는 "이 축이 이월될 **수 있다**"를 말할 뿐 "이월됐다"를 말하지 않는다. 실제 이월 여부는 여전히 관측 불가다(§C.1).

**(라) 이 정책의 성질 — 무엇을 사고 무엇을 잃는가**

- **신규 미발화 커맨드 0개.** `/CueOnly`처럼 발화 실적 없는 커맨드를 도입하지 않으므로 미측정 위험이 0이다. FXLIB이 "신규 시퀀스 Cue 1만"으로 택한 구조적 회피와 같은 계열이다.
- **신규 발명 값 0개.** 자산 무편집(`server/looks/**`는 PRESERVE) — 경계 교차가 없다.
- **기계 검증 가능.** "룩 값 라인이 균일 집합을 이 순서로 담는다"와 "미주장 열거가 정확히 차집합이다"는 둘 다 **정적으로 단정**된다. 관측 불가 축을 우회한다.
- **잃는 것 — 의도적 지속(intentional tracking).** 트래킹은 조명 디자이너가 **의도적으로 쓰는 기법**이기도 하다(색만 바꾸고 위치는 유지). 균일 집합은 코어 4에 대해 "의견 없음"을 표현할 자리를 없앤다. 대신 (다)의 열거가 그 지속을 **우연이 아니라 매 컴파일마다 보고되는 사실**로 만든다.
- **닫지 못하는 축이 남는다 — Pan/Tilt.** 균일화로 **원리적으로 닫히지 않는다**(§D). 은폐하지 않고 (다)로 노출한다.
- **상속된 부채의 성질 변화**: SONGCUE도 무플래그로 Store하므로(`server/looks/songcue.py:462-466`) 이제 저장소에 **플래그 정책의 분기는 없다**. 남는 대비는 "SONGCUE는 균일 집합을 강제하지 않는다"이며, 그것은 **기록하되 고치지 않는다**(SONGCUE는 PRESERVE, research.md §5, design.md §6.1).

#### D2 — 결합 순서: 룩 먼저, 충돌은 이펙트 우선

하나의 씬 번들 안에서 커맨드 조립 순서는 **`design.md §3.1` 골격이 정본이다.** 본 절은 그 골격을 복제하지 않는다 — 병렬 브리프는 `design.md §3` 전문을 문면 그대로 인용하며(plan.md §F.3 SC-1), **여기에 두 번째 사본을 두면 그 사본이 세 번째 해석이 된다.** 요구 형태로 규범화된 판본은 REQ-SCENE-010이고, 그 역시 `design.md §3.1`을 정본으로 지시한다.

본 절이 소유하는 것은 골격이 아니라 **골격이 그런 모양인 이유** 둘이다.

**왜 룩이 먼저인가 — 이건 취향이 아니라 강제다.** 페이저는 2개 이상의 스텝을 요구하고(`server/fx/schema.py:66` `MIN_STEPS = 2`), 빌더는 `Step 1` 라인을 **발화하지 않는다**(`server/fx/instantiate.py:326-342` — *"`Step 1` is never emitted — the first step is the current one"*). 즉 **첫 스텝은 "현재 프로그래머 상태"이며 이펙트가 그 위에서 변형을 시작한다.** 룩은 그 현재 상태를 채우는 값이므로 스텝 1에 **자연히** 착지해야 하고, 그러려면 첫 `Step 2` 라인보다 앞에 있어야 한다. 룩을 이펙트 뒤에 놓으면 룩 값이 마지막 스텝에 얹혀 페이저의 종점이 되어 버린다.

**충돌 시 이펙트가 이긴다.** 같은 attribute를 룩과 이펙트가 모두 지정하면, 나중 라인이 프로그래머 값을 덮으므로 **이펙트가 승자**다. 이는 자연 귀결이지만 **조용해서는 안 된다** — 컴파일러는 덮인 attribute를 **전수 열거**해 리포트에 싣는다. 조용한 덮어쓰기는 결함이다(REQ-SCENE-005, AC-SCENE-005).

#### D3 — `/Merge` 미사용, 신규 큐 번호 전용

씬 컴파일러는 `/Merge`를 **0건** 발화하고, **비어 있는 큐 번호에만** 쓴다.

라이브 실측 근거 (`SPEC-COPILOT-SONGCUE-001/progress.md:337-344` — 실측 표 전재):

| 시퀀스 | 발화 | 재조회 childCount | 사용자 큐 | 앞 큐 |
|---|---|---|---|---|
| 101 | `Store … Cue 2 'PROBEA2' CueFade 2 /Merge` | **4** | **2** | **보존** |
| 102 | `Store … Cue 2 'PROBEB2' CueFade 2` (**`/Merge` 없음**) | **4** | **2** | **보존** |
| 102 | `Store … Cue 1 'PROBEB3' CueFade 2` (**기존 큐**, `/Merge` 없음) | 4 (불변) | 2 | **거부 — `Not allowed`** |

읽는 법: **새 큐 번호에는 `/Merge`가 있으나 없으나 결과가 같고**(둘 다 가산·보존), **기존 큐 번호에는 플래그 없는 Store가 거부되며 쇼파일이 불변**이다. 그 거부가 `server/fx/instantiate.py:225`가 *"the LAST line of defence"* 라고 부르는 안전망이다. `/Merge`를 달면 그 안전망이 **꺼진다** — 실익 0(새 번호에서 동작 동일)에 안전망만 잃는 거래이므로 채택하지 않는다.

`/Overwrite`는 **절대 금지**다. 4곳에서 블랙리스트로 봉쇄돼 있다: 룰북 `:57-58`(DESTRUCTIVE 표시), `server/safety/blacklist.yaml:18`(`"Store /overwrite"`), `DESIGN.md:133`, `server/web/preview.py:113`(`store_overwrite` 액션 라벨). 부재 단언은 **대소문자 무관**으로 쓴다 — 런타임 매칭이 이미 대소문자 무관이라 대소문자 고정 assert는 빌더가 `/overwrite`를 내도 **조용히 통과**하는 위양성 테스트가 된다(`SPEC-COPILOT-BUSKWIZ-001/design.md:209`).

#### D4 — Tier L

아티팩트 5종(spec/plan/acceptance/design/research) + progress = **디렉터리 6파일**. plan-auditor 문턱 **0.85**.

### 씬의 폐쇄 어휘 — 무엇을 합성할 수 있는가

씬은 **새 어휘를 만들지 않는다.** 룩 어휘는 LOOKLIB이, 이펙트 어휘는 FXLIB이 소유하고, 씬 컴파일러는 **두 라이브러리에 실존하는 엔트리만** 조합한다(REQ-SCENE-002). 씬이 자기 것으로 갖는 축은 **결합 규칙 + 타이밍**뿐이다:

| 씬의 축 | 내용 | 근거 |
|---|---|---|
| `look_id` | LOOKLIB 라이브러리 실존 id (선택 — 이펙트 단독 씬 허용) | `server/looks/loader.py` |
| `fx_id` | FXLIB 라이브러리 실존 id (선택 — 룩 단독 씬 허용) | `server/fx/loader.py` |
| 대상 그룹 | rig context 등재 번호 (발명 금지) | `31_choreography_patterns.md:210-211` |
| 시퀀스 번호 | 재조회 실측 또는 사용자 지정 | `server/fx/instantiate.py:218` |
| **큐 번호** | **비어 있는 정수 번호** (fx의 `Cue 1` 상수 고정을 넘는 축). 기존 큐보다 **낮은 번호는 콘솔이 거부**하므로 실질 오름 순이다(§C.1a-1) | D3 |
| 트리거 | `TrigType` / `TrigTime` (선택) | `31_choreography_patterns.md:106-117` |
| 라벨 | ASCII, Store 리터럴에 인라인 | `server/looks/songcue.py:462` |

**`look_id`와 `fx_id`가 둘 다 비면 씬이 아니다** — 로더·툴이 거부한다(REQ-SCENE-003).

## B. 요구사항 (GEARS)

### B.1 씬 데이터 계층 (스키마 + 결합 규칙)

- **REQ-SCENE-001** [Ubiquitous] — 씬 스키마 **shall** 다음 축을 정의한다: 아이덴티티(안정적 scene id, 표시 이름, 한국어 별칭/무드 키워드), 참조 축(`look_id` / `fx_id` — 각각 선택이되 **최소 1개 필수**), 타이밍 축(`cue_number` / `sequence_number` / `trig_type` / `trig_time` — 전부 선택), 라벨 축, 명시적 `schema_version`. 씬 스키마는 **룩·이펙트의 값 축을 복제하지 않는다** — 참조만 담는다.
- **REQ-SCENE-002** [Ubiquitous] — 씬 컴파일러 **shall** `look_id` / `fx_id`를 각각 LOOKLIB · FXLIB 라이브러리의 **실존 엔트리로만** 해석하고, 미등재 id를 명시 에러로 거부한다 — 엔트리 발명·합성·인라인 정의는 금지된다(LOOKLIB REQ-LOOKLIB-007 · FXLIB REQ-FXLIB-007 계승).
- **REQ-SCENE-003** [Unwanted] — the 로더·툴 **shall not** `look_id`와 `fx_id`가 **모두 부재**한 씬을 성립시킨다 — 합성할 것이 없는 씬은 씬이 아니며, 명시 에러로 거부된다.
- **REQ-SCENE-004** [Unwanted] — 씬 데이터 **shall not** per-show 값(구체 그룹 번호·이름, FID, 익스큐터 번호)을 정적 자산에 포함한다 — 리그 바인딩은 오직 컴파일 시점에 일어난다(LOOKLIB REQ-LOOKLIB-004 · FXLIB REQ-FXLIB-004 계승). 타이밍 축(시퀀스·큐 번호)은 **호출 인자**이지 정적 자산 필드가 아니다.
- **REQ-SCENE-005** [Event-driven] — **When** 룩과 이펙트가 같은 attribute를 지정하면, the 컴파일러 **shall** 이펙트 값을 승자로 삼고(D2 — 나중 라인이 이긴다), **덮인 attribute 전량을 열거해** 컴파일 결과에 싣는다. 조용한 덮어쓰기는 금지된다 — 열거가 비어 있는데 실제로 충돌이 있었다면 그것은 결함이다.
- **REQ-SCENE-006** [Event-driven] — **When** 씬 라이브러리가 로드되면, the 로더 **shall** 스키마를 검증하고 위반을 명시적 에러로 보고한다 — 부분적으로 깨진 라이브러리를 조용히 서빙하지 않는다. 검증 대상: 미지 필드, 중복 scene id, `look_id`/`fx_id` 동시 부재(REQ-SCENE-003), 수치 범위 이탈(`cue_number` > 0, `trig_time` ≥ 0), 미지 `trig_type`(폐쇄 집합 밖).

### B.2 자연어 매칭

- **REQ-SCENE-007** [Event-driven] — **When** 채팅 지시가 룩 축과 이펙트 축을 **함께** 담으면(예: "파란 백라이트가 천천히 웨이브하는 씬"), the 매칭기 **shall** 두 축을 분리해 각각 `find_looks` · `find_fx`의 매칭 규율로 해석하고, 씬 후보를 조합해 반환한다. 매칭 규율은 두 선행 계층의 미러다: **한국어 조사 처리**, **폴백 3종**(무매칭/저신뢰/모호), **동점은 None**(임의 선택 금지), **결정론적 정렬**(같은 입력 → 같은 출력).
- **REQ-SCENE-008** [Event-driven] — **When** 두 축 중 **한쪽만** 신뢰 매칭되면, the 매칭기 **shall** 그 사실을 **부분 매칭 신호로 구분해** 반환한다 — 매칭된 축만으로 씬을 세우는 것은 허용되지만(룩 단독·이펙트 단독 씬은 적법), **매칭되지 않은 축을 임의 기본값으로 채우는 것은 금지**된다.
- **REQ-SCENE-009** [Event-driven] — **When** 어느 축도 신뢰 매칭되지 않으면, the 시스템 **shall** 명시적 폴백 신호를 반환하고 기존 룰북 무드 폴백으로 강등한다 — 폴백 경로 자체는 무변경으로 보존된다.

### B.3 MA3 컴파일 (게이트 경유, 단일 큐)

- **REQ-SCENE-010** [Event-driven] — **When** 사용자가 하나의 씬에 대한 컴파일을 지시하면, the 컴파일러 **shall** D2 결합 순서(**정본 design.md §3.1**)로 커맨드 번들을 구성한다: 선두 `ChangeDestination Root` 정확 1회 → `ClearAll` → 그룹 선택(bare `Group <n>` **번호형 단일**, `Select` 접두 금지) → **룩 값 라인**(하나의 `;` 체인) → **fx 스텝 열**(스텝 1 값 → `Step 2` → 스텝 2 값 → …) → 위상 라인들 → 속도 라인 → (선언 시) MAtricks 라인들 → `Store Sequence <s> Cue <c> '<라벨>'`(**플래그 없음** — REQ-SCENE-013) → (MAtricks 사용 시) `Reset Selection MAtricks` → `ClearAll` → **(트리거 지정 시) 트리거 PROPERTY 2줄** → **(익스큐터 명시 지정 시) `Assign` 1줄**. **선택 말미 2종은 REQ-SCENE-016 · REQ-SCENE-017이 소유한다** — 본 요구의 사슬은 그 둘을 포함해야 완결이다. **산출물은 시퀀스 1개 + 큐 1개다.**
- **REQ-SCENE-011** [Ubiquitous] — 컴파일 번들 **shall** 검증된 프로그래밍 규율을 따른다: 목적지 1회, 캡처 전·Store 후 `ClearAll`, MAtricks를 쓴 번들은 Store 후 `Reset Selection MAtricks`, 라벨은 Store 리터럴에 인라인. **스텝 규율(FXLIB M0 실측 계승)**: `Step 1` 라인은 발화하지 않고, 둘째 스텝부터 **단독 `Step <k>` 라인**을 그 스텝의 값 라인 **앞에** 놓으며, 스텝 값 라인은 `;` 체이닝하지 않는다. **금지 형태 `Attribute '<attr>' At Step <k>` 0건**(FXLIB REQ-FXLIB-022 계승 — `ok:true`이나 효과 없음).
- **REQ-SCENE-012** [Ubiquitous] — **룩을 담은 씬의 룩 값 라인 shall 균일 속성 집합 `SCENE_UNIFORM_ATTRIBUTES = ("Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B")` 을 전부, 이 순서로 포함한다**(D1 (가)). 규율 4항:
  - **(a) 적용 범위**: 룩을 담은 씬에만 적용된다 — 이펙트 단독 씬에는 룩 값 라인 자체가 없다(REQ-SCENE-001, REQ-SCENE-003이 허용하는 적법 형태). 그 씬의 미주장 축은 REQ-SCENE-014 (d)의 열거가 전담한다.
  - **(b) 순서 강제**: 컴파일러는 값 시퀀스를 **균일 집합 순서 우선 + 나머지 선언 속성은 선언 순서 유지**로 정렬해 상류 `_values_line`에 넘긴다. 재조립이 아니라 **인자 순서 선택**이므로 결정 D(문자열 단일 출처)를 위반하지 않는다. 이 정렬은 오늘 라이브러리 32/32에 대해 **바이트 무변화**임이 측정됐다 `[측정]`.
  - **(c) 위반 시**: 균일 집합을 채우지 못하는 룩을 받으면 컴파일러는 번들 생성을 **거부(raise)** 한다 — `UNIFORM_ATTRIBUTES_INCOMPLETE` 사유. 조용한 부분 발화는 금지된다.
  - **(d) 균일 보장 밖**: `Zoom` · `Iris`는 룩이 선언한 경우에만 실린다. **컴파일러는 미선언 속성에 값을 발명해 채우지 않는다**(D1 (나) · §D).
- **REQ-SCENE-013** [Unwanted] — the 컴파일 **shall not**: (a) `/Overwrite`를 어떤 경로로도 발화하지 않고(블랙리스트 — `server/safety/blacklist.yaml:18`), (b) **`/Merge`를 어떤 경로로도 발화하지 않으며**(D3 — 대소문자 무관 부재), (c) 기존 큐 번호에 Store를 시도하지 않고(재조회로 실측한 빈 번호만 — 콘솔의 `Not allowed` 거부는 마지막 방어선이지 계획 경로가 아니다), (d) 시퀀스·큐 번호를 발명하지 않으며 — 재조회 결과의 `truncated`가 참이면 자동 배정을 **거부**하고 명시 보고한다(이 방어가 가상이 아님은 M0에서 실측됐다: `DataPool/Sequences` childCount **24**에 반환 **18** + `truncated: True` — `progress.md §E.2`) — (e) **Store 라인에 어떤 플래그도 달지 않는다**(`/CueOnly` 포함, 대소문자 무관 0건). 근거는 취향이 아니라 실측이다: **콘솔은 미지 store 플래그를 조용히 접수한다**(존재하지 않는 `/CueOnlyy`가 `ok` + 저장까지 됨 — `progress.md §E.2`). 즉 플래그 철자에 대해 `ok`도 재조회도 변별력이 없으므로, **오타가 침묵으로 통과하는 축 자체를 열지 않는다.**
- **REQ-SCENE-014** [Event-driven] — **When** 컴파일이 완료되면, the 시스템 **shall** 한국어 2단 리포트(요약 1단 + 상세 1단)를 반환하며, 그 문면은 아래 **네 주장을 분리해** 싣는다 — 뭉뚱그려 "확인했다"고 적는 것은 금지된다(SONGCUE REQ-SONGCUE-017 규율 계승, 구현 선례 `server/looks/songcue_report.py:15` `PROPERTY_UNOBSERVED_NOTE`):
  - **(a) 기계 확인된 사실** — 생성 시퀀스·큐의 **존재**와 이름·`cueNo`(재조회 실측), 발화 커맨드 수, 실행 결과(실패 시 `not_executed` 목록 전파; **비면제 라인의 `skipped_already_executed` 발생 시 그 목록도 전파하고 성공 보고를 금지**).
  - **(b) 기계 확인 불가 — 효과** — 이펙트의 모션·룩의 발색은 **기계로 확인되지 않는다.** 리포트 **shall** "무대/GUI에서 사람이 확인해야 한다"는 취지를 **무조건**(성공 경로 포함 전 경로에서) 싣는다. FXLIB이 같은 형상의 상수를 이미 갖는다(`server/fx/report.py:52` `EFFECT_EVIDENCE_NOTICE`) — 씬 리포트는 **동형의 자기 상수**를 갖고, 테스트는 **상수 동일성 검사**로 확인한다(산문 비교 금지 — 선례 `server/tests/test_songcue_report.py:119`).
  - **(c) 기계 확인 불가 — 트래킹 무해화** — **균일 집합을 발화했다는 것**과 **그래서 트래킹이 무해해졌다는 것**은 다른 주장이다. 전자만 기계로 확인되며(산출 문자열 정적 검사), 후자는 **관측 채널이 존재하지 않는다** — 큐의 내용을 돌려주는 경로가 없다(§C.1). 리포트 **shall** 이 둘을 분리해 적고, 균일성 확인을 "트래킹이 해결됐다"의 증거로 제시하지 않는다. **실패 모드가 `/CueOnly` 때와 동일하다** — 정책은 바뀌었으나 관측 천장은 그대로다.
  - **(d) 미주장 속성 전수 열거** — 리포트 **shall** `KNOWN_ATTRIBUTES − (룩이 낸 속성 ∪ fx가 구동하는 속성)`을 **전수 열거**해 싣는다(D1 (다)). 유니버스는 상류 공개 상수 `server.looks.schema.KNOWN_ATTRIBUTES`가 **정의**이며, *오늘 = 유니온6 ∪ {Pan, Tilt}* 는 **예시 값일 뿐 정의가 아니다**(AC-SCENE-024 · design.md §6 · plan.md 결정 K와 같은 문면). 계산은 **정적**이며 콘솔 질의를 요구하지 않는다. 문면은 "이 축은 앞 씬의 값이 **이월될 수 있다**"까지만 주장하며, **"이월됐다"고 적지 않는다** — 실제 이월 여부는 (c)와 같은 이유로 관측 불가다. 열거가 비어야 할 때 비고 채워져야 할 때 채워지는지는 정적으로 판정된다(AC-SCENE-024).
- **REQ-SCENE-015** [Ubiquitous] — **값 라인 충돌 가드 (1급 요구 — 경계 2중, FXLIB REQ-FXLIB-011 계승)**:
  - **(a) 번들 내 경계 (구성 시점)**: 번들 구성기 **shall** 구성 완료 시점에 비면제 커맨드 문자열의 **번들 내 유일성**을 검사하고, 중복이 존재하면 번들을 **생성하지 않고** 명시적 에러(`VALUE_LINE_COLLISION` 동형 사유)로 보고한다. 씬 번들은 룩 값 라인과 fx 스텝 값 라인을 **함께** 담으므로 FXLIB 번들보다 값 라인 수가 크고, 따라서 충돌 표면이 넓다.
  - **(b) 지시 턴 경계 (교차 호출 — 실행 결과 시점)**: dedupe의 실제 경계는 번들이 아니라 **지시 턴 전체**다(`server/orchestrator/runner.py` 가 `ExecutionContext(executed_ok=…)`를 다음 호출로 전달; 판정 주석 원문 "either **in a prior tool call** … or earlier in THIS bundle" — `server/orchestrator/tools.py:699-703`). the 툴 **shall** 실행 결과의 커맨드별 outcome을 검사해 **비면제 라인에 `skipped_already_executed`가 1건이라도 있으면 해당 컴파일을 성공으로 보고하지 않고** 교차 호출 충돌을 명시적 실패로 보고한다.
  - **(c) 1차 가드의 정책**: 위반 시 the 컴파일러 **shall** 번들 생성을 **거부(raise)** 한다 — 건너뛰기(skip)가 아니다. 근거: 씬 컴파일은 **하나의 Store**이고 남는 잔여가 없으므로, 부분 산출이라는 개념이 성립하지 않는다(FXLIB `server/fx/instantiate.py:432` 정책 계승 — 세 선례의 비교는 design.md §4).
- **REQ-SCENE-016** [Event-driven] — **When** 사용자가 트리거를 지정하면, the 컴파일러 **shall** 검증된 PROPERTY 형태만 발화한다: `Set Cue <c> Sequence <s> Property 'TrigType' '<Token>'` + `Set Cue <c> Sequence <s> Property 'TrigTime' <절대초>`(`31_choreography_patterns.md:106-117` · `server/looks/songcue.py:488-499`). 트리거 토큰은 **Capitalized 폐쇄 집합**(`Go` / `Time` / `Follow` / `Sound` / `BPM`)이며, `TrigTime`은 **시퀀스 시작 기준 절대 초**다(SONGCUE 라이브 실측 — `SPEC-COPILOT-SONGCUE-001/progress.md:502`: Cue 2에 `TrigTime 14`를 넣고 readback이 `"14.0"`이었다; 상대 해석이었다면 `"4.0"`이 관측됐어야 한다).
- **REQ-SCENE-017** [Unwanted] — the 컴파일 **shall not** `Assign Cue … /trig=<token>` 옵션 형태를 발화한다 — onPC 2.4.2에서 `"Illegal object"`를 반환한다(`31_choreography_patterns.md:115-117`). 또한 익스큐터를 **자동 배치하지 않는다**(빈 익스큐터는 식별 불가 — BUSKWIZ 측정 2); 사용자가 번호를 명시 지정한 경우에만 `Assign Sequence <n> At Executor <m>` 1줄이 번들 말미에 붙는다.

### B.4 툴 표면

- **REQ-SCENE-018** [Event-driven] — **When** 모델이 `compile_scene`을 호출하면, the 툴 **shall** (룩 id | fx id | 양쪽) + 대상 그룹 + (선택) 시퀀스/큐 번호·트리거·라벨·익스큐터 번호를 받아 **단일 번들을 통째로 조립**하고 기존 `run_commands` 경로로만 실행한다. 대상 그룹은 **rig context 재조회에 등재된 실존 그룹만**이며, 미등재 그룹 번호·이름의 발명과 `Fixture <slot>` 직접 타깃은 금지된다(슬롯≠FID).
  - **단일 툴은 강제된 형상이지 선호가 아니다**: `instantiate_look` → `instantiate_fx`를 한 지시 턴에서 연쇄하는 경로는 **원리적으로 성립하지 않는다.** dedupe 경계가 지시 턴 전체이고 `Step <k>`·스텝 값 라인이 패턴 간 공통 문자열이므로 2회차 번들은 접힌다 — FXLIB이 이를 제외 범위로 명문화했다(`SPEC-COPILOT-FXLIB-001/spec.md:146-148` §D). 따라서 씬은 **하나의 툴이 하나의 번들을 조립**해야 한다(design.md §2).

### B.5 안전·경계 규율 계승

- **REQ-SCENE-019** [Unwanted] — 단일 초크포인트: `server/scene/` **shall not** 어떤 transport(`server.bridge`/`pythonosc`)도, 게이트 표면(`server.safety.gate` / `server.safety.console` / `server.orchestrator.ports`)도 import하지 않는다 — 커맨드는 문자열로만 구성되고, 실행은 `run_commands` → `gate.screen()` 경로 하나다. 신규 `server/scene/`는 `server/tests/test_architecture.py`의 전역 import 스캔에 **자동 포섭**되며, 예외 명단(`_NAMED_TOOL_EXEMPTIONS`)에 항목을 추가하는 것은 금지된다.
- **REQ-SCENE-020** [State-driven] — **While** LiveLock이 활성인 동안, 씬 컴파일 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이다 — **Store 라인을 포함해** 전 커맨드가 `status == "proposal"`이며, 강등은 **실패가 아니라 답**이므로 `is_error is False`이고 `succeeded is False`다(`server/tests/test_fx_boundary.py:459` 패턴 계승). 본 SPEC은 그 강등 기제를 소비만 하고 수정하지 않는다.

### B.6 라이브 판정 기록 의무

- **REQ-SCENE-021** [Ubiquitous] — 라이브 세션(M0 프로브 · M8 종단)의 각 판정 — **그리고 그 판정이 유발한 사용자 재결정(`REOPEN_SCOPE`)** — 은 **shall** `progress.md §E.2`에 **폐쇄 판정 어휘**(`GO` / `NEGATIVE` / `CONDITION_NOT_MET` / `INCONCLUSIVE` / `REOPEN_SCOPE`) 중 하나로 판정되는 **명시적 섹션**으로 기록되고, 그 판정마다 대응하는 **접두 행**(`GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`)이 같은 `§E.2` 안에 **정확히 1행** 존재한다 — 각주로 대체되지 않는다. **접두 행의 배치는 판정 절 안이어도, `§E.2` 말미의 통합 색인 블록이어도 무방하다**(현 기록은 후자이며 `plan.md §B` M0 절과 AC-SCENE-019가 그 형태를 서술한다) — 요구되는 것은 **판정 절의 존재**와 **행두 접두 행의 기계 판독 가능성**이지 둘의 물리적 인접이 아니다. **두 어휘의 대응은 아래 매핑 표가 정본이다** — 어휘 5종과 접두어 4종은 개수가 다르므로 매핑 없이는 요구가 성립하지 않는다. 세부 3항:
  - **(a) 분리 기록**: 서로 다른 ASSUMPTION의 판정을 하나로 합치지 않는다. 특히 **접수(무엇이 받아들여졌는가)와 효과(무엇이 일어났는가)는 언제나 별개 판정**이다.
  - **(b) 부정 시 중단**: 사용자 확정 정책의 전제가 부정되면 the run-phase **shall** 중단하고 **블로커를 보고**한다 — 에이전트가 대체 정책을 골라 진행하는 것은 결정 월권이며 금지된다(plan.md §A.3 예외).
  - **(c) 대조군 선행**: `ok`를 어느 축의 증거로 채택하기 전에 **날조 대조군 1발**로 그 축에서 `ok`가 변별적임을 확립한다. 변별적이지 않다고 판명되면 **그 사실 자체를 판정으로 기록**한다.
  - 이 요구는 M0에서 **실제로 발동했다** — ASSUMPTION-41이 (c)에 걸려 `CONDITION_NOT_MET`으로 닫혔고 (b)에 따라 중단·보고됐으며, 그 결과가 D1 개정이다.

**판정 어휘 → 접두 행 매핑 (REQ-SCENE-021이 소유하는 정본)**

본 표는 **인라인 정본**이며 타 SPEC 요약을 가리키는 포인터로 대체되지 않는다 — 공유 계약을 요약본으로 참조하지 않는다는 규율(plan.md §F.3)이 판정 어휘에도 그대로 적용된다. PRECHK가 세운 4행(`GO` · `NEGATIVE` · `CONDITION_NOT_MET` · `REOPEN_SCOPE`)을 계승하되, **PRECHK에 대응 행이 없던 `INCONCLUSIVE`는 본 SPEC이 신설한다**(PRECHK 어휘에는 그 판정이 나오지 않았으나 본 SPEC의 ASSUMPTION-42가 실제로 그 판정을 받았다).

| 판정 어휘 | 접두어 | 행 형태 (한 판정당 정확히 1행) |
|---|---|---|
| `GO` | `GO:` | `GO: <대상> literal=<발화 리터럴> effect=<재조회 또는 사람 GUI 관측 증거>` |
| `NEGATIVE` | `DESCOPE:` | `DESCOPE: <대상> <부정 근거>` |
| `CONDITION_NOT_MET` | `SKIP:` | `SKIP: <대상> precondition=<미성립 전제> <사유>` |
| `INCONCLUSIVE` | `DESCOPE:` | `DESCOPE: <대상> verdict=INCONCLUSIVE <판정 불능 사유>` — **`verdict=` 키가 필수**다 |
| `REOPEN_SCOPE` | `REOPEN:` | `REOPEN: <대상> <재개방 사유>` |

`<대상>`은 `ASSUMPTION-nn`, 사용자 확정 결정 `Dn`, 또는 **인수 기준 `AC-SCENE-nnn`** 이다(본 SPEC의 `REOPEN_SCOPE`는 D1을, M8의 종단 판정은 `AC-SCENE-021`을 대상으로 삼는다). **AC 대상은 M8에서 신설됐다** — M0의 판정 대상은 전부 미검증 전제(ASSUMPTION)였으나 M8의 판정 대상은 **인수 기준 그 자체**이며, 그 축에 ASSUMPTION 토큰을 새로 발급하는 것은 없는 전제를 만들어 내는 일이다. `INCONCLUSIVE` 행을 신설했을 때와 같은 종류의 확장이다. **접두 행은 반드시 행두(column 0)에서 시작한다** — H4 헤딩이나 볼드/코드 스팬 안에 들어가면 `^` 앵커 grep이 잡지 못하고, 그러면 AC-SCENE-019의 기계 확인이 성립하지 않는다.

**`INCONCLUSIVE`가 `DESCOPE:`를 공유하는 근거, 그리고 그 대가**: 접두어 4종이 표시하는 것은 판정의 *원인*이 아니라 **판정이 그 축에 대해 내리는 처분**이다. `INCONCLUSIVE`는 측정을 수행했으나 대조군이 갈리지 않아 판정이 서지 않은 상태이고, 본 SPEC의 교리("미검증 축을 기본 경로에 넣지 않는다" — D1 (나) · §D `Zoom`/`Iris` 제외)에 따라 **판정이 서지 않은 축은 `NEGATIVE`와 동일하게 v1 기본 경로에서 내려간다.** 처분이 같으므로 접두어를 공유한다. `SKIP:`이 아닌 이유는 `CONDITION_NOT_MET`이 *"전제 미성립으로 측정하지 못했다"* 인 반면 `INCONCLUSIVE`는 *"측정했으나 판정이 서지 않았다"* 로 성질이 다르기 때문이다 — 측정하지 않은 것을 측정한 것처럼 세지 않는다는 `SKIP:`의 취지를 역으로 위반하게 된다. 대가는 `^DESCOPE:` grep이 부정과 판정 불능을 함께 잡는다는 것이며, 그래서 `verdict=INCONCLUSIVE` 키를 **필수**로 두어 두 경우를 행 안에서 구별한다 — 접두어는 공유하되 **판정 어휘 자체는 뭉치지 않는다**((a) 분리 기록의 연장이다).

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존, OSC `127.0.0.1` UDP. site config는 effective 값에서만 읽는다 — 하드코딩 금지.
- **기능 전제**: LOOKLIB(`server/looks/` — `status: completed`), FXLIB(`server/fx/` — `status: completed`, main `e4bc78e`에 머지됨), SONGCUE·BUSKWIZ·PRECHK·OVERLAP(전부 머지 완료), MVP 파이프라인(`run_commands`·`gate.screen()` 단일 관문·승인/제안 카드), `get_rig_context` 재조회 + 드릴다운. 전부 `related_specs`(비차단) 참조이며, **run-phase 킥오프 시 각 전제의 실제 상태를 재확인하고 어긋남을 progress.md에 기록한다**. (프론트매터가 `depends_on:`이 아니라 `related_specs:`를 쓰는 이유: 6건 전부 `status: completed`로 이미 머지돼 있어 차단할 대상이 없고, `depends_on:`은 Phase 1 Depends_on Pre-flight Check를 활성화해 **매 run 진입마다 완료된 SPEC 6건을 재해석**하게 만든다. 참조 관계는 남기되 게이트는 열지 않는다는 선택이다.)
- **실행 특성 (선행 SPEC 실측 전재 — `[실측]` 원출처는 해당 SPEC 기록)**: `run_commands`는 stop-on-first-failure이며 실패 이후 커맨드는 `not_executed`로 전파된다. 번들 규모 기준선 87줄/5.77s, 줄당 ~66ms(66.3-66.7ms — SPEC-COPILOT-BUSKWIZ-001/progress.md:278-281 실측 전재). 씬 번들은 **~14-22줄**(룩 값 라인 1줄 + fx 스텝 열 + 트리거 2줄)이므로 여유가 크다.

### C.1 검증 천장 — 무엇이 기계로 확인되고 무엇이 안 되는가

**이 표는 본 SPEC의 인수 설계 전체를 지배한다.** 아래 "NO" 행에 대해 기계 증거를 주장하는 리포트 문면·AC는 그 자체로 결함이다.

| 항목 | 기계 검증 | 경로 |
|---|---|---|
| 큐의 **존재**, 이름, 실제 `cueNo` | **YES** | `state` 재조회 |
| 시퀀스 이름, `childCount` | **YES** | `state` 재조회 |
| **값 라인의 균일 속성 집합** | **YES** | 산출 문자열 정적 검사 — 콘솔 무접촉 |
| **미주장 속성 열거의 정확성** | **YES** | 정적 차집합 — 콘솔 무접촉 |
| **룩/이펙트 충돌 attribute 열거** | **YES** | 정적 교집합 — 콘솔 무접촉 |
| `TrigType` / `TrigTime` | **YES** — 단 **게이트 우회 직결 경로** | 응답기 `prop` 동사(v1.5.0), `server/safety/console.py:391` `query_property` |
| `CueFade` | **NO** | 두 경로 모두 `property not readable: CueFade` |
| **큐의 내용(저장된 값)** | **NO** | 반환 경로가 존재하지 않는다 |
| **효과 / 모션 / 발색** | **NO** | 사람의 GUI 관측이 유일 |
| **트래킹 전파(= 균일화가 실제로 무해화했는가)** | **NO** | 관측 주체가 없다(`ui/src/components/ExecutionPreviewCard.tsx:61`) |
| **store 플래그의 철자·유효성** | **NO** | **M0 실측** — 존재하지 않는 `/CueOnlyy`가 `ok`를 받고 저장까지 됐고, 그 큐는 기대 이름·`cueNo`를 그대로 가졌다. `ok`도 재조회도 **비변별**이다 |

`Cmd()` OK는 효과 증거가 아니다. FXLIB이 이를 라이브로 증명했다 — *"스텝 쌍 없이 변형 라인만 발화하면 `ok:true` 전량에 모션 0이다"*(M0 §3 실패 3회, `SPEC-COPILOT-FXLIB-001/spec.md:50`). 본 SPEC의 M0가 여기에 **한 층을 더 얹었다**: `ok`는 *일반적으로는* 변별적이지만(점유 큐 재저장은 실제로 거부됐다) **미지 store 플래그에 한해 관대하다.** "`ok`는 아무 의미 없다"도 과잉 일반화이고 "`ok`면 파싱됐다"도 틀렸다 — **축마다 대조군으로 확인해야 한다**(REQ-SCENE-021 (c)).

### C.1a M0가 추가한 콘솔 제약 2건 (승계 필수)

1. **큐 생성은 실질 append-only다** `[실측]`. 이미 존재하는 큐보다 **낮은 번호**의 큐를 나중에 저장하면 플래그 유무와 무관하게 `Not allowed`로 거부된다. ⚠️ 이 발견은 룰북 `:56`의 서술(*"Cue numbers carry decimals — insert between existing cues with `1.5`, `1.55`"*)과 **표면상 충돌하며, 소수 번호 삽입은 미측정이다.** 정수 번호 역순 저장이 거부된다는 것만이 실측이고, **"삽입 일반이 불가하다"로 확대 해석하면 안 된다**(소수 큐는 §D 제외).
2. **거부 메시지 리터럴을 단정 근거로 쓰지 말 것** `[실측]`. 원인마다 메시지가 다르다 — 점유 큐 재저장은 `User Canceled Command`, 역순 저장은 `Not allowed`였다. SONGCUE M0가 기록한 것은 후자다. **메시지 문자열 일치로 원인을 판정하는 테스트·서술을 세우지 않는다.**

### C.2 미검증 전제 (ASSUMPTION — FXLIB이 36~40을 사용, 본 SPEC은 41부터)

**각각이 실제로 막는 대상은 서로 다르다** — 전부가 저작을 막는 것은 아니다(LOOKLIB 순서 결함 교훈 계승, 표의 소유는 plan.md §A.2).

**M0 실행 완료 (2026-08-01) — 판정 정본은 `progress.md §E.2`다.** 아래는 그 판정의 요약과 SPEC 저작에 미친 영향이며, 증거 원문을 여기에 복제하지 않는다.

- **ASSUMPTION-41 (`/CueOnly` 접수 가능성)** — **`CONDITION_NOT_MET` → moot.** 판정 이력: 날조 대조군이 `ok`로 통과·저장까지 되어 **기계 채널이 소진**됐고(§C.1 마지막 행), 접수를 입증할 제3 경로가 없어 `GO`로 올릴 수 없었다. **가정 자체가 소멸한 이유**: D1 개정으로 `/CueOnly`를 포함한 store 플래그를 일절 쓰지 않으므로 접수 여부가 더 이상 어느 것도 막지 않는다. **삭제하지 않고 이력으로 남긴다** — 이 판정이 D1 개정의 직접 원인이기 때문이다.
- **ASSUMPTION-42 (`/CueOnly`의 트래킹 차단 효과)** — **`INCONCLUSIVE` → 실질 무효 → moot.** A/B 대조에서 **A군(`/CueOnly`)과 B군(무플래그)이 동일**했다(둘 다 Cue 2에서 딤머 잔존). B군이 남았다는 것은 **전방 트래킹이 이 콘솔에서 실재함**을 확인해 주므로 관측 설계 자체는 유효했다. A=B의 설명은 §C.1a-1의 append-only 제약이다 — 보정 대상이 존재할 수 없다. 41과 동일하게 moot이며 이력으로 남긴다.
- **ASSUMPTION-43 (임의 큐 번호 Store 가능성)** — **`GO`, 단 판정 대상을 v1이 실제로 쓰는 범위로 좁혀서다.** (판정 정본 `progress.md §E.2`. 이전 판본이 쓴 *"부분 검증"* 은 REQ-SCENE-021의 폐쇄 어휘 밖이었으므로 폐쇄 어휘로 교체했다 — 판정 내용은 바뀌지 않았고 어휘만 바뀌었다.) 성립(`GO`의 근거): **신규 시퀀스의 정수 큐 번호 Store가 성립한다** — SONGCUE가 `Cue 2`를 라이브로 성립시켰고(`SPEC-COPILOT-SONGCUE-001/progress.md:337-344`) M0 프로브도 같은 형태를 냈다. **좁힌 근거 2건이 같은 세션에서 실측됐다**: ① 존재하는 큐보다 낮은 번호의 나중 저장은 플래그 무관 거부된다(§C.1a-1), ② **`truncated: True`가 실측됐다**(childCount 24 / 반환 18) — REQ-SCENE-013 (d)의 `truncated` 거부 가드가 **가상의 방어가 아니라 실재 조건에 대한 방어**임이 확인됐다. 좁히지 않은 원형(*"임의"* 큐 번호)은 역순 축에서 부정이 실측됐고 소수 축은 미측정이므로 **둘 다 §D 제외**다. 막는 대상: **없음** — v1은 정수·신규·오름 번호만 쓴다.
- **ASSUMPTION-44 (룩 값 라인과 fx 스텝 열의 결합 성립)** — **`GO` (사람 GUI 관측).** 관측: **파란색이 유지된 채 딤머가 순차 웨이브.** 기대 형상과 일치한다. ⇒ **`design.md §3.1` 결합 순서 골격이 실측으로 확정됐다** — 룩의 정지 값이 스텝 축에 흡수되지 않고 베이스로 남는다. **이제 가정이 아니라 실측이다.**
- **ASSUMPTION-45 (충돌 attribute의 승자)** — **`GO` (사람 GUI 관측).** 관측: 룩 `Dimmer At 80` + fx `Dimmer` 스텝 열(100/0)에서 **딤머가 펄스 — 이펙트 승.** ⇒ **`design.md §3.3` 충돌 규칙이 확정됐다.** 열거 자체는 정적 계산이므로 이 관측과 무관하게 정확하다.

**⚠️ 승계 필수 — M0가 남긴 프로브 설계 결함**: 플랜의 프로브 A와 B가 **같은 `Sequence 191 Cue 1`을 대상으로 삼았다.** 대조군이 표적을 점유해 설계대로는 B를 실행할 수 없었고, 실제로는 그 충돌을 이용한 추가 발화(A' — 점유 큐 무플래그 Store)가 판정의 핵심 근거가 됐다. **결함이 관측을 도운 우연이며, 후속 프로브는 프로브별 시퀀스를 분리해야 한다.**

**정리 의무 (미이행)**: M0 프로브가 만든 시퀀스 **191·192·193·194·195·196·197**이 쇼파일에 잔존한다. `Delete`가 블랙리스트라 툴 경로로 제거 불가 — 사용자 GUI 삭제가 필요하며 그 사실을 `progress.md`에 기록한다.
- **측정된 기준선**: 기반 `main` = `e4bc78e`(clean). pytest/vitest 수치는 plan-phase가 단언하지 않는다 — **각 마일스톤 착수 직전 직접 실측**한다(baseline-integrity 원칙). 오케스트레이터 세션 실측값(2026-08-01, 참고용): pytest 3432 passed / 5 skipped, vitest 223. 본 아티팩트 6종의 커밋 SHA는 자기참조 불가이므로 `pending-backfill`이다.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 오디오 분석 / 음악 구조 추출

- 오디오 파일 판독, BPM 자동 검출, 섹션 경계 자동 분할 일체. 본 SPEC의 타이밍은 **호출자가 주는 수치**이며, 곡 구조 축은 SONGCUE(큐리스트)의 영역이다.

### Out of Scope — 프리셋 참조 큐

- 큐가 프리셋을 참조하게 만드는 축 일체. `Assign Preset … At Cue` 계열 문법은 **저장소 근거 0건**이며, "큐는 프로그래머 상태를 직접 캡처한다"가 확립된 사실이다(`SPEC-COPILOT-SONGCUE-001/spec.md:264-267`). 씬 컴파일러는 룩의 **값**을 큐에 재캡처하며, `instantiate_look`이 만든 프리셋을 **가리키지 않는다**.

### Out of Scope — 익스큐터 자동 배치·바인딩

- 빈 익스큐터 탐색·자동 `Assign` 일체 — 빈 익스큐터는 식별 불가다(BUSKWIZ 측정 2). 사용자 명시 지정 시의 `Assign Sequence <n> At Executor <m>` 1줄만 선택적으로 허용된다(REQ-SCENE-017).

### Out of Scope — 큐 편집 · 재배열 · 삭제

- 기존 큐의 값 수정, 큐 번호 재배열, `Delete Cue` 일체. v1은 **비어 있는 큐 번호에 새로 쓰는 것**만 한다(D3). 편집 경로는 기존 큐 번호를 건드리므로 `Not allowed` 안전망과 정면 충돌한다.

### Out of Scope — 섹션 점프 / `Goto Cue`

- `Goto Cue <n>` 류 큐 이동 커맨드 일체. 게이트의 `RECOGNIZED_REFERENCE_TYPES`(`server/safety/classify.py:44`)는 `("Macro", "Plugin", "Sequence", "Executor")`이며 **`Cue`가 없다** — 큐 참조 커맨드는 게이트가 인식하는 참조 종별이 아니므로, 그 축을 여는 것은 게이트 어휘 확장을 요구한다. 본 SPEC은 `server/safety/**` 무변경이므로 보류한다.

### Out of Scope — `CueFade` 및 판독 불가 프로퍼티

- `CueFade` 설정 축 일체. 두 경로 모두 `property not readable: CueFade`이므로 **설정해도 확인할 수 없다**(§C.1). 확인 불가 프로퍼티를 v1 산출물에 넣지 않는다.

### Out of Scope — 소수 큐 번호

- `Cue 1.5` / `1.55` 류 소수 큐 번호. 룰북 산문(`:56`)에만 존재하고 라이브 실측 0건이다(ASSUMPTION-43). v1은 정수 큐 번호만 쓴다. **M0가 정수 역순 저장의 거부를 실측했으나(§C.1a-1) 소수 삽입은 여전히 미측정이며, 그 실측을 "삽입 일반 불가"로 확대 해석해 이 제외의 근거로 삼지 않는다** — 제외 근거는 어디까지나 **미측정**이다.

### Out of Scope — 지시 턴당 2회 이상의 컴파일

- 한 지시 턴에서 `compile_scene`을 2회 이상 온전히 성립시키는 축. dedupe 경계가 **지시 턴 전체**이고 `Step <k>`·값 라인이 씬 간 공통 문자열이므로 2회차 번들은 접힌다(FXLIB `spec.md:146-148` 계승). v1은 넓히는 대신 **명시 실패로 막는다**(REQ-SCENE-015 (b)).

### Out of Scope — dedupe 전역 의미론 변경

- `_PROGRAMMER_STATE_COMMANDS` 면제 집합 확장, dedupe 판정 루프 개정 일체. dedupe 규칙 개정은 **기각된 선례**다(BUSKWIZ 결정). SONGCUE가 같은 규율을 명문화했다 — *"본 SPEC 하나를 위해 전역 실행 의미론을 바꾸지 않는다"*(`spec.md:298-302`).

### Out of Scope — 룰북 자산 변경

- `server/rulebook/assets/v2.4.2/**` 일체 (PRESERVE — byte-diff 0). `server/tests/test_fx_boundary.py:595`가 *"the rulebook never learned about fx"* 를 단언하는 것과 같은 규율로, **씬 계층도 룰북 어휘를 추가하지 않는다.** 툴 발견성은 툴 스키마 설명 문면이 전담한다.

### Out of Scope — Pan/Tilt 트래킹 이월

- **movement 씬이 남긴 Pan/Tilt의 다음 씬 이월을 v1에서 닫지 않는다.** 균일화로 **원리적으로 닫을 수 없는 축**이며, 이것을 적지 않으면 *"균일화로 트래킹을 구조적으로 회피했다"* 는 서술이 **과잉 주장**이 된다. 구조 근거 3건이 맞물린다: ① **룩은 Pan/Tilt를 정적 값으로 가질 수 없다** — `server/looks/loader.py:105-110`이 풀 패밀리 없는 속성을 구조적으로 거부하고(*"movement-only attributes may appear inside a movement spec only"*), `server/looks/schema.py:47`이 `MOVEMENT_ONLY_ATTRIBUTES = ("Pan","Tilt")`를 `ATTRIBUTE_POOL_FAMILY`에서 제외한다 — 스키마 주석이 이유를 적는다: *"As a static value they are exactly the hard pan/tilt the SPEC forbids."* ② 라이브러리 32개 룩의 movement 선언은 **0/32**이며 `TestMovementAbsence`가 그것을 단언한다. ③ **fx 12개 중 8개(67%)가 Pan/Tilt 전용이다**(`server/fx/library/movement.yaml`) `[측정]`. ⇒ movement 씬 뒤에는 위치가 트래킹되고, **룩 값 라인이 그것을 덮을 수단이 구조적으로 없다.** 우회는 전부 경계를 넘는다 — 씬이 자체 `Attribute 'Pan' At <n>`을 발화하면 LOOKLIB이 명문으로 금지한 hard pan/tilt를 우회 발화하는 것이고 값도 미측정(`server/fx/schema.py:78-84`가 *"the repository carries no measured unit or fixture limit"* 라고 자인)이며, 로더 완화는 PRESERVE 위반이다. **은폐가 아니라 가시화로 다룬다**: REQ-SCENE-014 (d)의 미주장 열거가 이 구멍을 **매 컴파일마다 이름으로 노출**한다.

### Out of Scope — `Zoom`/`Iris` 채움값 발명

- **룩이 선언하지 않은 `Zoom`/`Iris`를 씬 컴파일러가 채워 넣는 축 일체**(범위 중점·극값·룩별 저작 어느 형태든). 두 속성은 **범위의 어느 끝이 무엇인지 콘솔에서 측정된 적이 없고**, 라이브러리 저자가 그 사실과 함께 저작 원칙을 명문화해 두었다(`server/looks/library/worship.yaml:25-27`: *"it did not measure which end of each range is which, so both are used sparingly and only where a wrong direction would be a cosmetic miss"*). 채움은 그 원칙을 정면으로 뒤집으며(“드물게”가 소멸한다), 미측정 방향 가정 위에 놓이는 값을 24개 → 64개로 늘린다 `[측정]`. **`/CueOnly`를 버린 이유가 "미검증 축을 기본 경로에 넣지 않는다"였는데, 채움값 발명은 그 위험을 커맨드에서 값으로 옮길 뿐 성질이 같다.** 이 축은 `Zoom`/`Iris` 방향이 라이브로 실측된 뒤에 재검토할 후보다.

### Out of Scope — SONGCUE 균일 집합 소급 적용

- SONGCUE가 균일 속성 집합을 강제하지 않는다는 사실은 **기록하되 고치지 않는다**. `server/looks/**`는 PRESERVE이며, 소급 정책 변경은 별도 SPEC의 결정이다. (D1 개정으로 **store 플래그 정책의 분기는 사라졌다** — SONGCUE도 씬도 무플래그다. 남는 대비는 균일 집합 축뿐이다.)

### Out of Scope — 콘솔측 Lua 변경 / 비게이트 실행 경로

- `console/lua/copilot_responder.lua` 및 신규 프로토콜 동사 일체 (PRESERVE). 실행용 REST 엔드포인트, 제2 스크리닝, `server/scene/`의 OSC·게이트 표면 직접 import 일체 (REQ-SCENE-019).

### Out of Scope — UI 표면 변경

- `ui/src/**` 및 패널 타일 추가. v1 표면은 기존 채팅 + 툴이다.

### Out of Scope — 생성형 Lua 경로

- 씬 컴파일을 Lua 플러그인 생성으로 구현하는 축. v1 번들은 ~14-22줄 규모이므로 커맨드라인 문자열로 충분하다.

## E. 참조 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line — 착수 직전 재실측 관례 적용) |
|---|---|
| 후속 좌석 예약 3곳 (본 SPEC의 존재 근거) | `SPEC-COPILOT-FXLIB-001/spec.md:42, :70, :140` — `[문서]` |
| **`/CueOnly` 기계 판정 불능 + 미지 플래그 조용한 접수** | `progress.md §E.2` (M0 프로브 A/A′ — `/CueOnlyy`가 `ok`+저장) — `[실측]` |
| **큐 생성 실질 append-only (역순 저장 거부)** | `progress.md §E.2` (프로브 D″) — `[실측]` |
| **전방 트래킹 실재 (무플래그 B군 잔존)** | `progress.md §E.2` (프로브 D) — `[실측]` |
| **룩+fx 결합 성립 · 충돌 시 이펙트 승** | `progress.md §E.2` (프로브 C·E, 사람 GUI) — `[실측]` |
| **`truncated: True` 실재 조건** | `progress.md §E.2` (childCount 24 / 반환 18) — `[실측]` |
| **균일 집합 = 코어 4가 32/32, 선언 순서까지 일치** | `server/looks/library/*.yaml` 파싱 계산 + `server/looks/schema.py:39-43` `CONFIRMED_ATTRIBUTES` — `[측정]`+`[코드]` |
| **코어 4 균일성이 이미 테스트로 강제됨** | `server/tests/test_looks_library.py:231-237, :239-246, :248-252` — `[코드]` |
| **미주장 열거 유니버스 = `KNOWN_ATTRIBUTES`(8개)** | `server/looks/schema.py:52-54` — `[코드]` |
| **`Zoom`/`Iris` 방향 미측정 (자인 문면)** | `server/looks/library/worship.yaml:25-27` — `[문서]` |
| **룩은 Pan/Tilt 정적 값 불가** | `server/looks/loader.py:105-110` · `server/looks/schema.py:11-14, :47, :62-69` — `[코드]` |
| **fx 12개 중 8개가 Pan/Tilt 전용** | `server/fx/library/movement.yaml` · `server/fx/schema.py:46-56` — `[측정]`+`[코드]` |
| `/CueOnly` 문법·트래킹 모델 (폐기된 D1의 원 근거) | `31_choreography_patterns.md:59, :130-134` — `[문서]` |
| Store 플래그 라이브 실측 (신규 번호 = `/Merge` 불요 · 기존 번호 = `Not allowed`) | `SPEC-COPILOT-SONGCUE-001/progress.md:337-344` — `[실측]` |
| `Not allowed` = 마지막 방어선 | `server/fx/instantiate.py:225` — `[코드]` |
| `/Overwrite` 봉쇄 4곳 | `31_choreography_patterns.md:57-58` · `server/safety/blacklist.yaml:18` · `DESIGN.md:133` · `server/web/preview.py:113` — `[코드]` |
| 대소문자 무관 assert 논거 (대소문자 고정은 위양성) | `SPEC-COPILOT-BUSKWIZ-001/design.md:209` — `[문서]` |
| **`MIN_STEPS = 2` + `Step 1` 미발화** (룩 먼저의 강제 근거) | `server/fx/schema.py:66` · `server/fx/instantiate.py:326-342` — `[코드]` |
| fx 큐 번호 상수 고정 (씬이 넘어야 할 축) | `server/fx/instantiate.py:96` (`_CUE_NUMBER = 1`), `:481` (Store 라인) — `[코드]` |
| `select_sequence_number` 2벌 (fx는 `requested=` 지원) | `server/fx/instantiate.py:218` · `server/looks/songcue.py:286` — `[코드]` |
| 1차 가드 정책 3갈래 (raise / skip / skip+ledger) | `server/fx/instantiate.py:432` · `server/looks/busking.py:240` · `server/looks/songcue.py:436` + ledger `:243` — `[코드]` |
| 2차 가드 (지시 턴 경계) — **looks 쪽에 대응물 없음** | `server/fx/instantiate.py:537` `collided_lines` — `[코드]` |
| dedupe 판정 + 면제 3종 + 축적 경계 | `server/orchestrator/tools.py:327-331, :688-712` · `runner.py` ExecutionContext — `[코드]` |
| 툴 핸들러 = `run_commands`의 **caller** (제2 실행 표면 금지) | `server/orchestrator/tools.py:638, :848-858, :1116, :1688-1698` — `[코드]` |
| 트리거 PROPERTY 형태 + `/trig=` 금지 | `31_choreography_patterns.md:106-117` · `server/looks/songcue.py:488-499` — `[문서]`+`[코드]` |
| `TrigTime` = 절대 초 (라이브 2점 판별) | `SPEC-COPILOT-SONGCUE-001/progress.md:502` — `[실측]` |
| 시퀀스 라벨 위치 (첫 Store 직후) | `server/looks/songcue.py:258-266`, `_first_store_index:520` — `[코드]` |
| 큐 사후 개명 경로 부재 (`Label Cue` 0건) | SONGCUE REQ-SONGCUE-008 — `[문서]` |
| 프리셋 참조 문법 근거 0건 | `SPEC-COPILOT-SONGCUE-001/spec.md:264-267` — `[문서]` |
| 게이트 참조 종별에 `Cue` 부재 | `server/safety/classify.py:44` — `[코드]` |
| `query_property` (게이트 우회 직결 경로) | `server/safety/console.py:391` — `[코드]` |
| 효과 증거 상수 선례 + 상수 동일성 검사 선례 | `server/fx/report.py:52` · `server/looks/songcue_report.py:15` · `server/tests/test_songcue_report.py:119` — `[코드]` |
| 경계 AST 스캔 · 예외 명단 고정 · LiveLock 강등 패턴 | `server/tests/test_fx_boundary.py:132, :228-230, :459` · `test_looks_boundary.py:85` — `[코드]` |
| 룰북 무학습 단언 선례 | `server/tests/test_fx_boundary.py:595` — `[코드]` |
| 한 턴 2회 인스턴스화 불가 (단일 툴의 강제 근거) | `SPEC-COPILOT-FXLIB-001/spec.md:146-148` — `[문서]` |
| 전역 실행 의미론 불변 규율 | `SPEC-COPILOT-SONGCUE-001/spec.md:298-302` — `[문서]` |
| 트래킹 미관측 진술 | `ui/src/components/ExecutionPreviewCard.tsx:61` — `[코드]` |
