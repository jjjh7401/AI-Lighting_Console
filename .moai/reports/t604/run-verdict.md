# t604 run 판정 — 혼합 효과 번호대 22.0 시작(슬롯 0) 질문

판정: **코드 무변경 — 실측 근거 없음, 실기 항목으로 돌림** (리드 지시: 「실측 근거가 없으면 고치지 말고 실기 항목으로」). 콘솔 접촉 0.
트리: `WT-mixed-band-slot` @ origin/main `d04b0a3d`

## 질문
`server/design/beat_grid_data/preset_pools.yaml` 의 `mixed_all: {start: "22.0", end: "22.99"}` 때문에, 「＋ 새 프리셋」 창의 혼합 효과 첫 배정은 슬롯 0(`22.0`)이 된다. MA3 프리셋 풀이 슬롯 0 을 받는가?

## 찾은 것 (저장소 판독 기록 grep)
1. **슬롯 0 을 잰 기록은 없다.** `.moai/reports` 전체에서 `"i": 0` 이 들어간 파일은 2개뿐이다(`t501/ac016/rehearse_rain_212/analysis.json`, `t509/evidence/app_sections.json`). 둘 다 곡 **구간** 번호이고 프리셋 풀이 아니다. 메모리와 SPEC 문서에도 슬롯 0 실측은 없다.
2. **풀 22 의 실제 판독**: `.moai/reports/t543/r1_pools.json` → `PresetPools/22` = `{"name": "All 2", "childCount": 1, children: [{"i": 1, "name": "Piano Solo"}]}`. `.moai/reports/t150/fx-pool-paging.md:87` → 그때는 비어 있었다(0). 지금까지 관측된 모든 풀 자식의 `i` 는 1 이상이다. 하지만 **부재는 거절의 증거가 아니다.** 「아무도 0 에 저장해 본 적 없다」와 「0 은 저장할 수 없다」를 가를 증거는 없다.
3. 그래서 `start` 를 `22.1` 로 고치는 것도, 그대로 두는 것도 근거가 없다. 둘 다 하지 않았다.

## 덤으로 찾은 것 — 혼합 풀 이름과 번호대가 서로 다른 풀을 가리킨다 (새 카드 요청)
- 같은 판독(`t543/r1_pools.json`)에서 이름 **"All 1" = 풀 21**, **"All 2" = 풀 22** 이다.
- 코드는 혼합 종류를 이름 **"All 1"** 로 해석한다(`server/design/beat_grid_presets.py:59,65` — `EFFECT_SEARCH_POOL_NAMES`, `_POOL_NAME_TO_EFFECT_KIND`). 그런데 번호대는 **22.x** 다(`preset_pools.yaml:31`).
- 창의 번호 배정 `first_free_preset_number`(`beat_grid_presets.py:315`)는 `console_children` 의 **풀 번호를 대조하지 않는다**. 그래서 이 리그에서는 풀 21(All 1)의 빈칸을 보고 22.x 를 고른다. 풀 22 의 실제 점유(슬롯 1 "Piano Solo")는 창에서 보지 않는다.
- **덮어쓰기는 막혀 있다.** 반영 때 t590 가드와 t598 송신 직전 재판독이 번호(22)로 풀을 다시 다 읽기 때문이다. 틀리는 건 창의 배정(예: 이미 있는 22.1 을 고름 → 반영 때 「슬롯 있음」이 되어 기존 프리셋을 참조하는 칸이 됨)과 드로워 검색 범위다.
- 이건 t604 범위 밖이라 고치지 않았다. 리드에게 카드로 요청한다.

## 실기 항목 요청 (t606)
- `Store Preset 22.0` 이 받아들여지는지 확인한다(빈 테스트 프로그래머, 직후 `PresetPools/22` 를 되읽어 `i: 0` 자식이 생겼는지 본다 → 끝나면 지움). 받아들여지면 그대로 두고, 거절되거나 1 로 바뀌면 `start` 를 `22.1` 로 고친다(t603 시험의 `startswith("22.")` 는 영향 없음).

## 안 잰 것
- 실기 콘솔 0회. 쇼 파일마다 풀 이름(All 1/All 2)이 다를 수 있다. 위 판독은 t543 시점의 쇼 하나다.
