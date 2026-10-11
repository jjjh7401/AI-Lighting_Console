# t566 plan 판정서 — SPEC-LDBEAT-001 0.4.1 → 0.5.0 묶음 개정

- 카드: t566 (+ t556 · t564 함께 닫음, t555 수정 반영)
- 브랜치: `WT-spec-entry-wording` (작업 트리 `.claude/worktrees/t566`), 기준 `b961cc9e`
- 작성: manager-spec (본문), 리드 규칙: 옛 REQ/AC 삭제 0 · 정본 = `design/` 시안 · 코드 0
- 판정: **델타 plan-audit 2회차 PASS (0.97)** — `.moai/reports/t566/plan-audit-delta-2.md`

## 1. 무엇이 바뀌었나

| 묶음 | 내용 | 자리 |
|---|---|---|
| ① t566 | 전환 `entry` 를 시안 필드만큼 넓힘 — `fade_beats`(박, `fade_bars` 와 배타), `trigger_beat`(1..마디당 박 수), `delay_beats`([미확인] 유지), `position_late_beats`(⚠미확인 유지), `tracking`(Track/Cue Only/Block/Release 닫힌 집합, 기존 `cue_sheet_edit.TRACKING_VALUES` 재사용). 음악 단위만, 초 저장 금지, 마디당 박 수는 곡 박자표에서(4 하드코딩 금지). 「모두 1박 페이드」 저장 가능 | REQ-006 (i-4a)~(i-4f), REQ-020(e), AC-020 (f)~(k), plan.md M9 step 3 선행 조건 + §F 안티패턴 1건 |
| ② t556 | (a) 번호대 밖 = `preset_pools.yaml` `confirmed:false` 동안 경고, `true` 면 거절 (b) 번호대 출처 = 지금은 `preset_pools.yaml`(데이터 파일), 쇼 파일 판독은 목표 — §5 항목 11 신설 (c) 「프리셋 번호 전부 null」 → 「non-null 이면 source_ref 또는 완전한 evidence.approval」(33칸 중 12칸 non-null, 전부 승인 있음) | AC-016(a)(e), AC-025(d), REQ-015(f) 근거, spec.md §5 |
| ③ t564 | REQ-023 근거: 「이 마디 한눈에」 표는 2칼럼이었다(구현 아님). 줄 번호 대신 심볼 인용 | REQ-023 근거 |
| ④ t555 반영 | 새 프리셋 번호는 **같은 변경**에 함께 온 `evidence.approval` 만 인정(커밋 `0a947e72`) | REQ-015(h), AC-016(v) |

- REQ 25 · AC 25 그대로(Tier L 상한), 새 ID 0, 코드 diff 0.
- 바뀐 옛 문장은 지우지 않고 「(대체됨 — 카드 t566, 옛 문면: 「…」)」로 남겼다.
- 버전 0.5.0, HISTORY 1행, design.md 각주 1개, progress.md 계획 단계 기록 2줄.

## 2. 진행 경과 (실패를 포함해 그대로)

1. manager-spec 1차 작성.
2. **오케스트레이터 검산에서 결함 발견** — 조항 표지는 다 남았지만 옛 문장 14개가 덮어써져 사라졌다(`dropped_text_check-1-before-fix.txt`: spec.md 3 · acceptance.md 11). manager-spec 에 되살리기 지시 → `dropped_text_check-2.txt` 0/0.
3. 델타 plan-audit 1회차 **FAIL (0.94)** — D1(치명) REQ-020(e) 새 문장에 GEARS 트리거 없음, D2(사소) REQ-023 줄 번호 낡음, D3(사소) 검사 산출물이 고치기 전 기록. (`plan-audit-delta-1.md`)
4. D1·D2 → manager-spec. 재검토 중 같은 종류 결함 1건을 스스로 더 찾아 고침(REQ-006(i-4a) 둘째 문장). D3 → 오케스트레이터가 고치기 전 파일 이름에 `-before-fix` 표시(내용은 안 고침).
5. 델타 plan-audit 2회차 **PASS (0.97)**. (`plan-audit-delta-2.md`)

## 3. 증거 (이 트리)

| 명령 | 결과 | 파일 |
|---|---|---|
| `python3 .moai/reports/t566/dropped_text_check.py <옛 파일 폴더>` | spec.md · acceptance.md 모두 `합계 사라진 문장: 0` | `dropped_text_check-3.txt` |
| `grep -c '^\| REQ-LDBEAT-' spec.md` / `grep -c '^\| AC-LDBEAT-' acceptance.md` | `25` / `25` | — |
| `python3 .moai/reports/t566/sweep_016_025.py` | `REQ-LDBEAT-016~025 합계 shall 부재 문장: 0` | — |
| `git status --short` (커밋 전) | SPEC-LDBEAT-001 다섯 파일 + `.moai/reports/t566/` 뿐 | — |

감사관은 저자 스크립트를 믿지 않고 바뀐 조항 전부(REQ-006 (i-4a)~(i-4f), REQ-015(h), REQ-020(e), AC-020 (f)~(k), AC-016(v))를 손으로 다시 봤고, 사실 주장(12칸·승인, `confirmed:false`, `beat_grid_edit.py:465-469`, `TRACKING_VALUES`, `parseBeatsPerBar`, t560 머지)을 저장소와 대조했다.

## 4. 안 잰 것 · 남은 것

- **D4(감사 2회차, 사소·선택)**: 점검 스크립트 `sweep_016_025.py` 의 한계 — 마침표로만 나눠 대시(—)로 이은 절을 덜 쪼개고, `range(16, 26)` 이라 REQ-006·015 는 아예 안 본다. 그래서 그 「0」은 REQ-006(i-4a) 수정의 증거가 아니다(그건 감사관 손 검토가 증거). SPEC 결함은 아니라 이 카드에서 고치지 않았다.
- **코드 0**: ① 의 저장·검증·편집 배선(`_validate_entry`, `BeatGridEntry`, 전환 화면 비활성 컨트롤 활성화)은 머지 뒤 새 run 카드 몫이다. AC-020 (f)~(k) 는 「미구현 — run 뒤 재검증」으로 표시돼 있다.
- **t556 ④(코드 꼬리)**: `BeatGrid.tsx` 의 낡은 주석(「효과·디머 효과는 아직 읽기 전용」)과 호출 안 되는 `isBrightnessValueEditable` — 코드라 손대지 않았다. 별도 코드 카드 감.
- **research.md** 는 고치지 않았다 — t560 머지로 「이 마디 한눈에」가 6칼럼이 된 현실 반영은 sync 몫.
