# t651 머지 기록 — PR #689

- 카드: t651 · 브랜치 `WT-grid-field-life` (지우지 않았다. 스쿼시 머지라 개별 커밋 이력이 이 브랜치에만 남는다)
- PR: #689 — https://github.com/jjjh7401/AI-Lighting_Console/pull/689
- 머지 커밋 (main): `3f67e525db93c98cc13074179161dfd0932c45cd` (스쿼시, 2026-10-14T05:21:51Z)
- 머지한 헤드: `27c5c5b55034a4d08275581838135c03e28bc7a7` (`headRefOid` 와 같다. 머지 명령에 `--match-head-commit` 으로 고정했다)
- 머지 명령: `gh pr merge 689 --squash --match-head-commit 27c5c5b55034a4d08275581838135c03e28bc7a7`. `--admin` 과 `--delete-branch` 는 쓰지 않았다. 보호 우회는 없다.

## 1. 판정 읽기 (머지 전, 머지와 다른 호출)

명령: `gh run view 38515391465 --json conclusion,status,headSha,url`

출력:

```
{"conclusion":"success","headSha":"27c5c5b55034a4d08275581838135c03e28bc7a7","status":"completed","url":"https://github.com/jjjh7401/AI-Lighting_Console/actions/runs/38515391465"}
```

명령: `gh pr view 689 --json state,headRefOid,mergeable,mergeStateStatus,reviewDecision` (CI 완료 뒤 재조회)

출력:

```
{"headRefOid":"27c5c5b55034a4d08275581838135c03e28bc7a7","mergeStateStatus":"CLEAN","mergeable":"MERGEABLE","reviewDecision":"","state":"OPEN"}
```

첫 조회에서는 `mergeStateStatus` 와 `mergeable` 이 `UNKNOWN` 이었다. GitHub 가 CI 완료 뒤 상태를 다시 계산하는 중이었다. `CLEAN` 과 `MERGEABLE` 이 확인된 뒤에만 머지했다.

## 2. CI 체크 (verbatim, 머지 뒤 최종)

명령: `gh pr checks 689`

출력:

```
test	pass	8m27s	https://github.com/jjjh7401/AI-Lighting_Console/actions/runs/38515391465/job/115692918913
```

Run 38515391465 의 작업 단계는 `Python tests` 와 `UI tests` 를 포함해 모두 ✓ 였다. 주석 하나는 러너 이미지 이전 안내이고 실패가 아니다.

## 3. 머지 확인 (verbatim)

명령: `gh pr view 689 --json state,mergeCommit,mergedAt,headRefOid,url`

출력:

```
{"headRefOid":"27c5c5b55034a4d08275581838135c03e28bc7a7","mergeCommit":{"oid":"3f67e525db93c98cc13074179161dfd0932c45cd"},"mergedAt":"2026-10-14T05:21:51Z","state":"MERGED","url":"https://github.com/jjjh7401/AI-Lighting_Console/pull/689"}
```

명령: `git log --oneline -4 origin/main`

출력:

```
3f67e525 fix(t651): 재연결 뒤 빈 프리셋 표식 소실 — 풀 판독 기억을 저장소로 옮김 (#689)
23161f6d Merge pull request #690 from jjjh7401/WT-seconds-rest
ec1b238b docs(t653): 판정 — 표시만 바꾸고 저장값은 그대로 (카드 t653)
7ec8f3cd fix(t653): 전환 화면·장면 전환 머리글 초 표기 뒤의 0을 뗀다 — 저장값은 그대로 (카드 t653)
```

명령: `git show --stat --format='%h %s' 3f67e525`

출력:

```
3f67e525 fix(t651): 재연결 뒤 빈 프리셋 표식 소실 — 풀 판독 기억을 저장소로 옮김 (#689)

 .moai/reports/t651/fix.md                      | 163 +++++++++++++++
 .moai/reports/t651/scope.md                    | 205 +++++++++++++++++++
 server/tests/test_beat_grid_field_life_t651.py | 268 +++++++++++++++++++++++++
 server/web/session.py                          |  67 +++++--
 server/web/timeline_api.py                     |   7 +-
 5 files changed, 693 insertions(+), 17 deletions(-)
```

## 4. CI 가 덮은 범위

CI 는 PR 헤드 `27c5c5b5` 를 돌렸다. 머지 직전 main 에는 PR #690 이 먼저 들어와 있었다 (`23161f6d`). 명령 `git diff --name-only 58d3da69 23161f6d` 의 결과, #690 은 UI 파일 네 개와 `.moai/reports/t653/verdict.md` 만 바꿨다. 우리 파일과 겹치는 것이 없다. 따라서 CI 가 본 조합과 머지 결과 사이에 차이는 없다.

## 5. 남긴 것

- 보고: `.moai/reports/t651/scope.md`, `fix.md`, 이 파일.
- 후속 후보 (이 카드 밖, 손대지 않았다): 판독 시각을 화면에 그리는 카드; 보류 제안의 수명을 정하는 별도 카드 (감독 결정 1).
- 제안 (`_beat_grid_suggestions`) 과 `_beat_grid_empty_marks`, `app.py` 는 이 PR 에서 바뀌지 않았다.
