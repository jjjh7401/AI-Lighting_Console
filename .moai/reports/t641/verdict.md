# t641 판정 — 런북 Fade 줄 반올림 (표시만, 저장값 불변)

## 1. 주장 (Claim)

- 런북 Fade 줄(`ui/src/components/SongTimeline.tsx`의 `fadeTrackLine`)은 페이드 초를 소수 둘째 자리로 보여 준다. 뒤의 0은 뗀다. 예: `Fade 3.4365532879818375s` → `Fade 3.44s`.
- 저장값(`section.fade_seconds`)은 바뀌지 않는다. 반올림은 표시 문자열을 만들 때만 한다.
- 반올림 시험은 수정 전 코드에서 실패한다(재현 먼저).

## 2. 증거 (Evidence)

**(a) 수정 전 재현.** 시험만 추가한 상태에서 `unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && npm --prefix ui run test -- src/components/SongTimeline.test.tsx` 를 실행했다. 원문:

```
FAIL  src/components/SongTimeline.test.tsx > REQ-LDDESIGN-083 — 하단 3줄이 읽는 컨셉 행 짝짓기 (t460) > Fade display rounds to 2 decimals but never touches the stored fade_seconds (t641)
AssertionError: expected 'Fade 3.1573333333333267s · Track —' to be 'Fade 3.16s · Track —' // Object.is equality
Test Files  1 failed (1)
Tests  1 failed | 21 passed (22)
```

**(b) 수정 후.** 같은 환경 정리 형식으로 실행했다.

- `src/components/SongTimeline.test.tsx`: `Tests 22 passed (22)`
- `src/components/RunbookMode.test.tsx` + `src/components/runbookM7.test.tsx`: `Tests 36 passed (36)`
- `npm --prefix ui run build` (`tsc && vite build`): `EXIT=0`
- 전체 UI 시험: `Test Files 60 passed (60)`, `Tests 1273 passed (1273)`

**(c) 실곡 미리보기.** `http://127.0.0.1:47010`, 런북 모드 켬, 곡 「Design Interview」(139.67 BPM). 같은 백엔드 데이터를 같은 화면에서 읽었다.

| 줄 | 수정 전 (운영 빌드, DOM 원문) | 수정 후 (카드 빌드, 같은 데이터) |
|---|---|---|
| 1 | `Fade 3.4365532879818375s · Track —` | `Fade 3.44s · Track —` |
| 2 | `Fade 0.6443537414965945s · Track —` | `Fade 0.64s · Track —` |
| 3 | `Fade 0.21478458049886484s · Track —` | `Fade 0.21s · Track —` |

캡처: `before-47010.png`(수정 전), `after-47010-card-build.png`(수정 후).

**(d) 커밋.** `02854714` `fix(t641): 런북 Fade 줄을 소수 둘째 자리로 표시 — 저장값은 그대로`. 시험과 수정을 한 커밋에 넣었다(아래 6번 참고).

## 3. 기준선 귀속 (Baseline-attribution)

- 브랜치 `WT-runbook-fade-round`, 시작점 `origin/main` `31c11421`. 시작 전 `git rev-list --count --left-right origin/main...HEAD` 결과는 `0 0`이었다.
- 시험과 빌드는 워크트리 `WT-t641-fade-display`에서 실행했다.
- 반올림 규칙의 근거는 세 가지다. ① 시안 `.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.html` 222행(「화면은 초를 먼저, 예: 2.14초 (1마디)」)과 같은 파일의 스크립트 `beatsToS`(`toFixed(2)` 뒤 0 제거). ② 선례 `ui/src/components/runbookM7.ts:95`(`Number(…toFixed(2))`). ③ `ui/src/components/CueSheetTimeline.tsx:775`(`toFixed(2)`).

## 4. 미검증 (Gaps)

1. 운영 47010은 아직 수정 전 빌드다. 이 빌드는 `lead-preview` 워크트리(`cca88d23`)에서 나온다. 머지 뒤 재배포되기 전까지 47010에서 수정 결과를 직접 보지 못한다. 「수정 후」 캡처는 47010의 같은 데이터에 카드 빌드의 번들만 바꿔 넣은 일회용 브라우저 세션에서 찍었다.
2. 실곡을 새로 불러오지 않았다. `POST /api/timelines/{id}/load`는 공유 백엔드 상태를 바꾸고 콘솔이 온라인이라 쓰기 경로에 닿을 수 있어 호출하지 않았다. 이 화면의 값은 캡처 시점에 이미 로드돼 있던 곡이다.
3. 저장값 불변은 단위 시험(함수 호출 뒤 객체의 `fade_seconds`가 그대로인지)과 변경 파일이 두 개뿐이라는 사실로 확인했다. 콘솔 명령 전송 경로(CueFade)는 이 diff에서 건드리지 않았고, 그 경로를 따로 재현하지는 않았다.
4. 형제 자리, 손대지 않음: `ui/src/components/PlanCueRequestGenerator.tsx:101`의 `fadeBeforeLabel`도 `${section.fade_seconds}초`로 원시값을 찍는다. 이 값은 같은 파일 342행 `applyFade`에서 변경 항목의 `before` 필드로 들어간다. 저장되거나 보내지는 페이로드 경로에 걸려 있으므로 이번 카드에서는 바꾸지 않았다. 표시만 바꿀지는 별도 판단이 필요하다.
5. 형제 자리, 표기만 다름, 손대지 않음: `ui/src/components/beatGridTransition.ts:19-21`의 `trimSeconds`는 `toFixed(2)`만 하고 0을 떼지 않아 `2.00초 (1마디)`로 찍힌다. 시안 스크립트는 0을 뗀다. 다른 화면이라 이번 카드 범위 밖이다.
6. CI(PR 헤드) 결과는 아직 없다. PR을 만든 뒤 헤드 SHA를 확인하고 나서 기록한다. 이 문서에는 CI 결과를 적지 않는다. 적으면 헤드가 밀린다.

## 5. 잔여 위험 (Residual-risk)

- 소수 둘째 자리로 반올림하므로 0.005 미만의 페이드는 `0s`로 보인다. 저장값은 그대로다. 시안 규칙과 같은 결과다.
- 시험 한 줄이 `Fade 3.16s · Track —` 형식에 고정돼 있다. 표기 규칙을 바꾸면 이 시험도 함께 고쳐야 한다.

## 6. 진행 메모 (Process notes)

- 구현 서브에이전트를 한 번 띄웠으나, 격리 워크트리에서 시작해 위치 확인 단계에서 멈췄다. 파일은 건드리지 않았다. 그래서 이 카드의 편집과 시험은 레인 세션이 직접 했다.
- 시험만 먼저 커밋하려 했더니 품질 게이트(pre-commit `npm test`)가 빨간 시험을 막았다. 게이트는 우회하지 않았다(`SKIP_MOAI_PRECOMMIT` 미사용). 그래서 시험과 수정을 한 커밋(`02854714`)에 묶었다. 수정 전 빨간 상태는 (a)로 기록했다.
