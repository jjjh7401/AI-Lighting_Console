# t445 판정서 — 후렴 색 운용을 곡별 선택으로

- 카드: t445 (클래스 C, 감독 결정 2026-09-23 「음악 스타일마다 다르니 하나로 고정은 무리」)
- 브랜치: `WT-chorus-color-mode`, 기준 `origin/main` db601e8a
- 콘솔 쓰기: 0 (계획·게이트·테스트 모두 메모리 안에서만 계산)
- 리드 결정: A안 채택. 배차서의 「고르지 않은 곡은 바이트 동일」 조건은 감독 결정(기본은 주색 고정)에 따라 철회됨

## 1. 주장

기본 색 운용(`modulate`, Q2B 빈 답 포함)과 `single` 에서, 긴 후렴(chorus/finale)을 마디 단위로 나눈
큐도 주색을 유지한다. 한 후렴 안에서 주색·보조색을 맞바꾸는 t305 동작은 넷째 곡별 선택
`split_swap` 으로 옮겼다.

| 색 운용(Q2B) | 후렴 분할 큐 | G7(후렴 주색 동일) |
|---|---|---|
| `modulate`(기본)·`single` | 주색 고정, 보조색만 돈다. 돌릴 보조색이 없으면(2색) 쪼개지 않는다 | 판정 |
| `per_chorus` | 기존 그대로(회차마다 색 변화 + 분할 회전) | n/a (t439) |
| `split_swap` (신규) | 고치기 전 기본 동작과 같다(주·보조색 교대) | n/a (신규) |

- verse·intro·bridge 등 후렴이 아닌 역할의 분할 회전은 바꾸지 않았다.
- 감독이 곡마다 고르는 자리는 기존 인터뷰 Q2B 카드다. 런북 화면에는 고르는 곳이 없어서
  새 UI는 만들지 않았다. `analysisSummary.ts` 에는 표시 라벨만 추가했다.
- Q2B 카드는 선택지 3개를 유지한다. `QuestionCard` 가 표준 §2d 「제안 3개」를 기계적으로
  강제하기 때문이다(`interview.py` `__post_init__`). `split_swap` 은 1급 자유 입력(DI3)으로
  받는다. 키워드는 맞바꾸·교대·분할·swap 이고, single 다음·modulate 앞 순서로 판정한다.
  카드의 why 문구에 「맞바꾸기라고 직접 적어 주세요」를 붙였다.
- 두 입구 일치: 경로 B(곡 업로드, `_override_songcue_main_color`)도 `split_swap` 이면
  후렴 분할 조각마다 주·보조색을 맞바꾸게 했다.

## 2. 증거

### 2.1 같은 probe 전후 — `probe.py`

BPM 120, 32초(16마디) 후렴 3회 + 절, Q2B 빈 답(기본).

| | 수정 전(`probe_before.txt`) | 수정 후(`probe_after.txt`) |
|---|---|---|
| 큐 수 | 11 (입력 구간 8) | 8 |
| 후렴 큐 주색 | blue / warm white 교대 ×3 | blue ×3 |
| G7 | passed=False, 위반 5건 | passed=True, 위반 0건 |

`split_swap` 을 고르면 수정 전 기본 출력과 같다. 테스트
`TestSplitSwapKeepsThePreviousBehaviour` 가 이 값을 고정한다: 후렴 행
`('Chorus (1/2)', ('blue','warm white')), ('Chorus (2/2)', ('warm white','blue'))` ×3, 큐 11개.
세션 단계에서도 확인했다. `test_web_session.py` 의 t305 시험 둘은 Q2B 에 「맞바꾸기」를
답하게만 바꿨고, 기댓값(9큐, 시작 시각 목록, 여는 큐 ≠ 잇는 큐)은 한 글자도 고치지 않았다.
둘 다 통과한다.

### 2.2 두 입구 표 — `probe_two_paths.py` → `probe_two_paths_after.txt`

같은 곡 모양, 같은 답(Q2 블루). 경로 A = 인터뷰, 경로 B = 곡 업로드. RGB (5,20,100) = 블루,
(100,75,40) = warm white (`color_names.resolve_color_name` 실측).

| Q2B | 경로 A 후렴 큐 주색 | 경로 B 후렴 큐 주색 |
|---|---|---|
| `modulate` | 블루 ×3 (분할 없음) | 블루 ×6 (조각 2개씩) |
| `split_swap` | 블루, warm white 교대 ×3 | 블루, warm white 교대 ×3 |

- 주색 순서는 두 입구가 같다.
- 큐 수는 다르다(기본에서 A 3, B 6). B 는 색이 아니라 룩 목록을 돌려 쪼개므로 2색이어도
  조각이 서로 다르다. 이 차이는 이 카드 이전부터 있던 설계(t306)라 바꾸지 않았다.

### 2.3 대조군 — 소스를 되돌리고 새 시험 실행 (`control_run.txt`)

소스 4개(`session.py`·`gates.py`·`interview.py`·`tools.py`)만 되돌리고 시험은 그대로 둔 채
돌렸다: **16 failed, 8 passed**. 실패한 16건은 새 시험과 바꾼 시험이다. 통과한 8건은 수정
전에도 참인 성질(대조 성격)이다. 예: per_chorus G7 n/a, modulate 대조군 G7 FAIL, verse 회전
불변, split_swap 바이트 고정, 복제 큐 없음. 되돌린 뒤 다시 적용했다.

### 2.4 검증 명령

- `uv run pytest -q server/tests/test_chorus_split_color_t445.py` → 20 passed
- `uv run pytest -q server/tests -k "color or chorus or split or density or interview or concept or gate or palette or songcue or song or colormode or session or timeline or cue or tools"` → 3473 passed, 24 skipped
- `uv run ruff check server .moai/reports/t445` → All checks passed · `ruff format` 적용
- `npm --prefix ui test -- --run` → 583 passed (25 files) · `npm --prefix ui run build` 성공
- 전체 스위트는 CI 에서 돈다(레인 규약: 레인은 영향 범위만).

## 3. 바뀌는 바이트 범위

- **기본(modulate, 빈 답 포함)·single 곡의 후렴(chorus/finale) 중 분할 단위(8마디) 2개 이상인 것.**
  - 2색 팔레트(보통의 경우: 주색 + 아크 악센트): 쪼개지 않아 큐 수가 준다(probe 11→8). 색은 여는 큐와 같다.
  - 3색 이상: 여전히 쪼갠다. 주색은 고정하고 보조색만 돈다.
- 경로 B 는 기본에서 바이트 변화가 없다. `split_swap` 을 고른 곡만 후렴 분할 조각의 주색이 바뀐다.
- 16마디 미만 후렴, 후렴이 아닌 역할, BPM 미선언 곡(분할 없음)은 바뀌지 않는다.

## 4. 미검증

- 실기 콘솔 육안 확인은 하지 않았다(콘솔 쓰기 0).
- 실제 곡 9곡으로 큐 수 변화를 전수 측정하지 않았다. 합성 곡과 세션 시험 곡(`_BPM_BRIEF`: 9→8큐)만 쟀다.
- 3색 이상 후렴의 보조색 회전은 코드 경로로만 확인했다. 전용 시험은 없다(이 카드의 입력 곡에는 2색만 있었다).
- 경로 B 의 `split_swap` 조각 순번은 연속한 같은 `(label, instance)` 로 센다. 조각이 연속하지 않는 입력은 `split_selections_for_density` 구조상 생기지 않지만 따로 쏘지는 않았다.
- 콘셉트 게이트 경로 B(`build_concept_report_from_songcue_sections`)는 `color_usage` 를 받지 않는다. 그래서 경로 B 에서 `split_swap` 곡의 G7 은 n/a 가 아니라 입력 색 기준으로 판정된다. 이 카드는 경로 A 게이트만 다뤘다.

## 5. 잔여 위험

- 기본 곡의 긴 후렴 큐 수가 줄어 G13(큐 밀도 10~45) 하한에 가까운 곡이 생길 수 있다. probe 곡은 시퀀스 큐 20개로 통과했다.
- 자유 입력 키워드 「분할」이 다른 뜻의 문장(예: 「분할 없이 단색」)에 걸릴 수 있다. single 판정을 먼저 하므로 「단색」이 들어가면 single 이 된다.

## 6. 판정

PASS (리드 확인 대기). 주장 §1 의 세 성질(기본 고정·split_swap 이전 동작 유지·G7 존중)과
두 입구 주색 일치를 전후 probe, 시험 20건, 대조군 16 FAIL 로 확인했다.
