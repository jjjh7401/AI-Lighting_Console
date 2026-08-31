# t204 2회차 — 같은 카드를 다른 레인이 독립으로 다시 잼

브랜치 `WT-fixture-type-split` · base `ba9ceaa` · 2026-08-31
**콘솔 쓰기 0건**(preview 전용) · 코드 변경 0 · 새 카드 0 · 처방 미실행

## 0-A. 🔴 이 문서의 자리 — 1회차를 대체하지 않는다

**같은 카드를 run 레인이 먼저 수행했고, 그 보고서가 이미 main 에 있다**
(`.moai/reports/t204/verdict.md` · PR #250 · `a649823`). 리드는 그 레인이
「20분째 파일 변경 0건, 죽었거나 막혔다」고 판단해 나에게 재배차했는데,
**그 전제가 틀렸다 — 레인은 산출물을 냈고 머지까지 끝나 있었다.**

🔴 **그리고 나는 착수할 때 그 파일이 이미 있는지 안 보고 `>` 로 덮었다.**
git 에 남아 있어 손실은 없고(`ba9ceaa` 에서 sha256 `42adb26e…` 로 바이트 동일 복원),
규약 §5 —「`.moai/reports/` 아래는 그 시점 기록이다 — 정정 대상이 아니라 고지 대상」—
에 따라 1회차 문서를 되돌리고 이 문서를 **별도 파일**로 분리했다.
**증거 경로에 쓰기 전에 그 자리에 무엇이 있는지 먼저 봐야 했다.**

두 문서는 대체 관계가 아니다. **결론은 일치하고, 각자 상대가 안 잰 것을 갖고 있다.**

### 두 회차가 일치하는 것 (독립 측정, 계기가 서로 다름)

| 항목 | 1회차 | 2회차(이 문서) |
|---|---|---|
| `type_unresolved` | 0 | 0 |
| 타입 해석 | 8종 전부 | 8종 전부, `unresolved: []` |
| `already_patched` | 62 | 62 |
| `mode_unresolved` | 24 | 24 |
| 합계 | 86 | 86 |
| 판독 완전성 | `complete_enough_to_judge_absence: True` | 같음 + `missing_count: 0` |
| 가림 없음 | `_occupancy_skip` 이 `console_type` 을 인자로 받는다 | 호출 자리 `:571` 실측 |

**두 레인이 다른 근거로 같은 결론에 도달했다.** 특히 「가림 없음」은 1회차가 시그니처로,
2회차가 호출 자리로 각각 확인했다 — 서로의 대조군이 된다.

### 1회차가 나보다 나은 것 — 채택한다

**정확한 버전 문자열을 얻는 계기**를 1회차가 갖고 있었다.
나는 `introspect` 회신의 `offset` 에코로 **「1.6.2 이상」**까지만 판정했는데,
1회차는 `responder_roundtrip --skip-exec` 로 ping 회신에서 버전을 직접 읽었다.

**그 값을 릴레이하지 않고 내가 다시 쟀다:**

```
uv run python -m server.tools.responder_roundtrip --listen-port 9005 --skip-exec --wait 5
  [PASS] ping: ok
         live version=1.6.2 plugin=CopilotResponder
  result: PASS
```

**`1.6.2` 확정.** 아래 §1 의 「1.6.2 이상까지만 주장한다」는 이 측정으로 **대체된다** —
두 계기가 같은 방향을 가리키고, 이쪽이 더 좁다.

### 이 문서가 더한 것 셋

1. **`mode_unresolved` 24행의 원인을 실제로 팠다** (§4). 1회차는 t128 의 기존 분류를
   존중해 재검증하지 않았다. 나는 24행이 전부 한 타입(`Martin MAC Aura XB`)이고,
   콘솔 폭-25 모드가 셋이며, CSV 가 두 겹 모드명의 **앞 겹만** 말한다는 것까지 열었다
2. 🔴 **그 분류를 두고 1회차와 갈린다** (§5). 1회차는 8/30 의 「우리 코드/문서 매칭 문제」
   분류를 그대로 뒀고, 나는 **(C) 문서 의도 미확인**으로 본다 — 가를 수 있는 값이
   CSV 에 **존재하지 않기** 때문이다. 근거는 §4 의 규칙 직독이다
3. **0 에 검출력 대조군을 붙였다** (§3.2). 같은 술어가 형제 둘은 잡고 이것만 0임을 보였다

### 1회차가 남긴 물음 하나 — 나도 못 갈랐다

1회차 §4: 「`ambiguous` 상태가 이 저장소에서 실측된 적이 있는지 — 코드 어휘에는 있는데
실측 사례가 없다. **공허한 분기인지 갈리지 않았다.**」
**나도 이번 회차에서 `ambiguous` 를 한 번도 못 봤다.** 두 회차 다 0이다.
이 물음은 열린 채로 남는다.

---


## 0. 한 줄

**감독 지적이 맞다.** 픽스처 타입은 콘솔에 **들어가 있었고**, 8/30 에 우리가 **못 읽었다**.
지금 재니 **타입 미해석 0행 · 8종 전부 해석**이다. 54는 사라진 것이 아니라 **처음부터
타입 문제가 아니었다.**

남은 것은 전혀 다른 문제 하나다 — **`Martin MAC Aura XB` 24행의 모드 미확정.**

## 1. 응답기 버전 — 명령 결과가 아니라 회신 필드로 판정했다

카드가 「`executed_ok` 같은 명령 결과로 판정하지 마라」고 못 박았다. 그대로 했다.

| 단계 | 명령 | 관측 |
|---|---|---|
| 살아 있나 | `python -m server.tools.probe_preflight --listen-port 9005` | `verdict: responder_ok` · `health: online` |
| 버전 | `python -m server.tools.introspect_probe --path Patch/FixtureTypes --offset 0 --listen-port 9005` | 회신에 **`"offset": 0` 에코** · `truncated: false` · `total: 16` · `ok: true` |

판별자는 `introspect_probe.py:96-105` 가 정한 것이다 — **회신에 `offset` 에코가 없으면
1.6.2 이전**이고 `paging: unsupported` 를 단다. 이번 회신은 **에코가 왔고 그 키가 안 붙었다.**

**따라서 응답기는 1.6.2 이상이다.** (정확한 버전 문자열은 이 채널로 안 온다 — 「1.6.2 이상」
까지만 주장한다.) 감독이 재임포트한 것이 실제로 반영돼 있다.

⚠️ 첫 시도는 `--path` 를 위치 인자로 줘서 **exit 2 로 죽었고 산출물이 0바이트**였다.
그 0을 「에코 없음」으로 읽지 않았다 — `wc -c` 로 먼저 갈랐다. 규약 §4.0.

## 2. 8/30 의 54는 어디로 갔나

`console_read` 가 직접 답한다:

```
complete_enough_to_judge_absence : true          <- 8/30 에는 이것이 서지 않았다
child_count                      : 86
observed_count                   : 86
missing_count                    : 0
unread_count                     : 0
unreadable_address_count         : 0
caveat                           : 열거는 절단됐으나 선언된 자식을 전부 관측했다
                                   — 수량 비교는 정확하고, 인덱스 도메인만 미상
type_translation.attempted       : true
type_translation.named           : 15
type_translation.untranslated    : {}            <- 미번역 0
fid_read                         : known 86 · unresolved 0
```

**「선언된 자식 86개를 전부 관측했다」**가 핵심이다. 8/30 리포트는 「풀 childCount 20인데
19개만 회신」을 스스로 적었다 — 그때는 판독이 절단됐고, 그 상태에서 나온 「없다」가
54행으로 기록됐다.

**타입 해석 결과 전문** (`payload.types`):

```
resolved (8종, 전부):
  ETC S4 LED S3 Lustr X8      ->  Source 4 LED Series 3 Lustr X8
  Elation CUEPIX Blinder WW2  ->  CuePix Blinder WW2
  Martin Atomic 3000 LED      ->  Atomic 3000 LED
  Look Unique 2.1             ->  Unique 2 1
  Robe MegaPointe             ->  Robin MegaPointe
  Robe Spiider                ->  Robin Spiider
  Martin MAC Aura XB          ->  Mac Aura XB
  Martin RUSH PAR 2 RGBW Z    ->  Rush Par 2 RGBW Zoom
unresolved: []
```

이름이 상당히 다른데도 전부 걸렸다 — 제조사 접두 탈락(`Martin` 삭제), `Robe` -> `Robin`,
`2.1` -> `2 1`. **매칭 계층이 실제로 일하고 있다.** 8/30 에 이 매칭이 실패한 것이 아니라,
비교할 라이브러리 목록 자체를 못 받았던 것이다.

🔴 **「54종」이라는 말 자체가 두 번 어긋나 있었다.** CSV 가 요청하는 **타입은 8종**이고
**행이 86개**다. 54는 종 수도 행 수도 아니고, 8/30 회차에 `type_unresolved` 로 스킵된
**행 수**였다. 감독이 「왜 54종이야?」라고 물으신 것이 정확한 질문이었다 —
그 수는 종 수가 아니었다.

## 3. 🔴 상태별 전수 표 — 이 카드의 본체

`lxseq_e2e --action preview` 재실행, 86행 전수. **쓰기 0건**(`summary_ko`: 「미리보기 —
쓰기 0건. 런 0개 · 계획 0대 · 건너뛴 행 86건」).

| 스킵 종류 | 행 수 | 타입 | 뜻 | 처분 |
|---|---:|---|---|:--:|
| **`type_unresolved`** | **0** | — | 타입을 못 찾음 | — |
| ├ `absent` | **0** | — | 콘솔에 없다 | (B) 였을 것 |
| ├ `ambiguous` | **0** | — | 후보가 여럿 | (A) 였을 것 |
| └ `library_unreadable` | **0** | — | 라이브러리를 못 읽음 | (B) 였을 것 |
| `already_patched` | **62** | 7종 | 같은 타입이 같은 자리에 이미 있다 | 할 일 없음 |
| `mode_unresolved` | **24** | `Martin MAC Aura XB` 1종 | 타입은 찾았고 **모드**를 못 정함 | §4 |
| 합계 | **86** | 8종 | | |

**세 상태 전부 0이다.** 카드가 요구한 「absent 몇 · ambiguous 몇 · library_unreadable 몇」의
답은 **0 · 0 · 0** 이다. 8/30 의 54행은 세 상태 중 어느 것으로도 지금 나타나지 않는다.

행 수 산술이 맞는다: CSV 타입별 행 수가 Aura 24 · RUSH PAR 20 · S4 LED 14 · Spiider 8 ·
MegaPointe 8 · CUEPIX 6 · Atomic 4 · Unique 2 = **86**. Aura 24행이 `mode_unresolved`,
나머지 7종 62행이 `already_patched` — **24 + 62 = 86**, 남는 행이 없다.

### 3.1 이 0이 다른 신호에 가려진 것이 아님을 확인했다

이 표의 가장 큰 함정은 **`already_patched` 가 타입 판정을 가리는 것**이었다.
줄번호만 보면 그렇게 보인다 — `already_patched` 는 `:408`, `type_unresolved` 는 `:530` 이다.

**호출 자리를 열어 보니 정반대다:**

```
:515  for record in records:                 루프 진입
:518      if console_type is None:           <- 타입 판정이 먼저
:530          kind="type_unresolved"
:534          continue
:549      if mode.resolution == "unresolved" <- 그다음 모드
:560          kind="mode_unresolved"
:567          continue
:571      occupied = _occupancy_skip(...)    <- 점유 검사는 여기서 처음 불린다
```

`_occupancy_skip` 은 `:370` 에 **정의**돼 있고 `:571` 에서 **호출**된다.
정의 순서가 실행 순서가 아니다. **86행 전부가 타입 검사를 통과한 뒤에** 62행이
`already_patched` 로 갈렸다. 가림은 없다.

### 3.2 검출력 대조군

`type_unresolved` 0건이 「없다」인지 「내 술어가 못 본다」인지 갈랐다:

```
grep -c type_unresolved  .moai/reports/t204/e2e-preview.json   -> 0
grep -n type_unresolved  server/lxseq/mapper.py                -> 530  (어휘 실재)
grep -n already_patched  server/lxseq/mapper.py                -> 408  (같은 술어가 잡는다)
grep -n mode_unresolved  server/lxseq/mapper.py                -> 560  (같은 술어가 잡는다)
```

같은 술어가 형제 둘은 잡고 이것만 0이다. **검출력 있는 0이다.**

## 4. 남은 24행 — 타입이 아니라 모드다

24행 전부 같은 타입 `Martin MAC Aura XB` (콘솔 `Mac Aura XB`).
FID `201-212` · `301-306` · `311-316`.

사유 문자열이 24행 모두 **바이트 동일**하다:

```
모드를 확정하지 못했다 — 실측 모드: [Extended - Extended(25), Extended - RAW(25),
Extended - RGB(25), Standard - Extended(14), Standard - RAW(14), Standard - RGB(14)].
mode_overrides: {"Martin MAC Aura XB": "<콘솔 모드 이름>"} 로 재호출하라.
```

**콘솔이 답한 모드는 6종이고 폭은 두 값뿐이다** — 25가 셋, 14가 셋.

CSV 가 주는 것:

```
201,BACK,Martin MAC Aura XB,Extended 25ch,25,4,1,4.001–025,업스테이지 트러스
                            ^^^^^^^^^^^^^ ^^
                            Mode 열        Ch 열
대조군(잘 붙은 타입): 501,MOVER-U,Robe MegaPointe,Mode 1 39ch,39,...
```

해석 규칙을 직독했다(`mapper.py:278` `_resolve_mode`, `:360` `_match_by_label_token`):

1. `same_width` = 폭 25인 콘솔 모드 -> **3종**. 유일하지 않으니 `width_unique` 실패
2. 라벨 토큰 매칭 -> 토큰은 `["Extended", "25ch"]`. 후보 3종의 이름이 **셋 다
   `Extended` 로 시작**하므로 `any(token in name)` 이 셋 다 참 -> `hits=3`
3. `return hits[0] if len(hits) == 1 else None` -> **`None`** -> `unresolved`

즉 **어떤 규칙으로도 지금 정보로는 못 고른다.** 콘솔 모드 이름이
`<Extended|Standard> - <Extended|RAW|RGB>` 라는 **두 겹**인데, CSV 는 **앞 겹만** 말한다.
뒤 겹(색 혼합 방식 Extended/RAW/RGB)은 **CSV 에 아예 없다.**

## 5. 3분류 — 기본값 (C) 를 지켰다

| 항목 | 분류 | 근거 (같은 줄에) |
|---|:--:|---|
| 픽스처 타입 8종 전부 해석됨 | 해결됨 | `payload.types.unresolved: []` · `untranslated: {}` |
| 8/30 의 54행 = 판독 절단의 결과 | **(B) 해소됨** | 응답기 1.6.2+ 회신 에코 · `complete_enough_to_judge_absence: true` · `missing_count: 0` |
| `Aura XB` 24행 모드 미확정 | 🔴 **(C) 문서 의도 미확인** | CSV `Mode` 열이 「Extended 25ch」로 **앞 겹만** 말하고, 콘솔은 뒤 겹(Extended/RAW/RGB)을 요구한다. **정보가 CSV 에 없다** — 코드 규칙으로는 못 만든다 |
| 62행 `already_patched` | 할 일 없음 | 같은 타입이 같은 자리에 이미 있다 |

🔴 **`mode_unresolved` 를 (A) 로 분류하지 않은 이유를 적는다.** 카드는 「`ambiguous` 가
나오면 (A) 후보」라고 했고 이것은 형태가 비슷하다 — 콘솔에 있는데 우리가 못 골랐다.
그런데 **못 고른 원인이 우리 규칙이 아니라 입력의 정보 부족**이다. 폭도 라벨도 셋을
가르지 못하고, 가를 수 있는 값이 CSV 에 존재하지 않는다. 코드는 **추측하지 않고 거절했고
그 자리에서 해법(`mode_overrides`)까지 문자열로 안내한다** — fail-closed 가 설계대로 돈 것이다.
근거 없이 (A) 로 적으면 감독께 한 줄 여쭈면 끝날 일이 코드 카드가 된다.

**감독께 여쭐 것 하나**: `Martin MAC Aura XB` 24대를 콘솔의 어느 모드로 패치할까요 —
`Extended - Extended` / `Extended - RAW` / `Extended - RGB` (셋 다 25ch). CSV 의
「Extended 25ch」는 앞 겹만 지정하고 있습니다. 답을 주시면 `mode_overrides` 로 바로 붙습니다.

## 6. 처방은 정하지 않았다 (카드 지시)

재료만 놓는다. 갈래는 셋으로 보이고 **어느 것도 실행하지 않았다**:
(a) 감독이 모드를 지정 -> `mode_overrides` 로 재호출 (코드 변경 0) ·
(b) CSV `Mode` 열에 뒤 겹을 적는다 (정본 데이터 변경) ·
(c) 매칭 규칙을 바꾼다 — **권하지 않는다.** 정보가 없는데 규칙만 정교하게 하면
추측이 되고, 이 앱에는 실행 취소가 없다.

## 7. 안 잰 것

- **`apply` 를 안 돌렸다.** 이 회차는 preview 전용이고 콘솔 쓰기 0건이다.
  62행이 `already_patched` 이므로 남은 대상은 24행뿐인데, 그 24행이 바로 모드 미확정이다
- **정확한 응답기 버전 문자열을 안 쟀다.** 「1.6.2 이상」까지만 회신으로 판정했다
- **`Patch/FixtureTypes` 의 실제 타입 목록을 열거하지 않았다.** `introspect` 는 그 클래스의
  **프로퍼티 접근자 16종**을 답한다(타입 목록이 아니다). 타입 해석 결과는 하네스의
  `payload.types` 로 읽었다 — 콘솔 라이브러리 전량 열거는 이 회차에 안 했다
- **8/30 리포트 원본을 열지 않았다.** 「54」와 「childCount 20 중 19 회신」은 카드 본문이
  전한 값이고 내가 그 파일을 직접 읽어 대조하지 않았다
- **`already_patched` 62행이 언제 어떻게 패치됐는지 안 쟀다.** 감독 GUI 작업인지 이전
  `apply` 런인지 이 측정으로는 안 갈린다
- **뮤테이션 0건.** 코드 변경이 없어 걸 대상이 없다. 대신 0에 검출력 대조군을 붙였다(§3.2)

## 8. 증거 파일

```
.moai/reports/t204/introspect-probe.json   1,326 B   응답기 버전 판별 회신
.moai/reports/t204/e2e-preview.json       53,553 B   preview 전수 (stderr 0 B)
```

---

**측정자**: t204 레인 · 콘솔 쓰기 0 · 코드 변경 0 · 새 카드 0 · 처방 미실행

