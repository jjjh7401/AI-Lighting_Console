# 2026-08-15 세션 핸드오프 — MA3 이펙트(Phaser) 생성 + 코파일럿 UI 개편

브랜치: `research/ma3-effects-phaser` (main 미병합, 원격 미푸시).
콘솔: onPC 2.4.2 라이브, 서버는 hub 항목 `grandma3-web-stable`(8765)이 관리.

## 1. 이펙트/페이저 역량 (SPEC-COPILOT-FXGEN-001)

### 라이브 실측 (V1~V7 — spec.md §A에 정본 기록)
- V1 `Step <k> At Accel/Decel -100` — **스텝 열 완성 후** 발화하면 사인 페이드 (M0 SKIP의 원인은 발화 순서였다)
- V2 `At Relative <n>` 스텝 값 — 현재 위치 위에 승차
- V3 `At SpeedMaster <n>` — 라이브 변속; 고정 Speed와 동시 지정은 미측정 → 두 계층에서 거부
- V4 `At Width 25` + `At Measure 4` 동시 확인
- V5 3스텝 RGB + 채널별 phase 스프레드 = 레인보우
- V6 `Store Preset 21.101 '<label>' /Universal` — All 1 풀(기본 쇼파일에서 21) 저장, **풀 목록 readback = 기계 증거**
- V7 `Group N` + `At Preset 21.n` → 큐 저장. 프리셋 내용은 여전히 기계 판독 불가 → 효과는 사람 관측

### 구현 (전부 커밋 완료)
- `server/fx/schema.py`/`loader.py`/`instantiate.py`: accel/decel·relative(bool)·speed_master·width·measure 방출. `SPEED_SOURCE_CONFLICT`, 프리셋 목적지(`build_fx_preset_bundle`, `select_preset_number` — 풀·슬롯 재조회 실측만)
- `server/orchestrator/tools.py`: **`compose_fx` 신설**(TOOL_NAMES 32) — 자연어 파라메트릭 페이저, 출하 라이브러리와 동일 로더 스키마 검증, `_deliver_fx_plan` 단일 관문. `instantiate_fx`에 `destination: "preset"` 추가
- 라이브러리 19종 (신규 7: pulse-sine-breath, pulse-snap, pulse-master-sync, sweep-relative-center, circle-relative-orbit, sweep-sine-ease, chase-rainbow-wave)
- 룰북 자산 `33_effect_editors.md` (허가 추가 2호) — Phaser/Recipe/MAtricks 3패러다임 라우팅 + **레시피 쓰기 금지 경계**(EditRecipe/Cook 미실측 → 읽기 전용)
- 리서치 코퍼스 `docs/research/ma3-effects/00~07` (오케스트레이션 병렬 7워커)

### 콘솔 잔여물 (사용자 테스트용)
- Preset All 1(풀 21) 슬롯 1~9: Breath FX(동작 확인됨) / Snap Pulse / Master Sync Pulse / Rainbow Wave / Warm Cool Sine / Relative Orbit / Eased Sweep / Mirror Tilt Wave / Shuffle Chase
- **미회수 관측 3건** (게이트 판정 대기): ① 21.5 — Accel/Decel이 컬러 축에서도 사인인가 ② 21.6 — Relative가 프리셋 리콜 경유로도 중심-추종인가 ③ 21.8/21.9 — MAtricks 형상(미러/셔플)이 프리셋에 고착되는가

## 2. UI/성능 (전부 커밋 완료)
- 프리셋 팝업: 카테고리 카드(정보 있는 풀만) → 정사각 팝업, onPC 정사각 타일 통일, 단어 경계 줄바꿈, 노란 개수 배지(실측 stored_count만). API `GET /api/presets/{pool}` — 해피패스 1쿼리
- **성능 근본 수정**: `AuditLog.iter_events_reversed`(709MB 로그 → 4MiB 역방향 청크; RSS 5.6GB→106MB, `/` 8s→ms). stale-while-revalidate 스냅샷 캐시(`WebDeps.snapshots`). 드릴 예산 실측 상향(프리셋 12→16, 익스큐터 verify 16→32 — 슬롯당 2쿼리)
- 대시 순서: 그룹→프리셋→매크로 대신 **그룹→프리셋→익스큐터→매크로→플러그인** (서버측 재배열, REQ-DASHUI-003)
- 섹션 창 auto-fit(45vh 상한, 드래그 우선)
- 큐 진행 모니터 = **진행 순서 보드**: 세로 리스트, 감독 타임라인 시퀀스 선두 + "진행 n" 배지(`order_by_show_plan`), 진행도 "큐 x/y"(재생 가능 큐만, 확인된 현재 큐만)

## 3. 환경 주의사항
- **서버 이중 기동 금지**: `grandma3-web-stable`(hub, persist)이 8765/9005 관리. 과거 좀비(9005만 물고 8765 없는 인스턴스)가 생기면 `lsof -nP -iUDP:9005`로 찾아 kill
- 감사 로그는 백그라운드 폴러(초당 ~10건)가 계속 키움(현재 709MB+) — 읽기는 이제 bounded지만 **로그 자체의 성장/보존 정책은 미해결 과제**
- 콘솔 프로브는 `tools/console_probe.py`(9005 선점 필요 — 서버 잠시 내릴 것)

## 4. 테스트 상태
- 서버 pytest: 전체 그린(단, 사용자 병행 WIP에 따라 프리핀류 변동 가능). UI vitest 449 + tsc 클린
- 이 세션 신규 테스트: fx 5축/compose/preset ~30건, presets API 9, cue monitor ordering 3+3, audit tail-read 5, autofit/배지/세로리스트 핀

## 5. 다음 후보
1. 미회수 관측 3건 반영 → 스펙 게이트 확정 (컬러 Accel/Decel, 프리셋-리콜 Relative, MAtricks 고착)
2. 감사 로그 성장 억제(프로브 이벤트 샘플링/일별 상한/보존 단축)
3. 진행 순서 보드에 세트리스트(타임라인 라이브러리 다곡) 순서 연동 확대
4. 레시피 쓰기 경로 라이브 프로브(EditRecipe/Assign/Cook) → DESCOPE 해제 여부
