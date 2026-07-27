# SPEC-COPILOT-BUSKWIZ-001 — Plan-Phase Research

status: draft (v0.1.3, 2026-07-27). 본 문서는 버스킹 준비 마법사(N개 룩 조율 계층)가 얹힐 기존 코드베이스를 file:line 근거로 분석한다. **구현 코드는 제안하지 않는다 — 분석 전용.** **라이브 조사 수행 여부: 없음** — 실물 콘솔 세션은 M0(ASSUMPTION-16/17/18/19)와 M7(종단)의 2회로 계획되어 있고(사용자 확정 ④), 본 plan-phase는 리포지토리 실측과 출하된 라이브러리·코드에 대한 **인메모리 실측**만 수행했다. 인메모리 실측 7건(§2 라이브러리 계수 / §3 슬롯 비전진 재현 / §4 번들 규모·경계접기 / §4 캡처 형상 값 라인 충돌 / §5 프리셋-익스큐터 문법 0건 전수 / §6 `(룩, 역할)` 쌍 괴리 / §9.4 슬롯 상한 부재)은 그 사실을 각 지점에 명시한다.

> **참조 규약 (v0.1.3부터)**: 정본(spec.md · acceptance.md)은 **줄번호로 인용하지 않는다** — `REQ-BUSKWIZ-nnn` · `AC-BUSKWIZ-nnn` · `ASSUMPTION-nn` · 절 제목 · 명명된 하위 절 같은 **안정 토큰**만 쓴다. 토큰은 개정을 견디고, 가리키는 내용이 사라지면 **토큰도 함께 사라져 즉시 드러난다**. 반면 줄번호는 조용히 옆 문장을 가리킨다. `파일:줄`은 **코드·룰북·타 SPEC 아티팩트**에만 유지한다 — 그쪽은 커밋 없이 움직이지 않고 달리 쓸 안정 식별자가 없다.

> **v0.1.3 — 독립 plan-audit(FAIL 0.78) 후속 정본 v0.1.3 반영.** 조사 결론·기각 대안·실측치는 **무변경**이다. 세 가지를 고쳤다.
>
> - **(a) 정본 줄 앵커 전면 폐기.** 감사가 형제→SSOT 줄 앵커 52개 중 10개가 빈 줄, 6개 이상이 다른 내용을 가리킨다고 지적했다. 본 문서의 정본 앵커 **29개소를 안정 토큰으로 전면 교체**했다(위 참조 규약). v0.1.1에서 두 번, v0.1.2에서 한 번 재접지했던 바로 그 비용이 사라진다 — **재접지를 잘하는 것이 아니라 재접지가 필요 없게 만드는 것이 답이었다.**
> - **(b) "슬롯 소진"을 근거로 쓰던 2개소 교체 (감사 D2).** REQ-BUSKWIZ-010의 옛 트리거 "슬롯이 부족해"는 **도달 불가**다 — 본 문서가 재확인했다: `_first_free_slot`(`server/looks/instantiate.py:307-312`)은 `slot = 1`에서 시작해 상한 없이 증가하므로 **항상 슬롯을 반환**하고, 풀 용량 상수는 `server/`·`console/` 전체에서 **0건**(`max_slot`/`pool_size`/`POOL_CAPACITY`/`MAX_SLOT`/`slot_limit`/`SLOT_MAX`)이며, `_observed_contents`(`:193-214`)는 점유된 자식의 슬롯·라벨만 반환할 뿐 **풀 크기를 보고하지 않는다**. 런타임에도 상한을 알 방법이 없다.
> - **(c) PRESERVE에 `instantiate.py`가 들어오면서 §7(b)의 "정직한 단서"가 뒤집혔다.** v0.1.2까지 본 문서는 "이 파일은 PRESERVE 목록에 없으니 이 기각은 PRESERVE 논거가 아니다"라고 적었는데, 정본 v0.1.3이 이 파일을 목록에 넣었다. **논거를 바꿀 필요는 없고 오히려 강해졌다** — §7(b)의 세 실질 사유는 그대로이고, 정본이 그 결론을 diff로 기계 강제하는 장치를 얹었기 때문이다. 해당 항목을 그렇게 다시 썼다.
>
> **v0.1.2 — 정본 v0.1.2(ASSUMPTION-19 신설) 반영.** 조사 결론·기각 대안은 **무변경**이고, §5에 근거 행 2개와 함의 1개, §9에 **§9.4**를 추가했다.
>
> - **결함의 성격**: v0.1.1까지 REQ-BUSKWIZ-016은 ASSUMPTION-16 ∧ 17이 GO면 익스큐터 레이아웃을 만들도록 쓰여 있었는데, 라이브 검증된 유일한 바인딩 커맨드의 **목적어가 시퀀스**이고(`31_choreography_patterns.md:99`) 본 SPEC의 산출물은 **프리셋**이며 §D가 시퀀스 생성을 닫아 두었다 — **게이트가 열려도 얹을 대상이 없었다.** 정본이 ASSUMPTION-19를 신설해 게이트를 3항 논리곱으로 바꿨다(REQ-BUSKWIZ-016과 그 하위 절, 전제 본문 ASSUMPTION-19).
> - **본 문서의 몫**: §5의 3분류 표가 **주소형**만 축으로 세우고 **목적어 타입**을 묻지 않아 이 불일치가 어느 칸에도 들어가지 않았다. 축을 하나 추가해 시정했다(§9.4에 경위 기록).
> - **독립 재확인**: `Assign Preset` · `Store Executor` · `Label Executor` · `Preset <p>.<s> At …` 전부 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/`에서 **0개 파일**이고, 리포지토리의 **모든** `At Executor` 목적어가 예외 없이 `Sequence`다. 룰북의 프리셋 동사 4종은 전부 프로그래머 쪽이며(`00_grammar.md:59`·`:67`·`:68`·`:72`), 룰북 자신이 "프리셋을 발사하려면 **큐로 되불러라**"라고 답한다(`31_choreography_patterns.md:225-227`) — 그 경로가 곧 §D가 닫은 시퀀스 생성이다. **ASSUMPTION-19의 기본 기대값은 부정(DESCOPE)이다.**
>
> **v0.1.1 — 정본(spec.md · acceptance.md) v0.1.1 동기화.** 조사 결론·기각 대안·참조 표는 **무변경**이다. 네 가지를 반영한다.
>
> - **(a) §9.3의 3항목이 전부 정본에 채택되었다.** 번들 규모 실측 → `spec.md §A "번들 규모의 실측"`, stop-on-first-failure → REQ-BUSKWIZ-013의 보고 요소 **(e) 신설**, 미매핑 사유 인용 세분화 → `REQ-BUSKWIZ-013 하위 절((b)의 사유 5종)`, 코드 앵커 드리프트 → REQ-BUSKWIZ-007(`blacklist.yaml:18`)·REQ-BUSKWIZ-008(`tools.py:77-79`). 따라서 §9.3의 제목과 항목을 "본 문서가 닫는다"에서 **"본 문서가 열었고 정본이 받았다"**로 고쳐 적는다 — 열린 채로 남았다고 오독되면 run-phase가 같은 조사를 반복한다.
> - **(b) spec.md·acceptance.md 앵커를 전수 재접지했다.** v0.1.1이 §A에 실측 절을 신설하고 AC-BUSKWIZ-008에 구간을 추가하며 이후 줄이 밀렸다. **v0.1.3에서 이 항목은 무의미해졌다** — 정본 줄 앵커를 전부 안정 토큰으로 바꿨으므로 다음 개정에는 재접지할 대상이 없다. 이 줄은 "세 번 재접지한 뒤에야 앵커 방식 자체를 바꿨다"는 이력으로만 남긴다.
> - **(c) 하한 51 vs 57은 서로 다른 형상을 잰 수다.** 정본의 51은 룩 경계의 인접 `ClearAll`을 1회로 접은 뒤의 최소치(ballad · Dimmer+Color)이고, 본 문서의 57은 출하 `_bundle`을 그대로 이어붙인(접기 없음) 같은 시나리오의 실측치다. §4 표에 **경계 접기 열을 신설**해 두 수를 함께 싣는다 — 상한 87은 양쪽 모두 접기 없는 최악값이라 동일하다.
> - **(d) CAPTURE_PER_FAMILY는 "규모 레버"에서 "닫힌 경로"로 바뀌었다.** `REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)`이 `shared_capture` 고정 + 모델 인자 미노출로 확정했고, 그 근거는 규모가 아니라 **조용한 오염**이다. 본 문서가 이를 교차 확인했다(§4) — 근거가 규모였다면 v0.1.0의 §4 함의 3이 유효했겠지만, 실제 근거는 다른 축이므로 함의 3을 그 축으로 다시 썼다.
>
> **v0.1.0 — 최초 작성.** 선행 SPEC `SPEC-COPILOT-LOOKLIB-001`(completed)의 research.md 구조를 계승하되, 조사 대상은 정반대 방향이다 — LOOKLIB은 "룩 계층이 살 곳"을 찾았고, 본 문서는 **이미 출하된 룩 계층이 다중 룩 조율에 어떤 접합면과 결함을 남겼는지**를 찾는다. 세 가지가 실질 기여였다: (a) **§3의 슬롯 비전진을 코드 읽기가 아니라 실행으로 재현** — 워십 8룩 × 2풀 = 16건의 계획된 저장이 **서로 다른 목적지 2개**만 겨냥한다. (b) **§4의 번들 규모를 실측** — 당시 정본의 "약 40여 커맨드"는 쌍(pair) 수에서 나온 추정치였고 실제 행 수는 훨씬 크다(정본 v0.1.1이 이를 `spec.md §A "번들 규모의 실측"`으로 받았고, 추정치의 출처는 `spec.md §A "수용된 잔여 위험"`에 이력으로 남아 있다). (c) **§5의 3분류 표를 룰북 원문을 열어 작성** — 라이브 검증을 선언하는 룰북 파일은 `31_choreography_patterns.md:7` 하나뿐임을 전수로 확인했고, 페이지 **저작** 문법은 룰북 전체에서 0건임을 grep으로 확정했다.

---

## §1. 출처 — 제안서 P1-2 + 로드맵 + 선행 SPEC 예약 조항 + 사용자 사전 확정 4건

- **제안서**: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 **P1-2**(`:76-80`) — "리그 컨텍스트(이미 구현됨)를 읽어 '이 리그로 버스킹 준비해줘' 한 마디에 **컬러/포지션/빔 프리셋 팔레트 + 장르별 익스큐터 페이지 레이아웃**을 일괄 생성한다"(`:78-79`). 근거로 든 것은 "버스킹 실무의 성패가 사전 준비물 품질에 달려 있고, '큐 작성 전 프리셋 구축'이 최대 시간 소모처"라는 조사 결과다(`:79-80`).
- **공통 기반 관계**: 같은 제안서 `:86` — "P1-1·P1-2가 모두 이 어휘 위에서 돌아가므로 공통 기반이 된다"(P1-3 = 룩 라이브러리). 즉 본 SPEC은 **P1-3의 첫 번째 실행 소비자**이지 병렬 기능이 아니다.
- **로드맵 정합 (3중 표기 — spec.md §서두가 정본)**: "버스킹"이 등재된 유일한 로드맵 행은 **Phase 4**(`.moai/project/product.md:40` "버스킹 팔레트 추천")이고 그 행의 성공 기준은 문자 그대로 **"미정(TBD) — DESIGN.md에 정량 기준 없음"**이다 — 충족 여부를 판정할 수 없다. 본 SPEC이 실제로 충족하는 성공 기준은 **Phase 2**(`product.md:38`)의 "'코러스에서 금색 톤으로 웅장하게' 수준의 추상 지시를 리그에 맞게 실행"이며, 같은 행 목표 열의 **"프리셋 어휘 온보딩 마법사"**가 본 SPEC의 마법사와 직접 대응한다. 소비 자산인 "장르별 룩 템플릿"은 **Phase 3** 목표 열(`product.md:39`) 소속이나 LOOKLIB이 선착지시켰다.
- **비목표 계승**: `product.md:44` "라이브 실시간 자율 운영 배제 — 라이브 잠금 모드에서는 read-only + 제안 카드만 생성", `:45` "미적 최종 판단은 사람의 몫". 전자가 REQ-BUSKWIZ-014(LiveLock 제안 강등)의 로드맵측 근거다.
- **선행 SPEC의 예약 조항 3곳 (본 SPEC의 직접 발주서)**:
  - `SPEC-COPILOT-LOOKLIB-001/spec.md:70` — "인스턴스화 **API 형상**은 룩 단위/장르 묶음 단위 모두 표현 가능하게 설계한다. 단 **장르 묶음 인스턴스화의 런타임 실행은 v1 범위 밖**이다 — v1은 스키마 형상만 예약한다."
  - 같은 파일 `:180-182` Out of Scope 절 — "'이 리그로 버스킹 준비해줘' 일괄 팔레트 + 익스큐터 페이지 레이아웃 생성. **장르 묶음 인스턴스화는 스키마의 API 형상만 예약하고 런타임 실행은 만들지 않는다**(REQ-LOOKLIB-010, 감사 D7). 마법사 UX·페이지 레이아웃도 별도 SPEC."
  - `SPEC-COPILOT-LOOKLIB-001/research.md:226` — 소비 계약 원문. "**(b) P1-2는 장르 단위 일괄 인스턴스화(팔레트 생성)를 필요로 하므로 인스턴스화 API는 룩 1개 단위와 장르 묶음 단위를 모두 표현할 수 있는 형상이어야 한다.**" 이 한 문장이 `build_instantiation`의 키워드 전용 `resolution`/`pools` 파라미터(`server/looks/instantiate.py:416-423`)로 코드에 실현되어 있다 — §2에서 실측한다.
  - 같은 파일 `:186` — "**빈 익스큐터 탐색**, `Assign Sequence ... At Executor ...` 바인딩 일체"를 v1 Out of Scope로 두며 그 사유를 "익스큐터 주소 체계는 SHOWUI-001·EXECREF-001·EXECBODY-001이 반복해서 데인 영역"이라 기록. 본 SPEC의 ASSUMPTION-17이 정확히 이 미개봉 지점이다.
- **사용자 사전 확정 4건** (본 세션 이전, 재질의 금지 — 전문은 `spec.md §A 사전 확정 사실`): ① 익스큐터 페이지 레이아웃 = **M0 라이브 프로브 GO/DESCOPE 게이트**, ② 팔레트 축 = **LOOKLIB in-scope 4풀 그대로 상속**, ③ 실행 단위 = **단일 번들 · 승인 1회 · 부분 성공 구조화 보고**, ④ **라이브 세션 2회**(M0 + M7). 이 4건이 결정 A~D를 폐쇄한다(§9.1).

---

## §2. 조사 ① — 선행 룩 계층이 남긴 접합면

### 실측 구조

- **라이브러리 형상**: `LookLibrary`는 `schema_version` + `looks: tuple[Look, ...]` 두 필드뿐인 frozen 데이터클래스이며, 조회 메서드는 **`by_id` 하나뿐이다**(`server/looks/schema.py:119-130`). **장르 인덱스도 `by_genre`도 존재하지 않는다.** 즉 장르 조회는 새 자료구조가 아니라 `library.looks`에 대한 **읽기 전용 순회**로 성립한다 — REQ-BUSKWIZ-003이 요구하는 형상이 이미 유일하게 가능한 형상이다.
  - **인메모리 실측(본 plan-phase, 라이브 아님)**: 출하 라이브러리 32룩, 장르별 **worship 8 / rock 8 / ballad 7 / edm 9**. `look_id` 유일성은 로더가 강제하고(`server/looks/loader.py:218-220` docstring — "Look ids must be unique across the whole set"), **`display_name` 중복은 장르 내·간 모두 0건**, **작은따옴표를 포함한 표시 이름도 0건**이다. 후자는 `_label_of`의 `LookInstantiationError` 경로(`server/looks/instantiate.py:315-322`)가 **출하 라이브러리로는 도달 불가**임을 뜻한다 — acceptance.md §D의 "현행 라이브러리 32룩에는 해당 이름이 0건"(`acceptance.md §D "룩 표시 이름에 작은따옴표"`)을 기계로 재확인한 것이다. 전자에 대해 정본 v0.1.1은 한 걸음 더 나갔다 — 중복이 0건인 것과 **막는 기제가 있는 것은 다르다**며 원장이 라벨도 누적하도록 REQ-BUSKWIZ-005에 부속 조항을 신설했다(`REQ-BUSKWIZ-005 하위 절(원장은 라벨도 누적)`). 본 문서의 계수가 그 조항의 "지금 깨져 있지는 않다" 쪽 근거다.
- **로더 진입점**: `load_library_from_dir(directory=DEFAULT_LIBRARY_DIR)`(`loader.py:217`), 기본 경로는 `server/looks/library`(`loader.py:34`). 툴 계층은 이 함수를 `nonlocal looks` 캐시와 함께 지연 로드한다(`server/orchestrator/tools.py:665-671`, `:712-716`).
- **in-scope 풀 4종은 상수 하나로 고정되어 있다**: `IN_SCOPE_POOL_FAMILIES = ("Dimmer", "Color", "Beam", "Focus")`(`server/looks/schema.py:58`). 속성→패밀리 라우팅은 `ATTRIBUTE_POOL_FAMILY`(`:62-69`) 6항목이며 `Pan`/`Tilt`는 **의도적으로 부재**한다(`:60-61` 주석 — "Pan/Tilt are absent by design: they have no pool"). 사용자 확정 ②의 "그대로 상속"은 이 상수를 import한다는 뜻이지 재정의가 아니다.
- **패밀리 분해는 이미 함수로 존재한다**: `payload_for_family(look, family)`(`schema.py:133-147`) — in-scope가 아닌 패밀리를 넘기면 `ValueError`, 그리고 docstring `:139-140`이 "로더가 패밀리 없는 속성을 거부하므로 **네 패밀리 부분집합의 합집합은 항상 전체 페이로드**"임을 보증한다. 다중 룩 번들이 패밀리별로 저장을 계획할 때 이 보증이 "어느 값도 조용히 누락되지 않음"의 근거다.
- **리그 해석 2반쪽이 이미 분리되어 있다**: `resolve_roles(groups_section)`(`server/looks/resolver.py:121`)와 `resolve_pools(preset_pools_section)`(`server/looks/instantiate.py:217`). 두 함수 모두 **하나의 리그 섹션만** 입력으로 받고 룩을 전혀 모른다 — 룩과 무관한 순수 해석이라는 사실이 1회 해석 재사용을 문법적으로 가능하게 한다.
- **번들 빌더의 재사용 형상 (LOOKLIB이 예약했다고 말한 그것)**: `build_instantiation(look, *, resolution, pools, shape=CAPTURE_SHARED)`(`instantiate.py:416-423`). `resolution`과 `pools`가 **키워드 전용 파라미터**이고 함수 내부에서 두 해석을 다시 수행하지 않는다는 점이 예약의 실체다. 대비되는 편의 함수 `instantiate_look(look, *, groups_section, preset_pools_section, shape)`(`:476-489`)은 매 호출마다 `resolve_roles`+`resolve_pools`를 **다시** 수행한다(`:486-487`) — 다중 룩 경로가 써서는 안 되는 쪽이다.
- **역할 어휘는 6종 폐쇄 집합**: `ROLES`(`server/looks/roles.py:44`) — 백라이트(`:46`) / 프론트(`:52`) / 사이드(`:58`) / 탑(`:64`) / 배경(`:70`) / 스페셜(`:76`). 본 SPEC은 이 집합을 읽기만 한다.
- **미매핑 사유는 3종 판정 + 2종 전파 = 값 5종이다 (spec.md 인용 정정)**: 판정 3종은 `AMBIGUOUS`(`roles.py:22`) · `NO_MATCH`(`roles.py:23`) · `UNADDRESSABLE`(`resolver.py:50`)이고, 여기에 **섹션이 도착하지 않았을 때 그 사유가 역할 전체에 그대로 실린다** — `resolve_roles`가 `groups_section["reason"]`을 6역할 전부의 `UnmappedRole.reason`으로 복제한다(`resolver.py:128-137`). 실려 오는 값은 `path_not_resolved` / `console_unreachable` 2종(`tools.py:127-131`, `:409-415`). `matching.py:62`가 스스로 "the resolver keeps its **five** unmapped reasons apart"라고 적은 것이 이 5종이다. spec.md REQ-BUSKWIZ-013 (b)와 acceptance.md AC-BUSKWIZ-008 구간 3이 인용한 `server/looks/resolver.py:70`은 `UnmappedRole` 클래스 docstring 위치이며, 3종 상수의 실제 정의처는 위 세 줄이다.
- **장르 별칭 표와 해석기**: `GENRE_ALIASES` 11항목(`server/looks/matching.py:73-90`) — 한국어 7종(워십/예배/찬양/록/락/발라드/이디엠) + 영어 슬러그 4종. `resolve_genre(query)`(`:197-207`)는 별칭 히트 집합이 **정확히 1개일 때만** 장르를 반환하고 그 외에는 `None`이다(`:206-207`) — 2개 장르가 언급되면 "절반의 제약"이 아니라 축 자체가 침묵한다(`:200-203` docstring). 이 표를 본 SPEC이 재정의하지 않는 근거는 `matching.py:16-19`가 이미 적었다 — "The bridge belongs HERE and not in the assets: ... an alias field would be a schema change rippling into P1-1/P1-2".
- **결정론적 전순서는 이미 존재하는 관례다**: `_ranked`(`matching.py:294-297`)가 `(-score, look.dynamics, look.look_id)`로 정렬한다. 장르 전량 조회처럼 점수가 균일한 경우 이 키는 **다이내믹스 오름차순 → `look_id` 사전순**으로 퇴화하며, 그것이 REQ-BUSKWIZ-001이 요구하는 전순서와 정확히 같다. 즉 본 SPEC의 정렬 규칙은 신규 발명이 아니라 라이브러리 계층의 기존 타이브레이크 관례를 그대로 쓴 것이다.
- **툴 등록 표준 형태**: `TOOL_NAMES` 6종(`tools.py:40-47`), `build_toolset(...)`(`:448`)이 내부 클로저 핸들러를 정의하고, `definitions` 튜플(`:808-1051`)과 `handlers` 딕셔너리(`:1052-1059`)를 병렬로 채운 뒤 `ToolRegistry(definitions, handlers)`를 반환한다(`:1060`). `ToolDefinition`은 `name`/`description`/`parameters` 3필드 frozen 데이터클래스(`server/llm/types.py:16-26`)이며 어댑터가 제공자 와이어 형식으로 변환한다(`:20-21`).
- **`is_error` 규약의 3분기 선례**: (i) **정정 가능한 실수** → `_error_result`(`tools.py:419-427`): 알 수 없는 `look_id`(`:723-727` — "a retry with the right id succeeds"), 잘못된 `capture_shape`(`:709-711`), 리그 경로 미설정(`:730-734`). (ii) **답변인 실패** → `is_error=False`: `find_looks`의 미스(`:677-680` — "A miss is an ANSWER ..., not a tool failure: an is_error payload feeds the self-correction loop and would invite a retry that can only miss again"), 빈 번들(`:779-790`). (iii) **리그 섹션 미도착** → `is_error=True`(`:750-768`) — 관측하지 못한 리그에 대해 "매핑 실패"를 주장하지 않기 위한 구분.
- **리그를 모델 인자로 받지 않는 관례의 근거 원문**: `tools.py:735-738` — "The rig is READ here, never accepted as an argument: a model retyping a rig section can paraphrase a name, drop the truncation signal or supply a number the console never gave."

### 함의

1. **본 SPEC이 새로 만들 것은 "조율"뿐이며, 그 경계가 코드로 이미 그어져 있다.** 룩 데이터·패밀리 분해·역할 해석·풀 해석·단일 룩 번들·툴 등록 관례는 전부 소비 대상이다. 신규 계층이 필요한 곳은 정확히 네 지점 — (a) 장르 전량 조회(§2 라이브러리 형상), (b) 풀 패밀리별 슬롯 원장(§3 장애물 1), (c) N개 룩 번들 결합(§3 장애물 2), (d) 집계+룩별 2단 보고(§6). REQ-BUSKWIZ-001~020이 정확히 이 네 축을 덮는다.
2. **1회 해석 재사용은 "설계 선택"이 아니라 이미 열려 있는 문이다.** `build_instantiation`의 시그니처(`instantiate.py:416-423`)가 그 문이고, `instantiate_look` 편의 함수(`:476-489`)와 `instantiate_look` 툴 핸들러(`tools.py:739-744`)가 그 문을 쓰지 않는 쪽이다. 본 SPEC은 새 API를 만드는 것이 아니라 **예약된 API를 처음으로 실제로 사용**한다.
3. **장르 조회의 결정론은 신규 규칙이 아니다.** `_ranked`(`matching.py:294-297`)의 타이브레이크가 그대로 REQ-BUSKWIZ-001의 전순서다 — 새 정렬 규칙을 발명하면 같은 라이브러리에 두 개의 순서 관례가 생긴다.
4. **미매핑 사유는 판정 3종 + 전파 2종 = 값 5종이다 (정본 v0.1.1이 채택).** REQ-BUSKWIZ-013 (b)가 검증하는 3종은 **판정** 사유이고, 리그 섹션 자체가 도착하지 않으면 `path_not_resolved`/`console_unreachable`가 역할 6종 전부에 실려 온다(`resolver.py:128-137`). 정본은 이를 `REQ-BUSKWIZ-013 하위 절((b)의 사유 5종)`에 "3종이 아니라 최대 5종"으로 등재하고 **두 부류를 구분해 싣되 병합하지 말 것**을 요구한다. 다만 도달성은 형상에 달려 있다 — `instantiate_look` 선례는 섹션 미도착을 번들 구성 **이전에** `is_error=True`로 조기 반환하므로(`tools.py:745-768`) 그 형상에서는 전파 2종이 보고 계층에 닿지 않는다. 따라서 **테스트 스캐폴딩의 "미매핑 3종"은 축소가 아니라 정확한 표현이며**(조기 반환 형상에서 보고 어휘는 3종으로 닫힌다), 5종은 `UnmappedRole.reason` **필드가 담을 수 있는 값의 범위**에 대한 사실이다. 이 둘을 같은 층위로 섞으면 도달 불가 경로에 대한 테스트를 쓰게 된다.

---

## §3. 조사 ② — 다중 룩 조율의 실측 장애물 2건

두 장애물 모두 **단일 룩 경로에서는 발현할 수 없다.** 이유는 하나다: `instantiate_look` 툴 핸들러가 **호출마다 리그를 새로 읽는다**(`tools.py:739-744` `collect_rig_sections(...)`). 새로 읽은 리그로 새 `PoolIndex`를 만들고 그것을 즉시 버리므로, 슬롯 상태가 호출 사이에 이월될 일도 없고 번들이 두 개 이어붙을 일도 없다. 두 결함은 **하나의 해석을 N개 룩에 재사용하는 순간**(= REQ-BUSKWIZ-004를 지키는 순간) 동시에 발현한다.

### 장애물 1 — 슬롯 비전진 (본 SPEC이 반드시 해결, 결정 E)

- **frozen 계약**: `PoolBinding`(`instantiate.py:78-79`)과 `PoolIndex`(`:96-97`) 모두 `@dataclass(frozen=True)`다. `PoolBinding.occupied: tuple[int, ...] | None`(`:91`)은 콘솔이 관측 보고한 점유이며, `PoolIndex.bindings`는 `Mapping[str, PoolBinding]`(`:100`)이다.
- **선택 함수에 전진이 없다**: `_first_free_slot(occupied)`(`:307-312`)는 인자로 받은 점유 집합에서 1부터 오름차순으로 첫 미점유를 고를 뿐, **어디에도 쓰기가 없다** — 순수 함수이므로 같은 입력에 항상 같은 출력이다.
- **계획 함수가 읽기만 한다**: `_plan_stores`(`:325-384`)는 패밀리를 순회하며 `binding.occupied`를 `:346`(미관측 판정)과 `:358`(슬롯 선택)에서 **읽기만** 하고 갱신하지 않는다.
- **충돌 검사가 이 경우를 잡지 못한다**: `:359-361`의 충돌 판정은 `binding.labels`, 즉 **콘솔이 이미 갖고 있던 라벨**만 비교한다. 같은 번들 안에서 앞 룩이 방금 청구한 슬롯·라벨은 `labels`에 들어가지 않으므로, 라벨이 다른 N개 룩은 전부 `CONFLICT`(`:65`)를 피해 같은 슬롯으로 계획된다.
- **인메모리 실측 (본 plan-phase, 라이브 아님 — 결함을 코드 읽기가 아니라 실행으로 확인)**: 6역할 전부가 그룹으로 매핑되는 리그와 Dimmer(풀 1, 점유 `(1,2)`) · Color(풀 4, 점유 `(1,2)`)를 놓고, **하나의 `PoolIndex`**로 워십 8룩에 `build_instantiation`을 각각 호출했다.
  - 결과: 계획된 저장 **16건**(8룩 × 2풀), **서로 다른 목적지는 2개**(`Dimmer 1.3`, `Color 4.3`)뿐.
  - 즉 8룩 전부가 `Store Preset 1.3` / `Store Preset 4.3`을 겨냥하고, 라벨만 다르다. 14건이 앞 저장 위로 쓰인다.
  - 이것이 acceptance.md AC-BUSKWIZ-004 구간 2가 "선행 구현 회귀 고정"으로 assert하라고 지정한 바로 그 형상이다(`AC-BUSKWIZ-004 구간 2`) — 본 실측은 그 assert가 **비어 있지 않음**을 미리 확인한 것이다.
- **왜 이것이 이 프로젝트에서 특히 나쁜가**: 같은 파일 `:294-299`의 `@MX:REASON`이 이미 이 실패 모드를 이름으로 적어 두었다 — "**A store aimed at a wrong slot destroys a preset the operator built by hand, and MA3 reports it as success.**" 조용한 파괴이며 콘솔은 성공을 답한다.
- **해소 방향(결정 E)이 지켜야 하는 경계**: 원장은 **관측을 대체하지 않는다.** `binding.occupied is None`(= 미관측)일 때 `_plan_stores`가 `NO_FREE_SLOT`으로 건너뛰는 경로(`:346-357`)는 원장이 있든 없든 그대로여야 한다 — `PoolBinding` docstring(`:82-85`)이 "That is NOT the same as an empty pool (`()`), and treating it as one is how a store lands on top of somebody's work"라고 적은 그 구분이다. REQ-BUSKWIZ-005의 부속 조항과 REQ-BUSKWIZ-009가 이 경계를 문언으로 고정한다.

### 장애물 2 — `ChangeDestination Root`의 dedupe 탈락 (본 SPEC이 설계로 회피, 결정 F)

- **발생 기제 (룩 계층 쪽)**: `_bundle`(`instantiate.py:387-413`)은 형상과 무관하게 `commands[0]`을 `_DESTINATION`(= `"ChangeDestination Root"`, `:70`)으로 시작한다(`:395`). 따라서 **N개 룩의 번들을 단순 연접하면 `ChangeDestination Root`가 N번 등장한다.** 인메모리 실측(§4)에서 워십 8룩 연접 시 `dest_count = 8`로 확인했다.
- **발생 기제 (실행 계층 쪽)**: `run_commands`의 dedupe는 `already_executed = set(context.executed_ok)`를 **가변 지역 복사본**으로 만들고(`tools.py:526`), 루프 안에서 성공한 커맨드를 즉시 추가한다(`:554`). 판정은 `elif command in already_executed and not _is_programmer_state(command)`(`:537`)이며, 면제 집합은 `_PROGRAMMER_STATE_COMMANDS` **3종뿐**이다(`:227-231`) — `Clear` / `ClearAll` / 맨-형태 `Fixture|Group` 선택. `ChangeDestination Root`는 여기 없다. 따라서 2번째 이후는 `skipped_already_executed`로 떨어진다(`:544-550`).
- **라이브에서 실제로 관측되었다**: LOOKLIB M7 세션이 `skipped_already_executed` **정확히 1건**을 관측했고 그것이 `ChangeDestination Root`였다(`SPEC-COPILOT-LOOKLIB-001/progress.md:799-807`). 감사 로그 대조가 이를 확정한다 — 승인 이벤트는 10개 커맨드를 열거하고 실행된 행은 9개이며, 빠진 1개가 `ChangeDestination Root`다(`:803-805`, 재진술 `:1167-1170`).
- **그럼에도 그 세션의 두 번째 번들은 정상 왕복했다** — 목적지 상태가 세션에 남아 있기 때문이다. 같은 세션에서 `ClearAll`은 **4회 전부 보존**되었다(`progress.md:1171-1173`) — 면제 집합이 유닛이 아니라 실물 왕복에서 하중을 받은 최초 기록이며, 면제가 없었다면 2번째 이후가 드롭돼 캡처가 오염된다.
- **선행 SPEC이 남긴 미결 판단**: `progress.md:1330` — "dedupe 규칙 개정(=`tools.py`, M5 소관) 여부는 M4가 단독으로 정하지 않는다." (여기의 M4·M5는 **LOOKLIB의 마일스톤**이지 본 SPEC의 것이 아니다.) 본 SPEC의 답이 결정 F이며, spec.md §D가 "개정하지 않는다"로 문서화한다(`spec.md §D "Out of Scope — dedupe 규칙 개정"`).
- **회피가 성립하는 이유**: 커맨드 문자열이 번들 안에 **1회만** 존재하면 dedupe가 발동할 대상 자체가 없다(`:537`의 `command in already_executed`가 거짓). 룰북도 같은 형상을 지시한다 — "Before any programming command, issue **exactly once at the start of the bundle**"(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:11-15`). 즉 REQ-BUSKWIZ-006은 dedupe 회피를 위한 편법이 아니라 **룰북 원문 그대로의 형상**이며, 룩 단위 번들 연접이 오히려 룰북에서 벗어난 형태다.
- **`ClearAll` 규율은 반대로 룩마다 유지되어야 한다**: `31_choreography_patterns.md:40-41` — "`ClearAll` before every fresh look AND after every `Store` — leftover programmer values TRACK into the next capture and silently corrupt the following cue." 이것이 면제 집합에 `ClearAll`이 들어 있는 이유이며(`progress.md:1320` — "`ClearAll`이 두 번 나온 것은 같은 명령 두 번이 아니라, 서로 다른 두 순간에 실행되어야 하는 하나의 명령이다"), REQ-BUSKWIZ-006이 "선두 1회 + 룩 단위 `ClearAll` 유지"라는 **비대칭** 형상을 요구하는 근거다.

---

## §4. 조사 ③ — 리그 컨텍스트 획득 경로와 쿼리 예산

- **경로 상수 (현재 트리 기준 — spec.md 인용 드리프트 정정)**: `DEFAULT_RIG_CONTEXT_PATHS` 10종은 `tools.py:89-100`, 드릴다운 대상은 `DEFAULT_RIG_DRILLDOWN = ("preset_pools", "pages")`(`:105`), 쿼리 상한은 `RIG_DRILLDOWN_QUERY_CAP = 16`(`:112`). "추측된 경로는 죽은 채 출하된다" 사고 기록은 `:77-79`다. (spec.md·LOOKLIB 문서가 인용한 `:65-76` / `:81` / `:88` / `:53-55`는 룩 툴 2종이 추가되기 전 줄번호다 — §9.3.)
- **룩 경로는 2섹션만 읽는다**: `LOOK_RIG_SECTIONS = ("groups", "preset_pools")`(`tools.py:118`), 그리고 프리셋 풀 드릴은 선택이 아니다 — `_LOOK_DRILLDOWN = frozenset({"preset_pools"})`(`:124`)를 호출자 설정과 OR 결합한다(`:742`). 이유는 `:120-123` 주석 그대로 "Occupancy is what makes 'is this slot free' answerable at all".
- **수집 함수와 예산 소비**: `collect_rig_sections(state_port, paths, drilldown, budget)`(`:366-416`)는 섹션마다 1회 `query_state`(`:393`)를 쓰고, 드릴 대상 섹션은 `drill_into(...)`로 예산을 넘긴다(`:407`). `drill_into`(`:322-363`)는 자식 1개당 예산 1을 소비하며(`:353`), 예산 소진 시 섹션에 `drilldown_capped`를 표시한다(`:361-362`) — "partial walk as a complete one"을 금지하는 규율.
- **1룩당 쿼리 비용**: 상위 2회(`groups`, `preset_pools`) + 프리셋 풀 자식 드릴 최대 16회 = **최대 18회 UDP 왕복**(각 왕복은 게이트+감사를 통과한다 — `:341-343`).
  - 따라서 **1회 해석 재사용(REQ-BUSKWIZ-004)의 절감은 정성적 선호가 아니라 산술이다**: EDM 9룩을 단일 룩 경로로 반복하면 최대 162회, 1회 해석이면 최대 18회. 9배.
- **예산 소진이 곧 저장 건너뜀으로 연결되는 사슬 (기록해 둘 가치가 있는 연쇄)**: 예산이 다해 드릴되지 않은 풀에는 `contents` 키가 없다 → `_observed_contents`가 `None`을 반환한다(`instantiate.py:199-201`) → `PoolBinding.occupied is None` → `_plan_stores`가 `NO_FREE_SLOT`으로 건너뛴다(`:346-357`). 즉 **`drilldown_capped`는 보고용 부가 신호가 아니라 저장 건수를 직접 깎는 원인**이며, acceptance.md §D의 "드릴다운 상한 도달" 엣지 케이스(`acceptance.md §D "드릴다운 상한 도달"`)가 이 사슬을 가리킨다.
  - 자식이 번호 없이 도착해도 같은 결과다 — `_observed_contents:207-211`이 "Some slot in here is taken and the responder could not say which, so no slot in this pool can be claimed free"라며 `None`을 반환한다.
- **실패 사유 이분은 병합 금지**: `path_not_resolved`(설정 결함) vs `console_unreachable`(운영 조건). 분류 규칙은 `collect_rig_sections:374-386` docstring과 `:409-415`에 있고, 두 소비자(`get_rig_context`, `instantiate_look`)가 같은 규칙을 공유하도록 함수로 뽑혀 있다(`:380-386` — "two copies of that classification would be two chances to collapse it back into one soft 'unavailable'").

### 번들 규모 — ASSUMPTION-18의 실측 대상 (인메모리 실측, 본 plan-phase)

`_bundle`(`instantiate.py:387-413`)의 형상으로부터 장르 번들의 줄 수가 결정된다. CAPTURE_SHARED에서 룩 1개는 `ChangeDestination Root` + `ClearAll` + 선택 + 값 + (`Store`+`Label`) × 패밀리수 + `ClearAll`이다(`:395-404`). 선두 `ChangeDestination Root` 1회 형상(REQ-BUSKWIZ-006)으로 결합하면 총 줄 수 = 1 + 4N + 2S (N = 룩 수, S = 계획된 저장 수).

출하 라이브러리로 실측한 결과(6역할 전부 매핑, 관측된 빈 풀 가정):

| 장르 | 룩 | 저장(4풀) | SHARED·4풀 | 〃 +경계접기 | SHARED·D+C만 | 〃 +경계접기 | (닫힌 경로) PER_FAMILY·4풀 |
|---|---|---|---|---|---|---|---|
| ballad | 7 | 19 | **67** | 61 | 57 | **51** | 103 |
| worship | 8 | 22 | **77** | 70 | 65 | 58 | 119 |
| rock | 8 | 22 | **77** | 70 | 65 | 58 | 119 |
| edm | 9 | 25 | **87** | 79 | 73 | 65 | 135 |

"경계접기"는 룩 k의 말미 `ClearAll`과 룩 k+1의 선두 `ClearAll`이 인접 중복이 되므로 1회로 접는 형상이다(N-1행 절감). 정본의 하한 **51**은 이 접기를 적용한 최소치(ballad · Dimmer+Color)이고, 상한 **87**은 접기 없는 최악값(edm · 4풀)이다 — 즉 `ASSUMPTION-18`의 "51~87행"은 단일 형상의 밴드가 아니라 **하한은 최선·상한은 최악을 취한 포괄 봉투**이며, ASSUMPTION-18의 측정에는 그것이 옳은 방향이다(측정은 최악값으로 해야 한다).

- **함의 1 — 측정 기준은 "40여 줄"이 아니라 실제 상한 87행이다.** 당시 정본의 "약 40여 커맨드"는 **쌍(pair) 수**에서 나온 추정치였고(이력은 `spec.md §A "수용된 잔여 위험"`), 행 수 기준 실제 밴드는 위 표와 같다. M0가 40줄을 통과시키고 GO를 선언하면 EDM에서 미검증 구간이 47줄 남는다. 정본 v0.1.1이 이를 받아 `spec.md §A "번들 규모의 실측"`(실측 절)·`:117`(ASSUMPTION-18)·`AC-BUSKWIZ-016 측정 항목 3`(AC-BUSKWIZ-016 측정 항목 3)을 **87행**으로 고정했다 — REQ·AC 집합은 무변경이고 측정값만 구체화되었다.
- **함의 2 — LOOKLIB M7 실측 최대와의 배율은 약 2배가 아니라 약 4.1배다(87/21).** M7이 무손실 왕복을 확인한 최대 번들은 21줄 FALLBACK 형상이었다(`SPEC-COPILOT-LOOKLIB-001/progress.md:1326` — "21줄 FALLBACK 번들이 `console.executed == plan.commands`로 **정확히** 왕복함을 확인했고, 4개 격리 사이클·`ClearAll` 5회·`Group 11` 4회 전부 보존, `is_error: False`"). 즉 "40여 줄"을 기준으로 잡으면 배율이 절반으로 축소 보고된다.
- **함의 3 — CAPTURE_PER_FAMILY는 규모 레버가 아니라 닫힌 경로다 (v0.1.1 정정).** v0.1.0의 이 항목은 per-family를 "ASSUMPTION-18 부정 시의 완화 수단 후보"로 적었다. **그 프레이밍은 틀렸다** — 정본 `REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)`이 `shared_capture` 고정 + 모델 인자 미노출로 닫았고, 근거는 규모(103~135행)가 아니라 **조용한 오염**이다: per-family는 룩마다 패밀리별 값 라인을 따로 발화하는데(`instantiate.py:406-411`) 서로 다른 룩의 값 라인이 문자열로 같아질 수 있고, 값 라인은 dedupe 면제 집합에 없는 반면(`tools.py:227-231`) 직전 `ClearAll`은 면제라 살아남는다 → 두 번째 값 라인이 탈락하면 **빈 프로그래머 상태로 `Store`가 실행되고 콘솔은 성공으로 답한다.**
  - **본 문서의 교차 확인(인메모리 실측)**: 장르 내 per-family 값 라인 충돌은 **rock 1건**(`Attribute 'Iris' At 100` ×2)·**edm 1건**(`Attribute 'Dimmer' At 100` ×2)으로 실재한다. 반면 `shared_capture`의 룩당 전체 값 라인은 **32룩 전수에서 중복 0건**이라 이 경로가 존재하지 않는다. 정본의 실측과 독립 계수가 일치한다.
  - **귀결**: per-family 열의 103~135는 **참고 수치일 뿐 M0의 측정 대상이 아니다.** 도달 불가능한 형상을 M0가 재면 측정 예산만 쓰고 GO/DESCOPE 판정에는 기여하지 않는다. ASSUMPTION-18 부정 시의 완화 수단은 형상 교체가 아니라 **번들 분할 정책**이며, 그것은 사용자 확정 ③(단일 승인)과 충돌하므로 M0 게이트의 사용자 결정 항목이다(`ASSUMPTION-18`).
- **함의 4 — 40여 줄이든 87행이든 "사람이 프리뷰에서 실질 검토하기 어렵다"는 잔여 위험은 커진 채 그대로다.** 이 논거는 사용자에게 제시되어 수용되었고(`spec.md §A "수용된 잔여 위험"`), 완화는 REQ-BUSKWIZ-013의 집계 보고가 담당한다. 실측치는 그 위험의 크기를 정정할 뿐 결정을 재개봉하지 않는다.

---

## §5. 조사 ④ — 익스큐터/페이지 문법의 근거 지형

**전수 확인 방법**: `server/rulebook/assets/v2.4.2/` 전체에 대해 (i) 라이브 검증 선언 문자열, (ii) `Page` 등장 지점, (iii) 페이지·익스큐터 **저작** 동사를 grep했고, v0.1.2에서 (iv) **프리셋을 익스큐터에 얹는 형태**를 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/` 전체로 넓혀 다시 grep했다. 결과는 아래 3분류다.

- **라이브 검증을 선언하는 룰북 파일은 정확히 1개다**: `31_choreography_patterns.md:7` — "Every pattern below was validated live on onPC 2.4.2." 이 파일은 절 제목에도 `(validated)`를 반복 표기한다(`:25`, `:33`, `:43`, `:61`, `:82`, `:96`, `:106`, `:108`, `:119`, `:140`, `:151`). **나머지 4개 자산(`00_grammar.md` · `10_object_model.md` · `20_korean_terms.md` · `30_plugin_patterns.md`)에는 라이브 검증 표시가 없다** — `10_object_model.md:25`, `:31`의 "live"는 "live playback" / "live editing buffer"라는 일반 명사이지 검증 선언이 아니다.
- **페이지·익스큐터 저작 문법은 룰북 전체에서 0건이다**: `Store Page` / `Label Page` / `Label Executor` / `Delete Page`를 `v2.4.2/` 전체에 grep → **매치 없음**. `Copy Page`도 없다.
- **프리셋을 익스큐터에 얹는 형태는 리포지토리 전체에서 0건이다 (v0.1.2 — ASSUMPTION-19의 근거, 본 문서가 독립 재확인)**: `Assign Preset` · `Store Executor` · `Label Executor` · `Preset <p>.<s> At …`를 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/`에 grep → **각각 0개 파일**. 그리고 리포지토리에 존재하는 **모든** `At Executor` 발생(테스트 5파일 · 감사 로그 · 룰북 `:99`/`:168` · `last_created.py:13`/`:15`)의 목적어는 **예외 없이 `Sequence`**다.

### 3분류 표

| 분류 | 커맨드 형태 | 등장 지점 | 근거의 성격 |
|---|---|---|---|
| **① 라이브 검증됨** | `Assign Sequence <n> At Executor <m>` | `31_choreography_patterns.md:99` (Playback 절, `(validated)` `:96`) | 파일 헤더 `:7`의 전역 라이브 검증 선언 아래. 재등장 `:168`은 **Lua 플러그인 예제 안의 `Cmd(...)` 문자열**(`Cmd("Assign Sequence 16 At Executor 193")`)이라 같은 형태의 2차 확인이지 독립 실측은 아니다. 안전 게이트도 이 형태를 `safe`로 분류한다(`server/tests/test_safety_classify.py:152` — `Assign Sequence 1 At Executor 201`) |
| **① 라이브 검증됨** | `Go+ Executor <n>` / `Off Executor <n>` | `31_choreography_patterns.md:100-101` | 같은 절. `:104`가 "**Always address `Executor <n>` explicitly** so 'advance the show' is unambiguous"로 형식을 명시 지시 |
| **② 문법서 유래 (라이브 검증 표시 없음)** | `Page <page>.<executor>` dotted 주소형 | `00_grammar.md:19`(dotted id 규칙), `:47`(`Assign Sequence 2 Page 1.201`), `:51`(`Toggle Page 1.201`), `:52`(`Flash Page 1.203`), `:70`(`Assign Sequence 2 Page 1.201`), `:71`(`Page 1.201 At 75`); `10_object_model.md:23-24`; `20_korean_terms.md:26`(페이더), `:27`(페이지) | 세 파일 모두 라이브 검증 선언이 없다. **`00_grammar.md:47`과 `31_choreography_patterns.md:99`가 같은 작업(시퀀스→익스큐터 바인딩)에 서로 다른 형태를 제시한다** — 전자는 dotted, 후자는 `At Executor`. 리포지토리 코드는 후자만 발화한다(아래) |
| **③ 근거 0건** | 페이지 생성/라벨/복사 (`Store Page` / `Label Page` / `Copy Page`), 익스큐터 라벨링(`Label Executor`), 빈 익스큐터 열거 | 룰북 `v2.4.2/` **0건**. 유일 등장처는 `server/measurement/corpus.yaml:98`(`Store Page 3`), `:99`(`Label Page 3 "Ballad"`), `:105`(`Copy Page 1 At Page 4`) | `corpus.yaml:7-10`이 스스로 그 블록을 **"the deterministic offline action for M6a mock runs ONLY"** 이고 커맨드 라인은 **"structurally valid"** 할 뿐이라고 한정한다 — 콘솔 수용을 주장하지 않는다. 더욱이 `:99`는 **큰따옴표**를 쓰는데 `00_grammar.md:26-29`가 생성 커맨드에서 이를 금지한다("the transport wraps command lines in double quotes and an embedded double quote breaks the command") — **그대로 발화하면 깨지는 형태다.** 같은 파일 `:22`, `:31`도 같은 결함을 갖는다 |
| **③ 근거 0건 (ASSUMPTION-19)** | **프리셋을 익스큐터에 얹는 형태** — `Assign Preset …` / `Preset <p>.<s> At (Executor\|Page) <n>` / `Store Executor` | **리포지토리 전체 0개 파일** (`server/` · `console/` · `docs/` · `ui/` · `.moai/project/`). mock 자산에도 없다 — `corpus.yaml`조차 이 형태를 지어내지 않았다 | 룰북이 아는 프리셋 동사는 **전부 프로그래머 쪽**이다: `Store Preset`(`00_grammar.md:67`) · `Label Preset`(`:68`) · `Call Preset 4.1`(`:59` — "Recall an object into **the programmer**") · `At Preset 4.1`(`:72` — 선택에 적용). **익스큐터 쪽 프리셋 동사는 하나도 없다.** 더 결정적인 것은 룰북이 이 공백을 스스로 메우는 방식이다 — `31_choreography_patterns.md:225-227`은 "`instantiate_look` creates presets only — **no cue, no sequence, no executor assignment**. Build whatever the operator has to FIRE afterwards with `run_commands`, **recalling the presets it reports**"라고 지시한다. 즉 룰북 자신의 답이 "프리셋을 익스큐터에 얹어라"가 아니라 **"프리셋을 큐로 되불러라"**이며, 그 경로는 §D가 범위 밖으로 둔 시퀀스·큐 생성이다 |

### 리포지토리 코드가 실제로 발화하는 형태 — `Executor <n>` 단일

- **패널 재생 커맨드**: `playback_command(verb, target_kind, target)`(`server/web/panel.py:592-593`)이 `"Go+ Executor 191"` 형태를 만들고, 클래스별 콘솔 키워드는 `_TARGET_WORD = {"executor": "Executor", "sequence": "Sequence"}`(`:550`)로 고정되어 있다.
- **크로스턴 메모리 문서**: `server/orchestrator/last_created.py:13`이 인식 대상 형태로 `Assign Sequence <n> At Executor <m>`을 적고, `:15`가 Lua 플러그인 발화 예(`Assign Sequence 16 At Executor 193`)를 든다.
- **콘솔측 응답기**: `EXECUTOR_ADDRESS_PATTERN = "^Executor%s+(%d+)$"`(`console/lua/copilot_responder.lua:405`). 주석 `:397-404`가 "**This is the ONLY address form `resolve_path` special-cases**; every other path still walks the DataPool/Root/ShowData/Patch tree below unchanged"라고 명시한다 — 즉 응답기는 `Page 1.201`을 익스큐터 주소로 **해석하지 못하고** 트리 워크로 떨어진다.
- **결론**: `Page <p>.<e>` dotted form은 (i) 라이브 검증 표시가 없고, (ii) 서버·콘솔 어느 코드 경로도 발화하지 않으며, (iii) 응답기가 특수 처리하지 않는다. REQ-BUSKWIZ-018의 금지는 이 3중 근거 위에 선다.
- **ASSUMPTION-19에 주는 함의**: 위 세 지점 어디에도 **프리셋을 목적어로 받는 익스큐터 커맨드가 없다.** `_TARGET_WORD`는 `executor`/`sequence` 2종뿐이고(`panel.py:550`), `last_created.py:13`이 인식하는 생성 형태도 시퀀스 바인딩뿐이며, 응답기가 특수 처리하는 것은 주소형(`Executor <n>`)이지 목적어 타입이 아니다. 즉 ASSUMPTION-19는 "아직 안 찾아봤다"가 아니라 **"찾을 수 있는 모든 곳을 봤고 없다"**에 가깝다 — M0가 뒤집을 수는 있지만, 뒤집히지 않는 쪽이 기본 기대값이다.

### 역주소 문제 — 미해결로 상속됨

- **두 숫자 체계**: 페이지-로컬 자식 인덱스(실측 `1, 5, 11, 91, 92, 93, 95, 101`)와 콘솔 발화 번호(실측 `101, 105, 111, 191, 192, 193, 195, 201`)가 다르다(`SPEC-COPILOT-EXECBODY-001/spec.md:43`). **페이지 1에서 8/8 표본 전부 `+100` 오프셋이 관측되었고, 다른 페이지 관측은 전무하다**(같은 줄).
- **코드에 남은 형태**: `_executor_candidates(slot_no, page_no)`(`server/web/dash.py:145-163`)가 raw slot을 먼저, `page_no * 100 + slot_no`를 두 번째 후보로 만든다(`:158-162`). docstring `:150-152`가 "Live-measured on onPC 2.4.2 (2026-07-24, DASHUI M6 root-cause probe)"로 페이지 1 실측임을 명시하고, `:154-156`이 "every candidate is name-VERIFIED before being believed and an unconfirmed candidate is never emitted"라고 규율을 적는다. 확인 함수는 `_confirm_executor_no`(`:129-142`) — `Executor <n>` 조회 후 이름 일치를 요구한다.
- **믿을 수 있는 번호의 유일한 출구**: `resolved_executor_nos(sections)`(`dash.py:309-327`)는 `meta["resolved"] is True`이고 `console_no`가 int인 항목만 반환한다(`:325-326`). docstring `:312-313` — "These are the only numbers a dash executor press may target".
- **금지 규범**: `REQ-EXECBODY-007`(`SPEC-COPILOT-EXECBODY-001/spec.md:69`)은 "**최소 2개 이상의 서로 다른 페이지에서 라이브로 검증되기 전에 일반 해석 규칙으로 하드코딩**"을 금지하고, `REQ-EXECBODY-008`(`:70`)은 "검증이 수행되지 않으면 **해당 메커니즘은 출하하지 않는다**"고 못 박는다. 그 조건은 **아직 충족되지 않았다** — 관측은 여전히 페이지 1뿐이다. REQ-BUSKWIZ-017이 이 금지를 계승한다.
- **GO/DESCOPE 프로브 선례**: `AC-EXECBODY-010`(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123`)이 "M1 GO인 경우 / M1 DESCOPE인 경우: **본 AC는 미달성으로 정직하게 기록**"의 양 분기 판정을 이미 정의했다. AC-BUSKWIZ-012가 같은 형상이다.

### ASSUMPTION-17이 왜 열려 있는가 — 드릴다운의 정확한 한계

- `_build_executors_section`(`dash.py:166-240`)은 페이지를 드릴한 뒤 **`page.get("contents", [])`에 실제로 들어 있는 자식만** 순회하고(`:202`), 번호가 없는 자식은 건너뛴다(`:203-205`).
- 결과 항목은 `meta = {"resolved": ...}` + 확인된 경우 `console_no`(`:227-230`)를 담는다. 즉 이 보고는 **"열거된 자식 중 콘솔 번호를 확인하지 못한 것"**을 표시할 수 있다.
- **그러나 "비어 있는 익스큐터"에 대응하는 표현이 아예 없다.** 열거되지 않은 슬롯은 (a) 정말 아무것도 없는 것인지, (b) 드릴이 도달하지 못한 것인지(`contents_unavailable`, `:238`; `drill_into:357`), (c) 예산에 걸린 것인지(`drilldown_capped`, `:209`, `:213`) 항목 수준에서 구분되지 않는다. **"이 페이지의 어느 익스큐터 번호가 비어 있는가"를 묻는 질의 자체가 존재하지 않는다.**
- 이것이 ASSUMPTION-17의 정확한 형태다 — "판별 로직이 부실하다"가 아니라 **"물을 방법이 관측되지 않았다"**. LOOKLIB이 "빈 익스큐터 탐색"을 명시적 Out of Scope로 둔 이유와 같다(`SPEC-COPILOT-LOOKLIB-001/spec.md:186`).

### 대조 관측 — dotted form이 라이브에서 실행된 적은 있다 (정직한 기록)

- LOOKLIB M7 세션에서 **모델이** `Assign Sequence 17 At Page 1.102`와 `Go+ Page 1.102`를 발화했고, 후자는 참조 발화형이라 게이트가 보류한 뒤 운영자 승인 후 실행되었다(`SPEC-COPILOT-LOOKLIB-001/progress.md:790-791`, `:796`, 감사 타임라인 `:858-859`, 요약 `:1160`).
- **그 세션 자신이 이것을 인수 근거에서 배제했다**: `progress.md:862` — "**이것은 툴 위에서 일어난 모델의 창발 행동이지 본 SPEC의 요구가 아니다.** 인수 결과로 계수하지 않으며, AC 어느 항목의 근거로도 쓰지 않는다."
- **따라서 REQ-BUSKWIZ-018의 금지는 "콘솔이 거부한다"가 아니라 "본 프로젝트가 발화하는 형태를 하나로 유지한다"에 근거한다.** 이 구분을 기록해 두는 이유는, 후속 SPEC이 "라이브에서 돌던데?"로 금지를 스타일 선호라 재론하지 않게 하기 위함이다 — 재개봉의 정당한 조건은 (i) 룰북 자산에 라이브 검증 표시가 붙거나, (ii) 응답기가 dotted form을 특수 처리하게 되거나, (iii) `REQ-EXECBODY-008`의 2페이지 검증이 충족되는 것이다.

---

## §6. 조사 ⑤ — 안전 계층과 보고 표면

- **단일 스크리닝 경로 (앵커)**: `SafetyGate.screen`(`server/safety/gate.py:265`) 위의 `@MX:ANCHOR`(`:260-262`)와 `@MX:REASON`(`:263-264`) — "REQ-MVP-011/029 — exactly ONE screening path may exist; **a second entry would be a gate bypass by construction** (fan_in >= 3)". `run_commands`가 번들 전체를 이 경로로 통과시킨다(`server/orchestrator/tools.py:485`).
- **룩 계층이 이미 같은 규율을 명시적으로 상속했다**: `tools.py:686-696`의 `@MX:ANCHOR`/`@MX:REASON` — "This handler is a **CALLER of run_commands, never a second execution surface**: it re-enters the local run_commands closure above, so the bundle inherits that path's gate screening, execution preview, dedupe and audit log". 재진입은 `:791-794`. 세션 배선 쪽에도 같은 문장이 있다 — `server/web/session.py:218-220` "Held so a look bundle re-enters the SAME run_commands tool the model uses, rather than growing a second way to reach the console." **본 SPEC의 REQ-BUSKWIZ-011과 REQ-BUSKWIZ-012는 새 규범이 아니라 이 두 지점의 3번째 준수 사례다.**
- **프리뷰는 스크리닝을 감싼다**: `_ObservingBundleGate.screen`(`session.py:162-166`)의 본문은 정확히 세 줄 — `_on_preview(commands)`(`:163`) → `self._gate.screen(commands)`(`:164`) → `_on_decision(decision)`(`:165`). 배선은 `build_toolset(..., bundle_gate=_ObservingBundleGate(gate, self._on_preview, self._on_decision), ...)`(`:211-217`, 해당 인자 `:214`). 즉 채팅 세션이 만드는 모든 툴셋이 이 래퍼를 통과하며, **버스킹 번들도 예외 없다.** (spec.md·LOOKLIB이 인용한 `session.py:161-165` / `:213`은 한 줄 오프셋 — §9.3.)
- **커맨드별 severity 분류**(`server/web/preview.py:99-170`, 입력은 `lower = command.lower()`로 대소문자 무관 `:100`):

  | 패턴 | severity | label | 라인 |
  |---|---|---|---|
  | `delete` 액션 | `danger` | 삭제 명령 | `:104-112` |
  | `store_overwrite` 액션 | `caution` | 덮어쓰기 | `:113-121` |
  | `blackout` / `off` 액션 | `danger` | 블랙아웃/오프 | `:122-130` |
  | `\b(strobe\|shutter\|hz)\b` | `danger` | 스트로브/셔터 변화 | `:131-139` |
  | `\b(blinder\|audience)\b` 또는 `객석` | `danger` | 객석 블라인더 | `:140-148` |
  | `\b(pan\|tilt)\b` (`_has_movement` `:173-174`) | `caution` | Pan/Tilt 이동 | `:149-157` |
  | `full` / `at 100` / `dimmer 100` / `intensity 100` (움직임 없을 때만) | `caution` | 풀 인텐시티 | `:158-169` |

  중복 제거는 `_dedupe_warnings`(`:186-195`), 번들 등급 승격은 `_risk_level`(`:198-204`) — 최고 severity가 번들 등급이 된다.
- **버스킹 번들의 예상 등급**: 라이브러리에 스트로브/셔터·Pan/Tilt는 0건이고(LOOKLIB이 원천 차단 — `SPEC-COPILOT-LOOKLIB-001/spec.md:188-190`, `:196-199`), 번들에는 `Delete`도 `Off`도 없다. 남는 경로는 **풀 인텐시티 `caution`** 하나 — `Attribute 'Dimmer' At 100` 계열이 있으면 `:158-169`에 걸린다. 즉 정상 버스킹 번들의 상한은 `caution`이며, `danger`가 뜨면 그것은 **라이브러리 오염 신호**다(acceptance.md §D `:276`이 같은 판정을 적는다).
- **파괴적 저장의 차단선**: `server/safety/blacklist.yaml:18` `"Store /overwrite"`(**spec.md REQ-BUSKWIZ-007이 인용한 `:19`는 `"Shutdown"`이다** — §9.3). 블랙리스트는 닫힌 집합이며 파일 개정 + 버전 범프로만 바뀐다(`:3-5`). REQ-BUSKWIZ-007의 "Overwrite 0건"은 이 승인 보류를 회피하는 것이 아니라 **애초에 발화하지 않는 것**이다.
- **LiveLock 강등 경로**: 상태 객체는 `LiveLock`(`server/safety/lock.py:23`, `is_active` `:30`), 파이프라인 문서화는 `gate.py:7-8`("live-lock check → ③ human approval (risky only) → **lock re-check (lock-FIRST, REQ-MVP-035)**"). 잠금 시 산출물은 `ProposalCard(commands=..., reasons=("... — read-only proposal (REQ-MVP-016)",))`(`gate.py:471-474`; 타입 `lock.py:15-19`), 실행 직전 재확인은 `:504-506`, `:550-552`. REQ-BUSKWIZ-014는 이 기존 경로를 소비할 뿐 새 강등 로직을 만들지 않는다.
- **⚠️ 실행 시점 부분 성공의 두 번째 기제 — stop-on-first-failure (본 문서가 열었고 정본 v0.1.1이 받았다)**: `run_commands` 루프는 **첫 실패 이후의 모든 커맨드를 실행하지 않고 `not_executed`로 표기한다**(`tools.py:527-536`, 플래그 세팅 `:562`). 즉 87행 번들의 12번째 줄이 실패하면 나머지 75줄은 전부 미실행이며, 그 사실은 per-command status로만 드러난다.
  - **왜 중요한가**: REQ-BUSKWIZ-010이 말하는 부분 성공은 **빌드 시점**의 것이다 — 그 저장이 애초에 계획에 서지 않은 경우(**풀 미해석 · 라벨 충돌**; 점유 미관측은 REQ-BUSKWIZ-009가 따로 덮는다). 실행 시점에는 **다른 종류의 부분 성공**이 있고, REQ-BUSKWIZ-013 (d)의 "룩별 판정(전량 성공 / 부분 / 저장 0건)"은 계획 결과만으로 산출할 수 없다 — 실행 결과의 per-command status와 대조해야 한다. `instantiate_look` 선례가 그 대조 재료를 이미 반환한다(`tools.py:795-797` — `payload["executed"]`와 `payload["report"]`를 함께 싣는다). **"패밀리 구성 차이"는 v0.1.4에서 이 열거에서 빠졌다**(재감사 D2) — 값 없는 패밀리는 `_plan_stores`가 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않으므로(`server/looks/instantiate.py:332-334`) 그 룩은 `skipped=0 complete=True`인 완전 성공이다.
  - **정본 반영 상태**: 새 REQ가 아니라 REQ-BUSKWIZ-013의 보고 요소로 흡수되었다 — **(e) 미실행 커맨드 수**가 신설되고 `REQ-BUSKWIZ-013 하위 절((c)와 (e) 합산 금지)`이 두 수의 합산을 금지하며(건너뜀은 빌드 시점 판정, 미실행은 실행 시점 귀결), `AC-BUSKWIZ-008 구간 6`이 두 수를 합산한 단일 숫자만 내는 보고를 실패로 판정한다. AC 개수는 17건 그대로다.
- **집계 단위가 `(룩, 역할)` 쌍인 이유는 1회 해석의 직접 귀결이다 (정본 `REQ-BUSKWIZ-013 하위 절((b)의 집계 단위)`)**: 리그를 정확히 1회만 해석하므로(REQ-BUSKWIZ-004, §2 함의 2) **하나의 미매핑 역할은 그 역할을 선언한 모든 룩에서 반복된다.** 집계를 distinct 역할 수로 세면 룩별 합계와 어긋나 AC-BUSKWIZ-008 구간 1(산술 일치)이 기계적으로 깨진다.
  - **인메모리 실측으로 본 괴리 폭(본 plan-phase, 라이브 아님)**: 4장르 모두 6역할을 전부 사용하며, 장르별 `(룩, 역할)` 쌍은 **worship 25 / rock 26 / ballad 20 / edm 26**이고 distinct 역할은 언제나 6이다 — 즉 **3.3~4.3배**. 역할이 하나도 매핑되지 않는 리그에서 worship을 돌리면 보고의 집계는 25여야 하고 6이면 룩별 합계와 어긋난다. 단일 역할 기준 최대 기여는 rock의 `사이드`(8룩 중 7룩)·worship의 `배경`(8룩 중 6룩)이므로, **역할 하나만 미매핑이어도 쌍 카운트는 최대 7까지 올라간다.**
  - 이는 새 요구가 아니라 REQ-BUSKWIZ-004와 REQ-BUSKWIZ-013 (b)가 만나는 지점의 산술이며, 정본이 `REQ-BUSKWIZ-013 하위 절((b)의 집계 단위)`에 "distinct 역할 목록은 별도 필드로 병기"까지 함께 못 박아 사람이 읽을 값과 집계에 쓰는 값을 분리했다.
- **툴 설명문의 사유 열거 선례**: `instantiate_look`의 `ToolDefinition` 설명문(`tools.py:977-1050`)은 미매핑 3종(`:1006-1011`)과 건너뜀 4종(`:1012-1019`)을 문자열 그대로 열거하고, "the unit is one preset store, so a look can be **partly created and partly skipped**"(`:1018-1019`), "**'complete': false** whenever anything was unmapped or skipped. Say so — never report a partial run as a whole one"(`:1020-1021`)까지 적는다. REQ-BUSKWIZ-013의 2단 보고가 모델에게 전달되려면 신규 툴 설명문도 같은 밀도를 가져야 한다 — 이 선례가 그 기준선이다.
- **감사·승인 철학**: `product.md:45` "AI는 초안을 생성할 뿐, 연출의 최종 확정은 항상 사람이 한다." 승인 기본값은 deny-all(`gate.py:145` `DenyAllApprovalPort()`). 본 SPEC은 승인 카드·프리뷰·감사 어느 것도 새로 만들지 않는다.

---

## §7. 고려하고 기각한 대안

### 기각 (a) — 장르 룩 조회를 기존 `match_looks` **툴 경로**로 해결

- **내용**: 신규 조회 계층 없이 `find_looks` 툴에 장르명을 던져 그 결과를 장르 전량으로 사용한다.
- **기각 사유**:
  1. **툴 경로가 결과를 자른다.** `find_looks` 핸들러는 `match_looks(query, looks).to_dict()`를 직렬화하고(`tools.py:676`), `LookMatch.to_dict(limit=MAX_TOOL_MATCHES)`의 기본 상한이 **8**이다(`server/looks/matching.py:279-280`, 상수 `:71`). **EDM 9룩은 정확히 1건이 잘린다.** `truncated: True`가 함께 실려도(`:289`) 잘린 1룩의 정체는 복구할 수 없다.
     - 정밀 구분: `match_looks` **함수 자체**는 자르지 않는다 — 장르 제약이 걸리면 밴드 전체를 `matches`에 담는다(`:323-327`, 키워드 무득점 시 `:337-341`). 절단은 **툴 직렬화 경계**에서 일어난다. 따라서 이 기각은 함수의 결함이 아니라 **툴 경로 선택의 결함**에 대한 것이다.
  2. **장르 해석이 조용히 실패할 수 있다.** `resolve_genre`는 두 장르가 언급되면 `None`을 반환하고(`matching.py:206-207`), 그 경우 `match_looks`의 `survivors`는 장르 필터 없이 32룩 전체가 된다(`:326`) — "EDM 록 느낌으로"류 발화에서 조회 대상이 조용히 라이브러리 전체로 넓어진다.
  3. **툴 왕복이 한 번 더 든다.** 마법사는 이미 리그 조회 + 번들 실행으로 왕복을 쓰며, 조회를 별도 모델 왕복으로 빼면 모델이 `look_id` 9개를 재타이핑하는 지점이 생긴다 — `tools.py:735-738`이 리그에 대해 금지한 재타이핑과 같은 부류의 노출이다.
- **채택 대안**: `LookLibrary.looks` 직접 순회(결정 G). `LookLibrary`에 `by_id` 외 조회 API가 없다는 사실(`schema.py:119-130`)이 이것이 유일한 읽기 전용 경로임을 보증하며, 정렬은 기존 `_ranked` 타이브레이크(`matching.py:294-297`)와 동일 규칙을 쓴다.

### 기각 (b) — `PoolIndex`/`PoolBinding`을 mutable로 개정해 슬롯을 전진시킨다

- **내용**: `instantiate.py:78-79`, `:96-97`의 `frozen=True`를 풀고 `_plan_stores`가 `binding.occupied`에 방금 청구한 슬롯을 추가하게 한다. 코드 변경량이 가장 작다.
- **기각 사유**:
  1. **`build_instantiation`이 순수 함수가 아니게 된다.** 현재는 같은 `(look, resolution, pools)`에 항상 같은 결과를 낸다 — 이것이 §3의 인메모리 재현을 가능하게 한 성질이다. 인자를 변형하기 시작하면 **호출 순서가 결과를 바꾸고**, 같은 인자로 두 번 호출한 결과가 달라진다. 라이브러리 계층은 이 순수성을 명시적 계약으로 세웠다 — `match_looks` docstring `matching.py:310-313` "Pure: the only inputs are the query and the library handed in, so **the same pair always yields the same result**".
  2. **예약된 소비 계약을 조용히 바꾼다.** `build_instantiation`의 키워드 전용 `resolution`/`pools`(`:416-423`)가 LOOKLIB이 P1-1·P1-2 **둘 다**를 위해 예약한 API 형상이다(`SPEC-COPILOT-LOOKLIB-001/spec.md:70`, `research.md:226`). 파라미터의 가변성 여부는 시그니처에 드러나지 않으므로, P1-1이 나중에 같은 함수를 쓰면서 "인자가 변형된다"는 사실을 모르는 것이 기본값이 된다. 룩 스키마가 두 소비자의 공통 기반이라 파괴 변경이 둘을 함께 깨뜨린다는 `schema.py:20-25`의 `@MX:NOTE`와 정확히 같은 위험 구조가 인스턴스화 API에도 적용된다.
  3. **단일 룩 경로에 회귀를 만든다.** 출하된 `instantiate_look` 툴(`tools.py:698-806`)과 그 테스트가 현재 동작을 고정하고 있고, 이 개정은 그것들을 함께 건드린다 — 본 SPEC이 "신규 실행 표면 0, 기존 파이프라인 전면 재사용"(`spec.md §A 개요`)으로 좁힌 범위를 벗어난다.
  4. **PRESERVE가 이 기각을 기계로 강제한다 (v0.1.3 갱신)**: v0.1.2까지 본 항목은 "`server/looks/instantiate.py`는 PRESERVE 목록에 **없으므로** 이 기각은 PRESERVE 논거가 아니다"라고 적었다. **정본 v0.1.3이 이 파일을 PRESERVE에 넣으면서 그 단서는 뒤집혔다.** 다만 위 세 사유는 그대로이고 결론도 그대로다 — 바뀐 것은 **강제 수단이 생겼다**는 점이다. 정본의 사유가 정확히 §7(b)의 논리다: 결정 E는 "frozen 자료구조를 **바깥에서 감싼다**"는 형상이고, 그것이 성립하지 않아 `PoolIndex`/`PoolBinding`/`_plan_stores`를 고치게 되는 경우가 곧 **결정 E의 반증**이므로, 파일을 PRESERVE에 두면 그 반증이 **diff로 즉시 드러난다**(`AC-BUSKWIZ-014`). 목록에 없었다면 조용히 개정하고 지나갈 수 있었다.
- **채택 대안**: 원장을 **바깥 계층**에 둔다(결정 E). 룩마다 그 룩용 `PoolIndex`를 **새로** 만들어 넘기면 `build_instantiation`은 순수한 채로 남고, 누적 상태는 조율 계층이 소유한다. frozen 계약도 소비 계약도 건드리지 않는다.

### 기각 (c) — `_PROGRAMMER_STATE_COMMANDS`에 `ChangeDestination Root` 면제를 추가

- **내용**: `tools.py:227-231`의 면제 집합에 네 번째 패턴을 넣어, 룩별 번들을 단순 연접해도 dedupe에 걸리지 않게 한다.
- **기각 사유**:
  1. **라이브 관측상 불필요하다.** LOOKLIB M7에서 `ChangeDestination Root` 1건이 dedupe로 탈락했음에도 **두 번째 번들은 정상 왕복했다**(`SPEC-COPILOT-LOOKLIB-001/progress.md:799-807`). 목적지 상태가 세션에 남기 때문이다. 즉 이 면제는 관측된 고장을 고치는 것이 아니라 **관측되지 않은 고장을 예방하는 것**이며, 그 대가로 아래 비용을 치른다.
  2. **번들 문자열과 콘솔이 받은 것의 불일치를 방치한다.** 면제를 넣어도 연접 번들은 여전히 `ChangeDestination Root`를 N번 담고, N-1번은 무의미하게 재실행된다. AC-BUSKWIZ-017 ①이 요구하는 `console.executed == plan.commands`는 만족되지만, **번들이 룰북의 "exactly once at the start of the bundle"(`31_choreography_patterns.md:11`)에서 벗어난 상태 자체는 남는다.**
  3. **면제 집합 확장의 선례 비용.** LOOKLIB M4 후속이 이 집합의 원칙을 명문화했다 — "dedupe는 **영속 산출물**의 중복을 막는 장치이고, 프로그래머 상태를 세우는 커맨드는 중복시킬 산출물이 없다 ... 면제 집합은 열거형이며 커맨드의 **선두 토큰**에 고정된다"(`progress.md:1320`). 같은 문서가 `Select` 접두형을 면제하지 않는 이유까지 근거와 함께 남겼고, 그 이유를 적은 목적이 "다음 사람이 이것을 스타일 선호로 재론하지 않게" 하기 위함이라고 명시했다(`:1324`). 근거 없는 확장 1건이 그 규율을 "멤버십을 외워야 하는 목록"으로 퇴화시킨다.
  4. **PRESERVE 범위와 충돌한다.** spec.md §A(`:53`)와 §D(`:146-148`)가 `_PROGRAMMER_STATE_COMMANDS`(`tools.py:227-231`)와 dedupe 블록(`:518-550`)을 무변경으로 두고, `tools.py` 변경을 신규 툴 등록으로 한정했다. AC-BUSKWIZ-014의 추가 assert가 이를 기계 확인한다(`AC-BUSKWIZ-014`).
- **채택 대안**: 번들 형상 쪽에서 해결(결정 F, REQ-BUSKWIZ-006) — `ChangeDestination Root`가 문자열로 1회만 존재하면 dedupe 판정(`tools.py:537`)의 대상 자체가 없다. 코드 개정 0.

### 기각 (d) — 룩 단위 분할 승인 (또는 dry-run 선보고)

- **내용**: 6~10룩을 룩마다 별도 번들로 스크리닝해 승인 카드를 6~10회 띄우거나, 실행 전 전체 계획을 먼저 보고하고 두 번째 왕복에서 실행한다.
- **기각 사유**: **사용자 확정 ③으로 기각되었다**(`spec.md §A 사용자 확정 ③`). 근거는 "마법사의 가치가 '한 마디에 일괄'이므로 룩 단위 분할 승인(6~10회 왕복)은 기능 자체를 무력화한다"이며, 이 SPEC의 출처인 제안서가 요구한 것도 정확히 "**한 마디에** 일괄 생성"이다(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:78`).
  - **반대 논거는 기각되지 않고 수용된 위험으로 존치한다**: 긴 프리뷰는 사람이 실질 검토하기 어렵다. 이 논거는 대안(룩 단위 분할 / dry-run 선보고)과 함께 사용자에게 제시되었고, 사용자는 그것을 알고 단일 승인을 선택했다(`spec.md §A "수용된 잔여 위험"`). 따라서 design.md §4에 **표면화된 뒤 수용된 위험**으로 남으며, 완화는 REQ-BUSKWIZ-013의 집계 보고가 담당한다. §4의 실측(상한 87행)은 이 위험의 **크기를 정정**할 뿐 결정을 재개봉하지 않는다.
  - 부차 근거: 분할 승인은 §3 장애물 1을 해소하지 못한다. 승인을 N번 나눠도 하나의 `PoolIndex`를 재사용하면 슬롯은 그대로 겹치고, 해석을 N번 다시 하면 REQ-BUSKWIZ-004(쿼리 9배, §4)를 포기하게 된다.

### 기각 (e) — 신규 실행 표면(전용 REST 엔드포인트 / `execution_port` 직접 접근)으로 대량 번들 처리

- **내용**: 87줄 번들을 채팅 툴 왕복 대신 전용 경로로 흘려 타임아웃·절단 위험을 줄인다.
- **기각 사유**: `gate.py:263-264`의 `@MX:REASON`이 구성상 금지한다 — "exactly ONE screening path may exist; a second entry would be a gate bypass **by construction**". 룩 계층이 같은 유혹을 명시적으로 거절한 기록도 있다(`tools.py:692-696` — "Reaching execution_port directly from here would be the second path the SPEC forbids, and it would be **invisible to the gate**"). REQ-BUSKWIZ-011과 REQ-BUSKWIZ-012가 이를 계승하고 AC-BUSKWIZ-009 구간 1의 AST 스캔이 기계 확인한다(`AC-BUSKWIZ-009 구간 1`). 번들 규모 문제의 정당한 처리처는 **ASSUMPTION-18의 M0 실측**이지 게이트 우회가 아니다.

### 채택 — 출하된 룩 파이프라인 위의 **무상태 조율 계층** + 슬롯 원장 + 단일 번들

- **조회**: `LookLibrary.looks` 읽기 전용 순회(결정 G), 별칭은 `matching.GENRE_ALIASES`(`matching.py:73-90`) 재사용, 정렬은 `_ranked` 타이브레이크와 동일 규칙(`:294-297`).
- **해석**: `resolve_roles`(`resolver.py:121`) 1회 + `resolve_pools`(`instantiate.py:217`) 1회, 리그는 툴 핸들러가 `collect_rig_sections`로 직접 읽는다(`tools.py:366-416`, 선례 `:739-744`).
- **계획**: 풀 패밀리별 슬롯 원장을 조율 계층이 소유하고(결정 E), 룩마다 그 시점 상태를 반영한 `PoolIndex`를 만들어 순수한 `build_instantiation`(`instantiate.py:416-423`)에 넘긴다. 원장의 시작값은 항상 콘솔이 보고한 `occupied`이며 미관측 풀은 `NO_FREE_SLOT`으로 남는다(`:346-357`).
- **결합**: `ChangeDestination Root` 선두 1회 + 룩 단위 `ClearAll` 규율 유지(결정 F, 룰북 `31_choreography_patterns.md:11`, `:40-41`). 단순 연접 금지.
- **실행**: 신규 툴 1종 → `run_commands` 재진입 → `gate.screen()`(`tools.py:686-696` 선례, `gate.py:265`). 신규 실행 표면 0.
- **보고**: 집계 + 룩별 2단, 건너뜀 단위는 프리셋 저장 1회, 실행 시점 실패 전파(`tools.py:527-536`)까지 룩별 판정에 반영. 한국어는 표현 계층에서 매핑하고 자산·스키마는 무변경.

---

## §8. 핵심 참조 파일

| 파일 | 역할 |
|---|---|
| `server/looks/schema.py` | in-scope 풀 4종 상수(`:58`)와 속성→패밀리 라우팅(`:62-69`) — 본 SPEC이 **import해 쓰는** 팔레트 축. `LookLibrary`는 `by_id`만 갖는 순회 대상(`:119-130`), 패밀리 분해 함수(`:133-147`), P1-1/P1-2 공통 기반 경고(`:20-25`). **PRESERVE** |
| `server/looks/instantiate.py` | 재사용 대상 번들 빌더(`:416-423`, 키워드 전용 `resolution`/`pools`가 예약된 API 형상). **장애물 1의 진원** — frozen `PoolBinding`/`PoolIndex`(`:78-79`, `:96-97`), 전진 없는 `_first_free_slot`(`:307-312`, **상한 없음** — §9.4), 읽기만 하는 `_plan_stores`(`:346`, `:358`), 라벨 기반 충돌(`:359-371`). **장애물 2의 진원** — `_bundle`이 룩마다 `_DESTINATION`을 선두에 붙임(`:395`). 미관측≠빈 풀(`:82-85`, `:193-214`), 라벨 인용 불가 예외(`:315-322`), 조용한 파괴 경고(`:294-299`). **v0.1.3부터 PRESERVE** — 결정 E의 반증을 diff로 드러내기 위함(§7(b) 4항) |
| `server/looks/resolver.py` | `resolve_roles`(`:121`) — 1회 해석의 절반. 번호 날조 금지 `@MX:WARN`(`:113-120`), `UNADDRESSABLE` 정의(`:50`), 섹션 실패 사유의 역할 전파(`:128-137`). **PRESERVE** |
| `server/looks/roles.py` | 6역할 폐쇄 집합(`:44-76`), `AMBIGUOUS`(`:22`) / `NO_MATCH`(`:23`) — 미매핑 사유 3종 중 2종의 실제 정의처. **PRESERVE** |
| `server/looks/matching.py` | `GENRE_ALIASES`(`:73-90`)와 `resolve_genre`(`:197-207`) — 재사용 대상. **`MAX_TOOL_MATCHES = 8`(`:71`)과 `to_dict` 절단(`:279-291`)이 기각 (a)의 근거.** 결정론적 타이브레이크(`:294-297`), 별칭을 자산이 아닌 코드에 두는 이유(`:16-19`), 순수성 계약(`:310-313`). **PRESERVE** |
| `server/looks/loader.py` | 기본 라이브러리 경로(`:34`), 디렉터리 로드(`:217-220`, `look_id` 전역 유일성). **PRESERVE** |
| `server/looks/library/*.yaml` | 32룩 — worship 8 / rock 8 / ballad 7 / edm 9. 표시 이름 중복 0, 작은따옴표 0(§2 실측). **PRESERVE** |
| `server/orchestrator/tools.py` | 툴 등록 3지점(`:40-47` / `:808-1051` / `:1052-1060`)과 `build_toolset`(`:448`). **dedupe 블록(`:518-550`, 시드 `:526`, 판정 `:537`)과 면제 집합(`:227-231`) — 무변경 대상.** **stop-on-first-failure(`:527-536`)** — 실행 시점 부분 성공의 기제. 리그 수집(`:366-416`)·드릴 예산(`:322-363`, 상한 `:112`)·룩 섹션(`:118`, `:124`). 룩 툴 선례: `find_looks`(`:660-682`), `instantiate_look` 앵커(`:686-696`)·리그 직접 읽기(`:735-744`)·`run_commands` 재진입(`:791-794`)·툴 설명문 밀도(`:977-1050`). "추측된 경로" 사고(`:77-79`). **변경은 신규 툴 등록으로 한정** |
| `server/rulebook/assets/v2.4.2/31_choreography_patterns.md` | **라이브 검증을 선언하는 유일한 룰북 파일**(`:7`). `ChangeDestination Root` 선두 1회 규율(`:9-23`, 특히 `:11`), `ClearAll` 규율(`:40-41`), 익스큐터 바인딩의 유일한 검증 형식(`:99`, Lua 재등장 `:168`), `Executor <n>` 명시 지시(`:104`). **PRESERVE** |
| `server/rulebook/assets/v2.4.2/00_grammar.md` | dotted 주소형의 문법서측 출처(`:19`, `:47`, `:51`, `:52`, `:70`, `:71`) — 라이브 검증 표시 없음. **큰따옴표 금지(`:26-29`)** — `corpus.yaml:99`가 깨진 형태임의 근거. `Store Preset`/`Label Preset` 레시피(`:67-68`), `Clear`/`ClearAll`(`:57-58`). **PRESERVE** |
| `server/rulebook/assets/v2.4.2/10_object_model.md` | 프리셋 = 패밀리별 풀 + `Preset <pool>.<slot>`(`:18-20`), 패밀리 경계(`:38-40`), **익스큐터의 `Page <page>.<executor>` 진술(`:23-25`) — 라이브 검증 표시 없음**. **PRESERVE** |
| `server/measurement/corpus.yaml` | 페이지 커맨드의 **유일한** 리포지토리 등장처(`:84`, `:90`, `:98-99`, `:105`, `:146`, `:153`)이며 스스로 mock 전용임을 선언(`:7-10`). ASSUMPTION-16이 "근거 0건"인 이유의 실물. **ASSUMPTION-19 쪽으로는 이 파일조차 침묵한다** — mock 자산에도 프리셋을 익스큐터에 얹는 형태는 0건이다 |
| `server/web/dash.py` | 익스큐터 번호 확인 경로(`:129-142`)와 검증된 번호의 유일 출구(`:309-327`). `page*100+slot`의 페이지 1 한정 실측(`:145-163`, 특히 `:150-152`). **ASSUMPTION-17의 형태** — 존재하는 자식만 열거(`:200-206`), 빈 익스큐터에 대응하는 표현 부재(`:227-230`, `:238`) |
| `server/web/session.py` | 프리뷰가 스크리닝을 감싸는 래퍼(`:149-166`, 본문 `:162-166`)와 툴셋 주입(`:211-217`, 인자 `:214`). "두 번째 콘솔 경로를 만들지 않는다"의 배선측 근거(`:218-220`) |
| `server/web/preview.py` | 커맨드별 severity 분류(`:99-170`), 풀 인텐시티 `caution`(`:158-169`), 번들 등급 승격(`:198-204`). 버스킹 번들의 상한이 `caution`인 근거. **PRESERVE** |
| `server/safety/gate.py` | 단일 스크리닝 `@MX:ANCHOR`(`:260-265`), lock-FIRST 파이프라인(`:7-8`), 제안 강등(`:471-474`), 실행 직전 잠금 재확인(`:504-506`, `:550-552`), deny-all 기본(`:145`). **PRESERVE** |
| `server/safety/blacklist.yaml` | `"Store /overwrite"`는 **`:18`**(닫힌 집합 선언 `:3-5`) — REQ-BUSKWIZ-007의 경계 조건. **PRESERVE** |
| `server/safety/lock.py` | `LiveLock`(`:23`, `:30`)과 `ProposalCard`(`:15-19`) — REQ-BUSKWIZ-014가 소비. **PRESERVE** |
| `console/lua/copilot_responder.lua` | `EXECUTOR_ADDRESS_PATTERN`(`:405`)과 "유일하게 특수 처리되는 주소형" 주석(`:397-404`) — dotted form이 응답기에서 해석되지 않는 근거. **PRESERVE** |
| `server/llm/types.py` | `ToolDefinition` 3필드 계약(`:16-26`) — 신규 툴 등록의 형식 |
| `server/web/panel.py` | 재생 커맨드 생성(`:592-593`)과 콘솔 키워드 표(`:550`) — 코드가 `Executor <n>`만 쓴다는 증거 |
| `server/orchestrator/last_created.py` | 인식 대상 커맨드 형태 목록(`:13`, `:15`) — 같은 증거의 두 번째 지점 |
| `server/tests/test_safety_classify.py` | `Assign Sequence 1 At Executor 201` = `safe` 고정(`:152`) — GO 분기에서 바인딩 커맨드가 승인 보류를 유발하지 않음의 근거 |
| `SPEC-COPILOT-LOOKLIB-001/spec.md` | 예약 조항(`:70`, `:180-182`), 빈 익스큐터 탐색 Out of Scope(`:186`), Position 풀 제외(`:57`, `:192-194`), 무브먼트 제외(`:62`, `:196-199`), 건너뜀 단위(`:65`), 빔 축 GO/DESCOPE 선례(`:45` 대응 절) |
| `SPEC-COPILOT-LOOKLIB-001/progress.md` | **dedupe 탈락의 라이브 관측**(`:799-807`, `:1167-1170`), `ClearAll` 4/4 보존(`:1171-1173`), **21줄 무손실 왕복 실측**(`:1326`), dedupe 개정 판단 이관(`:1330`), 면제 원칙 명문화(`:1320`, `:1324`), dotted form의 창발 발화와 그 배제(`:790-791`, `:862`), M7 문법 최초 검증 목록(`:1174-1179`) |
| `SPEC-COPILOT-LOOKLIB-001/research.md` | 소비 계약 원문(`:226`) — 본 SPEC의 발주서 |
| `SPEC-COPILOT-EXECBODY-001/spec.md` | 역주소 문제 실측 표본(`:43`), `REQ-EXECBODY-007`(`:69`)·`REQ-EXECBODY-008`(`:70`)의 하드코딩 금지 — REQ-BUSKWIZ-017의 상위 규범 |
| `SPEC-COPILOT-EXECBODY-001/acceptance.md` | `AC-EXECBODY-010`(`:117-123`) — GO/DESCOPE 양 분기 판정의 선례 |
| `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` | P1-2 원문(`:76-80`), P1-3 공통 기반 진술(`:86`) |
| `.moai/project/product.md` | Phase 2 성공 기준·"프리셋 어휘 온보딩 마법사"(`:38`), Phase 3 룩 템플릿(`:39`), Phase 4 버스킹 행의 TBD(`:40`), 비목표(`:44-45`) |

---

## §9. 알려진 미결 지점 — **7건 → 0건**

**최종 상태: 미결 0건.** 결정 7건(A~G)이 전부 폐쇄되었고, 본 문서에는 미해결 clarification 마커가 하나도 없다(전수 스캔 0건). ASSUMPTION-16/17/18/19는 미결이 아니라 **M0가 실측할 대상**이며, 그 판정이 어느 쪽이든 정의된 결과(GO 또는 DESCOPE)로 이어지도록 REQ-BUSKWIZ-016과 AC-BUSKWIZ-012가 양 분기를 미리 규정해 두었다. **아래 §9.1~§9.3은 결정·사실의 폐쇄 이력이고, §9.4는 종류가 다른 항목 — 요구 자체가 충족 불가능하게 쓰여 있던 정합 결함 1건 — 의 폐쇄 이력이다.**

### §9.1 해소된 것 — 사용자 사전 확정 4건 (결정 A~D)

| 항목 | 폐쇄 경로 | 최종 결정 | 본 문서의 조사 기여 |
|---|---|---|---|
| **A. 익스큐터 페이지 레이아웃** | 사용자 확정 ① | **M0 라이브 프로브 GO/DESCOPE 게이트**(v0.1.2에서 3항 논리곱 16 ∧ 17 ∧ 19로 강화). 하나라도 부정이면 v1은 익스큐터·페이지 커맨드 0건 | §5가 근거 지형을 3분류로 확정 — 저작 문법 0건, dotted form은 문법서 유래, `At Executor`만 라이브 검증. ASSUMPTION-17이 "판별 부실"이 아니라 "물을 방법 부재"임을 `dash.py:200-206`, `:227-230`으로 특정. v0.1.2에서 **목적어 타입 축**을 추가해 ASSUMPTION-19 근거 행 2개를 보강(§9.4) |
| **B. 팔레트 축** | 사용자 확정 ② | LOOKLIB `IN_SCOPE_POOL_FAMILIES` 4종 그대로 상속(`schema.py:58`). 포지션은 선행 SPEC이 닫음 | §2가 상수 1개 + 라우팅 6항목이 전부임을 확인 — 재정의할 표면 자체가 없다. `payload_for_family`(`:133-147`)의 합집합 보증이 "값 누락 없음"의 기계 근거 |
| **C. 실행 단위** | 사용자 확정 ③ | 단일 번들 · 승인 1회 · 부분 성공 구조화 보고 | §4가 번들 규모를 57~87줄로 실측해 잔여 위험의 크기를 정정. §7(d)가 반대 논거를 수용된 위험으로 존치 |
| **D. 라이브 세션** | 사용자 확정 ④ | 2회 — M0 프로브 + M7 종단 | §4·§5가 M0의 측정 항목 **4건**을 구체적 수치·질의로 환원(87행 번들 / 페이지·익스큐터 저작 문자열 / 빈 익스큐터 질의 존재 여부 / 프리셋을 익스큐터에 얹는 문법) |

### §9.2 남아 있던 3건 → 전부 폐쇄 (결정 E~G, 엔지니어링 판단)

| 미결 | 폐쇄 경로 | 최종 결정 | 근거 |
|---|---|---|---|
| **E. 다중 룩의 슬롯 충돌을 어디서 막는가** | 엔지니어링 판단 | 풀 패밀리별 **누적 슬롯 원장**을 조율 계층이 소유. 시작값은 콘솔 관측 점유이며 미관측 풀을 비었다고 가정하지 않는다 | §3 장애물 1 — 결함을 실행으로 재현(16건 저장 → 목적지 2개). §7(b)가 대안(mutable 개정)을 순수성·소비 계약·회귀 범위 3사유로 기각 |
| **F. `ChangeDestination Root` dedupe 탈락을 코드로 고치는가** | 엔지니어링 판단 | **`tools.py` dedupe 규칙 무개정.** 장르 번들이 선두 1회만 발화하는 형상으로 회피 | LOOKLIB M7 라이브 관측(`progress.md:799-807`) — 탈락에도 두 번째 번들 정상 왕복. §7(c)가 면제 확장을 4사유로 기각. 룰북 `31:11`이 이미 같은 형상을 지시. 선행 SPEC이 이관한 판단(`progress.md:1330`)에 대한 답 |
| **G. 장르 룩 조회를 어느 경로로 하는가** | 엔지니어링 판단 | `LookLibrary` 직접 순회 | §7(a) — 툴 경로는 `to_dict(limit=8)`(`matching.py:279-280`)에서 EDM 9룩 중 1건을 자른다. 부가 사유 2건(다중 장르 언급 시 필터 소실 `matching.py:206-207`+`:326`, 모델 재타이핑 노출 `tools.py:735-738`) |

### §9.3 미결이 아니었으나 결정도 아니었던 항목 — 본 문서가 열었고, 정본 v0.1.1이 받았다

LOOKLIB이 남긴 교훈(**"미해결 마커로 표시되지 않은 미결이 마커로 표시된 미결보다 위험하다"** — `SPEC-COPILOT-LOOKLIB-001/research.md:220`)을 그대로 적용해, 마커도 결정도 아닌 채 하류로 번질 뻔한 항목 3부류를 v0.1.0에서 열었다. **셋 다 정본 v0.1.1이 채택했으므로 아래는 "열린 항목"이 아니라 처리 이력이다** — 미결로 오독하면 run-phase가 같은 조사를 반복한다.

1. **번들 규모의 실수치 → `spec.md §A "번들 규모의 실측"` 채택.** 당시 정본의 "최대 약 40여 커맨드"는 쌍(pair) 수 추정치였고 행 수 실측은 §4 표와 같다. 기록되지 않았다면 AC-BUSKWIZ-016 측정 항목 3이 40줄짜리 프로브로 GO를 선언하고 EDM에서 47줄이 미검증으로 남았을 것이다. **처리**: 정본이 §A 실측 절 · ASSUMPTION-18 · `AC-BUSKWIZ-016 측정 항목 3`을 **87행**으로 고정했다. REQ·AC 집합 무변경. 부산물로 `REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)`이 per-family 형상을 닫았고, 그 근거는 규모가 아니라 값 라인 충돌이었다(§4 함의 3 — 본 문서가 교차 확인).
2. **실행 시점 부분 성공(stop-on-first-failure) → REQ-BUSKWIZ-013 (e) 신설로 채택.** `tools.py:527-536`은 첫 실패 이후 전부를 `not_executed`로 만든다. 당시 정본의 "부분 성공"(REQ-BUSKWIZ-010)은 **빌드 시점 건너뜀만** 다뤄, REQ-BUSKWIZ-013 (d)의 룩별 판정이 **계획 결과만으로는 산출 불가**라는 사실이 어디에도 없었다. **처리**: 보고 요소 **(e) 미실행 커맨드 수**가 신설되고 `REQ-BUSKWIZ-013 하위 절((c)와 (e) 합산 금지)`이 합산을 금지했으며 `AC-BUSKWIZ-008 구간 6`이 이를 기계 판정한다. 룩별 판정은 계획(`created`/`skipped`)과 실행 결과(per-command status)의 **대조**로 산출한다 — `instantiate_look`이 `payload["executed"]`와 `payload["report"]`를 함께 싣는 선례(`tools.py:795-797`)가 그 재료 형상이다.
3. **코드 앵커 드리프트 → 정본이 전건 정정.** 본 문서가 v0.1.0에서 5건을 보고했고 정본 v0.1.1이 전부 받았다 — `server/safety/blacklist.yaml:19`→**`:18`**(REQ-BUSKWIZ-007이 정정된 줄을 인용하며 `blacklist.yaml:19`가 `Shutdown`임을 함께 명기), `server/orchestrator/tools.py:53-55`→**`:77-79`**(REQ-BUSKWIZ-008이 "인용 정밀도 주석"으로 사유까지 기록), `server/looks/resolver.py:70`→**`roles.py:22-23` + `resolver.py:50` + `resolver.py:128-137`**(REQ-BUSKWIZ-013 하위 절 (b)의 사유 5종). 아래 표는 **원인 유형별 기록**으로 남긴다 — 같은 드리프트가 다시 생길 때 진단 순서가 된다.

   | 정본의 인용 | 현재 트리의 실제 위치 | 원인 |
   |---|---|---|
   | `server/orchestrator/tools.py:53-55` ("추측된 경로는 죽은 채 출하된다") | **`:77-79`** | 룩 툴 2종 추가로 상단 주석 블록이 확장됨 |
   | `tools.py:65-76`(경로) / `:81`(드릴다운) / `:88`(쿼리 상한) — LOOKLIB 계승 | **`:89-100` / `:105` / `:112`** | 동일 |
   | `server/safety/blacklist.yaml:19` (`Store /overwrite`) | **`:18`** (`:19`는 `"Shutdown"`) | 한 줄 오프셋 |
   | `server/looks/resolver.py:70` (미매핑 사유 3종) | **`roles.py:22-23` + `resolver.py:50`** (`:70`은 `UnmappedRole` docstring). 또한 `UnmappedRole.reason`이 실제로 담을 수 있는 값은 **5종** — 판정 3종 + 섹션 실패 사유 2종 전파(`resolver.py:128-137`) | 상수 정의처와 클래스 정의처의 혼동 |
   | `server/web/session.py:161-165`(래퍼) / `:213`(주입) | **`:162-166` / `:214`** | 한 줄 오프셋 |

   부수 관측 1건: `instantiate.py:301-303`의 주석이 additive 선택형(`Group 11 + 12`)을 "grammar-derived and awaits the M7 live session"이라 적고 있으나, **M7이 이를 라이브 검증했다**(`SPEC-COPILOT-LOOKLIB-001/progress.md:1175-1176` — "OK x 2회"). 출하 코드의 주석이 M7 기록보다 낡았다. 본 SPEC은 그 파일을 고치지 않으므로 사실만 기록한다 — 조율 계층은 이 선택 라인을 그대로 소비하며, 라이브 근거는 주석이 아니라 M7 기록 쪽이 최신이다.

### §9.4 요구 정합 결함 **2건** — plan-phase에서 발견·폐쇄 (정본 v0.1.2 · v0.1.3)

**§9.1~§9.3과 종류가 다른 항목이다.** 앞의 것들은 "정해지지 않은 결정"이거나 "기록되지 않은 사실"이었지만, 여기 둘은 **요구 자체가 충족 불가능하게 쓰여 있던 결함**이다. 미결 마커로도, 결정 공백으로도 잡히지 않는 부류다 — 문장은 완결돼 있고 근거도 달려 있는데 **전제가 성립하지 않는다.** 둘 다 REQ·AC 개수를 바꾸지 않고 **문언 교체만으로** 닫혔다는 점도 같다.

#### 결함 ① — REQ-BUSKWIZ-016의 GO 분기에 얹을 대상이 없었다 (정본 v0.1.2 → ASSUMPTION-19)

- **결함의 형태**: v0.1.1까지의 REQ-BUSKWIZ-016은 "ASSUMPTION-16 ∧ 17이 둘 다 GO이면 팔레트에 대응하는 익스큐터 레이아웃을 생성한다"였고, 발화 형식으로 라이브 검증된 `Assign Sequence <n> At Executor <m>` 하나를 지정했다. 그런데 **그 커맨드의 목적어는 시퀀스**이고(`31_choreography_patterns.md:99`), 본 SPEC의 산출물은 **프리셋**이며, §D는 시퀀스·큐 생성을 범위 밖으로 두었다. 즉 게이트가 열려도 **얹을 대상이 없다.** 두 ASSUMPTION이 모두 GO인 세계에서도 요구는 충족 불가였다.
- **왜 v0.1.0에서 걸리지 않았는가 (본 문서의 몫)**: §5는 익스큐터 문법의 근거 지형을 3분류로 정리하면서 **"어떤 주소형이 검증되었나"**만 물었고 **"그 커맨드가 무엇을 목적어로 받나"**는 묻지 않았다. 분류 축이 주소형이었기 때문에 목적어 타입 불일치가 표의 어느 칸에도 들어가지 않았다. §5의 3분류 표는 그 자체로는 정확했으나 **REQ-BUSKWIZ-016의 충족 가능성을 판정하기에는 축이 하나 모자랐다** — 이것이 본 문서가 놓친 지점이다.
- **폐쇄 경로**: 정본 v0.1.2가 **ASSUMPTION-19**("팔레트를 익스큐터에 얹는 문법이 존재하는가")를 신설하고 REQ-BUSKWIZ-016의 게이트를 **3항 논리곱**(16 ∧ 17 ∧ 19)으로 바꿨다(`REQ-BUSKWIZ-016`과 그 하위 절(ASSUMPTION-19 추가 사유 · 우회 금지), 전제 본문은 `ASSUMPTION-19`). acceptance 쪽은 `acceptance.md §B 시나리오 6` · `AC-BUSKWIZ-012` 문형 · `AC-BUSKWIZ-016 측정 항목 4`로 반영됐다. **REQ 20건 · AC 17건 · 결정 A~G는 무변경**이다.
- **본 문서의 독립 재확인 (§5에 반영)**: `Assign Preset` · `Store Executor` · `Label Executor` · `Preset <p>.<s> At …`는 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/`에서 **각각 0개 파일**이고, 리포지토리의 **모든** `At Executor` 발생의 목적어가 예외 없이 `Sequence`다. 더해서 룰북이 아는 프리셋 동사는 `Store`/`Label`/`Call`/`At` **넷 다 프로그래머 쪽**이며(`00_grammar.md:59`, `:67`, `:68`, `:72`), 룰북 자신이 "프리셋을 어떻게 발사하느냐"에 대해 내놓는 답은 **"큐로 되불러라"**다(`31_choreography_patterns.md:225-227`) — 그 경로가 곧 §D가 닫은 시퀀스·큐 생성이다. 따라서 ASSUMPTION-19의 기본 기대값은 **부정(DESCOPE)**이며, M0는 그것을 뒤집을 기회이지 확인 절차가 아니다.
- **우회 금지가 요구에 박힌 것이 이 폐쇄의 핵심이다**: "문법을 못 찾았으니 시퀀스를 만들어 얹자"는 자연스러운 다음 수인데, 그 순간 §D가 배제한 시퀀스 생성이 암묵적으로 범위에 들어온다. `REQ-BUSKWIZ-016 하위 절(우회 금지)`이 이를 명문으로 금지했다 — **답은 DESCOPE이지 범위 확대가 아니다.**
- **교훈 (§9.3의 교훈과 짝을 이룬다)**: §9.3이 "마커로 표시되지 않은 미결이 더 위험하다"였다면, 여기서 얻은 것은 **"근거가 달린 문장이 근거 없는 문장보다 위험할 수 있다"**이다. REQ-BUSKWIZ-016은 라이브 검증된 커맨드를 정확히 인용하고 있었고, 그 인용이 정확했기 때문에 아무도 목적어를 다시 보지 않았다. 조사 문서가 커맨드를 분류할 때는 **주소형만이 아니라 목적어 타입도 축으로 세워야 한다** — §5의 3분류 표에 ASSUMPTION-19 행을 추가한 것이 그 시정이다.

#### 결함 ② — REQ-BUSKWIZ-010의 트리거가 도달 불가였다 (정본 v0.1.3, 감사 D2)

- **결함의 형태**: v0.1.2까지 REQ-BUSKWIZ-010은 "**슬롯이 부족해** 장르의 일부 룩만 저장 가능한 경우"를 트리거로 적었다. **그 상태는 발생할 수 없다.**
- **본 문서의 독립 재확인 (인메모리·정적 실측, 본 plan-phase)**: (i) `_first_free_slot`(`server/looks/instantiate.py:307-312`)은 `slot = 1`에서 시작해 점유 집합에 없을 때까지 `+1` 할 뿐 **상한 검사가 없다** — 어떤 점유 집합을 줘도 반드시 슬롯을 반환한다. (ii) 풀 용량 상수는 `server/`·`console/` 전체에서 **0건**이다(`max_slot` · `pool_size` · `POOL_CAPACITY` · `MAX_SLOT` · `slot_limit` · `SLOT_MAX` 전수 검색). (iii) `_observed_contents`(`:193-214`)는 **점유된 자식의 슬롯·라벨만** 반환하고 풀 크기를 보고하지 않는다 — 즉 런타임에도 상한을 알 방법이 없다. 세 가지가 겹쳐 "슬롯 소진"은 관측될 수도, 시뮬레이션될 수도 없다.
- **왜 위험했는가**: 상한이 없으니 그 트리거를 테스트하려면 **상한을 발명해야** 하고, 그것은 REQ-BUSKWIZ-008이 금지한 per-show 값의 정적 진입이다. 즉 이 문언을 그대로 두면 M2가 "요구를 검증하려다 다른 요구를 위반하는" 자리로 걸어 들어간다.
- **폐쇄 경로**: 정본 v0.1.3이 트리거를 "장르의 룩 중 **일부만 저장 가능한 경우**"로 바꾸고 도달 가능 경로를 명시했으며, **v0.1.4가 그 열거에서 1건을 다시 뺐다**(재감사 D2 부분 닫힘). 최종 열거는 **둘**이다 — (i) 특정 풀만 `pool_unresolved`/`pool_unaddressable`이라 그 풀 대상 저장만 전량 건너뛰어진다, (ii) 콘솔에 같은 이름의 프리셋이 이미 있어 `conflict`로 건너뛰어진다(같은 장르 연속 2회 실행이 그 경우다). 점유 미관측(`no_free_slot`)은 REQ-BUSKWIZ-009가 따로 덮는다. **삭제된 것 — "룩마다 값을 가진 패밀리가 달라 저장 쌍 수가 다르다"는 부분 성공이 아니다**: 값이 없는 패밀리는 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않으므로(`server/looks/instantiate.py:332-334`) 결과는 `planned=P, skipped=0, complete=True`이고 보고할 건너뜀이 없다. 도달 불가 트리거를 도달 가능 트리거로 바꾸면서 **부분 성공이 아닌 것을 하나 끼워 넣은 것**이며, 그 자체가 §9.4 결함 ②와 같은 부류의 재발이다.
- **본 문서에 미친 영향**: §6에서 REQ-BUSKWIZ-010을 "계획 시점의 **슬롯 소진**"으로 요약하던 문장을 "**빌드 시점**의 건너뜀(풀 미해석 · 라벨 충돌)"으로 교체했고, §9.3 항목 2의 같은 표현도 함께 고쳤다. §4의 번들 규모 실측은 영향받지 않는다 — 그 표는 저장 **쌍 수**를 세지 슬롯 상한을 가정하지 않는다.
- **교훈**: 결함 ①이 "**목적어**를 다시 보지 않았다"였다면 이것은 "**트리거가 실제로 발생할 수 있는지**를 묻지 않았다"이다. 두 질문 모두 요구 문장 자체를 읽어서는 나오지 않고 **코드를 열어야** 나온다 — GEARS 문형이 완결돼 있다는 것은 그 문장이 참이라는 뜻이 아니다.

---

## §10. P1-1(송 구조 큐리스트 생성기)과의 관계 — 예약만, 번들하지 않음

**입장이 뒤집혔다.** LOOKLIB research.md §10(`:226`)에서 본 SPEC(P1-2)은 **소비자**였다 — 스키마가 "장르 묶음 인스턴스화를 표현할 수 있는 형상"이기를 요구하는 쪽. 본 SPEC이 그 예약을 실행부로 구현하면, 아직 착수되지 않은 **P1-1에 대해서는 공급자**가 된다. 본 SPEC은 P1-1을 **번들하지 않되**, 조율 계층을 설계할 때 P1-1이 재사용할 수 있는 형상을 의도적으로 남긴다.

**P1-1이 쓸 수 있는 것 3종** (전부 본 SPEC이 새로 만드는 조율 계층의 산물이다):

1. **슬롯 원장 (결정 E)** — P1-1은 곡 1개당 섹션 수만큼(Intro/Verse/Chorus/Bridge…) 룩을 인스턴스화하며, 그 룩들도 하나의 리그 해석 위에서 서로 다른 슬롯을 청구해야 한다. §3 장애물 1은 P1-1에서도 **같은 형태로** 발현한다 — `_first_free_slot`(`instantiate.py:307-312`)은 소비자가 누구든 전진하지 않는다. 원장을 `build_instantiation` 바깥에 둔 §7(b)의 선택이 곧 P1-1이 같은 계층을 그대로 쓸 수 있게 하는 선택이다.
2. **다중 룩 번들 결합 형상 (결정 F / REQ-BUSKWIZ-006)** — "`ChangeDestination Root` 선두 1회 + 룩 단위 `ClearAll` 유지"는 장르에 고유한 규칙이 아니라 **N개 룩을 한 번들로 묶을 때의 일반 규칙**이다(룰북 `31_choreography_patterns.md:11`, `:40-41`). P1-1의 큐리스트 번들도 같은 비대칭을 지켜야 하며, dedupe 면제 집합을 건드리지 않았으므로 P1-1이 물려받는 제약도 동일하다.
3. **집계 + 룩별 2단 보고 형상 (REQ-BUSKWIZ-013)** — 건너뜀 단위가 프리셋 저장 1회이고, 룩별 판정이 `complete`/`partial`/`none` 3값이며, 실행 시점 실패 전파(§6, `tools.py:527-536`)까지 반영한다는 형상은 "N개 룩을 한 번에 처리한 결과를 사람이 읽는 법"의 일반형이다. P1-1은 여기에 **섹션 축**(어느 곡 섹션의 룩이 죽었는가)을 얹으면 된다.

**본 SPEC이 P1-1을 위해 하지 않는 것** (§D 제외 범위 — `spec.md §D "Out of Scope — P1-1 송 구조 큐리스트 생성기"`):

- 음원 분석(구간/BPM/에너지), 타임코드 트랙·섹션 마커 생성, 곡당 시퀀스 자동화. **타임코드 문법은 룰북 `v2.4.2/` 전체에서 0건**이라 별도 라이브 프로브가 선행되어야 한다 — 본 SPEC의 M0가 그것을 대신 측정하지 않는다.
- 시퀀스·큐 생성 전반(`spec.md §D "Out of Scope — 시퀀스 · 큐 생성"`). 시퀀스/큐 저작 문법 자체는 라이브 검증되어 있으나(`31_choreography_patterns.md:43-52`, `:50`), 버스킹 준비의 산출물은 **팔레트**다. REQ-BUSKWIZ-016이 GO되어 익스큐터 바인딩을 하게 되더라도 **바인딩 대상은 본 SPEC이 새로 만든 시퀀스가 아니라 이미 존재하는 오브젝트**여야 한다 — 그렇지 않으면 시퀀스 생성이 암묵적으로 범위에 들어오고, 그것이 곧 P1-1의 영역이다.
- 다이내믹스 축의 확장. P1-1이 소비할 "순서 있는 다이내믹스 레벨"은 LOOKLIB이 이미 스키마에 넣었고(`schema.py:35-36` `DYNAMICS_MIN`/`DYNAMICS_MAX`), 본 SPEC은 그것을 **정렬 키로 읽기만** 한다(§2, `matching.py:294-297`와 동일 규칙). 축을 바꾸지 않으므로 P1-1의 소비 계약은 본 SPEC 전후로 동일하다.

**한 문장 요약**: 본 SPEC은 룩 계층 위에 **"N개 룩을 하나의 안전한 번들로 만드는 법"**을 처음으로 구현하며, 그 계층은 장르(P1-2)로도 곡 섹션(P1-1)으로도 인덱싱될 수 있게 남는다 — 그러나 곡 섹션 쪽 인덱싱과 그에 필요한 음원·타임코드 표면은 별도 SPEC이다.
