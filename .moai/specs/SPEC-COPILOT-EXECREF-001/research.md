# SPEC-COPILOT-EXECREF-001 — Plan-Phase Research: 안전 게이트의 Executor 참조 인식

status: draft (v0.2.0, 2026-07-23). 모든 발견은 file:line 근거를 갖는다. **구현 코드는 제안하지 않는다 — 분석 전용.** 2026-07-23 라이브 프로브 결과가 §5.3에 후속 SPEC 권고로 추가되었다.

---

## §1. 결함의 코드 연쇄 (검증됨)

| 링크 | 위치 | 사실 |
|---|---|---|
| ① invoking 분류 | `server/safety/blacklist.yaml:22-25` | `Go`, `Go+`, `Go-`가 `invoking_verbs`에 있다(`Goto`/`On`/`Off`/`Toggle`/`Temp`/`Flash`/`Call`과 함께). `classify.py:222-229`가 이 동사 집합에 매치되면 `category="invoking"` + `reference=_extract_reference(...)`를 반환한다. |
| ② 참조 미인식 | `server/safety/classify.py:33` | `RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence")` — `Executor` 부재. `_extract_reference`(117-125)가 `Go+ Executor 191`에서 `None`을 반환. |
| ③ 보류 | `server/safety/expand.py:82-83` | `reference is None` → `_hold("unverifiable reference: no recognizable target object")`. |
| ④ 백업 발화 | `server/safety/gate.py:59`, `gate.py:325-329` | `BACKUP_COMMAND = "SaveShow"`. `_backup.before_risky_execution()`이 승인 직후 호출된다. |

**실측 (SPEC-COPILOT-SHOWUI-001 M3, 실제 UDP 트랜스포트)**: 익스큐터 타일 1회 누름 → `exec_commands == ["SaveShow", "Go+ Executor 201"]`. `Go+ Sequence 41`은 참조 해석 성공 → 승인 없이 통과.

### §1.1 정밀 관찰 — 백업은 `risky`가 아니라 `held`에 걸린다

`gate.py:325-329`:

```
            # Backup rule ③ (REQ-MVP-017): only the RISKY path backs up.
            if self._backup is not None:
                try:
                    self._backup.before_risky_execution()
```

이 블록은 `if held:`(gate.py:290) 블록 **안**에 있다. 주석은 "RISKY"라 쓰여 있으나 실제 게이팅 조건은 **보류 여부**다. 익스큐터 참조 보류는 `_hold(..., risky=False)`(expand.py:83 — `risky` 인자 미지정, 기본 `False`)이므로 위험으로 분류되지 않았음에도 `SaveShow`가 발화한다.

**함의**: 보류를 제거하면 승인 카드와 `SaveShow`가 동시에 사라진다. 두 개의 별도 수정이 아니라 하나의 수정이다.

**주의**: 이 관찰은 주석과 코드의 불일치를 드러내지만, 주석 수정은 본 SPEC의 범위가 아니다(scope discipline). design.md §4.7에 기록만 한다.

---

## §2. 고려하고 기각한 대안 (사람 결정 — 재논의 금지)

출처: `SPEC-COPILOT-SHOWUI-001/progress.md` §E.2 "M3에서 발견한 사항 — 사람 결정 필요 (승인 게이트 빈도)"(199-219행)에서 M3가 결함과 선택지를 보고했고, 사용자가 **게이트측 Executor 인식**을 채택했다.

### 기각 (a) — 승인-매-누름을 수용하고 design.md를 개정

- **내용**: 익스큐터 타일이 누를 때마다 승인 카드를 띄우는 것을 정상 동작으로 인정하고, SHOWUI-001 design.md §5의 "일반 타일은 single-press" 약속을 철회.
- **기각 사유**: 패널의 핵심 가치를 잃는다. SHOWUI-001의 전제(interview R1)는 "한 번의 시선과 한 번의 누름"이었고, `spec.md` §A는 광역 커맨드를 금지하는 근거로 "쇼 진행 중 블랙아웃 순간에 승인 카드가 뜨는 사고를 원천 배제"를 든다. 승인-매-누름은 그 사고를 상시화한다.

### 기각 (b) — 익스큐터 대신 시퀀스 참조로 치환

- **내용**: 패널이 `Go+ Executor 201` 대신 `Go+ Sequence 71`을 발화하도록 번들 형상을 바꾼다(시퀀스는 이미 해석되므로 승인 없이 통과).
- **기각 사유 1 (등가성 미검증)**: `Go+ Sequence N`과 `Go+ Executor M`이 동일한 재생을 일으킨다는 보장이 없다. MA3에서 시퀀스는 데이터이고 익스큐터는 재생 핸들이며, 같은 시퀀스가 여러 익스큐터에 할당될 수 있다.
- **기각 사유 2 (rename 취약)**: 익스큐터↔시퀀스 매핑을 익스큐터의 표시 이름에서 얻는 경로는 rename에 깨진다(§4 참조). 이는 REQ-EXECREF-007이 금지하는 것과 같은 취약성이다.
- **기각 사유 3 (문제 이동)**: 게이트의 인식 범위 결함을 UI 번들 형상으로 우회하는 것이므로, 채팅이 만든 `Go+ Executor N`은 여전히 보류된다.

### 채택 — 게이트측 Executor 인식

- 결함을 그 발생 지점에서 교정한다. 채팅 경로와 패널 경로가 동시에 이득을 본다.
- 안전 경계를 완화하므로 false-negative 검토가 필수 부수 의무가 된다(design.md §4).

---

## §3. 기존 기계가 이미 커버하는 것 (참조-타입-무관)

`expand.py`의 보류 로직은 전부 참조 문자열에 대해 **타입-무관**하게 작동한다. 익스큐터가 인식되는 순간 아래를 전부 자동 상속한다:

| 위험 | 방어 기제 | 위치 |
|---|---|---|
| 익스큐터→익스큐터 무한 재귀 | `visited` 집합 기반 순환 탐지 | `expand.py:84-86` |
| 깊은 참조 체인 | `MAX_EXPANSION_DEPTH = 3` 상한 | `expand.py:23-24, 87-88` |
| 본문에 블랙리스트 커맨드 | `finding.category == "blacklisted"` → `_hold(risky=True)` | `expand.py:110-112` |
| 본문 조회 실패/타임아웃 | `BodyUnavailable` → `_hold` | `expand.py:101-104` |
| 파싱 불가 본문 라인 | `grammar.ok is False` → `_hold` | `expand.py:107-109` |
| 본문 안의 중첩 invoking | 재귀 `_evaluate(depth+1)` | `expand.py:113-124` |

**이것이 이 SPEC의 안전 논증의 핵심이다**: 새 코드가 새 방어를 만드는 게 아니라, 기존 방어 안으로 참조를 **밀어 넣는** 것이다. 위험은 "익스큐터가 방어를 우회한다"가 아니라 "익스큐터 경로가 기존 방어를 **우회하도록 구현될 수 있다**"이며, 그래서 AC가 각 보류 사유를 익스큐터에 대해 개별 검증한다.

---

## §4. 익스큐터 본문 해석의 미결 지점

### §4.1 알려진 사실

- 익스큐터는 풀 오브젝트가 **아니다.** 룰북은 `Page <page>.<executor>`로 주소한다(`server/rulebook/assets/v2.4.2/10_object_model.md:23-25`): *"**Executor** — a playback handle (fader/button) on a **Page**, addressed as `Page <page>.<executor>` (e.g. `Page 1.201`). Sequences are assigned to executors for live playback."*
- 패널은 `DataPool/Pages` → 페이지 → 자식을 드릴다운하며 `f"{base_path}/{number}"`로 경로를 조합한다(`server/orchestrator/tools.py:264`). 따라서 후보 경로 형상은 `DataPool/Pages/<page>/<executor>`.
- 사전 라이브 프로브(`.moai/state/verify/probe-executor-numbers.log`, 실제 onPC 2.4.2, 읽기 전용) 결과: 페이지 자식은 `class='Executor'`이고 **실제 비연속 익스큐터 번호**(`i` = 1, 5, 11, 91, 92, 93, 95, 101)를 가지며, `name`은 `'Sequence 71'` 같은 값이다.

### §4.2 `name`은 해석 경로로 쓸 수 없다

익스큐터의 표시 이름은 할당된 시퀀스의 이름이다. 시퀀스를 "Cyan Look"으로 rename하면 그 문자열은 더 이상 `Sequence 71`을 말하지 않는다. 이름에서 할당을 파싱하는 것은 **기각한 대안 (b)를 다른 이름으로 되살리는 것**이며 같은 취약성을 갖는다. REQ-EXECREF-007이 이를 금지한다.

### §4.3 fetcher 형상 자체가 제약이다

`StateBodyFetcher`(console.py:403-432)의 현재 메커니즘:

```
DEFAULT_BODY_PATHS = {"Macro": "DataPool/Macros/{ref}", ...}
type_word, _, ref = reference.partition(" ")
template = self._templates.get(type_word)
payload = self._query(template.format(ref=ref))
```

`{ref}` 단일 치환은 페이지 성분을 요구하는 경로를 표현할 수 없다. `"Executor 201"`이라는 참조 문자열에는 페이지 번호가 없다. 따라서 다음 중 하나가 필요하며, 어느 쪽인지는 **프로브 결과에 달려 있다**:

- (i) 익스큐터가 페이지 무관하게 주소 가능한 경로가 존재 → 템플릿 메커니즘 유지 가능
- (ii) 페이지 성분이 필수 → fetcher가 타입별 해석 전략을 가질 수 있어야 함(형상 변경)
- (iii) 익스큐터 노드가 본문을 노출하지 않음 → 할당 시퀀스로의 간접 해석 필요, 또는 해석 불가로 fail-closed 유지

이는 "손으로 넘길" 사안이 아니라 추론해야 할 설계 결정이다. design.md §5가 결과별 함의를 기술한다.

### §4.4 프로브는 작성되어 있고 실행 대기 중이다

`.moai/state/verify/probe_executor_body.py` — `state` 동사 전용, 발화 0건·쓰기 0건. 세 질문(Q1 경로 해석 여부, Q2 자식이 할당 시퀀스의 큐인지, Q3 큐 페이로드가 커맨드 필드를 나르는지)을 답하도록 설계됨.

**아직 실행되지 못했다.** `.moai/state/verify/probe-executor-body.log`:

```
--- pages root ---
QUERY FAILED for 'DataPool/Pages': StateQueryError("no state reply for 'DataPool/Pages' within 5.0s")

No pages in this showfile — cannot probe executors.
```

응답기가 답하지 않았다(`ping -> False`) — 플러그인이 현재 로드된 쇼파일에 Import되지 않았거나 OSC가 무장되지 않은 상태로 추정. 사용자가 콘솔을 무장한 뒤 오케스트레이터가 재실행하고 **plan-audit 이전에** 결과를 접어 넣는다.

---

## §5. cue CMD 갭 — 기존 갭, 본 SPEC이 닫지 않음

### §5.1 사실

`StateBodyFetcher.fetch_body`(console.py:414-432)는 본문 라인을 `payload["children"][*]["name"]`으로 구성한다:

```python
        for child in children:
            name = child.get("name") if isinstance(child, dict) else None
            ...
            lines.append(name)
```

응답기는 자식당 `{name, class, i}`만 반환한다(`console/lua/copilot_responder.lua:456`):

```lua
        local item = { name = M.safe_name(entry.obj), class = M.safe_class(entry.obj) }
```

MA3 큐는 발화 시 실행되는 CMD(Command) 프로퍼티를 가질 수 있다. 그 필드는 와이어에 실리지 않는다.

### §5.2 함의 (정직하게)

- Sequence 참조의 "본문 라인"은 **큐 이름**이지 큐 커맨드가 아니다.
- `Blackout`이라는 **이름**의 큐는 스크리닝된다. CMD가 `Delete Sequence 5`인 큐는 보이지 않는다.
- 따라서 **`Go+ Sequence 41`이 오늘 통과하는 이유는 게이트가 큐를 검증해서가 아니라 큐 이름이 우연히 무해해서다.**
- expand-or-hold는 **어떤 참조 타입에 대해서도** 큐 커맨드를 스크리닝한 적이 없다. Executor 추가가 이 갭을 만들지 않는다.
- `DEFAULT_BODY_PATHS`의 독스트링(console.py:391-395)이 자신을 `PLACEHOLDER assumption (onPC-unverified, M6 live calibration)`이라 표기한 것이 이 사실을 가리고 있었다.

### §5.3 후속 SPEC 권고 (명명)

**`SPEC-COPILOT-CUECMD-001` — 큐 커맨드 프로퍼티 스크리닝** (권고, 미생성)

- 범위: 응답기가 자식 페이로드에 큐의 CMD/Command 프로퍼티를 실어 보내도록 확장 + `StateBodyFetcher`가 이름 대신(또는 이름과 함께) 커맨드를 본문 라인으로 사용.
- 선행 조건: `copilot_responder.lua` 변경 + `plugin_pack.py` 재배포 + Import + 라이브 재검증. 와이어 프로토콜 확장(하위 호환 필드 추가).
- 영향 범위: **모든** 참조 타입(Sequence 포함) — 본 SPEC보다 큰 안전 이득이지만 큰 배포 비용.
- 본 SPEC에서의 처리: `@MX:DEBT` + `@MX:CEILING`(큐 이름만 스크리닝됨) + `@MX:UPGRADE`(응답기가 CMD 프로퍼티를 전송하게 되면 본문 소스를 교체) 주석으로 코드에 고정(plan.md §D).

**`SPEC-COPILOT-EXECBODY-001` — 익스큐터 할당 시퀀스 아이덴티티 노출** (권고, 미생성, 2026-07-23 추가)

- 범위: `console/lua/copilot_responder.lua`의 `build_snapshot`을 확장해, 익스큐터 노드에 대해 범용 `handle:Children()`(자식 0건 반환 — design.md §5.1 Q2)이 아니라 익스큐터 전용 로직으로 할당된 시퀀스의 아이덴티티(시퀀스 번호 또는 경로)를 노출한다. 그 결과를 `StateBodyFetcher`가 본문 해석의 진입점으로 사용하도록 `server/safety/console.py`를 확장한다.
- 근거(2026-07-23 라이브 프로브, `.moai/state/verify/showui-m6-resume/5-probe-body.log`): 익스큐터 노드는 `DataPool/Pages/<page>/<local-index>`로 해석 가능하지만(ASSUMPTION-8 확인됨) 자식을 노출하지 않는다(ASSUMPTION-9 반증됨, `childCount: 0` 4/4 샘플). 응답기가 완전히 범용이라 익스큐터별 분기가 없기 때문 — 아키텍처적 갭이지 샘플링 아티팩트가 아니다(design.md §5.1).
- 선행 조건: `copilot_responder.lua` 변경 + `plugin_pack.py` 재배포 + Import + 라이브 재검증. `SPEC-COPILOT-CUECMD-001`과 마찬가지로 응답기 Lua 재배포가 필요하다.
- **설계 입력 — 역주소 문제**: 익스큐터의 페이지-로컬 자식 인덱스(1, 5, 11, 91, ...)와 콘솔 발화·표시에 쓰이는 번호(101, 105, 111, 191, ..., 페이지 1에서 +100 오프셋 균일 확인, `.moai/state/verify/showui-m6-resume/executor-offset.jsonl` 8/8행)는 서로 다른 두 숫자 체계다. 이 오프셋이 다른 페이지에서도 균일한지는 **미검증**이다. `SPEC-COPILOT-EXECBODY-001`을 계획하는 사람은 이 역주소 문제를 설계 초기에 명시적으로 다뤄야 한다 — 검증 없이 오프셋 관례를 하드코딩하면 REQ-EXECREF-007이 기각한 이름-파싱과 동일한 부류의 취약성(out-of-band 관례 의존, 안전-인접 코드)을 재도입하게 된다(design.md §5.6).
- **시퀀싱 메모**: `SPEC-COPILOT-CUECMD-001`과 함께 계획할 가치가 있을 수 있다 — 둘 다 응답기 Lua 재배포를 필요로 하므로, 별도의 두 번 재배포보다 한 번에 묶는 편이 배포 비용을 줄일 수 있다. 다만 이 결정은 두 SPEC을 실제로 계획하는 사람에게 맡긴다(본 SPEC은 범위 밖).
- 본 SPEC에서의 처리: 구현하지 않음(M2 DESCOPED, plan.md M2). REQ-EXECREF-004/005/006 및 REQ-EXECREF-013을 DEFERRED로 표기(spec.md §B.2/§B.5)하여 이 후속 SPEC의 근거로 남긴다.

---

## §6. 코퍼스 확장의 실제 형태 (브리핑 정정)

브리핑은 FN 코퍼스가 "폐쇄 집합을 동적으로 순회하므로 자동 확장된다"고 전제했다. **부분적으로만 참이다.**

`server/tests/test_safety_corpus.py:86-92`:

```python
def _invoking_commands() -> list[str]:
    """One gate-level command per SSOT invoking entry (verbs + bare forms)."""
    commands = [f"{verb} Macro 9" for verb in RULESET.invoking_verbs]
    for form in RULESET.bare_object_forms:
        commands.append(form.replace("<n>", "9"))
    return commands
```

- **동사 축**: `RULESET.invoking_verbs`를 동적으로 순회 → 자동 확장 ✅
- **참조 타입 축**: `Macro`로 **하드코딩** → `Executor` 추가가 자동 확장되지 **않음** ❌
- `_SCENARIOS`(95-110)의 본문 사전 키도 `"Macro 9"`/`"Plugin 9"` 고정.

또한 `RECOGNIZED_REFERENCE_TYPES`는 `blacklist.yaml`이 아니라 **`classify.py`의 파이썬 튜플**이다. 즉 `SafetyRuleset`(ruleset.py:30-36: `version`/`blacklist`/`invoking_verbs`/`bare_object_forms`)에는 없다.

따라서 REQ-EXECREF-011의 "동적 순회"는 **새로 만들어야 하는 것**이며, 구현 형태는 코퍼스가 `classify.RECOGNIZED_REFERENCE_TYPES`를 import하여 참조 타입 축으로 parametrize하고 `_SCENARIOS` 본문 키를 타입별로 생성하는 것이다. 이는 사소한 추가가 아니라 코퍼스의 실제 리팩터다(plan.md M1의 주요 작업량).

**주의**: 하드코딩된 `Macro` 축을 타입 축으로 일반화하면 케이스 수가 참조 타입 수만큼 곱해진다(현재 10 동사 × 4 시나리오 = 40 → 타입 4종이면 160). 실행 시간과 가독성을 저울질해야 하며, `bare_object_forms` 축(`Macro <n>`/`Plugin <n>`)은 타입 축과 무관하게 유지된다.

---

## §7. 리스크와 암묵 계약

1. **완화의 방향성** — 이 변경은 안전 경계를 넓히는 유일한 방향이다: 이전에 무조건 보류되던 커맨드 집합이 이제 본문 조회에 도달한다. 조회 결과가 무해할 때만 통과하지만, **본문 조회에 도달하는 것 자체가 확대**다. design.md §4가 이 확대의 각 노출면을 열거하고 증명한다.

2. **프로브 미실행 상태의 설계** — §4.4의 이유로 해석 경로가 미확정이다. 이를 "나중에 알아보자"로 처리하면 run-phase 에이전트가 임의 추측한다. design.md §5가 **결과별 함의**를 명시하고, 어떤 결과에서도 옳은 fail-closed 폴백을 규정한다: 본문을 읽을 수 없으면 보류 — 즉 오늘의 동작. **본 SPEC의 최악 결과는 "마찰이 줄지 않음"이지 "미검증 커맨드가 통과함"이 결코 아니다.**

3. **단일 스크리닝 경로 압력** — "패널 커맨드는 이미 안전하니 expansion을 건너뛰자"는 유혹이 이 SPEC 근처에서 자연스럽게 발생한다. 그것은 이름만 다른 제2 스크리닝이며 gate.py:260-264 `@MX:ANCHOR`와 SHOWUI REQ-SHOWUI-007이 금지한다.

4. **단일 분류 의미론 압력** — 익스큐터 전용 매칭 분기를 `classify_command` 밖에 두려는 유혹도 같은 이유로 금지된다(classify.py:158-161 `@MX:ANCHOR`). REQ-MVP-013/014의 FN=0은 하나의 매칭 의미론 위에 서 있다.

5. **비연속 익스큐터 번호** — 프로브 실측상 익스큐터 번호는 비연속(1, 5, 11, 91, 92, 93, 95, 101)이다. 배열 인덱스로 키잉하면 조용히 다른 오브젝트를 조회한다. `tools.py:164-168`의 "N번째 항목 ≠ 오브젝트 N" 계약을 그대로 계승해야 한다.

6. **`Go+ Page 1.101` 구문** — 패널은 만들지 않지만 LLM이 만들 수 있다. 해석되지 않으므로 계속 보류 = fail-closed. REQ-EXECREF-015가 이를 침묵 대신 명시로 처리한다.

7. **기준선 오염** — HEAD `0576553`에 환경적 실패 1건(`test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`, 구동 중 onPC가 UDP 9005 점유)이 있다. run-phase가 이를 자기 회귀로 오인하지 않도록 spec.md §C와 plan.md §C에 기록.

---

## §8. 핵심 참조 파일

`server/safety/classify.py`, `server/safety/expand.py`, `server/safety/console.py`, `server/safety/gate.py`, `server/safety/bootstrap.py`, `server/safety/ruleset.py`, `server/safety/blacklist.yaml`; `server/tests/test_safety_corpus.py`, `test_safety_classify.py`, `test_safety_expand.py`, `test_safety_gate.py`, `test_safety_console.py`, `test_safety_ruleset.py`, `test_architecture.py`, `test_web_panel_execute.py`; `server/orchestrator/tools.py`; `console/lua/copilot_responder.lua`, `console/lua/PROTOCOL.md`; `server/rulebook/assets/v2.4.2/10_object_model.md`, `31_choreography_patterns.md`; `.moai/state/verify/probe_executor_body.py`, `probe-executor-numbers.log`, `probe-executor-body.log`.
