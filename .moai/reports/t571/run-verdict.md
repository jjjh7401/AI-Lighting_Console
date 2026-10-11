# t571 run 판정 — 곡별 음원 영속 연결

카드: t571 · 브랜치 `WT-song-audio-persist` · 기준 origin/main `46e4fb27`(에이전트가 작업 중 main 이 10커밋 움직여 rebase)
범위: SPEC-LDBEAT-001 REQ-LDBEAT-024(c) 후속 — 앱·서버를 다시 열어도 런북 뷰가 곡의 음원을 자동 연결

## 설계 (리드 승인 2026-10-11)

- 브라우저는 업로드 파일의 로컬 경로를 주지 않는다 → 경로 저장은 불가능. 서버가 받은 **음원 바이트**를 앱 상태 폴더에 sha256 이름으로 보관한다.
- 저장 위치: `pin_store_path("song_audio_index.json")`(`server/web/panel.py:174`, 기존 `song_timeline.json`·`song_timeline_library.json` 과 같은 관행) → OS 사용자 데이터 폴더의 `song_audio_index.json` + 옆 `song_audio_files/`. 경로 상수 0.
- 곡 키: 기존 `ChatSession._beat_grid_song_key`(`server/web/session.py:9396`)가 쓰는 `(song_title, sequence_number)` — 새 id 체계 없음.
- 업로드 성공 시 현재 곡 키가 있으면 저장(같은 곡은 교체). 런북 뷰가 열리고 세션 첨부 파일이 없으면 `song_audio_link_request` → `song_audio_link`(크면 `_begin/_chunk/_end` 분할, 업로드와 같은 프레임 상한). 색인은 있는데 파일이 없거나 sha256 이 다르면 `missing` → 화면 「음원 없음」. 세션 첨부가 이긴다.
- 기존 인증된 WS 만 씀(새 비인증 HTTP 경로 0). 새 WS 타입은 messages.py 목록·PROTOCOL.md·prechk 동결 목록에 함께 넣음.

## 리드 확인 요구 2건

| 요구 | 근거 |
|---|---|
| ① 음원 폴더가 git 추적 밖 | `server/tests/test_song_audio_link_store.py::TestTheStorageDirectoryIsOutsideGitTracking` — 운영과 같은 방식으로 경로를 풀어 저장소 밖(또는 `git check-ignore`)임을 단언. `git ls-files '*.mp3' '*.wav' '*.flac' '*.m4a' | wc -l` → 0 |
| ② 같은 sha 는 한 번만, 원자적 쓰기 | `TestContentAddressedDedup`(같은 바이트 두 번째 저장은 파일을 다시 쓰지 않음·두 곡이 같은 바이트면 파일 하나), `TestAtomicWrites`(음원·색인 모두 같은 폴더 임시 파일 + `os.replace`, 교체 실패 시 반쯤 쓴 파일 없음·이전 색인 유지) |

## 검증 (이 트리 060d3ac1)

- `cd ui && npx vitest run` → `Test Files 53 passed (53)` / `Tests 1149 passed (1149)`
- `npx tsc --noEmit -p .` → exit 0 · `npm run build` → exit 0
- `uv run ruff check`(바꾼 서버 파일 7개) → `All checks passed!` · `ruff format --check`(새 파일 3개) → 이미 정리됨
- 전체 pytest: `uv run pytest -q` → `15241 passed, 33 skipped, 1 warning`(exit 0)

## 갭

- 엄격한 RED 먼저는 일부만 — 에이전트가 저장소·업로드 연결 일부를 시험과 함께 썼다고 스스로 밝힘(잡힌 실제 결함 2건은 RED 로 포착: WS 프레임 순서, prechk 동결 목록 회귀).
- 실제 서버를 다시 띄워 브라우저에서 자동 연결되는지는 안 해 봤다(DOM 시험대 없음, 서버 시험은 새 인스턴스로 재시작 흉내).
- 곡 키가 `(song_title, sequence_number)` 라서, 곡 제목을 바꾸면 이전 연결은 다른 곡으로 본다.
