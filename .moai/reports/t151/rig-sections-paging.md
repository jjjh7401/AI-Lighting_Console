# t151 — `collect_rig_sections` 도 섹션을 끝까지 걷는다

- 카드: `t151` · 브랜치 `WT-rig-sections-paging` · 워크트리 `.claude/worktrees/t151`
- base: `origin/main` **f47c5f5** (t150 이 들어간 커밋, 착수 시점 fetch 후 되읽음)
- 선행 계열: t131(공용 루프 신설) → t150(fx 프리셋 목적지) → **t151(rig 섹션, 셋째)**

## 1. 주장 (Claim)

`server/orchestrator/tools.py` 의 `collect_rig_sections` 가 섹션마다
`state_port.query_state(path)` 를 **한 번씩만** 불러 첫 창에서 멈췄다. t131·t150 과
같은 결함이고 다른 것은 **폭발 반경**이다 — 이 함수는 호출부 8곳이 공유하고 한 호출이
최대 10섹션을 답한다. `paged_children` 을 그 한 자리에 태워 닫았다.

## 2. 실기 실측 — 카드 물음 (a)

2026-08-30, grandMA3 onPC 2.4.2 pid **38706**, `--listen-port 9005`,
`probe_preflight` → `responder_ok` / `online`. **읽기 전용, 콘솔 쓰기 0건.**
`DEFAULT_RIG_CONTEXT_PATHS` 10섹션 **전수**:

| 섹션 | 경로 | childCount | 창 | 절단 |
|---|---|---|---|---|
| fixture_types | `Patch/FixtureTypes` | 15 | `[15]` | — |
| **fixtures** | `Patch/Stages/1/Fixtures` | **86** | **19·18·18·18·13** | **✔** |
| groups | `DataPool/Groups` | 18 | `[18]` | — |
| sequences | `DataPool/Sequences` | 1 | `[1]` | — |
| preset_pools | `DataPool/PresetPools` | 14 | `[14]` | — |
| macros | `DataPool/Macros` | 0 | `[0]` | — |
| plugins | `DataPool/Plugins` | 9 | `[9]` | — |
| pages | `DataPool/Pages` | 1 | `[1]` | — |
| matricks | `DataPool/MAtricks` | 0 | `[0]` | — |
| worlds | `DataPool/Worlds` | 1 | `[1]` | — |

**10개 중 1개만 절단에 닿는다.**

### 🔴 이 표가 개수 판별기를 죽인다

`groups` 는 **18건인데 안 잘리고**, `fixtures` 는 **19건에서 잘린다.** 한 개 차이로
결과가 갈린다. 개수 캡은 24 이므로 19 는 그 아래이고, 즉 걸린 축은 **바이트**다
(이름 길이). 「N개 이상인 섹션만 페이징한다」는 판별기는 이 한 쌍으로 원리적으로
불가능하다 — t131 모듈 독스트링이 경고한 그 판별기를, 이 쇼가 직접 반증한다.

다음에 누가 그 판별기를 다시 제안하면 이 두 행이면 끝난다.

## 3. 카드 물음 (b) — 전부 페이징. 비용은 실재하는 데서만 난다

`paged_children` 은 절단 주장이 없으면 **후속 조회를 쏘지 않는다**(`claims_more`
False → 즉시 반환). 위 실측에서 **10섹션 중 9섹션이 왕복 0**이다. 「전부 페이징」의
비용은 「절단 섹션만 페이징」과 실측상 같다.

반대로 「절단 실재 섹션만」은 고정 목록을 만드는 것인데, §2 가 그 목록을 개수로 고를
수 없음을 보였고 쇼마다 바뀐다. **노화하는 판별기를 새로 짓는 것은 이 자리가
없애려는 결함과 같은 형태다.** `drill_into` 예산과는 축이 다르므로(자식을 컨테이너로
여는 비용 vs 섹션 자체를 읽는 비용) 상한은 `PAGE_CAP=10` 하나로 둔다.

리드 판정으로 이 갈래를 채택했다.

## 4. 카드 물음 (c) — 소비자 추적. 걸리는 것은 안전장치 하나다

호출부는 **8곳**이다(카드 문면의 「섹션 10개」는 한 호출의 섹션 수):

| 호출부 | 섹션 | 절단 닿음 | 절단 신호 소비 |
|---|---|---|---|
| 2101 `get_rig_context` | 10개 전부 | fixtures | 모델에게 요약(읽기) |
| 2196·2314 look | groups, preset_pools | — | |
| 2535 songcue | groups, sequences | — | |
| 4710 `import_lxseq_groups` | groups, fixtures | fixtures | **없음** (§6 참조) |
| 5661 fx | groups, sequences | — | `select_sequence_number` |
| 6274 scene | groups, sequences | — | |
| 7712 `create_arrangement_groups` | groups, fixtures | fixtures | **안전장치** |

절단되는 섹션(`fixtures`)의 신호를 실제로 **소비**하는 자리는 7712 하나다:

    7736  fixtures_total = fixtures_section.get("total")   # 86
    7737  arrived = len(fixtures_section.get("objects"))    # 페이징 전 19
    7745  shortfall = max(total - arrived, 0)               # 67 → 0

`@MX:ANCHOR` 가 붙은 부분판독 쓰기 거절(SPEC-COPILOT-TRUNCATE-001 REQ/AC-TRUNCATE-008,
mutation-required)이다. 페이징 후 shortfall 이 0 이 되면 `topology_partial` 그룹은
**어떤 인정 목록으로도 통과하지 못한다** — 7630 이 non-empty 를 요구하고 7664 가
`len != 0` 을 거절하기 때문이다.

**이것은 설계된 동작이다.** 7669-7671 의 에러 문면이 그 경우의 처방을 이미 이름 짓고
있다: *"if the container now lists the whole rig, re-run classify_arrangement_topology
and write its fresh groups instead."* 19/86 판독 위에서 만든 그룹은 86을 다 볼 수 있게
된 순간 낡은 것이고, 방향은 **조이는 쪽**이다(안전이 깎이지 않는다).

레인 단독으로 정하지 않고 리드에게 넘겼으며, 리드가 근거 셋(방향이 엄격 · 낡은 그룹은
통과시키는 게 오히려 틀림 · 탈출로가 코드에 이름 지어져 있음)으로 수용 판정했다.

## 5. 증거 (Evidence)

### 5.1 고친 자리 — 한 곳

`collect_rig_sections` 의 섹션 루프. `paged_children(state_port, path, payload)` 로
끝까지 걷고, 얻은 완전성을 `rig_section` 에 실어 보낸다
(`dict(payload, truncated=truncated)`). **새로 짓지 않았다** — 공용 루프의 넷째 호출부다.

### 5.2 🔴 기존 검사로는 이 변경이 증명되지 않는다

구현만 넣고 전체 스위트를 돌렸더니 **10487 passed, 0 failed** — 아무것도 안 깨졌다.
이유는 기존 더블들이 `offset` 키워드를 받지 않기 때문이다:

    test_truncate_disclosure.py:123   def query_state(self, path: str) -> dict:
    test_truncate_disclosure.py:375   def query_state(self, path: str) -> dict:
    test_truncate_disclosure.py:473   def query_state(self, path: str) -> dict:   (_write_console)

공용 루프가 TypeError 를 잡아 첫 창만 쓰고 정직하게 강등하므로, 그 더블 위에서는
고치기 전과 뒤가 **같은 답**이 나온다. 초록은 안전의 증거가 아니라 **계기가 이 축을
못 본다**는 증거다. 그래서 `offset` 을 받는 더블이 선택이 아니라 필수였다.

### 5.3 새 검사 8개

**A. `test_state_paging_callsite.py` — `TestCollectRigSectionsWalksEverySection` (5)**

단언은 `truncated is False` 가 아니라 **모은 개수 == `childCount`**
(`len(entry["objects"]) == entry["total"]`, 이어서 `no` 가 1..86 연속인지).
픽스처는 실측 그대로 섹션마다 **다른** 창을 쓴다 — `fixtures` 19·18·18·18·13,
`groups` 한 창. 대조군 셋: 창 불균일성 자체 · 안 잘린 섹션 왕복 0 · 걷지 못하는 포트는
여전히 `truncated=True`.

**B. `test_truncate_disclosure.py` — `TestAFullyWalkedContainerRedirectsToReclassification` (3)**

거절 **사유 문자열**을 단언한다. 이 자리는 거절 갈래가 둘이고 **둘 다 거절**이라
`is_error is True` 만으로는 원리적으로 구별되지 않는다:

    "a non-empty list" 갈래                                    → 여기로 떨어지면 빨간다
    "reports 0 unseen … re-run classify_arrangement_topology"  → 이쪽이어야 맞다

왜 문자열까지 보는지를 클래스 독스트링에 박았다 — 다음 리팩터가 `is_error` 만 보도록
완화하기 쉬운 자리이기 때문이다. 대조군 둘: 걷지 못하는 `_write_console` 에서는
`[5]` 가 **여전히 통과**(옛 동작 보존) · 페이징 더블이 실제로 둘째 창을 요청했는지
(`offsets == [0, 4]`, 비공허).

### 5.4 뮤테이션 3/3

| 뮤테이션 | 되돌린 것 | 결과 |
|---|---|---|
| M1 | `paged_children` 제거, 첫 창만 | **4 failed** — 사유-문자열 검사 포함 |
| M2 | 첫 창만 + `truncated = False` | **5 failed** — 「걷지 못하면 여전히 절단」 대조군 포함 |
| M3 | 완전성 미전달 (`dict(payload, …)` → `payload`) | **1 failed** |

M1 에서 대조군 셋은 초록 유지 — 안전이 안 깎였다. M3 가 1개만 잡는 것은 분업이
정확하다는 뜻이다: M3 는 플래그만 틀리고 개수는 맞으므로 shortfall 이 여전히 0 이고,
안전장치 사유는 바뀌지 않는다.

**기존 AC-TRUNCATE-008 배터리 36개는 전 구간 초록**(mutation-required 앵커 보존 확인).

### 5.5 게이트

    uv run pytest -q                                   → 10495 passed, 12 skipped
    uv run ruff format --check server tools console    → 464 files already formatted
    uv run ruff check server tools packaging console   → All checks passed!

(첫 회차에 `test_overlap_preserve.py::test_ruff_format_reports_no_change` 1건이
빨갰다 — 내 추가분 서식. `ruff format` 으로 고쳤고 삭제 0, 기존 코드 무변경.)

## 6. 손대지 않은 것 — 4710 (조건부 승인을 반납했다)

리드가 「`import_lxseq_groups` 가 `fixtures` 를 조회하고 안 쓴다 → 이 카드에서
빼라, 단 (ㄱ) 하류 소비자 없음 (ㄴ) 요청 섹션 집합 단언 검사 없음, 둘 다 깨끗할 때만」
으로 조건부 승인했다. **둘 다 깨끗했지만 빼지 않았다.**

조건 밖에서 셋째 인자가 나왔기 때문이다:

    tools.py:1043  reason = REASON_UNRESOLVED if resolved else REASON_UNREACHABLE

`resolved` 는 **형제 섹션이 답했는지**를 센다. `fixtures` 를 빼면 그 호출은 `groups`
단독이 되고, `groups` 실패 시 사유가 `path_not_resolved` → `console_unreachable` 로
바뀐다. **낭비 제거가 아니라 오류 분류 변경이다.** 그리고 (ㄴ)이 깨끗한 것이 여기서는
안전이 아니라 **위험 신호**다 — 그 변화를 잡는 검사가 없으니 조용히 바뀐다.

함수 독스트링이 「ten sections vs two 로 표본 크기는 달라도 규칙은 같다」고 적어 뒀는데,
**2에서 1로 가는 것은 그 문장이 안 덮는다** — 둘일 때는 형제가 있고 하나일 때는 없다.

리드가 이 판단을 승인하고 **t152** 로 세웠다(자기 조건이 거꾸로였다는 기록 포함).
낭비는 사실로 남는다: 이 카드가 그 왕복을 **1회에서 5회로** 만든다.

## 7. 안 잰 것 (Gaps)

- **실기에서 이 수정이 여는 것을 못 봤다.** 절단되는 섹션은 `fixtures` 하나이고 그
  신호의 유일한 소비자는 7712 인데, 그것을 실기로 재현하려면 `topology_partial` 그룹을
  **쓰는** 것이라 콘솔 쓰기다 — 승인 밖. 실기 확인은 「절단이 실재한다」까지이고,
  「끝까지 걷는다 / 사유가 바뀐다」는 더블 위에서만 잰 것이다.
- **카드 문면의 「fx 의 나머지 절반인 시퀀스 판정이 여기 걸린다」는 지금은 거짓이다.**
  `sequences` 는 childCount 1 이라 절단이 없다. t150 의 All 풀과 같은 형태 —
  **잠재적**이지 현재 막혀 있는 것이 아니다. 그리고 이 0 은 **비어서 0**이지 못 읽어서
  0이 아니다(두 원인을 갈랐다). 다음 사람이 그 문장을 현재 상태로 읽지 않게 여기 적는다.
- **`drill_into` 는 손대지 않았다.** 그 안의 `child_payload.get("children", [])` 도
  한 창만 읽지만, 독스트링이 「`contents` 는 ONE responder window」라고 **명시**하고
  `contents_total` 로 총계를 따로 알린다 — 의도된 설계이지 이 카드의 결함이 아니다.
- `PAGE_CAP = 10` 이라 11창을 넘는 섹션은 여전히 `truncated` 로 남는다(설계된 정직한 미완).
- 실기 지문은 착수 시점 1회 측정이다. 이 쇼는 하루에도 바뀐다(리드 관측: `PresetPools/1`
  이 6→20→7).

## 8. 잔여 위험 (Residual-risk)

- 이 변경은 **8개 호출부에 동시에 걸린다.** 그 중 절단에 닿는 것은 실측상 `fixtures`
  를 요청하는 셋(2101·4710·7712)뿐이지만, 다른 쇼에서 다른 섹션이 커지면 새 자리가
  절단에 닿는다. 그때 열리는 것은 능력이고 바뀌는 것은 그 섹션 신호의 소비자다.
- 7712 의 동작 변경은 **`topology_partial` 그룹을 가진 사용자에게 보인다.** 인정 목록을
  내던 흐름이 재분류 요구로 바뀐다. 코드가 그 처방을 이름 짓고 있지만, 문서에는 없다.
- 더블의 창 크기는 실기 관측을 흉내 낸 것이지 실기 자체가 아니다. 실기 창 크기는 이름
  길이에 따라 변한다.

## 9. 트립와이어 갱신 — `_TOOLS_EXPECTED_HUNK_OLD_STARTS`

### 9.1 무엇이 발동했나

`server/tests/test_songcue_bundle.py:515`
`test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state` 가 CI 에서
빨갰다(#199 첫 회차, `1 failed, 10490 passed`). 결함이 아니라 **트립와이어 발동**이다 —
그 목록의 주석이 스스로 「It is a TRIPWIRE, not a constant」라고 적고, tools.py 를
정당하게 고치는 SPEC 은 **의도적으로** 갱신하라고 말한다. 진짜 불변식은 목록이 아니라
그 아래의 **보호 구간 비침범 단언**이고, 목록이 자라는 동안 그것이 계속 성립해야 한다.

### 9.2 판정 — 왜 이 헝크가 정당한 추가인가

    git diff --unified=0 38a6e7e2..HEAD -- server/orchestrator/tools.py

| 항목 | 값 |
|---|---|
| 헝크 수 | 73 → **74** |
| 새 시작점 | **410** 하나 |
| 사라진 시작점 | **없음** |
| 보호 구간 침범 | **ZERO** (기계 검산: 겹침 목록 `[]`) |

`410,3` 은 `collect_rig_sections` 섹션 루프의 `children` / `objects` / `entry`
**3줄 제자리 교체**다. BASE..HEAD 의 tools.py 삭제 줄은 그 3줄뿐이고, 나머지는 전부
근거 주석의 삽입이다 — **남의 코드를 다시 쓴 것이 아니라 이 루프 한 곳의 추가**다.

보호 구간과의 거리도 잰 값으로 남긴다:

    보호 234..238 :  앞 헝크 184,  뒤 헝크 302   → 사이에 헝크 없음
    보호 524..569 :  앞 헝크 479,  뒤 헝크 591   → 사이에 헝크 없음

CI 에러 문면의 `Left contains one more item: 1231` 은 **새 헝크가 아니다** — 410 이
index 18 에 삽입되면서 뒤가 한 칸씩 밀려 마지막 항목이 남아 보인 것이다. 기계로
집합 차를 재면 추가 `[410]`, 삭제 `[]` 다.

### 9.3 🔴 왜 로컬에서 안 걸렸나 — 순서를 어겼다

**별개 발견이 아니다. 내 절차 위반이다.**

이 트립와이어는 `_RUN_PHASE_BASE..HEAD` 를 본다 — **커밋된 HEAD**다. 작업트리 편집만
있는 동안에는 diff 에 안 잡히므로 **거짓 초록**이 나온다. PRESERVE 게이트와 같은 축이고,
이 저장소는 그것을 이미 알고 있었다(t142 에서 「커밋 → 스위트 → 보고」 순서로 갔다).

t151 에서 내가 돌린 마지막 전체 스위트는 `ruff format` 직후, **커밋 전**이었다
(`10495 passed`). 커밋(`6ad0207`) 뒤에 다시 돌리지 않았다. 그래서 로컬은 초록이었고
CI 가 처음 잡았다. 순서를 지켰는데도 안 걸린 것이 아니라, **순서를 안 지켰다.**

교정: 트립와이어 갱신 후 **커밋한 다음** 전체 스위트를 재실행해 확인했다.
같은 함정을 다음 사람이 밟지 않도록 갱신 주석에도 한 줄 박았다.
