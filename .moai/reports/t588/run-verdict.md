# t588 run verdict — 편집 칸 고르기를 처음부터 열고, 2D 무대에 빔·워시 장식

- 카드: t588 · SPEC-LDBEAT-001 REQ-021·022 · 리드 판단 「시안대로」(t586 판단 요청 답)
- 브랜치: `WT-open-dropdowns` · 기준 `origin/main` 0a89a121 → PR 직전 재확인 때 main 이 `6a7fc3c7`(t569 칩 설명, `BeatGrid.tsx` 겹침)로 움직여 합침(`e276751a`, 충돌 0). 합친 트리에서 빌드 통과 · vitest 1188 passed(`build_merged.txt`·`vitest_merged.txt`)
- 콘솔 연결 0 · 콘솔 쓰기 0(`console_executed_883{1,2}.log` 0바이트) · 백그라운드 서버 2개 내림(8831·8832 리스너 0, 프로세스 0)

## ① 편집 칸 — 처음부터 열린 고르기 (시안 `.sidepane .ed`)

| 전 | 후 |
|---|---|
| 값 + ✎ 를 눌러야 그 칸 하나만 드롭다운이 열림(`activeEditField`) | 편집할 수 있는 칸(밝기·위치·색·효과·움직임)은 **늘 열려 있다** |
| 칸을 열 때 초안을 현재 값으로 채움 | **고른 막대(줄+칸 시작 마디)가 바뀔 때** 모든 초안을 현재 값으로 채움(`seedEditDrafts`) — 한 칸을 적용해 격자가 새로 와도 다른 칸에 고치던 초안은 그대로 |
| [적용] [취소(닫기)] | [적용] [되돌리기(그 칸만 지금 값으로)] — 적용은 전과 같은 서버 격자 편집 요청(콘솔 아님) |
| 값이 비어도 표시는 「미정」 글자 | 고르기 맨 위 「— 미정 —」, 지금 값이 아직 읽은 목록에 없으면 「N (지금 값)」 한 줄 — 첫 선택지(「새 프리셋 만들기」)가 골라진 것처럼 보이지 않게 |
| 이름표·값 한 줄 | 이름표를 위 한 줄(진흙빛 굵게 + 위 구분선), 고르기를 그 아래 칸 폭으로(시안 `.sidepane .ed label`) |

움직임 칸(`BeatGridMovementPicker`)은 초안을 마운트 때 채우므로, 막대가 바뀌거나 되돌리기를 누르면 `key` 를 바꿔 다시 마운트한다. 그 컴포넌트의 공개 모양(`editing`·`onOpen`)과 시험은 그대로다.

**측정(브라우저, 하네스)**
- 막대 A 밝기 값에 70 입력(적용 안 함) → 막대 B → 다시 A: `{"A_initial":"25","A_typed":"70","B_shown":"60","A_back":"25","typed_value_leaked":false}` (`probe_reseed.py`) — 예전 「선택이 바뀌면 입력을 닫는다(이전 칸 값이 새 칸에 새지 않게)」 보장이 그대로다.
- 무빙 줄: 움직임 고르기가 처음부터 열림(select 1개), sweep 으로 바꾼 뒤 되돌리기 → 원래 값 `""` (`probe_mover.py`, 페이지 오류 0).

## ② 2D 무대 — 시안 `drawStage` 장식을 장비 좌표에서

| 장식 | 시안 | 앱(이 카드) |
|---|---|---|
| 바닥 | 손으로 정한 사각형 `#1b1b22` | 읽힌 장비 전체를 감싸는 사각형, 같은 색 |
| 워시 면 | 바닥 전체에 워시 색, `밝기/160` | 층 역할 **wash** 인 줄의 **소속 확인 장비 영역**에, 그 칸이 켜졌을 때만, 줄 색 · 40/160 |
| 무빙 빔 | 손으로 정한 줄에서 아래로, 반폭 9, 길이 = 틸트 | 층 역할 **mover** 인 줄의 소속 확인 장비마다, 켜졌을 때만, 반폭 9, 길이 = 장비→무대 앞 가장자리 거리의 절반(앱은 틸트를 읽지 않음), 줄 색 · 100/260 |

- 그룹 이름·번호 상수 0 — 어느 줄이 워시/무빙인지는 `layer_role`(앱 어휘)에서만, 위치는 소속이 확인된 장비 좌표에서만. 시험이 일부러 그룹 이름 `ZZZ`·`QQQ` 로 그린다(`beatGridStageDecor.test.ts` 6개).
- 장비 점·이름표·선택 점선·장비 클릭은 그대로(장식은 그 아래에 깐다).

**눈으로 본 것**: `side_by_side_{before,after}/1450x1000/1450_6_stage_2d.png` — 전: 점만, 후: 바닥 + MOVER-U(보라)·MOVER-D(청록) 빔 8개씩. 워시 면은 이 하네스 리그에 워시 장비가 없어 그림에선 못 봤다(시험으로만 확인).

**하네스 가정 표시**: 무빙 소속을 그림으로 보려고 하네스에 `T588_NAME_MEMBERSHIP=1`(장비 이름 앞부분 = 그룹 이름) 옵션을 넣었다. **제품 코드는 이름으로 소속을 추측하지 않는다** — 이 가정은 `serve_fake.py` 안에만 있고, 화면 안내 줄에 「(t588 하네스 가정) … 시험 그림 전용, 콘솔 판독 아님」으로 보인다.

## 바뀐 파일

- `ui/src/components/BeatGrid.tsx` — `activeEditField` 제거, `seedEditDrafts` + 막대 키 효과, 늘 열린 칸·되돌리기, `renderPresetOptions(…, current)` 「— 미정 —」·지금 값, 움직임 칸 `key`
- `ui/src/components/BeatGridCuePanelParts.tsx` — 움직임 고르기 버튼 「취소」→「되돌리기」
- `ui/src/components/BeatGridStage.tsx` — `stageDecorations` + 바닥·워시·빔 렌더
- `ui/src/components/beatGridStageDecor.test.ts` — 신설 6개
- `ui/src/styles.css` — `.beat-grid-cue-field.is-editing`(시안 `.ed label`)

## 증거

```
$ npm --prefix ui test
Test Files  54 passed (54) · Tests  1185 passed (1185)

$ npm --prefix ui run build      # tsc + vite
exit=0
```

- 전후 캡처 `side_by_side_{before,after}/{1450,1700}x1000/`(6 무대 · 7 편집 칸 · 8 전환 + 앱 전체 화면), 앱 페이지 오류 0
- 작업 중: `after_1450x1000_{default,selected,transition,bottom}.png`, `probe_after_mover_panel.png`

## 안 잰 것

- 워시 면을 실제 화면에서 — 하네스 리그(t525 판독 60대)에 워시 장비가 없다.
- 실기 콘솔·프리셋이 채워진 곡 0회 — 서랍을 연 뒤(프리셋 목록이 있을 때) 「지금 값」 줄이 목록 항목으로 대체되는 모양은 하네스 FakeConsole 이 풀을 못 읽어 눈으로 못 봤다(코드 경로: `listed` 이면 그 줄을 안 그림).
- 고르기가 늘 열려 편집 칸이 길어졌다 — 440px 칸 안 스크롤로 들어간다(시안도 같은 칸 스크롤). 무빙 줄처럼 칸이 많은 줄에서 첫 화면에 몇 칸이 보이는지는 세지 않았다.
