# SPEC-COPILOT-LOOKLIB-001 — Plan-Phase Research

status: draft (v0.1.0, 2026-07-26). 본 문서는 룩 라이브러리(연출 어휘 계층)가 얹힐 기존 코드베이스를 file:line 근거로 분석한다. **구현 코드는 제안하지 않는다 — 분석 전용.** 라이브 콘솔 조사는 이번 plan-phase 세션에서 수행하지 않았다(기존 SPEC들의 라이브 검증 결과와 룰북의 "validated live" 표기를 재사용한다).

---

## §1. 출처 — 제안서 P1-3 + 로드맵 Phase 2 + 사용자 사전 확정

- **제안서**: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 P1-3(82-86행) — "웅장한 금색 코러스" 같은 추상 지시를 **앵글·컬러·강도·무브먼트 조합의 '룩'**으로 변환하는 디자인 지식 레이어. 장르별(록/발라드/워십/EDM) 룩 템플릿 내장 + 사용자 리그에 맞는 인스턴스화. **P1-1(송 구조 큐리스트 생성기)·P1-2(버스킹 마법사)가 모두 이 어휘 위에서 돌아가는 공통 기반**(86행, §4 결론 118-119행).
- **로드맵 정합**: `.moai/project/product.md` §5 Phase 2(38행) — "'코러스에서 금색 톤으로 웅장하게' 수준의 추상 지시를 리그에 맞게 실행"이 Phase 2 성공 기준. 본 SPEC은 그 목표의 실체화다. §6 비목표(44-45행) — 미적 최종 판단은 사람, 라이브 자율 운영 배제 — 는 본 SPEC이 그대로 계승한다.
- **사용자 사전 확정 3건**(이번 세션, 재질의 금지 — spec.md §A에 전문 수록): ① v1 룩 속성 = 컬러/강도/빔 구체값 + **포지션은 역할 추상**(백라이트·FOH 워시·사이드 등, 인스턴스화 시점 리그 그룹 매핑 — 하드 pan/tilt 아님), ② v1 장르 = 워십/록/발라드/EDM 4종 × 장르당 약 6~10 룩(잔잔함→클라이맥스 섹션 다이내믹스 스팬), ③ v1 범위 = 데이터 계층 + MA3 인스턴스화 + **자연어 매칭까지 전부** — 완결된 사용자 기능이지 데이터 계층만이 아니다.

---

## §2. 조사 ① — 룰북 시스템 (룩이 살 곳의 첫 번째 후보)

### 실측 구조

- 룰북은 **고정(FIXED) 시스템 프롬프트 프리픽스**다: `server/rulebook/assembly.py:1-15` docstring — "assembled from static markdown assets under `assets/v<version>/` in sorted filename order — nothing else. No timestamps, session IDs, or any per-turn variable value may enter this string". 제공자 캐시(Anthropic prompt caching / Gemini context caching, REQ-MVP-041)가 이 문자열을 **바이트 단위로** 캐싱하며, 1바이트 변경이 전체 캐시를 무효화한다(AC-MVP-014가 byte identity를 핀).
- 조립 경로는 **정확히 하나**: `assemble_prefix()`(assembly.py:73-76), `@MX:ANCHOR`(assembly.py:69-72) — "the fixed system-prompt prefix is built ONLY here". 소비 지점: `server/web/serve.py:284`(서버 기동 시 1회), measurement 러너(`server/measurement/runner.py:276,336,392`).
- 자산: `server/rulebook/assets/v2.4.2/` 5파일 — `00_grammar.md`(128행), `10_object_model.md`(40행), `20_korean_terms.md`(36행), `30_plugin_patterns.md`(63행), `31_choreography_patterns.md`(206행). 파일명 정렬 순서로 이어붙임(assembly.py:61-66). 버전은 `RULEBOOK_VERSION = "2.4.2"`로 핀(assembly.py:25).
- `20_korean_terms.md`의 마감 규칙(31-36행): "this dictionary is part of the FIXED prompt prefix — **it never contains per-show or per-turn values**. Showfile-dependent rows name a vocabulary CLASS; the concrete group and preset ids come from `get_rig_context` at run time." — **정적 어휘 클래스는 룰북에, 쇼파일 구체값은 런타임 조회로**라는 이 프로젝트의 확립된 분리 원칙.

### 룩 저장 위치 결정에 주는 함의 (설계 입력 — plan.md §A.4 마커 ①/⑤의 제약 문맥)

1. **룩 데이터를 룰북 자산에 통째로 넣을 수 없다.** 4장르 × 6~10룩 × (컬러/강도/빔/역할/무드 키워드) 구조화 데이터는 (a) 매 턴 토큰 비용이 반복 발생하는 고정 프리픽스를 크게 불리고, (b) 룩 데이터 수정 때마다 프리픽스 바이트가 바뀌어 캐시가 무효화되며, (c) 무엇보다 서버 코드(매칭·인스턴스화 로직)가 소비할 **구조화 데이터**인데 룰북은 LLM 전용 산문이다.
2. **반면 `20_korean_terms.md` 선례는 "정적 어휘 안내 축"이 룰북에 사는 것이 자연스러움을 보여준다** — 룩 시스템의 존재·사용법("추상 무드 지시가 오면 룩 라이브러리를 먼저 조회하라" 류)을 안내하는 **얇은 정적 축**은 룰북 확장 후보다. `31_choreography_patterns.md:173-206`의 기존 "Concept / mood instructions" 절(무드→디자인 시작점 표)이 바로 그 자리에 이미 있고, 룩 라이브러리는 이 절의 조악한 4행 무드 표를 대체·정밀화하는 관계다.
3. **결론(권고)**: 구조화 룩 데이터는 **서버측 별도 데이터 계층**(신규 패키지)이 단일 진실원, 룰북에는 (필요 시) 얇은 정적 안내 축만. 최종 형상(안내 축을 넣을지, 기존 31 무드 절과의 관계)은 plan.md §A.4 마커로 이연.

---

## §3. 조사 ② — get_rig_context (역할→리그 매핑의 데이터원)

- **10 조회 경로**: `DEFAULT_RIG_CONTEXT_PATHS`(server/orchestrator/tools.py:65-76) — fixture_types / fixtures(`Patch/Stages/1/Fixtures`) / **groups(`DataPool/Groups`)** / sequences / **preset_pools(`DataPool/PresetPools`)** / macros / plugins / pages / matricks / worlds. 전 경로 2026-07-22 라이브 onPC 2.4.2에서 판독 확인 후 기본값 승격(tools.py:53-55 — "Guessed paths are how 'Patch/Fixtures' and 'DataPool/Presets' shipped dead for the whole of Stage 1" — **경로 추측 금지 교훈**).
- **드릴다운**: `DEFAULT_RIG_DRILLDOWN = ("preset_pools", "pages")`(tools.py:81) + 쿼리 상한 `RIG_DRILLDOWN_QUERY_CAP = 16`(tools.py:88) — 프리셋 풀은 "풀 존재"와 "풀 안에 뭔가 저장됨"이 다른 답이라 한 층 더 연다(tools.py:38-44). 상한 초과 시 `drilldown_capped` 명시(부분 워크를 완전한 것처럼 제시 금지).
- **실패 사유 이분**: `path_not_resolved`(설정 결함) vs `console_unreachable`(운영 조건) — tools.py:104-105, 병합 금지(REQ-SHOWUI-002가 이미 소비).
- **키잉 계약**: `rig_object`(tools.py:185-211) — 실제 풀 번호 `no` 노출, 배열 인덱스 아님. 그룹/프리셋 풀은 그 `no`가 곧 발화 번호(`Group <no>`). 슬롯을 확정 못 한 자식은 `no` 없이 이름만 도착(성능 저하가 아니라 의미 있는 신호).
- **슬롯≠FID gotcha**: fixtures 섹션의 번호는 스테이지 패치 슬롯이지 FID가 아니다(tools.py:33-36, 20_korean_terms.md 마감 규칙, 룰북 31:184-189). **역할 매핑은 그룹을 우선해야 하는 구조적 이유** — 룰북 31:186 "Prefer a group".
- **역할 매핑에 쓸 실질 데이터**: groups 섹션의 `{no, name}` 목록. `20_korean_terms.md`의 showfile 행들(샤막/워시/무빙/스팟/빔/객석등…)이 "Group named like 'Wash'/'워시'" 식 **이름 관례 기반 매핑**을 이미 확립된 어휘 클래스로 정의해 뒀다 — 역할→그룹 휴리스틱의 사전(dictionary) 기반이 이미 존재한다.
- **공유 헬퍼는 public**: `rig_object`/`rig_section`/`drill_into`(tools.py:168-177 주석) — 패널 카탈로그(panel.py)가 이미 두 번째 소비자다. 룩 리졸버가 세 번째 소비자가 되는 것이 의도된 재사용 형상.

---

## §4. 조사 ③ — 프리셋/그룹/큐 생성의 라이브 검증된 커맨드 패턴

- **프로그래밍 목적지 규칙**(라이브 검증): 모든 프로그래밍 번들 선두에 `ChangeDestination Root` 정확히 1회 — 룰북 `31_choreography_patterns.md:9-23`. 패치의 정반대 규칙(패치 플러그인은 ChangeDestination 금지 — 30_plugin_patterns). 이 규칙 위반이 "Illegal object"의 주 원인.
- **선택**(검증): bare `Fixture 11 Thru 19` / `Group 11` — `Select Fixture`/`SelFix` 금지(31:25-31).
- **값 설정**(검증): `Attribute 'Dimmer' At 80`, `'ColorRGB_R/G/B'` 0-100, `'Pan'/'Tilt'` 퍼센트, `;` 체인(31:33-39). **`ClearAll` 규율**: 새 룩 캡처 전 + 매 `Store` 후 — 프로그래머 잔류값이 다음 캡처로 TRACK되어 조용히 오염(31:40-41, 128-134 트래킹 모델).
- **프리셋/그룹 저장 레시피**: `Fixture ... Thru ...` → `Store Group 7` → `Label Group 7 'Vocals'`(00_grammar.md:66); 값 설정 후 `Store Preset 4.2` → `Label Preset 4.2 'Warm Wash'`(00_grammar.md:67-68). 프리셋 주소는 `Preset <pool>.<slot>`(10_object_model.md:20, pool 4 = "Color" 예시 00_grammar.md:18). 풀별 실제 번호·슬롯 점유는 쇼파일 종속 — get_rig_context preset_pools 드릴다운이 런타임에 답한다.
- **룩→큐 저장**(검증): `Store Sequence 11 Cue 1 'Warm Wash' CueFade 2`, 시퀀스는 첫 store에서 자동 생성, `/Merge` 추가·**`/Overwrite`는 파괴적 → 안전 게이트가 사람 승인으로 라우팅**(31:43-59).
- **페이저/MAtricks**(검증): Phase 0 Thru 360 팬, Speed, Step, MAtricks Set/Reset(31:61-94) — 룩의 "무브먼트" 속성이 쓸 수 있는 검증된 표면.
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

---

## §6. 조사 ⑤ — 안전 철학 (룩 적용이 계승해야 할 불변식)

- **단일 스크리닝 경로**: `SafetyGate.screen` `@MX:ANCHOR`(server/safety/gate.py:260-265) — "exactly ONE screening path may exist; a second entry would be a gate bypass by construction". run_commands가 번들 전체를 스크리닝(tools.py:326-333). **룩 인스턴스화 커맨드는 전부 이 경로를 경유해야 하며 제2 실행 경로는 구성상 금지**.
- **안전 비대칭**: "when in doubt, HOLD. Approval defaults to deny-all"(gate.py:17, approval.py:45 `DenyAllApprovalPort`).
- **분류 의미론 단일**: `classify_command` `@MX:ANCHOR`(classify.py:169). 개방형 타깃의 파괴적 커맨드 탐지(classify.py:95, REQ-MVP-036b). 블랙리스트: `Delete`/`Remove`/`Store /overwrite`(blacklist.yaml:15-18) — **점유 슬롯 덮어쓰기는 기본 경로가 될 수 없다**(승인 보류 유발).
- **LiveLock**: lock.py:23 + lock-FIRST 재확인(gate.py:318-321, REQ-MVP-035) — 라이브 잠금 중 제안 전용 강등. 룩 적용도 예외 없음.
- **감사**: clearance 토큰 1개당 송신 1회·감사 1:1(EXECBODY-001 AC-010 라이브 인수에서 audit_logs jsonl로 종단 확인된 계약).
- **초안→사람 확정 철학**: product.md §6 — AI는 초안 생성, 실행 버튼은 사람. 룩 적용의 UX도 기존 승인 카드/제안 카드 플로우를 그대로 소비한다.

---

## §7. 고려하고 기각한 대안

### 기각 (a) — 룩 데이터를 룰북 자산(고정 프리픽스)에 통째로 내장

- **내용**: `32_look_library.md` 같은 자산에 4장르 전체 룩을 산문/표로 내장, 매칭을 순수 프롬프트로만 해결.
- **기각 사유**: §2 함의 1-3 — 매 턴 반복 토큰 비용, 캐시 무효화 결합, 서버 코드(리졸버/번들 빌더)가 소비할 구조화 데이터가 LLM 산문에 갇힘, per-show 값 진입 금지 원칙과의 마찰(룩 자체는 정적이지만 확장·수정 주기가 룰북 버전 주기와 다름). 얇은 안내 축 후보만 남긴다(plan.md §A.4 ⑤).

### 기각 (b) — 매칭을 별도 임베딩/검색 인프라로 해결

- **내용**: 룩 설명문 임베딩 + 벡터 검색으로 무드 매칭.
- **기각 사유**: 신규 런타임 의존성 0 원칙(기존 SPEC 전통) 위반, 4장르 × ≤10룩 = 최대 40개 후보는 LLM 자체 판단(구조화 데이터 제시) 또는 키워드/별칭 매칭으로 충분한 규모. 과잉 설계.

### 기각 (c) — 인스턴스화를 신규 콘솔측 Lua 응답기 확장으로 해결

- **내용**: 응답기에 룩 전용 프로토콜 동사 추가.
- **기각 사유**: 인스턴스화는 이미 라이브 검증된 커맨드라인 패턴(§4)으로 전부 표현 가능 — 프로그래밍은 `run_commands`가 정석(룰북 31:5-7). 응답기 변경은 배포 왕복 비용(EXECBODY-001 M3 실측)을 수반하며 본 SPEC에 불필요. `copilot_responder.lua` 무변경 목표.

### 채택 — 서버측 구조화 룩 데이터 계층 + 기존 파이프라인 전면 재사용

- 룩 데이터는 신규 서버 패키지의 정적 자산(형식은 plan.md §A.4 ①), 역할→리그 매핑은 get_rig_context 형상 재사용(§3), 인스턴스화는 검증된 커맨드 패턴의 번들 생성 → 기존 게이트 경유(§4, §6), 매칭은 기존 채팅 파이프라인 + 툴 표면 확장(§5).

---

## §8. 핵심 참조 파일

| 파일 | 역할 |
|---|---|
| `server/rulebook/assembly.py` | 고정 프리픽스 단일 조립 경로(:73-76, ANCHOR :69-72), byte-stability 계약(:1-15) |
| `server/rulebook/assets/v2.4.2/31_choreography_patterns.md` | 라이브 검증된 프로그래밍 문법 전체 + 무드 폴백 절(:173-206) — 룩이 정밀화할 대상 |
| `server/rulebook/assets/v2.4.2/20_korean_terms.md` | 역할 어휘 클래스 사전(showfile 행) + "정적 어휘/런타임 구체값" 분리 원칙(:31-36) |
| `server/rulebook/assets/v2.4.2/00_grammar.md` | Store Group/Preset + Label 레시피(:66-68), dotted id 규칙(:32-34) |
| `server/orchestrator/tools.py` | 툴 레지스트리(:23, :304), rig 경로/드릴다운/캡(:65-88), rig_object 실번호 계약(:185-211), 슬롯≠FID(:33-36) |
| `server/web/session.py` | 채팅 1턴 파이프라인(:354), build_toolset 소비(:210), `_last_created` 크로스턴 메모리(:202, 387-409) |
| `server/web/panel.py` | 서버측 JSON 영속화 선례 `PinStore`(:186-330), user_data_dir 경로(:176), 재생 동사 표(:549) |
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

## §9. 알려진 미결 지점 (→ plan.md §A.4 [NEEDS CLARIFICATION] 마커)

1. **룩 저장 형식·위치** — YAML(blacklist.yaml 선례, 주석 가능, PyYAML 기존 의존) vs JSON(PinStore/stdlib 선례). repo-shipped 정적 템플릿 + (v1 범위 밖이지만 스키마가 열어둘) 사용자 확장의 이원 구조.
2. **프리셋 풀 슬롯 할당 전략** — 고정 예약 대역 vs 빈 슬롯 런타임 탐색 vs 설정값. 드릴다운 캡(16쿼리)과 풀별 번호가 쇼파일 종속이라는 사실이 제약.
3. **인스턴스화 산출물 범위** — 프리셋만 vs 프리셋+데모 시퀀스(+익스큐터 바인딩). 산출물이 커질수록 blast radius와 승인 마찰 증가.
4. **기존 사용자 프리셋과의 충돌 처리** — 스킵/재슬롯/명시적 승인 경유 덮어쓰기. `Store /overwrite` 블랙리스트(§6)가 기본값을 규정.
5. **매칭 표면 형상** — 신규 툴(라이브러리 조회) vs 얇은 룰북 안내 축 vs 하이브리드. 고정 프리픽스 byte-stability·토큰 예산·제공자 중립이 제약.
6. **역할 매핑 확정 UX** — 자동 휴리스틱+결과 보고 vs 적용 전 사용자 확인 단계. "사람이 확정" 철학과 지시→실행 왕복 마찰의 트레이드오프.

---

## §10. P1-1 / P1-2와의 관계 (소비자 예약 — 번들하지 않음)

P1-1(송 구조 큐리스트 생성기)과 P1-2(버스킹 준비 마법사)는 본 SPEC의 룩 스키마를 소비할 미래 SPEC이다(제안서 §3 — "P1-1·P1-2가 모두 이 어휘 위에서 돌아가므로 공통 기반"). 본 SPEC은 이들을 **번들하지 않되**, 스키마 설계 시 두 소비자의 알려진 요구를 반영한다: (a) P1-1은 섹션 다이내믹스 축(Intro/Verse/Chorus 에너지 레벨 → 룩 선택)을 필요로 하므로 룩의 다이내믹스 레벨은 순서 있는 값이어야 하고, (b) P1-2는 장르 단위 일괄 인스턴스화(팔레트 생성)를 필요로 하므로 인스턴스화 API는 룩 1개 단위와 장르 묶음 단위를 모두 표현할 수 있는 형상이어야 한다. 이 두 요구는 스키마 요구사항(REQ-LOOKLIB-001/002)에 반영되며, 그 이상의 P1-1/P1-2 기능은 §D 제외 범위다.
