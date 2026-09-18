---
id: SPEC-LDSEND-001
title: "Director apply 층의 실제 콘솔 송신기와 로컬 관측 도구"
version: "0.1.0"
status: draft
created: 2026-09-18
updated: 2026-09-18
author: jaihyun
priority: P1
phase: "Lighting Director v1.0 target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, bundle-sender, safety-gate, console-observation, execution, idempotency"
tier: M
depends_on: [SPEC-LDRECV-001]
---

# SPEC-LDSEND-001

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-18 | 최초 작성. `SPEC-LDRECV-001`(status: completed, 로컬)이 남긴 콘솔 게이트 부분(AC-LDPLUGIN-021 승격부·024 관측부·032 실행부)을 닫기 위한 후속 SPEC. `BundleSender` 프로토콜의 실물 구현이 아직 없다는 것이 근본 원인(코드 실측, §1). |

## 1. 목적과 경계

`SPEC-LDRECV-001` 은 apply 직전 재검사·SafetyGate 연결·durable journal·실패 분류의
**거부 방향**은 로컬 pytest 로 완결했지만, **승격 방향**(apply 가 실제로 콘솔에
적용됐는가, 전송 성공/실패/불확실이 실기와 일치하는가, recovery apply 가 실제로
적용됐는가)은 실기 관측 없이 확정할 수 없다고 명시적으로 남겼다
(`../SPEC-LDRECV-001/spec.md` §5 표, `progress.md` §J 2026-09-18).

근본 원인은 하나다 — `server/director/execution.py:231`
`class BundleSender(Protocol): def send(self, bundle) -> str` 의 **실물 구현이
존재하지 않는다.** `execute_bundles()`(같은 파일 974~1046행)는 이미 순서대로
번들을 보내고 첫 미확인 결과 뒤 후속을 중단하며 상태를 집계하는 로직을 전부
갖추고 있지만, 지금까지는 오직 시험용 `ScriptedSender`(`server/tests/
test_director_execution_failure.py:35`)만 그 자리를 채웠다. 이 SPEC 은 그
자리에 **실제 콘솔로 보내는 구현체**를 만들고, 콘솔 게이트 항목 셋(021 승격부·
024 관측부·032 실행부)을 로컬 checkout 에서 관측할 수 있는 도구를 만든다.

이 층은 판단(어떤 명령을 보낼지)도 승인(누가 허락했는지)도 하지 않는다 — 그
결정은 이미 `SPEC-LDRECV-001` 의 `ApplyCoordinator`/`ApprovalRegistry` 가
끝냈다. 이 SPEC 이 만드는 것은 그 뒤에 오는 **한 단계**뿐이다: 승인된 명령을
공유 `SafetyGate` 를 통해 실제로 보내고, 결과를 정직하게 분류해 돌려준다.

| 규범 | 위치 |
|---|---|
| `BundleSender` 프로토콜·`execute_bundles`·상태 우선순위(unknown > partial > sent > failed) | `server/director/execution.py` (특히 231~251행 프로토콜, 974~1046행 `execute_bundles`) |
| apply 재검사·`execute_preapproved` 호출 지점 | `server/director/execution.py` `ApplyCoordinator.apply`(798~971행, 특히 940~969행) |
| `execute_preapproved`·클리어런스 발급/소비 | `server/safety/gate.py` 553~657행(`execute_preapproved`), 904~950행(`_execute_cleared`) |
| 세션 스코프 클리어런스 키 | `server/safety/session_context.py`(ambient contextvar, `current_session_key()`) |
| 콘솔 왕복·`ExecOutcome` | `server/safety/console.py` `ConsolePort.execute`(185행)·`ConsoleLink.execute`(284행)·`ExecOutcome`(79~87행) |
| 합성 스택 구성 | `server/safety/bootstrap.py` `build_console_stack`(96~189행) |
| 콘솔 명령 안전 분류 실측 | `server/tests/test_bulkgate_declaration.py:38-41`(safe), `server/tests/test_deploy_safety_invariants.py:299-309`(blacklist/held) |
| 콘솔 게이트 원인·미해소 목록 | `../SPEC-LDRECV-001/spec.md` §5, `../SPEC-LDRECV-001/progress.md` §J |

### 1.1 형제 SPEC 과의 관계

`SPEC-LDRECV-001` 은 완료됐지만 그 완료는 "거부·직렬화·journal 이 정직한가"
까지였다(그 SPEC 자신의 acceptance.md §4 go 조건 — "콘솔 필요 항목은 이 SPEC
만으로 go/no-go 를 내지 않는다"). 이 SPEC 은 그 뒤를 잇는다: `BundleSender`
실물을 만들고, 콘솔 위에서 그 세 항목을 관측할 수단을 만든다. 이 SPEC 이 그
셋을 **직접 go/no-go 판정**하지는 않는다 — `SPEC-LDCERT-001`(미작성,
first-release go/no-go 전담)이 그 자리다. 이 SPEC 이 내는 것은 "만들고
관측했다"까지다.

## 2. 범위 결정

- **송신은 이미 발급된 클리어런스를 소비하는 것뿐이다.** 이 층은 `SafetyGate.
  execute_preapproved()` 가 이미 통과시킨 명령을 `SafetyGate.execution_port`
  로 보낸다. grammar/classify/backup/health/audit 재검사나 새 승인 경로를
  만들지 않는다 — 그것은 이미 `SPEC-LDRECV-001` M5(`ApplyCoordinator`)의
  일이다.
- **번들 하나는 정확히 넷 중 하나의 상태로 귀결된다.** `STATE_SENT`/
  `STATE_ACKNOWLEDGED`/`STATE_FAILED`/`STATE_UNKNOWN` 외에는 반환하지 않는다
  (`execute_bundles` 자신이 이를 강제한다, 1023~1024행). `STATE_PARTIAL` 은
  번들 하나가 아니라 **여러 번들에 걸친 집계** 상태이며 이 층이 만드는 값이
  아니다.
- **불확실하면 unknown 이다.** 콘솔 확인 타임아웃과 명시적 거부를 구분하지
  못하면 항상 `unknown` 쪽으로 접는다 — "blind 하게 success/failed 로
  확정하지 않는다"(계약 §10, `execution.py` 모듈 docstring)는 이 SPEC 이
  상속하는 불변식이다.
- **관측 도구는 진짜 게이트 파이프라인을 탄다.** `server.tools` 패키지는
  REQ-MVP-029 단일 관문 규칙에서 면제되어 있지만(`server/tools/
  responder_roundtrip.py` 머리말 실측), 이 도구는 그 면제를 쓰지 않는다 —
  `OscBridge` 를 직접 열지 않고 `build_console_stack()` 으로 진짜
  `SafetyGate`/`ConsoleLink` 조합을 그대로 구성한다. 이 도구가 재는 것이
  바로 그 게이트 경로이기 때문이다.
- **관측 도구가 만드는 승인은 운영 승인이 아니다.** cleanup 명령
  (`Delete Sequence <N>`)은 콘솔 세이프티 게이트의 **블랙리스트** 다
  (`test_deploy_safety_invariants.py:299-309` 실측 — 승인 없이는 거부되고,
  승인 채널이 있으면 held 로 사람 승인을 기다린다). 이 도구는 그 자신만의
  labelled auto-approve `ApprovalPort` 를 구성해 자기 cleanup 요청만 통과
  시킨다 — `server/web/serve.py` 의 운영 조립에는 절대 배선되지 않는다.
- **destination 은 create-only 스크래치 영역이다.** `SPEC-LDRECV-001` 이 세운
  "server-selected 새 Sequence create-only" 원칙(§2, 그 SPEC)을 그대로
  따른다 — 쓰기 전 반드시 비어 있는지 읽어서 확인하고, 이미 점유돼 있으면
  거부한다.

## 3. 안정 요구사항

`SHALL` 은 필수다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDSEND-001 | `BundleSender` 구현은 **SHALL** 모든 명령을 공유 `SafetyGate.execution_port` 로만 보내고 `server.bridge.osc` 를 직접 import 하지 않는다. | REQ-MVP-029; `execution.py:231` |
| REQ-LDSEND-002 | **When** `send(bundle)` 이 호출되면 송신기는 **SHALL** `bundle["commands"]` 를 순서대로 보내고, 확인되지 않은(ok 가 아닌) 첫 결과 뒤로는 같은 번들의 남은 명령을 보내지 않는다. | `execution.py` `execute_bundles` 924행 주석; 계약 §10 |
| REQ-LDSEND-003 | 송신기는 **SHALL** 번들 하나마다 `STATE_SENT`/`STATE_ACKNOWLEDGED`/`STATE_FAILED`/`STATE_UNKNOWN` 중 정확히 하나만 보고한다 — 판정 표는 plan.md 기술 접근에 둔다. | `execution.py:1023-1024` |
| REQ-LDSEND-004 | **When** 콘솔 링크 호출이 예외를 던지면 송신기는 **SHALL** 그 예외를 잡아 해당 명령을 unconfirmed 로 취급하고, 예외가 `send()` 밖으로 그대로 전파되지 않게 한다. | `console.py` `ConsoleLink._round_trip` 268행(미바인딩 시 `RuntimeError`) |
| REQ-LDSEND-005 | `send()` 가 반환한 뒤(전부 보냈든 도중에 멈췄든) apply 경로는 **SHALL** 그 apply 가 발급한, 아직 안 쓰인 클리어런스를 회수해 이후 무관한 명령이 재사용하지 못하게 한다. | `gate.py:645`(발급) — 오늘은 회수 API 부재(실측) |
| REQ-LDSEND-006 | **Where** `SafetyGate` 가 세션 클리어런스 회수 수단을 아직 갖지 않으면, `SafetyGate` 는 **SHALL** 호출 세션 자신의 클리어런스 카운터만 비우는 최소 public 메서드 하나로 확장되고, 이 확장은 다른 세션·다른 호출자의 `screen()`/`execute_preapproved()` 관측 가능 동작을 바꾸지 않는다. | `gate.py:415,520,580,645`(세션 키 스코프) |
| REQ-LDSEND-007 | 로컬 관측 도구는 **SHALL** 콘솔 접근을 오직 `server.safety.bootstrap.build_console_stack` 으로만 구성하고 별도 OSC 수신 소켓을 새로 열지 않는다. | `bootstrap.py:96-189` |
| REQ-LDSEND-008 | **When** 관측 도구가 한 실행(run) 안에서 스크래치 destination 에 처음 쓰려고 하면, 도구는 **SHALL** 그 destination 이 비어 있는지 콘솔에 물어 확인하고, 이미 점유돼 있으면 진행을 거부한다. | `../SPEC-LDRECV-001/spec.md` §2 LD-TARGET-001 |
| REQ-LDSEND-009 | 관측 도구는 **SHALL** 기본으로 dry-run 모드(보낼 명령만 출력하고 실제로 보내지 않음)로 동작하고, 콘솔에 무엇이라도 쓰려면 `--execute` 플래그를 명시적으로 요구한다. | `responder_roundtrip.py`(`--skip-exec` 선례) |
| REQ-LDSEND-010 | `--execute` 로 구동한 모든 시나리오에 대해 도구는 **SHALL** 그 결과(적용됐는지/안 됐는지)를 responder 를 통한 콘솔 state/property 재조회로 확인하고, `BundleSender` 가 돌려준 상태만으로 결과를 보고하지 않는다. | `../SPEC-LDRECV-001/spec.md` §5 "object-existence 확인" |
| REQ-LDSEND-011 | `--execute` 실행이 끝나면(성공이든 실패든) 도구는 **SHALL** 그 실행이 스크래치 destination 에 만든 콘솔 객체를 제거·해제하는 cleanup 단계를 제공한다. | §2 destination create-only |
| REQ-LDSEND-012 | 관측 도구가 자기 시나리오 구동이나 cleanup 을 위해 만드는 모든 승인 객체는 **SHALL** 로컬 관측 하네스 산출물임을 구분되는 고정 문자열(principal/reason)로 표시하고, `server/web/serve.py` 의 운영 조립에는 배선되지 않는다. | `test_deploy_safety_invariants.py:299-313`(blacklist held 실측) |

## 4. 비목표

### Out of Scope — 판단·승인·직렬화

- 새 승인 경로, 새 직렬화(중재자) 로직, apply 재검사 로직의 변경은 포함하지
  않는다 — 전부 `SPEC-LDRECV-001` `ApplyCoordinator`/`ProgrammerArbiter`
  소유다. 이 SPEC 은 그 뒤에 이미 승인된 명령을 보내기만 한다.
- HTTP 라우팅·자격 발급·`ContextProvider`/`ValidationProvider` 배선은
  포함하지 않는다 — 큐 카드 t421 이 담당하고, 그 자리에 필요한
  `ValidationProvider` 가 아직 없어 지금은 실행 가능한 경로가 아니다
  (`director_api.py:273` 실측).
- `InterferenceDetector` 프로토콜의 실물 구현(operator 개입 감지)은 포함하지
  않는다 — 이 SPEC 은 `BundleSender` 만 만든다. `execute_bundles()` 는
  `interference=None` 으로도 완결되게 이미 설계돼 있다(`execution.py:980`
  기본값).

### Out of Scope — 콘솔 게이트 최종 판정·형제 SPEC

- `SPEC-LDRECV-001` 의 spec.md/plan.md/acceptance.md 본문 변경은 포함하지
  않는다 — 그 SPEC 은 `completed` 로 닫혔다. 이 SPEC 은 별도 자식이다.
- 실기 관측 결과를 근거로 한 first-release go/no-go 판정은 포함하지 않는다
  — `SPEC-LDCERT-001`(미작성)의 몫이다. 이 SPEC 은 "관측했다"까지 낸다.
- 두 기존 예술 producer(`server/looks/songcue.py`,
  `server/web/session.py` 의 `_ARC_*`)의 cutover, MCP adapter, 검토 UI 는
  포함하지 않는다 — 각각 `SPEC-LDCUTOVER-001`/`SPEC-LDHOST-001`/
  `SPEC-LDUI-001`(모두 미작성 또는 별도 SPEC) 소유다.

## 5. 검증 수단의 한계 (착수 전 고지)

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이
유일한 자동 판정 근거다(`SPEC-LDRECV-001` 이 남긴 것과 같은 제약).

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| 송신기의 순서·중단·상태 매핑(001~004) | fake 콘솔 링크/게이트 + pytest | 아니오 |
| 클리어런스 소비·회수(005~006) | fake gate + pytest | 아니오 |
| 관측 도구의 스택 구성·dry-run 출력(007, 009) | 합성 스택 또는 fake console + pytest | 아니오 |
| 관측 도구의 destination 점유 확인 로직(008)의 거부 방향 | fake 콘솔 응답 + pytest | 아니오 |
| **AC-LDPLUGIN-021 승격부 — apply 가 실제로 콘솔에 적용됐는가** | onPC 실기 관측 (010) | **예** |
| **AC-LDPLUGIN-024 관측부 — 실패 뒤 후속 bundle 이 실기에서도 안 갔는가** | onPC 실기 관측 (010) | **예** |
| **AC-LDPLUGIN-032 실행부 — recovery apply 가 실제로 적용됐는가** | onPC 실기 관측 (010) | **예** |
| cleanup 이 실제로 콘솔 객체를 지웠는가(011) | onPC 실기 관측 | **예** |

이 SPEC 은 부분적으로 콘솔 게이트다 — 형제 `SPEC-LDRECV-001`·
`SPEC-LDCOMPILE-001` 과 같은 비대칭이다: **송신기 자체의 로직(거부·중단·
매핑)은 로컬로 닫히고, 실기 적용 확인만 콘솔이 필요하다.**
