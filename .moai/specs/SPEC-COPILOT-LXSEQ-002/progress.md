# SPEC-COPILOT-LXSEQ-002 — 진행 기록 (progress)

칸반 카드 t18. 워크트리 `.claude/worktrees/t18`, 브랜치 `WT-lxseq-group-plan`.

---

## 0. plan-phase 착수 조건 실측 (2026-08-24)

레인이 들어왔을 때의 트리 상태를 그 트리 안에서 직접 쟀다. 리드 배차문이 적은 값과 하나 어긋났고, 어긋난 쪽을 정정해 기록한다.

    git rev-parse --show-toplevel   .../.claude/worktrees/t18
    git branch --show-current       WT-lxseq-group-plan
    git status --short              (빈 출력)
    git rev-parse --short HEAD      6412fb6          ← 배차문은 fa08651 이라 적었다
    git rev-list --count --left-right origin/main...HEAD
                                    38  0            ← 로컬 0커밋, 순수 조상

로컬 커밋이 0이라 잃을 것이 없어 `git merge --ff-only origin/main` 으로 fa08651 에 맞췄고, 이후 `0 0` 이다. FF 이전에는 `.moai/specs/SPEC-COPILOT-RESTORE-001/` 디렉터리 자체가 없어 전제 3번(하향 판정 문면 확인)을 수행할 수 없었다.

**원인은 미확정으로 남긴다.** 리드 쪽 계기 둘이 같은 순간에 서로 다른 값을 냈다(`git worktree list` 는 6412fb6, `git -C <t18> rev-parse` 는 fa08651). 두 계기가 왜 갈렸는지는 밝히지 않았다. 그럴듯한 설명을 지어 붙이지 않는다. 앞으로 트리 상태는 그 트리 안에서 잰 값을 정본으로 삼는다(리드 합의, 2026-08-24).

의존성: `uv sync` 와 `npm --prefix ui install` 을 exit 0으로 완료했다.

---

## 1. 하향 정정 확인 (전제 3)

`.moai/specs/SPEC-COPILOT-RESTORE-001/readability-survey.md` 의 A.2, A.5, D.9를 읽었다. 확인된 등급은 이렇다.

| 대상 | 등급 | 근거 |
|---|---|---|
| 그룹 존재와 개수 | 읽힘 | 풀 계수 변화 관측 |
| 그룹 이름 | 읽힘 | `prop Name` |
| 그룹 멤버십 | **미측정** (「원리적 불가」에서 하향) | A.2 — 판정 전제가 만료 |

D.9의 범위 제한도 함께 기록한다. 전량 관측된 것은 **풀 노드**(`DataPool/Groups`, 필드 16개, 절단 없음)이고 **개별 그룹 오브젝트**는 그룹이 있는 쇼파일이 없어 재지 못했다. 미발사 경로는 둘이다 — Count 과 Ptr 을 쓰는 둘째 경로, Executor 우회 넷째 경로.

`server/groupgen/write.py:412-422` 는 이미 고친 문면을 달고 있어 엔진 쪽 정정은 필요 없다. 카드 t18 본문에 남아 있는 「원리적 불가」 문면은 **SPEC에 옮기지 않았다.**

---

## 2. 판독으로 드러난 사실 (근거)

카드 t18이 「해소」로 적은 두 항목(12 대 18, 실기 질문)은 재확인됐다. 그 밖에 넷이 새로 나왔고 전부 spec.md의 A.2에 실었다. 여기에는 근거 명령과 관측만 남긴다.

**멤버 개수와 파생 규칙 (이 트리에서 계산)**

    입력  server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv (86행)
    관측  BACK 12 (201-212) · BLIND 6 (601-606) · FOH 8 (111-118) · HAZE 2 (621-622)
          KEY 6 (101-106) · MOVER-D 8 (521-528) · MOVER-U 8 (501-508)
          SIDE-L 6 (301-306) · SIDE-R 6 (311-316) · STROBE 4 (611-614)
          WASH-D 10 (421-430) · WASH-U 10 (401-410)
          MOVER-ALL 16 · ODD 8 (501,503,505,507,521,523,525,527)
                        EVEN 8 (502,504,506,508,522,524,526,528)

**슬롯 상한 (소스 판독)**

    server/groupgen/write.py:66        DEFAULT_GROUP_PLAN_CAP = 16
    server/orchestrator/tools.py:7101  build_group_write_plan 호출에 max_plan_size 없음
    귀결                                18개를 한 호출로 넘기면 GROUP_PLAN_TOO_LARGE

**번들 바이트 (이 트리에서 계산 + 소스 판독)**

    server/spatial/choreography.py:341  구간 압축 없이 " + " 로 이어 붙인다
    ALL 선택 줄 계산값                  1201 bytes (86 FID)
    server/bridge/protocol.py:33        MAX_PLUGIN_CALL_BYTES = 2048
    console/lua/copilot_responder.lua:34-35
        실측 2026-07-24 (onPC 2.4.2): MA3 명령줄은 ~2048바이트를 넘으면 조용히 버린다

    미측정: 조립된 번들 전체(5줄 + 프레이밍)의 인코딩 길이. 1201 < 2048 은
            안전의 근거가 아니다 — 프레이밍 여백을 잰 적이 없다.

**GROUP 시트 정본과 사본**

    정본  src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.group.csv (git 추적 중)
    사본  server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv
    sha256  bc7aced27b0bc06938f2aed2b52c2cff8e2e6ec362ceac154694d5ef64af0172
    19줄 (헤더 1 + 데이터 18) · 헤더 4열 GroupNo,Name,Members,Purpose · BOM 있음

**시트 종류 레지스트리 현황**

    server/sheets/registry.py:302   REGISTRY 는 오늘 patch 와 vectorworks 둘뿐
    server/orchestrator/tools.py:523  SHEET_KIND_ACTIONS 에 patch 만
    server/web/session.py:2650        행 계수기에 patch 만
    server/tests/test_sheet_kind_consumers.py  t51의 함께 자라는 검사가 동반 지점을 강제

---

## 3. 하네스 마찰 기록 (카드 t47 입력)

이 레인에서 쓰기 경로를 찾는 데 걸린 시행착오를 남긴다. 카드 t47의 ②③ 축에 붙는 관측이다.

**Write 도구가 두 가드 사이에서 막혔다.** 같은 세션에서 두 층이 서로 다른 루트를 봤다.

    Write → .claude/worktrees/t18/...   "Path traversal detected: file is outside project directory"
    Write → .claude/worktrees/t51/...   "This session is isolated in the worktree .../t18"
    Write → 스크래치패드                "Path traversal detected"

세 경로 모두 거부라 Write 로는 쓸 곳이 없었다. 세션은 t51 에서 시작해 `EnterWorktree` 로 t18 에 들어왔다 — `docs/runbooks/writing-files-in-a-worktree.md` 가 적은 그 조건이다.

**Bash 우회의 방아쇠는 문자가 아니라 명령 총량이었다.** 런북의 표(중괄호, 리다이렉트)로는 안 잡혔다. 대조군으로 하나씩 쟀다.

    파이프 문자 포함                  통과
    부등호(줄머리)                     통과
    부등호(양쪽 공백, 리다이렉트 모양)  통과
    중괄호 리터럴                      통과   ← 런북 G행과 어긋난다
    chr(123) 로 만든 중괄호            통과
    물결표(범위 표기)                  통과
    반복 생성한 21KB 본문              통과
    실제 문서 약 15KB 를 한 번에        **거부**
    같은 문서를 3~6KB 조각으로          통과 (5조각 전부)

즉 이 세션에서 실제로 걸린 축은 **한 Bash 호출에 실린 명령 텍스트의 총량**이다. 런북이 적은 중괄호 축은 이 세션에서 재현되지 않았다 — 런북의 관측이 틀렸다고 말하는 것이 아니라, **가드 판정이 그 사이에 바뀌었을 수 있고 이 세션은 다른 축에 걸렸다**는 뜻이다. 임계값은 재지 않았다(15KB 는 거부, 6KB 는 통과라는 것만 안다).

**적용**: 워크트리에 들어간 세션에서 긴 문서를 쓸 때는 처음부터 조각으로 나눈다. 한 번에 밀어 넣고 거부되면 원인을 문자에서 찾게 되는데, 이 세션에서는 그 방향이 전부 헛다리였다.

**중요 — 이 관측이 답하지 않는 것.** 위 대조군의 중괄호는 **전부 따옴표 안**이었다. 파이썬 문자열 리터럴 안에 있었고, 통째로 밀어 넣어 거부된 15KB 본문도 삼중따옴표 안이었다. 즉 **따옴표 밖 중괄호는 이 세션에서 한 번도 시험하지 않았다.** 카드 t10b 가 대조군 7건으로 고정한 방아쇠는 「따옴표 밖에 있는, 내용이 든 중괄호 쌍」이고 「따옴표 안의 중괄호는 안 걸린다」도 함께 쟀다 — 그러므로 **이 세션의 관측은 t10b 와 충돌하지 않는다.** 축이 둘이고, 이 세션은 둘째 축(명령 총량)만 건드렸다. 임계값은 안 쟀다(15KB 거부, 6KB 통과만 안다).

참고로 이 세션의 첫 거부(`cat` heredoc + 리다이렉트 + 따옴표 밖 중괄호)는 변수가 셋이라 **어느 것도 귀속되지 않는다.** 한 덩어리에서 얻은 원인은 원인 하나에 무죄 둘이 붙은 것일 수 있다.

---

## 4. 열린 결정 2건 (Kickoff 대기)

리드 판정(2026-08-24): 두 결정 모두 저술을 막지 않으므로 지금 감독께 올리지 않고, plan에서 run으로 넘어가는 착수 승인 때 리드가 한 번에 올린다. 전문은 plan.md의 A.4에 있다.

| 번호 | 결정 | 권고 | 상태 |
|---|---|---|---|
| ① | 슬롯 번호의 권위 — 시트의 GroupNo 인가 엔진이 잰 빈 슬롯인가 | 어긋나면 계획을 내지 않고 대조표를 보고 | **미해소** |
| ② | 입력이 파일 하나인가 둘인가 | 인자 둘(그룹 시트와 패치 시트) | **미해소** |

리드가 두 권고의 방향에 동의를 표했으나(2026-08-24), 그것은 감독 답이 아니다. 답이 오면 이 절에 기록하고 결정 등록부(plan.md A.3)에 T, U로 옮긴다.

---

## §F Phase 4 Mode Selection

- **입력 매개변수**: tier M · scope 약 9파일(신규 2, 테스트 3, 수정 4, fixture 1은 plan-phase 커밋 선반영) · domain 1(Python 백엔드) · 언어 Python과 markdown · concurrency benefit LOW(M1에서 M2, M3으로 이어지는 데이터 사슬)
- **모드 평가**

| 모드 | 선택 | 사유 |
|---|---|---|
| `direct` | 미선택 | 신규 모듈 2개와 툴 배선. 자명한 변경이 아니다 |
| `serial` | **선택** | 코딩 중심 작업이고 마일스톤 사슬이 강한 순차다 |
| `fanout` | 미선택 | 도메인 1개. 다도메인 조사가 아니다 |
| `sweep` | 미선택 | 기계 변환이 아니고 파일 수도 30 미만이다 |

- **Decision: serial**
- **근거**: Anthropic의 코딩 작업 병렬성 단서를 따른다 — 코딩 작업은 조사보다 실제로 병렬화 가능한 갈래가 적다. M1의 파서 산출이 M2 매퍼의 입력이고 M2의 배치가 M3 툴 위임 인자이므로, 앞 단계 산출 없이 뒤 단계를 시작할 수 없다. 파일 수 9개는 `sweep` 의 30 문턱에 크게 못 미치고 변환 규칙도 단일 기계 규칙이 아니다.

---

## §E.1 Plan-phase Audit-Ready Signal

    plan_status: audit-ready
    plan_complete_at: 2026-08-24
    tier: M
    artifacts: spec.md, plan.md, acceptance.md, progress.md
    req_count: 16
    ac_count: 16 (오프라인 15 + 라이브 1)
    milestone_count: 5 (M0..M4)
    open_decision_count: 2 (plan.md A.4 — Kickoff 대기)
    assumption_count: 3 (ASSUMPTION-80..82)

**착수 전 확인이 필요한 것**

1. 열린 결정 2건의 감독 답. 답 없이 run에 들어가면 권고안으로 구현되고 그 사실이 이 파일에 기록돼야 한다.
2. M4 라이브 세션의 선행 조건 — 콘솔에 001의 패치 86대가 들어가 있고 그룹 풀이 비어 있어야 한다. 둘 중 하나라도 아니면 M4는 성립하지 않는다.
3. 전량 테스트 스위트는 **리드가 창을 열어 준 뒤에** 돌린다(2026-08-24 리드 지시 — 같은 기계에서 두 레인이 동시에 돌리면 초록과 빨강이 코드가 아니라 부하를 재게 된다). plan 단계에서는 필요하지 않았고 돌리지 않았다.

**금지어 검사의 대가 (명시)**

AC-LXSEQ2-015 의 금지어 grep 은 범위를 run 산출물로 좁혔다(사유는 acceptance.md AC-015 넷째 항). **그 대가로 그 검사는 SPEC 문서 4종 안의 진짜 단정형을 잡지 못한다.** 오늘 SPEC 4종의 금지어 준수는 다음과 같이 보증됐다.

    SPEC 문서 4종의 금지어 준수는 리뷰로 보증됨 · 검사 없음
    (2026-08-24 리드 육안 8건 판독 — 전부 규칙 문장 또는 하향 명시, 진짜 위반 0)

**검증된 것처럼 읽히게 두지 않는다.** run 단계 산출물은 검사가 보증하고, SPEC 문서 넷은 사람이 읽어서 보증한 것이다. 둘은 등급이 다르다.

**이 문서가 아직 답하지 않은 것**

- 번들 바이트 예산의 실제 값. M2에서 실측으로 정한다.
- 전송 상한의 실제 값. AC-LXSEQ2-016의 다섯째 항에서 처음 측정된다.
- 그룹 CSV의 `group` 종류 술어가 기존 두 종류(patch, vectorworks)의 판정을 흔들지 않는지. AC-LXSEQ2-014의 셋째와 넷째 항이 재지만, 실제 실행은 run 단계다.
