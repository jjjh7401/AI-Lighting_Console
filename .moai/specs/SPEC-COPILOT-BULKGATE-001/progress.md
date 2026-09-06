# SPEC-COPILOT-BULKGATE-001 — 진행 기록

> Tier M · 기준 트리 `main` `b7b030a` (2026-09-07) · 브랜치 `WT-spec-bulk-approval`

## §E.1 Plan-phase Audit-Ready Signal

- 산출물: `spec.md` · `plan.md` · `acceptance.md` · `progress.md` (Tier M 3종 + progress)
- REQ: 16건 (REQ-BULKGATE-001..016) — Tier M 상한 16 에 정확히 닿는다
- AC: 12건 (AC-BULKGATE-001..012), 전부 Given/When/Then
- 범위 제외: `### Out of Scope` H3 5개 (분류 확대 · 기존 봉합 통합 · 새 UI/채널 · 실기와 복원 · 세 번째 통로의 사후 조사)
- 미해결 clarification 마커: 없음
- 콘솔 예산: plan 단계 읽기 전용, 쓰기 0

### plan 단계에서 실제로 잰 것 (이 트리, 이 회차)

| 잰 것 | 명령 | 관측 |
|---|---|---|
| 기준 트리 동기 | `git fetch origin main` · `git rev-list --count --left-right origin/main...HEAD` | `0 0` · HEAD = `origin/main` = `b7b030a` · `git status --short` 빈 출력 |
| SPEC ID 형식 | `[[ "SPEC-COPILOT-BULKGATE-001" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` | `PASS` |
| 디스패치 자리 수 (session) | `grep -c 'name="run_commands"' server/web/session.py` | `16` |
| 디스패치 자리 수 (tools) | `grep -c 'name="run_commands"' server/orchestrator/tools.py` | `12` |
| 디스패치 자리 수 (프로덕션 전체) | `grep -rn 'name="run_commands"' server/ \| grep -v "/tests/" \| wc -l` | `31` (위 28 + `server/tools/lxseq_e2e.py`·`lxseq_pos_e2e.py`·`server/measurement/mock_provider.py`) |
| 프로덕션 승인 호출 전수 | `grep -rn "request_approval(" server/ \| grep -v /tests/` | 게이트 1(`gate.py:355`) + 봉합 4(`tools.py:5603`·`6534`·`9486`, `session.py:8925`) |
| 봉합의 소속 핸들러 | `grep -n '^    def [a-z_]*(call: ToolCall' server/orchestrator/tools.py` | `5603` → `import_lxseq_presets`(5410) · `6534` → `import_lxseq_cues`(5703) · `9486` → `create_arrangement_groups`(9270) |
| 곡 경로의 디스패치 자리 | `server/orchestrator/tools.py:3107-3111` 판독 | `command_bundle = bundle.commands + timing.commands` → `run_commands` 재진입. **봉합 없음** |
| `screen` 서명 | `server/safety/gate.py:322` 판독 | `def screen(self, commands: Sequence[str]) -> ScreenDecision` — 선언 인자 없음 |
| 단일 관문 앵커 | `server/safety/gate.py:317-321` 판독 | `@MX:ANCHOR` "exactly ONE screening path may exist; a second entry would be a gate bypass by construction" |
| 승인 묶음 계약 | `server/safety/approval.py:26-34` 판독 | `ApprovalRequest` = 묶음 하나, 전부-또는-전무 |
| 실패 안전 | `server/safety/approval.py:45-49` · `server/web/approval_bridge.py:11-16` 판독 | `DenyAllApprovalPort` + 4중 거절(미결선·notify 실패·시간 초과·연결 끊김) |
| 감사 API | `server/safety/audit.py:281-287` 판독 | `log_approved`/`log_rejected` 가 `**extra` 를 받는다 → `kind` 실을 자리 있음 |
| t292 봉합의 모양 | `server/web/session.py:8887-8930` 판독 | `_accept_draft_apply_batch` — `kind="draft_apply"` 로 `approved`/`rejected` 기록 |
| 블랙리스트 `Store` 항목 | `grep -n "Store" server/safety/blacklist.yaml` | 항목 둘: `Store /overwrite`(:109) · `Store Preset`(:172). `Sequence`·`Timecode` 없음 |
| 분류 확대의 선례 | `server/safety/blacklist.yaml:69-96` 판독 | 2026-08-05 `Store` 동사 확대 철회 · t86 재측정(전량 스위트 `Store` 67 대 `Label` 17) · 분모 인용 규율 |
| 고정 파일 내용 | `server/tests/test_writegate_merge_gap.py` 전문 판독 | 검사 6개(파라미터 3 + 단독 3). `assert "Store Sequence" not in RULESET.blacklist`(:79) |
| 부수 피해 파일 존재 | `ls server/tests/test_safety_ruleset.py test_fx_boundary.py test_scene_boundary.py test_web_session.py` | 넷 다 존재. `TestLastCreatedSessionTracking`(`test_web_session.py:571`)에 `def test_` 9개 |
| 전수 조사 검사가 빌릴 모양 | `server/tests/test_architecture.py:1-40` 판독 | 정적 임포트 주사 + 파일 지정 예외 목록 + 예외마다 독스트링 사유 |

### plan 단계에서 **안** 잰 것 (미검증)

- **t292 의 비용 숫자를 재현하지 않았다.** 「스위트 13건 실패 · 그중 범위 밖 8건 · 코퍼스 0」은 **카드 t292 의 실측을 옮긴 값**이다. 이 SPEC 은 분류를 안 넓히므로 그 13건을 다시 만들 이유가 없고, run 단계가 재는 것은 반대 방향의 사실 — **분류를 안 넓힌 상태에서 그 8건이 편집 없이 초록**(AC-010)이다.
- **부수 피해 8건의 파일별 내역도 t292 의 값이다.** 파일 넷이 존재한다는 것과 `TestLastCreatedSessionTracking` 에 검사 9개가 있다는 것만 이 트리에서 확인했다. 「4건이 붉어진다」는 그 클래스 안의 어느 4개인지까지는 안 쟀다.
- **검사를 한 번도 돌리지 않았다.** 이 워크트리에 프로젝트 인터프리터(`.venv`)가 없다 — `ls` 로 확인. 착수 초록과 인터프리터 귀속은 run 단계의 첫 작업이다.
- **브라우저 실측 「명령 28개 — 실행 완료 25 · 건너뜀 3」은 2026-09-07 회차의 관측이며 이 회차에서 재현하지 않았다.** 곡·리그·확정 구간이 다르면 숫자가 달라진다(plan.md B-7).
- **디스패치 자리 28개 각각이 쇼파일을 고치는지 안 쟀다.** 센 것은 자리 수뿐이다. 예를 들어 `session.py:9238` 셋리스트 배분(`Copy Sequence` / `Assign Sequence … At Executor`)이 쓰기인지, 그 경로에 채팅 확인 외의 봉합이 있는지는 미측정 — M3 이 분류한다.
- **`BatchRisk` 를 `gate.py` 에 둘지 `approval.py` 에 둘지 안 정했다.** 순환 임포트를 보고 run 단계가 정한다(plan.md M1).
- **M3 의 갈래 하나가 열려 있다**: 전수 조사에서 「쓰기인데 봉합 없음」으로 나온 자리를 표에 어떻게 담을지. 실측 목록을 보고 정하고 근거를 여기 남긴다.
- 실기 grandMA3 발사 0건. 이 SPEC 이 닫혀도 그대로다.

- plan_status: audit-ready
- plan_complete_at: 2026-09-07

## §E.2 Run-phase Evidence

> 브랜치 `WT-bulkgate-run` · 기준 `origin/main` `b7b030a` (`git merge --no-edit origin/main` → `Already up to date.`)
> 검증 인터프리터: 이 워크트리의 `.venv` — `uv run python -c "import server; print(server.__file__)"`
> (`server/` 하위에서) → `.../.claude/worktrees/agent-a5cec538e408d4e39/server/__init__.py`
> 콘솔: 가짜 콘솔 `server/tests/fake_console.py` (포트 **8100/9100**). 포트 8000 미사용, 실기 발사 0건.

### 무엇을 만들었나

| 마일스톤 | 자리 | 내용 |
|---|---|---|
| M1 | `server/safety/gate.py` | `BatchRisk(reason, kind)` frozen dataclass + `screen(commands, *, risk=None)`. 선언이 있으면 `approval_findings = list(findings)`(번들 전체), 없으면 `held`(오늘과 동일). 감사에 `**audit_extra` 로 `kind` 를 싣는다 |
| M2 | `server/orchestrator/tools.py` | `run_commands(call, context, *, risk=None)` · `prepare_songcue` 가 `BatchRisk(reason=…, kind="songcue")` 를 넘긴다 · 거절 갈래 문면(「콘솔에 0건 나갔습니다」) |
| M2+ | `server/web/session.py` · `server/orchestrator/ports.py` · `server/measurement/runner.py` | **브라우저 실측이 잡은 결함** — 아래 「경로가 안 이어져 있었다」 |
| M3 | `server/tests/test_write_dispatch_census.py` (신규) | 디스패치 자리 28 전수 분류 + 분할 단언 + 봉합 존재/부재 단언 + 한계 독스트링 |
| M4 | `server/tests/test_writegate_merge_gap.py` | 독스트링에 종결 기록(전/후). **단언 hunk 0건** |

### 경로가 안 이어져 있었다 — 브라우저가 잡은 결함

게이트만 고치고 단위 검사를 전부 초록으로 만든 뒤 브라우저를 돌렸더니 채팅 턴이
「⛔ 서버 내부 문제」로 끝났다. 감사 로그의 `provider_error` 가 원인을 적었다:

```
{"event": "provider_error", "kind": "unexpected", "provider": "",
 "raw_detail": "TypeError(\"_ObservingBundleGate.screen() got an unexpected keyword argument 'risk'\")"}
```

프로덕션은 게이트를 **감싼 래퍼**(`server/web/session.py:4220 _ObservingBundleGate`)를
통해 들어가는데 그 래퍼가 선언을 못 받았다. 단위 검사는 날것의 `SafetyGate` 를 써서
이 자리를 못 봤다 — 부품이 초록이어도 경로는 안 이어진 상태였다.

고친 자리 셋과, 다시는 이렇게 새지 않도록 세운 계측기 하나:

- `server/web/session.py` `_ObservingBundleGate.screen` — `risk` 를 받아 전달.
- `server/orchestrator/ports.py` `BundleGate` 프로토콜 — `risk` 를 선언(구체 타입은
  `object`, `gate.py` 가 이 모듈을 임포트하므로 반대 방향은 순환).
- `server/measurement/runner.py` 의 계수 래퍼 — 같은 모양.
- `test_bulkgate_declaration.py::test_every_production_screen_surface_accepts_the_declaration`
  — 프로덕션 소스 전수에서 `screen(self, commands, …)` 를 정의하는 자리가 `risk` 를
  키워드로 받는지 정적으로 단언한다. 새 래퍼가 생겨도 같은 자리에서 걸린다.

**전달은 조건부다.** `risk is None` 이면 `screen(commands)` 한 인자로 부른다 —
오늘과 바이트 동일하고, `screen(commands)` 시그니처만 가진 기존 게이트 더블들이
그대로 산다. 선언이 있는데 아래 게이트가 못 받으면 조용히 흘리지 않고 크게 깨진다.

### AC 판정표

| AC | 판정 | 실행한 명령 | 관측 |
|---|---|---|---|
| 001 | PASS | `uv run python -m pytest server/tests/test_safety_gate.py server/tests/test_writegate.py -q` | `87 passed in 1.88s`. 그리고 `git diff origin/main..HEAD --stat -- server/safety/classify.py server/safety/ruleset.py server/safety/grammar.py server/safety/blacklist.yaml` → **빈 출력** |
| 002 | PASS | `pytest server/tests/test_bulkgate_declaration.py::TestDeclarationSplitsTheVerdict -q` | 같은 명령 묶음이 `risk=None` 에서 `cleared=True`, 선언에서 `cleared=False`. `ApprovalRequest.commands == SONGCUE_BUNDLE` (부분집합 아님) |
| 003 | PASS | `TestAuditRecordsTheDecision` + 브라우저 회차 | 수락 `approved` 1건 `kind="songcue"`, 거절 `rejected` 1건 `kind="songcue"`. 선언 없는 번들은 `kind` 없음 |
| 004 | PASS | `TestOneCardPerBundle` | 명령 24건 → `request_approval` **1회**, 항목 24개. `Store Preset 4.1` 항목이 분류 사유를 잃지 않음(`risk_reasons[0]` = 선언 사유, 길이 > 1) |
| 005 | PASS | `TestRefusalSendsNothing` + `TestLockAndBackupStay…` | 거절 시 청산 0 · 콘솔 0건. 포트 미결선(=`DenyAllApprovalPort`)에서도 0건. 승인 중 락이 켜지면 비청산 + 0건. 위험 경로 백업이 선언 경로에서 돌고(`["b"]`), 선언 없는 같은 번들에서는 안 돈다(`[]`) |
| 006 | PASS | `TestTheModelCannotTurnItOff` | `arguments={"risk": None}` 로 불러도 선언 생존 → 승인 요구 → 거절 시 0건. `run_commands` 본문의 AST 주사에서 `arguments` 의 `risk` 접근 **0건**. 뮤테이션은 아래 표 |
| 007 | PASS | `test_bulkgate_songcue_seam.py` + 브라우저 | 승인 요청 1회. `reason` 이 시퀀스 번호·큐 건수·타임코드 슬롯·「복원 경로가 없습니다」 넷을 담음. 거절 문면 「콘솔에 0건 나갔습니다」, 부분 반영 주장 없음 |
| 008 | PASS | `pytest server/tests/test_write_dispatch_census.py -q` | `9 passed`. 주사 **28**자리 = 표 합계 28 (5 + 17 + 6). 두 표 동시 등재는 실패하는 단언 존재. 쓰기+봉합 표의 각 자리에 `risk=`·`request_approval(`·`_accept_` 중 하나 존재. 독스트링이 한계(정적·간접 호출 못 잡음) 기재 |
| 009 | PASS | 음성 대조 — 아래 인용 | 등재 없는 자리를 심으니 파일·행 번호와 함께 실패. 되돌린 뒤 `git status --porcelain` 빈 출력, 다시 초록 |
| 010 | PASS | `pytest test_safety_ruleset.py test_fx_boundary.py test_scene_boundary.py "test_web_session.py::TestLastCreatedSessionTracking" -q` | `99 passed`. `git diff --stat origin/main..HEAD` 로 그 네 파일 + `blacklist.yaml` **빈 출력** — 초록을 만들려고 검사를 고치지 않았다 |
| 011 | PASS | `git diff -U0 origin/main..HEAD -- server/tests/test_writegate_merge_gap.py` | 헝크 **하나**, `@@ -13,0 +14,30 @@` — 순수 삽입 30줄, 모듈 독스트링 안. `-` 로 시작하는 줄 **0건**(단언 삭제 0). `grep -c 'SPEC-COPILOT-BULKGATE-001'` ≥ 1. 파일 전량 초록 |
| 012 | PASS | 브라우저 회차 — 아래 절 | 카드가 명령 **전에** 등장, 문면 4요소 포함. 거절 → 콘솔 0건. 수락 → 한 번에 발사, 명령별 재질문 없음. 감사 `approved` 1 / `rejected` 1 |

### 반증 실험 셋 (전부 실행하고 되돌렸다)

| 실험 | 심은 것 | 관측 | 되돌림 |
|---|---|---|---|
| 뮤테이션 A | `gate.py` 의 선언 처리 분기 삭제 (`approval_findings = list(findings) if risk is not None else held` → `= held`) | `17 failed, 6 passed` — 두 신규 파일 전반이 빨강 | `git checkout` → 초록 |
| 뮤테이션 B | `prepare_songcue` 의 `risk=songcue_risk` 인자 삭제 | `8 failed, 10 passed`. 그중 `test_write_dispatch_census.py::TestSeamPresence::test_each_showfile_write_site_has_a_seam_in_its_function` 도 빨강 — 전수 조사가 봉합 소실을 **독립적으로** 잡는다 | `git checkout` → 초록 |
| 음성 대조 | `session.py` 에 어느 표에도 없는 `name="run_commands"` 자리 하나 | 아래 인용 | `git checkout` → `git status --porcelain` 빈 출력, `9 passed` |

음성 대조 실패 문면(꼬리, 그대로 옮김):

```
E       AssertionError: 등재되지 않은 run_commands 디스패치 자리가 있습니다 — 쇼파일을 고치는지 분류해 세 표 중 하나에 넣어 주세요:
E           server/web/session.py:8891  (함수 _planted_unregistered_dispatch, 그 함수 안 0번째 자리)
E       assert not [('server/web/session.py', '_planted_unregistered_dispatch', 0, 8891)]
```

### 디스패치 자리 28 — 이 회차의 분류

`grep -c 'name="run_commands"'` → `server/orchestrator/tools.py` **12** ·
`server/web/session.py` **16** = **28**. plan 단계 실측과 같다.

- **`SHOWFILE_WRITE_DISPATCHES` (쓰기 + 봉합 있음) — 5**: `prepare_songcue`(이 SPEC 의 `risk=`) ·
  `import_lxseq_presets` · `import_lxseq_cues` · `create_arrangement_groups`(각자 `request_approval`) ·
  `_cue_sheet_draft_apply`(t292 의 `_accept_`).
- **`WRITE_WITHOUT_SEAM_DISPATCHES` (쓰기인데 봉합 없음) — 17**: `instantiate_look` ·
  `prepare_busking` · `precheck_patch` · `_deliver_fx_plan` · `compile_scene` · `arrange_fixtures` ·
  `run_look_bundle` · `_look_pan_tilt` · `_position_fx_sequence` · `_offer_fx_executor_assignment` ·
  `_phaser_recall_sequence` · `_store_position_preset_looks` · `_position_cue_store` ·
  `_position_cue_sheet` · `_merge_timeline_cue_position` · `_setlist_mode` · `_song_finalize`(0번째).
- **`REVIEWED_NON_WRITE_DISPATCHES` (읽고 아니라고 판정) — 6**: `_fire`(`Plugin '<name>'`) ·
  `build_toolset`(디스패치가 아니라 `ToolDefinition` — 같은 리터럴이 주사에 걸린다) ·
  `_point_fixtures_at_target` · `_position_mood_suggestion`(둘 다 프로그래머 `Attribute … At`) ·
  `_phaser_recall`(회수/해제 한 줄) · `_song_finalize`(1번째 — `ClearAll`).

**M3 의 열린 갈래를 이렇게 닫았다**(plan.md M1/M3 이 run 단계에 넘긴 결정): 「쓰기인데 봉합
없음」을 비-쓰기 표에 숨기지 않고 **셋째 표**로 따로 세웠다. 봉합을 다는 일은 이 SPEC 의 범위
밖이므로(§4) 자리마다 사유를 적어 후속 카드로 남기고, 검사는 그 자리에 봉합이 **없음**도
단언한다 — 봉합이 붙으면 검사가 실패하고 그때 첫째 표로 옮긴다. 표가 양방향으로 정직하다.

`session.py` 셋리스트 배분(`_setlist_mode`)은 plan 단계가 「미확인 후보」로 남긴 자리다.
이 회차에서 `Copy Sequence` / `Assign Sequence … At Executor` 를 읽고 **쓰기로 확정**했다.

`BatchRisk` 는 `gate.py` 에 두었다(plan.md M1 의 미결). `tools.py` 가
`from server.safety.gate import BatchRisk` 를 넣어도 순환이 안 생김을 임포트로 확인했다.

### 브라우저 실측 (AC-012) — 2026-09-07, 가짜 콘솔 `full` 리그

띄운 것: 가짜 콘솔 `8100/9100`, 앱 서버 `127.0.0.1:8766` (`--console-port 8100 --receive-port 9100`),
UI 는 `npm run build` 산출물. 모델은 `Gemini · gemini-3.5-flash`.

**거절 회차.** 채팅으로 곡 큐리스트를 요청하니, 명령이 나가기 **전에** 승인 카드가 떴다:

```
승인 대기 — 위험 명령
· 쇼파일 쓰기 — Sequence 4 에 큐 2건을 저장하고 Timecode 7 슬롯을 씁니다
  (이 앱에는 시퀀스·타임코드 복원 경로가 없습니다).
[명령 19개]  [승인]  [거부]
거부 시 번들 전체가 실행되지 않습니다 (all-or-nothing).
```

카드는 **한 장**이고 그 안에 명령 19개가 통째로 들어 있다. 「거부」를 누른 뒤:

- 화면: 「승인 거부로 번들 전체가 실행되지 않았습니다. **감독이 승인을 거절해 콘솔에 0건
  나갔습니다** — Sequence 4 도 Timecode 7 도 바뀌지 않았고, 확정 구간과 타임라인은 그대로
  남아 있습니다.」 · 명령 표는 「명령 19개 — 거부됨 19」.
- 가짜 콘솔 로그: `grep -cE 'Store |Label |ClearAll'` → **0**.
- 감사: `rejected` **1건**, `kind: "songcue"`.

**수락 회차.** 같은 요청을 다시 보내고 「승인」을 눌렀다:

- 화면: 「요청한 명령을 모두 실행했습니다」 · 「명령 19개 — 실행 완료 19」.
  **명령마다 카드가 다시 뜨지 않았다** — 카드는 한 번뿐.
- 가짜 콘솔이 실제로 받은 쇼파일 쓰기(로그 그대로):
  `exec gate-139 Store Sequence 4 Cue 1 'Verse'` · `exec gate-140 Label Sequence 4 'Song 4'` ·
  `exec gate-145 Store Sequence 4 Cue 2 'Chorus'` · `exec gate-147 Store Timecode 7`.
- 감사 두 회차 합계: `approved` **1** · `rejected` **1** · `executed` **20**
  (수락 회차 19 + 위험 경로 백업 `SaveShow` 1).

관측한 명령 수는 **19**다. 2026-09-07 회차의 28과 다르지만 **28은 기준이 아니다** —
곡·리그·확정 구간이 다르면 달라진다(plan.md B-7). 기준은 「카드가 뜬다 / 거절하면 0건」이고
둘 다 관측했다.

### 검증 명령과 꼬리

```
$ uv run python -m pytest server/tests -q
11892 passed, 10 skipped, 1 warning in 153.44s (0:02:33)

$ npm --prefix ui run test
Test Files  24 passed (24)
     Tests  550 passed (550)

$ npx --prefix ui tsc --noEmit -p ui/tsconfig.json
(출력 없음, exit 0)

$ uv run ruff check server/
All checks passed!
```

분모를 함께 적는다: 파이썬 **11892 통과 / 실패 0** (스킵 10), UI **550 통과 / 실패 0**.

### 범위 밖이었는데 건드린 것 — 고정 검사 둘

이 SPEC 은 「검사를 고쳐 초록을 만들지 않는다」를 지킨다. 다만 **기준 SHA 에 고정된 가드
둘**이 이 변경으로 붉어졌고, 그 가드들의 문면이 스스로 「정당한 확장은 핀을 갱신한다」는
선례를 적고 있어 같은 규율로 갱신했다. **감독 확인이 필요한 항목이다.**

| 파일 | 무엇을 갱신했나 | 왜 |
|---|---|---|
| `server/tests/test_overlap_preserve.py` | `server/safety/gate.py` 삭제 줄수 8 → **15**, 그리고 새로 지워지는 **7줄의 정확한 문면**을 핀에 추가 | `screen` 이 `risk` 를 얻으면서 시그니처·독스트링·승인 블록이 **제자리 교체**된다. 지워진 능력은 없다 — 분류 4파일 diff 0 이 그것을 따로 증명한다 |
| `server/tests/test_songcue_bundle.py` | `tools.py` 헝크 시작점 목록에 **968** 하나 추가 | `run_commands` 클로저가 키워드 인자를 얻으면서 헝크 경계가 하나 더 갈린다. **보호 구간**(`_TOOLS_PROTECTED_OLD_RANGES`) 교차는 같은 검사의 둘째 단언이 따로 재고, 그 단언은 손대지 않았고 초록이다 |

같은 계열의 테스트 더블 넷도 `risk` 를 받도록 넓혔다(`test_fx_tool.py` · `test_looks_tool.py` 의
`_RecordingGate`, `test_looks_instantiate.py` 의 스파이). 앞의 둘은 값을 버리지 않고 `risks`
목록에 **기록**하도록 했다 — 나중에 선언이 관문까지 갔는지 검사가 볼 수 있게.

### 미검증 — 이 SPEC 이 닫혀도 남는 것

1. **실기 grandMA3 발사 0건.** 전부 가짜 콘솔이다. 포트 8000 은 한 번도 안 썼다.
2. **`WRITE_WITHOUT_SEAM_DISPATCHES` 의 17자리는 「분류했다」일 뿐 「안전하다」가 아니다.**
   각 자리가 오늘 분류 층에 잡히는지 안 잡히는지는 이 회차가 재지 않았다. 각자 후속 카드다.
3. **간접 호출로 만들어진 디스패치는 정적 주사가 못 잡는다**(검사 독스트링에 기재).
4. **t292 의 「13건 / 부수 8건」을 재현하지 않았다.** 이 SPEC 은 분류를 안 넓히므로 그 숫자를
   다시 만들지 않는다. 잰 것은 반대 방향 — 그 8건이 **편집 없이 초록**(AC-010)이다.
5. **2026-09-07 브라우저 회차가 `prepare_songcue` 를 지났는지 독립으로 확인하지 않았다.**
   그 회차의 「실행 완료 N · 건너뜀 M」 문면은 어떤 `run_commands` 디스패치에도 붙는 일반
   라벨이라 경로를 가르지 못한다. 이 SPEC 은 SPEC §1.4 가 지목한 자리(`tools.py:3108`)를
   봉합했고, **이 회차에서 그 자리로 카드가 뜨는 것을 직접 관측**했다. 다만 곡 업로드→디자인
   →확정 흐름의 `_song_finalize`(`session.py:10077`)는 **다른 경로**이며 봉합 없이 남아 있다
   (위 2번의 17자리 중 하나). 감독이 본 28건이 그쪽이었을 가능성은 **열려 있다**.
6. **`_function_body` 는 같은 이름의 함수가 여럿이면 첫 번째를 읽는다.** 이 회차의 28자리에서는
   충돌이 없었지만(검사 초록), 동명 함수가 생기면 봉합 판정이 엉뚱한 본문을 볼 수 있다.
7. UI DOM 의 접근성·시각 회귀는 안 쟀다. 잰 것은 카드의 **존재·문면·개수**와 콘솔 도달 건수다.

## §E.3 Run-phase Audit-Ready Signal

- run_status: audit-ready
- run_complete_at: 2026-09-07
- 구현 파일: `server/safety/gate.py` · `server/orchestrator/tools.py` · `server/orchestrator/ports.py` · `server/web/session.py` · `server/measurement/runner.py`
- 신규 검사: `server/tests/test_bulkgate_declaration.py` · `server/tests/test_bulkgate_songcue_seam.py` · `server/tests/test_write_dispatch_census.py`
- 문면만 갱신: `server/tests/test_writegate_merge_gap.py` (단언 hunk 0건)
- 고정 검사 갱신(감독 확인 필요): `server/tests/test_overlap_preserve.py` · `server/tests/test_songcue_bundle.py`
- AC: 12/12 PASS, 각 행이 실행한 명령과 관측을 함께 적는다
- 회귀: 0 (`server/tests` 11892 통과 / 실패 0, UI 550 통과 / 실패 0)
- 콘솔: 가짜 콘솔만. 실기 발사 0건, 포트 8000 미사용

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
