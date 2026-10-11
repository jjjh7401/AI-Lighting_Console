# t594 run 판정 — 새 프리셋 만들기 A-3 색 (SPEC-LDBEAT-001 REQ-LDBEAT-015(i-5))

판정: **PASS (콘솔 쓰기 0, 실기 미확인 항목은 t602 로 넘김)**
브랜치 `WT-color-preset` · 기준 origin/main `aa3b6f29` → 검증 시점 HEAD `03ba07a1`(main `9ab69fe5`, t601 포함 병합)

## 주장
1. 「＋ 새 프리셋」 창에서 색 종류를 고르면 R·G·B 칸(0~100%, 콘솔 ColorRGB 와 시안 `P[...].rgb` 와 같은 단위)과 미리보기가 나온다. 세 값이 다 맞아야 「만들기」가 켜진다.
2. 서버는 색을 더 이상 「번호대 없음」으로 거절하지 않는다. t599 위치와 같은 길로, 콘솔 Color 풀을 읽고 base 영역의 첫 빈 슬롯을 고른다. 이때 색 효과 번호대 4.41~4.99 는 건너뛴다. 풀을 못 읽으면 거절한다. RGB 는 곡 격자 `preset_colors["4.n"]` 에 남는다.
3. 반영 묶음은 `ClearAll` → `Group g ; Attribute 'ColorRGB_R' At r ; …G ; …B` → `Store Preset 4.n` → `Label Preset 4.n '이름'` → `ClearAll` 순서로 큐 줄보다 앞에 놓인다.
4. 칸 판정은 공용 `plan_cells` 에 `("color_preset_no", 번호)` 로 들어간다. 덮어쓰기 0, 그룹 미확인 보류, 여러 그룹 보류 규칙은 위치·효과와 같다. 빈 프리셋 표식은 `create_on_apply`(t595) 를, 송신 직전 재판독은 색 풀(t598) 을 덮는다.
5. 장비 컬러 판독(`_fixture_color_channel_names`, 콘솔 읽기)에서 그룹 소속 장비 전부의 채널을 다 읽어야 하고, 모두 ColorRGB_R/G/B 를 가져야 만든다. 하나라도 판독되지 않으면 「채널 미판독」 보류, 속성이 없으면(CMY 만 있는 리그 등) 「속성 없음」 보류다. 둘 다 보류 사유에 FID 를 적는다.

## 증거 (이 트리 `03ba07a1`, 2026-10-12)
- `uv run pytest -q -o addopts="" server/tests/test_new_color_preset_t594.py …t589 …t592 …t593 …t595 …t598 …t599 …t600 …t601 …t603 test_tools.py test_overlap_preserve.py test_songcue_bundle.py` → `439 passed in 5.69s`
- `ruff check` (변경 py 7개) → `All checks passed!` · `ruff format --check` (9개) → `9 files already formatted`
- `npm --prefix ui exec -- tsc --noEmit -p ui/tsconfig.json` → exit 0
- `npm --prefix ui test -- src/components/BeatGridNewColorPreset.test.tsx src/components/BeatGridNewFxPreset.test.tsx src/components/BeatGrid` → `23 files, 479 passed`
- 뮤테이션: `_build_bundle` 에서 선택과 값을 두 줄로 쪼개면 → `4 failed, 71 passed`(묶음 모양 2, 반영 묶음 1, 중복 제거 생존 1). 되돌린 뒤 `git status` 깨끗함.

## 결정과 이유
- **선택+값 한 줄**: 이 꼴은 `server/fx/instantiate.py` `_SELECTED_VALUE_LINE` 과 일치해서 송신 중복 제거가 면제하는 줄이다. 같은 그룹, 같은 RGB 의 색 둘이 한 묶음에 있어도 줄이 빠지지 않는다. t601(#641) 머지 뒤에는 묶음 안의 반복이 원래 보내지지만, 그와 상관없이 성립한다.
- **속성 이름**: 콘솔에서 읽은 채널 이름으로 판정하고, 보내는 줄에는 `ColorRGB_R/G/B` 를 적는다. 판정을 통과하는 조건이 「읽은 이름(모듈 접두를 뗀 것)에 정확히 이 셋이 있다」이므로, 보내는 이름은 판독된 이름과 같다. 다른 이름 체계의 리그는 지어내지 않고 보류한다.
- 구현 중 결함 1건을 잡아 고쳤다. 처음에는 위치 전용 `referencing_tracks`(필드 `position_preset_no`) 를 색에 재사용해서 그룹 조회가 비어 버렸다. 지금은 색 모듈이 자기 필드로 공개한다(`color_referencing_tracks`).

## 안 잰 것
- 실기 콘솔 0회. 다음 셋은 t602 실기 묶음에 넣어 달라고 요청한다(아래).
- `ColorRGB_W` 는 건드리지 않는다. W 가 있는 장비에서는 프리셋에 W 값이 없으므로, 불러올 때 W 는 이전 상태를 따라간다(t430 은 W At 0 을 적는 선례).
- 전체 시험 묶음은 돌리지 않았다(레인 규약). CI 가 전체를 돈다.
- 디머 base 풀(`dimmer_preset`)은 그대로 거절한다(REQ-015(i-6)).

## t602 실기 요청 항목 (⑩)
⑩ 새 색 프리셋 만들기 줄(`ClearAll` → `Group g ; Attribute 'ColorRGB_R' At r ; …` → `Store Preset 4.n` → `Label` → `ClearAll`)을 박자 격자 반영 묶음 앞에 섞어 보낼 때, 4.n 이 RGB 값으로 저장되고 큐가 그 번호를 참조하는지 되읽기로 확인한다. 그룹 안에 ColorRGB 가 없는 장비가 섞인 경우는 지금 보류되므로 실기 대상이 아니다.

## 잔여 위험
- Color 풀 이름 해석(`read_named_pool(..., "Color")`) 은 드로워와 같은 판독을 쓴다. 쇼 파일에서 풀 이름이 다르면 거절된다(fail-closed).
- 판독 비용: 색 후보가 있는 반영에서만 장비당 속성 2회 + (종류·모드) 조합별 채널 페이지를 읽는다.
