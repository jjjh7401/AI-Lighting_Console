# SPEC-COPILOT-BULKGATE-001 — 수용 기준

> 모든 기준은 **기계로 확인 가능**하다. 각 항목은 실행할 명령과 단언할 값을 함께 적는다.
> 기준 트리: `main` `b7b030a` (2026-09-07)
> 검증 인터프리터: 워크트리 안의 인터프리터. 그 귀속을 progress 에 남긴다(`server/tests` 하위에서 `import server; print(server.__file__)`).
> 콘솔: 가짜 콘솔(`server/tests/fake_console.py`)과 브라우저. 실기 grandMA3 발사 0건.

---

## §D 수용 기준 표

| AC | 대응 REQ | 층 |
|---|---|---|
| AC-BULKGATE-001 | REQ-001 | 오프라인 (기본값에서 동작 불변) |
| AC-BULKGATE-002 | REQ-002 | 오프라인 (선언 → 번들 전체 보류) |
| AC-BULKGATE-003 | REQ-003 | 오프라인 (감사 사건) |
| AC-BULKGATE-004 | REQ-002, REQ-008 | 오프라인 (카드 한 장) |
| AC-BULKGATE-005 | REQ-005 | 오프라인 (거절 → 0건 · 락/백업 순서) |
| AC-BULKGATE-006 | REQ-004 | 오프라인 (모델 도달 불가) |
| AC-BULKGATE-007 | REQ-006, REQ-007, REQ-009 | 오프라인 (곡 경로) |
| AC-BULKGATE-008 | REQ-010, REQ-012, REQ-013 | 오프라인 (전수 조사) |
| AC-BULKGATE-009 | REQ-011 | 오프라인 (전수 조사 — 음성 대조) |
| AC-BULKGATE-010 | REQ-014, REQ-015 | 오프라인 (부수 피해 0) |
| AC-BULKGATE-011 | REQ-016 | 오프라인 (고정 파일 문면) |
| AC-BULKGATE-012 | REQ-006..009 | 브라우저 실측 |

---

## §D.1 선언 통로

### AC-BULKGATE-001 — 선언이 없으면 오늘과 같다

- **Given** `SafetyGate.screen` 이 키워드 전용 `risk` 를 얻었다.
- **When** `python -m pytest server/tests/test_safety_gate.py server/tests/test_writegate.py -q` 를 실행한다.
- **Then** 전량 초록이고 새 실패 0건이다 — `risk` 를 안 넘기는 기존 호출자의 동작이 바뀌지 않았다.
- **그리고** `git diff origin/main..HEAD -- server/safety/classify.py server/safety/ruleset.py server/safety/grammar.py server/safety/blacklist.yaml` 이 **빈 출력**이다.

### AC-BULKGATE-002 — 선언은 safe 번들 전체를 보류로 만든다

- **Given** 명령 전부가 `classify_command` 에서 `safe` 로 판정되는 번들(예: `Store Sequence 210 Cue 1 /Merge` 를 포함한 `Store Sequence`/`Store Timecode` 계열 다수).
- **When** 승인을 항상 거절하는 포트를 붙인 게이트에 `screen(commands, risk=BatchRisk(reason=…, kind="songcue"))` 를 부른다.
- **Then** 판정이 `cleared=False` 이고, 같은 명령을 `risk=None` 으로 부르면 `cleared=True` 다 — **같은 명령, 선언 유무만 다른 두 호출**이 갈린다.
- **그리고** 승인 포트가 받은 `ApprovalRequest.commands` 가 번들의 **모든** 명령을 담는다(`safe` 로 분류된 것 포함) — 부분집합이 아니다.

### AC-BULKGATE-003 — 판단이 감사에 남는다

- **Given** 같은 선언 번들.
- **When** 수락 회차와 거절 회차를 각각 돌리고 감사 로그를 읽는다.
- **Then** 수락 회차에 `{"event": "approved", …, "kind": "songcue"}` 가 **1건**, 거절 회차에 `{"event": "rejected", …, "kind": "songcue"}` 가 **1건** 있다.
- **그리고** 「`executed N, blocked 0, approved 0`」 — t291·t294·t296 이 남긴 모양 — 이 이 경로에서 **재현되지 않는다**: 실행 사건이 있는 회차에는 `approved` 사건이 반드시 함께 있다.

### AC-BULKGATE-004 — 카드는 묶음당 한 장이다

- **Given** 명령 N 건(N ≥ 20)인 선언 번들. 그중 일부는 분류상 이미 risky 다.
- **When** `screen(commands, risk=…)` 를 부르고 승인 포트의 호출 횟수를 센다.
- **Then** `request_approval` 호출이 **정확히 1회**다 — N 회도 2회(선언 경로 + 분류 경로)도 아니다.
- **그리고** 그 한 요청 안에서 분류가 준 `risk_reasons`/`warnings` 를 가진 항목이 자기 값을 **잃지 않는다**.

### AC-BULKGATE-005 — 거절은 0건 발사이고, 수락은 순서를 지킨다

- **Given** 선언 번들과 기록형 콘솔 포트.
- **When** ① 거절 회차 ② 수락 회차를 돌린다.
- **Then** ①에서 콘솔 포트가 받은 명령이 **0건**이고 판정이 비청산이다. 채널 미결선·시간 초과에서도 같다(포트를 안 붙인 회차로 확인).
- **그리고** ②에서 **락 재확인**과 **위험 경로 백업**이 승인 **뒤**·청산 **앞**에 실행됐다 — 승인 도중 락이 켜진 회차에서 판정이 비청산이고 발사가 0건이다(`gate.py` 의 lock-FIRST 순서가 선언 경로에서도 유지된다).

### AC-BULKGATE-006 — 모델은 선언을 만질 수 없다

- **Given** 선언을 붙인 곡 경로.
- **When** `ToolCall(name="run_commands", arguments={"commands": [...], "risk": None})` 로 도구를 부른다 — 모델이 선언을 끄려 시도하는 모양.
- **Then** 선언이 살아 있어 승인이 요구되고, 거절 시 발사가 0건이다.
- **그리고** `grep -n 'arguments.*\brisk\b' server/orchestrator/tools.py` 가 **0행**이거나, 있다면 그 자리가 「무시한다」는 것을 단언하는 검사와 짝이다.
- **그리고** **뮤테이션**: `prepare_songcue` 의 `risk=` 인자를 지우면 이 SPEC 의 검사 중 최소 하나가 **실패**한다. 그 실패 출력을 인용하고 되돌린다.

---

## §D.2 곡→콘솔 경로

### AC-BULKGATE-007 — 곡 반영이 승인을 요구하고, 거절하면 아무것도 안 나간다

- **Given** 확정 구간을 가진 세션과 가짜 콘솔, 그리고 `prepare_songcue` 가 명령을 만들어 내는 입력.
- **When** ① 승인을 거절하는 채널로 `prepare_songcue` 를 실행 ② 수락하는 채널로 실행.
- **Then** ①에서 콘솔 포트가 받은 명령이 **0건**이고, 결과 문면이 「콘솔에 0건 나갔다」는 취지를 담으며 **부분 반영을 주장하지 않는다**. 확정 구간과 타임라인이 그대로 남는다.
- **그리고** ②에서 `Store Sequence <N> Cue …` 와 `Store Timecode <slot>` 이 콘솔에 도달하고, 승인 요청은 **한 번만** 있었다.
- **그리고** 승인 요청의 `reason` 문면이 네 가지를 전부 담는다: 시퀀스 번호 · 큐 건수 · 타임코드 슬롯 번호 · 복원 경로 없음.

---

## §D.3 여섯 번째 경로

### AC-BULKGATE-008 — 디스패치 자리가 전수로 분류된다

- **Given** `server/tests/test_write_dispatch_census.py`.
- **When** `python -m pytest server/tests/test_write_dispatch_census.py -q` 를 실행한다.
- **Then** 초록이며, 검사가 `server/orchestrator/tools.py` 와 `server/web/session.py` 에서 찾은 `name="run_commands"` 자리 수가 두 표의 항목 수 합과 **같다**. 이 회차의 관측 수를 progress 에 적는다(plan 단계 실측: 12 + 16 = 28).
- **그리고** 한 자리가 두 표에 동시에 등재되면 실패하는 단언이 존재한다.
- **그리고** `SHOWFILE_WRITE_DISPATCHES` 의 각 자리에 대해, 감싸는 함수 본문에 `risk=` · `request_approval(` · `_accept_` 중 하나가 있음을 단언한다.
- **그리고** 검사의 독스트링이 한계를 적는다 — 정적 텍스트 주사이며 간접 호출은 못 잡는다.

### AC-BULKGATE-009 — 전수 조사가 공허하지 않다 (음성 대조)

- **Given** 초록인 전수 조사 검사.
- **When** 두 표 어디에도 없는 `name="run_commands"` 디스패치 자리를 하나 심고 검사를 돌린 뒤 **되돌린다**.
- **Then** 검사가 **실패**하고 실패 문면에 그 파일과 행 번호가 들어 있다. 그 출력의 꼬리를 progress 에 인용한다.
- **그리고** 되돌린 뒤 같은 명령이 다시 초록이고 `git status --porcelain` 이 비어 있다.

---

## §D.4 안 움직인 것

### AC-BULKGATE-010 — 룩 생성·FX·씬은 그대로다

- **Given** 이 SPEC 은 분류를 안 넓혔다.
- **When** `python -m pytest server/tests/test_safety_ruleset.py server/tests/test_fx_boundary.py server/tests/test_scene_boundary.py "server/tests/test_web_session.py::TestLastCreatedSessionTracking" -q` 를 실행한다.
- **Then** 전량 초록이고 실패 **0건**이다 — t292 가 분류 확대 경로에서 잰 부수 피해 8건이 **발생하지 않았다**.
- **그리고** `git diff --stat origin/main..HEAD -- server/tests/test_safety_ruleset.py server/tests/test_fx_boundary.py server/tests/test_scene_boundary.py server/tests/test_web_session.py` 가 **빈 출력**이다 — 초록을 만들기 위해 검사를 고친 것이 아니다.
- **그리고** `git diff --stat origin/main..HEAD -- server/safety/blacklist.yaml` 이 빈 출력이다.

### AC-BULKGATE-011 — 고정 파일은 단언 불변, 문면만 갱신

- **Given** `server/tests/test_writegate_merge_gap.py`.
- **When** `git diff origin/main..HEAD -- server/tests/test_writegate_merge_gap.py` 를 읽고, 그 파일을 실행한다.
- **Then** 변경 hunk 가 **모듈 독스트링 안에만** 있고 `UNCARDED_SEQUENCE_WRITES` 와 네 개 검사 본문에는 hunk 가 **0건**이다. 특히 `assert "Store Sequence" not in RULESET.blacklist` 가 그대로다.
- **그리고** 파일 전량 초록이다.
- **그리고** 새 독스트링이 **전/후를 함께** 적는다 — 전: 노출이 열려 있고 고칠 자리는 `blacklist.yaml` 이라고 적혀 있었다. 후: 노출은 디스패치 층의 번들 선언으로 닫혔고, 분류는 **의도적으로** 안 움직였으며 그 이유는 부수 피해 8건이다. 그리고 이 SPEC ID 가 문면에 들어 있다(`grep -c 'SPEC-COPILOT-BULKGATE-001' server/tests/test_writegate_merge_gap.py` ≥ 1).

---

## §D.5 브라우저 실측

### AC-BULKGATE-012 — 감독이 보는 화면이 달라졌다

- **Given** 앱을 띄우고 가짜 콘솔에 연결한 브라우저 회차.
- **When** 곡 파일 하나를 올려 2026-09-07 회차와 같은 흐름을 태운다.
- **Then** 명령이 나가기 **전에** 승인 카드가 뜨고, 그 카드가 시퀀스 번호·큐 건수·타임코드 슬롯·복원 경로 없음을 문면에 담는다. 「주의」 배지만 있고 승인 컨트롤이 없던 상태가 재현되지 않는다.
- **그리고** 거절하면 가짜 콘솔이 받은 명령이 **0건**이고, 화면이 「콘솔에 0건 나갔다」는 취지를 말한다.
- **그리고** 수락하면 명령이 **한 번에** 나가고 명령마다 카드가 다시 뜨지 않는다.
- **그리고** 두 회차의 감사 로그가 각각 `approved` 1건 / `rejected` 1건을 담는다. 관측한 명령 수를 progress 에 적되, **28이라는 값 자체는 기준이 아니다**(곡·리그가 다르면 달라진다).

---

## §D.6 완료 정의 (Definition of Done)

- AC-001..012 전부 PASS 이며 각 항목이 **실행한 명령과 그 출력**으로 뒷받침된다.
- `server/tests` 전량 초록, 새 회귀 0건. 전체 건수를 실패 건수와 **나란히** 적는다(분모 인용 규율).
- 뮤테이션 둘의 실패 출력이 인용돼 있고 되돌림이 diff 로 확인된다: ① 게이트의 선언 처리 분기 삭제 ② `prepare_songcue` 의 `risk=` 인자 삭제.
- 음성 대조(등재 없는 디스패치 자리 심기)의 실패 출력이 인용돼 있다.
- `server/safety/blacklist.yaml` 과 부수 피해 8건 파일의 diff 가 0.
- 브라우저 회차 두 갈래(수락·거절)의 관측이 남아 있다.
- **미검증 항목이 progress 에 명시적으로 열거된다.** 최소한 다음은 이 SPEC 이 닫혀도 미검증으로 남는다:
  - 실기 grandMA3 에서의 발사 (가짜 콘솔로만 확인)
  - 선언을 안 붙인 나머지 디스패치 자리의 실제 쓰기 여부 — 전수 조사는 **분류**를 강제할 뿐 각 자리의 안전을 보장하지 않는다
  - 간접 호출로 만들어진 디스패치 자리 (정적 주사의 한계)
  - t292 가 잰 「13건 / 부수 8건」의 재현 — 이 SPEC 은 분류를 안 넓히므로 그 숫자를 다시 만들지 않는다
