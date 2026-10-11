# t557 run 판정서 — 효과 드롭다운이 효과 종류를 고정하던 결함

- 카드: t557 (t558 은 리드 결정으로 t577 로 옮겨 닫힘)
- 브랜치: `WT-effect-approval-pick` · 기준 `fc268e9b` (origin/main 대비 `0 0`, 착수 직전 fetch 후 측정)
- 판정: **PASS (lane 자체 판정 — 최종 판정은 리드)**

## 1. 결함 (재현으로 확인)

`ui/src/components/BeatGrid.tsx` 의 `buildEffectPresetChanges` 가 `effect_kind: "position"` 을 고정으로 보냈다.
코드를 읽어 보니 결함이 하나 더 있었다.

- 움직임 효과 드롭다운: 무엇을 골라도 `effect_kind: "position"`.
- 위치·색 드롭다운: 효과 번호대 항목(`is_effect_band: true`)도 목록에 나오는데, 고르면 효과가 아니라 **일반 위치/색 프리셋 번호**(`position_preset_no` / `color_preset_no`)로 저장됐다. 효과 종류도 번호대 검사도 엉뚱한 쪽으로 갔다.

RED 증거: `red-1.txt` — 새 시험 7건 실패 / 140 통과 (구현 전).

## 2. 고친 것

| 파일 | 변경 |
|---|---|
| `ui/src/components/BeatGrid.tsx` | `buildEffectPresetChanges(presetNo, kind)` 로 종류를 인자로 받음. `presetPickChanges(section, pool, presetNo)` 추가 — 고른 항목이 효과 번호대면 `{effect_preset_no, effect_kind: <풀 종류>}`, 아니면 그 풀의 기본 필드. 위치·색·움직임 효과 세 적용 지점이 모두 이 규칙 하나를 탄다. 위치·색 목록의 효과 항목엔 ` · 효과` 표시. 무버가 아닌 칸의 효과 행은 읽기 전용. |
| `ui/src/components/BeatGrid.test.tsx` | `presetPickChanges` 시험 7건 (색 효과 → `color`, 색 기본 → `color_preset_no`, 위치 효과/기본, 모르는 번호·섹션 없음 → 기본 필드, `kind` 인자, 라벨 표시, 적용 지점 3곳이 모두 규칙을 타는지 소스 검사) |
| `server/tests/test_beat_grid_effect_kind_t557.py` | 서버 쪽 증명 — 같은 색 효과 번호를 `effect_kind="color"` 로 보내면 번호대 경고 없음, `"position"` 으로 보내면 번호대 경고. 번호는 `preset_pools.yaml` 에서 읽음(코드에 번호 없음). |

장비·곡·프리셋 번호 상수는 코드에 넣지 않았다. 종류 판정은 서버가 준 `is_effect_band`(= `preset_pools.yaml`)만 쓴다.

## 3. 증거 (이 트리에서 실행)

| 검사 | 명령 | 결과 | 파일 |
|---|---|---|---|
| RED | `npx vitest run src/components/BeatGrid.test.tsx` (구현 전) | 7 failed / 140 passed | `red-1.txt` |
| UI 전체 | `npx vitest run` | 47 files, **1082 passed** | `vitest.txt` |
| 타입 | `npx tsc --noEmit` | exit 0, 출력 없음 | `tsc.txt` |
| 서버 증명 | `uv run pytest server/tests/test_beat_grid_effect_kind_t557.py` | 2 passed | (전체 실행에 포함) |
| Python 전체 | `uv run pytest -q -p no:cacheprovider` | exit 0 · **15170 passed**, 35 skipped | `pytest-full.txt` |
| 린트 | `ruff format` + `ruff check` (새 .py 둘) | unchanged / All checks passed | — |

## 4. t558 거절 재현 (리드 요청)

앱 드롭다운이 지금 보내는 모양(승인 없음) 그대로 새 효과 번호를 넣으면 서버가 거절한다.

명령: `uv run python .moai/reports/t557/t558_reject_repro.py` → `t558-reject-repro.txt`

```
REJECTED {'effect_preset_no': '2.63', 'effect_kind': 'position'} -> 프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반
REJECTED {'brightness': {'mode': 'dimmer_effect', 'value_percent': None, 'preset_no': '1.21'}} -> 프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반
```

이 카드는 이 거절을 고치지 않는다. 시안은 승인을 「⇪ 콘솔에 반영」 카드에서만 그리므로, 승인 대기 → 반영 시 승인 기록은 t577 몫이다.

## 5. 안 잰 것 (Gaps)

- **앱 화면을 띄워 눌러 보지 않았다.** 드롭다운 동작은 순수 함수·정적 렌더 시험으로만 확인했다.
- **혼합(mixed) 효과는 고를 수 없다.** 서랍(`build_preset_drawer`)이 Dimmer/Position/Color 풀만 내고 All 풀은 없다. `buildEffectPresetChanges` 는 `"mixed"` 를 받지만 그 값을 보내는 UI 경로는 없다.
- **디머 효과**는 이 카드에서 건드리지 않았다 — 기존 밝기 「디머 효과」 모드 경로 그대로.
- **새 효과 번호는 여전히 서버에서 거절된다**(§4) — t577 전까지.
- 콘솔: 읽기·쓰기 모두 0회.

## 6. 잔여 위험

- 위치 드롭다운에도 효과 번호대 항목이 계속 보인다(서랍이 같은 Position 섹션을 준다). 고르면 이제 위치 효과로 저장되지만, 사람이 「위치」 칸에 효과가 들어간 것을 헷갈릴 수 있어 ` · 효과` 표시를 붙였다.
- 서랍 항목에 없는 번호는 일반 프리셋으로 간주한다 — 효과 번호대 판정은 서랍 항목에 기대므로.
