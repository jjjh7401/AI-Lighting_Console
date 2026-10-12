# t613 — 상시 적재 규칙 16개: 측정과 축소 제안

| 항목 | 내용 |
|---|---|
| 카드 | t613 (배차: SPEC-LDRHYTHM-001 세션) |
| 측정 | 레인 lane-2, 세션 `71a3ded6-e7cd-4778-8f18-05515165aee6` |
| 기준 트리 | 주 체크아웃 HEAD `65db4d34` (2026-09-16). 16개 파일 `git status` clean |
| 변경 | 없음. 규칙·설정 미수정, 커밋 없음. 이 폴더의 증거 파일 3개만 신규 (미추적) |
| 측정 시각 | 2026-10-12 19:52–20:07 KST |

## 1. 주장 (Claim)

1. 상시 적재 instruction 파일은 16개, 주입 기준 **227,701자**. 한도 150.0k를 **77,701자(전체의 34.1%)** 넘는다.
2. 16개 구성: CLAUDE.md 1 + `@import` 2 (user.yaml, language.yaml) + `paths:` 조건이 없는 규칙 13.
3. 항목 하나만 줄여서는 한도를 못 맞춘다. 제안한 6단계를 모두 적용하면 **약 137.7k자 (여유 12.3k)**. 최소 세트(4단계까지)는 145.3k (여유 4.7k)이지만 스텁이 커지면 넘는다 (§4).
4. 이 파일들은 moai 템플릿 산출물이다. `moai update`를 dry-run으로 보면 `.claude/rules/moai/` 관리 경로는 지운 뒤 템플릿으로 재배포된다. **정책을 정하기 전에는 어떤 축소도 다음 동기화에서 되돌아가거나 파일이 지워진다** (§2.5, §5).
5. `paths:` 지연 적재는 해당 파일을 읽는 순간에만 동작한다. 글롭이 넓으면 절감이 줄어든다 (§2.3).

## 2. 증거 (Evidence)

### 2.1 파일별 크기와 적재 근거

원문 글자 수(`len`, 코드포인트). 템플릿 일치는 30자 이상 줄을 바이너리 내장본과 대조한 글자 기준 비율.

| 파일 | 원문 글자 | `paths:` | 템플릿 일치 | 적재 근거 |
|---|---:|---|---|---|
| CLAUDE.md | 20,347 | 없음 | 100% | 루트 지침 |
| .moai/config/sections/user.yaml | 204 | — | — | CLAUDE.md `@import` |
| .moai/config/sections/language.yaml | 1,257 | — | — | CLAUDE.md `@import` |
| core/agent-common-protocol.md | 26,855 | 없음 (`description`만) | 100% | 규칙, 조건 없음 |
| core/askuser-protocol.md | 29,875 | 없음 | **52.4%** (로컬 편집) | 규칙, 조건 없음 |
| core/moai-constitution.md | 18,876 | 없음 | 100% | 규칙, 조건 없음 |
| core/native-idiom-and-register.md | 4,722 | 없음 | 100% | 규칙, 조건 없음 |
| core/verification-claim-integrity.md | 12,811 | 없음 | 100% | 규칙, 조건 없음 |
| workflow/cache-aware-execution.md | 6,508 | 없음 | 100% | 규칙, 조건 없음 |
| workflow/context-window-management.md | 12,925 | 없음 | 100% | 규칙, 조건 없음 |
| workflow/cross-session-messaging.md | 16,579 | 없음 | 100% | 규칙, 조건 없음 |
| workflow/goal-directive.md | 6,552 | 없음 | 100% | 규칙, 조건 없음 |
| workflow/kanban-dispatch.md | 31,108 | 없음 | **81.5%** (로컬 편집) | 규칙, 조건 없음 |
| workflow/main-checkout-branch-guard.md | 11,523 | 없음 | 100% | 규칙, 조건 없음 |
| workflow/session-handoff.md | 22,899 | 없음 | **51.6%** (로컬 편집) | 규칙, 조건 없음 |
| workflow/skill-routing.md | 5,775 | 없음 | 100% | 규칙, 조건 없음 |
| **합계** | **228,816** | | | |

발견 명령: `.claude/rules/**/*.md` frontmatter 스캔 → 규칙 76개, `paths:` 없음 13개, `paths:` 있음 63개. `CLAUDE.md`의 `^@` 줄 2개가 user.yaml, language.yaml이다.

### 2.2 한도 값 재현

- 원문 228,816 → frontmatter 제외 −354 (agent-common 189 + askuser 165) → HTML 주석 제외 −761 → **227,701 = 227.7k**. 보고값과 일치한다.
- 이 계산 방식은 가설이다. Claude Code 내부 계산식은 바이너리에서 직접 읽히지 않는다. 대신 경고 구조 문자열 (`instruction files`, `totalChars`, `totalLimitChars`, `/memory to free up context`)이 Claude Code 2.1.296 바이너리 안에 있다. 경고의 주체는 Claude Code다.
- 파일 집합 확인: 세션 71a3ded6 트레이스에 `InstructionsLoaded` 이벤트가 19:52:59.507–.536 사이 16건 있다 (세션 시작 시점).

### 2.3 지연 적재 확인

트레이스에 시작 시점 16건 말고 2건씩 두 번 더 있다. 본문에 붙은 시스템 알림과 시각으로 대응시켰다.

- 19:58:56 — `.claude/settings.json` 읽기 직후 → hooks-system.md, settings-management.md
- 20:00:52 — `handle-instructions-loaded.sh` 읽기 직후 → agent-hooks.md, hook-independence.md
- (트레이스 대조 안 함) `measure.py` 작성 직후 → python.md, mx-tag-protocol.md, karpathy-quickref.md (3건)

### 2.4 템플릿 출처

- `/Users/studiox/.local/bin/moai` (35,970,082 bytes) 안에 규칙 본문이 그대로 들어 있다. 문구 확인 횟수: "Lessons are additive…" 1, "The delegation channel is the queue" 3, "Non-ASCII Tool-Call Encoding" 5, "Mechanical Enforcement (v1.2.0)" 1, "Hook Invocation Surface" 13.
- git 이력: 대부분 `f30ab4c6` (하네스 동기화, 2026-08-17)과 `65db4d34` (3.1.2 템플릿 "선별 채택", 2026-09-16)에서 왔다. 커밋 제목이 선별 채택이라고 밝힌다. 템플릿과 다른 로컬 편집이 있다는 뜻이다 (§2.1 표 마지막 열).

### 2.5 moai update 드라이런 (파일 미변경)

명령: `moai update --templates-only --dry-run </dev/null` (moai-adk 3.1.2). 실행 전후 `git status` 지문 `0ce6414d58d1`이 같았다.

```
·  [dry-run] managed cleanup  415 files removed under managed paths (410 re-deployed from templates, 5 not restored)
!  [dry-run] not restored: .claude/rules/moai/workflow/session-handoff-fields.md  deleted by the real run — local-only file
!  [dry-run] not restored: .claude/rules/moai/workflow/worktree-integration-detail.md  deleted by the real run — local-only file
·  [dry-run] .moai/config removed entirely  contents backed up and restored via 3-way merge by the Backup/Restore steps
```

나머지 3건은 스킬 `references/.moai/state/*.json` 런타임 파일이다.

해석: 실제 실행하면 `.claude/rules/moai/`를 지운 뒤 템플릿으로 다시 깐다. 그래서 로컬 편집은 되돌아간다. 템플릿에 없는 로컬 파일 2개는 삭제된다. 두 파일은 git 추적 중이라 git에서 복구할 수 있다 (`a3f441ba`, t345 분할 커밋).

### 2.6 기준선 귀속

- 워크트리 전체에서 16개 합은 228,816으로 같다. 예외는 `t415-verify` 하나 (220,726)다.
- 최근 커밋 60개 중 최신 `65db4d34`가 228,816이다. 227.7k와 정확히 맞는 커밋 상태는 없다. 차이는 계산 방식에서 나온다 (§2.2).

## 3. 파일별 축소 제안

추정치다. 근거는 `measure.py` 출력 (`measure-output.txt`). 스텁 크기는 가정치다. 순감소 = 이동 글자 − 스텁.

### A군: 이동만 하면 됨 (로더 변경 없음)

| 파일 | 이동 대상 (헤딩) | 이동 | 스텁 | 순감소 | 빠지면 안 보이는 것 (남기는 것) |
|---|---|---:|---:|---:|---|
| moai-constitution.md | Opus 5/4.8 절 → `agent-authoring.md` (이미 있음, `paths: **/.claude/agents/**`). Lessons 세부 → 동반 문서 | 5,815 | 600 | 5,215 | Lessons 자동 포착 절차. 남김: Agent Core Behaviors 6개, Lessons 핵심 규칙 |
| main-checkout-branch-guard.md | Mechanical Enforcement (Go 훅 구현 설명) → 동반 문서. `paths: **/internal/hook/**`는 이 저장소에 `internal/`이 없어 여기선 사실상 불리지 않는다 | 6,410 | 650 | 5,760 | 남김: 금지 표, 절차, Staleness 규칙, 차단 메시지(`BRANCH_GUARD_VIOLATION`) 해석 한 단락 |
| verification-claim-integrity.md | §4 상호참조, §5·§6 사례 → 동반 문서 | 4,194 | 500 | 3,694 | 사례의 맥락만. 남김: §1 불변식, §2 기준선, §3 5항목 형식 |
| context-window-management.md | 압축 계층, Reduction Ladder, Detection Heuristics (`paths: **/.moai/state/context-usage.json`), GLM-5.3 절, 상호참조 | 9,095 | 600 | 8,495 | 감소 수단 우선순위, 상태 파일이 없을 때의 추정. 남김: 모델별 임계표, 사용자·오케스트레이터 의무, 상태 파일 우선 원칙 |

### B군: 로딩 경로 변경 필요

| 파일 | 이동 대상 | 이동 | 스텁 | 순감소 | 빠지면 안 보이는 것 (남기는 것) |
|---|---|---:|---:|---:|---|
| kanban-dispatch.md | 리드 조항 15,220 (board, Entry, Report milestones, Card classes, dispatch cycle, Completion is read, Review lens, /clear) + 레인 조항 11,914 (Isolation, Verification load, Integration, Factory Mode) + 상호참조 844 | 27,978 | 1,500 | 26,478 | 역할 세션이 로딩하지 않으면 디스패치 형식과 판정 규칙이 한 줄 요약만 남는다. 남김: Scope, Boundaries, HARD 한 줄 요약 6개 |
| session-handoff.md | Canonical Format 7,171 (6블록 세부, 필드, 컷라인, ko 라벨표 포함), Auto-Injected 1,742, Auto-Memory 2,001, Paste-Time 629, Worktree 721, Diet 902, 상호참조 2,463 | 15,629 | 1,800 | 13,829 | 필드 규칙, 자동 주입 흐름, 메모리 저장 절차. 남김: 트리거 5개, 저장 의무, 출력 표면, 6블록 골격, ko 라벨, invariant |
| cross-session-messaging.md | 가용성, 위치, 주소·답장, 설정 표, 상호참조, 채널 설명 일부, 유휴 알림 일부 | 10,255 | 700 | 9,555 | 설정 키 의미와 가용성 조건. 실패가 조용하므로 진단할 때는 명시 Read가 필요하다. 남김: 메시지는 사용자 동의가 아니라는 원칙, HARD 규칙 전부, 동시성 연동, 안티패턴 |
| askuser-protocol.md | 인코딩 실패 원인 절, 보고 게이트 세부 3개, Blind Spot Pass, Free-form 세부, Unknowns 렌즈, Socratic 예시 | 10,390 | 1,000 | 9,390 | 실패 원인 설명, 보고 완전성 세부 기준. 남김: Channel Monopoly, ToolSearch 절차, Frozen 문단, 인코딩 지시문과 사전 점검 |
| agent-common-protocol.md | 훅 표 세부, Pre-Spawn 세부, Super-Advisor 세부, Per-Spawn 세부, Verbatim batch, Attributable diff-check | 8,008 | 400 | 7,608 | 검증 배치 명령 세부. 남김: 훅 결과 번역 3단계, 서브에이전트 경계(Frozen), Pre-Edit 동기화 검사 |

## 4. 단계별 합계 (stub 가정치 기준)

| 누적 단계 | 순감소 | 결과 | 한도 대비 |
|---|---:|---:|---|
| A군 | 23,164 | 204,537 | 초과 54,537 |
| + kanban | 49,642 | 178,059 | 초과 28,059 |
| + session-handoff | 63,471 | 164,230 | 초과 14,230 |
| + cross-session | 73,026 | 154,675 | 초과 4,675 |
| + askuser (최소 세트) | 82,416 | 145,285 | 여유 4,715 |
| + agent-common (**권장 세트**) | 90,024 | **137,677** | 여유 12,323 |

민감도: 스텁이 가정치의 2배가 되면 권장 세트는 145,427 (여유 4,573), 최소 세트는 152,635 (초과 2,635). **권장 세트를 제안한다.**

kanban 분할 (헤딩 기준): 리드 15,220, 레인 11,914, 공통 844.

## 5. 적용 전에 리드가 정할 것

1. **동기화 정책 (가장 먼저)**
   - (a) 정본 이전: MoAI-ADK 템플릿에 같은 축소를 반영하고 `moai update`로 전파한다. 템플릿 원본은 이 저장소에 없다 (`internal/` 부재). 위치 확인이 필요하다. 로컬 편집 3파일의 정정도 함께 올려야 한다.
   - (b) 로컬 고정: 이 저장소에서 `moai update`를 실행하지 않는 전제로 축소를 적용한다. 템플릿 개선의 유입은 멈춘다.
   - 어느 쪽도 정하지 않고 축소하면, 다음 동기화에서 원상 복구되고 로컬 전용 파일 2개가 삭제된다.
2. **목표 수준**: 최소 세트 145.3k 또는 권장 세트 137.7k. 권장.
3. **kanban 로딩 방식**
   - 레인 조항은 `.moai/docs/lane-protocol.md`에 합친다. 배차서가 이 파일을 레인이 직접 읽도록 이미 지시하고 있다.
   - 리드 조항은 신설 문서로 빼고 로딩을 SessionStart 주입 (`hookSpecificOutput.additionalContext`, hooks-system.md 기재) 또는 런처 지시문의 명시 Read로 한다. 이 세션 시작 컨텍스트에 역할(`Factory Mode … lane-2`)이 표시된 것은 확인했다. 주입 경로 자체는 미확인이다.

## 6. 미검증 (Gaps)

- G1. Claude Code 내부 계산식을 직접 확인하지 못했다. §2.2의 재현은 가설과 일치한다는 뜻이다.
- G2. `InstructionsLoaded` 트레이스에는 파일 목록이 없다. 16개 파일명은 규칙 구조(`paths:` 없음, `@import`)에서 도출했다. 개수만 이벤트로 확인했다.
- G3. dry-run은 요약만 출력한다. 16개 각각의 재배포 여부는 개별 확인하지 않았다. 간접 근거는 줄 대조와 local-only 열거다.
- G4. 템플릿 원본 저장소와 버전 관계를 확인하지 못했다. 바이너리 내장본이 설치 버전 3.1.2와 같다고 가정했다.
- G5. 서브에이전트가 `.claude/rules/**`를 상시 적재받는지 확인하지 않았다. agent-common-protocol 주석의 주장만 있다.
- G6. 시스템 프롬프트 상주분 중 스킬 목록과 MCP 도구 목록은 측정하지 않았다. 측정한 상시 항목은 출력 스타일 moai-easy.md 28,811자, MEMORY.md 16,000자다.
- G7. 역할별 로딩(SessionStart 주입, 명시 Read)의 실제 동작은 확인하지 않았다.
- G8. 중복 제거 후보는 주제 수준만 봤고 측정하지 않았다. 예: CLAUDE.md §14 (1,368) ↔ constitution Parallel Execution (1,617) ↔ agent-common Parallel Execution (9,170). CLAUDE.md §8 ↔ askuser Channel Monopoly.
- G9. lane-protocol.md와 kanban 레인 조항의 중복은 키워드 빈도만 비교했다 (ExitWorktree 6 / 2, WT- 8 / 2, release/ 2 / 0). 본문 대조는 하지 않았다.
- G10. `.moai/docs/`가 비관리 경로라는 판단은 dry-run이 열거하지 않았다는 점에 근거한 추정이다.
- G11. 스텁 크기는 가정치 (500–1,800자)다. 실제 편집 후 `measure.py`를 다시 돌려야 한다.

## 7. 잔여 위험 (Residual risk)

- R1. 스텁이 HARD 문장이나 ko 라벨을 빠뜨리면 역할과 출력이 틀어진다. 스텁에 HARD 문장과 ko 라벨을 유지해야 한다.
- R2. 명시 Read를 하지 않으면 이동된 절차가 적용되지 않는다. 핸드오프 형식과 디스패치 형식이 가장 크다.
- R3. 글롭 과매칭. 이번 세션에서 `.py` 파일을 하나 쓰자 규칙 3개가 더 올라왔다. 글롭을 좁게 잡아야 한다.
- R4. 새 스킬이나 문서를 추가하면 스킬 목록이 늘어난다 (`skillListingBudgetFraction` 0.02).
- R5. 로컬 정정 기록이 유실될 수 있다. askuser 52%, session-handoff 52%, kanban 82%가 템플릿과 다르다.
- R6. 이동 후 참조가 깨질 수 있다. 출력 스타일 moai.md §8과 moai-easy.md (Banner 7)가 session-handoff.md를 가리킨다. 갱신이 필요하다 (미측정).

## 8. 자기 점검

- 가장 약한 추정은 partial keep 값 (459, 1,600, 700, 340, 700, 400, 900)이다. 판단으로 넣은 값이다.
- 스텁 가정치에 민감하다. 최소 세트는 스텁이 2배면 한도를 넘는다. 그래서 권장 세트를 권한다.
- 헤딩 단위 이동은 문단 경계와 어긋날 수 있다. parser coverage 1.000은 제목 분할이 본문을 빠짐없이 덮는다는 뜻이지, 이동 경계가 의미 단위와 맞는다는 뜻은 아니다.

## 9. 재현

- `python3 .moai/reports/t613/measure.py` (읽기 전용). 출력은 `.moai/reports/t613/measure-output.txt`.
- 줄 대조, 트레이스 확인, dry-run은 §2에 적은 명령 그대로다. 실제 `moai update`는 실행하지 않았다.

## 10. 후속 카드 후보 (리드가 발급)

- F1. 동기화 정책 결정 (§5.1).
- F2. 로컬 전용 companion 2개 (`session-handoff-fields.md`, `worktree-integration-detail.md`)를 템플릿에 올리거나 보존 목록에 넣는다. 현재 `moai update` 삭제 대상이다.
- F3. 스킬 `moai-domain-html-report/references/.moai/state/*.json` 3개의 위치를 정리한다. 템플릿 밖 런타임 상태가 스킬 폴더 안에 있다.
- F4. 중복 제거 후보 측정 (G8).
