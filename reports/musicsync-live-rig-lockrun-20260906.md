# 실기 리그 앞 곡 → 큐 리스트 (라이브 잠금 회차) — 2026-09-06

기준 트리: main `54cc17c` · **실기 grandMA3 onPC** · 라이브 잠금 **켜짐** · **콘솔 쓰기 0건**

## 결론

가짜 리그가 아니라 **실기 쇼파일의 진짜 리그**(픽스처 86대, 그룹 18개) 앞에서, 곡 하나가 큐 리스트 제안 26개 명령까지 이어졌다. 라이브 잠금을 켜 두었으므로 명령은 **전송되지 않고 제안 카드로만** 나왔고, 감사 로그가 그것을 숫자로 증명한다 — `executed` **0**, `blocked` **26**, 사유 전부 `live lock active`.

이 회차가 답한 질문: 「지금까지의 성공이 가짜 콘솔 덕분은 아닌가?」 아니다. 진짜 리그의 진짜 그룹 이름이 매핑에 쓰였고, 진짜 타임코드 풀 상태 위에서 슬롯이 잡혔다.

## 환경

| 항목 | 값 |
|---|---|
| 서버 | `python -m server.web --port 8770 --console-port 8000 --receive-port 9005 --no-session-backup --no-browser` |
| 콘솔 | **실기 onPC**, 응답기 1.6.5 (`live version=1.6.5`) |
| 리그 | 픽스처 86대 · 그룹 18개(ALL·KEY·FOH·BACK·SIDE-L/R·SIDE-ALL·WASH-U/D/ALL·MOVER-U/D/ALL·BLIND·STROBE·HAZE·ODD·EVEN) · 프리셋 풀 4(Dimmer 7·Position 6·Color 9·All 1 6) |
| 안전장치 | 라이브 잠금 ON (화면 「콘솔 온라인 · 라이브 잠금 활성 (read-only)」) · `--no-session-backup`(t272 고침으로 기동 쓰기 0) |
| 입력 | `synth_128bpm.wav` · 「이 곡으로 큐 리스트 만들어줘. 제목 Synth Test, 장르 EDM, 타임코드 7번. 구간 이름은 Intro, Build, Drop, Outro 로 해줘」 |
| 증거 | `.moai/state/verify/musicsync-live-lock/{proposal.jpeg, audit-20260906.jsonl, srv_live.log}` |

## 관측

1. 잠금 먼저 — 업로드 전에 체크박스를 켜고 상태 배지가 「라이브 잠금 **제안만**」으로 바뀐 것을 확인했다.
2. 업로드 → 분석 → 카드(BPM 129.199, 구간 4) → 「확인」 → 「구간 4건 채택 · 0건 제외」.
3. 큐 요청 → **제안 카드**: 「실행 전 미리보기 — 26개 명령」 + 「제안 카드 — 라이브 잠금 중 (전송되지 않음)」.

제안된 명령(발췌) — **실기 그룹 번호**가 그대로 쓰였다:

```
ClearAll ; Group 4 + 5 + 6 + 7 ; Attribute 'Dimmer' At 72 ; ColorRGB… ; Zoom 35
Store Sequence 5 Cue 2 'Build'
Group 4 + 5 + 6 + 7 ; Dimmer 100 ; ColorRGB… ; Iris 100 ; Zoom 5
Store Sequence 5 Cue 3 'Drop'
Group 3 ; Dimmer 42 ; ColorRGB…
Store Sequence 5 Cue 4 'Outro'
Store Timecode 7 ; Set Timecode 7 Property 'Name' 'Synth Test Timecode'
Assign Sequence 5 At Timecode 7
Set Cue 2 Sequence 5 Property 'TrigType' 'Time' / 'TrigTime' 15.952
Set Cue 3 …                                   'TrigTime' 32.02
Set Cue 4 …                                   'TrigTime' 36.014
```

- **구간 이름이 감독 말 그대로** — `Intro` · `Build` · `Drop` · `Outro`(t274 로 열린 길). `S1..S4` 가 아니다.
- **그룹이 실기 이름** — `Group 3`(FOH), `Group 4+5+6+7`(BACK·SIDE-L·SIDE-R·SIDE-ALL). 가짜 리그였다면 나올 수 없는 조합이다.
- **시각 손실 0** — 15.952 / 32.02 / 36.014.

## 콘솔 쓰기 0 — 숫자로

```
$ grep -c '"event": "executed"' server/audit_logs/audit-20260906.jsonl   → 0
$ grep -o '"event": "[a-z_]*"' … | sort | uniq -c                       → 26 "blocked"
$ grep -o '"reason": "[^"]*"' … | sort -u                               → "live lock active"
```

26개 전부 게이트에서 막혔다. 쇼파일은 이 회차 전후로 바뀌지 않았다.

## 안 잰 것 · 남은 결정

- **실제 저장은 하지 않았다.** 라이브 잠금을 끄고 같은 요청을 하면 26개가 실제로 나가 시퀀스 5와 타임코드 7이 생긴다. 그것은 쇼파일을 바꾸는 행위라 **감독의 결정**으로 남긴다 — 이 회차는 「그 직전까지 전부 옳다」를 증명한 것이다.
- 룩 선택의 조명적 타당성(디머 72/100/42, 색·줌·아이리스)은 값이 나왔다는 것만 확인했다. 실제로 예쁜지는 사람이 볼 일이다.
- 시퀀스 5·타임코드 7 이 실기에서 비어 있는지는 도구가 판정했으나(제안이 만들어진 것이 그 증거), 저장을 안 했으므로 점유 충돌은 미검증이다.
- 다른 곡·장르·구간 수는 재지 않았다.

## 다음 손

1. (감독 결정) 라이브 잠금을 끄고 같은 요청 → 실제 저장. 그 전에 쇼파일 백업 1회.
2. 카드 t276 — 한글 큐 라벨.
