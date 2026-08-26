# t95 — 프리셋 **값** 판독 채널 조사 (읽기 전용)

날짜: 2026-08-26 · 트리: `.claude/worktrees/t95` (base `12b018b`) · 브랜치 `WT-preset-value-read`
콘솔: grandMA3 onPC 2.4.2 (pid 47006) · 응답기 `CopilotResponder` **1.6.1** (ping 실측)
전송: `127.0.0.1:8000` 송신 / `9005` 수신 · **콘솔 쓰기 0줄** (`exec` 미사용)

## 1. 주장 (Claim)

「이름은 같은데 값이 다른 프리셋」을 판별하려면 **값이 읽혀야 한다.** 이 조사는
"값을 읽는 채널이 존재하는가" 하나만 답한다. 결론:

> **미확정이다 — 채널이 없다고도, 있다고도 말할 수 없다.** 다만 **구현 판정은 확정적이다:
> 지금 값 일치 가드를 만들지 마라.** 유일한 후보 프로퍼티가 빈 문자열을 답하고,
> 그 빈 값을 해석할 기준선이 없으며, 프리셋 프로퍼티 138개 중 **111개가 현 응답기로
> 원리적으로 도달 불가**하기 때문이다.

## 2. 증거 (Evidence) — 명령과 관측 원문

원문은 같은 디렉터리의 JSON 파일에 그대로 있다.

### 2.0 대조군 — 날조 경로 (먼저 쐈다)

```
python -m server.tools.introspect_probe --path 'DataPool/ZZZNoSuchPoolXYZ' --listen-port 9005
→ exit 1 · introspect failed: path segment not found: 'ZZZNoSuchPoolXYZ'
```
→ `control-fabricated-path.txt`. **계기가 아무 경로에나 ok 를 주지 않는다.** 동시에
응답기가 살아 있다는 증거이기도 하다(죽었으면 타임아웃이지 거절이 아니다).

이후 **모든** props 조회는 날조 이름을 **목록 맨 앞**에 넣어 쐈다. 뒤에 넣었다가
페이로드 예산 절단으로 대조군이 잘려 나간 회차가 실제로 있었고(§5 참조), 그 회차는
증거로 쓰지 않았다.

### 2.1 경로 — `DataPool/Presets` 는 없다

```
--path 'DataPool/Presets' → path segment not found: 'Presets'
```
`server/prechk/inventory.py:56` 의 `RETIRED_PATHS` 와 일치. 실제 주소는
`DataPool/PresetPools/<pool>/<n>` 이다 (`state-presetpool-1.json`: 풀 14개,
1=Dimmer … 4=Color).

### 2.2 프리셋 오브젝트에는 자식이 없다

```
--path 'DataPool/PresetPools/1/3' (state)
→ {"node": {"childCount": 0, "class": "Preset", "name": "미드"}, "children": []}
```
→ `state-preset-1-3.json`. 값이 **자식으로** 실려 오지는 않는다.

### 2.3 프로퍼티 138개 중 27개만 열거된다

```
--path 'DataPool/PresetPools/1/3' (introspect)
→ ok true · class "Preset" · fields 27개 · total 138 · truncated true
```
→ `introspect-preset-1-3.json`. `introspect` 에는 페이징이 **없다**(`state` 에만
1.6.0 offset 이 있다). 절단은 꼬리부터라 앞 27개만 보이고 **111개 이름은 이 채널로
못 본다.**

### 2.4 열거된 이름 ≠ 읽히는 이름

`GUID` 는 introspect 목록에 있다(`t: "Custom"`). 그런데 props 는:

```
{"n": "GUID", "ok": false, "e": "property not readable: GUID"}
```
→ 열거 목록은 **판독 가능성의 목록이 아니다.** 그러므로 27개 안에 값 이름이
없다는 사실도, 111개 안에 있다는 추측도, 둘 다 증거가 아니다.

### 2.5 유일한 후보: `PRESETDATA` — 읽히지만 비어 있다

대조군을 맨 앞에 둔 회차(`props-preset-1-3-control-first.json`):

| 이름 | ok | 값 |
|---|---|---|
| `ZZZFAKE2` (날조 대조군) | **false** | property not readable |
| `MODE` | true | `0` |
| `HASDATA` | false | — |
| `ISEMPTY` | false | — |
| `VALUESTRING` | false | — |
| `PRESETDATA` | **true** | **`""` (빈 문자열)** |

`DataPool/PresetPools/1/1`(다른 프리셋)도 `PRESETDATA` = `""`,
`DEPENDENCYEXPORT` = `""`, `MEMORYFOOTPRINT` = `1536`, `COUNT` = `0`.

`PRESETDATA` 는 **Preset 클래스 고유**다 — 같은 이름이 Group 에서는 안 읽힌다(§2.6).
그래서 「아무 오브젝트나 답하는 껍데기」는 아니다.

### 2.6 🔴 결정적 대조 — 내용이 **확실히 있는** 오브젝트도 0을 답한다

`DataPool/Groups/1` (`ALL`) 은 t66 이 콘솔에 **18개 픽스처를 올린 것을 실측한** 그룹이다.
그 그룹을 오늘 같은 채널로 읽으면:

```
state  → {"node": {"childCount": 0, "class": "Group", "name": "ALL"}, "children": []}
props  → ZZZFAKE3 ok=false(대조군) · NAME ok=true "ALL" · COUNT ok=true "0"
         · PRESETDATA ok=false · MEMORYFOOTPRINT ok=true "1136"
```
→ `state-group-1.json`, `props-group-1-control-first.json`.

**내용이 있는데 `COUNT` 도 `childCount` 도 0 이다.** 그러므로 이 채널에서 나온
0 이나 빈 문자열은 **부재의 증거가 아니다.** (이건 메모리의 인용이 아니라 오늘 잰 값이다.)

## 3. 기준선 귀속 (Baseline-attribution)

- 트리: `.claude/worktrees/t95`, `git log --oneline -1` → `12b018b`
- 도구: 이 트리의 `server/tools/introspect_probe.py` 와 새로 쓴
  `server/tools/t95_state_dump.py`. 인터프리터는 주 체크아웃 `.venv` 를 빌렸지만
  `-m` 실행이라 `sys.path[0]` 이 이 트리이고, 트리 동일성 가드(t80)가 통과했다 —
  **도는 코드는 이 트리 것이다.**
- 응답기 버전은 가정이 아니라 ping 회신 실측: `live version=1.6.1`.

## 4. 미검증 (Gaps) — 안 잰 것과 그 이유

| 안 잰 축 | 왜 |
|---|---|
| 프로퍼티 111개 이름 | `introspect` 에 offset 페이징이 없다. 붙이려면 응답기 변경 = 콘솔 쓰기, 이 카드 밖 |
| **값이 있는 프리셋** 확보 | pool 1 의 6건은 우리 파이프라인이 만든 것이고, **내용이 실렸는지 자체가 미측정**이다. 넣으려면 `Store` = 쓰기, 이 카드 밖 |
| `prop`(단일) 경로 | `props`(복수)로 갈음했다. 같은 판독 구현을 탄다고 **가정**했고 안 쟀다 |
| Dimmer 이외 풀 | 나머지 13개 풀이 전부 비어 있어 클래스별 차이를 못 쟀다 |
| `MODE` ≠ 0 인 프리셋 | 시험한 프리셋이 전부 `MODE: 0`. 다른 모드에서 `PRESETDATA` 가 채워질 가능성 미측정 |

## 5. 잔여 위험 (Residual-risk)

- **절단이 꼬리부터**라 111개 중에 값 이름이 있을 가능성을 배제 못 한다. 「없다」로
  닫으면 그게 곧 미관측 결함 주장이 된다.
- 한 회차에서 이름 16개를 쐈다가 페이로드 예산으로 **대조군이 잘렸다**(`truncated: true`).
  그 회차는 버리고 6개로 다시 쐈다. props 는 최대 16개를 받지만 **예산은 개수가 아니라
  바이트**다 — 대조군은 항상 맨 앞에.
- `PRESETDATA` 가 실제 값 채널인데 우리 프리셋이 비어서 빈 문자열일 가능성과, 애초에
  값을 안 싣는 필드일 가능성이 **아직 안 갈린다**. 둘을 가르는 것이 다음 측정이다.

## 6. 그래서 무엇을 하나

1. **값 일치 가드를 구현하지 않는다.** 매퍼는 지금대로 `unverified=("value_match",)` 를
   회신에 실어 나른다 — 사용자에게 「이름만 봤다」가 보여야 한다.
2. 후속 두 갈래를 제안한다(승격은 감독·리드):
   - **(A) `introspect` 페이징** — `state` 의 offset 을 introspect 에도. 이게 138개를
     여는 유일한 길이고, 이 카드가 막힌 지점이다. 응답기 1.6.2 = 콘솔 쓰기 승인 필요.
   - **(B) 값이 있는 프리셋 확보 후 `PRESETDATA` 재판독** — t96(실기 재확인)과 같은
     쓰기 창에서 묶으면 승인 한 번으로 끝난다.
3. (A) 가 111개를 열어 값 이름이 **없다**고 나오면, 그때 비로소 NEGATIVE 로 닫고
   축을 「값은 콘솔에서 못 읽는다 → 시트를 진실의 원본으로」로 바꾸면 된다.
   지금 닫으면 안 잰 것을 닫는 것이다.
