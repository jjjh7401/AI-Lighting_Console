# t466 판정서 — 큐시트 편집 파서 어휘 확장 (트래킹·MIB·페이저·포지션 프리셋)

- 카드: t466 · SPEC-LDDESIGN-001 M7 후속(t460 계획 F3·D2) · REQ-089 포지션/페이저 행, AC-039 트래킹 1건의 서버 전제
- 브랜치: `WT-parser-vocab`, 기준 `origin/main` 1a2ecf50
- 콘솔 쓰기: 0
- 판정: **PASS**

## 0. 감독용 요약

코파일럿이 큐시트 초안을 고치는 문장 네 종류를 새로 알아듣는다 — 트래킹, MIB, 페이저, 포지션 프리셋.
이제 lane-3 의 수정요청 생성기가 이 네 조작을 버튼으로 붙일 수 있다.

바뀐 값은 **초안에만** 남는다. 콘솔로 보내는 명령은 실기에서 잰 적이 없어 이 카드에서 만들지 않았고,
콘솔 반영 때는 칸마다 「아직 콘솔로 안 보낸다」는 사유가 붙는다.

## 1. 생성기가 보낼 문장 (lane-3 용)

모양은 기존 무드·이펙트 문장과 같다 — `큐 N <칸> <값>(으)로 바꿔줘|설정|변경|수정|해줘`.
큐를 화면에서 고른 상태라면 `큐 N` 은 빼도 된다(기존 t290 규칙 그대로).

| 칸 | 문장 예 | `changes` | 받는 값 |
|---|---|---|---|
| 트래킹 | `큐 3 트래킹 Block으로 바꿔줘` | `{"tracking": "Block"}` | `Track` · `Block` · `Cue Only` · `Release` (한국어 `트랙·블록·블럭·큐온리·릴리즈·릴리스` 도 받음) |
| MIB | `큐 3 MIB dark로 설정` | `{"mib_mode": "dark"}` | `none`(=없음) · `dark` · `mark` · `live` (`없음·다크·마크·라이브` 도 받음) |
| 페이저 | `큐 3 페이저 Breathe Soft로 바꿔줘` | `{"phaser": "Breathe Soft"}` | 프리셋 이름(빈 값 거절) |
| 포지션 | `큐 3 포지션 2.11 Sweep L로 바꿔줘` | `{"position": "Sweep L", "position_preset_no": "2.11"}` | 번호는 선택, **이름은 필수**, 번호는 풀 2(`2.`)만 |

초안 칸 이름: `tracking`(없으면 Track 으로 본다), `mib_mode`(조립기가 계산한 기존 `mib` 참/거짓과 **다른 칸**,
건드리지 않는다), `phaser`, `position`(기존 칸), `position_preset_no`(새 칸). 네 칸 모두 큐 전체 값이라
그룹 지정(`KEY 트래킹 …`)은 기존 규칙대로 거절된다.

거절(쓰기 전, 부분 적용 없음) 사유 예:
- `트래킹 값은 Track, Block, Cue Only, Release 중 하나여야 합니다 (받은 값: 'Blok').`
- `MIB 값은 없음, dark, mark, live 중 하나여야 합니다 …`
- `번호만으로는 포지션 이름을 알 수 없습니다 …` / `포지션 프리셋은 풀 2에 있습니다 — '4.2'는 다른 풀의 번호입니다.`

⚠️ UI 쪽: `ui/src/protocol.ts` `SongTimelineSection` 에는 `tracking`·`mib_mode`·`phaser`·`position_preset_no` 가
아직 없다. 서버는 값을 싣지만 화면이 읽으려면 타입 추가가 필요하다(lane-3 영역, 이 카드는 손대지 않음).

## 2. 무엇을 바꿨나

| 파일 | 변경 |
|---|---|
| `server/design/cue_sheet_edit.py` | 문장 넷(`_TRACKING`·`_MIB`·`_PHASER`·`_POSITION`), 현장 말→닫힌 어휘 표, `TRACKING_VALUES`·`MIB_MODES`, 쓰기 전 판정 `_validate_t466_fields`, 쓰기 `_write_t466_fields`, 편집 가능 칸 5개 추가 |
| `server/design/cue_sheet_apply.py` | `UNSOURCED_FIELD_REASONS` 에 네 칸의 사유 |
| `server/tests/test_cue_sheet_edit_vocab_t466.py` | 새 시험 40개 |

## 3. 판정

### 기존 문장 파싱 결과 바이트 불변 — PASS

- 명령: `uv run python .moai/reports/t466/parse_corpus.py <json>` 을 변경 전(`parse_corpus_base.json`)·후(`parse_corpus_after.json`)로 떠서 비교
- 관측: `base 6867 after 6898 common 6867 changed 0 new_sentences 31` — 기존 6,867문장(`server/tests` 의 한국어 문자열 전부, `cue_selected` 참·거짓 둘 다)의 결과가 하나도 안 바뀌었다. 새 31문장은 이 카드의 시험 문장이다.
- 시험으로도 고정: `test_existing_sentences_parse_exactly_as_before` (기준 파일 `.moai/reports/t466/parse_corpus_base.json`). t461 의 같은 시험도 통과한다.

### 네 문장이 콘솔을 안 건드리고 초안에 닿는다 — PASS

- 이 파서 앞에는 콘솔로 쓰는 라우트가 줄지어 있다(페이저 recall·포지션 프리셋 등). 실제 `ChatSession` 으로 끝까지
  태워 `FakeConsole.executed == []` 를 셌다 — 트래킹·MIB·페이저(`Ph 2 step`, 카탈로그 진짜 라벨 `Breathe Soft`)·포지션
  5문장 모두 초안 칸이 바뀌고 콘솔 명령 0건.
- 근거: 페이저 recall 은 카탈로그 라벨 **그리고** 발사 동사(쳐줘·쏴·걸어·발사·틀어·재생)가 있어야 움직인다
  (`session.py` `_PHASER_RECALL_VERB`). `바꿔줘·설정` 은 그 목록에 없다.

### 회귀 — PASS

- 명령: 파서·반영기·사전 점검을 import 하는 11파일 + `test_web_cue_sheet_draft.py`·`test_web_session.py`·
  `test_draft_apply_routing.py` + 새 시험 → `803 passed, 22 skipped` (`affected_run.txt`)
- 린트: `ruff check`·`ruff format --check` 통과

## 4. 안 잰 것

- **콘솔 전송**: 네 칸 모두 콘솔 명령을 만들지 않는다. 트래킹·MIB 의 콘솔 문법은 이 저장소에서 실기로 잰 적이 없다
  (참고: lane-1 t464 가 MIB 관련 `SEQUMIBMODE` 를 관측한 기록이 있다 — 콘솔 전송 카드의 출발점).
- **전체 시험 스위트**: 로컬에서는 영향 범위만 돌렸다. 전체는 CI 가 PR head 에서 돈다.
- **화면 표시**: UI 타입에 네 칸이 없어 화면에 어떻게 보이는지는 확인하지 않았다(§1 ⚠️).

## 5. 남은 위험

- 포지션 이름은 자유 글자라 풀에 없는 이름도 초안에는 들어간다. 이름 확인은 콘솔 반영 경로가 할 일이다
  (지금은 반영 경로가 포지션을 보내지 않으므로 문제가 드러나지 않는다).
- `MIB` 는 대문자·소문자 모두 받는다. 앞에 영문자가 붙은 단어(`XMIB`)는 받지 않게 막았다.

## 6. 증거 파일

`.moai/reports/t466/` — `parse_corpus.py`·`parse_corpus_base.json`·`parse_corpus_after.json`(기존 문장 대조),
`affected_tests.txt`·`affected_run.txt`(회귀).

## 7. 후속 카드 제안

- 콘솔 전송: 트래킹·MIB·페이저·포지션을 초안 반영 경로에서 콘솔로 보내기 — 실기 문법 실측부터.
- UI 타입: `SongTimelineSection` 에 네 칸 추가(lane-3 의 생성기 카드와 묶을 수 있음).
