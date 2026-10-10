# t547 판정 — SPEC-LDBARMAP-001 REQ-LDBARMAP-006 반/두배 검사 재설계 (plan 단계)

- 카드: t547 · 브랜치 `WT-barmap-halfdouble` · 기준 `origin/main` 9c9b1767
- 범위: SPEC 문서만(`.moai/specs/SPEC-LDBARMAP-001/` 5개 파일). `server/`·`tools/` 변경 0, 콘솔 쓰기 0.
- 상태: **plan-audit PASS(2차, 0.923)** → **감독 승인 대기**. run 은 승인 뒤.

## 판정

| 항목 | 결과 | 근거 |
|---|---|---|
| plan-audit 1차 | FAIL 0.667 (필수 항목 7개 전부 통과, 점수 미달) | `plan-audit.md` — D1·D2: AC-004b/d 의 합성 시험 설명이 실제 렌더와 달랐다 |
| plan-audit 2차 | **PASS 0.923** | `plan-audit.md` Iteration 2 — D1·D2 해소, 새 불일치 0 |
| REQ/AC 개수 | 16/16 → 16/16 | 감사가 grep 으로 다시 셈 |
| 남은 결함 | D3·D4(경미, 선택), D5(주요, 선택 — run 에서 처리) | 아래 「run 에 넘기는 것」 |

## 무엇이 틀렸었나 (실측)

지금 검사(`server/audio/bar_map.py::_check_bpm_half_double`)에는 결함이 두 겹 있다.

1. **고정 격자가 BPM 오차에 무너진다.** 곡 전체에 격자 한 장을 깔고 온셋 적중률을 잰다. BPM 이 0.3% 만 틀려도 곡 끝에서 격자가 한 박쯤 밀려 점수가 우연 수준(0.27~0.33)으로 떨어진다. 그래서 옛 BPM(중앙값)에서는 10곡 모두 발동하지 않았다. 같은 LOVE ATTACK 이 112.347 BPM 에서는 0.29, 112.002 BPM 에서는 0.61 이다 (`probe_songs.txt`).
2. **촘촘한 격자일수록 점수가 구조적으로 높다.** BPM 이 정확해지자 두 배 격자가 8분음표 하이햇까지 잡아 10곡 중 3곡을 거짓 두 배로 뒤집었다. LOVE ATTACK 112→224, Let's Dance 120→240, LoveMe 100→200 (`probe_songs.txt` adopt@reg 열). LOVE ATTACK 의 정답은 112.35 다.
3. 두 문턱(절반 0.05, 두 배 0.20)은 근거 없이 손으로 고른 값이었다.

## 새 판정식 (REQ-LDBARMAP-006 재작성)

- 고정 격자 대신 **박 추적기가 찾은 박 시각 자체**를 기준으로 쓴다. 그래서 BPM 정확도에 기대지 않는다.
- 두 배 후보: 박 자리 세기와 이웃 박 사이 중간점의 세기를 박마다 짝지어 비교한다(단측 부호 검정, α=0.01).
  - p < α → 원래 BPM 유지(keep)
  - p ≥ α 이고 중간점이 더 센 쌍의 비율 w_mid ≥ 0.5 → 두 배 채택(adopt_double)
  - 그 밖 → 원래 BPM 유지 + `ambiguous`(사람 확인으로 넘김)
- 절반 후보: **자동 채택하지 않는다.** 짝/홀 박 비교로는 "추적기가 두 배로 잡음"과 평범한 킥/스네어 강세를 가를 수 없다. 실제 10곡 중 6곡, 그리고 합성한 참 절반 사례와 정상 킥/스네어 사례 모두가 유의하게 나온다 (`probe_sign.txt`·`probe_synth.txt`). 진단값만 기록하고 판단은 감독 BPM 확인 카드에 맡긴다.
- 문턱의 출처: α=0.01 은 통계 관행 상수이고, 0.5 는 대칭점이다. 10곡도 한 곡도 문턱을 고르는 데 쓰지 않았다(감독 원칙). 실제 곡은 대조군으로만 썼다.

## 새 판정식의 실측 행동

| 대상 | 결과 | 출처 |
|---|---|---|
| 실제 10곡(정확한 BPM) | 10곡 모두 keep (p_mid 최대 9.37e-04 = Ice cream, n=122) → 거짓 두 배 3곡이 사라진다 | `probe_sign.txt` |
| 합성 참 224(112 로 추적됨) | adopt_double (w_mid 0.54, p 0.845) | `probe_synth.txt` |
| 합성 참 240(120 으로 추적됨) | adopt_double (w_mid 0.62, p 0.999) | `probe_synth.txt` |
| 합성 112 + 8분 하이햇 0.3 | keep (p 9e-12) | `probe_synth.txt` |
| 합성 112 킥/스네어 + 8분 0.3 | keep (p 2.6e-6) | `probe_synth.txt` |
| 합성 112 + 센 8분 하이햇 0.7 | keep + ambiguous (w_mid 0.46, p 0.195) — 설계가 인정하는 한계 | `probe_synth.txt` |

## run 에 넘기는 것 (감독 승인 뒤)

- `_check_bpm_half_double`·`BpmCandidateCheck` 를 새 판정식으로 바꾼다. 시험은 정답 템포를 아는 합성 클릭으로 하고(CI 에서 돈다), 실제 곡은 로컬 대조로만 쓴다.
- **D5**: AC-004d 사례는 판정 경계에 가깝다(w_mid 0.46 vs 0.5). run 의 시험은 렌더 조건(시드, 다른 사례와 난수를 나눠 쓰지 않게 따로 렌더)을 고정하고, 그 신호에서 keep+ambiguous 가 나오는지 확인해야 한다. 경계에서 흔들리면 하이햇 세기를 경계에서 더 먼 값으로 옮긴다. 이것은 시험 자료 선택이지 문턱 조정이 아니다.
- 범위 밖, 후속 카드 후보: `bar_map.detect_beat_grid` 를 중앙값 BPM 에서 회귀 BPM 으로 맞추는 일(t546 에서 갈라 둔 두 경로). 새 판정식은 BPM 정확도에 기대지 않으므로, 갈라 둘 이유가 사라진다.

## 안 잰 것

- 사람이 직접 잰 BPM 과의 대조. 정답을 아는 곡은 LOVE ATTACK 하나와 합성 클릭뿐이다.
- 10곡 밖의 곡과 템포가 바뀌는 곡.
- 새 판정식의 코드 구현. 위 수치는 전부 탐침 스크립트(`probe_*.py`)로 잰 것이다.

## 증거 파일

`probe_songs.py/.txt` · `probe_sign.py/.txt` · `probe_synth.py/.txt` · `plan-audit.md` (모두 이 디렉터리), 앞 카드의 실측 `.moai/reports/t546/`
