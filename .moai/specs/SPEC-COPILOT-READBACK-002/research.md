# SPEC-COPILOT-READBACK-002 — Research (포인터)

> 조사 일자 2026-09-03 · 기준 `origin/main adae0ac` · 읽기 전용(파일 변경 0, 콘솔 접촉 0)

이 SPEC 은 **자체 조사 문서를 갖지 않는다.** R3·R4 의 조사는 분할 전에 이미 수행됐고, 그 결과는 원본 문서에 그대로 남아 있다. 사본을 만들면 두 벌이 따로 노후하므로 여기서는 가리키기만 한다.

## 정본

**`../SPEC-COPILOT-READBACK-001/research.md`** — 네 요구(R1~R4)를 한 문서에 담고 있다. 그중 본 SPEC 의 근거는 두 절이다.

| 절 | 제목 | 본 SPEC 의 무엇을 뒷받침하는가 |
|---|---|---|
| **§R3** | Runtime responder version gate | `ping` 발행·파싱 경로 · 오프라인/저하 status 가 계산되고 표면화되는 자리 · 정확한 이음매 · live-1.6.1 / main-1.6.2 전례 · 기존 테스트 · 위험 |
| **§R4** | FixtureType handle→name translation for `precheck_vectorworks_diff` and `build_patch_sheet` | 결함의 문면(`README.md:289-302`) · 번역 경로 전체 · 표를 넘기는 유일한 호출자 · 번역 없이 소비하는 두 자리 · 표를 주입할 수 있는 지점 · 기존 테스트 · 위험 |

§R1·§R2 는 SPEC-COPILOT-READBACK-001 의 근거이며 본 SPEC 과 무관하다. 「Scope note on the console-write budget」 절은 네 요구 전부에 걸리므로 본 SPEC 에도 유효하다 — 다만 본 SPEC 의 쓰기 예산은 **0** 이다(REQ-READBACK2-013).

## 이 SPEC 이 추가로 측정한 것

원본 조사 이후에 잰 사실은 `plan.md` 가 소유한다. 조사 문서에 덧붙이지 않고 계획에 두는 이유는, 그 측정들이 **착수 전 재확인 대상**이지 배경 지식이 아니기 때문이다.

| 어디 | 무엇 |
|---|---|
| `plan.md` §B B1 | 옳은 호출자 행 정정 — `research.md` §R4 의 `tools.py:6353` 은 실측 **`:6356`**(`:6352` 는 `read_fixture_type_names` 호출) |
| `plan.md` §B B5 | **조회 예산 실측표** — `read_inventory` 여섯 호출 지점이 fixture-type 루트를 이미 읽는가(예 3 / 아니오 3, 다섯 핸들러). SPEC-COPILOT-READBACK-001 v0.1.1 에서 이관 |
| `plan.md` §C C-1 | 응답기 버전 불일치의 health state 결정(자체 status 채택, 2026-09-03). SPEC-COPILOT-READBACK-001 v0.1.1 에서 이관 |

## 분할 경위

SPEC-COPILOT-READBACK-001 이 네 요구를 한 SPEC 에 담아 REQ 32 / AC 33 이 되면서 Tier M 예산(각 16)의 2배를 넘었다(`.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-2.md` D11). 감독이 2026-09-03 에 두 Tier M SPEC 으로 분할을 결정했고, 분할선은 원본 `plan.md` 가 이미 「순수 서버 · 병렬 가능」으로 떼어 둔 자리를 그대로 썼다. 조사 문서는 나누지 않았다 — 네 요구의 코드 좌표가 서로를 참조하고 있어서, 자르면 근거가 끊긴다.
