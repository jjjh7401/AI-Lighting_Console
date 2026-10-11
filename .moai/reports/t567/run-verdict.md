# t567 + t575 run 판정 (SPEC-LDBEAT-001 REQ-020)

브랜치 `WT-accent-exception` · 기준 origin/main `e5d0140e` · 콘솔 접촉 0건 · 곡 리터럴 0건

## t567 — 전환 경고에 시안의 ★ 마디 예외

- 정본: 시안 `ldbeat-runbook-ui-proposal-20261008.html` `warnOf` 322행
  `... && t.fade===0 && !ACC.includes(seg[0])` — ★ 예외는 **위치 경고에만** 걸린다(323행 색 경고엔 없음).
- 변경: `transitionWarnings(prev, cur, sectionStartBars, accentBars = [])`, `jointMarker(..., beatsPerBar, accentBars = [])`.
  ★ 마디 = 곡 데이터 `buildSongOverview().accentBars`(accents 가 있는 구간의 시작 마디). `BeatGrid.tsx` 가 세 소비자
  (`BeatGridJoint`·`BeatGridScenePanel`·`BeatGridTransitionView`)에 `overviewModel.accentBars` 를 넘긴다.
- 낡은 docstring 「★ 마디 예외는 아직 곡 데이터가 없어 적용하지 못한다」 교체.

### RED → GREEN
- RED(수정 전): `npx vitest run src/components/beatGridTransition.test.ts` → `Tests  2 failed | 42 passed (44)`
  (새 시험 「★ 마디에선 위치 끊김 경고 없음」, 「★ 마디의 위치 끊김은 ! 아님」)
- GREEN(수정 후): 아래 전체 실행에 포함, 통과.
- 같이 넣은 대조 시험: ★ 마디라도 구간 경계가 아닌 색 끊김은 여전히 경고(예외 범위가 위치뿐임을 고정).

## t575 — 낡은 주석·호출 안 되는 함수 정리

- `BeatGrid.tsx` 주석 「효과(움직임)·디머 "효과"는 아직 읽기 전용(아래 Missing Inputs 참조)」 제거 — 디머 효과 선택(`dimmer_effect` option)과 움직임 직접 고르기(카드 t584)가 이미 있다.
- `isBrightnessValueEditable` 제거 — 호출처 grep: `BeatGrid.tsx` 정의 1 + `BeatGrid.test.tsx` 시험뿐(컴포넌트 0). 시험 describe 블록(5건)도 함께 제거.
- 범위 밖으로 남긴 것(같은 꼴의 낡은 문구, 리드 판단 대기): `BeatGrid.tsx` 큐 편집 칸 JSX 주석 「위치/색/효과/디머 프리셋은 … 여전히 읽기 전용」, 밝기 편집 주석 「"디머 효과"는 아직 목록이 없어 읽기 전용 안내만」.

## 검증 (이 트리, main 합치기 전 작업본)
- `npx tsc --noEmit -p .` (ui) → rc=0
- `npx vitest run` (ui 전체) → `Test Files  53 passed (53)` / `Tests  1183 passed (1183)`

## 안 잰 것
- 실제 화면(브라우저)에서 ★ 마디 이음매 글자가 사라지는지 눈으로 보지 않았다 — 순수 함수 시험과 prop 배선만 확인.
- 실제 곡 데이터에 accents 가 있는 구간이 어느 곡인지 확인하지 않았다.
