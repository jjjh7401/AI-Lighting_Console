# t470 계획 — 생성기에 트래킹·MIB·페이저·포지션 위젯 (t466 후속 UI)

2026-09-27 · lane-3 · 트리 `.claude/worktrees/t470` @ `319412ed`(t460 #512 + t466 #511 포함)

t460 D2(감독 승인: 「파서가 아는 어휘만」)에서 뺀 네 조작을, t466 이 파서 어휘를 넓힌 뒤 붙인다. 원칙은 t460 그대로 — 산출물은 문장뿐, 판정은 서버.

## 문장 (t466 verdict §1 그대로)

| 칸 | 문장 | 기대 `changes` |
|---|---|---|
| 트래킹 | `큐 3 트래킹 Block으로 바꿔줘` | `{"tracking": "Block"}` |
| MIB | `큐 3 MIB dark로 설정` | `{"mib_mode": "dark"}` |
| 페이저 | `큐 3 페이저 Breathe Soft로 바꿔줘` | `{"phaser": "Breathe Soft"}` |
| 포지션 | `큐 3 포지션 2.11 Sweep L로 바꿔줘` | `{"position": "Sweep L", "position_preset_no": "2.11"}` |

네 칸 모두 큐 전체 값 — 그룹을 싣지 않는다.

## 결정

- **P1 포지션 행**: 풀 2 팝업 선택 → `포지션 2.<no> <이름>` 문장. t460 에서 포지션 행이 임시로 쓰던 `무브먼트 <이름>` 문장은 포지션 행에서 뗀다(서버에 진짜 포지션 칸이 생겼다). 이전값은 `section.position`.
- **P2 트래킹**: 4택(Track·Block·Cue Only·Release). 이전값 `section.tracking`, 없으면 `Track`(t466: 없으면 Track 으로 본다).
- **P3 MIB**: 4택(없음·dark·mark·live) → 칸 `mib_mode`. 조립기가 계산한 기존 `mib`(참/거짓)와 다른 칸이라 이전값은 `section.mib_mode` 만 읽는다.
- **P4 페이저**: 페이저 프리셋은 콘솔 풀에 있다(딤머 페이저 풀 1, 컬러 페이저 풀 4 — `server/web/presets_api.py`). 행에 풀 1·풀 4 두 `바꾸기`를 두고 고른 이름으로 문장을 만든다.
- **타입**: `SongTimelineSection` 에 `tracking?`·`mib_mode?`·`phaser?`·`position_preset_no?` 추가(추가만).

## 파일

`ui/src/protocol.ts` · `ui/src/components/cueRequestSentence.ts`(+시험) · `ui/src/components/PlanCueRequestGenerator.tsx`(+시험) · fixture `ui/src/components/__fixtures__/cueRequestSentences.json` 에 네 문장 추가 · `server/tests/test_plan_cue_generator_vocabulary_t460.py` 는 fixture 를 읽으므로 자동으로 네 건이 늘어난다(대표 5종 개수 단언은 9로 갱신). CSS 필요 시 `ui/src/styles.css`.

## 완료 조건

build exit 0 · vitest 전량 통과 · 어휘 잠금 pytest 에 네 문장 PASS · PR 전 main 합류(lane-2 t467 이 `protocol.ts` 를 만질 수 있다) · verdict.md.
