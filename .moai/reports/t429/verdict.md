# t429 판정 — 후렴 반복 곡의 큐 0개 회귀가 PR #475 이후 풀렸는가

- 카드: t429 (클래스 B, run→sync)
- 판정: **PASS — 분석 가능한 8곡 전부 풀림.** 코드 수정 없음, 닫기 근거만 제출.
- 기준 커밋: `7a5432a7` (origin/main, PR #477 머지 시점 — #475 `7447ca55`, #476 `b661da2d` 포함)
- 대조군 커밋: `9dd21171` (#475 직전)
- 측정일: 2026-09-23, 브랜치 `WT-chorus-8song-check`, 워크트리 `.claude/worktrees/t429`

## 무엇을 쟀나

업로드 경로의 실제 순서를 그대로 탔다: 오디오 바이트 → `server.audio.analyze.analyze` (DSP) →
확정 기록(`ConfirmedSongAnalysis`, 모든 구간 채택, 라벨은 `section_label`) →
`build_toolset(...).dispatch("prepare_songcue")`. 룩 라이브러리는 실제 `load_library_from_dir()`,
리그는 `LXSEQ_RIG` 그룹, 콘솔은 가짜 실행/상태 포트(콘솔 접촉 0건). 타임코드 7번(가짜 트리 기본 점유 1·3 회피).

곡마다 장르 2개(`rock`, `edm`) × 이름 2갈래:

- **A_default**: `section_names` 없음 → 확정 기본 이름 `S<n>`
- **B_chorus**: `section_names` = `pilot_baseline.json` 의 회차별 라벨(`Chorus 1`, `Chorus 2` …) — #475 가 고친 결함 형상. 8곡 모두 구간 수가 일치해 대체 이름 없이 baseline 이름을 그대로 썼다.

명령:

```
.venv/bin/python .moai/reports/t429/probe_upload_path.py <트리> <출력.json>
```

## 결과 (HEAD `7a5432a7`) — 32/32 OK

| 곡 | BPM | 구간 | 코러스 라벨 | rock A | rock B | edm A | edm B |
|---|---|---|---|---|---|---|---|
| Club Diver.mp3 | 139.7 | 13 | 9 | 7 | 7 | 9 | 9 |
| Cut and Run.mp3 | 107.7 | 17 | 10 | 10 | 10 | 12 | 12 |
| Ice cream.mp3 | 100.4 | 7 | 2 | 7 | 7 | 7 | 7 |
| Morning.mp3 | 117.5 | 13 | 8 | 7 | 7 | 9 | 9 |
| Rain.mp3 | 76.0 | 12 | 6 | 9 | 9 | 10 | 10 |
| Too Cool.mp3 | 161.5 | 23 | 13 | 12 | 13 | 14 | 15 |
| scott-buckley-neon.mp3 | 120.2 | 17 | 6 | 14 | 14 | 13 | 16 |
| 걸그룹DinoDino_C_max최고품질.wav | 126.0 | 9 | 1 | 10 | 10 | 9 | 9 |

칸의 숫자 = 생성 큐 수(`report.generated_cues`). 모든 칸에서 `Store Sequence` 명령 수가 큐 수와 같았다. 예외 0건, 오류 0건.
원자료: `head_7a5432a7.json` / `head_7a5432a7.txt`.

## 대조군 (`9dd21171`, #475 직전) — 32/32 ERR

같은 프로브, 같은 곡, 같은 인자로 옛 트리(`git archive 9dd21171 server`)를 쐈다. 32칸 전부
`song cue list cannot be built: movement_line_collision`, `Store Sequence` 0건 = 카드가 말한 「큐 0개」.
이 프로브가 결함을 잡을 수 있다는 증거다. 원자료: `control_9dd21171.json` / `control_9dd21171.txt`.

참고: 옛 트리에서는 이름이 전부 다른 A_default 갈래와 코러스 1개짜리 DinoDino 도 실패했다 — 라벨이 겹치지 않으면 모든 구간이 1회차로 세어진다는 #475 원인 진단과 맞는다.

## 분석 단계에서 거부된 2곡 — 이 카드 범위 밖

| 곡 | 거부 사유(앱 메시지 원문 요약) |
|---|---|
| LoveMe.mp3 | 형식을 읽지 못함 — `Format not recognised` (카드 t413 로 알려진 건) |
| Let's Dance.mp3 | **디코더가 91.0초에서 멈춤, 파일은 140.5초** — 부분 분석 거부 |

`Let's Dance.mp3` 거부는 배차서에 없던 사실이다. 앱이 의도한 대로 거부한 것(잘린 분석 금지)이며
`prepare_songcue` 까지 가지 못하므로 t429 판정에 들어가지 않는다. 카드 필요 여부는 리드 판단.

## 함께 돌린 테스트

```
.venv/bin/python -m pytest -q server/tests/test_songcue_t429_repeat_chorus_collision.py server/tests/test_songcue_bpm_production_wiring.py
4 passed, 1 warning in 2.45s
```

전체 스위트는 돌리지 않았다(레인 검증은 카드 범위만; 코드 변경 없음).

## 안 잰 것

- 실기 콘솔: 가짜 포트만 썼다. 콘솔로 실제 저장되는지는 재지 않았다.
- 운영자가 확정 카드에서 일부 구간을 **빼는** 경우: 전부 채택만 쐈다.
- 장르 단어 `rock`/`edm` 외(예: `록`, `발라드`)는 안 쐈다.
- 큐 수가 구간 수보다 적은 칸(예: Club Diver rock 13구간→7큐)이 있다. 이것이 정상 병합인지는 이 카드에서 판정하지 않았다 — t429 결함은 「0개」였고 모든 칸이 0보다 크다.
