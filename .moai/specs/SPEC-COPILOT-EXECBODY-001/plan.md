# SPEC-COPILOT-EXECBODY-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-07-23) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음.

## §A. 접근 요약 (Context)

본 절은 **변경 가능성이 높은 결정을 먼저** 배치한다(가장 되돌리기 어렵거나 후속 결정을 규정하는 순서). 빌드 순서(§B)는 이와 다를 수 있다 — §A.2가 그 편차를 설명한다.

### §A.1 결정 우선순위 (리뷰 순서 — 빌드 순서 아님)

| 순위 | 결정 | 위치 | 왜 먼저 검토해야 하는가 |
|---|---|---|---|
| **1위** | **역주소 문제 해소 방식** — 콘솔 네이티브 주소 해석 API를 쓸 것인가(회피), 다중-페이지 검증된 오프셋 관례를 쓸 것인가(검증 후 사용), 아니면 DESCOPE하는가 | spec.md §A "역주소 문제" + B.3, plan.md **M1** | 안전-인접 코드의 신뢰 경계를 규정하는 결정. 이 결정이 M2 이후 전부를 좌우한다 — EXECREF-001의 M2 DESCOPE 선례처럼 SPEC 전체가 부분 이연으로 귀결될 수 있다. |
| 2위 | 응답기 스냅샷 페이로드 스키마 변경 형상(가산적 필드 vs `PROTOCOL_VERSION` 범프) | spec.md REQ-EXECBODY-003, plan.md M2 | 와이어 프로토콜은 콘솔측 재배포가 필요해 되돌리기 비용이 높다 — 첫 배포 전에 형상을 확정해야 한다. |
| 3위 | 익스큐터→시퀀스 아이덴티티를 안전 게이트 진입점으로 배선하는 지점(StateBodyFetcher 확장 vs 신규 fetcher 클래스) | spec.md REQ-EXECBODY-004, plan.md M4 | 기존 `DEFAULT_BODY_PATHS` 템플릿 메커니즘(`{type_word: "path/{ref}"}`)이 익스큐터가 요구하는 2단계 조회(익스큐터→시퀀스 아이덴티티→시퀀스 본문)를 표현할 수 있는지가 아직 불확실 — EXECREF-001 §4.3이 같은 형상 제약을 남겼다. |
| 4위 | 코퍼스/테스트 축 확장(참조 타입별 본문 시나리오 추가) | plan.md M5 | 기계적 리팩터 — 상위 3개 결정이 확정된 뒤 자연히 따라온다. |

### §A.2 빌드 순서가 리뷰 순서와 다른 이유

빌드는 순수 가역성-우선 순서를 따르지 않는다 — **M1(역주소 문제 해소)이 먼저 오는 이유는 그것이 M2 이후 전체의 실행 가능성을 게이트하기 때문**이다. EXECREF-001의 선례(프로브 결과 게이트 M2, 결과가 부정적이면 DESCOPE)를 반복한다: M1은 조사이지 구현이 아니며, M1의 결과가 부정적(회피 경로 없음 + 다중-페이지 검증 실패)이면 M2 이후는 진행하지 않는다.

빌드 순서: **M1(조사) → M2(응답기) → M3(배포) → M4(게이트 배선) → M5(코퍼스/회귀) → M6(라이브 검증)**. 리뷰 순서는 §A.1로 분리한다.

### §A.3 M1 게이트 — DESCOPE는 실패가 아니라 유효한 출력

EXECREF-001이 확립한 규율을 그대로 계승한다: **부분 성공을 성공으로 위장하지 않는다.** M1의 조사 결과가 회피 경로도 검증 가능한 관례도 찾지 못하면, 본 SPEC은 정직하게 "본문 해석은 여전히 불가능하다"고 보고하고 마무리한다 — 이는 M1 자체의 실패가 아니라 M1이 답해야 했던 질문에 대한 정직한 답이다. 이 경우 run-phase는 M1 조사 결과만 기록하고 종료하며, spec.md의 REQ-EXECBODY-004 이후 요구사항은 EXECREF-001의 REQ-EXECREF-004~006처럼 `[DEFERRED]`로 재표기한다(sync-phase에서 spec.md를 재델리게이션 없이 manager-develop이 body를 고칠 수 없으므로, 이 경우 manager-spec으로 blocker 재위임이 필요하다 — B8 참조).

## §B. 마일스톤 (M1..M6)

### M1 — 역주소 문제 조사 및 해소 (cycle_type=ddd, 조사 중심)

- **회피 경로 조사**: grandMA3 Lua API 문서/룰북(`server/rulebook/assets/v2.4.2/`)과 실물 콘솔에서, 커맨드-라인 주소 문자열(예: `"Executor 201"`)을 오브젝트 핸들로 직접 해석하는 API가 존재하는지 조사한다(ASSUMPTION-10). 존재하면 이후 마일스톤은 이 경로를 채택하고 M1의 나머지 하위 항목(다중-페이지 검증)은 불필요해진다.
- **회피 경로가 없는 경우 — 다중-페이지 검증**: 읽기 전용 라이브 프로브(발화 0, 쓰기 0 — EXECREF-001의 `probe_executor_body.py` 패턴 계승)를 최소 2개의 서로 다른 페이지에서 실행해, 콘솔 발화 번호 ↔ 페이지-로컬 인덱스 관계가 페이지 1의 +100 오프셋과 동일한 형태(오프셋 상수 자체는 페이지마다 다를 수 있음 — "관계의 형태"가 안정적인지가 검증 대상)를 유지하는지 확인한다(ASSUMPTION-11). 오프셋이 페이지마다 다른 상수라면, 그 상수를 안전하게 도출하는 방법(예: 페이지 메타데이터 질의)이 있는지도 함께 조사한다.
- **익스큐터→시퀀스 프로퍼티 접근성 조사**: 익스큐터 핸들이 `Children()`이 아닌 다른 접근자(프로퍼티/포인터)로 할당된 시퀀스의 아이덴티티를 노출하는지 실측한다(ASSUMPTION-12) — 이는 회피/검증 경로 어느 쪽을 택하든 공통으로 필요한 사실이다.
- **결정 게이트**: 위 세 조사 결과를 종합해 M2 착수 여부를 결정한다. 결과는 `design.md §5`(신규 절, 본 SPEC 자체의 설계 슬롯 — EXECREF-001 design.md §5와 동일한 형식)에 접어 넣는다.
- 산출물: 조사 로그(`.moai/state/verify/execbody-m1-probe.log` 또는 등가 경로), design.md §5 fold-in, 결정 게이트 기록.

### M2 — Lua 응답기 확장 (익스큐터 전용 아이덴티티 노출)

- M1에서 선택된 해석 메커니즘(회피 경로 우선, 검증된 관례는 차선)에 따라 `build_snapshot`에 익스큐터 전용 분기를 추가한다.
- 스냅샷 페이로드에 할당-시퀀스 아이덴티티 필드를 가산적으로 추가한다(REQ-EXECBODY-003). `PROTOCOL_VERSION` 범프 필요 여부를 이 마일스톤에서 확정한다.
- 파일: `console/lua/copilot_responder.lua`, `console/lua/PROTOCOL.md`(가산적 필드 문서화, 필요 시 ASSUMPTION-10/11/12 등재).
- 이 마일스톤은 M1의 결정 게이트가 진행(GO)일 때만 착수한다.

### M3 — 배포 체인 (재패키징 + Import + 라이브 재검증)

- `plugin_pack.py`를 통해 응답기 변경을 재패키징(네이티브 인라인 Base64)한다.
- 콘솔측 Import를 수행하고, 읽기 전용 프로브로 신규 필드가 실제로 노출되는지 라이브 확인한다(발화 0, 쓰기 0 — build/state 동사만).
- 실패 시(신규 필드가 예상과 다른 값을 반환하는 등) M2로 되돌아간다 — 이 왕복은 콘솔측 변경의 정상적인 반복 비용이며 SPEC 실패가 아니다.

### M4 — 안전 게이트 본문 해석 배선 (Python 측)

- `server/safety/console.py`의 `StateBodyFetcher`(또는 §A.1 3위 결정에 따른 후속 메커니즘)를 확장해, M2가 노출한 할당-시퀀스 아이덴티티를 해석 진입점으로 사용한다.
- 기존 `Macro`/`Plugin`/`Sequence` 3종의 해석 결과는 회귀 없이 보존한다(REQ-EXECBODY-004의 위임 대상인 시퀀스 본문 조회 경로 자체는 무변경).
- 파일: `server/safety/console.py`, `server/tests/test_safety_console.py`.

### M5 — Fail-closed 회귀 + 코퍼스 확장

- EXECREF-001이 도입한 모든 보류 사유(재귀 상한·순환 탐지·블랙리스트 본문·본문 부재·파싱 불가)가 익스큐터-경유 본문 해석에 대해서도 개별적으로 성립함을 검증한다(REQ-EXECBODY-011, design.md §6.2의 병합 금지 원칙 계승).
- `test_safety_corpus.py`의 참조 타입 축(EXECREF-001 M1이 이미 동적 순회로 리팩터한 축)에 익스큐터-본문-해석 시나리오를 추가한다 — 축 자체의 재구조화는 필요 없다(EXECREF-001이 이미 완료).
- 파일: `server/safety/expand.py`(무변경 확인), `server/tests/test_safety_expand.py`, `server/tests/test_safety_corpus.py`, `server/tests/test_safety_console.py`.

### M6 — 전체 그린 + 라이브 검증 (실제 마찰 제거 실측)

- pytest 전체 + vitest 전체. 기준선(run-phase 킥오프 시점 재측정치) 대비 신규 실패 0건.
- `test_architecture.py` 그린 + `server/safety/**` OSC import 경계 grep 무변경.
- **라이브 AC(REQ-EXECBODY-013)**: 실물 콘솔에서 패널 익스큐터 타일 1회 누름 → 승인 카드 0장·`SaveShow` 0회, 콘솔 송신 기록이 정확히 `["Go+ Executor <no>"]`임을 실측한다. **이는 M1~M4가 GO 결정으로 진행된 경우에만 달성 가능한 목표다** — M1이 DESCOPE로 귀결되면 M6은 "여전히 마찰 감소 없음"을 정직하게 실측·기록하는 것으로 범위가 축소된다(EXECREF-001 M3 선례).

## §C. 기술 제약

1. **신규 런타임 의존성 0.** 기존 stdlib + 기존 grandMA3 Lua API 표면 + 기존 Python 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**:
   - `server/safety/gate.py:260-264` — 스크리닝 경로는 정확히 하나.
   - `server/safety/classify.py:158-161` — 분류 의미론은 하나.
3. **fail-closed는 협상 대상이 아니다.** 완화 범위는 "해석 가능한 익스큐터의 본문이 해석된다"이며, "해석 불가능한 익스큐터가 통과한다"가 결코 아니다.
4. **역주소 문제는 M1에서 해소되거나 SPEC이 정직하게 DESCOPE한다.** 미검증 관례를 강행 배포하는 것은 어떤 마일스톤에서도 허용되지 않는다(REQ-EXECBODY-007/008, 본 문서 §A.3).
5. **범위 경계**: `server/web/**`·`ui/src/**` 무변경. `SPEC-COPILOT-CUECMD-001`은 번들하지 않는다(REQ-EXECBODY-016).
6. **배포 왕복 비용**: M2~M3는 실물 콘솔 접근을 필요로 한다. 접근이 세션 중 확보되지 않으면 M1까지 완료 후 progress.md에 상태를 기록하고 세션을 마무리한다(EXECREF-001의 프로브 무응답→재시도 선례와 동일한 회복 절차).

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase에서 확정)

| 태그 | 대상 | 내용 |
|---|---|---|
| `@MX:NOTE` | `console/lua/copilot_responder.lua`(익스큐터 전용 분기 근처) | 이 분기가 EXECREF-001이 발견한 `childCount: 0` 구조적 갭을 닫기 위한 것임을 표시. |
| `@MX:NOTE` | `server/safety/console.py`(신규 진입점 근처) | 익스큐터 해석이 시퀀스 본문 조회로 위임됨을 표시 — 신규 신뢰 경계가 아니라 기존 경로 재사용임을 명시. |
| `@MX:DEBT`(계승, 신규 아님) | `server/safety/console.py` `StateBodyFetcher.fetch_body` 근처 | EXECREF-001이 이미 남긴 cue-CMD DEBT 주석이 존재한다면 그대로 유지 — 본 SPEC이 새로 만들지 않는다(REQ-EXECBODY-015). |
| `@MX:WARN` + `@MX:REASON`(M1 결과가 "검증된 오프셋 관례 채택"인 경우에만) | 오프셋 관례를 사용하는 코드 지점 | 위험 지대 표시 — 관례가 깨지면 잘못된 오브젝트를 조회할 수 있음을 명시. M1이 회피 경로(ASSUMPTION-10 확인)를 채택하면 이 태그는 불필요하다. |

`@MX:ANCHOR`는 신규 추가하지 않는다 — 기존 두 앵커(gate.py:260-264, classify.py:158-161)를 소비만 한다.

## §E. 테스트 스캐폴딩 계획

- **순수 함수 우선**: `classify`/`expand`는 이미 순수 모듈이며 fetcher는 주입된다(`DictBodyFetcher` 패턴, EXECREF-001이 확립). 익스큐터 본문 해석 테스트도 인메모리 fetcher로 결정론 유지 — 스크리닝 경로에 OSC 0.
- **Lua 응답기 테스트**: 기존 Lua 테스트 하네스(있다면) 또는 라이브 프로브로 검증 — 이 프로젝트의 Lua 코드는 콘솔 내부 실행이므로 순수 유닛 테스트 범위가 제한적일 수 있음을 인지(EXECREF-001도 동일 제약을 겪었다).
- **fail-closed 개별 테스트** (병합 금지, EXECREF-001 design.md §6.2 원칙 계승).
- **관측 형상 assert**: `console.executed` 기준으로 `["Go+ Executor N"]` 정확 일치, `"SaveShow"` 부재(EXECREF-001의 관측 assert 패턴 재사용).
- **run-phase 자기 검증 커맨드(예상, run-phase에서 확정)**:
  - `.venv/bin/python -m pytest server/tests/test_safety_classify.py server/tests/test_safety_expand.py server/tests/test_safety_corpus.py server/tests/test_safety_console.py server/tests/test_safety_gate.py -q`
  - `.venv/bin/python -m pytest server/tests/test_web_panel_execute.py server/tests/test_architecture.py -q`
  - `.venv/bin/python -m pytest -q` (전체, run-phase 킥오프 기준선 대비 신규 실패 0건)
  - `grep -rn "bridge.osc\|from server.bridge" server/safety/` (기준선 대비 무변경)
  - 라이브 프로브(state/build 동사 전용, 발화 0·쓰기 0) — M1/M3 각각

## §F. 결정 기록 (재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| 후속 SPEC 채택 여부 | EXECREF-001 research.md §5.3 권고를 그대로 채택해 SPEC-COPILOT-EXECBODY-001을 계획한다. | spec.md HISTORY |
| CUECMD-001 번들 여부 | 번들하지 않는다 — 별도 계획 세션으로 이관(이번 세션 사용자 결정). | spec.md REQ-EXECBODY-016, §D |
| 역주소 문제 처리 순서 | 회피(콘솔 네이티브 해석) 우선 → 검증된 관례 차선 → DESCOPE 최후. 각주가 아니라 M1을 첫 마일스톤이자 결정 게이트로 배치. | spec.md §A/B.3, plan.md M1, §A.3 |
| ASSUMPTION 번호 | EXECREF-001 ASSUMPTION-8/9 다음 번호(10/11/12) 계승. 등재는 sync-phase 선택 항목(EXECREF-001 선례와 동일). | spec.md §C |
| frontmatter 참조 | `related_specs`(비차단) — EXECREF-001·SHOWUI-001 모두 completed이나 관례 일관성을 위해 depends_on 대신 related_specs 유지. | spec.md frontmatter |
| Tier 판단 | L — 콘솔측 Lua + 와이어 프로토콜 + Python 세이프티 게이트 + 배포 체인 + 안전-인접 설계 결정(역주소 문제)이 결합되어 EXECREF-001과 동일한 도메인에서 EXECREF-001보다 넓은 파일 표면(응답기 포함)을 다룬다. | spec.md frontmatter `tier: L` |

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> 구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다(첫 run-phase `Agent()` 스폰 전 작성). 본 절은 plan-phase 권고이며 오케스트레이터가 확정·기각한다.

### 입력 파라미터

- **tier**: L (5-artifact 세트 + progress.md)
- **scope (file count)**: 예상 8~12 파일(응답기 1, PROTOCOL.md 1, console.py 1, 테스트 4~6, plugin_pack.py 재배포 산출물 제외)
- **domain count**: **2** (Lua 콘솔 응답기 도메인 + Python `server/safety/**` 도메인) — EXECREF-001의 domain count=1과의 핵심 차이
- **file language mix**: Lua + Python 혼합. 코딩 중심(안전 로직 확장 + 콘솔 응답기 확장 + 배포 왕복)
- **concurrency benefit**: **LOW** — M1(조사)이 M2(구현) 착수 여부 자체를 게이트하는 순차 의존. M2~M4도 순차(응답기 배포 → 게이트 배선).
- **Agent Teams prereqs**: 해당 없음 (Mode 3 RETIRED)

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 조사 + 콘솔측 변경 + 배포 왕복 + 안전 로직 확장 — 단일 라인 변경이 아님 |
| 2 | background | 미선택 | 쓰기 작업 포함, M3 배포 왕복은 오케스트레이터 판단 필요 |
| 3 | agent-team | 미선택 | RETIRED (tombstone) |
| 4 | parallel | 미선택 | 도메인 2개(<3 임계 미만)이며 M1이 M2 이후 전부를 게이트하는 순차 의존 — 병렬화 이득 없음 |
| 5 | **sub-agent** | **선택** | 순차 의존 체인(M1 게이트) + 코딩 중심 + Tier L Section A-E 위임 템플릿 적용 |
| 6 | workflow | 미선택 | 8~12 파일(30 미만), 단일 균일 변환 규칙 아님(안전 의미론 + 콘솔 API 조사 포함) |

### Decision: sub-agent

### 정당화

M1(역주소 문제 조사)이 M2 이후 전체의 실행 가능성을 결정하는 순차 게이트이므로 병렬화 이득이 없다. 도메인 수 2(Lua + Python)는 Mode 4의 ≥3 임계에 미달하며, 두 도메인 모두 코딩/조사 중심으로 리서치 팬아웃에 적합하지 않다. Anthropic의 coding-task parallelism caveat상 안전한 기본값은 순차 sub-agent다. Tier L이므로 `manager-develop` 위임에는 Section A-E 전체 템플릿을 적용한다. M2~M3는 실물 콘솔 접근을 요구하므로, 오케스트레이터는 이 마일스톤 진입 전 접근 가능성을 사용자에게 확인해야 한다(AskUserQuestion, run-phase 킥오프 시점 또는 M1 완료 직후).

### 경계 사례

domain count=2는 Mode 4의 `≥3 domains` 임계 미만이지만 file count 예상치(8~12)는 Mode 4의 `≥10 files` 임계 부근이다. tie-breaker 규칙("임계 ±1에서는 단순한 모드로") + concurrency benefit=LOW(순차 의존)가 Mode 5를 가리키므로 경계 모호성 없이 해소된다.
