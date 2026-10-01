## 8곡 요약표 (설계 층 → 송신 층)

| 곡 | 구간 | 송신 큐·줄 | 색: 설계 이름/조합/주색 → 송신 RGB | 색 변화: 설계 주색·팔레트 → 송신 | 기구 선택 묶음(큐당 최대) | 무대 층(최대) · 다른 값 받은 그룹(8중 최대) | 포지션: 설계 → 송신 | 효과: 요청/허용/페이저 제안 큐 → 송신 줄 | 액센트: 설계 액센트·블라인더 큐 → 송신 | 드롭 앞 어둠(설계) |
|---|---|---|---|---|---|---|---|---|---|---|
| Club Diver | 13 | 14·115 | 4/3/1 → **1** | 0·5 → **0** | 1 | 2 · 2 | 8 → 8 | 12/0/12 → **0** | 3·1 → 1 | 3 |
| Cut and Run | 17 | 18·147 | 3/2/1 → **1** | 0·11 → **0** | 1 | 2 · 2 | 8 → 8 | 16/0/16 → **0** | 3·1 → 1 | 6 |
| Ice cream | 7 | 8·67 | 4/3/1 → **1** | 0·4 → **0** | 1 | 2 · 2 | 6 → 6 | 6/0/6 → **0** | 2·1 → 1 | 2 |
| Morning | 13 | 14·115 | 3/2/1 → **1** | 0·3 → **0** | 1 | 2 · 2 | 8 → 8 | 12/0/12 → **0** | 3·1 → 1 | 2 |
| Rain | 12 | 13·107 | 3/2/1 → **1** | 0·5 → **0** | 1 | 2 · 2 | 8 → 8 | 0/0/11 → **0** | 3·1 → 1 | 3 |
| Too Cool | 23 | 24·195 | 4/3/1 → **1** | 0·8 → **0** | 1 | 2 · 2 | 8 → 8 | 36/0/22 → **0** | 3·1 → 1 | 3 |
| scott-buckley-neon | 17 | 18·147 | 4/3/1 → **1** | 0·7 → **0** | 1 | 2 · 2 | 8 → 8 | 16/0/16 → **0** | 3·1 → 1 | 3 |
| 걸그룹DinoDino_C_max최고품질 | 10 | 11·91 | 4/4/2 → **2** | 2·7 → **2** | 1 | 2 · 2 | 7 → 7 | 9/0/9 → **0** | 2·1 → 1 | 1 |

## 구간 성격별 디머(설계 key_pct = 송신 전체 디머)

| 곡 | 설계≠송신 큐 | intro | verse | chorus | bridge | finale |
|---|---|---|---|---|---|---|
| Club Diver | 0 | 20~20 | 25~25 | 100~100 | 20~20 | 100~100 |
| Cut and Run | 0 | 20~20 | 25~25 | 100~100 | — | 100~100 |
| Ice cream | 0 | 30~30 | 90~90 | 100~100 | 20~20 | 100~100 |
| Morning | 0 | 100~100 | 25~90 | 100~100 | — | 100~100 |
| Rain | 0 | 50~50 | 25~70 | 100~100 | — | 100~100 |
| Too Cool | 0 | 20~20 | 25~90 | 100~100 | 50~50 | 100~100 |
| scott-buckley-neon | 0 | 50~50 | 25~90 | 100~100 | 50~50 | 100~100 |
| 걸그룹DinoDino_C_max최고품질 | 0 | 50~50 | 25~90 | 100~100 | 30~30 | 100~100 |

정본 §6 대역: intro 20~40 · verse 25~50 · chorus 80~100 · bridge 20~35 · finale 행 없음

## 정본 조항별 위반 (곡마다 위반 항목 수, readout.py violations())

| 곡 | §6 밝기 | §6 색 | §6 움직임·효과 | §6.1 | §6.2 층 | §6.3 색 | §7 상승 | §8 어둠 |
|---|---|---|---|---|---|---|---|---|
| Club Diver | 0 | 1 | 1 | 0 | 1 | 1 | 1 | 1 |
| Cut and Run | 0 | 1 | 1 | 0 | 1 | 1 | 1 | 1 |
| Ice cream | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 0 |
| Morning | 2 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| Rain | 2 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| Too Cool | 6 | 1 | 1 | 0 | 1 | 1 | 1 | 1 |
| scott-buckley-neon | 7 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| 걸그룹DinoDino_C_max최고품질 | 5 | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| **위반 곡 수** | 6 | 8 | 8 | 0 | 8 | 7 | 6 | 3 |

## 붕괴 지점별 영향 곡 수

| 붕괴 지점 | 영향 곡 수 | 곡 |
|---|---|---|
| P1 보조색 탈락 | **7/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon |
| P2 설계 주색 고정 | **7/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon |
| P3 기구 선택 한 묶음 | **8/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
| P3′ 효과 기구가 전체 값을 받음 | **8/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
| P4 층 매핑 미사용(BACK 외) | **8/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
| P5a 효과 허용 0 | **7/8** | Club Diver, Cut and Run, Ice cream, Morning, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
| P5b 페이저 제안 → 송신 0 | **8/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
| P6 디머 대역 이탈(설계) | **6/8** | Ice cream, Morning, Rain, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
| P7 후렴 이음 무변화 | **6/8** | Club Diver, Cut and Run, Morning, Rain, Too Cool, scott-buckley-neon |
| P8 드롭 앞 어둠 부재 | **3/8** | Club Diver, Cut and Run, Too Cool |
| P9 절정 블라인더 근거 없음 | **8/8** | Club Diver, Cut and Run, Ice cream, Morning, Rain, Too Cool, scott-buckley-neon, 걸그룹DinoDino_C_max최고품질 |
