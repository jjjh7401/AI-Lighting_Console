# research/ma3-effects-phaser 작업 정리 (2026-08-15 세션 + 후속 확정)

## 실측/게이트
- V1~V7 라이브 실측 + 오퍼레이터 확인 3건(컬러 Accel/Decel 사인, 프리셋-리콜 Relative 중심추종, MAtricks 프리셋 고착) → 전량 확정, 31_choreography_patterns.md OBSERVED EFFECT 항(append-only grant)에 정본 기록.
- 효과의 기계 증거 채널 부재(childCount 0)는 측정된 경계로 유지 — 사람 관측이 최종 판정.

## 이펙트 3방식 → 자연어 라우팅
- Phaser(파형): find_fx(라이브러리 19종) → 미스 시 compose_fx(자연어 파라메트릭, 동일 로더 스키마 검증). 목적지: 시퀀스+큐(기본) / All 풀 프리셋(큐에는 참조가 실림).
- MAtricks(선택 분할, X축 5종): 두 도구의 공용 축으로 페이저에 얹혀 처리.
- Recipe(참조): 쓰기 미실측 → REQ-FXGEN-018/019 DESCOPE, 읽기 전용. 대안 = 프리셋 목적지.
- 라우팅 주체: 룰북 33_effect_editors 라우팅 표 + 도구 설명("라이브러리 먼저, 손으로 쓰지 말 것"). 판정: 자연어→방식 선택은 성립.

## 기타 변경
- 감사 로그: probe(state_query/property_query/heartbeat, 볼륨 99.9%)를 probe-*.jsonl로 분리 — 보존 2일 + 일 64MiB 캡 + 기동 시 레거시 압축. 1.1G→363M(수동 정리 포함), 이틀 내 ~1MB대 수렴. deploy_of 동반 이벤트는 90일 유지.
- 진행 순서 보드: planned_show_order — 실행된 셋리스트 배분 순서 > 감독 타임라인 단곡 > 빈 계획.
- 셋리스트 모드: 곡→시퀀스 210,220…/페이지1 익스큐터 일괄 배분(빈 슬롯 사전 점검, 승인 1장, readback 검증).
- 프리셋 팝업(정사각+실측 배지), 역방향 로그 리더(RSS 5.6G→106M), 스냅샷 캐시, 섹션 auto-fit.
- 검증: 서버 pytest 8,780 그린.

## 개선 제안 (우선순위)
1. 이펙트 저장 후 익스큐터 자동 배정 옵션 — 셋리스트 모드의 검증 패턴(사전 점검+승인 1장+readback) 재사용. FXLIB §D 계승 제외라 스펙 개정 필요.
2. 복합 요청(fx+fx) 1승인-순차발화 계획 큐잉 — dedupe 경계는 개정 불가(기각 선례), 우회는 계획 단위.
3. compose_fx 설명 예문 '팬은 천천히 틸트는 빠르게' ↔ fx 전역 단일 속도원 스키마 불일치 — 예문 교체(단기) / attribute별 속도 프로브(장기).
4. 레시피 쓰기 라이브 프로브(EditRecipe/Cook, 9005 선점 필요) → DESCOPE 해제 검토.
5. MAtricks Y/Grid 축 프로브 — 매트릭스형 리그 도입 시.
6. 사람 관측 기록 루프 — 프리셋 타일 '무대 확인됨' 마킹.
