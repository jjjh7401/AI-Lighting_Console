# t591 run verdict — 런북 화면 시안 꼬리 (무빙 네모 · 낡은 주석 둘 · 편집 칸 첫 화면 칸 수)

- 카드: t591 · SPEC-LDBEAT-001 REQ-022 · 리드 배차 2026-10-11 (Class A/B 경계 — plan 생략)
- 브랜치: `WT-stage-movers-boxes` · 기준 `origin/main` eb63ec17
- 콘솔 연결 0 · 콘솔 쓰기 0(`console_executed_884{1,2}.log` 0바이트) · 하네스 서버 2개 내림(8841·8842 리스너 0)

## ① 2D 무대 — 무빙 장비를 시안처럼 네모로

| 전 | 후 |
|---|---|
| 모든 장비가 반지름 5 동그라미 | 층 역할 **mover** 인 줄에 소속이 확인된 장비는 10×10 네모(시안 `drawStage` `rect x-5 y-5 width=10 height=10`), 나머지는 동그라미 그대로 |

- 무빙 판정은 `fixtureIsMover(fixture, tracks)` 하나 — `track.layer_role === "mover"` 이고 `fixtureBelongsTo`(무대 판독 `member_fids` 에서 온 확인 소속, 이름 정확 일치) 일 때만. **그룹 이름 규칙 0**.
- 색·불투명도는 동그라미와 같은 함수(`fixtureDisplayColor`·`fixtureDisplayOpacity`) — 꺼진 칸이면 회색 처리도 동그라미와 같다.
- 시험 2개 추가(`beatGridStageDecor.test.ts`): 그룹 이름 `QQQ` 로도 무빙 판정 · 이름이 「MOVER-U 501」이어도 소속 확인이 없으면 무빙 아님.

**눈으로 본 것**: `side_by_side_before/1450x1000/app_1450_6_stage_2d.png`(무빙 16대 동그라미) → `side_by_side_after/1450x1000/1450_6_stage_2d.png`(MOVER-U 보라 8대·MOVER-D 청록 8대 네모, BACK·STROBE·BLIND·FOH 는 동그라미 그대로). 1700 도 같은 폴더에.

**하네스 가정**: 무빙 소속을 그림으로 보려고 t588 하네스 옵션 `T588_NAME_MEMBERSHIP=1`(장비 이름 앞부분 = 그룹 이름)을 켜고 찍었다. 이 가정은 `serve_fake.py` 안에만 있다 — 제품 코드는 이름으로 소속을 추측하지 않는다(위 시험 두 번째가 그것을 잠근다).

## ② `BeatGrid.tsx` 낡은 주석 둘

| 위치 | 전 | 후 |
|---|---|---|
| 큐 편집 칸 JSX 머리 | 「밝기 값만 고칠 수 있고 위치/색/효과/디머 프리셋은 카탈로그가 없어 여전히 읽기 전용」 | 밝기(값·디머 프리셋·디머 효과)·위치·색·효과·움직임 칸이 늘 열린 고르기로 고쳐진다(t588), 프리셋 목록은 서랍 카탈로그에서 |
| 밝기 단일모드 | 「디머 효과는 아직 목록이 없어 읽기 전용 안내만」 | 디머 프리셋·디머 효과 목록은 서랍의 디머 섹션에서 온다(못 읽었으면 고르기가 꺼진다) |

근거(코드 대조): 디머 효과 고르기는 `splitDrawerSectionEffectEntries(dimmerSection)` 목록을 쓰고 「적용」에서 `buildBrightnessDimmerEffectChanges` 로 편집 요청을 보낸다. `disabled={!dimmerSection || dimmerSection.unread}` — 주석의 「못 읽었으면 꺼진다」는 이 줄이다. 동작은 바꾸지 않았다(주석만).

## ③ 늘 열린 편집 칸 — 무빙 줄 첫 화면에 몇 칸 보이나 (판정만, 고칠지는 리드)

MOVER-U 3마디 막대를 고른 직후, 스크롤 없이(`probe_fields.py`, 결과 `probe_fields_after.json`):

| 창 폭 × 높이 | 칸 수 | 다 보임 | 반만 걸침 | 편집 칸 상자 | 스크롤 |
|---|---|---|---|---|---|
| 1450 × 1000 | 6 | **6** | 0 | 높이 440 (scrollHeight 438 = clientHeight 438) | 없음 |
| 1700 × 1000 | 6 | **6** | 0 | 같음 | 없음 |

칸: 밝기 · 위치 프리셋 · 효과 프리셋 · 근거 · 움직임 · 설명(원문) — 그 아래 「콘솔 명령」까지 첫 화면에 다 들어온다(`after_{1450,1700}_mover_panel.png`). 페이지 오류 0.

판정: **이 하네스 곡·이 리그에서는 고칠 것 없음.** 다만 무빙 줄에 「색」 칸이 안 나온다(이 곡 MOVER-U 에 색 필드 없음) — 색 칸이 있는 무빙 줄이거나 안내 줄이 더 붙으면 7~8칸이 되어 넘칠 수 있다. 그 경우는 재지 않았다.

## 바뀐 파일

- `ui/src/components/BeatGridStage.tsx` — `fixtureIsMover` + 무빙 장비 `<rect className="beat-grid-stage-mover">`
- `ui/src/components/BeatGrid.tsx` — 주석 둘(코드 동작 변경 0)
- `ui/src/components/beatGridStageDecor.test.ts` — 시험 2개 추가

## 증거

```
$ npm --prefix ui test -- --run          # vitest.txt
Test Files  54 passed (54) · Tests  1191 passed (1191)

$ npm --prefix ui run build              # build.txt (tsc + vite)
exit=0
```

- 전후 캡처: `side_by_side_{before,after}/{1450,1700}x1000/` — before 는 수정 전 트리(eb63ec17)로 `ui/dist-before` 빌드, after 는 이 브랜치 `ui/dist`. 두 쪽 모두 앱 페이지 오류 0(`capture_{before,after}.log`).
- 하네스: `serve_fake.py`·`capture.py` 는 t588 것을 그대로 복사.

## 안 잰 것

- 실기 콘솔 0회 — 무빙 소속은 하네스 이름 가정으로만 그림에 나왔다. 실기에서는 `member_fids` 판독이 그 그룹을 확인해야 네모가 된다(확인 안 되면 동그라미 — 지어내지 않음).
- 색 칸이 있는 무빙 줄, 칸이 7개 이상인 줄의 첫 화면 칸 수.
- 1450·1700 외 폭, 높이 1000 외.
