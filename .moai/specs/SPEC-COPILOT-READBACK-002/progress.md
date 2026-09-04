# SPEC-COPILOT-READBACK-002 — 진행 기록

> 단계별 증거를 적는 자리. plan 단계는 §E.1 만 채우고 §E.2~§E.4 는 각 단계의 소유자가 채운다.

## §E.1 Plan-phase Audit-Ready Signal

- SPEC 작성 완료 2026-09-03 — `spec.md` · `plan.md` · `acceptance.md` (Tier M) + `research.md`(포인터 문서).
- SPEC ID 정규식 검사: `[[ "SPEC-COPILOT-READBACK-002" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` → `PASS`.
- **신설 경위**: SPEC-COPILOT-READBACK-001 v0.1.1 이 REQ 32 / AC 33 으로 Tier M 예산(각 16)의 2배를 넘었고(plan-audit iteration 2 D11, PASS 0.925), 감독이 2026-09-03 에 두 Tier M SPEC 으로 분할을 결정했다. 본 SPEC 은 **R3(런타임 응답기 버전 게이트) + R4(FixtureType 핸들→이름 번역)** 를 이관받았다. 분할선은 원본 `plan.md` 가 이미 「순수 서버 · 병렬 가능」으로 떼어 둔 자리 그대로다.
- **예산**: REQ **14건**(REQ-READBACK2-001~014) / AC **16건**(AC-READBACK2-001~015, `013a`·`013b` 가 유일한 하위 ID). 둘 다 Tier M 상한 16 이하.
- **번호 대응(옛 → 새)**: 옛 REQ-READBACK-015~019 → REQ-READBACK2-001~005 · 옛 021~027 → REQ-READBACK2-006~012 · 옛 020(R3 쓰기 0) 은 SPEC 전역 쓰기 0 인 REQ-READBACK2-013 으로 확장 흡수 · 옛 030+031(5절 형식 + `exec: ok` 금지)은 REQ-READBACK2-014 로 병합. AC 는 옛 015~020 → 001~006 · 옛 021~026 → 007~012(순서는 §C 흐름에 맞춰 재배열, `↔` 표기가 정본) · 옛 027a/027b → 013a/013b · 쓰기 0 대조군 AC-014 신설 · 옛 030 → 015.
- **이관된 계획 산출물 2건**: 옛 `plan.md §B B5`(조회 예산 실측표 — 여섯 호출 지점의 fixture-type 루트 보유 여부, 예 3 / 아니오 3, 다섯 핸들러)와 옛 `plan.md §C C-1`(응답기 버전 불일치의 자체 health state 결정, 2026-09-03)이 본 SPEC `plan.md` §B·§C 로 옮겨졌다. 001 쪽에는 포인터만 남았다.
- **D12 잔존 산출물 주어 해소**: 옛 REQ-016 `the 저장소` → **`the 안전 모듈(server/safety/)`**(REQ-READBACK2-002). 옛 REQ-030/031 은 **`the 완료 보고 작성자`**(REQ-READBACK2-014)로, 쓰기 금지는 **`the 본 SPEC 의 구현자`**(REQ-READBACK2-013)로 행위자가 세워졌다.
- **D13 하위 ID 설명**: `acceptance.md §F` 도입문이 REQ 14 / AC 16 의 개수와 `013a`·`013b` 가 유일한 하위 ID 라는 사실, 그리고 `AC-READBACK2-013`(하위 ID 없는 형태)이 존재하지 않는다는 사실을 적는다.
- **코드 좌표 실측 확인(2026-09-03, HEAD `adae0ac`)**: `console.py:297-307` 이 payload 를 버리고 `bool` 만 반환 · `copilot_responder.lua:82` `VERSION = "1.6.3"` · `gate.py:415-437` `_check_health` 의 오프라인/저하 2분기 · `gate.py:429` `_audit.log_blocked` · `gate.py:546-557` 전송 시점 재검사 · `read_inventory` 호출 7건 중 `type_names=` 는 `tools.py:6356` 하나뿐(나머지 `:3014, 3206, 3397, 4039, 4433, 4624`) · `tools.py:6326` `types_root` → `:6352` `read_fixture_type_names` · 핸들러 `def` 6건의 행 번호(3001 · 3182 · 3373 · 4009 · 4242 · 6188) · `tools.py:3046-3055` `walk_mode_widths` · `:4295-4298` `read_type_mode_widths` · `render.py:87` `escape(row.fixture_type or '')` · `diff.py:150` `found` 검사 · `:179-185` 매칭 · `:188-192` `QuantityMismatchEntry` · `inventory.py:111` `HANDLE_TEXT` · `:147-181` `translate_fixture_type` · `:469-473` 비준 문면 · `:479-485` 제3 형태 문면 · `:529-534` `read_inventory` 시그니처의 `type_names` kwarg · `mode_read.py:138-144` "Query count is 1" · `footprint.py:254` `query_state` · `web/PROTOCOL.md:57` `health` enum · `ui/src/protocol.ts:1192-1205` 라벨/가이던스 · `ui/src/protocol.test.ts:185-190` 라벨 단언.
  - **(0.1.1 만료 고지)** 위 목록의 앵커 넷은 범위 끝단이 어긋나 있었다 — `inventory.py:147-181`(본문은 **180** 에서 끝, 181 은 빈 줄) · `ui/src/protocol.ts:1192-1205`(라벨+가이던스 구역은 **1190-1207**, `HEALTH_LABELS` 선언 1190 이 인용 밖) · 그리고 `gate.py:419` 로 인용됐던 `blocked_console_offline` 리터럴은 **420**(419 는 분기 조건) · `test_overlap_preserve.py:227-231` → 다이제스트 사전은 **227-230**. 이 줄은 0.1.0 시점의 기록이므로 그대로 두고, **정본은 `spec.md`·`plan.md` 본문의 정정된 값**이다(plan-audit D5·D6, 재실측 HEAD `adae0ac`).
- **정정 2건(원본 문서 대비)**: `build_patch_sheet` 범위 `data.py:82-147` → **`:82-143`**(147행은 함수 밖 빈 줄과 구획 주석). `fuzzy_type_equal` 은 `diff.py` 에 정의된 것이 아니라 **`server/vwx/rig.py:58`** 정의이고 `diff.py:180` 에서 쓰인다 — REQ-READBACK2-010 의 「`server/vwx/**` 무변경」은 두 파일 모두를 덮으므로 결론은 바뀌지 않는다.
- **0.1.1 개정(2026-09-03)** — plan-audit iteration 1 은 **FAIL 0.75**(must-pass 7/7 통과, Testability 0.50)였다. 떨어진 원인은 요구층이 아니라 **검증층의 계기 두 개**이며 D1~D6 을 반영했다. 핵심은 D1 — REQ-READBACK2-012 가 `:3014`·`:4433`·`:4624` 에 걸었던 「기존 루트 판독 재사용 · 증가 0」 의무가 이 SPEC 자신의 `server/prechk/**` 무변경 제약(REQ-READBACK2-010) 아래에서 **도달 불가능**했다는 실측이다(`TypeModeRead`·`WalkOutcome` 둘 다 (슬롯, 이름) 쌍을 반환하지 않는다). 재사용은 허용으로 낮추고, AC-013b 는 「증가 0」에서 **상한 초과 부정 대조군(N+2 → FAIL)**으로 바꿨다. D2 는 AC-007 의 계기를 grep 에서 `ast` 호출 계수로 교체했고(포매터가 다섯 자리를 쪼갠다), D3 은 AC-014 에 `FakeConsole.executed` + `server/audit_logs/audit-*.jsonl` 경로를 적었고, D4 는 기준 N 의 보관처를 아래 §E.2 로 지정했다. D5·D6 앵커 4건 정정. REQ 14 / AC 16 불변.
- **미검증**: 라이브 응답기 버전(본 SPEC 은 탐지 기계만 만들고 재지 않는다 — 라이브 판독은 SPEC-COPILOT-READBACK-001 M3 소유) · ~~조회 재사용이 `walk_mode_widths` 경로에서 배관 가능한지~~ → **0.1.1 에서 측정됨: 불가능**(§B B4 — `TypeModeRead`·`WalkOutcome` 이 (슬롯, 이름) 쌍을 반환하지 않는다). 이 항목은 미검증에서 내려간다 · 미관측 제3 핸들 형태의 존재 여부(REQ-READBACK2-011 이 구멍으로 열어 둔다) · **포매터 실제 출력**(D2 의 근거는 `wc -c` 실측 폭 + `pyproject.toml:59` 설정 상한이지 `ruff format` 출력이 아니다 — 수리 시 실행해 확인한다).

## §E.2 Run-phase Evidence

### M0 — R3 응답기 버전 게이트 (2026-09-04, 워크트리 `readback002`, 브랜치 `WT-readback-gate`, base `2488336`)

> M1(R4 `type_names=` 배관 · AC-READBACK2-007~013b)은 **다른 위임이 소유**한다. 아래 표는 M0 이 소유한 AC-READBACK2-001~006 만 판정하며, AC-013a·013b 의 조회 계수표는 M1 이 이 절에 덧붙인다.

**기준 귀속**: 아래 모든 출력은 base `2488336`(== `origin/main`) 위 이 워크트리에서 이 회차에 실행된 것이다. 착수 전 기준 측정은 위임이 지정한 네 파일 `77 passed in 16.92s` 와 `npm --prefix ui test -- protocol.test.ts` → `Tests 109 passed (109)` 이며 **사전 실패는 0건**이었다. 수리 후 같은 계기가 각각 `150 passed`(테스트 파일 1개 추가 포함) 와 `115 passed` 를 답한다.

| AC | 판정 | 검증 명령 | 실측 출력 |
|---|---|---|---|
| AC-READBACK2-001 (version 보존 · `ping()` 시그니처 무변경) | **PASS** | `uv run pytest server/tests/test_safety_console.py::TestPingAndState -q` | `TestPingAndState` 전건 통과. `test_ping_preserves_the_reported_version_without_widening_the_port` 가 (a) `link.ping() is True` 이고 `isinstance(result, bool)`, (b) `link.responder_version == "1.6.1"`, (c) `list(inspect.signature(ConsolePort.ping).parameters) == ["self"]` 를 함께 단언 |
| AC-READBACK2-002 (기대 버전 단일 상수 · Lua 고정) | **PASS** | `uv run pytest server/tests/test_responder_roundtrip.py::TestExpectedVersionIsPinnedToTheResponder -q` | `2 passed`. 테스트가 `console/lua/copilot_responder.lua` 에서 `VERSION` 리터럴을 정규식으로 **1건만** 읽어 `EXPECTED_RESPONDER_VERSION` 과 대조하며, 두 번째 테스트는 `server/safety/**.py` 중 그 문자열을 담은 파일이 `["responder_version.py"]` 뿐임을 단언 |
| AC-READBACK2-003 [부정 대조군] (낮은 버전 차단) | **PASS** | `uv run pytest server/tests/test_safety_gate.py::TestResponderVersionGate -q` | `cleared is False` · `status == "blocked_responder_version_mismatch"`(≠ `blocked_responder_degraded`) · `notice` 에 `"1.6.1"` 과 `"재임포트"` · `_events(audit, "blocked")` 1건이며 그 `reason` 에 `"1.6.1"` · `gate.status["health"] == "responder_version_mismatch"` · `console.executed == []` |
| AC-READBACK2-004 [부정 대조군] (미인식 ≠ 낮은 버전) | **PASS** | 같은 명령 + `uv run pytest server/tests/test_safety_lock_monitor.py::TestVersionClassification -q` | 높은 버전(`9.9.9`)·파싱 불가(`dev-build`) 모두 `blocked_responder_version_unrecognized` 이고 `!= blocked_responder_version_mismatch`, `notice` 에 `"재임포트"` **없음**. 분류 술어는 낮음·같음·높음·파싱 불가·빈 문자열·공백·부재 **14 케이스**를 파라메트라이즈해 이진 판정 |
| AC-READBACK2-005 [부정 대조군] (오프라인 비가림) | **PASS** | 같은 명령 + `::TestHealthMonitorVersionStates` | 버전 불일치가 먼저 성립한 뒤 활동 창(15s)을 넘긴 침묵 → `status == "blocked_console_offline"`, `notice` 에 `"version"`·`"버전"`·`"재임포트"` **없음**. 창 **안**의 침묵은 `responder_degraded` (성공한 ping 자체가 콘솔 트래픽이므로) — 어느 쪽이든 버전 상태는 남지 않는다 |
| AC-READBACK2-006 (일치 시 무회귀) | **PASS** | 같은 명령 + `uv run pytest server/tests -q` | `cleared is True` · `status == "cleared"` · `health == "online"` · `_events(audit, "blocked") == []`. **행동 회귀 0건**: 커밋 후 전체 스위트 `10948 passed, 3 failed, 12 skipped` 이고 그 3건은 전부 `TestSafetyChokepointFileSet`(아래 「미해결 차단」) — 즉 범위 핀이며 응답기·게이트 행동 테스트는 하나도 깨지지 않았다. 커밋 **전** 실행은 `10951 passed` 였는데, 그 차이는 코드가 아니라 그 핀이 `BASE..HEAD` 를 diff 한다는 계기 성질에서 온다 |

**오프라인 명령 전문 (acceptance.md §A)**

```
$ uv run pytest server/tests/test_safety_gate.py server/tests/test_safety_lock_monitor.py \
    server/tests/test_deploy_health_ux.py server/tests/test_responder_roundtrip.py \
    server/tests/test_safety_console.py -q
150 passed in 15.12s

$ npm --prefix ui test -- protocol.test.ts
 Test Files  1 passed (1)
      Tests  115 passed (115)

$ uv run pytest server/tests -q
10951 passed, 12 skipped, 1 warning in 146.71s

$ cd ui && npx tsc --noEmit ; npm test
tsc exit=0
 Test Files  21 passed (21)
      Tests  506 passed (506)

$ uv run ruff check server/ ; uv run ruff format --check server/ ui/
All checks passed!
483 files already formatted
```

**콘솔 쓰기 0 (AC-READBACK2-014 의 M0 몫)**

- 오프라인: 새 테스트 전부가 `assert console.executed == []` 를 싣는다(`test_safety_gate.py` 의 `TestResponderVersionGate` 6개 지점 — 400·413·424·448·491·507·518·537·551·561 행대). 진단 명령 `git diff 2488336 | grep -nE "^\+.*(\.execute\(|\.deploy_plugin\(|send_command|Cmd\()"` → `NONE`.
- 라이브: 본 회차는 라이브 세션을 열지 않았다. `server/audit_logs/audit-20260904.jsonl` 4행 전수 판독 결과 `kind` 는 전부 `backup` 이고 `kind:"command"` 는 **0건**이다. 다만 이 파일은 git 추적 대상이 아니어서 본 회차 귀속 여부를 이 계기로는 가릴 수 없다 — 「내 회차가 0건」의 증거는 위 diff grep 쪽이다.

**뮤테이션 7/7 (구현을 일부러 깨서 각 테스트가 RED 가 되는지 확인)**

| # | 뮤테이션 | RED 결과 |
|---|---|---|
| 1 | `VERSION_LOW → RESPONDER_DEGRADED` (§C C-1 이 기각한 재사용안) | 4 failed |
| 2 | `VERSION_UNRECOGNIZED → RESPONDER_VERSION_MISMATCH` (두 팔 붕괴) | 5 failed |
| 3 | `note_ping_timeout` 이 버전 상태를 보존 (오프라인 가림) | 2 failed |
| 4 | 일치하는 버전을 `VERSION_LOW` 로 판정 | 6 failed |
| 5 | `ping` 이 다시 payload 의 `version` 을 폐기 | 1 failed |
| 6 | 상수를 `1.6.2` 로 드리프트 | 1 failed |
| 7 | UI 라벨 매핑 2건 삭제 (배너가 원문 status 노출) | 2 failed |

복원 뒤 재확인: `150 passed` / `115 passed`.

**RED 증거 (구현 전, TDD)**

```
E   ModuleNotFoundError: No module named 'server.safety.responder_version'
ERROR server/tests/test_safety_gate.py
ERROR server/tests/test_safety_lock_monitor.py
ERROR server/tests/test_deploy_health_ux.py
ERROR server/tests/test_responder_roundtrip.py
4 errors in 0.32s

# UI 절반
 × responder version health states > labels a low responder version with the re-import instruction
 × responder version health states > labels an unrecognized version differently from a low one
 × responder version health states > directs a low version to re-import
 × responder version health states > directs an unrecognized version to investigate, NOT to re-import
      Tests  4 failed | 111 passed (115)
```

**설계 결정 2건 (SPEC 이 지정하지 않아 구현이 정한 것)**

1. **`version` 부재(`None`)는 차단하지 않는다.** `pong` 에 `version` 이 없는 회신은 이 저장소의 오프라인 하네스가 실제로 보내는 형태다(2026-09-04 실측: `test_safety_console.py` `_echo_send`, `test_responder_import_gate.py:70`, `test_deploy_transport.py:262`, `test_safety_e2e_audit.py:75`). 이 채널로는 「버전 없는 응답기」와 「버전을 재지 않는 호출자」를 구별할 수 없으므로, 구별 불가를 차단 사유로 쓰지 않는다. 열린 구멍으로 §E.2 미검증에 적는다.
2. **게이트는 `ConsolePort` 를 넓히지 않고 `getattr(self._console, "responder_version", None)` 로 읽는다.** `ping() -> bool` 시그니처 무변경 제약(REQ-READBACK2-001)과 「버전이 게이트에 도달해야 한다」를 동시에 만족시키는 자리다. 속성이 없는 가짜 포트도 그대로 돌아간다는 것을 별도 테스트로 단언했다.

**계획 대비 파일 1건 추가**: `server/tests/test_safety_console.py`. plan.md §E M0 의 테스트 파일 목록 4건에는 없지만, AC-READBACK2-001 이 재는 대상은 `ConsoleLink.ping` 이고 그 테스트 홈이 이 파일이다. 범위 봉투(`server/safety/` + 그 테스트) 안이며 금지 경로가 아니다.

**미해결 차단 1건 — 안전 초크포인트 파일 집합 핀 (`test_overlap_preserve.py::TestSafetyChokepointFileSet`, 3건 FAIL)**

M0 의 커밋이 `server/safety/` 의 **고정된 변경 집합 핀**을 넓혔고, 그 핀은 설계상 **명시적 승인**을 요구한다. 자체 승인하지 않고 차단으로 올린다.

계기: `_SAFETY_EXPECTED_DELETIONS` / `_SAFETY_ALLOWED_DELETED_LINES`(`server/tests/test_overlap_preserve.py:319-325` 및 그 위 주석 `:286-318`). 기준 `_PRECHK_BASE = 95687a0e`.

실측 (`git diff --numstat 95687a0e..HEAD -- server/safety/`):

| 파일 | 핀 (삭제행) | 현재 | 성격 |
|---|---|---|---|
| `server/safety/console.py` | 57 | **59** | 내 변경이 2행 삭제 |
| `server/safety/gate.py` | 6 | **8** | 내 변경이 2행 삭제 |
| `server/safety/monitor.py` | (행 없음) | **3** | **새 행** |
| `server/safety/responder_version.py` | (행 없음) | **0** | **새 행** (신규 파일) |
| audit.py · backup.py · blacklist.yaml | 10 · 2 · 1 | 동일 | 무변경 |

내 변경이 삭제한 6행 전문 (`git diff --unified=0 2488336..HEAD`):

```
console.py  -        """Responder heartbeat; updates the health monitor when attached."""
console.py  -            self._monitor.note_ping_success()
gate.py     -        """Probe the responder once; audited; returns the resulting health state."""
gate.py     -            self.monitor.note_ping_success()
monitor.py  -    def note_ping_success(self) -> None:
monitor.py  -        """A responder heartbeat answered — the full path is healthy."""
monitor.py  -        self._state = self.ONLINE
```

**기준 확인**: 이 핀은 base `2488336` 에서 **정확히 초록**이었다(`git diff --numstat 95687a0e..2488336 -- server/safety/` 가 핀 5행과 일치). 즉 이 3건은 내 변경이 만든 것이며 사전 실패가 아니다.

**왜 자체 승인하지 않는가**: 핀 위 주석이 성장 이력을 「granted exception」으로 기록하고 한 건을 **"User-approved after the alternatives were searched and rejected"** 로 적으며, 「Another file under the chokepoint … still fails the gate」라고 못박는다. 내 변경은 **파일 2개 추가 + 삭제 계수 2건 상향 + 핀 텍스트 6행 추가**로, 기존 어떤 grant 보다 넓다. 여기에 이 SPEC 이 답을 갖고 있지 않은 교차 소유권 질문이 겹친다 — 같은 주석이 **「WRITEGATE-001 owns `server/safety/`」** 라고 적는데, 본 SPEC 의 `plan.md §E M0` 표는 `console.py`·`gate.py`·`monitor.py` + `server/safety/` 신규 상수를 M0 의 산출물로 명시한다. 어느 쪽이 이기는지는 감독/오케스트레이터 결정이다.

**필요한 결정**: (a) 핀을 넓히고 사유를 주석에 기록한다(위 6행 + 2개 행 추가), (b) 상수를 `server/safety/` 밖으로 옮겨 신규 행 1개를 없앤다(단 `monitor.py`·`console.py`·`gate.py` 행은 남는다 — 버전 게이트는 원리적으로 초크포인트를 건드린다), (c) WRITEGATE-001 소유로 이관한다.

**계기의 사각**: 이 핀은 `BASE..HEAD` 를 diff 하므로 **커밋 전 테스트 실행에는 보이지 않는다.** 회차 중 커밋 전 전체 스위트가 `10951 passed` 로 초록이었던 것은 참이지만, 이 가드에 대해서는 구조적으로 눈이 먼 관측이었다. 커밋 후 전체 스위트가 `10948 passed, 3 failed` 다.

**미검증 (M0)**

- **라이브 응답기 버전** — 본 회차는 콘솔에 접촉하지 않았다. 만든 것은 **탐지 기계**이고, 라이브가 실제로 1.6.1 인지 1.6.3 인지는 재지 않았다(B2 · SPEC-COPILOT-READBACK-001 M3 소유).
- **`version` 부재 갈래의 실기 빈도** — 오프라인 하네스가 그 형태를 보낸다는 것은 실측했으나, 라이브 응답기가 `version` 을 빠뜨리는 경우가 실제로 있는지는 재지 않았다. 위 설계 결정 1 은 그 미측정 위에 서 있다.
- **제3 핸들 형태**(REQ-READBACK2-011) — M1 소유이며 M0 에서 재지 않았다.
- **전체 스위트의 착수 전 기준** — 착수 전 기준은 위임이 지정한 네 파일 + UI 에 대해서만 측정했다. 전체 스위트(10951건)의 사전 기준은 재지 않았으므로, 「전체 초록」은 변경 **후** 관측이다. 회차 중 관측된 실패 2건(`test_overlap_preserve.py` 의 ruff 검사 2건)은 내가 만든 미포맷 파일 2개가 원인임을 확인하고 포맷으로 해소했다.
- **`_console_input` 프로브 경로** — 두 버전 상태는 `console_offline` 이 아니므로 프로브를 타지 않는다(설계대로). 이 상태에서 `console_input` 이 `undetermined` 로 나가는 것이 UI 에 어떻게 보이는지는 실기로 재지 않았다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_phase: M0
run_complete_at: 2026-09-04T01:52:00Z
run_commit_sha: 019399b
run_status: ac-pass-with-blocker   # AC-001..006 전부 PASS · 초크포인트 핀 승인 1건 미해결
ac_scope: AC-READBACK2-001..006   # M1 이 007..013b 를 별도로 계상한다
ac_pass_count: 6
ac_fail_count: 0
preserve_list_post_run_count: 0   # server/prechk/ · server/vwx/ · console/lua/ · server/lxseq/ · server/orchestrator/ · server/paperwork/ · server/web/presets_api.py 전부 빈 diff
console_writes: 0
mutation_checks: 7/7 red
new_warnings_or_lints_introduced: 0   # ruff check 통과 · ruff format 통과 · tsc exit 0
open_blockers: 1   # test_overlap_preserve.py::TestSafetyChokepointFileSet 3 FAIL — §E.2 「미해결 차단」 참조
full_suite_post_commit: 10948 passed / 3 failed / 12 skipped
total_run_phase_files: 13   # 신규 1 + 수정 12 (progress.md · spec.md frontmatter 제외)
m1_to_mN_commit_strategy: M0 단일 커밋 + SHA 백필 커밋 1건. 푸시는 오케스트레이터 소유.
l44_pre_commit_fetch: not-run   # 격리 워크트리 · 브랜치 WT-readback-gate 는 원격에 없다
l44_post_push_fetch: not-run    # 푸시하지 않았다
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## Plan Audit-Ready Signal

- plan_complete_at: 2026-09-04T00:45:29Z
- plan_status: audit-ready
- plan_audit: PASS 0.92 (iteration 2, .moai/reports/plan-audit/SPEC-COPILOT-READBACK-002-review-2.md) · 잔존 optional 3건(D7 재사용 경로 도달 · D8 앵커 1행 · D9 AC-009 문자열 술어)은 run 단계 소유
