# SPEC-COPILOT-SONGCUE-001 — 설계 근거 (design)

status: draft (v0.1.0, 2026-07-28) · Tier L · 본 문서는 spec.md 요구의 설계 근거와 위험 검토를 담는다. **§5는 한 부분이다 — §5.1 해소된 결정 10건(A~J), §5.2 열린 슬롯 0건.** BUSKWIZ가 v0.1.0부터 유지한 "열린 슬롯 0건" 상태를 착수 시점부터 계승한다.

> **참조 규약 (BUSKWIZ v0.1.3에서 확정된 규약을 그대로 계승 — 이 문서 전체에 적용).**
> **본 SPEC의 SSOT(spec.md · acceptance.md)와 형제 아티팩트(plan.md · research.md · progress.md)는 줄번호로 인용하지 않는다.** `REQ-SONGCUE-nnn` · `AC-SONGCUE-nnn` · `ASSUMPTION-nn` · 절 제목(`spec.md §C`)처럼 **개정을 견디는 토큰**만 쓴다. 근거는 BUSKWIZ의 감사 실측이다 — 형제→SSOT 줄 앵커 52개 중 10개가 빈 줄을, 6개 이상이 다른 내용을 가리키고 있었다. **토큰은 내용이 사라지면 토큰도 사라져 즉시 드러나지만, 줄번호는 조용히 옆 문장을 가리킨다.** 반면 **`파일:줄`은 코드 · 룰북 · 감사 로그 · 타 SPEC 아티팩트에 그대로 유지**한다 — 코드는 커밋 없이 움직이지 않고 다른 안정 식별자가 없으며, 완료·동결된 SPEC(BUSKWIZ · LOOKLIB · EXECREF · EXECBODY · SHOWUI)의 줄도 밀지 않는다.
>
> **약칭 금지.** 요구·인수 토큰은 항상 완전형이다 — `REQ-SONGCUE-007` · `AC-SONGCUE-011`. 슬러그를 뺀 축약형(`REQ-` 또는 `AC-` 뒤에 곧바로 세 자리 숫자가 오는 형태)은 이 문서에 **한 건도 없다.** 그 형태를 예시로 적지 않는 이유는 **예시 자체가 스캔에 걸려 이 주장을 거짓으로 만들기 때문**이다(BUSKWIZ가 마커 개수 주장에서 세운 규율의 재적용). 금지 이유는 실질적이다 — 같은 기반 위의 SPEC들이 저마다 007번 요구를 갖고 있으므로, 축약형은 어느 SPEC의 것인지 복원할 수 없다.

> **v0.1.0 — 최초 작성. 착수 전 앵커 정정 6건을 먼저 기록한다.**
> 본 문서는 작성 착수 시점에 인용 예정 앵커를 **전량 직접 실측**했고, 인계 브리핑과 어긋난 것 6건을 발견했다. 정정 없이 옮겨 적으면 여섯 개의 조용한 거짓이 남았을 것이므로 여기에 먼저 적는다. **정정된 값만 이 문서 전체에서 쓴다.** 앞 4건은 형제 문서(progress.md 담당)가 독립적으로 같은 결론에 도달했고, 뒤 2건은 본 문서가 단독으로 발견했다.
>
> | 인계된 앵커 | 실측 정정 | 무엇이 있었나 |
> |---|---|---|
> | `server/orchestrator/tools.py:227-231` (dedupe 면제 3종) | **`:234-238`** (패턴 `:235` `Clear` · `:236` `ClearAll` · `:237` 맨 `Fixture\|Group`) | `:227-233`은 그 위의 사유 주석이고 `:233`은 `_SELECTION_OPERAND` |
> | `server/safety/console.py:484-490` (자식 `name`을 본문 라인으로 수집) | **`:478-484`** (루프 `:479-483`, `return tuple(lines)` `:484`) | 파일 총 **484행** — `:485-490`은 존재하지 않는다 |
> | `server/safety/classify.py:46` (`RECOGNIZED_REFERENCE_TYPES`) | **`:44`** | `:46`은 `_NUMERIC_REF` |
> | `server/looks/matching.py:21-25` (`DYNAMICS_TERMS`) | 정의는 **`:92`**, 항목은 **`:94-130`**(닫는 `}`는 `:131`) | `:21-25`는 모듈 독스트링의 설명 산문. 인계 브리핑을 정정하며 한 번 더 좁혀 적은 `:99-121`도 표 전체가 아니다 — 그것은 `인트로`(`:99`)~`드랍`(`:121`) 열거 구간이고, `:94-98`(앰비언트 밴드)과 `:122-130`(`drop`~`finale`)이 밖에 남는다 |
> | `server/orchestrator/tools.py:526-550` (dedupe 블록) | **`:524-569`** (`failed = False` `:524` · `already_executed` 시드 `:533` · 루프 `:534` · stop-on-first-failure 가드 `:535-543` · 건너뛰기 분기 `:544-557` · `failed = True` `:569`) | `:525-532`는 `already_executed`의 사유 주석이고(주석은 `:525`의 `# MEDIUM backlog item …`에서 시작한다), `:551-569`가 범위 밖으로 빠져 stop-on-first-failure와 `executed_ok`가 PRESERVE 밖에 놓였다 |
> | `Set Cue … Property 'TrigType' **'Time'**` | 룰북의 실제 리터럴은 **`'Follow'`**(`31_choreography_patterns.md:111`) | `'Time'`은 같은 줄 주석의 토큰 메뉴(`Go / Time / Follow / Sound / BPM`)에서 온 것이다. 게다가 `:115`가 "Trigger tokens are Capitalized"를 명시한다 — **`'Time'`은 T2 문법의 검증된 리터럴이 아니라 토큰 치환**이며, 이 구분이 §4 위험 #10과 AP-15의 실체다 |
>
> **본 문서가 실측으로 새로 확정한 사실 4건** (전부 재현 가능하며 SSOT를 개정하지 않는다):
> (i) **라이브 `Cue ≥2`는 `server/audit_logs/*.jsonl`의 `executed` 이벤트 전량에서 0건**이다(직접 스캔). T1 등급의 큐 저작 기록 5건은 **전부 `Cue 1`**이다 — `audit-20260719.jsonl:148`(`Store Sequence 62 Cue 1 'Cyan Look'`) · `:186`(`Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4`) · `audit-20260722.jsonl:1057`(`… Sequence 90 Cue 1 'Blue Look'`) · `audit-20260726.jsonl:327`(`… Sequence 22 Cue 1 'Golden Chorus'`) · `:538`(`… Sequence 17 Cue 1 'Golden Chorus'`), 전부 `ok:true detail:"OK"`. **ASSUMPTION-21이 블로킹인 이유가 이 0건이다** — 본 SPEC의 핵심 형상(섹션 N개 = 큐 N개)이 정확히 미검증 구간에 놓인다.
> (ii) **시퀀스 번호 여집합에 라이브 근거가 있다.** 실기 쇼파일의 시퀀스 번호는 비연속이었다 — `1, 2, 11~16, 30, 41, 50, 62, 71, 80`이고 `3~10 · 17~29`가 부재하다(`SPEC-COPILOT-SHOWUI-001/progress.md:465`). 여집합은 공집합에 가까운 예외가 아니라 **일반적으로 넉넉한 집합**이며, 동시에 "존재하는 것만 열거된다"는 사실이 그 실측으로 확인된다(ASSUMPTION-23의 출발점).
> (iii) **`busking._merge`는 결합 번들과 함께 룩별 구간 `[시작, 끝)`을 반환한다**(`server/looks/busking.py:209`, `:226`). 그 docstring이 "경계를 아는 유일한 자리가 여기다. 보고 계층이 이 규칙을 다시 구현하면 두 곳이 갈라진다"라고 적는다(`:202-206`). 섹션별 2단 보고가 per-command status를 섹션에 귀속시키는 유일한 정당 경로가 이 반환값이며, 재구현은 AP-13이 막는다.
> (iv) **별도 Marker/Mark MA3 오브젝트는 룰북 `v2.4.2/` 전체에서 0건**이다(직접 스캔). 제안서가 산출물로 적은 "섹션 마커"(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:71`)의 저장소상 실체는 **큐 이름 문자열**뿐이며, 그것이 사전 확정 ③(ASCII 고정)을 산출물 정의의 문제로 만든다 — 마커가 별도 오브젝트라면 이름 규칙은 표현 문제였겠지만, 마커가 곧 큐 이름이므로 이름 규칙은 **게이트 통과 문제**다.

---

## §1. 설계 의도

LOOKLIB은 "룩 1개를 이 리그의 프리셋으로"를 완성했고, BUSKWIZ는 그 위에 "N개 룩을 가로지르는 조율"을 얹었다. 본 SPEC이 더하는 것은 **시간축 하나**다. 설계의 핵심 선택은 넷이다.

**첫째 — 제안서의 3부작 중 1부만 짓고, 나머지 둘은 게이트로 남긴다.** 제안서 P1-1은 산출물을 `"곡당 시퀀스 1개 + 타임코드 트랙 + 섹션 마커"`로 적었다(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:71`). 세 부분의 저장소 근거 등급이 서로 다르다 — **시퀀스·큐 저작은 T1**(감사 로그 실행 기록 5건, 위 실측 (i)), **타임코드는 T5**(저장소 전체 0건. 유일 등장은 외부 참고 링크 텍스트 `:125`, `:127`), **섹션 마커는 별도 오브젝트로서 0건**(위 실측 (iv)). 그래서 본 SPEC은 T1 구간을 짓고, T5 구간을 M0 라이브 게이트에 걸고, 마커를 큐 이름으로 환원한다. 이것은 축소가 아니라 **등급에 맞춘 배치**다 — 근거가 없는 구간에 코드를 먼저 쓰면 그 코드가 근거를 대신하게 된다.

**둘째 — 상태를 갖는 것은 큐 번호 원장 하나이고, 그것은 BUSKWIZ 슬롯 원장의 시간축 판본이다.** `_first_free_slot`(`server/looks/instantiate.py:307`, 본문 `:308-312`)은 인자로 받은 점유 목록에서 1부터 첫 미점유를 고를 뿐 **어디에도 쓰기가 없고**, `_plan_stores`(`:325-384`)는 `binding.occupied`를 읽기만 한다. BUSKWIZ가 이 결함을 고치지 않고 **바깥에서 감싸** 풀었다(`server/looks/busking.py:158` `_advance` — frozen `PoolIndex`를 새 객체로 갈아 끼운다). 본 SPEC의 큐 번호는 **동형이면서 더 단순하다** — 원장의 시작값이 리그 관측이 아니라 **섹션 입력 순서**이므로, 원장은 `i + 1`이라는 전순서를 갖는다. 단순함이 미덕인 이유는 실패 모드가 하나로 줄기 때문이다: 원장이 전진하지 않으면 섹션 N개가 같은 큐를 덮고, 콘솔은 성공으로 답한다(`instantiate.py:291-299`의 `@MX:WARN`이 슬롯 축에서 같은 문장을 적는다 — "MA3 reports it as success"). 그래서 AC-SONGCUE-006 구간 ②가 "큐 번호가 `1`부터 `N`까지 빠짐없이 한 번씩"을 기계로 고정한다.

**셋째 — 큐 이름은 표현이 아니라 실행 경로의 일부다.** 이것이 사전 확정 ③이 스타일 규칙이 아닌 이유다. 큐 이름은 생성 시 커맨드 문자열에 들어가고, **재조회 시 안전 게이트가 커맨드로 파싱하는 본문 라인으로 되돌아온다** — 체인은 `server/safety/console.py:478-484`(자식의 `name`을 그대로 본문 라인으로 수집) → `server/safety/expand.py:106-112`(라인마다 `validate`, 실패 시 **보류**) → `server/safety/grammar.py:20`(`_VERB_SHAPE = ^[A-Za-z][A-Za-z0-9_+\-]*$`, **ASCII 전용**)이다. ASCII 큐 이름의 종단 통과는 라이브 관측이 있다 — 큐 `'Blue Look'`을 담은 `Sequence 90`에 `Go+`/`Off` 둘 다 `ok=True`였다(`SPEC-COPILOT-SHOWUI-001/progress.md:460`). 한국어 큐 이름의 종단 효과는 **미관측**이고, 유일한 등장은 오프라인 목이다(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72` — `Label Cue 12 '오프닝'`, `detail:"offline mock execution"`). 즉 한국어를 발화하면 **관측된 적 없는 경로**로 들어가면서, 실패가 "보류"라는 조용한 형태로 나타난다. 한국어는 BUSKWIZ가 이미 세운 표현 계층에 둔다(`server/looks/report.py:63` `_REASON_LABELS`, `:74` `_VERDICT_LABELS`, 공개 접근자 `reason_label` `:77`).

**넷째 — 검증의 상한을 먼저 인정하고 그 안에서만 보고한다.** 응답기는 `DataPool/Sequences/<n>/<m>`에서 `name`/`class`/`i`(+ 중첩 `Part` 자식)만 반환하고 **커맨드·`CueFade`·`TrigType`은 어떤 형태로도 반환하지 않는다** — 라이브 실측이다(`SPEC-COPILOT-EXECREF-001/design.md:167`). 응답기 자체가 `Cue`를 특별 취급하지 않으며(`console/lua/copilot_responder.lua` 전체에 `Cue` 문자열 0건), 주소형 특례는 `Executor <n>` **하나뿐**이다(`:403` "the ONLY address form resolve_path special-cases", 패턴 `:405`). 그리고 `console/lua/**`는 PRESERVE다. 따라서 **본 SPEC이 만든 초안을 본 SPEC이 스스로 완전히 검증할 방법은 없다** — 확인 가능한 것은 큐의 **존재와 이름**이다. 설계가 여기서 할 수 있는 정직한 일은 하나뿐이다: 그 한계를 결과 페이로드에 **명시**하고(REQ-SONGCUE-017), "확인했다고 주장하는 필드가 0건"임을 테스트로 고정하는 것(AC-SONGCUE-014 구간 ②). 관측하지 않은 것을 보고하지 않는다.

---

## §2. 변경 표면 (예상)

1. **`server/looks/songcue.py` (신규)** — 섹션 파싱(시각 3종 → 밀리초 정수) + 어휘 조회 + **큐 번호 원장** + 섹션별 룩 매핑 + 섹션 번들 결합. 순수 함수 — 콘솔·OSC 무접촉, 주입된 리그 해석 결과와 섹션 목록에만 의존. `DYNAMICS_TERMS`(`server/looks/matching.py:92`, 항목 전체 `:94-130`)와 `DYNAMICS_MIN`/`DYNAMICS_MAX`(`server/looks/schema.py:35-36`)는 **재정의하지 않고 import**한다(REQ-SONGCUE-003 · AC-SONGCUE-003). 룩 후보 순회는 `looks_for_genre`(`server/looks/busking.py:81`)를 그대로 호출한다(REQ-SONGCUE-005).
2. **`server/looks/songcue_report.py` (신규) + `server/looks/report.py` 공개 접근자 1건 추가** — 섹션 축 2단 보고(REQ-SONGCUE-016). **별도 모듈인 이유**는 집계 단위가 다르기 때문이다: BUSKWIZ의 판정 단위는 `(룩, 역할)`이고 본 SPEC의 판정 단위는 **섹션**이다. 두 축을 한 모듈에 넣으면 BUSKWIZ 테스트가 고정한 `BuskingReport` 계약(`server/looks/report.py:116`)을 건드리게 된다. **한국어 어휘는 재정의하지 않는다** — 사유는 이미 공개된 `reason_label`(`:77`)을 import하고, 판정 라벨은 `report.py`에 공개 접근자 1개(`_VERDICT_LABELS` `:74`를 감싸는 형태)를 더해 재사용한다. 접근자 추가가 어휘 복제보다 나은 이유: 같은 한국어가 두 파일에 살면 한쪽만 갱신되는 순간 거짓이 된다(`server/looks/busking.py:75-77`이 상수 복제를 거부하며 적는 논리와 같다). 이 추가는 비파괴이며 기존 호출자에 영향이 없다(§5.1 결정 I). **이 모듈이 공개하는 이름 2개는 설계 산출물이지 구현 재량이 아니다** — 재조회 한계 문구의 정본은 공개 상수 **`PROPERTY_UNOBSERVED_NOTE`**이고, 결과 페이로드에서 그 문구를 싣는 키는 **`property_unobserved`**다. AC-SONGCUE-014가 그 둘을 **문자열 동일성**으로 대조하므로(산문 대조가 아니다) 문구를 보고 코드에 다시 적는 순간 대조가 깨진다 — 한국어 어휘를 복제하지 않는 것과 같은 이유다(REQ-SONGCUE-017).
3. **`server/orchestrator/tools.py`** — **신규 툴 1종 등록으로 한정**(REQ-SONGCUE-019). `TOOL_NAMES`(`:42`; 직전 선례 항목 `"prepare_busking"` `:49`) · `definitions`(선례 `:1196`) · `handlers`(선례 `:1231`) **3곳 병렬 갱신**, 기존 관례 그대로. **툴 인자는 섹션 목록과 장르뿐이다** — 리그 데이터도, 시퀀스 번호도, 큐 번호도 인자가 아니다(REQ-SONGCUE-020, AC-SONGCUE-015 구간 ③). 리그는 핸들러가 `collect_rig_sections`(`:373`)로 읽고, 미도착이면 **번들 구성 이전에** `is_error=True`로 조기 반환한다(선례 `:757`의 `unavailable` 가드). `_PROGRAMMER_STATE_COMMANDS`(`:234-238`)와 실행/dedupe 블록(`:524-569`)은 **무변경**(REQ-SONGCUE-011, AC-SONGCUE-010 구간 ②).
4. **타이밍 축 — M0 2항 게이트 종속, 파일 수 미정이 아니라 분기 확정.** ASSUMPTION-20(타임코드)이 GO일 때만 타임코드 발화 축이 생기고, ASSUMPTION-22(`TrigType`/`TrigTime`)가 GO일 때만 자동 진행 축이 생긴다. **둘은 독립이다** — 하나가 부정이어도 다른 하나는 살 수 있다(REQ-SONGCUE-013과 REQ-SONGCUE-014가 별 요구인 이유). 어느 쪽이든 부정이면 **그 축의 커맨드 0건**이고, AC-SONGCUE-012 **②(타임코드 축) · ④(자동 진행 축)**가 **생성 커맨드 튜플 전수 + 비공허성**으로 기계 고정한다. 이것은 "정해지지 않았다"가 아니라 **입력에 따라 정해지는 두 결과가 모두 정의되어 있다**는 뜻이다.
5. **테스트 6종 (신규)** — `server/tests/test_songcue_sections.py` · `test_songcue_map.py` · `test_songcue_bundle.py` · `test_songcue_timing.py` · `test_songcue_report.py` · `test_songcue_tool.py`. 경로는 acceptance.md §C.1이 인용한 것 그대로다.

**무변경(PRESERVE — REQ-SONGCUE-021, AC-SONGCUE-016)**: `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` · `server/safety/**` · `server/web/preview.py` · `console/lua/**` · `server/rulebook/assets/v2.4.2/**` · `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:234-238`)와 실행/dedupe 블록(`:524-569`). 신규 YAML·JSON 자산 **0개** — 본 SPEC은 출하된 32룩의 소비자이지 증보자가 아니다.

**`matching.py`와 `instantiate.py`가 PRESERVE에 들어온 이유는 반증 장치다.** 본 설계의 형상은 "섹션 축을 **바깥에서** 감싼다"이므로, 그 두 파일을 고치게 되는 것이 곧 **형상의 반증**이다. `matching.py`의 diff가 생기면 어휘를 재정의했거나 확장한 것이고(REQ-SONGCUE-003 위반), `instantiate.py`의 diff가 생기면 큐 번호 원장이 감싸기가 아니라 개정으로 풀렸다는 뜻이다 — 그 개정은 단일 룩 경로와 BUSKWIZ를 함께 흔든다. PRESERVE에 넣으면 그 반증이 diff로 즉시 드러나고, 넣지 않으면 조용히 지나갈 수 있다(AC-SONGCUE-016 추가 assert가 두 파일을 이름으로 지목하는 이유).

**`server/looks/busking.py`와 `report.py`는 재사용하되 확장 가능하다** — 다만 BUSKWIZ의 테스트가 그 계약을 고정하고 있으므로 파괴적 변경은 즉시 회귀로 드러난다. 본 SPEC이 실제로 손대는 것은 항목 2의 공개 접근자 1건뿐이며, `busking.py`는 **호출만** 한다.

---

## §3. 데이터 흐름 (설계 목표)

**범례** — 각 단계의 첫 글자가 그 단계의 성격이다.

```
  =   기존 코드 재사용. 본 SPEC이 한 줄도 고치지 않는다 (PRESERVE 또는 무변경 소비)
  +   본 SPEC이 새로 쓰는 지점
  ?   M0 라이브 게이트 종속. GO / DESCOPE 양 분기가 미리 정의되어 있다
```

```
[채팅] "Intro 0:00 / Verse 0:18 / Chorus 0:52 / … 이 구조로 록 큐리스트 만들어줘"
  │
  ├ + [툴 디스패치 — registry.dispatch          ← 모델이 들어오는 유일한 문]
  │      신규 툴 1종. TOOL_NAMES(tools.py:42) · definitions(선례 :1196) ·
  │      handlers(선례 :1231) 3곳 병렬 등재                      (REQ-SONGCUE-019)
  │      인자 = 섹션 목록 + 장르. 리그·시퀀스·큐 번호는 인자가 아니다(REQ-SONGCUE-020)
  │
  ├ + [섹션 파싱 — songcue.parse_sections                              ← 신규]
  │      mm:ss  |  mm:ss.mmm  |  초 단위 실수   →   **밀리초 정수**
  │        (부동소수 비교를 남기지 않는다 — AC-SONGCUE-001 구간 ②)
  │      단조 증가 위반 · 중복 → **거부 + 어긋난 인덱스**. 정렬 보정 0건
  │                                          (REQ-SONGCUE-002 / AP-1)
  │      ⇒ 여기서 정해진 **입력 순서가 곧 큐 번호 순서**이고 이후 바뀌지 않는다
  │
  ├ = [섹션 어휘 조회 — matching.DYNAMICS_TERMS (matching.py:92, 항목 전체 :94-130)]
  │      "인트로"/"intro"/"도입" → (1,2)      "벌스"/"verse" → (2,3)
  │      "빌드"/"프리코러스"/"riser" → (3,)   "코러스"/"후렴"/"드랍" → (4,5)
  │      다이내믹스 범위 1..5 = schema.py:35-36                (REQ-SONGCUE-005)
  │      **import만 한다** — 매핑 딕셔너리 리터럴 재정의 0건
  │                                          (REQ-SONGCUE-003 / AC-SONGCUE-003 / AP-8)
  │      어휘 밖 이름 → 추정 금지. 그 섹션만 "지정 필요"로 표시하고
  │      어휘에 있는 섹션은 계속 해석한다 (전량 실패로 접지 않는다)
  │                                          (REQ-SONGCUE-004 / AC-SONGCUE-004 / AP-2)
  │
  ├ = [룩 선택 — busking.looks_for_genre (busking.py:81)]
  │      다이내믹스 오름차순 → look_id 사전순의 **결정론적 전순서**
  │      요구 다이내믹스에 룩 없음 → 가장 가까운 룩으로 **승격 금지**,
  │      그 섹션을 미매핑으로 보고                (REQ-SONGCUE-006 / AC-SONGCUE-005 ③)
  │
  ├ = [리그 1회 해석 — collect_rig_sections (tools.py:373)
  │                  → resolve_roles / resolve_pools]
  │      섹션 수와 무관하게 **1회**. 이후 재해석 0건
  │      섹션 미도착 → 번들 구성 **이전에** is_error=True 조기 반환
  │        (선례 tools.py:757 unavailable 가드 — "보지 않은 리그에 대한 주장"을 막는다)
  │
  ├ + [시퀀스 번호 확정 — 리그 열거의 **여집합**                        ← 신규]
  │      열거가 알려주는 것은 **존재하는** 시퀀스뿐 (경로 console.py:399
  │      DEFAULT_BODY_PATHS["Sequence"] = "DataPool/Sequences/{ref}")
  │      실측 근거: 실기 쇼파일의 번호는 비연속이었다 —
  │        1,2,11~16,30,41,50,62,71,80 (3~10·17~29 부재)
  │        SPEC-COPILOT-SHOWUI-001/progress.md:465
  │      열거 실패 · 절단 신호 → **번호를 추측하지 않고 거부**
  │                                          (AC-SONGCUE-008 ② / AP-17)
  │      ? "비어 있음" vs "존재하지 않음"의 구별 가능성 = **ASSUMPTION-23**
  │        (BUSKWIZ가 익스큐터에서 데인 함정의 시퀀스 축 재발 여부)
  │
  ┌── + 섹션 루프 (파싱 순서 N개 — 큐 번호 원장이 루프를 가로질러 살아 있다) ────┐
  │  for i, section in enumerate(sections):                                     │
  │                                                                             │
  │    = look       = 섹션 다이내믹스 → 룩            (위 = 계층이 이미 고른 것)  │
  │    + cue_no     = i + 1        ← **원장이 전진한다. 되돌아가지 않는다**      │
  │         하드 결함 1의 정체: instantiate.py:307-312 `_first_free_slot`은      │
  │         소비자가 누구든 전진하지 않는다. 섹션마다 1로 되돌아가면 N개 섹션이   │
  │         같은 큐를 덮고 **콘솔은 성공으로 답한다**                            │
  │         (instantiate.py:291-299 @MX:WARN 이 슬롯 축에서 같은 문장을 적는다)   │
  │                                          (REQ-SONGCUE-007 / AC-SONGCUE-006 ②)│
  │    + cue_name   = ASCII 섹션명 (+ 같은 이름 반복 시 순번)                    │
  │         비-ASCII 0건. 한국어는 보고 계층에만                                 │
  │                                          (REQ-SONGCUE-008 / AC-SONGCUE-007)  │
  │    = 값 라인    = instantiate._values_line (instantiate.py:286)              │
  │         `Attribute 'X' At v ; Attribute 'Y' At w` — 세미콜론 1행 연결        │
  │    + 값 라인이 앞선 섹션과 **문자열로 같으면** → 저장 **건너뛰기** + 사유     │
  │         busking.VALUE_LINE_COLLISION(:230) / _guard_collision(:240) 계승     │
  │         **거부(예외)가 아니다** — 앞 섹션은 온전하고 번들은 실행 가능하다     │
  │         근거 선례: _plan_stores(instantiate.py:325-384)는 "저장 불가" 전량을  │
  │         SkippedStore 로 답한다 (`if not values: continue` :333-334 포함)      │
  │                                          (REQ-SONGCUE-012 / AC-SONGCUE-011 ③)│
  │                                                                             │
  │    section_body = [ ClearAll,                                               │
  │                     Group <sel>,                                            │
  │                     values,                                                 │
  │                     Store Sequence <n> Cue <cue_no> '<ascii>' [CueFade <t>],│
  │                     ClearAll ]                                              │
  │         ↑ 목적지 커맨드는 섹션 본문에 넣지 않는다 (번들 선두로 올라간다)      │
  │         ↑ `[CueFade <t>]` 는 **선택형** — 사용자가 준 페이드 값이            │
  │           있을 때만 발화한다. 없으면 그 토큰 없이 나간다 (결정 E)              │
  │         ↑ Cue 1 형은 T1: audit-20260719.jsonl:186 (CueFade 있음) ·           │
  │           :148 / audit-20260722.jsonl:1057 / audit-20260726.jsonl:327 ·      │
  │           :538 (CueFade 없음) — 5건 전부 ok:true detail:"OK"                 │
  │         ? **Cue 2 이상은 T2 — 라이브 0건.** 룰북에 있으나                    │
  │           (31_choreography_patterns.md:55 `… Cue 2 … /Merge`)                │
  │           감사 로그 executed 전량에서 Cue≥2 는 0건 = **ASSUMPTION-21**        │
  │           (블로킹: 부정이면 "곡 1개 = 시퀀스 1개" 정의가 무너진다)            │
  │         ? **큐 2..N 의 발화 형태는 M0 가 실측한 리터럴 그대로다** —          │
  │           `/Merge` 를 붙이는지 여부도 **M0 실측분**이고 계획이 정하지 않는다 │
  │           룰북의 검증된 레시피(31_choreography_patterns.md:45-52)는          │
  │           `Cue 1` 전용이라 섹션 2..N 에 그 등급이 미치지 않는다              │
  │           ⇒ GO 면 **잰 그 형태로만** 발화한다        (AP-15 와 같은 규율)    │
  └─────────────────────────────────────────────────────────────────────────────┘
  │
  ├ = [번들 결합 — busking._merge (busking.py:189)]
  │      commands = [ 목적지 커맨드 ]        ← **선두 정확히 1회** (:216-218)
  │                 + section_body(1) + section_body(2) + … + section_body(N)
  │      · **`Label Sequence <n> '<ascii-song>'` 1행이 첫 섹션의 `Store` 직후에
  │        정확히 1회** 들어간다 — 곡 이름은 시퀀스 라벨로 한 번만 붙는다
  │        T1 근거: audit-20260726.jsonl:328 `Label Sequence 22 'Golden Chorus'`
  │        ok:true · 문법 00_grammar.md:27. `Label Cue` 는 룰북 0건이라
  │        쓰지 않는다                                  (§4 위험 #12 / AP-4)
  │      ⇒ 커맨드 총수 = **5S + 2** — 목적지 1 + `Label Sequence` 1 +
  │        섹션당 5행 × S. 건너뛰기로 판정된 섹션만 그만큼 짧아진다
  │      · 섹션 단위 ClearAll 은 **전량 유지** — dedupe 면제 3종에 있다
  │        (tools.py:236 `ClearAll` 패턴; 면제 집합 정의 :234-238)
  │      · 목적지 리터럴을 여기서 다시 적지 않는다. 불일치는 **예외** (:220-224)
  │      · **spans `[시작, 끝)` 를 함께 반환한다** (:209, :226)
  │        docstring(:202-206): "경계를 아는 유일한 자리가 여기다"
  │        ⇒ 섹션별 판정이 per-command status를 섹션에 귀속시키는 **유일한 정당
  │           경로**이며, 보고 계층의 재구현은 금지다              (AP-13)
  │      · `Store …` 와 값 라인은 dedupe 면제가 **아니다** (면제는 3종뿐)
  │                                          (REQ-SONGCUE-011 / AC-SONGCUE-010 ①)
  │
  ├ ? [타이밍 — M0 게이트 종속. 두 축은 **독립**이다]
  │      ASSUMPTION-20 GO  → 타임코드 트랙 발화        (REQ-SONGCUE-013)
  │                DESCOPE → 타임코드 대상 커맨드 **0건** + 사유 기록
  │      ASSUMPTION-22 GO  → Set Cue <m> Sequence <n> Property 'TrigType' <tok>
  │                          Set Cue <m> Sequence <n> Property 'TrigTime' <t>
  │                          31_choreography_patterns.md:111-112 (T2, 라이브 0건)
  │                          ※ 룰북의 실제 리터럴은 'Follow' 이고 'Time' 은
  │                            :111 주석의 토큰 메뉴에서 온 것 · :115 "Capitalized"
  │                DESCOPE → 자동 진행 커맨드 0건. 큐 시간은 CueFade 로만
  │                                                  (REQ-SONGCUE-014)
  │      금지(무조건)  → MA2형 `/trig=` (같은 파일 :115-117 이 "Illegal object"로
  │                     거부됨을 적는다)             (REQ-SONGCUE-015 / AP-15)
  │      금지(무조건)  → /Overwrite · /Remove · Delete
  │                     (`Delete` 는 블랙리스트 server/safety/blacklist.yaml:15)
  │                                                  (REQ-SONGCUE-010 / AC-SONGCUE-009)
  │
  ├ = [run_commands (tools.py:483) → bundle_gate.screen (tools.py:492)]
  │      ├(1) 프리뷰 — 스크리닝 **이전**
  │      ├(2) 게이트 3-스테이지 · **승인 카드 1장** (단일 번들 · 승인 1회)
  │      │      · 큐 이름이 본문 라인이 되는 체인(재조회 시 되돌아온다):
  │      │        console.py:478-484 (자식 name → 본문 라인)
  │      │        → expand.py:106-112 (라인마다 validate, 실패 시 **보류**)
  │      │        → grammar.py:20 `^[A-Za-z][A-Za-z0-9_+\-]*$` **ASCII 전용**
  │      │      · `Store …` 는 게이트의 어느 분기도 아니라 **safe**
  │      │        (test_safety_classify.py:63-66, :149)
  │      │      · 참조 인식 타입에 **`Cue` 가 없다** (classify.py:44 —
  │      │        Macro/Plugin/Sequence/Executor 4종). `Goto Cue <m>` 는 참조를
  │      │        추출하지 못해 **보류**된다 (test_safety_classify.py:114 이 None
  │      │        을 고정) ⇒ 본 SPEC은 `Goto Cue` 를 발화하지 않는다 (AP-16)
  │      │      · LiveLock → 제안 강등, 콘솔 송신 **0건**, is_error=False
  │      │        (게이트 보류는 is_error=True — 강등과 보류는 다른 사건이다)
  │      │                                    (AC-SONGCUE-015 ④)
  │      └(3) 결정 기록 — 스크리닝 **이후**
  │
  ├ = [콘솔 송신 — per-command status (tools.py:524-569)]
  │      executed_ok(:563) / failed / not_executed(:540) / skipped_already_executed(:554)
  │      dedupe 분기 = `command in already_executed and not _is_programmer_state(command)`
  │        (:544; 판정자 _is_programmer_state :241-244)
  │      ※ **stop-on-first-failure**: `failed = True`(:569) 이후 남은 전량이
  │        not_executed(:540, :535 가드) ⇒ 섹션 3의 실패는 섹션 4..N 을 미실행으로
  │        만든다. **건너뜀(빌드 시점)과 미실행(실행 시점)은 다른 사건**이다
  │                                          (§4 위험 #11 / AC-SONGCUE-013)
  │
  ├ = [재조회 — DataPool/Sequences/{ref} (console.py:399 경로)]
  │      돌아오는 것    : name · class · i (+ 중첩 Part 자식)
  │      돌아오지 않는 것: 커맨드 · CueFade · TrigType — **어떤 형태로도**
  │        SPEC-COPILOT-EXECREF-001/design.md:167 (라이브 실측)
  │        응답기는 Cue 를 특별 취급하지 않는다 (copilot_responder.lua 에 `Cue` 0건)
  │        주소형 특례는 Executor <n> 하나뿐 (:403 "the ONLY address form", 패턴 :405)
  │      ⇒ 검증 가능 범위 = **큐의 존재와 이름**뿐. 그 한계를 결과에 **명시**한다
  │        "확인했다"고 주장하는 프로퍼티 필드 **0건**
  │                                          (REQ-SONGCUE-017 / AC-SONGCUE-014 ② / AP-7)
  │
  └ + [집계 + **섹션별** 2단 보고 — songcue_report]
         = 사유 한국어 매핑 재사용 : report.reason_label(report.py:77 공개)
         = 판정 라벨 재사용        : report.py:74 를 감싸는 공개 접근자 1건 (§5.1 결정 I)
         + 섹션 축 : 곡의 **모든 섹션이 정확히 한 번씩** 판정에 나타난다
         + 집계 수치 = 섹션별 합 (산술 일치)
         + 판정 어휘 = 닫힌 집합
         + 한계 문구 = 프로퍼티 미관측. 정본 상수 PROPERTY_UNOBSERVED_NOTE 를
                       페이로드 키 property_unobserved 에 그대로 싣는다
                       (AC-SONGCUE-014 — 문자열 동일성 대조, 산문 대조 아님)
         + 미실행 수 = 건너뜀과 **합산 금지** (다른 사건이므로)
                                             (REQ-SONGCUE-016 / AC-SONGCUE-013)
```

**핵심 설계 목표 — 원장이 루프의 유일한 기억이고, 그 기억은 단조롭다.** 위 흐름에서 섹션 i가 섹션 i+1에 남기는 것은 오직 둘이다: **소비된 큐 번호**와 **이미 발화된 값 라인 문자열**. 리그 해석 결과(`RoleResolution` / `PoolIndex`)는 frozen인 채 읽히기만 하고, 섹션 본문은 서로를 보지 않는다. 이 형상이 AC-SONGCUE-006 구간 ②(큐 번호가 `1..N` 빠짐없이 한 번씩)를 **구조적으로** 성립시킨다 — 큐 번호가 루프 인덱스에서 오고 다른 어떤 입력도 그것을 흔들 수 없기 때문이다.

**흐름이 BUSKWIZ와 다른 지점은 정확히 셋이다.** (i) 원장의 시작값이 **리그 관측이 아니라 섹션 입력 순서**다 — BUSKWIZ의 슬롯 원장은 콘솔이 관측한 점유에서 출발해야 했지만(미관측 풀을 비었다고 가정하면 남의 프리셋을 덮는다), 큐 번호는 **새로 만드는 시퀀스** 안에서 1부터 시작하므로 관측 종속이 없다. **단, 그 시퀀스가 정말 비어 있다는 판단은 관측 종속이며 그것이 ASSUMPTION-23이다.** (ii) 값 라인 충돌 확률이 **구조적으로 더 높다** — 장르 팔레트는 서로 다른 룩 8~9개를 한 번 발화하지만, 곡은 후렴을 반복하므로 같은 룩이 같은 값 라인을 여러 번 낸다(§4 위험 #4). (iii) 산출물이 **패널 핀에 자동 연동된다** — `_STORE_SEQUENCE`(`server/orchestrator/last_created.py:30`)가 `Store Sequence <n>` 발화를 잡아 패널 핀을 만들고, 그것은 **스냅샷 전용 · 최신 1건**이다(`:17-18`). "곡 1개 = 시퀀스 1개"일 때만 정상 동작한다(§4 위험 #6).

---

## §4. 위험 검토 (False-Negative / 오작동 노출면)

| # | 위험 | 생기는 지점 (경로:줄) | 발현 조건 | 대상 AC |
|---|---|---|---|---|
| **1** | **큐 번호가 전진하지 않아 섹션 N개가 같은 큐를 덮는다 — 콘솔은 성공으로 답한다** (하드 결함 1) | `server/looks/instantiate.py:307` `_first_free_slot`(본문 `:308-312`)은 소비자가 누구든 전진하지 않고, `_plan_stores`(`:325-384`)는 읽기만 한다. 실패가 조용한 근거: `:291-299` `@MX:WARN` "MA3 reports it as success" | 섹션 루프가 큐 번호를 루프 밖 원장에서 받지 않고 매 반복 `1`(또는 고정식)로 계산할 때. **테스트가 섹션 1개짜리 픽스처만 쓰면 통과한다** — 섹션 1개에서는 `1..N`이 `1..1`이라 비전진이 드러나지 않는다 | **AC-SONGCUE-006** ②③ (`1..N` 빠짐없이 한 번씩 · 섹션 6개/10개 두 크기) |
| **2** | **값 라인이 dedupe로 탈락해 빈 프로그래머 상태로 `Store`가 실행되고 콘솔이 성공으로 답한다** | dedupe 면제는 3종뿐 — `server/orchestrator/tools.py:234-238`(`:235` `Clear` · `:236` `ClearAll` · `:237` 맨 `Fixture\|Group`). `Store …`와 값 라인은 **면제 아님**. 탈락 분기 `:544`, 상태 `skipped_already_executed` `:554`. 직전 `ClearAll`은 면제라 **살아남는다**(`:236`) | 두 섹션의 값 라인이 **문자열로 동일**할 때. 면제된 `ClearAll`이 프로그래머를 비우고, 값 라인이 탈락하고, `Store`가 빈 상태를 저장한다 — 세 줄 중 가운데만 사라지므로 커맨드 목록만 보면 정상이다 | **AC-SONGCUE-011** ①②④ · **AC-SONGCUE-010** ①(무손실 · `skipped_already_executed` 0건) |
| **3** | **한국어 큐 이름이 재조회 시 게이트 보류를 유발한다 — 생성은 성공한 뒤에 막힌다** | 체인 3단: `server/safety/console.py:478-484`(자식 `name`을 본문 라인으로 수집) → `server/safety/expand.py:106-112`(라인마다 `validate`, 실패 시 `_hold`) → `server/safety/grammar.py:20` `_VERB_SHAPE = ^[A-Za-z][A-Za-z0-9_+\-]*$` **ASCII 전용** | 큐 이름에 한글 음절이 들어간 채 그 시퀀스를 참조하는 후속 커맨드가 본문 확장을 타는 순간. **생성 시점에는 발현하지 않는다**(`Store …`는 `safe` — `server/tests/test_safety_classify.py:63-66`, `:149`) — 시간차를 두고 나타나므로 유닛 테스트가 놓친다. 한국어 큐 이름의 종단 관측은 **오프라인 목 1건뿐**(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72` `Label Cue 12 '오프닝'` `detail:"offline mock execution"`); ASCII 통과는 라이브 관측 있음(`SPEC-COPILOT-SHOWUI-001/progress.md:460` 큐 `'Blue Look'`) | **AC-SONGCUE-007** ①②③ (커맨드 전수 `isascii()` · 보고에 한글 존재 · 자산 한국어 필드 0건) |
| **4** | **후렴 반복 때문에 값 라인 충돌이 장르 팔레트보다 구조적으로 자주 밟힌다** | 가드는 있다 — `server/looks/busking.py:230` `VALUE_LINE_COLLISION`, `:240` `_guard_collision`. 값 라인 생성은 `server/looks/instantiate.py:286` `_values_line` | 같은 다이내믹스 밴드의 섹션이 둘 이상일 때. **어휘 실측이 이를 강제한다** — `server/looks/matching.py:117-130`의 `(4,5)` 밴드에 `"코러스"`(`:117`) · `"후렴"`(`:119`) · `"고조"`(`:120`) · `"드랍"`(`:121`) · `"클라이맥스"`(`:123`) · `"절정"`(`:125`) · `"최고조"`(`:126`) · `"엔딩"`(`:127`) · `"피날레"`(`:129`)가 **전부 들어 있다.** 즉 후렴 3회 + 드랍 + 엔딩인 흔한 곡 구조는 같은 밴드를 **5회 이상** 요구하고, 같은 룩이 배정되면 값 라인도 같아진다. 밴드가 넓은 것은 의도된 설계다(`:114-116` 주석) — 필터로서 옳고 곡 축에서 충돌을 늘리는 것은 그 설계의 부수 결과다. BUSKWIZ는 서로 다른 룩 8~9개를 1회씩 발화해 이 경로가 자산 실측 0건이었다 | **AC-SONGCUE-011** ①②③④ · **AC-SONGCUE-013**(건너뛴 섹션이 판정에 나타남) |
| **5** | **생성한 초안을 앱이 스스로 검증할 수 없다 — 프로퍼티가 어떤 형태로도 노출되지 않는다** | 라이브 실측: `SPEC-COPILOT-EXECREF-001/design.md:167` — `DataPool/Sequences/<n>/<m>`은 `name`/`class`/`i`(+ 중첩 `Part`)만 반환. 조회 경로 `server/safety/console.py:399`. 응답기는 `Cue`를 특별 취급하지 않고(`console/lua/copilot_responder.lua`에 `Cue` 0건) 주소형 특례는 `Executor <n>` 하나뿐(`:403`, 패턴 `:405`). `console/lua/**`는 PRESERVE | 항상. **위험의 발현은 콘솔이 아니라 보고에서 일어난다** — 재조회가 큐 존재·이름만 준 채 보고가 "`CueFade` 4초로 설정됨"을 적으면, 관측하지 않은 것을 관측했다고 주장한 것이다 | **AC-SONGCUE-014** ①② (프로퍼티 확인 주장 필드 **0건** · 한계 문구 존재) |
| **6** | **`last_created` 스냅샷은 최신 1건뿐이라 곡 2개 이상이 한 번들에 들어오면 앞 곡의 핀이 조용히 사라진다** | `server/orchestrator/last_created.py:30` `_STORE_SEQUENCE`가 `Store Sequence <n>` 발화를 자동으로 패널 핀에 연동한다. `:17-18`이 "snapshot-only … the SINGLE most-recent look, never an accumulating history"라고 명시 | 한 번들에 `Store Sequence` 발화가 2회 이상일 때. **"곡 1개 = 시퀀스 1개"(REQ-SONGCUE-007)를 지키면 발현하지 않는다** — 즉 이 요구는 산출물 형상만이 아니라 **패널 연동의 전제**다. 반대로 `Store Cue 1 Sequence 71` 형태는 시퀀스 생성으로 읽히지 **않으므로**(`:27-29` 주석 + `server/tests/test_last_created.py:58-61`이 고정) 큐 저작 문법을 그쪽으로 바꾸면 핀이 아예 생기지 않는다 | **AC-SONGCUE-006** ①(시퀀스 번호가 정확히 1종) |
| **7** | **`Goto Cue <m> Sequence <n>`은 게이트가 참조를 추출하지 못해 보류된다 — 섹션 점프 UX는 문법 문제가 아니다** | `server/safety/classify.py:44` `RECOGNIZED_REFERENCE_TYPES = ("Macro","Plugin","Sequence","Executor")` — **`Cue` 없음**. `server/tests/test_safety_classify.py:114`가 `("Goto Cue 3", None)`을 고정. 룰북에는 형식이 있다 — `31_choreography_patterns.md:100` 주석의 `Goto Cue 2 Sequence 11`. 과보류 인정 선례 `SPEC-COPILOT-MVP-001/progress.md:215` | 본 SPEC이 섹션 점프를 편의로 얹으려 할 때. **발현 형태가 함정이다** — 커맨드가 거부되는 게 아니라 승인 대기로 **보류**되므로, "동작하지만 매번 사람을 부른다"가 되어 기능처럼 보인다 | **AC-SONGCUE-009** ①② (생성 커맨드 튜플 전수 스캔 + 비공허성 — `Goto Cue` 발화 0건) |
| **8** | **시퀀스 번호 여집합 오판 — "존재하지 않음"을 "비어 있음"으로 읽는다** | 열거가 주는 것은 **존재하는** 시퀀스뿐(경로 `server/safety/console.py:399`). BUSKWIZ가 익스큐터 축에서 같은 함정에 데였고 그 판정이 ASSUMPTION-23의 근거다. 라이브 실측: 실기 번호가 비연속이었다 — `1,2,11~16,30,41,50,62,71,80`, `3~10·17~29` 부재(`SPEC-COPILOT-SHOWUI-001/progress.md:465`) | 열거가 **절단**되었거나 조회가 실패했는데 그 신호를 소비하지 않을 때. 잘린 목록의 여집합은 잘린 만큼 낙관적이고, 그 번호로 `Store`하면 남의 시퀀스에 큐를 얹는다. 비연속 실측이 위험을 키운다 — 여집합이 넓어 보이므로 "아무 빈 번호나" 고르려는 압력이 생긴다 | **AC-SONGCUE-008** ①②(픽스처를 바꾸면 선택이 따라 바뀜 · 실패·절단 시 추측 금지 거부) |
| **9** | **ASSUMPTION-21 부정은 DESCOPE가 아니라 저작 차단이다 — 라이브 `Cue ≥2`가 0건이다** | 룰북에는 있다(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:55` `Store Sequence 11 Cue 2 'Blue Wash' CueFade 2 /Merge`)이고 그 파일은 라이브 선언을 갖는다(`:7` "Every pattern below was validated live on onPC 2.4.2"). 그러나 **`server/audit_logs/*.jsonl`의 `executed` 이벤트 전량에서 `Cue ≥2`는 0건**(직접 스캔)이고, T1 5건은 전부 `Cue 1`이다(`audit-20260719.jsonl:148`, `:186`, `audit-20260722.jsonl:1057`, `audit-20260726.jsonl:327`, `:538`). `Cue 12` 계열은 전부 오프라인 목(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73` `detail:"offline mock execution"`) | M0에서 `Cue 2 … /Merge`가 실패하면 **"섹션 1개 = 큐 1개"가 성립하지 않는다.** 다른 전제와 달리 축을 잘라 진행할 수 없다 — 산출물 정의 자체(REQ-SONGCUE-007)가 무너지므로 M3를 착수할 수 없다 | **AC-SONGCUE-017** 측정 1 (블로킹 — 부정이면 M3 미착수) |
| **10** | **`TrigType` 리터럴 치환 — 룰북이 검증한 것은 `'Follow'`이고 `'Time'`은 주석의 토큰 메뉴에서 왔다** | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:111`이 `Set Cue 1 Sequence 11 Property 'TrigType' 'Follow'`이고 `'Time'`은 **같은 줄 주석**의 `Go / Time / Follow / Sound / BPM` 목록 항목이다. `:115`가 "Trigger tokens are Capitalized (`Follow`, not `follow`)"를 명시. 절 제목 `:106`·선언 `:108`은 "validated form"/"validated on 2.4.2"라 적지만 **감사 로그 실행 기록은 0건**(T2) | M0가 `'Follow'`만 재고 GO를 선언한 뒤 구현이 `'Time'`을 발화할 때. 시간 기반 진행이 본 SPEC이 실제로 원하는 토큰이므로 이 치환은 자연스러워 보인다 — 그러나 **잰 것과 발화하는 것이 다르면 GO는 그 발화를 덮지 않는다.** 소문자 발화는 `:115`가 별도로 막는다 | **AC-SONGCUE-012** ③(발화 형식이 **M0가 실측한 것 하나뿐**) |
| **11** | **stop-on-first-failure가 섹션 중간에서 곡을 끊고, 그 결과가 "건너뜀"과 한 칸에 합산된다** | `server/orchestrator/tools.py:569` `failed = True` 이후 남은 전량이 `not_executed`(`:540`, 가드 `:535`). 빌드 시점 판정(값 라인 충돌 건너뛰기 — `server/looks/busking.py:240`)과 실행 시점 귀결은 **다른 사건**이다 | 섹션 k의 어느 줄이 실패하면 섹션 k+1..N이 전부 미실행이 된다. 보고가 두 수를 합치면 "3개 섹션 실패"가 되어 **원인이 사라진다** — 하나는 저작 결함이고 하나는 중도 중단이다. BUSKWIZ가 요소 (e)를 신설해 같은 문제를 닫았다 | **AC-SONGCUE-013** ①②(모든 섹션이 정확히 한 번씩 · 집계 = 섹션별 합) |
| **12** | **`Label Cue <n> '<name>'` 독립 동사는 룰북 0건 — 목 픽스처에만 있고 그 형태는 문법 위반이다** | 룰북 `v2.4.2/` 전체에 `Label Cue` **0건**. 유일 등장은 `server/measurement/corpus.yaml:69` `Label Cue 12 "Opening"`이고 그 블록은 스스로 "the deterministic offline action for M6a mock runs ONLY"라 한정한다(`:7-10`). **게다가 큰따옴표**를 쓰는데 `server/rulebook/assets/v2.4.2/00_grammar.md:26-29`가 생성 커맨드에서 이를 금지한다(전송이 커맨드 라인을 큰따옴표로 감싸므로 내장 큰따옴표는 커맨드를 깨뜨린다). 시퀀스 축에는 T1이 있다 — `Label Sequence 22 'Golden Chorus'` ok:true(`server/audit_logs/audit-20260726.jsonl:328`, 문법 `00_grammar.md:27`) | 큐 이름을 store와 분리해 붙이려 할 때. 목을 베끼면 **문법 위반형을 베낀다.** 큐 이름을 확정할 수 있는 유일한 T1 경로는 **store 인라인 3번째 토큰**이다 | **AC-SONGCUE-009** ①② · **AC-SONGCUE-007**(이름이 커맨드에 실제로 실린다) |
| **13** | **타임코드가 T5(저장소 전체 0건)라서 "우회 생성"의 압력이 크다** | 룰북 5파일 · `server/**` · `console/lua/**` 전량 무매치(직접 스캔). 유일 등장은 외부 참고 링크 텍스트 `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:125`, `:127`. 별도 Marker/Mark 오브젝트도 룰북 `v2.4.2/` 전체 0건 — 제안서가 적은 "섹션 마커"(`:71`)의 실체는 큐 이름 문자열뿐 | M0가 ASSUMPTION-20을 부정한 뒤 "시퀀스를 더 만들어 시간축을 흉내낸다"로 넘어갈 때. **DESCOPE가 답이다** — 우회는 시퀀스 저작을 암묵적으로 확장하고, 그 순간 위험 #6(패널 핀 스냅샷 최신 1건)이 함께 발현한다 | **AC-SONGCUE-012** ②(타임코드 대상 커맨드 0건 + 사유 기록) · **AC-SONGCUE-017** 비고(우회 금지) |
| **14** | **`_merge`의 목적지 불일치 예외가 곡 전량을 죽인다 — 충돌 가드와 성격이 반대다** | `server/looks/busking.py:220-224`가 `commands[0] != destination`이면 `LookInstantiationError`를 **raise**한다. 반면 값 라인 충돌은 예외가 아니라 건너뛰기다(`:240`) | 섹션 본문이 목적지 커맨드를 저마다 다른 문자열로 갖게 될 때(예: 일부 섹션만 목적지를 본문에 넣음). 두 실패 정책이 한 모듈에 있으므로 **어느 것이 어느 조건에 붙는지 혼동하면** 저작 결함 하나로 곡 전체가 0건이 된다 | **AC-SONGCUE-011** ③(거부가 아니라 건너뛰기 · 앞 섹션 온전) · **AC-SONGCUE-010** ①(목적지 선두 1회) |
| **15** | **시퀀스 자동 생성이 T2이고, 그것을 T1 정황으로 대체하려는 압력이 있다** | 룰북 `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:54` "The sequence auto-creates on the first store" — 라이브 선언 파일이지만 그 문장 자체의 실행 기록은 없다. 정황은 강하다: T1 5건이 **전부 신규 번호**(62 / 30 / 90 / 22 / 17)에서 성공했다 | 정황을 근거로 ASSUMPTION-23 측정을 생략할 때. **정황은 "번호가 새것이었다"를 말하고 측정은 "그 번호가 비어 있었음을 알 수 있었나"를 묻는다** — 앞의 것이 뒤의 것을 증명하지 않는다. 5건 전부 사람이 골라 준 번호였을 수 있다 | **AC-SONGCUE-017** 측정 2 (ASSUMPTION-23) · **AC-SONGCUE-008** ② |

### 위험 상세

**위험 #1·#4 상세 — 두 결함은 같은 루프에 살지만 서로를 가린다.** 큐 번호 비전진(#1)과 값 라인 충돌(#4)은 증상이 겹친다: 둘 다 "섹션 N개를 넣었는데 큐가 N개보다 적다"로 나타난다. 그러나 원인과 조치가 반대다. 비전진은 **커맨드가 N개 나갔는데 콘솔에서 서로를 덮은** 것이라 커맨드 목록만 보면 정상이고 재조회에서만 드러난다. 충돌은 **커맨드 자체가 N개보다 적게 만들어진** 것이라 빌드 시점에 이미 판정되어 있고 사유가 붙는다. 두 실패 모드를 한 테스트에 묶으면 둘 다 통과한다 — 그래서 §6.2가 이들을 분리하고, AC-SONGCUE-006 ②는 **커맨드에서 추출한 `(시퀀스, 큐)` 집합**을, AC-SONGCUE-011은 **건너뜀 사유의 존재**를 각각 본다.

**곡 자산이 이 겹침을 강제한다는 점이 BUSKWIZ와의 결정적 차이다.** 어휘 실측: `server/looks/matching.py`의 `(4,5)` 밴드는 `:117-130`에 걸쳐 있고 그 안에 `"코러스"`(`:117`) · `"chorus"`(`:118`) · `"후렴"`(`:119`) · `"고조"`(`:120`) · `"드랍"`(`:121`) · `"drop"`(`:122`) · `"클라이맥스"`(`:123`) · `"climax"`(`:124`) · `"절정"`(`:125`) · `"최고조"`(`:126`) · `"엔딩"`(`:127`) · `"ending"`(`:128`) · `"피날레"`(`:129`) · `"finale"`(`:130`)가 **전부** 들어 있다 — **한국어 9종 · 영어 5종, 합 14항목이 한 밴드다**(영·한 짝은 `코러스`↔`chorus` · `드랍`↔`drop` · `클라이맥스`↔`climax` · `엔딩`↔`ending` · `피날레`↔`finale` 5쌍이고, 한국어 `후렴` · `고조` · `절정` · `최고조` 4종은 대응 영어 항목 없이 단독 등재되어 있다 — 그래서 한국어가 4종 많다). 따라서 `Chorus / Chorus / Drop / Chorus / Ending`처럼 **완전히 평범한 곡 구조**가 같은 다이내믹스를 5회 요구하고, 같은 룩이 배정되면 값 라인 문자열도 같아진다. **밴드가 넓은 것 자체는 옳은 설계다** — `:114-116` 주석이 이유를 적는다("the library authored an EDM drop at 4 … so a single-level band here would hide a look the user plainly asked for"), 그리고 모듈 독스트링이 "this table FILTERS, and an over-narrow filter drops a good look silently"라고 그 방향을 못 박는다(`:22-25`). 즉 충돌 빈도는 결함이 아니라 **필터 설계의 부수 결과**이고, 그래서 답은 밴드를 좁히는 것(AP-8)이 아니라 건너뛰기 가드다(결정 H). BUSKWIZ에서 이 경로의 자산 발현이 0건이었던 이유는 장르 팔레트가 서로 다른 룩을 1회씩만 발화했기 때문이고, 곡에는 그 보호가 없다.

**위험 #3 상세 — 사전 확정 ③은 스타일 규칙이 아니라 실행 경로 결정이다.** 근거의 구조를 정확히 적는다. (i) **생성 시점에는 한국어가 통과한다** — `Store …`는 게이트의 invoking도 blacklisted도 아니라 `safe`이고(`server/tests/test_safety_classify.py:63-66`, `:149`) 이름은 단일 인용부호 안의 토큰일 뿐이다. 그래서 "한국어로 넣어 봤는데 됐다"는 관측이 나올 수 있다. (ii) **막히는 지점은 재조회다** — 그 시퀀스를 참조하는 후속 커맨드가 본문 확장을 타면 `server/safety/console.py:478-484`가 큐 이름을 **본문 라인으로** 수집하고, `server/safety/expand.py:106-112`가 라인마다 `validate`를 걸며, `server/safety/grammar.py:20`의 선두 토큰 규칙이 ASCII 전용이다. 실패는 거부가 아니라 **보류**다. (iii) **증거의 비대칭이 결정적이다** — ASCII는 종단 라이브 관측이 있고(`SPEC-COPILOT-SHOWUI-001/progress.md:460`: 큐 `'Blue Look'`을 담은 `Sequence 90`에 `Go+`/`Off` 둘 다 `ok=True`), 한국어 큐 이름은 **오프라인 목 1건**뿐이다(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72`). 목은 콘솔 수용을 주장하지 않는다(`server/measurement/corpus.yaml:7-10`이 스스로 한정한다). 즉 한국어 선택은 "아마 될 것"에 산출물을 거는 것이고, 실패가 조용한 영역에서 그 거래는 항상 나쁜 거래였다.

**위험 #5 상세 — 검증 불가는 결함이 아니라 경계이고, 경계는 문장으로만 지킬 수 있다.** 응답기 확장이 필요하다는 것은 이미 규명되어 있으나 `console/lua/**`는 PRESERVE이고 응답기 확장은 그 자체로 별도 범위 결정이다. 그래서 본 SPEC이 할 수 있는 일은 **한계를 결과 페이로드에 명시**하는 것이고(REQ-SONGCUE-017), AC-SONGCUE-014 ②가 그것을 **부정형으로** 고정한다 — "프로퍼티를 확인했다고 주장하는 필드가 0건". 부정형이어야 하는 이유는 긍정형 assert가 통과하기 쉽기 때문이다: "한계 문구가 있다"는 문자열 하나로 충족되지만, "확인 주장 필드가 없다"는 구현이 낙관적 필드를 하나라도 추가하면 즉시 깨진다. 같은 이유로 M7의 증거는 **툴 자신의 목록이 아니라 감사 로그**여야 한다 — 툴이 "만들었다"고 적은 목록은 툴의 주장이고, 감사 로그는 콘솔이 답한 기록이다.

**위험 #9 상세 — 블로킹과 DESCOPE의 구분은 형식이 아니다.** ASSUMPTION-20(타임코드)과 ASSUMPTION-22(`TrigType`)가 부정이면 그 **축만** 잘리고 나머지 산출물은 그대로 선다 — 큐리스트는 여전히 시퀀스 1개 + 큐 N개이고 시간은 `CueFade`로 표현된다. ASSUMPTION-21은 다르다. `Cue 2` 이상을 같은 시퀀스에 추가할 수 없다면 남는 선택은 둘뿐이고 **둘 다 산출물 정의를 바꾼다**: 섹션마다 시퀀스를 따로 만들면 "곡 1개 = 시퀀스 1개"(REQ-SONGCUE-007)가 깨지고 동시에 위험 #6(패널 핀 스냅샷 최신 1건)이 발현한다; 큐를 1개만 만들면 "섹션 1개 = 큐 1개"가 깨진다. 그래서 이것은 축소가 아니라 **저작 차단**이고, AC-SONGCUE-017 측정 1이 "부정이면 M3 저작을 착수하지 않는다"를 적는다. 실측이 이 위험을 뒷받침한다 — 라이브 `Cue ≥2`가 감사 로그 전량에서 0건이고, 룰북의 라이브 선언(`31_choreography_patterns.md:7`)은 **파일 단위 선언**이라 그 파일의 모든 줄이 개별로 실행되었음을 뜻하지 않는다. 이 구분은 BUSKWIZ가 이미 값을 치르고 배운 것이다: 같은 파일의 익스큐터 문법 3건이 M0에서 전부 DESCOPE로 판정됐다.

**위험 #10 상세 — "검증된 형식"이라는 낱말이 리터럴 하나를 가린다.** 룰북 절 제목이 "Self-running / auto-advance cues — **validated form**"(`31_choreography_patterns.md:106`)이고 본문이 "Use the PROPERTY form (**validated on 2.4.2**)"(`:108`)라 적으므로, 이 구간은 문서상 가장 자신 있는 표현을 쓴다. 그런데 예시가 실제로 적은 리터럴은 **`'Follow'`** 하나이고(`:111`), `'Time'`은 그 줄 주석의 토큰 메뉴 항목이다. 본 SPEC이 원하는 것은 시간 기반 진행이므로 `'Time'`을 쓰고 싶어지고, 인계 브리핑도 `'Time'`으로 적혀 있었다(위 앵커 정정 표의 `TrigType` 행). **잰 것과 발화하는 것이 다르면 GO는 그 발화를 덮지 않는다.** 따라서 M0 측정 항목은 "`Set Cue … Property 'TrigType' …`가 수용되는가"가 아니라 **"본 SPEC이 발화할 정확한 리터럴이 수용되는가"**여야 하고, 파싱 성공과 효과 발생을 구분해 기록해야 한다(`Cmd()`가 거부된 커맨드에도 OK를 보고한 실측 사례가 BUSKWIZ M0에 있다). 부수적으로 `:115`가 토큰 대문자 규칙을 적으므로 소문자 발화는 별도 실패 경로다.

**위험 #12 상세 — 목 픽스처는 두 겹으로 틀렸고, 그래서 유혹이 크다.** `server/measurement/corpus.yaml:69`의 `Label Cue 12 "Opening"`은 (i) 스스로 오프라인 목 전용이라 선언한 블록에 있고(`:7-10`), (ii) **큰따옴표를 쓴다** — `server/rulebook/assets/v2.4.2/00_grammar.md:26-29`가 생성 커맨드에서 이를 금지하는 이유는 전송이 커맨드 라인을 큰따옴표로 감싸기 때문이므로, 그대로 발화하면 커맨드가 깨진다. 목 실행 기록은 이 형태를 단일 인용부호 + 한국어로 렌더했고(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72` `Label Cue 12 '오프닝'`) 그것 역시 `detail:"offline mock execution"`이다. 유혹이 큰 이유는 시퀀스 축에 **동형의 T1이 있기** 때문이다 — `Label Sequence 22 'Golden Chorus'`가 `ok:true`로 실행됐다(`server/audit_logs/audit-20260726.jsonl:328`, 문법 근거 `00_grammar.md:27`). "시퀀스에 되니까 큐에도 될 것"은 그럴듯하지만 룰북에 `Label Cue`가 **0건**이라는 사실을 대체하지 않는다. 큐 이름을 확정하는 유일한 T1 경로는 `Store Sequence <n> Cue <m> '<name>'`의 **인라인 3번째 토큰**이며, 그 형은 5건이 실행됐다.

---

## §5. 설계 슬롯

### §5.0 대응 관계 (plan.md의 결정 집합과의 정직한 기술)

**대응은 1:1이다** — plan.md `§A.4a` 결정 **10건(A~J)** ↔ 본 문서 §5.1 항목 **10건(A~J)**, 문자와 순서가 같다. 열린 항목은 양쪽 모두 **0건**이며, 따라서 "표시 없이 게이트를 통과하는 결정"이 존재할 수 없다.

이 1:1은 자연히 성립한 것이 아니라 **선례의 실패를 피해 설계된 것**이다. LOOKLIB v0.1.0은 "슬롯 A~F ↔ 표시 6건이 1:1"이라 주장했으나 거짓이었고, 특히 역할 어휘 폐쇄 집합 슬롯은 **대응 표시가 없어** Kickoff 게이트를 통과하지 않고 구현 단계로 흘러갔다(`SPEC-COPILOT-LOOKLIB-001/design.md:97-108`). BUSKWIZ는 착수 시점에 결정 7건을 전부 닫아 그 구조를 차단했고, 본 SPEC은 같은 방식으로 10건을 닫는다:

1. **착수 시점에 열린 결정을 만들지 않는다.** 사용자 확정 3건(A · B · C)과 엔지니어링 판단 7건(D~J)으로 10건 전부가 spec.md 작성 시점에 폐쇄되었다. **폐쇄 경로 분류는 plan.md `§A.4a`의 정본을 그대로 쓴다** — E와 H처럼 요구 토큰(REQ-SONGCUE-007 · REQ-SONGCUE-012)이 근거로 붙는 항목도 **폐쇄 경로는 엔지니어링 판단**이다(요구가 결정을 기록한 것이지 결정을 대신 내린 것이 아니다). "M1 설계 산출물로 확정"처럼 게이트 뒤로 미룬 항목이 **0건**이다.
2. **미확정으로 남는 것은 결정이 아니라 측정이다.** ASSUMPTION-20~24는 설계 슬롯이 아니라 **라이브 실측 대상**이며, 그 판정에 따른 결과가 **미리 정의되어** 있다. 정의된 두 결과 사이의 분기는 열린 슬롯이 아니다 — 열린 슬롯은 "결과를 아직 모른다"가 아니라 **"결과를 정하지 않았다"**를 뜻하기 때문이다.

### §5.1 해소된 결정 (fold-in 완료 — 10건, 재질의 금지)

| 결정 | 확정 | 근거 요약 |
|---|---|---|
| **A. 음원 분석의 위치** | **범위 밖.** 섹션 목록은 **사용자가 제공**한다(DAW 마커 텍스트 또는 구조화 입력) | **사용자 확정 ①.** 오디오 분석 의존성이 저장소에 **0건**이고(`pyproject.toml:8-18`, `uv.lock` **58패키지** 전량 무매치 — numpy조차 없다), 파일 업로드 경로도 **0건**이며(`server/web/app.py:311` `receive_text()` 텍스트 전용, FastAPI 라우트 8개 전량에 `UploadFile` 없음, `ui/src/**`에 `input[type=file]` 0건), Tauri capability가 `no upload`를 **명시적으로 거부**한다(`src-tauri/capabilities/default.json:4`, 테스트가 강제: `server/tests/test_deploy_tauri_shell.py:347-351`). 함께 열면 신규 의존성 + 업로드 경로 + 진행률 프로토콜(현재 0건) 세 축이 동시에 열린다. **별도 SPEC** (spec.md §D) |
| **B. 타임코드와 자동 진행** | **M0 라이브 프로브 GO/DESCOPE 게이트.** ASSUMPTION-20(타임코드)과 ASSUMPTION-22(`TrigType`/`TrigTime`)는 **독립**이며 각각 자기 축만 자른다 | **사용자 확정 ②.** 타임코드는 **T5** — 룰북 5파일 · `server/**` · `console/lua/**` 전량 무매치이고 유일 등장은 외부 링크 텍스트(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:125`, `:127`). `TrigType`은 **T2** — `31_choreography_patterns.md:111-112`에 있고 절 제목 `:106`·선언 `:108`이 "validated"라 적지만 감사 로그 실행 기록 0건이며 **실제 리터럴은 `'Follow'`**(§4 위험 #10). MA2형 `/trig=`는 같은 파일 `:115-117`이 금지한다(REQ-SONGCUE-015). **DESCOPE는 실패가 아니라 정의된 결과다** — BUSKWIZ의 익스큐터 축 선례. 우회 생성은 AP-5가 막는다 |
| **C. 큐 이름의 문자 집합** | **ASCII 고정 + 한국어는 표현 계층 매핑.** 자산·스키마에 한국어 필드를 추가하지 않는다 | **사용자 확정 ③.** 큐 이름은 표현이 아니라 **실행 경로의 일부**다 — `server/safety/console.py:478-484` → `server/safety/expand.py:106-112` → `server/safety/grammar.py:20`(`^[A-Za-z][A-Za-z0-9_+\-]*$` ASCII 전용). ASCII 종단 통과는 라이브 관측(`SPEC-COPILOT-SHOWUI-001/progress.md:460`), 한국어는 **오프라인 목 1건**뿐(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72`). 표현 계층은 BUSKWIZ가 세운 형상을 그대로 쓴다(`server/looks/report.py:63`, `:74`, 공개 접근자 `:77`). §4 위험 #3 |
| **D. 라이브 세션 회계** | **2회** — M0 프로브(코드 변경 0) + M7 종단 | **엔지니어링 판단 + acceptance.md §C.0.** M0는 정의상 M3보다 앞서야 한다 — ASSUMPTION-21이 미확정이면 산출물 정의 자체가 미정이므로 **저작을 시작할 수 없다**(§4 위험 #9). M7은 정의상 M6보다 뒤여야 하므로 **합칠 수 없다**. **정직한 회계 주의**: LOOKLIB의 계획 2회는 실제 3회가 되었고 이탈 원인은 배선 결함이었다. 본 SPEC의 2회도 같은 성격의 **하한**이며, AP-19와 §6.1의 진입점 규율이 그 재발 경로를 직접 겨냥한다 |
| **E. 산출물 형상** | **곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개.** 큐 번호는 섹션 입력 순서대로 `1`부터 | **엔지니어링 판단 + REQ-SONGCUE-007.** 실무 표준이자 제안서의 산출물 정의(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:71`)이며, **패널 핀 연동의 전제**이기도 하다 — `server/orchestrator/last_created.py:30`이 `Store Sequence <n>`을 자동 연동하고 `:17-18`이 스냅샷 최신 1건임을 명시하므로, 곡 2개가 한 번들에 들어오면 앞 곡의 핀이 사라진다(§4 위험 #6). T1 근거 5건이 모두 이 형(`Store Sequence <n> Cue 1 '<name>'`)이다. **ASSUMPTION-21이 이 형상의 블로킹 전제**이며 부정이면 M3 저작이 차단된다(§4 위험 #9) |
| **F. 큐 번호 원장** | **섹션 루프를 가로지르는 누적 원장.** frozen 자료구조를 **바깥에서** 감싼다. 번호는 전진하고 **건너뜀에도 당기지 않는다** | **엔지니어링 판단.** spec.md §A 하드 결함 1의 유일한 해소 경로다 — `_first_free_slot`(`server/looks/instantiate.py:307`)에 전진이 없고 `_plan_stores`(`:325-384`)는 읽기만 한다. BUSKWIZ가 슬롯 축에서 같은 형상을 썼다(`server/looks/busking.py:158` `_advance`가 frozen `PoolIndex`를 새 객체로 갈아 끼운다). **시간축 판본은 더 단순하다** — 시작값이 리그 관측이 아니라 섹션 입력 순서이므로 원장은 `i + 1` 전순서를 갖는다. "당기지 않는다"는 AC-SONGCUE-006과 AC-SONGCUE-011이 **동시에 참이 되는 유일한 형상**이다. `instantiate.py`를 고치게 되는 것이 곧 **이 결정의 반증**이므로 PRESERVE에 넣는다(§2) |
| **G. 번들 결합과 dedupe** | **`busking._merge` 형상 계승 · dedupe 규칙 무개정.** 목적지 커맨드 선두 1회, 섹션 단위 `ClearAll` 전량 유지 | **엔지니어링 판단.** 면제 집합은 3종뿐이고(`server/orchestrator/tools.py:234-238`) `Store …`와 값 라인은 면제가 아니다. 룰북이 선두 1회를 **규범으로** 적으므로(`31_choreography_patterns.md:11` "issue exactly once at the start of the bundle") 이 형상은 우회가 아니라 준수다. `ClearAll`은 면제이므로(`:236`) 접지 않아도 손실이 0이다. **면제 확장은 `run_commands`를 쓰는 모든 소비자의 전역 실행 의미론을 바꾼다** — 본 SPEC 하나를 위해 그 거래를 하지 않는다(spec.md §D, AP-6) |
| **H. 값 라인 충돌의 처리** | **거부(예외)가 아니라 건너뛰기 + 사유 보고.** 뒤 섹션의 저장만 빠지고 앞 섹션은 온전하다 | **엔지니어링 판단 + REQ-SONGCUE-012 · BUSKWIZ 결정 H 계승**(그 SPEC 로컬 문자 배정이며 본 문서의 문자와 우연히 같다)**.** 근거 선례는 `_plan_stores`가 "저장 불가" 전량을 `SkippedStore`로 답한다는 것이다(`server/looks/instantiate.py:325-384`, `if not values: continue` `:333-334` 포함) — `LookInstantiationError`는 구조적 기형에만 쓴다. 섹션 하나의 충돌로 곡 전량을 실패시키면 큐리스트가 아무 산출도 내지 못한다. **곡에서 이 경로가 자주 밟히는 것이 결정을 강화한다** — 어휘 실측상 `(4,5)` 밴드(`server/looks/matching.py:117-130`)에 `"코러스"` · `"후렴"` · `"고조"` · `"드랍"` · `"클라이맥스"` · `"절정"` · `"최고조"` · `"엔딩"` · `"피날레"`가 전부 들어 있어, 평범한 곡 구조가 같은 밴드를 5회 이상 요구한다(§4 위험 #4) |
| **I. 보고 계층의 배치** | **신규 `songcue_report.py` + `report.py`에 공개 접근자 1건 추가.** 한국어 어휘는 재정의 0건 | **엔지니어링 판단.** 집계 단위가 다르다 — BUSKWIZ의 판정 단위는 `(룩, 역할)`이고 본 SPEC의 단위는 **섹션**이므로, 한 모듈에 넣으면 BUSKWIZ 테스트가 고정한 `BuskingReport` 계약(`server/looks/report.py:116`)을 건드린다. 사유 라벨은 이미 공개된 `reason_label`(`:77`)을 import하고, 판정 라벨은 `_VERDICT_LABELS`(`:74`)를 감싸는 공개 접근자 1개를 더해 재사용한다 — **어휘를 복제하지 않는 것이 접근자 추가보다 비싼 대안이다.** 같은 한국어가 두 파일에 살면 한쪽만 갱신되는 순간 거짓이 된다(`server/looks/busking.py:75-77`이 상수 복제를 거부하며 적는 논리). 추가는 비파괴이며 기존 호출자에 영향이 없다 — 따라서 `report.py`는 **"무변경"이 아니라 "비파괴 1건 추가"**다. 섹션별 판정의 경계는 **`_merge`가 반환하는 spans**(`:209`, `:226`; docstring `:202-206`)에서만 오고 재구현하지 않는다(AP-13) |
| **J. 섹션 어휘 · 다이내믹스의 출처** | **`matching.py`에서 import.** 본 SPEC은 어휘를 재정의하지 않고 **다이내믹스 밴드(튜플)를 점값으로 좁히지도 않는다** | **엔지니어링 판단 + REQ-SONGCUE-003.** 정본은 `server/looks/matching.py:92` `DYNAMICS_TERMS`(항목 전체 `:94-130`)이고 범위 상수는 `server/looks/schema.py:35-36`이다. 재정의하면 한/영 어휘가 두 곳에 살고 그 순간 갈라진다 — `server/looks/schema.py:20-25`의 `@MX:NOTE`가 이 스키마를 P1-1/P1-2 **공통 기반**으로 못 박았으므로 한쪽만 갱신되는 것은 두 SPEC을 동시에 깨는 일이다. 밴드를 점값으로 좁히는 것도 같은 위반이다 — 그 파일의 독스트링(`:22-25`)이 "this table FILTERS, and an over-narrow filter drops a good look silently"라고 그 방향을 이미 거부한다. 검증은 raw grep이 아니라 **AST 스캔**이다(산문이 어휘를 설명할 수 있다 — AC-SONGCUE-003, AP-11) |

### §5.2 열린 슬롯 — **0건**

**이 문서에 열린 설계 슬롯은 0건이고, 미해소 질의 표시도 0건이다.** LOOKLIB은 슬롯 6건 → 3건 → 0건에 이르는 동안 두 번의 감사 FAIL(0.65 / 0.80)을 소비했고, BUSKWIZ는 착수 시점부터 0건에서 출발했다. 본 SPEC은 사용자 확정 3건(A · B · C) · 엔지니어링 판단 7건(D~J)으로 같은 상태에서 출발한다. (개수를 주장하는 이 문장은 그 표시 토큰 자체를 적지 않는다 — 적으면 문장이 스스로 스캔에 걸려 주장을 거짓으로 만든다. LOOKLIB AP-19의 "검증 수단이 주장을 검사하지 못할 때 낮출 것은 주장이 아니라 수단의 조악함이다"와 같은 자리에서 방향만 반대다.)

**남아 있는 미확정은 결정이 아니라 측정 5건**(ASSUMPTION-20 · 21 · 22 · 23 · 24)이며, 각각의 결과가 미리 정의되어 있다:

| 전제 | 등급 | 부정 시 정의된 결과 | 성격 |
|---|---|---|---|
| ASSUMPTION-20 (타임코드) | **T5** — 저장소 전체 0건 | REQ-SONGCUE-013 DESCOPE. 타임코드 대상 커맨드 0건 + 사유 기록 | 축 절단 |
| ASSUMPTION-21 (같은 시퀀스 `Cue ≥2`) | **T2** — 라이브 실행 0건 | **DESCOPE가 아니라 M3 저작 차단.** 산출물 정의(REQ-SONGCUE-007)가 성립하지 않는다 | **블로킹** |
| ASSUMPTION-22 (`TrigType`/`TrigTime`) | **T2** — 라이브 실행 0건, 실제 리터럴은 `'Follow'` | REQ-SONGCUE-014 DESCOPE. 자동 진행 0건, 시간은 `CueFade`로만 | 축 절단 |
| ASSUMPTION-23 (빈 시퀀스 번호 식별) | 열거는 **존재하는 것만** 준다(라이브 비연속 실측 있음) | 여집합 신뢰 불가 → **번호를 추측하지 않고 거부**(AC-SONGCUE-008 ②) | 동작 축소 |
| ASSUMPTION-24 (곡 1개 번들 왕복) | BUSKWIZ M0 실측 기준 있음 — 87줄 87/87 · 5.77s · 66.3ms/줄 · 누적 열화 없음 | 계산이 그 범위를 넘으면 M0에서 다시 잰다 | 측정 재수행 |

**전제 번호가 20부터인 것은 규율이다.** BUSKWIZ가 19까지 소진했으므로 본 SPEC은 20을 잇는다 — 같은 기반 위의 SPEC들이 서로 다른 `ASSUMPTION-3`을 갖는 상황을 만들지 않는다.

---

## §6. 테스트 설계 방향

### §6.1 순수 함수 우선, 인메모리 리그

섹션 파싱 · 어휘 조회 · 룩 매핑 · 큐 번호 원장 · 번들 결합 · 보고는 전부 순수하다 — 주입된 `RoleResolution` / `PoolIndex`와 인메모리 `LookLibrary`, 그리고 섹션 목록 리터럴만 있으면 결정론 테스트가 가능하고 OSC는 0이다. 큐 번호 원장은 특히 순수 테스트에 유리하다: 입력은 섹션 목록, 출력은 발화된 `(시퀀스, 큐)` 집합이므로 라이브 없이 §4 위험 #1·#2·#4·#11·#14를 전부 고정할 수 있다.

**단, 툴 층은 순수 테스트로 검증하지 않는다.** AC-SONGCUE-015는 `registry.dispatch`로 진입해야 한다 — 빌더를 직접 호출하는 테스트는 배선 결함을 **구조적으로** 볼 수 없고, LOOKLIB이 그 함정으로 라이브 세션 1회를 더 썼다(원인: 세션 레벨 실행기에 프로덕션 호출자가 0인 상태로 유닛 테스트만 초록이었다). 이것은 스타일 선호가 아니라 **이 저장소가 이미 값을 치르고 배운 것**이다(AP-19).

### §6.2 실패 모드는 개별 테스트 (병합 금지)

서로 다른 실패 모드를 한 테스트에 묶지 않는다. 본 SPEC이 구분해야 하는 모드는 다음과 같고, **각각 개별 테스트**다:

- **입력 거부 2종** — 시각 **역행**과 시각 **중복**. 둘 다 REQ-SONGCUE-002가 거부하지만 사유가 다르고, 중복은 "섹션 시각이 모두 동일"이라는 경계 케이스로 이어진다(acceptance.md §D). 한 테스트에 묶으면 한쪽만 구현해도 통과한다.
- **어휘 밖 이름의 부분 처리** — 어휘에 있는 이름과 없는 이름이 **섞인** 입력에서 있는 것만 해석되고 없는 것만 표시되어야 한다(AC-SONGCUE-004 추가 assert). "전량 실패로 접는" 구현과 "전량 추정으로 채우는" 구현이 **둘 다** 이 테스트에서 떨어진다.
- **큐 번호 비전진 ≠ 값 라인 충돌** — §4 위험 상세가 적은 그 겹침이다. 전자는 **커맨드가 N개 나갔는데 서로를 덮은** 것이고 후자는 **커맨드가 N개보다 적게 만들어진** 것이다. 전자는 `(시퀀스, 큐)` 집합으로, 후자는 건너뜀 사유의 존재로 각각 본다. 한 테스트에 묶으면 둘 다 통과한다.
- **건너뜀 ≠ 미실행** — 빌드 시점 판정(값 라인 충돌 — `server/looks/busking.py:240`)과 실행 시점 귀결(`not_executed` — `server/orchestrator/tools.py:540`, `failed = True` `:569`)은 다른 사건이다(§4 위험 #11). 섹션별 판정에서 둘을 똑같이 접는 구현을 떨어뜨리는 테스트가 필요하고, 두 수를 한 칸에 합산하지 않음을 함께 본다.
- **건너뛰기 ≠ 거부** — 값 라인 충돌은 `SkippedStore` 계열이고 목적지 불일치는 **예외**다(`server/looks/busking.py:220-224`, §4 위험 #14). 충돌 픽스처에서 예외가 나면 실패, 목적지 불일치 픽스처에서 조용히 넘어가면 실패다.
- **미매핑 사유 2종** — 어휘 밖 이름(REQ-SONGCUE-004: "지정 필요")과 룩 부재(REQ-SONGCUE-006: 그 장르에 그 다이내믹스 룩이 없음)는 **다른 사실**이다. 전자는 사용자가 이름을 고치거나 지정하면 해소되고, 후자는 라이브러리 증보가 필요하다. 조치가 다르므로 사유를 합치면 보고가 쓸모를 잃는다.
- **리그 미도착은 이 계층에 도달하지 않는다** — 툴 핸들러가 섹션 미도착을 번들 구성 **이전에** `is_error=True`로 조기 반환하는 것이 기존 관례이므로(`server/orchestrator/tools.py:757` 선례), 그 사유를 섹션 판정에 넣는 테스트는 **도달 불가 경로**를 검사하는 것이다. 그 케이스는 툴 층 테스트가 조기 반환으로 본다(acceptance.md §D).
- **입력 오류 ≠ 답변인 실패** — 어긋난 섹션 입력은 정정 가능한 실수로 `is_error=True`, "리그가 역할을 하나도 주소 못 함"은 답변인 실패로 `is_error=False`다(acceptance.md §D). 게이트 보류는 `is_error=True`이고 LiveLock 강등은 `is_error=False`다 — **강등과 보류는 다른 사건이다**(AC-SONGCUE-015 ④).

### §6.3 번들 규율은 문자열 수준 assert

생성 번들의 커맨드 튜플에 대해 게이트와 독립적으로 빌더 자체의 불변식을 고정한다. **모든 스캔은 생성된 커맨드 튜플에 걸고, 목록이 비어 있지 않음을 함께 assert한다** — 공집합에 대한 전수 검사는 자동 통과하기 때문이다(AP-12).

- 발화된 `(시퀀스 번호, 큐 번호)` 집합이 **시퀀스 1종 × 큐 `1..N` 빠짐없이 한 번씩**이다. 중복·건너뜀 0건 — 위험 #1의 기계 판정(AC-SONGCUE-006 ②).
- 섹션 **6개와 10개** 두 크기에서 모두 성립한다(AC-SONGCUE-006 ③). 섹션 1개짜리 픽스처만 쓰면 비전진이 드러나지 않는다.
- 커맨드 문자열 전수 `c.isascii()`가 전량 True다(AC-SONGCUE-007 ①). 목적지 커맨드가 선두 정확히 1회이고 `commands[0]`이 그것이다.
- 섹션 단위 `ClearAll`이 **전량 생존**한다 — 면제 집합에 있으므로(`server/orchestrator/tools.py:236`) 접지 않아도 손실이 0이다(AC-SONGCUE-010 ①).
- `/Overwrite` · `/Remove` · `Delete` · MA2형 `/trig=` 부재를 **대소문자 무관**으로 assert한다. 런타임 매칭이 이미 대소문자 무관이므로 대소문자를 고정한 assert는 빌더가 `/overwrite`를 내보내도 **조용히 통과**한다(LOOKLIB 감사가 잡은 위양성 테스트).
- 각 스캐너의 **비공허성을 금지 형태 주입으로 증명**한다 — `Store Sequence 5 Cue 1 'X' /overwrite` · `Set Cue 1 Sequence 5 /trig=Time` · `Label Cue 1 'X'` · `Goto Cue 2 Sequence 5` · 한글 큐 이름을 각각 심어 스캐너가 실제로 잡는지 본다(AC-SONGCUE-009 ②).
- 커맨드에 등장하는 **모든 번호**가 주입한 리그 픽스처의 값 또는 섹션 입력 순서에서 온다 — 리터럴 유래 번호 0건. **리그 픽스처를 바꾸면 선택된 시퀀스 번호가 따라 바뀐다**(AC-SONGCUE-008 ①, AC-SONGCUE-010 ③).
- **값 라인의 번들 내 중복 0건**, 또는 중복이 있다면 그 섹션이 건너뜀으로 판정되어 있다 — 위험 #2·#4의 기계 고정.
- **섹션 판정의 경계가 `_merge`의 spans에서 온다**(`server/looks/busking.py:209`, `:226`) — 보고가 자체 경계 계산을 갖지 않음을 확인한다(AP-13).

### §6.4 회귀 방어선

- **PRESERVE diff 빈 출력** — `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `library/` · `server/safety/**` · `server/web/preview.py` · `console/lua/**` · `server/rulebook/assets/v2.4.2/**`. 추가로 `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:234-238`)와 실행/dedupe 블록(`:524-569`) 무변경 확인 — 결정 G의 기계 증거다. **범위를 `:524-569`로 잡는 이유**는 위 앵커 정정 표의 dedupe 블록 행이다: spec.md가 인용한 `:526-550`은 `failed` 플래그(`:524`)와 stop-on-first-failure의 실제 귀결(`:551-569`)을 범위 밖에 두므로, 그 범위로 건 diff 게이트는 실행 의미론의 절반을 지키지 못한다. **`matching.py`와 `instantiate.py`의 diff가 비어 있지 않다는 것은 결정 J·F가 반증되었다는 신호**이므로(§2 — `matching.py`는 어휘 출처 결정 J, `instantiate.py`는 큐 번호 원장 결정 F), 그 경우 통과시키지 말고 결정을 먼저 재검토한다(AC-SONGCUE-016 추가 assert). **`server/looks/report.py`는 PRESERVE가 아니다** — 결정 I의 공개 접근자 1건 추가가 예정된 유일한 비파괴 변경이며, 그 diff는 1건을 넘지 않아야 한다.
- **`git diff`는 반드시 `<BASE>..HEAD` 형태로 건다** — 인자 없는 `git diff`는 커밋 뒤 항상 빈 출력이라 PRESERVE 게이트가 무력해진다. `<BASE>`는 run-phase 킥오프에서 기록한 착수 SHA다(acceptance.md AC-SONGCUE-016의 "협상 불가" 항).
- **기존 스위트** — `test_looks_instantiate.py` · `test_looks_resolver.py` · `test_looks_tool.py` · `test_busking_bundle.py` · `test_busking_report.py` · `test_safety_gate.py` · `test_safety_classify.py` · `test_last_created.py` · `test_architecture.py` 신규 실패 0건. 특히 `test_busking_bundle.py`·`test_busking_report.py`는 본 SPEC이 재사용·확장하는 계층의 계약을 고정하므로 1차 신호다. `test_last_created.py`는 위험 #6의 감시선이다(`:58-61`이 `Store Cue 1 Sequence 71`을 시퀀스 생성으로 읽지 않음을 고정).
- **AST 식별자 스캔 3종** — (i) 신규 모듈에 섹션어→숫자 매핑 딕셔너리 리터럴 0건 + `matching` 심볼을 실제로 import(AC-SONGCUE-003), (ii) 핸들러 서브트리와 신규 모듈에 `execution_port` · `ConsoleLink` · `APIRouter` 직접 접근 0건(AC-SONGCUE-015 ①), (iii) 후보 순회가 `looks_for_genre`를 재사용함(재구현 0건 — AC-SONGCUE-005 ②). **raw 텍스트 grep이 아닌 이유**는 텍스트 스캔이 호출과 그 호출을 **금지한다고 적은 독스트링**을 구분하지 못하고, 그때 지워지는 것은 대개 독스트링이라는 사고 기록이다(AP-11). 동형 스캔이 `server/tests/test_looks_resolver.py:509-529`에 이미 있다.
- **정적 진입 금지 스캔 3종** — 문자열 상수 · f-string 숫자 상수 · 리그 파라미터 숫자 기본값. **독스트링은 제외**하고, 세 스캐너 전부 금지 형태 주입으로 비공허성을 증명한다(AC-SONGCUE-010 ③④).
- **뮤테이션 확인** — 각 마일스톤의 핵심 불변식을 깨는 뮤테이션이 **실제로 테스트를 죽이는지** 본다. 최소 4건: 큐 번호를 상수 `1`로 고정 · 값 라인 충돌 가드를 no-op으로 · 큐 이름을 한국어로 · 시퀀스 번호를 리터럴로. BUSKWIZ에서 이 단계가 **공허한 단언 3건**을 잡았다(통과하지만 아무것도 지키지 않던 테스트).
- **baseline은 이월 인용하지 않는다** — 각 마일스톤은 착수 직전 직접 실측한 수에만 델타를 귀속시킨다(spec.md §C "측정된 기준선"). LOOKLIB이 M1~M4에 걸쳐 baseline 3건 불일치를 끝내 규명하지 못한 전례가 근거다.

### §6.5 라이브 검증은 2 AC (결정 D)

| 세션 | AC | 시점 | 측정 대상 | 부정 시 |
|---|---|---|---|---|
| **M0 프로브** (코드 변경 **0건**) | **AC-SONGCUE-017** | **M3 착수 전** (M1·M2는 순수 계층이라 병행 가능하나, M3 저작은 판정 없이 착수 불가) | **5건 전부 판정 확정.** ① **ASSUMPTION-21 (블로킹)** — `Store Sequence <n> Cue 1 …` 후 `Cue 2 … /Merge`를 발화하고 `DataPool/Sequences/<n>` 재조회로 **자식 2개**를 확인한다. 라이브 `Cue ≥2`가 감사 로그 전량 0건이므로 이것이 첫 관측이다. ② **ASSUMPTION-23** — 여집합에서 고른 번호가 실제로 비어 있는지, 그리고 "비어 있음"과 "존재하지 않음"이 **구별되는지**. 실기 번호가 비연속이라는 실측(`SPEC-COPILOT-SHOWUI-001/progress.md:465`)이 출발점이다. ③ **ASSUMPTION-20** — 타임코드 존부를 **비파괴 범위에서** 재고, 판정 불가면 그 사실을 판정으로 기록한다. ④ **ASSUMPTION-22** — **본 SPEC이 발화할 정확한 리터럴**을 잰다(룰북 예시는 `'Follow'`이고 `'Time'`은 주석 메뉴 — §4 위험 #10). **파싱 성공과 효과 발생을 구분해 기록한다** — `Cmd()`가 거부된 커맨드에도 OK를 보고한 실측 사례가 있다. ⑤ **ASSUMPTION-24** — 곡 1개 번들 규모를 BUSKWIZ의 87줄/5.77s/66.3ms/줄 실측에서 계산하고, 상한을 넘으면 실측한다 | **ASSUMPTION-21 부정 → M3 저작 미착수**(축 절단이 아니다). 20·22 부정 → 해당 축 DESCOPE, 그 커맨드 0건. 23 부정 → 번호 추측 금지 거부. **우회 금지** — 타임코드가 없다고 시퀀스를 더 만들지 않는다(AP-5). 프로브 산물의 처분을 정리 기록으로 남긴다 |
| **M7 종단** | **AC-SONGCUE-018** | **M6 완료 후** | 곡 1개의 큐리스트를 종단 생성한다. ① `console.executed == plan.commands` — **순서까지 동일**, 전 행 `ok=True`. ② `skipped_already_executed` **0건**(값 라인 충돌 가드의 유닛 판정이 실물에서 재현). ③ 재조회에서 시퀀스 1개에 큐 N개가 **서로 다른 번호로** 존재하고 이름이 일치(큐 번호 원장의 라이브 확인 — 위험 #1). ④ 보고의 집계 수치가 재조회 실측과 일치. ⑤ **한계 명시의 실물 확인** — 재조회가 `CueFade`·`TrigType`을 주지 않음을 관측하고 그 사실이 결과에 적혀 있음을 본다 | **증거는 툴 자신의 목록이 아니라 감사 로그여야 한다** — 툴이 "만들었다"고 적은 목록은 툴의 주장이고 감사 로그는 콘솔이 답한 기록이다(BUSKWIZ M7의 교훈). 재조회 한계 때문에 검증은 **존재와 이름** 수준이며, 그 한계를 결과에 명시한다 |

**왜 M0가 M3보다 앞서야 하는가.** 다섯 전제가 서로 다른 것을 막는다. ASSUMPTION-20·22는 **축의 발동 여부**를, ASSUMPTION-23은 **번호 출처의 신뢰성**을, ASSUMPTION-24는 **번들 규모 정책**을 미정으로 만든다 — 이들은 부정이어도 M3가 축소된 형태로 선다. **ASSUMPTION-21만 다르다**: 부정이면 산출물 정의(REQ-SONGCUE-007) 자체가 성립하지 않아 **무엇을 저작해야 하는지가 정해지지 않는다.** 즉 M0는 "저작 전에 전제를 확인한다"는 일반 원칙이 아니라 **미확정 상태로는 M3의 산출물 형상 자체가 정해지지 않는다**는 구체적 이유로 앞선다. M1(섹션 입력)과 M2(섹션→룩)는 순수 계층이고 MA3 문법에 의존하지 않으므로 M0와 병행할 수 있다 — 그 두 마일스톤의 산출물은 어느 판정에서도 같다.

**M0의 부정 판정은 SPEC 실패가 아니다 — 단 하나만 예외다.** ASSUMPTION-20·22·23·24의 부정은 **정의된 결과**이며 AC-SONGCUE-012 **②(타임코드 축) · ④(자동 진행 축)**의 "해당 커맨드 0건" 스캔과 AC-SONGCUE-008 ②의 "추측 금지 거부"가 그 판정을 기계적으로 고정한다. 실행되지 않은 분기는 `skip` 사유를 명시한 채 **남긴다 — 삭제하지 않는다.** 후속 SPEC이 게이트를 다시 열 때 출발점이 된다. **ASSUMPTION-21의 부정만이 저작을 막으며**, 그 경우 M3를 보류하고 산출물 정의의 재설계를 사용자 결정 항목으로 올린다 — 섹션마다 시퀀스를 따로 만드는 대안은 REQ-SONGCUE-007과 위험 #6을 동시에 건드리므로 SPEC이 임의로 정하지 않는다(AP-14). **ASSUMPTION-23의 부정은 블로킹이 아니라 동작 축소다** — 여집합을 신뢰할 수 없으면 번호를 추측하지 않고 **거부로 답하며**(AC-SONGCUE-017 · AC-SONGCUE-008 ②), 그 답은 M3 저작을 막지 않는다.

---

## §7. 반-패턴 (이 SPEC 근처의 유혹)

ID는 **AP-1부터 재시작**한다(SPEC-로컬 번호). BUSKWIZ · LOOKLIB의 AP-n과 번호가 겹치는 것은 의도된 것이며, 인용 시 SPEC 접두를 붙인다.

| # | 유혹 | 왜 금지인가 |
|---|---|---|
| **AP-1** | **시각이 어긋나면 정렬해서 진행** — `sections.sort(key=lambda s: s.start)` 한 줄로 "고쳐 준다" | REQ-SONGCUE-002의 정면 위반. **정렬은 입력을 고치는 게 아니라 다른 곡을 만드는 것이다** — 사용자가 의도한 적 없는 구조의 큐리스트가 쇼파일에 남고, 그것은 사람이 콘솔에서 되돌려야 하는 비가역 산출물이다. 더 나쁜 것은 이 실패가 **조용하다**는 점이다: 정렬된 입력은 단조 증가를 만족하므로 이후 어느 검사도 걸리지 않고 큐 N개가 정상 생성된다. AC-SONGCUE-002 추가 assert가 "거부 후 반환에 섹션 목록이 없거나, 있다면 입력 순서와 동일(임의 재배열 0건)"을 고정한다. 역행과 중복은 **별개 사유**이므로 §6.2가 개별 테스트로 떨어뜨린다 |
| **AP-2** | **모르는 섹션 이름을 가장 비슷한 것으로 승급** — `"Breakdown"` → `"빌드"`(문자열 유사도) 또는 기본 다이내믹스 `3` | REQ-SONGCUE-004 / AC-SONGCUE-004의 정면 위반. `server/looks/matching.py`의 모듈 레벨 `@MX:WARN`이 같은 규율을 코드 층에서 적는다 — "matching must never manufacture a look — a query that hits nothing returns a fallback signal, never the nearest neighbour"(`:28-29`, 사유 `:30`). 승급의 결과는 **사용자가 원한 적 없는 룩이 그 섹션에 박히는 것**이고, 큐는 프리셋과 달리 라벨 충돌 검사로 걸러지지 않는다(`_plan_stores`의 `CONFLICT` 검사는 프리셋 라벨을 보는 것이고 큐에는 대응 장치가 없다). 부분 처리가 답이다: 어휘에 있는 섹션은 해석하고 없는 것만 "지정 필요"로 표시한다 — **전량 실패로 접는 것도 같은 위반**이다(AC-SONGCUE-004 추가 assert가 섞인 입력으로 양쪽을 동시에 떨어뜨린다) |
| **AP-3** | **큐 이름을 한국어로 발화** — "사용자가 한국어로 말했으니 큐 이름도 `'코러스 1'`이 친절하다" | 사전 확정 ③ / REQ-SONGCUE-008 / AC-SONGCUE-007의 정면 위반이고, **친절이 아니라 시간차 고장**이다. 생성 시점에는 통과한다(`Store …`는 `safe` — `server/tests/test_safety_classify.py:63-66`). 막히는 곳은 재조회다: `server/safety/console.py:478-484`가 큐 이름을 본문 라인으로 수집하고 `server/safety/expand.py:106-112`가 라인마다 `validate`를 걸며 `server/safety/grammar.py:20`이 ASCII 전용이다 — 결과는 거부가 아니라 **보류**다. 증거도 비대칭이다: ASCII 종단 통과는 라이브 관측(`SPEC-COPILOT-SHOWUI-001/progress.md:460`), 한국어는 **오프라인 목 1건**(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72`). 한국어는 표현 계층에 둔다(`server/looks/report.py:63`, `:74`, `:77`) — §4 위험 #3 |
| **AP-4** | **`Label Cue <n> '<name>'`로 큐 이름을 따로 붙이기** — "`Label Sequence`가 되니까 `Label Cue`도 될 것" | **룰북 `v2.4.2/` 전체에 `Label Cue` 0건**이다. 유일 등장은 `server/measurement/corpus.yaml:69`이고 그 블록은 스스로 "the deterministic offline action for M6a mock runs ONLY"라 한정하며(`:7-10`), **큰따옴표를 써서** `server/rulebook/assets/v2.4.2/00_grammar.md:26-29`를 위반한다(전송이 커맨드 라인을 큰따옴표로 감싸므로 내장 큰따옴표는 커맨드를 깨뜨린다). 유혹이 강한 이유는 시퀀스 축에 T1이 있기 때문이다 — `Label Sequence 22 'Golden Chorus'` `ok:true`(`server/audit_logs/audit-20260726.jsonl:328`, 문법 `00_grammar.md:27`). **한 축의 T1이 다른 축의 0건을 대체하지 않는다.** 큐 이름을 확정하는 유일한 T1 경로는 `Store Sequence <n> Cue <m> '<name>'`의 **인라인 3번째 토큰**이며 그 형은 5건이 실행됐다 — §4 위험 #12 |
| **AP-5** | **타임코드가 없으니 시퀀스를 더 만들어 우회** — "섹션마다 시퀀스를 하나씩 만들고 순서대로 `Go+`하면 시간축이 된다" | **답은 DESCOPE이지 우회가 아니다**(REQ-SONGCUE-013). 이 우회는 셋을 동시에 깬다: (i) REQ-SONGCUE-007의 "곡 1개 = 시퀀스 1개", (ii) 위험 #6 — `server/orchestrator/last_created.py:30`이 `Store Sequence <n>`마다 패널 핀을 갱신하는데 그것은 **스냅샷 최신 1건**이므로(`:17-18`) 섹션 N개 시퀀스는 앞 N−1개의 핀을 조용히 잃는다, (iii) 시퀀스 번호 여집합을 N배로 소모해 ASSUMPTION-23의 위험을 N배로 키운다. BUSKWIZ가 정확히 같은 우회를 AP로 막았고(익스큐터 게이트가 닫혔을 때 시퀀스를 만들어 얹으려는 유혹), LOOKLIB M7에서 모델이 **스스로** 그 경로를 밟은 기록이 있다. **DESCOPE는 실패가 아니라 정의된 결과다** — AC-SONGCUE-017 비고가 "우회 금지"를 명문화한다 |
| **AP-6** | **dedupe 면제 집합을 확장** — "값 라인만 면제하면 충돌 문제가 사라진다" | `_PROGRAMMER_STATE_COMMANDS`(`server/orchestrator/tools.py:234-238`)와 실행/dedupe 블록(`:524-569`)은 PRESERVE다(spec.md §D, AC-SONGCUE-010 ②). 면제 집합은 `run_commands`를 쓰는 **모든** 소비자가 공유하므로 본 SPEC 하나를 위해 전역 실행 의미론을 바꾸는 거래다. 면제의 근거가 좁은 것에도 이유가 있다 — `:236` `ClearAll`이 면제인 것은 그것이 "durable artifact를 만들지 않고 반복은 반복이 아니라 **다른 순간**"이기 때문이다(`:195-198` 주석). **값 라인은 그 논리에 맞지 않는다**: 값 라인의 반복은 같은 프로그래머 상태를 두 번 세우는 것이고, dedupe가 그것을 접는 것은 설계대로 동작하는 것이다. 답은 면제 확장이 아니라 **건너뛰기 + 사유 보고**다(결정 H) |
| **AP-7** | **프로퍼티를 읽은 적 없는데 검증됐다고 보고** — 재조회로 큐 존재를 확인한 뒤 보고에 `"cue_fade_verified": true` 또는 "4초 페이드로 설정 완료" | REQ-SONGCUE-017 / AC-SONGCUE-014 ②의 정면 위반이며 **이 SPEC에서 가장 밟기 쉬운 반-패턴**이다. 라이브 실측이 경계를 정한다: `DataPool/Sequences/<n>/<m>`은 `name`/`class`/`i`(+ 중첩 `Part`)만 반환하고 커맨드·`CueFade`·`TrigType`은 **어떤 형태로도** 반환하지 않는다(`SPEC-COPILOT-EXECREF-001/design.md:167`). 응답기는 `Cue`를 특별 취급하지 않고(`console/lua/copilot_responder.lua`에 `Cue` 0건) `console/lua/**`는 PRESERVE다. 밟기 쉬운 이유는 **툴이 그 값을 알고 있기** 때문이다 — 자기가 발화한 `CueFade 4`를 기억하므로 보고에 적는 것이 자연스러워 보인다. 그러나 발화한 것과 관측한 것은 다르고, 콘솔이 거부해도 발화 기록은 남는다. AC가 **부정형**으로 고정하는 이유가 이것이다 |
| **AP-8** | **`matching`의 섹션 어휘를 신규 모듈에 재정의** — "P1-1 전용 표가 있으면 곡 구조에 맞게 밴드를 좁힐 수 있다" | REQ-SONGCUE-003 / AC-SONGCUE-003의 정면 위반. 정본은 `server/looks/matching.py:92` `DYNAMICS_TERMS`(항목 전체 `:94-130`)이고 `server/looks/schema.py:20-25`의 `@MX:NOTE`가 이 스키마를 P1-1/P1-2 **공통 기반**으로 못 박았다 — 한쪽만 갱신되면 두 SPEC이 동시에 깨진다. **밴드를 좁히려는 동기 자체가 이미 문서에서 기각되어 있다**: `matching.py`의 모듈 독스트링이 "Bands are deliberately WIDE where the SPEC's own label spans two levels: this table FILTERS, and an over-narrow filter drops a good look silently"라고 적는다(`:22-25`). 좁힌 필터의 실패는 조용하다. 확장이 필요하면 정본을 고치고 두 SPEC의 테스트로 확인하는 것이 유일한 경로이며, 그것은 본 SPEC의 범위 밖이다(`matching.py`는 PRESERVE) |
| **AP-9** | **시퀀스 번호를 하드코딩** — "빈 번호 찾기가 불안정하니 `Sequence 100`부터 쓰자" 또는 파라미터 기본값 `sequence_no: int = 100` | REQ-SONGCUE-020 / AC-SONGCUE-010 ③④의 정면 위반. `server/looks/schema.py:20-25`가 적듯 이 계층에는 **번호를 넣을 필드가 애초에 없다** — 그 폐쇄 필드 집합이 per-show 값의 정적 진입을 막는 기제다. 실측이 하드코딩을 직접 반박한다: 실기 쇼파일의 시퀀스 번호는 `1,2,11~16,30,41,50,62,71,80`으로 비연속이었고(`SPEC-COPILOT-SHOWUI-001/progress.md:465`) 다른 쇼파일이 `100`을 쓰고 있을 이유는 없다. 스캔이 **문자열 상수 · f-string 숫자 상수 · 파라미터 숫자 기본값 3종**을 보는 이유가 이것이다 — 세 번째 형태가 가장 무해해 보이면서 실제로는 모든 호출에 적용된다 |
| **AP-10** | **값 라인 충돌을 거부(예외)로 처리해 곡 전체를 죽이기** — "충돌은 저작 오류이니 `raise`가 정직하다" | REQ-SONGCUE-012 / AC-SONGCUE-011 ③의 정면 위반. 선례가 반대를 적는다 — `_plan_stores`는 "저장 불가" 전량을 사유를 단 `SkippedStore`로 답하고(`server/looks/instantiate.py:325-384`) `LookInstantiationError`는 **구조적 기형에만** 쓴다. **곡에서 이 선택은 특히 나쁘다**: 어휘 실측상 `(4,5)` 밴드(`server/looks/matching.py:117-130`)에 `"코러스"`(`:117`) · `"후렴"`(`:119`) · `"드랍"`(`:121`) · `"클라이맥스"`(`:123`) · `"엔딩"`(`:127`) · `"피날레"`(`:129`)가 전부 들어 있으므로 후렴 3회 곡은 **정상 입력으로** 충돌을 밟는다 — 예외로 처리하면 가장 흔한 곡 구조가 아무 산출도 내지 못한다. 반대 방향의 혼동도 금지다: 목적지 불일치는 실제로 예외이므로(`server/looks/busking.py:220-224`) 두 정책을 뒤바꾸면 저작 결함이 조용히 통과한다(§4 위험 #14, §6.2) |
| **AP-11** | **raw 텍스트 grep으로 어휘 재정의·경계를 검사** — `grep -c "코러스" server/looks/songcue.py` == 0 이면 통과 | AC-SONGCUE-003이 **AST**를 요구하는 이유는 사고 기록이다 — 텍스트 스캔은 호출과 그 호출을 **금지한다고 적은 독스트링**을 구분하지 못하고, 그때 지워지는 것은 대개 독스트링이다(LOOKLIB AP-19). 본 SPEC에서는 이 위양성이 더 크다: 설계 산문이 어휘를 **설명해야** 하므로(예: "`인트로`는 `(1,2)`에 매핑된다") 텍스트 스캔은 정당한 문서를 결함으로 잡고, 그 압력은 문서를 지우는 쪽으로 작용한다. 반대 방향의 위음성도 있다 — `chr(0xC778)` 같은 우회는 텍스트로 안 잡히지만 AST로는 잡힌다. 동형 스캔이 `server/tests/test_looks_resolver.py:509-529`에 이미 있다 |
| **AP-12** | **소스 정규식으로 금지 커맨드 0건을 증명** — `assert "/Overwrite" not in open("songcue.py").read()` | BUSKWIZ 감사가 잡은 결함의 계승. 두 겹으로 틀렸다. (i) **소스에 없어도 런타임에 만들어질 수 있다** — f-string 조립·조건 분기·플래그 연결이 소스 검색을 통과한다. 스캔은 **생성된 커맨드 튜플 전수**에 걸어야 한다(AC-SONGCUE-009 ①). (ii) **공집합에 대한 전수 검사는 자동 통과한다** — 빌더가 아무것도 만들지 않으면 모든 부정형 assert가 통과하므로, 목록이 비어 있지 않음을 **함께** assert하고 금지 형태를 **심어서** 스캐너가 실제로 잡는지 확인해야 한다(AC-SONGCUE-009 ②). 대소문자 고정도 같은 부류의 결함이다 — 런타임 매칭이 대소문자 무관이므로 `/overwrite`가 조용히 통과한다(§6.3) |
| **AP-13** | **섹션별 판정의 경계를 보고 계층에서 다시 계산** — "섹션마다 커맨드 5줄이니 `i*5`로 나누면 된다" | `busking._merge`가 결합 번들과 함께 **spans `[시작, 끝)`을 반환한다**(`server/looks/busking.py:209`, `:226`)이고 그 docstring이 이유를 적는다 — "경계를 아는 유일한 자리가 여기다. 보고 계층이 이 규칙을 다시 구현하면 두 곳이 갈라진다"(`:202-206`). 곡 축에서 재계산은 **반드시 틀린다**: 값 라인 충돌로 건너뛴 섹션은 커맨드 수가 다르고(길이 0 구간을 받는다 — `:213-215`), 목적지 커맨드가 선두 1회만 있으므로 첫 섹션과 나머지의 길이가 다르다(`:216-218` vs `:225`). 틀린 경계는 **per-command status를 엉뚱한 섹션에 귀속**시키므로, 보고가 "코러스 실패"라 적을 때 실제로는 벌스가 실패한 상태가 된다 — AC-SONGCUE-013 ①②가 산술 일치로 잡는다 |
| **AP-14** | **`Cue 2` 라이브 0건인데 룰북 라이브 선언을 근거로 GO 선언** — "`31_choreography_patterns.md:7`이 이 파일 전체가 라이브 검증됐다고 적었으니 `:55`도 검증된 것" | ASSUMPTION-21의 등급을 T2에서 T1로 올리는 무근거 승급이다. **`:7`은 파일 단위 선언이고 그것이 모든 줄의 개별 실행을 뜻하지 않는다** — 직접 실측이 이를 증명한다: 같은 파일의 익스큐터 문법 3건이 BUSKWIZ M0에서 **전부 DESCOPE**로 판정됐고, `server/audit_logs/*.jsonl`의 `executed` 이벤트 전량에서 `Cue ≥2`는 **0건**이며 T1 5건은 전부 `Cue 1`이다(`audit-20260719.jsonl:148`, `:186`, `audit-20260722.jsonl:1057`, `audit-20260726.jsonl:327`, `:538`). 등장하는 모든 `Cue 12` 계열은 오프라인 목이다(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73`). 승급이 위험한 이유는 **이것이 블로킹 게이트**라는 점이다 — 잘못된 GO는 산출물 정의가 성립하지 않는 상태로 M3를 착수시킨다(§4 위험 #9) |
| **AP-15** | **잰 것과 다른 리터럴을 발화** — M0가 `'TrigType' 'Follow'`를 재고 GO를 받은 뒤 구현이 `'TrigType' 'Time'`을 발화 | AC-SONGCUE-012 ③("발화 형식이 **M0가 실측한 것 하나뿐**")의 정면 위반. 룰북이 실제로 적은 리터럴은 `'Follow'`이고(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:111`) `'Time'`은 **같은 줄 주석**의 토큰 메뉴(`Go / Time / Follow / Sound / BPM`) 항목이다 — 인계 브리핑조차 `'Time'`으로 적혀 있었고 본 문서가 그것을 정정했다(앵커 정정 표의 `TrigType` 행). 시간 기반 진행이 본 SPEC이 원하는 것이므로 치환은 자연스러워 보이지만, **잰 것과 발화하는 것이 다르면 GO는 그 발화를 덮지 않는다.** 따라서 M0는 `'Follow'`와 `'Time'`을 **각각 따로 재고 결과를 구분해 기록한다** — 룰북 예시 리터럴은 `'Follow'` 하나뿐이므로 `'Time'`의 수용 여부는 잰 적이 없는 별개 사실이다. 부수 함정 둘: `:115`가 "Trigger tokens are Capitalized"를 적으므로 소문자는 별도 실패이고, M0는 **파싱 성공과 효과 발생을 구분**해 기록해야 한다(`Cmd()`가 거부된 커맨드에도 OK를 보고한 실측 사례가 있다). 같은 규율이 `Cue 2` 축에도 적용된다 — `/Merge` 유무를 계획이 정하지 않고 M0가 잰 형태를 그대로 발화한다(§3 섹션 본문 주) |
| **AP-16** | **섹션 점프 UX를 위해 `Goto Cue <m> Sequence <n>`을 발화** — "섹션 목록이 있으니 그 섹션으로 바로 뛰는 기능이 자연스럽다" | 게이트가 참조를 추출하지 못해 **보류**된다 — `RECOGNIZED_REFERENCE_TYPES`에 `Cue`가 없고(`server/safety/classify.py:44` — `Macro`/`Plugin`/`Sequence`/`Executor` 4종), `server/tests/test_safety_classify.py:114`가 `("Goto Cue 3", None)`을 고정한다. 룰북에는 형식이 있으므로(`31_choreography_patterns.md:100` 주석의 `Goto Cue 2 Sequence 11`) "문법은 맞는데 왜 안 되지"로 읽히는데, **문제는 문법이 아니라 게이트의 참조 인식 범위**다. 발현 형태가 함정이다: 거부가 아니라 승인 대기이므로 "동작하지만 매번 사람을 부른다"가 되어 기능처럼 보인다. 과보류는 이미 인정된 사실이고(`SPEC-COPILOT-MVP-001/progress.md:215`) 그 확장은 `server/safety/**`를 건드리는 별도 과제다 — PRESERVE 위반(§4 위험 #7) |
| **AP-17** | **여집합이 비었거나 조회가 실패했을 때 번호를 추측** — "`DataPool/Sequences` 조회가 안 되면 일단 큰 번호로" | REQ-SONGCUE-009 / AC-SONGCUE-008 ②의 정면 위반이고, BUSKWIZ가 익스큐터에서 데인 함정("비어 있음"과 "미확인"의 미구분)의 시퀀스 축 재발이다. 열거가 주는 것은 **존재하는** 시퀀스뿐이므로(경로 `server/safety/console.py:399`) 잘린 목록의 여집합은 잘린 만큼 낙관적이고, 그 번호로 `Store`하면 **남의 시퀀스에 큐를 얹는다** — 실패는 조용하다(`server/looks/instantiate.py:291-299`의 `@MX:WARN`이 슬롯 축에서 "MA3 reports it as success"라 적는 그 형태다). 비연속 실측(`SPEC-COPILOT-SHOWUI-001/progress.md:465`)이 압력을 키운다: 여집합이 넓어 보이므로 "아무 빈 번호나"가 안전해 보인다. 답은 **거부**이고, 여집합 공집합도 거부다(acceptance.md §D) |
| **AP-18** | **이미 있는 시퀀스를 `/Overwrite`로 재사용** — "빈 번호 찾기가 까다로우니 기존 시퀀스를 덮어 쓰자" | REQ-SONGCUE-010 / AC-SONGCUE-009의 정면 위반이며 이중 차단선이다 — `Delete`는 블랙리스트(`server/safety/blacklist.yaml:15`)이고 `/Overwrite`는 룰북이 스스로 DESTRUCTIVE로 표시하며 게이트가 사람 승인으로 라우팅한다고 적는다(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:57-59`). **초안 생성기의 일은 덮는 것이 아니다** — spec.md §D가 큐 편집·재생성·삭제를 v1 범위 밖으로 두고 "초안은 한 번 생성하고 사람이 콘솔에서 고친다"를 적는다. 조용히 다른 번호에 두 번째 사본을 만드는 것도 답이 아니다(사용자가 의도하지 않은 자리의 생성). 같은 곡을 두 번 실행하면 **정직한 중복 거부**가 답이다 |
| **AP-19** | **신규 툴을 빌더 직접 호출로 테스트해 배선 결함을 못 보기** | AC-SONGCUE-015 ②가 "`TOOL_NAMES`·`definitions`·`handlers` 3곳에 모두 존재하고 **디스패치로** 확인한다(dict 조회가 아니라 모델이 닿는 경로)"를 요구하는 이유다. LOOKLIB이 정확히 이 함정으로 라이브 세션 1회를 더 썼다 — 세션 레벨 실행기에 프로덕션 호출자가 0인 상태로 유닛 테스트만 초록이었고, 원인은 **테스트가 그 함수를 직접 호출했기 때문**이다. 3곳 중 하나만 빠져도 모델은 툴에 닿지 못하는데 빌더 직접 호출 테스트는 그것을 **구조적으로** 볼 수 없다. 선례 앵커 2개가 형상을 고정한다(`server/orchestrator/tools.py:693-703`, `:817-824` — 핸들러는 `run_commands`의 **호출자**이지 제2 실행 표면이 아니다) |
| **AP-20** | **소수 큐 번호로 섹션을 삽입** — "룰북이 `Cue 1.5`를 적었으니 섹션 추가는 소수로 끼워 넣자" | spec.md §D가 소수 큐 번호 삽입을 v1 범위 밖으로 명시했다. 등급도 낮다 — `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:56`은 T2이고 라이브 실행 기록이 0건이다(`Cue ≥2` 전체가 0건이므로 `Cue 1.5`는 그 부분집합으로서도 0건). 게다가 AC-SONGCUE-006 ②가 "큐 번호가 `1`부터 `N`까지 빠짐없이 한 번씩"을 요구하므로 소수 번호는 **인수 기준 자체와 충돌**한다. 삽입이 필요하다는 것은 초안을 편집하려는 것이고, 그것은 "한 번 생성하고 사람이 콘솔에서 고친다"는 v1 형상과 다른 기능이다 — 별도 SPEC이며, 그 SPEC은 ASSUMPTION-21의 GO를 전제로 시작한다 |

---

## §8. 교차 참조

- **본 SPEC 내부** (줄 앵커 대신 토큰 — 위 참조 규약) — `spec.md` §A(사전 확정 3건 + 하드 결함 3건) · §B(REQ-SONGCUE-001~021, B.1~B.5) · §C(ASSUMPTION-20~24 + PRESERVE) · §D(Out of Scope 7절) · §E(참조 구현 표); `acceptance.md` §B(시나리오 6건) · §C.0(REQ↔AC 역추적 + 마일스톤별 AC 집합) · §C.1(AC-SONGCUE-001~018) · §D(Edge Cases) · §E(Quality Gate) · §F(DoD); `plan.md` §A.4a(결정 A~J의 **정본 등록부** — 본 문서 §5.1이 그 문자 배정을 그대로 따른다) · §B(M0~M7).
- **큐 번호 원장의 근거(결정 F)** — `server/looks/instantiate.py:78-85`(frozen + 미관측 독스트링) · `:96-102`(`PoolIndex`) · `:286`(`_values_line`) · `:291-299`(`@MX:WARN` — 잘못된 대상의 결과를 "MA3 reports it as success"로 적는다) · `:307-312`(`_first_free_slot` — 전진 없음) · `:325-384`(`_plan_stores`, `if not values: continue` `:333-334`); 시간축 판본의 선례 `server/looks/busking.py:158`(`_advance` — frozen을 바깥에서 감싼다).
- **번들 결합과 dedupe(결정 G)** — `server/looks/busking.py:189-227`(`_merge`: 목적지 선두 1회 `:216-218` · 리터럴 복제 금지와 불일치 예외 `:220-224` · **spans 반환 `:209`/`:226`, 근거 docstring `:202-206`**) · `server/orchestrator/tools.py:195-232`(면제의 사유 주석) · `:234-238`(면제 3종 정의; `:235` `Clear` · `:236` `ClearAll` · `:237` 맨 선택) · `:241-244`(`_is_programmer_state`) · **`:524-569`(실행/dedupe 블록 — `failed = False` `:524` · `already_executed` 시드 `:533` · 루프 `:534` · stop-on-first-failure 가드 `:535-543`와 `not_executed` `:540` · 건너뛰기 분기 `:544-557`과 `skipped_already_executed` `:554` · `executed_ok` `:563` · `failed = True` `:569`)** · `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:11`(목적지 선두 1회를 규범으로 적는다).
- **값 라인 충돌 가드(결정 H)** — `server/looks/busking.py:230`(`VALUE_LINE_COLLISION`) · `:240`(`_guard_collision`) · `:277-296`(`build_genre_bundle` — 리그 해석을 인자로 받는 형상과 충돌 실측 기록) · 충돌 확률의 자산 근거 `server/looks/matching.py:117-130`(`(4,5)` 밴드 **한국어 9종 · 영어 5종 = 총 14항목** — 한국어 `코러스` `:117` · `후렴` `:119` · `고조` `:120` · `드랍` `:121` · `클라이맥스` `:123` · `절정` `:125` · `최고조` `:126` · `엔딩` `:127` · `피날레` `:129`, 영어 `chorus` `:118` · `drop` `:122` · `climax` `:124` · `ending` `:128` · `finale` `:130`) · `:114-116`(밴드를 넓게 둔 사유 주석).
- **어휘와 스키마(결정 J)** — `server/looks/matching.py:92`(`DYNAMICS_TERMS` 정의) · `:94-130`(**항목 전체** — `앰비언트` `:94` ~ `finale` `:130`, 닫는 `}` `:131`) · `:99-121`(그 안의 `인트로` `:99` ~ `드랍` `:121` 열거 구간 — 표 전체가 아니다) · `:117-130`(`(4,5)` 밴드 전체 — 위험 #4의 자산 근거) · `:22-26`(밴드를 의도적으로 넓게 둔 이유 — "this table FILTERS, and an over-narrow filter drops a good look silently") · `:28-30`("never manufacture a look" `@MX:WARN` + 사유) · `:114-116`(EDM drop이 4에 저작된 탓에 단일 레벨 밴드를 쓸 수 없다는 주석) · `:71`(`MAX_TOOL_MATCHES = 8`) · `server/looks/schema.py:20-25`(`@MX:NOTE` — P1-1/P1-2 공통 기반이자 per-show 값의 정적 진입 차단 기제) · `:35-36`(`DYNAMICS_MIN`/`DYNAMICS_MAX`) · `server/looks/busking.py:81`(`looks_for_genre` 전순서) · `:75-77`(상수 복제 거부의 논리).
- **큐 이름이 실행 경로인 근거(결정 C)** — `server/safety/console.py:478-484`(자식 `name` → 본문 라인; 루프 `:479-483`) · `server/safety/expand.py:106-112`(라인마다 `validate`, 실패 시 보류) · `server/safety/grammar.py:20`(`_VERB_SHAPE` ASCII 전용) · `server/rulebook/assets/v2.4.2/00_grammar.md:26-29`(단일 인용부호 규칙과 그 이유) · `:27`(`Label Sequence 3 'Chorus'`) · 표현 계층 `server/looks/report.py:63`/`:74`/`:77`/`:116`/`:205`/`:278`.
- **단일 실행 경로와 툴 등록(REQ-SONGCUE-018 / REQ-SONGCUE-019 — 정본 결정 등록부에 대응 문자가 없다)** — `server/orchestrator/tools.py:483`(`run_commands`) · `:492`(`bundle_gate.screen`) · `:373`(`collect_rig_sections`) · `:757`(섹션 미도착 조기 반환 선례) · `:42`/`:49`(`TOOL_NAMES`와 직전 선례 항목) · `:1196`(`definitions` 선례) · `:1231`(`handlers` 선례) · `:693-703`·`:817-824`(핸들러는 호출자이지 제2 실행 표면이 아니라는 두 `@MX:ANCHOR` 주석 블록 — 각 블록 바로 위의 `:692`·`:816`은 빈 `#` 줄이다).
- **재조회의 한계(REQ-SONGCUE-017 / AC-SONGCUE-014 — 결정 I가 배치한 보고 모듈이 담는 항목)** — `SPEC-COPILOT-EXECREF-001/design.md:167`(라이브 실측: `name`/`class`/`i`(+ `Part`)만, 커맨드·프로퍼티는 어떤 형태로도 없음) · `server/safety/console.py:396-400`(`DEFAULT_BODY_PATHS`, `Sequence` 항목 `:399`) · `console/lua/copilot_responder.lua:403`("the ONLY address form resolve_path special-cases") · `:405`(`EXECUTOR_ADDRESS_PATTERN`) · `:426`(`resolve_path`) · `:497`(`function M.build_snapshot(id, path)`).
- **게이트의 참조 인식과 `Goto Cue`(위험 #7 · AP-16)** — `server/safety/classify.py:44`(`RECOGNIZED_REFERENCE_TYPES` — `Cue` 부재) · `:46`(`_NUMERIC_REF`) · `server/tests/test_safety_classify.py:63-66`·`:149`(`Store Cue 5`는 `safe`) · `:114`(`("Goto Cue 3", None)`) · `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:100`(주석의 `Goto Cue 2 Sequence 11`) · 과보류 인정 `SPEC-COPILOT-MVP-001/progress.md:215`.
- **패널 핀 연동(위험 #6 · AP-5)** — `server/orchestrator/last_created.py:14-18`(스냅샷 전용 · 최신 1건) · `:27-29`(`Store Cue 1 Sequence 71`을 시퀀스 생성으로 읽지 않는다는 주석) · `:30`(`_STORE_SEQUENCE`) · `:31-33`(`_ASSIGN_SEQ_EXEC`) · `server/tests/test_last_created.py:58-61`(그 구분을 고정하는 테스트).
- **큐 저작 문법의 등급 근거** — **T1(라이브 실행 기록)**: `server/audit_logs/audit-20260719.jsonl:148`(`Store Sequence 62 Cue 1 'Cyan Look'`) · `:149`(`Assign Sequence 62 At Executor 195`) · `:186`(`Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4`) · `:187`(`Assign Sequence 30 At Executor 105`) · `audit-20260722.jsonl:1057`(`… Sequence 90 Cue 1 'Blue Look'`) · `audit-20260726.jsonl:327`(`… Sequence 22 Cue 1 'Golden Chorus'`) · `:328`(`Label Sequence 22 'Golden Chorus'`) · `:538`(`… Sequence 17 Cue 1 'Golden Chorus'`) — 전부 `ok:true detail:"OK"`, **전부 `Cue 1`**. **T2(룰북 라이브 선언 아래이나 실행 기록 없음)**: `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:7`(파일 단위 라이브 선언) · `:50`·`:71`(T1로 승급된 store 형) · `:54`(시퀀스 자동 생성) · `:55`(`Cue 2 … /Merge` — ASSUMPTION-21) · `:56`(소수 큐 번호) · `:57-59`(store 플래그와 `/Overwrite` DESTRUCTIVE 표시) · `:106`·`:108`·`:111-112`(`TrigType`/`TrigTime` — ASSUMPTION-22, 실제 리터럴 `'Follow'`) · `:115-117`(MA2형 `/trig=` 금지, 토큰 대문자 규칙). **T4(mock 전용)**: `server/measurement/corpus.yaml:7-10`(자기 한정) · `:68`·`:69`·`:76`(`Store Cue 12` · `Label Cue 12 "Opening"` · `Store Cue 5 Fade 3`) · `.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73`(같은 것의 `offline mock execution` 기록, `:72`가 한국어 큐 이름). **T5(근거 0건)**: 타임코드 일체 · `Delete Cue <n>`(`server/safety/blacklist.yaml:15`가 `Delete`를 블랙리스트로 둔다) · 별도 Marker/Mark 오브젝트.
- **BUSKWIZ가 인계한 재사용 계약** — `SPEC-COPILOT-BUSKWIZ-001/research.md:377-381`(P1-1 인계 항목) · `SPEC-COPILOT-BUSKWIZ-001/spec.md:140-146`(시퀀스는 P1-1의 영역 + 타임코드 프로브 선행 필요) · `SPEC-COPILOT-BUSKWIZ-001/design.md`(§5.1 결정 E/F/H의 원형 — **그 SPEC 로컬 문자 배정이며 본 문서 §5.1의 동일 문자와 대응하지 않는다** · §6.2 실패 모드 분리 · §6.5 라이브 2 AC 형식 · 그 SPEC의 AP-9/AP-13/AP-17의 원형 — 번호는 SPEC-로컬이므로 본 문서의 동번호와 무관하다) · `SPEC-COPILOT-LOOKLIB-001/spec.md:176-178`(시퀀스를 P1-1에 남긴 자리) · `SPEC-COPILOT-LOOKLIB-001/design.md:97-108`(허위 1:1 주장의 정정 사례) · 그 SPEC의 AP-19(스캔을 고치고 산문을 지킨다).
- **라이브 관측(구속력 있음)** — `SPEC-COPILOT-SHOWUI-001/progress.md:457`(`Go+ Sequence 41 ok=True detail=OK`) · `:459`(`Off Sequence 41 ok=True`) · `:460`(`Store Sequence 90 Cue 1 'Blue Look' ok=True` → 핀 생성 → `Go+`/`Off` 둘 다 `ok=True` — **ASCII 큐 이름의 종단 통과**) · `:463`(콘솔은 돌고 앱은 모르는 상태) · **`:465`(실기 시퀀스 번호 비연속 실측 — `1,2,11~16,30,41,50,62,71,80`, `3~10·17~29` 부재)**.
- **제품·제안 근거** — `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:68`(P1-1 제목) · `:70-73`(산출물 정의와 근거) · **`:71`("곡당 시퀀스 1개 + 타임코드 트랙 + 섹션 마커" — 3부작 중 본 SPEC이 짓는 것은 1부이고 나머지는 게이트·환원)** · `:125`·`:127`(타임코드의 유일 등장 = 외부 참고 링크 텍스트) · `.moai/project/product.md:39`(Phase 3 성공 기준 — "3분 곡 1개 → 검토 가능한 큐리스트 초안을 10분 내 생성").
