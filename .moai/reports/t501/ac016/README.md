# t501 AC-016 준비 — 실기 감독 판정 2곡(Rain → 212/12, Club Diver → 213/13)

AC-LDRENDER-016(실기 감독 판정, ≥3점)을 위한 **읽기·오프라인 준비물**이다.
이 카드(에이전트)는 콘솔에 0건 접촉했다 — 레인이 아래 절차를 실기에서
실행한다. 감독·리드 결정(2026-10-02): t498 Rain 파일럿(시퀀스 211/타임코드
11)과 번호가 겹치지 않도록 Rain 은 시퀀스 212/타임코드 12, Club Diver 는
시퀀스 213/타임코드 13 을 쓴다. 지시문 형태는 t498 과 동일
(`"디자인 큐 시트, 시퀀스 <N>, 프리셋 21번부터, 타임코드 <M>"`) — 포지션
프리셋 21~30 은 이미 콘솔에 있다(`ac016_readonly_before.txt`).

## 이 폴더의 산출물

| 파일 | 용도 |
|---|---|
| `real_song.py` | t498 `real_console.py` 일반화. **실행하지 않았다** — 레인이 실기에서 돌린다 |
| `rehearse_song.py` | 가짜 콘솔(M7 능력/풀 패치) + 실제 DSP 리허설. 레인의 대조군을 미리 만든다 |
| `rehearse_rain_212/`, `rehearse_rain_212_run2/` | Rain 리허설 2회(결정성 확인) |
| `rehearse_clubdiver_213/`, `rehearse_clubdiver_213_run2/` | Club Diver 리허설 2회 |
| `classify_diff.py` | t498 `classify_diff.py` 일반화. 리허설 대 실기 전부-거절 목록 차이를 전량 분류 |
| `classify_diff_selftest_t498.txt` | 자가 시험 — t498 저장 쌍(아래 §3) 결과 |
| `verb_summary.py` | 명령 목록 파일의 동사·번호 요약(위험 동사·번호 이탈 확인) |
| `verb_summary_rain_212.txt`, `verb_summary_clubdiver_213.txt` | 위 스크립트를 두 곡 리허설 명령에 돌린 결과 |

## 1. 레인이 실기에서 돌릴 순서 (그대로, 번호만 곡마다 바꿔서 두 번)

변수: `<song>` = `Rain.mp3` 또는 `Club Diver.mp3`, `<seq>` = `212`/`213`,
`<tc>` = `12`/`13`, `<slug>` = `rain_212`/`clubdiver_213`.

```bash
# (a) 전부-거절 실기 승인 목록만 뜬다 — 쓰기 0, ClearAll 1줄만 송신(t497/t498 가 이미 그랬다)
uv run python .moai/reports/t501/ac016/real_song.py \
  "<song>" <seq> <tc> .moai/reports/t501/ac016/real_<slug>_denyall

# (b) 리허설(이미 만들어 둠, .moai/reports/t501/ac016/rehearse_<slug>/) 대 방금 뜬 실기 목록을 대조
uv run python .moai/reports/t501/ac016/classify_diff.py \
  .moai/reports/t501/ac016/rehearse_<slug>/approval_request_1.txt \
  .moai/reports/t501/ac016/real_<slug>_denyall/approval_request_1.txt

# (c) 실기 목록의 동사·번호 확인 — 리드 규칙(t498): 설명 안 되는 줄이 하나라도 있으면 쓰지 않는다
uv run python .moai/reports/t501/ac016/verb_summary.py \
  .moai/reports/t501/ac016/real_<slug>_denyall/approval_request_1.txt

# (d) STOP — 멈춘다. (b) 의 VERDICT 가 True(설명 안 되는 줄 0)이고 (c) 에
#     위험 동사(Store/Assign 밖)나 212/213·12/13·풀 2 의 21~30·풀 4 의
#     9~11·풀 21 의 7~8 밖의 번호가 없을 때만 다음으로 간다. 승인 후:
uv run python .moai/reports/t501/ac016/real_song.py \
  "<song>" <seq> <tc> .moai/reports/t501/ac016/real_<slug>_write \
  --approve .moai/reports/t501/ac016/real_<slug>_denyall

# (e) 읽기 전용 재조회 — 쓰기가 콘솔에 남았는지, 다른 번호가 안 건드려졌는지 확인
uv run python .moai/reports/t498/probe_readonly.py \
  state:ShowData/DataPools/Default/Sequences \
  state:ShowData/DataPools/Default/Sequences@15 \
  state:ShowData/DataPools/Default/Timecodes

# (f) 재생 준비 — §4 참조. "Go+ Sequence <seq>" 는 **콘솔에서 감독이 손으로**
#     누른다(앱/게이트 경로가 아니다 — t498 이 실제로 쓴 길, 아래 §4).
```

## 2. 8곡 최종 오프라인 판정(M7, `.moai/reports/t501/measure_m7_dsp_8songs.py`)과 대조

이 카드의 `rehearse_song.py` 는 그 스크립트의 `_rehearse_one`(= M7 능력/풀
몽키패치 + 실제 DSP)를 **그대로 import 해서 재사용**했다 — 새 리허설 로직을
안 짰다. 아래 값은 두 곡 모두 `measure_m7_dsp_8songs.json`(M7 8곡 전수
측정, 커밋 `c0375e7b`)의 해당 곡 행과 일치한다(소수 둘째 자리까지, DSP
초만 예외 — 측정마다 달라지는 wall-clock 값이다):

| 곡 | BPM | 구간 | 색 수 | 색변화 | LIT<3/전체 | fx 요청/힌트/송신 | 비액센트 effect>0 위반 | 액센트 상승 | 게이트 경고 |
|---|---|---|---|---|---|---|---|---|---|
| Rain (seq212/tc12) | 76.0135 | 12 | 2 | 5 | 0/13 | 0/11/0 | 0/12 | 1/1 | **YES**(효과 요청 0건 · 페이저 제안 11큐 → 송신 효과 줄 0) |
| Club Diver (seq213/tc13) | 139.6748 | 13 | 3 | 5 | 0/14 | 12/12/11 | 0/13 | 1/1 | no |

카드의 5개 오프라인 완료 조건(M7.md §"카드의 5개 오프라인 완료 조건"과
같은 기준) — 두 곡 모두 ① 색 2~3 ✓ ② 색변화≥1 ✓ ③ 모든 큐 LIT≥3 ✓
⑤ 비액센트 effect=0 ✓. ④(fx 요청곡 송신≥1)는 Club Diver ✓, Rain 은 설계
층 자체가 효과를 요청하지 않아(fx_requested=0) **비해당**(송신 실패가
아니다 — M7.md 와 같은 판단, Rain 은 t498 때도 같았다). **종합: 두 곡 다
PASS(Rain 은 ④ vacuous)**. 전문: `rehearse_rain_212/offline_checks.json`,
`rehearse_clubdiver_213/offline_checks.json`.

※ 위 "게이트 경고"는 **기계 신호**(송신 효과 줄 0건이라는 사실)이지 연출
품질 판정이 아니다 — t498 판정서 §0/§4(리드 지시 2026-10-01)가 분명히
한 구분: 기계 동작이 전부 맞아도 연출은 별개로 감독이 판정한다. 이 ②번
항목이 바로 AC-016(실기 감독 판정) 의 몫이다.

## 3. `classify_diff.py` 자가 시험 (t498 저장 쌍)

```bash
uv run python .moai/reports/t501/ac016/classify_diff.py \
  .moai/reports/t498/run1_fake_rain_1/console_commands_approved.txt \
  .moai/reports/t498/run3_rain_real_denyall/approval_request_1.txt
```

결과(`classify_diff_selftest_t498.txt`)는 t498 당시 산출물
`.moai/reports/t498/run3_classify_diff.txt` 와 **바이트 동일**
(`diff` 종료 코드 0으로 확인) — 리허설 107줄 대 실기 119줄, 차이 12줄 전부
`ColorRGB_W` 줄(기구 28대), `VERDICT ... True`. 로직을 한 글자도 안 바꿨다는
증거다.

## 4. 재생 준비 — `Go+ Sequence <N>` 은 어떻게 쏘는가

t498 판정서(`.moai/reports/t498/verdict.md` §5 "무엇이 재생을 움직이는가")가
실측·판독한 사실 그대로 옮긴다 — 추측 0건:

- **t498 이 실제로 쓴 길**: 재생은 **콘솔에서 감독이 손으로** 시작했다
  (`Go+ Sequence 211` + `Rain.mp3` 를 손으로 동시 재생). 이 카드가 원격
  `Go Timecode`/타임코드 재생 경로를 대신 쓴 적은 없다 — 저장소 기록상
  그 경로의 효과는 **미증명**이라고 verdict.md 가 명시한다
  (`docs/research/ma3-effects/14-musicsync-m3a-timecode-probe-run2.md`
  "2회차 정정" 인용).
- **앱에 있는(쓰지 않은) 길**: `server/web/PROTOCOL.md`(§Message Types)에
  `panel_execute` 메시지가 있다 — `target_kind: "sequence", target: <N>` 을
  보내면 `gate.screen()` 을 거쳐 `Go+ Sequence <N>` 을 쏜다
  (`server/web/panel.py` `PANEL_GO_VERB = "Go+"`, `playback_command("Go+",
  "sequence", N) == "Go+ Sequence N"`). **t498 은 이 경로를 쓰지 않았다** —
  t498 산출물 전체(`run*.stdout.txt`, `events.json`)에 `panel_execute` 가
  한 번도 안 나온다(grep 확인). 두 길을 섞지 마라 — 이 카드는 어느 쪽을
  쓸지 결정하지 않는다, t498 이 쓴 길만 옮긴다.
- 타이밍 판별 지점(t498 §5 재생 절차 그대로, 곡마다 큐 시각은 다르다 —
  `rehearse_<slug>/approval_request_1.txt` 의 `Set Cue N Sequence <seq>
  Property 'TrigTime'` 줄에서 각 곡의 실제 값을 읽어라): 첫 전환이 의도한
  시각에 오는지(절대 시각 해석) 대 직전 큐 기준 해석 시의 시각을
  나란히 적어 두고, 재생하며 어느 쪽인지 확인한다 — t498 의 큐 3 하나
  관측(33.6초)은 절대 시각 해석과 일치했다(반증된 가설은 verdict.md §발견2).

## 5. 안 잰 것 (이 카드가 그대로 남긴 것)

- **콘솔 접촉 0건** — 위 §1 전부는 레인이 실행한다. 이 README 의 번호(212/
  213, 12/13, 풀 2 의 21~30, 풀 4 의 9/10/11, 풀 21 의 7/8)는 전부
  `ac016_readonly_before.txt`(2026-10-02 읽기 전용 재조회) 기준이다 —
  레인이 (a) 를 돌리는 시점에 다시 비어 있는지는 **그 시점에 다시
  확인해야 한다**(번호 할당 경쟁조건, M6/M6c 가 이미 경고한 그대로).
- Club Diver 의 정확한 큐별 TrigTime(절대/직전-기준 두 해석의 초 단위
  차이표)은 레인이 (a) 실행 뒤 `playback_prediction.py` 류를 Club Diver
  에 맞춰 돌려야 한다(이 카드는 그 스크립트를 일반화하지 않았다 — t498
  원본은 Rain/시퀀스 211 상수를 하드코딩했다).
- `panel_execute` 로 재생하는 것이 `Go+ Sequence N` 을 손으로 누르는 것과
  **같은 효과**인지는 미증명 — 코드 경로가 같은 명령 문자열을 만든다는
  것만 읽었다(정적 판독), 실기로 두 길을 비교한 적은 없다.
