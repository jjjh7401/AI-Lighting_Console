# SPEC-COPILOT-POOLEMPTY-001 — 수용 기준

> 모든 기준은 **기계로 확인 가능**하다. 각 항목은 실행할 명령과 단언할 값을 함께 적는다.
> 기준 트리: `main` `f727e11` (2026-09-06)

---

## §D 수용 기준 표

| AC | 대응 REQ | 층 |
|---|---|---|
| AC-POOLEMPTY-001 | REQ-001, REQ-004, REQ-013 | 오프라인 (lupa) |
| AC-POOLEMPTY-002 | REQ-001, REQ-003, REQ-013 | 오프라인 (lupa) |
| AC-POOLEMPTY-003 | REQ-002 | 오프라인 (lupa) |
| AC-POOLEMPTY-004 | REQ-005 | 오프라인 (grep + 회귀) |
| AC-POOLEMPTY-005 | REQ-006 | 오프라인 (문서 + 리터럴) |
| AC-POOLEMPTY-006 | REQ-007 | 오프라인 (앱) |
| AC-POOLEMPTY-007 | REQ-008 | 오프라인 (앱, 하위 호환) |
| AC-POOLEMPTY-008 | REQ-008 | 오프라인 (앱) |
| AC-POOLEMPTY-009 | REQ-009 | 오프라인 (앱, 불변) |
| AC-POOLEMPTY-010 | REQ-010 | 오프라인 (프로브) |
| AC-POOLEMPTY-011 | REQ-011 | 오프라인 (크로스파일) |
| AC-POOLEMPTY-012 | REQ-012 | 오프라인 (게이트) |
| AC-POOLEMPTY-013 | REQ-014 | 실기 (운영자 게이트) |
| AC-POOLEMPTY-014 | REQ-015 | 실기 + 오프라인 (예산) |
| AC-POOLEMPTY-015 | REQ-016, REQ-010 | 오프라인 (임포트) |

---

## §D.1 응답기 — 열거 신뢰도

### AC-POOLEMPTY-001 — 성공적으로 빈 풀은 `"ok"` 라고 말한다

- **Given** `server/tests/test_lua_responder.py` 의 `ResponderHarness` 가 실제 `console/lua/copilot_responder.lua` 를 lupa 로 구동하고, 자식이 **0개인 정상 풀 노드**가 목 트리에 있다.
- **When** 그 풀 경로로 `state` 요청을 보낸다.
- **Then** 디코드된 회신이 `ok is True`, `payload["node"]["childCount"] == 0`, `payload["node"]["enumeration"] == "ok"`, `payload["children"] == []`, `payload["truncated"] is False` 를 동시에 만족한다.

### AC-POOLEMPTY-002 — 열거에 실패한 핸들은 `"failed"` 라고 말한다

- **Given** `Children()` 과 `Count()` 가 **둘 다** `error()` 를 던지는 목 노드가 `ResponderHarness(extra_env=...)` 로 주입되어 있다(기존 `__NODE` 는 수정하지 않는다 — `server/tests/lua_mock_env.py:61-62` 의 두 메서드는 실패할 줄 모른다).
- **When** 그 노드 경로로 `state` 요청을 보낸다.
- **Then** 회신이 `payload["node"]["childCount"] == 0` 이고 `payload["node"]["enumeration"] == "failed"` 다. `ok`·`children`·`truncated` 는 오늘 값(`True` / `[]` / `False`)을 유지한다.

### AC-POOLEMPTY-003 — 필드는 두 값만 갖는다

- **Given** 위 두 검사가 통과한 상태.
- **When** `server/tests/test_lua_responder.py` 의 모든 `state` 성공 회신에서 `node["enumeration"]` 을 수집한다.
- **Then** 수집된 값 집합이 `{"ok", "failed"}` 의 부분집합이고, 성공 회신 중 이 필드가 **누락된 것이 0건**이다.

### AC-POOLEMPTY-004 — 나머지 호출 지점은 동작이 바뀌지 않았다

- **Given** M1 이 적용된 트리.
- **When** `grep -n 'safe_children(' console/lua/copilot_responder.lua` 를 실행하고, `server/tests/test_lua_responder.py` 전체를 돌린다.
- **Then** grep 이 **4행**(정의 1 + 호출 3: `find_child` · `build_snapshot` · 플러그인 스캔)을 답하고, `find_child` 계열(슬롯 대 위치 해석, 갭 풀)과 플러그인 스캔 계열의 **기존 검사 전부가 초록**이며 새 실패 0건이다.

### AC-POOLEMPTY-005 — 버전과 문서가 함께 움직였다

- **Given** M1 이 적용된 트리.
- **When** `grep -n 'VERSION = ' console/lua/copilot_responder.lua` 와 `grep -n '1.6.5' console/lua/PROTOCOL.md` 를 실행한다.
- **Then** 전자가 `VERSION = "1.6.5"` 를 답하고, 후자가 (ㄱ) 1.6.5 revision note 와 (ㄴ) §4.2 의 `node` 필드 설명 **둘 다**에서 일치를 답한다. `console/lua/PROTOCOL.md` 의 최상단 `"v": 1` 선언은 **변하지 않았다**.

---

## §D.2 앱 — 판정

### AC-POOLEMPTY-006 — 마커가 `"ok"` 면 빈 풀은 free 다

- **Given** `node.childCount == 0`, `node.enumeration == "ok"`, `children == []`, `truncated == False` 를 답하는 가짜 `StateQueryPort`.
- **When** `from server.orchestrator.tools import timecode_slot_verdict` 로 들어올린 함수(REQ-016)를 `timecode_slot_verdict(port, path, wanted)` 로 호출한다.
- **Then** 반환된 점유자가 `None` 이고 반환된 축이 `timecode_go is True`(기본 축), `timecode_skip_reason is None` 이다.

### AC-POOLEMPTY-007 — 마커가 없으면 오늘과 동일하게 unknown 이다 (하위 호환)

- **Given** `node` 에 `enumeration` 키가 **아예 없는** 페이로드(`{"name":…, "class":…, "childCount":0}`) — 구버전 응답기가 보내는 형태 그대로.
- **When** 들어올린 `timecode_slot_verdict`(REQ-016)를 호출한다.
- **Then** 점유자가 `None` 이고 `timecode_go is False` 이며, `timecode_skip_reason` 이 오늘의 문자열(`"…reported zero children — a failed enumeration and an empty pool are indistinguishable here"` 을 포함)을 그대로 담는다. **사유 문자열이 바뀌지 않았다는 것까지 단언한다.**

### AC-POOLEMPTY-008 — 마커가 `"failed"` 면 unknown 이다

- **Given** `node.childCount == 0`, `node.enumeration == "failed"` 인 페이로드.
- **When** 들어올린 `timecode_slot_verdict`(REQ-016)를 호출한다.
- **Then** `timecode_go is False` 이고 사유가 보고된다.

### AC-POOLEMPTY-009 — 나머지 unknown 갈래는 완화되지 않았다

- **Given** 다섯 형상 각각 — (ㄱ) `query_state` 가 예외를 던짐, (ㄴ) 비-매핑 페이로드, (ㄷ) `truncated: True`, (ㄹ) `childCount` 키 부재, (ㅁ) `childCount 5` 인데 `children` 3개. **다섯 모두 `enumeration: "ok"` 를 실어** 마커가 다른 갈래를 뚫지 못함을 확인한다.
- **When** 각 형상으로 들어올린 `timecode_slot_verdict` 를 호출한다.
- **Then** 다섯 경우 **전부** `timecode_go is False` 이고, 각 사유 문자열이 오늘의 것과 동일하다.

### AC-POOLEMPTY-010 — 프로브 술어가 앱 술어와 갈리지 않았다

- **Given** `server/tools/musicsync_m3a_probe.py` 의 `slot_verdict` 와 `server.orchestrator.tools.timecode_slot_verdict`.
- **When** AC-006 ~ AC-009 의 **같은 입력 형상 전부**를 두 술어에 각각 먹인다.
- **Then** 두 술어의 판정(`free` / `occupied` / `unknown`)이 **모든 입력에서 일치**한다. AC-015 가 「같은 객체」를 단언하므로 이 AC 는 그 위의 **행동 수준 이중 확인**이다 — 프로브가 앱 판정을 `(str, str|None)` 로 번역하는 어댑터 층이 갈리지 않았는지를 본다.

### AC-POOLEMPTY-011 — 버전 핀 두 리터럴이 함께 움직였다

- **Given** M2 가 적용된 트리.
- **When** `pytest server/tests/test_responder_roundtrip.py` 를 실행한다.
- **Then** `:114` 의 크로스파일 대조(`self._lua_version() == EXPECTED_RESPONDER_VERSION`)가 통과하고, `grep -rn 'EXPECTED_RESPONDER_VERSION = ' server/` 가 **정확히 1행**(`server/safety/responder_version.py:35`, 값 `"1.6.5"`)을 답한다.

### AC-POOLEMPTY-012 — 낡은 응답기는 계속 「재임포트 필요」로 막힌다

- **Given** `1.6.4` 를 보고하는 응답기(기대는 `1.6.5`).
- **When** 안전 게이트의 건강 검사를 실행한다.
- **Then** READBACK-002 의 low 갈래로 차단되고 라벨이 「재임포트 필요」이며, 이 SPEC 이 **새 분기를 추가하지 않았음**을 `git diff server/safety/gate.py` 가 빈 diff 로 확인한다.

---

## §D.3 실기 (운영자 게이트)

### AC-POOLEMPTY-013 — 빈 풀이 free 로 읽힌다, 그리고 대조군은 unknown 이다

- **Given** 운영자가 (1) 워크트리의 `console/lua/copilot_responder.lua` 를 `~/MALightingTechnology/gma3_library/datapools/plugins/` 에 **먼저 복사**한 뒤 콘솔 플러그인 슬롯을 지우고 재임포트했고, (2) `python -m server.tools.responder_roundtrip --expect-version 1.6.5` 가 **통과**했으며, (3) `DataPool/Timecodes` 에서 `Timecode 1` 과 `999` 를 삭제해 풀을 비웠다.
- **When** 같은 회차에 세 가지를 쏜다 — ① `DataPool/Timecodes` 의 슬롯 판정, ② `DataPool/Timecodes` 의 **raw `state` 회신**(응답기가 실제로 `node.enumeration` 을 실었는지), ③ **음성 대조군**: 슬롯 판정이 unknown 으로 닫히는 경로.
- **Then** ①이 **free**, ②의 raw 회신에 `"enumeration":"ok"` 와 `"childCount":0` 이 **함께** 찍혀 있고, ③이 **unknown** 이다. ③은 「응답기가 답하지 않은」 경로(존재하지 않는 경로)여도 되지만, 그 경우 노트에 **「③은 판독-예외 갈래이지 `"failed"` 마커 갈래가 아니다」라고 명시**한다 — 실기에서 `Children()` 이 실패하는 살아 있는 핸들을 찾으면 그것을 ③으로 쓰고 raw 회신의 `"enumeration":"failed"` 를 인용한다. 세 결과의 명령줄과 출력을 그대로 인용해 `docs/research/ma3-effects/` 아래 새 회차 노트에 남긴다. **①만 있고 ②·③이 없으면 이 AC 는 미통과다** — ②가 없으면 free 가 마커 때문인지 알 수 없고, ③이 없으면 계기가 살아 있다는 증거가 없다.

### AC-POOLEMPTY-014 — 콘솔 쓰기는 0이다

- **Given** M1~M3 전 구간.
- **When** 실기 회차를 `server/tools/musicsync_m3a_probe.py` 의 판정 단계로 돌리고 그 출력의 「합계 {n} / 상한 {MAX_WRITES}」 줄(`:578`)을 읽는다. 오프라인으로는 `git diff main...HEAD -- server/ console/ | grep -c 'execution_port.execute\|run_commands('` 를 센다.
- **Then** 「합계 0 / 상한 8」이고, 위 grep 이 **0** 이다(이 SPEC 이 발화 지점을 하나도 더하지 않았다). 유일한 콘솔 변경은 운영자의 플러그인 재임포트이며, 그것은 앱의 발화가 아니다.

### AC-POOLEMPTY-015 — 술어는 하나다 (들어올리기)

- **Given** M2 가 적용된 트리.
- **When** `python -c "from server.orchestrator.tools import timecode_slot_verdict; import server.tools.musicsync_m3a_probe as p; print(p.timecode_slot_verdict is timecode_slot_verdict)"` 를 실행하고, `grep -n 'def _timecode_slot_verdict' server/orchestrator/tools.py` 와 `grep -n 'def slot_verdict' -A3 server/tools/musicsync_m3a_probe.py` 를 본다.
- **Then** 첫 명령이 `True` 를 찍고, 중첩 정의 grep 이 **0행**이며, 프로브의 `slot_verdict` 본문이 들어올린 함수를 **호출만** 한다(자체 분기 없음). `test_songcue_tool.py` 의 `prepare_songcue` 계열 검사(`:388-405` 부근)가 옮기기 전과 같은 결과로 초록이다.

---

## §D.4 완료의 정의 (Definition of Done)

- AC-POOLEMPTY-001..012 전부 통과 (오프라인).
- AC-POOLEMPTY-013..014 통과 (실기, 운영자 게이트).
- `pytest server/tests/` 초록, 새 회귀 0건.
- 실기 회차 노트가 `docs/research/ma3-effects/` 에 존재하고, free 와 대조군 unknown 두 결과를 **명령줄과 함께** 인용한다.
- `progress.md` §E.2/§E.3 에 실행 증거가 채워져 있다.
