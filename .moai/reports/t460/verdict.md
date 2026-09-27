# t460 판정서 — PLAN CUE 수정요청 생성기 (SPEC-LDDESIGN-001 M7 4차)

2026-09-27 · lane-3 · 브랜치 `WT-plancue-generator-ui` · 계획 `plan.md`(감독 승인: 범위 「파서가 아는 것만」, 전송 「줄마다 한 문장」)

## 판정: PASS (조건부 2건은 아래 「안 잰 것」)

런북 모드의 PLAN CUE 카드 하단에 REQ-083 3줄·`Q###` 배지가 붙고, 그 아래 생성기가 마운트된다. 생성기는 클릭 선택을 **문장**으로 만들어 기존 `sendChat` 한 길로 보낸다. 타임라인을 로컬에서 고치지 않고 `changes` 를 만들지 않는다. 서버 코드는 한 줄도 바꾸지 않았다.

## 무엇이 생겼나 (diff 기준)

- `SongTimeline.tsx` — PLAN CUE 카드 하단 `Fade/Track`·`MIB/남김`·헤드룸 줄 + `Q###` 배지(REQ-083). 없는 값은 `—`.
- `cueRequestSentence.ts` — 선택 → 문장. 그룹 조도(`큐 3 KEY·BACK 밝기 95%로 바꿔줘`), 그룹 하나 컬러, 이펙트·무브먼트(프리셋 이름), 페이드, 전환. 자유 입력은 마지막 문장 끝에 그대로.
- `cueRequestWarnings.ts` — 파생 경고 4종: 후렴 밝기 역전, 리저브 위반(`reserve` 그대로), 잔여 그룹<4(`unused_groups` 그대로), MIB live(`rows[].mib` 그대로).
- `PresetPoolPopup.tsx` — `onSelect?` 하나. 없으면 기존 읽기 전용 그대로(기존 시험 무변경 통과).
- `PlanCueRequestGenerator.tsx` — 그룹 칩(혼합/혼합 2색, BLIND 잠금), 값 입력, 콘솔 반영 값 행, 변경 스택(줄별 경고·거절 사유·`✕`), `선택 취소`, 자유 입력, `코파일럿에게 반영 요청`. 줄마다 한 문장을 순차 전송, 거절되면 그 줄에 사유를 두고 멈춘다.
- `protocol.ts` — `reserve`·`unused_groups` 타입(추가만). `App.tsx`·`RunbookMode.tsx` — 선택 prop 으로 `sendChat` 관통.

## 리뷰에서 고친 것 (`eb44e9f8`)

1. **수락을 거절로 읽는 결함** — 처음 구현은 「depth 가 늘면 수락」이었다. 서버 되돌리기 기록이 `deque(maxlen=20)`(`server/web/timeline_draft.py:36`)라 20단계에선 편집이 성공해도 depth 가 20 그대로다. 「새 초안 표식 도착 + depth 비감소 + 변경 보고 있음」으로 바꿨다. 옛 판정으로 되돌리면 상한 시험 1건이 FAIL 하는 것을 확인했다.
2. **서버 규칙의 UI 복제** — `COLOR_CAPABLE_GROUPS = {KEY, BACK}` 가 서버 `_GROUP_COLOR_FIELD` 를 베끼고 있었다(REQ-092 위반 소지). 지웠다. 어느 그룹이 컬러 칸을 갖는지는 서버가 판정하고 거절 사유를 그 줄에 돌려준다.

## AC 대응표

| AC | 검증 | 결과 |
|----|------|------|
| 034 마운트 | `SongTimeline.test.tsx` — `onGeneratorSend` 없으면 미마운트, 있으면 마운트 | PASS |
| 035 혼합 표시 | `cueRequestSentence.test.ts` mixedIntensityLabel/mixedColorLabel + 생성기 뷰 시험 | PASS |
| 036 프리셋 이름 | `PlanCueRequestGenerator.test.tsx` 프리셋 이름 저장·표시 | PASS (딤머 행은 표시 전용 — 안 잰 것 2) |
| 037 BLIND 잠금 | `isGroupLocked` 단위 시험 + 뷰 시험 | PASS |
| 038 상태 라벨·줄별 경고 | 생성기 뷰 시험 | PASS |
| 039 어휘 일치 | fixture 5문장 — vitest(TS 빌더 출력 = fixture) + pytest `test_plan_cue_generator_vocabulary_t460.py`(파서 → 기대 `changes`) | PASS |
| 040 경고 6종 | 4종 구현·시험(`cueRequestWarnings.test.ts`), 재사용 3종은 서버 값만 읽음. **(2) 팬 폭·(6) 페이저=BPM 은 n/a → t467** | PASS 4 / n/a 2 |
| 041 대화 기록 동일 경로 | 구조: `onGeneratorSend` → 기존 `sendChat` 직결, 새 메시지 타입 0 | PASS(코드 판독) |
| 042 선택 취소 무전송 | 전송 spy 호출 0 시험 + 판독: `cancelSelection` 은 로컬 상태만 비움 | PASS |
| 043 「되돌리기」 라벨 1개 | 생성기에 「되돌리기」 문자열 부재 시험 | PASS |
| 044 수락 뒤 스택 비움 | `turnAccepted`/`applyTurnResult` 순수 시험(상한 20 포함) | PASS(순수 함수 수준 — 안 잰 것 1) |
| 052 `✕` 개별 제거 | 생성기 뷰 시험 — 한 줄만 사라지고 전송 0 | PASS |
| 053 자유 입력 | 마지막 문장 끝 덧붙임 시험 | PASS |

## 증거

| 무엇 | 명령 | 결과 |
|------|------|------|
| 빌드 | `npm --prefix ui run build` | exit 0, `✓ built` (`build.txt`) |
| UI 시험 전량 | `npm --prefix ui test` | `30 files, 691 passed` (`vitest_full.txt`) |
| 어휘 일치 + 편집 파서 회귀 | `pytest test_plan_cue_generator_vocabulary_t460.py test_cue_sheet_edit.py test_cue_sheet_edit_group_scope_t461.py` | `88 passed` (`pytest_vocab.txt`) |
| main 합류 | `origin/main` 7871767c(#510) 합류 뒤 위 세 개 재실행 | 위 값 |

## 안 잰 것 (Gaps)

1. **순차 전송 `useEffect` 배선 자체는 자동 시험이 없다.** 이 저장소 vitest 에 jsdom·testing-library 가 없고 의존성 추가는 범위 밖이라, 판정 로직을 순수 함수로 빼서 시험했다. 「응답 끝 → 다음 줄 전송」 타이밍은 코드 판독만 했다.
2. **딤머 프리셋(풀 1) 선택은 표시 전용이다.** `PresetEntry` 에 % 값이 없어 이름만으로는 보낼 문장을 만들 수 없다. 실제 전송은 밝기 숫자 입력이다. 프리셋 번호 문장은 t466.
3. 실기 콘솔·실제 브라우저에서 눌러 보지 않았다.
4. fixture 는 5종(조도·컬러·이펙트·페이드·전환)이다. 무브먼트 문장은 이펙트와 같은 문법이지만 fixture 에 따로 없다.

## 잔여 위험

- 생성기가 줄을 순차 전송하는 도중 감독이 대화창에 직접 입력하면 같은 `sendChat` 으로 섞일 수 있다(단일 채널 설계를 재사용한 결과, REQ-094).
- 수락 판정은 「그 턴에 새 초안 표식이 왔는가」다. 전송 중 다른 경로로 초안 표식이 오면(예: 다른 창의 편집) 오판할 수 있다.

## 후속 카드

- **t466** 파서 어휘 확장(트래킹·MIB·페이저·프리셋 번호)
- **t467** 팬 폭·페이저 속도 필드 노출(REQ-093 (2)(6))

SPEC 전체 sync 는 M8 이후 SPEC 을 닫을 때 한다(마일스톤마다 아님).
