## t415 브라우저 실측 (2026-09-14, 이 브랜치 9b8fb9d)

실제 Chromium(Playwright)으로 파일 선택창에 곡을 넣었다. 서버는 `python -m server.web --console-port 1 --no-session-backup` — 상태 `console_offline`, 콘솔 접촉 0.

| 파일 | 크기(바이트) | 보낸 프레임 | 가장 큰 프레임 | 서버 고지 sha256 = 원본 |
|---|---|---|---|---|
| scott-buckley-neon.mp3 | 10366612 (구 상한 8 MiB 초과) | begin + chunk 4 + end | 4194374 | ✅ |
| Cut and Run.mp3 | 8595361 (구 상한 초과) | begin + chunk 3 + end | 4194374 | ✅ |
| 합성 WAV 178.5초 스테레오 | 31487444 (감독 곡 급) | begin + chunk 11 + end | 4194374 | ✅ |

- 가장 큰 프레임 4194374 바이트 < uvicorn 기본 `ws_max_size` 16777216
- 세 경우 모두 UI 에 「곡 «…» 첨부됨」 표시, 서버 로그에 `song_audio_rejected`·Traceback 0건

**미검증**: 감독 실제 곡 파일(이 컴퓨터에 없음) · 올린 뒤 「분석」 버튼 경로(이번 실측은 업로드까지) · Tauri 패키지 앱 안의 WKWebView(이번은 Chromium)

🗿 MoAI
