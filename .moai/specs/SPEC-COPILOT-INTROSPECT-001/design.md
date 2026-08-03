# SPEC-COPILOT-INTROSPECT-001 — 설계 (design)

status: draft (v0.1.0, 2026-08-03) · Tier L · base `3176900`

본 문서는 **와이어 형상**(되돌리기 비용 1위)과 **M1 프로브 사다리**(범위 게이트)를 확정 가능한 수준까지 전개한다. §5는 M1 판정을 접어 넣을 슬롯이며 plan-phase에서는 비어 있다.

---

## §1. 설계의 중심 명제

> **"후보를 소진했다"는 "그 정보가 없다"를 함의하지 않는다.**

코디네이터의 22종 소진이 만든 손해는 라운드트립 낭비가 아니라 **틀린 일반화**였다. 본 SPEC의 설계는 그 일반화를 **구조적으로 불가능하게** 만드는 것을 목표로 하며, 그 목표는 두 축으로 나뉜다:

| 축 | 무엇을 없애는가 | 산출물 |
|---|---|---|
| **열거**(`introspect`) | "이 이름이 없다" → "정보가 없다"의 비약 | 필드 목록의 부재가 **관측된 부재**가 된다 |
| **일괄 판독**(`props`) | 후보를 하나씩 찍는 비용과 그 기록의 산실 | "없다"의 근거가 한 회신에 남는다 |

열거 축이 M1에서 부정되어도 **판독 축은 살아남는다.** 두 축을 별개 동사로 분리한 것이 그 생존을 가능하게 만든 설계 결정이다(spec.md D-1).

---

## §2. 요청 문법 — 모호성 제거

### §2.1 기존 문법의 제약

`PROTOCOL.md` §2가 규정하는 파싱은 동사마다 다르다:

| 기존 동사 | rest 파싱 |
|---|---|
| `state` | 전부 rest-of-line = 경로 (공백 허용) |
| `prop` | **마지막** 비공백 토큰 = 프로퍼티 이름, 그 앞 전부 = 경로 |
| `exec` | 전부 rest-of-line = 커맨드 |
| `deploy` | 두 토큰(둘 다 percent-encoded) |

`prop`이 "마지막 토큰"을 쓰는 이유는 경로에 공백이 허용되기 때문이다. 그리고 **본 SPEC이 가장 겨냥하는 경로가 바로 공백을 포함한다** — `Executor 80`(응답기 1.4.0이 `ObjectList()` 네이티브 API로 해석하는 특수 주소 형태).

### §2.2 왜 단일 동사가 불가능한가

`introspect <id> <path> [name-list]` 형태를 시도하면:

```
introspect 7 Executor 80          → "80"은 경로의 일부인가, 이름 목록인가?
```

두 해석 모두 문법적으로 유효하다. 구분자(`@`, `--`)를 도입하면 해결되지만, 그것은 기존 4개 동사 어디에도 없는 다섯 번째 파싱 규칙을 추가하는 것이다.

### §2.3 채택 — 동사 2개

```
introspect <id> <object-path>                 -- 경로 = rest-of-line (state와 동일 규칙)
props       <id> <name-list> <object-path>    -- 이름 목록 = 첫 토큰, 경로 = 나머지 rest-of-line
```

`props`의 이름 목록은 **첫 토큰**이므로 공백을 포함할 수 없고(프로퍼티 이름은 어차피 단일 토큰 — 기존 `build_prop_query`가 이미 강제한다), 경로는 rest-of-line이므로 공백을 자유롭게 포함한다. **양쪽 모두 모호성 0.**

부수 이익: M1 판정이 `introspect`만 게이트하고 `props`는 독립적으로 출하 가능하다.

### §2.4 `prop` / `props` 근접 이름 위험

디스패치는 정확 문자열 일치(`parsed.kind == "prop"`)이므로 **기계적 혼선은 구조적으로 불가능**하다. 남는 것은 사람의 오독이며, 세 겹으로 봉쇄한다:

1. `PROTOCOL.md` §2 요청 표에서 **인접 배치**하고 파싱 규칙 차이를 그 자리에서 대비.
2. Python 빌더 이름을 명확히 분리(`build_prop_query` / `build_props_query`).
3. **회귀 테스트**: `props` 요청이 `prop` kind를 반환하지 않고, 그 역도 아님(AC-INTROSPECT-022).

이름 변경은 어휘를 늘릴 뿐 위험을 줄이지 않으므로 채택하지 않는다(spec.md D-3).

---

## §3. 회신 형상 (되돌리기 비용 1위 — 첫 배포 전 확정)

두 kind 모두 **상태 회신 주소**로 나간다(`prop`과 동일 — 읽기 계열). 인코딩은 기존과 동일한 percent-encoded JSON.

### §3.1 `introspect` kind

성공:

```json
{"v":1,"kind":"introspect","id":"<id>","ok":true,
 "path":"Executor 80","class":"Executor",
 "source":"<채택 열거원 식별자>",
 "fields":[{"n":"Name","t":"string"},{"n":"Index","t":"function"}],
 "total":57,"truncated":true}
```

실패:

```json
{"v":1,"kind":"introspect","id":"<id>","ok":false,"path":"...","error":"<message>"}
```

설계 근거:

- **`fields[].n` + `.t`만** — 값 없음(REQ-INTROSPECT-002). 타입만으로 코디네이터가 겪은 함정이 즉시 갈린다: `Index`가 `"t":"function"`이면 그것이 메서드이지 프로퍼티가 아님을 **값을 읽지 않고** 안다.
- **`source`** — 어느 열거원이 답했는지(REQ-INTROSPECT-003). 출처 불명의 열거는 검증 불가능한 주장이며, 이 프로젝트에서 그런 주장은 유효한 회신이 아니다.
- **`total`** — 축소 이전 관측 총계(REQ-INTROSPECT-015). `state`의 `node.childCount`가 `children` 캡과 무관하게 실제 총계를 나르는 것과 같은 계약. 소비자가 `total - #fields`로 누락분을 계산할 수 있다.
- **`truncated`** — 축소 신호(REQ-INTROSPECT-014). 조용한 절단 금지.
- **키 길이 최소화**(`n`/`t`) — 항목당 바이트가 곧 담을 수 있는 필드 수다. §4 참조.

### §3.2 `props` kind

```json
{"v":1,"kind":"props","id":"<id>","ok":true,
 "path":"DataPool/Sequences/80",
 "reads":[{"n":"CurrentCue","ok":true,"t":"string","v":"Sequence 80.2"},
          {"n":"CueNo","ok":true,"t":"string","v":""},
          {"n":"Progress","ok":false,"e":"property not readable: Progress"}],
 "truncated":false}
```

설계 근거:

- **최상위 `ok`는 "요청이 처리되었다"**(REQ-INTROSPECT-007). 전 이름이 판독 실패여도 `ok:true`다. 이는 기존 `prop`의 의미론(*"`ok`는 콘솔이 값으로 답했다는 뜻이지 값이 쓸 만하다는 뜻이 아니다"* — `server/prechk/query.py` `PropertyRead` docstring)을 목록 층위로 올린 것이며, `PROTOCOL.md` §4.8에 명문화한다.
- **`reads[].e`** — 실패 사유를 항목별로. `read_properties`가 판독 실패를 **포착하되 전파하지 않는** 것과 같은 규율: 하나의 실패가 판독 가능한 나머지를 버리게 해서는 안 된다.
- **값 축약 표시** — 개별 값이 항목 예산을 넘으면 축약하고 그 항목에 표시(REQ-INTROSPECT-008). 표시 키는 M2에서 확정하되 **표시 자체는 협상 대상이 아니다.**
- **`truncated`** — 항목이 통째로 빠진 경우의 신호. 값 축약(항목별)과 항목 탈락(목록 전체)은 **다른 사건이며 다른 신호**를 갖는다. 이 구분이 무너지면 "값이 잘렸다"와 "이름이 통째로 사라졌다"가 같은 플래그를 공유해 소비자가 판별할 수 없다.

### §3.3 두 절단 신호를 분리하는 이유

이 프로젝트에는 *"8룩 중 1개가 조용히 사라진"* 선례가 있다. 그 결함의 본질은 절단 자체가 아니라 **절단이 신호를 남기지 않은 것**이었다. 본 설계는 절단을 두 종류로 나누고 각각에 신호를 준다:

| 사건 | 신호 위치 | 소비자가 알 수 있는 것 |
|---|---|---|
| 값이 길어서 잘림 | 해당 **항목** | 이 이름은 판독됐고 값이 더 길다 |
| 항목이 예산 때문에 빠짐 | 회신 **최상위** | 이름 목록 자체가 불완전하다 |

두 신호를 하나로 접으면 "판독은 됐는데 값이 잘림"과 "아예 판독 결과가 없음"이 구별되지 않는다 — 이는 §1의 중심 명제를 정확히 위반한다.

---

## §4. 페이로드 예산 산술

### §4.1 확립된 제약 (실측)

| 값 | 출처 |
|---|---|
| MA3 커맨드 라인 한계 **2048바이트**(초과 시 **조용히 드롭**, `Cmd()`는 성공 보고) | `server/tests/test_lua_responder_payload_budget.py` `MA3_COMMAND_LINE_LIMIT` — 2026-07-24 라이브 스윕(2000 전달, 2100 드롭) |
| `CONFIG.max_payload = 1900` | 응답기 CONFIG — 위 한계에서 `SendOSC N "<addr>,s,…"` 래퍼 여유분을 뺀 값 |
| `CONFIG.max_children = 24` | 응답기 CONFIG — `state`의 자식 캡 |

**핵심 위험**: 초과는 런타임 신호가 0이다. `cmd_keyword` 전송 변형에서 `Cmd()`가 성공을 보고하고 회신은 그냥 사라진다. 따라서 **테스트가 유일한 그물**이다.

### §4.2 회신 측 — `introspect`

percent-encoding은 비영숫자 바이트를 3배로 부풀린다. 항목 `{"n":"CurrentCue","t":"string"}`의 인코딩 후 크기를 대략 60~80바이트로 잡으면, 1900 예산에서 봉투(고정 키·경로·출처)를 뺀 뒤 대략 **20~25개 항목**이 한 회신에 들어간다.

핸들의 실제 필드 수가 그보다 많으면 절단이 발생한다 — 그래서 `total`이 필수다(§3.1). 그리고 `state`의 무페이징 계약(`PROTOCOL.md` §4.2: *"재조회해도 같은 첫 N개가 영원히 온다"*)과 달리, **`introspect`의 절단분에는 `props`라는 우회로가 없다** — 이름을 모르면 `props`로 물을 수 없기 때문이다.

이것이 이 설계에 남는 **알려진 천장**이다. plan-phase에서 이를 인정하고 기록한다: v1은 절단분을 회수할 수단을 제공하지 않으며, `total`이 그 사실을 소비자에게 **드러낼** 뿐이다. 절단이 실제로 발생하는지는 M7에서 실측하며(핸들의 진짜 필드 수는 미지), 빈번하면 오프셋 토큰 도입이 후속 SPEC 권고가 된다. **예측으로 미리 만들지 않는다** — 이 프로젝트의 YAGNI 규율.

### §4.3 회신 측 — `props`

요청한 이름 수가 상한(§4.4)으로 이미 제한되므로 항목 수는 통제된다. 통제되지 않는 것은 **값의 길이**다. 따라서:

1. 개별 값에 항목 예산을 두고 초과분을 축약 + 표시(§3.2).
2. 그래도 전체가 1900을 넘으면 기존 `build_snapshot`의 size guard 패턴대로 항목을 뒤에서 제거하고 `truncated`.

축약 시 **UTF-8 연속 바이트를 쪼개지 않아야 한다** — 응답기에 이미 그 목적의 헬퍼(`safe_truncate`)가 있으므로 재사용한다. 새로 만들면 두 곳이 갈라진다.

### §4.4 요청 측 — `props` 이름 목록

요청은 다음 형태로 커맨드 라인을 탄다:

```
Plugin "CopilotResponder" "props <id> <n1>,<n2>,...,<nk> <path>"
```

래퍼(`Plugin "CopilotResponder" ""` = 약 26바이트) + 동사 + id + 경로를 뺀 나머지가 이름 목록의 예산이다. 2048 예산은 넉넉하지만 **경로가 길면(깊은 트리) 좁아진다** — 그래서 상한은 개수만이 아니라 **인코딩 후 전체 길이**로도 걸어야 한다(REQ-INTROSPECT-016).

**상한값은 16으로 확정됐다**(2026-08-03 게이트, plan.md §F). 확정 근거는 이 절의 초안이 놓친 것이었다 — 구속 제약은 요청 측 2048B가 **아니라 회신 측 1900B**다(§4.3). plan-audit review-1의 산술: percent-encoding이 약 3배 팽창시켜 대표 성공 항목이 약 111B, 엔벨로프가 약 185B이므로 안전 적재는 약 15항목이다. 요청 측은 16개 × 32B 이름 최대 요청이 **640B(여유 1408B)**로 비구속임이 M3 산술 고정 테스트로 확인됐고, M6가 실물에서 최대 길이 요청 1건을 통과시켰다. 실사용 판독 횟수(약칭 "22")는 2회 왕복으로 처리한다.

**Lua CONFIG 상한과 Python 빌더 상한이 갈라지면 요청이 조용히 드롭된다** — 한쪽만 늘어나면 콘솔이 받지 못하는 요청을 서버가 보낸다. 동치 테스트가 이를 고정한다(AC-INTROSPECT-016 (c)).

---

## §5. M1 프로브 — 열거 가능성 판정

> **이 절은 채워졌다.** plan-phase에서 비어 있었고 run-phase M1이 판정을 §5.7에 접어 넣었다(2026-08-03, **GO** — 채택 열거원 `property_accessors`). 아래 §5.1~§5.6은 **판정 이전의 설계 문맥**으로 보존한다(EXECBODY-001 design.md §5와 동일한 형식). 결론만 필요하면 §5.7로 가라.

### §5.1 판정해야 할 질문

**MA3 2.4.2의 오브젝트 핸들에서 필드 이름 집합을 열거할 수 있는가?**(ASSUMPTION-46)

이 질문에 대한 답은 이 저장소 어디에도 없다:

- 룰북(`server/rulebook/assets/v2.4.2/`) grep 결과 `Dump`·`PropertyCount`·`GetPropertyDisplayName` **전건 0**.
- 저장소의 모든 핸들 접근 코드가 **예외 없이 pcall 방어 프로브 사다리**다 — 확립된 API 표면이 아니라 "시도해 보고 되면 쓴다"는 규율로 쓰여 있다.

### §5.2 알려진 사실 (프로브 설계의 입력)

코디네이터의 22종 실측이 남긴 **구조적 단서** 하나가 있다:

> `prop Executor <n> Index` → `ok=true`, 값 `'function: 0x...'`

응답기의 `M.safe_property`는 `handle:Get(name)`을 먼저 시도하고, 실패하면 `handle[name]`을 시도한다. `Index`가 함수를 돌려줬다는 것은 **`handle[...]`이 메서드 이름까지 해석했다**는 뜻이다 — 즉 핸들의 `__index`가 어떤 메서드 테이블에 닿아 있다.

이것은 **열거 가능성에 대한 긍정적 단서이지 증거가 아니다.** `__index`가 테이블이면 `pairs()`로 순회 가능하고, C 함수면 불가능하다. 어느 쪽인지는 실사격만 답한다.

### §5.3 프로브 사다리 (후보 — 확립된 API 아님, 전부 pcall 방어)

| # | 후보 | 성립 조건 | 성립 시 얻는 것 |
|---|---|---|---|
| 1 | `getmetatable(handle)` → `__index`가 **테이블** → `pairs()` | 메타테이블 접근이 막혀 있지 않고 `__index`가 테이블 | 메서드/필드 이름 전체 |
| 2 | `pairs(handle)` 직접 | `__pairs` 메타메서드 존재 | 필드 이름 전체 |
| 3 | 카운트+이름 접근자 쌍: `PropertyCount()`+`PropertyName(i)`, `GetPropertyDisplayName(i)`, `PropertyType(i)` | 해당 메서드 존재 | 프로퍼티 이름(메서드 제외) — **가장 이상적** |
| 4 | 정수 색인 판독: `handle:Get(i)` | `Get`이 색인 오버로드를 가짐 | 순서 있는 열거 |
| 5 | `handle:Dump()`의 **반환값** | 출력 부작용이 아니라 반환이 있음 | 문자열 파싱 필요 |

**5번 주의**: Printf/Echo가 GUI에 보이지 않는다는 이 프로젝트의 확립된 사실 때문에, `Dump()`가 출력만 하고 반환이 없으면 **무용하다**. 반환값 유무가 채택 조건이다.

### §5.4 정합성 게이트 (채택의 유일한 기준)

열거원이 답했다는 것만으로는 채택하지 않는다. **그럴듯한 부분 열거가 "없다"의 오판을 만드는 재료**이기 때문이다 — 본 SPEC이 없애려는 결함을 새 표면에서 재생산하게 된다.

게이트: **열거된 이름 집합이, 동일 핸들에서 `prop`으로 독립 확인된 판독 가능 이름을 전부 포함할 것.**

대조군(이미 라이브 확인됨):

| 핸들 | 대조 이름 | 확인된 사실 |
|---|---|---|
| `Executor <n>` | `Index` | `ok=true`, 함수 포인터 |
| `Executor <n>` | `Fader` | `ok=true`, 값 `'Master'` |
| `DataPool/Sequences/<n>` | `CurrentCue` | `ok=true`, 재생에 따라 이동 |

이 게이트는 `M.probe_slots`의 규율을 그대로 옮긴 것이다 — **전량 채택 또는 전량 폐기, 부분 채택 없음.** 그 함수의 주석이 이유를 이미 적어 두었다: *"반쯤 믿는 numbering이 그럴듯한 오답이 새어 나가는 정확히 그 경로다."*

### §5.5 증거 채널

**우선 — OSC 직접 회신**(쇼파일 쓰기 0):

프로브 플러그인이 자신의 결과를 percent-encoded JSON으로 조립해 상태 회신 주소로 직접 송신한다. 서버측은 콘솔 링크의 왕복 헬퍼에 **임의 커맨드 라인 + 요청 id**를 넘겨 프로브를 호출한다 — 링크의 상관 로직은 요청 id로만 매칭하므로 응답기가 아닌 플러그인의 회신도 수신된다. (`server/tools/responder_roundtrip.py` 패턴 계승.)

**폴백 — 매크로 채널**(ASSUMPTION-48 부정 시):

`Store Macro <n>` + 프로퍼티 설정 후 `prop`/`state`로 재조회. PRECHK-001 M0가 이 경로를 라이브로 확립했으며, **라인 개체 생성(`Store Macro <m>.<line>`)이 프로퍼티 설정에 선행해야 한다**는 순서 제약까지 실측으로 남겼다.

폴백의 비용: 쇼파일 쓰기가 발생하고 **`Delete`가 블랙리스트**라 툴 경로로 지울 수 없다. SCENE-001 M0가 시퀀스 7개를 남겨 사용자 GUI 삭제를 요청한 선례가 있다. 이 비용을 감수할지는 사용자 결정이다(plan.md §F).

### §5.6 부작용 확인 (ASSUMPTION-49)

미지 이름 판독이 콘솔 상태를 바꾸지 않는다는 것은 **간접 증거만 있다** — 코디네이터가 22회 판독했고 부작용이 관측되지 않았다. 그러나 "관측되지 않았다"는 "없다"가 아니다(본 SPEC의 중심 명제가 그것이다).

프로브는 대상 오브젝트를 **판독 전후로 `state` 재조회**해 형상 무변화를 기록한다. 대조 대상은 **정지 상태 핸들**을 쓴다 — 재생 중 핸들은 자연 변화하므로 대조군으로 부적합하다.

### §5.7 판정 기록 슬롯

**상태: GO (2026-08-03 M1 라이브 프로브 완료).**

증거:

- 원본 로그: `.moai/state/verify/introspect-m1-20260803T091729.log`
- 최종 프로브 소스: `.moai/state/verify/introspect_m1_20260803T092930.lua`
- 최종 프로브 플러그인: `CopilotIntrospectProbe092930` (`osc_slot=2`, `/copilot/state` 직접 회신, 수신 포트 9005)
- 대상: `Executor 201`(정지 + `Go+` 재생 중), `DataPool/Sequences/80`, `DataPool/Groups/1`

**대조군 확인.** 동일 세션에서 `prop`으로 `Executor 201 Index` → `function: 0x...`, `Executor 201 Fader` → `Master`, `DataPool/Sequences/80 CurrentCue` → `Sequence 80.3`을 확인했다. `PropertyName()`은 MA의 canonical uppercase 이름을 반환하므로, 같은 세션에서 `INDEX` → `201`, `FADER` → `Master`, `CURRENTCUE` → `Sequence 80.3`도 별도 확인했다. 게이트 비교는 이 canonical property name을 같은 이름의 대소문자 표기로 취급한다.

| 사다리 | 결과 | 게이트 판정 |
|---|---|---|
| 1. `getmetatable(handle).__index` | `getmetatable`은 성공하지만 `__index` 타입이 `function`이다. 테이블 순회 불가, 이름 0건. | 폐기 |
| 2. `pairs(handle)` | `bad argument #1 to 'for iterator'`로 실패, 이름 0건. | 폐기 |
| 3. `PropertyCount()` + `PropertyName(i)` / `PropertyType(i)` | **성공.** Executor 71건, Sequence 65건, Group 101건. `PropertyName`/`PropertyType`는 응답했고 `GetPropertyDisplayName`은 응답 0건. Executor 정지/재생 모두 `INDEX`·`FADER` 포함, Sequence 80은 `CURRENTCUE` 포함. | **채택** |
| 4. `handle:Get(i)` 정수 색인 | 호출은 성공하나 이름 0건. Sequence 80은 userdata 5건을 반환했지만 프로퍼티 이름으로 쓰지 못한다. | 폐기 |
| 5. `handle:Dump()` 반환값 | 문자열 반환 있음. 토큰 스캔으로 Executor의 `INDEX`·`FADER`, Sequence의 `CURRENTCUE`를 포함해 게이트는 통과한다. | 구현 비채택 |

**채택 열거원:** `property_accessors` 하나만 M2 구현 입력으로 채택한다. 이유: 같은 게이트를 통과한 `dump_return`은 문자열 토큰 파싱에 의존하고, §5.3이 예고한 대로 파싱 비용과 거짓 양성 위험이 있다. `PropertyCount()` + `PropertyName(i)`는 구조화된 이름 열거원이므로 M2는 이 경로만 구현한다.

**부작용 확인(ASSUMPTION-49).** 정지 대상 `Executor 201`을 프로브 전후 `state`로 재조회했다. 전후 모두 `children=[]`, `node={ childCount=0, class=Executor, name="Ballad Yellow Red", sequenceNo=20 }`, `truncated=false`로 동일했다. 재생 대상은 `Go+ Executor 201` 후 프로브하고 `Off Executor 201`로 원복했다.

**ASSUMPTION 판정.**

| Assumption | 판정 | 근거 |
|---|---|---|
| ASSUMPTION-46 | TRUE | `PropertyCount()` + `PropertyName(i)`가 MA3 2.4.2 핸들에서 이름 집합을 열거했다. `Dump()`도 문자열 이름 후보를 반환했다. |
| ASSUMPTION-47 | TRUE | 채택원 `property_accessors`가 Executor 정지/재생 대조 이름(`INDEX`·`FADER`)과 Sequence 대조 이름(`CURRENTCUE`)을 전부 포함했다. |
| ASSUMPTION-48 | TRUE | 프로브 플러그인 자체가 `SendOSCMessage`로 `/copilot/state`에 percent-encoded JSON을 직접 회신했다. 매크로/라벨/쇼파일 증거 폴백은 사용하지 않았다. |
| ASSUMPTION-49 | TRUE | 정지 `Executor 201`의 `state` 형상이 프로브 전후 동일했다. |

**콘솔 잔여.** slot 지정 `Import Plugin <slot> '<slug>'`만 성공했다. slotless import 시도와 payload 축소 재시도 때문에 본 세션의 일회용 프로브 플러그인 슬롯이 남았다(`introspect-m1-20260803T091729`, `introspect_m1_20260803T091729`, `CopilotIntrospectProbe091729`, `CopilotIntrospectProbe092425`, `CopilotIntrospectProbe092745`, `CopilotIntrospectProbe092930`). 증거 채널로서의 매크로/라벨/씬 쓰기는 0건이다.

---

## §6. 민감정보 경계

### §6.1 무엇이 노출되고 무엇이 노출되지 않는가

| 동사 | 노출 | 미노출 | 근거 |
|---|---|---|---|
| `introspect` | 필드 **이름**과 **타입** | 값 전부 | 이름·타입은 오브젝트의 **스키마**이지 쇼의 **내용**이 아니다. 큐 이름·픽스처 이름 같은 내용은 이미 `state`가 노출하며, 본 SPEC이 새로 여는 축이 아니다 |
| `props` | 호출자가 **명시한 이름**의 값 | 명시하지 않은 것 전부 | 호출자 선택이 곧 경계. 전 필드 덤프 모드는 존재하지 않는다(REQ-INTROSPECT-017) |

### §6.2 봉쇄 지점 3곳

1. **덤프 모드 부재** — 한 요청으로 모든 값을 가져올 수단이 없다. 이것이 1차 방어다.
2. **감사에 값 금지** — 감사 주체는 `경로 + 요청 이름들`이며 값을 담지 않는다(REQ-INTROSPECT-018). 기존 `property_query` 감사가 `f"{path} {property_name}"`을 쓰는 것과 같은 수준이며, 이 한 줄이 **민감정보 경계의 실제 집행 지점**이다. AC-INTROSPECT-018이 감시 문자열 부재로 기계 검증한다.
3. **LLM 툴 미등재** — 닫힌 툴 집합 18개 유지(REQ-INTROSPECT-024). v1의 유일한 소비자는 개발자 CLI이므로, 판독된 값이 모델 컨텍스트로 흘러 들어가는 경로가 **구조적으로 없다.**

### §6.3 남는 위험 (정직한 기록)

`props`로 판독한 값은 개발자 CLI의 stdout과 프로브 로그(`.moai/state/verify/**`)에 남는다. `.moai/state/`는 gitignore이므로 저장소에는 들어가지 않지만, **로그 파일 자체는 로컬에 남는다.** v1은 이를 허용한다 — 소비자가 개발자이고 대상이 로컬 쇼파일이기 때문이다. LLM 툴을 여는 후속 SPEC은 이 경계를 **다시 판정해야 한다.**

---

## §7. 서버 소비 경로

```
introspect_probe.py (개발자 CLI, v1의 유일한 소비자)
  → 좁은 포트 프로토콜 (ports.py — 소비자가 필요한 능력만 선언)
    → SafetyGate 메서드 (감사 1:1, 값 미기록)
      → ConsoleLink 왕복 (동일 id 상관 / 동일 타임아웃 / 동일 예외 타입)
        → OSC 송신 (기존 단일 표면, 신규 채널 없음)
```

설계 근거:

- **좁은 포트 분리** — `PropertyQueryPort`의 docstring이 이유를 이미 적었다: *"게이트는 한 오브젝트에 둘 다 구현하지만, 프로토콜을 분리해 두면 소비자가 필요한 능력만 정확히 선언할 수 있다."* 열거와 일괄 판독을 하나로 둘지 둘로 나눌지는 M1 판정 후 확정한다(NEGATIVE면 판독 하나만 존재하므로 자연히 하나).
- **신규 수신 채널 없음** — 두 kind 모두 상태 회신 주소로 오며, 링크의 수신 처리가 이미 그 주소를 받는다.
- **감사 1:1** — 타임아웃도 이미 **보낸** 송신이므로 감사에 남는다(REQ-INTROSPECT-023). 기존 두 조회 메서드가 같은 규율을 명시적 주석과 함께 지키고 있다.

---

## §8. 알려진 천장 (정직한 기록)

1. **`introspect` 절단분은 회수할 수 없다.** `state`는 슬롯별 개별 조회라는 우회로가 있지만, 열거는 이름을 모르면 물을 수 없다. `total`이 누락 사실을 드러낼 뿐이다(§4.2). **M7 실측(2026-08-03)**: 이 천장이 실물에서 핸들당 **27~28필드**로 나타났고(Executor 27/71 · Sequence 28/65 · Group 28/101), M7의 모든 결론 범위를 그만큼 좁혔다. 페이징/커서가 후속 SPEC 1순위 권고인 이유다(progress.md §M7.7).
2. **열거의 정확성은 콘솔이 신고하지 않는다.** §5.4의 교차 대조 게이트가 유일한 그물이며, 그 게이트는 *"확인된 이름을 포함하는가"*만 검사한다 — **거짓 양성**(실재하지 않는 이름을 열거에 섞는 열거원)은 걸러내지 못한다. 소비자는 열거된 이름을 `props`로 재확인해야 하며, 이 2단 절차가 v1의 운용 규율이다.
3. **판독 가능 ≠ 유의미.** `Fader` → `'Master'`(페이더 이름), `CueNo` → 재생 중 빈 문자열이 실제 사례다. 본 SPEC은 값을 **해석하지 않으며**, 의미 판정은 사람 또는 후속 SPEC의 몫이다.
4. **클래스 단위 일반화 — M7에서 관측 범위 내 참으로 판정됐다(2026-08-03).** 같은 클래스 두 인스턴스의 관측 집합이 이름·순서까지 동일했다(Executor 201 ≡ 101, Sequences/80 ≡ 1). 대조군 Group 1은 Executor와 15개만 공유해 집합이 클래스에 따라 실제로 갈린다(비공허). **다만 판정은 관측된 앞 27~28개에 한정된다** — 전체 집합(71/65/101)에 대한 일반화는 여전히 미검증이며, 천장 1번이 풀려야 닫힌다. 그때까지 "Executor는 이런 필드를 갖는다"는 진술은 **관측 범위 안에서만** 참이다(ASSUMPTION-51, progress.md §M7.2).
