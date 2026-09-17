# 설계 결정 — SPEC-LDRECV-001 (seam 3건)

[요구사항](spec.md) · [구현 계획](plan.md) · [인수](acceptance.md) · 우산:
[계약](../SPEC-LDPLUGIN-001/contract.md) · [설계](../SPEC-LDPLUGIN-001/design.md)

**이 문서의 범위.** 이것은 우산 `design.md` 를 대체하는 전면 컴포넌트 설계가 아니다 —
`spec.md` §1.1 이 설명하듯, 이 SPEC 은 원칙적으로 자체 `design.md`/`research.md` 를
만들지 않는 형제 관례를 따르되, plan-audit(2026-09-16, FAIL, ≈0.75)이 D3·D5 로 지적한
**세 가지 seam 결정**만 여기서 독립적으로 다룬다. 이 세 결정은 기존 안전장치
(`SafetyGate`)의 동작을 바꾸거나, 완료된 형제 SPEC 이 소유한 저장 스키마의 경계와
맞닿아 있어, `plan.md` 서술 안에 묻어두면 사람이 그 판단만 떼어 검토하기 어렵다.

## 1. SafetyGate 승인 이중화 — `execute_preapproved` 대안 비교

### 1.1 문제

`server/safety/gate.py` `SafetyGate.screen()`(358~475행)을 실제로 읽으면, `held` 로
분류되거나 호출자가 번들 위험을 선언한 명령에 대해 내부적으로
`self._approval_port.request_approval(approval_request)` 를 호출한다(415행). 이
`ApprovalPort` 는 기존 일반 채팅/WS 승인 채널이며, UI 세션이 없으면 fail-safe 로 항상
거부한다(`DenyAllApprovalPort`).

director 의 apply 경로가 `screen()` 을 그대로 호출하면, 사람이 이미 director 자신의
`ApprovalBinding` 으로 승인한 뒤인데도 두 번째로 — 이번엔 존재하지 않는 UI 세션을
향해 — 승인을 요청하고 자동으로 거부당한다. `REQ-LDPLUGIN-021` 원문이 우회 금지
대상으로 열거하는 것은 정확히 "문법·위험·백업·health·audit" 다섯이며, 이 목록에
"승인"은 없다 — 즉 설계 의도는 grammar→classify→lock→backup→audit 는 그대로
지나가되, **일반 `ApprovalPort` 재질문만 건너뛴다**는 것이다.

### 1.2 ANCHOR 제약 — 왜 "새 메서드 추가"가 자명한 선택이 아닌가

`screen()` 은 `@MX:ANCHOR` 로 표시되어 있고(353행), 그 `@MX:REASON` 이 명시적으로
이렇게 적혀 있다: *"REQ-MVP-011/029 — 정확히 하나의 심사 경로만 존재해야 한다; 두
번째 진입점은 그 자체로 게이트 우회다(fan_in >= 3)."* 이것은 이 설계가 정면으로
마주해야 하는 제약이다 — `execute_preapproved` 라는 두 번째 **공개 진입점**을 만드는
것은 문면 그대로 읽으면 이 ANCHOR 가 금지하는 바로 그것처럼 보인다.

이 제약과 REQ-021 의 "승인만 건너뛴다"는 요구를 동시에 만족시키려면, ANCHOR 의
실제 의도(무엇을 보호하는가)를 정확히 읽어야 한다: 보호 대상은 "공개 메서드가 하나여야
한다"가 아니라 **"grammar→classify→backup→health→audit 의 심사 파이프라인이 우회
없이 하나여야 한다"**는 것이다(REQ-MVP-011/029 의 실제 위반 시나리오는 "심사를 안
거치고 바로 실행하는 두 번째 경로"이지 "심사를 거치는 두 번째 공개 함수"가 아니다).

### 1.3 대안 비교

| 대안 | 설명 | 장점 | 단점 |
|---|---|---|---|
| A. `screen()` 에 flag 인자 추가 (예: `screen(commands, *, skip_approval_reask=False)`) | 기존 시그니처를 확장 | 공개 진입점이 여전히 하나 — ANCHOR 문면을 가장 온전히 지킨다 | `risk` 매개변수와 마찬가지로 **모델이 끌 수 있는 스위치**가 되면 안전장치가 아니게 된다(§2.0-가 인용 원칙과 동일 — `run_commands` 의 `risk` 가 키워드 전용인 이유). `skip_approval_reask` 가 호출자 코드에서만 만들어지는 값이라는 보장을 `screen()` 시그니처 자체로는 강제할 수 없다 — 호출부마다 별도 감사가 필요해 오히려 감사 표면이 넓어진다 |
| B. 완전히 새 파일/경로에 director 전용 실행기 작성 (grammar/classify/backup/audit 로직을 복제) | `gate.py` 를 건드리지 않는다 | `gate.py` PRESERVE 완전 보존 | REQ-021 이 금지하는 정확히 그 상황(문법·위험·백업·health·audit **파이프라인이 둘**)을 코드로 만든다 — 두 구현이 갈라지면 한쪽만 고쳐지는 회귀가 구조적으로 열린다. 가장 위험한 대안 |
| **C. `gate.py` 에 새 public 메서드 `execute_preapproved` 추가(채택)** | `screen()` 과 동일한 private stage 순서(`_check_health`→`_stage_grammar`→`_stage_classify`→`_check_lock`→backup)를 호출하되, `approval_findings` 유무와 무관하게 `self._approval_port` 를 절대 부르지 않고 director 호출자가 이미 가진 `ApprovalBinding` 을 그 자리의 증거로 삼는다. `screen()` 자신은 한 글자도 바뀌지 않는다 | REQ-021 의 "승인만 건너뛴다" 요구를 가장 정확히 구현 — grammar/classify/backup/health/audit 는 실제로 같은 코드(같은 private 메서드)를 지난다 | 공개 메서드 개수는 2가 된다(ANCHOR 문면과 표면적으로 충돌) — 단, §1.2 의 해석대로 ANCHOR 의 실질 보호 대상(심사 파이프라인의 단일성)은 두 메서드가 같은 private 스테이지를 호출하는 한 위반되지 않는다 |

**채택**: C. A 는 안전 스위치가 모델 조작 가능 표면으로 재해석될 위험이 있고, B 는
심사 로직을 복제해 REQ-021 이 금지하는 상황을 정확히 재현한다. C 는 두 공개
진입점이 **동일한 private 스테이지 시퀀스**를 호출하도록 강제함으로써 ANCHOR 의
실질 취지("심사 경로가 하나")를 지킨다 — `@MX:ANCHOR`/`@MX:REASON` 주석은
`execute_preapproved` 추가 시 갱신하여(§2.0 의 PRESERVE 원칙과 모순되지 않는다 —
"경로가 갈라지지 않는다"는 사실 자체를 주석에 반영하는 것) fan_in 계산이 두 진입점을
모두 인식하게 한다.

### 1.4 characterization 검증 방법

- `screen()` 의 기존 동작이 바이트 동일하게 유지되는지: 기존 `server/tests/test_*gate*.py`
  전체가 `execute_preapproved` 추가 후에도 그대로 통과해야 한다(회귀 0).
- `execute_preapproved` 가 grammar/classify/backup/health/audit 를 실제로 통과시키는지:
  위반 명령을 넣었을 때 `screen()` 과 동일하게 거부되는 대조 시험 — 두 메서드에 같은
  위반 명령을 넣고 결과(`ScreenDecision.status`, `reasons`)가 일치하는지 단언한다.
- `self._approval_port.request_approval` 이 `execute_preapproved` 경로에서 **호출되지
  않는지**: mock 호출 횟수 0 단언(이미 `plan.md` §4·`acceptance.md` AC-021 항목 3 에
  명시).

## 2. `server/orchestrator/tools.py` 접점 — 확정

### 2.1 실측: 9개 grep 매치 중 실제 호출은 1곳(if/else 두 분기)

```
$ grep -n "gate\.screen(" server/orchestrator/tools.py
531, 1647, 2591, 2951, 7539, 8070, 12994 행 — 전부 주석/문서 인용
2366, 2368 행 — 실제 호출 (하나의 if/else 분기, `run_commands` 클로저 안)
```

`server/orchestrator/tools.py:2360-2369` 의 `run_commands` 클로저가 `bundle_gate.screen(
commands)`(`risk is None`일 때) 또는 `bundle_gate.screen(commands, risk=risk)`(선언이
있을 때)를 부른다. 이것이 9개 grep 매치 중 유일한 실제 호출부이며, 논리적으로는
하나의 호출 지점(risk 유무에 따른 분기)이다.

### 2.2 추가 실측: tools.py 는 이 패턴의 유일한 호출부가 아니다

`plan.md` 의 두 가설은 모두 "`tools.py` 만" 대상으로 두었으나, 같은 패턴
(`self._gate.screen(commands) if risk is None else self._gate.screen(commands,
risk=risk)`)을 검색하면 다른 두 파일에서도 동일 호출이 발견된다:

```
server/measurement/runner.py:167
server/web/session.py:4691
```

`session.py` 는 `plan.md` §3 PRESERVE 표가 **"쓰지 않는다 — SPEC-LDUI-001 전용.
충돌 없음"** 으로 명시한 파일이다. 이것이 이번 조사에서 나온 가장 중요한 발견이다:
**만약 직렬화를 "호출부마다 lock 을 감싼다"(가설 1) 방식으로 구현하면, 최소
`tools.py`·`session.py`·`measurement/runner.py` 세 파일을 수정해야 하고, 그중
`session.py` 수정은 이 SPEC 의 PRESERVE 선언과 정면으로 충돌한다.**

### 2.3 결정: `tools.py` 를 수정하지 않는다 — lock 은 `gate.py` 안에 둔다

가설 2 를 채택한다: 공유 programmer 중재자(REQ-022)의 lock 획득/해제는
`server/orchestrator/tools.py`(또는 `session.py`·`measurement/runner.py`)의 각
호출부가 아니라, `SafetyGate` 자신의 **공유 파이프라인 지점**(`screen()` 과
`execute_preapproved()` 가 공통으로 거치는 private 스테이지, 예: `_check_lock` 직후
또는 별도의 새 private 헬퍼)에서 획득한다.

**근거**:
1. `screen()` 은 `run_commands`(`tools.py`)·`session.py`(4691행)·`measurement/runner.py`
   (167행) 세 곳 모두에서 **동일한 시그니처**(`.screen(commands)` /
   `.screen(commands, risk=risk)`)로 불린다 — 즉 이미 "모든 shared mutation 경로가
   하나의 함수를 거친다"는 구조가 있다. lock 을 그 함수 **안**에 두면 세 호출부를
   전혀 건드리지 않고도 REQ-022 가 요구하는 "director/chat/import 등 모든 shared
   programmer mutation 을 하나의 중재자로 직렬화"를 달성한다.
2. 반대로 호출부마다 감싸는 방식(가설 1)은 `session.py` PRESERVE 를 깨고, 향후
   `.screen(` 호출이 새로 추가될 때마다 그 호출부도 잊지 않고 감싸야 하는 유지보수
   부담을 만든다 — lock 을 빠뜨린 새 호출부는 조용히 직렬화 밖으로 샌다.
3. `execute_preapproved`(§1) 도 같은 private 스테이지를 호출하므로, 그 자리에 lock 을
   두면 director 경로와 기존 chat/import 경로가 **자동으로 같은 lock** 을 공유한다 —
   별도 배선이 필요 없다.

**"screen() 은 바이트 동일"과의 관계**: `plan.md` §2.0-가·§3.1 이 앞서 "기존
`screen()`/내부 stage 메서드는 수정하지 않는다"고 적은 것은, 이 조사 이전 시점의
가정(호출부 wrapping 방식)에 근거한 서술이었다. 이 설계 결정으로 그 서술을
수정한다: `screen()` 의 **관측 가능한 동작**(입력별 결정·사유·감사 로그)은 회귀
없이 유지되지만, `_check_lock` 직후(또는 신설 private 스테이지)에 중재자 lock
획득/해제가 **내부적으로 추가**된다. 기존 단일 세션 테스트 스위트는 동시 요청이
없으므로 이 추가로 인한 관측 가능한 동작 변화가 없다 — `AC-LDPLUGIN-021` 항목 4
("기존 `screen()` 의 회귀 없음")는 이 의미로 재확인한다: **입출력 계약**은 바이트
동일, **내부 구현**에는 lock 스테이지가 추가된다.

이 결정은 `plan.md`·`acceptance.md`·`progress.md` 에도 반영한다(§4 이하 및 해당
문서의 수정 참고).

### 2.4 미검증으로 남는 것

`session.py`·`measurement/runner.py` 의 `.screen(` 호출부 본문(주변 맥락)은 이번
조사에서 존재만 확인했고 전문을 읽지 않았다 — M3 착수 시 그 두 호출부가 정말
"차용 없이 동일 시그니처로 `SafetyGate` 인스턴스를 공유"하는지(같은 `SafetyGate`
객체인지, 아니면 세션별 별도 인스턴스인지)를 확인해야 한다. 별도 인스턴스라면
lock 은 인스턴스가 아니라 **모듈 레벨 공유 객체**(또는 명시적으로 주입되는 공유
`ProgrammerArbiter`)로 만들어야 하며, 이 확인 전에는 "세 호출부가 자동으로 같은
lock 을 공유한다"는 §2.3 근거 1 이 완전히 검증된 것은 아니다.

## 3. Destination occupancy 데이터 — 어디에 둘 것인가

### 3.1 문제

`plan.md` §6·`acceptance.md` 가 목적지 점유 재확인(REQ-021: "target/destination
occupancy" 재검사)을 "합성 입력만으로 간단히" 가능한 것처럼 적었다. 그러나
`server/director/context.py`(434줄)·`server/director/models.py`(304줄)를 직접 읽은
결과, `datapool_id`/`occupancy`/`occupancy_revision`/`Destination` 관련 필드나 타입이
**전혀 없다**. `ContextObservations.target`(context.py:134)은 타입 없는
`Mapping[str, Any]`이며, 발급 파이프라인(`build_snapshot`, 178-218행)도 `target`
필드를 그대로 복사할 뿐 occupancy 를 계산하거나 검증하지 않는다(`_reject_promoted_
unknowns`, 221-249행이 `target.identity_status`/`identity_evidence_refs`는 검사하지만
occupancy 는 다루지 않는다).

### 3.2 옵션 비교

| 옵션 | 설명 | 장점 | 단점 |
|---|---|---|---|
| A. `SPEC-LDSTORE-001` 후속 amendment 로 `context.py` 에 필드 추가 | `ContextObservations`/`build_snapshot` 에 occupancy 축 추가 | `target` 과 같은 자리에 있어 자연스러워 보인다 | (1) `plan.md` §3 PRESERVE 표가 `context.py` 를 "형제 SPEC 소유. 이 층은 읽고 호출만"으로 명시 — 이 SPEC 은 그 파일을 쓸 권한이 없다. (2) `SPEC-LDSTORE-001` 은 이미 `completed` 로 닫혔다 — amendment 는 별도 절차(완료→진행중 재개, HISTORY 기록)가 필요한 무거운 경로다. (3) 근본적으로 `ContextSnapshot` 은 계약 §6.1 이 규정하는 **불변** 구조다("동일 source revision·live binding 이면 같은 snapshot 반환") — occupancy 는 apply 가 일어날 때마다 바뀌는 **가변** 상태이므로, 불변 snapshot 안에 넣으면 "점유가 바뀌어도 snapshot 은 그대로"라는 모순이 생긴다 |
| **B. LDRECV 소유의 독립 테이블/모듈로 점유 상태를 추적(채택)** | `ContextSnapshot.target` 과는 별도로, LDRECV 자신의 마이그레이션(`002_execution_journal.sql`, M4)에 destination 예약 테이블을 추가 | (1) PRESERVE 경계를 지킨다 — `context.py` 를 전혀 건드리지 않는다. (2) `001_initial.sql` 자신의 주석이 이미 이 경로를 예견했다: *"approval 과 execution journal 은 형제 SPEC-LDRECV-001 의 것이므로 여기서 만들지 않는다"*(1-8행 실측) — LDSTORE 는 execution 관련 스키마를 의도적으로 LDRECV 에 남겼다. (3) occupancy 는 본질적으로 apply 실행의 부산물(어떤 Sequence 가 이미 만들어졌는가)이므로 execution journal 과 같은 층에 속한다 — 불변 snapshot 과 섞이지 않는다 | LDRECV 가 "target 재검사"를 할 때 `ContextSnapshot.target`(제출 시점 값)과 LDRECV 자신의 occupancy 테이블(실시간 값)을 **둘 다** 참조해야 한다 — 단일 출처가 아니라는 인지 부담이 생긴다. 이 SPEC 의 M5 구현에서 이 결합을 명시적으로 문서화해야 한다 |

**채택**: B. 결정적 근거는 세 가지다 — (1) PRESERVE 경계(§ context.py 는 형제
소유), (2) `001_initial.sql` 자신의 주석이 이미 이 분리를 의도했다는 실측 증거,
(3) 계약 §6.1 의 ContextSnapshot 불변성 원칙과 occupancy 의 본질적 가변성이
구조적으로 충돌한다. REQ-021("destination 은 server-selected 새 Sequence
create-only")과 계약 §6.1(ContextSnapshot 이 server-owned 라는 원칙) 둘 다 B 가 더
부합한다 — §6.1 은 "snapshot 이 불변"이라고 했지 "occupancy 추적이 snapshot 안에
있어야 한다"고는 하지 않았고, occupancy 는 apply 실행이 만드는 최신 상태이므로
execution journal(LDRECV 소유)에 속하는 것이 자연스럽다.

### 3.3 구현 방향 (M4/M5 착수 시 확정할 세부, 여기서는 스키마 방향만)

- `server/director/migrations/002_execution_journal.sql`(M4, `001_initial.sql` 뒤에
  이어붙임)에 destination 예약 테이블을 추가한다 — 가칭 `destination_reservations`,
  최소 컬럼: `project_id, show_id, sequence_id, reserved_by_execution_id, reserved_at,
  status(reserved|released)`.
- M5 의 apply 직전 재검사는 `ContextSnapshot.target`(제출된 declared identity)을
  읽는 것과 별개로, 이 테이블을 조회해 요청된 Sequence slot 이 이미 `reserved` 인지
  확인한다 — 점유돼 있으면 차단(create-only, silent reselection 금지, §2 스펙
  본문의 LD-TARGET-001).
- 이 구현 방향은 M4/M5 착수 시 재확인 대상이다(§4). 컬럼 이름·정확한 상태 enum 은
  이 문서가 확정하지 않는다.

## 2.5. M3 착수 후 발견 — REQ-LDPLUGIN-022 범위를 director/chat/import 로
좁힌다 (panel 제외)

### 2.5.1 충돌

M3 구현(§1·§2)을 `server/safety/gate.py` 에 배선한 뒤 전체 회귀
(`uv run pytest -q`)를 돌리자, 이 SPEC 문서 어디에도 등장하지 않는 기존
요구사항과 충돌했다: `server/web/panel.py`(SHOWUI M2/M3 소유,
REQ-SHOWUI-001..013/022..026)의 `PanelRuntime.fire()` — 대시보드 실행기
버튼 하나가 콘솔에 닿는 유일한 경로 — 도 `self._gate.screen([command])`
를 직접 부른다. 이것은 §2.1(실측)이 찾은 `tools.py`/`session.py`/
`measurement/runner.py` 세 호출부에 포함되지 않은 **네 번째** 호출부이며,
이 SPEC 의 spec.md·plan.md·acceptance.md 어디에도 "panel"이라는 단어가
없다 — 순수하게 이번 회귀에서 처음 드러났다.

`REQ-SHOWUI-013`(기존, 배포됨): "a chat turn in flight must not busy-out
the panel" — chat 이 진행 중이어도 panel 조작은 busy 로 막히지 않고 실제로
콘솔에 닿아야 한다. 이것을 지키는 기존 테스트
(`server/tests/test_web_panel_execute.py::TestSerialization`)는 chat 과
panel 의 `screen()` 호출이 **의도적으로 동시에, 직렬화 없이** 통과하는
것을 전제로 짜여 있다.

`REQ-LDPLUGIN-022`(이 SPEC): "director/chat/import 등 **모든** shared
programmer mutation을 하나의 중재자로 직렬화". `gate.py` 의 공유 private
스테이지에 lock 을 둔 것(§2.3 의 핵심 이점 — 세 호출부 무수정)은 그
대가로 `.screen(` 을 부르는 모든 경로를 자동으로 포함시킨다 — panel 도
예외가 아니다. 결과: `TestSerialization` 의 2개 시험이 실패했다(director
apply 가 lock 을 쥔 동안 panel 요청이 콘솔에 닿지 못함).

### 2.5.2 결정 (사람 확인, 2026-09-17)

**REQ-LDPLUGIN-022 의 "모든 shared programmer mutation"을
"director/chat/import"로 좁힌다 — panel(REQ-SHOWUI-013)은 중재자 범위에서
제외한다.** 근거: panel 은 사람이 지금 이 순간 누른 실행기 버튼이라
REQ-022 의 동기("오래 대기시켜 낡은 승인을 실행하지 않는다")가 원천적으로
적용되지 않는다 — panel 에는 "낡아질 승인"이 없다, 매 press 가 그 자체로
새 요청이다. 반면 director apply 는 M2 의 `ApprovalBinding`(최대
10분짜리 승인)을 들고 대기했다가 실행하므로 "낡은 승인" 위험이 실재한다.

### 2.5.3 채택한 가드 메커니즘

`SafetyGate.screen()`에 키워드 전용 매개변수 `arbitrate: bool = True`를
추가한다. 기본값이 `True`이므로 **기존 호출부(`tools.py`의
`run_commands`, `session.py`의 chat 래퍼, `measurement/runner.py`)는
코드를 전혀 바꾸지 않고도** REQ-022 의 직렬화를 그대로 받는다(이
키워드를 아예 넘기지 않으므로). `panel.py`의 `PanelRuntime.fire()` 만
`self._gate.screen([command], arbitrate=False)`로 명시적으로 넘겨
중재자를 건너뛴다 — grammar/classify/backup/health/audit 는 조건 없이
그대로 지난다, `arbitrate`가 건드리는 것은 새 arbiter 스테이지 하나뿐이다.

**이 대안을 고른 이유**: (1) `tools.py`/`session.py`/`measurement/
runner.py` 를 안 건드린다는 §2.3 의 원래 이점을 그대로 지킨다 — 새
매개변수의 기본값이 곧 "과거와 동일"이라서 세 파일이 여전히 무수정이다.
(2) panel.py 는 이 SPEC 소유가 아니므로(SHOWUI 소유) 최소 1줄만
건드린다 — `arbitrate=False`를 넘기는 호출부 변경 자체가 REQ-SHOWUI-013
을 지키기 위한 필수 최소 수정이다(gate.py 내부만으로는 "이 호출이
panel 발신"이라는 사실을 판별할 신호가 전혀 없다 — session_key 는
세션 단위 식별자이지 chat-vs-panel 구분자가 아니다). (3) 대안(호출부마다
직접 lock 을 관리하게 하거나, gate.py 가 명령 내용으로 panel 을
추측하는 것)은 각각 §2.3-근거2 가 이미 기각한 "호출부마다 감싸기"의
재현이거나, 안전장치가 내용 기반 추측에 의존하는 더 위험한 설계다.

**부작용 — test harness 1줄 추가 수정**: `server/tests/
test_web_panel_execute.py::make_harness` 의 `spy()` 함수가 `gate.screen`
을 모니터링용으로 감싸는데, 실제 시그니처와 다른 파라미터 목록
(`commands, *, risk=None`)만 받고 있어 `arbitrate=`를 못 받아
`TypeError`를 냈다(카드 t323 이 남긴 같은 모양의 결함 — `risk=`때도
같은 문제였다). 시그니처를 게이트의 실제 것과 맞춰
`spy(commands, *, risk=None, arbitrate=True)`로 확장하고 그대로
전달한다 — 이 파일은 SHOWUI 소유 **테스트** 코드이며, 프로덕션 코드는
아니다.

### 2.5.4 이 결정이 재확인이 필요 없는 이유

`execute_preapproved()`(director 전용, M5 apply 가 부를 유일한 경로)는
`arbitrate` 매개변수를 갖지 않는다 — director 는 REQ-022 의 세 갈래 중
하나이므로 항상 중재자를 타야 하고, 이 SPEC 의 어떤 결정도 그것을
바꾸지 않는다.

## 4. 이 문서가 판정하지 않는 것

- SafetyGate `execute_preapproved` 의 최종 시그니처·private 스테이지 재사용 방식의
  세부 코드는 M3 착수 시 확정한다 — 이 문서는 방향(대안 C, ANCHOR 해석)만 정한다.
- destination 예약 테이블의 정확한 스키마(컬럼 타입·인덱스)는 M4 착수 시 확정한다.
- `session.py`·`measurement/runner.py` 의 `.screen(` 호출부가 같은 `SafetyGate`
  인스턴스를 공유하는지는 §2.4 의 미검증 항목이며, M3 착수 시 먼저 확인한다.
