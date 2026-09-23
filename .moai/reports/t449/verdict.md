# t449 판정서 — 프리셋 번호 결함의 네 번째 경로(무드 인터뷰 포지션 큐 시트)

- 카드: t449 (클래스 B — 원인은 t232 판독으로 이미 확정, 이 경로만 남음)
- 브랜치: `WT-cuesheet-preset-label`, 기준 `origin/main` f898d8a2
- 콘솔 쓰기: 0 (재현·테스트 모두 FakeConsole/대역 레지스트리)

## 1. 주장

`server/spatial/position_cuesheet.py` 의 `build_position_cue_sheet` 는 프리셋 번호를
`preset_start + BASIC_POSITION_SEQUENCE.index(label)` 로 계산했고, 그 슬롯에 실제로 그
라벨이 있는지는 확인하지 않았다. 이 카드는 t232(PR #490)가 곡 큐·대화 포지션 수정·포지션
FX 세 경로에 적용한 규율을 네 번째 경로에도 똑같이 적용한다.

- 빌더는 `preset_start` 대신 `preset_numbers: Mapping[str, int]` 를 받는다.
- 새 순수 함수 `required_sheet_labels(sections)` 가 시트가 부를 라벨을 미리 알려준다.
  빌더와 같은 선택 규칙(`_section_looks` — 암전·건너뜀·대안 회전)을 공유하므로 두 결과가
  어긋날 수 없다.
- 세션 `_position_cue_sheet` 는 그 라벨들을 `_resolve_position_preset_labels` 로 풀 1회
  판독해 실제 슬롯을 찾는다. 라벨이 없거나 모호하면 사유를 붙여 거절하고, 콘솔 쓰기는
  한 줄도 나가지 않는다.
- 설계층 래퍼 `build_standard_position_cue_sheet` 도 같은 인자로 바꿨다(운영 코드 호출처 0,
  테스트만 호출).

## 2. 증거

### 2.1 수정 전/후 재현 — `repro_cuesheet_path.py`

같은 스크립트를 수정 전 트리와 수정 후 트리에서 그대로 실행했다(진입점
`_position_cue_sheet(text)` 의 호출 형태는 바뀌지 않았다).
출력: `repro_cuesheet_path.before.txt` / `repro_cuesheet_path.after.txt`.

| 상태 | 쇼파일 | 수정 전 | 수정 후 |
|---|---|---|---|
| C | 기본 10종이 1~10 (정상) | 2.5 / 2.8 | **바이트 동일** (diff 없음) |
| D | 1~10 은 시트 프리셋, 진짜 기본 10종은 41~50 | 2.5 / 2.8 — `POS05 시트`·`POS08 시트`를 부름 | 2.45 / 2.48 — 진짜 Vocal DSC·Cross |
| D2 | 1~10 은 시트 프리셋, 기본 10종 없음 | 2.5 / 2.8 로 8줄 전송 | 거절, 전송 0줄 — `'Vocal DSC' 라벨의 Position 프리셋을 콘솔에서 찾지 못했습니다` |

`diff before after` 는 상태 D·D2 줄에서만 차이가 났고, 상태 C 구간(1~16행)은 차이가 없다.

### 2.2 테스트

- 새 테스트 7개:
  - `test_position_cuesheet.py::TestLabelResolvedPresetNumbers` 4개 — 라벨 목록이 빌더가
    실제로 부르는 라벨과 같은지, 산술 대신 해석된 슬롯을 부르는지, 번호가 없으면 거절하는지.
  - `test_web_session.py::TestPositionCueSheetSession` 3개 — 시트 프리셋이 21~30 을 차지한
    쇼파일에서 2.45/2.48 을 부르는지, 라벨 없음·모호일 때 `run_commands` 0건으로 거절하는지.
- **대조군**: 소스 3개만 수정 전으로 되돌리고 세션 테스트를 돌렸다 →
  `3 failed, 4 passed`. 새 세션 테스트 3개가 바로 이 결함을 잡는다는 뜻이다(공허한 테스트가
  아님). 원래 있던 4개는 두 트리 모두에서 통과한다.
- 기존 테스트 수정: `preset_start=21` → `preset_numbers=_NORMAL_POOL_21` (정상 쇼파일을 라벨
  조회한 결과, 옛 번호와 같은 값). `preset start` 거절 검사는 `must be positive`(해석된 번호
  0) 검사로 바꿨다. 세션 테스트 대역 레지스트리에는 정상 풀(21~30) 판독 응답을 추가했다.
- 영향 범위 테스트 18개 파일: `902 passed, 23 skipped`.
- `ruff check` / `ruff format --check`: 변경 파일 전부 통과.

## 3. 기준선 귀속

- 모든 측정은 이 워크트리(`.claude/worktrees/t449`), 기준 f898d8a2 + 이 카드 변경분에서 했다.
- 재현 스크립트는 `sys.path` 맨 앞에 자기 트리를 얹어 메인 체크아웃 임포트 함정을 피한다
  (t232 repro 와 같은 방식).

## 4. 안 잰 것

- **실기 콘솔은 0회.** 풀 판독 응답은 가짜다. 실기 풀 판독(`_position_preset_pool_children`)
  자체는 t232 에서 쓰는 경로라 새로 만든 부분은 없다.
- 전체 테스트는 로컬에서 돌리지 않았다(레인 규약 — 전체는 CI 가 PR head 에서 돈다).
- `build_standard_position_cue_sheet` 는 운영 코드 호출처가 0이라 세션 경로로는 재현하지
  않았다. 시그니처만 맞췄다.

## 5. 남은 위험

- **동작 변화(의도됨)**: 라벨 없이 손으로 저장한 포지션 프리셋(이름이 `Vocal DSC` 등이 아님)은
  이제 이 경로에서도 거절된다. 예전에는 번호만 맞으면 조용히 불렀다. t232 가 세 경로에 남긴
  부작용과 같다.
- 풀 판독이 실패하면 시트 전체가 거절된다(예전에는 풀을 읽지 않고 저장했다). 판독 실패와
  라벨 부재는 서로 다른 사유 문구로 구분된다.

## 6. 남은 산술 경로 전수 확인

- `git grep -n "SEQUENCE.index(" -- server ':!server/tests'` → 1건.
  `session.py` 의 `_resolve_position_preset_labels` 독스트링이 옛 방식을 설명하는 문장뿐이다.
- `git grep -nE "(preset_start|fx_preset_start|_start) \+ " -- server ':!server/tests'` →
  프리셋을 부르는 번호 산출은 0건. `session.py` 의 `fx_preset_start + len(...) - 1` 은 조회
  구간의 끝을 계산할 뿐이고, 나머지는 시간·시퀀스·청크 계산이다.
- 결론: 이 저장소의 운영 코드에서 `시작 번호 + 순서` 로 포지션 프리셋을 부르는 경로는 이
  카드로 네 곳 모두 닫혔다(t232 세 곳 + t449 한 곳).
