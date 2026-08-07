# 세션 인계 — 2026-08-07 (스펙 실현가능성 정리 + P0 구현)

> **이 문서 하나로 재개할 수 있게 썼다.** 다음 세션은 대화 히스토리를 보지 못한다.
> 읽는 순서: §0(지금 상태) → §2(다음 할 일) → §3(리베이스 함정) → 필요할 때 §4~§7.
>
> 작성 세션: 2026-08-07 · 산출 커밋 5건 · 코드 변경 1건(P0) · 나머지는 문서

---

## §0. 지금 상태 — 브랜치 3개

| 브랜치 | HEAD | 기반 | 상태 | 다음 조치 |
|---|---|---|---|---|
| `origin/main` | `c6be036` | — | PR #28까지 머지됨 | — |
| **`jjjh7401/spec-feasibility`** | `1fa0f87` | `origin/main` `c6be036` | **깨끗함. 충돌 0.** 스펙 정정 29건 + 리포트 | **① PR → 머지** |
| **`jjjh7401/paperwork-p0`** | `f89efff` | `feature/SPEC-COPILOT-MCP-001`(스테일) | **main보다 40커밋 뒤.** P0 코드 4건 + 커버리지 리포트 v2 | **② 리베이스 → 회귀 재측정 → PR** (§3) |

작업 워크트리:
- 메인 리포 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` — `paperwork-p0` 체크아웃 중.
  ⚠️ `.claude/**`·`.moai/**`에 **이 작업과 무관한 미커밋 변경 77건**이 있다(MoAI 플러그인 갱신). **건드리지 마라.**
- `/Users/studiox/orca/workspaces/AI-Lighting_Console/spec-feasibility` — `spec-feasibility` 체크아웃. 깨끗함.
- `/Users/studiox/orca/workspaces/AI-Lighting_Console/spec-vwx-001` — **다른 세션이 VWX-001 plan 작업 중. 건드리지 마라.**

---

## §1. 이번 세션이 한 일

### `spec-feasibility` 브랜치 (2 커밋)

| 커밋 | 내용 |
|---|---|
| `2d04125` | **SPEC·제안서 정정 29건** — 13 files, +227/−56 |
| `1fa0f87` | `docs/reports/2026-08-07-spec-feasibility-review.html` — 정정의 근거와 판정을 한 장으로 |

정정의 성격 3유형:
1. **원리적 불가인데 "후속 후보"로 살아 있던 것 5건** — 무응답 탐지 · 이상 감지 · 매직시트 완전형 · `SaveShow` 디스크 판독 가설 · 큐 내용 판독
2. **문서가 자기 문단 안에서 모순되던 것 3건** — GROUPGEN 복원 조건 (b)(같은 문단이 금지한 행위) · (a)(존재하지 않는 `introspect` 동사) · TRUNCATE 상한 인상("비용"이 아니라 봉쇄)
3. **이미 열렸는데 "막혔다"로 적힌 것 8건** ← **이게 절반이고 가장 위험하다.** 열린 문을 닫힌 문으로 적어 두면 아무도 착수하지 않는다.

### `paperwork-p0` 브랜치 (3 커밋)

| 커밋 | 내용 |
|---|---|
| `d845ca0` | **P0 4건 구현** — 18 files, +2,657/−3 (코드) |
| `0b03e3c` | 커버리지 리포트 정정 15건 |
| `f89efff` | 커버리지 리포트 **v2 재작성** — 정정을 본문 통합 + 벽 대장 완성 + 매트릭스·목차 |

P0 4건 상세:
- **W1 폭 상계 + 인쇄 스타일** — `PatchSheet`에 `bound`/`bound_source`/`bound_unavailable` 3필드 +
  `build_patch_sheet(walk=…)`. 상계는 `footprint.upper_bound()`만 사용(부분 모드 집합의 `max`는 거짓 안심).
  렌더는 값·출처·**비대칭 한정을 한 문장에**, `walk` 없으면 줄 자체를 내지 않는다.
  세 렌더러 공용 `@media print`에 4규칙(thead 반복 · break-inside · print-color-adjust · 여백 정리).
- **W2 인수인계 패키지** — `server/paperwork/bundle.py` 신규. `build_handover_pack`이 시트 3종 + `index.html`을
  한 폴더에 결정적 파일명으로. 부분 실패는 문서 단위 격리(닫힌 어휘 `생성됨`/`조회 실패`/`미배선`),
  **불완전성을 인덱스 첫 화면에**. 툴 등록 18 → 19.
- **W3 UI 노출** — `server/web/paperwork_api.py`(`GET /api/paperwork` · `POST /api/paperwork/{kind}`,
  kind는 닫힌 테이블 라우팅) + `ui/src/components/PaperworkPanel.tsx`. 런북 모드의 헤더 토글 패턴 재사용.
- **코디네이터 직접 수정 2건** — ① 라우트 계수 게이트(`test_prechk_tool.py::_EXPECTED_WEB_ROUTES`)에
  paperwork 2라우트 등재 ② 인덱스 요약이 `4/4건 관측 (incomplete)`처럼 **수치는 맞는데 사유를 못 밝히던 결함**
  정정 + 비공허성 대조군 포함 테스트 3건.

검증 기록(그 시점): `pytest 4,300 passed / 5 skipped / 0 failed` · `vitest 379 passed` · `tsc --noEmit` 클린.
⚠️ **이 수치는 스테일 기반에서 잰 것이라 리베이스 후 재측정 전까지 근거가 아니다.**

---

## §2. 다음 할 일 — 이 순서로

### 1️⃣ `spec-feasibility` PR → 머지 (충돌 0, 가장 먼저)

```bash
cd /Users/studiox/orca/workspaces/AI-Lighting_Console/spec-feasibility
git log --oneline -2          # 1fa0f87, 2d04125 확인
git push -u origin jjjh7401/spec-feasibility
gh pr create --base main --title "docs: 스펙 실현가능성 정정 29건 — 실패·불가 판정이 '나중에 하자'로 살아 있던 곳"
```
**왜 먼저인가**: 문서만 바뀌고 코드 0건이라 충돌이 없다. 그리고 **다른 모든 판단의 근거 문서**다 —
이게 머지되기 전에 다른 작업이 착수하면 다시 스테일 문서를 읽는다.

### 2️⃣ `paperwork-p0` 리베이스 → 재측정 → PR (§3의 함정 먼저 읽을 것)

### 3️⃣ P0-5 매직시트 축약형 — 측정 없이 가능한 마지막 P0

완전형은 죽었다(§4 W1). **축약형은 선행 측정이 0건이라 지금 착수 가능**하다:
그룹·프리셋 **이름** + 패치 요약 + **배치 좌표**(`get_spatial_context`가 `(fid,name,x,y,z)`를 준다).
SPATIAL이 좌표를 열었으므로 **평면 배치도 매직시트가 제안 작성 시점보다 오히려 가능해졌다.**

### 4️⃣ 라이브 측정 2건 (콘솔이 붙는 세션에서, 비파괴 읽기, 예상 30분)

| # | 발화 | GO면 | NO-GO면 |
|---|---|---|---|
| M1 | `prop <id> DataPool/Sequences/<n>/Cue <m> CueFade` | 큐시트가 **진짜 큐시트**가 된다 | 명시적 DESCOPE 확정. **추정 열은 만들지 않는다** |
| M2 | `ASSUMPTION-27` 미측정 후보 2건(`PRECHK-001/progress.md:631` 등재) | 상계가 **정확폭으로 승격** | 상계 유지 |

`prop`은 임의 오브젝트 경로 + 단일 토큰 프로퍼티를 받고 응답기가 경로에 공백을 허용하므로
(`server/bridge/protocol.py:136-142`, `console/lua/copilot_responder.lua:901`) **구조적으로 발화 가능**하다 —
성립 여부만 미측정이다.

⚠️ **`TrigType`·`TrigTime`은 측정 대상이 아니다.** 이미 읽힌다(§4 W2).
⚠️ **그룹 멤버십도 측정 대상이 아니다.** 이미 답이 나왔다(§4 W1).

### 5️⃣ 쇼파일 복원 발신부 (자체 SPEC 필요)

스냅샷 보관·조회·감사연결은 완료, **되돌려 올리는 발신부만 비어 있다**.
자리는 `server/safety/gate.py`의 `@MX:NOTE`에 예약돼 있고 사유는 `server/safety/backup.py:24-28`에 있다.
**WRITEGATE-001이 쓰기 게이트를 깔아 선행의 절반을 이미 치렀다** — 착수 적기가 됐다.

### 6️⃣ 비텍스트 입력 개통 (§4 W8) — 오디오·이미지가 같은 잠금을 공유

열면 제안서 P1-1 전반부(음원 분석)와 P3-7(이미지→룩)이 **동시에** 살아난다.

---

## §3. `paperwork-p0` 리베이스 함정 — 착수 전 필독

**충돌은 정확히 2파일이다.** 나머지(`server/paperwork/**`, `server/web/**`, `ui/src/**`, `test_prechk_tool.py`)는
main에서 **변경 0건**임을 실측 확인했다.

| 파일 | 우리 | main | 해소 |
|---|---|---|---|
| `server/orchestrator/tools.py` | `TOOL_NAMES` **19** (`build_handover_pack` 추가) | **22** (spatial 4종 추가) | **23**으로 병합 |
| `server/tests/test_tools.py` | `== 19` 단정 | `== 22` 단정 | `== 23` |

**결정이 필요한 지점 하나** — `TOOL_NAMES` 배열에서 `build_handover_pack`을 어디에 둘 것인가:
(a) spatial 4종 뒤 맨 끝에 append(main의 순서 보존) / (b) 페이퍼워크 3종 바로 뒤(기능 인접).
저장소 선례는 **맨 끝 append**다(GROUPGEN이 `TOOL_NAMES` 확장 시 그렇게 했다) → **(a) 권장.**

리베이스 후 **반드시** 다시 돌릴 것:
```bash
uv run pytest server/tests -q          # 4,300은 스테일 기반 수치 — 재측정 필요
cd ui && npm test && npx tsc --noEmit
```

추가로 확인할 것 — **TRUNCATE-001과의 정합성**: main이 *"부분 판독은 구조적으로 다른 응답을 낸다"*
(`partial_fixtures` + `missing{...}` + `analysis_withheld`)를 도입했다. 우리 인수인계 인덱스는 불완전성을
**문자열 요약**으로 낸다. **같은 사실을 두 어휘로 말하게 두면 안 된다** — 어느 쪽으로 통일할지 결정할 것.

---

## §4. 벽 대장 — 모든 판정의 기준 (실측 확정)

### MA3가 닫은 것 — 응답기를 고쳐도 열리지 않는다

| # | 벽 | 근거 좌표 |
|---|---|---|
| **W1** | **그룹 멤버십 판독 불가 = 플랫폼 한계.** `prop` 사다리 9종 + 접근자 `COUNT` 전량 닫힘. 실사용 그룹 4개 전부 `0`인데 **날조 대조군은 `ok:false`** → 그 `0`은 **실제 판독값**이다. 사다리 전부를 탄 뒤의 결론 | `SPEC-COPILOT-GROUPGEN-001/spec.md:361-363` · `progress.md:387-389` · 교훈 `grandma3-group-membership-not-readable` |
| **W3** | **픽스처 하드웨어 피드백 0건.** 동사표가 `ping·state·prop·exec·deploy` 5종으로 닫혀 텔레메트리 자리가 없다 | `server/prechk/macro.py:3-7`(코드 자기선언) · `console/lua/copilot_responder.lua:884-946` |
| **W4** | **픽스처↔채널폭 조인 0건.** 후보 12경로 전수 반증. 상계는 **"겹침 없음"만 증명하고 "겹침 있음"은 증명 못 한다** | `SPEC-COPILOT-PRECHK-001/progress.md:296` · `server/prechk/footprint.py:1-15` |
| **W5** | **MA3 쇼파일 파서 0건.** 디스크 export는 **라이브 상태가 아니다**(BUSKWIZ 오진 선례) | `SPEC-COPILOT-PRECHK-001/research.md:44-47` |
| **W6** | **페이로드 1900B.** ~2048B 초과 회신을 **조용히 드롭**(스윕 2000 배달/2100 유실). **상한 인상은 봉쇄이지 트레이드오프가 아니다.** 39대 리그에서 **18/39** | `console/lua/copilot_responder.lua:33,36-39` · `GROUPGEN-001/progress.md:428` |
| **W7** | **빈 익스큐터 식별 불가.** "비어 있음"과 "존재하지 않음"이 구별 안 됨 — 텔레메트리가 아니라 **오브젝트 식별** 문제 | `SPEC-COPILOT-BUSKWIZ-001/progress.md:306` |

### 부분적으로 무너진 벽

| # | 벽 | 근거 |
|---|---|---|
| **W2** | **큐 판독 — `TrigType`·`TrigTime`은 v1.5.0 `prop`으로 읽힌다.** 그 개정은 SONGCUE-001 M0가 직접 집행했다. **남은 것은 `CueFade`와 큐의 내용 둘** | `SPEC-COPILOT-SCENE-001/spec.md:230`(YES) · `:231-232`(NO) · `copilot_responder.lua:55-57,593-594` |

### 우리가 안 연 것 — 벽이 아니다

| # | 축 | 내용 |
|---|---|---|
| **W8** | **비텍스트 입력 채널 부재** — 오디오/비전 의존성 0 · WS `receive_text()` 텍스트 전용 · Tauri capability `no upload`. **MA3 벽이 아니라 우리 앱 미개통 인프라. 열 수 있다.** 벽 목록과 섞으면 **열 수 있는 것을 못 여는 것으로 오분류**한다 | `SPEC-COPILOT-SONGCUE-001/spec.md:29-40` |

### 이미 열렸으니 "막혔다"고 쓰지 말 것

| # | 내용 |
|---|---|
| R1 | 무승인 좌표 쓰기 → **WRITEGATE-001이 2026-08-05 해소**(`blacklist.yaml` v2, `"Set Fixture"`) |
| R2 | "현 쇼파일은 픽스처타입 1종" → **2타입 리그 확보됨(2026-08-04)** |
| R3 | P2-4 자동 페이퍼워크 → **출하됨**(쇼파일 파서 없이 라이브 질의로) |
| R4 | 구간 겹침 재개 · 프리셋 읽기 → **둘 다 출하 완료** |
| R5 | 폐쇄집합(블랙리스트·어휘) 개정 → **절차가 WRITEGATE로 선례화됨** |
| R6 | `console/lua/**` PRESERVE 해제 → **blocker가 아니라 절차**(응답기 개정 2회 집행 선례) |

---

## §5. 확정된 결정 — 다시 논쟁하지 말 것

1. **관측하지 않은 것을 보고하지 않는다.** 못 읽으면 **못 읽었다고 산출물에 쓴다.**
   "일정 시간 무반응 → 죽은 것으로 간주" 류의 우회는 **금지**(관측하지 않은 시간을 보고하는 것).
2. **완결 SPEC의 과거 판정은 사실이다.** 뒤집혔으면 원문 보존 + **소급 정정 각주**.
   고쳐 쓰는 것은 **미래를 가리키는 문장**뿐이다.
3. **불가 항목을 지울 때는 사유를 남긴다.** 지우기만 하면 다음 사람이 다시 제안한다.
4. **제안서는 원문 무수정 + 판정 계층**(배너 + 앵커 + 말미 판정표). `2026-08-02` 문서의 §6이 형식 선례.
5. **순환 import**: `server/paperwork/data.py` → `server/orchestrator/tools.py` 방향이 있으므로
   역방향은 **함수 지역 지연 import**(`tools.py:2344-2346` 주석 참조).
6. **`server/paperwork/`는 조회 전용.** OSC 송신 표면·실행 포트·`server.bridge` import 0건
   (`test_paperwork_boundary.py`가 소스 스캔으로 강제).
7. **폐쇄집합 개정 절차**: 엔트리 추가 + version 범프 + REVISION HISTORY + 코퍼스 갈래 결정.
8. **PDF는 브라우저 인쇄로 종결.** weasyprint 류 도입 안 함(PyInstaller 번들 비용).

---

## §6. 함정 — 이번 세션에 실제로 밟은 것

1. **⚠️ Orca 병렬 워커 + 외부 워크트리 = 실패.** 워커를 메인 리포에서 띄우고 `cd`로 다른 워크트리를 쓰게 했더니
   Claude Code의 경로 샌드박스가 거부했다(`Error: Path traversal detected: file is outside project directory`).
   **`orca worktree create`로 만들어 워커의 프로젝트 루트 자체를 대상 워크트리로 잡아야 한다.**
   약 1시간 손실. 파일 오염은 0건.
2. **⚠️ `orca orchestration dispatch`가 프롬프트를 붙여넣고 Enter를 안 누르는 경우가 있다.**
   터미널에 `❯ [Pasted text #1 +N lines]`가 떠 있으면 그 상태다 →
   `orca terminal send --terminal <handle> --text "" --enter`.
3. **⚠️ `.moai/state/`는 `.gitignore:206` 대상**이라 거기 쓴 브리프는 **커밋되지 않는다.**
   durable 인계는 이 문서처럼 **추적되는 경로**에 써야 한다.
4. **⚠️ 스테일 기반에서 잰 테스트 수치는 근거가 아니다.** `paperwork-p0`의 4,300 green이 그렇다.
5. **⚠️ 메인 리포에 무관한 미커밋 변경 77건**이 있다. `git add -A` 금지 — 경로를 명시해 add 할 것.

---

## §7. 열린 질문 / 미해결

| # | 항목 | 상태 |
|---|---|---|
| 1 | 리베이스 시 `TOOL_NAMES`에서 `build_handover_pack` 위치 | **결정 필요**(§3 — (a) 맨 끝 append 권장) |
| 2 | 인수인계 인덱스의 불완전성 표현을 TRUNCATE-001의 구조 분기와 통일할지 | **결정 필요** |
| 3 | `MCP-001` plan-audit FAIL 0.78 | **살릴 수 있다** — P0 3건(D1 `precheck_patch` 변이 · D2 도달성 공허 통과 · D3 부팅 `SaveShow`)은 전부 `불가-축소`. 툴 분할표를 main 22종 기준으로 재작성 필요(현 문서는 18종 전제 — 이미 거짓) |
| 4 | `VWX-001` | 다른 워크트리에서 plan 진행 중. **`server/paperwork/render.py`에 `render_patch_diff()`를 얹을 예정** → 매직시트 축약형과 같은 파일이므로 **VWX 먼저 머지** 권장 |
| 5 | `SPATIAL` Layout 기록 축 | **유일하게 살아 있는 SPATIAL 잔여.** Layout 요소 좌표(`Set Layout … 'PositionX'`)는 오늘도 `safe` — 3D 축과 **함께** 다뤄야 한다 |
| 6 | OVERLAP 후속 순위 1(응답기 계수 파생) + C-2 | **같은 결함의 두 얼굴 — 하나의 SPEC으로 묶을 것.** 선행은 응답기 개정(절차) + 라이브 측정 1건 |

---

## §8. 산출물 색인

| 문서 | 브랜치 | 내용 |
|---|---|---|
| `docs/reports/2026-08-07-spec-feasibility-review.html` | `spec-feasibility` | **스펙 실현가능성 전수 검토** — 판정 어휘 4값 · 벽 대장 · 정정 3유형 · 제안서 9항목 판정 · 규율 검증 |
| `docs/reports/2026-08-06-workflow-coverage-review.html` | `paperwork-p0` | **업무 프로세스 커버리지 v2** — 기준 계열 표 · 직무별 과업 매트릭스 24행 · 단계별 현황 · 벽 8건 · 우선순위 P0~P3 · v1 개정 이력 15건 |
| `docs/proposals/2026-07-26-…-proposal.md` §5 | `spec-feasibility` | 제안 9항목 **이행·판정 기록**(각 판정/근거/무엇이/실현형 4줄) |
| 이 문서 | `spec-feasibility` | 세션 인계 |

⚠️ **두 리포트가 서로 다른 브랜치에 있다.** 한 트리에서 보려면 §2의 ①②를 마쳐야 한다.

---

## §9. 재개 첫 명령

```bash
cd /Users/studiox/Documents/Claude/Code/AI-Lighting_Console
git fetch origin
git log --oneline -1 origin/main                    # c6be036에서 전진했는지 확인
git worktree list                                   # spec-feasibility · spec-vwx-001 생존 확인
git -C /Users/studiox/orca/workspaces/AI-Lighting_Console/spec-feasibility log --oneline -2
```

그 다음 §2의 1️⃣부터. **`origin/main`이 `c6be036`에서 더 전진했다면 §3의 충돌 목록을 다시 실측할 것** —
이 문서의 "충돌 2파일"은 `c6be036` 기준이다.
