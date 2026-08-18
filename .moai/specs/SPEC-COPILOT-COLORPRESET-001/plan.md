# SPEC-COPILOT-COLORPRESET-001 — plan

## §A. 마일스톤

### M0 — 라이브 프로브 (판별 채널 + 풀 해석, 비파괴 읽기 ~15분)
- 컬러 어트리뷰트 판별: 측정 리그 41대 중 ColorRGB 미보유 장비 실측
  (2-hop 픽스처 타입 조회 — SPATIAL M0 절차 재사용, `tools/console_probe.py`).
- Color 풀 해석: `DataPool/PresetPools` 자식 이름 판독 → `Color` 풀의 실제
  번호·기존 점유 슬롯 확인 (이 리그는 4.1~4.7에 수동 프리셋 존재 — 07-28 감사).
- 판정 어휘: GO / NEGATIVE / INCONCLUSIVE, `progress.md §E`에 기록.

### M1 — 공용 몸통 풀 매개변수화 (동작 무변경 리팩터)
- `_position_preset_pool_children`·`_store_position_preset_sequence`·
  `_regenerate_position_preset_sequence`·되읽기·점유 헬퍼에 `pool_no`(또는
  해석기) 인자 — 기본값이 오늘의 2번 풀이라 기존 테스트 전건 그린 유지.
- `position_preset_store_commands`(pointing.py)는 `POSITION_PRESET_POOL`
  하드코딩 — spatial 무접촉(REQ-007)이므로 세션 계층에 풀-일반화 저장 명령
  빌더를 두거나 기존 빌더에 인자 추가 여부를 여기서 결정(트립와이어 확인).

### M2 — 컬러 시퀀스 + 라우팅
- `COLOR_PALETTE_SEQUENCE` 10색(라벨+RGB 상수, spec §A.2 표) — 세션 계층 상수.
- `_basic_color_presets` 라우팅: `(기본|베이직|basic)+(컬러|색|color)+동사`,
  포지션 어휘와 상호 배타 검증.
- 미보유 장비 제외+산술 고지 (M0 판별 채널).

### M3 — 재생성 + 회귀
- `first_label="Warm White"` 가족 재생성.
- 상호 오라우팅 코퍼스: 포지션/FX/컬러 3가족 × 저장/재생성 6경로.

### M4 — 라이브 E2E
- 빈 구간 저장 → 콘솔 프로브로 슬롯·라벨 실재 확인 → 재생성 제자리 갱신 →
  onPC GUI에서 색 확인(사람 관측 1회).

## §B. 위험

| 위험 | 완화 |
|---|---|
| 풀 4에 수동 프리셋 4.1~4.7 존재 (실측) | 점유 검사·카드가 그대로 방어 — E2E에서 충돌 카드 시나리오로 검증 |
| 공용 몸통 리팩터가 포지션 경로 회귀 | REQ-006: 기본값 유지 + 기존 테스트 무수정 그린 |
| tools.py 접촉 필요해질 가능성 (풀 목록 판독 경로) | 세션은 registry query_state로 이미 풀 목록을 읽는다 — tools.py 무접촉 예상, 불가피 시 헝크핀 상례 |

## §C. Out of Scope 재확인
spec §C 참조 — 특히 컬러 체이스 소비는 기존 fx 라이브러리 중복 분석 선행.
