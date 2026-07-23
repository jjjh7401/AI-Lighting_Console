# SPEC-COPILOT-EXECREF-001 — 설계 명세 (design)

status: draft (v0.2.0, 2026-07-23) · Tier L. 본 문서는 **안전 경계를 완화하는 변경**의 설계 계약이다. 중심은 §4 false-negative 검토이며, §5는 2026-07-23 라이브 프로브로 해소되었다 — S2(익스큐터 본문 해석)는 구현하지 않기로 확정되었다(YAGNI, Q2 결정적 부정).

---

## §1. 설계 의도

한 문장: **해석 가능한 익스큐터를 해석되게 한다.** 그 이상도 이하도 아니다.

- **이상이 아님**: 해석 불가능한 익스큐터는 여전히 보류된다. 새 예외·carve-out·우회는 없다.
- **이하가 아님**: 참조가 해석되면 기존 expand-or-hold 기계 **전체**가 그 위에서 돈다 — 별도 익스큐터 전용 경로가 아니라 같은 기계 안이다.

설계의 형태는 "새 방어를 만든다"가 아니라 "**기존 방어 안으로 참조를 밀어 넣는다**"이다. 이 형태 선택이 §4의 안전 논증 전체를 가능하게 한다.

---

## §2. 변경 표면 (두 곳, 그 이상 없음)

| # | 표면 | 변경 | 성격 |
|---|---|---|---|
| S1 | `server/safety/classify.py:33` `RECOGNIZED_REFERENCE_TYPES` | `"Executor"` 추가 | 폐쇄 집합의 의도적 개정 |
| S2 | `server/safety/console.py` `StateBodyFetcher` / `DEFAULT_BODY_PATHS` | 익스큐터 본문 해석 경로 추가 (형상 변경 가능 — §5) | 게이트-감사 `state_port` seam 위에서만 |

`expand.py`, `gate.py`, `ruleset.py`, `blacklist.yaml`, `server/web/**`, `ui/src/**`, `console/lua/**`는 **무변경**이다. 특히:

- `expand.py` 무변경이 §4 논증의 전제다 — 보류 기계를 건드리지 않으므로 보류 기계의 성질이 보존됨이 자명해진다.
- `blacklist.yaml` 무변경 — `invoking_verbs`는 이미 `Go`/`Go+`/`Go-`를 포함하며 익스큐터 인식과 무관하다.

### §2.1 S1의 단독 효과 = 무행동 변화 (fail-closed 방향)

S1만 적용하고 S2를 적용하지 않으면:

- 이전: `reference=None` → `_hold("unverifiable reference: no recognizable target object")` (expand.py:83)
- 이후: `reference="Executor 201"` → `fetch_body` → 템플릿 부재 → `BodyUnavailable("no body path mapping for 'Executor 201'")` (console.py:418) → `_hold("unverifiable reference 'Executor 201': ...")` (expand.py:104)

**두 경우 모두 `hold=True, risky=False`.** 게이트 결과는 동일하고 보류 사유 문자열만 바뀐다. 이는 M1을 독립적으로 안전하게 출하할 수 있게 하는 성질이며 AC-EXECREF-008이 이를 기계 검증한다.

---

## §3. 데이터 흐름 (변경 후)

```
Go+ Executor 201
  │
  ├─ grammar.validate                              (무변경)
  ├─ classify_command                              (S1: Executor 인식)
  │     └─ category="invoking", reference="Executor 201"
  │
  ├─ evaluate_reference  ─────────────────── expand.py 무변경
  │     ├─ reference is None?            → no
  │     ├─ cycle?                        → visited 검사        (expand.py:85-86)
  │     ├─ depth > 3?                    → 상한 검사           (expand.py:87-88)
  │     ├─ fetch_body("Executor 201")    → S2: state_port 경유 (console.py)
  │     │     └─ 실패/빈 본문 → BodyUnavailable → _hold        (expand.py:101-104)
  │     └─ 본문 각 라인
  │           ├─ grammar 실패            → _hold               (expand.py:107-109)
  │           ├─ blacklisted             → _hold(risky=True)   (expand.py:110-112)
  │           └─ invoking                → 재귀 _evaluate      (expand.py:113-124)
  │
  └─ hold=False → 승인 없이 clearance → 송신 1회 + 감사 1건
```

본문 조회는 `gate.state_port.query_state`(bootstrap.py:162 배선, gate.py:114-121 `_GateStatePort`)로 흐른다 — `get_rig_context`와 `build_catalog`가 쓰는 **동일한 감사되는 chokepoint**다. 신규 콘솔 경로도 신규 OSC 표면도 없다.

---

## §4. False-Negative 검토 (본 문서의 중심)

익스큐터 본문에 담길 수 있는 것을 열거하고, 각각이 여전히 잡히는지 증명한다.

### §4.0 열거

| # | 익스큐터 본문에 존재할 수 있는 것 | 위험 |
|---|---|---|
| 1 | 할당된 시퀀스의 큐들 | 큐 이름이 블랙리스트 키워드일 수 있음 |
| 2 | 큐의 CMD(Command) 프로퍼티 | **와이어에 실리지 않음 — §4.2** |
| 3 | 큐 CMD 안의 매크로 호출 (`Go Macro 9`, Macro 9가 파괴적) | 간접 파괴 |
| 4 | 중첩 익스큐터 참조 (큐 CMD가 `Go+ Executor M`) | 익스큐터→익스큐터 재귀 |
| 5 | 빈/미할당 익스큐터 (시퀀스 없음) | 해석 불가 |
| 6 | 읽을 수 없거나 사라진 본문 (시퀀스 삭제, 질의 타임아웃) | 해석 불가 |

### §4.1 케이스 1 — 큐 이름

`fetch_body`가 `children[*].name`을 본문 라인으로 만들고(console.py:426-432), `_evaluate`가 각 라인을 `grammar.validate` → `classify_command`에 통과시킨다(expand.py:106-112). 이름이 블랙리스트 커맨드로 파싱되면 `_hold(risky=True)`. **Sequence 참조와 정확히 동일한 처리**이며, 처리 코드가 동일하다.

### §4.2 케이스 2 — 큐 CMD 프로퍼티 (⚠️ 기존 갭, 본 SPEC이 닫지 않음)

**사실**: 응답기는 자식당 `{name, class, i}`만 보낸다(`copilot_responder.lua:456`). CMD 프로퍼티는 전송되지 않는다. 따라서 `fetch_body`가 만드는 본문 라인은 큐 **이름**이지 큐 **커맨드**가 아니다.

**동등성 논증 (개선이 아니라 패리티)**:

1. 익스큐터의 본문은 **할당된 시퀀스의 같은 큐 집합**이다.
2. 그 큐 집합은 **같은 리더**(`StateBodyFetcher`)로 읽힌다.
3. 따라서 익스큐터 참조가 보는 것 = `Go+ Sequence N`이 이미 보는 것.
4. Executor 추가는 cue-CMD 갭을 **만들지 않고**, 종류상 **악화시키지 않는다**.

**단, 확대는 존재한다 (얼버무리지 않음)**:

- 이전: 익스큐터 대상 invoking 커맨드는 **무조건** 보류 → 본문 조회에 **도달하지 않음** → 사람이 승인 카드에서 커맨드 텍스트를 보고 판단.
- 이후: 본문 조회에 **도달**하고, 본문이 무해해 보이면 사람 없이 통과.
- 따라서 **본문 조회에 도달하는 커맨드 집합이 넓어진다.** 넓어진 집합에 대해 큐 CMD는 여전히 보이지 않으므로, cue-CMD 갭의 **노출 표면적**이 커진다.

**이 확대를 수용하는 근거**: (a) 확대된 집합은 `Go+ Sequence N`이 이미 통과시키던 것과 동일한 오브젝트를 가리킨다 — 익스큐터는 시퀀스 재생 핸들이다. (b) 대안은 승인-매-누름(기각 (a)) 또는 시퀀스 치환(기각 (b))이며, 후자는 **같은 갭을 가진 경로로 우회**할 뿐이다. (c) 갭 자체는 응답기 변경 없이 닫을 수 없고, 사용자가 본 SPEC의 범위를 `server/safety/**`로 결정했다.

**의무**: 이 갭을 코드에 `@MX:DEBT`로 고정하고(plan.md §D), 후속 SPEC 권고 `SPEC-COPILOT-CUECMD-001`로 research.md §5.3에 명명한다. **게이트가 큐 커맨드를 스크리닝한다고 주장하지 않는다.**

### §4.3 케이스 3 — 큐 CMD 안의 매크로 호출

본문 라인이 `Go Macro 9`로 읽히면 `classify_command`가 `category="invoking"`, `reference="Macro 9"`를 반환하고 `_evaluate`가 `depth+1`로 재귀한다(expand.py:113-124). Macro 9의 본문이 파괴적이면 `_hold(risky=True)`(expand.py:110-112).

**단서**: 이 방어는 케이스 2의 갭에 종속된다 — 큐의 CMD가 와이어에 실리지 않으므로, CMD가 `Go Macro 9`인 큐는 그 이름이 다른 한 이 경로에 도달하지 않는다. 이는 **모든 참조 타입에 이미 존재하는 조건**이며 Executor가 새로 만드는 것이 아니다(§4.2 동등성).

### §4.4 케이스 4 — 중첩 익스큐터 재귀

`visited` 집합이 `key = reference.lower()`로 순환을 탐지한다(expand.py:84-86, 105). 익스큐터 참조 문자열도 동일하게 키잉되므로 `Executor 201 → Executor 202 → Executor 201`은 `_hold("reference cycle detected at ...")`로 잡힌다. 깊이 4 이상 체인은 `MAX_EXPANSION_DEPTH = 3`(expand.py:23-24, 87-88)이 `_hold`시킨다.

두 방어 모두 **참조 타입 무관**이므로 Executor가 자동 상속한다. AC-EXECREF-004/005가 개별 검증한다.

### §4.5 케이스 5 — 빈/미할당 익스큐터

`fetch_body`는 `children`이 리스트가 아니거나 비어 있으면 `BodyUnavailable("empty or missing body for ...")`를 던진다(console.py:423-425) → `_hold`(expand.py:101-104). 시퀀스가 할당되지 않은 익스큐터는 여기에 해당한다.

**이것이 fail-closed 계약의 핵심 지점이다**: 빈 본문을 "위험 없음"으로 해석하는 것은 명백한 FN이 되므로 절대 허용하지 않는다. AC-EXECREF-003a가 검증한다.

### §4.6 케이스 6 — 읽을 수 없는 본문

`self._query(...)`가 예외를 던지면 `BodyUnavailable("state query failed for ...")`(console.py:419-422) → `_hold`. 상태 질의 타임아웃은 `StateQueryError`(console.py:381-383)로 올라오며 같은 경로를 탄다. 자식에 이름이 없거나 공백이면 `BodyUnavailable("unreadable body line in ...")`(console.py:428-430).

AC-EXECREF-003b/003c가 각각 검증한다(단일 AC로 병합하지 않는다 — 실패 모드가 다르다).

### §4.7 부수 관찰 — `SaveShow`가 사라지는 기제 (주석/코드 불일치 기록)

`gate.py:325-329`의 백업 블록은 `if held:`(gate.py:290) 안에 있다. 주석은 "only the RISKY path backs up"이라 쓰여 있으나 실제 조건은 **보류 여부**이며, 익스큐터 참조 보류는 `risky=False`다(expand.py:83, 기본 인자).

따라서 `SaveShow`는 "위험하다고 분류되어서"가 아니라 "보류되었기 때문에" 발화한다. 보류가 사라지면 승인 카드와 `SaveShow`가 **하나의 수정으로** 동시에 사라진다.

**주석 수정은 본 SPEC 범위 밖이다**(scope discipline — 안전 모듈의 문서 문자열 변경은 별개 판단). 여기에 기록만 한다.

### §4.8 요약 — 어떤 방어가 어디서 오는가

| 케이스 | 방어 출처 | 신규 코드 필요? |
|---|---|---|
| 1 큐 이름 | 기존 `classify_command` 재귀 (expand.py:110-112) | 아니오 |
| 2 큐 CMD | **없음 — 기존 갭, 모든 타입 공통** | 아니오(범위 밖) |
| 3 매크로 호출 | 기존 재귀 (expand.py:113-124) | 아니오 |
| 4 중첩/순환 | 기존 순환·깊이 (expand.py:85-88) | 아니오 |
| 5 빈 본문 | 기존 `BodyUnavailable` (console.py:423-425) | 아니오 |
| 6 조회 실패 | 기존 `BodyUnavailable` (console.py:419-422, 428-430) | 아니오 |

**신규 방어 코드는 0줄이다.** 신규 코드가 하는 일은 참조를 기존 기계에 **연결**하는 것뿐이며, 그래서 AC가 "각 방어가 익스큐터에 대해서도 작동하는가"를 개별 검증한다 — 연결이 방어를 우회하도록 잘못 구현될 가능성이 유일한 위험이기 때문이다.

---

## §5. 익스큐터 본문 해석 경로 — 라이브 프로브 실측 결과 (해소됨, 2026-07-23)

**이 절은 2026-07-23 라이브 프로브로 해소되었다.** 결론: S2(익스큐터 본문 해석)는 구현하지 않는다 — Q2가 결정적으로 부정으로 답했기 때문이다. 근거: `.moai/state/verify/showui-m6-resume/5-probe-body.log`(실제 onPC 2.4.2, `state` 동사 전용 읽기 전용 프로브, 발화 0·쓰기 0).

### §5.1 프로브 결과 — 세 질문의 실측 답

| 질문 | 실측 답 | 근거 |
|---|---|---|
| **Q1** `DataPool/Pages/<page>/<exec>`가 익스큐터 노드로 해석되는가? | **예.** `DataPool/Pages/1/1`, `/5`, `/11`, `/91`이 전부 `ok: true, class: "Executor"`를 반환했다. | 5-probe-body.log |
| **Q1 부속 발견** | 해석에 쓰인 `<exec>` 성분은 페이지 목록이 보고하는 **페이지-로컬 자식 인덱스**(1, 5, 11, 91, 92, 93, 95, 101)이며, 물리 콘솔·발화 커맨드에 쓰이는 **더 큰 번호**(101, 105, 111, 191, 192, 193, 195, 201 — 별도 확정: `.moai/state/verify/showui-m6-resume/executor-offset.jsonl`, 페이지 1 전수 +100 균일, 8/8행)와 **다른 두 숫자**다. 같은 버튼을 가리키는 서로 다른 두 개의 번호다. | executor-offset.jsonl (선행 오프셋 프로브) |
| **Q2** 익스큐터 노드에 자식(할당 시퀀스의 큐)이 있는가? | **아니오 — 결정적.** 샘플링한 익스큐터 4개(1, 5, 11, 91) 전부 `"childCount": 0`. | 5-probe-body.log |
| **Q2 근본 원인** | `console/lua/copilot_responder.lua` `build_snapshot`(~429-465행)을 읽어 확인: 응답기는 완전히 범용이다 — 해석된 경로에서 `handle:Children()`을 호출할 뿐, 익스큐터 전용 로직이 없다. MA3는 이 API로 익스큐터의 시퀀스 할당을 자식으로 노출하지 않는다 — 할당은 부모-자식 포함 관계가 아니라 프로퍼티/포인터 관계로 보인다. 응답기 코드가 익스큐터별로 분기하지 않으므로 이는 아키텍처적 사실이지 샘플링 아티팩트가 아니다 — 나머지 4개(92, 93, 95, 101)가 다를 이유가 없다. | copilot_responder.lua ~429-465행 |
| **Q3** 큐가 커맨드를 나르는가? | **아니오, 이미 예상된 대로 확인됨.** `DataPool/Sequences/1/1`, `/1/2`(기존 신뢰 본문 소스)는 `name`/`class`/`i`(+ 중첩 `Part` 자식)만 반환하고 커맨드/CMD 필드는 결코 반환하지 않는다. §4.2가 이미 문서화한 기존 갭과 정확히 일치한다 — 새로운 발견이 아니며 모든 참조 타입에 균일하게 적용된다. | 5-probe-body.log |

### §5.2 결론 — S2는 구현하지 않는다 (YAGNI 판단)

Q2가 무조건 부정이라는 것은 **`server/safety/**` 범위 안에서 S2가 어떤 실질적 효과도 낼 수 없다**는 뜻이다 — 페이지 성분 주소를 아무리 영리하게 풀어도 마찬가지다. 그럼에도 본문 조회 경로를 만든다면, 콘솔에 보이는 발화 번호(예: 201)를 `(page, local_index)`(예: `1, 101`)로 되돌리는 역매핑이 추가로 필요할 것이다 — 그리고 그 역매핑은 페이지 1을 넘어서는 검증이 없고, REQ-EXECREF-007이 이미 같은 이유(취약·미검증·안전-인접)로 기각한 이름-파싱 접근과 구조적으로 동일한 부류의 out-of-band 관례 추측이다(§5.6). 어느 경로든 결과는 `children: []` → `BodyUnavailable` → `_hold`로 동일하므로, S2를 구현하는 것은 행동 변화 없이 안전-critical 코드에 새로운 미검증 주소 가정 하나를 추가하는 것뿐이다. **S2 구현을 권고하지 않는다.** 이것은 지름길이 아니라 정당한 YAGNI 판단이다.

이 결과는 §5.4가 예견했던 "Q1 예 / Q2 아니오(자식 없음)" 분기와 정확히 일치한다(당시에는 가설이었으나 이번 실측으로 확정됨). §2.1의 "S1 단독" 분석이 그대로 적용된다: `hold=True, risky=False` 불변 — 보류 사유 문자열만 "unverifiable reference: no recognizable target object"에서 "no body path mapping for 'Executor N'"으로 바뀐다. SPEC이 명시한 목표(평범한 익스큐터 타일의 single-press 마찰 제거)는 **이번 버전에서 달성되지 않는다.**

### §5.3 페이지 성분 해석 후보 — Q2 부정으로 무의미해짐 (moot)

원래 이 절이 열거했던 세 후보 — (a) 상태 질의로 현재 페이지 확인, (b) 전 페이지 순회, (c) 페이지 무관 전역 번호 — 는 **Q2가 부정으로 답한 이상 어느 것을 채택하든 결과가 같으므로(`children: []`) 선택 자체가 무의미(moot)해졌다.** S2를 구현하지 않기로 했으므로 이 세 후보 중 어느 것도 채택되지 않는다.

다만 §5.1에서 확인된 **로컬 인덱스 vs 콘솔 주소의 구분**(페이지-로컬 자식 인덱스 1/5/11/91... vs 발화·물리 콘솔에 쓰이는 +100 오프셋 번호 101/105/111/191...)은 후속 SPEC을 위한 설계 입력으로 남긴다 — 이 구분을 모르면 후속 SPEC이 같은 주소 혼동을 반복할 것이다. research.md §5.3의 `SPEC-COPILOT-EXECBODY-001` 권고에 이 발견을 인계한다.

### §5.4 Fail-closed 폴백 — 실현된 결과 (더 이상 가설이 아님)

**본 SPEC이 §5의 열린 슬롯을 열었을 때 서술한 폴백이 실제로 실현된 결과다.** 익스큐터 본문을 읽을 수 없으므로 `_hold`한다 — 즉 오늘의 동작이 그대로 유지된다.

이 폴백은 다음을 실측으로 확정한다:

> **본 SPEC의 실제 결과는 "마찰이 줄지 않음"이다 — "미검증 커맨드가 통과함"이 아니다.** 이는 사전에 규정한 최악 경계 안에 정확히 위치한다.

Q1/Q2가 부정적으로 답해 익스큐터 본문이 구조적으로 해석 불가능함이 실측으로 확인되었으므로, S1(classify 추가)만 남고 §2.1의 무행동 변화 상태로 귀결된다 — 보류 사유 문자열만 바뀐 채 마찰은 그대로다. **사용자 결정(AskUserQuestion, 2026-07-23)**: 이 상태를 정직한 부분 성공으로 출하한다 — S1만 배포하고 S2는 완전히 이연한다. 대안(응답기 확장 = cue-CMD 후속 SPEC과 병합 가능)은 후속 SPEC `SPEC-COPILOT-EXECBODY-001`로 명명해 권고한다(research.md §5.3). **부분 성공을 성공으로 위장하지 않는다** — SPEC의 목표(마찰 제거)가 달성되지 않았다는 사실은 spec.md §A, acceptance.md §A/§C 전역에 명시적으로 기록된다.

### §5.5 ASSUMPTION 비준 (실측 완료, 2026-07-23)

`console/lua/PROTOCOL.md` §6의 ASSUMPTION-1~7 다음 번호를 사용한다:

- **ASSUMPTION-8 (익스큐터 노드 경로)**: 익스큐터 노드는 `DataPool/Pages/<page>/<executor>` 형상의 오브젝트-트리 경로로 상태 질의에 해석된다. **상태: 확인됨(TRUE) — 단, 로컬-인덱스 단서 있음.** 해석에 쓰이는 `<executor>` 성분은 콘솔에 보이는/발화에 쓰이는 번호가 아니라 페이지-로컬 자식 인덱스다(§5.1 Q1 부속 발견). 검증 수단: `probe_executor_body.py`, 2026-07-23 실행, `.moai/state/verify/showui-m6-resume/5-probe-body.log`.
- **ASSUMPTION-9 (익스큐터 본문 내용)**: 익스큐터 노드의 자식은 할당된 시퀀스의 큐이며, 따라서 `Go+ Sequence N`이 이미 조회하는 것과 동일한 오브젝트 집합이다. **상태: 반증됨(FALSE).** 샘플링한 4개 익스큐터 전부 `childCount: 0` — 익스큐터 노드는 자식을 노출하지 않는다(응답기가 범용 `handle:Children()`을 호출할 뿐 익스큐터 전용 확장이 없기 때문 — §5.1 Q2 근본 원인). 검증 수단: 동일 프로브, 2026-07-23, 동일 로그.

비준 기록은 `progress.md` §E.2에도 남긴다. `PROTOCOL.md` §6 등재는 본 SPEC 범위(`server/safety/**`) 밖이므로 여전히 **sync-phase 선택 항목**이다(plan.md §F 참조) — 승인 없이 수행하지 않는다.

### §5.6 왜 게이트가 콘솔 주소→로컬 인덱스 역매핑을 시도하지 않는가

§5.2에서 언급한 역매핑(콘솔 발화 번호 → `(page, local_index)`)을 안전 게이트 코드에 구현하지 않는 근거는 REQ-EXECREF-007이 이름-파싱 접근을 기각한 근거와 병렬이다:

1. **미검증 범위** — 페이지 1에서만 +100 오프셋이 균일함이 확인되었다(executor-offset.jsonl, 8/8행). 다른 페이지에서도 동일한 오프셋 관례가 성립한다는 보장이 없다.
2. **out-of-band 관례 의존** — 오프셋이 페이지마다 다르거나 콘솔 설정에 따라 달라질 수 있는 관례라면, 하드코딩된 역매핑은 조용히 잘못된 오브젝트를 가리키는 안전-critical 실패 모드를 만든다. 이는 REQ-EXECREF-007이 이름-파싱을 기각한 것과 동일한 부류의 취약성이다 — 검증되지 않은 부가 규약에 안전 로직을 얹는 것.
3. **효과 없음** — Q2가 부정인 이상, 역매핑을 정확히 풀어도 `children: []`은 변하지 않는다. 위험을 감수할 이유가 없다.

따라서 안전 게이트는 콘솔 주소→로컬 인덱스 역매핑을 시도하지 않는다. 이 발견은 후속 SPEC `SPEC-COPILOT-EXECBODY-001`(research.md §5.3)의 설계 입력으로 인계된다 — 그 SPEC이 응답기 확장을 통해 익스큐터의 할당 시퀀스 아이덴티티를 직접 노출하면, 역매핑 문제 자체가 사라진다.

---

## §6. 테스트 설계 방향

### §6.1 참조 타입 축의 동적 순회 (REQ-EXECREF-011)

현재 `_invoking_commands()`(test_safety_corpus.py:86-92)는 동사 축만 동적이고 참조 타입은 `Macro` 하드코딩이다. `_SCENARIOS`(95-110)의 본문 키도 `"Macro 9"`/`"Plugin 9"` 고정이다.

설계 방향: 코퍼스가 `classify.RECOGNIZED_REFERENCE_TYPES`를 import하여 참조 타입을 **parametrize 축**으로 삼고, `_SCENARIOS`의 본문 사전을 타입별로 생성한다. 그러면 향후 어떤 참조 타입이 추가되어도 코퍼스가 자동 확장된다 — 이것이 "하드코딩 추가가 아니라 폐쇄 집합 순회"의 의미다.

**비용 고려**: 케이스 수가 타입 수만큼 곱해진다(현재 10 동사 × 4 시나리오 = 40 → 타입 4종이면 160). 실행 시간이 문제되면 타입 축 × 시나리오 축을 유지하되 동사 축을 대표 동사로 축소하는 것이 아니라, **동사 축을 유지하고 시나리오를 타입별로 나누는** 방향을 우선 검토한다 — 동사 축 축소는 REQ-MVP-017의 "ALL invoking_verbs entries" 계약을 깨뜨린다.

`bare_object_forms` 축(`Macro <n>` / `Plugin <n>`)은 참조 타입 축과 무관하게 현재 형태를 유지한다.

### §6.2 fail-closed 실패 모드는 개별 AC

빈 본문 / 조회 실패 / 파싱 불가는 서로 다른 코드 경로(console.py:423-425 / 419-422 / 428-430)를 타므로 **하나의 AC로 병합하지 않는다**. 병합하면 한 경로가 회귀해도 다른 경로가 테스트를 통과시킨다.

### §6.3 관측 형상은 SHOWUI M3 증적을 미러

AC-EXECREF-001은 기록된 콘솔 송신에 대해 assert한다: `sent == ["Go+ Executor 201"]`이며 `["SaveShow", "Go+ Executor 201"]`이 **아니다**. 이는 SHOWUI M3가 실제 UDP 트랜스포트에서 측정한 형상의 직접 교정이므로, 같은 형상으로 assert해야 회귀가 즉시 드러난다.

### §6.4 회귀 방어선

`test_safety_gate.py`, `test_web_panel_execute.py`, `test_safety_classify.py`, `test_safety_expand.py`, `test_safety_corpus.py`, `test_safety_ruleset.py`, `test_safety_console.py`, `test_architecture.py`. 안전 모듈 변경이므로 이들의 그린은 협상 대상이 아니다.

---

## §7. 반-패턴 (이 SPEC 근처에서 발생하는 유혹)

| # | 유혹 | 왜 금지인가 |
|---|---|---|
| AP-1 | "패널 커맨드는 이미 안전하니 expansion을 건너뛰자" | 이름만 다른 제2 스크리닝. gate.py:260-264 `@MX:ANCHOR` + SHOWUI REQ-SHOWUI-007 |
| AP-2 | 익스큐터 전용 분류 분기를 `classify_command` 밖에 둠 | classify.py:158-161 `@MX:ANCHOR`. REQ-MVP-013/014 FN=0이 단일 매칭 의미론 위에 있음 |
| AP-3 | 익스큐터 `name`에서 시퀀스를 파싱 | rename에 깨짐. 기각한 대안 (b)의 재등장. REQ-EXECREF-007 |
| AP-4 | 빈 본문을 "위험 없음"으로 통과 | 명백한 FN. REQ-EXECREF-008 |
| AP-5 | 배열 인덱스로 익스큐터 키잉 | 번호가 비연속(1,5,11,91,...). tools.py:164-168 계약 |
| AP-6 | "게이트가 큐를 검증한다"는 서술 | 하지 않는다. REQ-EXECREF-012 |
| AP-7 | 프로브 없이 §5.3 후보 중 하나를 임의 채택 | 추측. plan-audit 이전에 프로브 결과를 접어야 함 |
| AP-8 | 부분 성공(§5.4 폴백 상태)을 성공으로 보고 | 마찰 미감소는 목표 미달이며 그렇게 보고해야 함 |

---

## §8. 교차 참조

- `spec.md` §A(결함 연쇄·cue-CMD 고지), §B(요구사항), §D(제외 범위)
- `research.md` §2(기각 대안), §3(기존 기계), §4(미결 지점), §5(cue-CMD 갭 + 후속 SPEC 권고), §6(코퍼스 정정)
- `plan.md` §B(마일스톤), §D(@MX:DEBT 대상), §F(결정 기록)
- `acceptance.md` §C(AC 표)
- `SPEC-COPILOT-SHOWUI-001/progress.md` §E.2 199-219행 — 결함 발견 원 기록
