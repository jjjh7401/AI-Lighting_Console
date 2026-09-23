# t439 — 후렴 회차 색, 두 조립 경로 대조

명령: `uv run pytest server/tests/test_chorus_color_two_paths_t439.py::TestBothPathsSatisfyChorusColorIdentityInTheirOwnRepresentation::test_write_the_cross_path_report -q`

두 경로는 같은 입력을 받을 수 없다(Path A: 역할+D레벨+이름 팔레트, Path B: 구간 라벨+다이내믹스 → 버스킹 룩 라이브러리의 RGB). 그래서 이 표는 값을 직접 비교하지 않는다 — 각 경로가 **자기 색 표현 안에서** REQ-LDDESIGN-004/030(후렴 반복 전체가 동일한 색을 유지한다)을 지키는지만 본다.

## Path A — server/web/session.py (`_build_unified_song_plan`)

| 구간 | palette (primary, accent) |
|---|---|
| Chorus 1 | ('블루', 'warm white') |
| Chorus 2 | ('블루', 'warm white') |
| Chorus 3 | ('블루', 'warm white') |
| Chorus 4 | ('블루', 'warm white') |
| Chorus 5 | ('블루', 'warm white') |
| Chorus 6 | ('블루', 'warm white') |
| Final Chorus | ('블루', 'warm white') |

항등 확인 — Final Chorus 제외 6회 전부 팔레트 1종: PASS

## Path B — server/looks/songcue.py (`build_songcue_bundle`, genre=edm)

| 구간 | look_id | ColorRGB |
|---|---|---|
| Chorus 1 | edm-drop-crimson | ColorRGB_R=100, ColorRGB_G=0, ColorRGB_B=15 |
| Chorus 2 | edm-drop-crimson | ColorRGB_R=100, ColorRGB_G=0, ColorRGB_B=15 |
| Chorus 3 | edm-drop-crimson | ColorRGB_R=100, ColorRGB_G=0, ColorRGB_B=15 |
| Chorus 4 | edm-drop-crimson | ColorRGB_R=100, ColorRGB_G=0, ColorRGB_B=15 |
| Chorus 5 | edm-drop-crimson | ColorRGB_R=100, ColorRGB_G=0, ColorRGB_B=15 |
| Chorus 6 | edm-drop-crimson | ColorRGB_R=100, ColorRGB_G=0, ColorRGB_B=15 |

항등 확인 — 6회 전부 같은 look_id/ColorRGB: PASS

## 두 경로가 다른 지점 (실측)

- Path A 는 이 SPEC(M1, REQ-005~010)의 9종 닫힌 구간 어휘를 쓴다 (`intro`/`chorus`/`finale` 등 role 필드) — Final Chorus 가 chorus 와는 별도인 `finale` role 이라 REQ-030 의 클라이맥스 예외를 구조적으로 표현할 자리가 있다.
- Path B(`server/looks/songcue.py`)는 아직 옛 §6 5종 어휘(Intro/Build/Chorus/Drop/Breakdown 계열)를 쓴다 — `Final Chorus` 라는 별도 어휘가 없어 이 카드에서는 마지막 반복도 그냥 `Chorus`로 돌렸다. 두 경로가 완전히 같은 입력을 받을 수 없다는 것 자체가 REQ-LDDESIGN-003(두 경로가 단일 컴포저로 수렴해야 한다, M6/AC-017)의 잔여 격차이고, 이 카드(REQ-004) 가 아니라 그 REQ 의 범위다.
- Path A 의 색은 감독이 고른 이름(팔레트 문자열)이고 Path B 의 색은 버스킹 룩 라이브러리에 미리 박힌 RGB 값이다 — 같은 곡이라도 두 경로의 색 문자열/값이 우연히조차 일치할 이유가 없다(서로 다른 어휘 공간).
