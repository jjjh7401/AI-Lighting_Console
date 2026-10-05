# t505 판정서 — Club Diver 음악 순간 지도 + 비트 검출 실측

- 카드: t505 (리드 배차 2026-10-05, 리듬 SPEC t504 M1 대본 재료)
- 브랜치: `WT-music-map` (워크트리 `.claude/worktrees/t505`), 기준 `origin/main` `c11bc540`
- 성격: 오프라인 측정. 제품 코드 수정 0, 콘솔 접촉 0
- 보고서: `reports/clubdiver-music-map-20261005.{md,html}`
- 확인용 wav(저장소 밖): `/Users/studiox/Music/AI-Lighting_Console-listen/t505/` — 5개, 73 MB

## 1. 카드 항목별 판정

| 항목 | 판정 | 증거 |
|---|---|---|
| ① 마디별 표(구간·마디·시각·다운비트·킥·스네어·필·빌드업·드롭·보컬) | **부분 PASS** | 83마디 표 완성(보고서 부록 A). 구간·마디·시각·다운비트·순간(비트 진입·브레이크 4·재진입 4·끝)은 잰 값에 근거한다. 킥·스네어는 후보만 있고 품질이 낮다(저역 격자 정합 0.28, 우연 0.20). 필·빌드업은 검출 0건이다. 보컬 시작·끝은 미확정 |
| ① 다운비트 추정 방법·근거 | PASS | 근거 네 가지를 따로 쟀다(보고서 §3). 세 근거가 위상 0에 모인다. 신뢰도는 중간이고 귀로 확정해야 한다 |
| ② 클릭 트랙 확인용 wav | PASS | Club Diver 3개(위상 0·위상 3·킥/스네어 후보) + Rain·Too Cool 템포 확인용 2개 |
| ③ 8곡 BPM 절반·두 배 의심 표 | PASS | Rain 두 배(152) 의심, Too Cool 절반(80.75) 의심, 나머지 6곡은 낮음·없음. 참값이 없어 근거만 적었다 |
| ④ 잰 것/추정 구분 | PASS | 보고서 전체에 [잰 값]/[추정]/[미확정] 표기, §6 표 |

## 2. 잰 명령과 출력 (원본: `.moai/reports/t505/evidence/`)

모든 실행은 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.venv/bin/python`(librosa 0.11.0, numpy 2.4.6), 음원은 `src/sample music/`(주 체크아웃, 미추적 파일)이다.

| 명령 | exit | 출력 |
|---|---|---|
| `measure_music_map.py map-phase "<Club Diver.mp3>" .moai/reports/t505/evidence <listen> 0` | 0 | `evidence/clubdiver_map_phase0.json`, `evidence/map_phase0_stdout.txt` |
| 같은 명령, 위상 3 | 0 | `evidence/clubdiver_map_phase3.json`, `evidence/map_phase3_stdout.txt` |
| `measure_music_map.py bpm8 "<sample music>" .moai/reports/t505/evidence` | 0 | `evidence/bpm8_stdout.txt`, `evidence/bpm_doubt.json` |
| `measure_music_map.py listen-double "<Rain.mp3>"` / `"<Too Cool.mp3>"` | 0 / 0 | wav 2개 |
| `diag_beat_phase_profile.py` · `diag_tempo_candidates.py` · `diag_grid_lock.py` (Club Diver) | 0 / 0 / 0 | `evidence/diag_*.txt` |
| `make_table.py evidence/clubdiver_map_phase0.json` | 0 | `evidence/bar_table_phase0.md` (표 + 순간 목록) |
| 2마디 무늬·평평함 (python 한 줄) | 0 | `evidence/two_bar_and_flatness.txt` |
| 첫 실행(임계 0.25, 위상 자동=3) — §3 에서 버린 것 | 0 | `evidence/first_run_threshold025_stdout.txt` |

핵심 출력 원문:

```
app_path_bpm 139.67483108108198 / app_path_confidence 0.9689849461332691 / n_beats 331
downbeat: chroma 61.815/54.693/55.249/60.733 → 0 · snare slots 55/45/43/78 → {0,2}
          lowjump 4/3/3/2 → 0 · boundary-nearest 0/2/0/10 → 3 · chosen 0
MOMENTS 3 비트 진입 · 18 브레이크(깊음, 63%) · 19 재진입 · 34 브레이크(얕음, 82%) · 35 재진입
        50 브레이크(깊음, 64%) · 51 재진입 · 66 브레이크(얕음, 83%) · 67 재진입 · 83 끝
rms odd 0.235 even 0.216 · kickE odd 892 even 1167 · odd>even rms pairs 33 of 36
grid lock(±0.1 beat, chance 0.20): 140 → low 0.28 hi 0.49 perc 0.40 · 94 → 0.23/0.28/0.26 · 70 → 0.23/0.26/0.27
tempo candidates(autocorr): 139.67 0.683 · 93.96 0.681 · 69.84 0.675
```

린트 수정(ruff check/format, 의미 변경 없음) 뒤 위 명령을 전부 다시 돌렸다. JSON·txt 출력 7개와 표·HTML 모두 이전 실행과 바이트가 같았다(`cmp`).

앱 재현 대조: t499 캐시 `.moai/reports/t499/runs/Club Diver/analysis.json`의 `bpm`은 `139.67483108108198`이다. 재측정값과 끝자리까지 같다. 디코드·박 추적 경로가 앱과 같다는 양성 대조다.

## 3. 처음 시도에서 버린 것 (기록)

- 첫 실행(킥·스네어 임계 0.25)에서 킥 후보 892개(박당 2.7개), 박 위 비율 0.33이 나왔다. 사실상 잡음이라 임계를 0.5로 올렸다. 올려도 박 위 비율은 0.32로 같다. 그래서 킥 품질 문제는 임계가 아니라 대역(베이스 라인 혼입)에 있다고 판단했다 [추정].
- 첫 실행의 보컬 판정(마디별 중앙값 임계)은 마디마다 켜졌다 꺼졌다를 반복해 쓸 수 없었다. 4마디 평균으로 다듬은 값은 참고 열로만 남기고, 시작·끝 판정은 미확정으로 돌렸다.
- 첫 실행의 다운비트는 "앱 경계에 가장 가까운 박"(위상 3)을 따랐다. 앱 경계가 박 사이에 있다는 것을 재고 나서 근거에서 뺐다. 위상 3 wav는 대안으로 남겼다.

## 4. 재지 않은 것 (Gaps)

- 다운비트 위상, 킥·스네어 실제 위치, 필 유무, 보컬 시작·끝, Rain·Too Cool 참 BPM: 모두 귀로 확인해야 한다. 이번에 재지 않았다.
- 클릭 wav 자체를 들어 보지 않았다. 길이와 파일 크기만 확인했다(`evidence/listen_wav_length_check.txt`). wav 길이는 디코드한 샘플 수와 같다(Club Diver 6,424,704 = 145.685초 × 44,100). MP3 헤더 선언값과는 0~2,301 샘플(최대 약 0.05초) 차이가 난다. 이는 MP3 길이가 비트레이트 어림값이기 때문이다(analyze.py t443 주석). Rain은 차이가 0이다.
- `reports/music-lighting-benchmark-20261003.md`는 `origin/main`에 없어 읽지 않았다.
- 8곡 중 Club Diver 말고는 마디 지도를 만들지 않았다(카드 범위 밖).
- 다운비트 전용 검출기(madmom 등)는 설치되어 있지 않아 쓰지 않았다. 이번 근거는 librosa 기반 자작 휴리스틱이다.

## 5. 잔여 위험

- 위상 0이 틀리면 표의 마디 번호가 1~3박 밀린다. 다만 16마디 브레이크 위치는 마디 음량에서 나왔으므로 시각(초)은 그대로 쓸 수 있다.
- 앱 박이 실제 타격보다 약 27 ms 늦다(고역 타악 위상 분포). 타임코드 이벤트를 앱 박 시각 그대로 쏘면 이만큼 늦는다.
- 브레이크 판정 임계(85%·70%)는 이 곡 하나로 정했다. 다른 곡에 그대로 쓰면 맞지 않을 수 있다.

## 6. 리드에게

- M1 대본에 바로 쓸 수 있는 것: 비트 진입(3마디), 16마디 브레이크/재진입 네 쌍(깊음·얕음 교대), 2마디 루프, 끝. 그리고 "이 곡에는 빌드업과 음량 대비가 없다"는 사실이다.
- 감독이 들어 줘야 하는 것: wav 5개(보고서 §4 표). 특히 위상 0과 3 중 어느 쪽이 "하나"인지, Rain이 76인지 152인지.
