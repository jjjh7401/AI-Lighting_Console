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

1. **① 음원 자동 분석은 본 SPEC의 범위가 아니다 — 섹션 목록은 사용자가 준다.** 근거는 세 축이 **동시에 0건**이라는 실측이다. (ⓐ) 오디오 의존성 0건 — `pyproject.toml:8-18`의 런타임 의존은 `anthropic`/`fastapi`/`google-genai`/`keyring`/`lupa`/`python-osc`/`pyyaml`/`uvicorn`/`websockets`이고 `uv.lock`의 **58패키지**(`^name = ` 계수) 전량이 무매치다 — `librosa`·`essentia`·`numpy`·`scipy`·`madmom`·`aubio`·`soundfile`·`torchaudio` 전부 없다. (ⓑ) 업로드 경로 0건 — 웹소켓 수신은 `server/web/app.py:311`의 `receive_text()` 텍스트 전용이고, **`server/web/app.py` 한정으로** 라우트 데코레이터는 **정확히 2개**(`@app.get("/healthz")` `:200` · `@app.websocket("/ws")` `:205`)이며 **저장소 전체로는 8개**다(그 2개 + `server/web/settings_api.py` 4개 `:117`·`:130`·`:146`·`:177` + `server/web/provision_api.py` 2개 `:109`·`:125`) — **8개 어느 것도 파일을 받지 않는다.** `UploadFile`·`File(`·`multipart`가 **`server/` 전체에서 0건**이고 `ui/src/**`에 `input[type=file]`이 0건이다. (ⓒ) Tauri capability가 업로드를 **명시적으로 거부**한다 — `src-tauri/capabilities/default.json:4`의 description이 "ALL network plugins are denied by omission … no http, no websocket, no upload"라고 적었고 그 문언을 테스트가 강제한다(`server/tests/test_deploy_tauri_shell.py:347-351`). 자동 분석을 함께 열면 신규 의존성 + 업로드 경로 + 진행률 프로토콜(현재 0건) 세 축이 한꺼번에 열린다. **별도 SPEC.**
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
| 첫 store 시 시퀀스 자동 생성 | **T2 + T1 정황** | `31_choreography_patterns.md:54`. T1 **5건**이 전부 **신규 번호**(62 · 30 · 90 · 22 · 17)에서 성공했다 |

**전수 계수로 확정한 것 — 라이브 감사 로그의 `Cue` 커맨드는 전 파일 통틀어 정확히 5건이고 전부 `Cue 1`이다.** `server/audit_logs/*.jsonl` 전량에서 커맨드 문자열에 `Cue <숫자>`를 담은 실행 기록을 뽑으면 `Store Sequence 17 Cue 1 'Golden Chorus'` · `Store Sequence 22 Cue 1 'Golden Chorus'` · `Store Sequence 30 Cue 1 'Ballad Warmth' CueFade 4` · `Store Sequence 62 Cue 1 'Cyan Look'` · `Store Sequence 90 Cue 1 'Blue Look'` 다섯 줄이 전부다(각 1회). 즉 위 표의 T1 5건은 **큐 축에 존재하는 라이브 증거의 전량**이며, `Cue 2` 이상은 표본이 없어서가 아니라 **한 번도 실행된 적이 없어서** T2다. ASSUMPTION-21의 블로킹 성격은 이 계수 위에 선다.

**이 표가 SPEC의 형태를 결정했다.** 두 개의 결론이 직접 따라 나온다.

- **큐 이름을 붙이는 방법은 store 인라인 3번째 토큰 하나뿐이다.** `Label Cue`가 룰북 0건이므로 이름은 `Store … Cue <m> '<name>'` 안에서만 확정할 수 있고, 따라서 REQ-SONGCUE-008의 ASCII 제약은 **저작 시점에** 걸려야 한다(사후 교정 경로가 없다).
- **본 SPEC의 핵심 형상이 정확히 미검증 구간에 놓인다.** "섹션 1개 = 큐 1개"는 같은 시퀀스에 `Cue 2` 이상을 얹는다는 뜻인데 그것이 T2다. 그래서 ASSUMPTION-21은 DESCOPE 후보가 아니라 **블로킹**이다(아래 참조).

#### 조사 결과 요지 ② — 결정적 부정 실측: 초안을 앱이 스스로 검증할 수 없다

`DataPool/Sequences/<n>/<m>` 재조회는 `name`/`class`/`i`(+ 중첩 `Part` 자식)만 반환하고 **커맨드 · CueFade · TrigType 등 프로퍼티는 어떤 형태로도 반환하지 않는다** — 라이브 실측이며 원 출처는 `.moai/state/verify/showui-m6-resume/5-probe-body.log`다(`SPEC-COPILOT-EXECREF-001/design.md:167`). 조회 경로 자체는 존재하고 라이브 실행 기록이 있다(`server/safety/console.py:399` `DEFAULT_BODY_PATHS["Sequence"] = "DataPool/Sequences/{ref}"`, 실행 기록 `SPEC-COPILOT-EXECBODY-001/progress.md:180`). 응답기는 `Cue`를 특별 취급하지 않는다 — `console/lua/copilot_responder.lua` 전체에 `Cue` 문자열이 **0건**이다. `resolve_path`의 주소형 특례는 `Executor <n>` **하나뿐**이며 주석이 스스로 "the ONLY address form"이라고 못박았다 — 그 주석과 패턴은 **응답기 Lua에 있다**: `console/lua/copilot_responder.lua:397-404`(해당 문장은 `:403` "This is the ONLY address form resolve_path special-cases")와 `:405`(`local EXECUTOR_ADDRESS_PATTERN = "^Executor%s+(%d+)$"`). **`server/safety/console.py:397-404`가 아니다** — 그 파일은 총 484행이고 `:403-405`는 `StateBodyFetcher` 클래스 선언부이며 `resolve_path`를 담지 않는다(v0.1.1 앵커 정정). 두 파일 다 PRESERVE이므로 게이트 판정은 바뀌지 않지만, REQ-SONGCUE-017의 한계 명시는 **Lua 응답기**를 근거로 서고 PRESERVE 경계도 `console/lua/**` 쪽이다.

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
| 9 | 상한 규모 왕복 실측 | 87줄 번들 **87/87 · 총 5.77s · 66.3ms/줄**(`SPEC-COPILOT-BUSKWIZ-001/progress.md:280`) · **누적 열화 없음**(같은 표 `:281` — 직후 10회 재측정 66.5 ms) | ASSUMPTION-24의 계산 기준선 |

#### 조사 결과 요지 ④ — 설계에 직접 영향을 주는 부수 실측 4건

1. **시퀀스 생성이 패널 핀에 자동 연동된다.** `server/orchestrator/last_created.py:30`의 `_STORE_SEQUENCE = re.compile(r"^\s*Store\s+Sequence\s+(\d+)\b", re.IGNORECASE)`가 발화를 가로채 핀을 만든다. 그런데 그 저장소는 **스냅샷 전용 · 최신 1건**이므로(`server/orchestrator/last_created.py:17-18`) "곡 1개 = 시퀀스 1개"일 때만 정상 동작한다 — 본 SPEC의 REQ-SONGCUE-007이 그 조건을 우연이 아니라 **요구**로 만든다. 같은 파일 `:27-29`는 `Store Cue 1 Sequence 71` 형태를 시퀀스 생성으로 읽지 **않는다**고 명시하며 테스트가 그것을 고정한다(`server/tests/test_last_created.py:58-61`).
2. **`Goto Cue <m> Sequence <n>`은 안전 게이트가 참조를 추출하지 못해 보류된다**(`server/tests/test_safety_classify.py:114`). 과보류라는 인정 기록도 있다(`SPEC-COPILOT-MVP-001/progress.md:215`). 즉 섹션 점프 UX는 **문법 문제가 아니라 게이트의 참조 인식 확장 과제**이며 본 SPEC의 범위가 아니다.
3. **게이트의 닫힌 참조 집합에 `Cue`가 없다** — `server/safety/classify.py:44` `RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor")`. `Store …`는 어느 분기에도 걸리지 않아 `safe`다(`server/tests/test_safety_classify.py:63-66`, `:150`). 본 SPEC의 저작 번들이 승인 카드 없이 흐르는 이유가 이것이며, 그래서 **검증 부담이 전부 앱 쪽에 있다**.
4. **곡은 후렴이 반복된다 — 값 라인 충돌 확률이 장르 팔레트보다 구조적으로 높다.** dedupe 면제 집합은 3종뿐이고(`server/orchestrator/tools.py:234-238` — `Clear` · `ClearAll` · 맨 `Fixture|Group` 선택형) `Store …`와 값 라인은 면제가 **아니다**. BUSKWIZ에서는 픽스처를 일부러 겹쳐야 재현됐지만 본 SPEC에서는 `Chorus`가 두 번만 나와도 밟힌다.

#### 앵커 실측 정정 4건 — 본 문서가 브리핑을 그대로 옮기지 않은 지점

plan-phase에서 인용 대상을 전수 확인하는 중 **인계 브리핑의 코드 앵커 4건이 실제 위치와 어긋남**을 실측했다. 정본(spec.md · acceptance.md)에는 이 4건이 **처음부터 0건**이고 정정값이 들어 있었으므로 정정 대상은 브리핑을 그대로 옮겨 쓴 문서뿐이며, 여기에는 **측정값만 남긴다.** 규율은 하나다 — **앵커의 정체는 줄번호가 아니라 심볼 식별자이며, 줄번호는 그 심볼을 찾는 좌표일 뿐이다.**

| 대상 | 브리핑이 인용한 앵커 | 실측 위치 | 인용 위치에 실제로 있는 것 |
|---|---|---|---|
| `_PROGRAMMER_STATE_COMMANDS` (dedupe 면제 집합) | `server/orchestrator/tools.py:227-231` | **`:234-238`** | 사유 주석(`Select …` 접두형을 면제하지 않는 이유)이 `:220-232`, `:233`이 `_SELECTION_OPERAND`. 소비 함수 `_is_programmer_state`는 `:241-244` |
| 자식 `name`을 본문 라인으로 수집하는 코드 | `server/safety/console.py:484-490` | **`:478-484`** (`_fetch_body_at_path`) | `:484`가 `return tuple(lines)`이고 **파일 총 길이가 정확히 484행이라 `:490`은 존재하지 않는다**(`wc -l` 484, `sed -n '485p'` 빈 출력, 파일이 개행으로 끝난다) |
| `RECOGNIZED_REFERENCE_TYPES` | `server/safety/classify.py:46` | **`:44`** | `:46`은 `_NUMERIC_REF` 정규식 |
| `DYNAMICS_TERMS` (섹션 어휘 표) | `server/looks/matching.py:21-25` | **`:92`** | `:21-25`는 모듈 독스트링의 **설명 산문**이다 — 표 자체가 아니다 |

네 건 모두 **가리키려던 대상 자체는 실재하며 사실 주장은 유효하다** — 어긋난 것은 좌표뿐이다. 본 문서는 실측 좌표만 쓴다. 착수 시점에 형제 문서 담당자 전원과 오케스트레이터에게 공유했고, 세 담당자가 독립 실측으로 같은 값을 회신해 **교차 확인**되었다. 단 하나 어긋난 회신이 있었다 — `console.py` 총 길이를 485행으로 보고한 건이 있으나 재계수 결과 **484행**이 맞다(위 셀의 증거 3종). 그 차이는 `:490` 부재라는 결론을 바꾸지 않는다.

같은 성격의 경계 어긋남이 dedupe 블록에도 있다 — **인계 브리핑의 PRESERVE 목록**이 `server/orchestrator/tools.py:526-550`으로 적었으나 실행 루프의 실측 경계는 **`:524`~`:569`**다(주석 `:525-532` · `already_executed` 시드 `:533` · 루프 `:534` · stop-on-first-failure `:535-543` · 건너뛰기 분기 `:544-557` · 실행 분기 `:558-569`). PRESERVE 게이트는 `git diff`로 파일 단위 판정하므로 **판정 결과는 바뀌지 않지만**, 인용 좌표는 실측값을 쓴다.

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

### v0.1.1 — plan-audit 1회차 수령과 처리 (2026-07-28)

**판정: FAIL 0.63 / Tier L 기준 0.85.** 지적 18건(**P0 2 · P1 6 · P2 10**, 감사 보고 표 기준) + P3 11건. 가중 점수 내역 — 인용 정확도 0.92(20%) · **교차 정합 0.35(30%)** · 요구·AC 정합 0.62(15%) · AC 기계 검증성 0.65(15%) · 증거 등급 규율 0.60(10%) · 범위 경계 0.90(5%) · 미결 은닉 0.85(5%). **점수를 끌어내린 것은 인용이 아니라 교차 정합이다** — 6종이 각자 정확한 사실을 적고 서로 다른 것을 말했다. 이 구분을 기록하지 않으면 재작성이 엉뚱한 축(인용 재검증)에 예산을 쓴다.

#### P0 2건과 그 처리

| # | 감사 원문 지적 | confidence | 확정과 처리 |
|---|---|---|---|
| **P0-1** | "결정 등록부가 plan.md·design.md에서 서로 다른 문자를 쓴다 — design.md의 '문자와 순서가 같다'는 거짓"(design.md §5.0) | 0.97 | 어긋난 문자 **5개**(D·E·F·G·J). 오케스트레이터가 **plan.md §A.4a / §F.1을 정본**으로 확정했다 — A 음원 분석 · B 타임코드 · C 큐 이름 · **D 라이브 세션 수** · **E 산출물 형상** · F 큐 번호 원장 · G dedupe · H 값 라인 충돌 · I 보고 계층 · J 섹션 어휘. **본 문서의 처리**: §E.1 `decisions_closed`를 **3 → 10**으로 정정했다(사용자 확정 3 + 엔지니어링 판단 7). 착수 시점의 3은 "사용자가 답한 것"만 세어 등록부 10건과 어긋나 있었다 |
| **P0-2** | "ASSUMPTION-23을 plan.md만 '블로킹'으로 규정 — 나머지 5종은 '동작 축소', 부정 시 절차도 없다"(plan.md) | 0.95 | **블로킹은 ASSUMPTION-21 하나**로 확정. ASSUMPTION-23이 부정이면 빈 시퀀스 번호를 확정할 수 없으므로 **거부로 답한다**(REQ-SONGCUE-009 · AC-SONGCUE-008 구간 ②)이며 **M3 저작을 막지 않는다.** **본 문서의 처리**: 정정 없음 — 착수 시점부터 ASSUMPTION 표의 ASSUMPTION-23 행("REQ-SONGCUE-009가 거부로 답한다")과 §E.1 `blocking_for_run`("ASSUMPTION-21이 M3를 기술적으로 막는다")이 정본과 일치했음을 재확인만 했다 |

**P0-1의 파생 지적**(P1, "등록부 밖 결정 신설")은 research.md §9.4가 정본과 **다른 뜻의 제3의 D·E**(큐 이름 발화 형태 / 섹션 점프 배제)를 신설한 건이며, research.md가 두 항목을 결정 문자 없이 정본 근거(REQ-SONGCUE-008 · spec.md §D `Out of Scope — 재생 · 섹션 점프`)로 재서술해 닫았다. 본 문서는 착수 시점부터 결정 문자를 쓰지 않았으므로 해당 없음이다.

#### 본 문서에 대한 지적 5건과 처리 (P2 3 · P3 2)

| 등급 | 지적 | 실측 확정값 | 처리 |
|---|---|---|---|
| **P2** | §E.1 `decisions_closed: 3`이 결정 등록부 10건 체제와 어긋난다 | 등록부 A~J = **10건**(사용자 확정 3 · 엔지니어링 판단 7) | `decisions_closed: 10`으로 정정. `decisions_open: 0`의 주석에서 "BUSKWIZ 결정 E/F/H를 계승만 한다"는 **사실 주장을 제거**했다 — D·E·F·I·J는 본 SPEC이 새로 닫은 것이라 계승만이라는 서술이 거짓이었다 |
| **P2** | T1 센서스가 "4건(62 · 90 · 22 · 17)"이라 시퀀스 **30이 누락**되어 같은 문서의 "전수 5건"과 모순 | **T1 5건**, 시퀀스 **{17, 22, 30, 62, 90}** | 등급 표의 "첫 store 시 시퀀스 자동 생성" 행을 **T1 5건 · 62 · 30 · 90 · 22 · 17**로 정정. 같은 절의 "전수 계수" 문단은 처음부터 5건·5줄을 적었으므로 무변경 |
| **P2** | `resolve_path` 주소형 특례 주석의 앵커를 `server/safety/console.py:397-404`(패턴 `:405`)로 적었다 | 실제는 **`console/lua/copilot_responder.lua:397-404`**(해당 문장은 **`:403`** "This is the ONLY address form resolve_path special-cases")와 **`:405`**(`local EXECUTOR_ADDRESS_PATTERN = "^Executor%s+(%d+)$"`). `server/safety/console.py`는 총 **484행**이고 `:403-405`는 `StateBodyFetcher` 클래스 선언부라 `resolve_path`를 담지 않는다 | 두 파일을 직접 열어 확인하고 정정. **REQ-SONGCUE-017 한계 명시의 핵심 근거가 Python 안전 계층이 아니라 Lua 응답기임이 드러났고, 따라서 그 근거가 서는 PRESERVE 경계도 `console/lua/**` 쪽이다**(둘 다 PRESERVE라 게이트 판정 자체는 불변) |
| **P3** | BUSKWIZ 87줄 상한 실측의 출처를 `SPEC-COPILOT-BUSKWIZ-001/progress.md:281-284`로 적었다 | 87/87 · 5.77s · 66.3 ms/줄은 **`:280`**이고, `:281`은 별개 행(직후 10회 재측정 66.5 ms = 누적 열화 없음) | 원문을 직접 열어 확인하고 두 사실을 각자의 줄에 분리해 인용 |
| **P3** | "라우트 데코레이터는 **정확히 2개**"가 저장소 전체 계수처럼 읽힌다 | `server/web/app.py` 한정 **2개**, 저장소 전체는 **8개**(app.py 2 + `server/web/settings_api.py` 4 + `server/web/provision_api.py` 2) | 범위를 명시하고 8개 전량이 파일을 받지 않는다는 사실을 함께 적었다 — 사전 확정 ①의 논거는 "라우트가 적다"가 아니라 "**어느 라우트도 업로드를 받지 않는다**"이므로 8개로 세어도 결론은 불변이다 |

또한 §E.1의 `abbreviated_tokens_ssot_pair` 게이트가 "이동 중 — 착수 계수 23, 재계수 8"로 열려 있었다. **오케스트레이터가 정본 2종에서 8건을 전수 교체 완료**했으므로 **0**으로 갱신했다(같은 회차에 `BUSKWIZ AC-SONGCUE-nnn` 오귀속 2건도 `AC-BUSKWIZ-nnn`으로 교정되었다). 이 게이트가 열린 채로 감사에 들어간 것이 P2 중 하나를 만들었다 — **"이동 중"은 게이트 값이 아니다.**

#### 감사가 전수 검증해 **정확하다고 확인한 것**

FAIL 판정이 "전부 틀렸다"로 오독되면 재작성이 이미 맞은 것까지 흔든다. 감사가 명시적으로 통과 처리한 항목을 함께 남긴다 — **인용 347쌍 중 어긋남 5건**(98.6% clean, 인용 대상 파일 **51/51 실재**) · 마일스톤 AC 배정 **1:1** · REQ **21** / AC **18** / ASSUMPTION **5** · clarification 마커 **0건** · 범위 재개방 **0건** · 자기오염 **0건** · 형제 줄앵커 **0건** · 계수 산술(5S+2 — 32·42·52 / 44·58·72) **전수 정확**. 즉 무너진 축은 **교차 정합 하나**이고 나머지 여섯 축은 서 있었다.

#### 감사 보고서가 또 파일로 남지 않았다 — 연속 3번째

v0.1.0의 "#### next"가 `.moai/reports/plan-audit/` 아래 **파일 영속화**를 명시적으로 요구했는데 이번 회차도 지켜지지 않았다. 사실을 정확히 좁히면 이렇다 — 그 디렉터리에서 **git 추적 대상은 `.gitkeep`뿐**이고(`.gitignore:211-214`가 "Plan-audit verdict reports are local artifacts; only .gitkeep is tracked"로 그 디렉터리의 `*.md`를 의도적으로 로컬 산출물로 제외한다), **로컬 보고서 6건은 실재한다**(`plan-audit-20260715.md` · `plan-audit-20260716.md` · `SPEC-COPILOT-EXECREF-001-2026-07-23.md` · 같은 SPEC의 `-review-1` · `-review-2` · `-review-3`). 남지 않은 것은 **SONGCUE·LOOKLIB·BUSKWIZ 회차**다. 따라서 "절차가 실행 지점을 갖지 못했다"는 결론은 성립하지 않는다 — EXECREF 회차는 실제로 집행되어 파일로 남았고, 이번 회차가 그 실행 지점을 쓰지 않은 것이다. 본 절의 지적 내역·점수·처리 기록이 **이 회차의 유일한 사본**이며, `known_gaps`에 같은 사실을 게이트로도 남겼다.

### v0.1.2 — plan-audit 2회차 수령과 처리 (2026-07-28)

**판정: PASS 0.87 / Tier L 기준 0.85 · P0 0건.** 1회차 **FAIL 0.63 → PASS 0.87 (+0.24)**이며, 자동 FAIL 조건인 P0가 0건이라 판정은 점수만으로 갈렸다. 1회차 지적 **29건**(본 표 기준 18건 + P3 11건) 전량을 감사가 재검증해 **닫힘 27 · 부분 닫힘 2 · 미해결 0 · 과잉수정 0**으로 판정했다. 다만 통과는 **조건부**다 — 신규 결함 **16건(P1 1 · P2 7 · P3 8)**이 남았고, 전부 문서 정합·기계검증성 층이라 실행을 막지는 않으나 선행 SPEC(BUSKWIZ가 PASS 0.88 후 조건부 지적을 전량 닫은 선례)의 규율을 따라 아래 표로 전건 처리했다.

#### 7축 가중 점수 — 무엇이 점수를 끌어올렸는가

| 축 | 가중치 | 1회차 | 2회차 | 가중 기여 변화 |
|---|---|---|---|---|
| 인용 정확도 | 20% | 0.92 | **0.93** | +0.002 |
| **교차 정합** | 30% | 0.35 | **0.83** | **+0.144** |
| 요구·AC 정합 | 15% | 0.62 | **0.88** | +0.039 |
| AC 기계 검증성 | 15% | 0.65 | **0.80** | +0.023 |
| 증거 등급 규율 | 10% | 0.60 | **0.92** | +0.032 |
| 범위 경계 | 5% | 0.90 | **0.95** | +0.003 |
| 미결 은닉 | 5% | 0.85 | **0.78** | **-0.004** |

가중합 **0.8655 → 0.87**(가중치 합 100%, 1회차 0.627 → 0.63과 같은 방식). **점수를 끌어올린 것은 인용이 아니라 교차 정합이다** — 그 축 하나의 가중 기여 +0.144가 총 상승분 +0.24의 **6할**이고, 인용 정확도는 0.92 → 0.93으로 거의 움직이지 않았다. v0.1.1 절이 남긴 진단("6종이 각자 정확한 사실을 적고 서로 다른 것을 말했다 — 이 구분을 기록하지 않으면 재작성이 엉뚱한 축에 예산을 쓴다")이 그대로 적중했고, 재작성 예산을 **인용 재검증이 아니라 교차 정합에 쓴 판단**을 2회차가 확인했다.

**내려간 축은 하나뿐이고 그 원인이 중요하다** — 미결 은닉 0.85 → 0.78. 원인은 이번 정정 회전이 **새로 써 넣은 문장 두 개**다(아래 N-4의 `.gitkeep` 거짓 주장과 N-5의 유령 미결). 즉 하락분은 오래된 부채가 아니라 **정정 자체가 만든 부채**이며, 신규 16건 중 4건(N-1 · N-2 · N-3 · N-4)이 같은 부류다. 1회차 지적을 닫는 편집이 새 결함을 만드는 비율이 4/16이라는 사실이 이 회차의 가장 값진 계측이다.

#### 1회차 29건의 재검증 결과

**닫힘 27 · 부분 닫힘 2 · 미해결 0 · 과잉수정 0.** 미해결이 0건이라는 것은 1회차 P0 2건(결정 등록부 문자 충돌 · ASSUMPTION-23 블로킹 규정)이 실제로 닫혔다는 뜻이고, 과잉수정 0건이라는 것은 **원래 맞던 서술을 반대로 바꾼 지점이 없다**는 뜻이다. 부분 닫힘으로 남은 축은 전부 잔여 지적을 동반했다 — dedupe PRESERVE 범위 통일(1회차 P1-4 → research.md 두 곳만 이탈, N-8) · ASSUMPTION-23 부정 시 절차(1회차 P0-2 → 정본 행만 귀결 누락, N-6) · `/Merge` 등급 문구(1회차 P1-3 → 측정 지시 없는 항목을 실측분이라 기술, N-9) · 기계 판정 가능화(1회차 P3-9 → AC-SONGCUE-014가 준-공허 단언, N-2). 정리하면 **1회차 지적에 미해결은 없고, 잔여는 전부 "닫으려다 만든 새 결함" 형태로 신규 16건에 재계상되었다.**

#### 신규 16건 처리 표 — 이번 회전에서 전건 닫았다

감사가 준 번호(N-1~N-16)를 그대로 쓴다. 형제 문서는 **절·토큰으로만** 지목한다(줄 앵커 금지 규율).

| # | 등급 | 지적 요지 | 실측 확정값 | 처리 · 소관 |
|---|---|---|---|---|
| **N-1** | **P1** | `DESCOPE:` 접두 행 규약이 **소비 측에만** 있고 생산 측(M0)에 없다 | AC-SONGCUE-012 ②④와 acceptance.md §B 시나리오 6이 행 존재로 기계 판정하는데, M0 산출물 지시와 AC-SONGCUE-017 비고 어디에도 그 형식 지시가 없다 | **닫힘** — plan.md M0 산출물 항과 AC-SONGCUE-017 비고에 `DESCOPE: ASSUMPTION-nn <사유>` 기록 규약을 명문화. 소관 plan.md · acceptance.md |
| **N-2** | P2 | AC-SONGCUE-014 기대 결과가 자기참조 비교라 M4 뮤테이션 ⑤를 죽이지 못한다 | 상수 대입만으로 통과 — 상수 값이 빈 문자열이어도 통과한다 | **닫힘** — 상수 동일성에 최소 내용 불변식(비어 있지 않음 + `CueFade`·`TrigType` 토큰 포함)을 더했다. 소관 acceptance.md |
| **N-3** | P2 | `PROPERTY_UNOBSERVED_NOTE`·`property_unobserved`가 acceptance.md에만 존재 | 6종 전수에서 그 두 토큰은 acceptance.md 2회가 전부 — 설계·계획이 정본이 못 박은 공개 심볼을 모른다 | **닫힘** — design.md 신규 모듈 항과 plan.md M4 파일 절에 공개 상수명·페이로드 키를 명기. 소관 design.md · plan.md |
| **N-4** | P2 | **본 문서**가 "`.moai/reports/plan-audit/`에는 `.gitkeep`뿐"이라 적고 거기서 "절차가 실행 지점을 갖지 못했다"를 결론지었다 — 거짓 | 그 디렉터리에 로컬 보고서 **6건 실재**. `.gitignore:211-214`가 `*.md`를 의도적으로 로컬 산출물로 제외한 것일 뿐 | **닫힘** — v0.1.1 절 산문과 `known_gaps` 항 두 곳을 "git 추적 대상은 `.gitkeep`뿐이며 로컬 보고서 6건이 있으나 SONGCUE·LOOKLIB·BUSKWIZ 회차는 남지 않았다"로 좁혔다. 소관 **progress.md(본 문서)** |
| **N-5** | P2 | 앵커 드리프트 5건의 출처를 **정본**으로 오귀속 — research.md §9.3이 표 왼쪽 열을 "정본의 인용"이라 이름 붙였다 | 그 5개 앵커는 현재도, 최초 커밋 `b471ef6`에도 spec.md·acceptance.md에 **0건**. 정본은 처음부터 정정값(`:478-484` · `:234-238` · `:524-569` · `:44` · `:92`)을 담고 있었고 출처는 **인계 브리핑**이다. 그 결과 "정본은 run-phase 킥오프 전에 정정한다"가 **수행 대상 없는 유령 미결**이 되었다 | **닫힘** — research.md §9.3의 제목·산문·표 머리를 인계 브리핑으로 귀속하고 처리 상태를 "정본은 이미 정정값을 담고 있다"로 닫았다. 본 문서의 앵커 정정 절과 dedupe 경계 문단도 같은 귀속으로 고쳤다. 소관 **progress.md(본 문서)** · research.md · design.md |
| **N-6** | P2 | spec.md §C 미검증 전제 표에서 ASSUMPTION-23만 "부정 시 귀결"이 없다 | 20·21·22·24는 전부 귀결을 적는다. 1회차 P0-2("블로커에 부정 시 절차 없음")의 잔여가 정본에 남았다 | **닫힘** — 그 행에 "여집합을 신뢰할 수 없으므로 번호를 추측하지 않고 거부한다(AC-SONGCUE-008 ②) — 동작 축소이지 블로킹이 아니다"를 추가. 소관 spec.md(오케스트레이터) |
| **N-7** | P2 | REQ-SONGCUE-008이 못 박은 "발화 형태 = store 인라인 3번째 토큰 한정 / `Label Cue` 금지"가 어느 AC의 기계 판정에도 걸리지 않았다 | AC-SONGCUE-007은 ASCII·한글·자산 필드만, AC-SONGCUE-009는 `/Overwrite`·`/Remove`·`Delete`·`/trig=`만 본다 — 설계가 요구하는 스캐너를 인수 기준이 요구하지 않았다 | **닫힘** — AC-SONGCUE-009 ①의 금지 패턴에 `Label Cue`·`Goto Cue`를 넣고 ②의 주입 목록도 넓혔다. 소관 acceptance.md |
| **N-8** | P2 | dedupe PRESERVE 범위를 **research.md만** `:523-569`로 적었다 | 정본 범위는 **`:524-569`**(spec.md · plan.md 7곳 · design.md 3곳 전부 그 값). `:523`은 `outcomes: list[CommandOutcome] = []` | **닫힘** — research.md 두 곳을 `:524-569`로 맞추고 `:523`은 괄호 설명으로 돌렸다. 소관 research.md |
| **N-9** | P3 | M0가 `/Merge` **한 형태만** 발화하는데 계수 각주·결정 E는 "`/Merge` 포함 여부도 M0 실측분"이라 적는다 | ASSUMPTION-22는 `'Follow'`/`'Time'` 분리 측정을 명시 지시한 것과 대조된다 — 측정 지시 없는 항목을 측정 결과로 기술 | **닫힘** — 문구를 좁히는 대신 **측정 지시를 넣는 쪽**을 골랐다. plan.md M0의 ASSUMPTION-21 항과 AC-SONGCUE-017 측정 항목 1 **양쪽에** "`/Merge` 있는 형태와 없는 형태를 각각 발화해 결과를 구분 기록한다"를 넣었다(ASSUMPTION-22의 `'Follow'`/`'Time'` 분리 지시와 동형, 두 형태를 서로 다른 시퀀스 번호에서 발화). 좁히는 쪽을 버린 이유는 `/Merge` 없는 `Store`가 기존 큐에 대해 병합인지 치환인지가 **저작 안전성 자체**이고, 한 형태만 재면 결정 E의 "M0가 잰 리터럴 그대로"가 가리킬 대상이 정해지지 않는다는 것이다. 소관 plan.md · acceptance.md |
| **N-10** | P3 | "추측된 경로는 죽은 채 출하된다" 기록을 `server/orchestrator/tools.py:77-79`로 인용 | `:77-79`는 리그 컨텍스트 섹션 목록(`matricks` / `worlds`)이고 해당 문장은 **`:80-82`** | **닫힘** — 파일을 직접 열어 확인하고 `:80-82`로 정정. 소관 research.md |
| **N-11** | P3 | `@MX:ANCHOR` 두 블록 인용이 **3방향**으로 갈린다 | 실측 블록은 **`:693-703`**(instantiate_look) · **`:817-824`**(prepare_busking)이고 `:692`·`:816`은 빈 `#` 줄. plan.md가 드리프트로 지목한 값을 design.md가 쓰고 있었다 | **닫힘** — 세 문서를 `:693-703` / `:817-824`로 통일. 소관 research.md · design.md · plan.md |
| **N-12** | P3 | `DYNAMICS_TERMS` 항목 범위가 **3방향** | 정의 **`:92`** · 항목 **`:94-130`** · 닫는 `}` **`:131`**. 정정 전 plan.md가 쓴 `:94-128`은 `"피날레"`·`"finale"` 2항목을 범위 밖에 두었고, spec.md·design.md가 쓴 `:99-121`은 인트로~드랍 **열거 항목 한정**이라 `:94-98`(앰비언트 밴드)·`:122-130`이 그 밖에 남는다 | **닫힘** — 항목 전체를 가리키는 자리는 전부 `:94-130`으로, 열거 한정 자리는 그 한정을 문장 안에 명시. 소관 plan.md · research.md · spec.md · design.md |
| **N-13** | P3 | design.md 앵커 정정 표가 dedupe 사유 주석을 `:526-532`로 적었다 | 실측 **`:525-532`**(plan.md는 정확) — 한 줄 시작점 어긋남 | **닫힘** — `:525-532`로 정정. 소관 design.md |
| **N-14** | P3 | design.md §3 데이터 흐름이 `CueFade`를 **무조건형**으로 그린다 | 결정 E는 "`CueFade`는 사용자가 준 값이 있을 때만 발화하고 없으면 무-CueFade 형식을 쓴다 — 둘 다 T1이라 선택 비용 0"이다 | **닫힘** — `[CueFade <t>]` 선택형 표기로 맞췄다. 소관 design.md |
| **N-15** | P3 | design.md §8이 "결정 I의 '한계 문구' 항"을 근거로 든다 | 결정 I가 정하는 것은 **모듈 분리 + `report.py` 공개 접근자 1건 추가**뿐이고 한계 명시는 REQ-SONGCUE-017·AC-SONGCUE-014 소관이다 | **닫힘** — 결정 I에 없는 항의 인용을 제거하고 소관 요구·AC로 되돌렸다. 소관 design.md |
| **N-16** | P3 | plan.md §A.2 계수 각주 표 헤더 "DESCOPE 분기 (5S+2)"가 축별 독립 판정 재구성 이전 어법 | 5S+2는 ASSUMPTION-20·22가 **둘 다 부정**일 때만 성립하고, 오른쪽 열만 축 이름을 갖고 있어 비대칭이다 | **닫힘** — 왼쪽 열을 "ASSUMPTION-22 부정 (5S+2)"로 축을 명시. 소관 plan.md |

**본 문서가 직접 닫은 것은 N-4와 N-5의 progress 측 2건이다.** 나머지는 정본·형제 문서 소관이며 같은 회전에서 병행 처리했다. N-4·N-5가 둘 다 **이번 정정 회전이 새로 써 넣은 문장**이었다는 점을 기록한다 — 1회차 지적을 닫는 편집이 자기 확신을 근거 없이 강화하는 방향으로 미끄러졌고(둘 다 "절차가 무너졌다"·"정본이 틀렸다"는 더 센 주장이었다), 그것이 미결 은닉 축을 유일하게 끌어내렸다. **닫힘 보고는 원본 파일을 다시 열어 대조한 값으로만 쓴다**는 규율을 v0.1.1에서 이어 이번에도 적용했다.

#### 감사가 재현해 정확하다고 확인한 계수

| 항목 | 값 | 항목 | 값 |
|---|---|---|---|
| 인용 검사(중복 제거) | **185**, 어긋남 **5** → 97.3% | 결정 등록부 | **10** (3표 문자·순서 일치) |
| REQ 정의 | **21** | 기각 대안 | **7** |
| AC 본문 | **18** | 위험 표 행 | **15** (결번·중복 0) |
| 역추적표 REQ 행 | **21** | AP | **20** (결번·중복 0) |
| 역추적표 고유 AC | **16** (017·018 의도적 부재) | 축약 토큰 | **0** (6종 전수) |
| 마일스톤 AC 배정 합 | **18** (중복 0 · 누락 0) | clarification 마커 | **0** (6종 전수) |
| ASSUMPTION | **5** (20~24) | 라이브 `Cue` 커맨드 | **5** (전부 `Cue 1`) |
| `uv.lock` 명명 패키지 | **58** | 라우트 데코레이터 | **8** |
| spec.md §D Out of Scope 절 | **7** | 번들 줄수 5S+2 / 7S+2 | 32·42·52 / 44·58·72 **산술 일치** |

`§E.1` YAML은 `yaml.safe_load` 파싱에 성공하고 그 안의 계수가 위 실측과 전량 일치했다 — 단 하나 어긋난 것이 `known_gaps`의 `.gitkeep` 항(N-4)이고, 이번 회전에서 닫았다.

#### 감사가 스스로 적은 한계 4건 — 다음 회차가 아니라 run-phase가 받는다

감사는 자기 판정의 한계를 넷 적었다. 판정을 뒤집지 않으므로 3회차를 돌리지 않되, **기록해서 넘긴다**: ① 인용 185개는 전수가 아니라 표적 표본이다(1회차가 347쌍을 셌다 — 룰북 3파일과 로드맵·제안서 산문 일부는 존재만 확인). ② **1회차 감사 보고서 원문을 보지 못했다** — 이 디렉터리에 SONGCUE 회차 파일이 없어 18건의 문면은 오케스트레이터 요약과 v0.1.1 절에만 의존했다(N-4가 좁힌 사실의 실제 비용이 바로 이것이다). ③ 뮤테이션 20건 중 AC-SONGCUE-014 충돌만 실증했고 나머지는 코드 없는 시점의 논리 검토다. ④ 실행 가능성은 판정 대상이 아니다 — `Cue 2 /Merge`와 `TrigType 'Time'`의 수용 여부는 M0 라이브 세션만 답한다. ①③은 run-phase의 각 마일스톤이 착수 직전 실측으로 덮고, ②는 3회차를 열지 않는 대신 **본 절을 사본으로 삼는다.**

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-28
spec_version: "0.1.0"
audit_rounds: 2            # 1회차는 Plan-phase log v0.1.1 절, 2회차는 v0.1.2 절에 지적·점수·처리 내역 전문
audit_1: { verdict: FAIL, score: 0.63, threshold: 0.85, findings: 18, p3_findings: 11, breakdown: "P0 2 · P1 6 · P2 10 (+ P3 11)" }
audit_2: { verdict: PASS, score: 0.87, threshold: 0.85, closed: 27, partially_closed: 2, unresolved: 0, over_corrected: 0, new_findings: 16, breakdown: "P1 1 · P2 7 · P3 8 (P0 0)" }
audit_2_axes: "인용 0.93(20%) · 교차정합 0.83(30%) · 요구AC정합 0.88(15%) · AC기계검증성 0.80(15%) · 증거등급규율 0.92(10%) · 범위경계 0.95(5%) · 미결은닉 0.78(5%) → 가중합 0.8655 → 0.87. 점수를 올린 것은 교차 정합(+0.144, 총 상승분 +0.24의 6할)"
post_audit_2_fixes: "신규 16건 전건 처리 — 본 문서 N-4(.gitkeep 사실 좁힘)·N-5 progress 측(앵커 출처를 인계 브리핑으로 귀속) · research.md N-5/N-8/N-10/N-11/N-12 · spec.md N-6 · acceptance.md N-1/N-2/N-7/N-9 · plan.md N-1/N-3/N-9/N-11/N-12/N-16 · design.md N-3/N-5/N-11/N-13/N-14/N-15. 번호 정의는 v0.1.2 절의 신규 16건 처리 표"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 21           # REQ-SONGCUE-001~021 — spec.md 정의 행 21 = 고유 토큰 21
acceptance_criteria: 18    # AC-SONGCUE-001~018 — acceptance.md 절 제목 18 = 고유 토큰 18
decisions_closed: 10       # 결정 등록부 A~J 전량 (plan.md §A.4a/§F.1이 정본) — 사용자 확정 3(A·B·C) + 엔지니어링 판단 7(D~J)
decisions_open: 0          # 등록부 A~J에 열린 슬롯 0. 형제 문서는 이 등록부를 소비만 하며 새 결정 문자를 만들지 않는다
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
  abbreviated_tokens_ssot_pair: 0         # plan-audit 후 정본 2종에서 전수 교체 완료 (착수 계수 23 → 재계수 8 → 8건 전량 완전 토큰). 같은 회차에 BUSKWIZ 오귀속 2건도 AC-BUSKWIZ-nnn으로 교정
  live_cue_commands_in_audit_logs: 5      # 전부 Cue 1. Cue 2 이상 라이브 실행 0건 = ASSUMPTION-21의 계수 근거
  code_anchor_drift_measured: 5           # 심볼 앵커 4 + dedupe 블록 경계 1. '앵커 실측 정정 4건' 절, 전량 실측 좌표로 대체
  self_anchor_corrections_v0_1_1: 2       # 본 문서가 스스로 틀렸던 앵커 — resolve_path 특례(console.py -> copilot_responder.lua) · BUSKWIZ 87줄 실측(:281-284 -> :280). 둘 다 원본 파일을 열어 재확인
  audit_citation_pairs_verified: "347 — 어긋남 5건(98.6% clean), 인용 대상 파일 51/51 실재 (plan-audit 1회차 전수 검증)"
  audit_2_citation_checks: "185 — 어긋남 5건(97.3% 일치). 이번 회전에 교체·신설된 앵커는 전건 원본 대조 (plan-audit 2회차)"
known_gaps:
  - "1회차 정정이 새 불일치를 만들지 않았다는 증명은 plan-audit 2회차가 냈다 — 닫힘 27 · 부분 닫힘 2 · 미해결 0 · 과잉수정 0. 다만 2회차 신규 16건 중 4건(N-1 DESCOPE 규약 · N-2 AC-SONGCUE-014 · N-3 PROPERTY_UNOBSERVED_NOTE · N-4 .gitkeep)은 그 정정 회전이 만든 것이므로, v0.1.2 정정이 또 새 불일치를 만들지 않았다는 증명은 남아 있다. 3회차를 열지 않고 run-phase 각 마일스톤의 착수 직전 실측이 덮는다."
  - "타임코드 · TrigType · Cue 2 이상은 전부 라이브 실행 기록 0건 — plan-phase가 닫을 수 없고 M0가 닫는다."
  - "인계 브리핑의 앵커 5건이 실측과 어긋났다(정정 완료). 정본 2종에는 그 5건이 최초 커밋부터 0건이고 정정값이 들어 있었다. plan-audit 2회차가 6종 전량 앵커를 검사해(인용 185개 · 어긋남 5건) @MX:ANCHOR와 DYNAMICS_TERMS 범위가 3방향으로 갈린 것까지 특정했고, 그 5건은 v0.1.2에서 닫혔다."
  - "plan-audit 보고서가 .moai/reports/plan-audit/ 아래 SONGCUE 회차 파일로 남지 않았다 — git 추적 대상은 .gitkeep뿐이지만(.gitignore가 그 디렉터리의 *.md를 로컬 산출물로 의도적으로 제외한다) 로컬 보고서 6건이 실재하며 SONGCUE·LOOKLIB·BUSKWIZ 회차만 그중에 없다. 절차는 실행 지점을 갖고 있고 이번 두 회차가 그것을 쓰지 않았다. 두 회차의 유일한 사본은 Plan-phase log의 v0.1.1·v0.1.2 절이며, 2회차 감사가 1회차 원문을 못 본 것이 그 비용이다."
blocking_for_run: "ASSUMPTION-21이 M3를 기술적으로 막는다 — 같은 시퀀스에 Cue 2 이상을 추가할 수 없으면 곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개라는 산출물 정의(REQ-SONGCUE-007)가 성립하지 않으므로 DESCOPE가 아니라 저작 차단이다. M0 판정 전에 M3에 착수하지 않는다. 블로킹은 이 1건뿐이다 — ASSUMPTION-23이 부정이면 빈 시퀀스 번호를 확정할 수 없으므로 거부로 답하며(REQ-SONGCUE-009 · AC-SONGCUE-008 구간 2) M3 저작을 막지 않는다. ASSUMPTION-20/22는 M4의 정책 게이트일 뿐이며(두 축 각각의 GO/부정 분기가 AC-SONGCUE-012에 이미 정의됨), M1·M2는 M0와 독립이라 선행 가능하다."
next: "M0 라이브 세션 접근성 확인 → Implementation Kickoff Approval (plan→run HUMAN GATE) → run(M0 프로브부터). plan-audit는 2회차 PASS 0.87로 종료하고 3회차를 열지 않는다 — 신규 16건은 전부 P1 이하 문서 정합·기계검증성 층이며 v0.1.2에서 전건 닫혔다. M0 이전에 M3 저작을 착수하지 않는다(ASSUMPTION-21 블로킹)."
superseded_by_run: "§E.2 M0(2026-07-29)가 blocking_for_run과 next를 **소진**했다 — ASSUMPTION-20/21/22/23/24 다섯 건 전부 **GO**, DESCOPE 0건. ASSUMPTION-21 블로킹이 해제되어 **M3 저작 착수 가능**하다. 위 두 키는 plan-phase 시점의 감사 대상 기록으로 동결해 두며 현재 상태가 아니다. M0가 새로 연 항목은 §E.2 '계획을 고쳐야 하는 실측 4건'(F-1~F-4)과 Gaps 4건이고, 그중 **M4를 막는 것은 Gap 1(TrigTime 의미론 미관측)**, **M7을 막는 것은 F-1(큐 번호 재조회 불가)**이다."
```

## §E.2 Run-phase Evidence

### M0 — 라이브 프로브 (AC-SONGCUE-017, LIVE 2건 중 1번째) — 2026-07-29

**판정 5건 전부 GO. DESCOPE 0건. M3 저작 차단 해제.** 코드 변경 0 · 소스 파일 신규·수정 0.

#### 세션 조건 (착수 전 실측 — plan.md §B M0 baseline)

| | |
|---|---|
| 콘솔 | grandMA3 onPC 2.4.2, macOS (`app_gma3` PID 38963, `HOSTTYPE=onPC`) |
| 응답기 | `CopilotResponder` **v1.4.1** (ping 응답 `version` 실측) |
| OSC | **send 8000 / receive 9005** |
| 왕복 사전 확인 | `responder_roundtrip --listen-port 9005 --wait 5` → ping·state·exec **3/3 PASS** |
| 쇼파일 착수 상태 | Sequences **17** (`1,2,11–17,20,30,41,50,62,71,80,90`) · Groups 4 (`1,11,12,13`) · Timecodes **0** |
| 드라이버 | `.moai/state/verify/songcue-m0/probe.py` (scratch, `server.bridge.osc` 직결 — `responder_roundtrip`와 동일 등급의 매체 갭) |
| 원문 로그 | `.moai/state/verify/songcue-m0/steps.jsonl` (전 스텝 raw payload) |

**BUSKWIZ M0의 오진을 반복하지 않았다.** 착수 전 `SPEC-COPILOT-BUSKWIZ-001/progress.md:191`을 읽어 수신 포트 **9005**(기본 9000 아님)를 확인했고 첫 왕복에서 3/3 PASS했다.

#### 판정 요약

| # | 전제 | 판정 | 효과 증거 |
|---|---|---|---|
| 1 | **ASSUMPTION-21** 같은 시퀀스에 `Cue 2` 이상 (**블로킹**) | **GO** | 재조회 자식 수 증가 + 앞 큐 보존. `/Merge`·비`/Merge` **양 형태 모두** |
| 2 | **ASSUMPTION-23** 빈 시퀀스 번호 식별 | **GO** | 여집합에서 고른 101·102·103에 `Store`가 **정확히 그 번호로** 착지 |
| 3 | **ASSUMPTION-20** 타임코드 오브젝트·문법 | **GO** | `DataPool/Timecodes` 실재 + `Store Timecode 999` 후 childCount 0→1 |
| 4 | **ASSUMPTION-22** `TrigType`/`TrigTime` | **GO** | `'Follow'`·`'Time'` **양쪽 OK**, 날조 토큰·날조 프로퍼티는 각각 거부 |
| 5 | **ASSUMPTION-24** 곡 1개 번들 왕복 | **GO** | 86줄 **86/86** · 6.25s · 72.7 ms/줄 · 열화 +1.1ms |

**`DESCOPE:` 접두 행은 0건이다** — 다섯 판정이 모두 GO이므로 plan.md §B M0 기록 규약("GO 판정은 이 접두를 쓰지 않는다")에 따라 한 행도 쓰지 않았다. **AC-SONGCUE-012 구간 ②④의 행 존재 판정은 따라서 거짓이고 ①③이 발동한다** — 두 축의 `skip` 구간 테스트는 plan.md §B M3의 지시대로 축별 사유를 명시한 채 남긴다.

#### 측정 1 — ASSUMPTION-21 (블로킹 해제)

`/Merge` 유무를 **서로 다른 시퀀스 번호에서** 각각 발화했다(계획 지시).

| 시퀀스 | 발화 | 재조회 childCount | 사용자 큐 | 앞 큐 |
|---|---|---|---|---|
| 101 | `Store … Cue 1 'PROBEA1' CueFade 2` | 3 | 1 | — |
| 101 | `Store … Cue 2 'PROBEA2' CueFade 2 /Merge` | **4** | **2** | **보존** |
| 102 | `Store … Cue 1 'PROBEB1' CueFade 2` | 3 | 1 | — |
| 102 | `Store … Cue 2 'PROBEB2' CueFade 2` (**`/Merge` 없음**) | **4** | **2** | **보존** |
| 102 | `Store … Cue 1 'PROBEB3' CueFade 2` (**기존 큐**, `/Merge` 없음) | 4 (불변) | 2 | **거부 — `Not allowed`** |

**계획이 던진 질문("`/Merge` 없는 `Store`가 기존 큐에 대해 병합인가 치환인가")에 답이 나왔다: 어느 쪽도 아니다 — 거부한다.** 새 큐 번호에는 두 형태 모두 가산이고, **기존 큐 번호에는 플래그 없는 `Store`가 `Not allowed`로 거부되며 쇼파일은 불변**이다. 치환은 명시적 `/Overwrite`를 요구하고 그것은 룰북이 DESTRUCTIVE로 표시해 게이트가 사람 승인으로 라우팅하는 경로다. **REQ-SONGCUE-010(파괴적 커맨드 0건)은 구조적으로 안전하다** — 실수로 파괴 경로에 도달할 수 없다. M3는 결정 E에 따라 두 형태 중 하나를 고르면 되고, 실측상 **`/Merge`는 새 큐 번호에 대해 불필요**하다.

#### 측정 2 — ASSUMPTION-23 (BUSKWIZ 익스큐터 함정의 재발 없음)

`DataPool/Sequences` 열거는 **점유 슬롯마다 명시적 인덱스 `i`를 준다**(`1,2,11–17,20,30,…`, 희소). 따라서 **여집합이 계산 가능**하다 — BUSKWIZ가 익스큐터에서 데인 "미점유 인덱스가 해석되지 않아 비어 있음과 존재하지 않음이 구별 불가"(`SPEC-COPILOT-BUSKWIZ-001/progress.md:198`)는 **시퀀스 축에서 재발하지 않았다.**

개별 조회는 자유 번호(101·102)와 터무니없는 번호(9999)에 **똑같이** `path segment not found`를 준다. 그러나 이것은 함정이 아니다 — **시퀀스에는 "존재하지만 비어 있음"이라는 제3의 상태가 없기 때문**이다(점유=열거됨, 미점유=객체 없음). 익스큐터는 주소 공간이 선재해 그 구별이 필요했고, 시퀀스는 풀이 객체 기반이라 필요하지 않다. **결정적 증거는 착지 실측**이다 — 여집합에서 고른 101·102·103 전부에 `Store`가 정확히 그 번호로 착지했다. REQ-SONGCUE-009의 "여집합에서만 고른다"는 성립한다.

#### 측정 3 — ASSUMPTION-20 (T5 → 실측 GO)

**부정 프로브는 무력했다.** `Set Timecode 999 …`와 날조 키워드 `Set ZzzBogusType 999 …`가 **둘 다** `Illegal object`를 준다 — BUSKWIZ 측정 1이 겪은 "문법 없음과 대상 없음이 구별 불가"가 여기서는 실재한다. **판정을 가른 것은 생성 프로브다**: `Store Timecode 999` → `OK`, 재조회 `DataPool/Timecodes` childCount **0 → 1**(`Timecode 999`, `i=999`). 파싱이 아니라 **효과**다.

실측한 문법 — **M3·M4는 이 목록만 발화한다**:

| 커맨드 | 결과 | 효과 증거 |
|---|---|---|
| `Store Timecode <n>` | OK | 풀 childCount 0→1, `i=<n>` |
| `Set Timecode <n> Property 'Name' '<ascii>'` | OK | 노드 name이 `PROBETC`로 변경됨 |
| `Assign Sequence <s> At Timecode <n>` | OK | `TrackGroup 1` 자식 생성 |
| `Record Timecode <n>` | OK | (녹화 무장 — `Off Timecode <n>`로 해제 확인) |
| `Store Timecode <n> Sequence <s>` | **거부** | `User Canceled Command` (확인 대화상자 자동 취소) |
| `Stop Timecode <n>` | **거부** | `Not implemented` |

#### 측정 4 — ASSUMPTION-22 (`'Follow'`와 `'Time'`을 접지 않았다)

계획 지시대로 두 토큰을 **각각 따로** 쟀고, **날조 대조군**을 함께 발화해 `ok=True`가 변별력을 갖는지 먼저 증명했다.

| 커맨드 | `ok` | 응답 |
|---|---|---|
| `Set Cue 2 Sequence 101 Property 'TrigType' 'Follow'` | True | OK |
| `Set Cue 2 Sequence 101 Property 'TrigType' 'Time'` | **True** | **OK** |
| `Set Cue 2 Sequence 101 Property 'TrigType' 'Zzz'` | False | `Illegal value` |
| `Set Cue 2 Sequence 101 Property 'ZzzBogus' 'Follow'` | False | `Illegal property` |
| `Set Cue 2 Sequence 101 Property 'TrigTime' 4` | True | OK |
| `Set Cue 99 Sequence 101 …` (없는 큐) | False | `Illegal object` |
| `Set Cue 2 Sequence 9999 …` (없는 시퀀스) | False | `Illegal object` |

**룰북 줄 끝 주석의 토큰 메뉴에서 온 `'Time'`이 실측으로 승격됐다** — 곡 섹션 타이밍이 요구하는 쪽이 바로 이것이므로 REQ-SONGCUE-014가 성립한다. 콘솔은 프로퍼티명·값 토큰·객체 존재를 **각각 독립적으로** 검증하며 서로 다른 오류 문자열을 준다. 즉 **BUSKWIZ 측정 3의 "거부된 커맨드에 `Cmd()`가 OK를 보고했다"는 경고가 이 축에는 적용되지 않는다** — 여기서 `ok=True`는 변별적이다. 그럼에도 재조회를 효과 증거로 삼는 규율은 유지했다.

#### 측정 5 — ASSUMPTION-24 (계산 확인이 아니라 실측)

**ASSUMPTION-20이 GO이므로 plan.md §A.2의 예외 조항이 발동했다** — 타임코드 발화 형식이 계수 불가였던 근거가 사라졌고, 계산 확인 대신 **실측**했다. 12섹션 곡 1개의 종단 형상을 단일 번들로 발화:

| 항목 | 실측 | BUSKWIZ M0 기준 |
|---|---|---|
| 번들 줄 수 | **86** | 87 |
| 성공 | **86/86** | 87/87 |
| 총 시간 | **6.25s** | 5.77s |
| 줄당 | **72.7 ms** | 66.3 ms |
| 누적 열화 | **+1.1 ms**(전반 66.3 → 후반 67.4) | 없음 |

재조회 결과 시퀀스 103은 `Label Sequence`로 **`PROBESONG`**이 되었고 자식 14 = 시스템 2 + **사용자 큐 12**(`SEC01`…`SEC12`, 순서 일치)였다. **REQ-SONGCUE-007의 산출물 정의("곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개")가 실물에서 성립함을 종단으로 확인했다** — 타임코드 축 GO를 포함한 상태로. 번들 분할 정책은 필요 없다(§G 조건부 접점 2 미발생).

#### 계획을 고쳐야 하는 실측 4건

| # | 발견 | 영향 |
|---|---|---|
| **F-1** | **큐 자식의 `i`는 큐 번호가 아니라 나열 위치다.** `Store … Cue 7`로 저장한 `PROBEA7`이 `i=5`로 보고됐다. 반면 **풀 수준(`Sequences`·`Timecodes`)의 `i`는 실제 번호**다(101·999로 확인) | **AC-SONGCUE-018 측정 3의 "큐 N개가 서로 다른 번호로 존재"는 재조회로 직접 관측되지 않는다.** M7 착수 전 해당 AC의 검증 수단을 아래 우회로로 바꾸거나 응답기를 확장해야 한다 |
| **F-2** | **모든 시퀀스는 암묵 시스템 큐 2개(`OffCue`·`CueZero`)를 갖는다.** 갓 만든 시퀀스도 childCount 2에서 출발한다 | **AC-SONGCUE-017 측정 1의 문자 그대로의 "자식 2개" 기준은 오판한다.** 사용자 큐 수 = `childCount − 2`. 본 절은 그 보정을 적용해 판정했다 |
| **F-3** | **응답기 스냅샷에 `max_children = 24` 상한이 있다**(`console/lua/copilot_responder.lua`) | 시퀀스 풀이 24를 넘으면 열거가 `truncated`되어 **ASSUMPTION-23의 여집합 계산이 무효**가 된다. 현재 17이라 미발동. M3는 `truncated` 플래그를 반드시 확인하고 참이면 거부해야 한다(REQ-SONGCUE-020의 "추측 금지"와 동일 취지) |
| **F-4** | **큐 번호는 커맨드로는 관측 가능하다.** `Set Cue 7 Sequence 101 Property 'TrigTime' 0` → OK인데 `Set Cue 3 …` → `Illegal object`. 즉 존재/부재가 번호로 변별된다 | **F-1의 우회로다.** `PROBEA7`이 실제로 큐 **번호 7**임을 이 채널이 증명했다(나열은 `i=5`로 감췄다). AC-SONGCUE-018은 이 채널로 번호를 확인할 수 있으나 **쓰기성 프로브**라는 한계가 있다 |

#### 정리 기록 — 쇼파일 원상 복구 완료

프로브가 남긴 것: 시퀀스 **101**(큐 1·2·7 + `TrigType`/`TrigTime` 설정) · **102**(큐 1·2) · **103**(`PROBESONG`, 큐 12) · 타임코드 **999**(`PROBETC`, `TrackGroup 1`, 시퀀스 101 배정).

전량 삭제했고 **재조회로 베이스라인 일치를 확인**했다 — `DataPool/Sequences` = `[1,2,11,12,13,14,15,16,17,20,30,41,50,62,71,80,90]` (착수 시점과 **정확히 동일**), `DataPool/Timecodes` childCount **0**. **잔여물 0건.**

정리 중 실측 1건: **`Delete Sequence 101`이 처음에는 `User Canceled Command`로 거부됐다** — 타임코드 999에 배정돼 있어 확인 대화상자가 떴고 응답기가 그것을 자동 취소했다. 타임코드를 먼저 지운 뒤 재시도해 성공했다. **파괴적 커맨드가 확인 대화상자를 띄우면 기본값이 "취소"라는 뜻이며, 이는 안전 방향의 실패다**(REQ-SONGCUE-010에 유리). `Record Timecode 999`로 무장된 녹화 상태도 `Off Timecode 999`로 해제해 확인했다.

#### Gaps — 측정하지 못한 것

1. **`TrigTime`의 의미론(절대 시각 vs 직전 큐 기준 상대 지연)은 관측하지 못했다.** 계획이 "GO 시 반드시 함께 측정할 것"으로 지목한 항목이다. 원인은 **값 되읽기 경로의 부재**다 — 상태 조회는 name·class·slot만 반환하고(`copilot_responder.lua`에 프로퍼티 접근자 없음), `List Cue 2 Sequence 101`과 `Get Cue 2 Sequence 101 Property 'TrigType'`은 둘 다 `OK`만 돌려준다(값은 콘솔 커맨드라인 창으로 가고 OSC 응답에 실리지 않는다). **비파괴 범위에서 소진했고 판정 불가다.** M4가 이 값에 의존하므로 **M4 착수 전에 닫아야 한다** — 선택지는 (i) 응답기에 프로퍼티 읽기 추가, (ii) 두 큐의 실제 발화 시각을 재는 거동 관측. 어느 쪽도 M0 범위가 아니다. `PROPERTY_UNOBSERVED_NOTE`의 대상이다.
2. **매체 갭**: 전 발화가 `server.bridge.osc` 직결이며 `gate.screen()`을 경유하지 않았다 — LOOKLIB G2 · BUSKWIZ M0와 동일 등급이다. 안전 게이트를 통과한 발화의 종단 확인은 M7(AC-SONGCUE-018) 몫이다.
3. **F-3의 상한은 미실측이다.** `max_children = 24`는 소스에서 읽은 값이고 24를 넘는 풀에서 `truncated`가 실제로 어떻게 오는지는 재지 않았다(현재 시퀀스 17).
4. **`/Overwrite`는 발화하지 않았다.** 룰북이 DESTRUCTIVE로 표시한 경로이고 M3가 쓰지 않을 것이므로 비파괴 원칙에 따라 건드리지 않았다. 측정 1의 "치환은 명시적 플래그를 요구한다"는 `Not allowed` 거부로부터의 추론이며 `/Overwrite` 자체의 실측이 아니다.
5. **실측 원문이 git에 남지 않는다 — `known_gaps` 4항과 같은 실패 계열이다.** 전 스텝 raw payload 181행은 `.moai/state/verify/songcue-m0/steps.jsonl`에 있고 드라이버는 같은 디렉터리의 `probe.py`인데, **`.gitignore:206`의 `.moai/state/`가 둘 다 추적에서 제외한다**(BUSKWIZ `showui-m6` 선례와 동일 관례). 따라서 **커밋되는 유일한 사본은 위 절의 표와 인용문**이다. plan-audit 2회차가 1회차 원문을 못 봐서 치른 비용이 정확히 이것이었으므로, 본 절은 판정을 뒷받침하는 **모든 커맨드와 응답 문자열을 표 안에 그대로 옮겨 적었다** — 요약 서술로 대체하지 않았다. 원문 로그는 이 세션이 살아 있는 동안의 보조 증거일 뿐이다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

> 본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다. plan-phase 문서의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다. 이 헤딩은 v0.1.0 착수 시점에 **선제 생성**되었다 — LOOKLIB의 plan-phase 문서가 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목해 **끊어진 참조**를 만들었고(`SPEC-COPILOT-LOOKLIB-001/plan.md:289`), BUSKWIZ가 선제 생성으로 그것을 고쳤다(`SPEC-COPILOT-BUSKWIZ-001/progress.md:865-867`). 본 SPEC은 그 교정을 계승한다. 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이며, 비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록이다.

_<pending orchestrator>_
