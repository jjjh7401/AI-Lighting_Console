# t510 판정서 — LOVE ATTACK 기존 앱 연출 기준선 (가짜 콘솔, 콘솔 접촉 0, 제품 코드 0)

- 카드: t510 · 브랜치 `WT-loveattack-base` · 워크트리 `.claude/worktrees/t510`
- base: `origin/main` `e7eaf690` (`git merge-base --is-ancestor e7eaf690 HEAD` 성공)
- 산출물: `reports/loveattack-baseline-20261006.{md,html}`
- 음원: `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3` — 저장소 밖, 커밋 안 함

## 판정: 카드 산출물 전부 냈다 (조사 카드 — PASS/FAIL 걸린 AC 없음)

| 카드 요구 | 결과 | 근거 |
|---|---|---|
| main 앱 경로로 큐·송신 명령 생성 | 11큐 · 송신 190줄, exit 0 | `run1/console_commands_sent.txt`, `run1.stdout.txt` |
| 인터뷰 고정 답 기록 | t498/t499 와 같은 7답 + 매핑 + 승인, 카드 9장 | `run1/cards.json`, 보고서 §1 |
| 큐별 시각·유지·색·층·페이저·속도·강조 | 표 11행 | `hold_table.md` / `hold_table.json` |
| t499 readout.py 판독 | 복사본으로 판독(묶음 그룹 펼침만 추가) | `readout_run1.txt`, `run1/readout.json` |
| t502 hold_durations 와 같은 표 | Rain·Club Diver 와 나란히 | 보고서 §3 |
| md·html | 둘 다 | `reports/loveattack-baseline-20261006.{md,html}` |

## 측정 기록 (MEASURED)

| # | 주장 | 명령 | 출력(요지) |
|---|---|---|---|
| M1 | 앱 경로 끝까지 실행 | `uv run python .moai/reports/t510/rehearse_song.py "<음원>" .moai/reports/t510/run1` | exit 0 · `commands=190 approvals=1 cards=9 events=7` |
| M2 | 승인 = 송신 | `cmp run1/console_commands_approved.txt run1/console_commands_sent.txt` | 출력 없음(동일), 각 190줄 |
| M3 | 결정성 | 같은 명령 run2 → `cmp` 7개 파일 | 전부 동일 — `determinism.txt` |
| M4 | 곡 분석 | `run1/analysis.json` · `ffprobe … duration` | BPM 112.347(measured) · 구간 10 · 마지막 끝 197161ms · ffprobe 197.160635s |
| M5 | 큐 표·유지 시간 | `python3 .moai/reports/t510/hold_table.py` | n=10 max 34.2s median 14.9s ≥20s 3 ≥10s 8 · speed/BPM 줄 0 · 풀 2 밖 `At Preset` 줄 0 |
| M6 | 판독·위반 | `uv run python .moai/reports/t510/readout.py .moai/reports/t510/run1` | exit 0 · 위반 5건(§6 밝기 2 · §6 색 2 · §6 효과 1) · 전 큐 무대 층 5 |
| M7 | 페이저 미배정 고지 | `grep -o "페이저 미배정…" run1/replies.json` | Breathe Warm · Wave CM · Finale Slam 「콘솔에서 찾지 못했습니다」 · 「효과: 요청 9 · 허용 0 · 송신 0」 |
| M8 | 묶음 그룹 펼침 크기 | `readout.members()` | SIDE-ALL 12 · WASH-ALL 20 · MOVER-ALL 16 (BACK 12 · FOH 8 · BLIND 6) |
| M9 | 음원 미포함 | `run1/events.json` 이벤트 7개 타입·크기 나열, `ID3`/base64 머리 grep | 오디오 데이터 0 (최대 이벤트는 execution_preview 64KB) |

## t499 판독기에서 바꾼 것 (복사본 `readout.py`)

t499 원본은 SIDE-ALL·WASH-ALL·MOVER-ALL 을 만나면 「규칙을 만들어라」로 멈춘다(설계대로). LDRENDER-001 송신이 그 세 그룹을 쓰므로 실제로 멈췄다(`Group 7 'SIDE-ALL': 이름 첫 단어로 펼칠 기구가 없다`). 복사본에 펼침 규칙(SIDE-ALL = SIDE-L ∪ SIDE-R 등)만 넣었다 — 이름 첫 단어 기반이라 **추정**(t499 와 같은 갈래). 원본(t499 폴더)은 손대지 않았다. 판독기 양성 대조(줄 하나 끼워 숫자가 움직이는지)는 이번에 다시 하지 않았다 — t499 `control_readout.txt` 4팔이 원본 로직의 대조이고, 추가한 것은 펼침 표뿐이다(M8 로 크기만 확인).

## INFERRED (재지 않은 판단)

- 후렴 하나 ≈ 15~16마디(앱 BPM 112.35 기준). BPM 반/두 배 오검출 여부는 안 쟀다
- 구간 이름(Verse·Chorus)이 곡의 실제 구조와 맞는지 — 앱이 D 레벨로 붙인 이름, 대조 안 함
- 그룹 구성원(이름 첫 단어)

## 안 잰 것 (GAPS)

- 🔴 **실기 페이저**: 가짜 콘솔은 페이저 풀(`DataPool/PresetPools`)에 답하지 않아 페이저 줄 0. 실기 Club Diver(t501, 시퀀스 213)는 `At Preset 4.9` 등 페이저 호출 11개가 나갔다(t502 M2). LOVE ATTACK 실기 송신에서는 페이저 줄이 0이 아닐 수 있다
- 실기 W 줄 · 기구 좌표(지어낸 값) · 육안
- html 은 브라우저로 열었지만(`open`) 화면을 캡처해 눈으로 확인하지 못했다(헤드리스 크롬 호출이 워크트리 가드에 막힘) — 렌더러는 md 표를 그대로 옮기고 SVG 타임라인 하나를 더할 뿐이다
- 다른 인터뷰 답에서의 결과

## 콘솔 · 코드

- 콘솔 접촉 **0**: 모든 명령은 in-process `FakeConsole`(`server/tests/test_safety_gate.py`)이 받았다
- 제품 코드 변경 **0**: `server/`·`src/`·`ui/` 변경 없음. 추가 파일은 `.moai/reports/t510/` 와 `reports/loveattack-baseline-20261006.{md,html}` 뿐
