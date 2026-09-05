# SPEC-COPILOT-POOLEMPTY-001 — 실행 계획

> 대상 SPEC: `.moai/specs/SPEC-COPILOT-POOLEMPTY-001/spec.md` · Tier M · 기준 트리 `main` `f727e11` (2026-09-06)

---

## §A 맥락 — 실측으로 확인한 앵커

아래 행번호는 **2026-09-06 `f727e11` 에서 직접 열어 확인**했다. 인용은 각 파일을 이 트리에서 읽은 결과다.

| 자리 | 앵커 | 무엇 |
|---|---|---|
| 응답기 정의 | `console/lua/copilot_responder.lua:625-653` | `M.safe_children`. 세 갈래: `Children()` 성공 `:627-638` · `Count()`+`Ptr()` 성공 `:639-651` · **둘 다 실패 → `return {}` `:652`** |
| 응답기 버전 | `console/lua/copilot_responder.lua:98` | `VERSION = "1.6.4"` |
| 스냅샷 빌더 | `console/lua/copilot_responder.lua:822`(정의) · `:846-885`(페이로드 조립) | `local children = M.safe_children(handle)` → `total = #children` → `ok = true`, `node.childCount = total`, `children`, `truncated = last < total` |
| 호출 지점 | `grep -n 'safe_children(' console/lua/copilot_responder.lua` → **4행** | 정의 `:625` + 호출 **3곳**: `:690`(`find_child`) · `:846`(`build_snapshot`) · `:1219`(`set_plugin_source`, 정의 `:1217`) |
| 앱 판정 | `server/orchestrator/tools.py:2814` | `def _timecode_slot_verdict(port, path, wanted)` — 툴셋 빌더 안의 **중첩 함수** |
| 앱 판정 · 문제 갈래 | `server/orchestrator/tools.py:2876-2880` | `if child_count == 0: return _suppressed("… a failed enumeration and an empty pool are indistinguishable here")` |
| 앱 판정 · 유일 호출자 | `server/orchestrator/tools.py:2709` | `occupied, axes = _timecode_slot_verdict(...)` |
| 프로브 재구현 | `server/tools/musicsync_m3a_probe.py:140` | `def slot_verdict(port, path, wanted) -> tuple[str, str|None]` |
| 버전 핀 | `server/safety/responder_version.py:35` | `EXPECTED_RESPONDER_VERSION = "1.6.4"` |
| 크로스파일 검사 | `server/tests/test_responder_roundtrip.py:114` | `assert self._lua_version() == EXPECTED_RESPONDER_VERSION` |
| 게이트 low 갈래 | `server/safety/gate.py:435-439`(분기 머리 `:435`, 문구 `:439`) | 「재임포트 필요」 차단 (READBACK-002) |
| lupa 하네스 | `server/tests/test_lua_responder.py` (1,497행) · `server/tests/lua_mock_env.py:49-62` | `ResponderHarness(extra_env=...)` 가 실제 `.lua` 를 Lua 5.4 로 구동. `__NODE` 의 `Children()`/`Count()` 는 **절대 실패하지 않는다** |
| 프로브 특성검사 | `server/tests/test_musicsync_m3a_probe.py:282-316` | `TestSlotVerdictCharacterisation` — free / occupied / unknown 형상 / 판독 실패 |
| 실기 근거 1회차 | `docs/research/ma3-effects/14-musicsync-m3a-timecode-probe.md:9,13,20,61-64` | verdict **unknown**, 쓰기 0, 무결론 |
| 실기 근거 2회차 | `docs/research/ma3-effects/14-musicsync-m3a-timecode-probe-run2.md` | 운영자가 `Timecode 1` 을 손으로 만든 뒤에야 진행 |
| PROTOCOL 배너 | `console/lua/PROTOCOL.md:19-73` | 「Revision note (responder 1.6.x)」 블록 계열 (`:9-18` 은 Reland note — 여기 아님) |
| PROTOCOL §4.2 | `console/lua/PROTOCOL.md:193-240` | `node` 예시(`{"name":"Sequences","class":"Pool","childCount":12}`) + `truncated`/`childCount` 규약 |

---

## §B 알려진 함정

### B-1 배차서와 저장소의 행번호 앵커가 **둘 다 만료됐다**

- 배차서는 `_timecode_slot_verdict` 를 `server/orchestrator/tools.py:2801` 로 지목한다.
- 저장소 안의 `:2792` 인용은 **4건**이다 — `server/tools/musicsync_m3a_probe.py:32`(모듈 독스트링)·`:143`(`slot_verdict` 독스트링), `server/tests/test_musicsync_m3a_probe.py:19`(모듈 독스트링)·`:283`(특성검사 독스트링). `grep -n '2792' server/tools/musicsync_m3a_probe.py server/tests/test_musicsync_m3a_probe.py` 가 그 4행을 답한다.
- **2026-09-06 `f727e11` 실측: `def _timecode_slot_verdict` 는 `:2814`.** 세 숫자가 모두 다르다.

→ **처방**: 이 SPEC 이 그 함수를 건드리는 김에, 4건 전부를 **행번호 없는 인용**(`server/orchestrator/tools.py` `timecode_slot_verdict`)으로 바꾼다 — REQ-016 으로 함수가 모듈 수준으로 옮겨져 행번호 자체가 바뀌고, 이름으로 인용하면 만료되지 않는다. 행번호 인용을 **더 늘리지는 않는다**. M2 게이트에서 위 grep 이 **0행**이어야 한다.

### B-2 재임포트 함정 (M3 의 유일한 실패 형태)

머지된 코드는 **로드된 플러그인이 아니다.** 워크트리의 `console/lua/copilot_responder.lua` 를 `~/MALightingTechnology/gma3_library/datapools/plugins/` 로 **먼저 복사**하고, **그 다음** 콘솔에서 플러그인 슬롯을 지우고 재임포트한다. 순서를 뒤집으면 콘솔이 **낡은 파일을 다시 읽는다.**

유일한 심판은 `server/tools/responder_roundtrip.py --expect-version 1.6.5` 다(`:140-160`, `--expect-version` 은 ping 단계에서 라이브 버전과 대조해 「the deploy did not take effect -- re-import」로 실패시킨다). 「복사했다」·「재임포트했다」는 배치의 증거가 아니다.

### B-3 프로브가 앱 판정을 **재구현**한다 (술어 이중화)

`slot_verdict`(`server/tools/musicsync_m3a_probe.py:140`)는 `_timecode_slot_verdict` 의 복제본이다. 이유는 원본이 **툴셋 빌더 안의 중첩 함수**라 임포트할 수 없기 때문이다(`server/tests/test_musicsync_m3a_probe.py:19-20` 이 그렇게 적고 있다).

두 선택지:
- **(가) 그대로 미러링** — 두 자리를 같은 커밋에서 함께 고치고, 프로브 특성검사에 새 케이스를 더한다.
- **(나) 술어를 밖으로 들어올린다** — `_timecode_slot_verdict` 의 순수 판정부를 모듈 수준 함수로 빼고 양쪽이 임포트한다.

**결정(plan 단계, 2026-09-06 `f727e11` 코드 판독): (나) 채택 — REQ-016.** 클로저가 바깥에서 잡는 이름을 셌다: `_suppressed`(`:2849`, 자기 안의 중첩 함수, `SongCueTimingAxes` 만 쓴다)와 모듈 임포트 `SongCueTimingAxes`(`:75`) 둘뿐이다. 툴셋 빌더의 다른 로컬(`_suppressed` 밖)은 본문 `:2814-2885` 어디에서도 참조되지 않는다. 따라서 함수 본문을 그대로 모듈 수준으로 옮기고 `_suppressed` 를 함께 데려가면 동작이 바뀌지 않는다. 유일 호출자 `:2709` 는 이름만 바꾼다. 이 판단이 M2 착수 시 코드와 어긋나면(새 캡처가 생겼다면) **(가)로 후퇴하고 그 근거를 `progress.md` §E.2 에 남긴다** — 후퇴는 REQ-016 미이행이므로 SPEC 개정(HISTORY 행)이 따른다.

### B-4 `__NODE` 목 노드는 실패할 줄 모른다

`server/tests/lua_mock_env.py:61-62` 의 `Children()`/`Count()` 는 항상 성공한다. `enumeration: "failed"` 케이스를 만들려면 **둘 다 `error()` 를 던지는 새 목 노드**를 `ResponderHarness(extra_env=...)` 로 주입해야 한다. 기존 `__NODE` 를 고치면 1,497행짜리 스위트 전체에 파급되므로 **건드리지 않고 새 빌더를 더한다.**

### B-5 UDP 예산

`node` 에 필드가 하나 늘면 `CONFIG.max_payload` 안에서 children 창이 그만큼 좁아진다. 페이징 회귀 검사(`truncated`/`offset` 계열)가 기존대로 통과하는지 확인한다.

### B-6 `_free_macro_slot` 은 이 SPEC 이 고치지 않는다

`server/orchestrator/tools.py:2932-2946` 에 **바이트 수준으로 같은 함정**이 있다(주석까지 같은 논지). spec.md §4 가 명시적으로 out of scope 로 두었다. M2 에서 「김에 같이」 고치고 싶어지는 자리이므로 미리 못 박는다 — 범위를 넓히려면 먼저 한 줄 보고한다.

---

## §C 결정 — 갈래 (a) 를 택한다

> **가장 바뀌기 쉬운 결정을 먼저 둔다**: C-1(페이로드 필드 이름·형상)은 프로토콜 표면이라 한 번 배포되면 되돌리기가 비싸다. C-4(테스트 배치)는 언제든 바꿀 수 있다.

### C-1 페이로드 필드 (가장 되돌리기 어려움 — 먼저 검토)

**제안**: `node.enumeration`, 값은 `"ok" | "failed"` 문자열.

| 후보 | 장점 | 단점 | 판정 |
|---|---|---|---|
| `node.enumeration: "ok"\|"failed"` | 확장 가능(뒤에 `"partial"` 이 필요해지면 값만 늘린다), `node` 안에 있어 `childCount` 와 같이 읽힌다 | 불리언보다 몇 바이트 김 | **채택** |
| `node.enumOk: true\|false` | 가장 짧음 | 「없음/false/true」 3상태를 앱이 매번 풀어야 하고, 뒤에 3번째 상태가 필요해지면 형상이 깨진다 | 기각 |
| 최상위 `enumeration` | `node` 를 안 건드림 | `childCount` 와 떨어져 있어 소비 지점에서 두 번 꺼내야 함 | 기각 |

**하위 호환의 방향이 이 선택의 핵심이다**: 필드 **부재**가 곧 「모름」이고, 앱은 모름을 unknown 으로 읽는다. 구버전 응답기에 대해 새 앱이 더 관대해지는 경로는 구조적으로 존재하지 않는다.

### C-2 `M.safe_children` 반환 형태

**제안**: `return out, "ok"` / `return {}, "failed"` — 두 번째 반환값. 호출 지점 3곳 중 2곳(`:690`, `:1219`)은 두 번째 값을 **받지 않으므로 Lua 에서 무해하게 무시**된다. `:846` 만 받아서 payload 에 싣는다. 필드를 배열 테이블에 얹는 방식(`out.enumeration = ...`)은 `#out` 을 쓰는 자리들과 섞일 소지가 있어 기각한다.

### C-3 왜 (b)·(c) 가 아닌가

| 갈래 | 내용 | 기각 사유 |
|---|---|---|
| **(a) 마커 도입** ← 채택 | 응답기가 열거 성공 여부를 싣고, 앱은 그것을 신뢰할 때만 완화 | — |
| (b) 마커 없이 판정 완화 | `childCount 0` 을 그냥 free 로 | **죽은 풀이 free 로 읽혀 남의 쇼를 덮는다.** `_free_macro_slot` 주석이 같은 대가를 이미 적어 두었다 |
| (c) 운영 절차로 대체 | 운영자가 매번 `Timecode 1` 을 손으로 만든다 | 그것이 **현재의 우회이지 수정이 아니다**(2회차가 실제로 그렇게 진행됐다). 새 쇼마다 반복되고, 앱은 여전히 자기 기능을 못 쓴다 |

### C-4 프로브 술어 (B-3 참조)

plan 단계에서 (나) 들어올리기로 **결정됐다**(B-3, REQ-016). M2 는 결정을 실행하고, 코드가 판독과 어긋날 때만 후퇴한다.

---

## §D 제약

- **범위**: `console/lua/copilot_responder.lua`, `console/lua/PROTOCOL.md`, `server/orchestrator/tools.py`(`_timecode_slot_verdict` 갈래 **하나**), `server/tools/musicsync_m3a_probe.py`, `server/safety/responder_version.py`, 관련 검사 파일. 그 밖은 손대지 않는다.
- **와이어 프로토콜 버전은 `"v": 1` 유지.** 가산적 변경이다.
- **`console/lua/PROTOCOL.md` §6 에 새 `ASSUMPTION-<n>` 을 추가하지 않는다.** (2026-09-06 실측: 해당 문서 §6 계열 최고값 `ASSUMPTION-52`. 부득이 필요하면 `53` 부터.)
- **버전 두 리터럴은 한 커밋에서 함께 움직인다** — `console/lua/copilot_responder.lua:98` 과 `server/safety/responder_version.py:35`.
- **콘솔 예산: 읽기 전용.** 이 SPEC 이 발화하는 쓰기 명령은 0. M3 의 플러그인 재임포트는 **운영자의 행위**다.
- **M3 은 운영자 게이트.** 운영자가 (1) 재임포트, (2) `Timecode 1`·`999` 삭제로 `DataPool/Timecodes` 를 비우기 를 마친 뒤에만 실행한다.

---

## §E 마일스톤

### M1 — 응답기가 자기 열거를 말하게 한다 (오프라인, 우선순위 High)

1. `M.safe_children`(`:625-653`)이 두 번째 반환값으로 `"ok"`/`"failed"` 를 답하게 한다(§C-2).
2. `M.build_snapshot`(`:846`)이 그 값을 `node.enumeration` 으로 싣는다(§C-1).
3. `VERSION`(`:98`) `1.6.4` → `1.6.5`.
4. `console/lua/PROTOCOL.md`: 1.6.5 revision note(배너 `:19-73` 계열) + §4.2 `node` 예시·규약에 필드 추가.
5. `server/tests/test_lua_responder.py`: 두 케이스 추가 — (ㄱ) 성공적으로 빈 풀 → `enumeration:"ok"` + `childCount 0`, (ㄴ) `Children()`·`Count()` 가 **둘 다** `error()` 를 던지는 목 노드 → `enumeration:"failed"` + `childCount 0`. (ㄴ)용 목 노드는 `extra_env` 로 주입(B-4).
6. 회귀: `grep -n 'safe_children(' console/lua/copilot_responder.lua` 가 여전히 4행이고 `:690`·`:1219` 동작이 불변임을 검사로 확인.

**게이트**: `pytest server/tests/test_lua_responder.py` 초록.

### M2 — 앱이 마커를 믿는다 (오프라인, 우선순위 High)

1. REQ-016: `_timecode_slot_verdict`(`:2814-2885`)를 `_suppressed` 와 함께 모듈 수준 `timecode_slot_verdict` 로 옮기고, 호출자 `:2709` 를 새 이름으로. 옮기기 **전에** 기존 `test_songcue_tool.py:388-405` 계열이 초록임을 확인하고, 옮긴 **뒤** 같은 검사가 그대로 초록인지 본다(동작 불변의 증거).
2. `timecode_slot_verdict` 의 `childCount == 0` 갈래: `node.enumeration == "ok"` 일 때만 통과시키고, 그 외에는 **현행 사유 문자열 그대로** unknown.
3. `slot_verdict`(`server/tools/musicsync_m3a_probe.py:140`)를 재구현에서 **임포트**로 바꾼다(REQ-010). `:2792` 인용 4건을 이름 인용으로(B-1); `grep -n '2792'` 두 파일 → 0행.
4. `EXPECTED_RESPONDER_VERSION`(`server/safety/responder_version.py:35`) → `"1.6.5"`.
5. 검사 추가: 앱 쪽 free / 마커 부재 unknown / `"failed"` unknown / 나머지 unknown 갈래 불변; 프로브 특성검사(`test_musicsync_m3a_probe.py:282-316`) 확장.
6. 회귀: `test_responder_roundtrip.py:114` 크로스파일 대조가 초록인지(두 리터럴이 함께 움직였는지) 확인.

**게이트**: `pytest server/tests/` 초록, 새 회귀 0.

### M3 — 실기 (운영자 게이트, 우선순위 Medium)

1. **운영자**: 워크트리의 `console/lua/copilot_responder.lua` 를 `~/MALightingTechnology/gma3_library/datapools/plugins/` 에 **먼저 복사** → 콘솔 플러그인 슬롯 삭제 → 재임포트(B-2).
2. `python -m server.tools.responder_roundtrip --expect-version 1.6.5` — **유일한 배치 심판**. 실패면 여기서 멈춘다.
3. **운영자**: `DataPool/Timecodes` 를 비운다(`Timecode 1`, `999` 삭제).
4. 빈 풀 슬롯 판정 → **free** 를 기대. 콘솔 쓰기 0.
5. **음성 대조군**: 열거할 수 없는 경로에 같은 판정을 쏘아 **unknown** 을 확인. 대조군 없는 free 는 증거가 아니다.
6. 결과를 `docs/research/ma3-effects/` 아래 새 회차 노트로 남기고, 명령줄과 출력을 그대로 인용한다.

**게이트**: AC-POOLEMPTY-013 통과 + 콘솔 쓰기 0건.

---

## §F 위험

| 위험 | 형태 | 완화 |
|---|---|---|
| 낡은 응답기가 실기에 살아 있음 | free 가 안 나오고 게이트가 「재임포트 필요」로 막음 | 그것이 **설계된 동작**(REQ-012). `--expect-version` 이 먼저 잡는다 |
| UDP 예산으로 children 창 축소 | 페이징 회귀 | M1 게이트에서 기존 페이징 검사 전수 통과 확인 |
| 술어 이중화가 갈림 | 프로브 판정이 앱 판정의 증거가 아니게 됨 | §C-4 · 두 자리를 같은 커밋에서 |
| 범위 확대 유혹(`_free_macro_slot`) | 리뷰 반경 증가 | spec.md §4 out of scope · B-6 |
