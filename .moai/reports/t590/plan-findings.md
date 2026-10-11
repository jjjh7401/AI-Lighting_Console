# t590 plan 판독 — 새 프리셋의 「값」은 어디서 오나

기준: `WT-new-preset-store` @ origin/main `eb63ec17` · 코드 diff 0 · 콘솔 접촉 0

## 1. 내용(값) 출처 — 시안·SPEC 원문

| 출처 | 원문 | 값의 출처를 정하나? |
|---|---|---|
| 시안 `design/ldbeat-runbook-ui-proposal-20261008.html:455,527` | 「＋ 새 프리셋: 이름(영문 LA …)·값을 정하거나 명령창에 「○○ 같은 프리셋 만들어」로 AI 요청」 | 아니오 — 「값을 정한다」고만 함, 무슨 값·어떤 입력인지 없음 |
| 시안 `:645` (AI 제안 예시) | `P["2.69"]={t:"효과",pool:"m",nm:"LA Pan Wave 2 Rev",k:"s",per:2,…}` — 효과 종류·주기로 정의, 「⚠ 위상 반대 미확인」 | 효과 하나의 예시뿐(지어낸 데이터) |
| `design/ldbeat-runbook-mockup-20261008.md:36` | ③ AI: 「효과 프리셋 도구 있음(`find_fx`·`instantiate_fx`·`compose_fx`), 위치는 조준 도구(`pointing.py`) — **색 프리셋 생성**·격자 제안은 새로」 | 종류별 생성 도구를 가리킴 — 색은 도구 없음 |
| `:37` | 「콘솔은 「고친 것 콘솔에 반영」 승인 1회(새 프리셋 N개 + 다시 저장할 큐 M개 표시)에서만」 | 송신 시점만 정함 |
| SPEC REQ-LDBEAT-015 (a)~(h-6) (`spec.md:155`) | (h-2) 승인 카드에 「새로 만드는 프리셋 N개」 열거, (d) 이름 영문·숫자, (e) 앱이 만든 번호대만 덮어쓰기 | 아니오 — 번호·이름·승인 시점만, **값의 출처·생성 명령은 없음** |

결론: 값의 출처는 SPEC·시안 어디에도 정해져 있지 않다 → 카드 지시대로 구현 전 리드 판단 요청.

## 2. 지금 코드가 하는 것 (실측 grep)

- `server/design/beat_grid_edit.py:520-522` — `new_preset_label` 은 받아서 영문 검사만 하고 **저장하지 않는다**(`:539` merge 에서 빠짐, `:676` 보고 문장에만 「콘솔 생성은 별도 송신 경로」).
- 초안 데이터에 새 프리셋의 값을 담는 자리가 없다(`BeatGridCue` 는 번호만).
- `server/design/beat_grid_emit.py` — `Store Preset` 0줄(`Store Cue`·`Store Sequence` 만). t589 의 「Store Cue 만 보냄」과 일치.
- UI `BeatGrid.tsx:2237` 등 — 「이름·값을 정하는 창은 아직 배선되지 않았습니다」(창은 t589 lane-2 진행 중).

## 3. 콘솔 명령 문법 — 저장소 선례 (재발명 금지)

| 선례 | 꼴 | 상태 |
|---|---|---|
| `server/presets/store.py` | `Store Preset <pool>.<n>` + `Label Preset <pool>.<n> '<label>'` — 「문형을 아는 유일한 일반형 자리」, 라벨 거부 술어 포함 | 기존 빌더 |
| `server/looks/instantiate.py:459-479` | `Clear` → 선택 → 속성 값 줄 → `Store Preset` → `Label Preset` → `Clear` (값을 프로그래머에 넣고 저장) | 그룹 선택형 일부만 실측(`:329-330` 「additive form awaits M7 live」) |
| `server/fx/instantiate.py:177,717-737` | `Store Preset <pool>.<n> /Universal` + 별도 `Label Preset`(인라인 라벨은 실기 2026-08-16 문제) | live-verified |
| `server/spatial/pointing.py:368-373` | 위치 프리셋 `Store Preset 2.<n>` + Label (조준 결과 값) | 기존 경로 |

→ 문법은 실측 선례가 있다. t582 실기 확인 목록에 새로 올릴 것은 「beat grid 승인 배치 안에서 이 꼴을 섞어 보냈을 때」뿐.

## 4. 안 잰 것 / 위험

- `Store Preset` 은 기존 슬롯을 **경고 없이 덮어쓴다**(`session.py:5695,5790`). 새 번호가 쇼에 이미 있는 슬롯인지 송신 전에 확인하는 경로를 아직 확인하지 않았다(서랍 `read_named_pool` 이 쓸 수 있는지 미확인).
- Store Preset 에는 **선택(그룹)** 이 필요하다 — 트랙 그룹 번호 미확인(`group_no_confirmed=false`) 칸은 만들 수 없다.
- 프리셋 값을 콘솔에서 읽어 복사하는 리더(「○○ 같은 프리셋」)가 있는지 확인하지 않았다.
