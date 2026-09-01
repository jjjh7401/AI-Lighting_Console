# t236 — BM 성분 술어: 빌더 앞까지

베이스: `origin/main bda78b6` (착수 시점에 재서 확인) · 브랜치: `WT-beam-components`
워크트리: `.claude/worktrees/t236` · **콘솔 접촉 0 · 실기 0** (순수 코드 카드)
선행 설계: `.moai/reports/t229-bm/verdict.md` (main `9ba5bbf`) 8절

## 1. 판정 세 줄

1. **`_bm_components()` 를 넣었고, 판정기가 그것을 실제로 부른다.** 치환으로 쟀다 —
   술어를 눈멀게 하면 `Zoom 45°` 가 storable 에서 보류로 바뀐다. 사본이면 안 움직인다.
2. **성분 유실 검사가 7개 뮤테이션 중 7개를 잡는다.** 마지막 성분 버리기 · all-or-nothing
   제거 · 조각 무시 · 값 속 속성 무시 · 배선 제거 · 어휘 재결합 · 빈 값 허용.
3. **열리는 행 수는 0 → 0.** 그리고 **한 건은 오히려 닫혔다** — 아래 3절.

## 2. 무엇을 넣었나

`server/lxseq/preset_parser.py` (+110, 삭제 0):

- `_bm_segment_component(segment)` — **원자**. 조각 하나 -> `(속성, 원문값)`.
- `_bm_components(value_raw)` — `_col_components` 의 형제. **all-or-nothing**.
- `_bm_unreadable_segments(value_raw)` — 못 읽은 조각을 **보고**한다.
- `classify_storability` 의 bm 갈래에 배선 한 줄.

빌더는 **안 만들었다.** 설계 8.2 가 「Zoom 단위 확정 전에는 원문값만 나른다」로
못박았고, 그 단위는 이 채널로 원리적으로 못 잰다(t235). 리드 배차도 같다.
`LXSEQ_PRESET_APPLY_ATTRIBUTE` 에 bm 칸을 **넣지 않았고**, 안 넣었다는 것을 검사가 잰다.

### 정본 시트 5행이 실제로 읽히는 모양

| 행 | 값 | 성분 | 보류 사유 |
|---|---|---|---|
| BM.01 | `Zoom 45° · Gobo OPEN · Prism OFF` | 3 | probe_rejected + family_out_of_scope |
| BM.02 | `Zoom 20° · Gobo OPEN` | 2 | family_out_of_scope |
| BM.03 | `Zoom 8° · Prism 3-facet ON` | 2 | probe_rejected |
| BM.04 | `Frost 30%` | 1 | probe_rejected |
| BM.05 | `Gobo 슬롯2(브레이크업) · Zoom 25° · 예비` | **None** | family_out_of_scope + **value_not_machine_readable** |

읽히는 행 4개, 성분 합 8개. storable 은 5행 중 **0**.

## 3. 🔴 재서 알게 된 것 — 「Gobo 만 풀면 2건」은 틀렸다

기존 검사 `test_solving_one_class_would_not_open_every_beam_row` 는 「Gobo 만 풀면
5건 중 **2건**이 열린다」를 단언하고 있었다. 그 2번째가 BM.05 인데, 그 행의 `예비`
조각은 `_attribute_tokens` 가 한글 토큰을 아예 안 보기 때문에 **조용히 무시**되고
있었다. 즉 그 행은 시트가 적은 것의 일부를 버린 채 열릴 행이었다.

지금은 `예비` 가 보고되므로 BM.05 는 사유 둘을 지고, **Gobo 만 풀면 1건**이다.
숫자가 줄어든 것이 아니라 **과대 계상이 정정된 것**이다.

정본 시트 규약(`src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md`)이 주석 토큰을
규정하는지 **읽어서 확인했다 — 규정하지 않는다**(그 문서에 `예비` 0건). 설계 7절이
열어 둔 질문이 이것으로 닫힌다. 규약이 생기면 그때는 보고가 아니라 알고 무시하는
것이 맞고, 그 전환은 검사가 먼저 빨개지게 해 뒀다.

## 4. 🔴 한 번 회귀를 냈고 스위트가 잡았다

`_bm_segment_component` 를 처음에는 첫 낱말을 **아는 이름 목록에 대보는** 형태로
썼다. 그러자 t135 의 트립와이어가 깨졌다 — 그 검사는 목록을 `Prism1` 로 치환하면
BM.03 이 **열린다**는 것을 실제로 쏴서 보여주는데(그것이 그 치환이 회귀라는 증명),
구조 축이 어휘를 물으면 `Prism` 이 목록에서 빠지는 순간 조각도 못 읽게 되어 그 행이
**다른 사유로** 막힌다. 증명이 조용히 사라진다.

고친 방향: **구조 축은 어휘를 묻지 않는다.** 첫 낱말을 원문 그대로 속성 이름으로
나르고, 「그 속성을 쏠 수 있는가」는 기존 어휘 축이 답한다. 두 축이 한 몸이 되지
않는 것을 치환 검사로 고정했다(뮤테이션 M6).

## 5. 검증

명령: `uv run pytest server/tests -q` (워크트리 `.claude/worktrees/t236`, HEAD `bda78b6` + 작업 트리)

    10889 passed, 12 skipped, 1 warning in 147.27s

`uv run ruff check server/` -> `All checks passed!` · `ruff format --check` 통과.

### 뮤테이션 7/7 (판별력)

| # | 뮤테이션 | 결과 |
|---|---|---|
| M1 | 마지막 성분을 버린다 | RED (10 failed) |
| M2 | all-or-nothing 제거 — 읽은 것만 돌려준다 | RED (8) |
| M3 | 못 읽은 조각을 조용히 무시한다 | RED (3) |
| M4 | 값 자리의 다른 속성 이름을 안 본다 | RED (1) |
| M5 | 판정기가 이 술어를 안 부른다 | RED (3) |
| M6 | 구조 축을 어휘 목록에 다시 붙인다 | RED (5) |
| M7 | 값이 비어도 성분으로 친다 | RED (1) |

M7 은 **처음에 GREEN 이었다** — 살아남은 뮤테이션을 보고 검사를 추가했다
(`Zoom` 단독처럼 값 없는 조각). 뮤테이션을 돌리지 않았으면 그 구멍은 안 보였다.

### 갱신한 기존 검사 4건 — 무엇을 가렸나

동작 변경은 **하나**다: BM.05 가 사유를 하나 더 진다. 그 하나가 인구조사 검사 4개를
건드렸다(개수가 4라고 해서 동작 변경이 4가 아니다).

- `test_reasons_carry_a_machine_countable_class` — `value_not_machine_readable` 1 추가
- `test_the_class_sum_exceeds_the_row_count_by_the_multi_blocked_rows` — 다중 차단 행 `["BM.01"]` -> `["BM.01", "BM.05"]`
- `test_every_class_is_from_the_closed_set` — 클래스 종 2 -> 3
- `test_solving_one_class_would_not_open_every_beam_row` — 2 -> 1 (3절)

문서도 같이 고쳤다: `preset-unify-design.md` 빔 행의 클래스 집계(합 6 > 행 5 ->
합 7 > 행 5). `spec.md` A.4-2 표는 **안 건드렸다** — 그 절이 「t76 시점 실측 그대로
둔다」고 스스로 못박고 있다.

## 6. 안 잰 것 (Gaps)

- **콘솔에 아무것도 안 쐈다.** 이 카드는 쓰기 0이다. `Attribute 'Zoom' At 45` 가
  어떻게 해석되는지는 여전히 미측정이고, 이 채널로는 **측정 불가**다(t235).
- **빌더가 성분을 안 버리는지는 못 쟀다** — 빌더가 없다. 이 회차가 잰 것은 그 앞
  단계, **술어 자신이 안 버리는가**이다. 빌더가 생기는 날 같은 형태의 검사를 그쪽에도
  세워야 하고, 그것을 `TestTheBuilderIsDeliberatelyAbsent` 가 빨개지며 알린다.
- **`3-facet ON` · `슬롯2` 를 어떤 값 문면으로 옮길지 안 정했다.** 원문을 나르기만
  한다. 지금 정하면 미측정 문법을 코드에 박는 것이다.
- **`_bm_components` 의 프로덕션 소비자는 아직 판정기 하나뿐이다.** 「판정기와 판독기가
  같은 술어를 부른다」의 판독기 쪽은 빌더가 생겨야 실체가 된다.
- **bm 시트가 Beam 풀인데 Zoom 은 Focus 풀**이라는 축(t234)은 이 카드가 안 건드렸다.
  그 축이 안 풀리면 어휘를 열어도 4행이 엉뚱한 풀로 간다.

## 7. 잔여 위험

- **구조 축과 어휘 축이 다시 붙을 수 있다.** 4절의 회귀는 「정합성 개선」처럼 보이는
  모양으로 온다. M6 뮤테이션과 치환 검사가 그 자리를 지키지만, 검사를 같이 고치면
  뚫린다.
- **첫 낱말을 원문 그대로 나르므로 모르는 이름도 성분이 된다** (`Zorble 5` ->
  `("Zorble", "5")`). 그 이름을 쏠 수 있는지는 어휘 축이 답해야 하는데, 지금 어휘 축은
  **모르는 이름에 아무 사유도 안 붙인다** — `Zorble 5` 는 storable 이다. 이것은 이
  카드가 만든 것이 아니라 **원래 그랬고**, 빌더가 생기는 날 정면으로 걸린다. 빌더를
  만드는 회차가 「아는 이름만 쏜다」를 어디서 지킬지 정해야 한다.
- **`_LEADING_WORD` 는 ASCII 낱말만 본다.** 한글로 시작하는 조각은 전부 「못 읽음」이다.
  지금은 그것이 맞지만(시트 속성 이름이 전부 영문), 시트가 한글 속성명을 쓰기 시작하면
  이 술어가 통째로 눈먼다.
