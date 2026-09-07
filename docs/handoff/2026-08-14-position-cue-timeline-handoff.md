# 세션 핸드오프 — 2026-08-14 (position-cue-timeline: T1·T2·T3 완료)

브랜치 **`feature/position-cue-timeline`** (main `614eab9`에서 분기, PR 예정).
SPEC: `.moai/specs/SPEC-COPILOT-CUETIME-001/` (spec/plan/research/acceptance/
progress — progress.md가 마일스톤별 실측 기록의 원본). 전 기능 라이브
콘솔(onPC 2.4.2, 무빙 40대 링)에서 실측 검증.

## 1. 만들어진 것 (커밋 순)

1. `4ee0c88` — **T1 포지션 큐 트랜지션**: `position_cue_store_commands` +
   `preset_recall_command` (spatial/pointing.py), 세션 어휘 "프리셋 N을
   시퀀스 S 큐 C로 저장, 페이드 F초" (`_position_cue_store`).
   `tools/ws_live_t1.py` (WS 원샷 드라이버).
2. `c19e28b` — **T2 MIB**: `server/spatial/mib.py` (`PositionCuePlan`,
   `apply_mib`, `position_cue_bundle`). A/B 실측: moved_away 0 vs 4,731 px.
3. `3824da1` — **T3 곡 시트**: `server/spatial/position_cuesheet.py`
   (songcue 시각 파서 × position_moods × MIB), 세션 어휘 "포지션 큐 시트,
   시퀀스 S, 프리셋 P번부터: 이름 시각 무드, …".
4. `65d22b0` — 실제 앱 UI E2E (1분 헤비메탈 12구간) + digits-only 큐 이름
   폴백.
5. `369a035` — **반복 무드 대안 회전** (`_pick_varied`: 사용 횟수 최소 →
   최저 최근성 → 표 순서; `varied_from` 감사 필드).
6. `9ba5bac` — **MIB Follow 트리거** (`premove_follow_command`): 선이동
   큐는 Store만으론 TrigType=Go로 남아 자체 발화 안 함 — 사용자가 잡아낸
   결함. Go 12번(구간당 1번)으로 14큐 완주 검증.

## 2. 콘솔 잔존 산출물

- Position 프리셋 2.21~2.30 (이전 세션), Sequence 100 (이전 세션).
- **Sequence 101** (T1 데모: Cue 1 'Pos 228', CueInFade 5).
- **Sequence 102** (T2 MIB 데모: 큐 1/2/2.5/3).
- **Sequence 110** (T3 기본 데모: 5구간, MIB 3.5).
- **Sequence 114** (최종 메탈 데모: 12구간 14큐, Follow 선이동 3.5/7.5,
  대안 회전 적용). 111·112·113은 삭제됨.

## 3. 이 세션의 실측 함정 (전부 스킬 §3b~3d에 기록)

1. 큐 이름의 `.`은 MA3가 제거 ('Pos 2.28' → 'Pos 228').
2. CueFade readback은 Cue가 아니라 **Part의 `CueInFade`**.
3. **MIB 선이동 큐는 `TrigType 'Follow'` 필수** — Store만으로는 Go로 남아
   운영자 리빌 Go가 보이지 않는 다크 이동을 재생. 검증은 반드시 운영자
   플로우(구간당 Go 1번)로.
4. 픽셀 검증: 3D 뷰포트만 크롭, 프레임별 Otsu (고정 임계값은 무판별).
5. 한글+숫자 구간명은 ASCII 정리 후 숫자만 남음 → digits-only 폴백.
6. `Delete Sequence n /NoConfirm`은 probe(게이트 밖)에서 팝업 없이 동작.

## 4. 테스트 상태

- 스코프 스위트(mib/position_cuesheet/spatial_pointing/web_session) green,
  전체 8430+ passed.
- **기존 실패는 3건이 아니라 5건**: prechk 웹표면 / songcue diff 가드 /
  tools 레지스트리 + **test_paperwork_patch_sheet 채널폭 상계 2건**
  (main 614eab9에서 재현 확인 — 이 브랜치와 무관).

## 5. 다음 후보 (우선순위 제안)

1. **컬러 × 포지션 통합 시트** — 메탈 연출의 나머지 반쪽. 페이저와 포지션을
   한 프로그래머 상태로 만들어 저장 (`/merge` 금지 함정 주의, 스킬 §3).
2. TrigTime 자동 진행 — 시트가 이미 구간 시각을 파싱함; songcue
   auto_advance 축이 검증된 문법 보유. 비용 최소.
3. 관객 직사 가드 / 포커스 스웨이 / 버스킹 페이지 (제안서 §3~5).
