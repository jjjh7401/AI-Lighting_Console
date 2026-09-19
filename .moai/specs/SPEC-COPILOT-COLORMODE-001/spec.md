---
id: SPEC-COPILOT-COLORMODE-001
title: "색 운용 방식 확인 문항 — Q2B 색 운용(Color Usage) 인터뷰 스텝"
version: "0.2.0"
status: in-progress
created: 2026-09-20
updated: 2026-09-20
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.0 target"
module: "server/design, server/web, ui/src/components"
lifecycle: spec-anchored
tier: M
tags: "interview, color-usage, director-decisions, analysis-summary, kanban-t404"
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-09-20 | orchestrator | 최초 작성. 카드 t404. base main `91695109`. 감독 지시 2026-09-13 반영 — Q2 팔레트 다음에 "이 색을 어떻게 쓸지" 확인 문항(Q2B_COLOR_USAGE)을 인터뷰에 추가하고, 답을 `director_decisions`에 `color_usage` 축으로 남기며, 분석 요약과 구간 팔레트 산출에 실제로 반영한다. |
| 0.2.0 | 2026-09-20 | orchestrator | plan-audit FAIL(0.75) 5건 보정: (D8) frontmatter `tier: M` 추가. (D4) `single` × `palette_mode` 우선순위를 REQ-013/§2 D5/plan.md M2/AC-012에 명시(팔레트 충돌 해소가 먼저, single은 그 결과값을 그대로 반환). (D3) "Q2 다시"가 Q2B 답변도 폐기하는 부수효과를 REQ-016으로 신설하고 §2 D2에 명문화. (D1) REQ-004(기존 스텝 공백-답변 회귀)를 검증하는 AC-016 신설. (D2) 전체 AC 헤딩에 REQ 인용 추가 + §3 말미에 REQ→AC 추적 표 신설. minor 3건(D5 GEARS 태그 통일, D6 per_chorus 저-회차 경계, D7 skipped_steps 문서화)도 함께 반영. |

---

## §1 배경

카드 t404 (2026-09-13, 조명감독 지시): 「물론 곡과 조명감독의 스타일에 따라서 다르겠지. 그리고 조명감독의 확인을 받는게 좋을 것 같아.」

지금 인터뷰(`DirectorInterview`, `server/design/interview.py:151`)는 Q1(전체 컨셉) → Q2(팔레트) → Q3(클라이맥스) → Q4(공간 스토리) → Q5(전환 방식) 다섯 단계로 고정되어 있다. Q2에서 팔레트(어떤 색)는 확인하지만, **그 색을 곡 전체에 걸쳐 어떻게 쓸지**(한 계열로만 갈지 / 메인 중심으로 변조하다 임팩트에서 터뜨릴지 / 후렴마다 다른 포인트 색을 쓸지)는 묻지 않는다. 현재 구간별 팔레트 산출(`_section_palette_choice`, `server/web/session.py:1728`)은 곡·감독 스타일에 무관하게 항상 하나의 고정 로직(아크 회전)만 적용한다.

감독은 전역 기본값이 아니라 **곡마다** 이 축을 확인받고 싶어 한다. 기본값은 감독이 이미 밝힌 선호(「기본 설정은 메인 컬러를 중심으로 하되 각 부분마다 변조를 주고 임팩트를 줘야하는 곳에서 터뜨리는 게 맞아」)를 그대로 두되, 조용히 적용하지 않고 문항으로 띄워 확인받는다.

이 확인의 답은 분석 요약(카드 t387, `ui/src/components/analysisSummary.ts`)이 "왜 이 색인지"를 설명할 때 근거로 쓴다 — 근거 없이 지어내지 않는다는 그 파일의 기존 원칙(파일 상단 주석)을 그대로 따른다.

선행 카드 t402(#436, 팔레트 회차 회전) · t403(#436, 악센트 웨이트 사다리) · t406(#437, primary 우선 배치) 는 모두 main에 머지 완료.

## §2 결정 (확정 — 재검토 대상 아님)

이 절의 결정은 운영자가 위임한 최종 설계다. 아래 항목은 미해결 질문이 아니라 확정 사실로 기록한다.

### D1 — 새 인터뷰 스텝 Q2B_COLOR_USAGE

`STEP_ORDER`(`server/design/interview.py:151`)에 `Q2_PALETTE` 바로 다음, `Q3_CLIMAX` 이전에 새 스텝 `Q2B_COLOR_USAGE`를 삽입한다 (기존 5단계 → 6단계). 이 스텝의 질문 카드는 정확히 3개 옵션을 가지며(`QuestionCard.__post_init__`의 기존 불변식, `interview.py:260`), 순서는 다음과 같다:

1. (기본값, 첫 번째 옵션) 라벨 「메인 컬러 중심 변조 + 임팩트에서 터뜨림 (기본)」, value `"modulate"`
2. 라벨 「이 색 계열로만 간다」, value `"single"`
3. 라벨 「후렴마다 다른 포인트 색」, value `"per_chorus"`

카드의 `why` 필드는 2026-09-13 감독 지시를 인용한다. 자유 입력 파서는 다음 키워드를 인식한다: 단색/하나/only/single → `"single"`; 변조/기본/modulate/main → `"modulate"`; 후렴마다/포인트/per chorus/accent → `"per_chorus"`; 그 외는 기존 `_ParseFailure` 재질의 경로(`interview.py`의 `_parse_free_text` 계열, DI3 무추측 원칙)를 그대로 따른다.

### D2 — 재시작("Q3 다시") 의미 보존

`_SONG_RESTART`(`server/web/session.py:451`)와 그 사용처(`server/web/session.py:8617` `interview.restart_from(STEP_ORDER[int(...)-1])`)는 현재 "Q<N> 다시"의 N을 `STEP_ORDER`의 1-기반 인덱스로 직접 사용한다. Q2B를 `STEP_ORDER`에 삽입하면 이 직접 인덱싱이 깨진다("Q3 다시"가 더 이상 `Q3_CLIMAX`를 가리키지 않게 된다). 이를 막기 위해 번호/토큰 → 스텝의 **명시적 조회 테이블**을 도입한다: Q1~Q5는 지금과 동일하게 `Q3_CLIMAX` 등을 가리키고, 새 스텝은 "Q2B 다시" 또는 "색 운용 다시"로 별도 주소를 갖는다. `STEP_ORDER[N-1]` 형태의 암묵적 인덱싱은 더 이상 쓰지 않는다.

**"Q2 다시"의 부수효과(plan-audit D3, 의도된 동작)**: `restart_from(step)`(`interview.py:1153-1160`)는 `STEP_ORDER[STEP_ORDER.index(step):]` 구간 전체의 답변을 지운다. Q2B가 `Q2_PALETTE` 바로 다음에 삽입되므로, "Q2 다시"로 `Q2_PALETTE`를 재시작하면 그 이후 스텝인 `Q2B_COLOR_USAGE`의 답변도 함께 폐기된다 — 이 SPEC 도입 이전에는 존재하지 않았던 새 부수효과이지만, **의도된 동작**으로 확정한다: 색 운용(Q2B)의 답은 팔레트(Q2)에 종속적인 개념이므로, 팔레트가 바뀌면 그 팔레트를 어떻게 쓸지에 대한 답도 다시 확인받는 것이 맞다. 이 동작은 REQ-COLORMODE-016(§3)으로 명문화한다.

### D3 — 이 스텝만 기본값 수용 = 확정

다른 스텝(Q1/Q3/Q4/Q5)의 공백 답변은 `confirmed=False`, `source=SOURCE_AUTO_DRAFT`로 기록되어(`interview.py`의 `submit_answer`, 공백 분기) `song_cue_composer._requery_requirements`(`server/design/song_cue_composer.py:541`)가 재질의 카드를 만든다. Q2B는 다르다: 공백(또는 첫 옵션 그대로 통과) 답변은 `confirmed=True`, 새 출처 상수 `SOURCE_DEFAULT_ACCEPTED`로 기록되어 재질의 카드를 만들지 않는다 — 감독이 문항을 보았고 명시적으로 수용했다는 뜻이지 "모르겠다"가 아니기 때문이다. 값(첫 옵션의 `"modulate"`)은 여전히 기록된다.

### D4 — 새 결정 축 `color_usage`

`DecisionAxis`(`server/design/song_plan.py:59`)와 `_AXES`(같은 파일 79행)에 `"color_usage"`를 추가한다. `_DI_RECORD_AXES`(`server/web/session.py:468`)에 `Q2B_COLOR_USAGE → COLOR_USAGE_AXIS` 매핑을, `_DI_STEP_LABELS`(같은 파일 476행)에 「Q2B 색 운용」 라벨을 추가한다. 페이로드 직렬화(`server/web/session.py:2429` 부근)의 필드 모양(`step`/`axis`/`value`/`confirmed`/`source`)은 바뀌지 않는다 — 새 항목이 같은 배열에 하나 더 실릴 뿐이다.

분석 요약(`ui/src/components/analysisSummary.ts` `buildColorLine`, 44-64행)은 `director_decisions.find(axis === "palette")`에 더해 `axis === "color_usage"` 항목도 찾아, 운용 방식을 설명하는 한국어 문구를 팔레트 문장에 이어 붙인다. `source === "default_accepted"`(또는 그에 대응하는 값)일 때는 "(기본값 수용)" 표시를 덧붙인다. 기존 팔레트 문장은 바뀌지 않는다.

### D5 — 답이 실제 산출에 반영된다

`color_usage` 결정값은 `_section_palette_choice`(`server/web/session.py:1728`)의 구간별 팔레트 산출에 실제로 반영된다:

- `"modulate"` — 현재 동작과 **바이트 동일**(회귀 시험으로 증명). `_arc_palette`(`server/web/session.py:1062`) 회전 그대로.
- `"single"` — **`palette_mode`(concept/mixed) 충돌 해소가 먼저 실행되고, `single`은 그 해소 결과(resolved base)를 그대로 반환한다.** `_section_palette_choice`(`server/web/session.py:1728-1758`)는 구간 직접 색상(`direct_colors`) 분기 다음, `palette_mode`에 따라 `base`를 결정하는 if/elif/else 블록을 거쳐, 마지막에 공통 반환문에서 `_arc_palette(base, role, occurrence)`를 호출한다. `single`은 이 `base` 결정 블록과 공통 반환문 **사이**에 개입하는 새 분기다 — `base`가 이미 무엇으로 정해졌는지(`palette_mode="concept"`면 `concept_colors`, `"mixed"`면 역할에 따라 `concept_colors` 또는 프로필 팔레트, 그 외에는 `profile.palette or color_tendency`)와 **무관하게**, 그 `base`를 `_arc_palette` 회전 없이 그대로 반환한다. 즉 "Q2 base"라는 표현은 `palette_mode`가 기본(neither concept nor mixed)일 때만 문자 그대로 Q2 자체 팔레트를 뜻하고, `palette_mode="concept"`/`"mixed"`인 구간에서는 그 모드가 만든 concept/mixed 팔레트가 그대로 나간다. 구간 직접 색상(`section_text`)은 이 모든 것보다 앞서 처리되므로 `color_usage`와 무관하게 오늘과 동일하게 최우선이다. 출처 라벨은 구분 가능해야 한다(예: `"section_single"`).
- `"per_chorus"` — chorus(및 finale) 회차의 악센트는 **회차별로 서로 다른** 색을 뽑는 사다리에서 가져와, 연속된 두 후렴 회차가 같은 악센트를 갖지 않도록 한다(primary인 `base[0]`는 t409 판정대로 항상 첫 칸에 유지). chorus/finale 외 역할은 modulate 동작을 유지한다. **경계 사례(plan-audit D6)**: 곡 안에 후렴(또는 피날레) 회차가 정확히 1개뿐이면 비교할 이전 회차가 없으므로, 그 유일한 회차의 산출은 modulate 모드가 냈을 산출과 동일하다 — 별도 사다리 로직이 개입할 대상 자체가 없다.

임팩트 터뜨림(`_accent_decision`/`_occurrence_accent_label`, Q3 절정 채널)은 이 SPEC이 다루는 어느 모드에서도 변경하지 않는다.

## §3 요구사항 (GEARS)

- **REQ-COLORMODE-001** [Ubiquitous] The interview engine shall present exactly 6 steps in the fixed order Q1_CONCEPT → Q2_PALETTE → Q2B_COLOR_USAGE → Q3_CLIMAX → Q4_SPATIAL_STORY → Q5_TEXTURE.
- **REQ-COLORMODE-002** [Ubiquitous] The Q2B_COLOR_USAGE question card shall carry exactly 3 options, in the order (기본, "modulate") / ("single") / ("per_chorus"), with `why` citing the 2026-09-13 director instruction.
- **REQ-COLORMODE-003** [Event-driven] **When** the director submits a blank answer to Q2B_COLOR_USAGE, the interview engine shall record the first option's value (`"modulate"`) with `confirmed=True` and `source=SOURCE_DEFAULT_ACCEPTED`.
- **REQ-COLORMODE-004** [Ubiquitous] Every interview step other than Q2B_COLOR_USAGE shall retain byte-identical blank-answer behaviour (`confirmed=False`, `source=SOURCE_AUTO_DRAFT`).
- **REQ-COLORMODE-005** [Event-driven] **When** the director's free-text answer to Q2B_COLOR_USAGE matches a recognized keyword group (단색/하나/only/single, 변조/기본/modulate/main, 후렴마다/포인트/per chorus/accent), the interview engine shall resolve it to the corresponding value with `confirmed=True` and `source=SOURCE_FREE_TEXT`.
- **REQ-COLORMODE-006** [Event-driven] **When** the director's free-text answer to Q2B_COLOR_USAGE matches none of the recognized keyword groups, the interview engine shall return an unresolved-answer result and re-present the same card (no card advance), following the existing 3-attempt cap.
- **REQ-COLORMODE-007** [Event-driven] **When** the director sends "Q3 다시" (or the equivalent restart phrase for any existing Q1/Q4/Q5 step), the interview engine shall restart from that same step exactly as before Q2B_COLOR_USAGE existed.
- **REQ-COLORMODE-008** [Event-driven] **When** the director sends "Q2B 다시" or "색 운용 다시", the interview engine shall restart the interview from Q2B_COLOR_USAGE, preserving every earlier answer.
- **REQ-COLORMODE-009** [Ubiquitous] The song plan's `director_decisions` list shall contain, for the Q2B_COLOR_USAGE step, an entry with `axis="color_usage"`, `value` ∈ {"modulate","single","per_chorus"}, `confirmed`, and `source`.
- **REQ-COLORMODE-010** [Event-driven] **When** a Q2B_COLOR_USAGE decision is recorded with `confirmed=True` via the default-accepted path, the requery-requirement builder shall NOT create a re-ask card for that decision.
- **REQ-COLORMODE-011** [Where] Where the timeline payload carries a `color_usage`-axis decision, the analysis summary component shall append a Korean clause describing the usage mode to the existing color line, including a "(기본값 수용)" marker when the source is default-accepted.
- **REQ-COLORMODE-012** [State-driven] **While** the recorded `color_usage` value is `"modulate"`, the section palette computation shall produce output byte-identical to the pre-SPEC behaviour for every existing regression fixture.
- **REQ-COLORMODE-013** [State-driven] **While** the recorded `color_usage` value is `"single"`, the section palette computation shall return, unmodified for every section role and occurrence, the base palette that `palette_mode` conflict resolution already produced for that section (the Q2 profile palette when `palette_mode` is neither `"concept"` nor `"mixed"`; the concept/mixed base when it is) — resolved AFTER `palette_mode` resolution and BEFORE the `_arc_palette` rotation call, and never before a `section_text` direct-color match, which still takes precedence over `color_usage` entirely.
- **REQ-COLORMODE-014** [State-driven] **While** the recorded `color_usage` value is `"per_chorus"`, the section palette computation shall assign chorus and finale occurrences accents such that no two consecutive occurrences of the same role share the same accent color, while keeping `base[0]` (primary) first and leaving non-chorus/finale roles on the modulate behaviour; **while** a song contains exactly one chorus (or finale) occurrence, that occurrence's output shall be identical to what the modulate mode would produce for it (no prior occurrence exists to differ from).
- **REQ-COLORMODE-015** [Ubiquitous] The `DecisionAxis` type and its validation set shall include `"color_usage"` alongside the existing five axes.
- **REQ-COLORMODE-016** [Event-driven] **When** the director sends "Q2 다시", the interview engine shall restart from Q2_PALETTE, discarding both the Q2 palette answer and the Q2B_COLOR_USAGE answer (the standard `restart_from` suffix-drop semantics extended downstream by one step), and re-ask Q2B_COLOR_USAGE once Q2 is re-answered.

### REQ → AC 추적 표

| REQ | 검증 AC |
|---|---|
| REQ-COLORMODE-001 | AC-COLORMODE-001, AC-COLORMODE-014 |
| REQ-COLORMODE-002 | AC-COLORMODE-001, AC-COLORMODE-004 |
| REQ-COLORMODE-003 | AC-COLORMODE-002 |
| REQ-COLORMODE-004 | AC-COLORMODE-016 |
| REQ-COLORMODE-005 | AC-COLORMODE-004 |
| REQ-COLORMODE-006 | AC-COLORMODE-005 |
| REQ-COLORMODE-007 | AC-COLORMODE-006 |
| REQ-COLORMODE-008 | AC-COLORMODE-007 |
| REQ-COLORMODE-009 | AC-COLORMODE-008 |
| REQ-COLORMODE-010 | AC-COLORMODE-003 |
| REQ-COLORMODE-011 | AC-COLORMODE-009, AC-COLORMODE-010 |
| REQ-COLORMODE-012 | AC-COLORMODE-011 |
| REQ-COLORMODE-013 | AC-COLORMODE-012 |
| REQ-COLORMODE-014 | AC-COLORMODE-013 |
| REQ-COLORMODE-015 | AC-COLORMODE-008 |
| REQ-COLORMODE-016 | AC-COLORMODE-015 |

모든 REQ가 최소 1개의 AC로 검증되며(orphan 없음), 모든 AC는 최소 1개의 REQ를 인용한다(acceptance.md 각 AC 헤딩 참고).

## §4 제외 범위

### Out of Scope — 기존 인터뷰 문항 변경
- Q1/Q2/Q3/Q4/Q5의 질문 문구·옵션 구성·파서 로직은 변경하지 않는다.
- 기존 재질의(requery) 메커니즘(`song_cue_composer._requery_requirements`)의 일반 동작은 변경하지 않는다 — Q2B 전용 default-accepted 예외만 추가한다.

### Out of Scope — UI 렌더링
- `SongTimeline.tsx`의 `DecisionRail`은 이미 모든 결정을 축 무관하게 범용 렌더링하므로 이 SPEC에서 변경하지 않는다.
- 큐 시트 컴포저(`song_cue_composer.py`)의 출력 모양(스키마)은 변경하지 않는다.

### Out of Scope — 콘솔 송신
- 콘솔 쓰기 경로(`bundle_sender` 등)는 이 SPEC의 대상이 아니다. 색 운용 답은 서버 내부 산출(팔레트 계산)에만 반영되며, 콘솔로 나가는 방식 자체는 바꾸지 않는다.

### Out of Scope — 임팩트 터뜨림(Q3 채널)
- `_accent_decision`/`_occurrence_accent_label`(Q3 절정 답변 채널)은 색 운용(Q2B) 답과 별개 채널로 유지하며, 이 SPEC에서 로직을 바꾸지 않는다.

### Out of Scope — 색상 팔레트 확장
- 표준 팔레트 10색(SPEC-COPILOT-COLORPRESET-001 §A.2) 자체의 확장이나 새 RGB 추가는 하지 않는다. `per_chorus` 사다리도 기존 표준 팔레트 안에서만 색을 고른다.

## §5 관련 SPEC

- `SPEC-COPILOT-COLORPRESET-001` — 표준 10색 팔레트 정의(§A.2), 이 SPEC이 참조만 하고 확장하지 않음.
- 카드 t402/t403/t406 (관련 PR #436, #437) — `_arc_palette`, `_ACCENT_WEIGHT_LADDER`, primary-first 배치. 이 SPEC의 "modulate" 모드는 이 선행 작업의 동작을 그대로 보존한다.
