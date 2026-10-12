# 카드 t614 진행 기록 — 한 타임코드에 시퀀스 여러 개 배정

카드: 박자 격자 — 한 타임코드에 두 번째 시퀀스 배정이 거절된다 (Class B: run → sync).
브랜치: WT-timecode-multi-assign (base: origin/main 9dbc2445)

## 요약

- 원인: `beat_grid_emit.py` 가 모든 트랙을 맨 꼴 `Assign Sequence S At Timecode N` 으로 배정했다. 실기에서 맨 꼴의 첫 배정은 받아들여졌고, 같은 타임코드의 두 번째 맨 꼴 배정은 `Illegal object` 로 거절됐다.
- 문법 근거: 실기 선례는 `Store Timecode N.1` 뒤의 `Assign Sequence S At Timecode N.1.k` 꼴이다 (트랙 k 번째, 트랙 그룹 1). 한 타임코드에 시퀀스 여러 개가 들어간 실기 선례는 t520 이다.
- 수정: 에미터가 트랙 순번 k 로 `N.1.k` 를 내고, 설정 줄에 `Store Timecode N.1` 을 더했다.
- 정리(cleanup): 원인은 확정했다. 그러나 정리 목록을 만드는 코드는 이 저장소의 추적 파일이 아니다(§4). 이 PR 에서는 고치지 않았다.

## 1. 조사 근거 (출처와 원문)

1. 실기 맨 꼴 배정 실패 — `.moai/reports/t608/v2/run-S1b.jsonl` (주 체크아웃, 추적 안 됨)
   - index 3: `"line": "Assign Sequence 702 At Timecode 70"` → `"status": "ok", "detail": "OK"`
   - index 6: `"line": "Assign Sequence 703 At Timecode 70"` → `"status": "failed", "detail": "Illegal object"`
   - 같은 실행에서 `Store Sequence 702`·`703` 은 모두 `OK`. 실행은 index 6 에서 멈췄다(`"stopped_at": 6`).
   - 관측은 이 한 번이다. 맨 꼴 두 번째 배정의 거절을 여러 번 재지는 않았다.
2. 정리 실패 — `.moai/reports/t608/v2/run-cleanup.jsonl`
   - index 8: `"line": "Delete Sequence 701 /NoConfirm"` → `"status": "failed", "detail": "Illegal object"`
   - `"event": "end", "sent": 8, "stopped_at": 8, "status": "stopped"`. 701 은 이 실행이 만든 적이 없다(§4).
3. 점 꼴 선례 (t520, 실기 OK) — `.moai/reports/t520/live_write_b2/steps.jsonl` 564~570행
   - `Store Timecode 24` → OK · `Set Timecode 24 Property 'Name' …` → OK · `Set Timecode 24 Property 'Duration' 62 'AutoStop' 0` → OK
   - `Store Timecode 24.1` → OK
   - `Assign Sequence 269 At Timecode 24.1.1` → OK
   - `Assign Sequence 270 At Timecode 24.1.2` → OK
   - 571행 되읽기(`post_a_group`): `TrackGroup 1` 자식 3 — `MarkerTrack "Marker"`, `Track 2 "<LOVE ATTACK - RHYTHM M2a B2 SCENE>"`, `Track 3 "<LOVE ATTACK - RHYTHM M2a B2 RHYTHM>"`. 한 타임코드에 시퀀스 두 개가 두 트랙으로 살아 있다.
4. 점 꼴 선례 (t506, 실기 OK) — `.moai/reports/t506/live_write/steps.jsonl` 9행
   - `Assign Sequence 9 At Timecode 14.1.1` → `"ok": true, "detail": "OK"` (앞줄 `Store Timecode 14.1` 뒤)
5. 점 꼴 승인 목록 (t553) — `.moai/reports/t553/approval_t553.txt` 5~9행
   - `Assign Sequence 226 At Timecode 32.1.1` … `Assign Sequence 230 At Timecode 32.1.5` (8트랙까지 `32.1.8`). `beat_grid_emit.py` 110~113행의 주석은 타임코드 32, 트랙 8 을 실기 되읽기 값으로 적는다.
6. M0 주석 — `server/tools/musicsync_m3a_probe.py` 42~45행: 맨 꼴 `Assign Sequence <s> At Timecode <n>` 은 `TrackGroup 1` 을 만든다.
7. 저장소 이력 — `git log -S "At Timecode {timecode_number}"` 의 첫 커밋은 `b95a691a`(t549, 새 에미터)다. 점 꼴은 에미터 이력 어디에도 없다.

## 2. 원인

`server/design/beat_grid_emit.py` 의 배정 줄은 트랙마다 맨 꼴이었다. 맨 꼴은 첫 트랙에서만 받아들여진다(§1-1). 두 번째 트랙부터 `Illegal object` 로 거절되고, 앱의 「반영」 은 거기서 멈춘다.

## 3. 수정 (이 PR)

- 트랙 k 의 배정 줄: `Assign Sequence {S} At Timecode {N}.1.{k}` (k 는 같은 타임코드에서 실제로 배정된 트랙의 1부터 세는 순번).
- 설정 줄: 타임코드마다 `Store Timecode {N}` · `Set Timecode {N} Property 'Name' …` 뒤에 `Store Timecode {N}.1` 한 줄을 더했다. 선례(t520·t506)의 순서를 따랐다.
- 바꾸지 않은 것: Duration/AutoStop 줄, `beat_grid_send.py`(소유 재사용 시 설정·배정 줄을 빼는 로직), 다른 모듈.

## 4. 정리 (cleanup) — 원인 확정, 수정은 이 PR 밖

- 측정: `run-cleanup.jsonl` 8번째에서 멈췄다. 목록의 9~12행(`Delete Sequence 700 /NoConfirm`, `Delete Preset 22.97 /NoConfirm`, `Delete Preset 4.352 /NoConfirm`, 마지막 `ClearAll`)은 보내지 않았다.
- 원인: 정리 목록은 `.moai/reports/t608/v2/gen_payload.py` 823~832행이 만든다. 합본 전체에서 「만든 객체」를 뽑고, 그 객체 집합이 정리 집합과 같은지만 단언한다. 실행 결과(어디까지 실제로 만들어졌는지)는 보지 않는다. 그래서 실행이 중간에 멈추면 아직 없는 객체의 `Delete` 가 `Illegal object` 로 거절되고, 러너는 거기서 멈춘다. 뒤의 정리 줄은 영영 나가지 않는다.
- 이 파일이 저장소 밖에 있는 이유: `gen_payload.py` 는 t608 기록 문서가 밝혔듯 git 에 커밋하지 않은 주 체크아웃의 추적 안 되는 파일이다. 저장소의 추적 코드에는 정리 생성기가 없다(`server/design` 에 cleanup 문자열 0건).
- 제안 수정: 정리 줄을 합본이 아니라 실행 기록(`run-*.jsonl`)에서 만든다. 상태가 `ok` 로 기록된 「만든 줄」에 대응하는 객체만 `Delete` 한다. 순서는 만든 순서를 유지한다.
- 이 PR 에서 고치지 않은 이유: (가) 대상 파일이 추적되지 않는 기록용 생성기다. (나) 주 체크아웃의 공유 경로를 이 레인이 고치면 격리 규칙에 어긋난다. (다) 정리 생성기를 추적 코드로 옮길지 말지는 리드가 정할 일이다.

## 5. 재현 시험 (RED) 과 수정 후 (GREEN)

(작업 중 — 아래 파일에 원문 출력이 있다)
- `.moai/reports/t614/red.txt` — 수정 전 재현 시험
- `.moai/reports/t614/green.txt` — 수정 후 같은 시험
- `.moai/reports/t614/related.txt` — 배정 줄을 쓰는 관련 시험 모듈 전부
- `.moai/reports/t614/ruff.txt` — 린트·서식 검사

## 6. 검증하지 않은 것 (Gaps)

- 실기 콘솔 송신은 하지 않았다(카드 지시). 점 꼴 배정의 실기 확인은 리드가 한다.
- Duration/AutoStop 줄은 넣지 않았다. t520·t506 은 넣었다. 넣지 않은 상태의 실기 동작은 재지 않았다.
- `Store Timecode N.1` 을 뺀 변형은 재지 않았다. 선례 순서를 그대로 따랐다.
- 전체 시험 스위트는 로컬에서 돌리지 않았다. 관련 모듈만 돌렸고, 전체는 CI 에 맡긴다.
- 승인 목록 재생성(`gen_payload.py` 실행)은 하지 않았다. 생성기 출력의 전후 줄만 시험 출력으로 확인했다.
- 웹 문서 조사: 조사 에이전트 결과가 오기 전이다. 결과가 오면 여기에 출처를 붙인다.

## 7. 잔여 위험

- 점 꼴 배정이 실기에서 막히면, 이 PR 을 되돌리면 이전의 맨 꼴로 돌아간다(한 트랙만 살아남는다).
- 이미 승인된 목록 가운데 맨 꼴 배정을 담은 것은 이 수정과 맞지 않는다. 다시 생성해야 한다.
- 정리(§4)가 고쳐지기 전에는 실기 정리 실행이 같은 방식으로 멈출 수 있다.
