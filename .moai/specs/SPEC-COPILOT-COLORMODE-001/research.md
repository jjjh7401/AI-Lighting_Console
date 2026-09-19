# SPEC-COPILOT-COLORMODE-001 — 리서치 노트

측정 기준: 워크트리 `t404`, HEAD `91695109`(main), 2026-09-20 read-only Explore 패스 + 이 문서 작성 중 재확인한 스팟체크. 아래 인용은 이 커밋에서 직접 읽은 코드다.

## 1. 인터뷰 엔진 골격

- `server/design/interview.py:151` — `STEP_ORDER: tuple[str, ...] = (Q1_CONCEPT, Q2_PALETTE, Q3_CLIMAX, Q4_SPATIAL_STORY, Q5_TEXTURE)`. 현재 정확히 5단계. 카드 t404 원문의 "8단계"는 인터뷰 카드가 아니라 `session.py`가 별도로 묻는 타이밍 방식·타임코드 번호·레이어 매핑 확인까지 합친 숫자다(인터뷰 자체는 5).
- `server/design/interview.py:157` 부근 — 소스 상수 `SOURCE_OPTION = "option"`, `SOURCE_FREE_TEXT = "free_text"`, `SOURCE_PRE_SPECIFIED = "pre_specified"`, `SOURCE_AUTO_DRAFT = "auto_draft"`. 새 상수 `SOURCE_DEFAULT_ACCEPTED`는 이 그룹에 추가한다.
- `server/design/interview.py:249-263` — `QuestionCard.__post_init__`이 `len(self.options) != 3`이면 `InterviewError`를 던진다. 이 불변식은 Q2B에도 그대로 적용된다.
- `server/design/interview.py:892-900` — `build_question(step, profile, rig)`이 `_STEP_BUILDERS` 딕셔너리(883-889행)로 스텝별 빌더에 위임한다. Q2B는 `_STEP_BUILDERS`에 새 엔트리로 등록한다.
- `server/design/interview.py:1088-1151` — `submit_answer`. 공백 답변(1105-1117행)은 `card.options[0].value`를 `confirmed=False`/`SOURCE_AUTO_DRAFT`로 기록한다. 이 분기에 `card.default_confirms` 조건을 추가해 Q2B만 다르게 분기시킨다.
- `server/design/interview.py:1153-1160` — `restart_from(step)`는 `STEP_ORDER.index(step)`부터 이후 모든 스텝의 답변을 지운다. 스텝 이름만 받으므로 D2의 번호→스텝 조회 테이블 교체와 이 함수 자체는 무관하다(호출부만 바뀐다).
- `server/design/interview.py:443-475` — `_project_director_decision(step, value, profile)`. Q3/Q4/Q5에서만 `DirectorDecisionProjection`(내부 `MusicProfile` 갱신용, `song_plan.DirectorDecision`과는 다른 클래스)을 만든다. Q1/Q2/Q2B는 `None`을 반환하며 이는 기존 동작과 같다 — Q2B가 working profile을 갱신할 필요가 없으므로 이 함수는 변경 불필요.
- `server/design/interview.py:1005,1019,1072` — `skipped_steps` 메커니즘(plan-audit D7). `DirectorInterview.__init__`이 `skipped_steps: Sequence[str] = ()`를 받아 `frozenset`으로 저장하고(1019행), `is_complete`류 판정(1072행)이 `step not in self.answers and step not in self.skipped_steps`로 미답변-스킵을 구분한다. **현재 유일한 사용처는 `Q4_SPATIAL_STORY`**다 — `server/web/session.py:8492` 부근에서 위치 지정 가능한 rig가 없을 때 Q4를 건너뛰기 위해서만 쓰인다. **Q2B_COLOR_USAGE는 이 SPEC 어디에서도 `skipped_steps`에 들어가지 않는다** — 색 운용 확인은 rig 능력과 무관하게 항상 묻는 문항이므로 스킵 후보가 아니다. `current_step`/`is_complete`는 `STEP_ORDER`를 동적으로 순회하므로 Q2B 삽입에 자동 적응하며, 이 메커니즘과 기능적으로 충돌하지 않는다(문서 완결성 보완, 로직 변경 없음).

## 2. 전송·재시작 (`server/web/session.py`)

- `server/web/session.py:451` — `_SONG_RESTART = re.compile(r"[Qq]\s*(?P<no>[1-5])\s*(?:만)?\s*다시")`. 1~5 한 자리 숫자만 인식.
- `server/web/session.py:8615-8617` — 사용처: `restart_match = _SONG_RESTART.search(raw_answer)` 다음 `interview.restart_from(STEP_ORDER[int(restart_match.group("no")) - 1])`. **이것이 D2의 정확한 위험 지점이다** — 지금은 "Q3"의 3을 그대로 `STEP_ORDER[2]`에 꽂는다. Q2B를 `STEP_ORDER`에 삽입하면 `STEP_ORDER[2]`가 `Q3_CLIMAX`가 아니라 `Q2B_COLOR_USAGE`로 바뀌어 "Q3 다시"가 잘못된 스텝을 재시작하게 된다 — 확인된 회귀 위험, D2가 이를 명시적 조회 테이블로 대체하는 이유.
- `server/web/session.py:468-474` — `_DI_RECORD_AXES = {Q1_CONCEPT: PALETTE_AXIS, Q2_PALETTE: PALETTE_AXIS, Q3_CLIMAX: D_AXIS, Q4_SPATIAL_STORY: POSITION_AXIS, Q5_TEXTURE: TEXTURE_AXIS}`. 이 딕셔너리에 없는 스텝은 `_director_decisions`(540-548행)에서 조용히 걸러진다(`axis = _DI_RECORD_AXES.get(step); if axis is None: continue`) — Q2B를 여기 추가하지 않으면 답변이 있어도 `director_decisions`에 실리지 않는다.
- `server/web/session.py:476-481` — `_DI_STEP_LABELS`. 감사 로그 문구(`server/web/session.py:10536-10539` 부근 `_describe_di_value` 호출부)에서 쓰인다.
- `server/web/session.py:8603-8630` — `_song_run_interview`. `while not interview.is_complete()` 루프가 스텝 수와 무관하게 동작하므로, `STEP_ORDER`에 스텝이 하나 늘어도 이 루프 자체의 반복 로직은 변경이 필요 없다(다만 재시작 처리 라인은 D2대로 교체).
- `server/web/session.py:2415-2439` — 타임라인 페이로드 직렬화. `director_decisions`는 `{step, axis, value, confirmed, source}` 다섯 필드만 얕게 뽑아 실린다(`decision.to_dict()["value"]`로 값만 재사용, 다른 필드는 `song_plan.DirectorDecision`의 속성에서 직접). `DirectorDecision.to_dict()`(아래 §3) 자체는 `section_index`/`free_text`/`choice_label`까지 갖고 있지만 페이로드는 그 서브셋만 노출한다 — AC-COLORMODE-008이 이 서브셋 모양을 근거로 한다.

## 3. 결정 축 타입 (`server/design/song_plan.py`)

- `server/design/song_plan.py:59` — `DecisionAxis = Literal["d", "palette", "position", "texture", "fx", "accent"]`. `"color_usage"`는 여기에 추가하는 리터럴이다.
- `server/design/song_plan.py:63-68` — `D_AXIS`/`PALETTE_AXIS`/... 상수. `COLOR_USAGE_AXIS = "color_usage"`를 같은 그룹에 추가.
- `server/design/song_plan.py:79-81` — `_AXES: frozenset[str] = frozenset((D_AXIS, PALETTE_AXIS, POSITION_AXIS, TEXTURE_AXIS, FX_AXIS, ACCENT_AXIS))`. `_validate_axis`(122-124행)가 이 집합 밖의 축이면 `SongPlanError`를 던진다 — `COLOR_USAGE_AXIS`를 여기 추가하지 않으면 `DirectorDecision.__post_init__`이 즉시 실패한다.
- `server/design/song_plan.py:452-506` — `DirectorDecision` 데이터클래스, `from_audit_record`(클래스메서드, 473-489행)가 `AnswerRecord`를 감싸 `DirectorDecision`을 만드는 유일한 생산자. `to_dict()`(491-502행)는 8개 필드를 전부 직렬화하지만(§2에서 확인했듯 페이로드는 그 서브셋만 노출).

## 4. 재질의 게이트 (`server/design/song_cue_composer.py`)

- `server/design/song_cue_composer.py:541-556` — `_requery_requirements`. `for decision in plan.director_decisions: if decision.confirmed: continue` (546-547행). **이 조건은 이미 축(axis) 무관하게 동작한다** — D3에서 Q2B가 `confirmed=True`로 기록되기만 하면 이 함수는 별도 코드 없이 자동으로 Q2B용 재질의 카드를 만들지 않는다. AC-COLORMODE-003의 근거.

## 5. 분석 요약 (`ui/src/components/analysisSummary.ts`)

- `ui/src/components/analysisSummary.ts:1-7` — 파일 상단 원칙: "값에 출처가 없으면 그 줄 자체를 안 낸다 — 그럴듯한 이유를 지어내지 않는다." Q2B도 같은 원칙을 따른다(값이 없으면 절을 추가하지 않는다 — 다만 Q2B는 항상 값이 있다, D3의 default-accepted 덕분에 "미확정"으로 비는 경우가 없다).
- `ui/src/components/analysisSummary.ts:44-64` — `buildColorLine(timeline)`. `timeline.director_decisions.find((d) => d.axis === "palette")`로 **첫 번째 palette축 항목**(배열 순서상 Q1이 Q2보다 먼저 push되므로 사실상 Q1)을 찾아 `감독 지정(${step}): ${value}` 절을 만들고, 이어서 구간 역할 집합을 훑어 두 번째 절을 붙인다. `color_usage` 분기는 이 함수에 세 번째 절로 추가한다 — 기존 두 절의 로직·순서는 변경하지 않는다.
- `ui/src/protocol.ts:295,387` — `SongTimelineDecision`의 `axis` 필드는 `string`(리터럴 유니온 아님) — TS 쪽은 `"color_usage"` 문자열을 그대로 받아도 타입 에러가 나지 않는다. 다만 가독성을 위해 필요시 유니온을 넓히는 것을 M1에서 검토한다(스키마 변경은 아님).

## 6. 팔레트 산출 — 실제 반영 지점 (`server/web/session.py`)

- `server/web/session.py:1728-1758` — `_section_palette_choice(section, *, role, profile, color_tendency, palette_mode, concept_colors, occurrence=1)`. 우선순위: 구간 자체 색 단어(`section_text`) > `palette_mode` 충돌 해소(concept/mixed) > Q2 팔레트 + 아크 회전(`_arc_palette`). `color_usage` 파라미터는 세 번째 분기(else, base 계산 이후 `_arc_palette` 호출 지점)에 개입해야 한다 — 구간이 직접 색을 적은 경로(`direct_colors`)는 이 SPEC의 영향을 받지 않는다(§2 결정 D5의 "구간이 직접 색을 적었거나... 영향받지 않는다"와 일치하는 기존 주석, 1741-1743행).
- `server/web/session.py:1764-1792` — `_section_palette_sizes`(호출부 1). 큐 밀도 판정용 — 재질의 오버라이드는 아직 반영 전이므로 사이즈만 참고. `color_usage`를 여기도 전달해야 밀도 판정이 실제 산출과 어긋나지 않는다.
- `server/web/session.py:1836` — `_build_unified_song_plan`(호출부 2, 실제 프로덕션 경로). 1949-1957행에서 `_section_palette_choice`를 `occurrence=occurrence`와 함께 호출 — `color_usage`를 여기도 전달해야 한다.
- `server/web/session.py:1852-1892` 부근 — `occurrence_by_head`/`role_running` — 역할별 회차(occurrence) 카운팅이 이미 존재한다(카드 t402). `per_chorus` 모드의 "연속 회차" 판정은 이 기존 카운터를 그대로 재사용할 수 있다 — 새 카운팅 메커니즘이 필요 없다.
- `server/web/session.py:1062-1097` — `_arc_palette(base, role, occurrence)`. `_ARC_PALETTE.get(role)`(796-802행 정의, `chorus: ("warm white", "magenta")` 등 역할당 2색 고정 튜플)를 `rotate_palette(arc, occurrence-1)`로 회전한다. **스팟체크 결과**: `chorus`의 아크가 길이 2이므로 `occurrence` N과 N+1의 회전 결과는 항상 다르지만(주기 2), N과 N+2는 같은 값으로 돌아온다 — 즉 현재 "modulate" 경로는 우연히 인접 회차끼리는 다르지만 3회차 이상 반복되면 색이 순환 반복된다. 감독의 원 요청("후렴마다 다른 포인트 색")은 매 회차가 서로 다르길 원하는 것으로 읽히므로, `per_chorus` 모드는 이 2색 고정 아크가 아니라 더 넓은 사다리(표준 팔레트 10색 범위 내)에서 뽑아야 한다 — plan.md §C M2가 이를 run-phase 확정 사항으로 남긴 이유.
- `server/web/session.py:1026-1032` — `_distinct_from_primary(candidate, primary, fallback)`. t406 핫픽스로 아크 회전 색이 primary와 겹치는 경우를 걸러낸다. `per_chorus` 사다리도 이 함수를 재사용해 primary와의 충돌을 막아야 한다.
- `server/web/session.py:1049-1050` — `_ACCENT_WEIGHT_LADDER = ("", "짙은", "연한", "쿨톤", "웜톤")`. 이것은 색이 아니라 채도/톤 수식어 사다리(t403, 색과 분리된 채널) — `per_chorus`의 "다른 색" 요구와는 다른 축이므로 혼동하지 않는다.

## 7. 표준 팔레트 출처

- `.moai/specs/SPEC-COPILOT-COLORPRESET-001/spec.md` §A.2 — 표준 10색 팔레트 정의(원문 인용: `server/web/session.py:790-795` 주석 "표준 팔레트 10색(spec.md §A.2)"). `per_chorus` 사다리는 새 RGB를 짓지 않고 이 10색 안에서만 순환한다(spec.md §4 제외 범위와 일치).

## 8. 시험 좌표 (스팟체크로 확인한 정확한 라인)

- `server/tests/test_design_interview.py:52` — `TestBuildQuestionExactlyThreeOptions`. `:711` — `TestAuditTrail`. `:431` — `TestSequentialProgress`. `:562` — `TestNoAnswerAutoDraft`. `:584` — `TestUnresolvedFreeTextReAsks`. `:670` — `TestPartialRestart`.
- `server/tests/test_web_session.py:4717` — `class TestSongDesignInterviewSession`. `:4853-4860` — `_Channel` fake(`ask`가 `answers.pop(0)` 또는 `UNANSWERED`). `:4867` — `test_full_choice_flow_previews_before_any_write_and_asks_for_approval`: 답변 리스트 5개(`["우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]`), `assert len(channel.asked) == 6`(5문항 + 리뷰), `asked[:5]`의 prompt 리스트를 정확한 문자열로 단언. Q2B 삽입 시 답변 리스트에 항목 1개(Q2 다음)가 추가되고 `== 6` → `== 7`, prompt 리스트에 3번째 문항이 새로 삽입된다.
- `server/tests/test_song_timeline_decision_sources.py:1-40` — 파일 목적 자체가 "구간별 결정의 출처가 페이로드에 실리는지"를 재는 시험 모음 — `color_usage` 축의 출처 보존을 검증하기에 정확히 맞는 위치.
- `server/tests/test_song_palette_occurrence_t402.py`, `test_song_accent_ladder_t403.py`, `test_arc_fx_occurrence_t405.py`, `test_song_palette_occurrence_t406.py` — 존재 확인됨(`ls server/tests/`). 이름이 카드 번호를 따르되 t406용 시험 파일명은 `test_song_palette_occurrence_t406.py`다(원 리서치 노트가 "t405"로 뭉뚱그린 부분을 이 문서에서 파일명 기준으로 바로잡음).

## 9. 리서치 중 발견한 수정 사항 (원 위임 브리프 대비)

- 위임 브리프는 `_section_palette_choice`의 결정 지점을 "session.py:1728-1761"로 기술했다 — 실측 결과 함수 정의는 1728행에서 시작해 1758행에서 끝난다(오차 3줄, 실질적 영향 없음).
- 위임 브리프는 t406 전용 시험 파일을 명시하지 않았다 — 실측 결과 `test_song_palette_occurrence_t406.py`가 별도로 존재한다. plan.md M2 회귀 목록에 추가했다.
- 그 외 인용된 file:line은 모두 이 문서의 스팟체크로 확인됨(§1-§4, §6).
