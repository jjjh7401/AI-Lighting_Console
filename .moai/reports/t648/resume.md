# 재개 블록 — SPEC-LDBARMAP-003 (카드 t648)

## 상태 (2026-10-14)

- **착수 승인: 있음.** 감독 결정(2026-10-14, 리드 AskUserQuestion 경유). 대상은 SPEC-LDBARMAP-003 v0.1.4, 커밋 `25248fe0`(plan-audit 3차 PASS 0.85, 감사 대상 `a74093e7`).
- **구현: 아직 시작하지 않았다.** 이 세션은 컨텍스트 84%에서 중단했다.
- **브랜치:** `WT-barmap-entry-ui`. 원격 푸시 완료. 원격 HEAD는 `25248fe0`(푸시 직후 `git ls-remote`로 확인).
- **워크트리:** `.claude/worktrees/t648`(보존).
- **기준:** 브랜치는 `b8ac5719` 위의 계획 커밋 다섯 개다(`5880fc66`, `0db2f275`, `88edf81f`, `a74093e7`, `25248fe0`). 원격 `origin/main`은 `8ee56a9a`(PR #696 병합, PROTOCOL 라벨 정정). 구현을 시작하기 전에 `origin/main`을 다시 읽고 rebase한다.

## 검수 이력

- 1차 FAIL 0.68 → 2차 FAIL 0.77 → 3차 PASS 0.85. 보고서는 `.moai/reports/plan-audit/SPEC-LDBARMAP-003-review-{1,2,3}.md`(로컬, gitignore).
- 3차 남은 소견. 모두 v0.1.4(`25248fe0`)에 반영됨.
  - D1: AC-014 허용 목록에 `.moai/reports/t648/` 추가.
  - D2: App.tsx 범위를 식별자로. 구조분해 392~429행, `songAudioName` 선언 446행, 첨부 블록 1031~1042행.
  - D3: 배선 수동 항목 추가. 클릭 한 번, 연결 끊김, 분석 중 busy 유지, 취소 뒤 늦은 결과, 넘침.
  - D5: shall 없는 문장 보정. REQ-003·004·005·011.
  - D6: 계획 9행과 REQ-004의 드롭다운 불일치 정정.
  - 선택 소견: D4 grep 검사 구체화, D7 대기 밖 error 규정, D8 배치 검사, D9 AC-001 제목, D10 time_signature 필드 명시, D11 5초 폴링 인용.
- 리드 요청(v0.1.4에 반영): PROTOCOL 26행 항목을 Gaps에서 뺐다(정정은 PR #696, `8ee56a9a`). 결과 라벨 네 개(저장, 분석 거절, 저장 불가, 저장 거절)를 문구 표에 넣었다.

## 재개 절차 (다음 세션)

1. 이 파일과 `SPEC-LDBARMAP-003/{spec,plan,acceptance}.md`(v0.1.4)를 읽는다.
2. 착수 승인은 이미 받았다. 다시 묻지 않는다.
3. /moai run의 Phase 1: 계획 산출물 해시가 v0.1.4로 바뀌었으므로 v0.1.4의 차이만 재검수한다. 전체 재감사는 하지 않는다.
4. 구현은 RED부터 시작한다(plan.md §3). 시험은 DOM 없이 한다. 순수 리듀서(`barMapEntryState.ts`), `renderToStaticMarkup`(`BarMapEntry`), 소스·CSS 텍스트 검사.
5. 기준점 B = `git merge-base origin/main HEAD`를 구현 시작 때 고정한다. AC-014의 `git diff` 검사는 모든 변경을 커밋한 뒤 실행한다.
6. 수동 확인 다섯 개는 plan.md §4에 있다. 결과는 `.moai/reports/t648/`에 둔다(추적 대상이라 `git add -f`는 필요 없다).

## 고정된 결정 (되돌리지 않는다)

- 화면 자리 「나」: 곡 첨부 상태 블록 곁(감독, 2026-10-14).
- 「취소」 버튼을 넣는다. busy는 안내만 보이고 대기는 끝나지 않는다. 대기는 결과·오류·끊김·취소로만 끝난다(감독, 2026-10-14).
- 취소 뒤 늦은 결과는 표시한다. 결과 줄에는 오프셋을 적지 않는다.
- 입력창은 막지 않는다. 막는 것은 「분석」 버튼 두 개와 대기 중 드롭다운이다.
- 파일명 표시는 t648이 맡는다(REQ-LDBARUI-006, 013). 범위를 넓히지 않는다. t649는 감독이 「C + B 길이만」을 택했다(리드 전달).

## 금지

- `moai session list`, `moai todo`, 전역 `git stash`, `git add -A`, 콘솔 쓰기.
