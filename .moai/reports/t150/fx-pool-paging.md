# t150 — fx 경로가 프리셋 풀을 끝까지 걷는다

- 카드: `t150`
- 브랜치: `WT-fx-pool-paging` · 워크트리 `.claude/worktrees/t150`
- base: `origin/main` **41aed8c** (착수 시점 fetch 후 되읽음)
- 선행: t131 (공용 페이징 루프 `server/rig/paging.py` 를 만든 카드)

## 1. 주장 (Claim)

`server/orchestrator/tools.py` 의 fx 프리셋 목적지 판독이 프리셋 풀을
**첫 창까지만** 읽고 있었다. 첫 창 뒤의 점유를 못 보면
`server/fx/instantiate.py:304` 의 `select_preset_number` 가 그것을
`preset_pool_truncated` 로 거절한다 — **오발이 아니라 fail-closed 능력 상실**이다.
t131 이 만든 공용 루프 `paged_children` 을 그 한 자리에 태워 닫았다.

## 2. 증거 (Evidence)

### 2.1 고친 자리 — 한 곳

`server/orchestrator/tools.py` `_fx_preset_destination` (기존 5758행):

- `pool_path` 를 변수로 뽑고 `paged_children(state_port, pool_path, pool_payload)` 로
  첫 창 이후를 이어 읽는다.
- 걸어서 얻은 완전성을 `rig_section` 에 실어 보낸다:
  `dict(pool_payload, truncated=truncated)`.
  `rig_section` 은 payload 의 `truncated` 를 읽으므로, 이 전달이 없으면 다 모으고도
  첫 창의 절단 플래그로 거절한다 (뮤테이션 M3 가 이 줄을 잰다).

**새로 짓지 않았다.** 루프는 `server/rig/paging.py` 하나뿐이고, 이 자리는 그것을
부르는 세 번째 호출부다 (앞의 둘: `web/presets_api.py`, `tools.py:4905`).
`test_state_paging_callsite.py::test_the_call_site_does_not_carry_its_own_loop`
가 `offset=seen` 부재로 사본 발생을 계속 감시한다 — 초록 유지.

### 2.2 검사 — offset 을 받는 더블을 **새로** 만들었다

`server/tests/test_fx_tool.py` 에 `_PagedRigStatePort` + `TestThePresetPoolIsWalkedToTheEnd`.

기존 `_RigStatePort` (`:94`, `query_state(self, path)` — `offset` 키워드 없음)는
**지우지 않았다.** 공용 루프가 TypeError 를 잡아 `truncated` 로 정직하게 강등하므로
그 더블은 「걷지 못하면 여전히 fail-closed」를 재는 대조군으로 남는다.
그 더블만으로는 이 수정을 증명할 수 없다 — 걷지 못하는 포트는 고치기 전과 뒤가
같은 답을 내기 때문이다.

단언은 `truncated is False` 가 **아니다.** 슬롯 1..30 을 연속 점유시키고
`report.preset == 31` 을 잰다 — 하나라도 빠뜨리면 그 번호가 「비었다」로 나오므로,
**모은 개수 == childCount** 와 같은 것을 도구 경로에서 잰다. 첫 창(19)만 읽는
구현은 20 을 고르므로 이 검사를 원리적으로 통과할 수 없다.

창 크기는 **불균일**하게 뒀다(19 + 11). 응답기는 개수 캡이 아니라 페이로드
예산에서 먼저 잘리므로, 「N개씩 온다」를 가정한 더블은 실기와 다른 것을 잰다.

### 2.3 뮤테이션 — 3/3 이 빨개졌다

| 뮤테이션 | 무엇을 되돌렸나 | 결과 |
|---|---|---|
| M1 | `paged_children` 제거, 첫 창만 (플래그 유지) | **2 failed** — 실패 사유가 정확히 `preset_pool_truncated` |
| M2 | 첫 창만 + `truncated = False` (플래그만 지우는 우회) | **4 failed** — 여기엔 **기존** 대조군 `test_a_truncated_pool_listing_refuses_automatic_assignment` 포함 |
| M3 | `dict(pool_payload, truncated=truncated)` → `pool_payload` | **2 failed** — 완전성 전달 줄이 load-bearing |

M1 에서 대조군 둘(`..._spends_no_follow_up_query`, `..._cannot_be_paged_is_still_refused`)은
**초록 유지** — 즉 이 카드가 안전을 깎지 않았다.
M2 가 기존 검사를 빨갛게 만든 것은 리드 배차서의 진단(그 검사가 안전 축을 지킨다)의
실증이다.

### 2.4 게이트

    uv run pytest -q                                   → 10487 passed, 12 skipped
    uv run ruff format --check server tools console    → 464 files already formatted
    uv run ruff check server tools packaging console   → All checks passed!

## 3. 기준 귀속 (Baseline-attribution)

- 트리: `.claude/worktrees/t150`, base `origin/main` 41aed8c
- 콘솔: grandMA3 onPC pid **38706**, 응답기 `--listen-port 9005`,
  `probe_preflight` → `responder_ok` / `online`
- 실기 판독은 **읽기 전용**이다. 콘솔 쓰기 0건.

## 4. 실기 전제 검증 — 카드가 미측정으로 남긴 항목의 답

카드는 `🔴안 쟀다: 실기에서 All 풀이 실제로 절단되는지` 라고 정직하게 적었다.
착수 시점에 쟀다 (2026-08-30):

| 경로 | childCount | 창 | 판정 |
|---|---|---|---|
| `DataPool/PresetPools` | 14 | [14] | 절단 없음. `All 1` = **pool 21** |
| `DataPool/PresetPools/21` (fx 가 고르는 풀) | **0** | [0] | 비었다 |
| `DataPool/PresetPools/22` (All 2) | 0 | [0] | 비었다 |
| `DataPool/PresetPools/23` (All 3) | 0 | [0] | 비었다 |
| `DataPool/PresetPools/24` (All 4) | 0 | [0] | 비었다 |
| `DataPool/PresetPools/25` (All 5) | 0 | [0] | 비었다 |
| `DataPool/PresetPools/1` (Dimmer) | 7 | [7] | 절단 없음 |
| `Patch/Stages/1/Fixtures` (대조군) | **86** | **19·18·18·18·13** | **절단 실재** |

**답: 이 쇼에서는 All 풀이 절단되지 않는다 — All 계열 5개가 전부 비어 있다.**
그러나 절단 축 자체는 이 콘솔에서 실재한다(86건이 다섯 창). 첫 창은 19개뿐이고,
19 < 24 이므로 개수 캡이 아니라 **바이트 축**에 걸린 것이다.

즉 이 카드가 닫은 결함은 **잠재적**이다: All 풀이 첫 창을 넘기는 순간
자동 배정이 통째로 거절된다. 지금 안 나타나는 이유는 코드가 고쳐져서가 아니라
**풀이 비어 있어서**다.

## 5. 안 잰 것 (Gaps)

- **실기에서 이 수정이 실제로 열어 주는 것을 못 봤다.** 재현하려면 All 풀에
  20건 넘는 프리셋을 만들어야 하고 그것은 **콘솔 쓰기**라 승인 밖이다.
  실기 확인은 「절단 축이 실재한다」(다른 경로)까지이고, 「fx 경로가 그 절단을
  넘어 배정한다」는 더블 위에서만 잰 것이다.
- `PresetPools` 목록 자체가 절단되는 경우는 안 건드렸다 — 이 카드 범위(`5758` 한 자리)
  밖이고, 실측상 14건으로 절단되지 않는다. 풀 목록이 25개를 넘는 쇼에서는
  `5724` 도 같은 계열이다.
- `collect_rig_sections` (`tools.py:1008`) 는 **손대지 않았다** — 카드가 명시적으로
  범위 밖으로 뒀고 t151 이 그 자리다.
- 실기 지문은 착수 시점 1회 측정이다. 이 쇼는 하루에도 바뀐다(리드 관측:
  `PresetPools/1` 이 6→20→7).

## 6. 잔여 위험 (Residual-risk)

- `PAGE_CAP = 10` 이므로 11창을 넘는 풀은 여전히 `truncated` 로 남아 거절된다.
  이것은 설계된 정직한 미완이지 결함이 아니다 — 다만 아주 큰 풀에서는 자동 배정이
  여전히 막힌다.
- 더블의 창 크기(19+11)는 실기 관측을 흉내 낸 것이지 실기 자체가 아니다.
  실기 창 크기는 이름 길이에 따라 변한다.
- fx 의 나머지 절반인 시퀀스 판정(`select_sequence_number`)은 `collect_rig_sections`
  를 타므로 **여전히 첫 창만 읽는다.** t151 이 닫기 전까지 그 축은 열려 있다.
