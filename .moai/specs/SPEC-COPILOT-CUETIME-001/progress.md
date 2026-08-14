# SPEC-COPILOT-CUETIME-001 — 진행 기록

## M1 (T1) — 완료 2026-08-14

- 구현: `position_cue_store_commands` + `preset_recall_command`
  (server/spatial/pointing.py), 세션 어휘 `_position_cue_store`
  (server/web/session.py — 라우팅 basic_presets 뒤·look 앞), 시퀀스 미지정
  시 질문 카드 1장, 무응답 거절.
- 테스트: test_spatial_pointing.py `TestPositionCueStore`(7),
  test_web_session.py `TestPositionCueStoreSession`(5) — 스코프 스위트
  124 passed, ruff clean.
- 라이브 (onPC 2.4.2, 무빙 40대 링):
  - WS "프리셋 2.28을 시퀀스 101 큐 1로 저장, 페이드 5초" → 3/3
    executed_ok. 콘솔 산출물: **Sequence 101 Cue 1 'Pos 228'** (Preset
    2.28 Cross 참조).
  - readback: Part `CueInFade` = **5.0** (Cue의 CueFade prop은 not
    readable — Part 레벨이 정답).
  - 3D 픽셀 diff (Go+ 재생): t1→t3 215k px, t3→t7 400k px (이동 중),
    t7→t8.5 **5 px** (정지) — 5초 페이드 프로파일 정합.
  - 픽스처 시트 PanTilt 열 "2.28 Cro…" 표시 — 프리셋 참조 저장 성립.
- 신규 실측 함정 2건 스킬 §3b 기록: 큐 이름 점(.) 제거, CueInFade
  readback 경로.
- 도구: tools/ws_live_t1.py (WS 원샷 드라이버 — 승인 자동, 카드 답변
  스크립트).

## M2 (T2 MIB) — 미착수

## M3 (T3 곡 시트) — 미착수
