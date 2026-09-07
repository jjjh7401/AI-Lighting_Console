# 곡 업로드 → 분석 → 확인 카드 — 실브라우저 검증 보고 (2026-09-06)

기준 트리: main `f727e11` · 검증 트리: 주 체크아웃 · 콘솔 쓰기: 실기 0 (가짜 콘솔만 받음)

## 결론

- 업로드 → 「분석」 → 확인 카드 → 「확인」 까지 브라우저에서 **끝까지 동작한다**.
- 단, **콘솔이 오프라인이면 파일 첨부 버튼이 비활성**이라 분석 자체에 닿을 수 없다 (발견 1).
- `--no-session-backup` 을 줘도 서버 기동 직후 주기 백업 루프가 콘솔에 `SaveShow` 를 **1회 발사**한다 (발견 2).

## 환경

| 항목 | 값 |
|---|---|
| 서버 | `python -m server.web --port 8765 --console-port 64429 --receive-port 64430 --no-session-backup --no-browser` |
| 콘솔 | 가짜 콘솔 `.moai/state/verify/musicsync-ui/fake_console.py` (실제 Lua 응답기를 lupa 로 구동, 64429 수신 → 64430 회신) |
| 입력 | `.moai/state/verify/musicsync-ui/synth_128bpm.wav` (합성, 128 BPM, 40 s, 1,764,044 B) |
| 브라우저 | Aside (Playwright), `http://127.0.0.1:8765/` |
| 증거 | `card_after_analyse.jpeg`, `fake_console.log`, `server.log` (같은 폴더) |

## 관측 (순서대로)

| 단계 | 관측 | 판정 |
|---|---|---|
| 콘솔 오프라인(죽은 포트)으로 기동 | 상단 「콘솔 오프라인」, `button "파일 첨부" [disabled]` | 발견 1 |
| 가짜 콘솔 기동 후 재기동 | `@copilot:status online`, 첨부 버튼 활성 | OK |
| WAV 업로드 | 「'synth_128bpm.wav' 첨부됨 — 오디오 · sha256 373351cd… · 1764044바이트」 + 「분석」 버튼 | OK |
| 「분석」 클릭 | 「곡 분석 요청」 말풍선, ~20 s 뒤 카드 「구간과 BPM 을 확인해 주세요.」 | OK |
| 카드 내용 | BPM 129.199 (확신 0.98) · 구간 4개 체크박스 D1(0:00–0:15) D3(0:15–0:32) D5(0:32–0:36) D2(0:36–0:40) · 자유 입력란 | OK |
| 「확인」 클릭 | 「BPM 129.199 로 확정했습니다 (measured). 채택 우선순위: 측정 > 시트 HEAD.BPM > 기본값 120.」 | OK, 단 구간 확정 문구 없음 |

가짜 콘솔이 받은 명령 62건: ping 29 · state 31 (`DataPool/Pages` 24 등) · **exec 1 (`SaveShow`, gate-2, 기동 직후)**.

## 발견

### 발견 1 — 콘솔 오프라인이면 곡 분석에 닿을 수 없다
- 근거: `ui/src/App.tsx` `attachmentControlState` — 콘솔 health 가 offline 이면 첨부 버튼 disabled.
- 영향: 곡 분석은 콘솔 없이 되는 순수 DSP 인데, 콘솔이 없으면 업로드 입구가 닫힌다. 사전 준비(콘솔 없는 자리에서 곡 분석)가 불가능.
- 제안: 오디오 첨부는 콘솔 상태와 무관하게 허용하고, 콘솔이 필요한 단계(타임코드 인계)에서만 막는다. 카드 1장 규모.

### 발견 2 — `--no-session-backup` 이 기동 시 콘솔 쓰기를 막지 못한다
- 근거: `server/web/serve.py:106` `--backup-poll` 기본 30 s 로 `_backup_loop` (`server/web/app.py:264`) 이 기동 즉시 `manager.tick()` 을 호출하고, `server/safety/backup.py:130` 은 `_last_backup_at is None` 이면 무조건 `_backup("periodic")` → `SaveShow` 발사. 플래그는 `bootstrap.py:185` 의 rule-① 시도만 끈다.
- 영향: 검증·프로브 용도로 「쓰기 없이」 띄웠다고 믿는 서버가 실기 콘솔에 1회 저장을 남긴다. t269 의 SaveShow 2건 발사와 같은 계열.
- 제안: `--no-session-backup` 일 때 `backup_poll_seconds` 도 0 으로 내리거나, 첫 tick 을 interval 뒤로 미룬다. 카드 1장 규모.

### 발견 3 (경미) — 확정 후 구간 결과가 안 보인다
- 「확인」 뒤 메시지가 BPM 만 말하고, 체크한 구간 4개가 어떻게 됐는지(채택/다음 단계) 문구가 없다. 「분석」 버튼도 그대로 남아 재분석이 가능해 보인다. UX 문구 문제.

## 안 잰 것

- 실기 콘솔 앞 동작(가짜 콘솔만). 응답기 1.6.4 실기와의 차이는 이 검증 범위 밖.
- 체크박스를 풀고 자유 입력으로 고치는 경로, 「BPM 130」 같은 정정 입력 경로.
- mp3/flac/m4a 업로드 (wav 만).
- 확정 뒤 타임코드 인계 카드(`build_timecode_handoff_card`)는 생산 호출자가 없어 도달 불가 — MUSICSYNC-001 부채 그대로.

## 다음 손

1. 발견 1·2 를 백로그 카드로 올린다 (각 1장).
2. t270 (POOLEMPTY-001) plan-audit 1차 FAIL 0.71 — 결함 D1–D7 고치고 재감사.
