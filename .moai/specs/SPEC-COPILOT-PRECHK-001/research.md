# SPEC-COPILOT-PRECHK-001 — 조사 기록 (research)

status: draft (v0.1.0, 2026-07-29) · Tier L · 본 문서는 **읽기 전용 정적 조사 + 비파괴 라이브 사전 프로브**의 기록이다.

> **참조 규약** (SONGCUE research.md의 규약을 계승한다). 본 SPEC의 정본(spec.md · acceptance.md)은 **줄번호로 인용하지 않는다** — `REQ-PRECHK-nnn` · `AC-PRECHK-nnn` · `ASSUMPTION-nn` · 절 제목 같은 **안정 토큰**만 쓴다. 토큰은 개정을 견디고, 가리키는 내용이 사라지면 토큰도 함께 사라져 즉시 드러난다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다 — 그쪽은 커밋 없이 움직이지 않는다. **요구·인수 토큰은 예외 없이 슬러그를 포함한 완전형으로만 쓴다**(슬러그를 뺀 축약형은 본 문서 전체에서 **0건**). 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]`으로 구분 표기하며, **`[실측]`은 라이브 콘솔에서 직접 관측한 것만**을 가리킨다.

---

## 1. 출처와 범위 확정 경로

**출처**: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:98-105` — P2-6 「프리쇼 체크 자동화」. 원문은 *"픽스처 응답 확인 매크로 생성 + 결과 리포트(주소 불일치·무응답 픽스처 탐지)"*이며 *"기존 OSC 상태 조회 능력의 자연스러운 확장"*이라고 적었다 `[문서]`.

**범위는 착수 전 조사로 재확정되었다.** 제안서 원문 그대로는 성립하지 않는다 — 아래 §3이 그 근거다. 사용자가 재범위를 승인했고(2026-07-29), 확정된 형상은 다음 셋이다.

| # | 산출물 | 상태 |
|---|---|---|
| 1 | **패치 정합성 점검** — 주소 중복·간격 겹침·FID 충돌·픽스처타입 부적합 탐지 + 리포트 | **범위 내.** §4가 읽기 가능성을 실측으로 확립 |
| 2 | **픽스처 응답 확인 매크로 생성** — 사람이 콘솔에서 실행해 **눈으로** 확인하는 보조 도구 | **범위 내.** 저작 문법은 등급 T3이며 M0 게이트 대상(§5) |
| 3 | **무응답 픽스처 자동 탐지** | **명시적 DESCOPE.** 관측 경로가 존재하지 않는다(§3.2) |

**BUSKWIZ 후속 측정 4건을 같은 라이브 세션에 상정한다**(사용자 확정) — §6.

---

## 2. 조사 방법과 그 한계

본 SPEC의 조사는 두 층으로 이루어졌다.

| 층 | 수단 | 산출물 | 한계 |
|---|---|---|---|
| 정적 조사 | 병렬 read-only scout 4개 (Orca 오케스트레이션) | `.moai/state/verify/prechk-scout/{1-read-surface,2-rig-assets,3-rulebook,4-openq-and-process}.md` 총 586행 | 코드·문서만 읽었다. 라이브 미접촉 |
| 비파괴 라이브 사전 프로브 | 코디네이터 직접 실행, 읽기 전용 발화만 | 본 문서 §4 · §5의 `[실측]` 표 | 쓰기 0건. 판정 확정은 M0 소관 |

**사전 프로브를 왜 plan-phase에서 돌렸는가.** 산출물 1의 성립 여부가 *"픽스처 주소를 읽을 프로퍼티명이 존재하는가"* 하나에 걸려 있었고 scout는 그것을 **`미확정`**으로 남겼다(`prop`은 프로퍼티명을 열거할 수 없다 — §4.3). 그 전제가 거짓이면 6문서 전체가 헛일이 된다. **비파괴 범위에서 5분에 답이 나오는 질문을 6문서 뒤로 미루지 않았다.** 이것은 M0를 앞당긴 것이 아니라 조사의 일부이며, **판정은 M0가 소유한다**(§8).

> **scout 산출물은 `.gitignore:206`(`.moai/state/`) 대상이라 커밋되지 않는다.** 따라서 본 문서가 그 결론의 **유일한 추적 사본**이며, 인용은 요약이 아니라 좌표와 원문으로 옮겨 적었다. SONGCUE가 같은 계열의 비용을 치른 기록이 `.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:420`에 있다 `[문서]`.

---

## 3. 제안서 전제 2건이 거짓이다

### 3.1 쇼파일 파서는 존재하지 않는다

제안서는 P2-4 항목에서 *"쇼파일 파서가 이미 있어 구현 부담이 낮다"*고 적었다(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:92-95`) `[문서]`. **거짓이다.**

- `server/showfile/` 디렉터리가 없다 `[코드]`(저장소 정적 조사 — 라이브 실측이 아니다) — `server/` 하위는 `audit_logs` · `bridge` · `deploy` · `llm` · `looks` · `measurement` · `orchestrator` · `resources.py` · `rulebook` · `safety` · `tests` · `tools` · `web` 뿐이다.
- XML 파싱 코드는 `server/deploy/pack.py` · `server/deploy/provisioning.py`(배포 패키징)와 `server/safety/console.py`에만 있고 **MA3 쇼파일 구조를 읽는 코드가 아니다** `[코드]`.

**귀결**: 쇼파일 정보에 도달하는 경로는 **라이브 OSC 응답기 하나뿐**이다. 따라서 본 SPEC의 모든 읽기는 응답기의 읽기 표면에 종속되며, 그 표면의 한계가 곧 기능의 한계다.

### 3.2 무응답 픽스처 탐지는 관측 경로가 0건이다

두 scout가 **서로 독립적으로 같은 결론**에 도달했다.

| scout | 결론 | 근거 |
|---|---|---|
| 1 (읽기 표면) | `관측 불가` | `build_exec_result`는 `pcall(Cmd, command)` 하나를 감싸고 그 결과 문자열을 `classify_result`로 분류할 뿐이다 — **픽스처 하드웨어 피드백을 수집하는 코드가 없다** `[코드]` `console/lua/copilot_responder.lua:690-706`. 동사 디스패치 표가 `ping` · `state` · `prop` · `exec` · `deploy` **5종으로 닫혀 있어** 텔레메트리 동사를 추가할 자리가 없다 `[코드]` `console/lua/copilot_responder.lua:884-946` |
| 3 (룰북·선행 실측) | `T5 / 없음` | 픽스처 응답·무응답을 판정할 커맨드나 상태 경로가 **저장소 전체 근거 0건**. 정적 패치 메타데이터와 사람의 시각 확인 기록은 **픽스처 단위 응답 증거가 아니다** |

**DMX 출력값도 관측 불가다** — 응답기가 노출하는 읽기 표면은 오브젝트 트리 `state`(`build_snapshot`, `console/lua/copilot_responder.lua:559-641`)와 단일 프로퍼티 `prop`(`build_prop_result`, 호출부 `console/lua/copilot_responder.lua:913`) 둘뿐이고, 출력·DMX 스트림 동사는 5종 디스패치 표에 없다 `[코드]` `console/lua/copilot_responder.lua:884-946`.

**따라서 산출물 3은 DESCOPE다.** 이것은 실패가 아니라 **정의된 결과**이며, 우회(예: 임의 지연 후 "응답한 것으로 간주")는 금지다 — 관측하지 않은 것을 보고하지 않는다는 규율이 선행 SPEC 전체를 관통한다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:161-163`의 REQ-SONGCUE-017 계열) `[문서]`.

---

## 4. 픽스처 읽기 표면 — 실측

### 4.1 픽스처 열거 경로

`Patch/Stages/1/Fixtures`는 `node.childCount = 19`를 보고하면서 **자식 18개만 반환하고 `truncated = true`**를 세운다 `[실측]`. 즉 **참 픽스처 수는 19이고 그중 18개만 관측됐다** — §4.4의 절단이 이 경로의 **기본 상태**다. 상위 경로도 함께 실측했다.

| 경로 | `ok` | 자식 수 | 비고 |
|---|---|---|---|
| `Patch` | true | 14 | `DmxCurves` · `AttributeDefinit…` · `Layers` · `Classes` · `PsrExtraData` · `FixtureTypes` … |
| `Patch/Stages` | true | 1 | `Stage 1` |
| `Patch/Stages/1` | true | 2 | `Spaces` · `Fixtures` |
| `Patch/Stages/1/Fixtures` | true | **`childCount` 19 / 반환 18** | 픽스처 개체. **`truncated = True`** — 1개가 페이로드 예산에 잘렸다(§4.4) |
| `ShowData/Patch` | true | 0 | 자식 없음. 픽스처에 도달하지 못한다 |

**`Patch/Fixtures`는 발화하지 않았다.** `REQ-DASHUI-022`가 그 경로를 **2.4.2에서 죽은 것으로 실측**해 사용을 금지한다(`.moai/specs/SPEC-COPILOT-DASHUI-001/spec.md:82`) `[문서]`. 선행 실측을 재확인하는 대신 그 판정을 계승한다.

### 4.2 읽히는 프로퍼티와 읽히지 않는 프로퍼티

픽스처 `Patch/Stages/1/Fixtures/1`(`class: Fixture`, `name: RMMXSm1 1`, `childCount: 0`)에 후보 프로퍼티명을 전수 발화했다 `[실측]`.

| 프로퍼티 | `ok` | 값 | 판정 |
|---|---|---|---|
| `FID` | true | `'1'` | **읽힘 — 픽스처 ID** |
| `No` | true | `'1'` | 읽힘 (`FID`와 같은 값) |
| **`Patch`** | true | **`'1.001'`** | **읽힘 — DMX 주소. `유니버스.주소` 형식** |
| `Name` | true | `'RMMXSm1 1'` | 읽힘 |
| `FixtureType` | true | `'FixtureType 1'` | 읽힘 |
| `Mode` | true | `'1 Mode 1'` | 읽힘 |
| `IDType` | true | `'Fixture'` | 읽힘 |
| `CID` | true | `'None'` | 읽히나 값이 `'None'` 문자열 |
| `Index` | true | `'function: 0x105b0f048'` | **함정 — §4.3** |
| `Address` · `DMXAddress` · `DmxAddress` | false | — | `property not readable: <name>` |
| `BreakAddress` · `Break` | false | — | 같음 |
| `Universe` · `DMXUniverse` | false | — | 같음 |
| `FixtureID` · `FixtureId` | false | — | 같음 |

**주소 읽기 경로가 확립되었다**: `prop <path> Patch` → `'<universe>.<address>'`.

### 4.3 함정 3건 — 요구사항으로 승격해야 한다

| # | 함정 | 근거 | 귀결 |
|---|---|---|---|
| **T-1** | **`ok=true`인데 값이 Lua 함수 참조다.** `Index` → `'function: 0x105b0f048'` | `[실측]`. 원인은 `safe_property`가 `handle:Get(name)` 실패 후 `handle[name]`을 그대로 반환하고 `Index`가 **메서드**이기 때문이다 `[코드]` `console/lua/copilot_responder.lua:204-217` | **`ok=true`는 값의 유효성을 보증하지 않는다.** 값 형태 검증이 필수 요구다. 검증 없이 쓰면 함수 포인터를 주소로 오인한다 |
| **T-2** | **공백 포함 프로퍼티명은 조회 자체가 불가능하다.** `'Fixture ID'` 계열 | `[코드]` `server/bridge/protocol.py:141` — `property name must be a single token` 으로 `ProtocolError`를 던진다 | 프로퍼티명 후보에서 공백형을 구조적으로 배제한다. 이 제약은 응답기가 아니라 **클라이언트 검증**에서 온다 |
| **T-3** | **프로퍼티명을 열거할 수 없다.** | `[코드]` `console/lua/copilot_responder.lua:204-217` — 호출자가 준 exact name만 probe하고 enumerate API가 없다 | 읽을 프로퍼티명은 **실측으로 확정한 목록에 한정**된다. §4.2의 표가 그 목록이며, 목록 밖 이름을 추측 발화하지 않는다 |

### 4.4 절단이 예상보다 훨씬 이르게 발동한다 — 본 SPEC의 핵심 제약

`Patch/Stages/1/Fixtures`는 `childCount = 19`를 보고하면서 자식 **18개만** 반환하고 `truncated = True`를 세웠다 `[실측]`. **19개에서 절단이 발동한다.**

이는 산정을 뒤집는다. SONGCUE는 `max_children = 24` 상한을 근거로 *"시퀀스 풀이 24를 넘으면"* 절단된다고 산정했다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:403`) `[문서]`. **그 산정은 절단 원인 하나를 놓쳤다.** 코드에는 **독립된 절단 경로가 둘** 있다 `[코드]`:

| 원인 | 좌표 | 발동 조건 |
|---|---|---|
| ① 자식 수 상한 | `console/lua/copilot_responder.lua:610` — `truncated = cap < total`, `cap = math.min(total, CONFIG.max_children)` (`console/lua/copilot_responder.lua:581`) | 자식이 **24개**를 넘을 때 |
| ② **페이로드 예산** | `console/lua/copilot_responder.lua:634-639` — `while #M.encode_payload(payload) > CONFIG.max_payload and #items > 0 do table.remove(items); payload.truncated = true end` | 인코딩 결과가 **1900바이트**를 넘을 때. 자식 수와 무관하다 |

**픽스처 19개(반환 18개)에서 뜬 절단은 ②다.** `max_payload = 1900`은 MA3 커맨드라인이 ~2048바이트 초과 회신을 **조용히 드롭**하는 실측(2000바이트 배달 / 2100바이트 드롭)에서 나온 값이다 `[문서]` `console/lua/copilot_responder.lua:33-39`. 픽스처 자식은 이름이 길어 개체당 바이트가 커서 24개에 닿기 전에 예산이 먼저 소진된다.

**귀결이 크다.** 패치 점검은 **픽스처 수가 많은 것이 정상**인 도메인이다(현장 리그는 수십~수백). 따라서 절단 처리는 부가 기능이 아니라 **1급 요구**다. 열거가 절단되면 정합성 판정이 **불완전한 집합에 대한 주장**이 되므로, 그 사실을 숨기지 않고 리포트에 싣거나 거부해야 한다.

이 항목은 SONGCUE의 미결(`SONGCUE-F3/G3` — 절단 거동 미실측, `.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:418`)을 **본 SPEC이 실측으로 승계해 닫은 것**이다 `[실측]`.

### 4.5 실측한 리그 데이터 — 19개 중 18개 (**전수가 아니다**)

관측된 18개에서 `FID` · `Patch` · `FixtureType` · `Mode`를 읽었다 `[실측]`. **참 픽스처 수는 19이므로 1개는 미관측이다**(§4.1).

| 슬롯 `i` | 이름 | `FID` | `Patch` | `FixtureType` | `Mode` |
|---|---|---|---|---|---|
| 1 | `RMMXSm1 1` | 1 | `1.001` | `FixtureType 1` | `1 Mode 1` |
| 2~10 | `Copilot MMX 2`~`10` | 2~10 | `1.101` · `1.143` · `1.185` · `1.227` · `1.269` · `1.311` · `1.353` · `1.395` · `1.437` | 같음 | 같음 |
| 11~18 | `MMX 11`~`18` | 11~18 | `2.001` · `2.051` · `2.101` · `2.151` · `2.201` · `2.251` · `2.301` · `2.351` | 같음 | 같음 |

관측 사실: **관측된 18개 범위에서** 주소 중복 **0건**, `FID` 중복 **0건**, 유니버스 2개(1·2), 슬롯 2~10 구간은 42채널 간격, 슬롯 11~18 구간은 50채널 간격.

> **"정합한 리그"라고 단정할 수 없다.** 19번째 픽스처를 관측하지 못했으므로 그것이 기존 주소와 충돌하는지 **알 수 없다.** 이것은 본 SPEC의 `REQ-PRECHK-010`이 금지하는 바로 그 형태 — 불완전한 집합에 대한 정합성 단정 — 이며, **조사 스스로가 그 함정에 빠졌다가 최종 검증에서 잡아냈다**(§4.8). 따라서 판정은 **"관측된 18개 범위에서 충돌 0건, 완전성 불완전(19 중 18, 미관측 1)"**이다.

> **테스트 설계에 직접 영향.** 정합한 리그만으로는 탐지 로직이 참임을 보일 수 없다(모든 판정이 "이상 없음"으로 수렴해 위양성 없는 스캐너와 구별되지 않는다). **결함을 심은 인메모리 픽스처가 필수**이며, 라이브는 "정합 리그에서 오탐 0건"만 보인다.

### 4.6 `FID`가 읽히지만 **그 값이 FID라는 증명은 이 쇼파일로 불가능하다**

§4.5에서 슬롯 `i`와 `FID` 값이 **전부 같다**(1~18). 이것을 "우연"으로 넘기면 안 된다 — **응답기 프로토콜 문서가 이 함정을 이미 정밀하게 문서화해 두었고, 그 서술이 본 조사보다 강하다.**

`console/lua/PROTOCOL.md:305-324`가 `DEFERRED (fixture id in the snapshot)` 항으로 적는다 `[문서]`:

- `Patch/Stages/1/Fixtures`의 자식은 **컨테이너 슬롯 `i`만 carry하고 FID를 carry하지 않으므로**, 슬롯 ≠ FID인 리그에서 `Fixture <i>`는 **엉뚱한 리그를 선택하며 그것이 조용히 일어난다** — MA3가 그 범위를 받아들여 룩을 저장하기 때문이다(`console/lua/PROTOCOL.md:306-308`).
- **`FID` 읽기 접근자는 이 저장소 어디에도 확립되어 있지 않다** — `child.fid`와 `child:Get("fid")`는 **추측**이고, `fid` 증거는 쓰기 측(`AddFixtures{ fid = ... }`, 라이브 증명됨)에만 있다(`console/lua/PROTOCOL.md:316-318`).
- 슬롯 프로브가 `child.no`를 이미 읽으므로, **실제 2.4.2 픽스처에서 그것이 FID를 반환하면 응답기는 둘을 구별할 수 없다**(`console/lua/PROTOCOL.md:319-321`).
- **결정적**: *"the site calibration showfile has slot == FID by coincidence and so **CANNOT distinguish a correct FID probe from a slot probe**. Verify only against a showfile patched so slot ≠ FID (e.g. FIDs 101..109 in stage slots 1..9)"* (`console/lua/PROTOCOL.md:322-324`).

**따라서 본 조사의 `prop FID` → `'1'`은 두 가지로 나누어 적어야 한다.**

| 사실 | 등급 |
|---|---|
| `prop <fixture> FID`가 `ok=true`와 값 `'1'`을 **반환한다** | `[실측]` — 새 사실이다. 위 문서는 `prop` 동사가 없던 시점(v1.4.1)에 쓰였다 |
| 그 값이 **슬롯이 아니라 FID라는 것** | **`[미확정]`** — 이 쇼파일은 슬롯 == FID라서 원리적으로 판별할 수 없다 |

`REQ-LOOKLIB-008`도 같은 금지를 요구 층에서 적는다 — *"fixtures 섹션의 번호를 FID로 취급해 `Fixture … Thru …` 범위를 합성하지 않으며(슬롯≠FID, tools.py:33-36)"* (`.moai/specs/SPEC-COPILOT-LOOKLIB-001/spec.md:124`) `[문서]`. 인용문 안의 `tools.py:33-36`은 **LOOKLIB 원문의 표기**이며 본 SPEC의 직접 좌표가 아니다 — 본 SPEC이 쓰는 좌표는 `.moai/specs/SPEC-COPILOT-LOOKLIB-001/spec.md:124`다.

**귀결 셋을 요구·계획에 반영한다.**

1. **`FID` 판정은 M0의 측정 항목이 아니다** — 현재 쇼파일로는 어떤 라이브 세션도 이것을 닫을 수 없다. **슬롯 ≠ FID로 패치된 쇼파일이 선행 조건**이며 그것은 사용자의 GUI 작업이다(§10).
2. **그때까지 본 SPEC은 FID를 정합성 판정의 근거로 쓰지 않는다.** 리포트는 픽스처를 **슬롯과 이름**으로 식별하고, `FID`로 읽은 값은 `[미확정]` 표시와 함께 참고로만 싣는다 — 관측하지 않은 것을 관측했다고 보고하지 않는다.
3. **`Fixture <n>` 형태의 선택 커맨드를 생성하지 않는다.** 슬롯을 FID로 오인하는 경로 자체를 만들지 않는 것이 유일하게 안전한 형상이다.

### 4.7 채널 점유폭은 읽힌다 — 단 픽스처→타입→모드 연결이 미확정이다

구간 겹침 탐지는 픽스처의 **채널 점유폭**을 요구한다. 점유폭 프로퍼티는 어느 층에도 없었다 `[실측]` — 픽스처와 픽스처타입 양쪽에서 `ChannelCount` · `Channels` · `DMXChannels` · `Footprint` · `Size` · `Length` · `BreakCount` 전부 `property not readable`이다.

**그러나 트리 구조가 답을 갖고 있다** `[실측]`:

| 경로 | `childCount` | `truncated` | 비고 |
|---|---|---|---|
| `Patch/FixtureTypes` | 1 | false | `Robin MMX Spot` |
| `Patch/FixtureTypes/1/DMXModes` | 4 | false | 모드 4종 |
| **`Patch/FixtureTypes/1/DMXModes/1/DMXChannels`** | **29** | true | **점유폭 = 29채널** |

읽히는 프로퍼티는 `Name`(`'Robin MMX Spot'`) · `ShortName`(`'RMMXSm1'`)와 모드의 `Name`(`'Mode 1'`) · `Geometry`(`'Body'`)다 `[실측]`.

§4.5의 실측 간격(슬롯 2~10은 42채널, 11~18은 50채널)이 점유폭 29보다 크므로 **관측된 18개 사이에는 겹침이 없고 간격만 있다.** 미관측 1개에 대해서는 겹침 여부를 말할 수 없다(§4.5의 한정).

#### 절단되어도 계수는 정확하다 — 요구를 정밀하게 만드는 사실

`build_snapshot`의 `node.childCount`는 `total`(= `#children`, 즉 **참 전체 수**)로 설정되고(`console/lua/copilot_responder.lua:607`, `total`은 `console/lua/copilot_responder.lua:580`), 페이로드 예산 루프는 `items`에서만 원소를 제거하며 `childCount`를 **건드리지 않는다**(`console/lua/copilot_responder.lua:634-639`) `[코드]`.

**귀결이 크다.**

| 관측 | 절단 시 신뢰도 |
|---|---|
| **몇 개 있는가** (`node.childCount`) | **정확하다** |
| **그것들이 무엇인가** (`children` 목록) | **불완전하다** |

따라서 완전성 판정을 `truncated` 플래그에만 의존하지 않고 **읽은 개수와 `childCount`의 비교**로 정확히 내릴 수 있다. 이는 "몇 개를 못 읽었는지"까지 수치로 보고할 수 있다는 뜻이다.

**복구 경로의 한계도 함께 적는다.** 절단된 목록을 슬롯별 개별 조회(`Patch/Stages/1/Fixtures/<i>`)로 보완하는 것은 가능하나(단일 노드 조회는 절단되지 않는다), **인덱스 정의역을 모른다** — 풀은 희소할 수 있고(SONGCUE가 시퀀스 풀에서 `1,2,11–17,20,30,…`을 실측했다) 절단된 목록은 어느 슬롯이 존재하는지 알려주지 않는다. 즉 슬롯별 조회는 **경계 있는 범위 탐색**이며 그 범위 밖의 픽스처는 여전히 미관측이다. 이 한계를 숨기지 않는 것이 요구가 된다.

#### 미확정 — 픽스처를 자기 점유폭에 연결하는 경로

픽스처가 주는 것은 `FixtureType` = `'FixtureType 1'`, `Mode` = `'1 Mode 1'`이라는 **표시 문자열**이고 `Patch/FixtureTypes/<i>/DMXModes/<j>` 경로의 **인덱스가 아니다** `[실측]`. 문자열에서 숫자를 뽑아 인덱스로 쓰는 것은 **표시 이름에서 정체성을 끌어내는 것**이며 이 저장소가 반복해 금지한 형태다(`console/lua/PROTOCOL.md:305-324`의 FID 사례가 같은 계열).

**따라서 픽스처 → 픽스처타입 → 모드 → 점유폭 연결은 `[미확정]`이며 M0의 판정 대상이다.** 판정에 따라 산출물 1의 형상이 갈린다.

| 판정 | 산출물 1의 형상 |
|---|---|
| **GO** — 연결 경로가 확립된다 | 주소 중복 + **구간 겹침** 탐지 |
| **부정** | **주소 중복만** 탐지(동일 시작 주소). 구간 겹침은 DESCOPE이며 그 사실을 리포트에 명시 |

어느 쪽이든 산출물 1은 성립한다 — 부정은 **동작 축소이지 저작 차단이 아니다.**

### 4.8 조사가 스스로 절단 함정에 빠졌다 — 요구를 정당화하는 실증

**이 절은 본 SPEC이 막으려는 오류를 조사 자신이 저질렀다가 잡아낸 기록이다.** 숨기지 않고 적는 이유는 그것이 `REQ-PRECHK-004`·`REQ-PRECHK-010`의 필요성을 가장 강하게 뒷받침하는 증거이기 때문이다.

**무엇이 일어났나.** 최초 프로브에서 `Patch/Stages/1/Fixtures`를 열거하며 **`len(children)`만 출력하고 `node.childCount`를 출력하지 않았다.** 반환된 자식이 18개였고 `truncated = true`였는데, 조사는 그 18을 **픽스처 총수로 기록**했다. 참값은 **19**였다 — 19번째가 페이로드 예산에 잘려 나갔다.

**그 결과 두 가지 잘못된 서술이 문서에 들어갔다.**

| 잘못된 서술 | 왜 잘못인가 |
|---|---|
| *"픽스처 18개 전수에서 읽었다"* | 전수가 아니라 **19개 중 18개**였다 |
| *"이 쇼파일은 정합한 리그이며 결함 픽스처가 없다"* | **19번째를 보지 못했으므로 그것이 기존 주소와 충돌하는지 알 수 없다.** 불완전한 집합에 대한 정합성 단정이며 `REQ-PRECHK-010`이 정확히 금지하는 형태다 |

**어떻게 잡았나.** plan-phase 종료 직전 최종 상태 확인에서 `childCount`를 함께 출력했고 19가 나왔다. 처음에는 쇼파일이 변경된 것으로 의심했으나 — 조사의 모든 발화는 `state`·`prop`뿐이고 `exec` **0건**이었다 — 재측정 결과 `childCount = 19` / 반환 18 / `truncated = true`로 **처음부터 그 상태였음**이 확인됐다. 쇼파일은 변경되지 않았고 **조사가 자기 측정을 오독했다.**

**요구에 대한 함의 셋.**

1. **`REQ-PRECHK-004`의 개수 비교는 이론적 방어가 아니다.** 사람이 `len(children)`을 총수로 착각하는 것이 **실제로 일어났고**, `truncated` 플래그가 참이었는데도 그 착각을 막지 못했다. 플래그는 "불완전하다"고 말했지만 **얼마나 불완전한지는 말하지 않았고**, 그 수치의 부재가 오독을 허용했다. 이것이 `node.childCount` 비교를 요구로 승격한 진짜 이유다.
2. **`REQ-PRECHK-010`의 금지가 필요하다는 실증이다.** 조사자는 이 프로젝트의 관측 정직성 규율을 알고 있었고 그것을 다른 항목(`FID`·매크로)에는 정확히 적용했는데도 이 항목에서 미끄러졌다. **규율을 아는 것으로 충분하지 않고 기계 판정이 필요하다.**
3. **절단은 19개에서 발동한다** — `max_children = 24`보다 훨씬 이르다. 현장 리그는 픽스처가 수십~수백이므로 **절단은 예외가 아니라 기본 경로**이며, 그 처리가 1급 요구인 근거가 강화됐다.

**정정 범위**: §4.1 · §4.4 · §4.5 · §4.7 · §10.3의 픽스처 수 서술과 정합 판정을 전부 한정 표현으로 교체했다. `[실측]` 표의 18행 데이터 자체는 **유효하다**(그 18개는 실제로 읽은 값이다) — 틀린 것은 **그것을 전수로 부른 것**과 **거기서 끌어낸 정합 단정**이다.

---

## 5. 매크로 저작 표면 — 등급 T3

| 항목 | 등급 | 근거 |
|---|---|---|
| 매크로 **실행** `Macro <n>` | **T1** | DASHUI 라이브에서 `Macro 1` `ok=True` 실측 |
| 매크로 **저작** `Store Macro <n>` | **T3** | 룰북에만 있고 라이브 `OK` 기록 0건 |
| 매크로 **라인 추가** `Set Macro <m>.<line> Property 'Command' '<cmd>'` | **T3** | 같음 |

현재 쇼파일의 매크로 풀은 자식 **1개**(`Copilot Go`)이고 `truncated = False`다 `[실측]`. 즉 매크로 열거는 가능하다(scout 1의 `가능` 판정과 일치).

**T3은 M0가 GO/DESCOPE로 판정할 대상이다.** SONGCUE M0의 교훈이 직접 적용된다 — **부정 프로브로는 판정할 수 없다**: 날조 키워드도 유효 키워드와 똑같이 `Illegal object`를 주므로 "문법 없음"과 "대상 없음"이 구별되지 않는다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md`의 측정 3) `[문서]`. **판정을 가르는 것은 생성 프로브이며, 그 뒤 재조회가 유일한 효과 증거다.**

---

## 6. BUSKWIZ 후속 4건 — 같은 세션에 상정한다

scout 4가 선행 SPEC 7종의 미결을 전수 통합해(36행) PRECHK M0에 묶을 수 있는 항목을 산정했다. 사용자가 BUSKWIZ G1 동시 상정을 확정했다.

| 항목 | 내용 | 왜 같은 세션인가 |
|---|---|---|
| **G1 / ASSUMPTION-16** | 페이지·익스큐터 **저작 문법 존부**. 원문은 `Copy Page` · `Label Page` · `Label Executor` · `Assign Sequence/Preset At Executor <page/slot>` 계열 | BUSKWIZ가 미측정 사유를 *"결정적 테스트가 쇼파일 쓰기를 요구하고 그 결과가 v1 판정을 바꾸지 못한다"*로 적었다. **PRECHK는 쓰기 세션을 어차피 갖는다** |
| **A17** | **빈 익스큐터 식별.** BUSKWIZ는 미점유 인덱스를 어떤 주소형으로도 해석하지 못해 DESCOPE했다 | 조건부 — G1이 안전한 테스트 페이지·익스큐터를 만들면 같은 세션에서 닫힌다 |
| **A19 / G2** | `Assign Preset … At Executor <n>`의 **실제 효과**. 파싱만 확인됐고 효과 미검증 | 조건부 — G1이 실제 빈·테스트 익스큐터를 확보하면 효과까지 잰다 |
| **G5** | `page × 100 + slot` 주소식의 **page ≥ 2 일반화**. page 1만 재확인됨 | 현재 쇼파일의 페이지 풀은 자식 **1개**(`Page 1`)다 `[실측]` — 즉 **G1이 페이지를 만들지 않으면 G5는 측정 불가**다 |

**재측정하지 않을 것을 명시한다.** scout 4가 닫힘으로 산정한 항목 — `SONGCUE-F1` · `SONGCUE-F2` · `SONGCUE-F4` · `SONGCUE-G1`(TrigTime 절대 시각) · `SONGCUE-CUEFADE` · `LOOKLIB-CONTENT` · `SHOWUI-PAGE1` · `DASHUI-EXECADDR` · `EXECREF-S1/S2` · `EXECBODY-*` — 은 PRECHK M0가 **다시 재지 않는다.**

같은 세션에 **묶지 않을** 항목도 명시한다: `BUSKWIZ-G3`(중도 실패 프로그래머 상태 — 실패 유발 변수가 커진다) · `BUSKWIZ-APPROVAL` · `BUSKWIZ-VALUE` · `SONGCUE-OVERWRITE`(파괴적) · `SONGCUE-F3/G3`(§4.4에서 이미 실측으로 닫혔다) · `SHOWUI-FOH`(주관적 시각 판정) · `LOOKLIB-*`(별도 쇼파일·시각 확인자 필요).

---

## 7. 재사용 계약과 PRESERVE 합집합

### 7.1 재사용하고 재구현하지 않는다

이 프로젝트는 재구현을 금지하고 import 재사용을 요구하며, **검증은 raw 텍스트 grep이 아니라 AST 식별자 스캔**이다 — grep은 호출과 독스트링·주석을 구분하지 못한다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/plan.md:303` 계열의 규율) `[문서]`. 동형 구현이 이미 있다: `server/tests/test_busking_tool.py`의 `_identifiers`와 `server/tests/test_looks_tool.py`의 핸들러 서브트리 변형.

### 7.2 PRESERVE 합집합 — 선행 SPEC 전수 산정

| 항목 | 잠근 SPEC | 좌표 |
|---|---|---|
| `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` | BUSKWIZ · SONGCUE | `.moai/specs/SPEC-COPILOT-BUSKWIZ-001/spec.md:56`, `.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:240` |
| `server/safety/**` | BUSKWIZ · SONGCUE | 같음 |
| `server/web/preview.py` | BUSKWIZ · SONGCUE | 같음 |
| `server/rulebook/assets/v2.4.2/**` | BUSKWIZ · SONGCUE | 같음 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 dedupe 실행 루프 | BUSKWIZ · SONGCUE | `.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:242-243` |
| `console/lua/copilot_responder.lua` | **BUSKWIZ가 잠갔고 SONGCUE v0.2.0이 풀었다** | `.moai/specs/SPEC-COPILOT-BUSKWIZ-001/spec.md:56`, `.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:245-246` |

**본 SPEC은 응답기를 다시 PRESERVE로 둔다.** §4가 필요한 읽기를 현재 `prop`/`state` 표면으로 전부 달성함을 실측했으므로 확장할 이유가 없다. **이 결정을 명시적으로 적는 이유**: SONGCUE에서 오케스트레이터가 `plan.md`의 좁은 목록만 보고 `spec.md §C` 정본을 읽지 않아 `console/lua` 변경을 지시한 실수가 있었고(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md` §F 개정 절) `[문서]`, 같은 실수를 되풀이하지 않으려면 **잠금·해제의 근거를 문서에 남겨야 한다.**

### 7.3 선행 SPEC이 본 SPEC을 직접 구속하는 규칙 2건

| 규칙 | 내용 | 좌표 |
|---|---|---|
| `REQ-DASHUI-022` | `Patch/Fixtures`와 `DataPool/Presets`는 **2.4.2에서 죽은 것으로 실측**되어 사용 금지 | `.moai/specs/SPEC-COPILOT-DASHUI-001/spec.md:82` |
| `REQ-LOOKLIB-008` | fixtures 섹션의 **슬롯 번호를 FID로 취급 금지**(슬롯 ≠ FID) | `.moai/specs/SPEC-COPILOT-LOOKLIB-001/spec.md:124` |

### 7.4 강제된 충돌 — `prop`은 프로덕션 경로로 도달할 수 없고, 그 경로는 PRESERVE다

**본 SPEC의 1차 산출물이 이 항목에 걸린다.** 조사가 마지막에 발견했고, 성격이 SONGCUE의 `plan.md` ↔ `spec.md` 모순과 **같은 계열**이다 — 두 규율이 각각 옳은데 동시에 만족될 수 없다.

#### 사실 셋

| # | 사실 | 좌표 |
|---|---|---|
| 1 | **OSC 송신 표면을 import할 수 있는 디렉터리는 셋뿐이다** — `server/bridge/`(표면 자신) · `server/safety/`(**게이트 — 유일한 프로덕션 호출자**, `REQ-MVP-029`) · `server/tests/`. 파일 단위 예외는 운영 유틸 2개(`server/tools/osc_smoke.py` · `server/tools/responder_roundtrip.py`)뿐이다 | `[코드]` `server/tests/test_architecture.py:27-39` |
| 2 | **그 경계는 테스트로 강제된다** — 위반 시 `REQ-MVP-029 single-chokepoint violation`으로 실패한다 | `[코드]` `server/tests/test_architecture.py:48-61` |
| 3 | **`build_prop_query`에는 프로덕션 소비자가 0건이다** — 정의(`server/bridge/protocol.py:136`) 외에 `server/safety/`나 `server/orchestrator/` 어디에서도 호출되지 않는다 | `[코드]` 전수 grep |

#### 귀결

프로덕션 읽기 경로는 `query_state` 하나다 — `ConsoleLink.query_state`(`server/safety/console.py:372`)가 구현하고 `server/safety/gate.py:120`이 노출하며 `StateQueryPort`(`server/orchestrator/ports.py:68-73`)가 계약을 고정하고 툴 층의 `query_state`(`server/orchestrator/tools.py:601`)가 소비한다 `[코드]`.

**그런데 `state`는 프로퍼티를 반환하지 않는다**(`research.md` §4.2 — 픽스처 자식은 `name`/`class`/`i`만 준다). **주소는 프로퍼티에만 있다.** 따라서:

- `server/prechk/`(신규 모듈)는 `server.bridge`를 import할 수 **없다**(사실 1·2).
- 프로퍼티를 읽으려면 **초크포인트에 `query_property`가 있어야 한다**.
- 그 초크포인트는 `server/safety/**`이고 **BUSKWIZ와 SONGCUE가 둘 다 PRESERVE로 잠갔다**(§7.2).

**우회 경로를 전수로 배제했다.**

| 우회 | 배제 사유 |
|---|---|
| `state`로 주소를 얻는다 | 프로퍼티를 반환하지 않는다(§4.2). 구조적으로 불가 |
| `exec`로 커맨드를 쏘고 결과 문자열에서 주소를 읽는다 | `List` 계열이 `OK`만 돌려주는 것이 실측이다 — 값은 콘솔 커맨드라인 창으로 가고 OSC 응답에 실리지 않는다(SONGCUE M0) |
| `server/tools/` 예외에 파일을 추가한다 | 그 예외는 **운영 유틸**용이며(`server/tests/test_architecture.py:33-39`의 docstring) 프로덕션 기능 경로가 아니다. 기능을 유틸로 위장하는 것이 된다 |
| 응답기를 확장해 `state`가 프로퍼티를 싣게 한다 | `console/lua/**` PRESERVE를 건드리며(§7.2) 페이로드 예산을 더 압박한다(§4.4) — 절단을 악화시킨다 |

#### 필요한 변경의 규모 — 가산적이다

| 파일 | 변경 | 성격 |
|---|---|---|
| `server/safety/console.py` | `query_property(path, property_name) -> dict` 추가. `query_state`(`server/safety/console.py:372-386`)와 **동형** — `build_prop_query`로 요청하고 `kind="prop"` 응답을 기다리며 실패·타임아웃에 예외 | **순수 추가.** 기존 심볼·시그니처 무변경 |
| `server/orchestrator/ports.py` | 프로퍼티 조회 포트 프로토콜 추가(`StateQueryPort` `server/orchestrator/ports.py:68-73`과 동형) | 순수 추가 |
| `server/safety/gate.py` | 위임 노출(`query_state` `server/safety/gate.py:120`과 동형) | 순수 추가 |
| 테스트 대역 | `server/measurement/mock_provider.py:122`의 `query_state` 옆에 동형 추가 | 순수 추가 |

**이것은 PRESERVE 개정을 요구하며 사용자 승인 사항이다.** 본 조사는 개정을 실행하지 않고 **강제성의 근거만 확립한다** — 승인 절차는 `plan.md`의 사용자 접점이 소유한다.

> **SONGCUE의 교훈을 그대로 적용한다.** 그 SPEC에서 오케스트레이터가 정본 PRESERVE를 읽지 않고 워커에게 잠긴 파일 변경을 지시했고, 발견자는 워커였다. **본 SPEC은 착수 전에 발견해 문서에 적었다** — 그것이 이 절의 존재 이유다.

---

## 8. 기각한 대안

| # | 대안 | 기각 사유 |
|---|---|---|
| 1 | **쇼파일 XML을 직접 파싱한다** | 파서가 없고(§3.1) MA3 쇼파일 포맷은 버전 종속이다. 더 결정적으로 **디스크의 export 스냅샷은 라이브 상태가 아니다** — BUSKWIZ가 OSC 설정 XML을 근거로 삼아 오진한 실측 선례가 있다(`.moai/specs/SPEC-COPILOT-BUSKWIZ-001/progress.md:191`) |
| 2 | **무응답 탐지를 "발화 후 일정 시간 무반응"으로 근사한다** | 응답기가 하드웨어 피드백을 수집하지 않으므로(§3.2) 그 시간은 **아무것도 관측하지 않은 시간**이다. 관측하지 않은 것을 보고하는 것이 되어 규율 위반이다 |
| 3 | **응답기를 확장해 DMX 출력값을 읽는다** | 범위 확장이며 본 SPEC의 산출물 1·2가 현재 표면으로 성립한다(§4·§5). SONGCUE가 확장을 택할 때는 `plan.md`와 `spec.md`의 **모순**이라는 강제 사유가 있었다 — 여기엔 없다 |
| 4 | **슬롯 인덱스를 FID로 써서 `prop` 호출을 줄인다** | `REQ-LOOKLIB-008` 위반이며 §4.6의 우연한 일치가 그 오류를 감춘다 |
| 5 | **절단을 무시하고 열거된 것만으로 판정한다** | 불완전 집합에 대한 주장이 된다. §4.4가 절단이 18개에서 이미 발동함을 실측했으므로 **기본 경로**에서 발생한다 |
| 6 | **매크로 저작 문법을 룰북 근거만으로 발화한다** | 등급 T3이며 라이브 `OK` 0건이다(§5). 실측 없이 발화하지 않는다는 규율은 SONGCUE가 `'Time'` 토큰에 적용한 것과 동형이다 |

---

## 9. 핵심 파일

| 파일 | 역할 | 본 SPEC과의 관계 |
|---|---|---|
| `console/lua/copilot_responder.lua` | 응답기 v1.5.0 (`prop` · `cueNo`) | **PRESERVE**(§7.2). 읽기 표면의 정의 |
| `console/lua/PROTOCOL.md` | 동사·스키마 정본 | 읽기 전용 참조 |
| `server/bridge/protocol.py` | `build_state_query` · `build_prop_query` | 재사용. `server/bridge/protocol.py:141`이 T-2의 출처 |
| `server/orchestrator/tools.py` | 툴 등록부 · `run_commands` · `get_rig_context` | 신규 툴 등록만. 잠긴 2구간 무변경 |
| `server/web/dash.py` | 풀 열거 · 익스큐터 주소 해석 | 재사용 대상 산정(scout 2) |
| `.moai/state/verify/songcue-m0/probe.py` | 라이브 프로브 드라이버 | 사전 프로브에 재사용. `.gitignore` 대상 |

---

## 10. 미해결로 남기는 것

본 문서 시점의 미해결을 **성격별로 나눈다.** 조사 단계에서 닫을 수 있는 것은 남기지 않았다.

### 10.1 M0가 소유하는 열린 측정 6건

| # | 항목 | 성격 |
|---|---|---|
| 1 | **주소 읽기 판정 확정** — §4.2가 `prop <fixture> Patch` → `'1.001'`로 GO 방향 실측 | M0는 **재확인만** 하고 재탐색하지 않는다 |
| 2 | **매크로 저작 문법**(§5, 등급 T3, 라이브 `OK` 0건) | **블로킹** — 부정이면 산출물 2가 성립하지 않는다. 생성 프로브 + 재조회로만 갈린다 |
| 2b | **픽스처 → 픽스처타입 → 모드 → 점유폭 연결 경로**(§4.7) | **동작 축소 — 블로킹 아님.** GO면 구간 겹침 탐지, 부정이면 주소 중복만 탐지하고 그 축소를 리포트에 명시한다 |
| 3 | **BUSKWIZ G1** 페이지·익스큐터 저작 문법 존부(§6) | 선행 SPEC이 "후속 최우선"으로 지목 |
| 4 | **A17** 빈 익스큐터 식별 · **A19/G2** `Assign Preset … At Executor` 효과 | **G1 조건부** — G1이 테스트 익스큐터를 확보할 때만 |
| 5 | **G5** `page × 100 + slot`의 page ≥ 2 일반화 | **G1 조건부** — 페이지 풀 자식이 1개라 페이지 생성 없이는 측정 불가(§6) |

### 10.2 어떤 라이브 세션도 닫을 수 없는 것 1건 — 쇼파일 준비가 선행 조건

**`FID` 값의 의미**(§4.6). `prop <fixture> FID`가 값을 반환하는 것은 실측했으나, **그 값이 슬롯이 아니라 FID라는 증명은 현재 쇼파일로 원리적으로 불가능하다** — 슬롯 == FID이기 때문이다. `console/lua/PROTOCOL.md:322-324`가 검증 조건을 명시한다: *"Verify only against a showfile patched so slot ≠ FID (e.g. FIDs 101..109 in stage slots 1..9)"*.

**이것은 M0의 측정 항목이 아니라 사용자의 GUI 작업(쇼파일 패치)을 요구하는 선행 조건이다.** 본 SPEC은 그것을 기다리지 않고, §4.6의 귀결 3항대로 **FID를 정합성 판정의 근거로 쓰지 않는 형상**으로 출하한다. 쇼파일이 준비되면 후속 SPEC이 이 축을 연다.

### 10.3 조사가 실측으로 닫은 것 — M0가 재측정하지 않는다

**절단 거동**(§4.4 — 원인 2종을 코드 좌표로 특정, 픽스처 19개에서 페이로드 예산 발동을 실측)과 **함정 3건**(§4.3 — `ok=true`인 함수 참조 · 공백 프로퍼티명 거부 · 프로퍼티명 열거 불가). 이들은 M0의 측정 항목이 아니라 **요구사항의 입력**이다.

`SONGCUE-F3/G3`(절단 거동 미실측, `.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:418`)은 본 조사가 승계해 닫았다.
