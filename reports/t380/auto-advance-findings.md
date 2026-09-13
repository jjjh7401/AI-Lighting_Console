# t380 — 자동 진행(auto-advance) 조사 결과

## 결론 먼저

**자동 진행은 이미 구현되어 있고, 실기로 측정됐고, 실제 서비스 경로에 배선돼
있다.** 오늘 현장에서 "리듬에 안 맞는다"고 관측된 원인은 기능 부재가 아니라
**진단 스크립트가 그 기능을 켜는 별도 호출을 하지 않았기 때문**이다 — 아래에서
코드와 실기 기록으로 증명한다.

이 결론에 이르기 전에 카드 본문의 전제("자동 진행이 없다", "단위를 골라야
한다")를 먼저 검증해야 했다 — 검증 없이 새로 만들었다면 이미 있는 것을
중복해서 만드는 일이 됐을 것이다.

## 1. 코드가 이미 하는 일

- `server/looks/songcue.py` `_auto_advance_commands(bundle)` — 저장된 큐마다
  `Set Cue <n> Sequence <s> Property 'TrigType' 'Time'` +
  `Set Cue <n> Sequence <s> Property 'TrigTime' <초>` 두 줄을 만든다. `<초>`는
  그 큐가 대표하는 구간의 **자기 시작 시각**(`section.start_ms`, 밀리초→초
  변환은 `_format_seconds`)이다.
- `build_songcue_timing(bundle, timecode_number, axes)` 가 이 함수를
  `SongCueTimingAxes.auto_advance_go`(기본값 `True`) 아래 묶어 부른다 —
  타임코드 축(`timecode_go`)과 **독립**이라, 타임코드 풀 조회가 실패해도 자동
  진행 축은 죽지 않는다(`server/tests/test_songcue_tool.py
  ::test_the_auto_advance_axis_survives_a_dead_timecode_pool`).
- `prepare_songcue` 툴(`server/orchestrator/tools.py:3242` 부근)이
  `timing = build_songcue_timing(bundle, timecode_number=timecode_number,
  axes=axes)` 를 부르고, `command_bundle = bundle.commands + timing.commands`
  를 **`run_commands` 로 콘솔에 직접 쏜다**. 이것이 앱이 실제로 서비스하는
  "곡 큐 만들기" 경로다.
- 마디 기반 큐 분할(`server/design/cue_density.py`
  `split_selections_for_density`)과도 이미 맞물려 있다 — 쪼갠 큐마다
  `section = replace(source.section, start_ms=split.start_ms)` 로 **자기만의**
  시작 시각을 받고, `_auto_advance_commands` 는 그 값을 그대로 읽는다
  (`server/tests/test_songcue_cue_density.py
  ::test_cues_outnumber_sections_at_bar_derived_offsets` 가 오프셋 다섯 개를
  전부 단언한다).

## 2. 실기로 이미 확정된 것

- **문형 자체**: `TrigType 'Time'` · `TrigTime <n>` 둘 다 `ok=True` / `OK` —
  SONGCUE-001 M0 측정 4(`progress.md:373-379`), MUSICSYNC-001 spec.md:45 가
  재확인.
- **의미론(절대 vs 상대)**: SONGCUE-001 progress.md "Gap 1 폐쇄" 절
  (`:491-502`) — Cue 1 에 `TrigTime 10`, Cue 2 에 `TrigTime 14` 를 **일부러
  다른 값으로** 심고 `prop` 경로로 되읽었다. 값이 그대로 `"14.0"` 으로
  읽혔다(직전 큐 기준 상대 지연이면 `"4.0"` 이 나와야 한다). **판정: `TrigTime`
  은 시퀀스 시작 기준 절대 초다.** 지금 구현이 각 구간의 절대 `start_ms` 를
  그대로 쓰는 것과 정확히 일치한다 — 우연이 아니라 이 실측을 따른 설계다.

## 3. 단위 — 마디냐 초냐 (카드가 명시적으로 물은 질문)

**초다. 그리고 이미 그렇게 돼 있다.** 근거:

- 정본 §9(큐 밀도와 타이밍)는 **몇 개의 큐를 어디에 놓을지**(프레이즈 단위
  4~8마디)를 마디로 말하지, 트리거 명령의 시간 단위를 마디로 쓰라고 말하지
  않는다. 마디는 **큐를 몇 개 놓을지 정하는 상류 결정**이고, `cue_density.py`
  가 이미 그 결정을 마디로 한다.
- `TrigTime` 은 콘솔 프로퍼티이고 위 §2 에서 실측했듯 **초 단위 절대 시각**을
  받는다 — 콘솔이 받는 형이 초이므로, 상류에서 이미 정확한 초(그 구간의 실제
  분석 시작 시각)를 알고 있는데 마디로 되짚어 계산해 다시 초로 바꾸는 것은
  **불필요한 왕복이자 반올림 오차의 새 원천**이다.
- `_pre_drop_darkened` 독스트링(`songcue.py:1330-1338`)이 이미 이 구분을
  적어 뒀다 — "마디가 필요한 경우"는 **아직 시각이 없는 새 큐를 끼워 넣을
  때**(드롭 앞 긴장 큐 같은)뿐이고, 그때는 조립 단계가 BPM 을 안 받아서 마디
  산술을 할 수 없다고 명시돼 있다. 지금 자동 진행이 쓰는 큐는 전부 **이미
  분석으로 시작 시각을 아는** 큐라 이 문제가 아예 생기지 않는다.

결론: 두 단위는 서로 다른 층에 있다 — **마디는 큐를 몇 개 만들지**를 정하고,
**초는 이미 만들어진 큐를 언제 발화할지**를 정한다. 하나로 합칠 이유가 없고,
합치면 오히려 §9 의 실무 규칙(마디)과 콘솔 프로퍼티의 실측 계약(초)을 둘 다
어기게 된다.

## 4. 오늘 현장 관측이 실제로 일어난 이유

`reports/onsite-round-20260912/real_song_cues.py` (커밋 `aafefa6`)와
`diag.py` 둘 다 `build_songcue_bundle(...)` 만 부르고 `stack.gate
.execution_port.execute(c)` 로 `b.commands` 를 그대로 쐈다 —
`build_songcue_timing()` 을 부르지 않았다. `build_songcue_bundle` 는 설계상
타이밍 축을 전혀 안 낸다(룩/다이내믹스 조립만 한다) — `build_songcue_timing`
이 별도 함수인 이유가 바로 이 분리다. 그래서 발사된 90줄에 `Timecode` /
`TrigTime` / `Follow` 가 정말 0건이었고 — 그 관측 자체는 정확했다 — 다만
원인이 "기능이 없다"가 아니라 "이 진단 스크립트가 그 기능을 켜는 두 번째 호출을
안 했다"였다.

## 5. 이번에 한 일 (production 코드는 건드리지 않았다)

- `reports/onsite-round-20260912/diag.py` 를 고쳐 `build_songcue_timing()` 도
  부르고 `b.commands + timing.commands` 를 "음악 동기" 검사에 쓰게 했다 —
  `prepare_songcue` 가 실제로 쏘는 조합과 같다. `songcue.py` 는 한 줄도 안
  건드렸다(형제 레인 t377/t378 이 그 파일을 고치는 중이라 접촉면을 0으로
  뒀다).
- `server/tests/test_songcue_timing.py` 에 회귀 시험 두 개를 더했다
  (`TestBundleAloneCarriesNoTiming`) — `build_songcue_bundle` 혼자서는 동기
  줄이 0건이라는 것과, `build_songcue_timing` 과 합치면 저장된 큐 수만큼
  정확히 한 쌍씩 나온다는 것을 기계로 고정한다. 오늘 같은 착시가 다음에
  재발하지 않도록.

## 잔여 위험 (미검증 — 숨기지 않는다)

- **자동 발화 그 자체(스스로 GO 없이 다음 큐로 넘어가는가)는 아직 아무도
  실측하지 않았다.** SONGCUE-001/MUSICSYNC-001 이 실측한 것은 (a) 명령이
  콘솔에 받아들여진다는 것과 (b) 프로퍼티 값이 그대로 되읽힌다는 것 둘뿐이다
  — 시퀀스를 실제로 재생시켜 두 번째 큐가 사람 개입 없이 저절로 발화하는지를
  본 기록은 어디에도 없다. 이것은 이번 카드가 채우는 자리가 아니다 — "콘솔
  쓰기 0건" 경계를 지켰기 때문이다. 다음 실기 라운드에서 DinoDino 시퀀스를
  Go+ 한 번만 눌러 재생시키고 Cue 2 가 t=14s 부근에서 스스로 넘어가는지
  관측하는 것이 유일하게 남은 검증이다.
- 이 조사는 `real_song_cues.py`/`diag.py` 두 스크립트만 확인했다 — 현장에서
  실제로 쓰인 UI 채팅 경로(`prepare_songcue` 를 통했는지)는 오늘 로그에서
  직접 확인하지 못했다. 다만 코드상 채팅 경로는 `prepare_songcue` 하나뿐이고
  그 경로는 이미 `timing.commands` 를 포함하므로, 실제 서비스 경로 자체가
  기능을 빠뜨렸을 가능성은 낮다고 본다(추정 — 로그로 확정하지 않았다).
