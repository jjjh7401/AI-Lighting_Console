# t332 — Aura XB 모드는 읽힌다: `mode_overrides` 값 확정

- 카드: t332 (AC-LXSEQ-016 ③)
- 측정: 2026-09-08, 실기 onPC, 응답기 1.6.5, 트리 `.claude/worktrees/t332` @ `3df5457`
- 콘솔 쓰기: **0건** (`apply.entered = false`, `write_count_planned = 0` — 두 회차 모두)

## 1. Claim (주장)

1. 콘솔에 패치된 Martin MAC Aura XB 24대의 DMX 모드는 **판독 가능하다**.
2. 24대 전부 `1 Extended - Extended` 이며, 도구가 요구하는 콘솔 모드 이름은 `Extended - Extended` 다.
3. `mode_overrides {"Martin MAC Aura XB": "Extended - Extended"}` 를 넣으면 AC-016 ③ 의 재preview 조건이 **양쪽 다** 충족된다 — 런 0 · `already_patched 86`.

## 2. Evidence (증거)

### 2.1 콘솔 생존 + 포트

```
uv run python -m server.tools.responder_roundtrip --port 8000 --listen-port 9005 \
  --skip-exec --path "DataPool/Groups"
```
```
  [PASS] ping: ok
         live version=1.6.5 plugin=CopilotResponder
  [PASS] state: ok
         node={'childCount': 18, 'class': 'Groups', ...} children=18
result: PASS
```
회신 포트는 **9005**. (문서가 말하는 9000 은 낡음 — t327 에서 확정.)

### 2.2 판독 채널의 존재 — 픽스처 노드에 `MODE` 프로퍼티가 있다

```
uv run python -m server.tools.introspect_probe \
  --path "Patch/Stages/1/Fixtures/1" --listen-port 9005 --all-pages
```
→ `total: 108`, `paging: "complete"`. 이름 목록에 `MODE` 포함(그 밖에 `MODEDIRECT`, `BREAK1..8`, `ISMULTIPATCH` 등).

### 2.3 대조군 두 팔 — 채널이 진짜 값을 답하는지

**대조 A — 다른 타입은 다른 값을 답해야 한다.** 픽스처 1 은 CSV 상 `ETC S4 LED S3 Lustr X8 / Direct 12ch`:
```
uv run python -m server.tools.introspect_probe \
  --path "Patch/Stages/1/Fixtures/1" --names "MODE,NAME" --listen-port 9005
```
```
"n": "MODE",  "v": "3 Direct"
"n": "NAME",  "v": "KEY 101"
```
Aura 의 `1 Extended - Extended` 와 **다른 값**이다 → 상수 응답이 아니다.

**대조 B — 없는 대상은 거절되어야 한다.** 날조 인덱스 999:
```
uv run python -m server.tools.introspect_probe \
  --path "Patch/Stages/1/Fixtures/999" --names "MODE,NAME" --listen-port 9005
```
```
props failed: path segment not found: '999' (in Patch/Stages/1/Fixtures/999)
```
조용한 기본값이 아니라 **하드 실패**다 → `ok` 를 증거로 쓸 수 있다.

**세 번째 팔(부수 확인)** — 같은 요청 안의 `FIXTUREID` 는 `ok: false / "property not readable: FIXTUREID"` 로 돌아왔다. 즉 이 채널은 프로퍼티별로 가부를 가른다. `MODE` 의 `ok: true` 는 "전부 true 로 답하는 채널"의 산물이 아니다.

### 2.4 24대 전수 판독

콘솔 슬롯 43~66 (`BACK 201-212` · `SIDE-L 301-306` · `SIDE-R 311-316`). CSV 의 Aura 24행과 FID 가 1:1 대응한다.

전수 결과 → `aura-console-modes.tsv`. 분포:
```
  24  1 Extended - Extended
```
**24/24 동일.** 갈라지는 픽스처 0건.

### 2.5 도구가 요구하는 이름과의 일치

기준선 preview 의 skip detail(원문, `preview-base.json` → `payload.plan.skipped[42].detail`):
```
모드를 확정하지 못했다 — 실측 모드: [Extended - Extended(25), Extended - RAW(25),
Extended - RGB(25), Standard - Extended(14), Standard - RAW(14), Standard - RGB(14)].
mode_overrides: {"Martin MAC Aura XB": "<콘솔 모드 이름>"} 로 재호출하라.
```
매칭 규칙은 `server/lxseq/mapper.py:_resolve_mode` 의 `c.name.lower() == override.lower()` — 대소문자 무시 **완전일치**. 콘솔이 답한 `1 Extended - Extended` 에서 앞의 `1 ` 은 모드 인덱스 접두이고, 이름 부분 `Extended - Extended` 가 실측 목록의 첫 항목과 바이트 일치한다. 대시 양쪽에 **공백이 있다** — 카드 본문의 `Extended-Extended` 표기는 축약이며 그 문자열로는 매칭되지 않는다.

### 2.6 재preview 검산

```
uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview \
  --listen-port 9005 --mode-overrides '{"Martin MAC Aura XB": "Extended - Extended"}'
```

| | 기준선(override 없음) | override 적용 |
|---|---|---|
| `runs` | 0 | 0 |
| `write_count_planned` | 0 | 0 |
| `skipped_total` | 86 | 86 |
| `already_patched` | **62** | **86** |
| `mode_unresolved` | **24** | **0** |
| `types_unresolved` | [] | [] |
| `apply.entered` | false | false |
| `is_error` | false | false |

기준선 숫자(62 + 24)는 카드가 기록한 2026-09-07 실측과 **일치** — 전제가 만료되지 않았다.

## 3. Baseline-attribution (baseline 귀속)

- 트리: `.claude/worktrees/t332`, 브랜치 `WT-aura-mode-read`, `git log -1` → `3df5457`
- 원격 동기: `git rev-list --count --left-right origin/main...HEAD` → `0 0` (pull 후)
- 큐: `moai todo` 총 277행 · `queued 73` · `picked 17` · `dropped 187` (필드 기준 집계)
- 실기 응답기: `1.6.5` (main 코드와 대조 안 함 — §5 참조)
- 증거 원문: `preview-base.json` · `preview-override.json` · `aura-console-modes.tsv` (모두 이 디렉터리)

## 4. Gaps (미검증)

1. **AC-016 ② (`status created` 합 86)** — 이 쇼로는 원리적으로 못 잰다. 시작 상태가 빈 패치여야 하는데 콘솔에 이미 86대가 있다. 재지 않았다.
2. **AC-016 ④ (`address_occupied` 실기)** — 측정하지 않았다.
3. **`apply` 경로** — 한 번도 타지 않았다. override 가 실제 쓰기에서도 같은 폭(25)으로 자리를 잡는지는 코드 독해(`matched.width`)까지만이고 실측이 아니다.
4. **다른 6종 모드에 대한 override 매칭** — `Extended - Extended` 하나만 실측했다. `Standard - RAW` 등 나머지 5종이 같은 형식으로 매칭되는지는 재지 않았다(대조군 하나면 결론도 그만큼만 넓다).
   > **2026-09-08 후속 — 넓혔다.** 이 쇼의 타입 8종 전수에서 픽스처 `Mode` 문자열이 `"<라이브러리 DMXModes 슬롯> <모드 이름>"` 형식임을 확인했다 — 앞 숫자는 슬롯과 8/8 일치, 뗀 이름은 라이브러리 이름과 8/8 일치(86대). 다만 이는 **슬롯→이름 대응**의 확인이고 `Standard - RAW` 등 미사용 모드로 실제 override 를 걸어 본 것은 아니다(이 쇼에 그 모드의 픽스처가 없다). 측정: `.moai/reports/t333/preconditions.md` §2.3.
5. **CSV↔콘솔 FID 대응** — 이름 접두(BACK/SIDE-L/SIDE-R)와 번호로 맞췄고, 24개 각각의 FID 는 읽지 못했다. 대응은 **이름 기반 추론**이며 FID 판독으로 확증한 것이 아니다.
   > **2026-09-08 정정 — 이 gap 은 닫혔고, 사유 진술이 틀렸다.** 원문은 `property not readable: FIXTUREID` 를 근거로 「FID 판독 불가」라고 적었다. 실제 프로퍼티 이름은 **`FID`** 다(`server/tools/lxseq_e2e.py:200` — 하네스가 `("FID", "Patch", "FixtureType", "Mode")` 를 읽는다). `FIXTUREID` 는 존재하지 않는 이름이라 옳게 실패한 것이고, 채널의 한계가 아니었다. `FID` 로 다시 재니 86/86 판독되고 전부 CSV 에 있으며 시작 주소가 86/86 일치(불일치 0) — 대응은 **값으로 확증**됐다. 측정: `.moai/reports/t333/preconditions.md` §2.4.
6. **응답기 버전 대조** — 실기 1.6.5 가 이 트리의 `console/lua/copilot_responder.lua` 와 같은 빌드인지 확인하지 않았다. 과거에 실기 1.6.1 / main 1.6.2 로 갈린 전례가 있다.

## 5. Residual-risk (잔여 위험)

- **모드는 사람이 바꿀 수 있다.** 이 판독은 2026-09-08 시점의 쇼 상태다. 쇼파일이 교체되거나 누가 모드를 바꾸면 `Extended - Extended` 는 만료된다 — 착수 시점에 §2.4 를 다시 떠라.
- **24대가 지금 균일하다는 것이 앞으로도 균일하다는 뜻은 아니다.** `mode_overrides` 는 타입 단위 키라 타입 하나에 값 하나뿐이다. 같은 타입이 두 모드로 섞이는 쇼에서는 이 해법 자체가 부족하다(도구의 `resolution_key` 는 (타입, 폭, 라벨) 3중이라 폭이 갈리면 해석은 갈리지만, override 는 타입 키 단독이다).
- **③ 통과가 AC-016 통과는 아니다.** ②가 빈 쇼를 요구하므로 오늘 쇼로는 ③까지가 한계다 — 카드의 판단 그대로다.

## 6. 새로 알게 된 것 (카드 범위 밖 — 구현하지 않음)

도구는 모드를 **라이브러리**에서 읽는다(`server/prechk/mode_read.py:read_type_mode_widths` → `<FixtureTypes root>/<슬롯>/Modes` 를 열거하고 각 모드의 footprint 를 잰다). 그래서 폭 25 에 후보가 3개 남으면 거기서 멈춘다 — t128 의 "폭은 판별기가 아니다"가 정확히 이 자리다.

그런데 **이미 패치된 픽스처는 자기 모드를 문자열로 답한다**(§2.2~2.4). 즉 "기존 패치와 같은지 판정"하는 국면에서는 라이브러리 후보 목록이 아니라 픽스처의 `MODE` 를 읽는 것이 직접적인 판별기다. 라이브러리 판독으로는 원리적으로 못 좁히는 것을 픽스처 판독으로는 좁힐 수 있다.

이건 t332 가 요구한 범위(값 확정)를 넘는 **도구 변경**이라 하지 않았다. 후속 카드 후보로 남긴다:
> 기존 패치 대조 국면에서 `Patch/Stages/1/Fixtures/<슬롯>` 의 `MODE` 를 읽어 라이브러리 폭 중복을 해소한다 — 사람에게 `mode_overrides` 를 되묻는 왕복을 없앤다. ⚠️전제: §4 의 gap 4·5 를 먼저 닫아야 한다(다른 모드 이름 형식 · FID 대응 확증).
