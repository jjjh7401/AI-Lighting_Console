# SPEC-LDRENDER-001 sync 보고 (카드 t501)

## Claim

1. 송신 함수(`reviewed_song_commands` 및 호출 경로)가 역할별 렌더링·색 배정·효과
   기구 디머 분리·효과 송신 통로·연출 판독 게이트를 구현했고, 기계 판정
   AC-LDRENDER-001~015(acceptance.md 기준) 8곡 전부 PASS 했다.
2. 실기 콘솔(Rain 시퀀스 212, Club Diver 시퀀스 213)에 반영해 구조적으로
   동작함을 확인했으나, AC-LDRENDER-016(사람 판정)은 **1~2점/5점**(통과선
   3점)으로 **FAIL** 했다.
3. SPEC 상태는 `completed` 가 아니라 `implemented` 로 전이한다(DoD 1행 미충족).

## Evidence

- `.moai/specs/SPEC-LDRENDER-001/progress.md` §E.2 M1~M7 각 마일스톤 절 —
  테스트 명령·결과 원문, 측정 스크립트 산출물 경로.
- `.moai/reports/t501/measure_m7_dsp_8songs.py` → `measure_m7_dsp_8songs.json`
  — 실제 음원 DSP 경로, 8곡 전수: 색 수 2~3·색변화≥1·LIT<3 위반 0/120·
  비액센트 effect 위반 0/122·액센트 상승 8/8·fx 요청곡 7/8 송신≥1.
- `uv run pytest server/tests -q -p no:cacheprovider` (M7 커밋 시점, progress.md
  인용) → `14539 passed, 35 skipped, 1 warning` — 베이스라인 `14522 passed`
  대비 +17, 0 regressed.
- `.moai/reports/t501/ac016/` — `real_song.py`(전부-거절 리허설)·
  `verb_summary.py`(동사 요약: Store 14/15·Assign 1·Delete/Overwrite/
  SaveShow 0)·`postwrite_cue_props_probe.py`(되읽기: 212 큐 13개·213 큐
  14개, 이름/트리거 일치)·`c1_before_after_diff.txt`(기존 항목 변화 0,
  추가 4건만). 감독 판정 원문은 progress.md "AC-016 실기 준비·쓰기" 절에
  전사됨.
- `grep -c LDRENDER CHANGELOG.md`(sync 착수 전) → `0` — 중복 없음 확인 후
  작성.
- `grep -oE 'AC-([A-Z0-9]+-)*[0-9]+' .moai/specs/SPEC-LDRENDER-001/acceptance.md
  | sort -u | wc -l` → `32`(짧은형 16 + 긴형 16, 동일 16개 AC 의 이중 표기).
- `server/orchestrator/tools.py:3480-3492` — 업로드 경로 주석과 코드:
  `gate_cues = gate_cues_from_commands(cue_commands, bundle.cues,
  layer_mapping=())` — `layer_mapping=()` 하드코딩, 주석이 "이 경로는
  (아직) 층 매핑 확인 UX 가 없다"를 명시.

## Baseline-attribution

- `git log -1 --oneline` → 이 sync 커밋 자신(아래 보고 참조) — 직전 HEAD
  `50c11ccf`(run 브랜치 `c7b231cd` + manager-spec 문면 정렬 1커밋).
- `git diff --stat origin/main...HEAD -- '*.py' 'docs/proposals/*'` →
  51 files changed, 7634 insertions(+), 123 deletions(-) — 이 SPEC 의 run-phase
  전체 diff(M2~M7). 핵심 변경 파일: `server/design/rig.py`,
  `server/design/song_cue_composer.py`, `server/design/song_cue_render.py`,
  `server/design/ldrender_gate.py`(신설), `server/design/phaser_pregen.py`
  (신설), `server/design/capability_verdict.py`, `server/fx/instantiate.py`,
  `server/fx/schema.py`, `server/web/session.py`, `server/orchestrator/tools.py`,
  `docs/proposals/song-lighting-design-standard.md`.
- `acceptance.md` Definition of Done 1행(사람 판정 AC-016 을 run-phase 종료
  조건으로 명시) — 이 문구를 `completed`/`implemented` 분기의 근거로 썼다.

## Gaps (명시 — 미검증)

- **R5/R6 디머 대역 이월**(이 SPEC 범위 밖) — progress.md "AC-016 실기
  준비·쓰기" 절 "이월" 항목.
- **Rain: 효과 요청 0건 → 송신 효과 줄 0건**(게이트 경고 「효과 요청 0건 ·
  페이저 제안 11큐 → 송신 효과 줄 0」) — Rain 용으로 만든 페이저 5개(Wave
  CM/Breathe Cool/Breathe Warm/Drop Slam/Finale Slam)는 Rain 실기에서
  **불리지 않는다**(설계 층 D레벨 예산이 그 제안을 요청으로 승격한 적이
  없음 — Rain 자신의 곡 특성, M7/M6 결함 아님).
- **Finale 블라인더 근거 부재**(`blinder_six_row_absent`, P9) — 그대로
  이월.
- **업로드 경로의 `layer_mapping` 부재** — `server/orchestrator/
  tools.py:3480-3492` 확인: `gate_cues_from_commands(cue_commands,
  bundle.cues, layer_mapping=())` 로 하드코딩되어 있고, 주석이 "아직 층
  매핑 확인 UX 가 없다"를 명시한다. 이 경로(업로드 길)는 다중 역할
  렌더링을 받지 못하므로 LIT 축 경고가 구조적으로 거의 항상 발동한다 —
  M7 §1 주석이 이것을 "정확한 신호(거짓 경보 아님)"로 읽는다. **대화
  경로(`session.py` `_song_finalize`)는 `state.layer_mapping` 을 그대로
  넘기므로 이 공백이 없다** — 공백은 업로드 길에만 있다.
- **`last-wins` 가정 미검증** — M3/M4/M5 공통 트래킹 가정(콘솔이 뒤에 온
  역할 줄을 이긴다)이 실기에서 성립하는지 — AC-016 실기 세션이 이것을
  별도로 확인하지 않았다(progress.md "안 잰 것" 항목).
  복합 줄 페이저 스텝이 무대에서 의도대로 바뀌어 보이는지도 동일하게
  미확인.
- **효과 기구가 여전히 색/포지션/페이저 줄에 포함됨**(디머만 0 처리) —
  AC-LDRENDER-006 이 명시 축소한 PASS 조건대로, 공유 `fids` 는 effect
  기구를 포함한 86대 전체다. 이는 결함이 아니라 REQ-007 의 명시된 범위 밖
  잔여로 문서화됐다(2026-10-03 spec.md HISTORY 정렬).
- **AC-LDRENDER-016(음악적 리듬·비트 표현) — FAIL**: 감독 판정 1~2점/5점
  (통과선 3점, 2026-10-03). 판정 원문: 「작동은 한다. 그러나 Verse 하나가
  20~30초 이상 단조로운 동작·연출 하나 — 리듬·비트에 따라 빠르고 다채롭게
  움직여야 음악 표현이 된다」. 구조 복원(색·층·효과 통로)은 실기 동작을
  확인했으나 음악 표현은 미달 — 후속 리듬 SPEC(카드 t502)으로 이월한다.
- **AC-LDRENDER-015(t498 회귀 스위트)** — M7 §Gaps 가 t498 전용 재현
  스크립트 재실행을 기록하지 않았다. 전체 pytest 회귀(+17, 0 regressed)는
  대체 증거가 아니라 일반 회귀 신호일 뿐이므로 §E.4 AC 탈리에서 "불기록"
  으로 둔다(PASS 로 발명하지 않음).

## Residual-risk

- M6/M6c §잔여 위험이 그대로 상속: 프리셋 풀 스냅샷 노화, 번호 할당
  경쟁조건, `group=1` 일반화 미검증 — 실제 송신 시점 재조회가 필요하다는
  경고는 유효하다.
- `;`-체인 압축 폼(스텝 값 줄)의 실기 동작은 **같은 콘솔 명령 그래머의
  추론**(M6c §Gaps)이며 직접 측정이 아니다 — 실기로 반증되면 M6c 처방 전체
  재검토 필요.
- `completed`/`implemented` 분기는 이 sync 세션의 판단이다 — acceptance.md
  DoD 1행이 AC-016 을 run-phase 종료 조건으로 명시한다는 문면 해석에
  근거했으나, 리드가 다른 해석(음악 표현은 설계 의도 밖이므로 AC-016 의
  "통과를 전제로 한 종료"가 아니라 "별도 후속 SPEC 분리로 종료"가 맞다)을
  가질 경우 재조정이 필요할 수 있다.

---

**종결**: 구조 복원 · 실기 감독 판정 1~2점 미달 · 리듬은 t502.
