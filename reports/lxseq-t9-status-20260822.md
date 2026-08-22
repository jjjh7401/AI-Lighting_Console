# LX-SEQ 연계 프로젝트 진행 현황 — SPEC-COPILOT-LXSEQ-001 (카드 t9)

기간: 2026-08-21 ~ 2026-08-22 · 저장소: jjjh7401/AI-Lighting_Console · 브랜치: jjjh7401/LX-SEQ

## 핵심 지표

| 지표 | 값 |
|---|---|
| 마일스톤 | M0~M4 5/5 종료 |
| 수용기준(AC) | 16/17 PASS (94%), 1건 결함 이월(D2 → t11) |
| PR | #72 MERGED |
| 라이브 검증 | onPC 2.4.2, 86대 패치 확인 |
| 상태 | `status: implemented` (완료 아님 — AC-016 잔여) |

## 전체 로드맵 (4단계 중 1단계 진행)

| 단계 | SPEC ID | 내용 | 상태 |
|---|---|---|---|
| 1 — 패치 | SPEC-COPILOT-LXSEQ-001 | RIG 팩 패치 CSV → 픽스처 패치 | implemented (진행 중, 카드 t9) |
| 2 — 그룹 | SPEC-COPILOT-LXSEQ-002 | FID 매핑표 + GROUP 시트 → 그룹 생성 | ID만 예약, 미착수 |
| 3 — 프리셋/FX | SPEC-COPILOT-LXSEQ-003 | PRESET/FX 시트 → 프리셋·이펙트 | ID만 예약, 미착수 |
| 4 — 시퀀스/큐 | SPEC-COPILOT-LXSEQ-004 | CUE-EX CSV → 시퀀스·큐 | ID만 예약, 미착수 |

## 1단계(t9) 경과

### Plan phase
- v0.1.0 최초 작성 → plan-audit 1회차 FAIL 0.86 → v0.2.0(감독 Kickoff 결정 H·I·J 반영) → v0.2.1(UI 전달 경로를 후속 카드 t10으로 위임) → plan-audit 2회차 FAIL 0.88(N1 blocking) → v0.2.2 수정
- REQ 16건 · AC 17건(라이브 1건) · ASSUMPTION 3건 · 마일스톤 5개(M0~M4) · clarification 마커 0건

### Run phase (M0~M4)
- M0: 감독 Kickoff 결정 3건 기록(입력 채널·이름 접두·모드 미해결 처리)
- M1: 파서(`server/lxseq/parser.py`) — 실물 86행 거부 0·제외 0
- M2: 매퍼(`server/lxseq/mapper.py`) — 타입/모드 확정, 점유 슬롯 판정
- M3: 툴 등재(`import_lxseq_patch`, preview/apply) — 기존 툴 계약 0-diff
- M4: 라이브 확인(onPC 2.4.2) — preview 12런 86대·건너뜀 0 → apply 12런 전량 created, 생성 합 86 → 독립 재조회 `child_count 86` 일치
  - 결함 D1(수정 완료, `d48d4b7`): 매퍼 판독 게이트가 저장소 규약보다 엄격 — 실기 절단선 19대 리그에서 무력화될 위험. 뮤테이션 3회로 검증, 라이브 재검증 통과
  - 결함 D2(미수정, 카드 t11로 분리): 실기 콘솔의 `occupant.fixture_type`이 이름이 아니라 객체 핸들 — `already_patched` 판정이 실기에서 성립하지 않음(대신 `fid_occupied`로 건너뜀, 쓰기는 0건 유지되어 안전상 영향 없음)

### Sync phase
- CHANGELOG·README 반영, `status: implemented`
- 독립 감사(sync-auditor) 1차 FAIL 0.80 → F3·F4·DOC-2 후속 수정(`07bc93b`) → 재판정 FAIL 0.86
  - FAIL 유지 원인은 AC-LXSEQ-016 한 줄(D2에 기인, 의도적으로 t11 위임 — 이 카드가 손대기로 한 항목 아님)
  - 차단 결함 0건, 신규 코드 결함 0건

### PR #72 — MERGED
- 제목: "feat(SPEC-COPILOT-LXSEQ-001): LX-SEQ 패치 CSV 수입 1단계 — 파서 + 매퍼 + 툴 1종 (t9)"

### 머지 후 리뷰 결함 2건 — RV1·RV2 (2026-08-22)
- 원인: 매퍼가 계획한 자리와 콘솔이 실제로 놓을 자리가 어긋나는 축(모드 폭 산정). M4 실기 86대는 타입마다 폭이 하나뿐이라 이 갈래를 지나가지 않았음
- **RV1**: 한 타입에 모드가 2개 섞이면 주소가 밀림 — 모드 확정이 타입당 1회만 일어나고 재사용되던 결함
- **RV2**: `mode_overrides`가 실측 폭 대신 CSV 폭을 사용 — 폭이 구조적으로 사라짐
- 수정(`4d30134`): 해석 캐시 키 확장, 런 경계·연속성·점유 검사를 전부 실효 폭 하나로 통일, 계획 내 겹침 신규 검사(`_reject_plan_overlaps`) 추가
- 수용기준 개정(B안 채택, 감독 결정): `fid_map[2]` 기대값 `1.26` → `1.40` — CSV 주소는 장비의 하드웨어 사실이므로 밀린 자리를 정직히 보고하는 것이 아니라 틀린 자리이기 때문
- 검증: 뮤테이션 6회(양방향), 전체 스위트 9691 passed·8 skipped·exit 0(9682 → +9, 신규 테스트와 일치), 봉쇄 구역 0-diff
- **리드 독립 재검증 PASS**(`c1d9170`, 2026-08-22): 뮤테이션 3/3 RED 독립 재현, 원 재현 입력 2종 재실행 확인, 전체 스위트 재확인

## 앞으로 진행될 내용

| 항목 | 내용 | 처분 |
|---|---|---|
| 카드 t10 | UI 파일 선택기 → 툴 인자(`file_content_base64`) 전달 경로 배선(`ui/` + `server/web/session.py`) | 위임됨, 미착수 |
| 카드 t11 | 결함 D2(FixtureType 핸들 vs 이름) 수정 — 설계 변경 필요 | 이월, 미착수 |
| 카드 t11 후보 | acceptance.md §D DoD 문구 정정(D-2, low) · 좁은 override 물리 폭 이슈 고정 문서화 · 리뷰 지적 #3·#4·#5 재현 검토 | 이월, 미착수 |
| 리드 예고 재현 | 뮤테이션 3·6 재현, 겹침 검사 무력화, RV1·RV2 원입력 재실행 — 아직 실행 안 됨 | 대기 |
| 2단계 | SPEC-COPILOT-LXSEQ-002(그룹) — 착수 전 GROUP 시트 라벨 수 불일치(12 vs 18) 출처 확인 필요 | 미착수 |
| 3단계 | SPEC-COPILOT-LXSEQ-003(프리셋/FX) | 미착수 |
| 4단계 | SPEC-COPILOT-LXSEQ-004(시퀀스/큐) | 미착수 |

## 참고 — 워크트리의 별도 대기 변경사항

`.claude/` 하위 다수 프레임워크 파일이 수정 상태(M)로 남아있음 — LXSEQ-001 작업과 무관한 MoAI 템플릿/규칙 동기화로 보이며, 별도 커밋 대상.

## 출처

- `.moai/specs/SPEC-COPILOT-LXSEQ-001/{spec,plan,acceptance,progress}.md`
- `git log`, `gh pr view 72`, `CHANGELOG.md`
