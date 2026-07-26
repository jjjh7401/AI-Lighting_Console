# SPEC-COPILOT-LOOKLIB-001 — Plan-Phase Research

status: draft (v0.3.1, 2026-07-26). 본 문서는 룩 라이브러리(연출 어휘 계층)가 얹힐 기존 코드베이스를 file:line 근거로 분석한다. **구현 코드는 제안하지 않는다 — 분석 전용.** 라이브 콘솔 조사는 이번 plan-phase 세션에서 수행하지 않았다(기존 SPEC들의 라이브 검증 결과와 룰북의 "validated" 표기를 재사용한다).

> **v0.3.1 — 감사 PASS(0.92) 이후 정리 개정.** 조사 결론·기각 대안·참조 표는 **무변경**이다. (a) **F2 (§5.5 함의 2항)** — 무브먼트 `caution` 항목이 "무브먼트를 담은 룩"을 전제하고 요약 보고(REQ-013)에 설명 의무를 부과하고 있었으나, §D가 무브먼트 인스턴스화를 v1에서 제외한 뒤로 **그 시나리오는 v1에서 성립하지 않는다**(REQ-013에도 대응 요소가 없어 어떤 요구와도 연결되지 않은 채 떠 있었다). v1 룩 번들에서 **도달 불가 경로**임을 명시하고, 폴백 경로에서는 여전히 유효함을 분리해 적었다. (b) **F3 전파** — §4 페이저 항목에 "문법은 검증되었으나 v1은 쓰지 않는다"를, §10에 "무브먼트 라이브러리 금지가 P1-1/P1-2 소비 계약을 깨지 않는 이유"를 보강.
>
> **v0.3.0 — 재감사(FAIL 0.80) 반영 최종 개정.** 세 건을 정정·보강한다:
> - **폐쇄된 결정을 여전히 이연하고 있던 표기 정정 (§2)**: `:28` 제목과 `:32` 결론 3이 저장 형식·매칭 표면을 "plan.md §A.4 마커 ①/⑤로 이연"이라 적고 있었는데, **§9.1이 같은 문서 안에서 두 항목을 이미 폐쇄로 기록**하고 있었다 — 한 문서가 스스로와 모순된 상태였다. 마커 번호(①/⑤)도 v0.2.0에서 폐기된 표기다.
> - **§8 표의 낡은 라벨 정정**: `20_korean_terms.md`를 "**역할 어휘 클래스 사전**(showfile 행)"이라 부르고 있었는데, 이는 **§3이 정정으로 뒤집은 바로 그 프레이밍**이다(감사 D3 — 그 파일의 showfile 행은 픽스처 타입 클래스이지 포지션 역할이 아니다). §3과 §8이 서로 모순됐다.
> - **§4 프리셋 주소 체계 보강**: 프리셋 풀이 **속성 패밀리별로 조직**된다는 사실이 한 룩이 여러 풀에 걸친다는 귀결로 이어지는데, v0.2.0은 그 귀결을 적지 않아 `<pool>`이 미결로 남았다. plan.md §A.4a 결정 I의 근거를 여기 명시한다.
> - **§9 갱신**: 미결 지점 **3건 → 0건**.
>
> **v0.2.0 — 독립 감사(FAIL 0.65) 반영.** 두 건의 조사 결함을 보강한다:
> - **누락 (감사 D5)**: v0.1.0은 **`server/web/preview.py` 실행 프리뷰 계층 전체를 놓쳤다.** 이 계층은 룩 인스턴스화 경로에 **반드시** 놓여 있고(스크리닝을 감싼다), 스트로브를 `danger`로 분류해 룩 라이브러리의 v1 속성 범위 결정에 직접 영향을 준다. §5.5·§6 프리뷰 절·§8 표에 보강.
> - **오주장 (감사 D3)**: v0.1.0 §3 마지막 불릿은 `20_korean_terms.md`의 showfile 행이 "역할→그룹 휴리스틱의 사전 기반이 이미 존재한다"고 서술했다. 실측 결과 **거짓**이다. §3에서 정정.

---

## §1. 출처 — 제안서 P1-3 + 로드맵 Phase 2 + 사용자 사전 확정

- **제안서**: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 P1-3(82-86행) — "웅장한 금색 코러스" 같은 추상 지시를 **앵글·컬러·강도·무브먼트 조합의 '룩'**으로 변환하는 디자인 지식 레이어. 장르별(록/발라드/워십/EDM) 룩 템플릿 내장 + 사용자 리그에 맞는 인스턴스화. **P1-1(송 구조 큐리스트 생성기)·P1-2(버스킹 마법사)가 모두 이 어휘 위에서 돌아가는 공통 기반**(86행, §4 결론 118-119행).
- **로드맵 정합**: `.moai/project/product.md` §5 Phase 2(38행) — "'코러스에서 금색 톤으로 웅장하게' 수준의 추상 지시를 리그에 맞게 실행"이 Phase 2 성공 기준. 본 SPEC은 그 목표의 실체화다. §6 비목표(44-45행) — 미적 최종 판단은 사람, 라이브 자율 운영 배제 — 는 본 SPEC이 그대로 계승한다.
- **사용자 사전 확정 3건**(이번 세션, 재질의 금지 — spec.md §A에 전문 수록): ① v1 룩 속성 = 컬러/강도/빔 구체값 + **포지션은 역할 추상**(백라이트·FOH 워시·사이드 등, 인스턴스화 시점 리그 그룹 매핑 — 하드 pan/tilt 아님), ② v1 장르 = 워십/록/발라드/EDM 4종 × 장르당 6~10 룩(**하드 범위** — REQ-002/AC-002가 기계 assert; 잔잔함→클라이맥스 섹션 다이내믹스 스팬, 척도는 정수 1~5로 확정), ③ v1 범위 = 데이터 계층 + MA3 인스턴스화 + **자연어 매칭까지 전부** — 완결된 사용자 기능이지 데이터 계층만이 아니다.

---

## §2. 조사 ① — 룰북 시스템 (룩이 살 곳의 첫 번째 후보)

### 실측 구조

- 룰북은 **고정(FIXED) 시스템 프롬프트 프리픽스**다: `server/rulebook/assembly.py:1-15` docstring — "assembled from static markdown assets under `assets/v<version>/` in sorted filename order — nothing else. No timestamps, session IDs, or any per-turn variable value may enter this string". 제공자 캐시(Anthropic prompt caching / Gemini context caching, REQ-MVP-041)가 이 문자열을 **바이트 단위로** 캐싱하며, 1바이트 변경이 전체 캐시를 무효화한다(AC-MVP-014가 byte identity를 핀).
- 조립 경로는 **정확히 하나**: `assemble_prefix()`(assembly.py:73-76), `@MX:ANCHOR`(assembly.py:69-72) — "the fixed system-prompt prefix is built ONLY here". 소비 지점: `server/web/serve.py:284`(서버 기동 시 1회), measurement 러너(`server/measurement/runner.py:276,336,392`).
- 자산: `server/rulebook/assets/v2.4.2/` 5파일 — `00_grammar.md`(128행), `10_object_model.md`(40행), `20_korean_terms.md`(36행), `30_plugin_patterns.md`(63행), `31_choreography_patterns.md`(206행). 파일명 정렬 순서로 이어붙임(assembly.py:61-66). 버전은 `RULEBOOK_VERSION = "2.4.2"`로 핀(assembly.py:25).
- `20_korean_terms.md`의 마감 규칙(31-36행): "this dictionary is part of the FIXED prompt prefix — **it never contains per-show or per-turn values**. Showfile-dependent rows name a vocabulary CLASS; the concrete group and preset ids come from `get_rig_context` at run time." — **정적 어휘 클래스는 룰북에, 쇼파일 구체값은 런타임 조회로**라는 이 프로젝트의 확립된 분리 원칙.

### 룩 저장 위치 결정에 주는 함의 (설계 입력 — plan.md §A.4a 결정 **A**(저장 형식)·**E**(매칭 표면)의 제약 문맥)

1. **룩 데이터를 룰북 자산에 통째로 넣을 수 없다.** 4장르 × 6~10룩 × (컬러/강도/빔/역할/무드 키워드) 구조화 데이터는 (a) 매 턴 토큰 비용이 반복 발생하는 고정 프리픽스를 크게 불리고, (b) 룩 데이터 수정 때마다 프리픽스 바이트가 바뀌어 캐시가 무효화되며, (c) 무엇보다 서버 코드(매칭·인스턴스화 로직)가 소비할 **구조화 데이터**인데 룰북은 LLM 전용 산문이다.
2. **반면 `20_korean_terms.md` 선례는 "정적 어휘 안내 축"이 룰북에 사는 것이 자연스러움을 보여준다** — 룩 시스템의 존재·사용법("추상 무드 지시가 오면 룩 라이브러리를 먼저 조회하라" 류)을 안내하는 **얇은 정적 축**은 룰북 확장 후보다. `31_choreography_patterns.md:173-206`의 기존 "Concept / mood instructions" 절(무드→디자인 시작점 표)이 바로 그 자리에 이미 있고, 룩 라이브러리는 이 절의 조악한 4행 무드 표를 대체·정밀화하는 관계다.
3. **결론 (v0.3.0 — 이연 표기 삭제, 확정 상태 반영)**: 구조화 룩 데이터는 **서버측 별도 데이터 계층**(신규 패키지)이 단일 진실원, 룰북에는 **얇은 정적 안내 축만** 둔다. 이 형상은 **plan.md §A.4a 결정 E(하이브리드)로 확정**되었고 저장 형식은 **결정 A(YAML repo 자산)** 로 확정되었다 — 안내 축을 넣을지도, 31 무드 절과의 관계도(대체가 아니라 **보완**: 무드 절은 폴백으로 무변경 보존, 안내 축은 "라이브러리를 먼저 조회하라"만 말한다) 더 이상 열려 있지 않다.
   - **v0.2.0의 결함**: 이 줄과 위 제목이 두 항목을 "plan.md §A.4 마커로 이연"이라 적고 있었으나, **같은 문서의 §9.1이 두 항목 모두 폐쇄로 기록**하고 있었다 — 한 문서가 스스로와 모순된 상태였고, 마커 번호(①/⑤) 자체도 v0.2.0에서 폐기된 표기였다.

---

## §3. 조사 ② — get_rig_context (역할→리그 매핑의 데이터원)

- **10 조회 경로**: `DEFAULT_RIG_CONTEXT_PATHS`(server/orchestrator/tools.py:65-76) — fixture_types / fixtures(`Patch/Stages/1/Fixtures`) / **groups(`DataPool/Groups`)** / sequences / **preset_pools(`DataPool/PresetPools`)** / macros / plugins / pages / matricks / worlds. 전 경로 2026-07-22 라이브 onPC 2.4.2에서 판독 확인 후 기본값 승격(tools.py:53-55 — "Guessed paths are how 'Patch/Fixtures' and 'DataPool/Presets' shipped dead for the whole of Stage 1" — **경로 추측 금지 교훈**).
- **드릴다운**: `DEFAULT_RIG_DRILLDOWN = ("preset_pools", "pages")`(tools.py:81) + 쿼리 상한 `RIG_DRILLDOWN_QUERY_CAP = 16`(tools.py:88) — 프리셋 풀은 "풀 존재"와 "풀 안에 뭔가 저장됨"이 다른 답이라 한 층 더 연다(tools.py:38-44). 상한 초과 시 `drilldown_capped` 명시(부분 워크를 완전한 것처럼 제시 금지).
- **실패 사유 이분**: `path_not_resolved`(설정 결함) vs `console_unreachable`(운영 조건) — tools.py:104-105, 병합 금지(REQ-SHOWUI-002가 이미 소비).
- **키잉 계약**: `rig_object`(tools.py:185-211) — 실제 풀 번호 `no` 노출, 배열 인덱스 아님. 그룹/프리셋 풀은 그 `no`가 곧 발화 번호(`Group <no>`). 슬롯을 확정 못 한 자식은 `no` 없이 이름만 도착(성능 저하가 아니라 의미 있는 신호).
- **슬롯≠FID gotcha**: fixtures 섹션의 번호는 스테이지 패치 슬롯이지 FID가 아니다(tools.py:33-36, 20_korean_terms.md 마감 규칙, 룰북 31:184-189). **역할 매핑은 그룹을 우선해야 하는 구조적 이유** — 룰북 31:186 "Prefer a group".
- **역할 매핑에 쓸 실질 데이터**: groups 섹션의 `{no, name}` 목록.
- **⚠️ 정정 — 역할 어휘의 사전 기반은 존재하지 않는다 (감사 D3).** v0.1.0은 여기서 "`20_korean_terms.md`의 showfile 행들이 이름 관례 기반 매핑을 이미 확립된 어휘 클래스로 정의해 뒀다 — 역할→그룹 휴리스틱의 사전 기반이 이미 존재한다"고 서술했다. **실측 결과 이 주장은 성립하지 않는다:**
  - `20_korean_terms.md`는 **36행**이고, 그 showfile 행 7종은 샤막(:11) / 워시(:12) / 무빙(:13) / 스팟(:14) / 빔(:15) / 핀조명·폴로스팟(:16) / 객석등(:29)이다. 이들은 전부 **픽스처 타입 클래스**(Wash-class, Spot/Profile-class, Beam FixtureType, Followspot…)를 가리킨다.
  - 본 SPEC이 필요로 하는 것은 **무대 위 공간적 포지션 역할**(백라이트 / 프론트 / 사이드 / 탑 / 배경 / 스페셜)이다. 이는 다른 차원의 분류다 — 하나의 Wash 픽스처가 백라이트일 수도 프론트일 수도 있다.
  - 검증: `백라이트` / `FOH` / `사이드` / `스페셜`을 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/` 전체에서 검색 → **매치 0건**.
  - **결론**: 포지션 역할 어휘는 본 SPEC이 **새로 만드는 어휘**다. 상속할 사전이 없으므로 집합 구성이 실질 설계 결정이 되었고, **plan.md §A.4a 결정 J(사용자 확정 ⑨)로 6종 폐쇄 집합 + 6종 전부의 매핑 힌트 문자열이 확정**되었다(정본 표: spec.md §A). 기존 파일과의 관계는 *행 단위 정합*이 아니라 **명명 관례 스타일 준수**에 그친다(spec.md REQ-006). `20_korean_terms.md`는 무변경 PRESERVE 대상이다.
  - **힌트 설계에 이 조사가 직접 기여한 것**: (a) `20_korean_terms.md:11`의 `샤막 | ... Group named like 'Cyc'/'샤막'` 행이 **배경 역할 힌트의 스타일 선례**가 된다 — 그 파일을 수정하지 않고도 관례를 따를 수 있음을 보여주는 구체 사례. (b) 반대로 `워시`(:12)·`스팟`(:14)·`빔`(:15)은 **픽스처 타입 클래스이므로 어떤 역할의 힌트에도 넣지 않는다** — 하나의 Wash 픽스처가 백라이트일 수도 프론트일 수도 있으므로, 타입 어휘를 힌트에 넣으면 매핑이 체계적으로 오조준된다. 이 배제가 D3 교훈의 기계적 형태이며 AC-015 ④가 검증한다.
  - **여전히 유효한 부분**: showfile 행들이 확립한 **"이름 관례로 그룹을 찾는다"는 접근 방식 자체**(`Group named like 'Wash'/'워시'`)는 유효한 선례다. 상속되지 않는 것은 *어휘 목록*이지 *매핑 기법*이 아니다.
- **공유 헬퍼는 public**: `rig_object`/`rig_section`/`drill_into`(tools.py:168-177 주석) — 패널 카탈로그(panel.py)가 이미 두 번째 소비자다. 룩 리졸버가 세 번째 소비자가 되는 것이 의도된 재사용 형상.

---

## §4. 조사 ③ — 프리셋/그룹/큐 생성의 라이브 검증된 커맨드 패턴

- **프로그래밍 목적지 규칙**(라이브 검증): 모든 프로그래밍 번들 선두에 `ChangeDestination Root` 정확히 1회 — 룰북 `31_choreography_patterns.md:9-23`. 패치의 정반대 규칙(패치 플러그인은 ChangeDestination 금지 — 30_plugin_patterns). 이 규칙 위반이 "Illegal object"의 주 원인.
- **선택**(검증): bare `Fixture 11 Thru 19` / `Group 11` — `Select Fixture`/`SelFix` 금지(31:25-31).
- **값 설정**(검증): `Attribute 'Dimmer' At 80`, `'ColorRGB_R/G/B'` 0-100, `'Pan'/'Tilt'` 퍼센트, `;` 체인(31:33-39). **`ClearAll` 규율**: 새 룩 캡처 전 + 매 `Store` 후 — 프로그래머 잔류값이 다음 캡처로 TRACK되어 조용히 오염(31:40-41, 128-134 트래킹 모델).
- **프리셋/그룹 저장 레시피**: `Fixture ... Thru ...` → `Store Group 7` → `Label Group 7 'Vocals'`(00_grammar.md:66); 값 설정 후 `Store Preset 4.2` → `Label Preset 4.2 'Warm Wash'`(00_grammar.md:67-68). 프리셋 주소는 `Preset <pool>.<slot>`(10_object_model.md:20, pool 4 = "Color" 예시 00_grammar.md:18). 풀별 실제 번호·슬롯 점유는 쇼파일 종속 — get_rig_context preset_pools 드릴다운이 런타임에 답한다.
- **프리셋 풀은 속성 패밀리별로 조직된다 (v0.3.0 보강 — 결정 I의 직접 근거)**: `10_object_model.md:18-20` — "**Preset** — stored attribute values, **organized in pools by attribute family**: Dimmer, Position, Gobo, Color, Beam, Focus, Control, Shapers, Video, All." 패밀리 경계는 `:38-40`이 정의한다 — **Beam = iris/prism/frost, Focus = zoom/focus**(v0.1.0이 zoom을 Beam으로 묶은 오류의 정정 근거).
  - **v0.2.0이 적지 않은 귀결**: 컬러 + 강도(+ 빔)를 함께 담는 하나의 룩은 **여러 풀 타입에 걸친다.** 즉 룩 1개의 인스턴스화는 `Store Preset` 하나가 아니라 **패밀리 수만큼**이다. 이 귀결이 기록되지 않아 `<pool>`이 여섯 아티팩트에서 미결로 남았고, 그 미결이 번들 형상·스킵 카운트 단위·ASSUMPTION-14의 실측 대상·요약 보고 형상까지 함께 미정으로 끌고 갔다(design.md §4 위험 #11).
  - **풀 번호는 런타임에 해석 가능하다** — `server/orchestrator/tools.py:39-44`는 preset_pools가 "**the preset TYPES (Dimmer, Position, Gobo, Color, ...)**"이며 개별 프리셋보다 한 층 위임을 명시하고, `:81`이 이 경로를 기본 드릴다운으로 열며, `rig_object`(`:185-190`)가 **실제 풀 번호 `no`를 이름과 함께** 반환한다. 따라서 `Preset 4.1 = Color`를 코드에 박을 필요가 없다 — 박는 것은 `tools.py:53-55`가 기록한 "추측된 경로는 죽은 채 출하된다" 사고의 반복이다(design.md AP-16).
  - **v1 in-scope 풀**: Dimmer · Color (+ ASSUMPTION-15 GO 시 Beam · Focus). Position은 정적 pan/tilt 금지로 담을 값이 없고, All은 무차별 캡처라 패밀리별 검증을 불가능하게 만든다 — plan.md §A.4a-I.
- **룩→큐 저장**(검증): `Store Sequence 11 Cue 1 'Warm Wash' CueFade 2`, 시퀀스는 첫 store에서 자동 생성, `/Merge` 추가·**`/Overwrite`는 파괴적 → 안전 게이트가 사람 승인으로 라우팅**(31:43-59).
- **페이저/MAtricks**(검증): Phase 0 Thru 360 팬, Speed, Step, MAtricks Set/Reset(31:61-94) — 룩의 "무브먼트" 속성이 쓸 수 있는 검증된 표면. **단 v1은 이 표면을 쓰지 않는다** (v0.3.1 — F3): 번들이 무브먼트를 발화하지 않고(spec.md §D) v1 라이브러리도 무브먼트를 담지 않는다(REQ-003 신설 절, AC-003 구간 6). 문법이 검증되어 있다는 사실과 v1이 그것을 쓴다는 사실은 별개이며, 이 절은 **후속 SPEC이 켤 때를 위한 조사 기록**으로 남는다 — 빔(문법 미검증이라 못 쓴다)과 달리 무브먼트는 **쓸 수 있는데 v1이 범위 밖으로 둔 것**이다.
- **재생**(검증): `Assign Sequence 11 At Executor 191` / `Go+ Executor N` / `Off Executor N`(31:96-104).
- **생성형 Lua 경로**(검증): 루프·수학·다량 계산 큐는 Lua 플러그인 `main()`이 동일 커맨드 문자열을 `Cmd()`로 발화 — `ChangeDestination Root` 선행, 시간 스텝 루프는 `coroutine.yield`, `deploy_plugin` 후 `Plugin 'Name'` 실행(31:136-171). 다량 프리셋 인스턴스화의 대안 경로.
- **무드 폴백**: 룰북 31:173-206 "Concept / mood instructions" — get_rig_context 먼저, 실존 그룹만, **미등재 `Group 3` 발명 금지**(31:190-191), 조악한 무드→값 표(31:195-202). **룩 라이브러리가 정밀화·대체하는 대상이자, 매칭 실패 시의 보존해야 할 폴백**.

---

## §5. 조사 ④ — 서버/툴/배포 통합 지점 (매칭 계층이 꽂힐 곳)

- **툴 표면**: `TOOL_NAMES = ("run_commands", "query_state", "deploy_plugin", "get_rig_context")`(tools.py:23), 레지스트리는 `build_toolset()`(tools.py:304)이 조립, 채팅 세션이 `server/web/session.py:210`에서 생성. **신규 툴은 이 두 지점 + provider adapter의 ToolDefinition 직렬화로 등록**된다(REQ-MVP-005 형상).
- **채팅 파이프라인**: 한국어 지시 1턴 = `session.run_instruction`(session.py:354) — worker thread, 단일 지시 턴 락(app.py:322-325 busy_event + `asyncio.to_thread`). `_last_created` 크로스턴 메모리(session.py:202, 278, 387-400)가 "방금 만든 것"을 다음 턴에 주입(session.py:403-409) — **룩 인스턴스화 직후 "방금 그 룩 더 밝게" 류 후속 지시의 기존 지원 기제**.
- **제공자 스위치**: `build_provider`(server/llm/factory.py:17-28) — config `active` 값으로 anthropic/gemini 단일 어댑터 부팅(config.py:24 default_config_path, :126 load_provider_config). 양쪽 모두 고정 프리픽스 캐싱을 전제(anthropic_adapter.py:5, gemini_adapter.py:5) — **룩 매칭 설계는 제공자 중립이어야 한다**(툴/프롬프트 형상 공통 표면만 사용).
- **서버측 영속화 선례**: `PinStore`(server/web/panel.py:186-330) — `user_data_dir()/panel_pins.json`(panel.py:176-177, settings.py:184), 원자적 쓰기(temp + `os.replace`, panel.py:302-324), 자격 증명 거부(panel.py:155). **런타임 사용자 데이터의 확립된 패턴**. 정적 규칙 데이터의 선례는 `server/safety/blacklist.yaml`(YAML, repo-shipped; PyYAML은 이미 런타임 의존성 — ruleset.py:16,63).
- **배포 파이프라인**: `deploy_plugin` 툴 → pcall compile → destructive `Cmd()` scan → 사람 리뷰 게이트(deny-all 기본)(server/deploy/pipeline.py:5-12, tools.py:1-8). 패키징은 `server/deploy/pack.py` `build_plugin_xml`(:60, 네이티브 인라인 Base64 — 메모리의 "plugin_pack.py"가 가리키는 실체). 파일+Import 수동 경로와 앱 자동 배포 경로 모두 확립됨(EXECBODY-001 M3 실측). **룩 인스턴스화가 생성형 Lua 경로를 쓸 경우 이 파이프라인을 그대로 탄다 — 우회 금지**.
- **UI 표면**: 현행 콘솔 제어면은 DASHUI-001 세대(dash.py + panel.py 경로 재사용). 채팅이 자연어 매칭의 유일한 v1 표면이며 UI 변경은 본 SPEC 범위 밖(§D).

### §5.5 실행 프리뷰 계층 — v0.1.0 조사 누락분 (감사 D5)

**룩 인스턴스화 경로에 반드시 놓이는 계층인데 v0.1.0 연구가 통째로 놓쳤다.** 룩 데이터의 v1 속성 범위 결정(특히 스트로브)에 직접 영향을 주므로 여기 보강한다.

- **배선 지점**: `ChatSession.__init__`이 `build_toolset(...)`에 `bundle_gate=_ObservingBundleGate(gate, self._on_preview, self._on_decision)`를 넘긴다(`server/web/session.py:213`). 즉 **채팅 세션이 만드는 모든 툴셋**이 이 래퍼를 통과한다 — `run_commands`가 발화하는 룩 번들도 예외 없다.
- **호출 순서 — 프리뷰는 스크리닝을 감싼다 (이후가 아니다)**: `_ObservingBundleGate.screen`(`server/web/session.py:161-165`)의 본문은 정확히 세 줄이다 —
  1. `self._on_preview(commands)` ← **스크리닝 이전**
  2. `decision = self._gate.screen(commands)` ← 기존 3-스테이지 게이트
  3. `self._on_decision(decision)` ← 스크리닝 이후

  이 순서가 중요한 이유: 프리뷰 경고는 게이트 판정과 **독립적으로** 발화한다. 게이트가 무해하다고 판단해 승인 없이 통과시키는 번들이라도, 프리뷰는 그 커맨드의 위험 등급을 사용자에게 표시한다.
- **프리뷰 생성**: `ChatSession._on_preview`(`session.py:236-244`) → `build_execution_preview(preview_id=..., commands=...)`(`server/web/preview.py:36`) → `execution_preview_event(preview=preview)`로 클라이언트 송신.
- **커맨드별 경고 분류**(`server/web/preview.py:99-170`, 입력은 `lower = command.lower()`로 **대소문자 무관**, `:100`):

  | 패턴 | severity | label | 근거 라인 |
  |---|---|---|---|
  | `delete` 액션 | `danger` | 삭제 명령 | :104-112 |
  | `store_overwrite` 액션 | `caution` | 덮어쓰기 | :113-121 |
  | `blackout` / `off` 액션 | `danger` | 블랙아웃/오프 | :122-130 |
  | **`\b(strobe\|shutter\|hz)\b`** | **`danger`** | **스트로브/셔터 변화** — "스트로브 Hz 또는 셔터 상태가 **관객과 카메라에 직접 영향**을 줄 수 있습니다." | **:131-139** |
  | `\b(blinder\|audience)\b` 또는 `객석` | `danger` | 객석 블라인더 | :140-148 |
  | `\b(pan\|tilt)\b` (`_has_movement`, :173-174) | `caution` | Pan/Tilt 이동 | :149-157 |
  | `full` / `at 100` / `dimmer 100` (움직임 없을 때만) | `caution` | 풀 인텐시티 | :158-169 |

  경고들은 `_dedupe_warnings`(:186)로 중복 제거되고 `_risk_level`(:198)이 번들 전체 등급으로 승격한다.
- **테스트 핀**: `server/tests/test_web_preview.py:39-43` — `test_strobe_hz_gets_danger_preview`가 `risk_level == "danger"`와 `warnings[0]["label"] == "스트로브/셔터 변화"`를 고정한다. 즉 이 분류는 우발적 구현이 아니라 **의도적으로 핀된 계약**이다.

**룩 라이브러리에 주는 함의**:

1. **스트로브를 담은 룩은 인스턴스화할 때마다 최고 위험 등급 프리뷰를 유발한다.** 4장르 중 록·EDM·워십의 클라이맥스 대역이 스트로브를 자연스럽게 부르는 자리인데, 여기에 스트로브를 넣으면 **클라이맥스 룩 전체가 상시 danger**가 되고 사용자는 곧 danger 표시를 무시하게 된다(경보 피로). 이는 관객 안전 장치를 무디게 만드는 방향이다 → **v1 라이브러리는 스트로브/셔터 제외**(spec.md §A 사전 결정 규칙, §D Out of Scope, design.md §4 위험 #9).
2. **무브먼트(페이저)의 `caution` 경로는 v1 룩 번들에서 도달 불가다 (v0.3.1 정정 — F2)** — `Attribute 'Pan' At Phase 0 Thru 360`이 `_has_movement`(:173-174)에 걸려 `caution`을 유발하는 것은 사실이지만, **v1 룩 번들은 이 문자열을 발화할 수 없다.** spec.md §D가 무브먼트의 프리셋 인스턴스화를 v1에서 제외했고(번들 미발화), v0.3.1의 F3이 여기에 **v1 라이브러리의 무브먼트 수록 금지**까지 더했다(REQ-003 신설 절 / AC-003 구간 6). 따라서 v1에서는 룩발 번들에 `Pan`/`Tilt`가 등장하는 경우 자체가 없고, 이 프리뷰 경로는 **룩 계층과 무관하게** 남는다.
   - **무엇이 정정되었는가**: v0.3.0의 이 항목은 "무브먼트를 담은 룩이 왜 주의 표시가 뜨는지를 요약 보고(REQ-013)가 설명해야 한다"고 적어 **§D 확정 이후 성립하지 않는 시나리오**를 요구로 남겨 두었다. REQ-LOOKLIB-013의 보고 요소 (a)~(d)에도 그런 설명 항목은 없다 — 즉 이 문장은 어떤 요구와도 연결되지 않은 채 떠 있었다. §5.5가 v0.2.0에서 신설된 뒤 §D의 무브먼트 제외가 확정되었는데 이 항목이 함께 갱신되지 않은, **잔존 산문의 전파 실패**다(F1과 같은 부류).
   - **여전히 유효한 부분**: 사용자가 **폴백 경로**에서 직접 Pan/Tilt를 지시하면 기존 프리뷰가 그대로 `caution`으로 분류한다. 본 SPEC은 그 경로를 바꾸지 않는다(REQ-021, 위 4항).
3. **충돌 정책이 건너뛰기인 것이 프리뷰 관점에서도 옳다** — `Store /Overwrite`는 `caution`을 유발하므로, 건너뛰기 정책은 블랙리스트 승인 보류뿐 아니라 프리뷰 소음도 함께 없앤다.
4. **프리뷰 계층은 무변경 소비 대상이다** — 룩 계층이 프리뷰를 우회하거나 억제하는 경로를 만들어서는 안 된다(REQ-021).

---

## §6. 조사 ⑤ — 안전 철학 (룩 적용이 계승해야 할 불변식)

- **단일 스크리닝 경로**: `SafetyGate.screen` `@MX:ANCHOR`(server/safety/gate.py:260-265) — "exactly ONE screening path may exist; a second entry would be a gate bypass by construction". run_commands가 번들 전체를 스크리닝(tools.py:326-333). **룩 인스턴스화 커맨드는 전부 이 경로를 경유해야 하며 제2 실행 경로는 구성상 금지**.
- **관찰 래퍼 — 프리뷰는 스크리닝을 감싼다 (감사 D5 보강)**: 채팅 세션 경로에서 게이트는 `_ObservingBundleGate`(`server/web/session.py:148-165`)로 감싸여 있고, 그 `screen()`은 `_on_preview(commands)` → `gate.screen(commands)` → `_on_decision(decision)` 순으로 실행한다. 즉 **스크리닝 전에 실행 프리뷰가, 후에 판정 이벤트가 발화**한다. 이 래퍼는 단일 스크리닝 경로 불변식을 깨지 않는다(게이트를 대체하지 않고 위임한다). 룩 계층은 이 래퍼도 무변경으로 소비한다 — 상세는 §5.5.
- **안전 비대칭**: "when in doubt, HOLD. Approval defaults to deny-all"(gate.py:17, approval.py:45 `DenyAllApprovalPort`).
- **분류 의미론 단일**: `classify_command` `@MX:ANCHOR`(classify.py:169). 개방형 타깃의 파괴적 커맨드 탐지(classify.py:95, REQ-MVP-036b). 블랙리스트: `Delete`/`Remove`/`Store /overwrite`(blacklist.yaml:15-18) — **점유 슬롯 덮어쓰기는 기본 경로가 될 수 없다**(승인 보류 유발).
- **LiveLock**: lock.py:23 + lock-FIRST 재확인(gate.py:318-321, REQ-MVP-035) — 라이브 잠금 중 제안 전용 강등. 룩 적용도 예외 없음.
- **감사**: clearance 토큰 1개당 송신 1회·감사 1:1(EXECBODY-001 AC-010 라이브 인수에서 audit_logs jsonl로 종단 확인된 계약).
- **초안→사람 확정 철학**: product.md §6 — AI는 초안 생성, 실행 버튼은 사람. 룩 적용의 UX도 기존 승인 카드/제안 카드 플로우를 그대로 소비한다.

---

## §7. 고려하고 기각한 대안

### 기각 (a) — 룩 데이터를 룰북 자산(고정 프리픽스)에 통째로 내장

- **내용**: `32_look_library.md` 같은 자산에 4장르 전체 룩을 산문/표로 내장, 매칭을 순수 프롬프트로만 해결.
- **기각 사유**: §2 함의 1-3 — 매 턴 반복 토큰 비용, 캐시 무효화 결합, 서버 코드(리졸버/번들 빌더)가 소비할 구조화 데이터가 LLM 산문에 갇힘, per-show 값 진입 금지 원칙과의 마찰(룩 자체는 정적이지만 확장·수정 주기가 룰북 버전 주기와 다름). 얇은 안내 축만 남긴다 — 이 형상은 §9.1에서 **하이브리드로 확정**되었다(plan.md §A.4a 결정 E).

### 기각 (b) — 매칭을 별도 임베딩/검색 인프라로 해결

- **내용**: 룩 설명문 임베딩 + 벡터 검색으로 무드 매칭.
- **기각 사유**: 신규 런타임 의존성 0 원칙(기존 SPEC 전통) 위반, 4장르 × ≤10룩 = 최대 40개 후보는 LLM 자체 판단(구조화 데이터 제시) 또는 키워드/별칭 매칭으로 충분한 규모. 과잉 설계.

### 기각 (c) — 인스턴스화를 신규 콘솔측 Lua 응답기 확장으로 해결

- **내용**: 응답기에 룩 전용 프로토콜 동사 추가.
- **기각 사유**: 인스턴스화는 이미 라이브 검증된 커맨드라인 패턴(§4)으로 전부 표현 가능 — 프로그래밍은 `run_commands`가 정석(룰북 31:5-7). 응답기 변경은 배포 왕복 비용(EXECBODY-001 M3 실측)을 수반하며 본 SPEC에 불필요. `copilot_responder.lua` 무변경 목표.

### 채택 — 서버측 구조화 룩 데이터 계층 + 기존 파이프라인 전면 재사용

- 룩 데이터는 신규 서버 패키지의 정적 자산(형식은 **YAML repo 자산으로 확정** — §9.1, plan.md §A.4a 결정 A), 역할→리그 매핑은 get_rig_context 형상 재사용(§3), 인스턴스화는 검증된 커맨드 패턴의 번들 생성 → 기존 게이트 경유(§4, §6), 매칭은 기존 채팅 파이프라인 + 툴 표면 확장(§5).

---

## §8. 핵심 참조 파일

| 파일 | 역할 |
|---|---|
| `server/rulebook/assembly.py` | 고정 프리픽스 단일 조립 경로(:73-76, ANCHOR :69-72), byte-stability 계약(:1-15) |
| `server/rulebook/assets/v2.4.2/31_choreography_patterns.md` | 라이브 검증된 프로그래밍 문법 전체 + 무드 폴백 절(:173-206) — 룩이 정밀화할 대상 |
| `server/rulebook/assets/v2.4.2/20_korean_terms.md` | **픽스처 타입 클래스** 사전(showfile 행 :11-16, :29) + "정적 어휘/런타임 구체값" 분리 원칙(:31-36). **포지션 역할 사전이 아니다** — v0.2.0 이 표는 "역할 어휘 클래스 사전"이라 적어 §3이 정정으로 뒤집은 바로 그 프레이밍을 유지하고 있었다(감사 D3, v0.3.0 정정). 본 SPEC에는 **명명 관례 스타일의 선례**(`Group named like 'Cyc'/'샤막'`)로만 기여하며 **무변경 PRESERVE 대상**이다 |
| `server/rulebook/assets/v2.4.2/00_grammar.md` | Store Group/Preset + Label 레시피(:66-68), dotted id 규칙(:32-34), **`Preset 4.1` = pool 4 "Color" 예시(:18)** — 결정 I의 근거이자 "예시 산문이지 계약이 아님"의 출처 |
| `server/rulebook/assets/v2.4.2/10_object_model.md` | **프리셋 = 속성 패밀리별 풀 조직 + `Preset <pool>.<slot>` 주소(:18-20)**, 패밀리 경계(:38-40 — Beam=iris/prism/frost, Focus=zoom/focus) — 결정 I(풀 범위)와 빔/Focus 라우팅의 근거 |
| `server/orchestrator/tools.py` | 툴 레지스트리(:23, :304), rig 경로/드릴다운/캡(:65-88), rig_object 실번호 계약(:185-211), 슬롯≠FID(:33-36) |
| `server/web/session.py` | 채팅 1턴 파이프라인(:354), build_toolset 소비(:210), `_last_created` 크로스턴 메모리(:202, 387-409) |
| `server/web/panel.py` | 서버측 **런타임 사용자 데이터** JSON 영속화 선례 `PinStore`(:186-330), user_data_dir 경로(:176), 재생 동사 표(:549) — **정적 규칙 데이터의 선례는 아님**(§7 채택 근거) |
| `server/web/preview.py` | **실행 프리뷰 계층**(감사 D5 보강) — 조립(:36), 커맨드별 경고 분류(:99-170), **스트로브/셔터 = `danger`(:131-139)**, Pan/Tilt = `caution`(:149-157), 덮어쓰기 = `caution`(:113-121), 등급 승격(:198) |
| `server/web/session.py` (프리뷰 배선) | `_ObservingBundleGate`(:148-165 — 프리뷰가 `gate.screen()`을 **감싼다**), 툴셋 주입(:213), 프리뷰 이벤트 발화(:236-244) |
| `server/tests/test_web_preview.py` | 스트로브 `danger` 분류의 테스트 핀(:39-43) — 우발 구현이 아니라 의도된 계약임의 증거 |
| `pyproject.toml` | PyYAML 런타임 의존 확인(:16 `pyyaml>=6.0.3`) — 저장 형식 결정(YAML)의 근거 |
| `server/safety/gate.py` | 단일 스크리닝 ANCHOR(:260-265), lock-FIRST(:318-321), deny-all 비대칭(:17) |
| `server/safety/classify.py` | 분류 의미론 ANCHOR(:169), 개방형 타깃 탐지(:95) |
| `server/safety/blacklist.yaml` | `Delete`/`Remove`/`Store /overwrite`(:15-18) — 충돌 처리의 경계 조건 |
| `server/safety/ruleset.py` | PyYAML 기존 의존 확인(:16, :63) — 저장 형식 결정의 제약 문맥 |
| `server/llm/factory.py`, `server/llm/config.py` | 제공자 스위치(:17-28) — 매칭 설계의 제공자 중립 제약 |
| `server/deploy/pipeline.py`, `server/deploy/pack.py` | 생성형 Lua 경로의 compile→scan→review 게이트(:5-12), 패키징(:60) |
| `server/deploy/settings.py` | `user_data_dir`(:184) — 런타임 데이터 위치 |
| `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` | P1-3 원문 권고 + P1-1/P1-2 공통 기반 요구(§3, §4) |
| `.moai/project/product.md` | Phase 2 목표(:38), 비목표(:44-46) |

---

## §9. 알려진 미결 지점 — **6건 → 3건 → 0건**

**v0.3.0 최종 상태: 미결 0건.** plan.md에 clarification 마커가 남아 있지 않고 design.md §5.2(열린 슬롯)도 해체되었다. 모든 결정은 plan.md §A.4a에 11건(A~K)으로 기록되어 있다.

### §9.1 해소된 것 (v0.1.0의 6건 중 5건 + 신설 1건 폐쇄 — v0.2.0 시점)

| v0.1.0 항목 | 해소 방법 |
|---|---|
| 1. 룩 저장 형식·위치 | **리포지토리 증거로 폐쇄** — YAML repo 자산. `blacklist.yaml`이 정적 규칙 데이터의 선례이고 PyYAML은 기존 의존(`pyproject.toml:16`). v0.1.0이 병렬 후보로 든 `PinStore` JSON은 **런타임 사용자 데이터**로 클래스가 다르다 — 이 구분을 놓친 것이 항목을 미결로 남긴 원인이었다(감사 D6b). |
| 2. 프리셋 풀 슬롯 배정 | **사용자 확정 ⑤** — 런타임 빈 슬롯 탐색. |
| 3. 인스턴스화 산출물 범위 | **사용자 확정 ⑥** — 프리셋만. |
| 4. 충돌 처리 | **사용자 확정 ⑦** — 건너뛰고 "N개 건너뜀" 보고. |
| 5. 매칭 표면 형상 | **문서 내 증거로 폐쇄** — 하이브리드. §2 결론 3이 이미 도출했고 plan.md v0.1.0이 "권고 기본값"으로 기록했다. 결론이 있는 항목이 미결로 남아 있었다(감사 D6b). |
| (신설) 빔 축 | **사용자 확정 ④** — v1 유지 + M0 프로브 게이트. 스트로브/셔터는 §5.5 프리뷰 근거로 기본 제외. |

### §9.2 v0.2.0의 남은 3건 → **v0.3.0에서 전부 폐쇄**

| v0.2.0 미결 | 폐쇄 경로 | 최종 결정 |
|---|---|---|
| 1. **역할 어휘 폐쇄 집합** — §3 정정으로 사전 근거 부재가 확인되어 신규 창작이 되었고 집합 구성이 실질 설계 결정으로 무거워졌다. *v0.1.0에서는 design.md 슬롯 F로만 존재하고 마커가 없어 Kickoff 게이트를 통과했다(감사 D6a).* | **사용자 확정 ⑨** | 6종(백라이트/프론트/사이드/탑/배경/스페셜) + **6종 전부의** 매핑 힌트 문자열. 정본 표는 spec.md §A, 근거는 plan.md §A.4a-J. 힌트에서 픽스처 타입 클래스 어휘 배제(§3 기여) |
| 2. **다이내믹스 단계 척도** — REQ-005의 "범위 이탈" 검증과 AC-002의 "최저~최고 스팬" 판정이 이 척도 없이는 평가 불가다(감사 D8c). *v0.1.0에서는 아무 데도 기록되지 않은 채 정의만 비어 있었다.* | **엔지니어링 판단** | 정수 1~5, `1 <= level <= 5`, 스팬 `{1,2}`≥1 ∧ `{4,5}`≥1. 실수 0.0~1.0 명시 기각(임계값이라는 새 미결을 만든다). plan.md §A.4a-H |
| 3. **역할 매핑 확정 UX** — 자동 휴리스틱+보고 vs 적용 전 사용자 확인. 감사가 지적하지 않은, 진짜로 열린 트레이드오프. | **사용자 확정 ⑩** | 자동 휴리스틱 + 적용 전 요약 보고(확인 왕복 없음). **반대 논거는 기각이 아니라 design.md §4 위험 #1의 수용된 잔여 위험으로 존치.** plan.md §A.4a-K |

### §9.3 v0.3.0에서 새로 닫은 것 (미결이 아니었으나 결정도 아니었던 항목)

- **프리셋 풀 범위 + "N개 건너뜀"의 단위** — 이 항목은 v0.2.0에서 **마커도 아니고 결정도 아닌 채** `<pool>` 플레이스홀더로만 여섯 아티팩트에 흩어져 있었다. §4의 조사(프리셋 = 속성 패밀리별 풀)가 이미 답의 재료를 갖고 있었으나 그 귀결이 기록되지 않아, 번들 형상·스킵 단위·ASSUMPTION-14의 실측 대상·요약 보고 형상이 함께 미정으로 남았다. **plan.md §A.4a 결정 I로 폐쇄** — 이 조사 문서에는 §4에 그 근거를 보강했다.
- 교훈: **미해결 마커로 표시되지 않은 미결이 마커로 표시된 미결보다 위험하다.** 마커는 게이트에서 세어지지만, 플레이스홀더는 세어지지 않은 채 하류로 번진다(design.md §4 위험 #11).

---

## §10. P1-1 / P1-2와의 관계 (소비자 예약 — 번들하지 않음)

P1-1(송 구조 큐리스트 생성기)과 P1-2(버스킹 준비 마법사)는 본 SPEC의 룩 스키마를 소비할 미래 SPEC이다(제안서 §3 — "P1-1·P1-2가 모두 이 어휘 위에서 돌아가므로 공통 기반"). 본 SPEC은 이들을 **번들하지 않되**, 스키마 설계 시 두 소비자의 알려진 요구를 반영한다: (a) P1-1은 섹션 다이내믹스 축(Intro/Verse/Chorus 에너지 레벨 → 룩 선택)을 필요로 하므로 룩의 다이내믹스 레벨은 순서 있는 값이어야 하고, (b) P1-2는 장르 단위 일괄 인스턴스화(팔레트 생성)를 필요로 하므로 인스턴스화 API는 룩 1개 단위와 장르 묶음 단위를 모두 표현할 수 있는 형상이어야 한다. 이 두 요구는 스키마 요구사항(REQ-LOOKLIB-001/002)에 반영되며, 그 이상의 P1-1/P1-2 기능은 §D 제외 범위다.

**무브먼트 필드와 소비 계약의 관계 (v0.3.1 — F3).** v0.3.1은 v1 내장 라이브러리가 무브먼트(페이저) 지정을 담는 것을 금지했다(REQ-003 신설 절 / AC-003 구간 6). **이것은 위 두 소비 계약을 깨지 않는다** — 위에서 명시했듯 P1-1이 소비하는 것은 **순서 있는 다이내믹스 축**이고 P1-2가 소비하는 것은 **장르 묶음 인스턴스화 API 형상**이며, 둘 중 어느 것도 무브먼트 필드가 아니다. 무브먼트는 REQ-LOOKLIB-001이 정의하는 **선택적** 축이고, v0.3.1 이후에도 **스키마 필드로 정의된 채 유지**된다(AC-003 구간 6 (ii)가 필드의 존재와 왕복 가능성을 별도로 assert하므로, "필드가 삭제되었다"와 "v1이 값을 넣지 않는다"가 기계적으로 구분된다). 따라서 P1-1/P1-2 또는 별도 후속 SPEC이 무브먼트를 실제로 저작·발화하기 시작할 때 **스키마 변경 없이** 켤 수 있다 — 바꿔야 하는 것은 라이브러리 자산과 번들 빌더이지 소비 계약이 아니다.
