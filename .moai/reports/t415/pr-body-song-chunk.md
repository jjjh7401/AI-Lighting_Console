## 무엇
감독 곡 31.5MB 가 어느 경로로도 안 올라가던 것을 연다.

- 원본 상한 8 → **64 MiB** (REQ-MUSICSYNC-026)
- 한 프레임 대신 `song_audio_upload_begin` / `_chunk` / `_end` 로 분할 전송 (REQ-MUSICSYNC-027). 조각 base64 ≤ 4 MiB — uvicorn 기본 `ws_max_size` 16 MiB 안
- 조립 버퍼는 연결 지역 상태. 조각 수·순서·총 길이가 맞아야만 기존 보관 경로로 넘어간다
- Tauri capability 무변경 (AC-MUSICSYNC-014)
- SPEC 개정 커밋 310aa91 포함

## 검증 (워크트리에서 실행)
- `pytest server/tests/test_web_song_audio.py server/tests/test_prechk_tool.py` → 152 passed
- 전체 스위트(아래 5파일 제외) → 12869 passed, 1 failed(웹 표면 동결 목록) → 목록 등록 후 해당 파일 통과. **등록 후 전체 재실행은 안 했다**
- `npm --prefix ui test` → 571 passed · `tsc --noEmit` rc=0 · `ruff check` 통과
- 부정 대조군: `app.py` 분기를 끄면 WS 왕복 시험 2개 실패 확인 후 복구
- `git diff --name-only 310aa91 -- src-tauri` → 0줄

## 미검증
- `test_director_*` 5파일은 `jsonschema`·`rfc8785` 가 커밋된 pyproject 에 없어 수집 불가 (이 PR 과 무관한 기존 상태)
- **브라우저 실제 업로드 0회** (카드 t415) · 감독 곡 실파일 왕복 0회

🗿 MoAI
