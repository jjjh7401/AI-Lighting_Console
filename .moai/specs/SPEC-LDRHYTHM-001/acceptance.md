# SPEC-LDRHYTHM-001 — 인수 기준 (Given-When-Then)

표기: "오프라인 검사"는 콘솔 접촉 없이 문서·커밋 로그만 보는 것, "손 시연"은 M2 의 콘솔 접촉(감독 동석), "실기 판정"은 Club Diver 를 실제 콘솔에 올려 감독이 육안으로 보는 것을 가리킨다. **AC-LDRHYTHM-010(실기 판정)이 이 SPEC 의 유일한 완료 결정권자다** — 다른 모든 AC 는 그 판정에 이르는 사전 체(pre-filter)다.

## AC-LDRHYTHM-001 — M1~M3 게이트 동안 server/ 코드 변경 0 [REQ-LDRHYTHM-001, 002]

- **Given** 이 SPEC 의 run-phase 가 착수되고 M1~M3 중 어느 하나도 감독 최종 승인을 받지 못한 상태
- **When** `git log --oneline -- server/` 를 이 SPEC 의 run-phase 시작 커밋 이후로 조회하면
- **Then** 결과가 0건이다(server/ 아래 어떤 파일도 수정되지 않았다) — M3 감독 승인 전에 1건이라도 나오면 FAIL
- **측정**: `git log --oneline <run-phase-시작-SHA>..HEAD -- server/ | wc -l` → `0`

## AC-LDRHYTHM-002 — 순서 준수: M1→M2→M3→M4+ [REQ-LDRHYTHM-001]

- **Given** 이 SPEC 의 커밋 로그
- **When** 각 마일스톤의 커밋 타임스탬프를 비교하면
- **Then** M2 관련 커밋이 M1 감독 승인 기록(progress.md 또는 커밋 메시지)보다 앞서지 않고, M3 관련 커밋이 M2 완료 기록보다 앞서지 않는다
- **측정**: `git log --format='%ad %s' --date=iso -- .moai/specs/SPEC-LDRHYTHM-001/` 시간순 대조(오프라인 검사)

## AC-LDRHYTHM-003 — M1 대본의 형식과 코드-0 [REQ-LDRHYTHM-003]

- **Given** M1 산출물(Club Diver 연출 대본)
- **When** 그 문서를 열어 구조를 확인하면
- **Then** 시간순 표에 네 칸(음악 순간/놓는 연출/잇는 방식/이유)이 모두 있고, "이유" 칸이 벤치마크 보고서 §2.1 또는 §2.3 의 조항 번호를 인용하며, 문서 어디에도 실행 가능한 코드 블록이 없다
- **측정**: 오프라인 검사(문서 구조 육안 대조) + `git diff --stat <M1-전-SHA>..<M1-완료-SHA> -- server/` → 빈 출력

## AC-LDRHYTHM-004 — 첫 곡 범위 = Club Diver 단독 [REQ-LDRHYTHM-004]

- **Given** 8곡 전체 목록(t499 판독 대상)
- **When** M1~M3 의 대본·시연·규칙화 산출물이 다루는 곡을 세면
- **Then** Club Diver 1곡뿐이고, Rain 등 다른 곡의 대본·시연 산출물은 존재하지 않는다
- **측정**: 오프라인 검사(`.moai/specs/SPEC-LDRHYTHM-001/` 산출물 목록에서 곡명 언급 카운트)

## AC-LDRHYTHM-005 — 박자 층 이벤트가 정의대로 기록된다 [REQ-LDRHYTHM-005]

- **Given** M1 대본의 "박자 층" 항목들
- **When** 각 항목을 "킥/스네어 펄스", "체이스 한 칸", "색/위치 한 단계" 세 범주로 분류하면
- **Then** 모든 박자 층 항목이 이 세 범주 중 하나에 속하고, 범주 밖의 자유 서술(예: "화려하게")은 없다 — 항목 수가 수십~수백에 이르더라도 콘솔 큐 수(§9 의 "큐")로 집계되지 않음을 대본이 별도로 명시한다
- **측정**: 오프라인 검사(대본 "박자 층" 열의 범주 전수 분류)

## AC-LDRHYTHM-006 — 강조 층은 큰 히트에만, §10 금지목록 4번을 정확히 인용 [REQ-LDRHYTHM-006, 007]

- **Given** M1 대본의 "강조 층" 항목들(스트로브·블라인더)
- **When** 각 항목의 배치 위치와 인용 조항을 확인하면
- **Then** 모든 강조 층 항목이 코러스 진입·드롭·마지막 코러스급 순간에만 있고, 근거 인용이 "§10.3"이 아니라 정확한 위치("## 10." 목록 4번, 326~327행)를 가리킨다 — "§10.3"이라는 오표기가 하나라도 남아 있으면 FAIL
- **측정**: `grep -n "§10\.3" .moai/specs/SPEC-LDRHYTHM-001/*.md` → 매치 0건(오표기 잔존 검사)

## AC-LDRHYTHM-007 — 박자 층·강조 층과 §9/REQ-036 큐 밀도의 분리 [REQ-LDRHYTHM-008]

- **Given** M1~M3 산출물과 `docs/proposals/song-structure-lighting-standard.md` §9, `SPEC-LDDESIGN-001` REQ-036
- **When** §9 의 큐 밀도 수치(구간 수 중앙값 10 부근)와 `SPEC-LDDESIGN-001` REQ-036 원문을 이 SPEC 완료 전후로 비교하면
- **Then** 두 문서 모두 바이트 동일(변경 없음)하고, 이 SPEC 의 산출물 어디에도 박자 층 이벤트 수를 §9 의 "큐 수"로 합산한 서술이 없다
- **측정**: `git diff <시작-SHA>..HEAD -- docs/proposals/song-structure-lighting-standard.md` 의 §9 구간 + `.moai/specs/SPEC-LDDESIGN-001/spec.md` REQ-036 구간 → 두 곳 모두 빈 diff

## AC-LDRHYTHM-008 — 효과 속도가 스피드 마스터로 결속되고, 콘솔 오디오 입력을 쓰지 않는다 [REQ-LDRHYTHM-009, 010]

- **Given** M2 손 시연 로그
- **When** 효과 속도를 설정한 커맨드를 확인하면
- **Then** `Master 3.n At BPM <Club Diver 분석 BPM>` + `Attribute '<a>' At SpeedMaster <n>` 형태로 설정됐고, 스피드 마스터 16번(오디오 입력 BPM 마스터)은 사용되지 않았다
- **측정**: M2 시연 로그 그렙 — `grep -c "SpeedMaster 16" <시연 로그>` → `0`, `grep -c "At SpeedMaster" <시연 로그>` → `>=1`

## AC-LDRHYTHM-009 — 기계 점검은 사전 체일 뿐, 단독으로 PASS 를 만들지 않는다 [REQ-LDRHYTHM-011]

- **Given** M1~M3 산출물에 대한 오프라인 기계 점검(순간별 판정·연결 판정, 리듬 보고서 §⑤ R1~R4 류)
- **When** 그 기계 점검이 전부 PASS 로 나오더라도
- **Then** 이 SPEC 의 완료 보고서는 그것을 "완료"로 표기하지 않는다 — AC-LDRHYTHM-010(실기 판정)이 별도로 PASS 해야만 완료다. 완료 보고서 본문에 "기계 점검 PASS = 사전 체 통과, 완료 아님"이 명시돼 있지 않으면 이 AC 는 FAIL
- **측정**: 오프라인 검사(완료 보고서 본문에서 위 명시 문구 확인)

## AC-LDRHYTHM-010 — 실기 감독 판정 ≥3/5 (유일한 완료 결정권자) [REQ-LDRHYTHM-011]

- **Given** M3 완료 후 Club Diver 가 실제 콘솔에 올라간 상태, 감독 동석
- **When** 감독이 육안으로 점수를 매기면(AC-LDRENDER-016 과 같은 1~5점 척도)
- **Then** 점수가 **3점 이상**이어야 이 SPEC 이 `completed` 로 전이한다. 2점 이하는 FAIL이며, t501 과 같은 이월(후속 카드/SPEC)로 처리한다 — 기계 점검이 전부 PASS 여도 이 AC 가 FAIL 이면 이 SPEC 전체가 미완료다
- **측정**: 감독 실기 세션 기록(점수 + 판정 원문) — 수동, 기계로 대체 불가

## AC-LDRHYTHM-011 — M4+ 후보가 M3 종료 시점 실제 필요로 재확인된다 [REQ-LDRHYTHM-012]

- **Given** §3.6 의 M4+ 후보 네 항목(비트/다운비트/킥 검출, 타임코드 이벤트 송신, position_fx/plan_movement 연결, 장면 연결 규칙 승격)
- **When** M3 가 종료되면
- **Then** 네 항목 각각에 "Club Diver 대본·시연에서 실제로 쓰였다/안 쓰였다"가 기록되고, 안 쓰인 항목은 M4+ 범위에서 제외되거나 재설계 대상으로 명시된다 — 네 항목이 아무 재확인 없이 그대로 M4+ REQ 후보로 복사되면 FAIL
- **측정**: 오프라인 검사(M3 완료 보고서에 네 항목별 재확인 기록 존재 여부)

## Definition of Done

1. AC-LDRHYTHM-001~009, 011 전부 PASS(오프라인/시연 로그 검사로 확인 가능).
2. **AC-LDRHYTHM-010 이 PASS(실기 감독 ≥3/5)해야만 `status: completed`** — 기계 점검만으로는 `implemented` 까지만 전이한다(SPEC-LDRENDER-001 t501 의 선례와 같은 규율).
3. M4+ 후보에 대한 재확인 기록(AC-011)이 M3 완료 보고서에 남아 있다.
