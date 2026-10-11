# t560 run 판정 — SPEC-LDBEAT-001 M9-B 타임라인·표

카드: t560 · 브랜치 `WT-timeline-glance` · 기준 origin/main `e41ec326`(t559·t561 합침)
범위: plan.md M9 step 2·4(나)·6 — REQ-LDBEAT-019(a)(c)·021(a)·023(a)(b)(c)(d)

## 커밋

| SHA | 내용 |
|---|---|
| 1860b5ba | 1차 구현 — 막대 4종 상태, L·R 자식 줄, 표→편집 초점 콜백, ▸ 펼침, 칩 툴팁, sticky |
| 3e6e1989 | origin/main 1d1aa813(t559) 합침 — import 충돌 1곳 |
| 37baf843 | 시안 대조 교정 — 표 6칸(줄·밝기·위치·색·움직임·전환)+칩, L·R 버튼을 ▸ 상세 줄 안 「이 구간 왼쪽·오른쪽 따로」/「L·R 다시 합치기」로 이동, 자식 줄 「└ <그룹> L/R」, 이름 규칙 유도 삭제 |
| 9f129dab | origin/main e41ec326(t561) 합침 — props 충돌 2곳, 표 칸 클릭 → `selectCue` + `setFocusField` 배선 |

## 증거 (합친 트리 9f129dab, `ui/`)

- RED: `npx vitest run src/components/beatgrid/tableFocus.test.ts` → `TypeError: glanceFocusAction is not a function` 3건 실패(구현 전). 1차·교정 단계 RED 는 에이전트 보고(모듈 미존재 5건, `computeLRSplitEligibility is not a function` 등).
- `npx vitest run` → `Test Files 46 passed (46)` / `Tests 1043 passed (1043)`
- `npx tsc --noEmit -p .` → 출력 없음, `npm run build` → exit 0
- 리터럴 검사: `grep -nE '\b(18|46|63|67)\b|SIDE|MOVER|LOVE|WASH|BACK\b|FOH|BLIND|30↔60|4박' src/components/beatgrid/*.ts*`(시험·주석 제외) → 0건

## AC 판정

| AC | 판정 | 근거 |
|---|---|---|
| AC-019(a) 막대 4종 상태 | PASS(판정·클래스) / 갭 | `cueDisplayState.test.ts`. 「고침=초록」은 `editedCueKeys` 를 채우는 곳이 아직 없어 화면에서는 안 켜진다 |
| AC-019(c) L·R 자식 줄 | PASS / 갭 | `lrSplit.test.ts`. 선언 전 0줄. 분리 가능 판정은 이름 규칙이 아니라 **확인된 소속 장비(`confirmedGroupName`)의 무대 x** 가 가운데 양쪽에 다 있을 때만 — 지금 데이터(확인 그룹 4개·그룹당 2대, 부모 그룹 소속 없음)로는 버튼이 사실상 안 보인다 → **t565 에서 풀림**(그룹→`member_fids`) |
| AC-021(a) 표 클릭 → 편집 칸 초점 | PASS | `tableFocus.test.ts` — 그 자리 편집 0, 서버 요청 0, `selectCue` 후 칼럼 필드로 `setFocusField` |
| AC-023(a) 6칸 표 | PASS | `glanceCells.test.ts` |
| AC-023(b) ▸ 상세 한 줄 | PASS / 갭 | `glanceRowDetail.test.ts`. Seq/Cue·콘솔 명령은 클라이언트에 없어 「미확인」 |
| AC-023(c) 칩 툴팁 「설명 · 이 곡에서 큐 N곳 사용」 | PASS(모양) / 갭 | `presetChipTooltip.test.ts`. 서버가 `description` 을 아직 안 채워 지금은 사용 수만 보인다 |
| AC-023(d) 제목·표 머리 sticky | PASS(CSS) | DOM 시험 틀이 없어 vitest 로 안 잼 |

## 갭 · 안 잰 것

- 브라우저에서 화면을 직접 띄워 보지 않았다(sticky·자식 줄 위치·칩 툴팁은 코드·시험으로만 확인).
- 「x 가 작을수록 왼쪽(L)」은 콘솔 방향과 대조하지 않은 가정이다(코드 주석에 표기).
- `BeatGrid.tsx` 변경이 origin/main 대비 +239/−30줄 — 로직은 `beatgrid/` 모듈에 있고 이 파일은 마운트·배선이지만, 「몇 줄만」보다는 크다.
- 「바뀐 것」 표시는 구조화 필드 4개(밝기·위치·색·효과 프리셋)만 비교한다.
- spec.md:168 의 「(a) 구현됨」 오기는 리드가 t564 로 넘김(이 레인은 SPEC 본문 무수정).
