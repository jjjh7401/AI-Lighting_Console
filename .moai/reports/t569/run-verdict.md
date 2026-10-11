# 카드 t569 판정 — 프리셋 칩 설명의 출처

SPEC-LDBEAT-001 REQ-LDBEAT-023(c)(칩 툴팁 = 설명 + 사용 수). 기준 트리: origin/main `0a08eef3`, 브랜치 `WT-chip-description`. 콘솔 **쓰기 0건**. 코드 변경 0줄 — 아래 §4 의 결정이 필요해 멈췄다.

## 1. 콘솔 프리셋에 설명 계열 속성이 있나 — 있다(`NOTE`)

- **속성 목록(기존 실측 재사용)**: 카드 t538 의 실기 introspect 기록(`.moai/reports/t538/r2_preset_props.txt`·`r26_preset_fields.txt`, `class: "Preset"`, `total: 138`)에서 받은 이름 135개(고유 134) 중 설명 계열은 `NOTE`·`NAME`·`TAGS`·`SCRIBBLE`·`APPEARANCE`·`INITIALNAME` 이다. 창 0·27·54·81·108·135 를 이었고, 이름 3개(80·133·134번째)는 그 기록에 없다 — 이 3개는 재지 않았다.
- **읽기 가능 여부(이번 실측)**: `uv run python -m server.tools.introspect_probe --path ShowData/DataPools/Default/PresetPools/2/1 --names NAME,NOTE --listen-port 9005 --timeout-seconds 5` → `NAME` = `"POS01 보컬 센터 페이스 · 합성좌표"`, `NOTE` = `""` (`ok: true`, `t: "string"`). 원문: `p1_props_2_1.txt`.

## 2. 칩 서랍 세 풀의 `NOTE` 전수 — 34칸 모두 비어 있다

`uv run python .moai/reports/t569/note_survey.py` — 풀은 기존 `resolve_named_pool_no` + `paged_pool_children` 로 이름으로 찾고, 칸마다 기존 `query_properties(NAME,NOTE)` 로 읽었다. 원문: `p2_note_survey.json`.

| 풀 | 슬롯 판독 | `NOTE` 읽기 성공 | 실패 | 메모가 든 칸 |
|---|---|---|---|---|
| Dimmer (1) | 7 | 7 | 0 | **0** |
| Position (2) | 16 | 16 | 0 | **0** |
| Color (4) | 11 | 11 | 0 | **0** |

감사 로그(`audit/`): 42줄 = `props_query` 35(2.1 시험 1 + 전수 34) + `state_query` 7. 쓰기 계열 0줄. `props_query` 한 번에 약 66ms(로그 시각 간격).

## 3. 시안의 「설명」이 뜻하는 것

`design/ldbeat-runbook-ui-proposal-20261008.html:332` 칩 툴팁은 `${P[id].n} · 이 곡에서 큐 N곳 사용` 이다. 같은 파일 `:268` `const P` 의 각 프리셋은 이름 둘을 따로 가진다.

- `nm` — 콘솔에 저장되는 이름. 예: `"4.21": nm "LA Cold"`, `"2.41": nm "LA Floor"`
- `n` — 툴팁의 설명. 예: `"4.21": n "차가운 흰"`, `"4.22": n "라벤더"`, `"2.41": n "Pan 0 Tilt 15"`

즉 「설명」은 콘솔 이름과 다른, 사람이 읽는 한국어 풀이다. 위치 프리셋은 Pan·Tilt 값을 풀어 쓴 꼴이다. REQ-LDBEAT-023(c) 는 출처를 정하지 않는다(예시 「펄스 30↔60 · 4박」만 있다). 참고로 이 쇼의 실제 콘솔 이름은 이미 한국어 풀이를 담고 있다(`POS01 보컬 센터 페이스 · 합성좌표`) — 시안처럼 영문 `nm` 이 아니다.

## 4. 리드 결정이 필요한 것

| 안 | 내용 | 지금 칩에 보이는 것 | 비용 |
|---|---|---|---|
| A. 콘솔 `NOTE` | 기존 판독 길에 `NOTE` 필드 추가 | 34칸 모두 빈 값 → 지금은 아무것도 안 보인다(누군가 콘솔에 메모를 적어야 보인다) | 칸마다 `props` 1회(자식 목록 응답의 항목은 `name`·`class`·`i`·`cueNo` 뿐이고 `NOTE` 는 없다 — `console/lua/copilot_responder.lua:897-907`, 여러 칸을 한 번에 읽는 동사 없음). 서랍 열 때 34회 ≈ 2.3초 |
| B. 앱이 저장한 설명 | 앱이 만든 프리셋은 앱 쪽에 한국어 설명을 두고(REQ-015(c) 「한글은 화면 설명으로만」), 쇼 원래 프리셋은 콘솔 이름을 설명으로 | 쇼 원래 프리셋은 이름이 두 번 보인다 | 앱 저장소에 필드 1개 |
| C. 값으로 풀이 | Pan·Tilt·색 값을 읽어 `Pan 0 Tilt 15` 꼴로 | 시안과 가장 비슷 | 새 판독이 필요 — 이번 카드 규칙(새 판독 금지)에 걸린다 |

## 5. 안 잰 것

- t538 기록에 빠진 속성 이름 3개.
- 세 풀 밖의 프리셋 풀(효과 풀 등)의 `NOTE`.
- `NOTE` 에 글이 든 칸을 읽는 양성 대조 — 이 쇼에 그런 칸이 없고, 쓰기 0 규칙 때문에 만들 수 없다. `NAME` 이 같은 경로로 글을 돌려준 것이 간접 대조다.
