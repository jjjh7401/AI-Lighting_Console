# SPEC-LDBARMAP-005 — 수락 기준

모든 기준은 Given-When-Then 형식이며 이진 판정(PASS/FAIL)이 가능하도록 수치·단위·문턱을 명시한다. 각 AC는 검증하는 REQ-ID와 **작성할 시험 파일**을 적는다. 시험 파일 이름과 신규 모듈 이름은 가칭이며 run-phase가 확정한다. 이 문서는 plan-phase 산출물이라 **어떤 시험도 아직 돌리지 않았다.** 아래 문턱은 전부 `[predicted]`(측정 전에 정한 값)이고 design.md §6의 사전 등록 표(PR-01~18)와 같은 값이다 — 이 문서가 새 값을 정하지 않는다.

> **기준 커밋.** 파일 변경을 세는 명령은 base `bef3e16d9da14a398f7c07a8f48bdff94097a636`(이 plan-phase의 HEAD)을 쓴다. 이 SPEC의 plan 커밋이 병합된 뒤에는 plan 커밋의 부모를 base로 바꾼다. 그 base에서 세는 명령은 아래에 `<base>`로 적는다.

> **「SKIPPED」는 PASS가 아니다.** 로컬 전용 관문(AC-017)은 오디오가 없으면 SKIPPED가 아니라 「미검증」으로 기록한다. 미검증은 이 SPEC의 완료 조건을 채우지 못한다.

## §A. 수치 상수 (한 번 정의, 전체에서 재사용)

| 상수 | 값 | 단위 | 출처 | 근거 |
|---|---|---|---|---|
| 후보 분자 | 3, 4, 6 | 칸/마디 | [predicted] | design.md PR-01 |
| 폴백 분자 | 4 | 칸/마디 | [carried: 운영 원칙 P3] | design.md PR-07 |
| 시드 수 | 칸(cell)당 30 | 개 | [predicted] | PR-11 |
| 픽스처 칸 수 / 짧은 입력 | 96 / 24 | 칸 | [predicted] | PR-12 |
| 재현율 문턱 | 30개 중 27개 이상 | 개 | [predicted] | PR-13 |
| 대조군 N=4 반환 문턱 | 30개 중 29개 이상 | 개 | [predicted] | PR-14 |
| 오확신 상한 | 칸당 30개 중 1개 이하 | 개 | [predicted] | PR-15 |
| 단서 없음·짧은 입력의 추정 문턱 | 30개 중 29개 이상 | 개 | [predicted] | PR-16 |
| 추적기 칸 일치 문턱 | 30개 중 27개 이상 | 개 | [predicted] | PR-17 |
| 칸 일치 판정 허용 | 칸 간격 중앙값이 생성 간격의 ±5 % | % | [predicted] | PR-18 |
| 부호검정 유의수준 α | 0.01 | 무차원 | [carried: `bar_map.py:61`] | PR-03 |
| 주기 검정 유의수준 | 0.005 | 무차원 | [predicted] | PR-04 |
| 최소 비교 쌍 | 12 | 개 | [predicted] | PR-06 |
| 회귀 비교 | 곡 10 × 첫 박 오프셋 4 = 40번 | 번 | [predicted: 산술] | REQ-LDBARMETER-019 |
| 사전 디코드 오프셋 상한 | 후보 분자 최댓값 − 1 = 5 | 박 | [predicted: 산술] | REQ-LDBARMETER-012 |

## §B. Given-When-Then 시나리오

### M1 — 합성 정답지 관문 (판별기 통합 전)

### AC-LDBARMETER-001 (REQ-LDBARMETER-001, REQ-LDBARMETER-005, REQ-LDBARMETER-007, REQ-LDBARMETER-013) — 재현율: 3/4와 6/8을 알아본다

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`

**Given** 클릭 가족 합성 픽스처(design.md §7.2) — 분자 3과 6, 단서 수준 강·중, 칸 96개, 칸(cell)당 시드 30개 — 가 시험 실행 중 임시 폴더에 만들어져 있고 판별기 단독 경로(G-A: 생성한 칸 시각 + 합성 오디오에서 잰 칸 세기)가 준비돼 있고
**When** 시드마다 판별기를 돌리면
**Then** (1) 네 칸(3/4 강, 3/4 중, 6/8 강, 6/8 중) 각각에서 「상태 = 확신 AND 분자 = 정답」이 30개 중 **27개 이상**이다. (2) **음성 대조군**: 같은 관문 함수에 「항상 확신 4」를 내는 대역과 「항상 추정 4」를 내는 대역을 넣으면 둘 다 (1)에서 FAIL이다 — 3/4·6/8 칸에서 재현율 0/30이기 때문이다. 관문이 아무 판별기나 통과시키지 않음을 이 단언이 보인다. (3) 칸별 (확신·정답, 확신·오답, 추정) 개수 표를 progress.md §E.2에 적는다. 이 SPEC이 이 표의 수치를 실제 곡으로 일반화하지 않는다.

### AC-LDBARMETER-002 (REQ-LDBARMETER-005, REQ-LDBARMETER-007, REQ-LDBARMETER-013) — 4/4 대조군과 오확신 상한

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`

**Given** 클릭 가족 합성 픽스처 — 분자 4, 단서 수준 강·중, 칸 96개, 칸당 시드 30개 — 와 AC-001의 네 칸이 있고
**When** 시드마다 판별기를 돌리면
**Then** (1) 분자 4 두 칸 각각에서 결과 분자가 4인 시드(확신이든 추정이든)가 30개 중 **29개 이상**이다. (2) **거짓 양성 상한**: 분자 4 두 칸에서 「확신이면서 분자가 4가 아닌」 시드가 칸당 **1개 이하**이다. (3) AC-001의 네 칸에서도 「확신이면서 분자가 정답과 다른」 시드가 칸당 1개 이하이다 — 곧 여섯 칸 모두에 오확신 상한이 걸린다.

### AC-LDBARMETER-003 (REQ-LDBARMETER-005, REQ-LDBARMETER-006, REQ-LDBARMETER-008) — 단서가 없거나 입력이 짧아도 추정으로 진행한다

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`

**Given** (a) 단서 없음 픽스처(단서 수준 1.0, 모든 칸이 같은 세기) — 분자 3·4·6 각각, 칸 96개, 칸당 시드 30개 — 와 (b) 짧은 입력 픽스처(강 단서, 칸 24개) — 분자 3·4·6 각각, 칸당 시드 30개 — 가 있고
**When** 시드마다 판별기를 돌리면
**Then** (1) 여섯 칸(a 셋, b 셋) 각각에서 「상태 = 추정 AND 분자 = 4」가 30개 중 **29개 이상**이다. (2) 어느 시드에서도 판별기가 예외를 내거나 거절을 뜻하는 값을 돌려주지 않는다 — 거절 0개. (3) 짧은 입력에서 추정이 된 이유는 사유 코드 `TOO_SHORT` 또는 `TEST_UNAVAILABLE`로 기록된다(design.md §5).

### AC-LDBARMETER-004 (REQ-LDBARMETER-006, REQ-LDBARMETER-007) — 표지는 추정일 때만 붙는다

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`

**Given** AC-001·002·003이 돌린 모든 시드의 판별 결과와 표지 판정 함수(`판별 결과 → 표지 여부`)가 있고
**When** 모든 결과에 표지 판정 함수를 적용하면
**Then** 「표지 여부 = (상태 == 추정)」이 **모든** 결과에서 성립한다 — 반례 0개. 확신 결과에 표지가 붙은 예와 추정 결과에 표지가 빠진 예를 각각 따로 센다(둘 다 0이어야 한다).

### AC-LDBARMETER-005 (REQ-LDBARMETER-001, REQ-LDBARMETER-013) — 끝에서 끝까지(G-B): 추적기를 거쳐도 같은 문턱을 지킨다

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`

**Given** 클릭 가족 합성 오디오(분자 3·4·6, 단서 강·중, 칸당 시드 30개)가 임시 폴더에 있고
**When** 오디오를 `detect_beat_grid`에 통과시켜 추적기가 낸 칸으로 판별하면
**Then** (1) 칸 일치(칸 간격 중앙값이 생성 간격의 ±5 % 안)가 칸당 30개 중 **27개 이상**이다. (2) 칸이 일치하지 않은 시드도 분모에 남기고 실패로 세어, AC-001의 재현율 문턱(분자 3·6)과 AC-002의 대조군·오확신 문턱(분자 4와 여섯 칸)을 **같은 값으로** 적용한다. (3) 칸 불일치 시드의 수와 그때 추적기 칸 간격 ÷ 생성 간격의 비를 표로 적는다(판정이 아니라 기록). 추적기가 칸을 못 잡는 일은 판별기 탓이 아니어도 이 AC의 실패로 센다.

### AC-LDBARMETER-006 (REQ-LDBARMETER-005, REQ-LDBARMETER-013) — 드럼 가족: 하위 박 에너지가 있어도 오확신하지 않는다

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`

**Given** 드럼 가족 합성 오디오(킥을 칸마다 패턴 진폭으로, 하이햇을 칸 사이 중간점마다 진폭 0.3으로; design.md §7.6) — 분자 3·4·6, 단서 강·중, 칸당 시드 30개 — 가 있고
**When** 끝에서 끝까지(`detect_beat_grid` → 박자 판별) 돌리면
**Then** (1) 「확신이면서 분자가 정답과 다른」 시드가 칸당 **1개 이하**이다. (2) 판별에서 생긴 곡 거절이 **0개**이다. (3) BPM 검사가 `adopt_double`로 뒤집은 시드는 개수를 적고 재현율 분모에서 뺀다(그 시드는 기존 규칙으로 거절된다, design.md §5 U-0). (4) 재현율은 수치만 적는다 — 문턱 없음.

### AC-LDBARMETER-007 (REQ-LDBARMETER-003, REQ-LDBARMETER-013) — 사전 등록이 지켜졌다

시험 파일(가칭): `server/tests/test_audio_bar_meter.py`(항목 1), 명령(항목 2·3)

**Given** design.md §6.1 표(PR-01~18)와 M1을 통과시킨 구현이 있고
**When** (1) 코드의 판별 상수(후보 집합, α, α_period, MIN_PAIRS, 폴백 분자, 표기 분모 이름표)를 표의 값과 대조하는 시험을 돌리고, (2) 아래 명령을 실행하고, (3) M1 시험 파일에서 곡 이름과 샘플 폴더 이름을 찾으면
**Then** (1) 불일치가 **0개**이다. (2) 종료 코드가 0이다 —
```bash
F=$(git log --format=%H --diff-filter=A -1 -- .moai/specs/SPEC-LDBARMAP-005/design.md)   # 동결 커밋
E=$(git log --format=%H --grep='^[a-z]*(SPEC-LDBARMAP-005): M1' -1)                       # M1 증거 커밋
git merge-base --is-ancestor "$F" "$E"; echo $?
```
그리고 §6.1 표의 해시가 두 커밋에서 같다 — `git show "$F:.moai/specs/SPEC-LDBARMAP-005/design.md" | sed -n '/^### 6.1/,/^### 6.2/p' | sha256sum`과 `git show "$E:..."`의 같은 파이프 결과가 같다. 같지 않으면 §6.4에 날짜와 이유가 적힌 개정 행이 있고 M1이 개정 뒤에 다시 돌았음을 progress.md가 보여야 한다. (3) `grep -n -E "LOVE ATTACK|Club Diver|Cut and Run|Ice cream|Let's Dance|LoveMe|Morning|Rain|Too Cool|scott-buckley|sample music" server/tests/test_audio_bar_meter.py`가 **0건**이다 — M1이 실제 곡을 보지 않았다.

### M2 — 분석기 통합

### AC-LDBARMETER-008 (REQ-LDBARMETER-004) — BPM 검사와의 순서

시험 파일(가칭): `server/tests/test_audio_bar_map_entry.py`(수정·확장)

**Given** `synthesize_bar_map`의 `detect` 대역이 세 가지 박 격자를 돌려준다 — (a) `bpm_check.outcome = adopt_double`, (b) `keep` + `ambiguous = True`, (c) `keep` + `ambiguous = False` — 그리고 셋 모두 3칸 주기 강세가 뚜렷한 칸 세기를 싣고
**When** 각각으로 합성을 부르면
**Then** (a) 합성이 `kind = rejected`의 실패 객체를 돌려주고 사유 문장이 변경 전과 **바이트까지 같으며**, 박자 판별 함수의 호출 횟수가 **0**이다. (b) 마디 지도가 만들어지고 판별 상태가 추정(분자 4)이며 사유 코드가 `BPM_AMBIGUOUS`이다. (c) 확신 3이 저장된다. (b)·(c)에서 판별 전후 `grid.beat_times_ms`와 `grid.bpm`이 같다.

### AC-LDBARMETER-009 (REQ-LDBARMETER-002) — 분자는 칸 수이고 소비자 식과 맞는다

시험 파일(가칭): `server/tests/test_audio_bar_map_entry.py`

**Given** 칸이 정확한 간격으로 늘어선 박 격자 대역과 판별 결과를 3, 4, 6 각각으로 강제한 합성이 있고
**When** 합성이 낸 사전을 `build_song_timing_from_bar_map`에 넣으면
**Then** (1) `SongTiming.beats_per_bar`가 강제한 분자와 같다(3, 4, 6). (2) 저장 `bpm`이 입력 격자의 `bpm`과 같다(칸의 분당 횟수). (3) 저장 `time_signature[1]`이 3→4, 4→4, 6→8이다. (4) 참고 측정(판정 아님): `SongTiming.bar_start_seconds(n)`과 저장 `bars[].start_ms ÷ 1000`의 차이 최댓값을 마디 번호 범위와 함께 progress.md에 적는다.

### AC-LDBARMETER-010 (REQ-LDBARMETER-009) — 마디 분할이 분자를 따른다

시험 파일(가칭): `server/tests/test_audio_bar_map.py`(수정)

**Given** 칸 40개 목록과 분자 N ∈ {3, 4, 6}, 오프셋 o ∈ [0, N)이 있고
**When** `derive_bars(칸 목록, o, N)`을 부르면
**Then** (1) 다운비트 목록이 `{칸[i] : (i − o) % N == 0}`과 같고, 못갖춘마디 칸이 앞의 o개이며, 마디 경계가 다운비트와 같다. (2) 정적 점검 —
```bash
grep -c -E "_BEATS_PER_BAR|% 4|_TIME_SIGNATURE|0~3" server/audio/bar_map.py server/audio/bar_map_entry.py
```
가 두 파일 모두 **0**이다. 변경 전 기준값은 `bar_map.py` 8, `bar_map_entry.py` 5였다 [measured: 같은 명령 @ bef3e16d] — 명령이 공허하지 않다. (3) 현행에서 오프셋 4·5·99를 거절하던 기존 시험(`test_audio_bar_map.py:125-129`)은 새 계약에 맞춰 고쳐졌고, 오프셋 −1과 분자 N 이상의 값에 대한 단언은 OD-4가 정해질 때까지 `derive_bars`의 호출 계약(분자 인자 안의 범위)만 다룬다.

### AC-LDBARMETER-011 (REQ-LDBARMETER-010) — 저장 모양과 검증기 불변

시험 파일(가칭): `server/tests/test_audio_bar_map_entry.py`

**Given** 판별 결과를 3, 4, 6 각각으로 강제한 합성이 있고
**When** 합성이 낸 사전을 검사하면
**Then** (1) `time_signature`가 `[3, 4]`, `[4, 4]`, `[6, 8]`이다. (2) `first_beat_offset`이 입력과 같고 0 ~ N−1 안이다. (3) `validate_bar_map(사전) is None`이다. (4) 꽉 찬 마디마다 `len(beats_ms) == N`이다. (5) 검증기 불변(OD-3 기본안 기준):
```bash
git diff --quiet <base> HEAD -- server/audio/bar_map_store.py; echo $?
```
이 **0**이다. OD-3에서 선택지 2a를 고르면 (5)를 개정한다.

### AC-LDBARMETER-012 (REQ-LDBARMETER-011, REQ-LDBARMETER-012) — 오프셋은 사람의 값이고 범위는 분자를 따른다

시험 파일(가칭): `server/tests/test_audio_bar_map_entry.py`, `server/tests/test_session_bar_map_entry.py`, `server/tests/test_web_bar_map_entry.py`(수정)

**Given** 판별 결과를 3, 4, 6 각각으로 강제한 합성과 세션 하네스가 있고
**When** (a) 분자 N에서 오프셋 0 ~ N−1 각각으로 분석하고, (b) 오프셋 −1, 6, 99, `True`, `1.5`로 분석하고, (c) 오프셋 없이 프레임을 보내면
**Then** (a) 마디 지도가 만들어지고 저장된 `first_beat_offset`이 보낸 값과 같다. 분석기가 오프셋을 바꾸거나 채운 경우는 0개이다. (b) 모두 디코드 전에 거절되고(`detect` 대역의 호출 횟수 **0**), 거절은 `kind = rejected`이며 타임라인과 되돌리기 깊이가 요청 전과 같다. (c) 기존대로 프로토콜 오류이다(`messages.py:774`의 파서 단언이 수정 없이 통과). **이 AC는 오프셋이 판별한 분자 이상인 경우(예: 오프셋 3, 판별 3/4)를 단언하지 않는다 — OD-4(미결).** 오프셋 4·5가 디코드 전 점검을 통과해야 한다는 사실만 단언한다(분자 6일 수 있기 때문이다).

### AC-LDBARMETER-013 (REQ-LDBARMETER-008) — 박자를 이유로 거절하는 길이 없다

시험 파일(가칭): `server/tests/test_session_bar_map_entry.py`

**Given** 세션 하네스에서 판별 결과를 다음 여덟 가지로 강제한다 — 확신 3, 확신 4, 확신 6, 추정(사유 `BPM_AMBIGUOUS`), 추정(`TOO_SHORT`), 추정(`TEST_UNAVAILABLE`), 추정(`CONFLICT`), 추정(`NO_ACCENT`) — 그리고 초안 타임라인과 첨부 오디오가 있고
**When** `analyse_bar_map(유효한 오프셋)`을 부르면
**Then** (1) 여덟 경우 모두 저장이 성공하고 `song_timeline`이 정확히 1회, `chat_response`가 정확히 1개(요약 `마디 지도 저장`)이다. (2) `KIND_REJECTED` 응답이 0개이다. (3) 정적 점검 —
```bash
grep -c -E "BarMapEntryFailure|KIND_REJECTED|KIND_FAILED" server/audio/bar_meter.py
```
이 **0**이다. 판별 모듈은 거절을 만들 수 없다.

### AC-LDBARMETER-014 (REQ-LDBARMETER-016) — 박자 선택 경로가 없다

시험 파일(가칭): `server/tests/test_messages_bar_map_entry.py`(기존 단언 유지), 명령

**Given** 변경이 끝난 트리가 있고
**When** 아래 명령을 실행하고 파서에 박자 키를 얹은 프레임을 보내면
**Then** 모두 만족한다 —
1. 요청 파서 분기: `sed -n '/message_type == "bar_map_analyse"/,/^    if message_type == "question_answer"/p' server/web/messages.py | grep -c -i -E "meter|time_signature|numerator|beats_per_bar|박자"` → **0**. 변경 전 기준값 0, 분기 길이 16줄이라 비어 있지 않은 범위를 센다 [measured: 같은 명령과 `wc -l` @ bef3e16d].
2. 디스패치 분기: `sed -n '/message_type == "bar_map_analyse"/,/elif message_type == "history_restore"/p' server/web/app.py | grep -c -i -E "meter|time_signature|numerator|박자"` → **0** [measured 기준값 0 @ bef3e16d].
3. 화면: `grep -rn "bar_map_analyse" ui/src | grep -c -i -E "meter|time_signature|numerator|박자"` → **0**. **이 트리에서는 `ui/src`에 `bar_map_analyse`가 0건이라 이 명령이 공허하게 참이다** [measured: `grep -rn "bar_map_analyse" ui/src | wc -l` → 0 @ bef3e16d]. 화면 SPEC(SPEC-LDBARMAP-003)이 병합된 트리에서 다시 돌려야 의미가 있다 — 그 전에는 이 항목을 PASS로 세지 않고 「대상 없음」으로 기록한다.
4. 파서 시험: `{"type": "bar_map_analyse", "first_beat_offset": 1, "time_signature": [3, 4], "meter": "3/4", "numerator": 3}` 프레임을 파서에 넣으면 출력 키가 정확히 `{v, type, first_beat_offset}`이다.
5. 프로토콜 동결 시험이 수정 없이 통과한다: `git diff --quiet <base> HEAD -- server/tests/test_prechk_tool.py; echo $?` → **0**.

### AC-LDBARMETER-015 (REQ-LDBARMETER-017) — 「박자 추정」은 응답 한 개의 본문에만 실린다

시험 파일(가칭): `server/tests/test_session_bar_map_entry.py`

**Given** 세션 하네스(`ChatSession` + `SongTimelineStore` + 대역 콘솔, SPEC-002 AC-LDBARENTRY-015와 같은 틀)에서 판별 결과를 추정과 확신으로 각각 강제하고
**When** `analyse_bar_map(유효한 오프셋)`을 부르면
**Then** (추정) (1) `chat_response`가 정확히 1개이고 `summary`가 기존 성공 라벨 `마디 지도 저장`과 같으며 `text`에 「박자 추정」이 들어 있다. (2) `song_timeline`이 정확히 1회이다. (3) 저장된 `bar_map` 사전 안에 「박자 추정」 문구와 추정 여부를 뜻하는 키가 없다(OD-3 선택지 1 기준 — 선택지 2를 고르면 이 단언을 바꾼다). (확신) (4) `text`에 「박자 추정」이 0회이다. (공통) (5) 마디 지도 경로가 보내는 `summary` 값의 집합이 변경 전 집합(성공 `마디 지도 저장`, 거절 `마디 지도 분석 거절`, 저장 불가 `마디 지도 저장 불가`, 저장 거절 `마디 지도 저장 거절`)과 같다 — 새 라벨 0개.

### AC-LDBARMETER-016 (REQ-LDBARMETER-018) — 건드리지 않는 계약

시험 파일(가칭): `server/tests/test_session_bar_map_entry.py`

**Given** 세션 하네스와 대역 콘솔이 있고
**When** 추정 결과와 확신 결과로 각각 분석하면
**Then** (1) 콘솔 호출이 **0**이다. (2) `SongTimelineLibrary`에 쓰기가 **0**이다. (3) `_song_bpm`과 `_song_analysis`가 전후에 같다. (4) BPM 확정 계약의 기존 시험이 수정 없이 통과한다: `git diff --quiet <base> HEAD -- server/tests/test_web_song_audio.py; echo $?` → **0**.

### M3 — 회귀 관문 (로컬 전용)

### AC-LDBARMETER-017 (REQ-LDBARMETER-019) — 기록된 10곡에서 현행과 같은 마디 경계

실행: 로컬 비교 도구(가칭 `tools/barmap/capture_meter_baseline.py`의 비교 모드)

**Given** 기준선 파일(곡 10개, design.md §11.3)과 로컬에 있는 10곡 오디오와 M2까지 끝난 새 분석기가 있고
**When** 곡마다 새 분석기를 돌려 기준선과 비교하면(design.md §11.5)
**Then** (1) 곡 10 × 첫 박 오프셋 0·1·2·3 = **40번의 비교가 모두 일치**한다 — 칸 시각 목록이 같고 다운비트·마디 경계 목록이 기준선에서 `(i − k) % 4 == 0`으로 만든 목록과 같다. (2) 기준선의 `outcome`이 실패나 `rejected_adopt_double`인 곡은 새 분석기도 같은 종류로 끝난다. (3) 일치 개수, 불일치 목록(곡, 오프셋, 처음 다른 인덱스, 새 분자·상태·사유 코드), 곡별 분자·상태를 progress.md §E.2에 적는다. 불일치가 **1개라도** 있으면 FAIL이고 멈춘다 — 문턱을 바꿔 통과시키지 않는다(design.md §6.3). (4) 오디오가 없어 실행하지 못했으면 PASS가 아니라 미검증으로 적는다.

### AC-LDBARMETER-018 (REQ-LDBARMETER-020) — 기준선은 숫자만, 결정적이며, 변경 전에 찍었다

실행: 로컬 캡처 도구, 명령

**Given** M2가 `bar_map.py`를 바꾸기 전의 트리와 10곡 오디오가 있고
**When** 캡처 도구를 두 번 돌리고 아래 명령을 실행하면
**Then** (1) 두 결과 파일의 차이가 없다: `diff <첫째> <둘째>` 출력 없음, 종료 코드 0. 차이가 있으면 기준선으로 채택하지 않는다. (2) 곡 항목마다 `sha256`이 64자리 16진수이고 비교 때 다시 계산한 값과 같다. (3) 오디오 파일이 저장소에 없다: `git ls-files .moai/reports/t656 | grep -c -E '\.(mp3|wav|flac|ogg|m4a|aiff)$'` → **0**. (4) 캡처 커밋이 M2의 첫 `bar_map.py` 수정 커밋의 조상이다: `git merge-base --is-ancestor <캡처 커밋> <M2 첫 커밋>; echo $?` → **0**. (5) 기준선 파일 머리에 캡처 커밋 SHA와 `librosa`·`numpy`·`soundfile`·파이썬 버전이 적혀 있다.

### M4 / 교차

### AC-LDBARMETER-019 (REQ-LDBARMETER-015) — 실제 곡 정확도를 주장하지 않는다

실행: 문서 점검

**Given** progress.md §E.2의 증거 표들이 있고
**When** 실제 곡 표(M3)의 머리줄과 본문을 읽으면
**Then** (1) 실제 곡 표의 열은 곡, 분자, 상태, 사유 코드, 40번 비교의 일치 개수, 처음 다른 인덱스로 한정되고 「정답」「정확도」「accuracy」「correct」라는 열이 **없다**: `sed -n '<M3 표 범위>p' progress.md | grep -c -i -E "정답|정확도|accuracy|correct"` → **0**. (2) 재현율·오확신 수치는 합성 표(M1)에만 있다. (3) 합성 표 머리에 「합성 오디오」임이 적혀 있다.

### AC-LDBARMETER-020 (REQ-LDBARMETER-014) — 오디오 비커밋, 곡 고유값 없음

실행: 명령

**Given** 이 SPEC의 run-phase 커밋들이 있고
**When** 아래 명령을 실행하면
**Then** 모두 **0**이다 —
1. `git diff --name-only <base> HEAD | grep -c -E '\.(wav|mp3|flac|ogg|m4a|aiff)$'`
2. M1 시험·픽스처 파일(`test_audio_bar_meter.py`와 픽스처 생성 모듈)에서 `grep -c -E "LOVE ATTACK|Club Diver|Cut and Run|Ice cream|Let's Dance|LoveMe|Morning|Rain|Too Cool|scott-buckley|sample music|\bGroup\b|\bfid\b"` — 픽스처는 임시 폴더(`tmp_path`)에만 쓴다. 이 정적 점검은 M3 캡처·비교 도구와 기준선 파일에는 적용하지 않는다(그것들은 곡 파일 이름을 기록하는 것이 목적이다).

### AC-LDBARMETER-021 (REQ-LDBARMETER-021) — 동결 문서는 그대로다

실행: 명령

**Given** 이 SPEC의 모든 커밋이 있고
**When** 아래 명령을 실행하면
**Then** 출력이 없다 —
```bash
git diff --name-only bef3e16d9da14a398f7c07a8f48bdff94097a636 HEAD -- .moai/specs/SPEC-LDBARMAP-001 .moai/specs/SPEC-LDBARMAP-002
```
base는 이 plan-phase가 시작된 커밋 `bef3e16d`다. 작성 시점의 기준값은 출력 0줄이다 [measured: 같은 명령 `| wc -l` → 0 @ bef3e16d, 이 plan-phase가 SPEC-001·002 디렉터리 아래 어떤 파일도 쓰지 않았다].

### AC-LDBARMETER-022 (추적성, 전 REQ) — 모든 REQ가 AC 하나 이상에 대응한다

실행: 명령

**Given** spec.md와 acceptance.md가 있고
**When** 아래 명령을 실행하면
**Then** 어느 줄도 개수가 0이 아니다 — 세는 줄은 **AC 제목 줄**(`### AC-`로 시작)뿐이다. §D의 추적표 줄이나 본문 언급은 세지 않는다. 그렇지 않으면 추적표 한 줄이 명령을 공허하게 통과시킨다 —
```bash
cd .moai/specs/SPEC-LDBARMAP-005
for r in $(grep -o -E "REQ-LDBARMETER-[0-9]{3}" spec.md | sort -u); do printf "%s %s\n" "$r" "$(grep -c "^### AC-.*$r" acceptance.md)"; done
```
아래 §D의 추적표가 같은 대응을 사람이 읽는 모양으로 적는다. 작성 시점의 결과는 progress.md §E.1에 있다.

## §C. 가장자리 사례

| 사례 | 처리 | AC |
|---|---|---|
| 칸이 36개 미만(`MIN_PAIRS × 3`) | 추정, 분자 4, 사유 `TOO_SHORT` | AC-003 |
| 박 격자 검출 실패 | 기존 실패 경로(`BeatGridFailure`) — 박자 판별에 닿지 않는다 | AC-013 (2) |
| 두 배 BPM 채택 | 기존 거절. 판별을 실행하지 않는다 | AC-008 (a) |
| 오프셋이 판별한 분자 이상 | **이 SPEC이 정하지 않는다 — OD-4** | AC-012 |
| 6/8을 점4분음표 펄스로 잡은 곡 | 범위 밖(OQ-3). 합성 관문은 8분음표 펄스 조건에서만 잰다 | — |
| 곡 중간 박자 변화 | 알려진 한계. 곡 전체에 한 번 판별한다 | — |
| 마지막 마디가 분자보다 적은 칸 | 저장 스키마가 허용한다(`bar_map_store.py:258-262` [carried]) — 거절하지 않는다 | AC-011 (4) |
| 못갖춘마디(오프셋 o > 0) | 앞의 o개 칸이 마디 0 | AC-010 (1) |
| 기준선의 곡이 현행에서도 실패/거절 | 새 분석기도 같은 종류로 끝나면 일치로 센다 | AC-017 (2) |
| OD-3에서 저장 선택지를 고르면 | AC-011 (5)와 AC-015 (3)을 개정한다 | AC-011, AC-015 |

## §D. 추적표와 완료 정의

### 추적표 (REQ → AC)

| REQ | AC |
|---|---|
| REQ-LDBARMETER-001 | AC-001, AC-005 |
| REQ-LDBARMETER-002 | AC-009 |
| REQ-LDBARMETER-003 | AC-007 |
| REQ-LDBARMETER-004 | AC-008 |
| REQ-LDBARMETER-005 | AC-001, AC-002, AC-003, AC-006 |
| REQ-LDBARMETER-006 | AC-003, AC-004 |
| REQ-LDBARMETER-007 | AC-001, AC-002, AC-004 |
| REQ-LDBARMETER-008 | AC-003, AC-013 |
| REQ-LDBARMETER-009 | AC-010 |
| REQ-LDBARMETER-010 | AC-011 |
| REQ-LDBARMETER-011 | AC-012 |
| REQ-LDBARMETER-012 | AC-012 |
| REQ-LDBARMETER-013 | AC-001, AC-002, AC-005, AC-006, AC-007 |
| REQ-LDBARMETER-014 | AC-020 |
| REQ-LDBARMETER-015 | AC-019 |
| REQ-LDBARMETER-016 | AC-014 |
| REQ-LDBARMETER-017 | AC-015 |
| REQ-LDBARMETER-018 | AC-016 |
| REQ-LDBARMETER-019 | AC-017 |
| REQ-LDBARMETER-020 | AC-018 |
| REQ-LDBARMETER-021 | AC-021 |

### 완료 정의 (run·sync 단계)

- [ ] M1 증거: AC-001~007이 progress.md §E.2에 칸별 수치로 기록되고, 사전 등록 표(design.md §6.1)가 M1 실행 전에 동결되었다(AC-007).
- [ ] M2 증거: AC-008~016이 PASS이고, M1 통과 기록이 M2 첫 커밋보다 앞선다(REQ-LDBARMETER-013).
- [ ] M3 증거: AC-017·018이 PASS(미검증이면 완료 조건 미충족). 기준선이 M2 전에 찍혔다.
- [ ] 문서 증거: AC-019·020·021·022 PASS.
- [ ] OD-3·OD-4가 감독 결정으로 닫혔다(착수 승인 게이트). OD-4가 열린 채면 AC-012의 제외 문장이 남고, 그 상태를 progress.md에 적는다.
- [ ] `server/` 아래 코드 변경이 SPEC-001·002 디렉터리에 닿지 않았다(AC-021).
- [ ] 실제 곡 정확도 주장이 어디에도 없다(AC-019).
