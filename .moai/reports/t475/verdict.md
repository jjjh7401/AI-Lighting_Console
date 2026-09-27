# t475 판정서 — M8 사전 리허설: Rain 을 대화 길 끝까지 돌려 콘솔 명령을 파일로 떴다

- 카드: t475 · SPEC-LDDESIGN-001 M8 · lane-2
- 브랜치: `WT-m8-rehearsal`, 기준 `origin/main` 59440ec0 (차이 `0 0` 확인)
- 콘솔 쓰기: **0** — 명령은 in-process 가짜 콘솔(`server/tests/test_safety_gate.py` `FakeConsole`)이 받았다
- 제품 코드 변경: **0** — 이 카드의 산출물은 `.moai/reports/t475/` 아래 파일뿐이다
- 판정: **확인 ①~⑥ 측정 완료 · 새 결함 1건 발견(🔴 t474 전에 처리 필요)**

## 0. 감독용 요약

Rain 을 실제 오디오부터 대화 길 그대로 돌렸다. 순서는 업로드 → 분석 → 확인 → 인터뷰 → 승인 → 반영이다.
콘솔로 나갈 명령을 줄 하나 빠짐없이 파일로 남겼다. 같은 입력으로 세 번 돌렸고, 세 번 모두 바이트까지 같았다.

그런데 **승인 카드에 뜬 명령은 107줄인데 콘솔로 실제 나간 명령은 75줄**이다. 실행 경로의 「같은 명령은 한 지시
안에서 한 번만 보낸다」는 중복 제거가 32줄을 건너뛰었다. 대부분은 콘솔이 앞 큐 값을 이어 받는(트래킹) 덕에
무대에 차이가 없다. 하지만 **6곳은 무대가 달라진다.**

- Verse 3·Verse 4 의 드롭 앞 어둠(25%)이 빠져 **100% 로 나간다**. 백 그룹도 20% 가 아니라 80% 다.
- Chorus 6 의 Ring In 포지션이 빠져 **앞 큐의 Fan Out 에 머문다**. 런북 화면에는 Ring In 으로 보인다.

회신 문구는 「요청한 명령을 모두 실행했습니다」이고 readback 도 통과한다. 즉 **아무 신호 없이 틀린다.**
t474 가 이대로 실기에 들어가면, 콘솔 리드백은 75줄과는 맞지만 승인한 연출과는 어긋난다.

## 1. 어떻게 돌렸나

| 단계 | 실제 경로 | 대역(가짜)인 것 |
|---|---|---|
| 오디오 | `src/sample music/Rain.mp3` (주 체크아웃의 비추적 파일, sha256 `c3b78bbb…5b70`) | — |
| 분석 | `ChatSession.upload_song_audio` → `analyse_song_audio` (실제 DSP) | 확인 카드 답 「확인」(전 구간 채택) |
| 디자인 | `run_instruction("디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9")` — 구간을 적지 않아 확정 구간을 쓴다 | 인터뷰 답 6개(writegate 시험과 같은 답), 레이어 매핑 카드 「이 매핑 사용」, 리뷰 카드 「승인」 |
| 반영 | `_song_finalize` → 실제 `run_commands` (게이트·중복 제거·감사 로그 포함) | 게이트 승인 포트(항상 승인), 좌표 판독(기구 20·26 두 대), 그룹 풀(t379 실측 이름 18개에 **번호를 지어 붙임**), 포지션 풀 21~30 |
| 되읽기 | `_song_readback_requests` 의 실제 검증기 | 가짜 콘솔이 **받은 명령 문자열**에서 Store/Set 을 파싱해 돌려준다 |

- 스크립트: `rehearse_rain.py` (조립기 산출도 가로채지 않고 기록만 한다)
- 분석 결과는 8곡 기준선(`server/tests/fixtures/pilot_baseline.json` Rain)과 같다. 12구간, D 값
  2·3·3·5·5·3·5·5·5·4·5·1, BPM 76.01(측정). 구간이 8마디(≈25.3초)를 두 번 채우지 못해 쪼개지지 않았다.

## 2. 확인 항목 판정

### ① 명령 수 · Sequence/Cue/Timecode 줄 — 측정 완료

| 종류 | 승인 카드 | 콘솔로 나감 |
|---|---:|---:|
| 전체 | 107 | **75** |
| `Store Sequence 210 Cue …` | 13 (큐 1~12 + 11.5) | 13 |
| `ClearAll` | 13 | 13 |
| Timecode (`Store Timecode 9` · `Set Timecode 9 Property 'Name'` · `Assign Sequence 210 At Timecode 9`) | 3 | 3 |
| `TrigType 'Time'` / `TrigTime` | 13 / 13 | 13 / 13 |
| 값 줄(`Fixture …` · `Group …`) | 51 | **19** |
| `ChangeDestination Root` | 1 | 1 |

- 명령: `wc -l`, `grep -c` 로 두 파일을 셈 (`run3/console_commands_approved.txt` · `run3/console_commands_sent.txt`)
- 저장·타이밍 줄은 한 줄도 빠지지 않았다. 빠진 32줄은 전부 값 줄이다.

### ② 드롭 앞 어둠 · 블라인더 · 소수 큐 TrigTime — 줄은 나오지만 어둠은 첫 드롭에서만 산다

조립기 산출(`run3/bundle_cues.json`)에는 드롭 앞 어둠이 세 곳 있다. Verse 2 는 70→25, Verse 3 는 70→25,
Verse 4 는 90→25 이다. 콘솔로 나간 명령에서 산 것은 **Verse 2 하나**다.

```
Fixture 20 + 26 ; Attribute 'Dimmer' At 25          ← 큐 3 Verse 2 (나감)
Group 3 ; Attribute 'Dimmer' At 20
Group 13 ; Attribute 'Dimmer' At 80                 ← 큐 11 Chorus 6 블라인더 켬
Store Sequence 210 Cue 11 'Chorus 6' CueFade 0.394667
Group 13 ; Attribute 'Dimmer' At 0                  ← 큐 11.5 복귀 큐가 끔
Store Sequence 210 Cue 11.5 'Chorus 6 Return' CueFade 0
Set Cue 11.5 Sequence 210 Property 'TrigTime' 180.64
```

- 블라인더: Chorus 6 에서 켜지고 11.5 에서 꺼진다. 11.5 의 TrigTime 180.64 는 Chorus 6 의 179.061 보다
  1.579초 뒤다. BPM 76.01 에서 2박이 1.5787초이므로 t462 의 2박 상한과 맞다.
- Finale 블라인더는 켜지지 않았다. 사유는 `blinder_six_row_absent`(Finale 은 §6 표의 행이 아님)이고,
  arc_notes 와 회신에 남았다. t462 판정서가 적은 동작 그대로다.
- 조립기 경고 1건: `L9 큐 11.5: snap fade (0s) used outside an accent/hit/drop/button cue`.
  복귀 큐의 0초 페이드를 린트가 경고한다. 막지는 않는다.

### ③ t471 live_move 경고 건수(실곡 첫 측정) — **0건 (MIB 발화 0건이라서)**

- 조립기 산출 12+1 큐의 `mib.premove` 는 전부 `False` 이고, 런북 payload 의 `live_move` 는 전부 `None` 이다.
- 이유: Rain 에는 불이 꺼진(밝기 0) 큐 다음에 켜지는 큐가 없다. 가장 어두운 곳은 드롭 앞 25% 다.
  그래서 사전이동 자체가 생기지 않고, 경고를 따질 대상이 없다.
- 즉 「0건」은 **경고가 필요 없다는 증명이 아니라, 이 곡에서는 검사 대상이 0개였다**는 뜻이다(§4).

### ④ 후렴 주색 동일(REQ-030) — PASS

- 후렴 6개(Chorus 1~6)와 Finale 의 팔레트는 모두 `['블루', 'warm white']`, 주색은 `블루`다.
  절(Verse)은 `['블루', 'cyan']` 로 주색이 같다.
- 명령 쪽 주색 줄은 전부 `ColorRGB_R 5 · G 20 · B 100` 한 가지다. 큐 2~12 의 색 줄 11개는 중복 제거로
  빠졌다. 하지만 값이 큐 1 과 같아 트래킹으로 같은 색이 유지된다. 무대 차이 0건(`tracking_diff.txt`).

### ⑤ 8곡 게이트 75/29/0 — PASS

- 명령: `uv run python .moai/reports/t444/gen_gates_8songs.py` → `gates_8songs.txt`
- 관측: `집계: PASS 75 · n/a 29 · FAIL 0`
- 보강: `uv run pytest server/tests/test_concept_gates.py -q` → `22 passed`

### ⑥ 가짜 콘솔로 반영 경로 통과 — 통과, 단 **승인한 명령 전부가 나간 것은 아니다**

- 게이트 승인 1건, `run_commands` 디스패치 1건(`song-design-reviewed-bundle`) 기록.
  회신은 「readback 검증 완료: DataPool/Sequences/210, DataPool/Timecodes/9」다.
- 명령 결과 상태: `executed_ok 75 · skipped_already_executed 32` (`run3/events.json` 의 `chat_response`)
- 되읽기 통과의 뜻은 좁다. 가짜 콘솔은 자기가 받은 명령에서 큐와 TrigTime 을 돌려줄 뿐이다. 그래서 「명령이
  검증기가 기대하는 값을 담고 있다」까지만 증명한다. 게다가 검증기는 TrigType/TrigTime 만 보고
  **밝기·포지션 값은 보지 않는다**. 그래서 아래 결함이 되읽기를 통과한다.

## 3. 🔴 새 결함 — 승인한 값 줄이 중복 제거로 빠진다

**어디서**: `server/orchestrator/tools.py` 2622~2645행 `run_commands`. 한 지시 안에서 이미 성공한 명령
문자열과 같은 줄은 `skipped_already_executed` 로 건너뛴다. 면제는 `Clear`·`ClearAll`·값 없는 선택
(`Fixture 3`) 뿐이다(`_is_programmer_state`, 1063행).

**왜 곡 큐가 걸리나**: `position_cue_bundle`(`server/spatial/mib.py` 152행)은 이렇게 적었다. 「모든 값 줄은
Fixture 선택 접두를 달아 **글자가 유일하게 남도록** 한다」. 하지만 큐 번호는 Store 줄에만 있고 값 줄에는
없다. 그래서 두 큐가 같은 값을 쓰면 값 줄 글자가 같아진다. `Fixture 20 + 26 ; Attribute 'Dimmer' At 25`
가 큐 3·6·10 에 똑같이 들어가고, 큐 6·10 의 것은 「이미 실행됨」이 된다.

**무대 차이**: 승인 카드 명령과 콘솔로 나간 명령을 트래킹으로 풀어 큐별 값을 비교했다
(`tracking_diff.py` → `tracking_diff.txt`).

| 큐 | 대상 | 의도(승인) | 실제(콘솔) |
|---|---|---|---|
| 6 Verse 3 | Fixture 20+26 Dimmer | 25 | **100** |
| 6 Verse 3 | Group 3(BACK) Dimmer | 20 | **80** |
| 10 Verse 4 | Fixture 20+26 Dimmer | 25 | **100** |
| 10 Verse 4 | Group 3(BACK) Dimmer | 20 | **80** |
| 11 Chorus 6 | 포지션 | 2.30 Ring In | **2.26 Fan Out** |
| 11.5 Chorus 6 Return | 포지션 | 2.30 | **2.26** |

빠진 32줄 가운데 나머지 26줄은 앞 큐 값과 같아 트래킹으로 무해하다.

**왜 지금까지 안 보였나**: t462 는 명령 생성기(`_reviewed_song_commands`)를 직접 불러 명령을 찍었다
(`probe_a_console.py`). 이 방식은 실행 경로의 중복 제거를 거치지 않는다. 합성 곡도 드롭이 여러 번이었지만
실행 경로에 태운 적이 없었다. 이번에 처음으로 **생산자(생성기)가 아니라 소비자(실행 경로)까지** 탔다.

**t474 에 주는 영향**: t474 가 오늘 main 으로 실기에 들어가면 콘솔은 75줄을 받는다. 리드백은 75줄과
일치하므로 **대조는 통과하지만 연출은 틀린다.** 두 가지 중 하나를 권한다.

1. **권장**: t474 전에 결함 카드를 먼저 닫는다. 곡 큐 번들의 값 줄이 중복 제거에 먹히지 않게 하는 수정이다.
   고칠 자리(생성기 쪽이냐 실행기 쪽이냐)는 이 카드 범위 밖이라 판단하지 않았다.
2. t474 를 그대로 간다면 대조 기준을 **두 파일**로 둔다. 콘솔이 받은 것은 `console_commands_sent.txt`,
   연출 의도는 `console_commands_approved.txt` 이고, 무대 차이 6곳을 알고 본다.

## 4. 안 잰 것

- **실기 콘솔**에는 아무것도 보내지 않았다. 문법·소수 큐 11.5 의 TrigTime·블라인더 그룹 반응은 t474 의 몫이다.
- **그룹 번호**는 지어낸 값이다(KEY=1 … BACK=3 … BLIND=13). 실기 번호가 다르면 `Group N` 숫자가 바뀐다.
  줄 수와 구조는 번호와 무관하다.
- **기구 목록**은 좌표 판독 대역이 준 두 대(fid 20·26)다. 실기 리그에서는 `Fixture …` 선택이 길어진다.
  줄 수는 같다. 중복 제거가 먹는 패턴(같은 선택 + 같은 값)도 같다.
- **포지션 풀**은 21~30 에 기본 포지션 10개가 연속으로 있다고 가정했다(writegate 시험과 같다). 실기 풀 배치는 재지 않았다.
- **페이저**는 콘솔에서 못 찾아 전부 미배정이다(회신에 명시). 페이저 줄이 있는 쇼파일에서는 명령이 더 늘고,
  같은 페이저가 반복되면 같은 중복 제거에 걸릴 수 있다. 재지 않았다.
- **live_move**: Rain 은 MIB 대상이 0개라 경고 경로 자체를 타지 않았다. 실곡에서 경고가 뜨는지는 여전히 미측정이다.
- **그룹 멤버십 겹침**(기구 20·26 이 Group 3 에 속하는가)은 콘솔에서 못 읽어(RG5) 무대 차이 계산에 넣지 않았다.
- **전체 시험 스위트**는 돌리지 않았다. 제품 코드를 바꾸지 않아서다. 게이트 시험 22개만 돌렸다.
- **인터뷰 답**은 writegate 시험과 같은 여섯 개로 고정했다. 다른 답(다른 팔레트·전환)의 명령은 재지 않았다.

## 5. 남은 위험

- 이 결함은 Rain 만의 것이 아니다. **같은 값이 두 번 나오는 곡은 모두** 걸린다. 드롭이 여러 번이거나,
  같은 포지션으로 돌아오거나, 같은 밝기로 돌아오는 곡이다. 첫 번째 뒤의 되돌림은 전부 사라진다.
- 회신 요약 「요청한 명령을 모두 실행했습니다」가 `skipped_already_executed 32` 와 함께 나온다.
  감독 화면에서 이 결함을 알아챌 신호가 없다.
- 런북 payload(`song_timeline`)는 조립기 값을 보여 준다. 그래서 Chorus 6 이 Ring In 으로 보인다.
  **화면과 콘솔이 다르다.**

## 6. 증거 파일

`.moai/reports/t475/`
- `rehearse_rain.py` — 리허설 드라이버
- `run3/console_commands_sent.txt` (75줄, sha256 `ac76de8b…1934`) — **콘솔이 받은 명령 원문, t474 대조 기준**
- `run3/console_commands_approved.txt` (107줄) — 승인 카드에 뜬 명령 원문(연출 의도)
- `run3/bundle_cues.json` — 조립기 산출(큐별 밝기·색·포지션·MIB·드롭 앞 어둠·블라인더)
- `run3/analysis.json` · `cards.json` · `replies.json` · `events.json` · `queries.txt` — 분석·카드 답·회신·이벤트(런북 payload 포함)·조회 경로
- `tracking_diff.py` · `tracking_diff.txt` — 무대 차이 6건
- `gates_8songs.txt` — ⑤
- 재현성: `sha_before_rerun.txt` 로 두 명령 파일의 해시를 고정한 뒤 다시 돌렸다. `shasum -c` 결과 둘 다 `OK` 다
  (같은 입력 3회 실행이 바이트 동일).
