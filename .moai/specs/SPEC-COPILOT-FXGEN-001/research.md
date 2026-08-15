# SPEC-COPILOT-FXGEN-001 — Research 색인

> **근거 등급** (FXLIB research.md 규율 계승): `[실측]`(라이브 콘솔 직접 관측 — 본 SPEC은 2026-08-15 세션 V1~V7, `tools/console_probe.py` 발화 + 오퍼레이터 GUI 관측; V6의 풀 리스팅 재조회만 기계 증거) · `[문서]`(공식 매뉴얼·포럼·룰북 산문) · `[코드]`(리포지토리 소스 직접 판독) · `[미확정]`(어느 것도 아님 → 거부 또는 DESCOPE).
>
> 본 SPEC의 조사 정본은 **2026-08-14 오케스트레이션 리서치 코퍼스**(브랜치 `research/ma3-effects-phaser`, 커밋 `2ba4989`)다. 본 문서는 그 색인이며, 서술이 어긋나면 코퍼스 원문이 이긴다.

## 코퍼스 색인 — `docs/research/ma3-effects/`

| 문서 | 내용 | 본 SPEC 소비처 | 등급 |
|---|---|---|---|
| `00-summary-and-plan.md` | 코디네이터 종합본: 핵심 결론 4건(MA3 이펙트 = Phaser · 명령줄 생성 가능 · FXLIB 기구현 · 함정 3종), 갭 G1~G6, 실행 계획 Phase 1~5(V1~V5 검증 항목 정의) | spec.md 전체의 골격 — 특히 §A.3 신규 표면과 §B의 열린 축 목록 | `[문서]` (계획) + `[코드]` (현황 분석) |
| `01-phaser-fundamentals.md` | 페이저 엔진·파라미터 총론: Speed/Phase/Measure/Width/Accel·Decel/Transition/SpeedMaster(16개 마스터, 각 0~225 BPM, §5.7 커맨드라인 문법) | REQ-FXGEN-001(축 정의·범위 상수), REQ-FXGEN-004(마스터 번호 1~16) | `[문서]` |
| `02-pantilt-effects.md` | 포지션 이펙트 7종 레시피(figure-8, ballyhoo, fly-out, 상대 서클 등) + 커맨드라인 문법 | 라이브러리 확충 레퍼토리(E. test_fx_library 관할), REQ-FXGEN-003(relative 의미론) | `[문서]` — V2 실측이 relative 축만 승격 |
| `03-color-dimmer-beam-effects.md` | 디머/컬러/빔 레시피(사인 디머 = Accel −100/Decel −100 공식 레시피, rainbow 3스텝, 아이리스/줌/고보) + Measure/MAtricks | REQ-FXGEN-002(V1의 재검증 대상이었던 사인 레시피), REQ-FXGEN-006(V5 rainbow) | `[문서]` — V1/V5 실측이 해당 축 승격 |
| `04-programmatic-phasers.md` | 명령줄 쿠크북 + 저장소 통합 분석: 함정 3종(§1.3), 미방출 축 갭(§3.4), `Store preset … Step 2`의 스텝 삭제 포럼 사례(§1.2) | REQ-FXGEN-008(리터럴 발명 금지), REQ-FXGEN-018(레시피 위험 사례) | `[문서]` + `[코드]` |
| `05-phaser-editor.md` | Phaser Editor 구조 + **프리셋 저장 의미론**: "All 1~5" 풀의 정체, `Store Preset <g>.<n> /Universal` 정확 문법(§8.3), 페이저 레이어 세트 저장(§8.4), 큐에는 값이 아니라 참조 저장·Recast(§8.6) | REQ-FXGEN-011(/Universal 문법 — V6 실측으로 승격), REQ-FXGEN-014(참조 의미론 문면), REQ-FXGEN-016(Phaser Editor 라우팅) | `[문서]` — V6/V7 실측이 저장·리콜 경로 승격 |
| `06-recipe-editor.md` | Recipe 패러다임 총론 + 명령줄 문법 후보(§5: EditRecipe/Assign/Cook — **문서 자신이 "이 저장소에서 검증되지 않았다"고 경고**), 채택 판정 "아니오 — 후순위"(§7.4) | REQ-FXGEN-018/019(레시피 쓰기 DESCOPE의 직접 근거), REQ-FXGEN-016(Recipe Editor 라우팅 — 읽기 안내만) | `[문서]` — 리포지토리 실측 0건, 승격 없음 |
| `07-matricks-editor.md` | MAtricks Editor + Grid x/y 서브선택 분석 | Out of Scope(Grid — 갭 G5), REQ-FXGEN-016(MAtricks Editor 라우팅) | `[문서]` — 실측 0건, 승격 없음 |

## 실측 세션 (2026-08-15) — 코퍼스 밖의 추가 근거

- **V1~V7 전량**: onPC 2.4.2, `tools/console_probe.py` 발화 + 오퍼레이터 GUI 관측. 정본은 `31_choreography_patterns.md`의 2026-08-15 추가 항(spec.md REQ-FXGEN-017 (b))이며, spec.md §A.1 표가 요약이다. `[실측]`
- **기계 증거의 유일한 예외**: V6의 프리셋 풀 리스팅 재조회 — 프리셋 오브젝트의 **생성**을 기계로 판독한다. **내용**(효과)은 V7에서 `childCount 0` 재확인 — 사람 관측만이 효과 채널이다. `[실측]`
- **미측정으로 남은 것**: Speed+SpeedMaster 조합, relative/절대 혼합 스텝, 레시피 쓰기 접수 여부, Grid 문법, attribute별 독립 속도 — 전부 spec.md의 거부 또는 Out of Scope로 귀결. `[미확정]`

## 코드 현황 (본 브랜치, 조사 시점)

- `server/fx/schema.py` — 열린 축 상수(`CURVE_AXES`/`SPEED_MASTER_MIN·MAX`/`WIDTH_MIN·MAX`/`MEASURE_MIN`)와 `PHASER_MODIFIER_AXES` 확장이 실측 주석과 함께 반영돼 있다. `[코드]`
- `server/fx/instantiate.py` — 프리셋 목적지(`build_fx_preset_bundle`/`select_preset_number`)와 거부 사유 코드 4종(`PRESET_POOL_UNAVAILABLE`/`PRESET_POOL_TRUNCATED`/`PRESET_NUMBER_UNAVAILABLE`/`PRESET_OCCUPIED`), `SPEED_SOURCE_CONFLICT`가 존재한다. `[코드]`
- `server/orchestrator/tools.py` — `find_fx`/`instantiate_fx`는 기존, **`compose_fx`는 미존재**(본 SPEC이 정의하는 신규 표면). `[코드]`
- `server/rulebook/assets/v2.4.2/` — `33_effect_editors.md` **미존재**, `31_choreography_patterns.md`에 2026-08-15 실측 항 **미반영**(코드 주석이 선행 인용 중 — REQ-FXGEN-017이 그 앵커를 실체화한다). `[코드]`
- `server/tests/test_fx_*.py` 6종 — 확장 관할은 spec.md §E 표가 정본. `[코드]`
