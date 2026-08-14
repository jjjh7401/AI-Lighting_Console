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

## M2 (T2 MIB) — 완료 2026-08-14

- 구현: `server/spatial/mib.py` — `PositionCuePlan`, `apply_mib`(다크→
  리빌+새 프리셋이면 중간 번호에 포지션 전용 선이동 큐 삽입, 리빌 큐
  포지션 제거, 불명 시작 상태는 점등 간주), `position_cue_bundle`
  (T1 빌더 재사용).
- 테스트: test_mib.py 12개 — 65 passed (mib+pointing 스코프), ruff clean.
- 라이브 A/B (Seq 102 MIB vs Seq 103 대조군, Wide 2.26→Black→Cross 2.28):
  - 다크 선이동(큐 2.5) 중 가시 변화 0 px.
  - 리빌 t0.5→t2.5 moved_away: MIB **0 px** vs 대조군 **4,731 px**,
    기하 IoU(Otsu) 0.70 vs 0.54 — 허우적거림 제거 정량 확인.
  - 콘솔 산출물: **Sequence 102** (MIB 데모, 큐 1/2/2.5/3) 잔존.
    대조군 103은 삭제.
- 계측 노하우 스킬 §3c 기록 (뷰포트 크롭, 프레임별 Otsu, 고정 임계값
  함정, /NoConfirm).

## M3 (T3 곡 시트) — 완료 2026-08-14

- 구현: `server/spatial/position_cuesheet.py` —
  `build_position_cue_sheet` (songcue `normalise_start_ms` × position_moods
  × mib.apply_mib 결합), 세션 어휘 `_position_cue_sheet`
  ("포지션 큐 시트, 시퀀스 S, 프리셋 P번부터: 이름 시각 무드, …";
  시퀀스·프리셋 기준 미지정 시 카드 각 1장, 무응답 거절, 큐별 개별 번들).
- 테스트: test_position_cuesheet.py 6개 + 세션 4개 — 스코프 146 passed,
  ruff clean.
- 라이브 (Seq 110, 5구간: 잔잔→Vocal DSC 2.25 / 오프닝→Center 2.24 /
  암전 / 클럽 드롭→Cross 2.28 / 피날레→Ring In 2.30):
  - 큐 1/2/3/**3.5 'Section 4 Move'**/4/5 콘솔 실재 — MIB 자동 삽입.
  - 구간 간 기하 IoU 0.12~0.16 (전부 구별되는 포지션), 암전·다크 선이동
    가시 변화 0 px, 리빌 moved_away 0 px.
  - 콘솔 산출물: **Sequence 110** (곡 시트 데모) 잔존.
- 스킬 §3d 기록.

## 최종 E2E — 실제 앱 UI 경로 (2026-08-14)

- 브라우저(http://127.0.0.1:8765) 채팅 입력 → 미리보기 카드 → 실행:
  - Seq 111 (3구간): 13명령 실행 완료, 큐 1/2/2.5 Move/3, 리빌
    moved_away 1 px.
  - **Seq 112 — 1분 헤비메탈 (12구간, 페이드 0.5초)**: 49명령 실행 완료,
    14큐(암전 히트 2회 → MIB 3.5·7.5 자동 삽입). 재생 정량: 블랙 3회
    53 px(잔여 UI), 다크 이동 2회 비가시, 점등 룩 7종 IoU 0.01~0.65로
    전부 구별, 반복 리콜(Cross·Fan Out) 픽셀 수 완전 동일(결정론).
- 발견·수정: 한글+숫자 구간명("브레이크1")이 ASCII 정리 후 숫자만 남아
  큐 이름이 '1'로 퇴화 — digits-only 폴백('Section n') 추가, 테스트 고정.

## 반복 포지션 다양화 (사용자 피드백, 2026-08-14)

- 지적: 메탈 시트에서 동일 무드 반복 → 동일 프리셋 반복 (Cross×2,
  Fan Out×2, 픽셀 단위 동일).
- 수정: `_pick_varied` — 무드 항목의 alternatives 위에서 결정론 회전
  (사용 횟수 최소 → 최저 최근성 → 표 순서). 첫 등장은 대표 룩 유지,
  반복은 같은 결의 새 대안으로. `PositionSheetResolution.varied_from`
  기록 + 세션 요약에 "대안" 표시.
- 라이브 (Seq 113, 동일 12구간): 드롭1=Cross vs 후렴=**Ring Out**
  (IoU 0.46, 이전 1.00), 벌스=Fan Out vs 기타솔로=Cross — 점등 9큐가
  8종 룩 사용. 콘솔 정리: Seq 111·112 삭제, 110·113 잔존.
