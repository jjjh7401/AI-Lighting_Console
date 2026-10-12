# 카드 t614 진행 기록 — 한 타임코드에 시퀀스 여러 개 배정

카드: 박자 격자 — 한 타임코드에 두 번째 시퀀스 배정이 거절된다 (Class B: run → sync).
브랜치: WT-timecode-multi-assign (base: origin/main 9dbc2445)
구현 커밋: 8d55331d

## 요약

- 원인: `beat_grid_emit.py` 가 모든 트랙을 맨 꼴 `Assign Sequence S At Timecode N` 으로 배정했다. 실기에서 맨 꼴의 첫 배정은 받아들여졌고, 같은 타임코드의 둘째 맨 꼴 배정은 `Illegal object` 로 거절됐다.
- 문법 근거: `Store Timecode N.1` 뒤의 `Assign Sequence S At Timecode N.1.k` 꼴이다. N.1 은 트랙 그룹 1, k 는 트랙 순번이다. 실기 OK 선례가 여럿이고, 한 타임코드에 트랙을 여럿 넣은 것은 t553(8트랙)·t520(2트랙)·t516(2트랙, 판정 기록)이다.
- 수정: 에미터가 트랙 순번 k 로 `N.1.k` 를 내고, 설정 줄에 `Store Timecode N.1` 을 더했다.
- 정리(cleanup): 원인은 확정했다. 그러나 정리 목록을 만드는 코드는 이 저장소의 추적 파일이 아니다(§4). 이 PR 에서는 고치지 않았다.

## 1. 조사 근거 (출처와 원문)

모든 줄 번호는 이 워크트리(origin/main 9dbc2445) 기준이다.

1. 실기 맨 꼴 배정 실패 — `.moai/reports/t608/v2/run-S1b.jsonl` (주 체크아웃, 추적 안 됨)
   - index 3: `Assign Sequence 702 At Timecode 70` → `"status": "ok", "detail": "OK"`
   - index 6: `Assign Sequence 703 At Timecode 70` → `"status": "failed", "detail": "Illegal object"`
   - 같은 실행의 `Store Sequence 702`·`703` 은 모두 OK. 실행은 index 6 에서 멈췄다(`"stopped_at": 6`).
   - 관측은 이 한 번이다. 맨 꼴 둘째 배정의 거절을 여러 번 재지는 않았다.
2. 정리 실패 — `.moai/reports/t608/v2/run-cleanup.jsonl`
   - index 8: `Delete Sequence 701 /NoConfirm` → `Illegal object`, `"stopped_at": 8`. 701 은 이 실행이 만든 적이 없다(§4).
3. 점 꼴 선례, t553 (8트랙, 실기 OK) — `.moai/reports/t553/live_p1b.stdout.txt` 2·3·6·8~15행
   - `Store Timecode 32` → OK · `Store Timecode 32.1` → OK
   - `Assign Sequence 226 At Timecode 32.1.1` 부터 `Assign Sequence 233 At Timecode 32.1.8` 까지 여덟 줄 모두 OK
   - 줄 순서(2행 화면 목록): Store Timecode N → Set Name → Set Duration → Store Timecode N.1 → Assign ×8
4. 점 꼴 선례, t520 (2트랙, 실기 OK + 되읽기) — `.moai/reports/t520/live_write_b2/steps.jsonl` 564~571행
   - `Store Timecode 24.1` → OK → `Assign Sequence 269 At Timecode 24.1.1` → OK → `Assign Sequence 270 At Timecode 24.1.2` → OK
   - 571행 되읽기(`post_a_group`): `TrackGroup 1` 자식 3 — `MarkerTrack "Marker"`, `Track 2 "… SCENE"`, `Track 3 "… RHYTHM"`.
5. 점 꼴 선례, t506 (1트랙, 실기 OK) — `.moai/reports/t506/live_write/steps.jsonl` 9행
   - `Assign Sequence 9 At Timecode 14.1.1` → `"ok": true, "detail": "OK"`. 승인 목록에서는 바로 앞 줄이 `Store Timecode 14.1` 이다.
6. 점 꼴 판정 기록, t516 — `.moai/reports/t516/verdict.md` 104행
   - 「TC20/1 아래 Track 두 개: NO 1 → Sequence 220, NO 2 → Sequence 221. 두 번째 Assign … At Timecode 20.1.2 가 새 트랙을 만들었다」 — PASS. 판정 문서의 요약이다. 원자료 파일은 열어 보지 않았다.
7. 벤더 시험 코드 — 이 기계에 설치된 grandMA3 2.4.2 의 자체 시험 (저장소 밖, 읽기만): `/Users/studiox/MALightingTechnology/gma3_2.4.2/shared/resource/lib_plugins/systemtests/db/system_test_timecode_record.lua` 611~615행
   - `Set <TC> Property "Duration" 1 "AutoStop" 0` → `Store <TC>.1` → `Assign <seq> At <TC>.1.1` → `Store Type "CmdSubTrack" <TC>.1.1.1` → `cd <TC>.1.1.1.1`. 트랙 하나짜리 시험이다.
8. 공식 문서 — `https://help.malighting.com/grandMA3/2.4/HTML/timecode_track_groups.html`
   - 명령 예 `Select Timecode 1.2`. 설명: 「Track groups can also be selected via the command line. For example, select track group 2 of timecode show 1」. 가운데 숫자가 트랙 그룹 번호라는 뜻이다. 계층 점 표기는 `csk_parent_child` 페이지(「The dot (.) ends the selection on the current level and then steps one level down」)가 뒷받침한다. 배정 명령의 점 꼴 예는 공식 문서에 없다(Assign 페이지에 Timecode 예가 없다).
9. 저장소 이력 — `git log -S "At Timecode {timecode_number}"` 의 첫 커밋은 `b95a691a`(t549, 새 에미터)다. 점 꼴은 에미터 이력 어디에도 없었다.
10. M0 주석 — `server/tools/musicsync_m3a_probe.py` 42~45행: 맨 꼴 `Assign Sequence <s> At Timecode <n>` 은 `TrackGroup 1` 을 만든다.

## 2. 원인

`server/design/beat_grid_emit.py` 의 배정 줄은 트랙마다 맨 꼴이었다. 맨 꼴 배정은 첫 트랙에서만 받아들여졌고, 둘째 트랙부터 `Illegal object` 로 거절됐다. 그래서 앱의 「반영」 이 거기서 멈췄다.

## 3. 수정 (커밋 8d55331d)

- 트랙 k 의 배정 줄: `Assign Sequence {S} At Timecode {N}.1.{k}`. k 는 같은 타임코드에서 실제로 배정된 트랙의 1부터 세는 순번이다. 막혀서 배정 줄에 닿지 못한 트랙은 순번을 쓰지 않는다.
- 설정 줄: 타임코드마다 `Store Timecode {N}` · `Set Timecode {N} Property 'Name' …` 뒤에 `Store Timecode {N}.1` 한 줄을 더했다. 선례의 순서를 따랐다.
- 바꾸지 않은 것: Duration/AutoStop 줄, `beat_grid_send.py`(소유 재사용 시 설정·배정 줄을 빼는 로직), 다른 모듈.
- 테스트: 기존 기대값 두 곳(t549 한 곳, t612 한 곳)을 점 꼴로 고쳤다. 새 시험 모듈 `server/tests/test_beat_grid_timecode_track_t614.py` 는 8건이다.

## 4. 정리 (cleanup) — 원인 확정, 수정은 이 PR 밖

- 측정: `run-cleanup.jsonl` 8번째 줄(`Delete Sequence 701`)에서 멈췄다. 목록의 9~12행(`Delete Sequence 700 /NoConfirm`, `Delete Preset 22.97 /NoConfirm`, `Delete Preset 4.352 /NoConfirm`, 마지막 `ClearAll`)은 보내지 않았다.
- 원인: 정리 목록은 `.moai/reports/t608/v2/gen_payload.py` 823~832행이 만든다. 합본 전체에서 「만든 객체」를 뽑고, 그 객체 집합이 정리 집합과 같은지만 단언한다. 실행 결과(실제로 어디까지 만들어졌는지)는 보지 않는다. 실행이 중간에 멈추면 아직 없는 객체의 `Delete` 가 `Illegal object` 로 거절되고, 러너는 거기서 멈춘다. 뒤 줄은 나가지 않는다.
- 이 파일이 저장소 밖에 있는 이유: `gen_payload.py` 는 t608 기록이 밝혔듯 git 에 커밋하지 않은 주 체크아웃의 추적 안 되는 파일이다. 저장소의 추적 코드에는 정리 생성기가 없다(`server/design` 에 cleanup 문자열 0건).
- 제안 수정: 정리 줄을 합본이 아니라 실행 기록(`run-*.jsonl`)에서 만든다. 상태가 `ok` 로 기록된 만든 줄에 대응하는 객체만 `Delete` 한다. 순서는 만든 순서를 유지한다.
- 이 PR 에서 고치지 않은 이유: (가) 대상이 추적되지 않는 기록용 생성기다. (나) 주 체크아웃의 공유 경로를 이 레인이 고치면 격리 규칙에 어긋난다. (다) 정리 생성기를 추적 코드로 옮길지는 리드가 정할 일이다.

## 5. 재현 시험 (RED) 과 수정 후 (GREEN)

- RED (`.moai/reports/t614/red.txt`): 수정 전 새 시험 모듈 실행. 마지막 줄 `8 failed`, exit 1. 핵심 불일치(13행): `'Assign Sequence 300 At Timecode 30' != 'Assign Sequence 300 At Timecode 30.1.1'`.
- GREEN (`.moai/reports/t614/green.txt`): `8 passed`, exit 0.
- 관련 시험 (`.moai/reports/t614/related.txt`): `beat_grid_emit` 또는 `beat_grid_send` 를 import 하는 시험 모듈 15개. `263 passed, 1 warning`, exit 0.
- 린트 (`.moai/reports/t614/ruff.txt`): `ruff check` 통과, `ruff format --check` 4개 파일 이상 없음. 둘 다 exit 0.
- 리드 재실행 (주 체크아웃 밖, 스크래치 파일): 새 모듈과 편집한 두 모듈 `44 passed`, exit 0. 관련 15개 모듈 `263 passed, 1 warning`, exit 0.
- 전후 생성 줄: 전 `Assign Sequence 300 At Timecode 30` → 후 `Assign Sequence 300 At Timecode 30.1.1`. 둘째 트랙은 `…30.1.2`. 설정 줄에는 `Store Timecode 30.1` 이 `Set Timecode 30 Property 'Name' …` 뒤에 한 번 들어간다.
- 차단 칸 판단: 칸 하나만 차단된 트랙은 배정 줄이 그대로 나가므로 순번을 쓴다(시험 e 로 고정). 트랙 전체가 차단되면(검토 안 된 그룹, 시퀀스 번호 없음) 배정 줄이 없으니 순번을 쓰지 않는다.

## 6. 검증하지 않은 것 (Gaps)

- 실기 콘솔 송신은 하지 않았다(카드 지시). 점 꼴 배정의 실기 확인은 리드가 한다.
- Duration/AutoStop 줄은 넣지 않았다. 선례 넷(t506·t516·t520·t553)은 모두 `Store … .1` 앞에 Duration 줄을 두었다. 그 줄 없이 배정이 되는지는 재지 않았다. 곡 길이 값이 에미터 입력에 없어서 이번에는 넣지 않았다. 리드가 실기 확인 때 먼저 볼 항목이다.
- `Store Timecode N.1` 을 뺀 변형은 재지 않았다. 선례 순서를 그대로 따랐다.
- 전체 시험 스위트는 로컬에서 돌리지 않았다. 관련 15개 모듈만 돌렸고, 전체는 CI 에 맡긴다.
- 승인 목록 재생성(`gen_payload.py` 실행)은 하지 않았다. 생성기 출력의 전후 줄만 시험 출력으로 확인했다.
- 조사 에이전트가 읽은 파일은 주 체크아웃의 옛 커밋(efb40e03) 것이었다. 그 줄 번호는 이 워크트리와 달라서 이 기록에 쓰지 않았다.
- 「By default, tracks are added to the same Track Group」 이라는 문장은 확인하지 못했다. 이 기록에 인용하지 않는다.

## 7. 잔여 위험

- 점 꼴 배정이 실기에서 막히면, 이 PR 을 되돌리면 이전의 맨 꼴로 돌아간다(한 트랙만 살아남는다).
- 이미 승인된 목록 가운데 맨 꼴 배정을 담은 것은 이 수정과 맞지 않는다. 다시 생성해야 한다.
- 정리(§4)가 고쳐지기 전에는 실기 정리 실행이 같은 방식으로 멈출 수 있다.

## 8. PR · CI · 머지

- PR 번호, CI 결과, 머지 커밋은 PR 페이지와 머지 기록, 그리고 완료 보고에 있다.
- 이 문서에는 자기 CI 결과를 적지 않는다. 기록 커밋이 head 를 밀어서, 적힌 결과가 곧 낡기 때문이다.
