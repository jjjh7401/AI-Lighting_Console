# SPEC-COPILOT-COLORMODE-001 — 구현 계획

## §A 컨텍스트

- 워크트리: `t404`, 브랜치 `WT-color-usage-question`, base `main 91695109`.
- 대상 코드: `server/design/interview.py`(인터뷰 엔진), `server/web/session.py`(전송·재시작·팔레트 산출), `server/design/song_plan.py`(결정 축 타입), `server/design/song_cue_composer.py`(재질의 판정, 읽기만 함), `ui/src/components/analysisSummary.ts`(요약 문장).
- Tier: M. 마일스톤 2개, 예상 변경 파일 ~8개.
- 근거: `research.md`의 실측 file:line 인용을 그대로 따른다. 이 문서는 무엇을 어떤 순서로 바꿀지만 다룬다 — 정확한 구현 코드는 run-phase에서 확정한다.

## §B 마일스톤 순서 원칙

되돌리기 어려운 결정(새 타입·데이터 모델·사용자 대면 문항 순서)을 먼저 배치하고, 기계적인 배선·회귀 시험은 뒤로 미룬다. M1이 "무엇을 묻고 어떻게 기록하는가"(데이터 모델 확정), M2가 "그 답을 산출에 어떻게 반영하는가"(순수 함수 내부 구현)다 — M1의 결정이 잘못되면 M2 전체가 다시 쓰여야 하므로 M1을 먼저 검증한다.

## §C 마일스톤

### M1 — 문항 + 기록 + 요약 (데이터 모델 확정, 되돌리기 어려움)

가장 되돌리기 어려운 결정: 새 인터뷰 스텝 ID, 새 결정 축 이름, 재시작 주소 체계. 이 셋은 한 번 정하면 이후 축적되는 답변 데이터(`director_decisions` 리스트)의 스키마가 되므로 먼저 고정한다.

1. **`server/design/interview.py`**
   - `STEP_ORDER`에 `Q2_PALETTE`와 `Q3_CLIMAX` 사이에 `Q2B_COLOR_USAGE` 삽입(D1).
   - 새 소스 상수 `SOURCE_DEFAULT_ACCEPTED` 추가(D3).
   - `QuestionCard`에 `default_confirms: bool = False` 필드 추가(기본 False로 기존 카드 전부 무영향). Q2B 빌더만 `default_confirms=True`로 생성.
   - `submit_answer`의 공백 분기에서 `card.default_confirms`가 True면 `confirmed=True`, `source=SOURCE_DEFAULT_ACCEPTED`로 기록(그 외 카드는 기존 `confirmed=False`/`SOURCE_AUTO_DRAFT` 경로 그대로).
   - `_build_q2b` 빌더 추가: 3옵션 고정 순서(기본 modulate / single / per_chorus), `why`에 감독 지시 인용.
   - `_STEP_BUILDERS`에 `Q2B_COLOR_USAGE: _build_q2b` 등록.
   - 자유 텍스트 파서에 Q2B 분기 추가(키워드 매핑, §2 D1의 인식 목록).
2. **`server/web/session.py`**
   - `_SONG_RESTART`(451행)의 암묵적 `STEP_ORDER[N-1]` 인덱싱을 제거하고, 번호/토큰 → 스텝의 명시적 조회 테이블로 교체(D2). 정규식은 기존 "Q<1-5> 다시"에 더해 "Q2B 다시"·"색 운용 다시"를 인식하도록 확장. "Q2 다시"는 조회 테이블 교체 후에도 `Q2_PALETTE`를 가리키며, `interview.restart_from`의 기존 suffix-drop 동작(변경 없음)이 그 결과로 `Q2B_COLOR_USAGE` 답변까지 폐기한다 — 이는 새 코드가 아니라 기존 `restart_from` 시맨틱의 자연스러운 귀결이다(REQ-COLORMODE-016, spec.md §2 D2 참고).
   - `_DI_RECORD_AXES`(468행)에 `Q2B_COLOR_USAGE: COLOR_USAGE_AXIS` 추가.
   - `_DI_STEP_LABELS`(476행)에 `Q2B_COLOR_USAGE: "Q2B 색 운용"` 추가.
   - `_song_run_interview`(8603행)의 카드 루프·재시작 처리는 조회 테이블 교체 외 변경 없음 — 6단계 루프는 기존 `while not interview.is_complete()` 그대로 동작.
3. **`server/design/song_plan.py`**
   - `DecisionAxis` Literal과 `_AXES` frozenset에 `"color_usage"` 추가, `COLOR_USAGE_AXIS = "color_usage"` 상수 추가(D4).
   - `DirectorDecision.to_dict()`/`from_audit_record()`는 축 값이 늘어난 것 외 변경 없음(기존 필드 모양 유지).
4. **`ui/src/components/analysisSummary.ts`**
   - `buildColorLine`(44-64행)에 `color_usage` 축 조회 분기 추가. 세 값(modulate/single/per_chorus) 각각의 한국어 설명 문구, `source`가 default-accepted 계열일 때 "(기본값 수용)" 부기.
5. **시험 갱신** (M1의 데이터 모델이 옳은지 확인하는 관문)
   - `server/tests/test_design_interview.py` — `TestQ2bColorUsageOptions` 신규 클래스(정확히 3옵션·기본 순서·why 인용), `TestSequentialProgress`/`TestAuditTrail` 등 기존 스텝-수 의존 시험 갱신, 공백 답변이 `confirmed=True`가 되는 Q2B 전용 케이스 추가. **`TestNoAnswerAutoDraft` 확장(plan-audit D1/AC-COLORMODE-016)**: Q1/Q3/Q4/Q5(및 Q2)가 공백 답변에서 여전히 `confirmed=False`/`SOURCE_AUTO_DRAFT`임을 파라미터화 케이스로 회귀 확인 — Q2B 삽입이 다른 스텝의 동작을 바꾸지 않았음을 이 케이스로 증명한다. **`TestPartialRestart` 확장(plan-audit D3/AC-COLORMODE-015)**: Q1~Q2B까지 답한 뒤 `restart_from(Q2_PALETTE)`를 호출하면 `answers`에서 `Q2B_COLOR_USAGE`가 사라지고 `current_step == Q2_PALETTE`이며, Q2 재답변 후 다음 카드가 다시 Q2B임을 확인.
   - `server/tests/test_web_session.py` — `TestSongDesignInterviewSession`의 답변 리스트에 Q2B 답변 1개 삽입, `len(channel.asked) == 6` → `== 7`, prompt 리스트에 Q2B 문항 3번째 삽입 확인(6214/6502/6529행 유사 케이스 동일 갱신).
   - `server/tests/test_song_timeline_decision_sources.py` — `color_usage` 축 결정이 페이로드에 실리는지, `source`가 타임라인까지 살아남는지 확인.
   - `ui/src/components/analysisSummary.test.ts` — 세 모드 + 기본값 수용 마커 각각의 색 라인 문구 fixture 추가(60-71/90-93행 패턴 재사용).

### M2 — 운용 방식 반영 (순수 함수 내부, 기계적 배선)

M1에서 확정된 `color_usage` 값을 실제 팔레트 산출에 연결한다. 새 타입이나 스키마 변경 없이 기존 함수 내부 분기만 추가하므로 M1보다 되돌리기 쉽다.

1. **`server/web/session.py`**
   - `_build_unified_song_plan`(1836행)에서 `plan.director_decisions`(또는 인터뷰 답변)로부터 `color_usage` 값을 읽어 `_SongDesignState` 또는 동등한 상태에 스레딩.
   - `_section_palette_choice`(1728-1758행)에 `color_usage` 파라미터 추가. **개입 지점을 정확히 명명한다(plan-audit D4 보정)**: 함수 본문은 (a) `direct_colors`(구간 직접 색상) 조기 반환, (b) `if palette_mode == "concept" ... elif palette_mode == "mixed" ... else: base = _palette_colors(...)` 블록(=`base` 확정), (c) 공통 반환문 `return (_arc_palette(base, role, occurrence), "section_arc", _arc_accent_weight(role, occurrence))` 세 부분으로 구성된다. `color_usage` 분기는 **(b)와 (c) 사이**, 즉 `base`가 이미 확정된 직후·`_arc_palette` 호출 이전에 삽입한다:
     - `"modulate"`(기본) — 분기 없이 그대로 (c)로 진행(회귀 시험이 바이트 동일함을 증명).
     - `"single"` — (c)의 `_arc_palette(base, ...)` 호출을 건너뛰고 `return (base, "section_single", None)`을 (b) 직후 반환한다. `palette_mode`가 concept/mixed이면 그 `base`(=concept_colors 또는 역할별 결정값)가 그대로 나가고, 기본 모드면 Q2 자체 팔레트가 나간다 — palette_mode 해소를 우회하지 않는다(REQ-COLORMODE-013).
     - `"per_chorus"` — chorus/finale 역할에서 회차별로 서로 다른 악센트를 뽑는 사다리 적용(연속 회차 비반복 보장; 회차가 1개뿐이면 modulate와 동일 산출). 구체적 사다리 후보 색 순서는 표준 팔레트 10색(SPEC-COPILOT-COLORPRESET-001 §A.2) 안에서 run-phase에 확정.
   - 두 호출부(`_section_palette_sizes` 1764행, `_build_unified_song_plan` 내부 1949행 부근) 모두에 `color_usage`를 전달.
2. **시험**
   - `server/tests/test_song_color_usage_t404.py` 신규 — (i) modulate가 기존 fixture와 바이트 동일함을 특성화 시험(characterization test)으로 증명, (ii) single이 기본 palette_mode에서 모든 역할·회차에 base를 반환함을 증명 **+ `palette_mode="concept"`일 때 concept base를 반환함을 별도로 증명(plan-audit D4/AC-COLORMODE-012)**, (iii) per_chorus가 연속 후렴 회차에서 서로 다른 악센트를 냄을 증명(그리고 `base[0]`가 항상 첫 칸임을 재확인) **+ 후렴 회차가 1개뿐일 때 modulate와 동일함을 별도로 증명(plan-audit D6/AC-COLORMODE-013)**.
   - 기존 `test_song_palette_occurrence_t402.py` / `test_song_accent_ladder_t403.py` / `test_arc_fx_occurrence_t405.py` / `test_song_palette_occurrence_t406.py`는 default(`"modulate"`) 경로에서 그대로 초록이어야 한다(회귀 확인 관문).

## §D 기술 접근 요약

- 새 상태 없이 기존 `DirectorInterview`/`AnswerRecord`/`DirectorDecision` 파이프라인에 스텝 하나·축 하나를 추가하는 방식 — 새 클래스나 새 프로토콜을 만들지 않는다(Enforce Simplicity).
- "modulate = 바이트 동일" 요구사항이 회귀 안전망 역할을 한다 — 기본값 경로를 건드리지 않고 두 개의 새 경로(single/per_chorus)만 추가하는 구조.
- `_SONG_RESTART`의 인덱싱 방식 교체(D2)는 이 SPEC에서 가장 위험한 리팩터 지점이다 — 기존 5개 문자열("Q1 다시"~"Q5 다시")의 라우팅이 회귀하지 않는지가 M1의 시험 관문에서 최우선으로 확인되어야 한다.

## §E 위험

| 위험 | 완화 |
|---|---|
| `STEP_ORDER` 삽입이 `STEP_ORDER[N-1]` 암묵 인덱싱을 쓰는 다른 호출부를 놓칠 수 있다 | M1 시작 시 `grep -n "STEP_ORDER\["` 전수 조사를 run-phase 착수 조건으로 명시 |
| "per_chorus" 사다리의 정확한 색 순서가 표준 팔레트와 충돌할 수 있다 | 표준 팔레트 10색 상수를 새로 만들지 않고 기존 `_ARC_PALETTE`/`_distinct_from_primary`가 이미 참조하는 팔레트 소스를 재사용 |
| `_requery_requirements`가 Q2B의 `confirmed=True` 항목을 건너뛰지 못하면 감독에게 불필요한 재질의 카드가 뜬다 | `song_cue_composer.py:541`의 `if decision.confirmed: continue` 분기가 축 무관하게 이미 동작함을 확인했다(연구 근거) — 별도 예외 코드 불필요, 시험으로 확인만 |
| 분석 요약에 두 축(palette·color_usage)을 이어 붙이면 문장이 길어져 가독성이 떨어질 수 있다 | 기존 `·` 구분자 패턴을 그대로 따르고 문구를 한 절로 짧게 유지 |

## §F 완료 정의(요약)

- M1: 6단계 인터뷰가 실물 fixture에서 정확히 7장 카드(6문항 + 리뷰)를 낸다. `color_usage` 축이 페이로드·분석 요약에 나타난다.
- M2: 세 모드 모두 산출 팔레트가 사양대로 달라지고, modulate 기본값은 기존 시험이 전부 그대로 초록이다.
