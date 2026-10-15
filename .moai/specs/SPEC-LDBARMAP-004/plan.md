# SPEC-LDBARMAP-004 — 구현 계획

## §A. 개요 (Context)

이 계획은 SPEC-LDBARMAP-004의 서버 쪽 저장 경로를 어떤 순서로 정할지 적는다. 기준 커밋은 `fe6adf28`이다. 코드는 아직 쓰지 않았다. 아래 파일 목록과 줄 번호는 읽어서 얻은 추정이며, 구현 뒤에 다시 확인한다.

구현은 `server/web/session.py`의 저장 경로(`analyse_bar_map` → 길이 대조 → `store_timeline_bar_map`)를 중심으로 한다. 길이 값은 `server/audio/bar_map.py`의 디코드에서 나와야 하므로, 그 값이 탐지 결과를 거쳐 저장 경로까지 흘러가는 경로가 필요하다.

## §B. 결정 순서 — 되돌리기 어려운 것부터

이 SPEC의 열린 결정은 되돌리기 어려운 순서로 정렬했다. 데이터 모양과 사용자에게 보이는 판정을 먼저 정하고, 기계적 전달 경로는 맨 뒤에 둔다. 실행 순서는 의존이 정한다. 기계적 전달(M5)은 문서상 뒤에 있지만 M2보다 **먼저** 구현해야 한다.

1. **원본 기록의 자리 (OD-1).** 저장 데이터 모양을 바꾼다. 선택지 (a)는 SPEC-LDBARMAP-002 REQ-LDBARENTRY-010 개정을 요구한다. 가장 되돌리기 어렵다.
2. **타임라인 길이의 출처 (OD-4), 허용 오차 (OD-2), 불일치 라벨 (OD-3).** 사용자에게 보이는 저장 판정을 정한다. OD-4가 정해지지 않으면 B 검사는 실효가 없다(spec.md §5, §7).
3. **조용한 잘림 정책 (OD-5).** 길이 값을 믿어도 되는지를 정한다. 선택지 (b)는 정상 곡 Let's Dance를 거절한다.
4. **문구 세트 (OD-7).** 첫 문장은 REQ-LDBARLEN-004로 이미 고정되어 있다. 나머지 문구는 감독이 확정한다.
5. **기계적 전달 경로 (REQ-LDBARLEN-009).** 디코드 길이를 탐지 결과로 옮기는 일과 시험 정리. 모양이 정해진 뒤에만 한다.

[NEEDS CLARIFICATION: OD-1 원본 기록의 자리 — (a) 타임라인 최상위 형제 키(SPEC-LDBARMAP-002 REQ-LDBARENTRY-010 개정 필요), (b) 곡 열쇠로 찾는 별도 저장소, (c) 세션 메모리만]

[NEEDS CLARIFICATION: OD-4 타임라인 곡 길이의 출처 — 현재 생산 경로 없음(spec.md P10). 생산 경로 추가 / 유도 불가 / 「확인할 수 없음」을 상시 결과로 수용 / 다른 출처 중 택일]

[NEEDS CLARIFICATION: OD-2 길이 대조의 허용 오차 수치 — 근거 자료 없음(편집판 쌍 0, 타임라인 길이 측정 0). 숫자를 정하지 않는다]

[NEEDS CLARIFICATION: OD-3 길이 불일치 때 요약 라벨 — 「마디 지도 저장 거절」 또는 「마디 지도 분석 거절」 중 택일. 새 라벨은 금지]

[NEEDS CLARIFICATION: OD-5 조용한 잘림 가드 정책 — (a) 두 번째 디코더 교차 검증, (b) 어림 플래그면 거절(Let's Dance 오거절 측정됨), (c) 통과 후 「길이 추정」 고지 중 택일]

[NEEDS CLARIFICATION: OD-6 입력 자료 — LOVE ATTACK 음원의 저장소 밖 경로, 편집판 쌍 목록]

[NEEDS CLARIFICATION: OD-7 문구 세트 — 길이 결과 문구 세 가지(통과·불일치 문구 제안) 및 타임라인 제목 누락 문구]

## §C. 마일스톤 (의존 순서, 시간 추정 없음)

### M1 — 원본 기록의 자리와 저장 (우선순위 High, OD-1 필요)

- 산출물: 저장 성공 때 파일명과 sha256이 기록되고, 거절 때는 기록이 생기지 않는다(REQ-LDBARLEN-001, 002, 003).
- 기록 값은 분석 시작 때 잡은 곡 오디오 객체에서 가져온다(P2). 저장 시점의 `self._song_audio`를 읽지 않는다.
- 위치는 OD-1에 따른다. 선택지 (a)를 고르면 SPEC-LDBARMAP-002 REQ-LDBARENTRY-010 개정을 먼저 끝낸다.
- 통과 조건: AC-LDBARLEN-001, 002, 003 PASS.

### M2 — 길이 대조 규칙 (우선순위 High, OD-2·OD-3·OD-4 필요)

- 산출물: 타임라인 길이 정보가 없을 때 통과와 「확인할 수 없음」 문구, 있을 때 허용 오차 밖 불일치의 거절(REQ-LDBARLEN-005, 006, 007).
- 대조 위치는 곡 열쇠 재확인(`session.py:9557-9558`) 뒤, 저장 관문 호출 앞이다(REQ-LDBARLEN-005).
- 실행 의존: M5가 먼저 끝나야 길이 값이 저장 경로에 도달한다.
- 통과 조건: AC-LDBARLEN-007, 008, 009 PASS.

### M3 — 조용한 잘림 정책 (우선순위 High, OD-5 필요)

- 산출물: 감독이 고른 정책의 구현. 이 SPEC의 검사 본문은 OD-5 결정 전에는 쓰지 않는다.
- 선택지 (b)를 고르면 Let's Dance가 거절되므로, 그 결과를 감독에게 먼저 보고한다(M4 측정).
- 통과 조건: 감독이 고른 정책의 AC가 추가된다. 현재 이 SPEC의 AC 목록에는 없다. 추가되면 AC 수가 12를 넘는다. 그때 Tier M 상한(16) 안인지 다시 본다.

### M4 — 저장 응답 문구 (우선순위 High)

- 산출물: 성공 `text`의 첫 문장이 SPEC-LDBARMAP-003 REQ-LDBARUI-006과 같은 글자이고, 타임라인 제목과 길이 결과 문장이 뒤따른다(REQ-LDBARLEN-004, 006, 007).
- 첫 문장은 OD-7과 무관하게 바로 구현할 수 있다. 길이 문장과 제목 누락 문구는 OD-7에 따른다.
- 통과 조건: AC-LDBARLEN-004, 005 PASS.

### M5 — 디코드 길이 전달 경로 (우선순위 Medium, 실행은 M2보다 앞)

- 산출물: 탐지 결과가 디코드 길이(밀리초)를 함께 나른다. 길이는 분석에 쓴 바이트를 한 번 디코드한 결과에서 나온다(REQ-LDBARLEN-009).
- 현재 `BeatGridResult`는 길이 필드가 없다(P7). 길이 필드를 더하거나 별도 반환을 쓰는 방식은 run-phase에서 정한다. 어느 쪽이든 헤더 선언 길이를 쓰지 않는다.
- 잘림 검사 조건(`bar_map.py:199-211`)은 M3 결정 전까지 그대로 둔다.
- 통과 조건: AC-LDBARLEN-006 PASS.

### M6 — 회귀와 범위 확인 (우선순위 Medium)

- 산출물: 기존 저장 시험 전부 통과, 요약 라벨 집합 불변, 상수와 음원 0건, 변경 파일이 허용 목록 안.
- 통과 조건: AC-LDBARLEN-010, 011, 012 PASS.

## 파일 요약 (Tier 판단의 근거 — 코드를 짜 본 값이 아니다)

| # | 파일 | 예상 변경 | 관련 |
|---|------|-----------|------|
| 1 | `server/web/session.py` | 저장 경로: 원본 기록 전달, 길이 대조 호출, 성공 문구 조립 (`analyse_bar_map` ~9478, `store_timeline_bar_map` ~9421) | M1, M2, M4 |
| 2 | `server/audio/bar_map.py` | 디코드 길이를 탐지 결과로 전달 (`detect_beat_grid` ~221, `BeatGridResult` ~105). 잘림 검사 분기는 바꾸지 않는다 | M5 |
| 3 | `server/audio/bar_map_entry.py` | 합성 결과가 길이를 함께 실어 나르는 자리 (`synthesize_bar_map` ~93) | M5 |
| 4 | `server/audio/bar_map_store.py` | OD-1 결정에 따름. 원본 기록의 저장 자리와 읽기 함수가 이 파일에 들어가는지는 선택지에 달렸다. `validate_bar_map`과 `_TOP_LEVEL_KEYS`는 불변 | M1 |
| 5 | `server/web/PROTOCOL.md` | 26행의 `bar_map_analyse` 성공 문구 설명 갱신 | M4 |
| 6 | `server/tests/test_session_bar_map_entry.py` | 저장, 거절, 문구, 길이 대조 시험 | M1, M2, M4, M6 |
| 7 | `server/tests/test_audio_bar_map_store.py` | OD-1 결정에 따름. 원본 기록이 마디 지도 최상위 키 집합(여섯 개)을 바꾸지 않음을 확인. 시험의 자리와 방식은 OD-1이 정한다 | M1, M6 |
| 8 | `server/tests/` 아래 길이 시험 파일 (기존 파일을 확인한 뒤 정함) | 디코드 길이 값 시험 (AC-006) | M5 |

예상 8개 파일이다. Tier S 상한(5개 미만)을 넘고 Tier L 기준(15개 초과)에는 닿지 않으므로 Tier M이다. OD-1 (b)를 고르면 새 저장 모듈이 생겨 9~10개가 된다. 여전히 Tier M 안이다. 구현 뒤 LOC를 재고, 1000을 넘으면 Tier L로 재판정한다.

## §D. 제약 (위반 금지)

- 서버 범위만 다룬다. `ui/src/**`와 `WT-barmap-entry-ui` 브랜치의 파일은 건드리지 않는다.
- 기존 파일은 Edit로만 고친다. 새 파일은 OD-1 (b)를 고르고 꼭 필요할 때만 만든다.
- SPEC-LDBARMAP-002 REQ-LDBARENTRY-011(콘솔·라이브러리·BPM 확정 상태 금지), REQ-LDBARENTRY-013(프로토콜 동결)을 깨지 않는다.
- 시험과 구현에 곡 고유 길이, 제목, 파일 해시를 상수로 박지 않는다(REQ-LDBARLEN-010). 음원 파일을 커밋하지 않는다.
- 허용 오차 숫자와 라벨 선택은 OD-2, OD-3이 정하기 전에는 코드에 넣지 않는다.
- 이 plan 단계는 문서만 만든다. 코드, 시험 실행, 커밋, 브랜치 변경을 하지 않는다.

Run-phase에서 쓸 검증 명령(예정이며, 이 단계에서는 실행하지 않았다):

```
.venv/bin/python -m pytest server/tests/test_session_bar_map_entry.py server/tests/test_audio_bar_map_store.py -q
git diff --name-only
```

## §E. 위험표

| 위험 | 영향 | 완화 | 연결 |
|------|------|------|------|
| 타임라인 길이 출처가 없어 B 검사가 공허하다 | 「길이 대조 통과」가 실제 검사 없이 보고된다 | OD-4를 정하기 전까지 완료 보고에 「대조 통과」라고 쓰지 않는다. 대조 실행 증거를 남긴다 | OD-4, spec.md §7 |
| 조용한 잘림으로 부분 길이가 저장된다 | 잘린 곡의 마디 지도가 저장된다 | 정책 결정 전까지 위험으로 기록한다. 가드 정책은 OD-5가 정한다 | OD-5, M3 |
| 원본 기록 (a)가 SPEC-LDBARMAP-002 REQ-LDBARENTRY-010과 충돌한다 | 완료 보고가 약속을 깨고도 성공이라고 쓴다 | (a)를 고르면 REQ-LDBARENTRY-010을 먼저 개정한다 | OD-1 |
| 타임라인에 새 키가 실려 `song_timeline` 프레임이 달라진다 | 키 집합을 고정한 시험이나 클라이언트가 깨질 수 있다 | 시험 결과로 확인한다. 클라이언트 쪽은 전수 확인하지 않았다 | spec.md §6 Gap 2, OD-1 |
| 분석 도중 파일이 바뀌어 기록이 어긋난다 | 디코드한 곡과 기록한 파일명이 다르다 | 기록은 분석 시작 때 잡은 객체에서 가져온다 | REQ-LDBARLEN-001, AC-001 |
| 길이를 헤더 선언값에서 가져온다 | 곡에 따라 48초 이상 틀린다. 측정에서 헤더 판독기 셋 모두 Let's Dance에서 +48초 이상이고, 가장 큰 값은 libsndfile 선언값 +49.562초다(M2, measure.md §2 109행) | REQ-LDBARLEN-009로 금지하고, AC-006이 디코드 값을 확인한다 | REQ-LDBARLEN-009 |
| 분석이 같은 바이트를 두 번 디코드한다 | 두 번째 디코드 결과와 길이가 다를 수 있다 | 길이는 탐지 단계의 디코드 한 번에서만 얻는다 | P8, REQ-LDBARLEN-009 |
| 요약 라벨을 새로 만든다 | 화면이 새 라벨을 모른다(SPEC-LDBARMAP-003) | REQ-LDBARLEN-011로 금지하고 AC-010이 확인한다 | OD-3 |
| 문구가 SPEC-LDBARMAP-003과 어긋난다 | 같은 저장 결과가 화면에서 다르게 보인다 | 첫 문장을 같은 글자로 고정한다. 어느 한쪽이 바뀌면 두 SPEC을 함께 개정한다 | REQ-LDBARLEN-004 |
| Let's Dance를 어림 플래그로 거절한다 | 정상 곡이 저장되지 않는다(측정됨) | 선택지 (b)는 감독에게 측정 결과와 함께 보고한다 | OD-5, M4 |

## §F. 안티패턴

- 디코드 길이를 헤더 선언값으로 바꿔 쓰기. 헤더값은 곡에 따라 48초 이상 틀린다(측정: Let's Dance에서 헤더 판독기 셋 모두 +48초 이상, 가장 큰 값은 libsndfile 선언값 +49.562초, measure.md §2 109행). REQ-LDBARLEN-009 위반이다.
- 「확인할 수 없음」을 실패로 바꾸기. 타임라인에 길이가 없는 것이 지금의 정상 경로라서, 이렇게 하면 저장이 거의 모두 막힌다(REQ-LDBARLEN-006 위반).
- 측정 산포에서 허용 오차 숫자를 골라 쓰기. 편집판 쌍이 없어서 근거가 없다(OD-2).
- 원본 기록을 `bar_map` 사전 안에 넣기. `validate_bar_map`이 거절하거나 키 집합이 바뀐다(REQ-LDBARLEN-002 위반).
- 기록된 BPM을 읽어 비교하기(REQ-LDBARLEN-008 위반).
- 저장 시점에 `self._song_audio`를 다시 읽어 파일명을 가져오기(REQ-LDBARLEN-001 위반).
- 새 요약 라벨을 추가하기(REQ-LDBARLEN-011 위반, 화면 쪽 목록이 깨진다).

## §G. 교차 참조

- `.moai/specs/SPEC-LDBARMAP-004/spec.md` — 요구사항, 열린 결정 OD-1~OD-8, 제외 범위.
- `.moai/specs/SPEC-LDBARMAP-004/acceptance.md` — 수락 기준 AC-LDBARLEN-001~012.
- `.moai/specs/SPEC-LDBARMAP-002/spec.md` — REQ-LDBARENTRY-007, 009, 010, 011, 012, 013, 016(선행 SPEC).
- `WT-barmap-entry-ui:.moai/specs/SPEC-LDBARMAP-003/spec.md` — REQ-LDBARUI-006, 007, E3(화면 쪽 정렬 대상).
- `.moai/reports/t649/measure.md` — 길이 측정 원문과 관찰·추정 구분.
- `.claude/rules/moai/workflow/spec-workflow.md` § SPEC Complexity Tier — Tier M 판정과 산출물 목록.
