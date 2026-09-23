# t436 판정 — SPEC-LDDESIGN-001 M3 컨셉 계층 + 컬러 규칙 (REQ-026~035)

- 카드: t436 (클래스 C), 레인 lane-2
- 판정: **M3 단위 구현 PASS** — 새 모듈 2개와 테스트 2개. 8곡 게이트(AC-006·007·045)는 M6 배선 뒤에 판정한다(아래 「안 잰 것」).
- 기준: origin/main `18f42a8e` (#478 `20c027ff` 포함 확인: `git merge-base --is-ancestor 20c027ff HEAD`)
- 브랜치 `WT-concept-color-rules`, 워크트리 `.claude/worktrees/t436`
- 착수 승인: 감독(1~4번 진행 선택). REQ-031 해석: 리드 판정 (가).

## REQ-031 판정과 근거

- 리드 판정: **좁은 해석 (가)**. 새 `color_lint`·`color_strip`은 `_arc_palette`/`_per_chorus_palette`를 import하거나 호출하지 않는다. `server/web/session.py`는 바꾸지 않는다.
- 근거: 실제 출력 색을 바꾸라는 요구는 REQ-031이 아니라 REQ-004(spec.md:152, "When M0~M6이 완료되면")에 있다. 그래서 그 일은 M6 최종 배선에서 한다. 레인이 spec.md:152 원문을 읽어 이 근거를 확인했다.
- 그 결과 `plan.md` M3 파일 목록의 「session.py(수정 — 호출부 제거)」 문구를 「M6(REQ-004)에서」로 고쳤다(같은 브랜치 커밋).
- 증거: `grep -rn "_arc_palette\|_per_chorus_palette" server/concept/` → 일치 0건(exit 1).
- 기존 색 경로 테스트 4파일(t402·t404·t406·color_emission)은 아래 통합 실행에서 모두 통과했다. 무영향이다.

## 파일

| 파일 | 내용 |
|---|---|
| `server/concept/color_strip.py` | `ConceptCue`(M3 전용 최소 입력 타입), `compute_color_strip`(REQ-026/033), `render_concept_bullet`(REQ-032 항등), `resolve_palette`·`draft_palette_from_interview`(REQ-035) |
| `server/concept/color_lint.py` | 유보색(027), 언더페인팅(028), 브리지(029), 후렴 주색(030, AC-016 픽스처 포함), 피부톤 제약 게이트(034) |
| `server/tests/test_concept_color_strip.py`, `server/tests/test_concept_color_lint.py` | 단위 테스트 |
| `.moai/specs/SPEC-LDDESIGN-001/plan.md` | M3 파일 목록 문구 정정(리드 요청) |

`__init__.py`·`worksheet.py`·`vocab.py`·`session.py`는 건드리지 않았다. lane-1의 `cue_model.py`·`resolver.py`·`description.py` 이름도 쓰지 않았다.

## 리뷰에서 잡아 고친 결함 1건

- **증상**: 해제 전 원샷(또는 프레이즈) 큐가 유보색을 써도 REQ-027 검사가 `pass`를 냈다.
- **원인**: 구현 에이전트가 REQ-033의 "구간 큐만" 경계를 REQ-027에도 적용했다. 테스트(`test_phrase_and_one_shot_cues_are_ignored`)가 그 잘못된 동작을 정답으로 못박고 있었다.
- **실측(고치기 전)**: 같은 `Cool White`가 해제 전 원샷 큐에 있으면 `pass`, 구간 큐에 있으면 `fail`.
- **고침**: 테스트를 뒤집어 RED를 확인했다(`1 failed, 4 passed`). 검사 범위를 모든 층의 큐로 넓혀 GREEN이 됐다. 해제 뒤 원샷이 통과하는 대조 테스트도 추가했다.

## 흰색 경계(t409)

색 비교는 대소문자와 공백만 정규화한다. `color_names`의 수식어 벗기기(`warm`/`cold`)는 쓰지 않는다. 직접 실행한 결과:

- 브리지 Warm White → Cool White: `fail`
- 후렴 Warm White / Cool White: `fail`

두 경우 모두 두 흰색을 다른 색으로 판정했다.

## 검증 명령과 출력

```
.venv/bin/python -m pytest -q server/tests/test_concept_color_lint.py server/tests/test_concept_color_strip.py \
  server/tests/test_song_palette_occurrence_t402.py server/tests/test_song_palette_occurrence_t406.py \
  server/tests/test_song_color_usage_t404.py server/tests/test_song_cue_color_emission.py
86 passed in 0.62s

.venv/bin/python -m pytest -q server/tests -k concept
156 passed, 13749 deselected, 1 warning in 9.69s

uv run ruff check (변경 파일 4개) → All checks passed!
```

구현 에이전트의 RED 기록(모듈 부재로 수집 오류 2건 → 구현 후 GREEN)은 커밋 `7be12aab` 시점의 것이다.

## 안 잰 것

- **AC-006/007/045 (8곡 게이트)**: 검사기를 실제 8곡 큐에 걸지 않았다. 입력 큐 모델 v2(lane-1 M2)와 컴포저 배선(M6)이 아직 없다. 픽스처 단위 테스트만 있다.
- **`ConceptCue`와 큐 모델 v2의 연결**: M6 몫이다. 두 타입의 필드 대응은 검증하지 않았다.
- **REQ-028 "채도를 낮춘 형태"**: 불리언 플래그(`desaturated`)로만 표현했다. 실제 채도값은 계산하지 않는다(코드 주석에 설계 선택으로 명시).
- **REQ-034**: 규칙이 있는 제약은 피부톤 하나이고, 충돌 색 목록은 `green` 하나다. 의상·세트·LED 필드는 받기만 하고 규칙은 없다.
- **REQ-035 초안 토큰 분리**: `interview.py`의 private 헬퍼를 import하지 않고 따로 구현했다. 두 구현이 앞으로 서로 달라질 수 있다.
- **전체 테스트 스위트**: 돌리지 않았다(카드 범위만). CI가 PR head에서 전체를 돌린다.
