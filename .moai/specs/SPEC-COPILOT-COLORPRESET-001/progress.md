# SPEC-COPILOT-COLORPRESET-001 — progress

## §E. 라이브 판정

### §E.1 M0 — 판별 채널 + 풀 해석 프로브 (2026-08-16, onPC 2.4.2.2, 비파괴 읽기)

**GO** — 열린 결정 2건 모두 실측으로 닫힘.

| 판정 | 채널 | 실측 |
|---|---|---|
| GO: 컬러 판별 3-hop | ① `prop <fixture>\|FixtureType` → `"FixtureType N"` ② `prop <fixture>\|Mode` → `"<m> <이름>"` ③ `state Patch/FixtureTypes/N/DMXModes/m/DMXChannels` 자식 이름에 `ColorRGB` 포함 여부 | 타입2 MMX: `ColorRGB_R/G/B`+`Color1`휠 ✓ · 타입3 LEDBeam350: `ColorRGB_R/G/B/W` ✓ · 타입1 Sphere: 채널 1개(`DMXChannel 1`) ✗ · 타입4 Sharpy: `Color1` 휠만, RGB 믹싱 ✗ |
| GO: 제외 대상 | 이 리그 41대 중 **fid 40(Sha25Bea)·41(Sphere) 제외 = 2대** | REQ-005의 산술 고지 기준값 |
| GO: 풀 이름 매칭 | `state DataPool/PresetPools` 자식 이름 | 풀 4 = `Color` (1 Dimmer · 2 Position · 3 Gobo · 4 Color · 5 Beam …) — 이름 일치 탐색 채택, 실패 시 거부 |
| 주의 | 타입2 채널 목록 truncated(29 중 15) | 채널 판독은 **페이징 필수** (응답기 1.6.0 offset — 이미 배포됨) |
| 주의 | Color 풀 4.1~4.7 수동 프리셋 실존 | 점유 검사·덮어쓰기 카드가 그대로 방어 — E2E 시나리오에 포함 |

비용: 판별은 (타입,모드) 조합 단위 캐시 — 이 리그는 조합 5개 이하, 픽스처당 prop 2회.

## §F. 마일스톤 상태

- M0 ✅ GO (위)
- M1~M3 ✅ (커밋 ef0103a — 전체 스위트 9080 그린, 포지션/FX 무수정 무회귀)
- M4 ✅ 라이브 E2E (2026-08-16 23:2x KST, onPC 2.4.2.2):
  - 빈 구간 카드가 콘솔 검증 구간(4.11~/4.21~)만 제안 — 점유 4.1~4.7 회피 ✅
  - 판별 산술: "전체 41대 중 39대 적용, 제외 2대(FID 40, 41)" — M0 실측과 정확 일치 ✅
  - 되읽기: "기대 10개 중 10개 확인" — 27개 풀(캡 24 초과)에서 페이지드 판독 ✅
  - 콘솔 프로브: 4.11~ 'Warm White'~'Magenta' 라벨 실재 ✅
  - 참고: E2E 2회 실행으로 4.11~4.30에 두 벌 저장됨 — 한 벌은 onPC에서 수동 삭제 가능(Delete는 앱 블랙리스트)

- plan_complete_at: 2026-08-16T23:25+09:00
- plan_status: audit-ready
