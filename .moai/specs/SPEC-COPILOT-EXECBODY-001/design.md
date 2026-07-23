# SPEC-COPILOT-EXECBODY-001 — 설계 근거 (design)

status: completed (v0.1.0, 2026-07-24) · Tier L · M1~M6 전 마일스톤 완료, AC-EXECBODY-010 라이브 인수 완료. §5(역주소 문제 해소)는 **닫혔다** — M1 라이브 프로브(§5.8)가 주소 해석(ASSUMPTION-10)을 GO로 확정했고, M2 착수 직전 추가 프로브(§5.9)가 익스큐터→시퀀스 아이덴티티 접근자(ASSUMPTION-12)를 VERIFIED로 닫았다. `console/lua/copilot_responder.lua`의 `Executor` 분기(`node.sequenceNo`)가 §5.9의 API로 구현되었다.

## §1. 설계 의도

EXECREF-001이 증명한 것: 안전 게이트의 인식 폐쇄 집합(`RECOGNIZED_REFERENCE_TYPES`)에 `Executor`를 추가하는 것만으로는 실제 마찰이 줄지 않는다 — 콘솔 응답기가 익스큐터의 본문(할당 시퀀스)을 노출하지 않기 때문이다. 본 SPEC의 설계 의도는 그 노출 갭을 **콘솔측에서** 닫는 것이다: 응답기가 익스큐터 전용 로직으로 할당-시퀀스 아이덴티티를 노출하면, Python 세이프티 게이트는 그 아이덴티티를 **이미 신뢰하는 시퀀스 본문 조회 경로**로 위임하기만 하면 된다. 새로운 신뢰 경계를 만드는 것이 아니라, 기존 신뢰 경계(시퀀스 본문 조회)로 가는 진입점을 하나 더 여는 것이다.

이 설계는 EXECREF-001의 핵심 원칙("새 방어를 만드는 게 아니라 기존 방어 안으로 참조를 밀어 넣는다")을 한 단계 더 계승한다 — 이번에는 참조 인식이 아니라 본문 조회 자체가 기존 경로로 위임된다.

## §2. 변경 표면 (두 곳)

1. **`console/lua/copilot_responder.lua`** — `build_snapshot`에 익스큐터 전용 분기 추가. 범용 `handle:Children()` 호출은 유지하되(다른 오브젝트 클래스는 계속 그 경로를 쓴다), `class == "Executor"`인 경우에만 별도 로직이 개입한다.
2. **`server/safety/console.py`** — `StateBodyFetcher`(또는 후속 메커니즘)가 `"Executor <no>"` 참조를 만나면, 1단계로 M2가 노출한 아이덴티티를 조회하고, 2단계로 그 아이덴티티를 시퀀스 참조처럼 취급해 기존 시퀀스 본문 조회 경로에 위임한다.

`expand.py`·`gate.py`·`classify.py`·`blacklist.yaml`·`server/web/**`·`ui/src/**`는 원칙적으로 무변경이다(EXECREF-001이 이미 `classify.py`에 `Executor` 인식을 도입했으므로, 그 부분은 본 SPEC의 전제로 소비만 한다).

### §2.1 실패 시(M1 GO 이전) 안전한 상태

M2가 착수되지 않거나 부분 완료 상태에서 세션이 종료되면, 시스템은 EXECREF-001 v0.2.0 종료 시점과 동일한 상태로 남는다 — 익스큐터는 인식되지만 본문을 읽지 못해 계속 보류된다. 이는 fail-closed 방향으로 안전한 중간 상태이며, M2 착수 자체가 회귀를 만들지 않는다.

## §3. 데이터 흐름 (설계 목표 — M1 결과에 따라 세부 형상이 확정됨)

```
[패널/채팅] --Go+ Executor <no>--> [classify.py: 인식됨 (EXECREF-001)]
    --> [expand.py: invoking, reference="Executor <no>"]
    --> [console.py StateBodyFetcher: 익스큐터 아이덴티티 조회 (신규, M4)]
         --> [Lua 응답기: build_snapshot 익스큐터 분기 (신규, M2)]
              --> 할당 시퀀스 아이덴티티 반환
    --> [console.py: 아이덴티티를 시퀀스 참조로 위임 (신규, M4)]
         --> [기존 시퀀스 본문 조회 경로 (EXECREF-001 이전부터 존재)]
    --> [expand.py: 본문 라인 = 시퀀스 큐 이름 목록, 블랙리스트 검사]
    --> [gate.py: 승인 요청 여부 결정]
```

핵심 설계 목표는 마지막 4단계(`expand.py` 이후)가 **완전히 무변경**이라는 것 — 익스큐터 경유든 시퀀스 직접 참조든 동일한 파이프라인을 탄다.

## §4. False-Negative 검토

EXECREF-001의 false-negative 검토(design.md §4)는 참조 인식 확장에 대한 것이었다. 본 SPEC은 **본문 조회 자체가 새로 가능해지므로**, 그 조회가 만드는 노출면을 별도로 검토해야 한다.

### §4.0 열거

| # | 위험 | 방어 | 신규/기존 |
|---|---|---|---|
| 1 | 익스큐터가 순환 참조를 만드는 시퀀스를 가리킴 | 기존 순환 탐지(expand.py:85-86), 참조-타입-무관 | 기존, 상속 |
| 2 | 익스큐터 본문(시퀀스 큐)에 블랙리스트 커맨드 존재 | 기존 블랙리스트 본문 보류(expand.py:110-112) | 기존, 상속 |
| 3 | 아이덴티티 조회 자체가 실패/타임아웃 | `BodyUnavailable` → `_hold`(REQ-EXECBODY-006) | 기존 패턴 재사용 |
| 4 | 아이덴티티가 잘못된 오브젝트를 가리킴(역주소 오류) | M1의 검증 절차(REQ-EXECBODY-007/008) — 검증 안 되면 미출하 | **신규 위험, 신규 방어** |
| 5 | 큐 CMD 프로퍼티가 여전히 스크리닝되지 않음(cue-CMD 갭) | 기존 갭, 본 SPEC이 확장하지 않음(REQ-EXECBODY-015) | 기존, 계승(악화 아님) |

### §4.1 신규 위험(#4)이 이 SPEC의 설계 핵심인 이유

위 4개 위험 중 1~3, 5는 EXECREF-001의 기존 기계가 그대로 방어한다. **오직 #4(역주소 오류)만이 이 SPEC이 스스로 도입하는 신규 공격면이다** — 잘못된 페이지-로컬 인덱스를 계산해 엉뚱한 오브젝트의 본문을 조회하면, 게이트는 "다른 익스큐터의 본문을 보고 이 익스큐터를 판단"하는 조용한 오분류를 일으킬 수 있다. 이것이 spec.md §A "역주소 문제"가 각주가 아니라 SPEC 전체의 설계 중심으로 다뤄지는 이유다.

## §5. 역주소 문제 해소 — 열린 설계 슬롯 (M1 오프라인 조사 완료 · 라이브 프로브 대기)

**이 절은 아직 최종 해소되지 않았다.** M1의 콘솔-프리 부분은 2026-07-23 완료되었다(§5.4 오프라인 조사 기록). 오프라인 소스만으로는 후보 (a)를 확인도 반증도 할 수 없음이 확정되어, 결정 게이트는 §5.7의 **VERIFY-PENDING** 상태로 기록된다 — 다음 라이브 세션이 §5.5/§5.6의 ready-to-run 프로브를 실행해 이 슬롯을 GO 또는 DESCOPE로 닫는다. EXECREF-001 design.md §5가 처음 작성 시점(v0.1.0)에 열려 있다가 2026-07-23 라이브 프로브로 닫힌 것과 동일한 구조다.

### §5.1 세 가지 후보 경로

| 후보 | 내용 | 장점 | 위험 |
|---|---|---|---|
| **(a) 콘솔 네이티브 주소 해석 (회피, 1순위)** | grandMA3 Lua API가 커맨드-라인 문자열을 핸들로 직접 해석하는 함수를 제공한다면, 그 함수를 사용해 페이지-로컬 인덱스 역산 자체를 피한다. | 미검증 관례 의존이 전혀 없음 — 콘솔이 이미 신뢰하는 자기 해석을 재사용. | 그런 API가 존재하지 않을 수 있음(미확인) |
| **(b) 검증된 오프셋 관례 (검증 후 사용, 2순위)** | 페이지 1의 +100 오프셋이 다른 페이지에서도 성립함을 라이브로 확인한 뒤, 확인된 관례를 게이트 코드에 반영한다. | (a)가 없을 때의 유일한 실현 경로 | 검증 범위가 유한하다(모든 페이지를 다 검증할 수는 없다) — `@MX:WARN` + `@MX:REASON`으로 위험 지대 명시 필요 |
| **(c) DESCOPE (최후)** | (a)도 (b)도 확보되지 않으면 본문 해석을 이연한다. | 안전(fail-closed 유지), EXECREF-001 M2 선례와 일관 | 목표(마찰 제거) 미달성 — 정직하게 보고 |

### §5.2 결정 기준

- (a)가 확인되면 (b)는 불필요 — §5.1 우선순위대로 채택한다.
- (a)가 없고 (b)가 2개 이상 서로 다른 페이지에서 검증되면, (b)를 채택하되 `@MX:WARN`으로 신뢰 경계를 명시한다.
- 둘 다 실패하면 (c) — plan.md §A.3이 이 경우의 절차를 규정한다.

### §5.3 왜 이 슬롯을 plan-phase에서 미리 추측하지 않는가

EXECREF-001 design.md AP-7("프로브 없이 §5.3 후보 중 하나를 임의 채택")이 명시적으로 금지하는 반-패턴이다. 이 SPEC의 plan-phase 세션은 실물 콘솔 라이브 접근이 확보되지 않은 상태에서 작성되었으므로(연구 자료는 EXECREF-001의 기존 프로브 결과를 인용할 뿐, 본 SPEC 고유의 신규 라이브 조사를 수행하지 않았다), (a)/(b)의 실제 존재 여부를 이 문서가 단정하는 것은 근거 없는 추측이다. M1이 실제 조사를 수행한다.

### §5.4 M1 오프라인 조사 기록 (2026-07-23, 콘솔-프리 — 실측)

본 세션은 실물 콘솔 접근이 없으므로, 오프라인에서 답할 수 있는 것과 없는 것을 분리해 실측했다. 아래 4개 항목이 실제 실행된 조사와 그 관측 결과다.

**(1) 저장소 전역 API 토큰 탐색 — 0건.**
`grep -rn -i "ObjectList\|FromAddr\|AddrNative\|StrToHandle\|HandleToStr\|GetPath\|ToAddr" --include="*.md" --include="*.lua" --include="*.py" .` (`.moai/specs` 제외) → **매치 0건**. 이 저장소에는 grandMA3 Lua API 레퍼런스 문서 자체가 존재하지 않는다 — 후보 (a)의 존재/부재를 오프라인 소스로 답하는 것은 구조적으로 불가능하다.

**(2) 응답기 API 표면 인벤토리 — 주소-해석 호출 0건.**
`console/lua/copilot_responder.lua` 전체 리뷰. 응답기가 이미 사용하는(따라서 2.4.2에서 동작이 확인된) MA3 Lua 표면의 전량: 루트 진입점 `Root()` / `DataPool()` / `ShowData()` / `Patch()`(ROOT_ALIASES, :323-328), 탐색 `handle:Children()` / `handle:Count()` / `handle:Ptr(i)`(safe_children, :289-317), 아이덴티티 `handle.name` / `handle:Get("name")` / `handle:GetClass()` / `handle.class`(:161-187), 슬롯 프로브 `child:Index()` / `child.index` / `child.no` / `child:GetIndex()` / `child:Get("no")`(SLOT_PROBES, :218-224), 실행 `Cmd()`, 전송 `SendOSCMessage` / `Cmd("SendOSC ...")`, 기타 `GetVar(UserVars(), ...)` / `load` / `Printf`. **커맨드-라인 주소 문자열을 핸들로 해석하는 호출은 어디에도 없다.** 즉 기존 코드는 ASSUMPTION-10을 확인해 주지 못하며, 반증하지도 못한다(사용하지 않았을 뿐이다).

**(3) 룰북 확인 — 커맨드라인 문법 문서이지 Lua API 문서가 아님.**
`server/rulebook/assets/v2.4.2/`의 5개 파일(00_grammar / 10_object_model / 20_korean_terms / 30_plugin_patterns / 31_choreography_patterns)은 LLM용 **콘솔 커맨드라인 문법** 문서다. `10_object_model.md:23-25`는 `Page <page>.<executor>` 주소 규약(커맨드라인 측)만 기록하며 Lua 측 해석 API는 다루지 않는다.

**(4) EXECREF-001 프로브 증거 재판독 — 기존 확인 + 신규 관측 2건.**
`.moai/state/verify/showui-m6-resume/executor-offset.jsonl`(16행 = 8 익스큐터 × raw/plus100 2형) + `5-probe-body.log` 재판독. 기존 확인: 페이지 1의 8/8 샘플 전부 `console_no = local_index + 100` 성립. 이번 재판독에서 추출한 **신규 관측 2건**:

- **(4a) 로컬 인덱스는 100을 초과한다.** 페이지 1에 로컬 인덱스 `101`이 실존한다(콘솔 발화 번호 201, `Off Executor 201` OK). 따라서 "콘솔번호 = 페이지×100 + 로컬인덱스" 류의 규약이라면 인덱스 도메인이 0~99가 아니므로 **페이지 교차 충돌이 구조적으로 가능하다** — 페이지 1 로컬 101(→201)과, 만약 동일 형태가 성립한다면 페이지 2 로컬 1(→201)이 같은 발화 번호를 갖는다. 오프셋 규약의 "형태"(상수 +100인지, 페이지-종속인지, 충돌을 어떻게 처리하는지)가 다중-페이지 프로브의 정확한 판별 대상이다(acceptance.md §D "페이지 미지정 익스큐터 번호 충돌" 엣지 케이스의 실측 근거).
- **(4b) "OK"는 올바른 타깃팅의 증거가 아니다.** `{"i": 101, "addressed": 101, "form": "raw", "status": "ok"}` 행 — raw형 `Off Executor 101`이 성공한 것은 로컬 인덱스 주소가 동작해서가 아니라, **콘솔 번호 101이 로컬 인덱스 1의 익스큐터에 속하기 때문**이다(오발 히트). 번호 충돌 하에서는 잘못된 타깃으로 간 커맨드도 조용히 성공한다 — §4 위험 #4(조용한 오분류)의 구체적 실측 사례이며, §5.6의 발화-기반 판별 폴백이 "OK/Illegal object" 이분만으로는 불충분한 이유다.

부가 관측: 증거 쇼파일에는 페이지가 1개뿐이었다(`DataPool/Pages` childCount: 1) — 다중-페이지 검증은 라이브 세션에서 페이지 ≥2 쇼파일 준비(GUI 사용자 작업)를 선행 조건으로 요구한다.

### §5.5 ASSUMPTION-10/-12 후보 API — 미검증 가설 + ready-to-run 프로브 (P-A ~ P-D)

**정직성 프레이밍(구속력 있음)**: 아래 후보 API 이름들은 일반 grandMA3 Lua API 지식에서 온 **가설**이다 — 이 저장소의 어떤 소스에도 등장하지 않으며(§5.4-1), 검증된 문서 인용도 아니다. onPC 2.4.2에서의 존재/부재/시그니처가 바로 프로브가 확정해야 할 대상이다. 프로브 확인 전에는 어떤 후보도 채택하지 않는다(AP-7).

**전달 메커니즘(라이브 세션 결정 사항)**: 아래 스니펫은 읽기 전용(조회만)이지만, 콘솔에서 Lua를 실행하는 경로 자체는 둘 중 하나다 — (i) 콘솔 Lua 에디터에 수동 붙여넣기(배포 기계 불사용, 쇼파일 무변경에 가장 가까움), (ii) 임시 프로브 플러그인 배포(`plugin_pack.py` 경로 — 플러그인 풀에 1회 쓰기 발생, `Delete Plugin`으로 원복 가능). (ii)는 plan.md의 "쓰기 0" 문구를 초과하므로 라이브 세션에서 명시적 사용자 승인 후에만 사용한다. 스니펫 자체는 어느 경로로 실행해도 조회 외 부작용이 없다.

```lua
-- EXECBODY-001 M1 라이브 프로브 (조회 전용 — Cmd 발화 0, 오브젝트 쓰기 0)
-- 실행: 콘솔 Lua 에디터 붙여넣기 권장. 각 행 결과를 그대로 기록할 것.
local function try(label, fn)
    local ok, value = pcall(fn)
    Printf("EXECBODY-PROBE %s | ok=%s | type=%s | value=%s",
        label, tostring(ok), type(value), tostring(value))
    return ok, value
end

-- P-A (ASSUMPTION-10, 회피 후보 — 전역 주소 해석 함수의 존재/시그니처)
-- 대상 번호 201 = 페이지 1 로컬 101의 실측 콘솔 번호 (§5.4-4a). 쇼파일이 다르면
-- 라이브 세션에서 실존하는 콘솔 번호로 치환할 것.
try("A1 ObjectList('Executor 201')", function() return ObjectList("Executor 201") end)
try("A2 FromAddr('Executor 201')",   function() return FromAddr("Executor 201") end)
try("A3 GetExecutor(201)",           function() return GetExecutor(201) end)
try("A4 Obj('Executor 201')",        function() return Obj("Executor 201") end)

-- P-B (ASSUMPTION-12 — 익스큐터 핸들 → 할당 시퀀스 접근자)
-- 핸들 획득은 이미 검증된 경로(ASSUMPTION-8: 페이지-로컬 인덱스 탐색)만 사용.
local exec  -- DataPool/Pages/1/<로컬인덱스> 를 응답기와 동일한 Children() 탐색으로 획득
do
    local ok, pages = pcall(function() return DataPool().Pages end)
    -- 응답기 ROOT_ALIASES/safe_children과 동일한 방어적 탐색으로 페이지 1의
    -- 첫 익스큐터 핸들을 얻는다 (여기서는 개요만 — 라이브 세션에서 responder의
    -- M.resolve_path("DataPool/Pages/1/<i>") 재사용이 가장 확실).
end
try("B0 exec:Dump()",         function() return exec:Dump() end)          -- 프로퍼티 전수 나열
try("B1 exec.Object",         function() return exec.Object end)
try("B2 exec:Get('Object')",  function() return exec:Get("Object") end)
try("B3 exec:Get('object')",  function() return exec:Get("object") end)
try("B4 exec.object",         function() return exec.object end)

-- P-C (역주소 문제의 순방향 해소 후보 — 핸들이 자기 콘솔-발화 주소를 보고하는가)
try("C1 exec:Addr()",         function() return exec:Addr() end)
try("C2 exec:AddrNative()",   function() return exec:AddrNative() end)
try("C3 exec:ToAddr()",       function() return exec:ToAddr() end)
try("C4 tostring(exec)",      function() return tostring(exec) end)
```

**판별 기준(각 프로브의 결정적 결과)**:

- **P-A 확인** = 어느 한 형태가 핸들(또는 핸들 목록)을 반환하고, 그 핸들의 `GetClass()`가 `"Executor"`이며 GUI에서 확인되는 콘솔 번호 201의 익스큐터와 일치 → **후보 (a) 채택, §5.6 오프셋 검증 전체가 moot**(§5.2 결정 기준 1행). **P-A 반증** = 네 형태 전부 pcall 실패("attempt to call a nil value" 류) 또는 무의미 반환 → 후보 (a)는 이 후보군에 한해 기각(전역 함수가 더 존재할 가능성은 B0 Dump류 탐색으로 보강).
- **P-B 확인** = 어느 접근자가 `GetClass() == "Sequence"`인 핸들(또는 시퀀스 번호)을 반환하고 GUI의 할당 표시와 일치 → **ASSUMPTION-12 확정 + 정확한 접근자명 기록**(M2의 익스큐터 분기가 사용할 API). 전부 실패 → B0 Dump 출력에서 후보 프로퍼티명을 발굴해 재시도; 그래도 없으면 아이덴티티 노출 자체가 불가 → DESCOPE로 기운다.
- **P-C 확인** = 어느 형태가 콘솔-발화 번호를 담은 주소 문자열(예: `Page 1.201` 또는 `Executor 201` 형)을 반환 → **역주소 문제의 순방향 해소**: 응답기가 페이지를 전수 열거하며 익스큐터마다 "콘솔-발화 번호 + 할당 시퀀스 아이덴티티"를 함께 내보내면, 게이트는 발화 번호로 정방향 조회만 하면 되고 역산(콘솔번호→로컬인덱스)은 어느 층에도 존재하지 않게 된다. 반환값이 로컬 인덱스 형(예: `1.101`)이면 확인 실패로 기록.

### §5.6 ASSUMPTION-11 다중-페이지 오프셋 검증 프로브 계획 (후보 (b) — P-A·P-C 모두 실패 시에만)

**선행 조건(사이트 준비, GUI 사용자 작업)**: 페이지 ≥2, 각 페이지에 로컬 위치가 알려진 익스큐터 ≥2개를 가진 쇼파일. 가능하면 한 페이지에 로컬 인덱스 >100 익스큐터 1개 포함(§5.4-4a 충돌 도메인 검사용). 준비는 GUI 작업이며 프로브 자체는 조회 전용이다.

1. **1단계(읽기 전용, 기존 기계 재사용)**: `probe_executor_body.py` 패턴으로 `DataPool/Pages` → 각 페이지 p의 자식 열거(로컬 인덱스 + 이름). 페이지별 로컬 인덱스 표를 확보한다.
2. **2단계(P-C 성공 시 — 완전 읽기 전용 경로)**: 각 페이지의 각 샘플 익스큐터에서 P-C 주소 문자열을 읽어 `console_no = f(page, local_index)` 매핑을 페이지별로 기록. **PASS** = 동일한 매핑 형태가 서로 다른 ≥2 페이지 × 페이지당 ≥2 샘플에서 재현되고 f가 명시적으로 기록됨(상수 +100인지, `page*100 + local`인지, 그 외인지). **FAIL** = 어느 페이지든 형태 이탈.
3. **3단계(폴백 — 읽기 전용 아님, 명시적 승인 필요)**: P-C도 없으면 남는 판별 수단은 SHOWUI-M6식 발화 검사(`Off Executor <n>`, 비활성 익스큐터 한정, "OK"/"Illegal object" 비교)뿐이다. 이는 발화 >0으로 plan.md M1의 "발화 0" 제약을 초과하므로 **라이브 세션에서 오케스트레이터/사용자의 명시적 편차 승인 후에만** 수행한다. 또한 §5.4-4b의 실측 교훈을 구속 조건으로 적용한다: 번호 충돌 하에서 "OK"는 올바른 타깃의 증거가 아니므로, 발화 검사는 (i) 프로브 쇼파일 안에서 충돌 불가능함이 1단계 표로 증명된 번호만 쓰거나 (ii) 각 발화를 관측 가능한 상태 변화와 짝지어야 한다.

**ASSUMPTION-11 판정**: **VERIFIED** = 동일 매핑 형태가 서로 다른 ≥2 페이지에서 성립함이 기록되고, 페이지 교차 충돌 질문(어떤 발화 번호가 어느 페이지들에서 겹칠 수 있는가)에 답이 남음. **NOT VERIFIED** = 그 외 전부 → 후보 (b) 사용 불가 → (a)도 실패했다면 §5.1 (c) DESCOPE.

### §5.7 M1 결정 게이트 — 상태: **GO** (라이브 프로브 완료, 2026-07-23)

| 판정 후보 | 채택 여부 | 근거 |
|---|---|---|
| **GO (M2 착수)** | **예 (본 세션 결정)** | §5.8 라이브 프로브가 후보 (a)를 확정 확인했다 — `ObjectList("Executor <console_no>")[1]`이 `GetClass()=="Executor"`이며 `:Index()`가 GUI-실측 페이지-로컬 인덱스와 정확히 일치한다(§5.4-4a의 101과 재현). §5.2 결정 기준 1행("(a)가 확인되면 (b)는 불필요")에 따라 §5.6 다중-페이지 오프셋 검증은 moot. |
| DESCOPE | 아니오 | 후보 (a)가 반증이 아니라 **확인**되었으므로 해당 없음. |
| VERIFY-PENDING | 아니오 (해소됨) | 라이브 프로브가 완료되어 이 상태를 벗어났다. |

**귀결**: 회피 경로(후보 a)가 확정되었으므로, M2는 페이지-로컬 인덱스 역산(+100 오프셋 관례)이 아니라 `ObjectList("Executor <console_no>")[1]:Index()` 네이티브 API를 사용해 구현한다. §5.6(다중-페이지 오프셋 검증 계획)은 폐기하지 않고 보존하되 M2 구현 경로로는 채택하지 않는다(§5.2 1행).

### §5.8 라이브 프로브 실행 기록 (2026-07-23, 콘솔 라이브 — 실측)

사용자가 콘솔 Lua 에디터에 §5.5 스니펫을 수동 붙여넣기(전달 메커니즘 (i) 채택 — 배포 기계 미사용)해 직접 실행했다. Printf/Echo 출력 경로가 GUI에서 확인되지 않아, 이 저장소가 이미 신뢰하는 관례(§5.4 조사 대상이었던 `patch_here.xml` 등 기존 배포 플러그인의 `Store Macro` + `Label Macro` 패턴)로 프로브 스크립트를 재작성해 재실행했다. 두 스크립트 모두 `luac -p`로 문법 검증 + 목(mock) 실행까지 로컬에서 사전 검증했다(`.moai/state/verify/execbody_probe_v3.lua`, `execbody_probe_v4.lua`).

**1차 프로브 결과** (Macro 150~154 라벨, 콘솔 Command Line History에서 실측):

| ID | 프로브 | ok | 값(sanitize, 24자 절단) |
|---|---|---|---|
| A1 | `ObjectList("Executor 201")` | true | `table: 0x...`(테이블) |
| A2 | `FromAddr("Executor 201")` | true | `nil` |
| A3 | `GetExecutor(201)` | true | `Page 1.201`(24자 내 전체) |
| A4 | `Obj("Executor 201")` | **false** | `...attempt to call a t...` — `Obj`는 함수가 아니라 기존 전역 테이블과 이름 충돌 |

**2차 프로브 결과** (Macro 160~166, 169 — A1 테이블 내부 검사 + A3 전체값):

| ID | 검사 | 결과 |
|---|---|---|
| 160 | `GetExecutor(201)` 전체값(28자 한도, 절단 없음) | `Page 1.201` |
| 161 | `#ObjectList("Executor 201")` | **1** (원소 1개) |
| 162 | `type(v1[1])` | **`userdata`** — 네이티브 콘솔 오브젝트 핸들의 특징 |
| 163 | `v1[1]:GetClass()` | ok=true, **`"Executor"`** — §5.5 판정 기준의 확인 조건과 정확히 일치 |
| 164 | `v1[1].name` | ok=true, `"Sequence 71"` — 이 익스큐터에 할당된 시퀀스명(참고용) |
| 165 | `v1[1]:Index()` | ok=true, **`101`** — §5.4-4a에서 GUI로 실측한 페이지 1 로컬 인덱스(콘솔번호 201)와 **완전 일치** |
| 166 | `v1:GetClass()`(테이블 자체, `v1[1]`이 아님) | ok=false — 예상대로(테이블 래퍼 자체는 핸들이 아님) |
| 169 | 스크립트 완주 sentinel | `DONE2` — 전체 스크립트 정상 종료 확인 |

**판정**: §5.5 P-A 확인 기준("어느 한 형태가 핸들을 반환하고, `GetClass()`가 `"Executor"`이며 GUI에서 확인되는 콘솔 번호와 일치") — `ObjectList("Executor 201")[1]`이 정확히 이 기준을 충족한다. `:Index()`가 반환한 `101`은 §5.4-4a에서 별도의 독립 경로(GUI 발화 테스트 `Off Executor 201` OK)로 이미 확정된 페이지-로컬 인덱스와 동일하다 — 서로 독립적인 두 관측이 수렴한다.

**M2 채택 API**: `ObjectList("Executor " .. console_no)[1]`을 호출해 핸들을 얻고, `handle:GetClass() == "Executor"`로 아이덴티티를 확인한 뒤 `handle:Index()`로 페이지-로컬 인덱스를 얻는다. `Obj()`는 기존 전역과 충돌하므로 사용하지 않는다. `FromAddr()`은 이 입력 형식에 대해 무의미(nil)했으므로 채택하지 않는다.

**콘솔 잔여 정리 항목**(다음 세션 또는 사용자가 직접): Plugins 풀 슬롯 5 `UserPlugin 5`(현재 프로브 스크립트 보관 중), Macros 풀 슬롯 13(빈 오브젝트, 본 세션 실수로 생성), 150~154·160~166·169(프로브 결과 라벨). 전부 쇼파일 무해 잔여물이며 삭제해도 M2 구현에 영향 없음.

### §5.9 M2 사전 프로브 — P-B/ASSUMPTION-12 확정 (2026-07-23, 콘솔 라이브 — 실측)

M2 착수 전 재점검에서, plan.md §B M1 세 번째 조사 항목("익스큐터→시퀀스 프로퍼티 접근성", ASSUMPTION-12)이 §5.8의 라이브 프로브 세션에서 실제로는 테스트되지 않았음을 발견했다 — §5.5 P-B 스니펫은 작성만 되고 실행되지 않은 채 M1 게이트가 GO로 닫혔다. ASSUMPTION-12 없이 M2 코드를 쓰는 것은 AP-7(라이브 조사 없는 후보 채택)과 동일한 위험이므로, M2 착수 직전에 2라운드 추가 라이브 프로브를 수행했다.

**1차 프로브**(`execbody_probe_v5.lua`, Macro 170~176 — `ObjectList("Executor 201")[1]`에서 후보 접근자 5종 시도):

| ID | 접근자 | ok | type | 값(sanitize) |
|---|---|---|---|---|
| 171 | `exec.Object` | true | userdata | `Sequence 71` |
| 172 | `exec:Get("Object")` | true | userdata | `Sequence 71` |
| 173 | `exec:Get("object")` | true | userdata | `Sequence 71` |
| 174 | `exec.Assign` | true | nil | (프로퍼티 부재) |
| 175 | `exec:Get("Assign")` | true | nil | (프로퍼티 부재) |

세 형태(`.Object`/`:Get("Object")`/`:Get("object")`) 모두 동일한 핸들을 반환했다 — §5.8의 `.name` 관측("Sequence 71")과 독립적으로 수렴. `Assign` 계열은 존재하지 않는 프로퍼티(에러가 아니라 `nil`)로 확인되어 기각.

**2차 프로브**(`execbody_probe_v6.lua`, Macro 180~186 — 1차가 반환한 `exec.Object` 핸들 자체를 검사):

| ID | 접근자 | ok | type | 값 |
|---|---|---|---|---|
| 181 | `seq:GetClass()` | true | string | `Sequence` |
| 182 | `seq:Index()` | true | number | **71** |
| 183 | `seq:Get("No")` | true | number | **71** |
| 184 | `seq:Get("no")` | true | number | **71** |
| 185 | `seq.name` | true | string | `Sequence 71` |

GUI 확인(시퀀스 풀 화면 캡처): 풀 슬롯 71에 실제 오브젝트(무명, 클래스 기본 표시 "Sequence") 존재 — `seq:Index()`가 돌려준 71과 정확히 일치.

**판정**: ASSUMPTION-12 **VERIFIED**. `exec.Object`(또는 `:Get("Object")`/`:Get("object")`, 셋 다 동등)가 할당된 시퀀스 핸들을 반환하고, 그 핸들의 `GetClass()=="Sequence"` + `:Index()`(또는 `:Get("No")`/`:Get("no")`)가 실제 풀 번호를 이름-파싱 없이 반환한다. `seq.name`("Sequence 71")은 참고용으로만 관측되며 아이덴티티 도출에는 사용하지 않는다(AC-EXECBODY-005 — EXECREF-001 REQ-EXECREF-007과 동일한 취약성 부류: 표시 이름은 사용자가 바꾸면 깨진다).

**M2 채택 API**:
```lua
local assigned = handle.Object  -- (또는 handle:Get("Object")/:Get("object"))
if assigned and assigned:GetClass() == "Sequence" then
    local seq_no = assigned:Index()  -- (또는 :Get("No")/:Get("no"))
end
```

**구현**: `console/lua/copilot_responder.lua`에 `M.safe_object`(신규 헬퍼, `safe_name`/`safe_class`와 동일한 다중-폼 방어 패턴)를 추가하고, `build_snapshot`의 `Executor` 분기가 `node.sequenceNo`를 가산적으로 노출한다(PROTOCOL.md §4.2). 시퀀스 번호 추출은 ASSUMPTION-7의 `SLOT_PROBES`/`as_slot`을 그대로 재사용했다 — 별도 프로브 목록을 새로 만들지 않았다(단순성 원칙). PROTOCOL_VERSION은 범프하지 않는다(가산 필드, ASSUMPTION-6/§4.5와 동일 선례). 콘솔 잔여물: Macro 170~176·180~186(전부 쇼파일 무해, 정리는 §5.8과 동일하게 대기).

## §6. 테스트 설계 방향

### §6.1 인메모리 fetcher로 결정론 유지

익스큐터→시퀀스 아이덴티티 조회는 인메모리 dict 기반 fake(EXECREF-001이 확립한 `DictBodyFetcher` 패턴)로 테스트한다 — 스크리닝 경로 자체의 유닛 테스트에는 OSC가 개입하지 않는다. 콘솔 왕복이 필요한 부분은 별도 라이브 프로브(§6.3)로만 검증한다.

### §6.2 fail-closed 실패 모드는 개별 AC (병합 금지)

빈 본문 / 조회 실패 / 파싱 불가 / 역주소 검증 실패는 서로 다른 실패 모드이므로 각각 개별 테스트로 유지한다 — 병합하면 한 경로가 회귀해도 다른 경로가 테스트를 통과시킨다(EXECREF-001 §6.2 원칙 계승).

### §6.3 라이브 프로브는 읽기 전용, 발화 0·쓰기 0

M1/M3의 모든 라이브 프로브는 `state` 또는 등가 조회 동사만 사용한다 — EXECREF-001의 `probe_executor_body.py` 패턴을 그대로 재사용한다.

### §6.4 회귀 방어선

`test_safety_gate.py`, `test_web_panel_execute.py`, `test_safety_classify.py`, `test_safety_expand.py`, `test_safety_corpus.py`, `test_safety_console.py`, `test_architecture.py`. 안전 모듈 변경이므로 이들의 그린은 협상 대상이 아니다.

## §7. 반-패턴 (이 SPEC 근처에서 발생하는 유혹)

| # | 유혹 | 왜 금지인가 |
|---|---|---|
| AP-1 | "패널 커맨드는 이미 안전하니 expansion을 건너뛰자" | 이름만 다른 제2 스크리닝. gate.py:260-264 `@MX:ANCHOR` |
| AP-2 | 익스큐터 전용 분류 분기를 `classify_command` 밖에 둠 | classify.py:158-161 `@MX:ANCHOR` |
| AP-3 | 익스큐터 `name`에서 시퀀스를 파싱 | rename에 깨짐. EXECREF-001 REQ-EXECREF-007이 이미 기각 |
| AP-4 | M1 검증 없이 페이지 1 오프셋을 일반화해 즉시 구현 착수 | 미검증 out-of-band 관례에 안전-인접 코드를 얹는 것 — REQ-EXECBODY-007이 금지 |
| AP-5 | 배열 인덱스로 익스큐터 키잉 | 번호가 비연속(1,5,11,91,...). `tools.py:164-168` 계약 |
| AP-6 | "게이트가 큐 CMD를 검증한다"는 서술 | 하지 않는다. REQ-EXECBODY-015 |
| AP-7 | 라이브 조사 없이 §5.1 후보 (a) 또는 (b)를 임의 채택 | 추측. M1 완료 전에는 §5를 확정하지 않는다 |
| AP-8 | M1이 DESCOPE로 귀결되었는데 "부분 성공"으로 보고 | 마찰 미감소는 목표 미달이며 그렇게 보고해야 함(EXECREF-001 계승) |
| AP-9 | CUECMD-001 작업을 본 SPEC 커밋 범위에 슬쩍 포함 | 명시적으로 번들하지 않기로 결정됨(REQ-EXECBODY-016) |

## §8. 교차 참조

- `SPEC-COPILOT-EXECREF-001/design.md` §4~§5.6 — false-negative 검토 방법론, 역주소 문제의 최초 발견과 이연 결정.
- `SPEC-COPILOT-EXECREF-001/research.md` §5.3 — 본 SPEC의 origin 권고 및 설계 입력(로컬 인덱스 vs 콘솔 주소 구분).
- `.moai/state/verify/showui-m6-resume/5-probe-body.log`, `executor-offset.jsonl` — EXECREF-001이 이미 수행한 선행 프로브 증거(본 SPEC의 M1이 재출발점으로 삼는다).
- `console/lua/PROTOCOL.md` §6 — ASSUMPTION 번호 체계.
