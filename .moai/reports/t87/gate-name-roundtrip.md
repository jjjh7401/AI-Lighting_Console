# t87 착수 게이트 — 이름 왕복 바이트 대조

판정: **PASS** (compared 6 · byte_equal 6 · gate_pass true)

리드가 정한 축 (a) per-record hold 는 「콘솔이 CSV Name 을 바이트 그대로 저장한다」에
의존한다. 이름이 한국어라 절단·정규화·트림 위험이 있어, 구현 착수 **전에** 실측했다.

## 계기 신뢰성 — 날조 대조군

- 경로 `Patch/FixtureTypesZZZNotAThing/9999` → `ok = false` (거절이 정답)
- 같은 채널로 `DataPool/PresetPools/1` → `ok = true`, `truncated = false`, 6건
- 대조군이 거절되고 실경로가 읽혔으므로 이 판독은 증거다.

## 대조 결과

| # | CSV Name | CSV bytes (hex) | 콘솔 Name | 콘솔 bytes (hex) | byte_equal |
|---|---|---|---|---|---|
| 0 | 풀 | ed9280 | 풀 | ed9280 | true |
| 1 | 쇼 하이 | ec87bc20ed9598ec9db4 | 쇼 하이 | ec87bc20ed9598ec9db4 | true |
| 2 | 미드 | ebafb8eb939c | 미드 | ebafb8eb939c | true |
| 3 | 로우 | eba19cec9ab0 | 로우 | eba19cec9ab0 | true |
| 4 | 잔광 | ec9e94eab491 | 잔광 | ec9e94eab491 | true |
| 5 | 아웃 | ec9584ec9b83 | 아웃 | ec9584ec9b83 | true |

공백을 품은 `쇼 하이` 가 `20` 을 그대로 유지했고(트림 없음), 단음절 `풀` 도
NFC 조합형 그대로다(분해 없음). casefold/strip/NFC 변형 비교도 전부 참이라
「어떤 관대한 비교로만 맞는다」가 아니라 **바이트가 같다**.

## 미검증 (Gaps)

- **이 6건만 쟀다.** col/bm 시트는 저장 가능 0건이라 콘솔에 이름이 없다 —
  다른 계열의 이름 왕복은 미측정이다.
- **길이 상한 미측정.** 이 6개는 전부 짧다. 콘솔이 긴 이름을 자르는지는 안 쟀다.
- **값 일치는 여전히 안 읽힌다.** 이 게이트는 *이름*만 답한다.

## 카드 문면 정정 1건

카드는 「사고로 생긴 DIM.FULL(슬롯 1)」이라고 적었지만, 콘솔 슬롯 1 의 이름은
`DIM.FULL` 이 아니라 **`풀`** 이다. 콘솔에 나가는 것은 `preset_id` 가 아니라
`record.name` 이기 때문이다(`preset_store_commands(pool_no, slot, placement.name)`).
결함 자체는 그대로지만, 이름 비교를 `preset_id` 로 구현하면 6건 전부 안 맞는다.

## 결함 재현 (읽기 전용)

`--action preview --limit 0` (승인 통로 0, 명령 조립 0):

- 풀에 이미 6건 점유 (슬롯 1..6)
- 매퍼 `planned` 슬롯 = **7, 8, 9, 10, 11, 12**
- `held` = 빈 목록

같은 CSV 를 다시 쏘면 6건이 통째로 복제된다 — 카드의 주장이 실기로 재현됐다.

## 재현 명령

```
.venv/bin/python -m server.tools.lxseq_presets_e2e \
  --preset-csv "$PWD/src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv" \
  --action preview --limit 0 --listen-port 9005
```

이름 대조 원자료: `name-roundtrip.json` (같은 디렉터리).

주의 — 배차서는 `--probe-only` 를 지정했으나 그 갈래는 프리셋 풀을 **읽지 않는다**
(`lxseq_presets_e2e.py:186-187` 에서 기준선만 읽고 멈춘다). 풀 이름이 나오는 유일한
읽기 전용 경로가 `--action preview`(승인 없음)라 그것을 썼다. preview 는 명령을
만들기 전에 반환하므로(`tools.py:4863`) 콘솔 쓰기는 0 이다.
