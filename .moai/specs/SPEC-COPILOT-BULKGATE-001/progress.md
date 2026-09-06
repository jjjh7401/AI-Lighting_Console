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

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
