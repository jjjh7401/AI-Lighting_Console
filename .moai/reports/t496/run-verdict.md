# t496 판정서 — 런북 UI 사본이 서버 실출력과 다시 어긋나는 걸 막는 대조 시험 (+ t495 주석)

- 카드: t496(주) · t495(같은 PR, 주석 한 줄) · 워크트리 `.claude/worktrees/t496` · 브랜치 `WT-payload-drift-guard`
- 기준: `origin/main` = `25d912a1`. **EnterWorktree 가 `f0b0071d`(한 머지 전)에서 트리를 만들었다** → `git merge --ff-only origin/main` 뒤 `25d912a1` 확인(`git merge-base --is-ancestor 25d912a1 HEAD` 통과).
- 콘솔 접촉 0. 서버 제품 코드 변경 0(시험·시험 도우미만).

## 판정

- **t496: PASS.** 대조 시험이 실제로 어긋난 사본(착수 시 사본)에서 FAIL 하고, 재생성 명령을 오류 문구에 싣고, 재생성 뒤 PASS 한다.
- **t495: PASS.** 만료 주석(「t467 로 넘긴다」)을 t467 의 실제 결말(n/a 닫힘, 감독 결정 2026-09-27)로 고쳤다.

## 1. 착수 시 사본은 또 어긋나 있었다

| 측정 | 명령 | 결과 | 원본 |
|---|---|---|---|
| 실출력 생성 | `uv run python .moai/reports/t496/measure_payload.py`(t493 스크립트 사본, 출력 경로만 변경) | rows 21, hex 8개 — t493 stdout 과 같음 | `regen_stdout.txt`, `payload.json` |
| 결정성 | 두 번 돌려 `cmp` | 동일 | — |
| 사본 대조 | `cmp ui/src/components/runbookServerPayload.json .moai/reports/t496/payload.json` | **다름**(char 17307, line 801) | — |
| 텍스트 diff | `diff 사본 실출력` | 61줄, 한 덩어리: 최상위 `beat_grid` 키 추가(실출력에만) | `payload_diff.txt` |

- t493(`6ee9b8f5`) 이후 서버 타임라인 페이로드에 `beat_grid`(곡 비트 그리드 — `bar_range`·`tracks`·`probe_results`·`movement_vocabulary` 등)가 들어갔고, 사본은 그 뒤 다시 뜨지 않았다. 구조 차이 **34건**, 전부 `$.beat_grid` 아래다.
- `beat_grid` 를 넣은 카드는 이 카드에서 짚지 않았다(키 이름만으로는 출처가 갈리지 않는다). 서버 실경로가 지금 그 키를 낸다는 것만 확정이다.

## 2. 무엇을 만들었나

- `server/tests/runbook_payload_fixture.py`(신규, `fake_console.py` 와 같은 시험 도우미 모듈)
  - `build_payload()` — t458/t493 스크립트와 같은 8구간·120 BPM 곡 → `_song_timeline_payload`(서버 실경로).
  - `write_fixture()` + `__main__` — **재생성 명령**: `uv run python -m server.tests.runbook_payload_fixture`. 직렬화는 t493 과 같다(`ensure_ascii=False, indent=1`). 이 명령으로 다시 뜬 사본은 t493 스크립트 경로 출력과 **바이트 동일**하다(`cmp` → 동일).
- `server/tests/test_runbook_payload_fixture_t496.py`(신규)
  - `key_paths` — 키 경로 집합. 목록 원소의 키는 `[]` 한 경로로 합친다(원소마다 있는 선택 키도 잡힌다).
  - `list_lengths` — 목록 길이(행 수). 목록 안의 목록은 원소 번호로 가른다(구간마다 `intensity` 길이가 다르다).
  - `test_fixture_structure_matches_server_output` — 실출력 대비 사본의 구조 차이가 있으면 실패. 오류 문구에 차이 목록(최대 20건 + 「외 N건」) + `다시 뜨기: uv run python -m server.tests.runbook_payload_fixture`.
  - `TestStructureDiffCatches` 7건 — 값만 다름(통과) · 새 키 · 사본에만 있는 키 · 행 수 · 목록 원소 안 새 키 · 중첩 목록 길이 · 오류 문구에 명령.
- `ui/src/components/runbookServerPayload.json` — 위 명령으로 재생성(`beat_grid` 추가).
- `ui/src/components/runbookM7Third.test.tsx` 머리 주석 — 재생성 명령과 대조 시험 위치 두 줄.
- **t495**: `ui/src/components/cueRequestWarnings.ts:3-6` — 「서버 필드 노출 카드(t467)로 넘긴다」 → 「t467 은 두 값 모두 그 뜻으로는 서버에 없어 n/a 로 닫혔다(감독 결정 2026-09-27, .moai/reports/t467/verdict.md). 두 경고는 꺼진 채로 둔다.」 근거: `.moai/reports/t467/verdict.md:6`.

## 3. 증거

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| RED(착수 시 사본) | `uv run pytest -q server/tests/test_runbook_payload_fixture_t496.py` | **1 failed, 7 passed** — `사본에 없는 키: $.beat_grid` … 「외 14건」 + 「다시 뜨기: uv run python -m server.tests.runbook_payload_fixture」 | `red.txt` |
| 재생성 | `uv run python -m server.tests.runbook_payload_fixture` | `wrote …/runbookServerPayload.json`, t493 경로 출력과 `cmp` 동일 | `regen_cmd.txt` |
| GREEN | 같은 pytest | **8 passed** | `green.txt` |
| 범위 | `pytest server/tests/test_runbook_payload_fixture_t496.py server/tests/test_song_timeline_concept_report_wiring.py` | 13 passed | `pytest_scope.txt` |
| 대조군 발사 | `uv run python .moai/reports/t496/fire_controls.py` | **7/7 기대대로**(아래 표) | `fire_controls.txt` |
| UI 전체(새 사본) | `cd ui && npx vitest run` | 59 파일 · **1262 passed** | `vitest_full.txt` |
| 타입 | `npx tsc --noEmit -p ui` | 오류 0 | `tsc.txt` |
| 린트 | `ruff check` + `ruff format --check`(새 .py + 증거 .py) | All checks passed / already formatted | `ruff.txt` |

대조군(사본 파일은 건드리지 않고 메모리에서 비교):

| 대조군 | 차이 | 기대 |
|---|---|---|
| C0 재생성 뒤 사본 | 0 | 0 ✅ |
| C1 t458 시점 사본(`b9c28959`) | 53 | >0 ✅ |
| C2 착수 시 사본(`25d912a1`) | 34 | >0 ✅ |
| M1 `concept_report.rows` 한 줄 뺌 | 1 (`rows: 서버 21 · 사본 20`) | >0 ✅ |
| M2 `rows[0]` 에 키 추가 | 1 (`rows[].extra`) | >0 ✅ |
| M3 `sections[0].intensity` 한 칸 뺌 | 1 | >0 ✅ |
| M4 값만 바꿈(구조 같음) | 0 | 0 ✅ |

C1 의 `beat_grid` 밖 차이 19건(`c1_non_beatgrid.txt`)은 t493 이 찾은 구조 변화와 맞는다: `concept_bullet` · `concept_report.glance` · `concept_report.reserve` · `rows[].description` · `rows[].unused_groups` · `rows`/`mib` 20→21. 즉 이 시험이 t458 시점에 있었다면 t493 의 구조 어긋남을 잡았다.

## 4. 안 잰 것 / 한계

- **값은 비교하지 않는다(카드 범위 — 키 집합·행 수).** t493 의 80항목 중 값만 바뀐 것(`rows[].evidence` null→문자열, `sections[].intensity[].level`, 게이트 detail 숫자, q19 라벨 등)은 이 시험이 못 잡는다. 값까지 잠그면 서버 변경마다 사본을 다시 떠야 하는 부담이 생긴다 — 필요하면 별도 카드.
- 사본을 읽는 곳은 셋이다(`runbookM7Third.test.tsx`·`runbookMibWarning.test.tsx`·`runbookPreview.tsx`). 미리보기 화면(`runbookPreview.tsx`)은 이번에 띄워 보지 않았다 — 최상위 키가 하나 늘었을 뿐 기존 키는 그대로다(C2 차이 34건 = 새 키 28 + 새 목록 길이 6, 전부 `$.beat_grid` 아래, 사본에만 있는 키 0 — `start_copy.json` 으로 분류).
- 서버 전체 pytest 는 돌리지 않았다(시험 도우미·시험만 추가 — CI 가 전체를 돈다).
