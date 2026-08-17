# SPEC-COPILOT-LDGUIDE-001 — 수용 기준 (acceptance)

## HISTORY

| 버전 | 일자 | 변경 |
|---|---|---|
| 0.1.0 | 2026-08-17 | 최초 작성. AC-001~017, REQ 1:1 대응. |
| 0.2.0 | 2026-08-17 | plan-audit 1회차(FAIL 0.56) 반영. 정규식 파손 교정(D1) · AC-002/004/006/011/014/016 재작성(D6~D10) · AC-018/019 신설(REQ-016/017) · §A.1의 "전 항목 기계 검증" 과대 주장 정정(D9) · 모든 명령을 코드블록으로 이동. |

## §0. 표기 규약 [HARD]

**grep 명령은 반드시 코드블록에 둔다. 마크다운 표 셀에 넣지 않는다.**

1회차 감사 D1: 표 셀에 넣으면 파이프를 `\|`로 이스케이프하게 되는데, `grep -E`는 `\|`를
선택(alternation)이 아니라 **문자 그대로의 파이프**로 읽는다. 그 패턴은 어떤 입력에도 0을
반환하므로 **상시 통과하는 가짜 검사**가 된다. AC-005·AC-012가 실제로 이 상태였다.

아래 모든 AC의 명령은 `§D. 검증 명령 모음`의 코드블록에 있다. §C 표는 판정 기준만 담는다.

공통 변수:

```bash
G=docs/user-guide.html
E=.moai/specs/SPEC-COPILOT-LDGUIDE-001/evidence.md
B=.moai/specs/SPEC-COPILOT-LDGUIDE-001/backlog-candidates.md
```

## §A. 완료 정의 (Definition of Done)

1. AC-LDG-001~019 전부 그린.
2. **검증 수단의 정직한 구분** — 전 항목이 기계 검증이라는 주장은 하지 않는다(1회차 감사 D9
   정정). 실제 구성은:
   - **기계 검증 15건**: AC-001~010 · 012 · 013 · 017 · 018 · 019 — §D에 실행 가능한 명령이 있다.
   - **원장 대조 4건**: AC-011 · 014 · 015 · 016 — 명령으로 형식은 검사하지만, 판정의
     최종 근거는 `$E`/`$B`의 행 내용이다(§B).
3. M0 증거 원장(`$E`)이 존재하고, 가이드의 모든 능력 주장이 `data-ev`로 그 행을 가리킨다.
4. `$B`가 존재하고 9단계 전부에 행이 있다.
5. 변경 파일이 허용 2경로뿐이다(AC-013).

## §B. 판독 기준 — 기계 검증이 대신할 수 없는 것

grep은 "문장이 있는가"를 세지만 "그 문장이 참인가"는 세지 못한다.

| 판독 항목 | 판정 방법 | 불충분한 근거 |
|---|---|---|
| 능력 주장의 진위 | `$E`의 대응 행에 **명령 + 관측 출력**이 있고, 그 명령이 **재실행 가능**할 것 | 도구 설명문 인용(설명문은 LLM 지시문이지 동작 증명이 아니다) · `ok:true` · 코드를 읽었다는 진술 |
| 보존 판정의 타당성 | 25개 `<h3>` 전량에 `keep`/`merge`/`drop`이 부여됨 — 빈칸 0 | "중요한 것만 골랐다"는 서술 |
| "감독 언어"인가 | AC-005·006이 기계적 하한선 | 그 위의 문체는 사용자 검수 영역이며 SPEC 실패로 삼지 않는다 |

**자기인증 한계 [명시]**: `$E`를 쓰는 주체와 그 원장으로 채점받는 주체는 같은 run 단계
행위자다. 이 SPEC은 그 순환을 **완전히 닫지 못한다.** 닫은 것은 형식(행 존재·명령 열·
출력 열·재실행 가능성)이고, 닫지 못한 것은 "그 명령을 실제로 돌렸는가"다. 이 잔여 위험은
sync 단계의 독립 감사로 넘긴다 — 여기서 해결됐다고 주장하지 않는다.

## §C. AC 표 — REQ 1:1 대응

| AC | 대응 REQ | 판정 기준 | 명령 |
|---|---|---|---|
| **AC-LDG-001** | REQ-001 | 단계 `<h2 id="stage-N">`가 N=1~9로 빠짐·중복 없이 정확히 9개 | §D.1 |
| **AC-LDG-002** | REQ-002 | `part-do`/`part-app`/`part-gap` 각각 정확히 9개 **AND** 등장 순서가 `do app gap` 9회 반복 | §D.2 |
| **AC-LDG-003** | REQ-002 | `part-gap` 절 9개 각각의 본문 비어 있지 않음. 간극 없는 단계는 리터럴 문구 `확인된 간극 없음` 포함 | §D.3 |
| **AC-LDG-004** | REQ-003 | `class="op-note"` 블록이 **오퍼레이터 조작 절차가 있는 단계마다 1개 이상** **AND** 공백 정규화 후 본문과 완전 일치하는 문장 0건 | §D.4 |
| **AC-LDG-005** | REQ-004 | SPEC ID·모듈 경로·소스 파일명·에이전트명·함수 호출형 토큰이 문서 전체에 0건 | §D.5 |
| **AC-LDG-006** | REQ-005 | 도구 식별자 최초 등장 행 ≥ `<h2 id="appendix-tools">` 행. 즉 본문 구간 등장 0 | §D.6 |
| **AC-LDG-007** | REQ-006 | 소요 시간 예측 표현 0건 | §D.7 |
| **AC-LDG-008** | REQ-007 | `$E` 도구 배정표 행 수 == 등록 도구 수(개정 시점 재측정) **AND** 각 행의 명령 열·출력 열 비어 있지 않음 | §D.8 |
| **AC-LDG-009** | REQ-008 | 본문에 실린 주장 중 원장 확인 실패분은 리터럴 `미확인` 표기를 가짐. §A.2의 식별자 부재 16건 전부에 `covered-in-prose`/`stale`/`absent` 판정이 `$E`에 존재(공란 0) | §D.9 |
| **AC-LDG-010** | REQ-009 | 가이드의 모든 수치 토큰(`N가지`·`N종`·`N개`·`N%`·`N배`)이 `$E` 재측정표의 값과 일치. 불일치 0 | §D.10 |
| **AC-LDG-011** | REQ-010 | 개정 전 `<h3>` **25개** 전량에 `keep`/`merge`/`drop`이 `$E`에 기재(공란 0) **AND** `keep` 판정분 전량이 개정본에 존재 | §D.11 |
| **AC-LDG-012** | REQ-011 | 외부 URL 0 **AND** `<script>`/`<link>` 0 (개정 전 측정값 0/0에서 회귀 없음) | §D.12 |
| **AC-LDG-013** | REQ-012 | 변경 파일이 `docs/user-guide.html` + `.moai/specs/SPEC-COPILOT-LDGUIDE-001/` 하위뿐 | §D.13 |
| **AC-LDG-014** | REQ-013 | **본문에 실린** 안전 경고 전량이 지정 단계 `<h2>` 구간 안에 있고 각 근거가 `$E`에 귀속. 제외분은 `$E`에 제외 사유 기재. **건수 하한 없음** | §D.14 |
| **AC-LDG-015** | REQ-014 | `$B`의 단계 1~9 각 행이 3필드(막히는 지점/관측 근거/다음 SPEC이 정할 것) 전부 채움 — 빈 필드 0 | §D.15 |
| **AC-LDG-016** | REQ-015 | 변경 파일 목록에 `.moai/state/kanban/` 경로 0건 (plan 세션이 큐를 건드리지 않았다는 **산출물 쪽 음성 증거**) | §D.16 |
| **AC-LDG-017** | REQ-001 | 목차의 각 `href="#..."` 대상 `id`가 문서 내에 존재. 미해석 앵커 0 | §D.17 |
| **AC-LDG-018** | REQ-017 | 모든 `data-ev` 값이 `$E`의 실재 행 id로 해석됨 **AND** 능력 주장 문장 중 `data-ev` 없는 것 0건 | §D.18 |
| **AC-LDG-019** | REQ-016 | 가이드의 모든 스네이크케이스 토큰이 등록 도구명 ∪ 명시 허용목록에 속함. §A.4의 유령 3건 잔존 0 | §D.19 |

## §D. 검증 명령 모음

```bash
G=docs/user-guide.html
E=.moai/specs/SPEC-COPILOT-LDGUIDE-001/evidence.md
B=.moai/specs/SPEC-COPILOT-LDGUIDE-001/backlog-candidates.md
T=server/orchestrator/tools.py

# D.1  단계 h2 9개
grep -oE '<h2 id="stage-[0-9]+"' "$G" | sort -u | wc -l          # 9

# D.2  3부 구조 + 순서
grep -c 'class="part-do"' "$G"                                   # 9
grep -c 'class="part-app"' "$G"                                  # 9
grep -c 'class="part-gap"' "$G"                                  # 9
grep -oE 'class="part-(do|app|gap)"' "$G" | sed 's/.*part-//;s/"//'
#   기대: do app gap 가 9회 반복

# D.3  한계 절 비어있지 않음
grep -A3 'class="part-gap"' "$G" | grep -cE '[가-힣]'            # >= 9
grep -c '확인된 간극 없음' "$G"                                   # 간극 없는 단계 수와 일치

# D.4  오퍼레이터 보조 블록
grep -c 'class="op-note"' "$G"                                   # >= 1 per 해당 단계
#   중복 판정: 공백 정규화 후 op-note 내부 문장이 같은 절 본문에 완전 일치로 등장 = 0

# D.5  본문 금지 토큰 (파이프는 이스케이프 없음 — §0)
grep -cE 'SPEC-[A-Z]+|server/|\.py\b|manager-|\.moai/|[a-z_]+\(\)' "$G"   # 0

# D.6  도구 식별자는 부록 이후에만
APPENDIX_LINE=$(grep -n '<h2 id="appendix-tools"' "$G" | cut -d: -f1)
grep -nE '\b(run_commands|query_state|get_rig_context|find_looks|instantiate_look)\b' "$G" \
  | cut -d: -f1 | awk -v a="$APPENDIX_LINE" '$1 < a' | wc -l     # 0

# D.7  시간 예측 금지
grep -cE '[0-9]+ *(일|주|개월|시간) *(정도|쯤|이면|안에)' "$G"      # 0

# D.8  원장 배정표 행 수 == 등록 도구 수
grep -cE '^            name="[a-z_]+",$' "$T"                    # 등록 도구 수 (기준값)
grep -c '^| `' "$E"                                              # 배정표 행 수 — 위와 일치

# D.9  미확인 표기 + 16건 판정
grep -cE 'covered-in-prose|stale|absent' "$E"                    # >= 16

# D.10 수치 주장 대조
grep -oE '[0-9]+ *(가지|종|개|%|배)' "$G" | sort | uniq -c        # $E 재측정표와 수동 대조

# D.11 보존 판정 (모집단 25)
git show HEAD~1:"$G" 2>/dev/null | grep -c '<h3'                 # 25 (개정 전)
grep -cE '\b(keep|merge|drop)\b' "$E"                            # >= 25

# D.12 자체완결성 (회귀 금지)
grep -coE 'https?://[^"'"'"' ]+' "$G"                            # 0
grep -cE '<script|<link' "$G"                                    # 0

# D.13 변경 경로 봉쇄
git diff --name-only main...HEAD

# D.14 안전 경고 배치 — $E 귀속 대조 (건수 하한 없음)
grep -c 'class="warn"' "$G"

# D.15 백로그 3필드
grep -c '^| 단계' "$B"                                           # 9

# D.16 큐 무접촉 음성 증거
git diff --name-only main...HEAD | grep -c 'kanban'              # 0

# D.17 앵커 해석
for a in $(grep -oE 'href="#[^"]+"' "$G" | sed 's/href="#//;s/"//'); do
  grep -q "id=\"$a\"" "$G" || echo "MISSING: $a"
done                                                              # 출력 없음

# D.18 data-ev 대응
grep -oE 'data-ev="[^"]+"' "$G" | sed 's/data-ev="//;s/"//' | sort -u \
  | while read -r id; do grep -q "$id" "$E" || echo "UNRESOLVED: $id"; done   # 출력 없음

# D.19 유령 식별자 잔존 0
grep -cE '\b(run_preshow_check|check_patch|generate_groups)\b' "$G"          # 0
```

## §E. 엣지 케이스

| # | 상황 | 기대 동작 |
|---|---|---|
| E1 | M0에서 단계 3(포커싱) 대응 도구가 **없다**고 판정 | 실패 아님. 단계 3 `part-app`은 "앱이 대신하는 부분 없음"을 명시하고 `part-gap` + 백로그 1건으로 처리(plan §A.4 게이트 A NEGATIVE) |
| E2 | 식별자 부재 16건이 **전부** 산문으로 덮여 있음 | 실패 아님. AC-009는 판정이 존재하면 그린 — 결과값이 무엇이든 무방 |
| E3 | 안전 경고 4건 중 근거 재확인에 실패한 건이 있음 | 그 경고를 **싣지 않는다**(REQ-008). AC-014는 건수 하한이 없으므로 GO/NEGATIVE 양쪽 다 유효 — 1회차 감사 D3이 지적한 모순은 이 개정으로 해소됨 |
| E4 | 기존 서술 중 개정본과 **모순**되는 것 발견 | `drop` 판정 + `$E`에 사유 기재(AC-011). 모순을 남긴 채 병기하면 FAIL |
| E5 | 도구 수가 개정 도중 코드 변경으로 바뀜 | AC-008·010은 **개정 시점 재측정값** 기준. 고정 숫자 33을 하드코딩하지 않는다 |
| E6 | 9단계 중 일부가 실제로는 앱과 무관(전부 사람 일) | 실패 아님. `part-app`에 "없음", `part-gap`에 근거를 적고 백로그 판단은 M4에서 |
| E7 | 개정 전 `<h3>` 25개 중 일부가 `merge` 판정 | `keep` 아니므로 존재 검사 대상이 아님. 단 `$E`에 병합 대상 절을 명시 |
| E8 | 유령 식별자가 §A.4의 3건 외에 더 발견됨 | 실패 아님. §A.4는 실측된 3건의 기록이고, AC-019는 **전량 0**을 요구하므로 추가분도 자동 포섭 |

## §F. 품질 게이트

이 SPEC은 코드를 변경하지 않으므로 통상의 lint/test 게이트가 아니라 다음을 적용한다:

1. **경계 확인** — `git diff --name-only`가 허용 2경로뿐(AC-013). 서버 코드 무접촉.
2. **테스트 스위트 생략 — 사유 명시** — 코드 무변경이므로 실행 대상이 아니다.
   생략 사실을 침묵하지 않는다. 또한 이 워크트리에는 `ui/node_modules`가 없어 `npm test`가
   `vitest: command not found`로 실패하는데, 이는 환경 사유이며 변경 내용과 무관하다.
3. **증거 원장 대조** — §B. 원장 행이 없는 주장 0건.
4. **자기인증 잔여 위험** — §B 말미에 명시. 이 SPEC 안에서 닫히지 않으며 sync 단계 감사로 이관.
