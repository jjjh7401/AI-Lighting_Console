# SPEC-LDRENDER-001 — 연구 근거 (prior-art 재사용 표)

표기 등급: **잰 값**(이번 조사 또는 t498/t499 가 직접 실행해 관측) · **코드 판독**(파일:줄을 읽은 것, 실행 아님) · **추정**(둘 다 아님, 가설).

## 1. R-항목 → 기존 SPEC/함수 재사용 → 격차

| R-항목 | 재사용하는 기존 자산 | 격차(이 SPEC 이 메우는 것) |
|---|---|---|
| R1 층별 렌더링 | SPEC-LDDESIGN-001 결함 6(`_confirm_song_layer_mapping`, 층 매핑 확인 UX·안전 큐 트래킹), `server/design/rig.py` `_LAYER_GROUP_ALIASES`(key/back/effect/audience 4역할), `song_cue_render.py` `_back_layer_value_lines`(BACK 전용 단일 역할 렌더링 — **코드 판독**, `:621-644`) | `_back_layer_value_lines` 가 `role=="back"` 하나만 처리한다(**코드 판독**). SIDE/WASH/MOVER 는 접두-접미 복합 그룹 이름이라 현재 정확 토큰 매칭에 안 걸려 역할 자체가 비어 있다(**코드 판독 + 테스트 고정**, `rig.py:92-95` 주석 + `test_layer_mapping_effect_role.py:119`). `CueDimmerData` 가 `key_pct`/`back_pct` 둘뿐이라 다른 역할의 값을 담을 자리가 없다(**코드 판독**, `song_cue_composer.py:157-165`). |
| R2 색 전부 쓰기 | SPEC-LDDESIGN-001 M2(`song_cue_render.py` `_song_color_value_lines`, M2 색 배선 — **completed**, 카드 db324e36), `section_palette.py` `_arc_palette`(구간별 보조색 회전 — 설계 층, **코드 판독**), SPEC-COPILOT-COLORMODE-001(`color_usage` 곡별 스위치, **completed**) | `_song_color_value_lines` 자신이 "주색만 낸다. 보조색·유보색·언더페인팅은 M3 의 몫"이라고 DESCOPE 를 문서화했다(**코드 판독**, `:568` 독스트링). 그 M3(SPEC-LDDESIGN-001 §3.5, REQ-LDDESIGN-026~035)는 완료됐지만 **컨셉 계층의 색 규칙**(유보색·언더페인팅·인접 구간 공통색)만 구현했고, **송신 줄 자체에 보조색을 싣는 일**은 포함하지 않았다 — t499 가 잰 값으로 재확인(`palette[0]` 하나만 소비). |
| R3 효과 기구 분리 | `song_cue_render.py` `_accent_fixture_value_lines`(블라인더 켜기/끄기, 카드 t462, **코드 판독**), `rig.py` `_LAYER_GROUP_ALIASES["effect"]`(BLIND/STROBE/HAZE 정확 일치, **코드 판독**, `:109-120`) | 전체 기구 디머 값 줄(`position_cue_bundle` 이 쓰는 단일 `fids`)이 `effect` 역할 그룹을 뺄 통로를 갖지 않는다(**코드 판독**, `:1000` 단일 `fids` 인자). 액센트 줄이 전체 디머 뒤에 와도 전체 디머가 이미 100 을 효과 기구에 먹였으므로 액센트의 80 이 하강으로 읽힌다(**잰 값**, t498 §0 큐 11). |
| R4 효과 송신 통로 | SPEC-COPILOT-FXLIB-001(페이저 라이브러리·`instantiate_fx`, **completed**), SPEC-COPILOT-FXGEN-001(`compose_fx`·`build_fx_preset_bundle`·`select_preset_number`, **completed**), `song_cue_render.py` `_phaser_cue_value_lines`(recall 줄 생성 — **코드 판독**, `:508-530`, 이미 호출됨 `:1051`) | FXLIB/FXGEN 은 **독립 저작 도구**(모델이 "서클 만들어줘"라고 지시하면 시퀀스+큐 또는 프리셋을 만드는 경로)이고, 곡 큐 송신 경로(`reviewed_song_commands`)와 **배선되어 있지 않다**(**코드 판독** — `tools.py` 의 `instantiate_fx`/`compose_fx` 핸들러와 `song_cue_render.reviewed_song_commands` 사이에 호출 관계 0건, grep 확인). `_phaser_cue_value_lines` 는 자체적으로 이미 recall 줄을 만들 수 있으나, 그 전제(`cue.dimmer.key_pct`>0 및 `phaser_slots` 비공백)가 8곡 전부 충족되지 않는다 — 원인은 설계 층의 `fx.permitted=0`(**추정**, 아래 §2). |
| R7 연출 판독 게이트 | `.moai/reports/t499/readout.py`(8곡 판독 로직, **completed 산출물**, 364행), `server/looks/report.py`(2단 보고 선례 — SPEC-COPILOT-SONGCUE-001·FXLIB-001 공통 패턴, **코드 판독**), SPEC-LDDESIGN-001 REQ-LDDESIGN-052(헤드룸 경고 비차단 선례, **completed**) | `readout.py` 는 **보고서 전용 스크립트**(`.moai/reports/`)이며 제품 코드가 임포트할 수 없다. 비차단 경고 채널 자체는 SPEC-LDDESIGN-001 이 이미 만들었으나(헤드룸), 그 채널에 "색/층/효과 미흡" 신호를 넣는 배선은 존재하지 않는다. |

## 2. `fx.permitted = 0` 원인 — 이 SPEC 착수 시점의 등급

t499 가 "추정"으로 남긴 서술(`.moai/reports/t499/verdict.md` §3 P5a): "원인 추정: `server/design/energy.py:262` `_fx_axes` 가 리그에 `EFFECT_AXIS_CAPABILITY` 기구가 없으면 0 — 가짜 콘솔이 패치 판독에 못 답해 리그 능력이 비었을 수 있다."

이 SPEC 의 M1(plan.md 참조) 착수 전, 이번 조사(2026-10-01, **코드 판독**만 — 콘솔 접촉 0)로 다음을 추가 확인했다:

- `RigInventory.capability_fids`(`server/design/rig.py:170-180`)는 `RigFixtureRecord.capabilities`(패치 레코드의 **명시 선언** 필드)로만 채워진다 — 독스트링 자신이 "never inferred from `type_name`"이라고 적는다(**코드 판독**, `:138-146`).
- `build_rig_profile(patch=..., groups={})`(`server/web/session.py:7445`, `:7556`; `server/orchestrator/tools.py:3324`)이 그 `patch` 인자를 채우는 파이프라인은 `server/design/rig_capability_read.py`/`capability_verdict.py`(SPEC-COPILOT-PRECHK-001 계열 — t344 카드 주석 인용)로 **코드 판독**됐으나, 이 SPEC 은 그 파이프라인이 실기에서 "effect" 능력을 실제로 선언하는지까지는 **확인하지 못했다**(미측정 — M1 의 과제).
- **"effect" 라는 문자열이 두 개의 서로 다른 축에 쓰인다**는 것은 이번 조사의 신규 발견이다(**코드 판독**): `RigLayers.mapping["effect"]`(역할→그룹번호, R1/R3 가 쓰는 주소록)와 `RigInventory.capability_fids["effect"]`(능력 선언, R4/`energy.py` 예산이 쓰는 것)는 서로 다른 데이터 구조이고 서로 다른 생성 경로를 갖는다 — 층 매핑에서 "effect" 역할이 해석됐다고 해서 능력 축의 "effect" 가 채워지는 것은 아니다. 이 구분을 t499 는 하지 않았다(그 보고서의 "추정"은 이 구분 이전 단계의 가설이다).

따라서 이 SPEC 착수 시점 등급: **추정에서 코드 판독으로 한 단계 진전**(두 축이 분리되어 있다는 사실) — 그러나 실기에서 능력 선언 경로가 실제로 동작하는지는 여전히 **미측정**이며, M1 이 그것을 닫는다.

## 3. 기존 입력이 서로 모순되는 지점 · 이미 존재하는 기능

- **모순 없음, 그러나 혼동 위험**: §2 의 "effect" 이중 의미. 두 SPEC(LDDESIGN 의 층 매핑, 이 SPEC 의 fx 예산 투입) 이 같은 영어 단어를 역할 이름과 능력 이름 양쪽에 썼다 — 코드 자체는 분리돼 있어 모순은 아니지만, 사람이 읽을 때 "매핑됐으니 능력도 있겠지"로 오판하기 쉽다. plan.md §B 위험 1 로 명시.
- **이미 존재하는 기능**: `_phaser_cue_value_lines`(recall 메커니즘)와 `_back_layer_value_lines`(단일 역할 렌더링) 둘 다 "새로 만들 필요가 없는" 기존 코드다. R4·R1 이 재구현하지 않도록 plan.md §F 안티패턴에 명시했다.
- **t499 추정 중 하나가 이 조사로 더 좁혀짐**: DinoDino 2색이 "구간 분할 큐 팔레트 회전 탓"이라는 추정(`server/design/cue_density.py` `rotate_palette` 관련, t499 §3 P1 각주)은 이번 조사에서도 **코드 판독하지 않았다** — `section_palette.py` 가 `rotate_palette` 를 import 하는 것만 확인(`:26`), 실제 분기 조건은 안 읽었다. 이 SPEC 의 AC-004 는 색 수만 재므로 이 미확정 사실에 의존하지 않는다.

## 4. plan-auditor iteration 1 FAIL(0.74) 재조사로 확정된 것 (2026-10-01, D6/D2 근거)

- **두 개의 서로 다른 정본 문서가 존재한다 — 이름이 비슷해 혼동하기 쉽다.** `docs/proposals/song-structure-lighting-standard.md`(구간 구조·타이밍·§6 조명 의도 — v1 조사, 원 spec.md 가 §6.1~§6.3/§11.2 로 인용)와 `docs/proposals/song-lighting-design-standard.md`(§2c `RigProfile` 축 정의·§4 축별 규칙 — `server/design/rig.py` 의 모듈 독스트링이 직접 인용하는 **코드 구속력 있는** 정본)는 **별개 파일**이다(**코드 판독** — `rig.py:1-3` 독스트링이 후자를 "docs/proposals/song-lighting-design-standard.md §2c"로 명시 인용). 전자는 §6.3 에서 "동시에 보이는 색은 최대 2개(지배색 1+액센트 1)"를 말하고, 후자는 §4b C1/C3 에서 "팔레트 3~5색"·"프런트(키층)는 중립/웜 화이트 유지"를 말한다 — 둘은 **서로 모순되지 않는다**(§6.3 의 "최대 2개"는 동시성 상한, §4b C1 의 "3~5색"은 곡 전체 팔레트 크기, 서로 다른 축을 말한다). 그러나 원 spec.md 는 전자만 인용했고 후자(코드가 실제로 구속받는 정본)는 인용하지 않았다 — 이것이 D2/D6 의 근본 원인이다.
- **`RIG_LAYER_ROLES` 는 코드로 강제되는 닫힌 어휘다**(**코드 판독**, `server/design/rig.py:44` `= ("key", "back", "effect", "audience")`, `:305-308` `_build_layers` 가 `declared_layers` 경로에서 이 밖의 역할에 `RigProfileError` 를 던짐). 근거는 `song-lighting-design-standard.md` §2c("role층 → 그룹 매핑(key/back/effect/audience)")다. 원 spec.md REQ-001/002 는 SIDE/WASH/MOVER 를 새 역할로 추가하는 것을 이미 결정된 일처럼 서술했으나, 이 튜플과 그 검증 경로를 **인용하지 않았다** — 코드 판독 범위가 `_LAYER_GROUP_ALIASES`(휴리스틱 테이블, 검증 없음)에만 머물고 `declared_layers` 구성·검증 경로(`session.py:7550-7556` → `rig.py:305-308`)까지 가지 않았던 것이 누락의 직접 원인이다.
- **같은 정본 §4a I1 이 "3층 구조(키/백/이펙트)"를 직접 정의한다** — ~~이것은 REQ-001 의 "3개 이상 층" 목표가 `RIG_LAYER_ROLES` 의 기존 3역할(`key`/`back`/`effect`)만으로 이미 달성 가능함을 뜻한다~~. **철회·정정(2026-10-01, 2차 — plan-auditor iteration 2 D12 가 지목)**: 이 결론은 "디머=0(꺼짐)도 층으로 센다"는 암묵적 가정 위에서만 성립했다. 감독 결정 2(LIT-only 집계 — 디머>0 인 역할만 층으로 센다)가 확정되면서 이 가정이 깨졌다 — R3(REQ-007)에 의해 `effect` 는 비액센트 큐에서 항상 꺼져 있으므로 LIT 버킷에 들어가지 않고, `key`+`back` 둘만 남는다(버킷 2개). **I1 의 "3층 구조"는 LIT 여부와 무관하게 역할 3개가 "존재"함을 말하는 것이지, 매 큐에서 그 3개가 전부 점등된 서로 다른 값을 낸다는 뜻이 아니다** — 이번 재조사가 I1 을 잘못 적용한 지점이다(코드 판독은 정확했으나, 그로부터의 추론이 틀렸다 — 교훈: 정본의 "역할이 3개 존재한다"와 AC 의 "3개가 매 큐 LIT 상태로 다른 값을 낸다"는 서로 다른 주장이며, 후자는 전자로부터 자동으로 따라 나오지 않는다). SIDE/WASH/MOVER 세분화(REQ-002)는 **필수가 아니라 선택**이라는 이전 결론도 함께 철회한다 — 감독 결정 1로 REQ-002 가 실제로 승격되면서 이 논쟁은 실무적으로는 닫혔지만, 추론 자체의 오류는 기록으로 남긴다(재발 방지).

## 5. 감독 결정 4건(2026-10-01, 2차) — 근거와 등급

| 결정 | 내용 | 등급 |
|---|---|---|
| 결정 1 | 역할 어휘 옵션 (a) — 정본 §2c + `RIG_LAYER_ROLES` 확장 | **감독 결정**(이 조사가 제시한 3옵션 비용표에 대한 응답) |
| 결정 2 | LIT-only 집계, 큐 단위 전수 판정(과반 아님) | **감독 결정** — plan-auditor D11(과반 문구)·D12(트리오 게이밍)를 동시에 해소. 위 §4 의 정정이 이 결정의 코드-측 함의다 |
| 결정 3 | `back`+`mover`=지배색, `side`+`wash`=보조색, `key`=웜화이트(§4b C3 인용) | **감독 결정** — §6.3 "최대 2개" 집계에 웜화이트를 포함할지는 **이 SPEC 의 읽음**(제외)이지 감독이 명시적으로 확정한 것은 아니다 — 플래그로 남는다(spec.md §3.2 [HARD]) |
| 결정 4 | R4 옵션 (a) 전면 확정 + 충돌 사전 검출 | **감독 결정** — 충돌 검출은 FXLIB REQ-FXLIB-012 (c) 의 기존 사유 코드 재사용으로 구체화(이 SPEC 의 설계 선택, 새 검사 발명 아님) |

## 6. 안 잰 것 (이 plan-phase 조사의 한계)

- `rig_capability_read.py`/`capability_verdict.py` 의 "effect" 능력 선언 로직을 **실행해 보지 않았다** — 함수 시그니처와 호출 체인만 grep 으로 확인(코드 판독). M1 이 실제 실행/실기 측정을 한다.
- FXGEN 의 `compose_fx`가 송신 경로에 통합될 때 instruction-scoped dedupe(한 지시 턴에 fx 인스턴스화 1회 제한, SPEC-COPILOT-FXLIB-001 REQ-FXLIB-011 (b))가 곡 전체 송신(여러 큐가 각자 페이저 recall 을 쏘는 경우)과 충돌하는지 — **미검증**, M6(페이저 사전 생성, 감독 결정 4로 이미 (a) 확정)가 구현 시 확인해야 한다.
- DinoDino 2색의 "의도 아님" 판정이 이 SPEC 의 R2 작업으로 바뀌는지 — 미검증(§3).
- `song_cue_composer.py` 의 `has_layer()` 호출부가 `side`/`wash`/`mover` 신규 역할 등장에 실제로 안전한지(§B 위험 7 (d), plan.md M2) — 이 조사는 grep 으로 호출부 존재만 확인했고 각 호출부의 의미론적 안전성은 **확인하지 않았다**(M2 의 과제).
- `key` 웜화이트가 §6.3 "최대 2개" 집계에서 실제로 제외되어야 하는지 — 이 SPEC 의 읽음(§4b C1 "+화이트/CTO" 병기 근거)이지 감독에게 직접 확인받은 사실은 아니다(위 §5 결정 3 행 참조, 플래그 유지).
