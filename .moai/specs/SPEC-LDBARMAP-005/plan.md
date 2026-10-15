# SPEC-LDBARMAP-005 — 구현 계획

plan-phase 산출물이다. 코드 0줄, 시험 실행 0회, 콘솔 접촉 0건. 마일스톤은 우선순위 라벨(High / Medium / Low)과 앞뒤 순서로만 적는다 — 시간 추정을 쓰지 않는다. 규모 숫자는 `[predicted]`(코드를 짜 보지 않은 추정)이다. 파일·함수 이름은 가칭이며 run-phase가 확정한다.

## §A. 결정 목록 — 바뀔 가능성이 큰 것부터

검토가 바뀔 가능성이 큰 결정에 모이도록, 되돌리기 어려운 결정을 위에 두고 기계적인 치환을 맨 아래에 둔다.

| # | 결정 | 상태 | 바뀔 가능성 | 바뀌면 흔들리는 것 |
|---|---|---|---|---|
| 1 | **OD-3** 「박자 추정」 표지의 저장 자리 | 미결 — 착수 승인 게이트에서 감독 확정. 기본안: 저장하지 않고 응답 본문에만 싣는다 | 높음 | 선택지 2a면 `validate_bar_map` 본문·SPEC-001 §5·SPEC-LDARRANGE-001 미러·저장 시험. 2b면 SPEC-002 REQ-LDBARENTRY-010과 `song_timeline` 프레임 키 집합. AC-011 (5), AC-015 (3) |
| 2 | **판별기의 신호·검정·확신 조건** (design.md §4, §5) | 설계안 — M1에서 처음 잰다 | 높음 | 사전 등록 표(§6), AC-001~007, `MeterDecision`이 싣는 사유 코드 |
| 3 | **OD-4** 오프셋이 판별한 분자 이상일 때 | 미결 | 중간 | `first_beat_offset_problem`의 2단 구조, AC-012, 요청 거절 여부(P1과의 관계) |
| 4 | 후보 집합 {3, 4, 6}과 2/4 제외 (OQ-4) | 설계안 | 중간 | PR-01, 픽스처 가족, AC-001~003 |
| 5 | 합성 픽스처 매개변수와 문턱 (PR-11~18) | 사전 등록 제안 (OQ-9) | 중간 | M1 통과 판정 |
| 6 | `detect_beat_grid`가 칸 세기를 돌려주는 방식 | 설계안 | 낮음 | `BeatGridResult` 필드 하나, 시험 대역 |
| 7 | 분석기·합성의 `4`를 판별한 분자로 바꾸는 치환 | 기계적 | 낮음 | `bar_map.py`·`bar_map_entry.py`·기존 시험 4개 |

## §B. 마일스톤

순서의 근거는 의존이다 — 판별기가 합성 정답지에서 문턱을 넘기 전에는 분석기에 꽂을 이유가 없고(REQ-LDBARMETER-013), 분석기에 꽂기 전에는 현행과 비교할 새 분석기가 없다. 기준선만은 예외로 **가장 먼저** 찍는다 — M2가 `bar_map.py`를 바꾸면 「현행」이 사라지기 때문이다(REQ-LDBARMETER-020).

### M1 — 합성 정답지 관문 (우선순위 High)

**선행**: 감독의 착수 승인(Implementation Kickoff Approval) 통과, design.md §6 동결(OQ-9). M1은 OD-3·OD-4에 의존하지 않는다 — 판별기는 순수 함수이고 응답·오프셋 처리에 닿지 않는다. OD-3은 M2의 5번 작업 전에, OD-4는 M2의 3번 작업 전에 닫혀 있어야 한다.

**M1-0 (가장 먼저).** 회귀 기준선을 찍는다 — 현행 코드, 변경 전 트리. 캡처 도구를 로컬 전용으로 만들고(`tools/barmap/capture_meter_baseline.py` 가칭), 두 번 돌려 결과가 같은지 확인한 뒤 기준선 파일(`.moai/reports/t656/meter-baseline.json` 가칭)과 캡처 커밋 SHA를 남긴다. 오디오는 저장소에 넣지 않는다. 절차: design.md §11. 증거: AC-018.

**M1-1.** 합성 픽스처 생성기(시험 보조 모듈, 가칭 `server/tests/bar_meter_fixtures.py`)와 판별기 순수 함수(가칭 `server/audio/bar_meter.py`)를 시험 먼저(TDD의 RED)로 만든다. 판별기는 칸 세기 목록과 BPM 검사 결과를 받아 `MeterDecision`을 돌려주는 순수 함수다. librosa에 의존하지 않는다.

**M1-2.** G-A(판별기 단독) → G-B(추적기 포함) → 드럼 가족 순으로 관문을 돌린다. 수치를 progress.md §E.2에 칸별로 적는다. 판별기를 `bar_map.py`에 연결하지 않는다.

**산출물**: 판별기 모듈, 픽스처 생성기, 시험, 기준선 파일, progress.md §E.2의 M1 표.
**통과 조건**: AC-001~007, AC-018. 문턱 미달이면 멈춘다 — design.md §6.3. M2를 시작하지 않는다.

### M2 — 분석기 통합 (우선순위 High)

**선행**: M1의 통과 기록이 progress.md §E.2에 있고 그 커밋이 M2 첫 커밋의 조상이다. 기준선 커밋이 M2 첫 커밋의 조상이다.

작업 순서(앞의 것이 뒤의 것의 전제다):

1. `detect_beat_grid`가 칸 세기 목록을 돌려주게 한다(`BeatGridResult`에 필드 하나). 기존 필드와 판정은 바꾸지 않는다.
2. `derive_bars`가 분자를 인자로 받게 한다. `_BEATS_PER_BAR`와 `% 4`를 없앤다. 못갖춘마디와 다운비트 식은 REQ-LDBARMETER-009를 따른다.
3. 진입 합성(`bar_map_entry.py`)이 판별 결과를 쓰게 한다 — 두 배 BPM 거절 뒤, `derive_bars` 앞에 판별을 넣는다(design.md §8). `_TIME_SIGNATURE` 상수를 없애고 표기 분모 이름표로 바꾼다. `first_beat_offset_problem`을 2단 점검으로 나눈다(디코드 전: 형식과 상한 5, 분자 확정 뒤: 정확한 범위).
4. 합성의 반환이 마디 지도 사전과 판별 결과를 함께 돌려주게 한다. 사전의 모양은 저장 그대로다(`validate_bar_map`을 통과하는 사전 그대로 — OD-3 기본안 기준).
5. `session.py`의 진입 메서드가 추정이면 성공 응답 본문에 「박자 추정」을 싣게 한다. 저장 관문(`store_timeline_bar_map`)이 선택 인자로 문구 한 줄을 받아 자신이 만드는 응답에 붙인다 — 응답이 둘이 되지 않는다. 사유 코드는 로그에만 남긴다.
6. 기존 시험을 새 계약에 맞춘다: 오프셋 4·5·99를 거절하던 시험(research.md 부록 A-8)은 새 상한(5)에 맞고, `time_signature == [4, 4]`를 단언하던 시험은 판별 결과에 따른다.
7. `server/web/PROTOCOL.md`의 `bar_map_analyse` 행에 응답 본문의 「박자 추정」을 한 줄 더한다(`PROTOCOL.md:26` [carried]). 프레임 모양은 바뀌지 않는다.

**산출물**: 변경된 분석기·합성·세션 응답, 갱신된 시험, PROTOCOL.md 한 줄.
**통과 조건**: AC-008~016. 변경 전 검증기·동결 시험이 수정 없이 통과한다(AC-011 (5), AC-014 (5), AC-016 (4)).

### M3 — 회귀 관문 (우선순위 High, 로컬 전용)

**선행**: M2 완료, 기준선 파일, 로컬에 10곡 오디오.

기준선과 새 분석기를 비교한다(design.md §11.5): 곡 10 × 오프셋 4 = 40번. 일치 개수와 불일치 목록을 progress.md §E.2에 적는다. 불일치가 하나라도 있으면 멈추고 감독 결정을 기다린다 — 문턱을 바꿔 통과시키지 않는다.

**통과 조건**: AC-017. 오디오가 없으면 미검증으로 기록한다(완료 조건 미충족).

### M4 — 문서와 sync 준비 (우선순위 Medium)

**선행**: M1~M3.

- progress.md §E.3 run 단계 신호는 manager-develop이, §E.4 sync 단계 신호는 manager-docs가 쓴다(이 plan-phase는 §E.1만 쓴다).
- `.moai/specs/SPEC-LDBARMAP-002/spec.md` 등 대체 대상 문서는 건드리지 않는다. 대체 선언은 spec.md §3에 있다(REQ-LDBARMETER-021, AC-021).
- 증거 형식 점검(AC-019), 오디오 비커밋(AC-020), 추적성(AC-022).
- sync 단계의 `@MX` 태그: 판별기의 상수에 사전 등록 표를 가리키는 `@MX:NOTE`, 판별 결정 함수에 `@MX:ANCHOR` 후보(호출자 3 이상일 때). 근거 `bar_map.py:57-61`의 선례.

## §C. 변경 파일 (가칭)

| 파일 | 변경 | 마일스톤 | 비고 |
|---|---|---|---|
| `server/audio/bar_meter.py` | 신규 — 판별 순수 함수, `MeterDecision` | M1 | librosa 비의존 |
| `server/tests/test_audio_bar_meter.py` | 신규 — AC-001~007 | M1 | |
| `server/tests/bar_meter_fixtures.py` | 신규 — 합성 픽스처 생성기 | M1 | 임시 폴더에만 쓴다 |
| `tools/barmap/capture_meter_baseline.py` | 신규 — 기준선 캡처·비교, 로컬 전용 | M1-0, M3 | 저장소 밖 곡 경로를 인자로 받는다 |
| `.moai/reports/t656/meter-baseline.json` | 신규 — 숫자 기준선 | M1-0 | 오디오 없음 |
| `server/audio/bar_map.py` | 수정 — `BeatGridResult`, `derive_bars`, 상수 제거, docstring | M2 | `:55`, `:134`, `:445`, `:452-468` 등 |
| `server/audio/bar_map_entry.py` | 수정 — 판별 연결, 박자표 상수 제거, 오프셋 점검 2단 | M2 | `:50-55`, `:79-90`, `:134-136`, `:171` |
| `server/web/session.py` | 수정 — 진입 메서드 응답, 저장 관문 선택 인자 | M2 | `:9421-9467`, `:9478-9572` |
| `server/web/PROTOCOL.md` | 수정 — 한 줄 | M2 | `:26` |
| `server/web/messages.py` | 주석만(선택) — `:771`의 「범위(0~3)」 설명이 낡는다 | M2 | 동작과 `CLIENT_MESSAGE_TYPES`는 바꾸지 않는다 |
| `server/tests/test_audio_bar_map.py` | 수정 | M2 | `:125-129` 등 |
| `server/tests/test_audio_bar_map_entry.py` | 수정 | M2 | `:240-245`, `:266-270`, `:338`, `:527` |
| `server/tests/test_session_bar_map_entry.py` | 수정 | M2 | `:343-354`, `:377-385`, `:403`, `:698-700`, `:792-793` |
| `server/tests/test_web_bar_map_entry.py` | 수정 | M2 | `:336-340`의 오프셋 목록 |

규모: 운영 파일 4~5개, 시험 7~8개, 도구 1개, 보고서 1개 [predicted: 이 표를 센 값이며 코드를 짜 보지 않았다].

**건드리지 않는 파일(PRESERVE)**: `server/audio/bar_map_store.py`(OD-3 기본안), `server/audio/analyze.py`, `server/web/messages.py`의 동작, `server/web/app.py`, `server/tests/test_prechk_tool.py`, `server/tests/test_web_song_audio.py`, `server/design/*`, `.moai/specs/SPEC-LDBARMAP-001/**`, `.moai/specs/SPEC-LDBARMAP-002/**`.

## §D. 기술 접근 (요약)

- 판별은 순수 함수다. 입력은 칸 세기 목록과 BPM 검사 결과이고 출력은 (분자, 상태, 사유 코드, 통계량 기록)이다. librosa를 부르지 않으므로 합성 값만으로 시험할 수 있다.
- 칸 세기는 `detect_beat_grid`가 이미 계산하는 온셋 강도 환경에서 `_strength_at`으로 잰다. 환경을 새로 계산하지 않는다.
- 검정은 정확 이항 부호검정이고 기존 `_sign_test_p_value`와 같은 식이다. 새 의존성이 없다.
- 합성 픽스처는 `tools/barmap/make_phase_clicks.py`의 클릭 합성(`_click`)과 표본율을 재사용한다.
- 진입 합성의 순서: 오프셋 형식 점검 → 박 격자 검출 → 두 배 BPM 거절 → **박자 판별** → 마디 파생 → 특징 추출 → 사건 분류 → 저장용 사전.

## §E. 위험

| 위험 | 방향 | 완화·남는 것 |
|---|---|---|
| M1 문턱 미달 | 설계가 틀렸다 | 멈춤. 합성과 이론으로만 고친다(design.md §6.3). 문턱 조정으로 통과시키지 않는다 |
| M3에서 다른 분자를 확신한 곡 | 오확신 | 멈춤. 감독 결정. 기록된 곡의 라벨이 없어 「참 박자」는 모른다 |
| 형제 SPEC-LDBARMAP-004가 같은 파일(`bar_map*.py`, `session.py`)을 바꾼다 | 병합 충돌, 저장 모양 이중 결정 | run 착수 전 `origin/main`과 형제 브랜치를 확인한다(§F). OD-3을 OD-1(004)과 함께 정한다(OQ-10) |
| 기존 시험이 4/4를 암묵 가정한다 | 시험이 줄 번호로만 잡힌다 | research.md 부록 A-8의 전수 목록을 쓴다. 목록에 없는 시험은 M2 시험 전체 실행에서 드러난다 |
| 칸 세기 신호가 실제 곡에서 약하다 | 추정 4/4가 많아진다 | P3가 허용한 결과다. 표지가 응답에만 있어(OD-3 기본안) 새 연결에서는 사라진다 — 감독 확인 항목 |
| 기준선 캡처가 비결정적이다 | 회귀 비교가 무의미해진다 | 두 번 캡처해 같을 때만 채택(AC-018). 다르면 원인을 찾는다 |
| 합성 관문이 실제 곡 위험(자기상관, 2칸 하이퍼박자)을 못 잰다 | 합성 PASS가 실제 곡 정확도로 읽힌다 | REQ-LDBARMETER-015, AC-019 — 합성 수치를 실제 곡에 일반화하지 않는다 |

## §F. run 단계 사전 점검 (명령, 아직 실행하지 않았다)

```bash
# 1. 위치와 기준
git branch --show-current
git rev-parse HEAD
# 2. 병렬 세션과 원격 진행 (agent-common-protocol.md § Pre-Spawn Sync Check)
git fetch origin main
git rev-list --count --left-right origin/main...HEAD
# 3. 형제 SPEC과의 겹침 (읽기 전용)
ls -d ../*/.moai/specs/SPEC-LDBARMAP-00[3-9]
# 4. 변경 전 시험 기준선 (M2 전에 한 번)
uv run pytest server/tests/test_audio_bar_map.py server/tests/test_audio_bar_map_entry.py server/tests/test_session_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_messages_bar_map_entry.py -q
# 5. 동결 파일 확인 (AC-021)
git diff --name-only bef3e16d9da14a398f7c07a8f48bdff94097a636 HEAD -- .moai/specs/SPEC-LDBARMAP-001 .moai/specs/SPEC-LDBARMAP-002
```

## §G. 경로와 게이트

- Tier L이므로 경로 B(PR 경로)다(`spec-workflow.md` § SPEC Phase Discipline [carried]) — plan PR이 병합된 뒤에 run이 시작된다.
- plan-auditor 통과 기준은 Tier L의 0.85다 [carried: `spec-workflow.md` § SPEC Complexity Tier]. 최대 3회 반복한다.
- **Implementation Kickoff Approval**(plan → run 사람 게이트)에서 감독에게 올리는 항목: OD-3, OD-4, OQ-9(사전 등록 문턱 수용). 나머지 열린 질문(OQ-1~8, OQ-10~12)은 spec.md §6.4에 답 없이 적혀 있다. 그 가운데 착수 전에 닫아야 하는 것이 무엇인지는 감독이 가른다.
- `/moai goal` 자율 진행을 쓰더라도 게이트 뒤에만 건다. 이 SPEC의 M1 문턱 미달·M3 불일치는 자율 진행을 멈추는 조건이다.

## §H. 교차 참조

- 설계: design.md. 전수 점검: research.md. 수락 기준: acceptance.md.
- 대체 선언: spec.md §3. 동결 문서: `SPEC-LDBARMAP-001`, `SPEC-LDBARMAP-002`.
- 소비자: `SPEC-LDARRANGE-001`(마디 지도를 읽는 쪽), `SPEC-LDBEAT-001`(박자 격자).
