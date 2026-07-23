# SPEC-COPILOT-EXECBODY-001 — Plan-Phase Research

status: draft (v0.1.0, 2026-07-23). 본 문서는 SPEC-COPILOT-EXECREF-001 plan-phase 세션 중 이미 수행된 라이브 프로브 결과를 재사용한다 — 본 SPEC의 plan-phase 자체는 신규 라이브 조사를 수행하지 않았다(실물 콘솔 접근이 이번 세션에서 확보되지 않음). **구현 코드는 제안하지 않는다 — 분석 전용.**

---

## §1. 출처 — EXECREF-001 research.md §5.3

본 SPEC은 `SPEC-COPILOT-EXECREF-001/research.md` §5.3("SPEC-COPILOT-EXECBODY-001 — 익스큐터 할당 시퀀스 아이덴티티 노출", 2026-07-23 추가)에서 권고된 후속 SPEC이다. 원문 권고는 다음을 명시한다:

- **범위**: `console/lua/copilot_responder.lua`의 `build_snapshot`을 확장해, 익스큐터 노드에 대해 범용 `handle:Children()`(자식 0건 반환) 대신 익스큐터 전용 로직으로 할당된 시퀀스의 아이덴티티를 노출한다. `server/safety/console.py`를 확장해 그 결과를 본문 해석의 진입점으로 사용한다.
- **근거**: 2026-07-23 라이브 프로브(`.moai/state/verify/showui-m6-resume/5-probe-body.log`) — 익스큐터 노드는 `DataPool/Pages/<page>/<local-index>`로 해석 가능하지만(ASSUMPTION-8 확인됨) 자식을 노출하지 않는다(ASSUMPTION-9 반증됨, `childCount: 0` 4/4 샘플). 응답기가 완전히 범용이라 익스큐터별 분기가 없기 때문 — 아키텍처적 갭이지 샘플링 아티팩트가 아니다.
- **선행 조건**: `copilot_responder.lua` 변경 + `plugin_pack.py` 재배포 + Import + 라이브 재검증.
- **설계 입력 — 역주소 문제**: 익스큐터의 페이지-로컬 자식 인덱스(1, 5, 11, 91, ...)와 콘솔 발화·표시에 쓰이는 번호(101, 105, 111, 191, ..., 페이지 1에서 +100 오프셋 균일 확인)는 서로 다른 두 숫자 체계다. 이 오프셋이 다른 페이지에서도 균일한지는 미검증. 검증 없이 오프셋 관례를 하드코딩하면 REQ-EXECREF-007이 기각한 이름-파싱과 동일한 부류의 취약성(out-of-band 관례 의존, 안전-인접 코드)을 재도입하게 된다.
- **시퀀싱 메모**: `SPEC-COPILOT-CUECMD-001`과 함께 계획할 가치가 있을 수 있으나(둘 다 응답기 Lua 재배포 필요), 실제 번들 여부는 두 SPEC을 실제로 계획하는 사람에게 맡긴다.

본 SPEC은 이 원문 권고를 그대로 계획 대상으로 삼되, **번들 여부에 대해서는 명시적으로 번들하지 않기로 결정했다**(이번 세션 사용자 결정 — spec.md REQ-EXECBODY-016).

---

## §2. 고려하고 기각한 대안

### 기각 (a) — 즉시 오프셋 관례 하드코딩 (M1 조사 생략)

- **내용**: 페이지 1에서 관측된 +100 오프셋을 검증 없이 일반 규칙으로 채택해 즉시 M2로 진행.
- **기각 사유**: 미검증 out-of-band 관례에 안전-인접 코드가 의존하게 된다 — EXECREF-001 REQ-EXECREF-007이 이름-파싱을 기각한 것과 정확히 동일한 위험 부류(design.md §5.6이 이미 이 위험을 경고했다). 페이지 1 8행 외에는 관측이 전무하므로, 다른 페이지에서 오프셋이 다르거나 오프셋이 아예 존재하지 않을 가능성을 배제할 수 없다.

### 기각 (b) — 익스큐터 대신 항상 시퀀스 참조로 치환 (EXECREF-001에서 이미 기각된 대안의 재등장)

- **내용**: 패널/채팅이 애초에 `Go+ Executor N` 대신 `Go+ Sequence M`을 발화하도록 강제.
- **기각 사유**: EXECREF-001 research.md §2가 이미 기각한 대안 (b)와 동일 — 익스큐터↔시퀀스 매핑을 얻으려면 결국 같은 아이덴티티 노출 문제를 풀어야 하고, 문제를 UI 번들 형상으로 이동시킬 뿐 게이트의 근본 갭은 남는다.

### 채택 — 응답기 확장 + 회피 우선의 역주소 해소 절차

- 결함(응답기가 익스큐터 본문을 노출하지 않음)을 그 발생 지점(응답기)에서 교정한다.
- 역주소 문제는 각주가 아니라 첫 마일스톤(M1)의 결정 게이트로 다룬다 — 회피(콘솔 네이티브 해석) 우선, 검증된 관례 차선, DESCOPE 최후.

---

## §3. 핵심 참조 파일

| 파일 | 역할 |
|---|---|
| `console/lua/copilot_responder.lua` | `build_snapshot`(~429-465행) — 확장 대상. 현재 범용 `handle:Children()`만 호출. |
| `console/lua/PROTOCOL.md` | 와이어 프로토콜 문서. `PROTOCOL_VERSION`, ASSUMPTION-1~7 등재 위치. EXECREF-001 ASSUMPTION-8/9는 아직 미등재(선택 항목으로 이연됨). |
| `server/safety/console.py` | `StateBodyFetcher.fetch_body`(414-432행), `DEFAULT_BODY_PATHS`(396-400행) — 본문 해석 확장 대상. |
| `server/safety/classify.py` | `RECOGNIZED_REFERENCE_TYPES`(33행, EXECREF-001이 이미 `Executor` 포함), `_extract_reference`(117-125행). 본 SPEC은 이 파일을 전제로 소비만 한다. |
| `server/safety/expand.py` | `_evaluate`(72-125행) — 참조-타입-무관 보류 기계. 본 SPEC은 무변경으로 상속. |
| `server/safety/gate.py` | `_GateStatePort`(114-121행), 스크리닝 경로 `@MX:ANCHOR`(260-264행). |
| `server/orchestrator/tools.py` | 페이지→익스큐터 드릴다운 경로 조합(264행) — `f"{base_path}/{number}"`. 배열 인덱스가 아닌 실제 `no` 키잉 계약(164-168행)의 선례. |
| `server/rulebook/assets/v2.4.2/10_object_model.md` | 익스큐터 주소 규약(`Page <page>.<executor>`, 23-25행). |
| `server/rulebook/assets/v2.4.2/31_choreography_patterns.md` | 재생 동사(`Go+ Executor N` / `Off Executor N`). |
| `.moai/state/verify/showui-m6-resume/5-probe-body.log` | EXECREF-001의 라이브 프로브 결과 — Q1/Q2/Q3 답변, ASSUMPTION-8/9 비준 증거. |
| `.moai/state/verify/showui-m6-resume/executor-offset.jsonl` | 페이지 1의 +100 오프셋 실측 데이터(8/8행). |
| `.moai/state/verify/probe_executor_body.py` | EXECREF-001이 작성한 읽기 전용 프로브 스크립트 — M1이 재사용/확장할 수 있는 패턴. |
| `SPEC-COPILOT-EXECREF-001/spec.md` `REQ-EXECREF-007` | 이름-파싱 기각 근거 — 본 SPEC의 역주소 문제 논증이 병렬로 삼는 선례. |
| `SPEC-COPILOT-EXECREF-001/design.md` §5.6 | "왜 게이트가 콘솔 주소→로컬 인덱스 역매핑을 시도하지 않는가" — 본 SPEC에 설계 입력을 인계한 절. |

---

## §4. 알려진 미결 지점 (M1이 조사할 사항)

1. **콘솔 네이티브 주소 해석 API 존재 여부** (ASSUMPTION-10) — grandMA3 Lua API 문서·룰북에 커맨드-라인 문자열을 핸들로 직접 해석하는 함수가 문서화되어 있는지 확인되지 않았다. 본 plan-phase 세션은 이를 확인할 실물 콘솔 접근이 없었다.
2. **오프셋 관례의 다중-페이지 안정성** (ASSUMPTION-11) — 페이지 1 외 검증 없음.
3. **익스큐터→시퀀스 프로퍼티 접근성의 구체적 API 형태** (ASSUMPTION-12) — `Children()`이 빈 배열을 반환한다는 것은 확인되었으나, 그 대안이 되는 접근자(프로퍼티명, getter 함수 등)는 아직 실측되지 않았다.

이 세 미결 지점은 spec.md §C에 ASSUMPTION-10/11/12로 번호가 부여되었으며, plan.md M1이 이들을 조사·해소하는 첫 마일스톤이다.

---

## §5. SPEC-COPILOT-CUECMD-001과의 관계 (번들하지 않음, 참고용 기록)

`SPEC-COPILOT-CUECMD-001`(큐 커맨드 프로퍼티 스크리닝)은 EXECREF-001 research.md §5.3이 함께 권고한 별도 SPEC이며, 본 SPEC과 마찬가지로 응답기 Lua 재배포를 필요로 한다. 이번 세션의 사용자 결정에 따라 두 SPEC은 **번들하지 않는다** — CUECMD-001은 별도 계획 세션의 범위다. 두 SPEC이 동일한 배포 왕복(Lua 편집 → `plugin_pack.py` → Import → 라이브 재검증)을 필요로 한다는 사실은 향후 CUECMD-001을 계획하는 사람이 시퀀싱 이점을 재검토할 수 있도록 여기 기록만 남긴다 — 본 SPEC의 계획 범위나 마일스톤 구조에는 영향을 주지 않는다.
