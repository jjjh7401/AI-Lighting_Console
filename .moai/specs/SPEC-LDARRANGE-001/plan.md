# SPEC-LDARRANGE-001 — 구현 계획

## §A 맥락

- **입력**: `reports/ldbeat-feasibility-roadmap-20261010.md`(주 체크아웃 전용 경로 — 이 워크트리로 복사하지 않고 절대경로로 참조만 함, SPEC 진행안 순서 ①LDBEAT→②LDBARMAP→③LDARRANGE) · `reports/effect-arrangement-rules-20261007.md`(규칙 9개·역할 6종 §2·LOVE ATTACK 전체 배치 §3·0~25마디 격자 §4·감독 결정 §5) · `.moai/reports/t525/verdict.md`(무대 패치 좌표 86/86, 그룹 18개 중 4개·그룹당 앞 2칸만 확인) · `.moai/specs/SPEC-LDBEAT-001/spec.md`·`plan.md`(역할 어휘 출처 REQ-LDBEAT-004, 저장소 결정 미확정 REQ-LDBEAT-006, 송신 경로 REQ-LDBEAT-011~013 — status: draft, M1~M6 전부 미착수) · `.moai/specs/SPEC-LDRHYTHM-001/spec.md` REQ-LDRHYTHM-012(a)(비트/다운비트 미저장, 이 plan-phase가 `server/audio/analyze.py:352-390`로 재확인) · `.moai/specs/SPEC-LDDESIGN-001/spec.md` REQ-LDDESIGN-092/094/095(M7, AI 제안→「적용」 원칙의 출처, 단일 큐 단위) · `server/design/song_cue_render.py:815`(`_role_group_numbers`)·`:890`(`_effect_group_numbers`)(RG5 그룹-주소 패턴, 이 plan-phase가 재확인) · `server/design/section_palette.py:236-267`·`server/web/session.py:7685-7902`(`palette_mode` — 곡별 선택 메커니즘의 기존 선례).
- **전제 SPEC**: `SPEC-LDBEAT-001`(status: draft — M1~M6 전부 미착수, 이 SPEC의 산출물을 소비할 격자 화면·저장소 결정의 출처), `SPEC-LDBARMAP-001`(작성 시점에는 **존재하지 않았다** — 카드 t527이 병행 작성 중이었다; 지금은 PR #571로 생겼고 M4 PR #585로 저장 모양이 확정됐다, 카드 t545 현황 고지. 이 SPEC의 핵심 입력인 마디 지도의 출처). **이 SPEC의 run-phase는 두 전제 SPEC 모두가 run-phase에 진입하고 핵심 인터페이스가 안정된 뒤에만 착수한다**(§B 위험 1) — plan-phase 자체는 세 SPEC이 서로 독립적으로 진행 가능하다.
- **범위**: 역할×마디 초안을 생성하는 새 로직 모듈 1개(규칙 적용 + 그룹-번호 매핑) + AI 제안 카드 UI(LDDESIGN 패턴을 초안 전체 단위로 일반화) + `SPEC-LDBEAT-001` 격자와의 연결점(초안을 격자에 "편집 가능한 초안"으로 노출). 마디 분석(LDBARMAP), 격자 화면·저장·에미터·콘솔 송신(LDBEAT), 응답기 나눠 읽기 확장, 색 미세 조정, 다른 곡 규칙서 작성은 범위 밖(spec.md §4).
- **진입 조건**: 이 plan-phase 종료 후 Implementation Kickoff Approval(감독 착수 승인) — run-phase는 그 승인 뒤에만 시작한다. 그 승인 라운드에서 **spec.md §5의 열린 결정 4건 중 적어도 항목 1(마디 지도 인터페이스)·항목 3("느린 곡" 기준)을 감독에게 명시적으로 제시하고 확인받는다** — 항목 2(LDBEAT 저장 키)는 LDBEAT M2가 먼저 확정해야 하는 종속 결정이라 이 SPEC의 착수 승인만으로는 확정할 수 없다.

## §B 알려진 위험 (manager-develop 착수 전 필독)

1. **이 SPEC은 두 전제 SPEC에 동시 의존한다 — 둘 다 아직 run-phase를 시작하지 않았다.** `SPEC-LDBARMAP-001`은 디렉터리조차 없고(이 plan-phase 확인), `SPEC-LDBEAT-001`은 status: draft로 M1(콘솔 확인 프로브)조차 착수 전이다. run-phase 착수를 "일단 LDARRANGE부터 선작업"으로 서두르면, 마디 지도 스키마가 바뀔 때마다 생성 로직을 다시 쓰거나, LDBEAT 격자의 저장 키가 바뀔 때마다 연결점을 다시 배선하는 비용이 반복된다. **권고 순서**: LDBEAT M1~M2(또는 적어도 M2 저장소 결정) 확정 → LDBARMAP run-phase 진입 및 출력 스키마 고정 → 이 SPEC의 run-phase 착수. 이 순서를 당기려면 Implementation Kickoff Approval 라운드에서 감독이 명시적으로 확인해야 한다.
2. **"그룹 소속이 부분적으로만 확인됐다"를 "역할 배치를 못 만든다"로 오독하지 마라.** RG5 그룹-주소 패턴(`song_cue_render.py:815,890`)은 그룹 **멤버십**(어떤 fid가 속하는지)을 몰라도 그룹 **번호**만으로 값을 낸다 — 이 SPEC의 생성기도 이 패턴을 그대로 쓰면 그룹 소속 전수 확인(응답기 나눠 읽기 확장, 범위 밖)을 기다리지 않고 진행할 수 있다. 반대로 멤버십이 필요한 작업(예: "이 역할에 매핑된 그룹이 실제로 기대한 장비 종류를 담고 있는지 검증")은 이 SPEC에서 하지 않는다 — REQ-LDARRANGE-011/012가 이 경계를 명시한다.
3. **배치 규칙 9개를 전역 상수로 하드코딩하면 REQ-LDARRANGE-004를 어긴다.** `palette_mode`(`section_palette.py:236-267`)가 이미 "곡별 선택 상태 필드"의 선례를 보였다 — 규칙 적용 로직을 설계할 때 처음부터 "이 곡의 규칙 적용 방식" 필드를 데이터 모델에 넣는다. 나중에 전역 상수를 걷어내는 재작업보다, 처음부터 곡별 상태로 설계하는 쪽이 싸다.
4. **AI 제안 카드를 "LDDESIGN의 PLAN CUE 생성기를 그대로 포팅"으로 생각하지 마라.** `REQ-LDDESIGN-092/094/095`의 대상은 큐 카드 **하나**다. 이 SPEC의 대상은 역할×마디 **전체 초안**(여러 역할 × 여러 마디 구간에 걸친 값 집합)이다 — "포팅"이 아니라 "일반화"가 필요하다. 구체적으로, 승인이 칸마다 쪼개지면 안 된다(REQ-LDBEAT-012가 LDBEAT M4 쪽에서 이미 경계한 것과 같은 함정) — 이 SPEC의 AI 제안 카드는 초안 **전체**에 1개의 「적용」/거절 단위를 갖는다(REQ-LDARRANGE-009/010, acceptance.md AC-LDARRANGE-007).
5. **"느린 곡" 기준을 생성기 안에 수치로 박아 넣고 넘어가지 마라(§5 항목 3).** 배치 규칙서 원문에는 수치가 없다 — 감독의 "발라드처럼 느린 곡"이라는 질적 판단을 생성기가 혼자 수치화하면, 그 수치가 틀렸을 때 디버깅 대상이 "생성기 버그"가 아니라 "애초에 합의 안 된 임계값"이 된다. M1에서 이 결정을 명시적으로 받는다.
6. **재작성(카드 t533 — `SPEC-LDBEAT-001` v0.2.0이 트랙 모양을 재교정해 이 위험의 방향이 뒤집혔다).** **이제 LDBEAT·LDARRANGE의 역할 어휘는 `server/design/rig.py`의 `RIG_LAYER_ROLES`(key/back/side/wash/mover/effect/audience)와 같은 어휘다 — 섞지 않도록 지키던 축이 사라졌으니, 둘을 다시 분리하는 코드를 짜지 마라.** LDBEAT v0.2.0(PR #572, 카드 t526)이 트랙 모양을 재교정해, 이전 시안의 역할 6종(SCENE/BACK PULSE/SIDE CHASE/MOVER-U MOVE/MOVER-D MOVE/ACCENT — 장비와 효과를 섞은 임시 이름)을 철회하고, "줄 하나 = 콘솔 그룹 하나 = 시퀀스 하나" + 그 줄에 붙는 `rig.py`의 7개 층 역할 이름표로 바꿨다(REQ-LDBEAT-004). 이 SPEC도 그 교정을 그대로 따른다(REQ-LDARRANGE-002) — 생성기가 실제로 구분해야 할 축은 "트랙 정체성(= 콘솔 그룹)"과 "효과(펄스·체이스·스윕·웨이브·STROBE·BLIND, 큐 안의 내용일 뿐)"이지, 더 이상 "음악적 역할 축" 대 "장비 축"이 아니다. 배치 규칙서 §2의 역할 6종은 그 문서의 교정 전 1차 표기일 뿐이며 "콘솔 그룹별 배치"로 읽는다(값은 바뀌지 않는다) — 생성기 코드에서 트랙 식별자로 쓰지 않는다.

## §C 사전 점검 (run-phase 착수 직전)

```bash
git branch --show-current
git rev-parse HEAD
# 전제 SPEC 상태 재확인 — LDBARMAP 존재 여부, LDBEAT 진행 상태
ls .moai/specs/ | grep -i "LDBARMAP\|LDBEAT"
grep -n "^status:" .moai/specs/SPEC-LDBEAT-001/spec.md
# 역할 어휘 재확인(카드 t533 — LDBEAT REQ-LDBEAT-004가 v0.2.0에서 콘솔 그룹 트랙 + 7종 역할 이름표로 재교정했는지, LDARRANGE가 그 어휘를 쓰는지)
grep -n "key/back/side/wash/mover/effect/audience\|RIG_LAYER_ROLES" .moai/specs/SPEC-LDBEAT-001/spec.md
# RG5 그룹-주소 함수 위치 재확인(이름·줄 번호가 바뀌지 않았는지)
grep -n "^def _role_group_numbers\|^def _effect_group_numbers" server/design/song_cue_render.py
# palette_mode 곡별 선택 선례 재확인
grep -n "palette_mode" server/design/section_palette.py | head -5
# LDDESIGN AI 제안→적용 원칙 재확인
grep -n "REQ-LDDESIGN-092\|REQ-LDDESIGN-094\|REQ-LDDESIGN-095" .moai/specs/SPEC-LDDESIGN-001/spec.md
# 응답기 한도 재확인(그룹 소속 나눠 읽기 미구현 상태 — 범위 밖 전제)
grep -n "max_prop_value" console/lua/copilot_responder.lua
```

## §D 제약 (위반 금지)

- **PRESERVE**: `server/design/song_cue_render.py`의 `_role_group_numbers`/`_effect_group_numbers`(RG5 함수 본문 — 재사용만, 수정 금지) · `server/director/emit.py`의 `PLAYBACK_MODES`(이 SPEC이 수정할 이유가 없다 — 콘솔 송신은 LDBEAT의 몫) · `ui/src/components/RunbookMode.tsx`의 기존 5블록 순서(LDBEAT가 다루는 영역 — 이 SPEC은 그 화면에 데이터만 공급한다, 레이아웃을 직접 바꾸지 않는다).
- 배치 규칙 9개의 값(마디 수 4, 리듬층 수 2~3, 스트로브 마디 등)을 전역 상수로 하드코딩해 다른 곡에 암묵적으로 적용되는 경로를 만들지 않는다(REQ-LDARRANGE-004, AC-LDARRANGE-009가 검사).
- 생성기의 어떤 경로도 `fid`(장비 개별 식별자) 수준의 그룹 멤버십을 추론하거나 가정하지 않는다(REQ-LDARRANGE-011) — 그룹 번호 주소만 쓴다.
- AI 제안 카드의 승인·거절을 역할×마디 칸 단위로 쪼개지 않는다 — 초안 전체에 1개의 단위를 유지한다(REQ-LDARRANGE-009, AC-LDARRANGE-007).
- 이 SPEC의 어떤 코드도 콘솔에 직접 쓰지 않는다 — `ConsoleLink`/`exec`/`deploy` 류의 호출을 생성 로직에 넣지 않는다(REQ-LDARRANGE-003, AC-LDARRANGE-006이 검사).
- 마디 지도 스키마가 아직 확정되지 않은 상태에서, 그 스키마의 구체 필드명(작성 시점에는 존재하지 않던 `SPEC-LDBARMAP-001`의 필드)에 의존하는 코드를 작성하지 않는다(REQ-LDARRANGE-001) — 인터페이스가 확정되기 전까지는 그 경계를 추상화(예: 타입 스텁·프로토콜)로만 표현한다. **현황(카드 t545)**: 스키마는 확정됐다(M4, PR #585, 정본 `validate_bar_map`) — 필드명은 이제 실재한다. 이 줄이 막는 「미확정 스키마에 기대기」는 해소됐지만, REQ-LDARRANGE-001이 막는 「실제 지도 데이터 없이 데이터 의존 생성 로직 구현」은 데이터가 들어오기 전까지 그대로다.

## §E 마일스톤 (결정 번복 비용 순)

### M1 — 열린 결정 확정: 입력 인터페이스와 "느린 곡" 기준 (spec.md §5 항목 1·3)

가장 되돌리기 비싼 축 — 이후 모든 마일스톤이 이 결정 위에 선다.

- `SPEC-LDBARMAP-001`의 진행 상태를 재확인한다(§C 사전 점검; 카드 t545 현황: 존재·스키마 확정 둘 다 이미 충족 — PR #571·#585. 남은 확인은 실제 지도 데이터가 타임라인에 들어오는 진입 경로가 생겼는지다). 존재하지 않거나 출력 스키마가 미확정이면, 이 마일스톤은 **잠정 인터페이스(스텁 타입)**만 정의하고 실제 연결은 M4로 미룬다 — "스키마가 없으니 아무것도 안 한다"가 아니라 "스키마가 바뀌어도 흔들리지 않는 경계를 먼저 긋는다"가 목표다.
- "느린 곡" 판정 기준(spec.md §5 항목 3)을 감독과 확정한다 — 권고 기본값은 곡 메타데이터의 명시적 플래그(옵션 b)이며, BPM 임계값(옵션 a)을 보조 제안으로 노출할지도 이 마일스톤에서 결정한다.
- 결정과 근거를 `progress.md`에 기록한다.

### M2 — 데이터 모델: 규칙의 곡별 기본값 표현 (REQ-LDARRANGE-004~006)

되돌리기 비용이 M1보다 낮지만 M3~M5보다는 높다 — 규칙 적용 로직 전체가 이 모델 위에서 동작한다.

- `palette_mode` 선례(`section_palette.py:236-267`)와 같은 모양으로, 곡별 "규칙 적용 방식" 상태 필드를 설계한다 — 전역 상수가 아니라 곡 단위 상태다.
- 리듬층 동시 개수(보통 2, 드롭/마지막코러스만 3) 제약을 마디 구간 메타(드롭/마지막코러스 여부 — 이것도 마디 지도 또는 배치 규칙서 §3의 구간 라벨에서 온다)와 교차 검증하는 로직을 설계한다.
- 주인공 4마디 교대(8마디 상한) 제약을 교대 스케줄로 표현한다.

### M3 — 그룹 소속 불명 처리: RG5 그룹-번호 주소 재사용 (REQ-LDARRANGE-011~012)

되돌리기 비용은 낮다(기존 패턴을 그대로 가져오는 일) — 그러나 **"재사용 == 그대로 import해서 끝"이 아니라, 역할→그룹 매핑을 이 SPEC이 새로 선언해야 한다**는 것이 핵심이다(LDBEAT REQ-LDBEAT-009가 겪은 것과 같은 함정 — "매핑은 새로, 매핑 뒤 로직은 본뜬다").

- **재교정(카드 t533).** 콘솔 그룹 트랙(`SPEC-LDBEAT-001` REQ-LDBEAT-004 — 줄 하나 = 콘솔 그룹 하나, 7개 층 역할 이름표 key/back/side/wash/mover/effect/audience) → 그룹 번호의 매핑을 이 SPEC이 선언한다 — `reports/effect-arrangement-rules-20261007.md` §2 표(역할별 그룹 선택 — 교정 전 1차 표기, "콘솔 그룹별 배치"로 읽는다)가 그 그룹 선택 값의 1차 소스다.
- `_role_group_numbers`/`_effect_group_numbers`(`song_cue_render.py:815,890`)와 같은 모양의 함수(또는 그 함수 자체를 호출하는 얇은 래퍼)로 멤버십 전수 없이 그룹 번호 주소만 쓰는 생성 경로를 만든다.
- 커맨드 미리보기에 "멤버 N대" 같은 단정적 서술이 들어가지 않는지 자체 점검한다(REQ-LDARRANGE-012).

### M4 — 역할×마디 생성 로직 + AI 제안 카드 (REQ-LDARRANGE-002~003, 007~010)

되돌리기 비용은 M1~M3보다 낮다(결정된 모델 위에 로직을 얹는 일) — 다만 **M1에서 LDBARMAP 스키마가 스텁으로만 남아 있었다면, 이 마일스톤의 생성 로직은 그 스텁에 대해서만 동작을 보장한다**(실제 마디 지도 연결은 LDBARMAP run-phase 완료 후 재확인).

- 규칙 9개(§1)를 입력(마디 지도 스텁 또는 실제 출력 + 배치 규칙서 + 그룹 번호 매핑)에 적용해 역할×마디 초안을 산출하는 로직을 작성한다.
- STROBE 게이팅(REQ-LDARRANGE-007~008)을 M1의 "느린 곡" 결정과 마디 지도의 "임팩트" 표시에 연결한다.
- AI 제안 카드 UI를 LDDESIGN REQ-092/094/095 원칙을 초안 전체 단위로 일반화해 구현한다 — 「적용」 전 로컬 변형 없음, 거절 시 상태 유지(REQ-LDARRANGE-009~010).
- 생성 로직이 결정적(같은 입력 → 같은 출력)인지 자체 검증한다(acceptance.md AC-LDARRANGE-011).

### M5 — LDBEAT 격자 연결점 (spec.md §5 항목 2, 종속 결정)

되돌리기 비용은 낮다(연결 배선) — 다만 **LDBEAT M2의 저장 키 결정이 아직 확정되지 않았다면, 이 마일스톤은 그 결정이 확정될 때까지 대기한다**(§B 위험 1).

- `SPEC-LDBEAT-001` M2가 확정한 저장 키(권고: `timeline` 사전의 새 키)에 이 SPEC의 초안을 "편집 가능한 초안" 상태로 심는다.
- 격자 화면이 이 초안을 렌더할 때 콘솔에 아무것도 쓰지 않는지 재확인한다(REQ-LDARRANGE-003).

### M6 — LOVE ATTACK 수용 판정 (REQ-LDARRANGE-014)

되돌리기 비용이 가장 낮다(판정일 뿐, 설계 결정이 아니다) — 그러나 **이 SPEC의 유일한 최종 완료 기준**이다.

- LOVE ATTACK에 대해 생성한 자동 초안을 손 배치(배치 규칙서 §4, 또는 run-phase가 §3 전체로 확장)와 나란히 렌더한다.
- 감독 육안 비교를 거쳐 PASS/FAIL을 `progress.md`에 기록한다 — 기계 AC(M1~M5가 검사하는 모든 것)는 이 판정의 사전 체일 뿐, 이 판정을 대체하지 않는다.

## §F 안티패턴

- **마디 지도 스키마가 확정되기 전에 그 필드명에 생성 로직을 못박지 마라** — REQ-LDARRANGE-001. 스텁/추상 경계만 먼저 긋는다.
- **"그룹 멤버십을 모르니 배치를 못 만든다"고 포기하지 마라** — REQ-LDARRANGE-011. RG5 그룹-번호 주소로 우회할 수 있다.
- **배치 규칙 9개의 수치를 전역 상수로 박아 다른 곡에도 적용되게 하지 마라** — REQ-LDARRANGE-004.
- **AI 제안 카드 승인을 칸 단위로 쪼개지 마라** — REQ-LDARRANGE-009. 초안 전체에 1개 단위.
- **"느린 곡" 임계값을 합의 없이 생성기 안에 숫자로 박지 마라** — §5 항목 3. M1에서 감독과 확정한다.
- **배치 규칙서 §2의 역할 6종(SCENE/BACK PULSE/…)을 생성기의 트랙 식별자로 쓰지 마라** — §B 위험 6(카드 t533에서 반전). 이제 LDBEAT·LDARRANGE의 역할 어휘는 `rig.py`의 `RIG_LAYER_ROLES`(key/back/side/wash/mover/effect/audience)와 **같은** 어휘다 — 6종은 교정 전 1차 표기일 뿐이다.
- **이 SPEC의 생성 로직에 콘솔 쓰기 호출을 넣지 마라** — REQ-LDARRANGE-003. 송신은 LDBEAT M4의 몫이다.
- **LDBARMAP·LDBEAT 양쪽이 아직 run-phase에 진입하지 않은 상태에서 이 SPEC의 run-phase를 먼저 밀어붙이지 마라** — §B 위험 1. 재작업 비용이 반복된다.

## §G 교차 참조

- `reports/ldbeat-feasibility-roadmap-20261010.md`(주 체크아웃, 2026-10-10 작성 — 이 SPEC을 예고한 로드맵, SPEC 진행안 3행).
- `reports/effect-arrangement-rules-20261007.md`(규칙 9개·역할 6종 §2·LOVE ATTACK 전체 배치 §3·0~25마디 격자 §4·감독 결정 §5).
- `.moai/reports/t525/verdict.md`(무대 패치 좌표 86/86, 그룹 18개 중 4개 확인·그룹당 앞 2칸).
- `.moai/specs/SPEC-LDBEAT-001/spec.md`·`plan.md`(REQ-LDBEAT-004 역할 어휘, REQ-LDBEAT-006 저장소 미확정, REQ-LDBEAT-011~013 송신 경로 — 이 SPEC이 소비·종속하는 대상).
- `.moai/specs/SPEC-LDRHYTHM-001/spec.md` REQ-LDRHYTHM-012(a)(비트/다운비트 미저장 — 마디 지도 부재의 근거).
- `.moai/specs/SPEC-LDDESIGN-001/spec.md` REQ-LDDESIGN-092,094,095(AI 제안→「적용」 원칙의 출처, 큐 단위 선례).
- `server/design/song_cue_render.py:661,815,890` — RG5 그룹-주소 함수(재사용 대상).
- `server/design/section_palette.py:236-267`, `server/web/session.py:7685-7902` — `palette_mode`(곡별 선택 메커니즘 선례).
- `server/design/rig.py:51-59` — `RIG_LAYER_ROLES`(이 SPEC·LDBEAT가 쓰는 역할 어휘의 출처 — 7종, key/back/side/wash/mover/effect/audience; 카드 t533에서 정정).
- `server/audio/analyze.py:352-390` — 비트 시각 미저장 재확인.
- `console/lua/copilot_responder.lua:43` — `max_prop_value`(그룹 소속 전수 확인을 막는 응답기 한도 — 범위 밖 전제).
