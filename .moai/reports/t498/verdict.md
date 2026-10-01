# t498 판정서 — 8곡 실기 검증 0단계 + 파일럿 Rain (중간본: 3단계 재생 대기)

> 🔴 **치명 후보 (리드 지정, 2026-09-28)**: 이름 있는 `SaveShow '<이름>'` 가 앱 게이트에서 **승인 없이 cleared** 된다
> (`run2_saveshow_copy/result.json`·`run2b_saveshow_copy_sq.stdout.txt` — `approval_requests: []`). 공식 문서상
> 같은 이름 쇼 파일을 덮어쓰는 명령이다. 이번엔 브리지(큰따옴표)와 콘솔 확인 대화상자(작은따옴표)가 우연히 막았다.
>
> ~~중대 후보: TrigTime 절대 시각 대 MA3 직전 큐 기준~~ → **반증됨 (감독 육안 2026-10-01, 큐 3 하나 기준)**.
> `Go+ Sequence 211` + Rain.mp3 동시 시작 → **33.6초에 Verse 2** 로 바뀌었다(직전 기준이면 54.5초). 공식 문서
> 문구("after the previous cue is triggered")와 실기가 다른 이유는 **미측정**이다. 관측 범위: 큐 3 하나, 타임코드 11 이 아니라
> 시퀀스 직접 Go 로 시작했다 — 큐 4 이후·타임코드 재생 경로는 이 관측이 덮지 않는다.

- 카드: t498 · 브랜치 `WT-rehearsal-pilot` · 워크트리 `.claude/worktrees/t498`
- base: 착수 시점 `origin/main` = `6ee9b8f5` (`0 0`) · venv: 이 트리 `uv sync --group dev`
- 계획: 주 체크아웃 `reports/rehearsal-8song-plan-20260928.md` · 도구: t474 방식(`real_console.py`, 고정 승인)
- 콘솔: grandMA3 onPC · 응답기 `CopilotResponder` 1.6.5 · 송신 8000 / 수신 9005

## 1. 항목별 판정 (Rain)

| ID | 항목 | 판정 | 근거 |
|---|---|---|---|
| A1 | 곡 분석 재현 | PASS | BPM 76.0135(기준 76.0, 소수 1자리 저장) · 구간 12/12 — `judge_a1_a5_rain.txt` |
| A2 | 게이트 G1~G13 | PASS | 13/13 `passed: true`. 판정기 음성 대조: G7 을 거짓으로 뒤집으면 `not_passed=['G7 …']` — `control_a2_flipped_gate.txt` |
| A3 | 결정성 | PASS | 가짜 콘솔 2회 승인·송신 목록 바이트 동일(107줄) |
| A4 | 승인 = 송신 | PASS | 가짜 107 = 107 · 실기 119 = 119, 순서까지 동일 — `run6_sent_vs_approved.txt` |
| A5 | 승인 밖 명령 | PASS(주석) | 실기 쓰기 run6: 승인 밖 0. 전부-거절 run3 에서 알려진 `ClearAll` 1줄(t497) |
| A6 | 실기 쓰기 성공 | PASS | 119/119 `ok: true`, `SaveShow` 송신 0(자동 백업 1회는 기록만) — `run6_audit_commands_sent.txt` |
| A7 | 되읽기 | PASS | props 직접 판독 13/13 이름·TrigType·TrigTime(±0.001) 일치 — `judge_a7_rain.txt`. 앱 되읽기 「검증 완료」(t479 수정이 실기에서 동작). 음성 대조: 큐 7 을 0.002초 밀면 12/13 — `control_a7_shifted_time.txt` |
| A8 | 런북 화면 | 미판정 | 이번 단계에서 브라우저를 안 열었다 |
| C1 | 기존 쇼 보존 | PASS | 쓰기 전후 시퀀스·타임코드·그룹·프리셋 풀: 추가만 211·11, 제거·변경 0 — `c1_before_after_diff.txt` |
| C2 | 백업 | PASS(주석) | 감독이 콘솔에서 직접 저장 **`Copilot_Test_20260928`**(리드 전달). 앱 경로 저장은 불가(§4). 복원은 콘솔에서 쇼 불러오기 |
| C3 | 번호 충돌 | PASS | 쓰기 직전 211·11 빈 칸 재확인(`run5_before_write.txt`), 프리셋 새로 쓰기 0(2.21~2.30 재사용) |
| B1~B12 | 감독 육안 | (빈칸) | 3단계 |

## 2. 실측 기록

| run | 내용 | 결과 |
|---|---|---|
| run0 | 읽기: 응답기·시퀀스·타임코드·그룹·풀 | 211~218·11~18 빔 · 그룹 18(14=BLIND) · 2.21~2.30 존재 · 쇼 파일 이름 판독 불가(run0b) |
| run1 ×2 | 가짜 콘솔 Rain(그룹 풀은 run0 실기 번호) | 107줄, A1~A5 |
| run2 | `SaveShow "copilot-rehearsal-20260928"` | 브리지 거절(큰따옴표), 콘솔 도달 0. 1차 시도(run2a)는 스크립트 오류로 송신 전 종료 |
| run2b | `SaveShow 'copilot-rehearsal-20260928'` | 콘솔 회신 `User Canceled Command`, 재송신 안 함 |
| run3 | 실기 전부-거절 | 승인 요청 119줄, 송신은 `ClearAll` 1줄뿐 |
| run4 | 읽기: 기구 86대 번호·이름·기종 | W 줄 28기구 이름 붙임 |
| run5 | 읽기: 쓰기 직전 스냅숏 | run0 과 같음 |
| run6 | 실기 쓰기(run3 목록 고정 승인) | 119/119 ok · 앱 되읽기 「검증 완료」 |
| run7·8 | 읽기: 쓰기 뒤 풀·시퀀스 211·큐 13개 속성 | C1·A7 |
| run9 | 읽기: 타임코드 11 속성·트랙 | §5 |

### 리허설 대 실기 차이 전량 분류 (`classify_diff.py` → `run3_classify_diff.txt`)

- 줄 머리 기구 목록만 다른 줄: 가짜 콘솔 좌표 대역이 기구 20·26 두 대라서. 목록을 `<SET>` 으로 바꾸면 107줄 순서까지 일치
- 실기 전용 12줄: 전부 `… ; Attribute 'ColorRGB_W' At 0`, 큐마다 1줄, 같은 28기구 — MOVER-D 521~528(Robin Spiider) +
  WASH-U 401~410 · WASH-D 421~430(Rush Par 2 RGBW Zoom) (`run4_w_fixture_names.txt`, `run4b_fixture_types.txt`)
- 설명 안 되는 줄 0. 분류기 양성 대조: `Delete Sequence 14` 한 줄 끼우면 UNEXPLAINED(`control_classify_injected_line.txt`)

## 3. 발견 목록

형식: 곡 · 큐 · 항목 · 본 것 · 기대 · 심각도 · 증거

1. — · — · C2/안전 · 이름 있는 `SaveShow` 가 게이트에서 승인 없이 cleared · 쇼 파일 덮어쓰기 명령은 승인 카드 · **치명 후보** · `run2b_saveshow_copy_sq.stdout.txt`
2. Rain · 전 큐 · B2 · TrigTime 에 절대 시각 기록(`songcue.py:654`) 대 공식 문서의 「직전 큐 기준」 · ~~중대 후보~~ **반증됨(감독 육안, 큐 3 하나 기준 — 33.6초 전환)** · 문서와 실기가 다른 이유는 미측정 · §5, `stage3_playback_prediction.txt`
3. — · — · C2 · 앱으로 이름 있는 쇼 저장 불가 — 큰따옴표는 브리지 거절(`protocol.py:127`), 작은따옴표는 콘솔 확인 대화상자로 취소 · 백업 저장 가능 · 보통 · run2·run2b
4. Rain · 12 Finale · B8 · 앱 회신 「절정 연출 미반영: blinder_six_row_absent — 'Finale' 이 §6 표 행에 안 맞아 블라인더 밝기 근거 없음」 · 절정에 블라인더 · 보통(기록) · `run6_rain_real_write/replies.json`
5. Rain · 2~11 · — · 페이저 3종(Wave CM·Breathe Warm·Finale Slam) 콘솔 풀에 없어 미배정 · 계획 §8 에 알려진 한계 · 기록 · 같은 파일
7. Rain · 211/11 · C2 · 첫 쓰기(2026-09-28)가 재생 전에 콘솔에서 사라졌다(리드 2026-10-01 읽기 전용 확인, 시퀀스 18개·타임코드 5개 = 쓰기 전) · 쓰기가 재생까지 남는다 · 보통 · 원인 추정(미측정): 감독 복사본 저장이 쓰기 **전**이었고 그 뒤 재시작·재불러오기로 저장 안 한 쓰기가 소실 — `run10_before_rewrite.txt` 가 쓰기 전과 같음을 내가 다시 확인
6. — · — · 도구 · 풀 판독이 잘린 응답(시퀀스 19개 중 2000 이 1쪽 밖)을 「삭제」로 보이게 했다 · — · 보통(절차) · `control_pool_truncated.txt`

## 4. 절차 수정 사항 (나머지 7곡 전에)

1. **쇼 복사본은 콘솔에서 감독이 직접 저장**한다(앱 경로 불가, 발견 3). 계획 0단계의 「백업 저장」을 감독 작업으로 옮긴다.
2. **풀 판독은 `truncated`·`childCount` 를 확인**하고 다음 쪽을 읽는다. `pool_snapshot.py` 가 이제 잘린 응답이면 멈춘다.
3. **리허설 그룹 풀은 실기 판독 번호로** 넣는다(이번에 적용). 남는 차이는 기구 목록(가짜 좌표 대역)과 W 줄뿐이라 `classify_diff.py` 로 자동 분류된다.
4. **판정 스크립트마다 음성 대조를 같이 돌린다.** 이번에 A2 판정기가 없는 키를 읽어 「FAIL 0」을 냈고, 대조군 치환이 두 번 「적용 안 됨」이었다 — 치환 뒤 `cmp`/`assert` 로 적용을 확인한다.
5. ~~발견 2 가 참이면 나머지 7곡 실기 쓰기는 의미가 줄어든다~~ — 발견 2 반증(감독 육안). 재생 시작은 감독 기록대로
   `Go+ Sequence 211` + 음원 동시 시작이 쓰였다. 타임코드 11 재생 경로는 아직 안 쟀다.
6. 셸 주의: zsh 는 따옴표 없는 변수를 단어로 안 나눈다 — 인자 여러 개는 `xargs -0` 으로.
7. **복사본 테스트는 쓰기 직후 복사본에 저장한다 — 재생 전 소실 방지**(리드 지시 2026-10-01). 첫 쓰기(2026-09-28 run6)가
   재생 전에 콘솔에서 사라졌다(§8).

## 5. 3단계 재생 준비

### 무엇이 재생을 움직이는가 (판독)

- 타임코드 11: 이름 「Sequence 211 Timecode」 · DURATION 0.00 · LOOPMODE Off · 트랙 `<Sequence 211>` 의 TimeRange 이벤트 **0개**(`run9*`).
  타임코드 1(DinoSync)도 이벤트 0개 — 이 저장소의 방식은 「타임코드가 시퀀스를 돌리고 큐 전환은 각 큐의 Time 트리거가 한다」로 보인다(판독).
- 🔴 원격 `Go Timecode` 의 효과는 저장소 기록상 **미증명**(`docs/research/ma3-effects/14-musicsync-m3a-timecode-probe-run2.md` 「2회차 정정」). 재생은 콘솔에서 감독이 손으로 시작한다.
- 공식 문서(help.malighting.com, grandMA3 2.2 Sequence Sheet): Trig Type Time = "triggered a set time after the previous cue is triggered", Trig Time "starts counting down when the previous cue is triggered".

### 감독 절차 (제안)

1. 콘솔 Timecode 풀에서 11번을 열고 재생 위치 0 확인 → 재생 시작과 **동시에** 주 체크아웃 `src/sample music/Rain.mp3` 를 재생(손 동기 — 오차는 안 쟀다, 1박 = 0.789초)
2. **첫 판별 지점: 33.6초.** 의도대로면 여기서 큐 3 Verse 2 로 바뀐다. 직전 기준 해석이면 33.6초엔 아무 변화 없고 **54.5초**에 바뀐다
3. 49.5초에 큐 4 Chorus 1(후렴 첫 파랑)이 오는지 — 직전 기준이면 104.0초
4. 재생해도 큐 1 조차 안 걸리면(타임코드가 시퀀스를 안 움직이면) 그 자체가 발견이다 — 실행기 배정·Go 는 이번 승인 밖이므로 하지 않고 보고

큐별 예측표: `stage3_playback_prediction.txt` (의도 시각 / 직전 기준 해석 시 발사 시각 / 차이 박수)

## 6. 안 잰 것

- **재생**(B 전부, 발견 2): 콘솔에서 타임코드를 돌리지 않았다
- A8 런북 화면
- 쇼 복사본 저장 여부·활성 쇼 이름 — 응답기로 못 읽는다. 감독 확인(리드 전달)만 있다
- run2b 가 콘솔에 아무것도 저장하지 않았는지 — 취소 회신만 있다
- W 채널 이름 `ColorRGB_W` 는 앱 판독(`_w_capable_fids`) 결과이고 내가 채널 목록을 직접 읽지 않았다
- 큐 안의 값(밝기·색·포지션) — 응답기로 못 읽는다(계획 §8)
- 그룹 14 구성원 — 감독 육안 몫

## 8. 재쓰기 (2026-10-01) — 첫 쓰기 소실 뒤

| run | 내용 | 결과 |
|---|---|---|
| run10 | 읽기: 풀 스냅숏(2쪽까지) | run5(첫 쓰기 전)와 전 풀 동일 — 211·11 빔. 활성 쇼 = `Copilot_Test_20260928`(감독 확인, 리드 전달) |
| run11 | 실기 전부-거절 | 119줄, run3 `approval_request_1.txt` 와 **바이트 동일**(`cmp`) · 송신 `ClearAll` 1줄 |
| run12 | 실기 쓰기(run3 목록 고정, 리드 지시대로 재승인 없이) | 119/119 ok · SaveShow 송신 0(자동 1회 기록만) · 앱 되읽기 「검증 완료」 |
| run13·14 | 읽기: 쓰기 뒤 풀·큐 13개 속성 | A7 13/13(`judge_a7_rain_again.txt`) · C1 추가 211·11 뿐, 제거·변경 0(`c1_before_after_diff_again.txt`) |

- 판정 갱신: A6 PASS · A7 PASS · C1 PASS (첫 쓰기 판정은 그 쓰기에 대한 기록으로 남긴다)
- 쇼 저장: 앱에서 보내지 않았다. 감독이 콘솔에서 복사본에 Save Show 한다(감독 결정)

## 7. 콘솔에 남은 것

- 시퀀스 211 「Sequence 211」 큐 13개 · 타임코드 11 「Sequence 211 Timecode」. 이전 회차의 시퀀스 210·타임코드 9·프리셋 2.21~2.30 그대로
- 🔴 쓰기 뒤 쇼 저장 안 함(리드·감독 지시). 앱의 자동 `SaveShow` 도 보내지 않았다(`skipped_saveshow=1`)
