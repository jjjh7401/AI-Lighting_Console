# t315 — 리그 기하가 크기를 들고 Q4 가 그것을 읽는다

- 카드: t315
- 브랜치: `WT-rig-span`
- 기준: `origin/main` @ `f85c0c3`
- 구현 커밋: `05e65e0`
- 측정 환경: 이 워크트리의 자체 인터프리터
  (`.claude/worktrees/agent-a4034196d12cd93f6/.venv/bin/python3`, Python 3.11,
  `uv run` 경로). 시스템 python 아님.
- 실기 데스크: **접촉 0건** (오프라인). 콘솔에 쓴 것 없음.

## 1. 무엇이 문제였나

`server/design/rig.py` `_build_geometry` 는 축별 span 을 계산한 뒤 지배축만
남기고 크기를 버렸다. 그래서 `RigGeometry` 는 네 값(`arrangement`,
`arrangement_low_confidence`, `centroid`, `dominant_axis`)만 들고 있었고,
소비자인 `interview._q4_candidates` 는 Q4(공간 스토리) 제안 순서를 **배치
라벨 하나**로만 정했다.

그 라벨은 **구조**를 답하고 크기를 답하지 않는다. `grid` 는 「깊이·좌우 양쪽이
또렷하게 묶였다」는 뜻이어서, 폭 10m·깊이 1m 리그와 폭 1m·깊이 10m 리그가
같은 라벨을 받는다. `_GEOMETRY_PREFERRED_PROGRESSION` 이 `grid` 에 붙여 둔
기본값은 `ascending`(「좁음→넓음」)인데, 그 서사의 근거는 같은 파일 주석에
적혀 있듯 「무대 폭이 열리는」 것이다 — 폭 1m 리그에는 열 폭이 없다.

## 2. 착수 전 전제 재검증

배차서의 전제가 낡았을 수 있어 `f85c0c3` 에서 두 쪽을 다시 확인했다.

| 전제 | 확인 명령 | 결과 |
|---|---|---|
| span 이 아직 버려진다 | `grep -n "spans\|dominant_axis" server/design/rig.py` | `rig.py:272` 에서 계산, `279-283` 반환에 없음 — **유효** |
| 크기 필드를 읽는 소비자가 없다 | `grep -rn --include='*.py' -E "spans\|depth_width\|aspect_ratio" server/` | `rig.py:272,277` 의 지역 변수뿐. `lxseq/parser.py`·`mapper.py`·`web/session.py` 의 `spans` 는 무관한 채널·주소 구간 — **유효** |

두 전제가 모두 살아 있어 작업을 진행했다.

## 3. 무엇을 고쳤나

**생산 쪽** (`server/design/rig.py`)

- `RigGeometry.spans: Mapping[Axis, float] | None` 을 실었다. `_build_geometry`
  가 **이미 계산해 둔** 값을 그대로 넘긴다 — 다시 재지 않고, `dominant_axis`
  를 고르는 `max` 식도 건드리지 않았다.
- `depth_width_ratio` 프로퍼티: 깊이(y) ÷ 폭(x). 좌표계는
  `server/spatial/pointing.py` 와 같다.
- **없으면 없다고 답한다.** 좌표가 없으면 `spans is None`(0 으로 채우지 않음),
  폭 span 이 `SPATIAL_ROW_NOISE_SPAN` 이하면 `depth_width_ratio is None`.

**소비 쪽** (`server/design/interview.py`)

- `_q4_preferred_progression` 이 라벨의 기본값을 실측 비와 대조한다. 깊이가
  폭을 `_DEPTH_DOMINANCE_RATIO`(1.5) 배 넘게 앞서면 `ascending` →
  `descending`.
- **한 방향으로만 뒤집는다.** `depth_rows`·`concentric` 이 모아 들어가는
  서사를 받은 근거는 span 크기가 아니라 구조였고, 그 근거는 비가 커져도
  그대로다. 있지도 않은 대칭을 만들지 않았다.
- `dominant_axis` 는 여전히 읽지 않는다(t314 가 적은 이유 그대로: 전 장비
  원점 리그에도 동률 타이브레이크로 `"x"` 를 답한다).

1.5 는 **잰 값이 아니라 정한 값**이다. 「깊이가 더 크다」(>1.0)로 잡으면 비
1.01 짜리 정사각 리그까지 뒤집혀, 무대에서 아무도 다르게 보지 못할 차이로
제안 순서가 흔들린다. 코드 주석에 그렇게 적어 두었다.

## 4. 동작 변경 측정 (요구 1)

**라벨이 같은데 답이 갈린다.** 좌표는 `server/tests/synthetic_rig.py` 하네스가
만든다(테스트 본문에 숫자를 박지 않았다).

| 리그 | `arrangement` | 깊이/폭 | Q4 첫 제안 |
|---|---|---|---|
| wide grid (폭 10.0m, 깊이 1.0m) | `grid` | 0.1 | `좁음→넓음 (E3 기본)` |
| deep grid (폭 1.0m, 깊이 10.0m) | `grid` | 10.0 | `넓음→좁음 (역순)` |

두 리그는 배치 판독이 구별해 주지 못한다 — 둘 다 `grid`, `low_confidence`
아님. 갈라 주는 것은 t315 가 실은 `spans` 뿐이다.

이 표의 모든 값은 추적되는 시험의 단언으로 박혀 있다. 재현 명령과 그 출력:

```
$ uv run pytest "server/tests/test_design_interview.py::TestQ4ReadsTheStageSize" -v
server/tests/test_design_interview.py::TestQ4ReadsTheStageSize::test_the_same_arrangement_label_with_a_different_ratio_differs PASSED [ 20%]
server/tests/test_design_interview.py::TestQ4ReadsTheStageSize::test_a_ratio_that_does_not_discriminate_keeps_todays_answer PASSED [ 40%]
server/tests/test_design_interview.py::TestQ4ReadsTheStageSize::test_a_degenerate_rig_gets_no_confident_ratio PASSED [ 60%]
server/tests/test_design_interview.py::TestQ4ReadsTheStageSize::test_a_rig_with_no_coordinates_carries_no_spans PASSED [ 80%]
server/tests/test_design_interview.py::TestQ4ReadsTheStageSize::test_a_depth_row_rig_is_not_flipped_by_a_wide_ratio PASSED [100%]
============================== 5 passed in 0.04s ===============================
```

## 5. 음성 대조군 (요구 2)

비가 경계 아래인 리그는 **오늘의 답을 그대로** 낸다.

- `test_a_ratio_that_does_not_discriminate_keeps_todays_answer` — t314 가 세운
  `_LATERAL_POINTS` 리그(`grid`, 깊이/폭 = 0.1). 라벨 세 줄이 바이트 동일:
  `["좁음→넓음 (E3 기본)", "넓음→좁음 (역순)", "사전 등재 순서"]`.
- `test_a_depth_row_rig_is_not_flipped_by_a_wide_ratio` — 폭이 3배 넓은
  `depth_rows` 리그(깊이/폭 = 0.3)도 `넓음→좁음 (역순)` 에 남는다. 대칭으로
  구현했다면 이 리그가 뒤집혔을 자리다.
- t314 가 남긴 기존 시험 4건(`TestQ4ReadsTheStageShape`)이 그대로 초록이다 —
  퇴화 리그·좌표 없는 리그·컨셉 우선 경로가 모두 불변.

## 6. 도달 검사 (요구 3 — t312 의 실패 형태)

t312 는 `RigProfile.geometry` 가 **생산되고 아무도 읽지 않는** 필드였다고
적었다. 같은 결함을 한 층 아래에서 되풀이하지 않았는지 직접 확인했다.

```
$ grep -rn --include='*.py' -E "^[^#]*(\.depth_width_ratio|self\.spans|geometry\.spans)" server/ \
    | grep -v "^server/tests/" | grep -v "def depth_width_ratio"
server/design/interview.py:731:    ratio = rig.geometry.depth_width_ratio
server/design/rig.py:213:        if self.spans is None:
server/design/rig.py:215:        width = self.spans["x"]
server/design/rig.py:218:        return self.spans["y"] / width
```

**비-테스트 소비자: `server/design/interview.py:731`** (`_q4_preferred_progression`
안). 개수는 0 이 아니다.

호출 사슬이 시험 하네스에서 끝나지 않고 감독 경로까지 이어지는지도 확인했다:

```
interview.py:731  rig.geometry.depth_width_ratio
  ← _q4_preferred_progression
  ← _q4_candidates            (interview.py:794)
  ← _build_q4                 (interview.py:807)
  ← build_question
  ← DirectorInterview         (server/web/session.py:7971)
  ← _song_design_interview    (server/web/session.py:11230)
```

그리고 그 경로가 **실제 좌표를 넘긴다** — 이게 더 중요하다. `session.py:7957-7961`
은 콘솔에서 읽은 좌표로 `build_rig_profile(coords=coords)` 를 부르므로,
운영 경로에서 `spans` 가 항상 `None` 인 일은 없다. 필드가 열리기만 하고
운영에서는 죽어 있는 상태가 아니다.

## 7. 뮤테이션 (요구 4)

5개 뮤테이션 전부 잡혔다. 매번 되돌린 뒤 `git diff --stat` 이 빈 출력임을
확인했다.

| # | 뮤테이션 | 빨간 시험 수 | 잡은 시험 |
|---|---|---|---|
| 1 | 비교 방향 뒤집기 (`ratio > ` → `ratio < `) | **3** | `..._the_same_arrangement_label_with_a_different_ratio_differs`, `..._a_ratio_that_does_not_discriminate_keeps_todays_answer`, t314 의 `..._two_rigs_with_the_same_music_and_different_geometry_differ` |
| 2 | 한 방향 가드 제거(대칭 구현) | **3** | `..._a_depth_row_rig_is_not_flipped_by_a_wide_ratio`, t314 의 `..._two_rigs_...`, `..._a_confirmed_concept_still_outranks_geometry` |
| 3 | 생산 배선 끊기 (`spans=spans` → `spans=None`) | **8** | rig 4건 + interview 4건 |
| 4 | 정직한 부재 깨기 (폭 0 일 때 `None` → `0.0`) | **2** | `test_depth_width_ratio_is_absent_when_the_rig_has_no_width`, `..._a_degenerate_rig_gets_no_confident_ratio` |
| 5 | 경계 무력화 (1.5 → 100.0) | **1** | `..._the_same_arrangement_label_with_a_different_ratio_differs` |

뮤테이션 2 가 특히 이 카드의 설계 판단을 지킨다: 한 방향 가드가 없으면
폭 넓은 `depth_rows` 리그가 `ascending` 으로 올라간다.

## 8. 전체 시험 (요구 5)

이 워크트리 자체 인터프리터로 전수 실행:

```
$ uv run pytest server/tests -q
..................................                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.11/site-packages/fastapi/testclient.py:1
  .../.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
12027 passed, 31 skipped, 1 warning in 167.04s (0:02:47)
```

경고 1건은 이 변경과 무관한 기존 `fastapi`/`starlette` 항목이다 — 새로 생긴
경고가 아니다.

린트·포맷:

```
$ uv run ruff check <변경 파일 5개>
All checks passed!
$ uv run pytest server/tests/test_overlap_preserve.py::TestTouchedFilesPassLint -q
4 passed in 0.18s
```

첫 전수 실행에서 `TestTouchedFilesPassLint::test_ruff_format_reports_no_change`
가 `server/tests/test_design_interview.py` 를 잡았다. `ruff format` 을 돌려
해소한 뒤 재실행해 초록을 확인했다(위 출력).

## 9. 재지 않은 것

- **실기 콘솔 확인 0건.** 데스크가 오프라인이라 grandMA3 에서 읽은 좌표로
  이 경로를 굴려 보지 못했다. 이 카드의 모든 기하는 하네스가 만든 **합성**
  좌표다. 실제 무대의 리그가 어떤 비를 내는지는 미측정이다.
- **1.5 경계가 실기에서 옳은 값인지 미검증.** 정한 값이고, 어떤 실측도
  이 숫자를 지지하지 않는다. 실기 리그의 비 분포를 재면 조정 근거가 생긴다.
- **감독이 이 제안 순서를 더 낫다고 느끼는지 미검증.** 이 카드가 잰 것은
  「기하가 답을 바꾼다」이고, 「바뀐 답이 더 좋다」는 연출 판단은 사람이
  봐야 한다.
- **`concentric`·`vertical_levels` 라벨에서의 비 분포 미측정.** 규칙상 이
  둘은 `ascending` 이 아니라 뒤집기 대상이 아니지만, 실제로 어떤 비를 내는
  리그들인지는 재지 않았다.
- **CI 초록 미확인** (이 보고서 작성 시점). PR 푸시 뒤 확인 필요.
- **`_q4_rig_note` 문면은 건드리지 않았다.** 비가 순서를 바꿨을 때도 문면은
  여전히 배치 라벨만 말한다. 「기하가 정했다」는 주장 자체는 참이라 거짓이
  되지는 않지만, 크기가 정한 경우를 문면에 드러내지는 않는다 — 범위 밖으로
  두었다.

🗿 MoAI
