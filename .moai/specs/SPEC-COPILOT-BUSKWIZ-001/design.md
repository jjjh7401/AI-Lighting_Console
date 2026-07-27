# SPEC-COPILOT-BUSKWIZ-001 — 설계 근거 (design)

status: draft (v0.1.3, 2026-07-27) · Tier L · 본 문서는 spec.md 요구의 설계 근거와 위험 검토를 담는다. **§5는 한 부분이다 — §5.1 해소된 결정 7건(A~G), §5.2 열린 슬롯 0건.** LOOKLIB이 v0.3.0에서 도달한 "열린 슬롯 0건" 상태를 착수 시점부터 계승한다.

> **참조 규약 (v0.1.3에서 확정 — 이 문서 전체에 적용).** **SSOT(spec.md · acceptance.md)는 줄번호로 인용하지 않는다.** `REQ-BUSKWIZ-nnn` · `AC-BUSKWIZ-nnn` · `ASSUMPTION-nn` · 절 제목(`spec.md §C`) · 명명된 하위 절(`spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)`)처럼 **개정을 견디는 토큰**만 쓴다. 근거는 감사 실측이다 — 형제→SSOT 줄 앵커 52개 중 10개가 빈 줄을, 6개 이상이 다른 내용을 가리키고 있었고, 본 문서만도 v0.1.1→v0.1.2에서 16곳을 재접지해야 했다. **토큰은 내용이 사라지면 토큰도 사라져 즉시 드러나지만, 줄번호는 조용히 옆 문장을 가리킨다.** 반면 **`파일:줄`은 코드·룰북·타 SPEC 아티팩트에 그대로 유지**한다 — 코드는 커밋 없이 움직이지 않고 다른 안정 식별자가 없으며, 완료·동결된 SPEC(LOOKLIB · EXECBODY)의 줄도 밀지 않는다.

> **v0.1.4 — 재감사(PASS 0.88) 조건부 지적 반영.** §5는 또 무변경(결정 7건 A~G · 열린 슬롯 0건). 단 하나가 바뀌었다 — **REQ-BUSKWIZ-010의 도달 가능 트리거 열거에서 "룩별 패밀리 수 차이"가 삭제되었다**(재감사 D2 부분 닫힘). 값이 없는 패밀리는 `_plan_stores`가 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않으므로(`server/looks/instantiate.py:332-334`) 그 룩은 `skipped=0 complete=True`인 **완전 성공**이며 보고할 건너뜀이 없다(실행 확인: `ballad-single-key` P=4 / `ballad-moonlight` P=2). 최종 열거는 **풀 미해석 · 라벨 충돌 둘**이고 점유 미관측은 REQ-BUSKWIZ-009가 따로 덮는다. 아래 v0.1.3 항의 "3경로" 표기는 **그 시점의 기록**이며 현행 열거가 아니다 — 본 문서 §4 위험 #7 행·상세와 AP-4는 v0.1.4 열거로 갱신되어 있다.
>
> **v0.1.3 — spec.md/acceptance.md v0.1.3 반영 (독립 plan-audit FAIL 0.78 후속).** **§5는 또 무변경** — 결정 7건(A~G), 열린 슬롯 0건, 새 결정 문자 0건. 요구·AC·마일스톤 집합도 전부 무변경이며 바뀐 것은 문언과 검증 수단이다.
> (D2) **REQ-BUSKWIZ-010의 트리거가 도달 불가였다** — "슬롯이 부족해"는 발생할 수 없다(`_first_free_slot`(`server/looks/instantiate.py:307-312`)에 상한이 없고, 풀 용량 상수가 리포지토리 0건이며, `_observed_contents`(`:195-215`)가 풀 크기를 보고하지 않는다). 본 문서에서 그 표현을 근거로 쓰던 세 곳(§4 위험 #7 행·상세, AP-4)을 **도달 가능한 3경로**(패밀리 수 차이 / 풀 미해석 / 라벨 충돌)로 교체했다. **이것은 본 문서가 v0.1.0부터 "슬롯 소진"을 부분 성공의 대표 사례로 써 온 것에 대한 정정**이다 — 사례가 도달 불가면 그 사례로 세운 테스트도 도달 불가다.
> (D4) **PRESERVE에 `server/looks/instantiate.py` 추가** → §2 무변경 목록. 결정 E는 "frozen을 **바깥에서** 감싼다"는 형상이므로, 그 파일을 고치게 되는 것이 **결정 E의 반증**이고 PRESERVE에 넣어야 diff로 드러난다.
> (D6) **AC-BUSKWIZ-012 ①의 번호 출처 모순 해소** — 본 문서 §4 위험 #4가 "확인된 번호 = 점유된 익스큐터"를 서술해 놓고도 AC는 `resolved_executor_nos`를 출처로 적고 있었다. SSOT가 "M0가 GO로 판정한 빈-익스큐터 식별 경로가 반환한 번호"로 교체했고, §4에 그 해소를 표기했다.
> (D7) `product.md` 비목표 인용 `:43`(빈 줄) → **`:44`** → §8.
> 함께: AC-BUSKWIZ-013 ②의 수단이 소스 grep → **생성 커맨드 튜플 전수 + 비공허성 assert**, AC-BUSKWIZ-002 ③이 import 스캔 → **AST 스캔**으로 바뀌어 §5.1 결정 G·§6.3에 반영. **모든 SSOT 줄 앵커를 토큰으로 교체**(위 참조 규약).
>
> **v0.1.2 — ASSUMPTION-19 신설 · 요구 정합 결함 1건 해소.** **§5 무변경.** 익스큐터 축의 게이트가 **2항 → 3항 논리곱**(ASSUMPTION-16 ∧ 17 ∧ 19)이 되었고, 근거는 **얹을 대상의 부재**다: 라이브 검증된 유일한 바인딩 커맨드 `Assign Sequence <n> At Executor <m>`(`31_choreography_patterns.md:99`, `:168`)의 목적어는 **시퀀스**인데 본 SPEC의 산출물은 **프리셋**이고 `spec.md §D`는 시퀀스 생성을 범위 밖으로 뒀다 — 즉 16·17이 둘 다 GO여도 REQ-BUSKWIZ-016은 충족 불가였다. 본 문서 추가: **§4 위험 #13** · **AP-18**(레이아웃을 완성하려고 시퀀스를 만든다) · §2 항목 4 · §5.1 결정 A · §5.2 · §6.5 M0 행.
> **독립 재확인**: 룰북 `v2.4.2/` 전체의 `Assign` 용례는 세 곳이고 목적어가 전부 시퀀스다(`00_grammar.md:47`, `:70`, `31_choreography_patterns.md:99`, `:168`). 더 강한 근거가 하나 더 있다 — `00_grammar.md:72`는 프리셋의 사용법을 **"Apply an effect/preset to a selection: `Select Group 3` then `At Preset 4.1`"** 로 적는다. 룰북 자신의 모델에서 프리셋은 **선택에 리콜하는 것**이지 플레이백에 바인딩하는 것이 아니며, 익스큐터로 가는 경로는 `31_choreography_patterns.md:230`이 적듯 **큐·시퀀스를 경유**한다. 즉 ASSUMPTION-19의 부정은 개연성이 낮은 가정이 아니라 **현재 문서가 가리키는 기본값**이다.
>
> **v0.1.1 — 요구 수준 폐쇄 4건.** **§5 무변경.** v0.1.0이 "설계가 정해야 할 것"으로 적었던 네 항목이 spec.md에서 **요구로 확정**되었고, 본 문서는 그것을 **열린 결정 → 닫힌 요구 + 회귀 위험**으로 재프레이밍한다:
> (a) **캡처 형상 `shared_capture` 고정 · 모델 인자 미노출**(spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정) + REQ-BUSKWIZ-020) → §4 위험 #8 · AP-13. per-family 상한 **135행은 "도달 불가 · 참고"로 존치**한다 — 삭제하면 인자가 되살아났을 때 그 비용을 처음부터 다시 계산해야 한다.
> (b) **원장이 라벨도 누적**(spec.md REQ-BUSKWIZ-005 하위 절(원장은 슬롯과 함께 라벨도 누적한다)) → 위험 #9. (c) **미실행 커맨드 수 = 보고 요소 (e), (c)와 합산 금지**(REQ-BUSKWIZ-013 (e) + 하위 절((c)와 (e)를 합산하지 않는다)) → 위험 #7. (d) **미매핑 집계 단위 = `(룩, 역할)` 쌍**(REQ-BUSKWIZ-013 하위 절((b)의 집계 단위)) → 위험 #11. 네 건 모두 v0.1.0에서 본 문서가 **먼저 표면화한 뒤 spec.md가 받아 닫은** 것이므로, 위험 행은 지우지 않고 성격만 바꾼다 — 요구가 닫은 사항의 위험 행은 **회귀 감시 지점**이다.
> 함께 갱신: 번들 규모 밴드 **51~87행**(spec.md §A "번들 규모의 실측", ASSUMPTION-18; per-family는 도달 불가) · 미매핑 사유는 **3종이 아니라 2부류 최대 5종**(REQ-BUSKWIZ-013 하위 절((b)의 사유)) · 인용 정정 2건(`server/safety/blacklist.yaml:18` — LOOKLIB의 `:19`는 현재 트리에서 `Shutdown`; `server/orchestrator/tools.py:77-79` — LOOKLIB의 `:53-55`는 같은 블록 앞부분) · dotted form 금지의 성격(spec.md REQ-BUSKWIZ-018 하위 절(금지의 성격을 정확히 적는다) — 콘솔이 거부해서가 아니다).
>
> **v0.1.0 — 최초 작성.** 결정은 **§5.1의 7건(A~G)** 이며 `plan.md §A.4a`의 결정 문자와 **동일 집합**이다. 열린 슬롯은 양쪽 모두 **0건**이고 clarification 마커도 **0건**이다 — LOOKLIB v0.1.0이 슬롯 F를 대응 마커 없이 Kickoff 게이트로 흘려보낸 구조적 결함(`SPEC-COPILOT-LOOKLIB-001/design.md:106-108`)은 열린 항목을 하나도 만들지 않음으로써 착수 시점에 무해화된다. (마커 개수를 주장하는 문장은 마커 토큰 자체를 적지 않는다 — 적으면 그 문장이 스스로 스캔에 걸려 주장을 거짓으로 만든다. LOOKLIB AP-19의 "검증 수단이 주장을 검사하지 못할 때 낮출 것은 주장이 아니라 수단의 조악함이다"와 같은 자리에서 방향만 반대다.)
>
> **본 문서가 자산 실측으로 새로 확정한 수치 3건** (전부 재현 가능한 계수이며 SSOT를 개정하지 않는다):
> (i) **장르 번들의 실제 행 수는 51~87행**이다. `shared_capture` 기본형(`행수 = 1 + Σ(4 + 2·nᵢ)`) 4풀 전량 가용 시 ballad 67 / rock 77 / worship 77 / **edm 87**, Dimmer·Color만 가용 시 57 / 65 / 65 / 73. 룩 경계 `ClearAll`을 접는 병합형은 룩 수 −1행(61 / 70 / 70 / 79, 하한 51)이나 **병합은 M2의 형상 선택이지 요구가 아니다** — `ClearAll`은 dedupe 면제(`server/orchestrator/tools.py:229`)라 접지 않아도 손실이 0이다. **상한 87 · 하한 51**이 v1의 밴드이며 spec.md §C ASSUMPTION-18이 같은 수를 쓴다. 사용자에게 제시될 당시의 추정 "40여 줄"보다 크다 — **결정은 불변이고 갱신된 것은 그 결정이 안고 가는 비용의 크기**다(spec.md §A "수용된 잔여 위험"). M0는 **상한 87행**에서 측정한다(§4 위험 #5).
> (ii) **`run_commands`는 stop-on-first-failure**다(`server/orchestrator/tools.py:527-536`, `:562`) — 한 줄이 실패하면 뒤 전량이 `not_executed`가 되어 REQ-BUSKWIZ-010의 "일부만 저장 가능"과 다른 형상을 만든다(§4 위험 #7).
> (iii) **per-family 캡처 형상에는 값 라인 dedupe 탈락 경로가 실재**한다 — edm의 Dimmer 페이로드 `Attribute 'Dimmer' At 100` 2건, rock의 Beam 페이로드 `Attribute 'Iris' At 100` 2건이 문자열 동일이다. **v0.1.1에서 이 경로는 요구로 닫혔다**(spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)) — 본 문서의 실측이 그 요구의 근거이며, 위험 #8·AP-13은 이제 **회귀 감시**로 남는다.

## §1. 설계 의도

LOOKLIB은 "룩 1개를 이 리그의 프리셋으로"를 완성했다. 본 SPEC은 그 위에 **N개 룩을 가로지르는 조율 계층**만 얹는다. 설계의 핵심 선택은 셋이다.

**첫째 — 조율 계층이지 실행 계층이 아니다.** 룩 스키마·로더·역할 어휘·역할 해석기·풀 해석기·단일 룩 번들 빌더는 전부 그대로 소비하고 한 줄도 고치지 않는다(spec.md §A PRESERVE, REQ-BUSKWIZ-003). 콘솔로 나가는 모든 문자열은 기존 `run_commands` → `gate.screen()` 단일 경로를 탄다(`server/safety/gate.py:260-265` `@MX:ANCHOR`; 소비 선례 `server/orchestrator/tools.py:686-696`). 본 SPEC이 게이트에 하는 일은 **소비자 목록에 하나를 더하는 것**뿐이며, 이는 LOOKLIB이 EXECBODY로부터 계승한 "새 방어를 만드는 게 아니라 기존 방어 안으로 밀어 넣는다"(`SPEC-COPILOT-LOOKLIB-001/design.md:22`)의 재적용이다.

**둘째 — 상태를 갖는 것은 슬롯 원장 하나다.** LOOKLIB의 인스턴스화 계층은 전부 frozen이다(`server/looks/instantiate.py:78-79`, `:96-97`, `:105-106`) — 이것은 미덕이지만, 슬롯 배정만은 **N개 룩에 걸쳐 전진하는 상태**를 요구한다. `_first_free_slot`(`:307-312`)은 인자로 받은 점유 목록에서 1부터 첫 미점유를 고를 뿐 어디에도 쓰기가 없고, `_plan_stores`는 `binding.occupied`를 **읽기만** 한다(`:346`, `:358`). 하나의 `PoolIndex`로 N룩을 돌리면 N개 전부가 같은 슬롯을 겨냥하며, 라벨이 서로 달라 `CONFLICT`(`:359-361`)에도 걸리지 않는다. 따라서 본 SPEC의 설계는 **frozen 지형 위에 딱 하나의 얇은 가변 원장을 얹고, 그 원장 외에는 아무것도 상태를 갖지 않는 것**이다(REQ-BUSKWIZ-005, §5.1 결정 E). 원장의 시작값이 항상 콘솔 관측 점유라는 제약이 이 가변성을 안전하게 묶는다 — 원장은 **관측에 더하는 장치이지 관측을 대신하는 장치가 아니다**.

**셋째 — 코드를 고치는 대신 번들 형상을 고른다.** `ChangeDestination Root`는 dedupe 면제 3종(`server/orchestrator/tools.py:227-231`)에 들어 있지 않고, dedupe는 번들 내부에서도 누적한다(`:526`, `:537`). LOOKLIB M7이 이 탈락을 **실물에서 1건 관측**했다(`progress.md:799-805`, `:1167-1170`). 해법은 두 가지였다 — 면제 집합을 넓히거나, 애초에 두 번 발화하지 않는 형상을 쓰거나. 본 SPEC은 후자를 택한다(§5.1 결정 F): 룰북 자신이 `ChangeDestination Root`를 "**issue exactly once at the start of the bundle**"이라고 적고 있으므로(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:11`), 선두 1회 형상은 우회가 아니라 **규범 준수**다. 면제 집합을 넓히는 쪽은 안전 코드를 건드려 편의를 사는 거래이고, 이 프로젝트에서 그 거래는 항상 나쁜 거래였다.

## §2. 변경 표면 (예상)

1. **`server/looks/busking.py` (신규)** — 장르 조회(결정 G: `LookLibrary` 직접 순회) + 슬롯 원장(결정 E) + 다중 룩 번들 결합(결정 F의 형상). 순수 함수 — 콘솔·OSC 무접촉, 주입된 리그 해석 결과에만 의존. `IN_SCOPE_POOL_FAMILIES`(`server/looks/schema.py:58`)와 `GENRE_ALIASES`(`server/looks/matching.py:73-90`)는 **재정의하지 않고 import**한다(결정 B, REQ-BUSKWIZ-002 · AC-BUSKWIZ-002 ③).
2. **`server/looks/report.py` (신규)** — 집계 + 룩별 2단 구조화 보고(REQ-BUSKWIZ-013)와 한국어 표현 매핑(REQ-BUSKWIZ-015). **별도 모듈인 이유**: 사유 코드→한국어 매핑이 표현 계층에 있어야 하고(자산·스키마 금지 — `server/looks/matching.py:17-19` 선례), 번들 빌더와 섞이면 AC-BUSKWIZ-014의 PRESERVE 교차 확인이 "자산에 한국어가 없다"만 보고 "코드 어디에 있는지"를 놓친다.
3. **`server/orchestrator/tools.py`** — **신규 툴 1종 등록으로 한정**(REQ-BUSKWIZ-019). `TOOL_NAMES`(`:40-47`) · `definitions` · `handlers` 3곳 병렬 갱신, 기존 관례 그대로(`:448-457`, `:1052-1060`; `server/llm/types.py:16-26`). **툴 인자는 장르 식별자 하나다** — 리그 데이터도, 캡처 형상도 인자가 아니다(REQ-BUSKWIZ-020). 즉 `instantiate_look`의 `capture_shape` 파라미터(`:1035-1046`)는 **복제하지 않는다**: 그 관례는 단일 룩 툴의 것이고, 다중 룩에서 같은 인자는 dedupe 탈락 경로와 번들 상한 급증을 동시에 연다(§4 위험 #8·#5, AP-13). `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 블록(`:526-550`)은 **무변경**(§5.1 결정 F, spec.md §D, AC-BUSKWIZ-014 추가 assert).
4. **익스큐터 축 — M0 3항 게이트 종속, 파일 수 미정이 아니라 분기 확정.** ASSUMPTION-16 ∧ ASSUMPTION-17 ∧ **ASSUMPTION-19**가 **셋 다** GO일 때만 `busking.py`에 익스큐터 발화 축이 추가되며, 발화 형식은 **M0가 실측한 것 하나뿐**이다(REQ-BUSKWIZ-016 + 그 하위 절(GO여도 발화 형식은 M0가 실측한 것 하나뿐)). 하나라도 부정이면 **파일 변경 0건**이고, 그 사실은 AC-BUSKWIZ-013이 **생성 커맨드 튜플 전수 + 비공허성 assert**로 기계 고정한다(v0.1.3에서 소스 grep에서 교체 — 공집합에 대한 전수 검사가 자동 통과하지 않도록 비공허성을 함께 본다). 이것은 "정해지지 않았다"가 아니라 **입력에 따라 정해지는 두 결과가 모두 정의되어 있다**는 뜻이다(LOOKLIB의 빔 축 처리 `LOOKLIB spec.md:45`와 동형). **DESCOPE를 피하려고 시퀀스를 만드는 우회는 금지된다**(spec.md §D, AP-18).
5. **테스트 5종 (신규)** — `server/tests/test_busking_genre.py` · `test_busking_bundle.py` · `test_busking_report.py` · `test_busking_tool.py` · `test_busking_executor.py`. 경로는 acceptance.md §C.1이 인용한 것 그대로다.

**무변경(PRESERVE)**: `server/looks/{schema,loader,roles,resolver}.py` · **`server/looks/instantiate.py`**(v0.1.3 추가) · `server/looks/library/*.yaml` · `server/safety/**` · `server/web/preview.py` · `console/lua/copilot_responder.lua` · `server/rulebook/assets/v2.4.2/**`. 신규 YAML·JSON 자산 **0개**(AC-BUSKWIZ-015 추가 assert) — 본 SPEC은 출하된 32룩의 소비자이지 증보자가 아니다. **`instantiate.py`가 목록에 들어온 이유**: 결정 E는 "frozen 자료구조를 **바깥에서** 감싼다"는 형상이므로, `PoolIndex`/`PoolBinding`/`_plan_stores`를 고치게 되는 것이 곧 **결정 E의 반증**이다. PRESERVE에 넣으면 그 반증이 diff로 즉시 드러나고, 넣지 않으면 조용히 개정하고 지나갈 수 있다 — 그 개정은 단일 룩 경로와 P1-1을 함께 흔든다.

## §3. 데이터 흐름 (설계 목표)

```
[채팅] "이 리그로 워십 버스킹 준비해줘"
   → [툴 디스패치 — registry.dispatch  ← 모델이 들어오는 문, REQ-BUSKWIZ-019]
   → [장르 해석: GENRE_ALIASES (matching.py:73-90, resolve_genre :197-207)]
        · 해석 실패 → 후보 4종과 함께 정직한 실패, 승격 없음 (REQ-BUSKWIZ-002)
   → [룩 집합 조회: LookLibrary 직접 순회  ← 결정 G (match_looks 경로 우회)]
        · 정렬 = dynamics ASC → look_id ASC (결정론적 전순서, REQ-BUSKWIZ-001)
        · 절단 0 — MAX_TOOL_MATCHES=8 (matching.py:71) 을 타지 않는다
        · 자산 실측: worship 8 / rock 8 / ballad 7 / edm 9
   → [리그 1회 읽기: collect_rig_sections  ← 모델 인자 아님 (REQ-BUSKWIZ-020, tools.py:735-744)]
        ├── resolve_roles(sections["groups"])         × 1  ┐  이후 룩 수와 무관하게
        └── resolve_pools(sections["preset_pools"])   × 1  ┘  재해석 0 (REQ-BUSKWIZ-004)
   → [슬롯 원장 초기화 — 풀 패밀리별 1개, 본 설계의 유일한 가변 상태]
        ledger[f] = set(bindings[f].occupied)   if occupied is not None   ← 관측된 점유가 시작값
        ledger[f] = MISSING                     if occupied is None       ← 미관측 ≠ 빈 풀
                                                   (instantiate.py:80-85)
   ┌── 룩 루프 (정렬된 N개; 원장은 루프를 가로질러 살아 있다) ─────────────────┐
   │ for look in looks:                                                       │
   │   for family in IN_SCOPE_POOL_FAMILIES:            (schema.py:58 상속)   │
   │     payload = payload_for_family(look, family) ; 비었으면 continue        │
   │     ledger[f] is MISSING       → SkippedStore(no_free_slot)              │
   │                                              ← REQ-BUSKWIZ-009           │
   │     bindings[f].reason 있음     → SkippedStore(그 사유)                    │
   │     label ∈ (콘솔 기존 라벨 ∪ 이번 번들이 이미 청구한 라벨)                  │
   │                                 → SkippedStore(conflict)                 │
   │                                              ← REQ-BUSKWIZ-007           │
   │     slot = min{ s ≥ 1 : s ∉ ledger[f] }            ← 원장 조회             │
   │     ledger[f].add(slot)                            ← 원장 갱신 (전진!)     │
   │     planned += (family, pool, slot, label, payload)                      │
   │   look_body = [ ClearAll, Group <sel>, values,                           │
   │                 (Store,Label) × n, ClearAll ]                            │
   │                 ↑ ChangeDestination Root 는 룩 본문에 넣지 않는다          │
   └──────────────────────────────────────────────────────────────────────────┘
   → [단일 번들 조립 — 결정 F / REQ-BUSKWIZ-006]
        commands = [ "ChangeDestination Root" ]            ← 선두 정확히 1회
                 + look_body(1) + look_body(2) + … + look_body(N)
        · look_body = [ ClearAll, Group <sel>, values, (Store,Label)×n, ClearAll ]
        · 룩 경계의 ClearAll 2줄을 1줄로 접는 것은 M2의 선택이지 요구가 아니다 —
          ClearAll 은 dedupe 면제(tools.py:229)라 접지 않아도 손실 0이고, 룰북 규율
          (:40-41 "before every fresh look AND after every Store")은 접지 않은
          기본형에서 문자 그대로 성립한다. 접으면 룩 수 −1행이 줄 뿐이다.
        · 실측 규모: 기본형 57~87행 / 병합형 51~79행 → 밴드 51~87 (§4 위험 #5)
          — ASSUMPTION-18 의 측정 대상은 상한 87행(edm · 4풀 전량)이다
          — capture_shape 는 툴 인자가 아니다 (REQ-BUSKWIZ-020)
   → [run_commands (tools.py:484~) → _ObservingBundleGate.screen (session.py:162-166)]
        ├─(1) _on_preview(commands)      ← 스크리닝 **이전**  (preview.py:99-170)
        ├─(2) gate.screen(commands)      ← 기존 3-스테이지 · 승인 카드 1장
        │        · LiveLock 이면 여기서 제안 강등, 콘솔 송신 0 (REQ-BUSKWIZ-014)
        └─(3) _on_decision(decision)     ← 스크리닝 **이후**
   → [콘솔 송신 — per-command status: executed_ok / failed / not_executed /
        skipped_already_executed  (tools.py:527-562)]
        ※ stop-on-first-failure: 한 줄 실패 시 뒤 전량 not_executed (§4 위험 #7)
   → [집계 + 룩별 2단 보고 — REQ-BUSKWIZ-013 / report.py]
        (a) 생성 프리셋 전량 (풀·슬롯·이름)   (b) 미매핑 역할 — 사유 2부류(최대 5종)
        (c) 건너뜀 — 단위는 프리셋 저장 1회   (d) 룩별 complete/partial/none
        (e) 미실행 커맨드 수 — (c)와 **합산 금지** (REQ-BUSKWIZ-013 (e) + 하위 절)
```

**핵심 설계 목표 — 원장이 루프의 유일한 기억이다.** 위 흐름에서 룩 i가 룩 i+1에 남기는 것은 오직 `ledger[f]`에 추가된 슬롯 번호와 청구된 라벨뿐이다. 리그 해석 결과(`RoleResolution` / `PoolIndex`)는 frozen인 채 읽히기만 하고, 룩 본문은 서로를 보지 않는다. 이 형상이 AC-BUSKWIZ-004 구간 4("Dimmer 원장과 Color 원장은 서로 영향을 주지 않는다")를 **구조적으로** 성립시킨다 — 패밀리별로 분리된 집합이므로 교차 오염이 일어날 자리가 없다.

**흐름이 LOOKLIB과 다른 지점은 정확히 두 곳이다.** (i) 리그 읽기가 룩 루프 **밖**으로 나왔다 — LOOKLIB의 `instantiate_look`은 호출마다 `collect_rig_sections`를 다시 돈다(`tools.py:739-744`). (ii) `ChangeDestination Root`가 룩 본문에서 번들 선두로 올라갔다. 나머지 단계는 손으로 쓴 지시와 **완전히 동일한 경로**를 지난다.

## §4. 위험 검토 (False-Negative / 오작동 노출면)

| # | 위험 | 방어 | 신규/기존 |
|---|---|---|---|
| **1** | **(a) 51~87행 단일 프리뷰를 사람이 실질 검토할 수 없다** — 승인 카드 1장에 80여 줄이 올라오면 운영자는 읽지 않고 승인한다(경보 피로의 규모 버전) | **방어 아님 — 수용된 잔여 위험.** 대안 2건(룩 단위 분할 승인 / dry-run 선보고)이 제시된 뒤 사용자가 단일 승인을 택했다(사용자 확정 ③ — spec.md §A "실행 단위"). **결정은 불변이고 갱신된 것은 비용의 크기다**(spec.md §A "수용된 잔여 위험" — 제시 당시 추정 "40여 줄", 실측 51~87). 완화는 사후 쪽이다 — REQ-BUSKWIZ-013의 집계+룩별 2단 보고가 "무엇이 실제로 생겼는가"를 실행 **후에** 읽을 수 있게 만든다. **위험 #8의 형상 고정이 이 위험의 크기도 함께 줄인다** — 프리뷰 행 수의 상한을 87로 묶는 유일한 장치다. 아래 상세 | **신규 위험, 표면화 후 수용** |
| **2** | **(b) 슬롯 원장이 관측을 대체하는 오용** — "원장이 있으니 미관측 풀도 슬롯 1부터 쓰면 된다" | **원장의 시작값은 항상 `binding.occupied`이고, `None`이면 원장을 만들지 않는다**(§3 `MISSING`). REQ-BUSKWIZ-005 하위 절 + REQ-BUSKWIZ-009. `instantiate.py:80-85` 독스트링이 그 오용의 결과를 명시한다 — "treating it as one is how a store lands on top of somebody's work". AC-BUSKWIZ-007이 `occupied=()`와 `occupied=None`의 **서로 다른 결과**를 별도 테스트로 고정, AC-BUSKWIZ-004 구간 5가 한 쌍 | **신규 위험, 신규 방어** |
| **3** | **(c) 같은 장르 연속 2회 실행이 전량 건너뜀 — 멱등이 아니다** | **정직한 중복 거부로 정의**(acceptance.md §D). 1회차가 만든 라벨이 2회차의 `binding.labels`에 나타나 전부 `conflict`가 되고(`instantiate.py:359-361`), 보고가 "N개 건너뜀(이미 존재)"을 명시한다. 재슬롯도 `/Overwrite`도 하지 않는다(REQ-BUSKWIZ-007) — 조용히 다른 슬롯에 두 번째 사본을 만드는 쪽이 더 나쁘다 | **신규 위험, 정의된 동작으로 흡수** |
| **4** | **(d) 익스큐터 GO 시 오바인딩의 비가역성** — 잘못된 익스큐터에 `Assign`하면 운영자가 쓰던 플레이백을 덮는다. 프리셋 충돌과 달리 **라벨 검사로 걸러지지 않는다** | **부분 방어.** 번호는 이름 검증을 마친 것만 쓴다(`server/web/dash.py:129-143`, `:221-229`) — 확인 실패 후보는 발화하지 않는다(REQ-BUSKWIZ-017). 그러나 "**비어 있는** 익스큐터"의 판별은 ASSUMPTION-17이며 현재 드릴다운은 **존재하는 자식만** 열거한다(`dash.py:200-206`) — 즉 "이름이 확인된 익스큐터"는 곧 "이미 무언가 있는 익스큐터"다. **v0.1.3에서 이 모순이 AC 층에서도 해소되었다**: AC-BUSKWIZ-012 ①의 번호 출처가 `resolved_executor_nos`(=점유된 익스큐터)에서 **"M0가 GO로 판정한 빈-익스큐터 식별 경로가 반환한 번호"** 로 교체되었다 — 본 문서가 서술만 하고 AC는 반대를 적고 있던 상태가 닫혔다. 위험 #13이 그 앞단을 막는다. 아래 상세 | **신규 위험, M0 게이트에 종속 (v0.1.3에서 AC 정합 확보)** |
| **5** | **(e) 번들 규모가 왕복 상한을 넘는다 (ASSUMPTION-18)** — 절단·타임아웃 시 콘솔이 받은 것과 계획이 어긋나고, 부분 실행이 성공으로 보고될 수 있다 | **M0 프로브 선행**(AC-BUSKWIZ-016). 부정이면 **번들 분할 정책은 SPEC이 임의로 만들지 않고 사용자 결정 항목으로 M0 게이트에 기록**한다(spec.md §C ASSUMPTION-18, AP-15) — 사용자 확정 ③과 충돌하는 변경이기 때문. **측정 기준은 실제 상한 87행**(edm · 4풀)이며, 그보다 작은 합성 번들에서의 통과는 GO 근거가 되지 못한다(spec.md §A "번들 규모의 실측"). 아래 상세 | **신규 위험, 측정 기준 확정** |
| **6** | **(f) `Group N + M` 가산 선택의 상속된 잔여 위험** — `_selection_line`(`instantiate.py:300-304`)의 주석이 스스로 "additive form is grammar-derived and awaits the M7 live session"이라 자인한다 | **부분 폐쇄 — 항 수 축은 여전히 열려 있다.** LOOKLIB M7이 **2항** `Group 11 + 12`를 실물에서 OK ×2회 관측했고(`progress.md:835`, `:1175-1176`), 소스 주석은 그 뒤 갱신되지 않아 실제보다 비관적으로 남아 있다. 그러나 **3항 이상은 미실측**이며, 자산 실측상 **32룩 중 16룩이 3개 이상의 역할을 선언**한다(역할 수 분포 1:3 / 2:13 / 3:7 / 4:3 / 5:1 / 6:5) — 장르 번들은 정확히 그 구간을 밟는다. LOOKLIB 잔여 기록도 "6역할 중 2만 실물을 통과"라 적는다(`progress.md:1210-1211`). AC-BUSKWIZ-017이 종단에서 관측한다. 아래 상세 | **기존 위험 상속, 부분 폐쇄** |
| **7** | **stop-on-first-failure가 "부분 성공"의 형상을 바꾼다** — `run_commands`는 첫 실패 이후 남은 커맨드를 전부 `not_executed`로 만든다(`tools.py:527-536`, `:562`). 87행 번들의 3번째 줄이 실패하면 84행이 미실행이며, 이는 REQ-BUSKWIZ-010이 말하는 "**일부만 저장 가능**"과 **다른 사건**이다 | **v0.1.1에서 요구로 닫혔다** — 보고 요소 **(e) 미실행 커맨드 수**가 신설되고 **(c)와 합산 금지**·**자동 재시도 금지**가 명문화됐다(REQ-BUSKWIZ-013 (e) + 하위 절((c)와 (e)를 합산하지 않는다)). 건너뜀은 **빌드 시점** 판정이고 미실행은 **실행 시점** 귀결이다. **v0.1.4 최종 열거**: REQ-BUSKWIZ-010의 트리거는 "슬롯 부족"이 아니라 **풀 미해석 · 라벨 충돌 둘**이다(점유 미관측은 REQ-BUSKWIZ-009 소관). 남는 것은 회귀 감시 — 두 수를 한 칸에 합치는 구현을 §6.2가 개별 테스트로 떨어뜨린다 | **v0.1.0 표면화 → v0.1.1 요구로 폐쇄, v0.1.3·v0.1.4 트리거 정정** |
| **8** | **per-family 캡처 형상에서 값 라인이 dedupe로 탈락** — 동일 문자열의 값 라인은 면제 집합에 없어(`tools.py:227-231`) 두 번째가 `skipped_already_executed`가 되고, 직전 `ClearAll`은 면제라 살아남으므로 **빈 프로그래머로 `Store`** 가 실행된다. 콘솔은 성공으로 답한다 | **v0.1.1에서 요구로 닫혔다** — 캡처 형상은 `shared_capture` **고정**이고 모델 인자로 노출하지 않는다(spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정) + REQ-BUSKWIZ-020). 실측 근거: `shared_capture`의 값 라인은 룩의 전체 속성 집합이라 4장르 32룩 전수에서 중복 **0건**이고, `per_family_capture`는 패밀리 페이로드로 쪼개져 edm 두 룩의 `Attribute 'Dimmer' At 100`·rock 두 룩의 `Attribute 'Iris' At 100`이 충돌한다. 아래 상세 | **v0.1.0 표면화 → v0.1.1 요구로 폐쇄(회귀 감시로 존치)** |
| **9** | **번들 내부 라벨 중복이 검사되지 않는다** — `_plan_stores`의 충돌 검사는 `binding.labels`, 즉 **콘솔이 이미 갖고 있는 라벨**만 본다(`instantiate.py:359-361`). 같은 번들이 만들 라벨끼리는 비교 대상이 아니다 | **v0.1.1에서 요구로 닫혔다** — 원장이 슬롯과 함께 **이번 번들이 청구한 라벨도 누적**해 동일 판정(대소문자·공백 무시 일치 = 건너뛰기)을 적용한다(spec.md REQ-BUSKWIZ-005 하위 절(원장은 슬롯과 함께 라벨도 누적한다)). **현행 자산 발현 0건** — 32룩 `display_name`은 장르 내·간 모두 중복 0(실측). 즉 지금 깨진 것이 아니라 **막는 기제가 없던 것**이고, 0건 실측을 방어로 계산하지 않는다. **v0.1.4 기준으로 이 경로는 REQ-BUSKWIZ-010의 도달 가능 트리거 둘 중 하나(라벨 충돌)이기도 하다** | **v0.1.0 표면화 → v0.1.1 요구로 폐쇄** |
| **10** | **점유 목록의 truncation이 원장 시작값을 오염** — `drill_into`가 자식 목록의 `truncated`를 보존하지 않아 잘린 점유 목록을 완전한 것으로 읽을 수 있다(LOOKLIB M4가 "제거하지 못했고 가정하지도 않았다"로 남긴 관측 `progress.md:606`) | **부분 방어, 상속.** `drilldown_capped` 신호는 보고에 그대로 전달된다(acceptance.md §D). 그러나 원장은 이 신호를 **소비하지 않는다** — 잘린 점유 위에 세운 원장은 잘린 만큼 낙관적이다. 단일 룩에서 1슬롯이던 노출이 N룩에서 N슬롯으로 **선형 확대**된다는 점만 본 SPEC이 새로 지는 몫이다. 폐쇄에는 `drill_into`의 개정이 필요하고 그것은 PRESERVE 밖이 아니라 **범위 밖**이다 | **기존 위험 상속, 노출 확대** |
| **11** | **보고 집계의 단위 불일치** — 미매핑 역할을 distinct 역할 수로 세면 룩별 합계와 어긋나 AC-BUSKWIZ-008 구간 1(산술 일치)이 깨진다. 리그를 1회만 해석하므로(REQ-BUSKWIZ-004) 같은 역할이 그것을 선언한 모든 룩에서 반복 미매핑된다 | **v0.1.1에서 요구로 닫혔다** — 집계 단위는 **`(룩, 역할)` 쌍**이고 사람이 읽을 **distinct 역할 목록은 별도 필드로 병기**한다(spec.md REQ-BUSKWIZ-013 하위 절((b)의 집계 단위)). 건너뜀 단위가 **프리셋 저장 1회**인 것과 같은 규율이다(LOOKLIB AP-15 계승) — 세는 단위를 흐리면 부분 성공이 표현 불가능해진다 | **v0.1.0 표면화 → v0.1.1 요구로 폐쇄** |
| **12** | **`run_look_bundle` 재사용 유혹이 배선 결함을 재발시킨다** — `server/web/session.py:289`에 세션 레벨 번들 실행기가 이미 있으나 **프로덕션 호출자 0**이다(`progress.md:1213`, `:889`) | **신규 툴은 `registry.dispatch`로 들어가는 경로여야 하고, 테스트도 거기로 들어간다.** LOOKLIB이 라이브 3회차를 쓴 원인이 정확히 이 미배선이며(`progress.md:1224-1229`), M4 테스트가 그것을 못 본 이유는 **테스트가 `run_look_bundle`을 직접 호출했기 때문**이다(`server/tests/test_looks_tool.py:10-12`). AC-BUSKWIZ-011 구간 1(3곳 등재 정합)이 기계 고정 | **기존 사고 상속, 테스트 진입점으로 방어** |
| **13** | **얹을 대상이 없다 — 게이트가 열려도 REQ-BUSKWIZ-016이 충족 불가** (ASSUMPTION-19) | 라이브 검증된 유일한 바인딩 커맨드의 목적어는 **시퀀스**이고(`31_choreography_patterns.md:99`, `:168`) 본 SPEC의 산출물은 **프리셋**인데 spec.md §D가 시퀀스 생성을 범위 밖으로 뒀다 | **v0.1.2에서 게이트 항으로 승격**(REQ-BUSKWIZ-016의 3항 논리곱 + 그 하위 절(ASSUMPTION-19가 게이트에 추가된 이유), 전제 정의는 spec.md §C ASSUMPTION-19). **실측**: `Assign Preset` · `Preset <p>.<s> At (Executor\|Page) <n>` · `Store Executor` 계열 리포지토리 전체 **0건**이며, 룰북의 `Assign` 용례 3곳은 목적어가 전부 시퀀스다(`00_grammar.md:47`, `:70`). 더욱이 `00_grammar.md:72`가 프리셋을 **"선택에 리콜"**(`Select Group 3` → `At Preset 4.1`)로 정의하고 익스큐터 경로는 큐·시퀀스를 경유한다(`31_choreography_patterns.md:230`) — 부정이 **기본값**이다. M0가 직접 얹는 문법을 못 찾으면 답은 **DESCOPE**이고, 우회 생성은 AP-18이 막는다 | **v0.1.1 요구 정합 결함 → v0.1.2 게이트로 폐쇄** |

**위험 #1 상세 — 수용된 위험이지 기각된 반론이 아니다.** 이 구분은 형식이 아니다. 기각된 반론은 문서에서 사라지고 다시 논의되지 않지만, **수용된 위험은 존치되어 후속 SPEC이 재평가할 수 있는 상태로 남는다**. spec.md §A의 "실행 단위" 항과 "수용된 잔여 위험" 항이 그 거래를 정확히 기록한다 — 마법사의 가치는 "한 마디에 일괄"이고, 룩 단위 분할 승인은 6~10회 왕복을 만들어 기능 자체를 무력화한다. dry-run 선보고는 왕복을 1회 늘리는 대신 승인 시점의 정보량을 그대로 두므로, 검토 불가능성 자체를 풀지 못한다. 사용자는 두 대안을 보고 단일 승인을 택했다. **다만 제시 당시의 추정치는 "40여 줄"이었고 실측은 51~87행이다** — 결정은 불변이고 갱신된 것은 그 결정이 안고 가는 비용의 크기다. 남는 완화는 두 방향뿐이며 둘 다 왕복을 늘리지 않는다: (i) 프리뷰 자체는 기존 계층이 그대로 감당한다 — 커맨드별 severity 분류(`server/web/preview.py:99-170`)와 번들 등급 승격(`:198-203`)은 87행에서도 동일하게 동작하고, 자산에 스트로브·셔터가 0건이므로 `danger` 승격 경로는 v1에 없다(acceptance.md §D). (ii) 사후 가독성은 REQ-BUSKWIZ-013이 진다 — **집계만 보고하고 룩별을 생략하는 것이 금지된 진짜 이유가 이 위험**이다. 87행을 읽지 못한 운영자가 실행 후에 "8룩 중 6룩 완전 · 1룩 부분 · 1룩 0건"을 읽을 수 있어야 한다. AP-10이 그 생략을 막는다.

**위험 #4·#13 상세 — GO 분기가 성립하려면 모순 둘이 먼저 풀려야 한다.** 첫째는 **얹을 대상**(위험 #13, ASSUMPTION-19)이다. 이 문제는 v0.1.1까지 보이지 않았다 — REQ-BUSKWIZ-016이 "팔레트에 대응하는 익스큐터 레이아웃"을 말하면서 정작 팔레트를 익스큐터에 얹는 문법의 존부를 묻지 않았기 때문이다. 리포지토리가 아는 바인딩은 `Assign Sequence <n> At Executor <m>` 하나이고 목적어가 시퀀스이므로, 프리셋만 만드는 v1에는 **바인딩할 것이 없다.** 이것은 "아마 문법이 있을 것"의 문제가 아니라 **현재 문서가 반대 방향을 가리키는** 문제다 — `00_grammar.md:72`는 프리셋을 선택에 리콜하는 것으로 정의하고, `31_choreography_patterns.md:230`은 익스큐터로 가는 길을 "값 설정 → `Store` 큐 → `Assign … At Executor`"로 적는다. 둘째는 **빈 자리 판별**(위험 #4, ASSUMPTION-17)이다. 프리셋 충돌은 라벨 비교로 걸러지지만(`instantiate.py:359-361`) 익스큐터에는 그런 장치가 없다 — `Assign`은 대상이 비었는지 묻지 않고 실행되며 성공으로 답한다. 그런데 현재 리포지토리의 익스큐터 열거는 **페이지 드릴다운이 반환한 자식**에서 출발하고(`dash.py:200-206`), 그 번호를 `_confirm_executor_no`가 **이름으로** 검증한다(`:129-143`, `:221-229`). 이름이 확인된다는 것은 그 자리에 오브젝트가 있다는 뜻이다 — 즉 현재 도구로 "확인된 번호"를 모으면 그것은 **점유된 익스큐터 목록**이고, 비어 있는 자리는 "확인 실패"와 구별되지 않는다(`:210-231`). **두 모순 중 하나라도 M0에서 풀리지 않으면 REQ-BUSKWIZ-016은 발동하지 않는다 — 그것은 실패가 아니라 정의된 결과다**(AC-BUSKWIZ-012 ②).

**위험 #5 상세 — 측정은 실제 상한에서 해야 한다.** 계수는 재현 가능하다. `_bundle`의 `CAPTURE_SHARED` 형상(`instantiate.py:395-404`)은 룩당 `ClearAll` · 선택 · 값 1줄 · `(Store, Label)` × n · `ClearAll`을 쌓고, `CAPTURE_PER_FAMILY` 형상(`:406-413`)은 **패밀리마다** `ClearAll` · 선택 · 값 · `Store` · `Label` 5줄을 격리해 쌓는다. 장르 번들은 어느 쪽이든 선두 `ChangeDestination Root` 1행을 더한다. 따라서 **`shared_capture` 기본형 `1 + Σ(4 + 2·nᵢ)`** · **병합형 `1 + Σ(3 + 2·nᵢ) + 1`**(차이는 정확히 룩 수 −1) · **`per_family_capture` `1 + Σ(5·Pᵢ + 1)`**(v1에서는 도달 불가 — 아래) 이다. `nᵢ`(= `Pᵢ`)는 룩 i가 값을 가진 in-scope 풀 패밀리 수다. 라이브러리 자산(`server/looks/library/*.yaml`, 32룩)에 적용하면:

| 장르 | 룩 수 | Store+Label 쌍 | shared · 기본형 | shared · 병합형 | shared · D+C만 | per-family *(도달 불가 · 참고)* |
|---|---|---|---|---|---|---|
| ballad | 7 | 19 | 67행 | 61행 | 57행 | (103행) |
| rock | 8 | 22 | 77행 | 70행 | 65행 | (119행) |
| worship | 8 | 22 | 77행 | 70행 | 65행 | (119행) |
| edm | 9 | 25 | **87행** | 79행 | 73행 | (135행) |

**밴드는 51~87행이고 M0의 측정 대상은 상한 87행이다.** 하한 51은 ballad × Dimmer·Color만 × 병합형, 상한 87은 edm × 4풀 × 기본형이다 — **51~87은 단일 형상의 밴드가 아니라 서로 다른 형상을 덮는 포괄 봉투**다. LOOKLIB M7의 실측 최대는 21행(`progress.md:1326`의 FALLBACK 프로브)이므로 미측정 구간은 **약 4.1배**다. 40행짜리 합성 번들로 GO를 판정하면 그 GO는 v1의 실제 최악 경로를 덮지 않는다(spec.md §A "번들 규모의 실측" — "그보다 작은 합성 번들에서의 통과는 GO 근거가 되지 못한다"). **병합형을 측정 기준으로 삼는 것도 안 된다** — 병합은 M2가 택할 수도 택하지 않을 수도 있는 형상이고(`ClearAll`이 dedupe 면제이므로 접지 않아도 손실이 없다), 측정은 구현이 실제로 낼 수 있는 최댓값을 덮어야 한다. **per-family 열(103~135행)은 v1에서 도달 불가다** — spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)이 형상을 `shared_capture`로 고정하고 REQ-BUSKWIZ-020이 툴 인자를 장르 식별자 하나로 한정했다. 그럼에도 **열과 산식을 지우지 않는 이유**는 회귀 때문이다: 누군가 `capture_shape`를 인자로 되살리면 그 순간 **135행이 미측정 경로가 되고 값 라인 dedupe 탈락도 함께 돌아온다**(위험 #8, AP-13). 비용을 지워 두면 그 시점에 처음부터 다시 계산해야 한다. **"40여 줄"의 출처**: 그것은 v0.1.0이 쌍(pair) 수 — 룩 수 × 룩당 최대 4쌍 — 로 낸 추정치였고 행 수가 아니었다. v0.1.1이 §A에 실측 계수를 직접 적어 그 표현을 대체했으므로, 현재 spec.md에는 그 추정치가 남아 있지 않다.

**위험 #6 상세 — 소스 주석이 실측보다 오래되었고, 그럼에도 열린 부분이 남는다.** 두 사실을 함께 적는다. (i) `instantiate.py:301-304`는 "awaits the M7 live session"이라 적혀 있으나 그 M7은 이미 끝났고 `Group 11 + 12`는 OK ×2회로 관측되었다(`progress.md:835`, `:1148`, `:1175-1176`). 주석만 뒤처졌다 — 이 주석을 근거로 "가산 선택은 전혀 미실측"이라 쓰는 것은 리포지토리가 가진 관측을 버리는 것이다. (ii) 그러나 관측된 것은 **2항 1쌍, 단일 쇼파일, 6역할 중 2**다(`progress.md:1210-1211`). 본 SPEC의 장르 번들은 6역할 룩 5개를 포함하는 집합을 한 번에 돌리므로 3~6항 체인을 발화한다. 열린 잔여는 "가산 선택 자체"가 아니라 **항 수 축**이며, 이것이 정확한 상속 상태다. `_selection_line`은 PRESERVE 대상이므로 본 SPEC은 이 형태를 바꾸지 않고, AC-BUSKWIZ-017의 종단 관측이 실물 항 수를 기록한다.

**위험 #7 상세 — "부분 성공"이라는 낱말이 두 사건을 가린다 (v0.1.3에서 트리거 정정, v0.1.4에서 열거 1건 삭제).** REQ-BUSKWIZ-010은 장르의 룩 중 **일부만 저장 가능한 경우**를 말한다. v0.1.2까지 본 문서는 그 대표 사례를 "슬롯 소진"으로 적었으나 **그 상태는 발생할 수 없다** — `_first_free_slot`(`server/looks/instantiate.py:307-312`)은 `slot = 1`에서 시작해 점유 집합에 없을 때까지 증가할 뿐 **상한이 없고**, 리포지토리에 풀 용량 상수가 0건이며(`max_slot`/`pool_size`/`POOL_CAPACITY` 계열), `_observed_contents`(`:195-215`)는 점유된 자식만 반환해 **풀 크기를 아예 보고하지 않는다**. 도달 가능한 경로는 **둘**이다: **(i) 풀 미해석** — `pool_unresolved`/`pool_unaddressable`/`no_free_slot`(미관측)로 그 패밀리 전체가 서지 않는다, **(ii) 라벨 충돌** — 콘솔 기존 라벨 또는 이번 번들이 이미 청구한 라벨과 겹쳐 그 저장 하나가 빠진다. **v0.1.3이 셋으로 적었던 "(i) 룩별 패밀리 수 차이"는 v0.1.4에서 삭제되었다 — 그것은 부분 성공이 아니다**: 룩이 어떤 패밀리에 값을 갖지 않으면 `_plan_stores`가 `if not values: continue`로 넘어가 **`SkippedStore`를 만들지 않으므로**(`:332-334`) 결과는 `planned=P, skipped=0, complete=True`, 즉 **완전 성공**이다(실행 확인: `ballad-single-key` P=4 / `ballad-moonlight` P=2 둘 다). 패밀리 수의 차이는 그 룩이 원래 갖는 속성이지 실패가 아니며, 이 경로로 "건너뜀이 있다"를 assert하면 거짓이 된다. 남은 둘은 **번들을 만들기 전에** 원장·바인딩이 판정하는 사건이고, 결과는 번들에서 그 `Store`가 아예 빠지는 것이다. `not_executed`는 다르다 — 번들에 들어 있었고, 게이트를 통과했고, 앞선 줄이 실패해서 발화되지 않았다(`tools.py:527-536`, `:562`). 87행 번들에서 이 차이는 크다: 전자는 "이 리그·이 라이브러리에서는 그 저장이 애초에 서지 않는다", 후자는 "3번째 줄이 왜 실패했는지 보라"다. **v0.1.1이 이를 보고 요소 (e)로 분리하고 (c)와의 합산을 금지했다**(REQ-BUSKWIZ-013 (e) + 하위 절). **자동 재시도도 금지다** — 실패 지점 앞의 커맨드는 이미 실행됐으므로 번들 전체를 다시 보내면 중복 부작용이 되고, `Store Preset`은 dedupe 면제가 아니라 두 번째 왕복에서 조용히 탈락한다(`tools.py:537`). M0가 **중도 실패의 사후 상태**를 함께 기록하는 이유도 여기에 있다(spec.md §C ASSUMPTION-18).

**위험 #8 상세 — 결정 F가 덮어야 하는 면적은 `ChangeDestination Root` 한 줄이 아니었다.** spec.md v0.1.0 §A 하드 결함 2는 dedupe 탈락을 `ChangeDestination Root`의 문제로 서술했다. 정확히는 **면제 집합에 없는 모든 반복 문자열**의 문제이며, 면제는 `Clear` · `ClearAll` · 맨 `Fixture|Group` 선택 3종뿐이다(`tools.py:227-231`). 선택 라인은 면제된다(정규식 실측: `Group 11 + 12 + 13`도 fullmatch). `Store Preset <pool>.<slot>` / `Label Preset …`은 슬롯이 달라 자연히 유일하다. 남는 것은 **값 라인**이다. `shared_capture`에서는 값 라인이 룩의 전체 속성 집합이라 중복이 없고(4장르 32룩 전수, 장르 내·간 모두 0건), `per_family_capture`에서는 패밀리 페이로드로 쪼개져 충돌한다 — edm의 두 룩이 Dimmer `At 100`으로, rock의 두 룩이 Iris `At 100`으로 동일하다. LOOKLIB은 이 형상의 거부를 해제했고(`progress.md:1326`) `capture_shape`에 기계적 제약을 두지 않았다(`:1212`) — 단일 룩에서는 한 번들에 같은 패밀리가 두 번 나오지 않으므로 무해했다. 다중 룩에서는 무해하지 않다. **v0.1.1은 이 실측을 근거로 형상을 요구 수준에서 고정했다**(spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)) — 따라서 장르 번들의 캡처 형상은 설계 선택이 아니라 **닫힌 요구**이고, 이 절은 그 요구가 왜 있는지의 기록이자 되열렸을 때 무엇이 함께 돌아오는지의 경고로 남는다.

## §5. 설계 슬롯

### §5.0 대응 관계 (plan.md §A.4와의 정직한 기술)

**대응은 1:1이다** — `plan.md §A.4a` 결정 **7건(A~G)** ↔ 본 문서 §5.1 항목 **7건(A~G)**, 문자와 순서가 같다. 열린 항목은 양쪽 모두 **0건**이며(`plan.md`의 clarification 마커 0건, 본 문서 §5.2 열린 슬롯 0건), 따라서 "마커 없이 게이트를 통과하는 결정"이 존재할 수 없다.

이 1:1은 자연히 성립한 것이 아니라 **선례의 실패를 피해 설계된 것**이다. LOOKLIB v0.1.0은 "슬롯 A~F ↔ 마커 6건이 1:1"이라 주장했으나 거짓이었고(`SPEC-COPILOT-LOOKLIB-001/design.md:97-108`), 특히 슬롯 F(역할 어휘 폐쇄 집합)는 **대응 마커가 없어** Kickoff 게이트를 통과하지 않고 구현 단계로 흘러갔다. 본 SPEC은 그 구조를 두 가지로 차단한다:

1. **착수 시점에 열린 결정을 만들지 않는다.** 사용자 확정 4건(A·B·C·D)과 엔지니어링 판단 3건(E·F·G)으로 7건 전부가 spec.md 작성 시점에 폐쇄되었다. "M1 설계 산출물로 확정"처럼 게이트 뒤로 미룬 항목이 **0건**이다.
2. **미확정으로 남는 것은 결정이 아니라 측정이다.** ASSUMPTION-16/17/18/19는 설계 슬롯이 아니라 **라이브 실측 대상**이며, 그 판정에 따른 두 결과(GO / DESCOPE)가 **양쪽 다 미리 정의되어** 있다(REQ-BUSKWIZ-016, AC-BUSKWIZ-012 ①②). 정의된 두 결과 사이의 분기는 열린 슬롯이 아니다 — 열린 슬롯은 "결과를 아직 모른다"가 아니라 "결과를 정하지 않았다"를 뜻하기 때문이다.

### §5.1 해소된 결정 (fold-in 완료 — 7건, 재질의 금지)

| 결정 | 확정 | 근거 요약 |
|---|---|---|
| **A. 익스큐터 페이지 레이아웃** | **M0 라이브 프로브 GO/DESCOPE 게이트** — v0.1.2에서 **3항 논리곱**(ASSUMPTION-16 ∧ 17 ∧ **19**). 하나라도 부정이면 v1은 익스큐터·페이지 대상 커맨드 **0건** | **사용자 확정 ①.** 페이지 생성·라벨·익스큐터 라벨링·빈 익스큐터 탐색은 리포지토리 근거 **0건**이며, 유일 등장처 `server/measurement/corpus.yaml`은 스스로 "the deterministic offline action for M6a mock runs ONLY"라 한정한다(`:7-10`). 더욱이 `Label Page 3 "Ballad"`(`:99`)는 큰따옴표를 쓰는데 `00_grammar.md:26-29`가 생성 커맨드에서 이를 금지한다 — **그대로 발화하면 깨진다**. **v0.1.2가 ASSUMPTION-19를 더한 이유는 "얹을 대상"이다** — 라이브 검증된 바인딩의 목적어는 시퀀스이고(`31_choreography_patterns.md:99`, `:168`) 본 SPEC의 산출물은 프리셋이라, 16·17이 GO여도 요구가 충족될 수 없었다(REQ-BUSKWIZ-016 하위 절(ASSUMPTION-19가 게이트에 추가된 이유); §4 위험 #13). 선례: `SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010, 계승 `LOOKLIB spec.md:45` |
| **B. 팔레트 축** | **LOOKLIB `IN_SCOPE_POOL_FAMILIES` 4종 그대로 상속** — Dimmer · Color · Beam · Focus. 재정의하지 않고 **import** | **사용자 확정 ②.** `server/looks/schema.py:58`이 정본이고 매핑은 `:62-69`. 신규 attribute 어휘를 만들지 않으므로 빔 문법 프로브가 불필요하다 — LOOKLIB M0가 `Zoom`/`Iris`를 GO 판정했고(`schema.py:49-50` `PROBE_GATED_ATTRIBUTES`) 라이브러리에 실값이 출하되어 있다(자산 실측: `Iris` 8룩 / `Zoom` 16룩). **포지션 축은 v1에 없다** — 선행 SPEC이 닫았고(`LOOKLIB spec.md:57`, `:192-194`) `Pan`/`Tilt`는 어떤 풀에도 귀속되지 않는다(`schema.py:47`, `:62-69` 매핑 부재). 제안서 :78의 3축 중 1축이 빠지는 정직한 축소이며 spec.md §D가 사유를 적는다 |
| **C. 실행 단위** | **단일 번들 · 승인 1회 · 부분 성공 구조화 보고.** 룩 단위 분할 승인과 dry-run 선보고는 **기각** | **사용자 확정 ③.** 마법사의 가치가 "한 마디에 일괄"이므로 6~10회 승인 왕복은 기능 자체를 무력화한다. 건너뜀의 단위는 **프리셋 저장 1회이지 룩이 아니다**(`LOOKLIB spec.md:65` 결정 I 계승 — 슬롯을 갖는 것은 룩이 아니라 프리셋이다). **반대 논거는 기각되지 않고 §4 위험 #1의 수용된 잔여 위험으로 존치**한다 — 51~87행 프리뷰는 사람이 실질 검토할 수 없고, 완화는 REQ-BUSKWIZ-013의 사후 2단 보고가 진다. v0.1.1이 그 보고에 요소 (e)를 더해 중도 중단까지 담게 했고, v0.1.3~v0.1.4가 "일부만 저장 가능"의 트리거를 **도달 가능한 둘**(풀 미해석 · 라벨 충돌)로 확정했다 |
| **D. 라이브 세션** | **2회** — M0 프로브(코드 변경 0) + M7 종단 | **사용자 확정 ④.** LOOKLIB의 계획 회계를 그대로 따른다(`LOOKLIB design.md:156-159`). M0는 정의상 M1보다 앞서야 하고(ASSUMPTION-18이 미확정이면 번들 규모 정책이 미정, 16/17이 미확정이면 REQ-BUSKWIZ-016의 발동 여부가 미정), M7은 정의상 M6보다 뒤여야 하므로 **합칠 수 없다**. **정직한 회계 주의**: LOOKLIB의 계획 2회는 실제 3회가 되었고 이탈 원인은 배선 결함이었다(`progress.md:1216-1230` — "계획의 2회는 성공 경로의 하한이었고 통합 결함 1회분을 예산에 넣지 않았다"). 본 SPEC의 2회도 같은 성격의 하한이며, §4 위험 #12와 AP-14가 그 재발 경로를 직접 겨냥한다 |
| **E. 슬롯 원장** | **풀 패밀리별 누적 슬롯 원장.** 시작값은 콘솔 관측 점유이며, **미관측 풀을 비었다고 가정하지 않는다** | **엔지니어링 판단.** spec.md §A 하드 결함 1의 유일한 해소 경로다 — `PoolBinding`/`PoolIndex`가 frozen이고(`instantiate.py:78-79`, `:96-97`), `_first_free_slot`(`:307-312`)에 전진이 없으며, `_plan_stores`는 `binding.occupied`를 읽기만 한다(`:346`, `:358`). 라벨이 다르면 `CONFLICT`(`:359-361`)에도 안 걸리므로 **같은 슬롯에 N번 `Store`** 가 조용히 성립한다. 원장은 이 결함을 **감싸는** 계층이지 `instantiate.py`를 고치는 것이 아니다(PRESERVE 유지). 원장이 라벨도 함께 누적해야 하는 이유는 §4 위험 #9. AC-BUSKWIZ-004 구간 2가 결함의 실재와 계층의 해소를 **함께** assert한다 |
| **F. dedupe 처리** | **`tools.py` dedupe 규칙 무개정.** 장르 번들이 `ChangeDestination Root`를 **선두 1회만** 발화하는 형상으로 회피 | **엔지니어링 판단.** LOOKLIB이 "dedupe 규칙 개정 여부는 M4가 단독으로 정하지 않는다"고 넘긴 판단(`progress.md:1330`)에 대한 답은 **"개정하지 않는다"** 다. 근거는 라이브 관측이다 — M7이 `skipped_already_executed` 정확히 1건(`ChangeDestination Root`)을 관측했고 **그 번들은 그럼에도 정상 왕복했다**(`progress.md:799-805`, `:1167-1170`; 목적지 상태가 세션에 남기 때문). 반면 `ClearAll`은 면제 덕에 4/4 전부 실행됐다(`:1171-1173`) — 면제 집합은 이미 제 일을 하고 있다. 그리고 룰북이 선두 1회를 **규범으로** 적는다(`31_choreography_patterns.md:11` "issue exactly once at the start of the bundle") — 즉 이 형상은 우회가 아니라 준수다. **면제 집합이 덮지 못하는 면적은 값 라인이며, 그것은 형상 고정으로 닫는다**(§4 위험 #8) |
| **G. 장르 룩 조회** | **`LookLibrary` 직접 순회.** `match_looks` / `find_looks` 툴 경로는 사용하지 않는다 | **엔지니어링 판단.** `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71`)이 결과를 자르고 `truncated` 신호를 붙이므로(`:68-71`), **EDM 9룩은 정확히 1건이 잘린다**(자산 실측: worship 8 / rock 8 / ballad 7 / edm 9). 상한은 "잘린 목록을 완전한 것으로 제시하지 않는다"는 올바른 규율의 산물이지 결함이 아니다 — 그러나 장르 **전량** 조회에는 맞지 않는 도구다. 별칭 표(`GENRE_ALIASES` `:73-90`)와 해석기(`resolve_genre` `:197-207`)는 **그대로 재사용**하고 중복 정의 0건을 AC-BUSKWIZ-002 ③이 확인한다 |

### §5.2 열린 슬롯 — **0건**

**이 문서에 열린 설계 슬롯은 0건이고, `plan.md`의 clarification 마커도 0건이며, 본 문서의 clarification 마커도 0건이다.** LOOKLIB은 v0.1.0에서 슬롯 6건 · v0.2.0에서 3건을 거쳐 v0.3.0에 이르러서야 0건에 도달했고(`LOOKLIB design.md:130-132`), 그 과정에서 두 번의 감사 FAIL(0.65 / 0.80)을 소비했다. 본 SPEC은 사용자 확정 4건과 엔지니어링 판단 3건으로 착수 시점에 같은 상태에서 출발한다.

**남아 있는 미확정은 결정이 아니라 측정 4건**(ASSUMPTION-16 / 17 / 18 / 19 — v0.1.2에서 19 추가)이며, 각각의 두 결과가 미리 정의되어 있다 — 16·17·19는 REQ-BUSKWIZ-016의 GO/DESCOPE(3항 논리곱, AC-BUSKWIZ-012 ①②), 18은 GO 또는 **사용자 결정 항목으로의 에스컬레이션**(spec.md §C ASSUMPTION-18)이다. 18만이 "SPEC이 스스로 답할 수 없는" 것이며, 그 이유는 부정 판정 시 필요한 번들 분할이 사용자 확정 ③과 정면 충돌하기 때문이다. 구현이 이를 단독 결정하는 것은 AP-15가 금지한다. **v0.1.1이 요구로 닫은 네 항목과 v0.1.2가 게이트로 닫은 한 항목은 이 목록에 들어오지 않는다** — 그것들은 미확정이었던 적이 없고, 설계 위험으로 표면화된 뒤 spec.md가 받아 닫은 것이다(§4 위험 #7·#8·#9·#11·#13).

## §6. 테스트 설계 방향

### §6.1 순수 함수 우선, 인메모리 리그

장르 조회 · 슬롯 원장 · 번들 결합 · 보고는 전부 순수다 — 주입된 `RoleResolution` / `PoolIndex`와 인메모리 `LookLibrary`만 있으면 결정론 테스트가 가능하고 OSC는 0이다(LOOKLIB `design.md:138`의 `DictBodyFetcher` 전통 계승). 원장은 특히 순수 테스트에 유리하다 — 입력은 `occupied` 튜플과 룩 목록, 출력은 슬롯 청구 집합이므로 라이브 없이 §4 위험 #2·#9·#11을 전부 고정할 수 있다.

**단, 툴 층은 순수 테스트로 검증하지 않는다.** AC-BUSKWIZ-009 · AC-BUSKWIZ-010 · AC-BUSKWIZ-011은 `registry.dispatch`로 진입해야 한다 — 빌더를 직접 호출하는 테스트는 배선 결함을 구조적으로 볼 수 없고(`server/tests/test_looks_tool.py:10-12`), LOOKLIB이 그 함정으로 라이브 세션 1회를 더 썼다(`progress.md:1224-1229`). 이것은 스타일 선호가 아니라 **이 저장소가 이미 값을 치르고 배운 것**이다(§4 위험 #12).

### §6.2 실패 모드는 개별 테스트 (병합 금지)

서로 다른 실패 모드를 한 테스트에 묶지 않는다(EXECREF/EXECBODY §6.2 원칙, LOOKLIB `design.md:142` 계승). 본 SPEC이 구분해야 하는 모드는 다음과 같다:

- **건너뜀 사유 4종** — `conflict` · `no_free_slot` · `pool_unresolved` · `pool_unaddressable`(`server/looks/instantiate.py:63-68`). 넷은 리그의 서로 다른 상태를 가리키고 조치가 다르다.
- **미매핑 사유는 3종이 아니라 2부류 · 최대 5종이다 — 그러나 v1의 테스트 대상은 3종이다** (spec.md REQ-BUSKWIZ-013 하위 절((b)의 사유)). **부류 1(매칭 판정, 3종)** `ambiguous` · `no_match`(`server/looks/roles.py:22-23`) · `unaddressable`(`server/looks/resolver.py:50`) — 리그의 문제이며 그룹을 만들거나 이름을 고치면 해소된다. **각각 개별 테스트**다. **부류 2(관측 실패)** 그룹 섹션 자체가 오지 않으면 **섹션의 사유 문자열이 모든 역할에 그대로 전파**된다(`server/looks/resolver.py:128-137` — 예: `path_not_resolved` / `console_unreachable`). 두 부류는 **다른 사실**이다 — 후자를 "이 리그에 백라이트가 없다"로 보고하면 보지 않은 리그에 대한 주장이 된다(리졸버 주석 `:130-132`가 같은 문장을 적는다). **부류 2는 v1 보고 계층에 도달하지 않으므로 테스트 대상이 아니다**: 툴 핸들러가 섹션 미도착을 **번들 구성 이전에** `is_error=True`로 조기 반환하는 것이 기존 관례이고(`server/orchestrator/tools.py:745-768`; `build_instantiation` 호출은 그 뒤 `:770`), 본 SPEC의 신규 툴도 같은 관례를 따른다(§2 항목 3). 5종을 전부 테스트하면 **도달 불가 경로를 검증하는 위양성 테스트**가 된다. 다만 **M4가 조기 반환을 쓰지 않기로 하면 그 순간 부류 2가 보고 계층에 도달하므로 이 항목을 다시 연다** — 어휘가 5종인 것은 `UnmappedRole.reason` 필드가 담을 수 있는 값의 사실이고, 도달 가능한 어휘는 핸들러 형상이 정한다.
- **집계 단위 `(룩, 역할)` 쌍 ≠ distinct 역할 수** (spec.md REQ-BUSKWIZ-013 하위 절((b)의 집계 단위), §4 위험 #11). 리그를 1회만 해석하므로 미매핑 역할은 그것을 선언한 **모든 룩에서 반복**된다 — 두 수는 배수만큼 벌어지고, distinct로 세면 AC-BUSKWIZ-008 구간 1의 산술 일치가 즉시 깨진다. **자산 실측(6역할 전량 미매핑 픽스처 기준)**: ballad 쌍 20 / worship 25 / rock 26 / edm 26, distinct는 네 장르 모두 **6** — 배수 3.3~4.3배다(역할 선언 총계 97건). 서술이 아니라 **기대값이 박힌 테스트**로 고정한다: worship에서 25 대신 6이 나오면 구현이 distinct로 센 것이다. **경계 케이스**: 역할 **하나만** 미매핑이어도 쌍 카운트는 그 역할의 선언 수만큼 오른다 — 최다는 rock `사이드` **7**(8룩 중), worship·edm `배경` **6**. 단일 역할 미매핑을 "1"로 세는 구현을 이 케이스가 떨어뜨린다.
- **점유의 3상태** — `occupied=(1,2)` (관측된 점유) · `occupied=()` (검증된 빈 풀) · `occupied=None` (미관측). 뒤의 둘이 **서로 다른 결과**를 내는 것이 AC-BUSKWIZ-007의 핵심이며, 이 셋을 한 테스트에 묶으면 §4 위험 #2가 통과한다.
- **건너뜀 ≠ 미실행** — 빌드 시점 판정(`conflict`/`no_free_slot`)과 실행 시점 중단(`not_executed`, `tools.py:528-536`)은 다른 사건이다(§4 위험 #7). 룩별 판정에서 둘을 똑같이 `none`으로 접는 구현을 떨어뜨리는 테스트가 필요하다.
- **장르 해석 실패 ≠ 저장 0건** — 전자는 정정 가능한 실수로 `is_error=True`, 후자는 답변인 실패로 `is_error=False`다(AC-BUSKWIZ-011 구간 2; 선례 `tools.py:419-429`, `:677-681`, `:783-791`).

### §6.3 번들 규율은 문자열 수준 assert

생성 번들의 커맨드 튜플에 대해 게이트와 독립적으로 빌더 자체의 불변식을 고정한다:

- `commands.count("ChangeDestination Root") == 1` 이고 `commands[0]`이 그것이다(AC-BUSKWIZ-005 ①).
- 룩 2개 번들에서 `ChangeDestination Root`가 2회면 실패 — 단순 연접 형상의 기계적 거부(AC-BUSKWIZ-005 ③, AP-1).
- 각 룩 캡처 사이클 앞과 번들 말미에 `ClearAll`이 있고, **룩 경계에서 연접하지 않는다**(REQ-BUSKWIZ-006).
- `/Overwrite` 부재는 **대소문자 무관**으로 assert한다 — 런타임 매칭이 이미 대소문자 무관이기 때문이다: 옵션 토큰 비교가 양쪽을 `lower()`로 접고(`server/safety/classify.py:71-73`), 키워드 비교도 같다(`:63-65`), 프리뷰도 커맨드 전체를 소문자화해 본다(`server/web/preview.py:100`). 따라서 대소문자를 고정한 assert는 빌더가 `/overwrite`를 내보내도 **조용히 통과**한다(LOOKLIB AP-13, 감사 D14 — 위양성 테스트).
- 커맨드에 등장하는 **모든 번호**가 주입한 리그 픽스처의 값과 일치한다 — 리터럴 유래 번호 0건(AC-BUSKWIZ-015).
- 슬롯 청구 집합이 `{3,4,5}`처럼 **정확히** 일치하고 중복 0건(AC-BUSKWIZ-004 구간 1).
- **값 라인의 번들 내 중복 0건** — §4 위험 #8의 기계 고정. `shared_capture`에서 현재 자산은 0건이지만, 이 assert가 있어야 라이브러리 증보 시 발현이 잡힌다.

### §6.4 회귀 방어선

- **PRESERVE diff 빈 출력** — `server/looks/{schema,loader,roles,resolver}.py` · **`server/looks/instantiate.py`** · `library/` · `server/safety/` · `server/web/preview.py` · `console/lua/` · `server/rulebook/assets/`(AC-BUSKWIZ-014). 추가로 `tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 블록(`:526-550`) 무변경 확인 — 결정 F의 기계 증거다. **`instantiate.py`의 diff가 비어 있지 않다는 것은 결정 E가 반증되었다는 신호**이므로(§2), 그 경우 통과시키지 말고 결정 E를 먼저 재검토한다.
- **기존 스위트** — `test_looks_instantiate.py` · `test_looks_resolver.py` · `test_looks_tool.py` · `test_safety_gate.py` · `test_safety_classify.py` · `test_architecture.py` 신규 실패 0건. 특히 `test_looks_instantiate.py`는 단일 룩 경로의 계약을 고정하므로, 본 SPEC이 원장을 얹으면서 그 계약을 건드렸는지의 1차 신호다.
- **AST 식별자 스캔** — `execution_port` · `ConsoleLink` 직접 접근 0건(AC-BUSKWIZ-009 구간 1). raw 텍스트 grep이 아닌 이유는 LOOKLIB AP-19가 기록한 사고 그대로다 — 텍스트 스캔은 호출과 그 호출을 **금지한다고 적은 독스트링**을 구분하지 못하고, 그때 지워지는 것은 대개 독스트링이다. 동형 스캔이 `server/tests/test_looks_resolver.py:509-529`에 이미 있다.
- **baseline은 이월 인용하지 않는다** — 각 마일스톤은 착수 직전 직접 실측한 수에만 델타를 귀속시킨다(spec.md §C "측정된 기준선"; LOOKLIB이 M1~M4에 걸쳐 baseline 3건 불일치를 끝내 규명하지 못한 전례 `LOOKLIB progress.md:1332`). **`git diff`는 반드시 `<BASE>..HEAD` 형태로 건다** — 인자 없는 `git diff`는 커밋 뒤 항상 빈 출력이라 PRESERVE 게이트(AC-BUSKWIZ-014)가 무력해진다(v0.1.3 감사 지적).

### §6.5 라이브 검증은 2 AC (사용자 확정 ④)

| 세션 | AC | 시점 | 측정 대상 |
|---|---|---|---|
| **M0 프로브** (코드 변경 0) | AC-BUSKWIZ-016 | **M1 착수 전** | ASSUMPTION-16(페이지·익스큐터 저작 문법의 **콘솔 수용 문자열** — `corpus.yaml`의 mock 문자열 확인이 아니다) / ASSUMPTION-17(빈 익스큐터 열거·판별 — §4 위험 #4의 모순) / **ASSUMPTION-19(프리셋을 익스큐터에 직접 얹는 문법의 존부 — §4 위험 #13. 못 찾으면 답은 DESCOPE이고, 시퀀스를 만들어 우회하는 측정은 하지 않는다 — 그 측정은 범위 밖 기능의 근거가 되어 버린다)** / ASSUMPTION-18(**상한 87행**(edm · 4풀) 번들의 무절단 왕복 — 더 작은 합성 번들의 통과는 GO 근거가 아니다) + **중도 실패의 사후 상태**(stop-on-first-failure가 87행에서 어디서 끊고 프로그래머 상태를 어떻게 남기는지 — REQ-BUSKWIZ-013 (e)) + 프로브 잔여물의 무해성 + 미측정 항목(Gaps) 명시. **4건 전부 판정 확정**이 M1 착수 조건이다 |
| **M7 종단** | AC-BUSKWIZ-017 | **M6 완료 후** | `console.executed == plan.commands`(한 줄도 잃지 않음) · `skipped_already_executed` **0건**(AC-BUSKWIZ-005 ④의 유닛 판정이 실물에서 재현) · 재조회에서 프리셋이 **서로 다른 슬롯**에 존재(원장의 라이브 확인) · 집계 수치와 재조회 실측의 일치 · **가산 선택 체인의 실제 항 수 기록**(§4 위험 #6) |

**왜 M0가 M1보다 앞서야 하는가.** 네 전제가 각각 다른 것을 막는다 — ASSUMPTION-16/17/**19**는 REQ-BUSKWIZ-016의 **발동 여부**를, ASSUMPTION-18은 번들 규모 **정책**을 미정으로 만든다. 뒤쪽이 더 무겁다: 부정 판정이면 사용자 확정 ③(단일 승인)과 충돌하는 변경이 필요하고, 그 결정은 SPEC이 아니라 사용자의 것이다(AP-15). 즉 M0는 "저작 전에 전제를 확인한다"는 일반 원칙이 아니라 **미확정 상태로는 M1의 산출물 형상 자체가 정해지지 않는다**는 구체적 이유로 앞선다.

**M0의 부정 판정은 SPEC 실패가 아니다.** ASSUMPTION-16 / 17 / **19 중 하나라도** 부정 → REQ-BUSKWIZ-016 DESCOPE(AC-BUSKWIZ-012 ②)는 **정의된 결과**이며, AC-BUSKWIZ-013의 "익스큐터·페이지 대상 커맨드 0건" 스캔이 그 판정을 기계적으로 고정한다. **19의 부정이 특히 그렇다** — 현재 문서가 가리키는 기본값이 부정이므로(§4 위험 #13) DESCOPE는 예외 처리가 아니라 **예상 결과**에 가깝고, 그때 시퀀스를 만들어 게이트를 우회하는 것은 AP-18이 막는다. 라이브 접근이 아예 불가능하면 M1을 **보류**하고, 예외 진행은 익스큐터 축을 DESCOPE로 선확정하는 것으로만 성립한다 — 그 경우에도 ASSUMPTION-18은 미확정이므로 번들 규모 위험이 열린 채 남는다는 사실을 함께 기록한다(acceptance.md AC-BUSKWIZ-016 비고).

## §7. 반-패턴 (이 SPEC 근처의 유혹)

ID는 **AP-1부터 재시작**한다(SPEC-로컬 번호). LOOKLIB의 AP-n과 번호가 겹치는 것은 의도된 것이며, 인용 시 SPEC 접두를 붙인다.

| # | 유혹 | 왜 금지인가 |
|---|---|---|
| **AP-1** | **룩별 번들을 그냥 이어 붙이기** (`bundle = sum(look_bundles, [])`) | 2..N번째의 `ChangeDestination Root`가 dedupe로 탈락해(`server/orchestrator/tools.py:537`; 면제 3종에 부재 `:227-231`) **번들의 문자열과 콘솔이 실제로 받은 것이 어긋난다**. LOOKLIB M7이 이 탈락을 실물에서 관측했다(`progress.md:799-805`). 룰북 자신이 선두 1회를 규범으로 적는다(`31_choreography_patterns.md:11`). 룩 경계의 `ClearAll` 연접도 함께 생긴다. AC-BUSKWIZ-005 ③이 기계적으로 떨어뜨린다 |
| **AP-2** | **하나의 `PoolIndex`를 룩마다 그대로 `build_instantiation`에 넘기기** | N개 룩이 **전부 같은 슬롯**을 겨냥한다 — `PoolIndex`가 frozen이고(`instantiate.py:96-97`) `_first_free_slot`(`:307-312`)에 전진이 없으며 `_plan_stores`는 읽기만 한다(`:346`, `:358`). 라벨이 달라 `CONFLICT`(`:359-361`)에도 안 걸리므로 **같은 슬롯에 N번 `Store`** 가 조용히 성립한다. 이것이 spec.md §A 하드 결함 1이고 본 SPEC의 존재 이유다. AC-BUSKWIZ-004 구간 2가 결함의 실재와 해소를 함께 assert한다 |
| **AP-3** | **미관측 풀(`occupied is None`)을 빈 풀로 간주해 슬롯 1부터 청구** | `PoolBinding` 독스트링이 그 결과를 직접 적는다 — "That is NOT the same as an empty pool (`()`), and treating it as one is how a store lands on top of somebody's work"(`instantiate.py:82-85`). REQ-BUSKWIZ-009 / AC-BUSKWIZ-007. 원장이 생겼다고 이 규율이 완화되는 것이 아니다 — 원장은 **관측에 더하는** 장치다(§4 위험 #2) |
| **AP-4** | **저장이 서지 않을 때 `/Overwrite`로 밀어붙이기** | 트리거를 정확히 적는다(v0.1.3) — "슬롯이 다 찼다"는 **발생할 수 없는 상태**이고(`_first_free_slot`에 상한 없음 · 풀 용량 상수 0건), 실제로 저장이 서지 않는 경우는 **라벨 충돌**과 **풀 미해석·미관측**이다. 그 둘 중 어느 쪽에서도 `/Overwrite`는 답이 아니다: `Store /overwrite`는 블랙리스트(`server/safety/blacklist.yaml:18`)이자 프리뷰 `caution`(`server/web/preview.py:113-121`)으로 이중 차단된 하한선이며, 충돌 처리는 **건너뛰기 하나**이고 재슬롯도 금지다(REQ-BUSKWIZ-007) — 재슬롯은 "사용자가 의도하지 않은 자리에 조용히 생성"을 만들어 정직한 축소 원칙에 반한다(LOOKLIB 결정 D 계승) |
| **AP-5** | **페이지 커맨드를 `corpus.yaml`에서 복사해 오기** | 두 겹으로 틀렸다. (i) 그 블록은 스스로 **"the deterministic offline action for M6a mock runs ONLY"** 이고 "structurally valid"할 뿐이라고 선언한다(`server/measurement/corpus.yaml:7-10`) — 콘솔 수용을 주장하지 않는다. (ii) `Label Page 3 "Ballad"`(`:99`)는 **큰따옴표**를 쓰는데 `00_grammar.md:26-29`가 생성 커맨드에서 이를 금지한다(전송이 커맨드 라인을 큰따옴표로 감싸므로 내장 큰따옴표는 커맨드를 깨뜨린다). **목 픽스처를 베끼면 문법 위반형을 베낀다.** ASSUMPTION-16의 측정은 "콘솔이 실제로 받아들이는 문자열"을 찾는 일이다(AC-BUSKWIZ-016 측정 1) |
| **AP-6** | **`page*100 + slot`을 "어차피 맞을 테니" 하드코딩** | 이 관례는 **페이지 1에서만** 라이브 관측되었다(`server/web/dash.py:145-163`의 독스트링이 그 출처와 한계를 함께 적는다; 표본 `SPEC-COPILOT-EXECBODY-001/spec.md:43`). `REQ-EXECBODY-007`·`REQ-EXECBODY-008`(`SPEC-COPILOT-EXECBODY-001/spec.md:69-70`)이 "2개 이상 서로 다른 페이지에서 라이브 검증되기 전에는 일반 해석 규칙으로 하드코딩하지 않는다"고 못 박았고 그 조건은 **미충족**이다. 현행 코드조차 계산값을 곧바로 믿지 않는다 — 후보를 만들고 **이름 검증을 통과한 것만** 채택한다(`dash.py:216-229`). REQ-BUSKWIZ-017 / AC-BUSKWIZ-013 ①③ |
| **AP-7** | **dotted `Page 1.201` 형식으로 익스큐터를 주소** | **"콘솔이 거부한다"가 금지 근거가 아니다** — LOOKLIB M7에서 모델이 창발적으로 `Assign Sequence 17 At Page 1.102`를 발화했고 그것은 **실제로 executed 로그에 남았다**(`progress.md:790`, `:858-859`; 인수 계수에서는 제외 `:862`). 근거는 둘이다(spec.md REQ-BUSKWIZ-018 하위 절(금지의 성격을 정확히 적는다)): (a) **출처** — 이 형식은 `00_grammar.md:19`와 `10_object_model.md:23-25`에 진술되어 있으나 그 파일들에는 라이브 검증 표시가 없고, 라이브 검증을 선언하는 룰북 파일은 `31_choreography_patterns.md:7` 하나이며 그 파일은 `Executor <n>`만 담는다(`:104` "Always address `Executor <n>` explicitly"). (b) **단일 형식 일관성** — 게이트의 참조 인식(`server/safety/classify.py:44` `RECOGNIZED_REFERENCE_TYPES`), 본문 해석(`server/safety/console.py:414-421`), 응답기 주소 해석(`console/lua/copilot_responder.lua:403-405` — "the ONLY address form resolve_path special-cases")이 전부 `Executor <n>`에 맞춰져 있어, 두 번째 주소형을 들이면 세 계층이 각각 무엇을 보는지가 갈린다. REQ-BUSKWIZ-018 |
| **AP-8** | **"바인딩하려면 시퀀스가 있어야 하니까" 시퀀스를 온 김에 생성** | spec.md §D가 명시적으로 닫았다 — 버스킹 준비의 산출물은 **팔레트**이고 시퀀스는 P1-1의 영역이다. GO 분기에서도 **바인딩 대상은 이미 존재하는 오브젝트**여야 하며, 그렇지 않으면 시퀀스 생성이 암묵적으로 범위에 들어온다. 이것은 가상의 유혹이 아니다 — LOOKLIB M7에서 모델이 스스로 `Store Sequence 17 Cue 1` → `Assign Page 1.102` → `Go+`까지 나아갔고(`progress.md:1193-1197`), 그 창발 행동은 **인수 결과로 계수되지 않았고 AC 근거로도 쓰이지 않았다**. 같은 규율을 계승한다 |
| **AP-9** | **dedupe 면제 집합을 "한 줄이면 되니까" 확장** | 결정 F의 정면 위반이며 `_PROGRAMMER_STATE_COMMANDS`(`tools.py:227-231`)와 dedupe 블록(`:526-550`)은 PRESERVE다(spec.md §D, AC-BUSKWIZ-014 추가 assert). 면제 확장은 "번들 내 같은 커맨드를 두 번 실행하지 않는다"는 dedupe의 존재 이유를 그만큼 잠식하며, `tools.py:219-225`가 면제 판정에 요구하는 "선행 동사 하나가 무엇을 만들거나 부수는가"의 단순성도 함께 잃는다. LOOKLIB이 "M4가 단독으로 정하지 않는다"고 넘긴 판단(`progress.md:1330`)의 답은 **개정하지 않는다**이며, 그것이 결정 F다 |
| **AP-10** | **보고를 집계만 내고 룩별 판정을 생략** | REQ-BUSKWIZ-013 (d)의 정면 위반. 51~87행 번들에서 어느 룩이 죽었는지 사용자가 알 방법이 사라지고, 이는 §4 위험 #1(사람이 프리뷰를 읽을 수 없다)의 **유일한 완화 수단**을 제거하는 것이다. 부분 성공을 전체 성공으로 위장하지 않는다는 규율의 다중 룩 판(LOOKLIB AP-15 계승). 같은 부류로 **(c) 건너뜀과 (e) 미실행을 한 칸에 합산하는 것**도 금지다(spec.md REQ-BUSKWIZ-013 하위 절((c)와 (e)를 합산하지 않는다)). AC-BUSKWIZ-008 구간 5가 "모든 룩이 정확히 한 번씩 `complete`/`partial`/`none`으로 나타남"을 고정한다 |
| **AP-11** | **"제안서에 있으니까" 포지션 프리셋 팔레트를 부활** | 제안서 :78이 3축의 하나로 적었으나 **선행 SPEC이 닫았고**(`LOOKLIB spec.md:57`, `:192-194`) 사용자 확정 ①이 정적 pan/tilt를 금지했다. 구조도 막고 있다 — `Pan`/`Tilt`는 `MOVEMENT_ONLY_ATTRIBUTES`이고(`server/looks/schema.py:47`) `ATTRIBUTE_POOL_FAMILY` 매핑에 **부재**하므로(`:62-69`) 어떤 풀에도 라우팅되지 않는다. 번복하려면 새 근거(리그별 포지션의 재사용 가능성 증명)와 라이브러리 자산 증보가 함께 필요하고 둘 다 본 SPEC의 조율 계층 범위 밖이다(spec.md §D) |
| **AP-12** | **`find_looks` / `match_looks` 툴 경로로 장르 전량을 조회** | `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71`)이 자르고, **EDM 9룩 중 정확히 1건이 사라진다**(자산 실측 9룩). 상한 자체는 "잘린 목록을 완전한 것으로 제시하지 않는다"는 올바른 규율(`:68-71`)이지만 전량 조회의 도구가 아니다. 더 나쁜 것은 이 실패가 **조용하다**는 점이다 — 8룩이 돌아오고 번들이 만들어지고 실행이 성공한다. 결정 G / AC-BUSKWIZ-001 ①이 이 한 케이스로 경로를 증명한다 |
| **AP-13** | **`capture_shape`를 툴 인자로 되살려 per-family 형상을 허용** | **v0.1.1에서 요구 위반이다** — spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)이 형상을 `shared_capture`로 고정하고 REQ-BUSKWIZ-020이 툴 인자를 장르 식별자 하나로 한정했다. 되살리면 두 가지가 함께 돌아온다: (i) 동일 문자열의 값 라인이 dedupe로 탈락하고(값 라인은 면제 집합 밖 — `tools.py:227-231`) 직전 `ClearAll`은 면제라 살아남으므로 **빈 프로그래머로 `Store`** 가 실행되며 콘솔은 성공으로 답한다(실측 충돌 2건: edm `Attribute 'Dimmer' At 100`, rock `Attribute 'Iris' At 100`), (ii) 번들 상한이 87행 → **135행**(1.55배)이 되어 87에서 받은 ASSUMPTION-18 GO가 그 경로를 덮지 못한다. 유혹이 강한 이유는 기존 `instantiate_look`이 실제로 이 파라미터를 갖고 있어(`tools.py:1035-1046`) "관례를 따른다"는 명분이 붙기 때문이다 — 그러나 그 관례는 **단일 룩** 툴의 것이고, 단일 룩에서는 한 번들에 같은 패밀리가 두 번 나오지 않아 무해했을 뿐이다(REQ-BUSKWIZ-020이 이 구분을 명시한다). §4 위험 #8 |
| **AP-14** | **`run_look_bundle`(`server/web/session.py:289`)에 장르 번들을 태우기** | 그 함수는 단일 `LookInstantiation`을 받는 계약이고 **프로덕션 호출자가 0**이다(`progress.md:1213`, `:889`, `:1118-1121`). 여기에 태우면 모델이 도달할 수 있는 문이 여전히 없는 채로 유닛 테스트만 초록이 된다 — LOOKLIB이 라이브 3회차를 쓴 원인이 정확히 그 상태였고(`progress.md:1224-1229`), M4 테스트가 못 본 이유는 **테스트가 그 함수를 직접 호출했기 때문**이다(`server/tests/test_looks_tool.py:10-12`). 신규 툴은 `registry.dispatch`로 들어가야 하고 테스트도 거기로 들어가야 한다. AC-BUSKWIZ-011 구간 1 |
| **AP-15** | **ASSUMPTION-18이 부정으로 나왔을 때 SPEC이 임의로 번들을 분할** | spec.md §C ASSUMPTION-18이 명시한다 — 분할은 사용자 확정 ③(단일 번들·승인 1회)과 **충돌**하므로 M0 게이트에 **사용자 결정 항목으로 기록**하고 SPEC이 임의로 정하지 않는다. 사용자가 명시적으로 택한 트레이드오프를 구현 편의로 뒤집는 것은, 그 결정을 위해 §4 위험 #1을 수용까지 한 과정 전체를 무효화한다 |
| **AP-16** | **해석되지 않은 장르를 "가장 비슷한 장르"로 승격** | REQ-BUSKWIZ-002 / AC-BUSKWIZ-002 ②의 정면 위반 — 반환된 장르 필드가 `None`이어야 하고 후보 목록과 함께 실패해야 한다. `matching.py:61-66`이 실패 사유 3종을 굳이 나눠 둔 이유가 같다: "물어봤는데 답이 없다"와 "여럿이 똑같이 답했다"는 다른 사실이다. 잘못된 장르로 승격하면 **8~9개 프리셋이 엉뚱한 이름으로 쇼파일에 남고**, 그것은 비가역이다 |
| **AP-17** | **원장 시작값을 빈 집합으로 초기화하고 "충돌하면 콘솔이 거부하겠지"** | 콘솔은 거부하지 않는다. `instantiate.py:291-299`의 `@MX:WARN`이 그대로 적는다 — "A store aimed at a wrong slot destroys a preset the operator built by hand, and **MA3 reports it as success**." 실패가 조용한 영역에서 "런타임이 잡아줄 것"은 방어가 아니다. 원장의 시작값은 항상 `binding.occupied`이며, 그것이 `None`이면 원장을 만들지 않고 건너뛴다(AP-3와 한 쌍) |
| **AP-18** | **레이아웃을 완성하려고 시퀀스를 만든다** — M0가 프리셋을 직접 얹는 문법을 못 찾았을 때 "그럼 프리셋을 리콜하는 시퀀스를 하나 만들어서 그걸 익스큐터에 얹자"로 넘어가기 | **답은 DESCOPE이지 우회가 아니다**(spec.md REQ-BUSKWIZ-016 하위 절(GO여도 발화 형식은 M0가 실측한 것 하나뿐)). 이 우회는 spec.md §D "시퀀스·큐 생성"을 정면으로 열며, 그 순간 시퀀스 저작이 암묵적으로 범위에 들어온다 — 큐 타이밍·시퀀스 라벨·시퀀스 슬롯 충돌이 전부 따라 들어오고, 그중 어느 것도 본 SPEC의 AC가 검증하지 않는다. **AP-8과 구분할 것**: AP-8은 "바인딩하려면 대상이 필요하니 온 김에 만든다"는 **범위 누출**이고, AP-18은 **DESCOPE 판정 자체를 뒤집으려는 것**이라 더 나쁘다 — 전자는 게이트가 열린 상태의 과잉이지만 후자는 **닫힌 게이트를 우회**한다. LOOKLIB M7이 정확히 이 경로를 창발적으로 밟았고(`progress.md:1193-1197` — `Store Sequence 17 Cue 1` → `Assign Page 1.102` → `Go+`) 그 세션은 인수 계수에서 제외했다(`:862`). 사람이 같은 일을 "레이아웃을 완성하려고" 하면 제외할 근거가 없어진다. **DESCOPE는 실패가 아니라 정의된 결과다**(REQ-BUSKWIZ-016 하위 절(하나라도 부정이면 DESCOPE), AC-BUSKWIZ-012 ②) |

## §8. 교차 참조

- **본 SPEC 내부** — `spec.md` §A(사전 확정 4건 + 하드 결함 2건) · §B(REQ-BUSKWIZ-001~020) · §C(ASSUMPTION-16/17/18/19) · §D(Out of Scope 6절) · §E(참조 구현 표); `acceptance.md` §C.0(REQ↔AC 역추적 + 마일스톤별 AC 집합) · §D(Edge Cases) · §F(DoD); `plan.md` §A.4a(결정 A~G — 본 문서 §5.1과 1:1) · §B(M0~M7).
- **슬롯 원장의 근거(결정 E)** — `server/looks/instantiate.py:78-85`(frozen + 미관측 독스트링) · `:96-102`(`PoolIndex`) · `:307-312`(`_first_free_slot`) · `:325-384`(`_plan_stores`) · `:291-299`(`@MX:WARN` — 잘못된 슬롯의 결과).
- **번들 형상과 dedupe(결정 F)** — `server/orchestrator/tools.py:219-237`(면제 집합 + 판정) · `:516-562`(dedupe + stop-on-first-failure) · `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:9-23`(`ChangeDestination Root` 선두 1회) · `:40-41`(`ClearAll` 규율) · `server/looks/instantiate.py:387-413`(`_bundle` 두 형상).
- **단일 실행 경로와 프리뷰** — `server/safety/gate.py:260-265` `@MX:ANCHOR` · `server/orchestrator/tools.py:684-696` `@MX:ANCHOR`/`@MX:REASON`(핸들러는 호출자이지 제2 경로가 아니다) · `server/web/session.py:149-166`(프리뷰가 스크리닝을 **감싼다**) · `server/web/preview.py:99-170`, `:198-203`.
- **익스큐터 축의 근거와 금지** — `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:7`(유일한 라이브 검증 선언), `:96-104`(`Assign Sequence … At Executor <n>`) · `server/web/dash.py:129-143`, `:145-163`, `:194-238`, `:309-317` · `server/measurement/corpus.yaml:7-10`(mock 자인) · `server/rulebook/assets/v2.4.2/00_grammar.md:19`, `:24-34` · `SPEC-COPILOT-EXECBODY-001/spec.md:43`, `:69-70`; GO/DESCOPE 선례 `SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123`.
- **LOOKLIB이 남긴 라이브 관측(구속력 있음)** — `SPEC-COPILOT-LOOKLIB-001/progress.md:799-807`(dedupe 1건 + `ClearAll` 4/4) · `:834-838`(가산 선택·`Store Preset` 최초 라이브 검증) · `:1167-1173` · `:1209-1215`(잔여 위험) · `:1216-1230`(계획 2회 vs 실제 3회) · `:1326-1330`(FALLBACK 거부 해제 + M4 블로커 이관) · `:602-606`(M4가 남긴 미검증 4건).
- **선례 문서 구조** — `SPEC-COPILOT-LOOKLIB-001/design.md` §5.0(허위 1:1 주장의 정정 사례) · §5.1(fold-in 표) · §6.5(라이브 2 AC) · AP-19(스캔을 고치고 산문을 지킨다); `SPEC-COPILOT-EXECBODY-001/design.md` §5(열린 슬롯 → 라이브 fold-in 구조의 원형).
- **제품 근거** — `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:76-80`(P1-2) · `.moai/project/product.md:38`(Phase 2 성공 기준 — 본 SPEC이 실제로 충족하는 행), `:40`(Phase 4 "버스킹 팔레트 추천" — 성공 기준 TBD), `:44`(§6 비목표 — 라이브 실시간 자율 운영 배제. v0.1.3 정정: `:43`은 빈 줄이었다).
- **SSOT가 닫은 항목 ↔ 본 문서 대응** (줄 앵커 대신 토큰 — 위 참조 규약) — REQ-BUSKWIZ-005 하위 절(원장은 슬롯과 함께 라벨도 누적한다) → §4 위험 #9 · REQ-BUSKWIZ-006 하위 절(캡처 형상 고정) + REQ-BUSKWIZ-020 → 위험 #8 · AP-13 · §2 항목 3 · REQ-BUSKWIZ-013 (e) + 하위 절((c)와 (e)를 합산하지 않는다) → 위험 #7 · 하위 절((b)의 사유) → §6.2 · 하위 절((b)의 집계 단위) → 위험 #11 · §6.2 · REQ-BUSKWIZ-016 3항 논리곱 + 하위 절(ASSUMPTION-19가 게이트에 추가된 이유 / GO여도 발화 형식은 하나뿐 / 하나라도 부정이면 DESCOPE) → 위험 #13 · AP-18 · §2 항목 4 · §5.1 결정 A · REQ-BUSKWIZ-010 트리거 정정(v0.1.3 도달 불가 제거 → v0.1.4 최종 열거 둘: 풀 미해석 · 라벨 충돌) → 위험 #7 · AP-4 · spec.md §A "번들 규모의 실측"·"수용된 잔여 위험" + §C ASSUMPTION-18 → 위험 #1·#5 · §6.5 · spec.md §C "측정된 기준선" → §6.4 · AC-BUSKWIZ-012 ① 번호 출처 교체 → 위험 #4.
