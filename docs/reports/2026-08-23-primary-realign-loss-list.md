# 주 체크아웃 재정렬 — 손실 목록 (카드 t3, 2026-08-23)

> **조사만 한 문서다. 재정렬은 하지 않았고 브랜치 상태도 건드리지 않았다.**
> 주 체크아웃은 공유 트리라 다른 세션이 보고 있다. 처분은 리드가 정한다.

대상: `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` — 현재
`research/ma3-effects-phaser` = `ae8d494`. main(`c325e4a`)이 아니다.

---

## 요약 — 재정렬로 잃을 수 있는 것

| 항목 | 규모 | 판정 |
|---|---|---|
| 미머지 커밋 | **4개** | 내용은 대부분 main 이 앞섬 |
| 브랜치에만 있는 파일 | **22개 / 8,709줄** | 15개가 HTML 산출물 |
| 그중 테스트 2개 | 344줄 | **main 에서 19 실패 — 옛 계약** |
| 수정된 파일 | 80개 | 브랜치 고유분 **1,063줄**뿐 (main 이 7,416줄 앞섬) |
| 주 트리 미추적 | 19,600개 | **사실상 전부 생성물·무시 대상** |
| 그중 순수 미추적 문서 | **1개** | `handoff/2026-08-18-…-handoff.md` |
| checkout 을 막는 파일 | **24개** | `src/Lighting_Designer/**` |
| 그 트리에 붙은 프로세스 | **있음** | `codex` · `mcp-serve` · Chrome |

---

## 1. 미머지 커밋 — 4개 (직접 셌다)

```
git rev-list --count --left-right origin/main...research/ma3-effects-phaser
  → 49  4      (왼쪽=main만, 오른쪽=브랜치만)
```

| 커밋 | 내용 | 규모 |
|---|---|---|
| `ae8d494` | 트립와이어 재실측 부기 | 3파일 |
| `9469b65` | main 을 브랜치로 머지 | — |
| `819aa6f` | **WIP 보존 스냅숏** — 응답기·QuestionCard·prechk | 45파일 · +9,646 |
| `2566d68` | 하네스 동기화 | 293파일 |

메모리가 적은 "4개"와 일치한다. 다만 **커밋 개수는 손실의 척도가 아니다** — 아래
트리 대조가 실제 차이다.

## 2. 브랜치에만 있는 22개 — 8,709줄

| 종류 | 개수 | 처분 근거 |
|---|---|---|
| `src/artifacts/*.html` | 15 | 발행 산출물. 커리큘럼 덱·신라버스가 대부분(2,770줄) |
| 테스트 | 2 | **아래 §3** |
| 런타임 로그 | 2 | `usage-log.jsonl` · `lessons-inbox.jsonl` — 카드 t16 이 이미 "병렬 세션 충돌"로 지목 |
| 백업 | 2 | `.moai/backup/agency-2026-08-16…` |
| `manager-kanban.md` | 1 | **오늘 t19 가 의도적으로 폐기했다.** 손실이 아니다 |

## 3. 테스트 2개 — main 에서 돌지 않는다

`test_lua_responder_props.py` · `test_spatial_batch_read.py` (합 344줄).

**기능은 이미 main 에 있다**:

```
git grep -c SPATIAL_FIXTURE_PROPERTIES origin/main -- server/orchestrator/tools.py  → 7
git grep -c SPATIAL_PROPERTY_QUERY_CAP  origin/main -- server/orchestrator/tools.py  → 4
git grep -c "class ResponderHarness"    origin/main -- server/tests/lua_mock_env.py  → 1
git grep -c props origin/main -- console/lua/copilot_responder.lua                   → 21
```

그런데 두 파일을 main 트리에 얹어 돌리니 **19 실패 · 4 통과**. 원인은 응답 형태 변경이다:

```
assert "fixtures" in reply
  → main 은 {"source": "patch3d", "partial_fixtures": [], "unreadable": [...]} 를 준다
```

즉 **브랜치 테스트가 옛 계약을 담고 있다.** 되살리면 19개가 빨개진다.
main 쪽에는 같은 심볼을 덮는 `test_spatial_context.py` · `test_truncate_disclosure.py` 와
`test_lua_responder_payload_budget.py` 가 있다.

미검증: main 의 그 테스트들이 브랜치 테스트와 **동등한 커버리지**인지는 대조하지
않았다. 같은 심볼을 참조한다는 것까지만 확인했다.

## 4. 수정된 80개 — 브랜치 고유분은 1,063줄

```
git diff --diff-filter=M --stat origin/main research/ma3-effects-phaser
  → 80 files changed, 1,063 insertions(+), 7,416 deletions(-)
```

main 방향으로 7,416줄이 더 있다. 브랜치가 앞선 1,063줄이 무엇인지는 파일별로
가르지 않았다 — **미검증**이며, 리드가 필요하다 하면 잰다.

## 5. 주 트리 미추적 19,600개 — 거의 전부 생성물

| 위치 | 개수 | 성격 |
|---|---|---|
| `src-tauri/` | 18,077 | Rust 빌드 산출물 |
| `.moai/` | 1,397 | state · telemetry · backup (무시 대상) |
| `.claude/` | 54 | **전부 gitignore** — `agent-memory/` 51(`.gitignore:179`) · `settings.local.json`(174) · design-tokens(187) |
| `server/` | 39 | `audit_logs/`(244) · `paperwork_output/`(245) — 둘 다 무시 |
| `src/` | 26 | `Lighting_Designer/` — **오늘 t17 이 main 으로 옮긴 것의 원본 사본** |
| 기타 | 7 | `.DS_Store` 4 · `.env`(126) · `.coverage`(59) · **handoff 1** |

### 유일하게 느슨한 문서 1개

`handoff/2026-08-18-patch-spatial-responder16-handoff.md`

- `git check-ignore` **무출력** → 무시 대상이 아니다. 순수 미추적이다
- main 의 `handoff/` 에 8개가 있는데 **이것은 없다**
- 즉 이 파일은 디스크에만 있다. `git clean` 계열이 지운다

`.claude/agent-memory/` 51개(에이전트 교훈)는 **의도적으로 무시**되는 것이라
재정렬로는 안 지워진다. 다만 `git clean -fdx` 는 지운다.

## 6. 평범한 checkout 을 막는 24개

`src/Lighting_Designer/**` 24개가 **주 트리엔 미추적으로 있고 main 은 추적**한다.
이 상태에서 `git switch main` 은 «untracked working tree files would be overwritten»
으로 거부된다. 개수가 t17 이 옮긴 24개와 정확히 일치한다.

주의: 주 트리의 사본은 **옛 판**이다(t20 이 고친 하드코딩 경로가 그대로 있다).
main 판으로 덮이는 것은 손실이 아니라 갱신이다.

## 7. 그 트리에 붙은 프로세스 — 있다

```
lsof -d cwd | awk ... → codex(96204) · mcp-serve(94088) · Chrome 헬퍼 7
```

`moai session list --json` 은 `[]` 를 답했다. **레지스트리를 믿으면 안 된다** —
프로세스는 실제로 붙어 있다. 재정렬은 최소한 codex 세션의 발밑을 뺀다.

---

## 측정 자기 정정 1건

처음에 checkout 차단 파일을 **4개**로 셌다. 원인은 git 이 비ASCII 경로를 따옴표로
이스케이프해(`core.quotePath`) 한글 디렉터리 경로가 `find` 출력과 대조되지 않은 것이다.
`git -c core.quotePath=false` 로 다시 재어 **24개**를 얻었다. 4개는 ASCII 경로만
우연히 맞은 값이었다.

## 조사 중 일어난 부수 효과 1건

`moai session list --json` 이 **머지된 워크트리 t13 · t19 · t21 을 자동 제거**했다
(PR-merge cleanup). 셋 다 머지 완료분이라 손실은 없다. t14 는 세션이 잠그고 있어
남았다. 의도한 명령의 문서화되지 않은 부수 효과이므로 기록한다.

## 이 문서가 답하지 않는 것

- 수정된 80개의 브랜치 고유 1,063줄이 무엇인지 (파일별 미분류)
- main 테스트가 브랜치 테스트와 동등한 커버리지인지
- `src/artifacts/*.html` 15개가 다른 곳에 발행돼 있는지
- `819aa6f` 가 "보존"한 원래 미커밋 작업 중 아직 어디에도 없는 것이 있는지
