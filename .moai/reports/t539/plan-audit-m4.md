# SPEC-LDBARMAP-001 부분 plan-audit — M4 저장 인터페이스 확정 교정 (카드 t539)

대상 커밋: `0c3bdf0c` (`git show 0c3bdf0c`)
심사 범위(부분, HISTORY 마지막 행 자신이 예고한 범위): REQ-LDBARMAP-010(교체) · AC-LDBARMAP-010(교체) · spec.md §5 열린 결정 0(확정 표기) · Out of Scope — 저장 인터페이스 확정(갱신 주석) · plan.md §B·M4 · acceptance.md DoD 체크리스트 "열린 결정" 행 · 신규 HISTORY 행.
Iteration: 9/부분 (iteration 1~8은 `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-{1..8}.md`; iteration 8은 PASS 0.86이었으나 이번 심사는 그 뒤 새로 들어온 M4 확정 개정에 대한 **신규 부분심사**다 — iteration 8의 결함과는 무관한 범위).

**Verdict: FAIL**
**Overall Score: 0.60** (조화평균, 통과선 0.80 — Tier M)

---

## Must-Pass 결과

- **[PASS] MP-1 REQ 번호 연속성**: REQ-LDBARMAP-001~016, 3자리 zero-padding 일관, 갭·중복 없음(`grep -n "^| REQ-LDBARMAP-" spec.md` → 16행).
- **[PASS] MP-2 EARS/GEARS 표기 준수 (요구사항 계층만)**: REQ-LDBARMAP-010 신규 문면 — "**The** 마디 지도 산출물 **shall** ... 임베드되어 저장된다 ..." — 단일 모달(`shall`만), Ubiquitous 패턴과 정확히 일치. 이 판정은 `REQ-XXX`(spec.md) 계층에만 적용했다 — AC-LDBARMAP-010(acceptance.md의 검증 계층, Given-When-Then)에는 GEARS 패턴 검사를 적용하지 않았다(M3 § Scope).
- **[PASS] MP-3 YAML frontmatter 유효성**: 12개 필수 필드(id/title/version/status/created/updated/author/priority/phase/module/lifecycle/tags) + 선택 필드 `tier: M` 모두 존재, 타입 정상, `version: "0.1.5"`(quoted semver), snake_case alias 없음(spec.md:1-16).
- **[N/A] MP-4 §22 언어 중립성**: 이 SPEC은 단일 언어(Python) 범위 프로젝트 — 자동 PASS.
- **[PASS] MP-5 D7 교차-SPEC 정합성**: 본문에서 인용된 SPEC은 `SPEC-LDARRANGE-001`(status: draft)·`SPEC-LDBEAT-001`(status: in-progress)·`SPEC-LDRHYTHM-001`(status: in-progress) 셋뿐이다(`grep -Eo 'SPEC-...' spec.md/plan.md/acceptance.md` 실측). 셋 다 retired/superseded/archived가 아니므로 BLOCKING 없음.
- **[N/A] MP-6 D8 크로스플랫폼 규율**: `grep -n "syscall" spec.md plan.md acceptance.md` → 0건. "syscall" 문자열 자체가 없어 D8은 자동 PASS(D8-4).
- **[N/A] MP-7 [NEEDS CLARIFICATION] 게이트**: `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` → 매치 0건(exit 1). research.md는 존재하지만 마커가 없어 N/A가 아니라 사실상 PASS로 읽을 수 있으나, 마커 자체가 아예 없으므로 안전하게 PASS로 기록한다.

Must-Pass 7개는 모두 PASS/N/A다 — **그럼에도 FAIL인 이유는 집계 점수가 통과선(0.80) 미달이기 때문이다** (아래 Category Scores + Defects 참조).

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | "Multiple requirements require interpretation. A reasonable engineer might implement them differently." | D5(4곳)가 현재 시점에도 "저장 인터페이스가 아직 열려 있다"고 단정하는 활성 서술을 남겨, 독자가 이 문서의 현재 상태(확정 vs 미확정)를 일관되게 해석할 수 없다 — spec.md:35, spec.md:160, plan.md:70, plan.md:79 |
| Completeness | 0.75 | "One non-critical section missing or sparse; frontmatter complete." | §5 확정 모양에 두 신규 필드(schema_version·first_beat_offset)를 추가했지만, `first_beat_offset`의 "비(非)4/4" 단위 정의가 비어 있다(D1) — 섹션 자체는 존재하나 핵심 내용이 sparse |
| Testability | 0.50 | "Several ACs contain weasel words or require judgment calls to evaluate." | AC-LDBARMAP-010 조건 2 "그 모듈의 재로드 경로를 재호출"이 구체적 함수/커맨드를 지정하지 않아 판정자마다 다르게 해석할 수 있다(D4) + 조건 5(일반화 검증)가 first_beat_offset의 비-4/4 단위 정의 부재(D1)로 인해 기계적으로 판정 불가능하다 |
| Traceability | 0.75 | "One AC references a REQ that exists but the mapping is indirect." | AC-LDBARMAP-010 헤더가 `(REQ-LDBARMAP-010, REQ-LDBARMAP-011)`을 인용하지만, 재작성된 Given-When-Then 본문은 REQ-011의 `shall` 절(§5가 `SPEC-LDBEAT-001` REQ-LDBEAT-006을 옵션으로 인용하고 `SPEC-LDARRANGE-001`을 소비자로 명시해야 한다는 요구)을 전혀 검증하지 않는다(D3) |

**조화평균** = 4 / (1/0.50 + 1/0.75 + 1/0.50 + 1/0.75) = 4 / 6.667 ≈ **0.60** → 통과선 0.80 미달 → **FAIL**.

---

## Defects Found (구조화 결함 목록)

**D1.** critical-generality-contradiction — `spec.md:157`(및 `:144`, HISTORY `:31`) vs `spec.md:159` — `first_beat_offset`이 "`beat_times` 인덱스 **mod 4**, 범위 **0~3**"으로 고정 정의되어, 바로 다음 문단(같은 커밋이 신설한 "일반화 규칙")이 선언하는 "임의의 박자표(분자 1~16)" 원칙과 정면으로 충돌한다. 분자가 3인 곡(3/4박자)이라면 첫 박 오프셋은 mod 3·범위 0~2여야 하는데, 현재 정의로는 그 곡에도 mod 4·범위 0~3을 강제한다. 이 결함은 AC-LDBARMAP-010 조건 5(일반화 검증, `acceptance.md:125`)가 요구하는 "3/4박자 픽스처"에 대해 `first_beat_offset`의 유효 범위를 정의 불능으로 만들어 그 조건 자체를 기계적으로 판정 불가능하게 만든다.
Severity: **critical** — Class: **blocking**
Required fix: `first_beat_offset`을 "`beat_times` 인덱스를 그 마디의 박자표 분자로 나눈 나머지, 범위 0~(분자−1)"로 일반화하거나, REQ-LDBARMAP-016(현재 LOVE ATTACK 4/4 전용으로 작성됨)과의 관계를 명시적으로 분리(이 REQ는 4/4 전용 M2 범위, M4의 일반화 스키마는 그 값을 분자로 재해석)하는 주석을 추가한다. AC-LDBARMAP-010 조건 5에 3/4 픽스처의 기대 `first_beat_offset` 범위(0~2)를 명시한다.

**D2.** major-generality-contradiction — `spec.md:153` vs `spec.md:159` — `events[].start_beat`가 "1-base(**1~4**)"로 고정 정의되어 있는데, 같은 §5 항목 0 안에서 이번 커밋이 신설한 일반화 규칙은 "`start_beat`는 1~분자"라고 선언한다. 두 문장이 같은 필드에 대해 서로 다른 범위를 서술한다.
Severity: **major** — Class: **blocking**
Required fix: `spec.md:153`의 "1-base(1~4)"를 "1-base(1~분자)"로 고쳐 일반화 규칙과 통일한다.

**D3.** major-traceability-gap — `acceptance.md:115-125` — AC-LDBARMAP-010의 헤더는 `(REQ-LDBARMAP-010, REQ-LDBARMAP-011)`을 인용하지만, 재작성된 Given-When-Then 본문(왕복·영속화·되돌리기·거부·일반화 5개 조건)은 REQ-LDBARMAP-011의 `shall` 절(§5가 `SPEC-LDBEAT-001` REQ-LDBEAT-006을 첫 옵션으로 인용하고 `SPEC-LDARRANGE-001`을 장래 소비자로 명시해야 한다)을 전혀 검증하지 않는다. 교체 전 AC-LDBARMAP-010(구 문면)은 정확히 이 인용 요구("옵션 A로 인용되어 있고, 옵션이 2개 이상 제시되며...")를 검증했었다 — 이번 재작성이 그 검증을 삭제하면서 대체물을 두지 않았다.
Severity: **major** — Class: **blocking**
Required fix: AC-LDBARMAP-010 헤더에서 REQ-LDBARMAP-011을 제거하거나(이미 AC-LDBARMAP-011이 그 요구의 일부를 다룬다면), §5의 인용 내용(LDBEAT REQ-006 인용 + LDARRANGE 소비자 명시)을 검증하는 6번째 AND 조건을 추가한다.

**D4.** major-testability-ambiguity — `acceptance.md:122` — AC-LDBARMAP-010 조건 2("영속화")가 "`SongTimelineStore`가 프로세스를 **재시작(또는 그 모듈의 재로드 경로를 재호출)**한 뒤에도"라고 적어, 정확히 어떤 커맨드/함수를 호출해야 이 조건을 만족하는지 지정하지 않는다. 이 SPEC의 다른 AC들(예: AC-LDBARMAP-009의 `grep -rln "downbeat" server`, AC-LDBARMAP-011의 `ls .moai/specs/ | grep -i ARRANGE`)은 정확한 커맨드를 명시하는 반면, 이 조건만 "그 모듈의 재로드 경로"라는 미지정 표현을 쓴다.
Severity: **major** — Class: **blocking**
Required fix: 구체적 검증 동사를 지정한다(예: "`server/web/session.py`의 세션 재생성 경로를 호출하거나 프로세스를 재기동해, 재기동 전/후 `timeline["bar_map"]` 값을 비교한다" 등 M4 구현이 실제로 제공할 재로드 함수명을 M4 산출물과 함께 확정해 이 조건에 cross-reference).

**D5.** major-stale-contradiction (4곳) — 이번 커밋이 건드리지 않은 "나머지" 본문에, 현재도 "저장 인터페이스가 아직 열려 있다/확정되지 않았다"고 단정하는 활성(비-HISTORY) 서술이 4곳 남아 REQ-LDBARMAP-010/§5 열린 결정 0의 새 "확정" 상태와 직접 충돌한다:
  - `spec.md:35`(§0 Tier 선택 근거): "저장 인터페이스는 §5 열린 결정으로 **이 SPEC이 확정하지 않으므로** Tier L급 아키텍처 결정 분량은 아니다" — Tier M 판단의 근거 중 하나가 이제 사실이 아니다.
  - `spec.md:160`(§5 항목 1): "두 SPEC이 같은 **저장 위치**(열린 결정 0의 옵션 A/B)를 공유할지는 **여전히 M2+에서 정한다**."
  - `plan.md:70`(§D 기술적 접근): "M2의 신규 모듈은 `AnalysisResult`를 확장하지 않는다 — **REQ-LDBARMAP-010이 저장 형태를 정하지 않으므로**..."
  - `plan.md:79`(§E 위험 표): "저장 인터페이스를 이 plan-phase가 섣불리 확정 | REQ-LDBARMAP-010 — **열린 결정으로 명시 보존, M2+에서 확정**"
Severity: **major** — Class: **blocking**
Required fix: 네 곳 모두에 이 SPEC의 다른 곳(예: Out of Scope — 저장 인터페이스 확정 섹션, DoD 체크리스트)이 이미 쓰고 있는 "**갱신(카드 t539, M4, 2026-10-10)**: ... 더 이상 유효하지 않다" 패턴의 주석을 추가하거나, 서술 자체를 확정 상태에 맞게 고친다. 특히 `spec.md:35`의 Tier M 근거는 재검토가 필요하다 — "저장 인터페이스 미확정"이 더 이상 근거가 될 수 없으므로, REQ/AC 16개 상한 도달이라는 다른 근거만으로 Tier M을 유지할 수 있는지 명시해야 한다.

**D6.** minor-RQ4-style (참고) — `spec.md`의 REQ-LDBARMAP-010 신규 문면이 구체적 프로덕션 클래스명(`SongTimelineStore`·`TimelineDraftHistory`·`SongTimelineLibrary`)과 리터럴 딕셔너리 키(`timeline["bar_map"]`)를 `shall` 절 안에 직접 명시한다 — RQ-3/RQ-4(요구사항은 WHAT/WHY, HOW 아님) 관점에서는 구현 세부사항이다. 다만 같은 스타일이 이미 REQ-LDBARMAP-011에 있고 8회의 이전 plan-audit iteration을 통과했으므로, 이번에 새로 들여온 결함이 아니라 기존에 용인된 패턴의 연장이다.
Severity: minor — Class: **optional** (이미 검토·용인된 스타일의 재사용 — 신규 결함 아님)
Required fix: 없음(정보성 기록).

**D7.** minor-out-of-scope-note (참고, 채점에는 포함하지 않음) — `acceptance.md`의 AC-LDBARMAP-011("LDARRANGE-001 부재 확인")은 "`SPEC-LDARRANGE-001`은 아직 존재하지 않는다"고 단정하지만, 같은 `spec.md` §5 항목 1(이번 커밋 범위 밖)은 "`SPEC-LDARRANGE-001`, PR #570 머지"라고 적어 이미 존재한다고 말한다. 이 모순은 t539 커밋 이전부터 있던 것이고 사용자 지시("Do not re-audit the rest of the SPEC")에 따라 이번 심사의 점수에는 포함하지 않지만, D3(REQ-011 추적성 공백)을 보완하는 후속 교정 때 함께 다루는 것이 효율적이다.
Severity: minor — Class: **optional** (범위 밖, 채점 미반영)
Required fix: 별도 카드로 후속 처리 권고.

---

## Regression Check

해당 없음 — 이번 부분심사는 iteration 8(PASS 0.86, REQ-LDBARMAP-004 "네 지표" 표현 교정)과 **무관한 새 범위**(M4 저장 인터페이스 확정)를 심사한다. iteration 8의 D8(advisory)은 이미 RESOLVED로 확인됐고 이번 교정이 그 범위를 다시 건드리지 않았다.

---

## Recommendation (FAIL — manager-spec에 대한 구체적 교정 지시)

1. **D1 먼저 고친다** — `first_beat_offset`의 단위를 "mod 분자, 범위 0~(분자−1)"로 일반화하거나 REQ-LDBARMAP-016과의 관계(4/4 전용 M2 vs 일반화된 M4 스키마)를 명시한다. AC-LDBARMAP-010 조건 5에 3/4 픽스처의 기대 오프셋 범위를 추가한다. (`spec.md:144,157,159`, `plan.md:144`, `acceptance.md:125`)
2. **D2** — `spec.md:153`의 `start_beat` 정의를 "1~분자"로 통일한다.
3. **D3** — AC-LDBARMAP-010이 REQ-LDBARMAP-011을 실제로 검증하도록 6번째 AND 조건을 추가하거나, 헤더에서 REQ-011 인용을 제거한다.
4. **D4** — AC-LDBARMAP-010 조건 2의 "재로드 경로"를 구체적 커맨드/함수로 명시한다.
5. **D5** — `spec.md:35`, `spec.md:160`, `plan.md:70`, `plan.md:79` 네 곳에 "갱신(카드 t539, M4)" 주석을 추가하거나 서술을 확정 상태로 고친다. 특히 `spec.md:35`의 Tier 근거 재검토.
6. 교정 뒤 REQ-LDBARMAP-010/AC-LDBARMAP-010/§5만 다루는 2차 부분심사(iteration 10)를 재실행한다.
