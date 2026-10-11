# t579 run 판정 — 실기 미확인 배지·스피드 마스터 안내 (SPEC-LDBEAT-001 M5·M6)

카드: t579 · 브랜치 `WT-unverified-badges` · 기준 origin/main `63de8d95`
범위: REQ-LDBEAT-010(plan.md M5) · REQ-LDBEAT-014(plan.md M6)

## 이미 돼 있던 것 (grep 으로 확인 후 손대지 않음)

- 「⚠ 번호대 미확인」(t551, `presetPoolBandBadge`) · 전환 화면 「[미확인]」 표기(t561/t576) — 그대로 둠.
- 송신 게이트: `app_movement` 칸은 M1 ⑤⑦⑨ 가 「통과」이거나 실측 기록(`measured_movements.yaml`)이 연 칸만 나간다(`beat_grid_emit.blocked_m1_items_for_cue`, t549/t553). 미확인 모양은 이미 콘솔로 안 나간다 — 손대지 않음.
- 「⚠ 실기 미확인」 배지 자체는 있었다(`BeatGrid.tsx`). **문제는 판정 출처**였다.

## 빈 곳과 채운 것

| 빈 곳 | 전 | 후 |
|---|---|---|
| 배지 판정 출처 | 화면이 **라벨 글자**를 상수 목록(`서클·발리후·위상 펼침·circle·ballyhoo`)과 맞춰 봄. 확인 여부와 무관 — M1 이 통과해도 영원히 배지, 라벨에 안 쓰면 circle 칸도 배지 없음 | 서버가 칸의 `app_movement` 를 보고 **M1 표 ⑨(`probe_results`, progress.md 를 서빙마다 새로 읽은 값)** 와 **실측 무빙 기록**으로만 가른 목록 `beat_grid.unverified_cells` 를 보냄. 화면은 그 목록만 읽음 |
| 편집 경고 출처 | 서버 상수 `UNVERIFIED_SHAPES = {circle, ballyhoo}` — M1 무관 | 같은 판정 함수(`beat_grid_unverified.unverified_movement_terms`), 트랙 그룹별로. 상수 제거 |
| 「움직임」 행 배지 | 없음 | 편집 칸 「움직임」 행에도 같은 배지 |
| 곡 기본값 금지(REQ-010 shall not) | 검사 없음 | LOVE ATTACK 기본 격자의 미확인 칸 = 0 을 시험으로 잠금(살아있는 progress.md 기준 + M1 전부 미확인 가정 둘 다). 대조군: circle 칸을 넣으면 잡힘 |
| M6 스피드 마스터 | BPM 알약에 hover title 만 — 눈에 보이는 글자는 「BPM 112.35」뿐이라 앱이 맞춘 값처럼 읽힘 | 알약에 「· 스피드 마스터 — 콘솔에서 직접 설정」을 보이게 붙임(시안 `ldbeat-runbook-mockup-20261008.html` 상단 바 문구에서 리그 번호 15 만 뺌), title 은 「사람이 콘솔에서 직접 설정합니다(자동 설정 방법 미확인)」 |

### 판단 근거 (리드가 뒤집을 수 있게 적음)

- **위상 펼침 ↔ M1 ⑨**: M1 표에 위치 위상 펼침 전용 행이 없다(⑩ 은 디머 위상 — 별개). §6 어휘 행인 ⑨ 에 묶었다.
- **실측 기록도 「확인」 출처로 씀**: 배차는 「M1 상태표에서」였다. 그런데 M1 표만 쓰면 기본 격자 MOVER-D 7마디(wave·Tilt·위상 펼침, t548 D1 실측)가 미확인이 되어 **REQ-010 「기본값으로 제공하지 않는다」를 기존 데이터가 어긴다**. 송신 게이트가 이미 같은 기록으로 이 칸을 연다(t553) — 배지와 송신이 다른 말을 하지 않게 같은 기록을 썼다. 두 출처 모두 데이터 파일이고 코드 상수가 아니다.
- **바뀐 동작 1건**: 옛 화면은 7마디 칸에 라벨 「위상 펼침」 때문에 배지를 달았다(progress.md:254 「캡처에서 MOVER-D 위상 펼침 칸에 배지 실제 렌더」). 이제 그 칸은 실측으로 열려 배지가 없다. progress.md 기록은 고치지 않았다(당시 사실).

## 검증 (이 트리, 커밋 전 작업본 = 63de8d95 + 이 변경)

- `python -m pytest -q server/tests/test_beat_grid_unverified_t579.py` → `21 passed`
- `python -m pytest -q server/tests -k 'beat_grid or architecture or web_session or protocol or ldbeat'` → `987 passed, 14337 deselected`
- 뮤테이션: `_M1_PASS_PREFIX` 를 `"XX"` 로 → `4 failed`; 실측 기록 검사 줄 삭제 → `6 failed`(기본값 0 시험 포함). 둘 다 되돌린 뒤 `21 passed`
- `ruff check server` → `All checks passed!` · `ruff format --check server` → `803 files already formatted`
- `ui: vitest run` → `Test Files 53 passed (53)` / `Tests 1157 passed (1157)`
- `ui: tsc --noEmit -p .` → 출력 없음(오류 0) · `npm run build` → `✓ built in 442ms`
- 살아있는 M1 표(이 트리 progress.md) ⑨ = `wave 움직임 없음 · circle·발리후 미확인` → 「통과」 아님 → circle·발리후·(실측 밖) 위상 펼침은 배지

## 갭

- **전체 pytest 는 로컬에서 안 돌렸다**(레인 규칙 — CI 몫). `-n auto` 시도는 xdist 없음으로 시험 0개 실행 — 그 결과를 통과로 읽지 않는다.
- 실제 브라우저에서 배지·알약 모양을 눈으로 보지 않았다(DOM 시험대 없음, `renderToStaticMarkup` + 소스 구조 시험만).
- 「명시적 선택만 허용」의 **선택 UI**(모양 고르기 목록)는 지금 화면에 없다 — 모양은 AI 제안·문장 경로로만 들어오고, 그 경로는 경고 + 배지를 낸다. 고르기 목록이 생기면 같은 `unverified_cells`/판정 함수를 써야 한다.
- 콘솔 접촉 0건.
