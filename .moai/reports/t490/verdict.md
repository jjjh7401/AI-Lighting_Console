# t490 판정서 — 재질의 대기 타임라인의 `fade_seconds: null` 로 런북 화면이 빈다

- 카드: t490(t485 lane-2 실측). 재현 원천 `.claude/worktrees/t485/.moai/reports/t485/bullet_probe.json` `raw_payload_without_workaround`
- 레인: lane-1 · 워크트리 `.claude/worktrees/t490` · 브랜치 `WT-null-fade-crash` · 기준 `7f8990fc`(착수 시점 `origin/main`)
- 콘솔 접속 0 · 서버 코드 변경 0

## 1. 요약

| 항목 | 결과 |
|---|---|
| 결함 | 재질의 대기(`lifecycle: requires_requery`) 타임라인은 구간마다 `fade_seconds: null` 을 싣는다. CUE SHEET(`CueSheetTimeline.tsx:773`)는 `undefined` 만 막아 `null.toFixed` 로 터지고, 에러 경계가 없어 `#root` 전체가 빈다 |
| 서버 null 은 의도인가 | **의도다** — §3 |
| 처방 | UI 만 고쳤다. 타입을 `number \| null` 로 바로잡고 소비처 셋이 null 을 빈 칸으로 받는다 |
| 커밋 | `6d011989`(수정 + 시험) · `cd880643`(뮤테이션) |

## 2. 재현(RED)

`ui/src/components/nullFade.t490.test.tsx` 가 t485 의 **실제 세션 출력**(`payload_causal.json`, 인터뷰부터 끝까지 돌린 `song_timeline` 이벤트)을 픽스처로 쓴다. 파일은 바이트 그대로 옮겼다 — `ui/src/components/__fixtures__/requeryTimeline.t490.json`, sha256 `a61b651fd274270669004ec4ac5b0d5c8cd5835ef7d2cf6a013c9249ef1bcdd0`(원본과 같음).

고치기 전(`red_ui.txt`): 4 failed · 2 passed. CUE SHEET 렌더가 브라우저와 **같은 문구**로 터졌다 — `TypeError: Cannot read properties of null (reading 'toFixed')`. 통과한 둘은 픽스처 전제(재질의 대기 · 구간 전부 null) 확인과 값 있는 페이드 대조군이다.

## 3. 서버가 null 을 싣는 것은 의도인가

**의도다.** 근거는 코드 불변식이다.

- `server/design/song_cue_composer.py` `SongCueCompositionResult.__post_init__`: `"a successful bundle cannot also request re-query cards"` — 재질의 요구가 있으면 조립기 결과(`bundle`)는 반드시 `None` 이다.
- `server/web/session.py` `_song_send_timeline`: `requery_requirements` 가 있으면 `lifecycle = "requires_requery"`.
- `server/web/session.py` `_song_timeline_payload`: `fade_by_section` 은 `bundle is None` 이면 빈 사전이고, 구간마다 `fade_by_section.get(index)` → `None`.

즉 재질의 대기에서는 큐가 아직 만들어지지 않았고, 페이드는 **정해지지 않은 값**이다. 0 을 넣으면 「즉시 전환」이라는 거짓 값이 되고, 키를 빼면 「값 미정」과 「구버전 페이로드」가 구별되지 않는다. 그래서 서버는 그대로 두고, UI 타입(`fade_seconds?: number`)이 서버 계약보다 좁았던 것을 고쳤다.

## 4. 같은 페이로드의 null 전수

`jq -c '[paths(. == null)]'` 로 픽스처 전체를 셌다 — null 은 8자리다.

| 경로 | 개수 | 종류 | UI 소비처 | 위험 |
|---|---|---|---|---|
| `sections[].fade_seconds` | 3 | 숫자 | CUE SHEET 페이드 칸 · Fade/Track 줄 · 수정 요청 「이전 값」 | **셋 다 결함** — 크래시 1 · `Fade nulls` 1 · `null초` 1 |
| `director_decisions[4].value.d_level` | 1 | 숫자(Q4 값 안) | `value` 는 `unknown` 타입. 화면은 `palette`·`color_usage` 축만 읽는다(`analysisSummary.ts:58,68`) | 없음 |
| `director_decisions[4].value.color_tendency` | 1 | 문자열 | 위와 같음 | 없음 |
| `disabled[0].section_index` | 1 | 숫자 | 타입이 이미 `number \| null`, 화면은 `reason` 만 읽는다(`analysisSummary.ts:96`) | 없음 |
| `readback.verified` | 1 | 불리언 | `SongTimeline.tsx:314` 가 `=== null` 로 따로 받는다 | 없음 |
| `readback.message` | 1 | 문자열 | `?? ` 로 받는다(`SongTimeline.tsx:316`) | 없음 |

`fade_seconds` 를 소비하는 자리는 `grep -rn fade_seconds ui/src`(시험 제외)로 셌다 — 위 셋과 요청 문장 생성기(`cueRequestSentence.ts` — 새 값만 쓰고 이전 값은 받은 문자열) · 예시 데이터뿐이다.

## 5. 처방

| 파일 | 변경 |
|---|---|
| `ui/src/protocol.ts` | `fade_seconds?: number` → `number \| null`(주석에 재질의 대기 의미) |
| `ui/src/components/CueSheetTimeline.tsx` | `=== undefined` → `== null` |
| `ui/src/components/SongTimeline.tsx` | `fadeTrackLine` 의 `!== undefined` → `!= null` |
| `ui/src/components/PlanCueRequestGenerator.tsx` | 이전 값 계산을 `fadeBeforeLabel` 로 뽑고 `!= null` |

## 6. 시험

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| RED | `vitest run src/components/nullFade.t490.test.tsx`(고치기 전) | 4 failed · 2 passed | `red_ui.txt` |
| GREEN | 같은 명령(런북 전체 렌더 시험 추가 뒤) | 7 passed | `green_ui.txt` |
| 런북 전체 | 같은 파일 — `RunbookMode` 를 실제 재질의 대기 페이로드로 `renderToStaticMarkup` | 첫 구간 라벨이 그려지고 `nulls`·`null초` 없음 | `green_ui.txt` |
| 뮤테이션 | `uv run python .moai/reports/t490/mutate.py` | **3/3 CAUGHT** — M1(CUE SHEET 원래 결함 되살림)은 CUE SHEET 시험 둘 + 런북 전체 시험, M2(Fade/Track)는 단위 시험 + 런북 전체 시험, M3(이전 값)은 단위 시험. 추적 파일 복원 확인 | `mutation.txt` |
| UI 전체 | `vitest run` | 33 파일 · **735 passed**(= 728 + 7) | `vitest_full.txt` |
| 타입 | `tsc --noEmit -p ui` | 오류 0 | `tsc.txt` |

## 7. 안 잰 것

- **헤드리스 브라우저 재실행.** t485 의 `bullet_probe.js` 를 이 트리에서 다시 돌려 `#root` 길이가 0 이 아닌지 보지는 않았다. 대신 같은 페이로드로 `RunbookMode` 트리 전체를 서버 렌더해 확인했다 — 브라우저의 효과(`useEffect`)·스크롤 코드는 이 렌더에서 돌지 않는다.
- **픽스처의 출처 트리.** 픽스처는 t485 브랜치(미머지)에서 만든 페이로드라 `concept_bullet` 키가 하나 더 있다. 이 카드의 코드는 그 키를 읽지 않는다.
- **에러 경계.** 한 컴포넌트의 예외가 화면 전체를 비우는 구조(에러 경계 없음)는 그대로다. 이 카드 범위 밖이다.
- **서버 시험.** 서버 코드를 바꾸지 않아 로컬에서 돌리지 않았다. PR CI 가 전체를 잰다.

## 8. 남은 위험

- 다른 lifecycle 이나 다른 곡에서 null 로 오는 숫자 필드가 더 있을 수 있다. 전수는 이 한 페이로드(재질의 대기 · 3구간) 기준이다. `trig_time_seconds` 는 서버 코드상 null 이 될 수 있지만(`uses_trig_time` 이 거짓일 때) 이 페이로드에는 없었고, UI 는 이미 `!== null` 로 받는다(`SongTimeline.tsx:231`).
- t485(PR #540)가 `conceptGlance.ts`·`session.py` 를 건드린다. 이 카드는 그 두 파일을 건드리지 않았다.
