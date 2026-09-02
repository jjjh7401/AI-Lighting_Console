# t246 — 판별자는 안 움직였다. 갈래 B 다.

기준: 워크트리 `.claude/worktrees/t246` · 브랜치 `WT-selection-channel` · base `origin/main 1eea552`
2026-09-02 · **콘솔 쓰기 정확히 2건** (`Fixture 501`, `Clear` — 승인된 그 둘뿐)

## 0. 한 줄

`Fixture 501` 을 쏘기 전과 쏜 뒤, `Selection` 과 `ProgrammerPart` 의 `childCount`
가 **둘 다 0 에서 안 움직였다.** 이 채널은 프로그래머 점유의 판별자가 되지
못한다 — t242 verdict §7 의 **갈래 B**, `SelectionCount()` 계열 새 동사가
유일한 경로다.

🔴 다만 이 결론에는 **살아 있는 대안 가설이 하나 남는다.** §5 를 먼저 읽어라.
「안 움직였다」를 「채널이 눈멀었다」로 곧장 읽으면 안 되는 이유가 거기 있다.

## 1. 선행 전제 — 이 트리에서 다시 쟀다

| 전제 | 명령 | 관측 |
|---|---|---|
| 응답기 실기 = `1.6.3` | `responder_roundtrip --expect-version 1.6.3` | `[PASS] ping: live version=1.6.3` — **일치** |
| 계기 생존 (음성 대조군) | `--path ZZZNOTREALROOT9` | `responder error: path segment not found` — 살아 있다 |
| base | `git rev-parse --short origin/main` | `1eea552` — 배차서와 일치 |
| `Fixture 501` · `Clear` 가 게이트 통과 | `validate` + `classify_command`(정본 룰셋) | 둘 다 `category='safe'` |

같은 분류에서 `'Off Fixture 501' → invoking` (여전히 막힘) 과
`'ZZZNOTACOMMAND' → safe` 를 함께 재현했다. **게이트는 위험을 막는 장치이지
실재를 확인하는 장치가 아니다** — 이 사실이 §5 에서 결정적으로 쓰인다.

## 2. 절차와 회신 원문

각 단계 사이에 되읽었다. `node=` 는 응답기 회신 그대로다.

### (0) 음성 대조군
```
--path ZZZNOTREALROOT9
  [FAIL] state: responder error: path segment not found: 'ZZZNOTREALROOT9'
```

### (1) 사전 판독 — 쏘기 전
```
Selection        node={'childCount': 0, 'class': 'Selection',   'name': 'Selection'}
Programmer       node={'childCount': 1, 'class': 'Programmer',  'name': 'Programmer'}
ProgrammerPart   node={'childCount': 0, 'class': 'ProgPart',    'name': 'Part Zero'}
Programmer/1     node={'childCount': 0, 'class': 'ProgPart',    'name': 'Part Zero'}
```

### (2) 🔴 콘솔 쓰기 1/2 — `Fixture 501` (선택만, 값 없음)
```
--exec-command 'Fixture 501'
  [PASS] exec: ok
```

### (3) 되읽기 — **판별자**
```
Selection        node={'childCount': 0, 'class': 'Selection',   'name': 'Selection'}   ← 안 움직임
Programmer       node={'childCount': 1, 'class': 'Programmer',  'name': 'Programmer'}  ← 안 움직임
ProgrammerPart   node={'childCount': 0, 'class': 'ProgPart',    'name': 'Part Zero'}   ← 안 움직임
Programmer/1     node={'childCount': 0, 'class': 'ProgPart',    'name': 'Part Zero'}   ← 안 움직임
```

### (4) 🔴 콘솔 쓰기 2/2 — `Clear`
```
--exec-command 'Clear'
  [PASS] exec: ok
```

### (5) 해제 후 되읽기 + 계기 재확인
```
Selection        childCount 0     ← (1) 과 동일
Programmer       childCount 1     ← (1) 과 동일
ProgrammerPart   childCount 0     ← (1) 과 동일
Programmer/1     childCount 0     ← (1) 과 동일
ZZZNOTREALROOT9  path segment not found     ← 계기, 끝까지 생존
```

**다섯 지점 전부 사전 판독과 바이트 동일하다.** 남은 것이 없다.

## 3. `Programmer` 는 애초에 판별자 후보가 아니었다

배차서는 셋을 후보로 세웠지만 실제 후보는 **둘**이다.

`Programmer` 의 `childCount 1` 은 그 자식이 `Part Zero`(`class 'ProgPart'`)
하나라는 뜻이다 — **파트 개수이지 픽스처 개수가 아니다.** 파트는 선택으로
늘지 않으므로 이 값은 구조적으로 안 움직인다. 안 움직인 것이 이 노드에서는
증거가 아니다.

판별자였던 것은 `Selection` 과 `ProgrammerPart` 둘이고, **그 둘이 안 움직였다.**

## 4. 대상 부재 가설 — 제거했다

「안 움직였다」의 가장 값싼 대안 설명은 **FID 501 이 이 쇼파일에 없다** 는
것이다. 그러면 이 회차는 채널에 대해 아무것도 안 말한다. 그래서 쟀다.

```
Patch/Stages/1/Fixtures   childCount 86
paged walk: offsets [0,19,37,55,73] · windows [19,18,18,18,13]
collected 86 / 86 · truncated False · VERDICT COMPLETE
```

전수 86개 이름 중 **`MOVER-U 501` 이 있다.** 대상은 존재한다.

🔴 이 단계는 잘린 창 하나로는 못 닫는다 — 첫 창은 19개만 답한다. **잘린 출력의
부재는 부재가 아니다.** 페이징을 완주해 `COMPLETE` 를 받고서야 「있다」를 말할
수 있다.

## 5. 🔴 살아남은 대안 가설 — `exec: ok` 는 실행의 증거가 아니다

응답기 소스를 읽었다(콘솔 무접촉):

```lua
function M.classify_result(result)
    if result == nil then
        return true, ""          -- :978-980
    end
    ...
```
`build_exec_result` 는 `pcall(Cmd, command)` 가 안 던지고 결과가 `nil` 이면
`ok = true` 를 돌려준다. MA3 `Cmd()` 는 대부분의 명령에 `nil` 을 답한다.

**즉 `exec: ok` 는 「응답기가 받아 Cmd 를 불렀고 예외가 안 났다」이지
「콘솔이 501 을 선택했다」가 아니다.** §1 의 `'ZZZNOTACOMMAND' → safe` 와 같은
계열의 함정이 회신 쪽에도 있다.

그래서 두 가설이 아직 살아 있다:

| 가설 | 내용 | 상태 |
|---|---|---|
| (i) 채널이 눈멀었다 | 선택은 됐는데 `Selection`/`ProgrammerPart` 가 그걸 안 비춘다 | **남음** — 갈래 B |
| (ii) 선택이 안 됐다 | `Cmd("Fixture 501")` 이 실제로는 아무 선택도 안 했다 | **남음** |

(ii)가 참이면 이 회차는 채널을 판정하지 못한 것이 된다.

### 이 회차가 (ii)를 못 지운 이유

지우려면 **음성 대조군 발사**가 필요하다 — 존재하지 않는 명령을 쏴서
`exec: ok` 가 그때도 돌아오는지 보는 것. 돌아오면 `exec: ok` 는 실행의
증거가 아님이 확정되고, 안 돌아오면 (ii)가 지워진다.

🔴 **안 쐈다. 감독 승인 범위가 `Fixture 501` 과 `Clear` 정확히 둘이고,
대조군은 세 번째 쓰기다.** 대조군이 필요하다는 이유로 승인 범위를 넓히는 것은
이 카드가 존재하는 규율 자체를 무너뜨린다. 안 잰 채로 남기고 다음 카드로 넘긴다.

### 5.1 🔴 만료 고지 (2026-09-02, 발행 당일) — 위 처방은 **작동하지 않는다**

위 문단이 적은 처방(「존재하지 않는 **명령**을 쏜다」)은 **틀린 축을 쏜다.**
원문은 그대로 둔다 — 그 시점 정보로는 옳은 판단이었다. 처방만 갈아끼운다.

**왜 안 되나.** `t215/verdict.md` §1 이 콘솔의 거절 축을 셋으로 갈라 놨다:

| 축 | 예 | 콘솔 |
|---|---|---|
| 없는 **동사** | `Frobnicate Sequence 9` | `Illegal object` — 거절 |
| 없는 **꼬리 키워드** | `Group 1 At Full Zorble 3` | 🔴 `ok` — 통과 |
| 없는 **속성명** | `Property 'Preset1Frobnicate'` | `Illegal property` — 거절 |

`ZZZNOTACOMMAND` 는 **없는 동사** 축이고, `t233/verdict.md` §8 이 그 축에서
`failed · "Illegal object"` 를 이미 받아 뒀다. 즉 그 대조군은 **이미 존재하고,
다시 쏠 필요가 없으며, 쏴도 (ii)를 못 지운다.**

`Fixture 501` 은 **있는 동사 + 있어 보이는 피연산자**라 그 셋 중 어디도 아니다.

**정정 후 처방 — 넷째 축을 쏜다: 있는 동사 + 검증되지 않은 피연산자 값.**
`t241/verdict.md` §6 이 같은 자리를 이미 「안 잰 것」으로 세워 뒀다 —
「`Fixture <n>` 이 FID 를 겨누는지 슬롯을 겨누는지 이 리그에서 안 쟀다」.
**그 미지와 이 카드의 (ii)는 같은 결함이다.**

이 회차의 §4 측정이 그것을 잴 수 있게 만든다. `MOVER-U 501` 은 픽스처 목록의
**슬롯 27번**이고(전수 86개), FID 501 과 슬롯 27 은 다른 수다.

`27` 은 **동시에 둘**이다 — 유효한 **슬롯**이면서, 규약상 없는 **FID**
(`LX-SEQ-SPEC-v2.1.md:341` — 「FID 체계는 그룹당 100번대 블록 (101~ KEY,
201~ BACK …)」). 그래서 한 발이 두 축을 덮는다.

| 쏠 것 | 되읽기 | 읽는 법 |
|---|---|---|
| `Fixture 27` | `Selection` 이 **움직인다** | `Fixture <n>` 은 **슬롯**을 겨눈다 ⇒ `Fixture 501` 은 없는 슬롯이라 아무것도 안 했다 ⇒ **채널은 멀쩡하다** ⇒ 🔴 **§6 의 「갈래 B」가 반증된다** |
| `Fixture 27` | 안 움직인다 | 🔴 **아무것도 확정하지 못한다** — 아래 참조 |

### 🔴 두 행은 대칭이 아니다 — 「불변」은 갈래 B 를 강화하지 못한다

「안 움직인다」에는 후보가 **둘**이고 이 측정은 그 둘을 못 가른다:

| 후보 | 내용 | 갈래 B 에 대해 |
|---|---|---|
| (a) | 슬롯 축도 안 비친다 | 강화한다 |
| (b) | `Fixture <n>` 은 **FID** 를 겨누는데 FID 27 이 없어서 아무 일도 안 났다 | **아무 말도 안 한다** — `Fixture 9999` 와 같은 뜻이 된다 |

그러므로 **둘째 행을 「갈래 B 확정」으로 읽으면 안 된다.** 얻는 것은
「피연산자가 검증되든 안 되든 관측 가능한 변화가 없다」 하나뿐이고, 그건
`Fixture 9999` 로도 얻는 것이다. 첫째 행(움직이면 슬롯 축, t246 반증)만이
비대칭적으로 결정적이다.

**그래도 `Fixture 27` 이 `Fixture 9999` 보다 낫다** — 움직이면 `9999` 로는
원리적으로 못 얻는 정보를 얻고, 안 움직여도 `9999` 만큼은 얻는다. 열위가 없다.

⚠️ 한계 — **이 절의 FID 판단 둘 다 추론이고, 콘솔에서 잰 값이 아니다.**

| 추론 | 출처 | 안 잰 것 |
|---|---|---|
| 「이 쇼의 FID 는 101 이상」 | §4 의 `name`(`"MOVER-U 501"`) 끝자리 | 이름 끝의 수가 FID 라는 것 |
| 「FID 27 은 없다」 | `LX-SEQ-SPEC-v2.1.md:341` 정본 문면 | 그 규약이 이 쇼파일에 실제로 적용됐는지 |

§4 가 이 채널로 읽은 것은 `name` 과 슬롯 인덱스 `i` 둘뿐이다. **콘솔에서 FID
속성을 직접 판독할 수 있는지는 안 쟀다** — 그게 되면 위 추론 둘이 한 번에
관측으로 바뀐다. 그 전까지 이름과 FID 가 어긋난 픽스처가 하나라도 있으면
둘째 행의 (b)가 더 흐려진다. 첫째 행은 그래도 선다.

🔴 **`Fixture 27` 이 움직이면 이 판정서의 결론이 뒤집힌다.** 쏘기 전에 그 가능성을
승인자에게 먼저 말해야 한다.

## 6. 판정

**갈래 B 로 간다 — 다만 (ii)를 지운 뒤에.**

| | |
|---|---|
| 이 채널이 프로그래머 점유를 비추는가 | **관측된 범위에서 아니다** — 선택 전후 다섯 지점 전부 불변 |
| 그래서 무엇을 해야 하나 | `SelectionCount()` / `SelectionFirst()` **새 동사**. 별칭이 아니라 응답기 확장이고, 값 반환이라 `state` 로는 못 싣는다 — 회신 형태부터 정해야 한다 |
| 먼저 할 것 | ~~🔴 **음성 대조군 발사 1건**(존재하지 않는 명령)으로 (ii)를 지운다~~ → 🔴 **만료됨, §5.1 참조.** 없는 **명령**은 틀린 축이고 그 대조군은 t233 §8 에 이미 있다. 쏠 것은 **`Fixture 27`** — 있는 동사 + 검증되지 않은 피연산자. 새 동사 설계는 그 다음이다 |

배차서는 「어느 쪽이 나와도 이긴다」고 했고 그건 맞다. 다만 이긴 쪽이
**「B 다」가 아니라 「B 인데 한 발 더 재야 확정된다」** 이다. 등급을 증거보다
앞세우지 않는다.

## 7. 덤 — 「FID 501 에 Zoom 45 가 남았나」

배차서가 예고한 대로 **이 답은 무효다.**

사전 판독은 `Programmer`/`ProgrammerPart` 가 비어 있다고 답했다. 그런데 (3)이
「이 채널은 점유를 안 비춘다」로 나왔으므로, 그 0 은 「비었다」의 증거가 못 된다.
어제 사고의 잔존 여부는 **이 회차가 답하지 않는다.**

## 8. 안 잰 것

| 미측정 | 왜 | 어떻게 닫나 |
|---|---|---|
| `Cmd("Fixture 501")` 이 실제로 선택했는가 | 대조군이 세 번째 콘솔 쓰기라 승인 밖 | ~~존재하지 않는 명령 1발~~ → 🔴 **만료됨, §5.1 참조.** `Fixture 27` 1발 → `Selection` 이 움직이는지 |
| 콘솔 화면에 501 이 선택돼 보였는가 | 이 채널에 화면 판독이 없다 | 사람 눈 또는 새 동사 |
| `Selection` 이 **다른 종류의 선택**에는 반응하는가 | 승인이 픽스처 선택 한 줄이었다 | 별도 카드 |

## 9. 이 카드가 안 한 것

- 콘솔 쓰기는 `Fixture 501` 과 `Clear` **둘뿐**이다. 값은 안 실었다 —
  `Attribute … At …` 류는 한 번도 안 나갔다
- 대조군이 필요하다는 이유로 승인 범위를 넓히지 않았다
- 머지 안 했다 — 리드가 확인하고 한다
