# 이 채널이 무엇을 답하고 무엇을 안 답하는가 (2026-09-02)

> **한 자리에 모은 이유.** 아래 넷은 각각 다른 카드가 다른 날 실측했는데, 전부
> 「응답기 채널로 무엇을 알 수 있나」라는 한 질문의 답이다. 흩어져 있으면 다음
> 사람이 **이미 답이 있는 것을 다시 재거나, 없는 것을 있다고 읽는다** — 오늘
> 하루에만 그 두 형태가 각각 한 번씩 났다.
>
> 측정 조건: onPC · 응답기 **1.6.3** · `osc.udp://127.0.0.1:8000` · 회신 **9005**.
> 전부 **콘솔 쓰기 없이** 잰 값이거나, 쓰기가 있었던 경우 그 사실을 각 항에 적었다.

관련 판정서: `.moai/reports/t237` · `t248` · `t255` · `t261`

---

## 1. 프로그래머 점유는 이제 **읽힌다** — 다만 필드를 골라야 한다

```
prop Selection COUNTTOTALSELECTED     0 -> 1 -> 0     (Fixture 501 쏘고 Clear)
prop Selection COUNTFULLYSELECTED     0 -> 1 -> 0
prop Selection COUNT                  안 움직임
prop Selection ACTIVE                 안 움직임
state Selection childCount            안 움직임
```

🔴 **한동안 「이 채널은 프로그래머를 못 비춘다」로 알려져 있었는데, 그건 틀린
필드를 봤기 때문이다**(t246 이 `childCount` 를 봤고 t248 이 반증했다).
채널은 처음부터 비추고 있었다.

**쓸 때 주의**

- 판별자는 `COUNTTOTALSELECTED` 다. `childCount`·`COUNT`·`ACTIVE` 는 선택에 안 움직인다
- ⚠️ **「죽은 필드」로 읽지 마라** — 안 움직이는 것은 관측이고, **무엇에 움직이는지는
  아무도 안 쟀다**
- 응답기 **1.6.3** 이 `ROOT_ALIASES` 에 `programmer`·`programmerpart` 를 실어서 열렸다
  (1.6.2 까지는 `path segment not found`)
- `ProgrammerPart` 는 `NAME`·`COUNT`·`MEMORYFOOTPRINT` 만 답한다 —
  `OWNDATAPRESENT`·`ACTIVE` 는 **not readable**

## 2. `Fixture <n>` 은 **FID** 를 겨눈다 — 슬롯이 아니다

```
Fixture 501   -> exec ok        · COUNTTOTALSELECTED 0 -> 1
Fixture 27    -> Illegal object · 되읽기 전후 변화 0
```

FID 27 은 이 쇼에 없고 **슬롯** 27 은 실재한다. 슬롯을 겨눴다면 27 이 통했을 것이다.

🔴 **덤으로 확정된 것 — 콘솔이 피연산자를 검증한다.** 그래서 `Fixture <n>` 계열에
한해 `exec: ok` 는 이전보다 강한 신호다. **다른 명령 계열로 일반화하지 마라** —
꼬리 키워드 축에서는 `ok` + 무효과가 관측된 적이 있다(t215 C2).

## 3. `Clear` 는 **단계 명령**이다 — 선택과 값이 두 번에 나뉜다

정본 룰북 `server/rulebook/assets/v2.4.2/00_grammar.md:57-58`:

```
| Clear    | Step programmer clear (selection -> values) |
| ClearAll | Clear the whole programmer                  |
```

`server/orchestrator/tools.py` 의 dedupe 면제 주석도 독립으로 같은 말을 한다
(`# step clear (selection -> values)`).

| 문형 | 범위 | 안전 게이트 |
|---|---|---|
| `Off Fixture <fid>` | 한 대, 가장 정밀 | 🔴 **승인 필요** — `Off` 가 invoking 동사이고 픽스처엔 확장할 본문이 없어 hold 된다 |
| `Clear` | 한 단계 (선택 → 값) | 통과 (`safe`) |
| `ClearAll` | 프로그래머 전체 | 통과 (`safe`) — 감독이 손으로 쌓은 것까지 지운다 |

**쏜 것을 되돌릴 때는 `Clear` 를 두 줄 보낸다.** 한 번들에 두 줄로 — `Clear` 는
dedupe 면제라 둘 다 산다(`"Clear Clear"` 한 문자열은 면제가 안 걸린다).

🔴 **여기 함정이 하나 있다.** 1회째 `Clear` 뒤 **선택은 비고 값은 남는데**,
§1 의 판별자 `COUNTTOTALSELECTED` 는 **그때 이미 0 을 답한다.** 즉
**「값이 남은 위험한 상태」와 「완전히 빈 상태」가 같은 0 으로 나온다.**
값 축을 읽을 필드는 §1 대로 아직 없다.

## 4. 큐 **내용**은 이 채널이 안 준다 — 완전 열거로 확인했다

```
introspect DataPool/Sequences/3/4     class=Cue   total=23   truncated=false  paging=complete
introspect DataPool/Sequences/3/4/1   class=Part  total=195  truncated=false  paging=complete
```

`Cue` 23필드 어디에도 내용 필드가 없다. **「못 찾았다」가 아니라 「다 세어 봤는데 없다」**다.

`Part` 195필드 중 내용 후보 넷:

```
STOREDDATA     property not readable
PRESETDATA     ""            <- 데이터가 있는 것이 확실한 자리에서도 빈 문자열
REFERENCES     ""            <- 〃
SELECTIONDATA  table: 0x…    <- 🔴 빈값이 아니라 **Lua 테이블 주소**
DEPENDENCIES   table: 0x…    <- 〃
양성 대조군 NAME = 'Q010 INTRO 화사' · OWNDATAPRESENT = true · MEMORYFOOTPRINT = 4580
```

🔴 **빈 문자열과 테이블 주소는 다른 사건이다.** 빈 문자열은 「이 채널이 그 축을
안 잰다」이고, 테이블 주소는 **「값은 거기 있는데 응답기가 문자열로 안 풀었다」**다.
후자는 **제거 가능한 미구현**이다 — 다만 그 테이블 안에 무엇이 들었는지는 **안 쟀다**.

---

## 이 채널을 쓸 때의 계기 규율 넷

1. **음성 대조군을 먼저 쏴라.** 날조 경로(`…/ZZZNOTREAL9`)가 `path segment not found`
   를 답하는 것을 본 뒤에야 그 뒤의 `ok` 가 증거로 선다
2. **양성 대조군을 판독 계기에 박아라.** 매 스냅샷에 반드시 값이 있는 필드(`NAME`)를
   같이 읽어라 — **계기가 죽어서 0 을 답하는 것과 살아서 0 을 답하는 것이 같은 출력**이다
   (t248 에서 망가진 파서가 우연히 정답과 같은 글자를 냈다)
3. **자식 목록은 잘린다.** `childCount` 와 수신 개수를 대조하고 `truncated` 를 읽어라.
   `Sequences/3` 는 childCount 21 인데 첫 창이 **13만** 준다 — 페이징 없이 세면
   18큐를 13으로 센다
4. **`exec: ok` 는 효과의 증거가 아니다.** 판정은 되읽기로 한다 (§2 가 유일한 예외이고,
   그것도 `Fixture <n>` 계열 한정이다)

## 안 잰 것

- `COUNT`·`ACTIVE` 가 **무엇에** 움직이는지 (선택에는 안 움직인다는 것만 안다)
- `COUNTTOTALSELECTED` 와 `COUNTFULLYSELECTED` 의 차이 (부분 선택에서 갈릴 것으로 보이나 미측정)
- `SELECTIONDATA`·`DEPENDENCIES` 테이블의 **내용**
- 1회째 `Clear` 뒤 값이 실제로 남는지 (룰북 문면 근거이고 이 콘솔에서 미측정 —
  재려면 값을 실어야 하고 그것은 새 승인이다)
