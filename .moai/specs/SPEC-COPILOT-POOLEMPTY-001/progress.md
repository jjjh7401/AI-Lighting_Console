# SPEC-COPILOT-POOLEMPTY-001 — 진행 기록

> 카드 t270 · Tier M · 기준 트리 `main` `f727e11` (2026-09-06)

## §E.1 Plan-phase Audit-Ready Signal

- 산출물: `spec.md` · `plan.md` · `acceptance.md` · `progress.md` (Tier M 4종)
- REQ: 16건 (REQ-POOLEMPTY-001..016), 전부 GEARS 마커 표기 (Tier M 상한 — 이후 개정은 문구 확장만)
- AC: 15건 (AC-POOLEMPTY-001..015), 전부 Given/When/Then
- plan-audit: 1차 FAIL 0.71 → 2차 **PASS 0.86** (`.moai/reports/plan-audit/SPEC-COPILOT-POOLEMPTY-001-review-2.md`); 2차 차단 결함 D-N1·D-N2 와 선택 D-N3·N4·N7 을 같은 커밋에서 반영
- 범위 제외: `### Out of Scope` H3 3개 (형제 결함 `_free_macro_slot` · 타임코드 기능 확장 · 프로토콜 구조 변경)
- 앵커 실측: `f727e11` 에서 직접 열어 확인 (plan.md §A 표)
- 미해결 clarification 마커: 없음
- 콘솔 예산: 읽기 전용, 쓰기 0
- plan_status: audit-ready
- plan_complete_at: 2026-09-06

## §E.2 Run-phase Evidence

> 실행 트리: 워크트리 `.claude/worktrees/agent-a0769b97bff1e9289`, 브랜치 `WT-pool-empty-run`, 기준 `origin/main` `72e4ca6` (2026-09-06 `git fetch origin main` 으로 확인). 커밋: M1 `f7e0285` · M2 `792593a`. 모든 출력은 **이 트리에서 이 회차에** 실행한 명령의 꼬리를 그대로 옮긴 것이다.
>
> 인터프리터: `.venv/bin/python` (Python 3.11.15, `uv run` 이 `.python-version` 으로 이 워크트리 안에 만든 환경). 착수 시 `server/tests` 하위 디렉터리에서 `uv run --project ../.. python -c "import server; print(server.__file__)"` → `…/agent-a0769b97bff1e9289/server/__init__.py` — 남의 트리 `.pth` 가 이기지 않는다. 그래서 `server/tests/test_tree_identity.py` 는 이 트리에서 **통과**한다(알려진 환경 실패는 발생하지 않았다).
>
> 콘솔 접촉 0 — UDP 전송 0건, 127.0.0.1:8000 대상 실행 0건. conftest 의 `_refuse_live_console_port` 는 그대로이고, 전량 실행에서 그 가드가 실패시킨 검사는 없다.

### E.2.1 AC PASS/FAIL 표 (오프라인 AC 전부)

| AC | 판정 | 명령 | 실제 출력 (꼬리) |
|---|---|---|---|
| AC-POOLEMPTY-001 | PASS | `.venv/bin/python -m pytest server/tests/test_lua_responder.py -q -p no:cacheprovider -k EnumerationMarker` | `14 passed, 121 deselected` — `test_a_successfully_empty_pool_says_ok` 가 `ok True · childCount 0 · enumeration "ok" · children [] · truncated False` 를 동시에 단언 |
| AC-POOLEMPTY-002 | PASS | 같은 명령 | `test_a_handle_that_cannot_enumerate_says_failed` — `Children()`·`Count()` 가 둘 다 `error()` 를 던지는 노드를 `ResponderHarness(extra_env=_dead_pool_env())` 로 주입(`__NODE` 무수정). `enumeration "failed"` + `childCount 0` + 오늘 값 셋 유지 |
| AC-POOLEMPTY-003 | PASS | 같은 명령 | `test_every_successful_state_reply_carries_one_of_two_values` 10형상(기본 트리 4 + 갭 풀 3 + 빈/죽은/Count전용 풀 3) 전부 `enumeration ∈ {"ok","failed"}`, 누락 0 |
| AC-POOLEMPTY-004 | PASS | `grep -n 'safe_children(' console/lua/copilot_responder.lua` | `647:function M.safe_children(handle)` / `712:    local children = M.safe_children(handle)` / `868:    local children, enumeration = M.safe_children(handle)` / `1246:    local children = M.safe_children(plugin)` — **4행**. `test_lua_responder.py` 전량 135 passed(갭 풀·`find_child`·`deploy`/`set_plugin_source` 계열 포함), 새 실패 0 |
| AC-POOLEMPTY-005 | PASS | `grep -n 'VERSION = ' console/lua/copilot_responder.lua` · `grep -n '1\.6\.5' console/lua/PROTOCOL.md` · `grep -n '"v": 1' console/lua/PROTOCOL.md` | `111:    VERSION = "1.6.5",` · PROTOCOL `19:> Revision note (responder 1.6.5, …` + `215:- **\`node.enumeration\`** (additive, responder 1.6.5, …` (revision note 와 §4.2 **둘 다**) · `7:Versioning: every reply payload carries "v": 1` 불변 · `grep -c 'ASSUMPTION-53'` → 0 |
| AC-POOLEMPTY-006 | PASS | `.venv/bin/python -m pytest server/tests/test_songcue_tool.py -q -p no:cacheprovider` | `test_an_empty_pool_with_the_ok_marker_is_free` — `(None, SongCueTimingAxes())`, `timecode_go is True`. 종단: `test_an_empty_pool_the_responder_vouches_for_is_free` 가 `Store Timecode 7` 발화 + `skipped_axes == []` |
| AC-POOLEMPTY-007 | PASS | 같은 명령 | `test_an_empty_pool_without_the_marker_is_unknown_with_todays_exact_reason` — 사유가 `"timecode pool occupancy could not be established (DataPool/Timecodes reported zero children — a failed enumeration and an empty pool are indistinguishable here) — the timecode write is withheld rather than sent unchecked"` 와 **바이트 동일**. 기존 `test_an_empty_pool_is_treated_as_unreadable_not_as_free`(마커 부재)도 그대로 초록 |
| AC-POOLEMPTY-008 | PASS | 같은 명령 | `test_an_empty_pool_with_the_failed_marker_is_unknown` — `timecode_go False`, 사유 위와 동일. 추가: `"OK"` 같은 제3값도 신뢰하지 않음 |
| AC-POOLEMPTY-009 | PASS | 같은 명령 | `test_the_other_five_unknown_branches_are_not_relaxed_by_the_marker` — 다섯 형상 전부 `timecode_go False`, 사유 5종이 현행 문자열과 동일(판독 예외·비매핑은 `node` 가 없어 마커를 실을 자리가 없고, truncated·childCount 부재·짧은 열거는 `"ok"` 를 실은 채) |
| AC-POOLEMPTY-010 | PASS | `.venv/bin/python -m pytest server/tests/test_musicsync_m3a_probe.py -q -p no:cacheprovider` | `TestSlotVerdictIsTheAppPredicate::test_the_two_verdicts_agree_on_every_shape` 12형상(free·occupied·unknown 5·마커 ok/failed·마커+truncated·마커+짧은 열거·비매핑·판독 예외) 전부 프로브 판정 == 앱 판정, unknown 사유 문자열 동일 |
| AC-POOLEMPTY-011 | PASS | `.venv/bin/python -m pytest server/tests/test_responder_roundtrip.py -q -p no:cacheprovider` · `grep -rn 'EXPECTED_RESPONDER_VERSION = ' server/` | 교차 파일 대조 통과(부분집합 281 passed 에 포함) · `server/safety/responder_version.py:35:EXPECTED_RESPONDER_VERSION = "1.6.5"` **정확히 1행** |
| AC-POOLEMPTY-012 | PASS | `git diff 72e4ca6 --stat -- server/safety/gate.py` | 출력 **없음**(빈 diff) — 새 분기 0. low 갈래 검사는 `test_safety_lock_monitor.py` 등 기존 검사가 전량 실행에서 초록 |
| AC-POOLEMPTY-013 | NOT RUN | (실기, 운영자 게이트 — M3) | 이 회차 범위 밖. §E.2.5 Gaps |
| AC-POOLEMPTY-014 | PASS (오프라인 반쪽) / NOT RUN (실기 반쪽) | `git diff 72e4ca6 -- server/ console/ \| grep -c 'execution_port.execute\|run_commands('` | `0` — 발화 지점 추가 0. 「합계 0 / 상한 8」 실기 줄은 M3 |
| AC-POOLEMPTY-015 | PASS | `.venv/bin/python -c "from server.orchestrator.tools import timecode_slot_verdict; import server.tools.musicsync_m3a_probe as p; print(p.timecode_slot_verdict is timecode_slot_verdict)"` · `grep -n 'def _timecode_slot_verdict' server/orchestrator/tools.py` | `True` · grep **0행**(exit 1) · 프로브 `slot_verdict` 본문(`:156-161`) = `timecode_slot_verdict(...)` 호출 1 + `(점유자, 축)` → 3분 문자열 번역 5행, 판독 분기 0(`test_the_adapter_only_calls_it_and_reimplements_no_branch` 가 `query_state/childCount/truncated/children` 부재를 단언) · `test_songcue_tool.py` `prepare_songcue` 계열 옮기기 전(기준 트리 238 passed)과 후 모두 초록 |

### E.2.2 불변식·게이트 증거

- **RED 증거 (E8, GREEN 전 실측)** — M1: `.venv/bin/python -m pytest server/tests/test_lua_responder.py -q -p no:cacheprovider -k EnumerationMarker` → `13 failed, 1 passed, 121 deselected in 0.43s`, 대표 실패 `AssertionError: {'childCount': 1, 'class': 'Pool', 'name': 'Timecodes'} … assert 'enumeration' in {…}`(살아남은 1건은 `safe_children(` 4행 구조 불변식). M2: `.venv/bin/python -m pytest server/tests/test_songcue_tool.py server/tests/test_musicsync_m3a_probe.py -q -p no:cacheprovider` → `ImportError: cannot import name 'timecode_slot_verdict' from 'server.orchestrator.tools'` · `2 errors during collection`.
- **비테스트 호출자 grep** — `grep -rn 'timecode_slot_verdict' server | grep -v tests/` → `server/tools/musicsync_m3a_probe.py:77` (import) · `:156` (호출) · `server/orchestrator/tools.py:1955` (정의) · `:2797` (prepare_songcue 핸들러 호출) + 주석 4행(`probe:32,149,545`, `tools:371`) + `server/orchestrator/songcue_timecode.py:16`(옛 이름을 언급하는 독스트링, 아래 잔여 위험). 생산 호출자 **2**(핸들러 + 프로브).
- **행번호 인용 정리 (plan B-1)** — `grep -n '2792' server/tools/musicsync_m3a_probe.py server/tests/test_musicsync_m3a_probe.py` → 출력 없음, exit 1 (**0행**).
- **chokepoint 가드 (`test_overlap_preserve.py`)** — `_SAFETY_EXPECTED_DELETIONS["server/safety/responder_version.py"] == 0` 그대로 통과: 값 한 줄 교체지만 이 파일은 PRECHK 기준에 없어 numstat 삭제 0. `TestToolsProtectedRegions` 통과(보호 구간 247..251 / 537..582 무접촉, 이웃 197/315 · 496(+4)/604). **console/lua 다이제스트 재고정**: `_CONSOLE_LUA_GRANTED_REVISION_DIGESTS` 를 `copilot_responder.lua 615fdf31…` / `PROTOCOL.md 3e97fcda…` 로 갱신하고 grant 문단(동기·가산성·미실증)을 관례대로 기록 — 약화가 아니라 재고정.
- **songcue hunk 핀 (`test_songcue_bundle.py`)** — `git diff 38a6e7e…..HEAD --unified=0 -- server/orchestrator/tools.py` 시작점 65 → **68**(1061·1067·1070 신설, 소실 0), 보호 구간 234..238 / 524..569 무접촉(이웃 184/302 · 483+7/591). 커밋 전에는 `..HEAD` 를 재는 이 검사가 빨갛고(1 failed) 커밋 후 `20 passed` — 파일 주석이 예고한 「커밋 후 다시 돌려라」형태.
- **페이징 회귀 (plan B-5)** — 자식 0개 `state` 회신 바닥 295 → **326 바이트**(실측: cap 300/340/400 모두 326·자식 0·truncated True, cap 1900 은 579·자식 3). `test_payload_size_guard_drops_children_to_fit` 의 합성 예산 300 → 400(자식 1개 411 이라 가드는 여전히 셋 다 떨어뜨림). 페이징 검사(`truncated`/`offset` 계열) 전부 초록.
- **버전 핀 이동 시점** — `VERSION` 과 `EXPECTED_RESPONDER_VERSION` 은 **M1(f7e0285)** 에서 함께 올렸다: `test_responder_roundtrip.py:114` 교차 대조가 M1 부분집합에 들어 있어 한쪽만 올리면 M1 게이트가 빨갛다. M1 부분집합 밖에 있던 `test_responder_deploy.py:177` 의 `"1.6.4"` 리터럴은 전량 실행에서 잡혀 **M2(792593a)** 에서 `"1.6.5"` 로 옮겼다.
- **ruff** — 손댄 Python 9파일(`tools.py`·`musicsync_m3a_probe.py`·`responder_version.py`·`test_lua_responder.py`·`test_overlap_preserve.py`·`test_songcue_tool.py`·`test_musicsync_m3a_probe.py`·`test_songcue_bundle.py`·`test_responder_deploy.py`) `ruff check` → `All checks passed!`, `ruff format --check` → `already formatted`(중간에 `test_musicsync_m3a_probe.py` 1파일을 `ruff format` 으로 정렬).

### E.2.3 실행 결과 (커밋 후, HEAD `792593a`)

```
$ .venv/bin/python -m pytest server/tests/test_lua_responder.py server/tests/test_responder_roundtrip.py server/tests/test_musicsync_m3a_probe.py server/tests/test_songcue_tool.py server/tests/test_overlap_preserve.py server/tests/test_responder_deploy.py -q -p no:cacheprovider
281 passed in 14.59s

$ .venv/bin/python -m pytest server/tests/test_songcue_bundle.py -q -p no:cacheprovider
20 passed in 0.29s

$ .venv/bin/python -m pytest server/tests -q -p no:cacheprovider
11298 passed, 12 skipped, 1 warning in 152.68s (0:02:32)
```

기준 트리(`72e4ca6`, 변경 전) 같은 부분집합 + `test_tree_identity.py`: `238 passed in 18.82s`. 전량 실행의 warning 1건은 `starlette.testclient` 의 기존 DeprecationWarning(이 SPEC 무관, 변경 전과 동일).

### E.2.4 손댄 파일 (총 12, 커밋 2)

- M1 `f7e0285` (6): `console/lua/copilot_responder.lua` · `console/lua/PROTOCOL.md` · `server/safety/responder_version.py` · `server/tests/test_lua_responder.py` · `server/tests/test_overlap_preserve.py` · `.moai/specs/SPEC-COPILOT-POOLEMPTY-001/spec.md`(frontmatter `status: draft → in-progress` 만)
- M2 `792593a` (6): `server/orchestrator/tools.py` · `server/tools/musicsync_m3a_probe.py` · `server/tests/test_songcue_tool.py` · `server/tests/test_musicsync_m3a_probe.py` · `server/tests/test_songcue_bundle.py` · `server/tests/test_responder_deploy.py`
- 손대지 않음(확인): `server/safety/gate.py`(빈 diff) · `server/tests/lua_mock_env.py`(`__NODE` 무수정) · `_free_macro_slot`(plan B-6) · `spec.md`/`plan.md`/`acceptance.md` 본문.

### E.2.5 Gaps (이 회차에 관측하지 않은 것)

- **AC-POOLEMPTY-013 — 실행 안 함(실기).** 운영자가 1.6.5 를 재임포트하고 `DataPool/Timecodes` 를 비운 뒤 ①슬롯 판정 free ②raw `state` 회신의 `"enumeration":"ok"` ③음성 대조군 unknown — M3 운영자 게이트.
- **AC-POOLEMPTY-014 실기 반쪽 — 실행 안 함.** 프로브의 「합계 n / 상한 8」 줄은 실기에서만 나온다. 오프라인 반쪽(발화 지점 grep 0)만 관측.
- **`python -m server.tools.responder_roundtrip --expect-version 1.6.5`** 미실행 — 콘솔 접촉 0 제약. 배치 심판은 M3.
- **커버리지 수치 미측정.** `pytest --cov` 를 돌리지 않았다(과제 지시 명령 밖). 새 코드 경로는 위 AC 검사들이 직접 밟는다(마커 3값 × childCount 0, 다섯 unknown 갈래, 어댑터 3분기).
- **크로스플랫폼** — darwin(arm64)에서만 실행. Lua 5.4 lupa 검사·pytest 를 다른 OS 에서 돌리지 않았다.

### E.2.6 Residual-risk (관측했음에도 남는 것)

- 마커는 **오프라인 실증**뿐이다. 실기 콘솔의 `Children()` 이 죽은 풀에서 실제로 `error()` 를 던지는지, 아니면 빈 테이블/nil 을 조용히 돌려주는지(이 경우 `"ok"` 로 오판) 는 M3 의 음성 대조군이 답한다.
- `server/orchestrator/songcue_timecode.py:16` 독스트링이 옛 이름 `_timecode_slot_verdict` 와 「팩토리 안」 배치를 서술한다 — plan §D 범위 밖 파일이라 손대지 않았다(스테일 서술, 동작 무관). sync 단계 정리 후보.
- `docs/research/ma3-effects/14-musicsync-m3a-timecode-probe*.md` 의 「`_timecode_slot_verdict` 재구현 판정」 줄은 과거 회차 노트 그대로 둔다(역사 기록).
- UDP 예산: `node` 필드 +1 로 첫 창의 자식 수가 한 항목 안팎 줄 수 있다(1900 기본 예산에서는 실측 579 바이트/3자식으로 여유). 24-자식 상한 풀에서의 창 폭은 재지 않았다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-06
run_commit_sha: 792593a            # M2 코드 커밋. M1 은 f7e0285. 이 progress.md 증거 커밋 자체는 pending-backfill(자기 참조)
run_status: implemented-offline    # M1·M2 완료. M3(실기, 운영자 게이트)은 이 회차 범위 밖
ac_pass_count: 13                  # AC-001..012, 015 (오프라인 전부) + AC-014 오프라인 반쪽
ac_fail_count: 0
ac_not_run: [AC-POOLEMPTY-013, AC-POOLEMPTY-014(실기 반쪽)]
preserve_list_post_run_count: 4    # gate.py 빈 diff · lua_mock_env.__NODE 무수정 · _free_macro_slot 무수정 · SPEC 본문 무수정
l44_pre_commit_fetch: "git fetch origin main → origin/main 72e4ca6 == 기준 (0 0 → 착수)"
l44_post_push_fetch: "pending — 푸시는 이 커밋 뒤에 실행; 결과는 완료 보고서에"
new_warnings_or_lints_introduced: 0   # ruff check/format 전부 통과; pytest warning 1건은 기존 starlette DeprecationWarning
cross_platform_build:
  darwin_arm64: "pytest server/tests → 11298 passed, 12 skipped"
  other: not-measured
total_run_phase_files: 12
m1_to_mN_commit_strategy: "마일스톤당 커밋 1(M1 f7e0285 → M2 792593a) + progress.md 증거 커밋 1; --amend/force-push 없음; 명시 pathspec 스테이징"
verification_snapshot_key: "792593a0297663c39e1ea35ca9aa534bdf27abc6:6e340b9cffb37a98"
interpreter: ".venv/bin/python (Python 3.11.15, 워크트리 자체 환경)"
console_writes: 0
```

## §E.4 Sync-phase Audit-Ready Signal

> **부분 sync 다 — 3단계 종결(plan→run→sync)은 M3 실기 뒤로 미룬다.**
> 이 회차가 닫은 것은 **오프라인 M1·M2** 뿐이다. M3 은 운영자 게이트(응답기 1.6.5 재임포트 +
> `DataPool/Timecodes` 비우기)라 실행되지 않았고, 따라서 `AC-POOLEMPTY-013` 과
> `AC-POOLEMPTY-014` 의 실기 반쪽은 **미충족**이다. `status` 를 `completed` 로 올리지 않고
> `in-progress` 로 유지한다 — 실기가 남았는데 닫으면 「잰 것」과 「안 잰 것」이 문서에서 구별되지
> 않는다. M3 회차가 끝나면 그 회차가 §E.4 를 다시 쓰고 종결 전이를 수행한다.

```yaml
sync_status: partial               # M1·M2 오프라인만 닫힘; M3 실기 대기
sync_scope: "CHANGELOG [Unreleased] 항목 1건 + §E.4 (부분 신호)"
sync_complete_at: 2026-09-06
sync_commit_sha: 2fce40d491098e3233c687fa19fbf92b72e41aba   # 부분 sync 커밋; M3 회차가 §E.4 를 다시 쓰면 종결 커밋 SHA 로 갱신
frontmatter_status_transitions:
  spec_md: "in-progress → in-progress (전이 없음 — M3 실기 미실행)"
  plan_md: n/a                     # Tier M plan.md 는 status 프론트매터 없음
  acceptance_md: n/a
  progress_md: n/a
  rationale: "AC-013·AC-014(실기 반쪽) 미충족 — implemented/completed 전이의 전제가 안 섰다"

closed_this_sync:
  - "M1 응답기 열거 마커 (node.enumeration, VERSION 1.6.5)"
  - "M2 앱 판정 조건부 완화 + timecode_slot_verdict 들어올리기 + 프로브 어댑터"
  - "오프라인 AC 13건: AC-POOLEMPTY-001..012, 015"
  - "AC-POOLEMPTY-014 오프라인 반쪽 (발화 지점 순증 0)"

remaining_for_close:
  - "M3 실기 회차 (운영자 게이트: 플러그인 재임포트 + Timecodes 풀 비우기)"
  - "AC-POOLEMPTY-013 — 빈 풀 free + raw 회신의 enumeration:ok + 음성 대조군 unknown"
  - "AC-POOLEMPTY-014 실기 반쪽 — 프로브 「합계 0 / 상한 8」"
  - "docs/research/ma3-effects/ 아래 실기 회차 노트 (명령줄 + 출력 인용)"
  - "그 뒤 §E.4 재작성 + in-progress → implemented → completed 전이"

b12_self_test_a: "grep -c 'POOLEMPTY-001' CHANGELOG.md → 0 (emission 전) → 1 (emission 후). 중복 0"
b12_self_test_b: "acceptance.md 고유 AC-ID 18개 중 3개(AC-006·AC-009·AC-015)는 AC-010 본문의 축약 상호참조; 정본 AC 는 AC-POOLEMPTY-001..015 15건 — §D 표 행수와 일치"
b12_self_test_c: "CHANGELOG 가 지목한 파일 5종 전부 ls 확인 (copilot_responder.lua · PROTOCOL.md · tools.py · musicsync_m3a_probe.py · responder_version.py)"

changelog_entry_position: "[Unreleased] → ### Added → 첫 항목"

spec_lint: "moai spec lint spec.md → 0 error, 1 warning (StatusGitConsistency: frontmatter 'in-progress' vs git-implied 'implemented'). 이 경고는 부분 sync 결정의 **예상된 귀결**이다 — 코드가 머지돼 git 은 implemented 로 읽지만 실기 AC 둘이 미충족이라 프론트매터를 의도적으로 붙잡았다. status 를 올려 경고를 없애는 것은 미검증을 검증으로 보고하는 것이므로 하지 않는다. M3 회차가 해소한다"

mx_scan:
  target: "server/orchestrator/tools.py timecode_slot_verdict (모듈 수준 신설 함수)"
  fan_in_measured: 2
  fan_in_command: "grep -rn 'timecode_slot_verdict' server/ console/ docs/ | grep -v '/tests/'"
  call_sites: ["server/orchestrator/tools.py:2884 (prepare_songcue 핸들러)", "server/tools/musicsync_m3a_probe.py:156 (slot_verdict 어댑터)"]
  verdict: "fan_in 2 < 3 → @MX:ANCHOR 의무 아님. run 단계가 붙인 @MX:NOTE(:1995-2000) 가 이미 두 호출자와 들어올린 근거를 적고 있어 추가 태그 0건"

docs_sync:
  readme_md: "무변경 — 응답기 절이 버전 리터럴을 안 박고 responder_version.py 를 가리킨다"
  console_lua_readme_md: "무변경 — §2.1 재임포트 순서(파일 복사 → 슬롯 삭제 → 재임포트)가 정확하고 --expect-version 은 매개변수형"
  protocol_md: "M1 에서 이미 갱신 (1.6.5 revision note + §4.2 node.enumeration)"
  research_notes: "무변경 — 날짜 붙은 실측 기록이라 고쳐 쓰지 않는다"

console_writes: 0
```
