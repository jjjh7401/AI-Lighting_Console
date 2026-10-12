# t610 판정서 — LDBEAT `sync_commit_sha` 꼴 맞추기 + spec drift 우회 문서화

lane-2, 2026-10-12. 트리 `.claude/worktrees/t610`, 브랜치 `WT-ldbeat-sha-line`, 기준 origin/main `ba8279f0`.
코드 diff 0줄(문서 두 파일 + 이 증거 폴더).

## 1. 판정 — PASS

| 항목 | 결과 | 근거 |
|---|---|---|
| LDBEAT `sync_commit_sha` 를 줄 맨 앞 표준 꼴로 | 했다. 값 `48e51135` | `git log -1 48e51135` → `docs(SPEC-LDBEAT-001): sync-phase artifacts — … 상태 completed` |
| era 판정이 바로잡혔나 | V3R5 → **V3R6** | `count-before.txt` / `count-after.txt` 의 audit 줄 |
| 예측대로 drift 에서 빠지나 | 빠진다. 기록 67 → 66 | 같은 두 파일의 `missing` 줄. t494 §3 예측(`exp9`)과 일치 |
| 우회를 문서에 | `.moai/docs/lane-protocol.md` §2 끝에 적었다 | diff |
| 로컬 `main` ff | **하지 않았다** — 감독 판단 항목 | 아래 §3 |

## 2. 실측

명령(전후 같음):

```
moai spec drift --json --no-cache > drift-*.json
moai spec audit --json --include-grandfathered > audit-*.json
python3 .moai/reports/t610/count.py drift-*.json audit-*.json
```

고치기 전(`count-before.txt`): 기록 67, 디렉터리 72. 빠진 것은 COPILOT 넷 + LDDESIGN. LDBEAT 는 drift 에 `era-exempt` 로 있고 audit 은 `V3R5` + `Grandfathered`.

고친 뒤(`count-after.txt`): 기록 66. 빠진 목록에 **SPEC-LDBEAT-001 추가**. audit 은 LDBEAT·LDDESIGN 둘 다 `V3R6`.

로컬 `main` 은 여전히 `b661da2d`(2026-09-22)이고 주 체크아웃이 쥐고 있다(`git worktree list` 첫 줄 `b661da2d [main]`). 원인은 t494 판정 그대로다.

progress.md 를 실제로 읽는 앱 코드(`server/design/beat_grid_probes.py`, `|` 로 시작하는 M1 표 줄만 파싱)에 대한 시험: `uv run pytest -q server/tests/test_beat_grid_t537.py` → `32 passed`. 고친 줄은 표 줄이 아니라 영향이 없다.

`count.py` 린트: `uvx ruff check` → `All checks passed!`, `ruff format --check` → `1 file already formatted`.

## 3. 감독 판단 항목

- **주 체크아웃의 로컬 `main` fast-forward**(`git pull --ff-only`). 이걸 해야 LDDESIGN·LDBEAT 가 drift 에 돌아온다(예측, 실행 안 함). 공유 체크아웃 브랜치 상태 변경이라 레인 권한 밖이다. 당긴 뒤에도 새 커밋이 쌓이면 다시 낡는다.
- 도구 쪽 수정(`moai-adk`): 기록을 못 찾으면 버리지 말고 `unknown`/경고를 내기, 비교 브랜치는 `origin/<main>` 우선. 이 저장소 밖이다.

## 4. 안 잰 것

- ff 뒤 두 SPEC 이 실제로 돌아오는지(위 §3, 예측만).
- 서버 전체 시험 묶음 — 문서 변경이라 progress.md 를 읽는 시험 파일 하나만 돌렸다. 전체는 CI 몫.
- `Drifted: true` 건들의 원인(t494 §4와 같이 범위 밖).
