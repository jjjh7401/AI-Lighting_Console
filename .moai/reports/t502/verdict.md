# t502 판정서 — 리듬 표현 조사(읽기 전용)

- 카드: t502 · 브랜치 `WT-rhythm-research` · 기준 `origin/main` `5220ca4e`
- 산출물: `reports/rhythm-expression-research-20261003.{md,html}`
- 코드 수정 0 · 콘솔 쓰기 0 · 콘솔 읽기 0(t501이 남긴 되읽기 사본만 사용)
- 합격 기준 초안(⑤)은 **감독 확정 대기** 상태다. SPEC에 옮기지 않았다.

## 판정

조사 ①~⑤ 다섯 항목 모두 보고서에 답했다. 이 카드는 조사 산출물만 내는 카드라 PASS/FAIL이 걸린 AC는 없다. 빈칸은 G1·G4·G5·G6·G8·G9가 남았고, G2·G3·G7은 리드 판독 뒤 해소했다(보고서 「안 잰 것」 절).

## 측정 기록 (MEASURED)

| # | 주장 | 명령 | 출력(요지, 원문은 경로) |
|---|---|---|---|
| M1 | 212 큐 13개, 유지 시간 최대 28.5초, 중앙값 16.6초, 20초 이상 4개. 213 큐 14개, 최대 17.1초, 중앙값 10.3초 | `python3 .moai/reports/t502/evidence/hold_durations.py` (exit 0) | `evidence/hold_durations.txt` |
| M2 | 213 송신: 페이저 호출 11(4.9×9, 4.11×1, 21.8×1), speed 줄 0, 위치 프리셋 13, Pan/Tilt 페이저 줄 0 | `grep -ci speed` · `grep -oE "At Preset (4\|21)\.[0-9]+"` · `grep -oE "At Preset 2\.[0-9]+"` · `grep -oE "Attribute '[^']+'"` | `evidence/t501_clubdiver_213_approval_request.txt`. 양성 대조: `At Preset 4.9` 9건 |
| M3 | 212 송신: 페이저 호출 0, speed 0, 위치 프리셋 12 | 같은 명령 | `evidence/t501_rain_212_approval_request.txt` |
| M4 | 저장된 분석 캐시 키는 `sha256, bpm, bpm_source, sections` 뿐. Club Diver 139.67 / Morning 117.45 / Rain 76.01 BPM | `python3 -c "json.load(...)['bpm']"` 등 | 보고서 ①절 인용 |
| M5 | `downbeat` 생산자 0건 | `grep -rln "downbeat" server` | 출력 없음 |
| M6 | `server.fx` 실제 import 6개 파일, 곡 렌더러에는 없음. 간접 경로 `looks/songcue.py:10` → `looks/movement.py:41` | `grep -rnE "^\s*(from server\.fx\|import server\.fx)" server` · `grep -n "^from\|^import" server/looks/songcue.py ...` | 보고서 §2.1 |
| M7 | 곡 송신 경로에 `Speed 30` 리터럴 없음. 옛 증거(t225)에만 있음 | `grep -rn "Speed 30\|CM Speed\|At Speed" server` / `.moai/` | 보고서 §2.1 |
| M8 | 인용한 규칙 원문(§9 312행, REQ-036 212행, REQ-040 216행) 일치. LDRENDER-001 spec status `draft` | `sed -n '312,313p' ...` · `sed -n '212p;216p' ...` · `grep -n "^status"` | 원문 대조 일치 |

## 공식 문서 확인 (DOC, 직접 WebFetch)

- 스피드 마스터 0~225 BPM, 16개, 페이저에 걸 수 있음, 16번은 오디오 BPM — https://help.malighting.com/grandMA3/2.4/HTML/masters_speed.html
- `Master 3.1 At BPM 75`, `At Speed BPM 5` — https://help.malighting.com/grandMA3/2.0/HTML/keyword_bpm.html
- 큐 트리거 Go/Time/Follow/Sound/BPM 원문 — https://help.malighting.com/grandMA3/2.2/HTML/cue_sequence_sheet.html
- 타임코드 내부 시계 구동은 서브에이전트가 가져온 문서다(https://help.malighting.com/grandMA3/2.3/HTML/timecode.html). 직접 다시 읽지는 않았다.

## 리드 판독 반영 (헤드 ba97d0ef 이후)

| # | 주장 | 명령 | 출력(요지) |
|---|---|---|---|
| M9 | 곡 렌더러 밖에 `At Speed` 명령을 만드는 곳이 있다. 생산 줄은 `position_fx.py:160,161,167,176,177`과 `choreography.py:381` | `grep -rn "At Speed" server --include='*.py' \| grep -v server/fx/ \| grep -v test` | 8줄(리드 측정과 같음). 나머지 둘은 주석이다(`looks/schema.py:89`, `scene/report.py:139`) |
| M10 | `position_fx_commands` 호출처는 대화 명령 처리기 하나뿐이다 | `grep -rln "position_fx" server --include='*.py' \| grep -v test` | `session.py`(호출 `:4952` `_position_fx_sequence`), `cue_fade.py`(주석만), `position_fx.py` |
| M11 | `plan_movement` 호출처는 테스트뿐이다 | `grep -rln "plan_movement" server --include='*.py'` | `movement.py`, `tests/test_looks_library.py`, `tests/test_songcue_movement.py` |
| M12 | 곡 렌더러는 큐 묶음에 `movement`를 넘기지 않는다 | `sed -n 1095,1125p server/design/song_cue_render.py` | `SongCueSectionBundle(section=…, cue_number=…, cue_name=…, selection=…, commands=…)`. movement 인자 없음, 기본값 `None`(`songcue.py:206`) |
| M13 | `songcue.py:210` 주석이 가리키는 `_movement_carrier` 함수는 없다 | `grep -rn "_movement_carrier" server` | 주석 1줄뿐 |
| M14 | G3 해소: 단위는 BPM | `grep -rn "Speed display\|BPM/Hz" server/rulebook .moai/specs` | FXLIB `spec.md:64` "Speed 단위는 확정됐다: BPM(ASSUMPTION-38 GO — GUI 표시 판독)", `plan.md:49` "M0로 해소" |
| M15 | G2 해소: `At SpeedMaster <n>` 실기 확인 | `sed -n 35,48p .moai/specs/SPEC-COPILOT-FXGEN-001/spec.md` | V3 [실측 2026-08-15], onPC 2.4.2, 오퍼레이터 GUI 관측 |

룰북 원문 `31_choreography_patterns.md:61`의 절 제목은 "Phasers (running effects) — validated command building"이다. 70행 주석은 단위를 "BPM/Hz/sec per the phaser's Speed display"라고 적어 룰북 안에서는 단위가 미해결이었다. 단위를 확정한 것은 FXLIB M0다.

## INFERRED (재지 않은 판단)

- Rain 76 BPM의 절반/두 배 오검출 가능성
- 권고 순서(BPM 동기 페이저 → 원샷 레인 → 타임코드), 선택지 작업량
- `looks/movement.py` 경로가 곡 송신에서 줄을 만들지 않는 원인

## 바로잡은 것 (서브에이전트 보고 · 배차 전제 · 내 초안)

- 「`server/fx`는 아무 데서도 import하지 않는다」 → 실제로는 6개 파일이 import한다(M6). 곡 렌더러에 직접 import가 없다는 점만 맞았다.
- 「Wave CM Speed 30」(배차 전제) → 곡 송신 경로에 근거 없음(M7). 콘솔에 저장된 값은 재지 않음(G1).
- **내 첫 PR(ba97d0ef)이 빠뜨린 기존 자산**(리드 지적): 실기 검증된 BPM 속도 무빙 페이저(`server/spatial/position_fx.py:145-177`)와 쓰이지 않는 `plan_movement`를 놓쳤다. 그래서 G2·G3를 "실기 확인 필요"로 남겼지만, 둘 다 저장소의 과거 실기 기록(FXGEN V3, FXLIB ASSUMPTION-38)으로 이미 답이 나와 있었다. 원인은 `server/fx`의 import만 셌고 `At Speed`를 만드는 곳을 저장소 전체에서 세지 않은 데 있다. 보고서 §2.1·§2.3(선택지 D 추가, 권고 B+D)·빈칸 표(G2·G3·G7 해소, G9 추가)를 고쳤다.
- **실수로 커밋한 세션 상태 파일 2개**(`evidence/.moai/state/{config-cache,context-usage}.json`): evidence 폴더 안에서 명령을 돌리다 생겼다. 삭제했다.
- 내 보고서 초안의 「무빙 라이트는 위치를 바꾸지 않는다」 → 위치는 큐 경계에서 프리셋으로 바뀐다(M2·M3). 0인 것은 큐 안 Pan/Tilt 페이저다.
