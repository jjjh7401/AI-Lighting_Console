# 구현 계획 — SPEC-LDSEND-001

[요구사항](spec.md) · [인수](acceptance.md) · 선행: [SPEC-LDRECV-001](../SPEC-LDRECV-001/spec.md)

## 1. 착수 경계

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 다 —
`.moai/config/sections/quality.yaml` `constitution.development_mode: tdd`.

이 계획은 **Implementation Kickoff Approval 을 아직 받지 않았다.** 승인 없이
구현을 시작하지 않는다.

**§2.0 의 인터페이스 결정 다섯 항목은 사람 확인을 마쳤다(2026-09-18,
plan-audit iter1 D1-D4 + iter2 D9 대응).** `ExecutionResult.outcome` 확장(가),
`SafetyGate` 클리어런스 회수 + 세션 격리(나), readback 질의 경로(다),
AC-024 실패 유발 명령의 실기 탐색 방침(라), 관측 도구의 apply 경로 —
공유 함수로 real `GateBundleSender`/`execute_bundles()` 를 실제로 탄다(마,
iter2 D9-D11 대응) — 다섯 다 되돌리기 비싼 결정이라 Implementation Kickoff
Approval 이전에 확정해 뒀다. M1 착수 전 마지막으로 남는 것은 §6 중단 조건의
재실측(행 번호·버전 드리프트 확인)뿐이다.

## 2.0 인터페이스 결정 — 가장 먼저 확인받아야 하는 것

### (가) `ExecutionResult`(게이트 쪽) 에 명시적 `outcome` 필드를 추가할지 — **확정(사람 확인 완료, 2026-09-18)**

**문제**: `server/orchestrator/ports.py` 의 `ExecutionResult` 는 `ok: bool`,
`detail: str` 두 필드뿐이다(24~28행 실측). `SafetyGate._execute_cleared`
(`gate.py:904-950`)는 콘솔의 `ExecOutcome.status`(`"ok"`/`"failed"`/
`"unconfirmed"`, `console.py:79-87`)를 이 두 필드로 접는데, `"failed"` 와
`"unconfirmed"` 가 **둘 다 `ok=False`** 로 뭉개진다 — 구분은 `detail` 문자열
안에 "execution unconfirmed" 라는 문구가 있는지로만 가능하다(`gate.py:943-948`).

이 SPEC 의 REQ-LDSEND-003(번들 상태 매핑)은 정확히 이 구분에 의존한다 —
"확인 안 됨"(콘솔이 확인을 안 줬다, timeout)과 "명시적으로 실패"(콘솔이
거부를 확인해 줬다)를 갈라야 `unknown`/`failed` 를 정직하게 나눌 수 있다
(계약 §10, "blind 하게 success/failed 로 확정하지 않는다").

**대안 A(비권장)**: `detail` 문자열에서 `"unconfirmed"` 부분 문자열을 찾아
구분한다. 코드 변경이 없다는 장점이 있지만, 사람이 읽으라고 쓴 안내 문구를
제어 흐름 신호로 쓰는 것은 취약하다 — 문구가 바뀌면 조용히 깨진다.

**대안 B(채택)**: `ExecutionResult` 에 선택적 필드
`outcome: str = "ok"`(값: `"ok"`/`"failed"`/`"unconfirmed"`)를 추가하고,
`gate.py` 안의 기존 생성 지점에서 이 값을 명시적으로 채운다.

**채택: 대안 B. 확정됨 — 아래는 재실측한 생성 지점·소비자 전수다.**

**생성 지점 재실측(11곳, 두 메서드 — "5곳"은 낡은 수였다).**
`grep -n "ExecutionResult(" server/safety/gate.py` 로 다시 세면 **11개**
호출부가 **두 개의 서로 다른 메서드**에 걸쳐 있다:

- `deploy_plugin_source()`(845~900행, M7 플러그인 배포 전용 — 이 SPEC 의
  `execution_port` 경로와 무관) — 5곳(861·865·890·892·900행).
- `_execute_cleared()`(904~950행 — `_GateExecutor.execute()`(148행)가
  호출하고, `BundleSender`/관측 도구가 실제로 타는 경로가 여기다) — 6곳
  (917·921·927·940·943·950행).

**M1 의 범위는 `_execute_cleared()` 의 6곳뿐이다** — 이 SPEC 이 만드는
`send()`/관측 도구가 지나가는 유일한 경로이기 때문이다(REQ-LDSEND-001/003).
`deploy_plugin_source()` 의 5곳은 이 SPEC 의 PRESERVE 대상(§3)이고 손대지
않는다 — **다만 정직하게 밝힌다**: 그 5곳을 안 고치면 `outcome` 필드
기본값(`"ok"`)이 `ok=False` 인 반환값에도 그대로 남는다(예: 861행
`ExecutionResult(ok=False, detail="blocked: ...")` 는 `outcome="ok"` 로
읽힌다). 이는 이 SPEC 이전부터 있던 계약 불일치이고, `deploy_plugin_source()`
의 유일한 소비자(`server/deploy/pipeline.py`)는 `outcome` 필드를 읽지 않는
`.ok`/`.detail` 전용 소비자이므로 오늘은 관측 가능한 결함이 아니다 — 이
SPEC 은 이 불일치를 **만들지 않지만 고치지도 않는다**. 후속 카드로 남긴다.

**소비자 전수 재실측(D3 정정 — grep 두 갈래로 교차검증).**

1. `ExecutionResult` 이름을 직접 import 하는 소비자:
   `grep -rln "ExecutionResult" server/ --include="*.py" | grep -v "/tests/"`
   → `server/measurement/runner.py`, `server/director/execution.py`(별개
   클래스, §1 D7 각주), `server/web/session.py`, `server/web/panel.py`,
   `server/deploy/pipeline.py`, `server/safety/gate.py`(생산자),
   `server/orchestrator/ports.py`(정의).
2. `execution_port.execute()`/`.execution_port` 를 실제로 부르는(덕타이핑)
   소비자: `grep -rln "execution_port\.execute(\|\.execution_port\b" server/
   --include="*.py" | grep -v "/tests/"` → 위 넷에 더해
   **`server/orchestrator/tools.py:2436`**(`result = execution_port.execute
   (command); if result.ok: ...`) — `.ok`/`.detail` 만 읽고 구조 분해·위치
   인자 소비 없음(직접 읽음, 확인). `server/tools/*_e2e.py` 아홉 파일도 같은
   grep 에 걸리지만, 전부 `execution_port=stack.gate.execution_port` 형태로
   **다른 함수에 전달만** 할 뿐 반환값을 자신이 읽지 않는다(각 파일의 해당
   줄을 직접 읽어 확인) — 별도 소비자가 아니다.

**결론**: 실제 읽기 전용(`.ok`/`.detail` 전용) 소비자는 **다섯**이다 —
`server/measurement/runner.py`, `server/web/session.py`(두 자리:
`outcome_view()` 4401행, `_MeasuredExecutionPort._is_console_result()`
4551-4556행), `server/web/panel.py`, `server/deploy/pipeline.py`,
`server/orchestrator/tools.py:2436`. `outcome` 필드는 선택적 기본값을 가지므로
다섯 모두 영향받지 않는다. acceptance.md §4 no-go 기준은 이 다섯을 전부
반영하도록 정정했다(D3) — 그리고 최종 백스톱은 여전히 `uv run pytest -q`
전체 회귀다.

**추가 발견(부수 이득, 이 SPEC 범위 밖)**: `server/web/session.py:4401,4556`
와 `server/measurement/runner.py:193` 셋은 이미 `UNCONFIRMED_MARKER =
"execution unconfirmed"`(정확히 대안 A 가 경고한 그 문자열 스니핑)를
`.detail` 에 대고 쓰고 있다. 대안 B 의 `outcome` 필드는 이 기존 세 자리도
문자열 스니핑에서 벗어나게 할 수 있지만, 그 마이그레이션은 이 SPEC 의
PRESERVE 경계(§3) 밖이므로 여기서 하지 않는다 — 후속 카드로 남긴다.

### (나) `SafetyGate` 클리어런스 회수 메서드와 세션 격리 — **확정(사람 확인 완료, 2026-09-18)**

**문제**: `execute_preapproved()`(`gate.py:645`)는 성공 시
`self._clearances[session_key] = Counter(commands)` 로 세션별 카운터를
덮어쓴다. `_execute_cleared()`(`gate.py:922-930`)는 명령 하나를 보낼 때마다
그 카운터에서 하나씩 줄인다. **문제는 이 카운터를 명시적으로 비우는 API 가
오늘 존재하지 않는다는 것이다** — 다음 `screen()`/`execute_preapproved()`
호출이 같은 세션 키로 다시 올 때까지, 다 안 쓴 클리어런스는 그대로
남는다. `BundleSender` 가 REQ-LDSEND-002 대로 번들 중간에 송신을 멈추면,
남은 명령들의 클리어런스는 이 apply 요청이 끝난 뒤에도 살아 있다 — 같은
세션 키로 오는 **다른, 무관한** `execution_port.execute(command)` 호출이
그 클리어런스를 우연히 재사용할 수 있다는 뜻이다(같은 명령 문자열이 우연히
같을 때).

**채택**: `SafetyGate` 에 최소 public 메서드를 하나 추가한다 —
`def revoke_clearances(self) -> None:` — 호출한 세션의
`self._clearances[current_session_key()]` 를 빈 `Counter()` 로 되돌린다.
`_clearances_lock` 을 그대로 재사용해 동시성 안전을 지킨다. 다른 세션 키의
카운터는 건드리지 않는다 — `screen()`/`execute_preapproved()` 의 세션별
스코프 불변식(M6c-1, `gate.py` 머리말 19~26행)을 그대로 지킨다.
`GatePort` Protocol(`execution.py:228-238`)도 `def revoke_clearances(self)
-> None: ...` 한 줄을 얻는다 — fake gate 와 실물 `SafetyGate` 양쪽이 그
구조적 타입을 만족해야 하기 때문이다.

**D2 정정 — 세션 자체를 격리하지 않으면 회수는 무의미하다(사람 확인 완료:
전용 세션 + 회수 채택).** plan-audit iter1 이 정확히 지적한 결함: 위
`revoke_clearances()` 는 **호출 세션의** 카운터만 비운다. 그런데 apply
경로 자체가 오늘 어떤 세션 키도 바인딩하지 않는다 — 실측:
`grep -n "bind_session_key\|session_context\|current_session_key" server/
director/*.py server/measurement/runner.py` → **0 매치**. `server/web/
session.py:11650`(`ChatSession`)·`server/web/panel.py:821`(`PanelRuntime`)
만 `bind_session_key()` 를 부른다. 즉 director apply 와
`server/measurement/runner.py` 는 **둘 다** 오늘 암묵적으로 같은
`DEFAULT_SESSION_KEY`(`session_context.py:35`) 를 공유한다 — apply 가
`revoke_clearances()` 를 불러도 그것이 실제로 비우는 것은
"director apply 의 세션" 이 아니라 "`DEFAULT_SESSION_KEY` 를 쓰는 모든
호출자가 공유하는 그 하나의 카운터"다. REQ-LDSEND-006 의 "다른 세션·다른
호출자의 관측 가능 동작을 바꾸지 않는다"는 오늘의 배선에서는 지켜지지
않는다 — 다른 세션이 아니라 **같은(기본) 세션**이기 때문이다.

**채택(전용 세션 + 회수, D2)**: `apply` 요청 하나마다 전용 `SessionKey` 를
새로 발급해 바인딩한다 — REQ-LDSEND-013.

- **바인딩 위치**: `server/director/execution.py` `ApplyCoordinator.apply()`
  가 아니라 **`server/director/director_api.py` `post_apply()`**(404~452행)
  다. `ApplyCoordinator.apply()` 자신은 `execute_bundles()` 를 호출하지
  않는다(코드 실측 — `apply()` 는 `execute_preapproved()` 판정까지만 내고
  `ExecutionResult`(journal 쪽, D7 각주)를 반환한다) — `execute_bundles()`
  는 `post_apply()` 가 `apply()` 반환 직후 별도로 부른다(437-448행). 따라서
  "`execute_preapproved()` 호출 시작부터 `execute_bundles()` 반환·회수
  직후까지"를 한 세션 키로 감싸려면, 그 **둘을 다 부르는** `post_apply()`
  가 감싸는 지점이어야 한다 — `ApplyCoordinator` 내부에 감싸면
  `execute_bundles()` 호출 시점의 세션 키를 알 수 없다.
- **plan.md §3 PRESERVE 의 `director_api.py` 예외**: 이 파일은 형제
  SPEC(`SPEC-LDRECV-001`) 소유로 읽기·호출만 하는 것이 원칙이지만(§3), 이
  변경은 검증·라우팅·승인 판단을 전혀 바꾸지 않는 순수 격리 배선이다 —
  `post_apply()` 본문 맨 앞에서 `token = bind_session_key(new_session_key())`
  하고, `try/finally` 로 감싸 `finally` 에서 `reset_session_key(token)` 을
  부른다(세션.py:11650·panel.py:821 과 같은 기존 관용구). `execute_bundles()`
  호출 직후(성공이든 예외든, `finally` 안에서) `deps.apply_coordinator.
  revoke_clearances()` 를 부른다 — 이를 위해 `ApplyCoordinator` 에 전달
  메서드 하나를 추가한다: `def revoke_clearances(self) -> None: self._gate.
  revoke_clearances()`(순수 위임, `apply()` 의 재검사 순서는 그대로다).
- **AC 갱신(D2)**: acceptance.md AC-LDSEND-005/006 은 이제 **실제
  `DEFAULT_SESSION_KEY` 공유 구성**을 재현해 대조한다 — 세션 키를 바인딩
  하지 않는 fake 호출자(`server/measurement/runner.py` 를 흉내)가
  `execute_preapproved()` 로 클리어런스를 남긴 뒤, apply 가 전용 세션에서
  `revoke_clearances()` 를 불러도 그 fake 호출자의(DEFAULT 세션) 클리어런스가
  안 지워지는지, 그리고 그 역방향(전용 세션의 apply 클리어런스가 DEFAULT
  세션 회수로 안 지워지는지)도 함께 잰다. 예외 발생 시에도 토큰이
  `reset_session_key()` 되는지(즉 다음 요청이 이전 요청의 세션을 물려받지
  않는지)도 별도로 잰다.

### (다) 021 승격부 readback 질의 경로 — **해소(코드로 확정, 더 이상 미확정 아님)**

plan.md §7 이 사람 확인 대기 마커로 남겼던 항목이지만, 코드를 읽으면
이미 확립된 선례가 있다 — 미확정이 아니라 **재사용할 경로가 이미 있다**.
`server/web/cue_monitor.py` 머리말(12-15행)이 명시적으로 적어 뒀다:
"`DataPool/Sequences/<no>` 를 `server/orchestrator/tools.py`의 `drill_into`
가 다른 pool 을 여는 것과 같은 방식으로 연다." 실제 사용 지점 다수 실측—
`server/tools/lxseq_*_e2e.py`, `server/tools/t230_cue_content_survey.py`,
`server/preshow/checks.py`, `server/web/cue_monitor.py` 전부
`state_port.query_state("DataPool/Sequences" [+ "/<N>" [+ "/<cue-index>"]])`
를 부르고, 응답의 `children`(리스트, 각 원소가 `i`/`name`/`childCount`)을
읽어 존재 여부·자식을 판정한다(`t230_cue_content_survey.py:60-73`
`read_state`/`read_children`).

**021 승격부의 readback**은 이 선례를 그대로 따른다 —
`state_port.query_state(f"DataPool/Sequences/{N}")` (또는 부모 pool 을 읽고
`children` 에서 `i == N` 원소를 찾음)으로 object-existence 를 확인한다.
**아직 실기로 확인 못 한 것 하나만 남는다**: 존재하지 않는 `<N>` 을 직접
질의했을 때 콘솔이 `ok:false`(→ `StateQueryError`)로 답하는지, 아니면
`ok:true` + 빈/부재 `node` 로 답하는지 — 이 둘 중 어느 쪽이 "없음"의 응답
모양인지는 M5 에서 실기로 한 번 확인해 이 문서에 반영한다. **질의 경로
자체는 더 이상 미확정이 아니다.**

> **구현 결과(2026-09-19):** M5 실기 관측(5회 일관 — progress.md §E.2
> M5)으로 응답 모양이 확정됐다 — 부재: `ok:false`
> `path segment not found: '<N>'`; 존재: `ok:true` + node
> `class: Sequence`. 여기에 더해 M4 구현은 콘솔 **무응답**
> (`ConsoleSilentError`, `StateQueryError` 의 하위형)을 "비어있음"으로
> 잘못 읽던 결함을 발견해 정정했다 — 무응답은 이제 "비어있음"이 아니라
> **판독 불가**(`empty=None`/`exists=None`)로 다뤄, destination 점유
> 확인은 무응답이면 쓰기를 거부한다(최초 구현 결함 재현 2건 → 수정
> `eee1c4e4`, progress.md §E.2 M4 "무응답 결함 수정" 참고).

### (라) AC-024 실패 유발 명령 — 실기 탐색으로 이연(사람 확인 완료: M4a 신설)

plan.md §7 이 사람 확인 대기 마커로 남겼던 항목. 사람 결정: 후보를 미리
목록화하고 M4a("실기 탐색") 에서 확정한다 — §2 마일스톤 표·§4 참고.
**후보 1(권장, 실측 근거 있음)**: 스크래치 destination 이 **이미 점유된
상태**에서 `Store Sequence <N>`(맨몸, `/Merge`·`Cue` 없음)을 보낸다.
`server/web/session.py:10662`(2026-08-16 실측·사용자 방향)가 이 정확한
형태의 실패를 기록한다: "시퀀스 {N}에 이미 콘솔 데이터가 있어 그대로
저장하면 콘솔이 'Not allowed'로 거부합니다." — 이는 게이트 승인 여부와
무관한, **콘솔 자신의** 명시적 거부다(참고: `Store Sequence` 자체는
`blacklist.yaml` v6 이후 held 이므로 이 도구의 labelled auto-approve
`ApprovalPort` 로 승인을 통과한 **뒤** 콘솔이 별도로 거부한다는 뜻 — 두
층이 다르다, §1 규범표·§2 spec.md 참고). 시나리오: (1) M3~M4 의 첫 bundle 로
scratch `<N>` 에 `Store Sequence <N> Cue 1 /Merge` 를 보내 점유시킨다. (2)
후속 bundle 의 첫 명령으로 같은 `<N>` 에 맨몸 `Store Sequence <N>` 을
보낸다 — 그 bundle 은 `STATE_FAILED` 로 귀결되어야 하고, 그 뒤 bundle 은
전혀 전송되지 않아야 한다(REQ-LDSEND-002/024).
**후보 2(미검증, 대체 후보)**: `Copy Sequence <N> At <occupied-M>` — 이미
점유된 대상으로의 Copy 도 유사하게 거부될 것으로 추정되나 실측 인용이
없다.

> **구현 결과(2026-09-19):** M4a 실기 탐색(progress.md §E.2 M4a — 사람
> 승인 후 실행)에서 후보 ①(`Store Sequence {n}`, 점유된 destination 에
> 맨몸 Store)이 2회 재현 모두 성공해 확정됐다. 다만 콘솔이 실제로 낸
> 거부 사유는 위에서 인용한 `'Not allowed'` 가 아니라
> `User Canceled Command` 였다(감사 로그 실측, 2/2 일치) — 저장 확인
> 팝업이 취소된 것으로 추정(미확인). 후보 ②는 후보 ①이 이미 안정적인
> 명시적 실패를 냈으므로 시도되지 않았다. 후속 bundle 미송신(REQ-002/
> AC-024)은 실기에서도 관측됨(감사 로그 부재 + readback 부재 두 갈래).

**HALT 조건(사람 결정 4)**: M4a 에서 이 두 후보를 실기로 먼저 시도하고,
그 결과를 `progress.md` 에 기록한 뒤에만 `--execute` 경로 스크립트에
확정 명령을 굳힌다 — 확정 전에는 dry-run 출력까지만 완성한다(§6 중단
조건과 동일 취지, 여기서는 별도 마일스톤으로 명시).

> **구현 결과(2026-09-19):** 이 HALT 게이트는 M4 구현에서 CLI 옵션
> `--confirmed-failure-command` 로 구체화됐다 — `--execute` 실행이
> 024/032 시나리오를 고르고 이 옵션이 없으면, **콘솔 스택을 만들기
> 전에** 거부 메시지를 출력하고 exit 1 로 종료한다(세션 시작 백업조차
> 나가지 않는다, progress.md §E.2 M4). M4a 확정 뒤에는
> `--confirmed-failure-command 'Store Sequence {n}'` 로 넘긴다.

### (마) 관측 도구의 apply 경로 — 공유 함수로 real `GateBundleSender`/`execute_bundles` 를 실제로 탄다 — **확정(사람 확인 완료, 2026-09-18, iter2 D9-D11 대응)**

**문제(D9, critical — iter2 감사).** iter1 개정의 REQ-LDSEND-007/012 는
관측 도구의 진입점을 `SafetyGate.screen()` 단독으로 못박았다. 그런데
`screen()` 은 명령 목록 하나를 분류·승인·발급할 뿐, **여러 bundle 에 걸친
중단 판단**은 하지 않는다 — 그 판단은 `execute_bundles()`(`execution.py:
974-1046`)의 일이고, 이 SPEC 이 만드는 `GateBundleSender`(M2)를 그 함수에
주입해야 실제로 관측된다. `execute_bundles()`/`GateBundleSender` 를
실제로 부르는 코드는 오늘 `post_apply()`(`director_api.py:437-448`)
하나뿐이다 — 그리고 그 자리는 이 SPEC 의 §4(spec.md) Out of Scope 가
"지금은 실행 가능한 경로가 아니다"(HTTP 라우팅·credential 발급 미배선,
`director_api.py:273`)라고 명시한 바로 그 경로다. 즉 `screen()` 만 쓰는
도구는 M2 가 만드는 `GateBundleSender` 를 **한 번도 실행하지 않고**, 이
SPEC 이 존재하는 이유(AC-LDPLUGIN-021/024/032 를 실기로 관측하는 것)를
달성하지 못한다.

**D6 판단의 재검토 — 뒤집는 것이 아니라 좁혀 읽는다.** iter1 의 D6 대응은
`execute_preapproved()`(`gate.py:553-660`) 의 자체 ANCHOR 주석
(`gate.py:540-552`)을 "director HTTP 경로만 이 메서드를 부를 수 있다"로
읽었다. 그러나 그 주석을 다시 읽으면 실제 조건은 다르다 — "director 는
이미 자신의 `ApprovalBinding` 을 갖고 있으므로, 일반 `ApprovalPort` 로
다시 묻는 것은 중복 승인이다"(§ 승인 **증거**의 존재가 조건이지, 호출자의
정체가 "director route" 인지가 조건이 아니다). 이 관측 도구가 자기 자신의
진짜 `ApprovalBinding` 을 만들 수 있다면, 그 조건을 충족하는 정당한
호출자가 된다 — 아래가 그 구성 방법이다.

**채택(공유 함수 추출 + 도구 자신의 로컬 승인, REQ-LDSEND-007/012/013/015).**

1. **공유 함수 `run_director_apply()` 를 `server/director/execution.py`
   에 신설한다** — `director_api.py` 가 아니라 `execution.py` 에 두는
   이유: `director_api.py` 는 `fastapi` 를 import 하므로(머리말 실측),
   순수 로컬 관측 하네스가 그 파일을 import 하면 웹 프레임워크 의존이
   따라붙는다. `execution.py` 는 이미 `ApplyCoordinator`/`execute_bundles`
   를 갖고 있어 이 함수가 자연스러운 확장이다. 시그니처(제안):

   ```python
   def run_director_apply(
       *, coordinator: ApplyCoordinator, journal: ExecutionJournal | None,
       bundle_sender: BundleSender | None, interference: InterferenceDetector | None,
       project_id: str, plan_id: str, revision: int, principal_id: str,
       operation: str, current_context_digest: str, body: Mapping[str, Any],
   ) -> tuple[dict[str, Any], int]:  # (response_body, response_status)
   ```

   본문은 `post_apply()`(`director_api.py:404-452`, 이 개정 이전 행
   번호)가 오늘 인라인으로 갖고 있는 것 그대로다 — `bind_session_key
   (new_session_key())` → `coordinator.apply(...)` → (sender 배선돼 있고
   replay 아니면) `execute_bundles(...)` → `finally` 에서
   `coordinator.revoke_clearances()` + `reset_session_key(token)`(REQ-013
   이 이 함수 내부로 이동). `post_apply()` 는 이 함수를 호출하고 그 반환
   튜플을 `JSONResponse` 로 감싸기만 하는 얇은 adapter 가 된다 — 기존
   응답 상태·본문·journal 기록은 바이트 동일해야 한다(REQ-LDSEND-015,
   행동 보존 — 기존 LDRECV apply route 시험이 회귀 백스톱이다).

2. **관측 도구는 자기 자신의 로컬 `DirectorStore`/`ApprovalRegistry`
   인스턴스에서 진짜 `ApprovalBinding` 을 발급한다** — HTTP 라우팅도
   credential 발급도 거치지 않는다(§4 spec.md Out of Scope 불변). 구체적
   구성:
   - 로컬 sqlite(또는 `tmp_path`) `DirectorStore` 를 만들고
     `store.submit(plan={...}, expected_revision=0, ...)` 로 최소 plan
     하나를 심는다(실측 선례:
     `server/tests/test_director_ops_lifecycle.py` `store` fixture,
     84-159행).
   - `ValidationRef`/`ContextRef`(`approvals.py:126,143`)는 평범한
     frozen dataclass 다 — 도구가 그 값을 직접 구성한다(`plan_digest`
     는 방금 심은 plan 을 `store.get(...)` 으로 되읽어 일치시킨다).
   - 로컬 `ApprovalRegistry()` 를 만들고 **공개 API**
     `approvals.approve(store=..., project_id=..., plan_id=..., revision=...,
     principal_id="ldsend-observe-harness", validation=..., context=...,
     body={...}, operation=...)`(`approvals.py:315`)를 호출해 진짜
     `ApprovalBinding` 을 받는다. **주의**: `test_director_ops_lifecycle.py`
     가 쓰는 `_register()` 헬퍼(140-142행)는 `_approvals`/`_latest_by_plan`
     private dict 를 직접 건드리는 **시험 전용** 지름길이다 — 이 도구는
     시험이 아니라 운영에 가까운 하네스이므로 그 지름길을 쓰지 않고
     공개 `approve()` 만 쓴다(REQ-LDSEND-012).
   - `principal_id="ldsend-observe-harness"` 가 REQ-LDSEND-012 가 요구하는
     구분 문자열이다 — 로컬 `ApprovalRegistry`/`DirectorStore` 자체가
     `server/web/serve.py` 운영 조립과 무관한 별도 인스턴스이므로, 배선
     자체가 이미 격리돼 있다(grep 대상은 여전히
     "`director_apply_observe` 가 `serve.py` 에 나타나지 않는다").

3. **`ApplyCoordinator` 는 로컬 journal/approvals/store 와 진짜 gate 를
   섞어 구성한다** — `ApplyCoordinator(journal=<로컬 ExecutionJournal>,
   approvals=<로컬 ApprovalRegistry>, store=<로컬 DirectorStore>,
   gate=stack.gate)` — `gate` 만 `build_console_stack()` 이 만든 **진짜**
   `SafetyGate` 다. 시나리오 함수는 `run_director_apply(coordinator=...,
   journal=<같은 로컬 journal>, bundle_sender=<진짜 GateBundleSender>,
   ...)` 를 호출한다 — 이것이 director HTTP 경로와 **동일한 코드
   경로**(`ApplyCoordinator.apply()` → `execute_preapproved()` →
   `execute_bundles()` → `GateBundleSender.send()` → 진짜 콘솔)를 타는
   지점이다.

4. **D10 은 이 추출로 구조적으로 해소된다.** 세션 바인딩/회수(REQ-013)가
   `run_director_apply()` 내부에 있으므로, 관측 도구가 그 함수를 부르는
   순간 자동으로 전용 세션을 얻는다 — 별도의 "도구 자신의 세션 격리"
   배선을 추가로 설계할 필요가 없다.

5. **D11 — dry-run 이 세션 시작 백업을 실제로 보내던 결함.**
   `build_console_stack(attempt_session_backup=True, ...)`(기본값,
   `bootstrap.py:106`)는 구성 시점에 `stack.attempt_session_backup()`
   을 호출해 실제 `SaveShow` 를 콘솔로 보낸다(`bootstrap.py:185-189`,
   `backup.py:147-149` `session_start()`). `--execute` 이전에 인자
   파싱만으로 이 부작용이 발생하면 REQ-LDSEND-009 의 "dry-run 은 아무것도
   안 보낸다" 약속이 깨진다. **채택**: 도구는 인자 파싱을 **먼저** 끝내고
   (`--execute` 여부 확정), dry-run 이면 `build_console_stack
   (attempt_session_backup=False, ...)` 로, `--execute` 면 기본값
   (`True`)으로 스택을 구성한다. `--execute` 경로에서도 스택 구성이 실제
   `SaveShow` 를 보낸다는 사실을 도구가 dry-run 계획 출력에 명시적으로
   한 줄 적어(예: "이 실행은 세션 시작 시 실제 콘솔 백업(SaveShow)을
   보냅니다") 사람이 `--execute` 를 누르기 전에 그 사실을 볼 수 있게
   한다 — `--execute` 플래그 자체가 이미 "콘솔에 쓰겠다"는 명시적
   동의이므로 별도 확인 프롬프트를 추가하지는 않는다.

   > **구현 결과(2026-09-19):** 실기 관측(M4a·M5, progress.md §E.2)으로
   > `SaveShow` 송신 빈도가 확정됐다 — 세션 시작 1회 + `--execute` 실행
   > 중 승인된 배치(batch)마다 1회이며, **명령 단위가 아니다**. M4 GREEN
   > 구현 시점에 코드 주석으로 남긴 "`Store Sequence` 는 blacklist held
   > 이므로 apply 마다 위험 명령 직전 백업이 나갈 것으로 예상"이라는
   > 추정은 이 실측으로 반증됐다(진짜 빈도는 명령 단위가 아니라 승인
   > 배치 단위) — 모든 실행에서 `backup_precondition: ok` 로 확인됐다.

6. **D12 — REQ-008 "run" 범위.** "run" = CLI 1회 호출 = 시나리오 1개로
   명문화한다(spec.md REQ-LDSEND-008 갱신). AC-024 시나리오가 의도적으로
   재사용하는 "이미 점유된" 대상은 **그 시나리오 자신이 같은 실행 안에서
   먼저 채운** destination 이므로(§2.0-라 1단계), "처음 쓰려는 시도"
   가드의 대상이 아니다 — 그 가드는 도구가 새로 골라 쓰려는 destination
   에만 적용된다.

**이 결정이 spec.md §5 의 go-table 을 바꾸지는 않는다** — 오히려 그
표가 이미 주장한 "M5 가 AC-LDPLUGIN-021/024/032 를 관측한다"를 이제
실제로 달성 가능하게 만드는 결정이다(수정 전에는 `screen()` 만으로는
그 표의 주장이 성립하지 않았다).

## 2. 마일스톤

착수 순서를 정하는 원리: 되돌리기 가장 비싼 인터페이스 결정을 먼저
확정하고(M1), 그 인터페이스 위에 실물 송신기를 얹고(M2), 사람이 보는 CLI
동작(dry-run/`--execute`)을 정하고(M3), 그 위에 실제 시나리오 배선을
쌓고(M4), 실기 탐색으로 미확정 실패 명령을 확정하고(M4a), 마지막으로
코드가 아닌 실기 관측을 수행한다(M5).

| 단계 | REQ | 파일 소유 | 완료 산출물 | 콘솔 | TDD |
|---|---|---|---|---|---|
| M1 인터페이스 확정 | 003, 005, 006, 013, 015 | 기존 `server/orchestrator/ports.py` **EXTEND**(`outcome` 필드); 기존 `server/safety/gate.py` **EXTEND**(`revoke_clearances()` 추가 + `_execute_cleared()` 의 6곳 `ExecutionResult(...)` 생성에 `outcome=` 채움 — §2.0-가, `deploy_plugin_source()` 의 5곳은 PRESERVE); 기존 `server/director/execution.py` **EXTEND**(`GatePort` Protocol 에 `revoke_clearances` 추가, `ApplyCoordinator.revoke_clearances()` 위임 메서드 추가, 신규 `run_director_apply()` 공유 함수 — §2.0-마·REQ-015); 기존 `server/director/director_api.py` **EXTEND**(`post_apply()` 본문을 `run_director_apply()` 호출로 교체 — 행동 보존); 기존 `server/tests/test_safety_gate.py` **EXTEND**; 신규 `server/tests/test_run_director_apply.py`(공유 함수 자체의 단위 시험 — fake coordinator/journal/sender) | `revoke_clearances()` 가 자기 세션 카운터만 비운다, `ExecutionResult.outcome` 이 ok/failed/unconfirmed 를 정확히 구분, `run_director_apply()` 가 전용 세션을 바인딩하고 예외에도 되돌린다(DEFAULT_SESSION_KEY 공유 호출자와 교차하지 않음), 기존 LDRECV apply route 시험(`test_director_ops_lifecycle.py`·`test_director_apply_rejection.py`)이 추출 후에도 그대로 통과한다(REQ-015 행동 보존) | 아니오 | RED 먼저 |
| M2 실물 송신기 | 001, 002, 004 | 신규 `server/orchestrator/bundle_sender.py`(`GateBundleSender` 클래스, `BundleSender` Protocol 구현); 신규 `server/tests/test_bundle_sender.py` | 순서대로 송신, 첫 미확인 뒤 중단, 넷 중 하나의 상태 반환, 콘솔 링크 예외를 unconfirmed 로 흡수 — 클리어런스 회수(M1)는 M2 의 책임이 아니라 M1 이 배선한 `run_director_apply()` 의 책임이다(§2.0-나/마) | 아니오 | RED 먼저 |
| M3 관측 도구 골격 | 007, 009, 012 | 신규 `server/tools/director_apply_observe.py`; 신규 `server/tests/test_director_apply_observe.py` | `build_console_stack()` 재사용(dry-run 시 `attempt_session_backup=False`, D11), 로컬 `DirectorStore`/`ApprovalRegistry` 구성 + 공개 `approve()` 로 `ldsend-observe-harness` 라벨 `ApprovalBinding` 발급(§2.0-마), `run_director_apply()` 만 호출(`director_api.py` import 안 함, §2.0 D9 — D6 뒤집힘), 인자 파싱, dry-run 기본값, `--execute` 없이는 콘솔에 아무것도 쓰지 않는다는 것(세션 시작 백업 포함)을 fake 콘솔로 확인 | 아니오 | RED 먼저 |
| M4 시나리오 배선 | 008, 010, 011, 014 | `server/tools/director_apply_observe.py` 계속 확장 | AC-021/024/032 세 시나리오 함수(각각 `run_director_apply()` 호출), destination 점유 확인, cleanup **명령 출력**(REQ-011 — 도구는 실행하지 않음), 백업 선행조건 관측 기록 경로(REQ-014) | 아니오(로직) / 예(§4 실행 자체) | RED 가능한 부분만(dry-run 출력 형태, cleanup 출력 형태) |
| M4a 실기 탐색(AC-024 명령 확정) | (§7 미검증, §2.0-라) | 코드 없음 — `progress.md` 기록만, 그 결과로 M4 의 AC-024 시나리오 함수를 확정 | 후보 1(`Store Sequence <N>` on 점유됨)·후보 2 를 onPC 에 먼저 시도한 기록, 채택 명령 확정 | **예** | n/a — 수동, HALT 조건(§2.0-라) |
| M5 실기 관측 | (spec.md §5 콘솔 필요 항목) | 코드 없음 — `progress.md` 기록만 | 021 승격부(readback 응답 모양 확정 포함, §2.0-다)·024 관측부·032 실행부의 관측 기록, cleanup 명령을 사람이 실행한 뒤 destination 이 비었는지, 시나리오 실행 시 백업 선행조건 통과 여부(REQ-014) | **예** | n/a — 수동 |

M1 → M2 → M3 → M4 → M4a → M5. M2 는 M1 의 `revoke_clearances()`/`outcome`
필드가 있어야 완결된다(TDD 로 M1 을 GREEN 으로 만든 뒤 M2 의 fake 게이트가
그 인터페이스를 흉내낸다). M4 는 M3 의 CLI 골격 위에 시나리오를 얹으므로
순서가 뒤바뀌면 다시 쓰게 된다. M4a 는 M4 가 만든 dry-run 출력까지만
완성된 상태에서 실기로 후보 명령을 확정하고, 그 결과로 M4 의 AC-024
시나리오 함수 코드를 마저 채운다 — 그래서 M4a 는 M4 와 M5 사이에 있다(M4
가 "코드 골격+미확정 명령", M4a 가 "명령 확정", M5 가 "그 확정된 코드로
실기 관측"). M5 는 M1~M4a 가 전부 닫힌 뒤에만 의미가 있다 — 실물 송신기
없이, 그리고 확정 안 된 실패 명령으로는 실기를 관측할 수 없다.

> **구현 결과(2026-09-19):** M4 구현은 032 recovery apply 가 원본과
> **다른** scratch destination 에 쓰도록 설계했다 — 원본 destination
> 이 partial 이후에도 create-only 예약이 풀리지 않는다는 실측 근거다
> (`ExecutionJournal._reserve_destination_locked`, progress.md §E.2
> M4). 이 문서는 이 설계 선택을 명문화하지 않았으므로 M5 재확인 대상으로
> 남겼고, M5 실기 관측이 AC-LDPLUGIN-032 실행부 관측으로 이를 뒷받침한
> 뒤 사람이 이 설계를 **인정**했다(2026-09-19, progress.md §E.3) —
> destination 예약 해제 절차는 이 SPEC 이 정하지 않으며 후속 카드
> **t422** 로 넘겼다.

## 3. PRESERVE — 건드리지 않는다

| 영역 | 파일 |
|---|---|
| apply 재검사·직렬화·journal | `server/director/execution.py` 의 `ApplyCoordinator`/`ExecutionJournal` 본체 — `execute_bundles()` 호출부만 새 송신기를 주입할 뿐, 그 함수 자체·`ApplyCoordinator.apply()` 의 재검사 순서는 바꾸지 않는다 |
| SafetyGate 파이프라인 본체 | `server/safety/{grammar,classify,backup,console,monitor,expand,ruleset,blacklist.yaml,programmer_arbiter}.py` — 읽기·호출만. `gate.py` 자체도 §2.0 이 명시한 최소 확장(새 메서드 1개 + `_execute_cleared()` 의 6개 생성 지점에 필드 채움, `deploy_plugin_source()` 의 5곳은 아래 별도 행 참고)만 한다 |
| OSC 송신 | `server/bridge/osc.py` — 이 SPEC 도 직접 import 하지 않는다. `SafetyGate.execution_port` 를 거친다(REQ-LDSEND-001) |
| `ExecutionResult` 소비자 다섯(D3 정정 — "넷"이 아니다) | `server/measurement/runner.py`, `server/web/session.py`(두 자리), `server/web/panel.py`, `server/deploy/pipeline.py`, **`server/orchestrator/tools.py:2436`**(덕타이핑 — `ExecutionResult` 를 import 하지 않고 `execution_port.execute()` 반환값의 `.ok`/`.detail` 만 읽음) — 전부 `.ok`/`.detail` 전용 소비자이므로 §2.0-가의 선택적 필드 추가에 영향받지 않는다. 이 다섯의 코드 자체는 건드리지 않는다. `server/tools/*_e2e.py` 아홉 파일은 `execution_port` 를 다른 함수에 전달만 하므로 별도 소비자가 아니다(§2.0-가) |
| `deploy_plugin_source()` 의 `ExecutionResult(...)` 생성 지점 다섯(`gate.py:861,865,890,892,900`) | M7 플러그인 배포 전용 — 이 SPEC 의 `execution_port` 경로와 무관하다(§2.0-가). `outcome=` 을 채우지 않으며, 그로 인한 기본값(`"ok"`) 불일치는 이 SPEC 이전부터 있던 것으로 후속 카드에 남긴다 |
| 저장·검증·인증층(단, `director_api.py` 는 §2.0-나/마 예외 하나 있음) | `server/director/{models,store,service,context,knowledge,digest,emit,auth,approvals}.py` — 형제 SPEC 소유, 읽고 호출만(`approvals.py` 의 공개 `approve()` API 는 관측 도구가 그대로 **호출**한다 — API 자체는 고치지 않는다). `server/director/director_api.py` 는 원칙적으로 동일하게 PRESERVE 이나, **`post_apply()`** 에 한해 §2.0-마 가 요구하는 대로 본문을 `run_director_apply()` 호출(+ 그 반환 튜플을 `JSONResponse` 로 감싸는 코드)로 교체한다 — 검증·라우팅·승인 판단 순서·응답 상태/본문/journal 기록은 바이트 동일해야 한다(REQ-LDSEND-015, 행동 보존) |
| 스크래치 destination 정책 | `../SPEC-LDRECV-001/spec.md` §2 의 "server-selected 새 Sequence create-only" 원칙을 관측 도구도 그대로 따른다 — overwrite·silent reselection 없음 |

**결정 기록(2026-09-18)**: `server/director` 는 `test_director_boundary.py`
(SPEC-LDSTORE-001)가 보장하는 콘솔 비접촉 상태를 그대로 유지한다. 송신기
구현은 `server/director` 밖, `server/orchestrator/bundle_sender.py` 에 두고
`BundleSender` Protocol 로 주입된다.

> **구현 결과(2026-09-19):** 위 표는 §3 대상을 "읽기·호출만"으로
> 명시했지만, 실제 구현은 회귀 방지를 위해 시험 파일 두 개를 추가로
> 건드렸다 — `server/tests/test_overlap_preserve.py`(`gate.py` 의
> 파일-집합 핀을 69→74 로 수정, `_execute_cleared()` 옛 문면 5줄 추가에
> 따른 삭제 라인 수 변경, 커밋 `75ed61c7`)와
> `server/tests/test_director_ops_lifecycle.py`(`_SpyApplyCoordinator`
> 에 구조적 호환성을 위한 no-op `revoke_clearances()` 추가 —
> `run_director_apply()` 가 `finally` 에서 무조건 그 메서드를 호출하므로
> 없으면 `AttributeError` 로 회귀한다). 두 변경 모두 판정 로직을 바꾸지
> 않는 최소 수정이다(progress.md §E.2 M1·M2).

## 4. TDD 순서 (대표 마일스톤 예시)

### M1 (인터페이스)

1. **RED** `server/tests/test_safety_gate.py` 에 추가: `execute_preapproved()`
   로 클리어런스를 발급한 뒤 `revoke_clearances()` 를 부르면 그 세션의
   `execution_port.execute(command)` 가 더 이상 통과하지 않는지(`ok=False`,
   "not cleared" 사유). 다른 세션 키로 발급된 클리어런스는 어느 세션이
   `revoke_clearances()` 를 불러도 영향받지 않는지(두 세션 키를
   `bind_session_key` 로 각각 만들어 대조). `_execute_cleared` 가 반환하는
   `ExecutionResult.outcome` 이 성공/실패/미확인 세 경로 각각에서
   `"ok"`/`"failed"`/`"unconfirmed"` 인지.
2. **GREEN** `gate.py` 에 `revoke_clearances()` 추가, `_execute_cleared()`
   의 6곳 생성 지점(917·921·927·940·943·950행)에 `outcome=` 채움 —
   `deploy_plugin_source()` 의 5곳은 PRESERVE(§3). `server/orchestrator/
   ports.py` 에 `outcome: str = "ok"` 필드 추가. `GatePort` Protocol
   (`execution.py:228-238`)에 `revoke_clearances` 시그니처 추가.
3. **REFACTOR** 필요 시 `_execute_cleared()` 의 6곳을 작은 헬퍼로 통일.
4. **RED** `server/tests/test_run_director_apply.py`(신규): 세션 키를
   바인딩하지 않은 fake 호출자(측정기 흉내)와 교차로 `run_director_apply()`
   를 호출해 — apply 가 남긴 클리어런스를 fake 호출자가(`DEFAULT_SESSION_KEY`)
   못 쓰는지, fake 호출자가 남긴 클리어런스를 `run_director_apply()` 의
   `revoke_clearances()` 가 안 지우는지, `execute_bundles()` 내부에서 예외가
   나도 `reset_session_key()` 가 호출되는지(다음 요청이 이전 세션을 물려받지
   않는지, mock 토큰으로 확인), replay 경로(`result.replayed=True`)에서는
   `execute_bundles()` 가 호출되지 않는지.
5. **GREEN** `execution.py` 에 `run_director_apply()` 신설 — 본문에
   `bind_session_key(new_session_key())`/`try`/`finally:
   reset_session_key(token)` 감쌈, `coordinator.apply(...)` 호출,
   `execute_bundles()` 반환 직후(같은 `try` 안, 성공이든 예외든 `finally`
   에서) `coordinator.revoke_clearances()` 호출. `ApplyCoordinator` 에
   `revoke_clearances(self) -> None: self._gate.revoke_clearances()` 위임
   메서드 추가(순수 위임, `apply()` 재검사 순서 불변).
6. **RED** 기존 `test_director_ops_lifecycle.py`/`test_director_apply_rejection.py`
   등 `post_apply()` 를 거치는 LDRECV 시험을 착수 시점 그대로 먼저 돌려
   (회귀 기준선), 추출 뒤 다시 돌려 바이트 동일한 응답/상태가 나오는지
   대조한다(REQ-LDSEND-015 행동 보존 — 이 시험들은 이 SPEC 이 새로 작성하는
   것이 아니라 기존 파일을 그대로 재사용하는 회귀 백스톱이다).
7. **GREEN** `director_api.py` `post_apply()` 본문을 `run_director_apply
   (coordinator=deps.apply_coordinator, journal=deps.execution_journal,
   bundle_sender=deps.bundle_sender, interference=deps.interference_detector,
   ...)` 호출 + 그 반환 튜플을 `JSONResponse` 로 감싸는 코드로 교체한다.

### M2 (실물 송신기)

1. **RED** `server/tests/test_bundle_sender.py`: fake 콘솔 링크(즉
   `ConsolePort` 를 흉내내는 fake — `execute(command) -> ExecOutcome`)와
   fake gate(`GatePort` Protocol — `.lock`·`.execute_preapproved()`)를
   주입해 — 전부 ok → `STATE_ACKNOWLEDGED`; 첫 명령이 명시적으로 실패(그 전
   확인된 명령 없음) → `STATE_FAILED`; 중간 명령이 확인 안 됨(timeout) →
   `STATE_UNKNOWN`; 앞선 명령이 이미 확인됐는데 뒤 명령이 명시적으로
   실패(부분 완료) → `STATE_UNKNOWN`(콘솔에 이미 일부가 도달했으므로
   `failed` 로 부를 수 없고, 전부가 확인된 것도 아니므로 `ACKNOWLEDGED` 도
   아니다 — 계약의 "atomic OSC rollback 을 주장하지 않는다"를 이 갈래가
   구체화한다); 콘솔 링크가 예외를 던짐 → 그 명령을 unconfirmed 로 잡고
   번들 전체 `STATE_UNKNOWN`. **클리어런스 회수는 이 시험의 책임이 아니다**
   — `revoke_clearances()` 호출은 M1 이 `run_director_apply()` 에
   배선했다(§2.0-나/마).
   `GateBundleSender.send()` 자신은 `execution_port.execute()` 만 부르고
   회수를 호출하지 않는다 — 이 점을 명시적으로 잰다(fake gate 의
   `revoke_clearances` mock 호출 카운트가 0인지, `send()` 시험 전체에서).
2. **GREEN** `sender.py` 의 `GateBundleSender` 최소 구현.
3. **REFACTOR** 상태 판정 로직을 표 기반 헬퍼로 정리.

**번들 내부 상태 판정 표(REQ-LDSEND-003 의 구체화)**:

| 조건 | 반환 상태 |
|---|---|
| 모든 명령이 확인됨(ok) | `STATE_ACKNOWLEDGED` |
| 첫 명령부터 명시적 실패, 그 전 확인된 명령 없음 | `STATE_FAILED` |
| 어떤 명령이든 confirm 안 됨(timeout) | `STATE_UNKNOWN` |
| 앞서 확인된 명령이 있는 상태에서 뒤 명령이 명시적 실패(부분 완료) | `STATE_UNKNOWN` |
| 콘솔 링크가 예외를 던짐 | `STATE_UNKNOWN`(그 명령을 unconfirmed 로 취급) |

`STATE_SENT` 는 이 구현이 반환하지 않는다 — `ConsoleLink.execute()` 자체가
확인 또는 timeout 까지 블록하므로(`console.py:284-286` 독스트링,
"blocks until confirmed or timeout"), "보냈지만 아직 확인 대기 중"이라는
중간 상태가 `send()` 반환 시점에는 존재하지 않는다. `STATE_SENT` 는 향후
비동기 송신기를 위해 프로토콜 어휘로 남는다.

### M3~M4 (관측 도구)

1. **RED** `server/tests/test_director_apply_observe.py`: fake 콘솔로
   `build_console_stack()` 을 대체해 — 기본 인자(플래그 없음, dry-run)로
   실행하면 `build_console_stack(attempt_session_backup=False, ...)` 로
   불렸는지(mock 호출 인자 확인, D11), 콘솔에 아무 명령도 안 나가고
   계획만 출력되는지(fake send 카운트 0, 세션 시작 백업 포함); `--execute`
   없이는 어떤 인자 조합으로도 실행 경로가 콘솔 쓰기에 도달하지 않는지;
   도구가 `server.director.director_api` 를 import 하지 않는지(정적 grep,
   REQ-LDSEND-007); 로컬 `DirectorStore`/`ApprovalRegistry` 로 만든
   `ApprovalBinding` 의 `principal_id` 가 `ldsend-observe-harness` 인지,
   그리고 그 레지스트리 인스턴스가 fake `ApplyCoordinator` 에만 전달되고
   전역/운영 조립과 무관한지(REQ-LDSEND-012); `run_director_apply()` 가
   정확히 시나리오 개수만큼 호출되는지(mock 호출 카운트); cleanup 단계는
   fake 콘솔로 명령을 보내지 않고 `Delete Sequence <N>` 문자열만
   표준출력에 내는지(REQ-011), 그리고 cleanup 이 어떤 `ApprovalBinding` 도
   만들지 않는지(mock 카운트 0).
2. **GREEN** CLI 골격 + dry-run 출력 + cleanup 출력 + 로컬 plan/승인 구성
   헬퍼(`_build_local_approval(...)`, §2.0-마).
3. 시나리오 함수(021/024/032)는 fake `ApplyCoordinator`(fake gate 주입)로
   `run_director_apply()` 호출 경로와 그 판정 로직(readback 호출 순서,
   destination 점유 확인 순서)만 pytest 로 고정한다 — 실제 onPC 대상
   `--execute` 경로는 M4a(024 의 실패 명령 확정)·M5(수동 실행)의 몫이다.
   백업 선행조건 관측(REQ-014)은 fake `BackupManager`(성공/실패 두 경로)로
   그 관측·기록 로직만 로컬에서 고정한다 — 실제 onPC 통과 여부는 M5.

각 단계마다 `uv run pytest` 관련 파일을 돌려 착수 시점 기준선이 깨지지
않는지 본다(§5).

## 5. 검증 명령

```bash
# 착수 시 기준선 재측정
uv run pytest -q

# 이 SPEC 범위
uv run pytest server/tests/test_safety_gate.py server/tests/test_bundle_sender.py \
  server/tests/test_run_director_apply.py server/tests/test_director_apply_observe.py -q

# 회귀 — ExecutionResult 소비자 다섯(D3 정정: "넷"이 아니다) 전부
uv run pytest server/tests/test_measurement_runner.py server/tests/test_web_session.py \
  server/tests/test_web_panel_execute.py server/tests/test_deploy_pipeline.py \
  server/tests/test_orchestrator_tools.py -q 2>&1 \
  || echo "일부 파일명은 실제 존재 여부를 착수 시 확인한다 — 추정 이름"
# 구현 결과(2026-09-19): server/tests/test_orchestrator_tools.py 는 이
# 저장소에 존재하지 않는다(위 "추정 이름" 각주가 예견한 그대로). 그
# 소비자(server/orchestrator/tools.py:2436)의 회귀는 전용 시험 없이
# 아래 "전체 회귀(기준선 대조)" 의 uv run pytest -q 전체 실행이
# 전이적으로 백스톱한다(progress.md §E.2 M1/M4 E3).

# 세션 격리(D2/REQ-LDSEND-013) + 공유 함수 추출 행동 보존(REQ-LDSEND-015) — post_apply() 회귀
uv run pytest server/tests/test_director_ops_lifecycle.py server/tests/test_director_apply_rejection.py -q

# 전체 회귀 (기준선 대조) — §2.0-가 "다섯 소비자" 전제의 최종 백스톱이기도 하다
uv run pytest -q

# 경계: 이 층은 OSC 를 직접 만지지 않는다
grep -rnE "^\s*(from|import)\s+server\.bridge" server/orchestrator/bundle_sender.py server/tools/director_apply_observe.py \
  || echo "OK - no direct OSC import"

# 경계: 관측 도구가 director_api.py(fastapi 의존)를 import 하지 않는지(D9)
grep -nE "^\s*(from|import)\s+server\.director\.director_api" server/tools/director_apply_observe.py \
  && echo "FAIL: 관측 도구가 director_api(fastapi 의존)를 import 한다" || echo "OK - director_api 미참조"

# 경계: 관측 도구가 공유 apply 경로(run_director_apply)만 쓰는지(§2.0-마)
grep -n "run_director_apply" server/tools/director_apply_observe.py \
  || echo "FAIL: 관측 도구가 공유 apply 경로를 쓰지 않는다"

# 경계: 관측 도구의 로컬 ApprovalRegistry/DirectorStore 가 운영 조립에 배선되지 않았는지
grep -n "director_apply_observe" server/web/serve.py || echo "OK - not wired into serve.py"

# 경계: 관측 도구가 만드는 ApprovalBinding 이 라벨링돼 있는지(REQ-LDSEND-012)
grep -n "ldsend-observe-harness" server/tools/director_apply_observe.py

# 경계: cleanup 이 실제로 명령을 보내지 않는지 — Delete 문자열은 표준출력에만 있어야 한다
grep -n "def cleanup\|Delete Sequence" server/tools/director_apply_observe.py
```

**CI 는 과금 차단으로 죽어 있어 판정 근거가 아니다.** 위 로컬 명령의 출력만
증거로 쓴다. spec.md §5 의 「콘솔 필요 = 예」 항목은 위 명령들로 판정할 수
없다 — M5 의 별도 관측 기록이 증거다.

## 6. 중단 조건

- **§2.0(가)·(나)·(마) 의 인터페이스 결정은 확정됐다(2026-09-18)** —
  재론하지 않는다. 다만 착수 시 `gate.py`/`execution.py`/`director_api.py`/
  `approvals.py` 를 다시 읽어 이 문서가 인용한 행 번호·시그니처가 그대로인지
  확인한다(아래 둘째 항목). 특히 `ApprovalRegistry.approve()`(§2.0-마)의
  파라미터 시그니처가 바뀌었으면 관측 도구의 로컬 승인 구성 코드를 그에
  맞춰 다시 쓴다.
- `server/measurement/runner.py`/`server/web/session.py`/
  `server/web/panel.py`/`server/deploy/pipeline.py`/`server/orchestrator/
  tools.py:2436`(다섯, D3 정정) 중 하나라도 `.ok`/`.detail` 외의 필드를
  구조 분해나 위치 인자로 소비하고 있는 것이 발견되면(§2.0-가의 "읽기 전용
  소비자" 전제가 반증되면) 중단하고 대안 A(문자열 판별)로 재조정한다.
- `SPEC-LDRECV-001` 이 확정한 `ApplyCoordinator.apply()` 의 재검사 순서나
  `execute_bundles()` 의 시그니처, 또는 `director_api.py` `post_apply()`
  가 `apply()`→`execute_bundles()` 를 부르는 순서(§2.0-나가 세션 바인딩의
  근거로 삼는 그 순서)가 이 문서가 인용한 것과 다르면(코드가 이 문서 작성
  뒤 바뀌었으면) 중단하고 다시 읽는다.
- M4a 실기 탐색(§2.0-라)이 두 후보 모두 안정적인 명시적 실패를 못 낸다고
  확인하면, `--execute` 경로를 스크립트에 굳히지 않고 다시 원인을 코드에서
  찾는다 — 추측으로 세 번째 후보를 만들지 않는다.
- `blacklist.yaml` 의 버전이 이 문서 작성 시점(9)과 다르면(착수 전 재확인),
  `Store Sequence`/`Store Cue` 의 블랙리스트 소속 여부를 다시 확인하고
  §2.0-라·REQ-LDSEND-007/012 의 전제를 재검산한다.

## 7. 미검증 (착수 전 남은 것)

> **구현 결과(2026-09-19):** M4a·M5 실기 관측(progress.md §E.2 M4a·M5)이
> 완료돼 아래 항목 중 콘솔 필요 항목은 전부 관측 완료로 닫혔다 — 남는
> 것은 §2.0-마 032 recovery destination 설계와 §2.0-다 응답 모양처럼
> 사람 확인/문서 정정 대상으로 넘어간 몇 건과, LOC 추정처럼 이 SPEC이
> 애초에 재지 않기로 한 항목뿐이다.

- **AC-024 관측 시나리오의 "안전한 실패 유발 명령"은 후보 2개로 좁혀졌다
  (해소 — §2.0-라, 인간 결정 4).** M4a 에서 실기로 확정하고 이 문서를
  갱신한다 — 더 이상 사람 확인 대기 마커가 아니라 명시적 마일스톤이다.

  > **구현 결과(2026-09-19):** 후보 ①(`Store Sequence {n}`)로 확정됨
  > (§2.0-라 blockquote 참고, progress.md §E.2 M4a).
- **021 승격부의 readback 질의 경로는 코드로 확정됐다(해소 — §2.0-다).**
  남은 것은 존재/부재를 가르는 정확한 응답 모양(`ok:false` vs 빈
  `children`)뿐이고, 이는 M5 실기 관측 한 항목으로 축소됐다 — 더 이상
  경로 자체가 미지수가 아니다.

  > **구현 결과(2026-09-19):** 응답 모양 확정됨(§2.0-다 blockquote
  > 참고, progress.md §E.2 M5).
- **cleanup 의 스크래치 destination 정확한 번호 범위는 정책만 정했다.**
  "높은 미사용 Sequence 번호대, 쓰기 전 비어 있는지 확인, 점유돼 있으면
  거부"라는 정책(REQ-LDSEND-008)만 확정했고, 정확한 시작 번호는 M3~M4
  착수 시 CLI 인자(`--sequence-range-start`, 기본값 제안 9900)로 남긴다 —
  스크립트에 하드코딩하지 않는다.
- **§2.0-가의 "읽기 전용 소비자" 전제는 두 갈래 grep 확인이지 전수 대조가
  아니다.** 다섯 중 하나가 실은 `ExecutionResult` 를 위치 기반으로 소비하고
  있을 가능성은 M1 착수 시 각 파일을 직접 읽어 다시 확인한다(§5 의 회귀
  명령이 최종 백스톱이다).
- **REQ-LDSEND-014 의 백업 실패 시 후속 절차가 상세하지 않다.** "readback
  판정과 구분해 기록한다"까지만 요구했고, 백업 실패가 확인되면 그 실행을
  중단할지 경고만 남기고 계속할지는 M4 착수 시 코드로 결정한다 — 안전
  방향은 계속하지 않는 쪽이므로 기본값은 "중단+기록"으로 잠정한다.

  > **구현 결과(2026-09-19):** "중단+기록"으로 구현됨 —
  > `_backup_failure_detail()` 이 backup 실패를 감지하면
  > `backup_precondition="failed"` 로 반환하고 readback 을 **시도하지
  > 않는다**(progress.md §E.2 M4). M5 실기 관측에서는 5회 전부
  > `backup_precondition: ok` 였다.
- **로컬 `ApprovalRegistry`/`DirectorStore` 구성이 도구 안에서 몇 줄로
  끝나는지 재지 않았다(§2.0-마).** `test_director_ops_lifecycle.py` 의
  fixture 규모(약 20줄)로 어림했지만, 공개 `approve()` API 는 그 시험이
  쓰는 private dict 지름길보다 인자가 많아 실제 코드량은 M3 착수 시 확정한다.
- **LOC 추정 없음.** Tier M 으로 잡았으나(§1, spec.md — 새 파일 3개
  (`sender.py`, `director_apply_observe.py`, 그 시험들) + 공유 파일
  5개(EXTEND — `ports.py`, `gate.py`, `execution.py`(`run_director_apply()`
  신설 포함, §2.0-마), `director_api.py`) + 신규 시험
  `test_run_director_apply.py` + 콘솔 게이트 항목 몇 건의 규모로 판단, 예상
  800~1300 LOC — iter2 §2.0-마 반영으로 iter1 추정(700~1100)보다 늘었다),
  실제 구현 규모는 재지 않았다.
- **독립 plan-audit 완료(갱신) — iter1 FAIL 0.75, iter2 FAIL 0.63(STOP),
  이 개정으로 D9-D12 반영.** `.moai/reports/plan-audit/SPEC-LDSEND-001-
  review-1.md` 가 iter1, `-review-2.md` 가 iter2 결과다. iter1 의 D1-D8 은
  iter2 감사에서 전부 회귀 확인(재발 없음)됐다. iter2 의 D9(critical)는
  §2.0-마 신설 + REQ-LDSEND-007/012/013/015 재정의로, D10 은 세션 바인딩을
  공유 함수 내부로 옮김으로써 구조적으로, D11 은 REQ-LDSEND-009 확장으로,
  D12 는 REQ-LDSEND-008 명문화로 반영했다 — Retry Loop Contract 에 따라
  iter3(3-iteration 상한의 마지막 회차) 재심사를 받는다(§ delta-scoped,
  D9-D12 + D1-D8 회귀 재확인).

  > **구현 결과(2026-09-18):** iter3 **PASS 0.86**
  > (`.moai/reports/plan-audit/SPEC-LDSEND-001-review-3.md`). iter3 가
  > 지적한 D13(문장 잔재)은 `3c6aa451`·`7804dc13` 으로 정정됐다
  > (progress.md §G).
