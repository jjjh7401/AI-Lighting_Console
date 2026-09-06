# SPEC-COPILOT-D1GRANT-001 — 진행 기록

> 카드 t282 후속 · Tier M · 기준 트리 `main` `a1e75e5` (2026-09-06)

## §E.1 Plan-phase Audit-Ready Signal

- 산출물: `spec.md` · `plan.md` · `acceptance.md` · `progress.md` (Tier M 4종)
- REQ: 21건 (REQ-D1GRANT-001..021), 전부 GEARS 마커 표기
- AC: 14건 (AC-D1GRANT-001..014), 전부 Given/When/Then
- 범위 제외: `### Out of Scope` H3 4개 (선택 로직 · 다른 장르/칸 · 게이트 구조 · 실기 발사와 색 보정)
- 미해결 clarification 마커: 없음
- 콘솔 예산: 읽기 전용, 쓰기 0

### plan 단계에서 실제로 잰 것 (이 트리, 이 회차)

| 잰 것 | 명령 | 관측 |
|---|---|---|
| D1 인구조사 | 워크트리 루트에서 `uv run python` 으로 `looks_for_genre` 순회 (프로브 스크립트는 실행 후 삭제) | `edm [('edm-ambient-hold', ('배경',))]` · `rock [('rock-empty-stage', ('배경',))]` · ballad·worship 은 각 2건 |
| 실기 18그룹 역할 결속 | 같은 회차 `resolve_roles` | `mapped: ['백라이트','사이드','스페셜','프론트']` · `unmapped: {'탑':'no_match','배경':'no_match'}` |
| 정렬 축 | `server/looks/busking.py:81-97` 판독 + `sorted()` 확인 | `looks_for_genre` = `sorted(key=(dynamics, look_id))`. `['edm-ambient-hold','edm-haze-shafts']` · `['rock-empty-stage','rock-wing-embers']` |
| 착수 초록 | `.venv/bin/python -m pytest server/tests/test_overlap_preserve.py server/tests/test_songcue_rig_aware_look.py -q -p no:cacheprovider` | `130 passed in 2.15s` |
| 인터프리터 귀속 | `server/tests` 하위에서 `../../.venv/bin/python -c "import server; print(server.__file__)"` | 이 워크트리의 `server/__init__.py` — 남의 트리 `.pth` 가 이기지 않았다 |
| 룩 디렉터리 승인 diff | `git diff --numstat 95687a0e..HEAD -- server/looks/library/` | `ballad 2/2` · `edm 1/1` · `worship 2/2` (rock 없음) |
| `edm.yaml` 훅 위치 | `git diff --unified=0 95687a0e..HEAD -- server/looks/library/edm.yaml \| grep '^@@'` | `@@ -74 +74 @@` — 훅 하나 |
| 기준 커밋 파일 길이 | `git show 95687a0e:server/looks/library/{edm,rock}.yaml \| wc -l` | `156` · `141` |
| 개수 의존 소비자 (부분) | `grep -rn 'len(looks_for_genre\|== 9' server/tests/` 외 | `test_busking_genre.py:30,45` · `test_looks_matching.py:676` · `edm.yaml:7` · `busking.py:13` · `test_looks_library.py:50` (`MAX_LOOKS_PER_GENRE = 10`) · `preshow/checks.py:111` (동적, 핀 아님) |
| SPEC ID 형식 | `[[ "SPEC-COPILOT-D1GRANT-001" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` | `PASS` |

### plan 단계에서 **안** 잰 것

- 두 룩을 실제로 넣은 상태의 게이트 판정 — 이 SPEC 은 라이브러리를 한 바이트도 안 바꿨다(plan 단계). §1.3 에 인용한 실패 출력은 **PR #344 브랜치의 것**이며, run 단계가 이 트리에서 다시 만든다.
- 개수 의존 자리의 **전수** — 위 표는 부분 스윕이다. 전수는 REQ-020 이 run 단계에 요구한다.
- 실기 콘솔 발사 0건. 색·밝기 값은 이웃 룩에서 역산한 설계값이다.
- 실기 cyc 리그 지문에서의 무회귀 — 대조는 합성 리그 `_CYC_RIG` 로만 계획돼 있다.
- PR #344 의 머지 여부는 시점 의존이라 착수 시 다시 잰다(plan.md B-6).

- plan_status: audit-ready
- plan_complete_at: 2026-09-06

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
