# t570 run 판정 — 재생·음원 마무리

카드: t570 · 브랜치 `WT-playback-finish` · 기준 origin/main `3e118327`(t563 포함, 합침)
범위: SPEC-LDBEAT-001 REQ-LDBEAT-024 / AC-LDBEAT-024, plan.md M9 step 7

## 커밋

| SHA | 내용 |
|---|---|
| 15d3f5e7 | 플레이 묶음·재생 동기·음원 자동 연결·⏪⏩ 이어 재생·갈라짐 마커/부모 줄 넘어감·화면 오류 시 재생 계속 |
| 1040b1a6 · 9a53c757 | origin/main 합침(t566·t563·#612) |
| (이 커밋) | 시안 대조 교정 — ⏪ 10초/10초 ⏩ 를 플레이 묶음 안으로, 「플레이」 이름표, 시계 `분:초.소수` 모양, 「콘솔 같이 끔」 문구, 묶음 테두리 |

## AC-024 판정

| AC | 판정 | 근거 |
|---|---|---|
| (a) 플레이 묶음 | PASS | 시안 순서 플레이·⏮·⏪ 10초·▶ 재생·10초 ⏩·시계·♪·콘솔 같이 끔 — `BeatGridTopBar.test.tsx` 순서 시험 |
| (b)(h) 재생 동기·자동 스크롤·마디 클릭 이어 재생 | PASS(코드·순수 함수) | `playbackClock.autoScrollTargetForPlayhead` 시험, RAF 틱 배선은 DOM 시험대 없음 |
| (c) 음원 자동 연결 | PASS | 생산 지점 `App.tsx` `uploadSongAudio`(세션 첨부) → `attachedSongAudioFile` → `audioAutoConnect` 시험. 경로 상수 0, 커밋된 음원 0(`git ls-files '*.mp3' '*.wav' '*.flac' '*.m4a' | wc -l` → 0) |
| (d) ⏪10초/10초⏩ | PASS | `clampPlaybackSeconds` 시험, 재생 중이면 다시 앵커, 멈춤이면 그 자리 대기 |
| (e) 갈라짐 마커·부모 줄 넘어감 | PASS | `lrSplit.resolveLRSplitViewAfterBarChange` 시험, 「여기서 갈라짐」 |
| (f) 화면 오류 시 재생 계속 | PASS | `playbackClock.runPlaybackFrameUpdate` 시험 |
| (g) ⏮·스페이스·콘솔 같이 | 부분 | ⏮·스페이스 PASS. **콘솔 같이는 꺼 둠** — 아래 갭 |

## 검증 (이 트리)

- RED(교정분): `npx vitest run src/components/beatgrid/playbackClock.test.ts` → `TypeError: formatPlaybackClock is not a function` 3건 → GREEN 18/18
- `cd ui && npx vitest run` → `Test Files 52 passed (52)` / `Tests 1117 passed (1117)`
- `npx tsc --noEmit -p .` → exit 0 · `npm run build` → exit 0
- `uv run pytest -q server/tests/test_beat_grid_console_audio_offset_t570.py server/tests/test_beat_grid_t537.py` → 34 passed
- 콘솔 쓰기 0, 곡·그룹·마디 리터럴 0(시험 고정값 제외)

## 갭

- **「콘솔 같이」 송신 경로 없음**: t563 송신 길(`beat_grid_apply`·`beat_grid_preview`·`beat_grid_preview_off`·`beat_grid_send_status`)은 `Top/Go Timecode` 를 보내지 않고, 게이트 경유로 그 명령을 내는 앱 경로가 없다(`server/tools/musicsync_m3a_probe.py` 탐침뿐). 새 쓰기 경로는 만들지 않았고 토글은 「타임코드 재생 송신 경로 없음」 이유로 꺼 둔다. 음원 지연 3.002초(t520 실측)는 `server/design/beat_grid_data/console_audio_offset.yaml` 데이터로 두고 순수 함수는 인자로 받는다.
- 곡별 음원 영속 연결은 저장소가 없어 범위 밖 — 리드가 t571 로 만듦.
- DOM 시험대가 없어 실제 재생 루프·오디오 이벤트·스페이스 리스너는 브라우저에서 안 띄워 봤다.
