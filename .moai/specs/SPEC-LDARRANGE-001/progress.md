# SPEC-LDARRANGE-001 — Progress

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-10
- 작성 카드: t528. 입력 출처는 `spec.md` HISTORY·`plan.md` §A/§G 참조.
- Tier: M (spec.md §0 근거) — REQ 14개·AC 16개, Tier M 상한(각 16개) 이내.
- 플랜-오딧 전 자체 점검: SPEC ID 정규식 PASS(Bash 실행 — `[[ "SPEC-LDARRANGE-001" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS` → `PASS`), 프런트매터 12필드 schema 대조 완료, 기존 SPEC ID와 충돌 없음(`ls .moai/specs/` 확인 — `SPEC-LDARRANGE-001` 디렉터리 생성 전 부재 확인), Out of Scope 섹션 5개 H3 하위헤딩 + `-` 불릿 포함.
- **전제 SPEC 의존 상태(이 plan-phase 시점)**: `SPEC-LDBEAT-001` status: draft(M1~M6 전부 미착수), `SPEC-LDBARMAP-001` 디렉터리 없음(카드 t527 병행 작성 중) — 이 SPEC의 run-phase는 두 SPEC 모두 run-phase 진입 후 착수 권고(plan.md §B 위험 1).
- 열린 결정 4건(spec.md §5) — Implementation Kickoff Approval 라운드에서 항목 1(마디 지도 인터페이스)·항목 3("느린 곡" 기준)을 명시적으로 확인받아야 한다.
- **plan-audit (리포트는 `.moai/reports/plan-audit/` — gitignore 대상이라 결과를 여기 옮긴다)**:
  - iter1 `SPEC-LDARRANGE-001-review-1.md` — PASS 0.80 (Clarity 0.75 · Completeness 1.0 · Testability 0.75 · Traceability 0.75). 결함 D1~D7, 치명 0.
  - iter2 `SPEC-LDARRANGE-001-review-2.md` — **PASS 0.86** (Traceability 0.75→1.0, 회귀 없음). D1·D3·D6 해소 확인(독립 재검증). 새 결함 D8(spec.md:30·progress.md:8 「AC 14개」 잔존)·D9(묶음 REQ 7→9개 재계수) — 둘 다 숫자 정정으로 반영(이 커밋). D2·D4·D5·D7 은 설계상 유지.

## 인터페이스 맞춤 (카드 t529, 2026-10-10)

- 바뀐 곳: `spec.md` frontmatter(`depends_on`·`related_specs`에 SPEC-LDBARMAP-001), §5 항목 1 + §2 항목 1(권고 모양 추가), HISTORY 1행, version 0.1.1→0.1.2. **REQ 표·`acceptance.md`·`plan.md`는 한 글자도 안 바꿨다.**
- plan-audit 재실행 안 함 — 사유: 추가한 것은 §5 열린 결정 안의 **권고**(확정 아님)뿐이고, 저장 형태 확정 금지(REQ-LDBARMAP-010)·마디 지도 없이는 생성 로직 미구현(REQ-LDARRANGE-001)·STROBE는 임팩트 마디에만(REQ-LDARRANGE-008) 같은 구속의 뜻은 그대로다. 권고 모양은 그 구속들이 이미 요구하는 것(마디 단위, REQ-LDBARMAP-007의 단위 명시, REQ-LDBARMAP-008의 사건 4종)에 이름을 붙인 것이다.
- 마디 번호 공간 실측(t529): 지도 보고서 §2 "마디 번호는 위상 1 기준이다. 1마디 = 1.50초. 0.96초의 첫 박은 못갖춘마디" · 같은 보고서 18마디 = "후렴 1 진입 — 큰 히트" · 배치 규칙서 §3 18~21행 = "코러스 1 앞", §4 첫 행 = "0~2" — 두 문서가 같은 번호 공간을 쓰고 0은 못갖춘마디다.
- ③ 저장 키 맞춤(t529 후속, 2026-10-10): §5 열린 결정에 세 SPEC 공통 권고 키 `timeline["beat_grid"]`/`["bar_map"]`/`["arrangement_draft"]` 추가. 권고뿐 — REQ·AC·plan.md·acceptance.md 변경 0, plan-audit 재실행 없음.

## 역할 어휘 맞춤 (카드 t533, 2026-10-10)

- **배경**: `SPEC-LDBEAT-001` v0.2.0(PR #572, 카드 t526)이 REQ-LDBEAT-004 트랙 모양을 "콘솔 그룹 트랙(줄 하나 = 콘솔 그룹 하나 = 시퀀스 하나) + `rig.py`의 7개 층 역할 이름표 key/back/side/wash/mover/effect/audience"로 재교정하면서, 이 SPEC이 인용하던 역할 6종(SCENE/BACK PULSE/SIDE CHASE/MOVER-U MOVE/MOVER-D MOVE/ACCENT) 어휘가 LDBEAT 쪽에서 철회됐다 — 바로 위 HISTORY 행(카드 t529 ③)이 "이 카드 범위 밖, 리드 보고"로 적어 둔 알려진 미해결을 이 카드가 해소한다.
- **바뀐 REQ**: `REQ-LDARRANGE-002`(생성기가 쓸 트랙 모양·역할 어휘를 LDBEAT와 맞추고, 배치 규칙서 §2의 역할 6종을 트랙 식별자로 금지, 겹치는 그룹 트랙 동시 사용 금지를 흡수) · `REQ-LDARRANGE-007`(STROBE 게이팅을 "ACCENT 트랙"이 아니라 트랙 비종속으로 재서술 — 게이팅의 뜻 자체는 불변).
- **바뀐 AC**: `AC-LDARRANGE-003` · `AC-LDARRANGE-004`(둘 다 "ACCENT 트랙" 참조를 "모든 콘솔 그룹 트랙" + "STROBE 내용"으로 교체, 기계 검증 뜻 불변) · `AC-LDARRANGE-014`(라벨 집합 검증을 "LDBEAT 6종과 정확히 일치"에서 "7종의 부분집합 + 트랙 식별자에 6종 미사용"으로 재정의). AC 총수 16 불변, REQ 총수 14 불변.
- **바뀐 plan.md**: §B 위험 6(역할 어휘 분류축 안내를 반전 — 이제 LDBEAT·LDARRANGE와 `rig.py`는 같은 어휘다) · §C 사전 점검 grep(LDBEAT의 6종 문자열 그렙을 7종 어휘/`RIG_LAYER_ROLES` 그렙으로 교체) · §E M3(그룹 매핑 입력을 7종 트랙으로 교정) · §F 안티패턴(반전) · §G 교차 참조(`rig.py:51-59` 인용 정정).
- **바뀐 spec.md**: §1 배경 문단 2곳(단위 표현 교정 + "콘솔 그룹별 배치" 읽기 추가) · §2 끝에 "단위 정정" 문단 신설(이 문서 전체의 "역할×마디" 표현을 "콘솔 그룹 트랙 × 마디"로 재정의) · HISTORY 신규 행 · version 0.1.3→0.2.0.
- **plan-audit 재실행 필요**: REQ·AC가 구속하는 뜻(생성기의 새 역할 발명 금지·STROBE 게이팅 조건·그룹 번호 주소만 사용) 자체는 바뀌지 않았으나, 그 뜻을 표현하는 **인용 어휘**(어느 어휘가 "정본"이고 어느 것이 "교정 전 1차 표기"인지)가 바뀌었다 — 직전 카드(t529 ③)는 "뜻이 같으므로 재실행 없음"으로 판단했지만, 이번 변경은 REQ-LDARRANGE-002·007·acceptance.md AC-014의 검증 **대상 집합**(허용 라벨 집합·금지 라벨 집합) 자체를 교체했으므로 같은 논리가 적용되지 않는다. 다음 run-phase 착수 전 plan-auditor를 다시 돌려야 한다(`.moai/reports/plan-audit/SPEC-LDARRANGE-001-review-3.md` 또는 다음 가용 iteration 번호).
- plan-audit iteration 3/3 (`.moai/reports/plan-audit/SPEC-LDARRANGE-001-review-3.md`, gitignore — 결과를 여기 옮긴다): **PASS 0.81** (Clarity 0.75 · Completeness 1.0 · Testability 0.75 · Traceability 0.75), must-pass 7/7. iter2(0.86) 대비 하락 → STOP 신호 + 3회 상한 도달. 하락 원인 D1(차단): t533 이 REQ-002 에 흡수한 "겹치는 그룹 트랙 금지"를 검증하는 AC 가 0건(`grep -c 겹치 acceptance.md plan.md` → 0/0, 오케스트레이터 재확인). **델타 교정**: AC-LDARRANGE-014 에 겹침 카운트 == 0 검사를 추가(AC 수 16 그대로, §A.1 추적표 REQ-002→AC-014 기존 행이 덮음). 4회차 감사는 상한 초과라 돌리지 않았다 — 교정은 D1 처방 그대로의 한 절 추가. 나머지 두 소견(REQ-002 다중 shall not 묶음 — iter1 D2 와 같은 Tier M 상한 우선 결정, 7종 어휘 인용 순서)은 선택 사항이라 반영 안 함.

## 마디 지도 입력 모양 맞춤 (카드 t541, 2026-10-10)

- **주장**: §5 항목 1의 미러 문단이 생산자 `SPEC-LDBARMAP-001` M4 확정 모양(PR #585 `364ab000`)과 같은 문면이다. spec.md v0.2.0→0.2.1. REQ·AC 문면 변경 0(REQ-LDARRANGE-001의 구속 — 실제 지도 **데이터** 없이 생성하지 않음 — 그대로 유효: 서버 저장 배선은 있으나 오디오→`timeline["bar_map"]` 진입 경로가 아직 없다).
- **바뀐 곳**: §5 항목 1 머리·본문(「생산자 쪽 확정, 소비 방식만 열림」), 입력 모양 문단(`schema_version`·`first_beat_offset` 추가, `time_signature` `[분자, 분모]` 일반형, `start_beat` 1~분자, 일반화 규칙 승계), §2 입력 1, §1 만료 고지, HISTORY.
- **증거**: 생산자 쪽 AC-LDBARMAP-011 검사 3(두 SPEC §5 범위에서 확정 필드 8개 각각 ≥1줄) — 이 트리 LDARRANGE `1 1 1 1 1 2 1 3`(8개 모두 ≥1). 대조: 교정 전(origin/main `ef854b0a`) 이 SPEC §5 에서 `schema_version`/`first_beat_offset` → `0` — 검사 3이 갈라짐을 잡는다.
- **감사**: 부분 plan-audit(LDBARMAP 쪽과 한 묶음) 1차 FAIL 0.80 → 2차 FAIL → 3차 **PASS 1.00** — `.moai/reports/t541/plan-audit.md`.
- **미검증·남은 것**: 이 SPEC 자신의 REQ-LDARRANGE-001·AC-LDARRANGE-015·plan.md:6·:46 의 「LDBARMAP 존재하지 않음」 문면은 t529 HISTORY 일괄 만료 고지에 맡기고 고치지 않았다(카드 범위 밖) — 다음 개정 때 인라인 고지 후보.

## 낡은 문면 인라인 고지 (카드 t545, 2026-10-10)

- **주장**: 「SPEC-LDBARMAP-001 존재하지 않음/미작성」을 현재형으로 단언하던 본문 6곳(spec.md §0·REQ-LDARRANGE-001 괄호와 근거 칸, plan.md §A·§D·M1, acceptance.md AC-LDARRANGE-015)에 제자리 고지를 붙였다. 뜻은 바꾸지 않았다. spec.md v0.2.1→0.2.2.
- **뜻 불변 근거(이 트리 diff, 바뀐 줄 6→6)**: 지운 줄/더한 줄의 규범 표현 개수 — `**While**` 1→1, `== true` 1→1, `== 0` 2→2, `카운트` 2→2, `| AC-LDARRANGE-015 |` 1→1, `shall not` 1→2(늘어난 1은 근거 칸의 「`shall not`은 그대로 유효」 인용 — 새 의무 아님). 그래서 plan-audit 미실행(리드 지시: 뜻이 바뀔 때만).
- **잔여 문면 검사**: LDBARMAP 를 담은 줄에서 부재 표현 앞 140자·뒤 60자 안에 고지 표지가 없는 경우(HISTORY 제외) — 고치기 전 10건(8줄 — spec.md:34·70×2·150, plan.md:6·46·54, acceptance.md:23×2·52) → 지금 3건(이 트리 재실행, 「작성 시점에는」·「현황」도 고지 표지로 셈). 남은 3건은 일부러 둠: spec.md:150(§5 항목 3(c), run-phase 시점에 **데이터**가 없을 가능성 — 참), acceptance.md:23 Given 칸·:52(스텁 상태 시나리오 — 시험 조건이지 사실 단언 아님).
- **현황 사실**: 선행 조건(존재 PR #571, 스키마 확정 PR #585 `364ab000`) 충족 · 실제 지도 데이터 진입 경로(오디오→`timeline["bar_map"]`)는 아직 없음 → REQ-LDARRANGE-001 `shall not` 유효.
- **미검증**: 독립 감사 없음(뜻 불변 판단은 레인이 규범 표현 개수로 잰 것).

## §E.2 Run-phase Evidence

_<run-phase 대기 — manager-develop 착수 전까지 비어 있음>_

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
