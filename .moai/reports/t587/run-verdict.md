# t587 run 판정 — 상단 바 1450px 줄임 규칙 (SPEC-LDBEAT-001 REQ-LDBEAT-017(b))

- 카드: t587 · 브랜치 `WT-topbar-fit` · 기준 `origin/main` 0a08eef3
- 정본: `.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.html` `.top`(26행·158행), `.md:122`
- 범위: 상단 바 파일만(`ui/src/components/BeatGridTopBar.tsx`, `ui/src/styles.css` 상단 바 `@media` 블록, 시험 1개). 콘솔 접촉 0(FakeConsole 서버, 측정 뒤 내림)

## 원인 (잰 것)

`measure_topbar.py`(가짜 서버 + 헤드리스 크롬, 고치기 전 빌드)로 1450·1700 × 900·1000·1200 여섯 창을 쟀다 — `before/topbar_before.json`.

| 창 | 바 폭 | 내용 폭(scrollWidth) | 잘린 버튼 | BPM 알약 글자 |
|---|---|---|---|---|
| 1450 × 900/1000/1200 | 1378 | **1465** (87px 넘침) | 「⇪ 반영」「▤」 | `BPM 112.35 · 스피드 마스터 — 콘솔에서 직접 설정` (251px) |
| 1700 × 900/1000/1200 | 1616 | 1614 | 없음 | 같은 긴 문구 |

- 잘림은 **폭** 문제였다 — 세 높이에서 숫자가 같다. 카드 문면의 「세로 900px」은 t585 가 1450×900 에서 처음 본 자리일 뿐, 1000·1200 에서도 똑같이 잘린다(헤드리스 크롬은 겹침 스크롤바라 높이가 폭을 깎지 않는다 — 실제 맥 브라우저의 스크롤바 폭은 안 쟀다, 아래 「안 잰 것」).
- 두 원인: (1) 1450px 이상에서 `.beat-grid-topbar { flex-wrap: nowrap }` — 넘치면 줄바꿈 대신 오른쪽이 잘린다. 시안 `.top`은 늘 `flex-wrap: wrap`. (2) BPM 알약의 안내 문구(카드 t579)가 1450px 이상에서도 그대로 보여 251px 를 차지 — 시안은 `BPM 112.35` 만 보이고 안내는 `title`(마우스를 올리면).

## 고친 것

1. BPM 알약: 구분점 ` · ` 까지 `.beat-grid-pill-note` 칸 안으로 옮기고, `@media (min-width: 1450px)` 에서 그 칸을 숨김 → 시안처럼 `BPM 112.35` 만. 안내 전문은 알약 `title`(`SPEED_MASTER_MANUAL_TITLE`, 「사람이 콘솔에서 직접 설정합니다(자동 설정 방법 미확인)」)에 그대로 있다. 1450px 미만에서는 지금처럼 보인다.
2. `@media (min-width: 1450px)` 의 `flex-wrap: nowrap` 제거 — 시안 `.top{flex-wrap:wrap}` 과 같게. 한 줄은 줄임 문구로 지키고, 그래도 넘치면(긴 곡 제목·긴 음원 파일명) 잘리지 않고 다음 줄로 내려간다.

## 증거

**고친 뒤** — `after/topbar_after.json` (같은 스크립트, 고친 빌드):

```
1450x900  bar_w 1378 scrollW 1376 overflow False clipped [] | BPM 112.35
1450x1000 bar_w 1378 scrollW 1376 overflow False clipped [] | BPM 112.35
1450x1200 bar_w 1378 scrollW 1376 overflow False clipped [] | BPM 112.35
1700x900  bar_w 1616 scrollW 1614 overflow False clipped [] | BPM 112.35
1700x1000 bar_w 1616 scrollW 1614 overflow False clipped [] | BPM 112.35
1700x1200 bar_w 1616 scrollW 1614 overflow False clipped [] | BPM 112.35
```

- 한 줄 유지: 바 높이 전후 모두 58px(여섯 창 전부). 두 줄이면 높이가 늘어난다. (스크립트의 `rows` 칸은 세로 가운데 정렬 차이까지 세는 엉터리 지표라 판정에 안 쓴다.)
- 캡처: `before/` · `after/` 에 창마다 `app_{W}x{H}_topbar.png`(앱 상단 바)·`app_{W}x{H}_full.png`(창)·`mockup_{W}x{H}_topbar.png`(시안 상단 바).
- 시험(RED→GREEN): `ui/src/components/BeatGridTopBar.test.tsx` 새 묶음 「상단 바 — 1450px 이상 한 줄 (카드 t587)」 3건 — 고치기 전 `Tests 3 failed | 17 passed (20)`, 고친 뒤 `Tests 20 passed (20)`.
- UI 전체: `npx vitest run` → `Test Files 53 passed (53)` · `Tests 1178 passed (1178)`. `npm run build`(tsc && vite build) 종료 0.

## 리드 판단 요청 하나

카드 t579(REQ-LDBEAT-014)는 「hover title 만으로는 앱이 맞춘 값처럼 읽힌다」며 안내를 **보이게** 붙였다. 이 카드는 1450px 이상에서 그 안내를 다시 title 로만 돌린다(시안 정본 + 카드 지시). 1450px 미만에서는 여전히 보인다. REQ-014 문면(「안내를 표시한다」)은 title 표시로도 충족된다고 읽었지만, t579 의 판단과 방향이 반대라 승인 여부는 리드 몫이다.

## 안 잰 것

- 실제 맥 브라우저(겹침이 아닌 고정 스크롤바)에서의 폭 — 헤드리스 크롬만 쟀다.
- 1450px 미만 창(안내 문구가 보이고 줄바꿈되는 쪽)은 이번에 재지 않았다 — 코드상 그 경로는 바뀌지 않았다(`@media` 밖 규칙 무변경).
- 긴 곡 제목·긴 음원 파일명에서 실제로 둘째 줄로 내려가는 모습 — 시험 데이터(LOVE ATTACK, 음원 없음)에서는 한 줄로 들어가 그 경우가 안 생겼다.
