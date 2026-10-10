# SPEC-LDBARMAP-001 — 진행 기록

카드: t527(plan-phase) / t530(M1 run-phase). plan-phase 세션은 `server/` 코드 변경
0줄, 콘솔 접촉 0건이었다. M1 run-phase(이 세션)도 `server/` 코드 변경 0줄, 콘솔
접촉 0건이다(REQ-LDBARMAP-002/003) — 측정·채점 스크립트만 `tools/barmap/`에 신설했다.

## 작성된 파일

- `.moai/specs/SPEC-LDBARMAP-001/spec.md` — REQ 16개(R1~R6, R6은 카드 t530이 신설한 REQ-LDBARMAP-016), Out of Scope 5개 H3 섹션, 열린 결정 4개
- `.moai/specs/SPEC-LDBARMAP-001/plan.md` — M1~M5 마일스톤(저장 인터페이스 열린 결정을 마일스톤보다 먼저 제시)
- `.moai/specs/SPEC-LDBARMAP-001/acceptance.md` — AC 16개(Given-When-Then + 수치·단위 + REQ-ID 인용), Definition of Done
- `.moai/specs/SPEC-LDBARMAP-001/research.md` — 이 plan-phase가 실행한 10개 실측(명령+출력)
- `.moai/specs/SPEC-LDBARMAP-001/progress.md` — 이 파일

## plan-audit 이력

- iteration 1: FAIL(0.60, 통과선 0.80). `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-1.md`. D1(critical, AC-006 분모 13≠8)·D3(critical, 1마디 밀림 음성 대조군·매칭 방법론 누락)·D2(major, REQ-010/012 이중 모달)·D4(major, AC→REQ 인용 희박 + REQ-001 무검증)·D5(minor, 224.70/224.69 불일치) — 모두 spec.md·acceptance.md에 교정 반영(REQ 14→15, AC 13→15). D6(minor, 선택)은 비용 대비 효과가 낮아 보류.
- iteration 2: FAIL(0.68, 통과선 0.80). `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-2.md`. D1~D6(iteration 1) 전부 RESOLVED 재확인. iteration 1의 AC-003 신설이 그 뒤 AC 번호를 전부 1씩 밀렸는데 `plan.md`가 반영 못 함 — **D-NEW-1(critical)**: M1(`plan.md:31` AC-001~005→001~006)·M2(`plan.md:38` AC-004/005→005/006)·M3(`plan.md:45-46` AC-006→007, M3 자신이 가리키려던 이벤트 재현율은 007)을 재매핑. **D-NEW-2(minor)**: `acceptance.md` AC-009가 무관한 REQ-008을 인용 — REQ-001(간접)로 재지정. 교정 뒤 spec.md/plan.md/research.md/progress.md 전수 grep 재확인(research.md·progress.md 0건, plan.md 4건 전부 교정). REQ/AC 총량 변경 없음(15/15).
- iteration 3: **PASS(0.86, 통과선 0.80)**. `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-3.md`(주 체크아웃, gitignore — 1~3행 `Verdict: PASS` / `Overall Score: 0.86`). must-pass 7개 PASS, D-NEW-1/D-NEW-2 RESOLVED 재확인. Implementation Kickoff Approval 가능 판정 — 감독 착수 승인 2026-10-10(M1~M3, 카드 t530).
- iteration 4(부분, v0.1.3 개정분만 — 카드 t530): FAIL(0.68). `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-4.md`(t530 워크트리, gitignore). D1(must-pass MP-2: REQ-016 굵은 shall 없음)·D2(spec.md §0 REQ/AC 15개 표기 잔존)·D3(progress.md 같은 잔존). 교정 커밋 `e3e63a17`.
- iteration 5(부분, D1~D3 델타): **PASS(0.95)**. `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-5.md`. D1~D3 RESOLVED, 개정 범위 안 새 결함 0.

## §E.1 Plan-phase Audit-Ready Signal

plan_status: audit-passed (iteration 3 PASS 0.86 — 2026-10-10, 정정: 카드 t530)
plan_complete_at: 2026-10-10

5개 산출물이 모두 작성되었고, SPEC ID 사전 검사(Bash 정규식)가 PASS했으며, 프런트매터 12개 필수 필드가 모두 채워졌다. plan-audit iteration 1·2 FAIL 교정을 거쳐 iteration 3에서 PASS(0.86)했다.

## 인터페이스 맞춤 (카드 t529, 2026-10-10)

- 바뀐 곳: `spec.md` frontmatter(version만), §5 열린 결정 0·항목 1(권고 모양 추가), HISTORY 1행, version 0.1.0→0.1.1. **REQ 표·`acceptance.md`·`plan.md`는 한 글자도 안 바꿨다.**
- plan-audit 재실행 안 함 — 사유: 추가한 것은 §5 열린 결정 안의 **권고**(확정 아님)뿐이고, 저장 형태 확정 금지(REQ-LDBARMAP-010)·마디 지도 없이는 생성 로직 미구현(REQ-LDARRANGE-001)·STROBE는 임팩트 마디에만(REQ-LDARRANGE-008) 같은 구속의 뜻은 그대로다. 권고 모양은 그 구속들이 이미 요구하는 것(마디 단위, REQ-LDBARMAP-007의 단위 명시, REQ-LDBARMAP-008의 사건 4종)에 이름을 붙인 것이다.
- 마디 번호 공간 실측(t529): 지도 보고서 §2 "마디 번호는 위상 1 기준이다. 1마디 = 1.50초. 0.96초의 첫 박은 못갖춘마디" · 같은 보고서 18마디 = "후렴 1 진입 — 큰 히트" · 배치 규칙서 §3 18~21행 = "코러스 1 앞", §4 첫 행 = "0~2" — 두 문서가 같은 번호 공간을 쓰고 0은 못갖춘마디다.
- ③ 저장 키 맞춤(t529 후속, 2026-10-10): §5 열린 결정에 세 SPEC 공통 권고 키 `timeline["beat_grid"]`/`["bar_map"]`/`["arrangement_draft"]` 추가. 권고뿐 — REQ·AC·plan.md·acceptance.md 변경 0, plan-audit 재실행 없음.

## §E.2 Run-phase Evidence

### M1 — 계기 보정(카드 t530, 2026-10-10)

산출물: `tools/barmap/{__init__,ground_truth,scorer,candidates,run_calibration,test_scorer}.py`
(신규, `server/` 아래 0줄 변경) + `.moai/reports/SPEC-LDBARMAP-001-probes/{m1-calibration.md,
m1-raw-stdout.txt,m1-pytest-output.txt,m1-ruff-output.txt}`(신규, gitignore 대상이라
`git add -f`로 올림). 전체 수치·근거·Gaps는 `m1-calibration.md`에 있다 — 여기서는
AC PASS/FAIL 요약만 반복한다.

| AC | 상태 | 근거 |
|---|---|---|
| AC-LDBARMAP-001 | **PASS** | 네 지표 전부 수치+단위 출력, `git diff --stat origin/main -- server/` 출력 0줄, 콘솔 쓰기 0건 |
| AC-LDBARMAP-002 | **PASS** | 1박 밀림 음성 대조군 0/82(0.0%) < 10% |
| AC-LDBARMAP-003 | **PASS** | 1마디 밀림 음성 대조군 0/82(0.0%) < 10%(엄격한 순서 대응으로 D3 함정 차단 확인) |
| AC-LDBARMAP-004 | **PASS**(후보 A/B/C 전부) | 후보 C가 두 배 BPM 함정(raw 224.69)을 실제로 겪고 격자 정합도 비교 후 112.35로 보정 + 근거 기록. A/B는 함정 미발동(공허 PASS) |
| AC-LDBARMAP-005 | **FAIL**(후보 A/B/C 전부, 자체 위상 선택 기준 0.0%) | 세 후보의 자체 위상 선택 규칙(온셋 악센트/화성 변화/저역 도약)이 모두 정답 위상(1)을 못 골랐다 — 위상 1로 강제하면 A 100%·B 97.6%(진단용, PASS로 세지 않음) |
| AC-LDBARMAP-006 | **FAIL**(동일 격자, AC-005와 같은 이유) | 4/4박자라 다운비트=마디 경계(spec.md §5 결정 3) |
| AC-LDBARMAP-007 | **FAIL**(A 0/7, B·C 1/7=14.3%, 통과선 5/7=70%) | M1 간이 이벤트 규칙 — M3가 실제 분류기 담당 |

**M1 통과 조건("AC-001~006 전부 PASS인 후보 최소 1개 존재") 미충족** — 세 후보
모두 AC-005/006에서 FAIL한다. plan.md M1이 명시한 원칙("채점 전 채택하지 않는다")
대로 정직하게 보고한다: 세 후보의 BPM·비트 격자 자체는 거의 완벽(오차율
0.003%, 올바른 위상으로 보면 다운비트 적중 100%/97.6%)하지만, **다운비트 위상
선택(1~4박 중 어느 것이 "하나"인가)이 M1에서 풀리지 않은 문제로 남았다** — 지도
보고서 자신도 이 위상을 [미확정(귀로)]로 표기했던 바로 그 지점이다. M2는 이
위상 문제를 우선 다뤄야 한다(단일 신호 대신 앙상블/투표, 또는 사람 확인 단계
유지).

Preserve 목록 확인: `SPEC-LDRHYTHM-001`·`SPEC-LDBEAT-001` 쪽 파일 미수정, 원곡
오디오 비커밋(`git status --porcelain`에 `*.mp3`/`*.wav` 없음), `server/audio/analyze.py`는
`_tempo_from_beats`만 읽기 전용 import로 호출 — 파일 자체는 안 고침.

### M1 판정 후 감독 결정(2026-10-10, 리드 경유)

- **M1 통과선 미달은 그대로 기록한다**: AC-001~006 전부 PASS인 후보 0개(자기 위상 기준 다운비트 0/82, 세 후보 모두). 박 격자·BPM은 맞았다(위상 1 강제 시 A 82/82, B 80/82).
- 결정: 「귀 확인 + 수동 지정 병행」 — (1) 위상 후보 4개 클릭 파일을 감독이 듣고 첫 박 위상을 확정, (2) M2 범위 축소: 박 격자는 자동, 마디 첫 박은 사람이 지정(「첫 박 오프셋」 한 값), 자동 위상 선택은 보류.
- PR #575(M1 결과·도구) 머지 `de5f5fdd`(CI `test` pass, head `c3903b15` 확인 후 별도 호출로 머지).

### 위상 확인용 클릭 파일(저장소 밖, 커밋 안 함)

- 위치: `/Users/studiox/Music/AI-Lighting_Console-listen/t530/`
- 파일: `LOVE_ATTACK_t530_phase0_40s.wav` · `..._phase1_40s.wav` · `..._phase2_40s.wav` · `..._phase3_40s.wav` (각 앞 40초, 44.1kHz mono, 3,528,044바이트)
- 내용: 원곡(0.6배 음량) + 마디 첫 박 강한 클릭(1760Hz) + 나머지 박 약한 클릭(880Hz). 위상 규칙은 지도 보고서 §3과 같다 — 박 번호 i에서 (i − phase) % 4 == 0인 박이 첫 박.
- 명령: `.venv/bin/python tools/barmap/make_phase_clicks.py "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3" /Users/studiox/Music/AI-Lighting_Console-listen/t530`
- 출력(그대로):
  ```
  beats=326 tempo=112.35 first5=[0.96, 1.5, 2.04, 2.58, 3.11]
  LOVE_ATTACK_t530_phase0_40s.wav 첫 박(강클릭) 앞 4개=[0.96, 3.11, 5.26, 7.37]
  LOVE_ATTACK_t530_phase1_40s.wav 첫 박(강클릭) 앞 4개=[1.5, 3.66, 5.78, 7.92]
  LOVE_ATTACK_t530_phase2_40s.wav 첫 박(강클릭) 앞 4개=[2.04, 4.2, 6.46, 8.45]
  LOVE_ATTACK_t530_phase3_40s.wav 첫 박(강클릭) 앞 4개=[2.58, 4.73, 6.86, 8.99]
  ```
- 대조: 박 326개·112.35 BPM은 지도 보고서 §6 「박 시각 326개」와 같고, phase1 첫 박 넷(1.50·3.66·5.78·7.92초)은 부록 A 1~4마디 다운비트와 일치한다(같은 박 경로라는 확인 — 정답 여부는 감독 귀 확인이 정한다).
- **확인됨(2026-10-10)**: 감독 청취 결과 — phase1 채택(아래 "위상 정답 확정" 참조). "미확인: 감독 청취 결과(대기 중)"이던 이전 기록을 이 줄로 교정한다.

### 위상 정답 확정(카드 t530, 2026-10-10)

위상 정답 = **phase1**, 감독 귀 확정 2026-10-10, 근거 t530 클릭 wav
(`/Users/studiox/Music/AI-Lighting_Console-listen/t530/LOVE_ATTACK_t530_phase0_40s.wav`,
`..._phase1_40s.wav`, `..._phase2_40s.wav`, `..._phase3_40s.wav`). 후렴 1 진입(0:37.9)에서
강한 클릭이 "하나"에 떨어지는 것을 들어 확정했다 — 지도 보고서 부록 A의 1마디
다운비트(1.50초)와 일치한다. 지도 보고서 §6이 **[미확정(귀로)]**로 매겼던 "다운비트
위상"은 이제 **감독 귀 확정** 등급으로 올라갔다(spec.md REQ-LDBARMAP-009 근거 칸 갱신,
2026-10-10) — 그 외 "추정" 항목(구간 이름·드롭 63~66마디 등)은 등급 불변. M2 회귀
기준 오프셋 값은 **1**(REQ-LDBARMAP-016 정본 단위, acceptance.md AC-LDBARMAP-016·
plan.md M2 참조)로 고정했다. 자동 위상 선택기 재설계는 여전히 **보류**(follow-up) —
이 확정은 정답지 쪽 불확실성만 없앤다.

### SPEC 개정(카드 t530, 2026-10-10) — M2 범위 축소 반영

M1 판정 결과(위 표, AC-LDBARMAP-005/006 FAIL — 세 후보 모두 자체 위상 선택 기준
다운비트 0/82)에 따른 리드 경유 감독 결정("귀 확인 + 수동 지정 병행")을 spec.md·
plan.md·acceptance.md에 반영했다 — REQ-LDBARMAP-016(신설, 수동 첫 박 오프셋·정수
0~3) 추가, REQ-LDBARMAP-004 근거 칸·AC-LDBARMAP-005/006에 "보류 — 감독 귀 확정
정답 뒤 재설계" 주석 추가(PASS 요구 대상에서 제외, 회귀 추적용 참고 지표로 보존),
AC-LDBARMAP-016(신설, 오프셋 기반 평가 — M2 실제 통과 기준) 추가, plan.md M1/M2/M3
갱신(M1 통과 조건 미충족을 그대로 기록 + M2는 그 조건이 아니라 이 감독 결정으로
진행함을 명시). REQ 15→16개·AC 15→16개(Tier M 상한 16개에 정확히 닿음, 초과 없음).
version 0.1.2→0.1.3. 코드 변경 0줄 — 이 개정은 plan-phase 문서 3개(spec.md·plan.md·
acceptance.md)만 다룬다. 커밋: `2f79fdb045acd9c2d7c922fc4191a0905b0081cf`(백필 —
직전 커밋이 자기 자신의 SHA를 몰라 `pending-backfill-SPEC-LDBARMAP-001-t530-amendment`로
썼던 것을 실제 SHA로 교정, 워크트리 `.claude/worktrees/t530`, 브랜치 `WT-barmap-run`).

**같은 개정에 접어 넣은 추가분(위 "위상 정답 확정" 참조, 별도 버전 올리지 않음)**:
감독이 위상 클릭 wav를 듣고 phase1을 다운비트 정답으로 확정한 결과를 REQ-LDBARMAP-009
근거 칸(spec.md)·AC-LDBARMAP-005/006 보류 주석(acceptance.md)·M2 회귀 기준 오프셋
(plan.md, acceptance.md AC-016)에 반영했다 — REQ·AC 개수·version 변경 없음(여전히
16/16, 0.1.3). 커밋: `e376bc169a390c3d710ecf32c6b8a15e63156973`(백필 — 직전 커밋이 자기 자신의
SHA를 몰라 `pending-backfill-SPEC-LDBARMAP-001-t530-phase-confirm`으로 썼던 것을
실제 SHA로 교정).

### M2 — 다운비트·마디 경계 검출기, 사람이 지정한 첫 박 오프셋 기반(카드 t530, 2026-10-10)

산출물: `server/audio/bar_map.py`(신규, `detect_beat_grid`·`derive_bars`, `server/audio/analyze.py`는
**읽기만** 함 — `_HOP_LENGTH`·`_MIN_DECODED_FRACTION`·`_mp3_length_is_a_bitrate_guess`·
`_tempo_from_beats`·`analysis_available`·`MANUAL_BPM_FALLBACK_REASON`을 import해 재사용, 파일 자체는
0줄 수정 — `git diff --stat HEAD -- server/audio/analyze.py` 출력 0줄로 확인) +
`server/tests/test_audio_bar_map.py`(신규, 42개 테스트) +
`server/tests/fixtures/love_attack_beat_grid.json`(신규 — LOVE ATTACK 326개 검출 비트
시각(ms)만 담은 **파생 숫자 픽스처**, 오디오 아님, `detect_beat_grid`가 원곡에서 실제로
검출한 숫자를 고정한 것) + `.moai/reports/SPEC-LDBARMAP-001-probes/{m2-pytest-output.txt,
m2-ruff-output.txt}`(신규 — gitignore 대상, `git add -f`로 올림).

**`detect_beat_grid`**: `analyze()`와 같은 디코드 경로(soundfile 읽기 → mono 다운믹스 →
`librosa.beat.beat_track` hop=512)를 재사용한다. REQ-LDBARMAP-006(절반/두 배 격자 정합도
비교 + 채택 근거 기록)은 M1 보정 스크립트(`tools/barmap/scorer.py`)의 LOVE ATTACK 전용
고정 함정 상수(56.175/224.69)에 기대지 않고, 원시 추정치 자신의 절반·두 배와 비교하는
일반화된 버전으로 production 모듈 안에 별도 구현했다(`_check_bpm_half_double` — 개발
도구 모듈을 production이 import하지 않는다). 예외를 밖으로 내보내지 않는다(`analyze.py:297`과
같은 계약) — `BeatGridResult | BeatGridFailure`.

**`derive_bars`**: 순수 함수(librosa 미사용). `beat_times[i]`에서 `(i − offset) % 4 == 0`인
자리를 다운비트/마디 경계로 삼는다(REQ-LDBARMAP-016). 오프셋 이전 박은 못갖춘마디로
분류해 마디 번호에서 뺀다(마디 1 = 첫 다운비트, 지도 보고서 부록 A와 일치). 오프셋이
정수 0~3 범위를 벗어나면 `BarMapFailure`(예외 아님 — `analyze.py`와 같은 "예외를 밖으로
내보내지 않는다" 원칙을 모듈 전체에 적용, `bool`은 `int`의 서브타입이지만 명시적으로
거부).

| AC | 상태 | 근거 |
|---|---|---|
| AC-LDBARMAP-015 | **PASS** | M2 구현 시점 — 실제 함수 시그니처 검사로 전환. `detect_beat_grid(audio_bytes: bytes)` 단일 인자(완결 바이트열), `derive_bars(beat_times_ms, first_beat_offset)` 둘 다 스트리밍 핸들·콜백 없음(`test_ac015_*` 2건 PASS) |
| AC-LDBARMAP-016 | **PASS** | 오프셋=1(감독 귀 확정)로 `derive_bars` 후 `tools/barmap/scorer.strict_index_hit_rate`(±60ms, 엄격한 순서 대응)로 채점 — 다운비트 적중률 **82/82(100.0%)**, 마디 경계 적중률(4/4박자라 같은 수열) **82/82(100.0%)**, 둘 다 통과선 90% 이상 |
| AC-LDBARMAP-014 | **PASS(유지)** | 이 M2 커밋에도 `*.mp3`/`*.wav` 확장자 변경 파일 0건(`git status --short` 확인) |

음성(오프셋) 대조군 — 엄격한 순서 대응이 「잘못된 위상」을 통과시키지 않는지 재확인:

| 오프셋 | 다운비트 적중률 | 기대 | 판정 |
|---|---|---|---|
| 0 | 0/82 (0.0%) | <10% | **PASS** |
| 1(감독 귀 확정) | 82/82 (100.0%) | ≥90% | **PASS**(AC-LDBARMAP-016) |
| 2 | 0/82 (0.0%) | <10% | **PASS** |
| 3 | 0/82 (0.0%) | <10% | **PASS** |

명령 + verbatim 출력(`.moai/reports/SPEC-LDBARMAP-001-probes/m2-pytest-output.txt`에 재수록):

```
.venv/bin/python -m pytest server/tests/test_audio_bar_map.py tools/barmap -q
..........................................                               [100%]
42 passed in 2.27s
```

```
.venv/bin/python -m ruff check server/audio/bar_map.py server/tests/test_audio_bar_map.py
All checks passed!
.venv/bin/python -m ruff format --check server/audio/bar_map.py server/tests/test_audio_bar_map.py
2 files already formatted
```

기존 `analyze()` 회귀(변경 없음 확인용 — `server/audio/analyze.py` 0줄 변경이므로 당연히
그대로지만 명시적으로 재실행):

```
.venv/bin/python -m pytest server/tests/test_audio_analyze.py server/tests/test_audio_boundary.py \
    server/tests/test_audio_fallback.py server/tests/test_audio_grade_saturation.py \
    server/tests/test_audio_segment_floor_bars.py -q
........................................................................ [ 67%]
..................................                                       [100%]
106 passed in 7.83s
```

로컬 전용 회귀(원곡 있을 때만, `pytest.mark.skipif` — 이번 세션은 원곡 존재해 PASS로
실행됨, CI에서는 자동 skip): `test_detect_beat_grid_real_love_attack_matches_fixture_and_ac016` —
실제 `"/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"`로 다시 재도
BPM 112.347(±0.005 상대오차 안), 326개 비트가 픽스처와 1ms 이내로 일치, AC-016 재현
(82/82, 100.0%) — 42개 테스트 안에 포함되어 위 출력에 이미 들어 있다.

**Gaps(미검증, 정직하게 기록)**:
- REQ-LDBARMAP-006의 절반/두 배 비교 로직이 실제로 "함정을 올바르게 잡는" 경우(진짜
  절반/두 배 오추정 상황)에 대한 전용 단위시험은 없다 — LOVE ATTACK·합성 클릭 트랙
  둘 다 함정이 발동하지 않는 사례만 재현했다(`trap_triggered=False`). 완전 주기적인
  합성 데이터에서는 절반/두 배/원시 격자가 서로 포함 관계라 위상을 쓸어도 적중률이
  똑같이 1.0이 나오는 구조적 한계 때문에(실측 확인) 함정이 실제로 발동하는 시나리오를
  결정론적으로 합성하지 못했다 — follow-up.
- `trap_triggered=True`일 때 `beat_times_ms` 배열 자체를 재구성(resample)하지 않는다 —
  채택된 BPM과 격자 간격이 불일치할 수 있는 알려진 한계(M1 후보 C의
  `reconstruct_uniform_grid`처럼 재구성하지 않음). 이 SPEC 범위(LOVE ATTACK, beat_track
  경로)에서는 함정이 발동하지 않아 실제로 문제가 되지 않았다.
- AC-LDBARMAP-005/006(검출기 자신의 위상 선택)은 이번에도 보류 상태 그대로다 — M2는
  다루지 않는다(자동 위상 선택기 재설계는 follow-up).

**리드 재측정 메모(카드 t530, M2 수령 시)** — BPM 값은 프레임 양자화 격자 위의 값이다:
- 명령: `.venv/bin/python -c "for sr in (22050,44100): f=512/sr; [print(sr,n,round(n*f*1000,2),'ms',round(60/(n*f),3),'BPM') for n in (45,46,47)]"`
- 출력(발췌): `44100 45 522.45 ms 114.844 BPM` · `44100 46 534.06 ms 112.347 BPM` · `44100 47 545.67 ms 109.957 BPM`
- 뜻: `_tempo_from_beats`(analyze.py, 박 간격 **중앙값**)는 hop 512 프레임(44.1kHz에서 11.61ms) 단위로 양자화된 간격의 중앙값을 쓰므로, BPM은 109.96 / 112.35 / 114.84처럼 프레임 한 칸씩 띄엄띄엄 나온다. 정답지 112.35도 같은 경로의 값이라 M1/M2의 「BPM 오차 0.003%」는 **순환**이다 — 곡의 참 템포가 112.35라는 증거가 아니다. 합성 테스트가 22050Hz 대신 22×1024Hz를 쓴 것도 이 양자화를 피한 것이다.
- 영향 범위: 다운비트·마디 경계는 박마다의 개별 시각(`beat_times`)을 쓰므로 이 양자화와 무관하다(AC-016 82/82는 영향 없음). BPM 숫자를 쓰는 곳(구간 하한 마디 환산 등 analyze.py 경로)에만 해당한다.
- 처리: 이 SPEC은 analyze.py를 수정하지 않는다(plan.md §F) — 고치지 않고 Gap으로 남긴다. 필요하면 별도 카드(박 시각 선형 회귀로 BPM 추정)로.

### M3 — 마디별 변화 이벤트 분류기(카드 t530, 2026-10-10)

산출물: `server/audio/bar_map.py`(확장, `extract_bar_features`·`classify_bar_events` 신규 +
`detect_beat_grid` 디코드 블록을 `_decode_mono_audio` 공유 헬퍼로 리팩터 — 기존 42개
M2 시험 전부 재통과 확인) + `server/tests/test_audio_bar_map.py`(확장, 20개 신규 시험,
42→62개) + `tools/barmap/ground_truth.py`(확장, `parse_bar_features` 신규 — 지도
보고서 부록 A의 음량·저역·보컬 대역 비율 칸을 정규식으로 파싱, 하드코딩 사본
아님) + `tools/barmap/candidates.py`(M1 probe 어휘 `"kick_absence"` → `"break"`로
통일, 아래 "어휘 통일" 참조) + `.moai/reports/SPEC-LDBARMAP-001-probes/{m3-pytest-output.txt,
m3-ruff-output.txt}`(신규 — gitignore 대상, `git add -f`로 올림).

**분류 함수 설계**: `extract_bar_features(audio_bytes, bar_boundaries_ms)` —
`server/audio/analyze.py`와 같은 디코드 경로(이제 `detect_beat_grid`와 공유하는
`_decode_mono_audio`) + `librosa.decompose.hpss`(화성/타악 분리, `margin=(1.0, 5.0)`)로
저역(35~120Hz)은 **타악 성분만**, 보컬 대역(300~3,400Hz 비율)은 **화성 성분의 합
기반 비율**(0~1로 묶임)로 잰다. 음량(RMS)은 분리 없이 `analyze.py`와 같은
프레임 길이로 잰다. `classify_bar_events(features)`는 순수 함수(librosa 미사용) —
킥 진입(저역≥2.0배)·브레이크(저역≤0.45배 OR 온셋 개수≤2)·빌드업(큰 히트 직전
3마디 이상 연속 음량 상승, anchoring)·드롭(보컬 대역≤0.15 AND 저역≥1.4배, 참고
지표)의 네 종류(REQ-LDBARMAP-008)로 나눈다. 저장은 하지 않는다(REQ-LDBARMAP-010).

**어휘 통일**: M1(카드 t527) 당시엔 spec.md의 `events[].kind` 어휘(카드 t529
인터페이스 맞춤에서 `kick_entry`/`build`/`drop`/`break` 4개로 확정)가 아직 없어
`tools/barmap/ground_truth.py`·`candidates.py`가 "킥 멈춤" 사건에 `"kick_absence"`를
썼다. 이번 M3에서 `bar_map.py`의 분류기 출력(REQ-LDBARMAP-008 어휘)과 맞춰 둘 다
`"break"`로 고쳤다(해당 리터럴을 읽는 테스트는 없었음 — grep으로 전수 확인 후
변경, M1/M2 42개 시험 재통과로 안전 확인).

**AC-LDBARMAP-007 — 7개 사건 중 적중(두 가지 입력 경로 모두 7/7):**

| # | 사건 | 지도 보고서 구간 | ① 보고서 수치 경로(파일 비의존) 검출 마디 | ② 실제 오디오 경로 검출 마디 |
|---|---|---|---|---|
| 1 | 빌드업 1 | 14~17 | 14 | 14 |
| 2 | 빌드업 2 | 42~45 | 42 | 42 |
| 3 | 큰 히트(후렴 진입) 1 | 18 | 18 | 18 |
| 4 | 큰 히트(후렴 진입) 2 | 46 | 46 | 46 |
| 5 | 킥 멈춤 1 | 33 | 33 | 33 |
| 6 | 킥 멈춤 2 | 61 | 61 | 61 |
| 7 | 킥 멈춤 3 | 82 | 82 | 81(±1마디 허용오차 안) |

① = `tools/barmap/ground_truth.parse_bar_features()`(지도 보고서 부록 A의 음량·저역·
보컬 대역 칸을 직접 파싱, 오디오 아님 — `test_ac007_love_attack_report_features_recall_at_least_5_of_7`).
② = `extract_bar_features`가 실제 LOVE ATTACK mp3에서 재고 `classify_bar_events`로
분류한 결과(로컬 전용 — `test_real_love_attack_extraction_reproduces_volume_and_achieves_ac007`).
**드롭(63~66마디, [추정] 등급, 참고 지표 — AC-007 분모·판정 밖)**: ①에서는
`drop(start_bar=63, end_bar=66)`로 정확히 재현됐다. ②(실제 오디오)에서는 드롭이
**0건** 검출됐다 — 아래 Gaps 참조(보컬 대역 비율 분리 척도 불일치, 참고 지표라
PASS 판정에 영향 없음).

**과적합 가드(카드 지시 3) — 몇 개를 튜닝했고 무엇에 맞췄나**: 문턱 4개를 썼다.
(1) 킥 진입 저역≥2.0배, (2) 브레이크 저역≤0.45배(+ 보조 신호 온셋≤2개),
(3) 빌드업 최소 3마디 연속 상승(지도 보고서 §1 "3마디 이상 연달아 오름"을 그대로
썼다 — 튜닝 아님), (4) 드롭 보컬≤0.15·저역≥1.4배(이 SPEC이 직접 정함, 지도
보고서가 드롭에 구체 문턱을 주지 않아서 — REQ-LDBARMAP-009 "추정" 등급이라
AC-007 판정에 영향 없음). (1)·(2)는 지도 보고서 문턱(2.5·0.35)에서 시작했으나,
이 모듈의 HPSS 분리가 보고서 비공개 파이프라인보다 분리 폭이 좁아(아래 Gaps)
**두 정답지 입력 경로(①②) 모두에서 7/7을 유지하는 값**(2.0·0.45)으로 낮췄다 —
LOVE ATTACK 82개 마디 중 특정 마디에 맞춘 것이 아니라 두 독립된 측정 경로
(보고서 수치표·실제 오디오 추출) 모두에서 성립하는 값을 골랐다(단일 경로에만
맞추는 과적합과 다르다).

**민감도 확인(±20%, 카드 지시 3)** — `test_ac007_sensitivity_*`(9개 테스트,
위 pytest 출력에 포함):

| 문턱 | 기준값 | −20% | +20% | 재현율(둘 다) |
|---|---|---|---|---|
| 킥 진입 저역 배수 | 2.0 | 1.6 | 2.4 | 7/7 (둘 다, PASS) |
| 브레이크 저역 배수 | 0.45 | 0.36 | 0.54 | 7/7 (둘 다, PASS) |
| 빌드업 최소 마디 수(정수라 ±1로 해석) | 3 | 2 | 4 | 7/7 (셋 다, PASS) |

**5/7(70%) 통과선 대비 여유 폭**: 위 표의 모든 변형이 여전히 **7/7(100%)**을
유지한다 — 지식의 날(knife-edge, 문턱을 살짝만 움직여도 통과선 밑으로 떨어지는
상태)이 아니라 견고하다. 다만 진단용으로 더 넓게 흔들어 보면(테스트에 포함하지
않은 참고 수치, progress.md 기록용): 실제 오디오 경로에서 킥 진입 문턱을 기준값
대비 +32%(2.64)까지 올리면 5/7로 떨어진다(18마디 저역 2.633이 그 근방이라 — 아래
Gaps). 이는 테스트의 ±20% 범위 **밖**이라 PASS에 영향 없다.

명령 + verbatim 출력(`.moai/reports/SPEC-LDBARMAP-001-probes/m3-pytest-output.txt`에
재수록):

```
.venv/bin/python -m pytest server/tests/test_audio_bar_map.py tools/barmap -q
..............................................................           [100%]
62 passed in 14.76s
```

```
.venv/bin/python -m ruff check server/audio/bar_map.py server/tests/test_audio_bar_map.py tools/barmap/ground_truth.py tools/barmap/candidates.py
All checks passed!
.venv/bin/python -m ruff format --check server/audio/bar_map.py server/tests/test_audio_bar_map.py tools/barmap/ground_truth.py tools/barmap/candidates.py
4 files already formatted
```

기존 M2 회귀(변경 없음 확인용 — `detect_beat_grid`를 리팩터했으므로 실제로
재확인 가치가 있다):

```
.venv/bin/python -m pytest server/tests/test_audio_bar_map.py tools/barmap -q -k "not real_love_attack"
............................................................             [100%]
60 passed, 2 deselected in 1.46s
```

기존 `analyze()` 회귀(0줄 변경이라 당연히 그대로지만 명시적으로 재실행):

```
.venv/bin/python -m pytest server/tests/test_audio_analyze.py server/tests/test_audio_boundary.py \
    server/tests/test_audio_fallback.py server/tests/test_audio_grade_saturation.py \
    server/tests/test_audio_segment_floor_bars.py -q
........................................................................ [ 67%]
..................................                                       [100%]
106 passed in 7.83s
```

로컬 전용 회귀(원곡 있을 때만, `pytest.mark.skipif` — 이번 세션은 원곡 존재해
PASS로 실행됨, CI에서는 자동 skip): `test_real_love_attack_extraction_reproduces_volume_and_achieves_ac007` —
음량(`volume_norm`)은 지도 보고서 부록 A 수치와 ±0.05 절대오차 안에서 재현됐다
(82개 마디 전부, RMS 방법론이 `analyze.py`와 같아 거의 정확히 일치 — 실측 예:
14마디 보고서 0.74 vs 추출 0.739, 33마디 보고서 1.07 vs 추출 1.069). 전체
파이프라인(`detect_beat_grid` → `derive_bars` → `extract_bar_features` →
`classify_bar_events`)은 실제 오디오에서도 AC-007 7/7을 재현했다. 62개 테스트
안에 포함되어 위 출력에 이미 들어 있다.

**Gaps(미검증, 정직하게 기록)**:
- **저역·보컬 대역의 절대 수치는 지도 보고서의 비공개 파이프라인을 재현하지
  않는다.** 지도 보고서의 "저역 타악 에너지"·"보컬 대역 비율"은
  `measure_music_map.py`(이 저장소에 없음 — t505/t509 비커밋 개발 도구)가 낸
  값이다. 이 모듈은 같은 **개념**(타악 성분 저역 에너지, 화성 성분의 보컬 대역
  비중)을 `librosa.decompose.hpss`로 독자 구현했는데, 분리 정밀도가 달라 절대
  분리 폭이 더 좁다 — 실측: 큰 히트(18마디) 저역 배수가 보고서는 4.42배인데
  이 모듈의 실제 오디오 추출은 2.633배, 킥 멈춤(33마디)은 보고서 0.25배 vs
  이 모듈 0.6배. **방향은 맞지만(큰 히트는 높게, 킥 멈춤은 낮게) 절대 수치는
  다르다** — 그래서 분류 문턱도 보고서 수치(2.5·0.35)를 그대로 쓰지 않고
  두 입력 경로 모두에서 7/7이 나오는 값(2.0·0.45)으로 조정했다(위 "과적합
  가드" 참조). 순수 저역(타악 분리 없는 raw STFT)으로는 큰 히트·킥 멈춤의
  대비가 거의 사라진다는 것도 실측으로 확인했다(초안 시도, 기록 폐기 — 이
  모듈에는 반영 안 함).
- **드롭(참고 지표)은 실제 오디오 경로에서 0건 검출됐다.** 보고서 수치 경로
  (①)에서는 정확히 63~66마디로 재현되지만, 실제 오디오 경로(②)의
  `vocal_band_ratio`(화성 성분 합 기반 비율, 0.17~0.54 관측 범위)는 보고서의
  원시 비율 척도(0.03~0.75 관측 범위)와 분포가 달라, 같은 문턱(≤0.15)으로는
  63~66마디를 가려내지 못한다. 드롭은 AC-LDBARMAP-007의 7개 사건에 들지 않고
  REQ-LDBARMAP-009가 "추정" 등급을 PASS 판정의 유일한 근거로 쓰지 말라고
  명시하므로 **PASS 판정에는 영향이 없지만**, "드롭 검출기로 실전에 쓸 수
  있는가"라는 질문에는 솔직히 **아니오**다 — 별도 보정이 필요한 follow-up.
- **`onset_count`는 보고서 수치 경로(①)에서 재지 못한다.** 부록 A 표에는
  온셋 개수 열이 없다 — ①에서는 `onset_count=None`으로 두고 브레이크 판정은
  저역 문턱 하나로만 돈다(그래도 7/7). 두 경로가 ①은 저역만, ②는 저역+온셋을
  쓴다는 뜻이라, "두 경로 모두 같은 로직"이라는 주장은 저역 쪽 로직에만
  해당한다 — 온셋 보조 신호는 ②(실제 오디오)에서만 작동을 확인했다.
- **킥 진입 문턱의 실제 오디오 경로 여유 폭이 테스트 범위(±20%) 밖에서는
  좁다.** 18마디 저역 배수(실측 2.633)가 기준값(2.0) 대비 +32%(2.64) 근방에서
  이 마디가 빠지기 시작한다(위 민감도 표 참조) — 테스트가 검증하는 ±20%
  범위 안에서는 견고하지만, 더 멀리 흔들면 지식의 날에 더 가까워진다.
- **빌드업 anchoring은 "큰 히트가 있어야" 작동한다.** 큰 히트(킥 진입) 없이
  일어나는 빌드업은(이 곡엔 없음, REQ-008의 build 정의 자체가 "히트로
  이어지는 상승") 이 분류기로는 못 잡는다 — 설계상 의도된 범위이지 결함은
  아니다.
- **다른 곡·다른 박자로 일반화를 시험하지 않았다**(spec.md §5 열린 결정 3과
  같은 경계, M1·M2 Gaps와 동일한 한계).

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
