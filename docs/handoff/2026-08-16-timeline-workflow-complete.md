# MA3 코파일럿 — 감독 타임라인 워크플로우 완결 핸드오프 (2026-08-16)

> 2026-08-15 핸드오프(`2026-08-15-timeline-workflow-handoff.md`)를 대체한다.
> 그 문서의 "다음 작업 1~6"은 전부 구현·검증·main 머지 완료.

## 실행 환경
- 테스트 주소: `http://127.0.0.1:8765/` — 감독 프로세스 `grandma3-web-stable`
  (`.venv/bin/python -m server.web`, cwd=이 저장소, `restart=on-failure`+persist,
  ready체크 `@copilot:ready`/포트 8765). 코드 변경 후 `cd ui && npx vite build` → 재시작.
- OSC: 콘솔 8000 송신 / 앱 수신 9005 (`settings.toml`의 receive_port).
  **주의**: 다른 세션이 `--receive-port 9000`으로 프로세스를 교체 기동한 사고가 있었음
  — console_offline이면 `hub describe grandma3-web-stable`로 argv/cwd부터 확인.
- 브랜치: `research/ma3-effects-phaser` == `main` (머지 커밋 `c2aec1d`, 전부 푸시됨).
- 테스트: 서버 8,789 passed · UI 450 passed.

## 완성된 워크플로우 (전부 라이브 또는 재현 스크립트 검증)
곡 브리프 → 인터뷰(검증 번호 제안 포함) → PLAN 타임라인(무제한 편집) → 승인(영향 요약)
→ 원자 실행+readback → 자동 버전 스냅샷 → 셋리스트 배분 → 리허설 "지금 이 큐" 편집.

- PLAN 편집 어휘: 포지션/컬러/디머(D1~5)/페이드/FX on-off/시간 이동/큐 추가·삭제/시퀀스 변경. 콘솔 무접촉.
- 오류 예방: 시퀀스 `(비어 있음)`·프리셋 `(저장 확인됨)`·타임코드 빈 슬롯 검증 제안,
  점유/거부 시 복구 카드(빈 슬롯 제안→즉시 재저장, 최대 3회), Store 실패 시 계획 보존+ClearAll,
  보류 계획 새로고침 생존(`PendingSongPlanStore`, 서버 재시작만 소실).
- 탐침 판정 3규칙: `path segment not found` = 비어 있음 확답 / 타임아웃 = 조회 실패(제안 금지,
  1회 재탐침) / 풀 자식 슬롯 번호는 `"i"` 키(PROTOCOL §4.2).
- 현장어: 전환 방식(컷/페이드)·베이스 컬러 결정·큐 타임(자동 진행)·타임코드 N번 슬롯·
  승인 카드 리뷰 요약 한글화. FX 프리셋은 Store 뒤 별도 `Label` 명령(인라인 이름 미적용 실측).

## 콘솔 상태 (onPC 2.4.2.2)
- Sequence 110·120·150·210·240·250·260 점유
  (120=Back 분리 검증 2큐, 240/250/260=셋리스트 실기 복사본, 150=과거 오수정 잔재 미원복).
- Position 프리셋 2.21~2.30 (라벨 있음). FX 프리셋 21.1/21.10~21.12는 **무명**
  — 복구: `Label Preset 21.1 'Breath FX'` 등 실행(라벨은 영어로 — 콘솔 타일 한글 미표시, d56f926).
- Executor 101→Seq 240 · 102→250 · 103→260 (셋리스트 실기 결과.
  원복: `Assign Sequence 17 At Executor 102`, `Assign Sequence 100 At Executor 103`,
  최초 상태는 `Assign Sequence 50 At Executor 101`).

## 실기 검증 완료 (2026-08-16)
- **Copy Sequence** (셋리스트): 210 충돌 → 검증된 대체 구간 카드(240부터) → Copy×3+Assign×3
  전부 executed_ok, Executor readback 3건 일치. ✅
- **Back 그룹 디머 last-wins**: Seq 120에 `Group 11 ; Dimmer At 40/80` 저장 →
  Go 재생에서 Back 픽스처가 키 대비 한 단계 어둡게 출력됨을 **감독 육안 확인**. ✅

## 알려진 이슈
- responder flapping 근본 원인(콘솔측) 미조사 — 탐침은 1회 재시도+진단 표기로 완화.
- 보류 계획은 서버 재시작 시 소실(직렬화 불가한 인터뷰 상태 — 의도된 한계, 안내 문구 있음).
- 같은 포지션이 연속된 두 큐에서 두 번째 recall이 instruction-scope dedupe로
  `skipped_already_executed` — tracking이 커버해 무해하나 두 번째 큐가 포지션 참조를
  잃는다(Seq 120 실기 관측). 후속 후보.

## 다음 후보 (합의 안 된 제안)
1. 레이어 매핑 확장(effect/audience 역할 활용)
2. 브리프 인용형 질문(카드 문장을 곡 설명에서 생성)
3. 동일 포지션 연속 큐의 recall dedupe 예외 처리
4. Sequence 150 잔재 정리 · 무명 FX 프리셋 라벨 복구

## 안전 규칙 (불변)
승인 게이트 경유 없는 콘솔 쓰기 금지 · 기존 슬롯 덮어쓰기 금지(사전점검+복구 카드) ·
탐침 실패는 제안 금지 · 타임라인/라이브러리는 읽기 projection.
