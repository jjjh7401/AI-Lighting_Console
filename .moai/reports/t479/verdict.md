# t479 판정서 — 곡 되읽기가 실기에서 성공한 반영을 「실패」로 알리던 결함

- 카드: t479 · SPEC-LDDESIGN-001 · lane-2 · 발견 t474(`.moai/reports/t474/verdict.md` §4)
- 브랜치: `WT-readback-props`, 기준 `origin/main` b1ded510 (차이 `0 0` 확인)
- 콘솔 쓰기: **0** (실기 확인은 `state`·`props` 읽기뿐 — 감사 로그 `props_query` 13건)
- 판정: **PASS**

## 0. 요약

앱은 곡을 반영한 뒤 콘솔의 시퀀스를 다시 읽어 큐 시각(TrigType·TrigTime)을 맞춰 본다. 이 검사는 시퀀스를 한 번 읽은
**큐 목록** 안에서 그 값을 찾았다. 그런데 실기 응답기의 큐 목록에는 이름·번호만 있고 속성이 없다. 그래서 값이 `None` 으로
읽혔고, 성공한 반영이 매번 「readback 실패」로 감독에게 보였다(t474).

고친 것: 큐 목록에 그 값이 없는 큐만 그 큐 경로를 속성 읽기(`props`)로 한 번 더 읽어 채운다. 판정 규칙은 그대로다.
값이 틀리면 여전히 실패로 잡고, 속성을 못 읽으면 「검증 완료」라고 하지 않는다.

## 1. 변경

| 파일 | 변경 |
|---|---|
| `server/web/session.py` | `_readback_props_port`(게이트 상태 포트, 감사되는 읽기) 한 줄 · `_song_readback_requests` 가 판정 전에 `_fill_readback_cue_properties` 를 부름 · 그 메서드 신설 |
| `server/tests/test_song_readback_props_t479.py` | 새 시험 3개 — 가짜 콘솔이 **실기 모양**으로 답한다 |

`_fill_readback_cue_properties`:
- 기대 큐마다 큐 목록에서 번호(`cueNo`)로 찾는다. TrigType·TrigTime 이 둘 다 이미 있으면(기존 가짜 콘솔 모양) 읽지 않는다.
- 없으면 `<시퀀스 경로>/<i>` 를 `props TRIGTYPE,TRIGTIME` 로 읽어 그 자식에 덧붙인다. 읽은 값 중 `ok` 인 것만 쓴다.
- 읽기 예외는 「`<경로>` 큐 속성(props) 판독 실패: …」라는 실패 사유로 돌려준다.
- 판정은 기존 `_validate_song_sequence_readback` 이 한다(속성 이름은 대소문자·밑줄 무시 비교라 `TRIGTYPE` = `TrigType`).

## 2. 완료 조건

### ① 재현 시험 RED → GREEN — PASS

- 가짜 콘솔 `_LiveShapedConsole`: t474 캡처(`run7_seq210_state.txt`·`run8_cue_props.txt`)와 같은 모양이다. 자식은 OffCue(i=1)·
  CueZero(i=2)·큐들(i=3..)로 `class`·`i`·`name`·`cueNo` 만 싣는다. 속성은 `query_properties` 로만 나오고, 값은 콘솔이 받은 명령에서 온다.
- RED: `uv run pytest server/tests/test_song_readback_props_t479.py -q` → `2 failed, 1 passed` (`pytest_red.txt`).
  실패 문구는 「Sequence readback timed cue 1의 TrigType이 Time이 아닙니다: None」이다. **t474 실기에서 뜬 문구와 같다.**
  통과한 1개는 「props 를 못 읽으면 검증 완료가 아니다」 시험이다(고치기 전에도 실패로 끝나므로 참).
- GREEN: `3 passed` (`pytest_green.txt`)
  - 실기 모양 + 전부 저장됨 → 「readback 검증 완료」, `readback.verified = True`, props 읽기는 `DataPool/Sequences/210/<i>` 경로
  - 음성 대조: props 로 읽은 큐 6 의 TrigTime 을 +1초 틀리게 → 여전히 실패, 사유에 TrigTime
  - props 읽기 예외 → 「검증 완료」 아님, `verified = False`

### ② 기존 가짜 콘솔 모양(자식에 속성)도 통과 — PASS

- `test_web_session.py` 의 두 「readback 검증 완료」 시험(자식에 `TrigType` 을 직접 싣는 모양과 `properties` 에 싣는 모양)과
  되읽기 경로 순서를 못박은 시험이 그대로 통과한다. 그 모양에서는 추가 읽기를 하지 않으므로 조회 순서 단언도 그대로다.
- 영향받는 시험 185파일(`affected_tests.txt`): `uv run pytest @.moai/reports/t479/affected_tests.txt -q` → `5086 passed, 27 skipped` (`pytest_affected.txt`)

### ③ 실기 확인(읽기 전용) — PASS

- `uv run python .moai/reports/t479/live_readback_check.py` → `live_readback_check.txt`
  - 대상: t474 가 넣고 저장하지 않은 채 남긴 시퀀스 210(큐 13) · 타임코드 9. 기대값은 t474 에서 승인한 13개 TrigTime.
  - `고치기 전 판정: Sequence readback timed cue 1의 TrigType이 Time이 아닙니다: None`
  - `고친 뒤 판정: 통과` · `타임코드 9 판정: 통과`
  - 감사 로그: `props_query` 13건만(`audit/`). 쓰기 0. 자동 SaveShow 는 보내지 않게 바꿔 끼웠다(t474 감독 결정과 같음).

### 린트

- `ruff check`·`ruff format --check`: `session.py` · 새 시험 · 증거 스크립트 통과

## 3. 안 잰 것

- **앱 전체 경로로 실기 반영을 다시 해 보기**: 콘솔 쓰기 0 조건이라 하지 않았다. 실기 확인은 고친 메서드를 실기 포트에 직접 댄 것이다.
  `_song_readback_requests` 가 그 메서드를 부르는 연결은 ①의 시험이 받친다.
- **다른 되읽기 경로**: 이번 수정은 곡 반영(`_song_readback_requests`)만 고쳤다. 같은 「state 자식에서 속성 찾기」 모양이 다른 경로에도
  있는지는 전수로 세지 않았다.
- **큐가 많을 때 비용**: 큐마다 `props` 1회를 더 보낸다(Rain 13회). 큐가 수백 개인 곡의 되읽기 시간은 재지 않았다.
- **전체 시험 스위트**: 영향받는 185파일만 돌렸다. 전체는 CI 가 PR head 에서 돈다.

## 4. 증거 파일

`.moai/reports/t479/` — `pytest_red.txt` · `pytest_green.txt` · `affected_tests.txt` · `pytest_affected.txt` ·
`live_readback_check.py` · `live_readback_check.txt` · `audit/`(실기 읽기 감사 로그)
