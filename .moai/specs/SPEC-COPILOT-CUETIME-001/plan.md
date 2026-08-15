# SPEC-COPILOT-CUETIME-001 — 구현 계획

## 오케스트레이션 판단

- 조사: 병렬 (scout 3 — session/songcue/grammar) — 완료, research.md 참조.
- 구현·검증: **직렬** — T2는 T1 빌더 의존, T3는 T1+T2 의존, 라이브 콘솔·
  서버 포트가 단일 자원이라 병렬 라이브 검증 불가.

## M1 (T1) — 포지션 큐 저장 빌더 + 세션 어휘

1. `server/spatial/pointing.py`:
   `position_cue_store_commands(sequence_no, cue_no, *, fade_seconds=None,
   label=None)` → `("Store Sequence S Cue C ['name'] [CueFade F]",)`.
   경계: 양수 시퀀스/큐(소수점 큐 허용), fade ≥ 0 유한, 라벨 따옴표 금지
   (기존 `position_preset_store_commands` 관례 동일).
2. `server/web/session.py`:
   - `_PRESET_CUE_STORE` 정규식 — "프리셋 N … 큐로 저장", "시퀀스 S 큐 C",
     "페이드 F초" 캡처 (`_LOOK_PRESET_STORE`:165 옆).
   - 핸들러 `_position_cue_store` (라우팅: look 뒤, point 앞):
     프리셋 번호 필수(명시 없으면 None→모델 경로), 시퀀스 미지정 시
     `_ask_one` 카드, 번들 = 선택+`At Preset 2.N` → Store → `ClearAll`,
     단일 `run_commands` dispatch.
3. 테스트: `test_spatial_pointing.py`(빌더), `test_web_session.py`(어휘·
   카드·번들 텍스트). ruff.
4. 라이브: 서버 재시작 → WS로 "프리셋 2.28을 시퀀스 101 큐 1로 저장,
   페이드 5초" → `Go+ Sequence 101` → 페이드 중간/완료 3D 프레임 diff,
   responder prop `CueFade` readback.

## M2 (T2) — MIB 규칙

- `server/looks/` 또는 `server/spatial/`에 MIB 삽입 계산
  (`mib_insertions(cues) -> 선행 큐 목록`), T1 빌더 재사용(소수점 번호).
- 라이브 실측으로 MIB 동작 확인 후 스킬 기록.

## M3 (T3) — songcue × position_moods

- `songcue.py` 확장: 구간 무드→프리셋 선택, `_section_bundle`에 프리셋
  리콜 라인, MIB 축 (`SongCueTimingAxes` 패턴).

## 검증 사이클 (각 M 공통)

구현 → `uv run pytest <scope>` + ruff → 서버 재시작 → WS 라이브(자동 승인
스크립트) → 3D 스크린샷 픽셀 diff → 함정 발견 시 SKILL.md 기록 → 커밋.
