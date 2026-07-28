# SPEC-COPILOT-SONGCUE-001 — 진행 기록 (progress)

> **인용 규율 (v0.1.0 착수 시점 확정)**: 본 문서가 **정본(spec.md · acceptance.md)** 을 가리킬 때는 줄번호를 쓰지 않고 **안정 토큰**만 쓴다 — `REQ-SONGCUE-nnn` · `AC-SONGCUE-nnn` · `ASSUMPTION-nn` · 절 제목. **형제 아티팩트(plan.md · design.md · research.md)도 줄번호로 가리키지 않는다** — 절 이름이나 결정 이름으로만 참조한다. `파일:줄` 앵커는 **코드 · 룰북 · 감사 로그 · 타 SPEC 아티팩트**에만 남긴다(그것들은 커밋 없이 움직이지 않고 달리 안정 식별자가 없다). 이 규율은 BUSKWIZ가 독립 감사에서 "형제→정본 줄 앵커 52개 중 10개가 빈 줄을 가리킨다"는 지적을 받고 v0.1.3에서 전환한 정책의 계승이다(`SPEC-COPILOT-BUSKWIZ-001/progress.md:110`). 본 SPEC은 그 전환을 **착수 시점부터** 적용한다.

## Plan-phase log

### v0.1.0 최초 작성 (2026-07-28)

- **출처**: 제안서 §3 **P1-1**(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:68-74`)이며 로드맵 Phase 3의 구체화다(`.moai/project/product.md:39`, `DESIGN.md:157-160`). 선행 SPEC 2건이 **명시적으로 남겨 둔 자리**에 선다 — LOOKLIB이 룩 어휘를(`SPEC-COPILOT-LOOKLIB-001/spec.md:176-178`), BUSKWIZ가 다중 룩 조율(슬롯 원장 · 번들 결합 · 2단 보고)을 만들고 "시퀀스·큐는 P1-1의 영역"이라고 인계했다(`SPEC-COPILOT-BUSKWIZ-001/spec.md:140-146`). 본 SPEC이 얹는 것은 **시간축** 하나다.
- **정체**: id `SPEC-COPILOT-SONGCUE-001` · 착수 version `0.1.0` · status `draft` · **Tier L** · priority `P1` · phase `Phase 3 음악분석 → 큐리스트 자동화 (v1.4.0 target)`(spec.md frontmatter).
- **산출물의 성격**: 곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개를 **단일 번들 · 승인 1회**로 생성하는 **초안**이다. 사람이 콘솔에서 고치는 것을 전제하며, 부분 수정·삭제·재배열은 §D가 v1 밖으로 닫았다.
- **착수 시점 형상**: 섹션 6개(§A~§E) · 요구 **21건** · AC **18건** · 사용자 확정 **3건** · ASSUMPTION **5건**(20~24) · 하드 결함 3건 · 라이브 세션 2회 · clarification 마커 **0건**. 이 수는 아래 "AC · REQ 개수 정합" 절에서 실측으로 닫았다.

#### 사용자 사전 확정 3건 (전문 — 재질의 금지, spec.md §A 사전 확정 사실 수록)

세 건 모두 **결정을 요청받은 시점에 근거가 함께 제시된** 것이며, plan-phase가 임의로 재해석하지 않는다.

1. **① 음원 자동 분석은 본 SPEC의 범위가 아니다 — 섹션 목록은 사용자가 준다.** 근거는 세 축이 **동시에 0건**이라는 실측이다. (ⓐ) 오디오 의존성 0건 — `pyproject.toml:8-18`의 런타임 의존은 `anthropic`/`fastapi`/`google-genai`/`keyring`/`lupa`/`python-osc`/`pyyaml`/`uvicorn`/`websockets`이고 `uv.lock`의 **58패키지**(`^name = ` 계수) 전량이 무매치다 — `librosa`·`essentia`·`numpy`·`scipy`·`madmom`·`aubio`·`soundfile`·`torchaudio` 전부 없다. (ⓑ) 업로드 경로 0건 — 웹소켓 수신은 `server/web/app.py:311`의 `receive_text()` 텍스트 전용이고, 라우트 데코레이터는 **정확히 2개**(`@app.get("/healthz")` `:200` · `@app.websocket("/ws")` `:205`)이며, `UploadFile`·`File(`·`multipart`가 **`server/` 전체에서 0건**이고 `ui/src/**`에 `input[type=file]`이 0건이다. (ⓒ) Tauri capability가 업로드를 **명시적으로 거부**한다 — `src-tauri/capabilities/default.json:4`의 description이 "ALL network plugins are denied by omission … no http, no websocket, no upload"라고 적었고 그 문언을 테스트가 강제한다(`server/tests/test_deploy_tauri_shell.py:347-351`). 자동 분석을 함께 열면 신규 의존성 + 업로드 경로 + 진행률 프로토콜(현재 0건) 세 축이 한꺼번에 열린다. **별도 SPEC.**
2. **② 타임코드는 M0 라이브 프로브의 GO/DESCOPE 게이트다.** 근거: 타임코드 문법·객체가 **저장소 전체에서 0건**이다(룰북 5파일 · `server/**` · `console/lua/**` · `.moai/**` 전량 무매치). 유일한 등장은 외부 참고 링크 텍스트뿐이다(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:125`, `:127`). 선행 SPEC이 같은 사실을 이미 기록하고 인계했다(`SPEC-COPILOT-BUSKWIZ-001/spec.md:146`, `SPEC-COPILOT-BUSKWIZ-001/research.md:385`). **DESCOPE는 실패가 아니라 정의된 결과다** — BUSKWIZ M0가 익스큐터 축 3건을 전부 DESCOPE로 닫고도 출하한 선례가 있다(`SPEC-COPILOT-BUSKWIZ-001/progress.md:197-202`).
3. **③ 큐 이름은 ASCII로 고정하고 한국어는 표현 계층에서 매핑한다.** 이것은 취향이 아니라 **안전 게이트의 구조적 귀결**이다. 큐 이름은 재조회 시 **커맨드로 파싱되는 본문 라인**이 된다 — `server/safety/console.py:478-484`의 `_fetch_body_at_path`가 자식의 `name`을 그대로 `lines`에 쌓고, `server/safety/expand.py:106-112`가 라인마다 `validate`를 걸어 실패하면 **보류**하며, `server/safety/grammar.py:20`의 선두 토큰 규칙은 `^[A-Za-z][A-Za-z0-9_+\-]*$` **ASCII 전용**이다. ASCII 큐 이름의 종단 통과는 라이브 관측이 있다 — 큐 `'Blue Look'`을 담은 `Sequence 90`에 대해 `Go+`·`Off` 둘 다 `ok=True`였다(`SPEC-COPILOT-SHOWUI-001/progress.md:460`). **한국어 큐 이름의 종단 효과는 미관측**이며, 미관측을 근거로 열지 않는다. 표현 계층 매핑은 BUSKWIZ가 이미 세운 형상을 그대로 쓴다(`server/looks/report.py:63` `_REASON_LABELS`, `:74` `_VERDICT_LABELS`, `:278` `to_korean`).

#### 조사 결과 요지 ① — MA3 큐 저작 문법의 증거 등급 (T1~T5)

**본 SPEC의 모든 문법 주장은 등급을 달고 다닌다.** 등급 없이 적힌 문법은 감사 결함이다. 등급 정의는 BUSKWIZ가 세운 것을 계승한다.

| 등급 | 정의 | 판별 근거 |
|---|---|---|
| **T1** | 감사 로그에 실제 실행 기록 | `server/audit_logs/*.jsonl`에 `"ok": true`, `"detail": "OK"` |
| **T2** | 룰북 라이브 선언 아래의 문법이나 실행 기록 없음 | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:7` — "Every pattern below was validated live on onPC 2.4.2" |
| **T3** | 룰북 산문만, 라이브 표시 없음 | `00_grammar.md` · `10_object_model.md` · `20_korean_terms.md` · `30_plugin_patterns.md` |
| **T4** | mock 전용 | `server/measurement/corpus.yaml:8-10` 자기 선언, `.moai/state/verify/**`의 `offline mock execution` |
| **T5** | 근거 0건 | 저장소 전량 무매치 |

**라이브 선언을 가진 룰북 파일은 정확히 1개다**(`31_choreography_patterns.md`) — 이 계수는 BUSKWIZ가 실측해 남겼다(`SPEC-COPILOT-BUSKWIZ-001/research.md:141`). 즉 T2는 "룰북에 있으니 된다"가 아니라 **"이 파일에 있으니 그나마 T2"**라는 뜻이며, 나머지 4개 자산의 문법은 T3다.

항목별 실측 등급:

| 항목 | 등급 | 근거 |
|---|---|---|
| `Store Sequence <n> Cue <m> '<name>' CueFade <t>` | **T1** | `31_choreography_patterns.md:50` + `server/audit_logs/audit-20260719.jsonl:186`(`Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4`, `ok:true`) |
| `Store Sequence <n> Cue <m> '<name>'` | **T1 ×4** | `31_choreography_patterns.md:71` + `audit-20260719.jsonl:148`, `audit-20260722.jsonl:1057`, `audit-20260726.jsonl:327`, `:538` |
| `Label Sequence <n> '<name>'` | **T1** | `00_grammar.md:27` + `audit-20260726.jsonl:328`(`Label Sequence 22 'Golden Chorus'`, `ok:true`) |
| `Off Sequence <n>` · `Go+ Sequence <n>` | **T1** | `SPEC-COPILOT-SHOWUI-001/progress.md:459`, `:460`, `:463` |
| `Assign Sequence <n> At Executor <m>` | **T1** | `31_choreography_patterns.md:99` + `audit-20260719.jsonl:149`, `:187` |
| **같은 시퀀스에 `Cue 2` 이상(`/Merge`)** | **T2 — 라이브 0건** | `31_choreography_patterns.md:55`. 감사 로그의 `Cue≥2`는 전량 offline mock(`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73`) |
| **`Set Cue <m> Sequence <n> Property 'TrigType'` · `'TrigTime'`** | **T2 — 라이브 0건** | `31_choreography_patterns.md:111-112`(절 제목 `:106`, `:108`) |
| MA2형 `/trig=` | **금지 확정** | `31_choreography_patterns.md:116-117` — 2.4.2에서 "Illegal object" 반환 |
| 소수 큐 번호(`Cue 1.5`) | **T2** | `31_choreography_patterns.md:56` |
| `Store Cue <n>`(Sequence 미지정) | **T3 + T4** | `00_grammar.md:42`, `:56`, `:69`; mock `corpus.yaml:68`, `:76` |
| **`Label Cue <n> '<name>'` 독립 동사** | **룰북 0건 · T4만** | 유일 등장이 `corpus.yaml:69`이고 큰따옴표라 `00_grammar.md:27-29`를 위반한다 |
| `Delete Cue <n>` | **T5** | 저장소 0건. `Delete`는 블랙리스트(`server/safety/blacklist.yaml:15`) |
| 타임코드 일체 | **T5** | 사용자 확정 ② |
| 별도 Marker/Mark 오브젝트 | **T5** | 룰북 · 코드 · 응답기 전량 0건. `Marker` 매치는 전부 파이썬 내부 상수(`server/web/session.py:56` 등)로 MA3 오브젝트가 아니다 |
| 첫 store 시 시퀀스 자동 생성 | **T2 + T1 정황** | `31_choreography_patterns.md:54`. T1 4건이 전부 **신규 번호**(62 · 90 · 22 · 17)에서 성공했다 |

**전수 계수로 확정한 것 — 라이브 감사 로그의 `Cue` 커맨드는 전 파일 통틀어 정확히 5건이고 전부 `Cue 1`이다.** `server/audit_logs/*.jsonl` 전량에서 커맨드 문자열에 `Cue <숫자>`를 담은 실행 기록을 뽑으면 `Store Sequence 17 Cue 1 'Golden Chorus'` · `Store Sequence 22 Cue 1 'Golden Chorus'` · `Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4` · `Store Sequence 62 Cue 1 'Cyan Look'` · `Store Sequence 90 Cue 1 'Blue Look'` 다섯 줄이 전부다(각 1회). 즉 위 표의 T1 5건은 **큐 축에 존재하는 라이브 증거의 전량**이며, `Cue 2` 이상은 표본이 없어서가 아니라 **한 번도 실행된 적이 없어서** T2다. ASSUMPTION-21의 블로킹 성격은 이 계수 위에 선다.

**이 표가 SPEC의 형태를 결정했다.** 두 개의 결론이 직접 따라 나온다.

- **큐 이름을 붙이는 방법은 store 인라인 3번째 토큰 하나뿐이다.** `Label Cue`가 룰북 0건이므로 이름은 `Store … Cue <m> '<name>'` 안에서만 확정할 수 있고, 따라서 REQ-SONGCUE-008의 ASCII 제약은 **저작 시점에** 걸려야 한다(사후 교정 경로가 없다).
- **본 SPEC의 핵심 형상이 정확히 미검증 구간에 놓인다.** "섹션 1개 = 큐 1개"는 같은 시퀀스에 `Cue 2` 이상을 얹는다는 뜻인데 그것이 T2다. 그래서 ASSUMPTION-21은 DESCOPE 후보가 아니라 **블로킹**이다(아래 참조).

#### 조사 결과 요지 ② — 결정적 부정 실측: 초안을 앱이 스스로 검증할 수 없다

`DataPool/Sequences/<n>/<m>` 재조회는 `name`/`class`/`i`(+ 중첩 `Part` 자식)만 반환하고 **커맨드 · CueFade · TrigType 등 프로퍼티는 어떤 형태로도 반환하지 않는다** — 라이브 실측이며 원 출처는 `.moai/state/verify/showui-m6-resume/5-probe-body.log`다(`SPEC-COPILOT-EXECREF-001/design.md:167`). 조회 경로 자체는 존재하고 라이브 실행 기록이 있다(`server/safety/console.py:399` `DEFAULT_BODY_PATHS["Sequence"] = "DataPool/Sequences/{ref}"`, 실행 기록 `SPEC-COPILOT-EXECBODY-001/progress.md:180`). 응답기는 `Cue`를 특별 취급하지 않는다 — `console/lua/copilot_responder.lua` 전체에 `Cue` 문자열이 **0건**이다. `resolve_path`의 주소형 특례는 `Executor <n>` **하나뿐**이며 주석이 스스로 "the ONLY address form"이라고 못박았다(`server/safety/console.py:397-404`, 패턴 `:405`).

**따라서 REQ-SONGCUE-017은 "검증한다"가 아니라 "존재와 이름까지만 검증하고 나머지는 관측하지 않았다고 적는다"로 쓰였다.** 응답기 확장은 `console/lua/**`가 PRESERVE이므로 §D가 범위 밖으로 닫았다.

#### 조사 결과 요지 ③ — 재사용 계약 9종 (BUSKWIZ가 P1-1에 인계)

인계 문서는 `SPEC-COPILOT-BUSKWIZ-001/research.md:377-381`이며, 본 SPEC은 이 계층을 **재사용하되 고치지 않는다**(REQ-SONGCUE-021이 diff 빈 출력으로 기계 증명한다).

| # | 계약 | 실측 위치 | 본 SPEC에서의 쓰임 |
|---|---|---|---|
| 1 | 슬롯 원장 — frozen을 바깥에서 감싼다 | `server/looks/busking.py:158` `_advance`, `server/looks/instantiate.py:307` `_first_free_slot` | 큐 번호 전진이 **같은 형상의 시간축 판본** |
| 2 | 번들 결합 — 목적지 선두 1회 + `ClearAll` 전량 유지 | `server/looks/busking.py:189` `_merge` | REQ-SONGCUE-011 |
| 3 | 값 라인 충돌 가드 — 거부가 아니라 건너뛰기 | `server/looks/busking.py:230` `VALUE_LINE_COLLISION`, `:240` `_guard_collision` | REQ-SONGCUE-012 |
| 4 | 2단 보고 + 한국어 표현 계층 | `server/looks/report.py:63`, `:74`, `:205`, `:278` | REQ-SONGCUE-016이 여기에 **섹션 축**을 얹는다 |
| 5 | 섹션 어휘 (재정의 금지) | `server/looks/matching.py:92` `DYNAMICS_TERMS`(독스트링 `:21-25`), 한영 매핑 `:99` 이하 | REQ-SONGCUE-003. **값이 점값이 아니라 밴드 튜플**이다 — `"코러스": (4, 5)`(`:117`) · `"드랍": (4, 5)`(`:121`) · `"프리코러스": (3,)`(`:110`). 즉 섹션→다이내믹스는 1:N이며 REQ-SONGCUE-005의 룩 선택이 그 폭을 **좁히지 않고** 받아야 한다 |
| 6 | 다이내믹스 축 `1..5` | `server/looks/schema.py:35-36` `DYNAMICS_MIN`/`DYNAMICS_MAX` | REQ-SONGCUE-005 |
| 7 | 룩 후보 전순서 | `server/looks/busking.py:81` `looks_for_genre` | REQ-SONGCUE-005 |
| 8 | 단일 실행 경로 | `server/orchestrator/tools.py:483` `run_commands` → `:492` `bundle_gate.screen()`. 실행 루프는 `:524`(`failed = False`) ~ `:569`(`failed = True`)이며 stop-on-first-failure 분기가 `:535-543`, dedupe 건너뛰기 분기가 `:544-557` | REQ-SONGCUE-018. 신규 툴은 **호출자**이며 `@MX:ANCHOR` 선례가 2개 있다(`:693` instantiate_look · `:817` prepare_busking — 둘 다 주석이 "a CALLER of run_commands, never a second execution surface"라고 스스로 적었다) |
| 9 | 상한 규모 왕복 실측 | 87줄 번들 **87/87 · 총 5.77s · 66.3ms/줄 · 누적 열화 없음**(`SPEC-COPILOT-BUSKWIZ-001/progress.md:281-284`) | ASSUMPTION-24의 계산 기준선 |

#### 조사 결과 요지 ④ — 설계에 직접 영향을 주는 부수 실측 4건

1. **시퀀스 생성이 패널 핀에 자동 연동된다.** `server/orchestrator/last_created.py:30`의 `_STORE_SEQUENCE = re.compile(r"^\s*Store\s+Sequence\s+(\d+)\b", re.IGNORECASE)`가 발화를 가로채 핀을 만든다. 그런데 그 저장소는 **스냅샷 전용 · 최신 1건**이므로(`server/orchestrator/last_created.py:17-18`) "곡 1개 = 시퀀스 1개"일 때만 정상 동작한다 — 본 SPEC의 REQ-SONGCUE-007이 그 조건을 우연이 아니라 **요구**로 만든다. 같은 파일 `:27-29`는 `Store Cue 1 Sequence 71` 형태를 시퀀스 생성으로 읽지 **않는다**고 명시하며 테스트가 그것을 고정한다(`server/tests/test_last_created.py:58-61`).
2. **`Goto Cue <m> Sequence <n>`은 안전 게이트가 참조를 추출하지 못해 보류된다**(`server/tests/test_safety_classify.py:114`). 과보류라는 인정 기록도 있다(`SPEC-COPILOT-MVP-001/progress.md:215`). 즉 섹션 점프 UX는 **문법 문제가 아니라 게이트의 참조 인식 확장 과제**이며 본 SPEC의 범위가 아니다.
3. **게이트의 닫힌 참조 집합에 `Cue`가 없다** — `server/safety/classify.py:44` `RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor")`. `Store …`는 어느 분기에도 걸리지 않아 `safe`다(`server/tests/test_safety_classify.py:63-66`, `:150`). 본 SPEC의 저작 번들이 승인 카드 없이 흐르는 이유가 이것이며, 그래서 **검증 부담이 전부 앱 쪽에 있다**.
4. **곡은 후렴이 반복된다 — 값 라인 충돌 확률이 장르 팔레트보다 구조적으로 높다.** dedupe 면제 집합은 3종뿐이고(`server/orchestrator/tools.py:234-238` — `Clear` · `ClearAll` · 맨 `Fixture|Group` 선택형) `Store …`와 값 라인은 면제가 **아니다**. BUSKWIZ에서는 픽스처를 일부러 겹쳐야 재현됐지만 본 SPEC에서는 `Chorus`가 두 번만 나와도 밟힌다.

#### 앵커 실측 정정 4건 — 본 문서가 브리핑을 그대로 옮기지 않은 지점

plan-phase에서 인용 대상을 전수 확인하는 중 **브리핑·정본의 코드 앵커 4건이 실제 위치와 어긋남**을 실측했다. SSOT 정정은 본 문서의 소유가 아니므로(오케스트레이터가 동일 세션에서 처리 중이다) 여기에는 **측정값만 남긴다.** 규율은 하나다 — **앵커의 정체는 줄번호가 아니라 심볼 식별자이며, 줄번호는 그 심볼을 찾는 좌표일 뿐이다.**

| 대상 | 인용된 앵커 | 실측 위치 | 인용 위치에 실제로 있는 것 |
|---|---|---|---|
| `_PROGRAMMER_STATE_COMMANDS` (dedupe 면제 집합) | `server/orchestrator/tools.py:227-231` | **`:234-238`** | 사유 주석(`Select …` 접두형을 면제하지 않는 이유)이 `:220-232`, `:233`이 `_SELECTION_OPERAND`. 소비 함수 `_is_programmer_state`는 `:241-244` |
| 자식 `name`을 본문 라인으로 수집하는 코드 | `server/safety/console.py:484-490` | **`:478-484`** (`_fetch_body_at_path`) | `:484`가 `return tuple(lines)`이고 **파일 총 길이가 정확히 484행이라 `:490`은 존재하지 않는다**(`wc -l` 484, `sed -n '485p'` 빈 출력, 파일이 개행으로 끝난다) |
| `RECOGNIZED_REFERENCE_TYPES` | `server/safety/classify.py:46` | **`:44`** | `:46`은 `_NUMERIC_REF` 정규식 |
| `DYNAMICS_TERMS` (섹션 어휘 표) | `server/looks/matching.py:21-25` | **`:92`** | `:21-25`는 모듈 독스트링의 **설명 산문**이다 — 표 자체가 아니다 |

네 건 모두 **가리키려던 대상 자체는 실재하며 사실 주장은 유효하다** — 어긋난 것은 좌표뿐이다. 본 문서는 실측 좌표만 쓴다. 착수 시점에 형제 문서 담당자 전원과 오케스트레이터에게 공유했고, 세 담당자가 독립 실측으로 같은 값을 회신해 **교차 확인**되었다. 단 하나 어긋난 회신이 있었다 — `console.py` 총 길이를 485행으로 보고한 건이 있으나 재계수 결과 **484행**이 맞다(위 셀의 증거 3종). 그 차이는 `:490` 부재라는 결론을 바꾸지 않는다.

같은 성격의 경계 어긋남이 dedupe 블록에도 있다 — PRESERVE 목록이 `server/orchestrator/tools.py:526-550`으로 적었으나 실행 루프의 실측 경계는 **`:524`~`:569`**다(주석 `:525-532` · `already_executed` 시드 `:533` · 루프 `:534` · stop-on-first-failure `:535-543` · 건너뛰기 분기 `:544-557` · 실행 분기 `:558-569`). PRESERVE 게이트는 `git diff`로 파일 단위 판정하므로 **판정 결과는 바뀌지 않지만**, 인용 좌표는 실측값을 쓴다.

#### ASSUMPTION 번호 계승 — BUSKWIZ가 소진한 19 다음인 20부터

미검증 전제는 **본 SPEC이 새로 1번부터 매기지 않는다.** LOOKLIB이 15까지 쓰고 BUSKWIZ가 16~19를 소진했으므로(`SPEC-COPILOT-BUSKWIZ-001/progress.md:39` — "착수 시점 3건(16/17/18)에 v0.1.2가 ASSUMPTION-19를 더해 현재 4건") 본 SPEC은 **20부터** 잇는다. 이유는 계보 예의가 아니라 **충돌 방지**다 — 같은 코드 기반 위의 SPEC 셋이 서로 다른 `ASSUMPTION-3`을 갖는 순간, 라이브 프로브 기록과 DESCOPE 판정이 어느 SPEC의 것인지 문서 밖에서 식별 불가능해진다.

착수 시점 5건이며 **전부 M0 라이브 실측 대상**이다(AC-SONGCUE-017이 5건 전부의 판정 확정을 요구한다).

| 전제 | 무엇 | 현재 등급 | 부정일 때 |
|---|---|---|---|
| ASSUMPTION-20 | 타임코드 오브젝트·문법의 존부 | **T5** (저장소 0건) | REQ-SONGCUE-013 DESCOPE |
| **ASSUMPTION-21** | 같은 시퀀스에 `Cue 2` 이상 추가 | **T2** (라이브 0건) | **DESCOPE 불가 — M3 저작 차단** |
| ASSUMPTION-22 | `TrigType`/`TrigTime` 프로퍼티 수용 | **T2** (라이브 0건) | REQ-SONGCUE-014 DESCOPE |
| ASSUMPTION-23 | 빈 시퀀스 번호를 식별할 수 있는가 | 미실측 | REQ-SONGCUE-009가 거부로 답한다 |
| ASSUMPTION-24 | 곡 1개 번들의 왕복이 실용 범위인가 | BUSKWIZ 실측에서 계산 | M0에서 재측정 |

**ASSUMPTION-21만 성격이 다르다.** 나머지 넷은 부정이어도 기능을 좁혀 출하할 수 있지만, 21이 부정이면 "곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개"라는 **산출물 정의 자체**(REQ-SONGCUE-007)가 성립하지 않는다. BUSKWIZ의 ASSUMPTION-18이 M2를 기술적으로 막았던 것과 같은 성격이며, §E.1 `blocking_for_run`에 그대로 적었다. ASSUMPTION-23은 BUSKWIZ가 익스큐터에서 데인 함정("비어 있음"과 "존재하지 않음"이 응답에서 구별되지 않는다 — `SPEC-COPILOT-BUSKWIZ-001/progress.md:218-249` 측정 2)이 **시퀀스 축에서 재발하는지**를 묻는다. 시퀀스는 주소 공간 상한이 문제되지 않을 가능성이 있으나 **그 판단을 실측 없이 내리지 않는다.**

#### AC · REQ 개수 정합 — 실측으로 닫았다

착수 시점에 **정본 2종을 직접 세어** 아래를 확정했다. LOOKLIB이 재감사에서 plan-phase 문서와 `acceptance.md` §C.0의 마일스톤 AC 배정 3곳 불일치를 지적받고 사후 재정합한 전례(`SPEC-COPILOT-LOOKLIB-001/progress.md:80`)를 반복하지 않기 위해, 배정은 **acceptance.md §C.0의 "마일스톤별 AC 집합" 표가 SSOT**이고 형제 문서가 그것을 복제하지 않고 인용한다.

| 계수 | 실측 | 수단 |
|---|---|---|
| 요구 정의 | **21** (`REQ-SONGCUE-001`~`021`) | spec.md §B의 정의 행 21개 = 고유 토큰 21개 |
| 역추적표 행 | **21** | acceptance.md §C.0의 REQ 행 21개 — 정의와 1:1, 누락 0 |
| AC 본문 | **18** (`AC-SONGCUE-001`~`018`) | acceptance.md §C.1 헤딩 18개 = 고유 토큰 18개 |
| 역추적표에 등장하는 고유 AC | **16** | 나머지 2건은 `AC-SONGCUE-017`(전제 판정) · `AC-SONGCUE-018`(종단 통합)이며 §C.0이 그 부재를 **의도로 명시**한다 |
| 마일스톤 배정 합 | **18** | M0 1 · M1 4 · M2 1 · M3 6 · M4 3 · M5 1 · M6 1 · M7 1 — 각 AC가 정확히 한 번, 중복 0 · 누락 0 |
| clarification 마커 | **0** | 정본 2종 전량 |

M6의 `AC-SONGCUE-010`·`AC-SONGCUE-011` **재확인은 소유가 아니다** — 최초 판정은 M3 소관이고 M6는 회귀로만 다시 본다. 이 구분을 흐리면 같은 AC가 두 번 카운트되어 합이 20이 된다.

#### 수치에 대한 규율 — plan-phase에서는 측정하지 않는다

**본 v0.1.0 로그는 테스트 개수 · 통과 수 · 커버리지를 단 하나도 적지 않는다.** plan-phase는 그것을 측정하지 않았으므로 적는 순간 근거 없는 수치가 된다. 이는 선례에서 실제로 발생한 결함이다 — LOOKLIB은 한 마일스톤이 기록한 수와 다른 마일스톤이 **같은 HEAD에서** 실측한 수의 차이를 끝내 규명하지 못했다(`SPEC-COPILOT-LOOKLIB-001/progress.md:1336`). 본 SPEC은 spec.md §C와 acceptance.md §E가 이미 **"각 마일스톤이 착수 직전 직접 실측하며 이월 인용을 금지한다"**로 못박았고, run-phase 킥오프에서 착수 SHA와 함께 최초 기준선을 기록한다. `<BASE>..HEAD` 범위 역시 협상 불가다 — 인자 없는 `git diff`는 커밋 직후 항상 빈 출력이라 PRESERVE 게이트가 무력해진다.

위 표의 계수(21 · 18 · 5 · 0)는 **테스트 측정이 아니라 문서 계수**이며 정본 2종을 세면 누구든 재현할 수 있다. 그래서 적었다.

#### §F를 착수 시점에 선제 생성한다

LOOKLIB의 plan-phase 문서는 "구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다"라고 적었으나(`SPEC-COPILOT-LOOKLIB-001/plan.md:289`), **그 §F 헤딩은 LOOKLIB의 progress.md에 실제로 존재하지 않았다** — 가리킨 목적지가 없는 **끊어진 참조**였다. BUSKWIZ가 착수 시점 선제 생성으로 그것을 고쳤고(`SPEC-COPILOT-BUSKWIZ-001/progress.md:865-867`), 본 SPEC은 그 교정을 그대로 계승한다. 아래 §F 헤딩은 **v0.1.0 착수 시점에 이미 존재하며** 본문만 오케스트레이터를 기다린다.

#### next

**plan-audit 실행**(Tier L PASS 기준 0.85. 감사 보고서는 `.moai/reports/plan-audit/` 아래 **파일로 영속화**한다 — 대화 안에만 존재한 감사는 처리 누락을 사후 검증할 방법이 없다는 것이 LOOKLIB이 남긴 교훈이다) → **M0 라이브 세션 접근 가능성 확인** → **Implementation Kickoff Approval**(plan→run HUMAN GATE) → run(M0 프로브부터). **M0 이전에 M3 저작을 착수하지 않는다** — ASSUMPTION-21이 블로킹이다.

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-28
spec_version: "0.1.0"
audit_rounds: 0            # 본 SPEC의 plan-audit 보고서는 .moai/reports/plan-audit/ 아래 0건
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 21           # REQ-SONGCUE-001~021 — spec.md 정의 행 21 = 고유 토큰 21
acceptance_criteria: 18    # AC-SONGCUE-001~018 — acceptance.md 절 제목 18 = 고유 토큰 18
decisions_closed: 3        # 사용자 확정 3건 (spec.md 사전 확정 사실 1/2/3)
decisions_open: 0          # 본 SPEC이 새로 여는 엔지니어링 결정 0 — BUSKWIZ 결정 E/F/H를 계승만 한다
clarification_markers: 0
assumptions_open: 5        # ASSUMPTION-20/21/22/23/24 — 전부 M0 라이브 실측 대상
live_sessions_planned: 2   # M0 프로브(AC-SONGCUE-017) + M7 종단(AC-SONGCUE-018)
machine_gates:
  requirements_counted: "21 — spec.md 정의 21 = 고유 토큰 21"
  req_to_ac_coverage: "21/21 — acceptance.md 역추적표 REQ 행 21, 커버 누락 0"
  acceptance_criteria_counted: "18 — acceptance.md AC 절 제목 18 = 고유 토큰 18"
  ac_milestone_assignment: "18 — M0 1 · M1 4 · M2 1 · M3 6 · M4 3 · M5 1 · M6 1 · M7 1, 중복 0 · 누락 0"
  ac_absent_from_traceability_table: "2 — AC-SONGCUE-017(전제 판정) · AC-SONGCUE-018(종단 통합), acceptance.md가 의도로 명시"
  clarification_markers_ssot_pair: 0
  clarification_markers_progress_md: 0
  ssot_line_anchors_in_progress_md: 0     # 정본 2종은 토큰으로만 참조. 본문의 spec.md:N 형태는 전부 타 SPEC(BUSKWIZ · LOOKLIB)의 것이며 허용 대상이다
  sibling_line_anchors_in_progress_md: 0  # 본 SPEC의 plan.md · design.md · research.md 줄 앵커 0
  abbreviated_tokens_progress_md: 0       # 정규식 (?<![A-Z-])(AC|REQ)-[0-9]{3}
  abbreviated_tokens_ssot_pair: "이동 중 — 착수 계수 23, 재계수 8(오케스트레이터가 동일 세션에서 완전 토큰 교체 진행). 최종 계수는 plan-audit 소관"
  live_cue_commands_in_audit_logs: 5      # 전부 Cue 1. Cue 2 이상 라이브 실행 0건 = ASSUMPTION-21의 계수 근거
  code_anchor_drift_measured: 5           # 심볼 앵커 4 + dedupe 블록 경계 1. '앵커 실측 정정 4건' 절, 전량 실측 좌표로 대체
known_gaps:
  - "정본 2종의 축약 토큰이 본 문서 작성 중 교체되고 있어 최종 계수를 본 문서가 확정하지 않았다. SSOT는 본 문서의 소유가 아니다."
  - "형제 3종(plan.md · design.md · research.md)의 기계 게이트는 본 문서 작성 시점에 동시 작성 중이라 미측정. plan-audit이 6종 전량에 대해 잰다."
  - "타임코드 · TrigType · Cue 2 이상은 전부 라이브 실행 기록 0건 — plan-phase가 닫을 수 없고 M0가 닫는다."
  - "브리핑 앵커 5건이 실측과 어긋났다(정정 완료). 같은 부류가 형제 문서에 남아 있는지는 plan-audit이 6종 전량 앵커 검증으로 확인해야 한다."
blocking_for_run: "ASSUMPTION-21이 M3를 기술적으로 막는다 — 같은 시퀀스에 Cue 2 이상을 추가할 수 없으면 곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개라는 산출물 정의(REQ-SONGCUE-007)가 성립하지 않으므로 DESCOPE가 아니라 저작 차단이다. M0 판정 전에 M3에 착수하지 않는다. ASSUMPTION-20/22는 M4의 정책 게이트일 뿐이며(GO/DESCOPE 양 분기가 AC-SONGCUE-012에 이미 정의됨), M1·M2는 M0와 독립이라 선행 가능하다."
next: "plan-audit 실행 (Tier L 기준 0.85, 보고서를 .moai/reports/plan-audit/ 아래 파일로 영속화) → M0 라이브 세션 접근성 확인 → Implementation Kickoff Approval (plan→run HUMAN GATE) → run(M0 프로브부터)"
```

## §E.2 Run-phase Evidence

_<pending run>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

> 본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다. plan-phase 문서의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다. 이 헤딩은 v0.1.0 착수 시점에 **선제 생성**되었다 — LOOKLIB의 plan-phase 문서가 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목해 **끊어진 참조**를 만들었고(`SPEC-COPILOT-LOOKLIB-001/plan.md:289`), BUSKWIZ가 선제 생성으로 그것을 고쳤다(`SPEC-COPILOT-BUSKWIZ-001/progress.md:865-867`). 본 SPEC은 그 교정을 계승한다. 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이며, 비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록이다.

_<pending orchestrator>_
