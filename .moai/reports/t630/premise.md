# t630 전제 재확인 — origin/main 19a52738

- 기준: 워크트리 HEAD = origin/main = 19a52738 (확인함)
- 8452171c 이후 ui/·server/ 코드 변경 0줄 (`git diff --stat 8452171c 19a52738 -- ui server` 출력 없음, 직접 확인)
- 직접 확인: ui/src/components/beatGridPanels.css 261–265행, 무대 칸 `height: 320px`
- 직접 확인: 시안 md 의 「높이 320px」 문장, 시안 HTML 93행 `.insp{height:390px}`, 시안 HTML 110행 `.stage svg{height:330px}`
- 직접 확인: SPEC REQ-LDBEAT-016(a)(b) 와 AC-LDBEAT-022(c) 가 무대 높이 320px 을 고정 요구함. 이탈은 감독 승인을 progress.md 에 먼저 기록해야 함 (spec.md 168·174행, acceptance.md 74행)
- 조사 에이전트 보고 (줄 근거는 구현 시 다시 읽어 확인): 아래 항목별 판정

## 항목별 판정

1. 마디 표시에 구간 이름 — 없음. 상단 바가 `N마디`만 그림. 구간 정보는 BeatGrid.tsx 의 viewBarSectionLabel 로 이미 계산 중. 계획: 같은 함수를 상단 바에 연결. 0마디 표기는 그 함수 결과를 따름.
2. 반영 대기 배지 — 일부 있음. 배지 코드는 있으나 값이 없으면 숨김. App.tsx 가 값 없음(undefined)을 넘김. 서버는 첫 반영 전 null 을 주도록 테스트로 고정되어 있음. 계획: null 이면 「—」 배지와 툴팁 「반영 기록 없음」. 0 으로 찍지 않음.
3. 줄 이름 둘째 줄 — 이미 있음 (BeatGrid.tsx 2257–2261 렌더, 그룹 소속이 확정된 줄만 표시). 제외.
4. 눈금 구간 이름·경계선 — 이미 있음 (BeatGrid.tsx 2186–2214). 제외.
5. 한눈에·무대 높이 389 — 보류. 앱은 320px, SPEC 은 320px 고정, 시안 md 는 320px, 시안 HTML 은 390px 상자(내부 389px)와 무대 SVG 330px. 시안 두 개가 서로 다름. 감독 결정이 필요함.
6. 무대 이름표·빔 — 코드는 있음 (BeatGridStage.tsx 198–206, 231–235). 확정 그룹 소속 장비에만 그려짐. 하네스는 8대만 확정되어 나머지는 회색 점으로 보임. 빔 길이·색 데이터는 페이로드에 없음. 제외하고 데이터 카드로 넘김.

## 요약
- 구현 예정: ①, ②
- 제외: ③, ④ (이미 있음), ⑥ (데이터 게이트)
- 보류: ⑤ (SPEC 수치와 시안 정본 불일치, 감독 승인 필요)

## 환경 메모
- 워크트리 디렉터리는 t630, 브랜치는 WT-runbook-ui-gaps. 디스패치의 EnterWorktree 값과 다르지만 레인 규약 §1 에 따라 디렉터리는 카드 id 를 유지함.
- 머지 방식은 merge commit (정책 커밋 21feaa67, t628). 레인 규약의 스쿼시 문장은 낡음.
- 기준선 캡처 대상: ui/runbook-preview.html 은 BeatGrid 를 포함하지 않으므로 t583 하네스(실제 앱 전체)로 재지정함.

## 아직 안 잰 것
- 화면 기준 확인: 기준선 캡처 대기 중
- 조사 보고의 줄 번호(BeatGridTopBar.tsx 렌더 줄, App.tsx 1221 등)는 구현 시 다시 읽어 확인함
