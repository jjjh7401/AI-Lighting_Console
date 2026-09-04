# SPEC-COPILOT-READBACK-002 — 구현 계획

> 정본은 `spec.md`. 이 문서는 **되돌리기 어려운 결정을 먼저** 놓고 기계적인 작업을 뒤로 미룬 실행 순서다.
> 기준 트리 `origin/main adae0ac` · 조사 근거 `../SPEC-COPILOT-READBACK-001/research.md` §R3·§R4 · 개발 방식 TDD.
> REQ 번호는 spec.md 0.1.1 의 연속 번호(REQ-READBACK2-001~014)를 따른다.

## A. 맥락

두 요구는 **둘 다 순수 서버**이고 **둘 다 되돌릴 수 있다.** 그래서 마일스톤 순서를 정하는 축은 위험도가 아니라 **결정의 되돌리기 난이도**다.

R3 은 **쇼를 멈출 수 있는 판정을 신설**한다 — 버전이 어긋나면 실행 화면이 차단된다. 그 차단이 어떤 이름과 어떤 배너를 갖는지는 UI 와 프로토콜 문서까지 파급되므로, 결정이 굳으면 되돌리는 비용이 코드보다 크다. 그래서 R3 이 먼저다.

R4 는 인자 하나를 여섯 자리에 넘기는 배관이고, 파급이 서버 안에서 닫힌다. 다만 **조회 예산**이라는 비준된 제약을 건드리므로 착수 전에 여섯 자리를 실측해 두었다(§B B5).

**SPEC-COPILOT-READBACK-001(R1+R2)과 병렬로 진행할 수 있다.** 파일 집합이 겹치지 않고, 본 SPEC 은 1.6.4 배포를 기다리지 않는다 — 버전 게이트는 기대 상수가 `1.6.3` 이든 `1.6.4` 든 동일하게 동작한다.

## B. 알려진 문제 (착수 전 재측정 대상)

| # | 항목 | 상태 |
|---|---|---|
| B1 | `research.md` 는 옳은 `read_inventory` 호출자를 `tools.py:6353` 으로 적었으나 2026-09-03 grep 실측은 **`:6356`** 이다(`:6352` 는 `read_fixture_type_names` 호출). 6줄 이내 드리프트이며 착수 시 재확인한다 | 측정됨 (본 계획이 정정) |
| B2 | 라이브 응답기 버전은 미상. main 은 1.6.3(`copilot_responder.lua:82`, 실측). live-1.6.1/main-1.6.2 전례가 있다 | 미측정 — **본 SPEC 은 이것을 재지 않는다.** 라이브 판독은 SPEC-COPILOT-READBACK-001 M3 이 소유하며, 본 SPEC 은 그 불일치를 **탐지하는 기계**를 만들 뿐이다 |
| B3 | 여섯 호출 지점이 fixture-type 루트를 **이미 읽고 있는가** — REQ-READBACK2-012 의 전제. 아래 표에 실측 | 측정됨 (2026-09-03, `adae0ac`) |
| B4 | 기존 루트 판독의 재사용이 `walk_mode_widths`·`read_type_mode_widths` 경로에서 **가능한가** | **측정됨 — 불가능**(2026-09-03, `adae0ac`). `TypeModeRead`(`server/prechk/mode_read.py`)는 `attempted`/`type_found`/`modes`/`detail` 만, `WalkOutcome`(`server/prechk/footprint.py`)은 `queried_paths` 로 경로 문자열만 반환한다 — 둘 다 함수 안에서 루트를 읽지만 **(슬롯, 이름) 쌍을 호출자에게 반환하지 않는다.** 그 쌍을 흘리려면 `server/prechk/**` 를 고쳐야 하고 REQ-READBACK2-010 이 금지한다. 따라서 재사용은 **허용이지 의무가 아니다**(REQ-READBACK2-012, 0.1.1). M1 은 재사용 가능성을 판정하는 것이 아니라 **상한(지점당 1회)과 스코프 안 표 공유**를 지킨다 |

### B5 실측 — `read_inventory` 여섯 호출 지점의 fixture-type 트리 보유 여부

> 이 표는 SPEC-COPILOT-READBACK-001 v0.1.1 `plan.md §B B5` 에서 이관됐다. R4 의 전제이므로 본 SPEC 이 소유한다. 001 `plan.md §B` 에는 포인터만 남아 있다.

측정 방법: `server/orchestrator/tools.py` 의 4-space `def` 경계로 각 호출 지점의 **소유 핸들러**를 확정하고, 그 핸들러 본문에서 `fixture_types` · `walk_mode_widths` · `read_type_mode_widths` · `read_fixture_type_names` · `types_root` 를 검색했다. 2026-09-03 재확인(HEAD `adae0ac`): 핸들러 `def` 행 6건과 각 근거 행을 다시 읽어 표와 대조했고 어긋난 항목은 0건이다.

| 호출 지점 | 소유 핸들러 (행 범위) | 이미 fixture-type 루트를 읽는가 | 근거 |
|---|---|---|---|
| `:3014` | `precheck_patch` (3001-3181) | **예** | `walk_mode_widths(state_port, root=rig_paths["fixture_types"], …)` `:3046-3055` |
| `:3206` | `precheck_vectorworks_diff` (3182-3292) | 아니오 | 핸들러 본문에 fixture-type 읽기 신호 0건 |
| `:3397` | `apply_vectorworks_patch` (3373-3552) | 아니오 | `resolve_fixture_types` `:3467` 은 VWX **라이브러리** 해석기(`server/vwx/typemap`)이며 콘솔 트리 조회가 아니다 |
| `:4039` | `resolve_patch_address` (4009-4241) | 아니오 | 핸들러 본문에 fixture-type 읽기 신호 0건 |
| `:4433` | `patch_fixtures` (4242-4817) | **예** | `read_type_mode_widths(…, root=rig_paths["fixture_types"])` `:4295-4298`, 이 호출보다 **앞** |
| `:4624` | `patch_fixtures` (같은 핸들러, 재조회 팔) | **예** | 위와 같은 판독이 같은 호출을 덮는다 |
| (참조) `:6356` | `import_lxseq_patch` (6188-6580) | 예 (옳게 구현됨) | `types_root = rig_paths.get("fixture_types")` `:6326` → `read_fixture_type_names(state_port, root=types_root)` `:6352` |

읽어야 할 사실 셋:

1. **여섯 호출 지점은 다섯 핸들러에 산다** — `:4433` 과 `:4624` 는 같은 `patch_fixtures` 안이다. 「호출 지점당 1회」를 「핸들러당 1회」로 읽으면 이 두 자리에서 조회가 두 번 늘 수 있다.
2. **`rig_paths` 는 여섯 자리 전부에서 클로저로 도달 가능**하므로(`build_toolset` `:2031`) `types_root` 를 만드는 데 추가 조회는 필요 없다. 늘어나는 것은 `read_fixture_type_names` 의 목록 조회 **1회**뿐이다(`server/prechk/mode_read.py:141` — "Query count is 1").
3. **「이미 읽는다」가 「그대로 재사용된다」는 아니다 — 그리고 이 경우 재사용은 실제로 불가능하다.** `read_fixture_type_names` 의 문서 문면(`mode_read.py:142-144`)은 `read_type_mode_widths` 가 이 목적을 대신할 수 없다고 못박는다 — 그것은 `type_name` 을 **인자로 받는데**, 그 이름이 바로 이 판독이 만들어 내야 할 값이다. `walk_mode_widths` 는 같은 루트 페이로드를 `query_state` 로 읽지만(`server/prechk/footprint.py:254`), 그 반환 형상 `WalkOutcome` 은 `queried_paths` 로 **경로 문자열**만 돌려주고 페이로드도 (슬롯, 이름) 쌍도 호출자에게 주지 않는다(B4 실측). **호출자가 조회를 냈다는 것과 페이로드를 쥐고 있다는 것은 다르다.** 그러므로 이 재사용은 배관 문제가 아니라 `server/prechk/**` 변경을 요구하는 문제이고, REQ-READBACK2-010 이 그것을 금지한다. REQ-READBACK2-012(0.1.1)는 이 사실 위에서 재사용을 **의무가 아니라 허용**으로 두고 상한만 건다 — 그리고 `server/prechk/**` 변경 없이 가능한 재사용(같은 핸들러 호출 안의 이름 표 공유)만 `shall` 로 요구한다. M1 은 지점별 증가분과 재사용하지 않은 사유를 `progress.md` §E.2 조회 계수표에 계상한다.

`_name_handle_types` 의 문서 문면(`server/prechk/inventory.py:469-473`)은 이 설계 전제를 **코드 안에서** 못박는다 — 「번역이 필요한 호출자는 이미 자기 이유로 fixture-type 트리를 걷고 있다」, 그리고 **「이 저장소는 query-budget guard 를 조정 대상이 아니라 비준(ratified)된 것으로 취급한다」**. 즉 예산 가드는 협상 대상이 아니며, 위 표에서 「아니오」로 나온 세 핸들러는 그 전제의 **예외**다. REQ-READBACK2-012 는 그 예외를 부정하지 않고 **상한으로 묶는다.**

## C. 결정 기록 (DECIDED)

> SPEC-COPILOT-READBACK-001 iteration 1 감사(D1 / MP-7)에서 미해결 결정 마커가 잡혔고, 오케스트레이터가 2026-09-03 에 확정했다. 그중 **C-1 은 R3 에 속하므로 분할과 함께 본 SPEC 으로 이관**됐다. 이 절은 마커가 아니라 **결정**을 싣는다. 마커 문자열은 이 SPEC 어디에도 남지 않는다.

| # | 주제 | 채택 | 기각 | 기각 사유 | 파급 파일 | 결정일 |
|---|---|---|---|---|---|---|
| C-1 | 응답기 버전 불일치의 health state | **자체 health state** — 고유 status 문자열 + 고유 한국어 라벨 「응답기 버전 불일치 — 재임포트 필요」 | 기존 `responder_degraded` 재사용 | 재사용하면 차단·감사·배너를 공짜로 얻지만 **사유를 거짓말한다** — 성능 저하가 아니라 버전 불일치다. 운영자가 취할 행동이 다르므로(「기다린다」 vs 「재임포트한다」) 같은 배너에 담길 수 없다 | `server/safety/gate.py`(`_check_health` `:415-437` 분기) · `server/safety/monitor.py` · `server/web/session.py` · `server/web/PROTOCOL.md:57`(`status` 행의 `health` enum) · `ui/src/protocol.ts:1190-1207`(라벨 + 가이던스) · `ui/src/protocol.test.ts:185-260` — **파급을 범위 안으로 수용한다** | 2026-09-03 |

C-1 은 REQ-READBACK2-003 으로 spec.md 에 이미 반영돼 있다. 착수 전에 다시 열 사안이 아니다.

> **C-2(테이블 값의 회신 형상)는 이 SPEC 의 결정이 아니다.** R1 에 속하므로 **SPEC-COPILOT-READBACK-001 `plan.md` §C** 가 그 결정을 소유한다.

## D. 제약

- **콘솔 쓰기 0.** 본 SPEC 의 어떤 단계도 콘솔에 쓰지 않는다(REQ-READBACK2-013). 읽기 조회조차 구현 구간에는 필요 없다 — 전 AC 가 오프라인 테스트와 가짜 포트로 판정된다.
- `console/lua/` 는 **읽기만** 한다. `copilot_responder.lua:82` 의 `VERSION` 은 기대 상수의 고정 대상이지 편집 대상이 아니다. 이 디렉터리를 편집하면 다이제스트 잠금(`test_overlap_preserve.py:227-230`)이 거부하며, 그 편집 권한은 SPEC-COPILOT-READBACK-001 이 갖는다.
- 조회 예산: 고친 호출 지점당 `query_state` **최대 1회** 증가(REQ-READBACK2-012 · §B B5). 기존 루트 판독의 재사용은 `server/prechk/**` 무변경 제약 아래에서 불가능하므로(§B B4) **의무가 아니다**. 한 핸들러 호출 안의 두 자리(`:4433`·`:4624`)는 이름 표를 나눠 써 **합쳐 1회**를 넘지 않는다.
- `server/prechk/**` · `server/vwx/**` 는 **무변경**(REQ-READBACK2-010). diff 가 비어 있어야 한다.
- `server/lxseq/**` · `server/web/presets_api.py` · `console/lua/**` 편집은 **범위 밖**(001 소유). 본 SPEC 의 diff 에 이 셋이 나타나면 범위 침범이다.
- TDD. 전 범위가 순수 서버·UI 이므로 라이브 없이 RED 가능.

---

## E. 마일스톤

### M0 — R3 버전 게이트 (되돌리기 가장 어려운 결정이 여기 있다)

버전 불일치의 status 이름과 배너 문면은 §C C-1 로 확정됐고, 그 결정은 **프로토콜 문서와 UI 라벨까지 파급**된다. 한 번 나가면 이름을 바꾸는 데 서버·문서·UI·테스트 넷을 함께 건드려야 하므로 첫 번째다.

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/safety/console.py` | [MODIFY] | `ping` `:297-307` — `version` 을 링크 속성으로 보존. `ConsolePort.ping()` 시그니처는 **무변경** |
| `server/safety/` (상수 위치는 구현 재량) | [NEW] | 기대 버전 단일 상수, `copilot_responder.lua:82` 에 고정 |
| `server/safety/gate.py` | [MODIFY] | `_check_health` `:415-437` 에 버전 불일치 분기 — 감사(`:429`)·`ScreenDecision`·전송 시점 재검사(`:546-557`) 상속. 오프라인 판정보다 **엄격히 하류** |
| `server/safety/monitor.py` | [MODIFY] | 버전 불일치 자체 상태 추가 |
| `server/web/session.py` · `server/web/PROTOCOL.md:57` | [MODIFY] | `health` enum 에 새 status 문자열 추가 |
| `ui/src/protocol.ts:1190-1207` · `ui/src/protocol.test.ts:185-260` | [MODIFY] | 한국어 라벨 + 가이던스 (§C C-1 이 수용한 범위). 미인식 버전은 재임포트가 아니라 **조사**를 지시한다 |
| `server/tests/test_safety_gate.py` `test_safety_lock_monitor.py` `test_deploy_health_ux.py` `test_responder_roundtrip.py` | [MODIFY] | 낮은 버전 / 미인식 / 오프라인 비가림 / 일치 시 무회귀 4종 |

산출: 오프라인 전부 초록. **콘솔 접촉 0.** (AC-READBACK2-001~006)

### M1 — R4 kwarg 감사 + 조회 예산 (순수 배관 · M0 과 병렬 가능)

M0 과 파일이 겹치지 않으므로 병렬로 진행할 수 있다. 되돌리기 쉽고 파급이 서버 안에서 닫힌다.

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/orchestrator/tools.py` | [MODIFY] | `read_inventory` 호출 6곳(`:3014, 3206, 3397, 4039, 4433, 4624`)에 `type_names=` 전달. 참조 구현은 `:6326`→`:6352`→`:6356`. **여섯 자리 전부가 `read_fixture_type_names` 1회를 소비할 수 있다** — §B B5 의 「예」 세 자리도 기존 루트 판독을 재사용할 수 없기 때문이다(§B B4: `TypeModeRead`·`WalkOutcome` 이 (슬롯, 이름) 쌍을 반환하지 않는다). 지키는 것은 **지점당 상한 1회**와 **한 핸들러 호출 안의 표 공유**다(REQ-READBACK2-012) |
| `server/paperwork/data.py` | [MODIFY] | `build_patch_sheet` `:82-143` 에 `type_names` 매개변수, `:102` 로 전달. **자체 조회 없음** |
| `server/web/paperwork_api.py` · `server/paperwork/bundle.py` | [MODIFY] | 표를 읽어 넘기는 호출자 측 변경 |
| `server/paperwork/render.py` | [MODIFY] | `:87` — `fixture_type_untranslated` 표면화 |
| `server/tests/` 조회 계수 포트 | [NEW] | AC-READBACK2-011 이 이미 쓰는 「조회를 세는 가짜 포트」를 호출 지점 단위로 재사용해 **지점당 N+1**(013a)과 **한 핸들러의 상한 초과 N+2 → FAIL**(013b)을 이진 판정. 조회 로그는 늘어난 경로가 `read_fixture_type_names` 목록 조회임을 지점별로 답해야 한다 |
| `server/tests/test_vwx_diff.py` `test_vwx_typegap.py` `test_paperwork_patch_sheet.py` `test_prechk_handle_types.py` `test_prechk_inventory.py` | [MODIFY] | 타입별 실제 대수 · 시트 이름 인쇄 · 번역 실패 표면화 · 무변경 확인 |
| `server/prechk/**` · `server/vwx/**` | [EXISTING] | **무변경** (REQ-READBACK2-010) |

`:4433` 과 `:4624` 는 **같은 `patch_fixtures` 핸들러**다. 두 자리를 각각 고치면서 `read_fixture_type_names` 를 두 번 부르면 REQ-READBACK2-012 를 어긴다 — 핸들러 진입부에서 한 번 읽어 두 자리가 그 표를 나눠 쓴다. 이 공유는 지역 변수 하나로 끝나므로 `server/prechk/**` 변경이 필요 없고, 그래서 §B B4 가 불가능하다고 판정한 재사용과 달리 **`shall` 로 요구할 수 있다.** AC-READBACK2-013b 가 이 자리를 N+2 → FAIL 로 이진 판정한다.

산출: 오프라인 전부 초록. **콘솔 접촉 0.** (AC-READBACK2-007~012 · 013a · 013b)

### M2 — 전수 대조와 완료 보고

콘솔 접촉 없이 문서로 닫는다.

1. 호출자 전수 대조: `acceptance.md` §A 의 `ast` 계수 스니펫이 `calls 7` / `with type_names 7` / `PASS` 를 인쇄한 출력 그대로 인용(AC-READBACK2-007). **줄 단위 grep 은 쓰지 않는다** — `pyproject.toml:59` `line-length = 100` 때문에 수리 뒤 다섯 자리가 여러 줄로 쪼개져 그 수치가 의미를 잃는다.
2. `git diff --stat origin/main -- server/prechk/ server/vwx/` 가 **빈 출력**임을 인용(AC-READBACK2-012).
3. 호출 지점 여섯 자리 전부의 조회 증가분을 지점별로 계상(REQ-READBACK2-012).
4. 완료 보고 5절 작성. 미검증 절에 **제3 핸들 형태**(REQ-READBACK2-011)와 **라이브 응답기 버전 미판독**(B2 — 본 SPEC 은 탐지 기계만 만들고 라이브를 재지 않는다)을 명시(AC-READBACK2-015).

---

## F. 위험과 완화

| 위험 | 완화 |
|---|---|
| 버전 게이트가 쇼 중에 하드 스톱을 만든다 | 낮은 버전 / 미인식 구별(REQ-READBACK2-004) + 오프라인 판정 하류 고정(REQ-READBACK2-005) + 일치 시 무회귀 대조군(AC-READBACK2-006) |
| 새 status 문자열이 UI 에 도달하지 않아 배너가 원문 status 를 노출한다 | `ui/src/protocol.test.ts` 가 라벨 매핑을 이진 판정한다 — 매핑이 없으면 `healthLabel` 이 status 문자열을 그대로 돌려주므로 테스트가 잡는다 |
| 기대 버전이 두 곳에 생겨 다시 단일 출처를 잃는다 | AC-READBACK2-002 가 상수와 `copilot_responder.lua:82` 를 직접 대조하고, 테스트 리터럴이 두 번째 출처가 되지 않음을 함께 단언한다 |
| 호출자 6곳 중 일부만 고쳐 나머지가 안 보이게 된다 | 한 집합으로 감사·수정(REQ-READBACK2-006), 커밋 메시지에 7곳 전수 대조를 적는다 |
| 수리가 조회 예산을 조용히 두 배로 만든다 | §B B5 실측 + REQ-READBACK2-012 의 지점당 상한 1회 + AC-READBACK2-013a 의 N+1 양성 판정 + AC-READBACK2-013b 의 상한 초과 부정 대조군(N+2 → FAIL). `:4433`·`:4624` 가 **같은 핸들러**라는 사실이 이 위험의 구체적 형태이며, 013b 가 정확히 그 자리를 잰다 |
| 번역 기계를 「가는 김에」 고친다 | AC-READBACK2-012 의 `git diff --stat` 이 빈 출력을 요구한다 |
| 001 과 같은 파일을 건드려 충돌한다 | 파일 집합이 겹치지 않는다(§D). 겹치는 유일한 디렉터리는 `server/tests/` 이며 파일 단위로 갈린다 |

## G. 안티패턴

- `exec: ok` 를 효과의 증거로 인용하는 것.
- 「호출 지점당 1회」를 「핸들러당 1회」로 읽어 `patch_fixtures` 에서 조회를 두 번 늘리는 것.
- 버전 불일치를 기존 `responder_degraded` 에 얹어 사유를 뭉개는 것 — §C C-1 이 기각한 선택지다.
- 오프라인 상황에서 버전 사유를 표시해 운영자에게 재임포트를 권하는 것.
- 제3 핸들 형태를 「없다」로 적는 것 — 안 잰 것이지 없는 것이 아니다.
- 기존 루트 판독의 재사용을 「했어야 하는데 안 했다」로 계상하는 것 — §B B4 가 그 재사용을 `server/prechk/**` 무변경 아래에서 **불가능**으로 실측했다. 계상할 것은 지점별 증가분과 상한 준수이지 재사용 여부가 아니다.
- 001 의 범위(`console/lua/**`, `server/lxseq/**`, `server/web/presets_api.py`)를 「가는 김에」 손대는 것.

## H. 교차 참조

`spec.md` · `acceptance.md` · `research.md`(포인터) · `../SPEC-COPILOT-READBACK-001/research.md` §R3·§R4 · `.moai/specs/SPEC-COPILOT-READBACK-001/` · `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-2.md` · `reports/app-fresh-eyes-review-20260903.md` · `server/prechk/inventory.py`(문서 문면 `:469-473`·`:479-485`) · `server/prechk/mode_read.py:138-144` · `.claude/rules/moai/core/verification-claim-integrity.md`
