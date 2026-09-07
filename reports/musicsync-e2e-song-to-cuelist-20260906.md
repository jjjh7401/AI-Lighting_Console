# 곡 → 큐 리스트 끝단 실측 (2026-09-06)

기준 트리: main `f611eef` + CI 복구 브랜치 `WT-hunk-pin-merge`(`178a0c4`, PR #322) · 실기 콘솔 쓰기 0 (가짜 콘솔만 받음)

## 결론

**곡 파일 하나에서 콘솔 명령 26개까지 한 번에 닿는다.** WAV 업로드 → 분석 → 확인 카드(구간 3 채택·1 제외) → 「이 곡으로 큐 리스트 만들어줘」 → 모델이 `prepare_songcue` 를 **확정 구간 그대로** 호출 → Sequence 4(큐 3개, TrigTime 0 / 15.952 / 36.014) + Timecode 5 가 가짜 콘솔에 저장됐다. 오늘 머지한 세 변경(t271·t273·t270 M2)이 전부 이 경로에서 실제로 쓰였다.

## 환경

| 항목 | 값 |
|---|---|
| 서버 | `python -m server.web --port 8768 --console-port 64441 --receive-port 64442 --no-session-backup --no-browser` (워크트리 `t273fix`) |
| 콘솔 | 가짜 콘솔 `fake_console.py … full` — 실제 Lua 응답기 **1.6.5**, 그룹 6(Back Wash·FOH Wash·Side L·Top·Cyc·Special)·시퀀스 3·**빈 Timecodes 풀** |
| 모델 | Gemini 3.5 Flash — `--config` 로 claude_code 를 지정했으나 사용자 설정(`~/Library/Application Support/GrandMA3 Copilot/settings.toml`, `active_provider = "gemini"`)이 우선했고 키는 OS 키스토어에서 주입됨 |
| 입력 | `synth_128bpm.wav` (합성 128 BPM, 40 s) · 지시문 「이 곡으로 큐 리스트 만들어줘. 제목 synth, 장르 EDM, 타임코드 5번」 |
| 증거 | `.moai/state/verify/musicsync-e2e/{song_to_cuelist.jpeg, fc_e2e.log, srv_e2e.log}` · `server/audit_logs/{audit,probe}-20260906.jsonl`(워크트리) |

## 관측

| 단계 | 관측 | 근거 |
|---|---|---|
| 기동 | `@copilot:status online`, 가짜 콘솔 exec **0** | t272 고침 유지 (`fc_e2e.log`) |
| 업로드·분석 | 카드 「구간과 BPM 을 확인해 주세요」 BPM 129.199, 구간 4 | 스냅샷 |
| 확인 (3번째 체크 해제) | 「BPM 129.199 로 확정 … **구간 3건 채택 · 1건 제외**. 이 곡의 큐 리스트를 만들려면 타임코드 번호와 함께 말씀해 주세요 — 확정한 구간을 그대로 씁니다.」 | t273 M1·M2 |
| 큐 요청 | 「실행 전 미리보기 — 26개 명령」 → 「요청한 명령을 모두 실행했습니다」 · 모델 답에 Cue 1 S1 `00:00.000` / Cue 2 S2 `00:15.952` / Cue 3 S3 `00:36.014` | 스크린샷 |
| 가짜 콘솔 수신 | exec **26**: `Store Sequence 4 Cue 1..3 'S1'..'S3'`, `Label Sequence 4 'synth'`, `Store Timecode 5`, `Assign Sequence 4 At Timecode 5`, `Set Cue n … 'TrigType' 'Time'` / `'TrigTime' 0 / 15.952 / 36.014`, 그룹·속성 명령 | `fc_e2e.log` |
| 슬롯 판정 | `DataPool/Timecodes` 조회 1회(`probe-…jsonl`), 빈 풀인데 **free** → `Store Timecode 5` 발화 | t270 M2 (마커 `"ok"`) |

확정 구간 → 큐 시각 대조: 채택 0:00 / 0:15(15,952 ms) / 0:36(36,014 ms), 제외 0:32 → TrigTime 0 / 15.952 / 36.014, 큐 3개. **손실 0, 제외 구간 미반영 확인.**

## 발견

1. **`--config` 는 사용자 설정에 진다.** 시드 설정을 바꿔도 `settings.toml` 의 `active_provider` 가 우선한다 — 검증 목적엔 함정(설정 화면에서 바꿔야 한다). 문서화 후보.
2. **미리보기 뒤 자동 실행.** 라이브 잠금이 꺼져 있으면 26개 명령이 승인 카드 없이 곧장 실행된다 — 가짜 콘솔이라 무해했지만, 실기에서는 「쇼파일을 바꾸는 저장」이 한 문장으로 나간다. 기존 설계(게이트가 저장 명령을 허용)이며, 실기 첫 회차 전에 감독이 라이브 잠금을 켤지 결정할 자리.
3. 큐 이름이 `S1·S2·S3` 중립 이름 — 설계대로(룩 어휘 오인 방지). 감독이 보기엔 「인트로/후렴」이 더 읽기 좋다 — 후속 카드 후보(확정 카드에서 구간 이름 입력).

## 안 잰 것

- 실기 콘솔(가짜 콘솔만). 응답기 1.6.5 실기 재임포트는 감독 몫(t270 M3).
- 룩 선택의 조명적 타당성(Dimmer 20/72/42, 색) — 값이 나왔다는 것만 확인.
- 다른 곡·장르·구간 수(4 이상)에서의 동작.

## 다음 손

1. PR #322(CI 복구) 머지 → main 초록 확인.
2. t270·t273 sync 단계(CHANGELOG·README·SPEC completed).
3. t270 M3 실기 — 감독: 슬롯 삭제→재임포트, Timecode 1·999 삭제 → ping·판정 실측.
4. 카드: 구간 이름 입력(발견 3) · `--config` 우선순위 문서화(발견 1).
