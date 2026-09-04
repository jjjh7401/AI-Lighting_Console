# SPEC-COPILOT-READBACK-002 — 인수 기준

> 각 항목은 **이진 판정 가능**해야 한다. 부정 대조군이 없는 항목은 통과해도 계기 고장과 구별되지 않는다.
> **전 항목이 오프라인이다.** 이 SPEC 은 콘솔에 쓰지 않고, 라이브 명령도 요구하지 않는다(REQ-READBACK2-013).

## A. 실행 명령

```bash
# 오프라인 — R3 안전 게이트 / 버전 보존 / 배너
uv run pytest server/tests/test_safety_gate.py server/tests/test_safety_lock_monitor.py server/tests/test_deploy_health_ux.py server/tests/test_responder_roundtrip.py -q

# 오프라인 — R3 UI 라벨·가이던스
npm --prefix ui test -- protocol.test.ts

# 오프라인 — R4 타입명 번역 / diff / 시트 / 조회 예산
uv run pytest server/tests/test_prechk_handle_types.py server/tests/test_prechk_inventory.py server/tests/test_vwx_diff.py server/tests/test_vwx_typegap.py server/tests/test_paperwork_patch_sheet.py -q

# 호출자 전수 대조 — AST 로 센다. 줄 경계에 의존하지 않는다 (아래 AC-007 의 계기 주석 참조)
uv run python -c "
import ast
tree = ast.parse(open('server/orchestrator/tools.py').read())
calls = [n for n in ast.walk(tree)
         if isinstance(n, ast.Call)
         and (getattr(n.func, 'id', None) == 'read_inventory'
              or getattr(n.func, 'attr', None) == 'read_inventory')]
withkw = [c for c in calls if any(k.arg == 'type_names' for k in c.keywords)]
print('calls', len(calls), sorted(c.lineno for c in calls))
print('with type_names', len(withkw), sorted(c.lineno for c in withkw))
assert len(calls) == 7, len(calls)
assert len(withkw) == len(calls), sorted(set(c.lineno for c in calls) - set(c.lineno for c in withkw))
print('PASS')
"

# 번역 기계 무변경 확인
git diff --stat origin/main -- server/prechk/ server/vwx/
```

---

## B. R3 — 응답기 버전 게이트

**AC-READBACK2-001** — 버전이 보존된다 ↔ REQ-READBACK2-001
Given 응답기가 `1.6.3` 을 실은 `pong` 을 답하고
When `ConsoleLink.ping()` 을 호출하면
Then 반환값은 여전히 `bool` 이고 `ConsolePort.ping()` 시그니처는 변하지 않았으며, 링크 속성에서 `1.6.3` 을 읽을 수 있다.

**AC-READBACK2-002** — 기대 버전이 소스에 고정된다 ↔ REQ-READBACK2-002
Given 기대 버전 상수가 `server/safety/` 안에 정의돼 있고
When `console/lua/copilot_responder.lua:82` 의 `VERSION` 리터럴과 대조하면
Then 두 값이 같으며, 어긋나면 테스트가 실패한다. **상수는 한 자리에만 있다** — 테스트 리터럴이 두 번째 출처가 되지 않는다.

**AC-READBACK2-003** [부정 대조군] — 낮은 버전이 차단된다 ↔ REQ-READBACK2-003
Given 응답기가 기대보다 낮은 버전(예: `1.6.4` 기대에 `1.6.1`)을 답하고
When 실행 화면 판정을 요청하면
Then `ScreenDecision.cleared` 가 `False` 이고, status 가 버전 불일치 전용 문자열이며(기존 `blocked_responder_degraded` 와 **다른 값**), 감사 기록이 남고, 사용자에게 「응답기 버전 불일치 — 재임포트 필요」 라벨이 도달한다.

**AC-READBACK2-004** [부정 대조군] — 미인식 버전이 낮은 버전과 구별된다 ↔ REQ-READBACK2-004
Given 응답기가 파싱 불가하거나 기대보다 높은 버전 문자열을 답하고
When 판정을 요청하면
Then 차단 사유가 「낮은 버전」과 **다른 값**으로 보고되고, 사용자 가이던스도 재임포트가 아니라 조사를 지시한다.

**AC-READBACK2-005** [부정 대조군] — 오프라인을 가리지 않는다 ↔ REQ-READBACK2-005
Given 콘솔이 오프라인이어서 `ping` 이 타임아웃하고
When 판정을 요청하면
Then status 는 `blocked_console_offline` 이며 버전 사유가 그것을 대체하지 않는다.

**AC-READBACK2-006** — 일치하면 아무 일도 일어나지 않는다 ↔ REQ-READBACK2-003
Given 응답기가 기대 버전과 정확히 같은 값을 답하고
When 판정을 요청하면
Then 기존 동작과 형상·status 모두 동일하다(회귀 없음).

---

## C. R4 — FixtureType 핸들→이름 번역

**AC-READBACK2-007** — 일곱 호출자 전수가 정합한다 ↔ REQ-READBACK2-006
Given §A 의 `ast` 계수 스니펫이 `server/orchestrator/tools.py` 를 파싱해 이름이 `read_inventory` 인 `Call` 노드를 전부 열거하고
When 각 `Call` 의 `keywords` 에 `type_names` 가 있는지 판정하면
Then (a) 호출 노드 수가 **정확히 7** 이고 (b) **전부**가 `type_names` 키워드를 갖는다 — 스니펫이 `PASS` 를 인쇄한다. 열거 수와 전달 수, 그리고 각 호출의 행 번호가 보고서에 나란히 적힌다(수리 전 기준 실측: `calls 7 [3014, 3206, 3397, 4039, 4433, 4624, 6356]` / `with type_names 1 [6356]`).

> **계기 주석 — 왜 grep 이 아니라 AST 인가.** `pyproject.toml:59` 가 `line-length = 100` 이고, 여섯 호출 지점의 현재 폭은 `:3014` 81 · `:3206` 81 · `:3397` 54 · `:4039` 81 · `:4433` 78 · `:4624` 84 다. `, type_names=type_names`(+23)를 더하면 여섯 중 다섯이 상한을 넘어 포매터가 호출을 여러 줄로 쪼갠다. 인자명을 `type_names=names`(+17)로 줄여도 `:4624` 는 101 로 여전히 넘는다. 즉 **한 줄 안에서 `read_inventory(` 와 `type_names=` 를 함께 찾는 grep 은 올바른 구현 뒤에도 7 을 답하지 않는다.** 계기는 줄 경계에 둔감해야 하고, AST 호출 노드 단위 판정이 그 조건을 만족한다.

**AC-READBACK2-008** — VWX diff 가 실제 대수를 센다 ↔ REQ-READBACK2-009
Given 핸들 형태 타입(`FixtureType 12` 등)을 가진 패치된 리그와 그에 대응하는 도면이 있고
When `precheck_vectorworks_diff` 를 실행하면
Then 타입별 `console_count` 가 실제 대수이며 **0 이 아니고**, 대수가 맞는 타입에 대해 `QuantityMismatchEntry` 가 생성되지 않는다.

**AC-READBACK2-009** [부정 대조군] — 번역 실패가 숨지 않는다 ↔ REQ-READBACK2-008
Given 알려진 형태가 아닌 타입 문자열이 섞인 리그가 있고
When 패치 시트를 렌더하면
Then 그 행은 `fixture_type_untranslated` 사실이 **시트 위에 보이게** 인쇄되며, 번역된 행과 시각적으로 구별된다.

**AC-READBACK2-010** — 시트가 이름을 인쇄한다 ↔ REQ-READBACK2-007, REQ-READBACK2-008
Given 타입명 표를 넘겨 만든 패치 시트가 있고
When 렌더 결과를 확인하면
Then `fixture_type` 열에 사람이 읽는 이름이 있고 `FixtureType <숫자>` 형태의 핸들이 남아 있지 않다.

**AC-READBACK2-011** — `build_patch_sheet` 가 스스로 읽지 않는다 ↔ REQ-READBACK2-007
Given 조회를 세는 가짜 포트를 주입하고
When 표를 넘겨 `build_patch_sheet` 를 호출하면
Then 함수 내부에서 발생한 타입 표 조회 횟수는 **0** 이다.

**AC-READBACK2-012** — 번역 기계가 무변경이다 ↔ REQ-READBACK2-010
Given 본 SPEC 의 변경 집합이 있고
When §A 의 `git diff --stat origin/main -- server/prechk/ server/vwx/` 를 실행하면
Then 출력이 **비어 있다** — 두 디렉터리에 변경이 없다.

**AC-READBACK2-013a** [양성] — 조회 증가분이 호출 지점당 정확히 1이다 ↔ REQ-READBACK2-012
Given 조회를 세는 가짜 `state_port` 를 주입하고, 수리 **전** 기준으로 `read_inventory` 호출 지점 하나(fixture-type 루트를 스스로 읽지 않는 지점 — 측정 기준 `tools.py:3206` `precheck_vectorworks_diff` · `:3397` `apply_vectorworks_patch` · `:4039` `resolve_patch_address`)의 `query_state` 호출 횟수 N 을 기록하고
When 수리 후 같은 툴을 같은 인자로 실행하면
Then 그 호출 지점의 `query_state` 횟수는 **정확히 N+1** 이며, 늘어난 1회의 경로가 fixture-type 목록 조회(`read_fixture_type_names`)임이 가짜 포트의 조회 로그(질의 경로 기록)로 확인된다. **N+2 이상은 실패다.**
**기준 N 의 보관처**: 세 지점의 수리 전 N 은 RED 단계에서 측정해 `progress.md` §E.2 의 조회 계수표(지점 · 수리 전 N · 수리 후 · 증가분 · 늘어난 경로 열)에 리터럴로 기록하고, 검증 시점에는 그 표의 값을 인용한다 — 기억된 숫자는 기준이 아니다(VCI §2 귀속 요건).

**AC-READBACK2-013b** [부정 대조군] — 상한이 초과되지 않는다 ↔ REQ-READBACK2-012
Given 같은 조회 계수 포트를 주입하고, **두 `read_inventory` 호출을 한 번에 덮는** `patch_fixtures` 핸들러(`tools.py:4433`·`:4624` — 같은 핸들러의 같은 호출)를 고르고
When 그 핸들러를 같은 인자로 한 번 실행해 수리 전후의 `query_state` 횟수를 대조하면
Then 증가분이 **1을 넘지 않으며**(**N+2 는 FAIL**), 조회 로그에 fixture-type 목록 조회(`read_fixture_type_names`) 경로가 **정확히 한 번만** 나타난다 — 두 자리가 같은 이름 표를 나눠 쓰기 때문이다. 이 대조군이 없으면 「호출 지점당 1회」를 「자리마다 한 번씩」으로 읽어 한 핸들러에서 조회가 두 번 늘어난 것이 통과한다.

> **이 대조군은 증가 0 을 요구하지 않는다.** `TypeModeRead`(`server/prechk/mode_read.py`)는 `attempted`/`type_found`/`modes`/`detail` 만, `WalkOutcome`(`server/prechk/footprint.py`)은 `queried_paths` 로 경로 문자열만 반환하므로, 기존 루트 판독을 (슬롯, 이름) 표로 재사용하려면 `server/prechk/**` 를 고쳐야 한다 — REQ-READBACK2-010 이 금지하고 AC-READBACK2-012 가 빈 diff 로 기계 판정하는 바로 그 변경이다. 따라서 「증가 0」은 이 SPEC 의 무변경 제약 아래에서 **도달 불가능**하며, 올바른 구현을 떨어뜨리는 계기가 된다. 여기서 재는 것은 재사용 여부가 아니라 **상한 초과 여부**다.

---

## D. 횡단 — 쓰기 예산과 증거

**AC-READBACK2-014** [부정 대조군] — 콘솔 쓰기 총계가 0이다 ↔ REQ-READBACK2-013
Given 본 SPEC 의 전 작업이 끝났고
When 두 계기를 함께 확인하면 — **(a) 오프라인**: 전 테스트에서 주입한 `FakeConsole` 의 `executed` 리스트(`server/tests/test_safety_gate.py:30-57`, `execute()` 가 호출마다 명령을 여기 append 한다). **(b) 라이브 세션**: `server/audit_logs/audit-*.jsonl`(감사 기록기 `server/safety/audit.py:35` `DEFAULT_AUDIT_DIR`, 기록 함수 `:269` `kind` 기본값 `"command"`)에서 본 SPEC 작업 구간의 `kind:"command"` 행
Then (a) 모든 `FakeConsole.executed` 가 **빈 리스트**이고, (b) 본 SPEC 의 코드 경로에 귀속되는 `kind:"command"` 행이 **0건**이다. 읽기 조회조차 구현 구간에는 필요 없다 — 모든 AC 가 오프라인 테스트와 가짜 포트로 판정된다. 두 계기의 실제 출력(리스트 내용과 `jq` 필터 결과)을 보고서에 인용한다.

**AC-READBACK2-015** — 완료 보고가 5절 형식을 갖춘다 ↔ REQ-READBACK2-014, REQ-READBACK2-011, REQ-READBACK2-012
Given 본 SPEC 의 완료 보고가 작성됐고
When 그 보고를 확인하면
Then 주장·증거(명령과 그 출력)·기준 귀속·**미검증**·잔여 위험 다섯 절이 모두 있고, 미검증 절에 최소한 REQ-READBACK2-011(제3 핸들 형태)이 명시돼 있으며, 호출 지점별 조회 증가분(REQ-READBACK2-012)이 여섯 자리 전부에 대해 계상돼 있고, **증거 절 어디에도 `exec: ok` 가 효과의 근거로 인용돼 있지 않다.**

---

## E. 완료 정의 (Definition of Done)

- [ ] §A 오프라인 명령 전부 초록, 출력 그대로 인용.
- [ ] AC-READBACK2-001~006 통과 (부정 대조군 3종 포함).
- [ ] AC-READBACK2-007~012 통과, §A `ast` 스니펫이 `calls 7` / `with type_names 7` / `PASS` 를 인쇄한 출력 그대로가 보고서에 적힘 (줄 단위 grep 수치는 인용하지 않는다 — 포매터가 호출을 쪼개므로 그 수는 의미가 없다).
- [ ] AC-READBACK2-013a·013b 통과, 조회 증가분이 호출 지점 여섯 자리 전부에 대해 `progress.md` §E.2 조회 계수표와 보고서에 계상됨. 재사용하지 않은 자리는 그 사유가 함께 적힘.
- [ ] 콘솔 쓰기 0건 — `FakeConsole.executed` 전부 빈 리스트 + `audit-*.jsonl` 의 `kind:"command"` 귀속 행 0건 (AC-READBACK2-014).
- [ ] 완료 보고 5절, 미검증 절에 제3 핸들 형태가 명시됨 (AC-READBACK2-015).

---

## F. 커버리지 표 (REQ → AC)

> **개수와 하위 ID 표기**: 이 SPEC 은 REQ **14건**(REQ-READBACK2-001~014 연속)과 AC **16건**을 갖는다. AC 번호는 `AC-READBACK2-001`~`015` 이며 그중 **`013a`·`013b` 만이 하위 ID** 다 — 조회 예산의 양성(지점당 정확히 N+1)과 상한 초과 부정 대조군(한 핸들러에서 N+2 → FAIL)이 한 기준의 두 팔이라 번호를 갈랐다. 따라서 AC 실개수는 `001~012`(12) + `013a`·`013b`(2) + `014`·`015`(2) = **16** 이다. 013 번대에는 접미사 없는 형태가 없고 두 하위 ID 만 존재한다 — 접미사를 뗀 이름은 이 문서 어디에도 정의돼 있지 않으므로, AC 를 세는 grep 은 그 이름을 만나지 않는다. 14개 REQ 전부가 최소 1개의 AC 를 갖고, 역방향(AC → REQ)은 각 AC 제목 끝의 `↔` 표기가 답한다.

| REQ | 요지 | 검증 AC |
|---|---|---|
| REQ-READBACK2-001 | `pong` 의 `version` 보존 · `ConsolePort.ping()` 시그니처 무변경 | AC-READBACK2-001 |
| REQ-READBACK2-002 | 기대 버전 단일 상수 · `copilot_responder.lua:82` 에 고정 | AC-READBACK2-002 |
| REQ-READBACK2-003 | 버전 불일치 → 자체 status 차단 판정 (`_check_health` 분기) | AC-READBACK2-003 · 006 |
| REQ-READBACK2-004 | 낮은 버전 / 미인식 버전 구별 보고 | AC-READBACK2-004 |
| REQ-READBACK2-005 | 오프라인 차단을 가리지 않음 | AC-READBACK2-005 |
| REQ-READBACK2-006 | 여섯 호출 지점이 `type_names=` 전달 | AC-READBACK2-007 |
| REQ-READBACK2-007 | `build_patch_sheet` 는 매개변수로 받고 자체 조회 없음 | AC-READBACK2-010 · 011 |
| REQ-READBACK2-008 | 렌더러가 `fixture_type_untranslated` 표면화 | AC-READBACK2-009 · 010 |
| REQ-READBACK2-009 | VWX diff 가 타입별 실제 대수 보고 | AC-READBACK2-008 |
| REQ-READBACK2-010 | `prechk`/`vwx` 번역 기계 무변경 | AC-READBACK2-012 |
| REQ-READBACK2-011 | 제3 핸들 형태 구멍을 열어 두고 명시 | AC-READBACK2-015 |
| REQ-READBACK2-012 | 호출 지점당 추가 `query_state` 최대 1회 · 스코프 안 이름 표 재사용(기존 루트 판독 재사용은 허용이지 의무 아님) | AC-READBACK2-013a · 013b · 015 |
| REQ-READBACK2-013 | 콘솔 쓰기 총계 0 | AC-READBACK2-014 |
| REQ-READBACK2-014 | 완료 보고 5절 형식 · `exec: ok` 를 효과의 증거로 인용 금지 | AC-READBACK2-015 |
