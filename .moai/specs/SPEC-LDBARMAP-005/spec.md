---
id: SPEC-LDBARMAP-005
title: "마디 지도 박자표 자동 판별 — 분석기가 3/4·4/4·6/8을 스스로 가르고 마디를 그 박자표로 나눈다"
version: "0.1.0"
status: draft
created: 2026-10-15
updated: 2026-10-15
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "server/audio/bar_map.py, server/audio/bar_map_entry.py, server/audio/bar_meter.py(가칭), server/web/session.py, server/web/PROTOCOL.md, server/tests/test_audio_bar_meter.py(가칭), tools/barmap/capture_meter_baseline.py(가칭)"
lifecycle: spec-anchored
tags: "bar-map, time-signature, meter-detection, synthetic-ground-truth, pre-registration, regression-gate"
tier: L
related_specs: [SPEC-LDARRANGE-001, SPEC-LDBEAT-001]
depends_on: [SPEC-LDBARMAP-001, SPEC-LDBARMAP-002]
---

# SPEC-LDBARMAP-005 — 마디 지도 박자표 자동 판별

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-15 | 최초 작성(카드 t656). **plan만 — 코드 변경 0줄, 시험 실행 0회, 콘솔 접촉 0건, 커밋 0건.** 입력: 리드 확정 결정 D-1~D-4와 운영 원칙 P1~P5(2026-10-15), `SPEC-LDBARMAP-001`(status: completed), `SPEC-LDBARMAP-002`(status: completed), 코드 직접 읽기(research.md의 전수 점검 — 인용한 줄은 전부 이 plan-phase에서 열어 읽은 줄이다), 카드 t656 체크포인트(`.moai/specs/SPEC-LDBARMAP-002/progress.md` §J). 이 SPEC은 **새 SPEC**이다 — `SPEC-LDBARMAP-002`를 다시 열지 않고 `amendment_of`도 쓰지 않는다. 두 SPEC의 결정 가운데 일부를 **대체한다고 §3에 선언만** 하며 두 SPEC의 어떤 파일도 고치지 않는다. REQ 접두사는 `REQ-LDBARMETER-`, AC 접두사는 `AC-LDBARMETER-`다 — 이 plan-phase가 두 접두사의 충돌을 확인했다(research.md 부록 A-13, 현재 트리와 `origin/main`과 전체 git 이력에서 `LDBARMETER` 0건). 작성 base: `bef3e16d`. |

## §0. Tier 선택 근거

**Tier L.** REQ 21개·AC 22개를 담는다 [measured: `grep -c "^| REQ-LDBARMETER-" spec.md`, `grep -c "^### AC-LDBARMETER-" acceptance.md` @ 이 plan-phase 산출물]. Tier M 상한(각 16개)을 REQ가 넘어서 tier를 올린다 — 상한을 완화하지 않았다. Tier L 상한(각 25개) 안이다. 한편 SPEC 분할은 D-1이 이미 정했다(새 SPEC 하나). 파일 수와 줄 수 추정은 코드를 짜 보지 않은 값이다 — 운영 파일 4~5개(신규 판별 모듈 1개 포함), 기존 시험 수정 4개, 신규 시험 2~3개, 로컬 도구 1개, 문서 1개 [predicted]. 숫자만으로는 Tier L 기준(15파일, 1000줄)에 못 미칠 수 있다는 점을 적어 둔다. Tier L을 고른 근거는 숫자가 아니라 다음 둘이다 — (1) REQ 개수가 Tier M 상한을 넘었다, (2) 두 문서가 SPEC 본문에 들어가지 못한다: `research.md`는 4/4 가정의 전수 점검(명령과 출력 원문)을 담고, `design.md`는 판별기의 신호·검정·사전 등록 문턱·표지 계약을 담는다. 이 SPEC은 같은 계열의 SPEC-LDBARMAP-001/002와 달리 **사전 등록**을 요구하므로(P4, 실제 곡을 보기 전에 문턱을 동결한다) 설계 문서가 따로 있어야 동결 시점을 가리킬 수 있다.

**출처 표기.** 이 SPEC의 숫자는 세 가지 표기 중 하나를 단다. `[measured: <명령> @ <트리>]`는 이 plan-phase가 실행해 본 값, `[carried: <파일:줄>]`은 다른 문서·코드에서 옮긴 값, `[predicted]`는 측정 전에 정한 값(사전 등록 문턱, 합성 매개변수, 산술, 규모 추정)이다. `[predicted]`는 관측이 아니다. 트리 `bef3e16d`는 이 워크트리의 HEAD다.

## §1. 배경 — 왜 지금인가

감독이 2026-10-15에 결정했다(리드 경유): **「어떤 음악이 들어와도 진행되어야 한다」.** 박자를 고르는 화면도, 박자를 모른다며 곡을 거절하는 길도 두지 않는다. 분석기가 박자표를 스스로 판별하고, 그 박자표대로 마디를 나눈다. 판별이 불확실하면 멈추지 않고 4/4로 진행하며 결과에 「박자 추정」을 표시한다.

이 결정은 `SPEC-LDBARMAP-002`가 하루 전(2026-10-14)에 확정한 「4/4 전용」(D2 (가), `spec.md:147` [carried])을 뒤집는다. 코드가 지금 4/4에 묶인 곳은 좁다.

- **분석기와 진입 합성이 4에 묶여 있다.** `server/audio/bar_map.py:55`의 `_BEATS_PER_BAR = 4`, 오프셋 범위(`:454-457`), 다운비트 식 `% _BEATS_PER_BAR`(`:462`), 합성 쪽 `_TIME_SIGNATURE = (4, 4)`(`server/audio/bar_map_entry.py:52`)와 오프셋 범위(`:88-89`) [carried]. 전수 점검 목록은 research.md §2.
- **저장 검증은 이미 박자표에 일반적이다.** 분자 1~16, 분모 {1, 2, 4, 8, 16}, 오프셋 0 ~ 분자−1(`server/audio/bar_map_store.py:203-215` [carried]). 바꿀 필요가 없다.
- **소비자도 이미 일반적이다.** 마디 시작을 `분자 × 60 / bpm`으로 계산하고(`server/design/beat_grid_emit.py:216`) 분모는 읽지 않으며(`server/design/beat_grid_send.py:248-255`), 3/4 시험이 있다(`server/tests/test_beat_grid_entry_t574.py:118-122`) [carried].

그래서 이 SPEC이 새로 만드는 것은 **박자표 판별기 하나**이고, 나머지는 4를 상수에서 판별 결과로 바꾸는 일이다.

**이 SPEC이 하는 말과 하지 않는 말.** 저장소에는 박자표가 3/4나 6/8이라고 라벨된 실제 곡 오디오가 없다(research.md §3). 판별기의 정확도는 박자를 아는 **합성 오디오**에서만 말한다(P4, P5). 실제 곡에 대해서는 「현행 분석 결과와 같은 마디 경계가 나온다」만 주장한다(D-4).

## §2. 범위

**들어오는 것.**

1. 박자표 판별기: 후보 3/4, 4/4, 6/8 가운데 하나를 칸 세기에서 고른다. 확신/추정 두 상태를 사전 등록한 규칙으로 낸다(design.md).
2. 마디 분할: `derive_bars`와 진입 합성이 판별한 분자로 다운비트·마디 경계·저장 `time_signature`를 만든다. 박자 때문에 곡을 거절하는 길은 없앤다.
3. 합성 정답지 관문(M1): 박자를 아는 합성 오디오로 판별기를 먼저 잰다. 분석기 통합(M2)은 그 뒤다.
4. 회귀 관문(M3): 저장소에 기록된 10곡에서 현행과 같은 마디 경계가 나오는지 로컬에서 잰다.
5. 「박자 추정」 표지: 추정 상태의 저장 성공 응답에 싣는다. 저장 자리는 OD-3(미결).

**들어오지 않는 것**은 §8.

## §3. 대체 관계 — 이 SPEC이 대체하는 결정

이 절은 **선언**이다. `SPEC-LDBARMAP-001`과 `SPEC-LDBARMAP-002`의 어떤 파일도 이 SPEC이 고치지 않는다(D-1, D-2, REQ-LDBARMETER-021). 원문은 역사로 그대로 남고, 읽는 사람은 이 절로 현행 효력을 판단한다.

### 3.1 대체되는 결정

| # | 대체 대상 | 위치 | 이 SPEC이 대체하는 방식 | 그대로 유지되는 것 |
|---|---|---|---|---|
| R-1 | SPEC-002 **D2 (가) 「4/4 전용」** | `SPEC-LDBARMAP-002/spec.md:147` (표 `:143-150`, 결정 기록 `:29`) | 2026-10-15 운영 결정 「박자표 자동 판별」로 대체. 분석기를 일반화하는 (나)(`:148`)의 방향을 택하되 판별을 자동으로 한다 | D2 표가 적은 「잘못 골랐을 때」 위험 서술(`:150`)은 이 SPEC의 동기로 유효하다 |
| R-2 | SPEC-002 **REQ-LDBARENTRY-015** 중 저장 `time_signature`를 `[4, 4]`로 명시하는 부분 | `SPEC-LDBARMAP-002/spec.md:126` | 저장 `time_signature`는 `[4, 4]`로 고정되지 않는다. 판별한 분자 N과 표기 분모가 들어간다(REQ-LDBARMETER-010) | 「다른 박자표를 받는 필드나 옵션을 프레임에 두지 않는다」는 부분은 그대로이고 REQ-LDBARMETER-016이 이어받아 더 넓힌다(박자 필드 일체 금지) |
| R-3 | SPEC-002 **제외 범위 「일반 박자표」** | `SPEC-LDBARMAP-002/spec.md:233`(제목), `:235`(「4/4 밖의 박자표 분석(D2). 분석기 `server/audio/bar_map.py`는 이 SPEC이 수정하지 않는다.」) | 분석기 작업에 한해 효력을 잃는다. 이 SPEC은 `bar_map.py`를 수정한다 | SPEC-002 자신의 범위(그 SPEC은 completed)에는 영향이 없다 |
| R-4 | SPEC-002 **제외 범위 「분석기·저장 스키마 변경」** 중 `derive_bars`·`detect_beat_grid` 수정 금지 | `SPEC-LDBARMAP-002/spec.md:244` | `derive_bars`와 `detect_beat_grid`(반환에 칸 세기를 더함)를 수정한다. `extract_bar_features`·`classify_bar_events`·`validate_bar_map`·저장 스키마는 이 SPEC도 수정하지 않는다 | 두 배 BPM 판정 재설계 금지, 박 격자 재구성 금지, 자동 위상 선택기 금지는 그대로 |
| R-5 | SPEC-002 **전제 P5 「분석기는 4/4 전용이다」**와 P7의 `(i - offset) % 4 == 0` 서술 | `SPEC-LDBARMAP-002/spec.md:71`, `:73` | 2026-10-14 시점의 사실 기록이다. M2 이후에는 사실이 아니다 | P7이 말하는 마디 번호 공간(첫 다운비트가 마디 1, 그 앞 박은 마디 0) |
| R-6 | SPEC-002 **REQ-LDBARENTRY-007** 중 「오프셋 범위 점검을 오디오 디코드 전에 한다」는 부분. REQ-LDBARENTRY-002 근거 칸의 「범위(0~3) 판정은 분석 첫 점검이 맡는다」(`:93`)도 같은 이유로 낡는다 | `SPEC-LDBARMAP-002/spec.md:103`, `:93` | 디코드 전 점검은 형식과 후보 분자 최댓값 − 1(5)까지만 본다. 정확한 범위는 분자가 정해진 뒤에 판정한다(REQ-LDBARMETER-012). 타임라인 존재 점검은 그대로 디코드 전이다 | 실패 사유를 응답에 싣고 `store.latest`와 되돌리기 깊이를 요청 전과 같게 유지하는 요구 |
| R-7 | SPEC-002 **수락 기준 값** 중 4/4 고정 부분 | `SPEC-LDBARMAP-002/acceptance.md:11`(오프셋 범위 0~3), `:12`(`[4, 4]`), `:45`(AC-LDBARENTRY-003의 응답 본문에 `0~3`), `:63`(AC-LDBARENTRY-005 (5)의 `time_signature == [4, 4]`), `:163`(마지막 마디 「4박 미만」 표현), `plan.md:17`(D2 한 줄) | 위 부분의 기대값이 판별한 분자에 따라 달라진다 | 각 AC의 나머지 단언 |
| R-8 | SPEC-001 **REQ-LDBARMAP-016**의 「mod 4, 범위 0~3」 | `SPEC-LDBARMAP-001/spec.md:107` | 4/4 인스턴스다. 이 SPEC은 같은 문서 §5 열린 결정 0의 일반 규칙을 따른다 — 「박자표 분자로 나눈 나머지, 범위 0 ~ 분자−1」(`spec.md:147`, `:160`). 리드의 메모는 이 항목을 「§5 item 1」이라 불렀으나 파일의 번호는 0이다 | 오프셋을 사람이 지정한다는 원칙(D-3) |
| R-9 | SPEC-001 **AC-LDBARMAP-016**과 §A 상수표의 4/4 표현 | `SPEC-LDBARMAP-001/acceptance.md:216-224`(`(i − offset) % 4`, 정수 0~3), `:35`(§A 상수표 「정수, 0~3 / mod 4」) | LOVE ATTACK 회귀 기준으로는 여전히 참이지만, 분석기의 일반 규칙으로서의 효력은 R-8로 대체된다 | LOVE ATTACK의 offset = 1 회귀값(`:224`) |

### 3.2 4/4 색이 있지만 대체하지 않는 항목

| 항목 | 위치 | 대체하지 않는 이유 |
|---|---|---|
| SPEC-001 REQ-LDBARMAP-004의 「(3) 마디 경계… 4/4 박자인 이 곡」 | `spec.md:71` | LOVE ATTACK 채점 서술이다. 곡이 4/4라는 사실을 말할 뿐 분석기를 묶지 않는다 |
| SPEC-001 REQ-LDBARMAP-005 「1마디(2.136초, 4박)」 | `spec.md:72` | 같은 이유 — 채점 대조군의 크기 |
| SPEC-001 AC-LDBARMAP-003·005·006, §A 상수표 마디 길이·1마디 밀림 행 | `acceptance.md:53-57`, `:95`, `:97-103`, `:26`, `:33` | LOVE ATTACK 채점 |
| SPEC-001 §5 항목 3 「다운비트와 마디 경계는 이 곡(4/4)에서 같은 사건」 | `spec.md:165` | 곡 서술. 이 SPEC도 두 필드를 같은 수열로 둔다 |
| SPEC-002 REQ-LDBARENTRY-008 (두 배 BPM 채택은 저장 거절) | `spec.md:104` | BPM 배수 거절이지 박자 거절이 아니다. P1과의 관계는 OQ-5 |
| SPEC-002 REQ-LDBARENTRY-010, -011, -012 | `spec.md:111-113` | OD-3 기본안에서는 그대로다. OD-3에서 저장 선택지를 고르면 -010이 개정 대상에 든다 |

### 3.3 OD-3에 따라 대체 목록이 늘어나는 경우

- OD-3 선택지 2a(마디 지도 사전 안에 필드를 더함): SPEC-001 §5 모양(`spec.md:147-160`), AC-LDBARMAP-010·011(`acceptance.md:167-190`), SPEC-LDARRANGE-001 §5 미러 문단, `validate_bar_map` 본문이 대체 대상에 든다.
- OD-3 선택지 2b(타임라인 형제 키): SPEC-002 REQ-LDBARENTRY-010(`spec.md:111`)이 대체 대상에 든다.

## §4. 전제와 증거

아래 줄은 이 plan-phase가 파일을 열어 읽은 것이다(트리 `bef3e16d`). **시험을 하나도 돌리지 않았다** — 「읽음」은 코드를 읽은 것이지 동작을 잰 것이 아니다. 전수 점검의 명령과 출력 원문은 research.md 부록 A에 있다.

| # | 전제 | 근거 | 판독 |
|---|---|---|---|
| P1 | 박 격자는 `librosa.beat.beat_track`이 내고, 온셋 강도 환경은 두 배 BPM 검사만 쓰고 버려진다 | `bar_map.py:241-262` | 읽음 |
| P2 | `derive_bars`는 오프셋 범위를 `0 ≤ 오프셋 < 4`로 거절하고 다운비트를 `(i − 오프셋) % 4 == 0`으로 정한다 | `bar_map.py:452-462` | 읽음 |
| P3 | 진입 합성은 박자표를 `(4, 4)`로 못박고 오프셋 범위를 디코드 전에 점검한다 | `bar_map_entry.py:50-55`, `:79-90`, `:134-136`, `:171` | 읽음 |
| P4 | 저장 검증은 알 수 없는 최상위 키를 거절한다 | `bar_map_store.py:54-56`, `:175-177` | 읽음 |
| P5 | 성공 응답은 저장 관문이 만든다. 진입 메서드는 성공을 「방금 넘긴 페이로드가 읽혀 나오는지」로 가른다 | `session.py:9457-9466`, `:9569-9572` | 읽음 |
| P6 | 두 배 BPM 채택은 저장 거절이다 | `bar_map_entry.py:142-152` | 읽음 |
| P7 | 요청 프레임은 `{v, type, first_beat_offset}`이고 파서는 범위를 재지 않는다 | `messages.py:766-779` | 읽음 |
| P8 | 기록된 곡은 10곡이다. 사람이 확인한 곡별 박자표 라벨은 저장소에 없다 | `.moai/reports/t547/after_songs.txt`의 곡 행 10개 [measured: `cat .moai/reports/t547/after_songs.txt` @ bef3e16d, 부록 A-12], 라벨 검색 research.md §3 | 측정 |
| P9 | 기존 시험이 오프셋 4를 거절하고 사유에 `0~3`을 요구한다 | research.md 부록 A-8 | 읽음 |
| P10 | `analyze.py:526`에 별개의 4칸 가정(`bar_ms = 4.0 × 60000 / bpm`)이 있다. 구간(section) 경계 하한이며 마디 지도 경로가 아니다 | `analyze.py:52-64`, `:526-528` | 읽음 |

## §5. 요구사항 (GEARS)

용어: **칸**은 박 격자 `beat_times`의 항목 하나, **분자**는 한 마디에 든 칸 수다(design.md §2).

### 5.1 R1 — 판별 대상과 단위 (REQ-LDBARMETER-001~004)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-001 | [HARD] **When** 박 격자 검출이 성공하고 BPM 검사 결과가 `adopt_double`이 아니면, 분석기 **shall** 칸마다 온셋 세기를 재고 그 세기만으로 분자를 후보 3, 4, 6 가운데에서 판별한다. 후보 밖 박자와 2/4는 판별 대상이 아니다. | 운영 결정 2026-10-15. 후보와 2/4 제외 이유: design.md §3.2. 신호: design.md §4.1(`bar_map.py:247-249`의 환경 재사용) |
| REQ-LDBARMETER-002 | [HARD] **The** 분자 **shall** 검출된 박 격자의 칸 수로 센다. 저장되는 `bpm`은 칸의 분당 횟수이고 `time_signature`의 분모는 소비자가 읽지 않는 표기 이름표(3→4, 4→4, 6→8)다. 저장된 지도로 만든 `SongTiming`의 `beats_per_bar`는 분자와 같아야 **shall** 한다. | 소비자 식 `beat_grid_emit.py:216`, 분모 비사용 `beat_grid_send.py:248-255`. 「비트 단위 문제」: design.md §3 |
| REQ-LDBARMETER-003 | [HARD] **The** 판별의 신호·검정·유의수준·후보 목록·확신 조건·합성 문턱 **shall** design.md §6 사전 등록 표의 값만 쓰고, 그 표는 M1 합성 실행 전에 동결된다. 동결 뒤 값을 바꾸려면 날짜와 이유를 적은 개정 행을 더하고 M1을 다시 돌려야 하며, 실제 곡의 결과를 이유로 값을 바꾸지 **shall not** 한다. | 감독 원칙 2026-10-10 「이 곡들에서 고른 값이 아니다」(`bar_map.py:57-61` [carried]). 운영 원칙 P4 |
| REQ-LDBARMETER-004 | [HARD] **The** 박자 판별 **shall** 칸 시각, `bpm`, 두 배 BPM 판정 결과를 읽기만 하고 바꾸지 **shall not** 한다. **When** `bpm_check.outcome`이 `adopt_double`이면 판별을 실행하지 않고 기존 거절을 유지하며, **when** 결과가 `keep`이면서 `ambiguous`이면 판별 상태는 추정이다. | SPEC-001 REQ-LDBARMAP-006 계열과 SPEC-002 REQ-LDBARENTRY-008을 건드리지 않는다. 상호작용: design.md §8 |

### 5.2 R2 — 불확실성 규칙 (REQ-LDBARMETER-005~008)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-005 | [HARD] **The** 판별 결과 **shall** (분자, 상태) 한 쌍이다. 분자는 3, 4, 6 가운데 하나이고 상태는 확신 또는 추정이다. 상태는 design.md §5의 확신 조건을 모두 채울 때만 확신이고, 근거 부족·모호·충돌·짧은 입력·박 강약 단서 없음은 전부 추정이다. | 운영 원칙 P3. 사전 등록한 불확실성 규칙: design.md §5 |
| REQ-LDBARMETER-006 | [HARD] **When** 판별 상태가 추정이면, 분석기 **shall** 분자 4로 마디를 나누고 결과에 「박자 추정」 표지를 붙인다. | 운영 원칙 P3 |
| REQ-LDBARMETER-007 | [HARD] **When** 판별 상태가 확신이면, 분석기 **shall** 판별한 분자로 마디를 나누고 「박자 추정」 표지를 붙이지 **shall not** 한다. | 운영 원칙 P3. 표지가 확신 결과에도 붙으면 표지가 정보를 잃는다 |
| REQ-LDBARMETER-008 | [HARD] **The** 분석기 **shall not** 박자를 모르거나 모호하거나 후보 밖이라는 이유로 곡을 거절한다. 이 요구는 박자 판별에서 생기는 거절에만 걸리며, 박 격자 검출 실패, 두 배 BPM 거절, 첨부 오디오·타임라인·busy 점검 같은 기존 거절 경로는 바꾸지 **shall not** 한다. | 운영 원칙 P1 「어떤 음악이 들어와도 진행되어야 한다」. 기존 경로를 건드리지 않는 이유: BPM 확정 계약은 범위 밖이다(§8). 두 배 BPM 거절과 P1의 관계는 OQ-5 |

### 5.3 R3 — 마디 분할과 저장 모양 (REQ-LDBARMETER-009~010)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-009 | [HARD] **The** `derive_bars` **shall** 판별한(또는 폴백한) 분자 N을 인자로 받아 다운비트를 `(i − first_beat_offset) % N == 0`인 칸으로 정하고 마디 경계를 만든다. 마디당 박 수 4를 상수로 두거나 `% 4`로 쓰지 **shall not** 한다. | P2(`bar_map.py:452-462`). SPEC-001 §5 열린 결정 0의 일반 규칙(`spec.md:160`) |
| REQ-LDBARMETER-010 | **When** 마디 지도가 저장되면, 저장되는 `time_signature` **shall** `[N, 표기 분모]`이고 `first_beat_offset`은 0 ~ N−1이며 그 지도는 `validate_bar_map`을 그대로 통과한다. `validate_bar_map` 본문은 이 SPEC에서 바뀌지 **shall not** 한다. | 저장 검증은 이미 일반적이다(`bar_map_store.py:203-215`). 마지막 문장은 OD-3 선택지 1과 2b에 대해서만 참이다 — 2a를 고르면 이 문장을 개정한다 |

### 5.4 R4 — 첫 박 오프셋 (REQ-LDBARMETER-011~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-011 | [HARD] **The** 첫 박 오프셋 **shall** 사람이 지정한 정수로 남는다. 분석기는 오프셋을 추정·보정하거나 기본값으로 채우지 **shall not** 하고, 프레임에 오프셋이 없거나 정수가 아니면 기존대로 프로토콜 오류다. | D-3. 자동 위상 선택은 M1에서 0/82로 실패했다(`SPEC-LDBARMAP-001/spec.md:29` [carried]) |
| REQ-LDBARMETER-012 | **While** 판별한 분자가 N인 동안, 첫 박 오프셋의 유효 범위 **shall** 0 ~ N−1이다. 오디오를 풀기 전의 싼 점검은 형식(정수, bool 아님)과 후보 분자 최댓값 − 1을 넘는지만 보고, 정확한 범위 판정은 분자가 정해진 뒤에 한다. | SPEC-001 §5 열린 결정 0(`spec.md:147`, `:160`). 이 요구는 오프셋이 N 이상인 경우를 다루지 않는다 — OD-4(미결) |

### 5.5 R5 — 합성 정답지 관문 (REQ-LDBARMETER-013~015)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-013 | [HARD] **The** 판별기 **shall** 분석기 통합(M2) 전에 박자를 아는 합성 오디오 — 3/4, 6/8, 4/4 대조군 — 로 design.md §7의 사전 등록 문턱을 통과해야 한다. M2는 M1 통과 기록이 progress.md §E.2에 쓰인 뒤에만 시작한다. | 운영 원칙 P4. 선례: SPEC-001이 M1 보정을 채택 앞에 둔 순서(`SPEC-LDBARMAP-001/spec.md:64`) |
| REQ-LDBARMETER-014 | [HARD] **The** 합성 픽스처 **shall** 시험 실행 중 임시 폴더에서 만들고 저장소에 오디오 파일을 커밋하지 **shall not** 한다. 픽스처 생성 코드와 시험은 곡 고유값(곡 제목, 시퀀스 번호, 그룹 번호, fid)을 박지 **shall not** 하며, 칸 빈도는 특정 곡의 BPM이 아니라 design.md §7.2의 생성기 매개변수 범위에서 시드로 뽑는다. | `REQ-LDBARMAP-014`(오디오 비커밋), `REQ-LDBARENTRY-016`(곡·장비 고유값 금지) 계승 |
| REQ-LDBARMETER-015 | [HARD] **The** 이 SPEC의 문서와 증거 **shall not** 실제 곡의 박자 판별 정확도를 주장한다. 정확도 수치는 합성 정답지에서 잰 것에만 쓰고, 실제 곡에는 판별 결과(분자·상태·사유 코드)와 현행 대비 마디 경계 차이만 기록한다. | 운영 원칙 P5. 저장소에 라벨된 3/4·6/8 실제 곡이 없다(research.md §3) |

### 5.6 R6 — 통합 경계 (REQ-LDBARMETER-016~018)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-016 | [HARD] **The** 진입 경로 **shall not** 박자를 고르는 필드·화면·옵션을 두고, `bar_map_analyse` 프레임의 모양 `{v, type, first_beat_offset}`을 바꾸지 **shall not** 한다. | 운영 원칙 P2. 프로토콜 동결 스냅샷은 그대로(`SPEC-LDBARMAP-002` REQ-LDBARENTRY-013) |
| REQ-LDBARMETER-017 | [HARD] **When** 마디 지도가 추정 상태로 저장되면, 서버 **shall** 저장 성공 `chat_response`(정확히 1개)의 본문에 「박자 추정」 문구를 싣고 요약 라벨의 집합은 늘리지 **shall not** 한다. 확신 상태의 성공 응답에는 이 문구가 없다. 표지를 저장하는 자리는 OD-3(미결)이 정한다. | 운영 원칙 P3. 응답은 1개(`REQ-LDBARENTRY-012`). 요약 라벨 고정: design.md §9.1 |
| REQ-LDBARMETER-018 | [HARD] **The** 박자 판별과 마디 분할 **shall not** 콘솔에 쓰거나 읽고, `SongTimelineLibrary`에 저장하고, BPM 확정 상태(`_song_bpm`, `_song_analysis`)를 읽거나 바꾸고, `analyse_song_audio`의 메시지 계약을 바꾼다. | `REQ-LDBARENTRY-011` 계승. BPM 확정 계약 변경은 범위 밖 |

### 5.7 R7 — 회귀 (REQ-LDBARMETER-019~020)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-019 | [HARD] **The** 분석기 **shall** 저장소에 기록된 10곡 각각에서 현행 분석 결과와 같은 마디 경계를 낸다 — 칸 시각 목록이 같고, 첫 박 오프셋 0·1·2·3 각각의 다운비트·마디 경계 목록이 같다. 이 비교는 오디오가 저장소 밖에 있으므로 로컬 전용 관문이다. | D-4(기준선은 저장소에 기록된 곡 목록 그대로, 라벨 없이 「현행과 같다」). 곡 목록: `.moai/reports/t547/after_songs.txt` [carried] |
| REQ-LDBARMETER-020 | [HARD] **The** 회귀 기준선 **shall** 숫자로만 저장한다 — 곡별 칸 시각 목록, `bpm`, 두 배 판정 결과, 오디오 파일의 SHA-256. 오디오는 저장소에 넣지 **shall not** 한다. 기준선은 M2가 분석기를 바꾸기 전에 현행 코드로 두 번 재서 결과가 같을 때만 채택한다. | `REQ-LDBARMAP-014`. 절차: design.md §11. 비결정성 점검의 필요: 바이트 비교가 원리적으로 불가능할 수 있다는 이 저장소의 교훈(`lesson-a-byte-comparison-can-be-impossible-by-construction.md`) |

### 5.8 R8 — 동결 문서 경계 (REQ-LDBARMETER-021)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMETER-021 | [HARD] **The** 이 SPEC의 plan·run·sync 작업 **shall not** `.moai/specs/SPEC-LDBARMAP-001/`과 `.moai/specs/SPEC-LDBARMAP-002/` 아래 어떤 파일(본문, frontmatter, HISTORY, progress.md 포함)도 수정한다. 대체는 §3의 선언뿐이다. | D-1, D-2 |

## §6. 결정과 열린 질문

### 6.1 확정된 결정 (리드, 2026-10-15) — 다시 열지 않는다

| # | 결정 |
|---|---|
| D-1 | 새 SPEC `SPEC-LDBARMAP-005`를 만든다. SPEC-002는 다시 열지 않는다. 이 SPEC은 SPEC-001·002를 파일 경로와 줄·REQ·AC로 **링크**만 한다 |
| D-2 | SPEC-001의 본문과 frontmatter는 고치지 않는다 |
| D-3 | 첫 박 오프셋(SPEC-002의 D1)은 사람이 지정한 채로 둔다. 이 SPEC의 범위 밖이다 |
| D-4 | 회귀 기준선은 저장소에 기록된 곡 목록 그대로다. 라벨된 4/4 정답이 없으므로 기준은 「현행 분석 결과와 같은 마디 경계」다 |

### 6.2 운영 원칙 → 요구·수락 기준 대응

| 원칙 | 내용 | REQ | AC |
|---|---|---|---|
| P1 | 어떤 음악이 들어와도 진행된다. 박자를 모르거나 모호해도 거절하지 않는다 | 008 | 003, 013 |
| P2 | 박자 선택 화면도 요청 필드도 없다 | 016 | 014 |
| P3 | 불확실하면 4/4로 진행하고 「박자 추정」을 표시한다. 불확실성 규칙은 실제 곡을 보기 전에 사전 등록한다 | 003, 005, 006, 007, 017 | 001, 002, 003, 004, 007, 015 |
| P4 | 합성 정답지가 먼저다. 문턱은 사전 등록하고 실제 곡으로 조정하지 않는다 | 003, 013, 014 | 001, 005, 006, 007, 020 |
| P5 | 실제 곡 정확도를 주장하지 않는다 | 015 | 019 |

### 6.3 열린 결정 — 감독이 정한다

**OD-3 — 「박자 추정」 표지를 어디에 저장하는가.** **미결 — 착수 승인 게이트에서 감독 확정.** SPEC-001의 저장 검증은 알 수 없는 필드를 거절한다(`bar_map_store.py:175-177`). 선택지와 코드 근거는 design.md §9.2.

- **선택지 1 (기본안)**: 저장하지 않는다. 저장 성공 응답의 본문에만 싣는다. 검증기·저장 모양·SPEC-002 REQ-LDBARENTRY-010이 모두 그대로다. 치르는 값: 연결을 다시 맺으면 표지가 없다.
- **선택지 2**: 저장한다. 2a는 마디 지도 사전 안에 필드를 더한다 — 검증기 본문이 바뀐다. 2b는 타임라인의 형제 키에 둔다 — 검증기는 그대로이나 REQ-LDBARENTRY-010을 개정한다.
- **검증기 본문을 바꾸지 않는 안이 존재한다.** 선택지 1과 2b는 둘 다 `validate_bar_map`을 건드리지 않는다. 그 가운데 SPEC-002 REQ-LDBARENTRY-010까지 건드리지 않는 것은 선택지 1뿐이라 기본안으로 두었다.
- 기본안으로 둔 이유와 위험: design.md §9.2. 같은 자리 문제를 형제 SPEC(`SPEC-LDBARMAP-004`, draft, 다른 워크트리)도 안고 있어 함께 정하는 편이 일관된다(OQ-10).

**OD-4 — 오프셋이 판별한 분자 이상일 때(예: 오프셋 3인데 판별이 3/4).** **미결.** 이 SPEC은 정하지 않는다. 선택지 셋(거절, 나머지로 줄임, 후보 배제)과 코드 근거는 design.md §10. REQ-LDBARMETER-012는 이 경우를 다루지 않는다.

### 6.4 열린 질문 — 답이 없다

| # | 질문 | 어디서 나왔나 |
|---|---|---|
| OQ-1 | 3칸 주기는 유의한데 3과 6을 가르는 홀짝 검정이 모호할 때 P3를 문면대로 4/4로 갈지, 부분 정보를 써서 3으로 갈지 | design.md §5 U-6. 4로 가면 3/4 곡이 틀린 경계로 저장된다 |
| OQ-2 | 두 배 BPM 검사가 `ambiguous`를 표시했을 때 박자 판별을 추정으로 만드는 규칙(U-1)을 확정할지 | design.md §5. 사전 등록 제안이다 |
| OQ-3 | 6/8을 점4분음표 펄스로 잡은 곡을 어떻게 다룰지 — 칸 사이 3등분 대 2등분 온셋 판정과, 6칸 마디로 저장하기 위한 보간 격자 | design.md §3.3. 이 SPEC의 6/8 주장은 8분음표 펄스에 한정된다 |
| OQ-4 | 2/4를 후보에서 뺀 결정(design.md §3.2)이 맞는지 | 리드의 안은 2/4를 선택으로 두었다 |
| OQ-5 | 두 배 BPM 채택은 저장 거절이다(REQ-LDBARENTRY-008). 「어떤 음악이든 진행」(P1)을 BPM 배수 거절까지 넓혀 읽을지 | 이 SPEC은 BPM 확정 계약을 건드리지 않는다(§8) |
| OQ-6 | 타임라인에 `time_signature` 문자열이 있으면 편집 검증이 그것을 `bar_map`보다 먼저 읽는다(`beat_grid_edit.py:326-347` [carried]). 견본 타임라인은 이 문자열을 `"4/4"`로 고정 기록한다(`sugar_timeline.py:473` [measured: research.md 부록 A-12f]). 판별이 3/4를 저장해도 편집 검증은 4를 쓸 수 있다 — 에미터는 `bar_map`의 3을 쓴다. 무엇이 이겨야 하는가 | research.md §4 |
| OQ-7 | 곡 중간에 박자가 바뀌는 곡(알려진 한계)에 판별 한 번으로 충분한가 | §8, Gaps 8 |
| OQ-8 | 6/8을 8분음표 펄스로 저장하면 `bpm`이 점4분음표 템포가 아니라 8분음표 빈도다. 화면에 보일 템포를 무엇으로 할지 | design.md §3.4. 후속 UI 카드의 일 |
| OQ-9 | 사전 등록 문턱 PR-01~PR-18(시드 30, 27/30 등)은 설계자의 제안이다. 감독 또는 plan-auditor가 값을 받아들이는지 | design.md §6. 착수 승인 때 동결한다 |
| OQ-10 | 형제 SPEC-LDBARMAP-004(draft, `../WT-barmap-song-match`)가 같은 종류의 저장 자리 문제(`bar_map` 밖에 값을 얹으면 REQ-LDBARENTRY-010과 부딪힌다)를 다룬다. OD-3을 그 SPEC의 결정과 함께 정할지 | design.md §9.2 근거 2. 그 SPEC은 이 트리와 `origin/main`에 없고, 다른 세션이 고치는 중이라 이 plan-phase가 읽는 사이에도 내용이 바뀌었다 |
| OQ-11 | `analyze.py:526`의 구간 경계 하한이 4칸 마디를 가정한다. 박자 판별 결과를 거기에 먹일지 | research.md §2. 이 SPEC의 범위 밖 |
| OQ-12 | 사건 분류기의 문턱(`bar_map.py:494-553`)이 4/4 곡(LOVE ATTACK)으로 맞춰졌다. 3/4·6/8 마디에서 다시 점검할지 | design.md §12 |

## §7. Gaps — 확인하지 못한 것

1. **아무것도 실행하지 않았다.** 시험도 코드도 돌리지 않았다. 판별 알고리즘(design.md §4)은 한 번도 실행된 적이 없으며, 이 SPEC은 성능을 주장하지 않는다. M1이 처음으로 잰다.
2. **라벨된 3/4·6/8 실제 곡 오디오가 저장소에 없다.** 리드의 「그런 곡이 있다」는 진술은 확인하지 못했다(research.md §3). 실제 곡 정확도는 말할 수 없다(P5).
3. **「11곡」을 저장소에서 찾지 못했다.** 기록은 10곡이다(D-4). 참고로 로컬 샘플 폴더에 오디오 파일이 10개 있고 그 가운데 9개가 기록된 곡이며 1개(wav)는 기록에 없다. LOVE ATTACK은 폴더 밖에 있다. 이것이 「11」의 출처라는 것은 추정이다(research.md §3).
4. **기록된 10곡의 박자표를 사람이 확인한 기록이 없다.** 회귀 기준은 「참 박자」가 아니라 「현행과 같다」이다. 10곡 가운데 4/4가 아닌 곡이 있는지 이 plan-phase는 알지 못한다 — 발견하지 못했을 뿐 4/4임을 확인한 것이 아니다. 10곡 중 7곡의 실행 산출물(`.moai/reports/t499/runs/<곡>/events.json`)에 `"time_signature": "4/4"` 줄이 있으나, 같은 문자열이 코드의 기본값·고정 리터럴이기도 해서 확인의 증거로 세지 않는다(research.md §3). M3에서 다른 N을 확신한 곡이 나오면 그대로 보고하고 멈춘다(design.md §11.5).
5. **칸 세기 신호가 실제 곡에서 충분한지 모른다.** 위상(마디의 첫 박) 자동 선택이 실제 곡에서 0/82로 실패한 선례가 있다(`SPEC-LDBARMAP-001/spec.md:29` [carried]). 박자 주기 판별은 다른 문제이지만 같은 종류의 신호를 쓴다. 실제 곡에서 추정 비율이 높을 수 있다 [predicted] — 재지 않았다.
6. **부호검정의 독립 가정.** 칸 세기는 자기상관이 있어 p 값이 실제보다 낙관적일 수 있다(design.md §12). 합성 관문은 이 효과를 재지 못한다.
7. **사건 분류기·특징 창의 3/4·6/8 적합성.** `classify_bar_events`의 문턱은 4/4 곡으로 맞춘 비율이다. 이 SPEC의 관문에 들어 있지 않다(OQ-12).
8. **곡 중간의 박자 변화는 지원하지 않는다.** 판별은 곡 전체에 한 번 한다. 알려진 한계다.
9. **복합박을 점4분음표 펄스로 잡은 경우는 다루지 않는다**(OQ-3, design.md §3.3).
10. **추적기의 칸 일치를 재지 않았다.** 합성 클릭 트랙에서 `beat_track`이 생성한 칸을 얼마나 잡는지는 G-B가 처음 잰다(design.md §7.5).
11. **다른 워크트리의 SPEC-LDBARMAP-003·004는 읽기만 했다.** 두 SPEC은 이 트리와 `origin/main`에 없다. 004는 `bar_map.py`·`bar_map_entry.py`·`bar_map_store.py`·`session.py`를 모듈 목록에 올려 이 SPEC의 변경 파일과 겹친다(research.md §5). 병합 순서에 따른 충돌은 점검하지 않았다.
12. **줄 번호는 `bef3e16d` 기준이다.** 다른 세션이 같은 파일(특히 `session.py`)을 고치면 줄이 움직인다.
13. **실기 콘솔 확인은 해당 없음**이다 — 이 SPEC은 콘솔을 만지지 않는다.

## §8. 제외 범위 (Out of Scope)

### 8.1 Out of Scope — 박자 선택 화면과 요청 필드

- 박자표를 고르는 화면, 선택지, 요청 프레임의 박자 필드(P2). `bar_map_analyse`는 `{v, type, first_beat_offset}`로 남는다.
- 「박자 추정」 표지를 화면에 보이는 일은 후속 UI 카드의 몫이다.

### 8.2 Out of Scope — 첫 박 오프셋의 자동 검출

- 첫 박 오프셋(SPEC-002의 D1)의 추정·기본값·자동 위상 선택(D-3). 사람이 지정한다.

### 8.3 Out of Scope — 실제 곡 정확도 주장

- 3/4·6/8 실제 곡에 대한 판별 정확도 수치(P5). 합성 정답지의 수치만 주장한다.

### 8.4 Out of Scope — 박자 변화와 후보 밖 박자

- 곡 중간에 박자가 바뀌는 곡의 구간별 판별(알려진 한계).
- 2/4, 5/4, 7/8 등 후보 밖 박자를 판별 결과로 내는 일. 후보 밖 입력은 추정 4/4로 진행한다.
- 칸 사이의 3등분·2등분 온셋 판정과 보간 하위 박 격자(OQ-3).

### 8.5 Out of Scope — 오디오 커밋

- 합성 픽스처나 실제 곡 오디오를 저장소에 커밋하는 일(REQ-LDBARMETER-014, -020).

### 8.6 Out of Scope — BPM 확정 계약과 분석기의 나머지

- SPEC-002 REQ-LDBARENTRY-011의 BPM 확정 계약, `analyse_song_audio`, 두 배 BPM 판정 재설계, 두 배 BPM 채택 거절(REQ-LDBARENTRY-008).
- `extract_bar_features`·`classify_bar_events` 수정, `analyze.py`의 구간 경계 하한(`:526`).
- `validate_bar_map`과 저장 스키마 변경(OD-3 선택지 2a를 고르지 않는 한).

### 8.7 Out of Scope — 콘솔과 하드웨어

- 콘솔 쓰기·읽기, `SongTimelineLibrary` 저장. 이 plan-phase 자신은 문서만 쓴다 — 코드 수정, 시험 실행, 콘솔 접촉, SPEC-001·002 디렉터리 수정, 커밋이 모두 0건이다.
