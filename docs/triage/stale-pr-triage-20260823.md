# 주인 없는 PR 5건 분류 — 2026-08-23 (카드 t21)

측정 트리: `.claude/worktrees/t21` · 기준 `origin/main` = `ed1dec1`.
커밋 산출물 없음 — 판단 재료만 만드는 카드였다. 시험 머지 2회는 `--no-commit` 으로 하고
`--abort` 했으며, 파일 대체 1회는 체크섬으로 복원을 확인했다.

결론: 다섯 중 넷이 측정으로 갈렸다. 감독 판단이 필요한 것은 #47 한 갈래뿐이었다.

| PR | 판정 | 갈린 근거 |
|---|---|---|
| #71 | 그대로 머지 | 드리프트 0 · 같은 날짜지만 다른 세션 문서 |
| #68 | 그대로 머지 | 순변경 13행 · 살아 있는 함정을 막고, 차단 작동을 실측 |
| #67 | 그대로 머지 | 시험 머지 후 전량 9,783 passed · 0 failed |
| #69 | 닫고 폐기 | 내용이 이미 main 에 있고 추월당함 · 머지하면 초록이 빨개짐 |
| #47 | 판단 이관 | 머지 비용은 0 · 내용 유효성은 측정 범위 밖 |

---

## [A] 머지 가능 여부 — 재측정이 필요하다

리드가 준 값은 `6296af3` 시점이었다. 다시 쟀다.

```
$ gh pr list --state open --json number,mergeable
#71 MERGEABLE · #69 CONFLICTING · #68 MERGEABLE · #67 MERGEABLE · #47 MERGEABLE
```

**첫 조회에서 셋이 `UNKNOWN` 으로 나왔다.** GitHub 은 머지 가능성을 지연 계산하고, 조회가
계산을 촉발한다. `UNKNOWN` 을 "머지 못 함"으로 읽으면 멀쩡한 PR 을 폐기하게 된다 —
재조회해서 확정된 값을 써야 한다.

## [B] 드리프트 — 그 파일을 main 이 그 뒤 몇 번 건드렸나

각 PR 의 merge-base 를 구하고 거기서 `origin/main` 까지 해당 파일만 로그를 셌다.

| PR | merge-base | 그 뒤 main 이 건드린 횟수 | 건드린 커밋 |
|---|---|---|---|
| #71 | `453846a` | **0** | — |
| #68 | `a593604` | 1 | `1b21c8d` STREAM-001 (#70) |
| #69 | `a593604` | 2 | `b2e22b0` LXSEQ (#72) · `1b21c8d` STREAM-001 (#70) |
| #67 | `a593604` | 1 | `1b21c8d` STREAM-001 (#70) |
| #47 | — | **0** | SPEC 디렉터리가 main 에 없음 · `docs/user-guide.html` 무변경 |

드리프트 계수는 리베이스 비용의 대리 지표다. 커밋 수가 아니라 **겹치는 파일**이 비용을
만든다 — [G] 가 그 예다.


## [C] #69 — 낡은 것이 아니라 되돌리는 PR이다

#69 는 `tools.py` 헝크 시작 행번호 트립와이어를 PR #66 시점 기준으로 갱신한다. 그런데 그
내용이 **이미 main 에 있다.**

```
$ git diff a593604..origin/main -- server/tests/test_songcue_bundle.py
+# 2026-08-20 re-walk 5 — SPEC-COPILOT-SPATIALMEM-001 (커밋 ff664a3, PR #66)이 ...
+    993,
-    1111,
```

#69 가 넣으려는 주석 블록이 한 글자도 다르지 않게 main 쪽에 들어와 있고, `993` 추가도
반영돼 있다. 그 위에 LXSEQ M3 재실측이 한 번 더 얹혀 있다(`971`·`1181` 추가 /
`1029`·`1129`·`1179` 제거).

주장으로 두지 않고 기계로 반증했다.

```
$ uv run pytest server/tests/test_songcue_bundle.py -q          # main 그대로
20 passed

$ git show pr/69:server/tests/test_songcue_bundle.py > <같은 경로>
$ uv run pytest server/tests/test_songcue_bundle.py -q          # #69 얹고
1 failed, 19 passed
FAILED test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state
```

복원은 초록이 아니라 체크섬으로 확인했다 — `f8bd1a8c...` 전후 동일.

즉 #69 는 뒤처진 PR 이 아니라 **되돌리는** PR 이다. 지금 머지하면 초록인 트립와이어를
빨갛게 만든다. 낡음과 역행은 다르고, 그 차이는 실행해 봐야 갈린다.


## [D] #68 — 검사가 diff 범위로 대상을 고르면 위반이 조용히 잠복한다

이 절이 이 문서에서 가장 오래 쓸모 있을 부분이다. 함정 자체는 #68 로 막혔지만, **모양이** 같은 자리가 이 저장소에 또 있을 수 있다.

### 무엇을 쟀나

```
$ uv run ruff format --check server/web/preview.py
Would reformat: server/web/preview.py          ← 이 파일은 포맷 위반 상태다

$ git diff --name-only 85a4b23..origin/main -- "*.py" | grep preview
(출력 없음)                                     ← 그런데 검사 대상 집합에 없다

$ git show origin/main:pyproject.toml | grep -n "force-exclude\|tool.ruff.format"
(출력 없음)                                     ← 그리고 막는 설정도 없다
```

### 기전

`server/web/preview.py` 는 PRECHK-001 / OVERLAP-001 이 **바이트 동일성**을 요구하는 핀
파일이다. 핀의 가치는 내용이 아니라 바이트가 안 변했다는 사실 자체에 있다. 그런데
저장소 전역 `ruff format` 은 그 안의 4행 컴프리헨션을 1행으로 접는다 — 의미는 같고
핀은 깨진다. 이미 두 번 깨졌고 두 번 원복됐다(`6d0b58c`, 그리고 #68).

핀을 지키는 검사는 `test_ruff_format_reports_no_change` 인데, 이 검사는 대상을
**diff 범위에서** 고른다.

```python
def _touched(self) -> list[str]:
    return [
        path
        for path in _git("diff", "--name-only", f"{_OVERLAP_BASE}..HEAD", "--", "*.py")
        ...
    ]
```

여기서 두 사실이 만난다.

1. `preview.py` 는 **지금 포맷 위반 상태다.**
2. `preview.py` 는 **지금 대상 집합 밖이다.**

그래서 검사는 초록이다. 초록인 이유가 "위반이 없어서"가 아니라 **"위반을 안 봐서"** 다.

### 왜 위험한가

누군가 `preview.py` 를 한 줄이라도 건드리는 순간 그 파일이 대상 집합에 들어온다. 검사가
빨개진다. 그리고 그 상황에서 다음 사람이 고르는 수정은 십중팔구 `ruff format` 이다 —
**그게 바로 핀을 깨는 동작이다.** 검사가 빨간불로 가리키는 해법이 검사가 지키려던 것을
부순다.

한 가지 더. 카드 t13 이 이 검사를 게이트 전면에 세웠다(main 이 이 검사 때문에 빨갰던
것을 고쳐 초록으로 만들고, PR 본문에 기준선으로 실었다). 그래서 이 함정은 **더 가까워진** 상태였다. 앞 카드가 뒤 카드의 도화선을 당겼다.

### #68 이 무엇을 막나

시험 머지 순변경은 `pyproject.toml | 13 insertions(+)` 뿐이다 — `preview.py` 쪽 절반은
main 에 이미 착지해 무동작이다. 남은 13행이 하는 일:

- `force-exclude = true` — 경로를 인자로 **명시해 넘겨도** 제외를 적용한다. 이 검사가
  파일 목록을 인자로 넘기기 때문에 이것이 없으면 제외가 무시된다.
- `[tool.ruff.format] exclude` — 포매터에서만 뺀다. lint 는 그대로 받는다.

작동을 실측했다.

```
적용 전:  $ uv run ruff format --check server/web/preview.py  → Would reformat
적용 후:  $ uv run ruff format --check server/web/preview.py  → exit=0, 출력 없음
```

### 계열 — 다음 사람이 알아볼 모양

이 함정의 일반형은 이렇다.

> 검사가 대상을 **diff 범위**(`<base>..HEAD`)에서 고르면, 범위 밖의 위반은 검사가 초록인
> 채로 잠복한다. 초록은 "위반 없음"이 아니라 "그 범위에서 위반 없음"이다.

찾는 법: 테스트가 `git diff --name-only` 로 대상을 만드는 자리를 훑고, 그 검사가 지키려는
불변식이 **범위 밖 파일에도 성립해야 하는지**를 묻는다. 성립해야 하는데 안 보고 있다면
같은 함정이다.

그리고 이번에 하나 더 확인됐다 — 이 검사는 `<base>..HEAD` 를 쓰므로 **워크트리 HEAD 와
머지 후 main HEAD 에서 대상 집합이 다르다.** "그 브랜치에서 초록"과 "머지 후 초록"은
다른 측정이다.


## [E] #67 — 텍스트 머지와 동작은 다른 물건이다

`git` 이 MERGEABLE 이라 해도 그것은 텍스트가 겹치지 않는다는 뜻이지 동작이 성립한다는
뜻이 아니다. `server/web/session.py` 는 그 사이 STREAM-001(#70)이 한 번 고쳤으므로
시험 머지 후 전량을 돌렸다.

```
$ git merge --no-commit --no-ff pr/67
Auto-merging server/web/session.py
Automatic merge went well; stopped before committing as requested

$ uv run pytest -q
9783 passed, 8 skipped, 1 warning in 151.93s
```

main 기준선 9,775 에 #67 이 가져온 8건이 더해진 값이다. 충돌 없음. 시험 머지는
`git merge --abort` 로 되돌렸고 `HEAD` 가 `ed1dec1` 로 돌아온 것을 확인했다.

`SPEC-COPILOT-INTENT-001` 디렉터리는 main 에 없었으므로 문서도 진짜 신규다.

## [F] #71 — 같은 날짜가 중복의 증거는 아니다

main 에 이미 `docs/handoff/2026-08-20-session-handoff.md` 가 있어 중복을 의심했다. 열어
보니 다른 세션이었다.

| | 제목 |
|---|---|
| main 의 것 | 2026-08-20 세션 핸드오프 — 응답 지연 개선 · 로컬 모델 평가 (174행) |
| #71 의 것 | 2026-08-20 세션 핸드오프 — 배치 인식 이펙트 · 의도 프레임 라우팅 |

파일명도 내용도 겹치지 않고, main 이 #71 의 파일을 건드린 적은 0회다. 추가일 뿐 충돌이
아니다.

## [G] #47 — 40커밋 뒤인데 리베이스 비용이 0이다

가장 낡고(40커밋 뒤) 가장 큰(+4,840) PR 이라 "닫고 내용만 새로 뽑는 게 쌀 수 있다"는
가정이 먼저 있었다. 측정이 그 가정을 뒤집었다.

```
$ git ls-tree -r --name-only origin/main -- .moai/specs/SPEC-COPILOT-BLOCKED16-001/
(출력 없음)                                     ← SPEC 디렉터리가 main 에 아예 없다

$ git log --oneline --since=2026-08-18 -- docs/user-guide.html
(출력 없음)                                     ← 유일한 비-SPEC 파일도 무변경
```

겹치는 파일이 하나도 없다. 커밋 수가 아니라 겹치는 파일이 비용을 만든다.

남은 것은 비용이 아니라 **내용 유효성**이다. 이 SPEC 의 `probe.md §2` 12행은 onPC 가
켜져 있을 때 재발화하는 판정이고, 지금 onPC 가 켜져 있다 — 즉 지금은 참·거짓이 실측으로
갈리는 상태다. 확인하지 않고 머지하면 미확인 판정 4,840행이 main 에 들어간다.

리드 판정: 12행을 먼저 재측정한 뒤 처분(카드 t12 의 읽기 전용 프로브에 얹어 비용 0).

---

## 이 카드가 커밋을 만들지 않은 이유

넷은 그대로 머지 가능해 리베이스도 재작업도 필요 없었고, 하나는 닫기만 하면 됐다. 손대면
오히려 헤드가 움직여 리드가 다시 재야 한다. 만들 산출물이 없다는 것 자체가 결론이었고,
이 문서는 그 판단의 근거를 남기기 위한 사후 기록이다.

