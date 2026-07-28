# SPEC-COPILOT-SONGCUE-001 — Plan-Phase Research

status: draft (v0.1.0, 2026-07-28). 본 문서는 송 구조 기반 큐리스트 초안 생성기(시간축 계층)가 얹힐 기존 코드베이스·룰북·감사 로그를 file:line 근거로 분석한다. **구현 코드는 제안하지 않는다 — 분석 전용.** **라이브 조사 수행 여부: 없음** — 실물 콘솔 세션은 M0(ASSUMPTION-20~24 판정)와 M7(종단)의 **2회로만** 계획되어 있고 본 plan-phase는 그 어느 쪽도 당겨 쓰지 않았다. 본 문서의 모든 실측은 **리포지토리 정적 실측**(grep 전수 · 파일 계수 · 줄 대조)과 **기존 산출물 재판독**(감사 로그 `server/audit_logs/*.jsonl`, 선행 SPEC의 progress.md·design.md에 기록된 라이브 관측)이며, 어느 것도 새 콘솔 왕복을 발생시키지 않았다. 정적 실측 8건은 그 사실을 각 지점에 명시한다 — §2 라이브 큐 커맨드 전수 census / §2 mock 판별 / §3 타임코드 5경로 전수 / §3 Marker 오브젝트 전수 / §5 응답기 `Cue` 0건 / §6 재사용 계약 9종 대조 / §8 앵커 전수 재접지 / §9 앵커 드리프트 5건.

> **참조 규약**: 본 SPEC의 정본(spec.md · acceptance.md)은 **줄번호로 인용하지 않는다** — `REQ-SONGCUE-nnn` · `AC-SONGCUE-nnn` · `ASSUMPTION-nn` · 절 제목 같은 **안정 토큰**만 쓴다. 토큰은 개정을 견디고, 가리키는 내용이 사라지면 토큰도 함께 사라져 즉시 드러난다. 줄번호는 조용히 옆 문장을 가리킨다. `파일:줄`은 **코드 · 룰북 · 감사 로그 · 타 SPEC 아티팩트**에만 유지한다 — 그쪽은 커밋 없이 움직이지 않고 달리 쓸 안정 식별자가 없다. **요구·인수 토큰은 예외 없이 슬러그를 포함한 완전형으로만 쓴다** — 슬러그를 뺀 축약형은 본 문서 전체에서 **0건**이며, 그것을 허용하면 서로 다른 SPEC의 같은 번호가 한 문장 안에서 구별되지 않는다.

> **v0.1.0 — 최초 작성.** 선행 SPEC `SPEC-COPILOT-BUSKWIZ-001`의 research.md 절 구조를 계승하되, 조사 축이 다르다 — BUSKWIZ는 "출하된 룩 계층이 **다중 룩 조율**에 남긴 접합면"을 찾았고, 본 문서는 그 위에 **시간축**을 얹을 때 무엇이 근거를 갖고 무엇이 갖지 못하는지를 찾는다. 실질 기여는 다섯이다. (a) **§2의 T1~T5 증거 등급을 감사 로그 전수 census로 확정** — 라이브 실행된 `Cue` 커맨드는 리포지토리 전체에서 **정확히 5건이고 전부 `Cue 1`**이다. 즉 본 SPEC의 핵심 형상(한 시퀀스에 큐 N개)이 정확히 미검증 구간에 놓인다. (b) **§3에서 타임코드 0건을 5경로 전수로 재확인하고, 로드맵·제안서가 그것을 요구한다는 모순을 명시** — 요구는 3곳에 문서화돼 있는데 문법 근거는 어디에도 없다. (c) **§3에서 "섹션 마커"의 실체를 특정** — MA3 Marker 오브젝트는 리포지토리 전체 0건이고, 섹션 마커의 유일한 물리적 실체는 **큐 이름 문자열**이다. (d) **§5에서 큐 이름이 안전 게이트의 본문 라인이 되는 4단계 코드 경로를 종단으로 추적** — ASCII 규칙이 스타일이 아니라 보류 유발 조건임을 코드로 확정했다. (e) **§9에서 정본의 코드 앵커 드리프트 5건을 실측 재접지** — 그중 하나(`server/safety/console.py:484-490`)는 **파일 끝을 넘어가는 범위**였다.

---

## §1. 출처 — 제안서 P1-1 + 로드맵 Phase 3 + 선행 SPEC 2건의 예약 조항 + 사용자 사전 확정 3건

- **제안서**: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 **P1-1**(`:68-74`) — 절 제목 자체가 "송 구조 기반 큐리스트 초안 생성기 — **로드맵 Phase 3의 구체화**"(`:68`)다. 산출물 정의는 `:71` — **"곡당 시퀀스 1개 + 타임코드 트랙 + 섹션 마커"라는 실무 표준 구조 그대로 MA3에 생성한다.** 근거로 든 것은 "실무자들이 손으로 하던 'DAW 마커 → MA3 미러링' 작업을 통째로 대체"(`:72`)와 "초안→사람 검토라는 앱의 안전 철학과도 맞는다"(`:73-74`)이다. **입력 정의는 `:70` — "음원 파일을 분석(구간 분할·BPM·에너지 곡선)해 Intro/Verse/Chorus 구조를 뽑고"**이며, 이 부분이 사용자 확정 ①로 분리되었다(§9.1).
- **로드맵 정합 (2중 표기, 서로 일치)**: `.moai/project/product.md:39` **Phase 3 — 음악분석 → 큐리스트 자동화**, 내용 열 "음악 분석(구간/BPM/에너지) → **타임코드 큐리스트 초안 생성**, 장르별 룩 템플릿", 성공 기준 열 **"3분 곡 1개 → 검토 가능한 큐리스트 초안을 10분 내 생성"**. 같은 내용이 `DESIGN.md:157-160`에 "Phase 3 — 연출 자동화 (8~12주)"로 중복 기재돼 있고 성공 기준(`:160`)도 동일하다. **본 SPEC은 이 성공 기준을 판정 가능한 유일한 로드맵 행 위에 선다** — BUSKWIZ가 Phase 4의 "미정(TBD)"(`product.md:40`)과 씨름해야 했던 것과 대조된다.
- **비목표 계승**: `product.md:44` "라이브 실시간 자율 운영 배제 — 라이브 잠금 모드에서는 read-only + 제안 카드만 생성", `:45` "미적 최종 판단은 사람의 몫 — AI는 초안을 생성할 뿐, 연출의 최종 확정은 항상 사람이 한다." 후자가 "산출물은 사람이 고치는 **초안**"이라는 본 SPEC 정의의 로드맵측 근거이며, `AC-SONGCUE-015` 구간 ④(LiveLock 제안 강등)의 근거는 전자다.
- **선행 SPEC의 예약 조항 3곳 (본 SPEC의 직접 발주서)**:
  - `SPEC-COPILOT-LOOKLIB-001/spec.md:176-178` — 시퀀스·큐 축을 P1-1의 영역으로 남긴 최초 기록.
  - `SPEC-COPILOT-BUSKWIZ-001/spec.md:143-146` Out of Scope 절 — 절 제목이 문자 그대로 "**Out of Scope — P1-1 송 구조 큐리스트 생성기**"(`:144`)이고 본문(`:146`)은 "음원 분석(구간/BPM/에너지), **타임코드 트랙·섹션 마커 생성**, 곡당 시퀀스 자동화 전부. **타임코드 문법은 룰북 전체에서 0건**이라 별도 라이브 프로브가 선행되어야 한다. 별도 SPEC."
  - `SPEC-COPILOT-BUSKWIZ-001/research.md:377-381` — 재사용 계약의 원문. "**P1-1이 쓸 수 있는 것 3종**"으로 슬롯 원장(`:379`) · 번들 결합 형상(`:380`) · 2단 보고 형상(`:381`)을 열거하고, `:381`이 "P1-1은 여기에 **섹션 축**(어느 곡 섹션의 룩이 죽었는가)을 얹으면 된다"고 적었다. `REQ-SONGCUE-016`이 그 한 문장의 실행부다. 같은 문서 `:385`가 타임코드에 대해 "별도 라이브 프로브가 선행되어야 한다 — 본 SPEC의 M0가 그것을 대신 측정하지 않는다"고 명시적으로 인계했다 — **ASSUMPTION-20은 본 SPEC이 새로 연 질문이 아니라 인계받은 질문이다.**
- **룰북이 스스로 남긴 인계 문장**: `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:225-227` — "`instantiate_look` creates presets only — **no cue, no sequence, no executor assignment.** Build whatever the operator has to FIRE afterwards with `run_commands`, recalling the presets it reports." 즉 룰북이 룩 계층의 공백으로 지목한 것이 정확히 큐·시퀀스이고, 그 공백을 메우는 것이 본 SPEC이다.
- **사용자 사전 확정 3건** (본 세션 이전, 재질의 금지 — 전문은 `spec.md §A 사전 확정 사실`): ① **음원 자동 분석은 범위 밖**(섹션 목록은 사용자가 제공), ② **타임코드는 M0 라이브 프로브 GO/DESCOPE 게이트**, ③ **큐 이름 ASCII 고정 + 한국어는 표현 계층**. 이 3건이 결정 A~C를 폐쇄한다(§9.1).

---

## §2. 조사 ① — MA3 시퀀스·큐 문법의 증거 지형 (T1~T5)

**본 SPEC 전체에 적용되는 규율**: 증거의 등급을 구분하지 않으면 "룰북에 있으니 된다"와 "실제로 돌았다"가 같은 무게로 섞이고, 그 순간 M0의 측정 대상이 흐려진다. BUSKWIZ가 익스큐터 축에서 3분류 표로 한 일을 본 SPEC은 **5등급**으로 한다 — 큐 축은 mock 자산이 오염원으로 끼어들기 때문이다(T4).

### 실측 구조

**등급 정의**

| 등급 | 뜻 | 판별 근거 |
|---|---|---|
| **T1** | 감사 로그에 **실제 실행 기록**이 있다 | `server/audit_logs/*.jsonl`에 `"event": "executed"` · `"ok": true` · `"detail": "OK"` |
| **T2** | 룰북의 **라이브 선언 아래**에 있으나 실행 기록은 없다 | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:7` — "Every pattern below was validated live on onPC 2.4.2." **라이브 선언을 가진 룰북 파일은 정확히 이 1개다**(전수 확인: `SPEC-COPILOT-BUSKWIZ-001/research.md:141`, 본 문서가 v2.4.2 디렉터리 파일 5개 목록으로 재확인 — `00_grammar.md` · `10_object_model.md` · `20_korean_terms.md` · `30_plugin_patterns.md` · `31_choreography_patterns.md`) |
| **T3** | 룰북 **산문·표에만** 있고 라이브 표시가 없다 | 위 4개 파일 |
| **T4** | **mock 전용 자산에만** 있다 | `server/measurement/corpus.yaml:7-10`이 스스로 "the deterministic offline action for M6a mock runs **ONLY**" 이며 커맨드는 "structurally valid" 할 뿐이라고 한정한다. 대응 감사 기록은 `detail: "offline mock execution: …"` |
| **T5** | 리포지토리 전체 **0건** | grep 전수 |

**정적 실측 1 — 라이브 큐 커맨드 전수 census (본 plan-phase, 라이브 아님)**: `server/audit_logs/*.jsonl` 12개 파일 전체에서 문자열 `Cue `를 담은 줄은 **10줄**이고, 이벤트 종류별로 `executed` 5 · `approved` 4 · `rejected` 1이다. 실제 실행된(`"event": "executed"`) **커맨드는 5건이고 서로 다른 5개 문자열이며, 전부 `Cue 1`이다**:

```
Store Sequence 17 Cue 1 'Golden Chorus'                  audit-20260726.jsonl:538
Store Sequence 22 Cue 1 'Golden Chorus'                  audit-20260726.jsonl:327
Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4        audit-20260719.jsonl:186
Store Sequence 62 Cue 1 'Cyan Look'                      audit-20260719.jsonl:148
Store Sequence 90 Cue 1 'Blue Look'                      audit-20260722.jsonl:1057
```

**5건 전부 `ok: true` · `detail: "OK"`이고, 5건 전부 서로 다른 시퀀스 번호(17 · 22 · 30 · 62 · 90)에 대한 첫 저장이다.** `Cue 2` 이상은 라이브에서 한 번도 실행된 적이 없다.

**정적 실측 2 — mock 판별**: 감사 로그에 등장하는 `Cue 12` 계열은 전부 `.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73`이며, 세 줄 모두 `"detail": "offline mock execution: …"`이다(`Store Cue 12` · `Label Cue 12 '오프닝'` · `Store Cue 5 Fade 3`). 출처는 `server/measurement/corpus.yaml:68`(`Store Cue 12`) · `:69`(`Label Cue 12 "Opening"`) · `:76`(`Store Cue 5 Fade 3`)이며, 파일 자신이 `:7-10`에서 mock 전용임을 선언한다. **`corpus.yaml:69`는 큰따옴표를 쓴다 — `server/rulebook/assets/v2.4.2/00_grammar.md:26-29`가 생성 커맨드에서 이를 금지한다**("the transport wraps command lines in double quotes and an embedded double quote breaks the command"). 즉 그대로 발화하면 깨지는 형태다.

**항목별 등급 (전수 확정)**

| # | 항목 | 등급 | 근거 |
|---|---|---|---|
| 1 | `Store Sequence <n> Cue <m> '<name>' CueFade <t>` | **T1** | 룰북 `31_choreography_patterns.md:50` + 실행 `server/audit_logs/audit-20260719.jsonl:186` |
| 2 | `Store Sequence <n> Cue <m> '<name>'` | **T1** ×4 | 룰북 `31_choreography_patterns.md:71` + 실행 `audit-20260719.jsonl:148` · `audit-20260722.jsonl:1057` · `audit-20260726.jsonl:327` · `:538` |
| 3 | `Label Sequence <n> '<name>'` | **T1** | 룰북 `00_grammar.md:27` + 실행 `audit-20260726.jsonl:328` |
| 4 | `Off Sequence <n>` / `Go+ Sequence <n>` | **T1** | 라이브 관측 `SPEC-COPILOT-SHOWUI-001/progress.md:459`(`Off Sequence 41`), `:460`(시퀀스 90에 `Go+`/`Off` 둘 다 `ok=True`), `:463`(`Go+ Sequence 41 ok=True`). 문법 출처는 둘로 갈린다 — `Off Sequence 11`은 라이브 선언 파일 `31_choreography_patterns.md:124`에 있으나 **`Go+ Sequence <n>`은 그 파일에 없다**(`:100`은 `Go+ Executor 191`이다). `Go+ Sequence 2`의 문법 출처는 라이브 표시 없는 `00_grammar.md:48`이며, **T1 등급은 룰북이 아니라 실물 관측이 부여한다** |
| 5 | `Assign Sequence <n> At Executor <m>` | **T1** | 룰북 `31_choreography_patterns.md:99` + 실행 `audit-20260719.jsonl:149`, `:187` |
| 6 | **같은 시퀀스에 `Cue 2` 이상 (`/Merge`)** | **T2 — 라이브 0건** | 룰북 `31_choreography_patterns.md:54-55`("The sequence auto-creates on the first store. Add more cues to it: `Store Sequence 11 Cue 2 'Blue Wash' CueFade 2 /Merge`"). 라이브 실행 **0건**(정적 실측 1). 등장하는 `Cue ≥ 2`는 전부 T4 |
| 7 | **`Set Cue <m> Sequence <n> Property 'TrigType' 'Time'` / `'TrigTime' <t>`** | **T2 — 라이브 0건** | 룰북 `31_choreography_patterns.md:111-112`, 절 제목 `:106`("Self-running / auto-advance cues — validated form"), 형식 지시 `:108`("Use the PROPERTY form (validated on 2.4.2)"). 감사 로그 0건 |
| 8 | 소수 큐 번호 (`Cue 1.5` · `1.55`) | **T2** | 룰북 `31_choreography_patterns.md:56`. 라이브 0건 |
| 9 | 저장 플래그 `/Merge` · `/Overwrite` · `/Remove` · `/CueOnly` | **T2** | 룰북 `31_choreography_patterns.md:57-59`. `/Overwrite`는 같은 줄이 "DESTRUCTIVE → the safety gate routes it to human approval"이라 적고 `server/safety/blacklist.yaml:18` `"Store /overwrite"`가 이를 강제한다 |
| 10 | `Store Cue <n>` (Sequence 미지정) | **T3 + T4** | 룰북 `00_grammar.md:42`(표), `:56`(`Store Cue 5 Fade 3`), `:69`(`Store Cue 3 Fade 2.5`) — 전부 라이브 표시 없는 파일. mock `corpus.yaml:68`, `:76` |
| 11 | **`Label Cue <n> '<name>'` 독립 동사** | **룰북 0건, T4만** | 리포지토리 유일 등장이 `corpus.yaml:69`이고 그것은 큰따옴표라 `00_grammar.md:26-29` 위반이다. **큐 이름을 붙이는 방법으로 확정 가능한 것은 store 인라인 3번째 토큰뿐이다**(항목 1·2, T1) — §9.4 결함 ① |
| 12 | `Delete Cue <n>` | **T5** | 리포지토리 0건. `Delete` 동사 자체는 룰북 `00_grammar.md:45`에 예시 `Delete Sequence 9`로 있으나 **블랙리스트 1항목**이다(`server/safety/blacklist.yaml:15` `"Delete"`) |
| 13 | 타임코드 일체 | **T5** | §3 전수 |
| 14 | 별도 Marker / Mark 오브젝트 | **T5** | §3 전수 |
| 15 | 시퀀스 자동 생성 (첫 store 시) | **T2 + T1 정황** | 룰북 `31_choreography_patterns.md:54`. 정황: T1 **5건**(항목 1·2)이 **전부 신규 번호**(62 · 30 · 90 · 22 · 17)에 대한 첫 저장이고 5/5 성공했다 |
| 16 | `Goto Cue <m> Sequence <n>` | **T3 + 게이트 보류** | 룰북 `00_grammar.md:48`, `31_choreography_patterns.md:100` 주석. **안전 게이트가 참조를 추출하지 못해 보류한다** — §5 후단 |

### 함의

1. **T1은 재사용하고 T2 이하는 M0가 잰다 — 이것이 본 SPEC 전체의 근거 규율이다.** 항목 1~5(T1)는 그대로 발화해도 되고 M0의 측정 예산을 쓸 필요가 없다. 항목 6~9(T2)는 룰북이 라이브를 선언한 파일 안에 있지만 **그 선언은 파일 헤더의 포괄 선언**(`31_choreography_patterns.md:7`)이지 줄 단위 실행 증거가 아니다 — 그 차이가 무너지면 미검증 문법이 T1 행세를 하고, 실패는 M3 저작이 아니라 M7 라이브에서 처음 드러난다. 항목 12~14(T5)는 발화 후보에서 제외되며, `REQ-SONGCUE-010`(파괴적 커맨드 금지) · `REQ-SONGCUE-013`/`REQ-SONGCUE-015`(타임코드·`/trig=`)가 이를 문언으로 고정한다.
2. **본 SPEC의 핵심 형상이 정확히 미검증 구간(항목 6)에 놓인다.** `REQ-SONGCUE-007`은 "곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개"를 요구하는데, 섹션이 2개 이상이면 **반드시** 같은 시퀀스에 `Cue 2` 이상이 필요하다. 그리고 그 형태의 라이브 실행 기록은 리포지토리 전체에서 0건이다(정적 실측 1). **따라서 ASSUMPTION-21은 DESCOPE 대상이 아니라 저작을 막는 블로킹 게이트다** — 부정이면 산출물 정의 자체가 성립하지 않고, "섹션마다 시퀀스 1개"로 도망치는 것은 §7 기각 (b)가 닫는다. `acceptance.md §C.0`이 M0에 `AC-SONGCUE-017`을 두고 그 안에서 ASSUMPTION-21을 **1번 측정 항목**으로 올린 것이 이 함의의 반영이다.
3. **`Cue 1` 5/5 성공은 "큐 저작이 검증됐다"가 아니라 "시퀀스 생성이 검증됐다"에 가깝다.** 5건 전부 서로 다른 신규 시퀀스 번호에 대한 **첫** 저장이므로, 실제로 라이브가 확인한 것은 항목 15(첫 store 시 시퀀스 자동 생성)와 항목 1·2의 **1큐 형태**다. 이 구분을 흐리면 ASSUMPTION-21이 "이미 검증된 것의 반복"으로 보이고 M0에서 생략된다.
4. **T4는 오염원이지 근거가 아니다 — 그리고 이 SPEC에서 가장 유혹적인 오염원이다.** `corpus.yaml`의 `Store Cue 12` / `Label Cue 12` 는 "큐를 다루는 커맨드"처럼 생겼고 감사 로그에 `ok: true`로 남아 있다. `detail` 필드를 읽지 않으면 T1과 구별되지 않는다. run-phase가 감사 로그를 근거로 인용할 때 **`detail`이 `"OK"`인지 `"offline mock execution: …"`인지를 반드시 함께 인용해야 한다** — 본 문서의 모든 T1 인용이 그 필드를 함께 적는 이유다.
5. **`Delete`는 T5와 블랙리스트의 이중 차단이다.** `REQ-SONGCUE-010`의 "`Delete` 계열 0건"은 승인 보류를 회피하려는 것이 아니라 **애초에 발화하지 않는 것**이다 — 발화하면 `blacklist.yaml:15`가 잡아 승인 카드가 뜨고, 초안 생성기가 사람에게 삭제 승인을 요구하는 순간 "초안"이라는 정의가 무너진다.

---

## §3. 조사 ② — 타임코드 0건의 직접 확인, 그리고 로드맵과의 모순

### 실측 구조

**정적 실측 3 — 타임코드 5경로 전수 (본 plan-phase, 라이브 아님)**. 검색 패턴은 대소문자 무관 `timecode` · `time-code` · `Timecode`이고, 훑은 경로는 다섯이다:

| 경로 | 무엇이 있는가 | 매치 |
|---|---|---|
| `server/rulebook/assets/v2.4.2/` | 룰북 자산 **5개 파일 전량**(`00_grammar.md` · `10_object_model.md` · `20_korean_terms.md` · `30_plugin_patterns.md` · `31_choreography_patterns.md`) | **0건** |
| `server/` | 서버 코드 · 테스트 · 감사 로그 · 측정 코퍼스 전량 | **0건** |
| `console/` | 콘솔측 Lua 응답기·플러그인 전량 | **0건** |
| `.moai/project/` · `.moai/state/` | 프로젝트 정본과 검증 산출물 전량 | **0건** |
| `ui/src/` | 프런트엔드 소스 전량 | **0건** |

**리포지토리 전체에서 타임코드가 등장하는 유일한 지점은 외부 참고 링크 텍스트다** — `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:125`(grandMA3 타임코드 실무 블로그 · MA Lighting 포럼 스레드)와 `:127`(Timecode vs Busking 블로그). 둘 다 §참고문헌 절의 하이퍼링크 제목이며 **문법도 커맨드도 오브젝트 이름도 아니다.**

**정적 실측 4 — Marker 오브젝트 전수**. `server/` · `console/` · `ui/src/` 전체에서 `Marker`/`MARKER`를 훑은 결과, 매치는 전부 **Python·TypeScript 내부 상수**다: `server/web/session.py:56` `UNCONFIRMED_MARKER = "execution unconfirmed"` · `server/web/panel.py:580` `_UNCONFIRMED_MARKER` · `server/llm/gemini_adapter.py:61` `_CACHE_MISS_MARKER` · `:66` `_MISSING_KEY_MARKERS` · `server/web/korean_errors.py:33` `_MISSING_KEY_MARKERS` · 나머지는 테스트 전용(`server/tests/test_deploy_tauri_shell.py:52` · `server/tests/test_deploy_cross_language_scan.py:259` · `ui/src/protocol.test.ts:173`). **MA3 오브젝트로서의 Marker / Mark은 룰북 · 코드 · 응답기 어디에도 0건이다.**

**모순의 형태 — 요구는 3곳에 있고 근거는 0곳에 있다.**

| 무엇이 타임코드·섹션 마커를 요구하는가 | 원문 |
|---|---|
| 제안서 P1-1 산출물 정의 | `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:71` — **"곡당 시퀀스 1개 + 타임코드 트랙 + 섹션 마커"라는 실무 표준 구조 그대로 MA3에 생성한다** |
| 로드맵 Phase 3 내용 열 | `.moai/project/product.md:39` — "음악 분석(구간/BPM/에너지) → **타임코드 큐리스트 초안 생성**, 장르별 룩 템플릿" |
| 설계 문서 Phase 3 | `DESIGN.md:158` — "음악 분석(구간/BPM/에너지, 로컬 라이브러리) → **타임코드 큐리스트 초안 생성**" |

**선행 SPEC이 이 모순을 이미 발견하고 인계했다**: `SPEC-COPILOT-BUSKWIZ-001/spec.md:146` — "타임코드 문법은 룰북 전체에서 **0건**이라 별도 라이브 프로브가 선행되어야 한다. 별도 SPEC." `SPEC-COPILOT-BUSKWIZ-001/research.md:385`가 더 강하게 못 박았다 — "**본 SPEC의 M0가 그것을 대신 측정하지 않는다.**" 즉 본 SPEC은 인계된 미결을 물려받은 것이지 새 미결을 연 것이 아니다.

### 함의

1. **로드맵이 요구하는 산출물의 3분의 1이 근거 0건 위에 서 있다.** 제안서 `:71`의 산출물은 세 조각이다 — (i) 곡당 시퀀스 1개, (ii) 타임코드 트랙, (iii) 섹션 마커. (i)은 T1~T2 혼합(§2 항목 1·2·6), (ii)는 **T5**, (iii)은 **T5**다. 이 사실을 SPEC 본문에 명시하지 않으면 run-phase는 "로드맵에 있으니 만든다"로 진입하고, 그 다음 수는 반드시 **문법을 지어내는 것**이다. `REQ-SONGCUE-013`(ASSUMPTION-20 GO일 때만 타임코드 발화, 아니면 0건 + DESCOPE 기록)과 `AC-SONGCUE-012` DESCOPE 분기가 그 진입을 문언으로 막는다.
2. **"섹션 마커"의 실체는 큐 이름 문자열뿐이다 — 이것이 본 조사의 실질 산출이다.** 별도 Marker 오브젝트가 0건이므로(정적 실측 4), 제안서가 말한 "섹션 마커"를 MA3에서 실현하는 방법은 **큐 이름에 섹션명을 넣는 것** 하나다. 그리고 그것은 이미 T1이다(§2 항목 1·2 — `Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4`가 라이브에서 성공했다). **따라서 (iii)은 DESCOPE 대상이 아니라 이미 해결된 항목이며, 그 해결 수단이 정확히 `REQ-SONGCUE-008`(ASCII 큐 이름)이다.** 이 연결을 기록하지 않으면 후속 SPEC이 "섹션 마커 기능"을 미구현으로 오해하고 없는 오브젝트를 찾아 나선다. §9.2가 이 항목을 미결에서 제거하는 근거다.
3. **DESCOPE는 실패가 아니라 정의된 결과다 — 그리고 여기서는 우회가 특히 쉽다.** 타임코드가 없다고 "시퀀스를 여러 개 만들어 시간을 흉내내자"거나 "`CueFade`를 누적해 절대 시각을 대신하자"는 것이 자연스러운 다음 수인데, 전자는 `REQ-SONGCUE-007`(곡 1개 = 시퀀스 1개) 위반이고 후자는 **관측하지 않은 것을 보고하는 것**이다(`CueFade`는 재조회로 읽을 수 없다 — §4). `AC-SONGCUE-017` 비고의 "**우회 금지**"가 이를 명문으로 막는다. 답은 DESCOPE이지 대체 구현이 아니다.
4. **ASSUMPTION-20의 기본 기대값은 부정 쪽이다.** BUSKWIZ의 ASSUMPTION-19가 "찾을 수 있는 모든 곳을 봤고 없다"였던 것과 같은 성격이다 — 룰북 5파일 · 서버 · 콘솔 · 프로젝트 정본 · 검증 산출물 · UI 전량이 침묵하고, mock 자산조차 타임코드 커맨드를 지어내지 않았다(§2 정적 실측 2의 corpus 3줄은 전부 `Cue` 계열이지 타임코드가 아니다). M0는 이를 뒤집을 기회이지 확인 절차가 아니며, **비파괴 범위에서 판정 불가면 그 사실 자체를 판정으로 기록한다**(`AC-SONGCUE-017` 측정 항목 3).

---

## §4. 조사 ③ — 생성한 초안을 앱이 스스로 검증할 수 없다 (실측 확정 사실)

### 실측 구조

- **결정적 부정 실측**: `SPEC-COPILOT-EXECREF-001/design.md:167` — 표의 Q3 행이 "큐가 커맨드를 나르는가?"에 대해 **"아니오, 이미 예상된 대로 확인됨. `DataPool/Sequences/1/1`, `/1/2`(기존 신뢰 본문 소스)는 `name`/`class`/`i`(+ 중첩 `Part` 자식)만 반환하고 커맨드/CMD 필드는 결코 반환하지 않는다"**라고 적고, 근거 열에 실측 로그 `.moai/state/verify/showui-m6-resume/5-probe-body.log`를 든다. 같은 표 `:165`가 "Q2 익스큐터 노드에 자식이 있는가? **아니오 — 결정적**"이고, `:157`이 이 절 전체를 "**2026-07-23 라이브 프로브로 해소되었다** … 실제 onPC 2.4.2, `state` 동사 전용 읽기 전용 프로브, 발화 0·쓰기 0"으로 못 박는다. **즉 이것은 코드 읽기가 아니라 실물 콘솔 실측이다.**
- **왜 그렇게 되는가 (응답기 구조)**: 같은 표 `:166`이 근본 원인을 적었다 — `console/lua/copilot_responder.lua`의 `build_snapshot`은 "완전히 범용이다 — 해석된 경로에서 `handle:Children()`을 호출할 뿐, 익스큐터 전용 로직이 없다." **정적 실측 5(본 plan-phase)**: 응답기 파일 875줄 전체에 문자열 `Cue`가 **0건**이다. 즉 응답기는 큐를 특별 취급하지 않으며, 큐가 보이는 것은 시퀀스 노드의 **자식 이름**으로서일 뿐이다.
- **재조회 경로는 존재하고 라이브 기록도 있다**: `server/safety/console.py:399` `DEFAULT_BODY_PATHS["Sequence"] = "DataPool/Sequences/{ref}"`. 이 경로가 실물에서 왕복한 기록은 `SPEC-COPILOT-EXECBODY-001/progress.md:180` — 감사 로그 verbatim 3줄 중 두 번째가 `{"command": "DataPool/Sequences/71", "kind": "state_query", "ok": true}`다. **즉 "시퀀스 본문을 조회할 수 있다"는 T1이고, "그 응답에 큐 프로퍼티가 들어 있다"는 부정 실측이다.** 두 사실은 양립한다.
- **응답이 실제로 무엇을 주는가**: `server/safety/console.py:471-484` — `payload["children"]`이 리스트여야 하고(`:471-473`), 각 자식에서 꺼내는 필드는 **`name` 하나뿐이다**(`:480`). 이름이 문자열이 아니거나 공백이면 `BodyUnavailable`을 던진다(`:481-482`). `CueFade` · `TrigType` · `TrigTime`을 담을 자리가 자료구조에 없다.
- **주소형 특례는 익스큐터 하나뿐**: `console/lua/copilot_responder.lua:405` `EXECUTOR_ADDRESS_PATTERN = "^Executor%s+(%d+)$"`이고, 바로 위 주석 `:397-404`가 "**This is the ONLY address form `resolve_path` special-cases**; every other path still walks the DataPool/Root/ShowData/Patch tree below unchanged"라고 명시한다. **`Cue <m> Sequence <n>` 같은 큐 주소형은 특례가 아니며, 응답기는 그것을 트리 워크로 떨어뜨린다.**
- **`console/lua/**`는 PRESERVE다**(`spec.md §C PRESERVE`). 응답기를 확장하면 큐 프로퍼티를 읽을 수 있을지 모르나, 그 확장은 그 자체로 별도 범위 결정이다 — `SPEC-COPILOT-EXECREF-001/design.md:171`이 같은 유혹을 명시적으로 거절했다: "S2를 구현하는 것은 **행동 변화 없이 안전-critical 코드에 새로운 미검증 주소 가정 하나를 추가하는 것**뿐이다. … 이것은 지름길이 아니라 정당한 YAGNI 판단이다."

### 함의

1. **본 SPEC의 파이프라인은 구조적으로 write-only다.** 앱은 커맨드를 보내고, 콘솔은 `ok: true`를 답하고, 재조회는 **큐가 몇 개 있고 이름이 무엇인지**까지만 알려준다. 시간(`CueFade`) · 자동 진행(`TrigType`/`TrigTime`) · 실제로 캡처된 값 — 초안의 품질을 결정하는 세 축 전부가 재조회로 확인 불가다. **최종 검증자는 콘솔 GUI 앞의 사람이다.**
2. **그러므로 `REQ-SONGCUE-017`의 요구는 "확인하라"가 아니라 "확인의 한계를 말하라"이다.** `AC-SONGCUE-014` 구간 ②가 "**`CueFade`·`TrigType`을 확인했다고 주장하는 필드가 0건**"을 기계로 판정하는 이유가 이것이다 — 이 프로젝트에서 가장 나쁜 실패는 잘못된 큐가 아니라 **잘못된 큐를 확인했다고 보고하는 것**이다. 부정 실측이 이미 존재하는데 확인 필드를 만드는 것은 실수가 아니라 거짓말이 된다.
3. **`ok: true`를 성공으로 읽으면 안 되는 구체적 사례가 이미 있다.** `AC-SONGCUE-017` 측정 항목 4가 "**파싱 성공과 효과 발생을 구분해 기록한다** — `Cmd()`가 거부된 커맨드에도 OK를 보고한 실측 사례가 있다"고 요구하는 근거가 이 성질이다. ASSUMPTION-22(`TrigType`/`TrigTime`)는 특히 위험한데, 프로퍼티 설정은 **효과가 즉시 눈에 보이지 않고** 재조회로도 읽히지 않기 때문이다 — M0가 파싱 성공만 보고 GO를 선언하면 M7에서도 드러나지 않고 **공연장에서 드러난다.**
4. **동시에 이 한계가 검증을 무의미하게 만들지는 않는다.** 재조회는 `REQ-SONGCUE-007`의 핵심 불변식 — **"큐 N개가 서로 다른 번호로 존재하는가"** — 을 답할 수 있다. 하드 결함 1(큐 번호 비전진)은 정확히 이 층위에서 관측 가능하며, `AC-SONGCUE-018` 기대 결과 3("재조회에서 시퀀스 1개에 큐 N개가 **서로 다른 번호로** 존재하고 이름이 일치한다")이 그것을 종단으로 잡는다. **검증 가능한 것과 불가능한 것의 경계를 정확히 긋는 것이 이 조사의 산출이지, 검증을 포기하는 것이 아니다.**

---

## §5. 조사 ④ — 큐 이름이 안전 게이트의 본문 라인이 되는 코드 경로

### 실측 구조

**4단계 체인 (각 단계 실측)**

| 단계 | 무슨 일이 일어나는가 | 근거 |
|---|---|---|
| **①** 시퀀스를 참조하는 커맨드가 게이트에 들어오면, 게이트는 그 **본문**을 가져온다 | `StateBodyFetcher.fetch_body`(`server/safety/console.py:414`)가 `DEFAULT_BODY_PATHS`(`:396-400`)에서 `Sequence` 템플릿(`:399` `DataPool/Sequences/{ref}`)을 골라 조회한다 | `server/safety/console.py:399`, `:414-421` |
| **②** 응답의 **자식 `name`이 그대로 본문 "라인"이 된다** | `_fetch_body_at_path`(`:464`)가 `children`을 순회하며 각 자식의 `name` 필드만 꺼내 `lines`에 넣고 튜플로 반환한다. `name` 외의 필드는 읽지 않는다 | `server/safety/console.py:478-484` |
| **③** 그 라인 하나하나에 **문법 검증이 걸린다** | `_evaluate`(`server/safety/expand.py:72`)가 `for line in body:`(`:106`) 안에서 `validate(line)`을 호출하고(`:107`), `not grammar.ok`이면 즉시 `_hold("unverifiable body line in …")`으로 **보류**한다(`:108-109`). 이어서 `classify_command`로 블랙리스트도 검사한다(`:110-112`) | `server/safety/expand.py:106-112` |
| **④** 그 문법 검증의 선두 토큰 규칙이 **ASCII 전용이다** | `_VERB_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]*$")` — 첫 글자는 ASCII 영문자, 이후는 ASCII 영숫자·`_`·`+`·`-`뿐이다 | `server/safety/grammar.py:20` |

**왜 이것이 스타일이 아니라 위험인가.** `server/safety/grammar.py:3-10`의 모듈 독스트링이 설계 의도를 적었다 — "STRUCTURAL parsing … the leading token must be verb-shaped … **Over-blocking is acceptable (safety asymmetry)**." 즉 게이트는 **의심스러우면 막는 쪽**으로 설계되었고, 큐 이름이 우연히 동사 모양이 아니면(한글 첫 글자는 반드시 그렇다) 그 시퀀스를 참조하는 **모든 후속 커맨드가 승인 보류로 떨어진다.** 큐를 만드는 시점이 아니라 **나중에 그 시퀀스를 재생하려 할 때** 터진다.

**ASCII 큐 이름의 종단 통과는 라이브 관측이 있다.** `SPEC-COPILOT-SHOWUI-001/progress.md:460` — `Store Sequence 90 Cue 1 'Blue Look' ok=True` → 패널 핀 `sequence:90` 생성 → **`Go+/Off Sequence 90 ok=True`**. 즉 큐 `'Blue Look'`을 담은 시퀀스 90에 대해 재생·정지가 둘 다 통과했다. 같은 표 `:459`(`Off Sequence 41`)와 `:463`(`Go+ Sequence 41 ok=True`)이 같은 경로의 추가 관측이다. **한국어 큐 이름의 종단 효과는 미관측이다** — 감사 로그의 한글 이름 큐(`Label Cue 12 '오프닝'`)는 `.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72`의 **offline mock**이며(§2 정적 실측 2), mock 실행은 게이트의 본문 조회 경로를 밟지 않는다.

**부수 실측 — 게이트는 `Cue`를 참조 타입으로 알지 못한다.** `server/safety/classify.py:44` `RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor")` — **`Cue`가 없다.** 귀결은 둘로 갈린다:

- **`Store …`는 어느 분기도 아니라 `safe`다.** `server/tests/test_safety_classify.py:63-66`이 `Store Cue 5`를 `category == "safe"` · `risky is False`로 고정하고, `:150`이 같은 판정을 재확인한다. 즉 본 SPEC의 저작 번들은 게이트에서 **승인 보류를 유발하지 않는다** — 이것이 "승인 1회"가 성립하는 이유다.
- **`Goto Cue <m> Sequence <n>`은 보류된다.** `server/tests/test_safety_classify.py:114`가 `("Goto Cue 3", None)` — 참조 추출 결과가 `None`임을 고정한다. `None`이 `expand.py:82-83`에 도달하면 `_hold("unverifiable reference: no recognizable target object")`다. 프로젝트가 이 과보류를 이미 인정하고 기록했다 — `SPEC-COPILOT-MVP-001/progress.md:215` — "인식 불가 참조(`Goto Cue 3` 등)는 전부 미검증 보류 — `Go Cue` 상용 패턴도 보류됨(**과보류 인정**, M5/M6에서 fetcher map 튜닝; 안전 기본값 유지)."

### 함의

1. **`REQ-SONGCUE-008`의 ASCII 고정은 표기 취향이 아니라 게이트 통과 조건이다.** 체인 ①→④가 성립하므로, 한국어 큐 이름은 **그 시퀀스를 참조하는 미래의 모든 커맨드**를 보류 위험에 놓는다. 게다가 실패 시점이 생성 시점과 분리되어 있어(생성은 성공하고 재생이 막힌다) 원인 추적이 어렵다. `AC-SONGCUE-007` 구간 ①이 "생성 커맨드 전수 `c.isascii()` 전량 True"를 기계 판정하는 근거가 이 체인이다.
2. **동시에 "한국어를 쓰지 않는다"가 아니다 — 층을 나눈다.** BUSKWIZ가 이미 형상을 세웠다: `server/looks/report.py:63` `_REASON_LABELS`와 `:74` `_VERDICT_LABELS`가 한국어를 **표현 계층에만** 둔다. 같은 파일 `:60-62`의 주석이 그 이유를 적었다 — "표현 계층의 한국어 라벨. **자산이나 스키마가 아니라 여기** 산다 — `matching.py:17-19`가 장르 별칭을 자산이 아닌 코드 표에 둔 것과 같은 이유다." `AC-SONGCUE-007` 구간 ②(보고 렌더에 한글 존재)와 ③(자산·스키마에 한국어 필드 0건)이 이 비대칭을 양쪽에서 고정한다.
3. **본 SPEC의 저작 경로가 승인 보류를 유발하지 않는다는 사실은 설계 전제다.** `Store …`가 `safe`이므로(`test_safety_classify.py:63-66`, `:150`) "단일 번들 · 승인 1회"는 게이트 정책과 충돌하지 않는다. 만약 `/Overwrite`를 쓰면 `blacklist.yaml:18`이 즉시 승인 카드를 띄우고 그 전제가 깨진다 — `REQ-SONGCUE-010`이 파괴적 플래그를 금지하는 두 번째 이유가 이것이다(첫 번째는 "덮는 것은 초안 생성기의 일이 아니다").
4. **섹션 점프 UX는 문법 문제가 아니라 게이트 참조 인식 확장 과제다.** `Goto Cue <m> Sequence <n>`은 룰북에 있고(`00_grammar.md:48`) 형태도 정당하지만, `classify.py:44`에 `Cue`가 없어 참조가 추출되지 않고 `expand.py:82-83`이 보류한다. 이 축을 열려면 **닫힌 집합 하나를 고쳐야 하며**, `classify.py:34-35`의 주석이 그 개정을 "deliberate, intentional revision of this closed set — weighted the same as a `blacklist.yaml` revision"으로 규정한다. 본 SPEC의 산출물은 큐리스트이지 재생 UX가 아니므로 이 축은 열지 않는다 — §10이 후속 SPEC으로 보낸다.

---

## §6. 조사 ⑤ — BUSKWIZ가 이 SPEC에 인계한 것 (재사용 계약 9종)

`SPEC-COPILOT-BUSKWIZ-001/research.md:377-381`이 "P1-1이 쓸 수 있는 것 3종"으로 예약했으나, 실제 출하 코드를 열어 보면 인계 항목은 **9종**이다. 아래는 각 항목이 **어떤 함수가 어떤 보장을 주는가** 수준으로 정리한 것이다.

### 실측 구조

**정적 실측 6 — 재사용 계약 9종 대조 (본 plan-phase, 라이브 아님)**

| # | 무엇 | 어떤 함수 | 그 함수가 주는 보장 | 본 SPEC이 쓰는 방식 |
|---|---|---|---|---|
| **1** | **슬롯 원장 형상** | `server/looks/busking.py:158` `_advance(pools, created) -> PoolIndex` | frozen `PoolBinding`/`PoolIndex`를 **고치지 않고 바깥에서 감싼다** — `replace(...)`로 새 인덱스를 만들어 돌려주므로 `build_instantiation`은 순수한 채로 남는다. 주석 `:161-163`이 그 이유를 적었다("그 자료구조를 고치는 순간 단일 룩 경로와 **P1-1 소비자**까지 함께 흔들린다"). 미관측 풀(`occupied is None`)은 전진시키지 않는다(`:176-180`) | **큐 번호 전진**이 같은 형상의 시간축 판본이다. `server/looks/instantiate.py:307-312` `_first_free_slot`은 `slot = 1`에서 시작해 점유에 없을 때까지 `+1`만 하는 **순수 함수**라 소비자가 누구든 전진하지 않는다 — 하드 결함 1의 진원 |
| **2** | **번들 결합 형상** | `server/looks/busking.py:189` `_merge(bundles)` | 목적지 커맨드는 **선두 1회**, 2번째 이후 번들은 선두가 같음을 확인한 뒤에만 떼어낸다(`:216-225`) — 다르면 `LookInstantiationError`(`:220-224`). 목적지 문자열을 **여기서 다시 적지 않는다**(`:198-200`). 덤으로 **룩별 구간 `[시작, 끝)`을 함께 반환한다**(`:202-206`, `:226`) — 실행 결과의 per-command status를 룩에 귀속시키는 유일한 다리 | 섹션 축에서 같은 비대칭을 지킨다. dedupe 면제 집합은 3종뿐이고(`server/orchestrator/tools.py:234-238`: `Clear` / `ClearAll` / 맨 `Fixture`\|`Group` 선택형) **`Store …`와 값 라인은 면제가 아니다** — `_is_programmer_state`(`:241-244`)가 `fullmatch`로만 판정한다 |
| **3** | **값 라인 충돌 가드** | `server/looks/busking.py:230` `VALUE_LINE_COLLISION` + `:240` `_guard_collision(look, plan, emitted)` | **거부(예외)가 아니라 건너뛰기 + 사유 보고**다. 주석 `:245-248`이 근거를 적었다 — `_plan_stores`(`server/looks/instantiate.py:325-384`)가 모든 "저장 불가"를 `SkippedStore`로 답하고 `LookInstantiationError`는 구조적 기형에만 쓰는 선례. 비교 문자열은 `instantiate._values_line`에서 **그대로 가져온다**(그 사실을 적은 주석은 `server/looks/busking.py:250-251`) — dedupe가 실제로 비교하는 그 문자열이며 재조립하면 두 곳이 갈라진다 | 섹션 축에서 재발하되 **확률이 구조적으로 더 높다** — 곡은 후렴이 반복되므로 같은 룩이 두 섹션에 배정되는 것이 예외가 아니라 정상이다. `AC-SONGCUE-011` 시나리오 4가 `Chorus 1` / `Chorus 2` 픽스처로 이를 고정한다 |
| **4** | **2단 보고 형상** | `server/looks/report.py:205` `build_report(bundle, outcomes)` · `:278` `to_korean(report)` · `:63` `_REASON_LABELS` · `:74` `_VERDICT_LABELS` | 룩별 판정을 **계획이 아니라 실행 결과에서** 산출한다(`:208-210` docstring — "계획 결과에는 중단 정보가 없기 때문이다"). 귀속은 `bundle.spans`가 다리를 놓고 결합 규칙을 재구현하지 않는다(`:211-212`). 사유 라벨은 8종 닫힌 집합(`:63-72`)이고 모르는 코드는 **지어내지 않고 그대로 통과**시킨다(`:77-83`). 판정은 3값(`:74` 전량 성공/부분/저장 0건) | 여기에 **섹션 축**을 얹는다 — `REQ-SONGCUE-016`. 집계만 내고 섹션별을 생략하는 것은 금지다. `to_korean`의 집계 한 줄(`:281-285`)이 그 형식의 원형이다 |
| **5** | **섹션 어휘** | `server/looks/matching.py:92` `DYNAMICS_TERMS` (내용 `:93-131`) | 섹션어 → 다이내믹스 밴드 매핑. 인트로 `:99-101`(1,2) · 벌스 `:103-104`(2,3) · 빌드/빌드업/프리코러스/라이저 `:106-113`(3) · 코러스/후렴/드랍/클라이맥스/엔딩 `:117-128`(4,5). **밴드가 의도적으로 넓다** — 모듈 독스트링 `:21-26`이 그 이유를 적었다("this table FILTERS, and an over-narrow filter drops a good look silently"). `:114-116`은 EDM 드랍이 다이내믹스 4로 저작돼 있어 단일 레벨 밴드면 사용자가 명백히 요청한 룩을 숨긴다는 실측 근거 | **재정의 금지** — `REQ-SONGCUE-003`. `AC-SONGCUE-003`이 raw grep이 아니라 **AST 식별자 스캔**으로 판정하는 이유는 산문이 어휘를 설명할 수 있기 때문이다 |
| **6** | **다이내믹스 축** | `server/looks/schema.py:35-36` `DYNAMICS_MIN = 1` / `DYNAMICS_MAX = 5` | 정수 1..5 폐쇄 구간. 같은 파일 `:20-25`의 `@MX:NOTE`가 이 스키마를 **P1-1/P1-2 공통 기반**으로 못 박았다 — "a breaking change here breaks two downstream SPECs at once." 이어서 `:23-25`가 `REQ-LOOKLIB-004`의 강제 기제를 설명한다 — "there is no group number, preset slot, FID or executor field to put a per-show value in, and the loader rejects unknown keys" | 읽기만 한다. `REQ-SONGCUE-020`(정적 진입 금지)이 스키마 쪽에서 이미 기계로 강제되고 있다는 뜻이며, 본 SPEC은 신규 모듈 쪽에서 같은 금지를 다시 세운다(`AC-SONGCUE-010` 구간 ③) |
| **7** | **룩 후보 전순서** | `server/looks/busking.py:81` `looks_for_genre(library, genre)` | 그 장르 룩 **전량**을 `(dynamics, look_id)` 오름차순으로 반환한다(`:92-97`). 모르는 장르는 예외가 아니라 **빈 튜플**이다(`:89-90` — "여기서는 '그런 룩이 없다'가 정직한 답이다"). 순서는 신규 발명이 아니라 `matching._ranked`의 타이브레이크가 점수 균일 구간에서 퇴화한 형태다(`:84-87`) | `REQ-SONGCUE-005`의 재사용 대상. `AC-SONGCUE-005` 구간 ②가 AST 식별자로 **재구현 0건**을 확인한다 |
| **8** | **단일 실행 경로** | `server/orchestrator/tools.py:483` `run_commands` → `:492` `bundle_gate.screen()` | 번들 전체가 정확히 한 경로로 스크리닝된다. 앵커 선례 **2개**가 이미 있다 — `:693-701`(instantiate_look: "This handler is a **CALLER of run_commands, never a second execution surface**") · `:817-824`(prepare_busking: "Reaching `execution_port` from here would be **invisible to the gate**"). 실행 루프는 **stop-on-first-failure**다(분기 `:535-543` — 첫 실패 이후 전부 `not_executed`, 플래그 세팅 `:569`) | 신규 툴은 **3번째 준수 사례**이지 새 규범이 아니다 — `REQ-SONGCUE-018`. `AC-SONGCUE-015` 구간 ①의 AST 스캔이 기계 확인한다 |
| **9** | **BUSKWIZ M0 실측 상한** | — (측정 기록) | `SPEC-COPILOT-BUSKWIZ-001/progress.md:200`, `:280` — **87줄 번들 87/87 성공 · 총 5.77s · 평균 66.3 ms/줄 · 누적 열화 없음** | ASSUMPTION-24의 계산 기준선. 곡 1개(섹션 6~10개) 번들 규모를 이 실측에서 **계산**하고, 계산이 87줄을 넘을 때만 M0에서 다시 잰다(`AC-SONGCUE-017` 측정 항목 5) |

**부수 실측 — 시퀀스 생성이 패널 핀에 자동 연동된다.** `server/orchestrator/last_created.py:30` `_STORE_SEQUENCE = re.compile(r"^\s*Store\s+Sequence\s+(\d+)\b", re.IGNORECASE)`가 실행된 커맨드에서 시퀀스 번호를 뽑아 다음 턴의 대상 정체로 주입한다(모듈 독스트링 `:3-8`). 두 성질이 본 SPEC에 직접 걸린다:

- **스냅샷 전용 · 최신 1건**이다 — `:17-18` — "It is snapshot-only: `parse_last_created` returns the SINGLE most-recent look, **never an accumulating history.**" 곡 1개 = 시퀀스 1개일 때만 이 형상이 정상 동작한다.
- **`Store Cue <m> Sequence <n>` 형태를 시퀀스 생성으로 읽지 않는다** — `:27-29` 주석이 "the parser anchors at the verb so a sequence named inside a modifier (e.g. `Store Cue 1 Sequence 71`) is NOT read as a 'Store Sequence' creation"이라 적고, `server/tests/test_last_created.py:58-61`이 이를 테스트로 고정한다(`parse_last_created(["Store Cue 1 Sequence 71"]) is None`).

### 함의

1. **본 SPEC이 새로 만들 것은 "시간축"뿐이고, 그 경계가 코드로 이미 그어져 있다.** 9종 전부가 소비 대상이며 신규 계층이 필요한 곳은 네 지점 — (a) 섹션 목록 파싱·검증(`REQ-SONGCUE-001`/`REQ-SONGCUE-002`), (b) 섹션 → 다이내믹스 → 룩 매핑(`REQ-SONGCUE-005`), (c) 큐 번호 원장과 큐리스트 번들 결합(`REQ-SONGCUE-007`/`REQ-SONGCUE-011`/`REQ-SONGCUE-012`), (d) 보고에 섹션 축 얹기(`REQ-SONGCUE-016`). `REQ-SONGCUE-001`~`REQ-SONGCUE-021`이 정확히 이 네 축을 덮는다.
2. **`REQ-SONGCUE-021`(PRESERVE 무변경)은 형상의 반증 장치이지 관료적 제약이 아니다.** BUSKWIZ가 §7(b)에서 세운 논리의 계승이다 — 설계는 "frozen 자료구조를 **바깥에서 감싼다**"이고, 그것이 성립하지 않아 `matching.py`나 `instantiate.py`를 고치게 되는 경우가 곧 **설계의 반증**이므로, 파일을 PRESERVE에 두면 그 반증이 **diff로 즉시 드러난다**. `AC-SONGCUE-016` 추가 assert("`server/looks/{matching,instantiate,resolver,schema,loader,roles}.py`의 diff가 빈 출력")가 그 장치다.
3. **큐 번호 전진은 슬롯 전진보다 판정이 쉽다 — 그리고 그 사실을 활용해야 한다.** 슬롯은 콘솔이 보고한 점유의 여집합에서 골라야 해서 "미관측 vs 빈 것"의 구분이 필요했지만(`server/looks/busking.py:176-180`), 큐 번호는 **섹션 입력 순서에서 온다** — `1`부터 `N`까지 결정론적이다. 따라서 `AC-SONGCUE-006` 구간 ②("큐 번호가 `1`부터 `N`까지 **빠짐없이 한 번씩**")는 리그 상태와 무관하게 순수 함수로 판정 가능하다. **미관측 문제가 남는 곳은 큐 번호가 아니라 시퀀스 번호다**(ASSUMPTION-23).
4. **stop-on-first-failure가 섹션 축에서 더 아프다.** `server/orchestrator/tools.py:535-543`은 첫 실패 이후 전부를 `not_executed`로 만든다(플래그는 `:569`에서 세워진다). 장르 팔레트에서는 프리셋 몇 개가 덜 만들어지는 것이지만, 큐리스트에서는 **곡의 뒷부분이 통째로 비는 것**이다 — 3번 섹션에서 실패하면 4~10번 섹션의 큐가 존재하지 않는다. `REQ-SONGCUE-016`의 섹션별 보고가 이 사실을 사람에게 전달하는 유일한 경로이며, 집계만 내면 "10개 중 3개 성공"이 되어 **어느 3개인지**가 사라진다. `AC-SONGCUE-013` 구간 ①("곡의 모든 섹션이 정확히 한 번씩 판정에 나타난다")이 그 소실을 막는다.
5. **`last_created.py`가 "곡 1개 = 시퀀스 1개"에 무료 보상을 준다.** 본 SPEC의 번들은 `Store Sequence <n> Cue 1 …`을 정확히 한 번 발화하므로(그 이후는 `Cue 2`, `Cue 3` …), 스냅샷 파서는 **정확히 그 시퀀스 하나**를 집는다 — `:27-29`가 `Store Cue … Sequence …` 형태를 생성으로 읽지 않기 때문이다. 만약 §7 기각 (b)의 "섹션마다 시퀀스 1개"를 채택했다면 스냅샷은 마지막 섹션의 시퀀스만 남기고 사용자의 "더 느리게" 후속 지시가 엉뚱한 대상에 걸렸을 것이다. **설계 선택이 기존 컴포넌트와 우연히 맞은 것이 아니라, 그 컴포넌트가 이 형상을 전제로 쓰였다.**

---

## §7. 고려하고 기각한 대안

### 기각 (a) — 큐가 프리셋을 참조하게 만든다 (프로그래머 상태 직접 캡처 대신)

- **내용**: BUSKWIZ가 만든 장르 팔레트를 재사용해, 각 섹션의 큐가 값을 직접 담는 대신 프리셋을 참조하게 한다. 값이 한 곳에 모여 수정이 쉽고 번들도 짧아진다.
- **기각 사유**:
  1. **문법 근거가 0건이다.** `Assign Preset … At Cue` 계열은 리포지토리 전체에서 매치가 없고, BUSKWIZ가 같은 축을 이미 전수로 훑었다 — `SPEC-COPILOT-BUSKWIZ-001/research.md:143`: "`Assign Preset` · `Store Executor` · `Label Executor` · `Preset <p>.<s> At …`를 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/`에 grep → **각각 0개 파일**." **mock 자산조차 이 형태를 지어내지 않았다.**
  2. **룰북 자신이 반대 방향을 지시한다.** `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:225-227` — "`instantiate_look` creates presets only … Build whatever the operator has to FIRE afterwards with `run_commands`, **recalling the presets it reports**." 즉 프리셋은 **프로그래머로 되불러서** 쓰는 것이고, 룰북이 아는 프리셋 동사 4종(`Store Preset` `00_grammar.md:67` · `Label Preset` `:68` · `Call Preset 4.1` `:59` · `At Preset 4.1` `:72`)은 **전부 프로그래머 쪽**이다.
  3. **T5를 발화하는 것은 본 SPEC의 증거 규율을 깨는 것이다.** §2 함의 1이 세운 규율("T1은 재사용하고 T2 이하는 M0가 잰다")에서 T5는 측정 대상조차 아니다 — 측정하려면 무엇을 보낼지부터 지어내야 한다.
- **채택 대안**: 큐가 프로그래머 상태를 직접 캡처한다(`spec.md §D "Out of Scope — 프리셋 생성"`). 룰북의 유효 레시피(`31_choreography_patterns.md:43-52`)가 정확히 그 순서다 — `ClearAll` → 선택 → 값 → `Store Sequence … Cue …` → `ClearAll`. 이 경로 전체가 T1이다.

### 기각 (b) — 섹션마다 시퀀스 1개를 만든다 (`Cue 2` 미검증 회피)

- **내용**: ASSUMPTION-21(같은 시퀀스에 `Cue 2` 이상)이 라이브 0건이므로, 섹션 N개를 **시퀀스 N개 × 큐 1개**로 만든다. 그러면 전부 T1 문법만 쓰고 M0의 블로킹 게이트가 사라진다. 실제로 라이브 실측 5건이 전부 이 형태다(§2 정적 실측 1).
- **기각 사유**:
  1. **산출물 정의가 무너진다.** 제안서 `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:71`이 요구한 것은 "**곡당 시퀀스 1개** + 타임코드 트랙 + 섹션 마커"이고, 그것이 "실무 표준 구조"라고 적힌 이유는 오퍼레이터가 익스큐터 하나로 곡 전체를 진행하기 때문이다. 시퀀스 10개는 익스큐터 10개를 요구하며, **익스큐터 축은 BUSKWIZ M0가 ASSUMPTION-16/17/19를 전부 DESCOPE로 판정해 닫아 둔 영역이다**(`SPEC-COPILOT-BUSKWIZ-001/progress.md:197-202`).
  2. **패널 핀 스냅샷이 깨진다.** `server/orchestrator/last_created.py:17-18`이 "**snapshot-only … never an accumulating history**"이므로 시퀀스 10개를 만들면 사용자에게 남는 대상 정체는 **마지막 하나뿐**이다. "더 느리게" 같은 후속 지시가 9개 섹션을 놓친다(모듈 독스트링 `:5-8`이 정확히 이 실패를 막으려고 쓰인 컴포넌트다).
  3. **미검증을 회피한 것이 아니라 옮긴 것이다.** 시퀀스 10개를 서로 다른 빈 번호에 만들려면 ASSUMPTION-23(빈 시퀀스 번호 식별)이 **10배로 중요해진다** — 하나만 틀려도 남의 시퀀스를 덮는다. 블로킹 게이트 하나를 없애고 더 위험한 게이트를 열 배 크게 만든다.
  4. **우회 금지가 요구에 이미 박혀 있다.** `AC-SONGCUE-017` 비고 — "**우회 금지** — 타임코드가 없다고 시퀀스·큐를 임의로 더 만들어 우회하지 않는다. DESCOPE가 답이다." 이 문언은 타임코드에 대해 쓰였지만 같은 논리가 ASSUMPTION-21에도 적용된다.
- **채택 대안**: ASSUMPTION-21을 **블로킹 게이트로 정직하게 세운다**. 부정이면 M3 저작을 착수하지 않는다(`AC-SONGCUE-017` 측정 항목 1). BUSKWIZ의 ASSUMPTION-18이 M2를 기술적으로 막았던 것과 같은 성격이며, **막히는 것이 잘못된 것을 만드는 것보다 낫다.**

### 기각 (c) — 큐 이름을 `Label Cue <n> '<name>'`으로 붙인다

- **내용**: 시퀀스에 `Label Sequence <n> '<name>'`(T1, `00_grammar.md:27` + `audit-20260726.jsonl:328`)이 있으니 큐에도 대응 동사를 쓴다. 저장과 명명을 분리하면 이름만 나중에 고치기도 쉽다.
- **기각 사유**:
  1. **룰북에 0건이다.** `Label Cue`는 `server/rulebook/assets/v2.4.2/` 5개 파일 어디에도 없다. `Label`의 룰북 예시는 `Label Group 7 'Wash L'`(`00_grammar.md:44`)과 `Label Sequence 3 'Chorus'`(`:27`)뿐이다.
  2. **유일한 리포지토리 등장처가 깨진 mock이다.** `server/measurement/corpus.yaml:69` `"Label Cue 12 \"Opening\""` — **큰따옴표**를 쓰는데 `00_grammar.md:26-29`가 이를 명시적으로 금지한다("the transport wraps command lines in double quotes and an embedded double quote breaks the command"). 대응 감사 기록도 `offline mock execution`이다(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72`). **즉 이 형태는 T4이면서 동시에 그대로 발화하면 깨지는 형태다.**
  3. **T1 대안이 이미 있고 더 간결하다.** 큐 이름을 store 인라인 3번째 토큰으로 넣는 형태는 라이브 5/5 성공이다(§2 정적 실측 1 — `Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4`). 별도 동사를 쓰면 번들이 섹션당 1줄 길어지고, 그 1줄은 T5다.
  4. **`REQ-SONGCUE-010`의 정신과 충돌한다.** 저장과 명명을 분리하면 "이름만 나중에 고친다"가 가능해지는데, 그것은 §D가 닫은 **큐 편집**의 입구다(`spec.md §D "Out of Scope — 큐 편집 · 재생성"`).
- **채택 대안**: **큐 이름은 store 인라인 3번째 토큰으로만 발화한다** — `Store Sequence <n> Cue <m> '<name>' [CueFade <t>]`. §9.4 결함 ①이 이 결정의 폐쇄 기록이다.

### 기각 (d) — dedupe 면제 집합에 `Store …`나 값 라인을 추가한다

- **내용**: 곡은 후렴이 반복되므로 값 라인이 겹치는 것이 정상인데, `server/orchestrator/tools.py:544`의 dedupe가 두 번째를 `skipped_already_executed`로 떨어뜨린다. 면제 집합(`:234-238`)에 값 라인을 넣으면 `_guard_collision` 없이 그냥 통과한다.
- **기각 사유**:
  1. **그것이 정확히 BUSKWIZ가 진단한 조용한 파괴의 기제다.** 값 라인이 dedupe로 탈락하면 직전 `ClearAll`은 면제라 살아남고(`:236`), 결과는 **빈 프로그래머 상태로 `Store`가 실행되는데 콘솔은 성공으로 답한다**. 면제를 넣으면 이 실패가 사라지는 것이 아니라 **탐지 지점이 사라진다** — 두 섹션이 같은 값을 캡처해 같은 큐 두 개가 되고, 사람은 뒤 섹션이 잘못됐다는 것을 공연에서 안다.
  2. **면제 집합은 열거형이고 원칙이 명문화돼 있다.** `tools.py:227-232`의 주석이 그 원칙을 적었다 — 면제는 "선두 동사가 무언가를 만들거나 부수지 않는" 커맨드에만 주어지며, 하나를 근거 없이 넣으면 "멤버십을 외워야 하는 목록"으로 퇴화한다. `Store …`는 정의상 **영속 산출물을 만드는** 커맨드다.
  3. **전역 실행 의미론을 이 SPEC 하나를 위해 바꾸는 것이다.** dedupe 블록은 `run_commands`를 쓰는 **모든** 소비자가 공유한다. `spec.md §D "Out of Scope — dedupe 규칙 개정"`이 이를 닫았고, `AC-SONGCUE-010` 구간 ②가 `<BASE>..HEAD` diff로 기계 확인한다.
- **채택 대안**: BUSKWIZ 결정 H를 계승한다 — `server/looks/busking.py:230` `VALUE_LINE_COLLISION` + `:240` `_guard_collision`. **거부가 아니라 건너뛰기 + 사유 보고**이며(`:245-248`), 번들은 여전히 실행 가능하고 앞 섹션은 온전하다(`AC-SONGCUE-011` 구간 ③). 코드 개정 0.

### 기각 (e) — 음원 자동 분석을 본 SPEC에 함께 넣는다

- **내용**: 제안서 `:70`이 "음원 파일을 분석(구간 분할·BPM·에너지 곡선)해 Intro/Verse/Chorus 구조를 뽑고"라고 적었으므로, 섹션 목록을 사용자에게 받는 것은 제안서 미달이다. 한 SPEC에서 끝낸다.
- **기각 사유**: **사용자 확정 ①로 기각되었다**(`spec.md §A 사전 확정 사실`). 근거는 세 축이 동시에 열린다는 것이고, 본 문서가 전부 실측으로 재확인했다:
  1. **오디오 의존성 0건.** `pyproject.toml:7-19`의 런타임 의존성은 9종(`anthropic` · `fastapi` · `google-genai` · `keyring` · `lupa` · `python-osc` · `pyyaml` · `uvicorn` · `websockets`)이고 오디오 라이브러리는 없다. `uv.lock`의 명명 패키지 **58종** 전수에서 `librosa` · `essentia` · `numpy` · `scipy` · `madmom` · `aubio` · `soundfile` · `torchaudio` **전부 무매치** — **numpy조차 없다.**
  2. **업로드 경로 0건.** `server/` 전체에 `UploadFile` · `File(` · `multipart` **0건**. 라우트 데코레이터는 리포지토리 전체 **8개**(`server/web/app.py:200` `@app.get("/healthz")` · `:205` `@app.websocket("/ws")` · `server/web/settings_api.py` 4개 · `server/web/provision_api.py` 2개)이고 어느 것도 파일을 받지 않는다. 채팅 입력은 텍스트 전용이다 — `server/web/app.py:311` `raw = await websocket.receive_text()`. UI 쪽도 `ui/src/` 전체에 `type="file"` **0건**.
  3. **Tauri capability가 업로드를 명시적으로 거부한다.** `src-tauri/capabilities/default.json:4` — "ALL network plugins are denied by omission (AC-DEPLOY-027 Layer 3): no http, no websocket, **no upload**, no geolocation." 테스트가 이를 강제한다(`server/tests/test_deploy_tauri_shell.py:344-353` — `TestCapabilityDeniesNetworkPlugins`, 클래스 독스트링 `:345`가 "capabilities deny network, shell = sidecar only").
  - 세 축에 더해 **진행률·취소 프로토콜이 현재 0건**이다 — 곡 1개 분석은 초 단위가 아니라 수십 초이므로 WebSocket 프로토콜에 새 이벤트 종류가 필요하다.
- **채택 대안**: 섹션 목록을 사용자가 제공한다(`REQ-SONGCUE-001` — DAW 마커 텍스트 또는 구조화 입력). **§10이 이 축을 후속 SPEC으로 명시 예약한다.** 제안서 미달이 아니라 **분할**이며, 분할선은 "MA3에 무엇을 쓰는가"(본 SPEC)와 "섹션 목록을 어떻게 얻는가"(후속) 사이다.

### 기각 (f) — 큐 이름을 한국어로 쓴다

- **내용**: 사용자는 한국어로 말하고 보고도 한국어다. 큐 이름이 `Intro` / `Chorus`면 콘솔 화면에서 한국인 오퍼레이터가 읽기 나쁘다. 섹션 어휘 표에 한국어가 이미 있으므로(`server/looks/matching.py:99-128`) 그대로 쓰면 된다.
- **기각 사유**:
  1. **사용자 확정 ③으로 기각되었고, 근거는 취향이 아니라 게이트 보류다.** §5의 4단계 체인 — `server/safety/console.py:478-484`(자식 `name` → 본문 라인) → `server/safety/expand.py:106-109`(라인마다 `validate`, 실패 시 `_hold`) → `server/safety/grammar.py:20`(`^[A-Za-z][A-Za-z0-9_+\-]*$`, ASCII 전용). 한글 첫 글자는 이 정규식을 통과할 수 없다.
  2. **실패가 생성 시점이 아니라 재생 시점에 터진다.** 저장은 성공하고, 나중에 그 시퀀스를 `Go+`하려 할 때 보류된다. 원인과 증상이 분리되어 있어 진단이 어렵다.
  3. **ASCII 쪽은 라이브 관측이 있고 한국어 쪽은 없다.** `SPEC-COPILOT-SHOWUI-001/progress.md:460`이 큐 `'Blue Look'`을 담은 시퀀스 90에 대해 `Go+`/`Off` 둘 다 `ok=True`를 관측했다. 한국어 큐 이름의 종단 효과는 **미관측**이고, 유일한 한글 큐 기록은 offline mock이다(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:72`).
  4. **자산·스키마에 한국어를 넣는 것은 별개의 더 큰 파괴다.** `server/looks/schema.py:20-25`의 `@MX:NOTE`가 스키마 변경이 두 하류 SPEC을 동시에 깨뜨린다고 경고하고, `server/looks/matching.py:16-19`가 같은 이유로 별칭을 자산이 아닌 코드에 두었다.
- **채택 대안**: **ASCII 고정 + 한국어는 표현 계층**(`REQ-SONGCUE-008`). 형상은 BUSKWIZ가 이미 세웠다 — `server/looks/report.py:63` `_REASON_LABELS` · `:74` `_VERDICT_LABELS`, 그리고 모르는 코드는 지어내지 않고 그대로 통과시키는 규율(`:77-83`). `AC-SONGCUE-007`이 세 구간으로 양쪽을 함께 고정한다(커맨드 전수 ASCII · 보고에 한글 존재 · 자산·스키마에 한국어 필드 0건).

### 기각 (g) — 시각이 어긋난 입력을 정렬해서 진행한다

- **내용**: 사용자가 `Verse 0:52 / Chorus 0:18`처럼 순서를 뒤집어 입력하면, 시각으로 정렬한 뒤 진행한다. 거부는 불친절하고 의도는 명백하다.
- **기각 사유**:
  1. **의도가 명백하지 않다 — 두 해석이 있고 결과가 다르다.** (i) 사용자가 순서를 잘못 적었다(정렬이 맞다), (ii) 사용자가 **시각을 잘못 적었다**(정렬하면 섹션 순서가 뒤바뀐다). 정렬은 (ii)를 (i)로 단정하는 것이고, 틀리면 **사용자가 의도한 적 없는 큐리스트가 쇼파일에 남는다**. 그리고 §4가 확정했듯 앱은 그것을 재조회로 발견할 수 없다.
  2. **이 프로젝트가 반복해서 거절해 온 실패 방향이다.** `server/looks/matching.py:28-33`의 `@MX:WARN`/`@MX:REASON`이 같은 유혹을 이름으로 적었다 — "matching must never manufacture a look … The tempting edits are all the same edit: lower the confidence bar, widen a term to a substring, or return 'the closest look anyway'." 시각 정렬은 그 목록의 네 번째 항목이다.
  3. **같은 규율이 인접 요구에 이미 두 번 적용돼 있다.** `REQ-SONGCUE-004`(모르는 섹션 이름의 다이내믹스를 추정하지 않는다)와 `REQ-SONGCUE-006`(맞는 룩이 없으면 가장 가까운 것으로 승격하지 않는다). 셋 중 하나만 추정을 허용하면 규율이 규율이 아니라 사례별 판단이 된다.
  4. **거부가 정보 손실이 아니다.** `REQ-SONGCUE-002`는 거부하되 **어느 항목이 왜 어긋났는지** 보고하도록 요구하므로, 사용자는 두 해석 중 어느 쪽인지 스스로 고를 수 있다. 정렬은 그 선택권을 빼앗는다.
- **채택 대안**: 거부 + 사유 보고. `AC-SONGCUE-002` 추가 assert가 "**정렬해서 진행하지 않는다** — 거부 후 반환에 섹션 목록이 들어 있지 않거나, 들어 있다면 입력 순서와 동일하다(임의 재배열 0건)"로 기계 판정한다.

### 채택 — 출하된 조율 계층 위의 **시간축 래퍼** + 큐 번호 원장 + 단일 번들

- **입력**: 사용자 제공 섹션 목록을 파싱·검증한다. 시각 3종 포맷을 밀리초 정수로 정규화하고(`AC-SONGCUE-001` 구간 ②), 단조성 위반은 거부한다(기각 (g)).
- **어휘**: `server/looks/matching.py:92` `DYNAMICS_TERMS`를 **import해서** 쓴다. 재정의 0건(`AC-SONGCUE-003` AST 스캔).
- **매핑**: `server/looks/busking.py:81` `looks_for_genre`의 전순서를 재사용하고, 다이내믹스 미스는 승격하지 않고 미매핑으로 보고한다.
- **번호**: 큐 번호는 **섹션 입력 순서**에서 온다(`1..N`, 결정론적). 시퀀스 번호는 **리그 조회 결과의 여집합**에서 고르며, 조회 실패·절단 시 추측하지 않고 거부한다(`AC-SONGCUE-008` 구간 ②).
- **문법**: T1만 무조건 발화한다 — `Store Sequence <n> Cue <m> '<name>' [CueFade <t>]`(§2 항목 1·2). `Cue 2` 이상과 `/Merge`(T2, ASSUMPTION-21)는 M0 GO가 전제다. 타임코드·`TrigType`/`TrigTime`(T5/T2)은 각각 ASSUMPTION-20·ASSUMPTION-22 게이트 뒤에 있다. 큐 이름은 store 인라인 3번째 토큰으로만 넣고 ASCII 고정이다(기각 (c)·(f)).
- **결합**: `server/looks/busking.py:189` `_merge`의 비대칭을 계승한다 — 목적지 선두 1회 + 섹션 단위 `ClearAll` 전량 유지. dedupe 규칙 무개정(기각 (d)).
- **충돌**: `server/looks/busking.py:230`/`:240`의 건너뛰기 + 사유 보고를 섹션 축에 적용한다.
- **실행**: 신규 툴 1종 → `server/orchestrator/tools.py:483` `run_commands` 재진입 → `:492` `bundle_gate.screen()`. 신규 실행 표면 0(앵커 선례 `:693-701`, `:817-824`).
- **보고**: `server/looks/report.py`의 2단 형상에 **섹션 축**을 얹는다. 재조회는 **존재와 이름**까지만 주장하고 프로퍼티 한계를 명시한다(§4).

---

## §8. 핵심 참조 파일

| 파일 | 역할 |
|---|---|
| `server/rulebook/assets/v2.4.2/31_choreography_patterns.md` | **라이브 검증을 선언하는 유일한 룰북 파일**(`:7`). T1 큐 저작 레시피(`:43-52`, 특히 `:50`)와 `:71`. **T2 핵심 3건** — 같은 시퀀스에 큐 추가 `/Merge`(`:54-55`, ASSUMPTION-21) · 소수 큐 번호(`:56`) · 자동 진행 프로퍼티(`:106`, `:108`, `:111-112`, ASSUMPTION-22). **MA2형 `/trig=` 금지**(`:115-117`). 저장 플래그(`:57-59`). `ClearAll` 규율(`:40-41`), 목적지 선두 1회(`:11-15`). 룩 계층의 공백을 큐로 지목한 인계 문장(`:225-227`). **PRESERVE** |
| `server/rulebook/assets/v2.4.2/00_grammar.md` | **큰따옴표 금지**(`:26-29`) — `corpus.yaml:69`가 깨진 형태임의 근거이며 기각 (c)의 2항. `Label Sequence 3 'Chorus'`(`:27`, T1). `Store Cue 5`(`:42`) · `Delete Sequence 9`(`:45`) · `Goto Cue 5 Sequence 2`(`:48`) · `Store Cue 5 Fade 3`(`:56`) · `Store Cue 3 Fade 2.5`(`:69`) — 전부 라이브 표시 없는 T3. 프리셋 동사 4종이 전부 프로그래머 쪽(`:59`, `:67`, `:68`, `:72`) — 기각 (a)의 2항. **PRESERVE** |
| `server/audit_logs/*.jsonl` | **T1의 유일한 출처.** 라이브 실행된 `Cue` 커맨드 전수 5건 — `audit-20260719.jsonl:148`, `:186` · `audit-20260722.jsonl:1057` · `audit-20260726.jsonl:327`, `:538`. 시퀀스 라벨 `audit-20260726.jsonl:328`. 익스큐터 바인딩 `audit-20260719.jsonl:149`, `:187`. **`detail` 필드가 `"OK"`인지 `"offline mock execution: …"`인지가 T1과 T4를 가른다**(§2 함의 4) |
| `server/measurement/corpus.yaml` | **T4의 진원.** 자기 선언 `:7-10`("for M6a mock runs **ONLY**", "structurally valid" 뿐). `Store Cue 12`(`:68`) · `Label Cue 12 "Opening"`(`:69`, **큰따옴표 = 깨진 형태**) · `Store Cue 5 Fade 3`(`:76`). 대응 mock 감사 기록 `.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73` |
| `server/safety/grammar.py` | `_VERB_SHAPE`(`:20`) — **ASCII 전용 선두 토큰 규칙**, 체인 ④. 과보류 수용 설계(`:3-10` — "Over-blocking is acceptable"). MA2형 부착 대입 탐지와 재작성 힌트(`:27-31`). **PRESERVE** |
| `server/safety/console.py` | 시퀀스 본문 조회 경로 `DEFAULT_BODY_PATHS["Sequence"]`(`:399`, 라이브 기록 있음). **자식 `name`이 본문 라인이 되는 지점**(`:478-484`, 체인 ②) — **파일 총 484행**(§9.3). 본문 경로가 onPC 미검증 placeholder임을 스스로 적은 주석(`:391-395`). **PRESERVE** |
| `server/safety/expand.py` | **라인마다 문법 검증 + 실패 시 보류**(`:106-112`, 체인 ③). 참조가 `None`이면 보류(`:82-83`) — `Goto Cue …`가 보류되는 지점. **PRESERVE** |
| `server/safety/classify.py` | `RECOGNIZED_REFERENCE_TYPES`(`:44`) — **`Cue` 없음**. 이 닫힌 집합의 개정이 `blacklist.yaml` 개정과 같은 무게임을 적은 주석(`:34-43`). **PRESERVE** |
| `server/safety/blacklist.yaml` | `"Delete"`(`:15`) — `Delete Cue`가 T5인 동시에 블랙리스트인 이중 차단. `"Store /overwrite"`(`:18`) — `REQ-SONGCUE-010`의 경계 조건. **PRESERVE** |
| `console/lua/copilot_responder.lua` | **`Cue` 문자열 0건**(875줄 전수) — 응답기가 큐를 특별 취급하지 않는다는 §4 근거. `EXECUTOR_ADDRESS_PATTERN`(`:405`)과 "the ONLY address form" 주석(`:397-404`). **PRESERVE** |
| `server/looks/busking.py` | 재사용 계약 4종의 진원 — `looks_for_genre`(`:81`) · 슬롯 원장 `_advance`(`:158`, 형상 근거 `:161-163`, 미관측 방어 `:176-180`) · 번들 결합 `_merge`(`:189`, 룩별 구간 반환 `:202-206`) · 값 라인 충돌(`:230`, `:240`, 건너뛰기 근거 `:245-251`). **재사용하되 확장 가능** |
| `server/looks/report.py` | 2단 보고 — `_REASON_LABELS`(`:63`, 8종 닫힌 집합) · `_VERDICT_LABELS`(`:74`, 3값) · `build_report`(`:205`, 룩별 판정은 실행 결과에서 `:208-212`) · `to_korean`(`:278`, 집계 형식 `:281-285`) · 모르는 코드는 지어내지 않음(`:77-83`). 한국어를 표현 계층에 두는 이유(`:60-62`). **재사용하되 확장 가능** |
| `server/looks/matching.py` | `DYNAMICS_TERMS` **정의는 `:92`**(내용 `:93-131`) — 인트로 `:99-101` · 벌스 `:103-104` · 빌드 계열 `:106-113` · 코러스/드랍 계열 `:117-128`. 밴드를 넓게 잡은 이유는 모듈 독스트링 `:21-26`, EDM 드랍 실측 근거는 `:114-116`. 어휘를 지어내지 않는 `@MX:WARN`(`:28-33`) — 기각 (g)의 3항. **PRESERVE** |
| `server/looks/schema.py` | `DYNAMICS_MIN`/`DYNAMICS_MAX`(`:35-36`). **P1-1/P1-2 공통 기반 경고**(`:20-25`) 와 per-show 값 진입을 스키마가 이미 막고 있다는 진술(`:23-25`). **PRESERVE** |
| `server/looks/instantiate.py` | `_first_free_slot`(`:307-312`) — 전진 없는 순수 함수, 하드 결함 1의 형상 진원. `_plan_stores`(`:325-384`) — 모든 "저장 불가"를 `SkippedStore`로 답하는 선례(값 없는 패밀리는 `:332-334`에서 건너뜀이 아니라 `continue`). **PRESERVE** |
| `server/orchestrator/tools.py` | 단일 실행 경로 — `run_commands`(`:483`) → `bundle_gate.screen()`(`:492`). **dedupe/실행 블록**(`:523-569`: 결과 목록·실패 플래그 초기화 `:523-524` · 시드 `:533` · 루프 `:534-569` · stop-on-first-failure 분기 `:535-543` · dedupe 판정 `:544` + 건너뛰기 분기 `:544-557` · `skipped_already_executed` 문자열 `:554` · 플래그 세팅 `:569`) — **무변경 대상**. **면제 집합 `_PROGRAMMER_STATE_COMMANDS`(`:234-238`)** 3종과 `fullmatch` 판정(`:241-244`), 확장 금지 사유(`:227-232`) — **무변경 대상**. 앵커 선례 2개(`:693-701`, `:817-824`). **변경은 신규 툴 등록으로 한정** |
| `server/orchestrator/last_created.py` | `_STORE_SEQUENCE`(`:30`)가 시퀀스 생성을 패널 핀에 자동 연동. **스냅샷 전용 · 최신 1건**(`:17-18`) — "곡 1개 = 시퀀스 1개"일 때만 정상 동작(기각 (b)의 2항). `Store Cue <m> Sequence <n>`을 생성으로 읽지 않음(`:27-29`) |
| `server/tests/test_last_created.py` | `parse_last_created(["Store Cue 1 Sequence 71"]) is None` 고정(`:58-61`) — 위 성질의 회귀 방어 |
| `server/tests/test_safety_classify.py` | `Store Cue 5` = `safe` · `risky is False` 고정(`:63-66`, 재확인 `:150`) — **저작 번들이 승인 보류를 유발하지 않는다**의 근거. `("Goto Cue 3", None)`(`:114`) — 섹션 점프가 보류되는 근거 |
| `pyproject.toml` · `uv.lock` | 런타임 의존성 9종(`pyproject.toml:7-19`), lock 명명 패키지 **58종** — 오디오 라이브러리 **0건**(numpy 포함). 기각 (e)의 1항 |
| `server/web/app.py` · `src-tauri/capabilities/default.json` | 텍스트 전용 입력(`app.py:311` `receive_text()`), 라우트 데코레이터 2개(`:200`, `:205`). Tauri가 `no upload`를 명시 거부(`default.json:4`), 테스트 강제(`server/tests/test_deploy_tauri_shell.py:344-353`). 기각 (e)의 2·3항 |
| `SPEC-COPILOT-EXECREF-001/design.md` | **Q3 부정 실측**(`:167`) — 시퀀스 재조회는 `name`/`class`/`i`(+`Part`)만 준다. 라이브 프로브 성격 선언(`:157`), 응답기 범용성 근본 원인(`:166`), 응답기 확장을 YAGNI로 거절한 선례(`:171`). §4 전체의 근거 |
| `SPEC-COPILOT-BUSKWIZ-001/research.md` | 재사용 계약 원문(`:377-381`) — 본 SPEC의 발주서. 라이브 선언 룰북 1개 전수(`:141`), 프리셋-익스큐터 문법 0건 전수(`:143`) — 기각 (a)의 1항. 타임코드 인계 명시(`:385`) |
| `SPEC-COPILOT-BUSKWIZ-001/spec.md` · 같은 SPEC의 `progress.md` | Out of Scope 절 제목과 본문(`SPEC-COPILOT-BUSKWIZ-001/spec.md:144`, `:146`) — 본 SPEC의 발주 조항. M0 실측 상한(`SPEC-COPILOT-BUSKWIZ-001/progress.md:200`, `:280` — 87/87 · 5.77s · 66.3 ms/줄), 익스큐터 축 DESCOPE 판정(같은 파일 `:197-202`) |
| `SPEC-COPILOT-SHOWUI-001/progress.md` | **ASCII 큐 이름 종단 통과 라이브 관측**(`:460` — 큐 `'Blue Look'`의 시퀀스 90에 `Go+`/`Off` 둘 다 `ok=True`), 추가 관측(`:459`, `:463`) |
| `SPEC-COPILOT-EXECBODY-001/progress.md` | 시퀀스 본문 조회 경로의 라이브 왕복 기록(`:180` — `DataPool/Sequences/71` `state_query` `ok: true`) |
| `SPEC-COPILOT-MVP-001/progress.md` | `Goto Cue 3` 과보류를 프로젝트가 인정하고 기록한 지점(`:215`) — §5 후단 |
| `SPEC-COPILOT-LOOKLIB-001/research.md` | 미해결 마커 교훈의 원문(`:220`) — §9의 규율 근거 |
| `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` | P1-1 원문(`:68-74`), 산출물 3조각 정의(`:71`), 입력 정의(`:70`). 타임코드 유일 등장이 외부 링크임(`:125`, `:127`) |
| `.moai/project/product.md` · `DESIGN.md` | Phase 3 행과 성공 기준(`product.md:39` / `DESIGN.md:157-160`), 비목표 2건(`product.md:44-45`) |

---

## §9. 알려진 미결 지점 — 최종 상태 **미결 0건**

**최종 상태: 미결 0건.** 본 문서에 미해결 clarification 마커는 **하나도 없다**(전수 스캔 0건). 폐쇄 경로는 넷이고 내역의 합이 맞는다 — **사용자 사전 확정 3건**(결정 A · B · C — §9.1) · **본 문서가 열고 닫은 항목 2건**(§9.2) · **요구 정합 결함 2건**(§9.4 — 정본 문언이 확정하며 **새 결정 문자를 만들지 않는다**) · **ASSUMPTION-20~24로 승격한 5건**(§9.5). 합 **12건**이고, 여기에 §9.3의 **코드 앵커 드리프트 5건**이 따로 붙는다(그것은 미결이 아니라 처리 이력이다). 승격은 미결의 존속이 아니라 **폐쇄의 한 형태**다 — 판정이 어느 쪽이든 정의된 결과(GO 또는 DESCOPE, ASSUMPTION-21만 블로킹)로 이어지도록 `REQ-SONGCUE-013`/`REQ-SONGCUE-014`와 `AC-SONGCUE-012`/`AC-SONGCUE-017`이 양 분기를 미리 규정해 두었다.

**적용한 규율은 LOOKLIB의 교훈이다** — `SPEC-COPILOT-LOOKLIB-001/research.md:220`: "**미해결 마커로 표시되지 않은 미결이 마커로 표시된 미결보다 위험하다.** 마커는 게이트에서 세어지지만, 플레이스홀더는 세어지지 않은 채 하류로 번진다." 따라서 아래 절들은 **마커를 남기는 대신** 각 항목을 (i) 결정으로 닫거나 (ii) ASSUMPTION 번호로 승격하거나 (iii) §D 범위 밖으로 보낸다. 셋 중 어느 것도 아닌 항목은 남아 있지 않다.

### §9.1 해소된 것 — 사용자 사전 확정 3건 (결정 A~C)

| 항목 | 폐쇄 경로 | 최종 결정 | 본 문서의 조사 기여 |
|---|---|---|---|
| **A. 음원 자동 분석을 포함하는가** | 사용자 확정 ① | **범위 밖 — 별도 SPEC.** 섹션 목록은 사용자가 제공 | §7 기각 (e)가 세 축을 전부 실측으로 재확인 — 오디오 의존성 0건(`pyproject.toml:7-19`, `uv.lock` 58패키지 전수 무매치, numpy조차 없음), 업로드 경로 0건(`server/` 전체 `UploadFile`/`File(`/`multipart` 0건, 라우트 8개 전량 무관, `app.py:311` 텍스트 전용, `ui/src/` `type="file"` 0건), Tauri 명시 거부(`src-tauri/capabilities/default.json:4` + 테스트 강제). 제안서 `:70`이 요구한 입력 축과 `:71`이 요구한 산출 축을 분리한 것이 분할선임을 §1이 명시 |
| **B. 타임코드를 만드는가** | 사용자 확정 ② | **M0 라이브 프로브 GO/DESCOPE 게이트**(ASSUMPTION-20). 부정이면 타임코드 대상 커맨드 **0건** + DESCOPE 사유 기록 | §3이 5경로 전수로 0건을 확정하고(룰북 5파일·`server/`·`console/`·`.moai/project/`·`.moai/state/`·`ui/src/`), 유일 등장이 외부 링크 텍스트임을 특정(`docs/proposals/…:125`, `:127`). **로드맵·제안서·DESIGN.md 3곳이 이것을 요구한다는 모순을 표로 명시** — 기록하지 않으면 run-phase가 "로드맵에 있으니 만든다"로 진입한다. 선행 SPEC의 인계도 재확인(`SPEC-COPILOT-BUSKWIZ-001/research.md:385`) |
| **C. 큐 이름을 어떤 문자로 쓰는가** | 사용자 확정 ③ | **ASCII 고정 + 한국어는 표현 계층.** 자산·스키마에 한국어 필드 추가 0건 | §5가 4단계 체인을 종단으로 추적해 이것이 취향이 아니라 **게이트 보류 조건**임을 확정(`server/safety/console.py:478-484` → `expand.py:106-109` → `grammar.py:20`). ASCII 쪽 라이브 관측 특정(`SPEC-COPILOT-SHOWUI-001/progress.md:460`)과 한국어 쪽 미관측 확정(유일 한글 큐 기록이 offline mock). §7 기각 (f)가 반대 논거를 4사유로 처리 |

### §9.2 미결이 아니었으나 결정도 아니었던 항목 — 본 문서가 열고 닫는다

LOOKLIB의 교훈(`SPEC-COPILOT-LOOKLIB-001/research.md:220`)을 적용해, **마커도 결정도 아닌 채 하류로 번질 뻔한 항목 2건**을 열고 여기서 닫는다.

1. **"섹션 마커"의 실체가 어디에도 정의되지 않은 채 세 문서에 적혀 있었다 → 본 문서가 특정하고 닫는다.**
   제안서 `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:71`이 산출물 3조각 중 하나로 "섹션 마커"를 들었고 `SPEC-COPILOT-BUSKWIZ-001/spec.md:146`이 그것을 그대로 인계했지만, **MA3 오브젝트로서의 Marker/Mark은 리포지토리 전체에서 0건이다**(§3 정적 실측 4 — 매치는 전부 `UNCONFIRMED_MARKER`(`server/web/session.py:56`) 계열의 Python/TS 내부 상수와 테스트 전용 식별자). **폐쇄**: 섹션 마커의 유일한 물리적 실체는 **큐 이름 문자열**이고, 그것은 이미 T1이며(`Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4` — `server/audit_logs/audit-20260719.jsonl:186`), `REQ-SONGCUE-008`이 그 실체를 규정한다. **따라서 산출물 3조각 중 (iii)은 DESCOPE 대상이 아니라 이미 해결된 항목이다.** 이 연결을 기록하지 않았다면 후속 SPEC이 "섹션 마커 기능 미구현"으로 오해하고 존재하지 않는 오브젝트를 찾아 M0 예산을 썼을 것이다.
2. **`Cue 2` 이상의 라이브 근거가 "룰북에 있음"으로 뭉뚱그려져 있었다 → 본 문서가 계수하고 ASSUMPTION-21로 승격한다.**
   `31_choreography_patterns.md:54-55`는 라이브 선언 파일 안에 있어 "검증됨"으로 읽히기 쉽다. 그러나 감사 로그 전수 census 결과 라이브 실행된 `Cue` 커맨드는 **5건이고 전부 `Cue 1`**이며(§2 정적 실측 1), 5건 모두 **서로 다른 신규 시퀀스에 대한 첫 저장**이다. **폐쇄**: ASSUMPTION-21로 승격하고 **블로킹**으로 등급을 매겼다 — DESCOPE가 아니라 M3 저작 자체를 막는다. `acceptance.md §C.0`이 이를 M0의 1번 측정 항목으로 올렸고, §7 기각 (b)가 "섹션마다 시퀀스 1개"라는 우회를 4사유로 닫았다.

### §9.3 코드 앵커 드리프트 5건 — 본 문서가 실측 재접지, 정본이 수령

정본(spec.md · acceptance.md)이 인용한 코드 앵커 중 **5건이 현재 트리와 어긋난다.** BUSKWIZ가 같은 부류를 5건 보고했던 것(`SPEC-COPILOT-BUSKWIZ-001/research.md:337`)과 같은 성격이며, **원인 유형별로 남긴다** — 같은 드리프트가 다시 생길 때 진단 순서가 된다.

| 정본의 인용 | 현재 트리의 실제 위치 | 원인 |
|---|---|---|
| `server/safety/console.py:484-490` (자식 `name` → 본문 라인) | **`:478-484`**. **파일 총 484행이라 `:490`은 존재하지 않는다** | 범위 전체가 파일 끝을 넘어감 — 가장 심각한 부류 |
| `server/orchestrator/tools.py:227-231` (`_PROGRAMMER_STATE_COMMANDS`) | **`:234-238`** (`:227-232`는 면제 원칙을 적은 사유 주석, `:233`은 `_SELECTION_OPERAND`) | +7행 오프셋 |
| `server/orchestrator/tools.py:526-550` (dedupe 블록) | **`:523-569`** — 초기화 `:523-524` · 시드 `:533` · 루프 `:534-569` · stop-on-first-failure 분기 `:535-543` · dedupe 판정 `:544` + 건너뛰기 분기 `:544-557` · 플래그 세팅 `:569` | 같은 +7행 오프셋. 인용 범위가 블록의 시작과 끝 어느 쪽과도 맞지 않는다 |
| `server/safety/classify.py:46` (`RECOGNIZED_REFERENCE_TYPES`) | **`:44`** (`:46`은 `_NUMERIC_REF`) | 2행 오프셋 |
| `server/looks/matching.py:21-25` (`DYNAMICS_TERMS`) | **정의는 `:92`**(내용 `:93-131`). `:21-26`은 **모듈 독스트링**의 설명 절 | 상수 정의처와 독스트링의 혼동 — BUSKWIZ가 `resolver.py:70`에서 겪은 것과 **정확히 같은 부류** |

**처리 상태**: 본 문서와 형제 문서가 위 실측값을 쓰고, 정본은 run-phase 킥오프 전에 정정한다. **본 문서에서는 열린 항목이 아니라 처리 이력이다** — 미결로 오독하면 run-phase가 같은 대조를 반복한다.

**부수 관측 1건**:
- `server/orchestrator/tools.py:823`의 주석이 리그 직접 읽기 사유로 `(:735-738)`을 자기 참조하는데, 이는 **소스 파일 안의 줄 참조**라 파일이 변하면 함께 낡는다. 본 SPEC은 그 파일을 신규 툴 등록 외로 고치지 않으므로 사실만 기록한다.

### §9.4 요구 정합 결함 2건 — plan-phase에서 발견·폐쇄

**§9.1~§9.3과 종류가 다르다.** 앞의 것들은 "정해지지 않은 결정"이거나 "기록되지 않은 사실"이었지만, 여기 둘은 **요구 문장이 완결돼 있는데 실행 방법이 정해지지 않았거나 하나뿐인** 부류다 — 마커로도 결정 공백으로도 잡히지 않는다. 둘 다 `REQ-SONGCUE-nnn`·`AC-SONGCUE-nnn` 개수를 바꾸지 않고 **정본 문언으로** 닫혔다. **결정 등록부(plan.md §A.4a)에 항목을 더하지 않으며, 본 문서가 새 결정 문자를 만들지도 않는다** — 등록부의 문자 배정은 plan.md §A.4a/§F.1이 정본이고 본 문서는 그것을 소비만 한다.

#### 결함 ① — 착수 시점의 `REQ-SONGCUE-008`이 큐 이름의 **발화 형태**를 정하지 않았다

- **결함의 형태**: `REQ-SONGCUE-008`은 "큐 이름을 **ASCII 문자열**로 발화하고"라고만 적는다. **어떤 커맨드로** 붙이는지가 열려 있다. 자연스러운 다음 수는 `Label Sequence`(T1, `00_grammar.md:27` + `audit-20260726.jsonl:328`)의 대응물인 `Label Cue <n> '<name>'`인데, **그것은 룰북 0건이고 유일한 리포지토리 등장처가 큰따옴표를 쓴 mock이라 발화하면 깨진다**(`server/measurement/corpus.yaml:69` vs 금지 조항 `00_grammar.md:26-29`).
- **왜 위험했는가**: 요구 문장은 완결돼 있고 근거(`server/safety/grammar.py:20`)도 정확하다. 그래서 아무도 "그 이름을 **어떻게** 붙이나"를 다시 묻지 않는다. M3가 `Label Cue`를 고르면 T5 동사를 발화하게 되고, 그 실패는 mock 테스트에서는 드러나지 않는다 — mock이 정확히 그 형태를 갖고 있기 때문이다(§2 함의 4의 오염 경로).
- **폐쇄 — `REQ-SONGCUE-008`이 확정한다**: **큐 이름은 `Store Sequence <n> Cue <m> '<name>'`의 인라인 3번째 토큰으로만 발화한다.** 요구 문언 자체가 그 한정을 담게 되었으므로 별도 결정 항목이 아니다. 사유 넷 — (i) 그 형태만 T1이다(라이브 5/5, §2 정적 실측 1), (ii) 별도 동사는 번들을 섹션당 1줄 늘리고 그 줄이 T5다, (iii) 저장/명명 분리는 §D가 닫은 큐 편집의 입구다, (iv) `Label Cue`의 유일 선례가 문법 위반 형태라 그것을 고쳐 쓰는 순간 "mock을 근거로 문법을 발명"하게 된다. 근거 전문은 §7 기각 (c).
- **교훈**: BUSKWIZ 결함 ①의 교훈("**근거가 달린 문장이 근거 없는 문장보다 위험할 수 있다**")의 변주다. 여기서는 근거가 정확했지만 **그 근거가 답하는 질문이 요구의 질문과 달랐다** — `grammar.py:20`은 "어떤 문자를 쓸 수 있나"에 답하고, 요구가 실제로 필요로 한 것은 "어떤 동사를 쓸 수 있나"였다.

#### 결함 ② — 섹션 점프 UX가 어느 문서에서도 배제되지도 예약되지도 않았다

- **결함의 형태**: 곡 섹션마다 큐를 만들면 "리허설에서 후렴만 다시"라는 요구가 즉시 따라오고, 그 커맨드는 `Goto Cue <m> Sequence <n>`이다(룰북 `00_grammar.md:48`). `spec.md §D`는 **큐 편집·재생성**을 닫았지만 **재생·점프**는 명시적으로 다루지 않았고, `REQ-SONGCUE-nnn` 어느 것도 재생을 요구하지 않는다 — 즉 배제도 예약도 아닌 상태였다.
- **왜 위험했는가**: 그 커맨드는 문법 문제가 아니라 **게이트 문제**다. `server/safety/classify.py:44`에 `Cue`가 없어 참조가 추출되지 않고(`server/tests/test_safety_classify.py:114`가 `("Goto Cue 3", None)`로 고정), `None`은 `server/safety/expand.py:82-83`에서 `_hold("unverifiable reference: no recognizable target object")`가 된다. **섹션 점프를 누를 때마다 승인 카드가 뜬다.** 열려면 `RECOGNIZED_REFERENCE_TYPES`라는 닫힌 집합을 고쳐야 하는데, `classify.py:34-35`가 그 개정을 "`blacklist.yaml` 개정과 같은 무게"로 규정한다 — 안전 계층 개정이지 UX 개선이 아니다.
- **폐쇄 — `spec.md §D`의 `Out of Scope — 재생 · 섹션 점프` 절이 확정한다**: **본 SPEC은 재생·점프를 만들지 않는다.** 정본이 그 절을 담게 되었으므로 별도 결정 항목이 아니다. 산출물은 큐리스트 초안이고, 그것을 어떻게 발사하는지는 이미 존재하는 경로(`Go+ Sequence <n>` — T1, `SPEC-COPILOT-SHOWUI-001/progress.md:463`)로 충분하다. 프로젝트가 과보류를 이미 인정하고 기록해 두었으므로(`SPEC-COPILOT-MVP-001/progress.md:215` — "`Go Cue` 상용 패턴도 보류됨(과보류 인정, M5/M6에서 fetcher map 튜닝; 안전 기본값 유지)") 이는 새 발견이 아니라 **알려진 상태의 계승**이다. §10이 이 축을 후속 SPEC으로 명시 이관한다 — **예약이 아니라 이관이다**(본 SPEC은 그 축을 위해 아무것도 남기지 않는다).
- **교훈**: 결함 ①이 "요구가 **어떻게**를 정하지 않았다"였다면 이것은 "**아무 문서도 그 질문을 하지 않았다**"이다. 산출물이 새 사용 시나리오를 만들 때, 그 시나리오가 기존 안전 계층에서 어떻게 취급되는지를 **범위 결정 시점에** 묻지 않으면 그 답은 v1 출하 다음 날 사용자가 알려 준다.

### §9.5 M0가 실측할 대상 — ASSUMPTION-20~24 (미결이 아니라 측정 항목)

| 전제 | 현재 등급 | 부정 시 귀결 | 본 문서의 근거 기여 |
|---|---|---|---|
| **ASSUMPTION-20** 타임코드 문법·오브젝트 존부 | **T5** | `REQ-SONGCUE-013` DESCOPE — 타임코드 대상 커맨드 0건 + 사유 기록 | §3 (5경로 전수 0건, 유일 등장이 외부 링크, 로드맵 3곳의 요구와의 모순) |
| **ASSUMPTION-21** 같은 시퀀스에 `Cue 2` 이상 (`/Merge`) | **T2 — 라이브 0건** | **블로킹 — M3 저작 착수 불가.** `REQ-SONGCUE-007`의 산출물 정의 자체가 성립하지 않음 | §2 정적 실측 1(라이브 `Cue` 커맨드 5건 전수, **전부 `Cue 1`**, 전부 신규 시퀀스 첫 저장), §9.2 항목 2, §7 기각 (b) |
| **ASSUMPTION-22** `Set Cue <m> Sequence <n> Property 'TrigType'`/`'TrigTime'` | **T2 — 라이브 0건** | `REQ-SONGCUE-014` DESCOPE — 자동 진행 0건, 큐 시간은 `CueFade`로만 | §2 항목 7(룰북 `:106`, `:108`, `:111-112`는 라이브 선언 아래지만 실행 기록 0건). §4 함의 3 — **파싱 성공과 효과 발생을 반드시 구분해 기록해야 하는 항목**이며, 프로퍼티는 재조회로도 읽히지 않아 M7에서도 드러나지 않는다 |
| **ASSUMPTION-23** 빈 시퀀스 번호 식별 가능성 | 미측정 | `AC-SONGCUE-008` 구간 ② — 추측하지 않고 거부 | §6 함의 3 — **큐 번호는 섹션 입력 순서에서 오므로 결정론적이고, 미관측 문제가 남는 곳은 시퀀스 번호뿐이다.** BUSKWIZ가 익스큐터에서 데인 "비어 있음 vs 존재하지 않음 미구분" 함정의 시퀀스 축 재발 여부 |
| **ASSUMPTION-24** 곡 1개 번들의 왕복 규모 | 계산 대상 | 상한 초과 시 M0에서 재측정 | §6 계약 9(BUSKWIZ M0 실측 87줄/5.77s/66.3 ms/줄 — `SPEC-COPILOT-BUSKWIZ-001/progress.md:200`, `:280`). **계산이 87줄 이내면 재측정 불필요** — 측정 예산을 ASSUMPTION-21/22로 돌린다 |

---

## §10. 후속 SPEC과의 관계 — 무엇을 예약하고 무엇을 예약하지 않는가

본 SPEC은 세 방향의 후속을 만든다. **셋을 구분해 적는 이유는 "예약"과 "이관"이 다르기 때문이다** — 예약은 본 SPEC이 그 소비자를 위해 형상을 남기는 것이고, 이관은 남기지 않고 넘기는 것이다. 구분하지 않으면 후속 SPEC이 있지도 않은 접합면을 찾는다.

### (1) 음원 자동 분석 — **예약한다** (입력 계약 1종)

- **예약하는 것**: **섹션 목록의 형상 하나.** `REQ-SONGCUE-001`이 정의하는 구조(이름 · 시작 시각 · 입력 순서, 시각은 밀리초 정수로 정규화 — `AC-SONGCUE-001` 구간 ②)가 곧 음원 분석기의 **출력 계약**이 된다. 분석기가 붙어도 본 SPEC의 파이프라인은 무변경이며, 바뀌는 것은 그 목록을 **누가 만드느냐**뿐이다.
- **예약하지 않는 것**: 오디오 의존성 · 업로드 경로 · 진행률·취소 프로토콜 · BPM·에너지 곡선의 표현. 본 SPEC은 이 축에 **아무 표면도 만들지 않는다** — 현재 리포지토리에 셋 다 0건이고(§7 기각 (e)), 하나라도 미리 만들면 쓰이지 않는 채로 출하되어 `server/orchestrator/tools.py:77-79`가 기록한 "추측된 경로는 죽은 채 출하된다" 사고를 반복한다.
- **경계선**: 분석기는 **섹션 목록까지만** 만들고 MA3에 아무것도 쓰지 않는다. 본 SPEC이 MA3 쪽 전부를 소유한다. 이 분할선이 유지되면 두 SPEC은 서로의 라이브 세션을 필요로 하지 않는다.

### (2) 시퀀스 → 익스큐터 바인딩 · 페이지 저작 — **예약하지 않는다** (이관)

- **왜 예약하지 않는가**: BUSKWIZ M0가 ASSUMPTION-16/17/19를 **전부 DESCOPE**로 판정했고(`SPEC-COPILOT-BUSKWIZ-001/progress.md:197-202`) 그 판정은 유효하다. 본 SPEC이 그 축을 위해 형상을 남기면 **DESCOPE된 축에 대한 미사용 접합면**이 생긴다 — 예약의 최악 형태다.
- **다만 본 SPEC이 그 후속을 **쉽게** 만든다**: 바인딩의 유일한 T1 커맨드 `Assign Sequence <n> At Executor <m>`(`31_choreography_patterns.md:99` + `server/audit_logs/audit-20260719.jsonl:149`, `:187`)의 목적어는 **시퀀스**다. BUSKWIZ가 §9.4 결함 ①에서 겪은 문제 — "게이트가 열려도 얹을 대상이 없다"(산출물이 프리셋이었다) — 가 본 SPEC에서는 **구조적으로 발생하지 않는다.** 본 SPEC의 산출물이 정확히 시퀀스이기 때문이다. 후속 SPEC은 존재하는 시퀀스를 바인딩하면 되며, **그 시퀀스를 어떻게 만드는가는 이미 풀려 있다.**
- **예약하지 않는 구체 항목**: 빈 익스큐터 탐색 · 페이지 저작(`Store Page`/`Label Page`/`Copy Page` — 룰북 0건, T4만) · `page*100+slot` 역주소 일반화(`REQ-EXECBODY-007`/`REQ-EXECBODY-008`이 2페이지 검증 전 하드코딩을 금지하고 그 조건은 아직 미충족).

### (3) 큐 편집 · 재생성 · 섹션 점프 — **예약하지 않는다** (이관, §9.4 결함 ②)

- **왜 예약하지 않는가**: 셋 다 본 SPEC의 정의와 충돌하거나 안전 계층 개정을 요구한다.
  - **큐 편집·삭제**: `Delete`는 T5인 동시에 블랙리스트(`server/safety/blacklist.yaml:15`)이고, `/Overwrite`는 승인 카드를 띄운다(`:18`). 초안 생성기가 삭제 승인을 요구하는 순간 "초안"이 아니다.
  - **소수 큐 번호 삽입(`Cue 1.5`)**: T2이고(`31_choreography_patterns.md:56`) 라이브 0건이며, `AC-SONGCUE-006` 구간 ②가 요구하는 "큐 번호가 `1..N` 빠짐없이 한 번씩"과 정면 충돌한다.
  - **섹션 점프(`Goto Cue <m> Sequence <n>`)**: 문법 문제가 아니라 **게이트 참조 인식 확장 과제**다 — `server/safety/classify.py:44`의 닫힌 집합에 `Cue`를 넣어야 하고, `:34-35`가 그 개정을 `blacklist.yaml` 개정과 같은 무게로 규정한다.
- **본 SPEC이 남기는 유일한 것은 사실 기록이다**: §5 후단과 §9.4 결함 ②가 위 세 경로의 정확한 차단 지점을 file:line으로 특정해 두었다. 후속 SPEC은 그것을 다시 조사할 필요가 없다. **접합면은 남기지 않고 진단만 남긴다.**

### (4) 응답기 확장 (큐 프로퍼티 읽기) — **예약하지 않는다** (선례가 이미 거절)

- `console/lua/**`는 PRESERVE이고(`spec.md §C`), 응답기를 확장해야 `CueFade`/`TrigType`을 읽을 수 있다(§4). 그러나 `SPEC-COPILOT-EXECREF-001/design.md:171`이 같은 유혹을 이미 거절했다 — "**행동 변화 없이 안전-critical 코드에 새로운 미검증 주소 가정 하나를 추가하는 것**뿐이다 … 정당한 YAGNI 판단이다."
- 본 SPEC은 `REQ-SONGCUE-017`이 **한계를 명시**하는 것으로 처리하며(`AC-SONGCUE-014` 구간 ②가 "확인했다고 주장하는 필드 0건"을 기계 판정), 확장 자체는 별도 범위 결정이다.

### 본 SPEC이 후속에 물려주는 형상 3종 (BUSKWIZ의 3종에 대응)

BUSKWIZ가 `SPEC-COPILOT-BUSKWIZ-001/research.md:377-381`에서 P1-1에 물려준 3종에 대응해, 본 SPEC은 다음을 물려준다:

1. **시간축 번호 원장** — 큐 번호가 섹션 입력 순서에서 오는 결정론적 전진. 슬롯 원장(`server/looks/busking.py:158`)이 콘솔 관측에 의존하는 것과 달리 **리그 상태와 무관하게 순수 함수로 판정 가능하다**(§6 함의 3). 시간축을 갖는 모든 후속(타임코드 트랙, 큐 재배열)이 같은 형상을 쓴다.
2. **섹션 축 2단 보고** — `server/looks/report.py`의 집계+개체별 형상에 섹션을 얹은 것. "어느 곡 섹션의 룩이 죽었는가"는 큐리스트 고유 질문이 아니라 **시간축을 갖는 모든 산출물의 질문**이며, stop-on-first-failure가 섹션 축에서 더 아프다는 §6 함의 4가 그 필요의 근거다.
3. **T1~T5 증거 등급 규율** — 본 문서 §2의 5등급과 "T1은 재사용하고 T2 이하는 M0가 잰다"는 원칙. 큐 축뿐 아니라 **mock 자산이 오염원으로 끼어들 수 있는 모든 축**에 적용된다. 특히 `detail` 필드로 T1과 T4를 가르는 판별법(§2 함의 4)은 감사 로그를 근거로 쓰는 모든 후속 SPEC이 그대로 쓸 수 있다.

**한 문장 요약**: 본 SPEC은 룩 조율 계층 위에 **"N개 룩을 시간 순서로 배열해 하나의 시퀀스에 담는 법"**을 처음으로 구현하며, 그 산출물이 정확히 시퀀스이므로 익스큐터 축의 후속 SPEC이 BUSKWIZ가 겪은 "얹을 대상이 없다"를 겪지 않는다 — 그러나 섹션 목록을 **어떻게 얻는가**(음원 분석)와 만든 큐를 **어떻게 고치고 점프하는가**(큐 편집 · 게이트 참조 확장)는 각각 별도 SPEC이며, 본 SPEC은 그 축들에 접합면이 아니라 **진단만** 남긴다.
