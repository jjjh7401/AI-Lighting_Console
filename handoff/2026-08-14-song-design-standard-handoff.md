# 세션 핸드오프 — 2026-08-14 (SONGSTD 다음 단계)

## 목적

`feature/song-design-standard` 브랜치의 최종 목표는 **조명감독이 한 곡의 음악을 시간축 위에서 설계하고, 그 결정을 검토·승인한 뒤 안전하게 콘솔 큐로 적용**하는 것이다.

현재 구현은 이 목표의 기반을 만들었으나, 감독 연출 데이터와 시간 기반 큐 생성이 서로 다른 두 경로에 남아 있다. 다음 구현은 새 보조 기능이 아니라 이 분리를 없애는 통합 작업이어야 한다.

## 현재 검증 결론

### 구현된 두 경로

1. `prepare_songcue` — `server/orchestrator/tools.py`, `server/looks/songcue.py`
   - 수동 구간 시각·장르·다이내믹스를 받는다.
   - 장르별 사전 제작 Look을 선택해 시퀀스 Cue, `TrigType=Time`/`TrigTime`, Timecode 오브젝트를 만들고 시퀀스를 재조회한다.
   - 감독 인터뷰, `MusicProfile`, `RigProfile`, 팔레트, 공간/질감/클라이맥스 결정을 소비하지 않는다.

2. `디자인 큐 시트`/`연출 인터뷰` — `server/web/session.py::_song_design_interview`, `server/design/interview.py`, `server/spatial/position_cuesheet.py`
   - Q1 컨셉, Q2 팔레트, Q3 클라이맥스, Q4 공간 스토리, Q5 질감을 한 카드씩 수집하고 감사 기록을 남긴다.
   - 포지션 프리셋, D레벨 기반 디머·페이드, blackout/MIB를 만든다.
   - `start_ms`는 순서 검증·표시용이다. Timecode/`TrigTime`을 만들지 않는다.
   - Q1/Q2만 `DirectorInterview.working_profile`에 반영된다. Q3/Q4/Q5는 감사 기록에는 남지만 현재 생성된 Cue의 실제 속성으로 전달되지 않는다.

### 직접 검증한 테스트

```text
uv run pytest server/tests/test_design_integration.py \
  server/tests/test_design_interview.py \
  server/tests/test_position_cuesheet.py \
  server/tests/test_web_session.py
# 162 passed
```

이 결과는 순수 설계 엔진·인터뷰·포지션 시트·가짜 세션 포트 계약만 증명한다. 실제 오디오, Timecode 재생, MA3 콘솔/3D 리허설 E2E는 증명하지 않는다.

## 마일스톤 상태

| 마일스톤 | 현 상태 | 남은 종료 증거 |
|---|---|---|
| M1 표준 엔진 | 완료 | `acceptance.md` M1 체크 완료. MusicProfile/RigProfile/energy/lint 및 테스트 존재. |
| M2 포지션+디머·감독 인터뷰 | 코드 구현됨, 미종료 | Q3~Q5를 실제 cue-plan에 반영, 12구간 콘솔/3D 밝기·페이드 실측, 인터뷰 자유 팔레트가 큐 색으로 나타나는 증거. |
| M3 컬러 통합 | 미구현 | 팔레트 3~5색/C1~C5, RGB cue 합성, FX 예산, `/Merge` 금지, 프레임 diff·색 히스토그램 실측. |
| M4 오디오 분석 | 미구현 | 업로드, 지연 import DSP, BPM/온셋/RMS/경계 테스트, 실제 곡→확인카드→시트→콘솔 재생. |
| 통합 타임라인 | 미구현 | 감독 판단과 Timecode/TrigTime 및 단일 승인·원자적 저장을 같은 plan으로 연결. |

`acceptance.md`의 M2~M4 체크박스는 모두 미체크다. M2 관련 코드와 단위/세션 테스트는 후속 구현으로 존재하지만, 문서가 요구한 라이브 검증·컬러 반영·완결 적용을 아직 충족하지 않는다.
### 2026-08-14 통합 타임라인 구현 갱신

- `server/design/song_plan.py`: immutable `UnifiedSongLightingPlan`이 timestamped sections, `MusicProfile`, `RigProfile`, Q1~Q5 감독 결정, 구간별 D/팔레트/포지션/질감/FX/악센트, 실행 타이밍, unresolved/disabled notes, approval state를 함께 보유한다.
- `server/design/interview.py`: Q3는 peak/accent/D 방향, Q4는 narrow-to-wide position story, Q5는 snap/fade·FX density·BPM speed 방향으로 typed projection 된다.
- `server/design/song_cue_composer.py`: 모든 구간을 하나의 비-I/O reviewed cue bundle로 조합하고, unresolved 또는 감독 미확정 답변에는 해당 카드 재질의를 요구한다. `/Merge` 명령은 생성하지 않는다.
- `server/web/session.py`: 디자인 인터뷰 완료는 먼저 전곡 리뷰를 표시한다. 별도 `승인` 전에는 console write가 없고, 승인 후에는 하나의 reviewed-bundle dispatch만 수행한 뒤 Sequence 및 선택 Timecode readback을 검증한다.
- `server/looks/songcue.py`: 기존 요청 문법을 유지하는 순수 timing-plan adapter를 추가했다.
- 검증: `uv run pytest server/tests/test_song_plan.py server/tests/test_song_cue_composer.py server/tests/test_songcue_timing.py server/tests/test_design_integration.py server/tests/test_design_interview.py server/tests/test_position_cuesheet.py server/tests/test_web_session.py` → **198 passed, 2 skipped**.
- 아직 수행하지 않음: 실제 MA3/onPC 또는 3D 검증, 12구간 실곡 시트, 색 히스토그램/프레임 diff. 이들은 Wave 4 단독 세션에서만 수행한다.

- `ui/src/components/SongTimeline.tsx`와 런북의 `감독 타임라인` 탭은 서버가 전송한 read-only plan projection을 시간축으로 보여준다. 실행·저장은 기존 승인 경로에만 남아 있으며, 타임라인에는 실행 명령 필드가 없다.
- WebSocket `song_timeline` 이벤트는 draft/requery/approval/readback lifecycle을 UI에 전달한다. 현재 연결이 끊기면 UI는 마지막 계획을 stale로 표시하고 새 세션의 plan으로 주장하지 않는다.

## 다음 구현의 단일 산출물

`UnifiedSongLightingPlan`을 정의·도입한다. 이 객체가 두 경로의 분리를 끝내는 유일한 공유 계약이다.

```text
Timestamped sections
+ MusicProfile
+ RigProfile
+ DirectorInterview audit/overrides
→ UnifiedSongLightingPlan
  - section decisions: D, palette, position, texture, FX, accents
  - cue bundles: position + dimmer + color + allowed FX + MIB
  - timing: manual Go or TrigTime/Timecode
  - validation: lint + unresolved/disabled notes
→ director review/approval
→ atomic console commit + readback verification
```

### 결정 규칙

- 감독 미확정(`confirmed=False`) 답변은 초안이다. 자동 콘솔 저장의 승인으로 취급하지 않는다.
- 무드/팔레트/효과가 해석되지 않으면 추측하지 말고 해당 카드로 되묻는다.
- Timecode와 수동 Go는 곡/운영자가 선택하는 실행 모드다. 기본 하이브리드 원칙을 유지한다.
- Cue 저장 전에는 완성된 전곡 plan을 한 번 검토한다. cue bundle을 개별 dispatch하여 부분 저장하는 방식은 통합 경로에서 금지한다.
- 기존 `prepare_songcue` 및 `포지션 큐 시트` 요청 문법은 호환성을 유지하되, 새 통합 경로는 명확한 새 요청/계약으로 시작한다.

## 다음 세션 병렬 오케스트레이션 DAG

Orca 런타임을 사용한다. 구현 전 동시 작업은 아래 세 가지이며 파일 소유권을 겹치지 않는다.

```text
Wave 1 (parallel)
A. Domain-plan contract
   Own: server/design/song_plan.py, server/tests/test_song_plan.py
   Define immutable section decision, timing mode, cue payload boundary, director
   override projection, unresolved/approval state. No session or command builder edits.

B. Existing timecode adapter audit/prototype
   Own: server/looks/songcue.py tests only, or a new adapter module/tests
   Extract/reuse safe TrigTime/Timecode plan formation behind a pure interface.
   Do not modify session.py or position_cuesheet.py.

C. Director-decision projection
   Own: server/design/interview.py, server/tests/test_design_interview.py
   Add an explicit typed projection for Q3/Q4/Q5 into per-section decisions.
   Do not create console command strings.

Wave 2 (depends on A+B+C)
D. Cue composer
   Own: new server/design/song_cue_composer.py + tests
   Combine plan, standard position/dimmer sheet, RGB palette/allowed FX/MIB.
   Build a complete non-I/O cue bundle and lint report; reject unresolved state.

Wave 3 (depends on D)
E. Web/session review gate + atomic executor
   Own: server/web/session.py, UI protocol/components, focused tests
   Render the complete timeline first. Require explicit director approval before any
   write. Execute as one reviewed bundle and read back sequence + timing.

Wave 4 (after E)
F. Real-console and 3D protocol
   Own: tools/runbooks/measurement artifact only, no speculative production changes
   Test a 12-section song on a new sequence, preserve baseline Sequence 114, record
   brightness/fade/color evidence and all MA3 readbacks.
```

### Orca coordinator commands for next session

Before dispatching, inspect the runtime; never adopt or terminate unrelated runs.

```bash
orca status --json
orca orchestration run-create --objective "SONGSTD unified director timeline: integrate director decisions with timed cue plan" --json
orca orchestration task-create --spec "<A contract task>" --json
orca orchestration task-create --spec "<B timing adapter task>" --json
orca orchestration task-create --spec "<C decision projection task>" --json
orca orchestration worker-start --task <A> --worktree current --agent codex --json
orca orchestration worker-start --task <B> --worktree current --agent codex --json
orca orchestration worker-start --task <C> --worktree current --agent codex --json
orca orchestration check --wait --types worker_done,escalation,question --timeout-ms 900000 --json
```

After each accepted `worker_done`, release the settled worker unless it is immediately reused:

```bash
orca orchestration worker-release --dispatch <dispatch_id> --json
```

Then create Wave 2 only after A/B/C all complete. Do not run console-writing or actual-song verification in parallel with another session against the same MA3/onPC instance.

## Existing Orca cleanup performed/required

The historical run `run_cf796cdcede1` contains 12 completed M1/M2 tasks. It is historical provenance, not the run for the next implementation wave. Its worker dispatches should be released only through `orca orchestration worker-release`; do not use broad terminal cleanup and do not close unrelated project sessions.

## High-value source files

- `.moai/specs/SPEC-COPILOT-SONGSTD-001/spec.md`
- `.moai/specs/SPEC-COPILOT-SONGSTD-001/plan.md`
- `.moai/specs/SPEC-COPILOT-SONGSTD-001/acceptance.md`
- `docs/proposals/song-lighting-design-standard.md`
- `server/design/interview.py`
- `server/design/profile.py`
- `server/design/energy.py`
- `server/design/rig.py`
- `server/design/lint.py`
- `server/spatial/position_cuesheet.py`
- `server/looks/songcue.py`
- `server/orchestrator/tools.py`
- `server/web/session.py`
