# SPEC-COPILOT-CUETIME-001 — 포지션 큐 시간축 (트랜지션·MIB·곡 시트)

- 브랜치: `feature/position-cue-timeline` (main `614eab9`에서 분기)
- 근거 문서: `handoff/2026-08-14-position-cue-timeline-kickoff.md`,
  `docs/proposals/pan-tilt-position-preset-strategy.md`,
  `.claude/skills/ma3-spatial-pointing/SKILL.md`
- 상태: T1 진행 중

## 배경

정지 포지션 룩(Preset 2.21~2.30)을 시간 위의 연출로 확장한다. 세 과제는
의존 사슬(T1→T2→T3)이며, 라이브 검증 자원이 단일(onPC 1대, hub 서버 1개)
이므로 구현·검증은 직렬로 수행한다 (조사만 병렬 스카우트로 완료).

## 요구사항 (GEARS)

### T1. 포지션 큐 트랜지션 (Fade)

- **G**: "빔이 천천히 넘어가는" 포지션 전환 — 포지션 프리셋 참조 큐를
  페이드 시간과 함께 저장.
- **E**: 사용자가 "프리셋 N(포지션)을 시퀀스 S 큐 C로 저장, 페이드 F초"류
  지시를 하면,
- **A**: 세션이 `Fixture <sel> ; At Preset 2.<N>` 리콜 → `Store Sequence S
  Cue C '<name>' CueFade F` → `ClearAll` 번들을 승인 게이트 경유로 실행한다.
- **R1**: 큐는 반드시 프리셋 **참조**로 저장 (프로그래머에 프리셋 리콜 상태) —
  32_spatial_design.md:167-170.
- **R2**: 시퀀스 번호 미지정 시 `_ask_one` 질문 카드 1장 (Store는 기존 큐를
  덮을 수 있으므로 운영자 결정). 무응답 → 거절(no-op). 큐 번호 미지정 시 1.
- **R3**: 페이드 미지정 시 CueFade 항 생략 (콘솔 기본). 페이드는 0 이상
  유한값만 허용.
- **R4**: `/Merge`·`/Overwrite` 미사용 — 페이저 평탄화 함정(SKILL §3)과
  블랙리스트(`Store /overwrite`) 회피. 빈 큐 슬롯 전제.
- **S**: 검증 — 유닛(빌더 문법·거절 경계) + 세션 테스트(카드·번들) +
  라이브: `Go+`로 페이드 중간 프레임과 완료 프레임의 3D 픽셀 diff ≠ 0,
  responder `prop`으로 `CueFade` readback == F (CueFade는 state snapshot에
  없음 — songcue_report.py:16).

### T2. MIB (Move In Black)

- **G**: 이전 큐 디머 0이면 다크 상태에서 포지션 선이동 — 헤드 허우적거림 제거.
- **E**: 큐 시퀀스 생성(T1 저장 또는 T3 시트)에서 큐 k의 디머가 0이고
  큐 k+1이 새 포지션 + 디머 >0이면,
- **A**: "포지션 선행 큐(디머 0 + 포지션, 소수점 번호 k.5) → 본 큐(디머
  페이드 인, 포지션 항 없음)" 패턴을 자동 삽입한다.
- **R**: 소수점 큐 번호 삽입은 검증 문법(31_choreography:56). MIB 자체는
  룰북 무근거(그렙 0건) — 라이브 실측 후 룰북/스킬에 기록.
- **S**: 라이브 — 선행 큐 재생 중 3D에서 빔 미표시(디머 0), 본 큐에서
  이동 없이 페이드 인만 관측.

### T3. 곡 구조 × 포지션 큐 시트

- **G**: 구간 무드 → 곡 전체 포지션 큐 초안 (에너지 곡선: 좁→넓, 사람→공간).
- **E**: `prepare_songcue` 계열 입력(구간+시각+무드)이 주어지면,
- **A**: `position_moods` 매핑으로 구간별 포지션 프리셋을 고르고, 큐를
  프리셋 참조(`At Preset 2.<n>`)로 빌드, T2 MIB 규칙 적용.
- **R**: 확장 지점은 `songcue.py::_section_bundle`(commands 튜플)과
  `SongCueTimingAxes` DESCOPE 패턴 (SongcueScout 실측).
- **S**: 세션 테스트 + 라이브 시퀀스 재생 검증.

## 비목표

- 관객 직사 가드, 포커스 스웨이, 버스킹 페이지 (kickoff 후순위).
- 기존 실패 테스트 3건(prechk/songcue diff/tools 레지스트리)의 수정.

## 함정 계약 (준수 필수)

1. 픽스처당 한 줄 체이닝 (동일 텍스트 dedupe — tools.py:432).
2. 페이저 큐 `/merge` 금지.
3. `Assign Sequence n At Executor m` 형만 사용.
4. Store 뒤 ClearAll, 번호 추측 금지(카드로 질의).
5. 검증은 ok 응답이 아니라 3D 픽셀 diff + prop readback.
