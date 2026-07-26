# SPEC-COPILOT-LOOKLIB-001 — 구현 계획 (plan)

status: draft (v0.2.0, 2026-07-26) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음.

> **v0.2.0 — 독립 감사(FAIL 0.65) 반영 개정.** 주요 변경: (a) 미해결 마커 6건 → **3건**(사용자 확정 4건 + 리포지토리 증거 2건으로 폐쇄, 다이내믹스 척도 1건 신설), (b) **M0 라이브 프로브 신설** + M1 분해 — 전제 검증이 그 전제에 의존하는 저작보다 먼저 오도록 순서 교정(감사 D9), (c) §A.4 ↔ design.md §5 대응 관계의 허위 1:1 주장 정정(감사 D6a), (d) 라이브 세션 **2회**로 정정.

## §A. 접근 요약 (Context)

본 절은 **변경 가능성이 높은 결정을 먼저** 배치한다(가장 되돌리기 어렵거나 후속 결정을 규정하는 순서). 빌드 순서(§B)와 다를 수 있다 — §A.2가 그 편차를 설명한다.

### §A.1 결정 우선순위 (리뷰 순서 — 빌드 순서 아님)

| 순위 | 결정 | 위치 | 왜 먼저 검토해야 하는가 |
|---|---|---|---|
| **1위** | **역할 어휘 폐쇄 집합** (§A.4 **마커 1**) | design.md §5.2 슬롯 R1, spec.md REQ-006 | 감사 D3 실측으로 **기존 사전 근거가 없음**이 확인되어, 이 어휘는 신규 창작이다. 스키마의 역할 축·리졸버 휴리스틱·라이브러리 24~40룩의 포지션 필드가 전부 여기에 종속된다 — 사후 변경은 라이브러리 전량 재저작을 유발하므로 **가장 미래-구속적**이다. (v0.1.0은 이를 "M1 설계 산출물"로 이연시켜 Kickoff 게이트를 통과시켰다 — 감사 D6a.) |
| 2위 | **다이내믹스 단계 척도** (§A.4 **마커 2**) | design.md §5.2 슬롯 R2, spec.md REQ-001/002/005 | REQ-005가 "다이내믹스 범위 이탈"을 검증 에러로, AC-002가 "최저~최고 스팬"을 인수 조건으로 삼는데 **척도가 정의되지 않으면 둘 다 평가 불가**다(감사 D8c). P1-1(섹션 에너지 → 룩 선택)의 소비 계약이기도 하다. |
| 3위 | **룩 스키마 형상** — 아이덴티티/장르/다이내믹스/속성/역할 축의 데이터 모델 | spec.md REQ-001~006, plan.md M1 | 마커 1·2가 확정되면 스키마는 그 위에서 결정된다. P1-1·P1-2가 공통 기반으로 소비하므로(research.md §10) 출하 후 파괴 변경은 소비자 2개를 함께 깨뜨린다. |
| 4위 | **역할 매핑 확정 UX** (§A.4 **마커 3**) | design.md §5.2 슬롯 R3, REQ-006~009 | 안전 철학과 왕복 마찰의 트레이드오프 — 단, 방어(미매핑 보고·게이트·프리뷰)는 어느 쪽이든 동일해 상대적으로 가역적. |
| 5위 | 테스트 축·회귀 확장 | plan.md M6 | 기계적 — 상위 결정 확정 후 자연히 따라온다. |

**폐쇄된 결정은 이 표에서 내려왔다.** 저장 형식·매칭 표면·슬롯 배정·산출물 범위·충돌 정책 5건은 §A.4의 "해소된 결정" 절로 이동했다(증거와 함께). 재질의 금지.

### §A.2 빌드 순서 vs 리뷰 순서 — 그리고 M0가 필요한 이유

본 SPEC은 데이터 계층부터 쌓는 순수-우선 구조라 빌드 순서가 결정 우선순위와 대체로 일치한다. 두 가지 편차가 있다:

1. **§A.4 마커 3건은 M1 착수 전(Implementation Kickoff Approval 시점)에 전부 해소**되어야 한다 — 마커 1(역할 어휘)·2(다이내믹스 척도)가 스키마 축 그 자체이기 때문이다.
2. **M0(라이브 프로브)가 M1보다 앞선다** (감사 D9). v0.1.0은 ASSUMPTION-13(명명 관례 실효성)·14(`Store Preset` 캡처 의미론)를 **M6에서만** 검증하도록 배치했다 — 즉 이 전제들에 의존하는 라이브러리 저작(24~40룩)·리졸버·번들 빌더를 **전부 만든 뒤에** 전제를 확인하는 순서였다. 부정 실측 시 되돌릴 작업량이 SPEC 전체와 맞먹는다. 여기에 감사 D2가 ASSUMPTION-15(빔 attribute 문자열 실재)를 추가하면서, "저작 전 실측"이 구조적으로 불가피해졌다. M0는 `SPEC-COPILOT-EXECBODY-001`의 M1 GO/DESCOPE 라이브 프로브 패턴(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123`)을 그대로 계승한다.

### §A.3 정직한 축소 원칙

역할 매핑이 특정 리그에서 전멸(전 역할 미매핑)하더라도 SPEC 실패가 아니다 — 명시적 미매핑 보고 + 폴백(룰북 무드 절)이 정직한 출력이다(REQ-LOOKLIB-009/017). EXECREF/EXECBODY의 "부분 성공을 성공으로 위장하지 않는다" 규율을 계승한다: M6 라이브에서 ASSUMPTION-13(명명 관례 실효성)이 부정으로 실측되면, 그 사실을 progress.md에 기록하고 매핑 휴리스틱 확장을 후속 항목으로 남긴다.

### §A.4 결정 현황 — 해소 7건 / 미해결 3건

> **대응 관계 정정 (감사 D6a).** v0.1.0은 "§A.4 마커 6건 ↔ design.md §5 슬롯 A~F가 1:1"이라고 네 곳(plan.md, design.md ×2, progress.md)에서 주장했으나 **거짓이었다**: 마커 ③과 ④가 함께 슬롯 C 하나로 접혔고(6↔6이 아니라 6↔5), 무엇보다 **슬롯 F(역할 어휘 폐쇄 집합)에는 대응 마커가 아예 없어** "M1 설계 산출물로 확정"으로 이연되어 Kickoff 게이트를 빠져나갔다. 개정 후 대응 관계는 **§A.4 미해결 3건 ↔ design.md §5.2 슬롯 R1/R2/R3가 진짜 1:1**이며, 해소된 결정은 design.md §5.1에 증거와 함께 기록된다(마커 없음 — 마커는 미해결 항목만을 위한 표시다).

#### §A.4a 해소된 결정 (재질의 금지 — 근거 포함)

| # | 결정 | 확정 내용 | 근거 |
|---|---|---|---|
| A | **룩 저장 형식·위치** | **YAML repo 자산** (`server/looks/` 하위) | **리포지토리 증거로 폐쇄**(감사 D6b). `server/safety/blacklist.yaml`이 정확한 선례다 — 정적·repo-shipped·주석을 담는 규칙 데이터. PyYAML은 이미 런타임 의존성(`pyproject.toml:16` `pyyaml>=6.0.3`; 사용처 `server/safety/ruleset.py:16` `import yaml`, `:63` `yaml.safe_load`). v0.1.0이 대안으로 든 JSON 선례(`PinStore`, `server/web/panel.py:186-330`)는 **런타임 사용자 데이터**로 클래스가 다르다 — 정적 규칙 데이터의 선례가 아니다. 사용자 질의 불필요. |
| B | **프리셋 풀 슬롯 배정** | **런타임 빈 슬롯 탐색** (고정 대역 ✗, 설정값 ✗) | 사용자 확정 ⑤. 기존 드릴다운 쿼리 상한(`server/orchestrator/tools.py:88` `RIG_DRILLDOWN_QUERY_CAP = 16`) 안에서 점유 실측. 근거: 검증되지 않은 관례를 하드코딩하지 않는다 — 고정 예약 대역은 그 자체가 미검증 관례다. |
| C | **인스턴스화 산출물 범위** | **프리셋만** (데모 시퀀스 ✗, 익스큐터 바인딩 ✗) | 사용자 확정 ⑥. 익스큐터 주소 체계는 SHOWUI-001·EXECREF-001·EXECBODY-001이 반복해 데인 영역 — v1에서 열지 않는다. spec.md §D에 Out of Scope H3로 등재. |
| D | **기존 프리셋 충돌 처리** | **건너뛰고 명시 보고**("N개 건너뜀"). 덮어쓰기 ✗, 재슬롯 ✗ | 사용자 확정 ⑦. `Store /overwrite`는 블랙리스트(`server/safety/blacklist.yaml:18`) + `server/web/preview.py:113-121`이 `caution`으로 분류. 본 SPEC의 정직한 축소 원칙(§A.3)과 동일 방향. |
| E | **매칭 표면 형상** | **하이브리드** (얇은 룰북 정적 안내 축 + 구조화 조회 툴) | **문서 내 증거로 폐쇄**(감사 D6b). research.md §2 결론 3이 이미 이 형상을 도출했고, v0.1.0 plan.md 자신이 "권고 기본값: 하이브리드"로 기록했다 — 결론이 이미 있는 항목을 마커로 남겨 둔 것이 결함이었다. 제약(고정 프리픽스 byte-stability REQ-022 · 제공자 중립 REQ-016 `server/llm/factory.py:17-28`)은 그대로 유지되며 AC-LOOKLIB-017이 이를 검증한다. |
| F | **빔 축의 처리** | **v1 범위 유지 + M0 라이브 프로브 선행**. 스트로브/셔터는 기본 제외 | 사용자 확정 ④ + 감사 D2/D5. spec.md §A 참조. |
| G | **장르 묶음 인스턴스화** | **런타임 실행 없음** — 스키마 API 형상만 예약 | 감사 D7. REQ-LOOKLIB-010에서 "(또는 장르 묶음)" 제거. spec.md §D P1-2와 정합. |

#### §A.4b 미해결 결정 — Kickoff 전 해소 대상 (design.md §5.2와 1:1)

각 항목은 **구체적 제안 기본값 + 그 근거**를 동반한다 — 오케스트레이터가 그대로 선택지로 구성할 수 있어야 한다.

1. **[NEEDS CLARIFICATION: 역할 어휘 폐쇄 집합의 정확한 구성]** (→ design.md §5.2 슬롯 R1, spec.md REQ-006)
   - **왜 열려 있는가**: 감사 D3 실측 결과 이 어휘는 **기존 근거가 없는 신규 창작**이다. `20_korean_terms.md`(36행)의 showfile 행은 샤막/워시/무빙/스팟/빔/핀조명/객석등 — **픽스처 타입 클래스**이지 공간 포지션 역할이 아니며, `백라이트`/`FOH`/`사이드`/`스페셜`은 리포지토리 전체 **0건**이다. 따라서 "사전을 따르면 된다"가 성립하지 않고, 집합의 크기·경계가 실질 설계 결정이 되었다.
   - **제안 기본값 — 6종 폐쇄 집합**: `백라이트`(back / backlight) · `프론트`(front / FOH) · `사이드`(side) · `탑`(top / downlight) · `배경`(cyc / backdrop — 샤막 포함) · `스페셜`(special / key). 각 역할은 한국어 1급 + 영어 별칭 + 매핑 힌트 문자열(예: 백라이트 ← `Back`, `백`, `Rear`, `BL`)을 갖는다.
   - **6종인 근거**: (a) 너무 넓으면 미매핑률이 올라 정직한 축소가 상시 발동해 기능이 무력해지고, 너무 좁으면 4장르 24~40룩의 표현력이 준다. (b) 6종은 `20_korean_terms.md`의 showfile 행 7종과 같은 자릿수로, 명명 관례 스타일(REQ-006)의 무게감이 일치한다. (c) 6종 각각이 **소규모 리그에서도 그룹 하나로 존재할 개연성**이 있는 굵은 구분이다 — 세분화된 역할(예: `사이드-상수` vs `사이드-하수`)은 매핑 실패를 구조적으로 늘린다.
   - **제안 기본값의 리스크**: ASSUMPTION-13이 M0에서 부정 실측되면(실제 리그 그룹명이 어떤 역할과도 안 맞음) 집합 크기와 무관하게 매핑이 전멸한다. 그 경우에도 실패 방향은 안전하다(REQ-009 명시 미매핑). **집합 확정은 M0 실측 결과를 보고 조정될 수 있다** — Kickoff 결정은 "이 집합으로 시작한다"이지 "불변이다"가 아니다.

2. **[NEEDS CLARIFICATION: 다이내믹스 단계 척도 — 단계 수와 범위]** (→ design.md §5.2 슬롯 R2, spec.md REQ-001/002/005)
   - **왜 열려 있는가**: 감사 D8c. v0.1.0은 다이내믹스를 "순서 있는 축"으로만 규정하고 **척도를 정의하지 않은 채** REQ-005가 "다이내믹스 범위 이탈"을 검증 에러로, AC-002가 "최소 저역…최고역" 커버리지를 인수 조건으로 삼았다 — 둘 다 평가 불가능한 상태였다.
   - **제안 기본값 — 정수 1~5의 5단계**: `1` 정적/앰비언트 · `2` 잔잔함(인트로·벌스) · `3` 중간(빌드업) · `4` 고조(코러스) · `5` 클라이맥스(드랍·엔딩). 스키마 필드는 정수형, 검증 규칙은 `1 <= level <= 5`(REQ-005의 "범위 이탈"이 이 식으로 기계화된다). AC-002의 "스팬"은 **각 장르가 레벨 1~2 중 최소 1개, 레벨 4~5 중 최소 1개를 포함**함으로 판정한다.
   - **5단계인 근거**: (a) 장르당 6~10룩(사용자 확정 ②)을 5단계에 배분하면 단계당 1~2룩으로 자연스럽다 — 3단계면 단계당 2~3룩이 뭉치고, 7단계 이상이면 6룩 장르가 단계를 다 못 채워 AC-002의 스팬 조건이 빈 단계를 만든다. (b) 순서 있는 정수는 P1-1(섹션 에너지 → 룩 선택)이 가장 단순하게 소비할 수 있는 형상이다(research.md §10 (a)). (c) 이름표(잔잔함/클라이맥스)는 §A 사용자 확정 ②의 표현을 그대로 양 끝점으로 쓴다.
   - **대안 축**: 실수 0.0~1.0(무단계) — P1-1이 연속 에너지 곡선을 다룰 경우 더 매끄럽지만, REQ-005의 "이탈" 검증과 AC-002의 "최저·최고 포함" 판정이 모호해지고 룩 저작 시 값을 고르기 어렵다.

3. **[NEEDS CLARIFICATION: 역할 매핑 확정 UX — 자동 휴리스틱+보고 vs 적용 전 사용자 확인]** (→ design.md §5.2 슬롯 R3)
   - **왜 열려 있는가**: 감사 이전과 동일하게 **진짜 열린 트레이드오프**다. 제약: "AI는 초안, 사람이 확정" 철학(product.md §6) vs 지시→실행 왕복 <10초 목표(product.md:37 Phase 1 기준).
   - **제안 기본값 — 자동 휴리스틱 + 적용 전 요약 보고**(별도 확인 왕복 없음): 매핑 결과(역할→그룹 바인딩 + 미매핑 목록)를 요약에 실어 보여주되, 별도의 "확인하시겠습니까" 단계를 넣지 않는다.
   - **근거**: 최종 방어가 **세 겹으로 이미 존재**한다 — (i) `gate.screen()` 3-스테이지(`server/safety/gate.py:260-265`), (ii) 위험 시 승인 카드(deny-all 기본, `server/safety/gate.py:17`), (iii) **스크리닝을 감싸는 실행 프리뷰**(`server/web/session.py:161-165`)가 대상·경고를 콘솔 송신 전에 사용자에게 표시한다. 매핑 확인 단계를 추가하면 이 세 겹 위에 네 번째 왕복을 얹는 것이며, 프리뷰가 이미 "무엇에 무엇을 하는지"를 보여주므로 한계 효용이 낮다.
   - **반대 논거(사용자가 채택할 수 있는 쪽)**: 프리뷰는 **커맨드**를 보여주지 역할→그룹 **매핑 의도**를 설명하지 않는다. `Group 11`이 사용자가 생각한 백라이트인지는 프리뷰만으로 판단하기 어렵다. 매핑이 틀렸을 때의 결과가 "엉뚱한 그룹에 프리셋 저장"이며 이는 쇼파일에 남는 비가역 산출물이다(design.md §4 위험 #1 — 본 SPEC의 유일한 실질 신규 노출면).

### §A.5 PRESERVE 목록 (무변경 대상)

`server/safety/**`(소비만 — gate/classify/blacklist/lock 무수정), `server/bridge/**`, `console/lua/**`, `ui/src/**`, `server/web/panel.py`, `server/rulebook/assembly.py`(자산 추가는 허용 후보, 조립 로직은 무변경), 기존 룰북 자산 5파일 중 4파일(`00_grammar.md` / `10_object_model.md` / **`20_korean_terms.md`(REQ-006이 이 파일 수정을 요구하지 않음 — 감사 D13)** / `30_plugin_patterns.md`)은 **완전 무변경**. `31_choreography_patterns.md`는 §A.4a 결정 E(하이브리드)에 따라 무드 절과의 관계를 밝히는 얇은 안내 축 1곳 추가 가능 — 무드 폴백 절(`:173-206`) 자체는 무변경 보존(REQ-017).

## §B. 마일스톤 (M0..M7)

> **v0.1.0 대비 변경 (감사 D9)**: ① **M0(라이브 프로브) 신설** — ASSUMPTION-13/14/15를 저작 전에 실측. ② **구 M1 분해** — v0.1.0의 M1은 스키마 설계 + 역할 어휘 창작 + 24~40룩 저작 + 로더 + 검증 + 테스트 2파일을 한 마일스톤에 묶은 과적재였다. 이제 **M1(스키마·어휘·로더)** 과 **M2(라이브러리 저작)** 로 분리한다. ③ 이후 마일스톤 번호가 하나씩 밀린다(구 M2~M6 → 신 M3~M7).

### M0 — 라이브 프로브 (실물 onPC, AC-LOOKLIB-020) — **M1의 전제**

**EXECBODY-001 M1 GO/DESCOPE 패턴 계승**(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123`). 코드 변경 없음 — 측정 세션이다.

- **ASSUMPTION-15 (빔 attribute 문자열)**: 후보 문자열 `Attribute 'Zoom'` / `'Focus'` / `'Iris'` / `'Frost'` / `'Prism1'` / `'Shutter'`를 실물 콘솔에 발화하고 수용 여부·값 범위를 관측. 판정: **GO**(≥1개 수용 → 해당 문자열만 REQ-003 구간 3에 진입) / **DESCOPE**(0개 수용 → REQ-001 빔 게이트 발동: 스키마 필드는 정의하되 v1 라이브러리 미사용).
- **ASSUMPTION-14 (`Store Preset` 캡처 의미론)**: 컬러 값만 활성인 프로그래머에서 `Store Preset <pool>.<slot>` → `Label` 후, 저장된 프리셋이 기대 속성만 담았는지 확인. 판정: GO / 형상 수정 필요.
- **ASSUMPTION-13 (그룹 명명 관례 실효성)**: 실물 리그의 groups 목록(`get_rig_context`)을 판독해, §A.4b 마커 1의 제안 6종 역할이 실제 그룹명과 얼마나 매칭되는지 실측. 판정: 매칭 역할 수를 기록(0이어도 DESCOPE가 아니라 **역할 어휘·힌트 문자열 조정 입력**).
- **슬롯 탐색 실현성**(사용자 확정 ⑤ 부수 확인): preset_pools 드릴다운으로 점유 슬롯을 읽어, 쿼리 상한 16(`tools.py:88`) 안에서 빈 슬롯을 판별할 수 있는지 관측. `drilldown_capped` 발생 여부 기록.
- **산출물**: progress.md §E.2에 판정 4건 + 실측 원문(콘솔 응답·감사 로그·GUI 스크린샷)을 **각주가 아니라 명시적 섹션으로** 기록(EXECBODY-001 AC-EXECBODY-013 형식 계승). 부정 실측도 유효한 완료 상태다(§A.3).
- **선행 조건**: 실물 콘솔 실행 + 이름 있는 그룹이 존재하는 쇼파일(GUI 사용자 작업).

### M1 — 룩 스키마 + 역할 어휘 + 로더 (cycle_type=tdd)

- §A.4b 마커 1(역할 어휘)·2(다이내믹스 척도) 확정 결과 + M0 판정을 전제로 **스키마 확정**: 아이덴티티 / 장르 / 다이내믹스(순서 정수 축) / 속성(REQ-003 3구간 어휘) / 역할(폐쇄 어휘) / 무드 키워드·별칭(한국어 1급) / `schema_version`.
- **역할 어휘 모듈**: 확정된 폐쇄 집합 + 한/영 별칭 + 매핑 힌트 문자열. `20_korean_terms.md`는 **건드리지 않는다**(PRESERVE — REQ-006은 스타일 준수만 요구).
- 로더 + 스키마 검증(명시적 에러, REQ-005 — 다이내믹스 범위 이탈은 마커 2가 확정한 식으로 기계화). 전부 순수 함수.
- **라이브러리 저작은 여기에 없다** — M2로 분리(과적재 해소).
- 파일: `server/looks/`(신규 — `schema.py`/`roles.py`/`loader.py`), `server/tests/test_looks_schema.py`.
- **AC**: AC-LOOKLIB-001, AC-LOOKLIB-015.

### M2 — 내장 4장르 라이브러리 저작 (cycle_type=tdd)

- 워십/록/발라드/EDM × 6~10룩, 다이내믹스 척도의 최저~최고 스팬. 값 근거: 룰북 무드 표(`31_choreography_patterns.md:195-202`)와 M0에서 확정된 attribute 문법.
- 저장 형식: **YAML repo 자산**(§A.4a 결정 A) — `server/looks/library/*.yaml`, `blacklist.yaml`과 동일한 주석-담는 정적 규칙 데이터 패턴.
- 전수 검증 테스트: attribute 어휘 한정(REQ-003 3구간), per-show 값 부재(REQ-004), 장르·룩 수·스팬(REQ-002).
- 파일: `server/looks/library/`(자산), `server/tests/test_looks_library.py`.
- **AC**: AC-LOOKLIB-002, AC-LOOKLIB-003, AC-LOOKLIB-004.

### M3 — 역할→리그 매핑 리졸버 (cycle_type=tdd)

- `rig_object`/`rig_section` 형상(`server/orchestrator/tools.py:185-230`)의 groups 데이터를 입력으로, 역할별 후보 그룹을 이름 휴리스틱(M1이 확정한 매핑 힌트 문자열 + M0 실측 조정 결과)으로 결정. 실존 그룹만, 미매핑은 명시 보고(REQ-007~009).
- `truncated`/`path_not_resolved`/`console_unreachable` 전파.
- 파일: `server/looks/resolver.py`(가칭), `server/tests/test_looks_resolver.py`. 콘솔 무접촉(fake rig).
- **AC**: AC-LOOKLIB-005, AC-LOOKLIB-006.

### M4 — 인스턴스화 번들 빌더 + 게이트 배선 (cycle_type=tdd)

- §A.4a 결정 B/C/D를 정책으로 반영: **런타임 빈 슬롯 탐색**(캡 16 내) · **프리셋만** · **충돌 건너뛰기 + "N개 건너뜀" 보고**.
- 번들 규율 기계화: `ChangeDestination Root` 선두, Store 전후 ClearAll, Label, `/Overwrite` 부재(REQ-011/012 — **대소문자 무관 부재 assert**, 감사 D14).
- 결과 요약 보고 형상 구현(REQ-013 (a)~(d)) — 라이브와 독립적인 유닛 검증 대상.
- 기존 `run_commands` 경로로만 실행되도록 배선 — 신규 실행 표면 0(REQ-010/019). 생성형 Lua 우회 표면 부재 확인(REQ-014).
- 파일: `server/looks/instantiate.py`(가칭), `server/tests/test_looks_instantiate.py`, (배선) `server/web/session.py`.
- **AC**: AC-LOOKLIB-007, AC-LOOKLIB-008, AC-LOOKLIB-009, AC-LOOKLIB-016, AC-LOOKLIB-018.

### M5 — 자연어 매칭 표면 + 채팅 통합 (cycle_type=tdd)

- §A.4a 결정 E(하이브리드)로 매칭 축 구현: 무드 키워드/별칭/장르/다이내믹스 매칭 + 신뢰 실패 시 폴백 신호(REQ-015~018).
- 툴 등록(`build_toolset` 확장, `server/orchestrator/tools.py:23, 304`) + 얇은 룰북 정적 안내 축 — 프리픽스 byte-diff가 **정적 텍스트 1회 변경으로 수렴**함을 확인(REQ-022).
- 제공자 중립 확인: 매칭 표면이 `server/llm/factory.py:17-28`의 두 어댑터 어느 쪽에도 종속되지 않음(REQ-016).
- 파일: `server/looks/matching.py`(가칭), `server/orchestrator/tools.py`, `server/tests/test_looks_matching.py`.
- **AC**: AC-LOOKLIB-011, AC-LOOKLIB-012, AC-LOOKLIB-013, AC-LOOKLIB-017.

### M6 — 회귀 + 경계 전체 그린

- pytest 전체 + vitest 전체: run-phase 킥오프 기준선 대비 신규 실패 0건.
- `test_architecture.py` 그린 + `server/looks/**`의 OSC/bridge import grep 0건 + `server/safety/**` diff 없음.
- LiveLock 강등 + 기존 안전 불변식 전체 상속 확인(REQ-020/021).
- 룰북 프리픽스 byte 검증(AC-MVP-014 계열)이 §A.4a 결정 E와 정합함을 확인.
- **AC**: AC-LOOKLIB-010, AC-LOOKLIB-014, AC-LOOKLIB-019.

### M7 — 종단 라이브 검증 (실물 onPC, AC-LOOKLIB-014)

- 실물 콘솔에서 종단 1회: 채팅 추상 지시("웅장한 금색 코러스" 류) → 매칭 → 역할 매핑 → 인스턴스화 → 실행 프리뷰 관측 → 게이트 감사 로그 확인 → 생성 프리셋 GUI 확인.
- **M0에서 이미 실측된 ASSUMPTION-13/14/15는 여기서 재측정하지 않는다** — M7은 종단 통합의 실측이지 전제 검증이 아니다. M0 판정과 M7 관측이 어긋나면 그 불일치 자체를 progress.md에 기록한다.
- 배포 왕복 불요(콘솔측 무변경). 선행 조건: 콘솔 실행 + 이름 있는 그룹이 있는 쇼파일(GUI 사용자 작업).

### 라이브 세션 회계 (감사 D9)

v0.1.0은 "라이브 검증은 정확히 1 AC"(design.md §6.5)를 설계 성질로 주장했다. M0 신설로 이 성질은 **바뀐다** — 숨기지 않고 명시한다:

| | 세션 | AC | 무엇을 측정하는가 | 왜 합칠 수 없는가 |
|---|---|---|---|
| 1 | **M0 프로브** | AC-LOOKLIB-020 | ASSUMPTION-13/14/15 + 슬롯 탐색 실현성 | **M1 저작 전**에 답이 필요하다 |
| 2 | **M7 종단** | AC-LOOKLIB-014 | 매칭→매핑→인스턴스화→게이트 종단 통합 | **M6 완료 후**에만 존재한다 |

**라이브 세션 수 = 2.** 두 세션은 시간축의 양 끝(저작 전 / 통합 후)에 있어 물리적으로 병합 불가능하다. 이는 프로젝트 관례("라이브 검증 마일스톤 1개")로부터의 의식적 이탈이며, 그 대가로 "전제 미검증 상태에서 24~40룩을 저작하고 마지막에 무너지는" 위험을 제거한다. M0는 코드 변경 0인 측정 세션이라 준비 비용이 M7보다 낮다.

## §C. 기술 제약

1. **신규 런타임 의존성 0.** 기존 stdlib + PyYAML(기존 의존) + 기존 Python 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**: `server/safety/gate.py:260-265`(스크리닝 경로 하나), `server/safety/classify.py:169`(분류 의미론 하나), `server/rulebook/assembly.py:69-72`(프리픽스 조립 하나).
3. **fail-safe는 협상 대상이 아니다.** 미매핑·충돌·리그 불능의 실패 방향은 항상 축소/보류이지 추측 보완이 아니다.
4. **per-show 값의 정적 데이터 진입 금지**(REQ-004/022) — 룩 자산과 룰북 어디에도 구체 그룹/슬롯/FID 없음.
5. **범위 경계**: P1-1/P1-2 미번들(§D), 장르 묶음 런타임 실행 없음, 데모 시퀀스·익스큐터 바인딩 없음, UI 무변경, 콘솔측 Lua 무변경.
6. **라이브 왕복 비용 — 세션 2회**: **M0**(저작 전 프로브)와 **M7**(통합 후 종단)이 실물 콘솔을 요구한다(§B 라이브 세션 회계).
   - **M0 접근 불가 시**: M1 착수를 보류하고 progress.md에 사유를 기록한다 — M0를 건너뛰고 M1~M2를 진행하는 것은 **금지**다(그 경우 v0.1.0이 가졌던 순서 결함이 그대로 재발한다). 예외적으로 진행이 필요하면, 빔 축을 DESCOPE로 선(先)확정하고 역할 어휘를 제안 기본값으로 동결한 뒤 그 사실을 명시적으로 기록한다.
   - **M7 접근 불가 시**: M6까지 완료 후 progress.md에 상태를 기록하고 세션을 마무리한다(EXECBODY-001 M3 회복 절차 선례).

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase에서 확정)

| 태그 | 대상 | 내용 |
|---|---|---|
| `@MX:NOTE` | `server/looks/` 스키마 모듈 | 스키마가 P1-1/P1-2 공통 기반임 + per-show 값 금지 불변식 표시 |
| `@MX:NOTE` | 번들 빌더 | ClearAll/목적지 규율이 트래킹 오염 방지 기계화임을 표시 |
| `@MX:WARN` + `@MX:REASON` | 역할 매핑 휴리스틱 지점 | 이름 관례 기반 — 관례 없는 리그에서 미매핑 축소가 정상 동작임을 명시(위험 지대: 휴리스틱 확장 시 그룹 발명 금지 경계) |
| `@MX:ANCHOR` 신설 없음 | — | 기존 3앵커(§C.2)를 소비만 한다. 룩 모듈은 fan_in 조건 충족 전까지 NOTE로 시작 |

## §E. 테스트 스캐폴딩 계획

- **순수 함수 우선**: 로더/리졸버/빌더/매칭 전부 인메모리 — 스크리닝 경로에 OSC 0(design.md §6.1).
- **실패 모드 개별 테스트**(병합 금지): 미매핑/불능/미해석/truncated/충돌/폴백 각각(design.md §6.2).
- **번들 문자열 불변식 assert**(design.md §6.3): 목적지 선두·ClearAll 쌍·Label·**대소문자 무관** `/Overwrite` 부재·미등재 그룹 부재.
  - **대소문자 무관 assert의 근거(감사 D14)**: 런타임 매칭은 이미 대소문자 무관이다 — `server/safety/ruleset.py:47`(`lowered = [e.lower() for e in entries]`), `server/safety/classify.py:64`(`t, k = text.lower(), keyword.lower()`), `server/web/preview.py:100`(`lower = command.lower()`). 따라서 테스트가 `"/Overwrite" not in bundle`처럼 대소문자를 고정해 assert하면, 빌더가 `/overwrite`를 내보내도 **테스트는 조용히 통과**한다. 위험은 런타임이 아니라 **테스트의 위양성(false pass)** 이다.
- **run-phase 자기 검증 커맨드(예상, run-phase에서 확정)**:
  - `.venv/bin/python -m pytest server/tests/test_looks_schema.py server/tests/test_looks_library.py server/tests/test_looks_resolver.py server/tests/test_looks_instantiate.py server/tests/test_looks_matching.py -q`
  - `.venv/bin/python -m pytest server/tests/test_architecture.py server/tests/test_safety_gate.py server/tests/test_safety_classify.py server/tests/test_web_preview.py -q`
  - `.venv/bin/python -m pytest server/tests/test_safety_gate.py server/tests/test_web_panel_execute.py -q` (REQ-021 안전 불변식 상속 — EXECBODY-001 AC-EXECBODY-011 형식 계승)
  - `.venv/bin/python -m pytest -q` (전체, 킥오프 기준선 대비 신규 실패 0건)
  - `grep -rn "bridge.osc\|from server.bridge" server/looks/` → 0건
  - `grep -rn "AskUserQuestion\|mcp__askuser" server/looks/` → 0건
  - `grep -rniE "/overwrite" server/looks/` → 0건 (대소문자 무관, 감사 D14)
  - `git diff --stat server/safety/ server/rulebook/assets/v2.4.2/20_korean_terms.md` → 빈 출력 (PRESERVE 확인)
  - 라이브 검증(M0·M7): 감사 로그 jsonl verbatim 판독 + GUI 스크린샷(EXECBODY-001 AC-010 인수 형식 계승)

## §F. 결정 기록 (재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| v1 속성 범위 | 컬러/강도/빔 구체값 + 포지션 역할 추상(하드 pan/tilt 금지, 인스턴스화 시점 그룹 매핑) — 사용자 확정 ① | spec.md §A, REQ-001/006 |
| v1 장르 세트 | 워십/록/발라드/EDM 4종 × 6~10룩, 잔잔함→클라이맥스 스팬 — 사용자 확정 ② | spec.md §A, REQ-002 |
| v1 완결 범위 | 데이터 계층 + MA3 인스턴스화 + 자연어 매칭 전부 v1(완결 사용자 기능) — 사용자 확정 ③ | spec.md §A, B.3/B.4 |
| **빔 축 처리** | v1 범위 **유지** + M0 라이브 프로브 선행(ASSUMPTION-15). 스트로브/셔터는 preview `danger` 분류로 기본 제외 — 사용자 확정 ④ | spec.md §A/§D, REQ-001/003, plan.md M0 |
| **프리셋 슬롯 배정** | 런타임 빈 슬롯 탐색(캡 16 내). 고정 예약 대역·설정값 기각 — 사용자 확정 ⑤ | spec.md §A, plan.md §A.4a B, M4 |
| **인스턴스화 산출물** | 프리셋만. 데모 시퀀스·익스큐터 바인딩 기각 — 사용자 확정 ⑥ | spec.md §A/§D, REQ-010, plan.md §A.4a C |
| **충돌 처리** | 건너뛰고 "N개 건너뜀" 명시 보고. 덮어쓰기·재슬롯 기각 — 사용자 확정 ⑦ | spec.md REQ-012/013, plan.md §A.4a D |
| **룩 저장 형식** | YAML repo 자산 — `blacklist.yaml` 선례 + PyYAML 기존 의존(`pyproject.toml:16`). PinStore JSON은 런타임 사용자 데이터로 클래스 상이 → 선례 아님 (감사 D6b, 증거로 폐쇄) | plan.md §A.4a A, design.md §5.1, M2 |
| **매칭 표면 형상** | 하이브리드(얇은 룰북 안내 축 + 구조화 조회 툴) — research.md §2 결론 3이 이미 도출 (감사 D6b, 문서 내 증거로 폐쇄) | plan.md §A.4a E, design.md §5.1, M5 |
| **장르 묶음** | 런타임 실행 없음 — 스키마 API 형상만 예약 (감사 D7 범위 누출 제거) | spec.md REQ-010, §D |
| **라이브 세션 수** | **2회**(M0 프로브 + M7 종단). 프로젝트 관례 1회로부터의 의식적 이탈 — 근거는 §B 라이브 세션 회계 (감사 D9) | plan.md §B, design.md §6.5, acceptance.md AC-014/020 |
| 룩 데이터의 거처 | 서버측 구조화 데이터 계층이 단일 진실원 — 룰북 고정 프리픽스에 구조화 데이터 내장 기각(research.md §7 (a)) | spec.md REQ-016/022 |
| 매칭 인프라 | 임베딩/벡터 검색 기각 — 구조화 데이터 제시 + LLM 판단/키워드 축(research.md §7 (b)) | spec.md §D |
| 콘솔측 | Lua 응답기 무변경 — 인스턴스화는 검증된 커맨드라인 패턴(research.md §7 (c)) | spec.md §C/§D |
| P1-1/P1-2 | 번들하지 않음 — 스키마 소비 형상만 예약(research.md §10) | spec.md §D, REQ-001 |
| frontmatter 참조 | `related_specs`(비차단) — MVP-001/DASHUI-001/EXECBODY-001; 엄격 충족 전제의 pre-flight 차단 회피 선례 계승 | spec.md frontmatter |
| Tier 판단 | L — 신규 데이터 계층 + 리졸버 + 인스턴스화 + 매칭 + 툴 배선 + 라이브 AC가 결합, 예상 파일 15+ | spec.md frontmatter `tier: L` |

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> 구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다(첫 run-phase `Agent()` 스폰 전 작성). 본 절은 plan-phase 권고이며 오케스트레이터가 확정·기각한다.

### 입력 파라미터

- **tier**: L (5-artifact 세트 + progress.md)
- **scope (file count)**: 예상 14~20 파일(신규 looks 패키지 6~8 + YAML 자산 4 + 테스트 5 + 배선 2~3 + 룰북 안내 축 1)
- **domain count**: 2 (Python 서버 도메인 + 룩/연출 데이터 도메인) — 콘솔 Lua·UI 무변경으로 도메인 확장 없음
- **file language mix**: Python + 정적 데이터(YAML) + markdown. 코딩 중심
- **concurrency benefit**: **LOW** — M0가 M1을, M1 스키마가 M2~M5 전부를 규정하는 순차 의존(프로브 → 스키마 → 라이브러리 → 리졸버 → 빌더 → 매칭)
- **Agent Teams prereqs**: 해당 없음 (Mode 3 RETIRED)

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 신규 패키지 + 배선 + 라이브 AC — 단일 라인 변경 아님 |
| 2 | background | 미선택 | 쓰기 작업 포함 |
| 3 | agent-team | 미선택 | RETIRED (tombstone) |
| 4 | parallel | 미선택 | 도메인 2(<3), M0→M1이 후속 전부를 규정하는 순차 의존 — 병렬화 이득 없음 |
| 5 | **sub-agent** | **선택** | 순차 의존 체인 + 코딩 중심 + Tier L Section A-E 위임 템플릿 적용 |
| 6 | workflow | 미선택 | 14~20 파일(30 미만), 균일 기계 변환 아님(설계 결정 다수) |

### Decision: sub-agent

### 정당화

M0(프로브)가 M1의 전제를, M1(스키마)이 M2~M5의 데이터 계약을 규정하는 순차 게이트이므로 병렬화 이득이 없고, 코딩 중심 작업은 Anthropic coding-task parallelism caveat상 순차 sub-agent가 안전한 기본값이다. Tier L이므로 `manager-develop` 위임에 Section A-E 전체 템플릿을 적용한다.

**오케스트레이터가 확보해야 할 사용자 접점 3건**(전부 AskUserQuestion):

1. **Kickoff 전** — §A.4b 미해결 마커 **3건**(역할 어휘 / 다이내믹스 척도 / 매핑 UX) 해소. 각 마커는 구체적 제안 기본값과 근거를 이미 담고 있으므로, 그대로 선택지로 구성 가능하다.
2. **Kickoff 시점** — **M0 라이브 세션 접근 가능성** 확인. M0는 M1의 전제이므로 run-phase 진입 자체가 여기에 걸린다(§C.6 M0 접근 불가 절차).
3. **M6 완료 직후** — **M7 라이브 세션 접근 가능성** 재확인.

v0.1.0 대비 마커는 6→3으로 줄었으나 라이브 접점이 1→2로 늘어, 전체 사용자 왕복 수는 실질적으로 동일하다. 차이는 **왕복이 무엇에 쓰이는가**다 — 증거로 답할 수 있는 질문(저장 형식·매칭 표면)이 사라지고, 실측이 필요한 지점(M0)이 그 자리를 대신했다.
