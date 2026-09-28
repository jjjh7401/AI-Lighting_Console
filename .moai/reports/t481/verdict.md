# t481 — 구간 위치 판정 통일 (BLIND 잠금 · 리저브 경고 · PLAN CUE 행 짝짓기) + 카드 넘침

- 카드: t481 (SPEC-LDDESIGN-001 AC-037·AC-040 FAIL 후속 — `sync-evidence/ac_ui_closeout.md` §3·§4)
- 워크트리 `.claude/worktrees/t481`, 브랜치 `WT-blind-lock-overflow`, 기준 `1e16bd8f`(= origin/main, PR #531 머지)
- 수정 커밋 `31c93714`. 서버 변경 0 — UI 파일만 고쳤다(t480 이 옮기는 `server/design`·`tools.py` 는 건드리지 않음). 콘솔 접속 0.

## 1. 결함 세 개와 원인

| # | 결함 | 원인(코드) | 증상(잰 값) |
|---|---|---|---|
| A | BLIND 가 한 번도 잠기지 않는다 | `PlanCueRequestGenerator.tsx:108` `cueNumber < item.released_q` — `released_q` 는 컨셉 **행** 번호(`session_bridge.py:212` `row["q"]`)인데 구간 `cue_number` 와 비교 | 36구간·행 49개 곡에서 BLIND `released_q=45, screen_position=33`. 큐 번호가 101~136 이라 `101 < 45` 는 거짓 → 카드 0~35 전부 풀림(`ac_ui_closeout.md` §3 AC-037). 실제 앱처럼 큐가 1부터라면 반대로 해제 뒤에도 잠긴 채 남는다 |
| B | 리저브 경고가 같은 비교를 쓴다 | `cueRequestWarnings.ts:47` 같은 식 | 경고 문구 「해제 큐(Q45)」 — 행 번호를 큐 번호처럼 표시 |
| C | **한 칸 밀림 — PLAN CUE 카드가 다음 구간의 컨셉 행을 읽는다** | `SongTimeline.tsx:200` `conceptRowForSection(report, section.index)` — `section.index` 는 1부터(`song_plan.py:154` `minimum=1`), `screen_position` 은 0부터(`session_bridge.py:66`, `protocol.ts:508`) | 「108 · Bridge 1」 카드가 Chorus 3 행 값 「MIB mark · 남김 2 / 헤드룸 부족 · 잔여 2그룹」을 표시(ac-ui 캡처 `01_initial.png`). 하단 3줄과 생성기 헤드룸·MIB 경고가 전부 한 칸 뒤 구간 값 |
| D | 생성기 버튼이 눌리지 않는다 | 카드 `min-width: 130px` 안에 생성기 내용 250px | 카드마다 버튼 26개 중 6~9개가 옆 카드에 덮임 |
| E | **카드 28장에 아예 닿을 수 없다**(D 를 재다 발견) | `.song-timeline { overflow: hidden }` — 가로 스크롤은 700px 이하 화면에만 있었다 | 1600×1000 에서 카드 36장 중 8장만 보이고, 20·35번 카드는 버튼 0/26 |

A·B·C 는 뿌리가 같다 — **"구간 위치"를 서로 다른 번호 체계로 셌다.** 예전 시험이 통과한 이유도 같다: 시험 데이터가 두 번호를 같게 뒀다(`released_q: 23` = 큐 23, `section.index: 0`). 실제 앱에서는 `index: 0` 이 나올 수 없다(최소 1).

## 2. 고친 것

- `runbookM7.ts` `sectionPosition(section, sections)` — 구간 위치(0부터)를 계산하는 **유일한** 함수.
- `cueRequestWarnings.ts` `reserveLock(name, reserve, position, sections)` — 잠금·경고 공통 판정 한 곳. 해제 위치는 `screen_position` 과 비교하고, 경고에는 그 구간의 큐 번호(`Q134`)를 적는다. `released_q` 가 null 이면 「미해제」로 잠그고, 해제 행이 화면 구간과 짝이 안 됐으면(`screen_position` null) 위치를 지어내지 않고 잠그지 않는다.
- `isGroupLocked` · `reserveViolationWarning` 은 `reserveLock` 을 부르기만 한다. `deriveWarningsForChange` · 생성기 훅 · `SongTimeline` 은 `sectionPosition` 을 쓴다.
- CSS: `.song-timeline-track { overflow-x: auto }`(카드 줄만 가로로 굴린다 — 머리말·결정 줄은 고정), `.song-timeline-section.has-generator { min-width: 280px }`(생성기가 붙은 카드만), 생성기 입력 줄·값 줄 `flex-wrap: wrap`.
- `SongTimeline` 은 생성기가 붙은 카드에만 `has-generator` 클래스를 단다. `SongTimeline` 은 `RunbookMode` 에서만 쓰여서 메인 화면은 바뀌지 않는다(`grep "<SongTimeline"` → `RunbookMode.tsx:247` 1곳).

## 3. 증거

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| RED | `vitest run SongTimeline.test.tsx PlanCueRequestGenerator.test.tsx cueRequestWarnings.test.ts` (수정 전) | **6 failed** — 「expected 'Fade — · Track —MIB mark · 남김 2헤드룸 부족…' to contain 'MIB — · 남김 9'」, 「해제 큐(Q45)」 등 | `red.txt` |
| GREEN | 같은 명령(수정 후) | 69 passed | `green.txt` |
| 전체 UI | `vitest run --reporter=verbose` | 31 파일 · **717 passed**(기존 710 + 신규 7) | `vitest_full.txt` |
| 타입 | `tsc --noEmit -p ui` | 제품 코드 오류 0(측정 당시 1건은 임시 하니스의 미사용 import — 하니스는 측정 뒤 삭제) | `tsc.txt` |
| 가드 변이 | `python3 mutate.py` — 고친 곳을 하나씩 옛 모양으로 되돌림 | **5/5 CAUGHT**(한 칸 밀림 2 fail · 행 번호 비교 3 fail · 가로 스크롤 제거 1 · 카드 폭 1 · has-generator 1). 실행 뒤 추적 파일 복원 확인 | `mutation.txt` |
| 브라우저 전 | `layout_probe.js … before_css`(BLIND 수정 뒤, CSS 수정 전) | 컨테이너 `overflow-x: hidden`, 사용자 스크롤 불가, 카드 36장 중 8장 보임. 버튼: 카드0 20/26 · 카드3 20/26 · 카드8 17/26 · **카드20 0/26 · 카드35 0/26**. 카드 3 「적용」 실제 마우스 클릭 5초 제한 **실패** | `layout_before_css.json`, `before_css_card3.png` |
| 브라우저 후 | `layout_probe.js … after_css` | 카드 줄 `overflow-x: auto`, 스크롤 가능, 카드 폭 280, 생성기 250/250(넘침 없음). 버튼 **26/26**(카드 0·3·8·20·35 전부). 카드 3 「적용」 실제 마우스 클릭 **성공**(스택 1줄) | `layout_after_css.json`, `after_css_card3.png` |
| BLIND(브라우저) | `?blind`(각 구간에 BLIND 칩만 덧붙이고 reserve 는 서버 값 그대로) | `LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLuuu` — 카드 0~32 잠김, 33~35 풀림(해제 구간 33). 수정 전 ac-ui 실측은 전부 풀림 | `layout_after_css.json` `blind` |
| 한 칸 밀림(브라우저) | 캡처 `after_css_card3.png` | Chorus 1(위치 3) 카드가 「MIB — · 남김 6 / 잔여 6그룹」 표시 = 자기 행(sp 3, unused 6). 수정 전에는 다음 행 값 「남김 7」 | `after_css_card3.png` |

데이터는 서버 `_song_timeline_payload` 실출력 36구간(`sync-evidence/ac_ui/payload_36.json`, `make_payload.py` 재현). 하니스 사본 `acuiHarness.tsx.txt` · `acui-harness.html.txt`(측정 때만 `ui/` 에 두고 커밋하지 않았다).

## 4. 판정

- AC-037(BLIND 잠금): **FAIL → PASS**(단위 시험 + 브라우저 잠김 패턴)
- AC-040(리저브 경고 부분): 번호 체계 결함 **해소**. 6종 중 팬 폭·페이저=BPM 2종은 감독 결정 D3·t467 그대로 n/a — 이 카드 범위 밖.
- 한 칸 밀림: **해소** — 하단 3줄·생성기 헤드룸/MIB 경고가 자기 구간 행을 읽는다.
- 카드 넘침·닿을 수 없는 카드: **해소**(1600×1000 에서 5개 카드 26/26, 실제 마우스 클릭 성공).

## 5. 안 잰 것

- 앱 본체(App + 웹소켓 + 서버)가 아니라 하니스로 띄웠다. 곡은 합성곡 하나, 뷰포트는 1600×1000 하나.
- 실제 앱처럼 큐 번호가 1부터인 페이로드로는 띄우지 않았다(위치 비교로 바꿨으므로 큐 번호 체계와 무관해졌지만, 그 곡으로 직접 보지는 않았다).
- 서버 페이로드 그대로는 BLIND 가 생성기 칩으로 나타나지 않는다(구간 `intensity` 가 KEY·BACK 뿐). 잠금은 `?blind` 로 칩을 덧붙여서 관찰했다 — 실제 리그에서 BLIND 칩이 언제 보이는지는 안 쟀다.
- 생성기 카드가 280px 로 고정되면서 PLAN CUE 카드 폭이 더는 곡 시간에 비례하지 않는다(이전에도 130px 최소 폭 때문에 5초 구간은 비례하지 않았다). 감독이 이 모양을 원하는지는 안 물었다.
- 스크롤 가능한 카드 줄에서 휠·트랙패드 조작은 `scrollLeft` 로 흉내 냈다(사람이 굴리는 것과 같은 효과로 가정).
