# SPEC-COPILOT-FXLIB-001 — Plan-Phase Research

> **근거 등급**: `[코드]`(리포지토리 소스 직접 판독) · `[문서]`(룰북·문서 산문 — **룰북의 "validated live" 선언 포함**) · `[실측]`(라이브 콘솔 직접 관측만 — 본 plan-phase에는 0건, 선행 SPEC 전재는 원출처 표기) · `[미확정]`(어느 것도 아님 → ASSUMPTION). 조사 방법: 병렬 read-only scout 3개 + 코디네이터 직접 재확인(제안서 grep · 줄 앵커 재실측 · 룰북 전문 판독).

## §1. 출처 — 제안서에 없다

- `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` 전수 grep(코디네이터 직접 실행, 2026-07-31): `이펙트|effect|페이저|phaser|MAtricks` 매치는 **2건뿐** — `:26`(버스킹형 정의의 배경 서술 "준비된 팔레트·이펙트·익스큐터"), `:52`(현재 앱 요약 "이펙트/큐 생성까지"). **이펙트 저작 항목은 0건.** `[코드]`
- 따라서 본 SPEC의 출처는 제안서가 아니라 **사용자 지시 격차 분석(2026-07-31)**이다: "의도→메모리 파이프라인" 1단계, LOOKLIB(정지 화면 어휘)의 시간축 자매편. 비제안서 출처 선례는 OVERLAP(spec.md:20, `feature/SPEC-COPILOT-OVERLAP-001` 브랜치 — **본 브랜치 트리에는 없음**, 인용은 그 브랜치 기준). `[문서]`

## §2. 조사 ① — 룰북 31의 검증 리터럴 (어휘의 원천)

`server/rulebook/assets/v2.4.2/31_choreography_patterns.md` 전문 판독(코디네이터 직접, 줄 앵커는 2026-07-31 실측). 파일 수준 선언 `:7` — "Every pattern below was validated live on onPC 2.4.2". **이 선언은 [문서] 등급이다** — 본 SPEC의 [실측]은 라이브 콘솔 직접 관측만을 가리키므로, 룰북 선언을 근거로 [실측]을 주장하지 않는다. **"39/39" 검증 카운트는 리포지토리 전수 grep 0건** — 존재하지 않는 수치이므로 어디에도 인용하지 않는다. `[코드]`

| 어휘 | 리터럴 | 앵커 |
|---|---|---|
| 목적지 | `ChangeDestination Root` 번들 선두 정확 1회 | `:11-23` (`:14` 코드) |
| 선택 | bare `Fixture …`/`Group …` — `Select`/`SelFix` 금지("Illegal object") | `:27-31` |
| 값·체이닝 | `Attribute '<name>' At …`, `;` 체이닝, ClearAll 규율 | `:35-41` |
| 페이저 | `At Relative 30` `:68` / `At Phase 0 Thru 360` `:69` / `At Speed 60` `:70`(**단위 미해결** — "BPM/Hz/sec per the phaser's Speed display") / `Store Sequence 12 Cue 1 'Pan Sweep'` `:71` | `:61-73` |
| 다단 | Step/Accel/Decel — **완전한 번들급 커맨드 라인 리터럴 부재**(`Step 2` / `Step 3` / `Step 1 At Accel -100` / `At Decel -100` 인라인 조각만 실재 — 조각의 조합 문법 미검증) → ASSUMPTION-37 | `:75-77` |
| 원형·역방향 | Pan Phase 0 + Tilt Phase 90 (0/180=대각선) / `Thru -360` | `:78-80` |
| MAtricks | `Set Selection MAtricks 'PhaseFromX' 0` `:85` · `'PhaseToX' 360` `:86` · `'X' 2` `:87` · `'XWings' 2` `:88` · `'XShuffle' 1234` `:89` · `Reset Selection MAtricks` `:90` · 풀 저장/호출 `:93-94`(v1 범위 밖) | `:85-94` |
| Store 규율 | CueFade `:50` · `/Merge` `:55` · 플래그(`/Overwrite`=destructive→게이트) `:57-59` | `:46-59` |
| 플레이백 | `Assign Sequence 11 At Executor 191` `:99`(명시 지정 시만) | `:96-104` |
| 트리거 | `Set Cue … Property 'TrigType'` `:111` / `/trig=` 금지 `:115-117` — **v1 범위 밖(SONGCUE 영역)** | `:106-117` |
| 트래킹 | ClearAll은 트래킹을 안 멈춤 | `:128-134` |
| 무드 시드 | warm/ballad Speed 10-20 · energetic/club 90-180 · dramatic accelerating — **폴백 설계 지침이지 라이브 검증 아님** | `:236-241` |
| 발명 금지 | 슬롯≠FID `:202-209` · "NEVER invent a `Group 3`" `:210-211` | `:202-211` |

**줄 앵커 드리프트 실증**: scout 전달값 대비 2건 정정 — mood 표가 LOOKLIB 인용(`:195-202`) 대비 `:236-241`로, 발명 금지가 `:184-191` 대비 `:202-211`로 밀려 있다. **착수 직전 재실측 관례**를 progress.md 인용 규율에 명기한다. `[코드]`

## §3. 조사 ② — 기존 코드 슬롯 (FXLIB은 그린필드가 아니다)

- `server/looks/schema.py:86-102` **MovementSpec**(attribute/phase_from/phase_to/speed/relative) — "v1 defines this field but does not emit it, and the v1 library carries no movement at all"(독스트링). Band 2 movement-only 어휘 `:46-47`, `KNOWN_ATTRIBUTES` `:52-54`, `Look.movement` `:116`. 로더는 파싱하지만 라이브러리 YAML의 movement 엔트리 0건, `instantiate.py`의 movement 참조 0건. **즉 "시간축"은 설계상 예약만 된 빈 슬롯이고, FXLIB은 그 슬롯을 채우는 게 아니라 자기 패키지를 세운다**(design.md §3 — MovementSpec은 P1-1/P1-2 소비 계약으로 보존). `[코드]`
- `server/web/panel.py:78-82` — rig snapshot은 페이저와 정적 값을 구분하지 못한다(scout 전달, 인용 유지). → 재조회 증거 채널의 선험적 한계 → ASSUMPTION-36. `[코드]`
- `server/looks/instantiate.py:1-31, 59-71` — 번들 규율의 기계화 선례(ClearAll 규율 상수 `_DESTINATION`/`_CLEAR` `:70-71`, 건너뜀 사유 코드 `:65-68`). `[코드]`
- `server/looks/busking.py:230-237` — `VALUE_LINE_COLLISION` 사유 코드와 그 논거("번들 안의 이웃에 달린 조건은 단일 빌더가 원리적으로 알 수 없다"). `[코드]`

## §4. 조사 ③ — 실행 파이프라인 특성 (게이트·dedupe·번들)

- **instruction-scoped dedupe (경계는 지시 턴 전체 — 번들 내가 아니다)**: 판정 지점 `server/orchestrator/tools.py:603-609`(`command in already_executed and not _is_programmer_state(command)`) — 비교 집합 `already_executed`는 번들이 아니라 **지시 턴 전체에 걸쳐 축적**된다: `runner.py:216`이 앞선 툴 호출들의 성공 커맨드를 `ExecutionContext(executed_ok=frozenset(executed_ok))`로 다음 호출에 넘기고, 판정 주석 원문이 "either **in a prior tool call** (context.executed_ok) or earlier in THIS bundle"이다. 면제 집합 `_PROGRAMMER_STATE_COMMANDS` `:283-287` — `Clear` / `ClearAll` / bare `Fixture|Group` 선택 3종뿐(fullmatch, 대소문자 무관). 면제 설계 논거 주석 `:241-281`. **값 라인 중복은 `skipped_already_executed`로 탈락하고, 탈락한 채 Store가 실행된다** — 같은 지시 턴의 교차 호출에서도 동일하다(REQ-FXLIB-011 (b)가 이 경계를 소비). BUSKWIZ 실증(`[실측]` 원출처: BUSKWIZ progress.md). dedupe 규칙 개정은 기각 선례. `[코드]`
- **재조회 경로 표**: `tools.py:117-127` — `sequences: DataPool/Sequences` `:120`, `matricks: DataPool/MAtricks` `:125`(**매핑만 존재, MAtricks 실측 0건** → ASSUMPTION-39). scout 전달값 `:126`은 1줄 드리프트 — `:125`로 정정. `[코드]`
- **단일 초크포인트**: `server/tests/test_architecture.py:1-39` — 전역 import 스캔, 허용 접두 3종 `:27-31`, 파일 정확 예외 `:34-39`, **신규 모듈 자동 포섭** `:12-13`("any NEW module … touching the bridge fails this test"). `server/fx/`는 생성 즉시 포섭 — 예외 추가 금지. `[코드]`
- **안전 게이트**: 닫힌 블랙리스트 하에서 `Phase`/`Speed`/`MAtricks`/`At`/무플래그 `Store`는 보류 없이 통과, `Off …` 변형은 invoking-verb expand-or-hold, `Store /overwrite`는 블랙리스트(스크리닝 의미론 무변경 — `server/safety/**` 수정 불요, 승인 대기 0건). scout 판정 전재. `[코드]`
- **실행 특성**: stop-on-first-failure + 이후 `not_executed`; 번들 규모 기준선 87줄/5.77s, ~66ms/줄(66.3-66.7ms). `[실측]` 원출처: BUSKWIZ progress.md:278-281 라이브 기록(전재 — 본 plan-phase의 관측 아님).

## §5. 조사 ④ — 미검증 축 4건 → ASSUMPTION-36~39

| # | 축 | 현 상태 | 판정 소비처 |
|---|---|---|---|
| ASSUMPTION-36 | 저장 큐의 페이저 값 **재조회** 판독 | 기록 0건 + panel.py 비구분 — **M0 1순위** | M4 리포트 문면 · M7 증거 형상 |
| ASSUMPTION-37 | Step/Accel/Decel 다단 리터럴 | 조각만 — 완전 리터럴 부재(`:75-77`) | M1 다단 필드 사용 · M2 pulse/chase |
| ASSUMPTION-38 | Speed 단위 | 룰북 자신이 3후보 병기(`:70`) | 라이브러리 시드 재보정 · 리포트 문면 |
| ASSUMPTION-39 | MAtricks 풀 재조회 | 경로 매핑만(`tools.py:125`) | 증거 채널 폭 기록 (v1 형상 불변) |

전부 `[미확정]`. ASSUMPTION-36의 이중 구조(기능: 큐가 모션을 담는가 / 증거: 재조회가 돌려주는가)는 spec.md §C가 정본 — **재조회 부정은 축소, 모션 미저장은 중단(블로커)**이다.

## §6. 조사 ⑤ — 선행 SPEC 상속 판정 (전재 — 원출처 표기)

| 판정 | 원출처 | FXLIB 반영 |
|---|---|---|
| looks 6파일(`{schema,loader,roles,resolver,instantiate,matching}.py`)+`library/`·preview.py·console/lua·룰북·dedupe 루프 PRESERVE | OVERLAP spec.md:114-116 (타 브랜치) | 전량 계승 + busking/report/songcue*는 **본 SPEC이 추가 잠금** — 읽기 import만, 수정 0 (plan §A.5) |
| Cmd OK ≠ 효과 증거 · 날조 대조군 선행 | BUSKWIZ progress.md:275-283, :314 · SONGCUE | M0 절차 + REQ-FXLIB-014 (c) |
| 기존 번호 무플래그 Store = "Not allowed" 거부 (fail-closed) | SONGCUE progress.md:344 | REQ-FXLIB-012 (b) |
| 재조회 truncation max_children=24 → 거부 | SONGCUE F-3 | REQ-FXLIB-012 (c) |
| 빈 익스큐터 식별 불가 | BUSKWIZ 측정 2 | REQ-FXLIB-013 + §D 제외 |
| 값 라인 충돌 가드 + dedupe 개정 기각 | BUSKWIZ (busking.py:230) | REQ-FXLIB-011 (1급 승격) |
| M0 판정 어휘·접두 행 (GO/NEGATIVE/CONDITION_NOT_MET/REOPEN_SCOPE · `GO:`/`DESCOPE:`/`SKIP:`/`REOPEN:`) | PRECHK acceptance.md:289 + progress.md P1-2/P1-3 (감사 지적으로 신설 — PRECHK plan.md에는 `DESCOPE:`만 존재) | plan §B M0 · AC-FXLIB-021 |
| M0 프로브 게이트 미경유(bridge 직결) → 감사 로그 없음 | LOOKLIB·PRECHK M0 관례 | M0/M7 증거 분담 (plan §B) |

## §7. 고려하고 기각한 대안

- **기각 (a) — looks MovementSpec 확장**: PRESERVE 위반 + P1-1/P1-2 파급 + 표현력 부족. design.md §3이 정본.
- **기각 (b) — 프리셋 저장 형태**: 프리셋의 동적 값 수용이 미측정. 미검증 전제 위에 산출물을 세우지 않는다 — 씬 컴파일러 후속 SPEC 몫 (사용자 확정 ②).
- **기각 (c) — 룰북에 FX 안내 축 추가**: 룰북 자산 PRESERVE. 발견성은 툴 스키마 설명 전담 (plan §A.4 결정 G).
- **기각 (d) — 생성형 Lua 경로**: v1 번들 ~10-15줄 — 커맨드라인 문자열로 충분, 배포 왕복 불요.
- **채택 — `server/fx/` 미러 패키지 + 기존 파이프라인 전면 재사용**: LOOKLIB 형상 검증 완료 선례의 최소 위험 경로.

## §8. 핵심 참조 파일

spec.md §E 표가 정본(중복 회피). 본 조사가 그 표의 전 행을 직접 판독 또는 원출처 표기로 커버했다.

## §9. 알려진 미결 지점 — 0건

- clarification 마커 0건 — 사용자 확정 ①~④가 결정 공간을 전부 닫았고, 남는 미지수는 전부 ASSUMPTION-36~39로 구조화되어 M0가 소비한다.
- 승인 대기 0건 — 어휘·안전·PRESERVE 어느 축도 신규 승인 불요(스크리닝 의미 무변경, 닫힌 어휘 확장 없음).
