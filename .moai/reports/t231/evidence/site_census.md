# t231 — 풀 탐색 자리 전수 (착수 시점 census)

기준: `.claude/worktrees/t231` · base `origin/main 09bd3a7` · 2026-09-01 · 콘솔 접촉 0

## 명령줄

    grep -rn "casefold().startswith" server/ --include="*.py" | grep -v "^server/tests"

출력 7건 중 풀 탐색은 5건이다. 나머지 둘은 풀 탐색이 아니다 —
`tools.py:667` 은 코드펜스 판별, `lxseq/preset_parser.py:244` 는 토큰 매칭.

## 시트 쪽 다섯 자리 (전부 `server/orchestrator/tools.py`)

| 줄 | 자리 | 잘림 방어 | 다중 일치 |
|---|---|---|---|
| 5015 | `_preset_pool_number` (카드가 지목한 자리) | **없음** — 맨 `query_state`, 페이징 없음 | 첫 일치 `return` |
| 5579 | `import_lxseq_cues` 프리셋 시트 조인 | `paged_children` 호출하되 반환된 절단 플래그를 `_truncated` 로 **버림** | 첫 일치 `break` |
| 5657 | FX 풀 (`all` 접두) | 같음 — 버림 | 첫 일치 `break` |
| 5718 | Position 풀 | 같음 — 버림 | 첫 일치 `break` |
| 6752 | `_fx_preset_destination` (`all` 접두) | **없음** — 맨 `query_state` | `all_pools[0]` |

## 대화 쪽 한 자리

`server/web/session.py:5739 _resolve_named_pool_no` — 완전 일치, 그리고
절단 플래그 **또는** childCount 산술로 절단을 잡아 `None`(거부).
주석 그대로: 절단된 목록에 대상 풀이 없다 != 풀이 없다, 모름은 거부다.
호출자 셋(Color · Dimmer · All 1)이 이 한 몸통을 공유한다 — 사본 3본을
2026-08-17 리뷰에서 합친 것이다.

## 결함 축은 둘이다

- **D1 — 접두 일치 + 첫 일치**: 다섯 자리 전부. 다중 일치를 거절하지 않는다.
- **D2 — 잘림을 부재로 읽음**: 다섯 자리 전부. 형태가 둘 —
  페이징이 아예 없는 둘(5015 · 6752), 페이징은 하고 절단 플래그를 버리는 셋(5579 · 5657 · 5718).

## 다중 일치 거절을 한 벌로 통일하면 깨지는 자리

5657 과 6752 의 접두어는 `all` 이고, 이 쇼파일 풀 목록에 `All 1` ~ `All 5`(21~25)가 있다
(t216 2단계 판독값). 즉 이 두 자리에서 **다중 일치는 예외가 아니라 정상 상태**이고,
코드도 그것을 의도한다 — `_fx_preset_destination` 독스트링:

    The pool defaults to the first pool whose NAME starts with "All"

**기존 검사가 이 의도를 고정하고 있다.** `server/tests/test_fx_tool.py:1003` 의 기본 풀 목록이
`All 1`(21)과 `All 2`(22) **둘**을 싣고, 같은 파일 1122행이 `Store Preset 21.` 로 시작하는
명령을 단언한다 — 즉 **첫 All 이 이기는 것**이 계약이다.
한 벌 거절 술어를 넣으면 이 검사가 빨개진다.

따라서 술어는 하나가 아니라 **둘**이어야 한다: 계열 조회(유일 일치 요구)와
All 계열 조회(명시적으로 첫째를 고르는 것). 지금은 둘이 같은 접두 일치 한 줄이라
의도가 코드에서 안 갈린다.
