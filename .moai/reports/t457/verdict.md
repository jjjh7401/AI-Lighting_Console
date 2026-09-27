# t457 판정서 — 근거 등급 생산자 배선 (REQ-LDDESIGN-022/071)

- 카드: t457 (클래스 C) · SPEC-LDDESIGN-001
- 브랜치: `WT-evidence-grades`, 기준 `origin/main` ab1c12f9
- 콘솔 쓰기: 0
- 리드 승인: 2026-09-27. 원칙은 「조문이 직접 받치는 곳만, 애매하면 null」이다. 감독 착수 승인을 받았다.

## 1. 주장

`concept_report.rows[].evidence` 에 행마다 근거 등급을 싣는다. 착수 전에는 생산자가 0곳이라 전 행이
`null` 이었다(`session_bridge._concept_rows` 의 `"evidence": None`). 이제 순수 함수
`server/concept/evidence.py` `evidence_for_row(kind, section, trigger, occurrence)` 가 아래 표대로 매기고,
값은 `cue_model.validate_evidence` 로 검증한다. 행 키 11개와 payload 키는 바뀌지 않았다.

### 1.1 배정 표 (조문 인용)

등급 정의 — **REQ-022**: 「`verified`(정본·실측 페이드 규칙 등), `practitioner_pattern`(회차 확장·빌드업 등
실무 관행), `designed_rule`(이 SPEC이 새로 구성한 규칙), `director`(구간 판정기 출력을 그대로 옮긴 경우)」.
**REQ-071**: 「`verified`는 정본이 실측한 페이드·안전 규칙에만 붙이고, 이 곡에서 직접 검증했다는 뜻이 아님」.

| 큐(행) | 생산 규칙 | 등급 | 받치는 조문 |
|---|---|---|---|
| safety 첫 큐 block | REQ-068 | `verified` | REQ-071 「정본이 실측한 … 안전 규칙」, `EVIDENCE_FOR_SAFETY` |
| safety 끝 큐 release | REQ-069 | `verified` | 같음 |
| section Chorus 2회차~ | REQ-042~044 | `practitioner_pattern` | REQ-022 「회차 확장」 |
| section Final Chorus | REQ-048 | `practitioner_pattern` | REQ-022 「회차 확장」 |
| phrase 「빌드업 시작」 | REQ-037 | `practitioner_pattern` | REQ-022 「빌드업」 |
| phrase 「악기 추가」 | REQ-045 | `practitioner_pattern` | REQ-043 회차 확장 축 「큐 밀도(그 후렴 안의 프레이즈 큐 수)」 |
| phrase 「드롭 직전의 정적」 | REQ-038 | `designed_rule` | REQ-022 「이 SPEC이 새로 구성한 규칙」 — REQ-038 은 이 SPEC 의 규칙 |
| section Pre-Chorus·Post-Chorus·Rap/Solo/Dance Break (retain) | `density.compile_density` else 분기 | `director` | REQ-022 「구간 판정기 출력을 그대로 옮긴 경우」 |
| section Chorus 1회차 | density k==1 | null | 확장 전 기준 상태라 「회차 확장」이 받치지 않는다 |
| section Bridge | REQ-046 | null | 근거가 SPEC 조문이 아니라 보고서(`chorus-escalation-audit`) |
| section Intro·Verse·Outro | 프로토타입 이식 값 | null | 등급을 정한 조문 없음 |
| phrase 「보컬 시작」 | 프로토타입 이식 | null | 등급을 정한 조문 없음 |
| 원샷 | REQ-040 | (행 아님) | REQ-040 「evidence … 계산 대상에서 제외」 |

## 2. 증거

### 2.1 8곡 등급 분포 — `grades_8songs.txt`

`_concept_rows(build_song(song), …)` 로 8곡(`fixtures/pilot_baseline.json`) 전 행을 셌다.

- 등급 분포: `practitioner_pattern` 135 · `verified` 16 · `designed_rule` 5 · null 72 (합 228행)
- 행 종류별: safety Intro/Outro 8+8 → verified. Chorus 41 → practitioner, Chorus 8(각 곡 1회차) → null.
  Final Chorus 6, 빌드업 16, 악기 추가 72 → practitioner. 드롭 직전 정적 5 → designed_rule.
  Bridge 9·Intro 8·Outro 8·Verse 31·보컬 시작 8 → null.
- `director` 는 8곡에 0행이다(판정기 이름 retain 구간이 이 표본에 없다). 단위 시험으로만 확인했다.
- 게이트 합계는 PASS 75 / n·a 29 / FAIL 0 으로 불변이다(evidence 는 게이트 입력이 아니다).

### 2.2 시험

- 신규 `server/tests/test_concept_evidence_grades_t457.py`: 27 passed. 단위 18건(표 각 칸)과 8곡 통합 9건
  (행 키 11개 불변, 값 ∈ 4등급 ∪ {None}, 첫·끝 safety verified, 등급 행 > 0)이다.
- 대조군: 함수만 넣고 `_concept_rows` 배선 전에 돌리면 **9 failed, 18 passed** 다
  (`red_before_wiring.txt` — 통합 9건이 실패). 배선 후에는 27 passed.
- 바뀐 기존 시험: `test_runbook_payload_t455_t456.py` `test_evidence_is_null_everywhere` 는 t455 가
  「생산자는 t457」이라며 둔 자리표시였다. `test_evidence_follows_the_approved_grade_table` 로 바꿨다
  (행마다 `evidence_for_row` 와 같음, 첫·끝 verified, null 행 존재).
- `uv run pytest -q server/tests -k "concept or gate or evidence or timeline or songcue or runbook or report or bridge"` → 2502 passed, 24 skipped
- `uv run ruff check server` → All checks passed · `ruff format --check` 통과
- `npm --prefix ui test -- --run` → 602 passed (26 files). UI 는 아직 `rows[].evidence` 를 읽지 않는다(`grep -rln evidence ui/src` → DashBoard.tsx 주석 1곳뿐).

## 3. 범위 밖

- REQ-072 「[공개 근거 없음]」 표시와 REQ-071 설명 문구의 화면 노출은 UI 몫이라 lane-3 t458 에 넘겼다(리드 결정). payload 는 null 을 그대로 둔다.
- 페이드(`EVIDENCE_FOR_FADE`)·MIB 초(`EVIDENCE_FOR_MIB_TIMING`) 등급은 행이 아니라 필드 단위라 이번 rows 배선 대상이 아니다.

## 4. 미검증

- `director` 등급은 8곡 표본에 해당 행이 없어 단위 시험으로만 확인했다. 판정기가 Pre-Chorus 등을 직접 내는 실제 곡으로는 태우지 않았다.
- 「악기 추가」 외의 프레이즈 트리거(「악기 제거」·「보컬 종료」 등, 어휘에는 있으나 compile_density 가 현재 만들지 않는 것)는 null 로 떨어진다. 생산자가 생기면 표를 다시 봐야 한다.

## 5. 판정

PASS (리드 확인 대기). 승인 표대로 배선했고, 값은 validate_evidence 를 통과한다. 행·payload 키는 불변이고
8곡 게이트 기준선도 불변이다.
