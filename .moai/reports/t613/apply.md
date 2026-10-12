# t613 — 상시 적재 규칙 축소 적용 결과

| 항목 | 내용 |
|---|---|
| 카드 | t613 (배차: SPEC-LDRHYTHM-001 세션) |
| 결정 | 감독 2026-10-12 「줄이고 재적용 도구 두기」 = §6 A안 + 재적용 스크립트 + 150k 점검 |
| 기준 트리 | worktree `t613`, 브랜치 `WT-rules-diet`, 기준 커밋 `1973c481` (= `origin/main` 시점) |
| 도구 | `.moai/tools/rules-diet/` (README 한 단락에 위치·실행법) |
| `moai update` | 실행하지 않음 (드라이런만) |

## 1. 주장 (Claim)

1. 상시 적재 16개 파일 합계가 **227,701 → 138,529자**로 줄었다 (한도 150,000, 여유 11,471). 제안서 권장 세트 예측치는 137.7k.
2. 조항은 삭제하지 않았다. 축소 전 원본의 비어 있지 않은 모든 줄이 (줄인 파일 + companion) 에 남아 있다 (누락 0줄).
3. `moai update` 뒤 `reapply.py` 한 번으로 줄인 판본과 local-only 2개가 복원되고 점검이 따라온다.

## 2. 증거 (Evidence)

### 2.1 전후 글자 수 (`check.py`, frontmatter·HTML 주석 제외)

| 파일 | 전 | 후 |
|---|---:|---:|
| core/agent-common-protocol.md | 26,501 | 18,444 |
| core/askuser-protocol.md | 29,710 | 20,673 |
| core/moai-constitution.md | 18,794 | 12,505 |
| core/verification-claim-integrity.md | 12,811 | 8,856 |
| workflow/context-window-management.md | 12,925 | 4,540 |
| workflow/cross-session-messaging.md | 16,579 | 7,540 |
| workflow/kanban-dispatch.md | 31,108 | 4,204 |
| workflow/main-checkout-branch-guard.md | 11,523 | 5,552 |
| workflow/session-handoff.md | 22,437 | 10,902 |
| (변경 없음 7개: CLAUDE.md, user.yaml, language.yaml, native-idiom, cache-aware, goal-directive, skill-routing) | | |
| **합계** | **227,701** | **138,529** |

실행 출력 (마지막 줄): `138529  TOTAL (limit 150000) -> OK, margin 11471`. 축소 전 `check.py`: `227701  TOTAL (limit 150000) -> FAIL, over by 77701`.

### 2.2 옮긴 조항 (헤딩 단위, 원문 그대로)

| 원 파일 | 옮긴 절 | 목적지 |
|---|---|---|
| moai-constitution | Opus 5/4.8 Prompt Philosophy, Lessons Protocol | `core/moai-constitution-deferred.md` |
| main-checkout-branch-guard | Mechanical Enforcement | `workflow/main-checkout-branch-guard-deferred.md` |
| verification-claim-integrity | §4 Cross-References, §5·§6 Worked Example | `core/verification-claim-integrity-deferred.md` |
| context-window-management | Graduated-Compaction, GLM-5.3, Reduction Ladder, Detection Heuristics, Cross-references | `workflow/context-window-management-deferred.md` |
| kanban-dispatch (리드) | The board, Entry into the board, Report milestones, Card classes, The dispatch cycle, Completion is read, Review lens selection, The `/clear` handoff, Cross-references | `.moai/docs/kanban-lead-protocol.md` (신설) |
| kanban-dispatch (레인) | Isolation is entered, Verification load, Integration into the release branch, Factory Mode | `.moai/docs/lane-protocol.md` § 부록 (proposal §5 ③안) |
| session-handoff | Cut-line Marker Spec, Field-by-Field Spec, Paste-Time Matrix, Auto-Injected Flow, Auto-Memory, Worktree-Anchored, Diet Constraints, V0 Abort Gate, Cross-references | `workflow/session-handoff-deferred.md` |
| cross-session-messaging | Availability, Where it sits, Addressing, An idle notice, Configuration surface, Cross-references | `workflow/cross-session-messaging-deferred.md` |
| askuser-protocol | Failure Mode, Root-Cause, Pollution Loop, Scope Note, Report Completeness, Preview-as-Report, Report-Promise, Blind Spot Pass, Why this matters, Correct Pattern, Unknowns Lens, Interview Example | `core/askuser-protocol-deferred.md` |
| agent-common-protocol | Hook Invocation Surface, Per-Spawn Model Injection, Super-Advisor, Verbatim batch, Attributable diff-check | `core/agent-common-protocol-deferred.md` |

원 파일에는 절마다 `> ↪ deferred → <목적지>: <제목>` 포인터 한 줄과, 파일당 stub 한 단락(핵심 [HARD] 한 줄 요약 포함)을 남겼다. Pre-Spawn·Pre-Edit Sync Check, Channel Monopoly, ToolSearch 선로드, 인코딩 지시문, 5 트리거·저장 의무·6블록 골격·ko 라벨 표는 원 파일에 그대로 남아 있다.

### 2.3 조항 보존 검증 (`verify.py` 실행 출력)

```
moai-constitution.md                       chars  18794 ->  12505  missing=  0  [HARD] orig= 10 now= 12
main-checkout-branch-guard.md              chars  11523 ->   5552  missing=  0  [HARD] orig=  2 now=  3
verification-claim-integrity.md            chars  12811 ->   8856  missing=  0  [HARD] orig=  3 now=  4
context-window-management.md               chars  12925 ->   4540  missing=  0  [HARD] orig=  5 now=  6
kanban-dispatch.md                         chars  31108 ->   4204  missing=  0  [HARD] orig= 25 now= 28
session-handoff.md                         chars  22437 ->  10902  missing=  0  [HARD] orig= 12 now= 13
cross-session-messaging.md                 chars  16579 ->   7540  missing=  0  [HARD] orig=  5 now=  8
askuser-protocol.md                        chars  29710 ->  20673  missing=  0  [HARD] orig=  9 now= 11
agent-common-protocol.md                   chars  26501 ->  18444  missing=  0  [HARD] orig= 15 now= 16
TOTAL missing lines: 0
```

`now` 가 `orig` 보다 큰 것은 stub 문구가 `[HARD]` 를 언급해서다 (원문 [HARD] 줄은 모두 어딘가에 있다).

### 2.4 고정 장치 근거 (재적용 도구를 둔 이유)

`moai update --help` 에 제외·고정 플래그 없음, 설정 키 없음, 문서상 제외 대상에 `.claude/rules/moai/` 없음, 드라이런에서 411개 managed cleanup + local-only 2개 삭제 예정 (지난 보고 보류 문서의 §2.1~2.4, 같은 출력). 그래서 기계적 고정 대신 재적용 도구로 해결했다.

### 2.5 재적용 시험

`reapply.py` 를 줄이기 전 트리에서 실행: 19개 파일 WRITE 후 점검 OK (위 §2.1). 줄인 뒤 재실행(`build.py` → `reapply.py`)은 9개만 WRITE, 부록 중복 없음 (`grep -c "부록 — kanban-dispatch.md" lane-protocol.md` → 1).

## 3. 기준선 귀속

- 전: `python3 .moai/tools/rules-diet/check.py` 227,701 (제안서의 측정값 227,701 과 일치). 후: 같은 명령 138,529. 같은 트리, 같은 계산식 (§2.2 of proposal).
- 원본 비교 기준: 커밋 `1973c4811de3ec4b06964bedd1b99584654179ac` (build.py 의 `BASE_REF`).

## 4. 새 세션 경고가 사라지는지 확인하는 방법

1. 이 PR 이 `main` 에 머지된 뒤, 주 체크아웃을 최신으로 맞추고(리드 몫) 새 세션을 연다.
2. 세션 시작 화면의 "instruction files … > 150.0k" 경고가 없어야 한다. 있으면 그 줄의 숫자를 `check.py` 의 TOTAL 과 비교한다.
3. 보조 점검: 저장소 루트에서 `python3 .moai/tools/rules-diet/check.py` 가 종료 코드 0.

## 5. 미검증 (Gaps)

- G1. Claude Code 내부 합계 계산식은 바이너리에서 직접 읽지 못했다. `check.py` 의 식이 보고값 227.7k 를 재현한다는 점만 확인했다 (가설). 실제 경고 소멸은 §4 의 새 세션에서만 확인된다.
- G2. `*-deferred.md` 의 `paths: "**/<원파일>.md"` 가 의도대로 "원 파일을 Read 할 때만" 적재되는지는 실행해 보지 않았다 (기존 `agent-common-protocol-reference.md` 와 같은 관례). 어긋나 상시 적재되면 합계가 다시 늘어난다. stub 은 명시 Read 를 지시하므로 적용 자체는 paths 동작에 의존하지 않는다.
- G3. 리드 세션이 SessionStart 주입 없이 stub 의 "Read kanban-lead-protocol.md" 를 지키는지는 시험하지 않았다. 지키지 않으면 리드가 디스패치 형식·판정 규칙을 놓칠 수 있다 (R2).
- G4. 출력 스타일 `moai.md` §8, `moai-easy.md` Banner 7 이 session-handoff.md 의 옮겨진 절을 가리키는지 점검하지 않았다 (R6). 가리키는 절은 사라진 것이 아니라 `session-handoff-deferred.md` 에 있다.
- G5. 서브에이전트가 `.claude/rules/**` 를 상시 적재받는지 확인하지 않았다 (제안서 G5 와 같다).
- G6. `.moai/docs/` 가 `moai update` 의 비관리 경로인지 실측하지 않았다. 지워져도 `reapply.py` 가 스냅샷에서 복원한다.
- G7. 실제 `moai update` 는 실행하지 않았다 (지시).

## 6. 잔여 위험 (Residual risk)

- R1. 스냅샷은 규칙 변경에 뒤처진다. 규칙을 고친 사람이 `snapshot/` 도 갱신하지 않으면 다음 `reapply.py` 가 변경을 되돌린다 (README 에 명시).
- R2. 명시 Read 를 하지 않은 세션은 옮겨진 절차를 적용하지 못한다. 가장 큰 것은 리드의 디스패치 형식과 핸드오프 필드 규칙이다.
- R3. `moai update` 가 템플릿에 새 조항을 추가했어도 `reapply.py` 는 스냅샷으로 덮어써 그 조항을 가린다. 업데이트 뒤 `git diff` 로 새 조항이 있는지 보고 스냅샷에 반영할 것.
- R4. `lane-protocol.md` 는 레인들이 갱신하는 문서다. 부록은 파일 끝에 붙어 있으나 다른 PR 과 끝부분이 겹치면 병합 충돌이 날 수 있다.
