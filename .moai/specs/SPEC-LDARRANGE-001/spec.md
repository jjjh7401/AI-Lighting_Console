---
id: SPEC-LDARRANGE-001
title: "배치 자동 생성 — 역할×마디 초안"
version: "0.2.0"
status: draft
created: 2026-10-10
updated: 2026-10-10
author: jaihyun
priority: P2
phase: "Lighting Copilot v1.2 target"
module: "server/design/song_cue_render.py(RG5 그룹-주소 함수 재사용만), ui/src/components/RunbookMode.tsx(SPEC-LDBEAT-001 격자가 이 SPEC의 산출물을 소비하는 자리), 신규 배치 생성 모듈(M2+, 이름·위치 미정), .moai/specs/SPEC-LDARRANGE-001(plan-phase 산출물뿐)"
lifecycle: spec-anchored
tags: "auto-arrangement, role-bar-draft, ai-suggestion-card, director-approval, rg5-group-address, love-attack"
tier: M
related_specs: [SPEC-LDBEAT-001, SPEC-LDBARMAP-001, SPEC-LDRHYTHM-001, SPEC-LDDESIGN-001]
depends_on: [SPEC-LDBEAT-001, SPEC-LDBARMAP-001]
---

# SPEC-LDARRANGE-001 — 배치 자동 생성: 역할×마디 초안

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-10 | 최초 작성(카드 t528). 감독 요청 2026-10-10(리드 경유, `reports/ldbeat-feasibility-roadmap-20261010.md`): 「되는 것과 안 되는 것, 그리고 앞으로 해야 할 것을 스펙을 만들어서 진행할 수 있도록 정리」, 그리고 그 보고서를 받아 「보고서대로 스펙을 만들어줘」. 입력: 위 로드맵 보고서(주 체크아웃 전용 경로, 추적 안 됨 — SPEC 진행안 순서 ①LDBEAT→②LDBARMAP→③LDARRANGE의 세 번째), `reports/effect-arrangement-rules-20261007.md`(규칙 9개·역할 6종·LOVE ATTACK 전체 배치 §3·0~25마디 격자 §4·감독 결정 §5), `.moai/reports/t525/verdict.md`(무대 패치 좌표 86/86 확인, 그룹 소속 18개 중 4개만·그룹당 앞 2칸만 확인), `.moai/specs/SPEC-LDBEAT-001/`(이 SPEC의 산출물을 소비할 격자 화면, 역할 6종 어휘의 출처, status: draft), `.moai/specs/SPEC-LDRHYTHM-001/`(REQ-LDRHYTHM-012(a) — 비트 시각 미저장·다운비트 생산자 0건, 이 plan-phase 재확인). **SPEC-LDBARMAP-001(마디 지도 SPEC)은 이 작성 시점에 존재하지 않는다**(`.moai/specs/` 확인, 카드 t527이 병행 작성 중) — 이 SPEC은 그 출력을 입력으로 가정하지만 스키마를 확정하지 않는다(§5 항목 1). Tier M(§0 근거). **plan만 — 코드 diff 0줄, 콘솔 접촉 0건.** |
| 2026-10-10 | plan-audit iteration 1 반영(`.moai/reports/plan-audit/SPEC-LDARRANGE-001-review-1.md`, 검증 PASS 0.80, Tier M 상한 충족). D1 — REQ-LDARRANGE-004·011의 요구사항 문장 안에 있던 파일:line·함수명 인용(`section_palette.py:236-267`, `session.py:7685-7902`, `song_cue_render.py:815`·`:890`)을 근거(rationale) 열로 이동. D6 — REQ-LDARRANGE-011의 GEARS 키워드를 `Where`→`While`로 통일(원문이 capability-gate 키워드와 "동안"(durative) 수식을 섞어 썼던 것을 고침). D3 — REQ-LDARRANGE-001·004·013에 전용 직접 AC를 부여(acceptance.md: AC-LDARRANGE-015 신규, AC-LDARRANGE-016 신규, AC-LDARRANGE-011 확장) — AC 총수 14→16, Tier M 상한(16개) 정확히 충족. D2 — REQ-LDARRANGE-002,003,004,006,008,009,011,012,013(9개 — plan-audit iter2 D9 재계수)의 `shall`/`shall not` 클로즈 묶음은 **분리하지 않는다**: 분리하면 REQ 총수가 14+9=23이 되어 Tier M 상한(16개)을 넘는다 — 쪼개기보다 상한 준수를 우선했다. 향후 리비전에서 SPEC을 둘로 나눌 기회가 생기면 재검토 후보로 남긴다. D4(인간 판단 AC의 자연어 서술)·D5(`depends_on`이 `SPEC-LDBARMAP-001`을 못 올림 — 그 SPEC이 아직 존재하지 않아서)·D7(`SPEC-LDBARMAP-001` 미존재 참조)은 plan-auditor가 이미 "의도된 공개"로 확인한 항목이라 변경하지 않는다. version 0.1.0→0.1.1. |
| 2026-10-10 | **인터페이스 맞춤(카드 t529, plan 문서만 — 코드 0·콘솔 0).** ① frontmatter `depends_on`에 `SPEC-LDBARMAP-001` 추가(iteration 1 D5 — 당시 그 SPEC이 없어 본문으로만 적었던 것; `related_specs`에도 추가). ② §5 항목 1에 "권고 입력 모양"을 넣어 `SPEC-LDBARMAP-001` §5 열린 결정 0의 "권고 출력 모양"과 같은 문면으로 맞췄다 — 필드 이름, 정수 밀리초/정수 마디 단위, 마디 번호 1-base 위상 1 기준 + 0 = 못갖춘마디(배치 규칙서 §4 "0~2"행), 사건 어휘 4개, "실제 임팩트" = `kick_entry`∪`drop`. 같은 자리에 소비자 쪽 공백 둘(사건 크기 없음, "마지막 코러스" 이름 없음)을 열린 채로 적었다. §2 항목 1 갱신. **REQ·AC 문면은 바꾸지 않았다** — plan-audit 재실행 없음(사유: `progress.md`). 만료 고지: §0·§1·§3 REQ-LDARRANGE-001·§4·`plan.md` §A/§B의 "`SPEC-LDBARMAP-001` 존재하지 않음"은 최초 작성 시점의 사실이다 — 그 SPEC은 같은 날 PR #571로 머지됐다(status: draft, 출력 데이터는 아직 없으므로 REQ-LDARRANGE-001의 구속은 그대로 유효). ③ LDBEAT 저장 키(§5 항목 2)는 t526 머지 뒤 후속 커밋. version 0.1.1→0.1.2. |
| 2026-10-10 | **저장 키 맞춤(카드 t529 ③, plan 문서만).** `SPEC-LDBEAT-001` v0.2.0(PR #572) 머지 뒤, §5 항목 2에 세 SPEC 공통 권고 키 이름(`beat_grid`/`bar_map`/`arrangement_draft`)과 같은 마디 번호 공간을 적었다. REQ·AC 문면 변경 0. 알려진 미해결(이 카드 범위 밖, 리드 보고): LDBEAT v0.2.0이 REQ-LDBEAT-004를 "콘솔 그룹 트랙 + 층 역할 이름표 key/back/side/wash/mover/effect/audience"로 재교정해, 이 SPEC의 REQ-LDARRANGE-002·AC-LDARRANGE-014가 인용하는 역할 6종(SCENE/BACK PULSE/…) 어휘가 LDBEAT 쪽에서 철회됐다. version 0.1.2→0.1.3. |
| 2026-10-10 | **역할 어휘 맞춤(카드 t533).** 직전 행이 적어 둔 미해결을 해소한다 — `SPEC-LDBEAT-001` v0.2.0(PR #572, 카드 t526)이 REQ-LDBEAT-004를 "콘솔 그룹 트랙(줄 하나 = 콘솔 그룹 하나 = 시퀀스 하나) + `rig.py`의 7개 층 역할 이름표 key/back/side/wash/mover/effect/audience"로 재교정했으므로, 이 SPEC도 같은 어휘를 쓰도록 맞춘다. §2 끝에 단위 정정 문단을 추가해 이 문서 전체가 쓰는 "역할×마디"의 뜻을 "콘솔 그룹 트랙(역할 이름표가 붙음) × 마디"로 명시했다. REQ-LDARRANGE-002(생성기가 쓸 트랙 모양·역할 어휘를 LDBEAT와 맞추고, 배치 규칙서 §2의 역할 6종을 트랙 식별자로 금지, 겹치는 그룹 트랙 동시 사용 금지를 흡수)·REQ-LDARRANGE-007(STROBE 게이팅을 "ACCENT 트랙"이 아니라 트랙 비종속 서술로 재작성)을 고쳤다. `acceptance.md` AC-LDARRANGE-003·004(ACCENT 트랙 참조 제거)·014(라벨 집합을 7종 부분집합 + 트랙 식별자가 6종이 아닌지로 재정의, AC 개수 16 불변)를 같은 방향으로 고쳤다. `plan.md` §B 위험 6(역할 어휘 분류축 안내를 반전 — 이제 LDBEAT·LDARRANGE와 `rig.py`는 같은 어휘다)·§C 사전 점검 grep(LDBEAT의 7종 어휘를 확인하도록 교체)·§E M3(그룹 매핑 입력을 7종 트랙으로 교정)·§F 안티패턴·§G 교차 참조(`rig.py` 인용 정정)를 갱신했다. REQ·AC가 구속하는 **뜻**(생성기가 새 역할 발명 금지·STROBE 게이팅·그룹 번호 주소만 사용)은 바뀌지 않았으나 **인용 어휘**가 바뀌었으므로 **plan-audit 재실행이 필요하다**(`progress.md`에 기록). version 0.1.3→0.2.0. |

## §0. Tier 선택 근거

**Tier M.** 이 SPEC은 신규 생성 로직 모듈(역할×마디 배치 알고리즘) 1개 + AI 제안 카드 UI(LDDESIGN REQ-092/094/095 패턴 확장, 단일 큐가 아니라 전체 초안 단위로 일반화) + 기존 RG5 그룹-주소 함수(`server/design/song_cue_render.py`) 재사용으로 구성된다. 영향 파일 추정 5~12개(생성 로직 모듈 1~2개, AI 제안 카드 UI 컴포넌트 1~2개, LDBEAT 격자와의 연결점 수정, 테스트 다수), LOC 추정 300~900줄로 Tier S 상한(5파일/300LOC)을 넘지만 Tier L 기준(15파일/1000LOC)에는 못 미친다. REQ 14개·AC 16개로 Tier M 상한(각 16개) 안에 든다. 또한 이 SPEC은 **SPEC-LDBARMAP-001(마디 지도, 아직 미작성)과 SPEC-LDBEAT-001(격자 화면, status: draft)에 둘 다 의존**하므로 — 두 전제 SPEC이 모두 run-phase에 진입하기 전에는 이 SPEC의 run-phase도 착수하지 않는다(§5 항목 1, Implementation Kickoff Approval 라운드에서 재확인).

## 감독 결정 (원문, 2026-10-10, 리드 경유)

> 「되는 것과 안 되는 것, 그리고 앞으로 해야 할 것을 스펙을 만들어서 진행할 수 있도록 정리」 → (로드맵 보고서 전달 뒤) 「보고서대로 스펙을 만들어줘」

이 결정은 `reports/ldbeat-feasibility-roadmap-20261010.md`의 "없는 것" 항목 2("역할×마디 배치 자동 생성 — 지금 LOVE ATTACK 배치는 리드 손작업")와 SPEC 진행안 3행("SPEC-LDARRANGE-001, 끝나면 감독이 보는 것: 새 곡의 배치 초안이 런북에 자동으로 뜸")을 그대로 승계한다. 같은 보고서의 감독 결정 필요 항목 4("AI 제안은 항상 「적용」을 거침 — 권고: 예")는 이 SPEC의 REQ-LDARRANGE-009가 요구사항으로 받는다.

## 1. 배경 — 지금 무엇이 없는가 (실측)

로드맵 보고서 "없는 것" 항목 2를 이 plan-phase가 재확인했다:

- **자동 배치 생성기는 지금 존재하지 않는다.** `grep -rln "arrangement\|auto_arrange\|generate_arrangement\|배치.*생성\|배치.*자동" server --include="*.py"`는 `arrangement`라는 낱말을 포함하는 파일을 전혀 찾지 못했다(이 plan-phase 재확인) — 있는 것은 효과 검색/합성(`find_fx`/`compose_fx`, `server/orchestrator/tools.py:7764,8117`)과 위치 커맨드 생성(`server/spatial/pointing.py`)뿐이다. 둘 다 "트랙 하나(콘솔 그룹 하나)·마디 하나"의 커맨드를 만드는 하위 도구이고, "콘솔 그룹 트랙 × 마디 N개"를 규칙에 맞춰 짜는 상위 로직은 없다.
- **LOVE ATTACK의 지금 배치는 손작업이다.** `reports/effect-arrangement-rules-20261007.md` §3~§4의 표(마디별 SCENE/주인공/보조/무빙 U·D/강조)는 리드가 전문가 조사·K팝 조사·감독 확인을 거쳐 손으로 짠 것이다(같은 문서 머리말) — 교정 뒤에는 `SPEC-LDBEAT-001`과 마찬가지로 "콘솔 그룹별 배치"로 읽는다(값 자체는 바뀌지 않는다, LDBEAT §1). 이것이 이 SPEC의 수용 판정 기준선이다(§5·acceptance.md AC-LDARRANGE-001).
- **마디 지도(SPEC-LDBARMAP-001)는 아직 없다.** `.moai/specs/`에 그 디렉터리가 없다(이 plan-phase 확인) — 카드 t527이 병행 작성 중이며, 완성되면 비트·다운비트·마디 경계·마디별 변화(킥·드롭·빌드)를 산출한다(로드맵 보고서 SPEC 진행안 2행). `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a)도 "지금은 BPM 숫자 하나만 렌더러에 닿는다(`analyze.py` 비트 시각 미저장·다운비트 생산자 0건)"고 이미 적어 뒀다 — 이 plan-phase가 `server/audio/analyze.py`를 재확인해도 같다(`beat_times`는 `_tempo_from_beats`에서 BPM 계산에만 쓰이고 저장되지 않는다, `:352-390`). **이 SPEC은 그 출력에 의존하지만, 출력 스키마를 이 plan-phase에서 확정하지 않는다**(§5 항목 1 — 열린 결정).
- **그룹 소속은 여전히 부분적으로만 확인됐다.** `.moai/reports/t525/verdict.md`: 무대 패치 좌표는 86/86 전부 확인됐지만, 그룹 소속은 18개 그룹 중 4개만 읽었고(`probe_groups.py`), 그 4개도 `SELECTIONDATA` 값이 응답기 한도(`console/lua/copilot_responder.lua:43` `max_prop_value=240`)에 잘려 그룹당 앞 2칸만 왔다. 전부 읽으려면 응답기의 "나눠 읽기" 확장이 필요하고, 그것은 이 SPEC의 범위 밖이다(§4 Out of Scope).
- **AI 제안 → 「적용」 흐름의 선례는 있지만, 단일 큐 단위다.** `SPEC-LDDESIGN-001` REQ-LDDESIGN-092/094/095(M7 "PLAN CUE 수정요청 생성기")가 "생성기는 문장만 산출, 서버가 단일 진실 지점, 로컬 변형 금지, 거절 시 상태 유지" 원칙을 확정했다 — 그러나 그 대상은 큐 카드 하나다. 이 SPEC은 같은 원칙을 **역할×마디 전체 초안**(여러 칸에 걸친 배치) 단위로 일반화해야 한다(REQ-LDARRANGE-009) — "선례가 있으니 그대로 포팅하면 된다"고 가정하면 N칸 배치 승인이 N개의 개별 승인으로 쪼개지는 사고가 난다(LDBEAT의 같은 함정, REQ-LDBEAT-012 참조).

## 2. 입력 인터페이스 — 세 가지 모두 확정되지 않았다

이 SPEC의 생성기는 세 입력을 받는다. 셋 중 **둘은 열린 결정**이다(§5):

1. **마디 지도** — `SPEC-LDBARMAP-001` 출력(그 SPEC은 PR #571로 머지됐지만 status: draft — 출력 **데이터**는 아직 없다). 값의 모양은 두 SPEC이 같은 권고 문면을 가진다(§5 항목 1, 카드 t529). 저장 위치는 미정.
2. **확정 배치 규칙** — `reports/effect-arrangement-rules-20261007.md`(저장소에 이미 추적됨, 이 입력은 확정). 규칙 9개(§1)·역할 6종(§2)·LOVE ATTACK 전체 배치(§3)·0~25마디 격자(§4)·감독 결정(§5).
3. **무대 패치** — t525가 확인한 좌표(86/86)·그룹(18개 중 4개, 그룹당 앞 2칸). RG5 그룹-주소 패턴(`server/design/song_cue_render.py:815` `_role_group_numbers`, `:890` `_effect_group_numbers` — "그룹-주소 패턴, fid 불요·RG5" 주석, 이 plan-phase 재확인)을 그대로 재사용하면 **멤버십 전수를 몰라도** 그룹 번호만으로 역할-그룹 매핑을 유지할 수 있다 — 이것이 이 SPEC이 "그룹 소속 부분 확인"이라는 조건에서도 진행할 수 있는 근거다(REQ-LDARRANGE-011).

출력(역할×마디 초안)이 `SPEC-LDBEAT-001`의 박자 격자 화면에 어떻게 닿는지(저장 키, 데이터 모델)도 열린 결정이다(§5 항목 2) — `SPEC-LDBEAT-001` REQ-LDBEAT-006이 격자 자체의 저장을 "기존 `timeline` 사전에 `beat_grid` 키로 임베드"를 권고(아직 결정 아님, M2 진행 중)로 두었으므로, 이 SPEC의 초안도 그 결정이 확정된 뒤 같은 모양(새 키, 예: `arrangement_draft`)을 따르는 쪽이 유력하지만 이 plan-phase에서 그 키 이름을 확정하지 않는다.

> **단위 정정(카드 t533, 2026-10-10)**: 이 SPEC의 산출 단위는 "역할×마디"가 아니라 **"콘솔 그룹 트랙 × 마디"**다 — `SPEC-LDBEAT-001` v0.2.0(REQ-LDBEAT-004)이 확정한 격자 모양과 같다. 트랙 하나 = 콘솔 그룹 하나 = 시퀀스 하나이며, 그 트랙에는 `server/design/rig.py`의 `RIG_LAYER_ROLES` 7종(key/back/side/wash/mover/effect/audience) 중 정확히 하나의 이름표가 붙는다. 펄스·체이스·스윕·웨이브·STROBE·BLIND 같은 효과는 트랙 **정체성**이 아니라 그 트랙의 마디·큐 **안의 내용**일 뿐이다(§4 Out of Scope에서 다루는 콘솔 송신 자체와는 별개 축). 이 문서가 이후에도 계속 쓰는 "역할×마디"라는 표현은 이 정정된 뜻(콘솔 그룹 트랙 × 마디, 트랙에 역할 이름표가 붙는다)으로 읽는다 — 배치 규칙서 §2의 역할 6종(SCENE/BACK PULSE/SIDE CHASE/MOVER-U MOVE/MOVER-D MOVE/ACCENT)은 그 문서의 교정 전 1차 표기일 뿐이며, 이 SPEC의 생성기가 쓰는 트랙 식별자가 아니다(REQ-LDARRANGE-002).

## 3. 요구사항 (GEARS)

### 3.1 R1 — 입력과 생성 범위 (REQ-LDARRANGE-001~003)

| ID | 요구사항 | 근거 |
|---|---|---|
| REQ-LDARRANGE-001 | [HARD] **While** 마디 지도(`SPEC-LDBARMAP-001` 출력)가 아직 존재하지 않는 동안(이 작성 시점 `.moai/specs/`에 그 디렉터리 없음, 이 plan-phase 확인), 배치 생성기는 실제 마디 지도 데이터에 의존하는 생성 로직을 구현하지 **shall not** 한다 — 이 plan-phase는 입력 인터페이스를 열린 결정(§5 항목 1)으로만 명시하고, run-phase 착수는 그 SPEC의 존재와 출력 스키마 확정을 선행 조건으로 삼는다. | `reports/ldbeat-feasibility-roadmap-20261010.md` SPEC 진행안(순서 ②LDBARMAP→③LDARRANGE), `.moai/specs/` 디렉터리 목록 확인(이 plan-phase) |
| REQ-LDARRANGE-002 | **재교정(카드 t533)**: `SPEC-LDBEAT-001` v0.2.0의 REQ-LDBEAT-004 트랙 모양 교정을 그대로 따른다. **The** 배치 생성기 **shall** 마디 지도 + 확정 배치 규칙(`reports/effect-arrangement-rules-20261007.md` §1~§4) + 무대 패치(t525 좌표·그룹)를 입력으로 받아, `SPEC-LDBEAT-001` REQ-LDBEAT-004가 정한 트랙 모양(줄 하나 = 콘솔 그룹 하나 = 시퀀스 하나) + 그 줄에 붙는 `rig.py`의 7개 층 역할 이름표(key/back/side/wash/mover/effect/audience) × 마디 격자 초안을 생성한다 — 그 7종 밖의 새 역할 이름을 발명하지 **shall not** 하고, 배치 규칙서 §2가 쓰는 역할 6종(SCENE/BACK PULSE/SIDE CHASE/MOVER-U MOVE/MOVER-D MOVE/ACCENT)을 트랙 식별자로 쓰지 **shall not** 하며(그 6종은 교정 전 1차 표기일 뿐이다 — §2 "단위 정정" 참조), 같은 장비를 두 트랙이 동시에 잡는 겹치는 그룹 배치(예: MOVER-ALL과 MOVER-U를 동시에 트랙으로 선택)를 산출하지 **shall not** 한다. | `REQ-LDBEAT-004`(트랙 모양·역할 어휘·겹치는 그룹 금지의 출처), `reports/effect-arrangement-rules-20261007.md` §2, `server/design/rig.py:51-59`(`RIG_LAYER_ROLES` 7종, 이 plan-phase 재확인) |
| REQ-LDARRANGE-003 | **The** 생성된 초안 **shall** `SPEC-LDBEAT-001`의 박자 격자 화면에 "편집 가능한 초안"으로만 표시되고, 콘솔에 이 SPEC이 직접 쓰지 **shall not** 한다 — 콘솔 반영은 `SPEC-LDBEAT-001` M4(REQ-LDBEAT-011~013)의 승인=송신 경로를 그대로 거친다, 이 SPEC이 별도 송신 경로를 신설하지 **shall not**. | `REQ-LDBEAT-011~013`(이미 확정된 송신 경로), §4 Out of Scope |

### 3.2 R2 — 규칙은 곡별 기본값 (REQ-LDARRANGE-004~006)

| ID | 요구사항 | 근거 |
|---|---|---|
| REQ-LDARRANGE-004 | [HARD] **The** 확정 배치 규칙 9개(`reports/effect-arrangement-rules-20261007.md` §1) **shall** 곡별 기본값으로 적용되고, 전곡에 강제되지 **shall not** 한다 — 기존 `palette_mode`(값 `"palette"`/`"concept"`/`"mixed"`, 저장소 상태 필드로 유지됨)와 같은 모양의 곡별 선택 메커니즘을 재사용한다. | 감독 결정(2026-09-23, 리드 경유) "스타일마다 다른데 하나로 고정은 무리" — `feedback-lighting-rules-are-defaults-not-universal.md`; 재사용 대상 코드 `server/design/section_palette.py:236-267`(실측 `:236,265-267`), `server/web/session.py:7685-7902`(실측 `:7685,7712,7714,7754,7780`) |
| REQ-LDARRANGE-005 | **The** 생성기 **shall** 어느 4마디 구간에서도 장면 위 리듬층 동시 개수를 보통 2개로 제한하고, 드롭·마지막 코러스 구간에서만 3개까지 허용한다(배치 규칙서 규칙 3). | `reports/effect-arrangement-rules-20261007.md` §1 규칙 3 |
| REQ-LDARRANGE-006 | **The** 생성기 **shall** 주인공(그 구간에서 가장 눈에 띄게 리듬을 타는 층) 역할을 4마디마다 교대하고, 같은 박자 동작이 8마디를 넘지 **shall not** 한다(배치 규칙서 규칙 4). | `reports/effect-arrangement-rules-20261007.md` §1 규칙 4 |

### 3.3 R3 — 강조(스트로브) 게이팅 (REQ-LDARRANGE-007~008)

| ID | 요구사항 | 근거 |
|---|---|---|
| REQ-LDARRANGE-007 | [HARD] **재서술(카드 t533)**: STROBE는 트랙 정체성이 아니라 트랙의 마디·큐 안의 내용이므로(§2 "단위 정정"), 이 요구사항은 "ACCENT 트랙"이 아니라 트랙 비종속으로 서술한다 — 게이팅의 뜻은 바뀌지 않는다. **While** 곡이 "느린 곡"으로 판정되는 동안, 생성기는 그 어떤 콘솔 그룹 트랙의 마디·큐에도 STROBE 내용을 채우지 **shall not** 한다 — "느린 곡" 판정 기준은 배치 규칙서에 수치가 없어 열린 결정이다(§5 항목 3). | 배치 규칙서 §1 규칙 9 "발라드처럼 느린 곡에는 쓸 필요가 없고", §5 "필수가 아니다" 감독 결정 원문 |
| REQ-LDARRANGE-008 | **The** STROBE 칸은 **shall** 마디 지도가 "실제 임팩트"로 표시한 마디에만 제안되고, 그런 마디 지도 표시 없이 임의로 추가되지 **shall not** 한다(규칙 9 "강하고 임팩트 있는 부분에 한번 강조하듯만"). | 배치 규칙서 §1 규칙 9, §5 감독 결정 원문 |

### 3.4 R4 — AI 제안 카드와 「적용」 (REQ-LDARRANGE-009~010)

| ID | 요구사항 | 근거 |
|---|---|---|
| REQ-LDARRANGE-009 | [HARD] **The** 생성된 역할×마디 초안 **shall** AI 제안 카드로 표시되며, 감독의 명시적 「적용」 없이 `SPEC-LDBEAT-001` 격자의 "확정" 상태로 전환되지 **shall not** 한다 — `SPEC-LDDESIGN-001` REQ-LDDESIGN-092/094(생성기는 문장/구조만 산출, 서버가 단일 진실 지점, 로컬 변형 금지)와 같은 원칙을, 큐 하나가 아니라 **초안 전체** 단위로 일반화해 적용한다. | 로드맵 보고서 감독 결정 필요 4항("AI 제안은 항상 「적용」을 거침 — 권고: 예"), `REQ-LDDESIGN-092,094` |
| REQ-LDARRANGE-010 | **When** 제안 카드가 거절되면, 격자 상태는 **shall** 변경 0건으로 유지되고 거절 사유가 표시된다 — `REQ-LDDESIGN-095`의 "거절 시 스택이 그대로 남고 거절 사유가 표시된다" 패턴과 같은 모양이다. | `REQ-LDDESIGN-095` |

### 3.5 R5 — 그룹 소속 불명 처리 (REQ-LDARRANGE-011~012)

| ID | 요구사항 | 근거 |
|---|---|---|
| REQ-LDARRANGE-011 | [HARD] **While** 그룹 소속 전수가 아직 확인되지 않은 상태인 동안(t525 — 18개 그룹 중 4개만 확인, 그 4개도 `SELECTIONDATA` 응답기 한도로 앞 2칸만 읽힘), 생성기는 **shall** 역할→그룹을 그룹 번호로만 주소하고(RG5 그룹-주소 패턴 재사용), 특정 장비(fid) 소속을 추론하거나 발명하지 **shall not** 한다. | `.moai/reports/t525/verdict.md` ②; 응답기 한도 `console/lua/copilot_responder.lua:43` `max_prop_value=240`; RG5 함수 `server/design/song_cue_render.py:815`(`_role_group_numbers`)·`:890`(`_effect_group_numbers`), 재확인 인용 `song_cue_render.py:661,815,890`("그룹-주소 패턴, fid 불요·RG5") |
| REQ-LDARRANGE-012 | **The** 생성기가 산출하는 커맨드 미리보기 **shall** 그룹 번호 주소만 쓰고, 멤버십이 확인되지 않은 그룹에 대해 "멤버 N대"류의 단정적 서술을 표시하지 **shall not** 한다. | `.moai/reports/t525/verdict.md` §미검증("그룹 18개 중 4개만 읽었다") |

### 3.6 R6 — 범위 경계와 수용 판정 (REQ-LDARRANGE-013~014)

| ID | 요구사항 | 근거 |
|---|---|---|
| REQ-LDARRANGE-013 | **The** 무대 패치의 좌표·방향(t525, 좌우/앞뒤) **shall** `SPEC-LDBEAT-001` 격자의 시각화 참고 정보로만 쓰이고, 역할×마디 배치 로직 자체의 입력으로 사용되지 **shall not** 한다 — 역할→그룹 매핑은 `REQ-LDBEAT-009`의 책임이며 이 SPEC은 그 매핑을 소비만 한다. 좌표 기반 배치 정교화는 이 SPEC의 범위 밖이다(§5 항목 4, §4 Out of Scope). | `.moai/reports/t525/verdict.md`, `REQ-LDBEAT-009` |
| REQ-LDARRANGE-014 | **The** 이 SPEC의 완료 판정은 **shall** LOVE ATTACK 자동 초안을 손 배치(`reports/effect-arrangement-rules-20261007.md` §4, 또는 run-phase가 §3 전체로 확장)와 나란히 렌더해 감독이 육안으로 비교하는 것이 유일한 최종 결정권자다 — `SPEC-LDRHYTHM-001` AC-LDRHYTHM-010("실기 판정이 유일한 완료 결정권자")과 같은 모양이며, 그 외 모든 기계 AC는 그 비교 전의 사전 체(pre-filter)다. | `SPEC-LDRHYTHM-001` acceptance.md AC-LDRHYTHM-010 선례 |

## 4. 제외 범위 (Out of Scope)

### Out of Scope — 마디 분석 자체 (SPEC-LDBARMAP-001)

- 비트·다운비트·마디 경계·마디별 변화(킥·드롭·빌드) 검출은 이 SPEC의 일이 아니다 — `SPEC-LDBARMAP-001`(카드 t527 병행 작성)의 범위다.
- 오디오 분석 알고리즘 자체(`server/audio/analyze.py`)의 변경도 이 SPEC의 범위 밖이다.

### Out of Scope — 격자 화면·저장·에미터·콘솔 송신 (SPEC-LDBEAT-001)

- 박자 격자 UI 렌더링, 저장 키/데이터 모델, 박자 전용 새 앱측 에미터, 승인=송신 비교 로직 승격은 모두 `SPEC-LDBEAT-001`의 범위다 — 이 SPEC은 그 화면에 표시될 **데이터**(초안)만 만든다.
- 이 SPEC이 생성한 초안의 콘솔 반영은 전적으로 `SPEC-LDBEAT-001` M4의 승인=송신 경로를 거친다 — 이 SPEC은 별도 송신 코드를 작성하지 않는다.

### Out of Scope — 응답기 "나눠 읽기" 확장 (그룹 소속 전수 확인)

- `console/lua/copilot_responder.lua`의 `max_prop_value` 확장, `SELECTIONDATA` 나눠 읽기 프로토콜 추가는 이 SPEC의 범위 밖이다(`.moai/reports/t525/verdict.md` "다음 카드 제안" 1항) — 이 SPEC은 그룹 소속이 부분적으로만 확인된 상태를 그룹-번호 주소(REQ-LDARRANGE-011)로 우회한다.

### Out of Scope — 색 미세 조정

- 감독 결정(2026-09-28, 리드 경유): 색 미세 조정은 전체 배치가 끝난 뒤의 별도 작업이다 — 이 SPEC이 생성하는 초안의 색은 배치 규칙서 §5("색 자리표시: 진하게, W0+채도 높은 RGB — 최종 색 고르기는 나중")의 자리표시 수준을 넘지 않는다.

### Out of Scope — 실시간 생성·다른 곡 배치 규칙서 작성

- 곡 재생 중 실시간으로 배치를 다시 짜는 기능은 범위 밖이다 — 생성은 재생 전 1회성 초안 생성이다.
- LOVE ATTACK 이외 곡의 배치 규칙서를 리드가 손으로 새로 쓰는 일, 또는 임의의 곡에서 배치 규칙 자체를 자동 추론하는 알고리즘(예: 비트/드롭 검출로 규칙을 역산)은 범위 밖이다 — 이 SPEC은 **확정된 규칙**을 **적용**하는 생성기이지, 규칙을 만드는 생성기가 아니다.

## 5. 열린 결정

이 결정들은 감독 착수 승인(Implementation Kickoff Approval) 라운드 또는 그 전에 명시적으로 확인받아야 한다 — 권고는 있으나 확정이 아니다.

1. **[열린 결정 — SPEC-LDBARMAP-001 확정 대기] 마디 지도 출력 인터페이스** (스키마, 저장 위치). 최초 작성 시점에는 `SPEC-LDBARMAP-001`이 없었다 — 지금은 PR #571(`deab5dd5`)로 머지됐고(status: draft), 저장 위치는 그 SPEC §5 열린 결정 0(REQ-LDBARMAP-010)이 M2+로 미뤘다. 권고: 그 SPEC이 run-phase에 진입하고 출력 스키마가 고정된 뒤, 이 SPEC의 run-phase 착수 전에 이 항목을 재확인한다 — 두 SPEC을 동시에 진행하면 LDARRANGE의 생성 로직이 아직 안정되지 않은 스키마에 묶이는 사고가 난다.
   - **권고 입력 모양(카드 t529 — 생산자 `SPEC-LDBARMAP-001` §5 열린 결정 0의 "권고 출력 모양"과 같은 문면, 확정 아님).** 한쪽만 고치면 생산자와 소비자가 갈라진다 — 두 문단을 같이 고친다.
     - `bpm`(실수, BPM) · `time_signature`(`[4, 4]`) · `bars[]` = `{bar, start_ms, beats_ms}` · `events[]` = `{kind, start_bar, end_bar, start_beat, grade}`.
     - **마디 번호(`bar`·`start_bar`·`end_bar`)**: 정수, **1-base, 위상 1 기준** — 지도 보고서(`reports/loveattack-music-map-20261006.md`) §2·부록 A와 이 SPEC의 입력인 배치 규칙서 §3~§4가 이미 같은 번호 공간이다(둘 다 후렴 1 진입 = 18마디, 실측 대조 t529). **0 = 못갖춘마디(앞박) 예약 번호** — 배치 규칙서 §4 "0~2"행의 0이 이것이다. 마디 지도에 못갖춘마디가 없으면 `bar: 0`은 생략된다 — 그때 0행을 어떻게 다룰지는 run-phase 생성기 설계의 몫이다. 사건 구간은 **양끝 포함**.
     - **단위**: 절대 시각(`start_ms`·`beats_ms`)만 정수 밀리초, 그 밖의 길이·창은 정수 마디(필요하면 `start_beat`, 마디 안 1-base 1~4). 초 단위 길이 필드는 없다 — REQ-LDARRANGE-005·006의 "4마디"·"8마디"는 `bar` 번호 차로 센다.
     - **사건 어휘(`kind`) 4개 고정**: `kick_entry`(킥 진입 — 지도 보고서의 "후렴 진입 큰 히트") · `build`(빌드업) · `drop`(드롭) · `break`(브레이크 — "킥 멈춤"). `grade`는 `measured` | `estimated`(지도 보고서 [잰 값]/[추정]).
     - **이 SPEC이 읽는 방식(권고)**: REQ-LDARRANGE-008의 "실제 임팩트" = `kind ∈ {kick_entry, drop}` 사건의 (`start_bar`, `start_beat`). REQ-LDARRANGE-005의 "드롭" 구간 = `kind == drop` 사건의 `start_bar`~`end_bar`.
     - **이 모양으로 메워지지 않는 소비자 쪽 공백 둘(열린 채로 둔다)**: (가) **크기가 없다** — 위 임팩트 집합은 STROBE를 제안해도 되는 마디의 **상한**일 뿐, 그 안에서 배치 규칙서 §3의 STROBE 자리(63·67마디)와 BLIND만 쓰는 자리(18·46마디)를 가를 신호가 마디 지도에 없다. (나) **"마지막 코러스" 이름이 없다** — 구간 이름은 마디 지도의 몫이 아니라 기존 분석 캐시의 `sections`(지도 보고서 §6 "추정" 등급)에서 온다. 두 공백은 Implementation Kickoff Approval 라운드에서 이 항목과 함께 제시한다.
2. **[열린 결정 — SPEC-LDBEAT-001 M2 확정 대기] LDBEAT 격자 입력 인터페이스(저장 키)**. `SPEC-LDBEAT-001` REQ-LDBEAT-006은 격자 자체의 저장을 "기존 `timeline` 사전에 `beat_grid` 키로 임베드"를 권고(아직 결정 아님, M2 미착수)로 두었다. 권고: 그 결정이 확정되면, 이 SPEC의 초안도 같은 `timeline` 사전 안의 새 키(예: `arrangement_draft`)로 임베드해 같은 되돌리기/영속 메커니즘(`TimelineDraftHistory`/`SongTimelineStore`/`SongTimelineLibrary`)을 코드 추가 없이 재사용한다 — 독립 저장소 신설은 M2가 LDBEAT 쪽에서 임베드를 기각할 경우에만 고려한다.
   - **세 SPEC 공통 권고 키 이름(카드 t529, `SPEC-LDBEAT-001` v0.2.0 §5 열린 결정 0'·`SPEC-LDBARMAP-001` §5 열린 결정 0과 같은 문면, 확정 아님)**: `timeline["beat_grid"]`(확정 격자 — `SPEC-LDBEAT-001`) · `timeline["bar_map"]`(마디 지도 — `SPEC-LDBARMAP-001`이 옵션 A를 고를 때) · `timeline["arrangement_draft"]`(자동 초안 제안 — 이 SPEC, 「적용」 전에는 `beat_grid`를 건드리지 않는다, REQ-LDARRANGE-009). 세 키의 마디 번호는 같은 번호 공간(§5 항목 1 — 1-base 위상 1, 0 = 못갖춘마디)이다. LDBEAT M2는 아직 미착수(v0.2.0 status: draft)라 저장 위치 확정은 여전히 그 M2의 몫이다.
3. **[열린 결정] "느린 곡" 판정 기준** (REQ-LDARRANGE-007의 STROBE 게이팅). 배치 규칙서는 "발라드처럼 느린 곡"이라고만 적고 수치 경계를 주지 않는다. 옵션: (a) BPM 임계값(예: `server/audio/analyze.py`가 산출하는 BPM < N) — 단순하지만 BPM은 느낌과 항상 일치하지 않는다(예: 빠른 BPM의 발라드풍 편곡), (b) 감독이 곡별로 직접 지정하는 플래그(곡 메타데이터에 "느린 곡" 불리언) — REQ-LDARRANGE-004의 곡별 기본값 모델과 자연스럽게 맞물린다, (c) 마디 지도(SPEC-LDBARMAP-001)가 산출하는 섹션 특성(예: 드롭/빌드 밀도)으로 추론 — 마디 지도가 아직 없어 이 SPEC의 run-phase 시점에 쓸 수 없을 가능성. 권고: (b)를 1차 기본값으로 채택하고 (a)를 보조 제안으로 노출한다 — 수치 하나로 전곡을 재단하는 위험(REQ-LDARRANGE-004가 경계하는 것과 같은 종류)을 피한다.
4. **[열린 결정] 무대 패치(좌표·방향)가 그룹-번호 주소를 넘어 역할 배치 자체에 영향을 주는가**. 옵션: (a) 아니다 — 역할 배치는 순수하게 규칙+마디 지도+그룹 번호로 결정되고, 좌표는 LDBEAT 격자나 무대 그림(t525)의 시각화 참고 정보로만 쓰인다, (b) 그렇다 — 예를 들어 무대 앞뒤 추정 방향(현재 이름 추정뿐, t525 "콘솔에서 무대 앞뒤를 따로 읽지는 않았다")이 FOH/BACK 역할의 그룹 선택에 영향을 줄 수 있다. 권고: (a) — 이 SPEC의 범위(§3.6 REQ-LDARRANGE-013)는 이미 (a)로 명시했다. 좌표 기반 배치 정교화가 필요해지면 별도 SPEC으로 분리한다.
