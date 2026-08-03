# SPEC-COPILOT-INTROSPECT-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 타 SPEC 아티팩트**에만 쓰고, **각 마일스톤 착수 직전 재실측**한다. 근거 등급 `[코드]` · `[문서]` · `[실측]` · `[인수]` · `[미확정]` — **`[실측]`은 본 세션의 라이브 콘솔 직접 관측만**이며, 코디네이터로부터 받은 관측은 `[인수]`다.

## §0 인수인계 — 여기서 시작한다 (2026-08-03 작성, plan-phase)

### 한 문단

**무엇**: 핸들 자기진단 동사 2종 — `introspect`(핸들이 노출하는 **필드 이름 + 타입** 열거)와 `props`(**명시한 이름 일괄 판독**). 이 SPEC은 **기능이 아니라 발견 도구**를 만든다. 재생 상태·진행률은 구현하지 않으며, 그것이 *존재하는지*를 추측이 아니라 증거로 판정할 수단을 만든다.

**상태**: **run-phase M1 완료 (GO, 2026-08-03).** 구현 코드 변경 0 · 커밋 0 · 라이브 프로브 1회. base `origin/main` = `3176900`. REQ **26** · AC **30** · Out of Scope **9항** · ASSUMPTION **46~49 TRUE**, **50~52 미해소** · 결정 **D-1~D-7**.

**이 SPEC의 한 줄**: *"후보를 소진했다"는 "그 정보가 없다"를 함의하지 않는다* — 코디네이터가 Executor 핸들에 22종을 찍고 실패한 뒤 Sequence 핸들에서 `CurrentCue`를 찾은 사건이, 그 비약을 구조적으로 불가능하게 만들 도구를 요구했다.

### 읽는 순서

1. **`spec.md` §A.1(실측 3건) · §A.3(동사 2개 분리 이유) · §A.4(M1 게이트)** — 이 셋이 설계 전체를 규정한다. §A.3을 건너뛰면 왜 동사가 둘인지 이해할 수 없고, `Executor 80` 경로에서 파싱이 왜 깨지는지 재발견하게 된다.
2. `spec.md` §C.2(검증 천장) → §C.3(ASSUMPTION-46~52) → §D(제외 8항 — 특히 "재생 상태 기능"과 "LLM 툴 추가")
3. **`design.md` §3(회신 형상) · §4(예산 산술) · §5(M1 프로브 사다리)** — §5.4(정합성 게이트)가 이 SPEC의 중심 방어선이다. §8(알려진 천장)을 건너뛰지 말 것.
4. `plan.md` §A.1(리뷰 순서) → §A.3(M1 두 분기) → §B(M1~M7) → §F(**열린 질문 2건 — run 진입 전 해소**)
5. `acceptance.md` §C(AC 30건 — 뮤테이션 필수 4건: 004·010·014·018) → §F(DoD, 특히 항목 4의 협상 불가 목록)
6. `research.md` §1(인수 실측) · §2(저장소가 남긴 오판 흔적) · §7(**룰북에 열거 API 문서 전건 0** — M1이 라이브인 이유)

### 함정 (다음 소유자가 알아야 할 것)

1. **`introspect`는 M1 판정에 걸려 있다. `props`는 걸려 있지 않다.** M1이 NEGATIVE여도 `props`만으로 22회 → 1~2회다. NEGATIVE를 SPEC 실패로 읽지 말 것 — DoD 항목 3이 그 분기를 명시적으로 인정한다.
2. **판독 성공은 세 가지를 뜻할 수 있다.** 진짜 프로퍼티 / 메서드 포인터(`Index` → `'function: 0x...'`) / 무관한 이름(`Fader` → `'Master'`). `ok=true`를 "그 프로퍼티가 실재하고 유의미하다"로 읽으면 이 SPEC의 전제가 무너진다.
3. **미지 이름에 대한 콘솔의 `ok`는 비변별적일 수 있다.** SCENE-001 M0 실측: 존재하지 않는 `/CueOnlyy`가 `ok`를 받고 저장까지 됐다. 콘솔의 긍정 응답이 "이해했다"를 뜻하지 않는 사례가 이미 있다.
4. **열거원은 전량 채택 또는 전량 폐기다.** 부분 채택은 `M.probe_slots`가 이미 봉인한 결함 유형(*"반쯤 믿는 numbering이 그럴듯한 오답이 새어 나가는 경로"*)이며, 여기서 재생산하면 이 SPEC이 없애려는 것을 새 표면에 만든다.
5. **절단 신호는 두 종류다.** 값 축약(항목별)과 항목 탈락(목록 전체)은 **다른 사건**이며 신호를 공유하면 안 된다. 이 프로젝트에는 "8룩 중 1개가 조용히 사라진" 선례가 있다.
6. **예산 초과는 런타임 신호가 0이다.** `cmd_keyword` 전송에서 `Cmd()`가 성공을 보고하고 회신은 사라진다. **테스트가 유일한 그물이며**, 절단 테스트의 재료는 반드시 상한을 넘겨야 한다 — 오늘의 실제 핸들이 상한 미만이면 절단 코드를 제거해도 테스트가 통과한다.
7. **`introspect`의 절단분은 회수할 수 없다.** `state`는 슬롯별 조회라는 우회로가 있지만, 이름을 모르면 `props`로 물을 수 없다. `total`이 누락 사실을 드러낼 뿐이다(design.md §8-1). 이것을 "페이징으로 해결하자"로 넘어가기 전에 M7 실측을 볼 것 — **예측으로 미리 만들지 않는다.**
8. **감사에 값이 들어가면 안 된다.** 감사 주체는 `경로 + 요청 이름들`이며, 이 한 줄이 민감정보 경계의 실제 집행 지점이다. AC-INTROSPECT-018이 감시 문자열 부재로 기계 검증한다.
9. **M1은 GO로 닫혔다.** 따라서 REQ-INTROSPECT-001~005 `[DEFERRED]` 재표기와 manager-spec 재위임은 필요 없다.
10. **M1 매크로 폴백은 사용하지 않았다.** ASSUMPTION-48은 TRUE로 닫혔고, 증거 채널은 OSC 직접 회신만 사용했다. 매크로/라벨/씬 증거 쓰기는 0건이다.
11. **`prop`과 `props`는 한 글자 차이다.** 디스패치는 정확 일치라 기계적 위험은 없지만, 사람이 읽을 때 놓친다. AC-INTROSPECT-022가 교차 오배정을 봉쇄한다.

### 다음 소유자의 착수 키트

- **다음 단계**: **M2(응답기 확장)**. M1이 GO이므로 `props`와 `introspect` 둘 다 범위에 남고, M2의 `introspect` 구현 열거원은 `property_accessors` 하나다.
- **남은 run-phase 미해소**: `props` 이름 목록 상한값(ASSUMPTION-50)과 M3/M6/M7 배정 전제(ASSUMPTION-51~52). M1 프로브의 쇼파일 증거 폴백 여부는 "불허 + 불필요"로 닫혔다.
- **기준선 재측정 의무**: run-phase 킥오프 시점에 pytest/vitest 기준선을 **다시 측정한다.** plan-phase 수치 재사용 금지.

---

## §E.1 Plan-phase Audit-Ready Signal

- **산출물**: `spec.md` · `plan.md` · `acceptance.md` · `design.md` · `research.md` · `progress.md` (6종)
- **Tier 판정**: **L** — 콘솔 Lua + 와이어 프로토콜 + Python 트윈 + 포트/게이트/링크 3계층 + 테스트, 예상 변경 8~12파일. 라이브 콘솔 의존 마일스톤 2건(M1·M6) + 산출물 1건(M7). 분기 게이트 1건(M1 GO/NEGATIVE). 배포 루프(재패키징 + Import) 필요. 선례 SPEC-COPILOT-EXECBODY-001(동일 형상: 응답기 확장 + 라이브 프로브 + 배포 루프)이 Tier L.
- **base**: `origin/main` = `3176900`. 인용한 4개 파일이 base와 바이트 동일함을 확인(`git diff --quiet`).
- **SPEC ID 자기검사**: `decomposition: SPEC ✓ | COPILOT ✓ | INTROSPECT ✓ | 001 ✓ → PASS` (정규식 `^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$` 실행 결과 `PASS`)
- **구현 범위**: 코드 변경 **0건** · 커밋 **0건** · 라이브 접근 **0건** (plan-phase 계약대로 문서만)
- **열린 질문**: **2건** (plan.md §F — run 진입 전 해소 필요)
- **미해소 ASSUMPTION**: 46~52 (7건, 전부 M1/M3/M6/M7에 확정 마일스톤 배정됨)

## §E.2 Run-phase Evidence

**2026-08-03 — M1 라이브 열거 가능성 프로브 완료 (GO)**

- **판정**: GO. M2는 `props`와 `introspect` 둘 다 진행한다.
- **채택 열거원**: `property_accessors` (`PropertyCount()` + `PropertyName(i)` + `PropertyType(i)`). `dump_return`도 문자열 토큰 스캔으로 게이트를 통과했지만, 문자열 파싱 기반이라 M2 구현 입력으로 채택하지 않는다.
- **증거**: raw OSC 로그 `.moai/state/verify/introspect-m1-20260803T091729.log` (304 JSONL lines, 173 KB), 최종 Lua 소스 `.moai/state/verify/introspect_m1_20260803T092930.lua`, XML wrapper `.moai/state/verify/introspect_m1_20260803T092930.xml`.
- **대상**: `Executor 201` 정지 + `Go+ Executor 201` 재생 중, `DataPool/Sequences/80`, `DataPool/Groups/1`.
- **대조군**: `Executor 201 Index` = `function: 0x...`, `Executor 201 Fader` = `Master`, `DataPool/Sequences/80 CurrentCue` = `Sequence 80.3`. Canonical uppercase alias도 같은 세션에서 확인: `INDEX` = `201`, `FADER` = `Master`, `CURRENTCUE` = `Sequence 80.3`.
- **사다리 결과**: `metatable_index`는 `__index`가 function이라 폐기. `pairs_handle`은 iterator 오류로 폐기. `property_accessors`는 Executor 71건, Sequence 65건, Group 101건을 열거했고 대조 이름 전부 포함. `get_integer`는 이름 0건. `dump_return`은 문자열 반환과 대조 이름 포함을 확인했지만 파싱 의존으로 구현 비채택.
- **ASSUMPTION 판정**: 46 TRUE, 47 TRUE, 48 TRUE, 49 TRUE.
- **부작용 확인**: 정지 `Executor 201`의 전후 `state` 형상이 동일했다(`children=[]`, `node.childCount=0`, `class=Executor`, `name="Ballad Yellow Red"`, `sequenceNo=20`, `truncated=false`). 재생 프로브 뒤 `Off Executor 201` 원복 완료.
- **콘솔 잔여**: slot 지정 `Import Plugin <slot> '<slug>'`만 성공했다. 본 세션의 일회용 프로브 플러그인 슬롯이 남았다(`introspect-m1-20260803T091729`, `introspect_m1_20260803T091729`, `CopilotIntrospectProbe091729`, `CopilotIntrospectProbe092425`, `CopilotIntrospectProbe092745`, `CopilotIntrospectProbe092930`). 매크로/라벨/씬 증거 쓰기는 0건이다.

**2026-08-03 — M2 응답기 확장 완료 (props 무조건 + introspect, M1 GO 입력)**

- **범위**: `console/lua/copilot_responder.lua`를 v1.6.0으로 올리고 `props`/`introspect` 분기를 상태 회신 주소(`/copilot/state`)에 가산 추가했다. `M.PROTO`는 1을 유지했다. 수정 파일은 `console/lua/copilot_responder.lua`, `server/tests/test_lua_responder.py`, `server/tests/lua_mock_env.py`, `.moai/specs/SPEC-COPILOT-INTROSPECT-001/progress.md`다.
- **최종 `introspect` 회신 스키마**: 성공은 `{"v":1,"kind":"introspect","id":"<id>","ok":true,"path":"<path>","class":"<class>","source":"property_accessors","fields":[{"n":"<name>","t":"<type>"}],"total":<observed_count>,"truncated":<bool>}`다. 실패는 `{"v":1,"kind":"introspect","id":"<id>","ok":false,"path":"<path>","error":"<message>"}`다. `fields[]`는 이름과 타입만 담고 값은 담지 않는다.
- **최종 `props` 회신 스키마**: 처리 성공은 `{"v":1,"kind":"props","id":"<id>","ok":true,"path":"<path>","reads":[...],"truncated":<bool>}`다. 성공 항목은 `{"n":"<name>","ok":true,"t":"<type>","v":"<value>","truncated":true?}`, 실패 항목은 `{"n":"<name>","ok":false,"e":"<message>"}`다. 요청/경로 실패는 `{"v":1,"kind":"props","id":"<id>","ok":false,"path":"<path>","reads":[],"truncated":false,"error":"<message>"}`다. 최상위 `ok`는 "요청 처리됨"만 의미하며, 모든 이름이 판독됐다는 뜻이 아니다.
- **CONFIG 상한**: 이름 개수 상한은 `CONFIG.max_props_names = 16`이다. 값 항목 축약 상한은 `CONFIG.max_prop_value = 240` raw bytes이며, 축약된 항목은 `reads[].truncated = true`를 갖는다.
- **채택 열거원**: 구현 열거원은 `property_accessors` 하나뿐이다. `PropertyCount()` + `PropertyName(i)` + `PropertyType(i)`만 호출하며, M1 사다리의 `__index` 순회, `pairs`, `Get(i)` 정수색인, `Dump()` 반환 문자열 파싱은 구현하지 않았다.
- **@MX 배치**: M1 채택 근거 `@MX:NOTE`/`@MX:SPEC`는 `console/lua/copilot_responder.lua:67`에 있다. 함수 타입 미호출 `@MX:WARN`/`@MX:REASON`은 `console/lua/copilot_responder.lua:246`에 있다. `props` 절단 신호 `@MX:ANCHOR`/`@MX:REASON`은 `console/lua/copilot_responder.lua:758`에 있고, 열거원 전량 채택/전량 폐기 게이트 `@MX:ANCHOR`/`@MX:REASON`은 `console/lua/copilot_responder.lua:766`에 있으며, `introspect` 절단 신호 `@MX:ANCHOR`/`@MX:REASON`은 `console/lua/copilot_responder.lua:827`에 있다.
- **테스트**: `server/tests/lua_mock_env.py`에 `PropertyCount`/`PropertyName`/`PropertyType`와 `Get` 모의 표면을 추가했다. `server/tests/test_lua_responder.py`에는 신규 M2 테스트 15건을 추가했다. 검증 결과는 `uv run pytest server/tests/test_lua_responder.py -q` → `74 passed`, `uv run pytest server/tests/test_lua_responder_payload_budget.py -q` → `2 passed`, 최종 묶음 `uv run pytest server/tests/test_lua_responder.py server/tests/test_lua_responder_payload_budget.py -q` → `76 passed`다. 기존 responder 테스트 59건은 무회귀로 통과했다.
- **절단 뮤테이션 확인**: `props` 절단 신호 줄을 `payload.truncated = false`로 바꾼 뒤 `TestPropsRead::test_props_payload_size_guard_drops_reads_and_signals_truncation`이 `assert False is True`로 실패함을 확인하고 복구했다. `introspect` 절단 신호 줄도 같은 방식으로 바꾼 뒤 `TestIntrospect::test_introspect_payload_truncation_preserves_total`이 `assert False is True`로 실패함을 확인하고 복구했다. 두 절단 재료는 기본 1900B 상한을 넘기는 mock 데이터로 합성했다.
- **남은 위험**: 라이브 콘솔 배포와 왕복 검증은 M6 범위라 수행하지 않았다. `console/lua/PROTOCOL.md`와 `server/bridge/protocol.py` 동기화는 M3 범위라 건드리지 않았다. 로컬 LSP 서버(`lua-ls`, `basedpyright`)는 설치되어 있지 않아 후크가 진단을 건너뛰었고, 본 M2 검증은 lupa 하네스와 focused pytest로 수행했다.

**2026-08-03 — M3 와이어 문서 + Python 트윈 완료**

- **문서 동기화**: `console/lua/PROTOCOL.md` 상단에 responder 1.6.0 Revision note를 추가했고, §2 요청 표에 `props`/`introspect`를 가산했다. `prop` 행은 `<PropertyName>`이 마지막 토큰이고 path가 그 앞 전부임을, 바로 다음 `props` 행은 `<PropertyName,...>` 목록이 첫 rest 토큰이고 path가 나머지 줄임을 표 안에서 대조해 D-3 혼선을 막았다. §4.7 `introspect`, §4.8 `props`, §6 ASSUMPTION-46~52도 추가했다.
- **회신 형상 기록**: §4.7은 `source="property_accessors"`, `fields[].n/t`, `total`(축소 이전 관측 총계), `truncated`(목록 축소), 실패 `error`를 설명한다. 구현이 이미 success payload에 싣는 `class`도 문서화했다. §4.8은 `reads[]` 성공/실패 항목, 항목별 값 축약 `reads[].truncated`, 목록 축소 top-level `truncated`, 그리고 top-level `ok:true`가 "모든 이름 판독 성공"이 아님을 명시했다.
- **Python 트윈**: `server/bridge/protocol.py`에 `MAX_PROPS_NAMES = 16`, `MAX_PLUGIN_CALL_BYTES = 2048`, `build_introspect_query(request_id, path)`, `build_props_query(request_id, path, property_names)`를 추가했다. 두 빌더는 `_validate_request_id`와 `_validate_rest`를 재사용하고 `build_plugin_call`로 래핑한다. `props` 빌더는 빈 목록, 17개 이상, 공백 포함 이름, 콤마 포함 이름, 큰따옴표/개행, UTF-8 인코딩 후 2048B 초과를 `ProtocolError`로 거부한다.
- **2048 산술 고정**: `server/tests/test_lua_responder_payload_budget.py::test_max_props_request_fits_the_ma3_command_line_limit`는 16개 이름 × 32B canonical ASCII property-name 가정, 32B request id, `DataPool/Sequences/Sequence 999999/Cue 999999` 경로, 전체 `Plugin "CopilotResponder" "..."` 래퍼로 계산한다. 실제 계산값은 640B, 2048B 한계 대비 여유 1408B다.
- **Lua↔Python 상한 동치**: `ResponderHarness().config["max_props_names"]`로 Lua 모듈의 `CONFIG`를 직접 읽어 Python `MAX_PROPS_NAMES`와 비교한다. 뮤테이션 확인으로 Python 상수만 17로 바꿨을 때 `test_python_props_name_limit_matches_lua_config`가 `assert 16 == 17`로 실패함을 확인했고, 즉시 16으로 복원했다.
- **테스트**: `uv run pytest server/tests/test_responder_protocol.py -q` → `40 passed`, `uv run pytest server/tests/test_lua_responder_payload_budget.py -q` → `4 passed`, 최종 묶음 `uv run pytest server/tests/test_responder_protocol.py server/tests/test_lua_responder_payload_budget.py -q` → `44 passed`.
- **남은 위험**: 라이브 최대 길이 `props` 왕복과 배포 검증은 M6 범위라 수행하지 않았다. 로컬 LSP 서버(`basedpyright`)는 설치되어 있지 않아 후크가 진단을 건너뛰었다. 작업 지시의 compact `introspect` 형상 목록에는 `class`가 없었지만, M2 출하 Lua와 테스트가 이미 success payload에 `class`를 싣고 있어 문서는 구현을 따랐다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
