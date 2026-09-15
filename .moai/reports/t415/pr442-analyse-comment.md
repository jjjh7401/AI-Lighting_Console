## t415 후속 — 분할로 올린 곡이 「분석」 → 확인 카드까지 간다 (브라우저 실측)

Chromium 에서 `scott-buckley-neon.mp3`(10366612 바이트, 구 상한 초과)를 올린 뒤 「분석」 버튼을 눌렀다. 서버 `console_offline`, 콘솔 접촉 0.

- 버튼 → `question_request` 도착 **3.1초**, `error` 프레임 0건, 서버 Traceback 0건
- 카드: `multi: true`, 구간 옵션 **17개**, DSP 제안 `selected: true`
- 마지막 구간 `3:54–4:19` 의 끝 = `soundfile.info` 길이 **259.08초** — 곡 전체가 분석됐다(조립 누락 없음)

**미검증**: 카드의 「확인」 누름(BPM 확정) · 감독 실제 곡 · Tauri WKWebView

🗿 MoAI
