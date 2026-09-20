# SPEC-LDACCENT-001 구현 계획

## §A. 컨텍스트

- **대상 파일**: `server/looks/songcue.py` (단일 파일 — 핵심 로직은 여기 하나에
  모여 있다). 보조로 손댈 시험 파일: `server/tests/test_songcue_ladder.py`,
  `server/tests/test_songcue_accent_ladder_t382.py`,
  `server/tests/test_songcue_chorus_rescue.py`(회귀 확인만, 변경 불필요할 수
  있음), `server/tests/test_songcue_accent_fixture.py`(회귀 확인),
  `server/tests/test_songcue_report.py`(회귀 확인),
  `server/tests/test_song_accent_ladder_t403.py`(회귀 확인).
- **⚠️ 착수 전 필수 동기화**: 이 SPEC 을 작성한 시점의 로컬 checkout(`HEAD
  469e41b2`)은 `origin/main`(`ca07b329`)보다 **12커밋 뒤져 있다**. t382 의
  D1/D2 정정(`fix(t382): 1회차엔 액센트를 안 붙이고, 액센트 표엔 명령이
  따라간다`, PR #468)이 이미 `origin/main` 에 있고, 이 SPEC 의 모든 함수
  인용(`_marking_accents`·`_climb_rungs`·`_ensure_marking_accent`·
  `_finalize_marking_accents`·`_reconcile_accent_fixture` 등)은 `origin/main`
  기준이다. run-phase 착수 전에 로컬 트리를 `origin/main` 과 동기화해야 한다
  (`git fetch origin main && git rev-list --count --left-right
  origin/main...HEAD` 로 확인 — `agent-common-protocol.md` § Pre-Spawn Sync
  Check 절차 그대로).
- **선행 완료 작업**: t382(PR #468, D1+D2 정정)가 이미 사다리(`ladder`)와
  실제 무대 명령(`accent_fixture`)의 **동기화**를 고쳤다 — 재배열 뒤에도
  둘이 같은 회차를 가리키게 한다. 이 SPEC 은 그 동기화된 상태 **위에서**,
  애초에 무영향 칸이 후보가 되지 않도록 한 단계 앞에서 거른다. t382 의
  `_reconcile_accent_fixture`(`songcue.py:1196`)·`_finalize_marking_accents`
  (`songcue.py:1255`)는 이 SPEC 이 바꾸는 함수들의 **호출자**다 — 시그니처를
  바꿀 때 이 두 호출자도 함께 갱신해야 한다.

## §B. 알려진 이슈

- **B1 — `_marking_accents` 의 직접 호출자는 네 곳**(plan-auditor D3 정정 —
  이전 초안은 다섯 곳이라 잘못 적었다): `_max_climb`(정의 `songcue.py:211`,
  호출 `songcue.py:218`), `_finalize_marking_accents`(정의
  `songcue.py:1255`, 호출 `songcue.py:1269`), `_climb_rungs`(정의
  `songcue.py:2333`, 호출 `songcue.py:2343`), `_ensure_marking_accent`(정의
  `songcue.py:2394`, 호출 `songcue.py:2433`). 시그니처에 룩+리그+라벨
  컨텍스트를 더하면 이 네 곳 전부 그 컨텍스트를 전달해야 한다 — 하나라도
  빠뜨리면 그 호출 경로에서만 필터가 안 걸리는 조용한 결함이 된다.
  **`_exhausted_rungs`(`songcue.py:200`)는 `_marking_accents` 를 부르지
  않는다** — 자신만의 상수 `LADDER_RUNGS` 를 그대로 돌려준다
  (`songcue.py:206-208`). 이전 초안이 이 함수를 다섯 호출자 중 하나로
  잘못 나열했다 — 이 함수는 오히려 M3 에서 **새로 배선해야 하는 호출부**다
  (§B2).
- **B2 — `_max_climb`/`_exhausted_rungs` 는 룩+리그+라벨을 모른다**: 오늘
  `allow_strobe: bool` 만 받는다. 유효 후보 수가 룩+리그+라벨마다 다르면
  "오를 수 있는 깊이의 상한"(`_max_climb`)과 "건너뜀 사유에 적을 칸 이름
  전량"(`_exhausted_rungs` — 오늘은 `_marking_accents` 를 거치지 않고
  `LADDER_RUNGS` 를 그대로 쓰므로, M3 에서 이 함수가 필터를 거친 유효
  집합을 대신 참조하도록 새로 연결해야 한다)도 그 수에 맞춰 달라져야
  정직하다 — 무영향 칸을 분모에 넣은 채 상한을 계산하면 실제로는 못 오를
  깊이까지 "시도해볼 가치가 있다"고 잘못 보고할 수 있다.
- **B3 — `_finalize_marking_accents` 의 강제 경로(`force=True`)**: 양보
  (`LADDER_DIMMER_YIELD`) 경로로 자리를 얻은 회차는 "마땅한 깊이" 개념이
  없어 무조건 액센트를 강제한다(`_ensure_marking_accent` 독스트링,
  `songcue.py:2394`). 이 경로도 필터를 통과해야 한다 — 강제한다고 무영향
  칸을 강제로 고르면 안 된다.
- **B4 — 1회차 걷어내기(`_strip_marking_accent_from_base_occurrence`,
  `songcue.py:1148`)는 건드리지 않는다**: 이 함수는 1회차가 재배열로
  물려받은 액센트를 지우기만 한다 — 필터링 로직과 무관하다. 회귀로만
  확인한다.
- **B5 — 매핑 리터럴 금지 규율**(plan-auditor D7 정정 — 이전 초안은 이
  규율을 과장했다): 이 모듈은 `{}` **매핑 리터럴**을 한 개도 두지 않는
  규율이 있다 — `dict()` **함수 호출**은 이미 쓰인다
  (`_ACCENT_FIXTURE_ROLE`, `songcue.py:275`). `test_songcue_sections.py`
  가 AST 로 재는 것도 `ast.Dict` 노드(`{}` 리터럴 구문)뿐이다
  (`test_songcue_sections.py:130`) — `dict(...)` 함수 호출은 이 가드를
  통과한다. 효과-판정 함수를 새로 쓸 때 `{}` 리터럴은 새로 추가하지
  않는다(튜플/조건문 또는 `dict()` 함수 호출 사용).

## §C. 사전 점검

```bash
# 1. 로컬 트리가 origin/main 과 동기화됐는지 확인 (착수 필수)
git fetch origin main
git rev-list --count --left-right origin/main...HEAD   # "0 N" 이어야 진행 가능

# 2. 대상 함수가 실제로 그 자리에 있는지 확인
grep -n "^def _marking_accents\|^def _climb_rungs\|^def _ensure_marking_accent\|^def _finalize_marking_accents" server/looks/songcue.py

# 3. 손댈 시험의 현재 통과 상태를 기준선으로 잡는다
uv run pytest -q server/tests/test_songcue_ladder.py server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_fixture.py server/tests/test_songcue_report.py server/tests/test_song_accent_ladder_t403.py

# 4. `{}` 매핑 리터럴 금지 가드(ast.Dict)가 오늘 통과하는지 확인 (새 코드가 어기지 않게)
uv run pytest -q server/tests/test_songcue_sections.py -k dict
```

## §D. 제약 (위반 금지)

- REQ-LDACCENT-008 / 감독 결정 2026-09-12 — 큐당 찍는 액센트 정확히 하나,
  밝기만 누적. 필터가 후보를 줄이거나 유보로 접어도 이 규율은 절대 깨지지
  않는다.
- `TestOneMarkingAccentPerCue`(`server/tests/test_songcue_ladder.py:470`)와
  `TestHeadroomCaseIsUntouched`(AC-3,
  `server/tests/test_songcue_accent_ladder_t382.py:236`)의 **의도**(하나뿐인
  액센트 불변식, 밝기 진행값의 바이트 동일성)는 그대로 지킨다. 두 시험의
  개별 `expected_ladders`/`.ladder` 단언값은 회전 후보 집합 자체가 바뀌는
  구체 픽스처에 한해 갱신해도 된다(spec.md §2 참고) — 그러나 `Dimmer` 값
  진행(`_dimmer_from_values_line`)과 `Zoom`/`Iris`/`ColorRGB_*` 등 다른 속성의
  명령 바이트는 이 SPEC 전후로 동일해야 한다(무영향 칸은 애초에 그 바이트를
  바꾼 적이 없었으므로).
- `server/looks/songcue.py` 밖의 파일(라이브러리 룩 YAML, `resolver.py`,
  `section_intent.py`)은 읽기만 하고 수정하지 않는다 — 이 SPEC 은 사다리
  회전 계층 하나만 고친다.
- `{}` 매핑 리터럴을 새로 추가하지 않는다(`dict()` 함수 호출은 허용, §B5).
- 콘솔로 명령을 실제로 보내는 코드 경로(`server/safety/`, `server/bridge/`)는
  건드리지 않는다 — 이 SPEC 은 순수 계산 계층이다.

## §E. 자기검증

- REQ-001~008 각각에 대해 판정 명령과 관측 출력을 PASS/FAIL 표로 제출한다
  (`verification-claim-integrity.md` §3 5-section 형식).
- `uv run pytest -q` 전체 스위트 통과 수를 착수 전 기준선과 나란히 제출한다
  (증분만 보고하지 않는다 — 기준선 자체를 `git show origin/main:` 기준으로
  다시 재는 것이 §A 동기화 이후 첫 판정이다).
- `ruff check server/looks/songcue.py server/tests/test_songcue_ladder.py
  server/tests/test_songcue_accent_ladder_t382.py` / `ruff format --check`
  둘 다 clean.

## §F. 마일스톤 (결정 되돌리기 쉬운 순서 — 데이터 모델을 먼저)

### M1 — 유보 기록의 데이터 모델 (가장 되돌리기 비싼 결정)

새 자료구조를 도입한다 — 이후 모든 마일스톤이 이 모양에 의존하므로 가장
먼저 확정한다.

- `SongCueWithheldAccent`(신규 frozen dataclass, `songcue.py` — 위치는
  `SongCueWithheldMovement`/`SongCueWithheldDarkness` 옆) — 필드: `section:
  SongCueSection`, `cue_number: int`, `reason: str`, `detail: str = ""`.
  `SongCueWithheldMovement`(`songcue.py:472`)와 같은 모양을 그대로 따른다.
- `SongCueSectionBundle` 에 `accent_withheld: SongCueWithheldAccent | None =
  None` 필드 추가(`darkness_withheld` 와 같은 자리 — 섹션 번들 하나가 조립
  도중에만 알 수 있는 값).
- `SongCueBundle` 에 `withheld_accents: tuple[SongCueWithheldAccent, ...] =
  ()` 필드 추가(`withheld_movement`/`withheld_darkness` 와 같은 자리,
  `songcue.py:487`).
- `build_songcue_bundle`(`songcue.py:752`)이 섹션 번들 전량에서
  `accent_withheld` 를 걷어 `withheld_accents` 로 집계한다 — 기존
  `withheld_movement`/`withheld_darkness` 집계와 같은 패턴.
- reason 상수 이름(예: `ACCENT_NO_EFFECTIVE_AXIS`/`ACCENT_NO_FIXTURE_GROUP`
  둘로 가를지, 통합 상수 하나로 할지)은 이 마일스톤에서 확정한다 — 최소
  요구는 "룩이 축을 안 실었다"와 "리그에 그룹이 없다"를 `detail` 또는
  `reason` 으로 구분 가능하게 하는 것(REQ-LDACCENT-005 는 "명시적이고 눈에
  보이는" 것만 요구하고 사유 세분화를 강제하지 않으므로, 구현 편의를 따른다).

### M2 — 효과-판정 술어 (새 타입 인터페이스)

무영향 여부를 묻는 순수 함수를 새로 만든다 — 부작용 없음, 입출력 계약이
새로 생기는 자리라 M1 다음으로 되돌리기 비싸다.

- 룩 축 판정: `zoom_pinch`/`iris_pinch` 가 겨냥하는 속성이
  `look.attributes` 에 있는지 확인하는 헬퍼(신규 또는 `_stepped` 가 이미
  하는 "속성 부재 시 그대로 반환" 판단을 앞에서 재사용). `_DIMMER`/`_ZOOM`/
  `_IRIS` 상수(`songcue.py:150-152`)를 그대로 쓴다 — 새 문자열 리터럴을
  짓지 않는다.
- 리그 그룹 판정: `blinder_or_flash`/`strobe_hit` 이 겨냥하는 역할이
  `resolution.groups_for(role)`(`_ACCENT_FIXTURE_ROLE` 경유,
  `songcue.py:275`)로 실제 그룹을 갖는지 확인.
- **라벨 판정(감독 결정 2026-09-20으로 범위 편입 — 이전 초안은 이 축을
  사람 확인 대기 마커로 남겨 뒀었다. 그 마커는 해소되어 이 절로
  대체됐다)**: `blinder_or_flash`/
  `strobe_hit` 이 리그 그룹 판정을 통과했더라도, 이 큐가 속한 섹션의
  라벨에 대해 `intent_for_label(section.label)`(`server/looks/section_intent.py:156`)
  가 `None` 이 아닌지 추가로 확인한다 — 새 판정 로직을 다시 짓지 않고
  기존 `intent_for_label` 을 그대로 호출한다. 리그 그룹 판정과 라벨
  판정은 **AND** 로 묶인다(REQ-LDACCENT-003) — 둘 중 하나라도 실패하면
  그 회차·그 큐에서 해당 칸은 무영향이다.
- 세 판정(룩 축·리그 그룹·라벨)을 합쳐 `_marking_accents(*, allow_strobe,
  look, resolution, section) -> tuple[str, ...]`(시그니처 확장안 — 이름·
  인자 순서는 구현 시 결정. `section` 은 라벨 판정에 쓰인다 —
  `section.label` 만 필요하면 `label: str` 로 좁혀도 된다)를 만든다.
  반환값은 "이 룩+이 리그+이 라벨에서 유효한" 후보만 담은, 기존 순서
  (줌→블라인더→아이리스[→스트로브]) 를 보존한 부분집합이다.
  `_unique_floor_climb` 소진 경로(D2, spec.md §4 Out of Scope)는 이
  술어가 보지 않는다 — `emitted` 누적 상태에 의존하는 판정이라 이
  단계(회전 후보 선택, `emitted` 확정 전)에서는 계산할 수 없다.

### M3 — 회전 호출부 배선 (네 직접 호출자 + `_exhausted_rungs` 신규 배선)

M2 의 확장된 `_marking_accents` 를 §B1 이 나열한 네 직접 호출자
(`_max_climb`·`_finalize_marking_accents`·`_climb_rungs`·
`_ensure_marking_accent`)에 전부 연결하고, `_exhausted_rungs` 는
새로 배선한다:

- `_climb_rungs(depth, *, allow_strobe, look, resolution, section)` —
  `_distinct_values_line`(`songcue.py:2275`, `_climb_rungs` 의 유일한
  호출자)이 이미 `look`·`section` 을 인자로 받으므로 그대로 전달할 수
  있다. 깊이가 가리키는 소박한 칸이 유효 집합 밖이면(REQ-004), 같은
  순서 안에서 다음 유효 후보로 넘어가는 탐색 로직을 추가한다. 유효
  집합이 비어 있으면 액센트 없이 밝기 히트만 돌려주고, 호출자가 유보
  사유를 판단하도록 신호를 남긴다(반환 타입 확장 또는 별도 헬퍼 — 구현
  시 결정).
- `_max_climb(*, allow_strobe, look, resolution, section)` — 유효 집합
  크기에 맞춰 상한을 다시 계산한다(§B2).
- `_exhausted_rungs(*, allow_strobe, look, resolution, section)` —
  오늘은 `_marking_accents` 를 거치지 않고 `LADDER_RUNGS` 상수를 그대로
  돌려준다(`songcue.py:206-208`). M2 의 필터를 거친 유효 집합을 대신
  참조하도록 새로 배선한다 — 건너뜀 사유 문면에 "실제로 그 자리에서
  후보였던 칸"만 남긴다(§B2, 무영향 칸을 후보였다고 잘못 보고하지
  않는다).
- `_ensure_marking_accent`/`_finalize_marking_accents` — `force=True`
  (양보 경로, §B3)와 `force=False`(직접 사다리 경로) 양쪽에서 M2 의 필터를
  거친 후보만 쓴다.

### M4 — 유보 기록 실제 기입

M1 의 데이터 모델에 M3 이 만든 "유효 후보 없음" 신호를 연결한다 —
`_section_bundle`/`_ensure_marking_accent`/`_finalize_marking_accents` 가
빈 칸으로 조용히 넘어가는 대신 `SongCueWithheldAccent` 를 만들어
`accent_withheld` 에 싣는다. `SongCueWithheldDarkness` 가 조립 도중에만
알 수 있는 값을 `darkness_withheld` 에 두는 것과 같은 배선.

### M5 — 시험 픽스처 정합 (기계적 갱신)

- `TestHeadroomCaseIsUntouched`(AC-3,
  `server/tests/test_songcue_accent_ladder_t382.py:236`) — 단일 축 룩 +
  FULL_RIG(블라인더 없음) 조합에서 `zoom_pinch`/`iris_pinch`/
  `blinder_or_flash` 셋 다 무영향이므로, 필터 적용 후 `expected_ladders`
  에 이 셋이 더는 등장하지 않아야 한다(모든 회차가 `dimmer_hit`/
  `dimmer_yield` 조합만 갖거나, 유보 기록이 새로 생긴다). `Dimmer` 값
  진행(20/25/30/35/40/45/50)은 그대로 단언한다.
- `test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking`
  (`server/tests/test_songcue_ladder.py:517`) — `_bundle_of` 가 FULL_RIG
  를 쓰므로(블라인더 없음) 이 시험의 룩(줌·아이리스 둘 다 실제 축)에서
  `blinder_or_flash` 는 항상 무영향이다. 필터 적용 후 4회차(깊이 3)의
  `.ladder` 는 더 이상 `blinder_or_flash` 를 담지 않고, 남은 유효 후보
  (아이리스, 또는 회전이 재순환한 줌)로 바뀐다 — 정확한 새 기대값은 M3
  구현 뒤 실제 실행 결과로 확정한다(사전에 손으로 계산해 두지 않는다).
- 신규 대조군 — 블라인더 그룹이 **있는** 리그(`_RIG_WITH_BLINDER` 패턴,
  `test_songcue_accent_ladder_t382.py:49`)에서는 필터가 과도하게 거르지
  않고 `blinder_or_flash` 가 여전히 회전에 오르며 무대 명령까지 실제로
  나가는지 확인하는 양성 대조군을 추가한다(spec.md AC-LDACCENT-003).
- 신규 대조군 — 블라인더 그룹이 **있는** 리그 + `intent_for_label` 이
  `None` 을 돌려주는 섹션 라벨(§6 표에 없는 라벨) 조합에서는, 그룹은
  있어도 라벨 조건을 못 만족해 `blinder_or_flash` 가 여전히 후보에서
  제외되는지 확인하는 음성 대조군을 추가한다(spec.md AC-LDACCENT-006 —
  D1 정정으로 범위에 들어온 세 번째 필터링 축).
- `test_songcue_chorus_rescue.py`/`test_songcue_accent_fixture.py`/
  `test_songcue_report.py`/`test_song_accent_ladder_t403.py` 는 회귀
  확인만 — 실행해서 여전히 통과하는지 본다. 픽스처가 이미 유효 축/그룹을
  가진 룩+리그를 쓰면(예: 실기 EDM 라이브러리 + 실기 LXSEQ 리그) 값이 안
  바뀔 가능성이 높다.

### M6 — 전량 회귀 + lint

- `uv run pytest -q` 전체 스위트. `ruff check`/`ruff format --check` 대상
  파일 전량.
- `@MX:ANCHOR`/`@MX:REASON` 주석을 M2/M3 이 바꾼 함수에 이 저장소 관행대로
  추가한다(예: `_climb_rungs` 가 새로 얻는 "무영향 칸 건너뛰기" 분기).
