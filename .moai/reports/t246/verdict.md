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

## 6. 판정

**갈래 B 로 간다 — 다만 (ii)를 지운 뒤에.**

| | |
|---|---|
| 이 채널이 프로그래머 점유를 비추는가 | **관측된 범위에서 아니다** — 선택 전후 다섯 지점 전부 불변 |
| 그래서 무엇을 해야 하나 | `SelectionCount()` / `SelectionFirst()` **새 동사**. 별칭이 아니라 응답기 확장이고, 값 반환이라 `state` 로는 못 싣는다 — 회신 형태부터 정해야 한다 |
| 먼저 할 것 | 🔴 **음성 대조군 발사 1건**(존재하지 않는 명령)으로 (ii)를 지운다. 새 동사를 설계하기 전에 이게 먼저다 |

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
| `Cmd("Fixture 501")` 이 실제로 선택했는가 | 대조군이 세 번째 콘솔 쓰기라 승인 밖 | 존재하지 않는 명령 1발 → `exec: ok` 가 그때도 오는지 |
| 콘솔 화면에 501 이 선택돼 보였는가 | 이 채널에 화면 판독이 없다 | 사람 눈 또는 새 동사 |
| `Selection` 이 **다른 종류의 선택**에는 반응하는가 | 승인이 픽스처 선택 한 줄이었다 | 별도 카드 |

## 9. 이 카드가 안 한 것

- 콘솔 쓰기는 `Fixture 501` 과 `Clear` **둘뿐**이다. 값은 안 실었다 —
  `Attribute … At …` 류는 한 번도 안 나갔다
- 대조군이 필요하다는 이유로 승인 범위를 넓히지 않았다
- 머지 안 했다 — 리드가 확인하고 한다
