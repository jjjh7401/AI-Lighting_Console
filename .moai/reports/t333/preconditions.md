# t333 착수 전제 — 둘 다 닫혔다 (+ 잠재 결함 둘 발견)

- 카드: t333 (전제 검증분. 도구 변경은 아직 하지 않았다)
- 측정: 2026-09-08, 실기 onPC, 응답기 1.6.5, 회신 포트 9005, `a3f28df` 기준
- 콘솔 쓰기: **0건** — 전부 state/props 판독

## 1. Claim (주장)

1. **전제 A 닫힘** — 콘솔 픽스처의 `Mode` 문자열은 `"<라이브러리 DMXModes 슬롯> <모드 이름>"` 형식이고, 이것이 **타입 8종 전부**에서 성립한다. 앞 숫자는 슬롯 인덱스와 8/8 일치, 뒤 이름은 라이브러리 이름과 8/8 일치.
2. **전제 B 닫힘** — 픽스처의 `FID` 는 판독 가능하다(프로퍼티 이름은 `FID`, `FIXTUREID` 가 아니다). 86/86 읽혔고 전부 CSV 에 있으며 시작 주소가 86/86 일치. CSV↔콘솔 대응은 이제 **값으로 확증**됐다 — 이름 추론이 아니다.
3. **따라서 t333 의 판별기는 이름 매칭이 아니라 슬롯 조회로 짜는 것이 옳다** — 픽스처 `Mode` 의 앞 숫자를 슬롯으로 써서 라이브러리 `DMXModes/<슬롯>` 을 직접 집으면 이름 문자열을 비교할 필요가 없다.
4. **잠재 결함 둘**을 같이 발견했다(아래 §6). 둘 다 오늘은 사고를 내지 않지만 둘 다 조용하다.

## 2. Evidence (증거)

### 2.1 t332 verdict.md 의 gap 5 표현이 틀렸다 — 정정

t332 는 "`FIXTUREID` 는 `property not readable` 이라 FID 대응을 확증 못 했다"고 적었다. 실제로는 **프로퍼티 이름이 `FID`** 다(`server/tools/lxseq_e2e.py:200` — 하네스가 `("FID", "Patch", "FixtureType", "Mode")` 를 읽는다). `FIXTUREID` 는 존재하지 않는 이름이라 옳게 실패한 것이고, 판독 불가가 아니었다.

```
uv run python -m server.tools.introspect_probe --path "Patch/Stages/1/Fixtures/43" \
  --names "FID,Mode,NAME,FixtureType,Patch" --listen-port 9005
```
```
"n": "FID",          "v": "201"
"n": "Mode",         "v": "1 Extended - Extended"
"n": "NAME",         "v": "BACK 201"
"n": "FixtureType",  "v": "FixtureType 8"
"n": "Patch",        "v": "4.001"
```
CSV 해당 행: `201,BACK,Martin MAC Aura XB,Extended 25ch,25,4,1,4.001–025,업스테이지 트러스` → FID·시작주소 모두 일치.

### 2.2 라이브러리 경로 — 세그먼트는 `DMXModes` 다

`Patch/FixtureTypes/<슬롯>/Modes` 는 8종 전부 `path segment not found` 로 답했다. 이건 부재가 아니라 **이름이 틀린 것**이었다 — 실제 세그먼트는 `DMXModes` (`server/prechk/footprint.py:62`). 8종이 *균일하게* 실패한 것이 신호였다.

`Patch/FixtureTypes` → childCount 15, 15개 전부 열거:
```
1 Robin Esprite · 2 Robin Forte HP · 3 Robin LEDBeam 350 · 4 Robin Spiider
5 Xtylos · 6 Sharpy Plus · 7 Robin MMX Spot · 8 Mac Aura XB
9 Rush Par 2 RGBW Zoom · 10 Source 4 LED Series 3 Lustr X8 · 11 Robin MegaPointe
12 Robin Spiider · 13 CuePix Blinder WW2 · 14 Atomic 3000 LED · 15 Unique 2 1
```
픽스처가 답하는 `FixtureType 8` 의 `8` 은 이 라이브러리 슬롯과 **일치**한다(8 = `Mac Aura XB`).

### 2.3 전제 A — 86대 전수 판독 + 8종 라이브러리 대조

86대 전부 `FID,Mode,NAME,FixtureType,Patch` 판독 성공, 빈 필드 0건 (`console-86-fixtures.tsv`). 쓰인 타입 8종의 `DMXModes` 전수 열거 (`library-dmxmodes.tsv`).

| 타입 | 픽스처 `Mode` | 앞 숫자 | 뗀 나머지 | 라이브러리 `DMXModes/<앞숫자>` | 슬롯 일치 | 이름 일치 | 대수 |
|---|---|---|---|---|---|---|---|
| FixtureType 4 | `1 Mode 1` | 1 | `Mode 1` | `Mode 1` | YES | YES | 8 |
| FixtureType 8 | `1 Extended - Extended` | 1 | `Extended - Extended` | `Extended - Extended` | YES | YES | 24 |
| FixtureType 9 | `2 9 channel` | 2 | `9 channel` | `9 channel` | YES | YES | 20 |
| FixtureType 10 | `3 Direct` | 3 | `Direct` | `Direct` | YES | YES | 14 |
| FixtureType 11 | `1 Mode 1` | 1 | `Mode 1` | `Mode 1` | YES | YES | 8 |
| FixtureType 13 | `4 4 channel` | 4 | `4 channel` | `4 channel` | YES | YES | 6 |
| FixtureType 14 | `3 Extended` | 3 | `Extended` | `Extended` | YES | YES | 4 |
| FixtureType 15 | `1 Mode 0` | 1 | `Mode 0` | `Mode 0` | YES | YES | 2 |

**서로 다른 타입-모드 쌍 8건 · 슬롯 일치 8/8 · 이름 일치 8/8 · 합계 86대.**

t332 는 이 성질을 **한 종**(`Extended - Extended`)으로만 봤다. 이제 8종이다 — [[lesson-one-control-bounds-the-conclusion]] 이 요구한 넓히기를 했다.

**파싱 함정을 실제로 밟아 봤다.** `4 4 channel`(타입 13)과 `2 9 channel`(타입 9)은 앞 숫자를 떼면 남는 문자열이 *또 숫자로 시작한다*. 「숫자를 전부 떼기」류의 술어를 쓰면 `channel` 이 남아 조용히 틀린다. 옳은 변환은 **첫 공백 구분 토큰 하나만** 떼는 것이고, 위 표는 그 술어로 8/8 이다.

### 2.4 전제 B — FID·주소 대조 전수

`console-86-fixtures.tsv` 와 정본 CSV 87행(헤더 1 + 데이터 86)을 FID 로 조인:

```
FID present in CSV: 86/86 | patch start matches: 86 | mismatch: 0 | FIDs absent from CSV: []
```
불일치 0건. **대응은 이름 접두 추론이 아니라 값 일치로 확증됐다.**

## 3. Baseline-attribution (baseline 귀속)

- 트리 `.claude/worktrees/t333-pre`, 브랜치 `WT-mode-slot-discriminator`, `git log -1` → `a3f28df`
- 정본 CSV: `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` (데이터 86행)
- 실기 응답기 `1.6.5` · 회신 포트 9005
- 증거 원문: `console-86-fixtures.tsv`(86행) · `library-dmxmodes.tsv`(32행, 8종)

## 4. Gaps (미검증)

1. **라이브러리 모드의 폭(`TotalFootprint`)을 재지 않았다.** 슬롯→이름 대응만 쟀다. t333 구현은 폭도 라이브러리에서 가져오므로, 슬롯 조회가 이름 조회와 같은 폭을 준다는 것은 아직 확인되지 않았다.
2. **쓰이지 않는 7종**(1·2·3·5·6·7·12)의 `DMXModes` 는 12번만 봤다. 나머지 6종은 열거하지 않았다.
3. **모드가 여러 개인 픽스처가 실제로 서로 다른 슬롯에 있는 쇼를 못 봤다.** 이 쇼는 타입마다 모드가 하나로 균일하다 — 같은 타입이 두 모드로 섞인 경우의 동작은 재지 않았다.
4. **`Mode` 문자열의 앞 숫자가 항상 존재한다는 보장을 못 봤다.** 8종 8건에서 모두 있었지만, 없는 경우(예: 모드가 하나뿐인 타입)를 만들어 보지 않았다. 타입 15는 모드가 1개인데도 `1 Mode 0` 로 숫자가 붙어 있었다 — 이건 약한 양성 증거다.
5. **`apply` 경로 여전히 미실측** (t332 gap 3 그대로).
6. **응답기 버전 대조 여전히 안 함** (t332 gap 6 그대로).

## 5. Residual-risk (잔여 위험)

- 이 쇼는 타입 8종·모드 8종이고 타입마다 모드가 하나다. 표가 8/8인 것은 **이 쇼의 다양성 한도** 안에서의 8/8이다. 모드가 섞인 쇼에서 같은 결론이 나오는지는 §4-3 이 열려 있다.
- 콘솔이 `Mode` 를 어떤 규칙으로 문자열화하는지는 문서로 확인한 게 아니라 **8건에서 관찰한 규칙**이다. 콘솔 버전이 바뀌면 형식도 바뀔 수 있다.

## 6. 발견한 잠재 결함 둘 (t333 범위에 넣을지 감독 판단 필요)

### 6-a. 라이브러리에 같은 이름 타입이 둘 있고, 이름 조회는 앞의 것이 조용히 이긴다

슬롯 **4 와 12 가 둘 다 `Robin Spiider`** 다. `server/prechk/mode_read.py` 의 타입 조회는:

```python
exact = [(slot, name) for slot, name in pairs if name == type_name]
if not exact:
    folded = [... casefold ...]
    exact = folded if len(folded) == 1 else []   # ← 접힌 쪽만 중복을 거부한다
if not exact:
    return TypeModeRead(attempted=True, type_found=False, detail=absent)
type_slot = exact[0][0]                          # ← 정확일치가 2건이면 앞것이 이긴다
```

정확일치가 2건이면 `if not exact` 가 거짓이라 `exact[0][0]` = 슬롯 4 가 **경고 없이** 채택된다. casefold 갈래는 `len(folded) == 1` 로 중복을 거부하는데 정확일치 갈래는 안 한다 — 두 갈래의 엄격도가 갈려 있다.

**오늘은 무해하다** — 슬롯 12의 `DMXModes` 를 열거해 보니 슬롯 4와 **바이트 동일**(10개, 이름·순서 같음). 다만 **폭은 재지 않았으므로**(§4-1) "무해"의 범위는 이름·순서까지다.

슬롯 조회 기반 판별기(§1-3)는 이름을 안 쓰므로 이 함정을 원리적으로 우회한다 — 이게 슬롯 조회를 택할 두 번째 이유다.

### 6-b. `console_after` 는 86대 중 18대만 읽는다

`preview-base.json` 의 `console_after`:
```json
{"path": "Patch/Stages/1/Fixtures", "ok": true, "child_count": 86,
 "children_listed": 18, "truncated": true, "enumeration_complete": false, ...}
```

즉 하네스는 **이미 픽스처마다 `FID`·`Patch`·`FixtureType`·`Mode` 를 읽고 있다** — 판별기에 필요한 데이터가 이미 손에 있다. 다만 (1) 첫 페이지 18대에서 잘리고 (2) 사후 보고용이라 `_resolve_mode` 로 흘러가지 않는다. Aura(슬롯 43~66)가 이 목록에 안 보였던 이유가 여기다.

`truncated: true` / `enumeration_complete: false` 를 **정직하게 달고 있다** — 잘린 것을 전체로 읽지 않게 막아 준다. t333 이 할 일은 이 판독을 페이징 끝까지 돌려(응답기 1.6.2+ 지원, t104) 결과를 해석 단계로 잇는 것이다.

## 7. t333 구현 방향 (제안 — 아직 코드 0줄)

1. `console_after` 계열 판독을 페이징 완주로 바꾼다. **부분 목록으로 "없다"를 단정하지 않는다** — `enumeration_complete` 가 거짓이면 판별기를 켜지 않고 기존 경로로 떨어진다(fail-open).
2. 기존 패치 대조 국면에서 픽스처 `Mode` 의 **앞 숫자를 슬롯으로** 써서 `DMXModes/<슬롯>` 의 이름·폭을 집는다. 이름 문자열 비교를 하지 않으므로 §6-a 를 우회한다.
3. 조인 키는 **FID** 다(§2.4 로 확증). 이름 접두로 잇지 않는다.
4. 판별기가 답을 못 내면 지금 동작(`mode_unresolved` + `mode_overrides` 안내)을 그대로 유지한다. 능력만 더하고 기존 경로를 대체하지 않는다.
5. §6-a 를 고칠지는 **별개 결정** — 정확일치 갈래에 `len(exact) == 1` 을 요구하면 오늘 8대(FixtureType 4)가 `type_unresolved` 로 떨어질 수 있다. 방어를 조이는 것이 이 쇼에서 기능을 빼앗는 방향이라 t333 에 묶지 않고 분리해 올린다.
