# t599 run 판정 — 「＋ 새 프리셋 만들기」 창의 위치 종류: 목표 좌표 입력 (SPEC-LDBEAT-001 REQ-015 (i-3)·(h))

- 카드: t599 · lane-1 · 브랜치 `WT-pos-preset-dialog` · 기준 origin/main `eb936648`. 그 뒤 main `f8d7a8a9`(t597)를 합쳤다(충돌 0).
- 콘솔 쓰기 0: 가짜 콘솔 쓰기 기록 `console_executed_8873.log`가 전·후 캡처 모두 0줄이다. 이 창이 콘솔에 닿는 것은 빈 번호를 확인하는 **읽기** 한 번뿐이다(`read_named_pool`, Position 풀).
- 장비 구성(리그)에 맞춘 고정값 0. 번호대·풀 번호를 코드에 박지 않았다.

## 무엇이 바뀌었나

- 위치 칸에서 「＋ 새 프리셋 만들기…」를 고르면, 창 **안에** 칸 셋이 더 생긴다: `X (m)` · `Y (m, + = 무대 뒤)` · `Z (m, + = 위)`. 기존 영문 이름·설명 칸은 그대로다. 위치 칸 옆에 따로 입력칸을 두지 않았다. 다른 네 종류의 창은 예전과 같다.
- 서버(`ChatSession._beat_grid_new_position_preset`)는 번호를 고른 뒤 일반 편집 길(`apply_beat_grid_edit`)로 칸에 씌운다. 그다음 세 곳에 남긴다.
  - `preset_labels`: 영문 이름
  - `preset_descriptions`: 설명
  - `preset_targets`: 목표 좌표 (t592 `record_position_preset_target`)

  반영 때 t592 레시피(`plan_position_preset_creation`)가 이 셋을 읽어 콘솔에 프리셋을 만든다.
- 프로토콜(`messages.py`): `aim{x,y,z}`는 위치일 때 **필수**다. 세 값 모두 유한한 수여야 하고, bool은 받지 않는다. 다른 종류에 `aim`이 오면 거절한다.
- 디머 프리셋·기본 색은 예전처럼 거절한다.

## 번호 규칙 (리드 승인 2026-10-11)

`first_free_base_position_number`(`server/design/beat_grid_presets.py`)가 번호를 고르는 순서:

1. 콘솔 Position 풀을 읽는다. 못 읽으면 **거절**한다. 기본 풀은 번호대 보호가 없어서, 격자만 보고 고르면 쇼 프리셋을 덮어쓸 수 있기 때문이다.
2. `preset_pools.yaml`에 선언된 번호대 중 **읽은 풀 번호와 같은 것**은 건너뛴다. 지금은 2.61~2.68이다.
3. 그 밖에서 콘솔에 있는 가장 큰 슬롯 다음부터 위로 훑어, 콘솔에도 격자 참조에도 없는 첫 슬롯을 고른다. 기본 위치가 하나도 없으면 1부터 시작한다.
4. 번호 앞자리(풀 번호)는 콘솔에서 읽은 값을 쓴다. `2`라는 숫자를 코드에 박지 않았다.

## 좌표계 출처 (리드 지시 — `pointing.py`가 정본)

`server/spatial/pointing.py:3`(metres), `:14`(`Pan 0 / Tilt 0` = stage −Z 곧장 아래 → +Z가 위), `:15`(Tilt를 + 쪽으로 기울이면 stage +Y = upstage). 창 이름표 `ui/src/components/BeatGrid.tsx:1007` 일대가 이 정의에서 나왔다. pointing.py에는 X의 좌·우 이름이 없어서, 이름표도 `X (m)`만 적었다(지어내지 않음).

## 증거

- RED(구현 에이전트 보고, 구현을 되돌린 상태에서 시험을 먼저 씀):
  - 서버: `ImportError: cannot import name 'first_free_base_position_number'`
  - 화면: protocol 시험 `"aim"` 누락, BeatGrid 시험 3개 실패(`aria-label="X (m)"` 없음, 좌표가 비거나 틀려도 만들기가 켜짐)
- 합친 트리(`c4ca8afd`)에서 이 레인이 다시 돌림:
  - `uv run pytest -q -p no:cacheprovider server` → `15462 passed, 33 skipped, 1 warning in 269.61s`
  - `uv run ruff check server .moai/reports/t599` → `All checks passed!` · `ruff format --check` → `815 files already formatted`
  - `ui/`: `npx vitest run` → `Tests 1223 passed (1223)` · `npm run build` → `✓ built`
- 뮤테이션: 번호대를 건너뛰는 줄을 `base_occupied = list(children)`로 바꾸니 → `2 failed, 31 passed`(`test_capture_harness_fake_pool_example`, `test_band_slots_are_skipped_even_when_occupied`). 되돌린 뒤 `grep -c MUTATION` → `0`.
- 전후 캡처(`capture.py`·`serve_fake.py`, 1450×1000, 가짜 콘솔). 가짜 위치 풀은 `{41: 'LA Center', 61: 이름 없음}`이다. 시험값이지 실기 값이 아니다.
  - `before/`(main `eb936648` 빌드): 창 안 좌표 칸 0개. 만들기를 누르면 「'위치 프리셋'은(는) 효과 풀 번호대가 없는 기본 풀입니다 …」로 거절된다. 드롭다운은 빈 값.
  - `after/`(`c4ca8afd`): 좌표 칸 3개. X 0 · Y −2 · Z 0, 이름 `LA Center Front`로 만들면 「새 위치 프리셋 **2.42** 'LA Center Front' → 목표 (0, -2, 0) m 배정 — 승인 대기」가 뜨고 드롭다운도 `2.42`다.
    - 41 다음이고, 61(이름 없는 점유 슬롯)은 번호대 안이라 기준에서 빠졌다. 규칙대로다.
    - t595 표식도 「빈 위치 프리셋 — 반영 때 목표 좌표로 만듦」으로 바뀌었다.

## 이 레인이 고친 것

| # | 내용 | 고침 |
|---|---|---|
| 1 | 구현 커밋이 에이전트 자기 작업 공간 브랜치(`worktree-agent-…`)에 들어감 | 이 브랜치로 ff-merge(`e4fefc4d`) |
| 2 | 배정 답이 「승인 때 콘솔에 만듦」이라고 단정함. 그룹 소속·장비 좌표를 못 읽으면 t592가 보류하므로 거짓이 될 수 있다 | 「못 만들면 승인 카드에 보류 사유가 나옴」으로 고침(`43be717f`) |

## 안 잰 것

- **반영 왕복**: 이 창으로 만든 번호가 「⇪ 반영」에서 실제로 조준 줄 → `Store`/`Label Preset`으로 나가는 모습은 브라우저로 재지 않았다. 캡처 하네스의 그룹 소속이 `complete: False`라 t592가 보류할 것이다. t592 시험이 저장 모양(`preset_targets`·`preset_labels`)을 이미 잠그고, 이 카드는 같은 함수로 같은 자리에 쓴다.
- **실기 콘솔**: 0회. 실제 쇼 파일의 기본 위치 풀 모양(가장 큰 번호 다음 칸이 정말 비어 있어도 되는 자리인지)은 모른다. `preset_pools.yaml`도 아직 `confirmed: false`다.
- **좌표 범위**: 무대 밖 좌표나 장비 바로 위 좌표도 받는다. 조준할 수 없는지는 반영 때 t592가 「목표를 조준할 수 없는 장비가 있음」으로 가른다. 입력 단계에서는 막지 않는다.
- **창 안 클릭 흐름**: jsdom이 없어서 순수 부품(`renderToStaticMarkup`) 시험과 위 캡처 한 번으로만 봤다.
