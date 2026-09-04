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

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## Plan Audit-Ready Signal

- plan_complete_at: 2026-09-04T00:45:29Z
- plan_status: audit-ready
- plan_audit: PASS 0.92 (iteration 2, .moai/reports/plan-audit/SPEC-COPILOT-READBACK-002-review-2.md) · 잔존 optional 3건(D7 재사용 경로 도달 · D8 앵커 1행 · D9 AC-009 문자열 술어)은 run 단계 소유
