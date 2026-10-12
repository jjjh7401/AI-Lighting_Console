# t613 — 적용 보류 보고 (고정 장치 실측 결과)

| 항목 | 내용 |
|---|---|
| 카드 | t613 (배차: SPEC-LDRHYTHM-001 세션, 감독 결정 2026-10-12: 동기화=로컬 고정, 목표=권장 137.7k) |
| 상태 | **적용 보류.** 규칙·설정 수정 0건. 이 파일만 신규 |
| 기준 트리 | worktree `t613`, 브랜치 `WT-rules-diet`, `origin/main` 과 `0 0` (fetch 직후) |
| 측정일 | 2026-10-12 |

## 1. 주장 (Claim)

`moai update` 가 `.claude/rules/moai/**` 의 로컬 편집을 덮어쓰지 못하게 막는 파일 단위 제외·고정 장치는, 설치된 moai-adk 3.1.2 에서 **발견되지 않았다.** 배차 지시 ① 의 조건("없으면 적용하지 말고 보고")에 해당하므로 6단계 세트를 적용하지 않았다.

## 2. 증거 (Evidence)

### 2.1 `moai update --help` 플래그 전체 (발췌)

```
--binary --check -c/--config --dry-run --force --help --no-hooks --profile
--restore --shell-env --templates-only --verbose --version --yes
```
경로·파일을 제외하거나 고정하는 플래그(`--exclude`, `--keep`, `--pin` 등)는 없다.

### 2.2 설정 키 검색

`grep -rniE "protected|preserve|pinned|exclude|skip_paths|user_modified|customi[sz]" .moai/config/sections/*.yaml` →
`mx.yaml` 의 MX 분석 제외 글롭, `quality.yaml` 의 `preserve_before_improve`(DDD 모드 설정) 등만 나왔다. `moai update` 동기화 대상을 제외하는 키는 없다.

### 2.3 문서가 말하는 제외 목록

- `.claude/rules/moai/development/agent-authoring.md:32` — 제외: `.claude/agents/harness/`, `.claude/agents/local/`
- `.claude/rules/moai/development/skill-authoring.md:365` — 제외: `hns-*`, `harness-*`, `my-harness-*` 스킬
- `.claude/rules/moai/workflow/dynamic-workflows.md:116` — 제외: `hns-*`, `harness-*` 워크플로
- `.claude/rules/moai/development/skill-authoring.md:364` — `moai-*` 는 템플릿 배포물이고 직접 수정하면 다음 `moai update` 가 덮어쓴다
- `dynamic-workflows.md:115` — MoAI 배포 워크플로 스크립트도 덮어쓴다

`.claude/rules/moai/` 는 제외 목록에 없다.

### 2.4 드라이런 (파일 미변경, 명령: `moai update --templates-only --dry-run --verbose </dev/null`)

```
·  [dry-run] managed cleanup  411 files removed under managed paths (409 re-deployed from templates, 2 not restored)
!  [dry-run] not restored: .claude/rules/moai/workflow/session-handoff-fields.md  deleted by the real run — local-only file
!  [dry-run] not restored: .claude/rules/moai/workflow/worktree-integration-detail.md  deleted by the real run — local-only file
·  [dry-run] .moai/config removed entirely  contents backed up and restored via 3-way merge by the Backup/Restore steps
```

규칙 파일 경로는 managed cleanup → 템플릿 재배포 대상이다. 3-way merge 로 복원되는 것은 `.moai/config` 뿐이다.

## 3. 기준선 귀속 (Baseline)

- moai-adk 3.1.2 (`moai update` 출력의 `Current version`), 이번 실행, 이 트리.

## 4. 미검증 (Gaps)

- G1. 바이너리 소스를 읽지 않았다. 숨은 설정 키·환경변수가 있을 수 있다 (도움말·문서·설정에서는 못 찾았다는 뜻).
- G2. `.claude/rules/` 아래 managed 경로 밖(예: `.claude/rules/local/`)에 둔 파일이 `moai update` 에 살아남는지는 **측정하지 않았다.** 드라이런 출력은 "managed paths" 의 범위를 열거하지 않는다.
- G3. 실제 `moai update` 는 실행하지 않았다 (지시 사항).
- G4. 배차의 "동기화=로컬 고정" 은 "moai update 를 실행하지 않는다" 는 운영 정책으로 읽었다. 이 정책이 기계적 장치 없이 충분한지는 리드·감독 판단이다.

## 5. 잔여 위험 (Residual risk)

- R1. 장치 없이 축소하면 누군가 `moai update` 를 한 번 돌리는 순간 §3 의 모든 축소가 되돌아가고, 로컬 전용 companion 2개는 삭제된다 (git 복구 가능: `a3f441ba`).
- R2. `.moai/config` 만 3-way merge 되므로 설정 쪽에 고정 표지를 두는 방식은 규칙 파일에는 효과가 없다.

## 6. 선택지 (리드가 정함)

| 안 | 내용 | 비고 |
|---|---|---|
| A | 정책 고정: 축소를 적용하고 이 저장소에서 `moai update` 를 금지한다. 되돌아감에 대비해 `session-handoff-fields.md`·`worktree-integration-detail.md` 는 git 추적 유지 | 기계적 보호 없음. 실수 1회로 되돌아간다 |
| B | G2 를 먼저 실측: 상세 companion 을 managed 경로 밖에 두면 살아남는지 확인한 뒤, stub 만 managed 경로에 남긴다 | 측정 후 결정. 새 카드 후보 |
| C | 템플릿 쪽 정본 이전 (proposal §5.1(a)) | 원본 저장소 위치 확인 필요 |
