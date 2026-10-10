# 부분 Plan-Audit 보고서 — 카드 t541 (커밋 `00fb1a55`)

범위: `git show HEAD`(`00fb1a55`)가 건드린 두 SPEC의 변경분만. `SPEC-LDBARMAP-001`의 표준 iteration 번호 체계(review-N)와는 별도의 1회성 부분 감사다. Reasoning context ignored per M1 Context Isolation — 커밋 메시지와 HISTORY 서술은 "배차자가 무엇을 주장했는가"로만 읽고, 모든 판정은 아래 재실행 결과로 한다.

**Verdict: FAIL**
**Overall Score: 0.80** (Tier M pass line 0.80 — 경계값, "의심되면 FAIL" 원칙 적용)

---

## 1. AC-LDBARMAP-011 재실행 결과 (3개 검사, 저장소 루트 기준)

### 검사 1 — 존재
```bash
$ ls -d .moai/specs/SPEC-LDARRANGE-001
.moai/specs/SPEC-LDARRANGE-001
$ echo exit:$?
exit:0
```
→ **PASS** (디렉터리 1개, exit 0).

### 검사 2 — 소비자 명시
```bash
$ sed -n '/^## 5\./,$p' .moai/specs/SPEC-LDBARMAP-001/spec.md | grep -c 'SPEC-LDARRANGE-001'
5
```
→ **PASS** (5 ≥ 1).

### 검사 3 — 미러 필드 일치 (8개 필드, 양쪽 §5 범위)
```
LDBARMAP §5                      LDARRANGE §5
schema_version      : 2          schema_version      : 1
bpm                  : 1          bpm                  : 1
time_signature       : 1          time_signature       : 1
first_beat_offset    : 2          first_beat_offset    : 1
bars[]               : 1          bars[]               : 1
beats_ms             : 2          beats_ms             : 2
events[]             : 1          events[]             : 1
start_beat           : 3          start_beat           : 3
```
8개 필드 전부 양쪽에서 ≥1줄 → **PASS**.

**비공허성(non-vacuous) 검증**: 커밋 전 상태(`origin/main`)의 LDARRANGE §5에서 같은 필드를 재조회:
```bash
$ git show origin/main:.moai/specs/SPEC-LDARRANGE-001/spec.md > /tmp/old.md
$ sed -n '/^## 5\./,$p' /tmp/old.md > /tmp/old_s5.md
$ grep -c schema_version /tmp/old_s5.md
0
$ grep -c first_beat_offset /tmp/old_s5.md
0
```
교정 전에는 `schema_version`·`first_beat_offset` 둘 다 LDARRANGE §5에 0줄이었다 — 즉 교정 전 상태로 검사 3을 돌렸다면 "한쪽에만 있는 필드"가 2개여서 **FAIL**했을 것이다. 검사 3은 **비공허**(생산자·소비자 문단이 실제로 갈라지면 FAIL한다)로 확인됨 — 커밋 메시지가 암시한 "`git show origin/main:.../spec.md`는 §5에서 schema_version/first_beat_offset 0줄" 주장도 그대로 재현됨.

**검사 3의 절차적 결함(경미)**: 검사 1·2는 리터럴 셸 명령이 AC 본문에 명시되어 있는 반면, 검사 3은 "필드 이름 8개가 모두 1줄 이상 나온다"는 서술만 있고 실행 가능한 단일 명령이 없다 — 어떤 섹션 절단 방식·어떤 매칭 규칙(단어 경계 vs 부분 문자열)을 쓸지가 검사자의 재량에 맡겨져 있다. 위에서 재구성한 `sed + grep -c` 조합은 합리적인 해석으로 PASS·비공허성 둘 다 재현했지만, 이 AC 자체는 "기계로 그대로 실행 가능"이라는 체크리스트 RQ-6/AC-2 기준을 검사 1·2보다 느슨하게 만족한다.

---

## 2. LDARRANGE 미러 문단 vs LDBARMAP §5 확정 모양 — 필드/범위/단위 대조

| 항목 | LDBARMAP §5 (생산자, 확정) | LDARRANGE §5 항목 1 (소비자, 미러) | 일치 여부 |
|---|---|---|---|
| `schema_version` | 정수, `=1` | 정수, 고정값 `1` | 일치 |
| `bpm` | 실수, BPM | 실수, BPM | 일치 |
| `time_signature` | `[분자, 분모]`, LOVE ATTACK `[4,4]` (이 커밋에서 `[4,4]` 고정 표기 교정) | `[분자, 분모]` — 분자 1~16, 분모 ∈{1,2,4,8,16}; LOVE ATTACK `[4,4]` | 일치 |
| `first_beat_offset` | 정수, 사람 지정, 단위 박, 범위 0~(분자−1) | 정수, 단위 박, 범위 0~(분자−1) | 일치 |
| `bars[]` | `{bar, start_ms, beats_ms}`, `bar` 1-base+0=못갖춘마디, `start_ms` 정수 ms | `bars[] = {bar, start_ms, beats_ms}`, 같은 1-base+0 규칙, 마디 번호 서술은 spec.md 본문(§5 항목1 하위)에 그대로 승계 | 일치 |
| `events[]` | `{kind, start_bar, end_bar, start_beat, grade}` | 동일 | 일치 |
| `start_beat` | 1~분자(일반화) | 1~분자(이 커밋에서 "1~4"→"1~분자"로 교정) | 일치 |
| 일반화 규칙 | 곡 길이·박자표·못갖춘마디 가정 금지, `bar:0` 못갖춘마디, 마지막 마디 부분 채움 허용 | "곡 길이·박자표·못갖춘마디 유무는 곡마다 다르다... 82마디·4/4를 가정하지 않는다" | 일치 |

**불일치 없음.** 필드 이름·범위·단위·일반화 규칙 모두 두 문서가 같은 문면이다.

---

## 3. REQ/AC 의미·개수 보존 확인

- **REQ-LDBARMAP-011**: `shall` 절의 주어·동사·목적(①`SPEC-LDBEAT-001` REQ-LDBEAT-006을 첫 옵션으로 인용, ②`SPEC-LDARRANGE-001`을 장래 소비자로 명시)은 변경 전/후 동일 — 바뀐 것은 `SPEC-LDARRANGE-001`을 가리키는 **괄호 설명**뿐("아직 존재하지 않음" → "최초 작성 시점에는 없었다 — 같은 날 PR #570으로 생겼다"). 구속 내용 불변 — 확인됨.
- **REQ-LDARRANGE-001**: 이 커밋의 diff에 해당 행(spec.md:70)은 전혀 포함되지 않음(`git diff origin/main HEAD -- spec.md` 확인) — `shall not` 절 그대로, "지도 데이터 없이 생성하지 않음" 구속 불변 — 확인됨.
- **REQ 개수**: `SPEC-LDBARMAP-001` REQ-LDBARMAP-001~016 연속·중복 없음, 16개(`grep -c '^| REQ-LDBARMAP-'` = 16) — 확인됨.
- **AC 개수**: `SPEC-LDBARMAP-001` AC-LDBARMAP-001~016, 16개(`grep -c '^### AC-LDBARMAP-'` = 16) — 확인됨.
- **`SPEC-LDARRANGE-001` REQ/AC**: 이 커밋은 `SPEC-LDARRANGE-001/acceptance.md`를 전혀 건드리지 않았고(diff stat 확인), `spec.md`의 REQ 표도 REQ-LDARRANGE-001~014(14개, `origin/main`과 동일 — 재조회 확인) 그대로. AC 개수는 acceptance.md 비변경이므로 definitionally 불변. — 확인됨, "REQ/AC 변경 0" 주장과 일치.

---

## 4. 잔존 결함 — HISTORY/만료 고지 바깥에서 여전히 "LDARRANGE 부재" 또는 "저장 모양 미정"을 단언하는 줄

전수 grep(`존재하지 않\|아직 없\|미정`, HISTORY 표 바깥) 결과, **1건의 미교정 잔존 결함**을 찾았다:

> **`.moai/specs/SPEC-LDBARMAP-001/spec.md:117`** (`### Out of Scope — 역할×마디 배치 자동 생성` 절, HISTORY 아님, 만료 고지 없음):
> > 마디 지도(이 SPEC의 산출물)를 입력받아 역할별 배치를 자동으로 짜는 것은 `SPEC-LDARRANGE-001`(**아직 존재하지 않음**)의 몫이다 — 이 SPEC은 지도만 만든다.

이 줄은 커밋이 명시적으로 교정한 3개 자리(①LDARRANGE §5 미러 문단, ②AC-LDBARMAP-011, ③REQ-LDBARMAP-011 근거 칸)와 같은 성격의 단언("LDARRANGE 아직 존재하지 않음")을 담고 있지만, 커밋 범위 ①②③ 어디에도 포함되지 않았다. 바로 아래 `### Out of Scope — 저장 인터페이스 확정` 절(spec.md:123)은 같은 종류의 과거 단언에 **"갱신(카드 t539, M4...)" 만료 고지**를 붙여 놓았는데, 117행은 그 패턴을 받지 못했다 — 같은 문서 안에서 같은 범주의 사실 오류가 한 자리는 고쳐지고 다른 자리는 남은 비일관성이다. 현재 사실(§1 확인)은 `SPEC-LDARRANGE-001`이 PR #570으로 이미 존재하므로, 이 문장은 **현재 거짓**이다.

(참고: `SPEC-LDARRANGE-001/spec.md:150`의 "마디 지도가 아직 없어 ... 쓸 수 없을 가능성"은 SPEC 존재 여부가 아니라 **지도 데이터**(타임라인 진입 경로) 부재를 가리키는 문장이며, 이 커밋 자신의 §5 항목1 업데이트(spec.md:56, "실제 곡의 지도 **데이터**가 타임라인에 들어 있는 상태는 아직 아니다")와 일치해 현재도 사실이다 — 결함 아님.)

---

## Must-Pass Results

- [PASS] MP-1 REQ 번호 일관성: `SPEC-LDBARMAP-001` REQ-001~016 연속·중복 없음(spec.md 전수 grep). 이 커밋은 REQ 번호를 바꾸지 않았다.
- [PASS] MP-2 EARS/GEARS 형식: REQ-LDBARMAP-011(`The ... shall ...`)·REQ-LDARRANGE-001(`While ... shall not ...`) 둘 다 변경 전 패턴 그대로(이 커밋은 셀 본문의 서술적 설명만 수정, 모달 절 불변). (검사 대상은 REQ-XXX 요구사항 레이어; AC-LDBARMAP-011의 Given-When-Then은 검증 레이어로 이 기준에서 평가하지 않음 — M3 § Scope.)
- [PASS] MP-3 YAML frontmatter: 두 SPEC 모두 `version` 필드만 갱신(LDARRANGE 0.2.0→0.2.1, LDBARMAP 0.1.5→0.1.6), 12개 필수 필드 구조 불변.
- [N/A] MP-4 언어 중립성: 다국어 툴링 SPEC 아님.
- [N/A] MP-5 D7 교차-SPEC 재조정: 이 커밋이 참조하는 `SPEC-LDBEAT-001`·`SPEC-LDRHYTHM-001`·`SPEC-LDARRANGE-001` 전부 `status: in-progress` 또는 `draft`(grep 확인) — retired/superseded/archived 없음, BLOCKING 없음.
- [N/A] MP-6 D8 크로스플랫폼: `syscall` 언급 없음(두 파일 변경분에 해당 토큰 부재).
- [N/A] MP-7 [NEEDS CLARIFICATION] 게이트: `grep -n 'NEEDS CLARIFICATION' .moai/specs/SPEC-LDBARMAP-001/plan.md .moai/specs/SPEC-LDARRANGE-001/plan.md` → 0건(exit 1). LDARRANGE는 Tier M이라 `research.md` 없음(N/A 전제 충족).

## Category Scores (0.0-1.0, rubric-anchored, 이 diff 범위로 한정)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — 소수 문장에 경미한 모호성 | AC-LDBARMAP-011 검사 3이 실행 명령 없이 서술로만 조건을 기술(acceptance.md:138) — 합리적 해석으로 일관되게 재현 가능하지만 리터럴 명령이 빠져 있다 |
| Completeness | 0.75 | 0.75 — 비핵심 절 1곳 누락/미반영 | spec.md:117(Out of Scope)이 같은 커밋이 고친 다른 3곳과 같은 범주의 "LDARRANGE 부재" 단언을 만료 고지 없이 남김 |
| Testability | 0.75 | 0.75 — 하나의 AC가 정밀하게 이진 판정은 아니나 약간의 해석으로 측정 가능 | 검사 1·2는 완전 이진; 검사 3은 위 Clarity와 같은 사유로 소폭 해석 필요 — 세 조건 모두 AND로 재현 시 PASS, 공허성 없음 확인 |
| Traceability | 1.0 | 1.0 — 모든 REQ가 AC를 가지며 고아 없음 | REQ-LDBARMAP-011 ↔ AC-LDBARMAP-011 추적 유지(acceptance.md:128 헤더 인용); REQ-LDARRANGE-001 커버리지 불변(이 커밋 미접촉) |

조화평균 = 4 / (1/0.75 + 1/0.75 + 1/0.75 + 1/1.0) = **0.80** — Tier M 통과선(0.80)과 정확히 같다. 경계값이며, §4에서 실제 결함(현재 거짓인 미교정 단언)을 구체적 증거로 확인했으므로 "의심되면 FAIL" 원칙에 따라 FAIL로 판정한다.

## Defects Found

D1. `spec-staleness-out-of-scope` — `.moai/specs/SPEC-LDBARMAP-001/spec.md:117` — Out of Scope 절("역할×마디 배치 자동 생성")이 `SPEC-LDARRANGE-001`을 "(아직 존재하지 않음)"으로 단언 — 이 커밋이 §1·§4("저장 인터페이스 확정")·REQ-LDBARMAP-011 근거 칸에 붙인 것과 같은 종류의 만료 고지가 이 줄에는 없고, 현재 사실(LDARRANGE는 PR #570으로 이미 존재)과 모순된다. — Severity: major — Class: blocking — Required fix: `(아직 존재하지 않음)`을 `(최초 작성 시점에는 없었다 — 같은 날 PR #570으로 생겼다, 카드 t541 고지)` 또는 동등한 만료 고지로 교체하고, 바로 아래 §4 "저장 인터페이스 확정" 절의 갱신 패턴과 통일한다. REQ/AC 문면·개수는 건드릴 필요 없음(이 줄은 Out of Scope 서술일 뿐 REQ shall 절이 아님).

D2. `ac-011-condition3-no-literal-command` — `.moai/specs/SPEC-LDBARMAP-001/acceptance.md:138` — AC-LDBARMAP-011의 검사 3("미러 필드 일치")이 검사 1·2(리터럴 `ls -d ...` / `sed ... | grep -c ...` 명령)와 달리 실행 가능한 단일 명령을 제공하지 않고 서술로만 조건을 기술한다. — Severity: minor — Class: optional — Required fix: 검사 1·2와 같은 형식으로, 8개 필드 각각에 대해 `sed -n '/^## 5\./,$p' <file> | grep -c -- '<field>'` 류의 루프 또는 한 줄 명령을 명시해 검사자의 해석 여지를 제거한다(이번 재실행에서 보인 대로 비공허성 자체는 이미 확인됨 — 선택적 개선).

No other defects found within this commit's diff scope.

## Recommendation

1. (필수, D1) `spec.md:117`에 만료 고지를 추가해 "LDARRANGE 부재" 단언을 §1·§4·REQ-LDBARMAP-011과 같은 수준으로 현재화한다. 한 줄 편집으로 충분하며 REQ/AC 문면·개수에는 영향 없다.
2. (선택, D2) AC-LDBARMAP-011 검사 3에 리터럴 grep 루프를 추가해 검사 1·2와 같은 수준의 기계적 실행 가능성을 맞춘다.
3. D1 교정 후, 이 부분 감사의 재확인은 `grep -n '존재하지 않\|아직 없\|미정' .moai/specs/SPEC-LDBARMAP-001/spec.md`로 HISTORY/만료 고지 바깥에 잔존 단언이 없는지만 다시 확인하면 된다(전체 재감사 불필요 — delta 재감사).
