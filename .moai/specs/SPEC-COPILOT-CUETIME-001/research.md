# SPEC-COPILOT-CUETIME-001 — 조사 기록 (scout 3 병렬, 2026-08-14)

## 문법 (CueGrammarScout)

- `Store Cue 5 Fade 3` — 00_grammar.md:56,69; corpus.yaml:76 (측정 코퍼스 검증).
- `Store Sequence 11 Cue 1 'Warm Wash' CueFade 2` — 31_choreography:50.
  추가 큐 `/Merge`(:55) — 단, 페이저 평탄화 함정 때문에 포지션 작업엔 금지.
- 소수점 큐 번호 삽입(1.5) — 31_choreography:56. MIB 선행 큐에 사용.
- `Set Cue 1 Sequence 11 Property 'TrigType' 'Follow'` / `'TrigTime' 4` —
  31_choreography:111-112. `/trig=` 옵션형은 2.4.2 거부(:115-117).
- 안전 게이트: `/Merge`는 블랙리스트 아님(자동 실행 가능), `Store /overwrite`·
  `Delete`는 블랙리스트(blacklist.yaml:62-68). 약어 매칭 ≥3자(classify.py:5-9).
- MIB/Move In Black — 룰북·server/ 전체 그렙 0건. 새 실측 대상.
- 큐 빌드 규칙: Position 프리셋 존재 시 값 재계산 금지, 프리셋 리콜로 빌드 —
  32_spatial_design.md:167-170.

## 세션 심 (SessionScout)

- 라우팅(run_instruction, session.py:1690): elevation → basic_presets(1705) →
  look(1707) → point(1709) → mood(1711) → 레이아웃 → 모델 폴백.
- 프리셋 저장 체이닝: `_LOOK_PRESET_STORE`(:165) → `_look_pan_tilt`:908-917에서
  commands.extend 후 단일 run_commands dispatch(918-920). T1 큐 저장의 병렬
  분기 모델.
- 질문 카드: `_ask_one`(:1820-1849) 블로킹, 무응답 → `_pointing_refusal`(:716)
  no-op. 파괴적 번호는 카드로 질의가 관례(`_basic_position_presets`:1044-1060).
- 모든 콘솔 쓰기 = `registry.dispatch(ToolCall(name='run_commands'))`, 승인
  게이트는 dispatch 내부 동기.

## songcue 심 (SongcueScout)

- `prepare_songcue`(tools.py:1840): sections(name+start) → 섹션당 5줄
  (`ClearAll`/`Group…`/values/`Store Sequence n Cue m 'name'`/`ClearAll`),
  선행 `ChangeDestination Root`. **CueFade 현재 미사용** — T1/T3 확장 지점 =
  songcue.py:461-467 commands 튜플.
- 큐 번호 enumerate start=1, 이름 `_cue_names`(ASCII 정규화·중복 접미).
- 시퀀스 번호 = 최소 미사용(select_sequence_number:290), 실행은 run_commands
  재진입(tools.py:2023), 성공 후 requery 검증.
- 타이밍 축 패턴: `SongCueTimingAxes` DESCOPE 플래그(songcue.py:104-113) —
  timecode/auto_advance처럼 MIB 축 추가 가능.
- 디머 판독(T2): `SongCueSectionBundle.selection.look.attributes`의
  name=='Dimmer' 값, `stored_sections`가 저장된 큐 순서 제공.
- **검증 한계**: CueFade/TrigType은 state snapshot 부재 —
  songcue_report.py:16 PROPERTY_UNOBSERVED_NOTE. readback은 responder prop
  (test_responder_roundtrip.py:197-203에 CueFade prop 왕복 실증).
