# t459 — SPEC-LDDESIGN-001 M8 콘솔 문법 프로브 3종 (lane-1)

- 브랜치 `WT-console-syntax-probe` · 기준 `origin/main@ab1c12f9`
- 작성: 2026-09-27 · 코드 수정 0 (방출 계층 구현은 결과 보고 후 별도)
- 감독 확인(이 세션 터미널, AskUserQuestion): 시험 시퀀스 **900**, 대상 **Robin Spiider 521·522**
- 도구: 쓰기 `tools/console_probe.py exec:` · 읽기 `.moai/reports/t431/probe_t431.py` (`state`/`introspect`/`props`). 원문은 `run*.txt`
- 판정은 AC-022~024 규정대로 **PASS/FAIL 이 아니라 관측치**다.

## 0. 요약

| 대상 | 문법 | 판정 | 근거 |
|---|---|---|---|
| Release | `Set Cue <n> Sequence <s> Property 'Release' 1` | 🟢 **확정** | 되읽기 `RELEASE false→true` + 감독 화면 Release `Yes` |
| Block | `Block Sequence <s> Cue <n>` / `Unblock …` | 🟢 **확정(화면)** | 트랙 시트 Q2 Dimmer 흰색 → Unblock 뒤 자홍. 대조 Q5 는 자홍 그대로 |
| 큐 전체 딜레이(Position) | `Set Cue <n> Part 0 Sequence <s> Property 'Preset2Delay' <초>` | 🟢 확정(기존 C6 재확인) | 되읽기 `1.0→1.5`, 화면 Duration `1.5` |
| 기구별 순차 딜레이 | `Fixture … ; Attribute 'Pan' At <v>` → `Attribute 'Pan' At Delay 0 Thru 2` → `Store` | 🟡 **저장은 확정, 나뉨은 미확인** | 되읽기 `INDIVDELAY=2.0`·`DURATION=2.0`(대조 Q8 0.0), 화면에 주황 타이밍 표시. 재생 시 팬이 안 나가 521/522 시차는 못 봤다 |
| 파트 X축 딜레이 | `…Property 'DelayToX' …` | 🔴 거절 | `Illegal property` (큐·Part 0 양쪽, 띄어쓰기 변형 포함) |
| MIB 설정 | `MIBPreference` 값 / `MIBFade`·`MIBDelay` | 🔴 거절 | 값 `Early/Late/None/Prefer/Mark` → `Illegal value`, 속성 둘 → `Illegal property` |
| Mark / MIB 이동·정착 초 | — | ⚪ **미측정** | 재생에서 팬이 나가지 않아 관찰 불가. 잠정값 1.5+0.5초 그대로 |

## 1. 착수 전 판독 (읽기 전용)

- 시퀀스 풀 전수: 17개 `[1..15, 1999, 2000]`, `truncated:false` (`run1_seq_pool.txt`)
- `Sequences/900` → `path segment not found: '900'` · 양성 대조 `Sequences/2`·`/1999` 는 큐 목록이 나옴 → 번호로 찾는 경로가 맞다 (`run2`)
- 속성 이름 판독 (`run3`~`run6`):
  - Cue: `RELEASE`(bool) · `ASSERT` · `MIBPREFERENCE`(기본 `Normal`) · `TRIGTYPE` …
  - Part(195개): `PRESET2DELAY` · `INDIVDELAY` · `INDIVDURATION` · `DELAYFROMX/DELAYTOX` · `MIBFADE/MIBDELAY/MIBMULTISTEP` …
  - Sequence: `TRACKING` · `SEQUMIB`(기본 `Enabled`) · `SEQUMIBMODE`(`None`) · `RELEASEFIRSTCUE`
  - `DELAYTOX`·`MIBFADE`·`MIBDELAY`·`CUEFADE`·`STOREDDATA` 는 **읽기 불가**(`property not readable`)
  - 기본 파트는 **Part 0** (`PART=0` 되읽기). `Part 1` 로 가리키면 `Illegal object`

## 2. 🔴 날조 대조군 — `OK` 는 키워드 명령의 증거가 아니다

| 명령 | 응답 | 뜻 |
|---|---|---|
| `Blorkify Sequence 900 Cue 1` (900 없음) | `Illegal object` | 대상이 없어서 — 키워드 판별 아님 |
| `Set Cue 4 Sequence 900 Property 'NoSuchPropT459' 1` | `Illegal property` | **속성 경로는 판별력 있음** |
| `Set Cue 3 … 'MIBPreference' 'Blorp'` | `Illegal value` | **값도 판별력 있음** |
| `Blockzz Sequence 900 Cue 2` | **`ok:true "OK"`** | 가짜 키워드도 통과 |
| `Attribute 'Pan' At Delayzz 0 Thru 2` | **`ok:true "OK"`** | 가짜 키워드도 통과 — 게다가 그 뒤 저장한 Q6 에 팬 60 이 **안 들어갔다**(트랙 시트 Pan `center` 자홍) |

→ `Set … Property` 계열은 콘솔 응답으로 판정할 수 있다. 키워드·프로그래머 명령은 **화면이나 되읽기로만** 판정한다. 방출 계층이 `OK` 를 성공으로 읽으면 안 된다.

## 3. 트랙 시트 관측 (감독 스크린샷, 이 세션)

| 큐 | 521/522 Dim | Pan | Tilt | 비고 |
|---|---|---|---|---|
| Q1 on center | open 청록 | center 청록 | center 청록 | Release `<Yes>`(시퀀스 기본값) |
| Q2 pan30 only (**Block**) | open **흰색** | 30.00 청록 | center 청록 | Duration 1.5 (Preset2Delay) |
| Q2 — **Unblock 뒤** | open **자홍** | 30.00 청록 | center 청록 | 이 칸만 바뀜 |
| Q3 dark | closed 초록 | 30.00 자홍 | center 자홍 | |
| Q4 on pan-30 | open 청록 | -30.00 청록 | center 청록 | Release **Yes** |
| Q5 pan0 (대조, Block 안 함) | open 자홍 | center 청록 | center 흰색 | |
| Q6 (Delayzz 오염) | open 자홍 | **center 자홍** | center 흰색 | 팬 60 저장 실패 |
| Q7 pan60 + At Delay 0 Thru 2 | open 자홍 | **60.00 청록 + 주황 표시** | center | Duration **2** |
| Q8 pan-60 (대조, 딜레이 없음) | open 자홍 | -60.00 청록 | center | Duration 0 |

색 해석(자홍=이어받은 값, 흰색=앞과 같은 값을 박아 둔 값)은 **grandMA3 관례를 아는 것**이지 여기서 잰 것이 아니다. 대신 Block→Unblock 한 칸 변화와 대조 Q5 로 판별했다.

## 4. 재생 관찰 — 팬이 나가지 않았다

- 1차 재생(Q1~Q8, `Attribute 'Dimmer' At 100` 으로 만든 큐): 3D 에서 **아무것도 안 보임**. 감독 지적 「딤머를 켠 게 맞아?」
- 대조: 프로그래머 `Fixture 521 Thru 522 ; At 100` → **둘 다 켜짐**. → Spiider 에서 `Attribute 'Dimmer' At 100` 은 불을 켜지 못하고 `At 100` 은 켠다(t442 와 같은 형태)
- 2차 재생(Q11~Q15, `At 100` 으로 다시 만듦, `Goto … Cue 11` 후 `Go+`): **켜지지만 팬은 움직이지 않음**(두 번 반복)
- 대조: 프로그래머에서 팬 -60→60→-60 → **3D 에서 두 대가 같이 움직임**(프로그래머에는 딜레이가 없으니 동시가 정상)
- → 3D·기구는 팬을 표시한다. **시퀀스 재생에서만 팬이 안 나갔다.** 원인은 재지 않았다(후보: `Goto`/`Go+` 로 부른 미배정 시퀀스의 Position 출력, 우선순위, 다른 재생의 점유 — 전부 미측정)
- 그래서 **순차 딜레이의 기구별 시차**와 **MIB 사전이동·이동/정착 초**는 관찰하지 못했다

## 5. 정리 — 만든 것 전부 삭제 후 되읽기

- `Off Sequence 900` · `ClearAll` · `Delete Sequence 900 /NoConfirm` → 전부 `OK`
- `Sequences/900` → `path segment not found: '900'`
- 시퀀스 풀 17개 `[1..15, 1999, 2000]` — **착수 전과 동일** (`run26` vs `run1`)
- `Selection COUNTTOTALSELECTED` = `0`
- 쇼 저장 0회. 시퀀스 900 밖의 대상에 Store·Delete 0회

## 6. 안 잰 것 (Gaps)

- 기구별 딜레이가 521=0초·522=2초로 **나뉘는지** — 저장은 되지만 재생에서 팬이 안 나가 못 봤다
- MIB(`SEQUMIB=Enabled`) 자동 사전이동이 일어나는지, 이동+정착 실제 초 — 미측정. plan.md §F 잠정값 교체 불가
- Mark 전용 문법 — `MIBPreference` 의 유효한 값을 하나도 찾지 못했다(시도 5개 전부 `Illegal value`). 값 목록을 읽는 경로가 없다
- 재생에서 팬이 안 나간 원인
- 색 규칙(자홍/흰색)의 공식 정의 — 관례로만 해석
- `Block` 이 Dimmer 외 다른 속성도 박는지 — Dim 칸만 봤다

## 7. 다음 카드에 권하는 것

1. 재생 출력 원인부터: 시퀀스 900 을 실행기에 배정해 `Go` 로 돌려 팬이 나가는지(대조: 프로그래머 이동은 확인됨)
2. 그 뒤 Q11→Q12 로 기구별 시차, Q13→Q14→Q15 로 MIB 초 측정
3. `MIBPreference` 값 목록 — 콘솔 도움말(`HelpLua` 류) 또는 GUI 드롭다운에서 읽기
4. 방출 계층은 키워드 명령의 `OK` 를 성공으로 치지 말 것(§2)
