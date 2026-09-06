# SPEC-COPILOT-D1GRANT-001 — 수용 기준

> 모든 기준은 **기계로 확인 가능**하다. 각 항목은 실행할 명령과 단언할 값을 함께 적는다.
> 기준 트리: `main` `a1e75e5` (2026-09-06) · 게이트 기준 커밋: `_PRECHK_BASE` `95687a0e`
> 검증 인터프리터: 워크트리 안의 `.venv/bin/python` (귀속을 progress 에 남긴다)

---

## §D 수용 기준 표

| AC | 대응 REQ | 층 |
|---|---|---|
| AC-D1GRANT-001 | REQ-001, REQ-002 | 오프라인 (라이브러리 로드) |
| AC-D1GRANT-002 | REQ-001, REQ-002 | 오프라인 (기록 포트 도달) |
| AC-D1GRANT-003 | REQ-003 | 오프라인 (정렬 축) |
| AC-D1GRANT-004 | REQ-003 | 오프라인 (무회귀, cyc 리그) |
| AC-D1GRANT-005 | REQ-004, REQ-005 | 오프라인 (diff 형상) |
| AC-D1GRANT-006 | REQ-006 | 오프라인 (선언 층 불변) |
| AC-D1GRANT-007 | REQ-007, REQ-008, REQ-009, REQ-010, REQ-011 | 오프라인 (게이트 통과) |
| AC-D1GRANT-008 | REQ-012 | 오프라인 (심은 변경 — 게이트가 여전히 거절) |
| AC-D1GRANT-009 | REQ-013 | 오프라인 (게이트 골격 불변) |
| AC-D1GRANT-010 | REQ-014 | 오프라인 (핀 교체 + 전/후 기록) |
| AC-D1GRANT-011 | REQ-015 | 오프라인 (행렬 + 음성 대조) |
| AC-D1GRANT-012 | REQ-016 | 오프라인 (skip 0건) |
| AC-D1GRANT-013 | REQ-017, REQ-018, REQ-019, REQ-020 | 오프라인 (개수 소비자 전수) |
| AC-D1GRANT-014 | REQ-021 | 오프라인 (콘솔 예산) |

---

## §D.1 라이브러리 내용

### AC-D1GRANT-001 — 두 룩이 명세대로 존재한다

- **Given** 워킹트리의 `server/looks/library/` 를 `load_library_from_dir` 이 프로덕션과 같은 방식으로 읽는다.
- **When** `looks_for_genre(library, "edm")` 과 `looks_for_genre(library, "rock")` 에서 `dynamics == 1` 인 룩을 뽑는다.
- **Then** edm 의 D1 목록은 `["edm-ambient-hold", "edm-haze-shafts"]` 이고 `edm-haze-shafts` 의 `roles` 는 `("백라이트",)`, `Dimmer 18` · `ColorRGB_R 0` · `ColorRGB_G 40` · `ColorRGB_B 78` 이다. rock 의 D1 목록은 `["rock-empty-stage", "rock-wing-embers"]` 이고 `rock-wing-embers` 의 `roles` 는 `("사이드",)`, `Dimmer 22` · `ColorRGB_R 65` · `ColorRGB_G 10` · `ColorRGB_B 22` 이다.
- **그리고** `server/tests/test_looks_library.py` 전량이 초록이다 — 스키마·색 3채널·강도·역할 어휘·한국어 display_name·무브먼트 0건·`FORBIDDEN_ATTRIBUTE_TOKENS` 미검출·`PER_SHOW_PATTERN` 미검출·장르당 6~10룩.

### AC-D1GRANT-002 — cyc 없는 리그에서 조용한 구간이 큐를 받는다

- **Given** `_REAL_RIG`(실기 18그룹, `Cyc` 도 `Top` 도 없다)가 그룹 섹션으로 주어진다.
- **When** `_stored_cues(library, genre, "ambient", _REAL_RIG)` 를 edm·rock 에 대해 실행한다 — 이 헬퍼는 문자열 검색이 아니라 도구 → 게이트 → `run_commands` → 기록 포트까지 실제 경로를 타고 `Store Sequence` **도달**을 잰다.
- **Then** 두 장르 모두 빈 목록이 **아니다**. 고쳐지기 전 이 두 호출은 `[]` 였다(`test_songcue_rig_aware_look.py:255-257` 의 옛 단언).
- **그리고** 같은 회차의 음성 대조 — `_UNBINDABLE_RIG`(어느 역할에도 안 걸리는 리그)로 같은 호출을 하면 네 장르 모두 `[]` 다.

### AC-D1GRANT-003 — 무회귀의 축이 검사로 고정된다

- **Given** `looks_for_genre` 가 `(dynamics, look_id)` 로 정렬한다는 사실(`server/looks/busking.py:81-97`).
- **When** edm·rock 의 D1 목록을 읽는다.
- **Then** 각 장르의 **첫** D1 룩이 기존 룩(`edm-ambient-hold` / `rock-empty-stage`)이며, 그 성질이 **파일 위치가 아니라 `look_id` 사전순 때문**임을 단언하는 검사가 존재한다 — 즉 `기존 look_id < 새 look_id` 를 직접 단언한다.
- **그리고** `test_busking_genre.py::TestDeterministicTotalOrder` 가 초록이다(정렬 규칙 자체의 수호자).

### AC-D1GRANT-004 — cyc 있는 리그는 한 칸도 움직이지 않는다

- **Given** `_CYC_RIG`(`Back Wash`·`FOH Wash`·`Side L`·`Top`·`Cyc`·`Special`, 역할 6종 전부 묶임)가 주어진다.
- **When** 네 장르 × dynamics 1~5 로 `_chosen(...)` 을 실행한다(`TestCycRigIsUnchanged`).
- **Then** 고른 룩이 전부 `_naive_first_match`(오늘의 규칙)와 **같다**. 특히 edm D1 은 `edm-ambient-hold`, rock D1 은 `rock-empty-stage` 다.
- **그리고** `_stored_cues(..., "ambient", _CYC_RIG)` 가 네 장르 모두 비어 있지 않다.

---

## §D.2 게이트와 선언 층

### AC-D1GRANT-005 — diff 형상이 승인된 모양 그대로다

- **Given** 게이트 기준 커밋 `95687a0e`.
- **When** `git diff --numstat 95687a0e..HEAD -- server/looks/library/` 와 `git diff --unified=0 95687a0e..HEAD -- <각 파일>` 을 실행한다.
- **Then** 바뀐 파일은 정확히 넷(`ballad.yaml`·`edm.yaml`·`rock.yaml`·`worship.yaml`)이고, 삭제 줄은 승인된 「파란」 옛 줄 **넷**뿐이다(`ballad` 2 · `edm` 1 · `worship` 2 → 합 5 … 실제 수치는 실행 출력으로 확정하며, `rock.yaml` 의 삭제는 **0**이어야 한다).
- **그리고** `edm.yaml` 과 `rock.yaml` 각각에 `old_count == 0` 인 삽입 훅이 **정확히 하나** 있고 그 `old_start` 는 기준 커밋 본문의 줄 수와 같다(edm 156, rock 141).
- **그리고** 각 삽입 블록에 `- look_id:` 가 **정확히 한 번** 나타난다.

### AC-D1GRANT-006 — 닫힌 SPEC 의 선언은 바이트 동일하다

- **Given** `SPEC-COPILOT-PRECHK-001` 은 닫혀 있고 그 `plan.md:89` §A.5 가 원 선언이다.
- **When** `git diff --stat origin/main..HEAD -- .moai/specs/SPEC-COPILOT-PRECHK-001/` 을 실행한다.
- **Then** 출력이 빈 문자열이다.

### AC-D1GRANT-007 — 게이트가 새 승인으로 통과한다

- **Given** `_LOOKS_GRANTED_D1_APPENDS` 가 등록되고 `TestLooksLibraryGrantedExtension` 이 갱신됐다.
- **When** `.venv/bin/python -m pytest server/tests/test_overlap_preserve.py -q -p no:cacheprovider` 를 실행한다.
- **Then** 전량 초록이고, 새 상수 위의 승인 주석이 `2026-09-06 granted addition — SPEC-COPILOT-D1GRANT-001` 로 시작해 이 SPEC ID 를 문면에 담는다(`grep -n 'SPEC-COPILOT-D1GRANT-001' server/tests/test_overlap_preserve.py` 가 1행 이상).
- **그리고** 파일 집합 단언이 두 승인의 **합집합**을 요구하고, 줄 텍스트 단언이 `==`(부분집합 아님)를 유지한다.

### AC-D1GRANT-008 — 게이트는 여전히 거절한다 (심은 변경 셋)

- **Given** 반영이 끝난 트리.
- **When** 다음 셋을 하나씩 심어 커밋하고 `test_overlap_preserve.py` 를 실행한 뒤 **되돌린다**: ① `ballad.yaml` 에 한 줄 추가, ② `rock.yaml` 에 두 번째 룩 블록 추가, ③ `edm.yaml` 에서 기존 줄 하나 삭제.
- **Then** 세 경우 모두 `TestLooksLibraryGrantedExtension` 이 **실패**하고, 각 실패 출력의 꼬리가 progress 에 인용된다.
- **그리고** 되돌린 뒤 같은 명령이 다시 초록이고, `git diff --stat origin/main..HEAD -- server/looks/library/` 가 심기 전과 같다.

### AC-D1GRANT-009 — 게이트 골격은 안 움직였다

- **Given** 반영이 끝난 트리.
- **When** `git diff origin/main..HEAD -- server/tests/test_overlap_preserve.py` 를 읽는다.
- **Then** `_PRESERVE_PATHS`(10항목)·`_PRECHK_BASE`·`_preserve_diff_command()` 의 본문에 변경 hunk 가 **0건**이다.
- **그리고** `TestPreserveList::test_the_list_has_ten_entries` 와 `TestPreserveDiffIsEmpty` 가 초록이다.

---

## §D.3 뒤집히는 핀

### AC-D1GRANT-010 — 잔여 기록이 의도적으로 교체된다

- **Given** `TestWhatThisFixCannotReach` 는 「이 수정이 닿지 못하는 곳」의 기록이었다.
- **When** `server/tests/test_songcue_rig_aware_look.py` 를 읽는다.
- **Then** 그 클래스가 **삭제되지 않고 교체**되어 있으며, 새 독스트링이 **전**(edm·rock 의 D1 룩이 하나이고 역할이 `("배경",)` 뿐이었다는 것, `ambient` 가 `[]` 였다는 것)과 **후**(두 장르가 묶이는 D1 룩을 얻었다는 것)를 함께 적는다.
- **그리고** 새 단언이 네 장르 전부에 대해 「역할이 `{탑, 배경}` 의 부분집합이 아닌 D1 룩이 하나 이상 있다」와 「`ambient` 밴드가 실기 리그에서 큐를 받는다」를 요구한다.

### AC-D1GRANT-011 — 행렬과 그 음성 대조가 같은 자리에 있다

- **Given** `test_the_matrix_is_recorded_for_the_report`.
- **When** 그 함수를 실행한다.
- **Then** 실기 리그 행렬이 `{"ballad": "OOOOO", "edm": "OOOOO", "rock": "OOOOO", "worship": "OOOOO"}` 다.
- **그리고** **같은 함수 안에서** `_UNBINDABLE_RIG` 로 잰 행렬이 `{"ballad": "XXXXX", "edm": "XXXXX", "rock": "XXXXX", "worship": "XXXXX"}` 임을 단언한다 — 전량 O 인 행렬만으로는 계측기의 공허함이 구별되지 않는다.

### AC-D1GRANT-012 — 부재 트립와이어가 자기 목적을 다하고 사라진다

- **Given** `server/tests/test_songcue_d1_cycless.py`.
- **When** `.venv/bin/python -m pytest server/tests/test_songcue_d1_cycless.py -q -rs -p no:cacheprovider` 를 실행한다.
- **Then** **skip 0건**이고 전량 통과다.
- **그리고** `grep -c 'pytest.skip\|_require_proposed\|TestTheSkipIsNotAPermanentPass' server/tests/test_songcue_d1_cycless.py` 가 `0` 이다.

---

## §D.4 개수 소비자와 예산

### AC-D1GRANT-013 — 개수를 세는 자리가 전수로 갱신된다

- **Given** edm 이 9→10, rock 이 8→9 가 된다.
- **When** `.venv/bin/python -m pytest server/tests -q -p no:cacheprovider` 를 실행하고, 별도로 룩 개수 의존 자리를 grep 으로 훑는다.
- **Then** 전량 초록이며 새 실패 0건이다.
- **그리고** `test_busking_genre.py` 의 `_EXPECTED_COUNTS` 가 `{"worship": 8, "rock": 9, "ballad": 7, "edm": 10}` 이고, edm 검사의 비공허 근거 `len(edm) > MAX_TOOL_MATCHES` 가 남아 있다.
- **그리고** `test_looks_matching.py` 의 `report["total"]` 기대값이 `10` 이다.
- **그리고** `grep -rn 'Nine looks' server/` 가 **0행**, `grep -n '9룩' server/looks/busking.py` 가 **0행**이며, `busking.py` 의 해당 문장이 「사라지는 건수」를 새 값으로 다시 쓴 것이지 숫자만 갈아끼운 것이 아니다.
- **그리고** run 단계가 실행한 전수 스윕 명령과 그 출력이 progress 에 있다. plan 단계 실측 세 건이 전부라는 주장을 하지 않는다.

### AC-D1GRANT-014 — 콘솔 예산 0

- **Given** 이 SPEC 의 모든 검증.
- **When** 회차 전체를 되짚는다.
- **Then** UDP 전송 0건, `127.0.0.1:8000` 대상 실행 0건이며, conftest 의 라이브 포트 거절 가드가 실패시킨 검사가 없다.
- **그리고** progress 의 §E.2 가 그 사실을 명시한다.

---

## §D.5 완료 정의 (Definition of Done)

- AC-001..014 전부 PASS 이며 각 항목이 **실행한 명령과 그 출력**으로 뒷받침된다.
- `server/tests` 전량 초록, 새 회귀 0건.
- 심은 변경 세 종의 실패 출력이 인용돼 있고, 되돌림이 diff 로 확인된다.
- `SPEC-COPILOT-PRECHK-001/` diff 0.
- 미검증 항목이 progress 에 **명시적으로** 열거된다 — 최소한 다음 셋은 이 SPEC 이 닫혀도 미검증으로 남는다: 실기 콘솔 발사, 실기 cyc 리그 지문에서의 무회귀, 색·밝기의 무대 적합성.
